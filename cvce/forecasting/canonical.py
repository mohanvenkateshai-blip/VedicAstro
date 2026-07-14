"""Canonical serialization and identifiers for reproducible forecast artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


def canonical_value(value: Any) -> Any:
    """Return a JSON-compatible value with deterministic ordering and formatting."""

    if isinstance(value, BaseModel):
        return canonical_value(value.model_dump(mode="json", exclude_none=False))
    if is_dataclass(value) and not isinstance(value, type):
        return canonical_value(asdict(value))
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): canonical_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [canonical_value(item) for item in value]
    if isinstance(value, set):
        items = [canonical_value(item) for item in value]
        return sorted(items, key=lambda item: canonical_json(item))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize a value using the pipeline's stable JSON representation."""

    return json.dumps(
        canonical_value(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def stable_hash(value: Any) -> str:
    """Return the SHA-256 digest of canonical JSON input."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(namespace: str, value: Any) -> str:
    """Create a readable, deterministic identifier without truncating the digest."""

    return f"{namespace}_{stable_hash(value)}"
