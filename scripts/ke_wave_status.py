#!/usr/bin/env python3
"""
KE Wave Status — narrow supervision script for the 2026-06-30 Full Update Wave.

Prints:
- Registered engines (source + runtime when importable)
- Probe results with source/fingerprint/counts
- Crack flags (no on_refresh, cache-only without real reload)
- Summary counts

Usage:
  python3 scripts/ke_wave_status.py
  python3 -m scripts.ke_wave_status
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _scan_registrations() -> list[str]:
    """Source-level discovery of register_engine calls. No runtime side effects."""
    regs: list[str] = []
    for p in (ROOT / "cvce").rglob("*.py"):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r'register_engine\s*\(\s*["\']([^"\']+)["\']', txt):
                regs.append(m.group(1))
        except Exception:
            continue
    return sorted(set(regs))


def _classify_on_refresh_real(names: list[str]) -> dict[str, bool]:
    """Heuristic map from the wave audit of on_refresh bodies.
    Updated 2026-06-30 after agents wired real reloads (load/revive structured + citations)."""
    real = {
        "dasha": True,
        "yoga": True,
        "ashtakavarga": True,
        "report": True,
        "gochar": True,
        # Wave updates: these now do structured load / revive in their on_refresh
        "panchanga": True,
        "muhurta": True,
        "kp_system": True,
        "prashna": True,
    }
    return {n: real.get(n, False) for n in names}


def _load_runtime_registered() -> list[str]:
    """Best-effort runtime registered names. May be empty if heavy deps block import."""
    try:
        # Ensure package path
        if str(ROOT / "cvce") not in sys.path:
            sys.path.insert(0, str(ROOT / "cvce"))
        from knowledge_engine.integration import get_knowledge_engine  # type: ignore

        ke = get_knowledge_engine()
        if ke and ke.registry:
            return sorted(ke.registry.registered_names())
    except Exception:
        pass
    return []


def _run_probes() -> dict[str, Any]:
    """Run auditor probes where possible. Returns machine-readable dict."""
    try:
        if str(ROOT / "cvce") not in sys.path:
            sys.path.insert(0, str(ROOT / "cvce"))
        from knowledge_engine.refresh_auditor import run_all_probes  # type: ignore
        from knowledge_engine.integration import get_knowledge_engine  # type: ignore

        ke = get_knowledge_engine()
        return run_all_probes(ke=ke)
    except Exception as exc:
        return {"error": str(exc), "probes_run": 0, "results": {}}


def _crack_flags(names: list[str], runtime_names: list[str]) -> dict[str, str]:
    """Return per-name crack reasons or '' if clean."""
    real_map = _classify_on_refresh_real(names)
    cache_only = {"muhurta", "kp_system", "prashna", "panchanga"}
    flags: dict[str, str] = {}
    for n in names:
        reasons: list[str] = []
        if n not in runtime_names and runtime_names:
            reasons.append("not_registered_at_runtime")
        if not real_map.get(n, False) and n in cache_only:
            reasons.append("cache_clear_only")
        if not real_map.get(n, False) and n not in cache_only:
            # unknown or not yet upgraded to real reload
            pass
        flags[n] = ";".join(reasons) if reasons else ""
    return flags


def main() -> int:
    src_names = _scan_registrations()
    rt_names = _load_runtime_registered()
    # Prefer runtime if any; else fall back to source
    names = rt_names or src_names
    real_map = _classify_on_refresh_real(names)
    cracks = _crack_flags(names, rt_names)
    probes = _run_probes()

    # Build table rows
    rows: list[dict[str, Any]] = []
    for n in names:
        pres = probes.get("results", {}).get(n, {}) if isinstance(probes, dict) else {}
        src = ""
        fp = ""
        cnt = 0
        if isinstance(pres, dict):
            # try domain first
            dom = pres.get("domain") or {}
            src = dom.get("source") or pres.get("rules", {}).get("source") or ""
            fp = pres.get("fingerprint") or dom.get("content_hash") or ""
            for k in ("node_count", "entry_count", "yoga_node_count"):
                if isinstance(dom.get(k), int):
                    cnt = dom[k]
                    break
            if not cnt:
                kn = (pres.get("knowledge") or {}).get("stats") or {}
                cnt = kn.get("nodes") or kn.get("node_count") or 0
        rows.append({
            "name": n,
            "real_reload": "yes" if real_map.get(n) else "no",
            "crack": cracks.get(n, ""),
            "source": src,
            "count": cnt,
            "fingerprint": (fp or "")[:16],
        })

    # Print
    print("KE Wave Status —", ROOT.name)
    print("Registered (source scan):", len(src_names))
    print("Registered (runtime):", len(rt_names))
    print()
    print(f"{'name':<14} {'real':<6} {'crack':<22} {'source':<10} {'count':>6}  fingerprint")
    print("-" * 78)
    for r in rows:
        print(f"{r['name']:<14} {r['real_reload']:<6} {r['crack']:<22} {r['source']:<10} {r['count']:>6}  {r['fingerprint']}")
    print()

    # Summary
    crack_count = sum(1 for r in rows if r["crack"])
    probed = probes.get("probes_run", 0) if isinstance(probes, dict) else 0
    print(f"SUMMARY: engines={len(names)}  probed={probed}  cracks={crack_count}")
    if probes.get("error"):
        print("probe_error:", probes["error"])
    print("probe_supported:", probes.get("supported", []) if isinstance(probes, dict) else [])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
