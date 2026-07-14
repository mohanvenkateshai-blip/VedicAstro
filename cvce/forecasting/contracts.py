"""Pydantic v2 contracts for evidence, candidates, and forecast claims."""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .taxonomy import EventCode, EventDomain, get_event_definition

CURRENT_CONTRACT_VERSION = "1.0.0"
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class ForecastMode(StrEnum):
    FORECAST = "forecast"
    ELECTIONAL = "electional"
    NATAL_INTERPRETATION = "natal_interpretation"
    EXPLANATION = "explanation"


class EvidenceDirection(StrEnum):
    SUPPORTING = "supporting"
    OPPOSING = "opposing"
    CONTEXT = "context"


class ForecastPolarity(StrEnum):
    FAVOURABLE = "favourable"
    UNFAVOURABLE = "unfavourable"
    MIXED = "mixed"
    INDETERMINATE = "indeterminate"


class TemporalGranularity(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"


class ProbabilityStatus(StrEnum):
    UNAVAILABLE = "unavailable"
    UNCALIBRATED_SIGNAL = "uncalibrated_signal"
    CALIBRATED = "calibrated"


class CertaintyTier(StrEnum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    TRADITIONAL_SIGNAL = "traditional_signal"
    CALIBRATED_FORECAST = "calibrated_forecast"


class BirthTimeSensitivity(StrEnum):
    STABLE = "stable"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class AbstentionCode(StrEnum):
    NONE = "none"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    BIRTH_TIME_INSTABILITY = "birth_time_instability"
    OUT_OF_DISTRIBUTION = "out_of_distribution"
    UNSUPPORTED_EVENT = "unsupported_event"
    POLICY_BLOCKED = "policy_blocked"
    DATA_INCOMPLETE = "data_incomplete"


class CalculationProvenance(ContractModel):
    calculation_hash: str = Field(min_length=16, description="Hash of canonical calculation inputs")
    calculation_hash_algorithm: str = "sha256"
    engine_version: str = Field(min_length=1)
    rule_pack_versions: dict[str, str] = Field(default_factory=dict)
    source_ids: tuple[str, ...] = ()
    citation_ids: tuple[str, ...] = ()
    data_cutoff_at: datetime
    calculated_at: datetime

    @model_validator(mode="after")
    def validate_provenance(self) -> CalculationProvenance:
        if self.calculated_at.tzinfo is None or self.data_cutoff_at.tzinfo is None:
            raise ValueError("provenance timestamps must be timezone-aware")
        if self.data_cutoff_at > self.calculated_at:
            raise ValueError("data_cutoff_at cannot be after calculated_at")
        return self


class TimingWindow(ContractModel):
    start_on: date
    end_on: date
    resolution_due_on: date
    timezone: str
    granularity: TemporalGranularity
    horizon_days: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_window(self) -> TimingWindow:
        if self.end_on < self.start_on:
            raise ValueError("end_on cannot precede start_on")
        if self.resolution_due_on < self.end_on:
            raise ValueError("resolution_due_on cannot precede end_on")
        inclusive_days = (self.end_on - self.start_on).days + 1
        if self.horizon_days != inclusive_days:
            raise ValueError("horizon_days must equal the inclusive timing-window length")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        return self


class UncertaintyAssessment(ContractModel):
    birth_time_sensitivity: BirthTimeSensitivity = BirthTimeSensitivity.UNKNOWN
    sampled_birth_times: int = Field(default=0, ge=0)
    event_agreement_ratio: float | None = Field(default=None, ge=0, le=1)
    polarity_agreement_ratio: float | None = Field(default=None, ge=0, le=1)
    cross_system_agreement_ratio: float | None = Field(default=None, ge=0, le=1)
    data_completeness_ratio: float = Field(ge=0, le=1)
    unresolved_conflict_count: int = Field(default=0, ge=0)
    notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_birth_time_sampling(self) -> UncertaintyAssessment:
        ratios = (self.event_agreement_ratio, self.polarity_agreement_ratio)
        if any(value is not None for value in ratios) and self.sampled_birth_times < 2:
            raise ValueError("birth-time agreement ratios require at least two sampled birth times")
        return self


class Abstention(ContractModel):
    abstained: bool
    code: AbstentionCode
    reason: str | None = None
    retryable: bool = False

    @model_validator(mode="after")
    def validate_state(self) -> Abstention:
        if self.abstained and self.code is AbstentionCode.NONE:
            raise ValueError("an abstention requires a specific code")
        if self.abstained and not self.reason:
            raise ValueError("an abstention requires a human-readable reason")
        if not self.abstained and self.code is not AbstentionCode.NONE:
            raise ValueError("a non-abstained claim must use code 'none'")
        return self


class RuleEvidence(ContractModel):
    schema_version: str = CURRENT_CONTRACT_VERSION
    evidence_id: str = Field(min_length=1)
    event_code: EventCode
    direction: EvidenceDirection
    rule_id: str = Field(min_length=1)
    signal_name: str = Field(min_length=1)
    traditional_strength_index: float
    source_confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)
    provenance: CalculationProvenance

    @model_validator(mode="after")
    def validate_semantics(self) -> RuleEvidence:
        _validate_contract_version(self.schema_version)
        _validate_finite(self.traditional_strength_index, "traditional_strength_index")
        return self


class EventCandidate(ContractModel):
    schema_version: str = CURRENT_CONTRACT_VERSION
    candidate_id: str = Field(min_length=1)
    event_code: EventCode
    subject: str = Field(default="native", pattern=r"^native$")
    timing: TimingWindow
    polarity: ForecastPolarity
    traditional_strength_index: float
    supporting_evidence_ids: tuple[str, ...] = ()
    opposing_evidence_ids: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    alternate_manifestations: tuple[str, ...] = ()
    disconfirmers: tuple[str, ...] = ()
    uncertainty: UncertaintyAssessment
    provenance: CalculationProvenance

    @model_validator(mode="after")
    def validate_candidate(self) -> EventCandidate:
        _validate_contract_version(self.schema_version)
        _validate_finite(self.traditional_strength_index, "traditional_strength_index")
        definition = get_event_definition(self.event_code)
        if self.timing.horizon_days > definition.maximum_horizon_days:
            raise ValueError("timing horizon exceeds the event taxonomy maximum")
        if self.timing.granularity.value not in definition.permitted_granularities:
            raise ValueError("timing granularity is not permitted for this event")
        if set(self.supporting_evidence_ids) & set(self.opposing_evidence_ids):
            raise ValueError("one evidence item cannot be both supporting and opposing")
        return self


class ForecastClaim(ContractModel):
    """One user-visible, versioned claim about one event and one horizon."""

    contract_version: str = CURRENT_CONTRACT_VERSION
    claim_id: str = Field(min_length=1)
    forecast_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    locale: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    mode: ForecastMode
    event_code: EventCode
    event_domain: EventDomain
    subject: str = Field(default="native", pattern=r"^native$")
    observable_outcome: str = Field(min_length=1)
    timing: TimingWindow
    polarity: ForecastPolarity
    traditional_strength_index: float
    forecast_probability: float | None = Field(default=None, ge=0, le=1)
    probability_status: ProbabilityStatus
    calibration_release_id: str | None = None
    base_rate: float | None = Field(default=None, ge=0, le=1)
    base_rate_source: str | None = None
    supporting_evidence_ids: tuple[str, ...] = ()
    opposing_evidence_ids: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    citation_ids: tuple[str, ...] = ()
    provenance: CalculationProvenance
    uncertainty: UncertaintyAssessment
    prerequisites: tuple[str, ...] = ()
    alternate_manifestations: tuple[str, ...] = ()
    disconfirmers: tuple[str, ...] = ()
    what_to_expect: tuple[str, ...] = ()
    safe_next_steps: tuple[str, ...] = ()
    avoidance_advice: tuple[str, ...] = ()
    decision_scope: str = Field(min_length=1)
    limitations: tuple[str, ...] = ()
    certainty_tier: CertaintyTier
    abstention: Abstention
    high_stakes: bool = False
    review_required: bool = False

    @model_validator(mode="after")
    def validate_claim(self) -> ForecastClaim:
        _validate_contract_version(self.contract_version)
        _validate_finite(self.traditional_strength_index, "traditional_strength_index")
        definition = get_event_definition(self.event_code)

        if self.mode is not ForecastMode.FORECAST:
            raise ValueError("ForecastClaim is reserved for forecast mode")
        if self.event_domain is not definition.domain:
            raise ValueError("event_domain must match the event_code hierarchy")
        if self.observable_outcome != definition.observable_predicate:
            raise ValueError("observable_outcome must be the canonical taxonomy predicate")
        if self.timing.horizon_days > definition.maximum_horizon_days:
            raise ValueError("timing horizon exceeds the event taxonomy maximum")
        if self.timing.granularity.value not in definition.permitted_granularities:
            raise ValueError("timing granularity is not permitted for this event")

        calibrated = self.probability_status is ProbabilityStatus.CALIBRATED
        if calibrated and self.forecast_probability is None:
            raise ValueError("calibrated status requires forecast_probability")
        if calibrated and not self.calibration_release_id:
            raise ValueError("calibrated probability requires calibration_release_id")
        if not calibrated and self.forecast_probability is not None:
            raise ValueError(
                "forecast_probability is only permitted for an empirically calibrated forecast; "
                "use traditional_strength_index for internal rule scores"
            )
        if not calibrated and self.calibration_release_id is not None:
            raise ValueError("calibration_release_id is only valid for calibrated forecasts")
        if self.certainty_tier is CertaintyTier.CALIBRATED_FORECAST and not calibrated:
            raise ValueError("calibrated certainty tier requires calibrated probability status")
        if calibrated and self.certainty_tier is not CertaintyTier.CALIBRATED_FORECAST:
            raise ValueError("a calibrated probability requires the calibrated certainty tier")
        if (self.base_rate is None) != (self.base_rate_source is None):
            raise ValueError("base_rate and base_rate_source must be supplied together")
        if set(self.supporting_evidence_ids) & set(self.opposing_evidence_ids):
            raise ValueError("one evidence item cannot be both supporting and opposing")
        if self.abstention.abstained:
            if self.polarity is not ForecastPolarity.INDETERMINATE:
                raise ValueError("an abstained claim must have indeterminate polarity")
            if self.forecast_probability is not None:
                raise ValueError("an abstained claim cannot expose a forecast probability")
        if definition.requires_explicit_opt_in and not self.review_required:
            raise ValueError("sensitive opt-in events require review")
        return self


def _validate_contract_version(value: str) -> None:
    if not _SEMVER.fullmatch(value):
        raise ValueError("contract version must use MAJOR.MINOR.PATCH")
    if value.split(".", maxsplit=1)[0] != CURRENT_CONTRACT_VERSION.split(".", maxsplit=1)[0]:
        raise ValueError("unsupported contract major version")


def _validate_finite(value: float, field_name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
