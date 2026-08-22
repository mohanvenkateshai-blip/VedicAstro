"""
Build graph.db from graph.json — streaming, memory-safe (B-56 durable fix).

Adapted from docs/graph-sqlite-migration-playbook_1.md to the REAL schema of
this repo's graph.json (node-link networkx export with a third top-level
collection, hyperedges — not the playbook's assumed {nodes, edges}):

  nodes:      flat dict, ~61 possible keys (id, file_type, label, source_file,
              plus sparse domain fields like rule_text/yoga_type/effects/...)
  links:      source, target (not from/to), relation, confidence,
              confidence_score, source_file, optional weight/source_location
  hyperedges: {id, label, nodes:[...3+ ids...], relation, confidence, ...}

`nodes`/`links` get a handful of indexed columns (id/type/source/target) plus
a `props` JSON blob for everything else, so every field survives the bake
without a 61-column table. `hyperedges` is baked too (real data, cheap) but
not yet wired to any KnowledgeStore consumer -- neither backend serves
hyperedges through that interface today, so this stays additive.

Usage: python build_graph_db.py [graph.json] [graph.db]
Requires: ijson (build-time only — see requirements-build.txt; never
ships in the runtime bundle).
"""

import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from decimal import Decimal

import ijson


def _json_default(o):
    # ijson yields Decimal for JSON numbers (exact-precision parsing); plain
    # json.dumps doesn't know how to serialize that back out.
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GRAPH_JSON", "graph_rag/graph.json")
DB = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("GRAPH_DB", "knowledge_engine/graph.db")

# Columns pulled out of the sparse node dict for indexed/fast access; every
# other key (rule_text, yoga_type, effects, nature, ...) goes into `props`.
NODE_CORE_FIELDS = ("id", "file_type", "label", "source_file", "community")
LINK_CORE_FIELDS = ("source", "target", "relation", "confidence", "confidence_score", "source_file")


def _scalar(v):
    return float(v) if isinstance(v, Decimal) else v


def _split_props(d: dict, core_fields: tuple[str, ...]) -> tuple[tuple, str]:
    core = tuple(_scalar(d.get(f)) for f in core_fields)
    extra = {k: v for k, v in d.items() if k not in core_fields}
    return core, json.dumps(extra, ensure_ascii=False, default=_json_default)


def build(src: str = SRC, db: str = DB) -> None:
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=OFF")  # build-time speed only
    cur.execute("PRAGMA synchronous=OFF")
    cur.executescript(
        """
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY, file_type TEXT, label TEXT,
            source_file TEXT, community INTEGER, props TEXT
        );
        CREATE TABLE links (
            source TEXT, target TEXT, relation TEXT,
            confidence TEXT, confidence_score REAL, source_file TEXT, props TEXT
        );
        CREATE TABLE hyperedges (
            id TEXT PRIMARY KEY, label TEXT, relation TEXT,
            confidence TEXT, nodes_json TEXT, props TEXT
        );
        """
    )

    node_count = 0
    with open(src, "rb") as f:
        rows = []
        for n in ijson.items(f, "nodes.item"):
            core, props = _split_props(n, NODE_CORE_FIELDS)
            rows.append((*core, props))
            node_count += 1
        cur.executemany("INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?)", rows)

    link_count = 0
    dangling = 0
    with open(src, "rb") as f:
        rows = []
        for e in ijson.items(f, "links.item"):
            core, props = _split_props(e, LINK_CORE_FIELDS)
            rows.append((*core, props))
            link_count += 1
        cur.executemany("INSERT INTO links VALUES (?,?,?,?,?,?,?)", rows)

    # Dangling-reference check (58/157 known in the current snapshot) — logged,
    # never fatal: a link pointing at a since-removed node is a data-quality
    # fact to surface, not a build-blocking error.
    cur.execute("SELECT COUNT(*) FROM links WHERE source NOT IN (SELECT id FROM nodes)")
    dangling_src = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM links WHERE target NOT IN (SELECT id FROM nodes)")
    dangling_dst = cur.fetchone()[0]

    hyperedge_count = 0
    built_at_commit = None
    with open(src, "rb") as f:
        rows = []
        for h in ijson.items(f, "hyperedges.item"):
            extra = {k: v for k, v in h.items() if k not in ("id", "label", "relation", "confidence", "nodes")}
            rows.append((
                h.get("id"), h.get("label"), h.get("relation"), h.get("confidence"),
                json.dumps(h.get("nodes", []), ensure_ascii=False, default=_json_default),
                json.dumps(extra, ensure_ascii=False, default=_json_default),
            ))
            hyperedge_count += 1
        cur.executemany("INSERT OR REPLACE INTO hyperedges VALUES (?,?,?,?,?,?)", rows)

    # built_at_commit lives at the JSON top level, not inside an array — read
    # it directly (cheap, single scalar) rather than via ijson.items streaming.
    with open(src, "rb") as f:
        for prefix, event, value in ijson.parse(f):
            if prefix == "built_at_commit" and event == "string":
                built_at_commit = value
                break

    cur.executemany(
        "INSERT INTO meta VALUES (?,?)",
        [
            ("built_at_commit", built_at_commit or ""),
            ("built_at", datetime.now(UTC).isoformat()),
            ("node_count", str(node_count)),
            ("link_count", str(link_count)),
            ("hyperedge_count", str(hyperedge_count)),
            ("dangling_source_links", str(dangling_src)),
            ("dangling_target_links", str(dangling_dst)),
        ],
    )

    cur.executescript(
        """
        CREATE INDEX idx_links_source ON links(source);
        CREATE INDEX idx_links_target ON links(target);
        CREATE INDEX idx_nodes_type   ON nodes(file_type);
        ANALYZE;
        """
    )
    con.commit()
    cur.execute("VACUUM")
    con.close()

    size_mb = os.path.getsize(db) / 1e6
    print(
        f"Built {db}: {size_mb:.1f} MB — {node_count} nodes, {link_count} links "
        f"({dangling_src} dangling source, {dangling_dst} dangling target), "
        f"{hyperedge_count} hyperedges, commit={built_at_commit}"
    )


if __name__ == "__main__":
    build()
