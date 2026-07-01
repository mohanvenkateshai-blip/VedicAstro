from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..core.panchanga import NAK_LORD, NAKSHATRAS
from knowledge_engine.integration import get_structured_book, get_hierarchy_for_node, get_nodes_for_chapter

# Chara Dasha periods (108-year cycle)
CHARA_PERIODS = {
    "Sun": 9,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
    "Ketu": 7,
    "Venus": 20,
}

# Chara Dasha order (from Moon's nakshatra lord)
CHARA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

# Nakshatras ruled by each planet (for determining starting Chara dasha)
CHARA_NAKSHATRAS = {
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

@dataclass
class CharaDasha:
    """A single Chara dasha period."""

    planet: str
    start_date: str  # YYYY-MM-DD
    end_date: str
    duration_years: float
    antardashas: list = field(default_factory=list)

@dataclass
class CharaDashaResult:
    """Complete Chara Dasha computation."""

    birth_nakshatra: str = ""
    birth_nak_lord: str = ""
    balance_of_chara: float = 0  # years remaining in birth Chara dasha
    current_mahadasha: CharaDasha | None = None
    current_antardasha: CharaDasha | None = None
    all_mahadashas: list = field(default_factory=list)
    summary: str = ""

    # Chapter-aware provenance (populated via KE structured chapters + node patches)
    chapter_citation: str | None = None
    hierarchy_path: str | None = None

    # KE-sourced variant effects / conditionals (from _revive_dasha_rules)
    variant_notes: list[str] = field(default_factory=list)
    variant_citations: list[str] = field(default_factory=list)


def _add_years(date_str: str, years: float) -> str:
    """Add years (365.25 days each) to a date string."""
    y, m, d = map(int, date_str.split("-"))
    total_days = years * 365.25
    dt = datetime(y, m, d) + timedelta(days=total_days)
    return dt.strftime("%Y-%m-%d")


def _chara_antardashas(maha_name: str, maha_years: int, start_date: str) -> list:
    """Chara antardashas: proportional to Mahadasha duration."""
    antars = []
    current = start_date
    start_idx = CHARA_ORDER.index(maha_name)
    for i in range(9):
        sub_name = CHARA_ORDER[(start_idx + i) % 9]
        sub_years = (maha_years * CHARA_PERIODS[sub_name]) / 108
        end = _add_years(current, sub_years)
        antars.append(
            {
                "planet": sub_name,
                "start": current,
                "end": end,
                "years": sub_years,
            }
        )
        current = end
    return antars

def compute_chara(
    birth_date: str,
    birth_nakshatra: str = None,
    birth_moon_lon: float = None,
    query_date: str = None,
) -> CharaDashaResult:
    """Compute Chara Dasha periods with birth balance and proportional antardashas."""
    if birth_nakshatra not in NAKSHATRAS:
        return CharaDashaResult()

    if query_date is None:
        query_date = datetime.now().strftime("%Y-%m-%d")

    result = CharaDashaResult()
    result.birth_nakshatra = birth_nakshatra
    result.birth_nak_lord = NAK_LORD[NAKSHATRAS.index(birth_nakshatra)]

    # Determine starting Mahadasha lord
    nak_lord = result.birth_nak_lord

    # Balance of Chara dasha at birth
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
    total_period = CHARA_PERIODS[nak_lord]
    balance = total_period * (1 - elapsed_fraction)
    result.balance_of_chara = balance

    # Build all Mahadashas from birth
    start_map = {}
    start_idx = CHARA_ORDER.index(nak_lord)
    start_date = birth_date

    # First dasha: remaining balance
    dasha_periods = []
    current = start_date
    first_lord = nak_lord
    end_first = _add_years(current, balance)
    dasha_periods.append(
        {
            "planet": first_lord,
            "start": current,
            "end": end_first,
            "years": balance,
        }
    )
    current = end_first

    # Remaining dashas in order
    for i in range(1, 9):
        idx = (start_idx + i) % 9
        lord = CHARA_ORDER[idx]
        years = CHARA_PERIODS[lord]
        end = _add_years(current, years)
        antars = _chara_antardashas(lord, years, current)
        dasha_periods.append(
            {
                "planet": lord,
                "start": current,
                "end": end,
                "years": years,
                "antardashas": antars,
            }
        )
        current = end

    result.all_mahadashas = dasha_periods

    # Find current Mahadasha for query_date
    for dp in dasha_periods:
        if dp["start"] <= query_date < dp["end"]:
            result.current_mahadasha = CharaDasha(
                planet=dp["planet"],
                start_date=dp["start"],
                end_date=dp["end"],
                duration_years=dp["years"],
            )

            # Compute Antardasha (sub-period)
            maha_lord = dp["planet"]
            maha_start = dp["start"]
            maha_total = CHARA_PERIODS[maha_lord]

            # Find position of maha lord in dasha order
            maha_idx = CHARA_ORDER.index(maha_lord)

            # Build antardasha sequence
            antardashas = []
            ant_start = maha_start
            for j in range(9):
                ant_idx = (maha_idx + j) % 9
                ant_lord = CHARA_ORDER[ant_idx]
                ant_years = (maha_total * CHARA_PERIODS[ant_lord]) / 108
                ant_end = _add_years(ant_start, ant_years)
                antardashas.append(
                    {
                        "planet": ant_lord,
                        "start": ant_start,
                        "end": ant_end,
                        "years": ant_years,
                    }
                )
                ant_start = ant_end

            # Find current Antardasha
            for ad in antardashas:
                if ad["start"] <= query_date < ad["end"]:
                    result.current_antardasha = CharaDasha(
                        planet=ad["planet"],
                        start_date=ad["start"],
                        end_date=ad["end"],
                        duration_years=ad["years"],
                    )
                    break
            break

    # Build summary
    parts = []
    if result.current_mahadasha:
        m = result.current_mahadasha
        a = result.current_antardasha
        parts.append(f"Chara: {m.planet} Mahadasha ({m.start_date} → {m.end_date}) ")
        if a:
            parts.append(f"  {a.planet} Antardasha ({a.start_date} → {a.end_date}) ")

    result.summary = "\n".join(parts)

    return result