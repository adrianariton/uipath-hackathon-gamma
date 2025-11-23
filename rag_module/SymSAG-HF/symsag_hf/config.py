"""
Configuration helpers for SymSAG-HF.

The configuration follows the Hugging Face ``PretrainedConfig`` contract so that
SymSAG-HF checkpoints can be shared via the Hub.  The dataclasses in this file
focus on *serializability* and *clarity* rather than raw performance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional

import yaml
from transformers import PretrainedConfig

DEFAULT_CONFIG = {
    "text_encoder": {
        "model_name": "sentence-transformers/all-mpnet-base-v2",
        "dim": 768,
        "normalize": True,
    },
    "expr_encoder": {
        "model_name": "gpt2",
        "dim": 768,
        "normalize": True,
    },
    "specificity": {
        "text_model": "gpt2",
        "expr_model": "gpt2",
        "expr_structural_weight": 0.25,
        "use_lm": True,
    },
    "graph": {
        "backend": "boostx",
        "max_nodes": 1_000_000,
        "knn_k": 64,
        "percentile": 95,
        "layer_switch_prob": 0.15,
        "storage_format": "csr",
        "seed": 42,
    },
    "walks": {
        "num_walks": 40,
        "walk_length": 120,
        "p": 0.75,
        "q": 1.5,
    },
    "data": {
        "text_dataset": "gsm8k",
        "text_dataset_config": "main",
        "expr_dataset": "math_dataset",
        "expr_dataset_config": None,
        "split_train": "train",
        "split_eval": "test",
        "max_samples": 50000,
    },
    "distill": {
        "teacher_model": "text-embedding-3-large",
        "loss": "mse+cos",
    },
    "eval": {
        "datasets": ["gsm8k", "math", "mmlu_pro_math", "gpqa_stem"],
        "metrics": ["exact_match", "accuracy", "recall_at_k"],
    },
    "rag": {
        "retriever": "faiss",
        "top_k": 5,
        "symbolic_verifier": "sympy",
    },
    "training": {
        "learning_rate": 2e-4,
        "weight_decay": 0.01,
        "num_epochs": 8,
        "batch_size": 64,
        "seed": 42,
        "gradient_accumulation_steps": 4,
        "mixed_precision": True,
    },
}


class SymSAGConfig(PretrainedConfig):
    """
    Hugging Face-compatible configuration for SymSAG-HF.

    Parameters mirror the project specification.  Nested dictionaries are kept
    flexible so that downstream users can extend them in configs without having
    to subclass ``PretrainedConfig``.
    """

    model_type = "symsag_hf"

    def __init__(self, **kwargs: Any) -> None:
        merged: Dict[str, Any] = _deep_update(DEFAULT_CONFIG.copy(), kwargs)
        super().__init__(**merged)

    # --------------------------------------------------------------------- I/O
    @classmethod
    def from_yaml(cls, path: str | Path) -> "SymSAGConfig":
        """Load a configuration from a YAML file."""
        with Path(path).expanduser().open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        """Persist the configuration as YAML alongside the regular HF JSON."""
        with Path(path).expanduser().open("w", encoding="utf-8") as f:
            yaml.safe_dump(self.to_dict(), f, sort_keys=False)


def _deep_update(target: MutableMapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """Recursively merge ``override`` into ``target``."""

    for key, value in override.items():
        if (
            key in target
            and isinstance(target[key], MutableMapping)
            and isinstance(value, Mapping)
        ):
            target[key] = _deep_update(dict(target[key]), value)
        else:
            target[key] = value
    return dict(target)
