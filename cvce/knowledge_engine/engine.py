"""
KnowledgeEngine — The central manager for the Knowledge Graph and its consumers.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .models import GraphVersion, InvalidationReason, KnowledgeValidity
from .registry import EngineRegistry, RegisteredEngine
from .store.base import KnowledgeStore
from .store.supabase_store import SupabaseKnowledgeStore

logger = logging.getLogger(__name__)


# Fallback file-based store (current behavior)
class _FileKnowledgeStore(KnowledgeStore):
    def __init__(self, graph_path: Path | None = None):
        self.graph_path = graph_path or Path("knowledge-graph/graphify-out/graph.json")
        self._graph = None

    def _load(self):
        if self._graph is None:
            self._graph = json.loads(self.graph_path.read_text(encoding="utf-8"))
        return self._graph

    def get_version(self) -> str:
        return os.environ.get("CORPUS_GRAPH_VERSION", "file-based")

    def get_stats(self) -> dict[str, Any]:
        g = self._load()
        return {"node_count": len(g.get("nodes", [])), "link_count": len(g.get("links", []))}

    def get_node(self, node_id: str):
        g = self._load()
        return next((n for n in g.get("nodes", []) if n.get("id") == node_id), None)

    def get_nodes(self, limit: int = 100):
        g = self._load()
        return g.get("nodes", [])[:limit]

    def get_links(self, source_id=None, limit=100):
        g = self._load()
        links = g.get("links", [])
        if source_id:
            links = [l for l in links if l.get("source") == source_id]
        return links[:limit]

    def health_check(self) -> bool:
        return self.graph_path.exists()


@dataclass
class KnowledgeEngine:
    """
    Single point of control for the Vedic Knowledge Graph.

    Goals:
    1. When new texts are added → cascade updates to registered engines.
    2. Block stale/wrong/confusing knowledge from being consumed.
    3. Support periodic revival (engines can request fresh context).
    """

    store: KnowledgeStore = field(default_factory=_FileKnowledgeStore)
    registry: EngineRegistry = field(default_factory=EngineRegistry)
    current_version: GraphVersion | None = None
    _invalidations: dict[str, KnowledgeValidity] = field(default_factory=dict)
    _last_revived_at: datetime | None = None
    _revive_interval_seconds: int = 3600

    def __post_init__(self):
        self._load_current_version()
        self._attach_graph_compat()

    def _load_current_version(self) -> GraphVersion:
        """Load the active graph version."""
        stats = self.store.get_stats()
        version_str = os.environ.get("CORPUS_GRAPH_VERSION", self.store.get_version())
        self.current_version = GraphVersion(
            version=version_str,
            node_count=stats.get("node_count", 0),
            link_count=stats.get("link_count", 0),
            loaded_at=datetime.now(UTC),
        )
        return self.current_version

    def _attach_graph_compat(self):
        """Provide self.graph for legacy accessors (query_nodes, get_safe_node, on_new...).
        Prefers the real GraphRAG singleton (so cache clears in on_refresh also affect it);
        falls back to a thin store-backed shim.
        """
        if getattr(self, "graph", None) is not None:
            return
        try:
            from graph_rag.graph import GraphRAG

            self.graph = GraphRAG()
            return
        except Exception as exc:
            logger.debug("GraphRAG compat attach failed, using store shim: %s", exc)

        # Fallback shim backed by the store (supports .nodes, .node(), .stats, _load)
        class _StoreGraphShim:
            def __init__(self, store):
                self._store = store
                self.nodes = []
                self.links = []
                self._nodes_by_id = {}
                self._loaded = False
                try:
                    self.stats = store.get_stats() or {}
                except Exception:
                    self.stats = {}

            def _load(self):
                if self._loaded:
                    return
                try:
                    self.nodes = self._store.get_nodes(limit=100000) or []
                    self.links = self._store.get_links(limit=100000) or []
                    self._nodes_by_id = {
                        n.get("id"): n for n in self.nodes if isinstance(n, dict) and n.get("id")
                    }
                except Exception:
                    pass
                self._loaded = True

            def node(self, node_id: str):
                self._load()
                return self._nodes_by_id.get(node_id)

        self.graph = _StoreGraphShim(self.store)

    # ------------------------------------------------------------------ #
    # Public API for engines
    # ------------------------------------------------------------------ #

    def register_engine(
        self,
        name: str,
        on_refresh: Callable[[str], None] | None = None,
        on_invalidation: Callable[[list[str], InvalidationReason, str], None] | None = None,
    ) -> RegisteredEngine:
        """Register an engine that depends on knowledge (e.g. 'gochar', 'report', 'muhurta')."""
        return self.registry.register(
            name,
            on_refresh=on_refresh,
            on_invalidation=on_invalidation,
        )

    def get_safe_knowledge(self, engine_name: str) -> dict:
        """
        Preferred safe access point for any engine that needs current validated knowledge.

        Raises RuntimeError when the graph is globally unhealthy. Returned payload
        excludes invalidated nodes from direct use — consumers should call
        ``get_safe_node`` / ``filter_valid_nodes`` for node-level access.
        """
        if not self.is_knowledge_healthy():
            raise RuntimeError(f"Knowledge is currently unhealthy. Engine '{engine_name}' blocked.")

        g = getattr(self, "graph", None)
        stats = getattr(g, "stats", None) or {}
        if not stats and g is not None:
            try:
                nc = len(getattr(g, "nodes", []) or [])
                lc = len(getattr(g, "links", []) or [])
                stats = {"node_count": nc, "link_count": lc, "nodes": nc, "links": lc}
            except Exception:
                stats = {}
        return {
            "version": self.current_version.version if self.current_version else "unknown",
            "stats": stats,
            "invalidated_nodes": self.invalidated_node_ids(),
            "invalidation_count": len(self._invalidations),
            "last_revived": self._last_revived_at.isoformat() if self._last_revived_at else None,
        }

    def get_graph(self):
        """Returns the underlying store (for advanced use)."""
        if not self.is_knowledge_healthy():
            raise RuntimeError("Knowledge is currently unhealthy.")
        return self.store

    @classmethod
    def with_supabase(cls, graph_version: str = "newbooks-v1") -> KnowledgeEngine:
        """Convenience constructor for Supabase-backed mode."""
        store = SupabaseKnowledgeStore(graph_version=graph_version)
        return cls(store=store)

    def get_safe_node(self, node_id: str) -> dict | None:
        """
        Return a graph node only when it is currently valid.

        Invalidated or unknown nodes return ``None`` without raising.
        """
        if not self.is_node_valid(node_id):
            return None
        return self.graph.node(node_id)

    def filter_valid_nodes(self, nodes: list[dict]) -> list[dict]:
        """Return only nodes whose ``id`` is not invalidated."""
        return [node for node in nodes if self.is_node_valid(node.get("id", ""))]

    def query_nodes(self, pattern: str | None = None, limit: int | None = None) -> list[dict]:
        """
        Safe graph query that omits invalidated nodes.

        When ``pattern`` is given, only node IDs matching the glob pattern are
        considered (e.g. ``"muhurta_*"``).
        """
        if not self.is_knowledge_healthy():
            raise RuntimeError("Knowledge is currently unhealthy — node query blocked.")

        candidates = self.graph.nodes
        if pattern:
            candidates = [
                node for node in candidates if fnmatch.fnmatch(node.get("id", ""), pattern)
            ]

        valid = self.filter_valid_nodes(candidates)
        if limit is not None:
            return valid[:limit]
        return valid

    def get_structured_book(self, book_id: str) -> dict | None:
        """Return the clean, hierarchical chapter/subtitle/content structure for a source book.
        This is generated from the original Gyan markdown (scripts/build_structured_library.py)
        and is the authoritative organised view (chapters, titles, subtitles, sections).
        Used to drive the Learn reader and to map graph nodes back to precise locations.
        """
        try:
            from pathlib import Path
            import json
            base = Path("knowledge-graph/structured")
            candidates = [
                base / f"{book_id}.json",
                base / f"{book_id.replace(' ', '_')}.json",
            ]
            for p in candidates:
                if p.exists():
                    return json.loads(p.read_text(encoding="utf-8"))
            # fuzzy
            if base.exists():
                for p in base.glob("*.json"):
                    try:
                        d = json.loads(p.read_text(encoding="utf-8"))
                        if book_id in (d.get("book_id") or "") or book_id in (d.get("canonical_name") or ""):
                            return d
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("get_structured_book failed for %s: %s", book_id, e)
        return None

    def get_safe_rules(self, category: str = "transit"):
        """Safe access to specific rule sets (transit, muhurta, etc.)."""
        if not self.is_knowledge_healthy():
            raise RuntimeError(f"Knowledge unhealthy — {category} rules blocked.")

        # Delegate to store if it supports rule methods (Supabase store will in future)
        if hasattr(self.store, "get_safe_rules"):
            return self.store.get_safe_rules(category)

        # Fallback to current providers (temporary until store implements rules)
        if category == "transit":
            from graph_rag.rules_provider import active_transit_rules

            return active_transit_rules()
        elif category == "muhurta":
            from graph_rag.muhurta_rules_provider import active_muhurta_rules

            return active_muhurta_rules()
        else:
            raise ValueError(f"Unknown rule category: {category}")

    # ------------------------------------------------------------------ #
    # Vector / Hybrid Search (P0 item under KnowledgeEngine)
    # ------------------------------------------------------------------ #

    def vector_search_available(self) -> bool:
        """Check if embeddings exist in Supabase corpus_chunks."""
        if hasattr(self.store, "has_embeddings"):
            try:
                return self.store.has_embeddings()
            except Exception:
                return False
        return False

    def on_embeddings_updated(self, chunk_count: int = 0) -> dict:
        """
        Called after corpus chunk embeddings are populated or refreshed.

        Clears store caches and notifies registered engines so they can use
        vector retrieval on the next refresh cycle.
        """
        if hasattr(self.store, "mark_embeddings_updated"):
            self.store.mark_embeddings_updated()

        self._load_current_version()
        version = self.current_version.version if self.current_version else "unknown"
        self.registry.notify_refresh(new_version=version)
        self._last_revived_at = datetime.now(UTC)

        return {
            "status": "embeddings_updated",
            "chunks_embedded": chunk_count,
            "vector_search_available": self.vector_search_available(),
            "version": version,
        }

    # ------------------------------------------------------------------ #
    # LLM Narration (KnowledgeEngine-owned)
    # ------------------------------------------------------------------ #

    # Narration sources — virtual node IDs for per-domain LLM blocking
    NARRATION_SOURCE_KEYS = (
        "dasha_intelligence",
        "transit_intelligence",
        "timing_merge",
        "yogas",
        "ashtakavarga",
    )

    def narration_source_id(self, source_key: str) -> str:
        """Return the invalidation node ID for an LLM narration source."""
        return f"narration_source:{source_key}"

    def is_narration_source_valid(self, source_key: str) -> bool:
        """Return True when narration for this fact domain is not blocked."""
        return self.is_node_valid(self.narration_source_id(source_key))

    def get_llm_narration(self, facts: dict, birth: dict) -> dict | None:
        """
        Optional Gemini prose layer for report facts.

        Gated by ``CVCE_LLM_NARRATION=1`` and overall knowledge health.
        Respects per-source invalidation via ``narration_source:*`` node IDs.
        Returns ``None`` when the feature flag is off; otherwise a status dict.
        """
        if os.environ.get("CVCE_LLM_NARRATION") != "1":
            return None

        if not self.is_knowledge_healthy():
            return {
                "status": "blocked",
                "reason": "knowledge unhealthy",
            }

        allowed, blocked = self._resolve_narration_sources(facts)
        if not allowed:
            return {
                "status": "blocked",
                "reason": "all narration sources blocked",
                "sources_blocked": blocked,
            }

        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            return {"status": "skipped", "reason": "no Gemini key"}

        from google import genai

        client = genai.Client(api_key=key)

        prompt_payload = {k: facts[k] for k in allowed if k in facts}
        prompt = f"""You are a concise Vedic astrologer. Given the structured facts below for {birth}, write 3-5 short natural paragraphs (no tables) that a client can read directly. Cover: overall tone of the period, key strengths, cautions, and one actionable recommendation. Stay factual to the data. Use plain modern English.

Facts (abbrev):
{json.dumps(prompt_payload, indent=2)[:3000]}
"""

        resp = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        text = (resp.text or "").strip()
        return {
            "prose": text,
            "model": "gemini-1.5-flash",
            "generated": True,
            "sources_used": allowed,
            "sources_blocked": blocked,
        }

    def _resolve_narration_sources(self, facts: dict) -> tuple[list[str], list[str]]:
        """Split narration source keys into allowed vs invalidated (with data present)."""
        allowed: list[str] = []
        blocked: list[str] = []
        for key in self.NARRATION_SOURCE_KEYS:
            if key not in facts or facts[key] is None:
                continue
            if self.is_narration_source_valid(key):
                allowed.append(key)
            else:
                blocked.append(key)
        return allowed, blocked

    def search(self, query: str, top_k: int = 8) -> list[dict]:
        """
        Semantic + keyword hybrid search over corpus chunks (Supabase pgvector).

        Returns ranked chunk dicts with ``source_id``, ``content``, ``chunk_index``,
        and ``similarity`` when vector search contributed.
        """
        query = (query or "").strip()
        if not query:
            return []

        if not hasattr(self.store, "search"):
            logger.debug("store has no search() — returning empty for %r", query[:80])
            return []

        try:
            results = self.store.search(query, top_k)
            logger.info(
                "knowledge search %r → %d hits (vector_available=%s)",
                query[:80],
                len(results),
                self.vector_search_available(),
            )
            return results
        except Exception:
            logger.exception("knowledge search failed for %r", query[:80])
            return []

    # ------------------------------------------------------------------ #
    # Validity & Blocking (Invalidation Protocol)
    # ------------------------------------------------------------------ #

    def invalidate(
        self,
        node_ids: list[str] | None = None,
        pattern: str | None = None,
        reason: InvalidationReason = InvalidationReason.MANUAL,
        details: str = "",
    ) -> list[str]:
        """
        Block specific knowledge from being consumed by any engine.

        Targets may be supplied as explicit ``node_ids``, a glob ``pattern``
        (matched against all graph node IDs), or both. Returns the list of
        node IDs that were newly or re-invalidated.
        """
        targets = self._resolve_invalidation_targets(node_ids=node_ids, pattern=pattern)
        if not targets:
            return []

        now = datetime.now(UTC)
        for node_id in targets:
            self._invalidations[node_id] = KnowledgeValidity(
                node_id=node_id,
                is_valid=False,
                reason=reason,
                details=details,
                invalidated_at=now,
            )

        self.registry.notify_invalidation(targets, reason, details)
        return targets

    def revalidate(
        self,
        node_ids: list[str] | None = None,
        pattern: str | None = None,
    ) -> list[str]:
        """
        Remove invalidations for the given IDs or glob pattern.

        Returns the node IDs that were restored to valid status.
        """
        if node_ids is None and pattern is None:
            cleared = list(self._invalidations.keys())
            self._invalidations.clear()
            return cleared

        targets = self._resolve_invalidation_targets(
            node_ids=node_ids,
            pattern=pattern,
            known_only=True,
        )
        for node_id in targets:
            self._invalidations.pop(node_id, None)
        return targets

    def get_validity(self, node_id: str) -> KnowledgeValidity:
        """Return the validity record for a node (valid by default)."""
        if node_id in self._invalidations:
            return self._invalidations[node_id]
        return KnowledgeValidity(node_id=node_id, is_valid=True)

    def is_node_valid(self, node_id: str) -> bool:
        """Return True when the node is not in the invalidation set."""
        return node_id not in self._invalidations

    def invalidated_node_ids(self) -> list[str]:
        """Return all currently invalidated node IDs."""
        return list(self._invalidations.keys())

    def is_knowledge_healthy(self) -> bool:
        """High-level health for the whole system."""
        if self.current_version is None:
            return False
        return len(self._invalidations) < 50

    def _resolve_invalidation_targets(
        self,
        node_ids: list[str] | None = None,
        pattern: str | None = None,
        known_only: bool = False,
    ) -> list[str]:
        """Resolve explicit IDs and/or glob patterns into a deduplicated ID list."""
        targets: set[str] = set()

        if node_ids:
            targets.update(node_ids)

        if pattern:
            graph_ids = {node.get("id", "") for node in getattr(self.graph, "nodes", [])}
            if known_only:
                source_ids = set(self._invalidations.keys())
            else:
                source_ids = graph_ids
            targets.update(nid for nid in source_ids if nid and fnmatch.fnmatch(nid, pattern))

        return sorted(targets)

    def _clear_stale_invalidations(self) -> list[str]:
        """
        Drop invalidations for nodes that no longer exist in the loaded graph.

        Returns the stale node IDs that were removed.
        """
        graph_ids = {node.get("id", "") for node in getattr(self.graph, "nodes", [])}
        stale = [node_id for node_id in self._invalidations if node_id not in graph_ids]
        for node_id in stale:
            del self._invalidations[node_id]
        return stale

    # ------------------------------------------------------------------ #
    # Cascading updates (when new literature is added)
    # ------------------------------------------------------------------ #

    def on_new_literature_ingested(self, new_graph_path: Path, new_version: str):
        """
        Called after ingestion pipeline finishes.

        This is the cascade point:
        - Force reload of GraphRAG with the new file
        - Update version metadata
        - Clear old invalidations
        - Notify all registered engines to refresh
        """
        if hasattr(self.graph, "_loaded"):
            self.graph._loaded = False
            self.graph._GRAPH_PATH = str(new_graph_path)  # type: ignore[attr-defined]

        self.graph._load()

        stats = getattr(self.graph, "stats", {})
        self.current_version = GraphVersion(
            version=new_version,
            node_count=stats.get("nodes", 0),
            link_count=stats.get("links", 0),
            loaded_at=datetime.now(UTC),
            source=str(new_graph_path),
        )

        self._invalidations.clear()
        self.registry.notify_refresh(new_version=new_version)
        self._last_revived_at = datetime.now(UTC)

    # ------------------------------------------------------------------ #
    # Periodic Revival (Revival Protocol)
    # ------------------------------------------------------------------ #

    def revive(self, force: bool = False) -> bool:
        """
        Refresh knowledge state and push updates to registered engines.

        Intended for periodic background jobs or on-demand calls. When run:

        1. Re-loads version metadata from the current graph and environment.
        2. Clears invalidations for nodes that no longer exist (stale blocks).
        3. Notifies all registered engines via ``on_refresh`` so they can
           rebuild caches and rule views.

        Returns True when a revival cycle completed; False when skipped due
        to the cooldown window (unless ``force=True``).
        """
        if not force and self._last_revived_at:
            age = (datetime.now(UTC) - self._last_revived_at).total_seconds()
            if age < self._revive_interval_seconds:
                return False

        self._load_current_version()
        self._clear_stale_invalidations()

        new_version = self.current_version.version if self.current_version else "unknown"
        self.registry.notify_refresh(new_version=new_version)

        self._last_revived_at = datetime.now(UTC)
        return True

    def trigger_global_refresh(self, reason: str = "manual") -> dict:
        """
        **Force refresh command** — tells every registered engine to
        immediately recalculate all logic, analysis, predictions, and
        interpretations using the current knowledge graph.

        This is the explicit "refresh all" trigger that can be called
        after new literature is added or when knowledge needs to be
        forcefully propagated across the entire system.
        """
        self._load_current_version()
        self._clear_stale_invalidations()

        new_version = self.current_version.version if self.current_version else "unknown"
        self.registry.notify_refresh(new_version=new_version)

        self._last_revived_at = datetime.now(UTC)

        return {
            "status": "triggered",
            "version": new_version,
            "reason": reason,
            "engines_notified": self.registry.registered_names(),
            "timestamp": self._last_revived_at.isoformat(),
        }

    # ------------------------------------------------------------------ #
    # Observability
    # ------------------------------------------------------------------ #

    def health(self) -> dict:
        return {
            "version": self.current_version.version if self.current_version else None,
            "healthy": self.is_knowledge_healthy(),
            "invalidated_count": len(self._invalidations),
            "invalidated_nodes": self.invalidated_node_ids()[:20],
            "registered_engines": self.registry.registered_names(),
            "last_revived": self._last_revived_at.isoformat() if self._last_revived_at else None,
        }
