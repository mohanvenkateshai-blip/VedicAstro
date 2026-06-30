"""Assemble unified report facts for Phase 7–11 report API."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.chart import build_chart_geometry
from app.config import get_settings
from app.dasha_vimshottari import (
    antardasha_table,
    birth_balance,
    dasha_deep_payload,
    running_ladder,
)
from app.ephem import jd_place, parse_dt, set_ayanamsa
from knowledge_engine.integration import get_knowledge_engine, get_llm_narration
from knowledge_engine.integration import get_prediction_enhancer as PredictionEnhancer
from knowledge_engine.integration import get_structured_book, get_hierarchy_for_node, get_nodes_for_chapter
from vedic_engine.prediction.ashtakavarga import SAV_BANDS, compute_ashtakavarga
from vedic_engine.synthesis.dasha_analyzer import DashaImpactAnalyzer
from vedic_engine.synthesis.engine import VedicPredictor

_report_rules_version: str | None = None
_predictor: VedicPredictor | None = None
_report_registered = False


def _clear_report_knowledge_caches() -> None:
    """Invalidate graph-backed rule caches used when assembling report facts."""
    try:
        from knowledge_engine.integration import clear_knowledge_engine_cache

        clear_knowledge_engine_cache()
    except Exception:
        # legacy direct clears (kept only as fallback during transition)
        try:
            from graph_rag.rules_provider import GraphTransitRules
            GraphTransitRules._instance = None
        except Exception:
            pass
        try:
            from graph_rag.muhurta_rules_provider import GraphMuhurtaRules
            GraphMuhurtaRules._instance = None
        except Exception:
            pass
        try:
            from graph_rag.graph import GraphRAG
            GraphRAG()._loaded = False
        except Exception:
            pass


def _on_report_refresh(new_version: str) -> None:
    global _report_rules_version, _predictor
    _report_rules_version = new_version
    _predictor = None
    _clear_report_knowledge_caches()
    # Propagate structured signals (chapter/hierarchy) on refresh
    try:
        get_structured_book("BPHS")
        get_structured_book("Phaladeepika")
        get_nodes_for_chapter("BPHS", "ch-1")
    except Exception:
        pass


def _get_predictor() -> VedicPredictor:
    global _predictor
    if _predictor is None:
        _predictor = VedicPredictor()
    return _predictor


def _register_report_engine() -> None:
    global _report_registered
    if _report_registered:
        return
    try:
        get_knowledge_engine().register_engine("report", on_refresh=_on_report_refresh)
        _report_registered = True
    except Exception:
        pass


_register_report_engine()


def _ensure_report_registered() -> None:
    if not _report_registered:
        _register_report_engine()


_RASHIS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

_AKV_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def _rashi_idx(name: str) -> int | None:
    try:
        return _RASHIS.index(name)
    except ValueError:
        return None


def _get_band_label(bindus: int) -> str:
    for band_name, (lo, hi, verdict, label) in SAV_BANDS.items():
        if lo <= bindus <= hi:
            return band_name
    return "depleted"


def _compute_timing_merge(dasha_intel: dict | None, transit_intel: dict | None) -> dict | None:
    if not dasha_intel:
        return None

    d_score = dasha_intel.get("score", 0)
    d_verdict = dasha_intel.get("final_verdict", "mixed")
    m_lord = dasha_intel.get("maha_lord", "")
    a_lord = dasha_intel.get("antar_lord", "")

    t_verdict = (transit_intel or {}).get("overall_verdict", "neutral")
    t_score = 2 if t_verdict == "shubh" else (-2 if t_verdict == "ashubh" else 0)

    combined = d_score + t_score

    if combined >= 5:
        window, label = "shubh", "Strong favourable window — ideal for major initiatives"
    elif combined >= 2:
        window, label = "shubh", "Moderately favourable window — good for steady progress"
    elif combined <= -5:
        window, label = (
            "ashubh",
            "Challenging window — avoid major decisions, focus on consolidation",
        )
    elif combined <= -2:
        window, label = "ashubh", "Unfavourable window — delays and friction expected"
    else:
        window, label = "mixed", "Mixed window — results vary by domain; selective action advised"

    reasons = []
    if d_verdict == "shubh":
        reasons.append(f"{m_lord}–{a_lord} dasha period is favourable (score {d_score})")
    elif d_verdict == "ashubh":
        reasons.append(f"{m_lord}–{a_lord} dasha period is challenging (score {d_score})")
    else:
        reasons.append(f"{m_lord}–{a_lord} dasha period gives mixed results (score {d_score})")

    if t_verdict == "shubh":
        reasons.append("Current planetary transits are supportive")
    elif t_verdict == "ashubh":
        reasons.append("Current transits add friction — patience recommended")

    return {
        "verdict": window,
        "label": label,
        "score": combined,
        "dasha_score": d_score,
        "transit_verdict": t_verdict,
        "reasons": reasons,
    }


def _next_shubh_days(
    from_date: str,
    lat: float,
    lon: float,
    tz: float,
    janma_rashi: str | None,
    janma_nakshatra: str | None,
    natal_sign: dict | None,
    dasha_maha: str | None = None,
    dasha_antar: str | None = None,
    dasha_score: int = 0,
    limit: int = 3,
    max_scan: int = 90,
) -> list[dict]:
    """Scan forward from from_date to find the next shubh transit days."""
    from vedic_engine.prediction.gochar import compute_gochar
    from vedic_engine.synthesis.transit_analyzer import TransitImpactAnalyzer

    analyzer = TransitImpactAnalyzer()
    start = date.fromisoformat(from_date) + timedelta(days=1)
    results: list[dict] = []

    for i in range(max_scan):
        d = start + timedelta(days=i)
        date_str = d.isoformat()
        try:
            gochar = compute_gochar(
                date_str=date_str,
                lat=lat,
                lon=lon,
                tz=tz,
                janma_rashi=janma_rashi,
                janma_nakshatra=janma_nakshatra,
                natal_sign=natal_sign,
            )
            intel = analyzer.analyze(
                gochar,
                natal_sign=natal_sign,
                dasha_maha=dasha_maha,
                dasha_antar=dasha_antar,
                dasha_score=dasha_score,
            )
            if intel and intel.overall_verdict == "shubh":
                results.append(
                    {
                        "date": date_str,
                        "summary": intel.day_summary,
                        "score": intel.overall_score,
                        "top_drivers": intel.top_drivers[:2],
                    }
                )
                if len(results) >= limit:
                    break
        except Exception:
            continue

    return results


def _compute_forecast(
    antar_table: list[dict],
    lagna_rashi: str | None,
    janma_rashi: str | None,
    natal_sign: dict | None,
    today_str: str,
    limit: int = 8,
) -> list[dict]:
    analyzer = DashaImpactAnalyzer()
    today = date.fromisoformat(today_str)
    forecast: list[dict] = []

    for row in antar_table:
        try:
            start_d = date.fromisoformat(row["start"])
        except Exception:
            continue
        dur_days = max(1, int(row.get("durationYears", 1) * 365.25))
        end_d = start_d + timedelta(days=dur_days)

        if end_d < today:
            continue
        if len(forecast) >= limit:
            break

        mini_ladder = [
            {
                "lord": row["maha"],
                "start": str(start_d),
                "end": str(end_d),
                "level": 1,
                "levelLabel": "Mahadasha",
            },
            {
                "lord": row["antara"],
                "start": str(start_d),
                "end": str(end_d),
                "level": 2,
                "levelLabel": "Antardasha",
            },
        ]

        intel = analyzer.analyze(
            mini_ladder,
            lagna_rashi=lagna_rashi,
            janma_rashi=janma_rashi,
            natal_sign=natal_sign,
        )
        if intel:
            is_current = start_d <= today <= end_d
            forecast.append(
                {
                    "maha": row["maha"],
                    "antar": row["antara"],
                    "start": str(start_d),
                    "end": str(end_d),
                    "durationYears": round(row.get("durationYears", 0), 2),
                    "isCurrent": is_current,
                    "verdict": intel["final_verdict"],
                    "score": intel["score"],
                    "summary": intel["summary"],
                    "profession": intel["profession"][:2],
                    "wealth": intel["wealth"][:2],
                    "health": intel["health"][:1],
                    "family": intel["family"][:1],
                    "caution": intel["caution"][:1],
                }
            )

    return forecast


def build_report_facts(
    birth_datetime: str,
    birth_lat: float,
    birth_lon: float,
    birth_tz: float,
    ayanamsa: str = "LAHIRI",
    name: str | None = None,
    query_date: str | None = None,
    query_time: str = "12:00",
    include_dasha_tree: bool = False,
) -> dict:
    _ensure_report_registered()
    set_ayanamsa(ayanamsa)
    settings = get_settings()
    dt = parse_dt(birth_datetime)
    jd, place = jd_place(dt, birth_lat, birth_lon, birth_tz)

    if not query_date:
        query_date = datetime.now().strftime("%Y-%m-%d")

    geometry = build_chart_geometry(
        jd,
        place,
        ayanamsa=ayanamsa,
        vargas=settings.VARGAS[:2] if settings.VARGAS else [1, 9],
    )

    lagna = geometry.get("lagna") or {}
    planets = geometry.get("planets") or []
    moon = next((p for p in planets if p.get("planet") == "Moon"), None)
    janma_rashi = moon.get("rashi") if moon else None
    janma_nakshatra = moon.get("nakshatra") if moon else None
    natal_sign = geometry.get("natalSign")

    ladder = running_ladder(jd, place, depth=5)
    antar_table = antardasha_table(jd, place)

    dasha_block = {
        "balanceAtBirth": birth_balance(jd, place),
        "current": [row["lord"] for row in ladder],
        "currentLadder": ladder,
        "antardashaTable": antar_table,
        "dashaTree": (
            dasha_deep_payload(jd, place, max_level=5)["dashaTree"] if include_dasha_tree else []
        ),
    }

    pred = _get_predictor().predict(
        date=query_date,
        time=query_time,
        lat=birth_lat,
        lon=birth_lon,
        tz=birth_tz,
        janma_rashi=janma_rashi,
        janma_nakshatra=janma_nakshatra,
        birth_date=birth_datetime[:10],
        birth_time=birth_datetime[11:16] if len(birth_datetime) > 10 else "12:00",
        birth_lat=birth_lat,
        birth_lon=birth_lon,
        birth_tz=birth_tz,
        birth_moon_lon=moon.get("longitude") if moon else None,
        natal_sign=natal_sign,
    )

    enhancer = PredictionEnhancer()
    enhancements = enhancer.enhance(
        pred,
        natal_sign=natal_sign,
        janma_nakshatra=janma_nakshatra,
        janma_rashi=janma_rashi,
    )

    # Consumer update: attach chapter hierarchy to graph matches/citations in output
    # Expanded: also enrich from engine results that now carry chapter_citation/hierarchy_path
    try:
        for ins in (enhancements or {}).get("natal_insights") or []:
            for gm in (ins.get("graph_matches") or [])[:1]:
                nid = gm.get("id") if isinstance(gm, dict) else None
                if nid:
                    gm["chapter_hierarchy"] = get_hierarchy_for_node(nid)
        for yc in (enhancements or {}).get("yoga_citations") or []:
            if isinstance(yc, dict):
                nid = yc.get("id")
                if not nid and isinstance(yc.get("node"), dict):
                    nid = yc.get("node", {}).get("id")
                if nid:
                    yc["chapter_hierarchy"] = get_hierarchy_for_node(nid)
                    break
        # Pull from predictor outputs (yogas, dasha, ashtakavarga) which now resolve via KE
        if getattr(pred, "yogas", None):
            for y in (pred.yogas or [])[:3]:
                if hasattr(y, "chapter_citation") and y.chapter_citation:
                    # surface first concrete one
                    if "yoga_chapter_citation" not in (pred.__dict__ if hasattr(pred, "__dict__") else {}):
                        setattr(pred, "yoga_chapter_citation", y.chapter_citation)
        if getattr(pred, "dasha", None) and getattr(pred.dasha, "chapter_citation", None):
            setattr(pred, "dasha_chapter_citation", pred.dasha.chapter_citation)
        if getattr(pred, "ashtakavarga", None) and getattr(pred.ashtakavarga, "chapter_citation", None):
            setattr(pred, "ashtakavarga_chapter_citation", pred.ashtakavarga.chapter_citation)
    except Exception:
        pass

    transit_intel = (enhancements or {}).get("transit_intelligence")
    transit_verdict = transit_intel.get("overall_verdict") if transit_intel else None

    # --- Alternate dasha systems (Chara, Kalachakra, Kaksha) ---
    alternate_dashas = None
    try:
        from jhora.panchanga.drik import Date as DrikDate

        from app.dasha_extras import (
            chara_dasha_payload,
            kaksha_payload,
            kalachakra_dasha_payload,
        )

        dob = DrikDate(dt.year, dt.month, dt.day)
        tob = (dt.hour, dt.minute, dt.second)
        q_dt = parse_dt(f"{query_date}T{query_time}:00")
        query_jd, _ = jd_place(q_dt, birth_lat, birth_lon, birth_tz)
        alternate_dashas = {
            "chara": chara_dasha_payload(jd, place, dob, tob, query_jd=query_jd),
            "kalachakra": kalachakra_dasha_payload(jd, place, dob, tob, query_jd=query_jd),
            "kaksha": kaksha_payload(jd, place, query_jd=query_jd),
        }
    except Exception:
        alternate_dashas = None

    lagna_rashi = lagna.get("rashi")

    dasha_intel = DashaImpactAnalyzer().analyze(
        ladder,
        lagna_rashi=lagna_rashi,
        janma_rashi=janma_rashi,
        natal_sign=natal_sign,
        transit_verdict=transit_verdict,
    )

    # --- Yogas ---
    panchanga = None
    yogas_raw = None
    try:
        from app.server import _panchanga, _yogas

        panchanga = _panchanga(jd, place)
        yogas_raw = _yogas(jd, place)
    except Exception:
        pass

    # --- Shadbala ---
    shadbala_data = None
    try:
        from app.server import _shadbala

        shadbala_data = _shadbala(jd, place)
    except Exception:
        pass

    # --- Ashtakavarga ---
    ashtakavarga_data = None
    try:
        natal_sign_idx: dict[str, int] = {}
        for p in planets:
            pname = p.get("planet")
            rashi = p.get("rashi")
            if pname in _AKV_PLANETS and rashi:
                idx = _rashi_idx(rashi)
                if idx is not None:
                    natal_sign_idx[pname] = idx

        lagna_idx = _rashi_idx(lagna_rashi) if lagna_rashi else 0

        akv = compute_ashtakavarga(natal_sign_idx, lagna_idx or 0)

        # SAV with band labels per sign
        sav_annotated = []
        for sign_idx, bindus in enumerate(akv.sav):
            band = _get_band_label(bindus)
            sav_annotated.append(
                {
                    "sign": _RASHIS[sign_idx],
                    "bindus": bindus,
                    "band": band,
                }
            )

        ashtakavarga_data = {
            "bav": akv.bav,
            "sav": akv.sav,
            "sav_annotated": sav_annotated,
            "planet_totals": akv.planet_totals,
            "total": akv.total_sav,
        }
    except Exception:
        pass

    # --- Timing merge ---
    timing_merge = _compute_timing_merge(dasha_intel, transit_intel)

    # --- Dasha forecast (upcoming antardasha periods) ---
    forecast = _compute_forecast(
        antar_table,
        lagna_rashi=lagna_rashi,
        janma_rashi=janma_rashi,
        natal_sign=natal_sign,
        today_str=query_date,
    )

    # --- Next shubh days (only when transit is not already shubh) ---
    next_shubh_days: list[dict] = []
    if transit_verdict != "shubh":
        try:
            d_maha = dasha_intel.get("maha_lord") if dasha_intel else None
            d_antar = dasha_intel.get("antar_lord") if dasha_intel else None
            d_score = dasha_intel.get("score", 0) if dasha_intel else 0
            next_shubh_days = _next_shubh_days(
                query_date,
                birth_lat,
                birth_lon,
                birth_tz,
                janma_rashi,
                janma_nakshatra,
                natal_sign,
                dasha_maha=d_maha,
                dasha_antar=d_antar,
                dasha_score=d_score,
            )
        except Exception:
            pass

    # --- Planet table ---
    planet_table = [
        {
            "planet": p.get("planet"),
            "rashi": p.get("rashi"),
            "degree": p.get("degLabel") or p.get("degree"),
            "nakshatra": p.get("nakshatra"),
            "pada": p.get("pada"),
            "dignity": p.get("dignity"),
            "retrograde": p.get("retrograde", False),
        }
        for p in planets
        if p.get("planet")
        in {
            "Sun",
            "Moon",
            "Mars",
            "Mercury",
            "Jupiter",
            "Venus",
            "Saturn",
            "Rahu",
            "Ketu",
            "Lagna",
        }
    ]

    facts = {
        "schemaVersion": "1.1",
        "meta": {
            "name": name,
            "birth_datetime": birth_datetime,
            "birth_lat": birth_lat,
            "birth_lon": birth_lon,
            "birth_tz": birth_tz,
            "ayanamsa": ayanamsa,
            "query_date": query_date,
            "query_time": query_time,
            "engine": "PyJHora/SwissEphemeris",
        },
        "natal": {
            "lagna": {
                "rashi": lagna_rashi,
                "degree": lagna.get("degLabel"),
                "nakshatra": lagna.get("nakshatra"),
                "pada": lagna.get("pada"),
            },
            "moon": {
                "rashi": janma_rashi,
                "nakshatra": janma_nakshatra,
                "pada": moon.get("pada") if moon else None,
            },
            "planets": planet_table,
        },
        "panchanga": panchanga,
        "dashas": {
            "balanceAtBirth": birth_balance(jd, place),
            "current": dasha_block.get("current"),
            "currentLadder": ladder,
            "antardashaTable": antar_table,
            "dashaTree": dasha_block.get("dashaTree"),
        },
        "alternate_dashas": alternate_dashas,
        "dasha_intelligence": dasha_intel,
        "transit_intelligence": transit_intel,
        "graph_enhancements": {
            "transit_citations": (enhancements or {}).get("transit_citations") or [],
            "yoga_citations": (enhancements or {}).get("yoga_citations") or [],
            "natal_insights": (enhancements or {}).get("natal_insights") or [],
            "god_node_insights": (enhancements or {}).get("god_node_insights") or [],
            "text_conflicts": (enhancements or {}).get("text_conflicts") or [],
            "graph_stats": (enhancements or {}).get("graph_stats"),
        },
        # Chapter-aware classical provenance (from engines consuming KE structured chapters + patches)
        "classical_sources": {
            "yoga": getattr(pred, "yoga_chapter_citation", None) or (getattr(pred, "yogas", [None])[0].chapter_citation if getattr(pred, "yogas", None) and getattr(pred.yogas[0], "chapter_citation", None) else None),
            "dasha": getattr(pred, "dasha_chapter_citation", None) or getattr(getattr(pred, "dasha", None), "chapter_citation", None),
            "ashtakavarga": getattr(pred, "ashtakavarga_chapter_citation", None) or getattr(getattr(pred, "ashtakavarga", None), "chapter_citation", None),
        },
        "next_shubh_days": next_shubh_days,
        "timing_merge": timing_merge,
        "forecast": forecast,
        "yogas": {
            "activeCount": yogas_raw.get("activeCount") if yogas_raw else 0,
            "totalChecked": yogas_raw.get("totalChecked") if yogas_raw else None,
            "yogas": yogas_raw.get("yogas") if yogas_raw else {},
        },
        "ashtakavarga": ashtakavarga_data,
        "shadbala": shadbala_data,
        "prediction_summary": pred.summary if hasattr(pred, "summary") else None,
    }

    birth = {
        "name": name,
        "birth_datetime": birth_datetime,
        "birth_lat": birth_lat,
        "birth_lon": birth_lon,
        "birth_tz": birth_tz,
    }

    try:
        narration = get_llm_narration(facts, birth)
        if narration is not None:
            facts["narration"] = narration
    except Exception as e:
        facts["narration_error"] = str(e)[:200]

    try:
        ke = get_knowledge_engine()
        facts["knowledge_engine"] = ke.health()
    except Exception:
        facts["knowledge_engine"] = None

    return facts
