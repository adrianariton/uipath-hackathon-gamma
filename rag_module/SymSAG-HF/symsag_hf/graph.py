"""
BoostX graph wrapper.

The real project targets the C++ BoostX backend.  In this reference
implementation we expose a Python-first wrapper that mimics the API while using
``networkx`` underneath.  The wrapper focuses on:

* layer-aware node insertion (text vs. expression),
* percentile-based edge pruning via t-digest,
* dual-layer random walks with configurable layer-switch probability,
* HF-friendly serialization hooks.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import networkx as nx
import numpy as np
from tdigest import TDigest

EDGE_TYPES = {
    "TEXT_SIM",
    "EXPR_SYN",
    "EXPR_FUN",
    "ANCHOR_OCCURS_IN",
}

LAYER_TEXT = "text"
LAYER_EXPR = "expr"


@dataclass
class GraphNode:
    node_id: str
    layer: str
    embedding: np.ndarray
    perplexity: Optional[float] = None
    metadata: Dict[str, object] = field(default_factory=dict)


class BoostXGraph:
    """Simple in-memory approximation of the BoostX backend."""

    def __init__(
        self,
        *,
        max_nodes: int = 1_000_000,
        storage_format: str = "csr",
        backend: str = "boostx",
        seed: int = 42,
    ) -> None:
        self.max_nodes = max_nodes
        self.storage_format = storage_format
        self.backend = backend
        self.random = random.Random(seed)
        self.graph = nx.MultiDiGraph()
        self.nodes: Dict[str, GraphNode] = {}

    # ------------------------------------------------------------------ nodes
    def add_nodes(self, nodes: Sequence[GraphNode]) -> None:
        """Register a batch of nodes."""
        if len(self.nodes) + len(nodes) > self.max_nodes:
            raise ValueError("Adding nodes would exceed max_nodes limit.")

        for node in nodes:
            if node.node_id in self.nodes:
                raise ValueError(f"Duplicate node id {node.node_id}")
            self.nodes[node.node_id] = node
            self.graph.add_node(
                node.node_id,
                layer=node.layer,
                perplexity=node.perplexity,
                **node.metadata,
            )

    # ------------------------------------------------------------------ edges
    def add_edge(self, source: str, target: str, *, edge_type: str, weight: float) -> None:
        """Insert a typed edge with normalized weight."""
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"Unsupported edge type: {edge_type}")
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("Source or target node missing.")
        norm_weight = float(np.clip(weight, 0.0, 1.0))
        self.graph.add_edge(source, target, edge_type=edge_type, weight=norm_weight)

    def build_knn_edges(
        self,
        layer: str,
        *,
        k: int,
        edge_type: str,
    ) -> None:
        """
        Construct KNN edges inside a layer.  ``k`` is applied per node.

        The routine operates on the stored embeddings, so it is adequate for
        small and medium graphs during development even though it is not backed
        by the real BoostX native implementation.
        """
        node_ids = [nid for nid, node in self.nodes.items() if node.layer == layer]
        if not node_ids:
            return

        matrix = np.stack([self.nodes[nid].embedding for nid in node_ids])
        norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9
        matrix = matrix / norms
        sim = matrix @ matrix.T

        for i, src in enumerate(node_ids):
            neighbors_idx = np.argsort(sim[i])[::-1]
            added = 0
            for j in neighbors_idx:
                if src == node_ids[j]:
                    continue
                self.add_edge(src, node_ids[j], edge_type=edge_type, weight=float(sim[i, j]))
                added += 1
                if added >= k:
                    break

    # ------------------------------------------------------------ edge prune
    def percentile_prune(self, percentile: float) -> None:
        """
        Remove edges whose weight falls below ``percentile`` according to a
        streaming t-digest estimate.  Keeps anchor edges intact.
        """
        digest = TDigest()
        weighted_edges: List[Tuple[str, str, int]] = []
        for u, v, key, data in self.graph.edges(data=True, keys=True):
            if data.get("edge_type") == "ANCHOR_OCCURS_IN":
                continue
            digest.update(float(data.get("weight", 0.0)))
            weighted_edges.append((u, v, key))
        if not weighted_edges:
            return
        if hasattr(digest, "quantile"):
            threshold = digest.quantile(percentile / 100.0)
        else:
            threshold = digest.percentile(percentile)
        to_remove: List[Tuple[str, str, int]] = []
        for u, v, key in weighted_edges:
            weight = float(self.graph[u][v][key].get("weight", 0.0))
            if weight < threshold:
                to_remove.append((u, v, key))
        self.graph.remove_edges_from(to_remove)

    # -------------------------------------------------------------- serialization
    def to_dict(self) -> Dict[str, Dict]:
        """Serialize nodes + adjacency for ``save_pretrained``."""
        return {
            "nodes": {
                node_id: {
                    "layer": node.layer,
                    "embedding": node.embedding.tolist(),
                    "perplexity": node.perplexity,
                    "metadata": node.metadata,
                }
                for node_id, node in self.nodes.items()
            },
            "edges": [
                {
                    "source": u,
                    "target": v,
                    "edge_type": data.get("edge_type"),
                    "weight": float(data.get("weight", 0.0)),
                }
                for u, v, data in self.graph.edges(data=True)
            ],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Dict]) -> "BoostXGraph":
        graph = cls()
        nodes = []
        for node_id, node_data in payload.get("nodes", {}).items():
            nodes.append(
                GraphNode(
                    node_id=node_id,
                    layer=node_data["layer"],
                    embedding=np.asarray(node_data["embedding"], dtype=np.float32),
                    perplexity=node_data.get("perplexity"),
                    metadata=node_data.get("metadata", {}),
                )
            )
        graph.add_nodes(nodes)
        for edge in payload.get("edges", []):
            graph.add_edge(
                edge["source"],
                edge["target"],
                edge_type=edge["edge_type"],
                weight=float(edge["weight"]),
            )
        return graph

    # --------------------------------------------------------------- persistence
    def save(self, path: str | Path) -> None:
        """Write the graph JSON representation to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f)

    @classmethod
    def load(cls, path: str | Path) -> "BoostXGraph":
        with Path(path).open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return cls.from_dict(payload)

    # ----------------------------------------------------------- random walks
    def sample_walks(
        self,
        *,
        num_walks: int,
        walk_length: int,
        p: float,
        q: float,
        layer_switch_prob: float,
    ) -> List[List[str]]:
        """
        Sample dual-layer node2vec-style walks.  ``p`` and ``q`` control bias.

        The approximation treats ``p``/``q`` heuristically to avoid storing the
        full second-order matrix: ``p`` penalizes immediate backtracking while
        ``q`` scales cross-layer hops even further.
        """
        if not self.graph.nodes:
            return []
        walks: List[List[str]] = []
        node_ids = list(self.graph.nodes)
        for _ in range(num_walks):
            current = self.random.choice(node_ids)
            walk = [current]
            prev = None
            for _ in range(walk_length - 1):
                neighbors = list(self.graph.neighbors(current))
                if not neighbors:
                    break
                weights = []
                for neighbor in neighbors:
                    edge_data = self.graph.get_edge_data(current, neighbor)
                    weight = sum(float(data.get("weight", 1.0)) for data in edge_data.values())
                    if prev is not None and neighbor == prev:
                        weight /= max(p, 1e-3)
                    if self.graph.nodes[current].get("layer") != self.graph.nodes[neighbor].get("layer"):
                        weight *= layer_switch_prob
                    else:
                        weight /= max(q, 1e-3)
                    weights.append(weight)
                total = sum(weights) or 1.0
                probs = [w / total for w in weights]
                next_node = self.random.choices(neighbors, weights=probs, k=1)[0]
                walk.append(next_node)
                prev, current = current, next_node
            walks.append(walk)
        return walks
