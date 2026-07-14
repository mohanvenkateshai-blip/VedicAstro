"""Stable identity and temporal-order provenance helpers for timeline records."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..identity import stable_hash
from .contracts import (
    EventDirection,
    MilestoneOrigin,
    MilestoneProvenance,
    TemporalOrderProof,
    TimelineMilestone,
    TimelineWindow,
    temporal_order_payload,
)


def stable_timeline_id(subject_reference_id: str, namespace: str = "person_timeline:v1") -> str:
    return f"timeline_{stable_hash({'namespace': namespace, 'subject': subject_reference_id})[:32]}"


def stable_record_id(prefix: str, payload: Any) -> str:
    """Return a deterministic, namespaced identifier without leaking payload content."""

    return f"{prefix}_{stable_hash(payload)[:32]}"


def build_milestone(
    *,
    timeline_id: str,
    subject_reference_id: str,
    origin: MilestoneOrigin,
    origin_record_id: str,
    canonical_event_id: str,
    original_label: str,
    title: str,
    window: TimelineWindow,
    created_at: datetime,
    provenance: MilestoneProvenance,
    description: str | None = None,
    direction: EventDirection = EventDirection.NOT_APPLICABLE,
    magnitude: Any | None = None,
    sealed_at: datetime | None = None,
    knowledge_cutoff_at: datetime | None = None,
    sealed_match_criteria: dict[str, Any] | None = None,
    sealed_match_criteria_hash: str | None = None,
    known_event_milestone_id: str | None = None,
    supersedes_milestone_id: str | None = None,
    native_score_refs: tuple[str, ...] = (),
    visibility: str = "private",
) -> TimelineMilestone:
    """Construct a milestone whose id is inseparable from its scientific origin."""

    milestone_id, origin_hash = TimelineMilestone.stable_identity(
        timeline_id=timeline_id,
        subject_reference_id=subject_reference_id,
        origin=origin,
        origin_record_id=origin_record_id,
        canonical_event_id=canonical_event_id,
    )
    return TimelineMilestone(
        milestone_id=milestone_id,
        timeline_id=timeline_id,
        subject_reference_id=subject_reference_id,
        origin=origin,
        origin_record_id=origin_record_id,
        origin_identity_hash=origin_hash,
        canonical_event_id=canonical_event_id,
        original_label=original_label,
        title=title,
        description=description,
        direction=direction,
        magnitude=magnitude,
        window=window,
        created_at=created_at,
        sealed_at=sealed_at,
        knowledge_cutoff_at=knowledge_cutoff_at,
        sealed_match_criteria=sealed_match_criteria,
        sealed_match_criteria_hash=sealed_match_criteria_hash,
        known_event_milestone_id=known_event_milestone_id,
        supersedes_milestone_id=supersedes_milestone_id,
        native_score_refs=native_score_refs,
        provenance=provenance,
        visibility=visibility,
    )


def temporal_order_proof(
    *,
    prediction_created_at: datetime,
    prediction_sealed_at: datetime | None,
    outcome_known_at: datetime | None,
) -> TemporalOrderProof:
    hash_payload = temporal_order_payload(
        prediction_created_at=prediction_created_at,
        prediction_sealed_at=prediction_sealed_at,
        outcome_known_at=outcome_known_at,
    )
    return TemporalOrderProof(
        prediction_created_at=prediction_created_at,
        prediction_sealed_at=prediction_sealed_at,
        outcome_known_at=outcome_known_at,
        proof_hash=stable_hash(hash_payload),
    )


def artifact_hash(value: Any) -> str:
    return stable_hash(value)
