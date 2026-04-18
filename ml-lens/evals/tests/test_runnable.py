"""Runnable test: does `python generated.py` exit cleanly?

The generated file's `__main__` block is responsible for constructing the
model with the spec's config and running one forward pass. Exit 0 = pass.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(code_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(code_path)],
        capture_output=True,
        text=True,
        timeout=90,
        cwd=code_path.parent,
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
    for p in [Path("artifacts/baseline/generated.py"), Path("artifacts/mllens/generated.py")]:
        if p.exists():
            print(p, "→", json.dumps(run(p), indent=2))
