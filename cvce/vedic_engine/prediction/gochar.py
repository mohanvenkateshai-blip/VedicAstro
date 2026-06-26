"""
Gochar (Transit) Prediction Module — Computes transit predictions using rules from GPD/PD/HS.

Uses transit_rules.py for the rule tables and panchanga.py for planetary positions.
"""

from dataclasses import dataclass, field
from typing import Optional

from ..core.astronomy import julian_day, all_positions, is_retrograde, planet_sidereal_lon
from ..core.panchanga import (
    RASHIS, NAKSHATRAS, NAK_NATURE, NAK_LORD, PLANETS,
    rashi_index, nak_index as _nak_idx, compute_panchanga, PanchangaResult, sun_times
)
from ..rules.transit_rules import (
    TRANSIT_HOUSES, LATTA_RULES, MOORTHI_RESULTS, SADE_SATI_PHASES,
    GOCHARA_VEDHA, VIPAREETHA_VEDHA, TARA_RESULTS, tara_of,
    COMBUST_ORB, SATURN_PARYAYA, JUPITER_PARYAYA, EXALT_SIGN, DEBIL_SIGN, OWN_SIGN,
    reconcile_dasha_transit
)

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


@dataclass
class TransitPrediction:
    """Single planet's transit prediction."""
    planet: str
    house_from_janma: Optional[int]  # None if no natal chart
    rashi: str
    nakshatra: str
    retrograde: bool
    verdict: str  # shubh, ashubh, neutral
    house_quality: str  # good, bad, worst, neutral
    effects: list = field(default_factory=list)  # list of effect strings
    vedha_active: bool = False
    vedha_by: Optional[str] = None
    vipareetha_vedha_active: bool = False
    vipareetha_vedha_by: Optional[str] = None
    combustion: Optional[dict] = None  # {orb, within_orb}
    latta: Optional[dict] = None  # {kicked_nak, hits_janma, effect, mitigated}
    natal_override: Optional[str] = None  # exaltation/debilitation override
    score: int = 0  # -10 to +10


@dataclass
class GocharResult:
    """Complete gochar (transit) prediction for a given date and natal chart."""
    date: str
    janma_rashi: Optional[str]
    janma_nakshatra: Optional[str]
    planet_predictions: list = field(default_factory=list)  # list of TransitPrediction
    moorthy: Optional[dict] = None
    sade_sati: Optional[dict] = None
    ashtama_shani: Optional[dict] = None
    tara_balam: Optional[dict] = None
    overall_verdict: str = "neutral"
    overall_score: int = 0
    synthesis: str = ""


def compute_gochar(date_str: str = None, time_str: str = "12:00",
                    lat: float = 12.30, lon: float = 76.65, tz: float = 5.5,
                    janma_rashi: str = None, janma_nakshatra: str = None,
                    natal_sign: dict = None) -> GocharResult:
    """Compute transit (gochar) predictions for a given date and optional natal chart.

    Args:
        date_str: 'YYYY-MM-DD' (default: today)
        time_str: 'HH:MM' (default: noon)
        lat, lon, tz: location for sunrise/sunset
        janma_rashi: native's Moon sign (e.g., 'Leo')
        janma_nakshatra: native's birth star (e.g., 'Purva Phalguni')
        natal_sign: dict of planet → rashi_idx (0=Aries)
    """
    # Compute panchanga first (for planet positions)
    panch = compute_panchanga(date_str, time_str, lat, lon, tz)

    j_rashi_idx = RASHIS.index(janma_rashi) if janma_rashi and janma_rashi in RASHIS else None
    j_nak_idx = NAKSHATRAS.index(janma_nakshatra) if janma_nakshatra and janma_nakshatra in NAKSHATRAS else None

    results = GocharResult(
        date=panch.date,
        janma_rashi=janma_rashi,
        janma_nakshatra=janma_nakshatra,
    )

    # Compute transit for each planet
    for planet in PLANETS:
        row = next((t for t in panch.transit if t["planet"] == planet), None)
        if not row:
            continue

        pred = TransitPrediction(
            planet=planet,
            rashi=row["rashi"],
            nakshatra=row["nak"],
            retrograde=row["retro"],
            house_from_janma=None,
            verdict="neutral",
            house_quality="neutral",
        )

        if j_rashi_idx is not None:
            planet_rashi_idx = rashi_index(row["lon"])
            house = ((planet_rashi_idx - j_rashi_idx + 12) % 12) + 1  # 1-indexed
            pred.house_from_janma = house

            # Determine house quality from TRANSIT_HOUSES
            rules = TRANSIT_HOUSES.get(planet, {})
            if house in rules.get("worst", []):
                pred.house_quality = "worst"
                pred.verdict = "ashubh"
                pred.score = -10
            elif house in rules.get("bad", []):
                pred.house_quality = "bad"
                pred.verdict = "ashubh"
                pred.score = -5
            elif house in rules.get("good", []):
                pred.house_quality = "good"
                pred.verdict = "shubh"
                pred.score = 7
            else:
                pred.house_quality = "neutral"
                pred.verdict = "neutral"
                pred.score = 0

            # Exaltation/Debilitation override
            if natal_sign and planet in natal_sign:
                natal_rashi = RASHIS[natal_sign[planet]]
                if natal_rashi in OWN_SIGN.get(planet, []) or natal_rashi == EXALT_SIGN.get(planet):
                    if pred.verdict == "ashubh":
                        pred.natal_override = "Exalted/own sign in natal chart mitigates bad transit"
                        pred.verdict = "neutral"
                        pred.score = max(pred.score, -2)
                elif natal_rashi == DEBIL_SIGN.get(planet):
                    pred.natal_override = "Debilitated in natal chart; no good even in favourable transit"
                    if pred.verdict == "shubh":
                        pred.verdict = "neutral"
                        pred.score = min(pred.score, 2)

            # Vedha check
            vedha_rules = GOCHARA_VEDHA.get(planet, {}).get("vedha", {})
            if house in vedha_rules:
                vedha_house = vedha_rules[house]
                for tp in panch.transit:
                    tp_rashi = rashi_index(tp["lon"])
                    tp_house = ((tp_rashi - j_rashi_idx + 12) % 12) + 1
                    if tp_house == vedha_house:
                        pred.vedha_active = True
                        pred.vedha_by = tp["planet"]
                        if pred.verdict == "shubh":
                            pred.verdict = "neutral"
                            pred.score = 0
                        break

            # Combustion check (transiting planet near transiting Sun)
            sun_row = next((t for t in panch.transit if t["planet"] == "Sun"), None)
            if planet != "Sun" and sun_row and row["rashi"] == sun_row["rashi"]:
                diff = abs(row["deg"] - sun_row["deg"])
                orb = COMBUST_ORB.get(planet, 12)
                pred.combustion = {"diff_deg": round(diff, 1), "orb": orb,
                                    "is_combust": diff < orb}

            # Latta check (star affliction)
            if j_nak_idx is not None and planet in LATTA_RULES:
                dist, direction, effect, source = LATTA_RULES[planet]
                planet_nak_idx = _nak_idx(row["lon"])
                kicked = ((planet_nak_idx + direction * (dist - 1)) % 27 + 27) % 27
                kicked_nak = NAKSHATRAS[kicked]
                hits_janma = (kicked_nak == janma_nakshatra)
                mitigated = row["retro"] and planet in ("Mars", "Jupiter", "Saturn", "Venus", "Mercury")
                pred.latta = {
                    "kicked_nak": kicked_nak,
                    "hits_janma": hits_janma,
                    "effect": effect,
                    "mitigated": mitigated,
                }
                if hits_janma and not mitigated:
                    pred.score -= 7
                    if pred.verdict == "shubh":
                        pred.verdict = "neutral"

            # Build effect descriptions
            if pred.house_quality == "good":
                pred.effects.append(f"In {house}th from Janma Rasi — favourable position")
            elif pred.house_quality == "bad":
                pred.effects.append(f"In {house}th from Janma Rasi — unfavourable position")
            elif pred.house_quality == "worst":
                pred.effects.append(f"In {house}th from Janma Rasi — WORST position, caution advised")

            if pred.vedha_active:
                pred.effects.append(f"Gochara Vedha by {pred.vedha_by} — effects cancelled")
            if pred.natal_override:
                pred.effects.append(pred.natal_override)
            if pred.latta and pred.latta["hits_janma"]:
                if pred.latta["mitigated"]:
                    pred.effects.append(f"Latta on Janma star mitigated by retrogression")
                else:
                    pred.effects.append(f"Latta affliction: {pred.latta['effect']}")
            if pred.combustion and pred.combustion["is_combust"]:
                pred.effects.append(f"Combust — within {pred.combustion['diff_deg']}° of Sun")

        results.planet_predictions.append(pred)

    # Moorthy Nirnaya (if Janma Rashi known)
    if j_rashi_idx is not None:
        moon_row = next((t for t in panch.transit if t["planet"] == "Moon"), None)
        if moon_row:
            moon_rashi = rashi_index(moon_row["lon"])
            moorthy_house = ((moon_rashi - j_rashi_idx + 12) % 12) + 1
            if moorthy_house in MOORTHI_RESULTS:
                name, verdict, desc = MOORTHI_RESULTS[moorthy_house]
                results.moorthy = {"house": moorthy_house, "name": name, "verdict": verdict, "description": desc}

    # Sade Sati check (Saturn in 12, 1, or 2 from Janma Rasi)
    if j_rashi_idx is not None:
        saturn_row = next((t for t in panch.transit if t["planet"] == "Saturn"), None)
        if saturn_row:
            sat_rashi = rashi_index(saturn_row["lon"])
            sat_house = ((sat_rashi - j_rashi_idx + 12) % 12) + 1
            if sat_house == 1:
                results.sade_sati = {"phase": "peak", **SADE_SATI_PHASES["peak"]}
            elif sat_house == 12:
                results.sade_sati = {"phase": "rise", **SADE_SATI_PHASES["rise"]}
            elif sat_house == 2:
                results.sade_sati = {"phase": "setting", **SADE_SATI_PHASES["setting"]}
            elif sat_house == 8:
                results.ashtama_shani = {"house": 8,
                                          "effect": "Ashtama Shani — Saturn in 8th from Janma Rasi; obstacles, delays, health issues"}

    # Tara Balam
    if j_nak_idx is not None:
        moon_row = next((t for t in panch.transit if t["planet"] == "Moon"), None)
        if moon_row:
            moon_nak = _nak_idx(moon_row["lon"])
            count = ((moon_nak - j_nak_idx + 27) % 27) + 1
            tara = tara_of(count)
            if tara:
                results.tara_balam = tara

    # Overall scoring
    scores = [p.score for p in results.planet_predictions]
    results.overall_score = sum(scores) if scores else 0

    if results.sade_sati:
        results.overall_score -= 15
    if results.tara_balam and results.tara_balam["verdict"] == "ashubh":
        results.overall_score -= 8

    if results.overall_score >= 15:
        results.overall_verdict = "shubh"
    elif results.overall_score >= 0:
        results.overall_verdict = "neutral"
    else:
        results.overall_verdict = "ashubh"

    # Synthesis
    good = [p for p in results.planet_predictions if p.verdict == "shubh"]
    bad = [p for p in results.planet_predictions if p.verdict == "ashubh"]
    parts = []
    if good:
        parts.append(f"{len(good)} planets in favourable transit ({', '.join(p.planet for p in good)})")
    if bad:
        parts.append(f"{len(bad)} planets in unfavourable transit ({', '.join(p.planet for p in bad)})")
    if results.sade_sati:
        parts.append(f"Sade Sati: {results.sade_sati['phase']} phase — {results.sade_sati['effect']}")
    if results.tara_balam:
        parts.append(
            f"Tara Balam: {results.tara_balam['name']} ({results.tara_balam['verdict']}, Paryaya {results.tara_balam['paryaya']})")
    results.synthesis = " | ".join(parts) if parts else "No natal chart — transit-only analysis"

    return results
