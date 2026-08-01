"""
Muhurta Lagna scoring, Pushkarabhaga, Gandanta, and Varga charts.

Ported from panchanga_muhurtha ``MuhurtaCosmos.jsx`` (B-16.3):
  - ``muhurtaLagna()``       ~L3588–3640
  - ``isPushkarabhaga()``    ~L400–409 + ``PUSHKARABHAGA_DEG``
  - ``isGandanta()``         ~L433–437 + ``GANDANTA_SIGN_PAIRS``
  - ``computeVargas()``      ~L2305–2326
  - Varga activity scoring   ~L4059–4096 + ``ACTIVITY_PROFILES`` varga map

Classical sources (cited per factor):
  - Brihat Parasara Hora Sastra (BPHS), Girish Chand Sharma tr. — Gandanta
    ("half Ghari Lagna at the end of Pisces … beginning of Aries … left out
    in all auspicious deeds"; same junctions at Cancer/Leo, Scorpio/Sagittarius);
    divisional-chart definitions (Ch.6 Vargas).
  - Muhurta Darpana (quoted in C.S. Patel, *Predicting Through Navamsa & Nadi
    Astrology*) — Pushkarabhaga single degree per triplicity, "useful for
    fixing Pushkara Muhurta for auspicious activities."
  - Dr. N.G. Kumaran, "Pushkara Navamsa", IJATET Vol.8 Issue.1 (2023) —
    cross-check of Pushkara degree/navamsa framing.
  - Standard muhurta practice for Lagna strength: empty 8th, fixed Lagna
    preferred for durability, Jupiter/benefics in kendra–trikona, Lagna lord
    in kendra–trikona vs dusthana (6/8/12).

Astronomy is intentionally *not* reimplemented here. Callers supply sidereal
longitudes (and optionally a pre-built house map) from the host engine
(Swiss Ephemeris / CVCE core), matching how ``natal_structure.py`` is wired.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, MutableMapping, Optional, Sequence, Union

# ---------------------------------------------------------------------------
# Foundational tables (must match MuhurtaCosmos.jsx exactly)
# ---------------------------------------------------------------------------

RASHIS: list[str] = [
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
]

PLANETS: list[str] = [
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
]

RASHI_LORD: dict[str, str] = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

FIXED_SIGNS: list[str] = ["Taurus", "Leo", "Scorpio", "Aquarius"]
DUAL_SIGNS: list[str] = ["Gemini", "Virgo", "Sagittarius", "Pisces"]
# Movable (chara) = the rest: Aries, Cancer, Libra, Capricorn

BENEFICS: list[str] = ["Jupiter", "Venus", "Mercury", "Moon"]
MALEFICS: list[str] = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]

KENDRA: list[int] = [1, 4, 7, 10]
TRIKONA: list[int] = [1, 5, 9]
DUSTHANA: list[int] = [6, 8, 12]
# Houses counted as "well placed" for a varga house-lord (JS L4089)
VARGA_GOOD_HOUSES: list[int] = [1, 4, 5, 7, 9, 10]

# Sign element cycle Aries→Pisces (JS SIGN_ELEMENT)
SIGN_ELEMENT: list[str] = [
    "fire",
    "earth",
    "air",
    "water",
    "fire",
    "earth",
    "air",
    "water",
    "fire",
    "earth",
    "air",
    "water",
]

# Pushkarabhaga: single classical degree per triplicity (floor match).
# Source: Muhurta Darpana via C.S. Patel; Fire 21°, Earth 14°, Air 24°, Water 7°.
PUSHKARABHAGA_DEG: dict[str, int] = {
    "fire": 21,
    "earth": 14,
    "air": 24,
    "water": 7,
}

# Gandanta junctions: water→fire sign pairs (0-based indices).
# BPHS: Pisces→Aries, Cancer→Leo, Scorpio→Sagittarius; ±3°20' at the boundary.
GANDANTA_SIGN_PAIRS: list[tuple[int, int]] = [(11, 0), (3, 4), (7, 8)]
GANDANTA_ORB_DEG: float = 3.0 + 20.0 / 60.0  # 3°20′

# Finder integration weights (JS findMuhurta ~L4175–4192)
MUHURTA_LAGNA_SHUBH_BONUS: int = 8
MUHURTA_LAGNA_ASHUBH_PENALTY: int = -10
MUHURTA_LAGNA_ASHUBH_CAP: int = 62
PUSHKARABHAGA_BONUS: int = 10
GANDANTA_PENALTY: int = -12
GANDANTA_CAP: int = 35

# Muhurta Lagna internal score thresholds (JS)
ML_SHUBH_MIN: int = 68
ML_NEUTRAL_MIN: int = 48

Number = Union[int, float]


# ---------------------------------------------------------------------------
# Activity → primary Varga + houses (from ACTIVITY_PROFILES, varga fields only)
# Full profiles (nakshatra/weekday/karana) land in activity_profiles.py (B-16.4).
# ---------------------------------------------------------------------------

ACTIVITY_VARGA_PROFILES: dict[str, dict[str, Any]] = {
    "Business & Finance · Accounting & Bookkeeping": {"varga": "D2", "vargaHouses": [2, 6]},
    "Business & Finance · Borrowing": {"varga": "D2", "vargaHouses": [2]},
    "Business & Finance · Investing": {"varga": "D2", "vargaHouses": [2, 11]},
    "Business & Finance · Lending": {"varga": "D2", "vargaHouses": [2, 6]},
    "Business & Finance · Opening a Business or Store": {
        "varga": "D2",
        "vargaHouses": [2, 7, 10],
    },
    "Business & Finance · Paying Debts": {"varga": "D2", "vargaHouses": [6]},
    "Business & Finance · Selling": {"varga": "D2", "vargaHouses": [11]},
    "Business & Finance · Signing Contracts & Agreements": {
        "varga": "D2",
        "vargaHouses": [2, 7],
    },
    "Jewelry & Gems · Making Jewelry with Gems": {"varga": "D2", "vargaHouses": [2]},
    "Jewelry & Gems · Making Other Jewelry": {"varga": "D2", "vargaHouses": [2]},
    "Jewelry & Gems · Wearing a Gem First Time": {"varga": "D2", "vargaHouses": [2]},
    "Construction & Home · Digging Foundation (Bhumi Puja)": {
        "varga": "D4",
        "vargaHouses": [4],
    },
    "Construction & Home · Installing the Main Door": {
        "varga": "D4",
        "vargaHouses": [4],
    },
    "Crafts & Arts · Learning & Making Crafts": {"varga": "D24", "vargaHouses": [5]},
    "Crafts & Arts · Beginning a Painting": {"varga": "D24", "vargaHouses": [5]},
    "Education & Learning · Alphabet (Aksharabhyasa)": {
        "varga": "D24",
        "vargaHouses": [5],
    },
    "Education & Learning · Astrology (Jyotisha)": {
        "varga": "D24",
        "vargaHouses": [5, 9],
    },
    "Education & Learning · Grammar & Language": {
        "varga": "D24",
        "vargaHouses": [2, 5],
    },
    "Education & Learning · Mathematics": {"varga": "D24", "vargaHouses": [5]},
    "Education & Learning · Medicine": {"varga": "D24", "vargaHouses": [5]},
    "Education & Learning · Art & Music": {"varga": "D24", "vargaHouses": [5]},
    "Education & Learning · Starting a Trade or Apprenticeship": {
        "varga": "D24",
        "vargaHouses": [5, 10],
    },
    "Job & Career · Applying for a New Job": {"varga": "D10", "vargaHouses": [10]},
    "Job & Career · Job Interview": {"varga": "D10", "vargaHouses": [10, 7]},
    "Job & Career · Asking for Promotion": {"varga": "D10", "vargaHouses": [10, 5]},
    "Job & Career · Hiring a New Employee": {"varga": "D10", "vargaHouses": [10, 6]},
    "Litigation & Legal · Filing a Case": {"varga": "D9", "vargaHouses": [6, 9]},
    "Litigation & Legal · Taking an Oath or Swearing-In": {
        "varga": "D9",
        "vargaHouses": [9],
    },
    "Litigation & Legal · Signing Important Legal Documents": {
        "varga": "D9",
        "vargaHouses": [7, 9],
    },
    "Marriage & Family · Wedding (Vivaha)": {"varga": "D9", "vargaHouses": [7]},
    "Marriage & Family · First Conception (Garbhadhana)": {
        "varga": "D7",
        "vargaHouses": [5],
    },
    "Real Estate · Purchasing Property": {"varga": "D4", "vargaHouses": [4]},
    "Real Estate · Dividing Property": {"varga": "D4", "vargaHouses": [4]},
    "Religion & Spirituality · Mantra Initiation (Diksha)": {
        "varga": "D9",
        "vargaHouses": [9],
    },
    "Religion & Spirituality · Installing a Deity (Pratishtha)": {
        "varga": "D9",
        "vargaHouses": [9],
    },
    "Religion & Spirituality · Sacred Thread (Upanayanam)": {
        "varga": "D9",
        "vargaHouses": [9, 5],
    },
    "Religion & Spirituality · Religious Study": {"varga": "D9", "vargaHouses": [9]},
    "Religion & Spirituality · Performing Ceremonies (Puja & Yajna)": {
        "varga": "D9",
        "vargaHouses": [9],
    },
    "Religion & Spirituality · Planetary Pacification (Shanti Karma)": {
        "varga": "D9",
        "vargaHouses": [9],
    },
    "Religion & Spirituality · Beginning a Vrata (Religious Observance)": {
        "varga": "D9",
        "vargaHouses": [9],
    },
    "Vehicles · First Driving (Learning)": {"varga": "D4", "vargaHouses": [4]},
    "Agriculture & Farming · Sowing Seeds": {"varga": "D4", "vargaHouses": [4]},
    "Agriculture & Farming · Harvesting": {"varga": "D4", "vargaHouses": [4]},
    "Agriculture & Farming · Buying Cattle & Livestock": {
        "varga": "D4",
        "vargaHouses": [4],
    },
    "Agriculture & Farming · Planting Trees": {"varga": "D4", "vargaHouses": [4]},
    "Agriculture & Farming · Taming or Training Animals": {
        "varga": "D4",
        "vargaHouses": [4],
    },
    "Writing · Starting a New Writing Project": {
        "varga": "D24",
        "vargaHouses": [2, 5],
    },
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def norm360(deg: Number) -> float:
    """Normalise degrees into [0, 360)."""
    return float(deg) % 360.0


def rashi_index(lon: Number) -> int:
    """0-based rashi index from sidereal longitude (Aries=0 … Pisces=11)."""
    return int(math.floor(norm360(lon) / 30.0)) % 12


def deg_in_sign(lon: Number) -> float:
    """Longitude within the current sign, [0, 30)."""
    return norm360(lon) % 30.0


def house_from(planet_sign_idx: int, lagna_idx: int) -> int:
    """Whole-sign house number (1..12) of ``planet_sign_idx`` from ``lagna_idx``."""
    return (int(planet_sign_idx) - int(lagna_idx) + 12) % 12 + 1


def _clamp_score(score: Number, lo: int = 0, hi: int = 100) -> int:
    return int(max(lo, min(hi, round(score))))


def _as_sign_name(sign: Union[int, str]) -> str:
    if isinstance(sign, int):
        return RASHIS[sign % 12]
    if sign in RASHIS:
        return sign
    # allow lowercase / common aliases
    titled = str(sign).strip().title()
    if titled in RASHIS:
        return titled
    raise ValueError(f"Unknown rashi: {sign!r}")


def _as_sign_idx(sign: Union[int, str]) -> int:
    if isinstance(sign, int):
        return sign % 12
    return RASHIS.index(_as_sign_name(sign))


# ---------------------------------------------------------------------------
# Pushkarabhaga
# ---------------------------------------------------------------------------

def is_pushkarabhaga(sign_idx: Union[int, str], deg_in_sign_: Number) -> bool:
    """Return True if Lagna (or any point) sits in Pushkarabhaga.

    Pushkarabhaga is a *single* classically-cited degree per sign, keyed by
    triplicity — not a range. Matched as the whole degree
    (``floor(deg) == target``), the classical reading of a one-degree Bhaga
    rather than a zero-width instant.

    Source: Muhurta Darpana (via C.S. Patel); degrees Fire 21 / Earth 14 /
    Air 24 / Water 7. Checked at the Muhurta Lagna in findMuhurta (+10 bonus).

    Port of JS ``isPushkarabhaga(signIdx, degInSign)``.
    """
    si = _as_sign_idx(sign_idx)
    element = SIGN_ELEMENT[si]
    target = PUSHKARABHAGA_DEG[element]
    return int(math.floor(float(deg_in_sign_))) == target


# ---------------------------------------------------------------------------
# Gandanta
# ---------------------------------------------------------------------------

def is_gandanta(sign_idx: Union[int, str], deg_in_sign_: Number) -> bool:
    """Return True if the point falls in a Gandanta junction zone.

    Three water→fire boundaries (Pisces/Aries, Cancer/Leo, Scorpio/Sagittarius).
    Zone = last 3°20′ of the water sign **or** first 3°20′ of the fire sign.

    BPHS (Sharma tr.): the half-ghati Lagna at these junctions "is to be left
    out in all auspicious deeds." In findMuhurta: −12 bonus and score cap 35.

    Port of JS ``isGandanta(signIdx, degInSign)``.
    """
    si = _as_sign_idx(sign_idx)
    d = float(deg_in_sign_)
    orb = GANDANTA_ORB_DEG
    for water, fire in GANDANTA_SIGN_PAIRS:
        if si == water and d >= 30.0 - orb:
            return True
        if si == fire and d < orb:
            return True
    return False


# ---------------------------------------------------------------------------
# Divisional charts (Vargas) — BPHS Ch.6
# ---------------------------------------------------------------------------

def compute_vargas(
    planet_lons: Mapping[str, Number],
    asc_lon: Number,
) -> dict[str, dict[str, int]]:
    """Compute D1/D2/D4/D7/D9/D10/D24 sign indices for planets + Lagna.

    Port of JS ``computeVargas(planetLons, ascLon)``.

    Each chart maps body name → 0-based rashi index occupied in that varga.
    Formulas match the browser engine exactly (including odd/even start rules):

      D2  Hora         — 15° halves; odd signs 1st=Leo(4)/2nd=Cancer(3), even reversed
      D4  Chaturthamsha — 7°30′ parts; part N → sign + N×3
      D7  Saptamsha    — ~4°17′; odd starts in sign, even starts in 7th
      D9  Navamsha     — 3°20′; fire→Aries, earth→Cap, air→Lib, water→Can
      D10 Dashamsha    — 3°; odd starts in sign, even starts in 9th
      D24 Siddhamsha   — 1°15′; odd→Leo(4), even→Cancer(3)

    Activity mapping (primary varga):
      D2 wealth · D4 home/land · D7 children · D9 marriage/dharma ·
      D10 career · D24 education/skills  (+ D1 always as the base chart)
    """
    v: dict[str, dict[str, int]] = {
        "D1": {},
        "D2": {},
        "D4": {},
        "D7": {},
        "D9": {},
        "D10": {},
        "D24": {},
    }
    all_points: dict[str, float] = {
        **{k: float(val) for k, val in planet_lons.items()},
        "Lagna": float(asc_lon),
    }

    # Navamsha start sign by rashi index (fire/earth/air/water)
    d9_start = {
        0: 0,
        4: 0,
        8: 0,  # fire → Aries
        1: 9,
        5: 9,
        9: 9,  # earth → Capricorn
        2: 6,
        6: 6,
        10: 6,  # air → Libra
        3: 3,
        7: 3,
        11: 3,  # water → Cancer
    }

    for name, lon in all_points.items():
        lon = norm360(lon)
        si = rashi_index(lon)
        deg = lon % 30.0

        v["D1"][name] = si

        # D2 Hora — JS: si % 2 === 0 (even idx = odd-numbered sign Aries…)
        # Aries si=0 → odd sign → 1st half Leo(4), 2nd Cancer(3)
        if si % 2 == 0:  # odd-numbered signs (Aries, Gemini, …)
            v["D2"][name] = 4 if deg < 15.0 else 3
        else:
            v["D2"][name] = 3 if deg < 15.0 else 4

        # D4 Chaturthamsha
        v["D4"][name] = (si + int(math.floor(deg / 7.5)) * 3) % 12

        # D7 Saptamsha
        p7 = int(math.floor(deg / (30.0 / 7.0)))
        if si % 2 == 0:
            v["D7"][name] = (si + p7) % 12
        else:
            v["D7"][name] = (si + 6 + p7) % 12

        # D9 Navamsha
        p9 = int(math.floor(deg / (30.0 / 9.0)))
        v["D9"][name] = (d9_start[si] + p9) % 12

        # D10 Dashamsha
        p10 = int(math.floor(deg / 3.0))
        if si % 2 == 0:
            v["D10"][name] = (si + p10) % 12
        else:
            v["D10"][name] = (si + 8 + p10) % 12

        # D24 Siddhamsha
        p24 = int(math.floor(deg / 1.25))
        if si % 2 == 0:
            v["D24"][name] = (4 + p24) % 12
        else:
            v["D24"][name] = (3 + p24) % 12

    return v


# ---------------------------------------------------------------------------
# Varga activity scoring
# ---------------------------------------------------------------------------

def score_varga_for_activity(
    vargas: Mapping[str, Mapping[str, int]],
    activity_key: Optional[str] = None,
    *,
    varga_name: Optional[str] = None,
    varga_houses: Optional[Sequence[int]] = None,
) -> dict[str, Any]:
    """Score the activity-relevant divisional chart.

    Port of JS findMuhurta factor #26 (Varga scoring, ~L4059–4096).

    For each house in ``vargaHouses`` (default ``[1]``):
      - Benefic in that varga house → +3
      - Malefic in that varga house → −2
      - Lord of the sign on that house well-placed (1/4/5/7/9/10) → +3
      - Lord in dusthana (6/8/12) → −3

    House lord is the lord of the *sign actually occupying* that house from
    the Varga Lagna (not a fixed Aries-rising table).

    Returns ``{score, reasons, varga, vargaHouses}``. ``score`` is the raw
    varga contribution (added to the finder bonus in JS).
    """
    prof: dict[str, Any] = {}
    if activity_key and activity_key in ACTIVITY_VARGA_PROFILES:
        prof = dict(ACTIVITY_VARGA_PROFILES[activity_key])
    if varga_name:
        prof["varga"] = varga_name
    if varga_houses is not None:
        prof["vargaHouses"] = list(varga_houses)

    vname = prof.get("varga")
    if not vname or not vargas:
        return {
            "score": 0,
            "reasons": [],
            "varga": vname,
            "vargaHouses": list(prof.get("vargaHouses") or [1]),
        }

    varga_chart = vargas.get(vname)
    if not varga_chart or "Lagna" not in varga_chart:
        return {
            "score": 0,
            "reasons": [],
            "varga": vname,
            "vargaHouses": list(prof.get("vargaHouses") or [1]),
        }

    v_lagna = int(varga_chart["Lagna"])
    v_houses = list(prof.get("vargaHouses") or [1])
    v_score = 0
    reasons: list[str] = []

    for vh in v_houses:
        vh = int(vh)
        vh_sign = (v_lagna + vh - 1) % 12

        # Occupants of this varga house
        for p, si in varga_chart.items():
            if p == "Lagna":
                continue
            ph = (int(si) - v_lagna + 12) % 12 + 1
            if ph != vh:
                continue
            if p in BENEFICS:
                v_score += 3
                reasons.append(f"{p} in {vname} {vh}th (benefic)")
            elif p in MALEFICS:
                v_score -= 2
                # JS pushes no reason string for malefic occupancy (silent −2)

        # Lord of the sign on this house from Varga Lagna
        h_lord = RASHI_LORD[RASHIS[vh_sign]]
        if h_lord in varga_chart and varga_chart[h_lord] is not None:
            hl_house = (int(varga_chart[h_lord]) - v_lagna + 12) % 12 + 1
            n_label = str(vname).replace("D", "")
            if hl_house in VARGA_GOOD_HOUSES:
                v_score += 3
                reasons.append(
                    f"{h_lord} (lord of D{n_label} {vh}th) well-placed in {hl_house}th"
                )
            elif hl_house in DUSTHANA:
                v_score -= 3
                reasons.append(
                    f"{h_lord} (lord of D{n_label} {vh}th) in dusthana"
                )

    return {
        "score": v_score,
        "reasons": reasons,
        "varga": vname,
        "vargaHouses": v_houses,
    }


# ---------------------------------------------------------------------------
# Muhurta Lagna evaluation
# ---------------------------------------------------------------------------

def planet_houses_from_longitudes(
    planet_lons: Mapping[str, Number],
    asc_lon: Number,
) -> dict[str, int]:
    """Whole-sign house (1..12) of each planet from the Muhurta Lagna."""
    asc_idx = rashi_index(asc_lon)
    houses: dict[str, int] = {}
    for p in PLANETS:
        if p not in planet_lons:
            continue
        houses[p] = house_from(rashi_index(planet_lons[p]), asc_idx)
    return houses


def evaluate_muhurta_lagna(
    *,
    asc_lon: Optional[Number] = None,
    asc_sign: Optional[Union[int, str]] = None,
    asc_deg: Optional[Number] = None,
    planet_lons: Optional[Mapping[str, Number]] = None,
    houses: Optional[Mapping[str, int]] = None,
) -> dict[str, Any]:
    """Evaluate Muhurta Lagna strength.

    Port of JS ``muhurtaLagna()`` scoring body (~L3588–3640). Astronomy is
    left to the caller — pass either:

      * ``planet_lons`` + ``asc_lon`` (sidereal degrees), or
      * precomputed ``houses`` {planet: 1..12} + ``asc_sign`` (+ optional
        ``asc_deg`` for Pushkarabhaga/Gandanta downstream checks).

    Scoring (base 50, clamped 0–100):
      +14 empty 8th / −12 occupied 8th
      +10 fixed Lagna / dual+benefic-in-1st +6 / dual alone +1 / movable 0
      +12 Jupiter in kendra or trikona
      +6  any benefic in kendra/trikona
      −10 malefic in 1st
      +12 Lagna lord in kendra/trikona / −12 lord in dusthana

    Verdict: ``shubh`` ≥68, ``neutral`` ≥48, else ``ashubh``.

    Note on the backlog phrasing "score cap 36–100": the JS clamp is 0–100;
    the 35-cap applies to *finder day score* when Gandanta hits the ML, not
    to this internal 0–100 Lagna strength meter. We match JS.
    """
    if houses is None:
        if planet_lons is None or asc_lon is None:
            raise ValueError(
                "evaluate_muhurta_lagna requires planet_lons+asc_lon or houses+asc_sign"
            )
        houses = planet_houses_from_longitudes(planet_lons, asc_lon)

    houses = {str(k): int(v) for k, v in houses.items()}

    if asc_sign is None:
        if asc_lon is None:
            raise ValueError("asc_sign or asc_lon is required")
        asc_sign_name = RASHIS[rashi_index(asc_lon)]
        if asc_deg is None:
            asc_deg = deg_in_sign(asc_lon)
    else:
        asc_sign_name = _as_sign_name(asc_sign)
        if asc_deg is None and asc_lon is not None:
            asc_deg = deg_in_sign(asc_lon)
        elif asc_deg is None:
            asc_deg = 0.0

    asc_deg_f = float(asc_deg)
    # Match JS `+(asc % 30).toFixed(2)` presentation when derived from lon
    asc_deg_out = round(asc_deg_f, 2)

    score = 50
    notes: list[str] = []

    # 8th house occupancy
    in8 = [p for p in PLANETS if houses.get(p) == 8]
    if len(in8) == 0:
        score += 14
        notes.append("8th house from Lagna is unoccupied (favourable).")
    else:
        score -= 12
        notes.append(
            f"8th house occupied by {', '.join(in8)} (weakens the Lagna)."
        )

    # Sign nature
    if asc_sign_name in FIXED_SIGNS:
        score += 10
        notes.append(f"{asc_sign_name} is a fixed sign (preferred for durability).")
    elif asc_sign_name in DUAL_SIGNS:
        ben_here = [
            p
            for p in PLANETS
            if houses.get(p) == 1 and p in BENEFICS
        ]
        if ben_here:
            score += 6
            notes.append(
                f"{asc_sign_name} (dual) tenanted by benefic {', '.join(ben_here)}."
            )
        else:
            score += 1
            notes.append(f"{asc_sign_name} is a dual sign (acceptable).")
    else:
        notes.append(
            f"{asc_sign_name} is a movable sign (least preferred for permanence)."
        )

    # Jupiter in kendra or trikona
    jup_h = houses.get("Jupiter")
    if jup_h is not None and (jup_h in KENDRA or jup_h in TRIKONA):
        score += 12
        notes.append(
            f"Jupiter in house {jup_h} from Lagna (kendra/trikona — strong support)."
        )

    # Any benefic in kendra/trikona
    ben_kt = [
        p
        for p in BENEFICS
        if houses.get(p) is not None
        and (houses[p] in KENDRA or houses[p] in TRIKONA)
    ]
    if ben_kt:
        score += 6
        notes.append(f"Benefics in kendra/trikona: {', '.join(ben_kt)}.")

    # Malefic in 1st
    mal_in1 = [
        p for p in PLANETS if houses.get(p) == 1 and p in MALEFICS
    ]
    if mal_in1:
        score -= 10
        notes.append(
            f"Malefic {', '.join(mal_in1)} in the 1st house (adverse)."
        )

    # Lagna lord placement
    ll = RASHI_LORD[asc_sign_name]
    ll_h = houses.get(ll)
    if ll_h is not None and (ll_h in KENDRA or ll_h in TRIKONA):
        score += 12
        notes.append(
            f"Lagna lord {ll} in house {ll_h} (kendra/trikona — well placed)."
        )
    elif ll_h is not None and ll_h in DUSTHANA:
        score -= 12
        notes.append(
            f"Lagna lord {ll} in dusthana (house {ll_h}) — weak."
        )
    elif ll_h is not None:
        notes.append(f"Lagna lord {ll} in house {ll_h}.")
    else:
        notes.append(f"Lagna lord {ll} placement unknown (missing longitude).")
        ll_h = None

    score = _clamp_score(score, 0, 100)
    if score >= ML_SHUBH_MIN:
        verdict = "shubh"
    elif score >= ML_NEUTRAL_MIN:
        verdict = "neutral"
    else:
        verdict = "ashubh"

    # Convenience flags for the exact ML degree (Pushkara / Gandanta)
    si = RASHIS.index(asc_sign_name)
    pushkara = is_pushkarabhaga(si, asc_deg_out)
    gandanta = is_gandanta(si, asc_deg_out)

    return {
        "ascSign": asc_sign_name,
        "ascDeg": asc_deg_out,
        "lagnaLord": ll,
        "lagnaLordHouse": ll_h,
        "eighthOccupants": in8,
        "houses": dict(houses),
        "score": score,
        "verdict": verdict,
        "notes": notes,
        "isPushkarabhaga": pushkara,
        "isGandanta": gandanta,
    }


# Alias matching the JS name more closely
muhurta_lagna = evaluate_muhurta_lagna


def apply_muhurta_lagna_to_finder(
    ml: Mapping[str, Any],
    *,
    bonus: int = 0,
    cap: Optional[int] = None,
) -> dict[str, Any]:
    """Apply Muhurta Lagna / Pushkarabhaga / Gandanta to a finder day score.

    Port of the JS findMuhurta block ~L4175–4192:

      * shubh ML  → +8
      * ashubh ML → −10, cap ≤ 62
      * Pushkarabhaga at ML degree → +10
      * Gandanta at ML degree → −12, cap ≤ 35

    ``cap is None`` means uncapped. Returns
    ``{bonus, cap, reasons}`` with the *new* running bonus/cap.
    """
    reasons: list[str] = []
    new_bonus = int(bonus)
    new_cap = cap
    sign = ml.get("ascSign", "?")

    verdict = ml.get("verdict")
    if verdict == "shubh":
        new_bonus += MUHURTA_LAGNA_SHUBH_BONUS
        reasons.append(f"Muhurta Lagna {sign} is strong")
    elif verdict == "ashubh":
        new_bonus += MUHURTA_LAGNA_ASHUBH_PENALTY
        new_cap = (
            MUHURTA_LAGNA_ASHUBH_CAP
            if new_cap is None
            else min(new_cap, MUHURTA_LAGNA_ASHUBH_CAP)
        )
        reasons.append(f"Muhurta Lagna {sign} is weak")

    # Prefer flags on the ml dict; recompute if only raw fields present
    pushkara = ml.get("isPushkarabhaga")
    if pushkara is None and "ascSign" in ml and "ascDeg" in ml:
        pushkara = is_pushkarabhaga(ml["ascSign"], ml["ascDeg"])
    if pushkara:
        new_bonus += PUSHKARABHAGA_BONUS
        reasons.append(
            f"Muhurta Lagna {sign} falls in Pushkarabhaga — classically "
            "auspicious for this exact Muhurta"
        )

    gandanta = ml.get("isGandanta")
    if gandanta is None and "ascSign" in ml and "ascDeg" in ml:
        gandanta = is_gandanta(ml["ascSign"], ml["ascDeg"])
    if gandanta:
        new_bonus += GANDANTA_PENALTY
        new_cap = (
            GANDANTA_CAP if new_cap is None else min(new_cap, GANDANTA_CAP)
        )
        reasons.append(
            f"Muhurta Lagna {sign} falls in Gandanta — classically avoided "
            "for auspicious deeds (BPHS)"
        )

    return {"bonus": new_bonus, "cap": new_cap, "reasons": reasons}


__all__ = [
    "RASHIS",
    "PLANETS",
    "RASHI_LORD",
    "FIXED_SIGNS",
    "DUAL_SIGNS",
    "BENEFICS",
    "MALEFICS",
    "KENDRA",
    "TRIKONA",
    "DUSTHANA",
    "SIGN_ELEMENT",
    "PUSHKARABHAGA_DEG",
    "GANDANTA_SIGN_PAIRS",
    "GANDANTA_ORB_DEG",
    "ACTIVITY_VARGA_PROFILES",
    "norm360",
    "rashi_index",
    "deg_in_sign",
    "house_from",
    "is_pushkarabhaga",
    "is_gandanta",
    "compute_vargas",
    "score_varga_for_activity",
    "planet_houses_from_longitudes",
    "evaluate_muhurta_lagna",
    "muhurta_lagna",
    "apply_muhurta_lagna_to_finder",
]
