# Unfiltered Prediction Research Strategy

**Date:** 2026-07-14  
**Status:** Corrected governing strategy for private research  
**Supersedes:** Research restrictions in `STRATEGY.md`  
**Objective:** Learn which Vedic prediction techniques, combinations, configurations, and timing methods actually improve prediction accuracy without censoring the experiment or discarding inconvenient results.

## 1. Governing decision

The prediction research system is a lossless laboratory, not a publishing system.

No technique, event domain, timing resolution, configuration, score, contradiction, failed rule, false alarm, miss, raw narrative, or low-confidence result may be blocked, softened, widened, replaced, or erased before it is recorded and evaluated. Controls such as provenance, leakage detection, negative controls, reproducibility checks, and outcome validation remain mandatory because they measure scientific quality; they do not censor prediction generation.

Any future public-facing policy is a separate terminal adapter operating on a derived copy **after** the immutable research record is sealed. It cannot write back to, alter, or determine what the research engine runs.

The central invariant is:

> Every technique runs; every result and native resolution is preserved; every contradiction, miss, and failure remains measurable.

## 2. Non-negotiable research invariants

1. Every registered technique can run, including techniques covering sensitive or uncomfortable event classes.
2. The engine stores the original technique output before normalization, aggregation, narration, or policy transformation.
3. Native scores, scales, units, polarity, formulas, intermediate values, and configuration identifiers are retained.
4. Sensitive domains are ordinary research domains, not excluded domains.
5. Exact technique timing is retained: an instant or minute must not be widened to a day, week, or month.
6. Instability, missing evidence, conflict, out-of-distribution input, weak sourcing, and low sample size are annotations—not reasons to suppress a record.
7. One malformed or unmapped item is quarantined individually; it must not fail or erase the rest of a technique run.
8. All schools and configurations are comparable experiment arms. No preferred school silently becomes truth.
9. Invalidated, contradicted, unhealthy, and low-confidence knowledge nodes remain queryable for retrospective analysis.
10. Raw, normalized, revised, and narrated predictions are separately versioned and linked.
11. Misses, false alarms, abstentions, unresolved forecasts, and failed rules remain visible in their correct denominators.
12. Scientific controls may challenge a technique's validity but never prevent its generation or preservation.

## 3. Correct architecture

```text
Encrypted subject/input snapshot
        |
        v
School x technique x parameter x timing-resolution experiment matrix
        |
        v
Immutable TechniqueRun + native RawPrediction + RawScore records
        |
        +--> lossless normalization and per-item quarantine
        +--> research annotations: conflict, stability, provenance, leakage, OOD
        +--> progressive-constraint stages and ablations
        +--> outcome ledger and comparative evaluation
        +--> unrestricted, de-identified research narration
        |
        v
Optional future ProductPresentationAdapter over a derived copy only
```

The research API and storage layer must never call the product presentation adapter. The product adapter consumes sealed research records through a read-only interface.

## 4. Canonical lossless contracts

### 4.1 `TechniqueConfiguration`

- `configuration_id` and stable configuration hash
- school and lineage
- ayanamsa and ephemeris
- house and bhava systems
- dasha system and depth
- aspect, orb, node, combustion, retrogression, and strength rules
- divisional-chart mappings
- location, timezone, calendar, and birth-time policy
- technique-specific parameters
- engine, package, rule-pack, and source versions

### 4.2 `TechniqueRun`

- immutable run ID
- subject/input snapshot ID
- technique and configuration IDs
- exact code, data, ephemeris, and rule-pack versions
- start/end timestamps and execution status
- complete raw payload or content-addressed raw artifact
- item-level results and quarantines
- deterministic replay information

### 4.3 `RawPrediction`

- technique-native event label and unmodified statement
- optional normalized event mappings, allowing one-to-many and unmapped values
- exact start, peak, end, tolerance, and native time unit
- direction, magnitude, conditions, supporting and opposing factors
- natal promise, period activation, transit trigger, and micro-trigger components
- raw prose plus every later narrative revision
- provenance to formula, rule, source, and intermediate evidence

### 4.4 `RawScore`

- `technique_id`, `score_name`, numeric or categorical value
- units, native scale, valid range, and polarity mapping
- formula and formula version
- normalized score as an additional field, never a replacement
- uncertainty and stability estimates when available

### 4.5 `ResearchAnnotation`

Annotations include low confidence, contradiction, missing inputs, OOD, source weakness, licensing limitations, calculation disagreement, instability, leakage suspicion, sparse sample, unresolved outcome, and product-display eligibility. An annotation never deletes or overwrites the annotated record.

## 5. Open event and timing registries

Replace the research engine's closed six-domain/nine-event taxonomy with versioned, extensible registries. Preserve original labels even after mapping.

The research event registry must allow all domains, including marriage and relationships, conception and pregnancy, health and disease, injury, surgery, death and longevity, accidents, violence, crime and legal events, money and loss, employment and profession, education, property, travel and migration, family, spiritual events, and any newly observed category.

The timing registry must support instant, minute, ghati, hora, day, tithi, nakshatra interval, week, fortnight, month, quarter, year, multi-year, open interval, technique-native unit, and explicit tolerance. Horizons are experiment parameters, not hard-coded exclusions.

## 6. Exhaustive technique laboratory

The registry and experiment runner must cover, at minimum:

- Natal promise: D1, bhava and lord analysis, karakas, yogas, shadbala, avasthas, divisional charts, Parashari, Jaimini, and documented Nadi methods.
- Period systems: Vimshottari through all available sub-levels, Yogini, Ashtottari, Chara/Narayana, Kalachakra, and annual Mudda/Tajika periods.
- Transits: from lagna, Moon, relevant house lords and dasha lords; Saturn-Jupiter frameworks; vedha, latta, tara, moorthi, retrogression, combustion; fast-planet, Moon, daily and hora triggers.
- Strength and point systems: BAV, SAV, kaksha, bindu transit interpretations, and combinations with dasha/transit stages.
- Other timing schools: KP significators and sub-lords, Varshaphala, Muntha, sahams, solar/lunar/monthly/daily revolutions, Prashna, Panchanga, and Muhurta.
- Remedies as testable interventions: diagnosis, proposed mechanism, protocol, timing, adherence, outcome, non-completion, adverse effects, and competing explanations.

Source fidelity and empirical accuracy are separate axes. A faithfully implemented classical rule may perform poorly; a hypothesis may perform well before strong textual support is found. Preserve both facts.

## 7. Progressive constraint becomes an experiment

Natal promise -> period activation -> slow transit -> fast trigger is a valuable hypothesis, but must not be a gate that prevents a forecast.

Run and store:

- each stage alone;
- every pair and higher-order combination;
- the full progressive chain;
- order-sensitive variants where the school requires them;
- stage-removal ablations;
- alternative thresholds and weighting functions.

This permits measurement of whether each constraint improves precision, recall, calibration, timing error, or only reduces coverage. A constraint earns use through incremental skill, not authority or intuition.

## 8. Schools and parameters are a comparison matrix

Run all supported ayanamsas, house/bhava systems, ephemerides, dasha choices, divisional mappings, orbs, node treatments, aspect rules, and school-specific interpretations. Each arm receives a stable configuration hash. Do not average incompatible systems before their individual outputs are stored.

Use hierarchical evaluation to identify:

- universally useful signals;
- school-specific signals;
- cohort-specific signals;
- redundant techniques;
- contradictory techniques;
- combinations that improve out-of-sample performance.

## 9. Cross-engine verification

- Use Swiss Ephemeris and JPL data for numerical astronomy verification.
- Build offline adapters for VedAstro and, where technically/licensably feasible, Jagannatha Hora exports.
- Adopt the useful architectural pattern of a versioned event registry, delegated calculations, fine time slices, and interval compression.
- Treat external prose or claims of perfect prediction as unverified hypotheses, never as accuracy evidence.
- Expand golden fixtures from the present minimal set to at least 30 charts, emphasizing sign, nakshatra, tithi, dasha, ingress, retrogression, timezone, DST, polar-location, and birth-time boundaries.

Cross-engine disagreement is stored as evidence. It does not cause silent selection of whichever result looks preferable.

## 10. Evaluation without suppression

### Baselines and controls

- M0 population/base-rate baseline
- person-history baseline where legitimate historical features exist
- calendar and seasonality baselines
- M1 non-astrological feature baseline
- shuffled birth charts
- shifted event dates
- randomized dasha assignments
- unrelated chart-event pairing
- individual-technique and progressive-stage ablations

### Statistical models

Use point-in-time evaluation, discrete-time survival/hazard models, competing-risk models for mutually competing events, calibration models fitted only on training folds, and prospective frozen releases. Keep exploratory and confirmatory analyses distinct.

### Required metrics

- hits, misses, false alarms, true negatives, sensitivity, specificity, precision, and coverage
- Brier score, Brier skill, log loss, calibration intercept/slope/error, sharpness, and discrimination
- exact-time error, interval coverage, lead time, peak-time error, and tolerance-aware scoring
- subgroup results, including small groups with explicit uncertainty rather than suppression
- birth-time stability and cross-engine stability
- incremental skill of every technique and constraint
- confidence/credible intervals and sample counts

Sparse or unstable results must be returned with flags and intervals. They are not hidden. Unresolved outcomes remain unresolved rather than being treated as failures or successes.

## 11. Research Workbench correction

Change the pipeline to:

```text
RawResearchCapture
    -> EvidenceAssessment
    -> ExperimentalRulePack
    -> optional PromotedRulePack
```

Capture first. LLM-generated, uncited, contradictory, weakly sourced, unapproved, or redistribution-restricted material is retained with explicit provenance and status. It may enter hypothesis generation and sandbox experiments. Promotion to a canonical production rule pack remains evidence-based, but non-promotion must not erase the hypothesis or its experiment history.

Licensing controls code execution, copying, redistribution, and product bundling; it must not cause deletion of bibliographic metadata, findings, reproducible observations, or independently expressed hypotheses.

## 12. Knowledge engine and narration

Research queries must optionally include every invalidated, unhealthy, contradicted, superseded, and low-confidence node. Query defaults in the research plane are exhaustive, not curated.

Build an unrestricted Research Narration Engine that can verbalise the complete, de-identified `TechniqueRun`, including:

- the precise predicted event and direction;
- exact time window, peak and tolerance;
- technique-by-technique reasoning;
- agreements and contradictions;
- conditions that change the interpretation;
- probability or score only on its truthful native/calibrated scale;
- expected observable manifestations;
- what outcome would count as a hit, partial hit, miss, or false alarm;
- alternative explanations and uncertainty sources.

It must not turn broad buckets such as “good for marriage, travel, contracts and abundance” into artificial specificity. Specific prose must be generated only from specific upstream event claims. De-identification removes direct identifiers; it must not remove predictive calculation features.

## 13. Existing application modules: accuracy improvement map

Yes: the existing VedicAstro modules should be improved as one connected prediction system. The Knowledge Graph does not merely decorate a finished prediction, and the prediction engine must not compensate for incomplete calculations or vague rules. Every layer has a distinct accuracy responsibility.

| Existing module | Current strength | Accuracy limitation found | Required improvement | How improvement is measured |
|---|---|---|---|---|
| `vedic_engine/core/astronomy.py` | Deterministic planetary, node and ascendant calculations | One principal ayanamsa/calculation path and locally implemented astronomy can create systematic boundary errors | Add Swiss Ephemeris/JPL reference adapters; configurable ayanamsa, true/mean nodes, topocentric/geocentric mode, house system and ephemeris; retain every configuration arm | Arc-second disagreement, sign/nakshatra/pada/house boundary agreement, cross-engine stability |
| `vedic_engine/core/panchanga.py` | Tithi, nakshatra, yoga, karana, sunrise and boundaries | Accuracy near transitions depends on timezone, sunrise convention and numerical search precision | Use timezone IDs plus historical DST, configurable sunrise/day convention, high-precision root finding and boundary uncertainty | Boundary-time error and golden-fixture agreement |
| `knowledge_engine/` | Central graph versioning, retrieval, refresh and engine registration | Research access filters invalidated/unhealthy nodes; prose nodes are not yet a complete executable rule representation | Add exhaustive research queries and typed rule nodes with antecedent, consequent, event target, timing, school, exceptions, strength, source passage, contradiction links and evidence status | Rule coverage, source-to-rule traceability, contradiction recall, executable-node percentage |
| `graph_rag/` | Classical citations, graph context and contradiction discovery | Primarily enriches predictions after calculation; retrieval can return relevant prose without proving rule applicability | Compile retrieved rules into chart-specific evidence only when their formal antecedents match; preserve non-matches and competing interpretations | Retrieval precision, rule-applicability precision, added out-of-sample skill |
| `rules_engine/engine.py` and `vedic_engine/rules/` | Structured transit, vedha, tara, moorthy and related tables | Many outputs are broad verdicts or prose; formulas, exceptions and native strength are not uniformly represented | Convert each tradition into atomic, versioned, testable rules with event mapping, exact scope, polarity, native score, prerequisites and exceptions | Rule-level fixtures, mutation tests, source fidelity, incremental skill |
| `vedic_engine/prediction/dasha.py` and `chara_dasha.py` | Vimshottari, Yogini and Chara timing foundations | Technique depth and alternative period systems/configurations are incomplete; period output is not consistently event-specific | Add all documented sub-period depths and additional dasha systems as independent arms; connect lords, houses, karakas, yogas and divisional promise to event hypotheses | Period-boundary agreement, event-family lift, ablation skill |
| `vedic_engine/prediction/gochar.py` and `synthesis/transit_analyzer.py` | Gochar, vedha, tara, moorthy, special transits and dasha context | Transit evidence is condensed early into favourable/unfavourable scores | Store every planet-reference-point-rule result; test lagna/Moon/lord/dasha-lord references, kaksha and fast triggers independently | Timing error, precision/recall change, stage-ablation results |
| `vedic_engine/prediction/ashtakavarga.py` | BAV/SAV and transit bindu calculations | Aggregate bands can obscure planet, sign and kaksha-level signal | Preserve per-planet BAV, SAV, prastara and kaksha features; test each as independent and interacting predictors | Incremental Brier skill and timing lift over transit-only models |
| `vedic_engine/prediction/yoga.py` | Detects natal yogas | Detection alone does not establish activation, cancellation, strength or event delivery | Formalise formation, cancellation, modification, strength, relevant event families, dasha activation and transit triggering | Yoga detection fixtures and activated-vs-unactivated event skill |
| `kp_system.py`, `prashna.py`, `muhurta_yogas.py` | Existing alternative technique entry points | These techniques are not yet first-class comparable prediction arms | Give each the same lossless contracts, parameters, event mappings, outcome scoring and replay support | Standalone and incremental out-of-sample skill |
| `vedic_engine/synthesis/engine.py` | Runs Panchanga, Gochar, Dasha, Yoga and Ashtakavarga together | It currently sums unlike scores into one generic total and maps it to broad labels such as “Favourable”; this loses event identity and can create meaningless prose | Replace the global sum with an event-specific evidence tensor. Preserve each raw score, learn/compare combination functions per event and horizon, model conflicts explicitly, and emit multiple precise hypotheses | Event-level calibration, discrimination, exact timing, coverage and ablations versus the legacy sum |
| `forecasting/` | Typed contracts, ledger, baselines, uncertainty and retrospective evaluation | Closed taxonomy, limited time units, abstention erasure and score normalization constrain research | Apply the lossless/open-registry refactors in this strategy; introduce survival/competing-risk evaluation and prospective frozen releases | Baseline-relative skill, calibration, timing accuracy, complete denominators |
| `research_workbench/` | Offline path for turning literature/repos into rule packs | Evidence/license/approval checks currently reject some hypotheses before experimentation | Capture everything first, assess second, experiment third, promote optionally | Captured-hypothesis coverage, reproducibility, successful rule conversion and measured lift |
| `vedic_engine/verbalization/` | Structured `PredictionBrief` generation | It can only be as precise as the upstream event contract and currently operates on narrowed claim fields | Create research narration from the full evidence record; generate event, direction, window, manifestations, conditions, conflicts and resolution criteria without inventing specificity | Semantic faithfulness, event/window preservation, contradiction coverage, expert usefulness ratings |
| API/orchestrator/UI | Existing execution and report surfaces | Product-policy projection is currently in the forecast service path | Add a separate authenticated research service and experiment workbench; prove product presentation code cannot alter research runs | Plane-isolation tests and end-to-end raw-record round trips |

### 13.1 The synthesis change is the highest-leverage correction

The current `VedicPredictor._synthesize()` combines Panchanga verdict points, Muhurta score, Gochar score, and Dasha score by addition, then labels the total “Favourable”, “Mixed”, or similar. Those inputs do not necessarily share a scale, event target, horizon, or empirical meaning. A high value therefore cannot answer what will happen.

Replace it with an event-specific structure:

```text
Event hypothesis
  x natal-promise evidence
  x dasha/period evidence
  x slow-transit evidence
  x fast-trigger evidence
  x technique/school/configuration
  x exact time interval
```

For each event hypothesis, retain supporting, opposing and neutral evidence separately. Compare rule-based combination, Bayesian/hierarchical combination, calibrated statistical models, and learned ensembles in retrospective experiments. No learned weight is accepted from in-sample fit alone, and no method replaces the raw traditional outputs.

### 13.2 The Knowledge Graph becomes an executable research memory

Each textual rule should be represented as both the original passage and a machine-testable rule object. Required graph relations include `supports`, `contradicts`, `exception_to`, `requires`, `activates`, `cancels`, `modifies`, `times`, `targets_event`, `belongs_to_school`, and `derived_from`. This lets the engine ask not only “what passage is similar?” but “which rules exactly apply to this chart, at this time, for this event, under this school configuration?”

The graph should also link every rule to experiment runs and outcome metrics. It then learns a two-dimensional status:

- textual fidelity: whether implementation matches its source;
- empirical performance: how the rule performs prospectively and in which cohorts.

Neither dimension deletes the other. This is the practical feedback loop through which the Knowledge Engine can improve prediction accuracy rather than only supplying citations.

## 14. Person Timeline: prediction-to-life-event environment

Add a first-class Person Timeline that overlays observed milestones, sealed predictions, Dasha periods, transit/fructification windows and resolved outcomes. Selecting a milestone must reveal its precise prediction, date/month/year interval and peak, Mahadasha -> Antardasha -> Pratyantardasha or other timing-system path, natal promise, activating and opposing evidence, calculations, Knowledge Graph rules, classical passages, configuration and replay identity.

This creates the cohesive environment required for both human understanding and empirical learning. It also supplies the outcome loop needed to evaluate which techniques actually predict events. Prospective predictions, observed events and retrospective explanations must have immutable distinct identities; all are retained, but retrospective fit must never be counted as advance prediction accuracy.

The implementation and interaction contract are specified in [PERSON_TIMELINE_DESIGN.md](./PERSON_TIMELINE_DESIGN.md).

## 15. Required code changes

### Add

- `cvce/research_engine/contracts.py`
- `cvce/research_engine/technique_registry.py`
- `cvce/research_engine/run_store.py`
- `cvce/research_engine/experiment_matrix.py`
- `cvce/research_engine/constraint_trace.py`
- `cvce/research_engine/normalization.py`
- `cvce/research_engine/research_narration.py`
- `cvce/research_engine/survival.py`
- `cvce/research_engine/cross_engine/`
- open, versioned event and timing registries
- immutable research-run and raw-score migrations
- at least 30 boundary-heavy golden fixtures

### Refactor

- Make `cvce/forecasting/taxonomy.py` product-only; research contracts accept new and unmapped events.
- Make adapters normalize successful items and quarantine malformed items individually.
- Change abstention in `forecasting/uncertainty.py` into an annotation while retaining direction, probability, score, and evidence.
- Preserve native scores in `forecasting/retrospective.py`; never coerce all measures to `[0,1]`.
- Evaluate abstained and small-subgroup records with explicit status and uncertainty.
- Make Research Workbench capture precede evidence and license assessment.
- Make Knowledge Engine research traversal exhaustive.
- Add raw research services that do not pass through prediction policy or positive projection.
- Let the research verbalizer consume complete sealed records; keep any product renderer separate.

## 16. Migration order

1. Freeze the current 145-pass/1-skip checkpoint as a reproducible legacy/product baseline.
2. Add lossless contracts, raw artifact storage, migrations, and replay hashes.
3. Write raw technique records before any normalizer, aggregator, abstention logic, or narrator.
4. Introduce open event/timing registries and the configuration experiment matrix.
5. Replace whole-run adapter failure with per-item quarantine.
6. Preserve native scores, exact timings, all groups, and all abstention metadata.
7. Make Knowledge Engine traversal and research narration exhaustive.
8. Split Research Workbench capture, assessment, experiment, and promotion stages.
9. Implement progressive-stage factorial experiments and ablations.
10. Add cross-engine adapters and boundary-focused golden fixtures.
11. Run retrospective studies with clean point-in-time data.
12. Freeze releases and begin prospective prediction/outcome collection.

No legacy product filter should be deleted merely to achieve separation. Instead, remove it from the research dependency graph and prove by tests that it cannot affect raw generation or storage.

## 17. Research acceptance gates

These gates validate completeness; they do not restrict content.

- **R0 Reproducibility:** same inputs/configuration/version produce identical records.
- **R1 Losslessness:** raw payload, native score, timing, and prose survive round-trip storage.
- **R2 Exhaustiveness:** every registered technique/configuration arm executes or records an explicit technical failure.
- **R3 Quarantine:** one bad item cannot erase valid sibling results.
- **R4 Traceability:** every normalized claim and sentence links to raw evidence and code/source versions.
- **R5 Comparative validity:** baselines, negative controls, ablations, leakage checks, and confidence intervals are reported.
- **R6 Outcome integrity:** point-in-time predictions and append-only resolutions cannot be rewritten after observation.
- **R7 Plane isolation:** product policy cannot change research execution, storage, denominators, or evaluation.

## 18. Accuracy baseline and completion criteria

**Current demonstrated prediction accuracy remains N/A.** The application has calculation and rule-test coverage, but no sufficiently large, clean, resolved, point-in-time prospective cohort from which an honest prediction-accuracy number can be calculated. Internal rule scores are not empirical accuracy.

This programme is complete only when:

- all registered techniques and configurations produce replayable lossless records;
- no event or timing class is structurally excluded from private research;
- raw outputs survive every transformation;
- progressive constraints are measured through ablation rather than assumed;
- cross-engine and boundary correctness are quantified;
- narrative claims are precise, traceable, and faithful to upstream prediction resolution;
- retrospective results beat relevant baselines out of sample;
- frozen prospective releases produce resolved calibration and skill results;
- failures and contradictions remain as accessible as successes.

The technological edge will come from the combination of exhaustive traditional-technique execution, lossless evidence engineering, configuration search, survival/timing models, rigorous negative controls, prospective outcome learning, and traceable human-language rendering—not from suppressing difficult predictions or making unsupported prose sound certain.
