# SymSAG-HF

SymSAG-HF (Symbolic Semantic-Augmented Graphs) is a dual-modality graph model
that merges semantic text chunks with symbolic expressions in a Hugging
Face-native package.  It implements the architecture described in `Plan.md`
including BoostX-style graph construction, percentile pruning, dual-layer random
walks, and RAG pipelines.

## Key Features

- **HF-native** `SymSAGConfig` / `SymSAGModel` with `save_pretrained` support.
- **Graph backend** implemented via a BoostX-compatible wrapper (NetworkX mock
  for local development) featuring typed edges, percentile pruning, and layered
  random walks.
- **Specificity via perplexity** using GPT-2 (with heuristic fallback for offline
  runs) for both text and expression layers.
- **Training flow** with dataset splits (Phase A/B), encoder-driven embeddings,
  walk generation, and a lightweight node2vec-style trainer.
- **RAG + QA scripts** leveraging the learned embeddings with optional symbolic
  verification through SymPy.

## Repository Layout

```
symsag_hf/
  config.py       # HF config helpers
  model.py        # SymSAGModel implementation
  graph.py        # BoostXGraph wrapper
  data.py         # Dataset + preprocessing utilities
  embeddings.py   # Hugging Face encoder wrappers
  perplexity.py   # Specificity scoring
  trainer.py      # Node2Vec-style smoothing trainer
  walks.py        # Random-walk helpers
  rag.py          # Retrieval pipeline
scripts/
  train.py        # Build graph + train
  eval_rag.py     # RAG evaluation
  eval_qa.py      # QA benchmark driver
Plan.md           # Project specification
README.md
pyproject.toml
```

## Quickstart

```bash
python scripts/train.py --output_dir outputs/demo --max_docs 64
python scripts/eval_sts.py --model_dir outputs/demo --dataset mteb/stsbenchmark-sts --split test --max_samples 200
python scripts/eval_qa.py --model_dir outputs/demo --dataset gsm8k --dataset_config main --split test --max_samples 10
```

The trainer consumes only a subset of documents by default.  Provide a YAML file
with overrides (see `Plan.md`) via `--config` to control encoders, graph
parameters, and walk options.

## Testing

Run unit tests with:

```bash
pytest
```

Tests cover dataset helpers, graph operations, and serialization to guarantee a
baseline of correctness.
