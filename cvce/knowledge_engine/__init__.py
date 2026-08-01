"""
KnowledgeEngine — Central authority for the Vedic Knowledge Graph.

Responsibilities:
- Owns loading, versioning, and validity of the knowledge graph.
- Maintains links/interlinks with consuming engines.
- Provides controlled access (with blocking/invalidation).
- Supports cascading updates when new literature is ingested.
- Enables periodic revival of context for prediction & interpretation engines.

This is the single source of truth for "what classical knowledge is currently safe and active".
"""

from .engine import KnowledgeEngine
from .integration import (
    get_hierarchy_for_node,
    get_knowledge_engine,
    get_nodes_for_chapter,
    get_structured_book,
    query_research_knowledge,
    rebuild_structured_library,
    remap_nodes_to_structured,
    search_knowledge,
)
from .models import GraphVersion, KnowledgeValidity
from .refresh_auditor import KnowledgeRefreshAuditor, RefreshImpact
from .registry import EngineRegistry

# Self-evolving memory subsystem (lazy-friendly re-exports)
try:
    from .auto_mapper import AutoMapper, map_new_nodes
except Exception:  # pragma: no cover - optional at import time
    AutoMapper = None  # type: ignore
    map_new_nodes = None  # type: ignore
try:
    from .schema_mutator import SchemaMutator, mutate_schema
except Exception:  # pragma: no cover
    SchemaMutator = None  # type: ignore
    mutate_schema = None  # type: ignore
try:
    from .session_memory import build_session_graph, query_session_memory
except Exception:  # pragma: no cover
    build_session_graph = None  # type: ignore
    query_session_memory = None  # type: ignore

__all__ = [
    "KnowledgeEngine",
    "KnowledgeRefreshAuditor",
    "GraphVersion",
    "KnowledgeValidity",
    "RefreshImpact",
    "EngineRegistry",
    "get_knowledge_engine",
    "search_knowledge",
    "get_structured_book",
    "get_nodes_for_chapter",
    "get_hierarchy_for_node",
    "query_research_knowledge",
    "rebuild_structured_library",
    "remap_nodes_to_structured",
    "AutoMapper",
    "map_new_nodes",
    "SchemaMutator",
    "mutate_schema",
    "build_session_graph",
    "query_session_memory",
]
