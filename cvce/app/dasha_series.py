"""
Dasha Series — monthly transit score scan for a Maha-Antar time window.

For each sample date we compute planetary positions and score them against the
native's natal chart. The Dasha score is constant for the window (determined by
Maha/Antar lord quality); the transit score varies month-by-month as planets move.

The output is a time series suitable for a front-end line chart plus a list of
key planetary sign-change events that explain the peaks and dips.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional


def _next_month_first(d: date) -> date:
    """First day of the month following d."""
    return (d.replace(day=1) + timedelta(days=32)).replace(day=1)


def _sample_dates(start: date, end: date, interval_days: int = 30) -> list[date]:
    """Generate sample dates at interval_days spacing from start to end."""
    dates: list[date] = []
    cur = start
    while cur <= end:
        dates.append(cur)
        cur += timedelta(days=interval_days)
    if dates and dates[-1] < end:
        dates.append(end)
    return dates


def _planet_rashi(gochar, planet_name: str) -> Optional[str]:
    """Extract transit rashi for a planet from the GocharResult."""
    for pred in (gochar.planet_predictions or []):
        if pred.planet == planet_name:
            return pred.rashi
    return None


def build_dasha_series(
    maha_lord: str,
    antar_lord: str,
    start_date: str,
    end_date: str,
    dasha_score: int,
    lat: float,
    lon: float,
    tz: float,
    janma_rashi: Optional[str],
    janma_nakshatra: Optional[str],
    natal_sign: Optional[dict],
    lagna_rashi: Optional[str] = None,
    interval_days: int = 30,
) -> dict:
    """
    Build a time-series of combined Dasha+Transit scores for a period window.

    Returns:
        series   — list of monthly data points
        events   — list of planetary sign-change events (the inflection points)
        stats    — aggregate statistics (peak, trough, shubh/ashubh month counts)
    """
    from vedic_engine.prediction.gochar import compute_gochar
    from vedic_engine.synthesis.transit_analyzer import TransitImpactAnalyzer

    start = date.fromisoformat(start_date[:10])
    end   = date.fromisoformat(end_date[:10])
    samples = _sample_dates(start, end, interval_days)

    analyzer = TransitImpactAnalyzer()

    # Track sign changes for all planets except Moon — Moon changes sign every
    # 2-3 days, so monthly sampling produces noisy and misleading Moon entries
    ALL_PLANETS = ("Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")

    series: list[dict] = []
    events: list[dict] = []
    prev_rashis: dict[str, str] = {}

    for d in samples:
        try:
            g = compute_gochar(
                date_str=d.isoformat(),
                lat=lat, lon=lon, tz=tz,
                janma_rashi=janma_rashi,
                janma_nakshatra=janma_nakshatra,
                natal_sign=natal_sign,
                lagna_rashi=lagna_rashi,
            )
            ti = analyzer.analyze(
                g,
                natal_sign=natal_sign,
                dasha_maha=maha_lord,
                dasha_antar=antar_lord,
                dasha_score=dasha_score,
            )
            transit_score        = ti.overall_score if ti else 0
            lagna_transit_score  = g.lagna_overall_score if g else 0
            combined_score       = dasha_score + transit_score
            lagna_combined_score = dasha_score + lagna_transit_score
            verdict = "shubh" if combined_score > 0 else "ashubh"

            # Key driver for this date (most impactful planet)
            key_planet = key_note = None
            if ti and ti.planets:
                worst = min(ti.planets, key=lambda p: p.get("score", 0))
                best  = max(ti.planets, key=lambda p: p.get("score", 0))
                dominant = worst if combined_score <= 0 else best
                key_planet = dominant.get("planet")
                key_note   = dominant.get("primary_driver", "")[:80]

            planet_scores = {
                pred.planet: pred.score
                for pred in (g.planet_predictions if g else [])
            }

            series.append({
                "date":                d.isoformat(),
                "transit_score":       transit_score,
                "combined_score":      combined_score,
                "lagna_transit_score": lagna_transit_score,
                "lagna_combined_score": lagna_combined_score,
                "planet_scores":       planet_scores,
                "verdict":             verdict,
                "key_planet":          key_planet,
                "key_note":            key_note,
            })

            # Detect sign changes across all planets → visible events
            if g and g.planet_predictions:
                for pred in g.planet_predictions:
                    if pred.planet not in ALL_PLANETS:
                        continue
                    rashi_now = pred.rashi
                    rashi_prev = prev_rashis.get(pred.planet)
                    if rashi_prev and rashi_now != rashi_prev:
                        house = pred.house_from_janma
                        events.append({
                            "date":       d.isoformat(),
                            "planet":     pred.planet,
                            "from_rashi": rashi_prev,
                            "to_rashi":   rashi_now,
                            "house_from_moon": house,
                            "transit_score_at_event": transit_score,
                            "note": (
                                f"{pred.planet} moves from {rashi_prev} to {rashi_now}"
                                + (f" (house {house} from natal Moon)" if house else "")
                            ),
                        })
                    prev_rashis[pred.planet] = rashi_now

        except Exception:
            continue

    if not series:
        return {
            "maha_lord": maha_lord, "antar_lord": antar_lord,
            "dasha_score": dasha_score, "series": [], "events": [], "stats": {},
        }

    peak   = max(series, key=lambda s: s["combined_score"])
    trough = min(series, key=lambda s: s["combined_score"])
    shubh_count  = sum(1 for s in series if s["combined_score"] > 0)
    ashubh_count = len(series) - shubh_count

    lagna_peak   = max(series, key=lambda s: s["lagna_combined_score"])
    lagna_trough = min(series, key=lambda s: s["lagna_combined_score"])

    return {
        "maha_lord":    maha_lord,
        "antar_lord":   antar_lord,
        "dasha_score":  dasha_score,
        "series":       series,
        "events":       events,
        "stats": {
            "shubh_months":  shubh_count,
            "ashubh_months": ashubh_count,
            "total_months":  len(series),
            "peak":          {"date": peak["date"],         "score": peak["combined_score"]},
            "trough":        {"date": trough["date"],       "score": trough["combined_score"]},
            "lagna_peak":    {"date": lagna_peak["date"],   "score": lagna_peak["lagna_combined_score"]},
            "lagna_trough":  {"date": lagna_trough["date"], "score": lagna_trough["lagna_combined_score"]},
        },
    }
