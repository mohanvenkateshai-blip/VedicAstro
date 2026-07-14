"""SQLite reference store with serialized, immutable append semantics."""

from __future__ import annotations

import hashlib
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .contracts import ResearchAnnotation, TechniqueRun
from .identity import canonical_json, stable_hash
from .registries import EventRegistry, TimingRegistry

_MIGRATION = Path(__file__).with_name("migrations") / "0001_immutable_research_store.sql"
_SCHEMA_VERSION = 1
_MIGRATION_NAME = "0001_immutable_research_store"
_Registry = TypeVar("_Registry", EventRegistry, TimingRegistry)
_Result = TypeVar("_Result")
_REQUIRED_COLUMNS = {
    "research_schema_migrations": {"version", "name", "checksum", "applied_at"},
    "technique_runs": {"run_id", "run_hash", "payload_json"},
    "research_annotations": {
        "annotation_id",
        "run_id",
        "supersedes_annotation_id",
        "annotation_hash",
        "payload_json",
    },
    "event_registries": {"registry_id", "version", "registry_hash", "payload_json"},
    "timing_registries": {"registry_id", "version", "registry_hash", "payload_json"},
}
_APPEND_ONLY_TABLES = tuple(_REQUIRED_COLUMNS)


class ResearchStoreError(RuntimeError):
    """Base integrity or append-policy error."""


class ResearchStoreConflict(ResearchStoreError):
    """Raised when an immutable identity or lineage constraint is violated."""


class ResearchStoreIntegrityError(ResearchStoreError):
    """Raised when content or schema no longer matches its stable identity."""


class ResearchStoreSchemaError(ResearchStoreIntegrityError):
    """Raised when the database schema is unjournaled, unknown, or drifted."""


class ImmutableResearchStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = RLock()
        self._db = sqlite3.connect(
            self.path,
            timeout=1.0,
            isolation_level=None,
            check_same_thread=False,
        )
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA busy_timeout = 1000")
        try:
            self._initialize_schema()
            self._enable_wal()
        except Exception:
            self._db.close()
            raise

    def _initialize_schema(self) -> None:
        migration_sql = _MIGRATION.read_text(encoding="utf-8")
        checksum = hashlib.sha256(migration_sql.encode("utf-8")).hexdigest()
        last_error: sqlite3.OperationalError | None = None
        for attempt in range(8):
            try:
                self._db.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise ResearchStoreSchemaError("schema initialization failed") from exc
                last_error = exc
                time.sleep(0.02 * (attempt + 1))
                continue
            try:
                if not self._table_names():
                    for statement in _complete_sql_statements(migration_sql):
                        if not statement.lstrip().upper().startswith("PRAGMA "):
                            self._db.execute(statement)
                    self._db.execute(
                        "INSERT OR IGNORE INTO research_schema_migrations VALUES (?, ?, ?, ?)",
                        (
                            _SCHEMA_VERSION,
                            _MIGRATION_NAME,
                            checksum,
                            datetime.now(UTC).isoformat(),
                        ),
                    )
                self._verify_schema(checksum)
            except Exception:
                self._db.execute("ROLLBACK")
                raise
            self._db.execute("COMMIT")
            return
        raise ResearchStoreSchemaError(
            "could not serialize schema initialization after retries"
        ) from last_error

    def _enable_wal(self) -> None:
        last_error: sqlite3.OperationalError | None = None
        for attempt in range(8):
            try:
                self._db.execute("PRAGMA journal_mode = WAL").fetchone()
                return
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise ResearchStoreSchemaError("could not enable WAL mode") from exc
                last_error = exc
                time.sleep(0.02 * (attempt + 1))
        raise ResearchStoreSchemaError("could not enable WAL mode after retries") from last_error

    def _table_names(self) -> set[str]:
        return {
            row["name"]
            for row in self._db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }

    def _verify_schema(self, checksum: str) -> None:
        existing = self._table_names()
        if existing and "research_schema_migrations" not in existing:
            raise ResearchStoreSchemaError(
                "unjournaled legacy research schema requires an explicit reviewed migration"
            )
        journal = self._db.execute(
            "SELECT version, name, checksum FROM research_schema_migrations ORDER BY version"
        ).fetchall()
        expected = [(_SCHEMA_VERSION, _MIGRATION_NAME, checksum)]
        observed = [(row["version"], row["name"], row["checksum"]) for row in journal]
        if observed != expected:
            raise ResearchStoreSchemaError("research schema version or migration checksum mismatch")
        if set(_REQUIRED_COLUMNS) != existing:
            raise ResearchStoreSchemaError("research schema table set does not match its journal")
        for table, expected_columns in _REQUIRED_COLUMNS.items():
            observed_columns = {
                row["name"] for row in self._db.execute(f"PRAGMA table_info({table})")
            }
            if observed_columns != expected_columns:
                raise ResearchStoreSchemaError(f"research schema columns drifted for {table}")
        lineage_indexes: list[str] = []
        for index in self._db.execute("PRAGMA index_list(research_annotations)"):
            columns = tuple(
                row["name"] for row in self._db.execute(f"PRAGMA index_info({index['name']})")
            )
            if index["unique"] and columns == ("supersedes_annotation_id",):
                lineage_indexes.append(index["name"])
        if lineage_indexes != ["research_annotations_one_successor"]:
            raise ResearchStoreSchemaError(
                "annotation successor uniqueness index is missing or drifted"
            )
        expected_triggers = {
            f"{table}_no_{action}": (
                table,
                _normalized_sql(
                    f"CREATE TRIGGER {table}_no_{action} "
                    f"BEFORE {action.upper()} ON {table} "
                    "BEGIN SELECT RAISE(ABORT, 'append-only research store'); END"
                ),
            )
            for table in _APPEND_ONLY_TABLES
            for action in ("update", "delete")
        }
        triggers = {
            row["name"]: (row["tbl_name"], row["sql"] or "")
            for row in self._db.execute(
                "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger'"
            )
        }
        if set(triggers) != set(expected_triggers):
            raise ResearchStoreSchemaError("append-only trigger set is missing or drifted")
        for name, actual in triggers.items():
            table, sql = actual
            expected_table, expected_sql = expected_triggers[name]
            if table != expected_table or _normalized_sql(sql) != expected_sql:
                raise ResearchStoreSchemaError(f"append-only trigger definition drifted: {name}")

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def __enter__(self) -> ImmutableResearchStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def append_run(self, run: TechniqueRun) -> str:
        run = _revalidate_model(run)
        content_hash = stable_hash(run)

        def write(db: sqlite3.Connection) -> str:
            self._verify_run_registries(db, run)
            try:
                db.execute(
                    "INSERT INTO technique_runs (run_id, run_hash, payload_json) VALUES (?, ?, ?)",
                    (run.run_id, content_hash, canonical_json(run)),
                )
            except sqlite3.IntegrityError as exc:
                raise ResearchStoreConflict("technique run identity already exists") from exc
            return content_hash

        return self._write(write)

    def replay_run(self, run_id: str) -> TechniqueRun:
        row = self._one(
            "SELECT payload_json, run_hash AS content_hash FROM technique_runs WHERE run_id=?",
            (run_id,),
        )
        return self._validated_model(row, TechniqueRun)

    def append_annotation(self, annotation: ResearchAnnotation) -> str:
        annotation = _revalidate_model(annotation)
        content_hash = stable_hash(annotation)

        def write(db: sqlite3.Connection) -> str:
            run_row = db.execute(
                "SELECT payload_json FROM technique_runs WHERE run_id=?", (annotation.run_id,)
            ).fetchone()
            if run_row is None:
                raise ResearchStoreConflict("annotation run does not exist")
            run = TechniqueRun.model_validate_json(run_row["payload_json"])
            if annotation.prediction_id is not None and annotation.prediction_id not in {
                prediction.prediction_id for prediction in run.predictions
            }:
                raise ResearchStoreConflict("annotation prediction does not belong to its run")
            if annotation.supersedes_annotation_id is not None:
                prior_row = db.execute(
                    "SELECT payload_json FROM research_annotations WHERE annotation_id=?",
                    (annotation.supersedes_annotation_id,),
                ).fetchone()
                if prior_row is None:
                    raise ResearchStoreConflict("superseded annotation does not exist")
                prior = ResearchAnnotation.model_validate_json(prior_row["payload_json"])
                if (prior.run_id, prior.prediction_id, prior.annotation_type) != (
                    annotation.run_id,
                    annotation.prediction_id,
                    annotation.annotation_type,
                ):
                    raise ResearchStoreConflict(
                        "superseded annotation must belong to the same run, prediction, and type"
                    )
                if annotation.created_at <= prior.created_at:
                    raise ResearchStoreConflict(
                        "a successor annotation must be created after its parent"
                    )
            try:
                db.execute(
                    "INSERT INTO research_annotations "
                    "(annotation_id, run_id, supersedes_annotation_id, annotation_hash, "
                    "payload_json) VALUES (?, ?, ?, ?, ?)",
                    (
                        annotation.annotation_id,
                        annotation.run_id,
                        annotation.supersedes_annotation_id,
                        content_hash,
                        canonical_json(annotation),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ResearchStoreConflict(
                    "annotation identity is duplicate or parent already has a successor"
                ) from exc
            return content_hash

        return self._write(write)

    def replay_annotation(self, annotation_id: str) -> ResearchAnnotation:
        row = self._one(
            "SELECT payload_json, annotation_hash AS content_hash "
            "FROM research_annotations WHERE annotation_id=?",
            (annotation_id,),
        )
        return self._validated_model(row, ResearchAnnotation)

    def append_event_registry(self, registry: EventRegistry) -> str:
        return self._append_registry("event_registries", registry)

    def replay_event_registry(self, registry_id: str, version: str) -> EventRegistry:
        return self._replay_registry("event_registries", registry_id, version, EventRegistry)

    def append_timing_registry(self, registry: TimingRegistry) -> str:
        return self._append_registry("timing_registries", registry)

    def replay_timing_registry(self, registry_id: str, version: str) -> TimingRegistry:
        return self._replay_registry("timing_registries", registry_id, version, TimingRegistry)

    def _append_registry(self, table: str, registry: EventRegistry | TimingRegistry) -> str:
        registry = _revalidate_model(registry)
        content_hash = registry.registry_hash

        def write(db: sqlite3.Connection) -> str:
            try:
                db.execute(
                    f"INSERT INTO {table} "  # noqa: S608 - internal table allowlist
                    "(registry_id, version, registry_hash, payload_json) VALUES (?, ?, ?, ?)",
                    (
                        registry.registry_id,
                        registry.version,
                        content_hash,
                        canonical_json(registry),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ResearchStoreConflict("registry version already exists") from exc
            return content_hash

        return self._write(write)

    def _replay_registry(
        self,
        table: str,
        registry_id: str,
        version: str,
        model: type[_Registry],
    ) -> _Registry:
        row = self._one(
            f"SELECT payload_json, registry_hash AS content_hash FROM {table} "  # noqa: S608
            "WHERE registry_id=? AND version=?",
            (registry_id, version),
        )
        restored = model.model_validate_json(row["payload_json"])
        if restored.registry_hash != row["content_hash"]:
            raise ResearchStoreIntegrityError("stored registry failed replay identity check")
        return restored

    def _verify_run_registries(self, db: sqlite3.Connection, run: TechniqueRun) -> None:
        references = (
            (
                "event_registries",
                run.event_registry_id,
                run.event_registry_version,
                run.event_registry_hash,
                EventRegistry,
            ),
            (
                "timing_registries",
                run.timing_registry_id,
                run.timing_registry_version,
                run.timing_registry_hash,
                TimingRegistry,
            ),
        )
        for table, registry_id, version, expected_hash, model in references:
            if registry_id is None or version is None or expected_hash is None:
                raise ResearchStoreConflict("a stored run requires event and timing registry refs")
            row = db.execute(
                f"SELECT registry_hash, payload_json FROM {table} "  # noqa: S608
                "WHERE registry_id=? AND version=?",
                (registry_id, version),
            ).fetchone()
            if row is None:
                raise ResearchStoreConflict(f"referenced {table} version does not exist")
            restored = model.model_validate_json(row["payload_json"])
            if row["registry_hash"] != restored.registry_hash:
                raise ResearchStoreIntegrityError(f"stored {table} payload failed integrity check")
            if expected_hash != row["registry_hash"]:
                raise ResearchStoreConflict(
                    f"referenced {table} hash does not match stored version"
                )

    def _write(self, operation: Callable[[sqlite3.Connection], _Result]) -> _Result:
        last_error: sqlite3.OperationalError | None = None
        for attempt in range(5):
            with self._lock:
                try:
                    self._db.execute("BEGIN IMMEDIATE")
                except sqlite3.OperationalError as exc:
                    if "locked" not in str(exc).lower():
                        raise
                    last_error = exc
                else:
                    try:
                        result = operation(self._db)
                    except Exception:
                        self._db.execute("ROLLBACK")
                        raise
                    self._db.execute("COMMIT")
                    return result
            time.sleep(0.01 * (attempt + 1))
        raise ResearchStoreConflict("research store remained locked after retries") from last_error

    def _one(self, statement: str, parameters: tuple[str, ...]) -> sqlite3.Row:
        with self._lock:
            row = self._db.execute(statement, parameters).fetchone()
        if row is None:
            raise KeyError(parameters)
        return row

    @staticmethod
    def _validated_model[ModelT: BaseModel](row: sqlite3.Row, model: type[ModelT]) -> ModelT:
        restored = model.model_validate_json(row["payload_json"])
        if stable_hash(restored) != row["content_hash"]:
            raise ResearchStoreIntegrityError("stored artifact failed replay identity check")
        return restored


def _revalidate_model[ModelT: BaseModel](value: ModelT) -> ModelT:
    try:
        return type(value).model_validate_json(canonical_json(value))
    except (ValidationError, TypeError, ValueError) as exc:
        raise ResearchStoreIntegrityError(
            f"{type(value).__name__} failed canonical persistence-boundary validation"
        ) from exc


def _complete_sql_statements(script: str) -> tuple[str, ...]:
    statements: list[str] = []
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                statements.append(statement)
            buffer = ""
    if buffer.strip():
        raise ResearchStoreSchemaError("migration contains an incomplete SQL statement")
    return tuple(statements)


def _normalized_sql(value: str) -> str:
    return " ".join(value.upper().split())
