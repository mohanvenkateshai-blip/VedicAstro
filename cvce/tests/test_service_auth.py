"""Portal-to-CVCE service authentication boundary."""

import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from app import server


client = TestClient(server.app)


def _configure(monkeypatch, *, token: str, required: bool) -> None:
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", token)
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", required)


def test_public_health_does_not_require_token(monkeypatch):
    _configure(monkeypatch, token="test-secret", required=True)

    response = client.get("/health")

    assert response.status_code == 200


def test_required_auth_fails_closed_when_server_token_is_missing(monkeypatch):
    _configure(monkeypatch, token="", required=True)

    response = client.get("/version")

    assert response.status_code == 503
    assert response.json() == {"detail": "Service authentication is unavailable"}


def test_protected_endpoint_rejects_missing_token(monkeypatch):
    _configure(monkeypatch, token="test-secret", required=True)

    response = client.get("/version")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_protected_endpoint_rejects_wrong_token_without_logging_secrets(
    monkeypatch, caplog
):
    _configure(monkeypatch, token="test-secret", required=True)

    response = client.get(
        "/version", headers={"x-cvce-service-token": "wrong-secret"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
    assert "test-secret" not in caplog.text
    assert "wrong-secret" not in caplog.text


def test_deep_health_is_protected(monkeypatch):
    _configure(monkeypatch, token="test-secret", required=True)

    response = client.get("/health/deep")

    assert response.status_code == 401


def test_protected_endpoint_accepts_correct_token(monkeypatch):
    _configure(monkeypatch, token="test-secret", required=True)

    response = client.get(
        "/version", headers={"x-cvce-service-token": "test-secret"}
    )

    assert response.status_code == 200
    assert response.json()["service"] == "cvce"


def test_local_dev_can_explicitly_run_without_auth(monkeypatch):
    _configure(monkeypatch, token="", required=False)

    response = client.get("/version")

    assert response.status_code == 200


def test_configured_token_enables_auth_even_when_not_required(monkeypatch):
    _configure(monkeypatch, token="test-secret", required=False)

    response = client.get("/version")

    assert response.status_code == 401


def test_fly_deployment_declares_production_environment():
    fly_config = tomllib.loads(
        (Path(__file__).parents[1] / "fly.toml").read_text(encoding="utf-8")
    )

    assert fly_config["env"]["CVCE_ENVIRONMENT"] == "production"


def test_backend_rate_limit_returns_429_with_retry_after(monkeypatch):
    _configure(monkeypatch, token="", required=False)
    monkeypatch.setattr(server.settings, "RATE_LIMIT_REQUESTS", 1)
    monkeypatch.setattr(server.settings, "RATE_LIMIT_WINDOW", 60)
    server._rate_limit_store.clear()

    first = client.post("/gochar", json={})
    second = client.post("/gochar", json={})

    assert first.status_code == 422
    assert second.status_code == 429
    assert second.json() == {"detail": "Rate limit exceeded. Try again later."}
    assert int(second.headers["retry-after"]) >= 1
    server._rate_limit_store.clear()
