"""
Yoga Detection Module — Identifies classical planetary combinations (Yogas)

Sources:
  - BPHS Ch.35-36 (Raja Yogas, Nabhasa Yogas)
  - Phaladeepika Ch.6-7 (Yogas)
  - Sarvartha Chintamani Ch.8 (Raja Yogas)
  - Hora Sara Ch.7 (Chandra Yogas)

Each yoga has:
  - conditions: dict of planet→sign relationships
  - effect: description of the yoga's results
  - source: text reference
  - confidence: 1.0 (direct) or 0.7 (partial match)
"""

from dataclasses import dataclass, field
from typing import Optional

from ..core.panchanga import RASHIS, NAKSHATRAS


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
        "condition": "All planets in Kendra (1,4,7,10) OR two adjacent Kendras",
        "effect": "Wealthy, strong, respected, authoritative",
        "source": "BPHS-Ch12",
    },
    {
        "name": "Shankha Yoga",
        "condition": "All planets in Panaphara (2,5,8,11) and Apoklima (3,6,9,12) — one in each type",
        "effect": "Learned in scriptures, charitable, long-lived, wealthy, enjoys life",
        "source": "BPHS-Ch12",
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

        # Adhi Yoga: benefic in each of 6th, 7th, and 8th from Moon
        benefic_houses_678: set[int] = set()
        adhi_planets: list[str] = []
        for p in planet_rashis:
            if p in BENEFICS and p != "Moon":
                h = planet_house_from_moon(p)
                if h in (6, 7, 8):
                    benefic_houses_678.add(h)
                    adhi_planets.append(p)
        if benefic_houses_678 >= {6, 7, 8}:
            detected.append(DetectedYoga(
                name="Adhi Yoga", category="Chandra",
                description="Leadership, authority, prosperity, respected, powerful",
                planets_involved=adhi_planets,
                source="BPHS-Ch35", benefic=True, confidence=1.0
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
                name="Lakshmi Yoga", category="Dhana",
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

        if all(h in KENDRA for h in graha_houses):
            detected.append(DetectedYoga(
                name="Gada Yoga", category="Nabhasa",
                description=NABHASA_YOGAS[3]["effect"],
                planets_involved=list(graha_rashis.keys()),
                source="BPHS-Ch12", benefic=True, confidence=0.85,
            ))

        in_pana = all(h in PANAPHARA for h in graha_houses)
        in_apo = all(h in APOKLIMA for h in graha_houses)
        mixed_ps = (
            any(h in PANAPHARA for h in graha_houses)
            and any(h in APOKLIMA for h in graha_houses)
            and all(h in PANAPHARA + APOKLIMA for h in graha_houses)
        )
        if in_pana or in_apo or mixed_ps:
            detected.append(DetectedYoga(
                name="Shankha Yoga", category="Nabhasa",
                description=NABHASA_YOGAS[4]["effect"],
                planets_involved=list(graha_rashis.keys()),
                source="BPHS-Ch12", benefic=True, confidence=0.8,
            ))

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

    return detected
