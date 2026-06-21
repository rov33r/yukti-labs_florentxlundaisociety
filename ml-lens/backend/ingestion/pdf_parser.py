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

# Section headings that signal architecture-relevant content
_ARCH_SECTION_RE = re.compile(
    r"^\s*(?:\d+\.?\s+)?"
    r"(model|architecture|method|approach|network|design|framework|proposed|system|overview|background|preliminaries|transformer|encoder|decoder|attention)\b",
    re.IGNORECASE | re.MULTILINE,
)

# Captions that likely describe an architecture diagram
_ARCH_CAPTION_RE = re.compile(
    r"(architecture|overview|model|framework|network|structure|diagram|encoder|decoder|transformer)",
    re.IGNORECASE,
)

_CAPTION_RE = re.compile(r"(Figure|Fig\.?)\s*\d+[:\.]?\s*(.{10,300})", re.IGNORECASE)


@dataclass
class ParsedPaper:
    text: str
    equations: list[str]
    figure_captions: list[str]
    high_context_text: str = ""
    figure_images: list[bytes] = field(default_factory=list)


def _fetch_latex_source(arxiv_id: str) -> str | None:
    url = f"https://arxiv.org/e-print/{arxiv_id}"
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
    except Exception:
        return None

    raw = resp.content
    try:
        with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
            parts = []
            for member in tf.getmembers():
                if member.name.endswith(".tex"):
                    f = tf.extractfile(member)
                    if f:
                        parts.append(f.read().decode("utf-8", errors="ignore"))
            return "\n".join(parts) if parts else None
    except tarfile.TarError:
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
    seen: set[str] = set()
    result = []
    for eq in equations:
        if eq not in seen:
            seen.add(eq)
            result.append(eq)
    return result[:200]


def _extract_high_context(pages_text: list[str], full_text: str) -> str:
    """Return only the sections most likely to describe the model architecture.

    Strategy (in priority order):
    1. Pages whose first non-empty line looks like an architecture section heading.
    2. Pages that contain an architecture figure caption.
    3. Pages that mention architecture-specific terms densely (≥3 distinct terms).
    4. Fallback: full text.
    """
    ARCH_TERMS = [
        "encoder", "decoder", "attention", "embedding", "layer norm",
        "feed-forward", "feedforward", "positional", "residual", "softmax",
        "self-attention", "cross-attention", "multi-head", "transformer",
        "projection", "linear", "token", "head",
    ]

    scored: list[tuple[int, str]] = []
    for page_text in pages_text:
        score = 0
        lines = page_text.strip().splitlines()
        first_line = next((l.strip() for l in lines if l.strip()), "")

        # Heading match → high priority
        if _ARCH_SECTION_RE.match(first_line):
            score += 10

        # Architecture caption on this page
        if _CAPTION_RE.search(page_text):
            caption_match = _CAPTION_RE.search(page_text)
            if caption_match and _ARCH_CAPTION_RE.search(caption_match.group(0)):
                score += 8

        # Term density
        page_lower = page_text.lower()
        distinct_hits = sum(1 for t in ARCH_TERMS if t in page_lower)
        score += distinct_hits

        if score > 0:
            scored.append((score, page_text))

    if not scored:
        return full_text

    # Sort by score descending, keep top pages up to ~30k chars
    scored.sort(key=lambda x: x[0], reverse=True)
    selected: list[str] = []
    total = 0
    for _, page_text in scored:
        if total + len(page_text) > 30_000:
            break
        selected.append(page_text)
        total += len(page_text)

    # Preserve original page order for readability
    page_set = set(id(p) for p in selected)
    ordered = [p for p in pages_text if id(p) in page_set]
    return "\n\n".join(ordered) if ordered else full_text


def _score_figure_images(
    pages_text: list[str],
    page_images: list[tuple[int, bytes]],  # (page_index, png_bytes)
) -> list[bytes]:
    """Return figures sorted by how likely they are to be architecture diagrams.

    Scoring: pages whose captions mention architecture keywords get priority.
    Falls back to all images if none score.
    """
    # Build page_index → caption score map
    page_scores: dict[int, int] = {}
    for page_idx, page_text in enumerate(pages_text):
        for m in _CAPTION_RE.finditer(page_text):
            if _ARCH_CAPTION_RE.search(m.group(0)):
                page_scores[page_idx] = page_scores.get(page_idx, 0) + 5
            else:
                page_scores[page_idx] = page_scores.get(page_idx, 0) + 1

    scored_images = sorted(page_images, key=lambda pi: page_scores.get(pi[0], 0), reverse=True)
    return [img for _, img in scored_images]


def parse_pdf(pdf_path: Path, arxiv_id: str | None = None) -> ParsedPaper:
    doc = fitz.open(str(pdf_path))

    pages_text: list[str] = []
    figure_captions: list[str] = []
    page_images: list[tuple[int, bytes]] = []  # (page_index, png_bytes)

    for page_idx, page in enumerate(doc):
        text = page.get_text("text")
        pages_text.append(text)

        for m in _CAPTION_RE.finditer(text):
            figure_captions.append(m.group(0).strip())

        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.width > 100 and pix.height > 100:
                    if pix.n > 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    page_images.append((page_idx, pix.tobytes("png")))
            except Exception:
                pass

    doc.close()
    full_text = "\n".join(pages_text)

    equations: list[str] = []
    if arxiv_id:
        latex_src = _fetch_latex_source(arxiv_id)
        if latex_src:
            equations = _extract_equations(latex_src)

    if not equations:
        equations = [
            m.group(1).strip()
            for m in _INLINE_MATH.finditer(full_text)
            if len(m.group(1)) > 5
        ][:100]

    high_context_text = _extract_high_context(pages_text, full_text)
    figure_images = _score_figure_images(pages_text, page_images)[:5]

    return ParsedPaper(
        text=full_text,
        equations=equations,
        figure_captions=figure_captions,
        high_context_text=high_context_text,
        figure_images=figure_images,
    )
