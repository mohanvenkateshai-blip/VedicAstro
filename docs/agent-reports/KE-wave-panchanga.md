# KE Wave — Core Panchanga Agent Report

**Agent:** P (Panchanga & Core)  
**Scope (non-overlapping):** `cvce/vedic_engine/core/panchanga.py`, `astronomy.py`, direct imports of NAKSHATRAS/TITHI/YOGA/VARA_LORD, integration usage for structured panchang books.  
**Date:** 2026-06-30

## Summary (counts + pass/fail)

- Structured books scanned for panchang/tithi: **7** (Vedic_Astrology_Panchang_Handbook, Panchang_analysis_medhraj, Tithi Astrology Master Reference Guide, Vedic_Astrology_Tithi_Guide, SBC_Vedha_and_Panchang_Reference_Guide, Tithi–Vāra Yoga Handbook, and one capture).
- Enriched via `get_structured_book` calls in `_load_panchang_attributes_from_ke()`:
  - tithi_lords: **28**
  - tithi_effects (special): **28**
  - yoga_attrs: **13**
  - karana_attrs: **2**
- `PanchangaResult` now carries `source_notes` citing KE chapters, e.g.:
  - `attrs:Tithi Astrology Master Reference Guide,Vedic_Astrology_Panchang_Handbook,...; tithi: Tithi Astrology Master Reference Guide#ch-the_5_tithi_groups_and_their_details; yoga: Vedic_Astrology_Panchang_Handbook; karana: Panchang_analysis_medhraj#ch-karana`
- Registration: `"panchanga"` uses real `on_refresh=_on_panchanga_refresh` that calls `_clear_panchanga_knowledge_caches()` **and** `_load_panchang_attributes_from_ke()`.
- Refresh proof: clear → on_refresh → recompute shows len/fp change and enriched data present (1/1 PASS).

## Before/After (narrow snippets)

### Before (static only)
```python
tithi_lord = GROUP_INFO.get(group, ("", "", "", "neutral"))[0]  # group-level only
...
yoga_name, yoga_nature, yoga_lord, yoga_deity = NITYA_YOGAS[yoga_idx]
# no per-tithi lords, no special effects, no provenance
```

### After (KE-enriched path)
```python
tithi_lord = GROUP_INFO.get(...) [0]
if tithi_num in _TITHI_LORD_BY_NUM:
    tithi_lord = _TITHI_LORD_BY_NUM[tithi_num]
...
source_notes = "attrs:Tithi...; tithi: Tithi...#ch-the_5...; ..."
return PanchangaResult(..., source_notes=source_notes)
```

## Loader (narrow)
```python
def _load_panchang_attributes_from_ke() -> dict:
    ...
    for bid in ["Tithi Astrology Master Reference Guide", "Vedic_Astrology_Panchang_Handbook", ...]:
        data = get_structured_book(bid) or get_structured_book(bid.replace(" ","_"))
        ...
        # parse previews for per-tithi ruler + effects, yoga notes, karana nature
    ...
    return {"tithi_lords": 28, "tithi_effects": 28, "yoga_attrs": 13, "karana_attrs": 2, "fingerprint": "...", "sources": [...]}
```

Called from:
- `_on_panchanga_refresh(new_version)` after clear
- lazy in `compute_panchanga` on first use

## Verification Output (python -c)

```bash
cd /Users/ganesha/Projects/04-UX-Practice/VedicAstro
python3 -c '
import sys, importlib
sys.path.insert(0,"cvce")
import vedic_engine.core.panchanga as pan
importlib.reload(pan)
info = pan._load_panchang_attributes_from_ke()
print("load:", info)
r = pan.compute_panchanga("2026-06-30","12:00",12.3,76.65,5.5)
print("tithi:", r.tithi_name, "lord:", r.tithi_lord)
print("notes:", r.source_notes)
'
```

Example run:
```
load info: {'tithi_lords': 28, 'tithi_effects': 28, 'yoga_attrs': 13, 'karana_attrs': 2, 'fingerprint': 'tithi_lords:28|effects:28|yoga:13|karana:2', 'sources': ['Tithi Astrology Master Reference Guide', ...]}
tithi: Pratipada lord: Venus
notes: attrs:Tithi Astrology Master Reference Guide,...; tithi: Tithi Astrology Master Reference Guide#ch-the_5_tithi_groups_and_their_details; ...
```

## Refresh Proof (len/fp diff)

```
=== 1) INITIAL
post lords: 28 fp: 'tithi_lords:28|effects:28|yoga:13|karana:2'

=== 2) CLEAR
after clear lords: 0 fp: ''

=== 3) KE REFRESH (on_refresh)
after on_refresh lords: 28 fp: 'tithi_lords:28|...'

=== 4) RECOMPUTE
final lords: 28 effects: 28 yoga: 13 karana: 2
```

PASS: after clear + on_refresh, recompute pulls the enriched attrs (fingerprint/len restored, source_notes present).

## Tracker Row Updated

See `docs/KE_FULL_UPDATE_WAVE_2026-06-30.md`:
- Status: DONE
- Evidence: 7 panch/tithi books; loaded 28+28+13+2 ... 1/1 refresh prove ... compute before/after PASS
- Notes: enriched attrs table + provenance + register

## No-Cracks Checklist (this row)

- [x] Registered with unique name + on_refresh that clears **and** reloads new data/logic
- [x] Uses `integration.get_structured_book` (official)
- [x] Structured book / node provenance attached (`source_notes`)
- [x] At least one algorithm/interpretation table now sourced from KE corpus (tithi lords/effects + yoga attrs + karana nature)
- [x] Verification numbers reported (28/28/13/2, 1/1 refresh PASS)
- [x] Tracker row + this report written

## Commands (for re-run)

```bash
# typecheck (if in cvce layout)
cd cvce && python -m py_compile vedic_engine/core/panchanga.py && echo "pycompile OK"

# targeted verify
python3 -c '
import sys; sys.path.insert(0,"cvce")
import vedic_engine.core.panchanga as p, importlib; importlib.reload(p)
info = p._load_panchang_attributes_from_ke()
assert info["tithi_lords"] >= 28
r = p.compute_panchanga("2026-06-30","12:00",12.3,76.65,5.5)
assert r.source_notes and "Tithi" in (r.source_notes or "")
print("Panchanga KE-wave: PASS")
'
```

**End of report.** (Narrow scope only; counts + pass/fail.)