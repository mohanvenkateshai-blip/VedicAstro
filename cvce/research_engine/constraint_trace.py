"""Progressive constraint variants and lossless per-layer traces."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, JsonValue, model_validator

from .constraint_types import ConstraintLayer, all_constraint_variants
from .contracts import ResearchModel
from .experiment_matrix import ExperimentArm
from .immutable import freeze_json, snapshot_model

__all__ = [
    "ConstraintLayer",
    "ConstraintObservation",
    "ConstraintObservationStatus",
    "ProgressiveConstraintTrace",
    "all_constraint_variants",
]


class ConstraintObservationStatus(StrEnum):
    EXECUTED = "executed"
    TECHNICAL_FAILURE = "technical_failure"
    NOT_SELECTED = "not_selected"


class ConstraintObservation(ResearchModel):
    layer: ConstraintLayer
    status: ConstraintObservationStatus
    native_result: JsonValue = Field(default_factory=dict)
    supporting_refs: tuple[str, ...] = ()
    opposing_refs: tuple[str, ...] = ()
    neutral_refs: tuple[str, ...] = ()
    error_code: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_execution_state(self) -> ConstraintObservation:
        object.__setattr__(self, "native_result", freeze_json(self.native_result))
        if self.status is ConstraintObservationStatus.TECHNICAL_FAILURE:
            if not self.error_code or not self.error_message:
                raise ValueError("technical constraint failure requires code and message")
            if self.native_result != {} or self.supporting_refs or self.opposing_refs or self.neutral_refs:
                raise ValueError("technical constraint failure cannot contain directional results")
        elif self.status is ConstraintObservationStatus.NOT_SELECTED:
            if self.native_result != {} or self.supporting_refs or self.opposing_refs or self.neutral_refs:
                raise ValueError("unselected constraint cannot contain results or evidence refs")
            if self.error_code or self.error_message:
                raise ValueError("only a technical failure may contain error fields")
        elif self.error_code or self.error_message:
            raise ValueError("only a technical failure may contain error fields")
        return self


class ProgressiveConstraintTrace(ResearchModel):
    trace_id: str = Field(min_length=1)
    arm: ExperimentArm
    event_code: str = Field(min_length=1)
    observations: tuple[ConstraintObservation, ...]

    @model_validator(mode="after")
    def validate_layer_order(self) -> ProgressiveConstraintTrace:
        layers = [item.layer for item in self.observations]
        if len(layers) != len(ConstraintLayer) or set(layers) != set(ConstraintLayer):
            raise ValueError("constraint trace must cover every layer exactly once")
        selected = set(self.arm.constraints)
        for observation in self.observations:
            if observation.layer in selected:
                if observation.status is ConstraintObservationStatus.NOT_SELECTED:
                    raise ValueError("selected constraint cannot be marked not selected")
            elif observation.status is not ConstraintObservationStatus.NOT_SELECTED:
                raise ValueError("ablated constraint must be marked not selected")
        executed_order = tuple(
            item.layer
            for item in self.observations
            if item.status is not ConstraintObservationStatus.NOT_SELECTED
        )
        if executed_order != self.arm.constraints:
            raise ValueError("executed constraint order must match the bound experiment arm")
        object.__setattr__(self, "arm", snapshot_model(self.arm))
        return self

    @property
    def arm_id(self) -> str:
        return self.arm.arm_id

    @property
    def arm_hash(self) -> str:
        return self.arm.arm_hash
