#!/usr/bin/env python3
"""
Gemini Batch API semantic graph extraction (additive merge — never prunes).

Avoids realtime 503s from graphify extract. Uses the same prompts as graphify deep mode.

Usage:
  ./scripts/sync-gyan-to-raw.sh
  python scripts/gemini-batch-graph-extract.py prepare     # sync + deterministic base graph
  python scripts/gemini-batch-graph-extract.py submit      # upload JSONL + create batch job
  python scripts/gemini-batch-graph-extract.py status      # check job state
  python scripts/gemini-batch-graph-extract.py wait        # poll until done
  python scripts/gemini-batch-graph-extract.py merge       # additive merge into graph.json
  python scripts/gemini-batch-graph-extract.py run         # prepare → submit → wait → merge

Requires: pip install google-genai (in Panchang .venv or active env)
Env: GEMINI_API_KEY or GOOGLE_API_KEY
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
GRAPH_PATH = KG / "graphify-out" / "graph.json"
BATCH_DIR = KG / "graphify-out" / "batch"
JOB_META = BATCH_DIR / "last-job.json"
FILE_CHAR_CAP = 20_000

# graphify lives in Panchang venv
GRAPHIFY_SITE = Path(
    "/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv/lib/python3.14/site-packages"
)
if GRAPHIFY_SITE.is_dir() and str(GRAPHIFY_SITE) not in sys.path:
    sys.path.insert(0, str(GRAPHIFY_SITE))


def _api_key() -> str:
    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = os.environ.get(k, "").strip()
        if v:
            return v
    print("error: set GEMINI_API_KEY or GOOGLE_API_KEY", file=sys.stderr)
    sys.exit(1)


def _client():
    try:
        from google import genai
    except ImportError:
        print("error: pip install google-genai", file=sys.stderr)
        sys.exit(1)
    return genai.Client(api_key=_api_key())


def _corpus_paths() -> list[Path]:
    paths: list[Path] = []
    for sub in ("raw", "digests"):
        d = KG / sub
        if d.is_dir():
            paths.extend(sorted(d.glob("*.md")))
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


def _build_requests(*, deep: bool) -> list[dict]:
    from graphify.llm import _extraction_system

    system = _extraction_system(deep=deep)
    requests: list[dict] = []
    root = KG.resolve()

    for path in _corpus_paths():
        for unit in _units_for_file(path):
            key = _unit_key(unit, root)
            user_text = _build_user_message(unit, root)
            requests.append(
                {
                    "key": key,
                    "request": {
                        "system_instruction": {"parts": [{"text": system}]},
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": user_text}],
                            }
                        ],
                        "generation_config": {
                            "temperature": 0,
                            "maxOutputTokens": 16384,
                        },
                    },
                }
            )
    return requests


def merge_graph(base: dict, fragment: dict) -> dict:
    """Additive merge — same policy as gyan-corpus-extract."""
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
        link = dict(e)
        g.setdefault("links", []).append(link)
        existing_links.add(key)

    existing_he = {h.get("id") for h in g.get("hyperedges", []) if h.get("id")}
    for h in fragment.get("hyperedges", []):
        if h.get("id") and h["id"] not in existing_he:
            g.setdefault("hyperedges", []).append(h)
            existing_he.add(h["id"])

    return g


def cmd_prepare(_: argparse.Namespace) -> int:
    sync = ROOT / "scripts" / "sync-gyan-to-raw.sh"
    extract = ROOT / "scripts" / "gyan-corpus-extract.py"
    if sync.is_file():
        print("→ sync-gyan-to-raw.sh")
        subprocess.run([str(sync)], cwd=ROOT, check=True)
    print("→ gyan-corpus-extract.py --force")
    subprocess.run([sys.executable, str(extract), "--force"], cwd=ROOT, check=True)
    g = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    print(f"✓ deterministic base: {len(g.get('nodes', []))} nodes")
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    from google.genai import types

    requests = _build_requests(deep=args.deep)
    if not requests:
        print("error: no corpus .md files in knowledge-graph/raw or digests/", file=sys.stderr)
        return 1

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    jsonl_path = BATCH_DIR / f"requests-{ts}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False) + "\n")

    print(f"requests: {len(requests)} → {jsonl_path}")
    size_mb = jsonl_path.stat().st_size / (1024 * 1024)
    print(f"jsonl size: {size_mb:.2f} MB")

    client = _client()
    uploaded = client.files.upload(
        file=str(jsonl_path),
        config=types.UploadFileConfig(
            display_name=f"vedicastro-graph-{ts}",
            mime_type="jsonl",
        ),
    )
    print(f"uploaded: {uploaded.name}")

    job = client.batches.create(
        model=args.model,
        src=uploaded.name,
        config={"display_name": f"vedicastro-graph-{ts}"},
    )
    meta = {
        "job_name": job.name,
        "model": args.model,
        "deep": args.deep,
        "requests": len(requests),
        "jsonl": str(jsonl_path),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "state": getattr(job.state, "name", str(job.state)),
    }
    JOB_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"✓ batch job: {job.name}")
    print(f"  saved → {JOB_META}")
    return 0


def _load_job_meta(job_name: str | None) -> dict:
    if job_name:
        return {"job_name": job_name}
    if not JOB_META.is_file():
        print(f"error: no job metadata at {JOB_META}", file=sys.stderr)
        sys.exit(1)
    return json.loads(JOB_META.read_text(encoding="utf-8"))


def cmd_status(args: argparse.Namespace) -> int:
    meta = _load_job_meta(args.job)
    job_name = meta["job_name"]
    client = _client()
    job = client.batches.get(name=job_name)
    state = job.state.name if hasattr(job.state, "name") else str(job.state)
    print(f"job: {job_name}")
    print(f"state: {state}")
    if job.error:
        print(f"error: {job.error}")
    meta["state"] = state
    meta["last_checked"] = datetime.now(timezone.utc).isoformat()
    JOB_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    meta = _load_job_meta(args.job)
    job_name = meta["job_name"]
    client = _client()
    terminal = {
        "JOB_STATE_SUCCEEDED",
        "JOB_STATE_FAILED",
        "JOB_STATE_CANCELLED",
        "JOB_STATE_EXPIRED",
    }
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        job = client.batches.get(name=job_name)
        state = job.state.name if hasattr(job.state, "name") else str(job.state)
        print(f"[{time.strftime('%H:%M:%S')}] {state}")
        if state in terminal:
            meta["state"] = state
            JOB_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            if state == "JOB_STATE_SUCCEEDED":
                return 0
            print(f"job ended: {state}", file=sys.stderr)
            if job.error:
                print(job.error, file=sys.stderr)
            return 1
        time.sleep(args.interval)
    print(f"timeout after {args.timeout}s — run wait again later", file=sys.stderr)
    return 2


def _extract_text_from_response(resp: dict) -> str:
    if not resp:
        return ""
    # JSONL line format
    if "response" in resp and isinstance(resp["response"], dict):
        r = resp["response"]
        if "candidates" in r:
            parts = r["candidates"][0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        if "text" in r:
            return r["text"]
    if "candidates" in resp:
        parts = resp["candidates"][0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    return ""


def _parse_results_jsonl(text: str) -> list[tuple[str, dict]]:
    from graphify.llm import _parse_llm_json

    out: list[tuple[str, dict]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        key = row.get("key") or row.get("metadata", {}).get("key") or "unknown"
        if row.get("error"):
            print(f"  skip {key}: {row['error']}", file=sys.stderr)
            continue
        resp = row.get("response") or row
        text_out = _extract_text_from_response(resp if isinstance(resp, dict) else {})
        if not text_out and isinstance(resp, dict):
            # SDK inline response object
            text_out = str(resp.get("text", ""))
        frag = _parse_llm_json(text_out)
        nodes = len(frag.get("nodes", []))
        edges = len(frag.get("edges", []) or frag.get("links", []))
        print(f"  {key}: +{nodes} nodes, +{edges} edges")
        out.append((key, frag))
    return out


def cmd_merge(args: argparse.Namespace) -> int:
    meta = _load_job_meta(args.job)
    job_name = meta["job_name"]
    client = _client()
    job = client.batches.get(name=job_name)
    state = job.state.name if hasattr(job.state, "name") else str(job.state)
    if state != "JOB_STATE_SUCCEEDED":
        print(f"error: job not succeeded (state={state})", file=sys.stderr)
        return 1

    if not GRAPH_PATH.is_file():
        print(f"error: {GRAPH_PATH} missing — run prepare first", file=sys.stderr)
        return 1

    base = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    base_nodes = len(base.get("nodes", []))
    backup = GRAPH_PATH.with_suffix(".json.bak")
    backup.write_text(json.dumps(base, indent=2), encoding="utf-8")
    print(f"backup → {backup} ({base_nodes} nodes)")

    results_text = ""
    if job.dest and getattr(job.dest, "file_name", None):
        raw = client.files.download(file=job.dest.file_name)
        results_text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        out_path = BATCH_DIR / f"results-{job_name.split('/')[-1]}.jsonl"
        out_path.write_text(results_text, encoding="utf-8")
        print(f"results → {out_path}")
    elif job.dest and getattr(job.dest, "inlined_responses", None):
        lines = []
        for i, ir in enumerate(job.dest.inlined_responses):
            row = {"key": f"inline-{i}"}
            if ir.error:
                row["error"] = str(ir.error)
            elif ir.response:
                try:
                    row["response"] = {"text": ir.response.text}
                except AttributeError:
                    row["response"] = json.loads(ir.response.model_dump_json())
            lines.append(json.dumps(row))
        results_text = "\n".join(lines)
    else:
        print("error: no results in job.dest", file=sys.stderr)
        return 1

    merged = base
    ok = 0
    for key, frag in _parse_results_jsonl(results_text):
        merged = merge_graph(merged, frag)
        ok += 1

    new_nodes = len(merged.get("nodes", []))
    new_links = len(merged.get("links", []))
    print(f"merged {ok} responses: {base_nodes} → {new_nodes} nodes, {new_links} links")

    if new_nodes < base_nodes:
        print("error: merge would shrink graph — keeping backup", file=sys.stderr)
        return 1

    if args.dry_run:
        print("dry-run: not writing graph.json")
        return 0

    GRAPH_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✓ wrote {GRAPH_PATH}")

    if args.deploy:
        sync = ROOT / "scripts" / "sync-graph.sh"
        subprocess.run([str(sync), "--deploy"], cwd=ROOT, check=True)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if cmd_prepare(args) != 0:
        return 1
    if cmd_submit(args) != 0:
        return 1
    wait_rc = cmd_wait(args)
    if wait_rc == 2:
        print(f"\nJob still running. When done:\n  python {__file__} merge --deploy")
        return 0
    if wait_rc != 0:
        return wait_rc
    args.dry_run = False
    return cmd_merge(args)


def main() -> int:
    ap = argparse.ArgumentParser(description="Gemini Batch API graph extraction")
    ap.add_argument("--model", default="gemini-3.5-flash", help="Gemini model id")
    ap.add_argument("--deep", action="store_true", default=True, help="Deep mode prompts (default)")
    ap.add_argument("--no-deep", action="store_false", dest="deep")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("prepare", help="Sync Gyan + rebuild deterministic graph")

    sub.add_parser("submit", help="Build JSONL and submit batch job")

    p_status = sub.add_parser("status", help="Check batch job state")
    p_status.add_argument("--job", help="Batch job name (default: last-job.json)")

    p_wait = sub.add_parser("wait", help="Poll until job completes")
    p_wait.add_argument("--job")
    p_wait.add_argument("--interval", type=int, default=30, help="Poll interval seconds")
    p_wait.add_argument("--timeout", type=int, default=7200, help="Max wait seconds (default 2h)")

    p_merge = sub.add_parser("merge", help="Download results and merge additively")
    p_merge.add_argument("--job")
    p_merge.add_argument("--dry-run", action="store_true")
    p_merge.add_argument("--deploy", action="store_true", help="Run sync-graph.sh --deploy")

    p_run = sub.add_parser("run", help="prepare → submit → wait → merge")
    p_run.add_argument("--deploy", action="store_true")
    p_run.add_argument("--timeout", type=int, default=7200)
    p_run.add_argument("--interval", type=int, default=30)

    args = ap.parse_args()
    if args.cmd == "run":
        args.dry_run = False
        if not hasattr(args, "timeout"):
            args.timeout = 7200
        if not hasattr(args, "interval"):
            args.interval = 30

    handlers = {
        "prepare": cmd_prepare,
        "submit": cmd_submit,
        "status": cmd_status,
        "wait": cmd_wait,
        "merge": cmd_merge,
        "run": cmd_run,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
