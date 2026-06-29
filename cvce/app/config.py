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


class Settings:
    """Process-wide settings, resolved once from the environment."""

    # Server
    HOST: str = os.environ.get("CVCE_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("CVCE_PORT", "8400"))

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
