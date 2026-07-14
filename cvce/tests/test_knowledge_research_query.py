from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from knowledge_engine.engine import KnowledgeEngine
from knowledge_engine.models import InvalidationReason
from knowledge_engine.research_state import SQLiteKnowledgeResearchState
from knowledge_engine.store.base import KnowledgeStore


class StaticStore(KnowledgeStore):
    def __init__(self) -> None:
        self.nodes = [
            {"id": "valid", "content": "supported material"},
            {"id": "invalidated", "content": "disputed material"},
            {"id": "unhealthy", "content": "damaged capture", "healthy": False},
        ]

    def get_version(self) -> str:
        return "research-test-v1"

    def get_stats(self) -> dict:
        return {"node_count": len(self.nodes), "link_count": 0}

    def get_node(self, node_id: str) -> dict | None:
        return next((item for item in self.nodes if item["id"] == node_id), None)

    def get_nodes(self, limit: int = 100) -> list[dict]:
        return self.nodes[:limit]

    def get_links(self, source_id: str | None = None, limit: int = 100) -> list[dict]:
        return []

    def health_check(self) -> bool:
        return True


def engine() -> KnowledgeEngine:
    ke = KnowledgeEngine(store=StaticStore())
    ke.graph = type(
        "StaticGraph",
        (),
        {
            "nodes": ke.store.nodes,
            "links": [],
            "stats": {"nodes": 3, "links": 0},
            "node": lambda self, node_id: next(
                (item for item in self.nodes if item["id"] == node_id), None
            ),
        },
    )()
    return ke


def test_research_query_includes_invalidated_and_unhealthy_with_status() -> None:
    ke = engine()
    ke.invalidate(
        node_ids=["invalidated"],
        reason=InvalidationReason.CONFLICT,
        details="Sources disagree",
    )

    result = ke.query_research_nodes()

    assert [item["id"] for item in result["nodes"]] == [
        "invalidated",
        "unhealthy",
        "valid",
    ]
    by_id = {item["id"]: item for item in result["nodes"]}
    disputed = by_id["invalidated"]["research_status"]
    assert disputed["invalidated"] is True
    assert disputed["reason"] == "conflict"
    assert disputed["details"] == "Sources disagree"
    damaged = by_id["unhealthy"]["research_status"]
    assert damaged["node_healthy"] is False
    assert damaged["product_eligible"] is False
    assert result["status"]["include_invalidated"] is True
    assert result["status"]["include_unhealthy"] is True
    assert result["status"]["returned_count"] == 3


def test_product_query_stays_safe_while_research_filters_are_explicit() -> None:
    ke = engine()
    ke.invalidate(node_ids=["invalidated"])

    assert "invalidated" not in {item["id"] for item in ke.query_nodes()}
    result = ke.query_research_nodes(include_invalidated=False, include_unhealthy=False)
    assert [item["id"] for item in result["nodes"]] == ["valid"]


def test_revalidated_node_keeps_non_destructive_research_history() -> None:
    ke = engine()
    ke.invalidate(
        node_ids=["invalidated"],
        reason=InvalidationReason.ERROR_IN_SOURCE,
        details="Bad edition",
    )
    ke.revalidate(node_ids=["invalidated"])

    result = ke.query_research_nodes(pattern="invalidated")
    status = result["nodes"][0]["research_status"]
    assert status["invalidated"] is False
    assert status["invalidation_history"][0]["reason"] == "error_in_source"
    assert status["invalidation_history"][0]["details"] == "Bad edition"


def test_removed_invalidated_node_remains_in_research_archive() -> None:
    ke = engine()
    ke.invalidate(node_ids=["invalidated"], details="Retain this capture")
    ke.graph.nodes = [node for node in ke.graph.nodes if node["id"] != "invalidated"]
    ke.store.nodes = [node for node in ke.store.nodes if node["id"] != "invalidated"]
    ke._clear_stale_invalidations()

    result = ke.query_research_nodes(pattern="invalidated")
    assert len(result["nodes"]) == 1
    status = result["nodes"][0]["research_status"]
    assert status["archived_capture"] is True
    assert status["invalidation_history"][0]["details"] == "Retain this capture"
    assert status["removal"]["reason"] == "removed_during_refresh"
    assert status["removal"]["removed_at"]
    assert status["removal"]["last_seen_version"] == "research-test-v1"


def test_unhealthy_graph_is_still_research_queryable_when_requested() -> None:
    ke = engine()
    ke.invalidate(node_ids=[f"blocked-{index}" for index in range(50)])
    assert ke.is_knowledge_healthy() is False

    blocked = ke.query_research_nodes(include_unhealthy=False)
    assert blocked["nodes"] == []
    assert blocked["status"]["blocked_reason"] == "knowledge_unhealthy"

    exhaustive = ke.query_research_nodes(include_unhealthy=True)
    assert len(exhaustive["nodes"]) == 3
    assert all(
        item["research_status"]["knowledge_healthy"] is False for item in exhaustive["nodes"]
    )


def test_official_integration_gateway_exposes_research_query(monkeypatch) -> None:
    from knowledge_engine.integration import query_research_knowledge

    ke = engine()
    monkeypatch.setattr("knowledge_engine.integration.get_knowledge_engine", lambda: ke)
    result = query_research_knowledge(pattern="valid")
    assert [item["id"] for item in result["nodes"]] == ["valid"]
    assert "knowledge_healthy" in result["status"]


def test_research_query_unions_graph_and_paginated_store_and_deep_copies() -> None:
    store = StaticStore()
    store.nodes = [
        {"id": f"store-{index:03d}", "content": f"store {index}"} for index in range(550)
    ] + [{"id": "shared", "content": "store copy"}]
    ke = KnowledgeEngine(store=store)
    ke.graph = type(
        "LocalGraph",
        (),
        {
            "nodes": [
                {"id": "local-only", "content": "local"},
                {"id": "shared", "content": "local wins"},
            ]
        },
    )()

    result = ke.query_research_nodes(limit=3)
    all_result = ke.query_research_nodes()
    ids = [item["id"] for item in all_result["nodes"]]
    assert "local-only" in ids and "store-549" in ids
    assert len(ids) == 552
    assert (
        next(item for item in all_result["nodes"] if item["id"] == "shared")["content"]
        == "local wins"
    )
    assert result["status"]["available_count"] == 552
    assert result["status"]["returned_count"] == 3
    assert result["status"]["truncated"] is True

    all_result["nodes"][0]["content"] = "mutated by caller"
    fresh = ke.query_research_nodes()
    assert fresh["nodes"][0]["content"] != "mutated by caller"


def test_research_query_reports_incomplete_backend_pagination_as_truncated() -> None:
    class FailingPagedStore(StaticStore):
        def __init__(self) -> None:
            self.nodes = [{"id": f"node-{index:03d}"} for index in range(600)]

        def get_nodes_page(self, limit: int = 500, offset: int = 0) -> list[dict]:
            if offset:
                raise RuntimeError("backend page failed")
            return self.nodes[:limit]

    ke = KnowledgeEngine(store=FailingPagedStore())
    result = ke.query_research_nodes()
    assert result["status"]["source_enumeration_complete"] is False
    assert result["status"]["truncated"] is True


def test_supabase_page_two_http_error_is_not_treated_as_eof(monkeypatch) -> None:
    import json

    from knowledge_engine.store.supabase_store import SupabaseKnowledgeStore

    store = SupabaseKnowledgeStore.__new__(SupabaseKnowledgeStore)
    store.graph_version = "research-test-v1"
    store._env = {}
    store._embeddings_present = False
    first_page = [{"id": f"supabase-{index:03d}"} for index in range(500)]

    def fake_request(method, path, body=None):
        del method, body
        if "select=count" in path:
            return 200, json.dumps([{"count": 600}]).encode()
        if "offset=0" in path:
            return 200, json.dumps(first_page).encode()
        if "offset=500" in path:
            return 503, b"temporarily unavailable"
        return 200, b"[]"

    monkeypatch.setattr(store, "_request", fake_request)
    ke = KnowledgeEngine(store=store)
    result = ke.query_research_nodes()
    assert result["status"]["source_enumeration_complete"] is False
    assert result["status"]["truncated"] is True
    assert result["status"]["store_observed_count"] == 500
    assert result["status"]["store_expected_count"] == 600
    assert "HTTP 503" in result["status"]["source_error"]


def test_version_refresh_archives_valid_local_removal_even_if_store_still_has_it(tmp_path) -> None:
    store = StaticStore()
    store.nodes.append({"id": "removed-valid", "content": "stale store copy"})
    ke = KnowledgeEngine(store=store)

    class RefreshGraph:
        def __init__(self) -> None:
            self.nodes = [{"id": "removed-valid", "content": "old version"}]
            self.links = []
            self.stats = {"nodes": 1, "links": 0}
            self._loaded = True

        def _load(self) -> None:
            self.nodes = [{"id": "new-valid", "content": "new version"}]
            self.stats = {"nodes": 1, "links": 0}

    ke.graph = RefreshGraph()
    ke.current_version.version = "version-old"
    ke.on_new_literature_ingested(tmp_path / "new-graph.json", "version-new")
    archived = ke.query_research_nodes(pattern="removed-valid")["nodes"][0]
    removal = archived["research_status"]["removal"]
    assert removal["reason"] == "removed_during_version_change"
    assert removal["last_seen_version"] == "version-old"
    assert removal["removed_in_version"] == "version-new"


def test_ke_research_state_survives_engine_restart(tmp_path) -> None:
    store = StaticStore()
    path = tmp_path / "ke-state.sqlite3"
    first = KnowledgeEngine(
        store=store,
        research_persistence=SQLiteKnowledgeResearchState(path),
    )
    first.graph = engine().graph
    first.invalidate(
        node_ids=["invalidated"],
        reason=InvalidationReason.CONFLICT,
        details="Persisted dispute",
    )

    restarted = KnowledgeEngine(
        store=store,
        research_persistence=SQLiteKnowledgeResearchState(path),
    )
    result = restarted.query_research_nodes(pattern="invalidated")
    status = result["nodes"][0]["research_status"]
    assert status["invalidated"] is True
    assert status["details"] == "Persisted dispute"
    assert status["invalidation_history"][0]["reason"] == "conflict"


def test_removed_valid_node_archive_survives_restart(tmp_path) -> None:
    store = StaticStore()
    path = tmp_path / "ke-removal.sqlite3"
    first = KnowledgeEngine(
        store=store,
        research_persistence=SQLiteKnowledgeResearchState(path),
    )
    first.graph = engine().graph
    first._reconcile_research_snapshot("test-baseline")
    first.graph.nodes = [item for item in first.graph.nodes if item["id"] != "valid"]
    store.nodes = [item for item in store.nodes if item["id"] != "valid"]
    first._clear_stale_invalidations()

    restarted = KnowledgeEngine(
        store=store,
        research_persistence=SQLiteKnowledgeResearchState(path),
    )
    result = restarted.query_research_nodes(pattern="valid")
    status = result["nodes"][0]["research_status"]
    assert status["archived_capture"] is True
    assert status["removal"]["removed_at"]
    assert status["removal"]["reason"] == "removed_during_refresh"


def test_ke_owned_state_mutations_are_concurrency_safe(tmp_path) -> None:
    ke = KnowledgeEngine(
        store=StaticStore(),
        research_persistence=SQLiteKnowledgeResearchState(tmp_path / "ke-concurrent.sqlite3"),
    )
    ids = [f"concurrent-{index}" for index in range(40)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        tuple(pool.map(lambda node_id: ke.invalidate(node_ids=[node_id]), ids))
    assert set(ids).issubset(set(ke.invalidated_node_ids()))


def test_singleton_reset_restores_durable_ke_state(monkeypatch, tmp_path) -> None:
    import knowledge_engine.integration as integration

    store = StaticStore()
    path = tmp_path / "singleton.sqlite3"
    engine_class = KnowledgeEngine
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("KE_USE_SUPABASE", raising=False)
    monkeypatch.setattr(
        integration,
        "KnowledgeEngine",
        lambda: engine_class(
            store=store,
            research_persistence=SQLiteKnowledgeResearchState(path),
        ),
    )
    integration.clear_knowledge_engine_cache()
    integration.get_knowledge_engine().invalidate(
        node_ids=["invalidated"], details="Across singleton reset"
    )
    integration.clear_knowledge_engine_cache()
    restored = integration.get_knowledge_engine()
    assert restored.get_validity("invalidated").details == "Across singleton reset"
    integration.clear_knowledge_engine_cache()


def test_singleton_creation_is_concurrency_safe(monkeypatch) -> None:
    import knowledge_engine.integration as integration

    engine_class = KnowledgeEngine
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("KE_USE_SUPABASE", raising=False)
    monkeypatch.setattr(integration, "KnowledgeEngine", lambda: engine_class(store=StaticStore()))
    integration.clear_knowledge_engine_cache()
    with ThreadPoolExecutor(max_workers=12) as pool:
        instances = tuple(pool.map(lambda _: integration.get_knowledge_engine(), range(48)))
    assert len({id(instance) for instance in instances}) == 1
    integration.clear_knowledge_engine_cache()


def test_explicit_research_mode_requires_durability(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("KE_RESEARCH_STATE_DB", raising=False)
    with pytest.raises(RuntimeError, match="requires db_path"):
        KnowledgeEngine.for_research(store=StaticStore())
    durable = KnowledgeEngine.for_research(
        store=StaticStore(), db_path=tmp_path / "required-ke.sqlite3"
    )
    assert durable.research_persistence is not None


def test_peer_ke_instances_reload_shared_durable_state(tmp_path) -> None:
    path = tmp_path / "shared-ke.sqlite3"
    first = KnowledgeEngine.for_research(store=StaticStore(), db_path=path)
    second = KnowledgeEngine.for_research(store=StaticStore(), db_path=path)
    first.invalidate(node_ids=["invalidated"], details="peer update")
    assert second.get_validity("invalidated").details == "peer update"
    second.revalidate(node_ids=["invalidated"])
    assert first.is_node_valid("invalidated") is True
