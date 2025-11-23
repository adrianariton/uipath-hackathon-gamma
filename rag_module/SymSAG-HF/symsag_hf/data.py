"""
Data ingestion helpers for SymSAG-HF.

All dataset interactions go through the Hugging Face ``datasets`` library so
that we can take advantage of streaming.  The functions intentionally avoid
hard-coding dataset schemas; instead they rely on lightweight accessors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional

from datasets import Dataset, IterableDataset, load_dataset

EXPR_PATTERN = re.compile(r"(\$[^$]+\$|\\\[[^\]]+\\\]|\\\([^)]*\\\))")


@dataclass
class PhaseDatasets:
    """Two-phase split as required by the spec."""

    phase_a: Iterable[Dict[str, str]]
    phase_b: Iterable[Dict[str, str]]


def load_phase_datasets(config_dict: Dict, *, streaming: bool = True) -> PhaseDatasets:
    """
    Load datasets for Phase A (graph build) and Phase B (walk sampling).

    A typical workflow uses ``split_train`` for Phase A and ``split_eval`` for
    Phase B, but the function keeps things configurable.
    """
    data_cfg = config_dict.get("data", {})
    split_a = data_cfg.get("split_train", "train")
    split_b = data_cfg.get("split_eval", "validation")
    text_ds_name = data_cfg.get("text_dataset", "gsm8k")
    text_config = data_cfg.get("text_dataset_config")

    ds_a = load_dataset(text_ds_name, text_config, split=split_a, streaming=streaming)
    ds_b = load_dataset(text_ds_name, text_config, split=split_b, streaming=streaming)

    max_samples = data_cfg.get("max_samples")
    if max_samples is not None:
        ds_a = _take(ds_a, max_samples)
        ds_b = _take(ds_b, max_samples)

    return PhaseDatasets(phase_a=ds_a, phase_b=ds_b)


def detect_expressions(text: str) -> List[str]:
    """
    Extract inline expressions (LaTeX or parenthesized forms) from text.

    The pattern is intentionally broad because training corpora vary widely.
    """
    matches = EXPR_PATTERN.findall(text)
    return [match for match in matches if match.strip()]


def chunk_text(text: str, *, max_tokens: int = 128) -> List[str]:
    """
    Naive text chunker: split on sentences and merge until ``max_tokens`` words.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: List[str] = []
    current: List[str] = []
    token_count = 0
    for sentence in sentences:
        tokens = sentence.split()
        if not tokens:
            continue
        if token_count + len(tokens) > max_tokens and current:
            chunks.append(" ".join(current).strip())
            current = []
            token_count = 0
        current.extend(tokens)
        token_count += len(tokens)
    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def _take(dataset: Dataset | IterableDataset, limit: int) -> List[Dict]:
    """Return the first ``limit`` entries of a dataset."""
    iterator: Iterator[Dict] = iter(dataset)
    results: List[Dict] = []
    for _, row in zip(range(limit), iterator):
        results.append(row)
    return results
