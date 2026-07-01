"""Chara Dasha (Jaimini rashi dasha) — engine module with KE integration.

Uses PyJHora via ephem only. Loads Jaimini structured + graph rules for
period calculation notes, karaka context, source_notes.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.ephem import RASHIS, jd_place, parse_dt
from knowledge_engine.integration import get_knowledge_engine, get_structured_book

# Graph node ids for Chara (from Jaimini Goel / Rath texts in newbooks-v1)
_GRAPH_CHARA_IDS = [
    "jaimini_goel_method_chara_dasha",
    "jaimini_goel_rule_chara_dasha_years",
    "jaimini_goel_rule_chara_dasha_subperiods",
    "jaimini_goel_concept_seven_karakas",
    "jaimini_sutras_atmakaraka",
]

# Structured Jaimini books for on_refresh
_CHARA_BOOK_IDS = [
    "rath_s_jaimini_maharishis_upadesa_sutra",
    "jaimini_astrology_calculation_of_mandook_dasha_with_a_case_study_compress",
]

_chara_cache: dict = {
    "ke_version": None,
    "source_notes": [],
    "structured": {},
    "year_rules": None,  # enriched from KE if present
}


def _on_chara_refresh(new_version: str) -> None:
    """Pull latest Jaimini structured + graph citations for Chara params."""
    global _chara_cache
    _chara_cache = {"ke_version": new_version, "source_notes": [], "structured": {}, "year_rules": None}
    try:
        ke = get_knowledge_engine()
        for nid in _GRAPH_CHARA_IDS:
            node = None
            try:
                node = ke.get_safe_node(nid) if hasattr(ke, "get_safe_node") else ke.store.get_node(nid)
            except Exception:
                pass
            if node:
                _chara_cache["source_notes"].append(
                    {
                        "id": nid,
                        "label": node.get("label", nid),
                        "description": (node.get("description") or "")[:380],
                        "source_file": node.get("source_file"),
                    }
                )
        for bid in _CHARA_BOOK_IDS:
            try:
                b = get_structured_book(bid)
                if b:
                    _chara_cache["structured"][bid] = {
                        "chapters": len(b.get("chapters", [])),
                        "has_full_text": bool(b.get("full_text")),
                    }
            except Exception:
                pass
        # Attempt to derive year rule notes (classical 7-10y etc from Goel node)
        for note in _chara_cache["source_notes"]:
            if "year" in (note.get("description") or "").lower():
                _chara_cache["year_rules"] = note["description"][:200]
                break
    except Exception:
        pass


def _register_chara() -> None:
    try:
        ke = get_knowledge_engine()
        ke.register_engine("chara_dasha", on_refresh=_on_chara_refresh)
    except Exception:
        pass


_register_chara()


def _sign_name(idx: int | None) -> str | None:
    if idx is None or not (0 <= idx < 12):
        return None
    return RASHIS[idx]


def _fmt(d: tuple) -> str:
    if not d or len(d) < 3:
        return None
    return f"{int(d[0]):04d}-{int(d[1]):02d}-{int(d[2]):02d}"


def _parse_lords(lords):
    if isinstance(lords, int):
        return lords, None
    if isinstance(lords, (list, tuple)) and lords:
        m = lords[0] if isinstance(lords[0], int) else None
        a = lords[1] if len(lords) > 1 and isinstance(lords[1], int) else None
        return m, a
    return None, None


def compute_chara_dasha(birth_datetime: str, birth_lat: float, birth_lon: float, birth_tz: float) -> dict:
    """Compute Chara dasha (Method 1 K.N. Rao) + current + periods + KE notes."""
    from jhora import const
    from jhora.horoscope.chart import charts
    from jhora.horoscope.dhasa.raasi import chara as chara_mod
    from jhora.panchanga.drik import Date as DrikDate

    dt = parse_dt(birth_datetime)
    jd, place = jd_place(dt, birth_lat, birth_lon, birth_tz)
    dob = DrikDate(dt.year, dt.month, dt.day)
    tob = (dt.hour, dt.minute, dt.second)
    today = date.today()

    # Current running — replicate proven logic from dasha_extras for reliable maha/antara on Mohan
    current = None
    try:
        antar_run = chara_mod.get_running_dhasa_for_given_date(
            jd, jd, place, dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA, chara_method=1
        )
        if antar_run:
            antar_row = antar_run[-1] if isinstance(antar_run, list) else antar_run
            lords, st, durv = antar_row[0], antar_row[1], antar_row[2] if len(antar_row) > 2 else 1.0
            maha_idx, ant_idx = _parse_lords(lords)
            dur = float(durv)
            start = _fmt(st) if isinstance(st, (list, tuple)) else None
            end = (date.fromisoformat(start) + timedelta(days=int(dur * 365.25))).isoformat() if start else None
            current = {"maha": _sign_name(maha_idx), "antara": _sign_name(ant_idx), "mahaStart": start, "mahaEnd": end}
    except Exception:
        pass

    # Periods (up to 8 upcoming antar) — row shape: ((m,a), (y,m,d,h), dur_years_float)
    periods: list[dict] = []
    try:
        rows = chara_mod.get_dhasa_antardhasa(
            dob, tob, place, chara_method=1, dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA
        )
        for row in (rows or [])[:8]:
            try:
                lords, st, durv = row[0], row[1], row[2] if len(row) > 2 else 1.0
                m, a = _parse_lords(lords)
                s = _fmt(st) if isinstance(st, (list, tuple)) else None
                if not s:
                    continue
                dur = float(durv)
                e = (date.fromisoformat(s) + timedelta(days=int(dur * 365.25))).isoformat()
                periods.append(
                    {
                        "maha": m,
                        "antara": a,
                        "start": s,
                        "end": e,
                        "years": round(dur, 2),
                        "isCurrent": (s <= today.isoformat() <= e) if s else False,
                    }
                )
            except Exception:
                continue
    except Exception:
        pass

    # Lagna for house context
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
        "system": "chara",
        "method": "Chara Dasha Method 1 (K.N. Rao / V.P. Goel) — Jaimini rashi dasha",
        "maha": current["maha"] if current else None,
        "antara": current["antara"] if current else None,
        "mahaStart": current.get("mahaStart") if current else None,
        "mahaEnd": current.get("mahaEnd") if current else None,
        "periods": periods,
        "lagnaSign": lagna_sign,
        "ke_version": _chara_cache.get("ke_version"),
        "source_notes": _chara_cache.get("source_notes", []),
        "structured_books": _chara_cache.get("structured", {}),
        "year_rules_note": _chara_cache.get("year_rules"),
    }
    # ladder for UI
    if current:
        payload["ladder"] = [
            {"levelLabel": "Mahadasha (sign)", "lord": current.get("maha"), "start": current.get("mahaStart"), "end": current.get("mahaEnd")},
            {"levelLabel": "Antardasha (sign)", "lord": current.get("antara"), "start": current.get("antaraStart") if "antaraStart" in current else None, "end": current.get("antaraEnd") if "antaraEnd" in current else current.get("mahaEnd")},
        ]
    return payload
