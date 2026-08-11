"""GraphRAG — Knowledge-graph-powered Vedic prediction enhancer.

Implementation moved to the shared `vedic-knowledge` package. This module
re-exports the public API for backward compatibility.
"""

from .enhancer import PredictionEnhancer
from .graph import GraphRAG
from .rules_provider import GraphTransitRules, active_transit_rules, graph_rules_enabled

__all__ = [
    "GraphRAG",
    "PredictionEnhancer",
    "GraphTransitRules",
    "graph_rules_enabled",
    "active_transit_rules",
]
