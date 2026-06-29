"""
KnowledgeEngine — The central manager for the Knowledge Graph and its consumers.
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from graph_rag.graph import GraphRAG

from .models import GraphVersion, KnowledgeValidity, InvalidationReason
from .registry import EngineRegistry, RegisteredEngine


@dataclass
class KnowledgeEngine:
    """
    Single point of control for the Vedic Knowledge Graph.

    Goals:
    1. When new texts are added → cascade updates to registered engines.
    2. Block stale/wrong/confusing knowledge from being consumed.
    3. Support periodic revival (engines can request fresh context).
    """

    graph: GraphRAG = field(default_factory=GraphRAG)
    registry: EngineRegistry = field(default_factory=EngineRegistry)
    current_version: Optional[GraphVersion] = None
    _invalidations: Dict[str, KnowledgeValidity] = field(default_factory=dict)
    _last_revived_at: Optional[datetime] = None
    _revive_interval_seconds: int = 3600

    def __post_init__(self):
        self._load_current_version()

    def _load_current_version(self) -> GraphVersion:
        """Load the active graph version (from graph.json or env)."""
        stats = self.graph.stats if hasattr(self.graph, "stats") else {}
        version_str = os.environ.get("CORPUS_GRAPH_VERSION", "unknown")
        self.current_version = GraphVersion(
            version=version_str,
            node_count=stats.get("nodes", 0),
            link_count=stats.get("links", 0),
            loaded_at=datetime.now(timezone.utc),
        )
        return self.current_version

    # ------------------------------------------------------------------ #
    # Public API for engines
    # ------------------------------------------------------------------ #

    def register_engine(
        self,
        name: str,
        on_refresh: Optional[Callable[[str], None]] = None,
        on_invalidation: Optional[Callable[[List[str], InvalidationReason, str], None]] = None,
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

        return {
            "version": self.current_version.version if self.current_version else "unknown",
            "stats": getattr(self.graph, "stats", {}),
            "invalidated_nodes": self.invalidated_node_ids(),
            "invalidation_count": len(self._invalidations),
            "last_revived": self._last_revived_at.isoformat() if self._last_revived_at else None,
        }

    def get_graph(self) -> GraphRAG:
        """Direct (but still validated) access to the raw GraphRAG when needed."""
        if not self.is_knowledge_healthy():
            raise RuntimeError("Knowledge is currently unhealthy — raw graph access blocked.")
        return self.graph

    def get_safe_node(self, node_id: str) -> Optional[dict]:
        """
        Return a graph node only when it is currently valid.

        Invalidated or unknown nodes return ``None`` without raising.
        """
        if not self.is_node_valid(node_id):
            return None
        return self.graph.node(node_id)

    def filter_valid_nodes(self, nodes: List[dict]) -> List[dict]:
        """Return only nodes whose ``id`` is not invalidated."""
        return [node for node in nodes if self.is_node_valid(node.get("id", ""))]

    def query_nodes(self, pattern: Optional[str] = None, limit: Optional[int] = None) -> List[dict]:
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
                node for node in candidates
                if fnmatch.fnmatch(node.get("id", ""), pattern)
            ]

        valid = self.filter_valid_nodes(candidates)
        if limit is not None:
            return valid[:limit]
        return valid

    def get_safe_rules(self, category: str = "transit"):
        """Safe access to specific rule sets (transit, muhurta, etc.)."""
        if not self.is_knowledge_healthy():
            raise RuntimeError(f"Knowledge unhealthy — {category} rules blocked.")

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
        """Returns True if embeddings are populated and healthy."""
        return False  # Will be wired properly once embeddings are populated

    def search(self, query: str, top_k: int = 8) -> list[dict]:
        """
        Future vector + graph hybrid search entry point.
        Currently returns empty until embeddings are live.
        """
        if not self.vector_search_available():
            return []
        return []

    # ------------------------------------------------------------------ #
    # Validity & Blocking (Invalidation Protocol)
    # ------------------------------------------------------------------ #

    def invalidate(
        self,
        node_ids: Optional[List[str]] = None,
        pattern: Optional[str] = None,
        reason: InvalidationReason = InvalidationReason.MANUAL,
        details: str = "",
    ) -> List[str]:
        """
        Block specific knowledge from being consumed by any engine.

        Targets may be supplied as explicit ``node_ids``, a glob ``pattern``
        (matched against all graph node IDs), or both. Returns the list of
        node IDs that were newly or re-invalidated.
        """
        targets = self._resolve_invalidation_targets(node_ids=node_ids, pattern=pattern)
        if not targets:
            return []

        now = datetime.now(timezone.utc)
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
        node_ids: Optional[List[str]] = None,
        pattern: Optional[str] = None,
    ) -> List[str]:
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

    def invalidated_node_ids(self) -> List[str]:
        """Return all currently invalidated node IDs."""
        return list(self._invalidations.keys())

    def is_knowledge_healthy(self) -> bool:
        """High-level health for the whole system."""
        if self.current_version is None:
            return False
        return len(self._invalidations) < 50

    def _resolve_invalidation_targets(
        self,
        node_ids: Optional[List[str]] = None,
        pattern: Optional[str] = None,
        known_only: bool = False,
    ) -> List[str]:
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

    def _clear_stale_invalidations(self) -> List[str]:
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
            loaded_at=datetime.now(timezone.utc),
            source=str(new_graph_path),
        )

        self._invalidations.clear()
        self.registry.notify_refresh(new_version=new_version)
        self._last_revived_at = datetime.now(timezone.utc)

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
            age = (datetime.now(timezone.utc) - self._last_revived_at).total_seconds()
            if age < self._revive_interval_seconds:
                return False

        self._load_current_version()
        self._clear_stale_invalidations()

        new_version = self.current_version.version if self.current_version else "unknown"
        self.registry.notify_refresh(new_version=new_version)

        self._last_revived_at = datetime.now(timezone.utc)
        return True

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
