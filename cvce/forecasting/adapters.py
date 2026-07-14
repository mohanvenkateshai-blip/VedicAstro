"""Strict, additive adapters from legacy structured rule-pack outputs.

The adapter deliberately requires an explicit field map. It does not guess that
legacy labels or scores are probabilities, event types, or evidence direction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .canonical import canonical_value, stable_id
from .contracts import (
    CalculationProvenance,
    EventCandidate,
    EvidenceDirection,
    ForecastPolarity,
    RuleEvidence,
    TimingWindow,
    UncertaintyAssessment,
)
from .research import NativeScore, tolerant_raw_value
from .taxonomy import EventCode


class LegacyAdapterError(ValueError):
    """Raised when a configured legacy output cannot be normalized safely."""


@dataclass(frozen=True, slots=True)
class RulePackDescriptor:
    rule_pack_id: str
    version: str

    def __post_init__(self) -> None:
        if not self.rule_pack_id.strip() or not self.version.strip():
            raise ValueError("rule_pack_id and version are required")


@dataclass(frozen=True, slots=True)
class EvidenceFieldMap:
    items_path: tuple[str | int, ...]
    rule_id: str
    signal_name: str
    direction: str
    traditional_strength_index: str
    source_confidence: str
    rationale: str
    source_ids: str | None = None
    citation_ids: str | None = None
    direction_values: Mapping[str, EvidenceDirection] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CandidateFieldMap:
    traditional_strength_index_path: tuple[str | int, ...]
    polarity_path: tuple[str | int, ...]
    polarity_values: Mapping[str, ForecastPolarity]


@dataclass(frozen=True, slots=True)
class LegacyRulePackAdapter:
    descriptor: RulePackDescriptor
    event_code: EventCode
    evidence: EvidenceFieldMap
    candidate: CandidateFieldMap


@dataclass(frozen=True, slots=True)
class AdapterContext:
    engine_version: str
    data_cutoff_at: datetime
    calculated_at: datetime
    timing: TimingWindow
    uncertainty: UncertaintyAssessment
    prerequisites: tuple[str, ...] = ()
    alternate_manifestations: tuple[str, ...] = ()
    disconfirmers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DirectionalConflict:
    """Exact evidence sets on both sides; no synthetic pairwise conflicts."""

    event_code: EventCode
    supporting_evidence_ids: tuple[str, ...]
    opposing_evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AdaptedRulePack:
    evidence: tuple[RuleEvidence, ...]
    candidate: EventCandidate
    conflicts: tuple[DirectionalConflict, ...]
    canonical_input: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ResearchEvidenceRecord:
    """Lossless view of one legacy item and its optional normalization."""

    item_index: int
    raw_item: Mapping[str, Any]
    raw_direction: Any
    native_score: NativeScore | None
    raw_prose: tuple[str, ...]
    normalized: RuleEvidence | None
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResearchCandidateRecord:
    raw_polarity: Any
    raw_score: Any
    raw_score_error: str | None
    native_score: NativeScore | None
    timing: TimingWindow
    normalized: EventCandidate | None
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResearchAdaptedRulePack:
    """Research capture that never discards an item because normalization failed."""

    evidence_records: tuple[ResearchEvidenceRecord, ...]
    candidate: ResearchCandidateRecord
    conflicts: tuple[DirectionalConflict, ...]
    canonical_input: Mapping[str, Any]
    product_view: AdaptedRulePack | None


def adapt_rule_pack_output_for_research(
    raw_output: Mapping[str, Any],
    adapter: LegacyRulePackAdapter,
    context: AdapterContext,
    *,
    native_score_scale: str = "legacy_native",
) -> ResearchAdaptedRulePack:
    """Capture every native item while normalizing each valid item independently.

    The existing :func:`adapt_rule_pack_output` remains the strict product path.
    This function is intentionally non-throwing for legacy shape/semantic errors;
    such errors are attached to the affected record with its canonical raw value.
    """

    canonical_input = tolerant_raw_value(
        {
            "raw_output": raw_output,
            "adapter": adapter,
            "engine_version": context.engine_version,
            "data_cutoff_at": context.data_cutoff_at,
            "timing": context.timing,
            "uncertainty": context.uncertainty,
            "prerequisites": context.prerequisites,
            "alternate_manifestations": context.alternate_manifestations,
            "disconfirmers": context.disconfirmers,
        }
    )
    calculation_hash = stable_id("calculation", canonical_input).removeprefix("calculation_")
    try:
        raw_items = _at_path(raw_output, adapter.evidence.items_path)
        if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
            raise LegacyAdapterError("evidence items path must resolve to a sequence")
        items = list(raw_items)
        collection_error: tuple[str, ...] = ()
    except Exception as exc:
        items = []
        collection_error = (str(exc),)

    records: list[ResearchEvidenceRecord] = []
    for index, item in enumerate(items):
        raw_item = tolerant_raw_value(item)
        if not isinstance(item, Mapping):
            records.append(
                ResearchEvidenceRecord(
                    index,
                    {"raw_value": raw_item},
                    None,
                    None,
                    (),
                    None,
                    (f"evidence item {index} must be a mapping",),
                )
            )
            continue
        try:
            records.append(
                _research_evidence_record(
                    item,
                    index=index,
                    adapter=adapter,
                    context=context,
                    calculation_hash=calculation_hash,
                    native_score_scale=native_score_scale,
                )
            )
        except Exception as exc:
            records.append(
                ResearchEvidenceRecord(
                    index,
                    raw_item,
                    None,
                    None,
                    (),
                    None,
                    (f"{type(exc).__module__}.{type(exc).__qualname__}: {exc}",),
                )
            )

    if collection_error:
        records.append(
            ResearchEvidenceRecord(-1, {}, None, None, (), None, collection_error)
        )

    normalized = tuple(record.normalized for record in records if record.normalized is not None)
    supporting = tuple(
        item.evidence_id for item in normalized if item.direction is EvidenceDirection.SUPPORTING
    )
    opposing = tuple(
        item.evidence_id for item in normalized if item.direction is EvidenceDirection.OPPOSING
    )
    conflicts = (
        (DirectionalConflict(adapter.event_code, supporting, opposing),)
        if supporting and opposing
        else ()
    )
    try:
        candidate = _research_candidate_record(
            raw_output,
            adapter=adapter,
            context=context,
            calculation_hash=calculation_hash,
            normalized_evidence=normalized,
            supporting=supporting,
            opposing=opposing,
            native_score_scale=native_score_scale,
        )
    except Exception as exc:
        candidate = ResearchCandidateRecord(
            None,
            tolerant_raw_value(raw_output),
            f"candidate capture failed: {type(exc).__module__}.{type(exc).__qualname__}: {exc}",
            None,
            context.timing,
            None,
            ("candidate normalization quarantined",),
        )
    try:
        product_view = adapt_rule_pack_output(raw_output, adapter, context)
    except Exception:
        product_view = None
    return ResearchAdaptedRulePack(
        tuple(records), candidate, conflicts, canonical_input, product_view
    )


def _research_evidence_record(
    item: Mapping[str, Any],
    *,
    index: int,
    adapter: LegacyRulePackAdapter,
    context: AdapterContext,
    calculation_hash: str,
    native_score_scale: str,
) -> ResearchEvidenceRecord:
    raw_direction = item.get(adapter.evidence.direction)
    raw_score = item.get(adapter.evidence.traditional_strength_index)
    native_score = _native_score(raw_score, native_score_scale)
    raw_prose = tuple(
        str(value)
        for key in (adapter.evidence.signal_name, adapter.evidence.rationale)
        if (value := item.get(key)) is not None
    )
    errors: list[str] = []
    normalized: RuleEvidence | None = None
    try:
        direction = adapter.evidence.direction_values[str(_required(item, adapter.evidence.direction))]
        source_ids = (
            _string_tuple(item.get(adapter.evidence.source_ids))
            if adapter.evidence.source_ids
            else ()
        )
        citation_ids = (
            _string_tuple(item.get(adapter.evidence.citation_ids))
            if adapter.evidence.citation_ids
            else ()
        )
        provenance = CalculationProvenance(
            calculation_hash=calculation_hash,
            engine_version=context.engine_version,
            rule_pack_versions={adapter.descriptor.rule_pack_id: adapter.descriptor.version},
            source_ids=source_ids,
            citation_ids=citation_ids,
            data_cutoff_at=context.data_cutoff_at,
            calculated_at=context.calculated_at,
        )
        identity = {
            "calculation_hash": calculation_hash,
            "rule_pack_id": adapter.descriptor.rule_pack_id,
            "rule_pack_version": adapter.descriptor.version,
            "event_code": adapter.event_code,
            "item_index": index,
            "item": item,
        }
        normalized = RuleEvidence(
            evidence_id=stable_id("evidence", identity),
            event_code=adapter.event_code,
            direction=direction,
            rule_id=str(_required(item, adapter.evidence.rule_id)),
            signal_name=str(_required(item, adapter.evidence.signal_name)),
            traditional_strength_index=float(
                _required(item, adapter.evidence.traditional_strength_index)
            ),
            source_confidence=float(_required(item, adapter.evidence.source_confidence)),
            rationale=str(_required(item, adapter.evidence.rationale)),
            provenance=provenance,
        )
    except KeyError:
        errors.append(f"unmapped evidence direction: {raw_direction!r}")
    except (LegacyAdapterError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return ResearchEvidenceRecord(
        index,
        tolerant_raw_value(item),
        tolerant_raw_value(raw_direction),
        native_score,
        raw_prose,
        normalized,
        tuple(errors),
    )


def _research_candidate_record(
    raw_output: Mapping[str, Any],
    *,
    adapter: LegacyRulePackAdapter,
    context: AdapterContext,
    calculation_hash: str,
    normalized_evidence: tuple[RuleEvidence, ...],
    supporting: tuple[str, ...],
    opposing: tuple[str, ...],
    native_score_scale: str,
) -> ResearchCandidateRecord:
    errors: list[str] = []
    try:
        raw_polarity = _at_path(raw_output, adapter.candidate.polarity_path)
    except Exception as exc:
        raw_polarity = None
        errors.append(str(exc))
    try:
        raw_score = _at_path(raw_output, adapter.candidate.traditional_strength_index_path)
    except Exception as exc:
        raw_score = None
        errors.append(str(exc))
    native_score = _native_score(raw_score, native_score_scale)
    raw_score_error = None
    if raw_score is not None and native_score is None:
        raw_score_error = "native score is non-numeric or non-finite"
    normalized_candidate: EventCandidate | None = None
    try:
        polarity = adapter.candidate.polarity_values[str(raw_polarity)]
        candidate_strength = float(raw_score)
        provenance = CalculationProvenance(
            calculation_hash=calculation_hash,
            engine_version=context.engine_version,
            rule_pack_versions={adapter.descriptor.rule_pack_id: adapter.descriptor.version},
            source_ids=tuple(
                sorted({value for item in normalized_evidence for value in item.provenance.source_ids})
            ),
            citation_ids=tuple(
                sorted(
                    {value for item in normalized_evidence for value in item.provenance.citation_ids}
                )
            ),
            data_cutoff_at=context.data_cutoff_at,
            calculated_at=context.calculated_at,
        )
        identity = {
            "calculation_hash": calculation_hash,
            "event_code": adapter.event_code,
            "timing": context.timing,
            "polarity": polarity,
            "traditional_strength_index": candidate_strength,
            "supporting_evidence_ids": supporting,
            "opposing_evidence_ids": opposing,
        }
        normalized_candidate = EventCandidate(
            candidate_id=stable_id("candidate", identity),
            event_code=adapter.event_code,
            timing=context.timing,
            polarity=polarity,
            traditional_strength_index=candidate_strength,
            supporting_evidence_ids=supporting,
            opposing_evidence_ids=opposing,
            prerequisites=context.prerequisites,
            alternate_manifestations=context.alternate_manifestations,
            disconfirmers=context.disconfirmers,
            uncertainty=context.uncertainty,
            provenance=provenance,
        )
    except KeyError:
        errors.append(f"unmapped candidate polarity: {raw_polarity!r}")
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    return ResearchCandidateRecord(
        tolerant_raw_value(raw_polarity),
        tolerant_raw_value(raw_score),
        raw_score_error,
        native_score,
        context.timing,
        normalized_candidate,
        tuple(errors),
    )


def _native_score(value: Any, scale: str) -> NativeScore | None:
    try:
        return NativeScore(value, scale)
    except (TypeError, ValueError):
        return None


def adapt_rule_pack_output(
    raw_output: Mapping[str, Any],
    adapter: LegacyRulePackAdapter,
    context: AdapterContext,
) -> AdaptedRulePack:
    """Normalize one configured legacy rule-pack result without changing it."""

    canonical_input = _canonical_input(raw_output, adapter, context)
    calculation_hash = stable_id("calculation", canonical_input).removeprefix("calculation_")
    items = _at_path(raw_output, adapter.evidence.items_path)
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise LegacyAdapterError("evidence items path must resolve to a sequence")

    normalized: list[RuleEvidence] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise LegacyAdapterError(f"evidence item {index} must be a mapping")
        source_ids = _string_tuple(item.get(adapter.evidence.source_ids)) if adapter.evidence.source_ids else ()
        citation_ids = (
            _string_tuple(item.get(adapter.evidence.citation_ids))
            if adapter.evidence.citation_ids
            else ()
        )
        provenance = CalculationProvenance(
            calculation_hash=calculation_hash,
            engine_version=context.engine_version,
            rule_pack_versions={
                adapter.descriptor.rule_pack_id: adapter.descriptor.version,
            },
            source_ids=source_ids,
            citation_ids=citation_ids,
            data_cutoff_at=context.data_cutoff_at,
            calculated_at=context.calculated_at,
        )
        direction_raw = str(_required(item, adapter.evidence.direction))
        try:
            direction = adapter.evidence.direction_values[direction_raw]
        except KeyError as exc:
            raise LegacyAdapterError(f"unmapped evidence direction: {direction_raw!r}") from exc

        identity = {
            "calculation_hash": calculation_hash,
            "rule_pack_id": adapter.descriptor.rule_pack_id,
            "rule_pack_version": adapter.descriptor.version,
            "event_code": adapter.event_code,
            "item_index": index,
            "item": item,
        }
        normalized.append(
            RuleEvidence(
                evidence_id=stable_id("evidence", identity),
                event_code=adapter.event_code,
                direction=direction,
                rule_id=str(_required(item, adapter.evidence.rule_id)),
                signal_name=str(_required(item, adapter.evidence.signal_name)),
                traditional_strength_index=float(
                    _required(item, adapter.evidence.traditional_strength_index)
                ),
                source_confidence=float(_required(item, adapter.evidence.source_confidence)),
                rationale=str(_required(item, adapter.evidence.rationale)),
                provenance=provenance,
            )
        )

    supporting = tuple(
        evidence.evidence_id
        for evidence in normalized
        if evidence.direction is EvidenceDirection.SUPPORTING
    )
    opposing = tuple(
        evidence.evidence_id
        for evidence in normalized
        if evidence.direction is EvidenceDirection.OPPOSING
    )
    polarity_raw = str(_at_path(raw_output, adapter.candidate.polarity_path))
    try:
        polarity = adapter.candidate.polarity_values[polarity_raw]
    except KeyError as exc:
        raise LegacyAdapterError(f"unmapped candidate polarity: {polarity_raw!r}") from exc
    candidate_strength = float(
        _at_path(raw_output, adapter.candidate.traditional_strength_index_path)
    )
    candidate_identity = {
        "calculation_hash": calculation_hash,
        "event_code": adapter.event_code,
        "timing": context.timing,
        "polarity": polarity,
        "traditional_strength_index": candidate_strength,
        "supporting_evidence_ids": supporting,
        "opposing_evidence_ids": opposing,
    }
    common_provenance = CalculationProvenance(
        calculation_hash=calculation_hash,
        engine_version=context.engine_version,
        rule_pack_versions={adapter.descriptor.rule_pack_id: adapter.descriptor.version},
        source_ids=tuple(sorted({item for ev in normalized for item in ev.provenance.source_ids})),
        citation_ids=tuple(
            sorted({item for ev in normalized for item in ev.provenance.citation_ids})
        ),
        data_cutoff_at=context.data_cutoff_at,
        calculated_at=context.calculated_at,
    )
    candidate = EventCandidate(
        candidate_id=stable_id("candidate", candidate_identity),
        event_code=adapter.event_code,
        timing=context.timing,
        polarity=polarity,
        traditional_strength_index=candidate_strength,
        supporting_evidence_ids=supporting,
        opposing_evidence_ids=opposing,
        prerequisites=context.prerequisites,
        alternate_manifestations=context.alternate_manifestations,
        disconfirmers=context.disconfirmers,
        uncertainty=context.uncertainty,
        provenance=common_provenance,
    )
    conflicts = (
        (
            DirectionalConflict(
                event_code=adapter.event_code,
                supporting_evidence_ids=supporting,
                opposing_evidence_ids=opposing,
            ),
        )
        if supporting and opposing
        else ()
    )
    return AdaptedRulePack(tuple(normalized), candidate, conflicts, canonical_input)


def _required(item: Mapping[str, Any], field_name: str) -> Any:
    try:
        value = item[field_name]
    except KeyError as exc:
        raise LegacyAdapterError(f"required legacy field is missing: {field_name}") from exc
    if value is None or value == "":
        raise LegacyAdapterError(f"required legacy field is empty: {field_name}")
    return value


def _at_path(value: Any, path: tuple[str | int, ...]) -> Any:
    current = value
    for part in path:
        try:
            current = current[part]
        except (KeyError, IndexError, TypeError) as exc:
            raise LegacyAdapterError(f"legacy path does not exist: {path!r}") from exc
    return current


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(str(item) for item in value)
    raise LegacyAdapterError("source and citation identifiers must be strings or sequences")


def _canonical_input(
    raw_output: Mapping[str, Any], adapter: LegacyRulePackAdapter, context: AdapterContext
) -> Mapping[str, Any]:
    return canonical_value(
        {
            "raw_output": raw_output,
            "adapter": adapter,
            "engine_version": context.engine_version,
            "data_cutoff_at": context.data_cutoff_at,
            "timing": context.timing,
            "uncertainty": context.uncertainty,
            "prerequisites": context.prerequisites,
            "alternate_manifestations": context.alternate_manifestations,
            "disconfirmers": context.disconfirmers,
        }
    )
