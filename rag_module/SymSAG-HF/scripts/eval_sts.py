#!/usr/bin/env python
"""
Evaluate SymSAG-HF on a semantic textual similarity (STS) benchmark.
"""

from __future__ import annotations

import argparse
from typing import List

import evaluate
import numpy as np
from datasets import load_dataset

from symsag_hf import SymSAGModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SymSAG-HF STS evaluation.")
    parser.add_argument("--model_dir", required=True, help="Path to a saved SymSAG-HF checkpoint.")
    parser.add_argument("--dataset", default="mteb/stsbenchmark-sts", help="HF dataset id with STS format.")
    parser.add_argument("--split", default="test")
    parser.add_argument("--max_samples", type=int, default=1000, help="Limit for fast experiments.")
    parser.add_argument("--batch_size", type=int, default=32, help="Encoder batch size.")
    return parser.parse_args()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return (a_norm * b_norm).sum(axis=1)


def main() -> None:
    args = parse_args()
    ds = load_dataset(args.dataset, split=args.split)
    if args.max_samples is not None:
        ds = ds.select(range(min(len(ds), args.max_samples)))

    sentences1: List[str] = [sample["sentence1"] for sample in ds]
    sentences2: List[str] = [sample["sentence2"] for sample in ds]
    scores = np.array([float(sample["score"]) for sample in ds], dtype=np.float32)

    model = SymSAGModel.from_pretrained(args.model_dir)
    encoder = model.get_text_encoder()
    emb1 = encoder.encode(sentences1, batch_size=args.batch_size)
    emb2 = encoder.encode(sentences2, batch_size=args.batch_size)

    pred = cosine_similarity(emb1, emb2)
    # Normalize cosine similarity to STS-style 0-5 scale
    pred_scaled = 2.5 * (pred + 1.0)

    metric = evaluate.load("spearmanr")
    result = metric.compute(predictions=pred_scaled.tolist(), references=scores.tolist())
    print(f"Spearman correlation: {result['spearmanr']:.4f} (n={len(sentences1)})")


if __name__ == "__main__":
    main()
