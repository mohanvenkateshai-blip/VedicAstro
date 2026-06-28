#!/usr/bin/env python3
"""
DeepSeek V4 semantic graph extraction → graph-deepseek.json (additive merge).

DeepSeek has no public batch API — uses concurrent realtime chat/completions.

Usage:
  python3 scripts/deepseek-graph-extract.py pilot
  python3 scripts/deepseek-graph-extract.py run [--max-concurrency 2] [--deploy]
  python3 scripts/deepseek-graph-extract.py merge   # rebuild from cache only

Env: DEEPSEEK_API_KEY — https://platform.deepseek.com
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KG = ROOT / "knowledge-graph"
GRAPH_BASE = KG / "graphify-out" / "graph.json"
GRAPH_OUT = KG / "graphify-out" / "graph-deepseek.json"
CACHE_DIR = KG / "graphify-out" / "cache" / "deepseek"
RUN_META = KG / "graphify-out" / "batch-deepseek" / "last-run.json"
FILE_CHAR_CAP = 20_000
BASELINE_NODES = 4253
BASE_URL = "https://api.deepseek.com"

GRAPHIFY_SITE = Path(
    "/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv/lib/python3.14/site-packages"
)
if GRAPHIFY_SITE.is_dir() and str(GRAPHIFY_SITE) not in sys.path:
    sys.path.insert(0, str(GRAPHIFY_SITE))

_ENV_KEYS = ("DEEPSEEK_API_KEY",)


def _load_env_local() -> dict[str, str]:
    out: dict[str, str] = {}
    p = ROOT / "portal" / ".env.local"
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
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
    for k, v in _load_env_local().items():
        if k in _ENV_KEYS and v.strip():
            return _validate_key(v.strip(), k)
    print("error: set DEEPSEEK_API_KEY in portal/.env.local", file=sys.stderr)
    print("  https://platform.deepseek.com/api_keys", file=sys.stderr)
    sys.exit(1)


def _validate_key(v: str, name: str) -> str:
    if any(c in v for c in "\n\r\t "):
        print(f"error: {name} has whitespace/newlines", file=sys.stderr)
        sys.exit(1)
    return v


def _openai_client():
    try:
        from openai import OpenAI
    except ImportError:
        print("error: pip install openai", file=sys.stderr)
        sys.exit(1)
    return OpenAI(api_key=_api_key(), base_url=BASE_URL)


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
        if n.get("id") and n["id"] not in existing_ids:
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


def _build_jobs(*, deep: bool, model: str) -> list[dict]:
    from graphify.llm import _extraction_system

    system = _extraction_system(deep=deep)
    jobs: list[dict] = []
    root = KG.resolve()
    for path in _corpus_paths():
        for unit in _units_for_file(path):
            key = _unit_key(unit, root)
            jobs.append(
                {
                    "key": key,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": _build_user_message(unit, root)},
                    ],
                    "model": model,
                }
            )
    return jobs


def _cache_path(key: str) -> Path:
    h = hashlib.sha256(key.encode()).hexdigest()
    return CACHE_DIR / f"{h}.json"


def _parse_fragment(text: str) -> dict:
    from graphify.llm import _parse_llm_json

    return _parse_llm_json(text)


def _call_one(client, job: dict) -> tuple[str, dict | None, str | None]:
    try:
        resp = client.chat.completions.create(
            model=job["model"],
            messages=job["messages"],
            temperature=0,
            max_tokens=16384,
            extra_body={"thinking": {"type": "disabled"}},
        )
        content = resp.choices[0].message.content or ""
        frag = _parse_fragment(content)
        return job["key"], frag, None
    except Exception as exc:
        return job["key"], None, str(exc)


def cmd_pilot(args: argparse.Namespace) -> int:
    jobs = _build_jobs(deep=args.deep, model=args.model)
    if not jobs:
        print("error: no corpus", file=sys.stderr)
        return 1
    job = jobs[0]
    client = _openai_client()
    print(f"pilot: {job['key']} model={args.model}")
    key, frag, err = _call_one(client, job)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    nodes = len(frag.get("nodes", []))
    edges = len(frag.get("edges", []) or frag.get("links", []))
    print(f"  parsed: {nodes} nodes, {edges} edges")
    if frag.get("nodes"):
        print(f"  sample: {frag['nodes'][0].get('id', '?')}")
    print("✓ pilot OK — run: deepseek-graph-extract.py run")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    jobs = _build_jobs(deep=args.deep, model=args.model)
    if not jobs:
        return 1
    if args.limit:
        jobs = jobs[: args.limit]

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RUN_META.parent.mkdir(parents=True, exist_ok=True)
    client = _openai_client()

    ok = 0
    failed = 0
    skipped = 0
    t0 = time.time()

    def work(job: dict) -> tuple[str, str]:
        cp = _cache_path(job["key"])
        if cp.is_file() and not args.force:
            return job["key"], "skip"
        key, frag, err = _call_one(client, job)
        if err:
            return key, f"fail:{err}"
        cp.write_text(json.dumps(frag, indent=2), encoding="utf-8")
        n = len(frag.get("nodes", []))
        e = len(frag.get("edges", []) or frag.get("links", []))
        print(f"  {key}: +{n} nodes, +{e} edges")
        return key, "ok"

    print(f"jobs: {len(jobs)} concurrency={args.max_concurrency}")
    with ThreadPoolExecutor(max_workers=args.max_concurrency) as pool:
        futures = {pool.submit(work, j): j for j in jobs}
        for fut in as_completed(futures):
            _key, status = fut.result()
            if status == "ok":
                ok += 1
            elif status == "skip":
                skipped += 1
            else:
                failed += 1
                print(f"  {_key}: {status}", file=sys.stderr)

    elapsed = time.time() - t0
    meta = {
        "model": args.model,
        "jobs": len(jobs),
        "ok": ok,
        "skipped": skipped,
        "failed": failed,
        "elapsed_s": round(elapsed, 1),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    RUN_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"done: {ok} ok, {skipped} cached, {failed} failed ({elapsed:.0f}s)")

    if failed and not ok and not skipped:
        return 1

    args_from_merge = argparse.Namespace(deploy=args.deploy, dry_run=False)
    return cmd_merge(args_from_merge)


def cmd_merge(args: argparse.Namespace) -> int:
    if not GRAPH_BASE.is_file():
        print(f"error: {GRAPH_BASE} missing", file=sys.stderr)
        return 1
    if not CACHE_DIR.is_dir():
        print(f"error: no cache at {CACHE_DIR}", file=sys.stderr)
        return 1

    base = json.loads(GRAPH_BASE.read_text(encoding="utf-8"))
    base_nodes = len(base.get("nodes", []))
    merged = base
    ok = 0
    for path in sorted(CACHE_DIR.glob("*.json")):
        try:
            frag = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        before = len(merged.get("nodes", []))
        merged = merge_graph(merged, frag)
        if len(merged.get("nodes", [])) > before:
            ok += 1

    new_nodes = len(merged.get("nodes", []))
    new_links = len(merged.get("links", []))
    print(f"merged {ok} cache files: {base_nodes} → {new_nodes} nodes, {new_links} links")

    if new_nodes < base_nodes:
        print("error: merge would shrink graph", file=sys.stderr)
        return 1

    if args.dry_run:
        return 0

    GRAPH_OUT.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✓ wrote {GRAPH_OUT}")
    print(f"vs baseline ({BASELINE_NODES}): {'PASS' if new_nodes > BASELINE_NODES else 'same'}")

    if args.deploy:
        subprocess.run(
            [str(ROOT / "scripts" / "sync-graph.sh"), "--deepseek", "--deploy"],
            cwd=ROOT,
            check=True,
        )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="DeepSeek V4 graph extraction")
    ap.add_argument("--model", default="deepseek-v4-flash", help="deepseek-v4-flash or deepseek-v4-pro")
    ap.add_argument("--deep", action="store_true", default=True)
    ap.add_argument("--no-deep", action="store_false", dest="deep")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("pilot")
    p_run = sub.add_parser("run")
    p_run.add_argument("--max-concurrency", type=int, default=2)
    p_run.add_argument("--limit", type=int, default=0, help="Process only first N chunks (test)")
    p_run.add_argument("--force", action="store_true", help="Re-fetch cached chunks")
    p_run.add_argument("--deploy", action="store_true")

    p_merge = sub.add_parser("merge")
    p_merge.add_argument("--dry-run", action="store_true")
    p_merge.add_argument("--deploy", action="store_true")

    args = ap.parse_args()
    handlers = {"pilot": cmd_pilot, "run": cmd_run, "merge": cmd_merge}
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
