"""
VedicAstro CVCE — Canonical Vedic Calculation Engine (FastAPI).

A hardened fork of the standalone MuhurtaCosmos precision backend. It wraps the
PyJHora (Swiss Ephemeris) engine and exposes:

  • granular transit/natal endpoints (positions, panchanga, rahu-kalam, dasha,
    shadbala, yogas, natal) — used for incremental/transit queries, and
  • a single composed `/chart` endpoint returning the canonical `chart_data`
    payload (geometry + dasha + shadbala + yogas + birth panchanga) that the
    VedicAstro portal stores once per horoscope.

`/cross-validate` keeps an independent jyotishganit positional check. All
positional logic lives in `app.ephem`; chart geometry in `app.chart`.

Config (CORS origins, port, ayanamsa, vargas, rate limits) comes from the
environment via `app.config` — see `.env.example`. No secrets in code.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from jhora import const
from jhora.panchanga import drik

from .config import get_settings
from .ephem import (PLANET_NAMES, RASHIS, NAKSHATRAS, WEEKDAYS,
                    parse_dt, jd_place, set_ayanamsa, ascendant, positions)
from .chart import build_chart_geometry
from .chart_svg import chart_svg

settings = get_settings()

SHADBALA_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
SHADBALA_ROWS = ["sthana", "kaala", "dig", "cheshta", "naisargika", "drik",
                 "total_shashtiamsa", "total_rupa", "strength_ratio"]
TITHI_NAMES = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
               "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
               "Trayodashi", "Chaturdashi", "Purnima/Amavasya"]
YOGA_NAMES = ["Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
              "Sukarma", "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata",
              "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyana", "Parigha",
              "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra",
              "Vaidhriti"]
KARANA_NAMES = ["Kimstughna", "Bava", "Balava", "Kaulava", "Taitila", "Gara",
                "Vanija", "Vishti", "Shakuni", "Chatushpada", "Naga"]

app = FastAPI(title="VedicAstro CVCE", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# --- rate limiting (per client IP) ----------------------------------------
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store[client_ip]
            if now - t < settings.RATE_LIMIT_WINDOW
        ]
        if len(_rate_limit_store[client_ip]) >= settings.RATE_LIMIT_REQUESTS:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        _rate_limit_store[client_ip].append(now)
    return await call_next(request)


# --- request models -------------------------------------------------------
class TransitRequest(BaseModel):
    datetime: str = Field(..., description="Local civil datetime, ISO 8601 e.g. 2026-06-20T12:00:00")
    lat: float
    lon: float
    tz_offset: float = 0.0
    ayanamsa: str = settings.DEFAULT_AYANAMSA


class BirthRequest(BaseModel):
    birth_datetime: str
    birth_lat: float
    birth_lon: float
    birth_tz: float = 0.0
    ayanamsa: str = settings.DEFAULT_AYANAMSA
    name: Optional[str] = None


class PrashnaRequest(BaseModel):
    """Horary chart — defaults to current UTC moment."""
    birth_lat: float
    birth_lon: float
    birth_tz: float = 0.0
    birth_datetime: Optional[str] = None
    ayanamsa: str = settings.DEFAULT_AYANAMSA
    name: Optional[str] = "Prashna"


# --- panchanga helper (shared by /panchanga and /chart) -------------------
def _panchanga(jd: float, place) -> dict:
    def label(arr, names, base=1):
        n = int(arr[0])
        idx = (n - base) % len(names)
        return {"number": n, "name": names[idx],
                "start": round(float(arr[1]), 4) if len(arr) > 1 else None,
                "end": round(float(arr[2]), 4) if len(arr) > 2 else None}

    t = drik.tithi(jd, place)
    nk = drik.nakshatra(jd, place)
    yg = drik.yogam(jd, place)
    kr = list(drik.karana(jd, place))
    vr = drik.vaara(jd, place)
    tnum = int(t[0])
    paksha = "Shukla" if tnum <= 15 else "Krishna"
    nnum = int(nk[0])
    vidx = int(vr) if not isinstance(vr, (list, tuple)) else int(vr[0])
    return {
        "tithi": {"number": tnum, "name": TITHI_NAMES[(tnum - 1) % 15], "paksha": paksha,
                  "start": round(float(t[1]), 4) if len(t) > 1 else None,
                  "end": round(float(t[2]), 4) if len(t) > 2 else None},
        "nakshatra": {"number": nnum, "name": NAKSHATRAS[(nnum - 1) % 27],
                      "pada": int(nk[1]) if len(nk) > 1 else None,
                      "start": round(float(nk[2]), 4) if len(nk) > 2 else None,
                      "end": round(float(nk[3]), 4) if len(nk) > 3 else None},
        "yoga": label(yg, YOGA_NAMES),
        "karana": {"number": int(kr[0]), "name": KARANA_NAMES[(int(kr[0]) - 1) % 11],
                   "start": round(float(kr[1]), 4) if len(kr) > 1 else None,
                   "end": round(float(kr[2]), 4) if len(kr) > 2 else None},
        "vara": {"index": vidx, "name": WEEKDAYS[vidx % 7]},
    }


def _dasha(jd: float, place) -> dict:
    from app.dasha_vimshottari import antardasha_table, birth_balance, running_ladder

    ladder = running_ladder(jd, place, depth=5)
    return {
        "balanceAtBirth": birth_balance(jd, place),
        "currentLadder": ladder,
        "current": ladder[-1]["lords"] if ladder else None,
        "periods": antardasha_table(jd, place),
    }


def _shadbala(jd: float, place) -> dict:
    from jhora.horoscope.chart import strength
    sb = strength.shad_bala(jd, place)  # 9 rows x 7 planets
    out = {}
    for col, planet in enumerate(SHADBALA_PLANETS):
        entry = {}
        for row, key in enumerate(SHADBALA_ROWS):
            try:
                entry[key] = round(float(sb[row][col]), 2)
            except Exception:
                entry[key] = None
        out[planet] = entry
    return out


def _yogas(jd: float, place) -> dict:
    from jhora.horoscope.chart import yoga
    details = yoga.get_yoga_details(jd, place)
    active, count, total = {}, 0, None
    if isinstance(details, (list, tuple)) and details:
        ydict = details[0]
        count = details[1] if len(details) > 1 else len(ydict)
        total = details[2] if len(details) > 2 else None
        for key, val in ydict.items():
            active[key] = {
                "name": val[1] if len(val) > 1 else key,
                "definition": val[2] if len(val) > 2 else "",
                "prediction": val[3] if len(val) > 3 else "",
            }
    return {"activeCount": count, "totalChecked": total, "yogas": active}


def _guard(fn):
    try:
        return fn(), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


# --- endpoints ------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "engine": "PyJHora",
            "version": getattr(const, "_APP_VERSION", "4.8.7"),
            "ayanamsa": settings.DEFAULT_AYANAMSA,
            "vargas": settings.VARGAS}


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.post("/positions")
def positions_endpoint(req: TransitRequest):
    set_ayanamsa(req.ayanamsa)
    jd, place = jd_place(parse_dt(req.datetime), req.lat, req.lon, req.tz_offset)
    return {
        "datetime": req.datetime, "jd": jd, "ayanamsa": req.ayanamsa,
        "ayanamsaValue": round(drik.get_ayanamsa_value(jd), 6),
        "ascendant": ascendant(jd, place),
        "positions": positions(jd, place),
    }


@app.post("/panchanga")
def panchanga_endpoint(req: TransitRequest):
    set_ayanamsa(req.ayanamsa)
    jd, place = jd_place(parse_dt(req.datetime), req.lat, req.lon, req.tz_offset)
    return {"datetime": req.datetime, "jd": jd, **_panchanga(jd, place)}


@app.post("/rahu-kalam")
def rahu_kalam(req: TransitRequest):
    jd, place = jd_place(parse_dt(req.datetime), req.lat, req.lon, req.tz_offset)
    rk = drik.raahu_kaalam(jd, place)
    yg = drik.yamaganda_kaalam(jd, place)
    gk = drik.gulikai_kaalam(jd, place)
    sr = drik.sunrise(jd, place)
    ss = drik.sunset(jd, place)
    return {
        "datetime": req.datetime,
        "rahu_kalam": {"start": rk[0], "end": rk[1]},
        "yamaganda": {"start": yg[0], "end": yg[1]},
        "gulika": {"start": gk[0], "end": gk[1]},
        "sunrise": sr[1] if isinstance(sr, (list, tuple)) else sr,
        "sunset": ss[1] if isinstance(ss, (list, tuple)) else ss,
    }


@app.post("/dasha")
def dasha_endpoint(req: BirthRequest):
    set_ayanamsa(req.ayanamsa)
    jd, place = jd_place(parse_dt(req.birth_datetime), req.birth_lat, req.birth_lon, req.birth_tz)
    return {"birth_datetime": req.birth_datetime, "jd": jd, **_dasha(jd, place)}


@app.post("/shadbala")
def shadbala_endpoint(req: BirthRequest):
    set_ayanamsa(req.ayanamsa)
    jd, place = jd_place(parse_dt(req.birth_datetime), req.birth_lat, req.birth_lon, req.birth_tz)
    return {"birth_datetime": req.birth_datetime, "jd": jd, "shadbala": _shadbala(jd, place)}


@app.post("/yogas")
def yogas_endpoint(req: BirthRequest):
    set_ayanamsa(req.ayanamsa)
    jd, place = jd_place(parse_dt(req.birth_datetime), req.birth_lat, req.birth_lon, req.birth_tz)
    return {"birth_datetime": req.birth_datetime, "jd": jd, **_yogas(jd, place)}


@app.post("/natal")
def natal(req: BirthRequest):
    """Lightweight natal bundle (positions, ascendant, dasha, shadbala, yogas).
    Each block is independently guarded. For the full canonical payload use /chart."""
    set_ayanamsa(req.ayanamsa)
    jd, place = jd_place(parse_dt(req.birth_datetime), req.birth_lat, req.birth_lon, req.birth_tz)
    result = {"birth_datetime": req.birth_datetime, "jd": jd, "ayanamsa": req.ayanamsa}
    result["ascendant"], _ = _guard(lambda: ascendant(jd, place))
    result["positions"], _ = _guard(lambda: positions(jd, place))
    val, err = _guard(lambda: _dasha(jd, place))
    result["dasha"] = val["periods"] if val else None
    result["dashaCurrent"] = val["current"] if val else None
    if err:
        result["dashaError"] = err
    val, err = _guard(lambda: _shadbala(jd, place))
    result["shadbala"] = val if val else None
    if err:
        result["shadbalaError"] = err
    val, err = _guard(lambda: _yogas(jd, place))
    if val:
        result["yogas"] = val["yogas"]
        result["yogaActiveCount"] = val["activeCount"]
    elif err:
        result["yogaError"] = err
    return result


@app.post("/chart")
def chart(req: BirthRequest):
    """Canonical `chart_data` in one round-trip — the contract the portal stores.

    Geometry (ascendant, planets, natalSign, vargas, ashtakavarga) is
    deterministic; the time blocks (dasha, shadbala, yogas, birth panchanga)
    are each guarded so one failing sub-engine never sinks the response.
    """
    set_ayanamsa(req.ayanamsa)
    jd, place = jd_place(parse_dt(req.birth_datetime), req.birth_lat, req.birth_lon, req.birth_tz)

    geometry, gerr = _guard(
        lambda: build_chart_geometry(jd, place, req.ayanamsa, settings.VARGAS))
    if geometry is None:
        raise HTTPException(status_code=500, detail=f"chart geometry failed: {gerr}")

    out = {
        "schemaVersion": "1.0",
        "meta": {
            "name": req.name,
            "birth_datetime": req.birth_datetime,
            "birth_lat": req.birth_lat,
            "birth_lon": req.birth_lon,
            "birth_tz": req.birth_tz,
            "engine": "PyJHora/SwissEphemeris",
        },
        **geometry,
    }

    dasha, derr = _guard(lambda: _dasha(jd, place))
    out["dashas"] = dasha
    if derr:
        out.setdefault("errors", {})["dasha"] = derr
    sb, serr = _guard(lambda: _shadbala(jd, place))
    out["shadbala"] = sb
    if serr:
        out.setdefault("errors", {})["shadbala"] = serr
    yg, yerr = _guard(lambda: _yogas(jd, place))
    out["yogas"] = yg
    if yerr:
        out.setdefault("errors", {})["yogas"] = yerr
    pan, perr = _guard(lambda: _panchanga(jd, place))
    out["panchanga"] = pan
    if perr:
        out.setdefault("errors", {})["panchanga"] = perr
    return out


@app.post("/cross-validate")
def cross_validate(req: TransitRequest):
    """Compare PyJHora sidereal longitudes against jyotishganit for the same
    instant. jyotishganit defaults to True Chitra Paksha while we drive PyJHora
    with Lahiri, so a roughly constant offset is expected (`ayanamsaDeltaDeg`)."""
    set_ayanamsa(req.ayanamsa)
    jd, place = jd_place(parse_dt(req.datetime), req.lat, req.lon, req.tz_offset)
    pj = {p["planet"]: p["longitude"] for p in positions(jd, place)}

    jg, jg_error = {}, None
    try:
        import jyotishganit.main as jgm
        dt = parse_dt(req.datetime)
        chart_obj = jgm.calculate_birth_chart(dt, req.lat, req.lon, req.tz_offset)
        cj = jgm.get_birth_chart_json(chart_obj)
        for house in cj["d1Chart"]["houses"]:
            sign_idx = RASHIS.index(house["sign"]) if house["sign"] in RASHIS else None
            for occ in house.get("occupants", []):
                name = occ.get("celestialBody")
                if name and sign_idx is not None:
                    jg[name] = round(sign_idx * 30 + float(occ["signDegrees"]), 6)
    except Exception as e:
        jg_error = f"{type(e).__name__}: {e}"

    rows, main_deltas = [], []
    for name in PLANET_NAMES:
        a, b = pj.get(name), jg.get(name)
        d = None
        if a is not None and b is not None:
            d = (a - b + 540) % 360 - 180
            if name not in ("Rahu", "Ketu"):
                main_deltas.append(d)
        rows.append({"planet": name, "pyjhora": a, "jyotishganit": b,
                     "deltaDeg": round(d, 5) if d is not None else None})
    offset = None
    if main_deltas:
        s = sorted(main_deltas)
        offset = round(s[len(s) // 2], 5)
    flagged = []
    if offset is not None:
        for r in rows:
            if r["planet"] in ("Rahu", "Ketu") or r["deltaDeg"] is None:
                continue
            if abs(r["deltaDeg"] - offset) > 0.1:
                flagged.append(r["planet"])
    return {
        "datetime": req.datetime, "comparison": rows,
        "ayanamsaDeltaDeg": offset, "flagged": flagged,
        "note": ("Rahu/Ketu excluded from offset/flags: PyJHora uses the mean "
                 "lunar node, jyotishganit the true node (~1-2deg difference is expected)."),
        "jyotishganitError": jg_error,
    }


# =====================================================================
# Vedic Prediction Engine (optional — present only if vedic_engine imports)
# =====================================================================
try:
    from vedic_engine import VedicPredictor
    _predictor = VedicPredictor()
    _ENGINE_AVAILABLE = True
except Exception:
    _ENGINE_AVAILABLE = False
    _predictor = None

# GraphRAG enhancement layer (optional — present if knowledge-graph exists)
try:
    from graph_rag import PredictionEnhancer
    from graph_rag.rules_provider import graph_rules_enabled
    from graph_rag.graph_grok import grok_graph_stats, grok_graph_available
    from graph_rag.graph_gemini import gemini_graph_stats
    from graph_rag.graph_glm import glm_graph_stats
    from graph_rag.graph_deepseek import deepseek_graph_stats
    _enhancer = PredictionEnhancer()
    _GRAPH_AVAILABLE = True
except Exception:
    _GRAPH_AVAILABLE = False
    _enhancer = None

    def graph_rules_enabled() -> bool:
        return False

    def grok_graph_stats():
        return None

    def grok_graph_available() -> bool:
        return False

    def gemini_graph_stats():
        return None

    def glm_graph_stats():
        return None

    def deepseek_graph_stats():
        return None

# Unified Rules Engine
try:
    from rules_engine import RuleEngine
    _rules = RuleEngine()
    _RULES_AVAILABLE = True
except Exception:
    _RULES_AVAILABLE = False
    _rules = None

# Orchestration Engine
try:
    from orchestrator import orchestrator
    _ORCH_AVAILABLE = True
except Exception:
    _ORCH_AVAILABLE = False
    orchestrator = None


@app.get("/")
def index():
    """Browser-friendly landing — CVCE is an API; use the portal for the UI."""
    graph_rag = None
    if _GRAPH_AVAILABLE and _enhancer is not None:
        try:
            from graph_rag.rules_provider import active_transit_rules
            graph_rag = {
                "available": True,
                "stats": _enhancer.graph.stats,
                "rules_source": "graph" if active_transit_rules() else "hardcoded",
                "graph_as_rules_env": graph_rules_enabled(),
            }
        except Exception:
            graph_rag = {"available": True, "stats": _enhancer.graph.stats}

    payload = {
        "service": "VedicAstro CVCE",
        "description": "Canonical Vedic Calculation Engine (API only — no web UI here)",
        "status": "ok",
        "engine": "PyJHora",
        "version": getattr(const, "_APP_VERSION", "4.8.7"),
        "portal": "https://portal-omega-two-10.vercel.app/vedicastro",
        "status_page": "https://portal-omega-two-10.vercel.app/status",
        "graph_rag": graph_rag,
        "endpoints": {
            "health": "GET /health",
            "predict_health": "GET /predict/health",
            "predict_health_grok": "GET /predict/health/grok",
            "predict_health_gemini": "GET /predict/health/gemini",
            "predict_health_glm": "GET /predict/health/glm",
            "predict_health_deepseek": "GET /predict/health/deepseek",
            "chart": "POST /chart",
            "predict": "POST /predict",
            "prashna": "POST /prashna",
            "yogas": "POST /yogas",
            "dasha_deep": "POST /dasha-deep",
            "kp_system": "POST /kp-system",
            "varshaphala": "POST /varshaphala",
            "orchestrate": "POST /orchestrate",
            "docs": "GET /docs",
        },
        "example": {
            "chart": "curl -s https://vedicastro-cvce.fly.dev/chart -H 'content-type: application/json' "
                      "-d '{\"birth_datetime\":\"1975-04-22T19:15:00\",\"birth_lat\":12.2958,"
                      "\"birth_lon\":76.6394,\"birth_tz\":5.5,\"name\":\"Mohan\"}'",
            "prashna": "curl -s https://vedicastro-cvce.fly.dev/prashna -H 'content-type: application/json' "
                       "-d '{\"birth_lat\":12.97,\"birth_lon\":77.59,\"birth_tz\":5.5}'",
        },
    }
    return JSONResponse(payload)


class PredictionRequest(BaseModel):
    date: str = Field(default="")
    time: str = Field(default="12:00")
    lat: float = Field(default=12.30)
    lon: float = Field(default=76.65)
    tz: float = Field(default=5.5)
    janma_rashi: Optional[str] = None
    janma_nakshatra: Optional[str] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_lat: Optional[float] = None
    birth_lon: Optional[float] = None
    birth_tz: Optional[float] = None
    birth_moon_lon: Optional[float] = None
    natal_signs: Optional[dict] = None


@app.post("/predict")
def predict(req: PredictionRequest):
    if not _ENGINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Prediction engine not available")
    r = _predictor.predict(
        date=req.date or None, time=req.time, lat=req.lat, lon=req.lon, tz=req.tz,
        janma_rashi=req.janma_rashi, janma_nakshatra=req.janma_nakshatra,
        birth_date=req.birth_date, birth_time=req.birth_time,
        birth_lat=req.birth_lat, birth_lon=req.birth_lon, birth_tz=req.birth_tz,
        birth_moon_lon=req.birth_moon_lon, natal_sign=req.natal_signs,
    )
    panch, gochar, dasha = r.panchanga, r.gochar, r.dasha
    return {
        "date": r.query_date, "time": r.query_time,
        "overall_verdict": r.overall_verdict, "overall_score": r.overall_score,
        "summary": r.summary,
        "panchanga": {
            "tithi": {"name": panch.tithi_name, "paksha": panch.tithi_paksha, "num": panch.tithi_num,
                      "group": panch.tithi_group, "lord": getattr(panch, "tithi_lord", None),
                      "verdict": panch.tithi_verdict} if panch else None,
            "vaar": panch.weekday if panch else None,
            "nakshatra": {"name": panch.nakshatra, "nature": panch.nakshatra_nature,
                          "lord": panch.nakshatra_lord, "verdict": panch.nakshatra_verdict} if panch else None,
            "yoga": {"name": panch.yoga_name, "nature": panch.yoga_nature,
                     "verdict": panch.yoga_verdict} if panch else None,
            "karana": {"name": panch.karana_name, "verdict": panch.karana_verdict} if panch else None,
            "sunrise": panch.sunrise if panch else None,
            "sunset": panch.sunset if panch else None,
        },
        "gochar": {
            "overall_verdict": gochar.overall_verdict, "overall_score": gochar.overall_score,
            "synthesis": gochar.synthesis,
            "planets": [
                {"planet": p.planet, "rashi": p.rashi, "nakshatra": p.nakshatra,
                 "house_from_janma": p.house_from_janma, "verdict": p.verdict,
                 "house_quality": p.house_quality, "score": p.score,
                 "effects": p.effects, "retrograde": p.retrograde,
                 "vedha": p.vedha_active, "combustion": p.combustion, "latta": p.latta}
                for p in gochar.planet_predictions
            ] if gochar else [],
            "moorthy": gochar.moorthy if gochar else None,
            "sade_sati": gochar.sade_sati if gochar else None,
            "kantaka_shani": gochar.kantaka_shani if gochar else None,
            "ashtama_shani": gochar.ashtama_shani if gochar else None,
            "tara_balam": gochar.tara_balam if gochar else None,
        } if gochar else None,
        "dasha": {
            "mahadasha": {"planet": dasha.current_mahadasha.planet,
                          "start": dasha.current_mahadasha.start_date,
                          "end": dasha.current_mahadasha.end_date}
            if dasha and dasha.current_mahadasha else None,
            "antardasha": {"planet": dasha.current_antardasha.planet,
                           "start": dasha.current_antardasha.start_date,
                           "end": dasha.current_antardasha.end_date}
            if dasha and dasha.current_antardasha else None,
            "score": dasha.dasha_score if dasha else 0,
            "summary": dasha.summary if dasha else "",
        } if dasha else None,
        "yogas": [
            {"name": y.name, "category": y.category, "description": y.description,
             "benefic": y.benefic, "planets": y.planets_involved}
            for y in (r.yogas or [])
        ],
        "ashtakavarga": {
            "total_sav": r.ashtakavarga.total_sav,
            "moon_transit_bindus": r.ashtakavarga.moon_transit_bindus,
            "moon_transit_verdict": r.ashtakavarga.moon_transit_verdict,
            "moon_transit_band": r.ashtakavarga.moon_transit_band,
            "sav": r.ashtakavarga.sav,
            "transit_sav": {
                p: {"sign": d["sign"], "bindus": d["bindus"], "band": d["band"]}
                for p, d in r.ashtakavarga.transit_sav.items()
            } if r.ashtakavarga.transit_sav else {},
        } if r.ashtakavarga else None,
        "muhurta_yogas": r.muhurta_yogas,
        "warnings": r.warnings,
        "transit_summary": getattr(r, "transit_summary", ""),
        "rules_source": "graph" if (_GRAPH_AVAILABLE and graph_rules_enabled()) else "hardcoded",
        "graph_enhancements": _graph_enhance(r, req) if _GRAPH_AVAILABLE else None,
    }


@app.get("/predict/health")
def predict_health():
    from graph_rag.rules_provider import graph_rules_enabled, active_transit_rules
    graph_rules = active_transit_rules()
    grok_stats = grok_graph_stats()
    gemini_stats = gemini_graph_stats()
    glm_stats = glm_graph_stats()
    deepseek_stats = deepseek_graph_stats()
    return {"engine": "vedic-prediction-engine",
            "version": _predictor.version if _ENGINE_AVAILABLE else "0.0.0",
            "available": _ENGINE_AVAILABLE,
            "graph_rag": {"available": _GRAPH_AVAILABLE,
                          "stats": _enhancer.graph.stats if _GRAPH_AVAILABLE else None,
                          "rules_source": "graph" if graph_rules else "hardcoded",
                          "graph_as_rules_env": graph_rules_enabled()},
            "graph_rag_grok": grok_stats,
            "graph_rag_gemini": gemini_stats,
            "graph_rag_glm": glm_stats,
            "graph_rag_deepseek": deepseek_stats,
            "rules_engine": {"available": _RULES_AVAILABLE}}


@app.get("/predict/health/grok")
def predict_health_grok():
    """Experimental Grok-enriched graph stats (does not affect /predict rules)."""
    stats = grok_graph_stats()
    if stats is None:
        raise HTTPException(
            status_code=404,
            detail="graph-grok.json not deployed — run scripts/build-graph-grok.py && sync-graph.sh --grok",
        )
    return {
        "initiative": "grok",
        "production_unchanged": True,
        "graph_rag": stats,
        "compare": {
            "production_endpoint": "/predict/health",
            "promote_when": "beats_baseline is true and quality spot-check passes",
        },
    }


@app.get("/predict/health/gemini")
def predict_health_gemini():
    """Experimental Gemini batch-enriched graph stats (does not affect /predict rules)."""
    stats = gemini_graph_stats()
    if stats is None:
        raise HTTPException(
            status_code=404,
            detail="graph-gemini.json not deployed — run gemini-batch merge --output graph-gemini.json",
        )
    return {
        "initiative": "gemini",
        "production_unchanged": True,
        "graph_rag": stats,
        "compare": {
            "production_endpoint": "/predict/health",
            "grok_endpoint": "/predict/health/grok",
        },
    }


@app.get("/predict/health/glm")
def predict_health_glm():
    """Experimental GLM 5.2 batch graph stats (does not affect /predict rules)."""
    stats = glm_graph_stats()
    if stats is None:
        raise HTTPException(
            status_code=404,
            detail="graph-glm.json not deployed — run glm-batch-graph-extract.py merge",
        )
    return {
        "initiative": "glm",
        "model": "glm-5.2",
        "production_unchanged": True,
        "graph_rag": stats,
        "compare": {
            "production_endpoint": "/predict/health",
            "gemini_endpoint": "/predict/health/gemini",
        },
    }


@app.get("/predict/health/deepseek")
def predict_health_deepseek():
    stats = deepseek_graph_stats()
    if stats is None:
        raise HTTPException(
            status_code=404,
            detail="graph-deepseek.json not deployed — run deepseek-graph-extract.py run",
        )
    return {
        "initiative": "deepseek",
        "model": "deepseek-v4-flash",
        "production_unchanged": True,
        "graph_rag": stats,
        "compare": {
            "production_endpoint": "/predict/health",
            "gemini_endpoint": "/predict/health/gemini",
        },
    }


# =====================================================================
# Unified Rules Engine endpoints
# =====================================================================

@app.get("/rules")
def get_rules():
    """Expose the unified rules database for frontend consumption."""
    if not _RULES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Rules engine not available")
    return _rules.rules


@app.get("/rules/{category}")
def get_rules_category(category: str):
    """Get a specific rules category: panchanga, transit, yogas, dasha, dignity."""
    if not _RULES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Rules engine not available")
    data = _rules.rules.get("categories", {}).get(category)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")
    return data


class RuleQuery(BaseModel):
    type: str
    planet: Optional[str] = None
    house: Optional[int] = None
    janma_nak: Optional[str] = None
    transit_nak: Optional[str] = None
    janma_rashi: Optional[str] = None
    tithi_num: Optional[int] = None
    nakshatra: Optional[str] = None
    sign: Optional[str] = None
    degree: Optional[float] = None
    yoga_name: Optional[str] = None
    positions: Optional[dict] = None
    query: Optional[dict] = None
    natal_sign: Optional[dict] = None


# =====================================================================
# Orchestration Engine — route queries to the right engine
# =====================================================================

@app.get("/orchestrate/manifest")
def orchestrate_manifest():
    """Get the full engine manifest: all engines, capabilities, endpoints."""
    if not _ORCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    return orchestrator.manifest()


class OrchestrateRequest(BaseModel):
    query: str = Field(..., description="What do you want to know? Natural language query.")


@app.post("/orchestrate")
def orchestrate(req: OrchestrateRequest):
    """Route a natural language query to the correct engine.
    
    Example: "what will happen to me today?" → Gochar Phala Engine
             "when should I get married?" → Muhurta Nirnaya Engine
             "are we compatible?" → Koota Milan Engine
    """
    if not _ORCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    return orchestrator.resolve(req.query)


@app.get("/orchestrate/engine/{feature}")
def orchestrate_feature(feature: str):
    """Find which engine handles a specific feature.
    Example: /orchestrate/engine/transit → Gochar Phala Engine details"""
    if not _ORCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    result = orchestrator.engine_for(feature)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No engine found for: {feature}")
    return result


@app.get("/orchestrate/health")
def orchestrate_health():
    return {"available": _ORCH_AVAILABLE, "engines_registered": len(orchestrator._engines) if _ORCH_AVAILABLE else 0}


@app.post("/rules/query")
def rules_query(req: RuleQuery):
    """Single endpoint for all rule lookups. Returns computed rule results."""
    if not _RULES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Rules engine not available")

    try:
        match req.type:
            case "transit":
                return _rules.transit(req.planet, req.house or 1)
            case "vedha":
                return _rules.vedha_check(req.planet, req.house or 1)
            case "moorthi":
                return _rules.moorthi(req.house or 1)
            case "tara":
                return _rules.tara(req.janma_nak or "", req.transit_nak or "")
            case "latta":
                return _rules.latta(req.planet)
            case "yoga":
                return _rules.yoga(req.yoga_name or "")
            case "dasha":
                return _rules.dasha_sequence(req.planet)
            case "nakshatra":
                return _rules.nakshatra(req.nakshatra or "")
            case "tithi":
                return _rules.tithi_group(req.tithi_num or 1)
            case "dignity":
                return _rules.dignity(req.planet, req.sign or "", req.degree or 0)
            case "synthesis":
                return _rules.predict_synthesis(req.positions or {}, req.query or {})
            case _:
                raise HTTPException(status_code=400, detail=f"Unknown query type: {req.type}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _graph_enhance(r, req: PredictionRequest) -> dict | None:
    """Enrich prediction with graph-sourced classical citations."""
    if not _GRAPH_AVAILABLE or _enhancer is None:
        return None
    try:
        return _enhancer.enhance(
            r,
            natal_sign=req.natal_signs,
            janma_nakshatra=req.janma_nakshatra,
            janma_rashi=req.janma_rashi,
        )
    except Exception:
        return {"error": "graph enhancement failed", "graph_stats": _enhancer.graph.stats}


# =====================================================================
# Chart SVG endpoint — server-side chart rendering
# =====================================================================

class SvgRequest(BaseModel):
    ayanamsa: str = "LAHIRI"
    birth_datetime: str
    birth_lat: float
    birth_lon: float
    birth_tz: float
    size: int = Field(default=400, ge=200, le=800)
    name: Optional[str] = None


@app.post("/chart.svg")
def chart_svg_endpoint(req: SvgRequest):
    """Render a South Indian Kundali chart as SVG.

    POST body matches the /chart endpoint; returns image/svg+xml.
    Size defaults to 400px, range 200–800.
    """
    from fastapi.responses import Response
    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    try:
        geometry = build_chart_geometry(jd, place, ayanamsa=req.ayanamsa, vargas=settings.VARGAS)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart computation failed: {e}")

    # Attach meta if name provided
    if req.name:
        geometry["meta"] = {"name": req.name}

    svg = chart_svg(geometry, size=req.size)
    return Response(content=svg, media_type="image/svg+xml")


# =====================================================================
# Phase 3: Deep dasha, special points, koota matching
# =====================================================================

@app.post("/dasha-deep")
def dasha_deep(req: BirthRequest):
    """Vimshottari to 5 levels + shubh/ashubh verdict on Maha and Antar nodes."""
    from app.dasha_vimshottari import dasha_deep_payload
    from app.chart import build_chart_geometry
    from vedic_engine.synthesis.dasha_analyzer import DashaImpactAnalyzer

    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    payload = dasha_deep_payload(jd, place, max_level=5)

    # Annotate levels 1 (Maha) and 2 (Antar) with shubh/ashubh verdict.
    # Level 1 uses self-self combination (Vedic proxy for the whole Mahadasha period).
    try:
        geometry = build_chart_geometry(jd, place, ayanamsa=req.ayanamsa)
        planets = geometry.get("planets") or []
        moon = next((p for p in planets if p.get("planet") == "Moon"), None)
        lagna_rashi = (geometry.get("lagna") or {}).get("rashi")
        janma_rashi = moon.get("rashi") if moon else None
        natal_sign = geometry.get("natalSign")
        analyzer = DashaImpactAnalyzer()

        def _assess(maha_lord, maha_start, maha_end, antar_lord, antar_start, antar_end):
            ladder = [
                {"lord": maha_lord, "level": 1, "levelLabel": "Mahadasha",
                 "start": maha_start, "end": maha_end},
                {"lord": antar_lord, "level": 2, "levelLabel": "Antardasha",
                 "start": antar_start, "end": antar_end},
            ]
            try:
                intel = analyzer.analyze(ladder, lagna_rashi=lagna_rashi,
                                         janma_rashi=janma_rashi, natal_sign=natal_sign)
                return (intel.get("final_verdict"), intel.get("score")) if intel else (None, None)
            except Exception:
                return None, None

        for maha in payload.get("dashaTree", []):
            ms, me = maha["start"], maha.get("end", maha["start"])
            maha["verdict"], maha["score"] = _assess(maha["lord"], ms, me, maha["lord"], ms, me)
            for antar in maha.get("subPeriods", []):
                antar["verdict"], antar["score"] = _assess(
                    maha["lord"], ms, me, antar["lord"],
                    antar["start"], antar.get("end", antar["start"]),
                )
    except Exception:
        pass

    return {"birth_datetime": req.birth_datetime, "jd": jd, **payload}


class ReportFactsRequest(BirthRequest):
    query_date: Optional[str] = None
    query_time: str = "12:00"
    include_dasha_tree: bool = False


@app.post("/report/facts")
def report_facts(req: ReportFactsRequest):
    """Unified horoscope facts + dasha/transit intelligence for the report UI."""
    from app.report_facts import build_report_facts

    try:
        return build_report_facts(
            birth_datetime=req.birth_datetime,
            birth_lat=req.birth_lat,
            birth_lon=req.birth_lon,
            birth_tz=req.birth_tz,
            ayanamsa=req.ayanamsa,
            name=req.name,
            query_date=req.query_date,
            query_time=req.query_time,
            include_dasha_tree=req.include_dasha_tree,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report facts failed: {e}") from e


class SpecialPointsResponse(BaseModel):
    class Config:
        arbitrary_types_allowed = True


@app.post("/special-points")
def special_points(req: BirthRequest):
    """Compute Mandi, Gulika, Bhrigu Bindu, and other special lagna points."""
    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    results = {}

    def split_lon(name: str, lon: float):
        lon = lon % 360.0
        si = int(lon // 30)
        deg = round(lon - si * 30, 4)
        dd = int(deg)
        mm = int(round((deg - dd) * 60))
        return {
            "name": name,
            "longitude": round(lon, 4),
            "rashi": RASHIS[si],
            "signIndex": si,
            "degInSign": deg,
            "degLabel": f"{dd}°{mm:02d}′",
        }

    # Mandi (Maandi / Gulika's son — computed from weekday-based Saturn portion)
    try:
        from jhora.panchanga.drik import mandi_kaalam
        md = mandi_kaalam(jd, place)
        if md and isinstance(md, (list, tuple)):
            results["mandi"] = split_lon("Mandi (Maandi)", float(md[0]))
    except Exception:
        results["mandi"] = None

    # Gulika
    try:
        from jhora.panchanga.drik import gulikai_kaalam
        gk = gulikai_kaalam(jd, place)
        if gk and isinstance(gk, (list, tuple)):
            results["gulika"] = split_lon("Gulika", float(gk[0]))
    except Exception:
        results["gulika"] = None

    # Bhrigu Bindu — midpoint of Rahu and Moon (karmic point)
    try:
        pos = positions(jd, place)
        rahu_lon = None
        moon_lon = None
        for p in pos:
            if p.get("planet") == "Rahu":
                rahu_lon = p["longitude"]
            elif p.get("planet") == "Moon":
                moon_lon = p["longitude"]
        if rahu_lon is not None and moon_lon is not None:
            mid = (rahu_lon + moon_lon) / 2
            if abs(rahu_lon - moon_lon) > 180:
                mid = (mid + 180) % 360
            results["bhriguBindu"] = split_lon("Bhrigu Bindu", mid)
    except Exception:
        results["bhriguBindu"] = None

    return {
        "birth_datetime": req.birth_datetime,
        "jd": jd,
        "points": results,
    }


class KootaRequest(BaseModel):
    bride: dict  # {birth_datetime, birth_lat, birth_lon, birth_tz}
    groom: dict
    ayanamsa: str = "LAHIRI"


@app.post("/koota-match")
def koota_match(req: KootaRequest):
    """36-point Guna Milan (Koota) compatibility matching.
    Returns total score, per-koota breakdown, Kuja Dosha, and Vedha exceptions."""
    set_ayanamsa(req.ayanamsa)

    def get_moon_data(birth: dict) -> dict:
        dt = parse_dt(birth["birth_datetime"])
        jd, place = jd_place(dt, birth["birth_lat"], birth["birth_lon"], birth["birth_tz"])
        pos = positions(jd, place)
        moon = next((p for p in pos if p["planet"] == "Moon"), None)
        mars = next((p for p in pos if p["planet"] == "Mars"), None)
        if not moon:
            raise HTTPException(status_code=400, detail="Could not compute Moon position")
        return {
            "moonNak": moon["nakIndex"],
            "moonRashi": moon["signIndex"],
            "marsRashi": mars["signIndex"] if mars else None,
        }

    bride = get_moon_data(req.bride)
    groom = get_moon_data(req.groom)

    # Scoring
    nak_bride = bride["moonNak"]
    nak_groom = groom["moonNak"]
    count = ((nak_groom - nak_bride) % 27) + 1

    # 1. Varna (1 point)
    varna_map = {
        0: [0, 0, 0, 0, 1, 1, 2, 3, 2, 3, 3, 3, 2, 2, 3, 3, 2, 2, 3, 2, 2, 2, 3, 2, 2, 2, 2],
    }
    varna = [0] * 27  # Brahmin=0, Kshatriya=1, Vaishya=2, Shudra=3
    varna_groups = [
        [0, 5, 6, 9, 10, 17, 18, 23, 24],  # Brahmin
        [1, 2, 11, 12, 13, 25, 26],        # Kshatriya
        [3, 4, 14, 15, 19, 20, 21, 22],    # Vaishya
        [7, 8, 16],                          # Shudra
    ]
    for gid, naks in enumerate(varna_groups):
        for n in naks:
            varna[n] = gid
    bv = varna[nak_bride]
    gv = varna[nak_groom]
    varna_score = 1 if gv >= bv else 0

    # 2. Vashya (2 points)
    vashya_groups = [
        [0, 4, 5, 9, 20],                   # Manava
        [1, 2, 7, 12, 17, 24, 26],          # Vanachara
        [3, 13, 15, 19, 22, 23],            # Chatushpada
        [6, 8, 10, 11, 16, 18, 21, 25],     # Jalachara
    ]
    def vashya_of(nak): return next((i for i, g in enumerate(vashya_groups) if nak in g), -1)
    bva = vashya_of(nak_bride)
    gva = vashya_of(nak_groom)
    vashya_score = 2 if bva == gva else (1 if bva >= 0 and gva >= 0 else 0)

    # 3. Tara (3 points)
    tara_count = count % 9
    if tara_count == 0: tara_count = 9
    tara_score = 3 if tara_count in (1, 3, 5, 7, 9) else (1.5 if tara_count in (2, 4, 6, 8) else 0)

    # 4. Yoni (4 points)
    yoni_map = [1, 6, 0, 3, 10, 7, 4, 8, 13, 12, 11, 2, 5, 9, 0, 13, 10, 7, 4, 1, 3, 6, 2, 11, 5, 8, 12]
    byoni = yoni_map[nak_bride]
    gyoni = yoni_map[nak_groom]
    yoni_score = 4 if byoni == gyoni else (3 if byoni % 2 == gyoni % 2 else (2 if abs(byoni - gyoni) <= 3 else 1))

    # 5. Graha Maitri (5 points)
    rashi_friends = {
        0: [0, 4, 5, 8, 11], 1: [1, 2, 3, 9, 10], 2: [1, 2, 3, 9, 10],
        3: [1, 2, 3, 9, 10], 4: [0, 4, 5, 8, 11], 5: [0, 4, 5, 8, 11],
        6: [6, 7], 7: [6, 7], 8: [0, 4, 5, 8, 11],
        9: [1, 2, 3, 9, 10], 10: [1, 2, 3, 9, 10], 11: [0, 4, 5, 8, 11],
    }
    br = bride["moonRashi"]
    gr = groom["moonRashi"]
    maitri_score = 5 if gr in rashi_friends.get(br, []) else (4 if br in rashi_friends.get(gr, []) else 1)

    # 6. Gana (6 points)
    gana_map = [2, 0, 0, 2, 1, 0, 1, 2, 1, 0, 0, 2, 1, 0, 1, 1, 2, 2, 0, 0, 2, 1, 2, 2, 0, 2, 0]
    bg = gana_map[nak_bride]
    gg = gana_map[nak_groom]
    gana_score = 6 if bg == gg else (5 if abs(bg - gg) == 1 else (1 if abs(bg - gg) == 2 else 0))

    # 7. Bhakoot (7 points)
    brs = bride["moonRashi"]
    grs = groom["moonRashi"]
    bhakoot_friends = [{0, 2, 4, 6, 8, 10}, {1, 3, 5, 7, 9, 11}]
    bhakoot_score = 7 if (brs in bhakoot_friends[0]) == (grs in bhakoot_friends[0]) else 0

    # 8. Nadi (8 points)
    nadi_map = [0, 1, 0, 1, 2, 2, 1, 2, 1, 0, 0, 2, 1, 0, 1, 1, 2, 2, 0, 0, 2, 1, 2, 2, 0, 2, 0]
    ndi_score = 8 if nadi_map[nak_bride] != nadi_map[nak_groom] else 0

    total = varna_score + vashya_score + tara_score + yoni_score + maitri_score + gana_score + bhakoot_score + ndi_score

    # Kuja Dosha (Manglik)
    mars_positions = [1, 2, 4, 7, 8, 12]  # houses from Lagna where Mars is Manglik
    bride_manglik = bride["marsRashi"] is not None
    groom_manglik = groom["marsRashi"] is not None

    return {
        "totalScore": round(total, 1),
        "maxScore": 36,
        "verdict": "Excellent" if total >= 28 else "Good" if total >= 21 else "Average" if total >= 18 else "Below Average" if total >= 12 else "Low",
        "breakdown": {
            "varna": {"score": varna_score, "max": 1, "name": "Varna (Caste/Spiritual compatibility)"},
            "vashya": {"score": vashya_score, "max": 2, "name": "Vashya (Mutual attraction/control)"},
            "tara": {"score": tara_score, "max": 3, "name": "Tara (Health/longevity of couple)"},
            "yoni": {"score": yoni_score, "max": 4, "name": "Yoni (Sexual/physical compatibility)"},
            "grahaMaitri": {"score": maitri_score, "max": 5, "name": "Graha Maitri (Mental/psychological affinity)"},
            "gana": {"score": gana_score, "max": 6, "name": "Gana (Temperament match)"},
            "bhakoot": {"score": bhakoot_score, "max": 7, "name": "Bhakoot (Financial/family prosperity)"},
            "nadi": {"score": ndi_score, "max": 8, "name": "Nadi (Physiological/genetic health)"},
        },
        "kujaDosha": {
            "bride": bride_manglik,
            "groom": groom_manglik,
            "note": "Mars in 1,2,4,7,8,12 from Lagna indicates Kuja Dosha. Both partners having it cancels the affliction."
        },
    }


# =====================================================================
# KP System — Placidus houses + star lords + sub-lords + sub-sub lords
# =====================================================================

@app.post("/kp-system")
def kp_system(req: BirthRequest):
    """Krishnamurti Paddhati: Placidus house cusps with star lords, sub-lords,
    and sub-sub-lords for each cusp and planet position."""
    import swisseph as swe

    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    # Vimshottari lord sequence (repeating): Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury
    VIM_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    NAK_SPAN = 360.0 / 27  # 13°20'

    def vim_lord_for_degree(lon: float) -> str:
        """The Vimshottari dasha lord for a given ecliptic longitude.
        Each nakshatra (13°20') is ruled by one Vim lord; the sequence repeats every 9 nakshatras."""
        lon = lon % 360.0
        nak_idx = int(lon // NAK_SPAN)  # 0..26
        return VIM_LORDS[nak_idx % 9]

    def sub_lord_for_degree(lon: float, level: int) -> tuple[str, float]:
        """Get the sub-lord (level=1), sub-sub-lord (level=2) etc.
        Returns (lord_name, remaining_span_in_degrees)."""
        rem = (lon % NAK_SPAN)
        span = NAK_SPAN
        for _ in range(level):
            sub_span = span / 9.0
            sub_idx = int(rem // sub_span)
            lord = VIM_LORDS[sub_idx % 9]
            rem = rem % sub_span
            span = sub_span
            if level == 1:
                return lord, rem
        return VIM_LORDS[int(rem // (span / 9)) % 9], rem

    # Compute Placidus cusps
    lat = req.birth_lat
    lon = req.birth_lon
    ut_jd = jd - req.birth_tz / 24.0
    cusps, ascmc = swe.houses(ut_jd, lat, lon, b'P')

    # Compute planetary positions
    pos_list = positions(jd, place)

    def cusp_data(title: str, cusp_lon: float, is_planet: bool = False):
        cusp_lon = cusp_lon % 360.0
        si = int(cusp_lon // 30)
        deg = round(cusp_lon - si * 30, 4)
        starlord = vim_lord_for_degree(cusp_lon)
        sublord, _ = sub_lord_for_degree(cusp_lon, 1)
        sslord, _ = sub_lord_for_degree(cusp_lon, 2)
        return {
            "name": title,
            "longitude": round(cusp_lon, 4),
            "rashi": RASHIS[si],
            "signIndex": si,
            "degInSign": deg,
            "degLabel": f"{int(deg)}°{int(round((deg-int(deg))*60)):02d}′",
            "starLord": starlord,
            "subLord": sublord,
            "subSubLord": sslord,
        }

    # 12 house cusps
    # cusps is 12-element tuple: cusps[0]=H1, cusps[1]=H2, ..., cusps[11]=H12
    houses = [cusp_data(f"Bhava {i+1}", cusps[i]) for i in range(len(cusps))]

    # Planets with KP signification
    planets = []
    for p in pos_list:
        pd = cusp_data(p["planet"], p["longitude"], is_planet=True)
        pd["retro"] = p.get("retro", False)
        # Which bhava (house) does this planet occupy?
        plon = p["longitude"] % 360.0
        bhava = 12
        for i in range(len(cusps) - 1):
            start = cusps[i] % 360.0
            end = cusps[i + 1] % 360.0
            if start < end:
                if start <= plon < end:
                    bhava = i + 1
                    break
            else:
                if plon >= start or plon < end:
                    bhava = i + 1
                    break
        pd["bhava"] = bhava
        planets.append(pd)

    # Cuspal signification: each planet that is star-lord or sub-lord of a cusp
    # "signifies" that house. Collect per-planet significations.
    significance = {}
    for pi, p in enumerate(pos_list):
        pname = p["planet"]
        sig_houses = set()
        for h in houses:
            if h["starLord"] == pname:
                sig_houses.add(h["name"])
            if h["subLord"] == pname:
                sig_houses.add(h["name"])
        significance[pname] = sorted(sig_houses)

    return {
        "birth_datetime": req.birth_datetime,
        "jd": jd,
        "ayanamsa": req.ayanamsa,
        "houseSystem": "Placidus",
        "cusps": houses,
        "planets": planets,
        "signification": significance,
    }


# =====================================================================
# Additional Dasha Systems — Chara, Ashtottari, Yogini, Kalachakra, Drig
# =====================================================================

def _now_jd() -> float:
    from datetime import datetime, timezone
    import swisseph as swe
    now = datetime.now(timezone.utc)
    return swe.julday(now.year, now.month, now.day,
                      now.hour + now.minute / 60 + now.second / 3600)


def _parse_dasha_lords(lords) -> tuple[int | None, int | None]:
    """Normalize PyJHora lord tuples: (maha,) or (maha, antara, ...)."""
    if isinstance(lords, int):
        return lords, None
    if isinstance(lords, (list, tuple)) and lords:
        maha = lords[0] if isinstance(lords[0], int) else None
        antara = lords[1] if len(lords) > 1 and isinstance(lords[1], int) else None
        return maha, antara
    return None, None


def _ashtottari_current(jd, place, lord_name):
    """Running Ashtottari maha/antara at query time, with classical applicability."""
    from jhora import const
    from jhora.horoscope.chart import charts
    from jhora.horoscope.dhasa.graha import ashtottari

    pp = charts.rasi_chart(jd, place)
    if not ashtottari.applicability_check(pp):
        return {
            "maha": None,
            "antara": None,
            "applicable": False,
            "reason": (
                "Not applicable per Parasara — Rahu must occupy a kendra or trikona "
                "from the lagna lord (excluding the lagna itself). Use Vimshottari for this chart."
            ),
        }

    run = ashtottari.get_running_dhasa_for_given_date(
        _now_jd(),
        jd,
        place,
        dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
    )
    if not run:
        return None
    row = run[-1] if isinstance(run, list) else run
    maha, antara = _parse_dasha_lords(row[0])
    return {
        "maha": lord_name(maha) if maha is not None else None,
        "antara": lord_name(antara) if antara is not None else None,
        "applicable": True,
    }


@app.post("/dashas")
def all_dashas(req: BirthRequest):
    """Compute multiple dasha systems for a birth chart.
    Returns current periods for Vimshottari, Yogini, Ashtottari, Chara, Kalachakra."""
    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    def lord_name(pid):
        return PLANET_NAMES[pid] if 0 <= pid < len(PLANET_NAMES) else str(pid)

    def fmt_date(y, m, d):
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    result = {}

    # Vimshottari — running period (NOT birth balance tuple from get_vimsottari_dhasa_bhukthi[0])
    try:
        from app.dasha_vimshottari import birth_balance, running_ladder

        ladder = running_ladder(jd, place, depth=2)
        maha_row = ladder[0] if ladder else None
        antar_row = ladder[1] if len(ladder) > 1 else None
        result["vimshottari"] = {
            "maha": maha_row["lord"] if maha_row else None,
            "antara": antar_row["lord"] if antar_row else None,
            "mahaStart": maha_row["start"] if maha_row else None,
            "mahaEnd": maha_row["end"] if maha_row else None,
            "antaraStart": antar_row["start"] if antar_row else None,
            "antaraEnd": antar_row["end"] if antar_row else None,
            "balanceAtBirth": birth_balance(jd, place),
        }
    except Exception as e:
        print(f"[all_dashas] vimshottari failed: {type(e).__name__}: {e}", flush=True)
        result["vimshottari"] = None

    # Yogini Dasha
    try:
        from jhora.horoscope.dhasa.graha import yogini
        from jhora.panchanga.drik import Date as DrikDate
        y = yogini.get_dhasa_bhukthi(DrikDate(dt.year, dt.month, dt.day), (dt.hour, dt.minute, dt.second), place)
        cy = y[0] if y and len(y) > 0 else None
        result["yogini"] = {
            "maha": lord_name(cy[0][0]) if cy and len(cy) > 0 and isinstance(cy[0], (list, tuple)) else (str(cy[0]) if cy else None),
            "antara": lord_name(cy[0][1]) if cy and len(cy) > 0 and len(cy[0]) > 1 and isinstance(cy[0], (list, tuple)) else (str(cy[1]) if cy and len(cy) > 1 else None),
        }
    except Exception:
        result["yogini"] = None

    # Ashtottari Dasha — running period via get_running_dhasa_for_given_date
    try:
        result["ashtottari"] = _ashtottari_current(jd, place, lord_name)
    except Exception as e:
        print(f"[all_dashas] ashtottari failed: {type(e).__name__}: {e}", flush=True)
        result["ashtottari"] = None

    return {
        "birth_datetime": req.birth_datetime,
        "jd": jd,
        "dashas": result,
    }


# =====================================================================
# Varshaphala (Tajika / Solar Return) + Prashna
# =====================================================================

@app.post("/prashna")
def prashna(req: PrashnaRequest):
    """Horary chart — cast for the query moment (defaults to now UTC)."""
    from datetime import datetime, timezone

    dt_str = req.birth_datetime
    if not dt_str:
        dt_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return chart(BirthRequest(
        birth_datetime=dt_str,
        birth_lat=req.birth_lat,
        birth_lon=req.birth_lon,
        birth_tz=req.birth_tz,
        ayanamsa=req.ayanamsa,
        name=req.name or "Prashna",
    ))


VARSHA_MUNTHA_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


@app.post("/varshaphala")
def varshaphala(req: BirthRequest):
    """Solar Return (Varshaphala) chart for a given birth and query year.
    Returns the moment Sun returns to its natal sidereal degree position."""
    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    # Get natal Sun position
    natal_pos = positions(jd, place)
    natal_sun = next((p for p in natal_pos if p["planet"] == "Sun"), None)
    if not natal_sun:
        raise HTTPException(status_code=400, detail="Could not compute natal Sun")

    natal_sun_lon = natal_sun["longitude"]

    # Simple solar return: compute chart for same birth datetime each year
    # Full Varshaphala requires iterating to find exact solar return moment
    from datetime import datetime as dt_now
    query_year = dt_now.utcnow().year

    # Build chart for the birth time on the query year
    vd = dt.replace(year=query_year)
    vjd, _ = jd_place(vd, req.birth_lat, req.birth_lon, req.birth_tz)
    vpos = positions(vjd, place)
    vsun = next((p for p in vpos if p["planet"] == "Sun"), None)
    vmoon = next((p for p in vpos if p["planet"] == "Moon"), None)

    # Muntha = progressed ascendant (1 sign per year from birth lagna)
    birth_year = dt.year
    years_elapsed = query_year - birth_year
    birth_lagna = natal_pos[0].get("signIndex", 0) if natal_pos else 0  # ascendant is first
    muntha_sign = (birth_lagna + years_elapsed) % 12

    return {
        "birth_datetime": req.birth_datetime,
        "queryYear": query_year,
        "natalSun": {
            "longitude": natal_sun_lon,
            "rashi": natal_sun["rashi"],
            "degLabel": natal_sun["degLabel"],
        },
        "solarReturn": {
            "sun": {
                "longitude": vsun["longitude"] if vsun else None,
                "rashi": vsun["rashi"] if vsun else None,
            },
            "moon": {
                "rashi": vmoon["rashi"] if vmoon else None,
            },
        },
        "muntha": {
            "signIndex": muntha_sign,
            "sign": VARSHA_MUNTHA_SIGNS[muntha_sign],
            "yearsElapsed": years_elapsed,
            "note": "Muntha = progressed Lagna (1 sign per year). Its lord gives the annual theme.",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
