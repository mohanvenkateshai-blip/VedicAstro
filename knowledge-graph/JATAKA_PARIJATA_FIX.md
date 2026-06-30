# Jataka_Parijata Structured Parser Fix — 2026-06-30

## Problem
- Raw source (`knowledge-graph/raw/Jataka_Parijata.md`) is heavily OCR-corrupted (5921 lines, 483 page markers).
- Zero recognizable chapter markers (no "Adhyaya", "Chapter", "Sloka").
- Previous structured extraction produced **178 garbage chapters** with titles like:
  - "Sisk we wept ee)"
  - "Bir Se Ne i a pt le Toaal"
  - "Rengarieniresrsress ereere!"
- `parse_quality: "medium"` (misleading), patch mapped 483 nodes to unusable `ch-*` slugs.
- Prior patch note: "STRUCTURED QUALITY POOR... suggest re-parsing with better chapter heuristics".

## Solution (targeted, non-destructive)
- Added `Jataka_Parijata` entry to `BOOK_OVERRIDES` in `scripts/build_structured_library.py`:
  - `prefer_patterns: []` (disable greedy all-caps / numbered heading matches)
  - `min_lines_per_chapter: 80`
  - `allow_heading_promote: False`
- Extended junk denylists (`is_likely_running_header`, `looks_like_junk_chapter_title`) with "JATAKA PARIJATA", "JATAKAPARIJATA".
- Added OCR-garbage heuristics (short 2-3 letter token clusters, low average word length).
- Fixed overzealous `\d{3,}$` filter that was flagging page-range titles.
- Implemented **page-group rescue** specific to this book:
  - Scans for `## Page N` markers (483 found).
  - Groups ~10 pages per chapter → stable titles `"Pages X–Y"`, ids `ch-pX-pY` (or canonical `ch-N` via later normalization).
  - Produces ~49 chapters instead of 178 micro-fragments.
- Post-rescue: fill `content_preview`; quality assessor returns `"medium-improved"` for clean page-grouped sets.

## Commands
```bash
python3 scripts/build_structured_library.py --books "Jataka_Parijata"
python3 scripts/map_nodes_to_structured.py --books "Jataka_Parijata" \
  --graph knowledge-graph/graphify-out/graph.json \
  --out knowledge-graph/patches/patch-Jataka_Parijata.json
# (canonical union, COVERAGE_MATRIX, RUN_LOG updated by follow-up steps)
```

## Results
| Metric                    | Before                  | After                          |
|---------------------------|-------------------------|--------------------------------|
| Chapters                  | 178 (garbage)           | 49 (page groups)               |
| parse_quality             | "medium"                | "medium-improved"              |
| Patch coverage            | 483/485 (99.6%)         | 483/485 (99.6%)                |
| review_needed=true        | many                    | 0                              |
| Unique chapter_ids        | ~3 usable               | 49 (all page groups)           |
| /learn nav usability      | broken (junk titles)    | usable (Pages X–Y ranges)      |

Sample chapter titles (new):
- "Pages 5–31" (ch-1)
- "Pages 46–56" (ch-3)
- ...
- "Pages 680–682" (ch-49)

## Impact on Consumers
- `knowledge-graph/structured/Jataka_Parijata.json` now has coherent hierarchy.
- Per-book patch and canonical `node-chapter-map.json` updated.
- Portal Learn reader left-nav will render 49 entries; deep links resolve to page ranges in the BookReader.
- `COVERAGE_MATRIX.json` carries `structured_quality` + `note` for this book.

## Limitations / Flags
- Titles are **synthetic page ranges**, not semantic (no chapter names in raw).
- If a cleaner source (with real Adhyaya/Chapter headings) is obtained, delete the override's rescue path and re-run for "high" quality.
- Similar pattern may exist in other OCR'd classics; consider generalizing page-group fallback.

## Files Touched
- `scripts/build_structured_library.py`
- `knowledge-graph/structured/Jataka_Parijata.json`
- `knowledge-graph/patches/patch-Jataka_Parijata.json`
- `knowledge-graph/patches/node-chapter-map.json` (canonical)
- `knowledge-graph/patches/COVERAGE_MATRIX.json`
- `knowledge-graph/patches/RUN_LOG.txt`
- `knowledge-graph/JATAKA_PARIJATA_FIX.md` (this file)

All changes preserve existing behavior for other books.
