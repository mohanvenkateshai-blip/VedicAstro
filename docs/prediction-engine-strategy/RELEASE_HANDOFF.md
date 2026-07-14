# Prediction Engine Release Handoff

**Checkpoint:** 2026-07-14T15:56:45+01:00 (Europe/Dublin)  
**Branch / remote:** `main`; `origin` = `https://github.com/mohanvenkateshai-blip/VedicAstro.git`; local `HEAD` `b20849c`, with `origin/main...HEAD` = `0 0` before any future commit.  
**Remote deployment status:** not executed.  
**Release decision:** Person Timeline local gate **PASS at 96/100 with zero Critical or High findings**. Remote release remains HOLD: the feature is uncommitted/local-only, rendered browser acceptance remains open, prospective ingestion/sealing is absent, Wave B and Transit Context retain their previously recorded programme gates, and the mixed worktree contains unrelated existing changes.

## Current checkpoint delta

- **Person Timeline gate:** remediation passed independent re-review at **96/100 with zero Critical or High findings**. This supersedes the historical 58/100 failure recorded in `PROGRESS.md`. Detail reads are timeline/subject-bound; portal calls use owner-scoped signed guest identity; matching criteria are sealed before resolution; premature miss/false-alarm resolution is rejected; successful resolution refreshes the timeline; outcome colours and zoom filtering were corrected.
- **Person Timeline automated evidence:** the full CVCE suite passed **338 tests with 1 intentional skip** from 339 collected using the canonical Swiss Ephemeris path; focused timeline tests passed **21/21**; portal ownership tests passed **5/5**; portal typecheck, targeted timeline ESLint, production build and `git diff --check` passed. A fresh guest request returned HTTP 200, forged ownership returned 403, and cross-subject stored detail returned 404. The live timeline returned 11 explicitly labelled `engine_inference` milestones, 90 timing periods and zero outcomes.
- **Person Timeline visual gate:** browser automation could not initialize because its runtime attempted to redefine `process`. HTTP 200 and rendered HTML are not substitutes for pixel, interaction, responsive or accessibility acceptance; that gap remains explicit.
- **Person Timeline scientific boundary:** prospective ingestion/sealing is not implemented. The 11 populated bands are migrated legacy `engine_inference` research candidates and explicitly non-prospective; there are zero resolved outcomes. Empirical predictability/accuracy therefore remains **N/A**, and no rule score is represented as probability. The timeline is an evidence and measurement surface, not proof that accuracy improved.
- **Person Timeline remaining non-blockers:** observed events do not yet have a correction/supersession UI. Browser automation remains blocked, so pixel, responsive, interaction and accessibility QA must be completed manually in a real browser before a remote UI release.
- **Transit Context:** implemented across the portal/CVCE boundary, but independent review rejected the gate at **68/100**. Remediation is active; no release claim is permitted yet. Current owned files include `portal/src/app/(main)/chart/transits/page.tsx`, `portal/src/components/explorers/{TransitWorkspace.tsx,GocharPanel.tsx,GraphicalEphemeris.tsx}`, `portal/src/lib/{transit-context.ts,transit-context.test.mts}`, and `cvce/tests/test_gochar_transit_context.py`, with overlapping CVCE integration changes subject to the remediation review.
- **B2 experiment system:** third remediation is active after an independent **66/100** result. Do not stage or release `technique_registry.py`, `experiment_matrix.py`, `constraint_trace.py`, `synthesis.py`, their immutable helpers, or experiment tests until the next independent gate passes.
- **B3 raw research service:** remediation is complete for distinct high-entropy credentials, mounted persistence, bounded SQL paging, strict JSON intake and shutdown lifecycle. Independent re-gate is pending; raw research remains disabled by default and no Fly volume or secret was provisioned remotely.
- **Native personalized Muhūrta:** implemented at `/chart/muhurta` using natal context plus a separate election moment and CVCE-only calculations. Exact files: `portal/src/app/(main)/chart/muhurta/page.tsx`, `portal/src/lib/muhurta-context.ts`, `portal/src/lib/muhurta-context.test.mts`, `portal/src/components/ChartSidebar.tsx`, and `docs/prediction-engine-strategy/MUHURTA_REUSE_MANIFEST.md`. Context tests **3/3**, portal typecheck, changed-file ESLint, production build and HTTP route/result smoke checks passed. Pixel-level visual QA remains open because browser control failed to initialize.
- **Standalone donor strategy:** retain the global `/muhurta` iframe as fallback; port typed information/interaction patterns only; validate activity rules, 14-step sequencing and window finding against CVCE/classical fixtures before reuse; reject browser astronomy, mean-element calibration, static DST tables and wholesale standalone bundles. The manifest above is canonical for this slice.
- **Remote state:** no commit, push, Supabase migration, Vercel deployment, or Fly deployment was executed.

## Accepted and active gates

- Wave A accepted after adversarial remediation: A1 **98/100**, A2 **96/100**, A3 **97/100**.
- Wave A accepted suite: **208 passed, 1 skipped**. Accepted capabilities: hash-bound immutable research runs, durable exhaustive knowledge/capture access, issuance-bound evaluation, hostile-value quarantine, concurrency and append-only integrity.
- Baseline scorecard remains non-combinable: demonstrated empirical prediction accuracy **N/A**, Prediction Research Readiness Index **23/100**, verbalisation quality **29/100**. Internal rule scores are not probabilities.
- Wave B is active: calculation profiles and cross-engine reference fixtures; technique registry, experiment matrix, constraint traces and synthesis; authenticated, policy-isolated raw research service plane. These artifacts are local and ungated.

## Changed-file groups

No files are staged. Treat each group as a separate review/commit boundary.

1. **Wave A forecasting and safety:** `cvce/forecasting/`, `cvce/prediction_policy/`, `cvce/vedic_engine/verbalization/`, forecast schemas in `docs/`, related forecast/verbalisation/ledger/retrospective tests, and the additive API/report integration in `cvce/app/`.
2. **Wave A knowledge and Research Workbench:** `cvce/knowledge_engine/` changes, `cvce/research_workbench/`, and the knowledge-query/capture/workbench tests.
3. **Wave B calculations:** `cvce/vedic_engine/core/astronomy.py`, `cvce/tests/cross_engine_reference_cases.py`, `cvce/tests/test_cross_engine_calculations.py`, and `cvce/research_engine/cross_engine/`.
4. **Wave B experiment system:** `cvce/research_engine/{technique_registry.py,experiment_matrix.py,constraint_trace.py,synthesis.py}` and `cvce/tests/test_research_experiment_matrix.py`.
5. **Wave B raw service plane:** `cvce/research_engine/{contracts.py,identity.py,registries.py,service.py,store.py,migrations/}`, `cvce/app/{config.py,server.py}`, CVCE env/Fly/readme changes, and research-service/foundation/path tests.
6. **Portal privacy, service auth and v2 shadow UI/API:** changed portal auth/chart/CVCE/config files, new encryption/boundary/auth helpers and tests, `PredictionBrief.tsx`, and `portal/supabase-schema.sql`.
7. **Programme documentation:** `docs/prediction-engine-strategy/` plus the root `CONTEXT.md` checkpoint.
8. **Transit Context remediation:** stage only the transit-owned portal/CVCE files listed in the current delta after its independent gate; keep them separate from native Muhūrta and from shared-file changes until diff ownership is reconciled.
9. **Native Muhūrta:** stage the five exact files listed in the current delta as one reviewed portal/docs group. `ChartSidebar.tsx` is the sole tracked shared navigation edit in this slice.
10. **B2 third remediation:** stage only the experiment registry/matrix/trace/synthesis/immutable modules and their dedicated tests after re-review.
11. **B3 remediation:** stage raw service/config/Fly/env/lifecycle/API-test files only after its independent re-gate; do not combine with B2.
12. **Person Timeline CVCE:** `cvce/research_engine/timeline/` including `migrations/0001_timeline_ledger.sql`, `cvce/tests/test_person_timeline_{store,api}.py`, and the timeline-owned portions of `cvce/app/{config.py,server.py}` and `cvce/.env.example`. Shared application files require hunk-level review before staging.
13. **Person Timeline portal:** `portal/src/app/(main)/chart/timeline/`, `portal/src/components/timeline/`, `portal/src/lib/timeline-subject.ts`, and the timeline-owned portions of `portal/src/lib/{cvce.ts,types.ts}`, `portal/src/app/api/cvce/[...path]/route.ts`, `portal/src/components/ChartSidebar.tsx`, and `portal/src/app/(main)/chart/dasha/page.tsx`. Shared files require hunk-level review before staging.

Known pre-existing or user-owned items kept out of all programme commits: `.gitignore`, `docs/knowledge-engine-status.md`, `knowledge-graph/KNOWLEDGE_CATALOG.md`, `Branding/`, `embeddings.pid`, and `vedicastro-audit-report.html`. Reconfirm ownership before staging any other overlapping file. Never use `git add .` in this worktree.

## Reproducible verification

Run from the repository root unless noted:

```bash
cd cvce
.venv/bin/python -m pytest -q --disable-warnings
.venv/bin/python -m compileall -q app forecasting graph_rag knowledge_engine prediction_policy research_engine research_workbench vedic_engine tests
git diff --check
```

Current integrated checkpoint: the complete CVCE suite collected 339 tests and exited 0 with **338 passed, 1 skipped** using `CVCE_SWISS_EPHEMERIS_PATH=/Users/ganesha/.local/share/swisseph/ephe`; focused Person Timeline tests passed **21/21**; portal ownership tests passed **5/5**; and portal typecheck, targeted timeline ESLint and production build passed. Fresh guest, forged-owner, cross-subject-detail and live timeline smokes returned the expected 200, 403, 404 and 200 outcomes respectively. Independent Person Timeline re-review passed at **96/100 with zero Critical or High findings**. Native Muhūrta separately passed 3/3 context tests, portal typecheck, changed-file ESLint and the Next production build. Pixel visual QA remains open for both native Muhūrta and Person Timeline. Deprecation warnings remain from PyJHora, Pydantic class config, Starlette/httpx, and Skyfield/NumPy.

## Database and deployment readiness

### Supabase / persistence

- `portal/supabase-schema.sql` contains documentation for encrypted chart writes and a safe rolling migration order, but the resumable owner-scoped plaintext-to-encrypted migration tool is explicitly not included.
- `cvce/forecasting/migrations/0001_append_only_ledger.sql` is reference-only; the executable SQLite schema/triggers live in `forecasting/ledger.py`. No production adapter is wired.
- `cvce/research_engine/migrations/0001_immutable_research_store.sql` defines the local append-only research schema.
- `cvce/research_engine/timeline/migrations/0001_timeline_ledger.sql` defines the Person Timeline ledger schema. Local development currently uses `/tmp/vedicastro-person-timeline.sqlite3`; production needs an intentionally provisioned durable path and backup/retention policy before writes are enabled.
- **Applied remote state is unverified; no Supabase or other production migration was executed.** Back up and count plaintext/encrypted rows before any chart-data migration.

### Vercel portal

The portal is structurally deployable through Vercel/Next.js, but release readiness is blocked on an accepted Wave B gate, a green `npm run ci`, and provisioned server-only environment variables: `CVCE_BASE_URL`, `CVCE_SERVICE_TOKEN`, `DATABASE_URL`, `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, and an exactly 32-byte `ENCRYPTION_KEY`. No `NEXT_PUBLIC_*` service or encryption secret is permitted. There is no repository `vercel.json`; existing project/build settings remain authoritative.

### Fly CVCE

`cvce/fly.toml` targets `vedicastro-cvce` in `lhr`, forces production auth semantics, exposes port 8400, and keeps one machine running. Before deploy, provision `CVCE_SERVICE_TOKEN` matching Vercel, verify `CVCE_ALLOWED_ORIGINS`, and keep raw research disabled unless all of `CVCE_RESEARCH_MODE_ENABLED`, durable `CVCE_RESEARCH_DB_PATH`, and a distinct `CVCE_RESEARCH_SERVICE_TOKEN` are intentionally configured. Do not reuse the browser/service token for research. Deployment command after gate acceptance: `cd cvce && fly deploy --remote-only --ha=false`.

## Rollback and commit plan

Rollback is feature-first: leave v2/research flags off, restore legacy rendering/API routing, and disable the research service plane without deleting immutable research or ledger history. If a portal release fails, revert only the bounded portal commit and redeploy the prior Vercel revision. If CVCE fails, deploy the previous known-good image/commit; do not roll back append-only records. Database changes must remain additive; correct with a reviewed forward migration, never destructive rewrites.

After Wave B review and green CVCE/portal gates, stage explicit paths (never `git add .`) and commit in the seven groups above, with tests recorded per commit. Re-run `git status --short`, `git diff --cached --stat`, secret scanning, full CVCE tests, and portal CI before push. Supabase migration, Fly deployment, and Vercel deployment require separate post-gate checkpoints and verification.

## Orchestration efficiency

Exact token telemetry and per-agent model routing are unavailable, so no savings or model claims are fabricated. Bounded ownership, minimal context forks, targeted retrieval/tests, diff-focused review, and this checkpoint protocol are active.
