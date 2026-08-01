"""
Natal structure factors — ported from panchanga_muhurtha MuhurtaCosmos.jsx.

Computes per-planet natal strength modifiers used by muhurta scoring:
Baladi / Deeptadi avastha, combustion, Graha Yuddha, Marana Karaka Sthana,
Gati (motion), Kartari on Lagna, plus activity-scoped karaka weighting.

Classical sources (cited per factor below):
  - BPHS Ch.47 (Avasthas), Evaluation-of-Strengths v.21-23 (Gati/Cheshta)
  - BPHS combustion orbs (Girish Chand Sharma translation)
  - BPHS Ch.3 (Graha Drishti)
  - Phaladeepika Ch.3 (Deeptadi), Ch.13 vv.10-11 (Mrityu Bhaga)
  - Jaimini Upadesha Sutras 3-4 (Rashi Drishti)
  - Later-practice Marana Karaka Sthana table (not verbatim JP ch.17)
  - Activity kāraka Atlas (Issue #28)

Main entry: compute_natal_structure(planets, lagna_idx, birth_jd) -> dict
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

try:
    from ..core.astronomy import planet_sidereal_lon
except ImportError:  # pragma: no cover — allow standalone compile/import
    planet_sidereal_lon = None  # type: ignore[assignment]


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

PLANETS: list[str] = [
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
]

FRIENDS: dict[str, list[str]] = {
    "Sun": ["Moon", "Mars", "Jupiter"],
    "Moon": ["Sun", "Mercury"],
    "Mars": ["Sun", "Moon", "Jupiter"],
    "Mercury": ["Sun", "Venus"],
    "Jupiter": ["Sun", "Moon", "Mars"],
    "Venus": ["Mercury", "Saturn"],
    "Saturn": ["Mercury", "Venus"],
    "Rahu": ["Venus", "Saturn"],
    "Ketu": ["Mars", "Venus"],
}

ENEMIES: dict[str, list[str]] = {
    "Sun": ["Venus", "Saturn"],
    "Moon": [],
    "Mars": ["Mercury"],
    "Mercury": ["Moon"],
    "Jupiter": ["Mercury", "Venus"],
    "Venus": ["Sun", "Moon"],
    "Saturn": ["Sun", "Moon", "Mars"],
}

EXALT_SIGN: dict[str, str] = {
    "Sun": "Aries",
    "Moon": "Taurus",
    "Mars": "Capricorn",
    "Mercury": "Virgo",
    "Jupiter": "Cancer",
    "Venus": "Pisces",
    "Saturn": "Libra",
}

DEBIL_SIGN: dict[str, str] = {
    "Sun": "Libra",
    "Moon": "Scorpio",
    "Mars": "Cancer",
    "Mercury": "Pisces",
    "Jupiter": "Capricorn",
    "Venus": "Virgo",
    "Saturn": "Aries",
}

OWN_SIGNS: dict[str, list[str]] = {
    "Sun": ["Leo"],
    "Moon": ["Cancer"],
    "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"],
    "Saturn": ["Capricorn", "Aquarius"],
}

RASHI_LORD: dict[str, str] = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

BENEFICS: list[str] = ["Jupiter", "Venus", "Mercury", "Moon"]
MALEFICS: list[str] = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]

# ---- Baladi Avastha (BPHS Ch.47) ------------------------------------------
# "one fourth in Baalavastha, half in Kumaravastha, full in Yuvavastha,
# very little in Vridhavastha and NIL in Mritavastha." Fractions of own
# positive result only — never a malefic penalty scale. 6° bands; odd signs
# forward, even signs reverse.
BALADI_STATES: list[str] = ["Bala", "Kumara", "Yuva", "Vridha", "Mrita"]
BALADI_BONUS: dict[str, int] = {
    "Bala": 2,
    "Kumara": 4,
    "Yuva": 8,
    "Vridha": 1,
    "Mrita": 0,
}

# ---- Deeptadi Avastha (Phaladeepika Ch.3) — 4-state dignity subset --------
# Full system is 10 states; only the 4 with zero new unverified data.
# Percentages scaled from source (100/75/60/-75) to app point scale.
DEEPTADI_BONUS: dict[str, int] = {
    "Pradeepta": 10,
    "Swastha": 7,
    "Mudita": 5,
    "Atibheeta": -8,
}

# ---- Combustion / Asta (BPHS, Sharma translation) -------------------------
# Moon 12°, Mars 17°, Mercury 14°, Jupiter 11°, Venus 10°, Saturn 16°.
# Mercury/Venus retrograde narrowing not applied (no per-planet retro flag).
COMBUSTION_ORB: dict[str, float] = {
    "Moon": 12,
    "Mars": 17,
    "Mercury": 14,
    "Jupiter": 11,
    "Venus": 10,
    "Saturn": 16,
}
COMBUSTION_PENALTY: int = -8

# ---- Mrityu Bhaga (Phaladeepika Ch.13 vv.10-11) — Moon & Lagna only ------
# ±1° orb is a documented judgment call, not a cited figure.
MRITYU_BHAGA_MOON: list[int] = [26, 12, 13, 25, 24, 11, 26, 14, 13, 25, 5, 12]
MRITYU_BHAGA_LAGNA: list[int] = [8, 9, 22, 22, 25, 14, 4, 23, 18, 20, 21, 10]

# ---- Graha Yuddha (BPHS Vol.II p.687) — detection only, 1° orb -----------
GRAHA_YUDDHA_PLANETS: list[str] = ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
GRAHA_YUDDHA_ORB: float = 1.0
GRAHA_YUDDHA_PENALTY: int = -8

# ---- Marana Karaka Sthana — later-practice house table (not verbatim JP) -
# JP ch.17 v.34-36 differs for Saturn (janma-nakshatra) and Venus (enemy
# sign). Ketu deliberately omitted (not in JP's list).
MARANA_KARAKA_STHANA: dict[str, int] = {
    "Sun": 12,
    "Moon": 8,
    "Mars": 7,
    "Mercury": 7,
    "Jupiter": 3,
    "Venus": 6,
    "Saturn": 1,
    "Rahu": 9,
}
MARANA_PENALTY: int = -8

# ---- Gati / Cheshta subset (BPHS Evaluation-of-Strengths v.21-23) --------
# 5 of 8 named states from daily motion vs mean sidereal rate.
# Bonuses = BPHS virupas rescaled; Sama is neutral baseline.
GATI_MEAN_DAILY_MOTION: dict[str, float] = {
    "Mars": 0.524,
    "Mercury": 4.092,
    "Jupiter": 0.083,
    "Venus": 1.602,
    "Saturn": 0.034,
}
GATI_BONUS: dict[str, int] = {
    "Vakra": 8,
    "Chara": 5,
    "Sama": 0,
    "Manda": -3,
    "Vikala": -3,
}

# ---- Graha Drishti (BPHS Ch.3) — Parashari planetary aspects -------------
# Nodes deliberately excluded (school-dependent).
GRAHA_DRISHTI_HOUSES: dict[str, list[int]] = {
    "Sun": [7],
    "Moon": [7],
    "Mars": [4, 7, 8],
    "Mercury": [7],
    "Jupiter": [5, 7, 9],
    "Venus": [7],
    "Saturn": [3, 7, 10],
}

# ---- Rashi Drishti (Jaimini Upadesha Sutras 3-4) -------------------------
SIGN_MODALITY: dict[str, str] = {
    "Aries": "movable",
    "Taurus": "fixed",
    "Gemini": "dual",
    "Cancer": "movable",
    "Leo": "fixed",
    "Virgo": "dual",
    "Libra": "movable",
    "Scorpio": "fixed",
    "Sagittarius": "dual",
    "Capricorn": "movable",
    "Aquarius": "fixed",
    "Pisces": "dual",
}

# Vargottama bonus (D1 sign == D9 sign)
VARGOTTAMA_BONUS: int = 5

# Contextual natal bonus cap (findMuhurta / AnswerCard shared rule)
NATAL_BONUS_CAP: int = 20


# ---------------------------------------------------------------------------
# Activity kāraka table (Issue #28) — primary full weight, secondary half
# ---------------------------------------------------------------------------

ACTIVITY_KARAKA: dict[str, dict[str, Any]] = {
    "Business & Finance · Accounting & Bookkeeping": {
        "primary": ["Mercury", "Sun"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 32: Mercury=calculation/document; Sun=revenue/authority.",
    },
    "Business & Finance · Borrowing": {
        "primary": ["Saturn", "Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 34: Saturn=debt explicit; Mercury=agreement/record.",
    },
    "Business & Finance · Investing": {
        "primary": ["Jupiter", "Mercury"],
        "secondary": [],
        "tier": "D",
        "note": "Modern activity; Jupiter=wealth/capital; Mercury=transaction/account (Atlas 31 analogy).",
    },
    "Business & Finance · Lending": {
        "primary": ["Jupiter", "Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 35: Jupiter=wealth/treasury; Mercury=transaction.",
    },
    "Business & Finance · Opening a Business or Store": {
        "primary": ["Mercury"],
        "secondary": ["Jupiter", "Saturn"],
        "tier": "B",
        "note": "Atlas 29: Mercury=commerce primary; Jupiter/Saturn by purpose (capital/labour).",
    },
    "Business & Finance · Paying Debts": {
        "primary": ["Saturn", "Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 79: Saturn=debt explicit; Mercury=calculation/record/agreement.",
    },
    "Business & Finance · Selling": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 33: Mercury=trade/commerce explicit.",
    },
    "Business & Finance · Buying & General Transactions": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 33: Mercury=commercial transaction clearest agent.",
    },
    "Business & Finance · Signing Contracts & Agreements": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 30: Mercury=speech/action/documents converge.",
    },
    "Jewelry & Gems · Making Jewelry with Gems": {
        "primary": ["Mercury"],
        "secondary": ["Venus"],
        "tier": "C",
        "note": "Craftsmanship=Mercury (Atlas 10); gemwork also relates to Venus ornaments.",
    },
    "Jewelry & Gems · Making Other Jewelry": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "C",
        "note": "Jewelry craftsmanship extension of Mercury fine/mechanical arts.",
    },
    "Jewelry & Gems · Wearing a Gem First Time": {
        "primary": ["Venus", "Sun"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 64: Venus=ornaments; Sun=gold (gems/precious stones akin to ornaments).",
    },
    "Construction & Home · Starting Construction": {
        "primary": ["Mars", "Saturn"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 23: Mars=earth/fire; Saturn=labour/iron/tools.",
    },
    "Construction & Home · Digging Foundation (Bhumi Puja)": {
        "primary": ["Mars", "Saturn"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 25: Moon+Mars for well-digging; Mars+Saturn for earth-work/labour.",
    },
    "Construction & Home · Installing the Main Door": {
        "primary": ["Mars", "Saturn"],
        "secondary": [],
        "tier": "C",
        "note": "Part of construction phase (Atlas 23); Mars+Saturn extension.",
    },
    "Construction & Home · House Warming (Griha Pravesh)": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 24: Moon=4th-house/home; Jupiter=auspicious rite/blessing.",
    },
    "Crafts & Arts · Learning & Making Crafts": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 10: Mercury=mechanical arts/dexterity/learning explicit.",
    },
    "Crafts & Arts · Beginning a Painting": {
        "primary": ["Venus", "Mercury"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 9: Venus=painting/poetry; Mercury=fine arts.",
    },
    "Dental · Cleaning & Checkup": {
        "primary": ["Saturn"],
        "secondary": [],
        "tier": "D",
        "note": "Atlas 39: Saturn=teeth (body-part analogy tier D); treatment mapping is later extension.",
    },
    "Dental · Oral Surgery & Extraction": {
        "primary": ["Mars"],
        "secondary": ["Saturn"],
        "tier": "B",
        "note": "Mars=wounds/cutting/blood explicit (surgical aspect); Saturn=teeth (body-part context).",
    },
    "Ear Piercing · Karna-Vedha": {
        "primary": ["Mars"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 67: Mars=weapons/wounds explicit (not Ketu per classical catalogues).",
    },
    "Education & Learning · Alphabet (Aksharabhyasa)": {
        "primary": ["Mercury", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 6 (Vidyarambha): Mercury=speech/name-expression; Jupiter=teaching/knowledge.",
    },
    "Education & Learning · Astrology (Jyotisha)": {
        "primary": ["Mercury", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 12: Mercury=computation; Jupiter=śāstra/teaching.",
    },
    "Education & Learning · Grammar & Language": {
        "primary": ["Mercury", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 6/7: Mercury=speech/learning; Jupiter=higher knowledge/language-śāstra.",
    },
    "Education & Learning · Mathematics": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Mercury=calculation/computation explicit (Atlas 12 Jyotiṣa analogy).",
    },
    "Education & Learning · Medicine": {
        "primary": ["Jupiter", "Mercury"],
        "secondary": ["Sun"],
        "tier": "B",
        "note": "Jupiter=śāstra/knowledge; Mercury=learning/discrimination; Sun=physicians (Phaladīpikā).",
    },
    "Education & Learning · Art & Music": {
        "primary": ["Venus", "Mercury"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 9: Venus=music/dance/poetry; Mercury=fine arts explicit.",
    },
    "Education & Learning · All Other Studies": {
        "primary": ["Jupiter", "Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 7: Jupiter=higher study/śāstra; Mercury=learning/discrimination.",
    },
    "Education & Learning · Starting a Trade or Apprenticeship": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 10: Mercury=craft/technical skill/learning.",
    },
    "Grooming · Hair & Beard Cutting": {
        "primary": ["Saturn"],
        "secondary": ["Venus"],
        "tier": "D",
        "note": "Atlas 65: Saturn's body-part analogy=hair; Venus=beauty/adornment context.",
    },
    "Grooming · Nail Cutting": {
        "primary": ["Saturn"],
        "secondary": [],
        "tier": "D",
        "note": "Saturn=body-part description (hair/teeth/nails); nails as grooming analogy.",
    },
    "Grooming · Shaving": {
        "primary": ["Saturn"],
        "secondary": [],
        "tier": "D",
        "note": "Saturn=hair/grooming (body-part context); akin to Atlas 65 haircut.",
    },
    "House & Home · Entering New House (East-facing)": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 24 (Gṛha-praveśa): direction does not alter kāraka; Moon=home, Jupiter=blessing.",
    },
    "House & Home · Entering New House (North-facing)": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 24 (Gṛha-praveśa): direction does not alter kāraka; Moon=home, Jupiter=blessing.",
    },
    "House & Home · Entering New House (West-facing)": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 24 (Gṛha-praveśa): direction does not alter kāraka; Moon=home, Jupiter=blessing.",
    },
    "House & Home · Entering New House (South-facing)": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 24 (Gṛha-praveśa): direction does not alter kāraka; Moon=home, Jupiter=blessing.",
    },
    "Job & Career · Applying for a New Job": {
        "primary": ["Saturn", "Mercury", "Sun"],
        "secondary": [],
        "tier": "B",
        "note": "Related to Atlas 72 (starting job): Saturn=livelihood/service; Mercury=action/skill; Sun=rank.",
    },
    "Job & Career · Job Interview": {
        "primary": ["Mercury", "Sun"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 11: Mercury=learning/speech; Sun=rank/authority (modern event inferred).",
    },
    "Job & Career · Asking for Promotion": {
        "primary": ["Sun", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 77 (oath/political launch): Sun=authority/rank; Jupiter=honour/advancement.",
    },
    "Job & Career · Resignation": {
        "primary": ["Saturn"],
        "secondary": [],
        "tier": "C",
        "note": "Saturn=12th-house ending/loss; extension of Atlas 72 job-start as its inverse.",
    },
    "Job & Career · Hiring a New Employee": {
        "primary": ["Saturn", "Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 73: Saturn=servants/labour explicit; Mercury=agreement/task.",
    },
    "Job & Career · Starting a New Position": {
        "primary": ["Saturn", "Mercury", "Sun"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 72: Saturn=livelihood/service explicit; Mercury=action/skill; Sun=rank.",
    },
    "Litigation & Legal · Filing a Case": {
        "primary": ["Mercury", "Mars", "Saturn"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 70: Mercury=speech/document; Mars=enemies/battle; Saturn=adversity/captivity.",
    },
    "Litigation & Legal · Taking an Oath or Swearing-In": {
        "primary": ["Sun", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 77: Sun=sovereign authority/rank; Jupiter=honour/counsel (oath ritual).",
    },
    "Litigation & Legal · Signing Important Legal Documents": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 30: Mercury=speech/action/documents converge explicitly.",
    },
    "Marriage & Family · Engagement (Vagdhana)": {
        "primary": ["Venus"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 02: Venus=direct extension of Venusian marriage/union.",
    },
    "Marriage & Family · Wedding (Vivaha)": {
        "primary": ["Venus"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 01: Venus explicit cover of marriage, wife, festivity.",
    },
    "Marriage & Family · First Conception (Garbhadhana)": {
        "primary": ["Jupiter", "Venus", "Moon"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 41: Jupiter=children; Venus=semen/union; Moon=mother/nurture.",
    },
    "Marriage & Family · Naming Ceremony (Namakarana)": {
        "primary": ["Mercury", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 44: Mercury=speech/name-expression; Jupiter=child/rite.",
    },
    "Marriage & Family · First Solid Food (Annaprashana)": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 45: Moon=food/milk/nourishment; Jupiter=the child/blessing.",
    },
    "Marriage & Family · First Haircut (Chudakarana)": {
        "primary": ["Saturn", "Moon"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 46: Saturn=hair (body-part); Moon=child/nurture context.",
    },
    "Marriage & Family · First Outing (Nishkramana)": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 48: Moon=care/mother; Jupiter=child/blessing/auspicious rite.",
    },
    "Medical & Surgery · Cosmetic Surgery": {
        "primary": ["Mars"],
        "secondary": ["Venus"],
        "tier": "C",
        "note": "Mars=wounds/cutting/surgery; Venus=beauty/adornment (cosmetic aspect).",
    },
    "Medical & Surgery · General Surgery (Sastra-Karma)": {
        "primary": ["Mars", "Sun"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 37: Mars=wounds/cutting/blood/weapons; Sun=physicians (Phaladīpikā).",
    },
    "Medical & Surgery · Laxatives & Purgatives": {
        "primary": ["Moon"],
        "secondary": [],
        "tier": "C",
        "note": "Moon=health/nourishment/bodily health; purification akin to Atlas 40 (bathing).",
    },
    "Medical & Surgery · Taking Medicine or Treatment": {
        "primary": ["Sun", "Moon"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 42: Sun=health/vigour/physicians; Moon=bodily health/nourishment.",
    },
    "Medical & Surgery · Eye Treatment": {
        "primary": ["Sun"],
        "secondary": [],
        "tier": "C",
        "note": "Sun=health/vigour/physicians; eyes as body-part (later analogy, tier D inference softened to C for medical context).",
    },
    "Music & Arts · First Use of Musical Instrument": {
        "primary": ["Venus", "Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 69: Venus=musical performance domain; Mercury=craftsmanship/skill.",
    },
    "Music & Arts · Dance, Music & Acting (Learning & Performing)": {
        "primary": ["Venus", "Mercury"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 68: Venus=music/dance/poetry; Mercury=fine arts/expressive skill explicit.",
    },
    "Health & Wellness · Starting a Diet or Fast": {
        "primary": ["Saturn"],
        "secondary": ["Jupiter"],
        "tier": "C",
        "note": "Saturn=deprivation/austerity/discipline; Jupiter=penance/beatitude (if spiritual fast).",
    },
    "Health & Wellness · Beginning Exercise or Yoga Practice": {
        "primary": ["Mars"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 42: Mars=strength/courage/prowess/athletic training explicit.",
    },
    "Health & Wellness · First Bath After Illness": {
        "primary": ["Moon"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 40: Moon=bathing/water/bodily health/purification explicit.",
    },
    "Real Estate · Purchasing Property": {
        "primary": ["Mars", "Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 22: Mars=earth/land; Mercury=transaction/documents.",
    },
    "Real Estate · Selling Property": {
        "primary": ["Mercury"],
        "secondary": ["Moon", "Mars"],
        "tier": "B",
        "note": "Atlas 28: Mercury=sale/document primary; Moon=home context; Mars=land.",
    },
    "Real Estate · Dividing Property": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "C",
        "note": "Mercury=documents/division/agreement (extension of Atlas 30 contract-signing).",
    },
    "Religion & Spirituality · Mantra Initiation (Diksha)": {
        "primary": ["Jupiter", "Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 52: Jupiter=preceptor/śāstra; Mercury=learning/meditation/ritual skill.",
    },
    "Religion & Spirituality · Installing a Deity (Pratishtha)": {
        "primary": ["Sun", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 51: Sun=temple/deity-related; Jupiter=worship/faith/rite.",
    },
    "Religion & Spirituality · Sacred Thread (Upanayanam)": {
        "primary": ["Jupiter", "Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 47: Jupiter=Veda/teaching/rite; Mercury=initiatory learning/skill.",
    },
    "Religion & Spirituality · Religious Study": {
        "primary": ["Jupiter"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 8: Jupiter=Vedas/śāstras/teaching/wisdom explicit.",
    },
    "Religion & Spirituality · Performing Ceremonies (Puja & Yajna)": {
        "primary": ["Jupiter", "Sun"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 50: Jupiter=sacrifice/faith explicit; Sun=homa/yajña/temple explicit.",
    },
    "Religion & Spirituality · Planetary Pacification (Shanti Karma)": {
        "primary": ["Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 55: Jupiter=sacrifice/worship/faith/religious merit (śānti=pacification via worship).",
    },
    "Religion & Spirituality · Beginning a Vrata (Religious Observance)": {
        "primary": ["Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Vrata=religious vow/observance; Jupiter=worship/dharma/penance explicit.",
    },
    "Travel & Journey · Any Direction (Yatra)": {
        "primary": ["Mars"],
        "secondary": ["Jupiter"],
        "tier": "C",
        "note": "Generic yatra; Mars=3rd-house journey (short); Jupiter=9th-house (long/sacred).",
    },
    "Travel & Journey · Returning Home": {
        "primary": ["Saturn"],
        "secondary": ["Moon"],
        "tier": "C",
        "note": "UNCERTAIN: Saturn=12th-house return/ending; Moon=home; both interpretable.",
    },
    "Travel & Journey · Short Journey": {
        "primary": ["Mars"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 15: Mars=3rd-house kāraka explicit.",
    },
    "Travel & Journey · Long Journey": {
        "primary": ["Jupiter", "Saturn"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 16: Jupiter=9th-house (pilgrimage/long); Saturn=12th-house (departure).",
    },
    "Travel & Journey · Relocation (Moving Home)": {
        "primary": ["Moon", "Saturn"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 21: Moon=home/4th-house; Saturn=12th-house leaving/loss.",
    },
    "Travel & Journey · Pilgrimage": {
        "primary": ["Jupiter", "Sun"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 18: Sun+Jupiter explicit (shrine visits=9th, Phaladīpikā 9th-kārakas).",
    },
    "Vehicles · First Driving (Learning)": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "C",
        "note": "Learning/skill domain; Mercury=mechanical arts/dexterity/learning (Atlas 10).",
    },
    "Vehicles · Buying a Vehicle (Vahana-Kraya)": {
        "primary": ["Venus"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 14: Venus=vehicles explicit; 4th-house=vehicle field.",
    },
    "Agriculture & Farming · Sowing Seeds": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 57: Moon=agriculture/grain/water explicit; Jupiter=fruitfulness/prosperity/gain.",
    },
    "Agriculture & Farming · Harvesting": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 59: Moon=corn/agriculture; Jupiter=wealth/treasury/fruitfulness.",
    },
    "Agriculture & Farming · Buying Cattle & Livestock": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 64: cows=lunar; quadrupeds=11th-house Jupiter.",
    },
    "Agriculture & Farming · Planting Trees": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "C",
        "note": "Growth/agriculture; Moon+Jupiter from sowing (Atlas 57) extension.",
    },
    "Agriculture & Farming · Taming or Training Animals": {
        "primary": ["Mars"],
        "secondary": [],
        "tier": "C",
        "note": "Mars=strength/courage/control; animal training as extension of Mars prowess.",
    },
    "Well & Water · Digging a Well or Borewell": {
        "primary": ["Moon", "Mars"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 25: Moon=water; Mars=earth/cutting.",
    },
    "Writing · Starting a New Writing Project": {
        "primary": ["Mercury"],
        "secondary": [],
        "tier": "B",
        "note": "Atlas 13: Mercury=speech/action/knowledge (writing principal agent).",
    },
    "Personal · Wearing New Clothes First Time": {
        "primary": ["Venus"],
        "secondary": [],
        "tier": "A",
        "note": "Atlas 63: Venus=clothing/ornaments/pleasure/adornment explicit.",
    },
    "Personal · First Bath in Holy River (Tirtha-Snana)": {
        "primary": ["Moon", "Jupiter"],
        "secondary": [],
        "tier": "B",
        "note": "Moon=bathing/water/purification; Jupiter=pilgrimage/sacred/worship.",
    },
    "Personal · Beginning a New Habit or Routine": {
        "primary": ["Saturn"],
        "secondary": [],
        "tier": "C",
        "note": "Saturn=discipline/livelihood/routine/austerity (habit-formation as Saturn domain).",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PlanetLike = Union[Mapping[str, Any], Any]


def house_from(from_sign_idx: int, to_sign_idx: int) -> int:
    """House number (1..12) of *to* counted from *from* (whole-sign)."""
    return (to_sign_idx - from_sign_idx + 12) % 12 + 1


def _pl_get(pl: PlanetLike, key: str, default: Any = None) -> Any:
    """Read a field from a planet dict or object (planet/rashi/deg)."""
    if isinstance(pl, Mapping):
        return pl.get(key, default)
    return getattr(pl, key, default)


def _planet_name(pl: PlanetLike) -> Optional[str]:
    return _pl_get(pl, "planet")


def _planet_rashi(pl: PlanetLike) -> Optional[str]:
    return _pl_get(pl, "rashi")


def _planet_deg(pl: PlanetLike) -> Optional[float]:
    d = _pl_get(pl, "deg")
    if d is None:
        return None
    try:
        return float(d)
    except (TypeError, ValueError):
        return None


def _angular_sep(lon_a: float, lon_b: float) -> float:
    sep = abs(lon_a - lon_b) % 360
    if sep > 180:
        sep = 360 - sep
    return sep


def _sidereal_lon(pl: PlanetLike) -> Optional[float]:
    rashi = _planet_rashi(pl)
    deg = _planet_deg(pl)
    if rashi is None or deg is None:
        return None
    try:
        idx = RASHIS.index(rashi)
    except ValueError:
        return None
    return idx * 30 + deg


# ---------------------------------------------------------------------------
# Individual factors
# ---------------------------------------------------------------------------


def baladi_avastha(sign_idx: int, deg_in_sign: float) -> str:
    """Baladi (age) avastha from sign parity and degree-in-sign.

    Source: BPHS Ch.47 — five states in 6° bands. Odd signs (Aries=0,
    Gemini=2, …) run Bala→Mrita forward; even signs reverse.

    Returns one of: Bala, Kumara, Yuva, Vridha, Mrita.
    """
    band = min(4, int(math.floor(deg_in_sign / 6)))
    is_odd_sign = sign_idx % 2 == 0  # JS: signIdx % 2 === 0 → odd rashi (1-based)
    return BALADI_STATES[band if is_odd_sign else 4 - band]


def deeptadi_avastha(planet: str, sign_name: str) -> Optional[str]:
    """Deeptadi dignity avastha (4-state subset).

    Source: Phaladeepika Ch.3 — Pradeepta (exalted), Swastha (own),
    Mudita (friend's sign), Atibheeta (debilitated). Unclassified → None
    (no silent wrong-state mapping).
    """
    if EXALT_SIGN.get(planet) == sign_name:
        return "Pradeepta"
    if DEBIL_SIGN.get(planet) == sign_name:
        return "Atibheeta"
    own = OWN_SIGNS.get(planet)
    if own and sign_name in own:
        return "Swastha"
    lord = RASHI_LORD.get(sign_name)
    friends = FRIENDS.get(planet)
    if lord and friends and lord in friends:
        return "Mudita"
    return None


def jagradadi_avastha(planet: str, sign_name: str) -> str:
    """Jagradadi (waking/dreaming/sleeping) label — display only, not scored.

    Source: BPHS Ch.47 vv.5-6. Same underlying dignity as Deeptadi; scoring
    both would double-count. Own/exalted → Jagrat; enemy/debilitated →
    Sushupti; else Swapna.
    """
    own = OWN_SIGNS.get(planet) or []
    if EXALT_SIGN.get(planet) == sign_name or sign_name in own:
        return "Jagrat"
    if DEBIL_SIGN.get(planet) == sign_name:
        return "Sushupti"
    lord = RASHI_LORD.get(sign_name)
    enemies = ENEMIES.get(planet)
    if lord and enemies and lord in enemies:
        return "Sushupti"
    return "Swapna"


def is_combust(planet: str, planet_lon: float, sun_lon: float) -> bool:
    """True if *planet* is within its BPHS combustion orb of the Sun.

    Source: BPHS (Sharma) — Moon 12°, Mars 17°, Mercury 14°, Jupiter 11°,
    Venus 10°, Saturn 16°. Sun itself and unlisted bodies → False.
    """
    orb = COMBUSTION_ORB.get(planet)
    if orb is None:
        return False
    return _angular_sep(planet_lon, sun_lon) <= orb


def mrityu_bhaga_hit(
    table: Sequence[float], sign_idx: int, deg_in_sign: float
) -> bool:
    """True if degree-in-sign is within ±1° of the table's critical degree.

    Source: Phaladeepika Ch.13 vv.10-11 (Moon & Lagna tables). Orb ±1° is
    a documented judgment call, not cited in the source.
    """
    if sign_idx < 0 or sign_idx >= len(table):
        return False
    return abs(deg_in_sign - table[sign_idx]) <= 1


def graha_yuddha_pairs(planets: Sequence[PlanetLike]) -> list[list[str]]:
    """Detect planetary-war pairs among the five star planets (≤1° separation).

    Source: BPHS Vol.II p.687 — conjunction within one degree. Detection
    only: no winner asserted (winner clause OCR-unreliable). Scope:
    Mars, Mercury, Jupiter, Venus, Saturn only.
    """
    pairs: list[list[str]] = []
    candidates = [
        pl
        for pl in planets
        if _planet_name(pl) in GRAHA_YUDDHA_PLANETS and _planet_deg(pl) is not None
    ]
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            a, b = candidates[i], candidates[j]
            lon_a = _sidereal_lon(a)
            lon_b = _sidereal_lon(b)
            if lon_a is None or lon_b is None:
                continue
            if _angular_sep(lon_a, lon_b) <= GRAHA_YUDDHA_ORB:
                pairs.append([_planet_name(a), _planet_name(b)])  # type: ignore[list-item]
    return pairs


def is_in_marana_karaka_sthana(
    planet: str, lagna_sign_idx: Optional[int], planet_sign_idx: Optional[int]
) -> bool:
    """True if *planet* occupies its Marana Karaka Sthana house from Lagna.

    Uses the widely-practiced later natal-table convention (house numbers),
    not a verbatim transcription of Jataka Parijata ch.17 vv.34-36
    (Saturn/Venus entries differ in the primary text). Ketu unscored.
    """
    target = MARANA_KARAKA_STHANA.get(planet)
    if target is None or lagna_sign_idx is None or planet_sign_idx is None:
        return False
    return house_from(lagna_sign_idx, planet_sign_idx) == target


def kartari_on_lagna(
    lagna_sign_idx: Optional[int], planets: Optional[Sequence[PlanetLike]]
) -> Optional[str]:
    """Shubh/Paap Kartari hemming the Lagna (2nd and 12th both occupied).

    Classical hemming doctrine: both flanks must be occupied. All malefic
    occupants → "paap"; all benefic → "shubh"; mixed or one-sided → None.
    Chart-wide factor (not scoped to a kāraka planet).
    """
    if lagna_sign_idx is None or not planets:
        return None
    neighbours = [(lagna_sign_idx + 1) % 12, (lagna_sign_idx + 11) % 12]
    in_first = [
        pl for pl in planets if _rashi_idx(_planet_rashi(pl)) == neighbours[0]
    ]
    in_second = [
        pl for pl in planets if _rashi_idx(_planet_rashi(pl)) == neighbours[1]
    ]
    if not in_first or not in_second:
        return None
    occupants = in_first + in_second
    names = [_planet_name(pl) for pl in occupants]
    if all(n in MALEFICS for n in names):
        return "paap"
    if all(n in BENEFICS for n in names):
        return "shubh"
    return None


def _rashi_idx(rashi: Optional[str]) -> int:
    if not rashi:
        return -1
    try:
        return RASHIS.index(rashi)
    except ValueError:
        return -1


def gati_state(planet: str, daily_speed: Optional[float]) -> Optional[str]:
    """Classify motion state from daily sidereal speed vs mean rate.

    Source: BPHS Evaluation-of-Strengths vv.21-23 (disclosed 5-of-8 subset).
    Vakra (retro), Vikala (near-stationary), Chara (fast), Manda (slow),
    Sama (near mean). Anu-vakra / Mandatara / Ati-chara need Sheeghrochha
    machinery this engine does not have.
    """
    mean = GATI_MEAN_DAILY_MOTION.get(planet)
    if mean is None or daily_speed is None or (
        isinstance(daily_speed, float) and math.isnan(daily_speed)
    ):
        return None
    if daily_speed < 0:
        return "Vakra"
    if abs(daily_speed) < mean * 0.05:
        return "Vikala"
    if daily_speed > mean * 1.15:
        return "Chara"
    if daily_speed < mean * 0.85:
        return "Manda"
    return "Sama"


def compute_gati_states(
    planets: Optional[Sequence[PlanetLike]], birth_jd: Optional[float]
) -> list[dict[str, str]]:
    """Per-planet Gati states via ±0.5 day finite difference of sidereal lon.

    Requires *birth_jd* and a working planet_sidereal_lon. Returns [] if
    either is missing. Same technique as transit retrograde detection.
    """
    detail: list[dict[str, str]] = []
    if not planets or birth_jd is None or planet_sidereal_lon is None:
        return detail
    present = {_planet_name(pl) for pl in planets}
    for planet in GATI_MEAN_DAILY_MOTION:
        if planet not in present:
            continue
        speed = planet_sidereal_lon(planet, birth_jd + 0.5) - planet_sidereal_lon(
            planet, birth_jd - 0.5
        )
        if speed > 180:
            speed -= 360
        elif speed < -180:
            speed += 360
        state = gati_state(planet, speed)
        if state:
            detail.append({"planet": planet, "state": state})
    return detail


def graha_drishti_aspects_sign(
    planet: str, planet_sign_idx: Optional[int], target_sign_idx: Optional[int]
) -> bool:
    """True if *planet* casts a Parashari graha-drishti on *target* sign.

    Source: BPHS Ch.3 — all grahas aspect 7th; Mars +4/8, Jupiter +5/9,
    Saturn +3/10. Node aspects not included.
    """
    houses = GRAHA_DRISHTI_HOUSES.get(planet)
    if not houses or planet_sign_idx is None or target_sign_idx is None:
        return False
    return house_from(planet_sign_idx, target_sign_idx) in houses


def rashi_drishti(sign_a: Optional[str], sign_b: Optional[str]) -> bool:
    """True if sign A aspects sign B by Jaimini rashi-drishti.

    Source: Jaimini Upadesha Sutras 3-4 — movable aspects fixed (except
    adjacent); fixed aspects movable (except adjacent); duals aspect each
    other mutually. Distinct from Graha Drishti — do not mix.
    """
    if not sign_a or not sign_b or sign_a == sign_b:
        return False
    mode_a = SIGN_MODALITY.get(sign_a)
    mode_b = SIGN_MODALITY.get(sign_b)
    if not mode_a or not mode_b:
        return False
    idx_a = _rashi_idx(sign_a)
    idx_b = _rashi_idx(sign_b)
    if idx_a < 0 or idx_b < 0:
        return False
    adj = abs(idx_a - idx_b)
    adjacent = adj == 1 or adj == 11
    if mode_a == "dual" and mode_b == "dual":
        return True
    if mode_a == "movable" and mode_b == "fixed":
        return not adjacent
    if mode_a == "fixed" and mode_b == "movable":
        return not adjacent
    return False


def bhavat_bhavam(base_house: Optional[int], n: Optional[int]) -> Optional[int]:
    """Nth house counted from *base_house* (1-based), wrapping 1..12.

    Source: BPHS — e.g. 4th-from-4th = 7th (mother), 5th-from-5th = 9th
    (children). Pure house arithmetic; chart-independent.
    """
    if base_house is None or n is None:
        return None
    return ((base_house - 1 + (n - 1)) % 12) + 1


# ---------------------------------------------------------------------------
# Aggregate natal structure + activity weighting
# ---------------------------------------------------------------------------


def compute_natal_structure(
    planets: Optional[Sequence[PlanetLike]],
    lagna_idx: Optional[int],
    birth_jd: Optional[float] = None,
    *,
    vargas: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Compute per-planet natal structure scores and factor detail lists.

    Port of JS ``computeNatalStructure(vargas, planets, birthJD)``.

    Parameters
    ----------
    planets :
        Sequence of planet placements. Each item needs ``planet`` (name),
        ``rashi`` (sign name), and ``deg`` (0–30 degree-in-sign).
    lagna_idx :
        Lagna sign index 0..11 (Aries=0). Used for Marana Karaka Sthana
        and Kartari on Lagna.
    birth_jd :
        Julian Day (UT) of birth. Optional; without it Gati states are
        omitted (same as JS when birthJD is falsy).
    vargas :
        Optional divisional maps ``{"D1": {name: signIdx, ...}, "D9": ...}``
        for Vargottama detection. Without vargas, vargottama list is empty.

    Returns
    -------
    dict with keys matching the JS return shape:
      planetNatal, vargottamaPlanets, baladiDetail, deeptadiDetail,
      combustDetail, yuddhaDetail, maranaDetail, gatiDetail, kartariLagna
    """
    planet_natal: dict[str, float] = {}

    def add_planet_natal(p: str, delta: float) -> None:
        planet_natal[p] = planet_natal.get(p, 0) + delta

    # --- Vargottama (D1 sign == D9 sign) ---------------------------------
    vargottama_planets: list[str] = []
    if vargas and vargas.get("D1") and vargas.get("D9"):
        d1, d9 = vargas["D1"], vargas["D9"]
        vargottama_planets = [
            name for name in d1 if d1.get(name) == d9.get(name)
        ]
        for p in vargottama_planets:
            if p != "Lagna":
                add_planet_natal(p, VARGOTTAMA_BONUS)

    # --- Baladi ----------------------------------------------------------
    baladi_detail: list[dict[str, str]] = []
    if planets:
        for pl in planets:
            name = _planet_name(pl)
            if name in ("Rahu", "Ketu") or not name:
                continue
            sign_idx = _rashi_idx(_planet_rashi(pl))
            deg = _planet_deg(pl)
            if sign_idx < 0 or deg is None:
                continue
            state = baladi_avastha(sign_idx, deg)
            add_planet_natal(name, BALADI_BONUS[state])
            if state in ("Yuva", "Mrita"):
                baladi_detail.append({"planet": name, "state": state})

    # --- Deeptadi (+ jagradadi label) ------------------------------------
    deeptadi_detail: list[dict[str, Any]] = []
    if planets:
        for pl in planets:
            name = _planet_name(pl)
            rashi = _planet_rashi(pl)
            if not name or not rashi:
                continue
            state = deeptadi_avastha(name, rashi)
            if state:
                add_planet_natal(name, DEEPTADI_BONUS[state])
                deeptadi_detail.append(
                    {
                        "planet": name,
                        "state": state,
                        "jagradadi": jagradadi_avastha(name, rashi),
                    }
                )

    # --- Combustion ------------------------------------------------------
    combust_detail: list[str] = []
    if planets:
        sun_entry = next((pl for pl in planets if _planet_name(pl) == "Sun"), None)
        if sun_entry is not None:
            sun_lon = _sidereal_lon(sun_entry)
            if sun_lon is not None:
                for pl in planets:
                    name = _planet_name(pl)
                    if name == "Sun" or not name:
                        continue
                    planet_lon = _sidereal_lon(pl)
                    if planet_lon is None:
                        continue
                    if is_combust(name, planet_lon, sun_lon):
                        add_planet_natal(name, COMBUSTION_PENALTY)
                        combust_detail.append(name)

    # --- Graha Yuddha ----------------------------------------------------
    yuddha_detail: list[list[str]] = []
    if planets:
        for a, b in graha_yuddha_pairs(planets):
            add_planet_natal(a, GRAHA_YUDDHA_PENALTY)
            add_planet_natal(b, GRAHA_YUDDHA_PENALTY)
            yuddha_detail.append([a, b])

    # --- Marana Karaka Sthana --------------------------------------------
    marana_detail: list[str] = []
    if lagna_idx is not None and planets:
        for pl in planets:
            name = _planet_name(pl)
            psi = _rashi_idx(_planet_rashi(pl))
            if not name or psi < 0:
                continue
            if is_in_marana_karaka_sthana(name, lagna_idx, psi):
                add_planet_natal(name, MARANA_PENALTY)
                marana_detail.append(name)

    # --- Gati ------------------------------------------------------------
    gati_detail = compute_gati_states(planets, birth_jd)
    for d in gati_detail:
        add_planet_natal(d["planet"], GATI_BONUS[d["state"]])

    # --- Kartari on Lagna ------------------------------------------------
    kartari_lagna = (
        kartari_on_lagna(lagna_idx, planets) if lagna_idx is not None else None
    )

    return {
        "planetNatal": planet_natal,
        "vargottamaPlanets": vargottama_planets,
        "baladiDetail": baladi_detail,
        "deeptadiDetail": deeptadi_detail,
        "combustDetail": combust_detail,
        "yuddhaDetail": yuddha_detail,
        "maranaDetail": marana_detail,
        "gatiDetail": gati_detail,
        "kartariLagna": kartari_lagna,
    }


def contextual_natal_bonus_for(
    activity_key: Optional[str], planet_natal: Mapping[str, float]
) -> dict[str, Any]:
    """Weight + cap a chart's natal-structure facts for one activity.

    Port of JS ``contextualNatalBonusFor(activityKey, planetNatal)``.

    Primary kāraka planets count at full weight, secondary at half, others
    at zero. If the activity is missing from ACTIVITY_KARAKA, falls back to
    every planet counting (pre-#28 flat-sum behaviour). Result capped to
    ±NATAL_BONUS_CAP (±20).
    """
    karaka = ACTIVITY_KARAKA.get(activity_key) if activity_key else None
    if karaka:
        primary = list(karaka.get("primary") or [])
        secondary = list(karaka.get("secondary") or [])
        relevant_planets = set(primary + secondary)
    else:
        primary = []
        secondary = []
        relevant_planets = set(PLANETS)

    def weight(p: str) -> float:
        if not karaka:
            return 1.0
        if p in primary:
            return 1.0
        if p in secondary:
            return 0.5
        return 0.0

    raw = 0.0
    for p, val in planet_natal.items():
        raw += val * weight(p)
    rounded = round(raw)
    bonus = max(-NATAL_BONUS_CAP, min(NATAL_BONUS_CAP, rounded))
    return {
        "relevantPlanets": relevant_planets,
        "bonus": bonus,
        "capped": rounded != bonus,
    }


__all__ = [
    "RASHIS",
    "PLANETS",
    "FRIENDS",
    "ENEMIES",
    "EXALT_SIGN",
    "DEBIL_SIGN",
    "OWN_SIGNS",
    "RASHI_LORD",
    "BENEFICS",
    "MALEFICS",
    "BALADI_STATES",
    "BALADI_BONUS",
    "DEEPTADI_BONUS",
    "COMBUSTION_ORB",
    "MRITYU_BHAGA_MOON",
    "MRITYU_BHAGA_LAGNA",
    "GRAHA_YUDDHA_PLANETS",
    "MARANA_KARAKA_STHANA",
    "GATI_MEAN_DAILY_MOTION",
    "GATI_BONUS",
    "GRAHA_DRISHTI_HOUSES",
    "SIGN_MODALITY",
    "ACTIVITY_KARAKA",
    "house_from",
    "baladi_avastha",
    "deeptadi_avastha",
    "jagradadi_avastha",
    "is_combust",
    "mrityu_bhaga_hit",
    "graha_yuddha_pairs",
    "is_in_marana_karaka_sthana",
    "kartari_on_lagna",
    "gati_state",
    "compute_gati_states",
    "graha_drishti_aspects_sign",
    "rashi_drishti",
    "bhavat_bhavam",
    "compute_natal_structure",
    "contextual_natal_bonus_for",
]
