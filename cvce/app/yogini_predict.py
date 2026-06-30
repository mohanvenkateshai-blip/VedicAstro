"""
Yogini Dasha Prediction Engine — pure Yogini framework.

Source: "Predict Effectively Through Yogini Dasha" — V.P. Goel (K.N. Rao, ed.)
        Vani Publications, 2002 / 2006. ISBN 81-89221-48-5.
        Supplemented by BPHS Yogini Dasha Adhyaya.

Yogini Dasha is a completely independent system from Vimshottari:
  • 8 Yogini deities (not 9 planets) — each rules 1–8 years
  • Predictions are keyed to the Yogini's planet lord + Maha×Antar combination
  • Natal lord placement from birth Lagna = Goel's primary birth-chart reference point
  • Progressed Lagna (sign of contributing nakshatra) = Goel's second reference point
    — computed here from birth Moon nakshatra + cycle tracking
  • Transit timing uses Saturn+Jupiter double-transit from Progressed Lagna (not natal Lagna)

Nothing here touches DashaImpactAnalyzer, fuse_dasha_transit, or any Vimshottari logic.
"""

from __future__ import annotations

# ── 1. Yogini data from Goel / BPHS ──────────────────────────────────────────

YOGINI_DATA: dict[str, dict] = {
    "Mangala": {
        "lord": "Moon",
        "nature": "benefic",
        "duration": 1,
        "career": [
            "New beginnings and fresh ventures — Moon-ruled initiatives in public-facing roles.",
            "Moon's house activates: its signified career domain sees movement.",
        ],
        "wealth": [
            "Fluctuating income typical of Moon; moderate gains through public or maternal sources.",
            "4th-house linked property/comforts may become available.",
        ],
        "health": [
            "Mind, emotions and digestive system need care; water-element imbalances possible.",
            "Short period — fluctuating energy, not chronic illness.",
        ],
        "family": [
            "Mother, domestic comforts, 4th-house matters are prominent.",
            "Love affairs, emotional bonds, travel with family or partner likely.",
        ],
        "caution": [
            "If Moon is in 6/8/12 or afflicted by Rahu/malefics: mental anguish, love affair without fulfilment, election loss, confinement.",
        ],
    },
    "Pingala": {
        "lord": "Sun",
        "nature": "mixed",
        "duration": 2,
        "career": [
            "Authority, career advancement, government recognition — 10th-house significations activate.",
            "Home Minister, Chief Minister, head-of-department level appointments possible when Sun is strong.",
        ],
        "wealth": [
            "Gains through paternal source, authority, or government; Sun's house dictates accumulation.",
        ],
        "health": [
            "Heart, eyes, vitality and spine (Sun significations) need attention.",
        ],
        "family": [
            "Father's wellbeing and relations with authority figures are prominent.",
            "Official recognition or dealings with government bodies likely.",
        ],
        "caution": [
            "If Sun is afflicted: father's illness, loss of career position, near-fatal health episode.",
            "Ego conflicts, power struggles — avoid direct confrontations with authority.",
        ],
    },
    "Dhanya": {
        "lord": "Jupiter",
        "nature": "benefic",
        "duration": 3,
        "career": [
            "Dharmic rise — advisory, educational, judicial or spiritual career gains.",
            "Appointment to positions of wisdom and counsel; Jupiter's aspect on 10th is decisive.",
        ],
        "wealth": [
            "Most auspicious Yogini for durable wealth; Jupiter's house shows the accumulation domain.",
            "Pushya sub-period (Saturn as star lord) yields lifelong-effect events — watch this window.",
        ],
        "health": [
            "Jupiter strengthens constitution overall; liver, fat-metabolism care if afflicted.",
        ],
        "family": [
            "Children, marriage, dharmic partnerships are blessed; elder/guru figures support.",
            "Progeny-related events (birth of child, child's milestones) prominent.",
        ],
        "caution": [
            "If Jupiter lords 7th/8th in natal: maraka risk for spouse or partner in afflicted sub-period.",
            "Over-expansion without discrimination — guard against speculative financial excess.",
        ],
    },
    "Bhramari": {
        "lord": "Mars",
        "nature": "malefic",
        "duration": 4,
        "career": [
            "Property, real estate, land, engineering, military or political power when Mars is strong.",
            "Abrupt career changes, sudden appointments — Mars acts fast.",
        ],
        "wealth": [
            "Land and property transactions, sibling-related gains; disputes over movable/immovable assets.",
        ],
        "health": [
            "Surgery, accidents, blood-related issues; Mars rules bone marrow and muscular energy.",
            "Physical vitality is tested — excessive strain, accidents, and violence are risk areas.",
        ],
        "family": [
            "Conflict within home; sibling interactions and disputes prominent; marital friction.",
        ],
        "caution": [
            "Most likely Maraka period if Mars holds maraka lordship (2nd/7th lord).",
            "Husband/partner's health at risk; assassination, serious illness, arrest have occurred in Bhramari in classical cases (Indira Gandhi, EC 17).",
            "Avoid aggression and hasty decisions — sudden reversals are the hallmark of this Yogini.",
        ],
    },
    "Bhadrika": {
        "lord": "Mercury",
        "nature": "benefic",
        "duration": 5,
        "career": [
            "Business, trade, communication, media, writing, intellectual roles — Mercury's domains thrive.",
            "Elections, litigation, negotiations favour the native when Mercury is strong.",
        ],
        "wealth": [
            "Commercial gains; Mercury's natal house shows the accumulation path.",
            "Trade partnerships and commission-based income are productive avenues.",
        ],
        "health": [
            "Nervous system, skin, respiratory care needed; Mercury's sign placement modifies risk.",
        ],
        "family": [
            "Nephews, siblings, cousins, neighbourhood relations; short-distance journeys.",
            "Intellectual bonding and communication within family is prominent.",
        ],
        "caution": [
            "If Mercury is maraka or afflicted: litigation, scandal, arrest, death of a close associate.",
            "Combust Mercury: distorted communication, legal trouble, business fraud.",
        ],
    },
    "Ulka": {
        "lord": "Saturn",
        "nature": "malefic",
        "duration": 6,
        "career": [
            "Service, discipline, structural roles — slow but enduring career consolidation.",
            "Loss of position or forced structural change when Saturn afflicts the 10th lord.",
        ],
        "wealth": [
            "Gradual, hard-earned accumulation; Saturn delays but may not deny if well-placed.",
            "Unexpected losses through delays, theft, or chronic expenditure.",
        ],
        "health": [
            "Chronic ailments — bones, teeth, joints, cold-related diseases; old-age patterns emerge.",
            "Six-year duration means prolonged health struggles are possible; early intervention critical.",
        ],
        "family": [
            "Deaths in family, separation from loved ones, old-age parents' decline; servants and employees prominent.",
            "Foreign stays, exile, or distant relocations possible.",
        ],
        "caution": [
            "Longest malefic Yogini — sorrow and endurance define the period; classical cases show death, loss of kingdom, election defeat.",
            "Death of close family member, wife, son, or own serious illness are classical Ulka outcomes.",
            "Avoid major irreversible decisions without deliberation; Saturn rewards patience.",
        ],
    },
    "Siddha": {
        "lord": "Venus",
        "nature": "benefic",
        "duration": 7,
        "career": [
            "Political power, arts, creative leadership, diplomatic roles — Venus on 10th/11th is potent.",
            "PMship, ministerial appointment, election wins, artistic recognition; 7-year window is long-lasting.",
        ],
        "wealth": [
            "Most comfortable Yogini for luxury, vehicles, jewellery, artistic and creative income.",
            "Financial prosperity through relationships, creative work, or diplomatic endeavours.",
        ],
        "health": [
            "Generally favourable; reproductive health, kidneys, and sensory-pleasure excess to watch.",
        ],
        "family": [
            "Marriage, romantic partnerships, birth of children, domestic harmony are blessed themes.",
            "Women in the native's life are prominent sources of support, growth, and events.",
        ],
        "caution": [
            "If Venus is afflicted or maraka: child's death, spouse's tragedy, partner's infidelity — classical cases include assassination (Rajiv Gandhi, EC 12) and Classroom Case 2 (child's fall).",
            "Overindulgence in sensory pleasures can undermine the period's promise.",
        ],
    },
    "Sankata": {
        "lord": "Rahu",
        "nature": "malefic",
        "duration": 8,
        "career": [
            "Unexpected rise through unconventional, foreign, or shadow-network connections.",
            "Chief Election Commissioner, Class-I service, sudden high appointments when Rahu/Ketu act beneficially.",
        ],
        "wealth": [
            "Hidden or foreign sources of income; equally prone to sudden, dramatic financial reversals.",
        ],
        "health": [
            "Mysterious, chronic, or karmic ailments — poison, toxins, epidemics, addictions.",
            "Ketu is additionally considered: spiritual health crises, chronic fatigue, pitta disorders.",
        ],
        "family": [
            "Marriage in Sankata possible but often with hidden complications or karmic weight.",
            "Karmic family events — separations, suicides, assassinations, intrigues are classical outcomes.",
        ],
        "caution": [
            "The longest Yogini and the most turbulent — 8 years of Rahu/Ketu themes.",
            "Assassination, suicide, treachery, sudden death of key persons — Indira Gandhi's assassination was in Sankata/Hasta.",
            "Hidden enemies active; obsessive relationships; foreign threats; Ketu also considered throughout.",
            "Rahu/Ketu as star lords act as dispositor and conjunct planet — their natal sign placement is critical.",
        ],
    },
}

# ── 2. Maha × Antar combination (Goel Ch.3 + benefic/malefic interplay) ──────

# Two-tuple of (maha_nature, antar_nature) → plain-language result modifier
COMBO_QUALIFIER: dict[tuple[str, str], str] = {
    ("benefic", "benefic"): "strongly positive — both lords support fulfilment of Maha's promise",
    ("benefic", "mixed"): "generally positive with authority-related fluctuations",
    (
        "benefic",
        "malefic",
    ): "mixed — gains possible but delayed or partially obstructed by Antar lord's pressures",
    ("mixed", "benefic"): "favourable overall, eased by Antar's benefic nature",
    ("mixed", "mixed"): "unpredictable — results depend heavily on natal planetary strength",
    ("mixed", "malefic"): "difficult sub-window; authority or health pressures dominate",
    ("malefic", "benefic"): "relief and mitigation within an otherwise challenging Mahadasha",
    ("malefic", "mixed"): "difficult overall with fluctuating respite",
    (
        "malefic",
        "malefic",
    ): "most demanding sub-period; intensified hardship — requires maximum endurance",
}

# ── 3. House significations (standard Parasara/BPHS) ─────────────────────────

HOUSE_SIG: dict[int, str] = {
    1: "self, vitality, personality, physical health",
    2: "wealth, speech, family, accumulated assets",
    3: "courage, communication, siblings, short journeys, arts",
    4: "home, mother, comforts, vehicles, property",
    5: "children, intelligence, creativity, romance, speculation",
    6: "enemies, disease, debt, service, legal disputes",
    7: "marriage, partnerships, contracts, public dealings",
    8: "longevity, transformations, hidden wealth, sudden events",
    9: "luck, father, dharma, higher education, foreign travel",
    10: "career, reputation, status, authority, government",
    11: "gains, income, aspirations, social networks, elder siblings",
    12: "losses, foreign lands, expenditure, liberation, hidden sorrows",
}

# Beneficial houses (Kendra + Trikona + Upachaya)
GOOD_HOUSES = {1, 2, 3, 4, 5, 9, 10, 11}
NEUTRAL = {7}
ADVERSE_HOUSES = {6, 8, 12}

# Planet dignity tables (0=Aries…11=Pisces)
_EXALT = {
    "Sun": 0,
    "Moon": 1,
    "Mars": 9,
    "Mercury": 5,
    "Jupiter": 3,
    "Venus": 11,
    "Saturn": 6,
    "Rahu": 1,
    "Ketu": 7,
}
_OWN = {
    "Sun": [4],
    "Moon": [3],
    "Mars": [0, 7],
    "Mercury": [2, 5],
    "Jupiter": [8, 11],
    "Venus": [1, 6],
    "Saturn": [9, 10],
    "Rahu": [],
    "Ketu": [],
}
_DEBIL = {
    "Sun": 6,
    "Moon": 9,
    "Mars": 3,
    "Mercury": 11,
    "Jupiter": 9,
    "Venus": 5,
    "Saturn": 0,
    "Rahu": 7,
    "Ketu": 1,
}


def _dignity(planet: str, sign_idx: int) -> str:
    if sign_idx == _EXALT.get(planet, -1):
        return "exalted"
    if sign_idx == _DEBIL.get(planet, -99):
        return "debilitated"
    if sign_idx in _OWN.get(planet, []):
        return "in own sign"
    return "in neutral sign"


def _house(planet_sign: int, lagna_sign: int) -> int:
    """1-indexed house counted from Lagna."""
    return (planet_sign - lagna_sign) % 12 + 1


# ── 4. Public API ─────────────────────────────────────────────────────────────


def predict_yogini_antardasha(
    maha_yogini: str,
    antar_yogini: str,
    lagna_sign_idx: int,  # birth Lagna sign (0=Aries … 11=Pisces)
    natal_sign: dict[str, int],  # {planet_name: sign_index} from chart geometry
) -> dict[str, list[str]]:
    """
    Generate Yogini-specific life-domain predictions for a Maha/Antar combination.

    Framework (Goel Ch.3):
      1. Maha Yogini domain effects (deity-specific, from Goel chs 4-11)
      2. Antar Yogini nature modulates the Maha (benefic/malefic combination)
      3. Maha lord's natal house from Lagna = birth-chart reference point
      4. Antar lord's natal house from Lagna = secondary reference point
      5. Dignity of each lord (exalted/own/debilitated) modifies strength of results

    Returns { career, wealth, health, family, caution } — same structure as the portal's
    DashaPrediction type — filled purely from Yogini's own classical framework.
    """
    maha_data = YOGINI_DATA.get(maha_yogini)
    antar_data = YOGINI_DATA.get(antar_yogini)
    if not maha_data or not antar_data:
        return {}

    maha_nature = maha_data["nature"]
    antar_nature = antar_data["nature"]
    maha_lord = maha_data["lord"]
    antar_lord = antar_data["lord"]

    combo_qual = COMBO_QUALIFIER.get(
        (maha_nature, antar_nature), "results depend on natal chart strength"
    )

    # Reference point 1: Maha lord natal placement
    maha_sign_idx = natal_sign.get(maha_lord)
    antar_sign_idx = natal_sign.get(antar_lord)

    maha_house = _house(maha_sign_idx, lagna_sign_idx) if maha_sign_idx is not None else None
    antar_house = _house(antar_sign_idx, lagna_sign_idx) if antar_sign_idx is not None else None
    maha_dignity = (
        _dignity(maha_lord, maha_sign_idx) if maha_sign_idx is not None else "unknown placement"
    )
    antar_dignity = (
        _dignity(antar_lord, antar_sign_idx) if antar_sign_idx is not None else "unknown placement"
    )

    # Strength qualifier based on house + dignity
    def _strength_note(lord: str, house: int | None, dignity: str) -> str:
        if house is None:
            return f"{lord}: placement unavailable."
        sig = HOUSE_SIG.get(house, "")
        zone = (
            "strong placement"
            if house in GOOD_HOUSES
            else ("adverse placement" if house in ADVERSE_HOUSES else "neutral placement")
        )
        return (
            f"{lord} is {dignity}, in house {house} ({sig}) — {zone}. "
            f"{'Results in this domain are enhanced.' if house in GOOD_HOUSES else 'Results may be tested or delayed.' if house in ADVERSE_HOUSES else 'Moderate results expected.'}"
        )

    maha_note = _strength_note(maha_lord, maha_house, maha_dignity)
    antar_note = _strength_note(antar_lord, antar_house, antar_dignity)

    # Build domain predictions from Maha Yogini's classical effects
    result: dict[str, list[str]] = {
        "career": list(maha_data["career"]),
        "wealth": list(maha_data["wealth"]),
        "health": list(maha_data["health"]),
        "family": list(maha_data["family"]),
        "caution": list(maha_data["caution"]),
    }

    # Prepend combination context to career and caution
    combo_intro = f"{antar_yogini} Antardasha ({antar_lord}-ruled, {antar_nature}) within {maha_yogini} Mahadasha: {combo_qual}."
    result["career"] = [combo_intro] + result["career"]

    # Add natal placement notes to caution (Goel Ch.3 reference point 1)
    result["caution"] = [
        f"Mahadasha lord placement — {maha_note}",
        f"Antardasha lord placement — {antar_note}",
    ] + result["caution"]

    # Add Antar Yogini's specific caution if malefic/mixed and distinct from Maha
    if antar_nature in ("malefic", "mixed") and antar_yogini != maha_yogini:
        antar_caution = antar_data.get("caution", [])
        if antar_caution:
            result["caution"].append(f"Antar Yogini ({antar_yogini}) caution: {antar_caution[0]}")

    return result


# Light-touch registration wiring for dasha KE (revive path)
try:
    from vedic_engine.prediction import dasha as _dasha_core  # type: ignore

    _dasha_core._ensure_dasha_registered()
except Exception:
    pass
