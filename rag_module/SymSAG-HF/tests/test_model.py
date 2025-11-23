from __future__ import annotations

import numpy as np

from symsag_hf import SymSAGConfig, SymSAGModel
from symsag_hf.walks import generate_walk_corpus


class DummyEncoder:
    def __init__(self, dim: int):
        self.dim = dim

    def encode(self, texts, batch_size: int = 16):
        return np.vstack(
            [np.linspace(0, 1, self.dim, dtype=np.float32) + idx for idx, _ in enumerate(texts)]
        )


def test_model_build_graph_with_dummy_encoders():
    config = SymSAGConfig(
        text_encoder={"model_name": "dummy-text", "dim": 4},
        expr_encoder={"model_name": "dummy-expr", "dim": 4},
        specificity={"use_lm": False},
        graph={"knn_k": 1},
        walks={"num_walks": 2, "walk_length": 4},
    )
    model = SymSAGModel(config)
    model._text_encoder = DummyEncoder(dim=4)
    model._expr_encoder = DummyEncoder(dim=4)
    model.build_graph(["When x^2 + 1 = 0, solve for x using sqrt{-1}."])
    assert model.node_embeddings.numel() > 0
    walks = generate_walk_corpus(
        model.graph,
        num_walks=2,
        walk_length=4,
        p=1.0,
        q=1.0,
        layer_switch_prob=0.5,
    )
    assert walks
