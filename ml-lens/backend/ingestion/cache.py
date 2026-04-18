from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from schema.models import ComponentManifest

from .arxiv_resolver import ArxivPaper
from .pdf_parser import ParsedPaper


def _default_cache_root() -> Path:
    env = os.getenv("ML_LENS_CACHE_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".cache" / "ml-lens"


def cache_root() -> Path:
    root = _default_cache_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def prompt_hash(*parts: str) -> str:
    """Stable short hash of the extraction prompt(s). Used to invalidate manifest cache
    when prompts change, so stale outputs don't leak into downstream agents."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:12]


class IngestionCache:
    """On-disk cache for the ingestion pipeline, keyed by arxiv id.

    Layout:
        <root>/<arxiv_id>/
            paper.pdf          — downloaded PDF bytes
            metadata.json      — ArxivPaper (title, authors, abstract, pdf_url, ...)
            parsed.json        — ParsedPaper (markdown + equations + sections)
            manifest-<h>.json  — ComponentManifest, h = short hash of extraction prompt
    """

    def __init__(self, arxiv_id: str, root: Optional[Path] = None) -> None:
        self.arxiv_id = arxiv_id
        self.dir = (root or cache_root()) / arxiv_id
        self.dir.mkdir(parents=True, exist_ok=True)

    # ---- paths ----------------------------------------------------------
    @property
    def pdf_path(self) -> Path:
        return self.dir / "paper.pdf"

    @property
    def metadata_path(self) -> Path:
        return self.dir / "metadata.json"

    @property
    def parsed_path(self) -> Path:
        return self.dir / "parsed.json"

    def manifest_path(self, phash: str) -> Path:
        return self.dir / f"manifest-{phash}.json"

    # ---- metadata (ArxivPaper) ------------------------------------------
    def get_metadata(self) -> Optional[ArxivPaper]:
        if not self.metadata_path.exists() or not self.pdf_path.exists():
            return None
        data = json.loads(self.metadata_path.read_text())
        data["pdf_path"] = self.pdf_path
        return ArxivPaper(**data)

    def set_metadata(self, paper: ArxivPaper) -> None:
        data = asdict(paper)
        data["pdf_path"] = str(data["pdf_path"])  # Path → str for JSON
        self.metadata_path.write_text(json.dumps(data, indent=2))

    # ---- parsed paper (Docling output) ----------------------------------
    def get_parsed(self) -> Optional[ParsedPaper]:
        if not self.parsed_path.exists():
            return None
        data = json.loads(self.parsed_path.read_text())
        return ParsedPaper(**data)

    def set_parsed(self, parsed: ParsedPaper) -> None:
        self.parsed_path.write_text(json.dumps(asdict(parsed), indent=2))

    # ---- manifest (Claude extraction) -----------------------------------
    def get_manifest(self, phash: str) -> Optional[ComponentManifest]:
        path = self.manifest_path(phash)
        if not path.exists():
            return None
        return ComponentManifest.model_validate_json(path.read_text())

    def set_manifest(self, manifest: ComponentManifest, phash: str) -> None:
        self.manifest_path(phash).write_text(manifest.model_dump_json(indent=2))

    # ---- invalidation ---------------------------------------------------
    def clear(self) -> None:
        for f in self.dir.glob("*"):
            if f.is_file():
                f.unlink()
