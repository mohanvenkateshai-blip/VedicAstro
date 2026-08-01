"""
Personal muhurta factors — Chandrabala, Ghaat Chakra, Pancha Pakshi, Choghadiya.

Ported from panchanga_muhurtha ``MuhurtaCosmos.jsx`` (B-16.7):
  - Chandrabala scoring          ~L2983–2989 / computePersonalFactors ~L1187–1193
    score ledger                 ~L3110  (+5 ok / −12 weak houses 6/8/12)
  - ``GHAAT_CHAKRA`` table       ~L1477–1490
    score hits                   ~L3104  (−8 vaar, −8 nak, −6 tithi-class)
  - ``PANCHA_PAKSHI_BIRD``       ~L739–748  (natal-only display, not scored)
  - ``CHOGHADIYAS`` + ``getChoghadiya()``  ~L1013–1024, ~L2758–2784

Classical sources (cited per factor):
  - *Kalaprakasika* / standard muhurta digests — Chandrabala: Moon's house
    counted from Janma Rashi; 6th, 8th (Chandra-Ashtama), and 12th are
    ashubh for new undertakings (cf. also BPHS gochara house quality for Moon).
  - Regional Ghaat / Ghaata Chakra tables (South-Indian panchanga tradition) —
    fixed inauspicious weekday, nakshatra, and tithi-class keyed to Janma Rashi.
    Exact tabular form matches the JS electional engine (muhurtha.uvwx.me).
  - Tamil Siddha *Pancha Pakshi Shastra* — five birds (Vulture, Owl, Crow,
    Cock, Peacock) assigned by birth nakshatra; full diurnal activity schedule
    is *not* implemented here (natal ruling-bird lookup only, as in the JS UI).
  - Popular Choghadiya (Vedic Muhurta §14 / North-Indian almanac practice) —
    8-named day/night segments starting from a weekday-dependent seed.
    Port preserves the JS simplified 4+4 split (day length ÷ 4, night ÷ 4),
    not the full classical 8+8 ghati table.

Astronomy is intentionally *not* reimplemented. Callers supply Moon rashi /
nakshatra names, weekday, tithi group, sunrise/sunset hours, etc. from the
host engine (Swiss Ephemeris / CVCE panchanga), matching ``muhurta_lagna.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping, Optional, Sequence, Union

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

# Scoring weights from JS runEngine ledger (L3104, L3110)
CHANDRABALA_OK_SCORE: int = 5
CHANDRABALA_WEAK_SCORE: int = -12
CHANDRABALA_WEAK_HOUSES: frozenset[int] = frozenset({6, 8, 12})

GHAAT_VAAR_PENALTY: int = -8
GHAAT_NAK_PENALTY: int = -8
GHAAT_TITHI_PENALTY: int = -6

# Ghaat Chakra: per Janma Rashi →
#   [tithi_class, vaar, nakshatra, lunar_month, lagna_same, lagna_opp]
# JS GHAAT_CHAKRA ~L1477–1490
GHAAT_CHAKRA: dict[str, list[str]] = {
    "Aries": ["Nanda (1,6,11)", "Sunday", "Magha", "Kartik", "Aries", "Libra"],
    "Taurus": [
        "Purna (5,10,15,30)",
        "Saturday",
        "Hasta",
        "Margashirsha",
        "Taurus",
        "Scorpio",
    ],
    "Gemini": ["Bhadra (2,7,12)", "Monday", "Swati", "Ashadha", "Cancer", "Capricorn"],
    "Cancer": ["Bhadra (2,7,12)", "Wednesday", "Anuradha", "Pausha", "Libra", "Aries"],
    "Leo": ["Jaya (3,8,13)", "Saturday", "Mula", "Jyeshtha", "Capricorn", "Cancer"],
    "Virgo": [
        "Purna (5,10,15,30)",
        "Saturday",
        "Shravana",
        "Bhadrapada",
        "Pisces",
        "Virgo",
    ],
    "Libra": ["Rikta (4,9,14)", "Thursday", "Shatabhisha", "Magha", "Virgo", "Pisces"],
    "Scorpio": ["Nanda (1,6,11)", "Friday", "Revati", "Ashwin", "Scorpio", "Taurus"],
    "Sagittarius": [
        "Jaya (3,8,13)",
        "Friday",
        "Bharani",
        "Shravan",
        "Sagittarius",
        "Gemini",
    ],
    "Capricorn": [
        "Rikta (4,9,14)",
        "Tuesday",
        "Rohini",
        "Vaishakha",
        "Aquarius",
        "Leo",
    ],
    "Aquarius": [
        "Jaya (3,8,13)",
        "Thursday",
        "Ardra",
        "Chaitra",
        "Gemini",
        "Sagittarius",
    ],
    "Pisces": [
        "Purna (5,10,15,30)",
        "Friday",
        "Ashlesha",
        "Phalguni",
        "Leo",
        "Aquarius",
    ],
}

# 27-way birth-nakshatra → ruling bird (Tamil Siddha Pancha Pakshi).
# JS PANCHA_PAKSHI_BIRD ~L739–745. Natal display only — not scored.
# Both "Dhanishta" (JS) and "Dhanishtha" (CVCE NAKSHATRAS) are accepted.
PANCHA_PAKSHI_BIRD: dict[str, str] = {
    "Ashwini": "Vulture",
    "Bharani": "Vulture",
    "Krittika": "Vulture",
    "Rohini": "Vulture",
    "Mrigashira": "Vulture",
    "Ardra": "Owl",
    "Punarvasu": "Owl",
    "Pushya": "Owl",
    "Ashlesha": "Owl",
    "Magha": "Owl",
    "Purva Phalguni": "Owl",
    "Uttara Phalguni": "Crow",
    "Hasta": "Crow",
    "Chitra": "Crow",
    "Swati": "Crow",
    "Vishakha": "Crow",
    "Anuradha": "Cock",
    "Jyeshtha": "Cock",
    "Mula": "Cock",
    "Purva Ashadha": "Cock",
    "Uttara Ashadha": "Cock",
    "Shravana": "Peacock",
    "Dhanishta": "Peacock",
    "Dhanishtha": "Peacock",
    "Shatabhisha": "Peacock",
    "Purva Bhadrapada": "Peacock",
    "Uttara Bhadrapada": "Peacock",
    "Revati": "Peacock",
}

# Eight Choghadiya names (JS CHOGHADIYAS ~L1015–1024).
# Verdict/activities are popular-almanac labels, not full classical muhurta.
CHOGHADIYAS: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "Rava",
        "planet": "Sun",
        "verdict": "Shubh",
        "activities": "Travel, buying, learning, auspicious beginnings",
    },
    {
        "id": 2,
        "name": "Aam",
        "planet": "Mars",
        "verdict": "Ashubh",
        "activities": "Avoid new ventures; litigation only",
    },
    {
        "id": 3,
        "name": "Sadhya",
        "planet": "Mercury",
        "verdict": "Shubh",
        "activities": "Writing, trade, education, business",
    },
    {
        "id": 4,
        "name": "Labha",
        "planet": "Jupiter",
        "verdict": "Shubh",
        "activities": "Wealth, marriage, auspicious rites",
    },
    {
        "id": 5,
        "name": "Nisha",
        "planet": "Venus",
        "verdict": "Ashubh",
        "activities": "Avoid new beginnings; repairs only",
    },
    {
        "id": 6,
        "name": "Mritu",
        "planet": "Saturn",
        "verdict": "Ashubh",
        "activities": "Avoid; dangerous/calamitous time",
    },
    {
        "id": 7,
        "name": "Kal",
        "planet": "Rahu",
        "verdict": "Ashubh",
        "activities": "Avoid; inauspicious for all acts",
    },
    {
        "id": 8,
        "name": "Jaya",
        "planet": "Moon",
        "verdict": "Shubh",
        "activities": "All auspicious work, ceremonies",
    },
]

# Weekday → starting CHOGHADIYAS index for the day half (0=Sun … 6=Sat).
# JS: choghadiyaStart = [1, 2, 3, 4, 5, 6, 7, 0]  (values are 0-based indices
# into CHOGHADIYAS; Sunday starts at index 1 = Aam in 0-based… wait:
# comment says "0=Sunday starts with Rava(1)" but array[0]=1 which is
# CHOGHADIYAS[1] = Aam. Port the array literally; do not "fix" the comment.)
_CHOGHADIYA_DAY_START: list[int] = [1, 2, 3, 4, 5, 6, 7, 0]

Number = Union[int, float]


# ---------------------------------------------------------------------------
# Chandrabala
# ---------------------------------------------------------------------------


@dataclass
class ChandrabalaResult:
    """Moon house counted from Janma Rashi (1–12) with electional score.

    Houses 6, 8, and 12 are ashubh (Chandra-Ashtama when 8th). Score matches
    the JS runEngine ledger: +5 acceptable, −12 weak.
    """

    house: int
    ok: bool
    moon_rashi: Optional[str] = None
    janma_rashi: Optional[str] = None
    score: int = 0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "house": self.house,
            "ok": self.ok,
            "moon_rashi": self.moon_rashi,
            "janma_rashi": self.janma_rashi,
            "score": self.score,
            "note": self.note,
            "verdict": "shubh" if self.ok else "ashubh",
        }


def chandrabala(
    janma_rashi: str,
    moon_rashi: str,
) -> Optional[ChandrabalaResult]:
    """Score Chandrabala — Moon's house from the native's Janma Rashi.

    Port of MuhurtaCosmos.jsx ~L2983–2989 / L1187–1193 / L3110.

    Classical rule (Kalaprakasika / standard muhurta): count the house of
    the *transiting* Moon from the natal Moon sign (Janma Rashi). The 6th,
    8th (Chandra-Ashtama), and 12th are weak for fresh undertakings.

    Args:
        janma_rashi: Natal Moon sign name (e.g. ``"Leo"``).
        moon_rashi: Transiting Moon sign name (e.g. ``"Scorpio"``).

    Returns:
        :class:`ChandrabalaResult`, or ``None`` if either rashi is unknown.
    """
    if janma_rashi not in RASHIS or moon_rashi not in RASHIS:
        return None
    j_idx = RASHIS.index(janma_rashi)
    m_idx = RASHIS.index(moon_rashi)
    house = ((m_idx - j_idx + 12) % 12) + 1  # 1..12
    ok = house not in CHANDRABALA_WEAK_HOUSES
    score = CHANDRABALA_OK_SCORE if ok else CHANDRABALA_WEAK_SCORE
    if ok:
        note = f"Moon in {house}th from Janma Rashi — acceptable."
    else:
        note = (
            f"Moon in {house}th from Janma Rashi — weak "
            f"(avoid 6/8/12; Chandra-Ashtama if 8th)."
        )
    return ChandrabalaResult(
        house=house,
        ok=ok,
        moon_rashi=moon_rashi,
        janma_rashi=janma_rashi,
        score=score,
        note=note,
    )


def chandrabala_from_indices(
    janma_rashi_idx: int,
    moon_rashi_idx: int,
) -> Optional[ChandrabalaResult]:
    """Chandrabala from 0-based rashi indices (Aries=0 … Pisces=11)."""
    if not (0 <= janma_rashi_idx < 12 and 0 <= moon_rashi_idx < 12):
        return None
    return chandrabala(RASHIS[janma_rashi_idx], RASHIS[moon_rashi_idx])


# ---------------------------------------------------------------------------
# Ghaat Chakra
# ---------------------------------------------------------------------------


@dataclass
class GhaatResult:
    """Ghaat Chakra row for a Janma Rashi plus live hit flags and score.

    Score deltas (JS L3104): −8 vaar hit, −8 nak hit, −6 tithi-class hit.
    Month / lagna columns are carried for display; they are not scored in JS.
    """

    tithi_class: str
    vaar: str
    nak: str
    month: str
    lagna_same: str
    lagna_opp: str
    vaar_hit: bool = False
    nak_hit: bool = False
    tithi_hit: bool = False
    score: int = 0
    janma_rashi: Optional[str] = None

    @property
    def active(self) -> bool:
        return self.vaar_hit or self.nak_hit or self.tithi_hit

    @property
    def verdict(self) -> str:
        return "ashubh" if self.active else "clear"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tithiClass": self.tithi_class,
            "vaar": self.vaar,
            "nak": self.nak,
            "month": self.month,
            "lagnaSame": self.lagna_same,
            "lagnaOpp": self.lagna_opp,
            "vaarHit": self.vaar_hit,
            "nakHit": self.nak_hit,
            "tithiHit": self.tithi_hit,
            "score": self.score,
            "active": self.active,
            "verdict": self.verdict,
            "janma_rashi": self.janma_rashi,
        }


def _tithi_group_key(tithi_class: str) -> str:
    """Leading word of a Ghaat tithi-class label, e.g. ``'Nanda (1,6,11)'`` → ``'Nanda'``."""
    return tithi_class.split()[0] if tithi_class else ""


def ghaat_chakra(
    janma_rashi: str,
    *,
    weekday: Optional[str] = None,
    moon_nakshatra: Optional[str] = None,
    tithi_group: Optional[str] = None,
) -> Optional[GhaatResult]:
    """Look up Ghaat Chakra for ``janma_rashi`` and optionally flag live hits.

    Port of MuhurtaCosmos.jsx ~L1477–1490 / L3061–3063 / L3104.

    Classical framing: each Janma Rashi has a fixed "ghaat" weekday,
    nakshatra, and tithi-class that is personally inauspicious. When today's
    factors match those cells, apply the electional penalties above.

    Args:
        janma_rashi: Natal Moon sign.
        weekday: Civil/Vedic weekday name (e.g. ``"Sunday"``).
        moon_nakshatra: Transiting Moon nakshatra name.
        tithi_group: Tithi class key — ``Nanda`` / ``Bhadra`` / ``Jaya`` /
            ``Rikta`` / ``Purna`` (same as panchanga ``tithi_group``).

    Returns:
        :class:`GhaatResult`, or ``None`` if ``janma_rashi`` is unknown.
    """
    row = GHAAT_CHAKRA.get(janma_rashi)
    if row is None:
        return None

    tithi_class, vaar, nak, month, lagna_same, lagna_opp = row
    vaar_hit = bool(weekday) and weekday == vaar
    # Allow Dhanishta/Dhanishtha spelling drift on the live nak side only;
    # table cells use the JS spelling ("Magha", "Shravana", …).
    nak_hit = False
    if moon_nakshatra:
        live = moon_nakshatra
        table = nak
        if live == table:
            nak_hit = True
        elif {live, table} <= {"Dhanishta", "Dhanishtha"}:
            nak_hit = True

    tithi_hit = False
    if tithi_group:
        # JS: g[0].includes(groupKey) — substring match on "Nanda (1,6,11)" etc.
        tithi_hit = tithi_group in tithi_class or _tithi_group_key(tithi_class) == tithi_group

    score = 0
    if vaar_hit:
        score += GHAAT_VAAR_PENALTY
    if nak_hit:
        score += GHAAT_NAK_PENALTY
    if tithi_hit:
        score += GHAAT_TITHI_PENALTY

    return GhaatResult(
        tithi_class=tithi_class,
        vaar=vaar,
        nak=nak,
        month=month,
        lagna_same=lagna_same,
        lagna_opp=lagna_opp,
        vaar_hit=vaar_hit,
        nak_hit=nak_hit,
        tithi_hit=tithi_hit,
        score=score,
        janma_rashi=janma_rashi,
    )


# ---------------------------------------------------------------------------
# Pancha Pakshi (natal ruling bird only)
# ---------------------------------------------------------------------------


def pancha_pakshi_ruling_bird(nakshatra_name: Optional[str]) -> Optional[str]:
    """Return the Pancha Pakshi ruling bird for a birth nakshatra.

    Port of ``panchaPakshiRulingBird()`` / ``PANCHA_PAKSHI_BIRD`` (JS ~L739–748).

    Natal-only display factor — **not scored** in the electional ledger.
    Full hour-by-hour bird activity (ruling / eating / walking / sleeping /
    dying) is intentionally omitted pending a primary classical source for
    the diurnal schedule (same caveat as the JS UI copy).

    Source tradition: Tamil Siddha *Pancha Pakshi Shastra*.
    """
    if not nakshatra_name:
        return None
    return PANCHA_PAKSHI_BIRD.get(nakshatra_name)


# ---------------------------------------------------------------------------
# Choghadiya
# ---------------------------------------------------------------------------


@dataclass
class ChoghadiyaResult:
    """Active Choghadiya segment at a query time."""

    id: int
    name: str
    planet: str
    verdict: str
    activities: str
    is_night: bool = False
    index: int = 0  # 0..7 into CHOGHADIYAS

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "planet": self.planet,
            "verdict": self.verdict,
            "activities": self.activities,
            "is_night": self.is_night,
            "index": self.index,
        }


def _weekday_index(date_like: Union[str, date, datetime, int]) -> int:
    """Return 0=Sunday … 6=Saturday (JS ``Date#getDay`` convention)."""
    if isinstance(date_like, int):
        if not 0 <= date_like <= 6:
            raise ValueError(f"weekday index out of range: {date_like}")
        return date_like
    if isinstance(date_like, datetime):
        # Python: Monday=0 … Sunday=6 → convert to JS Sunday=0
        return (date_like.weekday() + 1) % 7
    if isinstance(date_like, date):
        return (date_like.weekday() + 1) % 7
    # 'YYYY-MM-DD'
    d = date.fromisoformat(str(date_like)[:10])
    return (d.weekday() + 1) % 7


def get_choghadiya(
    date_like: Union[str, date, datetime, int],
    time_h: Number,
    sunrise: Number,
    sunset: Number,
) -> Optional[ChoghadiyaResult]:
    """Return the active Choghadiya for a local wall-clock time.

    Port of ``getChoghadiya()`` (JS ~L2758–2784) with tables ~L1013–1024.

    Uses the JS simplified scheme: day span and night span are each split
    into **four** equal parts (not the full classical eight-per-half). Night
    sequence begins four names after the day's starting name.

    Args:
        date_like: ``'YYYY-MM-DD'``, :class:`datetime.date`, or weekday index
            0=Sunday … 6=Saturday.
        time_h: Local decimal hour (0–24), e.g. 14.5 = 14:30.
        sunrise: Local decimal hour of sunrise.
        sunset: Local decimal hour of sunset.

    Returns:
        :class:`ChoghadiyaResult`, or ``None`` if sunrise/sunset missing.
    """
    if sunrise is None or sunset is None:
        return None
    sunrise_f = float(sunrise)
    sunset_f = float(sunset)
    time_f = float(time_h)

    day_dur = sunset_f - sunrise_f
    if day_dur <= 0:
        return None
    night_dur = 24.0 - day_dur

    wd = _weekday_index(date_like)
    day_chog_start = _CHOGHADIYA_DAY_START[wd]

    # Night when before sunrise or at/after sunset (JS isNightWrapped)
    is_night = time_f < sunrise_f or time_f >= sunset_f

    if is_night:
        if time_f >= sunset_f:
            night_time = time_f - sunset_f
        else:
            night_time = (24.0 - sunset_f) + time_f
        chog_per = night_dur / 4.0
        chog_idx = int(night_time // chog_per) if chog_per > 0 else 0
        chog_idx = max(0, min(3, chog_idx))
        chog_num = (day_chog_start + 4 + chog_idx) % 8
    else:
        day_time = time_f - sunrise_f
        chog_per = day_dur / 4.0
        chog_idx = int(day_time // chog_per) if chog_per > 0 else 0
        chog_idx = max(0, min(3, chog_idx))
        chog_num = (day_chog_start + chog_idx) % 8

    row = CHOGHADIYAS[chog_num]
    return ChoghadiyaResult(
        id=int(row["id"]),
        name=str(row["name"]),
        planet=str(row["planet"]),
        verdict=str(row["verdict"]),
        activities=str(row["activities"]),
        is_night=is_night,
        index=chog_num,
    )


def choghadiya_table() -> list[dict[str, Any]]:
    """Return a shallow copy of the eight Choghadiya definitions."""
    return [dict(row) for row in CHOGHADIYAS]


# ---------------------------------------------------------------------------
# Convenience bundle (mirrors JS personal-factor packaging)
# ---------------------------------------------------------------------------


@dataclass
class PersonalFactors:
    """Optional bundle of personal factors for a query moment."""

    chandrabala: Optional[ChandrabalaResult] = None
    ghaat: Optional[GhaatResult] = None
    pancha_pakshi_bird: Optional[str] = None
    choghadiya: Optional[ChoghadiyaResult] = None
    score_delta: int = 0
    ledger: list = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chandrabala": self.chandrabala.to_dict() if self.chandrabala else None,
            "ghaat": self.ghaat.to_dict() if self.ghaat else None,
            "pancha_pakshi_bird": self.pancha_pakshi_bird,
            "choghadiya": self.choghadiya.to_dict() if self.choghadiya else None,
            "score_delta": self.score_delta,
            "ledger": list(self.ledger),
        }


def compute_personal_factors(
    *,
    janma_rashi: Optional[str] = None,
    janma_nakshatra: Optional[str] = None,
    moon_rashi: Optional[str] = None,
    moon_nakshatra: Optional[str] = None,
    weekday: Optional[str] = None,
    tithi_group: Optional[str] = None,
    date_like: Optional[Union[str, date, datetime, int]] = None,
    time_h: Optional[Number] = None,
    sunrise: Optional[Number] = None,
    sunset: Optional[Number] = None,
) -> PersonalFactors:
    """Compute the B-16.7 personal factors that apply to a query.

    Chandrabala and Ghaat contribute to ``score_delta`` (JS ledger weights).
    Pancha Pakshi is display-only. Choghadiya is popularity-tier timing,
    returned when sunrise/sunset and time are supplied; not scored.
    """
    out = PersonalFactors()
    ledger: list[tuple[int, str]] = []

    if janma_rashi and moon_rashi:
        cb = chandrabala(janma_rashi, moon_rashi)
        if cb is not None:
            out.chandrabala = cb
            why = (
                "Chandrabala acceptable"
                if cb.ok
                else "Chandra Ashtama / weak Chandrabala"
            )
            ledger.append((cb.score, why))

    if janma_rashi:
        gh = ghaat_chakra(
            janma_rashi,
            weekday=weekday,
            moon_nakshatra=moon_nakshatra,
            tithi_group=tithi_group,
        )
        if gh is not None:
            out.ghaat = gh
            if gh.vaar_hit:
                ledger.append((GHAAT_VAAR_PENALTY, "Ghaat Vaar match"))
            if gh.nak_hit:
                ledger.append((GHAAT_NAK_PENALTY, "Ghaat Nakshatra match"))
            if gh.tithi_hit:
                ledger.append((GHAAT_TITHI_PENALTY, "Ghaat Tithi-class match"))

    out.pancha_pakshi_bird = pancha_pakshi_ruling_bird(janma_nakshatra)

    if (
        date_like is not None
        and time_h is not None
        and sunrise is not None
        and sunset is not None
    ):
        out.choghadiya = get_choghadiya(date_like, time_h, sunrise, sunset)

    out.ledger = ledger
    out.score_delta = sum(p for p, _ in ledger)
    return out
