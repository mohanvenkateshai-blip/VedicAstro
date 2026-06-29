#!/usr/bin/env python3
"""
Build graph-grok.json — additive merge of Grok semantic cache onto deterministic base.

Never prunes production graph.json. Output: knowledge-graph/graphify-out/graph-grok.json

Usage:
  python3 scripts/build-graph-grok.py              # build from cache
  python3 scripts/build-graph-grok.py --deploy     # build + sync-graph.sh --grok --deploy
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KG = ROOT / "knowledge-graph"
GRAPH_BASE = KG / "graphify-out" / "graph.json"
GRAPH_GROK = KG / "graphify-out" / "graph-grok.json"
SEMANTIC_CACHE = KG / "graphify-out" / "cache" / "semantic"
sys.path.insert(0, str(ROOT / "scripts"))
from graph_extract_common import production_node_floor  # noqa: E402


def merge_graph(base: dict, fragment: dict) -> dict:
    """Additive merge — same policy as gyan-corpus-extract / gemini-batch."""
    g = json.loads(json.dumps(base))
    existing_ids = {n["id"] for n in g.get("nodes", []) if n.get("id")}

    for n in fragment.get("nodes", []):
        if not n.get("id") or n["id"] in existing_ids:
            continue
        g.setdefault("nodes", []).append(n)
        existing_ids.add(n["id"])

    existing_links = {
        (l.get("source"), l.get("target"), l.get("relation")) for l in g.get("links", [])
    }
    edges = fragment.get("edges") or fragment.get("links") or []
    for e in edges:
        key = (e.get("source"), e.get("target"), e.get("relation"))
        if key in existing_links or not e.get("source") or not e.get("target"):
            continue
        link = dict(e)
        if "links" not in g and "edges" in fragment:
            pass
        g.setdefault("links", []).append(link)
        existing_links.add(key)

    existing_he = {h.get("id") for h in g.get("hyperedges", []) if h.get("id")}
    for h in fragment.get("hyperedges", []):
        if h.get("id") and h["id"] not in existing_he:
            g.setdefault("hyperedges", []).append(h)
            existing_he.add(h["id"])

    return g


def build_from_cache() -> tuple[dict, int, int]:
    if not GRAPH_BASE.is_file():
        print(f"error: base graph missing — {GRAPH_BASE}", file=sys.stderr)
        sys.exit(1)
    if not SEMANTIC_CACHE.is_dir():
        print(f"error: semantic cache missing — {SEMANTIC_CACHE}", file=sys.stderr)
        sys.exit(1)

    base = json.loads(GRAPH_BASE.read_text(encoding="utf-8"))
    base_nodes = len(base.get("nodes", []))
    merged = base
    merged_count = 0
    cache_files = sorted(SEMANTIC_CACHE.glob("*.json"))

    for path in cache_files:
        try:
            frag = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  skip {path.name}: {exc}", file=sys.stderr)
            continue
        before = len(merged.get("nodes", []))
        merged = merge_graph(merged, frag)
        after = len(merged.get("nodes", []))
        added = after - before
        if added or frag.get("nodes") or frag.get("edges") or frag.get("links"):
            print(f"  {path.name}: +{added} nodes")
            merged_count += 1

    return merged, base_nodes, merged_count


def main() -> int:
    ap = argparse.ArgumentParser(description="Build graph-grok.json from semantic cache")
    ap.add_argument("--deploy", action="store_true", help="sync + fly deploy after build")
    ap.add_argument("--dry-run", action="store_true", help="print stats only, do not write")
    args = ap.parse_args()

    merged, base_nodes, cache_hits = build_from_cache()
    new_nodes = len(merged.get("nodes", []))
    new_links = len(merged.get("links", []))
    new_hyper = len(merged.get("hyperedges", []))

    print(f"base: {base_nodes} nodes (deterministic graph.json)")
    print(f"cache: {cache_hits} semantic fragments merged")
    print(f"grok: {new_nodes} nodes, {new_links} links, {new_hyper} hyperedges")
    print(f"delta: +{new_nodes - base_nodes} nodes vs base")

    if new_nodes < base_nodes:
        print("error: grok graph smaller than base — aborting", file=sys.stderr)
        return 1

    floor = production_node_floor()
    beats_production = new_nodes > floor
    print(
        f"vs production floor ({floor}): "
        f"{'PASS — grok adds nodes' if beats_production else 'same count — semantic layer added links only or duplicates skipped'}"
    )

    if args.dry_run:
        print("dry-run: not writing graph-grok.json")
        return 0

    GRAPH_GROK.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✓ wrote {GRAPH_GROK}")

    if args.deploy:
        sync = ROOT / "scripts" / "sync-graph.sh"
        subprocess.run([str(sync), "--grok", "--deploy"], cwd=ROOT, check=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
