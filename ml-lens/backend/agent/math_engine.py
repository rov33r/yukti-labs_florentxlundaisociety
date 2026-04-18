"""
Deterministic math engine for transformer component state traversal.
Uses manifest tensor_contracts as ground truth; computes intermediates inside each component.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from schema.models import Component, TensorContract

# ── Symbol resolution ────────────────────────────────────────────────────────

_FALLBACK = {
    "B": 1, "T": 10, "S": 10, "L": 10,
    "d_model": 512, "d_k": 64, "d_v": 64, "d_q": 64,
    "h": 8, "d_ff": 2048, "vocab_size": 30000, "d_out": 512,
    "num_layers": 6,
}


def resolve_symbols(symbol_table: dict[str, str]) -> dict[str, int]:
    """Extract concrete values from symbol_table, e.g. '512 in base' → 512."""
    resolved: dict[str, int] = {}
    for sym, meaning in symbol_table.items():
        nums = re.findall(r"\b(\d+)\b", meaning)
        if nums:
            resolved[sym] = int(nums[0])
    for k, v in _FALLBACK.items():
        resolved.setdefault(k, v)
    return resolved


def _c(sym: str, resolved: dict[str, int]) -> int:
    try:
        return int(sym)
    except (ValueError, TypeError):
        return resolved.get(sym, 1)


def _shape_str(symbolic: list[str], resolved: dict[str, int]) -> str:
    concrete = [str(_c(s, resolved)) for s in symbolic]
    return f"[{', '.join(symbolic)}] = [{', '.join(concrete)}]"


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class IntermediateTensor:
    name: str
    symbolic: list[str]
    concrete: list[int]
    operation: str
    equation: str = ""

    def shape_str(self) -> str:
        return f"[{', '.join(self.symbolic)}]  ({', '.join(str(v) for v in self.concrete)})"


@dataclass
class MathTransformResult:
    input_symbolic: list[str]
    input_concrete: list[int]
    output_symbolic: list[str]
    output_concrete: list[int]
    intermediates: list[IntermediateTensor]
    input_description: str
    output_description: str
    transformation_steps: list[str]
    parameter_count: int
    flops_approx: Optional[int] = None


# ── Per-kind math ─────────────────────────────────────────────────────────────

def _mk(name: str, sym: list[str], res: dict, op: str, eq: str = "") -> IntermediateTensor:
    return IntermediateTensor(
        name=name, symbolic=sym, concrete=[_c(s, res) for s in sym],
        operation=op, equation=eq,
    )


def _math_input_embedding(comp: Component, in_sym: list[str], res: dict) -> MathTransformResult:
    d = res["d_model"]
    vocab = res.get("vocab_size", 30000)
    B, T = res["B"], res["T"]
    out_sym = ["B", "T", "d_model"]
    params = vocab * d
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[B, T, d],
        intermediates=[
            _mk("token_ids", ["B", "T"], res, "Tokenized input", "x \\in \\mathbb{Z}^{B \\times T}"),
            _mk("embedding_table", ["vocab_size", "d_model"], res, "Lookup table E", "E \\in \\mathbb{R}^{V \\times d_{model}}"),
            _mk("embedded", ["B", "T", "d_model"], res, "Embedding lookup", "E[x] \\in \\mathbb{R}^{B \\times T \\times d_{model}}"),
        ],
        input_description=f"Token indices {_shape_str(['B','T'], res)}",
        output_description=f"Dense embeddings {_shape_str(out_sym, res)}, each token mapped to a {d}-dim vector",
        transformation_steps=[
            f"Lookup embedding table E ∈ ℝ^{{{vocab}×{d}}}",
            f"Each of {T} token ids → a {d}-dim row vector",
            f"Output: B×T×d_model = {B}×{T}×{d} = {B*T*d} floats",
        ],
        parameter_count=params,
        flops_approx=B * T * d,
    )


def _math_positional_encoding(comp: Component, in_sym: list[str], res: dict) -> MathTransformResult:
    B, T, d = res["B"], res["T"], res["d_model"]
    out_sym = ["B", "T", "d_model"]
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[B, T, d],
        intermediates=[
            _mk("PE_sin", ["T", "d_model//2"], res, "sin positional encodings",
                r"PE_{pos,2i} = \sin(pos / 10000^{2i/d_{model}})"),
            _mk("PE_cos", ["T", "d_model//2"], res, "cos positional encodings",
                r"PE_{pos,2i+1} = \cos(pos / 10000^{2i/d_{model}})"),
            _mk("x_+_PE", ["B", "T", "d_model"], res, "Elementwise addition", "x + PE"),
        ],
        input_description=f"Embeddings {_shape_str(in_sym, res)}",
        output_description=f"Position-aware embeddings {_shape_str(out_sym, res)}, position info injected via sin/cos",
        transformation_steps=[
            "Compute sinusoidal PE matrix (fixed, no parameters)",
            f"PE[pos, 2i]   = sin(pos / 10000^(2i/{d}))",
            f"PE[pos, 2i+1] = cos(pos / 10000^(2i/{d}))",
            "output = input_embeddings + PE   (broadcast over batch)",
        ],
        parameter_count=0,
        flops_approx=B * T * d,
    )


def _math_multi_head_attention(comp: Component, in_sym: list[str], res: dict) -> MathTransformResult:
    B, T, d = res["B"], res["T"], res["d_model"]
    h, dk = res["h"], res["d_k"]
    dv = res.get("d_v", dk)
    out_sym = ["B", "T", "d_model"]
    params = 4 * d * d  # W_Q, W_K, W_V, W_O each d×d
    flops = (
        3 * B * T * d * d           # QKV projections
        + B * h * T * T * dk        # Q@K^T per head
        + B * h * T * T             # softmax
        + B * h * T * T * dv        # scores@V
        + B * T * d * d             # output projection
    )
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[B, T, d],
        intermediates=[
            _mk("Q", ["B", "T", "d_model"], res, "Query projection", r"Q = xW_Q,\; W_Q \in \mathbb{R}^{d_{model}\times d_{model}}"),
            _mk("K", ["B", "T", "d_model"], res, "Key projection", r"K = xW_K"),
            _mk("V", ["B", "T", "d_model"], res, "Value projection", r"V = xW_V"),
            _mk("Q_heads", ["B", "h", "T", "d_k"], res, "Split into h heads", f"reshape → {B}×{h}×{T}×{dk}"),
            _mk("K_heads", ["B", "h", "T", "d_k"], res, "Split into h heads", f"reshape → {B}×{h}×{T}×{dk}"),
            _mk("V_heads", ["B", "h", "T", "d_v"], res, "Split into h heads", f"reshape → {B}×{h}×{T}×{dv}"),
            _mk("scores", ["B", "h", "T", "T"], res, "Scaled dot-product",
                r"\frac{QK^\top}{\sqrt{d_k}}"),
            _mk("attn_weights", ["B", "h", "T", "T"], res, "Softmax over keys",
                r"\text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right)"),
            _mk("context", ["B", "h", "T", "d_v"], res, "Weighted sum of values",
                r"\text{attn} \cdot V"),
            _mk("concat", ["B", "T", "d_model"], res, "Concatenate heads", "concat h heads → B×T×d_model"),
            _mk("output", ["B", "T", "d_model"], res, "Output projection", r"W_O \in \mathbb{R}^{d_{model}\times d_{model}}"),
        ],
        input_description=f"x {_shape_str(in_sym, res)}  (queries, keys, values all from same source in self-attention)",
        output_description=f"Context-enriched representation {_shape_str(out_sym, res)}  — each position now attends to all others",
        transformation_steps=[
            f"Project to Q, K, V each: {B}×{T}×{d}  (W_Q, W_K, W_V ∈ ℝ^{{{d}×{d}}})",
            f"Split {h} heads: {B}×{h}×{T}×{dk}",
            f"Scores = Q@K^T / √{dk}  → {B}×{h}×{T}×{T}  ({B*h*T*T:,} values)",
            f"Softmax over T={T} keys (each row sums to 1)",
            f"Context = softmax(scores) @ V → {B}×{h}×{T}×{dv}",
            f"Concat heads + project W_O → {B}×{T}×{d}",
            f"Total parameters: 4×d_model² = 4×{d}² = {params:,}",
            f"Approx FLOPs: {flops:,}",
        ],
        parameter_count=params,
        flops_approx=flops,
    )


def _math_feedforward(comp: Component, in_sym: list[str], res: dict) -> MathTransformResult:
    B, T, d, dff = res["B"], res["T"], res["d_model"], res["d_ff"]
    out_sym = ["B", "T", "d_model"]
    params = 2 * d * dff + dff + d
    flops = 2 * B * T * d * dff
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[B, T, d],
        intermediates=[
            _mk("hidden", ["B", "T", "d_ff"], res, "Linear + ReLU",
                r"h = \max(0,\; xW_1 + b_1),\; W_1 \in \mathbb{R}^{d_{model}\times d_{ff}}"),
            _mk("output", ["B", "T", "d_model"], res, "Second linear",
                r"hW_2 + b_2,\; W_2 \in \mathbb{R}^{d_{ff}\times d_{model}}"),
        ],
        input_description=f"Attention output {_shape_str(in_sym, res)}",
        output_description=f"Non-linearly transformed {_shape_str(out_sym, res)}, bottlenecked through {dff}-dim hidden",
        transformation_steps=[
            f"Linear W₁ ∈ ℝ^{{{d}×{dff}}}: {B}×{T}×{d} → {B}×{T}×{dff}  (expand ×{dff//d})",
            "ReLU: max(0, x)  (zeroes ~50% of hidden units)",
            f"Linear W₂ ∈ ℝ^{{{dff}×{d}}}: {B}×{T}×{dff} → {B}×{T}×{d}  (contract)",
            f"Parameters: 2×{d}×{dff} + bias = {params:,}",
            f"Approx FLOPs: {flops:,}",
        ],
        parameter_count=params,
        flops_approx=flops,
    )


def _math_layernorm(comp: Component, in_sym: list[str], res: dict) -> MathTransformResult:
    B, T, d = res["B"], res["T"], res["d_model"]
    out_sym = in_sym[:]
    params = 2 * d  # gamma, beta
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[_c(s, res) for s in out_sym],
        intermediates=[
            _mk("mean", ["B", "T", "1"], res, "Per-token mean", r"\mu = \frac{1}{d}\sum_i x_i"),
            _mk("var", ["B", "T", "1"], res, "Per-token variance", r"\sigma^2 = \frac{1}{d}\sum_i (x_i-\mu)^2"),
            _mk("normalized", ["B", "T", "d_model"], res, "Normalize",
                r"\hat{x} = \frac{x-\mu}{\sqrt{\sigma^2+\epsilon}}"),
            _mk("scaled", ["B", "T", "d_model"], res, "Affine rescale",
                r"\gamma \hat{x} + \beta,\; \gamma,\beta \in \mathbb{R}^{d_{model}}"),
        ],
        input_description=f"Pre-norm tensor {_shape_str(in_sym, res)}",
        output_description=f"Normalized tensor {_shape_str(out_sym, res)}, zero-mean unit-variance per token, then rescaled",
        transformation_steps=[
            f"Compute μ per token (mean over {d} features)",
            f"Compute σ² per token (variance over {d} features)",
            "Normalize: x̂ = (x − μ) / √(σ² + ε),  ε = 1e-5",
            f"Affine: γ·x̂ + β  where γ,β ∈ ℝ^{{{d}}} (learned)",
            f"Parameters: 2×d_model = {params}  (γ and β)",
            "Shape unchanged — stabilizes gradient flow",
        ],
        parameter_count=params,
        flops_approx=B * T * d * 4,
    )


def _math_residual(comp: Component, in_sym: list[str], res: dict) -> MathTransformResult:
    B, T, d = res["B"], res["T"], res["d_model"]
    out_sym = in_sym[:]
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[_c(s, res) for s in out_sym],
        intermediates=[
            _mk("x_residual", in_sym, res, "Skip connection (x)", "x (identity)"),
            _mk("sublayer_out", in_sym, res, "Sublayer output F(x)", "F(x)"),
            _mk("sum", in_sym, res, "Elementwise add", "x + F(x)"),
        ],
        input_description=f"Input x {_shape_str(in_sym, res)} passed through and around sublayer",
        output_description=f"x + sublayer(x) {_shape_str(out_sym, res)}, gradient highway preserved",
        transformation_steps=[
            "Identity shortcut: copy x unchanged",
            "Add sublayer output: output = x + F(x)",
            "Shape preserved — gradient flows directly through shortcut",
            "Parameters: 0",
        ],
        parameter_count=0,
        flops_approx=_c("B", res) * _c("T", res) * _c("d_model", res),
    )


def _math_softmax(comp: Component, in_sym: list[str], res: dict) -> MathTransformResult:
    B, h, T = res["B"], res["h"], res["T"]
    # Softmax usually operates over attention scores [B, h, T, T]
    score_sym = ["B", "h", "T", "T"]
    out_sym = score_sym[:]
    flops = B * h * T * T * 3  # exp + sum + div per element
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[_c(s, res) for s in out_sym],
        intermediates=[
            _mk("scores", score_sym, res, "Raw attention logits",
                r"\frac{QK^\top}{\sqrt{d_k}}"),
            _mk("exp_scores", score_sym, res, "Exponentiate",
                r"e^{s_i / \sqrt{d_k}}"),
            _mk("attn_weights", score_sym, res, "Normalize rows to sum 1",
                r"\text{softmax}(s)_i = \frac{e^{s_i}}{\sum_j e^{s_j}}"),
        ],
        input_description=f"Scaled attention scores {_shape_str(score_sym, res)}",
        output_description=f"Attention probability distribution {_shape_str(out_sym, res)}, each row sums to 1",
        transformation_steps=[
            f"Input: scaled scores {B}×{h}×{T}×{T}  (one row per query position)",
            "Numerical stability: subtract row-max before exp  (prevents overflow)",
            f"exp(s): exponentiate all {B*h*T*T:,} values",
            "Normalise: divide each row by its sum → probabilities in [0, 1]",
            f"Each of {B*h*T} query positions now has a distribution over {T} key positions",
            f"Approx FLOPs: {flops:,}  (0 learnable parameters)",
        ],
        parameter_count=0,
        flops_approx=flops,
    )


def _math_masking(comp: Component, in_sym: list[str], res: dict) -> MathTransformResult:
    B, h, T = res["B"], res["h"], res["T"]
    score_sym = ["B", "h", "T", "T"]
    out_sym = score_sym[:]
    flops = B * h * T * T  # one comparison + fill per element
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[_c(s, res) for s in out_sym],
        intermediates=[
            _mk("causal_mask", ["T", "T"], res, "Upper-triangular boolean mask",
                r"M_{ij} = \begin{cases}0 & i \geq j \\ -\infty & i < j\end{cases}"),
            _mk("masked_scores", score_sym, res, "Scores after masking",
                r"s_{ij} + M_{ij}"),
        ],
        input_description=f"Raw attention scores {_shape_str(score_sym, res)}",
        output_description=f"Causally masked scores {_shape_str(out_sym, res)} — future positions set to −∞ so softmax zeroes them",
        transformation_steps=[
            f"Build T×T upper-triangular mask (−∞ above diagonal, 0 on/below)",
            f"Add mask to scores: positions where i < j become −∞",
            "After softmax, −∞ → 0 probability — model cannot attend to future tokens",
            f"Shape preserved: {B}×{h}×{T}×{T}",
            "Parameters: 0  (fixed operation, no learned weights)",
        ],
        parameter_count=0,
        flops_approx=flops,
    )


def _math_linear_projection(comp: Component, in_sym: list[str], res: dict) -> MathTransformResult:
    B, T, d = res["B"], res["T"], res["d_model"]
    # Determine output dim from hyperparameters if available, else same as input
    d_out_str = comp.hyperparameters.get("d_out") or comp.hyperparameters.get("d_model")
    try:
        d_out = int(str(d_out_str).split()[0]) if d_out_str else d
    except (ValueError, TypeError):
        d_out = d
    out_sym = ["B", "T", "d_out"] if d_out != d else ["B", "T", "d_model"]
    params = d * d_out
    flops = B * T * d * d_out * 2
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[B, T, d_out],
        intermediates=[
            _mk("weight", ["d_model", "d_out"], res, "Projection matrix",
                r"W \in \mathbb{R}^{d_{model} \times d_{out}}"),
            _mk("output", out_sym, res, "Linear map",
                r"xW + b"),
        ],
        input_description=f"Input representation {_shape_str(in_sym, res)}",
        output_description=f"Projected representation {_shape_str(out_sym, res)} via learned linear map",
        transformation_steps=[
            f"Weight matrix W ∈ ℝ^{{{d}×{d_out}}}  (bias b ∈ ℝ^{{{d_out}}})",
            f"output = x @ W + b  →  {B}×{T}×{d_out}",
            f"Parameters: {d}×{d_out} + {d_out} = {params + d_out:,}",
            f"Approx FLOPs: {flops:,}",
        ],
        parameter_count=params,
        flops_approx=flops,
    )


def _math_output_head(comp: Component, in_sym: list[str], res: dict) -> MathTransformResult:
    B, T, d = res["B"], res["T"], res["d_model"]
    vocab = res.get("vocab_size", 30000)
    out_sym = ["B", "T", "vocab_size"]
    params = d * vocab
    flops = B * T * d * vocab * 2
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[B, T, vocab],
        intermediates=[
            _mk("lm_weight", ["d_model", "vocab_size"], res, "Unembedding matrix (often tied to input embedding)",
                r"W_U \in \mathbb{R}^{d_{model} \times V}"),
            _mk("logits", ["B", "T", "vocab_size"], res, "Unnormalized vocabulary scores",
                r"h W_U^\top \in \mathbb{R}^{B \times T \times V}"),
            _mk("next_token_probs", ["B", "T", "vocab_size"], res, "Softmax over vocabulary (inference only)",
                r"\text{softmax}(h W_U^\top)"),
        ],
        input_description=f"Final hidden states {_shape_str(in_sym, res)}",
        output_description=f"Vocabulary logits {_shape_str(out_sym, res)} — one score per token per position",
        transformation_steps=[
            f"Unembedding W_U ∈ ℝ^{{{d}×{vocab:,}}} projects {d}-dim hidden → {vocab:,} vocab scores",
            "Often weight-tied to input embedding matrix (halves parameter count)",
            f"Output logits: {B}×{T}×{vocab:,}  — argmax gives predicted next token",
            "During training: cross-entropy loss over these logits vs true next tokens",
            f"Parameters: {params:,}  (or 0 if weight-tied)",
            f"Approx FLOPs: {flops:,}",
        ],
        parameter_count=params,
        flops_approx=flops,
    )


def _math_passthrough(comp: Component, in_sym: list[str], res: dict, label: str) -> MathTransformResult:
    """Generic shape-preserving passthrough for masking, softmax, output_head, etc."""
    B, T, d = res["B"], res["T"], res["d_model"]
    out_sym = in_sym[:]
    return MathTransformResult(
        input_symbolic=in_sym, input_concrete=[_c(s, res) for s in in_sym],
        output_symbolic=out_sym, output_concrete=[_c(s, res) for s in out_sym],
        intermediates=[
            _mk(label, in_sym, res, comp.description[:80], ""),
        ],
        input_description=f"Input {_shape_str(in_sym, res)}",
        output_description=f"Output {_shape_str(out_sym, res)} — {label}",
        transformation_steps=[comp.description],
        parameter_count=0,
        flops_approx=None,
    )


# ── Main entry point ──────────────────────────────────────────────────────────

def compute_transform(
    component: Component,
    tensor_contracts: list[TensorContract],
    current_shape: list[str],
    symbol_table: dict[str, str],
) -> MathTransformResult:
    """Compute the mathematical transformation for one component.

    Uses tensor_contracts as ground truth for I/O shapes when present.
    Falls back to current_shape propagation otherwise.
    """
    res = resolve_symbols(symbol_table)

    # Use tensor_contract shapes when available (manifest ground truth)
    contract = next((tc for tc in tensor_contracts if tc.component_id == component.id), None)
    if contract:
        # Take first input tensor shape as canonical input
        first_in = next(iter(contract.input_shapes.values()), current_shape)
        first_out = next(iter(contract.output_shapes.values()), current_shape)
        in_sym = first_in
        out_sym = first_out
    else:
        in_sym = current_shape
        out_sym = current_shape

    kind = component.kind

    if kind == "input_embedding":
        return _math_input_embedding(component, in_sym, res)
    elif kind == "positional_encoding":
        return _math_positional_encoding(component, in_sym, res)
    elif kind in ("multi_head_attention", "attention"):
        return _math_multi_head_attention(component, in_sym, res)
    elif kind == "feedforward":
        return _math_feedforward(component, in_sym, res)
    elif kind in ("layernorm", "rmsnorm"):
        return _math_layernorm(component, in_sym, res)
    elif kind == "residual":
        return _math_residual(component, in_sym, res)
    elif kind == "softmax":
        return _math_softmax(component, in_sym, res)
    elif kind == "masking":
        return _math_masking(component, in_sym, res)
    elif kind == "linear_projection":
        return _math_linear_projection(component, in_sym, res)
    elif kind == "output_head":
        return _math_output_head(component, in_sym, res)
    else:
        result = _math_passthrough(component, in_sym, res, kind.replace("_", " "))
        if contract:
            result.output_symbolic = out_sym
            result.output_concrete = [_c(s, res) for s in out_sym]
        return result
