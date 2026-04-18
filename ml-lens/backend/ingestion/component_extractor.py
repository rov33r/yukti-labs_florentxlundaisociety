from __future__ import annotations

import json
import os
from typing import Optional

from anthropic import Anthropic
from pydantic import ValidationError

from schema.models import ComponentManifest, PaperMetadata

from .arxiv_resolver import ArxivPaper
from .pdf_parser import ParsedPaper
from .prompts import EXTRACTION_SYSTEM_PROMPT, USER_MESSAGE_TEMPLATE


DEFAULT_MODEL = "claude-opus-4-7"
MAX_MARKDOWN_CHARS = 120_000  # guard against papers that blow past the context budget


class ComponentExtractorError(RuntimeError):
    pass


def _truncate(markdown: str, limit: int = MAX_MARKDOWN_CHARS) -> str:
    if len(markdown) <= limit:
        return markdown
    head = markdown[: int(limit * 0.75)]
    tail = markdown[-int(limit * 0.25) :]
    return f"{head}\n\n...[TRUNCATED {len(markdown) - limit} CHARS]...\n\n{tail}"


def _build_user_message(paper: ArxivPaper, parsed: ParsedPaper) -> str:
    return USER_MESSAGE_TEMPLATE.format(
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        authors=", ".join(paper.authors),
        equations="\n".join(f"- {eq}" for eq in parsed.equations) or "(none extracted)",
        markdown=_truncate(parsed.markdown),
    )


def _parse_response(text: str) -> dict:
    """Claude sometimes wraps JSON in ```json fences despite instructions — strip them."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].lstrip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ComponentExtractorError(
            f"Claude did not return valid JSON: {exc}\nraw: {text[:500]}"
        ) from exc


def extract_manifest(
    paper: ArxivPaper,
    parsed: ParsedPaper,
    client: Optional[Anthropic] = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 8192,
) -> ComponentManifest:
    """Call Claude with the locked-schema extraction prompt, validate into ComponentManifest."""
    if client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ComponentExtractorError(
                "ANTHROPIC_API_KEY is not set. Add it to your environment or .env file."
            )
        client = Anthropic(api_key=api_key)

    user_message = _build_user_message(paper, parsed)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": EXTRACTION_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    if not text_blocks:
        raise ComponentExtractorError("Claude response contained no text blocks")
    raw_json = _parse_response("".join(text_blocks))

    # Guarantee paper metadata is populated from the resolver, not the model.
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
        raise ComponentExtractorError(
            f"ComponentManifest validation failed: {exc}"
        ) from exc
