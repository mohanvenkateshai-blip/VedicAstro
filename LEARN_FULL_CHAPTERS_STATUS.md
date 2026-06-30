# LEARN_FULL_CHAPTERS_STATUS

**Generated:** 2026-06-30  
**Books tested:** 7 (mix of handbooks + hard OCR classics)  
**Overall:** 6/7 PASS

## Verification matrix (per book)

| Book                                      | Structured loads | Raw MD loads | Chapters presented | 1+ full chapter slice works | Notes |
|-------------------------------------------|------------------|--------------|--------------------|-----------------------------|-------|
| Ashtakavarga_System_Comprehensive_Handbook | YES (8 ch, 13 sec) | YES (303 ln) | 8 (structured)    | YES (1994 chars)           | Pilot; clean |
| Jaimini_Sutras                            | YES (10 ch, 659 sec) | YES (8988 ln) | 10 (structured)   | YES (59k chars)            | Section-heavy |
| Brihat_Parasara_Hora_Sastra_Vol_1         | YES (55 ch)      | YES (30k ln) | 55 (structured)   | YES (346 chars)            | Classic |
| Saravali                                  | YES (24 ch)      | YES (15k ln) | 24 (structured)   | YES (5.3k chars)           | Classic; 0 sec |
| Phaladeepika_Mantreswara                  | YES (157 ch)     | YES (11k ln) | 157 (structured)  | YES (2.4k chars)           | High chapter count |
| Brihat_Samhita                            | YES (43 ch)      | YES (21k ln) | 43 (structured)   | YES (21k chars)            | Tough OCR |
| Jataka_Tatva_Mahadeva                     | NO (0 ch)        | YES (39k ln) | 21 (fallback)     | NO                         | Zero-chapter gap |

**Pass rate:** 6/7 books have authoritative structured chapters + working content slices. 1 known gap (Jataka_Tatva_Mahadeva).

## Fallback ugliness (parseMarkdownToSections on raw MD)

Fallback is **ugly on all OCR-heavy classics** (hundreds of "Page N" junk titles + micro-sections). Structured path suppresses this.

| Book                            | Fallback chapters (filtered) | Fallback junk titles | Very short (<3 lines) |
|---------------------------------|------------------------------|----------------------|-----------------------|
| Ashtakavarga (handbook)         | 9                            | 0                    | 0                     |
| Jaimini_Sutras                  | 273                          | 219                  | 14                    |
| BPHS Vol 1                      | 896                          | 657                  | 132                   |
| Saravali                        | 333                          | 347                  | 44                    |
| Phaladeepika_Mantreswara        | 725                          | 265                  | 6                     |
| Brihat_Samhita                  | 2202                         | 484                  | 136                   |
| Jataka_Tatva_Mahadeva           | 21                           | 429                  | 1                     |

**No "Frontmatter"/"H1" junk appears in any structured chapter titles** (0 across the 6 good books). All structured chapters are clean.

## Suggested minimal parser improvements (only if fallback path must be used)

In `portal/src/lib/books.ts` `parseMarkdownToSections`:
- Expand junk filter to `Page \d+`, bare roman numerals, "Contents", "Index", lone "Chapter".
- Drop sections whose body (excl. heading) has <2 non-empty lines or <80 prose chars.
- Merge micro-sections under nearest preceding substantial heading when >N micro-sections detected.

These are **not required** while structured data is present and preferred.

## Supporting checks executed
- `scripts/verify_structured_books.py` (6/7 PASS, deep links OK where chapters>0).
- `portal/scripts/verify-structured-path.mjs` (Ashtakavarga: 8→21 flat entries, sectionsFromStructured produced 21 blocks, node enrichment works).
- Direct structured + raw loads + `sectionsFromStructured` slice for all 7.
- Portal `data/structured/*.json` parity with `knowledge-graph/structured/` (exact chapter count match for all 7).
- Zero "Frontmatter" junk in structured chapters; fallback junk quantified.

## Known gaps / follow-ups
- Jataka_Tatva_Mahadeva (and any other 0-chapter books) need re-run of structured build / node-chapter mapping.
- Several patched books have low chapter_id overlap (Jaimini ~2%, BPHS ~16%, Brihat_Samhita ~22%); does not affect chapter content slices, only node provenance labels.
- Prod smoke (2026-06-30) shows stale deploy (no jaimini redirect, missing structured signals on Jaimini/Hora). Local structured+slice verification passes; redeploy needed for user-visible effect.
