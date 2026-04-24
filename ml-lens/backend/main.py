from __future__ import annotations
import logging
import os
import ssl
import time
import json
import warnings
from datetime import datetime
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

# Configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "minimax/minimax-m2.7")

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

@app.post("/api/chat")
def chat(payload: dict):
    messages = payload.get("messages", [])
    manifest = payload.get("manifest")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or "your_" in api_key:
        return {"content": "OpenRouter API key is missing. Please set it in the .env file.", "action": None}
        
    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
    )

    system_prompt = f"""You are the ML Lens Architect. You help users understand and experiment with ML models.

## Your two modes:
1. INFORMATIONAL: If the user asks a question about ML concepts (e.g. "What is an encoder stack?"), explain it clearly. Do NOT propose an architecture change.
2. OPERATIONAL: If the user explicitly asks to modify, duplicate, or add something to the sandbox, propose an action.

## Context:
Current model architecture: {json.dumps(manifest.get('components') if manifest else [], indent=2)}

## Proposing Actions:
If (and ONLY if) an operational change is requested, include an "action" field in your response.
Action Schema: {{ "type": "duplicate_component", "payload": {{ "sourceId": string, "newId": string, "name": string, "depends_on": string[] }} }}

Return your response as a JSON object with:
- "content": Your markdown response.
- "action": null OR the action object.
"""

    try:
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *messages
            ],
            response_format={ "type": "json_object" },
            timeout=60,
        )
        res_data = json.loads(completion.choices[0].message.content)
        return res_data
    except Exception as e:
        logging.error(f"Chat error: {e}")
        return {"content": f"Error: {str(e)}", "action": None}

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
