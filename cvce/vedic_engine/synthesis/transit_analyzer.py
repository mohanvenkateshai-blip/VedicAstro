"""
Transit Impact Analyzer — per-planet combinatorial judgment for gochar.

Evaluates house table, special transits, vedha, natal dignity, AKV bindus,
dasha context, latta, combustion. Returns structured impact assessment
(not raw corpus text).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ..core.panchanga import RASHIS
from ..prediction.gochar import GocharResult, TransitPrediction
from ..rules.transit_rules import (
    DEBIL_SIGN,
    EXALT_SIGN,
    OWN_SIGN,
    TRANSIT_HOUSES,
    reconcile_dasha_transit,
)

# Life-area themes by house from Janma Rasi (classical gochar framing)
HOUSE_THEMES: dict[int, list[str]] = {
    1: ["self-image", "health", "vitality", "new personal initiatives"],
    2: ["finances", "family", "speech", "savings and resources"],
    3: ["courage", "siblings", "short travel", "communication"],
    4: ["home", "mother", "property", "inner peace"],
    5: ["children", "creativity", "education", "speculation"],
    6: ["health routines", "debts", "competition", "service"],
    7: ["marriage", "partnerships", "contracts", "public dealings"],
    8: ["longevity stress", "hidden matters", "obstacles", "inheritance"],
    9: ["fortune", "father", "dharma", "long journeys"],
    10: ["career", "status", "authority", "public recognition"],
    11: ["gains", "networks", "fulfilment of hopes", "income"],
    12: ["expenses", "retreat", "foreign lands", "sleep and recovery"],
}

SPECIAL_TRANSIT_LABELS = {
    "sade_sati": "Sade Sati",
    "ashtama_shani": "Ashtama Shani (Kalyani)",
    "kantaka_shani": "Kantaka / Ardhashtama Shani",
    "chandrashtama": "Chandrashtama",
}


@dataclass
class Factor:
    role: str  # aggravating | mitigating | contextual
    weight: int
    summary: str
    source: str = "GPD"


@dataclass
class PlanetTransitAnalysis:
    planet: str
    rashi: str
    nakshatra: str
    house_from_janma: int | None
    retrograde: bool
    final_verdict: str  # shubh | mixed | ashubh
    score: int
    primary_driver: str
    root_cause: str
    aggravating: list[str] = field(default_factory=list)
    mitigating: list[str] = field(default_factory=list)
    positive_impact: list[str] = field(default_factory=list)
    negative_impact: list[str] = field(default_factory=list)
    factors: list[dict] = field(default_factory=list)
    summary: str = ""
    classical_basis: list[str] = field(default_factory=list)


@dataclass
class TransitIntelligence:
    date: str
    janma_rashi: str | None
    overall_verdict: str
    overall_score: int
    day_summary: str
    dasha_context: str | None
    moorthy_note: str | None
    tara_note: str | None
    planets: list[dict] = field(default_factory=list)
    top_drivers: list[str] = field(default_factory=list)


def _ordinal(house: int) -> str:
    if house == 1:
        return "1st"
    if house == 2:
        return "2nd"
    if house == 3:
        return "3rd"
    if 11 <= house <= 13:
        return f"{house}th"
    v = house % 10
    if v == 1:
        return f"{house}st"
    if v == 2:
        return f"{house}nd"
    if v == 3:
        return f"{house}rd"
    return f"{house}th"


def _house_quality_hardcoded(planet: str, house: int) -> tuple[str, str, int]:
    rules = TRANSIT_HOUSES.get(planet, {})
    if house in rules.get("worst", []):
        return "worst", "ashubh", -10
    if house in rules.get("bad", []):
        return "bad", "ashubh", -5
    if house in rules.get("good", []):
        return "good", "shubh", 7
    return "neutral", "neutral", 0


def _natal_dignity(planet: str, natal_sign: dict | None) -> str | None:
    if not natal_sign or planet not in natal_sign:
        return None
    rashi = RASHIS[natal_sign[planet]]
    if rashi == EXALT_SIGN.get(planet):
        return "exalted"
    if rashi in OWN_SIGN.get(planet, []):
        return "own_sign"
    if rashi == DEBIL_SIGN.get(planet):
        return "debilitated"
    return "neutral"


def _special_for_planet(
    planet: str,
    house: int | None,
    gochar: GocharResult,
) -> tuple[str, str, int] | None:
    """Return (label, effect_text, score_delta) for named special transits."""
    if planet == "Saturn" and house is not None:
        if gochar.sade_sati and house in (12, 1, 2):
            phase = gochar.sade_sati.get("phase", "")
            effect = gochar.sade_sati.get("effect", "Sade Sati period")
            return (
                f"Sade Sati ({phase} phase)",
                effect,
                -15 if house == 1 else -12,
            )
        if gochar.ashtama_shani and house == 8:
            return (
                SPECIAL_TRANSIT_LABELS["ashtama_shani"],
                gochar.ashtama_shani.get(
                    "effect",
                    "Ashtama Shani — severe obstacles, delays, health strain",
                ),
                -12,
            )
        if gochar.kantaka_shani and house == gochar.kantaka_shani.get("house"):
            return (
                SPECIAL_TRANSIT_LABELS["kantaka_shani"],
                gochar.kantaka_shani.get("effect", "Kantaka Shani"),
                -10,
            )
    if planet == "Moon" and house == 8:
        return (
            SPECIAL_TRANSIT_LABELS["chandrashtama"],
            "Chandrashtama — Moon in 8th from natal Moon; among the most difficult Moon transits",
            -10,
        )
    return None


def _verdict_from_score(score: int) -> str:
    if score >= 4:
        return "shubh"
    if score <= -4:
        return "ashubh"
    return "mixed"


def _impact_bullets(
    planet: str,
    house: int | None,
    verdict: str,
    themes: list[str],
) -> tuple[list[str], list[str]]:
    pos: list[str] = []
    neg: list[str] = []
    theme = ", ".join(themes[:3]) if themes else "general life areas"
    if house is None:
        return pos, neg
    if verdict == "shubh":
        pos.append(f"Support for {theme} through {_ordinal(house)}-house transit themes")
        pos.append(f"{planet} transit tends to ease matters ruled by the {_ordinal(house)} house")
    elif verdict == "ashubh":
        neg.append(f"Pressure on {theme}")
        neg.append(f"Delays, friction, or caution in {_ordinal(house)}-house matters")
    else:
        pos.append(f"Mixed signals — some support for {theme}, but not a clear green light")
        neg.append("Avoid major commitments unless other factors strongly support")
    return pos, neg


class TransitImpactAnalyzer:
    """Combinatorial per-planet transit judgment."""

    def analyze(
        self,
        gochar: GocharResult | None,
        natal_sign: dict | None = None,
        dasha_maha: str | None = None,
        dasha_antar: str | None = None,
        dasha_score: int = 0,
        ashtakavarga: Any = None,
    ) -> TransitIntelligence | None:
        if not gochar or not gochar.planet_predictions:
            return None

        dasha_good = dasha_score > 0
        dasha_context = None
        if dasha_maha:
            dasha_context = f"Mahadasha: {dasha_maha}"
            if dasha_antar:
                dasha_context += f" · Antardasha: {dasha_antar}"

        planet_analyses: list[PlanetTransitAnalysis] = []

        for pred in gochar.planet_predictions:
            planet_analyses.append(
                self._analyze_planet(
                    pred,
                    gochar,
                    natal_sign,
                    dasha_maha,
                    dasha_antar,
                    dasha_good,
                    ashtakavarga,
                )
            )

        scores = [p.score for p in planet_analyses]
        overall = sum(scores) if scores else 0
        if gochar.moorthy:
            if gochar.moorthy.get("verdict") == "shubh":
                overall += 5
            elif gochar.moorthy.get("verdict") == "ashubh":
                overall -= 5
        if gochar.tara_balam and gochar.tara_balam.get("verdict") == "ashubh":
            overall -= 6

        if overall >= 12:
            overall_verdict = "shubh"
        elif overall <= -12:
            overall_verdict = "ashubh"
        else:
            overall_verdict = "mixed"

        ranked = sorted(planet_analyses, key=lambda p: p.score)
        top_neg = [p for p in ranked if p.score <= -6][:3]
        top_pos = [p for p in reversed(ranked) if p.score >= 6][:3]
        drivers: list[str] = []
        for p in top_neg:
            drivers.append(f"{p.planet}: {p.primary_driver}")
        for p in top_pos:
            drivers.append(f"{p.planet}: {p.primary_driver}")

        shubh_n = sum(1 for p in planet_analyses if p.final_verdict == "shubh")
        ashubh_n = sum(1 for p in planet_analyses if p.final_verdict == "ashubh")
        day_parts = [
            f"{shubh_n} favourable, {ashubh_n} unfavourable planetary transits today",
        ]
        if top_neg:
            day_parts.append(f"Primary caution: {top_neg[0].planet} — {top_neg[0].primary_driver}")
        if dasha_maha and top_neg:
            transit_good = top_neg[0].final_verdict == "shubh"
            day_parts.append(reconcile_dasha_transit(dasha_good, transit_good))

        moorthy_note = None
        if gochar.moorthy:
            m = gochar.moorthy
            moorthy_note = (
                f"Moorthi: Moon in {_ordinal(m['house'])} from Janma — "
                f"{m['name']}: {m['description']}"
            )
            day_parts.append(moorthy_note)

        tara_note = None
        if gochar.tara_balam:
            t = gochar.tara_balam
            tara_note = f"Tara Balam: {t.get('name', '?')} ({t.get('verdict', '?')})"
            day_parts.append(tara_note)

        return TransitIntelligence(
            date=gochar.date,
            janma_rashi=gochar.janma_rashi,
            overall_verdict=overall_verdict,
            overall_score=overall,
            day_summary=" ".join(day_parts),
            dasha_context=dasha_context,
            moorthy_note=moorthy_note,
            tara_note=tara_note,
            planets=[asdict(p) for p in planet_analyses],
            top_drivers=drivers[:5],
        )

    def _analyze_planet(
        self,
        pred: TransitPrediction,
        gochar: GocharResult,
        natal_sign: dict | None,
        dasha_maha: str | None,
        dasha_antar: str | None,
        dasha_good: bool,
        ashtakavarga: Any,
    ) -> PlanetTransitAnalysis:
        factors: list[Factor] = []
        house = pred.house_from_janma
        score = 0

        if house is not None:
            quality, base_verdict, base_score = _house_quality_hardcoded(pred.planet, house)
            factors.append(
                Factor(
                    role="contextual"
                    if base_verdict == "neutral"
                    else ("aggravating" if base_verdict == "ashubh" else "mitigating"),
                    weight=base_score,
                    summary=(
                        f"{pred.planet} in {_ordinal(house)} from natal Moon — "
                        f"{quality} house (Table 12)"
                    ),
                    source="GPD-Ch10-Table12",
                )
            )
            score += base_score
            primary_driver = factors[-1].summary
            root = f"Base gochar: {quality} transit house for {pred.planet}"
        else:
            primary_driver = "No natal Moon sign — house position unknown"
            root = primary_driver
            quality = "neutral"

        special = _special_for_planet(pred.planet, house, gochar)
        if special:
            label, effect, delta = special
            factors.append(
                Factor(
                    role="aggravating",
                    weight=delta,
                    summary=f"{label}: {effect}",
                    source="GPD special transit",
                )
            )
            score += delta
            primary_driver = label
            root = effect

        dignity = _natal_dignity(pred.planet, natal_sign)
        if dignity == "exalted" or dignity == "own_sign":
            if score < 0:
                w = 3
                factors.append(
                    Factor(
                        role="mitigating",
                        weight=w,
                        summary=(
                            f"Natal {pred.planet} is {dignity.replace('_', ' ')} — "
                            "reduces severity of difficult transit"
                        ),
                        source="GPD natal dignity",
                    )
                )
                score += w
        elif dignity == "debilitated":
            if score > 0:
                w = -3
                factors.append(
                    Factor(
                        role="aggravating",
                        weight=w,
                        summary=(
                            f"Natal {pred.planet} is debilitated — "
                            "limits benefit even in a good transit house"
                        ),
                        source="GPD natal dignity",
                    )
                )
                score += w
            else:
                w = -2
                factors.append(
                    Factor(
                        role="aggravating",
                        weight=w,
                        summary="Natal debilitation adds strain to an already difficult transit",
                        source="GPD natal dignity",
                    )
                )
                score += w

        if pred.vedha_active and pred.vedha_by:
            from vedic_engine.rules.transit_rules import VEDHA_EXEMPT_PAIRS

            pair = frozenset({pred.planet, pred.vedha_by})
            if pair in VEDHA_EXEMPT_PAIRS:
                factors.append(
                    Factor(
                        role="contextual",
                        weight=0,
                        summary=(
                            f"Vedha by {pred.vedha_by} does not apply — "
                            f"{pred.planet}/{pred.vedha_by} are classically exempt from "
                            "mutual Vedha (PD Ch.26)"
                        ),
                        source="PD-Ch26",
                    )
                )
            else:
                w = -4 if pred.verdict == "shubh" or score > 0 else 0
                if w:
                    factors.append(
                        Factor(
                            role="aggravating",
                            weight=w,
                            summary=f"Gochara Vedha by {pred.vedha_by} — favourable results blocked",
                            source="GPD Vedha",
                        )
                    )
                    score += w

        if pred.vipareetha_vedha_active and pred.vipareetha_vedha_by:
            w = 4
            factors.append(
                Factor(
                    role="mitigating",
                    weight=w,
                    summary=(
                        f"Vipareetha Vedha by {pred.vipareetha_vedha_by} — "
                        "malefic transit severity reduced"
                    ),
                    source="GPD Vipareetha Vedha",
                )
            )
            score += w

        if pred.latta and pred.latta.get("hits_janma"):
            if pred.latta.get("mitigated"):
                factors.append(
                    Factor(
                        role="mitigating",
                        weight=2,
                        summary="Latta on birth star — mitigated by retrograde motion",
                        source="GPD Latta",
                    )
                )
                score += 2
            else:
                factors.append(
                    Factor(
                        role="aggravating",
                        weight=-6,
                        summary=f"Latta affliction on birth nakshatra: {pred.latta.get('effect', '')}",
                        source="GPD Latta",
                    )
                )
                score -= 6

        if pred.combustion and pred.combustion.get("is_combust"):
            factors.append(
                Factor(
                    role="aggravating",
                    weight=-3,
                    summary=(
                        f"Combust within {pred.combustion.get('diff_deg')}° of Sun — "
                        "planet weakened"
                    ),
                    source="GPD combustion",
                )
            )
            score -= 3

        if pred.retrograde and pred.planet in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
            if score < 0:
                # Retrograde in a bad transit house ameliorates the negative.
                # GPD Ch.10, PD Ch.26: "A retrograde planet in its bad transit house
                # gives less evil than usual — the backward motion weakens the malefic
                # tendency of the unfavourable house."
                w = 3
                factors.append(
                    Factor(
                        role="mitigating",
                        weight=w,
                        summary=(
                            f"{pred.planet} retrograde in bad transit house — "
                            "classical amelioration: severity reduced (GPD Ch.10, PD Ch.26)"
                        ),
                        source="GPD-Ch10",
                    )
                )
                score += w
            else:
                # Retrograde in a good house: results come with delay or through
                # revisitation of circumstances, but the benefit stands.
                # The planet "insists" on the house themes; mild amplification.
                w = 1
                factors.append(
                    Factor(
                        role="mitigating",
                        weight=w,
                        summary=(
                            f"{pred.planet} retrograde in good transit house — "
                            "benefit persists with slight delay; retrograde deepens house themes (GPD Ch.10)"
                        ),
                        source="GPD-Ch10",
                    )
                )
                score += w

        if ashtakavarga and getattr(ashtakavarga, "transit_sav", None):
            sav = ashtakavarga.transit_sav.get(pred.planet)
            if sav:
                bindus = sav.get("bindus", 0)
                verdict = sav.get("verdict", "neutral")
                if bindus < 25:
                    factors.append(
                        Factor(
                            role="aggravating",
                            weight=-3,
                            summary=(
                                f"Ashtakavarga: only {bindus} SAV bindus in transit sign "
                                f"({sav.get('sign')}) — depleted support"
                            ),
                            source="Ashtakavarga",
                        )
                    )
                    score -= 3
                elif bindus >= 30:
                    factors.append(
                        Factor(
                            role="mitigating",
                            weight=2,
                            summary=(
                                f"Ashtakavarga: {bindus} bindus in {sav.get('sign')} — "
                                "strong sign support"
                            ),
                            source="Ashtakavarga",
                        )
                    )
                    score += 2

        active_lord = dasha_antar or dasha_maha
        if active_lord and active_lord == pred.planet:
            w = 2 if dasha_good else -2
            factors.append(
                Factor(
                    role="mitigating" if w > 0 else "aggravating",
                    weight=w,
                    summary=(
                        f"Transiting planet is current dasha lord ({active_lord}) — "
                        "period themes are activated"
                    ),
                    source="Dasha",
                )
            )
            score += w
            reconcile = reconcile_dasha_transit(
                dasha_good,
                _verdict_from_score(score) == "shubh",
            )
            factors.append(
                Factor(
                    role="contextual",
                    weight=0,
                    summary=reconcile,
                    source="GPD Ch.8",
                )
            )

        final_verdict = _verdict_from_score(score)
        themes = HOUSE_THEMES.get(house or 0, [])
        pos, neg = _impact_bullets(pred.planet, house, final_verdict, themes)

        aggravating = [f.summary for f in factors if f.role == "aggravating"]
        mitigating = [f.summary for f in factors if f.role == "mitigating"]
        basis = list({f.source for f in factors if f.source})

        summary = (
            f"{pred.planet} in {pred.rashi}"
            + (f", {_ordinal(house)} from natal Moon" if house else "")
            + f" — {final_verdict.upper()}. "
            + f"Main factor: {primary_driver}."
        )
        if mitigating:
            summary += f" Mitigation: {mitigating[0]}."
        if aggravating and final_verdict != "shubh":
            summary += f" Risk: {aggravating[0]}."

        return PlanetTransitAnalysis(
            planet=pred.planet,
            rashi=pred.rashi,
            nakshatra=pred.nakshatra,
            house_from_janma=house,
            retrograde=pred.retrograde,
            final_verdict=final_verdict,
            score=score,
            primary_driver=primary_driver,
            root_cause=root,
            aggravating=aggravating,
            mitigating=mitigating,
            positive_impact=pos,
            negative_impact=neg,
            factors=[asdict(f) for f in factors],
            summary=summary,
            classical_basis=basis,
        )
