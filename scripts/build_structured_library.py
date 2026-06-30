#!/usr/bin/env python3
"""
Builds a CLEAN, HIERARCHICAL, AUTHORITATIVE structured view of every source book.

This is the "organise from the beginning" step the user demanded.

For each raw/*.md it produces:
  knowledge-graph/structured/<book_stem>.json

Structure (no more "frontmatter", "H1", random page dumps):

{
  "book_id": "Ashtakavarga_System_Comprehensive_Handbook",
  "canonical_name": "Ashtakavarga System Comprehensive Handbook",
  "source_file": "Ashtakavarga_System_Comprehensive_Handbook.md",
  "graph_version": "newbooks-v1",
  "chapters": [
    {
      "id": "ch-01",
      "number": "1",
      "title": "Foundations and Philosophy of Ashtakavarga",
      "level": 1,
      "start_offset": 9,
      "end_offset": 26,
      "sections": [
        {
          "id": "ch-01-sec-1-1",
          "title": "1.1 Authoritative Classical Source Documents",
          "level": 2,
          "content_preview": "..."
        }
      ],
      "content_preview": "Ashtakavarga is an advanced..."
    },
    ...
  ],
  "toc": [ ... flat list for quick nav ... ],
  "total_sections": N
}

This becomes the single source of truth for the Learn reader left-nav + jumping.
It is also the mapping from KE nodes back to precise locations in the original Gyan source.

Run:
  python3 scripts/build_structured_library.py --all
  python3 scripts/build_structured_library.py --books "Ashtakavarga*,Brihat_Parasara*"

Then the portal will use these instead of guessing from weak source_location.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "knowledge-graph" / "raw"
STRUCTURED = ROOT / "knowledge-graph" / "structured"
STRUCTURED.mkdir(parents=True, exist_ok=True)

# Strong patterns for real Vedic / technical books
CHAPTER_PATTERNS = [
    re.compile(r"^(?:Chapter|Ch\.?|Ch)\s*[:\-]?\s*(\d+[\.\d\-]*)[\.\s:\-–—]*(.+?)$", re.I),
    re.compile(r"^(\d{1,2}(?:\.\d+)?)\.\s+([A-Z][^\n]{3,120})$"),  # 1. Foundations , 3.1 Foo
    re.compile(r"^(\d+)\s+([A-Z][A-Z\s\-–:']{5,80})$"),           # 1 THE CREATION (all caps style)
    re.compile(r"^(Sutra|Sūtra)\s*(\d+[\.\d\-]*)[\s:\-]*(.*)$", re.I),
]

SECTION_PATTERNS = [
    re.compile(r"^(\d+\.\d+(?:\.\d+)?)\s+(.+)$"),
    re.compile(r"^(#{2,6})\s+(.+)$"),   # ## , ### etc.
]

PAGE_HEADER = re.compile(r"^##\s*Page\s+(\d+)", re.I)

def slug(s: str, max_len: int = 60) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    s = re.sub(r"[\s_]+", "_", s)
    return s[:max_len] or "sec"

def clean_title(t: str) -> str:
    t = t.strip().strip(":-–—_ ")
    t = re.sub(r"\s+", " ", t)
    return t

@dataclass
class Section:
    id: str
    title: str
    level: int
    start_line: int
    end_line: int | None = None
    content_preview: str = ""

@dataclass
class Chapter:
    id: str
    number: str | None
    title: str
    level: int
    start_line: int
    end_line: int | None = None
    sections: list[Section] = None  # type: ignore
    content_preview: str = ""

    def __post_init__(self):
        if self.sections is None:
            self.sections = []

def parse_book(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    stem = path.stem
    book_id = stem

    chapters: list[Chapter] = []
    current_chapter: Chapter | None = None
    current_section: Section | None = None

    def close_current():
        nonlocal current_chapter, current_section
        if current_section and current_chapter:
            current_chapter.sections.append(current_section)  # type: ignore
        current_section = None

    def finish_chapter():
        nonlocal current_chapter
        if current_chapter:
            close_current()
            if not current_chapter.content_preview:
                # take first 300 chars of the chapter block
                start = current_chapter.start_line
                end = current_chapter.end_line or min(start + 8, len(lines))
                current_chapter.content_preview = " ".join(lines[start:end])[:280]
            chapters.append(current_chapter)
        current_chapter = None

    for i, raw_line in enumerate(lines):
        line = raw_line.strip()

        # Skip pure page markers as chapters (the old problem)
        if PAGE_HEADER.match(line):
            continue

        # Try chapter patterns first (stronger)
        matched_ch = False
        for pat in CHAPTER_PATTERNS:
            m = pat.match(line)
            if m:
                finish_chapter()
                num = m.group(1) if m.lastindex and m.lastindex >= 1 else None
                title = clean_title(m.group(2) if m.lastindex and m.lastindex >= 2 else line)
                ch_id = f"ch-{slug(num or title)}"
                current_chapter = Chapter(
                    id=ch_id,
                    number=num,
                    title=title or f"Chapter {num or i}",
                    level=1,
                    start_line=i,
                )
                matched_ch = True
                break
        if matched_ch:
            continue

        # Section / subheading
        for pat in SECTION_PATTERNS:
            m = pat.match(line)
            if m:
                if not current_chapter:
                    # Promote first strong section to a chapter (common in handbooks)
                    title = clean_title(m.group(2) if m.lastindex >= 2 else m.group(1))
                    current_chapter = Chapter(
                        id=f"ch-{slug(title)}",
                        number=None,
                        title=title,
                        level=1,
                        start_line=i,
                    )
                close_current()
                level = 2
                if m.group(1).startswith("#"):
                    level = len(m.group(1))
                sec_title = clean_title(m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1))
                sec_id = f"{current_chapter.id}-sec-{slug(sec_title)}"
                current_section = Section(
                    id=sec_id,
                    title=sec_title,
                    level=level,
                    start_line=i,
                )
                break

    finish_chapter()

    # If we got almost nothing (very flat file), fall back to a single chapter + major paragraphs
    if len(chapters) < 2:
        # Create synthetic chapters from the biggest numbered blocks we can find
        synthetic: list[Chapter] = []
        for i, line in enumerate(lines):
            m = re.match(r"^(\d+)\.\s+(.{5,120})$", line.strip())
            if m:
                num, t = m.groups()
                synthetic.append(Chapter(
                    id=f"ch-{num}",
                    number=num,
                    title=clean_title(t),
                    level=1,
                    start_line=i,
                    content_preview=line[:200]
                ))
        if len(synthetic) >= 2:
            chapters = synthetic

    # Build flat toc and assign end lines roughly
    toc = []
    for idx, ch in enumerate(chapters):
        next_start = chapters[idx+1].start_line if idx + 1 < len(chapters) else len(lines)
        ch.end_line = next_start - 1
        for sidx, sec in enumerate(ch.sections or []):
            next_sec = (ch.sections or [])[sidx+1].start_line if sidx+1 < len(ch.sections or []) else (ch.end_line or len(lines))
            sec.end_line = next_sec - 1
            toc.append({
                "id": sec.id,
                "title": sec.title,
                "chapter": ch.title,
                "chapter_id": ch.id,
            })
        toc.append({
            "id": ch.id,
            "title": ch.title,
            "chapter": ch.title,
            "chapter_id": ch.id,
        })

    result = {
        "book_id": book_id,
        "canonical_name": path.stem.replace("_", " "),
        "source_file": path.name,
        "graph_version": "newbooks-v1",
        "chapters": [asdict(c) for c in chapters],
        "toc": toc,
        "total_chapters": len(chapters),
        "total_sections": sum(len(c.sections or []) for c in chapters),
    }
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--books", help="Comma glob patterns, e.g. Ashtakavarga*,Brihat*")
    args = ap.parse_args()

    files: list[Path] = []
    if args.all:
        files = sorted(RAW.glob("*.md"))
    elif args.books:
        pats = [p.strip() for p in args.books.split(",")]
        for pat in pats:
            files.extend(RAW.glob(f"{pat}.md"))
        files = sorted(set(files))
    else:
        print("Use --all or --books 'Pattern*'")
        return

    print(f"Building structured library for {len(files)} books ...")
    for f in files:
        try:
            data = parse_book(f)
            out = STRUCTURED / f"{f.stem}.json"
            out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            print(f"  ✓ {f.name} → {len(data['chapters'])} chapters, {data['total_sections']} sections")
        except Exception as e:
            print(f"  ✗ {f.name}: {e}")

    print("Done. Structured files in knowledge-graph/structured/")

if __name__ == "__main__":
    main()
