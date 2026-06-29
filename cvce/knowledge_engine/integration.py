"""
KnowledgeEngine Integration Layer

This module is the **official gateway** for all code that needs access to the
Vedic Knowledge Graph. It ensures that every consumer goes through the central
KnowledgeEngine for health checks, invalidation, and versioning.

All new code should import from here instead of directly from `graph_rag`.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from .engine import KnowledgeEngine


@lru_cache(maxsize=1)
def get_knowledge_engine() -> KnowledgeEngine:
    """
    Singleton accessor for KnowledgeEngine.

    Defaults to Supabase-backed store when running in production context
    (detected via presence of Supabase credentials or KE_USE_SUPABASE=1).
    Falls back to file-based store for local development.
    """
    use_supabase = (
        os.environ.get("KE_USE_SUPABASE", "").lower() in ("1", "true")
        or bool(os.environ.get("SUPABASE_URL"))
    )
    if use_supabase:
        version = os.environ.get("CORPUS_GRAPH_VERSION", "newbooks-v1")
        return KnowledgeEngine.with_supabase(graph_version=version)
    return KnowledgeEngine()


# ------------------------------------------------------------------ #
# Safe Access Wrappers (Preferred API)
# ------------------------------------------------------------------ #

def get_safe_graph():
    """Returns the validated GraphRAG instance or raises if unhealthy."""
    ke = get_knowledge_engine()
    return ke.get_graph()


def get_safe_transit_rules():
    """Preferred way to get current validated transit rules."""
    ke = get_knowledge_engine()
    return ke.get_safe_rules("transit")


def get_safe_muhurta_rules():
    """Preferred way to get current validated muhurta rules."""
    ke = get_knowledge_engine()
    return ke.get_safe_rules("muhurta")


def get_safe_knowledge(engine_name: str = "unknown") -> Dict[str, Any]:
    """Returns a safe snapshot of current knowledge state."""
    ke = get_knowledge_engine()
    return ke.get_safe_knowledge(engine_name)


def is_knowledge_healthy() -> bool:
    """Quick health check for the entire knowledge layer."""
    ke = get_knowledge_engine()
    return ke.is_knowledge_healthy()


# ------------------------------------------------------------------ #
# Prediction Enhancement (via KnowledgeEngine)
# ------------------------------------------------------------------ #

def get_prediction_enhancer():
    """Returns a PredictionEnhancer that is aware of the KnowledgeEngine."""
    ke = get_knowledge_engine()
    # Create enhancer using the validated graph from KnowledgeEngine
    from graph_rag.enhancer import PredictionEnhancer
    enhancer = PredictionEnhancer()
    # Ensure enhancer uses the same graph instance as KE when possible
    if hasattr(ke.store, "_graph") and ke.store._graph is not None:
        enhancer.graph = ke.store._graph  # type: ignore[attr-defined]
    return enhancer


def get_llm_narration(facts: dict, birth: dict) -> dict | None:
    """Generate optional LLM narration via the central KnowledgeEngine."""
    ke = get_knowledge_engine()
    return ke.get_llm_narration(facts, birth)
