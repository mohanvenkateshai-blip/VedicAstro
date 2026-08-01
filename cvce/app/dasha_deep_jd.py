"""
JD-based comprehensive dasha deep analysis.

Used by POST /dasha/deep — accepts precomputed birth_jd, query_jd, sidereal Moon
longitude, and lagna index so callers (portal / muhurta) need not re-send place.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from jhora import utils as jhora_utils

from vedic_engine.core.panchanga import NAK_LORD, NAKSHATRAS, RASHIS
from vedic_engine.prediction.dasha import (
    DASHA_EFFECTS,
    compute_dasha,
    compute_vimshottari,
    compute_yogini,
)
from vedic_engine.prediction.functional_nature import compute_functional_nature
from vedic_engine.synthesis.dasha_analyzer import (
    DashaImpactAnalyzer,
    YOGAKARAKA_BY_LAGNA,
)

# Sign lords for simplified Chara year fallback (lord-in-own-sign baseline).
_SIGN_LORD_HOME: dict[int, int] = {
    0: 0,   # Aries → Mars home Aries (prefer first)
    1: 1,   # Taurus → Venus
    2: 2,   # Gemini → Mercury
    3: 3,   # Cancer → Moon
    4: 4,   # Leo → Sun
    5: 5,   # Virgo → Mercury
    6: 6,   # Libra → Venus
    7: 7,   # Scorpio → Mars (prefer Scorpio for dual)
    8: 8,   # Sag → Jupiter
    9: 9,   # Cap → Saturn
    10: 10, # Aq → Saturn
    11: 11, # Pisces → Jupiter
}

# Dual-lord preferred home for year count (classical KN Rao dual ownership handling simplified)
_LORD_OF: dict[int, str] = {
    0: "Mars",
    1: "Venus",
    2: "Mercury",
    3: "Moon",
    4: "Sun",
    5: "Mercury",
    6: "Venus",
    7: "Mars",
    8: "Jupiter",
    9: "Saturn",
    10: "Saturn",
    11: "Jupiter",
}

# Natural domicile(s) for year-count endpoint when natal placement unknown
_LORD_DOMICILE: dict[str, list[int]] = {
    "Sun": [4],
    "Moon": [3],
    "Mars": [0, 7],
    "Mercury": [2, 5],
    "Jupiter": [8, 11],
    "Venus": [1, 6],
    "Saturn": [9, 10],
}


def _jd_to_date_str(jd: float) -> str:
    """Gregorian YYYY-MM-DD from Julian Day (UT)."""
    try:
        y, m, d, _fh = jhora_utils.jd_to_gregorian(float(jd))
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except Exception:
        # Fallback civil conversion
        z = int(jd + 0.5)
        if z >= 2299161:
            alpha = int((z - 1867216.25) / 36524.25)
            a = z + 1 + alpha - int(alpha / 4)
        else:
            a = z
        b = a + 1524
        c = int((b - 122.1) / 365.25)
        d_val = int(365.25 * c)
        e = int((b - d_val) / 30.6001)
        day = int(b - d_val - int(30.6001 * e))
        month = e - 1 if e < 14 else e - 13
        year = c - 4716 if month > 2 else c - 4715
        return f"{year:04d}-{month:02d}-{day:02d}"


def _nakshatra_from_moon(moon_lon_sidereal: float) -> tuple[str, int]:
    lon = float(moon_lon_sidereal) % 360.0
    idx = int(lon / (360.0 / 27.0)) % 27
    return NAKSHATRAS[idx], idx


def _period_dict(planet: str | None, start: str | None, end: str | None, **extra) -> dict:
    out = {
        "planet": planet,
        "start": start,
        "end": end,
    }
    out.update(extra)
    return out


def _vimshottari_block(birth_date: str, query_date: str, moon_lon: float, nak: str, lagna_name: str) -> dict:
    result = compute_vimshottari(
        birth_date,
        birth_time="12:00",
        birth_nakshatra=nak,
        birth_moon_lon=moon_lon,
        query_date=query_date,
    )
    maha = result.current_mahadasha
    antar = result.current_antardasha
    maha_d = (
        _period_dict(
            maha.planet,
            maha.start_date,
            maha.end_date,
            years=maha.duration_years,
            level="Maha",
            effect=DASHA_EFFECTS.get(maha.planet, ""),
        )
        if maha
        else None
    )
    antar_d = (
        _period_dict(
            antar.planet,
            antar.start_date,
            antar.end_date,
            years=antar.duration_years,
            level="Antar",
        )
        if antar
        else None
    )

    score = float(result.dasha_score or 0)
    verdict = None
    try:
        if maha and antar:
            ladder = [
                {
                    "lord": maha.planet,
                    "level": 1,
                    "levelLabel": "Mahadasha",
                    "start": maha.start_date,
                    "end": maha.end_date,
                },
                {
                    "lord": antar.planet,
                    "level": 2,
                    "levelLabel": "Antardasha",
                    "start": antar.start_date,
                    "end": antar.end_date,
                },
            ]
            intel = DashaImpactAnalyzer().analyze(
                ladder,
                lagna_rashi=lagna_name,
                janma_rashi=RASHIS[int(moon_lon % 360 // 30) % 12],
            )
            if intel:
                score = float(intel.get("score", score))
                verdict = intel.get("final_verdict")
                if maha_d is not None:
                    maha_d["verdict"] = verdict
                    maha_d["score"] = score
                if antar_d is not None:
                    antar_d["verdict"] = verdict
                    antar_d["score"] = score
    except Exception:
        pass

    return {
        "maha": maha_d,
        "antar": antar_d,
        "score": score,
        "balance_at_birth_years": result.balance_of_dasha,
        "birth_nakshatra": result.birth_nakshatra,
        "birth_nak_lord": result.birth_nak_lord,
        "summary": result.summary or "",
    }


def _add_years_str(date_str: str, years: float) -> str:
    y, m, d = map(int, date_str.split("-"))
    dt = datetime(y, m, d) + timedelta(days=years * 365.25)
    return dt.strftime("%Y-%m-%d")


def _yogini_block(birth_date: str, query_date: str, moon_lon: float, nak: str) -> dict:
    """Current Yogini maha/antar, repeating the 36y cycle past the first pass."""
    from vedic_engine.prediction.dasha import YOGINI_EFFECTS, YOGINI_ORDER, YOGINI_PERIODS, _yogini_antardashas

    yoginis = compute_yogini(
        birth_date,
        birth_nakshatra=nak,
        birth_moon_lon=moon_lon,
        query_date=query_date,
    )
    maha_d = None
    antar_d = None

    def _match(periods):
        nonlocal maha_d, antar_d
        for y in periods:
            start = y.start_date if hasattr(y, "start_date") else y["start"]
            end = y.end_date if hasattr(y, "end_date") else y["end"]
            if not (start <= query_date <= end or start <= query_date < end):
                continue
            if hasattr(y, "yogini"):
                name, lord, years, nature, effect = y.yogini, y.lord, y.duration_years, y.nature, y.effect
                antars = y.antardashas or []
            else:
                name, lord = y["yogini"], y["lord"]
                years, nature, effect = y["years"], y["nature"], y["effect"]
                antars = y.get("antardashas") or []
            maha_d = {
                "yogini": name,
                "planet": lord,
                "lord": lord,
                "start": start,
                "end": end,
                "years": years,
                "nature": nature,
                "effect": effect,
            }
            for ad in antars:
                if ad["start"] <= query_date < ad["end"]:
                    antar_d = {
                        "yogini": ad["yogini"],
                        "planet": ad["yogini"],
                        "start": ad["start"],
                        "end": ad["end"],
                        "years": ad.get("years"),
                        "days": ad.get("days"),
                    }
                    break
            return True
        return False

    if _match(yoginis):
        return {"maha": maha_d, "antar": antar_d}

    # Advance full 36y cycles until query falls inside a mahadasha
    if not yoginis:
        return {"maha": None, "antar": None}

    cycle_start = yoginis[-1].end_date
    # First cycle may have reduced balance; subsequent cycles are full 36y
    start_idx = YOGINI_ORDER.index(yoginis[0].yogini)
    # After first cycle the next maha is the one after the last of first cycle
    next_idx = (YOGINI_ORDER.index(yoginis[-1].yogini) + 1) % 8

    guard = 0
    while guard < 20 and maha_d is None:
        guard += 1
        extended = []
        current = cycle_start
        for i in range(8):
            name = YOGINI_ORDER[(next_idx + i) % 8]
            years = float(YOGINI_PERIODS[name])
            end = _add_years_str(current, years)
            info = YOGINI_EFFECTS[name]
            antars = _yogini_antardashas(name, YOGINI_PERIODS[name], current)
            extended.append(
                {
                    "yogini": name,
                    "lord": info["lord"],
                    "start": current,
                    "end": end,
                    "years": years,
                    "nature": info["nature"],
                    "effect": info["effect"],
                    "antardashas": antars,
                }
            )
            current = end
        if _match(extended):
            break
        cycle_start = extended[-1]["end"]
        next_idx = (YOGINI_ORDER.index(extended[-1]["yogini"]) + 1) % 8

    return {"maha": maha_d, "antar": antar_d}


def _chara_years_for_sign(sign_idx: int) -> int:
    """
    Simplified Chara years when natal planet placements are unavailable.

    Uses distance from the dasha sign to its lord's primary domicile
    (KN Rao style count, excluding starting sign; own-sign → 12 years).
    """
    lord = _LORD_OF[sign_idx]
    homes = _LORD_DOMICILE[lord]
    # Prefer the domicile that yields a conventional 1–12 count
    best = 12
    for home in homes:
        if home == sign_idx:
            return 12
        # forward count excluding start
        steps = (home - sign_idx) % 12
        if steps == 0:
            steps = 12
        best = min(best, steps) if best != 12 or home == homes[0] else steps
        # also backward for even/odd rule: odd signs forward, even backward (0-based even = odd rasi)
    # Odd rashis (Aries=1): forward; even: backward — 1-based odd = 0-based even
    is_odd_rasi = (sign_idx % 2 == 0)
    home = homes[0]
    if is_odd_rasi:
        steps = (home - sign_idx) % 12
    else:
        steps = (sign_idx - home) % 12
    if steps == 0:
        steps = 12
    return int(steps)


def _chara_block(lagna_idx: int, birth_date: str, query_date: str) -> dict:
    """Lagna-start Chara sequence with simplified year weights."""
    li = int(lagna_idx) % 12
    # Direction: odd rasi lagna → forward; even → backward (common KN Rao seed)
    forward = li % 2 == 0
    periods = []
    cur = datetime.strptime(birth_date, "%Y-%m-%d")
    q = query_date
    current = None
    for i in range(12):
        sidx = (li + i) % 12 if forward else (li - i) % 12
        years = _chara_years_for_sign(sidx)
        start = cur.strftime("%Y-%m-%d")
        end_dt = cur + timedelta(days=years * 365.25)
        end = end_dt.strftime("%Y-%m-%d")
        row = {
            "sign": RASHIS[sidx],
            "sign_idx": sidx,
            "years": years,
            "start": start,
            "end": end,
        }
        periods.append(row)
        if start <= q < end or (i == 11 and start <= q <= end):
            current = {
                "maha": row["sign"],
                "sign": row["sign"],
                "sign_idx": sidx,
                "start": start,
                "end": end,
                "years": years,
                "antara": None,
            }
            # Proportional antardasha of 12 sub-signs
            ant_cur = cur
            for j in range(12):
                asidx = (sidx + j) % 12 if forward else (sidx - j) % 12
                ant_years = years / 12.0
                a_start = ant_cur.strftime("%Y-%m-%d")
                ant_end_dt = ant_cur + timedelta(days=ant_years * 365.25)
                a_end = ant_end_dt.strftime("%Y-%m-%d")
                if a_start <= q < a_end or (j == 11 and a_start <= q <= a_end):
                    current["antara"] = RASHIS[asidx]
                    current["antara_start"] = a_start
                    current["antara_end"] = a_end
                    break
                ant_cur = ant_end_dt
        cur = end_dt

    return {
        "current": current,
        "method": "Chara Dasha (Lagna-start, simplified years — full natal lord placement not supplied)",
        "lagna": RASHIS[li],
        "periods_preview": periods[:4],
    }


def _kalachakra_deha_jeeva(moon_lon_sidereal: float) -> dict:
    """Deha/Jeeva rasi from Moon nakshatra-pada (BPHS Vol.2 Ch.46)."""
    from jhora.horoscope.dhasa.raasi import kalachakra as kala_mod
    from jhora.panchanga.drik import nakshatra_pada

    lon = float(moon_lon_sidereal) % 360.0
    nak, pada, rem_deg = nakshatra_pada(lon)
    nak0, pada0 = nak - 1, pada - 1
    kc_index = kala_mod._kc_group_for_nak(nak0)
    is_savya = kc_index < 2
    cycle = kala_mod._cycle_for(kc_index, pada0)
    deha_idx, jeeva_idx = (cycle[0], cycle[-1]) if is_savya else (cycle[-1], cycle[0])
    deha = {
        "sign": RASHIS[deha_idx],
        "sign_idx": int(deha_idx),
        "role": "deha",
        "note": "Body (Deha) sign of the Kalachakra wheel — malefics here afflict health (BPHS Vol.2 Ch.46)",
    }
    jeeva = {
        "sign": RASHIS[jeeva_idx],
        "sign_idx": int(jeeva_idx),
        "role": "jeeva",
        "note": "Life-force (Jeeva) sign of the Kalachakra wheel — malefics here afflict vitality/spirit",
    }
    return {
        "deha": deha,
        "jeeva": jeeva,
        "nakshatra": NAKSHATRAS[nak0],
        "pada": int(pada),
        "kc_index": int(kc_index),
        "direction": "Savya" if is_savya else "Apasavya",
        "remainder_deg": round(float(rem_deg), 4),
    }


def _build_analysis(
    vim: dict,
    yog: dict,
    chara: dict,
    kala: dict,
    fn: dict,
) -> str:
    parts: list[str] = []
    vm = vim.get("maha") or {}
    va = vim.get("antar") or {}
    if vm.get("planet"):
        line = f"Vimshottari: {vm['planet']} Mahadasha"
        if va.get("planet"):
            line += f" / {va['planet']} Antardasha"
        line += f" (score {vim.get('score', 0):+g})."
        if vm.get("effect"):
            line += f" Theme — {vm['effect']}."
        parts.append(line)

    ym = yog.get("maha") or {}
    ya = yog.get("antar") or {}
    if ym.get("yogini"):
        line = f"Yogini: {ym['yogini']} ({ym.get('nature', '')})"
        if ya.get("yogini"):
            line += f" / {ya['yogini']} sub-period"
        line += "."
        if ym.get("effect"):
            line += f" {ym['effect']}"
        parts.append(line)

    cur = chara.get("current") or {}
    if cur.get("maha"):
        line = f"Chara: {cur['maha']} sign period"
        if cur.get("antara"):
            line += f" / {cur['antara']} sub-period"
        line += "."
        parts.append(line)

    if kala.get("deha") and kala.get("jeeva"):
        parts.append(
            f"Kalachakra wheel: Deha={kala['deha']['sign']}, Jeeva={kala['jeeva']['sign']} "
            f"({kala.get('direction', '')} from {kala.get('nakshatra', '')} pada {kala.get('pada', '')})."
        )

    yk = fn.get("yogakaraka") or []
    ben = fn.get("benefic") or []
    mal = fn.get("malefic") or []
    lagna = fn.get("lagna") or "?"
    parts.append(
        f"Functional nature for {lagna} Lagna — Yogakaraka: "
        f"{', '.join(yk) if yk else 'none'}; "
        f"benefics: {', '.join(ben) if ben else '—'}; "
        f"malefics: {', '.join(mal) if mal else '—'}."
    )

    # Cross-hint: is current Vimshottari lord yogakaraka / functional benefic?
    lord = (vm or {}).get("planet")
    if lord:
        if lord in yk:
            parts.append(f"{lord} is Yogakaraka for this Lagna — Mahadasha can deliver raja-yoga results.")
        elif lord in ben:
            parts.append(f"{lord} is a functional benefic for {lagna} — period generally supportive.")
        elif lord in mal:
            parts.append(f"{lord} is a functional malefic for {lagna} — expect effort and friction themes.")

    return " ".join(parts) if parts else "Insufficient data for dasha deep analysis."


def build_dasha_deep(
    birth_jd: float,
    query_jd: float,
    moon_lon_sidereal: float,
    lagna_idx: int,
) -> dict:
    """Assemble the canonical /dasha/deep response body."""
    birth_date = _jd_to_date_str(birth_jd)
    query_date = _jd_to_date_str(query_jd)
    moon = float(moon_lon_sidereal) % 360.0
    li = int(lagna_idx) % 12
    lagna_name = RASHIS[li]
    nak, _nak_i = _nakshatra_from_moon(moon)

    vim = _vimshottari_block(birth_date, query_date, moon, nak, lagna_name)
    yog = _yogini_block(birth_date, query_date, moon, nak)
    chara = _chara_block(li, birth_date, query_date)
    kala = _kalachakra_deha_jeeva(moon)
    fn_full = compute_functional_nature(li)
    fn = {
        "yogakaraka": fn_full.get("yogakaraka", []),
        "benefic": fn_full.get("benefic", []),
        "malefic": fn_full.get("malefic", []),
        "lagna": fn_full.get("lagna"),
        "lagna_idx": fn_full.get("lagna_idx"),
        "neutral": fn_full.get("neutral", []),
        "source": fn_full.get("source"),
    }
    analysis = _build_analysis(vim, yog, chara, kala, fn)

    return {
        "vimshottari": {
            "maha": vim.get("maha"),
            "antar": vim.get("antar"),
            "score": float(vim.get("score") or 0),
            "balance_at_birth_years": vim.get("balance_at_birth_years"),
            "birth_nakshatra": vim.get("birth_nakshatra"),
            "birth_nak_lord": vim.get("birth_nak_lord"),
        },
        "yogini": {
            "maha": yog.get("maha"),
            "antar": yog.get("antar"),
        },
        "chara": {
            "current": chara.get("current"),
            "method": chara.get("method"),
            "lagna": chara.get("lagna"),
        },
        "kalachakra": {
            "deha": kala.get("deha"),
            "jeeva": kala.get("jeeva"),
            "nakshatra": kala.get("nakshatra"),
            "pada": kala.get("pada"),
            "direction": kala.get("direction"),
        },
        "functional_nature": {
            "yogakaraka": fn["yogakaraka"],
            "benefic": fn["benefic"],
            "malefic": fn["malefic"],
        },
        "analysis": analysis,
        "meta": {
            "birth_jd": birth_jd,
            "query_jd": query_jd,
            "birth_date": birth_date,
            "query_date": query_date,
            "moon_lon_sidereal": round(moon, 6),
            "lagna_idx": li,
            "lagna": lagna_name,
            "yogakaraka_table": YOGAKARAKA_BY_LAGNA.get(lagna_name),
        },
    }
