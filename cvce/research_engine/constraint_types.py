"""Shared progressive-constraint identities without matrix/trace import cycles."""

from __future__ import annotations

from enum import StrEnum
from itertools import combinations


class ConstraintLayer(StrEnum):
    PROMISE = "promise"
    PERIOD = "period"
    SLOW_TRANSIT = "slow_transit"
    FAST_TRIGGER = "fast_trigger"


def all_constraint_variants(
    *, include_empty: bool = True
) -> tuple[tuple[ConstraintLayer, ...], ...]:
    """Return all 2^4 progressive combinations in deterministic order."""

    layers = tuple(ConstraintLayer)
    variants: list[tuple[ConstraintLayer, ...]] = [()] if include_empty else []
    for size in range(1, len(layers) + 1):
        variants.extend(combinations(layers, size))
    return tuple(variants)
