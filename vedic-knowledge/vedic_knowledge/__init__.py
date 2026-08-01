"""vedic-knowledge — shared GraphRAG + knowledge integration package.

Used by VedicAstro (cvce) and panchanga_muhurtha so both apps read the same
graph.json rules and citations.

Environment:
  GRAPH_JSON_PATH   Absolute path to graph.json (required in production).
  GRAPH_VERSION     Expected version / built_at_commit; startup fails on mismatch
                    when enforce_graph_version() is called with strict=True.
  GRAPHIFY_GRAPH_PATH  Legacy alias for GRAPH_JSON_PATH.
  CORPUS_GRAPH_VERSION Legacy KE version tag (Supabase store).
"""

from __future__ import annotations

__version__ = "0.1.0"

from .graph.graph import (
    GraphRAG,
    GraphVersionMismatchError,
    check_graph_version,
    read_graph_metadata,
    resolve_graph_path,
)
from .graph.rules_provider import GraphTransitRules, active_transit_rules, graph_rules_enabled
from .graph.muhurta_rules import GraphMuhurtaRules, active_muhurta_rules, graph_muhurta_enabled
from .graph.enhancer import PredictionEnhancer
from .knowledge.integration import (
    clear_knowledge_engine_cache,
    get_knowledge_engine,
    get_prediction_enhancer,
    get_safe_graph,
    get_safe_muhurta_rules,
    get_safe_transit_rules,
    is_knowledge_healthy,
    search_knowledge,
)


def get_knowledge_graph() -> GraphRAG:
    """Return the GraphRAG singleton (preferred public accessor)."""
    return GraphRAG()


def get_transit_rules():
    """Return active transit rules (graph-backed) or None."""
    return get_safe_transit_rules()


def get_muhurta_rules():
    """Return active muhurta rules (graph-backed) or None."""
    return get_safe_muhurta_rules()


def enforce_graph_version(expected: str | None = None, *, strict: bool = True) -> dict:
    """Build/startup gate: fail when GRAPH_VERSION mismatches graph metadata.

    Call from app startup (lifespan / main). When strict and mismatch → raises
    GraphVersionMismatchError so the process does not serve stale rules.
    """
    return check_graph_version(expected, strict=strict)


__all__ = [
    "__version__",
    "GraphRAG",
    "GraphVersionMismatchError",
    "GraphTransitRules",
    "GraphMuhurtaRules",
    "PredictionEnhancer",
    "get_knowledge_graph",
    "get_transit_rules",
    "get_muhurta_rules",
    "get_knowledge_engine",
    "get_safe_graph",
    "get_safe_transit_rules",
    "get_safe_muhurta_rules",
    "get_prediction_enhancer",
    "search_knowledge",
    "is_knowledge_healthy",
    "clear_knowledge_engine_cache",
    "check_graph_version",
    "enforce_graph_version",
    "read_graph_metadata",
    "resolve_graph_path",
    "active_transit_rules",
    "active_muhurta_rules",
    "graph_rules_enabled",
    "graph_muhurta_enabled",
]
