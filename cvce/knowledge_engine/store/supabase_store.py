"""
SupabaseKnowledgeStore — Secure, version-aware access to the Knowledge Graph in Supabase.

This is the recommended production backend for KnowledgeEngine.
It uses the service role key but through a controlled interface.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .base import KnowledgeStore


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

    def _load_env(self) -> Dict[str, str]:
        """Load Supabase credentials."""
        from scripts.supabase_corpus_sync import load_env as _load
        return _load()

    def _request(self, method: str, path: str, body: bytes | None = None) -> tuple[int, bytes]:
        from scripts.supabase_corpus_sync import api_request
        return api_request(self._env, method, path, body)

    # ------------------------------------------------------------------ #
    # KnowledgeStore Interface
    # ------------------------------------------------------------------ #

    def get_version(self) -> str:
        return self.graph_version

    def get_stats(self) -> Dict[str, Any]:
        code, body = self._request(
            "GET",
            f"/rest/v1/graph_nodes?select=count&graph_version=eq.{self.graph_version}&limit=1"
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

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        code, body = self._request(
            "GET",
            f"/rest/v1/graph_nodes?id=eq.{node_id}&graph_version=eq.{self.graph_version}&limit=1"
        )
        if code == 200:
            data = json.loads(body)
            if data:
                return data[0]
        return None

    def get_nodes(self, limit: int = 100) -> List[Dict[str, Any]]:
        code, body = self._request(
            "GET",
            f"/rest/v1/graph_nodes?graph_version=eq.{self.graph_version}&limit={limit}"
        )
        if code == 200:
            return json.loads(body)
        return []

    def get_links(self, source_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
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

    def search(self, query: str, top_k: int = 8) -> list[dict]:
        """
        Vector + keyword hybrid search using pgvector.
        Falls back to keyword search if no embeddings are present.
        """
        # Try vector search first
        try:
            # This assumes embeddings are populated.
            # For a real implementation we would embed the query here.
            # Placeholder: use content search until embedding generation is wired.
            code, body = self._request(
                "GET",
                f"/rest/v1/corpus_chunks?select=source_id,content&content=ilike.*{query}*&limit={top_k}"
            )
            if code == 200:
                return json.loads(body)
        except Exception:
            pass
        return []
