# Yukti

**Understand any ML paper, component by component.**

Yukti reads an arXiv paper, extracts every architectural decision into a verified schema, and gives you three ways to explore it: an interactive component graph, schema-grounded PyTorch code, and a chat interface that only knows what the paper actually says.

Built at the Florent x Lund AI Society Hackathon, April 2026.
**Team:** Saksham Grover + Chamalka Muwangala

---

## The problem

ML papers are dense. When a new architecture drops, the workflow for most engineers looks like this:

1. Read the paper (a few hours)
2. Understand the math (a few more hours)
3. Ask an LLM to implement it (fast, confident, and frequently wrong)

Step 3 is the problem. LLMs hallucinate implementations by blending architectures from their training data. Ask for Differential Attention and you get vanilla multi-head attention with a lambda variable bolted on. The Q/K split is wrong. The head-wise RMSNorm is missing. The tensor shapes are off. You find out two days later with a cryptic CUDA error.

This is not a prompting problem. It is a grounding problem. Without a verified contract anchoring the model to what the paper actually says, it fills gaps from memory, and for any paper published recently, that memory is noise.

---

## What Yukti does

Paste an arXiv ID. Yukti reads the PDF and LaTeX source, identifies every architectural component, and locks them into a content-hashed manifest. That manifest is the source of truth for everything that follows.

**Architecture DAG.** Every component in the paper rendered as a live, interactive graph. Click any node to see its equations (rendered with KaTeX), tensor shapes, invariants, and the exact paper quote it was extracted from.

**Schema-grounded code.** PyTorch generated from the locked manifest, not from the LLM's training memory. Components, shapes, and wiring all match the paper. Not hallucinated.

**Ask Yukti.** A chat interface grounded strictly in the schema. Ask what the FFN does, why a specific design choice was made, or how data flows through the network. Every answer is bounded by what the paper specifies. Math renders inline with LaTeX.

**Forward pass trace.** A step-by-step simulation of the forward pass using symbolic tensor shapes (B, T, D). Shows how data transforms through each component, with parameter counts and FLOPs approximations per step.

**Eval results.** A head-to-head comparison of baseline code generation (no context) versus schema-grounded generation (manifest injected). The hallucination delta (dH) is the headline metric.

---

## Results

We evaluated on two published papers. Same model, same prompt, same paper text. The only difference was whether the schema was injected.

### Differential Transformer (2410.05258)

| Metric | Without Yukti | With Yukti |
|---|---|---|
| Code runs | No | Yes |
| Shape correct | No | Yes |
| Drift errors | 4 | 1 |
| Architecture sections covered | 2 / 5 | 5 / 5 |

### Grouped-Query Attention (2305.13245)

| Metric | Without Yukti | With Yukti |
|---|---|---|
| Code runs | No | Yes |
| Shape correct | No | Yes |
| Drift errors | 5 | 4 |
| Architecture sections covered | 2 / 5 | 5 / 5 |

The schema is the difference between code that crashes and code that runs.

---

## Getting started

### Requirements

- Python 3.12+
- Node.js 18+
- An [OpenRouter](https://openrouter.ai) API key (free tier works)

### 1. Clone the repo

```bash
git clone https://github.com/rov33r/yukti-labs_florentxlundaisociety.git
cd yukti-labs_florentxlundaisociety/ml-lens
```

### 2. Set up the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
ANTHROPIC_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_FALLBACK_MODEL=qwen/qwen3-coder:free
TRAVERSAL_DEMO_MODE=true
```

> Both `OPENROUTER_API_KEY` and `ANTHROPIC_API_KEY` should be set to your OpenRouter key. Some internal modules reference each name. `TRAVERSAL_DEMO_MODE=true` skips LLM calls in the traversal agent for faster local development.

Start the backend:

```bash
uvicorn main:app --reload --port 8000
```

### 3. Set up the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### 4. Analyse a paper

1. Paste an arXiv ID into the input field, for example `2410.05258`
2. Click **Research paper** and wait for ingestion to complete (30 to 90 seconds depending on the model)
3. You land in **Schema Review**, showing the locked manifest as an interactive DAG
4. Click **Explore in Sandbox** to switch between the graph, code, and trace views
5. Open the chat panel on the right to ask questions about the architecture
6. Click **Eval Results** in the header to see the hallucination comparison

To skip straight to a preloaded example, click **or open sandbox directly** on the landing page.

---

## Running the eval

The eval framework generates PyTorch implementations under two conditions (baseline and schema-grounded), then scores them on three automated axes: runnability, shape correctness, and architectural drift.

```bash
cd evals

# Generate code and run all tests
../backend/.venv/bin/python runner.py
../backend/.venv/bin/python run_eval.py

# Skip code generation and reuse existing artifacts
../backend/.venv/bin/python run_eval.py --skip-gen
```

Results are written to `evals/artifacts/{arxiv_id}/REPORT.md` and served live from the Eval Results page in the app.

---

## Project structure

```
ml-lens/
├── backend/
│   ├── ingestion/
│   │   ├── arxiv_resolver.py       arXiv ID to metadata and PDF URL
│   │   ├── pdf_parser.py           PyMuPDF + LaTeX source extraction
│   │   ├── component_extractor.py  LLM extraction and manifest normalisation
│   │   ├── prompts.py              JSON Schema embedded in system prompt
│   │   ├── pipeline.py             Three-stage cached orchestrator
│   │   └── cache.py                /tmp/ml-lens-cache/{arxiv_id}/
│   ├── agent/
│   │   ├── traversal_agent.py      Topological graph walk, per-component trace
│   │   ├── math_engine.py          Deterministic params, FLOPs, and shapes
│   │   └── models.py               TraversalStep, TraversalTrace
│   ├── schema/
│   │   ├── models.py               ComponentManifest and all Pydantic models
│   │   ├── lock.py                 SHA-256 content-hash locking
│   │   └── validator.py            JSON Schema export
│   ├── llm.py                      Centralised LLM client, primary + fallback routing
│   └── main.py                     FastAPI app, all routes
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── LandingPage.jsx     Hero, how-it-works steps, feature previews, proof strip
│       │   ├── SchemaReview.jsx    Locked manifest as DAG or card view, traversal replay
│       │   ├── Sandbox.jsx         Three-view explorer (model, code, trace)
│       │   ├── ArchitectureFlow.jsx React Flow DAG with kind-coloured nodes
│       │   ├── TraceView.jsx       Forward pass step-by-step with tensor shapes
│       │   ├── CodeSandbox.jsx     Schema-grounded PyTorch code generation
│       │   ├── ChatPanel.jsx       Ask Yukti, schema-grounded chat with LaTeX rendering
│       │   ├── NodeInfoPopup.jsx   Click-on-node panel with equations and paper quotes
│       │   ├── EvalResults.jsx     Hallucination delta comparison, auto-generated summary
│       │   ├── MarkdownMessage.jsx Markdown with glossary tooltips and LaTeX rendering
│       │   └── Header.jsx          View toggle, Save Manifest, Eval Results
│       └── content/
│           └── glossary.js         17 plain-English ML term definitions
└── evals/
    ├── runner.py                   Generates baseline and schema-grounded code
    ├── run_eval.py                 Orchestrates generation, testing, and reporting
    ├── report.py                   Markdown dH report generator
    ├── tests/
    │   ├── test_runnable.py        Subprocess exit-code check
    │   ├── test_shapes.py          Forward pass output shape verification
    │   └── test_drift.py           AST-based architectural bucket coverage
    └── artifacts/
        └── {arxiv_id}/             Per-paper: REPORT.md, results.json, generated code
```

---

## API reference

| Method | Endpoint | Body | Response |
|---|---|---|---|
| `POST` | `/api/ingest` | `{"url_or_id": "2410.05258"}` | Locked manifest |
| `POST` | `/api/traverse` | `ComponentManifest` | Traversal trace |
| `POST` | `/api/chat` | `{"message": "...", "manifest": {...}}` | Streamed chat response |
| `GET` | `/api/schema/sample` | | Sample locked manifest |
| `GET` | `/api/evals/papers` | | List of evaluated paper IDs |
| `GET` | `/api/evals/results/{paper_id}` | | Full eval results for one paper |
| `GET` | `/health` | | `{"status": "healthy"}` |

---

## Environment variables

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | Your OpenRouter key (`sk-or-v1-...`) |
| `ANTHROPIC_API_KEY` | Set to the same OpenRouter key |
| `OPENROUTER_MODEL` | Primary model for ingestion and chat |
| `OPENROUTER_FALLBACK_MODEL` | Fallback if the primary model fails |
| `TRAVERSAL_DEMO_MODE` | Set to `true` to skip LLM calls in the traversal agent |

---

## Stack

| Layer | Tool |
|---|---|
| PDF parsing | PyMuPDF + arXiv LaTeX source |
| LLM routing | OpenRouter (primary + fallback, centralised in `llm.py`) |
| Schema validation | Pydantic v2, SHA-256 content-hash locking |
| API | FastAPI |
| Architecture graph | @xyflow/react |
| Math rendering | KaTeX (via remark-math + rehype-katex in chat, react-katex in nodes) |
| Fonts | Poppins, Lora, JetBrains Mono |

---

## Sponsors

Anthropic · Voyado · Specific (YC F25) · Atech · Librar Labs (YC W26)
