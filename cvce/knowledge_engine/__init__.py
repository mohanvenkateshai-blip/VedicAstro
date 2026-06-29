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
from .integration import get_knowledge_engine, search_knowledge
from .models import GraphVersion, KnowledgeValidity
from .refresh_auditor import KnowledgeRefreshAuditor, RefreshImpact
from .registry import EngineRegistry

__all__ = [
    "KnowledgeEngine",
    "KnowledgeRefreshAuditor",
    "GraphVersion",
    "KnowledgeValidity",
    "RefreshImpact",
    "EngineRegistry",
    "get_knowledge_engine",
    "search_knowledge",
]
