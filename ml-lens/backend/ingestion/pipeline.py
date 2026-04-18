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
    """Lightweight 3-stage ingestion: arxiv metadata → PyMuPDF parse → LLM extraction.

    Each stage is independently cached under /tmp/ml-lens-cache/{arxiv_id}/.
    """
    arxiv_id = _arxiv_id_from(url_or_id)
    cache = IngestionCache(arxiv_id)
    phash = prompt_hash(EXTRACTION_SYSTEM_PROMPT)

    if not force_refresh:
        cached = cache.get_manifest(phash)
        if cached is not None:
            logger.info("cache hit: manifest for %s", arxiv_id)
            return cached

    paper = None if force_refresh else cache.get_metadata()
    if paper is None:
        logger.info("fetching arXiv metadata + PDF for %s", arxiv_id)
        paper = resolve_arxiv(url_or_id, download_dir=download_dir, target_pdf_path=cache.pdf_path)
        cache.set_metadata(paper)

    parsed = None if force_refresh else cache.get_parsed()
    if parsed is None:
        logger.info("parsing PDF with PyMuPDF for %s", arxiv_id)
        parsed = parse_pdf(paper.pdf_path, arxiv_id=arxiv_id)
        cache.set_parsed(parsed)

    logger.info("calling LLM extractor for %s", arxiv_id)
    manifest = extract_manifest(paper, parsed)
    cache.set_manifest(manifest, phash)
    return manifest
