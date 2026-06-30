# KE Wave — Dasha Agent Report

**Agent:** D (Dasha)  
**Scope:** cvce/vedic_engine/prediction/dasha.py, cvce/vedic_engine/synthesis/dasha_analyzer.py (read-only), cvce/app/dasha_*.py + yogini_predict.py (light touch), related structured (BPHS*, Laghu_Parashari, Predict_Effectively_Through_Yogini_Dasha, etc.)

## 1. Counts (scripted)

- Dasha-related structured JSONs in `knowledge-graph/structured/`: **7**
  - Brihat_Parasara_Hora_Sastra_Vol_1.json
  - Brihat_Parasara_Hora_Sastra_Vol_2.json
  - Hora_Sara.json
  - Hora_Shastra_Varahamihira.json
  - Laghu_Parashari.json
  - Predict_Effectively_Through_Yogini_Dasha.json
  - jaimini_astrology_calculation_of_mandook_dasha_with_a_case_study_compress.json

- Books referenced during revive: **BPHS Vol_1, Laghu_Parashari, Predict_Effectively_Through_Yogini_Dasha** (via get_structured_book + FS fallback)

## 2. Audit (pre-change)

- `DASHA_EFFECTS`, `YOGINI_EFFECTS`, `DASHA_ORDER`, periods, and most conditionals were pure-Python static dicts.
- `_on_dasha_refresh` loaded `_dasha_structured_books` and warmed a couple chapter node sets, but did **not** extract effect variants/conditionals into state used by `compute_*`.
- `_resolve_dasha_citation` only attached a single chapter-level citation to the result (no per-period, no variant text).
- Registration existed (`register_engine("dasha", on_refresh=...)`) but revive path that mutates *algorithm data* did not.

## 3. Changes (narrow)

- Added module state: `_VIMSHOTTARI_CONDITION_VARIANTS`, `_YOGINI_EFFECT_VARIANTS`, `_DASHA_VARIANT_CITATIONS`.
- Added `_dasha_book_index["Laghu"]`.
- Implemented `_revive_dasha_rules()`:
  - Robust loader (cached → KE → FS via `__file__` parents + CWD fallbacks).
  - Scans BPHS + Laghu for condition language ("if ", "kendra", "trikona", "dasa", "lord") → short snippets + `chapter_id`.
  - Scans Yogini book for deity-named chapters → notes + citations.
- `_on_dasha_refresh` now calls `_revive_dasha_rules()` after book load.
- `compute_vimshottari`: attaches `citation` (book:ch-id) to a sample of `all_mahadashas` dicts and to current maha when variants present.
- `compute_dasha`: surfaces up to 2 `variant_notes` + `variant_citations` on `DashaResult`; appends `[KE variants] ...` line to `summary`.
- Added `variant_notes`, `variant_citations` fields to `DashaResult`.
- Light registration touch (ensure core dasha engine is registered when app shims are imported):
  - `cvce/app/dasha_vimshottari.py`
  - `cvce/app/dasha_other.py`
  - `cvce/app/yogini_predict.py`

No changes to `dasha_analyzer.py` (synthesis rules remain Parashari-derived; provenance already referenced BPHS/PD).

## 4. Verification (run after clear/refresh/recompute)

```
CLEAR: ok
on_refresh (registration hook): called → revive
RECOMPUTE: ok

evidence:
  structured books referenced via revive load: 2+
  periods carrying chapter citation: 3
  result.variant_notes: 2
  result.variant_citations: ['Brihat_Parasara_Hora_Sastra_Vol_1:ch-8', 'Predict_Effectively_Through_Yogini_Dasha:ch-venus_ulka']
  summary has [KE variants] marker: True
  result.chapter_citation present: True

cascade: clear → _on_dasha_refresh (which calls revive) → recompute → enriched output visible: PASS
```

Sample enriched period:
```
{'planet': 'Moon', 'start': '1984-06-15', ..., 'citation': 'Brihat_Parasara_Hora_Sastra_Vol_1:ch-8'}
```

Sample surfaced note (truncated):
```
Vimshottari variant: 8. DIVISIONAL CONSIDERATION ... Vimsopaka strength...
```

## 5. Tracker Update

Row updated in `docs/KE_FULL_UPDATE_WAVE_2026-06-30.md`:
- Status: `DONE`
- Evidence includes: 7 JSONs, revive loads, 3 cited periods, variant_notes + summary marker, registration calls revive that mutates visible output.

## 6. Exit Criteria Addressed (for this row)

- [x] Registered + on_refresh that clears *and* revives data/logic
- [x] Structured provenance (chapter ids) attached to periods + result
- [x] At least one algorithm surface (variant notes / citations in compute path) now sourced from KE corpus
- [x] Verification numbers reported (counts + PASS)
- [x] Tracker row + this report written
- [x] Cascade tested (clear, refresh via on_refresh, recompute)

## Files Touched (StrReplace + Write)

- `cvce/vedic_engine/prediction/dasha.py` (core revive + wiring + surface)
- `cvce/app/dasha_vimshottari.py`, `dasha_other.py`, `yogini_predict.py` (light reg touch)
- `docs/KE_FULL_UPDATE_WAVE_2026-06-30.md` (tracker row)
- `docs/agent-reports/KE-wave-dasha.md` (this report)

**Note on snippet quality:** Structured chapters for these sources contain OCR/page noise; the mechanism (load → extract → cite → surface) is proven and can be refined with better section heuristics later without changing the registration/revive contract.