from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from forecasting import (
    Abstention,
    AbstentionCode,
    BirthTimeSensitivity,
    CalculationProvenance,
    CertaintyTier,
    EventCode,
    ForecastClaim,
    ForecastMode,
    ForecastPolarity,
    ProbabilityStatus,
    TemporalGranularity,
    TimingWindow,
    UncertaintyAssessment,
    get_event_definition,
)

from vedic_engine.verbalization import (
    BroadBucketError,
    ContentPlan,
    GroundingError,
    build_content_plan,
    render_prediction_brief,
    validate_grounding,
)


def _claim(**changes: object) -> ForecastClaim:
    event = get_event_definition(EventCode.CONTRACT_SIGNED)
    data: dict[str, object] = {
        "claim_id": "claim-contract-1",
        "forecast_id": "forecast-1",
        "release_id": "release-1",
        "locale": "en-IN",
        "mode": ForecastMode.FORECAST,
        "event_code": event.code,
        "event_domain": event.domain,
        "observable_outcome": event.observable_predicate,
        "timing": TimingWindow(
            start_on=date(2027, 9, 1),
            end_on=date(2027, 11, 30),
            resolution_due_on=date(2028, 1, 31),
            timezone="Asia/Kolkata",
            granularity=TemporalGranularity.MONTH,
            horizon_days=91,
        ),
        "polarity": ForecastPolarity.FAVOURABLE,
        "traditional_strength_index": 7.5,
        "probability_status": ProbabilityStatus.UNCALIBRATED_SIGNAL,
        "supporting_evidence_ids": ("dasha-12", "transit-8"),
        "opposing_evidence_ids": ("ashtaka-3",),
        "rule_ids": ("rule-12",),
        "citation_ids": ("source-4",),
        "provenance": CalculationProvenance(
            calculation_hash="a" * 64,
            engine_version="cvce-test",
            rule_pack_versions={"dasha": "1.0.0"},
            source_ids=("source-4",),
            citation_ids=("source-4",),
            data_cutoff_at=datetime(2026, 1, 1, tzinfo=UTC),
            calculated_at=datetime(2026, 1, 2, tzinfo=UTC),
        ),
        "uncertainty": UncertaintyAssessment(
            birth_time_sensitivity=BirthTimeSensitivity.STABLE,
            sampled_birth_times=5,
            event_agreement_ratio=0.8,
            polarity_agreement_ratio=0.8,
            data_completeness_ratio=0.9,
        ),
        "prerequisites": ("A specific agreement must reach execution stage.",),
        "what_to_expect": ("The agreement may be ready for dated signatures.",),
        "safe_next_steps": ("Review obligations and dates before signing.",),
        "decision_scope": "Do not substitute this forecast for legal review.",
        "limitations": ("The signal has not been tested against observed outcomes.",),
        "certainty_tier": CertaintyTier.TRADITIONAL_SIGNAL,
        "abstention": Abstention(abstained=False, code=AbstentionCode.NONE),
    }
    data.update(changes)
    return ForecastClaim(**data)


def test_en_in_brief_snapshot_is_specific_and_single_event():
    brief = render_prediction_brief(_claim())

    assert brief.concise_sentence == (
        "Favourable: the available signal supports this outcome. "
        "Expected event: The native becomes a signatory to a dated, binding contract. "
        "Window: 1 September to 30 November 2027 (month-level, Asia/Kolkata)."
    )
    assert brief.paragraphs == (
        brief.concise_sentence,
        "What to expect: The agreement may be ready for dated signatures. "
        "Prerequisites: A specific agreement must reach execution stage.",
        "Supporting evidence (2): dasha-12, transit-8. "
        "Opposing evidence (1): ashtaka-3.",
        "Safe next steps: Review obligations and dates before signing.",
        "This is a traditional, uncalibrated signal; it is not an empirical probability. "
        "Birth-time stability: stable across the tested times. "
        "The signal has not been tested against observed outcomes. "
        "Do not substitute this forecast for legal review.",
    )
    assert "travel" not in brief.concise_sentence.lower()
    assert "ceremon" not in brief.concise_sentence.lower()


@pytest.mark.parametrize(
    ("polarity", "expected"),
    (
        (ForecastPolarity.FAVOURABLE, "Favourable: the available signal supports"),
        (ForecastPolarity.UNFAVOURABLE, "Unfavourable: the available signal weighs against"),
        (ForecastPolarity.MIXED, "Mixed: supporting and opposing signals are both present."),
        (ForecastPolarity.INDETERMINATE, "Indeterminate: the available signal has no stable direction."),
    ),
)
def test_implication_preserves_direction_without_claiming_certainty(polarity, expected):
    plan = build_content_plan(_claim(polarity=polarity))
    assert plan.implication.text.startswith(expected)


def test_calibrated_probability_and_release_are_rendered_without_strength_as_probability():
    claim = _claim(
        probability_status=ProbabilityStatus.CALIBRATED,
        forecast_probability=0.62,
        calibration_release_id="cal-contract-3",
        certainty_tier=CertaintyTier.CALIBRATED_FORECAST,
    )

    assert build_content_plan(claim).probability.text == (
        "Calibrated forecast probability: 62% (release cal-contract-3)."
    )


def test_abstention_snapshot_does_not_imply_an_outcome():
    claim = _claim(
        polarity=ForecastPolarity.INDETERMINATE,
        probability_status=ProbabilityStatus.UNAVAILABLE,
        uncertainty=UncertaintyAssessment(
            birth_time_sensitivity=BirthTimeSensitivity.HIGH,
            sampled_birth_times=5,
            event_agreement_ratio=0.4,
            polarity_agreement_ratio=0.2,
            data_completeness_ratio=0.9,
        ),
        certainty_tier=CertaintyTier.INSUFFICIENT_EVIDENCE,
        abstention=Abstention(
            abstained=True,
            code=AbstentionCode.BIRTH_TIME_INSTABILITY,
            reason="The direction changes across plausible birth times.",
        ),
    )
    brief = render_prediction_brief(claim)

    assert brief.concise_sentence == (
        "No prediction is issued: The direction changes across plausible birth times. "
        "Window assessed: Window: 1 September to 30 November 2027 "
        "(month-level, Asia/Kolkata)."
    )
    assert "supports this outcome" not in " ".join(brief.paragraphs)
    assert "weighs against" not in " ".join(brief.paragraphs)


def test_t3_policy_blocks_and_does_not_retain_unsafe_text_in_plan_or_brief():
    claim = _claim(what_to_expect=("You will be diagnosed with cancer.",))
    brief = render_prediction_brief(claim)
    rendered = brief.model_dump_json()

    assert brief.content_plan.abstention is not None
    assert brief.content_plan.expectations == ()
    assert "cancer" not in rendered.lower()
    assert "blocked high-severity topic" in rendered


def test_broad_bucket_soup_is_rejected_instead_of_rendered():
    claim = _claim(
        what_to_expect=(
            "Good for marriage, ceremonies, travel, contracts and education.",
        )
    )
    with pytest.raises(BroadBucketError, match="one observable claim"):
        render_prediction_brief(claim)


def test_grounding_validator_rejects_modified_assertion():
    claim = _claim()
    plan = build_content_plan(claim)
    altered = ContentPlan.model_validate(
        {
            **plan.model_dump(),
            "event": {
                "text": "You will definitely sign a lucrative contract.",
                "source_paths": ("observable_outcome",),
            },
        }
    )

    with pytest.raises(GroundingError, match="not grounded"):
        validate_grounding(altered, claim)


def test_evidence_identifier_cannot_inject_prediction_prose():
    claim = _claim(supporting_evidence_ids=("You will definitely sign it.",))

    with pytest.raises(ValueError, match="unsafe display identifier"):
        render_prediction_brief(claim)
