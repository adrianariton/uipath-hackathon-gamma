from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import faiss  # type: ignore
import numpy as np
from sentence_transformers import SentenceTransformer

from .config import (
    DEFAULT_CACHE_DIR,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_INDEX_PATH,
    DEFAULT_METADATA_PATH,
    DEFAULT_MODEL,
    DEFAULT_SOURCE_DIR,
    DEFAULT_TOP_K,
)


@dataclass
class RAGChunk:
    """Metadata for a text chunk stored in FAISS."""

    source: str
    chunk_id: int
    text: str
    token_start: int

    def to_json(self) -> str:
        return json.dumps(
            {
                "source": self.source,
                "chunk_id": self.chunk_id,
                "text": self.text,
                "token_start": self.token_start,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def from_json(line: str) -> "RAGChunk":
        data = json.loads(line)
        return RAGChunk(
            source=data["source"],
            chunk_id=int(data["chunk_id"]),
            text=data["text"],
            token_start=int(data.get("token_start", 0)),
        )


def chunk_text(text: str, chunk_size: int, overlap: int) -> Iterable[tuple[int, str]]:
    """Yield (token_start, chunk_text) pairs from a body of text."""
    tokens = text.split()
    if not tokens:
        return []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(tokens), step):
        window = tokens[start : start + chunk_size]
        yield start, " ".join(window)


class RAGPipeline:
    """Lightweight FAISS-backed retriever with HF sentence-transformer embeddings."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        index_path: Path | str = DEFAULT_INDEX_PATH,
        metadata_path: Path | str = DEFAULT_METADATA_PATH,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        auto_load_index: bool = True,
    ) -> None:
        self.model_name = model_name
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(self.cache_dir))

        self.model: SentenceTransformer | None = None
        self.index: faiss.Index | None = None
        self.metadata: list[RAGChunk] = []

        if auto_load_index:
            self._load_index_if_exists()
            self._load_metadata_if_exists()

    def _load_model(self) -> SentenceTransformer:
        if self.model is None:
            self.model = SentenceTransformer(self.model_name, cache_folder=str(self.cache_dir))
        return self.model

    def _load_index_if_exists(self) -> None:
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))

    def _load_metadata_if_exists(self) -> None:
        if self.metadata_path.exists():
            with self.metadata_path.open("r", encoding="utf-8") as f:
                self.metadata = [RAGChunk.from_json(line) for line in f if line.strip()]

    def reset(self) -> None:
        """Clear in-memory and on-disk index + metadata."""
        self.index = None
        self.metadata = []
        if self.index_path.exists():
            self.index_path.unlink()
        if self.metadata_path.exists():
            self.metadata_path.unlink()

    def _ensure_index(self, dimension: int) -> None:
        if self.index is None:
            self.index = faiss.IndexFlatIP(dimension)

    def _encode(self, texts: Sequence[str]) -> np.ndarray:
        model = self._load_model()
        embeddings = model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype=np.float32)

    def index_directory(
        self,
        source_dir: Path | str = DEFAULT_SOURCE_DIR,
        glob_pattern: str = "*.txt",
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
        reset: bool = True,
    ) -> int:
        """
        Ingest text files from a directory, chunk them, embed, and add to FAISS.

        Returns number of chunks indexed.
        """
        if reset:
            self.reset()

        src_path = Path(source_dir)
        files = sorted(src_path.rglob(glob_pattern))
        if not files:
            return 0

        chunks: list[str] = []
        chunk_meta: list[RAGChunk] = []

        for file_path in files:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for idx, (start, chunk) in enumerate(chunk_text(text, chunk_size, overlap)):
                if not chunk.strip():
                    continue
                chunk_meta.append(
                    RAGChunk(
                        source=str(file_path),
                        chunk_id=idx,
                        text=chunk,
                        token_start=start,
                    )
                )
                chunks.append(chunk)

        if not chunks:
            return 0

        embeddings = self._encode(chunks)
        self._ensure_index(embeddings.shape[1])
        assert self.index is not None  # for mypy
        self.index.add(embeddings)
        self.metadata.extend(chunk_meta)
        return len(chunks)

    def save(self) -> None:
        if self.index is None or self.index.ntotal == 0:
            raise ValueError("Nothing to save; index is empty.")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        with self.metadata_path.open("w", encoding="utf-8") as f:
            for meta in self.metadata:
                f.write(meta.to_json() + "\n")

    def query(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[dict]:
        if not query or not query.strip():
            raise ValueError("Query text is empty.")
        if self.index is None or self.index.ntotal == 0:
            raise FileNotFoundError("FAISS index not built yet. Run the indexer first.")
        embeddings = self._encode([query])
        assert self.index is not None  # for mypy
        scores, indices = self.index.search(embeddings, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            results.append(
                {
                    "score": float(score),
                    "source": meta.source,
                    "chunk_id": meta.chunk_id,
                    "text": meta.text,
                    "token_start": meta.token_start,
                }
            )
        return results

    def quick_context(self, query: str, top_k: int = DEFAULT_TOP_K) -> str:
        """Return a condensed string ready to be fed to an LLM or MCP tool."""
        results = self.query(query, top_k=top_k)
        if not results:
            return "No results found."
        lines = []
        for res in results:
            preview = res["text"][:500].replace("\n", " ")
            lines.append(
                f"[{res['score']:.3f}] {res['source']}#chunk-{res['chunk_id']} :: {preview}"
            )
        return "\n".join(lines)
