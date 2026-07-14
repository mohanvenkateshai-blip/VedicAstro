from __future__ import annotations

from datetime import UTC, date, datetime

from app import server
from fastapi.testclient import TestClient
from forecasting import (
    Abstention,
    AbstentionCode,
    BirthTimeSensitivity,
    CalculationProvenance,
    CertaintyTier,
    EventCode,
    ForecastMode,
    ForecastPolarity,
    ProbabilityStatus,
    TemporalGranularity,
    TimingWindow,
    UncertaintyAssessment,
    get_event_definition,
)

client = TestClient(server.app)
FORECASTS_PATH = "/v2/forecasts"


def _claim() -> dict:
    event = get_event_definition(EventCode.CONTRACT_SIGNED)
    return {
        "claim_id": "claim-v2-1",
        "forecast_id": "forecast-v2-1",
        "release_id": "release-v2-test",
        "locale": "en-IN",
        "mode": ForecastMode.FORECAST.value,
        "event_code": event.code.value,
        "event_domain": event.domain.value,
        "observable_outcome": event.observable_predicate,
        "timing": TimingWindow(
            start_on=date(2027, 9, 1),
            end_on=date(2027, 11, 30),
            resolution_due_on=date(2028, 1, 31),
            timezone="Asia/Kolkata",
            granularity=TemporalGranularity.MONTH,
            horizon_days=91,
        ).model_dump(mode="json"),
        "polarity": ForecastPolarity.FAVOURABLE.value,
        "traditional_strength_index": 7.5,
        "probability_status": ProbabilityStatus.UNCALIBRATED_SIGNAL.value,
        "base_rate": 0.12,
        "base_rate_source": "cohort-contract-90d-v1",
        "supporting_evidence_ids": ["dasha-12", "transit-8"],
        "opposing_evidence_ids": ["ashtaka-3"],
        "rule_ids": ["rule-12"],
        "citation_ids": ["source-4"],
        "provenance": CalculationProvenance(
            calculation_hash="a" * 64,
            engine_version="cvce-test",
            rule_pack_versions={"dasha": "1.0.0"},
            source_ids=("source-4",),
            citation_ids=("source-4",),
            data_cutoff_at=datetime(2026, 1, 1, tzinfo=UTC),
            calculated_at=datetime(2026, 1, 2, tzinfo=UTC),
        ).model_dump(mode="json"),
        "uncertainty": UncertaintyAssessment(
            birth_time_sensitivity=BirthTimeSensitivity.STABLE,
            sampled_birth_times=5,
            event_agreement_ratio=0.8,
            polarity_agreement_ratio=0.8,
            data_completeness_ratio=0.9,
        ).model_dump(mode="json"),
        "prerequisites": ["A specific agreement must reach execution stage."],
        "what_to_expect": ["The agreement may be ready for dated signatures."],
        "safe_next_steps": ["Review obligations and dates before signing."],
        "decision_scope": "Do not substitute this forecast for legal review.",
        "limitations": ["The signal has not been tested against observed outcomes."],
        "certainty_tier": CertaintyTier.TRADITIONAL_SIGNAL.value,
        "abstention": Abstention(
            abstained=False, code=AbstentionCode.NONE
        ).model_dump(mode="json"),
    }


def _configure(monkeypatch, *, mode: str, verbalization: bool) -> None:
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "FORECAST_V2_MODE", mode)
    monkeypatch.setattr(server.settings, "VERBALIZATION_V2", verbalization)
    monkeypatch.setattr(server.settings, "FORECAST_LEDGER_WRITE", False)


def test_off_returns_disabled_before_parsing_body(monkeypatch):
    _configure(monkeypatch, mode="off", verbalization=False)

    response = client.post(FORECASTS_PATH, content="not-json")

    assert response.status_code == 404
    assert response.json() == {"detail": "Forecast v2 is disabled"}


def test_shadow_validates_and_returns_metadata_without_brief(monkeypatch, caplog):
    _configure(monkeypatch, mode="shadow", verbalization=True)

    response = client.post(FORECASTS_PATH, json=_claim())

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "shadow"
    assert payload["verbalization_computed"] is True
    assert payload["metadata"]["contract_version"] == "1.0.0"
    assert "brief" not in payload
    assert "claim-v2-1" not in caplog.text
    assert "dasha-12" not in caplog.text


def test_on_returns_grounded_brief_and_never_exposes_score_as_probability(monkeypatch):
    _configure(monkeypatch, mode="on", verbalization=True)

    response = client.post(FORECASTS_PATH, json=_claim())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "released"
    assert payload["claim"]["polarity"] == "favourable"
    assert payload["brief"]["content_plan"]["event"]["text"].startswith(
        "The native becomes a signatory"
    )
    assert "7.5" not in response.text
    assert "uncalibrated signal" in response.text


def test_on_rejects_vague_legacy_payload_instead_of_fabricating_claim(monkeypatch):
    _configure(monkeypatch, mode="on", verbalization=True)

    response = client.post(
        FORECASTS_PATH,
        json={"prediction": "Favourable for marriage, travel and contracts", "score": 8},
    )

    assert response.status_code == 422
    assert "Favourable for marriage" not in response.text


def test_on_requires_separately_enabled_verbalizer(monkeypatch):
    _configure(monkeypatch, mode="on", verbalization=False)

    response = client.post(FORECASTS_PATH, json=_claim())

    assert response.status_code == 404
