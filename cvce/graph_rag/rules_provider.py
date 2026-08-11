"""Shim — GraphTransitRules lives in `vedic-knowledge`."""

from __future__ import annotations

from vedic_knowledge.graph.rules_provider import *  # noqa: F403
from vedic_knowledge.graph.rules_provider import (  # noqa: F401
    GraphTransitRules,
    active_transit_rules,
    graph_rules_enabled,
    rebuild_transit_rules,
)
