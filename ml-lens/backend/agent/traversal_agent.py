from __future__ import annotations

import json
import os
import asyncio
from openai import AsyncOpenAI

from schema.models import ComponentManifest, Component, TensorContract
from .models import TraversalStep, TraversalTrace

DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _topological_order(components: list[Component]) -> list[Component]:
    """Return components sorted so dependencies come before dependents."""
    id_map = {c.id: c for c in components}
    visited: set[str] = set()
    order: list[Component] = []

    def visit(cid: str):
        if cid in visited:
            return
        visited.add(cid)
        comp = id_map.get(cid)
        if comp is None:
            return
        for dep in comp.depends_on:
            visit(dep)
        order.append(comp)

    for c in components:
        visit(c.id)
    return order


async def _traverse_component(
    client: AsyncOpenAI,
    component: Component,
    contracts: list[TensorContract],
    symbol_table: dict[str, str],
    model: str,
    order: int,
    prev_output: str,
) -> TraversalStep:
    contract = next((tc for tc in contracts if tc.component_id == component.id), None)

    symbols_str = ", ".join(f"{k}={v}" for k, v in symbol_table.items()) if symbol_table else "none"
    contract_str = ""
    if contract:
        contract_str = (
            f"Input shapes: {contract.input_shapes}\n"
            f"Output shapes: {contract.output_shapes}\n"
            f"dtype: {contract.dtype or 'float32'}"
        )

    equations_str = "\n".join(component.equations) if component.equations else "none"
    ops_str = ", ".join(component.operations) if component.operations else "none"

    prompt = f"""You are a data tensor flowing through the architecture of a research paper model.
Your previous state (from the prior layer): {prev_output or "raw input tokens"}

You are now entering component: {component.name} (kind: {component.kind})
Description: {component.description}
Operations performed on you: {ops_str}
Equations: {equations_str}
{contract_str}
Symbol table: {symbols_str}

Respond ONLY with valid JSON (no markdown fences):
{{
  "input_state": "concise description of your tensor state entering this component (mention shapes symbolically)",
  "output_state": "concise description of your tensor state after this component",
  "transformation": "what mathematically/computationally happens to you here — be specific to the ops and equations",
  "key_insight": "one sentence on why this component is architecturally significant"
}}"""

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=400,
        temperature=0.3,
    )

    raw = response.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "input_state": prev_output or "input tokens",
            "output_state": f"transformed by {component.name}",
            "transformation": component.description,
            "key_insight": f"{component.name} processes the data.",
        }

    return TraversalStep(
        component_id=component.id,
        component_name=component.name,
        component_kind=component.kind,
        input_state=data.get("input_state", ""),
        output_state=data.get("output_state", ""),
        transformation=data.get("transformation", ""),
        key_insight=data.get("key_insight", ""),
        equations_applied=component.equations,
        order=order,
    )


async def run_traversal(manifest: ComponentManifest) -> TraversalTrace:
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("No API key found. Set ANTHROPIC_API_KEY in .env")

    client = AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
    model = DEFAULT_MODEL

    ordered = _topological_order(manifest.components)
    steps: list[TraversalStep] = []
    prev_output = ""

    for i, component in enumerate(ordered):
        step = await _traverse_component(
            client=client,
            component=component,
            contracts=manifest.tensor_contracts,
            symbol_table=manifest.symbol_table,
            model=model,
            order=i,
            prev_output=prev_output,
        )
        steps.append(step)
        prev_output = step.output_state

    return TraversalTrace(
        arxiv_id=manifest.paper.arxiv_id,
        paper_title=manifest.paper.title,
        steps=steps,
        model_used=model,
        total_components=len(ordered),
    )
