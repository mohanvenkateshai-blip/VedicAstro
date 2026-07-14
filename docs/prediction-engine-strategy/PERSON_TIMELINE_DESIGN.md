# Person Timeline and Prediction Provenance Design

**Date:** 2026-07-14  
**Status:** Proposed implementation track under the Unfiltered Prediction Research Strategy  
**Purpose:** Unite a person's life history, past/current/future predictions, exact timing periods, calculation evidence, classical rules, and resolved outcomes in one inspectable environment.

## 1. Product decision

Add a first-class **Person Timeline** to each saved chart. It is distinct from the existing Dasha Timeline:

- the Dasha Timeline is technique-centred and shows planetary/sign periods;
- the Person Timeline is person-and-event-centred and shows what happened or is predicted to happen;
- selecting a milestone opens the complete chain from event claim to Mahadasha, Antardasha, Pratyantardasha and finer periods, transits, natal promise, divisional evidence, rules, sources and calculations.

This should become the central workspace connecting the Calculation Engine, Knowledge Engine, Prediction Engine, Outcome Ledger and Verbalisation Engine.

## 2. Timeline model

```text
Person / saved chart
  |
  +-- observed life milestones -------------------------------+
  |                                                           |
  +-- sealed past, current and future predictions ------------+--> unified timeline
  |                                                           |
  +-- Dasha periods + transit/fructification windows ---------+
                                                              |
                         select milestone <--------------------+
                                  |
                                  v
          Prediction explanation + exact calculation provenance
```

The timeline should have synchronized lanes:

1. **Life events:** user-confirmed, imported, inferred and unresolved milestones.
2. **Predictions:** sealed past predictions, active windows and future predictions.
3. **Timing periods:** Mahadasha, Antardasha, Pratyantardasha, Sookshma and Prana where supported.
4. **Activation windows:** slow transits, fast triggers, fructification windows, annual charts and alternative Dasha systems.
5. **Outcome status:** hit, partial hit, miss, false alarm, unresolved, ambiguous and superseded resolution.

Zoom levels should support lifetime, decade, year, month, week and day. A technique's native timing must remain intact. The UI may show a date, month or year label, but it must also show the original interval, peak and tolerance rather than forcing false day-level precision.

## 3. Milestone types and scientific identity

Every milestone has an explicit origin:

- `prospective_prediction`: prediction sealed before the outcome window;
- `observed_event`: event entered or confirmed by the person;
- `retrospective_hypothesis`: engine explanation generated after the event was known;
- `imported_history`: event imported from a permitted personal source;
- `engine_inference`: candidate event inferred but not confirmed;
- `prediction_resolution`: later assessment linking an observed event to a sealed forecast.

These types are never collapsed. A retrospective match is useful for learning techniques, but it is not evidence that the engine predicted the event in advance.

Suggested visual language:

- solid marker: confirmed observed event;
- outlined marker: sealed prospective prediction;
- split marker: prediction matched to an outcome;
- dotted marker: retrospective hypothesis;
- open marker: unresolved or unconfirmed event;
- shaded band: prediction/timing interval;
- vertical line within a band: predicted peak date.

This is a measurement distinction, not a content filter: every record remains visible and research-queryable.

## 4. Milestone detail experience

Selecting a milestone opens a full-page detail view or wide side sheet with these sections.

### 4.1 Human-readable prediction

- precise event statement;
- favourable, unfavourable or mixed direction for that event;
- predicted start, peak, end, native resolution and tolerance;
- expected manifestations and observable signs;
- conditions under which the event changes or does not materialise;
- what counts as a hit, partial hit, miss or false alarm;
- prediction creation time and whether it was prospective or retrospective.

### 4.2 Timing ladder

Show the active hierarchy at the predicted peak:

```text
Vimshottari
Saturn Mahadasha      2020-04-18 -> 2039-04-18
  Venus Antardasha    2026-02-09 -> 2029-04-11
    Jupiter PD        2027-01-13 -> 2027-06-22
      Mercury SD      2027-03-04 -> 2027-03-27
```

Each level is clickable and deep-links to the corresponding node in the existing Dasha explorer. Parallel ladders from Yogini, Chara, Kalachakra, Ashtottari, KP or annual systems are shown separately rather than merged prematurely.

### 4.3 Why the engine predicted it

Present an event-specific evidence chain:

1. natal promise and relevant houses/lords/karakas;
2. divisional-chart confirmation or contradiction;
3. Yoga formation, strength, cancellation and activation;
4. Dasha activation through each period level;
5. slow-planet transit/fructification window;
6. fast trigger or exact-date signal;
7. Ashtakavarga/Kaksha/KP/annual/Prashna evidence where applicable;
8. supporting, opposing and neutral techniques;
9. event-specific combination method and configuration.

Every evidence row links to its raw score, exact calculation inputs, formula/rule version, school configuration, Knowledge Graph node, original source passage and experiment metrics.

### 4.4 Calculation trace

Provide an expandable technical trace:

- birth/input snapshot and provenance grade;
- ayanamsa, ephemeris, nodes, house system and timezone rules;
- planetary longitudes and relevant derived positions;
- exact Dasha boundary calculations;
- transit/aspect/orb/bindu values;
- native technique scores before normalization;
- code, graph, corpus, rule-pack and model versions;
- replay/run ID and artifact hash.

The trace turns “trust us” into an auditable explanation and enables exact reproduction.

### 4.5 Outcome and feedback

For completed windows, allow the person to record:

- whether the event occurred;
- actual date or interval and their uncertainty about it;
- event subtype and magnitude;
- partial manifestations;
- related evidence or notes;
- whether the prediction was useful and understandable.

The original forecast is immutable. Feedback creates an append-only resolution record so the engine can learn without rewriting history.

## 5. Data contracts

### `PersonTimeline`

- `timeline_id`, `subject_id`, encrypted chart/input reference
- visible range, zoom and filter preferences
- creation/update timestamps
- linked prediction release and outcome-ledger versions

### `TimelineMilestone`

- stable milestone ID and origin type
- canonical event ID plus original user/technique label
- event title, description, direction and magnitude
- start, peak, end, native temporal unit and tolerance
- observed/predicted/retrospective status
- confidence or native score references, never invented probability
- creation time, sealing time and author/engine provenance
- visibility and de-identification metadata

### `MilestonePredictionLink`

- milestone and raw-prediction IDs
- relation: predicted, supports, contradicts, matched, partial-match, unrelated
- match method and match version
- prospective/retrospective identity
- immutable temporal-order proof

### `MilestoneEvidenceLink`

- technique run, configuration and rule IDs
- Dasha system, level, lord/sign, start/end and path
- evidence role: natal promise, activation, trigger, support, opposition
- native score reference and calculated artifact pointer

### `MilestoneResolution`

- append-only resolution event
- actual event interval and certainty
- hit/partial/miss/false-alarm/ambiguous/unresolved status
- resolver and resolved timestamp
- notes and subsequent superseding resolution ID

## 6. Matching and timeline generation

Use two separate processes.

### Prospective generation

1. Generate event hypotheses without seeing future outcomes.
2. Store exact event/window/evidence records.
3. Seal the release with a timestamp and hash.
4. Render its milestone bands immediately.
5. Resolve after the observation window closes.

### Retrospective research

1. Accept an observed milestone and its date uncertainty.
2. Run every technique/configuration around the event window.
3. Show which techniques align, contradict or fail.
4. Mark all generated explanations as retrospective.
5. Use results for hypothesis discovery and ablation, never as prospective accuracy.

Matching must be event-specific and tolerance-aware. It should not mark any pleasant event inside a broad favourable period as a hit. Exact matching criteria are frozen with each prediction release.

## 7. Integration with existing VedicAstro modules

| Existing asset | Timeline use |
|---|---|
| `/chart/dasha` and `DashaDeepTree` | Deep links to exact MD/AD/PD nodes and period panels |
| `DashaSeriesChart` | Monthly/weekly activation series behind a milestone |
| fructification windows | Candidate manifestation bands and peaks |
| Kalachakra leap timeline | Parallel sign-Dasha activation lane |
| report `priority_predictions` | Initial migration source for predicted milestone candidates |
| v2 forecasting contracts and ledger | Sealed prediction identity and outcome resolution |
| Knowledge Engine/GraphRAG | Rule, contradiction, source and textual-fidelity provenance |
| Research Engine `TechniqueRun` | Complete raw evidence and replay trace |
| Prediction Verbalisation Engine | Milestone statement and explanation paragraphs |
| saved charts/authentication | Person identity, chart ownership and encrypted birth context |

Do not overload the existing Dasha page. Add `/chart/timeline` as the person's primary life-event workspace and keep `/chart/dasha` as the technical period explorer.

## 8. Implementation modules

### CVCE

- `cvce/research_engine/timeline/contracts.py`
- `cvce/research_engine/timeline/service.py`
- `cvce/research_engine/timeline/matcher.py`
- `cvce/research_engine/timeline/provenance.py`
- `cvce/research_engine/timeline/narration.py`
- endpoints for timeline query, milestone detail, event capture and append-only resolution
- migrations for timelines, milestones, prediction/evidence links and resolutions

### Portal

- `portal/src/app/(main)/chart/timeline/page.tsx`
- `portal/src/components/timeline/PersonTimeline.tsx`
- `TimelineControls`, `TimelineLanes`, `MilestoneMarker`, `MilestoneDetailSheet`
- `TimingLadder`, `EvidenceChain`, `CalculationTrace`, `OutcomeResolutionForm`
- add **Person Timeline** to `ChartSidebar` above the technique-specific Dasha Timeline
- extend `portal/src/lib/types.ts` and `cvce.ts` with the canonical timeline contracts

Before implementation, read the repository's installed Next.js documentation as required by `portal/AGENTS.md`.

## 9. Delivery sequence

### T0 — Contracts and provenance

Define milestone identity, origins, precision, links, immutable sealing and resolution semantics. Add migrations and round-trip tests.

### T1 — Read-only timeline

Render Dasha backgrounds and existing priority predictions as explicitly migrated/legacy candidates. Add exact deep links to Dasha nodes and sources.

### T2 — Person-entered history

Allow confirmed events, date ranges, uncertainty and notes. Encrypt person-linked data and support correction through superseding events.

### T3 — Full evidence drawer

Connect raw technique runs, Knowledge Graph rules, contradictions, calculations, configuration and narration.

### T4 — Prospective sealing and resolution

Display sealed future predictions, close evaluation windows, request outcomes and update the append-only ledger.

### T5 — Comparative research overlays

Toggle schools, Dasha systems, configuration arms, prospective versus retrospective views, and show technique agreement/contradiction.

## 10. Acceptance criteria

- A milestone can be traced to the exact prediction record and MD/AD/PD or alternative-system path.
- Every displayed sentence links to evidence; no generic bucket list is presented as a milestone prediction.
- Exact date/month/year labels preserve the original interval, peak, tolerance and native resolution.
- Prospective and retrospective records are unmistakable and cannot be converted into each other.
- A user-entered event cannot mutate a sealed prediction.
- Corrections and resolutions are append-only and replayable.
- Supporting and opposing techniques are both visible.
- All raw technique outputs remain available to research even if not selected for a timeline summary.
- Timeline matching uses frozen, event-specific criteria and reports false alarms and misses.
- The portal can deep-link from a milestone to Dasha, source, rule and calculation details and back without losing context.

## 11. Strategic value

The Person Timeline is more than a presentation feature. It creates the missing learning loop:

```text
calculation -> technique evidence -> dated prediction -> person timeline
    -> observed milestone -> resolution -> technique evaluation -> improved synthesis
```

It makes prediction logic understandable to the person while simultaneously building the point-in-time outcome dataset required to replace the current `N/A` accuracy baseline with honest event-family, horizon and timing metrics.
