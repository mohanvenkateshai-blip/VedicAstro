from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from forecasting import (
    AdapterContext,
    BirthTimeSensitivity,
    CandidateFieldMap,
    EventCode,
    EvidenceDirection,
    EvidenceFieldMap,
    EvidencePipeline,
    ForecastPolarity,
    LegacyAdapterError,
    LegacyRulePackAdapter,
    ReplayRecord,
    RulePackDescriptor,
    TemporalGranularity,
    TimingWindow,
    UncertaintyAssessment,
    artifact_hash,
)


def adapter() -> LegacyRulePackAdapter:
    """Map the current dasha-intelligence shape without importing its engine."""

    return LegacyRulePackAdapter(
        descriptor=RulePackDescriptor("vimshottari_dasha", "1.0.0"),
        event_code=EventCode.CONTRACT_SIGNED,
        evidence=EvidenceFieldMap(
            items_path=("factors",),
            rule_id="rule_id",
            signal_name="signal",
            direction="role",
            traditional_strength_index="weight",
            source_confidence="source_confidence",
            rationale="basis",
            source_ids="source_ids",
            citation_ids="citation_ids",
            direction_values={
                "mitigating": EvidenceDirection.SUPPORTING,
                "aggravating": EvidenceDirection.OPPOSING,
                "context": EvidenceDirection.CONTEXT,
            },
        ),
        candidate=CandidateFieldMap(
            traditional_strength_index_path=("score",),
            polarity_path=("final_verdict",),
            polarity_values={
                "favourable": ForecastPolarity.FAVOURABLE,
                "challenging": ForecastPolarity.UNFAVOURABLE,
                "mixed": ForecastPolarity.MIXED,
            },
        ),
    )


def raw_output() -> dict:
    return {
        "maha_lord": "Jupiter",
        "antar_lord": "Saturn",
        "score": 2,
        "final_verdict": "mixed",
        "factors": [
            {
                "rule_id": "dasha.contract.jupiter",
                "signal": "Jupiter contract-house activation",
                "role": "mitigating",
                "weight": 4,
                "source_confidence": 0.8,
                "basis": "Rule matched the configured house activation.",
                "source_ids": ["bphs-dasha"],
                "citation_ids": ["bphs-42"],
            },
            {
                "rule_id": "dasha.contract.saturn-delay",
                "signal": "Saturn delay condition",
                "role": "aggravating",
                "weight": -2,
                "source_confidence": 0.7,
                "basis": "Rule matched the configured delay condition.",
                "source_ids": ["phaladeepika-dasha"],
                "citation_ids": ["pd-20"],
            },
            {
                "rule_id": "dasha.period.context",
                "signal": "Antardasha boundary",
                "role": "context",
                "weight": 0,
                "source_confidence": 1.0,
                "basis": "Period boundary was calculated by the legacy engine.",
                "source_ids": ["cvce-ephemeris"],
                "citation_ids": [],
            },
        ],
    }


def context() -> AdapterContext:
    return AdapterContext(
        engine_version="cvce-legacy-2026.07",
        data_cutoff_at=datetime(2026, 7, 1, tzinfo=UTC),
        calculated_at=datetime(2026, 7, 14, tzinfo=UTC),
        timing=TimingWindow(
            start_on=date(2026, 8, 1),
            end_on=date(2026, 8, 31),
            resolution_due_on=date(2026, 10, 1),
            timezone="Europe/Dublin",
            granularity=TemporalGranularity.MONTH,
            horizon_days=31,
        ),
        uncertainty=UncertaintyAssessment(
            birth_time_sensitivity=BirthTimeSensitivity.UNKNOWN,
            data_completeness_ratio=0.85,
            unresolved_conflict_count=1,
            notes=("Legacy adapter does not estimate birth-time stability.",),
        ),
        prerequisites=("A contract reaches executable form.",),
        alternate_manifestations=("Negotiation continues without signature.",),
        disconfirmers=("No binding agreement is signed in the window.",),
    )


def test_pipeline_preserves_supporting_opposing_context_and_rule_pack_provenance():
    result = EvidencePipeline(adapter()).run(raw_output(), context())

    assert [item.direction for item in result.evidence] == [
        EvidenceDirection.SUPPORTING,
        EvidenceDirection.OPPOSING,
        EvidenceDirection.CONTEXT,
    ]
    assert result.candidate.supporting_evidence_ids == (result.evidence[0].evidence_id,)
    assert result.candidate.opposing_evidence_ids == (result.evidence[1].evidence_id,)
    assert result.candidate.polarity is ForecastPolarity.MIXED
    assert result.candidate.traditional_strength_index == 2
    assert result.candidate.provenance.rule_pack_versions == {"vimshottari_dasha": "1.0.0"}
    assert result.candidate.provenance.source_ids == (
        "bphs-dasha",
        "cvce-ephemeris",
        "phaladeepika-dasha",
    )
    assert len(result.conflicts) == 1
    assert result.conflicts[0].supporting_evidence_ids == (
        result.evidence[0].evidence_id,
    )
    assert "probability" not in result.candidate.model_dump()


def test_ids_and_artifacts_are_stable_and_change_with_canonical_inputs():
    pipeline = EvidencePipeline(adapter())
    first = pipeline.run(raw_output(), context())
    reordered = {
        "factors": raw_output()["factors"],
        "final_verdict": "mixed",
        "score": 2,
        "antar_lord": "Saturn",
        "maha_lord": "Jupiter",
    }
    second = pipeline.run(reordered, context())

    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.provenance.calculation_hash == second.candidate.provenance.calculation_hash
    assert artifact_hash(first) == artifact_hash(second)

    changed = raw_output()
    changed["score"] = 1
    third = pipeline.run(changed, context())
    assert third.candidate.candidate_id != first.candidate.candidate_id
    assert artifact_hash(third) != artifact_hash(first)


def test_capture_and_replay_reproduce_the_exact_normalized_artifacts():
    record = ReplayRecord.capture(raw_output(), adapter(), context())

    replayed = record.replay()

    assert artifact_hash(replayed) == record.expected_artifact_hash
    assert replayed.candidate.provenance.calculation_hash == replayed.evidence[0].provenance.calculation_hash


def test_adapter_refuses_unknown_semantics_instead_of_guessing():
    raw = raw_output()
    raw["factors"][0]["role"] = "probably_good"
    with pytest.raises(LegacyAdapterError, match="unmapped evidence direction"):
        EvidencePipeline(adapter()).run(raw, context())

    raw = raw_output()
    raw["final_verdict"] = "excellent"
    with pytest.raises(LegacyAdapterError, match="unmapped candidate polarity"):
        EvidencePipeline(adapter()).run(raw, context())


def test_adapter_rejects_incomplete_evidence_instead_of_dropping_it():
    raw = raw_output()
    del raw["factors"][1]["source_confidence"]

    with pytest.raises(LegacyAdapterError, match="source_confidence"):
        EvidencePipeline(adapter()).run(raw, context())
