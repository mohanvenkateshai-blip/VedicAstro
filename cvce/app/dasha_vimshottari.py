"""
Vimshottari dasha helpers — correct PyJHora wiring.

PyJHora get_vimsottari_dhasa_bhukthi returns:
  (balance_years_months_days, flat_period_list)
NOT the running dasha. Use get_running_dhasa_for_given_date for "now".
"""

from __future__ import annotations

from datetime import datetime, timezone

from jhora import const, utils
from jhora.horoscope.dhasa.graha import vimsottari

PLANET_NAMES = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter",
    "Venus", "Saturn", "Rahu", "Ketu",
]

LEVEL_LABELS = {
    1: "Mahadasha",
    2: "Antardasha",
    3: "Pratyantardasha",
    4: "Sookshma",
    5: "Prana",
}


def lord_name(pid: int) -> str:
    return PLANET_NAMES[pid] if 0 <= pid < len(PLANET_NAMES) else str(pid)


def lords_names(lords: tuple) -> list[str]:
    return [lord_name(p) for p in lords]


def _fmt_date(t) -> str:
    y, m, d = int(t[0]), int(t[1]), int(t[2])
    return f"{y:04d}-{m:02d}-{d:02d}"


def _duration_years(start_t, end_t) -> float:
    from jhora.panchanga import drik

    def to_jd(t):
        y, m, d, fh = t
        return utils.julian_day_number(drik.Date(y, m, d), (fh, 0, 0))

    return (to_jd(end_t) - to_jd(start_t)) / const.sidereal_year


def query_jd_now() -> float:
    import swisseph as swe

    now = datetime.now(timezone.utc)
    return swe.julday(
        now.year, now.month, now.day,
        now.hour + now.minute / 60 + now.second / 3600,
    )


def birth_balance(jd: float, place) -> dict:
    """Balance of first mahadasha at birth (e.g. Venus 4Y 7M 7D)."""
    lord, _ = vimsottari.vimsottari_dasha_start_date(jd, place)
    bal, _ = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place)
    years, months, days = int(bal[0]), int(bal[1]), int(bal[2])
    return {
        "lord": lord_name(lord),
        "years": years,
        "months": months,
        "days": days,
        "label": f"{lord_name(lord)} {years}Y {months}M {days}D",
    }


def running_ladder(
    jd: float,
    place,
    query_jd: float | None = None,
    depth: int = 5,
) -> list[dict]:
    """Running Vimshottari periods from Maha down to requested depth."""
    if query_jd is None:
        query_jd = query_jd_now()
    depth = max(1, min(5, depth))
    run = vimsottari.get_running_dhasa_for_given_date(
        query_jd, jd, place, dhasa_level_index=depth,
    )
    rows = []
    for i, row in enumerate(run or []):
        lords, start_t, end_t = row[0], row[1], row[2]
        level = len(lords) if isinstance(lords, tuple) else 1
        rows.append({
            "level": level,
            "levelLabel": LEVEL_LABELS.get(level, f"Level {level}"),
            "lords": lords_names(lords if isinstance(lords, tuple) else (lords,)),
            "lord": lord_name(lords[-1] if isinstance(lords, tuple) else lords),
            "start": _fmt_date(start_t),
            "end": _fmt_date(end_t),
            "durationYears": round(_duration_years(start_t, end_t), 4),
        })
    return rows


def antardasha_table(jd: float, place) -> list[dict]:
    """All Maha–Antar rows (81), like a professional report table."""
    _, periods = vimsottari.get_vimsottari_dhasa_bhukthi(
        jd, place, dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
    )
    rows = []
    for p in periods:
        lords, start, years = p[0], p[1], p[2]
        rows.append({
            "maha": lord_name(lords[0]),
            "antara": lord_name(lords[1]),
            "start": _fmt_date(start),
            "durationYears": round(float(years), 4),
        })
    return rows


def _period_end(start_t, years: float):
    """Gregorian end tuple from start tuple + duration in years."""
    from jhora import const, utils
    from jhora.panchanga import drik

    y, m, d = int(start_t[0]), int(start_t[1]), int(start_t[2])
    fh = float(start_t[3]) if len(start_t) > 3 else 0.0
    start_jd = utils.julian_day_number(drik.Date(y, m, d), (fh, 0, 0))
    end_jd = start_jd + float(years) * const.sidereal_year
    return utils.jd_to_gregorian(end_jd)


_DEPTH_FOR_LEVEL = {
    3: const.MAHA_DHASA_DEPTH.PRATYANTARA,
    4: const.MAHA_DHASA_DEPTH.SOOKSHMA,
    5: const.MAHA_DHASA_DEPTH.PRANA,
}


def _subtree_from_flat(
    flat_periods: list,
    prefix: tuple,
    child_level: int,
    max_level: int,
) -> list[dict]:
    """Build nested nodes from one bulk get_vimsottari_dhasa_bhukthi() slice."""
    if child_level > max_level:
        return []

    groups: dict[tuple, tuple] = {}
    for p in flat_periods:
        lords, start_t, dur = p[0], p[1], p[2]
        if len(lords) < child_level:
            continue
        if lords[: len(prefix)] != prefix:
            continue
        key = lords[:child_level]
        if key not in groups or start_t < groups[key][0]:
            groups[key] = (start_t, dur, lords)

    nodes = []
    for key in sorted(groups.keys(), key=lambda k: groups[k][0]):
        start_t, dur, lords = groups[key]
        end_t = _period_end(start_t, float(dur))
        nodes.append({
            "level": child_level,
            "lord": lord_name(lords[-1]),
            "start": _fmt_date(start_t),
            "end": _fmt_date(end_t),
            "durationYears": round(float(dur), 4),
            "subPeriods": _subtree_from_flat(
                flat_periods, lords, child_level + 1, max_level,
            ),
        })
    return nodes


def mahadasha_tree(
    jd: float,
    place,
    max_level: int = 5,
    deep_antar_path: tuple | None = None,
) -> list[dict]:
    """
    Nine Mahadashas with Antardashas; levels 3–5 nested only under the running antar.

    Uses one bulk PyJHora call for antars (81 rows, ~0.2s) instead of 9×
    vimsottari_immediate_children (~20s). Deep levels use one more bulk fetch
  filtered to the running maha–antar path.
    """
    max_level = max(1, min(5, max_level))
    maha_map = vimsottari.vimsottari_mahadasa(jd, place)
    items = list(maha_map.items())

    _, antar_periods = vimsottari.get_vimsottari_dhasa_bhukthi(
        jd, place, dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
    )
    antars_by_maha: dict[int, list] = {}
    for p in antar_periods:
        antars_by_maha.setdefault(p[0][0], []).append(p)

    deep_flat: list = []
    if max_level > 2 and deep_antar_path and len(deep_antar_path) >= 2:
        _, deep_flat = vimsottari.get_vimsottari_dhasa_bhukthi(
            jd, place, dhasa_level_index=_DEPTH_FOR_LEVEL[max_level],
        )
        m_id, a_id = deep_antar_path[0], deep_antar_path[1]
        deep_flat = [
            p for p in deep_flat
            if len(p[0]) >= 2 and p[0][0] == m_id and p[0][1] == a_id
        ]

    tree = []
    for idx, (m_lord, m_start_jd) in enumerate(items):
        if idx < len(items) - 1:
            m_end_jd = items[idx + 1][1]
        else:
            m_end_jd = m_start_jd + float(const.vimsottari_dict[m_lord]) * const.sidereal_year
        m_start_t = utils.jd_to_gregorian(m_start_jd)
        m_end_t = utils.jd_to_gregorian(m_end_jd)

        antar_nodes = []
        for p in antars_by_maha.get(m_lord, []):
            lords, start_t, years = p[0], p[1], p[2]
            a_lord = lords[1]
            end_t = _period_end(start_t, float(years))
            deep = (
                deep_antar_path is not None
                and len(deep_antar_path) >= 2
                and deep_antar_path[0] == m_lord
                and deep_antar_path[1] == a_lord
                and max_level > 2
            )
            antar_nodes.append({
                "level": 2,
                "lord": lord_name(a_lord),
                "start": _fmt_date(start_t),
                "end": _fmt_date(end_t),
                "durationYears": round(float(years), 4),
                "subPeriods": (
                    _subtree_from_flat(deep_flat, lords[:2], 3, max_level)
                    if deep
                    else []
                ),
            })

        tree.append({
            "level": 1,
            "lord": lord_name(m_lord),
            "start": _fmt_date(m_start_t),
            "end": _fmt_date(m_end_t),
            "durationYears": round(_duration_years(m_start_t, m_end_t), 4),
            "subPeriods": antar_nodes,
        })

    return tree


def dasha_deep_payload(jd: float, place, max_level: int = 5) -> dict:
    """Full /dasha-deep response."""
    ladder = running_ladder(jd, place, depth=max_level)
    current_lords = ladder[-1]["lords"] if ladder else []
    deep_path = None
    if len(ladder) >= 2:
        run = vimsottari.get_running_dhasa_for_given_date(
            query_jd_now(), jd, place, dhasa_level_index=2,
        )
        if run and len(run) >= 2:
            deep_path = run[1][0]

    return {
        "balanceAtBirth": birth_balance(jd, place),
        "current": current_lords,
        "currentLadder": ladder,
        "antardashaTable": antardasha_table(jd, place),
        "dashaTree": mahadasha_tree(
            jd, place, max_level=max_level, deep_antar_path=deep_path,
        ),
    }
