#!/usr/bin/env python3
"""
Ingest classical texts from Panchang/Gyan/newbooks/CoreJyothisha into the knowledge graph.

Pipeline:
  1. convert   PDF → knowledge-graph/raw/*.md (pymupdf for text PDFs; OCR for scans)
  2. manifest  refresh corpus-manifest.json
  3. extract   multi-provider parallel semantic extraction (new files only)
  4. merge     additive merge → graph-core-jyotisha.json
  5. run       convert → manifest → extract → merge

Usage:
  python3 scripts/ingest-core-jyotisha.py list
  python3 scripts/ingest-core-jyotisha.py convert [--force] [--ocr] [--max-pages N]
  python3 scripts/ingest-core-jyotisha.py extract [--providers deepseek,gemini] [--pilot]
  python3 scripts/ingest-core-jyotisha.py merge [--promote]
  python3 scripts/ingest-core-jyotisha.py run

Source: /Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha")
STATE_FILE = ROOT / "knowledge-graph" / "core-jyotisha-ingest.json"
GRAPH_OUT = ROOT / "knowledge-graph" / "graphify-out" / "graph-core-jyotisha.json"

sys.path.insert(0, str(ROOT / "scripts"))
from core_jyotisha_titles import (  # noqa: E402
    OCR_PRIORITY,
    TEXT_BOOKS_MD,
    TITLE_MAP,
    md_name_for_pdf,
)
from graph_extract_common import (  # noqa: E402
    GRAPH_BASE,
    KG,
    RAW,
    build_extraction_jobs,
    cache_path,
    env_key,
    load_graph_version,
    merge_caches_into,
    merge_graph,
    parse_fragment,
    production_node_floor,
    update_manifest,
)

CACHE_DIRS = {
    "deepseek": KG / "graphify-out" / "cache" / "deepseek",
}

PROVIDER_ORDER = ("deepseek", "gemini", "grok", "glm")


def _load_state() -> dict:
    if STATE_FILE.is_file():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"converted": {}, "extracted": {}}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(UTC).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _promoted_graph_version() -> str:
    v = os.environ.get("CORPUS_GRAPH_VERSION", "").strip()
    if v:
        return v
    return load_graph_version().get("graph_version", "core-jyotisha-v1")


def _notify_knowledge_engine_after_promote(graph_path: Path) -> None:
    cvce = ROOT / "cvce"
    if str(cvce) not in sys.path:
        sys.path.insert(0, str(cvce))
    from knowledge_engine.engine import KnowledgeEngine

    version = _promoted_graph_version()
    KnowledgeEngine().on_new_literature_ingested(graph_path, version)
    print(f"✓ KnowledgeEngine cascade ({version}) → {graph_path}")


def _md_name_for_pdf(pdf: Path) -> str:
    return md_name_for_pdf(pdf)


def classify_pdf(pdf: Path, sample_pages: int = 5, min_avg: int = 120) -> str:
    import fitz

    doc = fitz.open(pdf)
    n = min(sample_pages, len(doc))
    if n == 0:
        return "empty"
    total = sum(len(doc[i].get_text().strip()) for i in range(n))
    return "text" if total / n >= min_avg else "scan"


def convert_text_pdf(pdf: Path, out: Path, title: str) -> int:
    import fitz

    doc = fitz.open(pdf)
    parts = [f"# {title.replace('_', ' ')}\n"]
    chars = 0
    for i in range(len(doc)):
        text = doc[i].get_text().strip()
        if text:
            parts.append(f"## Page {i + 1}\n\n{text}\n")
            chars += len(text)
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return chars


def cmd_list(_args: argparse.Namespace) -> int:
    if not SOURCE.is_dir():
        print(f"error: source missing: {SOURCE}", file=sys.stderr)
        return 1
    pdfs = sorted(SOURCE.glob("*.pdf"))
    print(f"CoreJyothisha: {len(pdfs)} PDFs\n")
    print(f"{'TYPE':5} {'PAGES':>5}  {'OUT NAME':40}  SOURCE")
    print("-" * 100)
    for pdf in pdfs:
        kind = classify_pdf(pdf)
        import fitz

        pages = len(fitz.open(pdf))
        md = _md_name_for_pdf(pdf)
        exists = "✓" if (RAW / md).is_file() else " "
        print(f"{kind:5} {pages:5}  {md:40}  {exists} {pdf.name[:45]}")
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    if not SOURCE.is_dir():
        print(f"error: source missing: {SOURCE}", file=sys.stderr)
        return 1
    RAW.mkdir(parents=True, exist_ok=True)
    state = _load_state()
    converted: list[str] = []

    for pdf in sorted(SOURCE.glob("*.pdf")):
        md_name = _md_name_for_pdf(pdf)
        out = RAW / md_name
        if out.is_file() and not args.force:
            print(f"skip (exists): {md_name}")
            continue

        kind = classify_pdf(pdf)
        title = md_name[:-3]
        print(f"\n→ {pdf.name}")
        print(f"  type={kind} out={md_name}")

        if kind == "text":
            chars = convert_text_pdf(pdf, out, title)
            print(f"  pymupdf: {chars:,} chars")
        elif args.ocr:
            marker_py = ROOT / "scripts" / "marker-ocr.py"
            subprocess.run(
                [sys.executable, str(marker_py), "--pdf", str(pdf), "--out", str(out)],
                cwd=ROOT,
                check=True,
            )
        else:
            print("  scan PDF — re-run with --ocr to extract (slow)", file=sys.stderr)
            continue

        if out.is_file():
            state["converted"][md_name] = {
                "source_pdf": pdf.name,
                "method": kind if kind == "text" else "ocr",
                "bytes": out.stat().st_size,
            }
            converted.append(md_name)

    if converted:
        manifest = update_manifest()
        state["manifest_count"] = manifest["count"]
        _save_state(state)
        print(f"\n✓ converted {len(converted)} → raw/ ({manifest['count']} total)")
    else:
        print("\nno new conversions")
    return 0


def _new_md_files(state: dict) -> list[str]:
    """Files from this ingest not yet marked extracted."""
    pending = []
    for name in state.get("converted", {}):
        if name not in state.get("extracted", {}):
            pending.append(name)
    # Also pick up md files in raw that match CoreJyothisha titles but weren't in state
    known = {f"{v}.md" for v in TITLE_MAP.values()} | set(state.get("converted", {}))
    for md in known:
        if (RAW / md).is_file() and md not in state.get("extracted", {}):
            if md not in pending:
                pending.append(md)
    return sorted(pending)


def _run_deepseek(jobs: list[dict], *, model: str, concurrency: int, force: bool) -> dict:
    if not env_key("DEEPSEEK_API_KEY"):
        return {"provider": "deepseek", "status": "skipped", "reason": "no API key"}

    from openai import OpenAI

    cache_dir = CACHE_DIRS["deepseek"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=env_key("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

    ok = skipped = failed = 0

    def work(job: dict) -> str:
        cp = cache_path(cache_dir, job["key"])
        if cp.is_file() and not force:
            return "skip"
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=job["messages"],
                temperature=0,
                max_tokens=16384,
                extra_body={"thinking": {"type": "disabled"}},
            )
            content = resp.choices[0].message.content or ""
            frag = parse_fragment(content)
            cp.write_text(json.dumps(frag, indent=2), encoding="utf-8")
            return "ok"
        except Exception as exc:
            print(f"  deepseek {job['key']}: {exc}", file=sys.stderr)
            return "fail"

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futs = {pool.submit(work, j): j for j in jobs}
        for fut in as_completed(futs):
            r = fut.result()
            if r == "ok":
                ok += 1
            elif r == "skip":
                skipped += 1
            else:
                failed += 1

    return {
        "provider": "deepseek",
        "status": "done",
        "ok": ok,
        "skipped": skipped,
        "failed": failed,
    }


def _run_provider_subprocess(provider: str, only_md: list[str], pilot: bool) -> dict:
    scripts = {
        "gemini": "gemini-batch-graph-extract.py",
        "grok": "grok-batch-graph-extract.py",
        "glm": "glm-batch-graph-extract.py",
    }
    script = ROOT / "scripts" / scripts[provider]
    if not script.is_file():
        return {"provider": provider, "status": "skipped", "reason": "script missing"}

    key_map = {
        "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "grok": ("XAI_API_KEY",),
        "glm": ("ZAI_API_KEY", "ZHIPU_API_KEY", "GLM_API_KEY"),
    }
    if not any(env_key(k) for k in key_map[provider]):
        return {"provider": provider, "status": "skipped", "reason": "no API key"}

    # Batch scripts honor INGEST_ONLY_MD for incremental ingest
    env = {**dict(os.environ), "INGEST_ONLY_MD": ",".join(only_md)}
    cmd = [sys.executable, str(script), "pilot" if pilot else "run"]
    if pilot:
        # pilot doesn't need file filter
        cmd = [sys.executable, str(script), "pilot"]
    try:
        subprocess.run(cmd, cwd=ROOT, env=env, check=True, timeout=7200)
        return {"provider": provider, "status": "done"}
    except subprocess.TimeoutExpired:
        return {"provider": provider, "status": "timeout"}
    except subprocess.CalledProcessError as exc:
        return {"provider": provider, "status": "failed", "code": exc.returncode}


def cmd_extract(args: argparse.Namespace) -> int:
    state = _load_state()
    only_md = _new_md_files(state)
    if args.only:
        only_md = [n if n.endswith(".md") else f"{n}.md" for n in args.only]
    if not only_md:
        print("nothing pending — run convert first or all files already extracted")
        return 0

    jobs = build_extraction_jobs(only_md=only_md, deep=True)
    if not jobs:
        print("error: no extraction jobs", file=sys.stderr)
        return 1

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    providers = sorted(
        providers, key=lambda p: PROVIDER_ORDER.index(p) if p in PROVIDER_ORDER else 99
    )

    print(f"extract: {len(only_md)} files → {len(jobs)} chunks")
    print(f"providers (priority): {', '.join(providers)}")

    if args.pilot:
        providers = providers[:1]
        jobs = jobs[:1]
        print("pilot: 1 chunk, 1 provider")

    results: list[dict] = []
    t0 = time.time()

    if args.parallel and len(providers) > 1:
        with ThreadPoolExecutor(max_workers=len(providers)) as pool:
            futs = {}
            for p in providers:
                if p == "deepseek":
                    futs[
                        pool.submit(
                            _run_deepseek,
                            jobs,
                            model=args.deepseek_model,
                            concurrency=args.concurrency,
                            force=args.force,
                        )
                    ] = p
                else:
                    futs[pool.submit(_run_provider_subprocess, p, only_md, args.pilot)] = p
            for fut in as_completed(futs):
                results.append(fut.result())
    else:
        for p in providers:
            print(f"\n--- {p} ---")
            if p == "deepseek":
                r = _run_deepseek(
                    jobs,
                    model=args.deepseek_model,
                    concurrency=args.concurrency,
                    force=args.force,
                )
            else:
                r = _run_provider_subprocess(p, only_md, args.pilot)
            results.append(r)
            print(f"  {r}")

    for md in only_md:
        state.setdefault("extracted", {})[md] = {
            "at": datetime.now(UTC).isoformat(),
            "providers": providers,
        }
    _save_state(state)

    elapsed = time.time() - t0
    print(f"\ndone in {elapsed:.0f}s: {results}")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    if not GRAPH_BASE.is_file():
        print(f"error: production graph missing: {GRAPH_BASE}", file=sys.stderr)
        return 1

    base = json.loads(GRAPH_BASE.read_text(encoding="utf-8"))
    base_nodes = len(base.get("nodes", []))
    merged = base
    report: dict[str, dict] = {}

    for name, cache_dir in CACHE_DIRS.items():
        before = len(merged.get("nodes", []))
        merged, applied = merge_caches_into(merged, cache_dir)
        after = len(merged.get("nodes", []))
        report[name] = {"cache_files": applied, "nodes_added": after - before}

    # Also fold in provider-specific merged graphs if present
    for extra in (
        "graph-deepseek.json",
        "graph-gemini.json",
        "graph-grok.json",
        "graph-glm.json",
    ):
        p = KG / "graphify-out" / extra
        if p.is_file():
            frag = json.loads(p.read_text(encoding="utf-8"))
            before = len(merged.get("nodes", []))
            merged = merge_graph(merged, frag)
            report[extra] = {"nodes_added": len(merged.get("nodes", [])) - before}

    new_nodes = len(merged.get("nodes", []))
    new_links = len(merged.get("links", []))
    print(f"merge: {base_nodes} → {new_nodes} nodes, {new_links} links")
    for k, v in report.items():
        if v.get("nodes_added", 0) or v.get("cache_files", 0):
            print(f"  {k}: {v}")

    if new_nodes < base_nodes:
        print("error: merge would shrink graph", file=sys.stderr)
        return 1

    GRAPH_OUT.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✓ wrote {GRAPH_OUT}")
    floor = production_node_floor()
    print(f"vs production floor ({floor}): {'PASS' if new_nodes > floor else 'same'}")

    if args.promote:
        promoted = GRAPH_BASE.with_suffix(".json.bak-pre-core-jyotisha")
        if not promoted.is_file():
            GRAPH_BASE.rename(promoted)
            print(f"backup: {promoted}")
        GRAPH_OUT.replace(GRAPH_BASE)
        print(f"✓ promoted → {GRAPH_BASE}")
        _notify_knowledge_engine_after_promote(GRAPH_BASE)

    return 0


def cmd_go(args: argparse.Namespace) -> int:
    """Launch parallel lanes: DeepSeek extraction + Marker OCR queue."""
    LOG_DIR = KG / "ingest-logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

    venv_py = (
        Path(
            os.environ.get(
                "PANCHANG_VENV",
                "/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv",
            )
        )
        / "bin"
        / "python"
    )
    py = str(venv_py) if venv_py.is_file() else sys.executable

    only_md = ",".join(TEXT_BOOKS_MD)
    procs: list[tuple[str, subprocess.Popen, Path]] = []

    # Lane A — DeepSeek on 6 text books (network-bound)
    ds_log = LOG_DIR / f"lane-a-deepseek-{ts}.log"
    ds_env = {**os.environ, "INGEST_ONLY_MD": only_md, "PYTHONUNBUFFERED": "1"}
    ds_cmd = [
        py,
        str(ROOT / "scripts" / "deepseek-graph-extract.py"),
        "run",
        "--max-concurrency",
        str(args.concurrency),
    ]
    print(f"Lane A: DeepSeek → {len(TEXT_BOOKS_MD)} books, log={ds_log.name}")
    procs.append(
        (
            "deepseek",
            subprocess.Popen(
                ds_cmd,
                cwd=ROOT,
                env=ds_env,
                stdout=ds_log.open("w"),
                stderr=subprocess.STDOUT,
            ),
            ds_log,
        )
    )

    # Lane B — Marker OCR: priority queue then remaining scans (GPU-bound, sequential PDFs)
    ocr_log = LOG_DIR / f"lane-b-marker-{ts}.log"
    ocr_script = ROOT / "scripts" / "marker-ocr-queue.sh"
    ocr_cmd = ["bash", str(ocr_script)]
    if args.force:
        ocr_cmd.append("--force")
    ocr_env = {**os.environ.copy(), "PYTHONUNBUFFERED": "1"}
    print(f"Lane B: Marker OCR queue, log={ocr_log.name}")
    procs.append(
        (
            "marker",
            subprocess.Popen(
                ocr_cmd,
                cwd=ROOT,
                env=ocr_env,
                stdout=ocr_log.open("w"),
                stderr=subprocess.STDOUT,
            ),
            ocr_log,
        )
    )

    meta = {
        "started_at": datetime.now(UTC).isoformat(),
        "lanes": [{"name": n, "pid": p.pid, "log": str(log)} for n, p, log in procs],
        "text_books": TEXT_BOOKS_MD,
        "ocr_priority": OCR_PRIORITY,
    }
    meta_path = LOG_DIR / f"parallel-go-{ts}.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"\n✓ Parallel ingest started — meta: {meta_path}")
    for name, proc, log in procs:
        print(f"  {name}: pid={proc.pid}  tail -f {log}")

    if args.wait:
        print("\nwaiting for lanes to finish...")
        rc = 0
        for name, proc, _log in procs:
            code = proc.wait()
            print(f"  {name}: exit {code}")
            if code != 0:
                rc = code
        print("\nRunning merge...")
        return cmd_merge(args) if rc == 0 else rc

    print("\nMonitor:  tail -f knowledge-graph/ingest-logs/lane-*.log")
    print("When done: python3 scripts/ingest-core-jyotisha.py merge")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    steps = [
        ("convert", cmd_convert),
        ("extract", cmd_extract),
        ("merge", cmd_merge),
    ]
    for name, fn in steps:
        print(f"\n{'=' * 60}\nSTEP: {name}\n{'=' * 60}")
        rc = fn(args)
        if rc != 0:
            return rc
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest CoreJyothisha classical corpus")
    ap.add_argument("--force", action="store_true", help="Re-convert / re-extract cached chunks")
    ap.add_argument("--ocr", action="store_true", help="OCR scanned PDFs (slow)")
    ap.add_argument("--max-pages", type=int, default=0, help="Limit OCR pages (test)")
    ap.add_argument(
        "--providers",
        default="deepseek,gemini,grok,glm",
        help="Comma-separated providers in priority order",
    )
    ap.add_argument("--deepseek-model", default="deepseek-v4-flash")
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--parallel", action="store_true", default=True)
    ap.add_argument("--no-parallel", action="store_false", dest="parallel")
    ap.add_argument("--pilot", action="store_true", help="One chunk, one provider")
    ap.add_argument("--only", nargs="*", help="Limit to specific .md basenames")
    ap.add_argument("--wait", action="store_true", help="Wait for lanes then merge")
    ap.add_argument("--promote", action="store_true", help="Replace graph.json with merged output")

    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="Classify PDFs and show output names")
    sub.add_parser("convert", help="PDF → raw/*.md")
    sub.add_parser("manifest", help="Refresh corpus-manifest.json")
    sub.add_parser("extract", help="Multi-provider graph extraction")
    sub.add_parser("merge", help="Merge caches → graph-core-jyotisha.json")
    sub.add_parser("run", help="convert → extract → merge")
    sub.add_parser("go", help="Parallel: DeepSeek + Marker OCR lanes")

    args = ap.parse_args()
    if args.cmd == "manifest":
        doc = update_manifest()
        print(f"manifest: {doc['count']} sources")
        return 0
    handlers = {
        "list": cmd_list,
        "convert": cmd_convert,
        "extract": cmd_extract,
        "merge": cmd_merge,
        "run": cmd_run,
        "go": cmd_go,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
