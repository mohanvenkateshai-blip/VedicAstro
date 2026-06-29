#!/usr/bin/env python3
"""
Grok (xAI) Batch API semantic graph extraction — additive merge into graph-grok.json.

Mirrors gemini-batch-graph-extract.py; never prunes production graph.json.

Usage:
  python3 scripts/grok-batch-graph-extract.py submit      # upload JSONL + create batch
  python3 scripts/grok-batch-graph-extract.py status     # check job state
  python3 scripts/grok-batch-graph-extract.py wait       # poll until done (~24h SLO)
  python3 scripts/grok-batch-graph-extract.py merge        # merge into graph-grok.json
  python3 scripts/grok-batch-graph-extract.py run          # submit only (merge when wait completes)

Requires: pip install xai-sdk
Env: XAI_API_KEY
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KG = ROOT / "knowledge-graph"
GRAPH_BASE = KG / "graphify-out" / "graph.json"
GRAPH_GROK = KG / "graphify-out" / "graph-grok.json"
BATCH_DIR = KG / "graphify-out" / "batch-grok"
JOB_META = BATCH_DIR / "last-job.json"
FILE_CHAR_CAP = 20_000
sys.path.insert(0, str(ROOT / "scripts"))
from graph_extract_common import BASELINE_NODES  # noqa: E402

GRAPHIFY_SITE = Path(
    "/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv/lib/python3.14/site-packages"
)
if GRAPHIFY_SITE.is_dir() and str(GRAPHIFY_SITE) not in sys.path:
    sys.path.insert(0, str(GRAPHIFY_SITE))


def _api_key() -> str:
    v = os.environ.get("XAI_API_KEY", "").strip().strip('"').strip("'")
    if not v:
        # Optional: portal/.env.local (gitignored)
        env_local = ROOT / "portal" / ".env.local"
        if env_local.is_file():
            for line in env_local.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("XAI_API_KEY="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not v:
        print("error: set XAI_API_KEY (one line, no spaces/newlines)", file=sys.stderr)
        print("  export XAI_API_KEY='xai-...'  # from https://console.x.ai", file=sys.stderr)
        sys.exit(1)
    if any(c in v for c in "\n\r\t "):
        print(
            "error: XAI_API_KEY contains whitespace or newlines — "
            "paste only the key from console.x.ai on a single line",
            file=sys.stderr,
        )
        sys.exit(1)
    if len(v) < 20:
        print("error: XAI_API_KEY looks too short", file=sys.stderr)
        sys.exit(1)
    return v


def _client():
    try:
        from xai_sdk import Client
    except ImportError:
        print("error: pip install xai-sdk", file=sys.stderr)
        sys.exit(1)
    return Client(api_key=_api_key())


def _corpus_paths() -> list[Path]:
    only = os.environ.get("INGEST_ONLY_MD", "").strip()
    only_md = [x.strip() for x in only.split(",") if x.strip()] or None
    paths: list[Path] = []
    for sub in ("raw", "digests"):
        d = KG / sub
        if d.is_dir():
            paths.extend(sorted(d.glob("*.md")))
    if only_md:
        allow = {n if n.endswith(".md") else f"{n}.md" for n in only_md}
        paths = [p for p in paths if p.name in allow]
    return paths


def _units_for_file(path: Path) -> list:
    from graphify.file_slice import FileSlice, expand_oversized_files

    return expand_oversized_files([path], FILE_CHAR_CAP)


def _unit_key(unit, root: Path) -> str:
    from graphify.file_slice import FileSlice, unit_path

    p = unit_path(unit)
    try:
        rel = p.relative_to(root)
    except ValueError:
        rel = p
    key = str(rel).replace("\\", "/")
    if isinstance(unit, FileSlice):
        key = f"{key}#slice{unit.index}"
    return key


def _build_user_message(unit, root: Path) -> str:
    from graphify.llm import _read_files

    return _read_files([unit], root)


def merge_graph(base: dict, fragment: dict) -> dict:
    g = json.loads(json.dumps(base))
    existing_ids = {n["id"] for n in g.get("nodes", []) if n.get("id")}

    for n in fragment.get("nodes", []):
        if not n.get("id") or n["id"] in existing_ids:
            continue
        g.setdefault("nodes", []).append(n)
        existing_ids.add(n["id"])

    existing_links = {
        (l.get("source"), l.get("target"), l.get("relation"))
        for l in g.get("links", [])
    }
    edges = fragment.get("edges") or fragment.get("links") or []
    for e in edges:
        key = (e.get("source"), e.get("target"), e.get("relation"))
        if key in existing_links or not e.get("source") or not e.get("target"):
            continue
        g.setdefault("links", []).append(dict(e))
        existing_links.add(key)

    existing_he = {h.get("id") for h in g.get("hyperedges", []) if h.get("id")}
    for h in fragment.get("hyperedges", []):
        if h.get("id") and h["id"] not in existing_he:
            g.setdefault("hyperedges", []).append(h)
            existing_he.add(h["id"])

    return g


def _build_jsonl_rows(*, deep: bool, model: str) -> list[dict]:
    from graphify.llm import _extraction_system

    system = _extraction_system(deep=deep)
    rows: list[dict] = []
    root = KG.resolve()

    for path in _corpus_paths():
        for unit in _units_for_file(path):
            key = _unit_key(unit, root)
            user_text = _build_user_message(unit, root)
            rows.append(
                {
                    "custom_id": key,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": model,
                        "temperature": 0,
                        "max_tokens": 16384,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user_text},
                        ],
                    },
                }
            )
    return rows


def cmd_submit(args: argparse.Namespace) -> int:
    rows = _build_jsonl_rows(deep=args.deep, model=args.model)
    if not rows:
        print("error: no corpus .md files in knowledge-graph/raw or digests/", file=sys.stderr)
        return 1

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    jsonl_path = BATCH_DIR / f"requests-{ts}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    size_mb = jsonl_path.stat().st_size / (1024 * 1024)
    print(f"requests: {len(rows)} → {jsonl_path}")
    print(f"jsonl size: {size_mb:.2f} MB")

    api_key = _api_key()
    use_rest = getattr(args, "rest", False)
    if use_rest:
        return _submit_via_rest(api_key, jsonl_path, rows, args, ts)

    client = _client()
    with jsonl_path.open("rb") as fh:
        uploaded = client.files.upload(file=fh)
    file_id = getattr(uploaded, "id", None) or getattr(uploaded, "file_id", None)
    if not file_id:
        print(f"error: unexpected upload response: {uploaded}", file=sys.stderr)
        return 1
    print(f"uploaded: {file_id}")

    batch = client.batch.create(
        batch_name=f"vedicastro-graph-grok-{ts}",
        input_file_id=file_id,
    )
    batch_id = batch.batch_id
    meta = {
        "batch_id": batch_id,
        "model": args.model,
        "deep": args.deep,
        "requests": len(rows),
        "jsonl": str(jsonl_path),
        "input_file_id": file_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "state": str(getattr(batch, "state", "submitted")),
    }
    JOB_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"✓ batch job: {batch_id}")
    print(f"  saved → {JOB_META}")
    print("  SLO: ~24h — run: python3 scripts/grok-batch-graph-extract.py status")
    return 0


def _submit_via_rest(
    api_key: str,
    jsonl_path: Path,
    rows: list[dict],
    args: argparse.Namespace,
    ts: str,
) -> int:
    """HTTPS file upload + batch create (avoids gRPC metadata issues)."""
    import urllib.error
    import urllib.request

    print("→ REST upload (HTTPS)")

    boundary = "----vedicastro-batch"
    body_parts: list[bytes] = []
    file_bytes = jsonl_path.read_bytes()
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{jsonl_path.name}"\r\n'.encode()
    )
    body_parts.append(b"Content-Type: application/jsonl\r\n\r\n")
    body_parts.append(file_bytes)
    body_parts.append(f"\r\n--{boundary}--\r\n".encode())
    payload = b"".join(body_parts)

    req = urllib.request.Request(
        "https://api.x.ai/v1/files",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            file_resp = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        err = exc.read().decode(errors="replace")
        print(f"error: file upload HTTP {exc.code}: {err}", file=sys.stderr)
        return 1

    file_id = file_resp.get("id") or file_resp.get("file_id")
    if not file_id:
        print(f"error: unexpected upload response: {file_resp}", file=sys.stderr)
        return 1
    print(f"uploaded: {file_id}")

    batch_body = json.dumps(
        {"name": f"vedicastro-graph-grok-{ts}", "input_file_id": file_id}
    ).encode()
    batch_req = urllib.request.Request(
        "https://api.x.ai/v1/batches",
        data=batch_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(batch_req, timeout=60) as resp:
            batch_resp = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        err = exc.read().decode(errors="replace")
        print(f"error: batch create HTTP {exc.code}: {err}", file=sys.stderr)
        return 1

    batch_id = batch_resp.get("batch_id") or batch_resp.get("id")
    if not batch_id:
        print(f"error: unexpected batch response: {batch_resp}", file=sys.stderr)
        return 1

    meta = {
        "batch_id": batch_id,
        "model": args.model,
        "deep": args.deep,
        "requests": len(rows),
        "jsonl": str(jsonl_path),
        "input_file_id": file_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "transport": "rest",
    }
    JOB_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"✓ batch job: {batch_id}")
    print(f"  saved → {JOB_META}")
    print("  SLO: ~24h — run: python3 scripts/grok-batch-graph-extract.py status")
    return 0


def _load_job_meta(batch_id: str | None) -> dict:
    if batch_id:
        return {"batch_id": batch_id}
    if not JOB_META.is_file():
        print(f"error: no job metadata at {JOB_META}", file=sys.stderr)
        sys.exit(1)
    return json.loads(JOB_META.read_text(encoding="utf-8"))


def _batch_state(batch) -> dict:
    st = batch.state
    return {
        "num_requests": getattr(st, "num_requests", 0),
        "num_pending": getattr(st, "num_pending", 0),
        "num_success": getattr(st, "num_success", 0),
        "num_error": getattr(st, "num_error", 0),
    }


def cmd_status(args: argparse.Namespace) -> int:
    meta = _load_job_meta(args.batch)
    batch_id = meta["batch_id"]
    client = _client()
    batch = client.batch.get(batch_id=batch_id)
    counts = _batch_state(batch)
    print(f"batch: {batch_id}")
    print(f"state: {counts}")
    meta["state"] = counts
    meta["last_checked"] = datetime.now(timezone.utc).isoformat()
    JOB_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    meta = _load_job_meta(args.batch)
    batch_id = meta["batch_id"]
    client = _client()
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        batch = client.batch.get(batch_id=batch_id)
        counts = _batch_state(batch)
        done = counts["num_success"] + counts["num_error"]
        total = counts["num_requests"]
        print(
            f"[{time.strftime('%H:%M:%S')}] {done}/{total} done, "
            f"pending={counts['num_pending']} ok={counts['num_success']} err={counts['num_error']}"
        )
        meta["state"] = counts
        meta["last_checked"] = datetime.now(timezone.utc).isoformat()
        JOB_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        if total > 0 and counts["num_pending"] == 0:
            return 0
        time.sleep(args.interval)
    print(f"timeout after {args.timeout}s — run wait again later", file=sys.stderr)
    return 2


def _parse_fragment(text: str) -> dict:
    from graphify.llm import _parse_llm_json

    return _parse_llm_json(text)


def cmd_merge(args: argparse.Namespace) -> int:
    meta = _load_job_meta(args.batch)
    batch_id = meta["batch_id"]
    client = _client()
    batch = client.batch.get(batch_id=batch_id)
    counts = _batch_state(batch)
    if counts["num_requests"] == 0 or counts["num_pending"] > 0:
        print(
            f"error: batch not complete (pending={counts['num_pending']})",
            file=sys.stderr,
        )
        return 1

    if not GRAPH_BASE.is_file():
        print(f"error: {GRAPH_BASE} missing", file=sys.stderr)
        return 1

    base = json.loads(GRAPH_BASE.read_text(encoding="utf-8"))
    base_nodes = len(base.get("nodes", []))
    merged = base
    ok = 0
    failed = 0
    pagination_token = None

    while True:
        page = client.batch.list_batch_results(
            batch_id=batch_id,
            limit=100,
            pagination_token=pagination_token,
        )
        for result in page.succeeded:
            key = result.batch_request_id
            content = ""
            if result.response:
                content = getattr(result.response, "content", "") or ""
            if not content:
                print(f"  skip {key}: empty response", file=sys.stderr)
                failed += 1
                continue
            frag = _parse_fragment(content)
            nodes = len(frag.get("nodes", []))
            edges = len(frag.get("edges", []) or frag.get("links", []))
            print(f"  {key}: +{nodes} nodes, +{edges} edges")
            merged = merge_graph(merged, frag)
            ok += 1

        for result in page.failed:
            print(f"  fail {result.batch_request_id}: {result.error_message}", file=sys.stderr)
            failed += 1

        pagination_token = getattr(page, "pagination_token", None)
        if not pagination_token:
            break

    new_nodes = len(merged.get("nodes", []))
    new_links = len(merged.get("links", []))
    print(f"merged {ok} ok, {failed} failed: {base_nodes} → {new_nodes} nodes, {new_links} links")

    if new_nodes < base_nodes:
        print("error: merge would shrink graph", file=sys.stderr)
        return 1

    if args.dry_run:
        print("dry-run: not writing graph-grok.json")
        return 0

    GRAPH_GROK.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✓ wrote {GRAPH_GROK}")
    print(
        f"vs production floor ({BASELINE_NODES}): "
        f"{'PASS' if new_nodes > BASELINE_NODES else 'same as base'}"
    )

    if args.deploy:
        sync = ROOT / "scripts" / "sync-graph.sh"
        subprocess.run([str(sync), "--grok", "--deploy"], cwd=ROOT, check=True)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if cmd_submit(args) != 0:
        return 1
    print("\nBatch submitted. When complete (~24h):")
    print(f"  python3 {Path(__file__).name} wait")
    print(f"  python3 {Path(__file__).name} merge --deploy")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Grok Batch API graph extraction")
    ap.add_argument("--model", default="grok-4.3", help="xAI model id")
    ap.add_argument("--deep", action="store_true", default=True)
    ap.add_argument("--no-deep", action="store_false", dest="deep")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_submit = sub.add_parser("submit", help="Build JSONL and submit batch job")
    p_submit.add_argument(
        "--rest",
        action="store_true",
        help="Use HTTPS REST for upload (if gRPC fails with Illegal metadata)",
    )

    p_status = sub.add_parser("status", help="Check batch job state")
    p_status.add_argument("--batch", help="Batch id (default: last-job.json)")

    p_wait = sub.add_parser("wait", help="Poll until job completes")
    p_wait.add_argument("--batch")
    p_wait.add_argument("--interval", type=int, default=60)
    p_wait.add_argument("--timeout", type=int, default=86400, help="Max wait seconds (default 24h)")

    p_merge = sub.add_parser("merge", help="Download results into graph-grok.json")
    p_merge.add_argument("--batch")
    p_merge.add_argument("--dry-run", action="store_true")
    p_merge.add_argument("--deploy", action="store_true")

    p_run = sub.add_parser("run", help="submit batch (merge manually after wait)")

    args = ap.parse_args()
    handlers = {
        "submit": cmd_submit,
        "status": cmd_status,
        "wait": cmd_wait,
        "merge": cmd_merge,
        "run": cmd_run,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
