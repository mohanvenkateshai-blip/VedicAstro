"""Deterministic, network-free reference implementations."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Contradiction, ExtractedClaim, ResearchDocument, ResearchQuery, SourceManifest


@dataclass(frozen=True, slots=True)
class LocalManifestRetriever:
    documents_by_source_id: dict[str, ResearchDocument]

    def retrieve(
        self, query: ResearchQuery, manifests: tuple[SourceManifest, ...]
    ) -> tuple[ResearchDocument, ...]:
        requested = set(query.requested_source_ids)
        selected = (item for item in manifests if not requested or item.source_id in requested)
        return tuple(self.documents_by_source_id[item.source_id] for item in selected)


@dataclass(frozen=True, slots=True)
class DeterministicDraft:
    claims: tuple[ExtractedClaim, ...]
    contradictions: tuple[Contradiction, ...] = ()


@dataclass(frozen=True, slots=True)
class DeterministicResearchProvider:
    """Test/reference provider returning a pre-reviewed draft without I/O."""

    draft: DeterministicDraft

    def analyse(
        self, query: ResearchQuery, documents: tuple[ResearchDocument, ...]
    ) -> DeterministicDraft:
        del query, documents
        return self.draft
