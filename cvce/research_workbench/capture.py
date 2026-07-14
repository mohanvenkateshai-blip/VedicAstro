"""Capture-first research archive, separate from evidence promotion.

Raw capture maximises research recall.  It records weak or unusable hypotheses
without pretending they are evidence.  Promotion remains a separate,
fail-closed decision.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .models import (
    ApprovalState,
    ResearchModel,
    ResearchQuery,
    ResearchSnapshot,
    SourceKind,
    SourceManifest,
    snapshot_checksum,
)
from .persistence import SQLiteResearchPersistence
from .policy import SourceAllowlist


class HypothesisOrigin(StrEnum):
    SOURCE_EXTRACTION = "source_extraction"
    HUMAN_NOTE = "human_note"
    LLM_DERIVED = "llm_derived"


class CaptureAnnotation(StrEnum):
    LLM_DERIVED = "llm_derived"
    UNCITED = "uncited"
    WEAK = "weak"
    CONTRADICTED = "contradicted"
    UNAPPROVED = "unapproved"
    LICENSE_LIMITED = "license_limited"
    MISSING_REFERENCE = "missing_reference"


class CitationLicenseStatus(StrEnum):
    ALLOWED = "allowed"
    LIMITED = "limited"
    UNKNOWN = "unknown"


class AssessmentDecision(StrEnum):
    NEEDS_REVIEW = "needs_review"
    PROMOTABLE = "promotable"
    REJECTED_FOR_PROMOTION = "rejected_for_promotion"


class CapturedCitation(ResearchModel):
    """Citation metadata; quote text is optional when rights prohibit retention."""

    citation_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    quote: str | None = None
    retention_note: str = Field(min_length=1)
    license_status: CitationLicenseStatus = CitationLicenseStatus.UNKNOWN


class RawHypothesis(ResearchModel):
    hypothesis_id: str = Field(min_length=1)
    proposition: str = Field(min_length=1)
    origin: HypothesisOrigin
    citation_ids: tuple[str, ...] = ()
    confidence: float | None = Field(default=None, ge=0, le=1)
    contradicted_by: tuple[str, ...] = ()
    approval_state: ApprovalState = ApprovalState.DRAFT
    annotations: tuple[CaptureAnnotation, ...] = ()


class RawResearchCapture(ResearchModel):
    capture_id: str = Field(min_length=1)
    query: ResearchQuery
    sources: tuple[SourceManifest, ...]
    citations: tuple[CapturedCitation, ...]
    hypotheses: tuple[RawHypothesis, ...]
    captured_at: datetime
    checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_capture(self) -> RawResearchCapture:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        if self.checksum_sha256 != _capture_checksum(self):
            raise ValueError("raw capture checksum does not match immutable payload")
        return self


class EvidenceAssessment(ResearchModel):
    assessment_id: str = Field(min_length=1)
    capture_id: str = Field(min_length=1)
    hypothesis_id: str = Field(min_length=1)
    decision: AssessmentDecision
    reasons: tuple[str, ...]
    assessed_by: str = Field(min_length=1)
    assessed_at: datetime
    revision: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_assessment(self) -> EvidenceAssessment:
        if not self.reasons:
            raise ValueError("an evidence assessment requires reasons")
        if self.assessed_at.tzinfo is None:
            raise ValueError("assessed_at must be timezone-aware")
        return self


class PromotionCandidate(ResearchModel):
    """A staging record, not a RuleEvidence or production graph mutation."""

    capture_id: str
    hypothesis_id: str
    proposition: str
    citation_ids: tuple[str, ...]
    assessment_id: str
    assessed_by: str


def capture_raw_research(
    *,
    capture_id: str,
    query: ResearchQuery,
    sources: tuple[SourceManifest, ...],
    citations: tuple[CapturedCitation, ...],
    hypotheses: tuple[RawHypothesis, ...],
    captured_at: datetime,
    weak_confidence_threshold: float = 0.5,
) -> RawResearchCapture:
    """Capture hypotheses without applying evidence or product eligibility filters."""

    source_map = _unique(sources, lambda item: item.source_id, "source")
    _unique(citations, lambda item: item.citation_id, "citation")
    hypothesis_map = _unique(hypotheses, lambda item: item.hypothesis_id, "hypothesis")
    captured_citations: list[CapturedCitation] = []
    for citation in citations:
        source = source_map.get(citation.source_id)
        if source is None:
            citation = citation.model_copy(
                update={
                    "quote": None,
                    "license_status": CitationLicenseStatus.UNKNOWN,
                    "retention_note": (
                        f"{citation.retention_note.rstrip()} "
                        "Quote omitted because source rights and checksum are unavailable."
                    ),
                }
            )
        elif not source.research_use_allowed:
            citation = citation.model_copy(update={"license_status": CitationLicenseStatus.LIMITED})
        over_quote_limit = bool(
            source and citation.quote and len(citation.quote.split()) > source.max_quote_words
        )
        if (
            source is not None
            and (
                not source.research_use_allowed
                or citation.license_status is CitationLicenseStatus.LIMITED
                or over_quote_limit
            )
            and citation.quote
        ):
            citation = citation.model_copy(
                update={
                    "quote": None,
                    "retention_note": (
                        f"{citation.retention_note.rstrip()} "
                        "Quote omitted because source rights or quote limits do not permit retention."
                    ),
                }
            )
        captured_citations.append(citation)
    citation_map = {item.citation_id: item for item in captured_citations}

    captured_hypotheses: list[RawHypothesis] = []
    license_limited_sources = {
        source_id for source_id, source in source_map.items() if not source.research_use_allowed
    }
    for hypothesis in hypotheses:
        annotations = set(hypothesis.annotations)
        if hypothesis.origin is HypothesisOrigin.LLM_DERIVED:
            annotations.add(CaptureAnnotation.LLM_DERIVED)
        if not hypothesis.citation_ids:
            annotations.add(CaptureAnnotation.UNCITED)
        if hypothesis.confidence is not None and hypothesis.confidence < weak_confidence_threshold:
            annotations.add(CaptureAnnotation.WEAK)
        if hypothesis.contradicted_by:
            annotations.add(CaptureAnnotation.CONTRADICTED)
        if hypothesis.approval_state is not ApprovalState.APPROVED:
            annotations.add(CaptureAnnotation.UNAPPROVED)
        missing_citations = {
            citation_id
            for citation_id in hypothesis.citation_ids
            if citation_id not in citation_map
        }
        missing_contradictions = {
            hypothesis_id
            for hypothesis_id in hypothesis.contradicted_by
            if hypothesis_id not in hypothesis_map
        }
        cited_license_limited = any(
            citation_map[citation_id].license_status is CitationLicenseStatus.LIMITED
            or citation_map[citation_id].source_id in license_limited_sources
            for citation_id in hypothesis.citation_ids
            if citation_id in citation_map
        )
        if cited_license_limited:
            annotations.add(CaptureAnnotation.LICENSE_LIMITED)
        if (
            missing_citations
            or missing_contradictions
            or any(
                citation_map[citation_id].source_id not in source_map
                for citation_id in hypothesis.citation_ids
                if citation_id in citation_map
            )
        ):
            annotations.add(CaptureAnnotation.MISSING_REFERENCE)
        captured_hypotheses.append(
            hypothesis.model_copy(update={"annotations": tuple(sorted(annotations, key=str))})
        )

    # Unknown citation/contradiction references are annotations-worthy research
    # gaps, not reasons to erase the hypothesis. Their identifiers remain intact.
    payload = {
        "capture_id": capture_id,
        "query": query,
        "sources": sources,
        "citations": tuple(captured_citations),
        "hypotheses": tuple(captured_hypotheses),
        "captured_at": captured_at,
    }
    unsealed = RawResearchCapture.model_construct(**payload, checksum_sha256="")
    return RawResearchCapture(**payload, checksum_sha256=_capture_checksum(unsealed))


def stage_for_promotion(
    capture: RawResearchCapture,
    assessment: EvidenceAssessment,
    allowlist: SourceAllowlist,
    snapshot: ResearchSnapshot | None = None,
) -> PromotionCandidate:
    """Fail closed while leaving the original capture untouched and queryable."""

    if capture.checksum_sha256 != _capture_checksum(capture):
        raise ValueError("promotion requires an untampered immutable raw capture")
    if snapshot is not None and snapshot.checksum_sha256 != snapshot_checksum(snapshot):
        raise ValueError("promotion requires an untampered immutable evidence snapshot")
    if assessment.capture_id != capture.capture_id:
        raise ValueError("assessment does not belong to this capture")
    if assessment.decision is not AssessmentDecision.PROMOTABLE:
        raise ValueError("only a promotable assessment can create a promotion candidate")
    if snapshot is None:
        raise ValueError("promotion requires an immutable sealed evidence snapshot")
    if snapshot.query != capture.query:
        raise ValueError("sealed snapshot query is not bound to the raw capture")
    hypothesis = next(
        (item for item in capture.hypotheses if item.hypothesis_id == assessment.hypothesis_id),
        None,
    )
    if hypothesis is None:
        raise ValueError("assessment references an unknown hypothesis")
    if not hypothesis.citation_ids:
        raise ValueError("promotion requires citations")
    snapshot_claim = next(
        (item for item in snapshot.claims if item.claim_id == hypothesis.hypothesis_id),
        None,
    )
    if snapshot_claim is None:
        raise ValueError("sealed snapshot does not contain the promoted hypothesis")
    if (
        snapshot_claim.proposition != hypothesis.proposition
        or snapshot_claim.citation_ids != hypothesis.citation_ids
    ):
        raise ValueError("sealed snapshot evidence differs from the captured hypothesis")
    citations = {item.citation_id: item for item in capture.citations}
    sources = {item.source_id: item for item in capture.sources}
    for citation_id in hypothesis.citation_ids:
        citation = citations.get(citation_id)
        if (
            citation is None
            or not citation.quote
            or citation.license_status is not CitationLicenseStatus.ALLOWED
        ):
            raise ValueError("promotion requires retained source citation text")
        source = sources.get(citation.source_id)
        if source is None:
            raise ValueError("promotion citation has no source manifest")
        allowlist.require_allowed(source)
        if len(citation.quote.split()) > source.max_quote_words:
            raise ValueError("promotion citation exceeds source quote limit")
        if source.source_kind is SourceKind.LLM_GENERATED_REPORT:
            raise ValueError("LLM-generated reports cannot be promoted as evidence")
        sealed_source = next(
            (
                item.manifest
                for item in snapshot.documents
                if item.manifest.source_id == source.source_id
            ),
            None,
        )
        sealed_citation = next(
            (item for item in snapshot.citations if item.citation_id == citation_id),
            None,
        )
        if (
            sealed_source is None
            or sealed_source != source
            or sealed_citation is None
            or (
                sealed_citation.citation_id,
                sealed_citation.source_id,
                sealed_citation.locator,
                sealed_citation.quote,
            )
            != (
                citation.citation_id,
                citation.source_id,
                citation.locator,
                citation.quote,
            )
        ):
            raise ValueError("promotion requires matching checksummed snapshot evidence")
    return PromotionCandidate(
        capture_id=capture.capture_id,
        hypothesis_id=hypothesis.hypothesis_id,
        proposition=hypothesis.proposition,
        citation_ids=hypothesis.citation_ids,
        assessment_id=assessment.assessment_id,
        assessed_by=assessment.assessed_by,
    )


class ResearchCaptureArchive:
    """Thread-safe append-only archive with optional durable SQLite storage."""

    def __init__(self, persistence: SQLiteResearchPersistence | None = None) -> None:
        if persistence is None and os.environ.get("RESEARCH_CAPTURE_DB"):
            persistence = SQLiteResearchPersistence(os.environ["RESEARCH_CAPTURE_DB"])
        self._persistence = persistence
        self._lock = threading.RLock()
        self._captures: dict[str, RawResearchCapture] = {}
        self._assessments: list[EvidenceAssessment] = []
        self._reload_shared_state_locked()

    @classmethod
    def for_research(
        cls, db_path: str | os.PathLike[str] | None = None
    ) -> ResearchCaptureArchive:
        """Create fail-closed research mode with mandatory durable storage."""

        configured_path = db_path or os.environ.get("RESEARCH_CAPTURE_DB")
        if not configured_path:
            raise RuntimeError(
                "research mode requires db_path or RESEARCH_CAPTURE_DB durable storage"
            )
        return cls(SQLiteResearchPersistence(configured_path))

    def _reload_shared_state_locked(self) -> None:
        if self._persistence is None:
            return
        self._captures = {
            item.capture_id: item
            for item in (
                RawResearchCapture.model_validate(payload)
                for payload in self._persistence.load_captures()
            )
        }
        self._assessments = [
            EvidenceAssessment.model_validate(payload)
            for payload in self._persistence.load_assessments()
        ]

    def record_capture(self, capture: RawResearchCapture) -> None:
        with self._lock:
            self._reload_shared_state_locked()
            if capture.capture_id in self._captures:
                raise ValueError("capture IDs are immutable and cannot be overwritten")
            if self._persistence is not None:
                self._persistence.save_capture(capture.model_dump(mode="json"))
            self._captures[capture.capture_id] = capture

    def record_assessment(self, assessment: EvidenceAssessment) -> None:
        with self._lock:
            self._reload_shared_state_locked()
            capture = self._captures.get(assessment.capture_id)
            if capture is None:
                raise ValueError("assessment references an unknown capture")
            if assessment.hypothesis_id not in {item.hypothesis_id for item in capture.hypotheses}:
                raise ValueError("assessment references an unknown hypothesis")
            if assessment.assessment_id in {item.assessment_id for item in self._assessments}:
                raise ValueError("assessment IDs are immutable and cannot be overwritten")
            revisions = [
                item.revision
                for item in self._assessments
                if item.capture_id == assessment.capture_id
                and item.hypothesis_id == assessment.hypothesis_id
            ]
            expected_revision = max(revisions, default=0) + 1
            if assessment.revision != expected_revision:
                raise ValueError(
                    f"assessment revision must be monotonic; expected {expected_revision}"
                )
            if self._persistence is not None:
                self._persistence.save_assessment(assessment.model_dump(mode="json"))
            self._assessments.append(assessment)

    def query_hypotheses(
        self,
        *,
        include_rejected: bool = True,
        annotations: set[CaptureAnnotation] | None = None,
    ) -> tuple[dict[str, Any], ...]:
        with self._lock:
            self._reload_shared_state_locked()
            latest: dict[tuple[str, str], EvidenceAssessment] = {}
            for item in self._assessments:
                key = (item.capture_id, item.hypothesis_id)
                current = latest.get(key)
                if current is None or (item.revision, item.assessment_id) > (
                    current.revision,
                    current.assessment_id,
                ):
                    latest[key] = item
            results: list[dict[str, Any]] = []
            for capture in self._captures.values():
                for hypothesis in capture.hypotheses:
                    assessment = latest.get((capture.capture_id, hypothesis.hypothesis_id))
                    if (
                        not include_rejected
                        and assessment
                        and assessment.decision is AssessmentDecision.REJECTED_FOR_PROMOTION
                    ):
                        continue
                    if annotations and not annotations.issubset(set(hypothesis.annotations)):
                        continue
                    results.append(
                        {
                            "capture": capture.model_copy(deep=True),
                            "hypothesis": hypothesis.model_copy(deep=True),
                            "latest_assessment": assessment.model_copy(deep=True)
                            if assessment
                            else None,
                        }
                    )
            return tuple(results)


def _unique(items: tuple, key, label: str) -> dict:
    result = {}
    for item in items:
        item_id = key(item)
        if item_id in result:
            raise ValueError(f"duplicate {label} ID: {item_id!r}")
        result[item_id] = item
    return result


def _capture_payload(capture: RawResearchCapture | dict[str, Any]) -> dict[str, Any]:
    payload = capture.model_dump(mode="json") if isinstance(capture, BaseModel) else dict(capture)
    payload.pop("checksum_sha256", None)
    return payload


def _capture_checksum(capture: RawResearchCapture | dict[str, Any]) -> str:
    encoded = json.dumps(
        _capture_payload(capture),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"cannot canonicalize {type(value).__name__}")
