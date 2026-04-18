# ML Lens

**ML Lens** is an agentic pipeline that ingests an ML paper, extracts a locked schema contract, then uses that schema to ground a traversal agent — producing a visual architecture breakdown that is verifiably faithful to what the paper actually specifies.

Built at the **Florent × Lund AI Society Hackathon** (April 18, 2026).

---

## The Problem

ML engineers implement attention mechanism papers daily. The standard workflow:

1. Read the paper (~2 hrs)
2. Understand the math (~2 hrs)
3. Ask Claude or GPT to implement it

Step 3 is where things break. LLMs confidently blend architectures — ask for Flash Attention 2 and you get components from three other papers. Tensor shapes are wrong. Components are invented. **70%+ of researchers fail to reproduce published results.**

The problem isn't code generation. It's hallucination caused by no grounding.

---

## The Solution

ML Lens introduces a **locked schema contract** extracted directly from the paper before any implementation happens. The schema — component manifest, tensor contracts, paper invariants — is verified and frozen. The traversal agent is then constrained to that schema. Any deviation is caught structurally, not after a cryptic CUDA error.

```
ArXiv URL
    │
    ▼
Ingestion Agent          ← PyMuPDF + arXiv LaTeX → Claude extraction
    │
    ▼
Schema Contract (locked) ← components · tensor shapes · invariants · paper quotes
    │
    ▼
Traversal Agent          ← schema-grounded graph walk · math engine · step trace
    │
    ▼
Visual Architecture      ← React Flow DAG · KaTeX equations · step-by-step replay
```

---

## Features

### Ingestion Pipeline
- Resolves arXiv URLs → downloads PDF + LaTeX source
- Extracts structured text and equations with PyMuPDF
- Claude-powered component extraction with JSON schema injection (eliminates field-name hallucination)
- 3-stage cache: metadata → parsed text → locked manifest

### Schema Contract
- **ComponentManifest**: every architectural component typed by kind (`multi_head_attention`, `feedforward`, `rmsnorm`, `layernorm`, `residual`, `softmax`, `masking`, `linear_projection`, `output_head`, …)
- **TensorContracts**: input/output shapes per component with symbolic dimensions (B, T, d_model, h, …)
- **Invariants**: paper-specific rules (residual connections, weight tying, causal masking, normalisation placement)
- **Symbol table**: every dimension variable defined
- Schema is **locked** with a content hash before the traversal agent runs — no post-hoc modification

### Traversal Agent
- Topological graph walk grounded to the locked schema
- Math engine computes parameter counts, FLOPs, and intermediate tensor shapes deterministically for all 10 component kinds
- Per-step trace: symbolic shapes → concrete shapes → equations → key insight
- Full trace replay in the UI

### Visualization
- Interactive React Flow DAG with per-kind colour coding
- Longest-path DAG layout, sequential fallback for isolated nodes
- Step scrubber: click any step or let it auto-animate at 1.2s/step
- KaTeX equation rendering for all LaTeX math
- Cards view: component manifest with tensor contracts and paper quotes side by side

### Hallucination Eval Framework
- Head-to-head comparison: bare Claude vs Claude + ML Lens skill context (locked manifest + trace)
- Same model, same paper text, same output contract — only the injected schema context differs
- Three automated test axes:
  - **Runnable**: `python generated.py` exits 0
  - **Shape correctness**: top-level module forward pass, output shape vs locked contract
  - **Drift**: AST-extracted `nn.Module` classes mapped to architectural buckets; missing + extra = drift errors
- ΔH (hallucination delta) reported per axis
- Target paper: [Differential Transformer](https://arxiv.org/abs/2410.05258) — focused attention variant, recent enough to expose real hallucination rates

---

## Architecture

```
ml-lens/
├── backend/
│   ├── ingestion/
│   │   ├── arxiv_resolver.py     # arXiv URL → PDF + metadata
│   │   ├── pdf_parser.py         # PyMuPDF + LaTeX source extraction
│   │   ├── component_extractor.py # Claude extraction + normalisation layer
│   │   ├── prompts.py            # JSON schema injected into system prompt
│   │   ├── pipeline.py           # 3-stage cached orchestrator
│   │   └── cache.py              # file-based cache at /tmp/ml-lens-cache/
│   ├── agent/
│   │   ├── traversal_agent.py    # schema-grounded agentic loop
│   │   ├── math_engine.py        # deterministic param/FLOP/shape engine
│   │   └── models.py             # TraversalStep, TraversalTrace
│   ├── schema/
│   │   ├── models.py             # ComponentManifest, TensorContract, Invariant
│   │   ├── lock.py               # content-hash locking
│   │   └── validator.py          # JSON schema export
│   └── main.py                   # FastAPI app
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── PaperIngest.jsx       # arXiv input → full pipeline flow
│       │   ├── ArchitectureFlow.jsx  # React Flow DAG
│       │   ├── SchemaReview.jsx      # schema review + traversal replay
│       │   ├── SchemaContractCard.jsx # component cards with equations
│       │   └── Math.jsx              # KaTeX renderer
│       └── App.jsx
└── evals/
    ├── baseline.py          # bare Claude → PyTorch
    ├── runner.py            # Claude + manifest + trace → PyTorch
    ├── common.py            # shared client, artifact helpers
    ├── run_eval.py          # orchestrator
    ├── report.py            # REPORT.md generator
    ├── tests/
    │   ├── test_runnable.py
    │   ├── test_shapes.py
    │   └── test_drift.py
    └── fixtures/
        ├── 2410.05258.json        # Differential Transformer locked manifest
        └── ground_truth_spec.json # test config + architectural buckets
```

---

## Quickstart

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY (OpenRouter key)
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Run a paper

1. Open `http://localhost:5173`
2. Paste an arXiv URL (e.g. `https://arxiv.org/abs/1706.03762`)
3. Click **Analyse** — ingestion runs, manifest is extracted and locked
4. Switch to **Flow** view to see the architecture DAG
5. Click **▶ Run Traversal** — the agent walks the graph step by step
6. Click any node or step to inspect tensor shapes, equations, and key insights

### Run the eval

```bash
cd evals
# set ANTHROPIC_API_KEY (OpenRouter) in backend/.env
../backend/.venv/bin/python run_eval.py
# generates evals/REPORT.md with baseline vs ML Lens side-by-side
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | OpenRouter key (`sk-or-v1-…`) used for extraction and traversal |
| `OPENROUTER_MODEL` | No | Model override for ingestion (default: `minimax/minimax-m2.7`) |
| `EVAL_MODEL` | No | Model override for eval (default: `minimax/minimax-m2.7`) |

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/ingest` | `{"url_or_id": "1706.03762"}` → `LockedManifest` |
| `POST` | `/api/traverse` | `ComponentManifest` → `TraversalTrace` |
| `GET` | `/api/schema` | JSON Schema for ComponentManifest |
| `GET` | `/api/schema/sample` | Sample locked manifest (Attention Is All You Need) |
| `GET` | `/health` | Health check |

---

## Key Design Decisions

**Schema injection into the system prompt.** The JSON Schema for `ComponentManifest` is embedded verbatim in the extraction system prompt. This eliminates the field-name hallucination problem (LLMs inventing `kind: "attention_layer"` instead of the valid enum value) without requiring a normalisation layer for every possible variant.

**Deterministic math engine.** Parameter counts, FLOPs, and intermediate tensor shapes are computed by a Python function per component kind — not by the LLM. This means the traversal trace is reproducible and auditable.

**Sequential fallback in the layout.** The React Flow DAG uses a longest-path level assignment for components with explicit `depends_on` edges. Components with no declared dependencies get a sequential fallback edge to the previous component, ensuring the graph always renders as a connected flow even for loosely-specified manifests.

**Eval fairness.** Both baseline and ML Lens conditions use the same model, temperature, paper text, and output contract. The only variable is the injected `<manifest>` + `<traversal_trace>` context. Both prompts are saved verbatim in `evals/artifacts/` for reproduction.

---

## Built With

| Layer | Tool |
|---|---|
| PDF parsing | PyMuPDF + arXiv LaTeX source |
| LLM extraction | OpenRouter (minimax/minimax-m2.7) |
| Schema validation | Pydantic v2 |
| API | FastAPI |
| Architecture graph | React Flow (@xyflow/react) |
| Math rendering | KaTeX |
| Eval testing | pytest + subprocess |

---

## Team

Built by Saksham Grover + Chamalka Muwangala at the Florent × Lund AI Society Hackathon, April 18 2026.

Sponsored by Anthropic, Voyado, Specific (YC F25), Atech, and Librar Labs (YC W26).
