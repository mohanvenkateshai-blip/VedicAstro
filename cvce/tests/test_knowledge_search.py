"""Tests for KnowledgeEngine vector / hybrid search."""

import json
import os

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


def test_search_hybrid_merges_vector_and_keyword(monkeypatch):
    from knowledge_engine.store.supabase_store import SupabaseKnowledgeStore

    store = SupabaseKnowledgeStore.__new__(SupabaseKnowledgeStore)
    store.graph_version = "test-v1"
    store._env = {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "key"}
    store._embeddings_present = True

    vector_hit = [
        {
            "id": "vec-1",
            "source_id": "muhurta.md",
            "chunk_index": 0,
            "content": "vector muhurta passage",
            "similarity": 0.95,
        }
    ]
    keyword_hit = [
        {
            "id": "kw-1",
            "source_id": "notes.md",
            "chunk_index": 1,
            "content": "keyword-only muhurta note",
        }
    ]

    def fake_request(method, path, body=None):
        if method == "POST" and "/rpc/match_corpus_chunks" in path:
            return 200, json.dumps(vector_hit).encode()
        if method == "GET" and "content=ilike" in path:
            return 200, json.dumps(keyword_hit).encode()
        if method == "GET" and "embedding=not.is.null" in path:
            return 200, json.dumps([{"id": "x"}]).encode()
        return 404, b"[]"

    monkeypatch.setattr(store, "_embed_query", lambda q: [0.1] * 768)
    monkeypatch.setattr(store, "_request", fake_request)

    results = store.search("muhurta", top_k=8)
    assert len(results) == 2
    assert results[0]["similarity"] == 0.95
    assert results[1].get("similarity") == 0.0


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


def test_search_knowledge_integration_wrapper(monkeypatch):
    from knowledge_engine.integration import clear_knowledge_engine_cache, search_knowledge

    clear_knowledge_engine_cache()

    from knowledge_engine.engine import KnowledgeEngine
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

    clear_knowledge_engine_cache()
    ke = KnowledgeEngine(store=store)
    monkeypatch.setattr(
        "knowledge_engine.integration.get_knowledge_engine",
        lambda: ke,
    )

    results = search_knowledge("muhurta")
    assert len(results) == 1
    clear_knowledge_engine_cache()


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


# ------------------------------------------------------------------
# Live (non-mocked) verification — runs only when explicitly enabled.
# Use after embeddings land: REAL_KE_SEARCH=1 pytest cvce/tests/test_knowledge_search.py::test_real_ke_search_when_live -s
# ------------------------------------------------------------------

def _real_ke_available() -> bool:
    return bool(os.environ.get("REAL_KE_SEARCH") or os.environ.get("KE_REAL_EMBEDDINGS"))


@pytest.mark.skipif(not _real_ke_available(), reason="set REAL_KE_SEARCH=1 (or KE_REAL_EMBEDDINGS) to run against live store")
def test_real_ke_search_when_live():
    """When embeddings live: vector flag true + real search hits carry source_id + similarity (vector path)."""
    from knowledge_engine.integration import get_knowledge_engine, search_knowledge

    ke = get_knowledge_engine()
    assert ke.vector_search_available() is True, "vector_search_available must be True once corpus_chunks embeddings exist"

    for q in ("dasha", "muhurta", "yoga"):
        hits = search_knowledge(q, top_k=3) or ke.search(q, top_k=3) or []
        assert hits, f"expected hits for {q}"
        for h in hits[:2]:
            assert "source_id" in h and h["source_id"], f"hit for {q} missing source_id"
            # similarity present when vector contributed (may be 0.0 for pure keyword merge)
            assert "similarity" in h, f"hit for {q} missing similarity key"
