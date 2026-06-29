"""Tests for GraphRAG transit rules provider (Phase 4)."""

import pytest


@pytest.fixture(autouse=True)
def _reset_graph_rules_env(monkeypatch):
    monkeypatch.delenv("CVCE_GRAPH_AS_RULES", raising=False)
    from graph_rag.rules_provider import GraphTransitRules
    GraphTransitRules._instance = None


def test_graph_rules_disabled_by_default():
    from graph_rag.rules_provider import graph_rules_enabled, active_transit_rules

    assert graph_rules_enabled() is False
    assert active_transit_rules() is None


def test_graph_rules_enabled_when_env_set(monkeypatch):
    monkeypatch.setenv("CVCE_GRAPH_AS_RULES", "1")
    from graph_rag.rules_provider import graph_rules_enabled, active_transit_rules

    assert graph_rules_enabled() is True
    rules = active_transit_rules()
    assert rules is not None
    sun = rules.transit_houses("Sun")
    assert 5 in sun["worst"]
    assert 10 in sun["good"]


def test_graph_house_quality_sun_worst(monkeypatch):
    monkeypatch.setenv("CVCE_GRAPH_AS_RULES", "true")
    from graph_rag.rules_provider import GraphTransitRules

    GraphTransitRules._instance = None
    rules = GraphTransitRules()
    quality, verdict, score = rules.house_quality("Sun", 5)
    assert quality == "worst"
    assert verdict == "ashubh"
    assert score == -10


def test_predict_health_rules_source(monkeypatch):
    monkeypatch.setenv("CVCE_GRAPH_AS_RULES", "1")
    from fastapi.testclient import TestClient
    from app.server import app

    client = TestClient(app)
    health = client.get("/predict/health")
    assert health.status_code == 200
    data = health.json()
    if data.get("available"):
        assert data["graph_rag"]["rules_source"] in ("graph", "hardcoded")
    assert "graph_rag_grok" in data


def test_predict_health_production_node_count(monkeypatch):
    monkeypatch.setenv("CVCE_GRAPH_AS_RULES", "1")
    from fastapi.testclient import TestClient
    from app.server import app
    from graph_rag.production_floor import production_node_floor

    client = TestClient(app)
    health = client.get("/predict/health")
    assert health.status_code == 200
    data = health.json()
    if data.get("available") and data.get("graph_rag", {}).get("available"):
        assert data["graph_rag"]["stats"]["nodes"] >= production_node_floor()


def test_predict_health_grok_endpoint():
    from fastapi.testclient import TestClient
    from app.server import app

    client = TestClient(app)
    resp = client.get("/predict/health/grok")
    if resp.status_code == 200:
        body = resp.json()
        assert body["initiative"] == "grok"
        assert body["graph_rag"]["nodes"] > 0
    else:
        assert resp.status_code == 404
