# Supabase Egress Incident and Production Graph Cutover

**Record date:** 2026-08-22
**Owner decision:** Make Vercel the sole production CVCE path, move normal graph reads to
baked SQLite, remove the portal diagnostic corpus reader, disable the unattended Fly health
schedule, and scale the sunset Fly app to zero.
**Current state:** Migration and shutdown actions are complete; the one-week observation
window remains open. Review after **2026-08-29T21:30:24+0100** before deleting the manual-only
health workflow.

## Executive outcome

| Area | Final state | Evidence |
|---|---|---|
| Production CVCE | Vercel, SQLite-backed | Production `GRAPH_SOURCE=sqlite`; live `/graphinfo` reported `sqlite-baked@523f27371b346c100baed1c6d1ebae7abac28d64` |
| Graph snapshot | Baked into the CVCE deployment | 26,722 nodes, 38,881 links, 1,773 hyperedges; 18,604,032-byte `graph.db` |
| Provenance bundle | Present in the Vercel function | 62 structured JSON files, node-chapter map, 12 canonical patch files |
| Portal Admin corpus | Removed | `/admin/knowledge`, `KnowledgeExplorer`, `/api/admin/corpus/*`, and `portal/src/lib/corpus.ts` removed |
| Learn product | Removed | Main navigation, masthead search, reader routes, and unreferenced corpus reader/asset proxy removed |
| Fly CVCE | Scaled to zero, app preserved | Machine `d8d96956ae5308` removed with `fly scale count 0 -a vedicastro-cvce --yes`; no running image/machine remains |
| Health monitor | Scheduled trigger disabled; manual dispatch retained | `.github/workflows/health-monitor.yml`; delete after the observation window if rollback is not needed |
| Supabase credentials | Retained intentionally | Still needed by portal auth/chart/storage and CVCE fallback, parity, and research code paths |
| `_supabase_rest.py` | Retained intentionally | Still imported by `SupabaseKnowledgeStore`; owner-owned dirty UTF-8 URL fix was not staged or changed |

## Incident and root-cause history

The original incident was not ordinary user traffic. The panchanga_muhurtha-side Supabase
Edge Log investigation found `query_research_nodes()` calling
`_enumerate_current_research_nodes()` through an unfiltered `graph_nodes` scan. Dozens of
overlapping walks produced approximately 5.4 GB of egress in roughly 72 seconds and tripped
the shared organization quota, breaking the Muhurtha Admin dashboard.

The first mitigation reduced cache-miss frequency, but did not remove the expensive first
scan after a cache miss. The durable fix was to stop using Supabase as the normal runtime
graph store and ship the graph as a baked SQLite database.

## Timeline and decisions

| Timestamp | Event | Exact record/evidence |
|---|---|---|
| 2026-08-11 | Root incident recorded: full-table Supabase graph scans caused the quota event. | V-13 in `docs/BACKLOG.md`; panchanga_muhurtha investigation supplied the Edge Log evidence |
| 2026-08-11T16:53:35+01:00 | KnowledgeEngine refactor and cache mitigation committed. | `c779525`; dependency-injection fix plus TTL/row-count cache work landed and was tested |
| 2026-08-14T06:52:52+01:00 | Status record marked the egress fix shipped but not yet deployed. | `f426b5f` |
| 2026-08-22T11:29:38+01:00 | Cache TTL reduced to 60 seconds as an interim mitigation. | `2f0c656`; necessary but not permanent |
| 2026-08-22T17:11:37+01:00 | SQLite bake and store implementation committed. | `ff39ace`; `build_graph_db.py`, `SQLiteKnowledgeStore`, parity tooling, deployment workflows, and tests |
| 2026-08-22T18:47:40+01:00 | `/graphinfo` diagnostic endpoint committed. | `161c4be` |
| 2026-08-22 | Preview bundle verified in Vercel. | `dpl_2f3DCg86RLXAuoHN1KcM6CaqzHBs`; graph database and provenance assets were present in `/var/task/knowledge-graph` |
| 2026-08-22 | Production SQLite flag enabled and verified. | `dpl_i1QKUoMbvPvqKofybAvxu4hcWkXB`; authenticated `/graphinfo` proved SQLite backend and graph counts |
| 2026-08-22T20:44:12+01:00 | Owner decided not to build or migrate the portal Learn feature. | V-19; Learn removed in `f1d4197` |
| 2026-08-22T21:06:13+01:00 | Diagnostic Admin corpus removed. | `dc55618`; direct portal graph-query routes and library removed; live deployment followed |
| 2026-08-22T21:07:56+01:00 | Admin removal release evidence recorded. | `9a36f2b`; later stable docs-only deployment `dpl_CKchQ24BxUpEeFt3DnmvaFx22SH4` |
| 2026-08-22T21:13 approximately | Owner supplied Supabase Usage screenshot. | Current cycle 18 Aug–18 Sep: 6.94 GB used against 5 GB, 1.94 GB over; 21 Aug tooltip showed 2.143 GB PostgREST and 630.522 KB Auth egress |
| 2026-08-22 | Background caller investigated. | GitHub Actions health monitor ran about 40 times on 21 Aug and called old Fly `/health/deep`; Fly had no `GRAPH_SOURCE=sqlite` setting |
| 2026-08-22T21:28:16+01:00 | Owner selected the sunset path: disable the schedule, retain manual checks temporarily, and shut down Fly. | V-21 directive captured in `docs/BACKLOG.md` and `docs/handoff/context.md` |
| 2026-08-22T21:29:00+01:00 | Ten-minute monitor schedule disabled and pushed. | `6702eb7`; `workflow_dispatch` retained |
| 2026-08-22T21:30:24+01:00 | Fly machine scaled to zero after Vercel health pre-check passed. | `fly scale count 0 -a vedicastro-cvce --yes`; Vercel `/health` 200; Fly status empty; old Fly URL timed out |
| 2026-08-22T21:30:44+01:00 | Shutdown evidence committed and pushed. | `3c50ea9` |

## Health-monitor finding: confirmed versus inferred

The monitor is a confirmed unattended caller, but the screenshot alone does not prove that
every byte of the 2.143 GB was caused by it.

| Claim | Evidence level | Detail |
|---|---|---|
| GitHub Actions was making requests without human app use | Confirmed | `.github/workflows/health-monitor.yml` had a `*/10 * * * *` schedule; `gh run list` found about 40 successful scheduled runs on 21 Aug |
| The monitor targeted the old Fly deployment | Confirmed | Each run called `https://vedicastro-cvce.fly.dev/health/deep`, not Vercel |
| The old Fly runtime defaulted to Supabase graph access | Confirmed by configuration | `GRAPH_SOURCE` was absent from `cvce/fly.toml`; integration defaults to `supabase` |
| Every `/health/deep` request transferred the full graph | Not confirmed | The direct Supabase health check is `GET graph_nodes?select=id&limit=1`; KnowledgeEngine initialization can nevertheless reconcile the research graph and perform a larger scan |
| The monitor/Fly path explains the 2.143 GB day | Leading inference, not final proof | 2.143 GB divided by about 40 runs is roughly 55 MB per run, graph-scale. Supabase request logs filtered by `graph_nodes` and caller identity are required for final attribution |

The monitor did not intentionally keep Fly alive; Fly was configured with
`auto_stop_machines = "off"`. It did continually exercise a sunset service whose runtime
still had a Supabase-backed default. Disabling the schedule removes that confirmed
background caller. Scaling Fly to zero removes the service endpoint itself.

## Removal boundaries

The Admin corpus and Learn removals were deliberately narrower than deleting Supabase from
the whole system.

| Preserved path | Why it remains |
|---|---|
| Portal Supabase client | Auth, charts, profile/avatar storage, and other portal operations still use it |
| `SupabaseKnowledgeStore` | Fallback/research/parity code still imports it; production normal graph reads use SQLite when `GRAPH_SOURCE=sqlite` |
| `_supabase_rest.py` | Required by `SupabaseKnowledgeStore`; its owner-owned URL-encoding fix remains unstaged |
| CVCE knowledge endpoints | User-facing chart/source/prediction paths remain active and now resolve their normal graph store through production SQLite |
| Manual health workflow dispatch | Kept for one week in case rollback evidence is needed |

## Verification record

| Check | Result |
|---|---|
| CVCE SQLite direct tests | Passed; graph counts and store health verified |
| CVCE full suite | Passed in the cutover verification |
| Panchanga bridge/retrieval smoke | 43/43 passed; full suite recorded 207 passed, 4 skipped, and 6 unrelated encryption-test failures |
| Portal build | Passed with local placeholder Supabase build variables; no real Supabase access used |
| Portal typecheck | Passed |
| Portal unit tests | 29 passed, 0 failed |
| Targeted lint | Passed for edited Admin files |
| Full repository lint | Not green because generated `.vercel/output` bundles contain baseline errors; this was recorded rather than hidden |
| Live Vercel CVCE | `/health` 200; `/graphinfo` reported SQLite backend, database present, 26,722 nodes, 38,881 links |
| Live portal | Homepage 200; removed corpus API/asset routes 404; Admin auth redirects preserved |
| Fly shutdown | `fly status` showed no running image/machine after scale-to-zero |

## Observation and close gate

Do not interpret the existing 6.94 GB as a post-fix rate. Supabase usage is cumulative for
the billing cycle and cannot be reduced by deleting the caller. The next useful evidence is
the daily PostgREST value after the Fly schedule and machine are gone.

Before deleting `.github/workflows/health-monitor.yml`, verify:

1. Vercel CVCE `/health` and `/graphinfo` remain healthy.
2. No rollback to Fly is required.
3. Supabase daily PostgREST egress materially drops and no unexpected graph-table caller is
   visible in logs.
4. The owner accepts losing the manual Fly health probe and its GitHub issue alert path.

Until that review, V-21 remains **Observation**, not closed. No production payment or plan
upgrade was made, and no Supabase credentials were deleted.
