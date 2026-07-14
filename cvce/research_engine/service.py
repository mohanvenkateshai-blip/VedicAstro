"""Authenticated HTTP plane for immutable, policy-neutral research records.

This module deliberately depends only on the raw research contracts and store.
It must not import product projection, prediction policy, product taxonomy, or
verbalization code. Every returned record is replayed through the immutable
store's hash and schema validation before serialization.
"""

from __future__ import annotations

import json
import math
import os
import secrets
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path as FilePath
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi import Path as ApiPath
from pydantic import BaseModel, ValidationError

from .contracts import ResearchAnnotation, RunStatus, TechniqueRun
from .registries import EventRegistry, TimingRegistry
from .store import (
    ImmutableResearchStore,
    ResearchStoreConflict,
    ResearchStoreIntegrityError,
)

RESEARCH_TOKEN_HEADER = "x-cvce-research-token"
_MAX_PAGE_SIZE = 500
_MAX_OFFSET = 1_000_000
_MAX_REQUEST_BYTES = 2 * 1024 * 1024
_MIN_TOKEN_BYTES = 32
_MIN_TOKEN_ENTROPY_BITS_PER_CHAR = 3.0
_PRODUCTION_RESEARCH_MOUNT_PATH = FilePath("/data/research")


@dataclass(frozen=True)
class ResearchServiceConfiguration:
    enabled: bool
    database_path: str
    service_token: str
    product_service_token: str
    mount_path: str
    environment: str

    @classmethod
    def from_settings(cls, settings: Any) -> ResearchServiceConfiguration:
        return cls(
            enabled=bool(settings.RESEARCH_MODE_ENABLED),
            database_path=str(settings.RESEARCH_DB_PATH).strip(),
            service_token=str(settings.RESEARCH_SERVICE_TOKEN).strip(),
            product_service_token=str(getattr(settings, "SERVICE_TOKEN", "")).strip(),
            mount_path=str(getattr(settings, "RESEARCH_MOUNT_PATH", "")).strip(),
            environment=str(settings.ENVIRONMENT).strip().lower(),
        )

    def require_ready(self) -> None:
        if not self.enabled:
            raise HTTPException(status_code=404, detail="Research service is disabled")
        if not _is_strong_token(self.service_token):
            raise HTTPException(
                status_code=503,
                detail="Research service authentication is unavailable",
            )
        if self.environment in {"production", "prod"} and not self.product_service_token:
            raise HTTPException(
                status_code=503,
                detail="Research service authentication is unavailable",
            )
        if self.product_service_token and secrets.compare_digest(
            self.service_token.encode("utf-8"), self.product_service_token.encode("utf-8")
        ):
            raise HTTPException(
                status_code=503,
                detail="Research service authentication is unavailable",
            )
        if not _is_durable_database_path(
            self.database_path, self.mount_path, production=self.environment in {"production", "prod"}
        ):
            raise HTTPException(
                status_code=503,
                detail="Research service durable storage is unavailable",
            )


class RawResearchService:
    """Small service facade that preserves store replay validation."""

    def __init__(self, database_path: str) -> None:
        if not database_path.strip() or _is_memory_database(database_path):
            raise ValueError("raw research service requires durable storage")
        self.database_path = database_path
        self.store = ImmutableResearchStore(database_path)

    def close(self) -> None:
        self.store.close()

    def append_run(self, run: TechniqueRun) -> dict[str, Any]:
        content_hash = self.store.append_run(run)
        return _record_response(content_hash, self.store.replay_run(run.run_id))

    def replay_run(self, run_id: str) -> dict[str, Any]:
        run = self.store.replay_run(run_id)
        return _record_response(_stable_record_hash(run), run)

    def list_runs(
        self,
        *,
        event_code: str | None,
        technique_code: str | None,
        run_status: RunStatus | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        clauses: list[str] = []
        parameters: list[str] = []
        if event_code:
            clauses.append(
                "EXISTS (SELECT 1 FROM json_each(payload_json, '$.predictions') "
                "WHERE json_extract(value, '$.event_code') = ?)"
            )
            parameters.append(event_code)
        if technique_code:
            clauses.append("json_extract(payload_json, '$.configuration.technique_code') = ?")
            parameters.append(technique_code)
        if run_status:
            clauses.append("json_extract(payload_json, '$.status') = ?")
            parameters.append(run_status.value)
        identities, total = self._paged_identities(
            "technique_runs", "run_id", clauses, parameters, limit, offset
        )
        return {
            "records": [self.replay_run(run_id) for run_id in identities],
            "total": total,
        }

    def append_annotation(self, annotation: ResearchAnnotation) -> dict[str, Any]:
        content_hash = self.store.append_annotation(annotation)
        return _record_response(
            content_hash, self.store.replay_annotation(annotation.annotation_id)
        )

    def replay_annotation(self, annotation_id: str) -> dict[str, Any]:
        annotation = self.store.replay_annotation(annotation_id)
        return _record_response(_stable_record_hash(annotation), annotation)

    def list_annotations(
        self,
        *,
        run_id: str | None,
        prediction_id: str | None,
        annotation_type: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        clauses: list[str] = []
        parameters: list[str] = []
        for field, value in (
            ("run_id", run_id),
            ("prediction_id", prediction_id),
            ("annotation_type", annotation_type),
        ):
            if value:
                clauses.append(f"json_extract(payload_json, '$.{field}') = ?")  # noqa: S608
                parameters.append(value)
        identities, total = self._paged_identities(
            "research_annotations", "annotation_id", clauses, parameters, limit, offset
        )
        return {
            "records": [self.replay_annotation(item) for item in identities],
            "total": total,
        }

    def append_registry(
        self, kind: Literal["events", "timing"], registry: EventRegistry | TimingRegistry
    ) -> dict[str, Any]:
        if kind == "events":
            assert isinstance(registry, EventRegistry)
            content_hash = self.store.append_event_registry(registry)
            restored = self.store.replay_event_registry(registry.registry_id, registry.version)
        else:
            assert isinstance(registry, TimingRegistry)
            content_hash = self.store.append_timing_registry(registry)
            restored = self.store.replay_timing_registry(registry.registry_id, registry.version)
        return _record_response(content_hash, restored)

    def replay_registry(
        self, kind: Literal["events", "timing"], registry_id: str, version: str
    ) -> dict[str, Any]:
        if kind == "events":
            record = self.store.replay_event_registry(registry_id, version)
        else:
            record = self.store.replay_timing_registry(registry_id, version)
        return _record_response(record.registry_hash, record)

    def list_registries(
        self, kind: Literal["events", "timing"], *, limit: int, offset: int
    ) -> dict[str, Any]:
        table = "event_registries" if kind == "events" else "timing_registries"
        identities, total = self._paged_registry_identities(table, limit, offset)
        records = [self.replay_registry(kind, registry_id, version) for registry_id, version in identities]
        return {
            "records": records,
            "total": total,
        }

    def _paged_identities(
        self,
        table: str,
        column: str,
        clauses: list[str],
        parameters: list[str],
        limit: int,
        offset: int,
    ) -> tuple[tuple[str, ...], int]:
        if (table, column) not in {
            ("technique_runs", "run_id"),
            ("research_annotations", "annotation_id"),
        }:
            raise ValueError("unsupported research identity query")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with _read_connection(self.database_path) as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM {table}{where}", parameters  # noqa: S608
                ).fetchone()[0]
            )
            rows = connection.execute(
                f"SELECT {column} FROM {table}{where} ORDER BY rowid LIMIT ? OFFSET ?",  # noqa: S608
                (*parameters, limit, offset),
            ).fetchall()
        return tuple(str(row[0]) for row in rows), total

    def _paged_registry_identities(
        self, table: str, limit: int, offset: int
    ) -> tuple[tuple[tuple[str, str], ...], int]:
        if table not in {"event_registries", "timing_registries"}:
            raise ValueError("unsupported research registry query")
        with _read_connection(self.database_path) as connection:
            total = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # noqa: S608
            rows = connection.execute(
                f"SELECT registry_id, version FROM {table} "  # noqa: S608
                "ORDER BY rowid LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return tuple((str(row[0]), str(row[1])) for row in rows), total


class _ServiceProvider:
    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self._lock = threading.RLock()
        self._service: RawResearchService | None = None
        self._database_path: str | None = None

    def configuration(self) -> ResearchServiceConfiguration:
        return ResearchServiceConfiguration.from_settings(self.settings)

    def get(self) -> RawResearchService:
        configuration = self.configuration()
        configuration.require_ready()
        with self._lock:
            if self._service is None or self._database_path != configuration.database_path:
                if self._service is not None:
                    self._service.close()
                try:
                    self._service = RawResearchService(configuration.database_path)
                except (OSError, ValueError, sqlite3.Error, ResearchStoreIntegrityError) as exc:
                    raise HTTPException(
                        status_code=503,
                        detail="Research service durable storage is unavailable",
                    ) from exc
                self._database_path = configuration.database_path
            return self._service

    def clear(self) -> None:
        with self._lock:
            if self._service is not None:
                self._service.close()
            self._service = None
            self._database_path = None


def create_research_router(settings: Any) -> tuple[APIRouter, Callable[[], None]]:
    """Build the isolated router and return a cache-clear hook for tests/lifecycle."""

    router = APIRouter(prefix="/research", tags=["raw-research"])
    provider = _ServiceProvider(settings)

    def authenticate(request: Request) -> None:
        configuration = provider.configuration()
        configuration.require_ready()
        supplied = request.headers.get(RESEARCH_TOKEN_HEADER, "")
        if not secrets.compare_digest(
            supplied.encode("utf-8"), configuration.service_token.encode("utf-8")
        ):
            raise HTTPException(status_code=401, detail="Unauthorized")

    dependency = Depends(authenticate)

    @router.get("/health", dependencies=[dependency])
    def research_health() -> dict[str, str]:
        provider.get()
        return {"status": "ready", "mode": "raw_research"}

    @router.post("/runs", status_code=status.HTTP_201_CREATED, dependencies=[dependency])
    async def append_run(request: Request) -> dict[str, Any]:
        run = await _request_model(request, TechniqueRun)
        return _translate_store_errors(lambda: provider.get().append_run(run))

    @router.get("/runs", dependencies=[dependency])
    def list_runs(
        event_code: Annotated[str | None, Query(max_length=256)] = None,
        technique_code: Annotated[str | None, Query(max_length=256)] = None,
        run_status: Annotated[RunStatus | None, Query(alias="status")] = None,
        limit: Annotated[int, Query(ge=1, le=_MAX_PAGE_SIZE)] = 100,
        offset: Annotated[int, Query(ge=0, le=_MAX_OFFSET)] = 0,
    ) -> dict[str, Any]:
        return _translate_store_errors(
            lambda: provider.get().list_runs(
                event_code=event_code,
                technique_code=technique_code,
                run_status=run_status,
                limit=limit,
                offset=offset,
            )
        )

    @router.get("/runs/{run_id}", dependencies=[dependency])
    def replay_run(
        run_id: Annotated[str, ApiPath(min_length=1, max_length=256)],
    ) -> dict[str, Any]:
        return _translate_store_errors(lambda: provider.get().replay_run(run_id))

    @router.post(
        "/annotations", status_code=status.HTTP_201_CREATED, dependencies=[dependency]
    )
    async def append_annotation(request: Request) -> dict[str, Any]:
        annotation = await _request_model(request, ResearchAnnotation)
        return _translate_store_errors(
            lambda: provider.get().append_annotation(annotation)
        )

    @router.get("/annotations", dependencies=[dependency])
    def list_annotations(
        run_id: Annotated[str | None, Query(max_length=256)] = None,
        prediction_id: Annotated[str | None, Query(max_length=256)] = None,
        annotation_type: Annotated[str | None, Query(max_length=256)] = None,
        limit: Annotated[int, Query(ge=1, le=_MAX_PAGE_SIZE)] = 100,
        offset: Annotated[int, Query(ge=0, le=_MAX_OFFSET)] = 0,
    ) -> dict[str, Any]:
        return _translate_store_errors(
            lambda: provider.get().list_annotations(
                run_id=run_id,
                prediction_id=prediction_id,
                annotation_type=annotation_type,
                limit=limit,
                offset=offset,
            )
        )

    @router.get("/annotations/{annotation_id}", dependencies=[dependency])
    def replay_annotation(
        annotation_id: Annotated[str, ApiPath(min_length=1, max_length=256)],
    ) -> dict[str, Any]:
        return _translate_store_errors(
            lambda: provider.get().replay_annotation(annotation_id)
        )

    @router.post(
        "/registries/events", status_code=status.HTTP_201_CREATED, dependencies=[dependency]
    )
    async def append_event_registry(request: Request) -> dict[str, Any]:
        registry = await _request_model(request, EventRegistry, computed_hash="registry_hash")
        return _translate_store_errors(
            lambda: provider.get().append_registry("events", registry)
        )

    @router.get("/registries/events", dependencies=[dependency])
    def list_event_registries(
        limit: Annotated[int, Query(ge=1, le=_MAX_PAGE_SIZE)] = 100,
        offset: Annotated[int, Query(ge=0, le=_MAX_OFFSET)] = 0,
    ) -> dict[str, Any]:
        return _translate_store_errors(
            lambda: provider.get().list_registries("events", limit=limit, offset=offset)
        )

    @router.get("/registries/events/{registry_id}/{version}", dependencies=[dependency])
    def replay_event_registry(
        registry_id: Annotated[str, ApiPath(min_length=1, max_length=256)],
        version: Annotated[str, ApiPath(min_length=1, max_length=128)],
    ) -> dict[str, Any]:
        return _translate_store_errors(
            lambda: provider.get().replay_registry("events", registry_id, version)
        )

    @router.post(
        "/registries/timing", status_code=status.HTTP_201_CREATED, dependencies=[dependency]
    )
    async def append_timing_registry(request: Request) -> dict[str, Any]:
        registry = await _request_model(request, TimingRegistry, computed_hash="registry_hash")
        return _translate_store_errors(
            lambda: provider.get().append_registry("timing", registry)
        )

    @router.get("/registries/timing", dependencies=[dependency])
    def list_timing_registries(
        limit: Annotated[int, Query(ge=1, le=_MAX_PAGE_SIZE)] = 100,
        offset: Annotated[int, Query(ge=0, le=_MAX_OFFSET)] = 0,
    ) -> dict[str, Any]:
        return _translate_store_errors(
            lambda: provider.get().list_registries("timing", limit=limit, offset=offset)
        )

    @router.get("/registries/timing/{registry_id}/{version}", dependencies=[dependency])
    def replay_timing_registry(
        registry_id: Annotated[str, ApiPath(min_length=1, max_length=256)],
        version: Annotated[str, ApiPath(min_length=1, max_length=128)],
    ) -> dict[str, Any]:
        return _translate_store_errors(
            lambda: provider.get().replay_registry("timing", registry_id, version)
        )

    return router, provider.clear


def _translate_store_errors(operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return operation()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Research record not found") from exc
    except ResearchStoreConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ResearchStoreIntegrityError as exc:
        raise HTTPException(status_code=500, detail="Research record integrity failure") from exc


async def _request_model[ModelT: BaseModel](
    request: Request,
    model: type[ModelT],
    *,
    computed_hash: str | None = None,
) -> ModelT:
    """Validate from JSON bytes so strict tuple/datetime contracts retain JSON semantics."""

    try:
        media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            raise HTTPException(status_code=415, detail="Content-Type must be application/json")
        body = await _read_limited_body(request)
        payload = json.loads(body, object_pairs_hook=_reject_duplicate_keys)
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        declared_hash = payload.pop(computed_hash, None) if computed_hash else None
        restored = model.model_validate_json(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        )
        if computed_hash and declared_hash is not None:
            if not secrets.compare_digest(str(declared_hash), str(getattr(restored, computed_hash))):
                raise ValueError(f"declared {computed_hash} does not match payload")
        return restored
    except HTTPException:
        raise
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid raw research record") from exc


async def _read_limited_body(request: Request) -> bytes:
    """Consume the ASGI stream without ever retaining more than the hard cap."""

    declared_size = request.headers.get("content-length")
    if declared_size is not None:
        size = int(declared_size)
        if size < 0:
            raise ValueError("Content-Length cannot be negative")
        if size > _MAX_REQUEST_BYTES:
            raise HTTPException(status_code=413, detail="Raw research record is too large")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > _MAX_REQUEST_BYTES:
            raise HTTPException(status_code=413, detail="Raw research record is too large")
        body.extend(chunk)
    return bytes(body)


def _read_connection(database_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path, timeout=5)
    connection.execute("PRAGMA query_only = ON")
    return connection


def _record_response(content_hash: str, record: Any) -> dict[str, Any]:
    return {"content_hash": content_hash, "record": record.model_dump(mode="json")}


def _stable_record_hash(record: Any) -> str:
    from .identity import stable_hash

    return stable_hash(record)


def _is_memory_database(path: str) -> bool:
    normalized = path.strip().lower()
    return normalized == ":memory:" or "mode=memory" in normalized


def _is_strong_token(value: str) -> bool:
    encoded = value.encode("utf-8")
    if len(encoded) < _MIN_TOKEN_BYTES or not value:
        return False
    counts = {character: value.count(character) for character in set(value)}
    entropy = -sum(
        (count / len(value)) * math.log2(count / len(value)) for count in counts.values()
    )
    return entropy >= _MIN_TOKEN_ENTROPY_BITS_PER_CHAR


def _is_durable_database_path(database_path: str, mount_path: str, *, production: bool) -> bool:
    if not database_path or _is_memory_database(database_path) or not mount_path:
        return False
    try:
        mount = FilePath(mount_path).expanduser().resolve(strict=True)
        database = FilePath(database_path).expanduser().resolve(strict=False)
        if not mount.is_dir() or not os.access(mount, os.W_OK):
            return False
        database.relative_to(mount)
        if database == mount:
            return False
        if production:
            expected_mount = _PRODUCTION_RESEARCH_MOUNT_PATH.resolve(strict=False)
            if mount != expected_mount or mount == FilePath(mount.anchor):
                return False
            if not os.path.ismount(mount) or not _has_dedicated_device(mount):
                return False
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _has_dedicated_device(mount: FilePath) -> bool:
    """Exclude bind-mounted or ordinary directories on Fly's root device."""

    return mount.stat().st_dev != FilePath(mount.anchor).stat().st_dev


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result
