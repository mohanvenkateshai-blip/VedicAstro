"""First additive canonical evidence-pipeline slice."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .adapters import (
    AdaptedRulePack,
    AdapterContext,
    LegacyRulePackAdapter,
    adapt_rule_pack_output,
)


@dataclass(frozen=True, slots=True)
class EvidencePipeline:
    """Run a named adapter while leaving legacy engines and outputs untouched."""

    adapter: LegacyRulePackAdapter

    def run(self, raw_output: Mapping[str, Any], context: AdapterContext) -> AdaptedRulePack:
        return adapt_rule_pack_output(raw_output, self.adapter, context)
