"""Production graph size floor — read from baked graph.json (Fly) or pinned fallback."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_GRAPH = Path(__file__).resolve().parent / "graph.json"
_FALLBACK_NODES = 23267


@lru_cache(maxsize=1)
def production_node_floor() -> int:
    if _GRAPH.is_file():
        data = json.loads(_GRAPH.read_text(encoding="utf-8"))
        return len(data.get("nodes", []))
    return _FALLBACK_NODES


def experimental_vs_production(node_count: int) -> dict:
    floor = production_node_floor()
    return {
        "production_floor_nodes": floor,
        "beats_production": node_count > floor,
        "delta_vs_production": node_count - floor,
    }
