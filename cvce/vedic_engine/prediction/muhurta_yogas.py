"""
Muhurta yoga evaluation — Vara/Tithi/Nakshatra combination rules.

Sources (graph + classical):
  - muhurta_yogas.md (Ernst Wilhelm)
  - Sarvartha Chintamani / Phaladeepika (via graph citations)
  - knowledge-graph nodes tagged is_muhurta_yoga=True
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.panchanga import VARA_LORD, tithi_group, WEEKDAYS

# Vara lord → weekday index
VARA_LORD_INDEX = {lord: i for i, lord in enumerate(VARA_LORD)}

# Auspicious Vara/Tithi-group yogas (Wilhelm prose)
SIDDHA = {("Venus", "Nanda"), ("Mercury", "Bhadra"), ("Mars", "Jaya"), ("Saturn", "Rikta"), ("Jupiter", "Purna")}
AMRITA = {
    ("Sun", "Nanda"), ("Moon", "Bhadra"), ("Mars", "Nanda"), ("Mercury", "Jaya"),
    ("Jupiter", "Rikta"), ("Venus", "Bhadra"), ("Saturn", "Purna"),
}

# Inauspicious Vara/Tithi-number pairs (dagdha, visha — key pairs from prose)
DAGDHA = {
    ("Sun", 12), ("Moon", 11), ("Mars", 5), ("Mercury", 2), ("Mercury", 3),
    ("Jupiter", 6), ("Venus", 8), ("Saturn", 9),
}
VISHA = {
    ("Sun", 4), ("Moon", 6), ("Mars", 7), ("Mercury", 2), ("Jupiter", 8),
    ("Venus", 9), ("Saturn", 7),
}
KRITISHA = {("Saturn", 6)}  # simplified worst-case anchor


@dataclass
class MuhurtaYogaHit:
    name: str
    nature: str  # auspicious | inauspicious | mixed
    source: str
    detail: str


@dataclass
class MuhurtaYogaResult:
    active: list[MuhurtaYogaHit] = field(default_factory=list)
    overall: str = "neutral"
    score: int = 0
    summary: str = ""


def _vara_lord(weekday: str) -> str:
    try:
        idx = WEEKDAYS.index(weekday)
        return VARA_LORD[idx]
    except ValueError:
        return VARA_LORD[0]


def _tithi_tip(tithi_num: int) -> int:
    """Within-paksha tip 1–15."""
    if tithi_num == 30:
        return 15
    return ((tithi_num - 1) % 15) + 1


def evaluate_muhurta_yogas(
    weekday: str,
    tithi_num: int,
    nakshatra: str | None = None,
    graph_hits: list[dict] | None = None,
) -> MuhurtaYogaResult:
    """Evaluate vara/tithi (and optional nakshatra) combination yogas."""
    result = MuhurtaYogaResult()
    vara = _vara_lord(weekday)
    tip = _tithi_tip(tithi_num)
    group = "Purna" if tithi_num in (15, 30) else tithi_group(tip)

    checks: list[tuple[str, str, str, str]] = []

    if (vara, group) in SIDDHA:
        checks.append(("Siddha", "auspicious", "muhurta_yogas.md", f"{group} tithi on {vara}'s weekday"))
    if (vara, group) in AMRITA:
        checks.append(("Amrita", "auspicious", "muhurta_yogas.md", f"{group} tithi on {vara}'s weekday"))
    if (vara, tip) in DAGDHA:
        checks.append(("Dagdha", "inauspicious", "muhurta_yogas.md", f"Tithi {tip} on {vara}'s weekday"))
    if (vara, tip) in VISHA:
        checks.append(("Visha", "inauspicious", "muhurta_yogas.md", f"Tithi {tip} on {vara}'s weekday"))
    if (vara, tip) in KRITISHA:
        checks.append(("Krakacha", "inauspicious", "muhurta_yogas.md", f"Tithi {tip} on {vara}'s weekday"))

    # Graph-sourced hits (from expanded corpus)
    for gh in graph_hits or []:
        name = gh.get("name") or gh.get("label", "Muhurta yoga")
        nature = gh.get("nature") or gh.get("verdict", "mixed")
        checks.append((name, nature, gh.get("source", "graph.json"), gh.get("detail", "")))

    score = 0
    for name, nature, source, detail in checks:
        result.active.append(MuhurtaYogaHit(name=name, nature=nature, source=source, detail=detail))
        if nature == "auspicious":
            score += 2
        elif nature == "inauspicious":
            score -= 3
        else:
            score += 0

    if score >= 2:
        result.overall = "auspicious"
    elif score <= -3:
        result.overall = "inauspicious"
    else:
        result.overall = "neutral"
    result.score = score

    if result.active:
        names = ", ".join(h.name for h in result.active[:4])
        result.summary = f"Muhurta yogas active: {names} ({result.overall})"
    else:
        result.summary = "No major vara/tithi combination yogas detected"
    return result


def muhurta_yogas_to_dict(r: MuhurtaYogaResult) -> dict:
    return {
        "overall": r.overall,
        "score": r.score,
        "summary": r.summary,
        "active": [
            {"name": h.name, "nature": h.nature, "source": h.source, "detail": h.detail}
            for h in r.active
        ],
    }
