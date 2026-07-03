"""Self-contained Supabase REST helpers for the KnowledgeEngine store.

Vendored into cvce/ (stdlib urllib only) so the deployed image has ZERO
dependency on the repo-root scripts/ directory — which is NOT in the CVCE
Docker build context, and whose absence silently disabled the Supabase-
backed KnowledgeEngine in production (import of scripts/supabase_corpus_sync
threw at store init → engine None → /knowledge/* 503, while everything
worked locally because scripts/ was on the path). Also avoids shelling out
to curl (not guaranteed present in python:3.12-slim).
"""

from __future__ import annotations

import json as _json
import os
import time
import urllib.error
import urllib.request


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        v = os.environ.get(k, "").strip()
        if v:
            out[k] = v
    return out


def api_request(
    env: dict[str, str],
    method: str,
    path: str,
    body: bytes | None = None,
    headers: dict | None = None,
    *,
    timeout: int = 60,
) -> tuple[int, bytes]:
    """Minimal Supabase PostgREST call. Returns (status_code, body_bytes).
    Retries transient 5xx / network errors with backoff (the same resilience
    the original curl-based helper had)."""
    url = env["SUPABASE_URL"].rstrip("/") + path
    key = env["SUPABASE_SERVICE_ROLE_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    if headers:
        h.update(headers)
    if body is not None and "Content-Type" not in h:
        h["Content-Type"] = "application/json"

    last_err = ""
    for attempt in range(6):
        req = urllib.request.Request(url, data=body, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            code = e.code
            payload = e.read()
            if code >= 500 and attempt < 5:
                time.sleep(2**attempt)
                continue
            return code, payload
        except Exception as e:  # network / timeout
            last_err = str(e)[:300]
            if attempt < 5:
                time.sleep(2**attempt)
    raise RuntimeError(f"supabase request failed after retries: {last_err}")


# Convenience for JSON callers.
def api_json(env, method, path, obj=None, headers=None, **kw):
    body = _json.dumps(obj).encode() if obj is not None else None
    code, raw = api_request(env, method, path, body, headers, **kw)
    try:
        return code, _json.loads(raw) if raw else None
    except Exception:
        return code, None
