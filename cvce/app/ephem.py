"""
Low-level sidereal ephemeris primitives shared by every endpoint.

This is the single place that talks to PyJHora (Swiss Ephemeris). Both the
granular transit/natal endpoints in `server.py` and the composed canonical
`chart.py` import from here, so positional logic is defined exactly once.

Convention note (preserved from the original engine): PyJHora's `jd` is built
from the *local* clock time of the place; the drik layer subtracts
`place.timezone/24` internally to reach UT. We pass wall-clock time straight in
and hand PyJHora the tz offset on the Place struct — never pre-converting to UT.
"""

from __future__ import annotations

from datetime import datetime

from jhora import const, utils
from jhora.panchanga import drik
from jhora.panchanga.drik import Place

# Keep the planet list to the classical nine (drop Uranus/Neptune/Pluto) so
# planetary_positions lines up 1:1 with the frontend's PLANETS array.
const._INCLUDE_URANUS_TO_PLUTO = False

PLANET_NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
RASHIS = [
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
NAKSHATRAS = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]
WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# Classical dignities (sidereal, whole-sign) by sign index 0=Aries..11=Pisces.
EXALT_SIGN = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6}
DEBIL_SIGN = {"Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11, "Jupiter": 9, "Venus": 5, "Saturn": 0}
OWN_SIGNS = {
    "Sun": [4],
    "Moon": [3],
    "Mars": [0, 7],
    "Mercury": [2, 5],
    "Jupiter": [8, 11],
    "Venus": [1, 6],
    "Saturn": [9, 10],
}
# Combustion orbs in degrees from the Sun (classical, direct-motion values).
COMBUST_ORB = {
    "Moon": 12.0,
    "Mars": 17.0,
    "Mercury": 14.0,
    "Jupiter": 11.0,
    "Venus": 10.0,
    "Saturn": 15.0,
}


def parse_dt(s: str) -> datetime:
    """Tolerant ISO-8601 parse (accepts a trailing 'Z' and space separator)."""
    s = s.strip().replace("Z", "").replace(" ", "T", 1)
    return datetime.fromisoformat(s)


def jd_place(dt: datetime, lat: float, lon: float, tz: float):
    """Build a PyJHora (jd, place) pair from a *local* datetime + tz offset (hours)."""
    jd = utils.julian_day_number(
        (dt.year, dt.month, dt.day), (dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)
    )
    return jd, Place("loc", lat, lon, tz)


def set_ayanamsa(name: str) -> None:
    try:
        drik.set_ayanamsa_mode((name or "LAHIRI").upper())
    except Exception:
        drik.set_ayanamsa_mode("LAHIRI")


def split_longitude(lon: float) -> dict:
    """Decompose an absolute sidereal longitude into rashi / nakshatra / pada."""
    lon = lon % 360.0
    sign = int(lon // 30)
    deg_in_sign = lon - sign * 30
    nak = int(lon // (360 / 27))
    pada = int((lon % (360 / 27)) // (360 / 108)) + 1
    dd = int(deg_in_sign)
    mm = int(round((deg_in_sign - dd) * 60))
    if mm == 60:
        dd, mm = dd + 1, 0
    return {
        "longitude": round(lon, 6),
        "signIndex": sign,
        "rashi": RASHIS[sign],
        "degInSign": round(deg_in_sign, 6),
        "degLabel": f"{dd}°{mm:02d}′",
        "nakIndex": nak,
        "nakshatra": NAKSHATRAS[nak % 27],
        "pada": pada,
    }


def dignity_of(planet: str, sign_index: int) -> str | None:
    """Return 'exalted' | 'debilitated' | 'own' | 'neutral' (None for nodes)."""
    if planet not in EXALT_SIGN:
        return None
    if sign_index == EXALT_SIGN[planet]:
        return "exalted"
    if sign_index == DEBIL_SIGN[planet]:
        return "debilitated"
    if sign_index in OWN_SIGNS[planet]:
        return "own"
    return "neutral"


def retrograde(jd: float, place: Place) -> dict:
    """Retrograde by finite difference of true sidereal longitude (±0.5 day)."""
    jd_ut = jd - place.timezone / 24.0
    retro = {}
    for pid, name in enumerate(PLANET_NAMES):
        if name in ("Sun", "Moon"):
            retro[name] = False
            continue
        if name in ("Rahu", "Ketu"):
            retro[name] = True  # mean nodes are always retrograde
            continue
        try:
            a = drik.sidereal_longitude(jd_ut - 0.5, pid)
            b = drik.sidereal_longitude(jd_ut + 0.5, pid)
            diff = (b - a + 540) % 360 - 180
            retro[name] = diff < 0
        except Exception:
            retro[name] = False
    return retro


def positions(jd: float, place: Place) -> list[dict]:
    """Nine classical bodies with rashi/nakshatra/pada, retrograde, dignity,
    and combustion (computed relative to the Sun)."""
    raw = drik.planetary_positions(jd, place)  # [[pid, deg_in_sign, sign], ...]
    retro = retrograde(jd, place)
    bodies = {}
    for row in raw:
        pid, deg_in_sign, sign = row[0], row[1], row[2]
        if pid < 0 or pid >= len(const.PLANET_LIST):
            continue
        name = PLANET_NAMES[pid]
        lon = sign * 30 + deg_in_sign
        bodies[name] = {"planet": name, **split_longitude(lon), "retro": retro.get(name, False)}
    sun_lon = bodies.get("Sun", {}).get("longitude")
    out = []
    for name in PLANET_NAMES:
        item = bodies.get(name)
        if not item:
            continue
        item["dignity"] = dignity_of(name, item["signIndex"])
        item["combust"] = _is_combust(name, item["longitude"], sun_lon)
        out.append(item)
    return out


def _is_combust(planet: str, lon: float | None, sun_lon: float | None) -> bool:
    if planet not in COMBUST_ORB or lon is None or sun_lon is None:
        return False
    sep = abs((lon - sun_lon + 540) % 360 - 180)
    return sep < COMBUST_ORB[planet]


def ascendant(jd: float, place: Place) -> dict:
    asc = drik.ascendant(jd, place)  # [sign, deg_in_sign, ...]
    sign, deg = int(asc[0]), float(asc[1])
    lon = sign * 30 + deg
    return {"planet": "Ascendant", **split_longitude(lon)}
