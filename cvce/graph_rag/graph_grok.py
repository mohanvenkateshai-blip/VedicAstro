"""
graph_grok.py — read-only loader for experimental Grok-enriched graph.

Production /predict uses graph.json. This module only powers /predict/health/grok
stats until Grok graph is promoted.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from graph_rag.production_floor import experimental_vs_production

_DIR = Path(__file__).resolve().parent
_DEFAULT_PATH = _DIR / "graph-grok.json"
_FALLBACK_PATH = _DIR.parent.parent / "knowledge-graph" / "graphify-out" / "graph-grok.json"


def _resolve_path() -> Path | None:
    env = os.environ.get("CVCE_GRAPH_GROK_PATH", "").strip()
    if env:
        p = Path(env)
        return p if p.is_file() else None
    if _DEFAULT_PATH.is_file():
        return _DEFAULT_PATH
    if _FALLBACK_PATH.is_file():
        return _FALLBACK_PATH
    return None


def grok_graph_available() -> bool:
    return _resolve_path() is not None


def grok_graph_stats() -> dict | None:
    path = _resolve_path()
    if path is None:
        return None
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    nodes = len(data.get("nodes", []))
    return {
        "available": True,
        "loaded": True,
        "source": path.name,
        "path": str(path),
        "nodes": nodes,
        "links": len(data.get("links", [])),
        "hyperedges": len(data.get("hyperedges", [])),
        **experimental_vs_production(nodes),
    }
