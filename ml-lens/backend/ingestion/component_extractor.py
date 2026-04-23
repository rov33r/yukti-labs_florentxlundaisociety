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

# Kind-based topological order used to infer missing depends_on.
# Earlier kinds naturally precede later ones in a transformer data flow.
_KIND_ORDER = [
    "input_embedding",
    "positional_encoding",
    "masking",
    "linear_projection",
    "attention",
    "multi_head_attention",
    "softmax",
    "residual",
    "layernorm",
    "rmsnorm",
    "feedforward",
    "output_head",
    "other",
]


def _infer_depends_on(raw_json: dict) -> dict:
    """Best-effort pass to fill in missing depends_on links.

    Strategy (applied in order, stopping when enough connections are made):
    1. tensor_contracts: if component A's output shapes match component B's
       input shapes (same keys), A -> B.
    2. Kind-based ordering: assign each component a tier from _KIND_ORDER
       and connect sequential tiers when no connection exists.
    """
    comps = raw_json.get("components") or []
    if not comps:
        return raw_json

    ids = {c["id"] for c in comps if isinstance(c, dict) and "id" in c}
    id_list = [c["id"] for c in comps if isinstance(c, dict) and "id" in c]

    # Check if graph is already well-connected (>50% of non-root nodes have deps)
    non_root = [c for c in comps if isinstance(c, dict) and c.get("depends_on")]
    if len(non_root) > len(comps) * 0.5:
        return raw_json  # looks fine, skip inference

    tcs = raw_json.get("tensor_contracts") or []
    # Build output_shapes map: component_id -> set of output tensor name sets
    tc_out: dict[str, set] = {}
    tc_in: dict[str, set] = {}
    for tc in tcs:
        if not isinstance(tc, dict):
            continue
        cid = tc.get("component_id", "")
        if cid:
            tc_out[cid] = set(tc.get("output_shapes", {}).keys())
            tc_in[cid] = set(tc.get("input_shapes", {}).keys())

    # Pass 1: tensor shape key matching
    inferred: dict[str, list[str]] = {c["id"]: [] for c in comps if isinstance(c, dict) and "id" in c}
    for b_id in id_list:
        b_inputs = tc_in.get(b_id, set())
        if not b_inputs:
            continue
        for a_id in id_list:
            if a_id == b_id:
                continue
            a_outputs = tc_out.get(a_id, set())
            if a_outputs and b_inputs & a_outputs:  # overlapping tensor names
                inferred[b_id].append(a_id)

    # Pass 2: kind-order fallback — chain components by tier
    def _tier(comp):
        kind = comp.get("kind", "other") if isinstance(comp, dict) else "other"
        try:
            return _KIND_ORDER.index(kind)
        except ValueError:
            return len(_KIND_ORDER)

    sorted_comps = sorted([c for c in comps if isinstance(c, dict)], key=_tier)
    if not any(inferred.values()):  # only use kind-order if tensor matching found nothing
        for i, comp in enumerate(sorted_comps):
            cid = comp.get("id", "")
            if not cid or inferred.get(cid):
                continue
            # connect to the previous tier component
            if i > 0:
                prev_id = sorted_comps[i - 1].get("id", "")
                if prev_id and prev_id in ids:
                    inferred[cid] = [prev_id]

    # Merge inferred deps into raw_json (only for components that still have no deps)
    for comp in comps:
        if not isinstance(comp, dict):
            continue
        cid = comp.get("id", "")
        if not comp.get("depends_on") and inferred.get(cid):
            comp["depends_on"] = inferred[cid]

    return raw_json

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
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key or "your_" in api_key:
            raise ComponentExtractorError("No valid API key found. Set OPENROUTER_API_KEY in .env")
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

    # Guard: detect if the LLM echoed back the JSON Schema instead of real data
    if "$defs" in raw_json or "properties" in raw_json or "type" in raw_json:
        raise ComponentExtractorError(
            "LLM returned the JSON Schema definition instead of a populated manifest. "
            "This usually means the model misunderstood the prompt. Try re-running ingestion."
        )

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

    for comp in (raw_json.get("components") or []):
        if not isinstance(comp, dict): continue
        if "kind" in comp:
            comp["kind"] = _normalize_kind(comp["kind"])
        if "quote" in comp and isinstance(comp["quote"], str):
            comp["quote"] = {"text": comp["quote"]}
    for inv in (raw_json.get("invariants") or []):
        if not isinstance(inv, dict): continue
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
    for tc in (raw_json.get("tensor_contracts") or []):
        if not isinstance(tc, dict): continue
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

    # Post-process: infer missing depends_on connections
    raw_json = _infer_depends_on(raw_json)

    try:
        return ComponentManifest.model_validate(raw_json)
    except ValidationError as exc:
        raise ComponentExtractorError(f"ComponentManifest validation failed: {exc}") from exc
