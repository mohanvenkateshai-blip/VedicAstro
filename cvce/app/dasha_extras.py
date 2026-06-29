"""Chara, Kalachakra, and Kaksha helpers for /dashas and report facts."""

from __future__ import annotations

from datetime import date, timedelta

from app.ephem import PLANET_NAMES, RASHIS

# Kaksha lords in order (BPHS / Ashtakavarga Handbook §6).
KAKSHA_LORDS = [
    "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Lagna",
]
_KAKSHA_CONTRIB_IDX = {
    "Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3,
    "Jupiter": 4, "Venus": 5, "Saturn": 6, "Lagna": 7,
}
_KAKSHA_SPAN = 30.0 / 8.0  # 3°45′ per kaksha

_CHARA_KARAKA_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
_CHARA_KARAKA_ROLES = [
    "Atmakaraka", "Amatyakaraka", "Bhratrikaraka", "Matrikaraka",
    "Putrakaraka", "Gnatikaraka", "Darakaraka",
]

_GRAPH_CHARA_IDS = [
    "jaimini_goel_method_chara_dasha",
    "jaimini_goel_rule_chara_dasha_years",
    "jaimini_goel_rule_chara_dasha_subperiods",
    "jaimini_goel_concept_seven_karakas",
    "jaimini_sutras_atmakaraka",
]
_GRAPH_KALA_IDS = ["brihat_parasara_hora_sastra_vol_2_kalachakra_dasa"]
_GRAPH_KAKSHA_IDS = [
    "phaladeepika_concept_bindu",
    "phaladeepika_concept_sarvashtakavarga",
    "gyan_ashtakavarga_system_comprehensive_handbo_corpus",
]

_citation_cache: dict[str, list[dict]] = {}


def clear_dasha_extras_cache() -> None:
    """Clear cached graph citations (called by KnowledgeEngine dasha refresh)."""
    _citation_cache.clear()


def _sign_name(idx: int | None) -> str | None:
    if idx is None or not (0 <= idx < 12):
        return None
    return RASHIS[idx]


def _parse_sign_lords(lords) -> tuple[int | None, int | None]:
    """Normalize PyJHora rashi dasha lord tuples: (maha_sign,) or (maha, antara, ...)."""
    if isinstance(lords, int):
        return lords, None
    if isinstance(lords, (list, tuple)) and lords:
        maha = lords[0] if isinstance(lords[0], int) else None
        antara = lords[1] if len(lords) > 1 and isinstance(lords[1], int) else None
        return maha, antara
    return None, None


def _fmt_row_dates(row) -> tuple[str | None, str | None]:
    """Extract ISO start/end from a PyJHora dasha row [lords, start, duration_years]."""
    from jhora import utils as _u

    antar_start_str = antar_end_str = None
    try:
        if len(row) >= 2:
            st = row[1]
            if isinstance(st, (list, tuple)) and len(st) >= 3:
                antar_start_str = f"{int(st[0]):04d}-{int(st[1]):02d}-{int(st[2]):02d}"
            elif isinstance(st, (int, float)):
                st_g = _u.jd_to_gregorian(float(st))
                antar_start_str = f"{int(st_g[0]):04d}-{int(st_g[1]):02d}-{int(st_g[2]):02d}"
        if antar_start_str and len(row) >= 3:
            dur = float(row[2])
            antar_end_str = (
                date.fromisoformat(antar_start_str) + timedelta(days=int(dur * 365.25))
            ).isoformat()
    except Exception:
        pass
    return antar_start_str, antar_end_str


def _days_remaining(end_iso: str | None, today: date) -> int | None:
    if not end_iso:
        return None
    try:
        return max(0, (date.fromisoformat(end_iso[:10]) - today).days)
    except Exception:
        return None


def _house_from_lagna(sign_name: str | None, lagna_sign: str | None) -> int | None:
    if not sign_name or not lagna_sign:
        return None
    try:
        si = RASHIS.index(sign_name)
        li = RASHIS.index(lagna_sign)
        return ((si - li + 12) % 12) + 1
    except ValueError:
        return None


def _knowledge_version() -> str | None:
    try:
        from knowledge_engine.integration import get_knowledge_engine
        ke = get_knowledge_engine()
        return ke.current_version.version if ke.current_version else None
    except Exception:
        return None


def _chara_karakas(jd, place) -> list[dict]:
    """Seven Jaimini chara karakas ranked by degree within sign (Sun–Saturn)."""
    from app.ephem import positions

    ranked = sorted(
        (
            p for p in positions(jd, place)
            if p.get("planet") in _CHARA_KARAKA_PLANETS
        ),
        key=lambda p: float(p.get("degInSign", 0)),
        reverse=True,
    )
    out: list[dict] = []
    for i, p in enumerate(ranked[:7]):
        out.append({
            "role": _CHARA_KARAKA_ROLES[i],
            "planet": p["planet"],
            "sign": p.get("sign"),
            "degInSign": round(float(p.get("degInSign", 0)), 2),
        })
    return out


def _running_sign_dasha(module, jd, place, *, method_kw: dict | None = None) -> dict | None:
    """Current maha/antar for a PyJHora rashi dasha module (separate date ranges)."""
    from jhora import const

    method_kw = method_kw or {}
    antar_run = module.get_running_dhasa_for_given_date(
        jd,
        jd,
        place,
        dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
        **method_kw,
    )
    if not antar_run:
        return None

    antar_row = antar_run[-1] if isinstance(antar_run, list) else antar_run
    _, antara = _parse_sign_lords(antar_row[0])
    antar_start, antar_end = _fmt_row_dates(antar_row)

    maha = maha_start = maha_end = None
    try:
        maha_run = module.get_running_dhasa_for_given_date(
            jd,
            jd,
            place,
            dhasa_level_index=const.MAHA_DHASA_DEPTH.MAHA,
            **method_kw,
        )
        if maha_run:
            maha_row = maha_run[-1] if isinstance(maha_run, list) else maha_run
            maha, _ = _parse_sign_lords(maha_row[0])
            maha_start, maha_end = _fmt_row_dates(maha_row)
    except Exception:
        pass

    return {
        "maha": _sign_name(maha),
        "antara": _sign_name(antara),
        "mahaStart": maha_start,
        "mahaEnd": maha_end,
        "antaraStart": antar_start,
        "antaraEnd": antar_end,
    }


def _upcoming_sign_periods(rows, today: date, limit: int = 6) -> list[dict]:
    """Next few maha/antar rows from a PyJHora dasha table."""
    out: list[dict] = []
    for row in rows or []:
        try:
            lords = row[0]
            maha, antara = _parse_sign_lords(lords)
            start, _ = _fmt_row_dates(row)
            if not start:
                continue
            start_d = date.fromisoformat(start)
            dur = float(row[2]) if len(row) >= 3 else 1.0
            end_d = start_d + timedelta(days=int(dur * 365.25))
            if end_d < today:
                continue
            out.append({
                "maha": _sign_name(maha),
                "antara": _sign_name(antara),
                "start": start,
                "end": end_d.isoformat(),
                "years": round(dur, 2),
                "isCurrent": start_d <= today <= end_d,
            })
            if len(out) >= limit:
                break
        except Exception:
            continue
    return out


def _graph_dasha_citations(node_ids: list[str]) -> list[dict]:
    """Fetch classical notes for dasha system nodes from the knowledge graph."""
    cache_key = "|".join(node_ids)
    if cache_key in _citation_cache:
        return _citation_cache[cache_key]

    citations: list[dict] = []
    try:
        from knowledge_engine.integration import get_knowledge_engine

        ke = get_knowledge_engine()
        for nid in node_ids:
            node = ke.get_safe_node(nid)
            if not node:
                continue
            desc = (node.get("description") or node.get("label") or "").strip()
            if not desc:
                continue
            citations.append({
                "id": nid,
                "label": node.get("label", nid),
                "description": desc[:420],
                "source_file": node.get("source_file"),
                "source_location": node.get("source_location"),
            })
    except Exception:
        try:
            from knowledge_engine.integration import get_safe_graph

            graph = get_safe_graph()
            for nid in node_ids:
                node = graph.node(nid)
                if not node:
                    continue
                desc = (node.get("description") or node.get("label") or "").strip()
                if not desc:
                    continue
                citations.append({
                    "id": nid,
                    "label": node.get("label", nid),
                    "description": desc[:420],
                    "source_file": node.get("source_file"),
                    "source_location": node.get("source_location"),
                })
        except Exception:
            pass

    _citation_cache[cache_key] = citations
    return citations


def _enrich_sign_dasha(payload: dict, *, lagna_sign: str | None, today: date) -> dict:
    """Add Jaimini context, house positions, and knowledge version."""
    if lagna_sign:
        payload["lagnaSign"] = lagna_sign
        if payload.get("maha"):
            payload["mahaHouse"] = _house_from_lagna(payload["maha"], lagna_sign)
        if payload.get("antara"):
            payload["antaraHouse"] = _house_from_lagna(payload["antara"], lagna_sign)
    payload["daysRemainingMaha"] = _days_remaining(payload.get("mahaEnd"), today)
    payload["daysRemainingAntara"] = _days_remaining(payload.get("antaraEnd"), today)
    payload["knowledgeVersion"] = _knowledge_version()
    return payload


def chara_dasha_payload(jd, place, dob, tob, query_jd=None) -> dict:
    """Jaimini Chara dasha — Method 1 (K.N. Rao) via PyJHora."""
    from jhora import const
    from jhora.horoscope.dhasa.raasi import chara
    from jhora.horoscope.chart import charts

    today = date.today()
    q_jd = query_jd or jd
    current = _running_sign_dasha(chara, q_jd, place, method_kw={"chara_method": 1})
    try:
        rows = chara.get_dhasa_antardhasa(
            dob, tob, place,
            chara_method=1,
            dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
        )
        periods = _upcoming_sign_periods(rows, today)
    except Exception:
        periods = []

    lagna_sign = None
    try:
        pp = charts.rasi_chart(jd, place)
        for item in pp:
            if isinstance(item[0], str):
                lagna_sign = RASHIS[int(item[1][0]) % 12]
                break
    except Exception:
        pass

    payload = {
        "status": "active",
        "method": "Chara Method 1 (K.N. Rao / V.P. Goel)",
        "applicable": True,
        "periods": periods,
        "karakas": _chara_karakas(jd, place),
        "graph_citations": _graph_dasha_citations(_GRAPH_CHARA_IDS),
    }
    if current:
        payload.update(current)
        payload["ladder"] = [
            {"levelLabel": "Mahadasha (sign)", "lord": current.get("maha"),
             "start": current.get("mahaStart"), "end": current.get("mahaEnd")},
            {"levelLabel": "Antardasha (sign)", "lord": current.get("antara"),
             "start": current.get("antaraStart"), "end": current.get("antaraEnd")},
        ]
    return _enrich_sign_dasha(payload, lagna_sign=lagna_sign, today=today)


def kalachakra_dasha_payload(jd, place, dob, tob, query_jd=None) -> dict:
    """Kalachakra dasha via PyJHora (PVR / Moon nakshatra pada wheel)."""
    from jhora import const
    from jhora.horoscope.dhasa.raasi import kalachakra
    from jhora.horoscope.chart import charts

    today = date.today()
    q_jd = query_jd or jd
    current = _running_sign_dasha(kalachakra, q_jd, place, method_kw={"dhasa_method": 1})
    try:
        rows = kalachakra.get_dhasa_bhukthi(
            dob, tob, place,
            dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
            dhasa_method=1,
        )
        periods = _upcoming_sign_periods(rows, today)
    except Exception:
        periods = []

    lagna_sign = None
    try:
        pp = charts.rasi_chart(jd, place)
        for item in pp:
            if isinstance(item[0], str):
                lagna_sign = RASHIS[int(item[1][0]) % 12]
                break
    except Exception:
        pass

    payload = {
        "status": "active",
        "method": "Kalachakra (BPHS / PVR method)",
        "applicable": True,
        "periods": periods,
        "graph_citations": _graph_dasha_citations(_GRAPH_KALA_IDS),
    }
    if current:
        payload.update(current)
        payload["ladder"] = [
            {"levelLabel": "Mahadasha (sign)", "lord": current.get("maha"),
             "start": current.get("mahaStart"), "end": current.get("mahaEnd")},
            {"levelLabel": "Antardasha (sign)", "lord": current.get("antara"),
             "start": current.get("antaraStart"), "end": current.get("antaraEnd")},
        ]
    return _enrich_sign_dasha(payload, lagna_sign=lagna_sign, today=today)


def _kaksha_index(deg_in_sign: float) -> int:
    return min(7, max(0, int(deg_in_sign / _KAKSHA_SPAN)))


def _kaksha_lord_has_bindu(prastara, sign_idx: int, kaksha_lord: str) -> bool:
    """True if the kaksha lord contributed a bindu in this sign (prastara check)."""
    op = _KAKSHA_CONTRIB_IDX.get(kaksha_lord)
    if op is None:
        return False
    try:
        for p in range(len(prastara)):
            if prastara[p][op][sign_idx]:
                return True
    except Exception:
        pass
    return False


def _sav_band(bindus: int) -> dict:
    from vedic_engine.prediction.ashtakavarga import SAV_BANDS

    for band_name, (lo, hi, verdict, label) in SAV_BANDS.items():
        if lo <= bindus <= hi:
            return {"band": band_name, "verdict": verdict, "label": label}
    return {"band": "depleted", "verdict": "ashubh", "label": "Depleted SAV"}


def _planet_kaksha_row(
    planet: str,
    lon: float,
    sign_idx: int,
    prastara,
    samudhaya,
    *,
    context: str = "transit",
) -> dict:
    deg_in = lon % 30.0
    k_idx = _kaksha_index(deg_in)
    k_lord = KAKSHA_LORDS[k_idx]
    bindu = _kaksha_lord_has_bindu(prastara, sign_idx, k_lord)
    sav = int(samudhaya[sign_idx])
    return {
        "planet": planet,
        "sign": RASHIS[sign_idx],
        "degreeInSign": round(deg_in, 2),
        "kakshaIndex": k_idx + 1,
        "kakshaLord": k_lord,
        "binduActive": bindu,
        "savBindus": sav,
        "savBand": _sav_band(sav)["band"],
        "verdict": "shubh" if bindu else "ashubh",
        "context": context,
    }


def kaksha_payload(jd, place, query_jd=None) -> dict:
    """Kaksha refinement — natal prastara vs query-time (default today) positions."""
    from jhora.horoscope.chart import charts, ashtakavarga
    from jhora import utils
    from app.ephem import positions

    transit_jd = query_jd if query_jd is not None else utils.gregorian_to_jd(date.today())

    pp = charts.rasi_chart(jd, place)
    h2p = utils.get_house_planet_list_from_planet_positions(pp)
    _binna, samudhaya, prastara = ashtakavarga.get_ashtaka_varga(h2p)

    transit_positions = positions(transit_jd, place)
    pos_by_name = {p["planet"]: p for p in transit_positions}
    transits: list[dict] = []
    for planet in PLANET_NAMES[:7]:
        pos = pos_by_name.get(planet)
        if not pos:
            continue
        lon = float(pos.get("longitude", 0))
        sign_idx = int(pos.get("signIndex", int(lon // 30) % 12))
        transits.append(_planet_kaksha_row(
            planet, lon, sign_idx, prastara, samudhaya, context="transit",
        ))

    natal_positions = positions(jd, place)
    natal_by_name = {p["planet"]: p for p in natal_positions}
    natal: list[dict] = []
    for planet in PLANET_NAMES[:7]:
        pos = natal_by_name.get(planet)
        if not pos:
            continue
        lon = float(pos.get("longitude", 0))
        sign_idx = int(pos.get("signIndex", int(lon // 30) % 12))
        natal.append(_planet_kaksha_row(
            planet, lon, sign_idx, prastara, samudhaya, context="natal",
        ))

    # Lagna sign kaksha map (reference for natal lagna)
    lagna_lon = None
    for item in pp:
        if isinstance(item[0], str):
            lagna_lon = float(item[1][1]) + (int(item[1][0]) * 30)
            break
    lagna_kakshas = []
    lagna_sign = None
    if lagna_lon is not None:
        sign_idx = int(lagna_lon // 30) % 12
        lagna_sign = RASHIS[sign_idx]
        for i, lord in enumerate(KAKSHA_LORDS):
            lo = i * _KAKSHA_SPAN
            hi = (i + 1) * _KAKSHA_SPAN
            lagna_kakshas.append({
                "index": i + 1,
                "lord": lord,
                "rangeDeg": f"{lo:.2f}–{hi:.2f}°",
                "binduActive": _kaksha_lord_has_bindu(prastara, sign_idx, lord),
            })

    favorable = [t["planet"] for t in transits if t["binduActive"]]
    challenging = [t["planet"] for t in transits if not t["binduActive"]]
    moon_row = next((t for t in transits if t["planet"] == "Moon"), None)

    sav_by_sign = {}
    for i in range(12):
        sav = int(samudhaya[i])
        band = _sav_band(sav)
        sav_by_sign[RASHIS[i]] = {
            "bindus": sav,
            "band": band["band"],
            "verdict": band["verdict"],
            "label": band["label"],
        }

    overall_verdict = "shubh"
    if len(favorable) < len(transits) // 2:
        overall_verdict = "mixed"
    if len(favorable) <= 1:
        overall_verdict = "ashubh"

    return {
        "status": "active",
        "refinement": "Kaksha lords vs natal prastara bindus (BPHS Ch.67)",
        "summary": f"{len(favorable)}/{len(transits)} transiting planets in bindu-active kakshas",
        "overallVerdict": overall_verdict,
        "favorablePlanets": favorable,
        "challengingPlanets": challenging,
        "transits": transits,
        "natal": natal,
        "moonKaksha": moon_row,
        "lagnaSign": lagna_sign,
        "lagnaKakshas": lagna_kakshas,
        "savBySign": sav_by_sign,
        "graph_citations": _graph_dasha_citations(_GRAPH_KAKSHA_IDS),
        "knowledgeVersion": _knowledge_version(),
    }
