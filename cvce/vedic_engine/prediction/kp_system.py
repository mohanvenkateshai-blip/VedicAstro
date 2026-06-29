"""
KP System (Krishnamurti Paddhati) engine — Placidus cusps with star/sub lords.

Registers with KnowledgeEngine so KP significations and graph-backed sub-lord
rules reload when the knowledge graph updates.
"""

from __future__ import annotations

_kp_rules_version: str | None = None
_kp_registered = False
_signification_cache: dict[str, dict] = {}


def _clear_kp_knowledge_caches() -> None:
    """Drop KP graph caches so cusp significations reload from the latest corpus."""
    _signification_cache.clear()
    try:
        from graph_rag.graph import GraphRAG

        GraphRAG()._loaded = False
    except ImportError:
        pass
    try:
        from knowledge_engine.integration import get_knowledge_engine

        ke = get_knowledge_engine()
        if hasattr(ke.store, "_graph"):
            ke.store._graph = None  # type: ignore[attr-defined]
    except Exception:
        pass


def _on_kp_refresh(new_version: str) -> None:
    global _kp_rules_version
    _kp_rules_version = new_version
    _clear_kp_knowledge_caches()


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


_register_kp_engine()
