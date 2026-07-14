"""Event-specific evidence tensors and non-destructive research synthesis."""

from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType
from typing import Literal, Protocol

from pydantic import Field, JsonValue, model_validator

from .contracts import RawPrediction, ResearchModel
from .experiment_matrix import (
    ExecutionStatus,
    ExperimentExecutionBinding,
    ExperimentFailureArtifact,
)
from .identity import stable_hash
from .immutable import freeze_json, snapshot_model


class EvidenceDirection(StrEnum):
    SUPPORTING = "supporting"
    OPPOSING = "opposing"
    NEUTRAL = "neutral"


class EventEvidenceCell(ResearchModel):
    cell_id: str = Field(min_length=1)
    event_code: str = Field(min_length=1)
    technique_code: str = Field(min_length=1)
    profile_hash: str = Field(min_length=1)
    arm_id: str = Field(min_length=1)
    arm_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_id: str = Field(min_length=1)
    run_id: str | None = Field(default=None, min_length=1)
    direction: EvidenceDirection
    configuration: JsonValue
    raw_prediction: RawPrediction | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    technical_failure: ExperimentFailureArtifact | None = None
    execution_binding: ExperimentExecutionBinding

    @model_validator(mode="after")
    def bind_event(self) -> EventEvidenceCell:
        if self.raw_prediction is None and self.technical_failure is None:
            raise ValueError("evidence cell requires a raw prediction or technical failure")
        if self.raw_prediction is not None and self.technical_failure is not None:
            raise ValueError("evidence cell cannot be both executed and failed")
        if self.raw_prediction is not None and self.raw_prediction.event_code != self.event_code:
            raise ValueError("raw prediction event must match its evidence cell")
        if self.raw_prediction is not None and self.run_id is None:
            raise ValueError("executed evidence requires its technique run ID")
        binding = self.execution_binding
        if (
            binding.execution_id != self.execution_id
            or binding.arm_id != self.arm_id
            or binding.arm_hash != self.arm_hash
        ):
            raise ValueError("execution binding does not match evidence identity")
        snapshot = binding.configuration_snapshot
        if snapshot.technique_code != self.technique_code or snapshot.profile_hash != self.profile_hash:
            raise ValueError("execution binding technique/profile does not match evidence")
        if stable_hash(self.configuration) != binding.configuration_snapshot_hash:
            raise ValueError("execution binding configuration does not match evidence")
        if self.raw_prediction is not None:
            if binding.status is not ExecutionStatus.EXECUTED:
                raise ValueError("failed execution cannot be retyped as directional evidence")
            if self.run_id != binding.technique_run_id:
                raise ValueError("evidence run ID does not match its execution binding")
            declared = next(
                (
                    item
                    for item in binding.prediction_bindings
                    if item.prediction_id == self.raw_prediction.prediction_id
                ),
                None,
            )
            if declared is None:
                raise ValueError("raw prediction is not declared by its execution binding")
            if declared.prediction_hash != stable_hash(self.raw_prediction):
                raise ValueError("raw prediction content does not match its canonical binding")
            if declared.event_code != self.event_code:
                raise ValueError("prediction binding event does not match evidence cell")
            if declared.evidence_direction != self.direction.value:
                raise ValueError("evidence direction does not match its normalization binding")
        if self.technical_failure is not None:
            if self.run_id is not None:
                raise ValueError("technical failure evidence cannot invent a technique run ID")
            if self.direction is not EvidenceDirection.NEUTRAL:
                raise ValueError("technical failure evidence must be directionally neutral")
            if self.technical_failure.arm_id != self.arm_id:
                raise ValueError("technical failure arm does not match evidence cell")
            if self.technical_failure.arm_hash != self.arm_hash:
                raise ValueError("technical failure arm hash does not match evidence cell")
            if self.technical_failure.execution_id != self.execution_id:
                raise ValueError("technical failure execution does not match evidence cell")
            if binding.status is not ExecutionStatus.TECHNICAL_FAILURE:
                raise ValueError("executed binding cannot be represented as a technical failure")
            if self.technical_failure.configuration_snapshot != snapshot:
                raise ValueError("technical failure snapshot does not match execution binding")
            if snapshot.technique_code != self.technique_code:
                raise ValueError("technical failure technique does not match evidence cell")
            if snapshot.profile_hash != self.profile_hash:
                raise ValueError("technical failure profile does not match evidence cell")
            if (
                stable_hash(self.configuration)
                != self.technical_failure.configuration_snapshot_hash
            ):
                raise ValueError("technical failure configuration does not match evidence cell")
        object.__setattr__(self, "configuration", freeze_json(self.configuration))
        object.__setattr__(self, "metadata", freeze_json(self.metadata))
        if self.technical_failure is not None:
            object.__setattr__(self, "technical_failure", snapshot_model(self.technical_failure))
        if self.raw_prediction is not None:
            object.__setattr__(self, "raw_prediction", snapshot_model(self.raw_prediction))
        object.__setattr__(self, "execution_binding", snapshot_model(self.execution_binding))
        return self

    @property
    def evidence_identity_hash(self) -> str:
        """Canonical identity independent of the caller-selected cell label."""

        native_identity = (
            {
                "prediction_id": self.raw_prediction.prediction_id,
                "prediction_hash": stable_hash(self.raw_prediction),
            }
            if self.raw_prediction is not None
            else {"failure_artifact_hash": self.technical_failure.artifact_hash}
        )
        return stable_hash(
            {
                "event_code": self.event_code,
                "arm_hash": self.arm_hash,
                "configuration_hash": self.execution_binding.configuration_snapshot_hash,
                **native_identity,
            }
        )


def _reject_duplicate_evidence(cells: tuple[EventEvidenceCell, ...]) -> None:
    identities = [item.evidence_identity_hash for item in cells]
    if len(identities) != len(set(identities)):
        raise ValueError("canonical evidence identities must be unique")


def _authoritative_ledger_hashes(cells: tuple[EventEvidenceCell, ...]) -> tuple[str, ...]:
    """Return the exact non-overlapping ledger set that authorizes these cells.

    Multiple cells may refer to one ledger record when one execution declared
    multiple predictions. Distinct ledgers, however, may not claim the same
    planned arm, execution, technique run, or prediction identity.
    """

    ledgers = {}
    for cell in cells:
        binding = cell.execution_binding
        existing = ledgers.get(binding.ledger_hash)
        if existing is not None and existing != binding.ledger:
            raise ValueError("one ledger hash cannot identify different ledger snapshots")
        ledgers[binding.ledger_hash] = binding.ledger

    ownership: dict[str, dict[str, str]] = {
        "planned arm": {},
        "execution": {},
        "technique run": {},
        "prediction": {},
        "prediction content": {},
    }
    for ledger_hash, ledger in ledgers.items():
        identities = {
            "planned arm": (arm.arm_hash for arm in ledger.planned_arms),
            "execution": (record.execution_id for record in ledger.records),
            "technique run": (
                record.technique_run_id
                for record in ledger.records
                if record.technique_run_id is not None
            ),
            "prediction": (
                prediction_id
                for record in ledger.records
                for prediction_id in record.prediction_ids
            ),
            "prediction content": (
                binding.prediction_hash
                for record in ledger.records
                for binding in record.prediction_bindings
            ),
        }
        for identity_kind, values in identities.items():
            for value in values:
                prior = ownership[identity_kind].get(value)
                if prior is not None and prior != ledger_hash:
                    raise ValueError(
                        f"authoritative ledger set has overlapping {identity_kind} identity"
                    )
                ownership[identity_kind][value] = ledger_hash
    return tuple(sorted(ledgers))


class EventEvidenceSlice(ResearchModel):
    event_code: str = Field(min_length=1)
    cells: tuple[EventEvidenceCell, ...]
    authoritative_ledger_hashes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_slice(self) -> EventEvidenceSlice:
        if not self.cells:
            raise ValueError("event evidence slice cannot be empty")
        if any(item.event_code != self.event_code for item in self.cells):
            raise ValueError("event evidence slice cannot mix event codes")
        cell_ids = [item.cell_id for item in self.cells]
        if len(cell_ids) != len(set(cell_ids)):
            raise ValueError("event evidence slice cell IDs must be unique")
        _reject_duplicate_evidence(self.cells)
        expected_ledgers = _authoritative_ledger_hashes(self.cells)
        if self.authoritative_ledger_hashes and self.authoritative_ledger_hashes != expected_ledgers:
            raise ValueError("evidence slice authoritative ledger set does not match its cells")
        object.__setattr__(self, "authoritative_ledger_hashes", expected_ledgers)
        object.__setattr__(
            self,
            "cells",
            tuple(
                sorted((snapshot_model(item) for item in self.cells), key=lambda item: item.cell_id)
            ),
        )
        return self

    @property
    def evidence_hash(self) -> str:
        return stable_hash(self)


class EventEvidenceTensor(ResearchModel):
    tensor_id: str = Field(min_length=1)
    cells: tuple[EventEvidenceCell, ...]
    authoritative_ledger_hashes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_tensor(self) -> EventEvidenceTensor:
        cell_ids = [item.cell_id for item in self.cells]
        if len(cell_ids) != len(set(cell_ids)):
            raise ValueError("evidence cell IDs must be unique")
        _reject_duplicate_evidence(self.cells)
        expected_ledgers = _authoritative_ledger_hashes(self.cells)
        if self.authoritative_ledger_hashes and self.authoritative_ledger_hashes != expected_ledgers:
            raise ValueError("evidence tensor authoritative ledger set does not match its cells")
        object.__setattr__(self, "authoritative_ledger_hashes", expected_ledgers)
        object.__setattr__(
            self,
            "cells",
            tuple(
                sorted(
                    (snapshot_model(item) for item in self.cells),
                    key=lambda item: (item.event_code, item.cell_id),
                )
            ),
        )
        return self

    def for_event(self, event_code: str) -> EventEvidenceSlice:
        return EventEvidenceSlice(
            event_code=event_code,
            cells=tuple(item for item in self.cells if item.event_code == event_code),
        )


class StrategyOutcome(ResearchModel):
    derived_direction: EvidenceDirection
    native_result: JsonValue = Field(default_factory=dict)

    @model_validator(mode="after")
    def freeze_result(self) -> StrategyOutcome:
        object.__setattr__(self, "native_result", freeze_json(self.native_result))
        return self


class ValidatedStrategyOutcome(ResearchModel):
    """Factory-issued strategy result bound to one immutable evidence snapshot."""

    artifact_type: Literal["validated_strategy_outcome"] = "validated_strategy_outcome"
    strategy_code: str = Field(min_length=1)
    strategy_version: str = Field(min_length=1)
    derived_direction: EvidenceDirection
    native_result: JsonValue
    evidence_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    proof_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_proof(self) -> ValidatedStrategyOutcome:
        object.__setattr__(self, "native_result", freeze_json(self.native_result))
        expected = _validated_outcome_hash(
            strategy_code=self.strategy_code,
            strategy_version=self.strategy_version,
            derived_direction=self.derived_direction,
            native_result=self.native_result,
            evidence_hash=self.evidence_hash,
        )
        if self.proof_hash != expected:
            raise ValueError("validated strategy outcome proof does not match its typed payload")
        return self


class EventCombinationStrategy(Protocol):
    strategy_code: str
    strategy_version: str

    def combine(self, evidence: EventEvidenceSlice) -> StrategyOutcome: ...


class UnanimityCombinationStrategy:
    """Event-local unanimity; disagreement stays neutral without score summation."""

    strategy_code = "event_unanimity"
    strategy_version = "1.0.0"

    def combine(self, evidence: EventEvidenceSlice) -> StrategyOutcome:
        executed = tuple(item for item in evidence.cells if item.raw_prediction is not None)
        directions = {item.direction for item in executed}
        derived = next(iter(directions)) if len(directions) == 1 else EvidenceDirection.NEUTRAL
        return StrategyOutcome(
            derived_direction=derived,
            native_result={
                "cell_directions": [item.direction.value for item in executed],
                "excluded_failure_cell_ids": [
                    item.cell_id for item in evidence.cells if item.technical_failure is not None
                ],
                "rule": "unanimous_event_direction_else_neutral",
            },
        )


class EventSynthesisResult(ResearchModel):
    event_code: str
    strategy_code: str
    strategy_version: str
    derived_direction: EvidenceDirection
    strategy_native_result: JsonValue
    validated_outcome: ValidatedStrategyOutcome
    evidence: EventEvidenceSlice
    evidence_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_binding_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def retain_raw_evidence(self) -> EventSynthesisResult:
        object.__setattr__(self, "strategy_native_result", freeze_json(self.strategy_native_result))
        object.__setattr__(self, "validated_outcome", snapshot_model(self.validated_outcome))
        object.__setattr__(self, "evidence", snapshot_model(self.evidence))
        if self.event_code != self.evidence.event_code:
            raise ValueError("synthesis result must remain event-specific")
        if self.evidence_hash != self.evidence.evidence_hash:
            raise ValueError("synthesis evidence hash does not match retained raw evidence")
        if (
            self.strategy_code != self.validated_outcome.strategy_code
            or self.strategy_version != self.validated_outcome.strategy_version
            or self.derived_direction is not self.validated_outcome.derived_direction
            or self.strategy_native_result != self.validated_outcome.native_result
            or self.evidence_hash != self.validated_outcome.evidence_hash
        ):
            raise ValueError(
                "synthesis fields must equal the factory-validated strategy outcome"
            )
        expected_outcome_binding = _outcome_binding_hash(
            event_code=self.event_code,
            strategy_code=self.strategy_code,
            strategy_version=self.strategy_version,
            derived_direction=self.derived_direction,
            strategy_native_result=self.strategy_native_result,
            evidence_hash=self.evidence_hash,
        )
        if self.outcome_binding_hash != expected_outcome_binding:
            raise ValueError("synthesis outcome is not bound to its strategy result and evidence")
        if (
            not any(item.raw_prediction is not None for item in self.evidence.cells)
            and self.derived_direction is not EvidenceDirection.NEUTRAL
        ):
            raise ValueError("failure-only evidence cannot produce a directional synthesis")
        replay_direction, replay_native_result = _replay_registered_strategy(
            self.evidence,
            strategy_code=self.strategy_code,
            strategy_version=self.strategy_version,
        )
        if (
            self.derived_direction is not replay_direction
            or self.strategy_native_result != replay_native_result
        ):
            raise ValueError(
                "synthesis outcome does not match deterministic registered-strategy replay"
            )
        return self


def _validated_outcome_hash(
    *,
    strategy_code: str,
    strategy_version: str,
    derived_direction: EvidenceDirection,
    native_result: JsonValue,
    evidence_hash: str,
) -> str:
    return stable_hash(
        {
            "artifact_type": "validated_strategy_outcome",
            "strategy_code": strategy_code,
            "strategy_version": strategy_version,
            "derived_direction": derived_direction.value,
            "native_result": native_result,
            "evidence_hash": evidence_hash,
        }
    )


def _issue_validated_outcome(
    *,
    strategy_code: str,
    strategy_version: str,
    derived_direction: EvidenceDirection,
    native_result: JsonValue,
    evidence_hash: str,
) -> ValidatedStrategyOutcome:
    """Issue the sole typed outcome consumed by ``EventSynthesisResult``."""

    return ValidatedStrategyOutcome(
        strategy_code=strategy_code,
        strategy_version=strategy_version,
        derived_direction=derived_direction,
        native_result=native_result,
        evidence_hash=evidence_hash,
        proof_hash=_validated_outcome_hash(
            strategy_code=strategy_code,
            strategy_version=strategy_version,
            derived_direction=derived_direction,
            native_result=native_result,
            evidence_hash=evidence_hash,
        ),
    )


def _outcome_binding_hash(
    *,
    event_code: str,
    strategy_code: str,
    strategy_version: str,
    derived_direction: EvidenceDirection,
    strategy_native_result: JsonValue,
    evidence_hash: str,
) -> str:
    return stable_hash(
        {
            "event_code": event_code,
            "strategy_code": strategy_code,
            "strategy_version": strategy_version,
            "derived_direction": derived_direction.value,
            "strategy_native_result": strategy_native_result,
            "evidence_hash": evidence_hash,
        }
    )


_REGISTERED_STRATEGIES: MappingProxyType[
    tuple[str, str], type[UnanimityCombinationStrategy]
] = MappingProxyType({
    (
        UnanimityCombinationStrategy.strategy_code,
        UnanimityCombinationStrategy.strategy_version,
    ): UnanimityCombinationStrategy,
})


def _registered_strategy(
    strategy_code: str, strategy_version: str
) -> EventCombinationStrategy:
    strategy_type = _REGISTERED_STRATEGIES.get((strategy_code, strategy_version))
    if strategy_type is None:
        raise ValueError("synthesis strategy/version is not registered for deterministic replay")
    return strategy_type()


def _derive_synthesis_payload(
    evidence: EventEvidenceSlice,
    strategy: EventCombinationStrategy,
) -> tuple[EvidenceDirection, JsonValue]:
    directional_cells = tuple(item for item in evidence.cells if item.raw_prediction is not None)
    if directional_cells:
        directional_evidence = EventEvidenceSlice(
            event_code=evidence.event_code,
            cells=directional_cells,
        )
        outcome = snapshot_model(strategy.combine(directional_evidence))
    else:
        outcome = StrategyOutcome(
            derived_direction=EvidenceDirection.NEUTRAL,
            native_result={"rule": "no_executed_directional_evidence"},
        )
    native_result = {
        "strategy_result": outcome.native_result,
        "directional_cell_ids": [item.cell_id for item in directional_cells],
        "technical_failures": [
            item.technical_failure.model_dump(mode="json")
            for item in evidence.cells
            if item.technical_failure is not None
        ],
    }
    return outcome.derived_direction, freeze_json(native_result)


def _replay_registered_strategy(
    evidence: EventEvidenceSlice,
    *,
    strategy_code: str,
    strategy_version: str,
) -> tuple[EvidenceDirection, JsonValue]:
    return _derive_synthesis_payload(
        evidence,
        _registered_strategy(strategy_code, strategy_version),
    )


def synthesize_event(
    evidence: EventEvidenceSlice,
    strategy: EventCombinationStrategy,
) -> EventSynthesisResult:
    owned_evidence = snapshot_model(evidence)
    canonical_strategy = _registered_strategy(strategy.strategy_code, strategy.strategy_version)
    derived_direction, native_result = _derive_synthesis_payload(
        owned_evidence, canonical_strategy
    )
    validated_outcome = _issue_validated_outcome(
        strategy_code=strategy.strategy_code,
        strategy_version=strategy.strategy_version,
        derived_direction=derived_direction,
        native_result=native_result,
        evidence_hash=owned_evidence.evidence_hash,
    )
    outcome_binding_hash = _outcome_binding_hash(
        event_code=owned_evidence.event_code,
        strategy_code=strategy.strategy_code,
        strategy_version=strategy.strategy_version,
        derived_direction=derived_direction,
        strategy_native_result=native_result,
        evidence_hash=owned_evidence.evidence_hash,
    )
    return EventSynthesisResult(
        event_code=owned_evidence.event_code,
        strategy_code=strategy.strategy_code,
        strategy_version=strategy.strategy_version,
        derived_direction=derived_direction,
        strategy_native_result=native_result,
        validated_outcome=validated_outcome,
        evidence=owned_evidence,
        evidence_hash=owned_evidence.evidence_hash,
        outcome_binding_hash=outcome_binding_hash,
    )
