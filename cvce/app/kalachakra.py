"""Kalachakra Dasha (86y cycle, deha/jeeva, nak+rasi based) — engine module.

PyJHora via ephem only. KE integration for BPHS/structured notes on deha jeeva,
pada wheel, source_notes + ke_version.

Calculation rules (Deha/Jeeva Rasi, the three Gatis/leaps) follow BPHS Vol.2
Ch.46 v.60-100 verbatim (knowledge-graph/raw/Brihat_Parasara_Hora_Sastra_Vol_2.md),
not the simplified/secondary descriptions this module briefly carried during
development. See the plan doc for the verse citations and empirical validation
against PyJHora's actual (kc_index, pada) cycle tables.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.ephem import NAKSHATRAS, RASHIS, jd_place, parse_dt, positions
from knowledge_engine.integration import get_knowledge_engine, get_structured_book

_GRAPH_KALA_IDS = [
    "brihat_parasara_hora_sastra_vol_2_kalachakra_dasa",
    "phaladeepika_vb_digest_kalachakra_dasha",
    "deva_keralam_1_kalachakra_dasa",
]

_KALA_BOOKS = [
    "brihat_parasara_hora_sastra_vol_2",  # may be split
]

_kala_cache: dict = {"ke_version": None, "source_notes": [], "structured": {}}


def _on_kalachakra_refresh(new_version: str) -> None:
    global _kala_cache
    _kala_cache = {"ke_version": new_version, "source_notes": [], "structured": {}}
    try:
        ke = get_knowledge_engine()
        for nid in _GRAPH_KALA_IDS:
            node = None
            try:
                node = ke.get_safe_node(nid) if hasattr(ke, "get_safe_node") else ke.store.get_node(nid)
            except Exception:
                pass
            if node:
                _kala_cache["source_notes"].append(
                    {"id": nid, "label": node.get("label", nid), "description": (node.get("description") or "")[:360]}
                )
        for bid in _KALA_BOOKS:
            try:
                b = get_structured_book(bid)
                if b:
                    _kala_cache["structured"][bid] = {"chapters": len(b.get("chapters", []))}
            except Exception:
                pass
    except Exception:
        pass


def _register_kala() -> None:
    try:
        ke = get_knowledge_engine()
        ke.register_engine("kalachakra_dasha", on_refresh=_on_kalachakra_refresh)
    except Exception:
        pass


_register_kala()


def _sign_name(idx: int | None) -> str | None:
    if idx is None or not (0 <= idx < 12):
        return None
    return RASHIS[idx]


def _fmt(d: tuple) -> str:
    return f"{int(d[0]):04d}-{int(d[1]):02d}-{int(d[2]):02d}"


# ---------------------------------------------------------------------------
# Leap (Gati) classification — BPHS Vol.2 Ch.46 v.94-100
# ---------------------------------------------------------------------------

_LEAP_LABELS = {
    "monkey_leap": "Monkey Leap (Markati Gati)",
    "frog_leap": "Frog Leap (Mandooki Gati)",
    "lions_leap": "Lion Leap (Simhavalokana Gati)",
}


def _signed_circular_step(a: int, b: int) -> int:
    """Shortest signed step 0-11 sign index a->b, range -6..+6 (handles wraparound)."""
    d = (b - a) % 12
    if d > 6:
        d -= 12
    return d


def _classify_transition(step: int, is_savya: bool) -> dict | None:
    """Direction-relative classification per BPHS Vol.2 Ch.46 v.94-100.

    "Normal" step is +1 (forward) for Savya groups, -1 (backward) for Apasavya
    groups. Any step against that expected flow is itself a named Gati:
      step == normal                         -> None (expected progression)
      step == -normal (magnitude 1)          -> Monkey Leap (Markati Gati)
      step == -2*normal (magnitude 2)        -> Frog Leap (Mandooki Gati)
      abs(step) == 4 (5th/9th trine, either direction) -> Lion Leap (Simhavalokana Gati)
    """
    if step == 0:
        return None  # self-period (e.g. Antardasha of the Mahadasha's own sign) — no motion, no Gati
    normal = 1 if is_savya else -1
    if step == normal:
        return None
    if abs(step) == 4:
        leap_type = "lions_leap"
    elif step == -2 * normal:
        leap_type = "frog_leap"
    elif step == -normal:
        leap_type = "monkey_leap"
    else:
        leap_type = "monkey_leap"  # unclassified magnitude — default to the catch-all Gati
    return {
        "isLeap": True,
        "type": leap_type,
        "label": _LEAP_LABELS[leap_type],
        "direction": "forward" if step > 0 else "backward",
        "step": step,
    }


# ---------------------------------------------------------------------------
# Birth nakshatra/pada -> Savya/Apasavya group routing
# ---------------------------------------------------------------------------


def birth_nakshatra_info(jd: float, place) -> dict:
    """Moon's sidereal longitude, nakshatra/pada, and Savya/Apasavya routing (Steps A-C)."""
    from jhora.horoscope.dhasa.raasi import kalachakra as kala_mod
    from jhora.panchanga.drik import nakshatra_pada

    pos = positions(jd, place)
    moon = next((p for p in pos if p.get("planet") == "Moon"), None)
    moon_lon = moon["longitude"] if moon else 0.0

    nak, pada, rem_deg = nakshatra_pada(moon_lon)
    nak0, pada0 = nak - 1, pada - 1
    kc_index = kala_mod._kc_group_for_nak(nak0)
    group_name = ["Savya Group 1", "Savya Group 2", "Apasavya Group 1", "Apasavya Group 2"][kc_index]
    is_savya = kc_index < 2
    return {
        "moonLongitude": round(moon_lon, 4),
        "nakshatra": NAKSHATRAS[nak0],
        "nakshatraIndex": nak0,
        "pada": pada,
        "padaIndex": pada0,
        "remainderDeg": round(rem_deg, 4),
        "kcIndex": kc_index,
        "kcGroupName": group_name,
        "direction": "Savya (clockwise)" if is_savya else "Apasavya (counter-clockwise)",
        "isSavya": is_savya,
    }


def kalachakra_cycle(kc_index: int, pada_index: int) -> dict:
    """9-sign cycle with leap metadata + Deha/Jeeva Rasi (BPHS Vol.2 Ch.46 v.60-95)."""
    from jhora.horoscope.dhasa.raasi import kalachakra as kala_mod

    is_savya = kc_index < 2
    cyc = kala_mod._cycle_for(kc_index, pada_index)  # 9 sign indices 0-11
    years = kala_mod._sign_year_weights(cyc)

    nodes = []
    for i, sign in enumerate(cyc):
        leap = None
        if i > 0:
            step = _signed_circular_step(cyc[i - 1], sign)
            leap = _classify_transition(step, is_savya)
        nodes.append(
            {
                "index": i,
                "sign": RASHIS[sign],
                "signIndex": sign,
                "years": years[i],
                "leapFromPrevious": leap,
            }
        )

    # Savya: Deha = 1st sign, Jeeva = 9th (last) sign. Apasavya: reversed.
    deha_idx, jeeva_idx = (cyc[0], cyc[-1]) if is_savya else (cyc[-1], cyc[0])

    return {
        "kcIndex": kc_index,
        "padaIndex": pada_index,
        "signs": nodes,
        "totalYears": round(sum(years), 4),
        "dehaRasi": RASHIS[deha_idx],
        "jeevaRasi": RASHIS[jeeva_idx],
        "hasActiveLeap": any(n["leapFromPrevious"] for n in nodes),
    }


# ---------------------------------------------------------------------------
# Running ladder (current MD/AD/PD) — fixes the row[2]-as-duration bug
# ---------------------------------------------------------------------------

_LEVEL_LABELS = {1: "Mahadasha", 2: "Antardasha", 3: "Pratyantardasha"}


def _query_jd_now() -> float:
    from app.dasha_vimshottari import query_jd_now

    return query_jd_now()


def running_ladder(
    jd: float, place, query_jd: float | None = None, depth: int = 3, dhasa_method: int = 1
) -> list[dict]:
    """Running Kalachakra periods from Maha down to requested depth.

    get_running_dhasa_for_given_date(current_jd, jd_at_dob, place, ...) returns
    rows shaped [lords_tuple, start_date_tuple, end_date_tuple] — BOTH tuples.
    The prior version of this function mis-cast row[2] (an end-date tuple) as a
    duration float, which raised a silently-swallowed TypeError and made
    "current" always None. Fixed here; also fixes the argument order (current
    jd first, birth jd second — matching the Vimshottari precedent in
    dasha_vimshottari.py) and the birth-jd-used-for-both-args bug.
    """
    from jhora import const
    from jhora.horoscope.dhasa.raasi import kalachakra as kala_mod

    q_jd = query_jd if query_jd is not None else _query_jd_now()
    depth = max(1, min(3, depth))
    depth_enum = {
        1: const.MAHA_DHASA_DEPTH.MAHA_DHASA_ONLY,
        2: const.MAHA_DHASA_DEPTH.ANTARA,
        3: const.MAHA_DHASA_DEPTH.PRATYANTARA,
    }[depth]

    run = kala_mod.get_running_dhasa_for_given_date(
        q_jd, jd, place, dhasa_level_index=depth_enum, dhasa_method=dhasa_method
    )
    rows = []
    for row in run or []:
        lords, start_t, end_t = row[0], row[1], row[2]
        level = len(lords) if isinstance(lords, tuple) else 1
        sign_idx = lords[-1] if isinstance(lords, tuple) else lords
        signs = [RASHIS[s] for s in (lords if isinstance(lords, tuple) else (lords,))]
        rows.append(
            {
                "level": level,
                "levelLabel": _LEVEL_LABELS.get(level, f"Level {level}"),
                "signs": signs,
                "sign": RASHIS[sign_idx],
                "signIndex": sign_idx,
                "start": _fmt(start_t),
                "end": _fmt(end_t),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 3-level MD -> AD -> PD tree
# ---------------------------------------------------------------------------


def _period_end(start_t, years: float):
    from jhora import const, utils
    from jhora.panchanga import drik

    y, m, d = int(start_t[0]), int(start_t[1]), int(start_t[2])
    fh = float(start_t[3]) if len(start_t) > 3 else 0.0
    start_jd = utils.julian_day_number(drik.Date(y, m, d), (fh, 0, 0))
    end_jd = start_jd + float(years) * const.sidereal_year
    return utils.jd_to_gregorian(end_jd)


def _subtree_from_flat(
    flat_periods: list,
    prefix: tuple,
    child_level: int,
    max_level: int,
    is_savya: bool,
    parent_sign: int | None,
    gatis_verified: bool = True,
) -> list[dict]:
    """Build nested nodes, chronologically ordered, with leaps computed
    sibling-to-sibling within each parent group (not parent-to-child): the
    Gati concept describes how consecutive periods AT THE SAME LEVEL move
    through the cycle (MD[i-1]->MD[i], or AD[i-1]->AD[i] within one MD), not a
    parent/child relationship. The first sibling under a parent compares
    against the parent's own sign (PyJHora's AD/PD cycles are rotated to start
    at the parent's sign — a Deha/self-period), matching the classical
    "antardasha of the Mahadasha lord itself" convention.

    gatis_verified=False marks leaps whose Frog/Lion/Monkey classification is
    not backed by a classical citation for the dhasa_method in use — BPHS Vol.2
    Ch.46 v.94-100 describes these three Gatis specifically for the PVR/book
    nakshatra-pada model (dhasa_method=1); the geometric "non-adjacent
    transition" detection is method-agnostic, but the *names* are not verified
    for other methods (e.g. Raghavacharya's navamsa-based method=3).
    """
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
    prev_sign = parent_sign
    for key in sorted(groups.keys(), key=lambda k: groups[k][0]):
        start_t, dur, lords = groups[key]
        end_t = _period_end(start_t, float(dur))
        # lords is the row's full (leaf-depth) tuple — index by this node's own
        # depth (child_level), not -1/-2, or a level-1 node would pick up the
        # leaf-level sign instead of its own.
        sign = lords[child_level - 1]
        leap = None
        if prev_sign is not None:
            step = _signed_circular_step(prev_sign, sign)
            leap = _classify_transition(step, is_savya)
            if leap is not None:
                leap["verified"] = gatis_verified
        prev_sign = sign
        nodes.append(
            {
                "level": child_level,
                "sign": RASHIS[sign],
                "signIndex": sign,
                "start": _fmt(start_t),
                "end": _fmt(end_t),
                "durationYears": round(float(dur), 4),
                "leapFromPrevious": leap,
                "subPeriods": _subtree_from_flat(
                    flat_periods,
                    lords[:child_level],
                    child_level + 1,
                    max_level,
                    is_savya,
                    parent_sign=sign,
                    gatis_verified=gatis_verified,
                ),
            }
        )
    return nodes


def kalachakra_tree(
    jd: float, place, dob, tob, is_savya: bool, max_level: int = 3, dhasa_method: int = 1
) -> list[dict]:
    """3-level MD -> AD -> PD nested tree, leap-flagged.

    dhasa_method=1 (PVR/book, default) matches BPHS Vol.2 Ch.46's Gati
    definitions exactly. dhasa_method=3 (Raghavacharya, navamsa-based) is
    computed identically but its Frog/Lion/Monkey labels are marked
    unverified (see _subtree_from_flat) since that classical mapping isn't
    established for this method.
    """
    from jhora import const
    from jhora.horoscope.dhasa.raasi import kalachakra as kala_mod

    max_level = max(1, min(3, max_level))
    depth_enum = {
        1: const.MAHA_DHASA_DEPTH.MAHA_DHASA_ONLY,
        2: const.MAHA_DHASA_DEPTH.ANTARA,
        3: const.MAHA_DHASA_DEPTH.PRATYANTARA,
    }[max_level]

    rows = kala_mod.get_dhasa_bhukthi(dob, tob, place, dhasa_level_index=depth_enum, dhasa_method=dhasa_method)
    return _subtree_from_flat(
        rows or [], (), 1, max_level, is_savya, parent_sign=None, gatis_verified=(dhasa_method == 1)
    )


def leap_timeline(tree: list[dict]) -> list[dict]:
    """Flatten dashaTree into a chronological list of every leap, tagged past/current/future."""
    today = date.today().isoformat()
    out: list[dict] = []

    def walk(nodes):
        for n in nodes:
            if n.get("leapFromPrevious"):
                start, end = n["start"], n.get("end") or n["start"]
                when = "past" if end < today else ("future" if start > today else "current")
                out.append(
                    {
                        "level": n["level"],
                        "sign": n["sign"],
                        "start": start,
                        "end": end,
                        "leap": n["leapFromPrevious"],
                        "when": when,
                    }
                )
            walk(n.get("subPeriods") or [])

    walk(tree)
    out.sort(key=lambda e: e["start"])
    return out


# ---------------------------------------------------------------------------
# Balance of first dasha (Step D) — actual PyJHora algorithm + PRD's simplified formula
# ---------------------------------------------------------------------------


def _balance_of_first_dasha(jd: float, place) -> dict:
    """Both figures per user Decision 1: PyJHora's real balance (primary) and
    the PRD's simplified Y_R1 x (arcmin/200) formula (secondary, labeled)."""
    actual = None
    try:
        # The running ladder's first (birth-time) Mahadasha row already carries
        # PyJHora's real start/end for that period — its span IS the actual
        # balance-of-first-dasha figure the engine computes internally.
        ladder = running_ladder(jd, place, query_jd=jd, depth=1)
        if ladder:
            start_d = date.fromisoformat(ladder[0]["start"])
            end_d = date.fromisoformat(ladder[0]["end"])
            actual = round((end_d - start_d).days / 365.25, 2)
    except Exception:
        actual = None

    simplified = None
    try:
        birth = birth_nakshatra_info(jd, place)
        cycle = kalachakra_cycle(birth["kcIndex"], birth["padaIndex"])
        y_r1 = cycle["signs"][0]["years"]
        # nakshatra_pada()'s "remainder" is degrees traversed *since the start of
        # the nakshatra* (0-13.3333), not degrees remaining in the pada. Convert:
        # pada span = 13.3333/4 = 3.3333deg (200'); find degrees into the current
        # pada, then how much of that pada's 200' remains.
        pada_span_deg = 13.0 + 1.0 / 3.0
        pada_span_deg /= 4.0  # 3.3333...
        deg_into_pada = birth["remainderDeg"] - birth["padaIndex"] * pada_span_deg
        arcmin_remaining = (pada_span_deg - deg_into_pada) * 60.0
        simplified = round(y_r1 * (arcmin_remaining / 200.0), 2)
    except Exception:
        simplified = None

    return {"actual": actual, "simplifiedEstimate": simplified}


# ---------------------------------------------------------------------------
# Composed payloads
# ---------------------------------------------------------------------------


def _active_leap_from_tree(tree: list[dict], today: str) -> dict | None:
    """Find the currently-running leaf node in dashaTree and return its own
    leapFromPrevious. More robust than matching against the static wheel cycle
    (kalachakra_cycle) — a person's real Mahadasha sequence stitches together
    two different pada cycles (birth pada's tail + next pada's head, per
    PyJHora's _get_dhasa_progression), so the currently-running sign may not
    even appear in the birth pada's own 9-sign template for later Mahadashas."""
    for node in tree:
        if node["start"] <= today <= (node.get("end") or node["start"]):
            children = node.get("subPeriods") or []
            deeper = _active_leap_from_tree(children, today)
            if deeper is not None:
                return deeper
            return node.get("leapFromPrevious")
    return None


def current_state_payload(
    jd: float, place, tree: list[dict], query_jd: float | None = None, dhasa_method: int = 1
) -> dict:
    q_jd = query_jd if query_jd is not None else _query_jd_now()
    birth_info = birth_nakshatra_info(jd, place)
    cycle = kalachakra_cycle(birth_info["kcIndex"], birth_info["padaIndex"])
    ladder = running_ladder(jd, place, query_jd=q_jd, depth=3, dhasa_method=dhasa_method)
    active_leap = _active_leap_from_tree(tree, date.today().isoformat())

    return {
        "birthNakshatra": birth_info,
        "cycle": cycle,
        "currentLadder": ladder,
        "activeLeap": active_leap,
    }


def _method_block(jd, place, dob, tob, is_savya: bool, dhasa_method: int, query_jd: float) -> dict:
    tree = kalachakra_tree(jd, place, dob, tob, is_savya=is_savya, max_level=3, dhasa_method=dhasa_method)
    state = current_state_payload(jd, place, tree, query_jd=query_jd, dhasa_method=dhasa_method)
    timeline = leap_timeline(tree)
    return {
        "currentLadder": state["currentLadder"],
        "activeLeap": state["activeLeap"],
        "dashaTree": tree,
        "leapTimeline": timeline,
    }


def kalachakra_deep_payload(jd: float, place, dob, tob, query_jd: float | None = None) -> dict:
    """Canonical /kalachakra-deep response.

    Computes both dhasa_method=1 (PVR/book — matches BPHS Vol.2 Ch.46's Gati
    definitions, the primary result) and dhasa_method=3 (Raghavacharya,
    navamsa-based) as `alternateMethod`, so the two can be compared. The
    primary method's Deha/Jeeva/cycle wheel (nakshatra-pada derived) is shared
    by both, since that concept is defined independently of which method
    computes the Antardasha/Pratyantardasha sequence.
    """
    try:
        q_jd = query_jd if query_jd is not None else _query_jd_now()
        birth_info = birth_nakshatra_info(jd, place)
        is_savya = birth_info["isSavya"]
        cycle = kalachakra_cycle(birth_info["kcIndex"], birth_info["padaIndex"])

        primary = _method_block(jd, place, dob, tob, is_savya, dhasa_method=1, query_jd=q_jd)
        balance = _balance_of_first_dasha(jd, place)

        alternate = None
        try:
            alt = _method_block(jd, place, dob, tob, is_savya, dhasa_method=3, query_jd=q_jd)
            alternate = {
                "method": "raghavacharya",
                "methodLabel": "Raghavacharya (navamsa-based, JHora)",
                "gatisVerified": False,
                **alt,
            }
        except Exception:
            alternate = None

        return {
            "status": "active",
            "system": "kalachakra",
            "method": "Kalachakra Dasha — 86y nakshatra-pada wheel (BPHS Vol.2 Ch.46/49) — PVR/book method",
            "birthNakshatra": birth_info,
            "cycle": cycle,
            "balanceOfFirstDasha": balance,
            "currentLadder": primary["currentLadder"],
            "activeLeap": primary["activeLeap"],
            "dashaTree": primary["dashaTree"],
            "leapTimeline": primary["leapTimeline"],
            "alternateMethod": alternate,
            "ke_version": _kala_cache.get("ke_version"),
            "source_notes": _kala_cache.get("source_notes", []),
            "graph_citations": _kala_cache.get("source_notes", []),
        }
    except Exception as e:
        return {
            "status": "error",
            "system": "kalachakra",
            "error": str(e)[:200],
            "method": "Kalachakra Dasha — 86y nakshatra-pada wheel (BPHS Vol.2 Ch.46/49)",
            "dashaTree": [],
            "ke_version": _kala_cache.get("ke_version"),
        }


# ---------------------------------------------------------------------------
# Legacy flat entrypoint — kept for /all-dashas backward-compat
# ---------------------------------------------------------------------------


def compute_kalachakra_dasha(birth_datetime: str, birth_lat: float, birth_lon: float, birth_tz: float) -> dict:
    """Kalachakra via PyJHora (dhasa_method=1) + current + periods + deha/jeeva notes.

    Kept for /all-dashas's SignDashaBlock contract (flat shape, first 8 periods
    from birth). Prefer kalachakra_deep_payload for the full rich view.
    """
    from jhora import const
    from jhora.horoscope.chart import charts
    from jhora.horoscope.dhasa.raasi import kalachakra as kala_mod
    from jhora.panchanga.drik import Date as DrikDate

    dt = parse_dt(birth_datetime)
    jd, place = jd_place(dt, birth_lat, birth_lon, birth_tz)
    dob = DrikDate(dt.year, dt.month, dt.day)
    tob = (dt.hour, dt.minute, dt.second)
    today = date.today()

    current = None
    try:
        ladder = running_ladder(jd, place, depth=2)
        if len(ladder) >= 2:
            maha, antara = ladder[0], ladder[1]
            current = {
                "maha": maha["sign"],
                "antara": antara["sign"],
                "mahaStart": maha["start"],
                "mahaEnd": maha["end"],
                "antaraStart": antara["start"],
                "antaraEnd": antara["end"],
            }
    except Exception:
        pass

    periods: list[dict] = []
    calc_error = None
    try:
        rows = kala_mod.get_dhasa_bhukthi(
            dob, tob, place, dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA, dhasa_method=1
        )
        for row in (rows or [])[:8]:
            try:
                lords = row[0]
                st = row[1]
                dur = float(row[2]) if len(row) > 2 else 1.0
                m = _sign_name(lords[0] if isinstance(lords, (list, tuple)) else None)
                a = _sign_name(lords[1] if isinstance(lords, (list, tuple)) and len(lords) > 1 else None)
                s = _fmt(st) if isinstance(st, (list, tuple)) else None
                if not s:
                    continue
                e = (date.fromisoformat(s) + timedelta(days=int(dur * 365.25))).isoformat()
                periods.append(
                    {"maha": m, "antara": a, "start": s, "end": e, "years": round(dur, 2), "isCurrent": s <= today.isoformat() <= e}
                )
            except Exception:
                continue
    except Exception as e:
        calc_error = str(e)[:200]

    lagna_sign = None
    try:
        pp = charts.rasi_chart(jd, place)
        for item in pp:
            if isinstance(item[0], str):
                lagna_sign = RASHIS[int(item[1][0]) % 12]
                break
    except Exception:
        pass

    deha_jeeva = None
    try:
        birth_info = birth_nakshatra_info(jd, place)
        cycle = kalachakra_cycle(birth_info["kcIndex"], birth_info["padaIndex"])
        deha_jeeva = {
            "note": "Deha/Jeeva from Moon nakshatra-pada wheel (BPHS Vol.2 Ch.46 v.60-95)",
            "dehaRasi": cycle["dehaRasi"],
            "jeevaRasi": cycle["jeevaRasi"],
        }
    except Exception:
        pass

    if not periods and calc_error:
        return {
            "status": "error",
            "system": "kalachakra",
            "error": calc_error,
            "method": "Kalachakra Dasha 86y cycle (BPHS Vol.2 / Phaladeepika / Deva Keralam)",
            "periods": [],
            "ke_version": _kala_cache.get("ke_version"),
        }

    payload = {
        "status": "active",
        "system": "kalachakra",
        "method": "Kalachakra Dasha 86y cycle (BPHS Vol.2 / Phaladeepika / Deva Keralam / Moon nakshatra-pada wheel) — deha/jeeva applicable",
        "maha": current["maha"] if current else None,
        "antara": current["antara"] if current else None,
        "mahaStart": current.get("mahaStart") if current else None,
        "mahaEnd": current.get("mahaEnd") if current else None,
        "periods": periods,
        "lagnaSign": lagna_sign,
        "dehaJeeva": deha_jeeva or {"note": "Deha/Jeeva determined by Moon nakshatra-pada at birth (BPHS Vol.2 Ch.46)"},
        "ke_version": _kala_cache.get("ke_version"),
        "source_notes": _kala_cache.get("source_notes", []),
        "structured_books": _kala_cache.get("structured", {}),
        "graph_citations": _kala_cache.get("source_notes", []),
    }
    if current:
        payload["ladder"] = [
            {"levelLabel": "Mahadasha (sign)", "lord": current.get("maha"), "start": current.get("mahaStart"), "end": current.get("mahaEnd")},
            {"levelLabel": "Antardasha (sign)", "lord": current.get("antara"), "start": current.get("antaraStart"), "end": current.get("antaraEnd")},
        ]
    return payload
