"""Truthful, compact narration for Person Timeline records.

The timeline intentionally keeps legacy engine output visibly separate from a
prospectively sealed forecast.  These helpers never turn a rule score into a
probability or silently add precision that was absent from the source record.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_SPACE = re.compile(r"\s+")


def clean_statement(value: object, *, fallback: str) -> str:
    """Return one readable statement without leaking blank or malformed prose."""

    text = _SPACE.sub(" ", str(value or "")).strip()
    if not text:
        return fallback
    if text[-1] not in ".?!":
        text += "."
    return text


def legacy_candidate_statement(prediction: Mapping[str, Any]) -> str:
    name = clean_statement(prediction.get("name"), fallback="Legacy engine candidate").rstrip(
        "."
    )
    manifestation = clean_statement(
        prediction.get("manifestation_text"),
        fallback="The legacy engine surfaced this chart-specific combination.",
    )
    return f"{name}: {manifestation}"


def legacy_identity_notice() -> str:
    return (
        "Migrated legacy engine inference. It was generated from existing chart rules "
        "and was not sealed before an outcome; it is not a prospective prediction."
    )


def temporal_precision_text(
    *, start: str, peak: str | None, end: str, native_resolution: str, tolerance: str
) -> str:
    peak_text = f" Peak: {peak}." if peak else " No narrower peak was produced."
    return (
        f"Native {native_resolution} interval: {start} to {end}.{peak_text} "
        f"Tolerance: {tolerance}."
    )


def evidence_summary(
    supporting: Sequence[Mapping[str, Any]], opposing: Sequence[Mapping[str, Any]]
) -> str:
    support_count = len(supporting)
    oppose_count = len(opposing)
    return (
        f"{support_count} supporting evidence item{'s' if support_count != 1 else ''}; "
        f"{oppose_count} opposing evidence item{'s' if oppose_count != 1 else ''}. "
        "Counts describe evidence rows, not probability."
    )


def observed_event_statement(title: str, description: str | None) -> str:
    title_text = clean_statement(title, fallback="Observed event").rstrip(".")
    if description:
        return f"{title_text}: {clean_statement(description, fallback='')}"
    return f"{title_text}."
