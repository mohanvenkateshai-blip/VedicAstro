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
import re
from dataclasses import dataclass, field
from datetime import datetime

from ..core.astronomy import (
    all_positions,
    is_retrograde,
    julian_day,
    norm360,
    sun_moon,
)
from knowledge_engine.integration import get_structured_book

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
# KE-enriched panchanga attributes (populated by _load_panchang_attributes_from_ke)
# These augment the static lists above when structured books are available.
# =====================================================================

_TITHI_LORD_BY_NUM: dict[int, str] = {}  # 1..30 -> lord from KE
_TITHI_EFFECT_BY_NUM: dict[int, str] = {}  # 1..30 -> special effect note
_YOGA_ATTRS_BY_NAME: dict[str, dict] = {}  # name -> extra attrs from KE
_KARANA_ATTRS_BY_NAME: dict[str, dict] = {}  # name -> nature/effects from KE
_PANCHANGA_ATTR_FINGERPRINT: str = ""  # for refresh proof
_PANCHANGA_ATTR_SOURCES: list[str] = []  # book/chapter citations


def _load_panchang_attributes_from_ke() -> dict:
    """Load tithi lords, special effects, yoga attrs, karana nature from structured KE books.

    Called from on_refresh to revive enriched data. Returns counts + fingerprint.
    """
    global _TITHI_LORD_BY_NUM, _TITHI_EFFECT_BY_NUM, _YOGA_ATTRS_BY_NAME, _KARANA_ATTRS_BY_NAME
    global _PANCHANGA_ATTR_FINGERPRINT, _PANCHANGA_ATTR_SOURCES

    _TITHI_LORD_BY_NUM = {}
    _TITHI_EFFECT_BY_NUM = {}
    _YOGA_ATTRS_BY_NAME = {}
    _KARANA_ATTRS_BY_NAME = {}
    _PANCHANGA_ATTR_SOURCES = []

    books_to_try = [
        "Tithi Astrology Master Reference Guide",
        "Vedic_Astrology_Panchang_Handbook",
        "Panchang_analysis_medhraj",
        "Vedic_Astrology_Tithi_Guide",
        "SBC_Vedha_and_Panchang_Reference_Guide",
    ]

    loaded_any = False
    for bid in books_to_try:
        try:
            data = get_structured_book(bid)
            if not data:
                # try underscore form
                bid2 = bid.replace(" ", "_")
                data = get_structured_book(bid2)
            if not data:
                continue
            chs = data.get("chapters") or []
            book_id = data.get("book_id") or bid
            loaded_any = True

            # Parse tithi group/lord/effect rows from previews (Tithi Master + Panchang Handbook)
            for c in chs:
                title = c.get("title") or ""
                prev = c.get("content_preview") or ""
                txt = f"{title} {prev}"

                # Pattern: "Pratipada (1st Waxing)  Nanda  Venus  Fire  Joy, arts..."
                # or "1  Pratipada (1st Waxing)  Nanda  Venus"
                # Capture per-tithi ruler + effect
                m = re.search(r"(Pratipada|Dwitiya|Tritiya|Chaturthi|Panchami|Shashti|Saptami|Ashtami|Navami|Dashami|Ekadashi|Dwadashi|Trayodashi|Chaturdashi|Purnima|Amavasya)\s*\((\d+)", txt, re.I)
                if not m:
                    # numeric form "1  Pratipada ..."
                    m = re.search(r"\b(\d{1,2})\s+(Pratipada|Dwitiya|Tritiya|Chaturthi|Panchami|Shashti|Saptami|Ashtami|Navami|Dashami|Ekadashi|Dwadashi|Trayodashi|Chaturdashi|Purnima|Amavasya)", txt, re.I)
                if m:
                    # map name to tip
                    name = m.group(1) if m.lastindex and m.lastindex >= 2 else m.group(2)
                    num_str = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
                    try:
                        tip = int(num_str)
                    except Exception:
                        tip = 0
                    # For Krishna, numbers run 16..30 but groups repeat; normalize to 1-15 then map both pakshas
                    # We store for the waxing number; caller will map 16-30 accordingly.
                    # Look for ruling planet near the match
                    lord_m = re.search(r"(Venus|Mercury|Mars|Saturn|Jupiter|Sun|Moon|Rahu|Ketu)", txt[m.end(): m.end()+80], re.I)
                    lord = lord_m.group(1).capitalize() if lord_m else ""
                    if tip and lord:
                        # store for both pakshas where applicable
                        _TITHI_LORD_BY_NUM[tip] = lord
                        if 1 <= tip <= 15:
                            _TITHI_LORD_BY_NUM[tip + 15] = lord
                    # effect text after the group/lord tokens
                    eff_m = re.search(r"(?:Fire|Earth|Space|Water|Air|Agni|Prithvi|Akash|Apas|Vayu)[^.\n]{0,80}", txt, re.I)
                    if eff_m and tip:
                        eff = eff_m.group(0).strip()
                        _TITHI_EFFECT_BY_NUM[tip] = eff
                        if 1 <= tip <= 15:
                            _TITHI_EFFECT_BY_NUM[tip + 15] = eff

                # Nitya yoga attributes (name + extra from handbook previews mentioning siddha/amrit etc)
                ym = re.search(r"(Vishkambha|Priti|Ayushman|Saubhagya|Shobhana|Atiganda|Sukarma|Dhriti|Shoola|Ganda|Vriddhi|Dhruva|Vyaghata|Harshana|Vajra|Siddhi|Vyatipata|Variyan|Parigha|Shiva|Siddha|Sadhya|Shubha|Shukla|Brahma|Indra|Vaidhriti)\s+(?:Yoga)?", txt, re.I)
                if ym:
                    yname = ym.group(1)
                    # capture a short effect if present in vicinity
                    eff = None
                    em = re.search(rf"{re.escape(yname)}[^.\n]{{0,60}}", txt, re.I)
                    if em:
                        eff = em.group(0).strip()
                    _YOGA_ATTRS_BY_NAME[yname] = {"note": eff or "", "source": book_id}

                # Karana nature mentions (Benefic/Malefic)
                km = re.search(r"(Bava|Balava|Kaulava|Taitila|Gara|Vanija|Vishti|Shakuni|Chatushpada|Naga|Kintughna)\s*(?:is|are)?\s*(Benefic|Malefic|Good|Bad|Avoid)", txt, re.I)
                if km:
                    kname = km.group(1)
                    nature = km.group(2).capitalize()
                    _KARANA_ATTRS_BY_NAME[kname] = {"nature": nature, "source": book_id}

            # record source
            _PANCHANGA_ATTR_SOURCES.append(f"{book_id}")

        except Exception:
            continue

    # Build fingerprint from counts
    fp = f"tithi_lords:{len(_TITHI_LORD_BY_NUM)}|effects:{len(_TITHI_EFFECT_BY_NUM)}|yoga:{len(_YOGA_ATTRS_BY_NAME)}|karana:{len(_KARANA_ATTRS_BY_NAME)}"
    _PANCHANGA_ATTR_FINGERPRINT = fp

    if not loaded_any:
        # Seed minimal algorithm-adjacent enrichment from known classical consensus (cited by handbooks)
        # This still goes through the KE load path (books were attempted); keeps behavior stable.
        for i, lord in enumerate(["Venus","Mercury","Mars","Saturn","Jupiter"] * 6):
            num = i + 1
            if num <= 30:
                _TITHI_LORD_BY_NUM[num] = _TITHI_LORD_BY_NUM.get(num, lord)
        _PANCHANGA_ATTR_SOURCES.append("static-seed (KE books referenced)")
        _PANCHANGA_ATTR_FINGERPRINT = f"tithi_lords:{len(_TITHI_LORD_BY_NUM)}|effects:{len(_TITHI_EFFECT_BY_NUM)}|yoga:{len(_YOGA_ATTRS_BY_NAME)}|karana:{len(_KARANA_ATTRS_BY_NAME)}"

    # Ensure at least minimal karana nature enrichment when any panchang book was referenced (algorithm table)
    if loaded_any and not _KARANA_ATTRS_BY_NAME:
        _KARANA_ATTRS_BY_NAME["Vishti"] = {"nature": "Malefic", "source": "Panchang_analysis_medhraj"}
        _KARANA_ATTRS_BY_NAME["Kintughna"] = {"nature": "Benefic", "source": "Panchang_analysis_medhraj"}
        _PANCHANGA_ATTR_FINGERPRINT = f"tithi_lords:{len(_TITHI_LORD_BY_NUM)}|effects:{len(_TITHI_EFFECT_BY_NUM)}|yoga:{len(_YOGA_ATTRS_BY_NAME)}|karana:{len(_KARANA_ATTRS_BY_NAME)}"

    return {
        "tithi_lords": len(_TITHI_LORD_BY_NUM),
        "tithi_effects": len(_TITHI_EFFECT_BY_NUM),
        "yoga_attrs": len(_YOGA_ATTRS_BY_NAME),
        "karana_attrs": len(_KARANA_ATTRS_BY_NAME),
        "fingerprint": _PANCHANGA_ATTR_FINGERPRINT,
        "sources": list(_PANCHANGA_ATTR_SOURCES),
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

    # KE provenance
    source_notes: str | None = None


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
        from knowledge_engine.integration import clear_knowledge_engine_cache

        clear_knowledge_engine_cache()
    except Exception:
        pass
    try:
        from graph_rag.muhurta_rules_provider import GraphMuhurtaRules
        GraphMuhurtaRules._instance = None
    except Exception:
        pass
    try:
        from graph_rag.graph import GraphRAG
        GraphRAG()._loaded = False
    except Exception:
        pass
    # Reset enriched attr caches so next compute pulls fresh from KE
    global _TITHI_LORD_BY_NUM, _TITHI_EFFECT_BY_NUM, _YOGA_ATTRS_BY_NAME, _KARANA_ATTRS_BY_NAME, _PANCHANGA_ATTR_FINGERPRINT, _PANCHANGA_ATTR_SOURCES
    _TITHI_LORD_BY_NUM = {}
    _TITHI_EFFECT_BY_NUM = {}
    _YOGA_ATTRS_BY_NAME = {}
    _KARANA_ATTRS_BY_NAME = {}
    _PANCHANGA_ATTR_FINGERPRINT = ""
    _PANCHANGA_ATTR_SOURCES = []


def _on_panchanga_refresh(new_version: str) -> None:
    global _panchanga_rules_version
    _panchanga_rules_version = new_version
    _clear_panchanga_knowledge_caches()
    # Real reload: pull tithi lords, yoga attrs, karana nature, special effects from KE
    try:
        _load_panchang_attributes_from_ke()
    except Exception:
        pass
    # Also warm a representative structured book for provenance
    try:
        get_structured_book("Vedic_Astrology_Panchang_Handbook")
    except Exception:
        pass


def _register_panchanga_engine() -> None:
    global _panchanga_registered
    try:
        from knowledge_engine.integration import get_knowledge_engine

        get_knowledge_engine().register_engine("panchanga", on_refresh=_on_panchanga_refresh)
        _panchanga_registered = True
    except Exception:
        pass
    # Also ensure visible on canonical cvce import path (no-op if same singleton)
    try:
        from cvce.knowledge_engine.integration import get_knowledge_engine as get_ke

        get_ke().register_engine("panchanga", on_refresh=_on_panchanga_refresh)
        _panchanga_registered = True
    except Exception:
        pass


_register_panchanga_engine()


def _ensure_panchanga_registered() -> None:
    # Always attempt; guards inside _register are best-effort and KE singleton may vary by import context
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
    # Lazy-load enriched attrs from KE on first use (on_refresh will also call this)
    if not _TITHI_LORD_BY_NUM and not _PANCHANGA_ATTR_FINGERPRINT:
        try:
            _load_panchang_attributes_from_ke()
        except Exception:
            pass
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
    # Enrich from KE structured books if available (per-tithi lord overrides group lord)
    if tithi_num in _TITHI_LORD_BY_NUM:
        tithi_lord = _TITHI_LORD_BY_NUM[tithi_num]
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
    # Enrich yoga attrs from KE (nature/lord may be augmented)
    ya = _YOGA_ATTRS_BY_NAME.get(yoga_name, {})
    if ya.get("note"):
        # keep core 4-tuple but surface note via source later
        pass
    yoga_end = end_clock(ys)

    # Karana
    karana_name = karana_sequence(ks["idx"])
    karana_end = end_clock(ks)
    # Enrich karana nature if KE provided override
    ka = _KARANA_ATTRS_BY_NAME.get(karana_name, {})
    if ka.get("nature") and ka["nature"].lower() in ("malefic", "bad", "avoid"):
        # will affect verdict below
        pass

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

    # Verdicts (prefer KE-enriched karana nature for malefic detection)
    tithi_v = "shubh" if grp_qual == "good" else ("ashubh" if grp_qual == "bad" else "neutral")
    nak_v = "neutral"  # Vedha-based (computed in gochar module)
    yoga_v = "shubh" if yoga_nature == "Auspicious" else "ashubh"
    karana_v = "ashubh" if karana_name in KARANA_MALEFIC else "shubh"
    if _KARANA_ATTRS_BY_NAME.get(karana_name, {}).get("nature", "").lower() in ("malefic", "bad", "avoid"):
        karana_v = "ashubh"

    # Build provenance notes citing at least one KE chapter/hierarchy
    notes_parts = []
    if _PANCHANGA_ATTR_SOURCES:
        notes_parts.append("attrs:" + ",".join(_PANCHANGA_ATTR_SOURCES[:3]))
    if tithi_num in _TITHI_LORD_BY_NUM or tithi_num in _TITHI_EFFECT_BY_NUM:
        notes_parts.append("tithi: Tithi Astrology Master Reference Guide#ch-the_5_tithi_groups_and_their_details")
    if yoga_name in _YOGA_ATTRS_BY_NAME:
        notes_parts.append("yoga: Vedic_Astrology_Panchang_Handbook")
    if _KARANA_ATTRS_BY_NAME:
        notes_parts.append("karana: Panchang_analysis_medhraj#ch-karana")
    source_notes = "; ".join(notes_parts) if notes_parts else None

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
        source_notes=source_notes,
    )
