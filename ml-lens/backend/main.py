from __future__ import annotations

import logging
import os
import ssl
import warnings
from datetime import datetime
from typing import List, Optional, Literal

if os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true":
    ssl._create_default_https_context = ssl._create_unverified_context

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

warnings.filterwarnings('ignore', message='.*protected namespace.*')

load_dotenv()

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

logger = logging.getLogger("ml_lens.backend")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Yukti API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Shared models ────────────────────────────────────────────────────────────

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


# ── Chat models ──────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    content: str


_PAPER_CONTEXT = """
## Active paper: Attention Is All You Need
**Authors:** Vaswani, Shazeer, Parmar, Uszkoreit, Jones, Gomez, Kaiser, Polosukhin (2017)
**arXiv:** 1706.03762

### Default hyperparameters (base model)
| Parameter | Value |
|-----------|-------|
| d_model | 512 |
| num_heads | 8 |
| d_k = d_v | 64 |
| d_ff | 2048 |
| num_layers (enc + dec) | 6 + 6 |
| dropout | 0.1 |
| max_seq_len | 512 |
| vocab_size (WMT EN-DE) | ~37 000 |
| Activation | ReLU |

### Key component notes from the paper
- **Input Embedding:** Weight-tied with pre-softmax linear. Scaled by sqrt(d_model).
- **Positional Encoding:** Fixed sinusoidal (not learned). Generalises to unseen lengths.
- **Multi-Head Attention:** h=8 heads, d_k=64. Scaled dot-product attention (divide by sqrt(d_k)).
- **Masked Attention:** Causal mask sets future positions to -inf before softmax.
- **Feed-Forward:** FFN(x) = max(0, xW1+b1)W2+b2. d_ff=2048 = 4x d_model.
- **Residual + LayerNorm:** Every sub-layer: LayerNorm(x + Sublayer(x)).
- **Linear + Softmax:** Weight-tied projection to vocab_size logits.

### Training
- Adam: b1=0.9, b2=0.98, eps=1e-9. Warmup 4000 steps then inverse sqrt decay.
- Label smoothing: 0.1
"""

CHAT_SYSTEM_PROMPT = (
    "You are an ML model explainability assistant embedded in Yukti, "
    "an interactive ML analysis platform. The user is exploring a sandbox that visualises "
    "the architecture from the active paper below. Answer questions grounded in what the "
    "paper actually says — cite specific values (e.g. d_model=512, h=8) when relevant. "
    "Keep responses focused and moderately detailed: cover the key point and one supporting "
    "reason or example, then stop. Aim for 3-5 sentences or a short list — never more than "
    "two short paragraphs. Use plain language and analogies where helpful. "
    "Format with markdown (bold key terms, short bullet lists where appropriate) but avoid "
    "large walls of text or exhaustive breakdowns.\n\n"
    + _PAPER_CONTEXT
)


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy"}


# ── Stub dashboard endpoints ─────────────────────────────────────────────────

@app.get("/api/stats", response_model=List[StatItem])
async def get_stats():
    return [
        {"label": "Total Evaluations", "value": "24", "subtext": "This month"},
        {"label": "Pass Rate", "value": "92%", "subtext": "Baseline models"},
        {"label": "Avg Score", "value": "8.4/10", "subtext": "All evaluations"},
    ]


@app.get("/api/evaluations", response_model=List[Evaluation])
async def get_evaluations():
    return [
        {"id": 1, "name": "GPT-4 vs Claude", "status": "completed", "score": 8.7, "created_at": "2024-01-15"},
        {"id": 2, "name": "Summarization Task", "status": "in-progress", "score": None, "created_at": "2024-01-16"},
        {"id": 3, "name": "Code Generation", "status": "completed", "score": 8.2, "created_at": "2024-01-14"},
    ]


@app.post("/api/evaluations", response_model=Evaluation)
async def create_evaluation(evaluation: Evaluation):
    return {"id": 4, **evaluation.model_dump(), "created_at": datetime.now().isoformat()}


# ── Chat endpoint (OpenRouter) ───────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")

    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in req.messages]

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "google/gemma-3-27b-it", "messages": messages},
        )

    if resp.status_code != 200:
        logger.error("OpenRouter error %s: %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="LLM request failed")

    return ChatResponse(content=resp.json()["choices"][0]["message"]["content"])


# ── Ingestion endpoint (lightweight PyMuPDF pipeline) ────────────────────────

class IngestRequest(BaseModel):
    url_or_id: str
    force_refresh: bool = False


@app.post("/api/ingest", response_model=LockedManifest)
async def ingest(req: IngestRequest):
    """Download + parse an arXiv paper and extract its ComponentManifest."""
    try:
        manifest = ingest_paper(req.url_or_id, force_refresh=req.force_refresh)
        return lock_manifest(manifest)
    except ComponentExtractorError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ingestion error: {exc}")


# ── Traversal Agent endpoint ─────────────────────────────────────────────────

@app.post("/api/traverse", response_model=TraversalTrace)
async def traverse_manifest(manifest: ComponentManifest):
    """Run the traversal agent over a ComponentManifest and return the trace."""
    try:
        return await run_traversal(manifest)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Traversal agent error: {exc}")


# ── Schema Contract endpoints ────────────────────────────────────────────────

@app.get("/api/schema")
async def get_schema():
    """Return the JSON Schema for ComponentManifest."""
    return manifest_json_schema()


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
