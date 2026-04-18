"""Shared helpers for ML Lens evaluation.

Both baseline and ML Lens conditions must call Claude through the same surface
with identical model + decoding params. The only difference is the prompt.
"""
from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from openai import OpenAI


EVALS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = EVALS_DIR / "fixtures"
ARTIFACTS_DIR = EVALS_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Paper used for the head-to-head eval.
PAPER_ID = "2410.05258"

# Fixed decoding parameters — identical for both conditions.
MODEL_ID = os.environ.get("EVAL_MODEL", "minimax/minimax-m2.7")
MAX_TOKENS = 4000
TEMPERATURE = 0.0


def claude_client() -> OpenAI:
    """OpenRouter client that routes to real Claude models."""
    load_dotenv(EVALS_DIR.parent / "backend" / ".env")
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("No ANTHROPIC_API_KEY / OPENROUTER_API_KEY in env")
    return OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")


def call_claude(system: str, user: str) -> tuple[str, dict]:
    """Single blocking Claude call. Returns (raw_text, metadata)."""
    client = claude_client()
    resp = client.chat.completions.create(
        model=MODEL_ID,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = resp.choices[0].message.content or ""
    meta = {
        "model": MODEL_ID,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "usage": resp.usage.model_dump() if resp.usage else None,
    }
    return text, meta


# ── Artifact helpers ─────────────────────────────────────────────────────────

def load_paper_text() -> str:
    return (ARTIFACTS_DIR / "paper_text.txt").read_text()


def load_manifest() -> dict:
    return json.loads((FIXTURES_DIR / f"{PAPER_ID}.json").read_text())


def load_ground_truth_spec() -> dict:
    return json.loads((FIXTURES_DIR / "ground_truth_spec.json").read_text())


def extract_python_code(llm_output: str) -> str:
    """Strip markdown code fences if present, return pure Python source."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    return llm_output.strip()


def save_condition(name: str, code: str, prompt_user: str, prompt_system: str,
                   raw_response: str, meta: dict) -> dict:
    """Persist all artifacts for one condition to evals/artifacts/{name}/."""
    cond_dir = ARTIFACTS_DIR / name
    cond_dir.mkdir(exist_ok=True)
    (cond_dir / "generated.py").write_text(code)
    (cond_dir / "prompt_system.txt").write_text(prompt_system)
    (cond_dir / "prompt_user.txt").write_text(prompt_user)
    (cond_dir / "raw_response.txt").write_text(raw_response)
    (cond_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return {"dir": str(cond_dir), "code_path": str(cond_dir / "generated.py")}


# ── Code analysis helpers ────────────────────────────────────────────────────

def extract_module_classes(code: str) -> list[str]:
    """Return the class names that subclass nn.Module (direct or indirect)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                src = ast.unparse(base) if hasattr(ast, "unparse") else ""
                if "Module" in src:
                    result.append(node.name)
                    break
    return result


def contains_any(haystack: str, needles: Iterable[str]) -> bool:
    low = haystack.lower()
    return any(n.lower() in low for n in needles)


@dataclass
class GenerationResult:
    name: str
    code_path: str
    classes: list[str]
    meta: dict
