from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from docling.document_converter import DocumentConverter


_LATEX_INLINE_RE = re.compile(r"\$([^$\n]+?)\$")
_LATEX_DISPLAY_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)


@dataclass
class ParsedPaper:
    markdown: str
    equations: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)


def _extract_equations(markdown: str) -> list[str]:
    """Pull LaTeX math from Docling's markdown output.

    Docling emits equations as `$...$` (inline) or `$$...$$` (display).
    We keep both in a flat list, display first.
    """
    display = [m.group(1).strip() for m in _LATEX_DISPLAY_RE.finditer(markdown)]
    inline = [m.group(1).strip() for m in _LATEX_INLINE_RE.finditer(markdown)]
    seen: set[str] = set()
    out: list[str] = []
    for eq in display + inline:
        if eq and eq not in seen:
            seen.add(eq)
            out.append(eq)
    return out


def _split_sections(markdown: str) -> dict[str, str]:
    """Split markdown on `##`/`#` headings into a title → body map."""
    sections: dict[str, str] = {}
    current_title = "_preamble"
    buf: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("#"):
            if buf:
                sections[current_title] = "\n".join(buf).strip()
            current_title = line.lstrip("#").strip() or "_untitled"
            buf = []
        else:
            buf.append(line)
    if buf:
        sections[current_title] = "\n".join(buf).strip()
    return sections


def parse_pdf(pdf_path: Path) -> ParsedPaper:
    """Run Docling over a PDF, return markdown + extracted equations + section map."""
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    markdown = result.document.export_to_markdown()
    return ParsedPaper(
        markdown=markdown,
        equations=_extract_equations(markdown),
        sections=_split_sections(markdown),
    )
