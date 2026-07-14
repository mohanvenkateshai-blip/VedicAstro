# VedicAstro Prediction Engine Reliability Strategy

> **Research-scope correction — 2026-07-14:** For unrestricted technique discovery and prediction-accuracy research, this document is superseded by [UNFILTERED_RESEARCH_STRATEGY.md](./UNFILTERED_RESEARCH_STRATEGY.md). Safety, abstention, ontology, and presentation gates described below apply only to a future product-facing derived view. They must never filter, suppress, widen, erase, or prevent the storage and scoring of raw research techniques, configurations, timings, scores, narratives, or results.

**Protocol:** MAFIP multi-agent discovery and architecture phase  
**Date:** 2026-07-14  
**Status:** Proposed architecture — implementation requires user approval  
**Scope:** Prediction reliability, evidence, calibration, birth-time uncertainty, outcome learning, verbalisation, safety, privacy, API/UI, testing, observability, and rollout

## 1. Executive decision

VedicAstro should not be rebuilt from scratch. Its deterministic calculations, timing systems, Knowledge Engine, graph provenance, and classical rule coverage are valuable foundations. The correct strategy is to add a canonical forecasting and verbalisation layer beside the legacy engine, run it in shadow mode, and promote event families only after they demonstrate prospective skill.

The programme has two coupled goals:

1. Improve whether a forecast is correct through resolvable event definitions, outcome data, baselines, calibration, uncertainty, and prospective testing.
2. Improve whether a forecast is useful through a claim-bounded Prediction Verbalisation Engine that says what may happen, when, what evidence supports or opposes it, what the user may observe, what action is reasonable, and when the engine must abstain.

Better prose must never be used to manufacture precision that the upstream forecast does not contain.

## 2. Baseline scorecard

These scores measure different things and must never be combined or presented as an accuracy percentage.

| Baseline | Current | Meaning |
|---|---:|---|
| Demonstrated prediction accuracy | N/A | No resolved point-in-time prospective forecast cohort exists. |
| Verified Forecast Skill | N/A | Brier skill, log loss and calibration cannot yet be calculated. |
| Prediction Research Readiness Index | 23/100 | Overall calculation, textual, evaluation, uncertainty, and learning maturity. |
| Evaluation Readiness | 18/100 | Outcome-ledger, point-in-time, baseline, calibration, and prospective-study maturity. |
| Prediction Verbalisation Quality | 29/100 | Specificity, timing, traceability, uncertainty, actionability, readability, and grounding. |
| Safety and Governance Readiness | 21/100 | Privacy, access control, claim safety, auditability, user agency, and GenAI governance. |
| Current CVCE verification | 44 pass / 1 skip / 2 fail | Both failures arise from an `IndentationError` in `transit_analyzer.py:553`. |

### Prediction Research Readiness rubric

| Dimension | Weight | Current level | Weighted result |
|---|---:|---:|---:|
| Computational correctness | 20 | 3/5 | 12 |
| Textual/rule fidelity | 15 | 3/5 | 9 |
| Empirical predictive validity | 20 | 0/5 | 0 |
| Calibration | 15 | 0/5 | 0 |
| Prospective testing | 10 | 0/5 | 0 |
| Uncertainty handling | 10 | 1/5 | 2 |
| Outcome learning | 10 | 0/5 | 0 |
| **Total** | **100** |  | **23** |

### Future reassessment

- Recalculate readiness at every immutable model release.
- Report predictive skill separately for each event family, horizon, cohort, and birth-provenance grade.
- Never average marriage, employment, travel, education, health, and other outcomes into one global accuracy percentage.
- Report base rate, coverage, abstention, Brier score, Brier skill, log loss, calibration, sharpness, and confidence intervals.
- `N/A` must remain `N/A` until sufficient resolved point-in-time forecasts exist; it must not be converted into 0% or an internal rule score.

## 3. Current structural gaps

### 3.1 Multiple prediction truths

Scoring and prose are duplicated across:

- `cvce/vedic_engine/synthesis/engine.py`
- `cvce/vedic_engine/synthesis/dasha_analyzer.py`
- `cvce/vedic_engine/synthesis/transit_analyzer.py`
- `cvce/app/dasha_transit_fusion.py`
- `cvce/app/fructification.py`
- `cvce/app/report_facts.py`
- endpoint-local code in `cvce/app/server.py`

The same chart can therefore receive different score and verdict semantics depending on the endpoint.

### 3.2 Scores are not probabilities

Current sums and thresholds are useful traditional-strength indices, but they are not calibrated against observed outcomes. Required terminology:

- `source_confidence`: quality and agreement of textual evidence.
- `traditional_strength_index`: internal rule/evidence ranking.
- `forecast_probability`: an empirically calibrated probability; nullable until validated.

### 3.3 Mode confusion

The product currently mixes four different questions:

- **Forecast:** What observable event may happen to this native in a bounded future window?
- **Electional/muhurta:** Is a selected time suitable for one named activity?
- **Natal interpretation:** What persistent disposition or potential is traditionally indicated?
- **Explanation:** Why did the engine reach a result?

“Good for marriage, ceremonies, travel, contracts, completions and abundance rituals” is mostly generic electional suitability. It is not a personal forecast and bundles unrelated actions into an unusable statement.

### 3.4 No objective outcome loop

There is no production append-only ledger containing issued forecasts, point-in-time inputs, objective resolutions, evidence, adjudication, and immutable release versions.

### 3.5 Birth-time leakage

Known events used to rectify a birth time cannot also validate predictions made from that rectified time. Rectification must produce a distribution over plausible times and reserve strictly later unseen events for evaluation.

### 3.6 Current narration is unconstrained

`KnowledgeEngine.get_llm_narration()` sends broad fact blocks to Gemini, truncates JSON, and requests free-form paragraphs. It has no claim schema, sentence-level provenance, entailment validation, or protection against adding unsupported dates, events, probabilities, or advice.

## 4. Target architecture

```text
validated chart facts + calculation manifest
  -> normalized RuleEvidence
  -> mode-specific EventCandidate generation
  -> separate M0/M1/M2 predictors and rule packs
  -> evidence fusion and conflict retention
  -> calibrated probability when available
  -> birth-time/model uncertainty
  -> claim-risk policy and abstention
  -> ForecastClaim
  -> immutable ledger commit
  -> ContentPlan
  -> deterministic renderer
  -> optional constrained LLM stylist
  -> claim/number/date/polarity/safety validator
  -> v2 API and PredictionBrief UI
  -> later blinded outcome resolution
  -> evaluation and approved offline recalibration
```

### Canonical forecasting package

Add `cvce/forecasting/`:

- `contracts.py`
- `taxonomy.py`
- `evidence.py`
- `candidates.py`
- `features.py`
- `predictors.py`
- `baselines.py`
- `ensemble.py`
- `calibration.py`
- `abstention.py`
- `dataset.py`
- `evaluation.py`
- `releases.py`
- `policy.py`

All existing engines become structured evidence/feature producers. They must stop creating independent user-facing prediction truth.

## 5. Forecast contract and event ontology

### Initial low-risk, resolvable event families

- `employment.offer_received`
- `employment.start`
- `employment.involuntary_end`
- `contract.signed`
- `travel.departure_international`
- `residence.move_completed`
- `education.enrolment`
- `education.credential_completed`
- `relationship.marriage_registered` — later, sensitive and opt-in

Death, suicide, serious disease, pregnancy outcomes, crime, arrest, abuse, infidelity, investment returns, and third-party tragedy are prohibited as personalised forecasts.

Every ontology entry defines an observable predicate, target entity, inclusion/exclusion criteria, evidence hierarchy, resolution policy, horizon, permitted granularity, censoring policy, and sensitivity tier.

### `ForecastClaim`

Required fields include:

- Identity: claim/forecast ID, release ID, contract version, locale and mode.
- Target: event family/code, domain, subject and observable outcome.
- Timing: start, end, resolution date, timezone and granularity.
- Judgment: polarity, internal score, nullable probability, probability status and base rate.
- Evidence: supporting and opposing signal IDs, rule IDs, citations, calculation hash and conflict counts.
- Stability: birth-time sensitivity, cross-system agreement and data completeness.
- Conditions: prerequisites, alternate manifestations and disconfirmers.
- User value: what to expect, safe next step, avoidance advice and decision scope.
- Epistemics: limitations, certainty tier, abstention code, high-stakes flag and review requirement.

One claim must contain one event predicate and one horizon. “Career good” and multi-activity bundles fail schema validation.

## 6. Prediction Verbalisation Engine

### Purpose

The verbaliser translates a validated `ForecastClaim` into meaningful human language. It does not choose the event, calculate the timing, alter the polarity, invent a probability, or add advice that is absent from the approved content plan.

### Package

Add `cvce/vedic_engine/verbalization/`:

- `models.py`
- `signal_normalizer.py`
- `candidate_builder.py`
- `eligibility.py`
- `content_planner.py`
- `deterministic_renderer.py`
- `llm_stylist.py`
- `claim_validator.py`
- `safety_policy.py`
- `locales/en-IN.json`
- `locales/hi-IN.json`
- `locales/kn-IN.json`

### Content plan

The deterministic planner creates ordered slots:

1. Headline.
2. Exact time window.
3. Observable event.
4. Direction or polarity.
5. Probability and base rate, if calibrated.
6. Supporting evidence.
7. Opposing evidence.
8. What the user may observe.
9. Safe, reversible next step.
10. Uncertainty or abstention explanation.

Every rendered sentence maps `sentence_id -> claim_id(s) -> evidence_id(s)`.

### Deterministic first, LLM second

- Deterministic rendering is the default and permanent fallback.
- The optional LLM is a surface stylist operating only on a de-identified `ContentPlan`.
- Structured JSON output, temperature near zero and fixed claim IDs are mandatory.
- The validator rejects new dates, numbers, planets, events, people, actions, certainty, or recommendations absent from the plan.
- Any failure discards LLM prose and returns the deterministic rendering.
- Semantic entropy may flag unstable wording but must not become forecast confidence.

### Example transformations

Bad:

> Favourable — good for marriage, ceremonies, travel, contracts, completions and abundance rituals.

Honest output with only generic evidence:

> The day-level factors are generally supportive, but they do not predict that a marriage, journey, or contract will occur for you. Marriage suitability requires a marriage-specific election, while a contract or journey should be assessed as a separate activity. The engine does not have enough event-specific evidence to make a personal forecast here.

Uncalibrated event candidate:

> Between 1 September and 30 November 2027, the engine finds an elevated but uncalibrated traditional signal for formalising an existing partnership. Supporting daśā and transit indicators activate the relationship rules, while one Saturn factor may delay agreement. If you are already in a committed relationship, you may see engagement, registration, or shared-obligation discussions. If you are not, the available evidence is insufficient to predict marriage, so the engine abstains.

Calibrated future form:

> A formal job offer is estimated at 62% between 15 August and 31 October 2028, compared with a 38% rate for comparable cases. The strongest support is the 10th/11th-house daśā-transit concurrence; a weak Mercury period raises the risk of negotiation delay. Watch for a final-stage interview or written terms. Continue applications until an offer is signed.

The calibrated form is prohibited until prospective evidence passes the release gates.

### Verbalisation release gate

- 100% preservation of event, dates, polarity, probability and uncertainty.
- Zero unsupported factual or causal claims.
- Zero unrelated activity bundles.
- 100% sentence-to-claim traceability.
- Deterministic fallback always available.
- Practitioner factuality >=4.2/5.
- Layperson comprehension >=4.2/5.
- At least 90% of tested users can identify what, when, likelihood status, uncertainty and next step.
- Zero critical failures across a frozen 200-case multilingual/adversarial suite.

## 7. Outcome ledger and evaluation system

### Persistence

Use authenticated PostgreSQL for identifiable forecasts and outcomes. Add append-only tables:

- `forecast_releases`
- `forecast_runs`
- `forecast_claims`
- `forecast_evidence`
- `outcome_observations`
- `resolution_events`
- `evaluation_runs`
- `privacy_consents`
- `policy_decisions`
- `audit_events`
- `data_subject_requests`

Updates and deletes are denied for research records; corrections append a superseding row. Subjective “felt accurate” feedback is never an outcome label.

### Point-in-time dataset

- Store `effective_at`, `known_at`, `ingested_at`, `data_cutoff_at`, and `issued_at` separately.
- Split by person first, then by time: train, later calibration, latest untouched test.
- Delayed or unclear outcomes are censored/indeterminate, not negative.
- Freeze and hash the dataset manifest for every evaluation.
- Exclude rectification events from validation.

### Scientific comparisons

- M0: cohort/horizon base rate.
- M1: permitted non-astrological history/context available at issue time.
- M2a-n: separately evaluated Jyotiṣa rule packs.
- M3: M1 + M2 combined.

Primary question: does M3 add prospective skill beyond M1?

Negative controls include shuffled charts, zodiac rotations, shifted daśā/event dates, season-preserving event shuffles, and random rule weights. If controls match or beat the Jyotiṣa model, promotion stops.

### Metrics

- Brier score and Brier skill versus M0/M1.
- Log loss.
- Calibration intercept and slope.
- Reliability curves with person-clustered bootstrap intervals.
- Sharpness/resolution.
- Coverage and abstention rate.
- Risk-coverage curves.
- Time-dependent Brier/interval metrics for timing.
- Subgroup stability and adjudication disagreement.

### Calibration and sample size

- Begin with cross-fitted logistic/Platt or beta calibration.
- Use isotonic calibration only when the calibration set is sufficiently large.
- Fit calibrators on a calibration split only and version them independently.
- Determine sample size through preregistered power simulation for each event family.
- Fewer than 50 positive and 50 negative resolved outcomes remains exploratory.
- Target roughly 100 of each in untouched testing for an initial stable calibration assessment; rare events require substantially more participants.

## 8. Birth-time uncertainty and rectification

- Accept a birth-time interval and provenance grade, not only one exact time.
- Sample charts across the interval and propagate them through the full prediction pipeline.
- Return distributions and stability, not a single optimized minute.
- Record historical events used for rectification.
- Never reuse those events for accuracy evaluation.
- Abstain when the event, polarity, or reasonable action changes across plausible times.
- Keep rectification behind a separate API/UI and research consent gate.

## 9. Safety, privacy and service-security blockers

These are P0 before outcome collection or external narration:

1. Saved birth details are currently plaintext in `guest_charts`, which has no RLS and depends on application filtering, while the UI claims encryption at rest.
2. The optional Gemini narration receives the full birth object, including name, exact time and coordinates, without explicit external-processing consent.
3. Severe claims such as death, suicide, assassination, arrest, infidelity and serious health outcomes exist in product-facing rule data.
4. Portal-to-CVCE prediction traffic lacks an authenticated service boundary; CORS is not authentication.

Required actions:

- Consolidate or encrypt saved-chart persistence with versioned keys and fail-closed production behavior.
- Remove inaccurate encryption claims until verified.
- Use separate consents for calculation, storage, outcome research and external AI.
- Send only de-identified claim plans to external models and enforce outbound PII checks.
- Add a central risk/claim-policy compiler to every forecast endpoint.
- Block personalised high-stakes/T3 claims entirely.
- Add signed short-lived portal-to-CVCE service authentication, strict validation and shared rate limiting.
- Implement export, deletion, consent withdrawal, retention, audit and incident workflows.

## 10. Dependency-ordered implementation plan

### WP0 — Restore and freeze the baseline (2-4 days)

- Fix the `transit_analyzer.py:553` syntax failure.
- Restore 47/47 non-skipped tests or document justified skips.
- Install/pin Ruff and define one canonical verification command.
- Capture legacy API and UI fixtures.
- Freeze baseline releases and scorecards.

**Gate G0:** green tests/lint; no v2 feature work begins on a red baseline.

### WP1 — Safety and privacy foundation (2-4 weeks)

- Block prohibited claim classes.
- Disable or de-identify external narration.
- Fix saved-chart encryption/truthful UI.
- Add consent, retention, export/deletion and service authentication.
- Add privacy/security tests.

**Gate G1:** zero prohibited claims/PII leakage; tenant isolation and deletion flows pass.

### WP2 — Taxonomy, modes and contracts (1-2 weeks)

- Approve event ontology v1.
- Define `RuleEvidence`, `EventCandidate`, `ForecastClaim`, `Abstention`, `ContentPlan`, `ForecastResolution` and `ModelRelease`.
- Rename confidence and score semantics.
- Establish additive v2 schema.

**HITL Gate G2:** product owner, Jyotiṣa expert, evaluation lead, and safety reviewer approve examples and boundaries.

### WP3 — Canonical evidence pipeline (3-5 weeks)

- Normalize dasha, transit, yoga, Ashtakavarga, fructification and rule-graph outputs.
- Separate named rule packs.
- Preserve opposing evidence and conflicts.
- Route v2 through one forecasting owner while legacy remains unchanged.

**Gate G3:** no duplicated v2 scoring/prose path; deterministic replay passes.

### WP4 — Ledger, releases and outcome workflow (3-5 weeks)

- Add append-only schema, consent, release manifests and hashes.
- Implement point-in-time snapshots and resolution workflow.
- Add RLS, encryption, supersession and replay tests.

**Gate G4:** privacy/research governance approval before collecting outcomes.

### WP5 — Baselines, uncertainty and abstention (3-5 weeks)

- Implement M0 and M1 baselines.
- Keep M2 rule packs separately measurable.
- Propagate birth-time intervals.
- Add OOD, conflict, stability and calibration abstention.
- Integrate rectification without leakage.

**Gate G5:** unstable or uncalibrated claims cannot display precise probability.

### WP6 — Prediction Verbalisation Engine (3-5 weeks, parallel after WP2)

- Implement claim eligibility and content planning.
- Build deterministic renderer and PredictionBrief schema/UI.
- Add constrained optional stylist and validator.
- Add en-IN, then expert-reviewed hi-IN and kn-IN.
- Execute frozen human and automated evaluation.

**Gate G6:** all verbalisation hard gates pass.

### WP7 — v2 API/UI and shadow mode (2-4 weeks)

- Add `/v2/forecasts`, release and research-admin endpoints.
- Preserve existing endpoints unchanged.
- Show mode, event, window, probability status, base rate, stability, opposing evidence, abstention and release version.
- Run legacy and v2 side by side.

**Gate G7:** accessibility, comprehension, privacy, performance and shadow-diff review.

### WP8 — Retrospective research harness (4-7 weeks)

- Build point-in-time dataset tooling.
- Run M0-M3, negative controls and leakage tests.
- Fit no user-visible probabilities from contaminated data.
- Preregister prospective protocol.

**Gate G8:** permits a silent prospective study only.

### WP9 — Silent prospective trial (engineering 2-3 weeks; evidence 3-12+ months)

- Commit forecasts before outcome windows.
- Do not show forecasts to participants initially.
- Blind dual adjudication and preserve misses/abstentions.
- Evaluate event families individually.

**Gate G9:** positive prospective skill with confidence bound above zero versus M0/M1; calibration, negative-control, subgroup and safety gates pass.

### WP10 — Controlled release and outcome learning

- Promote only passing event families.
- Canary at 1%, 10%, 50%, 100%.
- Monitor drift, calibration and complaints.
- Train/reweight only offline from clean resolved outcomes.
- Use champion/challenger shadow releases and human approval.

## 11. File/module impact map

### Modify

- `cvce/app/config.py`
- `cvce/app/server.py`
- `cvce/app/ephem.py`
- `cvce/app/report_facts.py`
- `cvce/app/fructification.py`
- `cvce/app/dasha_series.py`
- `cvce/app/dasha_transit_fusion.py`
- `cvce/app/rectification.py`
- `cvce/vedic_engine/synthesis/engine.py`
- `cvce/vedic_engine/synthesis/dasha_analyzer.py`
- `cvce/vedic_engine/synthesis/transit_analyzer.py`
- `cvce/vedic_engine/prediction/*` structured-output seams
- `cvce/rules_engine/engine.py`
- `cvce/graph_rag/rules_provider.py`
- `cvce/graph_rag/enhancer.py`
- `cvce/knowledge_engine/engine.py`
- `cvce/knowledge_engine/integration.py`
- `portal/src/lib/auth/schema.sql`
- `portal/src/lib/types.ts`
- `portal/src/lib/cvce.ts`
- `portal/src/lib/features.ts`
- `portal/src/components/report/HoroscopeReport.tsx`
- birth, settings, profile, privacy and admin-health surfaces

### Add

- `cvce/forecasting/*`
- `cvce/vedic_engine/verbalization/*`
- `docs/forecast_event_ontology.yaml`
- `docs/forecast_contract.schema.json`
- `docs/outcome_observation.schema.json`
- versioned forecast/resolution API routes
- ledger repository and privacy/consent APIs
- `portal/src/components/report/PredictionBrief.tsx`
- admin evaluation/calibration/governance dashboards
- point-in-time dataset, evaluation and drift scripts
- forecasting, verbalisation, ledger, security and UI test suites

## 12. Feature flags and rollback

Backend:

- `CVCE_FORECAST_V2_MODE=off|shadow|on`
- `CVCE_FORECAST_LEDGER_WRITE=0|1`
- `CVCE_BIRTH_TIME_ENSEMBLE=0|1`
- `CVCE_ABSTENTION_V2=0|1`
- `CVCE_VERBALIZATION_V2=0|1`
- `CVCE_LLM_STYLIST=0|1`
- `CVCE_EXTERNAL_LLM_NARRATION=0|1`
- `CVCE_MODEL_RELEASE=<immutable-id>`

Portal:

- `PORTAL_FORECAST_V2=0|1`
- `PORTAL_OUTCOME_RESEARCH=0|1`
- `PORTAL_OUTCOME_RESOLUTION=0|1`
- family-specific calibrated-probability flags

All database migrations are additive. Legacy APIs/UI remain available. A flag restores legacy rendering without deleting ledger history. A vendor failure falls back to deterministic verbalisation. Forecasts and consent/audit records are never rewritten during rollback.

## 13. MAFIP implementation waves after approval

Use at least nine bounded roles across concurrency-limited waves:

1. Baseline repair and golden-fixture specialist.
2. Contract/taxonomy and mode-separation architect.
3. RuleEvidence and rule-pack normalisation specialist.
4. Privacy, security and claim-policy specialist.
5. Ledger and outcome-data specialist.
6. Forecasting, baselines and calibration scientist.
7. Rectification, uncertainty and abstention specialist.
8. Prediction Verbalisation Engine specialist.
9. API/UI and shadow-rollout specialist.
10. Independent QA, performance, security and alignment monitor.

`PROGRESS.md` remains the living source for phase, gate, decisions, metrics, blockers and verification evidence. Agents own non-overlapping modules. Contract schemas freeze at the architecture gate before dependent implementation begins.

## 14. Programme milestones

| Milestone | Expected readiness | Permission earned |
|---|---:|---|
| Current | PRRI 23; verbalisation 29 | Interpretation/research only |
| Green baseline + contracts + safety | PRRI approximately 45-55 | Safe v2 shadow development |
| Ledger + uncertainty + evaluation + verbaliser | PRRI approximately 65-75; verbalisation >=75 | Silent prospective trial |
| Positive prospective family-level evidence | PRRI >=80 | Limited user beta for passing families |
| Independent replication + safety >=85 | PRRI >=90 | Narrow evidence-backed product claims |

These are maturity targets, not promised accuracy. Failure to demonstrate incremental skill is a valid research result and requires continued abstention.

## 15. Definition of done

- Existing and new CI gates are green.
- Every user-visible prediction originates from a versioned `ForecastClaim`.
- Forecast, electional, natal and explanatory modes cannot cross-contaminate.
- Source confidence, traditional strength and forecast probability are distinct.
- Ledger replay reproduces the issued claim and wording.
- Birth-time instability triggers uncertainty or abstention.
- The verbaliser adds no unsupported claims and passes comprehension/grounding gates.
- Zero prohibited high-stakes claims and zero raw PII sent to external models.
- v2 passes shadow, privacy, security, performance, accessibility and rollback tests.
- At least one event family passes powered prospective baseline and calibration gates before empirical probabilities become user-visible.
- Architecture and rollout receive explicit user approval.
