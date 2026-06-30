# Structured Books Verification Report

**Overall:** 1/2 PASS  |  Generated: 2026-06-30T14:27:10.669341
**Strict mode:** False  |  Enforced FAIL this run: False

## Per-book results
- **FAIL Jataka_Tatva_Mahadeva** | chapters=0 | patched=642 | deep=True | ke=False
  - gap: 0 chapters after parse
  - gap: KE get_structured_book returned 0 or mismatched chapters vs direct
- **PASS Ashtakavarga_System_Comprehensive_Handbook** | chapters=8 | patched=49 | deep=True | ke=None | overlap=7/7 (100.0%)

## Gaps

- Jataka_Tatva_Mahadeva: 0 chapters after parse
- Jataka_Tatva_Mahadeva: KE get_structured_book returned 0 or mismatched chapters vs direct

## Remediation targets (from run)
- fix duplicate chapter ids on classics (Saravali, BPHS, Phaladeepika, Ashtakavarga)
- align patch chapter_ids with current structured chapter ids (0-overlap on several patched books)
- re-map low-coverage books (e.g. Jyotish_Yoga_Handbook_101)
- run with --strict to enforce >=80% chapter_id overlap on patched books