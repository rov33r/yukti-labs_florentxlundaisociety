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
from pydantic import BaseModel, Field

warnings.filterwarnings('ignore', message='.*protected namespace.*')

from ingestion import IngestionCache, ingest_paper, prompt_hash
from ingestion.arxiv_resolver import ArxivResolverError
from ingestion.component_extractor import ComponentExtractorError
from ingestion.pipeline import _arxiv_id_from
from ingestion.prompts import EXTRACTION_SYSTEM_PROMPT
from schema.models import ComponentManifest

load_dotenv()

logger = logging.getLogger("ml_lens.backend")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ML Lens API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    url: str = Field(..., description="arXiv URL or bare id (e.g. 1706.03762)")
    force_refresh: bool = Field(
        default=False,
        description="Ignore on-disk cache and re-run every stage (PDF, Docling, Claude).",
    )


class IngestResponse(BaseModel):
    manifest: ComponentManifest
    cached: bool = Field(
        description="True if the manifest came from on-disk cache (no Claude call this request)."
    )


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    content: str


_PAPER_CONTEXT = """
## Active paper: Attention Is All You Need
**Authors:** Vaswani, Shazeer, Parmar, Uszkoreit, Jones, Gomez, Kaiser, Polosukhin (Google Brain / Research, 2017)
**arXiv:** 1706.03762

### Architecture overview
The Transformer replaces recurrence and convolutions entirely with self-attention.
It follows an encoder-decoder structure where both sides stack N=6 identical layers.

### Default hyperparameters (base model)
| Parameter | Value |
|-----------|-------|
| d_model (embedding / residual dim) | 512 |
| num_heads | 8 |
| d_k = d_v (per-head key/value dim) | 64 (= d_model / num_heads) |
| d_ff (feed-forward hidden dim) | 2048 |
| num_encoder_layers | 6 |
| num_decoder_layers | 6 |
| dropout | 0.1 |
| max_seq_len | 512 |
| vocab_size (WMT EN-DE) | ~37 000 |
| Activation | ReLU in FFN |

### Key components and what the paper says
- **Input Embedding:** Weights are shared with the pre-softmax linear layer. Multiplied by √d_model to prevent the embeddings from being too small relative to positional encoding.
- **Positional Encoding:** Fixed sinusoidal encoding (not learned). Uses sin for even indices, cos for odd. Allows the model to generalise to sequence lengths unseen during training.
- **Multi-Head Attention:** Splits queries, keys, values into h=8 heads, each of dimension d_k=64. Applies scaled dot-product attention (divides by √d_k to stabilise gradients), then concatenates and projects. Three variants: encoder self-attention (full), decoder masked self-attention (causal), and cross-attention (decoder queries over encoder output).
- **Masked Attention (decoder):** Sets all positions i > j to -∞ before softmax, ensuring position j cannot attend to future positions. Critical for autoregressive generation.
- **Feed-Forward Network:** Two linear transformations with ReLU: FFN(x) = max(0, xW₁+b₁)W₂+b₂. d_ff=2048 is 4× d_model. Applied identically and independently to each position.
- **Residual connections + Layer Norm:** Every sub-layer output is LayerNorm(x + Sublayer(x)). Stabilises training in deep stacks.
- **Linear + Softmax:** The decoder output is projected to vocab_size logits via a weight-tied linear layer (shared with embedding). Temperature is not used at training time but can be applied at inference.

### Training details
- Optimizer: Adam with β₁=0.9, β₂=0.98, ε=1e-9
- Learning rate schedule: warmup for 4 000 steps then inverse square root decay
- Label smoothing: ε_ls = 0.1
- Trained on 8× P100 GPUs for 12 hours (base) / 3.5 days (big model)
"""

CHAT_SYSTEM_PROMPT = """You are an ML model explainability assistant embedded in Yukti, \
an interactive ML analysis platform. The user is exploring a sandbox that visualises \
the architecture from the active paper below. Answer questions grounded in what the \
paper actually says — cite specific values (e.g. d_model=512, h=8) when relevant. \
Keep responses focused and moderately detailed: cover the key point and one supporting \
reason or example, then stop. Aim for 3-5 sentences or a short list — never more than \
two short paragraphs. Use plain language and analogies where helpful. \
Format with markdown (bold key terms, short bullet lists where appropriate) but avoid \
large walls of text or exhaustive breakdowns.

{paper_context}""".format(paper_context=_PAPER_CONTEXT)

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/stats", response_model=List[StatItem])
async def get_stats():
    return [
        {"label": "Total Evaluations", "value": "24", "subtext": "This month"},
        {"label": "Pass Rate", "value": "92%", "subtext": "Baseline models"},
        {"label": "Avg Score", "value": "8.4/10", "subtext": "All evaluations"}
    ]


@app.get("/api/evaluations", response_model=List[Evaluation])
async def get_evaluations():
    return [
        {"id": 1, "name": "GPT-4 vs Claude", "status": "completed", "score": 8.7, "created_at": "2024-01-15"},
        {"id": 2, "name": "Summarization Task", "status": "in-progress", "score": None, "created_at": "2024-01-16"},
        {"id": 3, "name": "Code Generation", "status": "completed", "score": 8.2, "created_at": "2024-01-14"}
    ]


@app.post("/api/evaluations", response_model=Evaluation)
async def create_evaluation(eval: Evaluation):
    return {"id": 4, **eval.dict(), "created_at": datetime.now().isoformat()}


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


def _was_cache_hit(url_or_id: str) -> bool:
    """Peek the cache to report whether this request could have been served without
    a fresh Claude call. Cheap: just a file-exists check keyed by current prompt hash."""
    try:
        arxiv_id = _arxiv_id_from(url_or_id)
    except ValueError:
        return False
    return IngestionCache(arxiv_id).manifest_path(
        prompt_hash(EXTRACTION_SYSTEM_PROMPT)
    ).exists()


@app.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest) -> IngestResponse:
    cached_before = _was_cache_hit(req.url) and not req.force_refresh
    try:
        manifest = ingest_paper(req.url, force_refresh=req.force_refresh)
    except ArxivResolverError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ComponentExtractorError as exc:
        logger.exception("component extraction failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("unexpected ingestion error")
        raise HTTPException(status_code=500, detail=f"ingestion failed: {exc}") from exc
    return IngestResponse(manifest=manifest, cached=cached_before)
