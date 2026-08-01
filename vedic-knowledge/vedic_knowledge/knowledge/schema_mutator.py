"""Self-evolving schema — detect emerging communities, relation types, node types.

When a batch of new nodes/links is ingested, SchemaMutator:
  - Detects CLUSTERS: >5 new nodes sharing a common concept prefix (e.g.
    "Kalachakra_") that is not already represented as a community label →
    propose a new community.
  - Detects novel RELATION types: >3 new links share a relation label not in
    the existing link-type vocabulary → propose a new relation type.
  - Detects novel NODE types (file_type) not in the existing set.
  - Emits a MUTATION PROPOSAL JSON with justification, source citations, and
    node/link counts.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

def _default_graph_path() -> Path:
    for key in ("GRAPH_JSON_PATH", "GRAPHIFY_GRAPH_PATH"):
        raw = os.environ.get(key)
        if raw:
            return Path(raw)
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "graph" / "graph.json",
        here.parents[3] / "cvce" / "graph_rag" / "graph.json",
        here.parents[3] / "knowledge-graph" / "graphify-out" / "graph.json",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return candidates[0]


DEFAULT_GRAPH_PATH = _default_graph_path()

# Thresholds (overridable via kwargs)
CLUSTER_MIN_NODES = 5
RELATION_MIN_LINKS = 3
NODE_TYPE_MIN = 3

_PREFIX_RE = re.compile(
    r"^([A-Za-z][A-Za-z0-9]*(?:[_\-][A-Za-z][A-Za-z0-9]*)+)"  # Kalachakra_Dasha_X
)
_WORD_PREFIX_RE = re.compile(r"^([A-Z][a-zA-Z]+(?:[_\-\s][A-Z][a-zA-Z]+){0,3})")


def load_graph(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_GRAPH_PATH
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def _existing_relation_types(links: list[dict]) -> set[str]:
    out: set[str] = set()
    for l in links:
        rel = l.get("relation") or l.get("type") or l.get("label")
        if isinstance(rel, str) and rel.strip():
            out.add(rel.strip())
    return out


def _existing_node_types(nodes: list[dict]) -> set[str]:
    out: set[str] = set()
    for n in nodes:
        ft = n.get("file_type") or n.get("type") or n.get("node_type")
        if isinstance(ft, str) and ft.strip():
            out.add(ft.strip())
    return out


def _community_label_index(nodes: list[dict]) -> dict[int, list[str]]:
    """Map community id → sample labels (for prefix / theme matching)."""
    by_c: dict[int, list[str]] = defaultdict(list)
    for n in nodes:
        cid = n.get("community")
        if cid is None:
            continue
        try:
            cid_i = int(cid)
        except (TypeError, ValueError):
            continue
        lab = str(n.get("label") or n.get("id") or "")
        if lab and len(by_c[cid_i]) < 40:
            by_c[cid_i].append(lab)
    return by_c


def _normalize_prefix(raw: str) -> str:
    return re.sub(r"[\s\-]+", "_", raw.strip()).strip("_")


def _extract_prefixes(label: str) -> list[str]:
    """Candidate concept prefixes from a node label or id."""
    if not label:
        return []
    candidates: list[str] = []
    # id-style: Kalachakra_Dasha_Start
    m = _PREFIX_RE.match(label.replace(" ", "_"))
    if m:
        # take progressive prefixes of underscore parts
        parts = m.group(1).split("_")
        for i in range(1, min(len(parts), 4)):
            candidates.append("_".join(parts[: i + 1]) if i else parts[0])
        candidates.append(parts[0])
    # Title-case multiword: "Kalachakra Dasha"
    words = re.findall(r"[A-Za-z][A-Za-z0-9]+", label)
    if words:
        candidates.append(words[0])
        if len(words) >= 2:
            candidates.append(f"{words[0]}_{words[1]}")
        if len(words) >= 3:
            candidates.append(f"{words[0]}_{words[1]}_{words[2]}")
    # Dedup preserve order
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        key = c.lower()
        if key in seen or len(c) < 3:
            continue
        seen.add(key)
        out.append(c)
    return out


def _prefix_already_community(prefix: str, community_labels: dict[int, list[str]]) -> int | None:
    """Return community id if prefix already dominates an existing community."""
    pref = prefix.lower().replace("_", " ")
    pref_compact = prefix.lower().replace("_", "")
    for cid, labels in community_labels.items():
        if not labels:
            continue
        hits = 0
        for lab in labels:
            low = lab.lower()
            if pref in low or pref_compact in low.replace(" ", "").replace("_", ""):
                hits += 1
        if hits >= max(3, len(labels) // 4):
            return cid
    return None


class SchemaMutator:
    """Propose schema mutations from a batch of newly ingested graph elements."""

    def __init__(
        self,
        graph_path: Path | str | None = None,
        *,
        cluster_min: int = CLUSTER_MIN_NODES,
        relation_min: int = RELATION_MIN_LINKS,
        node_type_min: int = NODE_TYPE_MIN,
    ):
        self.graph_path = Path(graph_path) if graph_path else DEFAULT_GRAPH_PATH
        self.cluster_min = int(cluster_min)
        self.relation_min = int(relation_min)
        self.node_type_min = int(node_type_min)
        self._existing_relations: set[str] = set()
        self._existing_node_types: set[str] = set()
        self._community_labels: dict[int, list[str]] = {}
        self._existing_prefixes: Counter = Counter()
        self._loaded = False

    def load_corpus(self) -> dict[str, Any]:
        data = load_graph(self.graph_path)
        nodes = list(data.get("nodes") or [])
        links = list(data.get("links") or [])
        self._existing_relations = _existing_relation_types(links)
        self._existing_node_types = _existing_node_types(nodes)
        self._community_labels = _community_label_index(nodes)
        # Build prefix frequency over existing labels so we don't re-propose
        pref_counts: Counter = Counter()
        for n in nodes:
            for src in (n.get("label"), n.get("id")):
                if not src:
                    continue
                for p in _extract_prefixes(str(src)):
                    pref_counts[p.lower()] += 1
        self._existing_prefixes = pref_counts
        self._loaded = True
        return {
            "node_count": len(nodes),
            "link_count": len(links),
            "relation_types": len(self._existing_relations),
            "node_types": sorted(self._existing_node_types),
            "communities": len(self._community_labels),
        }

    def propose(
        self,
        new_nodes: list[dict[str, Any]] | None = None,
        new_links: list[dict[str, Any]] | None = None,
        *,
        # When new_nodes is None, analyse the full graph for emergent structure
        analyse_full_graph: bool = False,
    ) -> dict[str, Any]:
        """
        Generate a mutation proposal JSON:

          {
            new_communities: [...],
            new_relation_types: [...],
            new_node_types: [...],
            meta: {...}
          }
        """
        if not self._loaded:
            self.load_corpus()

        new_nodes = list(new_nodes or [])
        new_links = list(new_links or [])

        # Full-graph mode: treat every node/link as "new" for detection against
        # empty baselines of "already proposed" — used to surface real communities
        # from graph.json itself (verification path).
        if analyse_full_graph and not new_nodes:
            data = load_graph(self.graph_path)
            new_nodes = list(data.get("nodes") or [])
            new_links = list(data.get("links") or [])
            # For full-graph, we still want communities that LOOK like prefix clusters
            # even if the prefix is frequent — report top emerging prefix clusters
            # that aren't already tagged as their own community theme.
            return self._propose_from_full_graph(new_nodes, new_links)

        new_communities = self._detect_communities(new_nodes)
        new_relation_types = self._detect_relations(new_links)
        new_node_types = self._detect_node_types(new_nodes)

        proposal = {
            "new_communities": new_communities,
            "new_relation_types": new_relation_types,
            "new_node_types": new_node_types,
            "meta": {
                "new_node_count": len(new_nodes),
                "new_link_count": len(new_links),
                "existing_relation_types": len(self._existing_relations),
                "existing_communities": len(self._community_labels),
                "existing_node_types": sorted(self._existing_node_types),
                "cluster_min": self.cluster_min,
                "relation_min": self.relation_min,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "proposal_count": (
                    len(new_communities) + len(new_relation_types) + len(new_node_types)
                ),
            },
        }
        return proposal

    def propose_and_store(
        self,
        new_nodes: list[dict[str, Any]] | None = None,
        new_links: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            from knowledge_engine import memory_state
        except ImportError:
            memory_state = None  # type: ignore

        proposal = self.propose(new_nodes, new_links, **kwargs)
        memory_state.set_latest_mutations(proposal)
        return proposal

    # ── detectors ──────────────────────────────────────────────────────────

    def _detect_communities(self, new_nodes: list[dict]) -> list[dict[str, Any]]:
        prefix_nodes: dict[str, list[dict]] = defaultdict(list)
        for n in new_nodes:
            label = str(n.get("label") or "")
            nid = str(n.get("id") or "")
            prefixes: list[str] = []
            prefixes.extend(_extract_prefixes(label))
            prefixes.extend(_extract_prefixes(nid))
            # unique
            seen: set[str] = set()
            for p in prefixes:
                key = p.lower()
                if key in seen:
                    continue
                seen.add(key)
                prefix_nodes[p].append(n)

        proposals: list[dict[str, Any]] = []
        # Prefer longer/more specific prefixes first; skip if a longer one already covers
        ranked = sorted(prefix_nodes.items(), key=lambda kv: (-len(kv[1]), -len(kv[0])))
        accepted_prefixes: list[str] = []

        for prefix, members in ranked:
            if len(members) < self.cluster_min:
                continue
            # Skip if this prefix is a substring of an already-accepted more-specific one
            # with largely the same members — keep both only if disjoint enough
            pl = prefix.lower()
            if any(pl != ap and pl in ap for ap in accepted_prefixes):
                continue

            existing_cid = _prefix_already_community(prefix, self._community_labels)
            # Also skip if the prefix is already extremely common in the corpus
            # AND already mapped to a community
            if existing_cid is not None:
                continue

            sources = sorted(
                {
                    str(m.get("source_file"))
                    for m in members
                    if m.get("source_file")
                }
            )
            sample_labels = [str(m.get("label") or m.get("id")) for m in members[:8]]
            proposals.append(
                {
                    "name": prefix,
                    "label": f"Community: {prefix.replace('_', ' ')}",
                    "node_count": len(members),
                    "node_ids": [str(m.get("id")) for m in members if m.get("id")][:50],
                    "sample_labels": sample_labels,
                    "source_citations": sources[:20],
                    "justification": (
                        f"{len(members)} new nodes share the concept prefix "
                        f"'{prefix}', which is not yet represented as its own "
                        f"community in the knowledge graph "
                        f"({len(self._community_labels)} existing communities)."
                    ),
                    "kind": "community",
                }
            )
            accepted_prefixes.append(pl)

        return proposals

    def _detect_relations(self, new_links: list[dict]) -> list[dict[str, Any]]:
        counts: Counter = Counter()
        by_rel: dict[str, list[dict]] = defaultdict(list)
        for l in new_links:
            rel = l.get("relation") or l.get("type") or l.get("label")
            if not isinstance(rel, str) or not rel.strip():
                continue
            rel = rel.strip()
            counts[rel] += 1
            by_rel[rel].append(l)

        proposals: list[dict[str, Any]] = []
        for rel, cnt in counts.most_common():
            if cnt < self.relation_min:
                continue
            if rel in self._existing_relations:
                continue
            links = by_rel[rel]
            sources = sorted(
                {str(l.get("source_file")) for l in links if l.get("source_file")}
            )
            examples = [
                {
                    "source": l.get("source"),
                    "target": l.get("target"),
                    "source_file": l.get("source_file"),
                }
                for l in links[:5]
            ]
            proposals.append(
                {
                    "name": rel,
                    "label": rel,
                    "link_count": cnt,
                    "node_count": cnt,  # alias for uniform proposal shape
                    "examples": examples,
                    "source_citations": sources[:20],
                    "justification": (
                        f"{cnt} new links use the relation label '{rel}', which is "
                        f"absent from the existing vocabulary of "
                        f"{len(self._existing_relations)} relation types."
                    ),
                    "kind": "relation_type",
                }
            )
        return proposals

    def _detect_node_types(self, new_nodes: list[dict]) -> list[dict[str, Any]]:
        counts: Counter = Counter()
        by_t: dict[str, list[dict]] = defaultdict(list)
        for n in new_nodes:
            ft = n.get("file_type") or n.get("type") or n.get("node_type")
            if not isinstance(ft, str) or not ft.strip():
                continue
            ft = ft.strip()
            counts[ft] += 1
            by_t[ft].append(n)

        proposals: list[dict[str, Any]] = []
        for ft, cnt in counts.most_common():
            if cnt < self.node_type_min:
                continue
            if ft in self._existing_node_types:
                continue
            members = by_t[ft]
            sources = sorted(
                {str(m.get("source_file")) for m in members if m.get("source_file")}
            )
            proposals.append(
                {
                    "name": ft,
                    "label": ft,
                    "node_count": cnt,
                    "sample_labels": [
                        str(m.get("label") or m.get("id")) for m in members[:8]
                    ],
                    "source_citations": sources[:20],
                    "justification": (
                        f"{cnt} new nodes use file_type/node_type '{ft}', which is "
                        f"not in the existing set {sorted(self._existing_node_types)}."
                    ),
                    "kind": "node_type",
                }
            )
        return proposals

    def _propose_from_full_graph(
        self, nodes: list[dict], links: list[dict]
    ) -> dict[str, Any]:
        """
        Analyse the whole graph for prefix clusters that look like communities
        and relation-type inventory. Used for verification / discovery, not
        only delta batches.
        """
        # Temporarily clear "existing" so detectors surface structure
        saved_rels = self._existing_relations
        saved_types = self._existing_node_types
        # Keep community labels so we only propose prefixes NOT already a community
        self._existing_relations = set()  # report all relation types as inventory
        self._existing_node_types = set()

        # Communities: only novel prefixes
        communities = self._detect_communities(nodes)

        # Relation inventory (top novel would be empty since we cleared — instead
        # report under-documented low-frequency types AND high-frequency catalogue)
        rel_counts = Counter()
        for l in links:
            rel = l.get("relation")
            if isinstance(rel, str) and rel.strip():
                rel_counts[rel.strip()] += 1

        # Restore
        self._existing_relations = saved_rels
        self._existing_node_types = saved_types

        # Propose relation types that exist in graph but might be "emerging"
        # (rare, < 1% of links) as candidates for schema documentation
        total_links = max(sum(rel_counts.values()), 1)
        new_relation_types = []
        for rel, cnt in rel_counts.most_common():
            if rel in saved_rels and cnt >= self.relation_min:
                # Already known — skip for "new"
                continue
            if cnt >= self.relation_min:
                new_relation_types.append(
                    {
                        "name": rel,
                        "label": rel,
                        "link_count": cnt,
                        "node_count": cnt,
                        "source_citations": [],
                        "justification": (
                            f"Relation '{rel}' appears {cnt} times "
                            f"({100.0 * cnt / total_links:.2f}% of links)."
                        ),
                        "kind": "relation_type",
                    }
                )

        node_type_counts = Counter(
            str(n.get("file_type"))
            for n in nodes
            if n.get("file_type")
        )
        new_node_types = [
            {
                "name": ft,
                "label": ft,
                "node_count": cnt,
                "source_citations": [],
                "justification": f"Node type '{ft}' covers {cnt} nodes in graph.json.",
                "kind": "node_type",
            }
            for ft, cnt in node_type_counts.most_common()
            if ft not in saved_types and cnt >= self.node_type_min
        ]

        # Real community catalogue (existing) for verification transparency
        community_summary = []
        for cid, labels in sorted(
            self._community_labels.items(), key=lambda kv: -len(kv[1])
        )[:30]:
            community_summary.append(
                {
                    "community_id": cid,
                    "sample_size_indexed": len(labels),
                    "sample_labels": labels[:5],
                }
            )

        return {
            "new_communities": communities[:50],
            "new_relation_types": new_relation_types[:50],
            "new_node_types": new_node_types,
            "existing_community_samples": community_summary,
            "relation_catalogue": [
                {"name": r, "link_count": c} for r, c in rel_counts.most_common(40)
            ],
            "meta": {
                "mode": "full_graph",
                "node_count": len(nodes),
                "link_count": len(links),
                "existing_communities": len(self._community_labels),
                "existing_relation_types": len(saved_rels),
                "proposed_community_count": len(communities),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }


def mutate_schema(
    new_nodes: list[dict[str, Any]] | None = None,
    new_links: list[dict[str, Any]] | None = None,
    *,
    graph_path: Path | str | None = None,
    store: bool = True,
    analyse_full_graph: bool = False,
) -> dict[str, Any]:
    """Functional API for watcher + HTTP handlers."""
    mut = SchemaMutator(graph_path=graph_path)
    mut.load_corpus()
    if store:
        return mut.propose_and_store(
            new_nodes, new_links, analyse_full_graph=analyse_full_graph
        )
    return mut.propose(new_nodes, new_links, analyse_full_graph=analyse_full_graph)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    mut = SchemaMutator()
    stats = mut.load_corpus()
    print("corpus:", json.dumps(stats, indent=2))
    # Full-graph discovery
    proposal = mut.propose(analyse_full_graph=True)
    print("meta:", json.dumps(proposal["meta"], indent=2))
    print(f"new_communities={len(proposal['new_communities'])}")
    for c in proposal["new_communities"][:8]:
        print(f"  [{c['node_count']}] {c['name']}: {c['justification'][:100]}")
    print(f"relation_catalogue top-10:")
    for r in (proposal.get("relation_catalogue") or [])[:10]:
        print(f"  {r['link_count']:5d}  {r['name']}")
    print(f"existing_community_samples={len(proposal.get('existing_community_samples') or [])}")

    # Synthetic batch test
    batch = [
        {
            "id": f"Kalachakra_Test_Node_{i}",
            "label": f"Kalachakra_Dasha_Phase_{i}",
            "file_type": "kalachakra_rule",
            "source_file": "test/kalachakra_batch.md",
        }
        for i in range(8)
    ]
    links = [
        {
            "source": f"Kalachakra_Test_Node_{i}",
            "target": f"Kalachakra_Test_Node_{i+1}",
            "relation": "kalachakra_succession",
            "source_file": "test/kalachakra_batch.md",
        }
        for i in range(6)
    ]
    batch_prop = mut.propose(batch, links)
    print("\nbatch proposal:", json.dumps(batch_prop, indent=2)[:1500])
