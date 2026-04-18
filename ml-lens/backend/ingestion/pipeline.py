from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from schema.models import ComponentManifest

from .arxiv_resolver import resolve_arxiv
from .cache import IngestionCache, prompt_hash
from .component_extractor import extract_manifest
from .pdf_parser import parse_pdf
from .prompts import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")


def _arxiv_id_from(url_or_id: str) -> str:
    m = _ARXIV_ID_RE.search(url_or_id.strip())
    if not m:
        raise ValueError(f"Could not parse arXiv id from: {url_or_id!r}")
    return m.group(1)


def ingest_paper(
    url_or_id: str,
    download_dir: Optional[Path] = None,
    force_refresh: bool = False,
) -> ComponentManifest:
    """End-to-end ingestion with on-disk caching at every stage.

    Stages (each cached independently):
      1. Resolve arXiv id, download PDF (skipped if cached).
      2. Parse PDF with Docling (skipped if cached ParsedPaper exists).
      3. Call Claude with the locked-schema extraction prompt (skipped if cached
         ComponentManifest exists for the current prompt hash).

    Set `force_refresh=True` to ignore cache and re-run every stage. The download
    dir argument is preserved for callers that want a non-default PDF location,
    but by default everything lives under the central cache root.
    """
    arxiv_id = _arxiv_id_from(url_or_id)
    cache = IngestionCache(arxiv_id)
    phash = prompt_hash(EXTRACTION_SYSTEM_PROMPT)

    # --- stage 3 fast-path: cached manifest wins outright, skips everything else.
    if not force_refresh:
        cached_manifest = cache.get_manifest(phash)
        if cached_manifest is not None:
            logger.info("cache hit: manifest for %s (prompt %s)", arxiv_id, phash)
            return cached_manifest

    # --- stage 1: metadata + PDF.
    paper = None if force_refresh else cache.get_metadata()
    if paper is None:
        logger.info("cache miss: fetching arXiv metadata + PDF for %s", arxiv_id)
        paper = resolve_arxiv(
            url_or_id,
            download_dir=download_dir,
            target_pdf_path=cache.pdf_path,
        )
        cache.set_metadata(paper)
    else:
        logger.info("cache hit: metadata + PDF for %s", arxiv_id)

    # --- stage 2: parsed paper (Docling is CPU-heavy — worth caching).
    parsed = None if force_refresh else cache.get_parsed()
    if parsed is None:
        logger.info("cache miss: running Docling for %s", arxiv_id)
        parsed = parse_pdf(paper.pdf_path)
        cache.set_parsed(parsed)
    else:
        logger.info("cache hit: parsed paper for %s", arxiv_id)

    # --- stage 3: Claude extraction. Always writes into the cache on success
    #              so subsequent calls with the same prompt are free.
    logger.info("cache miss: calling Claude extractor for %s", arxiv_id)
    manifest = extract_manifest(paper, parsed)
    cache.set_manifest(manifest, phash)
    return manifest
