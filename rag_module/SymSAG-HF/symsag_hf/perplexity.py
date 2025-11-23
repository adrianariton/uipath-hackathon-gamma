"""
Perplexity scoring utilities.

The project measures *specificity* via perplexity for both language and
expressions.  We provide lightweight helpers that try to use GPT-2 by default
but gracefully degrade to a heuristic when the model is unavailable (e.g. in
offline CI environments).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class PerplexityResult:
    value: float
    tokens: int


class PerplexityScorer:
    """Compute perplexity for both text and expressions."""

    def __init__(
        self,
        *,
        text_model: str = "gpt2",
        expr_model: str = "gpt2",
        expr_structural_weight: float = 0.25,
        device: str = "cpu",
        use_lm: bool = True,
    ) -> None:
        self.text_model_name = text_model
        self.expr_model_name = expr_model
        self.expr_structural_weight = expr_structural_weight
        self.device = device
        self.use_lm = use_lm
        self._text_model = None
        self._text_tokenizer = None
        self._expr_model = None
        self._expr_tokenizer = None

    # -------------------------------------------------------------- public API
    def text_perplexity(self, text: str) -> PerplexityResult:
        return self._score(text, is_expression=False)

    def expression_perplexity(self, expr: str) -> PerplexityResult:
        base = self._score(expr, is_expression=True)
        structural = 1.0 + self.expr_structural_weight * _structural_complexity(expr)
        return PerplexityResult(value=base.value * structural, tokens=base.tokens)

    # ------------------------------------------------------------- internals
    def _score(self, payload: str, *, is_expression: bool) -> PerplexityResult:
        payload = payload.strip()
        if not payload:
            return PerplexityResult(value=1.0, tokens=0)
        tokenizer, model = self._get_model(is_expression=is_expression)
        if tokenizer is None or model is None:
            heuristic = math.exp(len(payload.split()) / 10.0)
            return PerplexityResult(value=float(heuristic), tokens=len(payload.split()))
        inputs = tokenizer(payload, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            loss = model(**inputs, labels=inputs["input_ids"]).loss
        ppl = math.exp(loss.item())
        return PerplexityResult(value=float(ppl), tokens=int(inputs["input_ids"].numel()))

    def _get_model(self, *, is_expression: bool):
        if not self.use_lm:
            return None, None
        if is_expression:
            if self._expr_model is None:
                self._expr_tokenizer, self._expr_model = _safe_load(self.expr_model_name, self.device)
            return self._expr_tokenizer, self._expr_model
        if self._text_model is None:
            self._text_tokenizer, self._text_model = _safe_load(self.text_model_name, self.device)
        return self._text_tokenizer, self._text_model


def _safe_load(model_name: str, device: str):
    """
    Attempt to load a causal LM.  Returns ``(tokenizer, model)`` or ``(None, None)``
    when weights are unavailable (e.g. offline execution).  This keeps unit tests
    fast while still enabling real perplexity scores when the environment allows.
    """
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        model.to(device)
        return tokenizer, model
    except Exception:
        return None, None


@lru_cache(maxsize=4096)
def _structural_complexity(expr: str) -> float:
    # Count operators, nesting depth, and unique symbols as a proxy.
    operators = re.findall(r"[+\-*/^=]", expr)
    depth = 0
    max_depth = 0
    for char in expr:
        if char in "([{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif char in ")]}":
            depth = max(depth - 1, 0)
    symbols = set(re.findall(r"[a-zA-Z]", expr))
    complexity = 0.1 * len(operators) + 0.2 * max_depth + 0.05 * len(symbols)
    return float(complexity)
