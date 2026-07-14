"""Central safety and privacy policy for product-facing predictions.

This module deliberately operates on copies of calculated facts.  It must not be
used while ingesting, indexing, or learning from the classical source corpus.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Iterable


BLOCKED_CLAIM_TEXT = (
    "A personalised prediction about this high-severity topic is not provided."
)

_CATEGORY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "death_or_fatality",
        re.compile(
            r"\b(?:death|die[sd]?|dying|not survive|pass(?:es|ed)? away|"
            r"lose (?:his|her|their|your) life|fatal(?:ity|ly)?|life[- ]threatening|"
            r"widow(?:ed|hood)?|widower)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "suicide_or_self_harm",
        re.compile(
            r"\b(?:suicid(?:e|al)|self[- ]harm|(?:take|end) (?:his|her|their|your) own life)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "violence_or_assassination",
        re.compile(
            r"\b(?:assassinat(?:e|ed|ion)|murder(?:ed)?|homicide|violen(?:ce|t)|"
            r"weapon attack|deadly accident)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "serious_disease_diagnosis",
        re.compile(
            r"\b(?:diagnos(?:e|ed|is) with|cancer|tumou?r|leukemia|stroke|"
            r"heart attack|hiv|aids|dementia|paralysis|kidney disease|"
            r"liver disease|multiple sclerosis|parkinson(?:'s)?|alzheimer(?:'s)?|terminal illness|"
            r"organ failure|serious (?:disease|illness)|malignant condition(?: confirmed)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "pregnancy_outcome",
        re.compile(
            r"\b(?:pregnan(?:t|cy)|miscarriage|stillbirth|abortion|infertility|"
            r"foetal|fetal|unborn child|loss (?:of )?(?:an? )?unborn child|"
            r"childbirth complication)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "crime_or_arrest",
        re.compile(
            r"\b(?:arrest(?:ed)?|imprison(?:ed|ment)?|prison|jail(?:ed)?|"
            r"criminal|crime|conviction|police custody)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "abuse",
        re.compile(
            r"\b(?:abuse[sd]?|abusive|domestic violence|sexual assault|rape[sd]?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "infidelity",
        re.compile(
            r"\b(?:infidelit(?:y|ies)|adulter(?:y|ous)|extramarital affair|spouse(?:'s)? affair|"
            r"cheat(?:s|ed|ing)? on (?:you|a |his |her |their ))\b",
            re.IGNORECASE,
        ),
    ),
)

_TRAGEDY = re.compile(
    r"\b(?:tragedy|tragic|calamity|catastrophe|grave accident|severe accident|"
    r"irreparable loss)\b",
    re.IGNORECASE,
)

_PREDICTIVE_FRAMING = re.compile(
    r"\b(?:will|may|might|likely|expected|expectation|indicat(?:e|ed|es|ion)|"
    r"predict(?:s|ed|ion)?|forecast(?:s|ed)?|risk of|destined|fated)\b",
    re.IGNORECASE,
)

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")
_PLANETS = frozenset(
    {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
)
_RASHIS = frozenset(
    {
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
        "Scorpio",
        "Sagittarius",
        "Capricorn",
        "Aquarius",
        "Pisces",
    }
)
_VERDICTS = frozenset(
    {
        "shubh",
        "ashubh",
        "mixed",
        "neutral",
        "favourable",
        "unfavourable",
        "supportive",
        "challenging",
        "good",
        "bad",
        "worst",
        "excellent",
        "strong",
        "moderate",
        "weak",
        "depleted",
    }
)
_ROLES = frozenset({"aggravating", "mitigating", "contextual"})
_YOGA_CATEGORIES = frozenset(
    {"raja", "dhana", "arishta", "parivartana", "pancha_mahapurusha", "general"}
)
_NARRATIVE_KEYS = frozenset(
    {
        "summary",
        "day_summary",
        "transit_summary",
        "synthesis",
        "prose",
        "prediction",
        "interpretation",
        "manifestation_text",
        "effects",
        "effect",
        "positive_impact",
        "negative_impact",
        "primary_driver",
        "root_cause",
        "aggravating",
        "mitigating",
        "profession",
        "career",
        "wealth",
        "health",
        "family",
        "caution",
        "recommendation",
        "recommendations",
        "warnings",
        "life_domains",
        "what_to_expect",
    }
)


@dataclass(frozen=True)
class ClaimSafetyResult:
    value: Any
    blocked_count: int
    blocked_categories: tuple[str, ...]


def _claim_categories(text: str) -> set[str]:
    categories = {name for name, pattern in _CATEGORY_PATTERNS if pattern.search(text)}
    # In a personalised report there is no safe actionable value in predicting a
    # tragedy. This deliberately blocks the broader phrase too, which also
    # covers named third parties whose relationship was not supplied.
    if _TRAGEDY.search(text):
        categories.add("named_third_party_tragedy")
    return categories if categories and _PREDICTIVE_FRAMING.search(text) else set()


def filter_personalised_claim_text(text: str) -> ClaimSafetyResult:
    """Remove unsafe sentences while retaining safe, useful sentences.

    Reports are personalised contexts, so matching high-severity statements are
    blocked even if phrased as uncertain predictions.  If every non-empty
    sentence is unsafe, a stable refusal sentence is returned.
    """
    if not text or not isinstance(text, str):
        return ClaimSafetyResult(text, 0, ())

    safe_parts: list[str] = []
    categories: set[str] = set()
    blocked_count = 0
    for part in _SENTENCE_BOUNDARY.split(text):
        part = part.strip()
        if not part:
            continue
        matched = _claim_categories(part)
        if matched:
            blocked_count += 1
            categories.update(matched)
        else:
            safe_parts.append(part)

    if not blocked_count:
        return ClaimSafetyResult(text, 0, ())
    if not safe_parts:
        safe_parts.append(BLOCKED_CLAIM_TEXT)
    return ClaimSafetyResult(" ".join(safe_parts), blocked_count, tuple(sorted(categories)))


def apply_product_claim_policy(value: Any) -> ClaimSafetyResult:
    """Return a product-safe copy, filtering only claim-bearing fields.

    Structural values such as the Cancer rashi, source citations and educational
    text are preserved. A bare string is treated as narration and filtered.
    """
    categories: set[str] = set()
    blocked_count = 0

    def visit(item: Any, claim_context: bool = False) -> Any:
        nonlocal blocked_count
        if isinstance(item, str):
            if not claim_context:
                return item
            result = filter_personalised_claim_text(item)
            blocked_count += result.blocked_count
            categories.update(result.blocked_categories)
            return result.value
        if isinstance(item, dict):
            output: dict[Any, Any] = {}
            for key, child in item.items():
                child_context = claim_context or (
                    isinstance(key, str) and key.lower() in _NARRATIVE_KEYS
                )
                output[key] = visit(child, child_context)
            return output
        if isinstance(item, list):
            return [visit(child, claim_context) for child in item]
        if isinstance(item, tuple):
            return tuple(visit(child, claim_context) for child in item)
        return copy.deepcopy(item)

    safe_value = visit(value, isinstance(value, str))
    return ClaimSafetyResult(safe_value, blocked_count, tuple(sorted(categories)))


def _number(value: Any, *, integer: bool = False) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value) if integer else value


def _token(value: Any, approved: frozenset[str]) -> str | None:
    return value if isinstance(value, str) and value in approved else None


def _numbers(value: Any, *, minimum: int | None = None, maximum: int | None = None) -> list:
    if not isinstance(value, (list, tuple)):
        return []
    output: list[int | float] = []
    for item in value:
        number = _number(item)
        if number is None:
            continue
        if minimum is not None and number < minimum:
            continue
        if maximum is not None and number > maximum:
            continue
        output.append(number)
    return output


def _put(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None and value != [] and value != {}:
        target[key] = value


def _project_factors(value: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for factor in value if isinstance(value, list) else []:
        if not isinstance(factor, dict):
            continue
        projected: dict[str, Any] = {}
        _put(projected, "role", _token(factor.get("role"), _ROLES))
        _put(projected, "weight", _number(factor.get("weight")))
        if projected:
            output.append(projected)
    return output


def _project_dasha(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, Any] = {}
    for key in ("maha_lord", "antar_lord", "pratyantar_lord"):
        _put(output, key, _token(value.get(key), _PLANETS))
    _put(output, "lagna", _token(value.get("lagna"), _RASHIS))
    _put(output, "janma_rashi", _token(value.get("janma_rashi"), _RASHIS))
    _put(output, "final_verdict", _token(value.get("final_verdict"), _VERDICTS))
    _put(output, "score", _number(value.get("score")))
    _put(output, "maha_houses", _numbers(value.get("maha_houses"), minimum=1, maximum=12))
    _put(output, "antar_houses", _numbers(value.get("antar_houses"), minimum=1, maximum=12))
    _put(output, "factors", _project_factors(value.get("factors")))
    return output


def _project_transit_planets(value: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for planet in value if isinstance(value, list) else []:
        if not isinstance(planet, dict):
            continue
        projected: dict[str, Any] = {}
        _put(projected, "planet", _token(planet.get("planet"), _PLANETS))
        _put(projected, "rashi", _token(planet.get("rashi"), _RASHIS))
        for key in ("house_from_janma", "house_from_lagna"):
            house = _number(planet.get(key), integer=True)
            _put(projected, key, house if house is not None and 1 <= house <= 12 else None)
        for key in ("final_verdict", "verdict", "house_quality", "dignity"):
            _put(projected, key, _token(planet.get(key), _VERDICTS))
        _put(projected, "score", _number(planet.get("score")))
        _put(projected, "retrograde", planet.get("retrograde") if isinstance(planet.get("retrograde"), bool) else None)
        _put(projected, "factors", _project_factors(planet.get("factors")))
        if projected:
            output.append(projected)
    return output


def _project_transit(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, Any] = {}
    _put(output, "janma_rashi", _token(value.get("janma_rashi"), _RASHIS))
    _put(output, "overall_verdict", _token(value.get("overall_verdict"), _VERDICTS))
    _put(output, "overall_score", _number(value.get("overall_score")))
    _put(output, "planets", _project_transit_planets(value.get("planets")))
    return output


def _project_timing(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, Any] = {}
    for key in ("verdict", "transit_verdict"):
        _put(output, key, _token(value.get(key), _VERDICTS))
    for key in ("score", "dasha_score", "transit_score"):
        _put(output, key, _number(value.get(key)))
    return output


def _project_yogas(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, Any] = {}
    for key in ("activeCount", "totalChecked"):
        _put(output, key, _number(value.get(key), integer=True))
    yoga_rows: list[dict[str, Any]] = []
    raw_yogas = value.get("yogas")
    if isinstance(raw_yogas, dict):
        yoga_values = list(raw_yogas.values())
    elif isinstance(raw_yogas, (list, tuple)):
        yoga_values = list(raw_yogas)
    else:
        yoga_values = []
    for yoga in yoga_values:
        if not isinstance(yoga, dict):
            continue
        projected: dict[str, Any] = {}
        _put(projected, "category", _token(yoga.get("category"), _YOGA_CATEGORIES))
        _put(projected, "strength", _token(yoga.get("strength"), _VERDICTS))
        _put(projected, "benefic", yoga.get("benefic") if isinstance(yoga.get("benefic"), bool) else None)
        planets = [p for p in yoga.get("planets", []) if isinstance(p, str) and p in _PLANETS]
        _put(projected, "planets", planets)
        if projected:
            yoga_rows.append(projected)
    _put(output, "items", yoga_rows)
    return output


def _project_ashtakavarga(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, Any] = {}
    _put(output, "total", _number(value.get("total")))
    _put(output, "sav", _numbers(value.get("sav"), minimum=0, maximum=56))
    totals = {
        planet: number
        for planet, raw in (value.get("planet_totals") or {}).items()
        if planet in _PLANETS and (number := _number(raw)) is not None
    } if isinstance(value.get("planet_totals"), dict) else {}
    _put(output, "planet_totals", totals)
    annotated: list[dict[str, Any]] = []
    for row in value.get("sav_annotated", []) if isinstance(value.get("sav_annotated"), list) else []:
        if not isinstance(row, dict):
            continue
        projected: dict[str, Any] = {}
        _put(projected, "sign", _token(row.get("sign"), _RASHIS))
        _put(projected, "bindus", _number(row.get("bindus")))
        _put(projected, "band", _token(row.get("band"), _VERDICTS))
        if projected:
            annotated.append(projected)
    _put(output, "sav_annotated", annotated)
    return output


def prepare_external_narration_payload(
    facts: dict[str, Any],
    birth: dict[str, Any] | None,
    allowed_sources: Iterable[str],
) -> dict[str, Any]:
    """Project approved structured fields for the external LLM.

    This is deliberately a positive schema, not a denylist scrub. Unknown keys,
    all free text, dates/times, names, places, coordinates, metadata and event
    history are structurally incapable of crossing this boundary. ``birth`` is
    accepted only for API compatibility and is never read into the projection.
    """
    del birth
    projectors = {
        "dasha_intelligence": _project_dasha,
        "transit_intelligence": _project_transit,
        "timing_merge": _project_timing,
        "yogas": _project_yogas,
        "ashtakavarga": _project_ashtakavarga,
    }
    projected: dict[str, Any] = {}
    for source in allowed_sources:
        projector = projectors.get(source)
        if projector is None or source not in facts:
            continue
        safe_value = projector(facts[source])
        if safe_value:
            projected[source] = safe_value
    return projected
