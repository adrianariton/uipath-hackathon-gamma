# 🧠 SymSAG-HF — Symbolic Semantic-Augmented Graphs

### Purpose of this prompt

You are implementing **SymSAG-HF**, a dual-modality graph model that unifies *semantic* (textual) and *symbolic* (mathematical expression) representations under a single scalable architecture.
Your goal is to generate the full project structure, code, and documentation according to this specification.
The project must be implemented **as a Hugging Face-native model** (with `PreTrainedModel` / `PretrainedConfig`) while internally using a performant **graph backend (BoostX)** for graph construction and traversal.

---

## 1.  Overall Scope

### 1.1  Motivation

Modern language models encode semantic knowledge well but struggle to handle symbolic reasoning.
The **SAG (Semantic-Augmented Graph)** model proposed a hierarchy-based approach for structuring text by specificity.
**SymSAG-HF** generalizes this idea by merging two complementary subgraphs:

| Layer                         | Content                                           | Representation goal                         |
| ----------------------------- | ------------------------------------------------- | ------------------------------------------- |
| **Text layer (SAG)**          | natural-language sentences, paragraphs, or chunks | encode semantic hierarchy and similarity    |
| **Expression layer (SymSAG)** | mathematical or logical expressions               | encode syntactic and functional equivalence |

These layers are connected through **anchor edges**, allowing traversal between natural language and formal expressions.

### 1.2  High-Level Objectives

1. **Drop tree reduction** — preserve multiple paths for richer connectivity.
2. **BoostX graph backend** for scalable operations (up to 1 M nodes).
3. **Specificity via perplexity** instead of SMOG:

   * For text: GPT-2 perplexity per token.
   * For expressions: “math perplexity” (tokenized LaTeX or AST) blended with structural complexity.
4. **Percentile-based edge pruning** using streaming t-digest quantile estimation.
5. **Dual traversal (text ↔ expr)** with configurable layer-switch probability.
6. **Two-phase dataset split**:

   * Phase A = graph construction.
   * Phase B = jump-in / random walks for embedding learning.
7. **Pluggable embeddings** (any Hugging Face model or distilled variant).
8. **Hugging Face ecosystem integration**:

   * Datasets via `datasets` library.
   * Models via `transformers`.
   * Metrics via `evaluate`.
   * Configs + checkpoints compatible with Hub (`from_pretrained`, `save_pretrained`).
9. **Evaluation** on math reasoning benchmarks (GSM8K, GSM-Hard, MATH, MMLU-Pro Math, GPQA-STEM).
10. **RAG and QA pipelines** using graph-based retrieval + optional symbolic verification (SymPy/Z3).
11. **Modular, reproducible, and test-covered** design with YAML configs and HF-style scripts.

---

## 2.  Conceptual Design

### 2.1  Graph Schema

| Edge Type          | Source | Target | Meaning                                      |
| ------------------ | ------ | ------ | -------------------------------------------- |
| `TEXT_SIM`         | text   | text   | semantic similarity                          |
| `EXPR_SYN`         | expr   | expr   | syntactic (AST) similarity                   |
| `EXPR_FUN`         | expr   | expr   | functional equivalence (simplification / Z3) |
| `ANCHOR_OCCURS_IN` | expr   | text   | expression occurs in text chunk              |

Each node stores embeddings, perplexity, and optional metadata (tokens, symbols, AST features).
Edges carry similarity weights normalized to [0, 1].
All layers share the same BoostX backend with typed adjacency lists.

### 2.2  Dual Traversal

Random walks behave like **layered node2vec**:

* standard 2nd-order transition (p, q) inside a layer;
* with probability `layer_switch_prob`, follow an anchor to the opposite layer.
  This enables mixed semantic–symbolic contexts for embedding learning and retrieval.

---

## 3.  Hugging Face Integration

SymSAG-HF behaves like any HF model.

```python
from symsag_hf import SymSAGModel, SymSAGConfig

config = SymSAGConfig()
model  = SymSAGModel(config)
model.save_pretrained("carolluca/symsag-base")
```

### 3.1  `SymSAGConfig`

Extends `PretrainedConfig`.  Stores encoder names, graph parameters, walk options, etc.
Supports YAML serialization for reproducible runs.

### 3.2  `SymSAGModel`

Extends `PreTrainedModel`.
Internally contains:

* Hugging Face encoders (`AutoModel` / `AutoTokenizer`).
* BoostX graph instance (`BoostXGraph`).
* Node embeddings table after training.

Implements:

* `forward()` for embedding inference.
* `build_graph()` and `fuse_layers()` helpers.
* `save_pretrained()` / `from_pretrained()` for full checkpoint restore (including graph).

---

## 4.  Data & Dependencies

### 4.1  Datasets (via `datasets`)

Use HF datasets streaming API for large corpora.

| Name          | Task                      | HF ID                        |
| ------------- | ------------------------- | ---------------------------- |
| GSM8K         | math word problems        | `"gsm8k"`                    |
| GSM-Hard      | harder GSM8K variant      | `"gsm8k_hard"` *(community)* |
| MATH          | competition problems      | `"math_dataset"`             |
| MMLU-Pro Math | advanced math reasoning   | `"mmlu_pro_math"`            |
| GPQA-STEM     | graduate-level science QA | `"gpqa_stem"`                |

Example:

```python
from datasets import load_dataset
ds = load_dataset("gsm8k", split="train")
```

### 4.2  Embedding & LM Models

Default backbones (replaceable via config):

| Purpose            | Default Model                                | HF ID                                       |
| ------------------ | -------------------------------------------- | ------------------------------------------- |
| Text embeddings    | Sentence-Transformers MiniLM                 | `"sentence-transformers/all-MiniLM-L12-v2"` |
| Perplexity LM      | GPT-2                                        | `"gpt2"`                                    |
| Expression encoder | same as GPT-2 (textual) or structural hybrid | `"gpt2"`                                    |

### 4.3  Metrics (via `evaluate`)

```python
import evaluate
acc  = evaluate.load("accuracy")
em   = evaluate.load("exact_match")
```

---

## 5.  Architecture Components

### 5.1  Math Processing (`sympy` + `z3`)

* Parse LaTeX/AsciiMath → SymPy AST.
* Canonicalize (sorted symbols, expanded form).
* Define two equivalence scores:

  * *syntactic sim*: Jaccard of operator multisets + AST depth similarity.
  * *functional sim*: simplified equivalence (SymPy) ∨ model-checking (Z3).

### 5.2  Perplexity

Compute token-normalized perplexity with causal LM:
[
\text{pplx}(x)=\exp!\left(\tfrac{1}{N}\sum_i -\log p(x_i|x_{<i})\right)
]
Used inversely as specificity weight.

### 5.3  Graph Construction

1. Encode nodes (text + expr).
2. Approximate k-NN via ANN (Faiss).
3. Compute weights combining similarity & perplexity.
4. Prune edges using percentile threshold.
5. Store in CSR shards.

### 5.4  Walks & Training

* Weighted, biased walks (node2vec) implemented in BoostX C++ core.
* Embedding learning via SGNS or contrastive loss (PyTorch).
* Optional distillation from larger text-embedding models.

### 5.5  Retrieval + RAG + QA

* `jump_in.py`: given a query (text or expr) → ANN → expansion → context collection.
* `rag_pipeline.py`: feed context to small LM or symbolic solver; verify answers with SymPy/Z3.
* Evaluate EM/Acc/Recall@K.

---

## 6.  Project Structure

```
symsag_hf/
  pyproject.toml
  setup.py
  README.md
  scripts/
    train.py          # full pipeline (build + walks + train + save)
    eval_rag.py       # retrieval-augmented evaluation
    eval_qa.py        # plain QA
  symsag_hf/
    configuration_symsag.py
    model_symsag.py
    data/
      hf_datasets.py
      preprocess.py
    features/
      perplexity.py
      expr_features.py
      embeddings.py
    graph/
      backend_boostx.py
      schema.py
      build.py
      fuse.py
      walks.py
      threshold.py
    trainer/
      node2vec_trainer.py
      rag_trainer.py
    retrieval/
      jump_in.py
      rag_pipeline.py
    math/
      sympy_utils.py
      z3_utils.py
      equivalence.py
    utils/
      logging.py
      metrics.py
      io.py
  configs/
    default.yaml
    biggraph.yaml
  tests/
    test_model_io.py
    test_dataset_loading.py
```

---

## 7.  Simplified CLI Usage

### Training

```bash
python scripts/train.py --config configs/biggraph.yaml
```

Performs preprocessing → graph build → walks → embedding training → saves with `save_pretrained`.

### Retrieval-Augmented Evaluation

```bash
python scripts/eval_rag.py --model runs/symsag_hf/ --dataset gsm8k
```

### QA-Only Evaluation

```bash
python scripts/eval_qa.py --model runs/symsag_hf/ --dataset mmlu_pro_math
```

### Push / Load from Hub

```python
from symsag_hf import SymSAGModel
model = SymSAGModel.from_pretrained("carolluca/symsag-base")
model.push_to_hub("carolluca/symsag-base")
```

---

## 8.  Configuration Example (`configs/default.yaml`)

```yaml
data:
  text_dataset: "gsm8k"
  expr_extract: true
  split_train: "train"
  split_eval: "test"

embedding:
  text_encoder: "sentence-transformers/all-MiniLM-L12-v2"
  expr_encoder: "gpt2"
  dim: 384
  normalize: true

specificity:
  model: "gpt2"
  normalize: per_token
  expr:
    structural_weight: 0.25

graph:
  backend: "boostx"
  max_nodes: 1_000_000
  knn_k: 64
  percentile: 95
  layer_switch_prob: 0.15
  storage_format: "csr"

walks:
  num_walks: 10
  walk_length: 80
  p: 1.0
  q: 1.0

distill:
  teacher_model: "text-embedding-3-large"
  loss: "mse+cos"

eval:
  datasets: ["gsm8k","math","mmlu_pro_math","gpqa_stem"]
  metrics: ["exact_match","accuracy","recall_at_k"]
```

---

## 9.  Simplified Training Loop Pseudocode

```python
def train_symsag(config):
    # Load HF datasets
    train_ds = load_dataset(config["data"]["text_dataset"], split=config["data"]["split_train"])
    # Build graph
    graph = BoostXGraph()
    text_embs = encode_texts(train_ds)
    expr_embs = encode_exprs(train_ds)
    graph.build(text_embs, expr_embs)
    # Random walks
    walks = graph.sample_walks(num_walks=config["walks"]["num_walks"])
    # Train node2vec / distill
    trainer = Node2VecTrainer(model, walks)
    trainer.train()
    model.save_pretrained(config["output_dir"])
```

---

## 10.  Design Rationale & Trade-offs

| Choice                         | Reason                                                                       |
| ------------------------------ | ---------------------------------------------------------------------------- |
| **BoostX backend**             | scales better than NetworkX; C++ bindings; suitable for million-node graphs. |
| **Percentile pruning**         | adaptive threshold independent of dataset scale.                             |
| **Perplexity for specificity** | language-model measure of informational density; generalizes beyond SMOG.    |
| **Dual traversal**             | unifies semantic + symbolic reasoning; enables cross-layer embeddings.       |
| **Hugging Face integration**   | ensures reusability, community compatibility, easy deployment.               |
| **SymPy + Z3**                 | captures both algebraic and logical equivalence automatically.               |
| **Simplified scripts**         | easier onboarding; advanced control still possible.                          |
| **HF datasets & metrics**      | no manual downloads; standardized evaluation.                                |

---

## 11.  Performance Goals

| Component       | Target                      |
| --------------- | --------------------------- |
| Graph size      | ≤ 1 M nodes, ≤ 100 M edges  |
| Build time      | < 2 h on 64 GB RAM          |
| Memory          | Sharded CSR + disk spilling |
| Walk generation | 5–10× faster via BoostX     |
| Eval latency    | ≤ 300 ms / query (RAG)      |

---

## 12.  Testing & Validation

Unit tests for:

* dataset streaming (HF datasets)
* perplexity scorer
* canonicalization & equivalence (SymPy + Z3)
* percentile pruning correctness
* layered random-walk transitions
* model save/load parity (`from_pretrained` ↔ `save_pretrained`)
* RAG pipeline accuracy on small GSM8K subset

Acceptance criteria:

* reproducible results (fixed seed → same graph statistics)
* retrieval recall ≥ baseline SAG
* RAG accuracy ≥ baseline LLM on GSM8K subset
* graph build under memory constraints

---

## 13.  Deliverables

* Installable Python package `symsag_hf` (PyPI-ready).
* Full HF model checkpoint (`config.json`, `pytorch_model.bin`, `graph/`).
* Three scripts: `train.py`, `eval_rag.py`, `eval_qa.py`.
* Example notebooks for inference and graph inspection.
* README + docstring coverage ≥ 90%.
* Passing test suite (`pytest`).

---

## 14.  Instructions for the LLM

1. Implement this project **exactly** according to the above scope.
2. Follow **Hugging Face best practices** for model/config/trainer design.
3. Use **BoostX** for all graph operations.
4. Implement all text and expression logic **automatically** (expression detection, parsing, canonicalization).
5. Ensure that every component (datasets, metrics, encoders) loads via HF APIs.
6. Provide clean, modular, type-hinted, well-commented code.
7. Optimize for scalability, clarity, and reproducibility.

---

**End of SymSAG-HF Specification Prompt**
