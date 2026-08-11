# Transit Scoring Memo — dry-run ingest batch

**Status: UNVERIFIED / DRY-RUN.** Not in `graph.json`. Not part of the canonical knowledge base.
Nothing here should back a prediction, a UI claim, or a citation until it clears the review below.

**Why this exists:** found sitting only in `knowledge-graph/graphify-out/memory-state/runtime.json`
(a regenerable local cache, now gitignored — see `docs/BACKLOG.md` V-5) during the 2026-08-11
project review. The batch's own temporary input file (`ingest_1785608009.md`) is already gone.
Preserved here, verbatim, before the cache it lived in got ignored — see `raw-batch.json` for the
exact untouched data (all 10 nodes, both mutation proposals, all 64 contradictions, all 2,485
proposed links).

## What it is

A single markdown memo (`ingest_1785608009.md`, source no longer on disk) was run through the
self-evolving memory pipeline's ingest as a pilot/test on 2026-08-01. It produced 10 graph nodes
(the memo doc + 3 structural concepts + 6 actual claims), matched against the existing 400-node
corpus at the time.

**No primary-source citation exists for any of the 6 claims below** — the memo states them as bare
rules with no author, no text, no chapter/verse. That absence is exactly why this needs review
before promotion, independent of whether the claims are individually true.

## The 6 claims

| # | Claim | Contradictions flagged |
|---|---|---|
| 1 | Jupiter transit over lagna is auspicious and beneficial | **30** |
| 2 | Saturn transit over Moon is inauspicious and malefic | **17** |
| 3 | Rahu-Ketu axis scoring uses house from lagna | 0 |
| 4 | Ashtakavarga bindus modify transit strength | 0 |
| 5 | Kaksha refinement applies to Sade Sati only | 0 |
| 6 | Benefic aspects raise the score | **17** |

## The 64 contradictions — the actual review question

All 64 land on just 3 of the 6 claims (30 + 17 + 17). In every case, the pattern is the same: the
memo states a **blanket, unqualified rule**; the existing graph — mostly nodes already sourced from
`Gochar_Phaladeepika_Pulippani` — carries **house-specific, nuanced classical rules** that
contradict the blanket version for particular placements.

**Example** (full detail in `raw-batch.json`):
- Memo claim: *"Jupiter transit over lagna is auspicious and beneficial"* (unqualified, no source)
- Existing, sourced node: *`gochar_phaladeepika_pulippani_jupiter_in_3_worst`* — "Jupiter in 3rd
  from Moon = WORST Jupiter transit: ominous sorrow, fear, sibling ill-health, displacement, debt,
  loss of job/business" (score 0.686)

This is not necessarily a *factual* error in the memo — "Jupiter over lagna is generally auspicious"
is a defensible classical generalization — but it's exactly the kind of generalization the existing,
sourced corpus already refines by house, and shipping the unqualified version into the graph
alongside the refined version would create a real internal contradiction the engine has no way to
resolve. **This is precisely why the batch needs primary-source citations and a house-by-house
qualification pass before promotion, not a straight merge.**

Claims 3–5 (Rahu-Ketu axis, Ashtakavarga bindus, Kaksha/Sade-Sati) triggered zero contradictions —
lower review risk, but still uncited.

## Pending structural proposals (not yet applied)

Two auto-generated community-clustering proposals sit alongside this batch, also unreviewed:

| Proposal | Node count | Justification |
|---|---|---|
| `community:ingest_ingest` | 10 | All 10 batch nodes share the `ingest_ingest` prefix, not yet its own community among the existing 120 |
| `community:ingest_ingest_claim` | 6 | The 6 claim nodes specifically, same reasoning |

## Supporting data (not reviewed in detail here)

**2,485 proposed semantic links** from this batch to existing corpus nodes (confidence-scored,
`INFERRED`, none applied) — preserved in full in `raw-batch.json` for whoever does the promotion
review, not reproduced here since they're supporting signal, not claims needing a yes/no.

## Before promotion, this batch needs

1. A primary-source citation for each of the 6 claims (author, text, chapter/verse — matching the
   sourcing standard every other node in the graph already carries, e.g. `Gochar_Phaladeepika_Pulippani`).
2. For claims 1, 2, and 6 specifically: house-by-house qualification reconciling the blanket
   statement against the 64 flagged contradictions, or an explicit decision to drop the unqualified
   version in favor of the existing nuanced nodes.
3. A decision on the 2 pending community proposals.
4. Only then: re-run through the real ingest pipeline (not this preserved snapshot) so it lands in
   `graph.json` with proper provenance — this file is a record of what was found, not a promotion
   mechanism.

## Files

- `README.md` — this file
- `raw-batch.json` — exact, untouched extract from `runtime.json`: `batch_meta`, `batch_nodes` (10),
  `pending_community_mutations` (2), `contradictions` (64), `proposed_links` (2,485)
