"""Release boundary for validated, product-safe v2 forecast briefs."""

from __future__ import annotations

import logging
from typing import Any, Literal

from prediction_policy import apply_product_claim_policy
from pydantic import BaseModel, ConfigDict

from vedic_engine.verbalization import PredictionBrief, render_prediction_brief

from .contracts import ForecastClaim, TimingWindow

logger = logging.getLogger(__name__)

API_VERSION = "2.0.0"
POLICY_VERSION = "personalised-t3-v1"
VERBALIZER_VERSION = "deterministic-en-IN-v1"


class ForecastReleaseMetadata(BaseModel):
    """Non-sensitive release metadata safe to retain in shadow logs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_version: str = API_VERSION
    contract_version: str
    release_id: str
    engine_version: str
    policy_version: str = POLICY_VERSION
    verbalizer_version: str = VERBALIZER_VERSION
    probability_status: str
    ledger_write_enabled: bool
    ledger_written: bool = False


class ForecastClaimSummary(BaseModel):
    """Safe structured fields needed for an accessible product presentation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_code: str
    timing: TimingWindow
    polarity: str
    probability_status: str
    forecast_probability: float | None
    base_rate: float | None
    base_rate_source: str | None
    birth_time_sensitivity: str
    supporting_evidence_ids: tuple[str, ...]
    opposing_evidence_ids: tuple[str, ...]


class ForecastBriefResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["released"] = "released"
    metadata: ForecastReleaseMetadata
    claim: ForecastClaimSummary
    brief: PredictionBrief


class ForecastShadowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["shadow"] = "shadow"
    accepted: bool = True
    verbalization_computed: bool
    safety_status: Literal["passed", "filtered"]
    blocked_category_count: int
    metadata: ForecastReleaseMetadata


def release_metadata(
    claim: ForecastClaim, *, ledger_write_enabled: bool
) -> ForecastReleaseMetadata:
    return ForecastReleaseMetadata(
        contract_version=claim.contract_version,
        release_id=claim.release_id,
        engine_version=claim.provenance.engine_version,
        probability_status=claim.probability_status.value,
        ledger_write_enabled=ledger_write_enabled,
    )


def process_forecast_claim(
    claim: ForecastClaim,
    *,
    mode: Literal["shadow", "on"],
    verbalization_enabled: bool,
    ledger_write_enabled: bool,
) -> ForecastBriefResponse | ForecastShadowResponse:
    """Apply safety and deterministic verbalisation without adapting legacy prose.

    Ledger writes remain false here even when the rollout flag is enabled: the
    endpoint deliberately accepts no tenant, subject, or consent material, so
    it cannot satisfy the append-only ledger's consent boundary.
    """

    safety = apply_product_claim_policy(claim.model_dump(mode="json"))
    metadata = release_metadata(claim, ledger_write_enabled=ledger_write_enabled)
    brief = render_prediction_brief(claim) if verbalization_enabled else None

    if mode == "shadow":
        response = ForecastShadowResponse(
            verbalization_computed=brief is not None,
            safety_status="filtered" if safety.blocked_count else "passed",
            blocked_category_count=len(safety.blocked_categories),
            metadata=metadata,
        )
        # Deliberately exclude claim identifiers, prose, birth data and evidence
        # identifiers from operational logs.
        logger.info(
            "forecast_v2_shadow event=%s probability_status=%s safety=%s verbalized=%s",
            claim.event_code.value,
            claim.probability_status.value,
            response.safety_status,
            response.verbalization_computed,
        )
        return response

    if brief is None:
        raise ValueError("v2 deterministic verbalization is disabled")
    summary = ForecastClaimSummary(
        event_code=claim.event_code.value,
        timing=claim.timing,
        polarity=claim.polarity.value,
        probability_status=claim.probability_status.value,
        forecast_probability=claim.forecast_probability,
        base_rate=claim.base_rate,
        base_rate_source=claim.base_rate_source,
        birth_time_sensitivity=claim.uncertainty.birth_time_sensitivity.value,
        supporting_evidence_ids=claim.supporting_evidence_ids,
        opposing_evidence_ids=claim.opposing_evidence_ids,
    )
    return ForecastBriefResponse(metadata=metadata, claim=summary, brief=brief)


def validation_error_detail(exc: Exception) -> list[dict[str, Any]]:
    """Return field locations and messages without echoing submitted values."""

    errors = getattr(exc, "errors", None)
    if not callable(errors):
        return [{"loc": ["body"], "msg": "Invalid ForecastClaim", "type": "value_error"}]
    return [
        {
            "loc": ["body", *error.get("loc", ())],
            "msg": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        }
        for error in errors()
    ]
