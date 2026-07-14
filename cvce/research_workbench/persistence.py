"""Transactional SQLite persistence for research captures and KE research state."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2


class SQLiteResearchPersistence:
    """Small additive reference adapter with process-local and SQLite locking."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS research_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS research_captures (
                    capture_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS research_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    capture_id TEXT NOT NULL,
                    hypothesis_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    UNIQUE(capture_id, hypothesis_id, revision)
                );
                CREATE INDEX IF NOT EXISTS research_assessment_lookup
                    ON research_assessments(capture_id, hypothesis_id, created_at);
                CREATE TABLE IF NOT EXISTS ke_current_invalidations (
                    node_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ke_invalidation_history (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ke_history_lookup
                    ON ke_invalidation_history(node_id, event_id);
                CREATE TABLE IF NOT EXISTS ke_node_archive (
                    node_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ke_graph_snapshot (
                    node_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                INSERT OR IGNORE INTO research_meta(key, value)
                    VALUES ('schema_version', '2');
                COMMIT;
                """
            )
            row = connection.execute(
                "SELECT value FROM research_meta WHERE key = 'schema_version'"
            ).fetchone()
            if row is None or int(row[0]) != SCHEMA_VERSION:
                raise RuntimeError("unsupported research persistence schema version")

    @staticmethod
    def _dump(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _load(value: str) -> dict[str, Any]:
        return json.loads(value)

    def save_capture(self, payload: dict[str, Any]) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "INSERT INTO research_captures VALUES (?, ?, ?, ?)",
                    (
                        payload["capture_id"],
                        self._dump(payload),
                        payload["checksum_sha256"],
                        payload["captured_at"],
                    ),
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def save_assessment(self, payload: dict[str, Any]) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "INSERT INTO research_assessments VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        payload["assessment_id"],
                        payload["capture_id"],
                        payload["hypothesis_id"],
                        self._dump(payload),
                        payload["assessed_at"],
                        payload["revision"],
                    ),
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def load_captures(self) -> tuple[dict[str, Any], ...]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM research_captures ORDER BY created_at, capture_id"
            ).fetchall()
        return tuple(self._load(row[0]) for row in rows)

    def load_assessments(self) -> tuple[dict[str, Any], ...]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM research_assessments "
                "ORDER BY capture_id, hypothesis_id, revision, assessment_id"
            ).fetchall()
        return tuple(self._load(row[0]) for row in rows)

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
                    "INSERT OR IGNORE INTO ke_node_archive VALUES (?, ?, ?)",
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
                    "INSERT OR REPLACE INTO research_meta(key, value) VALUES (?, ?)",
                    ("ke_snapshot_version", version or ""),
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
                "SELECT value FROM research_meta WHERE key = 'ke_snapshot_version'"
            ).fetchone()
        grouped_history: dict[str, list[dict[str, Any]]] = {}
        for row in history:
            grouped_history.setdefault(row[0], []).append(self._load(row[1]))
        return {
            "current": {row[0]: self._load(row[1]) for row in current},
            "history": grouped_history,
            "archive": {
                row[0]: {"node": self._load(row[1]), "metadata": self._load(row[2])}
                for row in archive
            },
            "snapshot": {row[0]: self._load(row[1]) for row in snapshot},
            "snapshot_version": version_row[0] if version_row and version_row[0] else None,
        }
