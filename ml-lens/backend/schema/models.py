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

InvariantKind = Literal[
    "weight_tying",
    "causal_mask",
    "residual_connection",
    "init_scheme",
    "normalization_placement",
    "scaling",
    "other",
]


class PaperQuote(BaseModel):
    text: str = Field(..., description="Verbatim excerpt from the paper")
    section: Optional[str] = Field(None, description="Section heading where this appears")


class TensorContract(BaseModel):
    component_id: str = Field(..., description="ID of the component this contract belongs to")
    input_shapes: dict[str, list[str]] = Field(
        ..., description="Symbolic input shapes, e.g. {'x': ['B', 'T', 'd_model']}"
    )
    output_shapes: dict[str, list[str]] = Field(
        ..., description="Symbolic output shapes"
    )
    dtype: Optional[str] = Field(None, description="Expected dtype, e.g. 'float32'")
    quote: Optional[PaperQuote] = None


class Invariant(BaseModel):
    id: str = Field(..., description="Unique snake_case identifier")
    description: str
    kind: InvariantKind
    affected_components: list[str] = Field(..., description="Component IDs this invariant applies to")
    quote: Optional[PaperQuote] = None


class Component(BaseModel):
    id: str = Field(..., description="Unique snake_case identifier, e.g. 'multi_head_attention'")
    name: str = Field(..., description="Human-readable name")
    kind: ComponentKind
    description: str
    operations: list[str] = Field(default_factory=list, description="Ordered list of ops this component performs")
    depends_on: list[str] = Field(default_factory=list, description="IDs of components this depends on")
    hyperparameters: dict[str, str] = Field(default_factory=dict, description="Symbolic hyperparameter names and meanings")
    equations: list[str] = Field(default_factory=list, description="LaTeX equations from the paper")
    quote: Optional[PaperQuote] = None


class PaperMetadata(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    pdf_url: str


class ComponentManifest(BaseModel):
    paper: PaperMetadata
    components: list[Component]
    tensor_contracts: list[TensorContract] = Field(default_factory=list)
    invariants: list[Invariant] = Field(default_factory=list)
    symbol_table: dict[str, str] = Field(
        default_factory=dict,
        description="Map of symbol -> meaning, e.g. {'d_model': 'model hidden dimension'}"
    )
    notes: Optional[str] = None
