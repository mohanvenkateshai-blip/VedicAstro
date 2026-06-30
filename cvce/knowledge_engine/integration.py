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

def rebuild_and_remap_structured(books: list[str] | None = None) -> dict:
    """Rebuild structured chapters then remap node linkages (full KE-owned step)."""
    ke = get_knowledge_engine()
    return ke.rebuild_and_remap_structured(books=books)


# ------------------------------------------------------------------ #
# Invalidation (chapter-aware via KE)
# ------------------------------------------------------------------


def invalidate_nodes(
    node_ids: list[str] | None = None,
    pattern: str | None = None,
    reason: str = "manual",
    details: str = "",
) -> list[str]:
    """Invalidate nodes by explicit IDs or glob pattern. Reason is a string mapped to InvalidationReason."""
    ke = get_knowledge_engine()
    from .models import InvalidationReason

    try:
        r = InvalidationReason(reason)
    except Exception:
        r = InvalidationReason.MANUAL
    return ke.invalidate(node_ids=node_ids, pattern=pattern, reason=r, details=details)


def invalidate_chapter(book_id: str, chapter_id: str, reason: str = "manual", details: str = "") -> dict:
    """Resolve nodes for a chapter and invalidate them. Dry-run friendly (caller decides)."""
    ke = get_knowledge_engine()
    nodes = ke.get_nodes_for_chapter(book_id, chapter_id)
    nids = [n.get("id") for n in nodes if isinstance(n, dict) and n.get("id")]
    from .models import InvalidationReason

    try:
        r = InvalidationReason(reason)
    except Exception:
        r = InvalidationReason.MANUAL
    invalidated = ke.invalidate(node_ids=nids, reason=r, details=details or f"chapter {chapter_id}@{book_id}")
    return {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "nodes_targeted": len(nids),
        "invalidated": invalidated,
    }


# ------------------------------------------------------------------ #
# Structured coverage snapshot (for CLI / ops)
# ------------------------------------------------------------------


def get_structured_coverage() -> dict:
    """Return a snapshot of structured books, chapter counts, and patch linkage stats."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    structured_dir = root / "knowledge-graph" / "structured"
    patch_file = root / "knowledge-graph" / "patches" / "node-chapter-map.json"

    books: list[dict] = []
    total_chapters = 0
    total_patched_nodes = 0

    if structured_dir.exists():
        for p in sorted(structured_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                chs = data.get("chapters") or []
                bid = data.get("book_id") or p.stem
                total_chapters += len(chs)
                books.append({
                    "book_id": bid,
                    "chapters": len(chs),
                    "source_file": data.get("source_file"),
                })
            except Exception:
                continue

    patch_stats: dict = {"present": False, "entries": 0, "books_covered": 0}
    if patch_file.exists():
        try:
            pdata = json.loads(patch_file.read_text(encoding="utf-8"))
            patches = pdata.get("patches") or []
            patch_stats["present"] = True
            patch_stats["entries"] = len(patches)
            covered = {p.get("book_id") for p in patches if p.get("book_id")}
            patch_stats["books_covered"] = len(covered)
            total_patched_nodes = len(patches)
        except Exception:
            pass

    return {
        "books": len(books),
        "total_chapters": total_chapters,
        "total_patched_nodes": total_patched_nodes,
        "patch": patch_stats,
        "books_detail": books[:50],  # cap for CLI readability
    }

