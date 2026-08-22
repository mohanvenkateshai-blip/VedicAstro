"""
KnowledgeEngine Integration Layer (shared package).

Preferred gateway for graph + rules access. When the full KnowledgeEngine
stack (cvce/knowledge_engine) is available it delegates there; otherwise it
falls back to the in-package GraphRAG singleton so panchanga and other
lightweight consumers can search the graph without Supabase/KE deps.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_KE = None
_KE_LOCK = threading.RLock()
_KE_UNAVAILABLE = False


def clear_knowledge_engine_cache() -> None:
    """Drop the KE singleton so the next call rebuilds store caches."""
    global _KE, _KE_UNAVAILABLE
    with _KE_LOCK:
        _KE = None
        _KE_UNAVAILABLE = False
    try:
        from vedic_knowledge.graph.graph import GraphRAG

        GraphRAG.reset_singleton()
    except Exception:
        pass


def _try_import_ke_class():
    """Import KnowledgeEngine from host app if present."""
    try:
        from knowledge_engine.engine import KnowledgeEngine  # type: ignore

        return KnowledgeEngine
    except ImportError:
        pass
    try:
        # Some installs keep KE next to this package under cvce
        import sys
        from pathlib import Path

        cvce = Path(__file__).resolve().parents[3] / "cvce"
        if cvce.is_dir() and str(cvce) not in sys.path:
            sys.path.insert(0, str(cvce))
        from knowledge_engine.engine import KnowledgeEngine  # type: ignore

        return KnowledgeEngine
    except ImportError:
        return None


def get_knowledge_engine():
    """
    Singleton accessor for KnowledgeEngine when available.

    Returns None (does not raise) when KE stack is not installed — callers
    that need KE should check; safe_* helpers fall back to GraphRAG.
    """
    global _KE, _KE_UNAVAILABLE
    with _KE_LOCK:
        if _KE is not None:
            return _KE
        if _KE_UNAVAILABLE:
            return None
        KE = _try_import_ke_class()
        if KE is None:
            _KE_UNAVAILABLE = True
            logger.debug("vedic_knowledge: KnowledgeEngine not available; using GraphRAG fallback")
            return None
        try:
            # GRAPH_SOURCE=sqlite|supabase (B-56 durable fix — migration in
            # progress, see docs/graph-sqlite-migration-playbook_1.md).
            # Defaults to "supabase" (current live behavior unchanged) until
            # parity between the two backends is verified in prod; flip the
            # env var to cut over once scripts/check_graph_parity.py is clean.
            graph_source = os.environ.get("GRAPH_SOURCE", "supabase").strip().lower()
            if graph_source == "sqlite":
                _KE = KE.with_sqlite(db_path=os.environ.get("GRAPH_DB_PATH"))
            else:
                use_supabase = os.environ.get("KE_USE_SUPABASE", "").lower() in (
                    "1",
                    "true",
                ) or bool(os.environ.get("SUPABASE_URL"))
                if use_supabase:
                    version = os.environ.get(
                        "CORPUS_GRAPH_VERSION",
                        os.environ.get("GRAPH_VERSION", "newbooks-v1"),
                    )
                    _KE = KE.with_supabase(graph_version=version)
                else:
                    _KE = KE()
            return _KE
        except Exception as exc:
            logger.warning("vedic_knowledge: KnowledgeEngine init failed: %s", exc)
            _KE_UNAVAILABLE = True
            return None


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


get_knowledge_engine.cache_clear = _compat_cache_clear  # type: ignore[attr-defined]
get_knowledge_engine.cache_info = _compat_cache_info  # type: ignore[attr-defined]


# ------------------------------------------------------------------ #
# Safe Access Wrappers (Preferred API)
# ------------------------------------------------------------------ #


def get_safe_graph():
    """Returns GraphRAG (via KE when healthy, else direct singleton).

    Normalizes KE store objects that only expose get_nodes/get_links into a
    GraphRAG instance so callers can always use .search / .nodes / .links.
    """
    from vedic_knowledge.graph.graph import GraphRAG

    ke = get_knowledge_engine()
    if ke is not None:
        try:
            g = ke.get_graph()
            if g is not None and hasattr(g, "search") and hasattr(g, "nodes"):
                return g
            # KE may return the raw store — prefer the real GraphRAG singleton
            # which shares the same graph.json via GRAPH_JSON_PATH.
            if g is not None:
                return GraphRAG()
        except Exception as exc:
            logger.debug("KE.get_graph failed: %s", exc)
    return GraphRAG()


def get_safe_transit_rules():
    """Preferred way to get current validated transit rules."""
    ke = get_knowledge_engine()
    if ke is not None:
        try:
            return ke.get_safe_rules("transit")
        except Exception:
            pass
    try:
        from vedic_knowledge.graph.rules_provider import active_transit_rules

        return active_transit_rules()
    except Exception:
        return None


def get_safe_muhurta_rules():
    """Preferred way to get current validated muhurta rules."""
    ke = get_knowledge_engine()
    if ke is not None:
        try:
            return ke.get_safe_rules("muhurta")
        except Exception:
            pass
    try:
        from vedic_knowledge.graph.muhurta_rules import active_muhurta_rules

        return active_muhurta_rules()
    except Exception:
        return None


def get_safe_knowledge(engine_name: str = "unknown") -> dict[str, Any]:
    """Returns a safe snapshot of current knowledge state."""
    ke = get_knowledge_engine()
    if ke is not None:
        try:
            return ke.get_safe_knowledge(engine_name)
        except Exception:
            pass
    g = get_safe_graph()
    stats = getattr(g, "stats", {}) or {}
    return {
        "engine": engine_name,
        "healthy": bool(stats.get("loaded")),
        "graph_stats": stats,
        "source": "graph_rag_fallback",
    }


def is_knowledge_healthy() -> bool:
    """Quick health check for the entire knowledge layer."""
    ke = get_knowledge_engine()
    if ke is not None:
        try:
            return bool(ke.is_knowledge_healthy())
        except Exception:
            pass
    g = get_safe_graph()
    return bool(getattr(g, "stats", {}).get("loaded"))


def search_knowledge(query: str, top_k: int = 8) -> list[dict[str, Any]]:
    """
    Semantic + keyword hybrid retrieval over corpus chunks when KE is present;
    falls back to keyword GraphRAG.search when KE is absent or returns nothing.
    """
    ke = get_knowledge_engine()
    if ke is not None:
        try:
            hits = ke.search(query, top_k=top_k)
            if hits:
                return hits
        except Exception:
            pass
    g = get_safe_graph()
    # get_safe_graph may return a store shim without .search — prefer GraphRAG
    if hasattr(g, "search"):
        return list(g.search(query, top_n=top_k) or [])
    from vedic_knowledge.graph.graph import GraphRAG

    return list(GraphRAG().search(query, top_n=top_k) or [])


def query_research_knowledge(
    pattern: str | None = None,
    limit: int | None = None,
    *,
    include_invalidated: bool = True,
    include_unhealthy: bool = True,
) -> dict[str, Any]:
    """Exhaustive annotated research access; requires full KE."""
    ke = get_knowledge_engine()
    if ke is None:
        return {"error": "KnowledgeEngine unavailable", "nodes": []}
    return ke.query_research_nodes(
        pattern=pattern,
        limit=limit,
        include_invalidated=include_invalidated,
        include_unhealthy=include_unhealthy,
    )


def notify_embeddings_updated(chunk_count: int = 0) -> dict[str, Any]:
    """Clear embedding caches and notify registered engines."""
    ke = get_knowledge_engine()
    if ke is None:
        clear_knowledge_engine_cache()
        return {"ok": False, "reason": "KnowledgeEngine unavailable"}
    result = ke.on_embeddings_updated(chunk_count=chunk_count)
    clear_knowledge_engine_cache()
    return result


def get_prediction_enhancer(transit_analyzer=None):
    """Returns a PredictionEnhancer backed by package GraphRAG.

    `transit_analyzer` (optional): pass a VedicAstro-side
    `TransitImpactAnalyzer()` instance to enable transit_intelligence
    enrichment. Left unset, that one field stays empty — every other
    enrichment (citations, conflicts, god nodes) is unaffected.
    """
    from vedic_knowledge.graph.enhancer import PredictionEnhancer

    return PredictionEnhancer(transit_analyzer=transit_analyzer)


def get_llm_narration(facts: dict, birth: dict) -> dict | None:
    """Generate optional LLM narration via the central KnowledgeEngine."""
    ke = get_knowledge_engine()
    if ke is None:
        return None
    return ke.get_llm_narration(facts, birth)


def get_structured_book(book_id: str) -> dict | None:
    ke = get_knowledge_engine()
    if ke is None:
        return None
    return ke.get_structured_book(book_id)


def get_safe_structured_book(book_id: str) -> dict | None:
    return get_structured_book(book_id)


def get_nodes_for_chapter(book_id: str, chapter_id: str) -> list[dict]:
    ke = get_knowledge_engine()
    if ke is None:
        return []
    return ke.get_nodes_for_chapter(book_id, chapter_id)


def get_safe_nodes_for_chapter(book_id: str, chapter_id: str) -> list[dict]:
    return get_nodes_for_chapter(book_id, chapter_id)


def get_hierarchy_for_node(node_id: str) -> dict | None:
    ke = get_knowledge_engine()
    if ke is None:
        return None
    return ke.get_hierarchy_for_node(node_id)


def rebuild_structured_library(books: list[str] | None = None) -> dict:
    ke = get_knowledge_engine()
    if ke is None:
        return {"error": "KnowledgeEngine unavailable"}
    return ke.rebuild_structured_library(books=books)


def remap_nodes_to_structured(books: list[str] | None = None) -> dict:
    ke = get_knowledge_engine()
    if ke is None:
        return {"error": "KnowledgeEngine unavailable"}
    return ke.remap_nodes_to_structured(books=books)


def rebuild_and_remap_structured(books: list[str] | None = None) -> dict:
    ke = get_knowledge_engine()
    if ke is None:
        return {"error": "KnowledgeEngine unavailable"}
    return ke.rebuild_and_remap_structured(books=books)


def invalidate_nodes(
    node_ids: list[str] | None = None,
    pattern: str | None = None,
    reason: str = "manual",
    details: str = "",
) -> list[str]:
    ke = get_knowledge_engine()
    if ke is None:
        return []
    try:
        from knowledge_engine.models import InvalidationReason  # type: ignore

        try:
            r = InvalidationReason(reason)
        except Exception:
            r = InvalidationReason.MANUAL
        return ke.invalidate(node_ids=node_ids, pattern=pattern, reason=r, details=details)
    except Exception:
        return []


def invalidate_chapter(
    book_id: str, chapter_id: str, reason: str = "manual", details: str = ""
) -> dict:
    ke = get_knowledge_engine()
    if ke is None:
        return {"error": "KnowledgeEngine unavailable", "invalidated": []}
    nodes = ke.get_nodes_for_chapter(book_id, chapter_id)
    nids = [n.get("id") for n in nodes if isinstance(n, dict) and n.get("id")]
    try:
        from knowledge_engine.models import InvalidationReason  # type: ignore

        try:
            r = InvalidationReason(reason)
        except Exception:
            r = InvalidationReason.MANUAL
        invalidated = ke.invalidate(
            node_ids=nids, reason=r, details=details or f"chapter {chapter_id}@{book_id}"
        )
    except Exception:
        invalidated = []
    return {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "nodes_targeted": len(nids),
        "invalidated": invalidated,
    }


def get_structured_coverage() -> dict:
    """Return a snapshot of structured books when KE paths are present."""
    import json
    from pathlib import Path

    # Prefer env, then support both the repository checkout and the bundled
    # Vercel project root. The latter contains the generated copy created by
    # cvce/scripts/sync_provenance_bundle.py.
    roots: list[Path] = []
    root_env = os.environ.get("VEDICASTRO_ROOT")
    if root_env:
        roots.append(Path(root_env))
    roots.extend((Path(__file__).resolve().parents[3], Path(__file__).resolve().parents[2], Path.cwd()))
    structured_dir = None
    patch_file = None
    for root in roots:
        candidate_structured = root / "knowledge-graph" / "structured"
        candidate_patch = root / "knowledge-graph" / "patches" / "node-chapter-map.json"
        if candidate_structured.exists() or candidate_patch.exists():
            structured_dir = candidate_structured
            patch_file = candidate_patch
            break

    books: list[dict] = []
    total_chapters = 0
    total_patched_nodes = 0

    if structured_dir and structured_dir.exists():
        for p in sorted(structured_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                chs = data.get("chapters") or []
                bid = data.get("book_id") or p.stem
                total_chapters += len(chs)
                books.append(
                    {
                        "book_id": bid,
                        "chapters": len(chs),
                        "source_file": data.get("source_file"),
                    }
                )
            except Exception:
                continue

    patch_stats: dict = {"present": False, "entries": 0, "books_covered": 0}
    if patch_file and patch_file.exists():
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
        "books_detail": books[:50],
    }


def get_registered_engines_with_status() -> dict[str, Any]:
    ke = get_knowledge_engine()
    if ke is None:
        return {"count": 0, "engines": [], "version": None}
    names = ke.registry.registered_names() if ke and ke.registry else []
    REAL_RELOAD_HINTS = {
        "dasha": True,
        "yoga": True,
        "ashtakavarga": True,
        "report": True,
        "gochar": True,
        "muhurta": True,
    }
    out: list[dict[str, Any]] = []
    for n in sorted(set(names)):
        eng = ke.registry._engines.get(n) if hasattr(ke.registry, "_engines") else None
        has_refresh = bool(eng and eng.on_refresh) if eng else False
        real = REAL_RELOAD_HINTS.get(n, False)
        cache_only = n in ("kp_system", "prashna", "panchanga")
        out.append(
            {
                "name": n,
                "has_on_refresh": has_refresh,
                "real_reload": real,
                "crack": (not has_refresh) or (cache_only and not real),
            }
        )
    ver = None
    try:
        ver = ke.current_version.version if getattr(ke, "current_version", None) else None
    except Exception:
        pass
    return {"count": len(out), "engines": out, "version": ver}


def ensure_engine_registration(
    engine_name: str,
    on_refresh: Callable | None = None,
    on_invalidation: Callable | None = None,
):
    ke = get_knowledge_engine()
    if ke is None:
        return None
    return ke.registry.ensure_registration(engine_name, on_refresh, on_invalidation)
