"""
Dasha Prediction Module — Vimshottari + Yogini + Chara Dasha

Sources:
  - BPHS Ch.48 (Vimshottari Dasha)
  - Hora Sara Ch.11-19 (Dasha effects)
  - Phaladeepika Ch.20 (Dasha)
  - Jaimini Sutras (Chara Dasha)
  - Yogini Dasha by V.P. Goel

The Dasha system distributes life events through time. The birth Moon's
nakshatra determines the starting Mahadasha. Antardashas (sub-periods)
are proportional to each planet's Mahadasha duration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from ..core.astronomy import julian_day
from ..core.panchanga import NAKSHATRAS, NAK_LORD, PLANETS

_dasha_rules_version: str | None = None
_dasha_registered = False


def _clear_dasha_knowledge_caches() -> None:
    """Drop graph-backed dasha citations and reload graph on knowledge refresh."""
    try:
        from knowledge_engine.integration import get_knowledge_engine
        ke = get_knowledge_engine()
        # Force GraphRAG reload via KnowledgeEngine
        if hasattr(ke.store, "_graph"):
            ke.store._graph = None  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        from app.dasha_extras import clear_dasha_extras_cache
        clear_dasha_extras_cache()
    except ImportError:
        pass


def _on_dasha_refresh(new_version: str) -> None:
    global _dasha_rules_version
    _dasha_rules_version = new_version
    _clear_dasha_knowledge_caches()


def _register_dasha_engine() -> None:
    global _dasha_registered
    if _dasha_registered:
        return
    try:
        from knowledge_engine.integration import get_knowledge_engine
        get_knowledge_engine().register_engine("dasha", on_refresh=_on_dasha_refresh)
        _dasha_registered = True
    except Exception:
        pass


def _ensure_dasha_registered() -> None:
    if not _dasha_registered:
        _register_dasha_engine()


# =====================================================================
# Vimshottari Dasha (120 years total)
# =====================================================================

VIMSHOTTARI_PERIODS = {
    "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18,
    "Jupiter": 16, "Saturn": 19, "Mercury": 17, "Ketu": 7, "Venus": 20,
}

# Dasha order from Moon's nakshatra lord: Ketu → Venus → Sun → Moon → Mars → Rahu → Jupiter → Saturn → Mercury
DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

# Nakshatras ruled by each planet (for determining starting dasha)
DASHA_NAKSHATRAS = {
    "Ketu": ["Ashwini", "Magha", "Mula"],
    "Venus": ["Bharani", "Purva Phalguni", "Purva Ashadha"],
    "Sun": ["Krittika", "Uttara Phalguni", "Uttara Ashadha"],
    "Moon": ["Rohini", "Hasta", "Shravana"],
    "Mars": ["Mrigashira", "Chitra", "Dhanishtha"],
    "Rahu": ["Ardra", "Swati", "Shatabhisha"],
    "Jupiter": ["Punarvasu", "Vishakha", "Purva Bhadrapada"],
    "Saturn": ["Pushya", "Anuradha", "Uttara Bhadrapada"],
    "Mercury": ["Ashlesha", "Jyeshtha", "Revati"],
}

# Yogini Dasha (36 years total)
YOGINI_PERIODS = {
    "Mangala": 1, "Pingala": 2, "Dhanya": 3, "Bhramari": 4,
    "Bhadrika": 5, "Ulka": 6, "Siddha": 7, "Sankata": 8,
}

YOGINI_ORDER = ["Mangala", "Pingala", "Dhanya", "Bhramari", "Bhadrika", "Ulka", "Siddha", "Sankata"]

# Yogini Dasha: starting Yogini = YOGINI_ORDER[(nak_idx + 3) % 8]
# Classical formula from V.P. Goel: add 3 to nakshatra index, divide by 8
def _yogini_start(nakshatra_name):
    if nakshatra_name not in NAKSHATRAS: return None
    idx = NAKSHATRAS.index(nakshatra_name)
    return YOGINI_ORDER[(idx + 3) % 8]

YOGINI_EFFECTS = {
    "Mangala": {"lord": "Moon", "nature": "auspicious",
                "effect": "Growth, new beginnings, prosperity, good health, success in ventures"},
    "Pingala": {"lord": "Sun", "nature": "auspicious",
                "effect": "Wealth, recognition, authority, government support, honour"},
    "Dhanya": {"lord": "Jupiter", "nature": "auspicious",
               "effect": "Prosperity, education, spiritual growth, good fortune, children"},
    "Bhramari": {"lord": "Mars", "nature": "mixed",
                 "effect": "Travel, change of residence, fluctuating health, moderate results"},
    "Bhadrika": {"lord": "Mercury", "nature": "auspicious",
                 "effect": "Knowledge, communication, business success, intellectual pursuits"},
    "Ulka": {"lord": "Saturn", "nature": "inauspicious",
             "effect": "Obstacles, delays, health issues, financial stress, conflicts"},
    "Siddha": {"lord": "Venus", "nature": "auspicious",
               "effect": "Fulfillment, success, luxury, relationships, creative achievements"},
    "Sankata": {"lord": "Rahu", "nature": "inauspicious",
                "effect": "Crisis, upheaval, sudden changes, hidden enemies, health problems"},
}

# Dasha effects by planet (simplified from BPHS + Hora Sara)
DASHA_EFFECTS = {
    "Sun": "Authority, leadership, government, father, health, career advancement",
    "Moon": "Mind, emotions, mother, domestic life, public image, nourishment",
    "Mars": "Energy, courage, siblings, property, conflicts, surgery, sports",
    "Mercury": "Intellect, communication, business, learning, writing, short travels",
    "Jupiter": "Wisdom, wealth, children, spirituality, marriage, good fortune",
    "Venus": "Love, luxury, arts, relationships, vehicles, comforts, creativity",
    "Saturn": "Discipline, delays, career, longevity, servants, hardships, maturity",
    "Rahu": "Foreign matters, ambition, unconventional paths, sudden events, obsession",
    "Ketu": "Detachment, spirituality, past-life karma, isolation, sudden endings",
}


@dataclass
class DashaPeriod:
    """A single dasha period."""
    planet: str
    start_date: str  # YYYY-MM-DD
    end_date: str
    duration_years: float
    level: str  # "Maha" or "Antar"


@dataclass
class YoginiDasha:
    """A single Yogini dasha period."""
    yogini: str
    lord: str
    start_date: str
    end_date: str
    duration_years: float
    nature: str
    effect: str
    antardashas: list = field(default_factory=list)


@dataclass
class DashaResult:
    """Complete Dasha computation."""
    # Vimshottari
    birth_nakshatra: str = ""
    birth_nak_lord: str = ""
    balance_of_dasha: float = 0  # years remaining in birth dasha
    current_mahadasha: Optional[DashaPeriod] = None
    current_antardasha: Optional[DashaPeriod] = None
    all_mahadashas: list = field(default_factory=list)

    # Yogini
    balance_of_yogini: float = 0
    yogini_start: Optional[YoginiDasha] = None
    current_yogini: Optional[YoginiDasha] = None
    current_yogini_antardasha: Optional[DashaPeriod] = None
    all_yoginis: list = field(default_factory=list)

    # Synthesis
    dasha_score: int = 0
    summary: str = ""


def _julian_to_date(jd: float) -> str:
    """Convert Julian Day to YYYY-MM-DD string."""
    z = int(jd + 0.5)
    f = jd + 0.5 - z
    if z >= 2299161:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - int(alpha / 4)
    else:
        a = z
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d_val = int(365.25 * c)
    e = int((b - d_val) / 30.6001)
    day = int(b - d_val - int(30.6001 * e) + f)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    return f"{year}-{month:02d}-{day:02d}"


def _add_years(date_str: str, years: float) -> str:
    """Add years (365.25 days each) to a date string."""
    y, m, d = map(int, date_str.split("-"))
    total_days = years * 365.25
    dt = datetime(y, m, d) + timedelta(days=total_days)
    return dt.strftime("%Y-%m-%d")


def compute_vimshottari(birth_date: str, birth_time: str = "12:00",
                         birth_nakshatra: str = None,
                         birth_moon_lon: float = None,
                         query_date: str = None) -> DashaResult:
    """Compute Vimshottari Mahadasha and Antardasha.

    Args:
        birth_date: 'YYYY-MM-DD'
        birth_time: 'HH:MM'
        birth_nakshatra: Native's janma nakshatra
        birth_moon_lon: Exact sidereal Moon longitude at birth (degrees, 0-360).
                        Used to compute precise balance of dasha. If None, assumes
                        Moon at nakshatra midpoint (50% traversed).
        query_date: Date to compute current dasha for (default: today)
    """
    if birth_nakshatra not in NAKSHATRAS:
        return DashaResult()

    if query_date is None:
        query_date = datetime.now().strftime("%Y-%m-%d")

    result = DashaResult()
    result.birth_nakshatra = birth_nakshatra
    result.birth_nak_lord = NAK_LORD[NAKSHATRAS.index(birth_nakshatra)]

    # Determine starting Mahadasha lord
    nak_lord = result.birth_nak_lord

    # Balance of dasha at birth
    # Each nakshatra spans 13°20' (13.333...°). The Moon's exact position within
    # the nakshatra determines the elapsed fraction and thus the balance.
    nak_span = 360 / 27  # 13.333...°
    nak_idx = NAKSHATRAS.index(birth_nakshatra)

    if birth_moon_lon is not None:
        # Exact position: compute actual fraction of nakshatra traversed
        nak_start = nak_idx * nak_span
        elapsed_fraction = ((birth_moon_lon % 360) - nak_start) / nak_span
        if elapsed_fraction < 0:
            elapsed_fraction += 27  # wrap around
        elapsed_fraction = max(0, min(1, elapsed_fraction))
    else:
        # Default: assume Moon at midpoint
        elapsed_fraction = 0.5
    total_period = VIMSHOTTARI_PERIODS[nak_lord]
    balance = total_period * (1 - elapsed_fraction)
    result.balance_of_dasha = balance

    # Build all Mahadashas from birth
    start_map = {}
    start_idx = DASHA_ORDER.index(nak_lord)
    start_date = birth_date

    # First dasha: remaining balance
    dasha_periods = []
    current = start_date
    first_lord = nak_lord
    end_first = _add_years(current, balance)
    dasha_periods.append({
        "planet": first_lord, "start": current, "end": end_first,
        "years": balance, "level": "Maha"
    })
    current = end_first

    # Remaining dashas in order
    for i in range(1, 9):
        idx = (start_idx + i) % 9
        lord = DASHA_ORDER[idx]
        years = VIMSHOTTARI_PERIODS[lord]
        end = _add_years(current, years)
        dasha_periods.append({
            "planet": lord, "start": current, "end": end,
            "years": years, "level": "Maha"
        })
        current = end

    result.all_mahadashas = dasha_periods

    # Find current Mahadasha for query_date
    for dp in dasha_periods:
        if dp["start"] <= query_date < dp["end"]:
            result.current_mahadasha = DashaPeriod(
                planet=dp["planet"],
                start_date=dp["start"],
                end_date=dp["end"],
                duration_years=dp["years"],
                level="Maha",
            )

            # Compute Antardasha (sub-period)
            maha_lord = dp["planet"]
            maha_start = dp["start"]
            maha_total = VIMSHOTTARI_PERIODS[maha_lord]

            # Find position of maha lord in dasha order
            maha_idx = DASHA_ORDER.index(maha_lord)

            # Build antardasha sequence
            antardashas = []
            ant_start = maha_start
            for j in range(9):
                ant_idx = (maha_idx + j) % 9
                ant_lord = DASHA_ORDER[ant_idx]
                ant_years = (maha_total * VIMSHOTTARI_PERIODS[ant_lord]) / 120
                ant_end = _add_years(ant_start, ant_years)
                antardashas.append({
                    "planet": ant_lord, "start": ant_start, "end": ant_end,
                    "years": ant_years,
                })
                ant_start = ant_end

            # Find current Antardasha
            for ad in antardashas:
                if ad["start"] <= query_date < ad["end"]:
                    result.current_antardasha = DashaPeriod(
                        planet=ad["planet"],
                        start_date=ad["start"],
                        end_date=ad["end"],
                        duration_years=ad["years"],
                        level="Antar",
                    )
                    break
            break

    # Score the current dasha
    maha_benefic = {"Jupiter", "Venus", "Moon", "Mercury"}
    maha_malefic = {"Saturn", "Rahu", "Ketu", "Mars"}
    ant_benefic = {"Jupiter", "Venus", "Moon", "Mercury"}
    ant_malefic = {"Saturn", "Rahu", "Ketu", "Mars"}

    maha = result.current_mahadasha
    antar = result.current_antardasha
    if maha and antar:
        score = 0
        if maha.planet in maha_benefic:
            score += 5
        elif maha.planet in maha_malefic:
            score -= 5
        if antar.planet in ant_benefic:
            score += 3
        elif antar.planet in ant_malefic:
            score -= 3
        # Sun is neutral/slightly benefic in dasha
        result.dasha_score = score

    return result


def _add_days(date_str: str, days: float) -> str:
    """Add days to a date string."""
    y, m, d = map(int, date_str.split("-"))
    dt = datetime(y, m, d) + timedelta(days=days)
    return dt.strftime("%Y-%m-%d")


def _yogini_antardashas(maha_name: str, maha_years: int, start_date: str) -> list:
    """Yogini antardashas per Goel p.12: days = maha_years × antar_years × 10.

    The sequence starts from the mahadasha lord itself and proceeds in Yogini
    order cyclically through all 8 Yoginis.
    """
    antars = []
    current = start_date
    start_idx = YOGINI_ORDER.index(maha_name)
    for i in range(8):
        sub_name = YOGINI_ORDER[(start_idx + i) % 8]
        sub_years = YOGINI_PERIODS[sub_name]
        days = maha_years * sub_years * 10
        end = _add_days(current, days)
        antars.append({
            "yogini": sub_name,
            "start": current,
            "end": end,
            "days": days,
            "years": days / 365.25,
        })
        current = end
    return antars


def compute_yogini(birth_date: str, birth_nakshatra: str = None,
                    birth_moon_lon: float = None,
                    query_date: str = None) -> list:
    """Compute Yogini Dasha periods with birth balance and antardashas."""
    start_yogini = _yogini_start(birth_nakshatra)
    if start_yogini is None:
        return []

    if query_date is None:
        query_date = datetime.now().strftime("%Y-%m-%d")

    nak_span = 360 / 27
    nak_idx = NAKSHATRAS.index(birth_nakshatra)
    if birth_moon_lon is not None:
        nak_start = nak_idx * nak_span
        elapsed_fraction = ((birth_moon_lon % 360) - nak_start) / nak_span
        elapsed_fraction = max(0.0, min(1.0, elapsed_fraction))
    else:
        elapsed_fraction = 0.5

    start_idx = YOGINI_ORDER.index(start_yogini)
    yoginis = []
    current = birth_date

    for i in range(8):
        idx = (start_idx + i) % 8
        name = YOGINI_ORDER[idx]
        full_years = YOGINI_PERIODS[name]
        years = full_years * (1 - elapsed_fraction) if i == 0 else float(full_years)
        end = _add_years(current, years)
        info = YOGINI_EFFECTS[name]
        antars = _yogini_antardashas(name, YOGINI_PERIODS[name], current)
        yoginis.append(YoginiDasha(
            yogini=name, lord=info["lord"],
            start_date=current, end_date=end,
            duration_years=years,
            nature=info["nature"],
            effect=info["effect"],
            antardashas=antars,
        ))
        current = end
        elapsed_fraction = 0.0

    return yoginis


def compute_dasha(birth_date: str, birth_time: str = "12:00",
                   birth_nakshatra: str = None,
                   birth_moon_lon: float = None,
                   birth_lat: float = None, birth_lon: float = None, birth_tz: float = None,
                   query_date: str = None) -> DashaResult:
    """Compute all Dasha systems for a birth chart.

    Returns DashaResult with Vimshottari and Yogini dashas.
    """
    _ensure_dasha_registered()
    result = compute_vimshottari(birth_date, birth_time, birth_nakshatra,
                                   birth_moon_lon=birth_moon_lon,
                                   query_date=query_date)

    # Yogini Dasha
    yoginis = compute_yogini(
        birth_date, birth_nakshatra,
        birth_moon_lon=birth_moon_lon,
        query_date=query_date,
    )
    result.all_yoginis = yoginis

    if yoginis:
        first_balance = yoginis[0].duration_years
        result.balance_of_yogini = first_balance
        result.yogini_start = yoginis[0]

    for y in yoginis:
        if y.start_date <= query_date <= y.end_date:
            result.current_yogini = y
            for ad in y.antardashas:
                if ad["start"] <= query_date < ad["end"]:
                    result.current_yogini_antardasha = DashaPeriod(
                        planet=ad["yogini"],
                        start_date=ad["start"],
                        end_date=ad["end"],
                        duration_years=ad["years"],
                        level="Yogini-Antar",
                    )
                    break
            break

    # Build summary
    parts = []
    if result.current_mahadasha:
        m = result.current_mahadasha
        a = result.current_antardasha
        parts.append(f"Vimshottari: {m.planet} Mahadasha ({m.start_date} → {m.end_date})")
        if a:
            parts.append(f"  {a.planet} Antardasha ({a.start_date} → {a.end_date})")
        parts.append(f"  Dasha effect: {DASHA_EFFECTS.get(m.planet, '')}")
        parts.append(f"  Score: {result.dasha_score}")

    if result.current_yogini:
        y = result.current_yogini
        parts.append(f"Yogini: {y.yogini} Mahadasha ({y.start_date} → {y.end_date})")
        ya = result.current_yogini_antardasha
        if ya:
            parts.append(f"  {ya.planet} Antardasha ({ya.start_date} → {ya.end_date})")
        parts.append(f"  Nature: {y.nature} — {y.effect[:60]}...")

    result.summary = "\n".join(parts)
    return result
