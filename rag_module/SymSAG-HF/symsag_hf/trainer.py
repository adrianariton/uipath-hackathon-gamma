"""
Lightweight trainer utilities (heuristic node2vec approximation).
"""

from __future__ import annotations

import torch


class Node2VecTrainer:
    """
    Simplified trainer that smooths node embeddings using walk contexts.

    A production system would plug in a full node2vec implementation.  Here we
    implement an inexpensive heuristic that averages neighborhood embeddings
    gathered from random walks, which keeps tests deterministic and avoids large
    dependencies.
    """

    def __init__(self, model, walks, *, window_size: int = 5):
        self.model = model
        self.walks = walks
        self.window_size = window_size

    def train(self) -> None:
        if not self.walks or self.model.node_embeddings.numel() == 0:
            return
        device = self.model.node_embeddings.device
        accum = torch.zeros_like(self.model.node_embeddings)
        counts = torch.zeros(len(self.model.node_index), dtype=torch.float32, device=device)
        for walk in self.walks:
            for idx, node_id in enumerate(walk):
                node_idx = self.model.node_index.get(node_id)
                if node_idx is None:
                    continue
                start = max(0, idx - self.window_size)
                end = min(len(walk), idx + self.window_size + 1)
                context = [
                    self.model.node_index.get(walk[i])
                    for i in range(start, end)
                    if i != idx and self.model.node_index.get(walk[i]) is not None
                ]
                if not context:
                    continue
                context_emb = self.model.node_embeddings[context].mean(dim=0)
                accum[node_idx] += context_emb
                counts[node_idx] += 1
        counts = counts.clamp(min=1).unsqueeze(1)
        smoothed = accum / counts
        self.model.node_embeddings = torch.nn.Parameter(smoothed, requires_grad=False)
