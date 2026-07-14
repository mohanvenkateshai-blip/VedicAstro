"""Offline orchestration, snapshot sealing, and approval-gated export."""

from __future__ import annotations

from datetime import datetime

from .models import (
    ApprovalState,
    Citation,
    Contradiction,
    ExtractedClaim,
    ResearchDocument,
    ResearchQuery,
    ResearchSnapshot,
    RuleEvidenceCandidate,
    RuleProposal,
    SourceKind,
    snapshot_checksum,
)
from .policy import SourceAllowlist


class ResearchValidationError(ValueError):
    pass


def seal_snapshot(
    *,
    snapshot_id: str,
    query: ResearchQuery,
    documents: tuple[ResearchDocument, ...],
    citations: tuple[Citation, ...],
    claims: tuple[ExtractedClaim, ...],
    contradictions: tuple[Contradiction, ...] = (),
    created_at: datetime,
    allowlist: SourceAllowlist,
) -> ResearchSnapshot:
    """Validate evidence and return a checksum-sealed immutable snapshot."""

    source_map = _unique_by(documents, lambda item: item.manifest.source_id, "source")
    citation_map = _unique_by(citations, lambda item: item.citation_id, "citation")
    claim_map = _unique_by(claims, lambda item: item.claim_id, "claim")
    for document in documents:
        allowlist.require_allowed(document.manifest)

    for citation in citations:
        document = source_map.get(citation.source_id)
        if document is None:
            raise ResearchValidationError(f"citation {citation.citation_id!r} has no source")
        source = document.manifest
        if source.source_kind is SourceKind.LLM_GENERATED_REPORT:
            raise ResearchValidationError("LLM-generated reports cannot be evidence")
        if citation.quote_word_count > source.max_quote_words:
            raise ResearchValidationError("citation exceeds the source quote limit")
        if citation.quote not in document.content:
            raise ResearchValidationError("citation quote is not present in the immutable source")

    for claim in claims:
        if not claim.citation_ids:
            raise ResearchValidationError(f"claim {claim.claim_id!r} has no source citation")
        if any(citation_id not in citation_map for citation_id in claim.citation_ids):
            raise ResearchValidationError(f"claim {claim.claim_id!r} has a missing citation")
        if any(parent not in claim_map for parent in claim.derived_from_claim_ids):
            raise ResearchValidationError(f"claim {claim.claim_id!r} has a missing parent claim")
    _reject_claim_cycles(claim_map)

    for contradiction in contradictions:
        if any(claim_id not in claim_map for claim_id in contradiction.claim_ids):
            raise ResearchValidationError("contradiction references an unknown claim")

    payload = {
        "snapshot_id": snapshot_id,
        "query": query,
        "documents": documents,
        "citations": citations,
        "claims": claims,
        "contradictions": contradictions,
        "created_at": created_at,
    }
    # ``model_construct`` is used only to canonicalize already validated child
    # models before the checksum.  The returned instance below undergoes full
    # validation, including checksum verification.
    unsealed = ResearchSnapshot.model_construct(**payload, checksum_sha256="")
    checksum = snapshot_checksum(unsealed)
    return ResearchSnapshot(**payload, checksum_sha256=checksum)


def export_rule_candidate(
    proposal: RuleProposal, snapshot: ResearchSnapshot
) -> RuleEvidenceCandidate:
    """Export a staging candidate; never writes a graph, database, or runtime pack."""

    if proposal.state is not ApprovalState.APPROVED:
        raise ResearchValidationError("only approved proposals are exportable")
    if (
        proposal.snapshot_id != snapshot.snapshot_id
        or proposal.snapshot_checksum != snapshot.checksum_sha256
    ):
        raise ResearchValidationError("proposal does not target this immutable snapshot")
    if proposal.approval is None:  # defensive: model validation already enforces this
        raise ResearchValidationError("human Jyotisha approval is required")

    claims = {item.claim_id: item for item in snapshot.claims}
    citations = {item.citation_id: item for item in snapshot.citations}
    if any(claim_id not in claims for claim_id in proposal.claim_ids):
        raise ResearchValidationError("proposal references a claim outside its snapshot")
    if any(citation_id not in citations for citation_id in proposal.citation_ids):
        raise ResearchValidationError("proposal references a citation outside its snapshot")
    claimed_citations = {
        citation_id
        for claim_id in proposal.claim_ids
        for citation_id in claims[claim_id].citation_ids
    }
    if not set(proposal.citation_ids).issubset(claimed_citations):
        raise ResearchValidationError("proposal citations are not evidence for its selected claims")
    source_ids = tuple(sorted({citations[item].source_id for item in proposal.citation_ids}))
    return RuleEvidenceCandidate(
        proposal_id=proposal.proposal_id,
        research_snapshot_id=snapshot.snapshot_id,
        research_snapshot_checksum=snapshot.checksum_sha256,
        event_code=proposal.event_code,
        rule_id=proposal.rule_id,
        signal_name=proposal.signal_name,
        direction=proposal.direction,
        traditional_strength_index=proposal.traditional_strength_index,
        source_confidence=proposal.source_confidence,
        rationale=proposal.rationale,
        source_ids=source_ids,
        citation_ids=proposal.citation_ids,
        test_case_ids=tuple(item.test_case_id for item in proposal.test_cases),
        approved_by=proposal.approval.reviewer_id,
        approved_at=proposal.approval.approved_at,
    )


def _unique_by(items: tuple, key, label: str) -> dict:
    result = {}
    for item in items:
        item_key = key(item)
        if item_key in result:
            raise ResearchValidationError(f"duplicate {label} id: {item_key!r}")
        result[item_key] = item
    return result


def _reject_claim_cycles(claims: dict[str, ExtractedClaim]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(claim_id: str) -> None:
        if claim_id in visiting:
            raise ResearchValidationError("circular claim derivation is not evidence")
        if claim_id in visited:
            return
        visiting.add(claim_id)
        for parent in claims[claim_id].derived_from_claim_ids:
            visit(parent)
        visiting.remove(claim_id)
        visited.add(claim_id)

    for claim_id in claims:
        visit(claim_id)
