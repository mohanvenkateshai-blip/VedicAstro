"""
Prashna (Horary) engine — chart cast for the query moment with graph-backed insights.

Registers with KnowledgeEngine so horary citation caches reload when the graph updates.

Revive pulls from Prasna_Marga + Jaimini structured sources.
"""

from __future__ import annotations

from knowledge_engine.integration import get_structured_book

_prashna_rules_version: str | None = None
_prashna_registered = False
_horary_insight_cache: dict[str, list] = {}
_enhancer = None
_prashna_structured_books: dict[str, dict] = {}

# Primary structured sources for Prashna (horary) + related Jaimini
_prashna_book_index: dict[str, str] = {
    "PrasnaMarga1": "Prasna_Marga_Part_1",
    "PrasnaMarga2": "Prasna_Marga_Part_2",
    "JaiminiSutras": "Jaimini_Sutras",
    "JaiminiPredicting": "Predicting_Through_Jaimini_Astrology",
    "JaiminiUpadesa": "rath_s_jaimini_maharishis_upadesa_sutra",
    "JaiminiMandook": "jaimini_astrology_calculation_of_mandook_dasha_with_a_case_study_compress",
}


def _clear_prashna_knowledge_caches() -> None:
    """Drop horary graph caches so the next prashna run reloads classical sources."""
    global _enhancer
    _horary_insight_cache.clear()
    _enhancer = None
    try:
        from knowledge_engine.integration import clear_knowledge_engine_cache

        clear_knowledge_engine_cache()
    except Exception:
        pass
    # legacy direct (only if the central clear is unavailable)
    try:
        from graph_rag.graph import GraphRAG
        GraphRAG()._loaded = False
    except Exception:
        pass
    try:
        from graph_rag.rules_provider import GraphTransitRules
        GraphTransitRules._instance = None
    except Exception:
        pass


def _on_prashna_refresh(new_version: str) -> None:
    global _prashna_rules_version, _prashna_structured_books
    _prashna_rules_version = new_version
    _clear_prashna_knowledge_caches()
    _prashna_structured_books = {}
    # Revive: load Prasna_Marga + Jaimini structured for horary context/citations
    for key, book_id in _prashna_book_index.items():
        try:
            data = get_structured_book(book_id)
            if data:
                _prashna_structured_books[book_id] = data
        except Exception:
            pass


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


def get_prashna_structured_context() -> dict:
    """Return loaded structured books for Prashna (for audits + provenance)."""
    _ensure_prashna_registered()
    return {
        "version": _prashna_rules_version,
        "books_loaded": list(_prashna_structured_books.keys()),
        "book_count": len(_prashna_structured_books),
    }


_register_prashna_engine()
