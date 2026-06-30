# Structured Chapter Extraction & Node Mapping Improvements (2026-06-30)

## Goals
Raise precision of chapter extraction and node→chapter provenance for the 61-book library so the Learn reader and KE have trustworthy structure.

## Root Causes Diagnosed (from Jaimini_Sutras.json and raw sources)
- Greedy all-caps pattern `^(\d+)\s+([A-Z][A-Z...]{5,80})$` matched page running headers ("2 JAIMINISUTRAS", "4 The Creation").
- No Devanagari numeral support → ids like "ch-१0".
- "Chapter 1" / "Chapter - 7" and "Su. N" variants not reliably captured.
- ADHYAYA/PADA structural markers for sutra texts ignored.
- Synthetic fallback and promotion too loose on body text / TOC.
- Mapper junk detection missed "JAIMINISUTRAS"; no review signal.

## Targeted Changes (build_structured_library.py)
- Added `normalize_num` + Devanagari map; roman small-value support.
- `is_likely_running_header`, `is_likely_sutra_aphorism`, `title_looks_like_prose`, `looks_like_junk_chapter_title` heuristics.
- Tightened CHAPTER_PATTERNS (optional title for Chapter N, tolerant ADHYAYA with OCR variants on PADA, broader Sutra).
- SECTION_PATTERNS extended with sutra aphorism forms for nesting.
- Early skips for page headers, running headers, TOC noise, aphorisms (for chapters).
- Post-prune for sutra-style books: keep Adhyaya/Pada chapters as primary structure.
- `parse_quality`: "high" | "medium" | "needs_review" added to structured output.
- Stricter synthetic fallback.

## Targeted Changes (map_nodes_to_structured.py)
- Expanded `_is_junk_title` (JAIMINISUTRAS, CREATION, etc.).
- `phrase_lookup` improved token filtering.
- `enrich_node` emits `review_needed` when conf low, chosen chapter looks junk, or upstream parse_quality == "needs_review".
- Explicit location matching tolerates normalized numbers.

## Results (Jaimini_Sutras)
Before: 141 chapters, 76 titled "JAIMINISUTRAS", 35 Devanagari nums, 141 zero-section chapters, parse garbage.
After: 8 logical Adhyaya/Pada chapters (e.g. "Adhyaya 1 Pada 1"), 214 sections (sutra aphorisms), parse_quality: high. Node mappings now resolve to real chapters like ch-11 / Adhyaya 1 Pada 1.

Ashtakavarga (good contrast) unchanged: 8 chapters, 13 sections, high quality.

## Usage
python3 scripts/build_structured_library.py --books "Jaimini_Sutras,..."
python3 scripts/map_nodes_to_structured.py --books "Jaimini_Sutras" --dry-run

The patch now includes `review_needed` for downstream triage.

## Notes / Future
- Some Padas missing due to heavy OCR variance ("Papa"/"Papy"); can be recovered with manual list or fuzzy Adhyaya scan.
- Section titles from Devanagari lines are noisy; can be improved with transliteration pass.
- Consider per-book "sutra_mode" flag or frontmatter detection for stronger pruning.

## 2026-06-30 — Jataka_Parijata OCR rescue
- Raw had 0 chapter markers (only 483 irregular `## Page N` + heavy garbage). Prior run produced 178 junk titles ("Sisk we wept ee)" etc.).
- Added BOOK_OVERRIDES + junk heuristics + page-group rescue in `build_structured_library.py`.
- Result: 49 "Pages X–Y" chapters, `parse_quality: "medium-improved"`, 483 patches with `review_needed: 0`.
- Canonical union, COVERAGE_MATRIX, RUN_LOG updated. See `JATAKA_PARIJATA_FIX.md`.
- /learn nav now usable (page ranges). Semantic titles require better source.
- Pattern may apply to other OCR page-dump classics.
