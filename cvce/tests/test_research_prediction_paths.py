from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from fractions import Fraction

import pytest
from forecasting.adapters import adapt_rule_pack_output_for_research
from forecasting.canonical import stable_hash
from forecasting.ledger import IssuedForecast
from forecasting.research import (
    NativeScore,
    ResearchArtifactOrigin,
    ResearchSignalArtifact,
)
from forecasting.retrospective import (
    DataOrigin,
    RetrospectiveDataset,
    RetrospectiveRow,
    evaluate_research_retrospective,
    row_from_ledger,
)
from forecasting.uncertainty import annotate_research_forecast
from test_evidence_pipeline import adapter, context, raw_output
from test_forecast_ledger import NOW as LEDGER_NOW
from test_forecast_ledger import SUBJECT as LEDGER_SUBJECT
from test_forecast_ledger import TENANT_A, claim
from test_forecasting_science import assessment


def dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


def test_research_adapter_quarantines_each_bad_item_and_preserves_raw_semantics():
    raw = raw_output()
    raw["score"] = -900
    raw["final_verdict"] = "excellent"
    raw["factors"][0]["role"] = "probably_good"
    del raw["factors"][1]["source_confidence"]
    raw["factors"][1]["basis"] = "Unmapped prose must survive exactly."

    result = adapt_rule_pack_output_for_research(raw, adapter(), context())

    assert len(result.evidence_records) == 3
    assert [record.normalized is not None for record in result.evidence_records] == [
        False,
        False,
        True,
    ]
    assert result.evidence_records[0].raw_direction == "probably_good"
    assert result.evidence_records[1].raw_item["basis"] == "Unmapped prose must survive exactly."
    assert result.evidence_records[1].native_score == NativeScore(-2, "legacy_native")
    assert result.candidate.normalized is None
    assert result.candidate.raw_polarity == "excellent"
    assert result.candidate.native_score == NativeScore(-900, "legacy_native")
    assert result.candidate.timing == context().timing
    assert result.product_view is None


def test_research_adapter_tolerates_hostile_values_without_losing_siblings():
    raw = raw_output()
    raw["factors"].insert(0, object())
    raw["factors"][1]["weight"] = float("nan")
    raw["factors"][1]["opaque"] = b"\x00\xff"

    result = adapt_rule_pack_output_for_research(raw, adapter(), context())
    whole_input = adapt_rule_pack_output_for_research(object(), adapter(), context())  # type: ignore[arg-type]

    assert len(result.evidence_records) == 4
    assert result.evidence_records[0].errors
    assert result.evidence_records[1].raw_item["weight"] == {"__float__": "nan"}
    assert result.evidence_records[1].raw_item["opaque"] == {"__bytes_base64__": "AP8="}
    assert result.evidence_records[2].normalized is not None
    assert whole_input.evidence_records[0].item_index == -1
    assert whole_input.candidate.errors

    class HostileDict(dict):
        def __getitem__(self, key):
            raise RuntimeError(f"hostile access: {key}")

    hostile = adapt_rule_pack_output_for_research(
        HostileDict(raw_output()), adapter(), context()
    )
    assert hostile.evidence_records[0].errors
    assert hostile.candidate.errors


def test_candidate_retains_categorical_native_score_and_explicit_error():
    raw = raw_output()
    raw["score"] = "very-strong"

    result = adapt_rule_pack_output_for_research(raw, adapter(), context())

    assert result.candidate.raw_score == "very-strong"
    assert result.candidate.raw_score_error == "native score is non-numeric or non-finite"
    assert result.candidate.native_score is None
    assert result.candidate.normalized is None

    raw["score"] = Fraction(1, 3)
    fractional = adapt_rule_pack_output_for_research(raw, adapter(), context())
    assert fractional.candidate.raw_score == {
        "__fraction__": {"numerator": 1, "denominator": 3}
    }
    assert fractional.candidate.raw_score_error is not None


def test_research_abstention_is_an_annotation_and_never_erases_the_signal():
    result = annotate_research_forecast(
        assessment(data_completeness_ratio=0.2),
        polarity="unfavourable",
        forecast_probability=0.83,
        native_score=NativeScore(-42, "dasha_points"),
    )

    assert result.release_annotation.abstained is True
    assert result.polarity == "unfavourable"
    assert result.forecast_probability == 0.83
    assert result.native_score == NativeScore(-42, "dasha_points")


def _research_row(index: int, outcome: bool, *, abstained: bool) -> RetrospectiveRow:
    year = 2020 + index
    return RetrospectiveRow(
        row_id=f"research-{index}",
        subject_key=f"subj_{index:016x}",
        event_family="sensitive-event",
        forecast_at=dt(year, 1, 1),
        target_at=dt(year, 2, 1),
        point_in_time_cutoff=dt(year - 1, 12, 31),
        abstained=abstained,
        m2_score=None,
        research_probability=0.9 if outcome else 0.1,
        native_m2_score=NativeScore(900 if outcome else -800, "unbounded_points"),
        research_direction="supporting" if outcome else "opposing",
        outcome=outcome,
        resolved_at=dt(year, 2, 2),
        label_available_at=dt(year, 2, 3),
        subgroup=(("rare_school", "school-x"),),
        data_origin=DataOrigin.SYNTHETIC_TEST,
    )


def test_research_evaluation_scores_abstentions_and_exposes_small_subgroups():
    rows = (
        _research_row(1, True, abstained=True),
        _research_row(2, False, abstained=False),
    )
    dataset = RetrospectiveDataset.build(rows, evaluation_cutoff=dt(2030, 1, 1))

    run = evaluate_research_retrospective(
        dataset,
        evaluation_id="research-eval",
        preregistration_id="research-plan",
        forecast_release_ids=("lab-run",),
        code_revision="test-revision",
        evaluated_at=dt(2030, 1, 2),
        minimum_comparison_samples=2,
        minimum_class_count=1,
        minimum_subgroup_cell=3,
        bootstrap_resamples=20,
        bootstrap_seed=7,
    )

    family = run.families[0]
    m2 = next(model for model in family.models if model.model_id == "M2")
    subgroup = family.subgroup_results[0]
    assert m2.scored_count == 2
    assert m2.abstention_count == 1
    assert m2.scored_abstention_count == 1
    assert run.manifest.research_mode is True
    assert subgroup.small_sample is True
    assert subgroup.cell_size == 2
    assert subgroup.m2_brier_interval is not None
    assert family.suppressed_subgroups == ()


def test_manual_or_label_chosen_probability_is_diagnostic_without_issued_artifact():
    row = replace(
        _research_row(1, True, abstained=False),
        data_origin=DataOrigin.OBSERVED,
        snapshot_hash="a" * 64,
        research_probability=0.99,
        native_m2_score=NativeScore(99, "chosen_after_label"),
    )

    dataset = RetrospectiveDataset.build((row,), evaluation_cutoff=dt(2030, 1, 1))
    assert dataset.diagnostic_only is True


def test_ledger_constructor_populates_and_verifies_issuance_bound_artifact():
    issued_claim = claim()
    issued = IssuedForecast(
        tenant_id=TENANT_A,
        subject_key=LEDGER_SUBJECT,
        claim=issued_claim,
        issued_at=LEDGER_NOW,
        rendered_content="Issued before the outcome.",
        claim_hash=stable_hash(issued_claim),
        wording_hash=stable_hash("Issued before the outcome."),
        content_hash=stable_hash({"claim": issued_claim, "wording": "Issued before the outcome."}),
        point_in_time_cutoff=issued_claim.provenance.data_cutoff_at,
    )
    row = row_from_ledger(issued, None, event_family="contract")

    unverified = RetrospectiveDataset.build((row,), evaluation_cutoff=dt(2030, 1, 1))
    verified = RetrospectiveDataset.build_from_issued_forecasts(
        (row,), (issued,), evaluation_cutoff=dt(2030, 1, 1)
    )

    assert row.research_artifact is not None
    assert unverified.diagnostic_only is True
    assert verified.diagnostic_only is False
    with pytest.raises(ValueError, match="claim hash failed"):
        row_from_ledger(
            issued.model_copy(update={"claim_hash": ""}),
            None,
            event_family="contract",
        )


def test_research_artifact_rejects_empty_hash_and_row_signal_mismatch():
    row = replace(
        _research_row(1, True, abstained=False),
        data_origin=DataOrigin.OBSERVED,
        snapshot_hash="a" * 64,
    )
    with pytest.raises(ValueError, match="sha256 forecast snapshot hash"):
        ResearchSignalArtifact.seal(
            row_id=row.row_id,
            subject_key=row.subject_key,
            forecast_snapshot_hash="",
            issued_at=row.forecast_at,
            probability=0.9,
            native_score=row.native_m2_score,
            direction=row.research_direction,
            origin=ResearchArtifactOrigin.ISSUANCE_LEDGER,
        )
    artifact = ResearchSignalArtifact.seal(
        row_id=row.row_id,
        subject_key=row.subject_key,
        forecast_snapshot_hash=row.snapshot_hash,
        issued_at=row.forecast_at,
        probability=row.research_probability,
        native_score=row.native_m2_score,
        direction=row.research_direction,
        origin=ResearchArtifactOrigin.ISSUANCE_LEDGER,
    )
    manually_assembled = replace(row, research_artifact=artifact)
    dataset = RetrospectiveDataset.build(
        (manually_assembled,), evaluation_cutoff=dt(2030, 1, 1)
    )
    assert dataset.diagnostic_only is True
    with pytest.raises(ValueError, match="probability differs"):
        replace(row, research_probability=0.01, research_artifact=artifact)


def test_subgroup_sample_status_uses_scored_not_cell_denominator():
    rows = [_research_row(index, index % 2 == 0, abstained=False) for index in range(1, 21)]
    rows = [
        row
        if index == 0
        else replace(
            row,
            research_probability=None,
            native_m2_score=None,
            research_direction=None,
        )
        for index, row in enumerate(rows)
    ]
    dataset = RetrospectiveDataset.build(rows, evaluation_cutoff=dt(2050, 1, 1))
    run = evaluate_research_retrospective(
        dataset,
        evaluation_id="sparse-scored",
        preregistration_id="sparse-plan",
        forecast_release_ids=("lab",),
        code_revision="test",
        evaluated_at=dt(2050, 1, 2),
        minimum_comparison_samples=2,
        minimum_class_count=1,
        minimum_subgroup_cell=20,
        bootstrap_resamples=20,
    )

    subgroup = run.families[0].subgroup_results[0]
    assert subgroup.cell_size == 20
    assert subgroup.resolved_count == 20
    assert subgroup.scored_count == 1
    assert subgroup.small_sample is True
    assert subgroup.interval_is_diagnostic is True


def test_product_retrospective_still_rejects_product_score_on_abstention():
    row = _research_row(1, True, abstained=True)

    try:
        replace(row, m2_score=0.9)
    except ValueError as exc:
        assert "abstention cannot have an M2 score" in str(exc)
    else:  # pragma: no cover - makes the compatibility requirement explicit
        raise AssertionError("product invariant was weakened")


def test_legacy_retrospective_row_positional_order_is_unchanged():
    row = RetrospectiveRow(
        "legacy-row",
        "subj_0000000000000001",
        "travel",
        dt(2026, 1, 1),
        dt(2026, 2, 1),
        dt(2025, 12, 31),
        False,
        "returning",
        0.8,
        True,
        dt(2026, 2, 2),
        dt(2026, 2, 3),
        (("region", "west"),),
        "a" * 64,
        "b" * 64,
        DataOrigin.SYNTHETIC_TEST,
    )

    assert row.outcome is True
    assert row.research_probability is None
