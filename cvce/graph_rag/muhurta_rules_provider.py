"""
GraphRAG muhurta rules provider — load vara/tithi yoga rules from graph.json.
"""

from __future__ import annotations

import os
from typing import Optional

from .graph import GraphRAG


def graph_muhurta_enabled() -> bool:
    raw = os.environ.get("CVCE_GRAPH_AS_MUHURTA", "1")
    return raw.strip().lower() in ("1", "true", "yes", "on")


class GraphMuhurtaRules:
    _instance: Optional["GraphMuhurtaRules"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._built = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_built", False):
            return
        self.graph = GraphRAG()
        self._yoga_nodes = [
            n for n in self.graph.nodes
            if n.get("is_muhurta_yoga") or "muhurta_yoga" in n.get("id", "")
        ]
        self._combo_nodes = [
            n for n in self.graph.nodes
            if n.get("vara_lord") and (n.get("tithi_group") or n.get("tithi_num"))
        ]
        self._sav_bands = [
            n for n in self.graph.nodes
            if n.get("domain") == "ashtakavarga" or "sav_band" in n.get("id", "")
        ]
        self._built = True

    def yoga_hits(self, vara_lord: str, tithi_group: str, tithi_tip: int) -> list[dict]:
        hits: list[dict] = []
        for n in self._combo_nodes:
            if n.get("vara_lord") != vara_lord:
                continue
            tg = n.get("tithi_group")
            tn = n.get("tithi_num")
            if tg and tg == tithi_group:
                hits.append({
                    "name": n.get("label", "").split(":")[0].strip(),
                    "nature": n.get("verdict", n.get("nature", "mixed")),
                    "source": n.get("source_file", "graph.json"),
                    "detail": n.get("label", ""),
                })
            elif tn and int(tn) == tithi_tip:
                hits.append({
                    "name": n.get("label", "").split(":")[0].strip(),
                    "nature": n.get("verdict", n.get("nature", "mixed")),
                    "source": n.get("source_file", "graph.json"),
                    "detail": n.get("label", ""),
                })
        return hits

    def sav_band_for_bindus(self, bindus: int) -> dict | None:
        for n in self._sav_bands:
            lo = n.get("min_bindus")
            hi = n.get("max_bindus")
            if lo is None:
                continue
            hi = hi if hi is not None else 999
            if lo <= bindus <= hi:
                return {
                    "band": n.get("label"),
                    "verdict": n.get("verdict", "neutral"),
                    "source": n.get("source_file", "graph.json"),
                }
        return None


def active_muhurta_rules() -> GraphMuhurtaRules | None:
    if not graph_muhurta_enabled():
        return None
    try:
        return GraphMuhurtaRules()
    except Exception:
        return None
