"""Drift test: are the right architectural components present?

Uses `required_module_keywords` buckets from ground_truth_spec.json. For each
bucket (attention, feedforward, norm, position_encoding, output_head, looped),
we count a bucket as "covered" if ANY generated class name contains one of the
keywords. Drift score = (missing buckets) + (extras over manifest-known classes).

Rationale: class naming is free — we don't demand exact names, we demand the
architectural category is represented. Missing buckets = hallucination by
omission. Extras beyond the manifest = hallucination by addition.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = EVALS_DIR / "fixtures"


def _extract_module_classes(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                src = ast.unparse(base) if hasattr(ast, "unparse") else ""
                if "Module" in src:
                    names.append(node.name)
                    break
    return names


def run(code_path: Path) -> dict:
    spec = json.loads((FIXTURES_DIR / "ground_truth_spec.json").read_text())
    buckets: dict[str, list[str]] = spec["required_module_keywords"]
    code = code_path.read_text()
    classes = _extract_module_classes(code)
    low_names = [c.lower() for c in classes]

    covered: dict[str, str | None] = {}
    for bucket, keywords in buckets.items():
        hit = next(
            (name for name, low in zip(classes, low_names)
             if any(k.lower() in low for k in keywords)),
            None,
        )
        covered[bucket] = hit

    missing = [b for b, hit in covered.items() if hit is None]

    # Extras = classes that don't map to any required bucket
    matched: set[str] = {hit for hit in covered.values() if hit}
    extras = [c for c in classes if c not in matched]

    drift_errors = len(missing) + len(extras)

    return {
        "passed": len(missing) == 0,
        "total_classes": len(classes),
        "classes": classes,
        "buckets_covered": covered,
        "missing_buckets": missing,
        "extra_classes": extras,
        "drift_errors": drift_errors,
    }


if __name__ == "__main__":
    for p in [EVALS_DIR / "artifacts/baseline/generated.py",
              EVALS_DIR / "artifacts/mllens/generated.py"]:
        if p.exists():
            print(p, "→", json.dumps(run(p), indent=2))
