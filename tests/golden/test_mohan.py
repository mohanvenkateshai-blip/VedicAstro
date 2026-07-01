import pytest
from app.report_facts import build_report_facts

# Mohan's birth details
BIRTH_DATETIME = "1975-04-22T19:15:00"
BIRTH_LAT = 12.2958
BIRTH_LON = 76.6394
BIRTH_TZ = 5.5

# Expected results for Mohan's chart
EXPECTED_LAGNA_RASHI = "Libra"
EXPECTED_LAGNA_NAKSHATRA = "Swati"
EXPECTED_LAGNA_PADA = 4

# Test case for Mohan's chart
def test_mohan_chart():
    facts = build_report_facts(
        birth_datetime=BIRTH_DATETIME,
        birth_lat=BIRTH_LAT,
        birth_lon=BIRTH_LON,
        birth_tz=BIRTH_TZ,
        include_yogas=True,
        include_ashtakavarga=True,
        include_shadbala=True,
        include_timing=True,
        include_dasha_forecast=True,
    )

    # Verify lagna details
    assert facts["natal"]["lagna"]["rashi"] == EXPECTED_LAGNA_RASHI
    assert facts["natal"]["lagna"]["nakshatra"] == EXPECTED_LAGNA_NAKSHATRA
    assert facts["natal"]["lagna"]["pada"] == EXPECTED_LAGNA_PADA

    # Verify yogas
    assert "yogas" in facts
    assert facts["yogas"]["activeCount"] > 0

    # Verify ashtakavarga
    assert "ashtakavarga" in facts
    assert facts["ashtakavarga"]["sav_annotated"] is not None

    # Verify shadbala
    assert "shadbala" in facts
    assert facts["shadbala"]["total"] is not None

    # Verify timing merge
    assert "timing_merge" in facts
    assert facts["timing_merge"]["verdict"] is not None

    # Verify dasha forecast
    assert "forecast" in facts
    assert len(facts["forecast"]) > 0