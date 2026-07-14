"""Thread-safe SQLite timeline ledger with database-enforced append semantics."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..identity import canonical_json, stable_hash
from .contracts import (
    MilestoneEvidenceLink,
    MilestoneOrigin,
    MilestonePredictionLink,
    MilestoneResolution,
    PersonTimeline,
    TimelineMilestone,
)

_MIGRATION = Path(__file__).with_name("migrations") / "0001_timeline_ledger.sql"
_Result = TypeVar("_Result")


class TimelineStoreError(RuntimeError):
    pass


class TimelineStoreConflict(TimelineStoreError):
    pass


class TimelineStoreIntegrityError(TimelineStoreError):
    pass


class SQLiteTimelineStore:
    """Durable local development store; all facts are immutable and replayable."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = RLock()
        self._db = sqlite3.connect(
            self.path,
            timeout=2.0,
            isolation_level=None,
            check_same_thread=False,
        )
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA busy_timeout = 2000")
        try:
            self._initialize()
            self._db.execute("PRAGMA journal_mode = WAL").fetchone()
        except Exception:
            self._db.close()
            raise

    def _initialize(self) -> None:
        sql = _MIGRATION.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode()).hexdigest()
        for attempt in range(8):
            try:
                self._db.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower() or attempt == 7:
                    raise TimelineStoreIntegrityError("timeline schema initialization failed") from exc
                time.sleep(0.02 * (attempt + 1))
                continue
            try:
                tables = {
                    row["name"]
                    for row in self._db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                }
                if not tables:
                    for statement in _complete_sql_statements(sql):
                        if not statement.lstrip().upper().startswith("PRAGMA "):
                            self._db.execute(statement)
                    self._db.execute(
                        "INSERT INTO timeline_schema_migrations VALUES (?, ?, ?, ?)",
                        (1, "0001_timeline_ledger", checksum, datetime.now(UTC).isoformat()),
                    )
                row = self._db.execute(
                    "SELECT version, name, checksum FROM timeline_schema_migrations"
                ).fetchone()
                if row is None or tuple(row) != (1, "0001_timeline_ledger", checksum):
                    raise TimelineStoreIntegrityError("timeline schema migration drift detected")
            except Exception:
                self._db.execute("ROLLBACK")
                raise
            self._db.execute("COMMIT")
            return

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def __enter__(self) -> SQLiteTimelineStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def append_timeline(self, timeline: PersonTimeline) -> str:
        timeline = _revalidate(timeline)
        content_hash = stable_hash(timeline)

        def write(db: sqlite3.Connection) -> str:
            try:
                db.execute(
                    "INSERT INTO person_timelines VALUES (?, ?, ?, ?)",
                    (
                        timeline.timeline_id,
                        timeline.subject.reference_id,
                        content_hash,
                        canonical_json(timeline),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise TimelineStoreConflict("timeline identity already exists") from exc
            return content_hash

        return self._write(write)

    def replay_timeline(self, timeline_id: str) -> PersonTimeline:
        return self._replay(
            "SELECT payload_json, content_hash FROM person_timelines WHERE timeline_id=?",
            (timeline_id,),
            PersonTimeline,
        )

    def append_milestone(self, milestone: TimelineMilestone) -> str:
        milestone = _revalidate(milestone)
        content_hash = stable_hash(milestone)

        def write(db: sqlite3.Connection) -> str:
            timeline = self._timeline_row(db, milestone.timeline_id)
            owner = PersonTimeline.model_validate_json(timeline["payload_json"])
            if owner.subject.reference_id != milestone.subject_reference_id:
                raise TimelineStoreConflict("milestone subject does not own its timeline")
            if milestone.origin is MilestoneOrigin.PROSPECTIVE_PREDICTION:
                assert milestone.sealed_match_criteria is not None
                assert milestone.sealed_match_criteria_hash is not None
                sealed_criteria = _validated_match_criteria(
                    milestone.sealed_match_criteria,
                    milestone.sealed_match_criteria_hash,
                )
                if sealed_criteria.canonical_event_id != milestone.canonical_event_id:
                    raise TimelineStoreConflict(
                        "seal-time matching criteria must bind the prediction event"
                    )
            if milestone.origin is MilestoneOrigin.RETROSPECTIVE_HYPOTHESIS:
                assert milestone.known_event_milestone_id is not None
                known_event = self._milestone_row(db, milestone.known_event_milestone_id)
                if known_event.origin not in {
                    MilestoneOrigin.OBSERVED_EVENT,
                    MilestoneOrigin.IMPORTED_HISTORY,
                }:
                    raise TimelineStoreConflict(
                        "retrospective hypothesis must reference observed/imported history"
                    )
                if known_event.timeline_id != milestone.timeline_id:
                    raise TimelineStoreConflict("retrospective hypothesis must share event timeline")
                if milestone.created_at < known_event.created_at:
                    raise TimelineStoreConflict(
                        "retrospective hypothesis cannot predate its known event record"
                    )
            if milestone.supersedes_milestone_id is not None:
                prior = self._milestone_row(db, milestone.supersedes_milestone_id)
                if prior.origin is MilestoneOrigin.PROSPECTIVE_PREDICTION:
                    raise TimelineStoreConflict("sealed prospective predictions cannot be superseded")
                if milestone.origin is not prior.origin:
                    raise TimelineStoreConflict("a correction cannot convert milestone origin")
                if (
                    milestone.timeline_id != prior.timeline_id
                    or milestone.subject_reference_id != prior.subject_reference_id
                    or milestone.canonical_event_id != prior.canonical_event_id
                ):
                    raise TimelineStoreConflict("a correction must retain subject, timeline, and event")
                if milestone.created_at <= prior.created_at:
                    raise TimelineStoreConflict("a correction must be recorded after its parent")
            try:
                db.execute(
                    "INSERT INTO timeline_milestones VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        milestone.milestone_id,
                        milestone.timeline_id,
                        milestone.origin.value,
                        milestone.origin_identity_hash,
                        milestone.supersedes_milestone_id,
                        milestone.created_at.isoformat(),
                        content_hash,
                        canonical_json(milestone),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise TimelineStoreConflict(
                    "milestone identity is duplicate or correction parent already has a successor"
                ) from exc
            return content_hash

        return self._write(write)

    def replay_milestone(self, milestone_id: str) -> TimelineMilestone:
        return self._replay(
            "SELECT payload_json, content_hash FROM timeline_milestones WHERE milestone_id=?",
            (milestone_id,),
            TimelineMilestone,
        )

    def list_milestones(self, timeline_id: str) -> tuple[TimelineMilestone, ...]:
        with self._lock:
            rows = self._db.execute(
                "SELECT payload_json, content_hash FROM timeline_milestones "
                "WHERE timeline_id=? ORDER BY created_at, milestone_id",
                (timeline_id,),
            ).fetchall()
        return tuple(self._validated(row, TimelineMilestone) for row in rows)

    def append_prediction_link(self, link: MilestonePredictionLink) -> str:
        link = _revalidate(link)
        content_hash = stable_hash(link)

        def write(db: sqlite3.Connection) -> str:
            milestone = self._milestone_row(db, link.milestone_id)
            prediction = self._milestone_row(db, link.prediction_milestone_id)
            if prediction.origin is not link.prediction_origin:
                raise TimelineStoreConflict("prediction link origin does not match stored identity")
            if (
                milestone.timeline_id != prediction.timeline_id
                or milestone.subject_reference_id != prediction.subject_reference_id
            ):
                raise TimelineStoreConflict("prediction link cannot cross subject or timeline")
            if link.raw_prediction_id != prediction.origin_record_id:
                raise TimelineStoreConflict(
                    "raw prediction id is not bound to the stored prediction origin"
                )
            proof = link.temporal_order_proof
            if (
                proof.prediction_created_at != prediction.created_at
                or proof.prediction_sealed_at != prediction.sealed_at
            ):
                raise TimelineStoreConflict(
                    "temporal-order proof does not match the stored prediction snapshot"
                )
            from .matcher import MatchCriteria, MatchDisposition, match_milestones

            criteria = MatchCriteria.model_validate(
                {**link.match_criteria, "criteria_hash": link.criteria_hash}, strict=False
            )
            if criteria.canonical_event_id != prediction.canonical_event_id:
                raise TimelineStoreConflict("matching criteria are not bound to the prediction event")
            if milestone.milestone_id == prediction.milestone_id:
                from .contracts import LinkRelation

                if link.relation is not LinkRelation.PREDICTED:
                    raise TimelineStoreConflict("a prediction self-link must use relation predicted")
                if proof.outcome_known_at is not None:
                    raise TimelineStoreConflict("prediction self-link cannot claim a known outcome")
            else:
                result = match_milestones(prediction, milestone, criteria)
                from .contracts import LinkRelation

                expected_relation = {
                    MatchDisposition.MATCH: LinkRelation.MATCHED,
                    MatchDisposition.PARTIAL_MATCH: LinkRelation.PARTIAL_MATCH,
                    MatchDisposition.NO_MATCH: LinkRelation.UNRELATED,
                }[result.disposition]
                if link.relation is not expected_relation:
                    raise TimelineStoreConflict("link relation contradicts the frozen matcher result")
                if proof.outcome_known_at != milestone.created_at:
                    raise TimelineStoreConflict(
                        "temporal-order proof does not match outcome knowledge time"
                    )
            self._insert_artifact(
                db,
                "milestone_prediction_links",
                "link_id",
                link.link_id,
                content_hash,
                link,
                (link.milestone_id, link.prediction_milestone_id),
            )
            return content_hash

        return self._write(write)

    def replay_prediction_link(self, link_id: str) -> MilestonePredictionLink:
        return self._replay(
            "SELECT payload_json, content_hash FROM milestone_prediction_links WHERE link_id=?",
            (link_id,),
            MilestonePredictionLink,
        )

    def append_evidence_link(self, link: MilestoneEvidenceLink) -> str:
        link = _revalidate(link)
        content_hash = stable_hash(link)

        def write(db: sqlite3.Connection) -> str:
            self._milestone_row(db, link.milestone_id)
            self._insert_artifact(
                db,
                "milestone_evidence_links",
                "evidence_link_id",
                link.evidence_link_id,
                content_hash,
                link,
                (link.milestone_id,),
            )
            return content_hash

        return self._write(write)

    def replay_evidence_link(self, evidence_link_id: str) -> MilestoneEvidenceLink:
        return self._replay(
            "SELECT payload_json, content_hash FROM milestone_evidence_links WHERE evidence_link_id=?",
            (evidence_link_id,),
            MilestoneEvidenceLink,
        )

    def append_resolution(self, resolution: MilestoneResolution) -> str:
        resolution = _revalidate(resolution)
        content_hash = stable_hash(resolution)

        def write(db: sqlite3.Connection) -> str:
            prediction = self._milestone_row(db, resolution.prediction_milestone_id)
            if prediction.origin is not MilestoneOrigin.PROSPECTIVE_PREDICTION:
                raise TimelineStoreConflict("only sealed prospective predictions can be resolved")
            assert prediction.sealed_match_criteria is not None
            assert prediction.sealed_match_criteria_hash is not None
            criteria = _validated_match_criteria(
                prediction.sealed_match_criteria,
                prediction.sealed_match_criteria_hash,
            )
            if resolution.match_criteria is not None:
                supplied = dict(resolution.match_criteria)
                supplied_hash = supplied.pop("criteria_hash", None)
                supplied_criteria = _freeze_match_criteria_input(supplied)
                if supplied_hash is not None and supplied_hash != supplied_criteria.criteria_hash:
                    raise TimelineStoreConflict(
                        "resolution matching criteria contain an invalid criteria hash"
                    )
                if supplied_criteria.criteria_hash != prediction.sealed_match_criteria_hash:
                    raise TimelineStoreConflict(
                        "resolution matching criteria differ from the sealed prediction criteria"
                    )
            if resolution.status.value in {"miss", "false_alarm"}:
                if resolution.resolved_at < prediction.window.end_at:
                    raise TimelineStoreConflict(
                        "miss or false alarm cannot be resolved before the prediction window ends"
                    )
            if resolution.observed_milestone_id is not None:
                observed = self._milestone_row(db, resolution.observed_milestone_id)
                if observed.origin not in {
                    MilestoneOrigin.OBSERVED_EVENT,
                    MilestoneOrigin.IMPORTED_HISTORY,
                }:
                    raise TimelineStoreConflict("resolution outcome must be observed/imported history")
                if observed.timeline_id != prediction.timeline_id:
                    raise TimelineStoreConflict("resolution milestones must share a timeline")
                if observed.subject_reference_id != prediction.subject_reference_id:
                    raise TimelineStoreConflict("resolution milestones must share a protected subject")
                if resolution.resolved_at < observed.created_at:
                    raise TimelineStoreConflict("resolution cannot predate the known outcome")
                if resolution.actual_window != observed.window:
                    raise TimelineStoreConflict(
                        "resolution actual interval must match the immutable observed event"
                    )
            if resolution.status.value in {"hit", "partial_hit"}:
                assert resolution.observed_milestone_id is not None
                from .matcher import MatchDisposition, match_milestones

                result = match_milestones(prediction, observed, criteria)
                expected = (
                    MatchDisposition.MATCH
                    if resolution.status.value == "hit"
                    else MatchDisposition.PARTIAL_MATCH
                )
                if result.disposition is not expected:
                    raise TimelineStoreConflict(
                        "resolution status contradicts its frozen matcher result"
                    )
            if resolution.supersedes_resolution_id is not None:
                row = db.execute(
                    "SELECT payload_json FROM milestone_resolutions WHERE resolution_id=?",
                    (resolution.supersedes_resolution_id,),
                ).fetchone()
                if row is None:
                    raise TimelineStoreConflict("superseded resolution does not exist")
                prior = MilestoneResolution.model_validate_json(row["payload_json"])
                if prior.prediction_milestone_id != resolution.prediction_milestone_id:
                    raise TimelineStoreConflict("resolution correction must retain prediction identity")
                if resolution.resolved_at <= prior.resolved_at:
                    raise TimelineStoreConflict("resolution correction must follow its parent")
            try:
                db.execute(
                    "INSERT INTO milestone_resolutions VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        resolution.resolution_id,
                        resolution.prediction_milestone_id,
                        resolution.supersedes_resolution_id,
                        resolution.resolved_at.isoformat(),
                        content_hash,
                        canonical_json(resolution),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise TimelineStoreConflict(
                    "resolution identity is duplicate or parent already has a successor"
                ) from exc
            return content_hash

        return self._write(write)

    def replay_resolution(self, resolution_id: str) -> MilestoneResolution:
        return self._replay(
            "SELECT payload_json, content_hash FROM milestone_resolutions WHERE resolution_id=?",
            (resolution_id,),
            MilestoneResolution,
        )

    def current_resolution(self, prediction_milestone_id: str) -> MilestoneResolution | None:
        with self._lock:
            row = self._db.execute(
                "SELECT r.payload_json, r.content_hash FROM milestone_resolutions r "
                "WHERE r.prediction_milestone_id=? AND NOT EXISTS ("
                "SELECT 1 FROM milestone_resolutions child "
                "WHERE child.supersedes_resolution_id=r.resolution_id) "
                "ORDER BY r.resolved_at DESC LIMIT 1",
                (prediction_milestone_id,),
            ).fetchone()
        return None if row is None else self._validated(row, MilestoneResolution)

    def list_current_resolutions(self, timeline_id: str) -> tuple[MilestoneResolution, ...]:
        """Return the current leaf of each prediction's linear resolution chain."""

        with self._lock:
            rows = self._db.execute(
                "SELECT r.payload_json, r.content_hash FROM milestone_resolutions r "
                "JOIN timeline_milestones prediction "
                "ON prediction.milestone_id=r.prediction_milestone_id "
                "WHERE prediction.timeline_id=? AND NOT EXISTS ("
                "SELECT 1 FROM milestone_resolutions child "
                "WHERE child.supersedes_resolution_id=r.resolution_id) "
                "ORDER BY r.resolved_at, r.resolution_id",
                (timeline_id,),
            ).fetchall()
        return tuple(self._validated(row, MilestoneResolution) for row in rows)

    def _write(self, operation: Callable[[sqlite3.Connection], _Result]) -> _Result:
        last_error: sqlite3.OperationalError | None = None
        for attempt in range(6):
            with self._lock:
                try:
                    self._db.execute("BEGIN IMMEDIATE")
                    result = operation(self._db)
                    self._db.execute("COMMIT")
                    return result
                except sqlite3.OperationalError as exc:
                    if self._db.in_transaction:
                        self._db.execute("ROLLBACK")
                    if "locked" not in str(exc).lower():
                        raise
                    last_error = exc
                except Exception:
                    if self._db.in_transaction:
                        self._db.execute("ROLLBACK")
                    raise
            time.sleep(0.01 * (attempt + 1))
        raise TimelineStoreConflict("timeline store remained locked after retries") from last_error

    @staticmethod
    def _timeline_row(db: sqlite3.Connection, timeline_id: str) -> sqlite3.Row:
        row = db.execute(
            "SELECT payload_json FROM person_timelines WHERE timeline_id=?", (timeline_id,)
        ).fetchone()
        if row is None:
            raise TimelineStoreConflict("timeline does not exist")
        return row

    @staticmethod
    def _milestone_row(db: sqlite3.Connection, milestone_id: str) -> TimelineMilestone:
        row = db.execute(
            "SELECT payload_json FROM timeline_milestones WHERE milestone_id=?", (milestone_id,)
        ).fetchone()
        if row is None:
            raise TimelineStoreConflict("milestone does not exist")
        return TimelineMilestone.model_validate_json(row["payload_json"])

    @staticmethod
    def _insert_artifact(
        db: sqlite3.Connection,
        table: str,
        id_column: str,
        artifact_id: str,
        content_hash: str,
        artifact: BaseModel,
        foreign_values: tuple[str, ...],
    ) -> None:
        values = (artifact_id, *foreign_values, content_hash, canonical_json(artifact))
        placeholders = ", ".join("?" for _ in values)
        try:
            db.execute(
                f"INSERT INTO {table} VALUES ({placeholders})",  # noqa: S608
                values,
            )
        except sqlite3.IntegrityError as exc:
            raise TimelineStoreConflict(f"{id_column} already exists or has invalid lineage") from exc

    def _replay[ModelT: BaseModel](
        self, statement: str, parameters: tuple[str, ...], model: type[ModelT]
    ) -> ModelT:
        with self._lock:
            row = self._db.execute(statement, parameters).fetchone()
        if row is None:
            raise KeyError(parameters)
        return self._validated(row, model)

    @staticmethod
    def _validated[ModelT: BaseModel](row: sqlite3.Row, model: type[ModelT]) -> ModelT:
        # Verify the exact persisted payload before model validation adds any
        # newly introduced optional defaults. This preserves append-only hash
        # integrity while keeping older ledger rows replayable after a
        # backwards-compatible contract extension.
        raw_payload = json.loads(row["payload_json"])
        if stable_hash(raw_payload) != row["content_hash"]:
            raise TimelineStoreIntegrityError("stored timeline artifact failed replay hash")
        # JSON-mode validation intentionally accepts the serialized forms of
        # strict datetimes, enums and tuples while retaining strict contracts.
        return model.model_validate_json(row["payload_json"])


def _revalidate[ModelT: BaseModel](value: ModelT) -> ModelT:
    try:
        return type(value).model_validate_json(canonical_json(value))
    except (ValidationError, TypeError, ValueError) as exc:
        raise TimelineStoreIntegrityError("timeline artifact failed persistence validation") from exc


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
        raise TimelineStoreIntegrityError("migration contains incomplete SQL")
    return tuple(statements)


TimelineStore = SQLiteTimelineStore


def _validated_match_criteria(payload: dict[str, object], expected_hash: str):
    from .matcher import MatchCriteria

    try:
        return MatchCriteria.model_validate(
            {**payload, "criteria_hash": expected_hash}, strict=False
        )
    except ValidationError as exc:
        raise TimelineStoreIntegrityError("sealed matching criteria failed validation") from exc


def _freeze_match_criteria_input(payload: dict[str, object]):
    from .matcher import MatchCriteria

    values = dict(payload)
    accepted = values.get("accepted_event_ids")
    if isinstance(accepted, list):
        values["accepted_event_ids"] = tuple(accepted)
    try:
        return MatchCriteria.freeze(**values)
    except (TypeError, ValidationError, ValueError) as exc:
        raise TimelineStoreConflict("resolution matching criteria are invalid") from exc
