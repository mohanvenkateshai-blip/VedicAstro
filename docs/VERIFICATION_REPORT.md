# Structured Books Verification Report

**Overall:** 3/4 PASS  |  Generated: 2026-06-30T20:04:44.158428
**Strict mode:** True  |  Enforced FAIL this run: True

## Per-book results
- **PASS Ashtakavarga_System_Comprehensive_Handbook** | chapters=8 | patched=49 | deep=True | ke=True | overlap=7/7 (100.0%)
- **PASS Jyotish_Yoga_Handbook_101** | chapters=132 | patched=0 | deep=True | ke=None
  - gap: no patch entries for book (may need remap_nodes_to_structured or was not included)
- **PASS Saravali** | chapters=24 | patched=836 | deep=True | ke=None | overlap=23/28 (82.1%)
- **FAIL Brihat_Parasara_Hora_Sastra_Vol_1** | chapters=55 | patched=1881 | deep=True | ke=None | overlap=41/259 (15.8%)
  - gap: strict: chapter_id overlap 15.8% < 80% (patch_chapter_ids vs structured)

## Gaps

- Jyotish_Yoga_Handbook_101: no patch entries for book (may need remap_nodes_to_structured or was not included)
- Brihat_Parasara_Hora_Sastra_Vol_1: strict: chapter_id overlap 15.8% < 80% (patch_chapter_ids vs structured)

## Strict overlap notes

NOTE: --strict would have failed (or did fail) for the following patched books due to <80% chapter_id overlap:
  - Brihat_Parasara_Hora_Sastra_Vol_1: overlap 41/259 = 15.8%
  Re-run with --strict after aligning patch chapter_ids to structured chapter ids.

## Remediation targets (from run)
- fix duplicate chapter ids on classics (Saravali, BPHS, Phaladeepika, Ashtakavarga)
- align patch chapter_ids with current structured chapter ids (0-overlap on several patched books)
- re-map low-coverage books (e.g. Jyotish_Yoga_Handbook_101)
- run with --strict to enforce >=80% chapter_id overlap on patched books