from __future__ import annotations

import sys
from types import SimpleNamespace

from app import server
from knowledge_engine.engine import KnowledgeEngine
from prediction_policy import (
    BLOCKED_CLAIM_TEXT,
    apply_product_claim_policy,
    filter_personalised_claim_text,
    prepare_external_narration_payload,
)


def test_claim_filter_retains_safe_sentences_and_blocks_t3_claims():
    result = filter_personalised_claim_text(
        "Contract discussions may move forward this month. "
        "You will be diagnosed with cancer. Travel plans may need flexibility."
    )

    assert result.value == (
        "Contract discussions may move forward this month. "
        "Travel plans may need flexibility."
    )
    assert result.blocked_count == 1
    assert result.blocked_categories == ("serious_disease_diagnosis",)


def test_claim_filter_covers_each_t3_category():
    claims = {
        "death_or_fatality": "You will die during this period.",
        "suicide_or_self_harm": "There is a risk of suicide.",
        "violence_or_assassination": "You will face a violent attack.",
        "serious_disease_diagnosis": "You will suffer a heart attack.",
        "pregnancy_outcome": "A pregnancy outcome is indicated.",
        "crime_or_arrest": "You are likely to be arrested.",
        "abuse": "Your partner will become abusive.",
        "infidelity": "Your spouse will commit infidelity.",
        "named_third_party_tragedy": "Your brother will face a tragic event.",
    }

    for category, claim in claims.items():
        result = filter_personalised_claim_text(claim)
        assert result.value == BLOCKED_CLAIM_TEXT
        assert category in result.blocked_categories


def test_claim_filter_blocks_review_adversarial_phrases():
    phrases = (
        "The native may not survive this period.",
        "A deadly accident is indicated.",
        "The client may end their own life.",
        "A malignant condition confirmed by doctors is likely.",
        "There may be loss of an unborn child.",
        "A spouse affair is expected.",
        "The native may enter police custody.",
    )

    for phrase in phrases:
        result = filter_personalised_claim_text(phrase)
        assert result.value == BLOCKED_CLAIM_TEXT, phrase
        assert result.blocked_count == 1, phrase


def test_recursive_policy_returns_copy_and_audit_without_retaining_unsafe_text():
    original = {
        "prediction": "A promotion is possible. Your spouse will die.",
        "nested": ["Travel may be delayed."],
    }

    result = apply_product_claim_policy(original)

    assert original["prediction"].endswith("will die.")
    assert result.value is not original
    assert result.value["prediction"] == "A promotion is possible."
    assert result.value["nested"] == ["Travel may be delayed."]
    assert result.blocked_count == 1
    assert result.blocked_categories == ("death_or_fatality",)


def test_external_payload_drops_and_redacts_birth_and_life_event_pii():
    birth = {
        "name": "Asha Example",
        "birth_datetime": "1990-01-02T03:04:00",
        "birth_lat": 12.345,
        "birth_lon": 67.89,
        "birth_tz": 5.5,
    }
    facts = {
        "dasha_intelligence": {
            "maha_lord": "Jupiter",
            "antar_lord": "Venus",
            "final_verdict": "shubh",
            "score": 6,
            "maha_houses": [2, 5],
            "summary": "Asha Example was born on 1990-01-02 at 03:04:00.",
            "birth_lat": 12.345,
            "coordinates": [12.345, 67.89],
            "life_events": [{"description": "Private divorce details"}],
            "safe_signal": "Career discussions may progress.",
            "unsafe_signal": "The native will be arrested.",
            "alias": "Client AX-194",
            "place": "Mysore, Karnataka",
            "reformatted_birth": "2 January 1990 at 3:04 AM",
        },
        "meta": birth,
    }

    payload = prepare_external_narration_payload(
        facts, birth, allowed_sources=("dasha_intelligence",)
    )
    rendered = repr(payload)

    assert "Asha Example" not in rendered
    assert "1990-01-02" not in rendered
    assert "03:04:00" not in rendered
    assert "12.345" not in rendered
    assert "67.89" not in rendered
    assert "Private divorce details" not in rendered
    assert "arrested" not in rendered
    assert "Client AX-194" not in rendered
    assert "Mysore" not in rendered
    assert "2 January 1990" not in rendered
    assert "Career discussions" not in rendered
    assert payload == {
        "dasha_intelligence": {
            "maha_lord": "Jupiter",
            "antar_lord": "Venus",
            "final_verdict": "shubh",
            "score": 6,
            "maha_houses": [2, 5],
        }
    }


def test_llm_boundary_uses_deidentified_prompt_and_filters_model_output(monkeypatch):
    captured: dict[str, str] = {}

    class FakeModels:
        def generate_content(self, *, model, contents):
            captured["model"] = model
            captured["contents"] = contents
            return SimpleNamespace(
                text="Contract talks may advance. You will be diagnosed with cancer."
            )

    class FakeClient:
        def __init__(self, *, api_key):
            captured["api_key"] = api_key
            self.models = FakeModels()

    fake_genai = SimpleNamespace(Client=FakeClient)
    fake_google = SimpleNamespace(genai=fake_genai)
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setenv("CVCE_LLM_NARRATION", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    engine = object.__new__(KnowledgeEngine)
    engine.is_knowledge_healthy = lambda: True
    engine._resolve_narration_sources = lambda facts: (["dasha_intelligence"], [])

    narration = engine.get_llm_narration(
        {
            "dasha_intelligence": {
                "maha_lord": "Jupiter",
                "antar_lord": "Venus",
                "final_verdict": "shubh",
                "score": 5,
                "summary": "Asha Example, born 1990-01-02, may sign a contract.",
                "birth_lat": 12.345,
                "alias": "AX-194",
                "place": "Mysore",
                "reformatted_birth": "2 January 1990 at 3:04 AM",
            }
        },
        {
            "name": "Asha Example",
            "birth_datetime": "1990-01-02T03:04:00",
            "birth_lat": 12.345,
            "birth_lon": 67.89,
        },
    )

    prompt = captured["contents"]
    assert "Asha Example" not in prompt
    assert "1990-01-02" not in prompt
    assert "03:04:00" not in prompt
    assert "12.345" not in prompt
    assert "67.89" not in prompt
    assert "AX-194" not in prompt
    assert "Mysore" not in prompt
    assert "2 January 1990" not in prompt
    assert "may sign a contract" not in prompt
    assert '"maha_lord": "Jupiter"' in prompt
    assert narration["prose"] == "Contract talks may advance."
    assert narration["claim_safety"]["status"] == "filtered"
    assert narration["claim_safety"]["blocked_categories"] == [
        "serious_disease_diagnosis"
    ]


def test_llm_flag_off_is_deterministic_and_does_not_touch_provider(monkeypatch):
    monkeypatch.delenv("CVCE_LLM_NARRATION", raising=False)
    engine = object.__new__(KnowledgeEngine)

    assert engine.get_llm_narration({"dasha_intelligence": {}}, {"name": "Asha"}) is None


def test_llm_data_block_is_deterministic_and_does_not_touch_provider(monkeypatch):
    monkeypatch.setenv("CVCE_LLM_NARRATION", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    engine = object.__new__(KnowledgeEngine)
    engine.is_knowledge_healthy = lambda: True
    engine._resolve_narration_sources = lambda facts: ([], ["dasha_intelligence"])

    assert engine.get_llm_narration(
        {"dasha_intelligence": {"summary": "Career discussions may progress."}},
        {"name": "Asha"},
    ) == {
        "status": "blocked",
        "reason": "all narration sources blocked",
        "sources_blocked": ["dasha_intelligence"],
    }


def test_every_personalised_prediction_route_has_product_policy_boundary():
    endpoints = {route.path: route.endpoint for route in server.app.routes}

    assert server._PERSONALISED_PREDICTION_PATHS <= endpoints.keys()
    for path in server._PERSONALISED_PREDICTION_PATHS:
        assert getattr(endpoints[path], "_product_claim_policy", None) == "personalised-t3-v1", path


def test_product_endpoint_boundary_filters_nested_narrative_values():
    result = server._product_safe_prediction_response(
        {
            "summary": "Career discussions may progress. The native may not survive.",
            "nested": {"effects": ["A spouse affair is expected."]},
        }
    )
    rendered = repr(result).lower()

    assert "not survive" not in rendered
    assert "spouse affair" not in rendered
    assert result["summary"] == "Career discussions may progress."
    assert result["claim_safety"]["status"] == "filtered"
    assert result["claim_safety"]["blocked_count"] == 2


def test_structural_cancer_rashi_and_benign_medical_education_are_preserved():
    payload = {
        "natal": {"moon": {"rashi": "Cancer"}},
        "educational_note": "Cancer screening can support early medical care.",
        "summary": "Preventive cancer screening can support general health.",
    }

    result = server._product_safe_prediction_response(payload)

    assert result["natal"]["moon"]["rashi"] == "Cancer"
    assert result["educational_note"] == payload["educational_note"]
    assert result["summary"] == payload["summary"]
    assert result["claim_safety"]["status"] == "passed"
