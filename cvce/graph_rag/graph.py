"""
graph.py — In-memory knowledge graph with search & traversal APIs.

Loads graph.json on first access (singleton). Builds adjacency lists +
inverted indices for O(1) lookups by ID, community, and keywords.

All query methods return dicts with `nodes`, `links`, and optional
`citations` (source_file, confidence) for provenance tracking.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict

_GRAPH_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph.json")
if not os.path.exists(_GRAPH_PATH):
    _GRAPH_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "knowledge-graph",
        "graphify-out",
        "graph.json",
    )


class GraphRAG:
    """In-memory Vedic knowledge graph. Singleton — load once, query many."""

    _instance: GraphRAG | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _load(self):
        if self._loaded:
            return
        with open(_GRAPH_PATH, encoding="utf-8") as f:
            data = json.load(f)
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
        """BFS traversal from a node, returns {nodes: [...], links: [...], depth}.

        depth=1: direct neighbours. depth=2: neighbours of neighbours.
        """
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
        """Get classical transit effects for a planet from the Gochar Phaladeepika text.

        Returns list of {effect, source, confidence, relation}.
        """
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
            # Also follow links FROM the planet's benefic/malefic house nodes
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
        """Find all graph node IDs related to a planet name.

        Tries exact ID, exact label, then keyword search fallback.
        Prioritises gochar nodes for transit effects.
        """
        planet_lower = planet.lower()
        ids = set()
        # Check exact ID first
        for n in self.nodes:
            nid = n["id"]
            label_lower = n.get("label", "").lower()
            if planet_lower == nid.lower():
                ids.add(nid)
            elif planet_lower in label_lower or label_lower.startswith(f"{planet_lower} ("):
                # Prefer gochar nodes for transit lookups
                ids.add(nid)
        # Sort: gochar nodes first, then alphabetically
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
        """Get muhurta rules for an activity: favored/contraindicated nakshatras, varas, karanas.

        Uses fuzzy keyword matching on activity name.
        Returns {activity, favored_by: [...], contraindicated: [...]}
        """
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
        """Get yoga definition, required planets, and classical descriptions.

        Uses fuzzy matching: first tries exact label, then keyword search fallback.
        Also checks hyperedges for group yoga compositions.
        """
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
        """Find yoga node ID by fuzzy keyword match, preferring BPHS/phaladeepika."""
        tokens = _tokenize(yoga_name)
        # First try exact label match
        for n in self.nodes:
            if yoga_name.lower() == n.get("label", "").lower():
                return n["id"]
        # Then keyword score
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

    # ── Stats ─────────────────────────────────────────────────────────────

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
        }


def _tokenize(text: str) -> set[str]:
    """Lowercase tokenizer preserving multi-word phrases in quotes."""
    text = text.strip().lower()
    quoted = set(re.findall(r'"([^"]+)"', text))
    text = re.sub(r'"[^"]+"', "", text)
    plain = re.findall(r"[a-z0-9]+", text)
    return set(plain) | quoted
