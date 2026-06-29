#!/usr/bin/env python3
"""
Convert scanned PDFs to markdown via Marker+Surya (local, free).

Usage:
  python3 scripts/marker-ocr.py --pdf book.pdf --out knowledge-graph/raw/Book.md
  python3 scripts/marker-ocr.py --queue 2015.312156.Jataka-Parijata.pdf saravaliofkalyan01kalyuoft.pdf

Requires: pip install marker-pdf (in Panchang .venv)
Env: TORCH_DEVICE=mps (default on Apple Silicon)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha")
RAW = ROOT / "knowledge-graph" / "raw"
LOG_DIR = ROOT / "knowledge-graph" / "ingest-logs"
MARKER_WORK = ROOT / "knowledge-graph" / "marker-work"

sys.path.insert(0, str(ROOT / "scripts"))
from core_jyotisha_titles import md_name_for_pdf  # noqa: E402


def _venv_bin(name: str) -> str:
    venv = Path(
        os.environ.get(
            "PANCHANG_VENV",
            "/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv",
        )
    )
    p = venv / "bin" / name
    return str(p) if p.is_file() else name


def _marker_env() -> dict[str, str]:
    env = dict(os.environ)
    if "TORCH_DEVICE" not in env:
        try:
            import torch

            if torch.backends.mps.is_available():
                env["TORCH_DEVICE"] = "mps"
            elif torch.cuda.is_available():
                env["TORCH_DEVICE"] = "cuda"
            else:
                env["TORCH_DEVICE"] = "cpu"
        except ImportError:
            env["TORCH_DEVICE"] = "cpu"
    env.setdefault("GRPC_VERBOSITY", "ERROR")
    env.setdefault("TRANSFORMERS_VERBOSITY", "error")
    return env


def convert_one(pdf: Path, out_md: Path, *, force: bool) -> bool:
    if out_md.is_file() and not force:
        print(f"skip (exists): {out_md.name}")
        return True
    if not pdf.is_file():
        print(f"error: missing {pdf}", file=sys.stderr)
        return False

    MARKER_WORK.mkdir(parents=True, exist_ok=True)
    out_dir = MARKER_WORK / pdf.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    marker = _venv_bin("marker_single")
    cmd = [
        marker,
        str(pdf),
        "--output_dir",
        str(out_dir),
        "--output_format",
        "markdown",
    ]
    print(f"marker: {pdf.name} → {out_md.name} (device={_marker_env().get('TORCH_DEVICE')})")
    t0 = time.time()
    try:
        subprocess.run(cmd, check=True, env=_marker_env(), cwd=ROOT)
    except subprocess.CalledProcessError as exc:
        print(f"marker failed ({exc.returncode}): {pdf.name}", file=sys.stderr)
        return False

    # marker writes <stem>.md or nested output
    candidates = list(out_dir.rglob("*.md"))
    if not candidates:
        print(f"error: no markdown output in {out_dir}", file=sys.stderr)
        return False
    src = max(candidates, key=lambda p: p.stat().st_size)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, out_md)
    elapsed = time.time() - t0
    print(f"✓ {out_md.name} ({out_md.stat().st_size:,} bytes, {elapsed:.0f}s)")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Marker+Surya PDF → markdown")
    ap.add_argument("--pdf", type=Path, help="Single PDF path")
    ap.add_argument("--out", type=Path, help="Output .md path")
    ap.add_argument("--queue", nargs="+", metavar="PDF", help="PDF filenames under SOURCE")
    ap.add_argument("--all-scans", action="store_true", help="Queue all scan PDFs not yet in raw/")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.pdf:
        out = args.out or RAW / f"{args.pdf.stem}.md"
        return 0 if convert_one(args.pdf, out, force=args.force) else 1

    queue: list[Path] = []
    if args.queue:
        queue = [SOURCE / name for name in args.queue]
    elif args.all_scans:
        import fitz

        for pdf in sorted(SOURCE.glob("*.pdf")):
            md = RAW / md_name_for_pdf(pdf)
            if md.is_file() and not args.force:
                continue
            doc = fitz.open(pdf)
            n = min(5, len(doc))
            avg = sum(len(doc[i].get_text().strip()) for i in range(n)) / max(n, 1)
            if avg < 120:
                queue.append(pdf)
    else:
        ap.print_help()
        return 1

    ok = 0
    for pdf in queue:
        md = RAW / md_name_for_pdf(pdf)
        if convert_one(pdf, md, force=args.force):
            ok += 1
    print(f"done: {ok}/{len(queue)}")
    return 0 if ok == len(queue) else 1


if __name__ == "__main__":
    raise SystemExit(main())
