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

# ── Topology templates (injected into the skeleton prompt) ───────────────────
_TOPOLOGY_ENCODER_DECODER = """
## Expected topology: ENCODER-DECODER (e.g. original Transformer, T5, BART)

Encoder column (bottom → top):
  src_embedding → pos_encoding_enc
  pos_encoding_enc → encoder_self_attn (×N layers, each depending on previous layer's output)
  encoder_self_attn → enc_add_norm_1 → encoder_ffn → enc_add_norm_2
  (repeat for N layers, renaming with layer index if needed)

Decoder column (bottom → top):
  tgt_embedding → pos_encoding_dec
  pos_encoding_dec → decoder_masked_self_attn (×N layers)
  decoder_masked_self_attn → dec_add_norm_1
  dec_add_norm_1 + enc_add_norm_2 (last encoder layer) → decoder_cross_attn
  decoder_cross_attn → dec_add_norm_2 → decoder_ffn → dec_add_norm_3

Output:
  dec_add_norm_3 (last decoder layer) → linear_proj → output_softmax
"""

_TOPOLOGY_DECODER_ONLY = """
## Expected topology: DECODER-ONLY (e.g. GPT, LLaMA, Mistral)

  token_embedding → pos_encoding (or RoPE applied inside attention)
  pos_encoding → masked_self_attn_layer_1
  masked_self_attn_layer_1 → add_norm_1_layer_1 → ffn_layer_1 → add_norm_2_layer_1
  add_norm_2_layer_1 → masked_self_attn_layer_2 → ... (repeat ×N)
  last_add_norm → lm_head → output_softmax

  Note: RoPE/ALiBi are applied INSIDE attention, not as a separate upstream component.
  Residual skip: each add_norm depends on BOTH the sublayer output AND the previous add_norm (skip path).
"""

_TOPOLOGY_ENCODER_ONLY = """
## Expected topology: ENCODER-ONLY (e.g. BERT, RoBERTa, ViT)

  token_embedding → pos_encoding
  pos_encoding → self_attn_layer_1
  self_attn_layer_1 → add_norm_1_layer_1 → ffn_layer_1 → add_norm_2_layer_1
  add_norm_2_layer_1 → self_attn_layer_2 → ... (repeat ×N)
  last_add_norm → pooler_or_cls_head

  Residual skip: each add_norm depends on BOTH the sublayer output AND the input to that sublayer.
"""

_TOPOLOGY_UNKNOWN = """
## Expected topology: UNKNOWN

Carefully trace the data-flow from the paper's figures and text.
Identify whether this is encoder-only, decoder-only, or encoder-decoder, then apply the appropriate pattern.
"""

TOPOLOGY_TEMPLATES: dict[str, str] = {
    "encoder_decoder": _TOPOLOGY_ENCODER_DECODER,
    "decoder_only":    _TOPOLOGY_DECODER_ONLY,
    "encoder_only":    _TOPOLOGY_ENCODER_ONLY,
    "unknown":         _TOPOLOGY_UNKNOWN,
}

# ── Pass 1: skeleton ────────────────────────────────────────────────────────
_SKELETON_SYSTEM_BASE = """You are an expert ML research engineer.

Your ONLY task right now is to identify every distinct architectural component in this paper and map the data-flow graph between them.

Output a single JSON object with ONE key: "components" — an array of objects, each with:
- "id"         : unique snake_case string  (e.g. "encoder_self_attention")
- "name"       : human-readable name
- "kind"       : one of: input_embedding, positional_encoding, linear_projection, attention, multi_head_attention, feedforward, layernorm, rmsnorm, residual, softmax, masking, output_head, other
- "depends_on" : array of component ids this receives data FROM (empty only for root inputs)
- "column"     : "encoder", "decoder", or "shared"  (use "shared" if the paper has no encoder-decoder split)

Rules:
- Every non-root component MUST have at least one depends_on entry.
- Cross-attention ALWAYS depends on two upstreams: the decoder's previous sublayer AND the encoder's final output.
- Residual/LayerNorm wrappers are separate components from the sublayer they wrap.
- Do NOT include prose, tensor shapes, equations, or hyperparameters — those come in a second pass.

{topology_hint}

Output ONLY a ```json code block. No prose."""


def make_skeleton_prompt(topology: str = "unknown") -> str:
    hint = TOPOLOGY_TEMPLATES.get(topology, _TOPOLOGY_UNKNOWN)
    return _SKELETON_SYSTEM_BASE.format(topology_hint=hint)


SKELETON_USER_TEMPLATE = """Paper: {title} ({arxiv_id})

## Architecture text
{high_context_text}

## Figure captions
{figure_captions}

List every component and the data-flow edges between them now."""

# ── Pass 1.5: graph verification ────────────────────────────────────────────
GRAPH_VERIFY_SYSTEM_PROMPT = """You are an expert ML research engineer specialising in data-flow graphs.

You are given a list of components extracted from an ML paper and their current depends_on edges. Your job is to verify and correct ONLY the graph edges — do not change ids, names, or kinds.

Rules:
- Every non-root component must have at least one depends_on entry.
- Root components (e.g. input tokens, raw embeddings) have an empty depends_on.
- Cross-attention must depend on TWO upstreams: the decoder sublayer before it (Queries) AND the encoder's final output (Keys+Values).
- Residual connections: the component receiving the residual add depends on BOTH the sublayer output AND its own input (the skip path).
- Encoder and decoder stacks repeat — make sure repeated layer components depend on the previous layer's output, not the first layer.
- If the paper has no encoder-decoder split, treat everything as a single column.

Output a single JSON object:
{
  "components": [
    {"id": "<same id>", "depends_on": ["<corrected list>"]},
    ...
  ]
}

Include ALL component ids in the output, even those with correct edges. Output ONLY a ```json code block."""

GRAPH_VERIFY_USER_TEMPLATE = """Paper: {title}

## Current component graph
```json
{skeleton_json}
```

## Figure captions (use these to verify connections)
{figure_captions}

## Key equations (use these to verify Q/K/V routing and residual paths)
{equations}

Review every edge. Output the corrected depends_on for all components."""

# ── Pass 2: enrich ───────────────────────────────────────────────────────────
ENRICH_SYSTEM_PROMPT = """You are an expert ML research engineer.

You are given a skeleton component graph for an ML paper. Your task is to enrich each component with detail and produce the complete manifest.

Output a single JSON object with these keys:
- "components"       : the same components as the skeleton, each extended with:
    - "description"      : 1-2 sentence explanation
    - "operations"       : ordered list of ops (e.g. ["linear_project_qkv", "scaled_dot_product", "concat_heads"])
    - "hyperparameters"  : {param_name: meaning} dict
    - "equations"        : list of LaTeX strings from the paper (double-escape backslashes: \\\\frac)
- "tensor_contracts" : array of {component_id, input_shapes, output_shapes, dtype}
    - shapes are dicts: {"Q": ["B","T","d_model"]}
- "invariants"       : array of {id, name, description, kind, affected_components}
    - kind: weight_tying | causal_mask | residual_connection | init_scheme | normalization_placement | scaling | other
- "symbol_table"     : {symbol: meaning}  e.g. {"d_model": "hidden dimension (512)"}
- "notes"            : a single string with any important architectural notes

IMPORTANT: Keep every component from the skeleton. Do not add or remove components or change their ids or depends_on.

Output ONLY a ```json code block. No prose."""

ENRICH_USER_TEMPLATE = """Paper: {title} ({arxiv_id})

## Skeleton (DO NOT change ids or depends_on)
```json
{skeleton_json}
```

## Architecture text
{high_context_text}

## Equations
{equations}

## Figure captions
{figure_captions}

Enrich the skeleton and produce the full manifest now."""

# ── Legacy single-pass prompt (kept as fallback) ─────────────────────────────
EXTRACTION_SYSTEM_PROMPT = f"""You are an expert ML research engineer. Your task is to read an ML paper (text, equations, and provided figure images) and produce a structured JSON manifest of its architecture.

## Structural Reasoning Process (THINK before structuring)

Before you write the JSON, you MUST follow these reasoning steps in your `<thinking>` block:

1. **Inventory the components**: List every distinct block seen in the figures or described in the text (e.g., embeddings, attention types, normalization, feed-forward).
2. **Column Layout Detection**: Identify if the architecture uses parallel columns (e.g., a distinct Encoder column and a Decoder column). 
3. **Vertical Stacking & Flow**: Determine the direction of data flow (usually bottom-up in diagrams). Assign each block a logical level or rank.
4. **Identify Connections**: Trace the main path and all "skip" or "residual" connections. Note any cross-column connections (e.g., Encoder K,V to Decoder Cross-Attention).
5. **Categorize**: Group components into functional categories (Attention, Normalization, Feed-Forward, etc.).

## Output format

Produce a JSON object that strictly conforms to the JSON Schema below.

## JSON Schema (reference only — do NOT output this schema; output a POPULATED instance of it)

```json
{_SCHEMA_JSON}
```

## Critical field rules

- `components[*].kind` — MUST be exactly one of the enum values listed in the schema.
- `depends_on` — encodes the **data-flow graph**. Every non-root component MUST have at least one entry.
- **Cross-attention**: ALWAYS depends on TWO upstreams — the decoder's previous sublayer output (Queries) AND the encoder's final output (Keys + Values).
- All LaTeX in JSON strings must use double backslashes (e.g. `\\\\frac`, `\\\\sqrt`).

<<<<<<< Updated upstream
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

=======
>>>>>>> Stashed changes
## Extraction scope

Focus on transformer attention mechanisms: Q/K/V projections, attention score computation, softmax, masking, head splitting/merging, output projection, residual + norm placement, FFN. 

## Final Output Structure

First write a `<thinking>` block following the Structural Reasoning Process above. Then output the JSON inside a ```json code block.
"""

USER_MESSAGE_TEMPLATE = """Paper metadata:
- arxiv_id: {arxiv_id}
- title: {title}
- authors: {authors}

## Primary Architectural Context (Extracted from Methodology/Model sections)
{high_context_text}

## Figure Data
Figure captions:
{figure_captions}

(Note: Figures themselves are provided as images in this message. Use them to verify columns, layers, and connections.)

## Extracted Equations
{equations}

Produce the ComponentManifest JSON now."""

# Used as a retry system prompt when the model echoes the schema instead of filling it in.
FALLBACK_SYSTEM_PROMPT = f"""You are an expert ML research engineer.

Read the paper text below and output a single JSON object that is a FILLED-IN manifest of the paper's architecture. Do NOT output the schema definition itself — output real data extracted from the paper.

The JSON must have these top-level keys (all arrays of objects):
- "components"   — each with: id, name, kind, description, operations[], depends_on[]
- "tensor_contracts" — each with: component_id, input_shapes{{}}, output_shapes{{}}
- "invariants"   — each with: id, name, description, kind, affected_components[]
- "symbol_table" — object mapping symbol → meaning
- "notes"        — string

Valid "kind" values for components: input_embedding, positional_encoding, linear_projection, attention, multi_head_attention, feedforward, layernorm, rmsnorm, residual, softmax, masking, output_head, other

Output ONLY a ```json code block. No prose, no schema, no examples."""
