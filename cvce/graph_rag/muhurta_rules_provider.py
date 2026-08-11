"""Shim — GraphMuhurtaRules lives in `vedic-knowledge`."""

from __future__ import annotations

from vedic_knowledge.graph.muhurta_rules import (  # noqa: F401
    GraphMuhurtaRules,
    active_muhurta_rules,
    graph_muhurta_enabled,
)

__all__ = ["GraphMuhurtaRules", "active_muhurta_rules", "graph_muhurta_enabled"]
