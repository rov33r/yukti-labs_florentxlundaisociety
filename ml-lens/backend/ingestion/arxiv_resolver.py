from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import arxiv

_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")


@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    pdf_url: str
    pdf_path: Path


class ArxivResolverError(RuntimeError):
    pass


def _extract_arxiv_id(url_or_id: str) -> str:
    candidate = url_or_id.strip()
    match = _ARXIV_ID_RE.search(candidate)
    if not match:
        raise ArxivResolverError(f"Could not parse arXiv id from: {url_or_id!r}")
    return match.group(1)


def resolve_arxiv(
    url_or_id: str,
    download_dir: Optional[Path] = None,
    target_pdf_path: Optional[Path] = None,
) -> ArxivPaper:
    arxiv_id = _extract_arxiv_id(url_or_id)
    search = arxiv.Search(id_list=[arxiv_id])
    try:
        result = next(arxiv.Client().results(search))
    except StopIteration as exc:
        raise ArxivResolverError(f"arXiv returned no results for {arxiv_id}") from exc

    if target_pdf_path is not None and target_pdf_path.exists():
        pdf_path = target_pdf_path
    else:
        if target_pdf_path is not None:
            dirpath = target_pdf_path.parent
            filename = target_pdf_path.name
        else:
            dirpath = download_dir or Path("/tmp/ml-lens-pdfs")
            filename = f"{arxiv_id}.pdf"
        dirpath.mkdir(parents=True, exist_ok=True)
        pdf_path = Path(result.download_pdf(dirpath=str(dirpath), filename=filename))

    return ArxivPaper(
        arxiv_id=arxiv_id,
        title=result.title.strip(),
        authors=[a.name for a in result.authors],
        abstract=result.summary.strip(),
        published=result.published.isoformat() if result.published else "",
        pdf_url=result.pdf_url,
        pdf_path=pdf_path,
    )
