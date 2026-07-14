"""Lossless research-only values shared by forecasting experiments.

These contracts annotate native engine output without changing the product
release contracts.  In particular, a native score is not assumed to be a
probability and may use an unbounded, signed, ordinal, or engine-specific scale.
"""

from __future__ import annotations

import base64
import math
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, StrEnum
from fractions import Fraction
from typing import Any

from pydantic import BaseModel

from .canonical import stable_hash


@dataclass(frozen=True, slots=True)
class NativeScore:
    """One finite engine score together with its native scale identity."""

    value: int | float
    scale: str
    units: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise TypeError("native score value must be numeric")
        if not math.isfinite(self.value):
            raise ValueError("native score value must be finite")
        if not self.scale.strip():
            raise ValueError("native score scale is required")


class ResearchArtifactOrigin(StrEnum):
    ISSUANCE_LEDGER = "issuance_ledger"
    MANUAL = "manual"
    SYNTHETIC = "synthetic"


@dataclass(frozen=True, slots=True)
class ResearchSignalArtifact:
    """Checksum-sealed research signal bound to one issued forecast snapshot."""

    row_id: str
    subject_key: str
    forecast_snapshot_hash: str
    issued_at: datetime
    probability: float | None
    native_score: NativeScore | None
    direction: str | None
    origin: ResearchArtifactOrigin
    artifact_hash: str

    def __post_init__(self) -> None:
        if not self.row_id or not self.subject_key:
            raise ValueError("research artifact row and subject identities are required")
        if len(self.forecast_snapshot_hash) != 64 or any(
            char not in "0123456789abcdef" for char in self.forecast_snapshot_hash
        ):
            raise ValueError("research artifact requires a sha256 forecast snapshot hash")
        if self.issued_at.tzinfo is None:
            raise ValueError("research artifact issued_at must be timezone-aware")
        if self.probability is not None and (
            not math.isfinite(self.probability) or not 0 <= self.probability <= 1
        ):
            raise ValueError("research artifact probability must be between zero and one")
        if self.artifact_hash != stable_hash(_artifact_payload(self)):
            raise ValueError("research artifact hash does not match its immutable payload")

    @classmethod
    def seal(
        cls,
        *,
        row_id: str,
        subject_key: str,
        forecast_snapshot_hash: str,
        issued_at: datetime,
        probability: float | None,
        native_score: NativeScore | None,
        direction: str | None,
        origin: ResearchArtifactOrigin,
    ) -> ResearchSignalArtifact:
        payload = {
            "row_id": row_id,
            "subject_key": subject_key,
            "forecast_snapshot_hash": forecast_snapshot_hash,
            "issued_at": issued_at,
            "probability": probability,
            "native_score": native_score,
            "direction": direction,
            "origin": origin,
        }
        return cls(**payload, artifact_hash=stable_hash(payload))


def _artifact_payload(value: ResearchSignalArtifact) -> dict[str, Any]:
    return {
        "row_id": value.row_id,
        "subject_key": value.subject_key,
        "forecast_snapshot_hash": value.forecast_snapshot_hash,
        "issued_at": value.issued_at,
        "probability": value.probability,
        "native_score": value.native_score,
        "direction": value.direction,
        "origin": value.origin,
    }


def tolerant_raw_value(value: Any, *, _seen: set[int] | None = None) -> Any:
    """Deterministically represent arbitrary native values without raising.

    Unsupported objects are quarantined by type and public state. Memory-address
    reprs are deliberately excluded because they are not replay-stable.
    """

    seen = _seen if _seen is not None else set()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return {"__float__": "nan"}
        if math.isinf(value):
            return {"__float__": "positive_infinity" if value > 0 else "negative_infinity"}
        return value
    if isinstance(value, bytes):
        return {"__bytes_base64__": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime):
        return {"__datetime__": value.isoformat()}
    if isinstance(value, date):
        return {"__date__": value.isoformat()}
    if isinstance(value, Decimal):
        return {"__decimal__": str(value)}
    if isinstance(value, Fraction):
        return {
            "__fraction__": {
                "numerator": value.numerator,
                "denominator": value.denominator,
            }
        }
    if isinstance(value, Enum):
        return tolerant_raw_value(value.value, _seen=seen)
    if isinstance(value, BaseModel):
        return tolerant_raw_value(value.model_dump(mode="python"), _seen=seen)
    if is_dataclass(value) and not isinstance(value, type):
        return tolerant_raw_value(asdict(value), _seen=seen)

    identity = id(value)
    if identity in seen:
        return {"__cycle__": _type_name(value)}
    seen.add(identity)
    try:
        if isinstance(value, dict) and all(isinstance(key, str) for key in value):
            return {
                key: tolerant_raw_value(value[key], _seen=seen)
                for key in sorted(value)
            }
        if isinstance(value, dict):
            pairs = [
                (tolerant_raw_value(key, _seen=seen), tolerant_raw_value(item, _seen=seen))
                for key, item in value.items()
            ]
            return {
                "__mapping__": sorted(
                    ({"key": key, "value": item} for key, item in pairs),
                    key=lambda pair: stable_hash(pair["key"]),
                )
            }
        if isinstance(value, (list, tuple)):
            return [tolerant_raw_value(item, _seen=seen) for item in value]
        if isinstance(value, (set, frozenset)):
            items = [tolerant_raw_value(item, _seen=seen) for item in value]
            return {"__set__": sorted(items, key=stable_hash)}
        state = getattr(value, "__dict__", None)
        public_state = (
            {
                str(key): tolerant_raw_value(item, _seen=seen)
                for key, item in state.items()
                if not str(key).startswith("_")
            }
            if isinstance(state, dict)
            else {}
        )
        slots = getattr(type(value), "__slots__", ())
        if isinstance(slots, str):
            slots = (slots,)
        for name in slots:
            if str(name).startswith("_") or not hasattr(value, name):
                continue
            public_state[str(name)] = tolerant_raw_value(getattr(value, name), _seen=seen)
        return {"__unsupported_type__": _type_name(value), "state": public_state}
    except Exception as exc:  # hostile custom containers/properties remain quarantined
        return {
            "__unsupported_type__": _type_name(value),
            "capture_error_type": _type_name(exc),
        }
    finally:
        seen.discard(identity)


def _type_name(value: Any) -> str:
    cls = type(value)
    return f"{cls.__module__}.{cls.__qualname__}"
