"""Lazy, bounded factorial expansion for technique/configuration experiments."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from enum import StrEnum
from math import prod
from typing import Literal

from pydantic import Field, JsonValue, computed_field, model_validator

from .constraint_types import ConstraintLayer, all_constraint_variants
from .contracts import ResearchModel
from .identity import stable_hash
from .immutable import freeze_json, snapshot_model
from .technique_registry import SchoolConfigurationProfile


class MatrixBoundExceeded(ValueError):
    pass


class TechniqueProfileSelection(ResearchModel):
    technique_code: str = Field(min_length=1)
    profile: SchoolConfigurationProfile

    @model_validator(mode="after")
    def validate_technique(self) -> TechniqueProfileSelection:
        if self.profile.technique_code != self.technique_code:
            raise ValueError("profile technique_code must match its matrix selection")
        object.__setattr__(self, "profile", snapshot_model(self.profile))
        return self


class ExperimentFactor(ResearchModel):
    factor_code: str = Field(min_length=1)
    values: tuple[JsonValue, ...]

    @model_validator(mode="after")
    def require_values(self) -> ExperimentFactor:
        if not self.values:
            raise ValueError("an experiment factor requires at least one value")
        hashes = [stable_hash(value) for value in self.values]
        if len(hashes) != len(set(hashes)):
            raise ValueError("factor values must be unique")
        object.__setattr__(
            self, "values", tuple(sorted((freeze_json(v) for v in self.values), key=stable_hash))
        )
        return self


class ExperimentArm(ResearchModel):
    arm_id: str = Field(min_length=1)
    arm_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    matrix_id: str
    matrix_version: str
    registry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    technique_code: str
    profile_id: str
    profile_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    constraints: tuple[ConstraintLayer, ...]
    ablated_constraints: tuple[ConstraintLayer, ...]
    factor_values: dict[str, JsonValue]

    @model_validator(mode="after")
    def seal_identity(self) -> ExperimentArm:
        object.__setattr__(self, "factor_values", freeze_json(self.factor_values))
        if len(self.constraints) != len(set(self.constraints)) or len(
            self.ablated_constraints
        ) != len(set(self.ablated_constraints)):
            raise ValueError("selected and ablated constraints cannot contain duplicates")
        if set(self.constraints) & set(self.ablated_constraints):
            raise ValueError("selected and ablated constraints cannot overlap")
        if set(self.constraints) | set(self.ablated_constraints) != set(ConstraintLayer):
            raise ValueError("selected and ablated constraints must cover every layer")
        identity = {
            "matrix_id": self.matrix_id,
            "matrix_version": self.matrix_version,
            "registry_hash": self.registry_hash,
            "technique_code": self.technique_code,
            "profile_hash": self.profile_hash,
            "constraints": [item.value for item in self.constraints],
            "factor_values": self.factor_values,
        }
        expected_hash = stable_hash(identity)
        if self.arm_hash != expected_hash or self.arm_id != f"arm_{expected_hash[:24]}":
            raise ValueError("arm identity/hash does not match its canonical contents")
        return self


class ExperimentMatrixPlan(ResearchModel):
    matrix_id: str = Field(min_length=1)
    matrix_version: str = Field(min_length=1)
    registry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    selections: tuple[TechniqueProfileSelection, ...]
    factors: tuple[ExperimentFactor, ...] = ()
    constraint_variants: tuple[tuple[ConstraintLayer, ...], ...]
    exhaustive_constraints: bool = False
    max_arms_per_expansion: int = Field(default=1000, gt=0)

    @model_validator(mode="after")
    def validate_plan(self) -> ExperimentMatrixPlan:
        if not self.selections:
            raise ValueError("matrix requires at least one technique/profile selection")
        if not self.constraint_variants:
            raise ValueError("matrix requires at least one constraint variant")
        codes = [factor.factor_code for factor in self.factors]
        if len(codes) != len(set(codes)):
            raise ValueError("factor_code must be unique within a matrix")
        selection_ids = [
            (item.technique_code, item.profile.profile_id, item.profile.profile_hash)
            for item in self.selections
        ]
        if len(selection_ids) != len(set(selection_ids)):
            raise ValueError("technique/profile selections must be unique")
        if len(self.constraint_variants) != len(set(self.constraint_variants)):
            raise ValueError("constraint variants must be unique")
        for variant in self.constraint_variants:
            if len(variant) != len(set(variant)):
                raise ValueError("a constraint variant cannot repeat a layer")
        subsets = [frozenset(variant) for variant in self.constraint_variants]
        if self.exhaustive_constraints and (
            len(subsets) != 16
            or len(set(subsets)) != 16
            or set(subsets) != {frozenset(item) for item in all_constraint_variants()}
        ):
            raise ValueError("exhaustive constraint mode requires exactly all 16 variants")
        object.__setattr__(
            self,
            "selections",
            tuple(
                sorted(
                    (
                        TechniqueProfileSelection.model_validate_json(item.model_dump_json())
                        for item in self.selections
                    ),
                    key=lambda item: (
                        item.technique_code,
                        item.profile.profile_id,
                        item.profile.profile_hash,
                    ),
                )
            ),
        )
        object.__setattr__(
            self,
            "factors",
            tuple(
                sorted(
                    (
                        ExperimentFactor.model_validate_json(item.model_dump_json())
                        for item in self.factors
                    ),
                    key=lambda item: item.factor_code,
                )
            ),
        )
        object.__setattr__(
            self,
            "constraint_variants",
            tuple(
                sorted(
                    self.constraint_variants,
                    key=lambda variant: tuple(layer.value for layer in variant),
                )
            ),
        )
        return self

    @property
    def plan_hash(self) -> str:
        return stable_hash(self)

    @computed_field
    @property
    def estimated_arm_count(self) -> int:
        factor_count = prod(len(factor.values) for factor in self.factors) if self.factors else 1
        return len(self.selections) * len(self.constraint_variants) * factor_count

    def iter_arms(self, *, offset: int = 0, limit: int | None = None) -> Iterator[ExperimentArm]:
        if offset < 0:
            raise ValueError("offset cannot be negative")
        requested = self.max_arms_per_expansion if limit is None else limit
        if requested < 0:
            raise ValueError("limit cannot be negative")
        if requested > self.max_arms_per_expansion:
            raise MatrixBoundExceeded(
                f"requested {requested} arms exceeds bound {self.max_arms_per_expansion}"
            )
        total = self.estimated_arm_count
        if offset > total:
            raise MatrixBoundExceeded(f"offset {offset} exceeds matrix size {total}")
        stop = min(total, offset + requested)
        axes = (
            self.selections,
            self.constraint_variants,
            *(factor.values for factor in self.factors),
        )
        radices = tuple(len(axis) for axis in axes)
        for arm_index in range(offset, stop):
            remainder = arm_index
            indices = [0] * len(axes)
            for position in range(len(axes) - 1, -1, -1):
                remainder, indices[position] = divmod(remainder, radices[position])
            row = tuple(axis[index] for axis, index in zip(axes, indices, strict=True))
            selection, constraints, *values = row
            factor_values = {
                factor.factor_code: value
                for factor, value in zip(self.factors, values, strict=True)
            }
            identity = {
                "matrix_id": self.matrix_id,
                "matrix_version": self.matrix_version,
                "registry_hash": self.registry_hash,
                "technique_code": selection.technique_code,
                "profile_hash": selection.profile.profile_hash,
                "constraints": [item.value for item in constraints],
                "factor_values": factor_values,
            }
            arm_hash = stable_hash(identity)
            yield ExperimentArm(
                arm_id=f"arm_{arm_hash[:24]}",
                arm_hash=arm_hash,
                matrix_id=self.matrix_id,
                matrix_version=self.matrix_version,
                registry_hash=self.registry_hash,
                technique_code=selection.technique_code,
                profile_id=selection.profile.profile_id,
                profile_hash=selection.profile.profile_hash,
                constraints=constraints,
                ablated_constraints=tuple(
                    layer for layer in ConstraintLayer if layer not in constraints
                ),
                factor_values=factor_values,
            )


class ExecutionStatus(StrEnum):
    EXECUTED = "executed"
    TECHNICAL_FAILURE = "technical_failure"


class ExperimentArmConfigurationSnapshot(ResearchModel):
    matrix_id: str = Field(min_length=1)
    matrix_version: str = Field(min_length=1)
    registry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    technique_code: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    constraints: tuple[ConstraintLayer, ...]
    ablated_constraints: tuple[ConstraintLayer, ...]
    factor_values: dict[str, JsonValue]

    @model_validator(mode="after")
    def freeze_values(self) -> ExperimentArmConfigurationSnapshot:
        object.__setattr__(self, "factor_values", freeze_json(self.factor_values))
        if len(self.constraints) != len(set(self.constraints)) or len(
            self.ablated_constraints
        ) != len(set(self.ablated_constraints)):
            raise ValueError("configuration snapshot cannot repeat constraints")
        if set(self.constraints) & set(self.ablated_constraints):
            raise ValueError("configuration selected and ablated constraints cannot overlap")
        if set(self.constraints) | set(self.ablated_constraints) != set(ConstraintLayer):
            raise ValueError("configuration snapshot must cover every constraint layer")
        return self

    @classmethod
    def from_arm(cls, arm: ExperimentArm) -> ExperimentArmConfigurationSnapshot:
        return cls(
            matrix_id=arm.matrix_id,
            matrix_version=arm.matrix_version,
            registry_hash=arm.registry_hash,
            technique_code=arm.technique_code,
            profile_id=arm.profile_id,
            profile_hash=arm.profile_hash,
            constraints=arm.constraints,
            ablated_constraints=arm.ablated_constraints,
            factor_values=arm.factor_values,
        )

    @property
    def configuration_hash(self) -> str:
        return stable_hash(self)

    @property
    def expected_arm_hash(self) -> str:
        return stable_hash(
            {
                "matrix_id": self.matrix_id,
                "matrix_version": self.matrix_version,
                "registry_hash": self.registry_hash,
                "technique_code": self.technique_code,
                "profile_hash": self.profile_hash,
                "constraints": [item.value for item in self.constraints],
                "factor_values": self.factor_values,
            }
        )


class ExperimentFailureArtifact(ResearchModel):
    artifact_type: Literal["experiment_execution_failure"] = "experiment_execution_failure"
    execution_id: str = Field(min_length=1)
    arm_id: str = Field(min_length=1)
    arm_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    configuration_snapshot: ExperimentArmConfigurationSnapshot
    configuration_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    started_at: datetime
    completed_at: datetime
    error_code: str = Field(min_length=1)
    error_message: str = Field(min_length=1)
    raw_error_payload: JsonValue

    @model_validator(mode="after")
    def bind_and_freeze(self) -> ExperimentFailureArtifact:
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("failure artifact timestamps must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("failure artifact completion cannot precede start")
        if self.configuration_snapshot_hash != self.configuration_snapshot.configuration_hash:
            raise ValueError("failure configuration hash does not match its snapshot")
        expected_arm_hash = self.configuration_snapshot.expected_arm_hash
        if self.arm_hash != expected_arm_hash or self.arm_id != f"arm_{expected_arm_hash[:24]}":
            raise ValueError("failure arm identity does not match its configuration snapshot")
        if self.raw_error_payload is None:
            raise ValueError("failure artifact requires its raw error payload")
        object.__setattr__(
            self, "configuration_snapshot", snapshot_model(self.configuration_snapshot)
        )
        object.__setattr__(self, "raw_error_payload", freeze_json(self.raw_error_payload))
        return self

    @property
    def artifact_hash(self) -> str:
        return stable_hash(self)


class ExperimentPredictionBinding(ResearchModel):
    """Execution-issued identity and normalization decision for one prediction."""

    prediction_id: str = Field(min_length=1)
    prediction_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_code: str = Field(min_length=1)
    evidence_direction: Literal["supporting", "opposing", "neutral"]
    normalization_provenance: JsonValue
    normalization_provenance_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def freeze_and_bind_provenance(self) -> ExperimentPredictionBinding:
        object.__setattr__(
            self, "normalization_provenance", freeze_json(self.normalization_provenance)
        )
        if self.normalization_provenance in ({}, [], "", None):
            raise ValueError("prediction normalization provenance cannot be empty")
        if self.normalization_provenance_hash != stable_hash(self.normalization_provenance):
            raise ValueError("prediction normalization provenance hash does not match")
        return self


class ExperimentExecutionRecord(ResearchModel):
    execution_id: str = Field(min_length=1)
    arm_id: str = Field(min_length=1)
    arm_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime
    technique_run_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw_error_payload: JsonValue | None = None
    configuration_snapshot: ExperimentArmConfigurationSnapshot
    configuration_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    prediction_ids: tuple[str, ...] = ()
    prediction_bindings: tuple[ExperimentPredictionBinding, ...] = ()

    @model_validator(mode="after")
    def validate_record(self) -> ExperimentExecutionRecord:
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("execution timestamps must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if self.configuration_snapshot_hash != self.configuration_snapshot.configuration_hash:
            raise ValueError("execution configuration hash does not match its snapshot")
        expected_arm_hash = self.configuration_snapshot.expected_arm_hash
        if self.arm_hash != expected_arm_hash or self.arm_id != f"arm_{expected_arm_hash[:24]}":
            raise ValueError("execution arm identity does not match its configuration snapshot")
        if len(self.prediction_ids) != len(set(self.prediction_ids)) or any(
            not item for item in self.prediction_ids
        ):
            raise ValueError("execution prediction IDs must be non-empty and unique")
        bound_ids = tuple(item.prediction_id for item in self.prediction_bindings)
        if bound_ids != self.prediction_ids:
            raise ValueError(
                "execution prediction IDs must exactly match ordered canonical bindings"
            )
        if len({item.prediction_hash for item in self.prediction_bindings}) != len(
            self.prediction_bindings
        ):
            raise ValueError("execution canonical prediction hashes must be unique")
        if self.status is ExecutionStatus.EXECUTED:
            if (
                not self.technique_run_id
                or self.error_code
                or self.error_message
                or self.raw_error_payload is not None
            ):
                raise ValueError("executed arm requires run ID and no technical error")
        elif (
            not self.error_code
            or not self.error_message
            or self.technique_run_id
            or self.raw_error_payload is None
            or self.prediction_ids
        ):
            raise ValueError(
                "technical failure requires error fields, raw payload, no predictions, and no run ID"
            )
        object.__setattr__(self, "raw_error_payload", freeze_json(self.raw_error_payload))
        object.__setattr__(
            self,
            "prediction_bindings",
            tuple(snapshot_model(item) for item in self.prediction_bindings),
        )
        object.__setattr__(
            self, "configuration_snapshot", snapshot_model(self.configuration_snapshot)
        )
        return self

    @property
    def research_artifact(self) -> ExperimentFailureArtifact:
        if self.status is not ExecutionStatus.TECHNICAL_FAILURE:
            raise ValueError("only a technical failure has a failure artifact")
        assert self.error_code is not None and self.error_message is not None
        assert self.raw_error_payload is not None
        return ExperimentFailureArtifact(
            execution_id=self.execution_id,
            arm_id=self.arm_id,
            arm_hash=self.arm_hash,
            configuration_snapshot=self.configuration_snapshot,
            configuration_snapshot_hash=self.configuration_snapshot_hash,
            started_at=self.started_at,
            completed_at=self.completed_at,
            error_code=self.error_code,
            error_message=self.error_message,
            raw_error_payload=self.raw_error_payload,
        )


class ExperimentExecutionBinding(ResearchModel):
    """Ledger-issued proof tying evidence to one planned execution."""

    ledger_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    ledger: ExperimentExecutionLedger
    execution_id: str = Field(min_length=1)
    arm_id: str = Field(min_length=1)
    arm_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: ExecutionStatus
    technique_run_id: str | None = None
    prediction_ids: tuple[str, ...] = ()
    prediction_bindings: tuple[ExperimentPredictionBinding, ...] = ()
    configuration_snapshot: ExperimentArmConfigurationSnapshot
    configuration_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_binding(self) -> ExperimentExecutionBinding:
        if self.ledger_hash != self.ledger.ledger_hash:
            raise ValueError("execution binding ledger hash does not match its ledger snapshot")
        record = next(
            (item for item in self.ledger.records if item.execution_id == self.execution_id),
            None,
        )
        if record is None:
            raise ValueError("execution binding is not present in its ledger snapshot")
        if (
            record.arm_id != self.arm_id
            or record.arm_hash != self.arm_hash
            or record.status is not self.status
            or record.technique_run_id != self.technique_run_id
            or record.prediction_ids != self.prediction_ids
            or record.prediction_bindings != self.prediction_bindings
            or record.configuration_snapshot != self.configuration_snapshot
            or record.configuration_snapshot_hash != self.configuration_snapshot_hash
        ):
            raise ValueError("execution binding does not match its ledger record")
        if self.configuration_snapshot_hash != self.configuration_snapshot.configuration_hash:
            raise ValueError("binding configuration hash does not match its snapshot")
        expected_arm_hash = self.configuration_snapshot.expected_arm_hash
        if self.arm_hash != expected_arm_hash or self.arm_id != f"arm_{expected_arm_hash[:24]}":
            raise ValueError("binding arm identity does not match its configuration snapshot")
        if self.status is ExecutionStatus.EXECUTED and not self.technique_run_id:
            raise ValueError("executed binding requires its technique run ID")
        if self.status is ExecutionStatus.TECHNICAL_FAILURE and (
            self.technique_run_id or self.prediction_ids
        ):
            raise ValueError("failed binding cannot contain a run or predictions")
        if len(self.prediction_ids) != len(set(self.prediction_ids)):
            raise ValueError("binding prediction IDs must be unique")
        if tuple(item.prediction_id for item in self.prediction_bindings) != self.prediction_ids:
            raise ValueError("binding prediction IDs do not match canonical bindings")
        object.__setattr__(
            self, "configuration_snapshot", snapshot_model(self.configuration_snapshot)
        )
        object.__setattr__(self, "ledger", snapshot_model(self.ledger))
        object.__setattr__(
            self,
            "prediction_bindings",
            tuple(snapshot_model(item) for item in self.prediction_bindings),
        )
        return self


class ExperimentExecutionLedger(ResearchModel):
    planned_arms: tuple[ExperimentArm, ...]
    records: tuple[ExperimentExecutionRecord, ...]

    @model_validator(mode="after")
    def bind_exact_execution_set(self) -> ExperimentExecutionLedger:
        if not self.planned_arms:
            raise ValueError("execution ledger requires at least one planned arm")
        planned = {arm.arm_id: arm for arm in self.planned_arms}
        if len(planned) != len(self.planned_arms):
            raise ValueError("planned arm IDs must be unique")
        if len({arm.arm_hash for arm in self.planned_arms}) != len(self.planned_arms):
            raise ValueError("planned arm hashes must be unique")
        record_ids = [record.arm_id for record in self.records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("each planned arm must have exactly one execution record")
        if set(record_ids) != set(planned):
            raise ValueError("execution ledger must cover every planned arm exactly once")
        execution_ids = [record.execution_id for record in self.records]
        if len(execution_ids) != len(set(execution_ids)):
            raise ValueError("execution IDs must be unique")
        technique_run_ids = [
            record.technique_run_id
            for record in self.records
            if record.technique_run_id is not None
        ]
        if len(technique_run_ids) != len(set(technique_run_ids)):
            raise ValueError("successful technique run IDs must be unique")
        prediction_ids = [
            prediction_id
            for record in self.records
            for prediction_id in record.prediction_ids
        ]
        if len(prediction_ids) != len(set(prediction_ids)):
            raise ValueError("prediction IDs must be unique across the execution ledger")
        prediction_hashes = [
            binding.prediction_hash
            for record in self.records
            for binding in record.prediction_bindings
        ]
        if len(prediction_hashes) != len(set(prediction_hashes)):
            raise ValueError("canonical prediction hashes must be unique across the execution ledger")
        for record in self.records:
            arm = planned[record.arm_id]
            if record.arm_hash != arm.arm_hash:
                raise ValueError("execution record arm hash does not match its plan")
            expected_snapshot = ExperimentArmConfigurationSnapshot.from_arm(arm)
            if record.configuration_snapshot != expected_snapshot:
                raise ValueError("execution configuration snapshot does not match planned arm")
        object.__setattr__(
            self,
            "planned_arms",
            tuple(
                sorted(
                    (snapshot_model(arm) for arm in self.planned_arms), key=lambda arm: arm.arm_id
                )
            ),
        )
        object.__setattr__(
            self,
            "records",
            tuple(
                sorted(
                    (snapshot_model(record) for record in self.records),
                    key=lambda record: record.arm_id,
                )
            ),
        )
        return self

    @property
    def ledger_hash(self) -> str:
        return stable_hash(self)

    def binding_for(self, arm_id: str) -> ExperimentExecutionBinding:
        record = next((item for item in self.records if item.arm_id == arm_id), None)
        if record is None:
            raise ValueError("execution ledger does not contain the requested arm")
        return ExperimentExecutionBinding(
            ledger_hash=self.ledger_hash,
            ledger=self,
            execution_id=record.execution_id,
            arm_id=record.arm_id,
            arm_hash=record.arm_hash,
            status=record.status,
            technique_run_id=record.technique_run_id,
            prediction_ids=record.prediction_ids,
            prediction_bindings=record.prediction_bindings,
            configuration_snapshot=record.configuration_snapshot,
            configuration_snapshot_hash=record.configuration_snapshot_hash,
        )
