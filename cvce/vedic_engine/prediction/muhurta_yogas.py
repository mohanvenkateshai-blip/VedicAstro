"""
Muhurta yoga evaluation — Vara/Tithi/Nakshatra combination rules.

Sources:
  - Wilhelm Ernst, "Classical Muhurta" Ch.9 pp.75-84 (Vara×Tithi, Vara×Nakshatra,
    triple Vara/Tithi/Nakshatra yogas; relative strengths on p.83)
  - Sarvartha Chintamani / Phaladeepika (via knowledge-graph nodes)
  - knowledge-graph nodes tagged is_muhurta_yoga=True

Relative strength (WE Ch.9 p.83):
  Vara/Tithi/Nakshatra  > Vara/Nakshatra (3×) > Vara/Tithi (3×) > Tithi/Nakshatra (weakest)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.panchanga import VARA_LORD

# ---------------------------------------------------------------------------
# VARA × TITHI YOGAS  (WE Ch.9 pp.75-76)
# ---------------------------------------------------------------------------

# Tithi group names used: Nanda(1,6,11), Bhadra(2,7,12), Jaya(3,8,13),
# Rikta(4,9,14), Purna(5,10,15/30)

SIDDHA_VT = {
    ("Venus", "Nanda"),
    ("Mercury", "Bhadra"),
    ("Mars", "Jaya"),
    ("Saturn", "Rikta"),
    ("Jupiter", "Purna"),
}

AMRITA_VT = {
    ("Sun", "Nanda"),
    ("Moon", "Bhadra"),
    ("Mars", "Nanda"),
    ("Mercury", "Jaya"),
    ("Jupiter", "Rikta"),
    ("Venus", "Bhadra"),
    ("Saturn", "Purna"),
}

# Dagdha: inauspicious Vara/Tithi-number pairs (WE Ch.9 p.75)
DAGDHA_VT = {
    ("Sun", 12),
    ("Moon", 11),
    ("Mars", 5),
    ("Mercury", 2),
    ("Mercury", 3),
    ("Jupiter", 6),
    ("Venus", 8),
    ("Saturn", 9),
}

# Visha: inauspicious Vara/Tithi-number pairs (WE Ch.9 p.75)
VISHA_VT = {
    ("Sun", 4),
    ("Moon", 6),
    ("Mars", 7),
    ("Mercury", 2),
    ("Jupiter", 8),
    ("Venus", 9),
    ("Saturn", 7),
}

# Krakacha (Kritisha): inauspicious (WE Ch.9 p.76)
KRAKACHA_VT = {("Saturn", 6)}

# Hutasana: inauspicious Vara/Tithi-number pairs (WE Ch.9 p.76)
HUTASANA_VT = {
    ("Sun", 7),
    ("Moon", 8),
    ("Mars", 9),
    ("Mercury", 10),
    ("Jupiter", 11),
    ("Venus", 12),
    ("Saturn", 13),
}

# Samvartaka / Vajra: inauspicious (WE Ch.9 p.76)
SAMVARTAKA_VT = {
    ("Sun", 6),
    ("Moon", 1),
    ("Mars", 8),
    ("Mercury", 11),
    ("Jupiter", 10),
    ("Venus", 4),
    ("Saturn", 5),
}

# ---------------------------------------------------------------------------
# VARA × NAKSHATRA YOGAS  (WE Ch.9 pp.77-83)
# ---------------------------------------------------------------------------

# Sarvartha Siddhi — "complete accomplishment" (WE Ch.9 p.77)
SARVARTHA_SIDDHI = {
    ("Sun", "Ashwini"),
    ("Sun", "Pushya"),
    ("Sun", "Hasta"),
    ("Sun", "Uttara Phalguni"),
    ("Sun", "Mula"),
    ("Sun", "Uttara Ashadha"),
    ("Sun", "Uttara Bhadrapada"),
    ("Moon", "Rohini"),
    ("Moon", "Mrigashira"),
    ("Moon", "Pushya"),
    ("Moon", "Anuradha"),
    ("Moon", "Shravana"),
    ("Mars", "Ashwini"),
    ("Mars", "Krittika"),
    ("Mars", "Ashlesha"),
    ("Mars", "Uttara Bhadrapada"),
    ("Mercury", "Krittika"),
    ("Mercury", "Rohini"),
    ("Mercury", "Mrigashira"),
    ("Mercury", "Hasta"),
    ("Mercury", "Anuradha"),
    ("Jupiter", "Ashwini"),
    ("Jupiter", "Punarvasu"),
    ("Jupiter", "Pushya"),
    ("Jupiter", "Anuradha"),
    ("Jupiter", "Revati"),
    ("Venus", "Ashwini"),
    ("Venus", "Punarvasu"),
    ("Venus", "Anuradha"),
    ("Venus", "Shravana"),
    ("Venus", "Revati"),
    ("Saturn", "Rohini"),
    ("Saturn", "Swati"),
    ("Saturn", "Shravana"),
}

# Siddha — variant 1 (WE Ch.9 p.77)
SIDDHA_VN_1 = {
    ("Sun", "Uttara Phalguni"),
    ("Sun", "Hasta"),
    ("Sun", "Mula"),
    ("Sun", "Uttara Ashadha"),
    ("Sun", "Shravana"),
    ("Sun", "Uttara Bhadrapada"),
    ("Sun", "Revati"),
    ("Mars", "Ashwini"),
    ("Mars", "Uttara Phalguni"),
    ("Mars", "Uttara Bhadrapada"),
    ("Mars", "Revati"),
    ("Mercury", "Krittika"),
    ("Mercury", "Purva Phalguni"),
    ("Mercury", "Uttara Phalguni"),
    ("Mercury", "Anuradha"),
    ("Mercury", "Purva Ashadha"),
    ("Mercury", "Uttara Ashadha"),
    ("Mercury", "Purva Bhadrapada"),
    ("Venus", "Uttara Phalguni"),
    ("Venus", "Hasta"),
    ("Venus", "Chitra"),
    ("Venus", "Swati"),
    ("Venus", "Anuradha"),
    ("Venus", "Purva Ashadha"),
    ("Venus", "Uttara Ashadha"),
    ("Venus", "Shravana"),
    ("Venus", "Dhanishtha"),
    ("Venus", "Shatabhisha"),
    ("Venus", "Purva Bhadrapada"),
    ("Venus", "Uttara Bhadrapada"),
}

# Siddha — variant 2 (WE Ch.9 p.77)
SIDDHA_VN_2 = {
    ("Sun", "Mula"),
    ("Moon", "Dhanishtha"),
    ("Mars", "Uttara Bhadrapada"),
    ("Mercury", "Krittika"),
    ("Jupiter", "Punarvasu"),
    ("Venus", "Purva Phalguni"),
    ("Saturn", "Swati"),
}

# Amrita — "immortal" (WE Ch.9 p.77)
AMRITA_VN = {
    ("Moon", "Rohini"),
    ("Moon", "Mrigashira"),
    ("Moon", "Punarvasu"),
    ("Moon", "Swati"),
    ("Moon", "Shravana"),
    ("Mars", "Mrigashira"),
    ("Mars", "Punarvasu"),
    ("Mars", "Pushya"),
    ("Mars", "Ashlesha"),
    ("Mars", "Magha"),
    ("Mars", "Purva Phalguni"),
    ("Mars", "Hasta"),
    ("Mars", "Chitra"),
    ("Mars", "Swati"),
    ("Mercury", "Ardra"),
    ("Mercury", "Punarvasu"),
    ("Mercury", "Pushya"),
    ("Mercury", "Ashlesha"),
    ("Mercury", "Magha"),
    ("Mercury", "Hasta"),
    ("Mercury", "Chitra"),
    ("Mercury", "Swati"),
    ("Mercury", "Vishakha"),
    ("Mercury", "Shravana"),
    ("Jupiter", "Ashwini"),
    ("Jupiter", "Punarvasu"),
    ("Jupiter", "Pushya"),
    ("Jupiter", "Magha"),
    ("Jupiter", "Swati"),
    ("Venus", "Ashwini"),
    ("Venus", "Bharani"),
    ("Venus", "Purva Phalguni"),
    ("Venus", "Revati"),
    ("Saturn", "Krittika"),
    ("Saturn", "Rohini"),
    ("Saturn", "Shatabhisha"),
    ("Saturn", "Swati"),
}

# Subha — "auspicious" (WE Ch.9 p.78)
SUBHA_VN = {
    ("Mercury", "Rohini"),
    ("Mercury", "Jyeshtha"),
    ("Mercury", "Shatabhisha"),
    ("Mercury", "Uttara Bhadrapada"),
    ("Jupiter", "Bharani"),
    ("Jupiter", "Ashlesha"),
    ("Jupiter", "Vishakha"),
    ("Jupiter", "Anuradha"),
    ("Jupiter", "Jyeshtha"),
    ("Jupiter", "Mula"),
    ("Jupiter", "Purva Ashadha"),
    ("Jupiter", "Uttara Ashadha"),
    ("Jupiter", "Shravana"),
    ("Jupiter", "Dhanishtha"),
    ("Saturn", "Ashwini"),
    ("Saturn", "Bharani"),
    ("Saturn", "Mrigashira"),
    ("Saturn", "Ardra"),
    ("Saturn", "Pushya"),
    ("Saturn", "Magha"),
    ("Saturn", "Vishakha"),
    ("Saturn", "Anuradha"),
    ("Saturn", "Jyeshtha"),
    ("Saturn", "Mula"),
    ("Saturn", "Uttara Phalguni"),
    ("Saturn", "Shravana"),
    ("Saturn", "Dhanishtha"),
    ("Saturn", "Purva Bhadrapada"),
    ("Saturn", "Uttara Bhadrapada"),
}

# ---------------------------------------------------------------------------
# INAUSPICIOUS VARA × NAKSHATRA YOGAS  (WE Ch.9 pp.79-83)
# ---------------------------------------------------------------------------

# Dagdha — "burnt" variant 1 (WE Ch.9 p.79)
DAGDHA_VN_1 = {
    ("Sun", "Bharani"),
    ("Moon", "Chitra"),
    ("Mars", "Uttara Ashadha"),
    ("Mercury", "Dhanishtha"),
    ("Jupiter", "Uttara Phalguni"),
    ("Venus", "Jyeshtha"),
    ("Saturn", "Revati"),
}

# Dagdha — fatal variant for Jupiter's Vara (WE Ch.9 p.79)
DAGDHA_VN_FATAL = {
    ("Jupiter", "Krittika"),
    ("Jupiter", "Rohini"),
    ("Jupiter", "Mrigashira"),
    ("Jupiter", "Ardra"),
    ("Jupiter", "Uttara Phalguni"),
    ("Jupiter", "Shatabhisha"),
}

# Yamaghanta — "rein of death" (WE Ch.9 p.79)
YAMAGHANTA = {
    ("Sun", "Magha"),
    ("Moon", "Vishakha"),
    ("Mars", "Ardra"),
    ("Mercury", "Mula"),
    ("Jupiter", "Krittika"),
    ("Venus", "Rohini"),
    ("Saturn", "Hasta"),
}

# Utpata — "tearing out" (WE Ch.9 p.79)
UTPATA = {
    ("Sun", "Vishakha"),
    ("Moon", "Purva Ashadha"),
    ("Mars", "Dhanishtha"),
    ("Mercury", "Revati"),
    ("Jupiter", "Rohini"),
    ("Venus", "Pushya"),
    ("Saturn", "Uttara Phalguni"),
}

# Mrityu — "death" variant 1 (WE Ch.9 p.80)
MRITYU_VN_1 = {
    ("Sun", "Anuradha"),
    ("Moon", "Uttara Ashadha"),
    ("Mars", "Shatabhisha"),
    ("Mercury", "Ashwini"),
    ("Jupiter", "Mrigashira"),
    ("Venus", "Ashlesha"),
    ("Saturn", "Hasta"),
}

# Mrityu — variant 2, "indicates disaster" (WE Ch.9 p.80)
MRITYU_VN_2 = {
    ("Sun", "Vishakha"),
    ("Moon", "Purva Ashadha"),
    ("Mars", "Dhanishtha"),
    ("Mercury", "Anuradha"),
    ("Jupiter", "Mrigashira"),
    ("Venus", "Swati"),
    ("Venus", "Rohini"),
    ("Saturn", "Shravana"),
}

# Mrityu — variant 3, Saturn's Vara only (WE Ch.9 p.80)
MRITYU_VN_3 = {
    ("Saturn", "Punarvasu"),
    ("Saturn", "Ashlesha"),
    ("Saturn", "Purva Phalguni"),
    ("Saturn", "Hasta"),
    ("Saturn", "Chitra"),
    ("Saturn", "Purva Ashadha"),
    ("Saturn", "Uttara Ashadha"),
    ("Saturn", "Revati"),
}

# Kana — "one-eyed" (WE Ch.9 p.80)
KANA = {
    ("Sun", "Jyeshtha"),
    ("Moon", "Shravana"),
    ("Mars", "Purva Bhadrapada"),
    ("Mercury", "Bharani"),
    ("Jupiter", "Ardra"),
    ("Venus", "Magha"),
    ("Saturn", "Chitra"),
}

# Nasa — "loss" (WE Ch.9 p.80)
NASA = {
    ("Sun", "Ashwini"),
    ("Sun", "Magha"),
    ("Sun", "Vishakha"),
    ("Sun", "Anuradha"),
    ("Sun", "Jyeshtha"),
    ("Moon", "Krittika"),
    ("Moon", "Uttara Phalguni"),
    ("Moon", "Chitra"),
    ("Moon", "Vishakha"),
    ("Moon", "Purva Ashadha"),
    ("Moon", "Uttara Ashadha"),
    ("Moon", "Uttara Bhadrapada"),
    ("Mars", "Mrigashira"),
    ("Mars", "Ardra"),
    ("Mars", "Vishakha"),
    ("Mars", "Uttara Ashadha"),
    ("Mars", "Dhanishtha"),
    ("Mars", "Shatabhisha"),
    ("Mars", "Purva Bhadrapada"),
    ("Mercury", "Ashwini"),
    ("Mercury", "Bharani"),
    ("Mercury", "Mula"),
    ("Mercury", "Dhanishtha"),
    ("Mercury", "Revati"),
    ("Jupiter", "Uttara Phalguni"),
    ("Venus", "Rohini"),
    ("Venus", "Pushya"),
    ("Venus", "Ashlesha"),
    ("Venus", "Magha"),
    ("Venus", "Vishakha"),
    ("Venus", "Jyeshtha"),
    ("Saturn", "Revati"),
}

# ---------------------------------------------------------------------------
# TRIPLE COMBINATION: TRIPUSHKARA / DVIPUSHKARA  (WE Ch.9 pp.81-82)
# Malefic Vara (Sun, Mars, Saturn) + Bhadra Tithi + specific Nakshatra class
# Tripushkara: event repeats 3×; Dvipushkara: event repeats 2×.
# Use carefully — auspicious for things one wants repeated, avoid for marriage.
# ---------------------------------------------------------------------------

MALEFIC_VARA = {"Sun", "Mars", "Saturn"}
TRIPADA_NAK = {  # Tripushkara (WE p.81): 3-pada nakshatras (Sun/Jupiter ruled)
    "Krittika",
    "Punarvasu",
    "Uttara Phalguni",
    "Vishakha",
    "Uttara Ashadha",
    "Purva Bhadrapada",
}
DVIPADA_NAK = {  # Dvipushkara (WE p.82): 2-pada nakshatras (Mars ruled)
    "Mrigashira",
    "Chitra",
    "Dhanishtha",
}

# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

WEEKDAYS_LIST = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
VARA_LORD_MAP = {day: lord for day, lord in zip(WEEKDAYS_LIST, VARA_LORD)}


@dataclass
class MuhurtaYogaHit:
    name: str
    nature: str  # auspicious | inauspicious | mixed
    source: str
    detail: str
    strength: int = 1  # 1=Vara/Tithi, 3=Vara/Nak, 9=triple


@dataclass
class MuhurtaYogaResult:
    active: list[MuhurtaYogaHit] = field(default_factory=list)
    overall: str = "neutral"
    score: int = 0
    summary: str = ""


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def _vara_lord(weekday: str) -> str:
    return VARA_LORD_MAP.get(weekday, VARA_LORD[0])


def _tithi_tip(tithi_num: int) -> int:
    if tithi_num == 30:
        return 15
    return ((tithi_num - 1) % 15) + 1


def _tithi_group_name(tip: int) -> str:
    groups = {
        1: "Nanda",
        6: "Nanda",
        11: "Nanda",
        2: "Bhadra",
        7: "Bhadra",
        12: "Bhadra",
        3: "Jaya",
        8: "Jaya",
        13: "Jaya",
        4: "Rikta",
        9: "Rikta",
        14: "Rikta",
        5: "Purna",
        10: "Purna",
        15: "Purna",
    }
    return groups.get(tip, "Bhadra")


def _is_bhadra(tip: int) -> bool:
    return tip in (2, 7, 12)


# ---------------------------------------------------------------------------
# MAIN API
# ---------------------------------------------------------------------------


def evaluate_muhurta_yogas(
    weekday: str,
    tithi_num: int,
    nakshatra: str | None = None,
    graph_hits: list[dict] | None = None,
) -> MuhurtaYogaResult:
    """
    Evaluate all Vara/Tithi/Nakshatra combination yogas for a muhurta moment.

    Strength weights (WE Ch.9 p.83):
      Vara/Tithi = 1 unit
      Vara/Nakshatra = 3 units
      Vara/Tithi/Nakshatra = 9 units (checked separately when nak is given)
    """
    result = MuhurtaYogaResult()
    vara = _vara_lord(weekday)
    tip = _tithi_tip(tithi_num)
    group = "Purna" if tithi_num in (15, 30) else _tithi_group_name(tip)

    hits: list[tuple[str, str, str, str, int]] = []  # name, nature, source, detail, strength

    # ── VARA × TITHI ────────────────────────────────────────────────────────
    src_vt = "Wilhelm-Ernst-Classical-Muhurta-Ch9-p75"

    if (vara, group) in SIDDHA_VT:
        hits.append(("Siddha", "auspicious", src_vt, f"{group} tithi on {vara}'s day", 1))
    if (vara, group) in AMRITA_VT:
        hits.append(("Amrita", "auspicious", src_vt, f"{group} tithi on {vara}'s day", 1))
    if (vara, tip) in DAGDHA_VT:
        hits.append(
            (
                "Dagdha",
                "inauspicious",
                src_vt,
                f"Tithi {tip} on {vara}'s day — avoid all actions",
                1,
            )
        )
    if (vara, tip) in VISHA_VT:
        hits.append(
            (
                "Visha",
                "inauspicious",
                src_vt,
                f"Tithi {tip} on {vara}'s day — poison combination",
                1,
            )
        )
    if (vara, tip) in KRAKACHA_VT:
        hits.append(
            (
                "Krakacha",
                "inauspicious",
                src_vt,
                f"Tithi {tip} on {vara}'s day — saw/cutting effect",
                1,
            )
        )
    if (vara, tip) in HUTASANA_VT:
        hits.append(
            (
                "Hutasana",
                "inauspicious",
                src_vt,
                f"Tithi {tip} on {vara}'s day — fire/destruction",
                1,
            )
        )
    if (vara, tip) in SAMVARTAKA_VT:
        hits.append(
            ("Samvartaka", "inauspicious", src_vt, f"Tithi {tip} on {vara}'s day — dissolution", 1)
        )

    # ── VARA × NAKSHATRA ────────────────────────────────────────────────────
    if nakshatra:
        src_vn = "Wilhelm-Ernst-Classical-Muhurta-Ch9-p77"
        src_vn_bad = "Wilhelm-Ernst-Classical-Muhurta-Ch9-p79"

        if (vara, nakshatra) in SARVARTHA_SIDDHI:
            hits.append(
                (
                    "Sarvartha Siddhi",
                    "auspicious",
                    src_vn,
                    f"{nakshatra} on {vara}'s day — complete accomplishment (3× strength)",
                    3,
                )
            )
        if (vara, nakshatra) in SIDDHA_VN_1 or (vara, nakshatra) in SIDDHA_VN_2:
            hits.append(
                (
                    "Siddha (Nak)",
                    "auspicious",
                    src_vn,
                    f"{nakshatra} on {vara}'s day — accomplished yoga (3× strength)",
                    3,
                )
            )
        if (vara, nakshatra) in AMRITA_VN:
            hits.append(
                (
                    "Amrita (Nak)",
                    "auspicious",
                    src_vn,
                    f"{nakshatra} on {vara}'s day — immortal yoga (3× strength)",
                    3,
                )
            )
        if (vara, nakshatra) in SUBHA_VN:
            hits.append(
                ("Subha", "auspicious", src_vn, f"{nakshatra} on {vara}'s day — auspicious yoga", 3)
            )

        if (vara, nakshatra) in DAGDHA_VN_1:
            hits.append(
                (
                    "Dagdha (Nak)",
                    "inauspicious",
                    src_vn_bad,
                    f"{nakshatra} on {vara}'s day — burnt yoga, avoid all actions",
                    3,
                )
            )
        if (vara, nakshatra) in DAGDHA_VN_FATAL:
            hits.append(
                (
                    "Dagdha (Fatal)",
                    "inauspicious",
                    src_vn_bad,
                    f"{nakshatra} on Jupiter's day — fatal Dagdha yoga",
                    3,
                )
            )
        if (vara, nakshatra) in YAMAGHANTA:
            hits.append(
                (
                    "Yamaghanta",
                    "inauspicious",
                    src_vn_bad,
                    f"{nakshatra} on {vara}'s day — rein of death yoga",
                    3,
                )
            )
        if (vara, nakshatra) in UTPATA:
            hits.append(
                (
                    "Utpata",
                    "inauspicious",
                    src_vn_bad,
                    f"{nakshatra} on {vara}'s day — tearing out yoga",
                    3,
                )
            )
        if (
            (vara, nakshatra) in MRITYU_VN_1
            or (vara, nakshatra) in MRITYU_VN_2
            or (vara, nakshatra) in MRITYU_VN_3
        ):
            hits.append(
                (
                    "Mrityu",
                    "inauspicious",
                    src_vn_bad,
                    f"{nakshatra} on {vara}'s day — death yoga, strongly avoid",
                    3,
                )
            )
        if (vara, nakshatra) in KANA:
            hits.append(
                (
                    "Kana",
                    "inauspicious",
                    src_vn_bad,
                    f"{nakshatra} on {vara}'s day — one-eyed (partial loss) yoga",
                    3,
                )
            )
        if (vara, nakshatra) in NASA:
            hits.append(
                ("Nasa", "inauspicious", src_vn_bad, f"{nakshatra} on {vara}'s day — loss yoga", 3)
            )

        # ── TRIPLE: TRIPUSHKARA / DVIPUSHKARA ───────────────────────────────
        src_tri = "Wilhelm-Ernst-Classical-Muhurta-Ch9-p81"
        if vara in MALEFIC_VARA and _is_bhadra(tip):
            if nakshatra in TRIPADA_NAK:
                hits.append(
                    (
                        "Tripushkara",
                        "mixed",
                        src_tri,
                        f"Malefic Vara ({vara}) + Bhadra Tithi ({tip}) + Tripada Nak ({nakshatra})"
                        " — event repeats 3× (favor for repetitions, avoid marriage)",
                        9,
                    )
                )
            elif nakshatra in DVIPADA_NAK:
                hits.append(
                    (
                        "Dvipushkara",
                        "mixed",
                        src_tri,
                        f"Malefic Vara ({vara}) + Bhadra Tithi ({tip}) + Dvipada Nak ({nakshatra})"
                        " — event repeats 2× (favor for repetitions, avoid marriage)",
                        9,
                    )
                )

    # ── GRAPH-SOURCED HITS ──────────────────────────────────────────────────
    for gh in graph_hits or []:
        name = gh.get("name") or gh.get("label", "Muhurta yoga")
        nature = gh.get("nature") or gh.get("verdict", "mixed")
        hits.append((name, nature, gh.get("source", "graph.json"), gh.get("detail", ""), 1))

    # ── SCORE (weighted by strength) ────────────────────────────────────────
    score = 0
    for name, nature, source, detail, strength in hits:
        result.active.append(
            MuhurtaYogaHit(
                name=name, nature=nature, source=source, detail=detail, strength=strength
            )
        )
        if nature == "auspicious":
            score += strength
        elif nature == "inauspicious":
            score -= strength * 2  # inauspicious outweighs auspicious per WE p.84

    result.score = score
    if score >= 3:
        result.overall = "auspicious"
    elif score <= -3:
        result.overall = "inauspicious"
    else:
        result.overall = "neutral"

    if result.active:
        names = ", ".join(h.name for h in result.active[:4])
        result.summary = f"Muhurta yogas: {names} ({result.overall}, score {score:+d})"
    else:
        result.summary = "No Vara/Tithi/Nakshatra combination yogas detected"
    return result


def muhurta_yogas_to_dict(r: MuhurtaYogaResult) -> dict:
    return {
        "overall": r.overall,
        "score": r.score,
        "summary": r.summary,
        "active": [
            {
                "name": h.name,
                "nature": h.nature,
                "source": h.source,
                "detail": h.detail,
                "strength": h.strength,
            }
            for h in r.active
        ],
    }
