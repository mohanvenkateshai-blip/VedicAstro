#!/usr/bin/env python3
"""
Apply node->chapter patch into graph nodes (embed chapter provenance) -- EXACT per user spec.

- Loads existing patch: prefer knowledge-graph/patches/node-chapter-map.json , fallback to latest node-chapter-map.backup-*.json in patches/
- Loads nodes: from --graph (default graphify-out/graph.json) or if --supabase fetch via similar logic to map_nodes_to_structured (fetch_nodes_via_supabase)
- Filter by --books (comma stems)
- Merge into nodes: for each patch entry, locate node by id, merge to node['properties'] = { **existing, chapter_id, section_id, hierarchy_path, verse_num (if in patch), match_method: p.get('method'), confidence, ... also keep original keys if flat compat needed }
- Idempotent: skip if node already has equivalent chapter_id+method+conf
- Safe: --dry-run (no writes, just report what would change + samples), before any write make .bak of graph or skip for supabase (print SQL/REST instead), validate counts
- CLI: --dry-run, --books, --graph PATH, --supabase, --patch PATH (override), --write (to enable writes; without it always dry), --out , --apply-to-graph
- At end print action metrics: nodes loaded, patches loaded, matched/applied/skipped, books touched, would-write count.
Robust, similar helpers, no side effects unless --write and not dry. Argparse style of sibling. Idempotent and safe by design.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH = ROOT / "knowledge-graph" / "graphify-out" / "graph.json"
DEFAULT_PATCH = ROOT / "knowledge-graph" / "patches" / "node-chapter-map.json"


def load_env():
    out = {}
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        v = os.environ.get(k, "").strip()
        if v:
            out[k] = v
    env_local = ROOT / "portal" / ".env.local"
    if env_local.is_file():
        for line in env_local.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") and k not in out:
                out[k] = v
    return out


def fetch_nodes_via_supabase(stems, graph_version="newbooks-v1"):
    env = load_env()
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return []
    try:
        import requests
    except Exception:
        return []
    nodes = []
    headers = {
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    for stem in stems:
        candidates = [
            "raw/" + stem + ".md",
            "%" + stem + "%",
            "%" + stem.replace("_", " ") + "%",
        ]
        got = False
        for cand in candidates:
            try:
                params = {
                    "select": "id,label,source_file,source_location,properties,community,norm_label,description,rule_text",
                    "graph_version": "eq." + graph_version,
                    "source_file": "ilike." + cand,
                    "limit": "2000",
                }
                r = requests.get(url + "/rest/v1/graph_nodes", headers=headers, params=params, timeout=30)
                if r.ok:
                    batch = r.json()
                    if batch:
                        nodes.extend(batch)
                        got = True
                        break
            except Exception:
                continue
        if not got:
            try:
                short = stem.split("_")[0]
                params = {
                    "select": "id,label,source_file,source_location,properties,community,norm_label,description,rule_text",
                    "graph_version": "eq." + graph_version,
                    "source_file": "ilike.%" + short + "%",
                    "limit": "2000",
                }
                r = requests.get(url + "/rest/v1/graph_nodes", headers=headers, params=params, timeout=30)
                if r.ok:
                    nodes.extend([n for n in r.json() if short.lower() in (n.get("source_file") or "").lower()])
            except Exception:
                pass
    seen = set()
    uniq = []
    for n in nodes:
        nid = n.get("id")
        if nid and nid not in seen:
            seen.add(nid)
            uniq.append(n)
    return uniq


def load_graph_data(path):
    return json.loads(path.read_text(encoding="utf-8"))


def find_patch_file(override):
    if override:
        p = Path(override)
        return p if p.exists() else None
    if DEFAULT_PATCH.exists():
        return DEFAULT_PATCH
    patch_dir = ROOT / "knowledge-graph" / "patches"
    cands = sorted(patch_dir.glob("node-chapter-map.backup-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if cands:
        return cands[0]
    odd = patch_dir / "node-chapter-map.json.backup-1938-2books"
    if odd.exists():
        return odd
    any_nc = sorted(patch_dir.glob("*node-chapter*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return any_nc[0] if any_nc else None


def book_stem_matches(stems, book_id):
    if not book_id:
        return False
    bid = (book_id or "").lower().replace(" ", "_").strip()
    for s in stems:
        ss = s.lower().replace(" ", "_").strip()
        if ss == bid or ss in bid or bid in ss:
            return True
    return False


def node_has_equivalent(node, p):
    ch = p.get("chapter_id")
    meth = p.get("method")
    conf = p.get("confidence")
    props = node.get("properties") or {}
    n_ch = props.get("chapter_id") or node.get("chapter_id")
    n_meth = props.get("match_method") or props.get("method") or node.get("match_method") or node.get("method")
    n_conf = props.get("confidence") or node.get("confidence")
    if n_ch != ch:
        return False
    if n_meth != meth:
        return False
    try:
        if abs(float(n_conf or 0) - float(conf or 0)) > 0.0005:
            return False
    except Exception:
        if n_conf != conf:
            return False
    return True


def merge_into_node(node, p):
    props = dict(node.get("properties") or {})
    injected = {}
    def put(k, v):
        if v is not None:
            props[k] = v
            injected[k] = v
    put("chapter_id", p.get("chapter_id"))
    put("section_id", p.get("section_id"))
    put("hierarchy_path", p.get("hierarchy_path"))
    if p.get("verse_num") is not None:
        put("verse_num", p.get("verse_num"))
    meth = p.get("method")
    if meth is not None:
        props["match_method"] = meth
        injected["match_method"] = meth
        node["match_method"] = meth
    conf = p.get("confidence")
    if conf is not None:
        props["confidence"] = conf
        injected["confidence"] = conf
        node["confidence"] = conf
    if p.get("book_id"):
        props["book_id"] = p["book_id"]
        node["book_id"] = p["book_id"]
    if p.get("matched_on") is not None:
        props["matched_on"] = p["matched_on"]
    node["properties"] = props
    for fk in ("chapter_id", "section_id", "hierarchy_path"):
        if fk in props:
            node[fk] = props[fk]
    return injected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", required=True, help="Comma list of book stems (no .json)")
    ap.add_argument("--graph", default=str(DEFAULT_GRAPH), help="Path to graph.json")
    ap.add_argument("--patch", default=None, help="Override patch file (node-chapter-map.json or backup)")
    ap.add_argument("--supabase", action="store_true", help="Fetch nodes via Supabase using book stems")
    ap.add_argument("--dry-run", action="store_true", help="Print what would change; do not write")
    ap.add_argument("--write", action="store_true", help="Enable writes (without this, always dry)")
    ap.add_argument("--apply-to-graph", action="store_true", help="Output modified graph JSON (file mode); creates .bak before write")
    ap.add_argument("--out", default=None, help="Target path for updated graph (when --apply-to-graph) or apply summary")
    ap.add_argument("--limit-samples", type=int, default=6, help="Max samples to show for would-change")
    args = ap.parse_args()

    book_stems = [b.strip() for b in args.books.split(",") if b.strip()]
    print("Applying node chapter patch for:", book_stems)

    patch_file = find_patch_file(args.patch)
    if not patch_file or not patch_file.exists():
        print("ERROR: could not locate patch (node-chapter-map.json or latest backup in patches/)")
        return
    patch_data = json.loads(patch_file.read_text(encoding="utf-8"))
    all_patches = patch_data.get("patches", []) or []
    print("Loaded", len(all_patches), "patches from", patch_file)

    filtered_patches = [p for p in all_patches if book_stem_matches(book_stems, p.get("book_id"))]
    print(" ", len(filtered_patches), "patches match requested books")

    gdata = None
    nodes = []
    if args.supabase:
        nodes = fetch_nodes_via_supabase(book_stems)
        print("Loaded", len(nodes), "nodes via Supabase (filtered to books)")
    if not nodes:
        gpath = Path(args.graph)
        if not gpath.exists():
            print("Graph not found:", gpath)
            return
        gdata = load_graph_data(gpath)
        all_gnodes = gdata.get("nodes", [])
        print("Loaded", len(all_gnodes), "nodes from", gpath)
        nodes = all_gnodes

    if not nodes:
        print("No nodes available for apply.")
        return

    id_to_node = {n["id"]: n for n in nodes if n.get("id")}

    matched = 0
    applied = 0
    skipped = 0
    books_touched = set()
    sample_changes = []

    for p in filtered_patches:
        nid = p.get("node_id")
        if not nid:
            continue
        node = id_to_node.get(nid)
        if not node:
            continue
        matched += 1
        bid = p.get("book_id")
        if bid:
            books_touched.add(bid)
        if node_has_equivalent(node, p):
            skipped += 1
            continue
        injected = merge_into_node(node, p)
        applied += 1
        if len(sample_changes) < args.limit_samples:
            sample_changes.append({
                "node_id": nid,
                "injected": injected,
                "patch": {"chapter_id": p.get("chapter_id"), "method": p.get("method"), "confidence": p.get("confidence")}
            })

    do_write = bool(args.write and not args.dry_run)
    would_write_count = applied

    if sample_changes:
        print("\n=== SAMPLE CHANGES ===")
        for s in sample_changes:
            print("node:", s["node_id"])
            print("  ->", s["injected"])

    if do_write:
        if args.supabase:
            print("\n[supabase] Write requested - emitting intended updates (no remote mutation):")
            for s in sample_changes[: min(3, len(sample_changes))]:
                nid = s["node_id"]
                print("  REST: PATCH /rest/v1/graph_nodes?id=eq." + nid)
                print("        body example: {\"properties\": <existing merged with", s["injected"], "> }")
        elif gdata is not None and args.apply_to_graph:
            gpath = Path(args.graph)
            ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            bak = gpath.with_name(gpath.name + ".bak-" + ts)
            try:
                shutil.copy2(str(gpath), str(bak))
                print("\nBackup written:", bak)
            except Exception as e:
                print("ERROR backing up graph before write:", e)
                return
            out_path = Path(args.out) if args.out else gpath
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(gdata, indent=2, ensure_ascii=False) + "\n")
            print("Wrote updated graph:", out_path)
        else:
            if args.out:
                spath = Path(args.out)
                spath.parent.mkdir(parents=True, exist_ok=True)
                summary = {
                    "generated_at": datetime.now(UTC).isoformat(),
                    "books": book_stems,
                    "source_patch": str(patch_file),
                    "applied_count": applied,
                    "skipped_idempotent": skipped,
                    "samples": sample_changes,
                }
                spath.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
                print("Wrote apply summary:", spath)
            else:
                print("\n--write present but no --apply-to-graph and no --out for summary; nothing written to disk.")
    else:
        if args.dry_run or not args.write:
            print("\n(dry-run or --write not supplied: no disk writes performed)")

    post_equiv = 0
    for p in filtered_patches:
        n = id_to_node.get(p.get("node_id", ""))
        if n and node_has_equivalent(n, p):
            post_equiv += 1

    print("\n=== ACTION METRICS ===")
    print("nodes loaded:", len(nodes))
    print("patches loaded:", len(all_patches))
    print("matched:", matched)
    print("applied:", applied)
    print("skipped:", skipped)
    print("books touched:", len(books_touched), sorted(books_touched))
    print("would-write count:", would_write_count)
    print("post-apply equivalent count (for filtered patches):", post_equiv)


if __name__ == "__main__":
    main()
