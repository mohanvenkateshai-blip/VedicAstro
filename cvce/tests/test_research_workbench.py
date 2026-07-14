from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

import pytest
from forecasting.contracts import EvidenceDirection
from forecasting.taxonomy import EventCode
from pydantic import ValidationError
from research_workbench.evaluation import evaluate_research_quality
from research_workbench.models import (
    ApprovalState,
    Citation,
    Contradiction,
    ExtractedClaim,
    JyotishaApproval,
    LocatorKind,
    ResearchDocument,
    ResearchQuery,
    RuleDiffOperation,
    RuleProposal,
    RuleTestCase,
    SourceKind,
    SourceManifest,
    SourceTier,
    VedicRuleDiff,
)
from research_workbench.policy import ResearchPolicyError, SourceAllowlist
from research_workbench.workbench import (
    ResearchValidationError,
    export_rule_candidate,
    seal_snapshot,
)

NOW = datetime(2026, 7, 14, 8, tzinfo=UTC)
CONTENT = "Saturn's stated condition is associated with delay in the cited source."


def manifest(
    *,
    source_id: str = "source-1",
    content: str = CONTENT,
    license_name: str = "licensed-local-research",
    research_allowed: bool = True,
    source_kind: SourceKind = SourceKind.HUMAN_AUTHORED,
) -> SourceManifest:
    return SourceManifest(
        source_id=source_id,
        title="Reviewed source",
        locator_kind=LocatorKind.LOCAL_PATH,
        locator=f"/approved/{source_id}.txt",
        tier=SourceTier.CRITICAL_EDITION,
        source_kind=source_kind,
        author_or_organisation="Human editor",
        rights_or_license=license_name,
        research_use_allowed=research_allowed,
        published_on=date(2000, 1, 1),
        accessed_at=NOW,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        max_quote_words=12,
    )


def policy() -> SourceAllowlist:
    return SourceAllowlist(
        local_roots=("/approved",),
        accepted_rights_or_licenses=("licensed-local-research",),
    )


def uri_manifest(locator: str) -> SourceManifest:
    return SourceManifest(
        source_id="source-1",
        title="Reviewed web source",
        locator_kind=LocatorKind.URI,
        locator=locator,
        tier=SourceTier.INSTITUTIONAL,
        author_or_organisation="Institution",
        rights_or_license="licensed-local-research",
        research_use_allowed=True,
        accessed_at=NOW,
        content_sha256=hashlib.sha256(CONTENT.encode()).hexdigest(),
        max_quote_words=12,
    )


def query() -> ResearchQuery:
    return ResearchQuery(
        query_id="query-1",
        question="What traditional rule is actually supported?",
        scope="Offline rule research only",
        requested_source_ids=("source-1",),
        created_at=NOW,
    )


def cited_items() -> tuple[Citation, ExtractedClaim]:
    citation = Citation(
        citation_id="citation-1",
        source_id="source-1",
        locator="paragraph 1",
        quote="associated with delay in the cited source",
    )
    claim = ExtractedClaim(
        claim_id="claim-1",
        proposition="The source associates the specified condition with delay.",
        citation_ids=(citation.citation_id,),
    )
    return citation, claim


def snapshot():
    citation, claim = cited_items()
    source = manifest()
    return seal_snapshot(
        snapshot_id="snapshot-1",
        query=query(),
        documents=(ResearchDocument(manifest=source, content=CONTENT),),
        citations=(citation,),
        claims=(claim,),
        created_at=NOW,
        allowlist=policy(),
    )


def proposal(state: ApprovalState = ApprovalState.APPROVED) -> RuleProposal:
    sealed = snapshot()
    approved = state is ApprovalState.APPROVED
    return RuleProposal(
        proposal_id="proposal-1",
        snapshot_id=sealed.snapshot_id,
        snapshot_checksum=sealed.checksum_sha256,
        state=state,
        rule_diff=VedicRuleDiff(
            operation=RuleDiffOperation.ADD,
            target_rule_pack="research-candidates",
            target_rule_pack_version="0.1.0-draft",
            proposed_definition="Map the reviewed condition to bounded opposing evidence.",
        ),
        event_code=EventCode.EMPLOYMENT_START,
        rule_id="research.saturn.delay.v1",
        signal_name="reviewed_saturn_delay",
        direction=EvidenceDirection.OPPOSING,
        traditional_strength_index=-0.4,
        source_confidence=0.75,
        rationale="A bounded proposal based on the cited traditional statement.",
        claim_ids=("claim-1",),
        citation_ids=("citation-1",),
        test_cases=(
            RuleTestCase(
                test_case_id="case-1",
                fixture_reference="fixtures/saturn-delay.json",
                expected_direction=EvidenceDirection.OPPOSING,
                rationale="Confirms the mapped direction.",
            ),
        )
        if approved
        else (),
        approval=JyotishaApproval(
            reviewer_id="jyotisha-1",
            reviewer_name="Qualified human reviewer",
            qualification_or_lineage="Documented Jyotisha training",
            approved_at=NOW,
            note="Citations, interpretation, and fixture reviewed.",
        )
        if approved
        else None,
        rejection_reason="The cited passage does not support this mapping."
        if state is ApprovalState.REJECTED
        else None,
    )


@pytest.mark.parametrize(
    ("license_name", "research_allowed"),
    [("unknown", True), ("licensed-local-research", False)],
)
def test_snapshot_fails_closed_on_licensing(license_name: str, research_allowed: bool) -> None:
    citation, claim = cited_items()
    source = manifest(license_name=license_name, research_allowed=research_allowed)
    with pytest.raises(ResearchPolicyError):
        seal_snapshot(
            snapshot_id="snapshot-1",
            query=query(),
            documents=(ResearchDocument(manifest=source, content=CONTENT),),
            citations=(citation,),
            claims=(claim,),
            created_at=NOW,
            allowlist=policy(),
        )


@pytest.mark.parametrize(
    "locator",
    (
        "https://trusted.example.evil/allowed/source.txt",
        "https://trusted.example/allowed-evil/source.txt",
        "https://user@trusted.example/allowed/source.txt",
        "https://trusted.example/allowed/source.txt#fabricated-section",
        "https://trusted.example/allowed/%2e%2e/outside.txt",
    ),
)
def test_uri_allowlist_rejects_host_path_and_identity_confusion(locator: str) -> None:
    source = uri_manifest(locator)
    strict_policy = SourceAllowlist(
        uri_prefixes=("https://trusted.example/allowed/",),
        accepted_rights_or_licenses=("licensed-local-research",),
    )
    with pytest.raises(ResearchPolicyError):
        strict_policy.require_allowed(source)


def test_uri_allowlist_accepts_only_contained_path_segments() -> None:
    source = uri_manifest("https://trusted.example/allowed/source.txt")
    strict_policy = SourceAllowlist(
        uri_prefixes=("https://trusted.example/allowed/",),
        accepted_rights_or_licenses=("licensed-local-research",),
    )
    strict_policy.require_allowed(source)


def test_snapshot_rejects_missing_citation() -> None:
    source = manifest()
    with pytest.raises(ResearchValidationError, match="no source citation"):
        seal_snapshot(
            snapshot_id="snapshot-1",
            query=query(),
            documents=(ResearchDocument(manifest=source, content=CONTENT),),
            citations=(),
            claims=(ExtractedClaim(claim_id="claim-1", proposition="Unsupported"),),
            created_at=NOW,
            allowlist=policy(),
        )


def test_llm_report_cannot_cite_itself_as_evidence() -> None:
    citation, claim = cited_items()
    source = manifest(source_kind=SourceKind.LLM_GENERATED_REPORT)
    with pytest.raises(ResearchValidationError, match="LLM-generated reports"):
        seal_snapshot(
            snapshot_id="snapshot-1",
            query=query(),
            documents=(ResearchDocument(manifest=source, content=CONTENT),),
            citations=(citation,),
            claims=(claim,),
            created_at=NOW,
            allowlist=policy(),
        )


def test_circular_claim_derivation_is_rejected() -> None:
    citation, _ = cited_items()
    source = manifest()
    claims = (
        ExtractedClaim(
            claim_id="claim-1",
            proposition="First",
            citation_ids=(citation.citation_id,),
            derived_from_claim_ids=("claim-2",),
        ),
        ExtractedClaim(
            claim_id="claim-2",
            proposition="Second",
            citation_ids=(citation.citation_id,),
            derived_from_claim_ids=("claim-1",),
        ),
    )
    with pytest.raises(ResearchValidationError, match="circular"):
        seal_snapshot(
            snapshot_id="snapshot-1",
            query=query(),
            documents=(ResearchDocument(manifest=source, content=CONTENT),),
            citations=(citation,),
            claims=claims,
            created_at=NOW,
            allowlist=policy(),
        )


def test_direct_self_derivation_is_rejected_by_contract() -> None:
    with pytest.raises(ValidationError, match="cannot cite itself"):
        ExtractedClaim(
            claim_id="claim-1",
            proposition="Circular",
            citation_ids=("citation-1",),
            derived_from_claim_ids=("claim-1",),
        )


def test_snapshot_is_frozen_and_checksum_detects_tampering() -> None:
    sealed = snapshot()
    with pytest.raises(ValidationError):
        sealed.snapshot_id = "changed"  # type: ignore[misc]
    payload = sealed.model_dump(mode="json")
    payload["query"]["question"] = "Tampered"
    with pytest.raises(ValidationError, match="checksum"):
        type(sealed).model_validate(payload)


@pytest.mark.parametrize(
    "state", [ApprovalState.DRAFT, ApprovalState.IN_REVIEW, ApprovalState.REJECTED]
)
def test_non_approved_proposal_cannot_export(state: ApprovalState) -> None:
    with pytest.raises(ResearchValidationError, match="only approved"):
        export_rule_candidate(proposal(state), snapshot())


def test_approved_proposal_exports_rule_evidence_compatible_candidate() -> None:
    sealed = snapshot()
    candidate = export_rule_candidate(proposal(), sealed)
    assert candidate.rule_id == "research.saturn.delay.v1"
    assert candidate.source_ids == ("source-1",)
    assert candidate.citation_ids == ("citation-1",)
    assert candidate.test_case_ids == ("case-1",)
    assert candidate.approved_by == "jyotisha-1"


def test_quality_metrics_report_unsupported_and_contradiction_coverage() -> None:
    citation, supported = cited_items()
    unsupported = ExtractedClaim(claim_id="claim-2", proposition="Unsupported")
    metrics = evaluate_research_quality(
        (supported, unsupported),
        (citation,),
        (
            Contradiction(
                contradiction_id="conflict-1",
                claim_ids=("claim-1", "claim-2"),
                explanation="The statements point in opposing directions.",
            ),
        ),
    )
    assert metrics.citation_coverage == 0.5
    assert metrics.unsupported_claim_rate == 0.5
    assert metrics.contradiction_coverage == 1.0
