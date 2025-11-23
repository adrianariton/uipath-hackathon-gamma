"""
Random-walk utilities built on top of :mod:`symsag_hf.graph`.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

from .graph import BoostXGraph


def generate_walk_corpus(
    graph: BoostXGraph,
    *,
    num_walks: int,
    walk_length: int,
    p: float,
    q: float,
    layer_switch_prob: float,
) -> List[List[str]]:
    """Wrapper that forwards to ``BoostXGraph.sample_walks``."""
    return graph.sample_walks(
        num_walks=num_walks,
        walk_length=walk_length,
        p=p,
        q=q,
        layer_switch_prob=layer_switch_prob,
    )


def walks_to_sentences(walks: Sequence[Sequence[str]]) -> List[str]:
    """
    Convert node ID walks to whitespace-separated strings suitable for
    Word2Vec / Node2Vec training.
    """
    return [" ".join(map(str, walk)) for walk in walks if walk]
