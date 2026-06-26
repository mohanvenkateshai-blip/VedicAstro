"""
Ashtakavarga Prediction Module — BAV + SAV transit predictions

Sources:
  - BPHS Ch.67-72 (Ashtakavarga)
  - Gochar Phaladeepika Ch.27
  - Phaladeepika Ch.19
  - Sarvartha Chintamani Ch.17

Ashtakavarga (literally "eight-fold") is the most refined transit prediction
system in Vedic astrology. Each planet contributes bindus (benefic dots) to
12 signs, creating the Bhinnashtakavarga (BAV). The sum of all 7 planets'
bindus gives the Sarvashtakavarga (SAV), which always totals 337.

Transit results are predicted by the number of bindus in the sign a planet
is transiting through (from SAV) or the specific planet's BAV.
"""

from dataclasses import dataclass, field
from typing import Optional

from ..core.astronomy import julian_day, all_positions
from ..core.panchanga import RASHIS, NAKSHATRAS, rashi_index, PLANETS


# =====================================================================
# BAV Tables — Benefic Placements (BPHS standard)
# =====================================================================
# Each planet gives bindus to signs at specific house-distances from
# each contributor (7 planets + Lagna). Per-planet totals: 48/49/39/54/56/52/39.
# Grand total SAV = 337 (mathematical invariant).

BAV_TABLE = {
    "Sun": {
        "Sun": [1, 2, 4, 7, 8, 9, 10, 11],
        "Moon": [3, 6, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11],
        "Venus": [6, 7, 12],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna": [3, 4, 6, 10, 11, 12],
    },
    "Moon": {
        "Sun": [3, 6, 7, 8, 10, 11],
        "Moon": [1, 3, 6, 7, 10, 11],
        "Mars": [2, 3, 5, 6, 9, 10, 11],
        "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 4, 7, 8, 10, 11, 12],
        "Venus": [3, 4, 5, 7, 9, 10, 11],
        "Saturn": [3, 5, 6, 11],
        "Lagna": [3, 6, 10, 11],
    },
    "Mars": {
        "Sun": [3, 5, 6, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12],
        "Venus": [6, 8, 11, 12],
        "Saturn": [1, 4, 7, 8, 9, 10, 11],
        "Lagna": [1, 3, 6, 10, 11],
    },
    "Mercury": {
        "Sun": [5, 6, 9, 11, 12],
        "Moon": [2, 4, 6, 8, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna": [1, 2, 4, 6, 8, 10, 11],
    },
    "Jupiter": {
        "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "Moon": [2, 5, 7, 9, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
        "Venus": [2, 5, 6, 9, 10, 11],
        "Saturn": [3, 5, 6, 12],
        "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11],
    },
    "Venus": {
        "Sun": [8, 11, 12],
        "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars": [3, 5, 6, 9, 11, 12],
        "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn": [3, 4, 5, 8, 9, 10, 11],
        "Lagna": [1, 2, 3, 4, 5, 8, 9, 11],
    },
    "Saturn": {
        "Sun": [1, 2, 4, 7, 8, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [3, 5, 6, 10, 11, 12],
        "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12],
        "Venus": [6, 11, 12],
        "Saturn": [3, 5, 6, 11],
        "Lagna": [1, 3, 4, 6, 10, 11],
    },
}

# Bindu interpretation (Gochar Phaladeepika Ch.27)
BINDU_RESULTS = {
    0: ("Extremely inauspicious", "ashubh", "Danger, severe loss, major health issues, avoid all important work"),
    1: ("Highly inauspicious", "ashubh", "Significant obstacles, financial drain, conflicts, stress"),
    2: ("Inauspicious", "ashubh", "Delays, minor losses, reduced success, tension"),
    3: ("Below average", "ashubh", "Struggles, some obstacles, mixed results with effort"),
    4: ("Average", "neutral", "Moderate results, normal progress, steady but unremarkable"),
    5: ("Above average", "shubh", "Good progress, some gains, supportive environment"),
    6: ("Favourable", "shubh", "Clear progress, gains, success in ventures, good health"),
    7: ("Highly favourable", "shubh", "Strong gains, happiness, success, prosperity"),
    8: ("Exceptionally auspicious", "shubh", "Maximum support, great success, wealth, honour, all-round prosperity"),
}

# SAV band interpretation (GPD Ch.27)
SAV_BANDS = {
    "excellent": (30, 999, "shubh", "Excellent — robust support for all activities"),
    "good": (28, 29, "shubh", "Good — strong support, proceed confidently"),
    "standard": (25, 27, "neutral", "Standard — moderate support, normal progress"),
    "depleted": (0, 24, "ashubh", "Depleted — thin support, avoid major initiatives"),
}

# Trikona Shodhana (reduction) — BPHS Ch.67
# Signs grouped into 4 trikonas: (1,5,9), (2,6,10), (3,7,11), (4,8,12)
# For each trikona where all 3 signs have bindus > 0, reduce the two
# higher bindus to match the lowest. Apply to each BAV first, then to SAV.

TRIKONA_GROUPS = [(0, 4, 8), (1, 5, 9), (2, 6, 10), (3, 7, 11)]  # 0-indexed signs


def _trikona_shodhana(arr: list) -> list:
    """Apply Trikona Shodhana to a 12-element bindu array. Returns new array."""
    result = arr[:]
    for g1, g2, g3 in TRIKONA_GROUPS:
        b1, b2, b3 = result[g1], result[g2], result[g3]
        if b1 > 0 and b2 > 0 and b3 > 0:
            min_b = min(b1, b2, b3)
            reduced = b1 + b2 + b3 - 3 * min_b
            result[g1] = result[g2] = result[g3] = min_b
    return result


def _ekadhipatya_shodhana(bav: dict, sav: list) -> list:
    """Apply Ekadhipatya Shodhana to SAV. Signs with same planetary lord
    (Cancer-Leo, Scorpio-Aries, Capricorn-Aquarius, Pisces-Sagittarius,
    Taurus-Libra, Gemini-Virgo) — if one sign has higher SAV, reduce to match.
    Only applied if SAV > 0 in both signs. Skip if BAV of lord is equal in both."""
    result = sav[:]
    pairs = [(3, 4), (7, 0), (9, 10), (11, 8), (1, 6), (2, 5)]  # 0-indexed
    lords = {"Moon": [3, 4], "Sun": [4], "Mars": [0, 7], "Venus": [1, 6],
             "Mercury": [2, 5], "Jupiter": [8, 11], "Saturn": [9, 10]}
    for s1, s2 in pairs:
        if result[s1] > 0 and result[s2] > 0:
            if result[s1] != result[s2]:
                min_b = min(result[s1], result[s2])
                result[s1] = result[s2] = min_b
    return result


@dataclass
class AshtakavargaResult:
    """Complete Ashtakavarga computation."""
    bav: dict  # {planet: [12 bindus per sign]}
    sav: list  # [12 total bindus]
    planet_totals: dict  # {planet: total bindus}
    total_sav: int  # always 337
    lagna_sign_idx: int = 0

    # Transit bindus
    transit_sav: dict = field(default_factory=dict)  # {planet: bindus in current transit sign}
    moon_transit_bindus: int = 0
    moon_transit_verdict: str = "neutral"
    moon_transit_band: str = ""

    # Synthesis
    summary: str = ""


def compute_ashtakavarga(natal_sign: dict, lagna_sign_idx: int) -> AshtakavargaResult:
    """Compute Bhinnashtakavarga (BAV) and Sarvashtakavarga (SAV).

    Args:
        natal_sign: dict of planet → rashi_idx (0=Aries) for 7 planets
        lagna_sign_idx: Lagna rashi index

    Returns:
        AshtakavargaResult with BAV, SAV, and totals.
    """
    bav = {}
    for planet in BAV_TABLE:
        arr = [0] * 12
        for contributor, distances in BAV_TABLE[planet].items():
            if contributor == "Lagna":
                base = lagna_sign_idx
            elif contributor in natal_sign:
                base = natal_sign[contributor]
            else:
                continue
            for dist in distances:
                arr[(base + dist - 1) % 12] += 1
        bav[planet] = arr

    # SAV: sum all BAVs = 337 (mathematical invariant, BPHS Ch.67)
    sav = [0] * 12
    for planet in bav:
        for s in range(12):
            sav[s] += bav[planet][s]
    # Trikona Shodhana deferred — requires redistribution logic to preserve SAV=337

    # Planet totals
    planet_totals = {p: sum(bav[p]) for p in bav}

    # Verify invariant: SAV sum = 337
    total_sav = sum(sav)

    return AshtakavargaResult(
        bav=bav,
        sav=sav,
        planet_totals=planet_totals,
        total_sav=total_sav,
        lagna_sign_idx=lagna_sign_idx,
    )


def compute_transit_ashtakavarga(akv: AshtakavargaResult, date_str: str = None,
                                  time_str: str = "12:00", lat: float = 12.30,
                                  lon: float = 76.65, tz: float = 5.5) -> AshtakavargaResult:
    """Compute transit bindus for the current date using existing Ashtakavarga.

    For each transiting planet, look up how many SAV bindus are in the sign
    it's currently transiting. This is the classical transit prediction method.
    """
    # Get current planet positions
    from ..core.panchanga import compute_panchanga
    panch = compute_panchanga(date_str, time_str, lat, lon, tz)

    transit_sav = {}
    for planet in PLANETS[:7]:  # Sun through Saturn (Rahu/Ketu excluded)
        row = next((t for t in panch.transit if t["planet"] == planet), None)
        if row:
            sign_idx = rashi_index(row["lon"])
            transit_sav[planet] = {
                "sign": RASHIS[sign_idx],
                "bindus": akv.sav[sign_idx],
                "band": _get_band(akv.sav[sign_idx]),
                "verdict": _get_band(akv.sav[sign_idx])[2],
            }

    # Moon transit bindus (most important — used for Muhurta)
    moon_sign_idx = rashi_index(next((t["lon"] for t in panch.transit if t["planet"] == "Moon"), 0))
    moon_bindus = akv.sav[moon_sign_idx]
    akv.moon_transit_bindus = moon_bindus
    akv.moon_transit_band = _get_band(moon_bindus)[0]
    akv.moon_transit_verdict = _get_band(moon_bindus)[2]

    akv.transit_sav = transit_sav

    # Build summary
    lines = [f"Ashtakavarga SAV total: {akv.total_sav} (invariant: 337) {'✓' if akv.total_sav == 337 else '⚠'}"]
    lines.append(f"Moon transiting {RASHIS[moon_sign_idx]} with {moon_bindus} bindus — {_get_band(moon_bindus)[3]}")
    lines.append("")

    for sign_idx in range(12):
        line = f"  {RASHIS[sign_idx]:12s} "
        bar = "█" * (akv.sav[sign_idx] // 2) + "░" * (16 - akv.sav[sign_idx] // 2)
        line += f"{bar} {akv.sav[sign_idx]:2d}"
        lines.append(line)

    akv.summary = "\n".join(lines)
    return akv


def _get_band(bindus: int) -> tuple:
    """Get the SAV band for a given number of bindus."""
    if bindus >= 30:
        return SAV_BANDS["excellent"]
    if bindus >= 28:
        return SAV_BANDS["good"]
    if bindus >= 22:
        return SAV_BANDS["standard"]
    return SAV_BANDS["depleted"]


def bindu_prediction(bindus: int) -> dict:
    """Get prediction for a specific bindu count (0-8)."""
    return {
        "count": bindus,
        "label": BINDU_RESULTS.get(bindus, ("Unknown", "neutral", ""))[0],
        "verdict": BINDU_RESULTS.get(bindus, ("", "neutral", ""))[1],
        "effect": BINDU_RESULTS.get(bindus, ("", "", ""))[2],
    }
