"""
Fructification Engine — finds the WHEN within a dasha period.

Classical doctrine (Phaladeepika Ch.26 / Goel 2002):
  The dasha period defines the DOMAIN (career, wealth, health, family).
  Saturn + Jupiter double-transit from Janma Rashi confirms the TIMING — the
  specific months within the AD when the dasha promise actually manifests.

  For Yogini dasha (Goel), the Progressed Lagna (sign of the contributing
  nakshatra for the running Yogini in the current 36-year cycle) and the
  contributing nakshatra's Star Lord natal position serve as additional
  reference points beyond Janma Rashi.

Ashtakavarga (BPHS Ch.67): SAV bindus in Saturn's transit sign weight
  the strength of the fructification window (7=exceptional, 5+=strong, 4=moderate).

Vedha (Phaladeepika Ch.26 / GPD Ch.22): if another planet occupies the
  Vedha house of Saturn or Jupiter during their "good" transit, the benefit
  is cancelled — EXCEPT Sun-Saturn and Moon-Mercury pairs (exempt).

Nothing here is invented. Every rule traces to the source texts.
"""

from __future__ import annotations

from datetime import date

from vedic_engine.core.astronomy import all_positions, ascendant, julian_day, lahiri_ayanamsha
from vedic_engine.rules.transit_rules import GOCHARA_VEDHA, TRANSIT_HOUSES, VEDHA_EXEMPT_PAIRS

# ── Constants ────────────────────────────────────────────────────────────────

RASHIS_12 = [
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

YOGINI_ORDER = [
    "Mangala",
    "Pingala",
    "Dhanya",
    "Bhramari",
    "Bhadrika",
    "Ulka",
    "Siddha",
    "Sankata",
]

# Nakshatra (1-indexed, 1=Ashwini) → the sign (0=Aries) where it starts.
# Uses the sign containing the nakshatra's FIRST pada.
NAK_PRIMARY_SIGN: dict[int, int] = {
    1: 0,  # Ashwini   0°
    2: 0,  # Bharani   13°20'
    3: 1,  # Krittika  26°40' (mostly Taurus: 10° in Tau, 3°20' in Aries)
    4: 1,  # Rohini    40°
    5: 1,  # Mrigashira 53°20' (starts in Taurus)
    6: 2,  # Ardra     66°40'
    7: 2,  # Punarvasu 80° (starts in Gemini)
    8: 3,  # Pushya    93°20'
    9: 3,  # Ashlesha  106°40'
    10: 4,  # Magha     120°
    11: 4,  # Purva Phalguni 133°20'
    12: 5,  # Uttara Phalguni 146°40' (mostly Virgo)
    13: 5,  # Hasta     160°
    14: 5,  # Chitra    173°20' (starts in Virgo)
    15: 6,  # Swati     186°40'
    16: 6,  # Vishakha  200° (starts in Libra)
    17: 7,  # Anuradha  213°20'
    18: 7,  # Jyeshtha  226°40'
    19: 8,  # Mula      240°
    20: 8,  # Purva Ashadha 253°20'
    21: 8,  # Uttara Ashadha 266°40' (starts in Sagittarius)
    22: 9,  # Shravana  280°
    23: 9,  # Dhanishtha 293°20' (starts in Capricorn)
    24: 10,  # Shatabhisha 306°40'
    25: 10,  # Purva Bhadrapada 320° (starts in Aquarius)
    26: 11,  # Uttara Bhadrapada 333°20'
    27: 11,  # Revati    346°40'
}

# Domain effects for key Saturn benefic houses (GPD / Phaladeepika Ch.26)
_SAT_HOUSE_DOMAINS: dict[int, list[str]] = {
    3: ["communication", "courage", "siblings"],
    6: ["overcoming obstacles", "health recovery", "defeating competition"],
    9: ["long-distance travel", "luck", "spiritual pursuits"],
    11: ["gains", "income", "fulfilment of desires"],
}

# Domain effects for key Jupiter benefic houses
_JUP_HOUSE_DOMAINS: dict[int, list[str]] = {
    2: ["wealth", "family", "speech"],
    5: ["intellect", "children", "investments", "creativity"],
    7: ["partnerships", "marriage", "business"],
    9: ["fortune", "higher education", "dharma"],
    11: ["gains", "income", "fulfilment"],
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _sign(lon: float) -> int:
    """Sidereal longitude → 0-indexed sign (0=Aries)."""
    return int(lon // 30) % 12


def _transit_house(transit_sign: int, ref_sign: int) -> int:
    """1-indexed house of transit_sign from ref_sign."""
    return (transit_sign - ref_sign) % 12 + 1


def _benefic(planet: str, house: int) -> bool:
    return house in TRANSIT_HOUSES.get(planet, {}).get("good", [])


def _vedha_blocked(planet: str, house: int, other_houses: dict[str, int]) -> bool:
    """True if a planet in the Vedha position cancels this transit (GPD Ch.22)."""
    vedha_h = GOCHARA_VEDHA.get(planet, {}).get("vedha", {}).get(house)
    if vedha_h is None:
        return False
    for other, oh in other_houses.items():
        if frozenset({planet, other}) in VEDHA_EXEMPT_PAIRS:
            continue
        if oh == vedha_h:
            return True
    return False


def _house_domains(planet: str, house: int) -> list[str]:
    if planet == "Saturn":
        return _SAT_HOUSE_DOMAINS.get(house, [f"house {house}"])
    return _JUP_HOUSE_DOMAINS.get(house, [f"house {house}"])


# ── Yogini Progressed Lagna ──────────────────────────────────────────────────


def _yogini_24slot_sequence(birth_nak_1idx: int) -> list[int]:
    """
    24-slot nakshatra sequence for Yogini dasha (Goel 2002/2006 BPHS).

    Nakshatras 1 (Ashwini), 2 (Bharani), 3 (Krittika) are clubbed with
    25 (Purva Bhadrapada), 26 (Uttara Bhadrapada), 27 (Revati) — they share
    a slot and are skipped in the main zodiacal progression UNLESS the native's
    birth nakshatra is one of them (in which case they begin the sequence).
    """
    CLUBBED = {1, 2, 3}
    birth_in_clubbed = birth_nak_1idx in CLUBBED
    seq: list[int] = []
    n = birth_nak_1idx
    while len(seq) < 24:
        seq.append(n)
        n = n % 27 + 1
        if not birth_in_clubbed:
            while n in CLUBBED:
                n = n % 27 + 1
    return seq


def compute_progressed_lagna(
    birth_nak_1idx: int,
    birth_date: date,
    maha_start_date: date,
    maha_yogini_name: str,
) -> tuple[int, int]:
    """
    Progressed Lagna for a running Yogini Mahadasha (Goel).

    Returns: (prog_lagna_sign_idx 0-11, contributing_nak_1idx 1-27)

    The contributing nakshatra is the one mapped to this Yogini in this cycle.
    The Progressed Lagna = the sign where that nakshatra starts.
    The Star Lord (Vimshottari lord of the contributing nakshatra) is the
    predictive key Goel identifies for transit timing.
    """
    if maha_yogini_name not in YOGINI_ORDER:
        return 0, 1  # fallback

    # 0-indexed starting Yogini at birth: formula (nak_1idx + 3) % 8, then -1 for 0-indexed
    starting_yogini_idx = (birth_nak_1idx + 2) % 8

    running_idx = YOGINI_ORDER.index(maha_yogini_name)
    position_in_cycle = (running_idx - starting_yogini_idx) % 8

    years_elapsed = max(0.0, (maha_start_date - birth_date).days / 365.25)
    cycle = min(3, int(years_elapsed / 36) + 1)

    slot = (cycle - 1) * 8 + position_in_cycle
    seq = _yogini_24slot_sequence(birth_nak_1idx)
    contrib_nak = seq[slot % 24]  # safety wrap

    return NAK_PRIMARY_SIGN[contrib_nak], contrib_nak


# ── Monthly sweep ────────────────────────────────────────────────────────────


def _sweep_months(
    start: date,
    end: date,
    ref_signs: list[tuple[str, int]],
    sav: list[int] | None,
    lat: float,
    lon: float,
    tz: float,
) -> list[dict]:
    """Sweep monthly from start to end, returning per-month evaluation dicts."""
    results: list[dict] = []

    cur = date(start.year, start.month, 1)
    end_m = date(end.year, end.month, 1)

    while cur <= end_m:
        jd = julian_day(cur.year, cur.month, cur.day, 12.0 - tz)
        all_pos = all_positions(jd)
        planet_signs: dict[str, int] = {p: _sign(lon_) for p, lon_ in all_pos.items()}

        sat_s = planet_signs.get("Saturn", 0)
        jup_s = planet_signs.get("Jupiter", 0)

        for ref_label, ref_sign in ref_signs:
            sat_house = _transit_house(sat_s, ref_sign)
            jup_house = _transit_house(jup_s, ref_sign)

            other_houses = {
                p: _transit_house(s, ref_sign)
                for p, s in planet_signs.items()
                if p not in {"Saturn", "Jupiter"}
            }

            sat_good = _benefic("Saturn", sat_house) and not _vedha_blocked(
                "Saturn", sat_house, other_houses
            )
            jup_good = _benefic("Jupiter", jup_house) and not _vedha_blocked(
                "Jupiter", jup_house, other_houses
            )

            sav_bindus = sav[sat_s] if sav else None

            results.append(
                {
                    "date": cur.isoformat(),
                    "ref_label": ref_label,
                    "ref_sign": ref_sign,
                    "saturn_house": sat_house,
                    "saturn_sign": sat_s,
                    "saturn_good": sat_good,
                    "jupiter_house": jup_house,
                    "jupiter_sign": jup_s,
                    "jupiter_good": jup_good,
                    "double_transit": sat_good and jup_good,
                    "sav_bindus": sav_bindus,
                }
            )

        # advance month
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)

    return results


def _group_windows(months: list[dict]) -> list[dict]:
    """Group consecutive double-transit months into fructification windows."""
    windows: list[dict] = []
    run_start: int | None = None

    for i, m in enumerate(months):
        if m["double_transit"]:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None:
                windows.append(_build_window(months[run_start:i]))
                run_start = None
    if run_start is not None:
        windows.append(_build_window(months[run_start:]))

    return windows


def _build_window(months: list[dict]) -> dict:
    if not months:
        return {}

    first = months[0]
    last_dt = date.fromisoformat(months[-1]["date"])
    if last_dt.month == 12:
        end_dt = date(last_dt.year + 1, 1, 1)
    else:
        end_dt = date(last_dt.year, last_dt.month + 1, 1)

    sav_vals = [m["sav_bindus"] for m in months if m["sav_bindus"] is not None]
    avg_sav = sum(sav_vals) / len(sav_vals) if sav_vals else None
    rounded_sav = round(avg_sav) if avg_sav is not None else None

    sat_h = first["saturn_house"]
    jup_h = first["jupiter_house"]
    ref_label = first["ref_label"]

    sat_effects = _house_domains("Saturn", sat_h)
    jup_effects = _house_domains("Jupiter", jup_h)

    # Score: base 5 for double transit, +0–3 from SAV bindus
    score = 5
    if avg_sav is not None:
        score += max(0, min(3, int(avg_sav) - 3))
    score = max(0, min(10, score))

    if rounded_sav is not None:
        if rounded_sav >= 7:
            strength = "exceptional"
        elif rounded_sav >= 5:
            strength = "strong"
        elif rounded_sav >= 4:
            strength = "moderate"
        else:
            strength = "limited"
    else:
        strength = "moderate"

    all_effects = sat_effects + jup_effects
    domains = list(
        {d for d in all_effects if d in ("wealth", "career", "health", "family", "gains", "income")}
    )

    narrative = (
        f"Saturn in {sat_h}th ({', '.join(sat_effects)}) · "
        f"Jupiter in {jup_h}th ({', '.join(jup_effects)}) from {ref_label}"
    )
    if rounded_sav is not None:
        from vedic_engine.prediction.ashtakavarga import BINDU_RESULTS

        bindu_label = BINDU_RESULTS.get(min(rounded_sav, 8), ("", "", ""))[0]
        narrative += f" — SAV {rounded_sav} bindus ({bindu_label})"

    return {
        "start": first["date"],
        "end": end_dt.isoformat(),
        "duration_months": len(months),
        "ref_label": ref_label,
        "saturn": {
            "house": sat_h,
            "sign": RASHIS_12[first["saturn_sign"]],
        },
        "jupiter": {
            "house": jup_h,
            "sign": RASHIS_12[first["jupiter_sign"]],
        },
        "sav_bindus": rounded_sav,
        "strength": strength,
        "domains": domains,
        "narrative": narrative,
        "score": score,
    }


def _merge_overlapping(windows: list[dict]) -> list[dict]:
    """Merge overlapping windows from different reference points."""
    if not windows:
        return []
    windows_s = sorted(windows, key=lambda w: w["start"])
    merged: list[dict] = [dict(windows_s[0])]
    for w in windows_s[1:]:
        last = merged[-1]
        if w["start"] <= last["end"]:
            # Merge: keep higher score, extend end
            if w["score"] > last["score"]:
                last.update(w)
            last["end"] = max(last["end"], w["end"])
            last["duration_months"] = max(last["duration_months"], w["duration_months"])
        else:
            merged.append(dict(w))
    return merged


# ── Main API ─────────────────────────────────────────────────────────────────


def fructify(
    birth_datetime: str,
    birth_lat: float,
    birth_lon: float,
    birth_tz: float,
    system: str,
    maha_lord: str,
    antar_lord: str,
    maha_start: str,
    maha_end: str,
    antar_start: str,
    antar_end: str,
) -> dict:
    """
    Compute fructification windows for a dasha antardasha period.

    The dasha (MD/AD) defines what life domain is activated.
    Saturn + Jupiter double transit from Janma Rashi and Progressed Lagna
    (for Yogini) confirms the TIMING within the AD when events manifest.

    Sources:
      - Phaladeepika Ch.26 (Mantreswara) — double transit criterion
      - GPD Ch.22 — Vedha cancellation rules
      - BPHS Ch.67 — Ashtakavarga SAV bindu strength
      - Goel (2002/2006) — Progressed Lagna for Yogini
    """
    from datetime import datetime

    from vedic_engine.core.panchanga import NAK_LORD
    from vedic_engine.prediction.ashtakavarga import compute_ashtakavarga

    # Parse birth
    birth_dt = datetime.fromisoformat(birth_datetime)
    birth_date_obj = birth_dt.date()
    birth_hour = birth_dt.hour + birth_dt.minute / 60.0 + birth_dt.second / 3600.0

    jd = julian_day(birth_dt.year, birth_dt.month, birth_dt.day, birth_hour - birth_tz)

    # Natal positions
    natal_pos = all_positions(jd)
    natal_sign: dict[str, int] = {
        p: _sign(l)
        for p, l in natal_pos.items()
        if p in {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
    }

    # Lagna
    ayan = lahiri_ayanamsha(jd)
    lagna_lon = ascendant(jd, birth_lat, birth_lon, ayan)
    lagna_sign = _sign(lagna_lon)

    # Janma Rashi (Moon sign)
    moon_lon = natal_pos.get("Moon", 0.0)
    janma_rashi = _sign(moon_lon)

    # Birth nakshatra (1-indexed, 1=Ashwini)
    birth_nak_1idx = int(moon_lon / (360 / 27)) % 27 + 1

    # Ashtakavarga SAV
    akv = compute_ashtakavarga(natal_sign, lagna_sign)
    sav = akv.sav  # 12-element list, sav[sign_idx] = bindus

    # Date objects
    antar_start_date = date.fromisoformat(antar_start)
    antar_end_date = date.fromisoformat(antar_end)
    maha_start_date = date.fromisoformat(maha_start)

    # Reference signs: Janma Rashi + Natal Lagna for all systems
    ref_signs: list[tuple[str, int]] = [
        ("Janma Rashi", janma_rashi),
        ("Natal Lagna", lagna_sign),
    ]

    # For Yogini: add Progressed Lagna + Star Lord natal position (Goel)
    prog_lagna_info: dict | None = None
    if system == "yogini" and maha_lord in YOGINI_ORDER:
        prog_sign, contrib_nak = compute_progressed_lagna(
            birth_nak_1idx, birth_date_obj, maha_start_date, maha_lord
        )
        years_elapsed = max(0.0, (maha_start_date - birth_date_obj).days / 365.25)
        cycle_no = min(3, int(years_elapsed / 36) + 1)

        prog_label = f"Progressed Lagna (cycle {cycle_no})"
        ref_signs.append((prog_label, prog_sign))

        # Star lord of contributing nakshatra
        star_lord = NAK_LORD[contrib_nak - 1]  # NAK_LORD is 0-indexed
        if star_lord in natal_sign:
            sl_sign = natal_sign[star_lord]
            ref_signs.append((f"Star Lord ({star_lord}) natal", sl_sign))

        prog_lagna_info = {
            "contributing_nak": contrib_nak,
            "contributing_nak_name": _nak_name(contrib_nak),
            "star_lord": star_lord,
            "cycle": cycle_no,
            "progressed_lagna": RASHIS_12[prog_sign],
        }

    # Sweep + group
    month_rows = _sweep_months(
        antar_start_date,
        antar_end_date,
        ref_signs=ref_signs,
        sav=sav,
        lat=birth_lat,
        lon=birth_lon,
        tz=birth_tz,
    )
    all_windows: list[dict] = []
    for ref_label, ref_sign in ref_signs:
        ref_months = [m for m in month_rows if m["ref_label"] == ref_label]
        all_windows.extend(_group_windows(ref_months))

    windows = _merge_overlapping(all_windows)
    windows.sort(key=lambda w: w["start"])

    # Reference point summary for UI
    ref_details = [{"label": label, "sign": RASHIS_12[sign_idx]} for label, sign_idx in ref_signs]

    return {
        "system": system,
        "maha_lord": maha_lord,
        "antar_lord": antar_lord,
        "antar_start": antar_start,
        "antar_end": antar_end,
        "janma_rashi": RASHIS_12[janma_rashi],
        "natal_lagna": RASHIS_12[lagna_sign],
        "reference_points": ref_details,
        "progressed_lagna": prog_lagna_info,
        "windows": windows,
        "total_windows": len(windows),
        "source": (
            "Phaladeepika Ch.26 (Mantreswara) — double transit criterion | "
            "GPD Ch.22 — Vedha | BPHS Ch.67 — Ashtakavarga SAV"
            + (" | Goel (2002/2006) — Progressed Lagna" if prog_lagna_info else "")
        ),
    }


def _nak_name(nak_1idx: int) -> str:
    NAMES = [
        "Ashwini",
        "Bharani",
        "Krittika",
        "Rohini",
        "Mrigashira",
        "Ardra",
        "Punarvasu",
        "Pushya",
        "Ashlesha",
        "Magha",
        "Purva Phalguni",
        "Uttara Phalguni",
        "Hasta",
        "Chitra",
        "Swati",
        "Vishakha",
        "Anuradha",
        "Jyeshtha",
        "Mula",
        "Purva Ashadha",
        "Uttara Ashadha",
        "Shravana",
        "Dhanishtha",
        "Shatabhisha",
        "Purva Bhadrapada",
        "Uttara Bhadrapada",
        "Revati",
    ]
    idx = (nak_1idx - 1) % 27
    return NAMES[idx]


# ── Nakshatra Vedha (Gochar Phaladeepika, Nakshathra Vedha chapter) ──────────
#
# Rule source: graph node gochar_phaladeepika_pulippani_nakshatra_vedha
#   label: "Nakshatra Vedha: transit effects through stars neutralised by a
#           planet occupying a specified Nakshatra counted from natal planet's
#           star (16 positions)"
#
# When a planet transits through a nakshatra, the good result is CANCELLED if
# another planet (other than the transiting one) currently occupies the
# nakshatra that is 16 stars counted from the natal planet's birth star.
# This is distinct from sign-level Gochara Vedha (GPD Ch.22).
#
# The count of 16 comes directly from the GPD chapter title / graph node
# label. Exemptions: the Vedha-exempt pairs from Gochara Vedha
# (Sun-Saturn, Moon-Mercury) are not stated for Nakshatra Vedha in the
# text, so no exemptions are applied here.

_NAKSHATRA_VEDHA_COUNT = 16  # GPD Nakshathra Vedha chapter


def nakshatra_vedha_check(
    transit_planet: str,
    natal_nakshatra_1idx: int,
    current_positions: dict[str, int],
) -> dict:
    """
    Check whether Nakshatra Vedha cancels the transiting planet's good result.

    Implements the rule from Gochar Phaladeepika (Pulippani), Nakshathra Vedha
    chapter — graph node gochar_phaladeepika_pulippani_nakshatra_vedha.

    Args:
        transit_planet: Name of the planet currently transiting (e.g. 'Jupiter').
        natal_nakshatra_1idx: Birth star of the native, 1-indexed (1=Ashwini…27=Revati).
        current_positions: Mapping of planet_name → current nakshatra (1-indexed).
                           Should include all transiting planets except the one
                           being checked.

    Returns:
        dict with keys:
          vedha_active (bool)     — True if the Nakshatra Vedha is triggered.
          vedha_nak_1idx (int)    — The Vedha nakshatra position (1-indexed).
          vedha_nak_name (str)    — Human-readable name of the Vedha star.
          blocking_planet (str|None) — Planet occupying the Vedha star, if any.
          source (str)            — Textual provenance citation.
    """
    if natal_nakshatra_1idx < 1:
        return {
            "vedha_active": False,
            "vedha_nak_1idx": None,
            "vedha_nak_name": None,
            "blocking_planet": None,
            "source": "gochar_phaladeepika_pulippani_nakshatra_vedha",
        }

    # Vedha nakshatra: 16th star counted from natal birth star (1-indexed, wrap at 27)
    vedha_1idx = ((natal_nakshatra_1idx - 1 + _NAKSHATRA_VEDHA_COUNT - 1) % 27) + 1
    vedha_name = _nak_name(vedha_1idx)

    blocking_planet = None
    for planet, nak_1idx in current_positions.items():
        if planet == transit_planet:
            continue  # skip self
        if nak_1idx == vedha_1idx:
            blocking_planet = planet
            break

    return {
        "vedha_active": blocking_planet is not None,
        "vedha_nak_1idx": vedha_1idx,
        "vedha_nak_name": vedha_name,
        "blocking_planet": blocking_planet,
        "source": "GPD Nakshathra Vedha chapter | graph:gochar_phaladeepika_pulippani_nakshatra_vedha",
    }
