from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from schema.models import (
    ComponentManifest,
    HyperparamDelta,
    TraversalTrace,
    SchemaDiff,
)
from sandbox.trace_emitter import build_trace_code
from sandbox.executor import execute_in_sandbox
from sandbox.result_parser import parse_trace_result
from agent.diff_agent import run_diff_agent


router = APIRouter()


class DiffRequest(BaseModel):
    manifest: ComponentManifest
    base_params: dict
    deltas: list[HyperparamDelta]


class DiffResponse(BaseModel):
    baseline_trace: TraversalTrace
    modified_trace: TraversalTrace
    schema_diff: SchemaDiff


@router.post("/", response_model=DiffResponse)
async def compute_diff(req: DiffRequest) -> DiffResponse:
    """Compute diff between baseline and modified hyperparameters."""

    # 1. Reject if manifest not locked
    if not req.manifest.locked:
        raise HTTPException(
            status_code=400,
            detail="manifest must be locked to compute diff"
        )

    # 2. Validate delta params exist in base_params
    unknown_params = set()
    for delta in req.deltas:
        if delta.param not in req.base_params:
            unknown_params.add(delta.param)

    if unknown_params:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown parameters in deltas: {', '.join(unknown_params)}"
        )

    # 3. Build modified params
    mod_params = dict(req.base_params)
    for delta in req.deltas:
        mod_params[delta.param] = delta.new_value

    # 4. Validate divisibility
    if "num_heads" in mod_params and "d_model" in mod_params:
        if mod_params["d_model"] % mod_params["num_heads"] != 0:
            raise HTTPException(
                status_code=422,
                detail=f"d_model={mod_params['d_model']} is not divisible by num_heads={mod_params['num_heads']}"
            )

    # 5. Build and execute both trace scripts
    baseline_code = build_trace_code(req.base_params)
    modified_code = build_trace_code(mod_params)

    baseline_raw = await execute_in_sandbox(baseline_code)
    if not baseline_raw.success:
        raise HTTPException(
            status_code=500,
            detail=f"Baseline trace execution failed: {baseline_raw.stderr}"
        )

    modified_raw = await execute_in_sandbox(modified_code)
    if not modified_raw.success:
        raise HTTPException(
            status_code=500,
            detail=f"Modified trace execution failed: {modified_raw.stderr}"
        )

    # 6. Parse both traces
    baseline_trace = parse_trace_result(baseline_raw, req.base_params)
    modified_trace = parse_trace_result(modified_raw, mod_params)

    # Set paper_id from manifest
    baseline_trace.paper_id = req.manifest.paper.arxiv_id
    modified_trace.paper_id = req.manifest.paper.arxiv_id

    # 7. Run diff agent
    schema_diff = await run_diff_agent(
        baseline_trace,
        modified_trace,
        req.deltas,
        req.manifest.paper.arxiv_id
    )

    return DiffResponse(
        baseline_trace=baseline_trace,
        modified_trace=modified_trace,
        schema_diff=schema_diff
    )
