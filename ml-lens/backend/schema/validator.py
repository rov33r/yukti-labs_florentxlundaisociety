from __future__ import annotations

from typing import Any
from pydantic import ValidationError

from .models import ComponentManifest

_CROSS_ATTN_SIGNALS = {"cross", "encoder_decoder", "encoder-decoder", "cross_attention"}
_ENC_SIGNALS = {"encoder"}
_DEC_SIGNALS = {"decoder"}


class SchemaValidationError(Exception):
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(f"Schema validation failed with {len(errors)} error(s)")


def validate_manifest(data: Any) -> ComponentManifest:
    """Validate raw data (dict or JSON string) against ComponentManifest schema.

    Raises SchemaValidationError with structured error list on failure.
    """
    try:
        if isinstance(data, str):
            return ComponentManifest.model_validate_json(data)
        return ComponentManifest.model_validate(data)
    except ValidationError as exc:
        raise SchemaValidationError(exc.errors()) from exc


def check_graph_structure(manifest: ComponentManifest) -> list[str]:
    """Return a list of structural warnings for the manifest's dependency graph.

    Does not raise — callers decide whether to surface or ignore warnings.
    Current checks:
      1. Cross-attention components must have upstreams from both encoder and decoder sides.
      2. Non-root components must have at least one upstream (disconnected nodes).
    """
    warnings: list[str] = []
    comps = manifest.components
    if not comps:
        return warnings

    ids = {c.id for c in comps}
    enc_ids = {c.id for c in comps if
               any(s in c.id.lower() or s in c.name.lower() for s in _ENC_SIGNALS) and
               not any(s in c.id.lower() or s in c.name.lower() for s in _DEC_SIGNALS)}
    dec_ids = {c.id for c in comps if
               any(s in c.id.lower() or s in c.name.lower() for s in _DEC_SIGNALS)}

    is_enc_dec = bool(enc_ids and dec_ids)

    for c in comps:
        # Check 1: non-root components must have at least one valid upstream
        if c.depends_on:
            bad = [d for d in c.depends_on if d not in ids]
            if bad:
                warnings.append(f"Component '{c.id}' depends_on unknown ids: {bad}")

        # Check 2: cross-attention in enc-dec architectures must bridge both sides
        if is_enc_dec and c.kind in ("multi_head_attention", "attention"):
            is_cross = any(sig in c.id.lower() or sig in c.name.lower()
                           for sig in _CROSS_ATTN_SIGNALS)
            if is_cross:
                has_enc_upstream = any(d in enc_ids for d in c.depends_on)
                has_dec_upstream = any(d in dec_ids or d not in enc_ids
                                       for d in c.depends_on)
                if not has_enc_upstream:
                    warnings.append(
                        f"Cross-attention '{c.id}' is missing an encoder-side upstream "
                        f"(depends_on={c.depends_on}). The encoder output (Keys+Values) "
                        f"must be listed in depends_on alongside the decoder query input."
                    )

    return warnings


def manifest_json_schema() -> dict:
    """Return the JSON Schema for ComponentManifest (for /api/schema endpoint)."""
    return ComponentManifest.model_json_schema()
