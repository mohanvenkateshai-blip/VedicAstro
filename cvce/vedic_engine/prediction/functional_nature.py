"""
Functional nature of planets by Lagna — Parashari temporal benefic/malefic table.

Classical basis (commonly labeled "Table 30" in modern digests; doctrine from
BPHS Ch.34 / Laghu Parashari / Phaladeepika Ch.20):

  • Yogakaraka — single planet owning both a Kendra (1/4/7/10) and a Trikona
    (1/5/9) distinct from pure Lagna-lord dual counting. Six lagnas have one.
  • Functional benefics — lords of Trikona (1,5,9) and pure Kendras when not
    also dusthana/trishadaya-laden.
  • Functional malefics — lords of Trishadaya (3,6,11) and Dusthana (6,8,12).

Rahu/Ketu are omitted from house-lordship (they do not own signs in Parashari
rasi lordship). Callers may still treat them as natural malefics in dasha scoring.
"""

from __future__ import annotations

from vedic_engine.core.panchanga import RASHIS
from vedic_engine.synthesis.dasha_analyzer import YOGAKARAKA_BY_LAGNA

# Sign index 0=Aries … 11=Pisces → classical rasi lord
SIGN_LORDS: dict[int, str] = {
    0: "Mars",
    1: "Venus",
    2: "Mercury",
    3: "Moon",
    4: "Sun",
    5: "Mercury",
    6: "Venus",
    7: "Mars",
    8: "Jupiter",
    9: "Saturn",
    10: "Saturn",
    11: "Jupiter",
}

# House sets (1-based)
_TRIKONA = (1, 5, 9)
_KENDRA = (1, 4, 7, 10)
_TRISHADAYA = (3, 6, 11)
_DUSTHANA = (6, 8, 12)

_CLASSICAL_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")


def house_lords(lagna_idx: int) -> dict[int, str]:
    """Map house number 1–12 → lord planet name for the given Lagna index."""
    li = int(lagna_idx) % 12
    return {h: SIGN_LORDS[(li + h - 1) % 12] for h in range(1, 13)}


def houses_ruled(planet: str, lagna_idx: int) -> list[int]:
    """Houses (1–12) ruled by *planet* for this Lagna."""
    return [h for h, lord in house_lords(lagna_idx).items() if lord == planet]


def yogakaraka_for_lagna(lagna_idx: int) -> list[str]:
    """Yogakaraka planet(s) for Lagna — empty list when none (6 of 12 lagnas)."""
    li = int(lagna_idx) % 12
    name = RASHIS[li] if 0 <= li < 12 else None
    yk = YOGAKARAKA_BY_LAGNA.get(name) if name else None
    if yk:
        return [yk]
    # Derive: planet owning at least one pure kendra and one pure trikona
    # (excluding the trivial "Lagna lord owns 1 which is both" alone).
    found: list[str] = []
    for p in _CLASSICAL_PLANETS:
        hs = set(houses_ruled(p, li))
        kendras = hs & set(_KENDRA)
        trikonas = hs & set(_TRIKONA)
        # Need kendra AND trikona; if only house 1 qualifies both, skip unless
        # another kendra or trikona is also owned.
        if kendras and trikonas and (kendras - {1} or trikonas - {1}):
            if p not in found:
                found.append(p)
    return found


def functional_nature(lagna_idx: int) -> dict:
    """
    Return functional nature buckets for a Lagna.

    Response shape:
      {
        "lagna_idx": int,
        "lagna": str,
        "yogakaraka": [...],
        "benefic": [...],
        "malefic": [...],
        "neutral": [...],
        "house_lords": { "1": "Mars", ... },
        "source": "BPHS Ch.34 / Laghu Parashari / Phaladeepika Ch.20 (Table 30)",
      }
    """
    li = int(lagna_idx) % 12
    lagna_name = RASHIS[li]
    hl = house_lords(li)
    yk = yogakaraka_for_lagna(li)
    yk_set = set(yk)

    # Score each classical planet by lordship weight
    # +2 trikona, +1 kendra (non-1 already counted), -2 dusthana, -2 trishadaya
    scores: dict[str, int] = {p: 0 for p in _CLASSICAL_PLANETS}
    for h, lord in hl.items():
        if lord not in scores:
            continue
        if h in _TRIKONA:
            scores[lord] += 2
        elif h in _KENDRA:
            scores[lord] += 1
        if h in _DUSTHANA:
            scores[lord] -= 2
        if h in _TRISHADAYA:
            scores[lord] -= 2

    benefic: list[str] = []
    malefic: list[str] = []
    neutral: list[str] = []

    for p in _CLASSICAL_PLANETS:
        if p in yk_set:
            # Yogakaraka listed separately; still a top functional benefic
            if p not in benefic:
                benefic.append(p)
            continue
        s = scores[p]
        if s > 0:
            benefic.append(p)
        elif s < 0:
            malefic.append(p)
        else:
            neutral.append(p)

    # Ensure yogakaraka appear first in benefic list
    for p in reversed(yk):
        if p in benefic:
            benefic.remove(p)
            benefic.insert(0, p)

    return {
        "lagna_idx": li,
        "lagna": lagna_name,
        "yogakaraka": yk,
        "benefic": benefic,
        "malefic": malefic,
        "neutral": neutral,
        "house_lords": {str(h): lord for h, lord in hl.items()},
        "source": "BPHS Ch.34 / Laghu Parashari / Phaladeepika Ch.20 (Table 30 functional nature)",
    }


def compute_functional_nature(lagna_idx: int) -> dict:
    """Alias used by API layer."""
    return functional_nature(lagna_idx)
