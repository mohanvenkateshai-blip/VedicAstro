# VedicAstro — Backlog

Opened 2026-08-11, after a ~3.5 week gap in handoff (last living-doc update: 2026-07-17). This
file exists because that gap is exactly what caused it: significant work landed with no record of
*why*, decisions were made with no trace, and one bug sat live-but-dormant across four commits
before this review caught it. Follow panchanga_muhurtha's `docs/BACKLOG.md` convention — table +
criticality + evidence — since that discipline is what caught the B-16 false-completion problem
described in V-3 below.

**Criticality:** Critical (breaks something or blocks all other work) · High (real risk, not
urgent-urgent) · Medium (should happen soon, not on fire) · Low (housekeeping).

**Status key:** ☐ pending · ◐ needs your decision before work starts · ☑ done

---

## Open

| # | Issue | Criticality | Opened | Status |
|---|---|---|---|---|
| V-1 | Uncommitted shim/de-dup diff activates `vedic_knowledge` as the primary knowledge-engine path — but `vedic_knowledge/graph/enhancer.py` imports `vedic_engine.synthesis.transit_analyzer`, and `vedic_engine` is VedicAstro-local code, not part of the "shared, portable" package. Proven **non-deterministic**: isolated test runs hard-crash (`KeyError` inside `importlib._bootstrap_external`, not a catchable `ImportError` — the existing `try/except ImportError` doesn't help), full-suite runs succeed *silently with different behavior* (traced one failure — `assert 8 == 1` in `test_search_knowledge_integration_wrapper` — to `TransitImpactAnalyzer` flipping from `None` to active depending on which test file imports `vedic_engine` first). Bisected via `git stash`: clean on committed `HEAD`, breaks with the uncommitted diff applied. 4/340 CVCE tests fail, all one root cause. **2026-08-11: independently confirmed via a separate panchanga_muhurtha-side investigation** of a real production incident — same working tree, same `KeyError: 'vedic_engine'`, same 3 failures in the research-query suite. **Also blocks the `query_research_nodes()` egress-caching fix bundled in the same diff** (`knowledge_engine/engine.py`) from being shipped alone: any `try: from vedic_knowledge import X`, including that fix's own, runs the same crash chain, since the failure is an uncaught `KeyError`, not a catchable `ImportError`. | **Critical** | 2026-08-11 (this review) | ☐ Blocks committing the uncommitted diff. Not live in VedicAstro's own deployments, but now confirmed to have already caused real cross-project harm — see V-13. |
| V-2 | `CONTEXT.md`, `STATUS.md`, `docs/handoff/context.md` all frozen at 2026-07-17 — zero record of the self-evolving memory system, B-16 Phases 1–2, the CVCE→Vercel vendoring, or the new `vedicastro-cvce-vercel` deployment. This is the direct cause of "I hadn't done handover" and of this review taking a full audit instead of reading one paragraph. | **High** | 2026-08-11 | ☑ **Rewritten (2026-08-11)** — new dated checkpoint sections added to all three files covering everything from 2026-08-01 through today, including V-7's in-progress cutover blockers. |
| V-3 | `CONTEXT.md`'s FROZEN guardrail — scope clarified. | High | 2026-08-11 | ☑ **Resolved by owner (2026-08-11):** freeze means zero influence/impact *from VedicAstro onto Muhurtha* (crossing paths risk) — it does not forbid Muhurtha's own independent development. panchanga_muhurtha's active Aug development is fine. **New follow-up risk:** the `vedic_knowledge` shared-package strategy (B-16 Phase 2) is explicitly built to be consumed by *both* apps — if panchanga_muhurtha ever imports it, a VedicAstro-side bug (e.g. V-1) could reach Muhurtha through the shared package, which is exactly what the freeze exists to prevent. Tracked as **V-12** below. |
| V-4 | B2 experiment-system code (`cvce/research_engine/{technique_registry,experiment_matrix,constraint_trace,synthesis}.py`) — internal research infra, failed independent review 3× (last 66/100), landed live via commit `7cc0acc`. Zero live exposure confirmed (not referenced by `server.py`, gated off by default via `CVCE_RESEARCH_MODE_ENABLED`). | High | 2026-07-18 | ☑ **Fresh independent review done (2026-08-11)** — the original per-finding detail from the 66/100 verdict wasn't preserved anywhere, so this was a from-scratch adversarial pass (DeepSeek v4-pro raw findings, then every claim individually verified by hand against the actual code/tests, not trusted as-is). Result: 8 of 8 checked findings were false positives once traced through the real invariants (e.g. two "wrong hash" claims turned out correct by design — confirmed via the test fixture that builds `EventEvidenceCell.configuration` as an exact snapshot mirror; a claimed race condition was actually safe since `snapshot_model()` already produces a fully detached copy before the lock; a claimed `StopIteration` crash was already guarded by the surrounding `len(directions) == 1` check). One real-but-inert issue found: `research_artifact` uses bare `assert` for fields already guaranteed non-`None` by an earlier model validator — dead under normal use, would only matter if this project ran Python under `-O`, which it doesn't. `tests/test_research_experiment_matrix.py` 30/30 pass. No code changes made — nothing genuine to fix. Whether this satisfies the *original* review's full rubric (which may have weighed non-code-correctness dimensions like B3's "mounted persistence") is unknown since that rubric wasn't preserved; flagging this honestly rather than claiming a specific numeric re-gate score I'm not positioned to certify. |
| V-5 | `knowledge-graph/graphify-out/memory-state/` (1.8MB: `runtime.json` + `node_embeddings.npz`) — generated runtime cache, not source. | Medium | 2026-08-11 | ☑ **Resolved by owner (2026-08-11):** gitignore the cache itself (`node_embeddings.npz` regenerable, `runtime.json` mutable runtime state) — but first, preserve the one valuable thing inside it: a dry-run ingest batch ("Transit Scoring Memo," 10 nodes / 2 pending community proposals / 2,485 proposed links / 64 contradiction flags) not present in canonical `graph.json`, whose original input file is already gone. Extracted to `knowledge-graph/dry-run-review/2026-08-01-transit-scoring-memo/` (tracked, marked UNVERIFIED/DRY-RUN, needs primary-source citations before promotion). Cache folder now gitignored. |
| V-6 | `supabase/migrations/20260721232500_enable_rls_guest_charts.sql` — security fix, enables RLS on `guest_charts` (Supabase advisor flagged it 2026-07-21 as publicly readable/writable/deletable via the anon key). | Medium | 2026-08-11 | ☑ Committed (`71736b5`) **and confirmed live-applied** — `supabase migration list` shows local `20260721232500` matches remote. Fully resolved. |
| V-7 | Fly→Vercel migration. | Medium | 2026-08-11 | ☑ **Resolved by owner (2026-08-11):** confirmed real cause — Muhurtha's Fly free tier was unintentionally billed and froze; no budget for Fly. **Approved: migrate VedicAstro's CVCE to Vercel too.** This makes V-1 blocking-urgent (the bug lives exactly in the path the Vercel deployment depends on). |
| V-12 | `vedic_knowledge` package (shared knowledge-engine code) is designed to be usable by VedicAstro *and* panchanga_muhurtha, which was in tension with the "zero influence onto Muhurtha" freeze principle if Muhurtha ever adopted it in-process. | Medium | 2026-08-11 | ☑ **Checked (2026-08-11): no coupling risk.** panchanga_muhurtha's `api/vedic_knowledge_bridge.py` primary path is an HTTP call to VedicAstro's deployed CVCE service (network boundary, degrades to `None`/`[]` on failure) — the in-process `vedic_knowledge` pip import is explicitly local-dev-only and isn't in panchanga_muhurtha's `api/requirements.txt`, so it never loads in their production/Vercel build. A VedicAstro-side bug (e.g. V-1) cannot reach Muhurtha in production through this package. |
| V-13 | **Real incident, already happened.** `query_research_nodes()` → `_enumerate_current_research_nodes()` (`cvce/knowledge_engine/engine.py`) did a full unfiltered Supabase `graph_nodes` table scan with no caching. Traced via Supabase Edge Logs (panchanga_muhurtha-side investigation): dozens of overlapping full-table walks in 72s, ~5.4GB egress this cycle, tripped the org-wide Supabase quota, broke Muhurtha's admin dashboard. This is *why* panchanga_muhurtha was stalled and this review happened. | **Critical** | 2026-08-11 (reported by owner, from Muhurtha-side investigation) | ☑ Fix already exists — it's the caching logic in `engine.py` I reviewed as part of V-1's uncommitted diff (TTL cache + row-count freshness check). **Cannot ship independently of V-1** — see V-1's updated description. Ships automatically once V-1 is fixed and the diff is committed. |
| V-14 | 2 chapters of `Phaladeepika_Mantreswara_1961` never embedded — DeepSeek API returned `402 Insufficient Balance` mid-run (slices 30/31). | `ingest-logs/status-report.log` | Medium | 2026-08-11 | ☑ **Re-run 2026-08-11** (owner confirmed balance was already sufficient — the 402 wasn't currently a live blocker). The local per-slice cache for this book wasn't present on disk (it's ephemeral/gitignored), so the run regenerated all 37 slices rather than resuming just the 2 — all 37 succeeded, 0 failures, committed (`76b6070`). **Scope note:** this only updates `graph-deepseek.json`, a separate diagnostic-only extraction snapshot (see V-17) — it does not touch the canonical `graph.json` CVCE actually serves from. If this book's content needs to be live in predictions, that's a different pipeline (`ingest-core-jyotisha.py`/newbooks path), not covered by this fix. |
| V-15 | 391 dormant git worktrees, `.kilo/worktrees/ensure-active-agents-*` (1–551), none active (confirmed via `ps`/`launchctl`). Disk bloat only, no functional harm. | Owner-reported | Low | 2026-08-11 | ☑ **456 of 458 pruned (2026-08-11)** via `git worktree remove`. 2 left (`feature-chara-dasha`, `feature-implementation`) — each had one trivially-dirty file (formatter whitespace noise / an orphaned dangling docstring, no real work); discarding them required `git checkout --` on uncommitted changes, which the sandbox's safety classifier correctly blocked as a destructive op. Left as-is rather than force through it — disk-bloat-only, not worth escalating. |
| V-16 | `com.vedicastro.ingest` launchd daemon has a crash-loop history — dozens of "sync-watch died — restarting" within ~20min (2026-06-29). Currently idle/dormant, underlying flakiness in `ingest-pipeline-daemon.sh`'s sync-watch was never actually fixed, just outran the issue. | `launchd.out.log` | Low | 2026-08-11 | ☐ Worth a look only before re-running ingestion — may recur. No ingestion currently running, so no action needed now. |
| V-17 | `graph-deepseek.json` has fewer nodes (23,267) than `graph.json`/`graph-core-jyotisha.json` (26,722). | Status report, flag-only | Low | 2026-08-11 | ☑ **Confirmed non-issue (2026-08-11):** `graph-deepseek.json` is a separate, standalone DeepSeek-only extraction pass, exposed only via its own diagnostic stats endpoint (`deepseek_graph_stats`, `cvce/app/server.py:1188`) — never merged into or read from the canonical serving graph (`graph.json`). No live impact. |
| V-8 | Transit Context (portal+CVCE) previously failed independent review at 68/100 (`RELEASE_HANDOFF.md`, 2026-07-14). Partially touched 2026-07-18 (blank-coordinate/timezone/stale-year fixes, commit `e2c1337`) but that was never run through a full remediation→re-gate cycle — the 68/100 verdict itself was never overturned. | Medium | 2026-07-14 (carried over) | ☑ **Fresh independent review done (2026-08-11)**, same from-scratch approach as V-4 (original findings not preserved). DeepSeek's own flagged CRITICAL finding — "client-side astronomy calculation in `GraphicalEphemeris.tsx`, violates the CVCE-only rule" — was **verified false**: the code only formats calendar/timezone strings client-side; the actual planetary-position call already goes through `postCvce("positions", ...)`, exactly per the architecture rule. The paired HIGH finding (timezone-verification bypass in `TransitWorkspace.tsx`) was also verified false — `setTransit()` is provably gated behind a successful, matching server verification with no code path that skips it. Two real, minor, non-blocking issues **were** found and fixed: a debounced place-search callback could still call React state setters after the component unmounted (added a `mounted` ref guard), and a geolocation timeout was reported with the same generic message as every other failure (now says "timed out" specifically). Verified: portal `tsc --noEmit` clean, `transit-context.test.mts` 5/5, CVCE `test_gochar_transit_context.py` 18/18. Same caveat as V-4 on the original numeric rubric being unrecoverable. |
| V-9 | `docs/prediction-engine-strategy/RELEASE_HANDOFF.md` still says B3's "Independent re-gate is pending" — it isn't; B3 passed at 97/100 on 2026-07-18. Stale doc, will mislead the next reader. | Low | 2026-08-11 | ☑ Fixed (2026-08-11) — line now reads "passed 97/100 on 2026-07-18." |
| V-10 | `cvce/graph_rag/_original_backup/`, `cvce/knowledge_engine/_original_backup/` — untracked pre-refactor safety copies. | Low | 2026-08-11 | ☑ **Deleted (owner approved, 2026-08-11).** Never tracked, nothing to commit — working tree clean. |
| V-11 | Life-Event Prediction engine (owner mandate: "did the app predict my marriage/kid/job date") — full design doc exists (`docs/prediction-engine-strategy/LIFE_EVENT_ENGINE_PLAN.md`, 2026-07-18) but zero implementation. Not urgent relative to the items above, but easy to lose track of under the volume of new B-16/Vercel work — keeping it visible here on purpose. | Low | 2026-07-18 (carried over) | ☐ |

---

## Closed (this review)

| # | Issue | Resolution |
|---|---|---|
| — | Whether any of the Aug 1–4 work is live in production | Verified no — Fly still on the 2026-07-18 image; portal still points at Fly by default. No user-facing risk from the open items above yet. |
| — | Whether the already-pushed B-16/vendoring commits (`2f8111a`..`04d2ffd`) are sound | Read in full — all four are well-reasoned, well-commented, and the deployed Vercel build (built from `04d2ffd`) verifiably works. The bug in V-1 is specific to the *uncommitted* diff on top of them. |

---

## Strategy

**Sequencing logic:** three items (V-3, V-4, V-7) are decisions only you can make, and they change
the shape of everything else — I'm not going to guess at them. Everything else has a clear
technical path once those land.

1. **You decide V-3, V-4, V-7 first.** Fifteen minutes of your input here saves redoing work —
   e.g., if V-7 means "yes, actively migrating to Vercel now," V-1 becomes urgent-blocking rather
   than just correctness debt, because the Vercel deployment is exactly the path that routes
   through the buggy package.
2. **Fix V-1** (I'll do this once you've weighed in on V-7, since the fix's urgency depends on it).
   Likely shape: inject `TransitImpactAnalyzer` into `PredictionEnhancer` from CVCE-side code
   instead of importing it inside the shared package — keeps `vedic_knowledge` genuinely portable
   and removes the import-order sensitivity entirely, not just papers over the crash.
3. **Re-run the full suite**, confirm 340/340 (not 336/340), *then* commit — in the two clean
   groups from the original review (shim/de-dup changes; the `supabase` migration separately),
   never as one giant commit.
4. **Rewrite the handoff docs** (V-2) in the same pass as the commit, per this project's own
   documentation-checkpoint rule — not "later."
5. **V-5, V-6, V-9, V-10** are small and independent — clean these up alongside step 3 rather than
   as separate sessions.
6. **V-4 (B2 remediation), V-8, V-11** are real but lower-urgency than the live correctness bug and
   the migration — sequenced after V-1/V-2/V-7 land.

## Decisions log

| Item | Decision | By | Date |
|---|---|---|---|
| V-3 | Freeze = zero VedicAstro→Muhurtha influence only; Muhurtha's own dev is unrestricted | Owner | 2026-08-11 |
| V-4 | Remediate B2 via B3-style cycle; sequenced after V-1/V-7 | Owner | 2026-08-11 |
| V-7 | Approved: migrate VedicAstro CVCE to Vercel too | Owner | 2026-08-11 |

## V-1 — fixed 2026-08-11

**Root cause fixed:** `vedic_knowledge/graph/enhancer.py` no longer imports `vedic_engine` at all —
`PredictionEnhancer` now takes `transit_analyzer` by dependency injection. CVCE's own
`app/report_facts.py` (the one real caller that needs transit intelligence) constructs
`TransitImpactAnalyzer()` locally and passes it in. Applied to both the vendored copy
(`cvce/vedic_knowledge/`) and the sibling source (`vedic-knowledge/vedic_knowledge/`) — kept in sync.

**Also found and fixed while verifying:** 4 test failures traced to a *different*, pre-existing bug
class exposed by the same refactor — 3 tests monkeypatched `knowledge_engine.integration.get_knowledge_engine`/`KnowledgeEngine`,
but those names' real implementation moved to `vedic_knowledge.knowledge.integration` during the
shim/de-dup work, so the patches silently had no effect. Fixed by retargeting the patches to where
execution actually happens now (`tests/test_knowledge_research_query.py`,
`tests/test_knowledge_search.py`). Test-target fix only — no production code involved.

**Verified:**
- 340/340 pass (was 336/340), 1 pre-existing unrelated skip
- Stable across 3 consecutive full-suite runs
- Stable in isolated single-file runs (the original crash mode) — confirms the import-order
  dependency is genuinely gone, not just hidden
- `/report/facts` (the real call site) returns 200 live against a fresh server boot, no errors in log

**Unblocks:** V-13 (egress-caching fix ships in the same commit) and the Vercel migration (V-7).

**Next:** commit in the two clean groups from the original review plan — shim/de-dup +
`vedic_engine` decoupling + test fixes as one group, `supabase` RLS migration (V-6) separately —
then push. Not yet done; waiting for your go-ahead to commit.
