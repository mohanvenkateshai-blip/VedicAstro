"""
KnowledgeEngine — The central manager for the Knowledge Graph and its consumers.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import GraphVersion, InvalidationReason, KnowledgeValidity
from .registry import EngineRegistry, RegisteredEngine
from .store.base import KnowledgeStore
from .store.supabase_store import SupabaseKnowledgeStore

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CVCE_ROOT = Path(__file__).resolve().parents[1]


def default_graph_path() -> Path:
    """Resolve graph.json for local dev and tests (cwd-independent)."""
    candidates = [
        _CVCE_ROOT / "graph_rag" / "graph.json",
        _REPO_ROOT / "knowledge-graph" / "graphify-out" / "graph.json",
        Path("knowledge-graph/graphify-out/graph.json"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


# Fallback file-based store (current behavior)
class _FileKnowledgeStore(KnowledgeStore):
    def __init__(self, graph_path: Path | None = None):
        self.graph_path = graph_path or default_graph_path()
        self._graph = None

    def _load(self):
        if self._graph is None:
            self._graph = json.loads(self.graph_path.read_text(encoding="utf-8"))
        return self._graph

    def get_version(self) -> str:
        return os.environ.get("CORPUS_GRAPH_VERSION", "file-based")

    def get_stats(self) -> dict[str, Any]:
        g = self._load()
        return {"node_count": len(g.get("nodes", [])), "link_count": len(g.get("links", []))}

    def get_node(self, node_id: str):
        g = self._load()
        return next((n for n in g.get("nodes", []) if n.get("id") == node_id), None)

    def get_nodes(self, limit: int = 100):
        g = self._load()
        return g.get("nodes", [])[:limit]

    def get_links(self, source_id=None, limit=100):
        g = self._load()
        links = g.get("links", [])
        if source_id:
            links = [l for l in links if l.get("source") == source_id]
        return links[:limit]

    def health_check(self) -> bool:
        return self.graph_path.exists()


@dataclass
class KnowledgeEngine:
    """
    Single point of control for the Vedic Knowledge Graph.

    Goals:
    1. When new texts are added → cascade updates to registered engines.
    2. Block stale/wrong/confusing knowledge from being consumed.
    3. Support periodic revival (engines can request fresh context).
    """

    store: KnowledgeStore = field(default_factory=_FileKnowledgeStore)
    registry: EngineRegistry = field(default_factory=EngineRegistry)
    current_version: GraphVersion | None = None
    _invalidations: dict[str, KnowledgeValidity] = field(default_factory=dict)
    _last_revived_at: datetime | None = None
    _revive_interval_seconds: int = 3600

    def __post_init__(self):
        self._load_current_version()
        self._attach_graph_compat()

    def _load_current_version(self) -> GraphVersion:
        """Load the active graph version."""
        stats = self.store.get_stats()
        version_str = os.environ.get("CORPUS_GRAPH_VERSION", self.store.get_version())
        self.current_version = GraphVersion(
            version=version_str,
            node_count=stats.get("node_count", 0),
            link_count=stats.get("link_count", 0),
            loaded_at=datetime.now(UTC),
        )
        return self.current_version

    def _attach_graph_compat(self):
        """Provide self.graph for legacy accessors (query_nodes, get_safe_node, on_new...).
        Prefers the real GraphRAG singleton (so cache clears in on_refresh also affect it);
        falls back to a thin store-backed shim.
        """
        if getattr(self, "graph", None) is not None:
            return
        try:
            from graph_rag.graph import GraphRAG

            self.graph = GraphRAG()
            return
        except Exception as exc:
            logger.debug("GraphRAG compat attach failed, using store shim: %s", exc)

        # Fallback shim backed by the store (supports .nodes, .node(), .stats, _load)
        class _StoreGraphShim:
            def __init__(self, store):
                self._store = store
                self.nodes = []
                self.links = []
                self._nodes_by_id = {}
                self._loaded = False
                try:
                    self.stats = store.get_stats() or {}
                except Exception:
                    self.stats = {}

            def _load(self):
                if self._loaded:
                    return
                try:
                    self.nodes = self._store.get_nodes(limit=100000) or []
                    self.links = self._store.get_links(limit=100000) or []
                    self._nodes_by_id = {
                        n.get("id"): n for n in self.nodes if isinstance(n, dict) and n.get("id")
                    }
                except Exception:
                    pass
                self._loaded = True

            def node(self, node_id: str):
                self._load()
                return self._nodes_by_id.get(node_id)

        self.graph = _StoreGraphShim(self.store)

    # ------------------------------------------------------------------ #
    # Public API for engines
    # ------------------------------------------------------------------ #

    def register_engine(
        self,
        name: str,
        on_refresh: Callable[[str], None] | None = None,
        on_invalidation: Callable[[list[str], InvalidationReason, str], None] | None = None,
    ) -> RegisteredEngine:
        """Register an engine that depends on knowledge (e.g. 'gochar', 'report', 'muhurta')."""
        return self.registry.register(
            name,
            on_refresh=on_refresh,
            on_invalidation=on_invalidation,
        )

    def get_safe_knowledge(self, engine_name: str) -> dict:
        """
        Preferred safe access point for any engine that needs current validated knowledge.

        Raises RuntimeError when the graph is globally unhealthy. Returned payload
        excludes invalidated nodes from direct use — consumers should call
        ``get_safe_node`` / ``filter_valid_nodes`` for node-level access.
        """
        if not self.is_knowledge_healthy():
            raise RuntimeError(f"Knowledge is currently unhealthy. Engine '{engine_name}' blocked.")

        g = getattr(self, "graph", None)
        stats = getattr(g, "stats", None) or {}
        if not stats and g is not None:
            try:
                nc = len(getattr(g, "nodes", []) or [])
                lc = len(getattr(g, "links", []) or [])
                stats = {"node_count": nc, "link_count": lc, "nodes": nc, "links": lc}
            except Exception:
                stats = {}
        return {
            "version": self.current_version.version if self.current_version else "unknown",
            "stats": stats,
            "invalidated_nodes": self.invalidated_node_ids(),
            "invalidation_count": len(self._invalidations),
            "last_revived": self._last_revived_at.isoformat() if self._last_revived_at else None,
        }

    def get_graph(self):
        """Returns the underlying store (for advanced use)."""
        if not self.is_knowledge_healthy():
            raise RuntimeError("Knowledge is currently unhealthy.")
        return self.store

    @classmethod
    def with_supabase(cls, graph_version: str = "newbooks-v1") -> KnowledgeEngine:
        """Convenience constructor for Supabase-backed mode."""
        store = SupabaseKnowledgeStore(graph_version=graph_version)
        return cls(store=store)

    def get_safe_node(self, node_id: str) -> dict | None:
        """
        Return a graph node only when it is currently valid.

        Invalidated or unknown nodes return ``None`` without raising.
        """
        if not self.is_node_valid(node_id):
            return None
        return self.graph.node(node_id)

    def filter_valid_nodes(self, nodes: list[dict]) -> list[dict]:
        """Return only nodes whose ``id`` is not invalidated."""
        return [node for node in nodes if self.is_node_valid(node.get("id", ""))]

    def query_nodes(self, pattern: str | None = None, limit: int | None = None) -> list[dict]:
        """
        Safe graph query that omits invalidated nodes.

        When ``pattern`` is given, only node IDs matching the glob pattern are
        considered (e.g. ``"muhurta_*"``).
        """
        if not self.is_knowledge_healthy():
            raise RuntimeError("Knowledge is currently unhealthy — node query blocked.")

        candidates = self.graph.nodes
        if pattern:
            candidates = [
                node for node in candidates if fnmatch.fnmatch(node.get("id", ""), pattern)
            ]

        valid = self.filter_valid_nodes(candidates)
        if limit is not None:
            return valid[:limit]
        return valid

    def get_structured_book(self, book_id: str) -> dict | None:
        """Return the clean, hierarchical chapter/subtitle/content structure for a source book.

        This is generated from the original Gyan markdown (scripts/build_structured_library.py)
        and is the authoritative organised view (chapters, titles, subtitles, sections).
        Used to drive the Learn reader and to map graph nodes back to precise locations.

        Enhanced: also attaches KE node linkage per chapter when the node→chapter
        patch map (produced by scripts/map_nodes_to_structured.py) is present.
        Returns keys:
          - chapters: the tree
          - chapter_node_ids: {chapter_id: [node_id, ...]}
          - nodes_by_chapter: {chapter_id: [full_node, ...]} (best-effort lookup)
        """
        try:
            from pathlib import Path
            import json

            base = _REPO_ROOT / "knowledge-graph" / "structured"
            data: dict | None = None
            candidates = [
                base / f"{book_id}.json",
                base / f"{book_id.replace(' ', '_')}.json",
            ]
            for p in candidates:
                if p.exists():
                    data = json.loads(p.read_text(encoding="utf-8"))
                    break
            if data is None and base.exists():
                for p in base.glob("*.json"):
                    try:
                        d = json.loads(p.read_text(encoding="utf-8"))
                        if book_id in (d.get("book_id") or "") or book_id in (d.get("canonical_name") or ""):
                            data = d
                            break
                    except Exception:
                        pass
            if not data:
                return None

            # Enrich with node linkage from the authoritative patch map (KE-owned)
            book_key = data.get("book_id") or book_id
            patches = self._get_patch_entries_for_book(book_key)

            chapter_node_ids: dict[str, list[str]] = {}
            for p in patches:
                ch = p.get("chapter_id")
                nid = p.get("node_id")
                if ch and nid:
                    chapter_node_ids.setdefault(ch, []).append(nid)

            # Best-effort materialise node payloads for consumers (Learn/CVCE)
            nodes_by_chapter: dict[str, list[dict]] = {}
            for ch, nids in chapter_node_ids.items():
                bucket: list[dict] = []
                for nid in nids:
                    n = None
                    try:
                        n = self.store.get_node(nid)
                    except Exception:
                        pass
                    if not n:
                        try:
                            getter = getattr(self.graph, "node", None)
                            if callable(getter):
                                n = getter(nid)
                        except Exception:
                            pass
                    if n:
                        bucket.append(n)
                if bucket:
                    nodes_by_chapter[ch] = bucket

            out = dict(data)
            out["chapter_node_ids"] = chapter_node_ids
            out["nodes_by_chapter"] = nodes_by_chapter
            return out
        except Exception as e:
            logger.debug("get_structured_book failed for %s: %s", book_id, e)
        return None

    # ------------------------------------------------------------------ #
    # Structured library + node/chapter mapping (owned by KE)
    # ------------------------------------------------------------------ #

    _node_chapter_patch: dict | None = None

    def _load_node_chapter_patch(self) -> dict:
        """Load (and cache) the node→(chapter, section, hierarchy) mapping patch.

        Enhanced: also incorporates any per-book patch-*.json files (preferred by
        the portal and produced by map_nodes_to_structured.py per book). This makes
        get_structured_book / get_nodes_for_chapter see the latest per-book provenance.
        """
        if self._node_chapter_patch is not None:
            return self._node_chapter_patch
        merged: dict = {"patches": [], "books": []}
        # 1. consolidated
        p = Path("knowledge-graph/patches/node-chapter-map.json")
        if p.exists():
            try:
                base = json.loads(p.read_text(encoding="utf-8"))
                merged["patches"].extend(base.get("patches") or [])
                merged["books"] = base.get("books") or []
            except Exception:
                pass
        # 2. per-book patches (patch-{name}.json) — prefer/merge like portal loadNodeChapterPatch
        patches_dir = Path("knowledge-graph/patches")
        if patches_dir.exists():
            try:
                for pf in sorted(patches_dir.glob("patch-*.json")):
                    try:
                        extra = json.loads(pf.read_text(encoding="utf-8"))
                        extras = extra.get("patches") or (extra if isinstance(extra, list) else [])
                        for e in extras:
                            # tag book if missing
                            if not e.get("book_id") and extra.get("book_id"):
                                e = dict(e)
                                e["book_id"] = extra.get("book_id")
                            merged["patches"].append(e)
                        bks = extra.get("books") or ([extra.get("book_id")] if extra.get("book_id") else [])
                        for b in bks:
                            if b and b not in merged.get("books", []):
                                merged.setdefault("books", []).append(b)
                    except Exception:
                        continue
            except Exception:
                pass
        if not merged.get("patches"):
            merged = {"patches": []}
        self._node_chapter_patch = merged
        return self._node_chapter_patch

    def _get_patch_entries_for_book(self, book_id: str) -> list[dict]:
        patch = self._load_node_chapter_patch()
        patches: list[dict] = patch.get("patches") or []
        key = (book_id or "").strip()
        k_norm = key.lower().replace(" ", "_")
        out: list[dict] = []
        for p in patches:
            bid = (p.get("book_id") or "")
            b_norm = bid.lower().replace(" ", "_")
            if bid == key or key in bid or bid.replace(" ", "_") == key.replace(" ", "_"):
                out.append(p)
            elif k_norm and (k_norm in b_norm or b_norm in k_norm or k_norm == b_norm):
                out.append(p)
        # de-dup by node_id
        seen = set()
        uniq = []
        for p in out:
            nid = p.get("node_id")
            if nid and nid not in seen:
                seen.add(nid)
                uniq.append(p)
        return uniq

    def get_nodes_for_chapter(self, book_id: str, chapter_id: str) -> list[dict]:
        """Return the KnowledgeEngine graph nodes that map to a given chapter of a book."""
        entries = [p for p in self._get_patch_entries_for_book(book_id) if p.get("chapter_id") == chapter_id]
        nids = [p["node_id"] for p in entries if p.get("node_id")]
        out: list[dict] = []
        seen: set[str] = set()
        for nid in nids:
            if nid in seen:
                continue
            seen.add(nid)
            n = None
            try:
                n = self.store.get_node(nid)
            except Exception:
                pass
            if not n:
                try:
                    getter = getattr(self.graph, "node", None)
                    if callable(getter):
                        n = getter(nid)
                except Exception:
                    pass
            if n:
                out.append(n)
        return out

    def get_hierarchy_for_node(self, node_id: str) -> dict | None:
        """Reverse lookup: given a KE node id, return its chapter/section/hierarchy in the source book."""
        patch = self._load_node_chapter_patch()
        for p in patch.get("patches") or []:
            if p.get("node_id") == node_id:
                return {
                    "node_id": node_id,
                    "book_id": p.get("book_id"),
                    "chapter_id": p.get("chapter_id"),
                    "section_id": p.get("section_id"),
                    "hierarchy_path": p.get("hierarchy_path"),
                    "method": p.get("method"),
                    "confidence": p.get("confidence"),
                }
        return None

    def rebuild_structured_library(self, books: list[str] | None = None) -> dict:
        """Rebuild the clean chapter/subtitle structured JSONs from raw sources.

        This is the 'organise from the beginning' step. Safe to call from
        on_new_literature_ingested or manually.
        """
        import subprocess
        import sys

        structured_dir = Path("knowledge-graph/structured")
        structured_dir.mkdir(parents=True, exist_ok=True)

        if not books:
            cmd = [sys.executable, "scripts/build_structured_library.py", "--all"]
        else:
            cmd = [sys.executable, "scripts/build_structured_library.py", "--books", ",".join(books)]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
            ok = res.returncode == 0
            return {
                "status": "ok" if ok else "error",
                "returncode": res.returncode,
                "stdout_tail": (res.stdout or "")[-2000:],
                "stderr_tail": (res.stderr or "")[-2000:],
            }
        except Exception as e:
            logger.warning("rebuild_structured_library failed: %s", e)
            return {"status": "failed", "error": str(e)}

    def remap_nodes_to_structured(self, books: list[str] | None = None) -> dict:
        """Re-run node-to-chapter mapping and refresh the patch consumed by get_* methods.

        After this, get_structured_book, get_nodes_for_chapter and get_hierarchy_for_node
        will see fresh linkages.
        """
        import subprocess
        import sys

        patch_dir = Path("knowledge-graph/patches")
        patch_dir.mkdir(parents=True, exist_ok=True)
        out_path = patch_dir / "node-chapter-map.json"

        if not books:
            # discover from whatever structured books exist
            books = [p.stem for p in Path("knowledge-graph/structured").glob("*.json")]

        if not books:
            return {"status": "skipped", "reason": "no structured books found"}

        cmd = [
            sys.executable,
            "scripts/map_nodes_to_structured.py",
            "--books",
            ",".join(books),
            "--out",
            str(out_path),
        ]
        if os.environ.get("SUPABASE_URL"):
            cmd.append("--supabase")

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
            # Bust cache so next reads see the new patch
            self._node_chapter_patch = None
            ok = res.returncode == 0
            return {
                "status": "ok" if ok else "error",
                "returncode": res.returncode,
                "books": books,
                "out": str(out_path),
                "stdout_tail": (res.stdout or "")[-2000:],
                "stderr_tail": (res.stderr or "")[-2000:],
            }
        except Exception as e:
            logger.warning("remap_nodes_to_structured failed: %s", e)
            return {"status": "failed", "error": str(e)}

    def rebuild_and_remap_structured(self, books: list[str] | None = None) -> dict:
        """Convenience: structured chapters then node mapping (the full 'KE owns organised data' step)."""
        r1 = self.rebuild_structured_library(books=books)
        r2 = self.remap_nodes_to_structured(books=books)
        return {"structured": r1, "mapping": r2}

    def get_safe_rules(self, category: str = "transit"):
        """Safe access to specific rule sets (transit, muhurta, etc.)."""
        if not self.is_knowledge_healthy():
            raise RuntimeError(f"Knowledge unhealthy — {category} rules blocked.")

        # Delegate to store if it supports rule methods (Supabase store will in future)
        if hasattr(self.store, "get_safe_rules"):
            return self.store.get_safe_rules(category)

        # Fallback to current providers (temporary until store implements rules)
        if category == "transit":
            from graph_rag.rules_provider import active_transit_rules

            return active_transit_rules()
        elif category == "muhurta":
            from graph_rag.muhurta_rules_provider import active_muhurta_rules

            return active_muhurta_rules()
        else:
            raise ValueError(f"Unknown rule category: {category}")

    # ------------------------------------------------------------------ #
    # Vector / Hybrid Search (P0 item under KnowledgeEngine)
    # ------------------------------------------------------------------ #

    def vector_search_available(self) -> bool:
        """Check if embeddings exist in Supabase corpus_chunks."""
        if hasattr(self.store, "has_embeddings"):
            try:
                return self.store.has_embeddings()
            except Exception:
                return False
        return False

    def on_embeddings_updated(self, chunk_count: int = 0) -> dict:
        """
        Called after corpus chunk embeddings are populated or refreshed.

        Clears store caches and notifies registered engines so they can use
        vector retrieval on the next refresh cycle.
        """
        if hasattr(self.store, "mark_embeddings_updated"):
            self.store.mark_embeddings_updated()

        self._load_current_version()
        version = self.current_version.version if self.current_version else "unknown"
        self.registry.notify_refresh(new_version=version)
        self._last_revived_at = datetime.now(UTC)

        return {
            "status": "embeddings_updated",
            "chunks_embedded": chunk_count,
            "vector_search_available": self.vector_search_available(),
            "version": version,
        }

    # ------------------------------------------------------------------ #
    # LLM Narration (KnowledgeEngine-owned)
    # ------------------------------------------------------------------ #

    # Narration sources — virtual node IDs for per-domain LLM blocking
    NARRATION_SOURCE_KEYS = (
        "dasha_intelligence",
        "transit_intelligence",
        "timing_merge",
        "yogas",
        "ashtakavarga",
    )

    def narration_source_id(self, source_key: str) -> str:
        """Return the invalidation node ID for an LLM narration source."""
        return f"narration_source:{source_key}"

    def is_narration_source_valid(self, source_key: str) -> bool:
        """Return True when narration for this fact domain is not blocked."""
        return self.is_node_valid(self.narration_source_id(source_key))

    def get_llm_narration(self, facts: dict, birth: dict) -> dict | None:
        """
        Optional Gemini prose layer for report facts.

        Gated by ``CVCE_LLM_NARRATION=1`` and overall knowledge health.
        Respects per-source invalidation via ``narration_source:*`` node IDs.
        Returns ``None`` when the feature flag is off; otherwise a status dict.
        """
        if os.environ.get("CVCE_LLM_NARRATION") != "1":
            return None

        if not self.is_knowledge_healthy():
            return {
                "status": "blocked",
                "reason": "knowledge unhealthy",
            }

        allowed, blocked = self._resolve_narration_sources(facts)
        if not allowed:
            return {
                "status": "blocked",
                "reason": "all narration sources blocked",
                "sources_blocked": blocked,
            }

        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            return {"status": "skipped", "reason": "no Gemini key"}

        from google import genai

        client = genai.Client(api_key=key)

        prompt_payload = {k: facts[k] for k in allowed if k in facts}
        prompt = f"""You are a concise Vedic astrologer. Given the structured facts below for {birth}, write 3-5 short natural paragraphs (no tables) that a client can read directly. Cover: overall tone of the period, key strengths, cautions, and one actionable recommendation. Stay factual to the data. Use plain modern English.

Facts (abbrev):
{json.dumps(prompt_payload, indent=2)[:3000]}
"""

        resp = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        text = (resp.text or "").strip()
        return {
            "prose": text,
            "model": "gemini-1.5-flash",
            "generated": True,
            "sources_used": allowed,
            "sources_blocked": blocked,
        }

    def _resolve_narration_sources(self, facts: dict) -> tuple[list[str], list[str]]:
        """Split narration source keys into allowed vs invalidated (with data present)."""
        allowed: list[str] = []
        blocked: list[str] = []
        for key in self.NARRATION_SOURCE_KEYS:
            if key not in facts or facts[key] is None:
                continue
            if self.is_narration_source_valid(key):
                allowed.append(key)
            else:
                blocked.append(key)
        return allowed, blocked

    def search(self, query: str, top_k: int = 8) -> list[dict]:
        """
        Semantic + keyword hybrid search over corpus chunks (Supabase pgvector).

        Returns ranked chunk dicts with ``source_id``, ``content``, ``chunk_index``,
        and ``similarity`` when vector search contributed.
        """
        query = (query or "").strip()
        if not query:
            return []

        if not hasattr(self.store, "search"):
            logger.debug("store has no search() — returning empty for %r", query[:80])
            return []

        try:
            results = self.store.search(query, top_k)
            logger.info(
                "knowledge search %r → %d hits (vector_available=%s)",
                query[:80],
                len(results),
                self.vector_search_available(),
            )
            return results
        except Exception:
            logger.exception("knowledge search failed for %r", query[:80])
            return []

    # ------------------------------------------------------------------ #
    # Validity & Blocking (Invalidation Protocol)
    # ------------------------------------------------------------------ #

    def invalidate(
        self,
        node_ids: list[str] | None = None,
        pattern: str | None = None,
        reason: InvalidationReason = InvalidationReason.MANUAL,
        details: str = "",
    ) -> list[str]:
        """
        Block specific knowledge from being consumed by any engine.

        Targets may be supplied as explicit ``node_ids``, a glob ``pattern``
        (matched against all graph node IDs), or both. Returns the list of
        node IDs that were newly or re-invalidated.
        """
        targets = self._resolve_invalidation_targets(node_ids=node_ids, pattern=pattern)
        if not targets:
            return []

        now = datetime.now(UTC)
        for node_id in targets:
            self._invalidations[node_id] = KnowledgeValidity(
                node_id=node_id,
                is_valid=False,
                reason=reason,
                details=details,
                invalidated_at=now,
            )

        self.registry.notify_invalidation(targets, reason, details)
        return targets

    def revalidate(
        self,
        node_ids: list[str] | None = None,
        pattern: str | None = None,
    ) -> list[str]:
        """
        Remove invalidations for the given IDs or glob pattern.

        Returns the node IDs that were restored to valid status.
        """
        if node_ids is None and pattern is None:
            cleared = list(self._invalidations.keys())
            self._invalidations.clear()
            return cleared

        targets = self._resolve_invalidation_targets(
            node_ids=node_ids,
            pattern=pattern,
            known_only=True,
        )
        for node_id in targets:
            self._invalidations.pop(node_id, None)
        return targets

    def get_validity(self, node_id: str) -> KnowledgeValidity:
        """Return the validity record for a node (valid by default)."""
        if node_id in self._invalidations:
            return self._invalidations[node_id]
        return KnowledgeValidity(node_id=node_id, is_valid=True)

    def is_node_valid(self, node_id: str) -> bool:
        """Return True when the node is not in the invalidation set."""
        return node_id not in self._invalidations

    def invalidated_node_ids(self) -> list[str]:
        """Return all currently invalidated node IDs."""
        return list(self._invalidations.keys())

    def is_knowledge_healthy(self) -> bool:
        """High-level health for the whole system."""
        if self.current_version is None:
            return False
        return len(self._invalidations) < 50

    def _resolve_invalidation_targets(
        self,
        node_ids: list[str] | None = None,
        pattern: str | None = None,
        known_only: bool = False,
    ) -> list[str]:
        """Resolve explicit IDs and/or glob patterns into a deduplicated ID list."""
        targets: set[str] = set()

        if node_ids:
            targets.update(node_ids)

        if pattern:
            graph_ids = {node.get("id", "") for node in getattr(self.graph, "nodes", [])}
            if known_only:
                source_ids = set(self._invalidations.keys())
            else:
                source_ids = graph_ids
            targets.update(nid for nid in source_ids if nid and fnmatch.fnmatch(nid, pattern))

        return sorted(targets)

    def _clear_stale_invalidations(self) -> list[str]:
        """
        Drop invalidations for nodes that no longer exist in the loaded graph.

        Returns the stale node IDs that were removed.
        """
        graph_ids = {node.get("id", "") for node in getattr(self.graph, "nodes", [])}
        stale = [node_id for node_id in self._invalidations if node_id not in graph_ids]
        for node_id in stale:
            del self._invalidations[node_id]
        return stale

    # ------------------------------------------------------------------ #
    # Cascading updates (when new literature is added)
    # ------------------------------------------------------------------ #

    def on_new_literature_ingested(self, new_graph_path: Path, new_version: str):
        """
        Called after ingestion pipeline finishes.

        This is the cascade point:
        - Force reload of GraphRAG with the new file
        - Update version metadata
        - Clear old invalidations
        - Notify all registered engines to refresh
        - (optional) Rebuild structured chapter trees + re-map KE nodes to chapters
          when KE_REBUILD_STRUCTURED_ON_INGEST or KE_AUTO_REBUILD_STRUCTURED is set.
        """
        if hasattr(self.graph, "_loaded"):
            self.graph._loaded = False
            self.graph._GRAPH_PATH = str(new_graph_path)  # type: ignore[attr-defined]

        self.graph._load()

        stats = getattr(self.graph, "stats", {})
        self.current_version = GraphVersion(
            version=new_version,
            node_count=stats.get("nodes", 0),
            link_count=stats.get("links", 0),
            loaded_at=datetime.now(UTC),
            source=str(new_graph_path),
        )

        self._invalidations.clear()
        self.registry.notify_refresh(new_version=new_version)
        self._last_revived_at = datetime.now(UTC)

        # === Structured data ownership: re-trigger organised chapter + mapping rebuild ===
        # This ensures the Learn portal / CVCE get the clean chapter tree + linked KE nodes
        # for any newly promoted literature.
        auto_rebuild = bool(
            os.environ.get("KE_REBUILD_STRUCTURED_ON_INGEST")
            or os.environ.get("KE_AUTO_REBUILD_STRUCTURED")
        )
        if auto_rebuild:
            try:
                # We don't know the exact new book stems here; rebuild everything that has raw sources.
                # The scripts are idempotent and the patch is the source of truth for linkages.
                rb = self.rebuild_and_remap_structured()
                logger.info("Structured library + node remap triggered by on_new_literature_ingested: %s", rb.get("structured", {}).get("status"))
            except Exception as e:
                logger.warning("Structured rebuild/remap in on_new_literature_ingested skipped: %s", e)

    # ------------------------------------------------------------------ #
    # Periodic Revival (Revival Protocol)
    # ------------------------------------------------------------------ #

    def revive(self, force: bool = False) -> bool:
        """
        Refresh knowledge state and push updates to registered engines.

        Intended for periodic background jobs or on-demand calls. When run:

        1. Re-loads version metadata from the current graph and environment.
        2. Clears invalidations for nodes that no longer exist (stale blocks).
        3. Notifies all registered engines via ``on_refresh`` so they can
           rebuild caches and rule views.

        Returns True when a revival cycle completed; False when skipped due
        to the cooldown window (unless ``force=True``).
        """
        if not force and self._last_revived_at:
            age = (datetime.now(UTC) - self._last_revived_at).total_seconds()
            if age < self._revive_interval_seconds:
                return False

        self._load_current_version()
        self._clear_stale_invalidations()

        new_version = self.current_version.version if self.current_version else "unknown"
        self.registry.notify_refresh(new_version=new_version)

        self._last_revived_at = datetime.now(UTC)
        return True

    def trigger_global_refresh(self, reason: str = "manual") -> dict:
        """
        **Force refresh command** — tells every registered engine to
        immediately recalculate all logic, analysis, predictions, and
        interpretations using the current knowledge graph.

        This is the explicit "refresh all" trigger that can be called
        after new literature is added or when knowledge needs to be
        forcefully propagated across the entire system.
        """
        self._load_current_version()
        self._clear_stale_invalidations()

        new_version = self.current_version.version if self.current_version else "unknown"
        self.registry.notify_refresh(new_version=new_version)

        self._last_revived_at = datetime.now(UTC)

        return {
            "status": "triggered",
            "version": new_version,
            "reason": reason,
            "engines_notified": self.registry.registered_names(),
            "timestamp": self._last_revived_at.isoformat(),
        }

    # ------------------------------------------------------------------ #
    # Observability
    # ------------------------------------------------------------------ #

    def health(self) -> dict:
        return {
            "version": self.current_version.version if self.current_version else None,
            "healthy": self.is_knowledge_healthy(),
            "invalidated_count": len(self._invalidations),
            "invalidated_nodes": self.invalidated_node_ids()[:20],
            "registered_engines": self.registry.registered_names(),
            "last_revived": self._last_revived_at.isoformat() if self._last_revived_at else None,
        }
