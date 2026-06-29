"""
Yoga Detection Module — Identifies classical planetary combinations (Yogas)

Sources:
  - BPHS Ch.35-36 (Raja Yogas, Nabhasa Yogas)
  - Phaladeepika Ch.6-7 (Yogas) — Viswa Bharati / Sastri edition, 1937
  - Sarvartha Chintamani Ch.8-9 (Raja Yogas, Sanyas Yoga)
  - Hora Sara Ch.19-20 (Chandra Yogas, Surya Yogas, Lagna Yogas, Nabhasa Yogas, Raja Yogas)
    by Prithuyasas (son of Varahamihira), transl. R. Santhanam, Ranjan Pub. 1982

Each yoga has:
  - conditions: dict of planet→sign relationships
  - effect: description of the yoga's results
  - source: text reference
  - confidence: 1.0 (direct) or 0.7 (partial match)
"""

from dataclasses import dataclass, field
from typing import Optional

from ..core.panchanga import RASHIS, NAKSHATRAS

_yoga_rules_version: str | None = None
_yoga_registered = False


def _clear_yoga_knowledge_caches() -> None:
    """Drop graph-backed yoga citations so the next detect_yogas reloads from graph."""
    try:
        from knowledge_engine.integration import get_knowledge_engine
        ke = get_knowledge_engine()
        if hasattr(ke.store, "_graph"):
            ke.store._graph = None  # type: ignore[attr-defined]
    except Exception:
        pass


def _on_yoga_refresh(new_version: str) -> None:
    global _yoga_rules_version
    _yoga_rules_version = new_version
    _clear_yoga_knowledge_caches()


def _register_yoga_engine() -> None:
    global _yoga_registered
    if _yoga_registered:
        return
    try:
        from knowledge_engine.integration import get_knowledge_engine
        get_knowledge_engine().register_engine("yoga", on_refresh=_on_yoga_refresh)
        _yoga_registered = True
    except Exception:
        pass


def _ensure_yoga_registered() -> None:
    if not _yoga_registered:
        _register_yoga_engine()


@dataclass
class DetectedYoga:
    """A detected yoga with its details."""
    name: str
    category: str  # Raja, Dhana, Chandra, Nabhasa, PanchaMahapurusha, etc.
    description: str
    planets_involved: list
    source: str
    benefic: bool
    confidence: float  # 0-1


# =====================================================================
# Pancha Mahapurusha Yogas (BPHS Ch.36)
# =====================================================================
# Five great-person yogas formed when a planet is in its own/exaltation sign in a Kendra (1, 4, 7, 10)

PANCHA_MAHAPURUSHA = [
    {
        "name": "Ruchaka Yoga",
        "planet": "Mars",
        "condition": "Mars in own sign or exaltation in a Kendra (1, 4, 7, 10)",
        "effect": "Energetic, courageous, military/leadership success, wealthy, famous",
        "source": "BPHS-Ch36",
    },
    {
        "name": "Bhadra Yoga",
        "planet": "Mercury",
        "condition": "Mercury in own sign or exaltation in a Kendra",
        "effect": "Highly intelligent, eloquent, wealthy, long-lived, learned in all sciences",
        "source": "BPHS-Ch36",
    },
    {
        "name": "Hamsa Yoga",
        "planet": "Jupiter",
        "condition": "Jupiter in own sign or exaltation in a Kendra",
        "effect": "Righteous, wealthy, respected, spiritual leader, beautiful appearance",
        "source": "BPHS-Ch36",
    },
    {
        "name": "Malavya Yoga",
        "planet": "Venus",
        "condition": "Venus in own sign or exaltation in a Kendra",
        "effect": "Luxurious life, artistic talent, beautiful spouse, vehicles, good fortune",
        "source": "BPHS-Ch36",
    },
    {
        "name": "Sasa Yoga",
        "planet": "Saturn",
        "condition": "Saturn in own sign or exaltation in a Kendra",
        "effect": "Authoritative, leader, disciplined, controls many people, long-lived",
        "source": "BPHS-Ch36",
    },
]

# =====================================================================
# Chandra Yogas (Moon-based yogas) — BPHS Ch.35 / Hora Sara Ch.7
# =====================================================================

CHANDRA_YOGAS = [
    {
        "name": "Sunapha Yoga",
        "condition": "Planet (other than Sun) in 2nd from Moon",
        "effect": "Wealth, intelligence, fame, self-earned prosperity",
        "source": "BPHS-Ch35",
    },
    {
        "name": "Anapha Yoga",
        "condition": "Planet (other than Sun) in 12th from Moon",
        "effect": "Prosperous, healthy, moral, famous, fond of luxuries",
        "source": "BPHS-Ch35",
    },
    {
        "name": "Durudhara Yoga",
        "condition": "Planets (other than Sun) in BOTH 2nd and 12th from Moon",
        "effect": "Wealthy, generous, owns vehicles, well-educated, happy",
        "source": "BPHS-Ch35",
    },
    {
        "name": "Kemadruma Yoga",
        "condition": "No planet (other than Sun) in 2nd or 12th from Moon, AND no planet in Kendra from Lagna",
        "effect": "Poverty, mental distress, isolation, struggle despite efforts",
        "source": "BPHS-Ch35",
    },
    {
        "name": "Adhi Yoga",
        "condition": "Benefics (Mercury, Jupiter, Venus) in 6th, 7th, and 8th from Moon",
        "effect": "Leadership, authority, prosperous, respected, powerful",
        "source": "BPHS-Ch35",
    },
]

# =====================================================================
# Raja Yogas (BPHS Ch.36, PD Ch.6, SC Ch.8)
# =====================================================================

RAJA_YOGAS = [
    # Kendra-Kona connection
    {
        "name": "Raja Yoga (Kendra-Kona)",
        "condition": "Lord of a Kendra (1,4,7,10) is with/aspected by lord of a Kona (1,5,9)",
        "planets": [],
        "effect": "Authority, power, high position, royal favour, success",
        "source": "BPHS-Ch36",
    },
    # Mutual Kendra lords
    {
        "name": "Raja Yoga (Mutual Kendra)",
        "condition": "Lords of Kendra houses in mutual exchange or conjunction",
        "planets": [],
        "effect": "Prestige, recognition, leadership role, governmental authority",
        "source": "BPHS-Ch36",
    },
    # 9th and 10th lord conjunction
    {
        "name": "Dharma-Karma Adhipati Yoga",
        "condition": "Lord of 9th and 10th conjoined or in mutual exchange",
        "effect": "Immense success, fame, righteous leadership, fortune through career",
        "source": "PD-Ch6",
    },
    # 4th and 9th lord connection
    {
        "name": "Raja Yoga (4-9 Connection)",
        "condition": "Lord of 4th and 9th in conjunction or mutual aspect",
        "effect": "Wealth from property/vehicles, happy home, spiritual fortune",
        "source": "SC-Ch8",
    },
    # 5th and 9th lord connection  
    {
        "name": "Raja Yoga (5-9 Connection)",
        "condition": "Lord of 5th and 9th conjoined or in Kendra to each other",
        "effect": "Great fortune, wisdom, higher education, spiritual authority",
        "source": "SC-Ch8",
    },
    # Mercury in 5th with benefic aspect
    {
        "name": "Buddha-Aditya Yoga",
        "condition": "Mercury and Sun conjoined in any sign",
        "effect": "High intelligence, education, writing ability, governmental position",
        "source": "BPHS-Ch36",
    },
    # Jupiter-Mercury conjunction
    {
        "name": "Gaja-Kesari Yoga",
        "condition": "Jupiter in Kendra from Moon",
        "effect": "Fame, respect, eloquence, wealthy, many followers",
        "source": "BPHS-Ch36",
    },
    # Venus-Jupiter conjunction
    {
        "name": "Lakshmi Yoga",
        "condition": "Venus and Jupiter in conjunction or mutual aspect in benefic signs",
        "effect": "Wealth, beauty, prosperity, good fortune, happy marriage",
        "source": "PD-Ch7",
    },
]

# =====================================================================
# Dhana Yogas (Wealth Yogas) — PD Ch.7
# =====================================================================

DHANA_YOGAS = [
    {
        "name": "Dhana Yoga (2nd lord + 11th lord)",
        "condition": "Lord of 2nd house associated with lord of 11th (or Jupiter)",
        "effect": "Wealth accumulation, multiple income sources",
        "source": "PD-Ch7",
    },
    {
        "name": "Dhana Yoga (2nd lord + 5th lord)",
        "condition": "Lord of 2nd in 5th or vice versa with benefic influence",
        "effect": "Wealth through speculation, children, creativity, education",
        "source": "PD-Ch7",
    },
    {
        "name": "Dhana Yoga (2nd lord + 9th lord)",
        "condition": "Lord of 2nd associated with lord of 9th",
        "effect": "Wealth through fortune, inheritance, dharma, pilgrimage",
        "source": "PD-Ch7",
    },
    {
        "name": "Dhana Yoga (5th lord in Kendra/Kona)",
        "condition": "Lord of 5th in Kendra or Kona with benefic aspect",
        "effect": "Wealth through intelligence, speculation, mantra, creativity",
        "source": "PD-Ch7",
    },
]

# =====================================================================
# Nabhasa Yogas (Celestial Yogas) — BPHS Ch.12
# =====================================================================

NABHASA_YOGAS = [
    {
        "name": "Rajju Yoga",
        "condition": "All planets in movable signs (Aries, Cancer, Libra, Capricorn)",
        "effect": "Frequent travel, foreign residence, adventurous life",
        "source": "BPHS-Ch12",
    },
    {
        "name": "Musala Yoga",
        "condition": "All planets in fixed signs (Taurus, Leo, Scorpio, Aquarius)",
        "effect": "Steady, determined, good at one profession, proud",
        "source": "BPHS-Ch12",
    },
    {
        "name": "Nala Yoga",
        "condition": "All planets in dual signs (Gemini, Virgo, Sagittarius, Pisces)",
        "effect": "Versatile, good at many skills, helpful, social",
        "source": "BPHS-Ch12",
    },
    {
        "name": "Gada Yoga",
        "condition": "All planets occupy two successive angular houses (e.g., 1st and 4th, 4th and 7th, 7th and 10th, or 10th and 1st)",
        "effect": "Wealthy, strong, respected, authoritative",
        "source": "BPHS-Ch12-v9",
    },
]

# =====================================================================
# Additional Yogas from Sarvartha Chintamani
# =====================================================================

SC_YOGAS = [
    {
        "name": "Viparita Raja Yoga",
        "condition": "Lord of 6th, 8th, or 12th in a Dusthana (6,8,12) or with another Dusthana lord",
        "effect": "Success through adversity, triumph over enemies, wealth from unexpected sources",
        "source": "SC-Ch8",
    },
    {
        "name": "Neecha Bhanga Raja Yoga",
        "condition": "Debilitated planet gets cancellation — lord of debilitation sign in Kendra from Moon/Lagna OR exalted lord aspects debilitated planet",
        "effect": "Rise from humble beginnings, success after struggles, Raja Yoga despite debilitation",
        "source": "BPHS-Ch36",
    },
    {
        "name": "Parivartana Yoga (Exchange Yoga)",
        "condition": "Two planets in mutual exchange of signs (each in the other's sign)",
        "effect": "Exchange of karakatwas, mutual support, combined effects of both houses",
        "source": "SC-Ch8",
    },
]

# =====================================================================
# Surya Yogas (Solar yogas) — Hora Sara Ch.19 sl.9-12 / BPHS Ch.35
# =====================================================================

SURYA_YOGAS = [
    {
        "name": "Vesi Yoga",
        "condition": "Planet (other than Moon) in 2nd from Sun",
        "effect": "Slow walk, soft-spoken, hopeful, balanced wealth and outgo, dear to men",
        "source": "HoraSara-Ch19-sl9",
    },
    {
        "name": "Vasi Yoga",
        "condition": "Planet (other than Moon) in 12th from Sun",
        "effect": "If benefics: all comforts and wealth; if malefics: sinful, defective-limbed, sleepy, laborious",
        "source": "HoraSara-Ch19-sl9",
    },
    {
        "name": "Ubhayachari Yoga",
        "condition": "Planets (other than Moon) in both 2nd and 12th from Sun",
        "effect": "Talkative, wise, strong, leader, dear to king, enthusiastic, eloquent",
        "source": "HoraSara-Ch19-sl9",
    },
]

# =====================================================================
# Lagna Yogas — Hora Sara Ch.19 sl.13-18
# =====================================================================

LAGNA_YOGAS = [
    {
        "name": "Sushubha Yoga",
        "condition": "Planet (other than luminaries) in 2nd from Lagna",
        "effect": "Wealthy, attached to women, principled, ever-active, head of monetary transactions",
        "source": "HoraSara-Ch19-sl13",
    },
    {
        "name": "Ashubha Yoga",
        "condition": "Planet (other than luminaries) in 12th from Lagna",
        "effect": "Strong body, caste leader, enthusiastic, speaker, helpful, charitable, dear to all",
        "source": "HoraSara-Ch19-sl15",
    },
    {
        "name": "Karthari Yoga",
        "condition": "Malefics in both 2nd and 12th from Lagna (scissors cutting the Lagna)",
        "effect": "Angry, grieved, hates parents, lacks enthusiasm, lives abroad, danger from poison/fire/weapons",
        "source": "HoraSara-Ch19-sl16",
    },
    {
        "name": "Lagnadhi Yoga",
        "condition": "Benefics (Jupiter, Venus, Mercury) in 6th, 7th, 8th from Lagna, free from malefic aspect",
        "effect": "Minister, army chief, king, many wives, humble, long life, virtuous, enemy-free",
        "source": "HoraSara-Ch19-sl17",
    },
]

# =====================================================================
# Additional Phaladeepika Yogas (VB / Sastri edition, 1937)
# Sources: Phaladeepika Ch.6 sl.14-31, sl.39-43, sl.57-69
# =====================================================================

PD_YOGAS = [
    {
        "name": "Mahabhagya Yoga",
        "condition": "Day birth (male): Sun, Moon, Lagna all in odd signs; OR night birth (female): all in even signs",
        "effect": "Immense pleasure, liberal, famous, ruler, 80-year life, spotless character",
        "source": "PD-Ch6-sl14",
    },
    {
        "name": "Sakata Yoga",
        "condition": "Moon in 6th, 8th, or 12th from Jupiter; cancelled if Moon in Kendra from Lagna",
        "effect": "Frequently loses fortune, may regain, ordinary, mental grief, insignificant",
        "source": "PD-Ch6-sl17",
    },
    {
        "name": "Vasumati Yoga",
        "condition": "All natural benefics (Jupiter, Venus, Mercury) in Upachaya houses (3,6,10,11) from Lagna or Moon",
        "effect": "Commands plenty of money, always at home in comfort",
        "source": "PD-Ch6-sl19",
    },
    {
        "name": "Amala Yoga",
        "condition": "Benefic planet (Jupiter, Venus, or unafflicted Mercury) in 10th from Lagna or Moon",
        "effect": "Rules the earth, wealthy, sons, famous, prosperous, prudent, untarnished career",
        "source": "PD-Ch6-sl20",
    },
    {
        "name": "Saraswati Yoga",
        "condition": "Venus, Jupiter, Mercury in Kendra/Trikona/2nd house; Jupiter in exaltation/own/friendly sign",
        "effect": "Highly intelligent, clever in drama/poetry/prose/accounts, famous, wealthy, respected by kings",
        "source": "PD-Ch6-sl26",
    },
    {
        "name": "Harsha Yoga",
        "condition": "Lord of 6th house placed in the 6th house (dusthana lord in own dusthana)",
        "effect": "Happiness, enjoyment, good fortune, strong constitution, overcomes enemies, friend of illustrious",
        "source": "PD-Ch6-sl57",
    },
    {
        "name": "Sarala Yoga",
        "condition": "Lord of 8th house placed in the 8th house (dusthana lord in own dusthana)",
        "effect": "Long-lived, resolute, fearless, prosperous, success, overcomes foes, celebrated, pure",
        "source": "PD-Ch6-sl63",
    },
    {
        "name": "Vimala Yoga",
        "condition": "Lord of 12th house placed in the 12th house (dusthana lord in own dusthana)",
        "effect": "Spends little, saves much, good to all, happy, independent, respectable profession",
        "source": "PD-Ch6-sl65",
    },
    # Sankhya (numerical) Nabhasa yogas by sign count — PD-VB Ch.6 sl.39-41
    {
        "name": "Vallaki Yoga",
        "condition": "All 7 planets spread across 7 distinct signs",
        "effect": "Fond of dance/music, greatly wealthy, talented polymath, cultural refinement",
        "source": "PD-Ch6-sl39",
    },
    {
        "name": "Dama Yoga",
        "condition": "All 7 planets spread across 6 distinct signs",
        "effect": "Liberal, king, benefactor, philanthropic, highly reliable, wise",
        "source": "PD-Ch6-sl39",
    },
    {
        "name": "Pasa Yoga",
        "condition": "All 7 planets spread across 5 distinct signs",
        "effect": "Opulent, enjoyment, extensive networks, great skill in people-ecosystems",
        "source": "PD-Ch6-sl40",
    },
    {
        "name": "Kedara Yoga",
        "condition": "All 7 planets spread across 4 distinct signs",
        "effect": "Wealth, agricultural lands, helps relatives, dutiful, honored, close to earth",
        "source": "PD-Ch6-sl40",
    },
    {
        "name": "Sula Yoga",
        "condition": "All 7 planets concentrated in 3 distinct signs",
        "effect": "Cruel, angry, focused single-mindedly, indigent, alternately prosperous",
        "source": "PD-Ch6-sl41",
    },
    {
        "name": "Yuga Yoga",
        "condition": "All 7 planets concentrated in 2 distinct signs",
        "effect": "Heretical, without consistent wealth, dual-life choices, limited relatives",
        "source": "PD-Ch6-sl41",
    },
    {
        "name": "Gola Yoga",
        "condition": "All 7 planets packed in 1 single sign",
        "effect": "Without wealth, sinful, low associates, short-lived, highly insular",
        "source": "PD-Ch6-sl41",
    },
]

# =====================================================================
# Additional Hora Sara Raja Yogas — Ch.20
# =====================================================================

HS_RAJA_YOGAS = [
    {
        "name": "Pushkala Yoga",
        "condition": "Moon's dispositor (sign lord of Moon's rashi) conjoined with Lagna lord in a friendly Kendra, aspecting Lagna",
        "effect": "Lords over earth; royal scion; exquisite speech; executive governance",
        "source": "HoraSara-Ch20-sl12",
    },
    {
        "name": "Sanyas Yoga",
        "condition": "Four or more planets together in a Kendra house",
        "effect": "Renunciation, ascetic life, spiritual orders",
        "source": "SC-Ch8-sl1",
    },
    {
        "name": "Mala Yoga",
        "condition": "All natural benefics (Jupiter, Venus, Mercury) in Kendra houses from Lagna",
        "effect": "Learned, wealthy, an unbroken stream of material comfort",
        "source": "HoraSara-Ch19-sl43",
    },
    {
        "name": "Sarpa Yoga",
        "condition": "All natural malefics (Sun, Mars, Saturn) in Kendra houses from Lagna",
        "effect": "Penniless, talkative, leaves paternal place, troubles others, short-lived",
        "source": "HoraSara-Ch19-sl44",
    },
]

# =====================================================================
# Planet ownership mappings
# =====================================================================

PLANET_OWNERSHIP = {
    "Sun": ["Leo"],
    "Moon": ["Cancer"],
    "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"],
    "Saturn": ["Capricorn", "Aquarius"],
}

EXALTATION = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces", "Saturn": "Libra",
}

DEBILITATION = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
    "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo", "Saturn": "Aries",
}

BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
KENDRA = [1, 4, 7, 10]
KONA = [1, 5, 9]


def _get_house_lord(house: int, lagna_rashi_idx: int) -> str:
    """Get the lord of a house from Lagna."""
    rashi_idx = (lagna_rashi_idx + house - 1) % 12
    rashi = RASHIS[rashi_idx]
    for planet, signs in PLANET_OWNERSHIP.items():
        if rashi in signs:
            return planet
    return ""


def _planet_in_house(house: int, lagna_idx: int, planet_rashi_idx: int) -> bool:
    """Check if a planet is in a specific house from Lagna."""
    planet_house = ((planet_rashi_idx - lagna_idx + 12) % 12) + 1
    return planet_house == house


def _is_in_kendra(house: int) -> bool:
    return house in KENDRA


def _is_in_kona(house: int) -> bool:
    return house in KONA


CLASSICAL_GRAHAS = frozenset({"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"})
PANAPHARA = [2, 5, 8, 11]
APOKLIMA = [3, 6, 9, 12]


def _sign_lord(rashi_name: str) -> str:
    for planet, signs in PLANET_OWNERSHIP.items():
        if rashi_name in signs:
            return planet
    return ""


def _lords_conjunct_or_exchange(
    h1: int, h2: int, lagna_idx: int, planet_rashis: dict,
) -> tuple[bool, list[str]]:
    """True when house lords are conjunct or in mutual sign exchange."""
    lord1 = _get_house_lord(h1, lagna_idx)
    lord2 = _get_house_lord(h2, lagna_idx)
    if not lord1 or not lord2 or lord1 not in planet_rashis or lord2 not in planet_rashis:
        return False, []
    if planet_rashis[lord1] == planet_rashis[lord2]:
        return True, [lord1, lord2]
    r1 = RASHIS[planet_rashis[lord1]]
    r2 = RASHIS[planet_rashis[lord2]]
    if r1 in PLANET_OWNERSHIP.get(lord2, []) and r2 in PLANET_OWNERSHIP.get(lord1, []):
        return True, [lord1, lord2]
    return False, []


def detect_yogas(natal_sign: dict, lagna_sign_idx: int,
                  moon_rashi_idx: int = None) -> list:
    """Detect all yogas present in a natal chart.

    Args:
        natal_sign: dict of planet → rashi_index (0=Aries) for Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn
        lagna_sign_idx: Lagna rashi index (0-11)
        moon_rashi_idx: Moon's rashi index (optional, can derive from natal_sign)

    Returns:
        list of DetectedYoga
    """
    _ensure_yoga_registered()
    detected = []

    if moon_rashi_idx is None and "Moon" in natal_sign:
        moon_rashi_idx = natal_sign["Moon"]

    if not natal_sign or lagna_sign_idx is None:
        return detected

    # Get planet rashis
    planet_rashis = {p: idx for p, idx in natal_sign.items() if idx is not None}

    # Helper: planet's house from Lagna
    def planet_house(planet: str) -> int:
        if planet not in planet_rashis:
            return -1
        return ((planet_rashis[planet] - lagna_sign_idx + 12) % 12) + 1

    # Helper: planet's house from Moon
    def planet_house_from_moon(planet: str) -> int:
        if planet not in planet_rashis or moon_rashi_idx is None:
            return -1
        return ((planet_rashis[planet] - moon_rashi_idx + 12) % 12) + 1

    # ---- Pancha Mahapurusha Yogas ----
    for yoga in PANCHA_MAHAPURUSHA:
        p = yoga["planet"]
        if p not in planet_rashis:
            continue
        house = planet_house(p)
        if house in KENDRA:
            rashi = RASHIS[planet_rashis[p]]
            is_own = rashi in PLANET_OWNERSHIP.get(p, [])
            is_exalt = rashi == EXALTATION.get(p)
            if is_own or is_exalt:
                detected.append(DetectedYoga(
                    name=yoga["name"], category="Pancha Mahapurusha",
                    description=yoga["effect"],
                    planets_involved=[p],
                    source=yoga["source"], benefic=True, confidence=1.0
                ))

    # ---- Chandra Yogas ----
    if moon_rashi_idx is not None:
        planets_in_2nd = []
        planets_in_12th = []
        for p in planet_rashis:
            if p == "Sun":
                continue
            h = planet_house_from_moon(p)
            if h == 2:
                planets_in_2nd.append(p)
            if h == 12:
                planets_in_12th.append(p)

        if planets_in_2nd:
            detected.append(DetectedYoga(
                name="Sunapha Yoga", category="Chandra",
                description="Wealth, intelligence, fame, self-earned prosperity",
                planets_involved=planets_in_2nd,
                source="BPHS-Ch35", benefic=True, confidence=1.0
            ))
        if planets_in_12th:
            detected.append(DetectedYoga(
                name="Anapha Yoga", category="Chandra",
                description="Prosperous, healthy, moral, famous, fond of luxuries",
                planets_involved=planets_in_12th,
                source="BPHS-Ch35", benefic=True, confidence=1.0
            ))
        if planets_in_2nd and planets_in_12th:
            detected.append(DetectedYoga(
                name="Durudhara Yoga", category="Chandra",
                description="Wealthy, generous, owns vehicles, well-educated, happy",
                planets_involved=planets_in_2nd + planets_in_12th,
                source="BPHS-Ch35", benefic=True, confidence=1.0
            ))
        if not planets_in_2nd and not planets_in_12th:
            # Kemadruma cancellation: benefic in Kendra from Lagna or Moon
            has_kendra_benefic = False
            for p in planet_rashis:
                if p in BENEFICS - {"Moon"}:
                    if planet_house(p) in KENDRA or planet_house_from_moon(p) in KENDRA:
                        has_kendra_benefic = True
                        break
            moon_house = planet_house("Moon") if "Moon" in planet_rashis else -1
            if moon_house in KENDRA:
                has_kendra_benefic = True
            if not has_kendra_benefic:
                detected.append(DetectedYoga(
                    name="Kemadruma Yoga", category="Chandra",
                    description="Poverty, mental distress, isolation — no Kendra benefic from Lagna",
                    planets_involved=[],
                    source="BPHS-Ch35", benefic=False, confidence=0.7
                ))
            else:
                detected.append(DetectedYoga(
                    name="Kemadruma (cancelled)", category="Chandra",
                    description="Kemadruma formed but cancelled — benefic in Kendra from Lagna",
                    planets_involved=[],
                    source="BPHS-Ch35", benefic=True, confidence=0.8
                ))

        # Adhi Yoga: benefic (Jupiter, Venus, Mercury) in 6th, 7th, or 8th from Moon
        # Benefics must not be conjunct the Sun (Hora Sara Ch.19 v.1)
        sun_rashi = planet_rashis.get("Sun")
        benefic_houses_678: set[int] = set()
        adhi_planets: list[str] = []
        for p in ("Jupiter", "Venus", "Mercury"):
            if p not in planet_rashis:
                continue
            # Exclude if conjunct Sun
            if sun_rashi is not None and planet_rashis[p] == sun_rashi:
                continue
            h = planet_house_from_moon(p)
            if h in (6, 7, 8):
                benefic_houses_678.add(h)
                adhi_planets.append(p)
        if benefic_houses_678 >= {6, 7, 8}:
            detected.append(DetectedYoga(
                name="Adhi Yoga", category="Chandra",
                description="Leadership, authority, prosperity, respected, powerful",
                planets_involved=adhi_planets,
                source="BPHS-Ch35", benefic=True, confidence=0.9
            ))

    # ---- Gaja-Kesari Yoga ----
    if "Jupiter" in planet_rashis and moon_rashi_idx is not None:
        jup_house = planet_house_from_moon("Jupiter")
        if jup_house in KENDRA:
            detected.append(DetectedYoga(
                name="Gaja-Kesari Yoga", category="Raja",
                description="Fame, respect, eloquence, wealthy, many followers",
                planets_involved=["Jupiter"],
                source="BPHS-Ch36", benefic=True, confidence=1.0
            ))

    # ---- Buddha-Aditya Yoga ----
    if "Mercury" in planet_rashis and "Sun" in planet_rashis:
        if planet_rashis["Mercury"] == planet_rashis["Sun"]:
            detected.append(DetectedYoga(
                name="Buddha-Aditya Yoga", category="Raja",
                description="High intelligence, education, writing ability, governmental position",
                planets_involved=["Sun", "Mercury"],
                source="BPHS-Ch36", benefic=True, confidence=1.0
            ))

    # ---- Lakshmi Yoga (Venus-Jupiter conjunction) ----
    if "Venus" in planet_rashis and "Jupiter" in planet_rashis:
        if planet_rashis["Venus"] == planet_rashis["Jupiter"]:
            detected.append(DetectedYoga(
                name="Lakshmi Yoga", category="Raja",
                description="Wealth, beauty, prosperity, good fortune, happy marriage",
                planets_involved=["Venus", "Jupiter"],
                source="PD-Ch7", benefic=True, confidence=1.0
            ))

    # ---- Raja Yogas (house-lord connections) ----
    for k_h in KENDRA:
        for ko_h in KONA:
            if k_h == ko_h:
                continue
            ok, lords = _lords_conjunct_or_exchange(k_h, ko_h, lagna_sign_idx, planet_rashis)
            if ok:
                detected.append(DetectedYoga(
                    name="Raja Yoga (Kendra-Kona)",
                    category="Raja",
                    description=RAJA_YOGAS[0]["effect"],
                    planets_involved=lords,
                    source="BPHS-Ch36", benefic=True, confidence=0.9,
                ))

    for h1, h2 in [(1, 4), (1, 10), (4, 7), (4, 10), (7, 10)]:
        ok, lords = _lords_conjunct_or_exchange(h1, h2, lagna_sign_idx, planet_rashis)
        if ok:
            detected.append(DetectedYoga(
                name="Raja Yoga (Mutual Kendra)",
                category="Raja",
                description=RAJA_YOGAS[1]["effect"],
                planets_involved=lords,
                source="BPHS-Ch36", benefic=True, confidence=0.9,
            ))

    for name, h1, h2, src in [
        ("Dharma-Karma Adhipati Yoga", 9, 10, "PD-Ch6"),
        ("Raja Yoga (4-9 Connection)", 4, 9, "SC-Ch8"),
        ("Raja Yoga (5-9 Connection)", 5, 9, "SC-Ch8"),
    ]:
        ok, lords = _lords_conjunct_or_exchange(h1, h2, lagna_sign_idx, planet_rashis)
        if ok:
            detected.append(DetectedYoga(
                name=name, category="Raja",
                description=f"Lords of {h1}th and {h2}th houses linked",
                planets_involved=lords,
                source=src, benefic=True, confidence=0.9,
            ))

    # ---- Dhana Yogas ----
    for h1, h2, label in [(2, 11, "2nd lord + 11th lord"), (2, 5, "2nd lord + 5th lord"), (2, 9, "2nd lord + 9th lord")]:
        ok, lords = _lords_conjunct_or_exchange(h1, h2, lagna_sign_idx, planet_rashis)
        if ok:
            detected.append(DetectedYoga(
                name=f"Dhana Yoga ({label})",
                category="Dhana",
                description=DHANA_YOGAS[0]["effect"],
                planets_involved=lords,
                source="PD-Ch7", benefic=True, confidence=0.9,
            ))

    lord5 = _get_house_lord(5, lagna_sign_idx)
    if lord5 in planet_rashis:
        h5 = planet_house(lord5)
        if h5 in KENDRA or h5 in KONA:
            detected.append(DetectedYoga(
                name="Dhana Yoga (5th lord in Kendra/Kona)",
                category="Dhana",
                description=DHANA_YOGAS[3]["effect"],
                planets_involved=[lord5],
                source="PD-Ch7", benefic=True, confidence=0.85,
            ))

    # ---- Neecha Bhanga Raja Yoga ----
    for p, rashi_idx in planet_rashis.items():
        if p not in DEBILITATION:
            continue
        if RASHIS[rashi_idx] != DEBILITATION[p]:
            continue
        debil_lord = _sign_lord(DEBILITATION[p])
        exalt_sign = EXALTATION.get(p, "")
        exalt_lord = _sign_lord(exalt_sign) if exalt_sign else ""
        cancelled = False
        if debil_lord in planet_rashis:
            if planet_house(debil_lord) in KENDRA or planet_house_from_moon(debil_lord) in KENDRA:
                cancelled = True
        if exalt_lord in planet_rashis and planet_rashis[exalt_lord] == rashi_idx:
            cancelled = True
        if cancelled:
            detected.append(DetectedYoga(
                name="Neecha Bhanga Raja Yoga",
                category="Raja",
                description=SC_YOGAS[1]["effect"],
                planets_involved=[p],
                source="BPHS-Ch36", benefic=True, confidence=0.85,
            ))

    # ---- Viparita Raja Yoga ----
    dusthana_lords = set()
    for house in [6, 8, 12]:
        lord = _get_house_lord(house, lagna_sign_idx)
        if lord in planet_rashis and planet_house(lord) in [6, 8, 12]:
            dusthana_lords.add(lord)
    if len(dusthana_lords) >= 2:
        detected.append(DetectedYoga(
            name="Viparita Raja Yoga", category="Raja",
            description="Success through adversity, triumph over enemies, wealth from unexpected sources",
            planets_involved=list(dusthana_lords),
            source="SC-Ch8", benefic=True, confidence=1.0
        ))

    # ---- Parivartana Yoga (Mutual Exchange) ----
    exchanges = []
    for p1 in planet_rashis:
        for p2 in planet_rashis:
            if p1 >= p2:
                continue
            if p1 not in PLANET_OWNERSHIP or p2 not in PLANET_OWNERSHIP:
                continue
            r1 = RASHIS[planet_rashis[p1]]
            r2 = RASHIS[planet_rashis[p2]]
            if r1 in PLANET_OWNERSHIP.get(p2, []) and r2 in PLANET_OWNERSHIP.get(p1, []):
                exchanges.append(f"{p1}-{p2}")
    if exchanges:
        detected.append(DetectedYoga(
            name="Parivartana Yoga", category="Raja",
            description=f"Mutual exchange between: {', '.join(exchanges)}",
            planets_involved=[p for pair in exchanges for p in pair.split("-")],
            source="SC-Ch8", benefic=True, confidence=1.0
        ))

    # ---- Nabhasa Yogas (classical seven grahas) ----
    graha_rashis = {p: planet_rashis[p] for p in CLASSICAL_GRAHAS if p in planet_rashis}
    if len(graha_rashis) >= 7:
        graha_houses = [planet_house(p) for p in graha_rashis]

        # Gada Yoga: all 7 grahas in exactly two successive angular houses (BPHS Ch.37 v.9)
        successive_kendra_pairs = [(1, 4), (4, 7), (7, 10), (10, 1)]
        for pair in successive_kendra_pairs:
            if all(h in pair for h in graha_houses):
                detected.append(DetectedYoga(
                    name="Gada Yoga", category="Nabhasa",
                    description=NABHASA_YOGAS[3]["effect"],
                    planets_involved=list(graha_rashis.keys()),
                    source="BPHS-Ch12-v9", benefic=True, confidence=0.85,
                ))
                break

        rashi_types = []
        for p_rashi in graha_rashis.values():
            if p_rashi in [0, 3, 6, 9]:
                rashi_types.append("movable")
            elif p_rashi in [1, 4, 7, 10]:
                rashi_types.append("fixed")
            else:
                rashi_types.append("dual")

        unique = set(rashi_types)
        if len(unique) == 1:
            if "movable" in unique:
                detected.append(DetectedYoga(
                    name="Rajju Yoga", category="Nabhasa",
                    description="Frequent travel, foreign residence, adventurous",
                    planets_involved=list(graha_rashis.keys()),
                    source="BPHS-Ch12", benefic=True, confidence=0.8,
                ))
            elif "fixed" in unique:
                detected.append(DetectedYoga(
                    name="Musala Yoga", category="Nabhasa",
                    description="Steady, determined, good at one profession",
                    planets_involved=list(graha_rashis.keys()),
                    source="BPHS-Ch12", benefic=True, confidence=0.8,
                ))
            elif "dual" in unique:
                detected.append(DetectedYoga(
                    name="Nala Yoga", category="Nabhasa",
                    description="Versatile, good at many skills, helpful",
                    planets_involved=list(graha_rashis.keys()),
                    source="BPHS-Ch12", benefic=True, confidence=0.8,
                ))

    # ---- Sankhya (Numerical) Nabhasa Yogas — PD-VB Ch.6 sl.39-41 ----
    # Based on how many distinct signs the 7 classical planets occupy.
    # These supersede (but do not exclude) Rajju/Musala/Nala which use sign-quality.
    if len(graha_rashis) >= 7:
        distinct_signs = len(set(graha_rashis.values()))
        sankhya_map = {
            7: ("Vallaki Yoga", "Fond of dance/music, greatly wealthy, cultural refinement, polymath", True, "PD-Ch6-sl39"),
            6: ("Dama Yoga", "Liberal, king, benefactor, philanthropic, highly communally reliable", True, "PD-Ch6-sl39"),
            5: ("Pasa Yoga", "Opulent, extensive networks, great skill in people-management", True, "PD-Ch6-sl40"),
            4: ("Kedara Yoga", "Wealth, agricultural lands, helps relatives, dutiful, honored", True, "PD-Ch6-sl40"),
            3: ("Sula Yoga", "Cruel, angry, focused single-mindedly, alternately prosperous", False, "PD-Ch6-sl41"),
            2: ("Yuga Yoga", "Heretical, without consistent wealth, dual-life choices, limited relatives", False, "PD-Ch6-sl41"),
            1: ("Gola Yoga", "Without wealth, sinful, low associates, short-lived, highly insular", False, "PD-Ch6-sl41"),
        }
        if distinct_signs in sankhya_map:
            y_name, y_desc, y_benefic, y_src = sankhya_map[distinct_signs]
            detected.append(DetectedYoga(
                name=y_name, category="Nabhasa",
                description=y_desc,
                planets_involved=list(graha_rashis.keys()),
                source=y_src, benefic=y_benefic, confidence=0.9,
            ))

    # ---- Mala Yoga and Sarpa Yoga — Hora Sara Ch.19 sl.43-45 ----
    # Mala: all three natural benefics (Jup, Ven, Mer) in Kendra from Lagna
    # Sarpa: all three natural malefics (Sun, Mars, Saturn) in Kendra from Lagna
    NATURAL_BENEFICS_TRIAD = {"Jupiter", "Venus", "Mercury"}
    NATURAL_MALEFICS_TRIAD = {"Sun", "Mars", "Saturn"}

    benefics_in_kendra = [
        p for p in NATURAL_BENEFICS_TRIAD
        if p in planet_rashis and planet_house(p) in KENDRA
    ]
    if set(benefics_in_kendra) == NATURAL_BENEFICS_TRIAD:
        detected.append(DetectedYoga(
            name="Mala Yoga", category="Nabhasa",
            description="All natural benefics in Kendras — learned, wealthy, unbroken material comfort",
            planets_involved=list(NATURAL_BENEFICS_TRIAD),
            source="HoraSara-Ch19-sl43", benefic=True, confidence=0.9,
        ))

    malefics_in_kendra = [
        p for p in NATURAL_MALEFICS_TRIAD
        if p in planet_rashis and planet_house(p) in KENDRA
    ]
    if set(malefics_in_kendra) == NATURAL_MALEFICS_TRIAD:
        detected.append(DetectedYoga(
            name="Sarpa Yoga", category="Nabhasa",
            description="All natural malefics in Kendras — penniless, talkative, troubles others, short-lived",
            planets_involved=list(NATURAL_MALEFICS_TRIAD),
            source="HoraSara-Ch19-sl44", benefic=False, confidence=0.9,
        ))

    # ---- Surya Yogas — Hora Sara Ch.19 sl.9-12 ----
    # Vesi: planet (not Moon) in 2nd from Sun
    # Vasi: planet (not Moon) in 12th from Sun
    # Ubhayachari: planets in both 2nd and 12th from Sun
    if "Sun" in planet_rashis:
        sun_rashi_idx = planet_rashis["Sun"]

        def planet_house_from_sun(planet: str) -> int:
            if planet not in planet_rashis:
                return -1
            return ((planet_rashis[planet] - sun_rashi_idx + 12) % 12) + 1

        planets_in_2nd_from_sun = [
            p for p in planet_rashis
            if p not in ("Sun", "Moon") and planet_house_from_sun(p) == 2
        ]
        planets_in_12th_from_sun = [
            p for p in planet_rashis
            if p not in ("Sun", "Moon") and planet_house_from_sun(p) == 12
        ]

        if planets_in_2nd_from_sun and planets_in_12th_from_sun:
            detected.append(DetectedYoga(
                name="Ubhayachari Yoga", category="Surya",
                description="Talkative, wise, strong, leader, dear to king, enthusiastic, eloquent",
                planets_involved=planets_in_2nd_from_sun + planets_in_12th_from_sun,
                source="HoraSara-Ch19-sl9", benefic=True, confidence=1.0,
            ))
        else:
            if planets_in_2nd_from_sun:
                detected.append(DetectedYoga(
                    name="Vesi Yoga", category="Surya",
                    description="Slow walk, soft-spoken, balanced income and outgo, dear to men",
                    planets_involved=planets_in_2nd_from_sun,
                    source="HoraSara-Ch19-sl9", benefic=True, confidence=1.0,
                ))
            if planets_in_12th_from_sun:
                # Qualifier: benefic planets give good results, malefic give bad
                has_benefic = any(p in BENEFICS for p in planets_in_12th_from_sun)
                detected.append(DetectedYoga(
                    name="Vasi Yoga", category="Surya",
                    description=(
                        "All comforts and wealth" if has_benefic
                        else "Sinful, defective-limbed, sleepy, laborious"
                    ),
                    planets_involved=planets_in_12th_from_sun,
                    source="HoraSara-Ch19-sl9", benefic=has_benefic, confidence=1.0,
                ))

    # ---- Lagna Yogas — Hora Sara Ch.19 sl.13-18 ----
    # Sushubha: non-luminary planet in 2nd from Lagna
    # Ashubha: non-luminary planet in 12th from Lagna
    # Karthari: malefics in BOTH 2nd and 12th from Lagna
    # Lagnadhi: benefics (Jup/Ven/Mer) in 6th, 7th, 8th from Lagna, free from malefic aspect
    non_luminaries = [
        p for p in planet_rashis if p not in ("Sun", "Moon")
    ]

    planets_in_2nd_lagna = [p for p in non_luminaries if planet_house(p) == 2]
    planets_in_12th_lagna = [p for p in non_luminaries if planet_house(p) == 12]

    # Karthari takes priority over Sushubha/Ashubha (malefic scissors)
    malefics_in_2nd = [p for p in planets_in_2nd_lagna if p in MALEFICS]
    malefics_in_12th = [p for p in planets_in_12th_lagna if p in MALEFICS]
    if malefics_in_2nd and malefics_in_12th:
        detected.append(DetectedYoga(
            name="Karthari Yoga", category="Lagna",
            description="Malefic scissors on Lagna: angry, hates parents, danger from poison/fire/weapons",
            planets_involved=malefics_in_2nd + malefics_in_12th,
            source="HoraSara-Ch19-sl16", benefic=False, confidence=0.9,
        ))
    else:
        if planets_in_2nd_lagna:
            detected.append(DetectedYoga(
                name="Sushubha Yoga", category="Lagna",
                description="Wealthy, principled, ever-active, head of monetary transactions",
                planets_involved=planets_in_2nd_lagna,
                source="HoraSara-Ch19-sl13", benefic=True, confidence=0.9,
            ))
        if planets_in_12th_lagna:
            detected.append(DetectedYoga(
                name="Ashubha Yoga", category="Lagna",
                description="Strong body, enthusiastic, charitable, dear to all, famous",
                planets_involved=planets_in_12th_lagna,
                source="HoraSara-Ch19-sl15", benefic=True, confidence=0.9,
            ))

    # Lagnadhi Yoga: benefics in 6th, 7th, 8th from Lagna (Hora Sara Ch.19 sl.17-18)
    # Rule: benefic participants free from Sun's conjunction (Hora Sara Ch.19 sl.6 notes for Adhi)
    lagnadhi_houses = {6, 7, 8}
    lagnadhi_planets: list[str] = []
    lagnadhi_found_houses: set[int] = set()
    for p in ("Jupiter", "Venus", "Mercury"):
        if p not in planet_rashis:
            continue
        # Exclude if combust (conjunct Sun in same rashi)
        if "Sun" in planet_rashis and planet_rashis[p] == planet_rashis["Sun"]:
            continue
        h = planet_house(p)
        if h in lagnadhi_houses:
            lagnadhi_found_houses.add(h)
            lagnadhi_planets.append(p)
    if lagnadhi_found_houses >= {6, 7, 8}:
        detected.append(DetectedYoga(
            name="Lagnadhi Yoga", category="Lagna",
            description="Minister, army chief, king, many wives, humble, long life, virtuous, enemy-free",
            planets_involved=lagnadhi_planets,
            source="HoraSara-Ch19-sl17", benefic=True, confidence=0.9,
        ))

    # ---- Mahabhagya Yoga — Phaladeepika Ch.6 sl.14-15 ----
    # Day birth male: Sun, Moon, Lagna all in odd signs (Aries=0, Gem=2, Leo=4, Lib=6, Sag=8, Aq=10)
    # Night birth female: Sun, Moon, Lagna all in even signs (Tau=1, Can=3, Vir=5, Sco=7, Cap=9, Pis=11)
    # ChartData only carries planet rashis; we can check Sun and Moon, and use lagna_sign_idx for Lagna.
    if "Sun" in planet_rashis and "Moon" in planet_rashis:
        sun_odd = (planet_rashis["Sun"] % 2 == 0)     # even index = odd sign (Aries=0 is odd)
        moon_odd = (planet_rashis["Moon"] % 2 == 0)
        lagna_odd = (lagna_sign_idx % 2 == 0)
        if sun_odd and moon_odd and lagna_odd:
            detected.append(DetectedYoga(
                name="Mahabhagya Yoga (day/male)",
                category="Raja",
                description="Immense pleasure, liberal, famous, ruler, 80-year life, spotless character",
                planets_involved=["Sun", "Moon"],
                source="PD-Ch6-sl14", benefic=True, confidence=0.85,
            ))
        sun_even = not sun_odd
        moon_even = not moon_odd
        lagna_even = not lagna_odd
        if sun_even and moon_even and lagna_even:
            detected.append(DetectedYoga(
                name="Mahabhagya Yoga (night/female)",
                category="Raja",
                description="Wealth, long-lived husband, sons, grandsons, lucky, well-behaved",
                planets_involved=["Sun", "Moon"],
                source="PD-Ch6-sl14", benefic=True, confidence=0.85,
            ))

    # ---- Sakata Yoga — Phaladeepika Ch.6 sl.17 ----
    # Moon in 6th, 8th, or 12th from Jupiter.
    # Cancelled if Moon is in Kendra from Lagna.
    if "Jupiter" in planet_rashis and "Moon" in planet_rashis:
        jup_rashi_idx = planet_rashis["Jupiter"]
        moon_from_jup = ((planet_rashis["Moon"] - jup_rashi_idx + 12) % 12) + 1
        if moon_from_jup in (6, 8, 12):
            moon_in_kendra_from_lagna = planet_house("Moon") in KENDRA
            if not moon_in_kendra_from_lagna:
                detected.append(DetectedYoga(
                    name="Sakata Yoga", category="Chandra",
                    description="Frequently loses fortune then may regain; ordinary, mental grief, insignificant",
                    planets_involved=["Moon", "Jupiter"],
                    source="PD-Ch6-sl17", benefic=False, confidence=0.85,
                ))
            else:
                detected.append(DetectedYoga(
                    name="Sakata Yoga (cancelled)", category="Chandra",
                    description="Sakata formed but cancelled — Moon in Kendra from Lagna",
                    planets_involved=["Moon", "Jupiter"],
                    source="PD-Ch6-sl17", benefic=True, confidence=0.8,
                ))

    # ---- Vasumati Yoga — Phaladeepika Ch.6 sl.19-20 ----
    # All three natural benefics (Jupiter, Venus, Mercury) in Upachaya houses (3,6,10,11) from Lagna or Moon.
    UPACHAYA = {3, 6, 10, 11}
    vasumati_from_lagna = all(
        p in planet_rashis and planet_house(p) in UPACHAYA
        for p in ("Jupiter", "Venus", "Mercury")
    )
    vasumati_from_moon = (
        moon_rashi_idx is not None and all(
            p in planet_rashis and planet_house_from_moon(p) in UPACHAYA
            for p in ("Jupiter", "Venus", "Mercury")
        )
    )
    if vasumati_from_lagna or vasumati_from_moon:
        basis = "Lagna" if vasumati_from_lagna else "Moon"
        detected.append(DetectedYoga(
            name="Vasumati Yoga", category="Dhana",
            description=f"All benefics in Upachaya from {basis} — commands plenty of money, always at home in comfort",
            planets_involved=["Jupiter", "Venus", "Mercury"],
            source="PD-Ch6-sl19", benefic=True, confidence=0.9,
        ))

    # ---- Amala Yoga — Phaladeepika Ch.6 sl.19-20 ----
    # Benefic planet (Jupiter, Venus, or Mercury) in 10th from Lagna or Moon, unafflicted.
    amala_planets: list[str] = []
    for p in ("Jupiter", "Venus", "Mercury"):
        if p not in planet_rashis:
            continue
        if planet_house(p) == 10:
            amala_planets.append(p)
        elif moon_rashi_idx is not None and planet_house_from_moon(p) == 10:
            if p not in amala_planets:
                amala_planets.append(p)
    if amala_planets:
        detected.append(DetectedYoga(
            name="Amala Yoga", category="Raja",
            description="Rules the earth, wealthy, famous, prosperous, prudent, untarnished career",
            planets_involved=amala_planets,
            source="PD-Ch6-sl20", benefic=True, confidence=0.9,
        ))

    # ---- Saraswati Yoga — Phaladeepika Ch.6 sl.26-27 ----
    # Venus, Jupiter, Mercury in Kendra/Trikona/2nd; Jupiter additionally in exaltation/own/friendly sign.
    KENDRA_TRIKONA_2 = set(KENDRA) | set(KONA) | {2}
    svj_in_position = all(
        p in planet_rashis and planet_house(p) in KENDRA_TRIKONA_2
        for p in ("Venus", "Jupiter", "Mercury")
    )
    if svj_in_position and "Jupiter" in planet_rashis:
        jup_rashi = RASHIS[planet_rashis["Jupiter"]]
        jup_dignified = (
            jup_rashi in PLANET_OWNERSHIP.get("Jupiter", [])
            or jup_rashi == EXALTATION.get("Jupiter")
        )
        if jup_dignified:
            detected.append(DetectedYoga(
                name="Saraswati Yoga", category="Raja",
                description="Highly intelligent, clever in drama/poetry/prose, famous, wealthy, respected by kings",
                planets_involved=["Venus", "Jupiter", "Mercury"],
                source="PD-Ch6-sl26", benefic=True, confidence=0.9,
            ))

    # ---- Harsha / Sarala / Vimala Yogas — Phaladeepika Ch.6 sl.57, 63, 65 ----
    # Distinct from Viparita Raja Yoga (which requires two dusthana lords).
    # Each is a single dusthana lord sitting in its OWN dusthana house.
    for house, yoga_name, description, src in [
        (6, "Harsha Yoga",
         "Happiness, enjoyment, good fortune, strong constitution, overcomes enemies",
         "PD-Ch6-sl57"),
        (8, "Sarala Yoga",
         "Long-lived, resolute, fearless, prosperous, overcomes foes, celebrated, pure",
         "PD-Ch6-sl63"),
        (12, "Vimala Yoga",
         "Spends little, saves much, good to all, happy, independent, respectable profession",
         "PD-Ch6-sl65"),
    ]:
        lord = _get_house_lord(house, lagna_sign_idx)
        if lord in planet_rashis and planet_house(lord) == house:
            detected.append(DetectedYoga(
                name=yoga_name, category="Raja",
                description=description,
                planets_involved=[lord],
                source=src, benefic=True, confidence=1.0,
            ))

    # ---- Pushkala Yoga — Hora Sara Ch.20 sl.12-13 ----
    # Moon's dispositor (sign lord of Moon's rashi) conjoined with Lagna lord in a friendly Kendra.
    # "Friendly Kendra" = a Kendra house where the lord of that house is friendly to the Lagna lord.
    # We use: Moon's dispositor and Lagna lord occupy the same house AND that house is a Kendra.
    if moon_rashi_idx is not None:
        moon_rashi_name = RASHIS[moon_rashi_idx]
        moon_dispositor = _sign_lord(moon_rashi_name)
        lagna_lord = _get_house_lord(1, lagna_sign_idx)
        if (moon_dispositor and lagna_lord
                and moon_dispositor in planet_rashis
                and lagna_lord in planet_rashis
                and moon_dispositor != lagna_lord):
            if planet_rashis[moon_dispositor] == planet_rashis[lagna_lord]:
                if planet_house(moon_dispositor) in KENDRA:
                    detected.append(DetectedYoga(
                        name="Pushkala Yoga", category="Raja",
                        description="Lords over earth; royal scion; exquisite speech; executive governance",
                        planets_involved=[moon_dispositor, lagna_lord],
                        source="HoraSara-Ch20-sl12", benefic=True, confidence=0.9,
                    ))

    # ---- Sanyas Yoga — Sarvartha Chintamani Ch.8 sl.1-4 ----
    # Four or more planets together in a Kendra house.
    for kendra_h in KENDRA:
        planets_in_k = [p for p in planet_rashis if planet_house(p) == kendra_h]
        if len(planets_in_k) >= 4:
            detected.append(DetectedYoga(
                name="Sanyas Yoga", category="Spiritual",
                description="Renunciation, ascetic orders, spiritual vocation",
                planets_involved=planets_in_k,
                source="SC-Ch8-sl1", benefic=True, confidence=0.85,
            ))
            break  # one instance suffices

    return detected
