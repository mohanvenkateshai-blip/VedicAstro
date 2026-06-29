"""Read-only loader for DeepSeek V4 graph (experimental)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from graph_rag.production_floor import experimental_vs_production

_DIR = Path(__file__).resolve().parent
_DEFAULT = _DIR / "graph-deepseek.json"
_FALLBACK = _DIR.parent.parent / "knowledge-graph" / "graphify-out" / "graph-deepseek.json"


def deepseek_graph_stats() -> dict | None:
    path = None
    env = os.environ.get("CVCE_GRAPH_DEEPSEEK_PATH", "").strip()
    if env and Path(env).is_file():
        path = Path(env)
    elif _DEFAULT.is_file():
        path = _DEFAULT
    elif _FALLBACK.is_file():
        path = _FALLBACK
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = len(data.get("nodes", []))
    return {
        "available": True,
        "loaded": True,
        "source": path.name,
        "nodes": nodes,
        "links": len(data.get("links", [])),
        "hyperedges": len(data.get("hyperedges", [])),
        **experimental_vs_production(nodes),
    }
