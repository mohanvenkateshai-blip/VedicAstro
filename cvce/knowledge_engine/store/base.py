"""
KnowledgeStore — Abstract interface for the Knowledge Graph storage backend.

This allows KnowledgeEngine to work with different backends:
- File-based (current default)
- Supabase (production / secure)
- Future: Neo4j, S3, etc.

All access to nodes, links, and metadata must go through this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class KnowledgeStore(ABC):
    """Abstract base class for knowledge graph storage."""

    @abstractmethod
    def get_version(self) -> str:
        """Return the current active graph version identifier."""
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Return basic stats (node_count, link_count, etc.)."""
        ...

    @abstractmethod
    def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Fetch a single node by ID. Returns None if not found or invalid."""
        ...

    @abstractmethod
    def get_nodes(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch a batch of nodes."""
        ...

    @abstractmethod
    def get_links(self, source_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch links, optionally filtered by source."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the store is reachable and healthy."""
        ...
