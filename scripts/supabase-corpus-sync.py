#!/usr/bin/env python3
"""Sync knowledge-graph raw/*.md + graph JSON → Supabase corpus vault (Storage + Postgres)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KG = ROOT / "knowledge-graph"
RAW = KG / "raw"
GRAPH_OUT = KG / "graphify-out"
MANIFEST = KG / "corpus-manifest.json"
ENV_LOCAL = ROOT / "portal" / ".env.local"
BUCKET = "corpus-vault"
GRAPH_VERSION = os.environ.get("CORPUS_GRAPH_VERSION", "")


def _graph_version_label() -> str:
    if GRAPH_VERSION:
        return GRAPH_VERSION
    ver_path = KG / "graph-version.json"
    if ver_path.is_file():
        return json.loads(ver_path.read_text(encoding="utf-8")).get(
            "graph_version", "newbooks-v1"
        )
    return "newbooks-v1"


BATCH = 400


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "GCP_BUCKET"):
        v = os.environ.get(k, "").strip()
        if v:
            out[k] = v
    if ENV_LOCAL.is_file():
        for line in ENV_LOCAL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") and k not in out:
                out[k] = v
    return out


def api_request(
    env: dict[str, str],
    method: str,
    path: str,
    body: bytes | None = None,
    headers: dict | None = None,
    *,
    timeout: int = 300,
) -> tuple[int, bytes]:

    url = env["SUPABASE_URL"].rstrip("/") + path
    h = {
        "apikey": env["SUPABASE_SERVICE_ROLE_KEY"],
        "Authorization": f"Bearer {env['SUPABASE_SERVICE_ROLE_KEY']}",
    }
    if headers:
        h.update(headers)
    if body is not None and "Content-Type" not in h:
        h["Content-Type"] = "application/json"

    last_err = ""
    for attempt in range(6):
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
            if code >= 500 and attempt < 5:
                time.sleep(2**attempt)
                continue
            return code, b"\n".join(body_lines)
        last_err = proc.stderr.decode(errors="replace")[:500]
        if attempt < 5:
            time.sleep(2**attempt)
    raise RuntimeError(f"curl failed after retries: {last_err}")


def ensure_bucket(env: dict[str, str]) -> None:
    code, body = api_request(
        env,
        "POST",
        "/storage/v1/bucket",
        json.dumps({"id": BUCKET, "name": BUCKET, "public": False}).encode(),
        {"Content-Type": "application/json"},
    )
    if code in (200, 201):
        print(f"✓ bucket {BUCKET} created (private)")
    elif code == 409 or b"already exists" in body.lower():
        print(f"✓ bucket {BUCKET} exists")
    else:
        print(f"bucket: HTTP {code} {body[:200]!r}")


def storage_object_path(path: str) -> str:
    import urllib.parse

    return "/".join(urllib.parse.quote(p, safe="") for p in path.split("/"))


def upload_storage(env: dict[str, str], path: str, data: bytes, content_type: str) -> None:
    encoded = storage_object_path(path)
    timeout = 600 if len(data) > 1_000_000 else 300
    code, body = api_request(
        env,
        "POST",
        f"/storage/v1/object/{BUCKET}/{encoded}",
        data,
        {"Content-Type": content_type, "x-upsert": "true"},
        timeout=timeout,
    )
    if code not in (200, 201):
        raise RuntimeError(f"storage upload {path}: HTTP {code} {body[:300]!r}")


def upsert_rows(
    env: dict[str, str], table: str, rows: list[dict], *, on_conflict: str | None = None
) -> None:
    if not rows:
        return
    path = f"/rest/v1/{table}"
    if on_conflict:
        path += f"?on_conflict={on_conflict}"
    body = json.dumps(rows).encode()
    code, resp = api_request(
        env,
        "POST",
        path,
        body,
        {
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    if code not in (200, 201):
        raise RuntimeError(f"upsert {table}: HTTP {code} {resp[:500]!r}")


def delete_graph_version(env: dict[str, str], version: str) -> None:
    for table, col in (("graph_links", "graph_version"), ("graph_nodes", "graph_version")):
        code, _ = api_request(
            env,
            "DELETE",
            f"/rest/v1/{table}?{col}=eq.{version}",
        )
        if code not in (200, 204):
            print(f"warn: delete {table} {version} HTTP {code}")


def storage_key_for_md(md: Path) -> str:
    stem = md.stem
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_")
    if not safe:
        safe = hashlib.sha256(stem.encode()).hexdigest()[:16]
    if len(safe) > 120:
        safe = f"{safe[:80]}_{hashlib.sha256(stem.encode()).hexdigest()[:8]}"
    return f"raw/{safe}.md"


def sync_markdown(env: dict[str, str]) -> int:
    if not RAW.is_dir():
        return 0
    manifest = (
        json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {"sources": {}}
    )
    sources_meta = manifest.get("sources", {})
    rows = []
    n = 0
    for md in sorted(RAW.glob("*.md")):
        data = md.read_bytes()
        if len(data) < 500:
            continue
        sha = hashlib.sha256(data).hexdigest()
        storage_path = storage_key_for_md(md)
        upload_storage(env, storage_path, data, "text/markdown; charset=utf-8")
        meta = sources_meta.get(md.name, {})
        rows.append(
            {
                "canonical_name": md.stem,
                "storage_path": storage_path,
                "sha256": sha,
                "bytes": len(data),
                "book_family": meta.get("book_family"),
                "ingest_method": meta.get("method", "ingest"),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        n += 1
        print(f"  ↑ {md.name} ({len(data):,} bytes)")
    for i in range(0, len(rows), BATCH):
        upsert_rows(env, "corpus_sources", rows[i : i + BATCH], on_conflict="canonical_name")
    return n


def pick_graph() -> Path:
    for name in ("graph.json", "graph-core-jyotisha.json", "graph-deepseek.json"):
        p = GRAPH_OUT / name
        if p.is_file():
            return p
    raise FileNotFoundError("no graph json in graphify-out/")


def sync_graph(env: dict[str, str], *, full_replace: bool) -> tuple[int, int]:
    graph_version = _graph_version_label()
    graph_path = pick_graph()
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = graph.get("nodes", [])
    links = graph.get("links", []) or graph.get("edges", [])

    # Snapshot to storage
    snap = json.dumps(graph, indent=2).encode()
    upload_storage(env, f"graphs/{graph_version}.json", snap, "application/json")

    if full_replace:
        delete_graph_version(env, graph_version)

    node_rows = []
    for n in nodes:
        nid = n.get("id")
        if not nid:
            continue
        props = {
            k: v
            for k, v in n.items()
            if k not in ("id", "label", "file_type", "source_file", "source_location", "community")
        }
        node_rows.append(
            {
                "id": nid,
                "graph_version": graph_version,
                "label": n.get("label"),
                "file_type": n.get("file_type"),
                "source_file": n.get("source_file"),
                "source_location": n.get("source_location"),
                "community": n.get("community"),
                "properties": props,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )

    link_rows = []
    for e in links:
        src, tgt = e.get("source"), e.get("target")
        if not src or not tgt:
            continue
        props = {k: v for k, v in e.items() if k not in ("source", "target", "relation")}
        link_rows.append(
            {
                "graph_version": graph_version,
                "source_id": src,
                "target_id": tgt,
                "relation": e.get("relation"),
                "properties": props,
            }
        )

    for i in range(0, len(node_rows), BATCH):
        upsert_rows(env, "graph_nodes", node_rows[i : i + BATCH], on_conflict="id,graph_version")
        print(f"  nodes {min(i + BATCH, len(node_rows))}/{len(node_rows)}")

    for i in range(0, len(link_rows), BATCH):
        upsert_rows(
            env,
            "graph_links",
            link_rows[i : i + BATCH],
            on_conflict="graph_version,source_id,target_id,relation",
        )
        print(f"  links {min(i + BATCH, len(link_rows))}/{len(link_rows)}")

    upsert_rows(
        env,
        "graph_ingest_runs",
        [
            {
                "graph_version": graph_version,
                "provider": graph_path.name,
                "node_count": len(node_rows),
                "link_count": len(link_rows),
                "storage_path": f"graphs/{graph_version}.json",
                "completed_at": datetime.now(UTC).isoformat(),
            }
        ],
    )
    print(f"✓ graph {graph_path.name} → {len(node_rows)} nodes, {len(link_rows)} links")
    return len(node_rows), len(link_rows)


def sync_chunks(env: dict[str, str]) -> int:
    """Chunk raw markdown for vector/hybrid search. Embeddings left null for now (fill via generator)."""
    import re as _re

    raw_dir = KG / "raw"
    if not raw_dir.is_dir():
        return 0

    total = 0
    for md in sorted(raw_dir.glob("*.md")):
        if len(md.read_bytes()) < 500:
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        # simple chunking: ~800 char windows, prefer paragraph breaks
        paras = _re.split(r"\n\s*\n", text)
        chunks: list[str] = []
        buf = ""
        for p in paras:
            if len(buf) + len(p) > 800 and buf:
                chunks.append(buf.strip())
                buf = p
            else:
                buf = (buf + "\n\n" + p).strip()
        if buf:
            chunks.append(buf)

        rows = []
        for i, ch in enumerate(chunks):
            rows.append(
                {
                    "source_id": md.stem,
                    "chunk_index": i,
                    "content": ch[:4000],  # safety
                    "embedding": None,
                    "metadata": {"len": len(ch)},
                }
            )
            total += 1

        if rows:
            # delete old for this source then insert (simple)
            api_request(env, "DELETE", f"/rest/v1/corpus_chunks?source_id=eq.{md.stem}")
            for r in rows:
                api_request(env, "POST", "/rest/v1/corpus_chunks", json.dumps(r).encode())

    return total


def check_schema(env: dict[str, str]) -> bool:
    code, body = api_request(env, "GET", "/rest/v1/corpus_sources?select=canonical_name&limit=1")
    if code == 200:
        return True
    print(
        "error: corpus_sources table missing — run portal/supabase-corpus-schema.sql in Supabase SQL Editor"
    )
    print(body[:300].decode(errors="replace"))
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync corpus → Supabase vault")
    ap.add_argument("--skip-gcp", action="store_true", help="Skip gcp-sync-results.sh")
    ap.add_argument("--md-only", action="store_true")
    ap.add_argument("--graph-only", action="store_true")
    ap.add_argument("--full-graph-replace", action="store_true", default=False)
    ap.add_argument("--incremental", action="store_true", help="Skip graph delete (upsert only)")
    args = ap.parse_args()

    env = load_env()
    if not env.get("SUPABASE_URL") or not env.get("SUPABASE_SERVICE_ROLE_KEY"):
        print(
            "error: set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in portal/.env.local",
            file=sys.stderr,
        )
        return 1

    if not args.skip_gcp and not args.graph_only:
        sync_sh = ROOT / "scripts" / "gcp-sync-results.sh"
        if sync_sh.is_file():
            print("=== GCP pull ===")
            os.system(f"bash {sync_sh}")  # noqa: S605

    if not check_schema(env):
        return 1

    ensure_bucket(env)

    if not args.graph_only:
        print("=== Markdown → Storage + corpus_sources ===")
        n = sync_markdown(env)
        print(f"✓ {n} markdown files")

        print("=== Markdown chunks (vector-ready) ===")
        c = sync_chunks(env)
        print(f"✓ {c} chunks (embeddings null until generator run)")

    if not args.md_only:
        print("=== Graph → graph_nodes / graph_links ===")
        full_replace = args.full_graph_replace and not args.incremental
        sync_graph(env, full_replace=full_replace)

    print("✓ Supabase corpus sync complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
