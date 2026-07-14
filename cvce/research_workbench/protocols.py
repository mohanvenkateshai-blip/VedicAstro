"""Ports for optional future research-framework adapters."""

from __future__ import annotations

from typing import Protocol

from .models import Contradiction, ExtractedClaim, ResearchDocument, ResearchQuery, SourceManifest


class ResearchRetriever(Protocol):
    """Retrieve only manifests/documents requested by the orchestrator."""

    def retrieve(
        self, query: ResearchQuery, manifests: tuple[SourceManifest, ...]
    ) -> tuple[ResearchDocument, ...]: ...


class ResearchDraft(Protocol):
    @property
    def claims(self) -> tuple[ExtractedClaim, ...]: ...

    @property
    def contradictions(self) -> tuple[Contradiction, ...]: ...


class ResearchProvider(Protocol):
    """Analysis port suitable for future STORM/GPT Researcher/ODR adapters."""

    def analyse(
        self, query: ResearchQuery, documents: tuple[ResearchDocument, ...]
    ) -> ResearchDraft: ...
