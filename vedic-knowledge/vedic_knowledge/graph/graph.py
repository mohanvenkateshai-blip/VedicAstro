"""
graph.py — In-memory knowledge graph with search & traversal APIs.

Loads graph.json on first access (singleton). Builds adjacency lists +
inverted indices for O(1) lookups by ID, community, and keywords.

Path resolution order:
  1. GRAPH_JSON_PATH environment variable
  2. GRAPHIFY_GRAPH_PATH environment variable (legacy alias)
  3. Package-local graph.json (symlink or data file)
  4. Common sibling locations (cvce/graph_rag, knowledge-graph/graphify-out)

Graceful degradation: if graph.json is missing, GraphRAG loads empty and
reports loaded=False rather than crashing.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

# Expected graph version — apps set GRAPH_VERSION; package compares on load.
DEFAULT_GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "")


def resolve_graph_path() -> Path | None:
    """Return the first existing graph.json path, or None.

    If GRAPH_JSON_PATH (or GRAPHIFY_GRAPH_PATH) is explicitly set, that path
    is the *only* candidate — a missing file yields None (graceful empty graph)
    rather than silently falling back to a different graph.
    """
    explicit: list[Path] = []
    for env_key in ("GRAPH_JSON_PATH", "GRAPHIFY_GRAPH_PATH"):
        raw = os.environ.get(env_key)
        if raw:
            explicit.append(Path(raw).expanduser())
    if explicit:
        for path in explicit:
            try:
                if path.is_file():
                    return path
            except OSError:
                continue
        return None  # env set but file missing → degrade, don't surprise-fallback

    here = Path(__file__).resolve().parent
    candidates = [
        here / "graph.json",
        here.parents[2] / "cvce" / "graph_rag" / "graph.json",
        here.parents[2] / "knowledge-graph" / "graphify-out" / "graph.json",
        Path("graph_rag/graph.json"),
        Path("knowledge-graph/graphify-out/graph.json"),
    ]
    for path in candidates:
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None


def read_graph_metadata(path: Path | None = None) -> dict:
    """Read lightweight metadata without fully indexing the graph."""
    p = path or resolve_graph_path()
    if p is None:
        return {"path": None, "version": None, "exists": False}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return {"path": str(p), "version": None, "exists": True, "error": str(exc)}
    version = (
        data.get("version")
        or data.get("graph_version")
        or (data.get("metadata") or {}).get("version")
        or data.get("built_at_commit")
        or os.environ.get("CORPUS_GRAPH_VERSION")
    )
    return {
        "path": str(p),
        "version": version,
        "exists": True,
        "nodes": len(data.get("nodes") or []),
        "links": len(data.get("links") or []),
        "built_at_commit": data.get("built_at_commit"),
    }


def check_graph_version(expected: str | None = None, *, strict: bool = True) -> dict:
    """Compare GRAPH_VERSION (or explicit expected) against graph metadata.

    Returns a result dict. When strict=True and a mismatch is detected with
    both sides present, raises GraphVersionMismatchError.
    """
    expected = expected if expected is not None else os.environ.get("GRAPH_VERSION", "")
    expected = (expected or "").strip()
    meta = read_graph_metadata()
    actual = (meta.get("version") or "").strip() if meta.get("version") else ""
    result = {
        "ok": True,
        "expected": expected or None,
        "actual": actual or None,
        "path": meta.get("path"),
        "exists": meta.get("exists", False),
        "message": "ok",
    }
    if not meta.get("exists"):
        result["ok"] = False
        result["message"] = (
            f"graph.json not found (GRAPH_JSON_PATH={os.environ.get('GRAPH_JSON_PATH')!r})"
        )
        if strict and expected:
            raise GraphVersionMismatchError(result["message"], result)
        return result
    if expected and actual and expected != actual:
        result["ok"] = False
        result["message"] = (
            f"GRAPH_VERSION mismatch: expected {expected!r}, graph has {actual!r} "
            f"(path={meta.get('path')}). Update the engine or point GRAPH_JSON_PATH "
            f"at the matching graph.json."
        )
        if strict:
            raise GraphVersionMismatchError(result["message"], result)
        return result
    if expected and not actual:
        # Graph has no embedded version — accept if file exists, note soft warn.
        result["message"] = (
            f"GRAPH_VERSION={expected!r} set but graph has no version metadata; "
            f"accepting file at {meta.get('path')}"
        )
    return result


class GraphVersionMismatchError(RuntimeError):
    """Raised when GRAPH_VERSION does not match graph.json metadata."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class GraphRAG:
    """In-memory Vedic knowledge graph. Singleton — load once, query many."""

    _instance: GraphRAG | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
            cls._instance._load_error: str | None = None
            cls._instance.nodes = []
            cls._instance.links = []
            cls._instance.hyperedges = []
            cls._instance._nodes_by_id = {}
            cls._instance._links_from = defaultdict(list)
            cls._instance._links_to = defaultdict(list)
            cls._instance._community_nodes = defaultdict(list)
            cls._instance._keyword_index = defaultdict(set)
            cls._instance._label_index = {}
            cls._instance.graph_path: str | None = None
            cls._instance.graph_version: str | None = None
        return cls._instance

    @classmethod
    def reset_singleton(cls) -> None:
        """Drop the singleton (tests / reload after GRAPH_JSON_PATH change)."""
        cls._instance = None

    def _load(self):
        if self._loaded or getattr(self, "_load_attempted", False):
            return
        self._load_attempted = True
        path = resolve_graph_path()
        if path is None:
            self._load_error = "graph.json not found"
            logger.warning(
                "vedic_knowledge: graph.json not found — GraphRAG running empty "
                "(set GRAPH_JSON_PATH to enable knowledge search)"
            )
            self._loaded = False
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            self._load_error = str(exc)
            logger.warning("vedic_knowledge: failed to load %s: %s", path, exc)
            self._loaded = False
            return

        self.graph_path = str(path)
        self.graph_version = (
            data.get("version")
            or data.get("graph_version")
            or (data.get("metadata") or {}).get("version")
            or data.get("built_at_commit")
        )
        self.nodes = list(data.get("nodes", []))
        self.links = list(data.get("links", []))
        self.hyperedges = list(data.get("hyperedges", []))
        self._nodes_by_id = {n["id"]: n for n in self.nodes}
        self._links_from = defaultdict(list)
        self._links_to = defaultdict(list)
        self._community_nodes = defaultdict(list)
        self._keyword_index = defaultdict(set)
        self._label_index = {}
        for n in self.nodes:
            node_id = n["id"]
            cid = n.get("community", -1)
            self._community_nodes[cid].append(node_id)
            label = n.get("label", "")
            tokens = _tokenize(label)
            for token in tokens:
                self._keyword_index[token].add(node_id)
            if label not in self._label_index:
                self._label_index[label] = node_id
        for link in self.links:
            src = link.get("source", "")
            tgt = link.get("target", "")
            self._links_from[src].append(link)
            self._links_to[tgt].append(link)
        self._loaded = True
        self._load_error = None

    def __init__(self):
        self._load()

    # ── Lookup APIs ──────────────────────────────────────────────────────

    def node(self, node_id: str):
        """Return node dict by ID or label, or None."""
        return self._nodes_by_id.get(node_id) or self._nodes_by_id.get(
            self._label_index.get(node_id, "")
        )

    def search(self, query: str, top_n: int = 20) -> list[dict]:
        """Keyword search across node labels. Returns ranked list of {id, label, score, community}."""
        if not self._loaded:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores: dict[str, float] = defaultdict(float)
        for token in tokens:
            for node_id in self._keyword_index.get(token, set()):
                scores[node_id] += 1
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_n]
        return [
            {
                "id": nid,
                "label": self._nodes_by_id[nid].get("label", ""),
                "score": s,
                "community": self._nodes_by_id[nid].get("community", -1),
                "source_file": self._nodes_by_id[nid].get("source_file", None),
            }
            for nid, s in ranked
        ]

    def neighbours(self, node_id: str, depth: int = 1) -> dict:
        """BFS traversal from a node, returns {nodes: [...], links: [...], depth}."""
        if not self._loaded:
            return {"depth": depth, "nodes": [], "links": []}
        nid = self._label_index.get(node_id, node_id)
        visited: set[str] = {nid}
        frontier: set[str] = {nid}
        all_links: list[dict] = []
        for d in range(depth):
            next_frontier: set[str] = set()
            for f in frontier:
                for link in self._links_from.get(f, []):
                    tgt = link.get("target", "")
                    all_links.append(link)
                    if tgt not in visited:
                        visited.add(tgt)
                        next_frontier.add(tgt)
                for link in self._links_to.get(f, []):
                    src = link.get("source", "")
                    all_links.append(link)
                    if src not in visited:
                        visited.add(src)
                        next_frontier.add(src)
            frontier = next_frontier
        return {
            "depth": depth,
            "nodes": [self._nodes_by_id[nid] for nid in visited if nid in self._nodes_by_id],
            "links": all_links,
        }

    def community(self, cid: int) -> list[dict]:
        """All nodes in a community."""
        return [
            self._nodes_by_id[nid]
            for nid in self._community_nodes.get(cid, [])
            if nid in self._nodes_by_id
        ]

    def links_by_relation(self, relation: str, node_id: str | None = None) -> list[dict]:
        """All links of a specific relation type, optionally filtered by source node."""
        candidates = self._links_from.get(node_id, []) if node_id else self.links
        return [l for l in candidates if l.get("relation") == relation]

    # ── Domain-specific APIs ─────────────────────────────────────────────

    def transit_effects(self, planet: str, house: int | None = None) -> list[dict]:
        """Get classical transit effects for a planet from the Gochar Phaladeepika text."""
        results = []
        planet_ids = self._planet_node_ids(planet)
        for pid in planet_ids:
            for link in self._links_from.get(pid, []):
                rel = link.get("relation", "")
                tgt_node = self._nodes_by_id.get(link.get("target", ""))
                if not tgt_node:
                    continue
                tgt_label = tgt_node.get("label", "")
                if rel == "gives_result":
                    results.append(
                        {
                            "effect": tgt_label,
                            "source": tgt_node.get("source_file", ""),
                            "confidence": link.get("confidence_score", 1.0),
                            "relation": "gives_result",
                        }
                    )
                elif any(
                    k in rel
                    for k in (
                        "transit_in_house",
                        "transit_best",
                        "transit_worst",
                        "is_auspicious",
                        "is_inauspicious",
                        "produces_during",
                        "can_give",
                    )
                ):
                    results.append(
                        {
                            "effect": tgt_label,
                            "source": tgt_node.get("source_file", ""),
                            "confidence": link.get("confidence_score", 1.0),
                            "relation": rel,
                        }
                    )
            for link in self._links_to.get(pid, []):
                src_node = self._nodes_by_id.get(link.get("source", ""))
                if not src_node or link.get("relation") != "gives_result":
                    continue
                results.append(
                    {
                        "effect": src_node.get("label", ""),
                        "source": src_node.get("source_file", ""),
                        "confidence": link.get("confidence_score", 1.0),
                        "relation": f"gives_result (via {pid.rsplit('_', 1)[-1]})",
                    }
                )
        return results

    def _planet_node_ids(self, planet: str) -> list[str]:
        """Find all graph node IDs related to a planet name."""
        planet_lower = planet.lower()
        ids = set()
        for n in self.nodes:
            nid = n["id"]
            label_lower = n.get("label", "").lower()
            if planet_lower == nid.lower():
                ids.add(nid)
            elif planet_lower in label_lower or label_lower.startswith(f"{planet_lower} ("):
                ids.add(nid)
        return sorted(ids, key=lambda x: (0 if "gochar" in x else 1, x))

    def vedha(self, planet: str) -> dict | None:
        """Get vedha (cancellation) pairs for a planet from Gochar text."""
        for pid in self._planet_node_ids(planet):
            for link in self._links_from.get(pid, []):
                if link.get("relation") == "has_vedha_at":
                    tgt = self._nodes_by_id.get(link.get("target", ""))
                    return {
                        "planet": planet,
                        "vedha_pairs": tgt.get("label", "") if tgt else "",
                        "source": tgt.get("source_file", "") if tgt else "",
                    }
        return None

    def activity_rules(self, activity: str) -> dict | None:
        """Get muhurta rules for an activity."""
        act_id = self._find_activity_node(activity)
        if not act_id:
            return None
        node = self._nodes_by_id[act_id]
        result = {"activity": node.get("label", activity), "favored_by": [], "contraindicated": []}
        for link in self._links_to.get(act_id, []):
            src = self._nodes_by_id.get(link.get("source", ""))
            if not src:
                continue
            rel = link.get("relation", "")
            if rel == "favored_by":
                result["favored_by"].append(
                    {
                        "node": src.get("label", ""),
                        "source": src.get("source_file", ""),
                    }
                )
            elif rel == "contraindicated_by":
                result["contraindicated"].append(
                    {
                        "node": src.get("label", ""),
                        "source": src.get("source_file", ""),
                    }
                )
        return result if (result["favored_by"] or result["contraindicated"]) else None

    def _find_activity_node(self, activity: str) -> str | None:
        """Find an activity node ID by fuzzy keyword match on label."""
        tokens = _tokenize(activity)
        best_id, best_score = None, 0
        for n in self.nodes:
            label = n.get("label", "").lower()
            nid = n["id"]
            if not nid.startswith("activity_mapping_act_"):
                continue
            score = sum(1 for t in tokens if t in label)
            if score > best_score:
                best_score, best_id = score, nid
        return best_id if best_score >= 1 else None

    def yoga_info(self, yoga_name: str) -> dict | None:
        """Get yoga definition, required planets, and classical descriptions."""
        yoga_id = self._find_yoga_node(yoga_name)
        if not yoga_id:
            return None
        info = {
            "yoga": yoga_name,
            "label": self._nodes_by_id[yoga_id].get("label", ""),
            "source_file": self._nodes_by_id[yoga_id].get("source_file", ""),
            "required_planets": [],
            "hyperedge_groups": [],
            "descriptions": [],
        }
        for link in self._links_from.get(yoga_id, []):
            rel = link.get("relation", "")
            tgt = self._nodes_by_id.get(link.get("target", ""))
            if not tgt:
                continue
            tgt_label = tgt.get("label", "")
            if rel in ("requires", "compose", "triggers"):
                info["required_planets"].append(tgt_label)
            elif rel in ("gives_effect", "expands_on", "demonstrates"):
                info["descriptions"].append(tgt_label)
        for he in self.hyperedges:
            if yoga_id in he.get("nodes", []):
                he_nodes = [
                    self._nodes_by_id[nid].get("label", nid)
                    for nid in he.get("nodes", [])
                    if nid in self._nodes_by_id and nid != yoga_id
                ]
                info["hyperedge_groups"].append(
                    {
                        "label": he.get("label", ""),
                        "members": he_nodes,
                        "confidence": he.get("confidence", "EXTRACTED"),
                    }
                )
        return info

    def _find_yoga_node(self, yoga_name: str) -> str | None:
        """Find yoga node ID by fuzzy keyword match."""
        tokens = _tokenize(yoga_name)
        for n in self.nodes:
            if yoga_name.lower() == n.get("label", "").lower():
                return n["id"]
        best_id, best_score = None, 0
        for n in self.nodes:
            label = n.get("label", "").lower()
            nid = n["id"]
            if "yoga" not in nid:
                continue
            score = sum(1 for t in tokens if t in label)
            if score > best_score:
                best_score, best_id = score, nid
        return best_id if best_score >= 1 else None

    def god_nodes(self, top_n: int = 15) -> list[dict]:
        """Return the most-connected nodes (highest degree centrality)."""
        degrees: dict[str, int] = defaultdict(int)
        for link in self.links:
            degrees[link.get("source", "")] += 1
            degrees[link.get("target", "")] += 1
        ranked = sorted(degrees.items(), key=lambda x: -x[1])[:top_n]
        return [
            {
                "id": nid,
                "label": self._nodes_by_id[nid].get("label", ""),
                "degree": d,
                "community": self._nodes_by_id[nid].get("community", -1),
            }
            for nid, d in ranked
            if nid in self._nodes_by_id
        ]

    def contradictions(self) -> list[dict]:
        """Return all 'contradicts' links (text conflicts to note)."""
        return [
            {
                "source": self._nodes_by_id.get(l.get("source", ""), {}).get(
                    "label", l.get("source")
                ),
                "target": self._nodes_by_id.get(l.get("target", ""), {}).get(
                    "label", l.get("target")
                ),
                "source_file": l.get("source_file", ""),
            }
            for l in self.links
            if l.get("relation") == "contradicts"
        ]

    @property
    def stats(self) -> dict:
        sources = {n.get("source_file", "") for n in self.nodes if n.get("source_file")}
        return {
            "nodes": len(self.nodes),
            "links": len(self.links),
            "hyperedges": len(self.hyperedges),
            "communities": len(self._community_nodes),
            "source_files": len(sources),
            "loaded": self._loaded,
            "path": self.graph_path,
            "version": self.graph_version,
            "error": self._load_error,
        }


def _tokenize(text: str) -> set[str]:
    """Lowercase tokenizer preserving multi-word phrases in quotes."""
    text = text.strip().lower()
    quoted = set(re.findall(r'"([^"]+)"', text))
    text = re.sub(r'"[^"]+"', "", text)
    plain = re.findall(r"[a-z0-9]+", text)
    return set(plain) | quoted
