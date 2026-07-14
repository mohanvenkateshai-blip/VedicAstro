from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app import server
from fastapi.testclient import TestClient
from research_engine import (
    DEFAULT_EVENT_REGISTRY,
    DEFAULT_TIMING_REGISTRY,
    RawPrediction,
    ResearchAnnotation,
    RunStatus,
    TechniqueConfiguration,
    TechniqueRun,
    stable_hash,
)
from research_engine import service as research_service

client = TestClient(server.app)
TOKEN = "research-A7v9-K2m4-Q8x6-Z1p3-N5w0"
PRODUCT_TOKEN = "product-B8w0-L3n5-R9y7-A2q4-M6x1"
HEADERS = {"x-cvce-research-token": TOKEN}
RAW_BIRTH_MARKER = "1975-04-22T19:15:00 private marker"
RAW_PROSE_MARKER = "Exact sensitive source prose marker"


def raw_run() -> TechniqueRun:
    payload = {"birth_input": RAW_BIRTH_MARKER, "native_flags": [1, 0, 1]}
    return TechniqueRun(
        run_id="raw-service-run",
        configuration=TechniqueConfiguration(
            configuration_id="raw-config",
            technique_code="unrestricted_native_technique",
            technique_version="source-v1",
            implementation_version="test-v1",
        ),
        original_input_payload=payload,
        original_input_payload_hash=stable_hash(payload),
        event_registry_id=DEFAULT_EVENT_REGISTRY.registry_id,
        event_registry_version=DEFAULT_EVENT_REGISTRY.version,
        event_registry_hash=DEFAULT_EVENT_REGISTRY.registry_hash,
        timing_registry_id=DEFAULT_TIMING_REGISTRY.registry_id,
        timing_registry_version=DEFAULT_TIMING_REGISTRY.version,
        timing_registry_hash=DEFAULT_TIMING_REGISTRY.registry_hash,
        started_at=datetime(2026, 7, 14, 10, tzinfo=UTC),
        completed_at=datetime(2026, 7, 14, 10, 1, tzinfo=UTC),
        status=RunStatus.COMPLETED,
        predictions=(
            RawPrediction(
                prediction_id="raw-prediction",
                event_code="unknown.sensitive.native.event",
                original_prose=RAW_PROSE_MARKER,
                original_payload={"unmapped": {"nested": [1, True, None]}},
            ),
        ),
    )


@pytest.fixture(autouse=True)
def research_configuration(monkeypatch, tmp_path):
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "RESEARCH_MODE_ENABLED", True)
    monkeypatch.setattr(server.settings, "RESEARCH_DB_PATH", str(tmp_path / "research.sqlite3"))
    monkeypatch.setattr(server.settings, "RESEARCH_MOUNT_PATH", str(tmp_path))
    monkeypatch.setattr(server.settings, "RESEARCH_SERVICE_TOKEN", TOKEN)
    server.clear_research_service_cache()
    yield
    server.clear_research_service_cache()


def test_research_plane_fails_closed_when_disabled_unauthenticated_or_misconfigured(
    monkeypatch,
):
    monkeypatch.setattr(server.settings, "RESEARCH_MODE_ENABLED", False)
    assert client.get("/research/health").status_code == 404

    monkeypatch.setattr(server.settings, "RESEARCH_MODE_ENABLED", True)
    assert client.get("/research/health").status_code == 401
    assert client.get("/research/health", headers={"x-cvce-research-token": "wrong"}).status_code == 401

    # Product and research credentials are intentionally non-interchangeable.
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "product-service-secret")
    assert (
        client.get(
            "/research/health",
            headers={"x-cvce-service-token": "product-service-secret"},
        ).status_code
        == 401
    )
    assert client.get("/version", headers=HEADERS).status_code == 401
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")

    monkeypatch.setattr(server.settings, "RESEARCH_DB_PATH", "")
    assert client.get("/research/health", headers=HEADERS).status_code == 503
    monkeypatch.setattr(server.settings, "RESEARCH_DB_PATH", ":memory:")
    assert client.get("/research/health", headers=HEADERS).status_code == 503

    monkeypatch.setattr(server.settings, "RESEARCH_DB_PATH", "/tmp/research.sqlite3")
    monkeypatch.setattr(server.settings, "RESEARCH_SERVICE_TOKEN", "")
    assert client.get("/research/health", headers=HEADERS).status_code == 503


def test_raw_append_replay_query_is_policy_isolated_and_non_mutating(monkeypatch, caplog):
    def forbidden_product_policy(*_args, **_kwargs):
        raise AssertionError("product policy entered raw research plane")

    monkeypatch.setattr(server, "apply_product_claim_policy", forbidden_product_policy)
    import prediction_policy

    monkeypatch.setattr(prediction_policy, "apply_product_claim_policy", forbidden_product_policy)

    for path, registry in (
        ("/research/registries/events", DEFAULT_EVENT_REGISTRY),
        ("/research/registries/timing", DEFAULT_TIMING_REGISTRY),
    ):
        response = client.post(path, headers=HEADERS, json=registry.model_dump(mode="json"))
        assert response.status_code == 201, response.text

    original = raw_run()
    created = client.post(
        "/research/runs", headers=HEADERS, json=original.model_dump(mode="json")
    )
    assert created.status_code == 201, created.text
    assert created.json()["record"]["original_input_payload"]["birth_input"] == RAW_BIRTH_MARKER
    assert created.json()["record"]["predictions"][0]["original_prose"] == RAW_PROSE_MARKER

    listing = client.get(
        "/research/runs",
        headers=HEADERS,
        params={"event_code": "unknown.sensitive.native.event"},
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    caller_copy = created.json()
    caller_copy["record"]["original_input_payload"]["birth_input"] = "product-mutated"
    replayed = client.get(f"/research/runs/{original.run_id}", headers=HEADERS)
    assert replayed.status_code == 200
    assert replayed.json()["record"]["original_input_payload"]["birth_input"] == RAW_BIRTH_MARKER

    annotation = ResearchAnnotation(
        annotation_id="raw-annotation",
        run_id=original.run_id,
        prediction_id="raw-prediction",
        annotation_type="unrestricted_research_note",
        payload={"verbatim_note": RAW_PROSE_MARKER},
        created_at=datetime(2026, 7, 14, 11, tzinfo=UTC),
        actor_id="researcher",
    )
    response = client.post(
        "/research/annotations", headers=HEADERS, json=annotation.model_dump(mode="json")
    )
    assert response.status_code == 201, response.text
    queried = client.get(
        "/research/annotations", headers=HEADERS, params={"run_id": original.run_id}
    )
    assert queried.json()["records"][0]["record"]["payload"]["verbatim_note"] == RAW_PROSE_MARKER

    assert client.get("/research/registries/events", headers=HEADERS).json()["total"] == 1
    assert client.get("/research/registries/timing", headers=HEADERS).json()["total"] == 1
    assert RAW_BIRTH_MARKER not in caplog.text
    assert RAW_PROSE_MARKER not in caplog.text


def test_research_token_must_be_strong_distinct_and_production_mount_verified(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", TOKEN)
    assert client.get("/research/health", headers=HEADERS).status_code == 503

    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", PRODUCT_TOKEN)
    monkeypatch.setattr(server.settings, "RESEARCH_SERVICE_TOKEN", "weak-token")
    assert client.get("/research/health", headers={"x-cvce-research-token": "weak-token"}).status_code == 503

    monkeypatch.setattr(server.settings, "RESEARCH_SERVICE_TOKEN", TOKEN)
    monkeypatch.setattr(server.settings, "ENVIRONMENT", "production")
    assert client.get("/research/health", headers=HEADERS).status_code == 503
    monkeypatch.setattr(
        research_service, "_PRODUCTION_RESEARCH_MOUNT_PATH", tmp_path
    )
    monkeypatch.setattr(research_service.os.path, "ismount", lambda _path: True)
    assert client.get("/research/health", headers=HEADERS).status_code == 503
    monkeypatch.setattr(research_service, "_has_dedicated_device", lambda _path: True)
    assert client.get("/research/health", headers=HEADERS).status_code == 200


def test_production_durability_rejects_root_filesystem_even_when_it_is_a_mount(
    monkeypatch,
):
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", PRODUCT_TOKEN)
    monkeypatch.setattr(server.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(server.settings, "RESEARCH_MOUNT_PATH", "/")
    monkeypatch.setattr(server.settings, "RESEARCH_DB_PATH", "/tmp/research.sqlite3")
    monkeypatch.setattr(research_service.os, "access", lambda _path, _mode: True)
    monkeypatch.setattr(research_service.os.path, "ismount", lambda _path: True)
    assert client.get("/research/health", headers=HEADERS).status_code == 503


def test_request_parser_rejects_wrong_media_type_duplicates_and_oversize():
    payload = DEFAULT_EVENT_REGISTRY.model_dump(mode="json")
    body = json.dumps(payload)
    assert client.post(
        "/research/registries/events",
        headers={**HEADERS, "content-type": "text/plain"},
        content=body,
    ).status_code == 415

    duplicate = '{"registry_id":"shadow",' + body.lstrip()[1:]
    assert client.post(
        "/research/registries/events",
        headers={**HEADERS, "content-type": "application/json"},
        content=duplicate,
    ).status_code == 422

    oversized = b'{"padding":"' + b"x" * (2 * 1024 * 1024) + b'"}'
    assert client.post(
        "/research/registries/events",
        headers={**HEADERS, "content-type": "application/json"},
        content=oversized,
    ).status_code == 413


@pytest.mark.parametrize("declared_length", [None, "1"])
def test_streaming_body_limit_rejects_missing_or_lying_content_length(declared_length):
    def oversized_chunks():
        yield b'{"padding":"'
        yield b"x" * (1024 * 1024)
        yield b"x" * (1024 * 1024)
        yield b'"}'

    headers = {**HEADERS, "content-type": "application/json"}
    if declared_length is not None:
        headers["content-length"] = declared_length
    response = client.post(
        "/research/registries/events",
        headers=headers,
        content=oversized_chunks(),
    )
    assert response.status_code == 413


def test_sql_pagination_replays_only_requested_records(monkeypatch):
    for path, registry in (
        ("/research/registries/events", DEFAULT_EVENT_REGISTRY),
        ("/research/registries/timing", DEFAULT_TIMING_REGISTRY),
    ):
        assert client.post(path, headers=HEADERS, json=registry.model_dump(mode="json")).status_code == 201
    for index in range(5):
        run = raw_run().model_copy(update={"run_id": f"bounded-{index}"})
        assert client.post("/research/runs", headers=HEADERS, json=run.model_dump(mode="json")).status_code == 201

    calls = 0
    original = research_service.ImmutableResearchStore.replay_run

    def counted_replay(store, run_id):
        nonlocal calls
        calls += 1
        return original(store, run_id)

    monkeypatch.setattr(research_service.ImmutableResearchStore, "replay_run", counted_replay)
    response = client.get("/research/runs", headers=HEADERS, params={"limit": 2, "offset": 1})
    assert response.status_code == 200
    assert response.json()["total"] == 5
    assert len(response.json()["records"]) == 2
    assert calls == 2
    assert client.get(
        "/research/runs", headers=HEADERS, params={"offset": 1_000_001}
    ).status_code == 422
    assert client.get(
        "/research/runs", headers=HEADERS, params={"event_code": "x" * 257}
    ).status_code == 422


def test_shutdown_hook_and_fly_research_mount_is_explicitly_opt_in():
    assert server.clear_research_service_cache in server.app.router.on_shutdown
    fly = tomllib.loads((Path(__file__).parents[1] / "fly.toml").read_text(encoding="utf-8"))
    assert "mounts" not in fly
    assert "CVCE_RESEARCH_MODE_ENABLED" not in fly["env"]
    assert "CVCE_RESEARCH_MOUNT_PATH" not in fly["env"]

    research_fly = tomllib.loads(
        (Path(__file__).parents[1] / "fly.research.toml").read_text(encoding="utf-8")
    )
    assert research_fly["mounts"]["destination"] == "/data/research"
    assert research_fly["env"]["CVCE_RESEARCH_MODE_ENABLED"] == "true"
    assert research_fly["env"]["CVCE_RESEARCH_DB_PATH"].startswith("/data/research/")
    assert research_fly["env"]["CVCE_RESEARCH_MOUNT_PATH"] == "/data/research"
    assert "CVCE_RESEARCH_SERVICE_TOKEN" not in research_fly["env"]
