# Retrospective Forecast Evaluation Protocol

Status: offline research protocol; it does not authorize product probability release.

## Purpose

Measure whether a frozen M2 Jyotisha rule pack adds point-in-time predictive skill over M0 event-family base rates and M1 temporal/cohort base rates. Event families are evaluated separately. A null or negative result is valid and retains abstention.

## Preregistration template

Complete, timestamp and freeze this section before reading evaluation outcomes:

- Preregistration ID and immutable document hash:
- Research question and event family:
- Observable binary outcome and adjudication rubric:
- Forecast release IDs and code revision:
- Enrollment start/end and evaluation cutoff:
- Inclusion/exclusion criteria fixed before labels are inspected:
- Primary M2 score and frozen rule-pack hash:
- M0 definition; M1 cohort and temporal bucket definition:
- Primary metric (Brier skill versus M0/M1):
- Secondary metrics (Brier, log loss, AUC, ECE, reliability and coverage):
- Minimum paired sample, positive-label and negative-label counts:
- Bootstrap resamples, confidence level and seed:
- Negative-control rule and pass criterion:
- Prespecified subgroup dimensions and minimum cell size:
- Missing-label, indeterminate-resolution and abstention handling:
- Multiplicity policy, if more than one primary comparison exists:
- Safety review owner and decision date:

Changing a preregistered field creates a new preregistration ID; it must not overwrite the earlier record.

## Dataset construction

1. Export only consented, de-identified immutable issued-forecast snapshots and resolution events. Do not include names, birth details, raw chart payloads or free-text outcome notes.
2. Preserve every issued forecast in the denominator, including abstentions, missing M2 scores, unresolved outcomes and misses. Never form a dataset from successful predictions alone.
3. Require the calculation/data cutoff to be strictly earlier than forecast issuance. A resolved label is usable only when its recorded availability time is on or before the evaluation cutoff and after its target window.
4. Train each M0/M1 estimate using labels available strictly before that forecast was issued. Do not use a final full-dataset base rate for earlier forecasts.
5. Keep event families separate. Do not pool marriage, travel, contract, employment or other families into an overall accuracy number.
6. Suppress subgroup cells below the preregistered minimum. Subgroup metadata must be coarse, prespecified and non-identifying.

Synthetic data is permitted only for deterministic software tests. Contaminated data is rejected. Any run containing synthetic rows is diagnostic-only and cannot create calibration IDs or user-visible probabilities.

## Analysis and release interpretation

- Report M0, M1 and M2 independently: issued/resolved/scored counts, coverage, abstention rate, Brier score, log loss, ECE, AUC, reliability bins and fixed-seed bootstrap intervals.
- Compare M2 against each baseline only on paired rows. Report incremental Brier skill and its interval.
- Run deterministic label-permutation negative controls. Investigate unexpectedly strong negative-control performance as leakage or pipeline failure.
- Do not claim positive evidence unless preregistered paired-sample and class-count gates pass and the incremental-skill interval has a lower bound above zero.
- Retrospective evidence alone does not meet Gate G9. Product probability release still requires a frozen prospective holdout, negative-control, calibration, subgroup, safety and governance review.

## Reproducibility artifact

Each result JSON must contain the retrospective schema version, evaluation and preregistration IDs, forecast release IDs, code revision, evaluation cutoff, evaluated time, input hash, bootstrap settings, minimum-cell gates, diagnostic-only flag, separate family results and a deterministic result hash. Store the result beside its immutable input manifest; never overwrite a prior run.
