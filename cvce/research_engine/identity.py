"""Deterministic serialization and content identity for research artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def canonical_json(value: BaseModel | Any) -> str:
    """Serialize JSON-compatible data without platform- or insertion-order drift."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", round_trip=True)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def stable_hash(value: BaseModel | Any) -> str:
    """Return the SHA-256 identity of canonical serialized content."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
