"""
Embedding utilities wrapping Hugging Face ``AutoModel`` stacks.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


class EmbeddingEncoder:
    """Thin wrapper above HF encoders with optional L2 normalization."""

    def __init__(
        self,
        model_name: str,
        *,
        normalize: bool = True,
        device: str = "cpu",
        max_length: int = 512,
    ) -> None:
        self.model_name = model_name
        self.normalize = normalize
        self.device = device
        self.max_length = max_length
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(device)
        if not self.tokenizer.pad_token:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def encode(self, texts: Sequence[str], *, batch_size: int = 16) -> np.ndarray:
        """Encode a list of texts into numpy embeddings."""
        outputs: List[np.ndarray] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            tokens = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(self.device)
            with torch.no_grad():
                hidden = self.model(**tokens).last_hidden_state
            mask = tokens.attention_mask.unsqueeze(-1)
            summed = (hidden * mask).sum(dim=1)
            denom = mask.sum(dim=1).clamp(min=1)
            pooled = summed / denom
            if self.normalize:
                pooled = torch.nn.functional.normalize(pooled, dim=1)
            outputs.append(pooled.cpu().numpy())
        if not outputs:
            return np.zeros((0, self.model.config.hidden_size), dtype=np.float32)
        return np.concatenate(outputs, axis=0)


def encode_iterable(encoder: EmbeddingEncoder, samples: Iterable[str], *, batch_size: int = 16) -> np.ndarray:
    """Convenience wrapper to encode a generator of strings."""
    texts = list(samples)
    if not texts:
        return np.empty((0, encoder.model.config.hidden_size), dtype=np.float32)
    return encoder.encode(texts, batch_size=batch_size)
