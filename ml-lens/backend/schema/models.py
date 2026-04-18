from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


ComponentKind = Literal[
    "input_embedding",
    "positional_encoding",
    "linear_projection",
    "attention",
    "multi_head_attention",
    "feedforward",
    "layernorm",
    "rmsnorm",
    "residual",
    "softmax",
    "masking",
    "output_head",
    "other",
]


class PaperQuote(BaseModel):
    """A verbatim snippet from the paper supporting an extracted claim."""

    text: str = Field(..., description="Quoted text exactly as it appears in the paper")
    section: Optional[str] = Field(
        None, description="Section or page reference the quote came from"
    )


class TensorContract(BaseModel):
    """I/O shape contract for a component. Dims use symbolic names (e.g., 'B', 'T', 'd_model')."""

    component_id: str = Field(..., description="Stable id of the component this applies to")
    input_shapes: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Named input tensors → symbolic shape (e.g., 'x': ['B', 'T', 'd_model'])",
    )
    output_shapes: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Named output tensors → symbolic shape",
    )
    dtype: Optional[str] = Field(None, description="Expected dtype (e.g., fp32, bf16)")
    quote: Optional[PaperQuote] = Field(
        None, description="Paper quote supporting the shape claim"
    )


class Invariant(BaseModel):
    """A paper-level structural invariant that must hold (e.g., weight tying, causal mask)."""

    id: str = Field(..., description="Stable id for this invariant")
    description: str = Field(..., description="Human-readable statement of the invariant")
    kind: Literal[
        "weight_tying",
        "causal_mask",
        "residual_connection",
        "init_scheme",
        "normalization_placement",
        "scaling",
        "other",
    ]
    affected_components: list[str] = Field(
        default_factory=list, description="Component ids this invariant constrains"
    )
    quote: Optional[PaperQuote] = None


class Component(BaseModel):
    """A single architectural component extracted from the paper."""

    id: str = Field(..., description="Stable, snake_case identifier (e.g., 'scaled_dot_product_attention')")
    name: str = Field(..., description="Display name from the paper")
    kind: ComponentKind
    description: str = Field(..., description="One-paragraph functional description")
    operations: list[str] = Field(
        default_factory=list,
        description="Ordered list of tensor ops (e.g., 'matmul(Q, K.T)', 'scale by sqrt(d_k)')",
    )
    depends_on: list[str] = Field(
        default_factory=list, description="Component ids whose outputs feed this one"
    )
    hyperparameters: dict[str, str] = Field(
        default_factory=dict,
        description="Named hyperparameters referenced in the paper (e.g., 'd_k': '64', 'h': '8')",
    )
    equations: list[str] = Field(
        default_factory=list,
        description="LaTeX equations describing this component (verbatim from paper where possible)",
    )
    quote: Optional[PaperQuote] = Field(
        None, description="Paper quote that grounds this component"
    )


class PaperMetadata(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    published: Optional[str] = None
    pdf_url: Optional[str] = None


class ComponentManifest(BaseModel):
    """The locked schema contract — single source of truth for downstream agents."""

    paper: PaperMetadata
    components: list[Component] = Field(default_factory=list)
    tensor_contracts: list[TensorContract] = Field(default_factory=list)
    invariants: list[Invariant] = Field(default_factory=list)
    symbol_table: dict[str, str] = Field(
        default_factory=dict,
        description="Paper-level symbol definitions (e.g., 'd_model': 'model dimension', 'h': 'num heads')",
    )
    notes: Optional[str] = Field(
        None, description="Extractor notes, ambiguities flagged for human review"
    )
