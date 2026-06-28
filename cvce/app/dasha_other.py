"""
Yogini and Ashtottari dasha tree builders.
Both libraries return flat rows: [(lords_tuple, (Y,M,D,H), duration_years), ...]
"""
from __future__ import annotations

from datetime import date as _d, timedelta as _td

PLANET_NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
LEVEL_LABELS  = {1: "Mahadasha", 2: "Antardasha", 3: "Pratyantardasha"}

# Yogini dasha: each planet corresponds to a specific Yogini deity
# Source: Parasara Hora Shastra — Yogini Dasha Adhyaya
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
    """Full /dasha-deep-yogini response with Yogini deity names."""
    from jhora.horoscope.dhasa.graha import yogini
    from jhora.panchanga.drik import Date as DrikDate

    flat = yogini.get_dhasa_bhukthi(
        DrikDate(dt.year, dt.month, dt.day),
        (dt.hour, dt.minute, dt.second),
        place,
    )
    tree, ladder = _build_tree_and_ladder(flat)
    tree, ladder = _enrich_yogini(tree, ladder)
    return {
        "system":        "yogini",
        "currentLadder": ladder,
        "dashaTree":     tree,
    }


# ── Ashtottari ────────────────────────────────────────────────────────────────

def ashtottari_deep_payload(jd: float, place) -> dict:
    """
    Full /dasha-deep-ashtottari response.
    Always computes the tree; flags applicability as informational note only.
    Parasara prescribes Ashtottari when Rahu occupies kendra/trikona from the lagna lord
    (excluding lagna itself). When not met, we show the tree with a note rather than blocking.
    """
    from jhora import const
    from jhora.horoscope.chart import charts
    from jhora.horoscope.dhasa.graha import ashtottari

    pp = charts.rasi_chart(jd, place)
    applicable = bool(ashtottari.applicability_check(pp))

    flat = ashtottari.get_ashtottari_dhasa_bhukthi(
        jd, place,
        dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
    )
    tree, ladder = _build_tree_and_ladder(flat)

    return {
        "system":        "ashtottari",
        "applicable":    applicable,
        "applicabilityNote": (
            None if applicable else
            "Parasara prescribes Ashtottari when Rahu is in kendra or trikona from "
            "the lagna lord (excluding lagna). Shown here for reference."
        ),
        "currentLadder": ladder,
        "dashaTree":     tree,
    }
