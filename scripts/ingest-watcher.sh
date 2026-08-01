#!/usr/bin/env bash
# ingest-watcher.sh — watch Gyan/ for new markdown, graphify → map → mutate → refresh.
#
# Pipeline when a new/changed .md file is detected under GYAN_DIR:
#   1. Run graphify extraction on the new file (or a lightweight local extractor)
#   2. Merge new nodes into knowledge-graph/graphify-out/graph.json
#   3. Run auto_mapper to find relationships
#   4. Run schema_mutator to detect new patterns
#   5. Call KnowledgeEngine.trigger_global_refresh() to re-index engines
#   6. Log everything with timestamps
#
# Usage:
#   ./scripts/ingest-watcher.sh              # foreground watch loop
#   ./scripts/ingest-watcher.sh --once       # single scan then exit
#   ./scripts/ingest-watcher.sh --file PATH  # process one file then exit
#
# Env:
#   GYAN_DIR, GRAPH_PATH, CVCE_PYTHON, POLL_SECONDS, LOG_DIR

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GYAN_DIR="${GYAN_DIR:-/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan}"
GRAPH_PATH="${GRAPH_PATH:-$ROOT/knowledge-graph/graphify-out/graph.json}"
LOG_DIR="${LOG_DIR:-$ROOT/knowledge-graph/ingest-logs}"
STATE_DIR="${MEMORY_STATE_DIR:-$ROOT/knowledge-graph/graphify-out/memory-state}"
POLL_SECONDS="${POLL_SECONDS:-30}"
CVCE_DIR="$ROOT/cvce"

# Prefer cvce venv (has fastembed + fastapi)
if [[ -n "${CVCE_PYTHON:-}" && -x "${CVCE_PYTHON}" ]]; then
  PYTHON="$CVCE_PYTHON"
elif [[ -x "$CVCE_DIR/.venv/bin/python" ]]; then
  PYTHON="$CVCE_DIR/.venv/bin/python"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

mkdir -p "$LOG_DIR" "$STATE_DIR"
LOG_FILE="$LOG_DIR/ingest-watcher.log"
SEEN_FILE="$STATE_DIR/watcher_seen.tsv"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

log "ingest-watcher start root=$ROOT gyan=$GYAN_DIR python=$PYTHON"

ONCE=0
SINGLE_FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --once) ONCE=1; shift ;;
    --file) SINGLE_FILE="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *) log "unknown arg: $1"; exit 2 ;;
  esac
done

# ── core processor (Python) ────────────────────────────────────────────────
# Invoked as: process_file <md-path>
process_file() {
  local md_path="$1"
  log "PROCESS begin: $md_path"

  GRAPH_PATH="$GRAPH_PATH" \
  MEMORY_STATE_DIR="$STATE_DIR" \
  GYAN_DIR="$GYAN_DIR" \
  PYTHONPATH="$CVCE_DIR${PYTHONPATH:+:$PYTHONPATH}" \
  "$PYTHON" - "$md_path" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

md_path = Path(sys.argv[1]).resolve()
graph_path = Path(os.environ["GRAPH_PATH"])
state_dir = Path(os.environ.get("MEMORY_STATE_DIR", graph_path.parent / "memory-state"))
state_dir.mkdir(parents=True, exist_ok=True)
batch_dir = state_dir / "batches"
batch_dir.mkdir(parents=True, exist_ok=True)

def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {msg}", flush=True)

def slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()[:60] or "node"

def extract_markdown(path: Path) -> dict:
    """Lightweight graphify-compatible extraction from a markdown file.

    Prefer `graphify` CLI when available; otherwise derive concept nodes from
    headings + bullet claims so the pipeline always makes progress offline.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = str(path)

    # Try graphify CLI if installed
    try:
        import shutil
        import subprocess
        import tempfile

        if shutil.which("graphify"):
            with tempfile.TemporaryDirectory(prefix="graphify_watch_") as td:
                td_path = Path(td)
                raw = td_path / "raw"
                raw.mkdir()
                (raw / path.name).write_text(text, encoding="utf-8")
                out = td_path / "graphify-out"
                out.mkdir()
                cmd = ["graphify", str(raw), "--no-viz", "--update"]
                # some installs write to ./graphify-out; chdir
                subprocess.run(
                    cmd,
                    cwd=str(td_path),
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                gpath = td_path / "graphify-out" / "graph.json"
                if not gpath.exists():
                    gpath = out / "graph.json"
                if gpath.exists():
                    data = json.loads(gpath.read_text(encoding="utf-8"))
                    # tag source_file
                    for n in data.get("nodes") or []:
                        n.setdefault("source_file", f"gyan/{path.name}")
                    for l in data.get("links") or []:
                        l.setdefault("source_file", f"gyan/{path.name}")
                    log(f"graphify extracted nodes={len(data.get('nodes') or [])}")
                    return data
    except Exception as exc:
        log(f"graphify CLI unavailable/failed ({exc}); using local extractor")

    # Local extractor: H1/H2/H3 → concept nodes; bullets under a heading → claims
    nodes = []
    links = []
    doc_id = f"gyan_{slug(path.stem)}"
    nodes.append(
        {
            "id": doc_id,
            "label": path.stem.replace("_", " "),
            "file_type": "document",
            "source_file": f"gyan/{path.name}",
            "source_location": "Header",
            "community": None,
            "norm_label": path.stem.replace("_", " ").lower(),
            "description": text[:400],
        }
    )

    heading_stack: list[str] = [doc_id]
    seen_ids = {doc_id}
    for i, line in enumerate(text.splitlines()):
        hm = re.match(r"^(#{1,4})\s+(.+)$", line.strip())
        if hm:
            level = len(hm.group(1))
            title = hm.group(2).strip()
            nid = f"{doc_id}_{slug(title)}"
            # uniquify
            base = nid
            n = 2
            while nid in seen_ids:
                nid = f"{base}_{n}"
                n += 1
            seen_ids.add(nid)
            nodes.append(
                {
                    "id": nid,
                    "label": title,
                    "file_type": "concept",
                    "source_file": f"gyan/{path.name}",
                    "source_location": f"L{i+1}",
                    "community": None,
                    "norm_label": title.lower(),
                    "description": title,
                }
            )
            parent = heading_stack[min(level - 1, len(heading_stack) - 1)]
            links.append(
                {
                    "source": parent,
                    "target": nid,
                    "relation": "contains_section",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "source_file": f"gyan/{path.name}",
                    "weight": 1.0,
                }
            )
            # resize stack
            heading_stack = heading_stack[:level] + [nid]
            continue

        bm = re.match(r"^[-*]\s+(.+)$", line.strip())
        if bm and heading_stack:
            claim = bm.group(1).strip()
            if len(claim) < 8:
                continue
            cid = f"{doc_id}_claim_{hashlib.sha1(claim.encode()).hexdigest()[:10]}"
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            nodes.append(
                {
                    "id": cid,
                    "label": claim[:160],
                    "file_type": "concept",
                    "source_file": f"gyan/{path.name}",
                    "source_location": f"L{i+1}",
                    "community": None,
                    "norm_label": claim[:160].lower(),
                    "description": claim,
                }
            )
            links.append(
                {
                    "source": heading_stack[-1],
                    "target": cid,
                    "relation": "states_rule",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "source_file": f"gyan/{path.name}",
                    "weight": 1.0,
                }
            )

    log(f"local extractor nodes={len(nodes)} links={len(links)}")
    return {"nodes": nodes, "links": links, "directed": False, "multigraph": False, "graph": {}}


def merge_into_graph(graph_path: Path, batch: dict) -> dict:
    if graph_path.exists():
        data = json.loads(graph_path.read_text(encoding="utf-8"))
    else:
        data = {"nodes": [], "links": [], "directed": False, "multigraph": False, "graph": {}}

    existing_ids = {n.get("id") for n in data.get("nodes") or [] if n.get("id")}
    existing_links = {
        (l.get("source"), l.get("target"), l.get("relation"))
        for l in data.get("links") or []
    }

    added_nodes = []
    for n in batch.get("nodes") or []:
        nid = n.get("id")
        if not nid or nid in existing_ids:
            continue
        data.setdefault("nodes", []).append(n)
        existing_ids.add(nid)
        added_nodes.append(n)

    added_links = []
    for l in batch.get("links") or []:
        key = (l.get("source"), l.get("target"), l.get("relation"))
        if key in existing_links:
            continue
        # only keep links whose endpoints exist after merge
        if l.get("source") in existing_ids and l.get("target") in existing_ids:
            data.setdefault("links", []).append(l)
            existing_links.add(key)
            added_links.append(l)

    # backup then write
    if graph_path.exists():
        bak = graph_path.with_suffix(graph_path.suffix + f".bak-watch-{time.strftime('%Y%m%d-%H%M%S')}")
        # keep only one rolling bak pointer lightly
        try:
            bak.write_bytes(graph_path.read_bytes())
        except Exception:
            pass
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"merged added_nodes={len(added_nodes)} added_links={len(added_links)} total_nodes={len(data['nodes'])}")
    return {"added_nodes": added_nodes, "added_links": added_links, "total_nodes": len(data["nodes"])}


def main() -> int:
    log(f"extract {md_path}")
    batch = extract_markdown(md_path)
    batch_path = batch_dir / f"{slug(md_path.stem)}_{int(time.time())}.json"
    batch_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"batch written {batch_path}")

    merge = merge_into_graph(graph_path, batch)
    new_nodes = merge["added_nodes"] or list(batch.get("nodes") or [])
    new_links = merge["added_links"] or list(batch.get("links") or [])

    # auto_mapper
    map_result = {}
    try:
        from knowledge_engine.auto_mapper import AutoMapper

        mapper = AutoMapper(graph_path=graph_path, threshold=float(os.environ.get("MAP_THRESHOLD", "0.75")))
        # Cap corpus embed on first run via env; cache makes subsequent runs fast
        max_n = os.environ.get("AUTO_MAPPER_MAX_NODES")
        mapper.load_corpus(max_nodes=int(max_n) if max_n else None)
        map_result = mapper.map_and_store(new_nodes)
        # Merge proposed links above threshold into graph
        proposed = map_result.get("proposed_links") or []
        if proposed:
            merge_into_graph(graph_path, {"nodes": [], "links": proposed})
        log(
            f"auto_mapper proposed_links={map_result.get('meta', {}).get('proposed_link_count')} "
            f"duplicates={map_result.get('meta', {}).get('duplicate_count')} "
            f"contradictions={map_result.get('meta', {}).get('contradiction_count')}"
        )
    except Exception:
        log("auto_mapper FAILED:\n" + traceback.format_exc())

    # schema_mutator
    mut_result = {}
    try:
        from knowledge_engine.schema_mutator import SchemaMutator

        mut = SchemaMutator(graph_path=graph_path)
        mut.load_corpus()
        mut_result = mut.propose_and_store(new_nodes, new_links)
        log(
            f"schema_mutator communities={len(mut_result.get('new_communities') or [])} "
            f"relations={len(mut_result.get('new_relation_types') or [])} "
            f"node_types={len(mut_result.get('new_node_types') or [])}"
        )
    except Exception:
        log("schema_mutator FAILED:\n" + traceback.format_exc())

    # KnowledgeEngine refresh
    refresh = {}
    try:
        from knowledge_engine.integration import get_knowledge_engine

        ke = get_knowledge_engine()
        refresh = ke.trigger_global_refresh(reason=f"ingest-watcher:{md_path.name}")
        log(f"trigger_global_refresh → {refresh.get('status')} engines={refresh.get('engines_notified')}")
    except Exception as exc:
        log(f"KnowledgeEngine refresh skipped/failed: {exc}")
        refresh = {"status": "skipped", "error": str(exc)}

    # memory_state ingest log
    try:
        from knowledge_engine import memory_state

        memory_state.log_ingest(
            {
                "file": str(md_path),
                "added_nodes": len(merge.get("added_nodes") or []),
                "added_links": len(merge.get("added_links") or []),
                "map_meta": map_result.get("meta"),
                "mutation_meta": mut_result.get("meta"),
                "refresh": refresh,
            }
        )
    except Exception as exc:
        log(f"memory_state log failed: {exc}")

    summary = {
        "file": str(md_path),
        "merge": {k: (len(v) if isinstance(v, list) else v) for k, v in merge.items()},
        "map_meta": map_result.get("meta"),
        "mutation_meta": mut_result.get("meta"),
        "refresh": refresh,
    }
    summary_path = state_dir / "last_ingest.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log(f"PROCESS done: {md_path.name}")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
PY
  local rc=$?
  if [[ $rc -ne 0 ]]; then
    log "PROCESS FAILED rc=$rc: $md_path"
  fi
  return $rc
}

file_fingerprint() {
  local f="$1"
  # size + mtime + inode — cheap change detector
  if stat -f "%i %m %z" "$f" >/dev/null 2>&1; then
    stat -f "%i %m %z" "$f"
  else
    stat -c "%i %Y %s" "$f"
  fi
}

load_seen() {
  declare -gA SEEN=()
  if [[ -f "$SEEN_FILE" ]]; then
    while IFS=$'\t' read -r path fp; do
      [[ -n "$path" ]] && SEEN["$path"]="$fp"
    done < "$SEEN_FILE"
  fi
}

save_seen() {
  local path="$1" fp="$2"
  # rewrite full map
  SEEN["$path"]="$fp"
  : > "$SEEN_FILE.tmp"
  for k in "${!SEEN[@]}"; do
    printf "%s\t%s\n" "$k" "${SEEN[$k]}" >> "$SEEN_FILE.tmp"
  done
  mv "$SEEN_FILE.tmp" "$SEEN_FILE"
}

scan_once() {
  load_seen
  local found=0
  # Only markdown — Gyan holds many PDFs; graphify/md path is the watcher scope
  while IFS= read -r -d '' f; do
    local fp
    fp="$(file_fingerprint "$f")"
    if [[ "${SEEN[$f]:-}" == "$fp" ]]; then
      continue
    fi
    log "change detected: $f"
    if process_file "$f"; then
      save_seen "$f" "$fp"
      found=$((found + 1))
    fi
  done < <(find "$GYAN_DIR" -type f \( -name '*.md' -o -name '*.markdown' -o -name '*.MD' \) -print0 2>/dev/null)
  log "scan complete processed=$found"
  return 0
}

if [[ -n "$SINGLE_FILE" ]]; then
  if [[ ! -f "$SINGLE_FILE" ]]; then
    log "file not found: $SINGLE_FILE"
    exit 1
  fi
  process_file "$SINGLE_FILE"
  exit $?
fi

if [[ "$ONCE" -eq 1 ]]; then
  scan_once
  exit 0
fi

log "watching $GYAN_DIR every ${POLL_SECONDS}s (ctrl-c to stop)"
# Prefer fswatch when present for low-latency; fall back to poll loop.
if command -v fswatch >/dev/null 2>&1; then
  log "using fswatch"
  # Process existing new files once at start
  scan_once || true
  fswatch -0 -e '.*' -i '\.md$' -i '\.markdown$' -i '\.MD$' "$GYAN_DIR" \
    | while IFS= read -r -d '' f; do
        [[ -f "$f" ]] || continue
        load_seen
        fp="$(file_fingerprint "$f")"
        if [[ "${SEEN[$f]:-}" == "$fp" ]]; then
          continue
        fi
        log "fswatch event: $f"
        if process_file "$f"; then
          save_seen "$f" "$fp"
        fi
      done
else
  log "fswatch not found — polling every ${POLL_SECONDS}s"
  while true; do
    scan_once || true
    sleep "$POLL_SECONDS"
  done
fi
