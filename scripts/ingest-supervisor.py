#!/usr/bin/env python3
"""
Autonomous supervisor — runs CoreJyothisha ingest to completion without user input.

Phases:
  1. deepseek_text    — 6 pymupdf books (parallel with OCR)
  2. marker_ocr       — scanned PDFs → raw/*.md (restart if crashed)
  3. deepseek_ocr     — graph extract on newly OCR'd books
  4. gemini_batch     — second-pass on all CoreJyothisha md (optional if key set)
  5. merge            — graph-core-jyotisha.json + COMPLETE.md

Usage:
  python3 scripts/ingest-supervisor.py          # foreground (for nohup)
  python3 scripts/ingest-supervisor.py --status
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KG = ROOT / "knowledge-graph"
RAW = KG / "raw"
LOG_DIR = KG / "ingest-logs"
STATE_PATH = LOG_DIR / "supervisor-state.json"
COMPLETE_PATH = LOG_DIR / "COMPLETE.md"
VENV_PY = (
    Path(
        os.environ.get(
            "PANCHANG_VENV",
            "/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv",
        )
    )
    / "bin"
    / "python"
)

sys.path.insert(0, str(ROOT / "scripts"))
from core_jyotisha_titles import TEXT_BOOKS_MD, md_name_for_pdf  # noqa: E402
from graph_extract_common import (  # noqa: E402
    GRAPH_BASE,
    load_graph_version,
    merge_caches_into,
    merge_graph,
    production_node_floor,
    update_manifest,
)

GRAPH_OUT = KG / "graphify-out" / "graph-core-jyotisha.json"

SOURCE = Path("/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha")
POLL_SEC = 60


def _py() -> str:
    return str(VENV_PY) if VENV_PY.is_file() else sys.executable


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load_state() -> dict:
    if STATE_PATH.is_file():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {
        "started_at": _now(),
        "phases": {
            "deepseek_text": "pending",
            "marker_ocr": "pending",
            "deepseek_ocr": "pending",
            "gemini_batch": "pending",
            "merge": "pending",
        },
        "pids": {},
        "logs": {},
    }


def _save_state(state: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    log_file = LOG_DIR / "supervisor.log"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _pgrep(pattern: str) -> list[int]:
    r = subprocess.run(
        ["pgrep", "-f", pattern],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return []
    return [int(x) for x in r.stdout.split() if x.strip().isdigit()]


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _run_bg(name: str, cmd: list[str], env: dict | None = None) -> tuple[int, Path]:
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    log_path = LOG_DIR / f"supervisor-{name}-{ts}.log"
    full_env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    if env:
        full_env.update(env)
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        env=full_env,
        stdout=log_path.open("w"),
        stderr=subprocess.STDOUT,
    )
    _log(f"started {name} pid={proc.pid} log={log_path.name}")
    return proc.pid, log_path


def _pending_scan_mds() -> list[str]:
    pending = []
    for pdf in sorted(SOURCE.glob("*.pdf")):
        md = md_name_for_pdf(pdf)
        if md in TEXT_BOOKS_MD:
            continue
        if not (RAW / md).is_file():
            pending.append(md)
    return pending


def _all_core_mds() -> list[str]:
    names = list(TEXT_BOOKS_MD)
    for pdf in SOURCE.glob("*.pdf"):
        md = md_name_for_pdf(pdf)
        if md not in names:
            names.append(md)
    return sorted(set(names))


def _ocr_mds_ready() -> list[str]:
    return [md for md in _all_core_mds() if md not in TEXT_BOOKS_MD and (RAW / md).is_file()]


def _deepseek_running() -> bool:
    return bool(_pgrep("deepseek-graph-extract.py run"))


def _marker_running() -> bool:
    return bool(
        _pgrep("marker-ocr-queue.sh")
        or _pgrep("marker-ocr.py")
        or _pgrep("marker_single")
        or _pgrep("gcp-ocr-watch.sh")
        or _pgrep("gcp-sync-watch.sh")
    )


def _gcp_vm_status() -> str:
    gcloud = "/opt/homebrew/bin/gcloud"
    if not Path(gcloud).is_file():
        import shutil

        gcloud = shutil.which("gcloud") or "gcloud"
    r = subprocess.run(
        [
            gcloud,
            "compute",
            "instances",
            "list",
            "--filter",
            "name~'^vedicastro-ocr'",
            "--format",
            "value(status)",
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return "MISSING"
    statuses = [s.strip() for s in (r.stdout or "").splitlines() if s.strip()]
    if not statuses:
        return "MISSING"
    if any(s == "RUNNING" for s in statuses):
        return "RUNNING"
    return statuses[0]


def _gcp_ocr_preferred() -> bool:
    st = _gcp_vm_status()
    return st in ("RUNNING", "STAGING", "PROVISIONING", "REPAIRING")


def _run_gcp_watch(state: dict) -> None:
    if _pgrep("gcp-ocr-watch.sh") or _pgrep("gcp-sync-watch.sh"):
        return
    pid, log = _run_bg("gcp_sync_watch", ["bash", str(ROOT / "scripts" / "gcp-ocr-watch.sh")])
    state["pids"]["gcp_sync_watch"] = pid
    state["logs"]["gcp_sync_watch"] = str(log)


def _gcp_extract_complete() -> bool:
    return (LOG_DIR / "gcp-extract-complete.marker").is_file()


def _gcp_extract_complete_via_graph() -> bool:
    p = KG / "graphify-out" / "graph-deepseek.json"
    if not p.is_file():
        return False
    try:
        g = json.loads(p.read_text(encoding="utf-8"))
        # Text-only pass landed ~11.4k nodes; scans add more
        return len(g.get("nodes", [])) > 11_400
    except (json.JSONDecodeError, OSError):
        return False


def _run_deepseek(only_md: list[str], label: str, state: dict) -> None:
    if _deepseek_running():
        return
    pid, log = _run_bg(
        label,
        [
            _py(),
            str(ROOT / "scripts" / "deepseek-graph-extract.py"),
            "run",
            "--max-concurrency",
            "3",
        ],
        env={"INGEST_ONLY_MD": ",".join(only_md)},
    )
    state["pids"][label] = pid
    state["logs"][label] = str(log)


def _run_marker(state: dict) -> None:
    if _marker_running():
        return
    if not _pending_scan_mds():
        state["phases"]["marker_ocr"] = "done"
        return
    if _gcp_ocr_preferred():
        _log("using GCP OCR VM — starting gcp-ocr-watch (skipping local Marker)")
        _run_gcp_watch(state)
        return
    pid, log = _run_bg(
        "marker_ocr",
        ["bash", str(ROOT / "scripts" / "marker-ocr-queue.sh")],
    )
    state["pids"]["marker_ocr"] = pid
    state["logs"]["marker_ocr"] = str(log)


def _run_gemini(state: dict) -> None:
    if _pgrep("gemini-batch-graph-extract.py"):
        return
    if not env_key_ok("GEMINI_API_KEY") and not env_key_ok("GOOGLE_API_KEY"):
        _log("gemini_batch skipped — no API key")
        state["phases"]["gemini_batch"] = "skipped"
        return
    only = ",".join([m for m in _all_core_mds() if (RAW / m).is_file()])
    pid, log = _run_bg(
        "gemini_batch",
        [_py(), str(ROOT / "scripts" / "gemini-batch-graph-extract.py"), "run"],
        env={"INGEST_ONLY_MD": only},
    )
    state["pids"]["gemini_batch"] = pid
    state["logs"]["gemini_batch"] = str(log)


def env_key_ok(name: str) -> bool:
    if os.environ.get(name, "").strip():
        return True
    env_local = ROOT / "portal" / ".env.local"
    if env_local.is_file():
        for line in env_local.read_text().splitlines():
            if line.strip().startswith(f"{name}="):
                return bool(line.split("=", 1)[1].strip())
    return False


def _production_merge_stats() -> dict:
    ver = load_graph_version()
    return {
        "production_nodes": ver.get("production_nodes", production_node_floor()),
        "production_links": ver.get("production_links"),
        "graph_version": ver.get("graph_version"),
        "source": "knowledge-graph/graph-version.json",
    }


def _run_merge(state: dict) -> bool:
    if not GRAPH_BASE.is_file():
        _log("merge failed — graph.json missing")
        return False
    base = json.loads(GRAPH_BASE.read_text(encoding="utf-8"))
    base_nodes = len(base.get("nodes", []))
    merged = base
    cache_dir = KG / "graphify-out" / "cache" / "deepseek"
    merged, applied = merge_caches_into(merged, cache_dir)
    for extra in (
        "graph-deepseek.json",
        "graph-gemini.json",
        "graph-grok.json",
    ):
        p = KG / "graphify-out" / extra
        if p.is_file():
            merged = merge_graph(merged, json.loads(p.read_text(encoding="utf-8")))
    new_nodes = len(merged.get("nodes", []))
    GRAPH_OUT.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    update_manifest()
    floor = production_node_floor()
    state["merge_stats"] = {
        "prior_nodes": base_nodes,
        "merged_nodes": new_nodes,
        "links": len(merged.get("links", [])),
        "production_floor_nodes": floor,
        "delta_vs_production_floor": new_nodes - floor,
    }
    _log(f"merge done: {base_nodes} → {new_nodes} nodes → {GRAPH_OUT.name}")
    return True


def _write_complete(state: dict) -> None:
    stats = state.get("merge_stats", {})
    mds = [m for m in _all_core_mds() if (RAW / m).is_file()]
    pending = _pending_scan_mds()
    body = f"""# Core Jyotisha Ingest — COMPLETE

Finished at: {_now()}

## Summary
- **Markdown sources in raw/**: {len(mds)} / {len(_all_core_mds())}
- **Scans still pending**: {len(pending)}
- **Graph nodes**: {stats.get("prior_nodes", "?")} → **{stats.get("merged_nodes", "?")}** (+{stats.get("delta_vs_production_floor", "?")} vs production floor {stats.get("production_floor_nodes", production_node_floor())})
- **Output graph**: `{GRAPH_OUT.relative_to(ROOT)}`

## Phases
{json.dumps(state.get("phases", {}), indent=2)}

## Logs
- Supervisor: `knowledge-graph/ingest-logs/supervisor.log`
- Phase logs: `knowledge-graph/ingest-logs/supervisor-*.log`

## Next step (manual)
Review `graph-core-jyotisha.json` then optionally:
```bash
python3 scripts/ingest-core-jyotisha.py merge --promote
```
"""
    COMPLETE_PATH.write_text(body, encoding="utf-8")
    _log(f"COMPLETE → {COMPLETE_PATH}")


def _tick(state: dict) -> bool:
    """One supervisor iteration. Returns True when fully done."""
    phases = state["phases"]

    # Phase 1: DeepSeek on text books
    if phases["deepseek_text"] == "pending":
        _run_deepseek(TEXT_BOOKS_MD, "deepseek_text", state)
        phases["deepseek_text"] = "running"
    elif phases["deepseek_text"] == "running":
        if not _deepseek_running():
            phases["deepseek_text"] = "done"
            _log("deepseek_text finished")

    # Phase 2: Marker OCR (parallel with phase 1) or GCP watch
    if phases["marker_ocr"] in ("pending", "running"):
        if not _pending_scan_mds():
            phases["marker_ocr"] = "done"
            _log("marker_ocr done — all scans converted")
        elif (ROOT / "knowledge-graph" / "ingest-logs" / "gcp-ocr-complete.marker").is_file():
            phases["marker_ocr"] = "done"
            _log("marker_ocr done — gcp-ocr-complete")
        elif phases["marker_ocr"] == "pending":
            _run_marker(state)
            phases["marker_ocr"] = "running"
        elif (
            _gcp_ocr_preferred()
            and not _pgrep("gcp-ocr-watch.sh")
            and not _pgrep("gcp-sync-watch.sh")
        ):
            _log("gcp-ocr-watch not running — restarting")
            _run_gcp_watch(state)
        elif not _gcp_ocr_preferred() and not _marker_running():
            _log("marker_ocr crashed — restarting")
            _run_marker(state)

    # Phase 3: DeepSeek on OCR'd books — GCP VM extracts; Mac only syncs
    ocr_mds = _ocr_mds_ready()
    if _gcp_ocr_preferred():
        if phases["deepseek_ocr"] == "pending":
            phases["deepseek_ocr"] = "running"
            _log("deepseek_ocr on GCP — local sync via gcp-sync-watch")
        elif _gcp_extract_complete() or _gcp_extract_complete_via_graph():
            phases["deepseek_ocr"] = "done"
            _log("deepseek_ocr done — synced from GCS")
        elif phases["marker_ocr"] == "done" and not ocr_mds:
            phases["deepseek_ocr"] = "skipped"
    elif phases["deepseek_text"] == "done" and ocr_mds:
        if phases["deepseek_ocr"] == "pending":
            # Wait until marker done OR run incrementally on ready files
            ready = ocr_mds if phases["marker_ocr"] == "done" else ocr_mds
            if ready and not _deepseek_running():
                _run_deepseek(ready, "deepseek_ocr", state)
                phases["deepseek_ocr"] = "running"
        elif phases["deepseek_ocr"] == "running":
            if not _deepseek_running():
                if phases["marker_ocr"] == "done":
                    phases["deepseek_ocr"] = "done"
                    _log("deepseek_ocr finished")
                elif ocr_mds:
                    _log("deepseek_ocr batch done — more OCR books may arrive")
                    phases["deepseek_ocr"] = "pending"  # re-run for new books
    elif phases["deepseek_text"] == "done" and not ocr_mds and phases["marker_ocr"] == "done":
        phases["deepseek_ocr"] = "skipped"

    # Phase 4: Gemini batch — parallel with Marker OCR once text DeepSeek is done
    if phases["deepseek_text"] == "done" and phases["gemini_batch"] == "pending":
        _run_gemini(state)
        if phases["gemini_batch"] != "skipped":
            phases["gemini_batch"] = "running"
    elif phases["gemini_batch"] == "running":
        if not _pgrep("gemini-batch-graph-extract.py"):
            phases["gemini_batch"] = "done"
            _log("gemini_batch finished")

    # Phase 5: Merge (after OCR + all DeepSeek + Gemini)
    ds_done = phases["deepseek_text"] == "done" and phases["deepseek_ocr"] in ("done", "skipped")
    ocr_done = phases["marker_ocr"] == "done"
    gem_done = phases["gemini_batch"] in ("done", "skipped")
    if ds_done and ocr_done and gem_done and phases["merge"] == "pending":
        if _run_merge(state):
            phases["merge"] = "done"
            state["finished_at"] = _now()
            state["merge_stats"] = _production_merge_stats()
            _write_complete(state)
            return True

    if phases.get("merge") == "done" and COMPLETE_PATH.is_file():
        state["merge_stats"] = _production_merge_stats()
        return True

    return False


def cmd_status() -> int:
    state = _load_state()
    print(json.dumps(state, indent=2))
    print(f"\nPending scans: {len(_pending_scan_mds())}")
    print(f"OCR mds ready: {len(_ocr_mds_ready())}")
    print(f"DeepSeek running: {_deepseek_running()}")
    print(f"Marker running: {_marker_running()}")
    if COMPLETE_PATH.is_file():
        print(f"\n✓ COMPLETE: {COMPLETE_PATH}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--poll", type=int, default=POLL_SEC)
    args = ap.parse_args()
    if args.status:
        return cmd_status()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    state = _load_state()
    if COMPLETE_PATH.is_file() and state.get("phases", {}).get("merge") == "done":
        state["merge_stats"] = _production_merge_stats()
        _save_state(state)
        _log("ingest already complete — exiting")
        return 0
    # If text deepseek already finished, advance state so Gemini can run in parallel
    if state["phases"].get("deepseek_text") == "running" and not _deepseek_running():
        state["phases"]["deepseek_text"] = "done"
    _log("supervisor started")

    # Bootstrap: honour already-running lanes from a prior `go` launch
    if _deepseek_running():
        if state["phases"].get("deepseek_text") in ("pending", "running"):
            state["phases"]["deepseek_text"] = "running"
            _log("detected running deepseek_text")
    if _marker_running():
        state["phases"]["marker_ocr"] = "running"
        _log("detected running marker_ocr")
    elif not _pending_scan_mds():
        state["phases"]["marker_ocr"] = "done"

    while True:
        try:
            _save_state(state)
            if _tick(state):
                _save_state(state)
                _log("ALL PHASES COMPLETE")
                return 0
        except Exception as exc:
            _log(f"tick error (will retry): {exc}")
        time.sleep(args.poll)


if __name__ == "__main__":
    raise SystemExit(main())
