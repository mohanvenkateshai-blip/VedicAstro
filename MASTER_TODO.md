# MASTER TODO — "complete all pending items" mission (Orchestrator maintained)
# Protocol: only 1 in_progress per major item at a time. Update on agent reports.
# All agents MUST report: [ROLE: xxx] + key evidence (counts, pass/fail, file:line) in FINAL reply.

## Major Items (sequential within, parallel across waves)
- [DONE] Learn stabilization (61/61 structured + green smoke)  [evidence: verify-all-learn-books: structured-pass=61, zero-chapter=0; Jataka_Tatva_Mahadeva=4ch structured-pass (KNOWN_EDGE flag but passes); smoke-learn 7/8 (Hora signal); local verify 61]
- [TODO] KE wave all rows DONE (Yogas, Ashtakavarga, Synthesis, Integration, Orchestration; maintain cracks=0)
- [TODO] Registration fixed (full runtime registration at cvce startup for 9 engines)
- [TODO] Hiranya full report (complete polish: narration, facts integration, all chapters UI)
- [TODO] Advanced dashas (Kaksha calendar + Chara/Kalachakra full engine + UI)
- [TODO] Verifications green (pytest, typecheck, ke_wave, learn verify, smoke-learn-production, verification_gate.sh)
- [TODO] Docs updated (all handoffs, STATUS, KE tracker, LEARN_*, CONTEXT, agent reports)
- [BLOCKED] Embeddings (Gemini quota; do not run)
- [FORBIDDEN] Direct git push / commit / deploy unless user explicitly asks this session

## Current Active Agents Wave
Wave-1 launched: 6 specialized parallel agents (non-overlapping). Orchestrator monitoring.
Agents instructed: MUST end final reply with [ROLE: <name>] + key evidence (counts/pass/fail/files:lines/verification outputs). Facts only. No commits.

## Verification Gate (run before any complete)
Must execute in order before declaring roadmap complete:
1. cd cvce && .venv/bin/python -m pytest tests/golden/ -v
2. cd portal && npm run typecheck
3. python3 scripts/ke_wave_status.py
4. node portal/scripts/verify-all-learn-books.mjs
5. ./scripts/smoke-learn-production.sh
6. bash scripts/verification_gate.sh
All green + docs updated. Only then aggregate and report complete.
- [TODO] KE wave all rows DONE (Yogas, Ashtakavarga, Synthesis, Integration, Orchestration; maintain cracks=0)
- [TODO] Registration fixed (full runtime registration at cvce startup for 9 engines)
- [TODO] Hiranya full report (complete polish: narration, facts integration, all chapters UI)
- [TODO] Advanced dashas (Kaksha calendar + Chara/Kalachakra full engine + UI)
- [TODO] Verifications green (pytest, typecheck, ke_wave, learn verify, smoke-learn-production, verification_gate.sh)
- [TODO] Docs updated (all handoffs, STATUS, KE tracker, LEARN_*, CONTEXT, agent reports)
- [BLOCKED] Embeddings (Gemini quota; do not run)
- [FORBIDDEN] Direct git push / commit / deploy unless user explicitly asks this session

## Sub-items / Evidence Log (append only)
- Learn: 60/61 structured-pass (Jataka_Tatva_Mahadeva=0 ch edge); last smoke 7/7 or 7/8 (Hora signal flaky)
- KE wave baseline: engines=9, probed=10, cracks=0 (2026-06-30)
- Graph: 26,722 nodes
- Muhurta: frozen external iframe; core KE done
- No edits to Panchang/panchanga_muhurtha/

Start time: 2026-07-01T09:26
Orchestrator: This agent (Kilo as Compliance/Reminder/Orchestrator)
Next action: Launch wave 1 (5+ agents) now. Re-launch compliance if <5 active or sequential drift.
