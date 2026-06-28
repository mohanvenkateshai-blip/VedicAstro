"""
Yogini and Ashtottari dasha tree builders.
Both libraries return flat rows: [(lords_tuple, (Y,M,D,H), duration_years), ...]
"""
from __future__ import annotations

from datetime import date as _d, timedelta as _td

PLANET_NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
LEVEL_LABELS  = {1: "Mahadasha", 2: "Antardasha", 3: "Pratyantardasha"}


def _lord_name(pid: int) -> str:
    return PLANET_NAMES[pid] if 0 <= pid < len(PLANET_NAMES) else str(pid)


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
    Returns: (tree, current_ladder)
    """
    today = _d.today()
    by_depth: dict[int, dict] = {}
    mahas:    dict[int, dict] = {}          # maha_id -> node data
    antars:   dict[tuple, dict] = {}        # (maha_id, antar_id) -> node data

    for row in (flat_rows or []):
        try:
            lords = row[0]
            st    = row[1]
            dur   = float(row[2])
            depth = len(lords) if isinstance(lords, (list, tuple)) else 0
            if depth == 0:
                continue
            if not (isinstance(st, (list, tuple)) and len(st) >= 3):
                continue

            s = _to_date(st)
            e = _end_date(st, dur)

            # Running period at this depth (first match wins)
            if depth not in by_depth and s <= today <= e:
                by_depth[depth] = {
                    "levelLabel": LEVEL_LABELS.get(depth, f"Level {depth}"),
                    "lord": _lord_name(lords[depth - 1]),
                    "start": _fmt(st),
                    "end":   e.isoformat(),
                }

            if depth == 1:
                mid = lords[0]
                if mid not in mahas:
                    mahas[mid] = {
                        "lord": _lord_name(mid),
                        "start": _fmt(st),
                        "end":   e.isoformat(),
                        "durationYears": round(dur, 4),
                        "_sort": s,
                    }

            elif depth == 2:
                key = (lords[0], lords[1])
                if key not in antars:
                    antars[key] = {
                        "lord": _lord_name(lords[1]),
                        "start": _fmt(st),
                        "end":   e.isoformat(),
                        "durationYears": round(dur, 4),
                        "_sort": s,
                        "_maha": lords[0],
                    }

        except Exception:
            continue

    # Sort mahas by start date
    sorted_mahas = sorted(mahas.items(), key=lambda x: x[1]["_sort"])

    # Build tree
    tree: list[dict] = []
    for mid, maha in sorted_mahas:
        antar_nodes = sorted(
            [v for (m, _), v in antars.items() if m == mid],
            key=lambda x: x["_sort"],
        )
        tree.append({
            "level": 1,
            "lord":  maha["lord"],
            "start": maha["start"],
            "end":   maha["end"],
            "durationYears": maha["durationYears"],
            "subPeriods": [
                {
                    "level": 2,
                    "lord":  a["lord"],
                    "start": a["start"],
                    "end":   a["end"],
                    "durationYears": a["durationYears"],
                    "subPeriods": [],
                }
                for a in antar_nodes
            ],
        })

    ladder = [by_depth[d] for d in sorted(by_depth.keys())]
    return tree, ladder


# ── Yogini ────────────────────────────────────────────────────────────────────

def yogini_deep_payload(jd: float, place, dt) -> dict:
    """Full /dasha-deep-yogini response."""
    from jhora.horoscope.dhasa.graha import yogini
    from jhora.panchanga.drik import Date as DrikDate

    flat = yogini.get_dhasa_bhukthi(
        DrikDate(dt.year, dt.month, dt.day),
        (dt.hour, dt.minute, dt.second),
        place,
    )
    tree, ladder = _build_tree_and_ladder(flat)
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
