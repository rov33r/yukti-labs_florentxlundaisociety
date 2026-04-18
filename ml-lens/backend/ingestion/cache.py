from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from schema.models import ComponentManifest

from .arxiv_resolver import ArxivPaper
from .pdf_parser import ParsedPaper

_CACHE_ROOT = Path("/tmp/ml-lens-cache")


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:12]


class IngestionCache:
    def __init__(self, arxiv_id: str):
        self.root = _CACHE_ROOT / arxiv_id
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def pdf_path(self) -> Path:
        return self.root / "paper.pdf"

    def get_metadata(self) -> Optional[ArxivPaper]:
        p = self.root / "metadata.json"
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text())
            return ArxivPaper(**{**d, "pdf_path": Path(d["pdf_path"])})
        except Exception:
            return None

    def set_metadata(self, paper: ArxivPaper) -> None:
        d = {**paper.__dict__, "pdf_path": str(paper.pdf_path)}
        (self.root / "metadata.json").write_text(json.dumps(d))

    def get_parsed(self) -> Optional[ParsedPaper]:
        p = self.root / "parsed.json"
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text())
            return ParsedPaper(
                text=d["text"],
                equations=d["equations"],
                figure_captions=d["figure_captions"],
                figure_images=[],  # images not cached (large)
            )
        except Exception:
            return None

    def set_parsed(self, parsed: ParsedPaper) -> None:
        d = {
            "text": parsed.text,
            "equations": parsed.equations,
            "figure_captions": parsed.figure_captions,
        }
        (self.root / "parsed.json").write_text(json.dumps(d))

    def get_manifest(self, phash: str) -> Optional[ComponentManifest]:
        p = self.root / f"manifest_{phash}.json"
        if not p.exists():
            return None
        try:
            return ComponentManifest.model_validate_json(p.read_text())
        except (ValidationError, Exception):
            return None

    def set_manifest(self, manifest: ComponentManifest, phash: str) -> None:
        p = self.root / f"manifest_{phash}.json"
        p.write_text(manifest.model_dump_json(indent=2))
