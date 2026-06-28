"""
Dasha Impact Analyzer — judged Vimshottari sub-period effects for the native chart.

Combines maha/antar (and optional deeper) lords with lagna lordship, natal placement,
dignity, and natural karakatwa. Output is structured prose drivers, not corpus dumps.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from ..core.panchanga import RASHIS
from ..rules.transit_rules import EXALT_SIGN, DEBIL_SIGN, OWN_SIGN

PLANET_RULES: dict[str, list[str]] = {
    "Sun": ["Leo"],
    "Moon": ["Cancer"],
    "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"],
    "Saturn": ["Capricorn", "Aquarius"],
}

NATURAL_BENEFIC = {"Jupiter", "Venus", "Moon", "Mercury"}
NATURAL_MALEFIC = {"Saturn", "Rahu", "Ketu", "Mars", "Sun"}

LORD_KARAKAS: dict[str, list[str]] = {
    "Sun": ["authority", "father", "vitality", "government"],
    "Moon": ["mind", "mother", "public", "emotions"],
    "Mars": ["courage", "property", "siblings", "competition"],
    "Mercury": ["intellect", "trade", "communication", "education"],
    "Jupiter": ["wisdom", "children", "dharma", "expansion"],
    "Venus": ["marriage", "comforts", "arts", "vehicles"],
    "Saturn": ["discipline", "delay", "service", "longevity"],
    "Rahu": ["ambition", "foreign", "unconventional gains", "obsession"],
    "Ketu": ["detachment", "spirituality", "sudden cuts", "research"],
}

LIFE_AREAS = ("profession", "wealth", "health", "family", "caution")


@dataclass
class DashaFactor:
    role: str
    weight: int
    summary: str


@dataclass
class DashaIntelligence:
    maha_lord: str
    antar_lord: str
    pratyantar_lord: Optional[str]
    maha_start: str
    maha_end: str
    antar_start: str
    antar_end: str
    lagna: Optional[str]
    janma_rashi: Optional[str]
    final_verdict: str
    score: int
    primary_driver: str
    root_cause: str
    maha_houses: list[int] = field(default_factory=list)
    antar_houses: list[int] = field(default_factory=list)
    aggravating: list[str] = field(default_factory=list)
    mitigating: list[str] = field(default_factory=list)
    profession: list[str] = field(default_factory=list)
    wealth: list[str] = field(default_factory=list)
    health: list[str] = field(default_factory=list)
    family: list[str] = field(default_factory=list)
    caution: list[str] = field(default_factory=list)
    factors: list[dict] = field(default_factory=list)
    summary: str = ""
    classical_basis: list[str] = field(default_factory=list)


def _houses_ruled(planet: str, lagna_rashi: str) -> list[int]:
    if planet not in PLANET_RULES or lagna_rashi not in RASHIS:
        return []
    lagna_idx = RASHIS.index(lagna_rashi)
    ruled_signs = set(PLANET_RULES[planet])
    houses = []
    for h in range(1, 13):
        sign = RASHIS[(lagna_idx + h - 1) % 12]
        if sign in ruled_signs:
            houses.append(h)
    return houses


def _house_from_lagna(planet_rashi: str, lagna_rashi: str) -> Optional[int]:
    if planet_rashi not in RASHIS or lagna_rashi not in RASHIS:
        return None
    lagna_idx = RASHIS.index(lagna_rashi)
    p_idx = RASHIS.index(planet_rashi)
    return ((p_idx - lagna_idx) % 12) + 1


def _dignity(planet: str, rashi: str) -> str:
    if rashi == EXALT_SIGN.get(planet):
        return "exalted"
    if rashi in OWN_SIGN.get(planet, []):
        return "own"
    if rashi == DEBIL_SIGN.get(planet):
        return "debilitated"
    return "neutral"


def _verdict(score: int) -> str:
    return "shubh" if score > 0 else "ashubh"


class DashaImpactAnalyzer:
    def analyze(
        self,
        ladder: list[dict],
        lagna_rashi: Optional[str] = None,
        janma_rashi: Optional[str] = None,
        natal_sign: Optional[dict[str, int]] = None,
        transit_verdict: Optional[str] = None,
    ) -> Optional[dict]:
        if not ladder or len(ladder) < 2:
            return None

        maha = ladder[0]
        antar = ladder[1]
        pratyantar = ladder[2] if len(ladder) > 2 else None

        m_lord = maha["lord"]
        a_lord = antar["lord"]
        p_lord = pratyantar["lord"] if pratyantar else None

        factors: list[DashaFactor] = []
        score = 0

        m_houses = _houses_ruled(m_lord, lagna_rashi) if lagna_rashi else []
        a_houses = _houses_ruled(a_lord, lagna_rashi) if lagna_rashi else []

        if m_lord in NATURAL_BENEFIC:
            score += 2
            factors.append(DashaFactor("mitigating", 2, f"{m_lord} Mahadasha — natural benefic period theme"))
        elif m_lord in NATURAL_MALEFIC:
            score -= 1
            factors.append(DashaFactor("contextual", -1, f"{m_lord} Mahadasha — malefic tone; results depend on house lordship"))

        if a_lord in NATURAL_BENEFIC:
            score += 2
            factors.append(DashaFactor("mitigating", 2, f"{a_lord} Antardasha activates benefic sub-theme"))
        elif a_lord in NATURAL_MALEFIC:
            score -= 2
            factors.append(DashaFactor("aggravating", -2, f"{a_lord} Antardasha — challenging sub-period"))

        trikona = {1, 5, 9}
        kendra = {1, 4, 7, 10}
        dusthana = {6, 8, 12}

        for h in m_houses:
            if h in trikona:
                score += 2
                factors.append(DashaFactor("mitigating", 2, f"Maha lord rules {h}th (trikona) — dharma/support"))
            elif h in kendra:
                score += 1
                factors.append(DashaFactor("mitigating", 1, f"Maha lord rules {h}th (kendra) — action and results"))
            elif h in dusthana:
                score -= 2
                factors.append(DashaFactor("aggravating", -2, f"Maha lord rules {h}th (dusthana) — obstacles and strain"))

        for h in a_houses:
            if h in {2, 11}:
                score += 1
                factors.append(DashaFactor("mitigating", 1, f"Antar lord rules {h}th — finances/gains channel"))
            elif h in dusthana:
                score -= 1
                factors.append(DashaFactor("aggravating", -1, f"Antar lord rules {h}th — stress in sub-period"))

        natal_rashi_by_planet: dict[str, str] = {}
        if natal_sign:
            for pname, idx in natal_sign.items():
                if isinstance(idx, int) and 0 <= idx < 12:
                    natal_rashi_by_planet[pname] = RASHIS[idx]

        for lord, label in ((m_lord, "Maha"), (a_lord, "Antar")):
            nr = natal_rashi_by_planet.get(lord)
            if not nr or not lagna_rashi:
                continue
            dig = _dignity(lord, nr)
            h = _house_from_lagna(nr, lagna_rashi)
            if dig == "exalted":
                score += 2
                factors.append(DashaFactor("mitigating", 2, f"{label} lord {lord} exalted in natal chart ({h}th)"))
            elif dig == "own":
                score += 1
                factors.append(DashaFactor("mitigating", 1, f"{label} lord {lord} in own sign natally ({h}th)"))
            elif dig == "debilitated":
                score -= 2
                factors.append(DashaFactor("aggravating", -2, f"{label} lord {lord} debilitated natally — weak delivery"))

        if m_lord == a_lord:
            score += 1
            factors.append(DashaFactor("contextual", 1, "Maha and Antar same planet — theme intensified"))

        if transit_verdict == "ashubh":
            score -= 2
            factors.append(DashaFactor("aggravating", -2, "Current transits unfavourable — delays dasha fruits"))
        elif transit_verdict == "shubh":
            score += 1
            factors.append(DashaFactor("mitigating", 1, "Current transits supportive — dasha results easier"))

        verdict = _verdict(score)
        primary = factors[0].summary if factors else f"{m_lord}–{a_lord} period"
        aggravating = [f.summary for f in factors if f.role == "aggravating"]
        mitigating = [f.summary for f in factors if f.role == "mitigating"]

        profession, wealth, health, family, caution = self._life_bullets(
            m_lord, a_lord, m_houses, a_houses, verdict,
        )

        root = (
            f"{m_lord} Mahadasha with {a_lord} Antardasha "
            f"({antar['start']} to {antar['end']}). "
            f"Maha rules houses {m_houses or '—'}; Antar rules {a_houses or '—'} from Lagna."
        )

        summary = (
            f"{'Favourable' if verdict == 'shubh' else 'Challenging' if verdict == 'ashubh' else 'Mixed'} "
            f"{m_lord}–{a_lord} sub-period. {primary}."
        )

        result = DashaIntelligence(
            maha_lord=m_lord,
            antar_lord=a_lord,
            pratyantar_lord=p_lord,
            maha_start=maha["start"],
            maha_end=maha["end"],
            antar_start=antar["start"],
            antar_end=antar["end"],
            lagna=lagna_rashi,
            janma_rashi=janma_rashi,
            final_verdict=verdict,
            score=score,
            primary_driver=primary,
            root_cause=root,
            maha_houses=m_houses,
            antar_houses=a_houses,
            aggravating=aggravating[:5],
            mitigating=mitigating[:5],
            profession=profession,
            wealth=wealth,
            health=health,
            family=family,
            caution=caution,
            factors=[asdict(f) for f in factors],
            summary=summary,
            classical_basis=["BPHS Ch.46–48 (Dasha phala)", "Phaladeepika Ch.20"],
        )
        return asdict(result)

    def _life_bullets(
        self,
        m_lord: str,
        a_lord: str,
        m_houses: list[int],
        a_houses: list[int],
        verdict: str,
    ) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
        profession, wealth, health, family, caution = [], [], [], [], []

        if 10 in m_houses or 10 in a_houses or 6 in a_houses:
            profession.append(
                f"Career and service themes strong — {a_lord} antar highlights workplace outcomes."
            )
        if 2 in m_houses or 11 in a_houses or 2 in a_houses or 11 in a_houses:
            wealth.append("Financial flow and savings are activated; watch discipline in expenditure.")
        if 6 in m_houses or 8 in m_houses or 12 in a_houses:
            health.append("Health routines need attention; dusthana lordship in maha/antar.")
        if 4 in m_houses or 5 in m_houses or 7 in a_houses:
            family.append("Domestic and relationship matters come to the foreground this antar.")
        if verdict == "ashubh":
            caution.append("Avoid major commitments without review; malefic/dusthana emphasis.")
        elif verdict == "mixed":
            caution.append("Results arrive with delay — persist with remedial discipline.")

        mk = ", ".join(LORD_KARAKAS.get(m_lord, [])[:2])
        ak = ", ".join(LORD_KARAKAS.get(a_lord, [])[:2])
        if mk:
            profession.insert(0, f"Maha karaka themes: {mk}.")
        if ak:
            family.insert(0, f"Antar karaka themes: {ak}.")

        return profession[:3], wealth[:3], health[:3], family[:3], caution[:3]
