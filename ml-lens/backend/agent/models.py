from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class TraversalStep(BaseModel):
    component_id: str
    component_name: str
    component_kind: str
    input_state: str = Field(..., description="Tensor state entering this component")
    output_state: str = Field(..., description="Tensor state leaving this component")
    transformation: str = Field(..., description="Mathematical description of what happens")
    key_insight: str = Field(..., description="Why this component matters architecturally")
    equations_applied: list[str] = Field(default_factory=list)
    order: int = Field(..., description="Topological traversal order (0-indexed)")


class TraversalTrace(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    arxiv_id: str
    paper_title: str
    steps: list[TraversalStep]
    model_used: str
    total_components: int
