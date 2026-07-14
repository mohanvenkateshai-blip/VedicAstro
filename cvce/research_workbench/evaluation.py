"""Deterministic quality metrics for draft research output."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Citation, Contradiction, ExtractedClaim


@dataclass(frozen=True, slots=True)
class ResearchQualityMetrics:
    citation_coverage: float
    unsupported_claim_rate: float
    contradiction_coverage: float


def evaluate_research_quality(
    claims: tuple[ExtractedClaim, ...],
    citations: tuple[Citation, ...],
    contradictions: tuple[Contradiction, ...],
) -> ResearchQualityMetrics:
    citation_ids = {item.citation_id for item in citations}
    supported_ids = {
        claim.claim_id
        for claim in claims
        if claim.citation_ids and all(item in citation_ids for item in claim.citation_ids)
    }
    total = len(claims)
    coverage = len(supported_ids) / total if total else 1.0
    contradiction_claim_ids = {item for conflict in contradictions for item in conflict.claim_ids}
    eligible = {claim.claim_id for claim in claims if claim.claim_id in supported_ids}
    contradiction_coverage = (
        len(eligible & contradiction_claim_ids) / len(eligible) if eligible else 1.0
    )
    return ResearchQualityMetrics(
        citation_coverage=coverage,
        unsupported_claim_rate=1.0 - coverage,
        contradiction_coverage=contradiction_coverage,
    )
