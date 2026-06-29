#!/usr/bin/env python3
"""
Ingest loose .md ebooks from Panchang/Gyan/newbooks/ into knowledge-graph/raw/.

Skips duplicates (same work already in corpus). Writes audit log to
knowledge-graph/ingest-logs/newbooks-dedupe.json.

Usage:
  python3 scripts/ingest-newbooks-md.py              # copy + manifest only
  python3 scripts/ingest-newbooks-md.py --extract    # copy + gyan extract + gemini batch
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWBOOKS = Path("/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks")
RAW = ROOT / "knowledge-graph" / "raw"
LOG_DIR = ROOT / "knowledge-graph" / "ingest-logs"
DEDUPE_LOG = LOG_DIR / "newbooks-dedupe.json"
MANIFEST = ROOT / "knowledge-graph" / "corpus-manifest.json"

# Same classical work already represented in raw/ (different filename/edition).
WORK_DUPLICATES: dict[str, str] = {
    "maharishi_parasaras_brihad_parasara_hora_sastra_vol_i.md": "Brihat_Parasara_Hora_Sastra_Vol_1.md",
    "maharishi_parasaras_brihad_parasara_hora_sastra_vol_ii.md": "Brihat_Parasara_Hora_Sastra_Vol_2.md",
}

CONTENT_DUP_THRESHOLD = 0.92


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _content_dup(candidate: Path, existing: Path) -> bool:
    a = candidate.read_text(encoding="utf-8", errors="replace")[:12000]
    b = existing.read_text(encoding="utf-8", errors="replace")[:12000]
    return len(a) > 500 and SequenceMatcher(None, a, b).ratio() >= CONTENT_DUP_THRESHOLD


def classify(path: Path, existing_files: dict[str, Path]) -> tuple[str, str | None, str]:
    name = path.name
    if name in WORK_DUPLICATES:
        target = WORK_DUPLICATES[name]
        if target in existing_files:
            return "skip_duplicate", target, f"same work as corpus/{target}"

    for ex_name, ex_path in existing_files.items():
        if _content_dup(path, ex_path):
            return "skip_duplicate", ex_name, "content prefix ≥92% match"

    return "ingest", None, ""


def update_manifest() -> None:
    files = {}
    for p in sorted(RAW.glob("*.md")):
        data = p.read_bytes()
        files[p.name] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()[:16],
            "path": f"raw/{p.name}",
        }
    MANIFEST.write_text(
        json.dumps({"sources": files, "count": len(files)}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", action="store_true", help="Run gyan + gemini extract after copy")
    args = ap.parse_args()

    if not NEWBOOKS.is_dir():
        print(f"error: {NEWBOOKS} not found", file=sys.stderr)
        return 1

    existing = {p.name: p for p in RAW.glob("*.md")}
    incoming = sorted(NEWBOOKS.glob("*.md"))
    report: dict = {
        "updated_at": _now(),
        "source_dir": str(NEWBOOKS),
        "ingested": [],
        "skipped_duplicates": [],
    }
    to_extract: list[str] = []

    for src in incoming:
        action, dup_of, reason = classify(src, existing)
        if action == "skip_duplicate":
            print(f"SKIP duplicate: {src.name} → {dup_of} ({reason})")
            report["skipped_duplicates"].append(
                {"file": src.name, "existing": dup_of, "reason": reason}
            )
            continue
        dst = RAW / src.name
        if dst.is_file() and dst.read_bytes() == src.read_bytes():
            print(f"already in raw/: {src.name}")
        else:
            shutil.copy2(src, dst)
            print(f"→ raw/{src.name}")
        report["ingested"].append({"file": src.name, "bytes": src.stat().st_size})
        to_extract.append(src.name)
        existing[src.name] = dst

    update_manifest()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DEDUPE_LOG.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {len(existing)} sources")
    print(f"dedupe log → {DEDUPE_LOG}")

    if not args.extract:
        print(
            f"copied/verified {len(to_extract)} files ({len(report['skipped_duplicates'])} duplicates skipped)"
        )
        return 0

    if not to_extract:
        print("nothing new to extract")
        return 0

    env = {**os.environ, "INGEST_ONLY_MD": ",".join(to_extract)}
    py = sys.executable

    env_local = ROOT / "portal" / ".env.local"
    if env_local.is_file():
        for line in env_local.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    print("\n→ gyan-corpus-extract.py (deterministic)")
    subprocess.run([py, str(ROOT / "scripts" / "gyan-corpus-extract.py")], cwd=ROOT, check=True)

    gemini = ROOT / "scripts" / "gemini-batch-graph-extract.py"
    if gemini.is_file():
        print("\n→ gemini batch (semantic layer)")
        for step in ("submit", "wait", "merge"):
            subprocess.run(
                [py, str(gemini), step],
                cwd=ROOT,
                env=env,
                check=True,
            )

    print("\n→ ingest-core-jyotisha merge --promote")
    subprocess.run(
        [py, str(ROOT / "scripts" / "ingest-core-jyotisha.py"), "--promote", "merge"],
        cwd=ROOT,
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
