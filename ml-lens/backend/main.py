from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/health")
async def health():
    return {"status": "healthy"}


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
