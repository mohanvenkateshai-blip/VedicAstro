"""
Panchanga Computation Module — Tithi, Vaar, Nakshatra, Yoga, Karana

Computes the five limbs of the Panchanga for any given date, time, and location.
Uses the astronomy module for planetary positions and root-finding for boundary times.

Sources:
  - Gochar Phaladeepika Ch.1 (General principles)
  - Phaladeepika Ch.26 (Nakshatra characteristics)
  - Parasara Hora (foundational definitions)
"""

import math
from dataclasses import dataclass, field
from datetime import datetime

from ..core.astronomy import (
    all_positions,
    is_retrograde,
    julian_day,
    norm360,
    sun_moon,
)

# =====================================================================
# Constants
# =====================================================================

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
    "Dhanishtha",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

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

WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

TITHI_NAMES = [
    "Pratipada",
    "Dwitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashti",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dwadashi",
    "Trayodashi",
    "Chaturdashi",
    "Purnima",
]

# 27 Nitya Yogas
NITYA_YOGAS = [
    ("Vishkambha", "Inauspicious", "Yama", "Dharma"),
    ("Priti", "Auspicious", "Vishnu", "Priti"),
    ("Ayushman", "Auspicious", "Chandra", "Chandra"),
    ("Saubhagya", "Auspicious", "Brahma", "Saubhagya"),
    ("Shobhana", "Auspicious", "Indra", "Shobhana"),
    ("Atiganda", "Inauspicious", "Chandra", "Atiganda"),
    ("Sukarma", "Auspicious", "Indra", "Sukarma"),
    ("Dhriti", "Auspicious", "Varuna", "Dhriti"),
    ("Shoola", "Inauspicious", "Shiva", "Shoola"),
    ("Ganda", "Inauspicious", "Kubera", "Ganda"),
    ("Vriddhi", "Auspicious", "Ganesha", "Vriddhi"),
    ("Dhruva", "Auspicious", "Vishnu", "Dhruva"),
    ("Vyaghata", "Inauspicious", "Brahma", "Vyaghata"),
    ("Harshana", "Auspicious", "Vayu", "Harshana"),
    ("Vajra", "Inauspicious", "Indra", "Vajra"),
    ("Siddhi", "Auspicious", "Kartikeya", "Siddhi"),
    ("Vyatipata", "Inauspicious", "Rudra", "Vyatipata"),
    ("Variyan", "Auspicious", "Mitra", "Variyan"),
    ("Parigha", "Inauspicious", "Vishwakarma", "Parigha"),
    ("Shiva", "Auspicious", "Shiva", "Shiva"),
    ("Siddha", "Auspicious", "Ganesha", "Siddha"),
    ("Sadhya", "Auspicious", "Vishnu", "Sadhya"),
    ("Shubha", "Auspicious", "Brahma", "Shubha"),
    ("Shukla", "Auspicious", "Surya", "Shukla"),
    ("Brahma", "Auspicious", "Brahma", "Brahma"),
    ("Indra", "Auspicious", "Indra", "Indra"),
    ("Vaidhriti", "Inauspicious", "Rudra", "Vaidhriti"),
]

# Nakshatra natures (Brihat Samhita / Phaladeepika Ch.26)
NAK_NATURE = {
    "Ashwini": "Light",
    "Bharani": "Fierce",
    "Krittika": "Mixed",
    "Rohini": "Fixed",
    "Mrigashira": "Soft",
    "Ardra": "Sharp",
    "Punarvasu": "Movable",
    "Pushya": "Light",
    "Ashlesha": "Sharp",
    "Magha": "Fierce",
    "Purva Phalguni": "Fierce",
    "Uttara Phalguni": "Fixed",
    "Hasta": "Light",
    "Chitra": "Soft",
    "Swati": "Movable",
    "Vishakha": "Mixed",
    "Anuradha": "Soft",
    "Jyeshtha": "Sharp",
    "Mula": "Sharp",
    "Purva Ashadha": "Fierce",
    "Uttara Ashadha": "Fixed",
    "Shravana": "Movable",
    "Dhanishtha": "Movable",
    "Shatabhisha": "Movable",
    "Purva Bhadrapada": "Fierce",
    "Uttara Bhadrapada": "Fixed",
    "Revati": "Soft",
}

# Karana sequence (60 half-tithis per lunar month)
KARANA_NAMES = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]
KARANA_MALEFIC = {"Vishti", "Shakuni", "Chatushpada", "Naga"}

KARANA_INFO = {
    "Bava": ("Movable", "Indra", "Brahma", "Benefic", "New projects, business, travel"),
    "Balava": ("Movable", "Brahma", "Agni", "Benefic", "Ceremonies, worship, study"),
    "Kaulava": ("Fixed", "Yama", "Kubera", "Benefic", "Agriculture, construction, stability"),
    "Taitila": ("Fixed", "Kubera", "Varuna", "Benefic", "Wealth, property, investments"),
    "Gara": ("Fixed", "Varuna", "Mitra", "Benefic", "Water-related, trade, minerals"),
    "Vanija": ("Movable", "Mitra", "Manibhadra", "Benefic", "Commerce, trade, business"),
    "Vishti": ("Fixed", "Nirriti", "Rakshasa", "Malefic", "Avoid — delays, obstacles, accidents"),
    "Shakuni": ("Fixed", "Rahu", "Kaliyuga Deva", "Malefic", "Curing chronic disease, medicine"),
    "Chatushpada": ("Fixed", "Ketu", "Rudra", "Malefic", "Governance, politics, cattle"),
    "Naga": ("Fixed", "Rahu", "Naga Deva", "Malefic", "Mining, extraction, land-clearing"),
    "Kintughna": ("Fixed", "Ketu", "Vayu", "Benefic", "Marriage, new projects, vows"),
}

# Tithi groups (Nanda/Bhadra/Jaya/Rikta/Purna)
TITHI_GROUP_NAMES = {1: "Nanda", 2: "Bhadra", 3: "Jaya", 4: "Rikta", 5: "Purna"}

# Group info: [lord, element, effect, quality]
GROUP_INFO = {
    "Nanda": ("Venus", "Agni", "Festive, initiating, structural expansion", "good"),
    "Bhadra": ("Mercury", "Prithvi", "Stability, community, material growth", "good"),
    "Jaya": ("Mars", "Akasha", "Overcoming resistance, winning conflicts", "good"),
    "Rikta": ("Saturn", "Vayu", "Destruction of barriers, cleansing", "bad"),
    "Purna": ("Jupiter", "Jala", "Ultimate fulfillment, permanence", "good"),
}

# Vara lords
VARA_LORD = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

# Nakshatra lords
NAK_LORD = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
]

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

# Dagdha Rashis by Tithi
DAGDHA_BY_TITHI = {
    1: ["Libra", "Capricorn"],
    2: ["Sagittarius", "Pisces"],
    3: ["Leo", "Capricorn"],
    4: ["Taurus", "Aquarius"],
    5: ["Gemini", "Virgo"],
    6: ["Aries", "Leo"],
    7: ["Cancer", "Sagittarius"],
    8: ["Gemini", "Virgo"],
    9: ["Leo", "Scorpio"],
    10: ["Leo", "Scorpio"],
    11: ["Sagittarius", "Pisces"],
    12: ["Libra", "Capricorn"],
    13: ["Taurus", "Leo"],
    14: ["Gemini", "Virgo", "Sagittarius", "Pisces"],
    15: [],
    30: [],
}


# =====================================================================
# Helper functions
# =====================================================================


def nak_index(lon: float) -> int:
    """Return nakshatra index (0-26) from sidereal longitude."""
    return int(lon / (360 / 27))


def rashi_index(lon: float) -> int:
    """Return rashi index (0-11) from sidereal longitude."""
    return int(lon / 30)


def pada_of(lon: float) -> int:
    """Return pada (1-4) from sidereal longitude."""
    return int((lon % (360 / 27)) / (360 / 27 / 4)) + 1


def hms(hours: float) -> str:
    """Convert decimal hours to HH:MM AM/PM string."""
    if hours is None:
        return "—"
    nd = hours >= 24
    h = ((hours % 24) + 24) % 24
    hh = int(h)
    mm = int(round((h - hh) * 60))
    if mm == 60:
        mm = 0
        hh = (hh + 1) % 24
    ap = "AM" if hh < 12 else "PM"
    h12 = hh % 12
    if h12 == 0:
        h12 = 12
    suffix = " (+1d)" if nd else ""
    return f"{h12}:{mm:02d} {ap}{suffix}"


def panch_instant(y: int, m: int, d: int, tz: float, hour_local: float, kind: str) -> float:
    """Return the continuous value of a panchanga limb at a given local hour.
    kind: 'tithi' | 'nak' | 'yoga' | 'karana'"""
    jd = julian_day(y, m, d) + (hour_local - tz) / 24
    sm = sun_moon(jd)
    sun, moon = sm["sun"], sm["moon"]

    if kind == "nak":
        return moon / (360 / 27)
    if kind == "tithi":
        return norm360(moon - sun) / 12
    if kind == "karana":
        return norm360(moon - sun) / 6
    if kind == "yoga":
        return norm360(sun + moon) / (360 / 27)
    return 0


def panch_index(y: int, m: int, d: int, tz: float, hour_local: float, kind: str) -> int:
    """Floored index of the panchanga limb at a given local hour."""
    return int(panch_instant(y, m, d, tz, hour_local, kind))


def find_boundary(
    y: int, m: int, d: int, tz: float, kind: str, start_idx: int, lo: float, hi: float
) -> float | None:
    """Find the local hour where the floored panchanga index first increases past start_idx.
    Uses coarse scan + bisection."""
    step = 0.25
    a = lo
    ia = int(panch_instant(y, m, d, tz, a, kind))
    t = lo + step
    while t <= hi + 1e-9:
        it = int(panch_instant(y, m, d, tz, t, kind))
        if it != ia:
            x0, x1 = a, t
            for _ in range(40):
                xm = (x0 + x1) / 2
                im = int(panch_instant(y, m, d, tz, xm, kind))
                if im == ia:
                    x0 = xm
                else:
                    x1 = xm
            return x1
        a = t
        ia = it
        t += step
    return None


def panch_segments(y: int, m: int, d: int, tz: float, kind: str) -> list:
    """Build all segments of a panchanga limb for one civil day with exact boundaries."""
    segs = []
    t = 0
    guard = 0
    while t < 24 - 1e-6 and guard < 40:
        guard += 1
        idx = int(panch_instant(y, m, d, tz, t, kind))
        b = find_boundary(y, m, d, tz, kind, idx, t, 24)
        to = min(b, 24) if b is not None else 24
        segs.append({"idx": idx, "from": t, "to": to})
        if b is None:
            break
        t = b
    # Last segment end may be after midnight
    if segs and segs[-1]["to"] >= 24 - 1e-6:
        b_end = find_boundary(y, m, d, tz, kind, segs[-1]["idx"], 24, 48)
        if b_end is not None:
            segs[-1]["ends_next_day"] = b_end
    return segs


def active_at(segs: list, hour: float) -> dict:
    """Return the segment active at a given hour."""
    return next((s for s in segs if hour >= s["from"] - 1e-9 and hour < s["to"] - 1e-9), segs[-1])


def end_clock(seg: dict) -> float:
    """Get the actual end hour of a segment (may be >24 if it extends past midnight)."""
    return seg.get("ends_next_day", seg["to"])


def tithi_name(tip: int, tithi_num: int) -> str:
    """Return the name of a tithi given its within-paksha tip and total number."""
    if tithi_num == 30:
        return "Amavasya"
    if tip == 15:
        return "Purnima"
    return TITHI_NAMES[tip - 1] if 1 <= tip <= 15 else f"Tithi {tip}"


def tithi_group(tip: int) -> str:
    """Return the group name for a tithi tip (1-15)."""
    return TITHI_GROUP_NAMES.get(((tip - 1) % 5) + 1, "Purna")


def karana_sequence(idx: int) -> str:
    """Return the karana name for a segment index within the lunar month."""
    if idx == 0:
        return "Kintughna"
    if idx >= 57:
        return ["Shakuni", "Chatushpada", "Naga"][idx - 57]
    return KARANA_NAMES[(idx - 1) % 7]


def sun_times(y: int, m: int, d: int, lat: float, lon: float, tz: float) -> dict:
    """NOAA sunrise/sunset approximation. Returns decimal local hours."""
    jd = julian_day(y, m, d)
    n = math.ceil(jd - 2451545.0 + 0.0008)
    Js = n - lon / 360.0
    M = norm360(357.5291 + 0.98560028 * Js)
    C = (
        1.9148 * math.sin(math.radians(M))
        + 0.02 * math.sin(math.radians(2 * M))
        + 0.0003 * math.sin(math.radians(3 * M))
    )
    lam = norm360(M + C + 180 + 102.9372)
    Jt = (
        2451545.0
        + Js
        + 0.0053 * math.sin(math.radians(M))
        - 0.0069 * math.sin(math.radians(2 * lam))
    )
    dec = math.asin(math.sin(math.radians(lam)) * math.sin(math.radians(23.44)))
    cH = (math.sin(math.radians(-0.833)) - math.sin(math.radians(lat)) * math.sin(dec)) / (
        math.cos(math.radians(lat)) * math.cos(dec)
    )
    cH = max(-1, min(1, cH))
    H = math.degrees(math.acos(cH))

    def to_local(J):
        f = ((J + 0.5) % 1) * 24 + tz
        return ((f % 24) + 24) % 24

    return {"sunrise": to_local(Jt - H / 360), "sunset": to_local(Jt + H / 360)}


# =====================================================================
# Main Panchanga Computation
# =====================================================================


@dataclass
class PanchangaResult:
    """Complete Panchanga for one date/time/location."""

    date: str
    time: str
    lat: float
    lon: float
    tz: float
    weekday: str
    sunrise: float
    sunset: float

    # Tithi
    tithi_name: str
    tithi_num: int
    tithi_paksha: str
    tithi_group: str
    tithi_lord: str
    tithi_verdict: str
    tithi_end_hr: float

    # Nakshatra
    nakshatra: str
    nakshatra_nature: str
    nakshatra_lord: str
    nakshatra_verdict: str
    nakshatra_end_hr: float

    # Yoga
    yoga_name: str
    yoga_nature: str
    yoga_lord: str
    yoga_deity: str
    yoga_verdict: str
    yoga_end_hr: float

    # Karana
    karana_name: str
    karana_verdict: str
    karana_end_hr: float

    # Transits
    transit: list = field(default_factory=list)

    # Raw data
    segments: dict = field(default_factory=dict)


_panchanga_rules_version: str | None = None
_panchanga_registered = False


def _clear_panchanga_knowledge_caches() -> None:
    """Drop graph-backed panchanga rule caches so the next run reloads from graph."""
    try:
        from rules_engine.engine import RuleEngine

        RuleEngine._instance = None
    except ImportError:
        pass
    try:
        from graph_rag.muhurta_rules_provider import GraphMuhurtaRules

        GraphMuhurtaRules._instance = None
    except ImportError:
        pass
    try:
        from graph_rag.graph import GraphRAG

        GraphRAG()._loaded = False
    except ImportError:
        pass
    try:
        from knowledge_engine.integration import get_knowledge_engine

        ke = get_knowledge_engine()
        if hasattr(ke.store, "_graph"):
            ke.store._graph = None  # type: ignore[attr-defined]
    except Exception:
        pass


def _on_panchanga_refresh(new_version: str) -> None:
    global _panchanga_rules_version
    _panchanga_rules_version = new_version
    _clear_panchanga_knowledge_caches()


def _register_panchanga_engine() -> None:
    global _panchanga_registered
    if _panchanga_registered:
        return
    try:
        from knowledge_engine.integration import get_knowledge_engine

        get_knowledge_engine().register_engine("panchanga", on_refresh=_on_panchanga_refresh)
        _panchanga_registered = True
    except Exception:
        pass


_register_panchanga_engine()


def _ensure_panchanga_registered() -> None:
    if not _panchanga_registered:
        _register_panchanga_engine()


_register_panchanga_engine()


def compute_panchanga(
    date_str: str = None,
    time_str: str = "12:00",
    lat: float = 12.30,
    lon: float = 76.65,
    tz: float = 5.5,
) -> PanchangaResult:
    """Compute the complete Panchanga for a given date, time, and location.

    Args:
        date_str: 'YYYY-MM-DD' format, defaults to today
        time_str: 'HH:MM' format, defaults to noon
        lat, lon: geographic coordinates
        tz: UTC offset in hours
    """
    _ensure_panchanga_registered()
    if date_str is None:
        now = datetime.now()
        date_str = f"{now.year}-{now.month:02d}-{now.day:02d}"

    y, m, d = map(int, date_str.split("-"))
    hh, mm = map(int, time_str.split(":"))
    query_hour = hh + mm / 60

    jd = julian_day(y, m, d)
    w_idx = ((int(jd + 1.5) % 7) + 7) % 7
    weekday = WEEKDAYS[w_idx]

    st = sun_times(y, m, d, lat, lon, tz)
    sunrise = st["sunrise"]
    sunset = st["sunset"]

    query_jd = jd + (query_hour - tz) / 24
    sm = sun_moon(query_jd)
    sun, moon = sm["sun"], sm["moon"]

    # Segments
    seg_t = panch_segments(y, m, d, tz, "tithi")
    seg_n = panch_segments(y, m, d, tz, "nak")
    seg_y = panch_segments(y, m, d, tz, "yoga")
    seg_k = panch_segments(y, m, d, tz, "karana")

    # Active segments at query hour
    ts = active_at(seg_t, query_hour)
    ns = active_at(seg_n, query_hour)
    ys = active_at(seg_y, query_hour)
    ks = active_at(seg_k, query_hour)

    # Tithi
    tithi_num = (ts["idx"] % 30) + 1
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    tip = tithi_num if tithi_num <= 15 else (30 if tithi_num == 30 else tithi_num - 15)
    group = "Purna" if tithi_num == 30 else tithi_group(tip)
    grp_qual = GROUP_INFO.get(group, ("", "", "", "neutral"))[3]
    tithi_lord = GROUP_INFO.get(group, ("", "", "", "neutral"))[0]
    tithi_end = end_clock(ts)

    # Nakshatra
    nak_idx_val = ns["idx"] % 27
    nak_name = NAKSHATRAS[nak_idx_val]
    nak_nature = NAK_NATURE.get(nak_name, "—")
    nak_lord = NAK_LORD[nak_idx_val]
    nak_end = end_clock(ns)

    # Yoga
    yoga_idx = ys["idx"] % 27
    yoga_name, yoga_nature, yoga_lord, yoga_deity = NITYA_YOGAS[yoga_idx]
    yoga_end = end_clock(ys)

    # Karana
    karana_name = karana_sequence(ks["idx"])
    karana_end = end_clock(ks)

    # Planet positions for transit
    positions = all_positions(query_jd)
    transit = []
    for planet in PLANETS:
        lon = positions[planet]
        deg_in_sign = lon % 30
        dd = int(deg_in_sign)
        mm_val = int((deg_in_sign - dd) * 60)
        transit.append(
            {
                "planet": planet,
                "rashi": RASHIS[rashi_index(lon)],
                "nak": NAKSHATRAS[nak_index(lon)],
                "pada": pada_of(lon),
                "deg": deg_in_sign,
                "deg_label": f"{dd}°{mm_val:02d}′",
                "retro": is_retrograde(planet, query_jd),
                "lon": lon,
            }
        )

    # Verdicts
    tithi_v = "shubh" if grp_qual == "good" else ("ashubh" if grp_qual == "bad" else "neutral")
    nak_v = "neutral"  # Vedha-based (computed in gochar module)
    yoga_v = "shubh" if yoga_nature == "Auspicious" else "ashubh"
    karana_v = "ashubh" if karana_name in KARANA_MALEFIC else "shubh"

    return PanchangaResult(
        date=date_str,
        time=time_str,
        lat=lat,
        lon=lon,
        tz=tz,
        weekday=weekday,
        sunrise=sunrise,
        sunset=sunset,
        tithi_name=tithi_name(tip, tithi_num),
        tithi_num=tithi_num,
        tithi_paksha=paksha,
        tithi_group=group,
        tithi_lord=tithi_lord,
        tithi_verdict=tithi_v,
        tithi_end_hr=tithi_end,
        nakshatra=nak_name,
        nakshatra_nature=nak_nature,
        nakshatra_lord=nak_lord,
        nakshatra_verdict=nak_v,
        nakshatra_end_hr=nak_end,
        yoga_name=yoga_name,
        yoga_nature=yoga_nature,
        yoga_lord=yoga_lord,
        yoga_deity=yoga_deity,
        yoga_verdict=yoga_v,
        yoga_end_hr=yoga_end,
        karana_name=karana_name,
        karana_verdict=karana_v,
        karana_end_hr=karana_end,
        transit=transit,
        segments={"tithi": seg_t, "nak": seg_n, "yoga": seg_y, "karana": seg_k},
    )
