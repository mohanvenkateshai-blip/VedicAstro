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


def _build_children(
    path: tuple,
    start_t,
    end_t,
    jd: float,
    place,
    level: int,
    max_level: int,
) -> list[dict]:
    if level >= max_level:
        return []
    children = vimsottari.vimsottari_immediate_children(
        path, start_t, parent_end=end_t, jd=jd, place=place,
    )
    nodes = []
    for child in children:
        child_path, c_start, c_end = child[0], child[1], child[2]
        child_lord = child_path[-1]
        nodes.append({
            "level": level + 1,
            "lord": lord_name(child_lord),
            "start": _fmt_date(c_start),
            "end": _fmt_date(c_end),
            "durationYears": round(_duration_years(c_start, c_end), 4),
            "subPeriods": _build_children(
                child_path, c_start, c_end, jd, place, level + 1, max_level,
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
    Nine Mahadashas; each includes all Antardashas.
    If deep_antar_path is set (e.g. (4, 3) Jupiter–Mercury), that antar gets
  levels 3–5 nested; others stop at Antar.
    """
    maha_map = vimsottari.vimsottari_mahadasa(jd, place)
    items = list(maha_map.items())
    tree = []

    for idx, (m_lord, m_start_jd) in enumerate(items):
        if idx < len(items) - 1:
            m_end_jd = items[idx + 1][1]
        else:
            m_end_jd = m_start_jd + float(const.vimsottari_dict[m_lord]) * const.sidereal_year
        m_start_t = utils.jd_to_gregorian(m_start_jd)
        m_end_t = utils.jd_to_gregorian(m_end_jd)

        antars = vimsottari.vimsottari_immediate_children(
            (m_lord,), m_start_t, parent_end=m_end_t, jd=jd, place=place,
        )
        antar_nodes = []
        for child in antars:
            child_path, a_start, a_end = child[0], child[1], child[2]
            a_lord = child_path[-1]
            deep = (
                deep_antar_path is not None
                and len(deep_antar_path) >= 2
                and deep_antar_path[0] == m_lord
                and deep_antar_path[1] == a_lord
            )
            antar_nodes.append({
                "level": 2,
                "lord": lord_name(a_lord),
                "start": _fmt_date(a_start),
                "end": _fmt_date(a_end),
                "durationYears": round(_duration_years(a_start, a_end), 4),
                "subPeriods": (
                    _build_children(child_path, a_start, a_end, jd, place, 2, max_level)
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
