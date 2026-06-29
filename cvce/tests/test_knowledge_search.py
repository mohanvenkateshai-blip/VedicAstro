"""Tests for KnowledgeEngine vector / hybrid search."""

import json

import pytest


@pytest.fixture
def supabase_store_with_embeddings(monkeypatch):
    from knowledge_engine.store.supabase_store import SupabaseKnowledgeStore

    store = SupabaseKnowledgeStore.__new__(SupabaseKnowledgeStore)
    store.graph_version = "test-v1"
    store._env = {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "key"}
    store._embeddings_present = True

    fake_results = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "source_id": "muhurta_timing.md",
            "chunk_index": 0,
            "content": "Muhurta selection for marriage and travel begins with tithi and nakshatra.",
            "similarity": 0.91,
        }
    ]

    def fake_request(method, path, body=None):
        if method == "POST" and "/rpc/match_corpus_chunks" in path:
            return 200, json.dumps(fake_results).encode()
        if method == "GET" and "embedding=not.is.null" in path:
            return 200, json.dumps([{"id": "x"}]).encode()
        return 404, b"[]"

    monkeypatch.setattr(store, "_embed_query", lambda q: [0.1] * 768)
    monkeypatch.setattr(store, "_request", fake_request)
    return store


def test_ke_search_muhurta_with_embeddings(supabase_store_with_embeddings):
    from knowledge_engine.engine import KnowledgeEngine

    ke = KnowledgeEngine(store=supabase_store_with_embeddings)
    results = ke.search("muhurta")

    assert len(results) > 0
    assert any(
        "muhurta" in (r.get("content") or "").lower()
        or "muhurta" in (r.get("source_id") or "").lower()
        for r in results
    )


def test_search_falls_back_to_keyword_without_embeddings(monkeypatch):
    from knowledge_engine.store.supabase_store import SupabaseKnowledgeStore

    store = SupabaseKnowledgeStore.__new__(SupabaseKnowledgeStore)
    store.graph_version = "test-v1"
    store._env = {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "key"}
    store._embeddings_present = False

    keyword_hit = [{"source_id": "notes.md", "content": "muhurta basics", "chunk_index": 0}]

    def fake_request(method, path, body=None):
        if method == "GET" and "embedding=not.is.null" in path:
            return 200, b"[]"
        if method == "GET" and "content=ilike" in path:
            return 200, json.dumps(keyword_hit).encode()
        return 404, b"[]"

    monkeypatch.setattr(store, "_request", fake_request)

    results = store.search("muhurta")
    assert len(results) == 1
    assert "muhurta" in results[0]["content"]


def test_on_embeddings_updated_clears_cache(supabase_store_with_embeddings):
    from knowledge_engine.engine import KnowledgeEngine

    ke = KnowledgeEngine(store=supabase_store_with_embeddings)
    supabase_store_with_embeddings._embeddings_present = True
    supabase_store_with_embeddings.mark_embeddings_updated()
    assert supabase_store_with_embeddings._embeddings_present is None

    result = ke.on_embeddings_updated(chunk_count=42)

    assert result["status"] == "embeddings_updated"
    assert result["chunks_embedded"] == 42
    assert result["vector_search_available"] is True
