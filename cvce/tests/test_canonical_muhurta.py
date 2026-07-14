from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from app import server


client = TestClient(server.app)


def _payload(**overrides):
    birth_datetime = "1975-04-22T19:15:00"
    natal_jd, _ = server.jd_place(datetime.fromisoformat(birth_datetime), 12.2958, 76.6394, 5.5)
    payload = {
        "birth_datetime": birth_datetime,
        "birth_lat": 12.2958,
        "birth_lon": 76.6394,
        "birth_tz": 5.5,
        "ayanamsa": "LAHIRI",
        "transit_instant": "2026-07-14T09:15:00+01:00",
        "transit_place": "Dublin, Ireland",
        "transit_lat": 53.3498,
        "transit_lon": -6.2603,
        "transit_timezone": "Europe/Dublin",
        "transit_disambiguation": "exact",
        "expected_natal_jd": natal_jd,
    }
    payload.update(overrides)
    return payload


def _enable(monkeypatch):
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")
    monkeypatch.setattr(server.settings, "NATIVE_MUHURTA_RESEARCH_ENABLED", True)
    monkeypatch.setattr(
        server,
        "ephemeris_runtime_provenance",
        lambda _jd: {
            "engine": "PyJHora",
            "engine_version": "test",
            "backend": "Swiss Ephemeris",
            "backend_version": "test",
        },
    )
    server._rate_limit_store.clear()


def test_route_fails_closed_by_default(monkeypatch):
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")
    monkeypatch.setattr(server.settings, "NATIVE_MUHURTA_RESEARCH_ENABLED", False)
    response = client.post("/muhurta/canonical", json=_payload())
    assert response.status_code == 404


def test_canonical_response_has_verified_identity_and_no_fallback(monkeypatch):
    _enable(monkeypatch)
    response = client.post("/muhurta/canonical", json=_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["calculation_context"] == {
        **body["calculation_context"],
        "engine": "PyJHora",
        "backend": "Swiss Ephemeris",
        "ayanamsa": "LAHIRI",
        "calculation_path": "app.ephem + jhora.panchanga.drik",
        "fallback_used": False,
    }
    assert body["natal_context"]["identity_verified"] is True
    assert body["natal_context"]["jd"] == _payload()["expected_natal_jd"]
    assert body["election_context"]["timezone_source"] == "server_coordinate_resolution"


def test_coordinate_timezone_mismatch_is_rejected(monkeypatch):
    _enable(monkeypatch)
    response = client.post(
        "/muhurta/canonical",
        json=_payload(
            transit_instant="2026-07-14T09:15:00+05:30",
            transit_timezone="Asia/Kolkata",
        ),
    )
    assert response.status_code == 422
    assert "server-resolved timezone" in response.text


def test_moshier_backend_is_refused_without_calculating_a_result(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(
        server,
        "ephemeris_runtime_provenance",
        lambda _jd: {
            "engine": "PyJHora",
            "engine_version": "test",
            "backend": "Moshier analytical fallback",
            "backend_version": "test",
        },
    )
    response = client.post("/muhurta/canonical", json=_payload())
    assert response.status_code == 503
    assert "refusing Moshier analytical fallback" in response.text


def test_loaded_natal_identity_mismatch_is_rejected(monkeypatch):
    _enable(monkeypatch)
    response = client.post(
        "/muhurta/canonical",
        json=_payload(expected_natal_jd=_payload()["expected_natal_jd"] + 0.01),
    )
    assert response.status_code == 409


def test_swiss_karana_projection_fixes_the_recorded_july_case(monkeypatch):
    _enable(monkeypatch)
    response = client.post("/muhurta/canonical", json=_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    # PyJHora index 60 is the fixed Naga Karana. The old generic modulo
    # projection incorrectly labelled that Swiss result as Taitila.
    assert body["panchanga"]["karana"] == {
        "name": "Naga",
        "num": 60,
        "verdict": "neutral",
    }
    # Regression for the removed modulo projection: index 60 was mislabeled.
    assert server.KARANA_NAMES[(60 - 1) % 11] == "Taitila"


def test_swiss_karana_projection_fixes_the_recorded_october_case(monkeypatch):
    _enable(monkeypatch)
    payload = _payload(
        transit_instant="2026-10-25T01:30:00+00:00",
        transit_disambiguation="later",
    )
    response = client.post("/muhurta/canonical", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["panchanga"]["karana"]["name"] == "Vanija"
    # Regression for the removed modulo projection: index 28 was mislabeled.
    assert server.KARANA_NAMES[(28 - 1) % 11] == "Gara"


def test_hardened_legacy_models_reject_missing_bounds_and_extra_fields():
    assert client.post("/predict", json={}).status_code == 422
    assert client.post(
        "/predict",
        json={"date": "2026-07-14", "time": "09:15", "lat": 999, "lon": 0, "tz": 0},
    ).status_code == 422


def test_canonical_request_rejects_malformed_or_impossible_birth_datetime(monkeypatch):
    _enable(monkeypatch)
    for invalid in (
        "not-a-date",
        "2026-02-30T12:00:00",
        "2026-07-14T09:15",
        "2026-07-14T09:15:00+01:00",
    ):
        response = client.post(
            "/muhurta/canonical",
            json=_payload(birth_datetime=invalid),
        )
        assert response.status_code == 422, (invalid, response.text)
        assert "birth_datetime" in response.text
    assert client.post(
        "/rahu-kalam",
        json={"datetime": "2026-07-14T09:15:00", "lat": 53, "lon": -6, "tz_offset": 1, "extra": True},
    ).status_code == 422
