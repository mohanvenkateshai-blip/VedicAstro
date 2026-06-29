"""
Prashna (Horary) engine — chart cast for the query moment with graph-backed insights.

Registers with KnowledgeEngine so horary citation caches reload when the graph updates.
"""

from __future__ import annotations

_prashna_rules_version: str | None = None
_prashna_registered = False
_horary_insight_cache: dict[str, list] = {}
_enhancer = None


def _clear_prashna_knowledge_caches() -> None:
    """Drop horary graph caches so the next prashna run reloads classical sources."""
    global _enhancer
    _horary_insight_cache.clear()
    _enhancer = None
    try:
        from graph_rag.graph import GraphRAG

        GraphRAG()._loaded = False
    except ImportError:
        pass
    try:
        from graph_rag.rules_provider import GraphTransitRules

        GraphTransitRules._instance = None
    except ImportError:
        pass
    try:
        from knowledge_engine.integration import get_knowledge_engine

        ke = get_knowledge_engine()
        if hasattr(ke.store, "_graph"):
            ke.store._graph = None  # type: ignore[attr-defined]
    except Exception:
        pass


def _on_prashna_refresh(new_version: str) -> None:
    global _prashna_rules_version
    _prashna_rules_version = new_version
    _clear_prashna_knowledge_caches()


def _register_prashna_engine() -> None:
    global _prashna_registered
    if _prashna_registered:
        return
    try:
        from knowledge_engine.integration import get_knowledge_engine

        get_knowledge_engine().register_engine("prashna", on_refresh=_on_prashna_refresh)
        _prashna_registered = True
    except Exception:
        pass


_register_prashna_engine()


def _ensure_prashna_registered() -> None:
    if not _prashna_registered:
        _register_prashna_engine()


def get_prashna_enhancer():
    """Lazy enhancer for horary graph citations (rebuilt after knowledge refresh)."""
    global _enhancer
    _ensure_prashna_registered()
    if _enhancer is None:
        from knowledge_engine.integration import get_prediction_enhancer

        _enhancer = get_prediction_enhancer()
    return _enhancer


def cached_horary_insights(cache_key: str, loader) -> list:
    """Return cached horary graph matches, or compute and store via ``loader``."""
    _ensure_prashna_registered()
    if cache_key in _horary_insight_cache:
        return _horary_insight_cache[cache_key]
    result = loader()
    _horary_insight_cache[cache_key] = result
    return result


_register_prashna_engine()
