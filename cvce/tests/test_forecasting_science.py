from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import pytest
from forecasting.baselines import (
    BaselineKind,
    LeakageError,
    OutcomeObservation,
    fit_m0_event_family,
    fit_m1_temporal_cohort,
)
from forecasting.contracts import (
    AbstentionCode,
    BirthTimeSensitivity,
    ForecastPolarity,
    UncertaintyAssessment,
)
from forecasting.evaluation import (
    ProbabilityReleaseGuard,
    assert_point_in_time_split,
    binary_log_loss,
    bootstrap_confidence_interval,
    brier_score,
    calibration_report,
    discrimination_auc,
    expected_calibration_error,
    negative_control_report,
    permuted_outcomes,
)
from forecasting.uncertainty import (
    AbstentionThresholds,
    BirthTimeSignal,
    aggregate_birth_time_signals,
    decide_abstention,
    to_uncertainty_assessment,
)


def dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


def observation(
    identifier: str,
    outcome: bool,
    *,
    family: str = "contract",
    cohort: str = "returning",
    forecast_at: datetime | None = None,
    target_at: datetime | None = None,
    resolved_at: datetime | None = None,
) -> OutcomeObservation:
    return OutcomeObservation(
        observation_id=identifier,
        event_family=family,
        outcome=outcome,
        cohort=cohort,
        forecast_at=forecast_at or dt(2025, 1, 1),
        target_at=target_at or dt(2025, 3, 1),
        resolved_at=resolved_at or dt(2025, 3, 2),
    )


def assessment(**overrides: object) -> UncertaintyAssessment:
    values: dict[str, object] = {
        "birth_time_sensitivity": BirthTimeSensitivity.STABLE,
        "sampled_birth_times": 4,
        "event_agreement_ratio": 1.0,
        "polarity_agreement_ratio": 1.0,
        "cross_system_agreement_ratio": 0.8,
        "data_completeness_ratio": 1.0,
        "unresolved_conflict_count": 0,
    }
    values.update(overrides)
    return UncertaintyAssessment(**values)


def test_m0_uses_only_matching_labels_resolved_by_point_in_time_cutoff():
    rows = [
        observation("yes", True),
        observation("no", False),
        observation("future-label", True, resolved_at=dt(2025, 7, 2)),
        observation("other-family", True, family="travel"),
    ]

    estimate = fit_m0_event_family(
        rows,
        event_family="contract",
        training_cutoff=dt(2025, 6, 1),
        forecast_at=dt(2025, 6, 2),
    )

    assert estimate.kind is BaselineKind.M0_EVENT_FAMILY
    assert estimate.sample_size == 2
    assert estimate.positive_count == 1
    assert estimate.probability == 0.5
    estimate.assert_precedes_forecast(dt(2025, 6, 2))
    with pytest.raises(LeakageError, match="strictly precede"):
        estimate.assert_precedes_forecast(dt(2025, 6, 1))


def test_m1_is_temporal_cohort_only_and_sparse_cell_falls_back_to_m0():
    rows = [
        observation("cell-yes", True),
        observation("cell-no", False),
        observation("different-cohort", True, cohort="new"),
        observation(
            "different-month",
            True,
            target_at=dt(2025, 4, 1),
            resolved_at=dt(2025, 4, 2),
        ),
    ]
    cutoff = dt(2025, 6, 1)

    cell = fit_m1_temporal_cohort(
        rows,
        event_family="contract",
        cohort="returning",
        target_at=dt(2026, 3, 1),
        training_cutoff=cutoff,
        forecast_at=dt(2025, 6, 2),
        minimum_cell_size=2,
    )
    sparse = fit_m1_temporal_cohort(
        rows,
        event_family="contract",
        cohort="missing",
        target_at=dt(2026, 3, 1),
        training_cutoff=cutoff,
        forecast_at=dt(2025, 6, 2),
        minimum_cell_size=2,
    )

    assert cell.probability == 0.5
    assert cell.sample_size == 2
    assert cell.fallback_used is False
    assert sparse.probability == 0.75
    assert sparse.sample_size == 4
    assert sparse.fallback_used is True


def test_metrics_reliability_discrimination_and_one_class_handling():
    probabilities = [0.1, 0.2, 0.8, 0.9]
    outcomes = [0, 0, 1, 1]

    report = calibration_report(probabilities, outcomes, bin_count=2)

    assert brier_score(probabilities, outcomes) == pytest.approx(0.025)
    assert binary_log_loss(probabilities, outcomes) == pytest.approx(0.164252, abs=1e-6)
    assert expected_calibration_error(probabilities, outcomes, bin_count=2) == pytest.approx(0.15)
    assert report.discrimination_auc == 1.0
    assert [item.count for item in report.reliability_bins] == [2, 2]
    assert discrimination_auc([0.1, 0.2], [0, 0]) is None


def test_bootstrap_and_negative_control_are_deterministic_with_fixed_seed():
    def statistic(values: list[float]) -> float:
        return sum(values) / len(values)

    first = bootstrap_confidence_interval([0.0, 1.0, 1.0], statistic, resamples=100, seed=7)
    second = bootstrap_confidence_interval([0.0, 1.0, 1.0], statistic, resamples=100, seed=7)

    assert first == second
    assert first.lower <= first.estimate <= first.upper
    assert permuted_outcomes([0, 0, 1, 1, 1], seed=7) == permuted_outcomes([0, 0, 1, 1, 1], seed=7)
    assert sorted(permuted_outcomes([0, 0, 1, 1, 1], seed=7)) == [0, 0, 1, 1, 1]
    control = negative_control_report([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1], seed=7)
    assert control.observed_discrimination_auc == 1.0
    assert control.observed_brier_score == pytest.approx(0.025)


def test_probability_release_is_fail_closed_until_every_gate_passes():
    report = calibration_report([0.1, 0.1, 0.9, 0.9], [0, 0, 1, 1], bin_count=2)
    guard = ProbabilityReleaseGuard(
        minimum_samples=4,
        minimum_positive_labels=2,
        minimum_negative_labels=2,
        maximum_ece=0.11,
    )

    blocked = guard.assess(
        report,
        calibration_release_id=None,
        evaluated_on_holdout=False,
        negative_control_passed=False,
    )
    allowed = guard.assess(
        report,
        calibration_release_id="calibration-contract-test-1",
        evaluated_on_holdout=True,
        negative_control_passed=True,
    )

    assert blocked.eligible is False
    assert blocked.calibration_release_id is None
    assert len(blocked.reasons) == 3
    assert allowed.eligible is True
    assert allowed.reasons == ()


def test_point_in_time_evaluation_rejects_training_forecast_overlap():
    assert_point_in_time_split(
        training_cutoff=dt(2025, 12, 31), forecast_times=[dt(2026, 1, 1), dt(2026, 2, 1)]
    )
    with pytest.raises(ValueError, match="strictly precede"):
        assert_point_in_time_split(
            training_cutoff=dt(2025, 12, 31), forecast_times=[dt(2025, 12, 31)]
        )


def test_birth_time_ensemble_keeps_traditional_strength_non_probabilistic():
    ensemble = aggregate_birth_time_signals(
        [
            BirthTimeSignal("t-5", True, ForecastPolarity.FAVOURABLE, 8.0),
            BirthTimeSignal("t-2", True, ForecastPolarity.FAVOURABLE, 6.0),
            BirthTimeSignal("t+2", True, ForecastPolarity.FAVOURABLE, 7.0),
            BirthTimeSignal("t+5", False, ForecastPolarity.INDETERMINATE, 1.0),
        ]
    )

    assert ensemble.sample_count == 4
    assert ensemble.event_agreement_ratio == 0.75
    assert ensemble.polarity_agreement_ratio == 1.0
    assert ensemble.sensitivity is BirthTimeSensitivity.MODERATE
    assert "probability" not in asdict(ensemble)
    converted = to_uncertainty_assessment(ensemble, data_completeness_ratio=0.95)
    assert converted.sampled_birth_times == 4


@pytest.mark.parametrize(
    ("uncertainty", "kwargs", "expected"),
    [
        (assessment(data_completeness_ratio=0.5), {}, AbstentionCode.DATA_INCOMPLETE),
        (assessment(), {"out_of_distribution": True}, AbstentionCode.OUT_OF_DISTRIBUTION),
        (
            assessment(birth_time_sensitivity=BirthTimeSensitivity.HIGH),
            {},
            AbstentionCode.BIRTH_TIME_INSTABILITY,
        ),
        (
            assessment(unresolved_conflict_count=1),
            {},
            AbstentionCode.CONFLICTING_EVIDENCE,
        ),
        (
            assessment(),
            {"probability_requested": True, "calibration_release_eligible": False},
            AbstentionCode.INSUFFICIENT_EVIDENCE,
        ),
    ],
)
def test_abstention_covers_instability_conflict_ood_incomplete_and_uncalibrated(
    uncertainty: UncertaintyAssessment,
    kwargs: dict[str, bool],
    expected: AbstentionCode,
):
    result = decide_abstention(
        uncertainty,
        thresholds=AbstentionThresholds(maximum_unresolved_conflicts=0),
        **kwargs,
    )

    assert result.abstained is True
    assert result.code is expected


def test_stable_complete_calibrated_case_does_not_abstain():
    result = decide_abstention(
        assessment(), probability_requested=True, calibration_release_eligible=True
    )
    assert result.abstained is False
    assert result.code is AbstentionCode.NONE
