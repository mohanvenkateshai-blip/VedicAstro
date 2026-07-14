"""Frozen, event-specific and tolerance-aware timeline matching."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from ..identity import stable_hash
from .contracts import TimelineMilestone, TimelineModel


class MatchDisposition(StrEnum):
    MATCH = "match"
    PARTIAL_MATCH = "partial_match"
    NO_MATCH = "no_match"


class MatchCriteria(TimelineModel):
    criteria_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    canonical_event_id: str = Field(min_length=1)
    accepted_event_ids: tuple[str, ...] = ()
    require_peak_within_actual: bool = False
    minimum_overlap_ratio: float = Field(default=0.01, gt=0.0, le=1.0)
    allow_tolerance: bool = True
    partial_overlap_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    criteria_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @staticmethod
    def hash_payload(
        *,
        criteria_id: str,
        version: str,
        canonical_event_id: str,
        accepted_event_ids: tuple[str, ...] = (),
        require_peak_within_actual: bool = False,
        minimum_overlap_ratio: float = 0.01,
        allow_tolerance: bool = True,
        partial_overlap_ratio: float = 0.0,
    ) -> dict[str, object]:
        return {
            "criteria_id": criteria_id,
            "version": version,
            "canonical_event_id": canonical_event_id,
            "accepted_event_ids": accepted_event_ids,
            "require_peak_within_actual": require_peak_within_actual,
            "minimum_overlap_ratio": minimum_overlap_ratio,
            "allow_tolerance": allow_tolerance,
            "partial_overlap_ratio": partial_overlap_ratio,
        }

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        payload = self.hash_payload(
            criteria_id=self.criteria_id,
            version=self.version,
            canonical_event_id=self.canonical_event_id,
            accepted_event_ids=self.accepted_event_ids,
            require_peak_within_actual=self.require_peak_within_actual,
            minimum_overlap_ratio=self.minimum_overlap_ratio,
            allow_tolerance=self.allow_tolerance,
            partial_overlap_ratio=self.partial_overlap_ratio,
        )
        if self.criteria_hash != stable_hash(payload):
            raise ValueError("criteria_hash does not match frozen matching criteria")
        if self.partial_overlap_ratio > self.minimum_overlap_ratio:
            raise ValueError("partial overlap threshold cannot exceed full-match threshold")
        return self

    @classmethod
    def freeze(cls, **values: object) -> Self:
        if "accepted_event_ids" in values:
            values["accepted_event_ids"] = tuple(values["accepted_event_ids"] or ())  # type: ignore[arg-type]
        payload = cls.hash_payload(**values)  # type: ignore[arg-type]
        return cls(**payload, criteria_hash=stable_hash(payload))  # type: ignore[arg-type]


class MatchResult(TimelineModel):
    disposition: MatchDisposition
    criteria_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_compatible: bool
    overlap_ratio: float = Field(ge=0.0, le=1.0)
    peak_within_actual: bool | None
    reasons: tuple[str, ...]


def match_milestones(
    prediction: TimelineMilestone,
    observed: TimelineMilestone,
    criteria: MatchCriteria,
) -> MatchResult:
    from .contracts import MilestoneOrigin

    if prediction.origin not in {
        MilestoneOrigin.PROSPECTIVE_PREDICTION,
        MilestoneOrigin.RETROSPECTIVE_HYPOTHESIS,
    }:
        raise ValueError("prediction must retain prospective or retrospective identity")
    if observed.origin not in {
        MilestoneOrigin.OBSERVED_EVENT,
        MilestoneOrigin.IMPORTED_HISTORY,
    }:
        raise ValueError("outcome must retain observed or imported-history identity")
    if prediction.timeline_id != observed.timeline_id:
        raise ValueError("prediction and outcome must belong to the same timeline")
    if prediction.subject_reference_id != observed.subject_reference_id:
        raise ValueError("prediction and outcome must belong to the same protected subject")
    accepted = {criteria.canonical_event_id, *criteria.accepted_event_ids}
    event_compatible = (
        prediction.canonical_event_id == criteria.canonical_event_id
        and observed.canonical_event_id in accepted
    )
    tolerance = prediction.window.tolerance
    before = tolerance.before_seconds if criteria.allow_tolerance else 0
    after = tolerance.after_seconds if criteria.allow_tolerance else 0
    predicted_start = prediction.window.start_at - timedelta(seconds=before)
    predicted_end = prediction.window.end_at + timedelta(seconds=after)
    actual_start = observed.window.start_at
    actual_end = observed.window.end_at
    overlap_start = max(predicted_start, actual_start)
    overlap_end = min(predicted_end, actual_end)
    actual_seconds = (actual_end - actual_start).total_seconds()
    predicted_seconds = (predicted_end - predicted_start).total_seconds()
    if actual_seconds == 0:
        overlap_ratio = 1.0 if predicted_start <= actual_start <= predicted_end else 0.0
        has_overlap = overlap_ratio == 1.0
    elif predicted_seconds == 0:
        overlap_ratio = 1.0 if actual_start <= predicted_start <= actual_end else 0.0
        has_overlap = overlap_ratio == 1.0
    else:
        overlap_seconds = max(0.0, (overlap_end - overlap_start).total_seconds())
        overlap_ratio = min(1.0, overlap_seconds / actual_seconds)
        has_overlap = overlap_seconds > 0
    peak = prediction.window.peak_at
    peak_within_actual = None if peak is None else actual_start <= peak <= actual_end
    reasons: list[str] = []
    if not event_compatible:
        reasons.append("event taxonomy does not satisfy the frozen criteria")
    if overlap_ratio < criteria.minimum_overlap_ratio:
        reasons.append("temporal overlap is below the full-match threshold")
    if criteria.require_peak_within_actual and peak_within_actual is not True:
        reasons.append("predicted peak is not inside the observed interval")
    full = (
        event_compatible
        and overlap_ratio >= criteria.minimum_overlap_ratio
        and (not criteria.require_peak_within_actual or peak_within_actual is True)
    )
    partial = event_compatible and overlap_ratio >= criteria.partial_overlap_ratio and has_overlap
    disposition = (
        MatchDisposition.MATCH
        if full
        else MatchDisposition.PARTIAL_MATCH
        if partial
        else MatchDisposition.NO_MATCH
    )
    return MatchResult(
        disposition=disposition,
        criteria_hash=criteria.criteria_hash,
        event_compatible=event_compatible,
        overlap_ratio=overlap_ratio,
        peak_within_actual=peak_within_actual,
        reasons=tuple(reasons),
    )
