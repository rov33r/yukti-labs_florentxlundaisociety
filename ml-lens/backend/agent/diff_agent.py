import json
import re
from anthropic import Anthropic
from schema.models import TraversalTrace, HyperparamDelta, SchemaDiff
from .prompts import DIFF_SYSTEM_PROMPT


async def run_diff_agent(
    baseline: TraversalTrace,
    modified: TraversalTrace,
    deltas: list[HyperparamDelta],
    paper_id: str,
) -> SchemaDiff:
    """Compare two traces using Claude and produce a SchemaDiff."""
    client = Anthropic()

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

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=DIFF_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text

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
