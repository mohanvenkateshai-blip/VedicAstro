"""Transactional SQLite persistence for KnowledgeEngine research-only state."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


class SQLiteKnowledgeResearchState:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS ke_meta (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ke_current_invalidations (
                    node_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ke_invalidation_history (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL, payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ke_history_lookup
                    ON ke_invalidation_history(node_id, event_id);
                CREATE TABLE IF NOT EXISTS ke_node_archive (
                    node_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ke_graph_snapshot (
                    node_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL
                );
                INSERT OR IGNORE INTO ke_meta(key, value)
                    VALUES ('schema_version', '1');
                COMMIT;
                """
            )
            row = connection.execute(
                "SELECT value FROM ke_meta WHERE key = 'schema_version'"
            ).fetchone()
            if row is None or int(row[0]) != SCHEMA_VERSION:
                raise RuntimeError("unsupported KE research-state schema version")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    @staticmethod
    def _dump(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def save_ke_invalidation(self, node_id: str, payload: dict[str, Any]) -> None:
        encoded = self._dump(payload)
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "INSERT OR REPLACE INTO ke_current_invalidations VALUES (?, ?)",
                    (node_id, encoded),
                )
                connection.execute(
                    "INSERT INTO ke_invalidation_history(node_id, payload_json) VALUES (?, ?)",
                    (node_id, encoded),
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def remove_ke_invalidations(self, node_ids: tuple[str, ...] | None = None) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                if node_ids is None:
                    connection.execute("DELETE FROM ke_current_invalidations")
                else:
                    connection.executemany(
                        "DELETE FROM ke_current_invalidations WHERE node_id = ?",
                        ((node_id,) for node_id in node_ids),
                    )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def save_ke_archive(
        self, node_id: str, payload: dict[str, Any], metadata: dict[str, Any]
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "INSERT OR REPLACE INTO ke_node_archive VALUES (?, ?, ?)",
                    (node_id, self._dump(payload), self._dump(metadata)),
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def replace_ke_graph_snapshot(
        self, nodes: dict[str, dict[str, Any]], version: str | None
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute("DELETE FROM ke_graph_snapshot")
                connection.executemany(
                    "INSERT INTO ke_graph_snapshot VALUES (?, ?)",
                    ((node_id, self._dump(payload)) for node_id, payload in nodes.items()),
                )
                connection.execute(
                    "INSERT OR REPLACE INTO ke_meta(key, value) VALUES (?, ?)",
                    ("snapshot_version", version or ""),
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def load_ke_state(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            current = connection.execute(
                "SELECT node_id, payload_json FROM ke_current_invalidations ORDER BY node_id"
            ).fetchall()
            history = connection.execute(
                "SELECT node_id, payload_json FROM ke_invalidation_history ORDER BY event_id"
            ).fetchall()
            archive = connection.execute(
                "SELECT node_id, payload_json, metadata_json FROM ke_node_archive ORDER BY node_id"
            ).fetchall()
            snapshot = connection.execute(
                "SELECT node_id, payload_json FROM ke_graph_snapshot ORDER BY node_id"
            ).fetchall()
            version_row = connection.execute(
                "SELECT value FROM ke_meta WHERE key = 'snapshot_version'"
            ).fetchone()
        grouped: dict[str, list[dict[str, Any]]] = {}
        for node_id, payload in history:
            grouped.setdefault(node_id, []).append(json.loads(payload))
        return {
            "current": {node_id: json.loads(payload) for node_id, payload in current},
            "history": grouped,
            "archive": {
                node_id: {"node": json.loads(payload), "metadata": json.loads(metadata)}
                for node_id, payload, metadata in archive
            },
            "snapshot": {node_id: json.loads(payload) for node_id, payload in snapshot},
            "snapshot_version": version_row[0] if version_row and version_row[0] else None,
        }
