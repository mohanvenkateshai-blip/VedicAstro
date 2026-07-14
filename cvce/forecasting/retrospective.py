"""Leakage-resistant, point-in-time retrospective forecast evaluation.

This module is deliberately an offline research harness.  It preserves the
issued-forecast denominator (including abstentions and unresolved outcomes),
reports event families separately, and never creates a calibration release or
product-facing probability.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo

from .baselines import OutcomeObservation, fit_m0_event_family, fit_m1_temporal_cohort
from .canonical import canonical_json, stable_hash
from .evaluation import (
    CalibrationReport,
    ConfidenceInterval,
    NegativeControlReport,
    bootstrap_confidence_interval,
    calibration_report,
    negative_control_report,
)
from .ledger import ForecastResolution, IssuedForecast, OutcomeStatus
from .research import NativeScore, ResearchArtifactOrigin, ResearchSignalArtifact

RETROSPECTIVE_SCHEMA_VERSION = "1.0.0"
_SUBJECT_KEY = re.compile(r"^subj_[0-9a-f]{16,64}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")


class RetrospectiveError(ValueError):
    """Invalid retrospective research input."""


class RetrospectiveLeakageError(RetrospectiveError):
    """Future information could enter a point-in-time evaluation."""


class DataOrigin(StrEnum):
    OBSERVED = "observed"
    SYNTHETIC_TEST = "synthetic_test"
    CONTAMINATED = "contaminated"


class EvidenceStatus(StrEnum):
    POSITIVE_BOUND_ABOVE_ZERO = "positive_bound_above_zero"
    BOUND_CROSSES_ZERO = "bound_crosses_zero"
    INSUFFICIENT_SAMPLES = "insufficient_samples"
    BASELINE_UNAVAILABLE = "baseline_unavailable"


@dataclass(frozen=True, slots=True)
class RetrospectiveRow:
    """One de-identified forecast snapshot as it was knowable at issuance."""

    row_id: str
    subject_key: str
    event_family: str
    forecast_at: datetime
    target_at: datetime
    point_in_time_cutoff: datetime
    abstained: bool
    cohort: str | None = None
    m2_score: float | None = None
    outcome: bool | None = None
    resolved_at: datetime | None = None
    label_available_at: datetime | None = None
    subgroup: tuple[tuple[str, str], ...] = ()
    snapshot_hash: str = ""
    resolution_hash: str | None = None
    data_origin: DataOrigin = DataOrigin.OBSERVED
    research_probability: float | None = None
    native_m2_score: NativeScore | None = None
    research_direction: str | None = None
    research_artifact: ResearchSignalArtifact | None = None

    def __post_init__(self) -> None:
        timestamps = (self.forecast_at, self.target_at, self.point_in_time_cutoff)
        if not self.row_id or not self.event_family:
            raise RetrospectiveError("row_id and event_family are required")
        if not _SUBJECT_KEY.fullmatch(self.subject_key):
            raise RetrospectiveError("subject_key must be a de-identified ledger key")
        if any(value.tzinfo is None for value in timestamps):
            raise RetrospectiveError("all row timestamps must be timezone-aware")
        if self.point_in_time_cutoff >= self.forecast_at:
            raise RetrospectiveLeakageError("point-in-time cutoff must precede issuance")
        if self.forecast_at >= self.target_at:
            raise RetrospectiveError("forecast_at must precede target_at")
        if self.m2_score is not None and (
            not math.isfinite(self.m2_score) or not 0 <= self.m2_score <= 1
        ):
            raise RetrospectiveError("m2_score must be finite and between zero and one")
        if self.abstained and self.m2_score is not None:
            raise RetrospectiveError("an abstention cannot have an M2 score")
        if self.research_probability is not None and (
            not math.isfinite(self.research_probability)
            or not 0 <= self.research_probability <= 1
        ):
            raise RetrospectiveError(
                "research_probability must be finite and between zero and one"
            )
        if self.research_artifact is not None:
            artifact = self.research_artifact
            if artifact.row_id != self.row_id or artifact.subject_key != self.subject_key:
                raise RetrospectiveError("research artifact identity does not match its row")
            if not self.snapshot_hash or artifact.forecast_snapshot_hash != self.snapshot_hash:
                raise RetrospectiveError("research artifact is not bound to the forecast snapshot")
            if artifact.issued_at != self.forecast_at:
                raise RetrospectiveError("research artifact is not bound to forecast issuance")
            if artifact.probability != self.research_probability:
                raise RetrospectiveError("research probability differs from its issued artifact")
            if artifact.native_score != self.native_m2_score:
                raise RetrospectiveError("native score differs from its issued artifact")
            if artifact.direction != self.research_direction:
                raise RetrospectiveError("research direction differs from its issued artifact")
        if self.outcome is None:
            if self.resolved_at is not None or self.label_available_at is not None:
                raise RetrospectiveError("an unresolved row cannot contain label timestamps")
        else:
            if type(self.outcome) is not bool:
                raise RetrospectiveError("outcome must be boolean when resolved")
            if self.resolved_at is None or self.label_available_at is None:
                raise RetrospectiveError("a resolved row requires both label timestamps")
            if self.resolved_at.tzinfo is None or self.label_available_at.tzinfo is None:
                raise RetrospectiveError("label timestamps must be timezone-aware")
            if self.resolved_at < self.target_at or self.label_available_at < self.target_at:
                raise RetrospectiveLeakageError("a label cannot be available before its target")
        if self.snapshot_hash and not _HASH.fullmatch(self.snapshot_hash):
            raise RetrospectiveError("snapshot_hash must be sha256 hex")
        if self.resolution_hash and not _HASH.fullmatch(self.resolution_hash):
            raise RetrospectiveError("resolution_hash must be sha256 hex")
        if tuple(sorted(self.subgroup)) != self.subgroup:
            raise RetrospectiveError("subgroup metadata must be sorted for deterministic hashing")
        if len({key for key, _ in self.subgroup}) != len(self.subgroup):
            raise RetrospectiveError("subgroup keys must be unique")


@dataclass(frozen=True, slots=True)
class RetrospectiveDataset:
    rows: tuple[RetrospectiveRow, ...]
    evaluation_cutoff: datetime
    input_hash: str
    diagnostic_only: bool

    @classmethod
    def build(
        cls,
        rows: Iterable[RetrospectiveRow],
        *,
        evaluation_cutoff: datetime,
        _verified_issuance_artifact_hashes: frozenset[str] = frozenset(),
    ) -> RetrospectiveDataset:
        if evaluation_cutoff.tzinfo is None:
            raise RetrospectiveError("evaluation_cutoff must be timezone-aware")
        ordered = tuple(sorted(rows, key=lambda row: row.row_id))
        if not ordered:
            raise RetrospectiveError("at least one retrospective row is required")
        if len({row.row_id for row in ordered}) != len(ordered):
            raise RetrospectiveError("row_id values must be unique")
        if any(row.data_origin is DataOrigin.CONTAMINATED for row in ordered):
            raise RetrospectiveLeakageError("contaminated rows are forbidden")
        for row in ordered:
            if row.forecast_at > evaluation_cutoff:
                raise RetrospectiveLeakageError("future forecast snapshot is not yet available")
            if row.outcome is not None and row.label_available_at > evaluation_cutoff:
                raise RetrospectiveLeakageError(
                    "future label is not available at evaluation cutoff"
                )
        payload = {
            "schema_version": RETROSPECTIVE_SCHEMA_VERSION,
            "evaluation_cutoff": evaluation_cutoff,
            "rows": ordered,
        }
        return cls(
            rows=ordered,
            evaluation_cutoff=evaluation_cutoff,
            input_hash=stable_hash(payload),
            diagnostic_only=any(
                row.data_origin is not DataOrigin.OBSERVED
                or (
                    _has_research_signal(row)
                    and (
                        row.research_artifact is None
                        or row.research_artifact.origin is not ResearchArtifactOrigin.ISSUANCE_LEDGER
                        or row.research_artifact.artifact_hash
                        not in _verified_issuance_artifact_hashes
                    )
                )
                for row in ordered
            ),
        )

    @classmethod
    def build_from_issued_forecasts(
        cls,
        rows: Iterable[RetrospectiveRow],
        issued_forecasts: Iterable[IssuedForecast],
        *,
        evaluation_cutoff: datetime,
    ) -> RetrospectiveDataset:
        """Verify research artifacts against immutable issuance records."""

        ordered_rows = tuple(rows)
        issued_by_claim = {item.claim.claim_id: item for item in issued_forecasts}
        verified: set[str] = set()
        for row in ordered_rows:
            if row.research_artifact is None:
                continue
            issued = issued_by_claim.get(row.row_id)
            if issued is None:
                raise RetrospectiveError("research artifact has no immutable issuance record")
            expected = _research_artifact_from_issued(issued)
            if row.research_artifact != expected:
                raise RetrospectiveError("research artifact differs from immutable issuance record")
            verified.add(expected.artifact_hash)
        return cls.build(
            ordered_rows,
            evaluation_cutoff=evaluation_cutoff,
            _verified_issuance_artifact_hashes=frozenset(verified),
        )


@dataclass(frozen=True, slots=True)
class ModelEvaluation:
    model_id: str
    issued_count: int
    resolved_count: int
    scored_count: int
    abstention_count: int
    missing_score_count: int
    coverage: float
    abstention_rate: float
    calibration: CalibrationReport | None
    brier_interval: ConfidenceInterval | None
    negative_control: NegativeControlReport | None
    scored_abstention_count: int = 0


@dataclass(frozen=True, slots=True)
class SkillComparison:
    candidate_model: str
    baseline_model: str
    paired_count: int
    positive_count: int
    incremental_brier_skill: float | None
    skill_interval: ConfidenceInterval | None
    evidence_status: EvidenceStatus
    claim_supported: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SubgroupResult:
    dimension: str
    value: str
    cell_size: int
    resolved_count: int
    scored_count: int
    m2_brier_score: float | None
    small_sample: bool = False
    m2_brier_interval: ConfidenceInterval | None = None
    interval_is_diagnostic: bool = False


@dataclass(frozen=True, slots=True)
class FamilyEvaluation:
    event_family: str
    issued_count: int
    unresolved_count: int
    models: tuple[ModelEvaluation, ...]
    comparisons: tuple[SkillComparison, ...]
    subgroup_results: tuple[SubgroupResult, ...]
    suppressed_subgroups: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvaluationManifest:
    schema_version: str
    evaluation_id: str
    preregistration_id: str
    forecast_release_ids: tuple[str, ...]
    code_revision: str
    input_hash: str
    evaluated_at: datetime
    evaluation_cutoff: datetime
    bootstrap_seed: int
    bootstrap_resamples: int
    minimum_comparison_samples: int
    minimum_class_count: int
    minimum_subgroup_cell: int
    diagnostic_only: bool
    probability_release_eligible: bool = False
    research_mode: bool = False


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    manifest: EvaluationManifest
    families: tuple[FamilyEvaluation, ...]
    result_hash: str

    def to_json(self) -> str:
        return canonical_json(self)


def row_from_ledger(
    issued: IssuedForecast,
    resolution: ForecastResolution | None,
    *,
    event_family: str,
    cohort: str | None = None,
    m2_score: float | None = None,
    subgroup: Mapping[str, str] | None = None,
) -> RetrospectiveRow:
    """Adapt immutable ledger objects without adding direct identifiers."""

    if resolution is not None:
        if resolution.claim_id != issued.claim.claim_id:
            raise RetrospectiveError("resolution does not belong to issued forecast")
        if resolution.subject_key != issued.subject_key or resolution.tenant_id != issued.tenant_id:
            raise RetrospectiveError("resolution subject does not match issued forecast")
        if resolution.observation.status is OutcomeStatus.OCCURRED:
            outcome: bool | None = True
        elif resolution.observation.status is OutcomeStatus.DID_NOT_OCCUR:
            outcome = False
        else:
            outcome = None
        resolved_at = resolution.observation.observed_at if outcome is not None else None
        label_available_at = resolution.recorded_at if outcome is not None else None
        resolution_hash = stable_hash(resolution)
    else:
        outcome = None
        resolved_at = None
        label_available_at = None
        resolution_hash = None
    target_at = datetime.combine(
        issued.claim.timing.end_on,
        datetime.max.time(),
        tzinfo=ZoneInfo(issued.claim.timing.timezone),
    )
    research_artifact = _research_artifact_from_issued(issued)
    return RetrospectiveRow(
        row_id=issued.claim.claim_id,
        subject_key=issued.subject_key,
        event_family=event_family,
        forecast_at=issued.issued_at,
        target_at=target_at,
        point_in_time_cutoff=issued.point_in_time_cutoff,
        abstained=issued.claim.abstention.abstained,
        cohort=cohort,
        m2_score=m2_score,
        outcome=outcome,
        resolved_at=resolved_at,
        label_available_at=label_available_at,
        subgroup=tuple(sorted((subgroup or {}).items())),
        snapshot_hash=issued.claim_hash,
        resolution_hash=resolution_hash,
        research_probability=research_artifact.probability,
        native_m2_score=research_artifact.native_score,
        research_direction=research_artifact.direction,
        research_artifact=research_artifact,
    )


def _research_artifact_from_issued(issued: IssuedForecast) -> ResearchSignalArtifact:
    if issued.claim_hash != stable_hash(issued.claim):
        raise RetrospectiveError("issued forecast claim hash failed integrity verification")
    if issued.point_in_time_cutoff != issued.claim.provenance.data_cutoff_at:
        raise RetrospectiveError("issued forecast cutoff differs from claim provenance")
    if issued.point_in_time_cutoff > issued.issued_at:
        raise RetrospectiveLeakageError("issued forecast cutoff is after issuance")
    return ResearchSignalArtifact.seal(
        row_id=issued.claim.claim_id,
        subject_key=issued.subject_key,
        forecast_snapshot_hash=issued.claim_hash,
        issued_at=issued.issued_at,
        probability=issued.claim.forecast_probability,
        native_score=NativeScore(
            issued.claim.traditional_strength_index,
            "traditional_strength_index",
        ),
        direction=issued.claim.polarity.value,
        origin=ResearchArtifactOrigin.ISSUANCE_LEDGER,
    )


def evaluate_retrospective(
    dataset: RetrospectiveDataset,
    *,
    evaluation_id: str,
    preregistration_id: str,
    forecast_release_ids: Sequence[str],
    code_revision: str,
    evaluated_at: datetime,
    minimum_comparison_samples: int = 200,
    minimum_class_count: int = 20,
    minimum_subgroup_cell: int = 20,
    bootstrap_resamples: int = 1_000,
    bootstrap_seed: int = 20260714,
    research_mode: bool = False,
) -> EvaluationRun:
    """Evaluate each event family independently; never pool families."""

    if not evaluation_id or not preregistration_id or not code_revision:
        raise RetrospectiveError("evaluation, preregistration, and code revision IDs are required")
    if evaluated_at.tzinfo is None or evaluated_at < dataset.evaluation_cutoff:
        raise RetrospectiveError("evaluated_at must be aware and not precede the cutoff")
    if minimum_comparison_samples < 1 or minimum_class_count < 1:
        raise RetrospectiveError("comparison sample gates must be positive")
    if minimum_subgroup_cell < 2 or bootstrap_resamples < 1:
        raise RetrospectiveError("subgroup and bootstrap settings are invalid")

    observations = [_to_observation(row) for row in dataset.rows if row.outcome is not None]
    families: list[FamilyEvaluation] = []
    for family in sorted({row.event_family for row in dataset.rows}):
        rows = tuple(row for row in dataset.rows if row.event_family == family)
        scored: dict[str, list[tuple[str, float, int]]] = {"M0": [], "M1": [], "M2": []}
        for row in rows:
            if row.outcome is None:
                continue
            outcome = int(row.outcome)
            training_cutoff = row.forecast_at - timedelta(microseconds=1)
            m0 = fit_m0_event_family(
                observations,
                event_family=family,
                training_cutoff=training_cutoff,
                forecast_at=row.forecast_at,
            )
            if m0.probability is not None:
                scored["M0"].append((row.row_id, m0.probability, outcome))
            if row.cohort:
                m1 = fit_m1_temporal_cohort(
                    observations,
                    event_family=family,
                    cohort=row.cohort,
                    target_at=row.target_at,
                    training_cutoff=training_cutoff,
                    forecast_at=row.forecast_at,
                    minimum_cell_size=minimum_subgroup_cell,
                )
                if m1.probability is not None:
                    scored["M1"].append((row.row_id, m1.probability, outcome))
            research_score = row.research_probability if research_mode else None
            if research_score is not None:
                scored["M2"].append((row.row_id, research_score, outcome))
            elif not row.abstained and row.m2_score is not None:
                scored["M2"].append((row.row_id, row.m2_score, outcome))

        resolved_count = sum(row.outcome is not None for row in rows)
        abstention_count = sum(row.abstained for row in rows)
        models = tuple(
            _evaluate_model(
                model_id,
                values,
                issued_count=len(rows),
                resolved_count=resolved_count,
                abstention_count=abstention_count,
                scored_abstention_count=(
                    sum(
                        row.abstained
                        and row.outcome is not None
                        and row.research_probability is not None
                        for row in rows
                    )
                    if research_mode and model_id == "M2"
                    else 0
                ),
                resamples=bootstrap_resamples,
                seed=bootstrap_seed,
            )
            for model_id, values in scored.items()
        )
        comparisons = tuple(
            _compare_skill(
                scored["M2"],
                scored[baseline],
                baseline=baseline,
                minimum_samples=minimum_comparison_samples,
                minimum_class_count=minimum_class_count,
                resamples=bootstrap_resamples,
                seed=bootstrap_seed,
            )
            for baseline in ("M0", "M1")
        )
        subgroup_results, suppressed = _subgroup_results(
            rows,
            minimum_cell=minimum_subgroup_cell,
            expose_small_samples=research_mode,
            use_research_scores=research_mode,
            resamples=bootstrap_resamples,
            seed=bootstrap_seed,
        )
        families.append(
            FamilyEvaluation(
                event_family=family,
                issued_count=len(rows),
                unresolved_count=len(rows) - resolved_count,
                models=models,
                comparisons=comparisons,
                subgroup_results=subgroup_results,
                suppressed_subgroups=suppressed,
            )
        )

    manifest = EvaluationManifest(
        schema_version=RETROSPECTIVE_SCHEMA_VERSION,
        evaluation_id=evaluation_id,
        preregistration_id=preregistration_id,
        forecast_release_ids=tuple(sorted(set(forecast_release_ids))),
        code_revision=code_revision,
        input_hash=dataset.input_hash,
        evaluated_at=evaluated_at,
        evaluation_cutoff=dataset.evaluation_cutoff,
        bootstrap_seed=bootstrap_seed,
        bootstrap_resamples=bootstrap_resamples,
        minimum_comparison_samples=minimum_comparison_samples,
        minimum_class_count=minimum_class_count,
        minimum_subgroup_cell=minimum_subgroup_cell,
        diagnostic_only=dataset.diagnostic_only,
        research_mode=research_mode,
    )
    result_payload = {"manifest": manifest, "families": tuple(families)}
    return EvaluationRun(
        manifest=manifest,
        families=tuple(families),
        result_hash=stable_hash(result_payload),
    )


def evaluate_research_retrospective(
    dataset: RetrospectiveDataset,
    **kwargs: Any,
) -> EvaluationRun:
    """Evaluate every research score, including release-abstained records.

    This is additive to the product-compatible evaluator. Native engine scores
    remain on each row for scale-specific analyses; only an explicitly supplied
    ``research_probability`` enters probability metrics such as Brier score.
    """

    if "research_mode" in kwargs:
        raise TypeError("evaluate_research_retrospective owns research_mode")
    return evaluate_retrospective(dataset, research_mode=True, **kwargs)


def _has_research_signal(row: RetrospectiveRow) -> bool:
    return any(
        value is not None
        for value in (
            row.research_probability,
            row.native_m2_score,
            row.research_direction,
            row.research_artifact,
        )
    )


def _to_observation(row: RetrospectiveRow) -> OutcomeObservation:
    assert row.outcome is not None and row.resolved_at is not None
    return OutcomeObservation(
        observation_id=row.row_id,
        event_family=row.event_family,
        outcome=row.outcome,
        forecast_at=row.forecast_at,
        target_at=row.target_at,
        resolved_at=max(row.resolved_at, row.label_available_at),
        cohort=row.cohort,
    )


def _evaluate_model(
    model_id: str,
    values: Sequence[tuple[str, float, int]],
    *,
    issued_count: int,
    resolved_count: int,
    abstention_count: int,
    scored_abstention_count: int,
    resamples: int,
    seed: int,
) -> ModelEvaluation:
    probabilities = [item[1] for item in values]
    outcomes = [item[2] for item in values]
    report = calibration_report(probabilities, outcomes) if values else None
    interval = None
    control = None
    if values:
        interval = bootstrap_confidence_interval(
            list(zip(probabilities, outcomes, strict=True)),
            lambda pairs: sum((p - y) ** 2 for p, y in pairs) / len(pairs),
            resamples=resamples,
            seed=seed,
        )
        control = negative_control_report(probabilities, outcomes, seed=seed)
    return ModelEvaluation(
        model_id=model_id,
        issued_count=issued_count,
        resolved_count=resolved_count,
        scored_count=len(values),
        abstention_count=abstention_count,
        missing_score_count=resolved_count - len(values),
        coverage=len(values) / resolved_count if resolved_count else 0.0,
        abstention_rate=abstention_count / issued_count if issued_count else 0.0,
        calibration=report,
        brier_interval=interval,
        negative_control=control,
        scored_abstention_count=scored_abstention_count,
    )


def _compare_skill(
    candidate: Sequence[tuple[str, float, int]],
    baseline_values: Sequence[tuple[str, float, int]],
    *,
    baseline: str,
    minimum_samples: int,
    minimum_class_count: int,
    resamples: int,
    seed: int,
) -> SkillComparison:
    candidate_by_id = {identifier: (score, outcome) for identifier, score, outcome in candidate}
    paired = [
        (candidate_by_id[identifier][0], score, outcome)
        for identifier, score, outcome in baseline_values
        if identifier in candidate_by_id
    ]
    positives = sum(item[2] for item in paired)
    negatives = len(paired) - positives
    reasons: list[str] = []
    if len(paired) < minimum_samples:
        reasons.append("minimum paired sample size not met")
    if positives < minimum_class_count:
        reasons.append("minimum positive-label count not met")
    if negatives < minimum_class_count:
        reasons.append("minimum negative-label count not met")
    if not paired:
        return SkillComparison(
            "M2",
            baseline,
            0,
            0,
            None,
            None,
            EvidenceStatus.BASELINE_UNAVAILABLE,
            False,
            tuple(reasons or ["no paired baseline and M2 scores"]),
        )

    def skill(values: Sequence[tuple[float, float, int]]) -> float:
        candidate_brier = sum((m2 - outcome) ** 2 for m2, _, outcome in values) / len(values)
        baseline_brier = sum((base - outcome) ** 2 for _, base, outcome in values) / len(values)
        return 0.0 if baseline_brier == 0 else 1 - candidate_brier / baseline_brier

    estimate = skill(paired)
    interval = bootstrap_confidence_interval(paired, skill, resamples=resamples, seed=seed)
    if reasons:
        status = EvidenceStatus.INSUFFICIENT_SAMPLES
        supported = False
    elif interval.lower > 0:
        status = EvidenceStatus.POSITIVE_BOUND_ABOVE_ZERO
        supported = True
    else:
        status = EvidenceStatus.BOUND_CROSSES_ZERO
        supported = False
        reasons.append("bootstrap interval does not have a positive lower bound")
    return SkillComparison(
        candidate_model="M2",
        baseline_model=baseline,
        paired_count=len(paired),
        positive_count=positives,
        incremental_brier_skill=estimate,
        skill_interval=interval,
        evidence_status=status,
        claim_supported=supported,
        reasons=tuple(reasons),
    )


def _subgroup_results(
    rows: Sequence[RetrospectiveRow],
    *,
    minimum_cell: int,
    expose_small_samples: bool = False,
    use_research_scores: bool = False,
    resamples: int = 1_000,
    seed: int = 20260714,
) -> tuple[tuple[SubgroupResult, ...], tuple[str, ...]]:
    cells: dict[tuple[str, str], list[RetrospectiveRow]] = defaultdict(list)
    for row in rows:
        for item in row.subgroup:
            cells[item].append(row)
    visible: list[SubgroupResult] = []
    suppressed: list[str] = []
    for (dimension, value), cell in sorted(cells.items()):
        key = f"{dimension}={value}"
        resolved_count = sum(row.outcome is not None for row in cell)
        scored = [
            (row.research_probability if use_research_scores else row.m2_score, row.outcome)
            for row in cell
            if row.outcome is not None
            and (row.research_probability if use_research_scores else row.m2_score) is not None
        ]
        scored_count = len(scored)
        small_sample = scored_count < minimum_cell
        if small_sample and not expose_small_samples:
            suppressed.append(key)
            continue
        brier = None
        interval = None
        if scored:
            brier = sum((score - int(outcome)) ** 2 for score, outcome in scored) / len(scored)
            interval = bootstrap_confidence_interval(
                scored,
                lambda values: sum((score - int(outcome)) ** 2 for score, outcome in values)
                / len(values),
                resamples=resamples,
                seed=seed,
            )
        visible.append(
            SubgroupResult(
                dimension,
                value,
                len(cell),
                resolved_count,
                scored_count,
                brier,
                small_sample=small_sample,
                m2_brier_interval=interval,
                interval_is_diagnostic=small_sample,
            )
        )
    return tuple(visible), tuple(suppressed)


def evaluation_dict(run: EvaluationRun) -> dict[str, Any]:
    """Plain JSON-compatible result for offline artifact writers."""

    return json.loads(run.to_json())
