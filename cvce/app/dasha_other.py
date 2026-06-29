"""
Yogini and Ashtottari dasha tree builders.
Both libraries return flat rows: [(lords_tuple, (Y,M,D,H), duration_years), ...]
"""
from __future__ import annotations

from datetime import date as _d, timedelta as _td

PLANET_NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
LEVEL_LABELS  = {1: "Mahadasha", 2: "Antardasha", 3: "Pratyantardasha"}

# Yogini dasha: each planet corresponds to a specific Yogini deity
# Source: BPHS Yogini Dasha Adhyaya + Goel "Predict Effectively Through Yogini Dasha" (KN Rao series)
YOGINI_BY_PLANET: dict[int, str] = {
    1: "Mangala",   # Moon  — 1 year
    0: "Pingala",   # Sun   — 2 years
    4: "Dhanya",    # Jupiter — 3 years
    2: "Bhramari",  # Mars  — 4 years
    3: "Bhadrika",  # Mercury — 5 years
    6: "Ulka",      # Saturn — 6 years
    5: "Siddha",    # Venus — 7 years
    7: "Sankata",   # Rahu  — 8 years
}

# Yogini dasha years per planet (planet_id → dasha years)
# Classical: Mangala=1, Pingala=2, Dhanya=3, Bhramari=4, Bhadrika=5, Ulka=6, Siddha=7, Sankata=8
YOGINI_YEARS: dict[int, int] = {1: 1, 0: 2, 4: 3, 2: 4, 3: 5, 6: 6, 5: 7, 7: 8}
YOGINI_TOTAL_YEARS = 36  # 1+2+3+4+5+6+7+8


def _lord_name(pid: int) -> str:
    return PLANET_NAMES[pid] if 0 <= pid < len(PLANET_NAMES) else str(pid)


def _yogini_name(pid: int) -> str | None:
    return YOGINI_BY_PLANET.get(pid)


def _fmt(t) -> str:
    return f"{int(t[0]):04d}-{int(t[1]):02d}-{int(t[2]):02d}"


def _to_date(t) -> _d:
    return _d(int(t[0]), int(t[1]), int(t[2]))


def _end_date(start_t, dur_years: float) -> _d:
    return _to_date(start_t) + _td(days=int(float(dur_years) * 365.25))


def _build_tree_and_ladder(flat_rows: list) -> tuple[list, list]:
    """
    Parse flat period rows into a Mahadasha tree + running ladder.

    flat_rows: [(lords_tuple, (Y,M,D,...), duration_years), ...]

    Yogini and Ashtottari only emit depth=2 (antardasha) rows.
    We group consecutive rows by Mahadasha to form blocks — this correctly
    handles repeating cycles (Yogini repeats every 36 years).

    Returns: (tree, current_ladder)
    """
    today = _d.today()

    # ── Step 1: collect and sort all valid depth=2 rows ─────────────────────

    parsed: list[tuple[_d, tuple, str, str, float]] = []
    # (start_date, lords, start_str, end_str, dur_years)

    for row in (flat_rows or []):
        try:
            lords = row[0]
            st    = row[1]
            dur   = float(row[2])
            depth = len(lords) if isinstance(lords, (list, tuple)) else 0
            if depth < 1:
                continue
            if not (isinstance(st, (list, tuple)) and len(st) >= 3):
                continue
            s = _to_date(st)
            e = _end_date(st, dur)
            parsed.append((s, lords, _fmt(st), e.isoformat(), dur))
        except Exception:
            continue

    parsed.sort(key=lambda x: x[0])

    # ── Step 2: group into Mahadasha blocks (contiguous by maha_id) ──────────

    # Each block = one Mahadasha occurrence (handles repeating cycles)
    blocks: list[dict] = []  # {mid, lord, start, end, antars: [...]}
    current_mid = None
    current_block: dict | None = None

    for s, lords, start_str, end_str, dur in parsed:
        depth = len(lords)

        if depth == 2:
            mid, aid = lords[0], lords[1]

            if mid != current_mid:
                # New Mahadasha block starts
                if current_block is not None:
                    blocks.append(current_block)
                current_mid = mid
                current_block = {
                    "mid":   mid,
                    "lord":  _lord_name(mid),
                    "start": start_str,
                    "end":   end_str,      # will be updated
                    "_start": s,
                    "_end":   _d.fromisoformat(end_str),
                    "antars": [],
                }

            # Extend Mahadasha end to cover this antardasha
            antar_end = _d.fromisoformat(end_str)
            if current_block and antar_end > current_block["_end"]:
                current_block["_end"] = antar_end
                current_block["end"]  = end_str

            if current_block is not None:
                current_block["antars"].append({
                    "lord":  _lord_name(aid),
                    "start": start_str,
                    "end":   end_str,
                    "durationYears": round(dur, 4),
                    "_start": s,
                })

        elif depth == 1:
            mid = lords[0]
            if mid != current_mid:
                if current_block is not None:
                    blocks.append(current_block)
                current_mid = mid
                current_block = {
                    "mid":   mid,
                    "lord":  _lord_name(mid),
                    "start": start_str,
                    "end":   end_str,
                    "_start": s,
                    "_end":   _d.fromisoformat(end_str),
                    "antars": [],
                }

    if current_block is not None:
        blocks.append(current_block)

    # Compute each Mahadasha's durationYears from its actual start/end
    for b in blocks:
        b["durationYears"] = round((b["_end"] - b["_start"]).days / 365.25, 4)

    # ── Step 3: build running ladder ─────────────────────────────────────────

    running_maha_block: dict | None = None
    running_antar: dict | None = None

    for b in blocks:
        if b["_start"] <= today <= b["_end"]:
            running_maha_block = b
            for a in b["antars"]:
                ae = _d.fromisoformat(a["end"])
                as_ = a["_start"]
                if as_ <= today <= ae:
                    running_antar = a
                    break
            break

    ladder: list[dict] = []
    if running_maha_block:
        ladder.append({
            "levelLabel": "Mahadasha",
            "lord":  running_maha_block["lord"],
            "start": running_maha_block["start"],
            "end":   running_maha_block["end"],
        })
    if running_antar:
        ladder.append({
            "levelLabel": "Antardasha",
            "lord":  running_antar["lord"],
            "start": running_antar["start"],
            "end":   running_antar["end"],
        })

    # ── Step 4: build tree ────────────────────────────────────────────────────

    tree = [
        {
            "level": 1,
            "lord":  b["lord"],
            "start": b["start"],
            "end":   b["end"],
            "durationYears": b["durationYears"],
            "subPeriods": [
                {
                    "level": 2,
                    "lord":  a["lord"],
                    "start": a["start"],
                    "end":   a["end"],
                    "durationYears": a["durationYears"],
                    "subPeriods": [],
                }
                for a in sorted(b["antars"], key=lambda x: x["_start"])
            ],
        }
        for b in blocks
    ]

    return tree, ladder


# ── Yogini ────────────────────────────────────────────────────────────────────

def _enrich_yogini(tree: list, ladder: list) -> tuple[list, list]:
    """Add yoginiName to every node so the UI can display deity names."""
    def add(node: dict) -> dict:
        # Resolve planet id from lord name to add yoginiName
        pid = next((i for i, n in enumerate(PLANET_NAMES) if n == node.get("lord")), None)
        if pid is not None:
            yn = _yogini_name(pid)
            if yn:
                node["yoginiName"] = yn
        node["subPeriods"] = [add(c) for c in node.get("subPeriods", [])]
        return node

    enriched_tree = [add(n) for n in tree]

    enriched_ladder = []
    for row in ladder:
        pid = next((i for i, n in enumerate(PLANET_NAMES) if n == row.get("lord")), None)
        new_row = dict(row)
        if pid is not None:
            yn = _yogini_name(pid)
            if yn:
                new_row["yoginiName"] = yn
        enriched_ladder.append(new_row)

    return enriched_tree, enriched_ladder


def yogini_deep_payload(jd: float, place, dt) -> dict:
    """
    Full /dasha-deep-yogini response with proportionally correct antardasha periods.

    PyJHora's get_dhasa_bhukthi at ANTARA level divides each Mahadasha into 8 equal
    sub-periods, which is wrong. The classical rule (Goel / BPHS) is proportional:
        antardasha_duration = maha_years × antar_years × (year_duration / 36)
    We get Maha-only rows from PyJHora (those dates ARE correct) and compute
    antardasha periods ourselves using the correct formula.
    """
    from jhora.horoscope.dhasa.graha import yogini
    from jhora.panchanga.drik import Date as DrikDate, dhasa_year_duration
    from jhora import const

    year_dur = dhasa_year_duration(jd=jd, place=place)  # sidereal days per year

    flat_maha = yogini.get_dhasa_bhukthi(
        DrikDate(dt.year, dt.month, dt.day),
        (dt.hour, dt.minute, dt.second),
        place,
        dhasa_level_index=const.MAHA_DHASA_DEPTH.MAHA_DHASA_ONLY,
        round_duration=False,
    )

    today = _d.today()
    blocks: list[dict] = []

    for row in flat_maha:
        lords = row[0]
        st    = row[1]
        dur   = float(row[2])
        maha_pid   = lords[0] if isinstance(lords, (list, tuple)) else lords
        maha_years = YOGINI_YEARS.get(maha_pid, 1)
        maha_start = _to_date(st)
        maha_end   = maha_start + _td(days=int(round(dur * year_dur)))

        # Antardasha order: starts with the Maha lord itself, then continues in Yogini cycle order
        antar_pids = yogini._antardhasa(maha_pid, antardhasa_option=1)

        antars: list[dict] = []
        cursor = maha_start
        for antar_pid in antar_pids:
            antar_years = YOGINI_YEARS.get(antar_pid, 1)
            # Classical proportional formula: duration = maha_years × antar_years / 36 years
            antar_days  = int(round(maha_years * antar_years * year_dur / YOGINI_TOTAL_YEARS))
            antar_end   = cursor + _td(days=antar_days)
            antars.append({
                "level":         2,
                "lord":          _lord_name(antar_pid),
                "yoginiName":    YOGINI_BY_PLANET.get(antar_pid),
                "start":         cursor.isoformat(),
                "end":           antar_end.isoformat(),
                "_start":        cursor,
                "_end":          antar_end,
                "durationYears": round(antar_days / year_dur, 4),
                "subPeriods":    [],
            })
            cursor = antar_end

        blocks.append({
            "lord":          _lord_name(maha_pid),
            "yoginiName":    YOGINI_BY_PLANET.get(maha_pid),
            "start":         maha_start.isoformat(),
            "end":           maha_end.isoformat(),
            "_start":        maha_start,
            "_end":          maha_end,
            "durationYears": round(dur, 4),
            "antars":        antars,
        })

    # Build running ladder
    ladder: list[dict] = []
    for b in blocks:
        if b["_start"] <= today <= b["_end"]:
            ladder.append({
                "levelLabel": "Mahadasha",
                "lord":       b["lord"],
                "yoginiName": b["yoginiName"],
                "start":      b["start"],
                "end":        b["end"],
            })
            for a in b["antars"]:
                if a["_start"] <= today <= a["_end"]:
                    ladder.append({
                        "levelLabel": "Antardasha",
                        "lord":       a["lord"],
                        "yoginiName": a["yoginiName"],
                        "start":      a["start"],
                        "end":        a["end"],
                    })
                    break
            break

    # Build tree (strip internal _start/_end helpers)
    tree = [
        {
            "level":         1,
            "lord":          b["lord"],
            "yoginiName":    b["yoginiName"],
            "start":         b["start"],
            "end":           b["end"],
            "durationYears": b["durationYears"],
            "subPeriods": [
                {k: v for k, v in a.items() if not k.startswith("_")}
                for a in b["antars"]
            ],
        }
        for b in blocks
    ]

    return {
        "system":            "yogini",
        "applicable":        True,
        "applicabilityNote": None,
        "currentLadder":     ladder,
        "dashaTree":         tree,
    }


# ── Ashtottari ────────────────────────────────────────────────────────────────

def _ashtottari_paksha_daynight_check(jd: float, place) -> tuple[bool, str]:
    """
    BPHS Condition 2 for Ashtottari applicability:
      - Daytime birth during Krishna Paksha (waning Moon), OR
      - Nighttime birth during Shukla Paksha (waxing Moon)

    Returns (passes: bool, note: str)
    """
    from jhora.panchanga import drik

    # Moon elongation from Sun → Paksha
    solar_long = drik.solar_longitude(jd)
    lunar_long = drik.lunar_longitude(jd)
    elongation = (lunar_long - solar_long) % 360
    # 0–180° = Shukla Paksha (waxing); 180–360° = Krishna Paksha (waning)
    shukla = elongation < 180.0
    paksha_name = "Shukla Paksha (waxing)" if shukla else "Krishna Paksha (waning)"

    # Day / night birth from sunrise and sunset at birth location
    try:
        sr = drik.sunrise(jd, place)   # [local_hour_float, str, jd]
        ss = drik.sunset(jd, place)    # [local_hour_float, str, jd]
        _, _, y, m, d, fh = _d.today().year, _d.today().month, *((jd,)*4)  # unused
        # Extract the birth hour from jd
        from jhora import utils as _u
        _, _, _, birth_fh = _u.jd_to_gregorian(jd)
        day_birth = sr[0] <= birth_fh <= ss[0]
    except Exception:
        # If sunrise/sunset calculation fails, skip this sub-condition
        return True, ""

    birth_type = "daytime" if day_birth else "nighttime"

    # Passes when: (day AND Krishna) OR (night AND Shukla)
    passes = (day_birth and not shukla) or (not day_birth and shukla)
    note = (
        f"{birth_type} birth during {paksha_name}"
        + (" — satisfies BPHS Paksha condition." if passes
           else " — does not satisfy BPHS Paksha condition (requires daytime×Krishna OR nighttime×Shukla).")
    )
    return passes, note


def ashtottari_deep_payload(jd: float, place) -> dict:
    """
    Full /dasha-deep-ashtottari response.

    BPHS (Parasara Hora Shastra) specifies two conditions for Ashtottari applicability
    — BOTH must be met:
      1. Rahu in kendra (1,4,7,10) or trikona (5,9) from Lagna Lord, NOT in Lagna itself
      2. Daytime birth during Krishna Paksha, OR nighttime birth during Shukla Paksha

    If either condition fails → not applicable. Tree is NOT computed (no data to show).
    """
    from jhora import const
    from jhora.horoscope.chart import charts
    from jhora.horoscope.dhasa.graha import ashtottari

    pp = charts.rasi_chart(jd, place)

    # Condition 1: Rahu kendra/trikona from Lagna Lord (jhora implements this correctly)
    cond1 = bool(ashtottari.applicability_check(pp))
    cond1_note = (
        "Rahu is in kendra or trikona from Lagna Lord (not in Lagna) ✓"
        if cond1 else
        "Rahu is NOT in kendra or trikona from Lagna Lord (or is in Lagna itself) ✗"
    )

    # Condition 2: Paksha × day/night birth
    cond2, cond2_note = _ashtottari_paksha_daynight_check(jd, place)

    applicable = cond1 and cond2

    if not applicable:
        failed = []
        if not cond1:
            failed.append(cond1_note)
        if not cond2:
            failed.append(cond2_note)
        return {
            "system":            "ashtottari",
            "applicable":        False,
            "applicabilityNote": (
                "Ashtottari Dasha does not apply to this chart per BPHS (Parasara). "
                "Both conditions must be satisfied: (1) Rahu in kendra/trikona from "
                "Lagna Lord, not in Lagna; and (2) daytime birth during Krishna Paksha "
                "or nighttime birth during Shukla Paksha. "
                "Failed: " + " | ".join(failed)
            ),
            "currentLadder": [],
            "dashaTree":     [],
        }

    flat = ashtottari.get_ashtottari_dhasa_bhukthi(
        jd, place,
        dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
    )
    tree, ladder = _build_tree_and_ladder(flat)

    return {
        "system":            "ashtottari",
        "applicable":        True,
        "applicabilityNote": None,
        "currentLadder":     ladder,
        "dashaTree":         tree,
    }
