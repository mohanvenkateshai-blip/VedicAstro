"""Point-in-time base-rate baselines for forecast evaluation.

M0 and M1 are deliberately independent of the traditional rule signal.  They
answer "how often did this observable event occur in comparable, already
resolved cases?" and must not be presented as a calibrated product forecast
until the release gate in :mod:`forecasting.evaluation` approves them.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class BaselineKind(StrEnum):
    M0_EVENT_FAMILY = "m0_event_family"
    M1_TEMPORAL_COHORT = "m1_temporal_cohort"


@dataclass(frozen=True, slots=True)
class OutcomeObservation:
    """A binary outcome whose label was available at ``resolved_at``."""

    observation_id: str
    event_family: str
    outcome: bool
    forecast_at: datetime
    target_at: datetime
    resolved_at: datetime
    cohort: str | None = None

    def __post_init__(self) -> None:
        timestamps = (self.forecast_at, self.target_at, self.resolved_at)
        if not self.observation_id or not self.event_family:
            raise ValueError("observation_id and event_family are required")
        if any(value.tzinfo is None for value in timestamps):
            raise ValueError("observation timestamps must be timezone-aware")
        if type(self.outcome) is not bool:
            raise ValueError("outcome must be a boolean resolved label")
        if self.forecast_at >= self.target_at:
            raise ValueError("forecast_at must precede target_at")
        if self.resolved_at < self.target_at:
            raise ValueError("resolved_at cannot precede target_at")

    @property
    def temporal_bucket(self) -> int:
        """Calendar month of the forecast target, in the target's timezone."""

        return self.target_at.month


@dataclass(frozen=True, slots=True)
class BaselineEstimate:
    kind: BaselineKind
    event_family: str
    probability: float | None
    sample_size: int
    positive_count: int
    training_cutoff: datetime
    cohort: str | None = None
    temporal_bucket: int | None = None
    fallback_used: bool = False

    def __post_init__(self) -> None:
        if self.training_cutoff.tzinfo is None:
            raise ValueError("training_cutoff must be timezone-aware")
        if self.sample_size < 0 or not 0 <= self.positive_count <= self.sample_size:
            raise ValueError("invalid baseline counts")
        if self.probability is not None and not 0 <= self.probability <= 1:
            raise ValueError("probability must be between zero and one")
        if self.sample_size == 0 and self.probability is not None:
            raise ValueError("an empty estimate cannot have a probability")

    def assert_precedes_forecast(self, forecast_at: datetime) -> None:
        if forecast_at.tzinfo is None:
            raise ValueError("forecast_at must be timezone-aware")
        if self.training_cutoff >= forecast_at:
            raise LeakageError("training cutoff must strictly precede forecast time")


class LeakageError(ValueError):
    """Raised when future information could enter a baseline."""


def fit_m0_event_family(
    observations: Iterable[OutcomeObservation],
    *,
    event_family: str,
    training_cutoff: datetime,
    forecast_at: datetime,
) -> BaselineEstimate:
    """Fit the M0 empirical event-family base rate from resolved labels only."""

    eligible = _eligible_observations(observations, event_family, training_cutoff)
    estimate = _estimate(
        eligible,
        kind=BaselineKind.M0_EVENT_FAMILY,
        event_family=event_family,
        training_cutoff=training_cutoff,
    )
    estimate.assert_precedes_forecast(forecast_at)
    return estimate


def fit_m1_temporal_cohort(
    observations: Iterable[OutcomeObservation],
    *,
    event_family: str,
    cohort: str,
    target_at: datetime,
    training_cutoff: datetime,
    forecast_at: datetime,
    minimum_cell_size: int = 1,
    fallback_to_m0: bool = True,
) -> BaselineEstimate:
    """Fit M1 for a cohort and target month, optionally falling back to M0.

    This is intentionally a simple, interpretable baseline rather than a
    traditional-signal model.  Sparse cells may fall back to the broader M0
    estimate, but the returned estimate still records that fallback.
    """

    if target_at.tzinfo is None or training_cutoff.tzinfo is None or forecast_at.tzinfo is None:
        raise ValueError("target_at, training_cutoff, and forecast_at must be timezone-aware")
    if forecast_at >= target_at:
        raise ValueError("forecast_at must precede target_at")
    if minimum_cell_size < 1:
        raise ValueError("minimum_cell_size must be positive")
    all_eligible = _eligible_observations(observations, event_family, training_cutoff)
    month = target_at.month
    cell = [
        item for item in all_eligible if item.cohort == cohort and item.temporal_bucket == month
    ]
    if len(cell) >= minimum_cell_size or not fallback_to_m0:
        estimate = _estimate(
            cell,
            kind=BaselineKind.M1_TEMPORAL_COHORT,
            event_family=event_family,
            training_cutoff=training_cutoff,
            cohort=cohort,
            temporal_bucket=month,
        )
        estimate.assert_precedes_forecast(forecast_at)
        return estimate
    broad = _estimate(
        all_eligible,
        kind=BaselineKind.M1_TEMPORAL_COHORT,
        event_family=event_family,
        training_cutoff=training_cutoff,
        cohort=cohort,
        temporal_bucket=month,
    )
    estimate = BaselineEstimate(
        kind=broad.kind,
        event_family=broad.event_family,
        probability=broad.probability,
        sample_size=broad.sample_size,
        positive_count=broad.positive_count,
        training_cutoff=broad.training_cutoff,
        cohort=broad.cohort,
        temporal_bucket=broad.temporal_bucket,
        fallback_used=True,
    )
    estimate.assert_precedes_forecast(forecast_at)
    return estimate


def _eligible_observations(
    observations: Iterable[OutcomeObservation],
    event_family: str,
    training_cutoff: datetime,
) -> list[OutcomeObservation]:
    if not event_family:
        raise ValueError("event_family is required")
    if training_cutoff.tzinfo is None:
        raise ValueError("training_cutoff must be timezone-aware")
    cutoff = training_cutoff.astimezone(UTC)
    return [
        item
        for item in observations
        if item.event_family == event_family and item.resolved_at.astimezone(UTC) <= cutoff
    ]


def _estimate(
    observations: list[OutcomeObservation],
    *,
    kind: BaselineKind,
    event_family: str,
    training_cutoff: datetime,
    cohort: str | None = None,
    temporal_bucket: int | None = None,
) -> BaselineEstimate:
    positives = sum(item.outcome for item in observations)
    count = len(observations)
    return BaselineEstimate(
        kind=kind,
        event_family=event_family,
        probability=positives / count if count else None,
        sample_size=count,
        positive_count=positives,
        training_cutoff=training_cutoff,
        cohort=cohort,
        temporal_bucket=temporal_bucket,
    )
