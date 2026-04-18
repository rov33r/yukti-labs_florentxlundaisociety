from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

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

app = FastAPI(title="ML Lens API")

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


# ── Ingestion endpoint ──────────────────────────────────────────────────────

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
    """Return the JSON Schema for ComponentManifest — the locked contract."""
    return manifest_json_schema()


@app.get("/api/schema/sample", response_model=LockedManifest)
async def get_sample_manifest():
    """Return a locked sample manifest (Attention Is All You Need excerpt)."""
    manifest = ComponentManifest(
        paper=PaperMetadata(
            arxiv_id="1706.03762",
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
            abstract="The dominant sequence transduction models are based on complex recurrent or "
                     "convolutional neural networks... We propose a new simple network architecture, "
                     "the Transformer, based solely on attention mechanisms.",
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
                equations=[r"Attention(Q,K,V) = softmax\!\left(\frac{QK^\top}{\sqrt{d_k}}\right)V"],
            ),
            Component(
                id="feedforward",
                name="Position-wise Feed-Forward",
                kind="feedforward",
                description="Two linear transforms with ReLU, applied identically to each position.",
                operations=["linear", "relu", "linear"],
                depends_on=["multi_head_attention"],
                hyperparameters={"d_ff": "inner dimension (2048 in base model)"},
                equations=[r"FFN(x) = \max(0, xW_1 + b_1)W_2 + b_2"],
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
