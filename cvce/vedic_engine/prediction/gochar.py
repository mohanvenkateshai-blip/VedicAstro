"""
Gochar (Transit) Prediction Module — Computes transit predictions using rules from GPD/PD/HS.

Uses transit_rules.py for the rule tables and panchanga.py for planetary positions.
"""

from dataclasses import dataclass, field

from ..core.panchanga import (
    NAKSHATRAS,
    PLANETS,
    RASHIS,
    compute_panchanga,
    rashi_index,
)
from ..core.panchanga import nak_index as _nak_idx
try:
    from vedic_knowledge import get_safe_transit_rules as _vk_transit  # noqa: F401
    from knowledge_engine.integration import get_structured_book
except ImportError:
    from knowledge_engine.integration import get_structured_book
from ..rules.transit_rules import (
    COMBUST_ORB,
    DEBIL_SIGN,
    EXALT_SIGN,
    GOCHARA_VEDHA,
    KANTAKA_ASHTAMA_PHASES,
    LATTA_RULES,
    MOORTHI_RESULTS,
    OWN_SIGN,
    SADE_SATI_PHASES,
    TRANSIT_HOUSES,
    VIPAREETHA_VEDHA,
    tara_of,
)
from .ashtakavarga import kaksha_bav_grade, kaksha_gives_bindu, saturn_bav_in_sign

try:
    from vedic_knowledge import get_safe_transit_rules as active_transit_rules
except ImportError:
    try:
        from knowledge_engine.integration import get_safe_transit_rules as active_transit_rules
    except ImportError:

        def active_transit_rules():
            return None

try:
    from vedic_knowledge.graph.rules_provider import rebuild_transit_rules as _rebuild_transit_rules
except ImportError:
    try:
        from graph_rag.rules_provider import rebuild_transit_rules as _rebuild_transit_rules
    except ImportError:

        def _rebuild_transit_rules():
            return None


PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

_rules_version: str | None = None
_gochar_registered = False


def _clear_transit_rules_cache() -> None:
    """Drop cached graph transit rules so the next gochar run reloads from graph.
    Uses provider rebuild + KE cache clear (no direct GraphRAG bypass).
    """
    try:
        try:
            from vedic_knowledge import clear_knowledge_engine_cache
        except ImportError:
            from knowledge_engine.integration import clear_knowledge_engine_cache

        clear_knowledge_engine_cache()
    except Exception:
        pass
    try:
        _rebuild_transit_rules()
    except Exception:
        # Last resort: reset provider singleton
        try:
            try:
                from vedic_knowledge import GraphTransitRules
            except ImportError:
                from graph_rag.rules_provider import GraphTransitRules

            GraphTransitRules._instance = None
        except Exception:
            pass


def _on_gochar_refresh(new_version: str) -> None:
    global _rules_version
    _rules_version = new_version
    _clear_transit_rules_cache()
    # Force active rules object to be rebuilt from current graph
    try:
        _rebuild_transit_rules()
    except Exception:
        pass
    # Propagate structured signals
    try:
        get_structured_book("Gochar_Phaladeepika")
    except Exception:
        pass


def _register_gochar_engine() -> None:
    global _gochar_registered
    if _gochar_registered:
        return
    try:
        try:
            from vedic_knowledge import get_knowledge_engine
        except ImportError:
            from knowledge_engine.integration import get_knowledge_engine

        ke = get_knowledge_engine()
        if ke is not None:
            ke.register_engine("gochar", on_refresh=_on_gochar_refresh)
        _gochar_registered = True
    except Exception:
        pass


_register_gochar_engine()


def _ensure_gochar_registered() -> None:
    if not _gochar_registered:
        _register_gochar_engine()


@dataclass
class TransitPrediction:
    """Single planet's transit prediction."""

    planet: str
    house_from_janma: int | None  # None if no natal chart
    rashi: str
    nakshatra: str
    retrograde: bool
    verdict: str  # shubh, ashubh, neutral
    house_quality: str  # good, bad, worst, neutral
    longitude: float | None = None
    effects: list = field(default_factory=list)  # list of effect strings
    vedha_active: bool = False
    vedha_by: str | None = None
    vipareetha_vedha_active: bool = False
    vipareetha_vedha_by: str | None = None
    combustion: dict | None = None  # {orb, within_orb}
    latta: dict | None = None  # {kicked_nak, hits_janma, effect, mitigated}
    natal_override: str | None = None  # exaltation/debilitation override
    score: int = 0  # -10 to +10
    # Lagna-based parallel scoring (same house-quality tables, different reference)
    house_from_lagna: int | None = None
    lagna_score: int = 0
    citations: list = field(default_factory=list)  # graph node citations from GraphTransitRules


@dataclass
class GocharResult:
    """Complete gochar (transit) prediction for a given date and natal chart."""

    date: str
    janma_rashi: str | None
    janma_nakshatra: str | None
    planet_predictions: list = field(default_factory=list)  # list of TransitPrediction
    moorthy: dict | None = None
    sade_sati: dict | None = None
    ashtama_shani: dict | None = None
    kantaka_shani: dict | None = None
    tara_balam: dict | None = None
    # B-16.7 personal factors (ported from MuhurtaCosmos.jsx)
    chandrabala: dict | None = None  # Moon house from Janma Rashi; 6/8/12 weak
    ghaat: dict | None = None  # Ghaat Chakra hits keyed to Janma Rashi
    pancha_pakshi_bird: str | None = None  # natal ruling bird (display only)
    choghadiya: dict | None = None  # 8-part day/night segment at query time
    eclipse: dict | None = None  # Grahan — universal, non-personal
    overall_verdict: str = "neutral"
    overall_score: int = 0
    lagna_overall_score: int = 0  # parallel score computed from Lagna reference
    synthesis: str = ""


def compute_gochar(
    date_str: str = None,
    time_str: str = "12:00",
    lat: float = 12.30,
    lon: float = 76.65,
    tz: float = 5.5,
    janma_rashi: str = None,
    janma_nakshatra: str = None,
    natal_sign: dict = None,
    lagna_rashi: str = None,
    transit_rows: list[dict] | None = None,
) -> GocharResult:
    """Compute transit (gochar) predictions for a given date and optional natal chart.

    Args:
        date_str: 'YYYY-MM-DD' (default: today)
        time_str: 'HH:MM' (default: noon)
        lat, lon, tz: location for sunrise/sunset
        janma_rashi: native's Moon sign (e.g., 'Leo')
        janma_nakshatra: native's birth star (e.g., 'Purva Phalguni')
        natal_sign: dict of planet → rashi_idx (0=Aries)
        transit_rows: optional canonical ephemeris rows. When supplied, these
            replace the legacy Panchanga astronomy while retaining the Gochar
            interpretation rules.
    """
    _ensure_gochar_registered()
    panch = None
    if transit_rows is None:
        # Compatibility path for existing research callers. Product endpoints
        # must inject canonical PyJHora/Swiss rows explicitly.
        panch = compute_panchanga(date_str, time_str, lat, lon, tz)
        transit_rows = panch.transit
        result_date = panch.date
    else:
        result_date = date_str
        # Grahan is universal/non-personal — still need it when ephemeris rows
        # are injected from outside (product path). Lightweight: reuse
        # compute_panchanga which already scans the civil day's tithi segs.
        try:
            panch = compute_panchanga(date_str, time_str, lat, lon, tz)
        except Exception:
            panch = None

    j_rashi_idx = RASHIS.index(janma_rashi) if janma_rashi and janma_rashi in RASHIS else None
    j_nak_idx = (
        NAKSHATRAS.index(janma_nakshatra)
        if janma_nakshatra and janma_nakshatra in NAKSHATRAS
        else None
    )
    l_rashi_idx = RASHIS.index(lagna_rashi) if lagna_rashi and lagna_rashi in RASHIS else None

    results = GocharResult(
        date=result_date,
        janma_rashi=janma_rashi,
        janma_nakshatra=janma_nakshatra,
        # Grahan (eclipse) — universal, non-personal fact from panchanga.
        eclipse=panch.eclipse if panch is not None else None,
    )

    # Compute transit for each planet
    for planet in PLANETS:
        row = next((t for t in transit_rows if t["planet"] == planet), None)
        if not row:
            continue

        pred = TransitPrediction(
            planet=planet,
            longitude=float(row["lon"]),
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

            # Determine house quality — graph rules when CVCE_GRAPH_AS_RULES=1
            graph_rules = active_transit_rules()
            if graph_rules is not None:
                pred.house_quality, pred.verdict, pred.score = graph_rules.house_quality(
                    planet, house
                )
                rules = graph_rules.transit_houses(planet)
                # Attach richer graph-derived citations for this planet/house
                try:
                    pred.citations = graph_rules.get_citations(planet, house)
                except Exception:
                    pred.citations = []
            else:
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
                        pred.natal_override = (
                            "Exalted/own sign in natal chart mitigates bad transit"
                        )
                        pred.verdict = "neutral"
                        pred.score = max(pred.score, -2)
                elif natal_rashi == DEBIL_SIGN.get(planet):
                    pred.natal_override = (
                        "Debilitated in natal chart; no good even in favourable transit"
                    )
                    if pred.verdict == "shubh":
                        pred.verdict = "neutral"
                        pred.score = min(pred.score, 2)

            # Vedha check
            vedha_rules = GOCHARA_VEDHA.get(planet, {}).get("vedha", {})
            if house in vedha_rules:
                vedha_house = vedha_rules[house]
                for tp in transit_rows:
                    tp_rashi = rashi_index(tp["lon"])
                    tp_house = ((tp_rashi - j_rashi_idx + 12) % 12) + 1
                    if tp_house == vedha_house:
                        pred.vedha_active = True
                        pred.vedha_by = tp["planet"]
                        if pred.verdict == "shubh":
                            pred.verdict = "neutral"
                            pred.score = 0
                        break

            # Vipareetha Vedha — malefic transit softened when blocker occupies vedha house
            vip = VIPAREETHA_VEDHA.get(planet, {})
            if pred.house_quality in ("bad", "worst") and house in vip:
                vedha_house = vip[house]
                for tp in transit_rows:
                    tp_rashi = rashi_index(tp["lon"])
                    tp_house = ((tp_rashi - j_rashi_idx + 12) % 12) + 1
                    if tp_house == vedha_house:
                        pred.vipareetha_vedha_active = True
                        pred.vipareetha_vedha_by = tp["planet"]
                        pred.score = min(pred.score + 4, -1)
                        if pred.verdict == "ashubh":
                            pred.verdict = "neutral"
                        pred.effects.append(
                            f"Vipareetha Vedha by {tp['planet']} — severity reduced"
                        )
                        break

            # Combustion check (transiting planet near transiting Sun)
            sun_row = next((t for t in transit_rows if t["planet"] == "Sun"), None)
            if planet != "Sun" and sun_row and row["rashi"] == sun_row["rashi"]:
                diff = abs(row["deg"] - sun_row["deg"])
                orb = COMBUST_ORB.get(planet, 12)
                pred.combustion = {"diff_deg": round(diff, 1), "orb": orb, "is_combust": diff < orb}

            # Latta check (star affliction)
            if j_nak_idx is not None and planet in LATTA_RULES:
                dist, direction, effect, source = LATTA_RULES[planet]
                planet_nak_idx = _nak_idx(row["lon"])
                kicked = ((planet_nak_idx + direction * (dist - 1)) % 27 + 27) % 27
                kicked_nak = NAKSHATRAS[kicked]
                hits_janma = kicked_nak == janma_nakshatra
                mitigated = row["retro"] and planet in (
                    "Mars",
                    "Jupiter",
                    "Saturn",
                    "Venus",
                    "Mercury",
                )
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
            if graph_rules is not None:
                pred.effects.extend(graph_rules.transit_effects(planet, house)[:6])
            elif pred.house_quality == "good":
                pred.effects.append(f"In {house}th from Janma Rasi — favourable position")
            elif pred.house_quality == "bad":
                pred.effects.append(f"In {house}th from Janma Rasi — unfavourable position")
            elif pred.house_quality == "worst":
                pred.effects.append(
                    f"In {house}th from Janma Rasi — WORST position, caution advised"
                )

            if pred.vedha_active:
                pred.effects.append(f"Gochara Vedha by {pred.vedha_by} — effects cancelled")
            if pred.natal_override:
                pred.effects.append(pred.natal_override)
            if pred.latta and pred.latta["hits_janma"]:
                if pred.latta["mitigated"]:
                    pred.effects.append("Latta on Janma star mitigated by retrogression")
                else:
                    pred.effects.append(f"Latta affliction: {pred.latta['effect']}")
            if pred.combustion and pred.combustion["is_combust"]:
                pred.effects.append(f"Combust — within {pred.combustion['diff_deg']}° of Sun")

        # Lagna-based house scoring — same house-quality tables, Lagna as house 1.
        # Vedha, Sade-Sati, Tara Balam are Moon-centric; not applied here.
        if l_rashi_idx is not None:
            planet_rashi_idx = rashi_index(row["lon"])
            l_house = ((planet_rashi_idx - l_rashi_idx + 12) % 12) + 1
            pred.house_from_lagna = l_house
            graph_rules = active_transit_rules()
            if graph_rules is not None:
                _, _, pred.lagna_score = graph_rules.house_quality(planet, l_house)
                if not getattr(pred, "citations", None):
                    try:
                        pred.citations = graph_rules.get_citations(planet, l_house)
                    except Exception:
                        pass
            else:
                rules = TRANSIT_HOUSES.get(planet, {})
                if l_house in rules.get("worst", []):
                    pred.lagna_score = -10
                elif l_house in rules.get("bad", []):
                    pred.lagna_score = -5
                elif l_house in rules.get("good", []):
                    pred.lagna_score = 7
                else:
                    pred.lagna_score = 0

        results.planet_predictions.append(pred)

    # Moorthy Nirnaya (if Janma Rashi known)
    if j_rashi_idx is not None:
        moon_row = next((t for t in transit_rows if t["planet"] == "Moon"), None)
        if moon_row:
            moon_rashi = rashi_index(moon_row["lon"])
            moorthy_house = ((moon_rashi - j_rashi_idx + 12) % 12) + 1
            if moorthy_house in MOORTHI_RESULTS:
                name, verdict, desc = MOORTHI_RESULTS[moorthy_house]
                results.moorthy = {
                    "house": moorthy_house,
                    "name": name,
                    "verdict": verdict,
                    "description": desc,
                }

    # Sade Sati / Kantaka / Ashtama Shani. Combines Kaksha bindu exception
    # (GPD Ch.27; kaksha_gives_bindu) with Saturn's own aggregate BAV in the
    # transited sign (saturn_bav_in_sign) into a qualitative grade
    # (kaksha_bav_grade) — owner's Kaksha research (Phaladeepika 23.10-20/
    # 26.1-5, BPHS 66.13-15/66.69-72; B-16.14 port from MuhurtaCosmos.jsx).
    # Kantaka Shani is reckoned at Saturn in the 4th, 7th, OR 10th from
    # Janma Rasi (was missing 10th before this port).
    if j_rashi_idx is not None:
        saturn_row = next((t for t in transit_rows if t["planet"] == "Saturn"), None)
        if saturn_row:
            sat_rashi = rashi_index(saturn_row["lon"])
            sat_house = ((sat_rashi - j_rashi_idx + 12) % 12) + 1
            sat_deg = saturn_row.get("deg")
            if sat_deg is None and saturn_row.get("lon") is not None:
                sat_deg = float(saturn_row["lon"]) % 30
            kaksha_ok = sat_house in (1, 12, 2, 4, 7, 8, 10) and bool(
                natal_sign
                and sat_deg is not None
                and kaksha_gives_bindu("Saturn", sat_rashi, sat_deg, natal_sign)
            )
            saturn_bav = (
                saturn_bav_in_sign(sat_rashi, natal_sign) if natal_sign else None
            )
            grade_info = kaksha_bav_grade(kaksha_ok, saturn_bav)
            if sat_house == 1:
                results.sade_sati = {"phase": "peak", **SADE_SATI_PHASES["peak"]}
            elif sat_house == 12:
                results.sade_sati = {"phase": "rise", **SADE_SATI_PHASES["rise"]}
            elif sat_house == 2:
                results.sade_sati = {"phase": "setting", **SADE_SATI_PHASES["setting"]}
            elif sat_house in (4, 7, 10):
                results.kantaka_shani = {
                    "house": sat_house,
                    **{
                        **KANTAKA_ASHTAMA_PHASES["kantaka"],
                        "name": (
                            f"Kantaka/Ardhashtama Shani "
                            f"(Saturn in {sat_house}th from Janma Rasi)"
                        ),
                    },
                }
            elif sat_house == 8:
                results.ashtama_shani = {
                    "house": 8,
                    **KANTAKA_ASHTAMA_PHASES["ashtama"],
                }
            for affliction in (
                results.sade_sati,
                results.ashtama_shani,
                results.kantaka_shani,
            ):
                if affliction is None:
                    continue
                affliction["kaksha_exception"] = kaksha_ok
                affliction["saturn_bav"] = saturn_bav
                affliction["grade"] = grade_info["grade"]
                affliction["subcase"] = grade_info["subcase"]

    # Tara Balam
    if j_nak_idx is not None:
        moon_row = next((t for t in transit_rows if t["planet"] == "Moon"), None)
        if moon_row:
            moon_nak = _nak_idx(moon_row["lon"])
            count = ((moon_nak - j_nak_idx + 27) % 27) + 1
            tara = tara_of(count)
            if tara:
                results.tara_balam = tara

    # B-16.7 — Chandrabala, Ghaat Chakra, Pancha Pakshi, Choghadiya
    # (ported from MuhurtaCosmos.jsx; see prediction/personal_factors.py)
    try:
        from .personal_factors import (
            chandrabala as _chandrabala,
            ghaat_chakra as _ghaat_chakra,
            get_choghadiya as _get_choghadiya,
            pancha_pakshi_ruling_bird as _pancha_pakshi_ruling_bird,
        )
    except ImportError:
        _chandrabala = None  # type: ignore[assignment]
        _ghaat_chakra = None  # type: ignore[assignment]
        _get_choghadiya = None  # type: ignore[assignment]
        _pancha_pakshi_ruling_bird = None  # type: ignore[assignment]

    moon_row = next((t for t in transit_rows if t["planet"] == "Moon"), None)
    moon_rashi_name = moon_row["rashi"] if moon_row else None
    moon_nak_name = moon_row["nak"] if moon_row else None

    if _chandrabala is not None and janma_rashi and moon_rashi_name:
        cb = _chandrabala(janma_rashi, moon_rashi_name)
        if cb is not None:
            results.chandrabala = cb.to_dict()

    if _ghaat_chakra is not None and janma_rashi:
        weekday = getattr(panch, "weekday", None) if panch is not None else None
        tithi_grp = getattr(panch, "tithi_group", None) if panch is not None else None
        gh = _ghaat_chakra(
            janma_rashi,
            weekday=weekday,
            moon_nakshatra=moon_nak_name,
            tithi_group=tithi_grp,
        )
        if gh is not None:
            results.ghaat = gh.to_dict()

    if _pancha_pakshi_ruling_bird is not None and janma_nakshatra:
        results.pancha_pakshi_bird = _pancha_pakshi_ruling_bird(janma_nakshatra)

    if _get_choghadiya is not None and panch is not None:
        # Sunrise/sunset as decimal hours when available on the panchanga result.
        sunrise_h = _decimal_hour(getattr(panch, "sunrise", None))
        sunset_h = _decimal_hour(getattr(panch, "sunset", None))
        query_h = _decimal_hour(time_str)
        if sunrise_h is not None and sunset_h is not None and query_h is not None:
            chog = _get_choghadiya(result_date or date_str, query_h, sunrise_h, sunset_h)
            if chog is not None:
                results.choghadiya = chog.to_dict()

    _apply_special_transit_overrides(results)

    # Overall scoring
    scores = [p.score for p in results.planet_predictions]
    results.overall_score = sum(scores) if scores else 0

    if results.moorthy:
        if results.moorthy.get("verdict") == "shubh":
            results.overall_score += 5
        elif results.moorthy.get("verdict") == "ashubh":
            results.overall_score -= 5

    # Sade Sati / Kantaka / Ashtama share Kaksha×BAV grade scoring (B-16.14).
    # Grade softens or sharpens instead of a flat penalty; natal dignity
    # (exalt/own on Saturn) halves the base penalty before the grade is applied.
    saturn_pred = next(
        (p for p in results.planet_predictions if p.planet == "Saturn"), None
    )

    def _apply_saturn_affliction(affliction: dict) -> int:
        base_penalty = affliction.get("penalty", -15)
        if (
            saturn_pred
            and saturn_pred.natal_override
            and "mitigates" in saturn_pred.natal_override
        ):
            base_penalty = base_penalty // 2
        grade = affliction.get("grade")
        subcase = affliction.get("subcase")
        if grade == "constructive":
            # Strongest-mitigation cell (Kaksha active AND Saturn BAV ≥5), or
            # kakshaOnly fallback when BAV data is unavailable. +8 on this
            # engine's point scale (JS Finder uses +6 on its own scale — same
            # qualitative grade, language-specific magnitudes; see
            # KAKSHA_SADE_SATI_OVERRIDE.md §10).
            penalty = 8
        elif grade == "frictional":
            penalty = base_penalty
        else:
            # MIXED: muted nudge. protectedMicroWindow / bavMixedActive lean
            # mildly positive; supportedFriction / bavMixedInactive half-penalty.
            if subcase in ("protectedMicroWindow", "bavMixedActive"):
                penalty = 3
            else:
                penalty = base_penalty // 2
        affliction["applied_penalty"] = penalty
        return penalty

    if results.sade_sati:
        results.overall_score += _apply_saturn_affliction(results.sade_sati)
    if results.ashtama_shani:
        results.overall_score += _apply_saturn_affliction(results.ashtama_shani)
    if results.kantaka_shani:
        results.overall_score += _apply_saturn_affliction(results.kantaka_shani)
    if results.tara_balam and results.tara_balam.get("verdict") == "ashubh":
        results.overall_score -= 8

    # Chandrabala: +5 acceptable / −12 weak (JS runEngine L3110)
    if results.chandrabala is not None:
        results.overall_score += int(results.chandrabala.get("score", 0))

    # Ghaat Chakra hits: −8 vaar / −8 nak / −6 tithi-class (JS L3104)
    if results.ghaat is not None:
        results.overall_score += int(results.ghaat.get("score", 0))

    # Grahan (eclipse) avoidance — universal, non-personal. Classical muhurta
    # treats an eclipse window as universally inauspicious for new undertakings.
    # Floors the FINAL score after every other modifier so nothing can push it
    # back up. -30 matches MuhurtaCosmos.jsx findMuhurta eclipse penalty.
    if results.eclipse:
        results.overall_score = min(results.overall_score, -30)

    if results.overall_score >= 15:
        results.overall_verdict = "shubh"
    elif results.overall_score >= 0:
        results.overall_verdict = "neutral"
    else:
        results.overall_verdict = "ashubh"

    # Lagna-based overall score — pure planet house scores from Lagna (no Moon modifiers)
    if l_rashi_idx is not None:
        results.lagna_overall_score = sum(p.lagna_score for p in results.planet_predictions)

    # Synthesis
    good = [p for p in results.planet_predictions if p.verdict == "shubh"]
    bad = [p for p in results.planet_predictions if p.verdict == "ashubh"]
    parts = []
    if results.eclipse:
        kind = "Solar" if results.eclipse["type"] == "solar" else "Lunar"
        parts.append(
            f"{kind} eclipse (Grahan) — classically avoided for all new undertakings "
            f"(Moon within {results.eclipse['node_distance']}° of the lunar node)"
        )
    if good:
        parts.append(
            f"{len(good)} planets in favourable transit ({', '.join(p.planet for p in good)})"
        )
    if bad:
        parts.append(
            f"{len(bad)} planets in unfavourable transit ({', '.join(p.planet for p in bad)})"
        )
    if results.sade_sati:
        parts.append(
            f"Sade Sati: {results.sade_sati['phase']} phase — {results.sade_sati['effect']}"
        )
    if results.tara_balam:
        tara_line = (
            f"Tara Balam: {results.tara_balam['name']} "
            f"({results.tara_balam['verdict']}, Paryaya {results.tara_balam['paryaya']})"
        )
        parts.append(tara_line)
        for exc in results.tara_balam.get("exceptions") or []:
            parts.append(f"Tara note: {exc}")
    if results.chandrabala:
        cb = results.chandrabala
        parts.append(
            f"Chandrabala: Moon {cb['house']}th from Janma "
            f"({'ok' if cb.get('ok') else 'weak'}, score {cb.get('score', 0)})"
        )
    if results.ghaat and results.ghaat.get("active"):
        hits = []
        if results.ghaat.get("vaarHit"):
            hits.append("vaar")
        if results.ghaat.get("nakHit"):
            hits.append("nak")
        if results.ghaat.get("tithiHit"):
            hits.append("tithi")
        parts.append(f"Ghaat Chakra active ({', '.join(hits)})")
    if results.pancha_pakshi_bird:
        parts.append(f"Pancha Pakshi ruling bird: {results.pancha_pakshi_bird}")
    if results.choghadiya:
        parts.append(
            f"Choghadiya: {results.choghadiya['name']} ({results.choghadiya['verdict']})"
        )
    if results.kantaka_shani:
        parts.append(results.kantaka_shani["effect"])
    if results.ashtama_shani:
        parts.append(results.ashtama_shani["effect"])
    if results.moorthy:
        parts.append(
            f"Moorthi Nirnaya: {results.moorthy['name']} — {results.moorthy['description']}"
        )
    results.synthesis = " | ".join(parts) if parts else "No natal chart — transit-only analysis"

    return results


def _decimal_hour(value) -> float | None:
    """Coerce sunrise/sunset/time to a local decimal hour, or None if unavailable.

    Accepts ``'HH:MM'``, ``'HH:MM:SS'``, decimal hours, or datetime-like with
    ``.hour``/``.minute``. Returns None for missing/unparseable values so
    Choghadiya stays optional when the panchanga payload lacks sun times.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        parts = value.strip().split(":")
        try:
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            s = float(parts[2]) if len(parts) > 2 else 0.0
            return h + m / 60.0 + s / 3600.0
        except (TypeError, ValueError, IndexError):
            return None
    hour = getattr(value, "hour", None)
    minute = getattr(value, "minute", None)
    if hour is not None and minute is not None:
        second = getattr(value, "second", 0) or 0
        return float(hour) + float(minute) / 60.0 + float(second) / 3600.0
    return None


def _apply_special_transit_overrides(results: GocharResult) -> None:
    """Named transits (Ashtama Shani, Sade Sati, etc.) override per-planet verdicts."""
    for pred in results.planet_predictions:
        house = pred.house_from_janma
        if pred.planet == "Saturn" and house is not None:
            if results.ashtama_shani and house == 8:
                pred.verdict = "ashubh"
                pred.house_quality = "worst"
                pred.score = min(pred.score, -12)
                pred.effects.append(results.ashtama_shani["effect"])
            elif results.kantaka_shani and house == results.kantaka_shani.get("house"):
                pred.verdict = "ashubh"
                pred.house_quality = "bad"
                pred.score = min(pred.score, -10)
                pred.effects.append(results.kantaka_shani["effect"])
            elif results.sade_sati and house in (12, 1, 2):
                pred.verdict = "ashubh"
                pred.house_quality = "worst" if house == 1 else "bad"
                pred.score = min(pred.score, -15 if house == 1 else -12)
                pred.effects.append(
                    f"Sade Sati {results.sade_sati['phase']} phase — {results.sade_sati['effect']}"
                )
        if pred.planet == "Moon" and house == 8:
            pred.verdict = "ashubh"
            pred.house_quality = "worst"
            pred.score = min(pred.score, -10)
            pred.effects.append(
                "Chandrashtama — Moon in 8th from natal Moon; heightened sensitivity and strain"
            )
