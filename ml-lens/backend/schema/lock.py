from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from .models import ComponentManifest


class LockedManifest(BaseModel):
    manifest: ComponentManifest
    content_hash: str = Field(..., description="SHA-256 of the manifest JSON (first 16 hex chars)")
    locked_at: str = Field(..., description="ISO-8601 UTC timestamp")
    schema_version: str = Field(default="1.0.0")


def lock_manifest(manifest: ComponentManifest) -> LockedManifest:
    """Freeze a manifest with a content hash and timestamp."""
    raw = manifest.model_dump_json(indent=None)
    content_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
    locked_at = datetime.now(timezone.utc).isoformat()
    return LockedManifest(
        manifest=manifest,
        content_hash=content_hash,
        locked_at=locked_at,
    )
