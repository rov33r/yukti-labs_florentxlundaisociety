from __future__ import annotations

import json

from schema.models import ComponentManifest

import copy

_raw_schema = ComponentManifest.model_json_schema()
_SCHEMA_FOR_LLM = copy.deepcopy(_raw_schema)
# Remove the `paper` field from the schema we show the LLM — it is injected server-side
_SCHEMA_FOR_LLM.get("properties", {}).pop("paper", None)
_SCHEMA_FOR_LLM.get("required", [None])  # keep as-is, just don't add
if "paper" in _SCHEMA_FOR_LLM.get("required", []):
    _SCHEMA_FOR_LLM["required"] = [r for r in _SCHEMA_FOR_LLM["required"] if r != "paper"]
_SCHEMA_JSON = json.dumps(_SCHEMA_FOR_LLM, indent=2)

EXTRACTION_SYSTEM_PROMPT = f"""You are an expert ML research engineer extracting a locked architectural contract from a paper. This contract grounds downstream code-generation agents, so precision matters more than breadth.

## Your job

Given the text of an ML paper (and its extracted LaTeX equations), produce a JSON object that strictly conforms to the JSON Schema below. Do not invent field names — use only the exact field names defined in the schema.

## JSON Schema (strict — your output MUST validate against this)

```json
{_SCHEMA_JSON}
```

## Critical field rules

- `components[*].kind` — MUST be exactly one of the enum values listed in the schema. No other values.
- `invariants[*].kind` — MUST be exactly one of the enum values listed in the schema. No other values.
- `quote` fields — MUST be an object with a `"text"` string field (and optional `"section"` string), NOT a plain string.
- `tensor_contracts[*].input_shapes` and `output_shapes` — MUST be objects mapping tensor name strings to arrays of symbolic dimension strings, e.g. {{"Q": ["B", "T_q", "d_model"]}}. Never a list.
- `notes` — MUST be a single string or null, NOT a list.
- Do NOT include the `paper` field — it will be injected automatically.
- All LaTeX in JSON strings must use double backslashes (e.g. `\\\\frac`, `\\\\sqrt`).

## depends_on — DATA FLOW GRAPH (CRITICAL — do not leave empty)

`depends_on` encodes the **data-flow graph**: which components feed their output tensor directly into this component's input.

Rules:
- Every non-root component MUST have at least one entry in `depends_on`.
- A root component (e.g. raw token embedding with no upstream) may have `depends_on: []`.
- Use only the `id` strings you defined for components in this manifest — never invent new ids.
- Model actual tensor flow: if component B receives its input tensor from component A, then `B.depends_on = ["<a_id>"]`.
- Multiple upstreams are allowed and required in these cases:
  - **Residual connections**: the merge node depends on both the pre-sublayer output AND the sublayer output.
  - **Cross-attention (encoder-decoder attention)**: ALWAYS depends on TWO upstreams — the decoder's previous sublayer output (Queries) AND the encoder's final output (Keys + Values). If you omit the encoder→cross-attention edge the graph is structurally wrong.
  - Any other data-join (e.g. concatenation, gating) similarly requires multiple upstreams.
- A disconnected graph (many nodes with empty depends_on, or encoder and decoder appearing as two separate trees) is WRONG. Re-read the paper and trace the data path.

Example dependency graph for a full Transformer encoder-decoder block (ids are illustrative only):
```json
[
  {{"id": "src_embedding",           "depends_on": []}},
  {{"id": "src_pos_enc",             "depends_on": []}},
  {{"id": "encoder_input",           "depends_on": ["src_embedding", "src_pos_enc"]}},
  {{"id": "enc_self_attention",      "depends_on": ["encoder_input"]}},
  {{"id": "enc_residual_1",          "depends_on": ["encoder_input", "enc_self_attention"]}},
  {{"id": "enc_norm_1",              "depends_on": ["enc_residual_1"]}},
  {{"id": "enc_feedforward",         "depends_on": ["enc_norm_1"]}},
  {{"id": "enc_residual_2",          "depends_on": ["enc_norm_1", "enc_feedforward"]}},
  {{"id": "enc_norm_2",              "depends_on": ["enc_residual_2"]}},
  {{"id": "tgt_embedding",           "depends_on": []}},
  {{"id": "tgt_pos_enc",             "depends_on": []}},
  {{"id": "decoder_input",           "depends_on": ["tgt_embedding", "tgt_pos_enc"]}},
  {{"id": "dec_masked_self_attn",    "depends_on": ["decoder_input"]}},
  {{"id": "dec_residual_1",          "depends_on": ["decoder_input", "dec_masked_self_attn"]}},
  {{"id": "dec_norm_1",              "depends_on": ["dec_residual_1"]}},
  {{"id": "dec_cross_attention",     "depends_on": ["dec_norm_1", "enc_norm_2"]}},
  {{"id": "dec_residual_2",          "depends_on": ["dec_norm_1", "dec_cross_attention"]}},
  {{"id": "dec_norm_2",              "depends_on": ["dec_residual_2"]}},
  {{"id": "dec_feedforward",         "depends_on": ["dec_norm_2"]}},
  {{"id": "dec_residual_3",          "depends_on": ["dec_norm_2", "dec_feedforward"]}},
  {{"id": "dec_norm_3",              "depends_on": ["dec_residual_3"]}},
  {{"id": "output_linear",           "depends_on": ["dec_norm_3"]}},
  {{"id": "output_softmax",          "depends_on": ["output_linear"]}}
]
```

Note how `dec_cross_attention` depends on BOTH `dec_norm_1` (decoder queries) AND `enc_norm_2` (encoder Keys+Values). This is the most commonly missed edge — never omit it for encoder-decoder architectures.

## Extraction scope

Focus on transformer attention mechanisms: Q/K/V projections, attention score computation, softmax, masking, head splitting/merging, output projection, residual + norm placement, FFN. If the paper is not attention-centric, still produce the manifest but flag it in `notes`.

## Correctness rules

- Never fabricate: if a shape, symbol, or invariant is not in the paper, omit it.
- Prefer symbolic over numeric: shapes use symbolic dim names from the paper.
- ids must be snake_case, unique, derived from the paper's own terminology.
- No prose outside JSON: your output must be a single JSON object. No markdown fences, no preamble.

## Output

Return ONLY a valid JSON object matching the schema above. No markdown, no explanation.
"""

USER_MESSAGE_TEMPLATE = """Paper metadata:
- arxiv_id: {arxiv_id}
- title: {title}
- authors: {authors}

Extracted LaTeX equations (deduped, up to 200):
{equations}

Figure captions extracted from PDF:
{figure_captions}

Paper text (PyMuPDF extraction):
---
{text}
---

Produce the ComponentManifest JSON now."""
