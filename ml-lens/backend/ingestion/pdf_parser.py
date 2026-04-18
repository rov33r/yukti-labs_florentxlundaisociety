from __future__ import annotations

import io
import re
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
import httpx

_EQUATION_ENVS = re.compile(
    r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}(.*?)\\end\{\1\}",
    re.DOTALL,
)
_INLINE_MATH = re.compile(r"\$([^$\n]{3,120})\$")


@dataclass
class ParsedPaper:
    text: str
    equations: list[str]
    figure_captions: list[str]
    figure_images: list[bytes] = field(default_factory=list)  # PNG bytes per figure


def _fetch_latex_source(arxiv_id: str) -> str | None:
    """Download arXiv LaTeX source tarball and return concatenated .tex content."""
    url = f"https://arxiv.org/e-print/{arxiv_id}"
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
    except Exception:
        return None

    content_type = resp.headers.get("content-type", "")
    raw = resp.content

    try:
        # tar.gz or tar
        with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
            parts = []
            for member in tf.getmembers():
                if member.name.endswith(".tex"):
                    f = tf.extractfile(member)
                    if f:
                        parts.append(f.read().decode("utf-8", errors="ignore"))
            return "\n".join(parts) if parts else None
    except tarfile.TarError:
        # Single .tex file returned directly
        if b"\\documentclass" in raw or b"\\begin{document}" in raw:
            return raw.decode("utf-8", errors="ignore")
        return None


def _extract_equations(latex_src: str) -> list[str]:
    equations = []
    for m in _EQUATION_ENVS.finditer(latex_src):
        eq = m.group(2).strip()
        if eq:
            equations.append(eq)
    for m in _INLINE_MATH.finditer(latex_src):
        eq = m.group(1).strip()
        if len(eq) > 5:
            equations.append(eq)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result = []
    for eq in equations:
        if eq not in seen:
            seen.add(eq)
            result.append(eq)
    return result[:200]  # cap to avoid blowing context


_CAPTION_RE = re.compile(r"(Figure|Fig\.?)\s*\d+[:\.]?\s*(.{10,300})", re.IGNORECASE)


def parse_pdf(pdf_path: Path, arxiv_id: str | None = None) -> ParsedPaper:
    doc = fitz.open(str(pdf_path))

    pages_text: list[str] = []
    figure_captions: list[str] = []
    figure_images: list[bytes] = []

    for page in doc:
        text = page.get_text("text")
        pages_text.append(text)

        for m in _CAPTION_RE.finditer(text):
            figure_captions.append(m.group(0).strip())

        # Extract embedded images (figures)
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.width > 100 and pix.height > 100:  # skip tiny icons
                    if pix.n > 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    figure_images.append(pix.tobytes("png"))
            except Exception:
                pass

    doc.close()
    full_text = "\n".join(pages_text)

    # Try to get clean equations from LaTeX source
    equations: list[str] = []
    if arxiv_id:
        latex_src = _fetch_latex_source(arxiv_id)
        if latex_src:
            equations = _extract_equations(latex_src)

    # Fallback: pull inline math from PDF text
    if not equations:
        equations = [m.group(1).strip() for m in _INLINE_MATH.finditer(full_text) if len(m.group(1)) > 5][:100]

    return ParsedPaper(
        text=full_text,
        equations=equations,
        figure_captions=figure_captions,
        figure_images=figure_images,
    )
