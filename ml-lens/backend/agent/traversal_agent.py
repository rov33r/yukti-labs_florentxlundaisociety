from __future__ import annotations

import asyncio
import json
import os

from openai import AsyncOpenAI

from schema.models import ComponentManifest, Component
from .math_engine import compute_transform, MathTransformResult
from .models import IntermediateTensor, TraversalStep, TraversalTrace

DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "minimax/minimax-m2.7")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_KIND_INSIGHT = {
    "input_embedding": "Maps discrete token IDs to continuous vector space — the only place where symbolic language enters the numeric world.",
    "positional_encoding": "Injects position information without parameters — uses fixed sin/cos frequencies so the model knows token order.",
    "multi_head_attention": "The core mechanism: every token attends to every other token simultaneously, learning which relationships matter.",
    "attention": "Computes query-key-value attention — determines how much each position contributes to each output.",
    "feedforward": "Position-wise MLP applies the same non-linear transform to every token independently, adding representational capacity.",
    "layernorm": "Normalizes activations per token to stabilize training and prevent gradient vanishing/explosion.",
    "rmsnorm": "Root-mean-square normalization — simpler than LayerNorm but empirically equivalent, used in LLaMA/Gemma.",
    "residual": "Skip connection lets gradients flow directly to earlier layers — the key to training very deep networks.",
    "softmax": "Converts raw scores to a probability distribution — ensures attention weights sum to 1 per query.",
    "masking": "Masks future positions so the model cannot cheat by looking ahead during autoregressive generation.",
    "linear_projection": "Learned linear map that projects between representation spaces.",
    "output_head": "Projects final hidden states to vocabulary logits — the probability distribution over the next token.",
    "other": "Component performs a specialized transformation in the model pipeline.",
}


def _topological_order(components: list[Component]) -> list[Component]:
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


async def _llm_insight(
    client: AsyncOpenAI,
    component: Component,
    math: MathTransformResult,
    model: str,
) -> str:
    """Call LLM for a one-sentence architectural insight. Falls back to template on any error."""
    try:
        prompt = (
            f"Component: {component.name} ({component.kind})\n"
            f"Input shape: {math.input_symbolic} = {math.input_concrete}\n"
            f"Output shape: {math.output_symbolic} = {math.output_concrete}\n"
            f"Key operations: {'; '.join(math.transformation_steps[:3])}\n"
            f"Parameters: {math.parameter_count:,}\n\n"
            "In one sentence (max 25 words), explain WHY this component is architecturally essential. "
            "Be specific to the math above. Reply with just the sentence, no quotes."
        )
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.4,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text if text else _KIND_INSIGHT.get(component.kind, _KIND_INSIGHT["other"])
    except Exception:
        return _KIND_INSIGHT.get(component.kind, _KIND_INSIGHT["other"])


async def run_traversal(manifest: ComponentManifest) -> TraversalTrace:
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("No API key found. Set ANTHROPIC_API_KEY in .env")

    client = AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
    model = DEFAULT_MODEL

    ordered = _topological_order(manifest.components)

    # ── Phase 1: deterministic math (sync, in topological order) ─────────────
    current_shape = ["B", "T"]
    math_results: list[tuple[Component, MathTransformResult]] = []

    for component in ordered:
        math = compute_transform(
            component=component,
            tensor_contracts=manifest.tensor_contracts,
            current_shape=current_shape,
            symbol_table=manifest.symbol_table,
        )
        math_results.append((component, math))
        current_shape = math.output_symbolic

    # ── Phase 2: parallel LLM insight calls ───────────────────────────────────
    insights = await asyncio.gather(
        *[_llm_insight(client, comp, math, model) for comp, math in math_results],
        return_exceptions=True,
    )

    # ── Phase 3: assemble TraversalSteps ─────────────────────────────────────
    steps: list[TraversalStep] = []
    for i, ((component, math), insight) in enumerate(zip(math_results, insights)):
        key_insight = (
            insight if isinstance(insight, str)
            else _KIND_INSIGHT.get(component.kind, _KIND_INSIGHT["other"])
        )

        steps.append(TraversalStep(
            component_id=component.id,
            component_name=component.name,
            component_kind=component.kind,
            input_state=math.input_description,
            output_state=math.output_description,
            transformation="\n".join(math.transformation_steps),
            key_insight=key_insight,
            equations_applied=component.equations,
            intermediates=[
                IntermediateTensor(
                    name=it.name,
                    symbolic=it.symbolic,
                    concrete=it.concrete,
                    operation=it.operation,
                    equation=it.equation,
                )
                for it in math.intermediates
            ],
            input_symbolic=math.input_symbolic,
            input_concrete=math.input_concrete,
            output_symbolic=math.output_symbolic,
            output_concrete=math.output_concrete,
            parameter_count=math.parameter_count,
            flops_approx=math.flops_approx,
            order=i,
        ))

    total_params = sum(s.parameter_count for s in steps)

    return TraversalTrace(
        arxiv_id=manifest.paper.arxiv_id,
        paper_title=manifest.paper.title,
        steps=steps,
        model_used=model,
        total_components=len(ordered),
        total_parameters=total_params,
    )
