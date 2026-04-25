"""Runnable test: does `python generated.py` exit cleanly?

The generated file's `__main__` block is responsible for constructing the
model with the spec's config and running one forward pass. Exit 0 = pass.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent.parent


def run(code_path: Path) -> dict:
    abs_path = code_path.resolve()
    proc = subprocess.run(
        [sys.executable, str(abs_path)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    ok = proc.returncode == 0
    return {
        "passed": ok,
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-400:],
        "stderr_tail": proc.stderr[-800:],
    }


if __name__ == "__main__":
    import json
    for p in [EVALS_DIR / "artifacts/baseline/generated.py",
              EVALS_DIR / "artifacts/mllens/generated.py"]:
        if p.exists():
            print(p.name, "→", json.dumps(run(p), indent=2))
