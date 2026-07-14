from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from research_workbench.capture import (
    AssessmentDecision,
    CaptureAnnotation,
    CapturedCitation,
    CitationLicenseStatus,
    EvidenceAssessment,
    HypothesisOrigin,
    RawHypothesis,
    ResearchCaptureArchive,
    capture_raw_research,
    stage_for_promotion,
)
from research_workbench.models import (
    ApprovalState,
    Citation,
    ExtractedClaim,
    LocatorKind,
    ResearchDocument,
    ResearchQuery,
    SourceKind,
    SourceManifest,
    SourceTier,
)
from research_workbench.persistence import SQLiteResearchPersistence
from research_workbench.policy import SourceAllowlist
from research_workbench.workbench import seal_snapshot

NOW = datetime(2026, 7, 14, 10, tzinfo=UTC)


def source(*, allowed: bool = True) -> SourceManifest:
    return SourceManifest(
        source_id="restricted-source",
        title="Captured source metadata",
        locator_kind=LocatorKind.URI,
        locator="https://archive.example/item/1",
        tier=SourceTier.DISCOVERY_ONLY,
        source_kind=SourceKind.LLM_GENERATED_REPORT,
        author_or_organisation="Research agent",
        rights_or_license="metadata-only",
        research_use_allowed=allowed,
        accessed_at=NOW,
        content_sha256=hashlib.sha256(b"").hexdigest(),
        max_quote_words=0,
    )


def query() -> ResearchQuery:
    return ResearchQuery(
        query_id="capture-query",
        question="Which hypotheses need investigation?",
        scope="Research recall, not product evidence",
        created_at=NOW,
    )


def test_raw_capture_retains_weak_uncited_llm_without_unrelated_license_annotation() -> None:
    hypothesis = RawHypothesis(
        hypothesis_id="hypothesis-1",
        proposition="An agent suggested a relationship that still needs evidence.",
        origin=HypothesisOrigin.LLM_DERIVED,
        citation_ids=(),
        confidence=0.2,
        approval_state=ApprovalState.DRAFT,
    )

    capture = capture_raw_research(
        capture_id="capture-1",
        query=query(),
        sources=(source(allowed=False),),
        citations=(),
        hypotheses=(hypothesis,),
        captured_at=NOW,
    )

    retained = capture.hypotheses[0]
    assert set(retained.annotations) >= {
        CaptureAnnotation.LLM_DERIVED,
        CaptureAnnotation.UNCITED,
        CaptureAnnotation.WEAK,
        CaptureAnnotation.UNAPPROVED,
    }
    assert CaptureAnnotation.LICENSE_LIMITED not in retained.annotations
    assert retained.proposition.startswith("An agent suggested")
    assert capture.sources[0].title == "Captured source metadata"
    assert capture.citations == ()


def test_license_limited_capture_keeps_metadata_but_not_quote_text() -> None:
    capture = capture_raw_research(
        capture_id="capture-1",
        query=query(),
        sources=(source(allowed=False),),
        citations=(
            CapturedCitation(
                citation_id="citation-1",
                source_id="restricted-source",
                locator="section 2",
                quote="This text must not be retained.",
                retention_note="Captured from a restricted source.",
            ),
        ),
        hypotheses=(
            RawHypothesis(
                hypothesis_id="hypothesis-1",
                proposition="Metadata-only claim for follow-up.",
                origin=HypothesisOrigin.HUMAN_NOTE,
                citation_ids=("citation-1",),
            ),
        ),
        captured_at=NOW,
    )
    assert capture.citations[0].quote is None
    assert "do not permit retention" in capture.citations[0].retention_note
    assert CaptureAnnotation.LICENSE_LIMITED in capture.hypotheses[0].annotations


def test_contradicted_hypotheses_are_retained_and_annotated() -> None:
    capture = capture_raw_research(
        capture_id="capture-1",
        query=query(),
        sources=(),
        citations=(),
        hypotheses=(
            RawHypothesis(
                hypothesis_id="a",
                proposition="First interpretation.",
                origin=HypothesisOrigin.HUMAN_NOTE,
                contradicted_by=("b",),
            ),
            RawHypothesis(
                hypothesis_id="b",
                proposition="Opposing interpretation.",
                origin=HypothesisOrigin.HUMAN_NOTE,
                contradicted_by=("a",),
            ),
        ),
        captured_at=NOW,
    )
    assert len(capture.hypotheses) == 2
    assert all(CaptureAnnotation.CONTRADICTED in item.annotations for item in capture.hypotheses)


def test_rejected_for_promotion_remains_research_queryable() -> None:
    capture = capture_raw_research(
        capture_id="capture-1",
        query=query(),
        sources=(),
        citations=(),
        hypotheses=(
            RawHypothesis(
                hypothesis_id="hypothesis-1",
                proposition="Unverified but retained hypothesis.",
                origin=HypothesisOrigin.LLM_DERIVED,
            ),
        ),
        captured_at=NOW,
    )
    assessment = EvidenceAssessment(
        assessment_id="assessment-1",
        capture_id=capture.capture_id,
        hypothesis_id="hypothesis-1",
        decision=AssessmentDecision.REJECTED_FOR_PROMOTION,
        reasons=("No eligible source citation",),
        assessed_by="reviewer-1",
        assessed_at=NOW,
    )
    archive = ResearchCaptureArchive()
    archive.record_capture(capture)
    archive.record_assessment(assessment)

    records = archive.query_hypotheses(include_rejected=True)
    assert len(records) == 1
    assert records[0]["hypothesis"].hypothesis_id == "hypothesis-1"
    assert records[0]["latest_assessment"].decision is AssessmentDecision.REJECTED_FOR_PROMOTION
    assert archive.query_hypotheses(include_rejected=False) == ()
    with pytest.raises(ValueError, match="only a promotable assessment"):
        stage_for_promotion(
            capture,
            assessment,
            SourceAllowlist(),
        )
    # Promotion rejection does not mutate or remove the research record.
    assert archive.query_hypotheses(include_rejected=True)[0]["hypothesis"].proposition


def make_capture(capture_id: str):
    return capture_raw_research(
        capture_id=capture_id,
        query=query(),
        sources=(),
        citations=(),
        hypotheses=(
            RawHypothesis(
                hypothesis_id=f"hypothesis-{capture_id}",
                proposition=f"Retained {capture_id}",
                origin=HypothesisOrigin.HUMAN_NOTE,
            ),
        ),
        captured_at=NOW,
    )


def test_sqlite_archive_survives_restart_with_assessment(tmp_path) -> None:
    persistence = SQLiteResearchPersistence(tmp_path / "research.sqlite3")
    archive = ResearchCaptureArchive(persistence)
    capture = make_capture("durable")
    archive.record_capture(capture)
    archive.record_assessment(
        EvidenceAssessment(
            assessment_id="durable-assessment",
            capture_id=capture.capture_id,
            hypothesis_id="hypothesis-durable",
            decision=AssessmentDecision.REJECTED_FOR_PROMOTION,
            reasons=("Insufficient evidence",),
            assessed_by="reviewer",
            assessed_at=NOW,
        )
    )

    restarted = ResearchCaptureArchive(SQLiteResearchPersistence(tmp_path / "research.sqlite3"))
    record = restarted.query_hypotheses()[0]
    assert record["capture"].checksum_sha256 == capture.checksum_sha256
    assert record["latest_assessment"].assessment_id == "durable-assessment"


def test_archive_mutations_are_concurrency_safe(tmp_path) -> None:
    archive = ResearchCaptureArchive(SQLiteResearchPersistence(tmp_path / "concurrent.sqlite3"))
    captures = [make_capture(f"concurrent-{index}") for index in range(24)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        tuple(pool.map(archive.record_capture, captures))
    assert len(archive.query_hypotheses()) == 24
    assert (
        len(
            ResearchCaptureArchive(
                SQLiteResearchPersistence(tmp_path / "concurrent.sqlite3")
            ).query_hypotheses()
        )
        == 24
    )


def test_explicit_capture_research_mode_requires_durability(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RESEARCH_CAPTURE_DB", raising=False)
    with pytest.raises(RuntimeError, match="requires db_path"):
        ResearchCaptureArchive.for_research()
    durable = ResearchCaptureArchive.for_research(tmp_path / "required.sqlite3")
    assert durable._persistence is not None


def test_peer_archives_reload_shared_appends_and_revision_order(tmp_path) -> None:
    path = tmp_path / "shared.sqlite3"
    first = ResearchCaptureArchive.for_research(path)
    second = ResearchCaptureArchive.for_research(path)
    capture = make_capture("shared")
    first.record_capture(capture)
    assert second.query_hypotheses()[0]["capture"].capture_id == "shared"

    second.record_assessment(
        EvidenceAssessment(
            assessment_id="z-first",
            capture_id="shared",
            hypothesis_id="hypothesis-shared",
            decision=AssessmentDecision.NEEDS_REVIEW,
            reasons=("First review",),
            assessed_by="reviewer",
            assessed_at=NOW,
            revision=1,
        )
    )
    first.record_assessment(
        EvidenceAssessment(
            assessment_id="a-second",
            capture_id="shared",
            hypothesis_id="hypothesis-shared",
            decision=AssessmentDecision.REJECTED_FOR_PROMOTION,
            reasons=("Second review",),
            assessed_by="reviewer",
            assessed_at=NOW,
            revision=2,
        )
    )
    latest = second.query_hypotheses()[0]["latest_assessment"]
    assert latest.revision == 2
    assert latest.assessment_id == "a-second"
    assert ResearchCaptureArchive.for_research(path).query_hypotheses()[0][
        "latest_assessment"
    ].revision == 2

    with pytest.raises(ValueError, match="expected 3"):
        second.record_assessment(
            EvidenceAssessment(
                assessment_id="bad-revision",
                capture_id="shared",
                hypothesis_id="hypothesis-shared",
                decision=AssessmentDecision.NEEDS_REVIEW,
                reasons=("Non-monotonic",),
                assessed_by="reviewer",
                assessed_at=NOW,
                revision=2,
            )
        )


def test_missing_references_are_retained_and_explicitly_annotated() -> None:
    capture = capture_raw_research(
        capture_id="missing",
        query=query(),
        sources=(),
        citations=(
            CapturedCitation(
                citation_id="orphan-citation",
                source_id="missing-source",
                locator="unknown",
                quote="Unverifiable quoted words",
                retention_note="Source metadata absent.",
            ),
        ),
        hypotheses=(
            RawHypothesis(
                hypothesis_id="orphan-hypothesis",
                proposition="Retain this gap.",
                origin=HypothesisOrigin.HUMAN_NOTE,
                citation_ids=("orphan-citation", "missing-citation"),
                contradicted_by=("missing-hypothesis",),
            ),
        ),
        captured_at=NOW,
    )
    assert capture.citations[0].quote is None
    assert CaptureAnnotation.MISSING_REFERENCE in capture.hypotheses[0].annotations
    assert CaptureAnnotation.LICENSE_LIMITED not in capture.hypotheses[0].annotations


def promotion_fixture():
    content = "A reviewed source associates this condition with a delay."
    quote = "associates this condition with a delay"
    manifest = SourceManifest(
        source_id="eligible-source",
        title="Eligible source",
        locator_kind=LocatorKind.URI,
        locator="https://trusted.example/text/1",
        tier=SourceTier.SCHOLARLY,
        source_kind=SourceKind.HUMAN_AUTHORED,
        author_or_organisation="Scholar",
        rights_or_license="accepted-research",
        research_use_allowed=True,
        accessed_at=NOW,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        max_quote_words=8,
    )
    hypothesis = RawHypothesis(
        hypothesis_id="promotable-hypothesis",
        proposition="The source describes a delay association.",
        origin=HypothesisOrigin.SOURCE_EXTRACTION,
        citation_ids=("eligible-citation",),
    )
    capture = capture_raw_research(
        capture_id="promotable-capture",
        query=query(),
        sources=(manifest,),
        citations=(
            CapturedCitation(
                citation_id="eligible-citation",
                source_id=manifest.source_id,
                locator="sentence 1",
                quote=quote,
                retention_note="Retention permitted by manifest.",
                license_status=CitationLicenseStatus.ALLOWED,
            ),
        ),
        hypotheses=(hypothesis,),
        captured_at=NOW,
    )
    allowlist = SourceAllowlist(
        uri_prefixes=("https://trusted.example/text/",),
        accepted_rights_or_licenses=("accepted-research",),
    )
    snapshot = seal_snapshot(
        snapshot_id="promotion-snapshot",
        query=query(),
        documents=(ResearchDocument(manifest=manifest, content=content),),
        citations=(
            Citation(
                citation_id="eligible-citation",
                source_id=manifest.source_id,
                locator="sentence 1",
                quote=quote,
            ),
        ),
        claims=(
            ExtractedClaim(
                claim_id=hypothesis.hypothesis_id,
                proposition=hypothesis.proposition,
                citation_ids=hypothesis.citation_ids,
            ),
        ),
        created_at=NOW,
        allowlist=allowlist,
    )
    assessment = EvidenceAssessment(
        assessment_id="promotion-assessment",
        capture_id=capture.capture_id,
        hypothesis_id=hypothesis.hypothesis_id,
        decision=AssessmentDecision.PROMOTABLE,
        reasons=("Verified against immutable source",),
        assessed_by="reviewer",
        assessed_at=NOW,
    )
    return capture, assessment, allowlist, snapshot


def test_promotion_requires_accepted_license_and_matching_immutable_snapshot() -> None:
    capture, assessment, allowlist, snapshot = promotion_fixture()
    candidate = stage_for_promotion(capture, assessment, allowlist, snapshot)
    assert candidate.hypothesis_id == "promotable-hypothesis"

    wrong_license = SourceAllowlist(
        uri_prefixes=("https://trusted.example/text/",),
        accepted_rights_or_licenses=("different-license",),
    )
    with pytest.raises(ValueError, match="unapproved license"):
        stage_for_promotion(capture, assessment, wrong_license, snapshot)

    fabricated = capture_raw_research(
        capture_id=capture.capture_id,
        query=capture.query,
        sources=capture.sources,
        citations=(
            capture.citations[0].model_copy(update={"quote": "fabricated but short phrase"}),
        ),
        hypotheses=capture.hypotheses,
        captured_at=NOW,
    )
    with pytest.raises(ValueError, match="matching checksummed snapshot"):
        stage_for_promotion(fabricated, assessment, allowlist, snapshot)

    alternate_source = capture.sources[0].model_copy(
        update={
            "source_id": "identical-content-substitute",
            "locator": "https://trusted.example/text/substitute",
        }
    )
    substituted = capture_raw_research(
        capture_id=capture.capture_id,
        query=capture.query,
        sources=(alternate_source,),
        citations=(
            capture.citations[0].model_copy(
                update={"source_id": alternate_source.source_id}
            ),
        ),
        hypotheses=capture.hypotheses,
        captured_at=NOW,
    )
    with pytest.raises(ValueError, match="matching checksummed snapshot"):
        stage_for_promotion(substituted, assessment, allowlist, snapshot)

    locator_substitution = capture_raw_research(
        capture_id=capture.capture_id,
        query=capture.query,
        sources=capture.sources,
        citations=(
            capture.citations[0].model_copy(update={"locator": "different paragraph"}),
        ),
        hypotheses=capture.hypotheses,
        captured_at=NOW,
    )
    with pytest.raises(ValueError, match="matching checksummed snapshot"):
        stage_for_promotion(locator_substitution, assessment, allowlist, snapshot)


def test_over_limit_quote_is_omitted_and_cannot_be_promoted() -> None:
    capture, assessment, allowlist, snapshot = promotion_fixture()
    restricted_manifest = capture.sources[0].model_copy(update={"max_quote_words": 2})
    restricted_capture = capture_raw_research(
        capture_id=capture.capture_id,
        query=capture.query,
        sources=(restricted_manifest,),
        citations=capture.citations,
        hypotheses=capture.hypotheses,
        captured_at=NOW,
    )
    assert restricted_capture.citations[0].quote is None
    with pytest.raises(ValueError, match="retained source citation"):
        stage_for_promotion(restricted_capture, assessment, allowlist, snapshot)
