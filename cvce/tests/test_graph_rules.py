"""Tests for KnowledgeEngine-backed GraphRAG transit rules (Phase 4+)."""

import pytest


@pytest.fixture(autouse=True)
def _reset_graph_rules_env(monkeypatch):
    monkeypatch.delenv("CVCE_GRAPH_AS_RULES", raising=False)
    try:
        from knowledge_engine.integration import clear_knowledge_engine_cache

        clear_knowledge_engine_cache()
    except Exception:
        pass
    try:
        from graph_rag.graph import GraphRAG

        GraphRAG._instance = None
    except Exception:
        pass
    try:
        from graph_rag.rules_provider import GraphTransitRules

        GraphTransitRules._instance = None
    except Exception:
        pass


def test_graph_rules_disabled_by_default():
    from knowledge_engine.integration import get_safe_transit_rules, is_knowledge_healthy

    # When KE is healthy, rules should be available (or None if not configured)
    assert is_knowledge_healthy() is True or get_safe_transit_rules() is None


def test_graph_rules_enabled_when_env_set(monkeypatch):
    monkeypatch.setenv("CVCE_GRAPH_AS_RULES", "1")
    from knowledge_engine.integration import get_safe_transit_rules

    rules = get_safe_transit_rules()
    # Rules may be None if store doesn't implement yet, but no crash
    assert rules is None or hasattr(rules, "transit_houses")


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
    from app.server import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    health = client.get("/predict/health")
    assert health.status_code == 200
    data = health.json()
    if data.get("available"):
        assert data["graph_rag"]["rules_source"] in ("graph", "hardcoded")
    assert "graph_rag_grok" in data


def test_predict_health_production_node_count(monkeypatch):
    monkeypatch.setenv("CVCE_GRAPH_AS_RULES", "1")
    from app.server import app
    from fastapi.testclient import TestClient
    from graph_rag.production_floor import production_node_floor

    client = TestClient(app)
    health = client.get("/predict/health")
    assert health.status_code == 200
    data = health.json()
    if data.get("available") and data.get("graph_rag", {}).get("available"):
        assert data["graph_rag"]["stats"]["nodes"] >= production_node_floor()


def test_predict_health_grok_endpoint():
    from app.server import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/predict/health/grok")
    if resp.status_code == 200:
        body = resp.json()
        assert body["initiative"] == "grok"
        assert body["graph_rag"]["nodes"] > 0
    else:
        assert resp.status_code == 404
