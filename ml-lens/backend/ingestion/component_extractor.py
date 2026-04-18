from __future__ import annotations

import json
import os
import re
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

_VALID_KINDS = {
    "input_embedding", "positional_encoding", "linear_projection", "attention",
    "multi_head_attention", "feedforward", "layernorm", "rmsnorm", "residual",
    "softmax", "masking", "output_head", "other",
}

_KIND_ALIASES: dict[str, str] = {
    "embedding": "input_embedding",
    "token_embedding": "input_embedding",
    "word_embedding": "input_embedding",
    "positional_embedding": "positional_encoding",
    "position_encoding": "positional_encoding",
    "pos_encoding": "positional_encoding",
    "self_attention": "attention",
    "cross_attention": "attention",
    "scaled_dot_product_attention": "attention",
    "multi_head_self_attention": "multi_head_attention",
    "multihead_attention": "multi_head_attention",
    "mha": "multi_head_attention",
    "feed_forward": "feedforward",
    "ffn": "feedforward",
    "mlp": "feedforward",
    "position_wise_ffn": "feedforward",
    "layer_norm": "layernorm",
    "layer_normalization": "layernorm",
    "rms_norm": "rmsnorm",
    "rms_normalization": "rmsnorm",
    "skip_connection": "residual",
    "residual_connection": "residual",
    "add_norm": "residual",
    "softmax_attention": "softmax",
    "causal_mask": "masking",
    "attention_mask": "masking",
    "padding_mask": "masking",
    "linear": "linear_projection",
    "projection": "linear_projection",
    "linear_layer": "linear_projection",
    "output_projection": "linear_projection",
    "lm_head": "output_head",
    "language_model_head": "output_head",
    "classification_head": "output_head",
}


def _normalize_kind(kind: str) -> str:
    k = kind.lower().strip()
    if k in _VALID_KINDS:
        return k
    if k in _KIND_ALIASES:
        return _KIND_ALIASES[k]
    return "other"


def _normalize_invariant_kind(kind: str) -> str:
    valid = {"weight_tying", "causal_mask", "residual_connection", "init_scheme", "normalization_placement", "scaling", "other"}
    aliases = {
        "residual": "residual_connection",
        "weight_sharing": "weight_tying",
        "tied_weights": "weight_tying",
        "normalization": "normalization_placement",
        "norm_placement": "normalization_placement",
        "initialization": "init_scheme",
        "scale": "scaling",
        "mask": "causal_mask",
    }
    k = kind.lower().strip()
    if k in valid:
        return k
    if k in aliases:
        return aliases[k]
    return "other"


class ComponentExtractorError(RuntimeError):
    pass


def _truncate(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    head = text[: int(limit * 0.75)]
    tail = text[-int(limit * 0.25) :]
    return f"{head}\n\n...[TRUNCATED {len(text) - limit} CHARS]...\n\n{tail}"


_VALID_JSON_ESCAPES = set('"' + "\\\\" + "/bfnrtu")


def _fix_latex_escapes(s: str) -> str:
    """Replace bare LaTeX backslashes (invalid JSON escapes) with double-backslash."""
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            if s[i + 1] in _VALID_JSON_ESCAPES:
                result.append(s[i])
                result.append(s[i + 1])
                i += 2
            else:
                result.append('\\\\')
                i += 1
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


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
    except json.JSONDecodeError:
        pass
    # retry after fixing bare LaTeX backslashes
    try:
        return json.loads(_fix_latex_escapes(cleaned))
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

    if isinstance(raw_json.get("notes"), list):
        raw_json["notes"] = " ".join(str(n) for n in raw_json["notes"])

    for comp in raw_json.get("components", []):
        if "kind" in comp:
            comp["kind"] = _normalize_kind(comp["kind"])
        if "quote" in comp and isinstance(comp["quote"], str):
            comp["quote"] = {"text": comp["quote"]}
    for inv in raw_json.get("invariants", []):
        # generate id from name if missing
        if "id" not in inv and "name" in inv:
            inv["id"] = re.sub(r"[^a-z0-9]+", "_", inv["name"].lower()).strip("_")
        if "id" not in inv:
            inv["id"] = "invariant_" + str(raw_json.get("invariants", []).index(inv))
        if "kind" not in inv:
            inv["kind"] = "other"
        else:
            inv["kind"] = _normalize_invariant_kind(inv["kind"])
        if "affected_components" not in inv:
            inv["affected_components"] = []
        if "quote" in inv and isinstance(inv["quote"], str):
            inv["quote"] = {"text": inv["quote"]}
    valid_tcs = []
    for tc in raw_json.get("tensor_contracts", []):
        if "quote" in tc and isinstance(tc["quote"], str):
            tc["quote"] = {"text": tc["quote"]}
        # coerce common field-name variants
        for wrong, right in [
            ("component", "component_id"), ("id", "component_id"),
            ("input_shape", "input_shapes"), ("output_shape", "output_shapes"),
            ("inputs", "input_shapes"), ("outputs", "output_shapes"),
        ]:
            if wrong in tc and right not in tc:
                tc[right] = tc.pop(wrong)
        # if shapes are still missing, provide empty dicts so Pydantic won't error
        if "input_shapes" not in tc:
            tc["input_shapes"] = {}
        if "output_shapes" not in tc:
            tc["output_shapes"] = {}
        # coerce list-of-strings shapes to dict if needed (LLM sometimes returns ["B","T","d"])
        for key in ("input_shapes", "output_shapes"):
            val = tc[key]
            if isinstance(val, list):
                tc[key] = {"x": [str(s) for s in val]}
            elif isinstance(val, dict):
                for k, v in val.items():
                    if isinstance(v, str):
                        val[k] = [v]
        valid_tcs.append(tc)
    raw_json["tensor_contracts"] = valid_tcs

    try:
        return ComponentManifest.model_validate(raw_json)
    except ValidationError as exc:
        raise ComponentExtractorError(f"ComponentManifest validation failed: {exc}") from exc
