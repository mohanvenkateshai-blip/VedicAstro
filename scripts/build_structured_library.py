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
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "knowledge-graph" / "raw"
STRUCTURED = ROOT / "knowledge-graph" / "structured"
STRUCTURED.mkdir(parents=True, exist_ok=True)

# Strong patterns for real Vedic / technical books
CHAPTER_PATTERNS = [
    # "Chapter 1", "Chapter - 7", "Ch. 3 - Foo", "Ch 2: Title"
    re.compile(r"^(?:Chapter|Ch\.?|Ch)\s*[:\-]?\s*(\d+[\.\d\-]*)[\.\s:\-–—]*(.*)$", re.I),
    # "1. Foundations", "3.1 Foo"
    re.compile(r"^(\d{1,2}(?:\.\d+)?)\.\s+([A-Z][^\n]{3,120})$"),
    # All-caps style but require a longer/more distinctive title (avoid "2 JAIMINISUTRAS")
    re.compile(r"^(\d+)\s+([A-Z][A-Z][A-Z\s\-–:']{8,80})$"),
    # Sutra markers as chapter-ish only if full word (individual "Su. N" are aphorisms, not chapters)
    re.compile(r"^(Sutra|Sūtra)\s*(\d+[\.\d\-]*)[\s:\-]*(.*)$", re.I),
    # Sanskrit structural: ADHYAYA N — PADA M (Jaimini style); tolerant of OCR on "PADA" and roman nums
    re.compile(r"^(?:ADHYAYA|Adhyaya)\s*([0-9IVX]+|[०-९]+)[\s,—–-]*(?:PADA|Pada|Papa|Papy|Paada)\s*([0-9IVX]+|[०-९]+)", re.I),
]

SECTION_PATTERNS = [
    re.compile(r"^(\d+\.\d+(?:\.\d+)?)\s+(.+)$"),
    # Devanagari numbered subheads e.g. "१.१ Foo" or "1.1 Foo" already covered above
    re.compile(r"^([०-९]+\.[०-९]+(?:\.[०-९]+)?)\s+(.+)$"),
    re.compile(r"^(#{2,6})\s+(.+)$"),   # ## , ### etc.
    # Sutra aphorisms as sections: "Su. 1,— Title..." or "१, उपदेश..." or "Su. 2.—..."
    re.compile(r"^(Su\.|Sūtra)\s*(\d+|[०-९]+)[\.,—–-]*\s*(.{0,80})$", re.I),
    re.compile(r"^([०-९]+)\s*[,.\s]\s*(.{3,80})$"),
]

PAGE_HEADER = re.compile(r"^##\s*Page\s+(\d+)", re.I)

# Devanagari to ASCII digit map for normalizing chapter/sutra numbers
DEVANAGARI_NUM_MAP = str.maketrans("०१२३४५६७८९", "0123456789")

# BOOK_OVERRIDES: targeted chapter detection for the 5 key classics to fix OCR junk and verse explosion.
# Each specifies prefer_patterns (strong TOC/body chapter signals), reject_patterns, and min_lines_per_chapter
# to enforce realistic spacing between chapters (preventing per-verse or per-list-item splits).
BOOK_OVERRIDES: dict[str, dict] = {
    "Brihat_Parasara_Hora_Sastra_Vol_1": {
        "prefer_patterns": [
            re.compile(r"^(\d{1,2})\.\s+([A-Z][^\n]{5,120}?)(?:\s+\d{2,4})?\s*$"),
            re.compile(r"^(?:Chapter|Ch\.?)\s*(\d+)[\s:\-]*(.*)$", re.I),
        ],
        "reject_patterns": [
            re.compile(r"^\d{1,4}$"),
        ],
        "min_lines_per_chapter": 5,
        "allow_heading_promote": True,
    },
    "Brihat_Parasara_Hora_Sastra_Vol_2": {
        "prefer_patterns": [
            re.compile(r"^(\d{1,2})\.\s+([A-Z][^\n]{5,120}?)(?:\s+\d{2,4})?\s*$"),
            re.compile(r"^(?:Chapter|Ch\.?)\s*(\d+)[\s:\-]*(.*)$", re.I),
        ],
        "reject_patterns": [
            re.compile(r"^\d{1,4}$"),
        ],
        "min_lines_per_chapter": 5,
        "allow_heading_promote": True,
    },
    "Jaimini_Sutras": {
        "prefer_patterns": [
            # Tolerant of OCR "Papa/Papy" and roman for Adhyaya/Pada
            re.compile(r"^[A-Za-z]*ADHY[A-Z]*\s*([0-9IVX]+|[०-९]+)[\s,—–-]*(?:PADA|Pada|Papa|Papy|Paada)\s*([0-9IVX]+|[०-९]+)", re.I),
            re.compile(r"^[A-Za-z]*ADHY[A-Z]*\s*([0-9IVX]+|[०-९]+)", re.I),
            re.compile(r"Chapter\s+(\d+)", re.I),
        ],
        "min_lines_per_chapter": 8,
        "reject_patterns": [
            re.compile(r"JAIMINISUTRAS|JATMINISUTRAS", re.I),
            re.compile(r"^(Su\.|St\.)", re.I),
            re.compile(r"End of .*Pada", re.I),
        ],
        "min_lines_per_chapter": 30,
        "allow_heading_promote": False,
    },
    "Phaladeepika_Mantreswara": {
        "prefer_patterns": [
            re.compile(r"^Chapter\s+(\d+)[:\s]*(.*)$", re.I),
        ],
        "reject_patterns": [
            re.compile(r"Chapter\s+\d+.*\bChapter\b", re.I),
            re.compile(r"End of ", re.I),
            re.compile(r"^\d+$", re.I),
        ],
        "min_lines_per_chapter": 5,
        "allow_heading_promote": True,
    },
    "Bhavartha_Ratnakara": {
        "prefer_patterns": [
            re.compile(r"^(?:C[h]?hapter|Cuarm|Cuaptern)\s*(\d+)[\s:,\-]*(.*)$", re.I),
            re.compile(r"^(\d+)\s+(Dhana|Nirdhana|Education|Tastes|Brothers|Conveyances|Health|Fortunate|Rayayoga|Results|Graha|Planetary|Yogas|Combinations)", re.I),
            re.compile(r"^(\d{1,2})\.\s+([A-Z][^\n]{5,})$"),
        ],
        "reject_patterns": [
            re.compile(r"BHAVARTHA|BHAVART.*RATNA", re.I),
            re.compile(r"^(Mesha|Veishabha|Mithuna|Kataka|Simha|Kanya|Thula|Vurschika|Dkanur|Makara|Kombha|Meena|Vrisha|Lagya|Lacxa|Lagna)", re.I),
            re.compile(r"End of |Stanza \d|born in ", re.I),
        ],
        "min_lines_per_chapter": 5,
        "allow_heading_promote": True,
    },
}

def normalize_num(n: str | None) -> str | None:
    if not n:
        return None
    n = n.translate(DEVANAGARI_NUM_MAP)
    # Basic roman to decimal for Adhyaya/Pada stability (common small values)
    rom = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10"}
    nu = n.upper()
    if nu in rom:
        return rom[nu]
    return n

def is_likely_running_header(line: str, book_stem: str) -> bool:
    """Heuristic to drop page-running headers that are not real chapters.
    Examples: "2 JAIMINISUTRAS", "4 The Creation", "6 JATMINISUTRAS"
    """
    s = line.strip()
    su = s.upper().strip(":-–—., ")
    standalone_junk = {"JAIMINISUTRAS", "JATMINISUTRAS", "BHAVARTHA RATNAKARA", "BHAVARTHARATNAKARA", "JAIMINI SUTRAS", "SAGAR PUBLICATIONS", "CH. DETAILS", "BANGALORE VENKATA", "BISTOR"}
    if su in standalone_junk or "BHAVART" in su and "RATNA" in su:
        return True
    if re.match(r"^\d{1,4}$", s):
        return True
    if re.search(r"^Phone\s*:|^\d{3,}$", s, re.I):
        return True
    # Very short all-caps after a number at start of line
    m = re.match(r"^(\d+|[०-९]+)\s+([A-Z][A-Z'\-–— ]{2,40})$", s)
    if not m:
        return False
    title = m.group(2).strip()
    stem_norm = book_stem.replace("_", " ").upper()
    junk_tokens = {"JAIMINISUTRAS", "JATMINISUTRAS", "CREATION", "THE CREATION", "BHAVARTHA RATNAKARA"}
    if title.upper() in junk_tokens:
        return True
    if title.upper() in stem_norm or stem_norm in title.upper():
        return True
    # Very short generic titles after bare number
    if len(title) <= 12 and title.isupper():
        return True
    return False

def is_likely_sutra_aphorism(line: str) -> bool:
    """Skip individual sutra/aphorism lines as chapter candidates.
    Examples: "१, ` उपदेश...", "Su. 2.—Abhipasyanti...", "२. अभिपर्यंति..."
    """
    s = line.strip()
    # Devanagari number + punctuation + (Devanagari or short text)
    if re.match(r"^[०-९]+\s*[,.\s]", s) and any(ord(ch) > 0x0900 for ch in s[:30]):
        return True
    # Sutra abbreviation at start
    if re.match(r"^(Su\.|St\.|Sutra|Sūtra)\s*\d+", s, re.I):
        return True
    # Line contains early sutra danda and is short
    if "॥" in s[:40] and len(s) < 80:
        return True
    return False

def title_looks_like_prose(title: str) -> bool:
    """Require titles for generic number patterns to look like real headings."""
    t = title.strip()
    if not t:
        return False
    # Must contain at least one ASCII letter run of 3+
    if not re.search(r"[A-Za-z]{3,}", t):
        return False
    # Avoid titles that are mostly punctuation/garbage or very garbled
    letters = sum(ch.isalpha() for ch in t)
    if letters < 5:
        return False
    # Reject table-like or numeric ghatis fragments
    if "%" in t or re.search(r"\d\s*%\s*ghatis", t, re.I):
        return False
    # Reject if it looks like a sutra fragment (Devanagari right after number word)
    if re.match(r"^[A-Z]{2,}\s*[ः।॥]", t):
        return False
    # Title should have more letters than digits (rough signal)
    digits = sum(ch.isdigit() for ch in t)
    if digits > letters // 2:
        return False
    # Reject sentence-like or mid-paragraph enumerations
    if len(t) > 70:
        return False
    if re.search(r"\b(signs|ghatis|from the|in the|may occur|there are)\b", t, re.I):
        return False
    # Prefer Title Case feel: at least two capitalized words or a clear heading shape
    t2 = re.sub(r"\d+(?:st|nd|rd|th)", "", t)
    caps = len(re.findall(r"\b[A-Z][a-z]", t))
    if caps < 1 and len(t.split()) > 3:
        if not (t.isupper() or t2.isupper()):
            return False
    return True

def looks_like_junk_chapter_title(title: str, number: str | None, book_stem: str) -> bool:
    t = (title or "").strip()
    if not t:
        return True
    tu = t.upper().replace(" ", "")
    if tu in {"JAIMINISUTRAS", "JATMINISUTRAS", "JAIMINISUTRAS", "CREATION", "THECREATION", "BHAVARTHARATNAKARA"}:
        return True
    if "JAIMINISUT" in tu or "BHAVARTHARATNA" in tu or ("BHAVART" in tu and "RATNA" in tu):
        return True
    stem_words = set(re.findall(r"[A-Z]+", book_stem.upper()))
    if tu in stem_words:
        return True
    # Number-only or extremely short
    if number and t == number:
        return True
    if len(t) < 4:
        return True
    if re.match(r"^\d{2,4}$", t):
        return True
    if re.search(r"Phone|Girish|Preface by|Ch\. Details|Sl\. No\.|translator| Sagar |Brihat Parasara Hora Shastra \d|Distribution by|Parasz|Parase", t, re.I):
        return True
    if re.search(r"\d{3,}$", t):
        return True
    if re.search(r"hours, at |These are used|Venus \| |Mars Sun|DEK,|Speculam|Mooltri|Lord of the Portion", t, re.I):
        return True
    return False

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

    override = BOOK_OVERRIDES.get(stem, {})
    ch_pats = override.get("prefer_patterns") or CHAPTER_PATTERNS
    reject_pats = override.get("reject_patterns", [])
    min_gap = override.get("min_lines_per_chapter", 0)

    chapters: list[Chapter] = []
    current_chapter: Chapter | None = None
    current_section: Section | None = None
    seen_ch_titles: set[str] = set()

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
        prev = lines[i-1].strip() if i > 0 else ""
        nxt = lines[i+1].strip() if i + 1 < len(lines) else ""
        separated = (not prev or len(prev) < 6 or prev.startswith("##")) and (not nxt or len(nxt) < 6 or nxt.startswith("##"))

        # Skip pure page markers as chapters (the old problem)
        if PAGE_HEADER.match(line):
            continue

        # Drop obvious page running headers (e.g. "2 JAIMINISUTRAS")
        if is_likely_running_header(line, stem):
            continue

        # Skip TOC-like lines for structural markers (page ranges, "Part I, Chapter")
        toc_noise = bool(re.search(r"\bwe\s+\d|\.\.\.\s*\d|Part\s+[IVX]|{.*Chapter", line, re.I))
        if toc_noise and not re.match(r"^(Chapter|Ch\.?|ADHYAYA)\s", line, re.I):
            continue

        # Try chapter patterns first (stronger); overrides provide book-specific prefers
        matched_ch = False
        for pat in ch_pats:
            m = pat.match(line)
            if not m and override:
                m = pat.search(line)
            if m:
                # ADHYAYA pattern captures (adhyaya, pada)
                if "ADHYAYA" in pat.pattern.upper() or "ADHY" in pat.pattern.upper():
                    adh = normalize_num(m.group(1))
                    pada = normalize_num(m.group(2)) if m.lastindex and m.lastindex >= 2 else None
                    num = f"{adh}.{pada}" if pada else adh
                    title = f"Adhyaya {adh} Pada {pada}" if pada else f"Adhyaya {adh}"
                    # Skip TOC-ish ADHYAYA lines (contain page ranges or "we ")
                    if re.search(r"\bwe\s+\d|\.\.\.|\{.*Chapter", line, re.I):
                        matched_ch = False
                        break
                else:
                    raw_num = m.group(1) if m.lastindex and m.lastindex >= 1 else None
                    num = normalize_num(raw_num)
                    # group(2) may be empty for bare "Chapter 1"
                    raw_title = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
                    title = clean_title(raw_title) if raw_title else ""
                if not title:
                    # Title may be on next line or absent; use a placeholder that will be improved later
                    title = f"Chapter {num}" if num else line[:60]
                if title:
                    title = re.sub(r"\s+\d{2,4}\s*$", "", title).strip()
                    title = clean_title(title)
                # Apply per-book reject patterns (e.g. duplicate TOC, page nums)
                for rp in reject_pats:
                    if rp.search(line) or (title and rp.search(title)):
                        matched_ch = False
                        break
                if not matched_ch:
                    break
                if looks_like_junk_chapter_title(title, num, stem):
                    matched_ch = False
                    break
                # Duplicate TOC entry guard
                tkey = (title or "").upper().strip()
                if tkey and tkey in seen_ch_titles:
                    matched_ch = False
                    break
                # min gap to suppress verse-level / list-item explosion in dense OCR
                if min_gap > 0 and chapters:
                    last_start = chapters[-1].start_line
                    if i - last_start < min_gap:
                        matched_ch = False
                        break
                # For loose number patterns, require prose-like title
                if pat.pattern.startswith("^(\\d") and not title_looks_like_prose(title):
                    matched_ch = False
                    break
                finish_chapter()
                ch_id = f"ch-{slug(num or title)}"
                current_chapter = Chapter(
                    id=ch_id,
                    number=num,
                    title=title,
                    level=1,
                    start_line=i,
                )
                if tkey:
                    seen_ch_titles.add(tkey)
                matched_ch = True
                break
        if matched_ch:
            continue

        # Heading promotion only for non-classic books or when explicitly allowed; classics rely on prefer + gap
        allow_hp = override.get("allow_heading_promote", True) if override else True
        # Heading promotion for strong all-caps / title-case headings (TOC listed chs, handbook sections, zero-ch fallback in main)
        s = line
        is_strong_heading = (
            allow_hp and s and 8 <= len(s) <= 70 and 2 <= len(s.split()) <= 8 and separated and
            not looks_like_junk_chapter_title(s, None, stem) and
            not is_likely_running_header(s, stem) and
            not re.search(r"\b(End of|of the First|from the)\b", s, re.I) and
            not re.search(r"[॥ऽ—]{1,}|\.{2,}", s) and
            (s.isupper() or (s[0].isupper() and len(re.findall(r"\b[A-Z][a-z]", s)) >= 1))
        )
        if is_strong_heading and not any(rp.search(s) for rp in reject_pats):
            gap_ok = True
            if min_gap > 0 and chapters:
                if i - chapters[-1].start_line < min_gap:
                    gap_ok = False
            if gap_ok:
                if not current_chapter:
                    current_chapter = Chapter(
                        id=f"ch-{slug(s)}",
                        number=None,
                        title=clean_title(s),
                        level=1,
                        start_line=i,
                    )
                    tkey = clean_title(s).upper().strip()
                    if tkey:
                        seen_ch_titles.add(tkey)
                    continue
                else:
                    finish_chapter()
                    current_chapter = Chapter(
                        id=f"ch-{slug(s)}",
                        number=None,
                        title=clean_title(s),
                        level=1,
                        start_line=i,
                    )
                    tkey = clean_title(s).upper().strip()
                    if tkey:
                        seen_ch_titles.add(tkey)
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
    # Use ==0 to preserve any chs found by main (e.g. body numbered for classics); synthetic for true zeros
    if len(chapters) == 0:
        # Create synthetic chapters from the biggest numbered blocks we can find
        # Stricter: require at least two words in title and not a pure running header token
        # Also promote strong uppercase headings (heading promotion fallback) for flat handbooks/OCR
        synthetic: list[Chapter] = []
        for i, line in enumerate(lines):
            s = line.strip()
            m = re.match(r"^(\d+)\.\s+(.{5,120})$", s)
            if m:
                num, t = m.groups()
                t_clean = clean_title( re.sub(r"\s+\d{2,4}\s*$", "", t) )
                if len(t_clean.split()) >= 2 and not looks_like_junk_chapter_title(t_clean, num, stem):
                    synthetic.append(Chapter(
                        id=f"ch-{num}",
                        number=normalize_num(num),
                        title=t_clean,
                        level=1,
                        start_line=i,
                        content_preview=line[:200]
                    ))
            elif s and len(s) >= 8 and s.isupper() and len(s.split()) >= 2:
                if i < 30:
                    pass  # skip front matter running/brand headers
                else:
                    t_clean = clean_title(s)
                    if len(t_clean.split()) >= 2 and not looks_like_junk_chapter_title(t_clean, None, stem) and not is_likely_running_header(s, stem):
                        synthetic.append(Chapter(
                            id=f"ch-{slug(t_clean)}",
                            number=None,
                            title=t_clean,
                            level=1,
                            start_line=i,
                            content_preview=s[:200]
                        ))
            # Additional title-case heading promotion in fallback for flat handbooks without strong uppers
            if not m and 8 <= len(s) <= 70 and 2 <= len(s.split()) <= 8 and s[0].isupper() and not s.endswith(('.', ',', ':', ';')) and not looks_like_junk_chapter_title(s, None, stem) and not is_likely_running_header(s, stem) and not re.search(r"->|http|Stanza|born in|check |the selected", s, re.I):
                t_clean = clean_title(s)
                synthetic.append(Chapter(
                    id=f"ch-{slug(t_clean)}",
                    number=None,
                    title=t_clean,
                    level=1,
                    start_line=i,
                    content_preview=s[:200]
                ))
        if len(synthetic) >= 2:
            chapters = synthetic

    # For sutra-style texts, prefer Adhyaya/Pada chapters as the logical structure.
    # Prune noisy chapters that slipped through (garbled OCR titles, body enumerations).
    if any("Adhyaya" in (c.title or "") for c in chapters):
        def _keep_as_chapter(c: Chapter) -> bool:
            t = (c.title or "")
            if "Adhyaya" in t:
                return True
            # Keep only if it has a clean prose title and is not obviously body text
            if looks_like_junk_chapter_title(t, c.number, stem):
                return False
            if not title_looks_like_prose(t):
                return False
            return False  # default: drop non-Adhyaya for sutra books
        kept = [c for c in chapters if _keep_as_chapter(c)]
        if kept:
            chapters = kept

    # Rescue for Jaimini-style sutra texts when main pass + override produced no Adhyaya chapters
    # (due to frontmatter noise, min_gap, or OCR). Build strictly from body ADHYAYA markers.
    if stem == "Jaimini_Sutras" and not any("Adhyaya" in (c.title or "") for c in chapters):
        adh_chapters: list[Chapter] = []
        adh_indices = []
        adh_pat = re.compile(r"ADHYAYA\s*([0-9IVX]+|[०-९]+)[\s,—–-]*(?:PADA|Pada|Papa|Papy)?\s*([0-9IVX]+|[०-९]+)?", re.I)
        for i, ln in enumerate(lines):
            m = adh_pat.search(ln)
            if m and not re.search(r"\bwe\s+\d|\.\.\.|\{.*Chapter", ln, re.I):
                adh = normalize_num(m.group(1)) or m.group(1)
                pada = normalize_num(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else None
                num = f"{adh}.{pada}" if pada else adh
                title = f"Adhyaya {adh} Pada {pada}" if pada else f"Adhyaya {adh}"
                adh_chapters.append(Chapter(id=f"ch-{adh}-{pada}" if pada else f"ch-{adh}", number=num, title=title, level=1, start_line=i))
                adh_indices.append(i)
        if len(adh_chapters) >= 2:
            # Attach simple sections from Su. / numbered aphorism lines between adhyayas
            for idx, ch in enumerate(adh_chapters):
                start = ch.start_line
                end = adh_indices[idx+1] if idx+1 < len(adh_indices) else len(lines)
                for j in range(start+1, end):
                    sline = lines[j].strip()
                    ms = re.match(r"^(?:Su\.|Sūtra)\s*(\d+|[०-९]+)", sline, re.I)
                    if not ms:
                        ms = re.match(r"^([०-९]+)\s*[,.\s]", sline)
                    if ms:
                        sec_title = sline[:80]
                        ch.sections.append(Section(id=f"{ch.id}-sec-{slug(sec_title)}", title=sec_title, level=2, start_line=j))
            chapters = adh_chapters

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

    # Compute parse quality signal for downstream consumers (Learn reader, KE provenance)
    def _assess_quality(chs: list[Chapter], book_stem: str) -> str:
        if not chs:
            return "needs_review"
        n = len(chs)
        junk_count = sum(1 for c in chs if looks_like_junk_chapter_title(c.title, c.number, book_stem))
        empty_sec = sum(1 for c in chs if not c.sections)
        has_dev = any(c.number and any(ord(ch) > 0x0900 for ch in str(c.number)) for c in chs)
        # Reasonable structure: several chapters, few junk titles, some sections, no dev nums in ids
        if n >= 3 and junk_count <= 1 and (empty_sec / n) < 0.6 and not has_dev:
            return "high"
        if n >= 1 and junk_count <= max(2, n // 3) and not has_dev:
            return "medium"
        return "needs_review"

    parse_quality = _assess_quality(chapters, stem)

    result = {
        "book_id": book_id,
        "canonical_name": path.stem.replace("_", " "),
        "source_file": path.name,
        "graph_version": "newbooks-v1",
        "parse_quality": parse_quality,
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
    ap.add_argument("--workers", type=int, default=1, help="Parallel workers for --all (ProcessPool)")
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

    workers = max(1, getattr(args, "workers", 1) or 1)
    results: list[tuple[Path, dict | None, str | None]] = []

    def _process_one(f: Path) -> tuple[Path, dict | None, str | None]:
        try:
            data = parse_book(f)
            out = STRUCTURED / f"{f.stem}.json"
            out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            return (f, data, None)
        except Exception as e:
            return (f, None, str(e))

    if workers == 1:
        for f in files:
            fpath, data, err = _process_one(f)
            if err:
                print(f"  ✗ {fpath.name}: {err}")
            else:
                print(f"  ✓ {fpath.name} → {len(data['chapters'])} chapters, {data['total_sections']} sections")
            results.append((fpath, data, err))
    else:
        print(f"  (parallel workers={workers})")
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_process_one, f): f for f in files}
            for fut in as_completed(futs):
                fpath, data, err = fut.result()
                if err:
                    print(f"  ✗ {fpath.name}: {err}")
                else:
                    print(f"  ✓ {fpath.name} → {len(data['chapters'])} chapters, {data['total_sections']} sections")
                results.append((fpath, data, err))

    ok = sum(1 for _, d, e in results if d is not None)
    print(f"Done. {ok}/{len(files)} books. Structured files in knowledge-graph/structured/")
if __name__ == "__main__":
    main()
