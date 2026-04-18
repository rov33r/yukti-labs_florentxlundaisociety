import json
from schema.models import TraversalTrace, StateSnapshot
from .executor import RawResult


def parse_trace_result(raw: RawResult, params: dict) -> TraversalTrace:
    """Parse E2B stdout JSON into a TraversalTrace."""
    try:
        data = json.loads(raw.stdout)
    except json.JSONDecodeError as e:
        raise ValueError(f"E2B stdout is not valid JSON: {raw.stdout[:200]}")

    if "snapshots" not in data:
        raise ValueError("E2B output missing 'snapshots' key")

    snapshots_data = data.get("snapshots", [])
    if not snapshots_data:
        raise ValueError("E2B output has empty snapshots list")

    snapshots = [StateSnapshot(**snap) for snap in snapshots_data]

    return TraversalTrace(
        paper_id="unknown",
        params=data.get("params", params),
        snapshots=snapshots
    )
