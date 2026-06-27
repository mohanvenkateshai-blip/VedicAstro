"""
Transit (Gochar) Rules — Extracted from Gochar Phaladeepika (Pulippani)

All rules are tagged with their source text for traceability.
Each rule is an IF-THEN predicate with a confidence score.

Key Sources:
  - GPD = Gochar Phaladeepika (main source)
  - PD  = Phaladeepika (Mantreswara)
  - HS  = Hora Sara (Prithuyasas)
  - BPHS = Brihat Parasara Hora Sastra
"""

from typing import Optional

# =====================================================================
# RULE 1: Good/Bad Houses from Janma Rasi (Gochar Phaladeepika, Table 12)
# =====================================================================

TRANSIT_HOUSES = {
    "Sun": {
        "good": [3, 6, 10, 11],
        "bad": [1, 2, 4, 8, 9, 12],
        "worst": [5],
        "source": "GPD-Ch10-Table12",
        "neutral": []  # houses 7
    },
    "Moon": {
        "good": [1, 3, 6, 7, 10, 11],
        "bad": [2, 4, 5, 12],
        "worst": [8],
        "source": "GPD-Ch10-Table12",
        "neutral": [9]  # house 9
    },
    "Mars": {
        "good": [3, 6, 11],
        "bad": [1, 2, 5, 7, 8, 9, 10, 12],
        "worst": [7],
        "source": "GPD-Ch10-Table12",
        "neutral": [4]
    },
    "Mercury": {
        "good": [6, 8, 10, 11],
        "bad": [1, 2, 3, 4, 5, 7, 9, 12],
        "worst": [1],
        "source": "GPD-Ch10-Table12",
        "neutral": []
    },
    "Jupiter": {
        "good": [2, 5, 7, 9, 11],
        "bad": [1, 3, 4, 6, 8, 10, 12],
        "worst": [3],
        "source": "GPD-Ch10-Table12",
        "neutral": []
    },
    "Venus": {
        "good": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "bad": [7, 10],
        "worst": [6],
        "source": "GPD-Ch10-Table12",
        "neutral": []
    },
    "Saturn": {
        "good": [3, 6, 9, 11],
        "bad": [2, 4, 5, 7, 8, 12],
        "worst": [1],
        "source": "GPD-Ch10-Table12",
        "neutral": [10]
    },
    "Rahu": {
        "good": [3, 6, 11],
        "bad": [1, 2, 4, 7, 8, 10, 12],
        "worst": [9],
        "source": "GPD-Ch10-Table12",
        "neutral": [5]
    },
    "Ketu": {
        "good": [3, 6, 11],
        "bad": [1, 2, 4, 7, 8, 10, 12],
        "worst": [9],
        "source": "GPD-Ch10-Table12",
        "neutral": [5]
    },
}

# =====================================================================
# RULE 2: Exaltation/Debilitation override (GPD Ch.10)
# =====================================================================
# "A planet in own sign or exaltation in natal chart gives no unavoidable evil
#  even in bad transit. A planet in debilitation/enemy sign gives no good even
#  in favourable transit."

EXALT_SIGN = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
    "Saturn": "Libra"
}

DEBIL_SIGN = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
    "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
    "Saturn": "Aries"
}

OWN_SIGN = {
    "Sun": ["Leo"], "Moon": ["Cancer"], "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"], "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"], "Saturn": ["Capricorn", "Aquarius"],
}

# =====================================================================
# RULE 3: Latta (Star Affliction) — GPD Ch.1.6
# =====================================================================

LATTA_RULES = {
    # Forward Latta (Puro Latta)
    "Sun": (12, +1, "Complete business ruined", "GPD-Ch1.6"),
    "Mars": (3, +1, "Death-class ruin; injury, accident, sibling conflict", "GPD-Ch1.6"),
    "Jupiter": (6, +1, "Death, misery to relations, fear", "GPD-Ch1.6"),
    "Saturn": (8, +1, "Many difficulties, danger to life", "GPD-Ch1.6"),
    # Rear Latta (Prustha Latta)
    "Venus": (5, -1, "Quarrels, marital disharmony", "GPD-Ch1.6"),
    "Mercury": (7, -1, "Loss of status, career collapse", "GPD-Ch1.6"),
    "Rahu": (9, -1, "Difficulties of all kinds, deception", "GPD-Ch1.6"),
    "Moon": (22, -1, "Humiliation, loss of honour, mental anxiety", "GPD-Ch1.6"),
    # Ketu mirrors Rahu (GPD convention — nodes share star-affliction logic)
    "Ketu": (9, -1, "Difficulties, sudden reversals, karmic obstacles", "GPD-Ch1.6"),
}

# =====================================================================
# RULE 4: Moorthy Nirnaya (GPD Ch.25 + HS Ch.11)
# =====================================================================
# Moon's position from Janma Rasi determines transit quality (Gochar Phaladeepika Ch.25).
# Houses 1,6,11=Swarna(Gold) | 2,5,9=Rajatha(Silver) | 3,7,10=Thambra(Copper) | 4,8,12=Loha(Iron)

MOORTHI_RESULTS = {
    1: ("Swarna (Gold)", "shubh", "Excellent — success, wealth, honour"),
    2: ("Rajatha (Silver)", "shubh", "Good — moderate success, comfort"),
    3: ("Thambra (Copper)", "ashubh", "Poor — obstacles, worries"),
    4: ("Loha (Iron)", "ashubh", "Worst — severe difficulties, loss"),
    5: ("Rajatha (Silver)", "shubh", "Good — moderate success, comfort"),
    6: ("Swarna (Gold)", "shubh", "Excellent — success, wealth, honour"),
    7: ("Thambra (Copper)", "ashubh", "Poor — obstacles, worries"),
    8: ("Loha (Iron)", "ashubh", "Worst — severe difficulties, loss"),
    9: ("Rajatha (Silver)", "shubh", "Good — moderate success, comfort"),
    10: ("Thambra (Copper)", "ashubh", "Poor — obstacles, worries"),
    11: ("Swarna (Gold)", "shubh", "Excellent — success, wealth, honour"),
    12: ("Loha (Iron)", "ashubh", "Worst — severe difficulties, loss"),
}

# =====================================================================
# RULE 5: Sade Sati / Saturn Transits (GPD Ch.26)
# =====================================================================
# Saturn's transit through 12th, 1st, and 2nd from Janma Rasi
# Total period: 7.5 years (2.5 years per sign)

SADE_SATI_PHASES = {
    "rise": {  # Saturn entering 12th from Janma Rasi
        "name": "Rising Phase (1st 2.5 years)",
        "effect": "Mental stress, financial pressure, health concerns begin",
        "severity": "moderate"
    },
    "peak": {  # Saturn in 1st (Janma Rasi) — middle 2.5 years
        "name": "Peak Phase (middle 2.5 years)",
        "effect": "Maximum difficulty — job loss, family strife, health crisis, financial drain",
        "severity": "severe"
    },
    "setting": {  # Saturn entering 2nd from Janma Rasi
        "name": "Setting Phase (last 2.5 years)",
        "effect": "Recovery period — gradual relief, lessons learned, rebuilding",
        "severity": "moderate"
    },
}

# =====================================================================
# RULE 6: Gochara Vedha (Cancellation) — GPD Ch.22
# =====================================================================
# When a planet's good transit is cancelled by another planet in a specific house

GOCHARA_VEDHA = {
    "Sun": {  # When Sun is in good house, planet in vedha house cancels it
        "vedha": {3: 12, 6: 5, 10: 8, 11: 9},
        "source": "GPD-Ch22"
    },
    "Moon": {"vedha": {1: 5, 3: 9, 6: 12, 7: 2, 10: 4, 11: 8}, "source": "GPD-Ch22"},
    "Mars": {"vedha": {3: 12, 6: 5, 11: 9}, "source": "GPD-Ch22"},
    "Mercury": {"vedha": {6: 2, 8: 4, 10: 1, 11: 9}, "source": "GPD-Ch22"},
    "Jupiter": {"vedha": {2: 12, 5: 4, 7: 3, 9: 10, 11: 8}, "source": "GPD-Ch22"},
    "Venus": {"vedha": {1: 8, 2: 7, 3: 1, 4: 10, 5: 9, 8: 5, 9: 11, 11: 3, 12: 6}, "source": "GPD-Ch22"},
    "Saturn": {"vedha": {3: 12, 6: 9, 9: 5, 11: 11}, "source": "GPD-Ch22"},
}

# Vipareetha Vedha: malefic transit nullified by planet in specific house
VIPAREETHA_VEDHA = {
    "Sun": {1: 3, 2: 4, 4: 8, 5: 9, 8: 10, 9: 11, 12: 12},
    "Moon": {2: 4, 4: 8, 5: 9, 12: 12},
    "Mars": {1: 3, 2: 4, 5: 9, 8: 10, 9: 11, 12: 12},
    "Mercury": {1: 3, 2: 4, 3: 6, 4: 8, 5: 9, 7: 10, 9: 11, 12: 12},
    "Jupiter": {1: 3, 3: 6, 4: 8, 6: 5, 8: 10, 10: 11, 12: 12},
    "Venus": {7: 10, 10: 11},
    "Saturn": {2: 4, 4: 8, 5: 9, 7: 10, 8: 10, 12: 12},
}

# =====================================================================
# RULE 7: Stellar Occupational (Tara) — GPD Ch.24
# =====================================================================
# Planet's transit count from birth star gives Tara classification

TARA_RESULTS = {
    1: ("Janma Tara", "Personal transformation, new beginnings, health focus",
        "ashubh", "Paryaya 1 — strong effect", 1),
    2: ("Sampat Tara", "Wealth, prosperity, gains, material comfort",
        "shubh", "Paryaya 1", 1),
    3: ("Vipat Tara", "Danger, accidents, losses, obstacles",
        "ashubh", "Paryaya 1", 1),
    4: ("Kshema Tara", "Security, well-being, recovery, protection",
        "shubh", "Paryaya 1", 1),
    5: ("Pratyak Tara", "Opposition, delays, hindrances, competition",
        "ashubh", "Paryaya 1", 1),
    6: ("Sadhana Tara", "Achievement, accomplishment, goal fulfillment",
        "shubh", "Paryaya 1", 1),
    7: ("Naidhana Tara", "Death-like suffering, endings, major transitions",
        "ashubh", "Paryaya 1", 1),
    8: ("Mitra Tara", "Friendship, support, alliances, help from others",
        "shubh", "Paryaya 1", 1),
    9: ("Parama Maitra Tara", "Highest friendship, ultimate support, divine grace",
        "shubh", "Paryaya 1", 1),
    # Paryaya 2 (10-18) — reduced effect
    10: ("Janma Tara (Paryaya 2)", "Reduced personal changes",
         "neutral", "Paryaya 2 — softened", 2),
    11: ("Sampat Tara (Paryaya 2)", "Moderate gains",
         "shubh", "Paryaya 2", 2),
    12: ("Vipat Tara (Paryaya 2)", "Reduced danger",
         "neutral", "Paryaya 2 — softened", 2),
    13: ("Kshema Tara (Paryaya 2)", "Moderate security",
         "shubh", "Paryaya 2", 2),
    14: ("Pratyak Tara (Paryaya 2)", "Minor delays",
         "neutral", "Paryaya 2 — softened", 2),
    15: ("Sadhana Tara (Paryaya 2)", "Moderate achievement",
         "shubh", "Paryaya 2", 2),
    16: ("Naidhana Tara (Paryaya 2)", "Significant but reduced suffering",
         "ashubh", "Paryaya 2", 2),
    17: ("Mitra Tara (Paryaya 2)", "Moderate support",
         "shubh", "Paryaya 2", 2),
    18: ("Parama Maitra Tara (Paryaya 2)", "High friendship",
         "shubh", "Paryaya 2", 2),
    # Paryaya 3 (19-27) — mild effect
    19: ("Janma Tara (Paryaya 3)", "Mild personal changes",
         "neutral", "Paryaya 3 — mild", 3),
    20: ("Sampat Tara (Paryaya 3)", "Mild prosperity",
         "shubh", "Paryaya 3", 3),
    21: ("Vipat Tara (Paryaya 3)", "Minor obstacles",
         "neutral", "Paryaya 3 — mild", 3),
    22: ("Kshema Tara (Paryaya 3)", "Mild security",
         "shubh", "Paryaya 3", 3),
    23: ("Pratyak Tara (Paryaya 3)", "Minor opposition",
         "neutral", "Paryaya 3 — mild", 3),
    24: ("Sadhana Tara (Paryaya 3)", "Mild achievement",
         "shubh", "Paryaya 3", 3),
    25: ("Naidhana Tara (Paryaya 3)", "Minor endings",
         "neutral", "Paryaya 3 — mild", 3),
    26: ("Mitra Tara (Paryaya 3)", "Mild support",
         "shubh", "Paryaya 3", 3),
    27: ("Parama Maitra Tara (Paryaya 3)", "Highest friendship",
         "shubh", "Paryaya 3", 3),
}


def _tara_exceptions(count: int, rem: int, paryaya: int) -> list:
    """Classical Tara exceptions (GPD Ch.24)."""
    exceptions = []
    if count == 22:
        exceptions.append(
            "22nd Nakshatra (Vainasika) — destructive exception; avoid major durable events."
        )
    if count == 27:
        exceptions.append(
            "27th from Janma — Parama Maitra but restricted for marriage/travel/shaving; avoid 2nd half."
        )
    if rem == 1 and paryaya == 1:
        exceptions.append("Janma Tara — negative effect lifts after midday.")
    return exceptions


def tara_of(count: int) -> dict:
    """Compute Tara classification from count (1-27) from Janma Nakshatra."""
    if count < 1:
        return None
    if count in TARA_RESULTS:
        rem = count % 9 if count % 9 != 0 else 9
        paryaya_num = TARA_RESULTS[count][4]
        return {
            "name": TARA_RESULTS[count][0],
            "description": TARA_RESULTS[count][1],
            "verdict": TARA_RESULTS[count][2],
            "paryaya": TARA_RESULTS[count][3],
            "paryaya_num": paryaya_num,
            "count": count,
            "rem": rem,
            "exceptions": _tara_exceptions(count, rem, paryaya_num),
        }
    # Generic for high counts
    paryaya = 1 if count <= 9 else (2 if count <= 18 else 3)
    rem = count % 9 if count % 9 != 0 else 9
    names = {1: "Janma", 2: "Sampat", 3: "Vipat", 4: "Kshema", 5: "Pratyak",
             6: "Sadhana", 7: "Naidhana", 8: "Mitra", 9: "Parama Maitra"}
    verdicts = {1: "ashubh", 2: "shubh", 3: "ashubh", 4: "shubh", 5: "ashubh",
                6: "shubh", 7: "ashubh", 8: "shubh", 9: "shubh"}
    # Special exceptions (Gochar Phaladeepika)
    exceptions = []
    if count == 22: exceptions.append("22nd Nakshatra (Vainasika) — destructive exception; avoid major durable events.")
    if count == 27: exceptions.append("27th from Janma — Parama Maitra but restricted for marriage/travel/shaving; avoid 2nd half.")
    if rem == 1 and paryaya == 1: exceptions.append("Janma Tara — negative effect lifts after midday.")
    
    return {
        "name": f"{names[rem]} Tara",
        "description": "",
        "verdict": "neutral" if paryaya == 3 and verdicts[rem] == "ashubh" else verdicts[rem],
        "paryaya": paryaya,
        "count": count,
        "rem": rem,
        "exceptions": exceptions,
    }


# =====================================================================
# RULE 8: Combustion Orbs (Classical, per GPD + PD)
# =====================================================================

COMBUST_ORB = {
    "Moon": 12, "Mars": 17, "Mercury": 14,
    "Jupiter": 11, "Venus": 10, "Saturn": 15
}

# =====================================================================
# RULE 9: Paryaya (Cycles) — GPD Ch.26
# =====================================================================
# Saturn completes 1 cycle ~30 years, Jupiter ~12 years
# Different paryaya (cycle number) gives different effects based on age

SATURN_PARYAYA = {
    1: {"age_range": "0-30 years", "effect": "Foundation building; transit results mild",
        "source": "GPD-Ch26"},
    2: {"age_range": "30-60 years", "effect": "Peak impact; strongest transit effects",
        "source": "GPD-Ch26"},
    3: {"age_range": "60-90+ years", "effect": "Culmination; spiritual emphasis, reduced material impact",
        "source": "GPD-Ch26"},
}

JUPITER_PARYAYA = {
    1: {"age_range": "0-12 years", "effect": "Childhood; mild results", "source": "GPD-Ch26"},
    2: {"age_range": "12-24 years", "effect": "Education, growth", "source": "GPD-Ch26"},
    3: {"age_range": "24-36 years", "effect": "Career, marriage", "source": "GPD-Ch26"},
    4: {"age_range": "36-48 years", "effect": "Peak prosperity", "source": "GPD-Ch26"},
    5: {"age_range": "48-60 years", "effect": "Wisdom, teaching", "source": "GPD-Ch26"},
    6: {"age_range": "60-72+ years", "effect": "Spiritual emphasis", "source": "GPD-Ch26"},
}


# =====================================================================
# RULE 10: Dasha-Transit Reconciliation (GPD Ch.8)
# =====================================================================

def reconcile_dasha_transit(dasha_good: bool, transit_good: bool) -> str:
    """Combine Dasha and Transit results per Gochar Phaladeepika Ch.8 formula."""
    if dasha_good and transit_good:
        return "Very favourable — both Dasha and Transit support excellent outcomes"
    elif dasha_good and not transit_good:
        return "Mixed — favourable Dasha period but unfavourable transit; moderate results, delays likely"
    elif not dasha_good and transit_good:
        return "Mixed — unfavourable Dasha period but supportive transit; small gains possible"
    else:
        return "Very unfavourable — both Dasha and Transit are adverse; caution advised, postpone major decisions"
