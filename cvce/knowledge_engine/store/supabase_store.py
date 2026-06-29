"""
SupabaseKnowledgeStore — Secure, version-aware access to the Knowledge Graph in Supabase.

This is the recommended production backend for KnowledgeEngine.
It uses the service role key but through a controlled interface.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .base import KnowledgeStore

logger = logging.getLogger(__name__)


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

    def _chunk_key(self, row: dict) -> str:
        if row.get("id"):
            return str(row["id"])
        return f"{row.get('source_id')}#{row.get('chunk_index')}"

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
            except json.JSONDecodeError as exc:
                logger.warning("vector search: invalid JSON response: %s", exc)
                return []
        logger.warning(
            "vector search RPC failed (HTTP %s): %s",
            code,
            body[:200].decode(errors="replace"),
        )
        return []

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        safe = quote(query.replace("*", ""), safe="")
        code, body = self._request(
            "GET",
            f"/rest/v1/corpus_chunks?select=id,source_id,content,chunk_index"
            f"&content=ilike.*{safe}*&limit={top_k}",
        )
        if code == 200:
            try:
                return json.loads(body)
            except json.JSONDecodeError as exc:
                logger.warning("keyword search: invalid JSON response: %s", exc)
                return []
        logger.warning(
            "keyword search failed (HTTP %s): %s",
            code,
            body[:200].decode(errors="replace"),
        )
        return []

    def _merge_hybrid_results(
        self,
        vector_results: list[dict],
        keyword_results: list[dict],
        top_k: int,
    ) -> list[dict]:
        def _rrf(rank: int, k: int = 60) -> float:
            return 1.0 / (k + rank)

        seen: set[str] = set()
        scored: list[tuple[float, dict]] = []

        for rank, row in enumerate(vector_results, 1):
            key = self._chunk_key(row)
            if key in seen:
                continue
            seen.add(key)
            base = float(row.get("similarity", 0.8) or 0.8)
            scored.append((base + _rrf(rank), row))

        for rank, row in enumerate(keyword_results, 1):
            key = self._chunk_key(row)
            if key in seen:
                continue
            seen.add(key)
            enriched = dict(row)
            enriched.setdefault("similarity", 0.0)
            scored.append((_rrf(rank) * 0.6, enriched))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [row for _, row in scored[:top_k]]

    def search(self, query: str, top_k: int = 8) -> list[dict]:
        """
        Hybrid retrieval: cosine similarity via pgvector when embeddings exist,
        merged with keyword ilike matches for recall.
        """
        query = (query or "").strip()
        if not query:
            return []

        vector_results: list[dict] = []
        k = max(top_k, 8) * 2
        if self.has_embeddings():
            vec = self._embed_query(query)
            if vec:
                vector_results = self._vector_search(vec, k)
            else:
                logger.info("query embedding unavailable — keyword-only for %r", query[:80])

        keyword_results = self._keyword_search(query, k)
        if not vector_results and not keyword_results:
            logger.debug("no corpus matches for query %r", query[:80])
            return []

        return self._merge_hybrid_results(vector_results, keyword_results, top_k)

    def mark_embeddings_updated(self) -> None:
        """Clear cached embedding availability (call after embedding generation)."""
        self._embeddings_present = None
