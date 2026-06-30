# Structured Gyan Library — Audit Report

**Corpus:** `knowledge-graph/structured/*.json` (61 files) 
**Parser:** `scripts/build_structured_library.py` 
**Cross-ref:** `knowledge-graph/raw/*.md` (61 matching sources) 
**Date:** 2026-06-30

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall health score** | **62 / 100** (Fair — usable for modern handbooks, unreliable for OCR classics) |
| Total books | 61 |
| Avg chapters / book | 139.2 (median **34**) — mean skewed by Brihat Samhita (2,066 ch) |
| Avg “real” chapters / book | 116.3 (median **26**) |
| Books with **<3 real chapters** | **11 (18.0%)** |
| Books with **0 chapters** | **6 (9.8%)** |
| Books with **0 sections total** | **29 (47.5%)** |
| Books with **>50% chapters having 0 sections** | **51 (83.6%)** |
| Books with any sections | 32 (52%) |
| Total sections corpus-wide | 641 (avg 20.0 when >0) |
| Per-book health (median) | 80 |
| Per-book health (mean) | 67.2 |

**Verdict:** The structured library works well for **author-written markdown handbooks** with `N. Title` numbering and `##` subsections. It **fails systematically** on OCR’d classical PDFs where page headers (`N JAIMINISUTRAS`), TOC lines, and numbered sentences are mistaken for chapters. Section detection is almost absent for classics (97% of classic chapters have 0 sections).

---

## Parser Logic (Known Behavior)

From `scripts/build_structured_library.py`:

```66:76:scripts/build_structured_library.py
CHAPTER_PATTERNS = [
 re.compile(r"^(?:Chapter|Ch\.?|Ch)\s*[:\-]?\s*(\d+[\.\d\-]*)[\.\s:\-–—]*(.+?)$", re.I),
 re.compile(r"^(\d{1,2}(?:\.\d+)?)\.\s+([A-Z][^\n]{3,120})$"), # 1. Foundations , 3.1 Foo
 re.compile(r"^(\d+)\s+([A-Z][A-Z\s\-–:']{5,80})$"), # 1 THE CREATION (all caps style)
 re.compile(r"^(Sutra|Sūtra)\s*(\d+[\.\d\-]*)[\s:\-]*(.*)$", re.I),
]

SECTION_PATTERNS = [
 re.compile(r"^(\d+\.\d+(?:\.\d+)?)\s+(.+)$"),
 re.compile(r"^(#{2,6})\s+(.+)$"), # ## , ### etc.
]
```

**Critical behaviors:**
1. `## Page N` headers are **skipped** (line 146–147) — good for page dumps, bad when that’s the *only* structure.
2. Pattern 3 (`^\d+\s+ALL_CAPS`) matches OCR **page running headers** → repeated junk chapters.
3. Pattern 2 (`^\d+\.\s+[A-Z]...`) matches **TOC lines, letter numbering, OCR sentences** → micro-chapters (2–10 lines).
4. Synthetic fallback (lines 201–217) only fires when `len(chapters) < 2` and finds `^\d+\.\s+.{5,120}$` — produces 0 or 1 chapter for most flat files.
5. `##` non-Page headers promote to sections/chapters but are never used as chapters when Page markers dominate.

---

## Junk / Repeated Title Prevalence

| Junk type | Corpus-wide count | Primary victims |
|-----------|-------------------|-----------------|
| Repeated OCR header (`JAIMINISUTRAS`, `HORASARA`, etc.) | 278 | Jaimini, Hora Sara, Bhavartha, Vedanga |
| Number-only title (`"6"`, `"4"`, `"0"`) | 540 | BPHS Vol 2, Saravali, classics |
| All-caps short fragment | 123 | Various OCR texts |
| Very short title (<5 chars) | 65 | Scattered |

**Top repeated titles (corpus-wide):**

| Count | Title |
|------:|-------|
| 128 | `HORASARA` |
| 76 | `JAIMINISUTRAS` |
| 47 | `6` |
| 41 | `BHAVARTHA RATNAKARA` |
| 30 | `4` |
| 25 | `VEDANGA JYOTISA` |

---

## Deep Dive: `Jaimini_Sutras.json` (Worst Core Classic)

| Field | Value |
|-------|-------|
| Chapters | 141 |
| Sections | **0** (100% empty) |
| Repeated `JAIMINISUTRAS` | **76 / 141 (54%)** |
| Devanagari chapter numbers | 35 (e.g. `१0`, `११`, `२५`) |
| First chapter `start_line` | **703** — **702 lines of intro/front matter lost** |
| Avg chapter span | 57.8 lines (median 53) |
| Chapters with span <5 lines | 17 |

**Root cause:** Raw file has 219 `## Page N` markers and 188 lines containing `JAIMINISUTRAS`. Pattern 3 matches running headers like `2 JAIMINISUTRAS` (raw L704) — the number is a **page/sutra index**, not a chapter.

**Examples of bad extractions:**

| Line | Number | Title | Issue |
|------|--------|-------|-------|
| 703 | `2` | `JAIMINISUTRAS` | Page header, not chapter |
| 1066 | `१0` | `JAIMINISUTRAS` | Devanagari digit + header |
| 1142 | `Sutra` | `9` | Sutra pattern inverted (title=`9`) |
| 1174 | `११` | `HET: कढादि। नः भामः` | OCR garbage as title |
| 3519 | `6` | `JATMINISUTRAS` | Typo variant of header |

**Raw vs structured:** Raw has 1 H1, 219 H2 (all pages), 65 `N. Title` lines, 77 all-caps header lines, 4 sutra lines. Real structure is **Page → Sutra blocks (`Su. N`)**, not `N JAIMINISUTRAS`.

**Contrast — `rath_s_jaimini_maharishis_upadesa_sutra.json` (score 100):** 46 chapters, **103 sections**, proper `1.11 Parivrittitraya Drekkana` numbering + `##` TOC fragments. Same domain, modern PDF layout → parses well.

---

## Deep Dive: Other Problem Families

### OCR classics — repeated headers
| Book | Chapters | Max repeat | Junk % | Notes |
|------|----------|------------|--------|-------|
| `Hora_Sara` | 349 | 128× `HORASARA` | ~38% junk titles | Same pattern as Jaimini; also `"CHAPTER 1"` + number-only titles |
| `Bhavartha_Ratnakara` | 49 | 41× `BHAVARTHA RATNAKARA` | 92% junk | OCR sentences like `3. Stanza 9 says that huja...` become chapters |
| `Vedanga_Jyotisa_Lagadha` | 100 | 25× `VEDANGA JYOTISA` | TOC fragmentation | Chapters are 2-line TOC entries (`2. Importance of Astronomy .. . . oe 35`) |

### Over-segmentation — TOC/OCR numbered lines
| Book | Chapters | Raw lines | Trigger |
|------|----------|-----------|---------|
| `Brihat_Samhita` | **2,066** | 21,715 | 2,043 TOC lines `1. Iutrodnetory 1/26, On Ashadhi Yoga 131` |
| `Brihat_Parasara_Hora_Sastra_Vol_1` | 800 | 30,473 | Numbered + OCR |
| `Phaladeepika_Mantreswara` | 761 | 11,303 | Numbered lines |
| `Gochar_Phaladeepika_Pulippani` | 646 | 17,051 | Numbered lines |

### Zero-chapter books (complete parse failure)
| Book | Raw lines | Why parser finds nothing |
|------|-----------|--------------------------|
| `Do_Ghati_Muhurta_Reference_Mysuru_Athlone` | 853 | Tables, no `N. Title` / `Chapter` |
| `Panchang_analysis_medhraj` | 109 | Only `## Page N` (skipped) + verse text |
| `Tithi Astrology Master Reference Guide` | 1,483 | Markdown tables, no numbered chapters |
| `Tithi–Vāra Yoga Handbook` | 162 | Bold headings, no patterns |
| `jaimini_astrology_calculation_of_mandook_dasha...` | 314 | `## Page N` only |
| `muhurta_yogas` | 451 | `## Page N` + yoga names (`Siddha "accomplished" Yoga:`) — no match |

### Single-chapter / near-empty
| Book | Chapters | Cause |
|------|----------|-------|
| `Jataka_Chandrika` | **1** | Only one `^\d+\.\s+` line in entire raw: `24. JATAKACHUNDRIKA.` (L1109) |
| `Jataka_Tatva_Mahadeva` | 2 | Number-only titles `35`, `4` |

### Digests (misleading but not empty)
| Book | Chapters | Sections | Issue |
|------|----------|----------|-------|
| `the_jyotish_digest_2005...` | 47 | 35 | Letter list items (`4. X prize: In 1996...`) as chapters |
| `the_jyotish_digest_2007...` | 39 | 2 | Repeated `Jyotish Digest ° Oct-Dec 2007` (5×) |
| `the_jyotish_digest_2009...` | 34 | 2 | Article fragments as chapters |

---

## High-Quality Contrast: `Ashtakavarga_System_Comprehensive_Handbook.json`

| Field | Value |
|-------|-------|
| Chapters | 8 |
| Sections | 13 |
| Health score | **100** |
| Chapters with sections | 7/8 |
| Junk titles | 0 |

**Why it works:** Raw uses clean `1. Foundations and Philosophy...` lines (8 matches) plus `##` / `N.N` subsections. Parser pattern 2 + section patterns align with author intent.

```
Ch1: Foundations... L8–25 (1 section)
Ch3: Mathematical Matrix... L40–109 (2 sections: BAV, SAV)
Ch8: Special Cases... L286–302 (3 sections)
```

Same pattern for: `vedic_astrology_unified_handbook`, `vedic_yoga_logic_engine`, `Tara_Balam_Muhurta_Handbook`, `Uttara_Kalamrita` (27 ch, 64 sec).

---

## Top 10 Worst Books

| Rank | Book | Score | Why |
|------|------|------:|-----|
| 1 | `Brihat_Parasara_Hora_Sastra_Vol_2` | 20 | 598 ch, 99.7% zero-section, 33× title `"6"`, 168 junk all-caps/number titles |
| 2 | `Hora_Sara` | 20 | 128× `HORASARA`, number-only titles (`"3"`, `"5"`), 99.7% zero-section |
| 3 | `Jataka_Chandrika` | 20 | **1 chapter** for 3,486-line book — entire text in one blob |
| 4 | `Jataka_Tatva_Mahadeva` | 30 | 2 chapters, 0 real, number-only titles |
| 5–10 | Six zero-chapter books | 30 | No pattern match at all (see table above) |
| 11 | `Jaimini_Sutras` | 35 | 76× repeated header, 0 sections, misses 702-line intro |
| 12 | `Vedanga_Jyotisa_Lagadha` | 35 | TOC micro-chapters, 25× header repeat |
| 13 | `Bhavartha_Ratnakara` | 35 | 41× header repeat, OCR sentence chapters |

**Example bad titles + line numbers:**

```
Hora_Sara L339 #2 "HORASARA"
Hora_Sara L386 #1 "3" (was "CHAPTER 1 3" in raw)
BPHS_Vol_2 many #6 "6" (33 repetitions)
Jaimini_Sutras L703 #2 "JAIMINISUTRAS"
Bhavartha L622 #3 "Stanza 9 says that huja can become Yogaharaka if"
Brihat_Samhita L398 #1 "Iutrodnetory 1/26, On Ashadhi Yoga 131" (TOC junk)
```

---

## Books with Excellent Structure

**Tier A — score 100, sections present, meaningful titles:**

- `Ashtakavarga_System_Comprehensive_Handbook`
- `vedic_astrology_unified_handbook`
- `vedic_yoga_logic_engine`
- `Uttara_Kalamrita` (27 ch / 64 sec)
- `Tara_Balam_Muhurta_Handbook`
- `rath_s_jaimini_maharishis_upadesa_sutra` (46 ch / 103 sec)
- `Crux_of_Vedic_Astrology_Timing_of_Events1` (46 ch / 98 sec)
- `Bhava_and_Graha_Balas_BVRaman_1996` (104 ch / 65 sec)
- `Prasna_Marga_Part_1`, `Prasna_Marga_Part_2`
- `Phaladeepika_English_Translation`
- `patel_cs_aiyar_cas_ashtakavarga`
- All three `the_jyotish_digest_*` (usable but not magazine-faithful)

**Tier B — high chapter count, low sections but structurally coherent numbering:**

- `Introduction_to_Vedic_Astrology_Sanjay_Rath` (283 ch, 32 sec)
- `Brihat_Parasara_Hora_Sastra_Vol_1` (800 ch, 69 sec)
- `Predicting_Through_Jaimini_Astrology` (282 ch, 3 sec)

---

## Recommendations for `build_structured_library.py`

### CHAPTER_PATTERNS

1. **Denylist running headers** — reject when `title.upper()` in `{JAIMINISUTRAS, HORASARA, BHAVARTHA RATNAKARA, VEDANGA JYOTISA, JATAKACHUNDRIKA, ...}` or when same title repeats >3× in a book.

2. **Tighten pattern 3** — require title length >10 chars OR not equal to a known header token:
 ```python
 # Reject: ^\d+\s+JAIMINISUTRAS$ 
 # Accept: ^\d+\s+THE CREATION OF THE UNIVERSE$
 ```

3. **Normalize Devanagari digits** before matching (`१` → `1`).

4. **Add classical patterns:**
 ```python
 r"^CHAPTER\s+([IVXLC\d]+)\s*[:\.\-]?\s*(.*)$"
 r"^(?:Adhyaya|Adhyāya|Pada|अध्याय)\s+(\d+)"
 r"^(?:INTRODUCTION|FOREWORD|PREFACE)\s+TO\s+(\w+)" # for Jaimini intro block
 ```

5. **TOC guard for pattern 2** — reject lines containing page refs (`\d{1,3}\s*$`, `\d+/\d+`, `oe 35`, trailing `\. \. \.`); reject if chapter span < 5 lines unless title matches `Chapter`.

6. **Use non-Page `##` as chapters** when `## Page` is the dominant H2 pattern:
 ```python
 # If >50% of ## lines are Page markers, promote other ## or ### headers
 ```

7. **Book-type profiles** — `sutra_ocr`, `handbook`, `digest`, `table_reference` with per-type pattern sets.

### SECTION_PATTERNS

1. **Sutra/stanza lines** (critical for Jaimini classics):
 ```python
 r"^(?:Su\.|Sutra|Sūtra)\s*\.?\s*(\d+)"
 r"^(?:Stanza|Shloka|Śloka|VERSE)\s+(\d+)"
 r"^॥\s*(\d+)\s*॥"
 ```

2. **Looser numbered subsections** for OCR: `r"^(\d+\.\d+)\s+(.+)"` (already present — extend to `(\d+\.\d+(?:\.\d+)?)` without requiring trailing content quality).

3. **Bold markdown sections:** `r"^\*\*([^*]+)\*\*\s*$"`

4. **Do not skip `##` that follows content** — only skip exact `## Page \d+`.

### Post-processing

1. **Merge consecutive chapters** with identical normalized titles.
2. **Flag `needs_review`** when: `total_chapters < 3`, or `max_title_repeat > 5`, or `total_sections == 0` and `total_chapters > 20`.
3. **Emit metadata:** `parse_quality`, `dominant_failure_mode`, `raw_h1_count`, `suggested_nav_strategy`.
4. **Pre-parse raw** — strip or tag running headers using position (centered short all-caps line between `## Page` blocks).

### Fallback for zero-chapter books

1. Split on `---` or `##` (non-Page) into synthetic chapters.
2. For table-heavy refs (`Do_Ghati_*`, `Tithi*`), create one chapter per major `**heading**` or top-level table.
3. For `muhurta_yogas`, split on yoga family headings (`AUSPISCIOUS VARA/TITHI YOGAS`).

---

## Suggested Lists

### `needs_review` (37 books)

**Critical (unusable nav):**
`Jaimini_Sutras`, `Hora_Sara`, `Bhavartha_Ratnakara`, `Jataka_Chandrika`, `Jataka_Tatva_Mahadeva`, `Vedanga_Jyotisa_Lagadha`, `Brihat_Parasara_Hora_Sastra_Vol_2`, all 6 zero-chapter books

**High (over-segmented / no sections):**
`Brihat_Samhita`, `Brihat_Parasara_Hora_Sastra_Vol_1`, `Phaladeepika_Mantreswara`, `Gochar_Phaladeepika_Pulippani`, `Saravali`, `Graha_Laghava`, `Deva_Keralam_1/2/3`, `Hora_Shastra_Varahamihira`, `Laghu_Parashari`, `Phaladeepika_Mantreswara_1961`, `Vedic_remedies_by_srath_pdf_free`, `Activity_Mapping`, `Bhrigu_Samhita_TMRao`, `Do_Ghati_Muhurta_Comprehensive_Handbook`, `Jyotish_Yoga_Handbook_101`, `Jataka_Parijata`, `Brihat_Jataka`, `Sarvartha_Chintamani`, `FireShot Capture 034...`

### `high_quality` (24 books)

`Ashtakavarga_System_Comprehensive_Handbook`, `vedic_astrology_unified_handbook`, `vedic_yoga_logic_engine`, `Uttara_Kalamrita`, `Tara_Balam_Muhurta_Handbook`, `rath_s_jaimini_maharishis_upadesa_sutra`, `Crux_of_Vedic_Astrology_Timing_of_Events1`, `Bhava_and_Graha_Balas_BVRaman_1996`, `Prasna_Marga_Part_1`, `Prasna_Marga_Part_2`, `Phaladeepika_English_Translation`, `patel_cs_aiyar_cas_ashtakavarga`, `Predict_Effectively_Through_Yogini_Dasha`, `Predicting_Through_Jaimini_Astrology`, `Introduction_to_Vedic_Astrology_Sanjay_Rath`, `wilhelm_ernst_classical_muhurta_jyotish`, `boney_marc_intricate_patterns_of_destiny_how_to_make_accurat`, `the_jyotish_digest_2005/2007/2009`, `Ravi_Yoga_Vedic_Astrology_Guide`, `SBC_Vedha_and_Panchang_Reference_Guide`, `Vedic_Astrology_Panchang_Handbook`, `Vedic_Astrology_Tithi_Guide`, `utpata_mrityu_kana_siddhi_handbook`, `gemini-code-1780093366483`

---

## Category Breakdown

| Category | Books | Avg ch | Avg sec | % ch with 0 sec |
|----------|------:|-------:|--------:|----------------:|
| Handbooks / Guides | 13 | 6 | 4.3 | 66% |
| Classics (BPHS, Jataka, etc.) | 26 | 267 | 6.7 | **97%** |
| Digests | 3 | 40 | 13.0 | 92% |

---

## Priority Fix Order

1. **Jaimini_Sutras** — highest user visibility (`/learn/jaimini`); add sutra-section parsing + header denylist.
2. **Six zero-chapter books** — add `##`/heading fallback (quick win for muhurta/tithi content).
3. **Hora_Sara / Bhavartha / Vedanga** — same header denylist as Jaimini.
4. **Brihat_Samhita / BPHS** — TOC detection guard before accepting pattern 2.
5. **Section patterns for classics** — `Su. N`, `Stanza N`, `॥ N ॥` to populate sections even when chapters stay coarse.

---

## Health Score Methodology

Per-book score (0–100) penalizes: <2 chapters (−40), <3 real chapters (−30), >80% zero-section chapters (−20), max title repeat >5 (−25), >200 chapters (−15), junk title ratio >30% (−20).

**Corpus score 62** = weighted by severity of failures in core classics (Jaimini, BPHS, Hora Sara) despite many handbooks scoring 100.

---

*This is a read-only diagnosis. Switch to Agent mode to implement parser fixes in `scripts/build_structured_library.py` and regenerate structured JSON.*

---

## Regenerated Audit Snapshot — 2026-06-30 03:55 (Audit Regenerator + Rebuilder wave)

**Run by:** Audit Regenerator + Quality Rebuilder + Visualizer Provenance agent  
**Trigger:** Structured auditor reported stale health 62 (19/61 parse_quality), 4 books <3ch, Hora_Sara 1-ch collapse.  
**Actions:** 
- Extended/ran `scripts/build_structured_library.py --all` + targeted with parser guard + rescue improvements.
- Stamped `parse_quality` on 100% of books.
- Re-tuned overrides for Jataka_Chandrika / Jataka_Tatva / Hora_Sara (min_gap, running header dot-comma, rescue dedup by num, first-seen).

### Current Metrics

| Metric | Value |
|--------|-------|
| Overall health | **77 / 100** |
| parse_quality coverage | **61/61** (high: 3, medium: 57, needs_review: 1) |
| Total books | 61 |
| Books with 0 chapters | 1 |
| Books with <3 chapters | 5 |
| Books with 0 sections | 28 |
| Total chapters | 12150 (avg 199.2, median 119) |
| Total sections | 1520 |
| Median per-book health | 80 |
| Mean per-book health | 76.9 |

### High Quality (sample)
Crux_of_Vedic_Astrology_Timing_of_Events1, Jaimini_Sutras, vedic_astrology_unified_handbook, vedic_yoga_logic_engine

### Needs Review / Low Chapter (current)
Activity_Mapping, Jataka_Tatva_Mahadeva, gemini-code-1780093366483, Tithi–Vāra Yoga Handbook, Phaladeepika_English_Translation

**Books rebuilt in this wave (targeted + all):** Jataka_Chandrika, Jataka_Tatva_Mahadeva, Hora_Sara, Brihat_Samhita, Tithi* handbooks, + full --all pass for stamping.

**Visualizer provenance work:** (see separate update to scripts/visualize-knowledge-graph-d3.html)

*Health methodology unchanged from prior section. Numbers reflect post-fix parser on 2026-06-30.*
