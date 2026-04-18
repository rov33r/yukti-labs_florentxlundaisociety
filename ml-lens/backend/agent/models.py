from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class IntermediateTensor(BaseModel):
    name: str
    symbolic: list[str]
    concrete: list[int]
    operation: str
    equation: str = ""

    @property
    def shape_str(self) -> str:
        return f"[{', '.join(self.symbolic)}]"

    @property
    def concrete_str(self) -> str:
        return f"[{', '.join(str(v) for v in self.concrete)}]"


class TraversalStep(BaseModel):
    component_id: str
    component_name: str
    component_kind: str
    input_state: str
    output_state: str
    transformation: str
    key_insight: str
    equations_applied: list[str] = Field(default_factory=list)
    intermediates: list[IntermediateTensor] = Field(default_factory=list)
    input_symbolic: list[str] = Field(default_factory=list)
    input_concrete: list[int] = Field(default_factory=list)
    output_symbolic: list[str] = Field(default_factory=list)
    output_concrete: list[int] = Field(default_factory=list)
    parameter_count: int = 0
    flops_approx: Optional[int] = None
    order: int


class TraversalTrace(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    arxiv_id: str
    paper_title: str
    steps: list[TraversalStep]
    model_used: str
    total_components: int
    total_parameters: int = 0
