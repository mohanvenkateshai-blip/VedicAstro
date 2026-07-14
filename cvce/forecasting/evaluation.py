"""Deterministic evaluation and probability-release controls."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ReliabilityBin:
    lower: float
    upper: float
    count: int
    mean_probability: float | None
    observed_rate: float | None


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    estimate: float
    lower: float
    upper: float
    confidence_level: float
    resamples: int
    seed: int


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    sample_size: int
    positive_count: int
    brier_score: float
    log_loss: float
    expected_calibration_error: float
    discrimination_auc: float | None
    reliability_bins: tuple[ReliabilityBin, ...]


@dataclass(frozen=True, slots=True)
class CalibrationReleaseDecision:
    eligible: bool
    calibration_release_id: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NegativeControlReport:
    """Diagnostic only; release policy decides whether this result passes."""

    seed: int
    observed_brier_score: float
    permuted_brier_score: float
    observed_discrimination_auc: float | None
    permuted_discrimination_auc: float | None


@dataclass(frozen=True, slots=True)
class ProbabilityReleaseGuard:
    """Minimum empirical gate for exposing a probability to a product user."""

    minimum_samples: int = 200
    minimum_positive_labels: int = 20
    minimum_negative_labels: int = 20
    maximum_ece: float = 0.10

    def __post_init__(self) -> None:
        if self.minimum_samples < 1:
            raise ValueError("minimum_samples must be positive")
        if self.minimum_positive_labels < 1 or self.minimum_negative_labels < 1:
            raise ValueError("minimum class counts must be positive")
        if not 0 <= self.maximum_ece <= 1:
            raise ValueError("maximum_ece must be between zero and one")

    def assess(
        self,
        report: CalibrationReport,
        *,
        calibration_release_id: str | None,
        evaluated_on_holdout: bool,
        negative_control_passed: bool,
    ) -> CalibrationReleaseDecision:
        reasons: list[str] = []
        negatives = report.sample_size - report.positive_count
        if report.sample_size < self.minimum_samples:
            reasons.append("minimum sample size not met")
        if report.positive_count < self.minimum_positive_labels:
            reasons.append("minimum positive-label count not met")
        if negatives < self.minimum_negative_labels:
            reasons.append("minimum negative-label count not met")
        if report.expected_calibration_error > self.maximum_ece:
            reasons.append("calibration error exceeds release threshold")
        if not evaluated_on_holdout:
            reasons.append("calibration was not evaluated on a holdout set")
        if not negative_control_passed:
            reasons.append("negative control did not pass")
        if not calibration_release_id or not calibration_release_id.strip():
            reasons.append("calibration release identifier is required")
        return CalibrationReleaseDecision(
            eligible=not reasons,
            calibration_release_id=calibration_release_id if not reasons else None,
            reasons=tuple(reasons),
        )


def brier_score(probabilities: Sequence[float], outcomes: Sequence[bool | int]) -> float:
    pairs = _validated_pairs(probabilities, outcomes)
    return sum((probability - outcome) ** 2 for probability, outcome in pairs) / len(pairs)


def binary_log_loss(
    probabilities: Sequence[float],
    outcomes: Sequence[bool | int],
    *,
    epsilon: float = 1e-15,
) -> float:
    if not 0 < epsilon < 0.5:
        raise ValueError("epsilon must be between zero and 0.5")
    pairs = _validated_pairs(probabilities, outcomes)
    total = 0.0
    for probability, outcome in pairs:
        clipped = min(max(probability, epsilon), 1 - epsilon)
        total -= outcome * math.log(clipped) + (1 - outcome) * math.log(1 - clipped)
    return total / len(pairs)


def reliability_bins(
    probabilities: Sequence[float],
    outcomes: Sequence[bool | int],
    *,
    bin_count: int = 10,
) -> tuple[ReliabilityBin, ...]:
    if bin_count < 1:
        raise ValueError("bin_count must be positive")
    pairs = _validated_pairs(probabilities, outcomes)
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bin_count)]
    for probability, outcome in pairs:
        index = min(int(probability * bin_count), bin_count - 1)
        buckets[index].append((probability, outcome))
    result = []
    for index, bucket in enumerate(buckets):
        count = len(bucket)
        result.append(
            ReliabilityBin(
                lower=index / bin_count,
                upper=(index + 1) / bin_count,
                count=count,
                mean_probability=(sum(item[0] for item in bucket) / count if count else None),
                observed_rate=(sum(item[1] for item in bucket) / count if count else None),
            )
        )
    return tuple(result)


def expected_calibration_error(
    probabilities: Sequence[float],
    outcomes: Sequence[bool | int],
    *,
    bin_count: int = 10,
) -> float:
    bins = reliability_bins(probabilities, outcomes, bin_count=bin_count)
    sample_size = len(probabilities)
    return sum(
        item.count / sample_size * abs(float(item.mean_probability) - float(item.observed_rate))
        for item in bins
        if item.count
    )


def discrimination_auc(
    probabilities: Sequence[float], outcomes: Sequence[bool | int]
) -> float | None:
    """ROC AUC via pairwise concordance; returns None for one-class data."""

    pairs = _validated_pairs(probabilities, outcomes)
    positives = [probability for probability, outcome in pairs if outcome == 1]
    negatives = [probability for probability, outcome in pairs if outcome == 0]
    if not positives or not negatives:
        return None
    concordance = 0.0
    for positive in positives:
        for negative in negatives:
            concordance += float(positive > negative) + 0.5 * float(positive == negative)
    return concordance / (len(positives) * len(negatives))


def calibration_report(
    probabilities: Sequence[float],
    outcomes: Sequence[bool | int],
    *,
    bin_count: int = 10,
) -> CalibrationReport:
    pairs = _validated_pairs(probabilities, outcomes)
    probabilities_checked = [item[0] for item in pairs]
    outcomes_checked = [item[1] for item in pairs]
    return CalibrationReport(
        sample_size=len(pairs),
        positive_count=sum(outcomes_checked),
        brier_score=brier_score(probabilities_checked, outcomes_checked),
        log_loss=binary_log_loss(probabilities_checked, outcomes_checked),
        expected_calibration_error=expected_calibration_error(
            probabilities_checked, outcomes_checked, bin_count=bin_count
        ),
        discrimination_auc=discrimination_auc(probabilities_checked, outcomes_checked),
        reliability_bins=reliability_bins(
            probabilities_checked, outcomes_checked, bin_count=bin_count
        ),
    )


def bootstrap_confidence_interval[T](
    values: Sequence[T],
    statistic: Callable[[Sequence[T]], float],
    *,
    resamples: int = 1_000,
    confidence_level: float = 0.95,
    seed: int = 20260714,
) -> ConfidenceInterval:
    """Fixed-seed percentile bootstrap for a caller-supplied statistic."""

    if not values:
        raise ValueError("values cannot be empty")
    if resamples < 1:
        raise ValueError("resamples must be positive")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between zero and one")
    rng = random.Random(seed)
    values_list = list(values)
    estimates = sorted(
        statistic([rng.choice(values_list) for _ in values_list]) for _ in range(resamples)
    )
    tail = (1 - confidence_level) / 2
    return ConfidenceInterval(
        estimate=statistic(values_list),
        lower=_percentile(estimates, tail),
        upper=_percentile(estimates, 1 - tail),
        confidence_level=confidence_level,
        resamples=resamples,
        seed=seed,
    )


def permuted_outcomes(outcomes: Sequence[bool | int], *, seed: int = 20260714) -> tuple[int, ...]:
    """Negative-control hook: deterministically break feature/label association."""

    if not outcomes or any(
        type(value) not in (bool, int) or value not in (0, 1) for value in outcomes
    ):
        raise ValueError("outcomes must be a non-empty binary sequence")
    normalized = [int(bool(value)) for value in outcomes]
    rng = random.Random(seed)
    rng.shuffle(normalized)
    return tuple(normalized)


def negative_control_report(
    probabilities: Sequence[float],
    outcomes: Sequence[bool | int],
    *,
    seed: int = 20260714,
) -> NegativeControlReport:
    """Evaluate unchanged scores against labels with their association broken."""

    shuffled = permuted_outcomes(outcomes, seed=seed)
    return NegativeControlReport(
        seed=seed,
        observed_brier_score=brier_score(probabilities, outcomes),
        permuted_brier_score=brier_score(probabilities, shuffled),
        observed_discrimination_auc=discrimination_auc(probabilities, outcomes),
        permuted_discrimination_auc=discrimination_auc(probabilities, shuffled),
    )


def assert_point_in_time_split(
    *, training_cutoff: datetime, forecast_times: Sequence[datetime]
) -> None:
    """Reject evaluation rows at or before the training-data cutoff."""

    if training_cutoff.tzinfo is None or any(item.tzinfo is None for item in forecast_times):
        raise ValueError("all timestamps must be timezone-aware")
    if any(item <= training_cutoff for item in forecast_times):
        raise ValueError("training cutoff must strictly precede every evaluated forecast")


def _validated_pairs(
    probabilities: Sequence[float], outcomes: Sequence[bool | int]
) -> list[tuple[float, int]]:
    if not probabilities or len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must be non-empty and equally sized")
    result: list[tuple[float, int]] = []
    for probability, outcome in zip(probabilities, outcomes, strict=True):
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("probabilities must be finite values between zero and one")
        if type(outcome) not in (bool, int) or outcome not in (0, 1):
            raise ValueError("outcomes must be binary")
        result.append((float(probability), int(outcome)))
    return result


def _percentile(sorted_values: Sequence[float], quantile: float) -> float:
    position = quantile * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction
