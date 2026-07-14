"""Uncertainty aggregation and fail-closed forecast abstention."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from statistics import fmean, pstdev

from .contracts import (
    Abstention,
    AbstentionCode,
    BirthTimeSensitivity,
    ForecastPolarity,
    UncertaintyAssessment,
)
from .research import NativeScore


@dataclass(frozen=True, slots=True)
class BirthTimeSignal:
    """Traditional output for one plausible birth time.

    ``traditional_strength_index`` remains an internal ordinal/rule score.  It
    is intentionally not transformed into, or named as, a probability.
    """

    sample_id: str
    event_supported: bool
    polarity: ForecastPolarity
    traditional_strength_index: float

    def __post_init__(self) -> None:
        if not self.sample_id:
            raise ValueError("sample_id is required")
        if not math.isfinite(self.traditional_strength_index):
            raise ValueError("traditional_strength_index must be finite")


@dataclass(frozen=True, slots=True)
class BirthTimeEnsemble:
    sample_count: int
    event_agreement_ratio: float | None
    polarity_agreement_ratio: float | None
    dominant_polarity: ForecastPolarity | None
    mean_traditional_strength_index: float | None
    traditional_strength_spread: float | None
    sensitivity: BirthTimeSensitivity


@dataclass(frozen=True, slots=True)
class AbstentionThresholds:
    minimum_data_completeness: float = 0.80
    maximum_unresolved_conflicts: int = 0
    minimum_event_agreement: float = 0.75
    minimum_polarity_agreement: float = 0.75

    def __post_init__(self) -> None:
        ratios = (
            self.minimum_data_completeness,
            self.minimum_event_agreement,
            self.minimum_polarity_agreement,
        )
        if any(not 0 <= value <= 1 for value in ratios):
            raise ValueError("ratio thresholds must be between zero and one")
        if self.maximum_unresolved_conflicts < 0:
            raise ValueError("maximum_unresolved_conflicts cannot be negative")


@dataclass(frozen=True, slots=True)
class ResearchForecastAssessment:
    """A release annotation plus the untouched research signal.

    Product code may continue to use :func:`decide_abstention`. Research code
    uses this envelope so a release decision can never erase the engine's
    original direction, native score, or experimental probability.
    """

    polarity: str
    forecast_probability: float | None
    native_score: NativeScore | None
    uncertainty: UncertaintyAssessment
    release_annotation: Abstention


def annotate_research_forecast(
    uncertainty: UncertaintyAssessment,
    *,
    polarity: str,
    forecast_probability: float | None,
    native_score: NativeScore | None,
    out_of_distribution: bool = False,
    calibration_release_eligible: bool = False,
    thresholds: AbstentionThresholds | None = None,
) -> ResearchForecastAssessment:
    """Annotate release eligibility without modifying the research forecast."""

    if forecast_probability is not None and not 0 <= forecast_probability <= 1:
        raise ValueError("forecast_probability must be between zero and one")
    annotation = decide_abstention(
        uncertainty,
        out_of_distribution=out_of_distribution,
        probability_requested=forecast_probability is not None,
        calibration_release_eligible=calibration_release_eligible,
        thresholds=thresholds,
    )
    return ResearchForecastAssessment(
        polarity=polarity,
        forecast_probability=forecast_probability,
        native_score=native_score,
        uncertainty=uncertainty,
        release_annotation=annotation,
    )


def aggregate_birth_time_signals(
    signals: tuple[BirthTimeSignal, ...] | list[BirthTimeSignal],
    *,
    stable_threshold: float = 0.80,
    moderate_threshold: float = 0.60,
) -> BirthTimeEnsemble:
    """Summarise agreement across plausible birth-time calculations."""

    if not 0 <= moderate_threshold <= stable_threshold <= 1:
        raise ValueError("sensitivity thresholds must satisfy 0 <= moderate <= stable <= 1")
    if not signals:
        return BirthTimeEnsemble(
            sample_count=0,
            event_agreement_ratio=None,
            polarity_agreement_ratio=None,
            dominant_polarity=None,
            mean_traditional_strength_index=None,
            traditional_strength_spread=None,
            sensitivity=BirthTimeSensitivity.UNKNOWN,
        )

    event_counts = Counter(item.event_supported for item in signals)
    event_agreement = max(event_counts.values()) / len(signals)
    supported = [item for item in signals if item.event_supported]
    if supported:
        polarity_counts = Counter(item.polarity for item in supported)
        dominant, dominant_count = sorted(
            polarity_counts.items(), key=lambda item: (-item[1], item[0].value)
        )[0]
        polarity_agreement = dominant_count / len(supported)
    else:
        dominant = None
        polarity_agreement = None

    agreement_floor = min(event_agreement, polarity_agreement or event_agreement)
    if len(signals) < 2:
        sensitivity = BirthTimeSensitivity.UNKNOWN
    elif agreement_floor >= stable_threshold:
        sensitivity = BirthTimeSensitivity.STABLE
    elif agreement_floor >= moderate_threshold:
        sensitivity = BirthTimeSensitivity.MODERATE
    else:
        sensitivity = BirthTimeSensitivity.HIGH

    strengths = [item.traditional_strength_index for item in signals]
    return BirthTimeEnsemble(
        sample_count=len(signals),
        event_agreement_ratio=event_agreement,
        polarity_agreement_ratio=polarity_agreement,
        dominant_polarity=dominant,
        mean_traditional_strength_index=fmean(strengths),
        traditional_strength_spread=pstdev(strengths) if len(strengths) > 1 else 0.0,
        sensitivity=sensitivity,
    )


def to_uncertainty_assessment(
    ensemble: BirthTimeEnsemble,
    *,
    data_completeness_ratio: float,
    unresolved_conflict_count: int = 0,
    cross_system_agreement_ratio: float | None = None,
    notes: tuple[str, ...] = (),
) -> UncertaintyAssessment:
    return UncertaintyAssessment(
        birth_time_sensitivity=ensemble.sensitivity,
        sampled_birth_times=ensemble.sample_count,
        event_agreement_ratio=ensemble.event_agreement_ratio,
        polarity_agreement_ratio=ensemble.polarity_agreement_ratio,
        cross_system_agreement_ratio=cross_system_agreement_ratio,
        data_completeness_ratio=data_completeness_ratio,
        unresolved_conflict_count=unresolved_conflict_count,
        notes=notes,
    )


def decide_abstention(
    uncertainty: UncertaintyAssessment,
    *,
    out_of_distribution: bool = False,
    probability_requested: bool = False,
    calibration_release_eligible: bool = False,
    thresholds: AbstentionThresholds | None = None,
) -> Abstention:
    """Return the first fail-closed reason in a stable priority order."""

    limits = thresholds or AbstentionThresholds()
    if uncertainty.data_completeness_ratio < limits.minimum_data_completeness:
        return _abstain(
            AbstentionCode.DATA_INCOMPLETE,
            "Required chart or outcome data is incomplete; no forecast is released.",
            retryable=True,
        )
    if out_of_distribution:
        return _abstain(
            AbstentionCode.OUT_OF_DISTRIBUTION,
            "This case is outside the validated evaluation population.",
        )
    if uncertainty.birth_time_sensitivity is BirthTimeSensitivity.HIGH:
        return _abstain(
            AbstentionCode.BIRTH_TIME_INSTABILITY,
            "The event direction is unstable across plausible birth times.",
            retryable=True,
        )
    if uncertainty.event_agreement_ratio is not None and (
        uncertainty.event_agreement_ratio < limits.minimum_event_agreement
    ):
        return _abstain(
            AbstentionCode.BIRTH_TIME_INSTABILITY,
            "The event does not repeat consistently across plausible birth times.",
            retryable=True,
        )
    if uncertainty.polarity_agreement_ratio is not None and (
        uncertainty.polarity_agreement_ratio < limits.minimum_polarity_agreement
    ):
        return _abstain(
            AbstentionCode.BIRTH_TIME_INSTABILITY,
            "Favourable and unfavourable directions conflict across plausible birth times.",
            retryable=True,
        )
    if uncertainty.unresolved_conflict_count > limits.maximum_unresolved_conflicts:
        return _abstain(
            AbstentionCode.CONFLICTING_EVIDENCE,
            "Material supporting and opposing signals remain unresolved.",
        )
    if probability_requested and not calibration_release_eligible:
        return _abstain(
            AbstentionCode.INSUFFICIENT_EVIDENCE,
            "No approved calibration release exists, so a probability cannot be shown.",
        )
    return Abstention(abstained=False, code=AbstentionCode.NONE)


def _abstain(code: AbstentionCode, reason: str, *, retryable: bool = False) -> Abstention:
    return Abstention(abstained=True, code=code, reason=reason, retryable=retryable)
