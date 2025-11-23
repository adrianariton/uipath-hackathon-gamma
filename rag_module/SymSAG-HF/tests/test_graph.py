from __future__ import annotations

import numpy as np

from symsag_hf.graph import BoostXGraph, GraphNode, LAYER_EXPR, LAYER_TEXT


def make_node(idx: int, layer: str) -> GraphNode:
    return GraphNode(
        node_id=f"{layer}_{idx}",
        layer=layer,
        embedding=np.full((4,), idx + 1, dtype=np.float32),
        perplexity=1.0,
    )


def test_graph_knn_and_walks():
    graph = BoostXGraph(max_nodes=10)
    nodes = [make_node(i, LAYER_TEXT) for i in range(3)]
    nodes += [make_node(i, LAYER_EXPR) for i in range(3)]
    graph.add_nodes(nodes)
    graph.build_knn_edges(LAYER_TEXT, k=2, edge_type="TEXT_SIM")
    graph.build_knn_edges(LAYER_EXPR, k=2, edge_type="EXPR_SYN")
    graph.add_edge("expr_0", "text_0", edge_type="ANCHOR_OCCURS_IN", weight=1.0)

    assert graph.graph.number_of_edges() > 0
    walks = graph.sample_walks(num_walks=2, walk_length=4, p=1.0, q=1.0, layer_switch_prob=0.5)
    assert walks and all(len(walk) >= 1 for walk in walks)
