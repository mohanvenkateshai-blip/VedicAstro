"""Read-only loader for DeepSeek V4 graph (experimental)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

_DIR = Path(__file__).resolve().parent
_DEFAULT = _DIR / "graph-deepseek.json"
_FALLBACK = _DIR.parent.parent / "knowledge-graph" / "graphify-out" / "graph-deepseek.json"
_BASELINE = 4253


def deepseek_graph_stats() -> Optional[dict]:
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
        "baseline_nodes": _BASELINE,
        "beats_baseline": nodes > _BASELINE,
        "delta_nodes": nodes - _BASELINE,
    }
