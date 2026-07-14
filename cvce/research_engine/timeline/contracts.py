"""Immutable contracts for a person's auditable event and prediction timeline."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from ..identity import stable_hash

_HASH = r"^[0-9a-f]{64}$"
_SUBJECT_REF = r"^(?:subj_[0-9a-f]{16,64}|enc_[A-Za-z0-9_-]{16,})$"


class TimelineModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class MilestoneOrigin(StrEnum):
    PROSPECTIVE_PREDICTION = "prospective_prediction"
    OBSERVED_EVENT = "observed_event"
    RETROSPECTIVE_HYPOTHESIS = "retrospective_hypothesis"
    IMPORTED_HISTORY = "imported_history"
    ENGINE_INFERENCE = "engine_inference"


class SubjectProtection(StrEnum):
    DEIDENTIFIED = "deidentified"
    ENCRYPTED = "encrypted"


class TemporalResolution(StrEnum):
    INSTANT = "instant"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    INTERVAL = "interval"
    TECHNIQUE_NATIVE = "technique_native"


class EventDirection(StrEnum):
    FAVOURABLE = "favourable"
    UNFAVOURABLE = "unfavourable"
    MIXED = "mixed"
    NEUTRAL = "neutral"
    NOT_APPLICABLE = "not_applicable"


class LinkRelation(StrEnum):
    PREDICTED = "predicted"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    MATCHED = "matched"
    PARTIAL_MATCH = "partial_match"
    UNRELATED = "unrelated"


class EvidenceRole(StrEnum):
    NATAL_PROMISE = "natal_promise"
    ACTIVATION = "activation"
    TRIGGER = "trigger"
    SUPPORT = "support"
    OPPOSITION = "opposition"
    CONTEXT = "context"


class ResolutionStatus(StrEnum):
    HIT = "hit"
    PARTIAL_HIT = "partial_hit"
    MISS = "miss"
    FALSE_ALARM = "false_alarm"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class SubjectReference(TimelineModel):
    """Opaque reference only; raw names or birth details cannot satisfy this contract."""

    reference_id: str = Field(pattern=_SUBJECT_REF)
    protection: SubjectProtection
    key_id: str | None = None

    @model_validator(mode="after")
    def validate_protection(self) -> Self:
        if self.protection is SubjectProtection.ENCRYPTED and not self.key_id:
            raise ValueError("encrypted subject references require a key_id")
        if self.protection is SubjectProtection.DEIDENTIFIED and self.key_id is not None:
            raise ValueError("deidentified subject references cannot expose an encryption key id")
        return self


class TemporalTolerance(TimelineModel):
    before_seconds: int = Field(default=0, ge=0)
    after_seconds: int = Field(default=0, ge=0)
    native_label: str = Field(min_length=1)


class TimelineWindow(TimelineModel):
    start_at: datetime
    peak_at: datetime | None = None
    end_at: datetime
    native_resolution: TemporalResolution
    native_resolution_label: str = Field(min_length=1)
    tolerance: TemporalTolerance

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        values = (self.start_at, self.end_at, self.peak_at)
        if any(value is not None and value.tzinfo is None for value in values):
            raise ValueError("timeline window timestamps must be timezone-aware")
        if self.end_at < self.start_at:
            raise ValueError("end_at cannot precede start_at")
        if self.peak_at is not None and not self.start_at <= self.peak_at <= self.end_at:
            raise ValueError("peak_at must fall within the original interval")
        return self


class MilestoneProvenance(TimelineModel):
    actor_id: str = Field(min_length=1)
    engine_version: str | None = None
    run_id: str | None = None
    release_id: str | None = None
    input_snapshot_hash: str | None = Field(default=None, pattern=_HASH)
    calculation_hash: str | None = Field(default=None, pattern=_HASH)
    rule_pack_versions: dict[str, str] = Field(default_factory=dict)
    source_ids: tuple[str, ...] = ()
    citation_ids: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()


class PersonTimeline(TimelineModel):
    timeline_id: str = Field(min_length=1)
    subject: SubjectReference
    created_at: datetime
    prediction_release_versions: tuple[str, ...] = ()
    outcome_ledger_version: str | None = None

    @model_validator(mode="after")
    def validate_timestamp(self) -> Self:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self


class TimelineMilestone(TimelineModel):
    milestone_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    subject_reference_id: str = Field(pattern=_SUBJECT_REF)
    origin: MilestoneOrigin
    origin_record_id: str = Field(min_length=1)
    origin_identity_hash: str = Field(pattern=_HASH)
    canonical_event_id: str = Field(min_length=1)
    original_label: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str | None = None
    direction: EventDirection = EventDirection.NOT_APPLICABLE
    magnitude: JsonValue | None = None
    window: TimelineWindow
    created_at: datetime
    sealed_at: datetime | None = None
    knowledge_cutoff_at: datetime | None = None
    sealed_match_criteria: dict[str, JsonValue] | None = None
    sealed_match_criteria_hash: str | None = Field(default=None, pattern=_HASH)
    known_event_milestone_id: str | None = None
    supersedes_milestone_id: str | None = None
    native_score_refs: tuple[str, ...] = ()
    provenance: MilestoneProvenance
    visibility: str = "private"

    @staticmethod
    def identity_payload(
        *,
        timeline_id: str,
        subject_reference_id: str,
        origin: MilestoneOrigin,
        origin_record_id: str,
        canonical_event_id: str,
    ) -> dict[str, str]:
        return {
            "timeline_id": timeline_id,
            "subject_reference_id": subject_reference_id,
            "origin": origin.value,
            "origin_record_id": origin_record_id,
            "canonical_event_id": canonical_event_id,
        }

    @classmethod
    def stable_identity(
        cls,
        *,
        timeline_id: str,
        subject_reference_id: str,
        origin: MilestoneOrigin,
        origin_record_id: str,
        canonical_event_id: str,
    ) -> tuple[str, str]:
        digest = stable_hash(
            cls.identity_payload(
                timeline_id=timeline_id,
                subject_reference_id=subject_reference_id,
                origin=origin,
                origin_record_id=origin_record_id,
                canonical_event_id=canonical_event_id,
            )
        )
        return f"tml_{digest[:32]}", digest

    @model_validator(mode="after")
    def validate_identity_and_origin(self) -> Self:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.knowledge_cutoff_at is not None and self.knowledge_cutoff_at.tzinfo is None:
            raise ValueError("knowledge_cutoff_at must be timezone-aware")
        expected_id, expected_hash = self.stable_identity(
            timeline_id=self.timeline_id,
            subject_reference_id=self.subject_reference_id,
            origin=self.origin,
            origin_record_id=self.origin_record_id,
            canonical_event_id=self.canonical_event_id,
        )
        if self.milestone_id != expected_id or self.origin_identity_hash != expected_hash:
            raise ValueError("milestone id/hash do not match immutable origin identity")
        if self.origin is MilestoneOrigin.PROSPECTIVE_PREDICTION:
            if self.sealed_at is None or self.knowledge_cutoff_at is None:
                raise ValueError("prospective predictions require sealing and knowledge cutoff")
            if self.known_event_milestone_id is not None:
                raise ValueError("prospective predictions cannot be created from a known event")
            if self.sealed_at.tzinfo is None or self.knowledge_cutoff_at.tzinfo is None:
                raise ValueError("sealing timestamps must be timezone-aware")
            if self.knowledge_cutoff_at > self.sealed_at:
                raise ValueError("knowledge cutoff cannot follow sealing")
            if self.created_at > self.sealed_at:
                raise ValueError("a prediction cannot be sealed before it was created")
            if self.sealed_at >= self.window.start_at:
                raise ValueError("a prospective prediction must be sealed before its window")
            if self.sealed_match_criteria is None or self.sealed_match_criteria_hash is None:
                raise ValueError("prospective predictions require seal-time matching criteria")
            if stable_hash(self.sealed_match_criteria) != self.sealed_match_criteria_hash:
                raise ValueError("sealed matching criteria hash does not match")
        elif self.sealed_at is not None:
            raise ValueError("only prospective predictions carry a sealed_at timestamp")
        elif self.sealed_match_criteria is not None or self.sealed_match_criteria_hash is not None:
            raise ValueError("only prospective predictions carry sealed matching criteria")
        if self.origin is MilestoneOrigin.RETROSPECTIVE_HYPOTHESIS:
            if not self.known_event_milestone_id:
                raise ValueError("retrospective hypotheses require the known event milestone")
            if self.knowledge_cutoff_at is None:
                raise ValueError("retrospective hypotheses require a knowledge cutoff")
        elif self.known_event_milestone_id is not None:
            raise ValueError("known_event_milestone_id is retrospective-only")
        if self.supersedes_milestone_id == self.milestone_id:
            raise ValueError("a milestone cannot supersede itself")
        return self


class TemporalOrderProof(TimelineModel):
    prediction_created_at: datetime
    prediction_sealed_at: datetime | None
    outcome_known_at: datetime | None
    proof_hash: str = Field(pattern=_HASH)

    @model_validator(mode="after")
    def validate_proof(self) -> Self:
        timestamps = (self.prediction_created_at, self.prediction_sealed_at, self.outcome_known_at)
        if any(value is not None and value.tzinfo is None for value in timestamps):
            raise ValueError("temporal-order timestamps must be timezone-aware")
        payload = temporal_order_payload(
            prediction_created_at=self.prediction_created_at,
            prediction_sealed_at=self.prediction_sealed_at,
            outcome_known_at=self.outcome_known_at,
        )
        if stable_hash(payload) != self.proof_hash:
            raise ValueError("temporal-order proof hash does not match")
        return self


class MilestonePredictionLink(TimelineModel):
    link_id: str = Field(min_length=1)
    milestone_id: str = Field(min_length=1)
    prediction_milestone_id: str = Field(min_length=1)
    raw_prediction_id: str = Field(min_length=1)
    relation: LinkRelation
    match_method: str = Field(min_length=1)
    match_version: str = Field(min_length=1)
    prediction_origin: MilestoneOrigin
    temporal_order_proof: TemporalOrderProof
    criteria_hash: str = Field(pattern=_HASH)
    match_criteria: dict[str, JsonValue]
    created_at: datetime

    @staticmethod
    def stable_identity(
        *,
        milestone_id: str,
        prediction_milestone_id: str,
        raw_prediction_id: str,
        relation: LinkRelation,
        match_method: str,
        match_version: str,
        criteria_hash: str,
    ) -> str:
        digest = stable_hash(
            {
                "milestone_id": milestone_id,
                "prediction_milestone_id": prediction_milestone_id,
                "raw_prediction_id": raw_prediction_id,
                "relation": relation.value,
                "match_method": match_method,
                "match_version": match_version,
                "criteria_hash": criteria_hash,
            }
        )
        return f"tmlink_{digest[:32]}"

    @model_validator(mode="after")
    def validate_link(self) -> Self:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.prediction_origin not in {
            MilestoneOrigin.PROSPECTIVE_PREDICTION,
            MilestoneOrigin.RETROSPECTIVE_HYPOTHESIS,
        }:
            raise ValueError("prediction links require prospective or retrospective identity")
        if stable_hash(self.match_criteria) != self.criteria_hash:
            raise ValueError("criteria_hash does not match the frozen criteria payload")
        expected_id = self.stable_identity(
            milestone_id=self.milestone_id,
            prediction_milestone_id=self.prediction_milestone_id,
            raw_prediction_id=self.raw_prediction_id,
            relation=self.relation,
            match_method=self.match_method,
            match_version=self.match_version,
            criteria_hash=self.criteria_hash,
        )
        if self.link_id != expected_id:
            raise ValueError("link_id does not match the stable prediction-link identity")
        sealed_at = self.temporal_order_proof.prediction_sealed_at
        if self.prediction_origin is MilestoneOrigin.PROSPECTIVE_PREDICTION:
            if sealed_at is None:
                raise ValueError("prospective links require sealing proof")
            known_at = self.temporal_order_proof.outcome_known_at
            if known_at is not None and sealed_at >= known_at:
                raise ValueError("prospective sealing must precede the known outcome")
        elif sealed_at is not None:
            raise ValueError("retrospective links cannot carry prospective sealing proof")
        return self


class DashaPeriod(TimelineModel):
    level: str = Field(min_length=1)
    ruler: str = Field(min_length=1)
    start_at: datetime
    end_at: datetime
    node_id: str | None = None
    deep_link: str | None = None

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("Dasha timestamps must be timezone-aware")
        if self.end_at < self.start_at:
            raise ValueError("Dasha end cannot precede start")
        return self


class TimingLadder(TimelineModel):
    system: str = Field(min_length=1)
    periods: tuple[DashaPeriod, ...] = ()

    @model_validator(mode="after")
    def validate_levels(self) -> Self:
        levels = [period.level for period in self.periods]
        if len(levels) != len(set(levels)):
            raise ValueError("a timing ladder cannot repeat a level")
        return self


class MilestoneEvidenceLink(TimelineModel):
    evidence_link_id: str = Field(min_length=1)
    milestone_id: str = Field(min_length=1)
    technique_run_id: str = Field(min_length=1)
    configuration_id: str = Field(min_length=1)
    rule_ids: tuple[str, ...] = ()
    role: EvidenceRole
    timing_ladder: TimingLadder | None = None
    native_score_ref: str | None = None
    calculated_artifact_ref: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    citation_ids: tuple[str, ...] = ()
    created_at: datetime

    @model_validator(mode="after")
    def validate_timestamp(self) -> Self:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self


class MilestoneResolution(TimelineModel):
    resolution_id: str = Field(min_length=1)
    prediction_milestone_id: str = Field(min_length=1)
    observed_milestone_id: str | None = None
    status: ResolutionStatus
    actual_window: TimelineWindow | None = None
    certainty: str = Field(min_length=1)
    resolver_id: str = Field(min_length=1)
    resolved_at: datetime
    notes: tuple[str, ...] = ()
    supersedes_resolution_id: str | None = None
    match_criteria: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> Self:
        if self.resolved_at.tzinfo is None:
            raise ValueError("resolved_at must be timezone-aware")
        if self.supersedes_resolution_id == self.resolution_id:
            raise ValueError("a resolution cannot supersede itself")
        if self.status in {ResolutionStatus.HIT, ResolutionStatus.PARTIAL_HIT}:
            if self.observed_milestone_id is None:
                raise ValueError("hit resolutions require an observed milestone")
            if self.actual_window is None:
                raise ValueError("hit resolutions require the actual event interval")
        return self


def temporal_order_payload(
    *,
    prediction_created_at: datetime,
    prediction_sealed_at: datetime | None,
    outcome_known_at: datetime | None,
) -> dict[str, str | None]:
    """Canonical UTC representation used by temporal-order hashes."""

    def canonical(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("temporal-order timestamps must be timezone-aware")
        return value.astimezone(UTC).isoformat()

    return {
        "prediction_created_at": canonical(prediction_created_at),
        "prediction_sealed_at": canonical(prediction_sealed_at),
        "outcome_known_at": canonical(outcome_known_at),
    }
