"""Eval orchestrator: generate both conditions, run all tests, aggregate results.

Usage:
    python run_eval.py           # full run: baseline + mllens + tests + report
    python run_eval.py --skip-gen # reuse existing artifacts/{baseline,mllens}/generated.py
    python run_eval.py --tests-only  # alias for --skip-gen
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import baseline
import runner
from common import ARTIFACTS_DIR
from tests import test_drift, test_runnable, test_shapes
import report


CONDITIONS = ["baseline", "mllens"]


def _maybe_generate(skip: bool) -> None:
    if skip:
        print("[orchestrator] --skip-gen: reusing existing artifacts")
        return
    print("[orchestrator] running baseline condition...")
    baseline.main()
    print("[orchestrator] running mllens condition...")
    runner.main()


def _run_tests(name: str) -> dict:
    code_path = ARTIFACTS_DIR / name / "generated.py"
    if not code_path.exists():
        return {"error": f"no generated.py for {name}"}
    return {
        "runnable": test_runnable.run(code_path),
        "shapes":   test_shapes.run(code_path),
        "drift":    test_drift.run(code_path),
    }


def main() -> None:
    skip_gen = "--skip-gen" in sys.argv or "--tests-only" in sys.argv
    _maybe_generate(skip_gen)

    results = {name: _run_tests(name) for name in CONDITIONS}
    out = ARTIFACTS_DIR / "results.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"[orchestrator] results → {out}")
    for name, r in results.items():
        print(f"  {name}:")
        for axis in ("runnable", "shapes", "drift"):
            print(f"    {axis:10s} passed={r.get(axis, {}).get('passed')}")
    report.write_report(results)


if __name__ == "__main__":
    main()
