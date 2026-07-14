from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from forecasting import (
    EVENT_TAXONOMY,
    Abstention,
    AbstentionCode,
    BirthTimeSensitivity,
    CalculationProvenance,
    CertaintyTier,
    EventCandidate,
    EventCode,
    EvidenceDirection,
    ForecastClaim,
    ForecastMode,
    ForecastPolarity,
    ProbabilityStatus,
    RuleEvidence,
    TemporalGranularity,
    TimingWindow,
    UncertaintyAssessment,
    get_event_definition,
)
from pydantic import ValidationError


def provenance() -> CalculationProvenance:
    return CalculationProvenance(
        calculation_hash="a" * 64,
        engine_version="cvce-test",
        rule_pack_versions={"vimshottari": "1.0.0"},
        source_ids=("source-1",),
        citation_ids=("citation-1",),
        data_cutoff_at=datetime(2026, 1, 1, tzinfo=UTC),
        calculated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


def timing() -> TimingWindow:
    return TimingWindow(
        start_on=date(2027, 9, 1),
        end_on=date(2027, 11, 30),
        resolution_due_on=date(2028, 1, 31),
        timezone="Europe/Dublin",
        granularity=TemporalGranularity.MONTH,
        horizon_days=91,
    )


def uncertainty() -> UncertaintyAssessment:
    return UncertaintyAssessment(
        birth_time_sensitivity=BirthTimeSensitivity.STABLE,
        sampled_birth_times=5,
        event_agreement_ratio=0.8,
        polarity_agreement_ratio=0.8,
        cross_system_agreement_ratio=0.75,
        data_completeness_ratio=0.9,
        unresolved_conflict_count=1,
    )


def claim_data() -> dict:
    event = get_event_definition(EventCode.CONTRACT_SIGNED)
    return {
        "claim_id": "claim-1",
        "forecast_id": "forecast-1",
        "release_id": "release-1",
        "locale": "en-IN",
        "mode": ForecastMode.FORECAST,
        "event_code": event.code,
        "event_domain": event.domain,
        "observable_outcome": event.observable_predicate,
        "timing": timing(),
        "polarity": ForecastPolarity.FAVOURABLE,
        "traditional_strength_index": 7.5,
        "probability_status": ProbabilityStatus.UNCALIBRATED_SIGNAL,
        "base_rate": 0.12,
        "base_rate_source": "cohort-2026-contract-90d",
        "supporting_evidence_ids": ("evidence-1",),
        "opposing_evidence_ids": ("evidence-2",),
        "rule_ids": ("rule-1", "rule-2"),
        "citation_ids": ("citation-1",),
        "provenance": provenance(),
        "uncertainty": uncertainty(),
        "what_to_expect": ("A specific agreement may reach signature stage.",),
        "safe_next_steps": ("Review obligations and dates before signing.",),
        "decision_scope": "Do not rely on this claim instead of legal or commercial review.",
        "limitations": ("The traditional signal has not been empirically calibrated.",),
        "certainty_tier": CertaintyTier.TRADITIONAL_SIGNAL,
        "abstention": Abstention(abstained=False, code=AbstentionCode.NONE),
    }


def test_taxonomy_is_complete_and_hierarchical():
    assert set(EVENT_TAXONOMY) == set(EventCode)
    for code, definition in EVENT_TAXONOMY.items():
        assert definition.code is code
        assert definition.hierarchy == (code.domain.value, code.value)
        assert definition.observable_predicate.endswith(".")
        assert definition.resolution_policy


def test_rule_evidence_and_candidate_keep_internal_scores_non_probabilistic():
    evidence = RuleEvidence(
        evidence_id="evidence-1",
        event_code=EventCode.CONTRACT_SIGNED,
        direction=EvidenceDirection.SUPPORTING,
        rule_id="rule-1",
        signal_name="Jupiter activates the contract rule",
        traditional_strength_index=3.0,
        source_confidence=0.8,
        rationale="The rule is present in the selected rule pack.",
        provenance=provenance(),
    )
    candidate = EventCandidate(
        candidate_id="candidate-1",
        event_code=EventCode.CONTRACT_SIGNED,
        timing=timing(),
        polarity=ForecastPolarity.MIXED,
        traditional_strength_index=2.0,
        supporting_evidence_ids=(evidence.evidence_id,),
        opposing_evidence_ids=("evidence-2",),
        uncertainty=uncertainty(),
        provenance=provenance(),
    )

    assert candidate.traditional_strength_index == 2.0
    assert "probability" not in candidate.model_dump()


def test_uncalibrated_internal_score_cannot_be_exposed_as_probability():
    data = claim_data()
    data["forecast_probability"] = 0.78

    with pytest.raises(ValidationError, match="only permitted for an empirically calibrated"):
        ForecastClaim(**data)


def test_calibrated_probability_requires_calibration_provenance():
    data = claim_data()
    data.update(
        probability_status=ProbabilityStatus.CALIBRATED,
        forecast_probability=0.62,
        certainty_tier=CertaintyTier.CALIBRATED_FORECAST,
    )

    with pytest.raises(ValidationError, match="calibration_release_id"):
        ForecastClaim(**data)

    data["calibration_release_id"] = "calibration-contract-2027-01"
    claim = ForecastClaim(**data)
    assert claim.forecast_probability == 0.62


def test_claim_round_trips_through_json_with_versions_and_enums():
    claim = ForecastClaim(**claim_data())

    restored = ForecastClaim.model_validate_json(claim.model_dump_json())

    assert restored == claim
    payload = restored.model_dump(mode="json")
    assert payload["contract_version"] == "1.0.0"
    assert payload["event_code"] == "contract.signed"
    assert payload["event_domain"] == "contract"
    assert payload["probability_status"] == "uncalibrated_signal"


def test_claim_rejects_broad_or_mismatched_event_semantics():
    data = claim_data()
    data["observable_outcome"] = "Career and travel are favourable."

    with pytest.raises(ValidationError, match="canonical taxonomy predicate"):
        ForecastClaim(**data)


def test_abstention_requires_indeterminate_claim_and_no_probability():
    data = claim_data()
    data.update(
        polarity=ForecastPolarity.INDETERMINATE,
        probability_status=ProbabilityStatus.UNAVAILABLE,
        certainty_tier=CertaintyTier.INSUFFICIENT_EVIDENCE,
        abstention=Abstention(
            abstained=True,
            code=AbstentionCode.BIRTH_TIME_INSTABILITY,
            reason="The event direction changes across plausible birth times.",
        ),
    )
    claim = ForecastClaim(**data)
    assert claim.abstention.abstained is True

    data["polarity"] = ForecastPolarity.FAVOURABLE
    with pytest.raises(ValidationError, match="indeterminate polarity"):
        ForecastClaim(**data)


def test_timing_window_requires_consistent_horizon_and_valid_timezone():
    with pytest.raises(ValidationError, match="inclusive timing-window length"):
        TimingWindow(
            start_on=date(2027, 1, 1),
            end_on=date(2027, 1, 31),
            resolution_due_on=date(2027, 2, 28),
            timezone="Europe/Dublin",
            granularity=TemporalGranularity.MONTH,
            horizon_days=30,
        )

    with pytest.raises(ValidationError, match="valid IANA timezone"):
        TimingWindow(
            start_on=date(2027, 1, 1),
            end_on=date(2027, 1, 1),
            resolution_due_on=date(2027, 1, 2),
            timezone="Mars/Olympus",
            granularity=TemporalGranularity.DAY,
            horizon_days=1,
        )
