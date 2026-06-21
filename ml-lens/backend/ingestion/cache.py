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
            d = json.loads(p.read_text(encoding="utf-8"))
            return ArxivPaper(**{**d, "pdf_path": Path(d["pdf_path"])})
        except Exception:
            return None

    def set_metadata(self, paper: ArxivPaper) -> None:
        d = {**paper.__dict__, "pdf_path": str(paper.pdf_path)}
        (self.root / "metadata.json").write_text(json.dumps(d), encoding="utf-8")

    def get_parsed(self) -> Optional[ParsedPaper]:
        p = self.root / "parsed.json"
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            images = []
            img_dir = self.root / "images"
            if img_dir.exists():
                for img_file in sorted(img_dir.glob("fig_*.png")):
                    images.append(img_file.read_bytes())
            
            return ParsedPaper(
                text=d["text"],
                equations=d["equations"],
                figure_captions=d["figure_captions"],
                high_context_text=d.get("high_context_text", d["text"][:15000]),
                figure_images=images,
            )
        except Exception:
            return None

    def set_parsed(self, parsed: ParsedPaper) -> None:
        d = {
            "text": parsed.text,
            "equations": parsed.equations,
            "figure_captions": parsed.figure_captions,
            "high_context_text": parsed.high_context_text,
        }
        (self.root / "parsed.json").write_text(json.dumps(d), encoding="utf-8")
        
        # Save images
        img_dir = self.root / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        for i, img_bytes in enumerate(parsed.figure_images):
            (img_dir / f"fig_{i:02d}.png").write_bytes(img_bytes)

    def get_manifest(self, phash: str) -> Optional[ComponentManifest]:
        p = self.root / f"manifest_{phash}.json"
        if not p.exists():
            return None
        try:
            return ComponentManifest.model_validate_json(p.read_text(encoding="utf-8"))
        except (ValidationError, Exception):
            return None

    def set_manifest(self, manifest: ComponentManifest, phash: str) -> None:
        p = self.root / f"manifest_{phash}.json"
        p.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
