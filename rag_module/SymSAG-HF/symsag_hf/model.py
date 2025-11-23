"""
SymSAG-HF Hugging Face model definition.

The model aligns semantic (text) and symbolic (expression) nodes inside a
graph.  Training happens via random walks + node2vec-style objectives handled
outside the core ``forward`` method, but the class still exposes a regular
``PreTrainedModel`` surface so that checkpoints integrate with the Hub.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import torch
from torch import nn
from transformers import PreTrainedModel

from .config import SymSAGConfig
from .data import chunk_text, detect_expressions
from .embeddings import EmbeddingEncoder
from .graph import BoostXGraph, GraphNode, LAYER_EXPR, LAYER_TEXT
from .perplexity import PerplexityScorer


class SymSAGModel(PreTrainedModel):
    config_class = SymSAGConfig
    _keys_to_ignore_on_load_missing = ["node_embeddings"]

    def __init__(self, config: SymSAGConfig) -> None:
        super().__init__(config)
        text_dim = config.text_encoder.get("dim", 384)
        expr_dim = config.expr_encoder.get("dim", 768)
        self.text_project = nn.Linear(text_dim, text_dim, bias=False)
        nn.init.eye_(self.text_project.weight)
        self.expr_project = nn.Linear(expr_dim, text_dim, bias=False)
        self.node_embeddings = nn.Parameter(torch.zeros(0, text_dim), requires_grad=False)
        graph_kwargs = {
            key: config.graph.get(key)
            for key in ("max_nodes", "storage_format", "backend", "seed")
            if key in config.graph
        }
        self._graph_kwargs = graph_kwargs
        self.graph = BoostXGraph(**graph_kwargs)
        self._text_encoder: Optional[EmbeddingEncoder] = None
        self._expr_encoder: Optional[EmbeddingEncoder] = None
        self._ppl = PerplexityScorer(
            text_model=config.specificity.get("text_model", "gpt2"),
            expr_model=config.specificity.get("expr_model", "gpt2"),
            expr_structural_weight=config.specificity.get("expr_structural_weight", 0.25),
            use_lm=config.specificity.get("use_lm", True),
        )
        self.node_index: Dict[str, int] = {}
        self.post_init()

    # ------------------------------------------------------------------ HF API
    def forward(
        self,
        text_embeddings: Optional[torch.Tensor] = None,
        expr_embeddings: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """Fuse provided embeddings into the shared latent space."""
        outputs: Dict[str, torch.Tensor] = {}
        if text_embeddings is not None:
            outputs["text_embeddings"] = self.text_project(text_embeddings)
        if expr_embeddings is not None:
            outputs["expr_embeddings"] = self.expr_project(expr_embeddings)
        return outputs

    # ------------------------------------------------------------- encoders
    def get_text_encoder(self) -> EmbeddingEncoder:
        if self._text_encoder is None:
            enc_cfg = self.config.text_encoder
            self._text_encoder = EmbeddingEncoder(
                enc_cfg["model_name"],
                normalize=enc_cfg.get("normalize", True),
            )
        return self._text_encoder

    def get_expr_encoder(self) -> EmbeddingEncoder:
        if self._expr_encoder is None:
            enc_cfg = self.config.expr_encoder
            self._expr_encoder = EmbeddingEncoder(
                enc_cfg["model_name"],
                normalize=enc_cfg.get("normalize", True),
            )
        return self._expr_encoder

    # -------------------------------------------------------------- graph ops
    def build_graph(self, documents: Sequence[str]) -> None:
        """Construct the dual-layer graph from raw documents."""
        self.graph = BoostXGraph(**self._graph_kwargs)
        text_encoder = self.get_text_encoder()
        expr_encoder = self.get_expr_encoder()
        text_nodes: List[GraphNode] = []
        expr_nodes: List[GraphNode] = []
        anchor_edges: List[tuple[str, str]] = []
        for doc_idx, doc in enumerate(documents):
            for chunk_idx, chunk in enumerate(chunk_text(doc)):
                node_id = f"text_{doc_idx}_{chunk_idx}"
                text_embedding = text_encoder.encode([chunk])[0]
                text_embedding = self._project_text_embedding(text_embedding)
                ppl = self._ppl.text_perplexity(chunk).value
                text_nodes.append(
                    GraphNode(
                        node_id=node_id,
                        layer=LAYER_TEXT,
                        embedding=text_embedding,
                        perplexity=ppl,
                        metadata={"doc_idx": doc_idx, "text": chunk},
                    )
                )
                for expr_idx, expr in enumerate(detect_expressions(chunk)):
                    expr_id = f"expr_{doc_idx}_{chunk_idx}_{expr_idx}"
                    expr_embedding = expr_encoder.encode([expr])[0]
                    expr_embedding = self._project_expr_embedding(expr_embedding)
                    expr_ppl = self._ppl.expression_perplexity(expr).value
                    expr_nodes.append(
                        GraphNode(
                            node_id=expr_id,
                            layer=LAYER_EXPR,
                            embedding=expr_embedding,
                            perplexity=expr_ppl,
                            metadata={"text_anchor": node_id},
                        )
                    )
                    anchor_edges.append((expr_id, node_id))
        self.graph.add_nodes(text_nodes + expr_nodes)
        for expr_id, text_id in anchor_edges:
            self.graph.add_edge(expr_id, text_id, edge_type="ANCHOR_OCCURS_IN", weight=1.0)
        graph_cfg = self.config.graph
        self.graph.build_knn_edges(LAYER_TEXT, k=graph_cfg.get("knn_k", 64), edge_type="TEXT_SIM")
        self.graph.build_knn_edges(LAYER_EXPR, k=graph_cfg.get("knn_k", 64), edge_type="EXPR_SYN")
        self.graph.percentile_prune(graph_cfg.get("percentile", 95))
        self._refresh_node_embeddings()

    def fuse_layers(self) -> torch.Tensor:
        """Return the fused embedding table (text + expr)."""
        return self.node_embeddings

    def state_dict(self, *args, **kwargs):
        """Exclude node_embeddings to avoid shape-mismatch issues."""
        state = super().state_dict(*args, **kwargs)
        state.pop("node_embeddings", None)
        return state

    # ------------------------------------------------------------- persistence
    def save_pretrained(self, save_directory: str, **kwargs) -> None:
        super().save_pretrained(save_directory, **kwargs)
        graph_dir = Path(save_directory) / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        self.graph.save(graph_dir / "graph.json")

    @classmethod
    def from_pretrained(cls, pretrained_model_name_or_path: str, *model_args, **kwargs):
        model = super().from_pretrained(pretrained_model_name_or_path, *model_args, **kwargs)
        graph_path = Path(pretrained_model_name_or_path) / "graph" / "graph.json"
        if graph_path.exists():
            model.graph = BoostXGraph.load(graph_path)
            model._refresh_node_embeddings()
        return model

    # ------------------------------------------------------------- utilities
    def _refresh_node_embeddings(self) -> None:
        if not self.graph.nodes:
            dim = self.config.text_encoder.get("dim", 384)
            self.node_embeddings = nn.Parameter(torch.zeros(0, dim), requires_grad=False)
            return
        embeddings = []
        node_ids = []
        for node_id, node in self.graph.nodes.items():
            embeddings.append(node.embedding)
            node_ids.append(node_id)
        stacked = torch.tensor(np.stack(embeddings), dtype=torch.float32)
        self.node_embeddings = nn.Parameter(stacked, requires_grad=False)
        self.node_index = {node_id: idx for idx, node_id in enumerate(node_ids)}

    def _project_text_embedding(self, embedding: np.ndarray) -> np.ndarray:
        tensor = torch.from_numpy(embedding).float().unsqueeze(0)
        with torch.no_grad():
            projected = self.text_project(tensor)
        return projected.squeeze(0).cpu().numpy()

    def _project_expr_embedding(self, embedding: np.ndarray) -> np.ndarray:
        tensor = torch.from_numpy(embedding).float().unsqueeze(0)
        with torch.no_grad():
            projected = self.expr_project(tensor)
        return projected.squeeze(0).cpu().numpy()
