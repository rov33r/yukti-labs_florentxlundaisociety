"""Generate evals/REPORT.md from artifacts/results.json.

The markdown report contains:
- Paper + model metadata
- Per-axis side-by-side results (baseline vs ML Lens)
- ΔH (hallucination delta) per axis and composite
- Links to both generated .py files, both prompts, both raw responses
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from common import ARTIFACTS_DIR, EVALS_DIR, MODEL_ID, PAPER_ID


def _load_usage(name: str) -> dict:
    p = ARTIFACTS_DIR / name / "meta.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def _yesno(b: bool | None) -> str:
    if b is None:
        return "—"
    return "✅" if b else "❌"


def _delta_pct(baseline_val: float, mllens_val: float) -> str:
    if baseline_val == 0:
        return "n/a" if mllens_val == 0 else "+∞"
    pct = (baseline_val - mllens_val) / baseline_val * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.0f}%"


def write_report(results: dict[str, Any]) -> Path:
    b = results.get("baseline", {})
    m = results.get("mllens", {})

    b_runnable = bool(b.get("runnable", {}).get("passed"))
    m_runnable = bool(m.get("runnable", {}).get("passed"))

    b_shapes = bool(b.get("shapes", {}).get("passed"))
    m_shapes = bool(m.get("shapes", {}).get("passed"))

    b_drift_errs = int(b.get("drift", {}).get("drift_errors", 0))
    m_drift_errs = int(m.get("drift", {}).get("drift_errors", 0))

    b_missing = b.get("drift", {}).get("missing_buckets", []) or []
    m_missing = m.get("drift", {}).get("missing_buckets", []) or []

    b_classes = b.get("drift", {}).get("classes", []) or []
    m_classes = m.get("drift", {}).get("classes", []) or []

    b_top = b.get("shapes", {}).get("top_class", "—")
    m_top = m.get("shapes", {}).get("top_class", "—")
    b_shape = b.get("shapes", {}).get("actual_shape", "—")
    m_shape = m.get("shapes", {}).get("actual_shape", "—")
    expected_shape = b.get("shapes", {}).get("expected_shape") or \
                     m.get("shapes", {}).get("expected_shape") or "—"

    b_usage = _load_usage("baseline").get("usage") or {}
    m_usage = _load_usage("mllens").get("usage") or {}

    report_lines = [
        f"# ML Lens Evaluation Report",
        "",
        f"**Paper:** [{PAPER_ID}](https://arxiv.org/abs/{PAPER_ID}) — Differential Transformer (DIFF Transformer)",
        f"**Model:** `{MODEL_ID}` (same for both conditions)",
        f"**Decoding:** temperature=0.0, single call per condition",
        "",
        "## Conditions",
        "",
        "- **Baseline** — Claude receives only the paper text and the output contract.",
        "- **ML Lens** — Claude receives the same paper text, the same output contract, PLUS the locked `ComponentManifest` JSON and the `TraversalTrace` JSON produced by the ML Lens pipeline.",
        "",
        "Both conditions are identical on model, decoding params, and ask. The only variable is the skill context injected into the ML Lens prompt.",
        "",
        "## Results",
        "",
        "| Axis | Baseline | ML Lens | ΔH |",
        "|------|----------|---------|----|",
        f"| Runnable (`python generated.py` exit 0) | {_yesno(b_runnable)} | {_yesno(m_runnable)} | {'+100%' if (m_runnable and not b_runnable) else ('0%' if b_runnable == m_runnable else '-100%')} |",
        f"| Shape correct (top-level forward) | {_yesno(b_shapes)} | {_yesno(m_shapes)} | {'+100%' if (m_shapes and not b_shapes) else ('0%' if b_shapes == m_shapes else '-100%')} |",
        f"| Drift errors (missing buckets + extras) | {b_drift_errs} | {m_drift_errs} | {_delta_pct(b_drift_errs, m_drift_errs)} |",
        f"| Missing architectural buckets | {len(b_missing)}: {', '.join(b_missing) or '—'} | {len(m_missing)}: {', '.join(m_missing) or '—'} | — |",
        "",
        "### Top-level forward pass",
        "",
        f"| | Baseline | ML Lens |",
        f"|---|---|---|",
        f"| Top-level class | `{b_top}` | `{m_top}` |",
        f"| Actual output shape | `{b_shape}` | `{m_shape}` |",
        f"| Expected output shape | `{expected_shape}` | `{expected_shape}` |",
        "",
        "### Generated `nn.Module` classes",
        "",
        f"**Baseline** ({len(b_classes)}): " + (", ".join(f"`{c}`" for c in b_classes) or "—"),
        "",
        f"**ML Lens** ({len(m_classes)}): " + (", ".join(f"`{c}`" for c in m_classes) or "—"),
        "",
        "### Token usage",
        "",
        "| | Baseline | ML Lens |",
        "|---|---|---|",
        f"| Input tokens | {b_usage.get('prompt_tokens', '—')} | {m_usage.get('prompt_tokens', '—')} |",
        f"| Output tokens | {b_usage.get('completion_tokens', '—')} | {m_usage.get('completion_tokens', '—')} |",
        "",
        "## Verbatim prompts",
        "",
        "All artifacts for reproduction:",
        "",
        "- Baseline system prompt — `artifacts/baseline/prompt_system.txt`",
        "- Baseline user prompt — `artifacts/baseline/prompt_user.txt`",
        "- Baseline raw response — `artifacts/baseline/raw_response.txt`",
        "- Baseline generated code — `artifacts/baseline/generated.py`",
        "- ML Lens system prompt — `artifacts/mllens/prompt_system.txt`",
        "- ML Lens user prompt — `artifacts/mllens/prompt_user.txt`",
        "- ML Lens raw response — `artifacts/mllens/raw_response.txt`",
        "- ML Lens generated code — `artifacts/mllens/generated.py`",
        "- Locked manifest — `fixtures/2410.05258.json`",
        "- Traversal trace — `artifacts/traversal_trace.json`",
        "",
        "## Interpretation",
        "",
        "*ΔH reads as \"percent reduction in errors vs baseline\".* Positive is good.",
        "",
        "- Runnable / Shape: binary per axis. A flip from ❌ to ✅ is reported as +100%.",
        "- Drift: `(missing_buckets + extra_classes)`. Lower is better. ΔH = (baseline − mllens) / baseline × 100%.",
        "",
        "The central claim is that injecting a paper-specific schema into the prompt reduces hallucination when implementing an unfamiliar paper. This report either supports or contradicts that claim on one paper — Differential Transformer (2410.05258), published 2024-10, chosen because it is a focused attention variant (λ·softmax subtraction) that baseline Claude is likely to collapse into vanilla MHA.",
        "",
    ]

    out = EVALS_DIR / "REPORT.md"
    out.write_text("\n".join(report_lines))
    print(f"[report] wrote {out}")
    return out


if __name__ == "__main__":
    results = json.loads((ARTIFACTS_DIR / "results.json").read_text())
    write_report(results)
