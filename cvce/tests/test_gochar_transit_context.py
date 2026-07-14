from __future__ import annotations

from types import SimpleNamespace

import pytest
import swisseph as swe
from app import chart as chart_module
from app import server
from fastapi.testclient import TestClient
from pydantic import ValidationError

from vedic_engine.prediction import gochar as gochar_module

client = TestClient(server.app)


def _payload(**transit_overrides):
    transit = {
        "transit_instant": "2026-07-14T12:30:00+01:00",
        "transit_place": "Dublin, Ireland",
        "transit_lat": 53.3498,
        "transit_lon": -6.2603,
        "transit_timezone": "Europe/Dublin",
    }
    transit.update(transit_overrides)
    return {
        "birth_datetime": "1975-04-22T19:15:00",
        "birth_lat": 12.2958,
        "birth_lon": 76.6394,
        "birth_tz": 5.5,
        **transit,
    }


def test_ireland_timezone_requires_dst_correct_offset(monkeypatch):
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")

    response = client.post(
        "/gochar",
        json=_payload(transit_instant="2026-07-14T12:30:00+00:00"),
    )

    assert response.status_code == 422
    assert "does not match transit_timezone" in response.text


def test_mysuru_natal_context_is_preserved_while_dublin_drives_transits(monkeypatch):
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")
    place_calls = []
    real_jd_place = server.jd_place

    def recording_jd_place(dt, lat, lon, tz):
        place_calls.append((dt.isoformat(), lat, lon, tz))
        return real_jd_place(dt, lat, lon, tz)

    monkeypatch.setattr(server, "jd_place", recording_jd_place)
    monkeypatch.setattr(
        chart_module,
        "build_chart_geometry",
        lambda *_args, **_kwargs: {
            "planets": [{"planet": "Moon", "rashi": "Aries", "nakshatra": "Ashwini"}],
            "natalSign": {"Moon": 0},
            "lagna": {"rashi": "Taurus"},
        },
    )
    transit_calls = []

    def fake_gochar(**kwargs):
        transit_calls.append(kwargs)
        return SimpleNamespace(
            overall_score=0,
            overall_verdict="neutral",
            lagna_overall_score=0,
            synthesis="",
            moorthy=None,
            sade_sati=None,
            ashtama_shani=None,
            kantaka_shani=None,
            tara_balam=None,
            planet_predictions=[],
        )

    monkeypatch.setattr(gochar_module, "compute_gochar", fake_gochar)

    response = client.post("/gochar", json=_payload())

    assert response.status_code == 200, response.text
    assert place_calls == [
        ("1975-04-22T19:15:00", 12.2958, 76.6394, 5.5),
        ("2026-07-14T12:30:00", 53.3498, -6.2603, 1.0),
    ]
    assert transit_calls[0]["date_str"] == "2026-07-14"
    assert transit_calls[0]["time_str"] == "12:30"
    assert transit_calls[0]["lat"] == 53.3498
    assert transit_calls[0]["lon"] == -6.2603
    assert transit_calls[0]["tz"] == 1.0
    assert len(transit_calls[0]["transit_rows"]) == 9
    body = response.json()
    assert body["natal_context"] == {
        "birth_datetime": "1975-04-22T19:15:00",
        "birth_latitude": 12.2958,
        "birth_longitude": 76.6394,
        "birth_timezone_offset_hours": 5.5,
        "ayanamsa": "LAHIRI",
    }
    assert body["transit_context"]["timezone"] == "Europe/Dublin"
    assert body["transit_context"]["utc_instant"] == "2026-07-14T11:30:00+00:00"


def test_ireland_winter_offset_is_zero():
    request = server.GocharRequest.model_validate(
        _payload(transit_instant="2026-01-14T12:30:00+00:00")
    )

    assert request.transit_instant.utcoffset().total_seconds() == 0


def test_ireland_overlap_requires_and_enforces_explicit_occurrence():
    with pytest.raises(ValidationError, match="must be earlier or later"):
        server.GocharRequest.model_validate(
            _payload(transit_instant="2026-10-25T01:30:00+01:00")
        )

    earlier = server.GocharRequest.model_validate(
        _payload(
            transit_instant="2026-10-25T01:30:00+01:00",
            transit_disambiguation="earlier",
        )
    )
    later = server.GocharRequest.model_validate(
        _payload(
            transit_instant="2026-10-25T01:30:00+00:00",
            transit_disambiguation="later",
        )
    )

    assert earlier.transit_disambiguation == "earlier"
    assert later.transit_disambiguation == "later"
    with pytest.raises(ValidationError, match="does not match"):
        server.GocharRequest.model_validate(
            _payload(
                transit_instant="2026-10-25T01:30:00+00:00",
                transit_disambiguation="earlier",
            )
        )


def test_coordinate_timezone_mismatch_is_rejected(monkeypatch):
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")

    response = client.post(
        "/gochar",
        json=_payload(
            transit_instant="2026-07-14T12:30:00+05:30",
            transit_timezone="Asia/Kolkata",
        ),
    )

    assert response.status_code == 422
    assert "server-resolved timezone" in response.text
    assert "Europe/Dublin" in response.text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("birth_lat", 91),
        ("birth_lon", 181),
        ("birth_tz", 15),
        ("birth_lat", float("nan")),
        ("birth_lon", float("inf")),
    ],
)
def test_malformed_natal_geometry_is_rejected(field, value):
    with pytest.raises(ValidationError):
        server.GocharRequest.model_validate({**_payload(), field: value})


def test_transit_place_is_trimmed_and_blank_place_is_rejected():
    request = server.GocharRequest.model_validate(_payload(transit_place="  Dublin  "))
    assert request.transit_place == "Dublin"

    with pytest.raises(ValidationError, match="must not be blank"):
        server.GocharRequest.model_validate(_payload(transit_place="   "))


def test_unsupported_ayanamsa_is_rejected_instead_of_relabelled():
    with pytest.raises(ValidationError, match="PyJHora-supported"):
        server.GocharRequest.model_validate({**_payload(), "ayanamsa": "not-a-mode"})


def test_gochar_refuses_non_swiss_runtime_instead_of_relabelling(monkeypatch):
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")
    monkeypatch.setattr(
        server,
        "ephemeris_runtime_provenance",
        lambda _jd: {
            "engine": "PyJHora",
            "engine_version": "4.8.7",
            "backend": "Moshier analytical fallback",
            "backend_version": "2.10.03",
        },
    )

    response = client.post("/gochar", json=_payload())

    assert response.status_code == 503
    assert "refusing analytical fallback" in response.text


@pytest.mark.parametrize("ayanamsa", ["LAHIRI", "RAMAN"])
def test_real_gochar_uses_canonical_positions_and_requested_ayanamsa(monkeypatch, ayanamsa):
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")

    response = client.post("/gochar", json={**_payload(), "ayanamsa": ayanamsa})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["natal_context"]["ayanamsa"] == ayanamsa
    assert body["calculation_context"]["ayanamsa"] == ayanamsa
    assert body["calculation_context"]["replay_payload"]["ayanamsa"] == ayanamsa
    assert body["calculation_context"]["request_id"].startswith("gochar_")
    assert body["calculation_context"]["engine"] == "PyJHora"
    assert body["calculation_context"]["engine_version"] != "unknown"
    assert body["calculation_context"]["backend"] == "Swiss Ephemeris"
    assert body["calculation_context"]["backend_version"] != "unknown"

    observation_jd, observation_place = server.jd_place(
        server.parse_dt("2026-07-14T12:30:00"),
        53.3498,
        -6.2603,
        1.0,
    )
    with server.ayanamsa_context(ayanamsa):
        expected = {
            item["planet"]: item["longitude"]
            for item in server.positions(observation_jd, observation_place)
        }
    actual = {item["planet"]: item["longitude"] for item in body["planets"]}
    assert actual.keys() == expected.keys()
    for planet, longitude in expected.items():
        assert actual[planet] == pytest.approx(longitude, abs=1e-6)


def test_lahiri_and_raman_transit_longitudes_are_not_relabelled_duplicates(monkeypatch):
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")

    lahiri = client.post("/gochar", json={**_payload(), "ayanamsa": "LAHIRI"})
    raman = client.post("/gochar", json={**_payload(), "ayanamsa": "RAMAN"})

    assert lahiri.status_code == raman.status_code == 200
    lahiri_sun = next(p for p in lahiri.json()["planets"] if p["planet"] == "Sun")
    raman_sun = next(p for p in raman.json()["planets"] if p["planet"] == "Sun")
    assert abs(lahiri_sun["longitude"] - raman_sun["longitude"]) > 0.5


@pytest.mark.parametrize(
    ("ayanamsa", "sidereal_mode"),
    [("LAHIRI", swe.SIDM_LAHIRI), ("RAMAN", swe.SIDM_RAMAN)],
)
def test_canonical_positions_equal_independent_swiss_oracle(ayanamsa, sidereal_mode):
    """Compare PyJHora output with a direct Swiss calculation path.

    The oracle reconstructs the documented PyJHora position convention using
    pyswisseph directly. It does not call ``server.positions`` for expected
    values and explicitly proves that Swiss, rather than Moshier, served every
    body used by the canonical transit response.
    """
    observation_jd, observation_place = server.jd_place(
        server.parse_dt("2026-07-14T12:30:00"),
        53.3498,
        -6.2603,
        1.0,
    )
    runtime = server.ephemeris_runtime_provenance(observation_jd)
    if runtime["backend"] != "Swiss Ephemeris":
        pytest.skip("official Swiss .se1 fixtures are unavailable")

    swe.set_sid_mode(sidereal_mode)
    flags = (
        swe.FLG_SWIEPH
        | swe.FLG_SIDEREAL
        | swe.FLG_TRUEPOS
        | swe.FLG_NOGDEFL
        | swe.FLG_NONUT
        | swe.FLG_SPEED
    )
    jd_ut = observation_jd - observation_place.timezone / 24.0
    planet_ids = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mars": swe.MARS,
        "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS,
        "Saturn": swe.SATURN,
        "Rahu": swe.TRUE_NODE,
    }
    expected = {}
    for planet, planet_id in planet_ids.items():
        position, return_flags = swe.calc_ut(jd_ut, planet_id, flags)
        assert return_flags & swe.FLG_SWIEPH
        expected[planet] = position[0] % 360
    expected["Ketu"] = (expected["Rahu"] + 180) % 360

    with server.ayanamsa_context(ayanamsa):
        actual = {
            item["planet"]: item["longitude"]
            for item in server.positions(observation_jd, observation_place)
        }

    assert actual.keys() == expected.keys()
    for planet, longitude in expected.items():
        assert actual[planet] == pytest.approx(longitude, abs=1e-6)
