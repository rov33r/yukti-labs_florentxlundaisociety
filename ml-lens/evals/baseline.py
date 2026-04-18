"""Baseline condition: bare Claude given the paper text, no schema grounding.

Same model, same decoding params, same output contract as the ML Lens runner.
The only difference: the user message contains only the paper text + the ask.
"""
from __future__ import annotations

from common import (
    call_claude,
    extract_python_code,
    load_ground_truth_spec,
    load_paper_text,
    save_condition,
)

SYSTEM_PROMPT = (
    "You are an ML engineer implementing research papers in PyTorch. "
    "Output ONLY a single self-contained Python file. No prose, no explanations "
    "outside code comments. The file must define one or more `torch.nn.Module` "
    "classes and a top-level model class that implements the paper's full "
    "architecture. The code must be runnable: `python file.py` should define "
    "the module without errors."
)

USER_TEMPLATE = """Implement the following paper as a single PyTorch file.

Requirements:
- Define all components as `torch.nn.Module` subclasses.
- Define a top-level model class whose `forward(token_ids)` accepts a LongTensor
  of shape `(B, T)` and returns logits of shape `(B, T, vocab_size)`.
- Use these exact constructor kwargs on the top-level class: `d_model`, `n_heads`,
  `n_layers`, `vocab_size`.
- Include `if __name__ == "__main__":` that constructs the model with
  `d_model={d_model}`, `n_heads={n_heads}`, `n_layers={n_layers}`,
  `vocab_size={vocab_size}` and runs one forward pass on
  `torch.randint(0, {vocab_size}, ({B}, {T}))`.
- No external dependencies beyond `torch`.
- Output ONLY the Python code inside a single ```python ... ``` fence.

Paper text:
<<<
{paper_text}
>>>
"""


def build_prompts() -> tuple[str, str]:
    spec = load_ground_truth_spec()["test_config"]
    paper = load_paper_text()
    user = USER_TEMPLATE.format(
        paper_text=paper,
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
    print(f"[baseline] prompt chars: system={len(system)} user={len(user)}")
    raw, meta = call_claude(system, user)
    code = extract_python_code(raw)
    info = save_condition("baseline", code, user, system, raw, meta)
    print(f"[baseline] saved → {info['code_path']}")
    print(f"[baseline] usage: {meta.get('usage')}")


if __name__ == "__main__":
    main()
