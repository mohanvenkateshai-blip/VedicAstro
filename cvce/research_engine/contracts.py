"""Lossless, policy-neutral contracts for raw technique research runs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, JsonValue, model_validator


class ResearchModel(BaseModel):
    """Strict envelope; arbitrary native data belongs in explicit payload fields."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class TimingTolerance(ResearchModel):
    value: str | int | float
    unit: str = Field(min_length=1)
    direction: str = Field(default="plus_or_minus", min_length=1)
    original_payload: JsonValue = Field(default_factory=dict)


class RawTiming(ResearchModel):
    """Native timing without coercion into a product forecast window.

    ``kind`` is deliberately an open string. Registries describe known kinds,
    while adapters can retain previously unseen technique-native resolutions.
    """

    kind: str = Field(min_length=1)
    instant: str | None = None
    start: str | None = None
    end: str | None = None
    native_value: str | None = None
    timezone: str | None = None
    tolerance: TimingTolerance | None = None
    original_payload: JsonValue = Field(default_factory=dict)


class RawScore(ResearchModel):
    score_code: str = Field(min_length=1)
    original_value: JsonValue
    numeric_value: float | None = None
    native_unit: str | None = None
    formula_version: str | None = None
    polarity_mapping: dict[str, JsonValue] = Field(default_factory=dict)
    normalization_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    scale_min: float | None = None
    scale_max: float | None = None
    original_payload: JsonValue = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scale(self) -> RawScore:
        if self.scale_min is not None and self.scale_max is not None:
            if self.scale_min > self.scale_max:
                raise ValueError("scale_min cannot exceed scale_max")
        return self


class RawPrediction(ResearchModel):
    prediction_id: str = Field(min_length=1)
    source_item_key: str | None = None
    event_code: str = Field(min_length=1)
    original_event_label: str | None = None
    original_prose: str | None = None
    native_direction: str | None = None
    native_polarity: str | None = None
    magnitude: JsonValue | None = None
    conditions: tuple[str, ...] = ()
    supporting_factor_refs: tuple[str, ...] = ()
    opposing_factor_refs: tuple[str, ...] = ()
    timing: RawTiming | None = None
    scores: tuple[RawScore, ...] = ()
    original_payload: JsonValue


class TechniqueItemError(ResearchModel):
    """One failed item that does not erase successful items from the run."""

    item_key: str = Field(min_length=1)
    phase: str = Field(min_length=1)
    error_code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False
    original_item_payload: JsonValue = Field(default_factory=dict)


class RunStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class TechniqueRunError(ResearchModel):
    phase: str = Field(min_length=1)
    error_code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False
    original_error_payload: JsonValue = Field(default_factory=dict)


class RunArtifactReference(ResearchModel):
    artifact_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    uri: str | None = None
    content_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class TechniqueConfiguration(ResearchModel):
    configuration_id: str = Field(min_length=1)
    technique_code: str = Field(min_length=1)
    technique_version: str = Field(min_length=1)
    implementation_version: str = Field(min_length=1)
    school_or_lineage: str | None = None
    ayanamsa: str | None = None
    ephemeris: str | None = None
    house_or_bhava_system: str | None = None
    dasha_system: str | None = None
    dasha_depth: int | None = Field(default=None, ge=0)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    original_configuration_payload: JsonValue = Field(default_factory=dict)

    @property
    def configuration_hash(self) -> str:
        """Deterministic identity of all configuration fields, without recursion."""

        from .identity import stable_hash

        return stable_hash(self.model_dump(mode="json", round_trip=True))


class TechniqueRun(ResearchModel):
    run_id: str = Field(min_length=1)
    configuration: TechniqueConfiguration
    original_input_payload: JsonValue
    original_input_payload_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        validation_alias=AliasChoices(
            "original_input_payload_hash",
            "declared_original_input_payload_hash",
            "input_snapshot_hash",
        ),
    )
    event_registry_id: str | None = None
    event_registry_version: str | None = None
    event_registry_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    timing_registry_id: str | None = None
    timing_registry_version: str | None = None
    timing_registry_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    external_input_snapshot_ref: str | None = None
    external_input_snapshot_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    started_at: datetime
    completed_at: datetime
    status: RunStatus = RunStatus.COMPLETED
    predictions: tuple[RawPrediction, ...] = ()
    item_errors: tuple[TechniqueItemError, ...] = ()
    run_errors: tuple[TechniqueRunError, ...] = ()
    artifact_references: tuple[RunArtifactReference, ...] = ()
    run_metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @property
    def input_snapshot_hash(self) -> str:
        """Backward-compatible alias for the embedded payload hash."""

        assert self.original_input_payload_hash is not None
        return self.original_input_payload_hash

    @model_validator(mode="after")
    def validate_run(self) -> TechniqueRun:
        from .identity import stable_hash

        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("run timestamps must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        computed_input_hash = stable_hash(self.original_input_payload)
        if (
            self.original_input_payload_hash is not None
            and self.original_input_payload_hash != computed_input_hash
        ):
            raise ValueError("embedded input payload hash does not match original_input_payload")
        object.__setattr__(self, "original_input_payload_hash", computed_input_hash)
        event_ref = (self.event_registry_id, self.event_registry_version, self.event_registry_hash)
        timing_ref = (
            self.timing_registry_id,
            self.timing_registry_version,
            self.timing_registry_hash,
        )
        if any(value is not None for value in event_ref) and any(
            value is None for value in event_ref
        ):
            raise ValueError("event registry id, version, and hash must be supplied together")
        if any(value is not None for value in timing_ref) and any(
            value is None for value in timing_ref
        ):
            raise ValueError("timing registry id, version, and hash must be supplied together")
        if (self.external_input_snapshot_ref is None) != (
            self.external_input_snapshot_hash is None
        ):
            raise ValueError("external snapshot reference and hash must be supplied together")
        if self.status is RunStatus.COMPLETED and (self.item_errors or self.run_errors):
            raise ValueError("a completed run cannot contain item-level or run-level errors")
        if self.status is RunStatus.PARTIAL and (
            not self.predictions or not (self.run_errors or self.item_errors)
        ):
            raise ValueError("a partial run requires predictions and at least one error")
        if self.status is RunStatus.FAILED and (self.predictions or not self.run_errors):
            raise ValueError(
                "a failed run requires zero predictions and at least one run-level error"
            )
        prediction_ids = [prediction.prediction_id for prediction in self.predictions]
        if len(prediction_ids) != len(set(prediction_ids)):
            raise ValueError("prediction_id must be unique within a run")
        return self


class ResearchAnnotation(ResearchModel):
    """Append-only research interpretation kept separate from raw output."""

    annotation_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    prediction_id: str | None = None
    annotation_type: str = Field(min_length=1)
    payload: dict[str, JsonValue]
    created_at: datetime
    actor_id: str = Field(min_length=1)
    supersedes_annotation_id: str | None = None

    @model_validator(mode="after")
    def validate_annotation(self) -> ResearchAnnotation:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.supersedes_annotation_id == self.annotation_id:
            raise ValueError("an annotation cannot supersede itself")
        return self
