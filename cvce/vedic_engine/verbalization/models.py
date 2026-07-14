"""Immutable output models for deterministic prediction verbalisation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VerbalizationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GroundedText(VerbalizationModel):
    """A rendered assertion and the ForecastClaim fields that support it."""

    text: str = Field(min_length=1)
    source_paths: tuple[str, ...] = Field(min_length=1)


class EvidenceSummary(VerbalizationModel):
    direction: str = Field(pattern=r"^(supporting|opposing)$")
    evidence_ids: tuple[str, ...] = ()
    statement: GroundedText


class ContentPlan(VerbalizationModel):
    """A claim-grounded plan; renderers may not introduce new assertions."""

    claim_id: str = Field(min_length=1)
    event: GroundedText
    timing: GroundedText
    implication: GroundedText
    expectations: tuple[GroundedText, ...] = ()
    prerequisites: tuple[GroundedText, ...] = ()
    evidence: tuple[EvidenceSummary, ...] = ()
    safe_actions: tuple[GroundedText, ...] = ()
    limitations: tuple[GroundedText, ...] = ()
    probability: GroundedText
    birth_time_stability: GroundedText
    abstention: GroundedText | None = None


class PredictionBrief(VerbalizationModel):
    """Human-facing concise and paragraph forms of one ContentPlan."""

    claim_id: str = Field(min_length=1)
    concise_sentence: str = Field(min_length=1)
    paragraphs: tuple[str, ...] = Field(min_length=1)
    content_plan: ContentPlan

