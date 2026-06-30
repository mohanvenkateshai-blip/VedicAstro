# Learn Reader Hard Verification + Deploy Report
**Date:** 2026-06-30  
**Agent:** Learn Reader Hard Verification + Deploy Agent (generalPurpose)  
**Context:** Post multi-agent wave (structured Gyan + KE node mapping + portal integration). Priority #8 "Deploy + hard verification" not previously evidenced as executed.

## Scope
End-to-end verification of:
- structured JSON (build_structured_library.py output) → patch (per-book + consolidated) → (local FS + Supabase if avail) → portal Learn reader render
- For 6 books (mix high-quality handbooks + post-fix classic + classics):
  1. Ashtakavarga_System_Comprehensive_Handbook
  2. Jaimini_Sutras (post-fix)
  3. Brihat_Parasara_Hora_Sastra_Vol_1
  4. Phaladeepika_English_Translation
  5. Vedic_Astrology_Panchang_Handbook
  6. Prasna_Marga_Part_2 (contrast)

Assertions checked:
- Correct chapter counts / TOC presence
- Stable chapter + section ids for jumps
- Deep link resolution (?chapter=...&section=...)
- Provenance strings ("Sourced from: … (method, conf)") wired in UI
- No junk / repeated titles in nav (for high-quality expectation)
- Graceful fallback when structured / nodes / fullMarkdown missing

## Execution
1. `python3 scripts/verify_structured_books.py --books "..." --deep-test --json`
2. Manual inspection of structured JSON titles, counts, sections, parse_quality.
3. Patch inspection (per-book patch-*.json) for chapter_id alignment + provenance keys.
4. Code audit of portal reader paths: learn/page.tsx, learn/[bookId]/page.tsx, BookReaderClient.tsx, books.ts (loadStructured, chaptersFromStructured, sectionsFromStructured, enrichChaptersWithNodeIds, buildNodeProvenanceMap).
5. `cd portal && npm run typecheck && npm run build` (with dummy Supabase envs to satisfy non-null assertions).
6. Raw MD spot-checks for intended structure.
7. Supabase availability: not present locally (no .env.local with SUPABASE_*); verified graceful handling in UI.

## Verification Results by Book

### 1. Ashtakavarga_System_Comprehensive_Handbook (high-quality handbook, has dedicated patch)
- **Python verify:** PASS (with gaps)
  - chapters=49 | patched=49 | provenance=OK | deep=OK | ke_smoke=OK
  - Gaps: duplicate chapter ids (40 unique of 49); patch chapter_ids have zero overlap with structured chapter ids (ID scheme mismatch)
- **Observed chapter count / TOC:** 49 chapters, 13 sections total. parse_quality=medium.
  - First titles: "THE ASHTAKAVARGA SYSTEM IN JYOTISH", "An Authoritative Reference Manual...", "Planet Matrix (BAV)", "Total Auspicious Bindus Allocated", "Functional Focus".
  - Intended structure (from raw): 1. Foundations..., 2. Core Mechanics..., 3. Mathematical Matrix..., with .1 subsections. Documented expectation during wave: 8 ch / 13 sec.
  - Current on-disk is over-segmented (promoted internal headings / table fragments).
- **ID jumps / deep links:** Sampled first ch + first sec resolved in simulation. Client uses id-based DOM lookup + title fallback.
- **Provenance:** Patch entries exist with hierarchy_path, method, confidence. Per-node provenance renders in UI. Per-chapter attachment in reader fails due to id mismatch (enrich uses exact ch.id match against patch chapter_id like "ch-1").
- **Junk in nav:** No classic OCR junk. But not the clean 8-chapter handbook nav users expect.
- **Graceful fallback:** Yes (fullMarkdown slice still works via start/end_line; nodes fall back to default view).
- **Verdict:** Partial. Structured exists and is usable, but regressed from wave gold standard. Patch alignment broken for this book.

### 2. Jaimini_Sutras (post-fix classic, high priority)
- **Python verify:** PASS (cleanest)
  - chapters=10 | patched=676 | provenance=OK | deep=OK
  - No gaps reported.
- **Observed:** parse_quality=high. Chapters are logical "Adhyaya 1 Pada 1", "Adhyaya 1 Pada 2", ..., "Adhyaya 2 Pada 3". 0 repeated titles. Sections present (sutra-level).
- **ID jumps / deep links:** First ch + first sec (including Devanagari) resolved. Ids stable.
- **Provenance:** 676 patch entries. Hierarchy paths should attach.
- **Junk:** None detected. Post-fix succeeded.
- **Portal render note:** Special-cased in learn/page.tsx and has dedicated /learn/jaimini + /api/learn/jaimini route that fetches nodes directly (bypasses the structured BookReaderClient path). The high-quality structured TOC is not exercised for Jaimini in the UI.
- **Verdict:** PASS on data quality. FAIL on integration (does not use the new structured reader).

### 3. Brihat_Parasara_Hora_Sastra_Vol_1 (classic, dedicated patch)
- **Python verify:** PASS (with gaps)
  - chapters=281 | patched=1889 | provenance=OK | deep=OK
  - Gaps: duplicate chapter ids (268 unique of 281); patch chapter_ids zero overlap with structured ids.
- **Observed:** Some short/junk titles present (e.g. "This remainder (3) is multiplied...", "[TO BE CONCLUDED]", truncated OCR lines). parse_quality not high.
- **Deep links:** Sampled ch + sec resolved.
- **Provenance:** Patch exists (explicit + phrase methods). Attachment broken by id mismatch (patch uses "ch-3" style; structured uses slug ids like "ch-maharshi_parasaras").
- **Junk:** Present in tail of list.
- **Verdict:** Usable at scale but noisy TOC. Patch/structured id alignment required.

### 4. Phaladeepika_English_Translation (classic + patch, clean ID alignment in patch)
- **Python verify:** PASS (with gaps)
  - chapters=38 | patched=1200 | provenance=OK | deep=OK
  - Gaps: duplicate chapter ids (30 unique of 38).
  - ch_id_overlap=19/19 (good for this book).
- **Observed titles:** Some truncated or odd: "V-8.", "II-37.", "PPE, भि", "The nature and characteristics of the several". Dup ids.
- **Deep:** Sample resolved.
- **Provenance:** Good overlap means per-chapter nodeIds will attach for matched chapters.
- **Verdict:** Best classic alignment of the set. Still has title quality issues.

### 5. Vedic_Astrology_Panchang_Handbook (small high-quality handbook)
- **Python verify:** PASS
  - chapters=5 | patched=0 | deep=OK
  - Gap: no patch entries matched (not included in mapper run).
- **Observed:** 5 clean chapters with sensible titles ("The 27 Nakshatras...", "Tithis...", "Auspicious..."). No sections.
- **Deep links:** Resolved.
- **Provenance:** None (no patch) — graceful (no "From:" noise).
- **Verdict:** PASS for what it is. Would benefit from a mapping pass for node provenance.

### 6. Prasna_Marga_Part_2 (contrast)
- **Python verify:** FAIL
  - chapters=12 | patched=0 | deep=FAIL (section ambiguity)
  - Gaps: duplicate ch ids; no patch; deep section id not resolvable/ambig.
- **Verdict:** Not production-ready for reader without fixes.

## Cross-Cutting Findings
- **Duplicate chapter ids:** Common (Ashtakavarga 9, BPHS 13, Phaladeepika 8, Prasna 1). The deep resolver takes first match and reports ambiguity only when sampling hits dups for the chosen sample. Real nav can have unstable jumps if user targets a dup id.
- **Patch vs structured id scheme mismatch:** 
  - Patches often use short "ch-N" or "ch-1.1" ids (from mapper or explicit).
  - Structured uses title-derived slugs (e.g. "ch-the_ashtakavarga_system_in_jyotish").
  - Result: enrichChaptersWithNodeIds returns no nodeIds for most chapters; sidebar "From:" per chapter is missing for those books. Per-node provenance still works.
  - Phaladeepika had overlap; others did not.
- **Jaimini bypass:** High-quality post-fix structured exists, but the prominent /learn/jaimini entry point uses a node-list UI and a separate API. The general structured reader is not validated for it.
- **Ashtakavarga regression:** Wave docs + IMPROVEMENTS.md state "8 chapters, 13 sections, high quality, unchanged". Current file: 49 chapters, 13 sections, parse_quality=medium. The builder re-segmented it (or a later full rebuild overwrote). Patch was generated against a different chaptering.
- **Provenance UI:** Code paths exist in BookReaderClient (per-node and chapter-level "From: hierarchy_path (mapped via X conf Y)"). Renders when data present.
- **Graceful fallback:** Multiple layers in [bookId]/page.tsx and BookReaderClient:
  - structured present → use it + slice by line ranges
  - else fullMarkdown parse
  - else node fallback
  - try/catch around listBooks + notFound on loadBook
  - Sections optional.
- **No junk titles (high quality expectation):** 
  - Jaimini (post-fix): clean.
  - Panchang handbook: clean.
  - Ashtakavarga: no OCR junk but wrong granularity.
  - BPHS / Phaladeepika: short/truncated/odd titles present.
- **Supabase (if avail):** Not available in this env. listCorpusSources / loadBook / fullMarkdown download will fail or return empty; UI catches and shows "0 nodes" / empty library or falls back to local structured where possible. Structured + patch loading is pure FS and works offline.

## Deploy Readiness (newbooks-v1)
- **Build:** ✅ SUCCESS (`npm run build` completed; routes `/learn`, `/learn/[bookId]`, `/learn/jaimini`, `/api/learn/jaimini` generated; static pages ok).
- **Typecheck:** ✅ Clean.
- **Lint:** ⚠️ Pre-existing issues (many `@typescript-eslint/no-explicit-any`, one Function type). Does not block build. 70 problems total (not introduced by structured work).
- **Env for newbooks-v1:**
  - Required at runtime (not just build): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (hard `!` in supabase.ts; corpus.ts, books.ts, learn pages all import paths that reach Supabase).
  - CVCE_BASE_URL used for calc endpoints (not primary for Learn reader).
  - .env.example does not document the Supabase vars needed for corpus (only DATABASE_URL, CVCE, auth, encryption). This is a documentation gap.
  - For full reader experience: corpus_sources + graph_nodes (graph_version='newbooks-v1') + corpus-vault objects must exist. Structured chapters + patches are checked into the repo and load from FS.
- **Static / dynamic:** Learn pages are dynamic (fetch Supabase + storage). Build produces the shells.
- **Special Jaimini route:** `/api/learn/jaimini` is a thin proxy to getBookTextNodes; no structured used.
- **Overall deploy status:** Code is deployable. Runtime will show empty library or node-only fallbacks until Supabase newbooks-v1 data is provisioned and envs are set. Structured TOCs will light up for books that have local JSONs as soon as Supabase calls are satisfied or additional graceful paths are added.

## Exact Issues + Owning Agent Types (for remediation)
1. **Ashtakavarga structured over-segmentation / regression to 49 ch**  
   Owning: Structured Library Builder / Parser Refiner (generalPurpose or explore) + build_structured_library.py owner. Re-run with stricter heading promotion + per-book profiles or manual chapter list.

2. **Patch chapter_id vs structured id mismatch (zero overlap for most books)**  
   Owning: Node Mapper (map_nodes_to_structured.py) + Learn Reader Integration (books.ts enrichment).  
   Fix options: 
   - Make mapper emit chapter_ids that match the final structured slugs (or store both).
   - Add fuzzy/normalized lookup in enrichChaptersWithNodeIds and buildNodeProvenanceMap.
   - Re-generate patches after locking the structured chapter ids.

3. **Jaimini high-quality structured not used by its dedicated reader**  
   Owning: Learn Reader + Structured Chapters Integration Engineer. Wire the normal [bookId] reader (or a structured variant) for Jaimini, or at minimum use chaptersFromStructured for the sidebar.

4. **Duplicate chapter ids in structured (affects deep link stability)**  
   Owning: Parser Refiner + build_structured_library.py. Add post-dup merge or id suffixing; tighten patterns that create micro-chapters.

5. **Lingering junk / truncated titles in classics (BPHS Vol1, Phaladeepika, etc.)**  
   Owning: Structured Library Quality Auditor + Parser (add stronger title quality filters, length guards, denylists, TOC guards).

6. **Missing patch coverage for some high-value handbooks (Panchang, Prasna, etc.)**  
   Owning: Bulk Mapper / map_nodes_to_structured agent. Include in next coverage run; or accept provenance=N/A for small books.

7. **Supabase env not documented for corpus / newbooks-v1**  
   Owning: Portal / DevEx (update .env.example + docs; consider soft-fail import or build-time guard).

8. **Pre-existing any lint noise** (non-blocking)  
   Owning: Portal maintainers (can be cleaned opportunistically).

## Recommendations (parallelizable)
- Rebuild structured for Ashtakavarga (and other handbooks) with a "handbook" profile that trusts "N. Title" + "##" only and rejects short/heading-like fragments. Assert chapter count ≈ 8.
- Align mapper output chapter_ids to the authoritative structured ids (or emit a secondary id_map). Re-run patches for the 5+ books.
- Un-special-case Jaimini or add a structured code path to its reader so the post-fix work is visible.
- Add a small runtime smoke in the portal (e.g. /api/status or a test page) that loads 2–3 structured books + patches and asserts chapter counts + a deep link sample.
- Extend verify_structured_books.py to also assert "chapter count within expected band" for known-good books and "no title shorter than X or matching denylist".
- Document + provision Supabase newbooks-v1 requirements for deploy.

## Summary
- **Data layer (Python + FS):** 5/6 PASS per the existing verifier; Jaimini is the star (post-fix). Ashtakavarga regressed; several id alignment and dup issues.
- **Portal render paths:** Code is correct and defensive; build passes. Real reader experience for structured + provenance is only partially realized due to id mismatches and the Jaimini bypass.
- **Deploy:** Build + typecheck ready. Needs Supabase env + newbooks-v1 corpus data for nodes/full text. Structured chapters will appear as soon as FS JSONs are present (they are).
- **Hard verification completed:** Assertions exercised via script + code inspection + raw cross-check. No browser screenshots possible in this session; visual behavior inferred from component logic (id targets, sections slice, provenance blocks, fallbacks).

*Report generated by Learn Reader Hard Verification + Deploy Agent. Act on the owning agent types above to close gaps.*
