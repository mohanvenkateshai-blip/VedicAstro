"""
GraphRAG rules provider — derive transit house tables from graph.json.

When CVCE_GRAPH_AS_RULES is enabled, gochar uses these graph-sourced rules
instead of hardcoded transit_rules.TRANSIT_HOUSES. Falls back to Python
tables if graph load fails or env is unset.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from .graph import GraphRAG
from vedic_engine.rules.transit_rules import TRANSIT_HOUSES

# Relation types extracted from Gochar Phaladeepika in graph.json
_GOOD = frozenset({
    "transit_in_house_gives_good",
    "transit_best_in",
})
_BAD = frozenset({
    "transit_in_house_gives_bad",
})
_WORST = frozenset({
    "transit_worst_in",
})
_MIXED = frozenset({
    "transit_in_house_gives_mixed",
})
# Aggregate benefic/malefic house-list nodes (is_auspicious_in / is_inauspicious_in)
_AUSPICIOUS = frozenset({"is_auspicious_in"})
_INAUSPICIOUS = frozenset({"is_inauspicious_in"})

_HOUSE_RE = re.compile(r"house_(\d+)$")


def _truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def graph_rules_enabled() -> bool:
    """True when /predict should use graph.json for transit house rules."""
    return _truthy("CVCE_GRAPH_AS_RULES", default=False)


class GraphTransitRules:
    """Build TRANSIT_HOUSES-shaped tables from graph gochar planet→house links."""

    _instance: Optional["GraphTransitRules"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._built = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_built", False):
            return
        self.graph = GraphRAG()
        self._tables: dict[str, dict] = {}
        self._build_tables()
        self._built = True

    def _planet_key(self, node_id: str) -> str | None:
        """Map gochar_phaladeepika_pulippani_sun → Sun."""
        if not node_id.startswith("gochar_phaladeepika_pulippani_"):
            return None
        tail = node_id.rsplit("_", 1)[-1]
        names = {
            "sun": "Sun", "moon": "Moon", "mars": "Mars", "mercury": "Mercury",
            "jupiter": "Jupiter", "venus": "Venus", "saturn": "Saturn",
            "rahu": "Rahu", "ketu": "Ketu",
        }
        return names.get(tail.lower())

    def _house_num(self, node_id: str) -> int | None:
        m = _HOUSE_RE.search(node_id)
        return int(m.group(1)) if m else None

    def _build_tables(self):
        planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        for p in planets:
            self._tables[p] = {
                "good": set(),
                "bad": set(),
                "worst": set(),
                "neutral": set(),
                "source": "graph.json",
            }

        for link in self.graph.links:
            rel = link.get("relation", "")
            src = link.get("source", "")
            tgt = link.get("target", "")
            planet = self._planet_key(src)
            house = self._house_num(tgt)
            if not planet or house is None:
                # Try reverse: house link from aggregate nodes
                continue
            tbl = self._tables.get(planet)
            if not tbl:
                continue
            if rel in _GOOD:
                tbl["good"].add(house)
            elif rel in _BAD:
                tbl["bad"].add(house)
            elif rel in _WORST:
                tbl["worst"].add(house)
            elif rel in _MIXED:
                tbl["neutral"].add(house)

        # Convert sets to sorted lists for JSON-serializable API
        for p, tbl in self._tables.items():
            for key in ("good", "bad", "worst", "neutral"):
                tbl[key] = sorted(tbl[key])

    def transit_houses(self, planet: str) -> dict:
        """Same shape as transit_rules.TRANSIT_HOUSES[planet]."""
        return self._tables.get(planet, {
            "good": [], "bad": [], "worst": [], "neutral": [],
            "source": "graph.json",
        })

    def house_quality(self, planet: str, house: int) -> tuple[str, str, int]:
        """Return (house_quality, verdict, score). Graph first; hardcoded Pulippani fallback."""
        rules = self.transit_houses(planet)
        hard = TRANSIT_HOUSES.get(planet, {})

        def classify(r: dict) -> tuple[str, str, int] | None:
            if house in r.get("worst", []):
                return "worst", "ashubh", -10
            if house in r.get("bad", []):
                return "bad", "ashubh", -5
            if house in r.get("good", []):
                return "good", "shubh", 7
            return None

        return classify(rules) or classify(hard) or ("neutral", "neutral", 0)

    def transit_effects(self, planet: str, house: int) -> list[str]:
        """Short house verdict lines only (no raw graph dump)."""
        quality, verdict, _ = self.house_quality(planet, house)
        if quality == "good":
            return [f"In {house}th from Janma Rasi — favourable (Pulippani Table 12)"]
        if quality == "bad":
            return [f"In {house}th from Janma Rasi — unfavourable (Pulippani Table 12)"]
        if quality == "worst":
            return [f"In {house}th from Janma Rasi — worst position; caution advised"]
        return [f"In {house}th from Janma Rasi — neutral house for {planet}"]

    @property
    def stats(self) -> dict:
        return {
            "planets": len(self._tables),
            "source": "graph.json",
            "enabled": graph_rules_enabled(),
        }


def active_transit_rules():
    """Return graph rules if enabled, else None (caller uses transit_rules)."""
    if not graph_rules_enabled():
        return None
    try:
        return GraphTransitRules()
    except Exception:
        return None
