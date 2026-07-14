"""Append-only, consent-aware reference ledger for forecast evaluation.

This module intentionally uses only a de-identified subject key.  It is a local
reference implementation, not a production database integration.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from .canonical import canonical_json, stable_hash
from .contracts import ContractModel, ForecastClaim

OUTCOME_RESEARCH_PURPOSE = "outcome_research"
_SUBJECT_KEY_PATTERN = r"^subj_[0-9a-f]{16,64}$"


class LedgerError(RuntimeError):
    """Base error for ledger policy or integrity failures."""


class ImmutableLedgerError(LedgerError):
    """Raised when an existing append-only fact would be changed."""


class ConsentRequiredError(LedgerError):
    """Raised when outcome research lacks active consent."""


class LedgerDisabledError(LedgerError):
    """Raised when an outcome write is attempted while the feature is off."""


class SubjectErasedError(LedgerError):
    """Raised after the subject's research key has been tombstoned."""


class ConsentAction(StrEnum):
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"


class OutcomeStatus(StrEnum):
    OCCURRED = "occurred"
    DID_NOT_OCCUR = "did_not_occur"
    INDETERMINATE = "indeterminate"
    UNOBSERVABLE = "unobservable"


class ConsentRecord(ContractModel):
    event_id: str = Field(min_length=1)
    consent_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_key: str = Field(pattern=_SUBJECT_KEY_PATTERN)
    action: ConsentAction
    purposes: tuple[str, ...] = ()
    occurred_at: datetime
    reason: str | None = None

    @model_validator(mode="after")
    def validate_consent(self) -> ConsentRecord:
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.action is ConsentAction.GRANTED and OUTCOME_RESEARCH_PURPOSE not in self.purposes:
            raise ValueError("research consent must explicitly include outcome_research")
        if self.action is ConsentAction.WITHDRAWN and not self.reason:
            raise ValueError("consent withdrawal requires a reason")
        return self


class ModelRelease(ContractModel):
    release_id: str = Field(min_length=1)
    created_at: datetime
    manifest: dict[str, Any]
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_release(self) -> ModelRelease:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if stable_hash(self.manifest) != self.manifest_hash:
            raise ValueError("manifest_hash does not match the canonical manifest")
        return self


class OutcomeObservation(ContractModel):
    observation_id: str = Field(min_length=1)
    status: OutcomeStatus
    observed_at: datetime
    source: str = Field(min_length=1)
    observable_value: str | None = None
    notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_observation(self) -> OutcomeObservation:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return self


class ForecastResolution(ContractModel):
    resolution_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_key: str = Field(pattern=_SUBJECT_KEY_PATTERN)
    observation: OutcomeObservation
    recorded_at: datetime
    supersedes_resolution_id: str | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> ForecastResolution:
        if self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        if self.observation.observed_at > self.recorded_at:
            raise ValueError("an observation cannot be recorded before it was observed")
        if self.supersedes_resolution_id == self.resolution_id:
            raise ValueError("a resolution cannot supersede itself")
        return self


class IssuedForecast(ContractModel):
    tenant_id: str
    subject_key: str = Field(pattern=_SUBJECT_KEY_PATTERN)
    claim: ForecastClaim
    issued_at: datetime
    rendered_content: str = Field(min_length=1)
    claim_hash: str
    wording_hash: str
    content_hash: str
    point_in_time_cutoff: datetime


class SubjectExport(ContractModel):
    tenant_id: str
    subject_key: str = Field(pattern=_SUBJECT_KEY_PATTERN)
    key_state: str
    consents: tuple[dict[str, Any], ...]
    forecasts: tuple[dict[str, Any], ...]
    resolutions: tuple[dict[str, Any], ...]
    tombstones: tuple[dict[str, Any], ...]


_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS model_releases (
  release_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
  manifest_json TEXT NOT NULL, manifest_hash TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS consent_events (
  event_id TEXT PRIMARY KEY, consent_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
  subject_key TEXT NOT NULL, action TEXT NOT NULL, purposes_json TEXT NOT NULL,
  occurred_at TEXT NOT NULL, reason TEXT
);
CREATE INDEX IF NOT EXISTS consent_subject_idx
  ON consent_events(tenant_id, subject_key, occurred_at);
CREATE TABLE IF NOT EXISTS issued_forecasts (
  tenant_id TEXT NOT NULL, subject_key TEXT NOT NULL, claim_id TEXT NOT NULL,
  forecast_id TEXT NOT NULL, release_id TEXT NOT NULL, issued_at TEXT NOT NULL,
  point_in_time_cutoff TEXT NOT NULL, claim_json TEXT NOT NULL,
  claim_hash TEXT NOT NULL, wording_hash TEXT NOT NULL, content_hash TEXT NOT NULL,
  PRIMARY KEY (tenant_id, subject_key, claim_id),
  FOREIGN KEY (release_id) REFERENCES model_releases(release_id)
);
CREATE TABLE IF NOT EXISTS resolution_events (
  event_id TEXT PRIMARY KEY, resolution_id TEXT NOT NULL UNIQUE,
  tenant_id TEXT NOT NULL, subject_key TEXT NOT NULL, claim_id TEXT NOT NULL,
  resolution_json TEXT NOT NULL, recorded_at TEXT NOT NULL,
  supersedes_resolution_id TEXT,
  FOREIGN KEY (tenant_id, subject_key, claim_id)
    REFERENCES issued_forecasts(tenant_id, subject_key, claim_id),
  FOREIGN KEY (supersedes_resolution_id) REFERENCES resolution_events(resolution_id)
);
CREATE TABLE IF NOT EXISTS tombstone_events (
  event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, subject_key TEXT NOT NULL,
  requested_at TEXT NOT NULL, reason TEXT NOT NULL, key_state TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tombstone_subject_idx
  ON tombstone_events(tenant_id, subject_key, requested_at);
"""


def _immutable_triggers() -> str:
    tables = ("model_releases", "consent_events", "issued_forecasts", "resolution_events", "tombstone_events")
    statements: list[str] = []
    for table in tables:
        statements.extend(
            (
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'append-only ledger'); END;",
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'append-only ledger'); END;",
            )
        )
    return "\n".join(statements)


class SQLiteForecastLedger:
    """Local reference repository with database-enforced append-only facts."""

    def __init__(self, path: str | Path, *, outcome_writes_enabled: bool = False) -> None:
        self.path = str(path)
        self.outcome_writes_enabled = outcome_writes_enabled
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(_SCHEMA + _immutable_triggers())

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> SQLiteForecastLedger:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def register_release(self, release: ModelRelease) -> None:
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO model_releases VALUES (?, ?, ?, ?)",
                    (release.release_id, release.created_at.isoformat(), canonical_json(release.manifest), release.manifest_hash),
                )
        except sqlite3.IntegrityError as exc:
            raise ImmutableLedgerError("model release already exists and cannot be replaced") from exc

    def append_consent(self, record: ConsentRecord) -> None:
        if self._is_erased(record.tenant_id, record.subject_key):
            raise SubjectErasedError("the subject research key has been destroyed")
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO consent_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        record.event_id, record.consent_id, record.tenant_id, record.subject_key,
                        record.action.value, canonical_json(record.purposes), record.occurred_at.isoformat(), record.reason,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ImmutableLedgerError("consent event already exists and cannot be replaced") from exc

    def has_active_research_consent(self, tenant_id: str, subject_key: str) -> bool:
        row = self._db.execute(
            "SELECT action, purposes_json FROM consent_events WHERE tenant_id=? AND subject_key=? "
            "ORDER BY occurred_at DESC, rowid DESC LIMIT 1",
            (tenant_id, subject_key),
        ).fetchone()
        return bool(
            row
            and row["action"] == ConsentAction.GRANTED.value
            and OUTCOME_RESEARCH_PURPOSE in json.loads(row["purposes_json"])
            and not self._is_erased(tenant_id, subject_key)
        )

    def issue_forecast(
        self,
        tenant_id: str,
        subject_key: str,
        claim: ForecastClaim,
        *,
        issued_at: datetime,
        rendered_content: str,
    ) -> IssuedForecast:
        if issued_at.tzinfo is None:
            raise ValueError("issued_at must be timezone-aware")
        if self._is_erased(tenant_id, subject_key):
            raise SubjectErasedError("the subject research key has been destroyed")
        cutoff = claim.provenance.data_cutoff_at
        if cutoff > issued_at:
            raise ValueError("point-in-time cutoff cannot be after issuance")
        payload = canonical_json(claim)
        issued = IssuedForecast(
            tenant_id=tenant_id,
            subject_key=subject_key,
            claim=claim,
            issued_at=issued_at,
            rendered_content=rendered_content,
            claim_hash=stable_hash(claim),
            wording_hash=stable_hash(rendered_content),
            content_hash=stable_hash({"claim": claim, "rendered_content": rendered_content}),
            point_in_time_cutoff=cutoff,
        )
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO issued_forecasts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        tenant_id, subject_key, claim.claim_id, claim.forecast_id, claim.release_id,
                        issued_at.isoformat(), cutoff.isoformat(), payload, issued.claim_hash,
                        issued.wording_hash, issued.content_hash,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ImmutableLedgerError("forecast snapshot cannot be inserted or replaced") from exc
        return issued

    def append_resolution(self, event_id: str, resolution: ForecastResolution) -> None:
        if not self.outcome_writes_enabled:
            raise LedgerDisabledError("outcome ledger writes are disabled")
        if self._is_erased(resolution.tenant_id, resolution.subject_key):
            raise SubjectErasedError("the subject research key has been destroyed")
        if not self.has_active_research_consent(resolution.tenant_id, resolution.subject_key):
            raise ConsentRequiredError("active outcome_research consent is required")
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO resolution_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event_id, resolution.resolution_id, resolution.tenant_id,
                        resolution.subject_key, resolution.claim_id, canonical_json(resolution),
                        resolution.recorded_at.isoformat(), resolution.supersedes_resolution_id,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ImmutableLedgerError("resolution is invalid or would replace an existing fact") from exc

    def replay_claim(self, tenant_id: str, subject_key: str, claim_id: str) -> ForecastClaim:
        row = self._db.execute(
            "SELECT claim_json, claim_hash FROM issued_forecasts "
            "WHERE tenant_id=? AND subject_key=? AND claim_id=?",
            (tenant_id, subject_key, claim_id),
        ).fetchone()
        if row is None:
            raise KeyError(claim_id)
        claim = ForecastClaim.model_validate_json(row["claim_json"])
        if stable_hash(claim) != row["claim_hash"]:
            raise LedgerError("stored forecast failed deterministic replay integrity check")
        return claim

    def request_erasure(
        self,
        event_id: str,
        tenant_id: str,
        subject_key: str,
        *,
        requested_at: datetime,
        reason: str,
    ) -> None:
        if requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO tombstone_events VALUES (?, ?, ?, ?, ?, ?)",
                    (event_id, tenant_id, subject_key, requested_at.isoformat(), reason, "destroyed"),
                )
        except sqlite3.IntegrityError as exc:
            raise ImmutableLedgerError("erasure event already exists") from exc

    def apply_retention_policy(
        self,
        event_id: str,
        tenant_id: str,
        subject_key: str,
        *,
        retain_until: datetime,
        evaluated_at: datetime,
        reason: str = "Configured research retention period expired.",
    ) -> bool:
        """Append a crypto-erasure tombstone once a subject's retention expires.

        Production adapters must destroy the subject-specific linkage/encryption
        key when persisting this event.  Historical aggregate facts are not
        silently rewritten.  Returns ``True`` only when a tombstone was added.
        """

        if retain_until.tzinfo is None or evaluated_at.tzinfo is None:
            raise ValueError("retention timestamps must be timezone-aware")
        if evaluated_at <= retain_until or self._is_erased(tenant_id, subject_key):
            return False
        self.request_erasure(
            event_id,
            tenant_id,
            subject_key,
            requested_at=evaluated_at,
            reason=reason,
        )
        return True

    def export_subject(self, tenant_id: str, subject_key: str) -> SubjectExport:
        tombstones = self._rows("tombstone_events", tenant_id, subject_key)
        erased = bool(tombstones)
        return SubjectExport(
            tenant_id=tenant_id,
            subject_key=subject_key,
            key_state="destroyed" if erased else "active",
            consents=() if erased else tuple(self._rows("consent_events", tenant_id, subject_key)),
            forecasts=() if erased else tuple(self._rows("issued_forecasts", tenant_id, subject_key)),
            resolutions=() if erased else tuple(self._rows("resolution_events", tenant_id, subject_key)),
            tombstones=tuple(tombstones),
        )

    def replace_claim(self, *_: object, **__: object) -> None:
        raise ImmutableLedgerError("issued forecasts are immutable; append a superseding event")

    def _rows(self, table: str, tenant_id: str, subject_key: str) -> list[dict[str, Any]]:
        allowed = {"consent_events", "issued_forecasts", "resolution_events", "tombstone_events"}
        if table not in allowed:
            raise ValueError("unsupported ledger table")
        rows = self._db.execute(
            f"SELECT * FROM {table} WHERE tenant_id=? AND subject_key=? ORDER BY rowid",  # noqa: S608
            (tenant_id, subject_key),
        ).fetchall()
        return [dict(row) for row in rows]

    def _is_erased(self, tenant_id: str, subject_key: str) -> bool:
        return self._db.execute(
            "SELECT 1 FROM tombstone_events WHERE tenant_id=? AND subject_key=? LIMIT 1",
            (tenant_id, subject_key),
        ).fetchone() is not None
