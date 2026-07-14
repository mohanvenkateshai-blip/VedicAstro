from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from forecasting.retrospective import (
    DataOrigin,
    EvidenceStatus,
    RetrospectiveDataset,
    RetrospectiveLeakageError,
    RetrospectiveRow,
    evaluate_retrospective,
)


def dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


def row(
    index: int,
    outcome: bool | None,
    *,
    family: str = "travel",
    abstained: bool = False,
    score: float | None = 0.8,
    subgroup: tuple[tuple[str, str], ...] = (("region", "west"),),
) -> RetrospectiveRow:
    year = 2020 + index
    return RetrospectiveRow(
        row_id=f"row-{index}-{family}",
        subject_key=f"subj_{index:016x}",
        event_family=family,
        forecast_at=dt(year, 1, 1),
        target_at=dt(year, 2, 1),
        point_in_time_cutoff=dt(year - 1, 12, 31),
        abstained=abstained,
        cohort="returning",
        m2_score=None if abstained else score,
        outcome=outcome,
        resolved_at=dt(year, 2, 2) if outcome is not None else None,
        label_available_at=dt(year, 2, 3) if outcome is not None else None,
        subgroup=subgroup,
        snapshot_hash="a" * 64,
        resolution_hash="b" * 64 if outcome is not None else None,
        data_origin=DataOrigin.SYNTHETIC_TEST,
    )


def evaluate(dataset: RetrospectiveDataset):
    return evaluate_retrospective(
        dataset,
        evaluation_id="retro-test-1",
        preregistration_id="prereg-test-1",
        forecast_release_ids=("release-1",),
        code_revision="deadbeef",
        evaluated_at=dt(2035, 1, 2),
        minimum_comparison_samples=4,
        minimum_class_count=2,
        minimum_subgroup_cell=3,
        bootstrap_resamples=100,
        bootstrap_seed=7,
    )


def test_rejects_point_in_time_and_future_label_leakage():
    with pytest.raises(RetrospectiveLeakageError, match="precede issuance"):
        replace(row(1, True), point_in_time_cutoff=dt(2021, 1, 1))

    future = row(10, True)
    with pytest.raises(RetrospectiveLeakageError, match="future label"):
        RetrospectiveDataset.build((future,), evaluation_cutoff=dt(2030, 2, 2))


def test_preserves_unresolved_misses_and_abstentions_in_denominators():
    rows = (row(1, True), row(2, False, score=None), row(3, True, abstained=True), row(4, None))
    run = evaluate(RetrospectiveDataset.build(rows, evaluation_cutoff=dt(2035, 1, 1)))
    family = run.families[0]
    m2 = next(model for model in family.models if model.model_id == "M2")

    assert family.issued_count == 4
    assert family.unresolved_count == 1
    assert m2.resolved_count == 3
    assert m2.scored_count == 1
    assert m2.missing_score_count == 2
    assert m2.abstention_count == 1


def test_families_are_never_pooled_and_sparse_subgroups_are_suppressed():
    rows = (row(1, True), row(2, False), row(3, True, family="contract"))
    run = evaluate(RetrospectiveDataset.build(rows, evaluation_cutoff=dt(2035, 1, 1)))

    assert [item.event_family for item in run.families] == ["contract", "travel"]
    assert sum(item.issued_count for item in run.families) == 3
    assert all("region=west" in item.suppressed_subgroups for item in run.families)


def test_negative_controls_sample_gates_and_no_probability_release():
    rows = tuple(row(i, i % 2 == 0, score=0.9 if i % 2 == 0 else 0.1) for i in range(1, 7))
    run = evaluate(RetrospectiveDataset.build(rows, evaluation_cutoff=dt(2035, 1, 1)))
    family = run.families[0]
    m2 = next(model for model in family.models if model.model_id == "M2")

    assert m2.negative_control is not None
    assert m2.negative_control.observed_brier_score < m2.negative_control.permuted_brier_score
    assert family.comparisons[0].evidence_status in {
        EvidenceStatus.POSITIVE_BOUND_ABOVE_ZERO,
        EvidenceStatus.BOUND_CROSSES_ZERO,
    }
    assert run.manifest.diagnostic_only is True
    assert run.manifest.probability_release_eligible is False


def test_insufficient_samples_never_claim_incremental_skill():
    rows = (row(1, True), row(2, False), row(3, True))
    run = evaluate(RetrospectiveDataset.build(rows, evaluation_cutoff=dt(2035, 1, 1)))

    assert all(comparison.claim_supported is False for comparison in run.families[0].comparisons)
    assert all(
        comparison.evidence_status
        in {EvidenceStatus.INSUFFICIENT_SAMPLES, EvidenceStatus.BASELINE_UNAVAILABLE}
        for comparison in run.families[0].comparisons
    )


def test_fixed_inputs_seed_and_ids_produce_identical_json_and_hash():
    rows = tuple(row(i, i % 2 == 0) for i in range(1, 6))
    dataset_a = RetrospectiveDataset.build(rows, evaluation_cutoff=dt(2035, 1, 1))
    dataset_b = RetrospectiveDataset.build(reversed(rows), evaluation_cutoff=dt(2035, 1, 1))
    first = evaluate(dataset_a)
    second = evaluate(dataset_b)

    assert dataset_a.input_hash == dataset_b.input_hash
    assert first.result_hash == second.result_hash
    assert json.loads(first.to_json()) == json.loads(second.to_json())


def test_contaminated_data_is_rejected_even_for_diagnostics():
    contaminated = replace(row(1, True), data_origin=DataOrigin.CONTAMINATED)
    with pytest.raises(RetrospectiveLeakageError, match="contaminated"):
        RetrospectiveDataset.build((contaminated,), evaluation_cutoff=dt(2035, 1, 1))
