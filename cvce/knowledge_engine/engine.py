"""
KnowledgeEngine — The central manager for the Knowledge Graph and its consumers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

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
    _invalidated_nodes: Set[str] = field(default_factory=set)
    _last_revived_at: Optional[datetime] = None

    def __post_init__(self):
        self._load_current_version()

    def _load_current_version(self):
        """Load the active graph version (from graph.json or env)."""
        # For now we derive version from the loaded graph stats + env
        stats = self.graph.stats if hasattr(self.graph, "stats") else {}
        version_str = os.environ.get("CORPUS_GRAPH_VERSION", "unknown")
        self.current_version = GraphVersion(
            version=version_str,
            node_count=stats.get("nodes", 0),
            link_count=stats.get("links", 0),
            loaded_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------ #
    # Public API for engines
    # ------------------------------------------------------------------ #

    def register_engine(self, name: str, on_refresh: Optional[Callable] = None) -> RegisteredEngine:
        """Register an engine that depends on knowledge (e.g. 'gochar', 'report', 'muhurta')."""
        engine = self.registry.register(name, on_refresh=on_refresh)
        return engine

    def get_safe_knowledge(self, engine_name: str) -> dict:
        """
        Engines should call this instead of talking directly to GraphRAG when they want
        validated + current knowledge.
        """
        if not self.is_knowledge_healthy():
            raise RuntimeError(f"Knowledge is currently unhealthy. Engine '{engine_name}' blocked.")

        base = {
            "version": self.current_version.version if self.current_version else "unknown",
            "stats": getattr(self.graph, "stats", {}),
        }

        # Future: we can return filtered views here (e.g. exclude invalidated nodes)
        return base

    # ------------------------------------------------------------------ #
    # Validity & Blocking
    # ------------------------------------------------------------------ #

    def invalidate(self, node_ids: List[str], reason: InvalidationReason, details: str = ""):
        """Block specific knowledge from being consumed by any engine."""
        for nid in node_ids:
            self._invalidated_nodes.add(nid)

        # Notify all registered engines
        self.registry.notify_invalidation(node_ids, reason, details)

    def is_node_valid(self, node_id: str) -> bool:
        return node_id not in self._invalidated_nodes

    def is_knowledge_healthy(self) -> bool:
        """High-level health for the whole system."""
        if self.current_version is None:
            return False
        # In future we can add more checks (embedding coverage, validation jobs, etc.)
        return len(self._invalidated_nodes) < 50  # arbitrary safety threshold for now

    # ------------------------------------------------------------------ #
    # Cascading updates (when new literature is added)
    # ------------------------------------------------------------------ #

    def on_new_literature_ingested(self, new_graph_path: Path, new_version: str):
        """
        Called after ingestion pipeline finishes (by scripts or future orchestrator).

        This is the "cascade" point:
        - Reload graph
        - Update version
        - Notify all engines so they can refresh their rules / caches
        """
        # 1. Reload the graph (GraphRAG is a singleton, but we can force reload)
        # For now we rely on process restart or we can add a reload method later.
        # Here we at least update our version metadata.
        self.current_version = GraphVersion(
            version=new_version,
            node_count=0,  # will be filled on next access
            link_count=0,
            loaded_at=datetime.now(timezone.utc),
        )

        # 2. Clear any previous invalidations that were specific to old version
        self._invalidated_nodes.clear()

        # 3. Notify every registered engine
        self.registry.notify_refresh(new_version=new_version)

        self._last_revived_at = datetime.now(timezone.utc)

    # ------------------------------------------------------------------ #
    # Periodic Revival
    # ------------------------------------------------------------------ #

    def revive(self, force: bool = False) -> bool:
        """
        Engines (or a background job) can call this to get fresh context.

        In production this would:
        - Re-check the latest deployed graph version
        - Re-apply any blocking rules
        - Push updated views to long-lived engines
        """
        if not force and self._last_revived_at:
            age = (datetime.now(timezone.utc) - self._last_revived_at).total_seconds()
            if age < 3600:  # don't revive more than once per hour unless forced
                return False

        # Re-load version info
        self._load_current_version()

        # Tell engines to refresh their internal caches / rules
        self.registry.notify_refresh(new_version=self.current_version.version if self.current_version else "unknown")

        self._last_revived_at = datetime.now(timezone.utc)
        return True

    # ------------------------------------------------------------------ #
    # Observability
    # ------------------------------------------------------------------ #

    def health(self) -> dict:
        return {
            "version": self.current_version.version if self.current_version else None,
            "healthy": self.is_knowledge_healthy(),
            "invalidated_count": len(self._invalidated_nodes),
            "registered_engines": self.registry.registered_names(),
            "last_revived": self._last_revived_at.isoformat() if self._last_revived_at else None,
        }
