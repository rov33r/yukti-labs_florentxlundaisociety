"""Shape test: instantiate the top-level module, feed a known input, check output shape.

We don't assume a specific top-level class name — we scan the generated file's
Module subclasses and pick the one whose class name best matches the expected
top-level keywords (from ground_truth_spec.json). We then construct it with the
spec's kwargs and run a forward pass. Pass = output shape == (B, T, vocab_size).
"""
from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = EVALS_DIR / "fixtures"


def _load_spec() -> dict:
    return json.loads((FIXTURES_DIR / "ground_truth_spec.json").read_text())


def _import_module(code_path: Path):
    spec = importlib.util.spec_from_file_location("gen_module", str(code_path))
    mod = importlib.util.module_from_spec(spec)
    # prevent __main__ block from running on import
    sys.modules["gen_module"] = mod
    src = code_path.read_text()
    src_no_main = _strip_main_block(src)
    exec(compile(src_no_main, str(code_path), "exec"), mod.__dict__)
    return mod


def _strip_main_block(src: str) -> str:
    lines = src.splitlines()
    out, skip_indent = [], None
    for line in lines:
        if skip_indent is not None:
            if line.strip() == "" or line.startswith(" ") or line.startswith("\t"):
                continue
            skip_indent = None
        if line.strip().startswith("if __name__"):
            skip_indent = 0
            continue
        out.append(line)
    return "\n".join(out)


def _pick_top_class(mod, keywords: list[str]) -> type | None:
    """Pick the class most likely to be the top-level model.

    Strong signal: __init__ signature takes both `n_layers` and `vocab_size`.
    Tiebreak: keyword hits, then penalise names ending in Layer/Block, then
    prefer shorter names (DiffTransformer over DiffTransformerLayer).
    """
    try:
        import torch.nn as nn
        import inspect
    except ImportError:
        return None
    candidates: list[tuple[int, int, int, int, type]] = []
    for name, obj in vars(mod).items():
        if not isinstance(obj, type):
            continue
        if not issubclass(obj, nn.Module) or obj is nn.Module:
            continue
        try:
            sig = inspect.signature(obj.__init__)
            params = set(sig.parameters.keys())
        except (TypeError, ValueError):
            params = set()
        top_marker = int(("n_layers" in params) and ("vocab_size" in params))
        kw_hits = sum(1 for k in keywords if k.lower() in name.lower())
        nonlayer = int(not name.endswith(("Layer", "Block", "Decoder", "Encoder")))
        short_bonus = -len(name)
        candidates.append((top_marker, kw_hits, nonlayer, short_bonus, obj))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], -x[1], -x[2], -x[3]))
    return candidates[0][-1]


def run(code_path: Path) -> dict:
    spec = _load_spec()
    cfg = spec["test_config"]
    kw = spec["expected_top_module_keywords"]
    try:
        import torch
        mod = _import_module(code_path)
        cls = _pick_top_class(mod, kw)
        if cls is None:
            return {"passed": False, "error": "no nn.Module subclass found"}
        kwargs = dict(
            d_model=cfg["d_model"],
            n_heads=cfg["n_heads"],
            n_layers=cfg["n_layers"],
            vocab_size=cfg["vocab_size"],
        )
        if "T_max" in cfg:
            kwargs["T_max"] = cfg["T_max"]
        # Drop kwargs the top class doesn't declare
        import inspect
        sig = inspect.signature(cls.__init__)
        accepted = set(sig.parameters.keys())
        kwargs = {k: v for k, v in kwargs.items() if k in accepted}
        model = cls(**kwargs)
        model.eval()
        tok = torch.randint(0, cfg["vocab_size"], (cfg["batch_size"], cfg["seq_len"]))
        with torch.no_grad():
            out = model(tok)
        # Accept a tuple (logits, ...) or a tensor
        if isinstance(out, tuple):
            out = out[0]
        if hasattr(out, "logits"):
            out = out.logits
        shape = tuple(out.shape)
        expected = (cfg["batch_size"], cfg["seq_len"], cfg["vocab_size"])
        return {
            "passed": shape == expected,
            "top_class": cls.__name__,
            "actual_shape": shape,
            "expected_shape": expected,
        }
    except Exception as e:
        return {
            "passed": False,
            "error": f"{type(e).__name__}: {e}",
            "traceback_tail": traceback.format_exc()[-600:],
        }


if __name__ == "__main__":
    import json as _j
    for p in [EVALS_DIR / "artifacts/baseline/generated.py",
              EVALS_DIR / "artifacts/mllens/generated.py"]:
        if p.exists():
            print(p, "→", _j.dumps(run(p), indent=2))
