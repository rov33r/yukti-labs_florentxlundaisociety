from __future__ import annotations

from typing import Any
from pydantic import ValidationError

from .models import ComponentManifest


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


def manifest_json_schema() -> dict:
    """Return the JSON Schema for ComponentManifest (for /api/schema endpoint)."""
    return ComponentManifest.model_json_schema()
