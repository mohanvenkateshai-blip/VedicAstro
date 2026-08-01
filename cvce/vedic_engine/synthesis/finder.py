"""
Muhurta Finder — day-range search and ranking.

Port of ``findMuhurta()`` / ``contextualNatalBonusFor()`` from
panchanga_muhurtha ``MuhurtaCosmos.jsx`` (~L3729–4275), B-16.5.

Core structure (this module):
  * Loop each civil day in ``[from_date, to_date]``
  * Score activity-profile factors (nak / weekday / tithi / karana)
  * Personal factors: Tara Balam, Chandrabala, Janma-nak rules
  * Sade Sati / Kantaka / Ashtama Shani with Kaksha grade when natal_sign given
  * Eclipse hard-cap (Grahan — universal)
  * Gochar Table-12 house quality from Janma Rashi
  * Dasha bonus from optional ``predict_ctx``
  * Best-window candidates via Muhurta Lagna (+ Pushkarabhaga / Gandanta)
  * Natal-structure contextual bonus via ACTIVITY_KARAKA
  * Ranked day list (score desc)

Not every one of the ~26 JS factors is ported yet (Vedha matrix, full 30-slot
ghati table, Moorti fine-print, yoga-activation ledger, etc.). The frame,
caps, blend rules, and the highest-weight factors match the JS finder so
later factors can drop in without reshaping the API.

Classical sources (same as JS methodology docs):
  - Gochar Phaladeepika Table 12 / Ch.26 (Sade Sati, Kantaka, Ashtama)
  - BPHS Gandanta / Muhurta Darpana Pushkarabhaga (via muhurta_lagna)
  - Activity nak/weekday/karana tables from ACTIVITY_PROFILES
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Mapping, Optional, Sequence, Union

from ..core.astronomy import (
    all_positions,
    ascendant,
    julian_day_ut,
    lahiri_ayanamsha,
)
from ..core.panchanga import RASHIS, compute_panchanga
from ..prediction.activity_profiles import (
    ACTIVITY_KARAKA,
    ACTIVITY_PROFILES,
    get_activity_profile,
)
from ..prediction.gochar import compute_gochar
from ..prediction.muhurta_lagna import (
    apply_muhurta_lagna_to_finder,
    evaluate_muhurta_lagna,
)
from ..prediction.muhurta_yogas import evaluate_muhurta_yogas
from ..prediction.natal_structure import (
    compute_natal_structure,
    contextual_natal_bonus_for,
)
from ..rules.transit_rules import TRANSIT_HOUSES

Number = Union[int, float]

# ---------------------------------------------------------------------------
# Constants matching MuhurtaCosmos.jsx findMuhurta
# ---------------------------------------------------------------------------

# Base day score before activity/personal bonuses (JS runEngine starts at 50).
BASE_DAY_SCORE: int = 50

# Eclipse — hard disqualification (JS ~L4100)
ECLIPSE_PENALTY: int = -30
ECLIPSE_CAP: int = 8

# Activity profile weights
NAK_FAVOURED_BONUS: int = 14
NAK_AVOID_PENALTY: int = -16
NAK_AVOID_CAP: int = 42
WEEKDAY_BONUS: int = 8
TITHI_AVOID_PENALTY: int = -10
TITHI_AVOID_CAP: int = 68
KARANA_BONUS: int = 8
SIDDHI_YOGA_BONUS: int = 8

# Tara / Chandrabala
TARA_SHUBH_BONUS: int = 10
TARA_ASHUBH_PENALTY: int = -14
TARA_ASHUBH_CAP: int = 55
TARA_EXCEPTION_PENALTY: int = -8
CHANDRABALA_WEAK_PENALTY: int = -10
CHANDRABALA_WEAK_CAP: int = 60

# Janma nak rules
JANMA_NAK_AVOID_PENALTY: int = -14
JANMA_NAK_AVOID_CAP: int = 50
JANMA_NAK_ALLOW_BONUS: int = 12

# Sade Sati / Kantaka / Ashtama phase table (JS PHASE_INFO)
# house → (key, penalty, cap)
SADE_SATI_PHASE_INFO: dict[int, dict[str, Any]] = {
    1: {"key": "peak", "penalty": -14, "cap": 45},
    2: {"key": "setting", "penalty": -8, "cap": 58},
    12: {"key": "rise", "penalty": -8, "cap": 58},
    4: {"key": "kantaka", "penalty": -6, "cap": 60},
    7: {"key": "kantaka", "penalty": -6, "cap": 60},
    10: {"key": "kantaka", "penalty": -6, "cap": 60},
    8: {"key": "ashtama", "penalty": -8, "cap": 55},
}

SADE_SATI_REASON: dict[str, str] = {
    "peak": "Sade Sati peak: Saturn in Janma Rashi",
    "setting": "Sade Sati setting: Saturn in 2nd from Janma Rashi",
    "rise": "Sade Sati rising: Saturn in 12th from Janma Rashi",
    "kantaka": "Kantaka Shani: Saturn from Janma Rashi",
    "ashtama": "Ashtama Shani: Saturn in 8th from Janma Rashi",
}

SADE_SATI_KAKSHA_REASON: dict[str, str] = {
    "peak": (
        "Sade Sati peak, but Saturn's current Kaksha still gives a bindu "
        "here (favourable window)"
    ),
    "setting": (
        "Sade Sati setting, but Saturn's current Kaksha still gives a bindu "
        "here (favourable window)"
    ),
    "rise": (
        "Sade Sati rising, but Saturn's current Kaksha still gives a bindu "
        "here (favourable window)"
    ),
    "kantaka": (
        "Kantaka Shani, but Saturn's current Kaksha still gives a bindu "
        "here (favourable window)"
    ),
    "ashtama": (
        "Ashtama Shani, but Saturn's current Kaksha still gives a bindu "
        "here (favourable window)"
    ),
}

# Ashtakavarga Moon SAV bands (JS factor #10)
AKV_EXCELLENT: int = 32
AKV_GOOD: int = 28
AKV_WEAK: int = 22
AKV_EXCELLENT_BONUS: int = 10
AKV_GOOD_BONUS: int = 6
AKV_WEAK_PENALTY: int = -8
AKV_WEAK_CAP: int = 62

# Mercury retro
MERCURY_RETRO_PENALTY: int = -8
MERCURY_RETRO_CAP: int = 60

# Time-filter empty windows
NO_WINDOWS_PENALTY: int = -20
NO_WINDOWS_CAP: int = 20

# Dasha bonuses (JS predictCtx block)
DASHA_MAHA: dict[str, int] = {
    "Jupiter": 8,
    "Venus": 7,
    "Moon": 5,
    "Mercury": 4,
    "Sun": 2,
    "Mars": -4,
    "Saturn": -6,
    "Rahu": -7,
    "Ketu": -5,
}
DASHA_ANTAR: dict[str, int] = {
    "Jupiter": 5,
    "Venus": 4,
    "Moon": 3,
    "Mercury": 3,
    "Sun": 1,
    "Mars": -3,
    "Saturn": -4,
    "Rahu": -5,
    "Ketu": -3,
}

# Gochar raw → bonus normalisation (JS): raw [-90,+45] → [-30,+30]
GOCHAR_NORM_CAP: int = 58  # when gocharNorm < -20

# Kartari on Lagna (always-on natal)
KARTARI_SHUBH_BONUS: int = 6
KARTARI_PAAP_PENALTY: int = -6
VARGOTTAMA_LAGNA_BONUS: int = 5

# Blend weights (JS)
ACTIVITY_BLEND_WEIGHT: float = 0.7
PREDICT_BLEND_WEIGHT: float = 0.3

# Candidate window sample hours (local) when full 30-slot table is absent.
# Covers Brahma, mid-morning, Abhijit-ish noon, afternoon, evening, night.
DEFAULT_WINDOW_HOURS: tuple[float, ...] = (5.5, 9.0, 12.0, 15.0, 18.0, 21.0)

MAX_RANGE_DAYS: int = 400

PersonLike = Mapping[str, Any]
TimeFilter = Optional[Mapping[str, Any]]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _parse_date(value: Union[str, date, datetime]) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _date_str(d: date) -> str:
    return d.isoformat()


def _tithi_tip(tithi_num: int) -> int:
    if tithi_num == 30:
        return 15
    return ((tithi_num - 1) % 15) + 1


def _rashi_idx(name: Optional[str]) -> int:
    if not name:
        return -1
    try:
        return RASHIS.index(name)
    except ValueError:
        return -1


def _house_from(planet_sign_idx: int, ref_idx: int) -> int:
    return ((planet_sign_idx - ref_idx + 12) % 12) + 1


def _clamp(n: Number, lo: int = 0, hi: int = 100) -> int:
    return int(max(lo, min(hi, round(n))))


def _hms_label(start_h: float, end_h: float) -> str:
    def fmt(h: float) -> str:
        hh = int(h) % 24
        mm = int(round((h - int(h)) * 60)) % 60
        return f"{hh:02d}:{mm:02d}"

    return f"{fmt(start_h)}–{fmt(end_h)}"


def _person_get(person: Optional[PersonLike], *keys: str, default: Any = None) -> Any:
    if not person:
        return default
    for k in keys:
        if k in person and person[k] is not None:
            return person[k]
    return default


def contextual_natal_bonus_for_activity(
    activity_key: Optional[str], planet_natal: Mapping[str, float]
) -> dict[str, Any]:
    """Thin re-export matching JS ``contextualNatalBonusFor`` name."""
    return contextual_natal_bonus_for(activity_key, planet_natal)


# ---------------------------------------------------------------------------
# Sade Sati / Kaksha / Ashtama scoring
# ---------------------------------------------------------------------------


def _saturn_phase_from_house(house: int) -> Optional[dict[str, Any]]:
    return SADE_SATI_PHASE_INFO.get(house)


def score_sade_sati(
    *,
    janma_rashi: Optional[str],
    transit_rows: Sequence[Mapping[str, Any]],
    natal_sign: Optional[Mapping[str, Any]] = None,
    grade: Optional[str] = None,
    subcase: Optional[str] = None,
) -> dict[str, Any]:
    """Score Sade Sati / Kantaka / Ashtama with optional Kaksha grade.

    Port of JS findMuhurta factor #9.

    When ``grade``/``subcase`` are not supplied:
      * default grade is ``frictional`` (full penalty) — safe without BAV
      * if caller later ports ``kakshaGivesBindu`` + ``kakshaBavGrade``, pass
        the resulting grade/subcase here

    Returns ``{bonus, cap, reasons, sade_sati}`` where ``cap`` is None if
    uncapped by this factor and ``sade_sati`` is the phase dict or None.
    """
    reasons: list[str] = []
    bonus = 0
    cap: Optional[int] = None
    detail: Optional[dict[str, Any]] = None

    j_idx = _rashi_idx(janma_rashi)
    if j_idx < 0:
        return {"bonus": 0, "cap": None, "reasons": reasons, "sade_sati": None}

    sat = next((t for t in transit_rows if t.get("planet") == "Saturn"), None)
    if not sat:
        return {"bonus": 0, "cap": None, "reasons": reasons, "sade_sati": None}

    sat_rashi = sat.get("rashi")
    sat_idx = _rashi_idx(sat_rashi)
    if sat_idx < 0:
        # fall back to lon if present
        lon = sat.get("lon")
        if lon is None:
            return {"bonus": 0, "cap": None, "reasons": reasons, "sade_sati": None}
        sat_idx = int(lon // 30) % 12

    house = _house_from(sat_idx, j_idx)
    info = _saturn_phase_from_house(house)
    if not info:
        return {"bonus": 0, "cap": None, "reasons": reasons, "sade_sati": None}

    key = info["key"]
    penalty = int(info["penalty"])
    phase_cap = int(info["cap"])

    # Grade resolution: explicit > frictional default
    g = grade or "frictional"
    sc = subcase

    # Optional future hook: if natal_sign provided and grade not forced,
    # leave as frictional — full Kaksha BAV needs BAV_TABLE (not yet in
    # ashtakavarga.py after the jhora migration). Structure is ready.
    _ = natal_sign  # reserved for kaksha bindu lookup

    if g == "constructive":
        bonus += 6
        reasons.append(SADE_SATI_KAKSHA_REASON[key])
    elif g == "frictional":
        bonus += penalty
        cap = phase_cap
        reason = SADE_SATI_REASON[key]
        if key == "kantaka":
            reason = f"Kantaka Shani: Saturn in {house}th from Janma Rashi"
        reasons.append(reason)
    elif sc in ("protectedMicroWindow", "bavMixedActive"):
        bonus += 3
        base = SADE_SATI_REASON[key]
        if key == "kantaka":
            base = f"Kantaka Shani: Saturn in {house}th from Janma Rashi"
        reasons.append(
            f"{base} — a protected micro-window (mild relief; Saturn's "
            "sign-strength is weak/mixed here)"
        )
    else:
        # mixed supportedFriction / bavMixedInactive
        bonus += round(penalty / 2)
        cap = round((phase_cap + 100) / 2)
        base = SADE_SATI_REASON[key]
        if key == "kantaka":
            base = f"Kantaka Shani: Saturn in {house}th from Janma Rashi"
        reasons.append(
            f"{base} — temporary friction, but the sign itself is well-supported"
        )

    detail = {
        "house": house,
        "phase": key,
        "grade": g,
        "subcase": sc,
        "penalty": penalty,
        "cap": phase_cap,
    }
    return {"bonus": bonus, "cap": cap, "reasons": reasons, "sade_sati": detail}


def score_sade_sati_from_gochar(gochar: Any) -> dict[str, Any]:
    """Apply Sade Sati scoring using a ``GocharResult`` (no Kaksha grade).

    Maps gochar.sade_sati / kantaka_shani / ashtama_shani onto the same
    PHASE_INFO table used by ``score_sade_sati``.
    """
    reasons: list[str] = []
    bonus = 0
    cap: Optional[int] = None
    detail: Optional[dict[str, Any]] = None

    house: Optional[int] = None
    if getattr(gochar, "sade_sati", None):
        phase = gochar.sade_sati.get("phase")
        house = {"peak": 1, "rise": 12, "setting": 2}.get(phase)
    elif getattr(gochar, "ashtama_shani", None):
        house = int(gochar.ashtama_shani.get("house") or 8)
    elif getattr(gochar, "kantaka_shani", None):
        house = int(gochar.kantaka_shani.get("house") or 0) or None

    if house is None:
        return {"bonus": 0, "cap": None, "reasons": reasons, "sade_sati": None}

    info = _saturn_phase_from_house(house)
    if not info:
        return {"bonus": 0, "cap": None, "reasons": reasons, "sade_sati": None}

    # Build a minimal transit row so score_sade_sati can run — but we already
    # know the house, so apply frictional grade directly.
    key = info["key"]
    penalty = int(info["penalty"])
    phase_cap = int(info["cap"])
    bonus += penalty
    cap = phase_cap
    reason = SADE_SATI_REASON[key]
    if key == "kantaka":
        reason = f"Kantaka Shani: Saturn in {house}th from Janma Rashi"
    reasons.append(reason)
    detail = {
        "house": house,
        "phase": key,
        "grade": "frictional",
        "subcase": None,
        "penalty": penalty,
        "cap": phase_cap,
    }
    return {"bonus": bonus, "cap": cap, "reasons": reasons, "sade_sati": detail}


# ---------------------------------------------------------------------------
# Gochar Table-12 day bonus
# ---------------------------------------------------------------------------


def score_gochar_table12(
    transit_rows: Sequence[Mapping[str, Any]], janma_rashi: Optional[str]
) -> dict[str, Any]:
    """Gochar Phaladeepika Table 12 house-quality bonus.

    Port of JS findMuhurta gochar block: raw ±5/±10 per planet, then
    normalised from [-90,+45] → [-30,+30].
    """
    reasons: list[str] = []
    j_idx = _rashi_idx(janma_rashi)
    if j_idx < 0:
        return {
            "bonus": 0,
            "cap": None,
            "gochar_score": 0,
            "gochar_good": [],
            "gochar_bad": [],
            "reasons": reasons,
        }

    gochar_score = 0
    gochar_good: list[str] = []
    gochar_bad: list[str] = []

    for t in transit_rows:
        planet = t.get("planet")
        rules = TRANSIT_HOUSES.get(planet or "")
        if not rules:
            continue
        r_idx = _rashi_idx(t.get("rashi"))
        if r_idx < 0:
            lon = t.get("lon")
            if lon is None:
                continue
            r_idx = int(lon // 30) % 12
        h = _house_from(r_idx, j_idx)
        if h in rules.get("good", []):
            gochar_score += 5
            gochar_good.append(planet)
        elif h in rules.get("worst", []):
            gochar_score -= 10
            gochar_bad.append(f"{planet}(w)")
        elif h in rules.get("bad", []):
            gochar_score -= 5
            gochar_bad.append(planet)

    if gochar_good:
        reasons.append(f"Gochar fav: {', '.join(gochar_good)}")
    if gochar_bad:
        reasons.append(f"Gochar unfav: {', '.join(gochar_bad)}")

    # Normalize raw [-90,+45] → [-30,+30]
    gochar_norm = round((gochar_score + 90) / 135 * 60 - 30)
    cap: Optional[int] = GOCHAR_NORM_CAP if gochar_norm < -20 else None

    return {
        "bonus": gochar_norm,
        "cap": cap,
        "gochar_score": gochar_score,
        "gochar_good": gochar_good,
        "gochar_bad": gochar_bad,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Muhurta Lagna at a local hour
# ---------------------------------------------------------------------------


def muhurta_lagna_at(
    date_str: str,
    hour_local: float,
    tz: float,
    lat: float,
    lon: float,
) -> dict[str, Any]:
    """Evaluate Muhurta Lagna at a local wall-clock hour.

    Builds sidereal longitudes via ``core.astronomy`` then scores with
    ``evaluate_muhurta_lagna`` (ported JS ``muhurtaLagna``).
    """
    y, mo, d = (int(x) for x in date_str.split("-"))
    hour_ut = float(hour_local) - float(tz)
    jd = julian_day_ut(y, mo, d, hour_ut)
    ayan = lahiri_ayanamsha(jd)
    asc = ascendant(jd, lat, lon, ayan)
    pos = all_positions(jd)
    return evaluate_muhurta_lagna(asc_lon=asc, planet_lons=pos)


def _candidate_windows(
    date_str: str,
    tz: float,
    lat: float,
    lon: float,
    *,
    sunrise: Optional[float] = None,
    sunset: Optional[float] = None,
    from_time_h: Optional[float] = None,
    to_time_h: Optional[float] = None,
    weekday: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Build a short list of candidate windows with Muhurta Lagna scores.

    Full 30-slot (2-ghati) table is not yet ported. We sample a handful of
    classically meaningful local hours, optionally filtered by the user's
    time range (including overnight ranges where from > to).
    """
    hours = list(DEFAULT_WINDOW_HOURS)
    # Prefer true noon / Brahma when sunrise known
    if sunrise is not None and sunset is not None:
        dinamana = (sunset - sunrise) % 24
        if dinamana <= 0:
            dinamana = 12.0
        abhijit = sunrise + dinamana / 2.0
        brahma = (sunrise - 1.5) % 24
        hours = sorted({round(h, 4) for h in (brahma, 9.0, abhijit, 15.0, sunset - 0.5, 21.0)})

    has_filter = from_time_h is not None and to_time_h is not None
    overnight = bool(has_filter and from_time_h > to_time_h)  # type: ignore[operator]

    # Overnight searches need post-midnight / late-night samples; the daytime
    # defaults alone can never satisfy from>to ranges like 22:00–04:00.
    if overnight:
        night_hours = [22.5, 23.5, 0.5, 1.5, 2.5, 3.5]
        if sunrise is not None:
            night_hours.append(round((sunrise - 1.5) % 24, 4))  # Brahma
        hours = sorted({round(h, 4) for h in list(hours) + night_hours})

    def _in_range(h: float) -> bool:
        if not has_filter:
            return True
        assert from_time_h is not None and to_time_h is not None
        if overnight:
            # Night-side of midnight: h >= from OR h <= to
            return h >= from_time_h or h <= to_time_h
        return from_time_h <= h <= to_time_h

    windows: list[dict[str, Any]] = []
    for h in hours:
        if not _in_range(h):
            continue
        # 48-minute (2-ghati) nominal window centred on h
        start = (h - 0.4) % 24
        end = (h + 0.4) % 24
        # For same-day display keep unwrapped if possible
        if end < start and not overnight:
            # straddles midnight — keep as-is
            pass
        try:
            ml = muhurta_lagna_at(date_str, h, tz, lat, lon)
        except Exception:
            continue
        # Light slot weight analogous to step11 special bonuses
        w = ml.get("score", 50) or 50
        if sunrise is not None and sunset is not None:
            noon = sunrise + ((sunset - sunrise) % 24) / 2.0
            if abs(h - noon) < 0.6:
                w += 8  # Abhijit-ish
                if weekday == "Wednesday":
                    w -= 6
            if abs(h - ((sunrise - 1.5) % 24)) < 0.6:
                w += 6  # Brahma
        windows.append(
            {
                "label": _hms_label(start if start <= end or overnight else h - 0.4, end if start <= end or overnight else h + 0.4),
                "startH": float(h - 0.4),
                "endH": float(h + 0.4),
                "midH": float(h),
                "lagna": ml.get("ascSign"),
                "lagnaVerdict": ml.get("verdict"),
                "lagnaScore": ml.get("score"),
                "isPushkarabhaga": ml.get("isPushkarabhaga"),
                "isGandanta": ml.get("isGandanta"),
                "ml": ml,
                "w": w,
                "nature": "—",
                "status": ml.get("verdict", "neutral"),
                "deity": "—",
                "nak": "—",
                "seq": len(windows) + 1,
            }
        )

    windows.sort(key=lambda s: s.get("w", 0), reverse=True)
    return windows[:3]


# ---------------------------------------------------------------------------
# Single-day score
# ---------------------------------------------------------------------------


@dataclass
class DayScore:
    """One ranked finder day — shape mirrors JS ``out.push({...})``."""

    date: str
    weekday: str
    score: int
    base_verdict: str
    tithi: str
    tithi_short: str
    group: str
    nak: str
    yoga: str
    karana: str
    tara: str = "—"
    tara_verdict: str = "neutral"
    eclipse: Optional[dict] = None
    lagna: str = "—"
    lagna_verdict: str = "neutral"
    lagna_score: Optional[int] = None
    windows: list = field(default_factory=list)
    no_windows_in_range: bool = False
    best_window: str = "—"
    predict_score: Optional[int] = None
    predict_label: str = ""
    gochar_good: list = field(default_factory=list)
    gochar_bad: list = field(default_factory=list)
    reasons: list = field(default_factory=list)
    sade_sati: Optional[dict] = None
    activity_score: int = 0
    bonus: int = 0
    cap: int = 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "weekday": self.weekday,
            "score": self.score,
            "baseVerdict": self.base_verdict,
            "tithi": self.tithi,
            "tithiShort": self.tithi_short,
            "group": self.group,
            "nak": self.nak,
            "yoga": self.yoga,
            "karana": self.karana,
            "tara": self.tara,
            "taraVerdict": self.tara_verdict,
            "eclipse": self.eclipse,
            "lagna": self.lagna,
            "lagnaVerdict": self.lagna_verdict,
            "lagnaScore": self.lagna_score,
            "windows": [
                {k: v for k, v in w.items() if k not in ("ml", "w")}
                for w in self.windows
            ],
            "noWindowsInRange": self.no_windows_in_range,
            "bestWindow": self.best_window,
            "predictScore": self.predict_score,
            "predictLabel": self.predict_label,
            "gocharGood": self.gochar_good,
            "gocharBad": self.gochar_bad,
            "reasons": list(self.reasons),
            "sadeSati": self.sade_sati,
            "activityScore": self.activity_score,
            "bonus": self.bonus,
            "cap": self.cap,
        }


def score_day(
    date_str: str,
    *,
    lat: float,
    lon: float,
    tz: float,
    activity_id: str,
    person: Optional[PersonLike] = None,
    time_filter: TimeFilter = None,
    predict_ctx: Optional[Mapping[str, Any]] = None,
    natal_structure: Optional[Mapping[str, Any]] = None,
    contextual_natal: Optional[Mapping[str, Any]] = None,
) -> DayScore:
    """Score a single civil day for the given activity.

    Uses panchanga + gochar + activity profile + (optional) natal context.
    """
    person = person or {}
    janma_rashi = _person_get(person, "janma_rashi", "janmaRashi")
    janma_nak = _person_get(person, "janma_nakshatra", "janmaNak", "janma_nak")
    lagna_nak = _person_get(person, "lagna_nakshatra", "lagnaNak", "lagna_nak")
    natal_sign = _person_get(person, "natal_sign", "natalSign")
    ashtakavarga = _person_get(person, "ashtakavarga", "akv")
    lagna_rashi = _person_get(person, "lagna_rashi", "lagnaRashi", "lagna_sign")

    prof = get_activity_profile(activity_id) or next(iter(ACTIVITY_PROFILES.values()))
    # Accept short aliases: last path segment match
    if activity_id and activity_id not in ACTIVITY_PROFILES:
        for k, v in ACTIVITY_PROFILES.items():
            if k.endswith(activity_id) or v.get("id") == activity_id:
                prof = v
                break

    panch = compute_panchanga(date_str, "12:00", lat, lon, tz)
    gochar = compute_gochar(
        date_str,
        "12:00",
        lat,
        lon,
        tz,
        janma_rashi=janma_rashi,
        janma_nakshatra=janma_nak,
        natal_sign=natal_sign,
        lagna_rashi=lagna_rashi,
        transit_rows=panch.transit,
    )

    bonus = 0
    reasons: list[str] = []
    cap = 100
    tip = _tithi_tip(panch.tithi_num)
    moon_nak = panch.nakshatra
    weekday = panch.weekday

    # --- Natal structure (once per chart; reasons scoped to karaka) -------
    if natal_structure is None and (
        _person_get(person, "planets") is not None
        or _person_get(person, "vargas") is not None
    ):
        planets = _person_get(person, "planets") or []
        vargas = _person_get(person, "vargas")
        birth_jd = _person_get(person, "birth_jd", "birthJD")
        lagna_idx = None
        if natal_sign and "Lagna" in natal_sign:
            lagna_idx = natal_sign["Lagna"]
        elif vargas and isinstance(vargas.get("D1"), dict):
            lagna_idx = vargas["D1"].get("Lagna")
        natal_structure = compute_natal_structure(
            planets, lagna_idx, birth_jd, vargas=vargas
        )

    if natal_structure:
        if contextual_natal is None:
            contextual_natal = contextual_natal_bonus_for(
                prof.get("id") or activity_id,
                natal_structure.get("planetNatal") or {},
            )
        relevant = set(contextual_natal.get("relevantPlanets") or [])

        vargottama = list(natal_structure.get("vargottamaPlanets") or [])
        if "Lagna" in vargottama:
            bonus += VARGOTTAMA_LAGNA_BONUS
            reasons.append(
                "Lagna Vargottama (D1=D9, natal strength comparable to exaltation)"
            )
        rel_v = [p for p in vargottama if p != "Lagna" and p in relevant]
        if rel_v:
            reasons.append(
                f"{', '.join(rel_v)} Vargottama (D1=D9, natal strength "
                "comparable to exaltation)"
            )
        for d in natal_structure.get("baladiDetail") or []:
            if d.get("planet") in relevant:
                reasons.append(
                    f"Natal Baladi Avastha: {d['planet']} {d['state']} (BPHS age-state)"
                )
                break
        for d in natal_structure.get("deeptadiDetail") or []:
            if d.get("planet") in relevant:
                reasons.append(
                    f"Natal Deeptadi Avastha: {d['planet']} {d['state']} "
                    f"({d.get('jagradadi', '')}) (Phaladeepika dignity-state)"
                )
                break
        rel_c = [p for p in (natal_structure.get("combustDetail") or []) if p in relevant]
        if rel_c:
            reasons.append(f"Natal {', '.join(rel_c)} combust (BPHS orb table)")
        rel_y = [
            pair
            for pair in (natal_structure.get("yuddhaDetail") or [])
            if pair and (pair[0] in relevant or pair[1] in relevant)
        ]
        if rel_y:
            reasons.append(
                "Natal Graha Yuddha: "
                + ", ".join(f"{a}-{b}" for a, b in rel_y)
                + " (BPHS, 1° orb)"
            )
        rel_m = [p for p in (natal_structure.get("maranaDetail") or []) if p in relevant]
        if rel_m:
            reasons.append(
                f"Natal {', '.join(rel_m)} in own Marana Karaka Sthana "
                "(common later natal-table convention)"
            )
        rel_g = [
            d
            for d in (natal_structure.get("gatiDetail") or [])
            if d.get("planet") in relevant and d.get("state") != "Sama"
        ]
        if rel_g:
            reasons.append(
                "Natal motion state: "
                + ", ".join(f"{d['planet']} {d['state']}" for d in rel_g)
                + " (BPHS Cheshta, simplified)"
            )
        kartari = natal_structure.get("kartariLagna")
        if kartari == "shubh":
            bonus += KARTARI_SHUBH_BONUS
            reasons.append("Lagna hemmed by benefics (Shubh Kartari Yoga)")
        elif kartari == "paap":
            bonus += KARTARI_PAAP_PENALTY
            reasons.append("Lagna hemmed by malefics (Paap Kartari Yoga)")

        ctx_bonus = int(contextual_natal.get("bonus") or 0)
        if ctx_bonus:
            bonus += ctx_bonus
            if contextual_natal.get("capped"):
                sign = "+" if ctx_bonus > 0 else ""
                reasons.append(
                    f"(combined natal-structure factors for this activity's "
                    f"Kāraka capped at {sign}{ctx_bonus} to keep day-to-day "
                    "ranking meaningful)"
                )

    # --- 1–5 Activity profile --------------------------------------------
    if prof.get("nakshatras") and moon_nak in prof["nakshatras"]:
        bonus += NAK_FAVOURED_BONUS
        reasons.append(f"{moon_nak} is a prescribed star")
    if prof.get("avoidNak") and moon_nak in prof["avoidNak"]:
        bonus += NAK_AVOID_PENALTY
        cap = min(cap, NAK_AVOID_CAP)
        reasons.append(f"{moon_nak} is contraindicated for this activity")
    if prof.get("weekdays") and weekday in prof["weekdays"]:
        bonus += WEEKDAY_BONUS
        reasons.append(f"{weekday} weekday fits")
    if prof.get("tithisAvoid") and tip in prof["tithisAvoid"]:
        bonus += TITHI_AVOID_PENALTY
        cap = min(cap, TITHI_AVOID_CAP)
        reasons.append(f"tithi {tip} is to be avoided")
    if prof.get("karanas") and panch.karana_name in prof["karanas"]:
        bonus += KARANA_BONUS
        reasons.append(f"{panch.karana_name} karana fits")

    # --- 6 Benefic yogas (Siddhi / Amrita via muhurta_yogas) --------------
    try:
        my = evaluate_muhurta_yogas(weekday, panch.tithi_num, moon_nak)
        names = " ".join(h.name for h in (my.active or [])).lower()
        if "siddhi" in names or "amrita" in names or "sarvartha" in names:
            bonus += SIDDHI_YOGA_BONUS
            reasons.append("Siddhi yoga")
    except Exception:
        pass

    # --- 7 Tara Balam + Chandrabala --------------------------------------
    tara_name = "—"
    tara_verdict = "neutral"
    if gochar.tara_balam:
        tara_name = gochar.tara_balam.get("name") or "—"
        tara_verdict = gochar.tara_balam.get("verdict") or "neutral"
        if tara_verdict == "shubh":
            bonus += TARA_SHUBH_BONUS
            reasons.append(f"Tara {tara_name}")
        elif tara_verdict == "ashubh":
            bonus += TARA_ASHUBH_PENALTY
            cap = min(cap, TARA_ASHUBH_CAP)
            reasons.append(f"Tara {tara_name} (unfavourable)")
        excs = gochar.tara_balam.get("exceptions") or []
        if excs:
            bonus += TARA_EXCEPTION_PENALTY
            reasons.append("Tara exception applies")

    if gochar.chandrabala and not gochar.chandrabala.get("ok", True):
        bonus += CHANDRABALA_WEAK_PENALTY
        cap = min(cap, CHANDRABALA_WEAK_CAP)
        reasons.append("Chandra Ashtama / weak Chandrabala")

    # --- 8 Janma Nakshatra avoid / allow ---------------------------------
    if prof.get("avoidJanmaNak") and janma_nak and moon_nak == janma_nak:
        bonus += JANMA_NAK_AVOID_PENALTY
        cap = min(cap, JANMA_NAK_AVOID_CAP)
        reasons.append(
            f"Today's Moon is your Janma Nakshatra ({janma_nak}) — "
            "avoid for this activity"
        )
    if prof.get("allowJanmaNak") and janma_nak and moon_nak == janma_nak:
        bonus += JANMA_NAK_ALLOW_BONUS
        reasons.append(
            f"Janma Nakshatra ({janma_nak}) is auspicious for this activity"
        )

    # --- 9 Sade Sati / Kantaka / Ashtama (+ Kaksha grade hook) -----------
    ss = score_sade_sati(
        janma_rashi=janma_rashi,
        transit_rows=panch.transit or [],
        natal_sign=natal_sign,
        grade=_person_get(person, "sade_sati_grade", "sadeSatiGrade"),
        subcase=_person_get(person, "sade_sati_subcase", "sadeSatiSubcase"),
    )
    # If person didn't force a grade, fall back to gochar phase detection
    # only when score_sade_sati found nothing (shouldn't happen) — otherwise
    # keep frictional default. When gochar has phase but transit parse failed,
    # use gochar helper.
    if ss["sade_sati"] is None and (
        gochar.sade_sati or gochar.kantaka_shani or gochar.ashtama_shani
    ):
        ss = score_sade_sati_from_gochar(gochar)
    bonus += ss["bonus"]
    if ss["cap"] is not None:
        cap = min(cap, ss["cap"])
    reasons.extend(ss["reasons"])

    # --- 10 Ashtakavarga Moon SAV ----------------------------------------
    sav = None
    if ashtakavarga:
        sav = ashtakavarga.get("sav") if isinstance(ashtakavarga, dict) else None
        if sav is None and hasattr(ashtakavarga, "sav"):
            sav = ashtakavarga.sav
    if sav:
        moon_row = next((t for t in (panch.transit or []) if t.get("planet") == "Moon"), None)
        if moon_row:
            m_idx = _rashi_idx(moon_row.get("rashi"))
            if 0 <= m_idx < len(sav):
                b = int(sav[m_idx])
                if b >= AKV_EXCELLENT:
                    bonus += AKV_EXCELLENT_BONUS
                    reasons.append(f"Moon in {b}-bindu sign (excellent Ashtakavarga)")
                elif b >= AKV_GOOD:
                    bonus += AKV_GOOD_BONUS
                    reasons.append(f"Moon in {b}-bindu sign (good Ashtakavarga)")
                elif b < AKV_WEAK:
                    bonus += AKV_WEAK_PENALTY
                    cap = min(cap, AKV_WEAK_CAP)
                    reasons.append(
                        f"Moon in depleted {b}-bindu sign (weak Ashtakavarga)"
                    )

    # --- 19 Lagna Nak avoid ----------------------------------------------
    if prof.get("avoidLagnaNak") and lagna_nak and moon_nak == lagna_nak:
        bonus -= 10
        reasons.append(
            "Today's Moon is your Lagna Nakshatra — avoid for this activity"
        )

    # --- 20 Mercury retrograde -------------------------------------------
    if prof.get("avoidMercuryRetro"):
        merc = next(
            (t for t in (panch.transit or []) if t.get("planet") == "Mercury"), None
        )
        if merc and merc.get("retro"):
            bonus += MERCURY_RETRO_PENALTY
            cap = min(cap, MERCURY_RETRO_CAP)
            reasons.append("Mercury is retrograde — avoid for this activity")

    # --- 22 Moorti Nirnaya ------------------------------------------------
    if gochar.moorthy:
        m = gochar.moorthy
        verdict = m.get("verdict")
        name = m.get("name") or "Moorti"
        if verdict == "shubh":
            bonus += 6
            reasons.append(f"Moorti Nirnaya: {name} (favourable)")
        elif verdict == "ashubh":
            bonus -= 6
            reasons.append(f"Moorti Nirnaya: {name} (unfavourable)")

    # --- Eclipse hard cap ------------------------------------------------
    eclipse = panch.eclipse or gochar.eclipse
    if eclipse:
        bonus += ECLIPSE_PENALTY
        cap = min(cap, ECLIPSE_CAP)
        kind = "Solar" if eclipse.get("type") == "solar" else "Lunar"
        reasons.append(
            f"{kind} eclipse (Grahan) — classically avoided for all new undertakings"
        )

    # --- Time filter + candidate windows + Muhurta Lagna -----------------
    from_time_h = None
    to_time_h = None
    if time_filter:
        from_time_h = time_filter.get("from") if "from" in time_filter else time_filter.get("fromTimeH")
        to_time_h = time_filter.get("to") if "to" in time_filter else time_filter.get("toTimeH")
        # also accept tuple/list
        if from_time_h is None and isinstance(time_filter, (list, tuple)) and len(time_filter) == 2:
            from_time_h, to_time_h = time_filter[0], time_filter[1]

    has_time_filter = from_time_h is not None and to_time_h is not None
    windows = _candidate_windows(
        date_str,
        tz,
        lat,
        lon,
        sunrise=getattr(panch, "sunrise", None),
        sunset=getattr(panch, "sunset", None),
        from_time_h=float(from_time_h) if from_time_h is not None else None,
        to_time_h=float(to_time_h) if to_time_h is not None else None,
        weekday=weekday,
    )

    m_lagna: Optional[dict[str, Any]] = None
    if windows:
        best = windows[0]
        m_lagna = best.get("ml") or muhurta_lagna_at(
            date_str, best["midH"], tz, lat, lon
        )
        applied = apply_muhurta_lagna_to_finder(m_lagna, bonus=bonus, cap=cap)
        bonus = applied["bonus"]
        if applied["cap"] is not None:
            cap = applied["cap"]
        reasons.extend(applied["reasons"])
    elif has_time_filter:
        bonus += NO_WINDOWS_PENALTY
        cap = min(cap, NO_WINDOWS_CAP)
        reasons.append("No suitable windows in the selected time range")

    no_windows_in_range = bool(has_time_filter and not windows)

    # --- Dasha context (same for all days when predict_ctx fixed) ---------
    predict_score: Optional[int] = None
    predict_label = ""
    if predict_ctx and predict_ctx.get("dasha"):
        ds = predict_ctx["dasha"]
        maha = (ds.get("mahadasha") or {}).get("planet")
        antar = (ds.get("antardasha") or {}).get("planet")
        if maha:
            mb = DASHA_MAHA.get(maha, 0)
            bonus += mb
            sign = "+" if mb > 0 else ""
            reasons.append(f"Dasha: {maha} Mahadasha ({sign}{mb})")
        if antar:
            ab = DASHA_ANTAR.get(antar, 0)
            bonus += ab
            sign = "+" if ab > 0 else ""
            reasons.append(f"Antar: {antar} ({sign}{ab})")
        ps = predict_ctx.get("overall_score")
        predict_score = int(ps) if ps is not None else None
        predict_label = (maha or "") + (("–" + antar) if antar else "")

    # --- Gochar Table 12 -------------------------------------------------
    gc = score_gochar_table12(panch.transit or [], janma_rashi)
    bonus += gc["bonus"]
    if gc["cap"] is not None:
        cap = min(cap, gc["cap"])
    reasons.extend(gc["reasons"])

    # --- Final activity score + blend ------------------------------------
    activity_score = _clamp(BASE_DAY_SCORE + bonus, 0, cap)
    if (
        predict_score is not None
        and not no_windows_in_range
        and not eclipse
    ):
        blended = round(
            activity_score * ACTIVITY_BLEND_WEIGHT
            + predict_score * PREDICT_BLEND_WEIGHT
        )
    else:
        blended = activity_score

    if activity_score >= 68:
        base_verdict = "shubh"
    elif activity_score >= 48:
        base_verdict = "neutral"
    else:
        base_verdict = "ashubh"

    paksha = panch.tithi_paksha
    best_window = "—"
    if windows:
        w0 = windows[0]
        best_window = f"{w0['label']} ({w0.get('deity') or w0.get('lagna') or '—'})"

    return DayScore(
        date=date_str,
        weekday=weekday,
        score=int(blended),
        base_verdict=base_verdict,
        tithi=f"{panch.tithi_name} ({paksha})",
        tithi_short=f"{tip} {paksha}",
        group=panch.tithi_group,
        nak=moon_nak,
        yoga=panch.yoga_name,
        karana=panch.karana_name,
        tara=tara_name,
        tara_verdict=tara_verdict,
        eclipse=eclipse,
        lagna=(m_lagna or {}).get("ascSign", "—") if m_lagna else "—",
        lagna_verdict=(m_lagna or {}).get("verdict", "neutral") if m_lagna else "neutral",
        lagna_score=(m_lagna or {}).get("score") if m_lagna else None,
        windows=windows,
        no_windows_in_range=no_windows_in_range,
        best_window=best_window,
        predict_score=predict_score,
        predict_label=predict_label,
        gochar_good=gc["gochar_good"],
        gochar_bad=gc["gochar_bad"],
        reasons=reasons,
        sade_sati=ss.get("sade_sati"),
        activity_score=activity_score,
        bonus=bonus,
        cap=cap,
    )


# ---------------------------------------------------------------------------
# Public API — find_best_muhurta
# ---------------------------------------------------------------------------


def find_best_muhurta(
    from_date: Union[str, date, datetime],
    to_date: Union[str, date, datetime],
    lat: float,
    lon: float,
    tz: float,
    person: Optional[PersonLike] = None,
    activity_id: str = "Wedding · Muhurta",
    time_filter: TimeFilter = None,
    *,
    predict_ctx: Optional[Mapping[str, Any]] = None,
    top_n: Optional[int] = None,
) -> dict[str, Any]:
    """Find and rank best muhurta days in a date range.

    Port of JS ``findMuhurta({ fromDate, toDate, lat, lon, tz, ... })``.

    Parameters
    ----------
    from_date, to_date :
        Inclusive civil-date bounds (``YYYY-MM-DD`` or ``date``).
    lat, lon, tz :
        Query location and UTC offset hours (e.g. 5.5 for IST).
    person :
        Optional natal context dict. Recognised keys (snake or camel)::

            janma_rashi / janmaRashi
            janma_nakshatra / janmaNak
            lagna_rashi / lagnaRashi
            lagna_nakshatra / lagnaNak
            natal_sign / natalSign   # planet → rashi idx (0=Aries), incl. Lagna
            ashtakavarga             # {sav: [12 ints]}
            planets, vargas, birth_jd
            sade_sati_grade / sade_sati_subcase  # Kaksha override

    activity_id :
        Key into ``ACTIVITY_PROFILES`` (full id or unique suffix).
    time_filter :
        Optional ``{"from": H, "to": H}`` local decimal hours. Overnight
        ranges (from > to) are supported.
    predict_ctx :
        Optional ``{"dasha": {...}, "overall_score": int, "yogas": [...]}``
        matching the JS prediction-engine payload.
    top_n :
        If set, only the top N days (by score) are returned in ``days``.
        Full list always available under ``all_days`` when top_n is set.

    Returns
    -------
    dict with keys:
      ``profile`` — activity profile used
      ``days``    — ranked list of day dicts (score desc; noWindows filtered
                    to the bottom but still present, matching JS return)
      ``from_date``, ``to_date``, ``activity_id``, ``count``
    """
    start = _parse_date(from_date)
    end = _parse_date(to_date)
    if end < start:
        start, end = end, start

    person = dict(person or {})
    # Resolve profile once
    prof = get_activity_profile(activity_id)
    if prof is None:
        # suffix / partial match
        for k, v in ACTIVITY_PROFILES.items():
            if activity_id in k or k.endswith(activity_id):
                prof = v
                activity_id = k
                break
    if prof is None:
        # first profile as fallback (JS does the same)
        activity_id = next(iter(ACTIVITY_PROFILES))
        prof = ACTIVITY_PROFILES[activity_id]

    # Natal structure once for the whole range (chart-fixed)
    natal_structure = None
    contextual_natal = None
    planets = person.get("planets")
    vargas = person.get("vargas")
    if planets is not None or vargas is not None:
        natal_sign = person.get("natal_sign") or person.get("natalSign")
        lagna_idx = None
        if natal_sign and "Lagna" in natal_sign:
            lagna_idx = natal_sign["Lagna"]
        elif vargas and isinstance(vargas.get("D1"), dict):
            lagna_idx = vargas["D1"].get("Lagna")
        natal_structure = compute_natal_structure(
            planets or [],
            lagna_idx,
            person.get("birth_jd") or person.get("birthJD"),
            vargas=vargas,
        )
        contextual_natal = contextual_natal_bonus_for(
            prof.get("id") or activity_id,
            natal_structure.get("planetNatal") or {},
        )

    out: list[DayScore] = []
    cur = start
    guard = 0
    while cur <= end and guard < MAX_RANGE_DAYS:
        guard += 1
        ds = _date_str(cur)
        try:
            day = score_day(
                ds,
                lat=lat,
                lon=lon,
                tz=tz,
                activity_id=activity_id,
                person=person,
                time_filter=time_filter,
                predict_ctx=predict_ctx,
                natal_structure=natal_structure,
                contextual_natal=contextual_natal,
            )
            out.append(day)
        except Exception as exc:  # pragma: no cover — keep range resilient
            out.append(
                DayScore(
                    date=ds,
                    weekday="—",
                    score=0,
                    base_verdict="ashubh",
                    tithi="—",
                    tithi_short="—",
                    group="—",
                    nak="—",
                    yoga="—",
                    karana="—",
                    reasons=[f"scoring error: {exc}"],
                )
            )
        cur += timedelta(days=1)

    out.sort(key=lambda d: d.score, reverse=True)
    day_dicts = [d.to_dict() for d in out]

    result: dict[str, Any] = {
        "profile": prof,
        "days": day_dicts if top_n is None else day_dicts[: int(top_n)],
        "from_date": _date_str(start),
        "to_date": _date_str(end),
        "activity_id": activity_id,
        "count": len(day_dicts),
    }
    if top_n is not None:
        result["all_days"] = day_dicts
    return result


# Friendly aliases matching the JS names more closely
findMuhurta = find_best_muhurta
contextualNatalBonusFor = contextual_natal_bonus_for_activity


__all__ = [
    "BASE_DAY_SCORE",
    "ECLIPSE_PENALTY",
    "ECLIPSE_CAP",
    "SADE_SATI_PHASE_INFO",
    "DayScore",
    "contextual_natal_bonus_for_activity",
    "score_sade_sati",
    "score_sade_sati_from_gochar",
    "score_gochar_table12",
    "muhurta_lagna_at",
    "score_day",
    "find_best_muhurta",
    "findMuhurta",
    "contextualNatalBonusFor",
]
