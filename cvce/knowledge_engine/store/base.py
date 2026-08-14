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


class KnowledgeStorePaginationError(RuntimeError):
    """Raised when an exhaustive store page cannot be distinguished from EOF."""


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

    def get_nodes_page(self, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        """Optional exhaustive-research pagination with a compatible fallback."""

        return self.get_nodes(limit=limit + offset)[offset : offset + limit]

    def supports_incremental_pagination(self) -> bool:
        """Whether get_nodes_page_since() returns real incremental deltas.

        False (the default) means callers must always use the full
        get_nodes_page() scan -- correct for every backend that doesn't
        override this, including test doubles and the file-based store.
        """
        return False

    def get_nodes_page_since(
        self,
        cursor: tuple[str, str] | None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Nodes with (updated_at, id) strictly greater than `cursor`, ordered
        by (updated_at, id) ascending -- keyset pagination so rows sharing
        the cursor's exact updated_at timestamp are never skipped or
        double-counted across pages. `cursor` is (updated_at_iso, id) or
        None to fetch from the beginning. Only meaningful when
        supports_incremental_pagination() is True; the default here mirrors
        get_nodes_page() (ignores the cursor) and must not be called
        otherwise.
        """
        return self.get_nodes_page(limit=limit, offset=offset)

    @abstractmethod
    def get_links(self, source_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch links, optionally filtered by source."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the store is reachable and healthy."""
        ...
