"""Assemble unified report facts for Phase 7 report API."""

from __future__ import annotations

from datetime import datetime

from app.chart import build_chart_geometry
from app.config import get_settings
from app.dasha_vimshottari import (
    antardasha_table,
    birth_balance,
    dasha_deep_payload,
    running_ladder,
)
from app.ephem import jd_place, parse_dt, set_ayanamsa
from graph_rag.enhancer import PredictionEnhancer
from vedic_engine.synthesis.dasha_analyzer import DashaImpactAnalyzer
from vedic_engine.synthesis.engine import VedicPredictor


def build_report_facts(
    birth_datetime: str,
    birth_lat: float,
    birth_lon: float,
    birth_tz: float,
    ayanamsa: str = "LAHIRI",
    name: str | None = None,
    query_date: str | None = None,
    query_time: str = "12:00",
    include_dasha_tree: bool = False,
) -> dict:
    set_ayanamsa(ayanamsa)
    settings = get_settings()
    dt = parse_dt(birth_datetime)
    jd, place = jd_place(dt, birth_lat, birth_lon, birth_tz)

    if not query_date:
        query_date = datetime.now().strftime("%Y-%m-%d")

    geometry = build_chart_geometry(
        jd, place, ayanamsa=ayanamsa, vargas=settings.VARGAS[:2] if settings.VARGAS else [1, 9],
    )

    lagna = geometry.get("lagna") or {}
    planets = geometry.get("planets") or []
    moon = next((p for p in planets if p.get("planet") == "Moon"), None)
    janma_rashi = moon.get("rashi") if moon else None
    janma_nakshatra = moon.get("nakshatra") if moon else None
    natal_sign = geometry.get("natalSign")

    ladder = running_ladder(jd, place, depth=5)
    dasha_block = {
        "balanceAtBirth": birth_balance(jd, place),
        "current": [row["lord"] for row in ladder],
        "currentLadder": ladder,
        "antardashaTable": antardasha_table(jd, place),
        "dashaTree": (
            dasha_deep_payload(jd, place, max_level=5)["dashaTree"]
            if include_dasha_tree
            else []
        ),
    }

    predictor = VedicPredictor()
    pred = predictor.predict(
        date=query_date,
        time=query_time,
        lat=birth_lat,
        lon=birth_lon,
        tz=birth_tz,
        janma_rashi=janma_rashi,
        janma_nakshatra=janma_nakshatra,
        birth_date=birth_datetime[:10],
        birth_time=birth_datetime[11:16] if len(birth_datetime) > 10 else "12:00",
        birth_lat=birth_lat,
        birth_lon=birth_lon,
        birth_tz=birth_tz,
        birth_moon_lon=moon.get("longitude") if moon else None,
        natal_sign=natal_sign,
    )

    enhancer = PredictionEnhancer()
    enhancements = enhancer.enhance(
        pred,
        natal_sign=natal_sign,
        janma_nakshatra=janma_nakshatra,
        janma_rashi=janma_rashi,
    )

    transit_intel = (enhancements or {}).get("transit_intelligence")
    transit_verdict = transit_intel.get("overall_verdict") if transit_intel else None

    dasha_intel = DashaImpactAnalyzer().analyze(
        ladder,
        lagna_rashi=lagna.get("rashi"),
        janma_rashi=janma_rashi,
        natal_sign=natal_sign,
        transit_verdict=transit_verdict,
    )

    panchanga = None
    yogas_raw = None
    try:
        from app.server import _panchanga, _yogas
        panchanga = _panchanga(jd, place)
        yogas_raw = _yogas(jd, place)
    except Exception:
        pass

    planet_table = [
        {
            "planet": p.get("planet"),
            "rashi": p.get("rashi"),
            "degree": p.get("degLabel") or p.get("degree"),
            "nakshatra": p.get("nakshatra"),
            "pada": p.get("pada"),
            "dignity": p.get("dignity"),
            "retrograde": p.get("retrograde", False),
        }
        for p in planets
        if p.get("planet") in {
            "Sun", "Moon", "Mars", "Mercury", "Jupiter",
            "Venus", "Saturn", "Rahu", "Ketu", "Lagna",
        }
    ]

    return {
        "schemaVersion": "1.0",
        "meta": {
            "name": name,
            "birth_datetime": birth_datetime,
            "birth_lat": birth_lat,
            "birth_lon": birth_lon,
            "birth_tz": birth_tz,
            "ayanamsa": ayanamsa,
            "query_date": query_date,
            "query_time": query_time,
            "engine": "PyJHora/SwissEphemeris",
        },
        "natal": {
            "lagna": {
                "rashi": lagna.get("rashi"),
                "degree": lagna.get("degLabel"),
                "nakshatra": lagna.get("nakshatra"),
                "pada": lagna.get("pada"),
            },
            "moon": {
                "rashi": janma_rashi,
                "nakshatra": janma_nakshatra,
                "pada": moon.get("pada") if moon else None,
            },
            "planets": planet_table,
        },
        "panchanga": panchanga,
        "dashas": {
            "balanceAtBirth": birth_balance(jd, place),
            "current": dasha_block.get("current"),
            "currentLadder": ladder,
            "antardashaTable": antardasha_table(jd, place),
            "dashaTree": dasha_block.get("dashaTree"),
        },
        "dasha_intelligence": dasha_intel,
        "transit_intelligence": transit_intel,
        "yogas": {
            "activeCount": yogas_raw.get("activeCount") if yogas_raw else 0,
            "yogas": yogas_raw.get("yogas") if yogas_raw else {},
        },
        "prediction_summary": pred.summary if hasattr(pred, "summary") else None,
    }
