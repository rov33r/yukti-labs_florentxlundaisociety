# ML Lens

> **Schema-grounded paper understanding for ML engineers.**
> Ingest any arXiv paper, lock a verified architecture contract, and traverse it step-by-step — with tensor shapes, equations, and parameter counts that are faithful to what the paper actually specifies.

---

## The Problem

Every week, hundreds of new ML papers drop proposing novel attention mechanisms, normalisation schemes, and training objectives. For an ML engineer, the workflow is always the same:

1. Read the paper *(~2 hours)*
2. Understand the math *(~2 hours)*
3. Ask Claude or GPT to implement it *(confident, fast, and frequently wrong)*

**The problem is step 3.** Large language models hallucinate implementations by blending architectures from their training data. Ask for Differential Attention and you get vanilla multi-head attention with a lambda variable bolted on. The Q/K split is wrong. The head-wise RMSNorm is missing. The tensor shapes are off by a factor of `h`. You only find out after a cryptic CUDA error two days in.

This is not a prompting problem. It is a **grounding problem.**

Without a verified contract anchoring the LLM to what the paper says, the model fills gaps from memory — and for any paper published in the last six months, that memory is noise.

> *70%+ of ML researchers fail to reproduce published results. The leading cause is not bad code — it is undocumented implementation decisions that deviate silently from the paper.*

---

## The Insight

Before any implementation happens, extract a **locked schema contract** directly from the paper. Every component, every tensor shape, every invariant — tied to the exact paper quote it was extracted from. Then constrain everything downstream to that contract.

The schema is not a prompt. It is a typed, hash-locked, machine-readable specification that the traversal agent cannot deviate from. Violations are caught structurally, not at runtime.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  1. INGESTION                                                    │
│                                                                  │
│  arXiv URL ──► PyMuPDF + LaTeX source ──► LLM extraction        │
│                                           (schema-injected)      │
│                                                   │              │
│                                                   ▼              │
│                               ComponentManifest (raw JSON)       │
└───────────────────────────────────────────────────┬─────────────┘
                                                    │
┌───────────────────────────────────────────────────▼─────────────┐
│  2. SCHEMA CONTRACT (the key layer)                              │
│                                                                  │
│  ┌──────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ Component        │  │ Tensor          │  │ Invariants     │  │
│  │ Manifest         │  │ Contracts       │  │                │  │
│  │                  │  │                 │  │ weight tying   │  │
│  │ id, name, kind   │  │ I/O shapes per  │  │ causal masking │  │
│  │ equations        │  │ component with  │  │ residuals      │  │
│  │ depends_on       │  │ symbolic dims   │  │ norm placement │  │
│  │ hyperparameters  │  │ (B, T, d, h…)   │  │                │  │
│  └──────────────────┘  └─────────────────┘  └────────────────┘  │
│                                                                  │
│  ── content-hash locked ──────────────────────────────────────── │
└───────────────────────────────────────────────────┬─────────────┘
                                                    │
┌───────────────────────────────────────────────────▼─────────────┐
│  3. TRAVERSAL AGENT                                              │
│                                                                  │
│  Topological graph walk · deterministic math engine              │
│  Per-step: symbolic shapes → concrete → equations → insight      │
│  Full trace saved for replay                                     │
└───────────────────────────────────────────────────┬─────────────┘
                                                    │
┌───────────────────────────────────────────────────▼─────────────┐
│  4. VISUALIZATION + EXPORT                                       │
│                                                                  │
│  React Flow DAG · KaTeX equations · step scrubber                │
│  Skill export: locked manifest + trace → portable context bundle │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technical Architecture

### Ingestion Pipeline

The ingestion pipeline runs in three cached stages:

| Stage | Input | Output | Cache key |
|---|---|---|---|
| Metadata | arXiv URL / ID | Paper title, authors, PDF URL | arxiv ID |
| Parsing | PDF bytes | Structured text + LaTeX equations | arxiv ID |
| Extraction | Paper text + equations | Locked `ComponentManifest` | SHA-256 of prompt + text |

**Parsing** uses PyMuPDF for PDF text extraction and fetches the arXiv LaTeX source tarball directly — preserving original equation notation rather than relying on PDF-rendered math. Equations are extracted via LaTeX environment regex (`equation`, `align`, `gather`) and inline math patterns.

**Extraction** uses a reasoning LLM (via OpenRouter) with the full `ComponentManifest` JSON Schema embedded verbatim in the system prompt. This is the key reliability mechanism: rather than asking the model to infer the output structure, we hand it the exact Pydantic schema and require strict conformance. A normalisation layer handles the remaining edge cases (quote coercion, invariant ID generation, LaTeX escape repair).

### Schema Contract

The `ComponentManifest` is a Pydantic v2 model with a content-hash lock:

```python
class ComponentManifest(BaseModel):
    paper: PaperMetadata
    components: list[Component]          # typed by ComponentKind enum
    tensor_contracts: list[TensorContract]  # input/output shapes per component
    invariants: list[Invariant]          # paper-specific structural rules
    symbol_table: dict[str, str]         # every dimension variable defined
    notes: Optional[str]
    locked: bool

class TensorContract(BaseModel):
    component_id: str
    input_shapes: dict[str, list[str]]   # e.g. {"Q": ["B", "T", "d_model"]}
    output_shapes: dict[str, list[str]]
    dtype: Optional[str]

class Invariant(BaseModel):
    id: str
    description: str
    kind: InvariantKind                  # weight_tying | causal_mask | residual_connection | …
    affected_components: list[str]
```

`ComponentKind` is a strict enum: `input_embedding`, `positional_encoding`, `multi_head_attention`, `attention`, `feedforward`, `layernorm`, `rmsnorm`, `residual`, `softmax`, `masking`, `linear_projection`, `output_head`, `other`. The LLM cannot invent kinds outside this set.

Locking computes `SHA-256(json.dumps(manifest, sort_keys=True))` and stamps a timestamp. The locked manifest is the only input the traversal agent accepts.

### Traversal Agent

The traversal agent walks the component graph in topological order (longest-path level assignment, sequential fallback for isolated nodes). For each component:

1. **Math engine** computes deterministically:
   - Parameter count (weights + biases per component kind)
   - FLOPs approximation (matrix multiply dominant cost)
   - Intermediate tensor names, symbolic shapes, and LaTeX equations
   - Concrete shapes given the manifest's hyperparameters

2. **LLM insight call** (optional, skippable via `TRAVERSAL_DEMO_MODE`) produces a one-sentence key insight per component

3. **TraversalStep** is recorded: input/output symbolic + concrete shapes, equations applied, intermediates, parameter count, FLOPs

The math engine covers all 10 component kinds with dedicated functions — no component falls through to a passthrough. Parameter counts and shapes are computed from manifest hyperparameters, not estimated.

### Visualization

The frontend is a React + Vite app using `@xyflow/react` for the DAG and KaTeX for equation rendering.

**Layout algorithm:** longest-path level assignment on the `depends_on` DAG. Nodes at the same level are centred horizontally. Explicit `depends_on` edges render as solid teal arrows; sequential fallback edges render as dashed grey. Node width is fixed at 210px; height is auto to prevent content truncation.

**Traversal replay:** the trace is auto-stepped at 1.2s/step with a manual scrubber. Active nodes get a coloured glow matching their component kind. Shape row updates on the active node: `[B, T, d_model] → [B, T, d_model]` in monospace.

**Cards view:** each component rendered as a card with kind badge, equations (KaTeX), tensor contract (input → output shape tags), invariant links, and the paper quote the data was extracted from.

### Hyperparameter Diff (Sandbox)

The sandbox layer extends the pipeline with a hyperparameter diff agent:

- `POST /diff/` accepts a locked manifest, base params, and a list of `HyperparamDelta`
- Generates and executes PyTorch forward-pass scripts for both base and modified configs via E2B sandboxed execution
- A diff agent (Claude) compares the two `TraversalTrace` outputs and produces a `SchemaDiff`: per-component shape changes, parameter deltas, invariant status, and implementation notes

### Hallucination Eval Framework

The eval framework measures whether ML Lens's schema context reduces hallucination when asking an LLM to implement a paper.

**Two conditions, one variable:**

| | Baseline | ML Lens |
|---|---|---|
| Model | `minimax/minimax-m2.7` | `minimax/minimax-m2.7` |
| Paper text | Full PyMuPDF extraction | Full PyMuPDF extraction |
| Output contract | Single PyTorch file | Single PyTorch file |
| Extra context | — | `<manifest>` + `<traversal_trace>` JSON |

**Three automated test axes:**

| Axis | Method | What it measures |
|---|---|---|
| **Runnable** | `subprocess.run(generated.py)`, exit 0 | Does the file execute at all |
| **Shape** | Import, instantiate top-level class, run forward pass | Is `output.shape == (B, T, vocab_size)` |
| **Drift** | AST-extract `nn.Module` subclasses, map to architectural buckets | Missing + extra components vs the locked manifest |

**ΔH (hallucination delta)** = `(baseline_errors − mllens_errors) / baseline_errors × 100%` per axis.

Target paper: [Differential Transformer (2410.05258)](https://arxiv.org/abs/2410.05258) — a focused attention variant (`softmax(Q1,K1) − λ·softmax(Q2,K2)`) published October 2024, chosen because baseline LLMs are likely to collapse it to standard MHA.

---

## Project Structure

```
ml-lens/
├── backend/
│   ├── ingestion/
│   │   ├── arxiv_resolver.py      # arXiv ID → metadata + PDF URL
│   │   ├── pdf_parser.py          # PyMuPDF + LaTeX tarball extraction
│   │   ├── component_extractor.py # LLM extraction + normalisation
│   │   ├── prompts.py             # JSON Schema injected into system prompt
│   │   ├── pipeline.py            # 3-stage cached orchestrator
│   │   └── cache.py               # /tmp/ml-lens-cache/{arxiv_id}/
│   ├── agent/
│   │   ├── traversal_agent.py     # topological walk, per-component trace
│   │   ├── math_engine.py         # deterministic params/FLOPs/shapes
│   │   └── models.py              # TraversalStep, TraversalTrace
│   ├── schema/
│   │   ├── models.py              # ComponentManifest + all Pydantic models
│   │   ├── lock.py                # SHA-256 content-hash locking
│   │   └── validator.py           # JSON Schema export for frontend
│   ├── sandbox/
│   │   ├── executor.py            # E2B sandbox runner
│   │   ├── trace_emitter.py       # generates PyTorch forward-pass scripts
│   │   └── result_parser.py       # E2B stdout → TraversalTrace
│   ├── routers/
│   │   ├── diff.py                # POST /diff/ — hyperparameter diff agent
│   │   └── test.py                # GET /test/diff-demo — interactive demo page
│   └── main.py                    # FastAPI app, CORS, route registration
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Sandbox.jsx            # React Flow DAG + hyperparameter controls
│       │   ├── ArchitectureFlow.jsx   # ingest-driven architecture graph
│       │   ├── SchemaReview.jsx       # schema review + traversal replay
│       │   ├── SchemaContractCard.jsx # component card with equations + quotes
│       │   ├── NodeInfoPopup.jsx      # click-on-node detail panel
│       │   ├── TraversalPanel.jsx     # step trace + shape flow
│       │   └── DiffPanel.jsx          # hyperparameter diff visualisation
│       ├── store/diffStore.js         # Zustand diff state
│       └── api/client.js             # typed fetch wrappers
├── evals/
│   ├── baseline.py                # bare LLM → PyTorch (no schema context)
│   ├── runner.py                  # LLM + manifest + trace → PyTorch
│   ├── common.py                  # shared client, artifact helpers
│   ├── run_eval.py                # orchestrator: generate + test + report
│   ├── report.py                  # markdown ΔH report generator
│   ├── tests/
│   │   ├── test_runnable.py       # subprocess exit-code check
│   │   ├── test_shapes.py         # forward pass shape verification
│   │   └── test_drift.py          # AST-based architectural bucket coverage
│   └── fixtures/
│       ├── 2410.05258.json        # Differential Transformer locked manifest
│       └── ground_truth_spec.json # test config, expected buckets, invariants
└── shared/
    ├── schema.json                # Pydantic-generated JSON Schema (single source of truth)
    └── schema.ts                  # TypeScript types derived from schema.json
```

---

## Quickstart

### Requirements

- Python 3.12+
- Node.js 18+
- An [OpenRouter](https://openrouter.ai) API key

### Backend

```bash
cd ml-lens/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Create .env with your OpenRouter key
echo "ANTHROPIC_API_KEY=sk-or-v1-..." > .env

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd ml-lens/frontend
npm install
npm run dev
# → http://localhost:5173
```

### Analyse a paper

1. Open `http://localhost:5173`
2. Paste an arXiv URL — e.g. `https://arxiv.org/abs/2410.05258`
3. Hit **Analyse** — ingestion runs, manifest is extracted and locked
4. Switch to **Flow** to see the architecture DAG
5. Click **▶ Run Traversal** — agent walks the graph step by step
6. Click any node or step to see tensor shapes, equations, and key insights

### Run the hallucination eval

```bash
cd ml-lens/evals
../backend/.venv/bin/python run_eval.py
# → evals/REPORT.md  (baseline vs ML Lens, per-axis ΔH)
```

To reuse existing generated code and only re-run tests:

```bash
../backend/.venv/bin/python run_eval.py --skip-gen
```

---

## API Reference

| Method | Endpoint | Body | Response |
|---|---|---|---|
| `POST` | `/api/ingest` | `{"url_or_id": "2410.05258"}` | `LockedManifest` |
| `POST` | `/api/traverse` | `ComponentManifest` | `TraversalTrace` |
| `POST` | `/diff/` | `{manifest, base_params, deltas}` | `{baseline_trace, modified_trace, schema_diff}` |
| `GET` | `/api/schema` | — | JSON Schema for `ComponentManifest` |
| `GET` | `/api/schema/sample` | — | Sample locked manifest |
| `GET` | `/health` | — | `{"status": "healthy"}` |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | OpenRouter key (`sk-or-v1-…`) |
| `OPENROUTER_MODEL` | No | `minimax/minimax-m2.7` | Model for ingestion extraction |
| `EVAL_MODEL` | No | `minimax/minimax-m2.7` | Model for eval conditions |
| `TRAVERSAL_DEMO_MODE` | No | `false` | Skip LLM insight calls for instant traversal |
| `DISABLE_SSL_VERIFY` | No | `false` | Disable SSL verification (dev only) |

---

## Built With

| Layer | Tool | Why |
|---|---|---|
| PDF parsing | PyMuPDF + arXiv LaTeX | Preserves original equation notation |
| LLM routing | OpenRouter | Model-agnostic; same key for ingestion and eval |
| Schema validation | Pydantic v2 | Typed contracts, JSON Schema export, hash locking |
| API | FastAPI | Async, typed, minimal |
| Architecture graph | @xyflow/react | Purpose-built for node graphs, custom nodes |
| Math rendering | KaTeX | Fast, lightweight, no MathJax overhead |
| Sandboxed execution | E2B | Sub-second boot, PyTorch pre-installed |
| State management | Zustand | Minimal; holds diff state and trace replay index |

---

## Team

**Saksham Grover + Chamalka Muwangala**

Built at the Florent × Lund AI Society Hackathon — *Build Your Next Startup* — April 18, 2026.

Sponsored by Anthropic · Voyado · Specific (YC F25) · Atech · Librar Labs (YC W26)
