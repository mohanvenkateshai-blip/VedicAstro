#!/usr/bin/env python3
"""Sync canonical structured/provenance artifacts into the CVCE deploy root.

The live CVCE Vercel project has ``cvce/`` as its project root, while the
authoritative structured library and node-chapter patches live one directory
above it under ``knowledge-graph/``. Vercel cannot include files outside its
project root, so the runtime bundle needs a tracked, generated copy.

Only runtime inputs are copied:
* every structured-library JSON;
* the canonical consolidated node-chapter map;
* canonical per-book ``patch-*.json`` files (not ``.fresh`` or backups).

The source remains authoritative. This script is deliberately deterministic
so CI can refresh the bundle whenever the source artifacts change.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_STRUCTURED = REPO_ROOT / "knowledge-graph" / "structured"
SOURCE_PATCHES = REPO_ROOT / "knowledge-graph" / "patches"
BUNDLE_ROOT = REPO_ROOT / "cvce" / "knowledge-graph"


def _runtime_files() -> list[tuple[Path, Path]]:
    files: list[tuple[Path, Path]] = []
    for src in sorted(SOURCE_STRUCTURED.glob("*.json")):
        files.append((src, BUNDLE_ROOT / "structured" / src.name))

    node_map = SOURCE_PATCHES / "node-chapter-map.json"
    if node_map.is_file():
        files.append((node_map, BUNDLE_ROOT / "patches" / node_map.name))

    for src in sorted(SOURCE_PATCHES.glob("patch-*.json")):
        # .fresh files are alternate/unreviewed outputs; backups are never
        # runtime inputs. The exact .json file is the canonical patch.
        if ".fresh." in src.name or ".bak" in src.name:
            continue
        files.append((src, BUNDLE_ROOT / "patches" / src.name))
    return files


def _check(files: list[tuple[Path, Path]]) -> list[str]:
    problems: list[str] = []
    for src, dst in files:
        if not src.is_file():
            problems.append(f"missing source: {src}")
        elif not dst.is_file():
            problems.append(f"missing bundle file: {dst}")
        elif not filecmp.cmp(src, dst, shallow=False):
            problems.append(f"stale bundle file: {dst}")
    return problems


def sync(files: list[tuple[Path, Path]]) -> None:
    for src, dst in files:
        if not src.is_file():
            raise FileNotFoundError(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the tracked bundle matches canonical source files without copying",
    )
    args = parser.parse_args()

    files = _runtime_files()
    if not files:
        raise SystemExit("no provenance artifacts found")

    if args.check:
        problems = _check(files)
        if problems:
            for problem in problems:
                print(f"FAIL: {problem}")
            return 1
        print(f"PASS: {len(files)} provenance artifacts match the canonical source")
        return 0

    sync(files)
    problems = _check(files)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    print(f"SYNCED: {len(files)} provenance artifacts into {BUNDLE_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
