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

import hashlib
import json
import os
import re
import secrets
import time
from collections import defaultdict
from datetime import UTC, datetime
from functools import wraps
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from forecasting.contracts import ForecastClaim
from forecasting.service import process_forecast_claim, validation_error_detail
from jhora import const
from jhora.panchanga import drik
from prediction_policy import apply_product_claim_policy
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    ValidationError,
    field_validator,
    model_validator,
)
from research_engine.service import create_research_router
from research_engine.timeline import (
    EventDirection,
    MilestoneResolution,
    ResolutionStatus,
    SQLiteTimelineStore,
    TemporalResolution,
    TemporalTolerance,
    TimelineStoreConflict,
    TimelineStoreIntegrityError,
    TimelineWindow,
)
from research_engine.timeline.service import PersonTimelineService

from vedic_engine.verbalization import VerbalizationError

# Dedicated dasha systems self-register with the KnowledgeEngine on import.
from . import chara_dasha as chara_mod  # noqa: F401
from . import kaksha as kaksha_mod  # noqa: F401
from . import kalachakra as kala_mod  # noqa: F401
from .chart import build_chart_geometry
from .chart_svg import chart_svg
from .config import get_settings
from .ephem import (
    NAKSHATRAS,
    PLANET_NAMES,
    RASHIS,
    WEEKDAYS,
    ascendant,
    ayanamsa_context,
    ephemeris_provenance,
    ephemeris_runtime_provenance,
    jd_place,
    parse_dt,
    positions,
    set_ayanamsa,
)

settings = get_settings()

SHADBALA_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
SHADBALA_ROWS = [
    "sthana",
    "kaala",
    "dig",
    "cheshta",
    "naisargika",
    "drik",
    "total_shashtiamsa",
    "total_rupa",
    "strength_ratio",
]
TITHI_NAMES = [
    "Pratipada",
    "Dwitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dwadashi",
    "Trayodashi",
    "Chaturdashi",
    "Purnima/Amavasya",
]
YOGA_NAMES = [
    "Vishkambha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Shobhana",
    "Atiganda",
    "Sukarma",
    "Dhriti",
    "Shula",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyana",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
]
KARANA_NAMES = [
    "Kimstughna",
    "Bava",
    "Balava",
    "Kaulava",
    "Taitila",
    "Gara",
    "Vanija",
    "Vishti",
    "Shakuni",
    "Chatushpada",
    "Naga",
]

app = FastAPI(title="VedicAstro CVCE", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
research_router, clear_research_service_cache = create_research_router(settings)
# Extend with the router's already-prefixed APIRoutes. This preserves the
# historical `app.routes` contract used by product safety introspection while
# keeping the research plane additive.
app.router.routes.extend(research_router.routes)
app.router.add_event_handler("shutdown", clear_research_service_cache)

# The shallow liveness endpoint intentionally stays public so an orchestrator
# can decide whether to restart the service. All diagnostic and business
# endpoints require the portal's server-side token when auth is enabled.
_PUBLIC_PATHS = frozenset({"/health", "/graphinfo", "/favicon.ico"})
_SERVICE_TOKEN_HEADER = "x-cvce-service-token"


# --- rate limiting (per client IP) ----------------------------------------
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store[client_ip] if now - t < settings.RATE_LIMIT_WINDOW
        ]
        if len(_rate_limit_store[client_ip]) >= settings.RATE_LIMIT_REQUESTS:
            oldest = min(_rate_limit_store[client_ip])
            retry_after = max(
                1,
                int(settings.RATE_LIMIT_WINDOW - (now - oldest) + 0.999),
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(retry_after)},
            )
        _rate_limit_store[client_ip].append(now)
    return await call_next(request)


@app.middleware("http")
async def service_auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in _PUBLIC_PATHS:
        return await call_next(request)
    if request.url.path.startswith("/research/"):
        return await call_next(request)

    expected = settings.SERVICE_TOKEN
    auth_enabled = settings.SERVICE_AUTH_REQUIRED or bool(expected)
    if not auth_enabled:
        return await call_next(request)

    # A required service with no configured secret must not silently become
    # public. Keep the response generic and never log token material.
    if not expected:
        return JSONResponse(
            status_code=503,
            content={"detail": "Service authentication is unavailable"},
        )

    supplied = request.headers.get(_SERVICE_TOKEN_HEADER, "")
    if not secrets.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    return await call_next(request)


# --- request models -------------------------------------------------------
class TransitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datetime: str = Field(
        ..., description="Local civil datetime, ISO 8601 e.g. 2026-06-20T12:00:00"
    )
    lat: float = Field(..., ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(..., ge=-180, le=180, allow_inf_nan=False)
    tz_offset: float = Field(0.0, ge=-14, le=14, allow_inf_nan=False)
    ayanamsa: str = settings.DEFAULT_AYANAMSA

    @model_validator(mode="after")
    def validate_datetime(self):
        try:
            parse_dt(self.datetime)
        except (TypeError, ValueError) as exc:
            raise ValueError("datetime must be a valid local ISO 8601 value") from exc
        return self


class BirthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    birth_datetime: str
    birth_lat: float = Field(..., ge=-90, le=90, allow_inf_nan=False)
    birth_lon: float = Field(..., ge=-180, le=180, allow_inf_nan=False)
    birth_tz: float = Field(0.0, ge=-14, le=14, allow_inf_nan=False)
    ayanamsa: str = settings.DEFAULT_AYANAMSA
    name: str | None = None

    @field_validator("birth_datetime")
    @classmethod
    def validate_birth_datetime(cls, value: str) -> str:
        """Require a real, timezone-free local civil second.

        Birth coordinates carry their UTC offset separately in ``birth_tz``;
        accepting an offset here would make the instant ambiguous.  Validate
        at the request boundary so malformed and impossible calendar values
        are reported as 422 rather than escaping from endpoint calculations.
        """
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value):
            raise ValueError(
                "birth_datetime must be a local ISO civil datetime in "
                "YYYY-MM-DDTHH:MM:SS format"
            )
        try:
            datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except ValueError as exc:
            raise ValueError("birth_datetime must be a valid local civil datetime") from exc
        return value


class DashaDeepJdRequest(BaseModel):
    """JD-based comprehensive dasha analysis (POST /dasha/deep).

    Callers supply precomputed Julian Days plus sidereal Moon longitude and
    Lagna index so the portal/muhurta stack need not re-send place coordinates.
    """

    model_config = ConfigDict(extra="forbid")

    birth_jd: float = Field(..., allow_inf_nan=False, description="Birth Julian Day (UT)")
    query_jd: float = Field(..., allow_inf_nan=False, description="Query Julian Day (UT)")
    moon_lon_sidereal: float = Field(
        ..., ge=0.0, lt=360.0, allow_inf_nan=False, description="Sidereal Moon longitude 0–360°"
    )
    lagna_idx: int = Field(..., ge=0, le=11, description="Lagna rashi index 0=Aries … 11=Pisces")


class AshtakavargaRequest(BaseModel):
    """True PyJHora BAV/SAV board + Kaksha grade (POST /ashtakavarga).

    Body (B-16.12):
      natal_sign: {planet: sign_idx|name, ...} for Sun..Saturn (+ optional Lagna)
      lagna_sign: sign_idx | rashi name | {sign|signIndex|index: ...}

    Optional transit snapshot fields (for moon_transit_bindus + kaksha grade):
      moon_transit_sign, saturn_transit_sign, saturn_deg_in_sign, kaksha_planet
    """

    model_config = ConfigDict(extra="forbid")

    natal_sign: dict = Field(
        ...,
        description="Natal sign indices (0=Aries) or rashi names keyed by planet",
    )
    lagna_sign: object = Field(
        ...,
        description="Lagna as int 0-11, rashi name, or dict with sign/signIndex",
    )
    moon_transit_sign: int | None = Field(
        default=None, ge=0, le=11, description="Transit Moon sign idx for moon_transit_bindus"
    )
    saturn_transit_sign: int | None = Field(
        default=None, ge=0, le=11, description="Transit Saturn sign idx for Kaksha grade"
    )
    saturn_deg_in_sign: float | None = Field(
        default=None, ge=0.0, lt=30.0, allow_inf_nan=False,
        description="Saturn degree-in-sign for active Kaksha lord (0–30)",
    )
    kaksha_planet: str = Field(
        default="Saturn",
        description="Planet whose BAV row the active Kaksha lord is checked against",
    )


class TimelineQueryRequest(BirthRequest):
    subject_id: str = Field(min_length=1, max_length=256)
    query_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class TimelineToleranceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    before_seconds: int = Field(default=0, ge=0)
    after_seconds: int = Field(default=0, ge=0)
    native_label: str = Field(min_length=1, max_length=500)


class TimelineWindowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_at: datetime
    peak_at: datetime | None = None
    end_at: datetime
    native_resolution: TemporalResolution
    native_resolution_label: str = Field(min_length=1, max_length=200)
    tolerance: TimelineToleranceRequest

    @model_validator(mode="after")
    def validate_timezone(self):
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("timeline timestamps must include a timezone")
        if self.peak_at is not None and self.peak_at.tzinfo is None:
            raise ValueError("peak_at must include a timezone")
        return self

    def to_contract(self) -> TimelineWindow:
        return TimelineWindow(
            start_at=self.start_at,
            peak_at=self.peak_at,
            end_at=self.end_at,
            native_resolution=self.native_resolution,
            native_resolution_label=self.native_resolution_label,
            tolerance=TemporalTolerance(
                before_seconds=self.tolerance.before_seconds,
                after_seconds=self.tolerance.after_seconds,
                native_label=self.tolerance.native_label,
            ),
        )


class ObservedTimelineEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    canonical_event_id: str = Field(min_length=1, max_length=256)
    original_label: str | None = Field(default=None, max_length=500)
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10_000)
    direction: EventDirection = EventDirection.NOT_APPLICABLE
    magnitude: object | None = None
    window: TimelineWindowRequest
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    supersedes_milestone_id: str | None = Field(default=None, max_length=256)

    @field_validator("recorded_at")
    @classmethod
    def recorded_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("recorded_at must include a timezone")
        return value


class TimelineResolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str = Field(min_length=1, max_length=256)
    resolution_id: str = Field(min_length=1, max_length=256)
    observed_milestone_id: str | None = Field(default=None, max_length=256)
    status: ResolutionStatus
    actual_window: TimelineWindowRequest | None = None
    certainty: str = Field(min_length=1, max_length=500)
    resolver_id: str = Field(min_length=1, max_length=256)
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: tuple[str, ...] = ()
    supersedes_resolution_id: str | None = Field(default=None, max_length=256)
    match_criteria: dict[str, JsonValue] | None = None

    @field_validator("resolved_at")
    @classmethod
    def resolved_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("resolved_at must include a timezone")
        return value


class PrashnaRequest(BaseModel):
    """Horary chart — defaults to current UTC moment."""

    birth_lat: float
    birth_lon: float
    birth_tz: float = 0.0
    birth_datetime: str | None = None
    ayanamsa: str = settings.DEFAULT_AYANAMSA
    name: str | None = "Prashna"


_timeline_service: PersonTimelineService | None = None
_timeline_service_database_path: str | None = None


def _clear_timeline_service_cache() -> None:
    global _timeline_service, _timeline_service_database_path
    if _timeline_service is not None:
        _timeline_service.close()
    _timeline_service = None
    _timeline_service_database_path = None


def _get_timeline_service(*, require_writes: bool = False) -> PersonTimelineService:
    global _timeline_service, _timeline_service_database_path
    path = str(settings.TIMELINE_DB_PATH).strip()
    if require_writes and (not settings.TIMELINE_WRITES_ENABLED or not path):
        raise HTTPException(
            status_code=503,
            detail="Person Timeline durable writes are unavailable",
        )
    if _timeline_service is None or _timeline_service_database_path != path:
        _clear_timeline_service_cache()
        try:
            store = SQLiteTimelineStore(path) if path else None
            _timeline_service = PersonTimelineService(store)
        except (OSError, ValueError, TimelineStoreIntegrityError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Person Timeline durable storage is unavailable",
            ) from exc
        _timeline_service_database_path = path
    return _timeline_service


app.router.add_event_handler("shutdown", _clear_timeline_service_cache)


def _timeline_query_kwargs(req: TimelineQueryRequest) -> dict:
    return {
        "subject_id": req.subject_id,
        "birth_datetime": req.birth_datetime,
        "birth_lat": req.birth_lat,
        "birth_lon": req.birth_lon,
        "birth_tz": req.birth_tz,
        "ayanamsa": req.ayanamsa,
        "name": req.name,
        "query_date": req.query_date,
    }


# --- panchanga helper (shared by /panchanga and /chart) -------------------
def _panchanga(jd: float, place) -> dict:
    def label(arr, names, base=1):
        n = int(arr[0])
        idx = (n - base) % len(names)
        return {
            "number": n,
            "name": names[idx],
            "start": round(float(arr[1]), 4) if len(arr) > 1 else None,
            "end": round(float(arr[2]), 4) if len(arr) > 2 else None,
        }

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
        "tithi": {
            "number": tnum,
            "name": TITHI_NAMES[(tnum - 1) % 15],
            "paksha": paksha,
            "start": round(float(t[1]), 4) if len(t) > 1 else None,
            "end": round(float(t[2]), 4) if len(t) > 2 else None,
        },
        "nakshatra": {
            "number": nnum,
            "name": NAKSHATRAS[(nnum - 1) % 27],
            "pada": int(nk[1]) if len(nk) > 1 else None,
            "start": round(float(nk[2]), 4) if len(nk) > 2 else None,
            "end": round(float(nk[3]), 4) if len(nk) > 3 else None,
        },
        "yoga": label(yg, YOGA_NAMES),
        "karana": {
            "number": int(kr[0]),
            "name": _canonical_karana_name(int(kr[0])),
            "start": round(float(kr[1]), 4) if len(kr) > 1 else None,
            "end": round(float(kr[2]), 4) if len(kr) > 2 else None,
        },
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


_PERSONALISED_PREDICTION_PATHS = frozenset(
    {
        "/predict",
        "/dasha-predict",
        "/dasha-predict-yogini",
        "/fructification",
        "/dasha-series",
        "/gochar",
        "/report/facts",
    }
)


def _product_safe_prediction_response(payload):
    """Apply fail-safe T3 policy only at a personalised product boundary."""
    safe = apply_product_claim_policy(payload)
    if not isinstance(safe.value, dict):
        return safe.value

    output = safe.value
    prior = output.get("claim_safety") if isinstance(output.get("claim_safety"), dict) else {}
    prior_count = prior.get("blocked_count", 0)
    prior_categories = prior.get("blocked_categories", [])
    blocked_count = (prior_count if isinstance(prior_count, int) else 0) + safe.blocked_count
    categories = sorted(
        set(prior_categories if isinstance(prior_categories, list) else [])
        | set(safe.blocked_categories)
    )
    output["claim_safety"] = {
        "policy": "personalised-t3-v1",
        "status": "filtered" if blocked_count else "passed",
        "blocked_count": blocked_count,
        "blocked_categories": categories,
    }
    return output


def _product_claim_safe(fn):
    """Mark and enforce a personalised prediction endpoint."""
    @wraps(fn)
    def wrapped(*args, **kwargs):
        return _product_safe_prediction_response(fn(*args, **kwargs))

    wrapped._product_claim_policy = "personalised-t3-v1"
    return wrapped


# --- endpoints ------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "engine": "PyJHora",
        "version": getattr(const, "_APP_VERSION", "4.8.7"),
        "ayanamsa": settings.DEFAULT_AYANAMSA,
        "vargas": settings.VARGAS,
    }


@app.get("/graphinfo")
def graphinfo():
    """B-56 migration checklist §5 step 6 — which knowledge-graph snapshot/backend
    is this container actually running, and is graph.db really present in the
    deployed bundle? (Vercel Python functions don't auto-trace file references
    the way Node imports do — includeFiles in vercel.json is required, and this
    endpoint is the way to prove it worked in a real deploy, not just locally.)
    """
    import os as _os

    graph_source = _os.environ.get("GRAPH_SOURCE", "supabase").strip().lower()
    db_path = _os.environ.get(
        "GRAPH_DB_PATH",
        _os.path.join(_os.path.dirname(__file__), "..", "knowledge_engine", "graph.db"),
    )
    db_path = _os.path.abspath(db_path)
    json_path = _os.path.abspath(
        _os.path.join(_os.path.dirname(__file__), "..", "graph_rag", "graph.json")
    )

    info = {
        "graph_source_env": graph_source,
        "graph_db": {
            "path": db_path,
            "present": _os.path.exists(db_path),
            "size_bytes": _os.path.getsize(db_path) if _os.path.exists(db_path) else None,
        },
        "graph_json": {
            "path": json_path,
            "present": _os.path.exists(json_path),
            "size_bytes": _os.path.getsize(json_path) if _os.path.exists(json_path) else None,
        },
    }

    ke = _ensure_knowledge_engine()
    if ke is not None:
        try:
            info["active_backend"] = {
                "version": ke.current_version.version if ke.current_version else None,
                "node_count": ke.current_version.node_count if ke.current_version else None,
                "link_count": ke.current_version.link_count if ke.current_version else None,
            }
        except Exception as exc:
            info["active_backend"] = {"error": str(exc)}
    else:
        info["active_backend"] = None

    return info


def _mem_snapshot() -> dict:
    """Current RSS + cgroup limit (Fly/Linux). Falls back gracefully off-Linux."""
    import os as _os

    rss_mb = limit_mb = None
    # Current RSS: cgroup v2 memory.current, else /proc/self/status VmRSS.
    try:
        with open("/sys/fs/cgroup/memory.current") as f:
            rss_mb = int(f.read().strip()) / (1024 * 1024)
    except Exception:
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        rss_mb = int(line.split()[1]) / 1024
                        break
        except Exception:
            try:
                import resource

                ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                rss_mb = ru / 1024 if _os.uname().sysname != "Darwin" else ru / (1024 * 1024)
            except Exception:
                pass
    # Limit: cgroup memory.max if set, else the VM's total RAM (Fly enforces
    # the machine size at the microVM level, so memory.max is often "max" and
    # MemTotal IS the real ceiling).
    try:
        with open("/sys/fs/cgroup/memory.max") as f:
            raw = f.read().strip()
            if raw != "max":
                limit_mb = int(raw) / (1024 * 1024)
    except Exception:
        pass
    if limit_mb is None:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        limit_mb = int(line.split()[1]) / 1024
                        break
        except Exception:
            pass
    headroom = None
    if rss_mb is not None and limit_mb:
        headroom = round(100 * (1 - rss_mb / limit_mb), 1)
    return {
        "rss_mb": round(rss_mb, 1) if rss_mb is not None else None,
        "limit_mb": round(limit_mb, 1) if limit_mb else None,
        "headroom_pct": headroom,
    }


@app.get("/health/deep")
def health_deep():
    """Active per-subsystem health — the observability the shallow /health
    lacks (a port-open check stayed green all while KnowledgeEngine was dead).
    Each check actually exercises its subsystem. Overall status:
      down     — a Tier-0 check (core PyJHora compute) failed → product broken
      degraded — a non-core check (KE / Supabase / memory) failed → still usable
      healthy  — all green
    """
    import time as _time

    checks = []

    def _check(name, tier, fn):
        t0 = _time.perf_counter()
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {str(e)[:160]}"
        checks.append(
            {"name": name, "tier": tier, "ok": bool(ok), "detail": detail,
             "ms": round((_time.perf_counter() - t0) * 1000, 1)}
        )

    # Tier 0 — core computation (must never fail)
    def _ephem():
        dt = parse_dt("1975-04-22T19:15:00")
        jd, place = jd_place(dt, 12.2979, 76.6393, 5.5)
        asc = ascendant(jd, place)
        # golden invariant: Mohan's Lagna is Libra
        return asc.get("rashi") == "Libra", f"Lagna={asc.get('rashi')}"

    _check("pyjhora_compute", 0, _ephem)

    # Tier 1 — KnowledgeEngine + Supabase + vectors
    def _ke():
        ke = _ensure_knowledge_engine()
        if ke is None:
            return False, "engine None"
        healthy = ke.is_knowledge_healthy()
        vec = ke.vector_search_available()
        return healthy, f"healthy={healthy} vector={vec} version={getattr(ke,'current_version',None) and ke.current_version.version}"

    _check("knowledge_engine", 1, _ke)

    def _supabase():
        ke = _ensure_knowledge_engine()
        store = getattr(ke, "store", None)
        if store is None or not hasattr(store, "health_check"):
            return False, "no supabase store (file-based)"
        return bool(store.health_check()), "graph_nodes reachable"

    _check("supabase", 1, _supabase)

    # Tier 1 — resource headroom (OOM early-warning)
    mem = _mem_snapshot()

    def _memory():
        hr = mem.get("headroom_pct")
        if hr is None:
            return True, f"rss={mem.get('rss_mb')}MB (limit unknown)"
        return hr > 12, f"rss={mem.get('rss_mb')}MB / {mem.get('limit_mb')}MB, headroom={hr}%"

    _check("memory_headroom", 1, _memory)

    tier0_down = any(not c["ok"] for c in checks if c["tier"] == 0)
    tier1_down = any(not c["ok"] for c in checks if c["tier"] == 1)
    status = "down" if tier0_down else ("degraded" if tier1_down else "healthy")

    from datetime import datetime as _dt

    return {
        "status": status,
        "checks": checks,
        "memory": mem,
        "timestamp": _dt.now(UTC).isoformat(),
    }


@app.get("/version")
def version():
    """Lightweight probe for KnowledgeEngine corpus version (used by portal proxy + clients)."""
    return {"ke_version": _ke_version(), "service": "cvce"}


@app.post("/v2/forecast/brief", include_in_schema=False)
@app.post("/v2/forecasts")
async def forecast_brief_v2(request: Request):
    """Validate one canonical event claim and render its safe product brief.

    This boundary intentionally has no legacy-output adapter. Callers must
    provide a complete event-specific ForecastClaim or receive a validation
    failure; broad legacy scores and prose are never promoted into claims.
    """

    mode = settings.FORECAST_V2_MODE
    if mode == "off":
        raise HTTPException(status_code=404, detail="Forecast v2 is disabled")
    if mode == "on" and not settings.VERBALIZATION_V2:
        raise HTTPException(status_code=404, detail="Forecast v2 verbalization is disabled")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    try:
        claim = ForecastClaim.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=validation_error_detail(exc)) from exc

    try:
        result = process_forecast_claim(
            claim,
            mode=mode,
            verbalization_enabled=settings.VERBALIZATION_V2,
            ledger_write_enabled=settings.FORECAST_LEDGER_WRITE,
        )
    except VerbalizationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if mode == "shadow":
        return JSONResponse(status_code=202, content=result.model_dump(mode="json"))
    return result


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.post("/positions")
def positions_endpoint(req: TransitRequest):
    set_ayanamsa(req.ayanamsa)
    jd, place = jd_place(parse_dt(req.datetime), req.lat, req.lon, req.tz_offset)
    return {
        "datetime": req.datetime,
        "jd": jd,
        "ayanamsa": req.ayanamsa,
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


@app.post("/timeline/query")
def timeline_query(req: TimelineQueryRequest):
    """Return a personal timeline without promoting legacy output to forecasts."""

    try:
        result = _get_timeline_service().query(**_timeline_query_kwargs(req))
        result.pop("_details", None)
        return result
    except HTTPException:
        raise
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid timeline calculation input") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Timeline calculation failed") from exc


@app.post("/timeline/milestones/{milestone_id}/detail")
def timeline_milestone_detail(milestone_id: str, req: TimelineQueryRequest):
    """Replay a milestone with native timing, evidence and calculation identity."""

    try:
        return _get_timeline_service().detail(
            milestone_id,
            **_timeline_query_kwargs(req),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Timeline milestone not found") from exc
    except HTTPException:
        raise
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid timeline calculation input") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Timeline detail failed") from exc


@app.post("/timeline/events", status_code=201)
def capture_timeline_event(req: ObservedTimelineEventRequest):
    """Append a person-entered event; corrections create successor milestones."""

    try:
        return _get_timeline_service(require_writes=True).capture_observed_event(
            subject_id=req.subject_id,
            event_id=req.event_id,
            canonical_event_id=req.canonical_event_id,
            original_label=req.original_label or req.title,
            title=req.title,
            description=req.description,
            direction=req.direction,
            magnitude=req.magnitude,
            window=req.window.to_contract(),
            recorded_at=req.recorded_at,
            supersedes_milestone_id=req.supersedes_milestone_id,
        )
    except TimelineStoreConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid observed event") from exc
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/timeline/milestones/{milestone_id}/resolutions", status_code=201)
def append_timeline_resolution(milestone_id: str, req: TimelineResolutionRequest):
    """Append an outcome assessment while leaving the sealed forecast untouched."""

    try:
        resolution = MilestoneResolution(
            resolution_id=req.resolution_id,
            prediction_milestone_id=milestone_id,
            observed_milestone_id=req.observed_milestone_id,
            status=req.status,
            actual_window=req.actual_window.to_contract() if req.actual_window else None,
            certainty=req.certainty,
            resolver_id=req.resolver_id,
            resolved_at=req.resolved_at,
            notes=req.notes,
            supersedes_resolution_id=req.supersedes_resolution_id,
            match_criteria=req.match_criteria,
        )
        return _get_timeline_service(require_writes=True).append_resolution(
            subject_id=req.subject_id,
            resolution=resolution,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=validation_error_detail(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Prediction milestone not found") from exc
    except TimelineStoreConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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

    geometry, gerr = _guard(lambda: build_chart_geometry(jd, place, req.ayanamsa, settings.VARGAS))
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
    out = {**out, "ke_version": _ke_version()}

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
    out["ke_version"] = _ke_version()
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
        rows.append(
            {
                "planet": name,
                "pyjhora": a,
                "jyotishganit": b,
                "deltaDeg": round(d, 5) if d is not None else None,
            }
        )
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
        "datetime": req.datetime,
        "comparison": rows,
        "ayanamsaDeltaDeg": offset,
        "flagged": flagged,
        "note": (
            "Rahu/Ketu excluded from offset/flags: PyJHora uses the mean "
            "lunar node, jyotishganit the true node (~1-2deg difference is expected)."
        ),
        "jyotishganitError": jg_error,
        "ke_version": _ke_version(),
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

# Shared vedic-knowledge package — graph path + version gate (B-16 Phase 2)
try:
    from .graph_version_gate import enforce_at_startup as _graph_version_gate

    _GRAPH_VERSION_STATUS = _graph_version_gate()
except Exception as _gve:
    # Only hard-fail when GRAPH_VERSION is set (mismatch) or GRAPH_VERSION_REQUIRED=1
    import os as _os

    if _os.environ.get("GRAPH_VERSION") or _os.environ.get("GRAPH_VERSION_REQUIRED", "").lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        raise
    _GRAPH_VERSION_STATUS = {"ok": False, "message": str(_gve)}

# Knowledge layer — prefer KnowledgeEngine safe access. GraphRAG kept only for
# specialized stats providers (deepseek/gemini etc) that are not yet under KE.
try:
    try:
        from vedic_knowledge import get_safe_graph, get_prediction_enhancer, is_knowledge_healthy
    except ImportError:
        from knowledge_engine.integration import get_safe_graph, get_prediction_enhancer, is_knowledge_healthy

    _enhancer = get_prediction_enhancer()
    _GRAPH_AVAILABLE = True
except Exception:
    _GRAPH_AVAILABLE = False
    _enhancer = None

# Legacy named imports for the specific LLM graph stat helpers (these are narrow providers)
try:
    from graph_rag.graph_deepseek import deepseek_graph_stats
    from graph_rag.graph_gemini import gemini_graph_stats
    from graph_rag.graph_glm import glm_graph_stats
    from graph_rag.graph_grok import grok_graph_available, grok_graph_stats
except Exception:
    def deepseek_graph_stats(): return None
    def gemini_graph_stats(): return None
    def glm_graph_stats(): return None
    def grok_graph_stats(): return None
    def grok_graph_available() -> bool: return False

def graph_rules_enabled() -> bool:
    try:
        from knowledge_engine.integration import is_knowledge_healthy
        return is_knowledge_healthy()
    except Exception:
        return False


# New central KnowledgeEngine (P0 active work)
try:
    try:
        from vedic_knowledge import get_knowledge_engine
    except ImportError:
        from knowledge_engine import get_knowledge_engine

    _knowledge_engine = get_knowledge_engine()
except Exception:
    _knowledge_engine = None


def _ensure_knowledge_engine():
    """Lazily (re)initialize the KnowledgeEngine. The import-time attempt above
    can fail on a transient at container boot (outbound network not yet ready
    to reach Supabase); a swallowed failure there must NOT permanently disable
    the knowledge endpoints — retry on first real use."""
    global _knowledge_engine
    if _knowledge_engine is None:
        try:
            try:
                from vedic_knowledge import get_knowledge_engine as _gke
            except ImportError:
                from knowledge_engine import get_knowledge_engine as _gke

            _knowledge_engine = _gke()
        except Exception:
            _knowledge_engine = None
    return _knowledge_engine

# KnowledgeEngine consumer registration (all 9 engines register via side-effect on import)
try:
    from vedic_engine.prediction import kp_system as _kp_engine  # noqa: F401
    from vedic_engine.prediction import prashna as _prashna_engine  # noqa: F401
    from vedic_engine.core import panchanga as _panchanga_engine  # noqa: F401
    from vedic_engine.prediction import dasha as _dasha_engine  # noqa: F401
    from vedic_engine.prediction import gochar as _gochar_engine  # noqa: F401
    from vedic_engine.prediction import yoga as _yoga_engine  # noqa: F401
    from vedic_engine.synthesis import engine as _synthesis_engine  # registers muhurta  # noqa: F401
    from vedic_engine.prediction import ashtakavarga as _ashtakavarga_engine  # noqa: F401
    import app.report_facts as _report_engine  # noqa: F401  # registers "report"
except Exception:
    pass

# Explicit registration at startup to guarantee all 9 (side-effect + explicit)
try:
    ke = get_knowledge_engine()
    for name in ("kp_system", "prashna", "panchanga", "dasha", "gochar", "yoga", "muhurta", "ashtakavarga", "report"):
        if name not in ke.registry.registered_names():
            ke.register_engine(name)
except Exception:
    pass

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


def _ke_version() -> str:
    """Return current KnowledgeEngine corpus version (for surfacing in responses)."""
    try:
        from knowledge_engine.integration import get_knowledge_engine

        ke = get_knowledge_engine()
        if getattr(ke, "current_version", None) and ke.current_version:
            return ke.current_version.version
        try:
            st = ke.get_stats() or {}
            if isinstance(st, dict) and "version" in st:
                return st["version"]
        except Exception:
            pass
        return "unknown"
    except Exception:
        return "unknown"


@app.get("/")
def index():
    """Browser-friendly landing — CVCE is an API; use the portal for the UI."""
    graph_rag = None
    if _GRAPH_AVAILABLE and _enhancer is not None:
        try:
            try:
                from vedic_knowledge import get_safe_transit_rules as active_transit_rules
            except ImportError:
                from knowledge_engine.integration import get_safe_transit_rules as active_transit_rules

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
            "dasha_deep_jd": "POST /dasha/deep",
            "ashtakavarga": "POST /ashtakavarga",
            "person_timeline": "POST /timeline/query",
            "timeline_detail": "POST /timeline/milestones/{milestone_id}/detail",
            "timeline_event": "POST /timeline/events",
            "timeline_resolution": "POST /timeline/milestones/{milestone_id}/resolutions",
            "kalachakra_deep": "POST /kalachakra-deep",
            "kp_system": "POST /kp-system",
            "varshaphala": "POST /varshaphala",
            "orchestrate": "POST /orchestrate",
            "knowledge_transit": "GET /knowledge/transit?planet=Sun&house=3",
            "docs": "GET /docs",
        },
        "example": {
            "chart": "curl -s https://vedicastro-cvce.fly.dev/chart -H 'content-type: application/json' "
            '-d \'{"birth_datetime":"1975-04-22T19:15:00","birth_lat":12.2958,'
            '"birth_lon":76.6394,"birth_tz":5.5,"name":"Mohan"}\'',
            "prashna": "curl -s https://vedicastro-cvce.fly.dev/prashna -H 'content-type: application/json' "
            '-d \'{"birth_lat":12.97,"birth_lon":77.59,"birth_tz":5.5}\'',
        },
    }
    return JSONResponse(payload)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: str = Field(..., pattern=r"^\d{2}:\d{2}(?::\d{2})?$")
    lat: float = Field(..., ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(..., ge=-180, le=180, allow_inf_nan=False)
    tz: float = Field(..., ge=-14, le=14, allow_inf_nan=False)
    janma_rashi: str | None = None
    janma_nakshatra: str | None = None
    birth_date: str | None = None
    birth_time: str | None = None
    birth_lat: float | None = Field(None, ge=-90, le=90, allow_inf_nan=False)
    birth_lon: float | None = Field(None, ge=-180, le=180, allow_inf_nan=False)
    birth_tz: float | None = Field(None, ge=-14, le=14, allow_inf_nan=False)
    birth_moon_lon: float | None = Field(None, ge=0, lt=360, allow_inf_nan=False)
    natal_signs: dict | None = None

    @model_validator(mode="after")
    def validate_date_time(self):
        try:
            datetime.fromisoformat(f"{self.date}T{self.time}")
        except ValueError as exc:
            raise ValueError("date and time must form a valid local civil datetime") from exc
        return self


@app.post("/predict")
@_product_claim_safe
def predict(req: PredictionRequest):
    if not _ENGINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Prediction engine not available")
    r = _predictor.predict(
        date=req.date or None,
        time=req.time,
        lat=req.lat,
        lon=req.lon,
        tz=req.tz,
        janma_rashi=req.janma_rashi,
        janma_nakshatra=req.janma_nakshatra,
        birth_date=req.birth_date,
        birth_time=req.birth_time,
        birth_lat=req.birth_lat,
        birth_lon=req.birth_lon,
        birth_tz=req.birth_tz,
        birth_moon_lon=req.birth_moon_lon,
        natal_sign=req.natal_signs,
    )
    panch, gochar, dasha = r.panchanga, r.gochar, r.dasha
    return {
        "date": r.query_date,
        "time": r.query_time,
        "overall_verdict": r.overall_verdict,
        "overall_score": r.overall_score,
        "summary": r.summary,
        "panchanga": {
            "tithi": {
                "name": panch.tithi_name,
                "paksha": panch.tithi_paksha,
                "num": panch.tithi_num,
                "group": panch.tithi_group,
                "lord": getattr(panch, "tithi_lord", None),
                "verdict": panch.tithi_verdict,
            }
            if panch
            else None,
            "vaar": panch.weekday if panch else None,
            "nakshatra": {
                "name": panch.nakshatra,
                "nature": panch.nakshatra_nature,
                "lord": panch.nakshatra_lord,
                "verdict": panch.nakshatra_verdict,
            }
            if panch
            else None,
            "yoga": {
                "name": panch.yoga_name,
                "nature": panch.yoga_nature,
                "verdict": panch.yoga_verdict,
            }
            if panch
            else None,
            "karana": {"name": panch.karana_name, "verdict": panch.karana_verdict}
            if panch
            else None,
            "sunrise": panch.sunrise if panch else None,
            "sunset": panch.sunset if panch else None,
        },
        "gochar": {
            "overall_verdict": gochar.overall_verdict,
            "overall_score": gochar.overall_score,
            "synthesis": gochar.synthesis,
            "planets": [
                {
                    "planet": p.planet,
                    "rashi": p.rashi,
                    "nakshatra": p.nakshatra,
                    "house_from_janma": p.house_from_janma,
                    "verdict": p.verdict,
                    "house_quality": p.house_quality,
                    "score": p.score,
                    "effects": p.effects,
                    "retrograde": p.retrograde,
                    "vedha": p.vedha_active,
                    "combustion": p.combustion,
                    "latta": p.latta,
                }
                for p in gochar.planet_predictions
            ]
            if gochar
            else [],
            "moorthy": gochar.moorthy if gochar else None,
            "sade_sati": gochar.sade_sati if gochar else None,
            "kantaka_shani": gochar.kantaka_shani if gochar else None,
            "ashtama_shani": gochar.ashtama_shani if gochar else None,
            "tara_balam": gochar.tara_balam if gochar else None,
        }
        if gochar
        else None,
        "dasha": {
            "mahadasha": {
                "planet": dasha.current_mahadasha.planet,
                "start": dasha.current_mahadasha.start_date,
                "end": dasha.current_mahadasha.end_date,
            }
            if dasha and dasha.current_mahadasha
            else None,
            "antardasha": {
                "planet": dasha.current_antardasha.planet,
                "start": dasha.current_antardasha.start_date,
                "end": dasha.current_antardasha.end_date,
            }
            if dasha and dasha.current_antardasha
            else None,
            "score": dasha.dasha_score if dasha else 0,
            "summary": dasha.summary if dasha else "",
            "chapter_citation": getattr(dasha, "chapter_citation", None),
            "hierarchy_path": getattr(dasha, "hierarchy_path", None),
        }
        if dasha
        else None,
        "yogas": [
            {
                "name": y.name,
                "category": y.category,
                "description": y.description,
                "benefic": y.benefic,
                "planets": y.planets_involved,
                "source": getattr(y, "source", None),
                "chapter_citation": getattr(y, "chapter_citation", None),
                "hierarchy_path": getattr(y, "hierarchy_path", None),
            }
            for y in (r.yogas or [])
        ],
        "ashtakavarga": {
            "total_sav": r.ashtakavarga.total_sav,
            "moon_transit_bindus": r.ashtakavarga.moon_transit_bindus,
            "moon_transit_verdict": r.ashtakavarga.moon_transit_verdict,
            "moon_transit_band": r.ashtakavarga.moon_transit_band,
            "sav": r.ashtakavarga.sav,
            "bav": r.ashtakavarga.bav,
            "planet_totals": r.ashtakavarga.planet_totals,
            "lagna_sign_idx": r.ashtakavarga.lagna_sign_idx,
            "transit_sav": {
                p: {"sign": d["sign"], "bindus": d["bindus"], "band": d["band"]}
                for p, d in r.ashtakavarga.transit_sav.items()
            }
            if r.ashtakavarga.transit_sav
            else {},
            "chapter_citation": getattr(r.ashtakavarga, "chapter_citation", None),
            "hierarchy_path": getattr(r.ashtakavarga, "hierarchy_path", None),
        }
        if r.ashtakavarga
        else None,
        "muhurta_yogas": r.muhurta_yogas,
        "warnings": r.warnings,
        "transit_summary": getattr(r, "transit_summary", ""),
        "rules_source": "graph" if (_GRAPH_AVAILABLE and graph_rules_enabled()) else "hardcoded",
        "graph_enhancements": _graph_enhance(r, req) if _GRAPH_AVAILABLE else None,
    }


def _enhancer_graph_stats() -> dict | None:
    """Return graph stats from PredictionEnhancer (GraphRAG or raw dict fallback)."""
    if not _GRAPH_AVAILABLE or _enhancer is None:
        return None
    graph = getattr(_enhancer, "graph", None)
    if graph is None:
        return None
    stats = getattr(graph, "stats", None)
    if stats is not None:
        return stats
    if isinstance(graph, dict):
        return {
            "nodes": len(graph.get("nodes", [])),
            "links": len(graph.get("links", [])),
        }
    return None


@app.get("/predict/health")
def predict_health():
    try:
        from vedic_knowledge import get_safe_transit_rules as active_transit_rules
    except ImportError:
        from knowledge_engine.integration import get_safe_transit_rules as active_transit_rules
    from knowledge_engine.integration import is_knowledge_healthy as graph_rules_enabled

    graph_rules = active_transit_rules()
    grok_stats = grok_graph_stats()
    gemini_stats = gemini_graph_stats()
    glm_stats = glm_graph_stats()
    deepseek_stats = deepseek_graph_stats()
    ke = _knowledge_engine
    ke_health = ke.health() if ke else None

    return {
        "engine": "vedic-prediction-engine",
        "version": _predictor.version if _ENGINE_AVAILABLE else "0.0.0",
        "available": _ENGINE_AVAILABLE,
        "knowledge_engine": ke_health,
        "graph_rag": {
            "available": _GRAPH_AVAILABLE,
            "rules_source": "graph" if graph_rules else "hardcoded",
            "graph_as_rules_env": graph_rules_enabled(),
            "stats": _enhancer_graph_stats(),
        },
        "graph_rag_grok": grok_stats,
        "graph_rag_gemini": gemini_stats,
        "graph_rag_glm": glm_stats,
        "graph_rag_deepseek": deepseek_stats,
        "rules_engine": {"available": _RULES_AVAILABLE},
    }


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
            "promote_when": "beats_production is true and quality spot-check passes",
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
    planet: str | None = None
    house: int | None = None
    janma_nak: str | None = None
    transit_nak: str | None = None
    janma_rashi: str | None = None
    tithi_num: int | None = None
    nakshatra: str | None = None
    sign: str | None = None
    degree: float | None = None
    yoga_name: str | None = None
    positions: dict | None = None
    query: dict | None = None
    natal_sign: dict | None = None


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
    return {
        "available": _ORCH_AVAILABLE,
        "engines_registered": len(orchestrator._engines) if _ORCH_AVAILABLE else 0,
    }


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
    name: str | None = None


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


@app.post("/dasha-deep-yogini")
def dasha_deep_yogini(req: BirthRequest):
    """Yogini Mahadasha tree with running ladder."""
    from app.dasha_other import yogini_deep_payload

    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)
    return yogini_deep_payload(jd, place, dt)


@app.post("/dasha-deep-ashtottari")
def dasha_deep_ashtottari(req: BirthRequest):
    """Ashtottari Mahadasha tree with running ladder. Always computed; applicability shown as note."""
    from app.dasha_other import ashtottari_deep_payload

    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)
    return ashtottari_deep_payload(jd, place)


@app.post("/dasha-deep")
def dasha_deep(req: BirthRequest):
    """Vimshottari to 5 levels + shubh/ashubh verdict on Maha and Antar nodes."""
    from app.chart import build_chart_geometry
    from app.dasha_vimshottari import dasha_deep_payload
    from vedic_engine.synthesis.dasha_analyzer import DashaImpactAnalyzer

    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    payload = dasha_deep_payload(jd, place, max_level=5)

    # Annotate levels 1 (Maha) and 2 (Antar) with shubh/ashubh verdict.
    # Level 1 uses self-self combination (Vedic proxy for the whole Mahadasha period).
    try:
        geometry = build_chart_geometry(jd, place, ayanamsa=req.ayanamsa, vargas=[1])
        planets = geometry.get("planets") or []
        moon = next((p for p in planets if p.get("planet") == "Moon"), None)
        lagna_rashi = (geometry.get("lagna") or {}).get("rashi")
        janma_rashi = moon.get("rashi") if moon else None
        natal_sign = geometry.get("natalSign")
        analyzer = DashaImpactAnalyzer()

        def _assess(maha_lord, maha_start, maha_end, antar_lord, antar_start, antar_end):
            ladder = [
                {
                    "lord": maha_lord,
                    "level": 1,
                    "levelLabel": "Mahadasha",
                    "start": maha_start,
                    "end": maha_end,
                },
                {
                    "lord": antar_lord,
                    "level": 2,
                    "levelLabel": "Antardasha",
                    "start": antar_start,
                    "end": antar_end,
                },
            ]
            try:
                intel = analyzer.analyze(
                    ladder, lagna_rashi=lagna_rashi, janma_rashi=janma_rashi, natal_sign=natal_sign
                )
                return (intel.get("final_verdict"), intel.get("score")) if intel else (None, None)
            except Exception:
                return None, None

        def _propagate(nodes, parent_verdict, parent_score):
            """Recursively set verdict on all sub-nodes, inheriting from parent."""
            for node in nodes:
                node["verdict"] = parent_verdict
                node["score"] = parent_score
                _propagate(node.get("subPeriods", []), parent_verdict, parent_score)

        for maha in payload.get("dashaTree", []):
            ms, me = maha["start"], maha.get("end", maha["start"])
            maha["verdict"], maha["score"] = _assess(maha["lord"], ms, me, maha["lord"], ms, me)
            for antar in maha.get("subPeriods", []):
                av, as_ = _assess(
                    maha["lord"],
                    ms,
                    me,
                    antar["lord"],
                    antar["start"],
                    antar.get("end", antar["start"]),
                )
                antar["verdict"], antar["score"] = av, as_
                # Levels 3–5 inherit Antardasha verdict (analyzer doesn't go deeper)
                _propagate(antar.get("subPeriods", []), av, as_)
    except Exception:
        pass

    return {"birth_datetime": req.birth_datetime, "jd": jd, **payload}


@app.post("/dasha/deep")
def dasha_deep_jd(req: DashaDeepJdRequest):
    """Comprehensive multi-system dasha analysis from precomputed JDs.

    Body: birth_jd, query_jd, moon_lon_sidereal, lagna_idx.
    Returns Vimshottari (+ score), Yogini, Chara current, Kalachakra deha/jeeva,
    functional nature (Table 30), and a plain-text analysis summary.
    """
    from app.dasha_deep_jd import build_dasha_deep

    try:
        return build_dasha_deep(
            birth_jd=req.birth_jd,
            query_jd=req.query_jd,
            moon_lon_sidereal=req.moon_lon_sidereal,
            lagna_idx=req.lagna_idx,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"dasha/deep failed: {type(exc).__name__}: {exc}",
        ) from exc



@app.post("/ashtakavarga")
def ashtakavarga_endpoint(req: AshtakavargaRequest):
    """True PyJHora BAV/SAV + Kaksha grade for a natal chart (B-16.12).

    Body: natal_sign, lagna_sign (+ optional transit snapshot fields).
    Returns named-sign BAV/SAV boards, SAV bands, moon_transit_bindus, and
    the 2×2 Kaksha × Saturn-BAV grade (constructive|mixed|frictional).
    """
    from vedic_engine.prediction.ashtakavarga import build_ashtakavarga_payload

    try:
        return build_ashtakavarga_payload(
            natal_sign=req.natal_sign,
            lagna_sign=req.lagna_sign,
            moon_transit_sign=req.moon_transit_sign,
            saturn_transit_sign=req.saturn_transit_sign,
            saturn_deg_in_sign=req.saturn_deg_in_sign,
            kaksha_planet=req.kaksha_planet,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"ashtakavarga failed: {type(exc).__name__}: {exc}",
        ) from exc


@app.post("/dasha-predict")
@_product_claim_safe
def dasha_predict(req: BirthRequest):
    """
    Transit-fused Dasha predictions for the current Mahadasha + next Mahadasha.

    For each Antardasha period in scope we:
      1. Take the midpoint date as a representative transit snapshot.
      2. Run compute_gochar + TransitImpactAnalyzer at that date.
      3. Merge with DashaImpactAnalyzer score.
      4. Return combined verdict, score breakdown, key transits, and life-domain bullets.

    Keyed by "MahaLord/AntarLord" — matches DashaNode lookup on the portal.
    """
    from datetime import date, timedelta

    from app.chart import build_chart_geometry
    from app.dasha_transit_fusion import fuse_dasha_transit
    from app.dasha_vimshottari import antardasha_table, mahadasha_tree
    from vedic_engine.synthesis.dasha_analyzer import DashaImpactAnalyzer

    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    geometry = build_chart_geometry(jd, place, ayanamsa=req.ayanamsa, vargas=[1])
    planets_data = geometry.get("planets") or []
    moon = next((p for p in planets_data if p.get("planet") == "Moon"), None)
    lagna_rashi = (geometry.get("lagna") or {}).get("rashi")
    janma_rashi = moon.get("rashi") if moon else None
    janma_nakshatra = moon.get("nakshatra") if moon else None
    natal_sign = geometry.get("natalSign")

    # Identify current and next Mahadasha lords
    today = date.today()
    maha_tree = mahadasha_tree(jd, place, max_level=1)
    current_maha = next_maha = None
    for m in maha_tree:
        ms = date.fromisoformat(m["start"][:10])
        me = date.fromisoformat(m["end"][:10])
        if ms <= today <= me:
            current_maha = m["lord"]
        elif current_maha and next_maha is None:
            next_maha = m["lord"]

    scope = {x for x in (current_maha, next_maha) if x}

    analyzer = DashaImpactAnalyzer()
    antar_table = antardasha_table(jd, place)
    predictions: dict = {}

    for row in antar_table:
        maha_lord = row["maha"]
        if maha_lord not in scope:
            continue
        try:
            start_d = row["start"][:10]
            dur_days = max(1, int(row.get("durationYears", 1) * 365.25))
            end_d = (date.fromisoformat(start_d) + timedelta(days=dur_days)).isoformat()
            antar_lord = row["antara"]

            ladder = [
                {
                    "lord": maha_lord,
                    "level": 1,
                    "levelLabel": "Mahadasha",
                    "start": start_d,
                    "end": end_d,
                },
                {
                    "lord": antar_lord,
                    "level": 2,
                    "levelLabel": "Antardasha",
                    "start": start_d,
                    "end": end_d,
                },
            ]
            dasha_intel = analyzer.analyze(
                ladder,
                lagna_rashi=lagna_rashi,
                janma_rashi=janma_rashi,
                natal_sign=natal_sign,
            )

            pred = fuse_dasha_transit(
                maha_lord=maha_lord,
                antar_lord=antar_lord,
                start_date=start_d,
                end_date=end_d,
                lat=req.birth_lat,
                lon=req.birth_lon,
                tz=req.birth_tz,
                lagna_rashi=lagna_rashi,
                janma_rashi=janma_rashi,
                janma_nakshatra=janma_nakshatra,
                natal_sign=natal_sign,
                dasha_intel=dasha_intel,
            )
            if pred is not None:
                predictions[f"{maha_lord}/{antar_lord}"] = pred
        except Exception:
            continue

    return {"predictions": predictions}


@app.post("/dasha-predict-yogini")
@_product_claim_safe
def dasha_predict_yogini(req: BirthRequest):
    """
    Yogini Dasha predictions — pure Yogini framework (V.P. Goel / BPHS).

    Yogini is a completely independent system from Vimshottari.
    Predictions are based on:
      1. Yogini deity domain effects (Mangala/Moon, Pingala/Sun … Sankata/Rahu)
      2. Maha × Antar combination (benefic/malefic interplay per Goel Ch.3)
      3. Maha lord and Antar lord natal house placement from birth Lagna
      4. Lord dignity (exalted / own sign / debilitated)

    Keyed by "MahaYogini/AntarYogini" (e.g. "Bhadrika/Ulka").
    DashaImpactAnalyzer and fuse_dasha_transit are NOT used here.
    """
    from datetime import date

    from jhora.horoscope.dhasa.graha import yogini
    from jhora.panchanga.drik import Date as DrikDate

    from app.chart import build_chart_geometry
    from app.dasha_other import _build_tree_and_ladder, _enrich_yogini
    from app.yogini_predict import predict_yogini_antardasha

    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    geometry = build_chart_geometry(jd, place, ayanamsa=req.ayanamsa, vargas=[1])
    lagna = geometry.get("lagna") or {}
    lagna_sign = lagna.get("signIndex", 0)
    natal_sign = geometry.get("natalSign") or {}

    # Build Yogini tree (with deity names)
    flat = yogini.get_dhasa_bhukthi(
        DrikDate(dt.year, dt.month, dt.day),
        (dt.hour, dt.minute, dt.second),
        place,
    )
    tree, ladder = _build_tree_and_ladder(flat)
    tree, ladder = _enrich_yogini(tree, ladder)

    # Scope = current + next Mahadasha blocks
    today = date.today()
    current_block = next_block = None
    for node in tree:
        ms = date.fromisoformat(node["start"][:10])
        me = date.fromisoformat(node["end"][:10])
        if ms <= today <= me:
            current_block = node
        elif current_block and next_block is None:
            next_block = node

    scope_blocks = [b for b in (current_block, next_block) if b]
    predictions: dict = {}

    for block in scope_blocks:
        maha_yogini = block.get("yoginiName") or block["lord"]  # e.g. "Bhadrika"
        for antar in block.get("subPeriods", []):
            try:
                antar_yogini = antar.get("yoginiName") or antar["lord"]  # e.g. "Ulka"
                pred = predict_yogini_antardasha(
                    maha_yogini=maha_yogini,
                    antar_yogini=antar_yogini,
                    lagna_sign_idx=lagna_sign,
                    natal_sign=natal_sign,
                )
                if pred:
                    key = f"{maha_yogini}/{antar_yogini}"
                    predictions[key] = pred
            except Exception:
                continue

    return {"predictions": predictions}


class FructificationRequest(BirthRequest):
    system: str  # "yogini", "vimshottari", "ashtottari"
    maha_lord: str  # Yogini deity name (for Yogini) or planet name
    antar_lord: str
    maha_start: str  # ISO date
    maha_end: str  # ISO date
    antar_start: str  # ISO date
    antar_end: str  # ISO date


@app.post("/fructification")
@_product_claim_safe
def fructification_endpoint(req: FructificationRequest):
    """
    Fructification windows within a dasha antardasha period.

    Classical basis (Phaladeepika Ch.26 / Goel 2002/2006):
      The dasha period defines the DOMAIN of events (career, wealth, health, family).
      Saturn + Jupiter double-transit from Janma Rashi (and Progressed Lagna for Yogini)
      determines the TIMING — the specific months within the AD when the dasha promise
      actually manifests as events.

    Vedha (GPD Ch.22) cancels benefic transits when another planet occupies the Vedha house.
    Ashtakavarga SAV bindus (BPHS Ch.67) weight the fructification strength.
    """
    from app.fructification import fructify

    return fructify(
        birth_datetime=req.birth_datetime,
        birth_lat=req.birth_lat,
        birth_lon=req.birth_lon,
        birth_tz=req.birth_tz,
        system=req.system,
        maha_lord=req.maha_lord,
        antar_lord=req.antar_lord,
        maha_start=req.maha_start,
        maha_end=req.maha_end,
        antar_start=req.antar_start,
        antar_end=req.antar_end,
    )


class DashaSeriesRequest(BirthRequest):
    maha_lord: str
    antar_lord: str
    start_date: str  # ISO date — Antardasha start
    end_date: str  # ISO date — Antardasha end
    dasha_score: int = 0  # Pre-computed Dasha score for the pair
    interval_days: int = 30  # Sampling interval (default monthly)


@app.post("/dasha-series")
@_product_claim_safe
def dasha_series(req: DashaSeriesRequest):
    """
    Monthly transit-score time series for a single Maha-Antar window.

    Returns a list of data points suitable for a front-end area/line chart —
    each point carries the combined (Dasha+Transit) score and the dominant
    planetary driver. Also returns sign-change events for the slow planets
    (Saturn, Jupiter, Rahu/Ketu, Mars) that explain the peaks and dips.
    """
    from app.chart import build_chart_geometry
    from app.dasha_series import build_dasha_series

    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    geometry = build_chart_geometry(jd, place, ayanamsa=req.ayanamsa, vargas=[1])
    planets_data = geometry.get("planets") or []
    moon = next((p for p in planets_data if p.get("planet") == "Moon"), None)
    janma_rashi = moon.get("rashi") if moon else None
    janma_nakshatra = moon.get("nakshatra") if moon else None
    natal_sign = geometry.get("natalSign")
    lagna_rashi = (geometry.get("lagna") or {}).get("rashi")

    return build_dasha_series(
        maha_lord=req.maha_lord,
        antar_lord=req.antar_lord,
        start_date=req.start_date,
        end_date=req.end_date,
        dasha_score=req.dasha_score,
        lat=req.birth_lat,
        lon=req.birth_lon,
        tz=req.birth_tz,
        janma_rashi=janma_rashi,
        janma_nakshatra=janma_nakshatra,
        natal_sign=natal_sign,
        lagna_rashi=lagna_rashi,
        interval_days=max(14, min(90, req.interval_days)),
    )


class GocharRequest(BirthRequest):
    transit_instant: datetime = Field(
        ...,
        description="Timezone-aware ISO 8601 instant for the transit observation",
    )
    transit_place: str = Field(..., min_length=1, max_length=200)
    transit_lat: float = Field(..., ge=-90, le=90, allow_inf_nan=False)
    transit_lon: float = Field(..., ge=-180, le=180, allow_inf_nan=False)
    transit_timezone: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="IANA timezone for the observation place, e.g. Europe/Dublin",
    )
    transit_disambiguation: Literal["exact", "earlier", "later"] = "exact"

    @model_validator(mode="after")
    def validate_transit_context(self):
        requested_ayanamsa = self.ayanamsa.strip().upper()
        if requested_ayanamsa not in const.available_ayanamsa_modes:
            raise ValueError("ayanamsa must be a PyJHora-supported mode")
        self.ayanamsa = requested_ayanamsa
        self.transit_place = self.transit_place.strip()
        if not self.transit_place:
            raise ValueError("transit_place must not be blank")
        if self.transit_instant.utcoffset() is None:
            raise ValueError("transit_instant must include a UTC offset")
        try:
            zone = ZoneInfo(self.transit_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("transit_timezone must be a valid IANA timezone") from exc
        local = self.transit_instant.astimezone(zone)
        if local.utcoffset() != self.transit_instant.utcoffset():
            raise ValueError(
                "transit_instant UTC offset does not match transit_timezone at that instant"
            )

        naive_local = local.replace(tzinfo=None)
        candidates = sorted(
            {
                naive_local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
                for fold in (0, 1)
                if naive_local.replace(tzinfo=zone, fold=fold)
                .astimezone(UTC)
                .astimezone(zone)
                .replace(tzinfo=None)
                == naive_local
            }
        )
        ambiguous = len(candidates) == 2 and candidates[0] != candidates[1]
        if ambiguous:
            if self.transit_disambiguation not in ("earlier", "later"):
                raise ValueError(
                    "transit_disambiguation must be earlier or later for an ambiguous local time"
                )
            expected = candidates[0] if self.transit_disambiguation == "earlier" else candidates[1]
            if self.transit_instant.astimezone(UTC) != expected:
                raise ValueError(
                    "transit_instant does not match the requested DST overlap disambiguation"
                )
        elif self.transit_disambiguation != "exact":
            raise ValueError(
                "transit_disambiguation must be exact when the local time is not ambiguous"
            )
        return self


class CanonicalMuhurtaRequest(GocharRequest):
    """One election instant plus the exact loaded natal-chart identity."""

    expected_natal_jd: float = Field(..., allow_inf_nan=False)


def _canonical_karana_name(number: int) -> str:
    """Map PyJHora's 1..60 half-tithi index to the canonical Karana name."""
    if number == 1:
        return "Kimstughna"
    if 2 <= number <= 57:
        return KARANA_NAMES[1 + ((number - 2) % 7)]
    return {58: "Shakuni", 59: "Chatushpada", 60: "Naga"}.get(number, "Unknown")


def _canonical_muhurta_panchanga(jd: float, place) -> dict:
    """Swiss/PyJHora-only Panchanga projection; no approximate fallback."""
    raw = _panchanga(jd, place)
    karana_number = int(raw["karana"]["number"])
    raw["karana"]["name"] = _canonical_karana_name(karana_number)
    return raw


@app.post("/muhurta/canonical")
def canonical_muhurta(req: CanonicalMuhurtaRequest):
    """Canonical calculation-only Muhurta research result.

    All astronomy is evaluated through PyJHora/Swiss Ephemeris. Interpretive
    Vara/Tithi/Nakshatra combinations are returned with their source records;
    unvalidated limb interpretations remain explicitly neutral.
    """
    if not settings.NATIVE_MUHURTA_RESEARCH_ENABLED:
        raise HTTPException(status_code=404, detail="Native Muhurta research is disabled")

    resolved_timezone = _timezone_at(req.transit_lat, req.transit_lon)
    if resolved_timezone != req.transit_timezone:
        raise HTTPException(
            status_code=422,
            detail=(
                "transit_timezone does not match the server-resolved timezone "
                f"for the supplied coordinates ({resolved_timezone})"
            ),
        )

    birth_dt = parse_dt(req.birth_datetime)
    natal_jd, _natal_place = jd_place(
        birth_dt, req.birth_lat, req.birth_lon, req.birth_tz
    )
    if abs(natal_jd - req.expected_natal_jd) > 1e-8:
        raise HTTPException(
            status_code=409,
            detail="Loaded natal chart identity does not match canonical recomputation",
        )

    observation_zone = ZoneInfo(resolved_timezone)
    observation_local = req.transit_instant.astimezone(observation_zone)
    observation_offset = observation_local.utcoffset()
    assert observation_offset is not None
    observation_tz_hours = observation_offset.total_seconds() / 3600
    local_naive = observation_local.replace(tzinfo=None)

    # Serialize the complete PyJHora calculation under the requested ayanamsa.
    # No alternate engine or approximate branch is permitted if this raises.
    with ayanamsa_context(req.ayanamsa):
        election_jd, election_place = jd_place(
            local_naive, req.transit_lat, req.transit_lon, observation_tz_hours
        )
        calculation_engine = ephemeris_runtime_provenance(election_jd)
        if calculation_engine["backend"] != "Swiss Ephemeris":
            raise HTTPException(
                status_code=503,
                detail=(
                    "Canonical Swiss Ephemeris data files are unavailable; "
                    f"refusing {calculation_engine['backend']}"
                ),
            )
        panchanga = _canonical_muhurta_panchanga(election_jd, election_place)
        rk = drik.raahu_kaalam(election_jd, election_place)
        yg = drik.yamaganda_kaalam(election_jd, election_place)
        gk = drik.gulikai_kaalam(election_jd, election_place)
        sr = drik.sunrise(election_jd, election_place)
        ss = drik.sunset(election_jd, election_place)
    karana_number = int(panchanga["karana"]["number"])

    from vedic_engine.prediction.muhurta_yogas import (
        evaluate_muhurta_yogas,
        muhurta_yogas_to_dict,
    )

    yoga_result = evaluate_muhurta_yogas(
        panchanga["vara"]["name"],
        panchanga["tithi"]["number"],
        panchanga["nakshatra"]["name"],
        graph_hits=[],
    )
    yoga_payload = muhurta_yogas_to_dict(yoga_result)

    replay_payload = req.model_dump(mode="json")
    request_digest = hashlib.sha256(
        json.dumps(replay_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    neutral = "neutral"
    summary = yoga_payload["summary"]
    if not yoga_payload["active"]:
        summary = (
            "No cited Vara/Tithi/Nakshatra combination yoga was active at this instant. "
            "The raw Panchanga limbs remain neutral until an activity-specific rule is validated."
        )

    return {
        "date": observation_local.strftime("%Y-%m-%d"),
        "time": observation_local.strftime("%H:%M:%S"),
        "overall_verdict": yoga_payload["overall"],
        "overall_score": yoga_payload["score"],
        "summary": summary,
        "panchanga": {
            "tithi": {
                "name": panchanga["tithi"]["name"],
                "paksha": panchanga["tithi"]["paksha"],
                "num": panchanga["tithi"]["number"],
                "verdict": neutral,
            },
            "vaar": panchanga["vara"]["name"],
            "nakshatra": {
                "name": panchanga["nakshatra"]["name"],
                "pada": panchanga["nakshatra"]["pada"],
                "nature": "unknown",
                "verdict": neutral,
            },
            "yoga": {
                "name": panchanga["yoga"]["name"],
                "nature": "unknown",
                "verdict": neutral,
            },
            "karana": {
                "name": panchanga["karana"]["name"],
                "num": karana_number,
                "verdict": neutral,
            },
            "sunrise": sr[1] if isinstance(sr, (list, tuple)) else sr,
            "sunset": ss[1] if isinstance(ss, (list, tuple)) else ss,
        },
        "gochar": None,
        "dasha": None,
        "ashtakavarga": None,
        "muhurta_yogas": yoga_payload,
        "warnings": [
            "Activity-specific contraindications and natal transit factors are not yet validated on this canonical research path."
        ],
        "rules_source": "cited_classical_muhurta_tables",
        "graph_enhancements": None,
        "windows": {
            "datetime": observation_local.isoformat(),
            "rahu_kalam": {"start": rk[0], "end": rk[1]},
            "yamaganda": {"start": yg[0], "end": yg[1]},
            "gulika": {"start": gk[0], "end": gk[1]},
            "sunrise": sr[1] if isinstance(sr, (list, tuple)) else sr,
            "sunset": ss[1] if isinstance(ss, (list, tuple)) else ss,
        },
        "calculation_context": {
            "request_id": f"muhurta_{request_digest}",
            **calculation_engine,
            "ayanamsa": req.ayanamsa,
            "calculation_path": "app.ephem + jhora.panchanga.drik",
            "fallback_used": False,
        },
        "election_context": {
            "instant": req.transit_instant.isoformat(),
            "utc_instant": req.transit_instant.astimezone(UTC).isoformat(),
            "local_datetime": observation_local.isoformat(),
            "place": req.transit_place,
            "latitude": req.transit_lat,
            "longitude": req.transit_lon,
            "timezone": resolved_timezone,
            "timezone_source": "server_coordinate_resolution",
            "disambiguation": req.transit_disambiguation,
            "utc_offset_hours": observation_tz_hours,
            "jd": election_jd,
        },
        "natal_context": {
            "birth_datetime": req.birth_datetime,
            "birth_latitude": req.birth_lat,
            "birth_longitude": req.birth_lon,
            "birth_timezone_offset_hours": req.birth_tz,
            "ayanamsa": req.ayanamsa,
            "jd": natal_jd,
            "identity_verified": True,
        },
    }


@app.post("/gochar")
@_product_claim_safe
def gochar_endpoint(req: GocharRequest):
    """
    Full Gochar (transit) interpretation for a given date against the natal chart.

    Returns per-planet house positions from natal Moon and Lagna, quality ratings,
    scores, effects, and any active special transits (Sade Sati, Ashtama Shani, etc.).
    """
    from app.chart import build_chart_geometry
    from vedic_engine.prediction.gochar import compute_gochar

    resolved_timezone = _timezone_at(req.transit_lat, req.transit_lon)
    if resolved_timezone != req.transit_timezone:
        raise HTTPException(
            status_code=422,
            detail=(
                "transit_timezone does not match the server-resolved timezone "
                f"for the supplied coordinates ({resolved_timezone})"
            ),
        )

    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)

    observation_zone = ZoneInfo(resolved_timezone)
    observation_local = req.transit_instant.astimezone(observation_zone)
    query_date = observation_local.strftime("%Y-%m-%d")
    query_time = observation_local.strftime("%H:%M")
    observation_offset = observation_local.utcoffset()
    assert observation_offset is not None
    observation_tz_hours = observation_offset.total_seconds() / 3600
    observation_clock = observation_local.replace(tzinfo=None)
    observation_jd, observation_place = jd_place(
        observation_clock,
        req.transit_lat,
        req.transit_lon,
        observation_tz_hours,
    )

    # PyJHora's ayanamsa mode is process-global. Keep natal and transit Swiss
    # calculations in one serialized context so the returned label necessarily
    # matches the math, even under concurrent mixed-ayanamsa requests.
    with ayanamsa_context(req.ayanamsa):
        natal_engine = ephemeris_runtime_provenance(jd)
        calculation_engine = ephemeris_runtime_provenance(observation_jd)
        if (
            natal_engine["backend"] != "Swiss Ephemeris"
            or calculation_engine["backend"] != "Swiss Ephemeris"
        ):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Canonical Swiss Ephemeris data files are unavailable for "
                    "the natal or transit instant; refusing analytical fallback"
                ),
            )
        geometry = build_chart_geometry(jd, place, ayanamsa=req.ayanamsa, vargas=[1])
        canonical_positions = positions(observation_jd, observation_place)

    planets_data = geometry.get("planets") or []
    moon = next((p for p in planets_data if p.get("planet") == "Moon"), None)
    janma_rashi = moon.get("rashi") if moon else None
    janma_nakshatra = moon.get("nakshatra") if moon else None
    natal_sign = geometry.get("natalSign")
    lagna_rashi = (geometry.get("lagna") or {}).get("rashi")
    transit_rows = [
        {
            "planet": body["planet"],
            "rashi": body["rashi"],
            "nak": body["nakshatra"],
            "pada": body["pada"],
            "deg": body["degInSign"],
            "deg_label": body["degLabel"],
            "retro": body["retro"],
            "lon": body["longitude"],
        }
        for body in canonical_positions
    ]

    g = compute_gochar(
        date_str=query_date,
        time_str=query_time,
        lat=req.transit_lat,
        lon=req.transit_lon,
        tz=observation_tz_hours,
        janma_rashi=janma_rashi,
        janma_nakshatra=janma_nakshatra,
        natal_sign=natal_sign,
        lagna_rashi=lagna_rashi,
        transit_rows=transit_rows,
    )

    replay_payload = req.model_dump(mode="json")
    request_digest = hashlib.sha256(
        json.dumps(replay_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]

    return {
        "date": query_date,
        "calculation_context": {
            "request_id": f"gochar_{request_digest}",
            **calculation_engine,
            "ayanamsa": req.ayanamsa,
            "replay_payload": replay_payload,
            "fallback_used": False,
        },
        "transit_context": {
            "instant": req.transit_instant.isoformat(),
            "utc_instant": req.transit_instant.astimezone(UTC).isoformat(),
            "local_datetime": observation_local.isoformat(),
            "place": req.transit_place,
            "latitude": req.transit_lat,
            "longitude": req.transit_lon,
            "timezone": resolved_timezone,
            "timezone_source": "server_coordinate_resolution",
            "disambiguation": req.transit_disambiguation,
            "utc_offset_hours": observation_tz_hours,
        },
        "natal_context": {
            "birth_datetime": req.birth_datetime,
            "birth_latitude": req.birth_lat,
            "birth_longitude": req.birth_lon,
            "birth_timezone_offset_hours": req.birth_tz,
            "ayanamsa": req.ayanamsa,
        },
        "janma_rashi": janma_rashi,
        "janma_nakshatra": janma_nakshatra,
        "lagna_rashi": lagna_rashi,
        "overall_score": g.overall_score,
        "overall_verdict": g.overall_verdict,
        "lagna_overall_score": g.lagna_overall_score,
        "synthesis": g.synthesis,
        "moorthy": g.moorthy,
        "sade_sati": g.sade_sati,
        "ashtama_shani": g.ashtama_shani,
        "kantaka_shani": g.kantaka_shani,
        "tara_balam": g.tara_balam,
        "planets": [
            {
                "planet": p.planet,
                "longitude": p.longitude,
                "rashi": p.rashi,
                "nakshatra": p.nakshatra,
                "retrograde": p.retrograde,
                "house_from_janma": p.house_from_janma,
                "house_from_lagna": p.house_from_lagna,
                "verdict": p.verdict,
                "house_quality": p.house_quality,
                "score": p.score,
                "lagna_score": p.lagna_score,
                "effects": p.effects[:2],
                "vedha_active": p.vedha_active,
                "vedha_by": p.vedha_by,
                "vipareetha_vedha_active": p.vipareetha_vedha_active,
            }
            for p in g.planet_predictions
        ],
    }


class ReportFactsRequest(BirthRequest):
    query_date: str | None = None
    query_time: str = "12:00"
    include_dasha_tree: bool = False


@app.post("/report/facts")
@_product_claim_safe
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
            include_varshaphala=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report facts failed: {e}") from e


class SpecialPointsResponse(BaseModel):
    class Config:
        arbitrary_types_allowed = True


@app.post("/special-points")
def special_points(req: BirthRequest):
    """Compute Mandi, Gulika, Bhrigu Bindu, and other special lagna points."""
    from jhora.panchanga.drik import Date, maandi_longitude, gulika_longitude

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

    # Maandi and Gulika — Upagraha longitudes (Saturn's portion of the day),
    # not the *_kaalam time-window helpers (those return start/end times, not
    # a zodiacal longitude).
    dob = Date(dt.year, dt.month, dt.day)
    tob = (dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)

    try:
        sign_idx, deg_in_sign = maandi_longitude(dob, tob, place)
        results["mandi"] = split_lon("Mandi (Maandi)", sign_idx * 30 + deg_in_sign)
    except Exception:
        results["mandi"] = None

    try:
        sign_idx, deg_in_sign = gulika_longitude(dob, tob, place)
        results["gulika"] = split_lon("Gulika", sign_idx * 30 + deg_in_sign)
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
        [1, 2, 11, 12, 13, 25, 26],  # Kshatriya
        [3, 4, 14, 15, 19, 20, 21, 22],  # Vaishya
        [7, 8, 16],  # Shudra
    ]
    for gid, naks in enumerate(varna_groups):
        for n in naks:
            varna[n] = gid
    bv = varna[nak_bride]
    gv = varna[nak_groom]
    varna_score = 1 if gv >= bv else 0

    # 2. Vashya (2 points)
    vashya_groups = [
        [0, 4, 5, 9, 20],  # Manava
        [1, 2, 7, 12, 17, 24, 26],  # Vanachara
        [3, 13, 15, 19, 22, 23],  # Chatushpada
        [6, 8, 10, 11, 16, 18, 21, 25],  # Jalachara
    ]

    def vashya_of(nak):
        return next((i for i, g in enumerate(vashya_groups) if nak in g), -1)

    bva = vashya_of(nak_bride)
    gva = vashya_of(nak_groom)
    vashya_score = 2 if bva == gva else (1 if bva >= 0 and gva >= 0 else 0)

    # 3. Tara (3 points)
    tara_count = count % 9
    if tara_count == 0:
        tara_count = 9
    tara_score = 3 if tara_count in (1, 3, 5, 7, 9) else (1.5 if tara_count in (2, 4, 6, 8) else 0)

    # 4. Yoni (4 points)
    yoni_map = [
        1,
        6,
        0,
        3,
        10,
        7,
        4,
        8,
        13,
        12,
        11,
        2,
        5,
        9,
        0,
        13,
        10,
        7,
        4,
        1,
        3,
        6,
        2,
        11,
        5,
        8,
        12,
    ]
    byoni = yoni_map[nak_bride]
    gyoni = yoni_map[nak_groom]
    yoni_score = (
        4
        if byoni == gyoni
        else (3 if byoni % 2 == gyoni % 2 else (2 if abs(byoni - gyoni) <= 3 else 1))
    )

    # 5. Graha Maitri (5 points)
    rashi_friends = {
        0: [0, 4, 5, 8, 11],
        1: [1, 2, 3, 9, 10],
        2: [1, 2, 3, 9, 10],
        3: [1, 2, 3, 9, 10],
        4: [0, 4, 5, 8, 11],
        5: [0, 4, 5, 8, 11],
        6: [6, 7],
        7: [6, 7],
        8: [0, 4, 5, 8, 11],
        9: [1, 2, 3, 9, 10],
        10: [1, 2, 3, 9, 10],
        11: [0, 4, 5, 8, 11],
    }
    br = bride["moonRashi"]
    gr = groom["moonRashi"]
    maitri_score = (
        5 if gr in rashi_friends.get(br, []) else (4 if br in rashi_friends.get(gr, []) else 1)
    )

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

    total = (
        varna_score
        + vashya_score
        + tara_score
        + yoni_score
        + maitri_score
        + gana_score
        + bhakoot_score
        + ndi_score
    )

    # Kuja Dosha (Manglik)
    mars_positions = [1, 2, 4, 7, 8, 12]  # houses from Lagna where Mars is Manglik
    bride_manglik = bride["marsRashi"] is not None
    groom_manglik = groom["marsRashi"] is not None

    return {
        "totalScore": round(total, 1),
        "maxScore": 36,
        "verdict": "Excellent"
        if total >= 28
        else "Good"
        if total >= 21
        else "Average"
        if total >= 18
        else "Below Average"
        if total >= 12
        else "Low",
        "breakdown": {
            "varna": {
                "score": varna_score,
                "max": 1,
                "name": "Varna (Caste/Spiritual compatibility)",
            },
            "vashya": {
                "score": vashya_score,
                "max": 2,
                "name": "Vashya (Mutual attraction/control)",
            },
            "tara": {"score": tara_score, "max": 3, "name": "Tara (Health/longevity of couple)"},
            "yoni": {"score": yoni_score, "max": 4, "name": "Yoni (Sexual/physical compatibility)"},
            "grahaMaitri": {
                "score": maitri_score,
                "max": 5,
                "name": "Graha Maitri (Mental/psychological affinity)",
            },
            "gana": {"score": gana_score, "max": 6, "name": "Gana (Temperament match)"},
            "bhakoot": {
                "score": bhakoot_score,
                "max": 7,
                "name": "Bhakoot (Financial/family prosperity)",
            },
            "nadi": {"score": ndi_score, "max": 8, "name": "Nadi (Physiological/genetic health)"},
        },
        "kujaDosha": {
            "bride": bride_manglik,
            "groom": groom_manglik,
            "note": "Mars in 1,2,4,7,8,12 from Lagna indicates Kuja Dosha. Both partners having it cancels the affliction.",
        },
        "ke_version": _ke_version(),
    }


# =====================================================================
# KP System — Placidus houses + star lords + sub-lords + sub-sub lords
# =====================================================================


@app.post("/kp-system")
def kp_system(req: BirthRequest):
    """Krishnamurti Paddhati: Placidus house cusps with star lords, sub-lords,
    and sub-sub-lords for each cusp and planet position."""
    from vedic_engine.prediction.kp_system import _ensure_kp_registered

    _ensure_kp_registered()
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
        rem = lon % NAK_SPAN
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
    cusps, ascmc = swe.houses(ut_jd, lat, lon, b"P")

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
            "degLabel": f"{int(deg)}°{int(round((deg - int(deg)) * 60)):02d}′",
            "starLord": starlord,
            "subLord": sublord,
            "subSubLord": sslord,
        }

    # 12 house cusps
    # cusps is 12-element tuple: cusps[0]=H1, cusps[1]=H2, ..., cusps[11]=H12
    houses = [cusp_data(f"Bhava {i + 1}", cusps[i]) for i in range(len(cusps))]

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
        "ke_version": _ke_version(),
    }


# =====================================================================
# Additional Dasha Systems — Chara, Ashtottari, Yogini, Kalachakra, Drig
# =====================================================================


def _now_jd() -> float:
    from datetime import datetime

    import swisseph as swe

    now = datetime.now(UTC)
    return swe.julday(now.year, now.month, now.day, now.hour + now.minute / 60 + now.second / 3600)


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
    # Extract start/end dates: row format = [lords_tuple, start_tuple_or_jd, duration_years]
    antar_start_str = antar_end_str = None
    try:
        from datetime import date as _d
        from datetime import timedelta as _td

        from jhora import utils as _u

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
                _d.fromisoformat(antar_start_str) + _td(days=int(dur * 365.25))
            ).isoformat()
    except Exception as _e:
        print(f"[ashtottari] date extraction: {_e}", flush=True)
    return {
        "maha": lord_name(maha) if maha is not None else None,
        "antara": lord_name(antara) if antara is not None else None,
        "applicable": True,
        "antaraStart": antar_start_str,
        "antaraEnd": antar_end_str,
    }


@app.post("/dashas")
def all_dashas(req: BirthRequest):
    """Compute multiple dasha systems for a birth chart.
    Returns current periods for Vimshottari, Yogini, Ashtottari, Chara, Kalachakra (P0 active work)."""
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

        _VIML = {1: "Mahadasha", 2: "Antardasha", 3: "Pratyantardasha", 4: "Sookshma", 5: "Prana"}
        vl = running_ladder(jd, place, depth=3)
        maha_row = vl[0] if vl else None
        antar_row = vl[1] if len(vl) > 1 else None
        result["vimshottari"] = {
            "maha": maha_row["lord"] if maha_row else None,
            "antara": antar_row["lord"] if antar_row else None,
            "mahaStart": maha_row["start"] if maha_row else None,
            "mahaEnd": maha_row["end"] if maha_row else None,
            "antaraStart": antar_row["start"] if antar_row else None,
            "antaraEnd": antar_row["end"] if antar_row else None,
            "balanceAtBirth": birth_balance(jd, place),
            "ladder": [
                {
                    "levelLabel": _VIML.get(i + 1, f"Level {i + 1}"),
                    "lord": r["lord"],
                    "start": r.get("start"),
                    "end": r.get("end"),
                }
                for i, r in enumerate(vl)
            ],
        }
    except Exception as e:
        print(f"[all_dashas] vimshottari failed: {type(e).__name__}: {e}", flush=True)
        result["vimshottari"] = None

    # Yogini Dasha — build full running ladder (Maha → Antar → Pratyantar)
    try:
        from datetime import date as _d
        from datetime import timedelta as _td

        from jhora.horoscope.dhasa.graha import yogini
        from jhora.panchanga.drik import Date as DrikDate

        y = yogini.get_dhasa_bhukthi(
            DrikDate(dt.year, dt.month, dt.day),
            (dt.hour, dt.minute, dt.second),
            place,
        )
        today = _d.today()

        _YL = {1: "Mahadasha", 2: "Antardasha", 3: "Pratyantardasha"}
        by_depth: dict = {}

        for row in y or []:
            try:
                lords = row[0]
                st = row[1]
                dur = float(row[2])
                depth = len(lords) if isinstance(lords, (list, tuple)) else 0
                if depth == 0 or depth in by_depth:
                    continue
                if isinstance(st, (list, tuple)) and len(st) >= 3:
                    s = _d(int(st[0]), int(st[1]), int(st[2]))
                    e = s + _td(days=int(dur * 365.25))
                    if s <= today <= e:
                        by_depth[depth] = {
                            "lord": lord_name(lords[depth - 1]),
                            "start": s.isoformat(),
                            "end": e.isoformat(),
                        }
            except Exception:
                continue

        ladder_y = [
            {"levelLabel": _YL.get(d, f"Level {d}"), **by_depth[d]} for d in sorted(by_depth.keys())
        ]

        d1 = by_depth.get(1, {})
        d2 = by_depth.get(2, {})

        # Fallback lords from first row if ladder empty
        if not d1:
            cy = y[0] if y else None
            lords0 = cy[0] if cy and isinstance(cy[0], (list, tuple)) else None
            d1 = {"lord": lord_name(lords0[0])} if lords0 else {}
            d2 = {"lord": lord_name(lords0[1])} if lords0 and len(lords0) > 1 else {}

        result["yogini"] = {
            "maha": d1.get("lord"),
            "antara": d2.get("lord"),
            "mahaStart": d1.get("start"),
            "mahaEnd": d1.get("end"),
            "antaraStart": d2.get("start"),
            "antaraEnd": d2.get("end"),
            "ladder": ladder_y,
        }
    except Exception as e:
        print(f"[all_dashas] yogini failed: {type(e).__name__}: {e}", flush=True)
        result["yogini"] = None

    # Ashtottari Dasha — running period via get_running_dhasa_for_given_date
    try:
        result["ashtottari"] = _ashtottari_current(jd, place, lord_name)
    except Exception as e:
        print(f"[all_dashas] ashtottari failed: {type(e).__name__}: {e}", flush=True)
        result["ashtottari"] = None

    # Chara + Kalachakra + Kaksha — PyJHora rashi dashas + prastara kaksha refinement
    try:
        from jhora.panchanga.drik import Date as DrikDate

        from app.dasha_extras import (
            chara_dasha_payload,
            kaksha_payload,
            kalachakra_dasha_payload,
        )

        dob = DrikDate(dt.year, dt.month, dt.day)
        tob = (dt.hour, dt.minute, dt.second)

        # Prefer dedicated KE-integrated modules (chara_dasha, kalachakra, kaksha) which self-register
        try:
            from app.chara_dasha import compute_chara_dasha
            from app.kalachakra import compute_kalachakra_dasha
            from app.kaksha import kaksha_calendar_full, get_current_kaksha

            result["chara"] = compute_chara_dasha(req.birth_datetime, req.birth_lat, req.birth_lon, req.birth_tz)
            result["kalachakra"] = compute_kalachakra_dasha(req.birth_datetime, req.birth_lat, req.birth_lon, req.birth_tz)
            # Kaksha calendar + current (use natal jd for prastara context + current transits)
            kk_cal = kaksha_calendar_full()
            # compute current for transiting planets using same jd for demo (in prod use query time)
            trans = positions(jd, place)  # reuse natal for baseline; caller can POST query
            cur_kak = []
            for p in trans[:7]:
                cur_kak.append(get_current_kaksha(p["planet"], p.get("longitude",0), p.get("signIndex",0)))
            result["kaksha"] = {
                "status": "active",
                "calendar": kk_cal,
                "current": cur_kak,
                "ke_version": kk_cal.get("ke_version"),
                "source_notes": kk_cal.get("source_notes", []),
            }
        except Exception:
            # fallback to extras (still emits graph_cites)
            result["chara"] = chara_dasha_payload(jd, place, dob, tob, query_jd=_now_jd())
            result["kalachakra"] = kalachakra_dasha_payload(jd, place, dob, tob, query_jd=_now_jd())
            result["kaksha"] = kaksha_payload(jd, place, query_jd=_now_jd())
    except Exception as e:
        print(f"[all_dashas] chara/kala/kaksha failed: {type(e).__name__}: {e}", flush=True)
        result["chara"] = {"status": "active", "error": str(e)[:100]}
        result["kalachakra"] = {"status": "active", "error": str(e)[:100]}
        result["kaksha"] = {"status": "active", "error": str(e)[:100]}

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
    from datetime import datetime

    from vedic_engine.prediction.prashna import _ensure_prashna_registered

    _ensure_prashna_registered()

    dt_str = req.birth_datetime
    if not dt_str:
        dt_str = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    res = chart(
        BirthRequest(
            birth_datetime=dt_str,
            birth_lat=req.birth_lat,
            birth_lon=req.birth_lon,
            birth_tz=req.birth_tz,
            ayanamsa=req.ayanamsa,
            name=req.name or "Prashna",
        )
    )
    if isinstance(res, dict):
        res = {**res, "ke_version": _ke_version()}
    return res


VARSHA_MUNTHA_SIGNS = [
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
        "ke_version": _ke_version(),
    }


# ── Kalachakra Dasha (exposed endpoint) ─────────────────────────────────────

@app.post("/kalachakra-dasha")
def kalachakra_dasha(req: BirthRequest):
    """Kalachakra Dasha (86y, deha/jeeva, Moon nak-pada wheel) — full periods + current."""
    from app.kalachakra import compute_kalachakra_dasha
    return compute_kalachakra_dasha(
        req.birth_datetime, req.birth_lat, req.birth_lon, req.birth_tz
    )


@app.post("/kalachakra-deep")
def kalachakra_deep(req: BirthRequest):
    """Kalachakra Dasha — rich view: birth nakshatra/pada, Deha/Jeeva Rasi, the
    9-sign cycle with Gati (leap) flags, current MD/AD/PD ladder, the active
    leap (if any), a 3-level MD->AD->PD tree, and a chronological leap timeline
    (past/current/future). Per BPHS Vol.2 Ch.46/49."""
    from jhora.panchanga.drik import Date as DrikDate

    from app.kalachakra import kalachakra_deep_payload

    set_ayanamsa(req.ayanamsa)
    dt = parse_dt(req.birth_datetime)
    jd, place = jd_place(dt, req.birth_lat, req.birth_lon, req.birth_tz)
    dob = DrikDate(dt.year, dt.month, dt.day)
    tob = (dt.hour, dt.minute, dt.second)
    return kalachakra_deep_payload(jd, place, dob, tob)


# ── Place search — backed by PyJHora's GeoNames dataset ─────────────────────


def _load_places_db() -> list[tuple[str, str, str, str, float, float, float]]:
    """Load GeoNames CSVs from PyJHora installation. Returns list of
    (place_name, alternate_names_lower, state, country, lat, lon, tz)."""
    import csv
    import pathlib

    import jhora as _jhora

    data_dir = pathlib.Path(_jhora.__file__).parent / "data"
    rows: list[tuple] = []

    for fname in ("geonames_places_5k_IN.csv", "geonames_places_5k.csv"):
        fpath = data_dir / fname
        if not fpath.exists():
            continue
        with open(fpath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rows.append(
                        (
                            row["place_name"],
                            (row["alternate_names"] or "").lower(),
                            row.get("state", ""),
                            row.get("country", ""),
                            float(row["latitude"]),
                            float(row["longitude"]),
                            float(row["timezone_hours"]),
                        )
                    )
                except (KeyError, ValueError):
                    continue
    return rows


_places_cache: list | None = None


def _get_places() -> list:
    global _places_cache
    if _places_cache is None:
        _places_cache = _load_places_db()
    return _places_cache


@app.get("/places")
def search_places(q: str = ""):
    """Search GeoNames city database. Returns top 8 matches with lat/lon/tz.
    Searches place_name and alternate_names (transliterations included)."""
    q = q.strip()
    if len(q) < 2:
        return {"results": []}

    ql = q.lower()
    places = _get_places()
    results = []
    seen: set[str] = set()

    # Pass 1: exact prefix on place_name (highest priority)
    # Pass 2: prefix in alternate_names
    # Pass 3: substring in place_name
    for mode in ("prefix_name", "prefix_alt", "substr_name"):
        if len(results) >= 6:
            break
        for name, alts, state, country, lat, lon, tz in places:
            if len(results) >= 6:
                break
            key = f"{name}|{state}|{country}"
            if key in seen:
                continue
            nl = name.lower()
            if mode == "prefix_name":
                match = nl.startswith(ql)
            elif mode == "prefix_alt":
                match = any(a.startswith(ql) for a in alts.split("|") if a)
            else:
                match = ql in nl
            if match:
                seen.add(key)
                label_parts = [p for p in [name, state, country] if p]
                results.append(
                    {
                        "name": name,
                        "label": ", ".join(label_parts),
                        "state": state,
                        "country": country,
                        "lat": round(lat, 4),
                        "lon": round(lon, 4),
                        "tz": tz,
                        "timezone": _timezone_at(lat, lon),
                    }
                )

    return {"results": results}


_timezone_finder = None


def _timezone_at(lat: float, lon: float) -> str:
    """Resolve an observation coordinate to an IANA timezone."""
    global _timezone_finder
    if _timezone_finder is None:
        from timezonefinder import TimezoneFinder

        _timezone_finder = TimezoneFinder(in_memory=True)
    timezone = _timezone_finder.timezone_at(lat=lat, lng=lon)
    if not timezone:
        raise HTTPException(status_code=422, detail="Could not resolve timezone for coordinates")
    return timezone


@app.get("/timezone")
def timezone_at(lat: float, lon: float):
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise HTTPException(status_code=422, detail="Coordinates are out of range")
    return {"timezone": _timezone_at(lat, lon), "lat": lat, "lon": lon}


@app.post("/knowledge/refresh")
def knowledge_refresh(reason: str = "manual"):
    """
    **Global Knowledge Refresh Trigger**

    Forces every registered engine to immediately recalculate its logic,
    predictions, and interpretations using the latest knowledge graph.

    This is the explicit "refresh all" command for the system.
    """
    if _ensure_knowledge_engine() is None:
        raise HTTPException(status_code=503, detail="KnowledgeEngine not available")

    result = _knowledge_engine.trigger_global_refresh(reason=reason)
    return result


@app.get("/knowledge/search")
def knowledge_search(q: str = "", top_k: int = 8):
    """Hybrid semantic + keyword search over corpus chunks via KnowledgeEngine."""
    if _ensure_knowledge_engine() is None:
        raise HTTPException(status_code=503, detail="KnowledgeEngine not available")

    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query parameter q is required")

    top_k = max(1, min(top_k, 50))
    results = _knowledge_engine.search(query, top_k=top_k)
    return {
        "query": query,
        "count": len(results),
        "vector_search_available": _knowledge_engine.vector_search_available(),
        "results": results,
    }


@app.post("/knowledge/embeddings-updated")
def knowledge_embeddings_updated(chunk_count: int = 0):
    """Called after corpus embeddings are populated — clears caches and notifies engines."""
    if _ensure_knowledge_engine() is None:
        raise HTTPException(status_code=503, detail="KnowledgeEngine not available")

    from knowledge_engine.integration import clear_knowledge_engine_cache

    result = _knowledge_engine.on_embeddings_updated(chunk_count=chunk_count)
    clear_knowledge_engine_cache()
    return result


# ------------------------------------------------------------------ #
# KnowledgeEngine — Structured literature (chapter tree + node linkage)
# The KE is now the owner of the organised structured data for the Learn reader.
# ------------------------------------------------------------------


@app.get("/knowledge/structured/{book_id}")
def knowledge_structured_book(book_id: str):
    """Return the clean chapter tree + KE nodes mapped to each chapter.

    This is what the Learn portal (and any CVCE consumer) should use to render
    a book with its authoritative TOC and the classical knowledge nodes that
    belong under each chapter/section.
    """
    if _ensure_knowledge_engine() is None:
        raise HTTPException(status_code=503, detail="KnowledgeEngine not available")
    data = _knowledge_engine.get_structured_book(book_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Structured book not found: {book_id}")
    return data


@app.get("/knowledge/chapter/{book_id}/{chapter_id}/nodes")
def knowledge_chapter_nodes(book_id: str, chapter_id: str):
    """Nodes that the KnowledgeEngine has mapped to one specific chapter."""
    if _ensure_knowledge_engine() is None:
        raise HTTPException(status_code=503, detail="KnowledgeEngine not available")
    nodes = _knowledge_engine.get_nodes_for_chapter(book_id, chapter_id)
    return {"book_id": book_id, "chapter_id": chapter_id, "count": len(nodes), "nodes": nodes}


@app.get("/knowledge/node/{node_id}/hierarchy")
def knowledge_node_hierarchy(node_id: str):
    """Where a given KE node sits inside the source book's chapter hierarchy."""
    if _ensure_knowledge_engine() is None:
        raise HTTPException(status_code=503, detail="KnowledgeEngine not available")
    h = _knowledge_engine.get_hierarchy_for_node(node_id)
    if not h:
        raise HTTPException(status_code=404, detail=f"No chapter mapping for node: {node_id}")
    return h


# Canonical planet names accepted by transit house tables (graph + hardcoded).
_TRANSIT_PLANETS = frozenset(
    {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
)
_TRANSIT_PLANET_ALIASES = {
    "sun": "Sun",
    "moon": "Moon",
    "mars": "Mars",
    "mercury": "Mercury",
    "jupiter": "Jupiter",
    "venus": "Venus",
    "saturn": "Saturn",
    "rahu": "Rahu",
    "ketu": "Ketu",
    "surya": "Sun",
    "chandra": "Moon",
    "mangal": "Mars",
    "budha": "Mercury",
    "guru": "Jupiter",
    "shukra": "Venus",
    "shani": "Saturn",
}


def _normalize_transit_planet(planet: str) -> str | None:
    raw = (planet or "").strip()
    if not raw:
        return None
    if raw in _TRANSIT_PLANETS:
        return raw
    return _TRANSIT_PLANET_ALIASES.get(raw.lower())


def _hardcoded_transit_lookup(planet: str, house: int) -> dict:
    """Fallback when graph rules are unavailable — uses vedic_engine transit tables."""
    from vedic_engine.rules.transit_rules import TRANSIT_HOUSES

    tbl = TRANSIT_HOUSES.get(planet, {})
    if house in tbl.get("worst", []):
        quality = "worst"
    elif house in tbl.get("bad", []):
        quality = "bad"
    elif house in tbl.get("good", []):
        quality = "good"
    elif house in tbl.get("neutral", []):
        quality = "neutral"
    else:
        quality = "neutral"

    src = tbl.get("source") or "GPD-Ch10-Table12"
    # Normalize source tags into human-readable citation list
    sources = ["GPD Ch.10"]
    if "HS" in str(src) or "Hora" in str(src):
        sources.append("Hora Sara Ch.17")

    effect_map = {
        "good": f"{planet} in {house}th from Janma Rasi — favourable (hardcoded GPD table)",
        "bad": f"{planet} in {house}th from Janma Rasi — unfavourable (hardcoded GPD table)",
        "worst": f"{planet} in {house}th from Janma Rasi — worst position (hardcoded GPD table)",
        "neutral": f"{planet} in {house}th from Janma Rasi — neutral (hardcoded GPD table)",
    }
    return {
        "quality": quality,
        "confidence": 0.5,
        "sources": sources,
        "effect_text": effect_map[quality],
        "conflict_note": None,
        "rules_source": "hardcoded",
        "planet": planet,
        "house": house,
    }


@app.get("/knowledge/transit")
def knowledge_transit(planet: str = "", house: int | None = None):
    """Graph-backed transit house quality for a planet in a house from Janma Rasi.

    Query params:
      - planet: Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu
      - house: 1–12 (house counted from natal Moon / Janma Rasi)

    Prefers KnowledgeEngine GraphTransitRules (multi-text consensus + confidence).
    Falls back to hardcoded vedic_engine.rules.transit_rules when graph rules
    are unavailable.
    """
    planet_norm = _normalize_transit_planet(planet)
    if not planet_norm:
        raise HTTPException(
            status_code=400,
            detail="planet is required (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu)",
        )
    if house is None:
        raise HTTPException(status_code=400, detail="house is required (integer 1–12)")
    try:
        house_num = int(house)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="house must be an integer 1–12") from None
    if not 1 <= house_num <= 12:
        raise HTTPException(status_code=400, detail="house must be an integer 1–12")

    rules = None
    try:
        from knowledge_engine.integration import get_safe_transit_rules

        rules = get_safe_transit_rules()
    except Exception:
        rules = None

    # Graph path: GraphTransitRules exposes house_quality / confidence / effects
    if rules is not None and hasattr(rules, "house_quality"):
        quality, _verdict, _score = rules.house_quality(planet_norm, house_num)
        conf = float(rules.confidence(planet_norm, house_num)) if hasattr(rules, "confidence") else 0.5
        conf = max(0.0, min(1.0, conf))

        effects = (
            rules.transit_effects(planet_norm, house_num)
            if hasattr(rules, "transit_effects")
            else []
        )
        # Prefer classical graph note (2nd line) when present; else join all
        if isinstance(effects, list) and len(effects) >= 2:
            effect_text = str(effects[1])
        elif isinstance(effects, list) and effects:
            effect_text = str(effects[0])
        else:
            effect_text = (
                f"{planet_norm} in {house_num}th from Janma Rasi — {quality}"
            )

        sources: list[str] = ["GPD Ch.10", "Hora Sara Ch.17"]
        # Enrich from graph citations when available
        if hasattr(rules, "get_citations"):
            try:
                cites = rules.get_citations(planet_norm, house_num) or []
                for c in cites:
                    nid = str(c.get("node") or "")
                    if "hora_sara" in nid and "Hora Sara Ch.17" not in sources:
                        sources.append("Hora Sara Ch.17")
                    if "sarvartha" in nid and "Sarvartha Chintamani" not in sources:
                        sources.append("Sarvartha Chintamani")
            except Exception:
                pass

        conflict_note = None
        if hasattr(rules, "transit_houses"):
            try:
                tbl = rules.transit_houses(planet_norm) or {}
                note = tbl.get("conflict_note")
                if note:
                    conflict_note = str(note)
            except Exception:
                conflict_note = None

        return {
            "quality": quality,
            "confidence": conf,
            "sources": sources,
            "effect_text": effect_text,
            "conflict_note": conflict_note,
            "rules_source": "graph",
            "planet": planet_norm,
            "house": house_num,
        }

    # Hardcoded fallback
    return _hardcoded_transit_lookup(planet_norm, house_num)


# ═══════════════════════════════════════════════════════════════════════════
# Self-evolving memory subsystem  (/memory/*)
# auto_mapper · schema_mutator · session_memory · ingest pipeline
# ═══════════════════════════════════════════════════════════════════════════


class MemoryIngestRequest(BaseModel):
    """Trigger ingestion of new content into the knowledge graph."""

    content: str | None = Field(
        default=None,
        description="Raw markdown/text to ingest. Ignored when path is set.",
    )
    path: str | None = Field(
        default=None,
        description="Filesystem path to a markdown file under Gyan/ (or absolute).",
    )
    label: str | None = Field(
        default=None,
        description="Optional document label when ingesting raw content.",
    )
    threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for auto-mapped links.",
    )
    skip_refresh: bool = Field(
        default=False,
        description="If true, do not call KnowledgeEngine.trigger_global_refresh.",
    )
    dry_run: bool = Field(
        default=False,
        description="If true, map+mutate only — do not merge into graph.json.",
    )


class MemoryEvolveRequest(BaseModel):
    """Accept or reject pending schema mutation proposals."""

    action: Literal["accept", "reject", "accept_all", "reject_all", "list"] = Field(
        default="list",
        description="Decision action. 'list' returns pending proposals without changing them.",
    )
    proposal_id: str | None = Field(
        default=None,
        description="Required for accept/reject of a single proposal.",
    )
    note: str = Field(default="", description="Optional decision note.")


@app.post("/memory/ingest")
def memory_ingest(req: MemoryIngestRequest):
    """
    Trigger ingestion of new content.

    Accepts either a filesystem `path` to a markdown file, or raw `content`
    (written to a temp batch under memory-state/). Runs extract → merge →
    auto_mapper → schema_mutator → KnowledgeEngine.trigger_global_refresh().
    """
    from pathlib import Path as _Path

    try:
        from knowledge_engine import memory_state
        from knowledge_engine.auto_mapper import AutoMapper
        from knowledge_engine.schema_mutator import SchemaMutator
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"memory subsystem unavailable: {exc}"
        ) from exc

    graph_path = _Path(
        os.environ.get(
            "GRAPHIFY_GRAPH_PATH",
            str(
                _Path(__file__).resolve().parents[2]
                / "knowledge-graph"
                / "graphify-out"
                / "graph.json"
            ),
        )
    )

    # Resolve source markdown
    src_path: _Path | None = None
    cleanup_tmp = False
    if req.path:
        src_path = _Path(req.path).expanduser().resolve()
        if not src_path.exists():
            raise HTTPException(status_code=404, detail=f"path not found: {req.path}")
    elif req.content and req.content.strip():
        state_dir = _Path(
            os.environ.get(
                "MEMORY_STATE_DIR",
                str(graph_path.parent / "memory-state"),
            )
        )
        state_dir.mkdir(parents=True, exist_ok=True)
        tmp = state_dir / f"ingest_{int(time.time())}.md"
        title = (req.label or "inline ingest").strip()
        tmp.write_text(f"# {title}\n\n{req.content}", encoding="utf-8")
        src_path = tmp
        cleanup_tmp = True
    else:
        raise HTTPException(
            status_code=400, detail="provide either path or content"
        )

    # Reuse the watcher's Python extraction by importing the same heuristics
    # inline (avoid shelling out from the request path).
    try:
        text = src_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"cannot read source: {exc}") from exc

    def _slug(s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()[:60] or "node"

    doc_id = f"ingest_{_slug(src_path.stem)}"
    nodes: list[dict] = [
        {
            "id": doc_id,
            "label": req.label or src_path.stem.replace("_", " "),
            "file_type": "document",
            "source_file": str(src_path.name),
            "description": text[:400],
            "norm_label": (req.label or src_path.stem).lower(),
        }
    ]
    links: list[dict] = []
    heading_stack = [doc_id]
    seen = {doc_id}
    for i, line in enumerate(text.splitlines()):
        hm = re.match(r"^(#{1,4})\s+(.+)$", line.strip())
        if hm:
            level = len(hm.group(1))
            title = hm.group(2).strip()
            nid = f"{doc_id}_{_slug(title)}"
            base, n = nid, 2
            while nid in seen:
                nid = f"{base}_{n}"
                n += 1
            seen.add(nid)
            nodes.append(
                {
                    "id": nid,
                    "label": title,
                    "file_type": "concept",
                    "source_file": str(src_path.name),
                    "source_location": f"L{i+1}",
                    "description": title,
                    "norm_label": title.lower(),
                }
            )
            parent = heading_stack[min(level - 1, len(heading_stack) - 1)]
            links.append(
                {
                    "source": parent,
                    "target": nid,
                    "relation": "contains_section",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "source_file": str(src_path.name),
                    "weight": 1.0,
                }
            )
            heading_stack = heading_stack[:level] + [nid]
            continue
        bm = re.match(r"^[-*]\s+(.+)$", line.strip())
        if bm and heading_stack:
            claim = bm.group(1).strip()
            if len(claim) < 8:
                continue
            cid = f"{doc_id}_claim_{hashlib.sha1(claim.encode()).hexdigest()[:10]}"
            if cid in seen:
                continue
            seen.add(cid)
            nodes.append(
                {
                    "id": cid,
                    "label": claim[:160],
                    "file_type": "concept",
                    "source_file": str(src_path.name),
                    "description": claim,
                    "norm_label": claim[:160].lower(),
                }
            )
            links.append(
                {
                    "source": heading_stack[-1],
                    "target": cid,
                    "relation": "states_rule",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "source_file": str(src_path.name),
                    "weight": 1.0,
                }
            )

    added_nodes: list[dict] = []
    added_links: list[dict] = []
    if not req.dry_run and graph_path.exists():
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            existing_ids = {n.get("id") for n in data.get("nodes") or []}
            existing_link_keys = {
                (l.get("source"), l.get("target"), l.get("relation"))
                for l in data.get("links") or []
            }
            for n in nodes:
                if n.get("id") and n["id"] not in existing_ids:
                    data.setdefault("nodes", []).append(n)
                    existing_ids.add(n["id"])
                    added_nodes.append(n)
            for l in links:
                key = (l.get("source"), l.get("target"), l.get("relation"))
                if key in existing_link_keys:
                    continue
                if l.get("source") in existing_ids and l.get("target") in existing_ids:
                    data.setdefault("links", []).append(l)
                    existing_link_keys.add(key)
                    added_links.append(l)
            graph_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"graph merge failed: {exc}"
            ) from exc
    else:
        added_nodes, added_links = nodes, links

    map_nodes = added_nodes or nodes
    map_result: dict = {}
    try:
        mapper = AutoMapper(graph_path=graph_path, threshold=req.threshold)
        max_n = os.environ.get("AUTO_MAPPER_MAX_NODES")
        mapper.load_corpus(max_nodes=int(max_n) if max_n else None)
        map_result = mapper.map_and_store(map_nodes, threshold=req.threshold)
        if not req.dry_run and map_result.get("proposed_links"):
            try:
                data = json.loads(graph_path.read_text(encoding="utf-8"))
                existing_link_keys = {
                    (l.get("source"), l.get("target"), l.get("relation"))
                    for l in data.get("links") or []
                }
                existing_ids = {n.get("id") for n in data.get("nodes") or []}
                for l in map_result["proposed_links"]:
                    key = (l.get("source"), l.get("target"), l.get("relation"))
                    if key in existing_link_keys:
                        continue
                    if l.get("source") in existing_ids and l.get("target") in existing_ids:
                        data.setdefault("links", []).append(l)
                        existing_link_keys.add(key)
                graph_path.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            except Exception:
                pass
    except Exception as exc:
        map_result = {"meta": {"error": str(exc)}}

    mut_result: dict = {}
    try:
        mut = SchemaMutator(graph_path=graph_path)
        mut.load_corpus()
        mut_result = mut.propose_and_store(map_nodes, added_links or links)
    except Exception as exc:
        mut_result = {"meta": {"error": str(exc)}}

    refresh: dict = {"status": "skipped"}
    if not req.skip_refresh and not req.dry_run:
        ke = _ensure_knowledge_engine()
        if ke is not None:
            try:
                refresh = ke.trigger_global_refresh(
                    reason=f"memory/ingest:{src_path.name}"
                )
            except Exception as exc:
                refresh = {"status": "error", "error": str(exc)}
        else:
            refresh = {"status": "unavailable"}

    memory_state.log_ingest(
        {
            "source": str(src_path),
            "added_nodes": len(added_nodes),
            "added_links": len(added_links),
            "map_meta": map_result.get("meta"),
            "mutation_meta": mut_result.get("meta"),
            "refresh": refresh,
            "dry_run": req.dry_run,
        }
    )

    if cleanup_tmp:
        try:
            src_path.unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass

    return {
        "status": "ok",
        "dry_run": req.dry_run,
        "extracted": {"nodes": len(nodes), "links": len(links)},
        "merged": {"nodes": len(added_nodes), "links": len(added_links)},
        "map": map_result.get("meta"),
        "mutations": mut_result.get("meta"),
        "refresh": refresh,
        "proposed_links": len(map_result.get("proposed_links") or []),
        "duplicates": len(map_result.get("duplicates") or []),
        "contradictions": len(map_result.get("contradictions") or []),
    }


@app.get("/memory/map")
def memory_map(similarity: float = 0.75, top_k: int = 5, rebuild: bool = False):
    """
    Show auto-mapped relationships for the latest ingest batch.

    If no batch is stored yet (or rebuild=true), re-runs AutoMapper on the
    latest_batch_nodes using the given similarity threshold.
    """
    try:
        from knowledge_engine import memory_state
        from knowledge_engine.auto_mapper import AutoMapper
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"memory subsystem unavailable: {exc}"
        ) from exc

    similarity = max(0.0, min(1.0, float(similarity)))
    top_k = max(1, min(int(top_k), 50))
    state = memory_state.get()
    latest = state.get("latest_map")
    batch = state.get("latest_batch_nodes") or []

    if rebuild or latest is None or (
        latest.get("meta", {}).get("threshold") != similarity and batch
    ):
        if not batch:
            # Fall back to a tiny demo batch so the endpoint is never empty-useless
            from knowledge_engine.auto_mapper import _demo_batch

            batch = _demo_batch()
        try:
            mapper = AutoMapper(threshold=similarity, top_k=top_k)
            max_n = os.environ.get("AUTO_MAPPER_MAX_NODES")
            mapper.load_corpus(max_nodes=int(max_n) if max_n else None)
            latest = mapper.map_and_store(batch, threshold=similarity, top_k=top_k)
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"auto_mapper failed: {exc}"
            ) from exc

    return {
        "similarity": similarity,
        "meta": (latest or {}).get("meta"),
        "matches": (latest or {}).get("matches") or [],
        "proposed_links": (latest or {}).get("proposed_links") or [],
        "duplicates": (latest or {}).get("duplicates") or [],
        "contradiction_count": len((latest or {}).get("contradictions") or []),
    }


@app.get("/memory/contradictions")
def memory_contradictions(limit: int = 100):
    """List auto-detected contradictions (latest batch + graph 'contradicts' links)."""
    limit = max(1, min(int(limit), 500))
    results: list[dict] = []

    try:
        from knowledge_engine import memory_state

        latest = (memory_state.get().get("latest_map") or {})
        results.extend(latest.get("contradictions") or [])
    except Exception:
        pass

    # Always include classical graph contradicts edges
    try:
        from graph_rag.graph import GraphRAG

        g = GraphRAG()
        for c in g.contradictions():
            results.append(
                {
                    "source_label": c.get("source"),
                    "target_label": c.get("target"),
                    "source_file": c.get("source_file"),
                    "flag": "CONTRADICTION",
                    "origin": "graph_link",
                }
            )
    except Exception:
        pass

    # Dedup by label pair
    seen: set[tuple] = set()
    unique: list[dict] = []
    for r in results:
        key = (
            str(r.get("new_id") or r.get("source_label") or ""),
            str(r.get("existing_id") or r.get("target_label") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
        if len(unique) >= limit:
            break

    return {"count": len(unique), "contradictions": unique}


@app.post("/memory/evolve")
def memory_evolve(req: MemoryEvolveRequest):
    """
    Accept or reject pending schema mutations produced by schema_mutator.

    Actions: list | accept | reject | accept_all | reject_all.
    """
    try:
        from knowledge_engine import memory_state
        from knowledge_engine.schema_mutator import SchemaMutator
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"memory subsystem unavailable: {exc}"
        ) from exc

    state = memory_state.get()
    pending = state.get("pending_mutations") or []

    if req.action == "list":
        # If nothing pending, offer a fresh full-graph discovery proposal
        if not pending:
            try:
                mut = SchemaMutator()
                mut.load_corpus()
                proposal = mut.propose_and_store(analyse_full_graph=True)
                state = memory_state.get()
                pending = state.get("pending_mutations") or []
                return {
                    "action": "list",
                    "pending_count": len(pending),
                    "pending": pending,
                    "latest_meta": (proposal or {}).get("meta"),
                    "relation_catalogue": (proposal or {}).get("relation_catalogue", [])[:20],
                    "existing_community_samples": (proposal or {}).get(
                        "existing_community_samples", []
                    )[:10],
                }
            except Exception as exc:
                return {
                    "action": "list",
                    "pending_count": 0,
                    "pending": [],
                    "error": str(exc),
                }
        return {
            "action": "list",
            "pending_count": len(pending),
            "pending": pending,
            "latest_meta": (state.get("latest_mutations") or {}).get("meta"),
        }

    if req.action in ("accept_all", "reject_all"):
        result = memory_state.decide_all(
            accept=(req.action == "accept_all"), note=req.note
        )
        return {"action": req.action, **result}

    if req.action in ("accept", "reject"):
        if not req.proposal_id:
            raise HTTPException(
                status_code=400, detail="proposal_id is required for accept/reject"
            )
        result = memory_state.decide_mutation(
            req.proposal_id, accept=(req.action == "accept"), note=req.note
        )
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return {"action": req.action, **result}

    raise HTTPException(status_code=400, detail=f"unknown action: {req.action}")


@app.get("/memory/query")
def memory_query(q: str = "", top_k: int = 8, graph: bool = True):
    """
    Semantic search across session memory (CONTEXT.md) + knowledge graph.

    Example: GET /memory/query?q=transit+scoring
    """
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query parameter q is required")
    top_k = max(1, min(int(top_k), 50))

    try:
        from knowledge_engine.session_memory import hybrid_memory_query
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"session_memory unavailable: {exc}"
        ) from exc

    try:
        result = hybrid_memory_query(query, top_k=top_k, include_graph=graph)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"query failed: {exc}") from exc

    # Also try KnowledgeEngine vector/keyword search when available
    ke_hits: list = []
    ke = _ensure_knowledge_engine()
    if ke is not None:
        try:
            ke_hits = ke.search(query, top_k=top_k) or []
        except Exception:
            ke_hits = []

    return {
        "query": query,
        "top_k": top_k,
        "session_memory": result.get("session_memory"),
        "functions": result.get("top_functions") or [],
        "gotchas": result.get("top_gotchas") or [],
        "patterns": result.get("top_patterns") or [],
        "graph_hits": result.get("graph_hits") or [],
        "knowledge_engine_hits": ke_hits,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
