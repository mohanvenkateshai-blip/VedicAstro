"""
KnowledgeEngine Integration Layer

This module is the **official gateway** for all code that needs access to the
Vedic Knowledge Graph. It ensures that every consumer goes through the central
KnowledgeEngine for health checks, invalidation, and versioning.

All new code should import from here instead of directly from `graph_rag`.
"""

from __future__ import annotations

import os
from typing import Any

from .engine import KnowledgeEngine


_KE: KnowledgeEngine | None = None


def clear_knowledge_engine_cache() -> None:
    """Drop the singleton so the next call rebuilds store caches."""
    global _KE
    _KE = None


def get_knowledge_engine() -> KnowledgeEngine:
    """
    Singleton accessor for KnowledgeEngine.

    Defaults to Supabase-backed store when running in production context
    (detected via presence of Supabase credentials or KE_USE_SUPABASE=1).
    Falls back to file-based store for local development.

    Uses a module global (with double-check) instead of lru_cache to ensure
    the exact same instance is returned even across import contexts and
    during import-time registration side-effects from dependent engines.
    """
    global _KE
    if _KE is not None:
        return _KE
    use_supabase = os.environ.get("KE_USE_SUPABASE", "").lower() in ("1", "true") or bool(
        os.environ.get("SUPABASE_URL")
    )
    if use_supabase:
        version = os.environ.get("CORPUS_GRAPH_VERSION", "newbooks-v1")
        _KE = KnowledgeEngine.with_supabase(graph_version=version)
    else:
        _KE = KnowledgeEngine()
    return _KE


# Back-compat shims for code that expects lru_cache interface (e.g. performance_monitor)
def _compat_cache_clear():
    clear_knowledge_engine_cache()


class _CompatCacheInfo:
    hits = 0
    misses = 0
    maxsize = 1
    currsize = 1 if _KE is not None else 0


def _compat_cache_info():
    _CompatCacheInfo.currsize = 1 if _KE is not None else 0
    return _CompatCacheInfo()


get_knowledge_engine.cache_clear = _compat_cache_clear
get_knowledge_engine.cache_info = _compat_cache_info


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


def get_safe_knowledge(engine_name: str = "unknown") -> dict[str, Any]:
    """Returns a safe snapshot of current knowledge state."""
    ke = get_knowledge_engine()
    return ke.get_safe_knowledge(engine_name)


def is_knowledge_healthy() -> bool:
    """Quick health check for the entire knowledge layer."""
    ke = get_knowledge_engine()
    return ke.is_knowledge_healthy()


def search_knowledge(query: str, top_k: int = 8) -> list[dict[str, Any]]:
    """
    Semantic + keyword hybrid retrieval over corpus chunks.

    Preferred API for any component that needs classical-text passage lookup.
    """
    ke = get_knowledge_engine()
    return ke.search(query, top_k=top_k)


def notify_embeddings_updated(chunk_count: int = 0) -> dict[str, Any]:
    """Clear embedding caches and notify registered engines."""
    ke = get_knowledge_engine()
    result = ke.on_embeddings_updated(chunk_count=chunk_count)
    clear_knowledge_engine_cache()
    return result


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


# ------------------------------------------------------------------ #
# Structured data access (KnowledgeEngine owns the organised chapter trees + node mappings)
# ------------------------------------------------------------------


def get_structured_book(book_id: str) -> dict | None:
    """Clean chapter/subtitle tree + linked KE nodes for a source book (authoritative)."""
    ke = get_knowledge_engine()
    return ke.get_structured_book(book_id)


def get_nodes_for_chapter(book_id: str, chapter_id: str) -> list[dict]:
    """KE graph nodes that belong to one chapter inside a structured book."""
    ke = get_knowledge_engine()
    return ke.get_nodes_for_chapter(book_id, chapter_id)


def get_hierarchy_for_node(node_id: str) -> dict | None:
    """Reverse map: which book/chapter/section a given KE node was mapped into."""
    ke = get_knowledge_engine()
    return ke.get_hierarchy_for_node(node_id)


def rebuild_structured_library(books: list[str] | None = None) -> dict:
    """Force rebuild of the organised chapter JSONs (scripts/build_structured_library.py)."""
    ke = get_knowledge_engine()
    return ke.rebuild_structured_library(books=books)


def remap_nodes_to_structured(books: list[str] | None = None) -> dict:
    """Recompute node→chapter linkages (scripts/map_nodes_to_structured.py)."""
    ke = get_knowledge_engine()
    return ke.remap_nodes_to_structured(books=books)
