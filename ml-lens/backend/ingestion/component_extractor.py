from __future__ import annotations

import json
import os
from typing import Optional

from openai import OpenAI
from pydantic import ValidationError

from schema.models import ComponentManifest, PaperMetadata

from .arxiv_resolver import ArxivPaper
from .pdf_parser import ParsedPaper
from .prompts import EXTRACTION_SYSTEM_PROMPT, USER_MESSAGE_TEMPLATE

DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "minimax/minimax-m2.7")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TEXT_CHARS = 80_000


class ComponentExtractorError(RuntimeError):
    pass


def _truncate(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    head = text[: int(limit * 0.75)]
    tail = text[-int(limit * 0.25) :]
    return f"{head}\n\n...[TRUNCATED {len(text) - limit} CHARS]...\n\n{tail}"


def _parse_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:])
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ComponentExtractorError(
            f"LLM did not return valid JSON: {exc}\nraw: {text[:500]}"
        ) from exc


def extract_manifest(
    paper: ArxivPaper,
    parsed: ParsedPaper,
    client: Optional[OpenAI] = None,
    model: str = DEFAULT_MODEL,
) -> ComponentManifest:
    if client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ComponentExtractorError("No API key found. Set ANTHROPIC_API_KEY in .env")
        client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)

    user_message = USER_MESSAGE_TEMPLATE.format(
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        authors=", ".join(paper.authors),
        equations="\n".join(f"- {eq}" for eq in parsed.equations) or "(none extracted)",
        figure_captions="\n".join(f"- {c}" for c in parsed.figure_captions) or "(none)",
        text=_truncate(parsed.text),
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=8192,
        temperature=0.1,
    )

    raw_text = (response.choices[0].message.content or "").strip()
    if not raw_text:
        raise ComponentExtractorError("LLM response was empty")

    raw_json = _parse_response(raw_text)

    raw_json["paper"] = PaperMetadata(
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        authors=paper.authors,
        abstract=paper.abstract,
        published=paper.published,
        pdf_url=paper.pdf_url,
    ).model_dump()

    try:
        return ComponentManifest.model_validate(raw_json)
    except ValidationError as exc:
        raise ComponentExtractorError(f"ComponentManifest validation failed: {exc}") from exc
