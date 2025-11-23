#!/usr/bin/env python
"""
Training entry point for SymSAG-HF.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List

from symsag_hf import SymSAGConfig, SymSAGModel
from symsag_hf.data import load_phase_datasets
from symsag_hf.trainer import Node2VecTrainer
from symsag_hf.walks import generate_walk_corpus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train SymSAG-HF.")
    parser.add_argument("--config", type=str, help="Path to YAML config.", default=None)
    parser.add_argument("--output_dir", type=str, required=True, help="Checkpoint directory.")
    parser.add_argument("--max_docs", type=int, default=128, help="Number of documents for the demo run.")
    return parser.parse_args()


def extract_text(sample: Dict) -> str:
    for key in ("question", "text", "problem", "content"):
        if key in sample and sample[key]:
            return str(sample[key])
    return str(sample)


def main() -> None:
    args = parse_args()
    if args.config:
        config = SymSAGConfig.from_yaml(args.config)
    else:
        config = SymSAGConfig()
    config_dict = config.to_dict()
    phase = load_phase_datasets(config_dict, streaming=False)
    docs: List[str] = []
    for sample in phase.phase_a:
        docs.append(extract_text(sample))
        if len(docs) >= args.max_docs:
            break
    model = SymSAGModel(config)
    model.build_graph(docs)
    walk_cfg = config.walks
    walks = generate_walk_corpus(
        model.graph,
        num_walks=walk_cfg.get("num_walks", 10),
        walk_length=walk_cfg.get("walk_length", 80),
        p=walk_cfg.get("p", 1.0),
        q=walk_cfg.get("q", 1.0),
        layer_switch_prob=config.graph.get("layer_switch_prob", 0.15),
    )
    trainer = Node2VecTrainer(model, walks)
    trainer.train()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    config.to_yaml(Path(args.output_dir) / "config.yaml")


if __name__ == "__main__":
    main()
