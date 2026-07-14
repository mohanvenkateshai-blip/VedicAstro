"""Deterministic capture and replay for canonical evidence adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .adapters import AdaptedRulePack, AdapterContext, LegacyRulePackAdapter
from .canonical import stable_hash
from .pipeline import EvidencePipeline


@dataclass(frozen=True, slots=True)
class ReplayRecord:
    raw_output: Mapping[str, Any]
    adapter: LegacyRulePackAdapter
    context: AdapterContext
    expected_artifact_hash: str

    @classmethod
    def capture(
        cls,
        raw_output: Mapping[str, Any],
        adapter: LegacyRulePackAdapter,
        context: AdapterContext,
    ) -> ReplayRecord:
        result = EvidencePipeline(adapter).run(raw_output, context)
        return cls(raw_output, adapter, context, artifact_hash(result))

    def replay(self) -> AdaptedRulePack:
        result = EvidencePipeline(self.adapter).run(self.raw_output, self.context)
        actual = artifact_hash(result)
        if actual != self.expected_artifact_hash:
            raise RuntimeError(
                f"deterministic replay mismatch: expected {self.expected_artifact_hash}, got {actual}"
            )
        return result


def artifact_hash(result: AdaptedRulePack) -> str:
    """Hash only normalized artifacts, not Python object identity."""

    return stable_hash(
        {
            "evidence": result.evidence,
            "candidate": result.candidate,
            "conflicts": result.conflicts,
            "canonical_input": result.canonical_input,
        }
    )
