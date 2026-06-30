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


def fetch_nodes_by_ids_via_supabase(node_ids: list[str], graph_version: str = "newbooks-v1", batch: int = 50) -> list[dict]:
    """Fetch full rows for specific node ids using id=in.(...) batches (small batches to keep URL safe).
    Falls back to per-id GETs if a batch fails.
    """
    env = load_env()
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key or not node_ids:
        return []
    try:
        import requests
    except Exception:
        return []
    headers = {
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    out = []
    seen = set()
    for i in range(0, len(node_ids), batch):
        chunk = [nid for nid in node_ids[i : i + batch] if nid]
        if not chunk:
            continue
        ids_literal = ",".join(chunk)
        got_any = False
        try:
            params = {
                "select": "id,label,source_file,source_location,properties,community,norm_label,description,rule_text",
                "graph_version": "eq." + graph_version,
                "id": "in.(" + ids_literal + ")",
                "limit": str(len(chunk) + 10),
            }
            r = requests.get(url + "/rest/v1/graph_nodes", headers=headers, params=params, timeout=60)
            if r.ok:
                for n in (r.json() or []):
                    nid = n.get("id")
                    if nid and nid not in seen:
                        seen.add(nid)
                        out.append(n)
                got_any = True
        except Exception:
            pass
        if not got_any:
            # per-id fallback (slower but reliable)
            for nid in chunk:
                if nid in seen:
                    continue
                try:
                    r = requests.get(
                        url + f"/rest/v1/graph_nodes?id=eq.{nid}&graph_version=eq.{graph_version}&limit=1",
                        headers=headers,
                        timeout=20,
                    )
                    if r.ok:
                        for n in (r.json() or []):
                            if n.get("id") and n["id"] not in seen:
                                seen.add(n["id"])
                                out.append(n)
                except Exception:
                    pass
    return out


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
        props["patch_method"] = meth
        injected["match_method"] = meth
        injected["patch_method"] = meth
        node["match_method"] = meth
        node["patch_method"] = meth
    conf = p.get("confidence")
    if conf is not None:
        props["confidence"] = conf
        props["patch_conf"] = conf
        injected["confidence"] = conf
        injected["patch_conf"] = conf
        node["confidence"] = conf
        node["patch_conf"] = conf
    if p.get("book_id"):
        props["book_id"] = p["book_id"]
        node["book_id"] = p["book_id"]
    if p.get("matched_on") is not None:
        props["matched_on"] = p["matched_on"]
    if p.get("review_needed") is not None:
        props["review_needed"] = p.get("review_needed")
        injected["review_needed"] = p.get("review_needed")
    node["properties"] = props
    for fk in ("chapter_id", "section_id", "hierarchy_path"):
        if fk in props:
            node[fk] = props[fk]
    return injected


def _load_supabase_env():
    env = load_env()
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY")
    return url, key


def _supabase_patch_properties(node_id: str, props_update: dict, graph_version: str = "newbooks-v1") -> tuple[int, str]:
    """PATCH a subset of properties for a graph node. Returns (code, body_text)."""
    url, key = _load_supabase_env()
    if not url or not key:
        return (0, "no-supabase-env")
    try:
        import requests
    except Exception:
        return (0, "no-requests")
    headers = {
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    # Merge strategy: send the full properties object we want (caller should pass merged)
    # We PATCH only properties + updated_at to avoid clobbering other columns.
    body = {
        "properties": props_update,
        "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    try:
        r = requests.patch(
            f"{url.rstrip('/')}/rest/v1/graph_nodes?id=eq.{node_id}&graph_version=eq.{graph_version}",
            headers=headers,
            json=body,
            timeout=30,
        )
        return (r.status_code, r.text[:500] if r.text else "")
    except Exception as e:
        return (0, str(e)[:300])


def _api_request(env_url: str, env_key: str, method: str, path: str, body: bytes | None = None, *, timeout: int = 120, extra_headers: dict | None = None) -> tuple[int, bytes]:
    import subprocess, time
    url = env_url.rstrip("/") + path
    h = {
        "apikey": env_key,
        "Authorization": f"Bearer {env_key}",
    }
    if extra_headers:
        h.update(extra_headers)
    if body is not None and "Content-Type" not in h:
        h["Content-Type"] = "application/json"
    last_err = ""
    for attempt in range(5):
        cmd = ["curl", "-sS", "-w", "\n%{http_code}", "-X", method, url]
        for k, v in h.items():
            cmd.extend(["-H", f"{k}: {v}"])
        if body is not None:
            cmd.extend(["--data-binary", "@-"])
            proc = subprocess.run(cmd, input=body, capture_output=True, timeout=timeout)
        else:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if proc.returncode == 0:
            raw = proc.stdout
            if b"\n" not in raw:
                return 0, raw
            *body_lines, code_line = raw.rsplit(b"\n", 1)
            try:
                code = int(code_line.decode().strip())
            except ValueError:
                return 0, raw
            if code >= 500 and attempt < 4:
                time.sleep(2**attempt)
                continue
            return code, b"\n".join(body_lines)
        last_err = proc.stderr.decode(errors="replace")[:400]
        if attempt < 4:
            time.sleep(2**attempt)
    raise RuntimeError(f"curl failed after retries: {last_err}")


def apply_supabase_patches_fast(id_to_node: dict, filtered_patches: list[dict], batch_size: int = 200) -> dict:
    """Fast batch upsert of patched nodes to Supabase graph_nodes using on_conflict merge.
    Re-uses the sync pattern for speed (hundreds per roundtrip instead of 1-per-PATCH).
    """
    url, key = _load_supabase_env()
    if not url or not key:
        return {"status": "skipped", "reason": "no SUPABASE_URL/KEY"}
    from datetime import datetime, timezone as _tz
    # Build targets: only nodes we have post-merge with chapter
    # IMPORTANT: every row MUST have exactly the same keys for postgrest bulk upsert.
    FIXED_KEYS = ("id", "graph_version", "label", "file_type", "source_file", "source_location", "community", "properties", "updated_at")
    targets = []
    now_iso = datetime.now(_tz.utc).isoformat()
    for p in filtered_patches:
        nid = p.get("node_id")
        n = id_to_node.get(nid) if nid else None
        if not n:
            continue
        props = dict(n.get("properties") or {})
        if not props.get("chapter_id"):
            continue
        row = {
            "id": nid,
            "graph_version": "newbooks-v1",
            "label": n.get("label"),
            "file_type": n.get("file_type"),
            "source_file": n.get("source_file"),
            "source_location": n.get("source_location"),
            "community": n.get("community"),
            "properties": props,
            "updated_at": now_iso,
        }
        targets.append(row)
    if not targets:
        return {"status": "done", "wrote": 0, "attempted": 0, "reason": "no targets with chapter_id after merge"}
    wrote = 0
    errors = 0
    sample_errs = []
    for i in range(0, len(targets), batch_size):
        chunk = targets[i : i + batch_size]
        body = json.dumps(chunk).encode()
        try:
            code, resp = _api_request(
                url,
                key,
                "POST",
                "/rest/v1/graph_nodes?on_conflict=id,graph_version",
                body,
                timeout=180,
                extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            )
            # Supabase returns 201/200 on success with Prefer resolution
            if code in (200, 201, 204):
                wrote += len(chunk)
            else:
                errors += len(chunk)
                if len(sample_errs) < 2:
                    sample_errs.append({"batch_start": i, "code": code, "body": resp[:400].decode(errors="replace") if resp else ""})
        except Exception as e:
            errors += len(chunk)
            if len(sample_errs) < 2:
                sample_errs.append({"batch_start": i, "error": str(e)[:300]})
        print(f"  supabase upsert progress: {min(i+batch_size, len(targets))}/{len(targets)} wrote={wrote} errs={errors}")
    return {"status": "done", "wrote": wrote, "errors": errors, "attempted": len(targets), "samples": sample_errs}


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
        # Fast path for patch apply: bulk load graph for the version then filter locally by needed ids
        # This is O(total) once instead of O(patches) roundtrips.
        env = load_env()
        u = env.get("SUPABASE_URL")
        k = env.get("SUPABASE_SERVICE_ROLE_KEY")
        if u and k:
            try:
                import requests as _rq
                hh = {"apikey": k, "Authorization": "Bearer " + k, "Accept": "application/json"}
                # page in 1000s
                bulk = []
                offset = 0
                page = 1000
                while True:
                    r = _rq.get(u + f"/rest/v1/graph_nodes?graph_version=eq.newbooks-v1&select=id,label,source_file,source_location,properties,community,norm_label,description,rule_text&limit={page}&offset={offset}", headers=hh, timeout=120)
                    if not r.ok:
                        break
                    batch = r.json() or []
                    bulk.extend(batch)
                    if len(batch) < page:
                        break
                    offset += page
                    if offset % 5000 == 0:
                        print("  bulk fetched so far:", len(bulk))
                if bulk:
                    nodes = bulk
                    print("Loaded", len(nodes), "nodes via bulk Supabase scan for newbooks-v1")
            except Exception as e:
                print("bulk scan failed, falling back:", e)
        if not nodes:
            nodes = fetch_nodes_via_supabase(book_stems)
            print("Loaded", len(nodes), "nodes via Supabase (filtered to books by source_file)")
        # Augment with any still-missing needed ids (small fallback)
        needed = [p.get("node_id") for p in filtered_patches if p.get("node_id")]
        have_ids = {n.get("id") for n in nodes if n.get("id")}
        missing = [nid for nid in needed if nid and nid not in have_ids]
        if missing:
            by_id = fetch_nodes_by_ids_via_supabase(missing, batch=40)
            addl = [n for n in by_id if n.get("id") and n["id"] not in have_ids]
            nodes.extend(addl)
            print("  +", len(addl), "by-id for any stragglers")
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
            props = node.get("properties") or {}
            if not props.get("patch_method"):
                # stamp patch provenance markers even if chapter+method+conf already match
                injected = merge_into_node(node, p)
                applied += 1
                if len(sample_changes) < args.limit_samples:
                    sample_changes.append({"node_id": nid, "injected": injected, "patch": {"chapter_id": p.get("chapter_id"), "method": p.get("method"), "confidence": p.get("confidence")}})
            else:
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
    supabase_targets = 0
    if args.supabase:
        for p in filtered_patches:
            n = id_to_node.get(p.get("node_id") or "")
            if n and ((n.get("properties") or {}).get("chapter_id")):
                supabase_targets += 1
        would_write_count = supabase_targets

    if sample_changes:
        print("\n=== SAMPLE CHANGES ===")
        for s in sample_changes:
            print("node:", s["node_id"])
            print("  ->", s["injected"])

    if do_write:
        if args.supabase:
            print("\n[supabase] Executing fast batch upserts (on_conflict=id,graph_version).")
            print("  This will send", supabase_targets, "rows; properties merged for chapter provenance.")
            print("  Safety: no local .bak (Supabase change history / prior graph export is your restore point).")
            supa_res = apply_supabase_patches_fast(id_to_node, filtered_patches)
            print("[supabase] result:", supa_res)
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
    if args.supabase:
        print("supabase_upsert_targets:", supabase_targets)
    print("post-apply equivalent count (for filtered patches):", post_equiv)


if __name__ == "__main__":
    main()
