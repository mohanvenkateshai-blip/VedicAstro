"""
Runtime configuration for the CVCE service.

Everything that differs between local dev, the standalone, and hosted
production is read from the environment here — no hardcoded origins, ports,
or secrets in the application code. A `.env` file (see `.env.example`) is
loaded if present, but real environment variables always win.
"""

from __future__ import annotations

import os
from functools import lru_cache


def _load_dotenv() -> None:
    """Minimal .env loader (avoids a hard dependency on python-dotenv).

    Only sets keys that are not already present in the real environment, so
    container/host-injected variables are never overridden by a checked-in file.
    """
    path = os.environ.get("CVCE_ENV_FILE", os.path.join(os.getcwd(), ".env"))
    if not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                os.environ.setdefault(key, val)
    except OSError:
        pass


_load_dotenv()


def _csv(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _choice(name: str, default: str, allowed: tuple[str, ...]) -> str:
    raw = os.environ.get(name, default).strip().lower()
    return raw if raw in allowed else default


class Settings:
    """Process-wide settings, resolved once from the environment."""

    # Server
    HOST: str = os.environ.get("CVCE_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("CVCE_PORT", "8400"))

    # Portal-to-service authentication. Production fails closed by default;
    # local development remains unauthenticated unless a token is configured
    # or CVCE_REQUIRE_SERVICE_AUTH is explicitly enabled.
    ENVIRONMENT: str = os.environ.get("CVCE_ENVIRONMENT", "development").strip().lower()
    SERVICE_TOKEN: str = os.environ.get("CVCE_SERVICE_TOKEN", "").strip()
    SERVICE_AUTH_REQUIRED: bool = ENVIRONMENT in ("production", "prod") or _bool(
        "CVCE_REQUIRE_SERVICE_AUTH",
        False,
    )

    # CORS — comma-separated allowlist. Default is local dev only; production
    # MUST set CVCE_ALLOWED_ORIGINS to the portal origin(s).
    ALLOWED_ORIGINS: list[str] = _csv(
        "CVCE_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    )

    # Calculation defaults
    DEFAULT_AYANAMSA: str = os.environ.get("CVCE_DEFAULT_AYANAMSA", "LAHIRI")

    # Divisional charts (Shodashvarga) to compute in the canonical /chart payload.
    # Comma-separated D-numbers; defaults cover the most-used shodashvarga set.
    VARGAS: list[int] = [int(x) for x in _csv("CVCE_VARGAS", "1,2,3,4,7,9,10,12,16,24,30,60")]

    # Rate limiting (per client IP)
    RATE_LIMIT_REQUESTS: int = int(os.environ.get("CVCE_RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW: int = int(os.environ.get("CVCE_RATE_LIMIT_WINDOW", "60"))

    # GraphRAG: use graph.json for /predict transit house rules (default off → hardcoded fallback)
    GRAPH_AS_RULES: bool = os.environ.get("CVCE_GRAPH_AS_RULES", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    # Additive v2 forecast release controls. These are deliberately off until
    # the evaluation and release gates approve user-visible use.
    FORECAST_V2_MODE: str = _choice(
        "CVCE_FORECAST_V2_MODE", "off", ("off", "shadow", "on")
    )
    VERBALIZATION_V2: bool = _bool("CVCE_VERBALIZATION_V2", False)
    FORECAST_LEDGER_WRITE: bool = _bool("CVCE_FORECAST_LEDGER_WRITE", False)

    # Product Person Timeline ledger. Local development gets an ephemeral
    # append-only SQLite store; production must opt into a durable mounted path.
    TIMELINE_DB_PATH: str = os.environ.get(
        "CVCE_TIMELINE_DB_PATH",
        "/tmp/vedicastro-person-timeline.sqlite3"
        if ENVIRONMENT not in ("production", "prod")
        else "",
    ).strip()
    TIMELINE_WRITES_ENABLED: bool = _bool(
        "CVCE_TIMELINE_WRITES_ENABLED",
        ENVIRONMENT not in ("production", "prod"),
    )

    # Accuracy-first native Muhurta research surface. The service and portal
    # both fail closed unless their server-only gates are explicitly enabled.
    NATIVE_MUHURTA_RESEARCH_ENABLED: bool = _bool(
        "NATIVE_MUHURTA_RESEARCH_ENABLED", False
    )

    # Raw research is a separate, authenticated plane. It is disabled by
    # default and never falls back to the product service token or an in-memory
    # database. The research router validates these values again at request
    # time so a misconfigured production deployment fails closed.
    RESEARCH_MODE_ENABLED: bool = _bool("CVCE_RESEARCH_MODE_ENABLED", False)
    RESEARCH_DB_PATH: str = os.environ.get("CVCE_RESEARCH_DB_PATH", "").strip()
    RESEARCH_MOUNT_PATH: str = os.environ.get("CVCE_RESEARCH_MOUNT_PATH", "").strip()
    RESEARCH_SERVICE_TOKEN: str = os.environ.get(
        "CVCE_RESEARCH_SERVICE_TOKEN", ""
    ).strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
