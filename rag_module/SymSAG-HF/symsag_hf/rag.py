"""
Graph-aware retrieval augmented generation helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Sequence

import numpy as np

try:
    import sympy as sp
except Exception:  # pragma: no cover - optional dependency
    sp = None


@dataclass
class RetrievedItem:
    node_id: str
    score: float
    text: str | None = None


class SymSAGRAGPipeline:
    """
    Lightweight RAG pipeline that uses SymSAG-HF embeddings as a knowledge base.
    """

    def __init__(self, model: Any, *, top_k: int = 5, symbolic_verifier: str = "sympy") -> None:
        self.model = model
        self.top_k = top_k
        self.symbolic_verifier = symbolic_verifier
        self._index_matrix: np.ndarray | None = None
        self._node_ids: List[str] = []

    def index_graph(self) -> None:
        """Prepare a dense index of graph embeddings."""
        fused = self.model.fuse_layers()
        if fused.numel() == 0:
            self._index_matrix = np.empty((0, fused.shape[-1]), dtype=np.float32)
            self._node_ids = []
            return
        self._index_matrix = fused.detach().cpu().numpy()
        self._node_ids = list(self.model.node_index.keys())

    def retrieve(self, query: str) -> List[RetrievedItem]:
        if self._index_matrix is None:
            self.index_graph()
        if self._index_matrix is None or self._index_matrix.size == 0:
            return []
        encoder = self.model.get_text_encoder()
        query_emb = encoder.encode([query])[0]
        sims = self._index_matrix @ query_emb
        top_idx = np.argsort(sims)[::-1][: self.top_k]
        results: List[RetrievedItem] = []
        for idx in top_idx:
            node_id = self._node_ids[idx]
            score = float(sims[idx])
            metadata = self.model.graph.nodes[node_id].metadata
            text = metadata.get("text") if metadata else None
            results.append(RetrievedItem(node_id=node_id, score=score, text=text))
        return results

    def answer(self, query: str) -> dict:
        """
        Simple QA routine that returns retrieved nodes plus optional symbolic
        verification output (via SymPy).
        """
        items = self.retrieve(query)
        verification = None
        if self.symbolic_verifier == "sympy" and sp is not None and items:
            try:
                exprs = [sp.sympify(item.text) for item in items if item.text]
                if exprs:
                    verification = sp.simplify(sum(exprs))
            except Exception:
                verification = None
        return {"query": query, "items": items, "verification": verification}
