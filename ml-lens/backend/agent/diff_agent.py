import json
import re
import os
from schema.models import TraversalTrace, HyperparamDelta, SchemaDiff, ComponentDiff
from .prompts import DIFF_SYSTEM_PROMPT


async def run_diff_agent(
    baseline: TraversalTrace,
    modified: TraversalTrace,
    deltas: list[HyperparamDelta],
    paper_id: str,
) -> SchemaDiff:
    """Compare two traces and produce a SchemaDiff (uses Claude if API key available, else mock)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if api_key:
        return await _run_with_claude(baseline, modified, deltas, paper_id)
    else:
        return _run_mock(baseline, modified, deltas, paper_id)


async def _run_with_claude(
    baseline: TraversalTrace,
    modified: TraversalTrace,
    deltas: list[HyperparamDelta],
    paper_id: str,
) -> SchemaDiff:
    """Use OpenRouter Claude API to analyze the diff."""
    from openai import OpenAI

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )

    # Build user message with both traces and deltas
    user_message = f"""
Baseline trace:
{json.dumps(baseline.model_dump(), indent=2)}

Modified trace:
{json.dumps(modified.model_dump(), indent=2)}

Hyperparameter deltas:
{json.dumps([d.model_dump() for d in deltas], indent=2)}

Analyze the tensor shape changes and explain which components changed, why, and which invariants hold or break.
"""

    response = client.chat.completions.create(
        model="claude-3.5-sonnet",
        max_tokens=4096,
        system=DIFF_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.choices[0].message.content

    # Strip markdown fences if present
    text = re.sub(r"^```json\n?", "", text)
    text = re.sub(r"\n?```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Diff agent returned invalid JSON: {text[:200]}")

    # Validate and ensure paper_id matches
    data["paper_id"] = paper_id
    result = SchemaDiff(**data)

    return result


def _run_mock(
    baseline: TraversalTrace,
    modified: TraversalTrace,
    deltas: list[HyperparamDelta],
    paper_id: str,
) -> SchemaDiff:
    """Generate a mock SchemaDiff without API calls (for quick testing)."""
    base_params = baseline.params
    mod_params = modified.params

    # Determine which components changed by comparing snapshots
    component_diffs = []
    for i, base_snap in enumerate(baseline.snapshots):
        if i >= len(modified.snapshots):
            break
        mod_snap = modified.snapshots[i]
        comp_id = base_snap.component_id

        changed = (
            base_snap.output_shape != mod_snap.output_shape
            or base_snap.input_shape != mod_snap.input_shape
        )

        rationale = ""
        if changed and comp_id == "attention":
            old_d_k = base_params.get("d_model", 512) // base_params.get("num_heads", 8)
            new_d_k = mod_params.get("d_model", 512) // mod_params.get("num_heads", 8)
            rationale = f"Halving num_heads doubles d_k from {old_d_k} to {new_d_k}. Each head now attends over a wider key subspace. The view() and transpose() calls in the forward pass must use (B, T, {mod_params.get('num_heads', 8)}, {new_d_k}) not (B, T, {base_params.get('num_heads', 8)}, {old_d_k}). Output shape is unchanged so the residual connection and downstream LayerNorm are unaffected."

        component_diffs.append(
            ComponentDiff(
                component_id=comp_id,
                changed=changed,
                param_deltas=[d for d in deltas if d.component_id == comp_id],
                old_shapes={
                    "input": base_snap.input_shape,
                    "output": base_snap.output_shape,
                },
                new_shapes={
                    "input": mod_snap.input_shape,
                    "output": mod_snap.output_shape,
                },
                rationale=rationale,
                invariants_held=["residual_connection"] if not changed else [],
                invariants_broken=[],
            )
        )

    # Generate implementation notes
    impl_notes = ""
    for delta in deltas:
        if delta.param == "num_heads":
            new_d_k = mod_params.get("d_model", 512) // delta.new_value
            old_d_k = base_params.get("d_model", 512) // delta.old_value
            impl_notes = f"Change MultiHeadAttention to use num_heads={delta.new_value} and d_k={new_d_k}. In the forward() method, update the view() calls from (B, T, {delta.old_value}, {old_d_k}) to (B, T, {delta.new_value}, {new_d_k}). The Q, K, V linear projections remain (d_model, d_model) — no weight shape changes required. FFN, LayerNorm, and embedding layers are unchanged. Residual connections are unaffected."

    return SchemaDiff(
        paper_id=paper_id,
        base_params=base_params,
        modified_params=mod_params,
        component_diffs=component_diffs,
        implementation_notes=impl_notes,
    )
