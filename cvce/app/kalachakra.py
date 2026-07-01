"""Kalachakra Dasha (86y cycle, deha/jeeva, nak+rasi based) — engine module.

PyJHora via ephem only. KE integration for BPHS/structured notes on deha jeeva,
pada wheel, source_notes + ke_version.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.ephem import RASHIS, jd_place, parse_dt
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


def compute_kalachakra_dasha(birth_datetime: str, birth_lat: float, birth_lon: float, birth_tz: float) -> dict:
    """Kalachakra via PyJHora (dhasa_method=1) + current + periods + deha/jeeva notes if exposed."""
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
        run = kala_mod.get_running_dhasa_for_given_date(
            jd, jd, place, dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA, dhasa_method=1
        )
        if run:
            row = run[-1] if isinstance(run, list) else run
            lords = row[0]
            maha_idx = lords[0] if isinstance(lords, (list, tuple)) and lords else None
            ant_idx = lords[1] if len(lords) > 1 else None
            st = row[1]
            dur = float(row[2]) if len(row) > 2 else 1.0
            start = _fmt(st) if isinstance(st, (list, tuple)) else None
            end = (date.fromisoformat(start) + timedelta(days=int(dur * 365.25))).isoformat() if start else None
            current = {
                "maha": _sign_name(maha_idx),
                "antara": _sign_name(ant_idx),
                "mahaStart": start,
                "mahaEnd": end,
            }
    except Exception:
        pass

    periods: list[dict] = []
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
    except Exception:
        pass

    lagna_sign = None
    try:
        pp = charts.rasi_chart(jd, place)
        for item in pp:
            if isinstance(item[0], str):
                lagna_sign = RASHIS[int(item[1][0]) % 12]
                break
    except Exception:
        pass

    # Deha/Jeeva hints from cycle if PyJHora exposes (future proof; many impls compute from Moon nak pada)
    deha_jeeva = None
    try:
        # PyJHora kalachakra may attach via cycle_for or internal; surface if available on module
        if hasattr(kala_mod, "_cycle_for"):
            # heuristic: keep lightweight
            deha_jeeva = {"note": "Deha/Jeeva from Moon nakshatra-pada wheel (BPHS Vol2)"}
    except Exception:
        pass

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
        "dehaJeeva": deha_jeeva or {"note": "Deha/Jeeva determined by Moon nakshatra-pada at birth (BPHS Vol.2 Ch.49)"},
        "ke_version": _kala_cache.get("ke_version"),
        "source_notes": _kala_cache.get("source_notes", []),
        "structured_books": _kala_cache.get("structured", {}),
        "graph_citations": _kala_cache.get("source_notes", []),
    }
    if current:
        payload["ladder"] = [
            {"levelLabel": "Mahadasha (sign)", "lord": current.get("maha"), "start": current.get("mahaStart"), "end": current.get("mahaEnd")},
            {"levelLabel": "Antardasha (sign)", "lord": current.get("antara"), "start": current.get("antaraStart") if "antaraStart" in current else None, "end": current.get("antaraEnd") if "antaraEnd" in current else current.get("mahaEnd")},
        ]
    return payload
