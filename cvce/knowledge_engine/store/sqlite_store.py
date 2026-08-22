"""
SQLiteKnowledgeStore — reads the static knowledge graph from a baked,
read-only graph.db instead of Supabase (B-56 durable fix).

Built by scripts/build_graph_db.py from graph_rag/graph.json at CI/release
time. This store never writes and never touches the network — the whole
point is to take graph reads off the live request path entirely, per
docs/graph-sqlite-migration-playbook_1.md.

Field shapes are kept identical to SupabaseKnowledgeStore's return values
(same dict keys for node/link rows) so callers written against that
interface don't need to change.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

from .base import KnowledgeStore

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "graph.db"


def default_db_path() -> Path:
    return Path(os.environ.get("GRAPH_DB_PATH", str(_DEFAULT_DB_PATH)))


def _row_to_node(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    props = json.loads(d.pop("props") or "{}")
    d.update(props)
    return d


def _row_to_link(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    props = json.loads(d.pop("props") or "{}")
    d.update(props)
    return d


class SQLiteKnowledgeStore(KnowledgeStore):
    """Knowledge graph backed by a baked, read-only SQLite file."""

    def __init__(self, db_path: str | Path | None = None, graph_version: str | None = None):
        self.db_path = Path(db_path) if db_path else default_db_path()
        self._graph_version_override = graph_version
        self._con: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._con is not None:
            return self._con
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"SQLiteKnowledgeStore: {self.db_path} not found — run "
                f"scripts/build_graph_db.py first (or check GRAPH_DB_PATH)"
            )
        con = sqlite3.connect(
            f"file:{self.db_path}?mode=ro&immutable=1",
            uri=True,
            check_same_thread=False,
        )
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA mmap_size=30000000")
        con.execute("PRAGMA query_only=true")
        self._con = con
        return con

    def _meta(self) -> dict[str, str]:
        cur = self._connect().execute("SELECT key, value FROM meta")
        return dict(cur.fetchall())

    # ------------------------------------------------------------------ #
    # KnowledgeStore interface
    # ------------------------------------------------------------------ #

    def get_version(self) -> str:
        if self._graph_version_override:
            return self._graph_version_override
        commit = self._meta().get("built_at_commit")
        return f"sqlite-baked@{commit}" if commit else "sqlite-baked"

    def get_stats(self) -> dict[str, Any]:
        meta = self._meta()
        return {
            "version": self.get_version(),
            "node_count": int(meta.get("node_count", 0)),
            "link_count": int(meta.get("link_count", 0)),
            "hyperedge_count": int(meta.get("hyperedge_count", 0)),
            # A baked snapshot is immutable for the life of the deployed
            # instance, so "freshness" is the build timestamp, not a live
            # per-row watermark — the engine's cache-freshness check just
            # sees this as constant until the next deploy, which is correct:
            # nothing here can change without a redeploy.
            "max_updated_at": meta.get("built_at"),
            "source": "sqlite",
        }

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        row = self._connect().execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        return _row_to_node(row) if row else None

    def get_nodes(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._connect().execute(
            "SELECT * FROM nodes LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_node(r) for r in rows]

    def get_nodes_page(self, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        rows = self._connect().execute(
            "SELECT * FROM nodes ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return [_row_to_node(r) for r in rows]

    def supports_incremental_pagination(self) -> bool:
        # A baked snapshot has no live updated_at watermark to page against —
        # it's atomic per build, so incremental delta paging isn't a
        # meaningful concept here (unlike Supabase's live table). Callers
        # fall back to get_nodes_page(), which is already a cheap local
        # disk read — not the expensive operation incremental paging exists
        # to avoid in the first place.
        return False

    def get_links(self, source_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if source_id:
            rows = self._connect().execute(
                "SELECT * FROM links WHERE source = ? LIMIT ?", (source_id, limit)
            ).fetchall()
        else:
            rows = self._connect().execute(
                "SELECT * FROM links LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_link(r) for r in rows]

    def health_check(self) -> bool:
        try:
            self._connect().execute("SELECT 1 FROM nodes LIMIT 1").fetchone()
            return True
        except Exception as exc:
            logger.warning("SQLiteKnowledgeStore health_check failed: %s", exc)
            return False
