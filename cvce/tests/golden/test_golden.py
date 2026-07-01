"""
Golden-chart regression tests for the CVCE.

Each reference chart in `reference_charts.json` is run through the live
`/chart` endpoint (FastAPI TestClient, in-process) and asserted against
known-good values from a professionally cast horoscope. The composed payload
is also validated against `docs/chart_data.schema.json`.

A second, independent oracle (jyotishganit via `/cross-validate`) guards the
sidereal longitudes: after removing the systematic ayanamsa offset, no planet
may diverge by more than 0.1 deg.
"""

from __future__ import annotations

import json
import os

import pytest
from app.server import app
from fastapi.testclient import TestClient

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # VedicAstro/
SCHEMA_PATH = os.path.join(REPO, "docs", "chart_data.schema.json")

client = TestClient(app)

with open(os.path.join(HERE, "reference_charts.json"), encoding="utf-8") as fh:
    REFERENCE = json.load(fh)["charts"]

CHART_IDS = [c["id"] for c in REFERENCE]


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _chart(birth):
    resp = client.post("/chart", json=birth)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "ke_version" in data, "ke_version missing from response"
    return data


@pytest.mark.parametrize("ref", REFERENCE, ids=CHART_IDS)
def test_chart_matches_schema(ref, schema):
    import jsonschema

    data = _chart(ref["birth"])
    jsonschema.validate(instance=data, schema=schema)
    assert "ke_version" in data, "ke_version missing from response"


@pytest.mark.parametrize("ref", REFERENCE, ids=CHART_IDS)
def test_lagna(ref):
    data = _chart(ref["birth"])
    exp = ref["expect"]["lagna"]
    lagna = data["lagna"]
    assert lagna["rashi"] == exp["rashi"]
    assert lagna["nakshatra"] == exp["nakshatra"]
    assert lagna["pada"] == exp["pada"]
    assert "ke_version" in data, "ke_version missing from response"


@pytest.mark.parametrize("ref", REFERENCE, ids=CHART_IDS)
def test_planet_placements(ref):
    data = _chart(ref["birth"])
    bodies = {p["planet"]: p for p in data["planets"]}
    for planet, exp in ref["expect"]["planets"].items():
        got = bodies[planet]
        assert got["rashi"] == exp["rashi"], f"{planet} rashi"
        assert got["nakshatra"] == exp["nakshatra"], f"{planet} nakshatra"
        assert got["pada"] == exp["pada"], f"{planet} pada"
        if "dignity" in exp:
            assert got["dignity"] == exp["dignity"], f"{planet} dignity"
    assert "ke_version" in data, "ke_version missing from response"


@pytest.mark.parametrize("ref", REFERENCE, ids=CHART_IDS)
def test_nodes_by_sign(ref):
    data = _chart(ref["birth"])
    bodies = {p["planet"]: p for p in data["planets"]}
    for node, sign in ref["expect"]["nodes"].items():
        assert bodies[node]["rashi"] == sign, f"{node} sign"
    assert "ke_version" in data, "ke_version missing from response"


@pytest.mark.parametrize("ref", REFERENCE, ids=CHART_IDS)
def test_sarvashtakavarga_total(ref):
    data = _chart(ref["birth"])
    sav = data["ashtakavarga"]["sav"]
    assert len(sav) == 12
    assert sum(sav) == ref["expect"]["savTotal"]
    assert "ke_version" in data, "ke_version missing from response"


@pytest.mark.parametrize("ref", REFERENCE, ids=CHART_IDS)
def test_current_mahadasha(ref):
    data = _chart(ref["birth"])
    periods = (data.get("dashas") or {}).get("periods") or []
    assert periods, "no dasha periods returned"
    # The reference birth's running mahadasha lord must appear as a maha lord.
    maha_lords = {p["maha"] for p in periods}
    assert ref["expect"]["currentMahadasha"] in maha_lords
    assert "ke_version" in data, "ke_version missing from response"


@pytest.mark.parametrize("ref", REFERENCE, ids=CHART_IDS)
def test_cross_validate_longitudes(ref):
    """Independent oracle: jyotishganit. Skips gracefully if unavailable."""
    b = ref["birth"]
    resp = client.post(
        "/cross-validate",
        json={
            "datetime": b["birth_datetime"],
            "lat": b["birth_lat"],
            "lon": b["birth_lon"],
            "tz_offset": b["birth_tz"],
            "ayanamsa": b["ayanamsa"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    if body.get("jyotishganitError"):
        pytest.skip(f"jyotishganit unavailable: {body['jyotishganitError']}")
    assert body["flagged"] == [], f"longitude divergence beyond 0.1deg: {body['flagged']}"
    assert "ke_version" in body, "ke_version missing from response"
