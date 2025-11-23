from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2" # SymSAG-HF
DEFAULT_CACHE_DIR = BASE_DIR / "cache"
DEFAULT_INDEX_PATH = BASE_DIR / "index" / "faiss.index"
DEFAULT_METADATA_PATH = BASE_DIR / "index" / "metadata.jsonl"
DEFAULT_SOURCE_DIR = Path(__file__).resolve().parent.parent / "documents"
DEFAULT_CHUNK_SIZE = 480
DEFAULT_CHUNK_OVERLAP = 80
DEFAULT_TOP_K = 5
