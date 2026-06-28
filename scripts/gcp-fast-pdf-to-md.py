#!/usr/bin/env python3
"""Fast PDF→markdown: pymupdf text layer, else Tesseract eng."""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import fitz
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None  # large scan pages


def _page_tesseract(pdf: Path, page_num: int, dpi: int) -> str:
    images = convert_from_path(
        str(pdf), first_page=page_num + 1, last_page=page_num + 1, dpi=dpi
    )
    if not images:
        return ""
    img = images[0].convert("L")
    w, h = img.size
    if w > 2400:
        img = img.resize((2400, int(h * 2400 / w)), Image.Resampling.LANCZOS)
    return pytesseract.image_to_string(img, lang="eng", config="--psm 3").strip()


def _ocr_page(args: tuple[str, int, int]) -> tuple[int, str]:
    pdf, page_num, dpi = args
    return page_num, _page_tesseract(Path(pdf), page_num, dpi)


def convert_pdf(
    pdf: Path, out: Path, *, min_chars: int = 80, workers: int = 8, dpi: int = 120
) -> int:
    doc = fitz.open(pdf)
    n = len(doc)
    parts: list[tuple[int, str]] = []
    total = 0
    ocr_jobs: list[tuple[str, int, int]] = []

    for i in range(n):
        text = doc[i].get_text().strip()
        if len(text) >= min_chars:
            parts.append((i, f"## Page {i + 1}\n\n{text}\n"))
            total += len(text)
        else:
            ocr_jobs.append((str(pdf), i, dpi))

    if ocr_jobs:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_ocr_page, j): j[1] for j in ocr_jobs}
            for fut in as_completed(futs):
                i, text = fut.result()
                if text:
                    parts.append((i, f"## Page {i + 1}\n\n{text}\n"))
                    total += len(text)

    parts.sort(key=lambda x: x[0])
    body = "".join(p[1] for p in parts)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"# {pdf.stem}\n\n{body}", encoding="utf-8")
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dpi", type=int, default=120)
    args = ap.parse_args()
    pdf, out = Path(args.pdf), Path(args.out)
    chars = convert_pdf(pdf, out, workers=args.workers, dpi=args.dpi)
    print(f"{pdf.name}: {chars:,} chars → {out}", flush=True)
    return 0 if chars > 1000 else 1


if __name__ == "__main__":
    raise SystemExit(main())
