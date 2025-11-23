#!/usr/bin/env python
"""
Evaluate SymSAG-HF on QA datasets using HF ``evaluate`` metrics.
"""

from __future__ import annotations

import argparse
import argparse

import evaluate
from datasets import load_dataset

from symsag_hf import SymSAGModel, SymSAGRAGPipeline


def parse_args():
    parser = argparse.ArgumentParser(description="QA evaluation for SymSAG-HF.")
    parser.add_argument("--model_dir", required=True)
    parser.add_argument("--dataset", default="gsm8k")
    parser.add_argument(
        "--dataset_config",
        default="main",
        help="HF dataset config (e.g. gsm8k: main or socratic).",
    )
    parser.add_argument("--split", default="test")
    parser.add_argument("--max_samples", type=int, default=100)
    return parser.parse_args()


def normalize(text: str) -> str:
    return " ".join(str(text).strip().lower().split())


def main():
    args = parse_args()
    ds = load_dataset(args.dataset, args.dataset_config, split=args.split)
    metric = evaluate.load("accuracy")
    model = SymSAGModel.from_pretrained(args.model_dir)
    rag = SymSAGRAGPipeline(model)
    rag.index_graph()
    preds = []
    refs = []
    for idx, sample in enumerate(ds):
        query = sample.get("question") or sample.get("problem") or sample.get("text")
        if not query:
            continue
        res = rag.answer(query)
        pred = res["items"][0].text if res["items"] else ""
        gold = sample.get("answer") or sample.get("solution") or ""
        preds.append(int(normalize(pred) == normalize(gold)))
        refs.append(1)
        if idx + 1 >= args.max_samples:
            break
    score = metric.compute(predictions=preds, references=refs)
    print(f"Accuracy: {score['accuracy']:.4f}")


if __name__ == "__main__":
    main()
