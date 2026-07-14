"""Immutable contracts for the offline research workbench.

These models describe research artefacts, not runtime predictions.  A sealed
snapshot can be reviewed and can yield a rule *candidate*, but it cannot mutate
the production graph or rule packs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import Enum, StrEnum
from typing import Any

from forecasting.contracts import EvidenceDirection
from forecasting.taxonomy import EventCode
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class LocatorKind(StrEnum):
    URI = "uri"
    LOCAL_PATH = "local_path"


class SourceTier(StrEnum):
    PRIMARY_TEXT = "primary_text"
    CRITICAL_EDITION = "critical_edition"
    SCHOLARLY = "scholarly"
    INSTITUTIONAL = "institutional"
    PRACTITIONER = "practitioner"
    DISCOVERY_ONLY = "discovery_only"


class SourceKind(StrEnum):
    HUMAN_AUTHORED = "human_authored"
    DATASET = "dataset"
    LLM_GENERATED_REPORT = "llm_generated_report"


class ApprovalState(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class RuleDiffOperation(StrEnum):
    ADD = "add"
    REPLACE = "replace"
    RETIRE = "retire"


class ContradictionStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class SourceManifest(ResearchModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    locator_kind: LocatorKind
    locator: str = Field(min_length=1)
    tier: SourceTier
    source_kind: SourceKind = SourceKind.HUMAN_AUTHORED
    author_or_organisation: str = Field(min_length=1)
    rights_or_license: str = Field(min_length=1)
    research_use_allowed: bool
    published_on: date | None = None
    accessed_at: datetime
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_quote_words: int = Field(default=25, ge=0, le=25)

    @model_validator(mode="after")
    def validate_dates_and_evidence_kind(self) -> SourceManifest:
        if self.accessed_at.tzinfo is None:
            raise ValueError("accessed_at must be timezone-aware")
        return self

    @property
    def evidence_eligible(self) -> bool:
        return self.research_use_allowed and self.source_kind is not SourceKind.LLM_GENERATED_REPORT


class ResearchDocument(ResearchModel):
    manifest: SourceManifest
    content: str

    @model_validator(mode="after")
    def validate_checksum(self) -> ResearchDocument:
        digest = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if digest != self.manifest.content_sha256:
            raise ValueError("document content does not match manifest checksum")
        return self


class ResearchQuery(ResearchModel):
    query_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    requested_source_ids: tuple[str, ...] = ()
    created_at: datetime

    @model_validator(mode="after")
    def validate_created_at(self) -> ResearchQuery:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self


class Citation(ResearchModel):
    citation_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    locator: str = Field(min_length=1, description="Page, verse, paragraph, or stable section")
    quote: str = Field(min_length=1)

    @property
    def quote_word_count(self) -> int:
        return len(self.quote.split())


class ExtractedClaim(ResearchModel):
    claim_id: str = Field(min_length=1)
    proposition: str = Field(min_length=1)
    citation_ids: tuple[str, ...] = ()
    derived_from_claim_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def reject_direct_self_reference(self) -> ExtractedClaim:
        if self.claim_id in self.derived_from_claim_ids:
            raise ValueError("a claim cannot cite itself as derivation evidence")
        return self


class Contradiction(ResearchModel):
    contradiction_id: str = Field(min_length=1)
    claim_ids: tuple[str, str]
    explanation: str = Field(min_length=1)
    status: ContradictionStatus = ContradictionStatus.OPEN
    resolution_note: str | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> Contradiction:
        if self.claim_ids[0] == self.claim_ids[1]:
            raise ValueError("a contradiction requires two different claims")
        if self.status is ContradictionStatus.RESOLVED and not self.resolution_note:
            raise ValueError("a resolved contradiction requires a resolution note")
        return self


class ResearchSnapshot(ResearchModel):
    snapshot_id: str = Field(min_length=1)
    query: ResearchQuery
    documents: tuple[ResearchDocument, ...]
    citations: tuple[Citation, ...]
    claims: tuple[ExtractedClaim, ...]
    contradictions: tuple[Contradiction, ...] = ()
    created_at: datetime
    checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_checksum(self) -> ResearchSnapshot:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.checksum_sha256 != snapshot_checksum(self):
            raise ValueError("snapshot checksum does not match immutable payload")
        return self


class RuleTestCase(ResearchModel):
    test_case_id: str = Field(min_length=1)
    fixture_reference: str = Field(min_length=1)
    expected_direction: EvidenceDirection
    rationale: str = Field(min_length=1)


class JyotishaApproval(ResearchModel):
    reviewer_id: str = Field(min_length=1)
    reviewer_name: str = Field(min_length=1)
    qualification_or_lineage: str = Field(min_length=1)
    approved_at: datetime
    note: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_time(self) -> JyotishaApproval:
        if self.approved_at.tzinfo is None:
            raise ValueError("approved_at must be timezone-aware")
        return self


class VedicRuleDiff(ResearchModel):
    """Human-reviewable change; never an executable patch."""

    operation: RuleDiffOperation
    target_rule_pack: str = Field(min_length=1)
    target_rule_pack_version: str = Field(min_length=1)
    previous_definition: str | None = None
    proposed_definition: str | None = None

    @model_validator(mode="after")
    def validate_operation(self) -> VedicRuleDiff:
        if self.operation is RuleDiffOperation.ADD and not self.proposed_definition:
            raise ValueError("an added rule requires a proposed definition")
        if self.operation is RuleDiffOperation.REPLACE and (
            not self.previous_definition or not self.proposed_definition
        ):
            raise ValueError("a replacement requires previous and proposed definitions")
        if self.operation is RuleDiffOperation.RETIRE and not self.previous_definition:
            raise ValueError("a retired rule requires its previous definition")
        return self


class RuleProposal(ResearchModel):
    proposal_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    snapshot_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    state: ApprovalState
    rule_diff: VedicRuleDiff
    event_code: EventCode
    rule_id: str = Field(min_length=1)
    signal_name: str = Field(min_length=1)
    direction: EvidenceDirection
    traditional_strength_index: float
    source_confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)
    claim_ids: tuple[str, ...]
    citation_ids: tuple[str, ...]
    test_cases: tuple[RuleTestCase, ...] = ()
    approval: JyotishaApproval | None = None
    rejection_reason: str | None = None

    @model_validator(mode="after")
    def validate_workflow_state(self) -> RuleProposal:
        if self.state is ApprovalState.APPROVED:
            if self.approval is None:
                raise ValueError("approved proposals require a human Jyotisha approval")
            if not self.test_cases:
                raise ValueError("approved proposals require test cases")
            if not self.claim_ids or not self.citation_ids:
                raise ValueError("approved proposals require claims and source citations")
        elif self.approval is not None:
            raise ValueError("only approved proposals may carry an approval record")
        if self.state is ApprovalState.REJECTED and not self.rejection_reason:
            raise ValueError("rejected proposals require a reason")
        return self


class RuleEvidenceCandidate(ResearchModel):
    """Staging contract aligned to ``forecasting.contracts.RuleEvidence``.

    It intentionally lacks runtime calculation provenance.  Runtime adapters
    must supply that only after a separately versioned rule-pack release.
    """

    proposal_id: str
    research_snapshot_id: str
    research_snapshot_checksum: str
    event_code: EventCode
    rule_id: str
    signal_name: str
    direction: EvidenceDirection
    traditional_strength_index: float
    source_confidence: float = Field(ge=0, le=1)
    rationale: str
    source_ids: tuple[str, ...]
    citation_ids: tuple[str, ...]
    test_case_ids: tuple[str, ...]
    approved_by: str
    approved_at: datetime


def _snapshot_payload(snapshot: ResearchSnapshot | dict[str, Any]) -> dict[str, Any]:
    if isinstance(snapshot, ResearchSnapshot):
        payload = snapshot.model_dump(mode="json")
    else:
        payload = dict(snapshot)
    payload.pop("checksum_sha256", None)
    return payload


def snapshot_checksum(snapshot: ResearchSnapshot | dict[str, Any]) -> str:
    payload = json.dumps(
        _snapshot_payload(snapshot),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_canonical_json_default,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"cannot canonicalize {type(value).__name__}")
