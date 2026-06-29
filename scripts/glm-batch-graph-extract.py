#!/usr/bin/env python3
"""
GLM 5.2 (Z.AI / 智谱) Batch API semantic graph extraction → graph-glm.json.

Additive merge on deterministic base — never touches production graph.json.

Usage:
  python3 scripts/glm-batch-graph-extract.py pilot     # test 1 chunk (realtime)
  python3 scripts/glm-batch-graph-extract.py submit    # upload JSONL + batch job
  python3 scripts/glm-batch-graph-extract.py status
  python3 scripts/glm-batch-graph-extract.py wait
  python3 scripts/glm-batch-graph-extract.py merge [--deploy]

Requires: pip install zai-sdk (in Panchang .venv)
Env: ZAI_API_KEY (or ZHIPU_API_KEY) — from https://z.ai or https://open.bigmodel.cn
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
GRAPH_GLM = KG / "graphify-out" / "graph-glm.json"
BATCH_DIR = KG / "graphify-out" / "batch-glm"
JOB_META = BATCH_DIR / "last-job.json"
FILE_CHAR_CAP = 20_000
sys.path.insert(0, str(ROOT / "scripts"))
from graph_extract_common import BASELINE_NODES  # noqa: E402

GRAPHIFY_SITE = Path(
    "/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv/lib/python3.14/site-packages"
)
if GRAPHIFY_SITE.is_dir() and str(GRAPHIFY_SITE) not in sys.path:
    sys.path.insert(0, str(GRAPHIFY_SITE))

_ENV_KEYS = ("ZAI_API_KEY", "ZHIPU_API_KEY", "GLM_API_KEY", "BIGMODEL_API_KEY")


def _load_env_local() -> dict[str, str]:
    out: dict[str, str] = {}
    env_local = ROOT / "portal" / ".env.local"
    if not env_local.is_file():
        return out
    for line in env_local.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _api_key() -> str:
    for k in _ENV_KEYS:
        v = os.environ.get(k, "").strip().strip('"').strip("'")
        if v:
            return _validate_key(v, k)
    local = _load_env_local()
    for k in _ENV_KEYS:
        v = local.get(k, "").strip()
        if v:
            return _validate_key(v, k)
    print(
        "error: set ZAI_API_KEY in portal/.env.local (from https://z.ai or open.bigmodel.cn)",
        file=sys.stderr,
    )
    sys.exit(1)


def _validate_key(v: str, name: str) -> str:
    if any(c in v for c in "\n\r\t "):
        print(f"error: {name} contains whitespace/newlines — use one line only", file=sys.stderr)
        sys.exit(1)
    if len(v) < 10:
        print(f"error: {name} looks too short", file=sys.stderr)
        sys.exit(1)
    return v


def _client(provider: str):
    try:
        from zai import ZaiClient, ZhipuAiClient
    except ImportError:
        print("error: pip install zai-sdk", file=sys.stderr)
        sys.exit(1)
    key = _api_key()
    if provider == "zhipu":
        return ZhipuAiClient(api_key=key)
    return ZaiClient(api_key=key)


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
    from graphify.file_slice import expand_oversized_files

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
        (l.get("source"), l.get("target"), l.get("relation")) for l in g.get("links", [])
    }
    for e in fragment.get("edges") or fragment.get("links") or []:
        key = (e.get("source"), e.get("target"), e.get("relation"))
        if key not in existing_links and e.get("source") and e.get("target"):
            g.setdefault("links", []).append(dict(e))
            existing_links.add(key)
    existing_he = {h.get("id") for h in g.get("hyperedges", []) if h.get("id")}
    for h in fragment.get("hyperedges", []):
        if h.get("id") and h["id"] not in existing_he:
            g.setdefault("hyperedges", []).append(h)
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
                    "url": "/v4/chat/completions",
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


def _parse_fragment(text: str) -> dict:
    from graphify.llm import _parse_llm_json

    return _parse_llm_json(text)


def _resolve_provider(args: argparse.Namespace, meta: dict | None = None) -> str:
    if getattr(args, "provider", None):
        return args.provider
    if meta and meta.get("provider"):
        return meta["provider"]
    return "zai"


def cmd_pilot(args: argparse.Namespace) -> int:
    rows = _build_jsonl_rows(deep=args.deep, model=args.model)
    if not rows:
        print("error: no corpus files", file=sys.stderr)
        return 1
    row = rows[0]
    body = row["body"]
    provider = _resolve_provider(args)
    client = _client(provider)
    print(f"pilot: {row['custom_id']} model={args.model} provider={provider}")
    resp = client.chat.completions.create(
        model=body["model"],
        messages=body["messages"],
        temperature=body.get("temperature", 0),
        max_tokens=body.get("max_tokens", 16384),
    )
    content = resp.choices[0].message.content or ""
    frag = _parse_fragment(content)
    print(f"  response chars: {len(content)}")
    print(f"  parsed: {len(frag.get('nodes', []))} nodes, "
          f"{len(frag.get('edges', []) or frag.get('links', []))} edges")
    if frag.get("nodes"):
        print(f"  sample node: {frag['nodes'][0].get('id', '?')}")
    print("✓ pilot OK — run: glm-batch-graph-extract.py submit")
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    rows = _build_jsonl_rows(deep=args.deep, model=args.model)
    if not rows:
        print("error: no corpus files", file=sys.stderr)
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

    client = _client(_resolve_provider(args))
    with jsonl_path.open("rb") as fh:
        file_object = client.files.create(file=fh, purpose="batch")
    file_id = file_object.id
    print(f"uploaded: {file_id}")

    batch = client.batches.create(
        input_file_id=file_id,
        endpoint="/v4/chat/completions",
        auto_delete_input_file=True,
        metadata={"project": "vedicastro-graph", "model": args.model},
    )
    batch_id = batch.id
    meta = {
        "batch_id": batch_id,
        "model": args.model,
        "provider": args.provider,
        "deep": args.deep,
        "requests": len(rows),
        "jsonl": str(jsonl_path),
        "input_file_id": file_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": getattr(batch, "status", "submitted"),
    }
    JOB_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"✓ batch job: {batch_id}")
    print(f"  saved → {JOB_META}")
    print("  ETA: up to ~24h — run: python3 scripts/glm-batch-graph-extract.py status")
    return 0


def _load_job_meta(batch_id: str | None) -> dict:
    if batch_id:
        return {"batch_id": batch_id}
    if not JOB_META.is_file():
        print(f"error: no job metadata at {JOB_META}", file=sys.stderr)
        sys.exit(1)
    return json.loads(JOB_META.read_text(encoding="utf-8"))


def cmd_status(args: argparse.Namespace) -> int:
    meta = _load_job_meta(args.batch)
    batch_id = meta["batch_id"]
    provider = meta.get("provider", args.provider)
    client = _client(provider)
    batch = client.batches.retrieve(batch_id)
    status = batch.status
    counts = {
        "status": status,
        "request_counts": getattr(batch, "request_counts", None),
        "output_file_id": getattr(batch, "output_file_id", None),
        "error_file_id": getattr(batch, "error_file_id", None),
    }
    print(f"batch: {batch_id}")
    print(f"state: {json.dumps(counts, default=str)}")
    meta["status"] = status
    meta["last_checked"] = datetime.now(timezone.utc).isoformat()
    JOB_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    meta = _load_job_meta(args.batch)
    batch_id = meta["batch_id"]
    provider = meta.get("provider", args.provider)
    client = _client(provider)
    terminal = {"completed", "failed", "expired", "cancelled"}
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        batch = client.batches.retrieve(batch_id)
        status = batch.status
        print(f"[{time.strftime('%H:%M:%S')}] {status}")
        meta["status"] = status
        meta["last_checked"] = datetime.now(timezone.utc).isoformat()
        JOB_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        if status in terminal:
            return 0 if status == "completed" else 1
        time.sleep(args.interval)
    print(f"timeout after {args.timeout}s", file=sys.stderr)
    return 2


def _extract_content_from_batch_line(row: dict) -> str:
    resp = row.get("response") or {}
    if row.get("error"):
        return ""
    body = resp.get("body") or {}
    choices = body.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        return msg.get("content") or ""
    return ""


def cmd_merge(args: argparse.Namespace) -> int:
    meta = _load_job_meta(args.batch)
    batch_id = meta["batch_id"]
    provider = meta.get("provider", args.provider)
    client = _client(provider)
    batch = client.batches.retrieve(batch_id)
    if batch.status != "completed":
        print(f"error: batch not completed (status={batch.status})", file=sys.stderr)
        return 1
    if not batch.output_file_id:
        print("error: no output_file_id on batch", file=sys.stderr)
        return 1

    if not GRAPH_BASE.is_file():
        print(f"error: {GRAPH_BASE} missing", file=sys.stderr)
        return 1

    out_path = BATCH_DIR / f"results-{batch_id}.jsonl"
    result_content = client.files.content(batch.output_file_id)
    result_content.write_to_file(str(out_path))
    print(f"results → {out_path}")

    base = json.loads(GRAPH_BASE.read_text(encoding="utf-8"))
    base_nodes = len(base.get("nodes", []))
    merged = base
    ok = 0
    failed = 0

    for line in out_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        key = row.get("custom_id", "unknown")
        if row.get("error") or (row.get("response") or {}).get("status_code", 200) >= 400:
            print(f"  skip {key}: error", file=sys.stderr)
            failed += 1
            continue
        text = _extract_content_from_batch_line(row)
        if not text:
            print(f"  skip {key}: empty", file=sys.stderr)
            failed += 1
            continue
        frag = _parse_fragment(text)
        nodes = len(frag.get("nodes", []))
        edges = len(frag.get("edges", []) or frag.get("links", []))
        print(f"  {key}: +{nodes} nodes, +{edges} edges")
        merged = merge_graph(merged, frag)
        ok += 1

    new_nodes = len(merged.get("nodes", []))
    new_links = len(merged.get("links", []))
    print(f"merged {ok} ok, {failed} failed: {base_nodes} → {new_nodes} nodes, {new_links} links")

    if new_nodes < base_nodes:
        print("error: merge would shrink graph", file=sys.stderr)
        return 1

    if args.dry_run:
        print("dry-run: not writing graph-glm.json")
        return 0

    GRAPH_GLM.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✓ wrote {GRAPH_GLM}")
    print(f"vs production floor ({BASELINE_NODES}): {'PASS' if new_nodes > BASELINE_NODES else 'same'}")

    if args.deploy:
        subprocess.run(
            [str(ROOT / "scripts" / "sync-graph.sh"), "--glm", "--deploy"],
            cwd=ROOT,
            check=True,
        )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="GLM 5.2 batch graph extraction")
    ap.add_argument("--model", default="glm-5.2", help="Model id (default glm-5.2)")
    ap.add_argument(
        "--provider",
        choices=("zai", "zhipu"),
        default="zai",
        help="zai=api.z.ai (intl), zhipu=open.bigmodel.cn (China)",
    )
    ap.add_argument("--deep", action="store_true", default=True)
    ap.add_argument("--no-deep", action="store_false", dest="deep")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_pilot = sub.add_parser("pilot", help="Test one chunk via realtime API")
    p_pilot.add_argument("--provider", choices=("zai", "zhipu"), default=None)

    p_submit = sub.add_parser("submit", help="Build JSONL and submit batch")
    p_submit.add_argument("--provider", choices=("zai", "zhipu"), default=None)

    p_status = sub.add_parser("status")
    p_status.add_argument("--batch")

    p_wait = sub.add_parser("wait")
    p_wait.add_argument("--batch")
    p_wait.add_argument("--interval", type=int, default=60)
    p_wait.add_argument("--timeout", type=int, default=86400)

    p_merge = sub.add_parser("merge")
    p_merge.add_argument("--batch")
    p_merge.add_argument("--dry-run", action="store_true")
    p_merge.add_argument("--deploy", action="store_true")

    args = ap.parse_args()
    handlers = {
        "pilot": cmd_pilot,
        "submit": cmd_submit,
        "status": cmd_status,
        "wait": cmd_wait,
        "merge": cmd_merge,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
