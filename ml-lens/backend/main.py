from __future__ import annotations
import logging
import os
import re
import ssl
import time
import json
import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Literal

from dotenv import load_dotenv
load_dotenv()

if os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true":
    ssl._create_default_https_context = ssl._create_unverified_context

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI

warnings.filterwarnings('ignore', message='.*protected namespace.*')

from schema.validator import manifest_json_schema
from schema.lock import lock_manifest, LockedManifest
from schema.models import (
    ComponentManifest,
    PaperMetadata,
    Component,
    TensorContract,
    Invariant,
)
from agent import run_traversal, TraversalTrace
from ingestion import ingest_paper, ComponentExtractorError

try:
    from routers import diff as diff_router, test as test_router
    _diff_ok = True
except ImportError:
    _diff_ok = False

from llm import OPENROUTER_BASE_URL, PRIMARY_MODEL as DEFAULT_MODEL, chat_create

logger = logging.getLogger("ml_lens.backend")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Yukti API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if _diff_ok:
    app.include_router(diff_router.router, prefix="/diff", tags=["diff"])
    app.include_router(test_router.router, prefix="/test", tags=["test"])

# ── Models ──────────────────────────────────────────────────────────────────
class StatItem(BaseModel):
    label: str
    value: str
    subtext: str

class Evaluation(BaseModel):
    id: int
    name: str
    status: str
    score: Optional[float] = None
    created_at: Optional[str] = None

class IngestRequest(BaseModel):
    url_or_id: str
    force_refresh: bool = False

# ── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/stats", response_model=List[StatItem])
async def get_stats():
    return [
        {"label": "Total Evaluations", "value": "24", "subtext": "This month"},
        {"label": "Pass Rate", "value": "92%", "subtext": "Baseline models"},
        {"label": "Avg Score", "value": "8.4/10", "subtext": "All evaluations"},
    ]

_EVALS_DIR = Path(__file__).parent.parent / "evals"

@app.get("/api/evals/papers")
def get_eval_papers():
    artifacts = _EVALS_DIR / "artifacts"
    if not artifacts.exists():
        return []
    return sorted(
        d.name for d in artifacts.iterdir()
        if d.is_dir() and (d / "results.json").exists()
    )

@app.get("/api/evals/results/{paper_id}")
def get_eval_results(paper_id: str):
    results_path = _EVALS_DIR / "artifacts" / paper_id / "results.json"
    if not results_path.exists():
        raise HTTPException(status_code=404, detail=f"No results for {paper_id}")
    results = json.loads(results_path.read_text())
    spec_path = _EVALS_DIR / "fixtures" / f"ground_truth_spec_{paper_id}.json"
    spec = json.loads(spec_path.read_text()) if spec_path.exists() else {}
    return {
        "paper_id": paper_id,
        "paper_title": spec.get("paper_title", paper_id),
        "required_module_keywords": spec.get("required_module_keywords", {}),
        "results": results,
    }


def _build_chat_system_prompt(manifest: dict | None) -> str:
    if not manifest:
        return (
            "You are the ML Lens Architect. No paper schema is loaded. "
            "Answer general ML architecture questions concisely. "
            "Reply in markdown."
        )

    paper = manifest.get("paper", {})
    components = manifest.get("components", [])
    contracts = manifest.get("tensor_contracts", [])
    invariants = manifest.get("invariants", [])
    symbol_table = manifest.get("symbol_table", {})

    # Build compact component block
    comp_lines = []
    for c in components:
        eq_str = "  equations: " + "; ".join(c.get("equations", [])) if c.get("equations") else ""
        ops_str = "  operations: " + ", ".join(c.get("operations", [])) if c.get("operations") else ""
        hp_str = ""
        if c.get("hyperparameters"):
            hp_str = "  hyperparameters: " + ", ".join(f"{k}={v}" for k, v in c["hyperparameters"].items())
        dep_str = "  depends_on: " + ", ".join(c.get("depends_on", [])) if c.get("depends_on") else ""
        block = f"- {c['name']} (id={c['id']}, kind={c['kind']})\n  {c.get('description', '')}"
        for extra in [eq_str, ops_str, hp_str, dep_str]:
            if extra:
                block += f"\n{extra}"
        comp_lines.append(block)

    # Build tensor contract block
    contract_lines = []
    for tc in contracts:
        ins = ", ".join(f"{k}: [{', '.join(str(d) for d in v)}]" for k, v in tc.get("input_shapes", {}).items())
        outs = ", ".join(f"{k}: [{', '.join(str(d) for d in v)}]" for k, v in tc.get("output_shapes", {}).items())
        contract_lines.append(f"- {tc['component_id']}: in=({ins}) → out=({outs}) dtype={tc.get('dtype','?')}")

    # Build invariants block
    inv_lines = [f"- [{i['kind']}] {i['description']}" for i in invariants]

    # Build symbol table block
    sym_lines = [f"  {k}: {v}" for k, v in symbol_table.items()]

    return f"""You are the ML Lens Architect, an expert on the specific ML paper loaded in this session.

## Communication style
Explain clearly without assuming the reader has ML background knowledge.
When you use a technical term (e.g. attention, residual connection, softmax, tensor), briefly define it inline in plain English the first time it appears.
Avoid jargon-heavy sentences — prefer "this layer rescales the activations so training stays stable" over "this applies layer normalisation".
Be precise about tensor shapes, equations, and invariants where relevant, but always explain what they mean.

## Your knowledge is bounded to this schema
Answer questions grounded strictly in the schema below.
If the user asks about something not covered by the schema, say so explicitly rather than guessing.

## Paper
Title: {paper.get('title', 'Unknown')}
arXiv: {paper.get('arxiv_id', '?')}

## Components
{chr(10).join(comp_lines) if comp_lines else 'None'}

## Tensor Contracts
{chr(10).join(contract_lines) if contract_lines else 'None'}

## Invariants
{chr(10).join(inv_lines) if inv_lines else 'None'}

## Symbol Table
{chr(10).join(sym_lines) if sym_lines else 'None'}

## Response format
Reply in markdown. Be concise and specific — cite tensor shapes and equations from the schema above where helpful.
If the user asks about something not covered by the schema, say so explicitly rather than guessing."""


@app.post("/api/chat")
def chat(payload: dict):
    messages = payload.get("messages", [])
    manifest = payload.get("manifest")

    if not manifest:
        return {"content": "No paper schema loaded. Ingest a paper first to get schema-grounded answers.", "action": None}

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or "your_" in api_key:
        return {"content": "OpenRouter API key is missing. Please set it in the .env file.", "action": None}

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
    system_prompt = _build_chat_system_prompt(manifest)

    try:
        completion = chat_create(
            client,
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *messages
            ],
            timeout=60,
        )
        raw = (completion.choices[0].message.content or "").strip()
        return {"content": raw, "action": None}
    except Exception as e:
        logging.error(f"Chat error: {e}")
        return {"content": f"Error: {str(e)}", "action": None}

_CODEGEN_SYSTEM = (
    "You are an ML engineer implementing research papers in PyTorch. "
    "You are given a verified ComponentManifest (locked schema). "
    "The manifest is the ground truth — your implementation MUST match the manifest's "
    "component names, tensor contracts, and invariants exactly. "
    "Do not invent components not in the manifest. Do not omit components that are in it. "
    "Output ONLY a single self-contained Python file. No prose outside code comments. "
    "The file must define one torch.nn.Module class per component and a top-level model class."
)

_CODEGEN_USER = """Implement the following paper as a single PyTorch file,
strictly grounded to the provided manifest.

Requirements:
- Each component in `components` must map to a `nn.Module` class.
- Honor every invariant in `invariants` (residual connections, masking, weight tying, etc.).
- Honor every tensor contract in `tensor_contracts` — add shape comments citing them.
- No external dependencies beyond `torch`.
- Output ONLY the Python code inside a single ```python ... ``` fence.

<manifest>
{manifest_json}
</manifest>
"""

@app.post("/api/codegen")
def codegen(payload: dict):
    manifest = payload.get("manifest")
    if not manifest:
        raise HTTPException(status_code=422, detail="manifest is required")

    arxiv_id = manifest.get("paper", {}).get("arxiv_id", "unknown")
    cache_path = Path(f"/tmp/ml-lens-cache/{arxiv_id}/codegen.py")
    force_refresh = payload.get("force_refresh", False)

    if not force_refresh and cache_path.exists():
        return {"code": cache_path.read_text(), "cached": True}

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or "your_" in api_key:
        raise HTTPException(status_code=503, detail="OpenRouter API key missing")

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
    user_msg = _CODEGEN_USER.format(manifest_json=json.dumps(manifest, indent=2))

    try:
        completion = chat_create(
            client,
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": _CODEGEN_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            timeout=120,
        )
        raw = completion.choices[0].message.content or ""
        raw = re.sub(r"^```(?:python)?\s*\n?", "", raw.strip())
        raw = re.sub(r"\n?```$", "", raw)

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(raw)

        return {"code": raw, "cached": False}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Codegen error: {exc}")


@app.post("/api/ingest", response_model=LockedManifest)
def ingest(req: IngestRequest):
    try:
        manifest = ingest_paper(req.url_or_id, force_refresh=req.force_refresh)
        return lock_manifest(manifest)
    except ComponentExtractorError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ingestion error: {exc}")

@app.post("/api/traverse", response_model=TraversalTrace)
async def traverse_manifest(manifest: ComponentManifest):
    try:
        return await run_traversal(manifest)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Traversal agent error: {exc}")

@app.get("/api/schema/sample", response_model=LockedManifest)
async def get_sample_manifest():
    """Return a locked sample manifest (Attention Is All You Need excerpt)."""
    manifest = ComponentManifest(
        paper=PaperMetadata(
            arxiv_id="1706.03762",
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
            abstract=(
                "The dominant sequence transduction models are based on complex recurrent or "
                "convolutional neural networks... We propose a new simple network architecture, "
                "the Transformer, based solely on attention mechanisms."
            ),
            published="2017-06-12",
            pdf_url="https://arxiv.org/pdf/1706.03762",
        ),
        components=[
            Component(
                id="multi_head_attention",
                name="Multi-Head Attention",
                kind="multi_head_attention",
                description="Computes attention over h heads in parallel, projects queries, keys, values.",
                operations=["linear_project_qkv", "scaled_dot_product_attention", "concat_heads", "output_projection"],
                depends_on=["input_embedding", "positional_encoding"],
                hyperparameters={"h": "number of heads", "d_k": "key dimension = d_model / h"},
                equations=["Attention(Q,K,V) = softmax(QK^T / sqrt(d_k))V"],
            ),
            Component(
                id="feedforward",
                name="Position-wise Feed-Forward",
                kind="feedforward",
                description="Two linear transforms with ReLU, applied identically to each position.",
                operations=["linear", "relu", "linear"],
                depends_on=["multi_head_attention"],
                hyperparameters={"d_ff": "inner dimension (2048 in base model)"},
                equations=["FFN(x) = max(0, xW_1 + b_1)W_2 + b_2"],
            ),
        ],
        tensor_contracts=[
            TensorContract(
                component_id="multi_head_attention",
                input_shapes={"Q": ["B", "T_q", "d_model"], "K": ["B", "T_k", "d_model"], "V": ["B", "T_k", "d_model"]},
                output_shapes={"out": ["B", "T_q", "d_model"]},
                dtype="float32",
            )
        ],
        invariants=[
            Invariant(
                id="residual_add_norm",
                description="Each sub-layer output is LayerNorm(x + Sublayer(x)). Residual applied before norm.",
                kind="residual_connection",
                affected_components=["multi_head_attention", "feedforward"],
            )
        ],
        symbol_table={
            "B": "batch size",
            "T": "sequence length",
            "d_model": "model hidden dimension (512 in base)",
            "d_k": "key/query dimension per head",
            "h": "number of attention heads (8 in base)",
        },
    )
    return lock_manifest(manifest)

# ── Serve Frontend ──────────────────────────────────────────────────────────
if os.path.exists("./static"):
    app.mount("/assets", StaticFiles(directory="./static/assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join("./static", full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse("./static/index.html")
else:
    @app.get("/")
    async def root_fallback():
        return {"message": "Backend is running. Frontend static files not found (expected in ./static)."}
