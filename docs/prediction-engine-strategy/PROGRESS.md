# Prediction Engine Reliability Strategy — MAFIP Progress

## Current Phase

- Phase: 8 — Person Timeline end-to-end implementation
- Status: Person Timeline local implementation passed independent re-gate at 96/100; rendered browser acceptance and prospective ingestion remain
- Scope: Person-centred milestone lanes, MD/AD/PD provenance, observed events, sealed predictions and append-only resolutions
- Started: 2026-07-14
- Orchestrator: Codex root agent

## Objective

Produce a complete, approval-gated strategy for improving VedicAstro from a deterministic, source-grounded interpretation engine into a measurable forecasting research system, including a dedicated Prediction Verbalisation Engine for precise, timed, conditional, human-readable outputs.

## Agent Waves

### Person Timeline release wave — Local automated gate passed

- [x] T0 canonical milestone, evidence, timing-ladder and append-only resolution contracts
- [x] T1 CVCE timeline/detail/capture/resolution endpoints
- [x] T2 interactive `/chart/timeline` lanes and milestone detail experience
- [x] T3 migrated prediction candidates with explicit origin/prospective identity
- [x] T4 automated runtime, regression, build, ownership and adversarial integrity gates
- [ ] Local preview accepted at `http://localhost:3000/chart/timeline`

### Wave 1 — Complete

1. Prediction science and baseline evaluation
2. Module and integration architecture
3. Prediction verbalisation and human-language design

### Wave 2 — Complete

4. Outcome data, experiment design, and calibration
5. Safety, privacy, governance, and misuse controls
6. QA, alignment, delivery sequencing, and acceptance gates

## Key Constraints

- More than five specialists will be used across two waves.
- Environment concurrency limit is four active agents including the orchestrator, so at most three specialists run concurrently.
- Existing user changes and unrelated untracked files must remain untouched.
- Current internal rule scores must not be represented as empirically calibrated prediction probabilities.
- Architecture and final strategy require user approval before implementation begins.

## Gates

- [x] Discovery evidence complete
- [x] Baseline scoring rubric agreed
- [x] Architecture and module impact reviewed
- [x] Prediction Verbalisation Engine design reviewed
- [x] Evaluation and outcome-data design reviewed
- [x] Safety/privacy review complete
- [x] Cross-agent alignment complete
- [x] User architecture approval
- [x] Implementation authorization
- [ ] G0 reproducible green baseline (tests/compile green; Ruff pin and legacy fixtures pending)
- [ ] G1 P0 safety/privacy/service-security foundation

## Metrics

- Agent model routing: Not exposed by the current orchestration environment; all available agents use the provided underlying capability.
- Exact per-agent token telemetry: Not exposed; no token counts or savings percentages will be fabricated.
- Token-efficiency controls in use: bounded file ownership, minimal forked context, existing-agent reuse, targeted retrieval, diff-focused review, targeted tests before full-suite verification, and concise structured handoffs.
- Specialist agents planned: 6
- Specialist agents launched: 6
- Specialist agents completed: 6
- Implementation specialists launched: 12
- Product files changed: 30+
- Planning artifacts changed: 2
- Critical implementation blockers: 4
  - Production encryption/service secrets are not provisioned; legacy plaintext migration and live owner/cookie isolation smoke tests remain.
  - Deterministic P0 claim filtering is not a semantic proof and remains limited to registered narrative/ForecastClaim fields.
  - Demonstrated prediction accuracy remains N/A until clean prospective outcomes exist; no traditional score may be displayed as probability.
  - Human G2 ontology review and later privacy/research governance gates are still required before outcome collection or user-visible v2 forecasts.

## Log

- 2026-07-14T15:56:45+01:00: Person Timeline remediation passed independent MAFIP re-review at **96/100 with zero Critical or High findings**, superseding the earlier 58/100 failure while preserving it below as audit history. Detail reads are now timeline/subject-bound; portal timeline calls use an owner-scoped signed guest cookie; forged ownership returns 403; cross-subject stored detail returns 404; matching criteria are sealed before resolution; premature miss/false-alarm resolution is rejected; resolution save refreshes the timeline; outcome colours and zoom filtering were corrected. Verification passed: **338 CVCE tests and 1 intentional skip** from 339 collected, **21/21** focused timeline tests, **5/5** portal ownership tests, portal typecheck, targeted lint, production build and `git diff --check`. A fresh guest returned 200 and the live timeline returned 11 non-prospective engine-inference milestones, 90 timing periods and zero outcomes. Remaining non-blockers are prospective ingestion/sealing (therefore empirical accuracy remains N/A), observed-event correction UI and browser visual/accessibility QA. No commit, push, migration or deployment was executed.

- 2026-07-14T15:42:44+01:00: Person Timeline did **not** pass its first independent MAFIP release gate (**58/100**, required 95/100 with no Critical/High findings). The reviewer reproduced a cross-subject stored-milestone detail disclosure; found no authenticated owner binding around portal timeline reads/writes; found resolution criteria could be selected after seeing an outcome; and found misses/false alarms could be recorded before the prediction window ended. Medium follow-ups cover durable production persistence, correction UI, outcome-marker semantics and zoom-edge filtering. The portal build/typecheck/targeted lint and HTTP/API smokes passed, but its gate also found that successful outcome resolution does not refresh the timeline. Remediation and a fresh independent re-gate are mandatory before release; the feature remains local-only and uncommitted.

- 2026-07-14T15:40:11+01:00: Integrated the local Person Timeline release slice. CVCE now has canonical milestone/evidence/timing contracts, a SQLite append-only ledger migration, subject-bound event capture, immutable matching criteria, linear superseding resolutions, current-outcome projection, MD/AD/PD provenance, detail and query services, and four timeline API routes. The portal now has `/chart/timeline`, six timeline UI components, observed-event and eligible prospective-resolution forms, Dasha deep links, proxy allowlisting, server/client contracts, subject pseudonymisation and a sidebar entry. The focused timeline suites passed **18 tests** after adversarial remediation; the integrated CVCE suite passed **335 tests with 1 intentional skip** from 336 collected using the official Swiss Ephemeris path; and `git diff --check` passed. A live Mohan query and detail returned Swiss Ephemeris 2.10.03 calculations, and the rendered route returned HTTP 200. The existing 11 migrated bands remain explicitly labelled non-prospective `engine_inference` research candidates; no prospective accuracy, probability or scientific-validation claim is made. Portal final gates, independent final review and rendered browser acceptance remain open. Browser automation could not initialize because its runtime attempted to redefine `process`; do not interpret HTTP rendering as completed pixel/accessibility QA. No commit, push, Supabase migration, Vercel deployment or Fly deployment was executed.

- 2026-07-14T15:14:31+01:00: User escalated Person Timeline to the priority release slice. Re-read the complete MAFIP guide, the complete `PERSON_TIMELINE_DESIGN.md`, portal agent instructions and relevant installed Next.js server/client/data-fetching guidance. Began parallel implementation with strict separation between observed events, prospective predictions and retrospective hypotheses. Local portal and CVCE services were healthy at wave start. No remote deployment or git mutation was authorized.

- 2026-07-14T15:06:00+01:00: Completed a read-only, symbol-level audit of the standalone Muhūrta donor and expanded `MUHURTA_REUSE_MANIFEST.md` across the implemented 13 numbered `runEngine` stages plus the implicit fruition stage, Finder, 64 activity profiles, personalization, explanations, six-locale assets, API and astronomy. Each candidate now records the exact donor symbol, VedicAstro equivalent, relative engineering maturity, provenance state, defects/tests, a PORT/VALIDATE/QUARANTINE/REJECT decision, prerequisites and target module. CVCE remains canonical for astronomy and existing Panchanga/Gochar/Ashtakavarga/Muhūrta-yoga capabilities; browser astronomy, a duplicate API and wholesale Finder/weight copying are rejected or quarantined. The donor's claimed 32-expert/160-review/4.42/94%/κ=0.68 result is explicitly unverified: the referenced `pilot_data/scores.jsonl` is absent, while the only local score file has 10 single-case expert rows plus one aggregate object claiming 50 reviews, insufficient to recompute the claimed review count or kappa. The 99-line seed corpus is source text, not outcome or calculation validation. The next three slices are now fixed as (1) canonical Panchanga/window boundaries, (2) three versioned source-bound activity profiles in research/shadow mode, and (3) a bounded server-side Finder with Muhūrta Lagna and PVE rendering. No source code, test code, git state, secrets, migrations or deployments were changed.

- 2026-07-14T14:08:28+01:00: Release/handoff checkpoint updated without source, git or remote mutations. Transit Context exists but its independent gate failed at 68/100 and remediation is active. B2 entered a third remediation after 66/100. B3 remediation is complete and awaits independent re-gate. Native `/chart/muhurta` is implemented in `portal/src/app/(main)/chart/muhurta/page.tsx`, `portal/src/lib/muhurta-context.ts`, `portal/src/lib/muhurta-context.test.mts`, `portal/src/components/ChartSidebar.tsx`, and `MUHURTA_REUSE_MANIFEST.md`; 3/3 context tests, typecheck, changed-file ESLint, production build and HTTP smoke checks passed, while pixel visual QA remains open. Standalone reuse follows the donor strategy: port validated patterns, retain the iframe fallback, and reject wholesale browser-engine/static-DST copying. No commit, push, Supabase migration, Vercel deployment, or Fly deployment was executed.

- 2026-07-14T12:35:51+01:00: Release/handoff checkpoint recorded in root `CONTEXT.md` and `RELEASE_HANDOFF.md`: Wave A scores and accepted suite preserved; Wave B artifacts, changed-file groups, excluded user-owned items, verification commands, migration/deployment prerequisites, rollback and explicit-path staging plan documented. Fresh CVCE verification completed with 246 passed and 1 skipped; compileall and `git diff --check` passed. Remote deployment status: not executed. No commit, push, migration or deployment performed while Wave B remains ungated.

- 2026-07-14: User authorized implementation under MAFIP. Re-read the complete MAFIP guide, confirmed a four-slot environment (orchestrator plus three concurrent specialists), and began Wave A with non-overlapping module ownership.
- 2026-07-14: Froze the pre-Wave-A verification baseline: the complete CVCE pytest suite passed with one intentional skip; only upstream/deprecation warnings were emitted.
- 2026-07-14: Wave A first implementation integrated at 165 passed, 1 skipped: immutable raw research contracts/store, open event/timing registries, non-destructive adapter/uncertainty/evaluation paths, exhaustive Knowledge Engine research query and capture-first Workbench.
- 2026-07-14: MAFIP peer review held the Wave A gate. A2 scored 64/100 due to memory-only archives, incomplete graph/store enumeration/removal capture, quote-verification and concurrency gaps. A3 scored 66/100 due to unbound hindsight probabilities, pre-quarantine serialization failure, candidate score loss and misleading subgroup denominators. Targeted remediations launched; Wave B remains blocked until re-review passes.
- 2026-07-14: A3 remediation passed independent re-review at 97/100: issuance-bound artifacts, diagnostic-only manual probabilities, hostile-value quarantine, raw candidate score preservation, true subgroup denominators and positional compatibility verified.
- 2026-07-14: A2 first remediation raised the integrated suite to 189 passed, 1 skipped, but re-review still rejected it at 82/100 after reproducing silent Supabase page failure, stale shared durable views, citation source/locator substitution and tied-assessment ordering. Second targeted remediation launched; Wave A gate remains correctly closed.
- 2026-07-14: A1 independent review rejected at 76/100 despite passing tests: embedded inputs were not mandatorily hash-bound, run-state combinations were contradictory, SQLite appends were not thread-safe, annotation histories could fork/backdate, and registry/schema bindings were incomplete. Exact integrity/concurrency remediations launched.
- 2026-07-14: Wave A closed after repeated adversarial remediation: A1 passed 98/100, A2 passed 96/100, A3 passed 97/100; clean CVCE verification reached 208 passed, 1 skipped. Accepted foundations include lossless immutable runs, durable exhaustive knowledge/capture access, issuance-bound evaluation and hostile-value quarantine.
- 2026-07-14: Began Wave B with three parallel specialists: calculation profiles/cross-engine fixtures, technique-configuration/constraint-ablation synthesis, and authenticated raw research service plane isolation.
- 2026-07-14: User requested a dedicated Release & Handoff agent. Queued it for the next available concurrency slot with responsibility for timestamped `CONTEXT.md`/handoff updates, git checkpoints, Supabase migration state, Vercel/Fly deployment readiness, rollback notes and major-gate release records. No mid-wave remote deployment will be performed.
- 2026-07-14: User clarified that the objective is unrestricted private technique learning and that no filter may block, hinder, erase, or diminish predictability.
- 2026-07-14: Re-audit found research restrictions in the closed event ontology, limited timing resolutions, score-erasing abstention, fail-fast adapters, Research Workbench rejection paths, hidden invalidated knowledge, filtered narration/report projection, and suppressed small-subgroup evaluation.
- 2026-07-14: Added `UNFILTERED_RESEARCH_STRATEGY.md`; all techniques, sensitive domains, native scores, exact timings, contradictions, failures, and raw narratives are now required research records. The previous strategy is retained only as a future product-presentation design.
- 2026-07-14: Mapped the existing astronomy, Panchanga, Knowledge Engine/GraphRAG, rules, Dasha, Gochar, Ashtakavarga, Yoga, KP, Prashna, Muhurta, synthesis, forecasting, Workbench and verbalisation modules into one accuracy-improvement programme. Identified the generic cross-scale score sum in `VedicPredictor._synthesize()` as a primary source of vague, non-event-specific outputs.
- 2026-07-14: Added the Person Timeline track. It unifies observed milestones, sealed predictions, Dasha/Pratyantardasha paths, transits, rules, source passages, calculation traces and outcomes. Prospective predictions and retrospective explanations remain separately identified so the feature improves both user understanding and honest accuracy measurement.

- 2026-07-14: Read the complete MAFIP guide.
- 2026-07-14: Began Phase 1 and launched Wave 1 specialists.
- 2026-07-14: Wave 1 completed. Baselines proposed: demonstrated prediction accuracy N/A; Prediction Research Readiness Index 23/100; verbalisation quality 29/100.
- 2026-07-14: Launched Wave 2 specialists for outcome/calibration, safety/governance, and QA/alignment.
- 2026-07-14: Confirmed CVCE baseline: 44 passed, 1 skipped, 2 failed; failures trace to `transit_analyzer.py:553`.
- 2026-07-14: Wave 2 completed; six specialists total completed across both waves.
- 2026-07-14: Consolidated strategy in `docs/prediction-engine-strategy/STRATEGY.md`.
- 2026-07-14: Entered MAFIP architecture approval gate. No product implementation has begun.
- 2026-07-14: User approved implementation (`ok proceed`).
- 2026-07-14: Launched implementation Wave 1: baseline repair, saved-chart privacy, and narration/claim safety.
- 2026-07-14: Repaired the transit-analysis syntax defect and independently verified the complete CVCE test baseline: 52 passed, 1 skipped. G0 remains open for the planned Ruff pin and legacy fixtures.
- 2026-07-14: Wave 1 privacy and narration-safety implementations completed and entered independent review.
- 2026-07-14: Launched implementation Wave 2 for service authentication and typed forecasting contracts; six implementation specialists have now been used including the independent reviewer.
- 2026-07-14: WP2 v1 typed contracts and nine-leaf resolvable event ontology completed; full CVCE suite reached 67 passed, 1 skipped. G2 awaits human domain/product approval.
- 2026-07-14: Portal-to-CVCE service authentication completed locally with production fail-closed configuration; no secrets or deployments were changed.
- 2026-07-14: Independent Wave 1 review rejected G1 and supplied adversarial safety/privacy gaps; remediation specialists relaunched.
- 2026-07-14: Launched WP3 additive canonical evidence-pipeline specialist.
- 2026-07-14: Safety remediation replaced outbound denylist scrubbing with a positive projection, narrowed claim filtering to narrative fields, added adversarial coverage and preserved structural Cancer rashi values.
- 2026-07-14: Privacy remediation added executable crypto/boundary tests, strict envelope consistency, valid calendar/time input, and fail-closed authenticated horoscope writes; live migration/smoke work remains.
- 2026-07-14: WP3 first slice completed with deterministic canonicalisation, stable IDs, evidence conflicts, named rule packs and replay; full CVCE suite reached 79 passed, 1 skipped.
- 2026-07-14: Launched WP6 deterministic Prediction Verbalisation Engine specialist.
- 2026-07-14: WP4 append-only de-identified ledger completed with consent, immutable releases/claims, superseding resolution events, replay, export and tombstone semantics; no production database migration executed.
- 2026-07-14: WP5 M0/M1 baselines, point-in-time leakage guards, evaluation metrics, birth-time stability and fail-closed abstention completed; full suite reached 109 passed, 1 skipped.
- 2026-07-14: WP6 deterministic en-IN PredictionBrief completed with exact event/window, direction, evidence, actions, limitations, abstention and bucket-soup rejection; full suite reached 95 passed, 1 skipped at that integration point.
- 2026-07-14: User approved incorporating the handbook repository option as an offline Research Workbench; implementation launched without adding it to the live prediction path.
- 2026-07-14: Launched WP7 feature-flagged v2 API/UI shadow specialist; all flags remain off by default.
