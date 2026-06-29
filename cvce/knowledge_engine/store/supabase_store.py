"""
SupabaseKnowledgeStore — Secure, version-aware access to the Knowledge Graph in Supabase.

This is the recommended production backend for KnowledgeEngine.
It uses the service role key but through a controlled interface.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .base import KnowledgeStore


def _sync_helpers():
    """Load Supabase REST helpers from scripts/supabase_corpus_sync.py."""
    root = Path(__file__).resolve().parents[3]
    scripts = root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from supabase_corpus_sync import api_request, load_env

    return load_env, api_request


class SupabaseKnowledgeStore(KnowledgeStore):
    """
    Knowledge graph backed by Supabase (graph_nodes + graph_links tables).

    Security model:
    - Uses service role key (from env)
    - All queries go through this class (no raw Supabase calls elsewhere)
    - Can be extended with row-level policies or dedicated KE credentials later
    """

    def __init__(self, graph_version: str = "newbooks-v1"):
        self.graph_version = graph_version
        self._env = self._load_env()
        self._embeddings_present: bool | None = None

    def _load_env(self) -> dict[str, str]:
        load_env, _ = _sync_helpers()
        return load_env()

    def _request(self, method: str, path: str, body: bytes | None = None) -> tuple[int, bytes]:
        _, api_request = _sync_helpers()
        return api_request(self._env, method, path, body)

    # ------------------------------------------------------------------ #
    # KnowledgeStore Interface
    # ------------------------------------------------------------------ #

    def get_version(self) -> str:
        return self.graph_version

    def get_stats(self) -> dict[str, Any]:
        code, body = self._request(
            "GET",
            f"/rest/v1/graph_nodes?select=count&graph_version=eq.{self.graph_version}&limit=1",
        )
        node_count = 0
        if code == 200:
            try:
                data = json.loads(body)
                node_count = data[0].get("count", 0) if data else 0
            except Exception:
                pass

        return {
            "version": self.graph_version,
            "node_count": node_count,
            "source": "supabase",
        }

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        code, body = self._request(
            "GET",
            f"/rest/v1/graph_nodes?id=eq.{node_id}&graph_version=eq.{self.graph_version}&limit=1",
        )
        if code == 200:
            data = json.loads(body)
            if data:
                return data[0]
        return None

    def get_nodes(self, limit: int = 100) -> list[dict[str, Any]]:
        code, body = self._request(
            "GET", f"/rest/v1/graph_nodes?graph_version=eq.{self.graph_version}&limit={limit}"
        )
        if code == 200:
            return json.loads(body)
        return []

    def get_links(self, source_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = f"/rest/v1/graph_links?graph_version=eq.{self.graph_version}&limit={limit}"
        if source_id:
            query += f"&source_id=eq.{source_id}"
        code, body = self._request("GET", query)
        if code == 200:
            return json.loads(body)
        return []

    def health_check(self) -> bool:
        code, _ = self._request("GET", "/rest/v1/graph_nodes?select=id&limit=1")
        return code == 200

    def has_embeddings(self) -> bool:
        """Return True when at least one corpus chunk has an embedding."""
        if self._embeddings_present is not None:
            return self._embeddings_present
        code, body = self._request(
            "GET",
            "/rest/v1/corpus_chunks?select=id&embedding=not.is.null&limit=1",
        )
        present = False
        if code == 200:
            try:
                present = len(json.loads(body)) > 0
            except Exception:
                present = False
        self._embeddings_present = present
        return present

    def _embed_query(self, query: str) -> list[float] | None:
        from knowledge_engine.embeddings import embed_text, get_genai_client

        client = get_genai_client()
        if not client:
            return None
        return embed_text(client, query)

    def _vector_search(self, embedding: list[float], top_k: int) -> list[dict]:
        payload = {"query_embedding": embedding, "match_count": top_k}
        code, body = self._request(
            "POST",
            "/rest/v1/rpc/match_corpus_chunks",
            json.dumps(payload).encode(),
        )
        if code == 200:
            try:
                return json.loads(body)
            except Exception:
                return []
        return []

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        safe = quote(query.replace("*", ""), safe="")
        code, body = self._request(
            "GET",
            f"/rest/v1/corpus_chunks?select=source_id,content,chunk_index"
            f"&content=ilike.*{safe}*&limit={top_k}",
        )
        if code == 200:
            try:
                return json.loads(body)
            except Exception:
                return []
        return []

    def search(self, query: str, top_k: int = 8) -> list[dict]:
        """
        Vector search when embeddings exist; keyword ilike fallback otherwise.
        """
        query = (query or "").strip()
        if not query:
            return []

        if self.has_embeddings():
            vec = self._embed_query(query)
            if vec:
                results = self._vector_search(vec, top_k)
                if results:
                    return results

        return self._keyword_search(query, top_k)

    def mark_embeddings_updated(self) -> None:
        """Clear cached embedding availability (call after embedding generation)."""
        self._embeddings_present = None
