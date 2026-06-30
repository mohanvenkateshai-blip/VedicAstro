"""
KP System (Krishnamurti Paddhati) engine — Placidus cusps with star/sub lords.

Registers with KnowledgeEngine so KP significations and graph-backed sub-lord
rules reload when the knowledge graph updates.

Revive pulls context from Jaimini/Prasna structured texts (related classical sources).
"""

from __future__ import annotations

from knowledge_engine.integration import get_structured_book

_kp_rules_version: str | None = None
_kp_registered = False
_signification_cache: dict[str, dict] = {}
_kp_structured_books: dict[str, dict] = {}

# Related structured sources for KP context (Jaimini + Prasna texts; no dedicated KP handbook in corpus)
_kp_book_index: dict[str, str] = {
    "JaiminiSutras": "Jaimini_Sutras",
    "JaiminiPredicting": "Predicting_Through_Jaimini_Astrology",
    "JaiminiUpadesa": "rath_s_jaimini_maharishis_upadesa_sutra",
    "PrasnaMarga1": "Prasna_Marga_Part_1",
    "PrasnaMarga2": "Prasna_Marga_Part_2",
    "JaiminiMandook": "jaimini_astrology_calculation_of_mandook_dasha_with_a_case_study_compress",
}


def _clear_kp_knowledge_caches() -> None:
    """Drop KP graph caches so cusp significations reload from the latest corpus."""
    _signification_cache.clear()
    try:
        from knowledge_engine.integration import clear_knowledge_engine_cache

        clear_knowledge_engine_cache()
    except Exception:
        pass
    try:
        from graph_rag.graph import GraphRAG
        GraphRAG()._loaded = False
    except Exception:
        pass


def _on_kp_refresh(new_version: str) -> None:
    global _kp_rules_version, _kp_structured_books
    _kp_rules_version = new_version
    _clear_kp_knowledge_caches()
    _kp_structured_books = {}
    # Revive: load relevant structured (Jaimini/Prasna) for KP cross-reference context
    for key, book_id in _kp_book_index.items():
        try:
            data = get_structured_book(book_id)
            if data:
                _kp_structured_books[book_id] = data
        except Exception:
            pass


def _register_kp_engine() -> None:
    global _kp_registered
    if _kp_registered:
        return
    try:
        from knowledge_engine.integration import get_knowledge_engine

        get_knowledge_engine().register_engine("kp_system", on_refresh=_on_kp_refresh)
        _kp_registered = True
    except Exception:
        pass


_register_kp_engine()


def _ensure_kp_registered() -> None:
    if not _kp_registered:
        _register_kp_engine()


def cached_kp_significations(cache_key: str, loader) -> dict:
    """Return cached KP significations, or compute and store via ``loader``."""
    _ensure_kp_registered()
    if cache_key in _signification_cache:
        return _signification_cache[cache_key]
    result = loader()
    _signification_cache[cache_key] = result
    return result


def get_kp_structured_context() -> dict:
    """Return loaded structured books for KP (used for audits/provenance)."""
    _ensure_kp_registered()
    return {
        "version": _kp_rules_version,
        "books_loaded": list(_kp_structured_books.keys()),
        "book_count": len(_kp_structured_books),
    }


_register_kp_engine()
