"""ML Lens condition: Claude + locked manifest + traversal trace.

Identical prompt framing to baseline.py except the user message also contains
the ML Lens skill context: the locked ComponentManifest and the traversal
trace, both as JSON, wrapped in XML-style tags. This is the minimum viable
"skill bundle" — the same artifacts a user would export to constrain their
own Claude workflow.
"""
from __future__ import annotations

import json

from common import (
    ARTIFACTS_DIR,
    call_claude,
    extract_python_code,
    load_ground_truth_spec,
    load_manifest,
    load_paper_text,
    save_condition,
)

SYSTEM_PROMPT = (
    "You are an ML engineer implementing research papers in PyTorch. "
    "You are given a verified ComponentManifest (locked schema) and a "
    "traversal trace extracted from the paper. These artifacts are the "
    "ground truth — your implementation MUST match the manifest's component "
    "names, tensor contracts, and invariants. Do not invent components that "
    "are not in the manifest. Do not omit components that are in the manifest. "
    "Output ONLY a single self-contained Python file. No prose outside code "
    "comments. The file must define one or more `torch.nn.Module` classes and "
    "a top-level model class that implements the paper's full architecture."
)

USER_TEMPLATE = """Implement the following paper as a single PyTorch file,
strictly grounded to the provided manifest and traversal trace.

Requirements:
- Each component in `<manifest>.components` must map to a `nn.Module` class.
- Honor every invariant in `<manifest>.invariants` (especially weight sharing
  across recurrent steps and causal masking).
- Honor every tensor contract in `<manifest>.tensor_contracts`.
- Top-level model `forward(token_ids)` accepts a LongTensor `(B, T)` and
  returns logits of shape `(B, T, vocab_size)`.
- Use these exact constructor kwargs on the top-level class: `d_model`, `n_heads`,
  `n_layers`, `vocab_size`.
- Include `if __name__ == "__main__":` that constructs the model with
  `d_model={d_model}`, `n_heads={n_heads}`, `n_layers={n_layers}`,
  `vocab_size={vocab_size}` and runs one forward pass on
  `torch.randint(0, {vocab_size}, ({B}, {T}))`.
- No external dependencies beyond `torch`.
- Output ONLY the Python code inside a single ```python ... ``` fence.

<manifest>
{manifest_json}
</manifest>

<traversal_trace>
{trace_json}
</traversal_trace>

<paper_text>
{paper_text}
</paper_text>
"""


def _load_trace() -> dict:
    return json.loads((ARTIFACTS_DIR / "traversal_trace.json").read_text())


def build_prompts() -> tuple[str, str]:
    spec = load_ground_truth_spec()["test_config"]
    paper = load_paper_text()
    manifest = load_manifest()
    trace = _load_trace()
    user = USER_TEMPLATE.format(
        paper_text=paper,
        manifest_json=json.dumps(manifest, indent=2),
        trace_json=json.dumps(trace, indent=2),
        B=spec["batch_size"],
        T=spec["seq_len"],
        d_model=spec["d_model"],
        n_heads=spec["n_heads"],
        n_layers=spec["n_layers"],
        vocab_size=spec["vocab_size"],
    )
    return SYSTEM_PROMPT, user


def main() -> None:
    system, user = build_prompts()
    print(f"[mllens] prompt chars: system={len(system)} user={len(user)}")
    raw, meta = call_claude(system, user)
    code = extract_python_code(raw)
    info = save_condition("mllens", code, user, system, raw, meta)
    print(f"[mllens] saved → {info['code_path']}")
    print(f"[mllens] usage: {meta.get('usage')}")


if __name__ == "__main__":
    main()
