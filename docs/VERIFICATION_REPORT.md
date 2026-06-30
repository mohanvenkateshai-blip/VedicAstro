# Structured Books Verification Report

**Overall:** 5/6 PASS  |  Generated: 2026-06-30T11:30:23.395375
**Strict mode:** False  |  Enforced FAIL this run: False

## Per-book results
- **PASS Ashtakavarga_System_Comprehensive_Handbook** | chapters=8 | patched=49 | deep=True | ke=True | overlap=7/7 (100.0%)
- **PASS Jaimini_Sutras** | chapters=10 | patched=676 | deep=True | ke=None | overlap=2/86 (2.3%)
- **PASS Brihat_Parasara_Hora_Sastra_Vol_1** | chapters=55 | patched=1881 | deep=True | ke=None | overlap=41/259 (15.8%)
- **PASS Saravali** | chapters=24 | patched=836 | deep=True | ke=None | overlap=23/28 (82.1%)
- **PASS Phaladeepika_Mantreswara** | chapters=157 | patched=1445 | deep=True | ke=None | overlap=116/116 (100.0%)
- **FAIL Jataka_Tatva_Mahadeva** | chapters=0 | patched=642 | deep=True | ke=None
  - gap: 0 chapters after parse

## Gaps

- Jataka_Tatva_Mahadeva: 0 chapters after parse

## Strict overlap notes

NOTE: --strict would have failed (or did fail) for the following patched books due to <80% chapter_id overlap:
  - Jaimini_Sutras: overlap 2/86 = 2.3%
  - Brihat_Parasara_Hora_Sastra_Vol_1: overlap 41/259 = 15.8%
  Re-run with --strict after aligning patch chapter_ids to structured chapter ids.

## Remediation targets (from run)
- fix duplicate chapter ids on classics (Saravali, BPHS, Phaladeepika, Ashtakavarga)
- align patch chapter_ids with current structured chapter ids (0-overlap on several patched books)
- re-map low-coverage books (e.g. Jyotish_Yoga_Handbook_101)
- run with --strict to enforce >=80% chapter_id overlap on patched books