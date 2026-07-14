from __future__ import annotations

from vedic_engine.prediction.ashtakavarga import AshtakavargaResult
from vedic_engine.prediction.gochar import GocharResult, TransitPrediction
from vedic_engine.synthesis.transit_analyzer import TransitImpactAnalyzer


def _prediction(rashi: str = "Aries") -> TransitPrediction:
    return TransitPrediction(
        planet="Jupiter",
        house_from_janma=1,
        rashi=rashi,
        nakshatra="Ashwini",
        retrograde=False,
        verdict="neutral",
        house_quality="neutral",
    )


def _gochar(prediction: TransitPrediction) -> GocharResult:
    return GocharResult(
        date="2026-07-14",
        janma_rashi="Aries",
        janma_nakshatra="Ashwini",
        planet_predictions=[prediction],
    )


def _ashtakavarga(bindus: int, *, sign: str = "Aries") -> AshtakavargaResult:
    sav = [25] * 12
    sav[0] = bindus
    return AshtakavargaResult(
        bav={},
        sav=sav,
        planet_totals={},
        total_sav=sum(sav),
        transit_sav={"Jupiter": {"bindus": bindus, "sign": sign}},
    )


def test_transit_sav_low_and_high_bands_adjust_score_and_preserve_factor():
    analyzer = TransitImpactAnalyzer()
    baseline = analyzer.analyze(_gochar(_prediction()))
    low = analyzer.analyze(_gochar(_prediction()), ashtakavarga=_ashtakavarga(24))
    high = analyzer.analyze(_gochar(_prediction()), ashtakavarga=_ashtakavarga(30))

    assert baseline is not None and low is not None and high is not None
    baseline_planet = baseline.planets[0]
    low_planet = low.planets[0]
    high_planet = high.planets[0]

    assert low_planet["score"] == baseline_planet["score"] - 3
    assert high_planet["score"] == baseline_planet["score"] + 2
    assert any("only 24 SAV bindus" in factor["summary"] for factor in low_planet["factors"])
    assert any("30 bindus" in factor["summary"] for factor in high_planet["factors"])


def test_unexpected_transit_rashi_uses_supplied_bindus_without_crashing():
    result = TransitImpactAnalyzer().analyze(
        _gochar(_prediction("Unknown")),
        ashtakavarga=_ashtakavarga(24, sign="Unknown"),
    )

    assert result is not None
    assert any(
        "only 24 SAV bindus" in factor["summary"]
        for factor in result.planets[0]["factors"]
    )
