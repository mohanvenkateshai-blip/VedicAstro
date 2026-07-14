from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from research_engine.constraint_trace import (
    ConstraintLayer,
    ConstraintObservation,
    ConstraintObservationStatus,
    ProgressiveConstraintTrace,
    all_constraint_variants,
)
from research_engine.contracts import RawPrediction, RawScore, RawTiming
from research_engine.experiment_matrix import (
    ExecutionStatus,
    ExperimentArmConfigurationSnapshot,
    ExperimentExecutionLedger,
    ExperimentExecutionRecord,
    ExperimentFactor,
    ExperimentMatrixPlan,
    ExperimentPredictionBinding,
    MatrixBoundExceeded,
    TechniqueProfileSelection,
)
from research_engine.identity import stable_hash
from research_engine.synthesis import (
    EventEvidenceCell,
    EventEvidenceSlice,
    EventEvidenceTensor,
    EventSynthesisResult,
    EvidenceDirection,
    UnanimityCombinationStrategy,
    synthesize_event,
)
from research_engine.technique_registry import (
    DEFAULT_TECHNIQUE_REGISTRY,
    SchoolConfigurationProfile,
    TechniqueDefinition,
    TechniqueRegistry,
)

NOW = datetime(2026, 7, 14, 12, tzinfo=UTC)


def profile(profile_id: str = "profile-lahiri") -> SchoolConfigurationProfile:
    return SchoolConfigurationProfile(
        profile_id=profile_id,
        technique_code="vimshottari",
        profile_version="1.0.0",
        school_or_lineage="Parashara research profile",
        parameters={"ayanamsa": "lahiri", "year_length": 365.25636},
    )


def test_open_registry_covers_existing_techniques_and_arbitrary_extensions() -> None:
    expected = {
        "natal",
        "panchanga",
        "vimshottari",
        "yogini",
        "chara",
        "kalachakra",
        "kp",
        "prashna",
        "gochar",
        "ashtakavarga",
        "yoga",
        "muhurta",
    }
    assert expected.issubset(set(DEFAULT_TECHNIQUE_REGISTRY.technique_codes()))

    definitions = list(DEFAULT_TECHNIQUE_REGISTRY.definitions())
    definitions.append(
        TechniqueDefinition(
            technique_code="experimental.arbitrary_native_method",
            display_name="Arbitrary native method",
            family="open-research",
            implementation_ref="external://adapter/arbitrary",
            version="0.0.1",
        )
    )
    first = TechniqueRegistry(definitions)
    second = TechniqueRegistry(reversed(definitions))
    assert first.registry_hash == second.registry_hash
    assert first.require("experimental.arbitrary_native_method").family == "open-research"
    first.register_profile(profile())
    assert first.profiles("vimshottari")[0].school_or_lineage.startswith("Parashara")


def test_school_profile_hash_is_deterministic_and_configuration_sensitive() -> None:
    original = profile()
    replay = SchoolConfigurationProfile.model_validate_json(original.model_dump_json())
    changed = original.model_copy(update={"parameters": {"ayanamsa": "raman"}})
    assert replay.profile_hash == original.profile_hash
    assert changed.profile_hash != original.profile_hash


def matrix_plan(max_arms: int = 10) -> ExperimentMatrixPlan:
    return ExperimentMatrixPlan(
        matrix_id="matrix-1",
        matrix_version="1.0.0",
        registry_hash=DEFAULT_TECHNIQUE_REGISTRY.registry_hash,
        selections=(
            TechniqueProfileSelection(
                technique_code="vimshottari",
                profile=profile(),
            ),
        ),
        factors=(
            ExperimentFactor(factor_code="ayanamsa", values=("lahiri", "raman")),
            ExperimentFactor(factor_code="depth", values=(1, 2)),
        ),
        constraint_variants=all_constraint_variants(),
        max_arms_per_expansion=max_arms,
    )


def arm_with_constraints(
    constraints: tuple[ConstraintLayer, ...],
):
    plan = matrix_plan(max_arms=64)
    return next(arm for arm in plan.iter_arms(limit=64) if arm.constraints == constraints)


def test_constraint_factorial_contains_alone_all_combinations_and_ablations() -> None:
    variants = all_constraint_variants()
    assert len(variants) == 16
    assert () in variants
    assert (ConstraintLayer.PROMISE,) in variants
    assert (ConstraintLayer.PERIOD,) in variants
    assert (ConstraintLayer.SLOW_TRANSIT,) in variants
    assert (ConstraintLayer.FAST_TRIGGER,) in variants
    assert tuple(ConstraintLayer) in variants
    assert sum(len(item) == 3 for item in variants) == 4


def test_matrix_expansion_is_lazy_bounded_and_replayable() -> None:
    plan = matrix_plan(max_arms=7)
    assert plan.estimated_arm_count == 64
    first = tuple(plan.iter_arms(limit=7))
    replay = tuple(plan.iter_arms(limit=7))
    next_window = tuple(plan.iter_arms(offset=7, limit=7))
    assert first == replay
    assert len(first) == len(next_window) == 7
    assert {item.arm_hash for item in first}.isdisjoint({item.arm_hash for item in next_window})
    assert first[0].arm_id.startswith("arm_")
    assert set(first[0].constraints) | set(first[0].ablated_constraints) == set(ConstraintLayer)
    with pytest.raises(MatrixBoundExceeded):
        tuple(plan.iter_arms(limit=8))


def test_execution_record_makes_success_or_technical_failure_explicit() -> None:
    arm = next(matrix_plan().iter_arms(limit=1))
    snapshot = ExperimentArmConfigurationSnapshot.from_arm(arm)
    executed = ExperimentExecutionRecord(
        execution_id="execution-success",
        arm_id=arm.arm_id,
        arm_hash=arm.arm_hash,
        status=ExecutionStatus.EXECUTED,
        started_at=NOW,
        completed_at=NOW,
        technique_run_id="run-1",
        prediction_ids=("prediction-1",),
        prediction_bindings=(
            prediction_binding(
                raw_prediction("prediction-1", "event.execution"),
                EvidenceDirection.SUPPORTING,
            ),
        ),
        configuration_snapshot=snapshot,
        configuration_snapshot_hash=snapshot.configuration_hash,
    )
    failed = ExperimentExecutionRecord(
        execution_id="execution-failure",
        arm_id=arm.arm_id,
        arm_hash=arm.arm_hash,
        status=ExecutionStatus.TECHNICAL_FAILURE,
        started_at=NOW,
        completed_at=NOW,
        error_code="adapter_timeout",
        error_message="The technique adapter did not return.",
        raw_error_payload={"native_exception": "timeout", "attempt": 1},
        configuration_snapshot=snapshot,
        configuration_snapshot_hash=snapshot.configuration_hash,
    )
    assert executed.technique_run_id == "run-1"
    assert failed.error_code == "adapter_timeout"
    assert failed.research_artifact.raw_error_payload["native_exception"] == "timeout"
    with pytest.raises(ValidationError):
        ExperimentExecutionRecord(
            execution_id="execution-invalid",
            arm_id=arm.arm_id,
            arm_hash=arm.arm_hash,
            status=ExecutionStatus.TECHNICAL_FAILURE,
            started_at=NOW,
            completed_at=NOW,
        )


def test_progressive_trace_preserves_each_constraint_native_result_and_failure() -> None:
    arm = arm_with_constraints(
        (ConstraintLayer.PROMISE, ConstraintLayer.PERIOD, ConstraintLayer.SLOW_TRANSIT)
    )
    trace = ProgressiveConstraintTrace(
        trace_id="trace-1",
        arm=arm,
        event_code="sensitive.unrestricted.research.event",
        observations=(
            ConstraintObservation(
                layer=ConstraintLayer.PROMISE,
                status=ConstraintObservationStatus.EXECUTED,
                native_result={"score": "42/60", "verdict": "mishra"},
                supporting_refs=("promise-1",),
            ),
            ConstraintObservation(
                layer=ConstraintLayer.PERIOD,
                status=ConstraintObservationStatus.EXECUTED,
                native_result={"active": ["mahadasha", "antardasha"]},
                opposing_refs=("period-9",),
            ),
            ConstraintObservation(
                layer=ConstraintLayer.SLOW_TRANSIT,
                status=ConstraintObservationStatus.TECHNICAL_FAILURE,
                error_code="ephemeris_missing",
                error_message="Slow transit could not execute.",
            ),
            ConstraintObservation(
                layer=ConstraintLayer.FAST_TRIGGER,
                status=ConstraintObservationStatus.NOT_SELECTED,
            ),
        ),
    )
    assert trace.arm_hash == arm.arm_hash
    assert trace.observations[0].native_result["score"] == "42/60"
    assert trace.observations[2].status is ConstraintObservationStatus.TECHNICAL_FAILURE


def raw_prediction(prediction_id: str, event_code: str) -> RawPrediction:
    return RawPrediction(
        prediction_id=prediction_id,
        event_code=event_code,
        native_direction="native-unmapped-direction",
        native_polarity="native-unmapped-polarity",
        timing=RawTiming(kind="native-window", native_value="third segment"),
        scores=(
            RawScore(
                score_code="native-bala",
                original_value="42/60",
                numeric_value=42.0,
            ),
        ),
        original_payload={"verbatim": True, "score": -7},
    )


def prediction_binding(
    prediction: RawPrediction,
    direction: EvidenceDirection,
) -> ExperimentPredictionBinding:
    provenance = {
        "method": "test-explicit-native-direction-map",
        "source_native_direction": prediction.native_direction,
    }
    return ExperimentPredictionBinding(
        prediction_id=prediction.prediction_id,
        prediction_hash=stable_hash(prediction),
        event_code=prediction.event_code,
        evidence_direction=direction.value,
        normalization_provenance=provenance,
        normalization_provenance_hash=stable_hash(provenance),
    )


def evidence_arm(
    key: str,
    technique_code: str,
    *,
    parameters: dict | None = None,
):
    supplied = SchoolConfigurationProfile(
        profile_id=f"profile-{key}",
        technique_code=technique_code,
        profile_version="1",
        school_or_lineage="test research profile",
        parameters=parameters or {},
    )
    plan = ExperimentMatrixPlan(
        matrix_id=f"evidence-{key}",
        matrix_version="1",
        registry_hash=DEFAULT_TECHNIQUE_REGISTRY.registry_hash,
        selections=(TechniqueProfileSelection(technique_code=technique_code, profile=supplied),),
        constraint_variants=((),),
        max_arms_per_expansion=1,
    )
    return next(plan.iter_arms(limit=1))


def executed_cell(
    *,
    cell_id: str,
    event_code: str,
    arm,
    execution_id: str,
    run_id: str,
    direction: EvidenceDirection,
    prediction: RawPrediction,
) -> EventEvidenceCell:
    snapshot = ExperimentArmConfigurationSnapshot.from_arm(arm)
    record = ExperimentExecutionRecord(
        execution_id=execution_id,
        arm_id=arm.arm_id,
        arm_hash=arm.arm_hash,
        status=ExecutionStatus.EXECUTED,
        started_at=NOW,
        completed_at=NOW,
        technique_run_id=run_id,
        prediction_ids=(prediction.prediction_id,),
        prediction_bindings=(prediction_binding(prediction, direction),),
        configuration_snapshot=snapshot,
        configuration_snapshot_hash=snapshot.configuration_hash,
    )
    ledger = ExperimentExecutionLedger(planned_arms=(arm,), records=(record,))
    return EventEvidenceCell(
        cell_id=cell_id,
        event_code=event_code,
        technique_code=arm.technique_code,
        profile_hash=arm.profile_hash,
        arm_id=arm.arm_id,
        arm_hash=arm.arm_hash,
        execution_id=execution_id,
        run_id=run_id,
        direction=direction,
        configuration=snapshot.model_dump(mode="json"),
        raw_prediction=prediction,
        execution_binding=ledger.binding_for(arm.arm_id),
    )


def test_event_tensor_preserves_direction_scores_timings_and_configuration() -> None:
    event = "sensitive.health.mortality.native_source_code"
    vim_arm = evidence_arm("vim", "vimshottari", parameters={"ayanamsa": "lahiri"})
    gochar_arm = evidence_arm("gochar", "gochar", parameters={"orb": "native"})
    yoga_arm = evidence_arm("yoga", "yoga")
    tensor = EventEvidenceTensor(
        tensor_id="tensor-1",
        cells=(
            executed_cell(
                cell_id="cell-support",
                event_code=event,
                arm=vim_arm,
                execution_id="execution-1",
                run_id="run-1",
                direction=EvidenceDirection.SUPPORTING,
                prediction=raw_prediction("prediction-1", event),
            ),
            executed_cell(
                cell_id="cell-oppose",
                event_code=event,
                arm=gochar_arm,
                execution_id="execution-2",
                run_id="run-2",
                direction=EvidenceDirection.OPPOSING,
                prediction=raw_prediction("prediction-2", event),
            ),
            executed_cell(
                cell_id="cell-neutral",
                event_code="another.event",
                arm=yoga_arm,
                execution_id="execution-3",
                run_id="run-3",
                direction=EvidenceDirection.NEUTRAL,
                prediction=raw_prediction("prediction-3", "another.event"),
            ),
        ),
    )
    event_slice = tensor.for_event(event)
    assert len(event_slice.cells) == 2
    vimshottari = next(item for item in event_slice.cells if item.technique_code == "vimshottari")
    assert vimshottari.raw_prediction.scores[0].original_value == "42/60"
    assert vimshottari.raw_prediction.timing.native_value == "third segment"
    assert vimshottari.profile_hash == vim_arm.profile_hash
    assert vimshottari.configuration["profile_hash"] == vim_arm.profile_hash


def test_combination_is_event_specific_research_result_and_retains_raw_outputs() -> None:
    event = "unrestricted.event.alpha"
    kp_arm = evidence_arm("kp", "kp")
    prashna_arm = evidence_arm("prashna", "prashna")
    cells = (
        executed_cell(
            cell_id="a",
            event_code=event,
            arm=kp_arm,
            execution_id="execution-a1",
            run_id="r1",
            direction=EvidenceDirection.SUPPORTING,
            prediction=raw_prediction("p1", event),
        ),
        executed_cell(
            cell_id="b",
            event_code=event,
            arm=prashna_arm,
            execution_id="execution-a2",
            run_id="r2",
            direction=EvidenceDirection.OPPOSING,
            prediction=raw_prediction("p2", event),
        ),
    )
    tensor = EventEvidenceTensor(tensor_id="tensor-combine", cells=cells)
    result = synthesize_event(tensor.for_event(event), UnanimityCombinationStrategy())
    assert result.event_code == event
    assert result.derived_direction is EvidenceDirection.NEUTRAL
    assert result.evidence.cells == cells
    assert result.strategy_code == "event_unanimity"
    assert not hasattr(result, "global_auspiciousness")


def test_nested_inputs_are_owned_frozen_and_hashes_cannot_go_stale() -> None:
    params = {"nested": {"values": [1, 2]}}
    supplied = SchoolConfigurationProfile(
        profile_id="owned", technique_code="vimshottari", profile_version="1", parameters=params
    )
    original_hash = supplied.profile_hash
    params["nested"]["values"].append(3)
    assert supplied.profile_hash == original_hash
    with pytest.raises(TypeError):
        supplied.parameters["nested"]["values"] += (3,)

    registry = TechniqueRegistry(DEFAULT_TECHNIQUE_REGISTRY.definitions())
    registry.register_profile(supplied)
    snapshot_hash = registry.registry_hash
    with pytest.raises(TypeError):
        registry.profiles()[0].parameters["new"] = True
    assert registry.registry_hash == snapshot_hash

    plan = ExperimentMatrixPlan(
        matrix_id="immutable",
        matrix_version="1",
        registry_hash=registry.registry_hash,
        selections=(TechniqueProfileSelection(technique_code="vimshottari", profile=supplied),),
        factors=(ExperimentFactor(factor_code="x", values=({"v": [2, 1]}, {"v": [1]})),),
        constraint_variants=((ConstraintLayer.PERIOD, ConstraintLayer.PROMISE),),
    )
    arm = next(plan.iter_arms(limit=1))
    with pytest.raises(TypeError):
        arm.factor_values["x"]["v"] += (9,)
    with pytest.raises(ValidationError):
        type(arm).model_validate_json(
            arm.model_copy(update={"arm_hash": "0" * 64}).model_dump_json()
        )


def test_exhaustive_subsets_duplicates_and_order_sensitive_stages() -> None:
    base = dict(
        matrix_id="validation",
        matrix_version="1",
        registry_hash=DEFAULT_TECHNIQUE_REGISTRY.registry_hash,
        selections=(TechniqueProfileSelection(technique_code="vimshottari", profile=profile()),),
    )
    with pytest.raises(ValidationError):
        ExperimentMatrixPlan(
            **base, constraint_variants=((ConstraintLayer.PROMISE,),), exhaustive_constraints=True
        )
    exhaustive = ExperimentMatrixPlan(
        **base,
        constraint_variants=tuple(reversed(all_constraint_variants())),
        exhaustive_constraints=True,
    )
    assert len(exhaustive.constraint_variants) == 16
    subset = ExperimentMatrixPlan(
        **base,
        constraint_variants=(
            (ConstraintLayer.PERIOD, ConstraintLayer.PROMISE),
            (ConstraintLayer.PROMISE, ConstraintLayer.PERIOD),
        ),
    )
    assert next(subset.iter_arms(limit=1)).constraints == (
        ConstraintLayer.PERIOD,
        ConstraintLayer.PROMISE,
    )
    assert len({arm.arm_hash for arm in subset.iter_arms(limit=2)}) == 2
    with pytest.raises(ValidationError):
        ExperimentFactor(factor_code="duplicate", values=({"x": 1}, {"x": 1}))
    selection = TechniqueProfileSelection(technique_code="vimshottari", profile=profile())
    with pytest.raises(ValidationError):
        ExperimentMatrixPlan(
            **{**base, "selections": (selection, selection)}, constraint_variants=((),)
        )


def test_execution_ledger_requires_one_record_per_arm_and_preserves_failures() -> None:
    arms = tuple(matrix_plan(max_arms=2).iter_arms(limit=2))
    success_snapshot = ExperimentArmConfigurationSnapshot.from_arm(arms[0])
    failure_snapshot = ExperimentArmConfigurationSnapshot.from_arm(arms[1])
    success = ExperimentExecutionRecord(
        execution_id="execution-success",
        arm_id=arms[0].arm_id,
        arm_hash=arms[0].arm_hash,
        status=ExecutionStatus.EXECUTED,
        started_at=NOW,
        completed_at=NOW,
        technique_run_id="run-success",
        prediction_ids=("success-prediction",),
        prediction_bindings=(
            prediction_binding(
                raw_prediction("success-prediction", "event.success"),
                EvidenceDirection.SUPPORTING,
            ),
        ),
        configuration_snapshot=success_snapshot,
        configuration_snapshot_hash=success_snapshot.configuration_hash,
    )
    failure_record = ExperimentExecutionRecord(
        execution_id="execution-failure",
        arm_id=arms[1].arm_id,
        arm_hash=arms[1].arm_hash,
        status=ExecutionStatus.TECHNICAL_FAILURE,
        started_at=NOW,
        completed_at=NOW,
        error_code="native-crash",
        error_message="adapter failed",
        raw_error_payload={"exception": {"type": "NativeError", "args": [7]}},
        configuration_snapshot=failure_snapshot,
        configuration_snapshot_hash=failure_snapshot.configuration_hash,
    )
    ledger = ExperimentExecutionLedger(planned_arms=arms, records=(failure_record, success))
    failure_record = next(
        item for item in ledger.records if item.status is ExecutionStatus.TECHNICAL_FAILURE
    )
    assert failure_record.research_artifact.artifact_type == "experiment_execution_failure"
    failure_cell = EventEvidenceCell(
        cell_id="failure-cell",
        event_code="event.native",
        technique_code="vimshottari",
        profile_hash=failure_record.configuration_snapshot.profile_hash,
        arm_id=failure_record.arm_id,
        arm_hash=failure_record.arm_hash,
        execution_id=failure_record.execution_id,
        direction=EvidenceDirection.NEUTRAL,
        configuration=failure_record.configuration_snapshot.model_dump(mode="json"),
        technical_failure=failure_record.research_artifact,
        execution_binding=ledger.binding_for(failure_record.arm_id),
    )
    retained_failure = (
        EventEvidenceTensor(tensor_id="failure-tensor", cells=(failure_cell,))
        .cells[0]
        .technical_failure
    )
    assert retained_failure.raw_error_payload["exception"]["type"] == "NativeError"
    with pytest.raises(ValidationError):
        ExperimentExecutionLedger(planned_arms=arms, records=(success,))
    with pytest.raises(ValidationError):
        ExperimentExecutionLedger(planned_arms=arms, records=(success, success))


def test_matrix_random_access_rejects_impossible_offset_and_is_input_order_invariant() -> None:
    first = matrix_plan(max_arms=3)
    second = ExperimentMatrixPlan(
        matrix_id=first.matrix_id,
        matrix_version=first.matrix_version,
        registry_hash=first.registry_hash,
        selections=tuple(reversed(first.selections)),
        factors=tuple(reversed(first.factors)),
        constraint_variants=tuple(reversed(first.constraint_variants)),
        max_arms_per_expansion=3,
    )
    assert first.plan_hash == second.plan_hash
    assert tuple(first.iter_arms(offset=61, limit=3)) == tuple(second.iter_arms(offset=61, limit=3))
    with pytest.raises(MatrixBoundExceeded):
        tuple(first.iter_arms(offset=10**30, limit=1))


def test_stage_trace_preserves_non_enum_execution_order() -> None:
    base = matrix_plan(max_arms=1)
    ordered_plan = ExperimentMatrixPlan(
        matrix_id="ordered-plan",
        matrix_version="1",
        registry_hash=base.registry_hash,
        selections=base.selections,
        constraint_variants=((ConstraintLayer.FAST_TRIGGER, ConstraintLayer.PROMISE),),
        max_arms_per_expansion=1,
    )
    arm = next(ordered_plan.iter_arms(limit=1))
    trace = ProgressiveConstraintTrace(
        trace_id="ordered",
        arm=arm,
        event_code="event",
        observations=(
            ConstraintObservation(
                layer=ConstraintLayer.FAST_TRIGGER, status=ConstraintObservationStatus.EXECUTED
            ),
            ConstraintObservation(
                layer=ConstraintLayer.PROMISE, status=ConstraintObservationStatus.EXECUTED
            ),
            ConstraintObservation(
                layer=ConstraintLayer.PERIOD, status=ConstraintObservationStatus.NOT_SELECTED
            ),
            ConstraintObservation(
                layer=ConstraintLayer.SLOW_TRANSIT, status=ConstraintObservationStatus.NOT_SELECTED
            ),
        ),
    )
    assert tuple(
        item.layer
        for item in trace.observations
        if item.status is not ConstraintObservationStatus.NOT_SELECTED
    ) == (ConstraintLayer.FAST_TRIGGER, ConstraintLayer.PROMISE)


def test_failure_evidence_is_typed_bound_visible_and_never_directional() -> None:
    arm = next(matrix_plan(max_arms=1).iter_arms(limit=1))
    snapshot = ExperimentArmConfigurationSnapshot.from_arm(arm)
    failure_record = ExperimentExecutionRecord(
        execution_id="failure-execution",
        arm_id=arm.arm_id,
        arm_hash=arm.arm_hash,
        status=ExecutionStatus.TECHNICAL_FAILURE,
        started_at=NOW,
        completed_at=NOW,
        error_code="timeout",
        error_message="adapter timed out",
        raw_error_payload={"native": {"args": [1, 2]}},
        configuration_snapshot=snapshot,
        configuration_snapshot_hash=snapshot.configuration_hash,
    )
    ledger = ExperimentExecutionLedger(planned_arms=(arm,), records=(failure_record,))
    failure = failure_record.research_artifact
    failure_cell = EventEvidenceCell(
        cell_id="failed",
        event_code="event.open",
        technique_code=arm.technique_code,
        profile_hash=arm.profile_hash,
        arm_id=arm.arm_id,
        arm_hash=arm.arm_hash,
        execution_id=failure.execution_id,
        direction=EvidenceDirection.NEUTRAL,
        configuration=snapshot.model_dump(mode="json"),
        technical_failure=failure,
        execution_binding=ledger.binding_for(arm.arm_id),
    )

    result = synthesize_event(
        EventEvidenceSlice(event_code="event.open", cells=(failure_cell,)),
        UnanimityCombinationStrategy(),
    )
    assert result.derived_direction is EvidenceDirection.NEUTRAL
    assert result.strategy_native_result["technical_failures"][0]["execution_id"] == (
        "failure-execution"
    )
    artifact_hash = failure.artifact_hash
    with pytest.raises(TypeError):
        failure.raw_error_payload["native"]["args"].append(3)
    assert failure.artifact_hash == artifact_hash
    with pytest.raises(ValidationError):
        EventEvidenceCell(
            **{
                **failure_cell.model_dump(mode="python"),
                "cell_id": "directional-failure",
                "direction": EvidenceDirection.SUPPORTING,
            }
        )
    with pytest.raises(ValidationError):
        EventEvidenceCell(
            **{
                **failure_cell.model_dump(mode="python"),
                "cell_id": "invented-run",
                "run_id": "not-a-technique-run",
            }
        )
    with pytest.raises(ValidationError):
        EventEvidenceCell(
            **{
                **failure_cell.model_dump(mode="python"),
                "cell_id": "wrong-arm",
                "arm_id": "different-arm",
            }
        )
    with pytest.raises(ValidationError):
        EventEvidenceCell(
            **{
                **failure_cell.model_dump(mode="python"),
                "cell_id": "wrong-configuration",
                "configuration": {"different": True},
            }
        )
    with pytest.raises(ValidationError, match="failed execution cannot be retyped"):
        EventEvidenceCell(
            cell_id="retyped-failure",
            event_code="event.open",
            technique_code=arm.technique_code,
            profile_hash=arm.profile_hash,
            arm_id=arm.arm_id,
            arm_hash=arm.arm_hash,
            execution_id=failure.execution_id,
            run_id="invented-run",
            direction=EvidenceDirection.SUPPORTING,
            configuration=snapshot.model_dump(mode="json"),
            raw_prediction=raw_prediction("invented-prediction", "event.open"),
            execution_binding=ledger.binding_for(arm.arm_id),
        )


def test_duplicate_cell_ids_are_rejected_by_slice_and_synthesis() -> None:
    event = "event.duplicate"
    arm = evidence_arm("duplicate", "open")
    cell = executed_cell(
        cell_id="duplicate",
        event_code=event,
        arm=arm,
        execution_id="duplicate-execution",
        run_id="run",
        direction=EvidenceDirection.SUPPORTING,
        prediction=raw_prediction("duplicate-prediction", event),
    )
    with pytest.raises(ValidationError, match="cell IDs must be unique"):
        EventEvidenceSlice(event_code=event, cells=(cell, cell))
    renamed_duplicate = EventEvidenceCell.model_validate(
        {**cell.model_dump(mode="python"), "cell_id": "different-caller-label"}
    )
    with pytest.raises(ValidationError, match="canonical evidence identities"):
        EventEvidenceSlice(event_code=event, cells=(cell, renamed_duplicate))
    with pytest.raises(ValidationError, match="canonical evidence identities"):
        EventEvidenceTensor(tensor_id="duplicate-tensor", cells=(cell, renamed_duplicate))
    with pytest.raises(ValidationError, match="configuration"):
        EventEvidenceCell.model_validate(
            {**cell.model_dump(mode="python"), "cell_id": "wrong-config", "configuration": {}}
        )
    with pytest.raises(ValidationError, match="not declared"):
        EventEvidenceCell.model_validate(
            {
                **cell.model_dump(mode="python"),
                "cell_id": "undeclared-prediction",
                "raw_prediction": raw_prediction("not-in-execution", event),
            }
        )


def test_nonexecuted_constraint_stages_cannot_carry_directional_payload() -> None:
    with pytest.raises(ValidationError, match="directional results"):
        ConstraintObservation(
            layer=ConstraintLayer.PROMISE,
            status=ConstraintObservationStatus.TECHNICAL_FAILURE,
            native_result={"direction": "supporting", "score": 999},
            supporting_refs=("fabricated",),
            error_code="native-failure",
            error_message="failed",
        )
    with pytest.raises(ValidationError, match="cannot contain results"):
        ConstraintObservation(
            layer=ConstraintLayer.PROMISE,
            status=ConstraintObservationStatus.NOT_SELECTED,
            opposing_refs=("fabricated",),
        )


@pytest.mark.parametrize("native_result", [0, False, "", []])
@pytest.mark.parametrize(
    ("status", "error_fields"),
    [
        (
            ConstraintObservationStatus.TECHNICAL_FAILURE,
            {"error_code": "failed", "error_message": "failed"},
        ),
        (ConstraintObservationStatus.NOT_SELECTED, {}),
    ],
)
def test_nonexecuted_constraint_stages_require_exact_empty_mapping(
    native_result,
    status,
    error_fields,
) -> None:
    with pytest.raises(ValidationError, match="cannot contain"):
        ConstraintObservation(
            layer=ConstraintLayer.PROMISE,
            status=status,
            native_result=native_result,
            **error_fields,
        )


def test_direct_synthesis_result_is_recursively_immutable() -> None:
    event = "event.immutable-result"
    arm = evidence_arm("immutable", "open")
    cell = executed_cell(
        cell_id="immutable-cell",
        event_code=event,
        arm=arm,
        execution_id="immutable-execution",
        run_id="run",
        direction=EvidenceDirection.SUPPORTING,
        prediction=raw_prediction("immutable-prediction", event),
    )
    evidence = EventEvidenceSlice(event_code=event, cells=(cell,))
    result = synthesize_event(evidence, UnanimityCombinationStrategy())
    original_binding_hash = result.outcome_binding_hash
    with pytest.raises(TypeError):
        result.strategy_native_result["strategy_result"]["cell_directions"].append("opposing")
    strategy_result = result.strategy_native_result["strategy_result"]
    with pytest.raises(TypeError):
        strategy_result |= {"forged": True}
    assert result.outcome_binding_hash == original_binding_hash
    assert "forged" not in result.strategy_native_result["strategy_result"]

    contradictory = result.model_dump(mode="python")
    contradictory["derived_direction"] = EvidenceDirection.OPPOSING
    with pytest.raises(ValidationError, match="factory-validated strategy outcome"):
        EventSynthesisResult.model_validate(contradictory)

    bad_proof = result.model_dump(mode="python")
    bad_proof["validated_outcome"]["proof_hash"] = "0" * 64
    with pytest.raises(ValidationError, match="proof"):
        EventSynthesisResult.model_validate(bad_proof)

    reminted = result.model_dump(mode="python")
    reminted["derived_direction"] = EvidenceDirection.OPPOSING
    reminted["validated_outcome"]["derived_direction"] = EvidenceDirection.OPPOSING
    reminted["validated_outcome"]["proof_hash"] = stable_hash(
        {
            "artifact_type": "validated_strategy_outcome",
            "strategy_code": reminted["strategy_code"],
            "strategy_version": reminted["strategy_version"],
            "derived_direction": "opposing",
            "native_result": reminted["strategy_native_result"],
            "evidence_hash": reminted["evidence_hash"],
        }
    )
    reminted["outcome_binding_hash"] = stable_hash(
        {
            "event_code": reminted["event_code"],
            "strategy_code": reminted["strategy_code"],
            "strategy_version": reminted["strategy_version"],
            "derived_direction": "opposing",
            "strategy_native_result": reminted["strategy_native_result"],
            "evidence_hash": reminted["evidence_hash"],
        }
    )
    with pytest.raises(ValidationError, match="registered-strategy replay"):
        EventSynthesisResult.model_validate(reminted)


def test_prediction_content_and_direction_are_execution_bound() -> None:
    event = "event.bound-prediction"
    arm = evidence_arm("bound-prediction", "open")
    prediction = raw_prediction("bound-prediction", event)
    cell = executed_cell(
        cell_id="bound",
        event_code=event,
        arm=arm,
        execution_id="bound-execution",
        run_id="bound-run",
        direction=EvidenceDirection.SUPPORTING,
        prediction=prediction,
    )

    forged_prediction = RawPrediction(
        prediction_id=prediction.prediction_id,
        event_code=event,
        native_direction="forged-opposite",
        original_prose="forged content",
        original_payload={"forged": True},
    )
    with pytest.raises(ValidationError, match="content does not match"):
        EventEvidenceCell.model_validate(
            {
                **cell.model_dump(mode="python"),
                "cell_id": "forged-content",
                "raw_prediction": forged_prediction,
            }
        )

    with pytest.raises(ValidationError, match="direction does not match"):
        EventEvidenceCell.model_validate(
            {
                **cell.model_dump(mode="python"),
                "cell_id": "retyped-direction",
                "direction": EvidenceDirection.OPPOSING,
            }
        )


def test_cross_ledger_replay_and_execution_retyping_are_rejected() -> None:
    event = "event.cross-ledger"
    arm = evidence_arm("cross-ledger", "open")
    prediction = raw_prediction("shared-prediction", event)
    first = executed_cell(
        cell_id="first",
        event_code=event,
        arm=arm,
        execution_id="execution-first",
        run_id="run-first",
        direction=EvidenceDirection.SUPPORTING,
        prediction=prediction,
    )
    replay = executed_cell(
        cell_id="replay",
        event_code=event,
        arm=arm,
        execution_id="execution-relabelled",
        run_id="run-relabelled",
        direction=EvidenceDirection.OPPOSING,
        prediction=prediction,
    )
    with pytest.raises(ValidationError, match="canonical evidence identities"):
        EventEvidenceTensor(tensor_id="replay", cells=(first, replay))

    snapshot = ExperimentArmConfigurationSnapshot.from_arm(arm)
    failed_record = ExperimentExecutionRecord(
        execution_id="shared-execution",
        arm_id=arm.arm_id,
        arm_hash=arm.arm_hash,
        status=ExecutionStatus.TECHNICAL_FAILURE,
        started_at=NOW,
        completed_at=NOW,
        error_code="failed",
        error_message="adapter failed",
        raw_error_payload={"native": "failed"},
        configuration_snapshot=snapshot,
        configuration_snapshot_hash=snapshot.configuration_hash,
    )
    failed_ledger = ExperimentExecutionLedger(
        planned_arms=(arm,), records=(failed_record,)
    )
    failure_cell = EventEvidenceCell(
        cell_id="failure",
        event_code=event,
        technique_code=arm.technique_code,
        profile_hash=arm.profile_hash,
        arm_id=arm.arm_id,
        arm_hash=arm.arm_hash,
        execution_id="shared-execution",
        direction=EvidenceDirection.NEUTRAL,
        configuration=snapshot.model_dump(mode="json"),
        technical_failure=failed_record.research_artifact,
        execution_binding=failed_ledger.binding_for(arm.arm_id),
    )
    successful_cell = executed_cell(
        cell_id="success",
        event_code=event,
        arm=arm,
        execution_id="shared-execution",
        run_id="successful-run",
        direction=EvidenceDirection.SUPPORTING,
        prediction=raw_prediction("successful-prediction", event),
    )
    with pytest.raises(ValidationError, match="authoritative ledger set has overlapping"):
        EventEvidenceTensor(
            tensor_id="retyped-execution", cells=(failure_cell, successful_cell)
        )


def test_evidence_authoritative_ledger_set_is_exact() -> None:
    event = "event.authority"
    arm = evidence_arm("authority", "open")
    cell = executed_cell(
        cell_id="authority",
        event_code=event,
        arm=arm,
        execution_id="authority-execution",
        run_id="authority-run",
        direction=EvidenceDirection.SUPPORTING,
        prediction=raw_prediction("authority-prediction", event),
    )
    evidence = EventEvidenceSlice(event_code=event, cells=(cell,))
    assert evidence.authoritative_ledger_hashes == (cell.execution_binding.ledger_hash,)
    with pytest.raises(ValidationError, match="authoritative ledger set"):
        EventEvidenceSlice(
            event_code=event,
            cells=(cell,),
            authoritative_ledger_hashes=("0" * 64,),
        )


def test_constraint_trace_is_bound_to_exact_arm_coverage_status_and_order() -> None:
    arm = arm_with_constraints((ConstraintLayer.PROMISE, ConstraintLayer.PERIOD))
    valid = (
        ConstraintObservation(
            layer=ConstraintLayer.PROMISE,
            status=ConstraintObservationStatus.EXECUTED,
        ),
        ConstraintObservation(
            layer=ConstraintLayer.PERIOD,
            status=ConstraintObservationStatus.EXECUTED,
        ),
        ConstraintObservation(
            layer=ConstraintLayer.SLOW_TRANSIT,
            status=ConstraintObservationStatus.NOT_SELECTED,
        ),
        ConstraintObservation(
            layer=ConstraintLayer.FAST_TRIGGER,
            status=ConstraintObservationStatus.NOT_SELECTED,
        ),
    )
    trace = ProgressiveConstraintTrace(
        trace_id="bound", arm=arm, event_code="event", observations=valid
    )
    assert (trace.arm_id, trace.arm_hash) == (arm.arm_id, arm.arm_hash)
    with pytest.raises(ValidationError, match="cover every layer"):
        ProgressiveConstraintTrace(
            trace_id="missing", arm=arm, event_code="event", observations=valid[:-1]
        )
    wrong_status = list(valid)
    wrong_status[2] = ConstraintObservation(
        layer=ConstraintLayer.SLOW_TRANSIT,
        status=ConstraintObservationStatus.EXECUTED,
    )
    with pytest.raises(ValidationError, match="ablated constraint"):
        ProgressiveConstraintTrace(
            trace_id="wrong-status",
            arm=arm,
            event_code="event",
            observations=tuple(wrong_status),
        )
    with pytest.raises(ValidationError, match="executed constraint order"):
        ProgressiveConstraintTrace(
            trace_id="wrong-order",
            arm=arm,
            event_code="event",
            observations=(valid[1], valid[0], valid[2], valid[3]),
        )


def test_ledger_rejects_empty_duplicate_runs_and_wrong_configuration_snapshot() -> None:
    with pytest.raises(ValidationError, match="at least one planned arm"):
        ExperimentExecutionLedger(planned_arms=(), records=())

    arms = tuple(matrix_plan(max_arms=2).iter_arms(limit=2))
    records = tuple(
        ExperimentExecutionRecord(
            execution_id="duplicate-execution",
            arm_id=arm.arm_id,
            arm_hash=arm.arm_hash,
            status=ExecutionStatus.EXECUTED,
            started_at=NOW,
            completed_at=NOW,
            technique_run_id=f"run-{index}",
            configuration_snapshot=ExperimentArmConfigurationSnapshot.from_arm(arm),
            configuration_snapshot_hash=ExperimentArmConfigurationSnapshot.from_arm(
                arm
            ).configuration_hash,
        )
        for index, arm in enumerate(arms)
    )
    with pytest.raises(ValidationError, match="Execution IDs|execution IDs"):
        ExperimentExecutionLedger(planned_arms=arms, records=records)

    duplicate_prediction_records = tuple(
        ExperimentExecutionRecord(
            execution_id=f"prediction-execution-{index}",
            arm_id=arm.arm_id,
            arm_hash=arm.arm_hash,
            status=ExecutionStatus.EXECUTED,
            started_at=NOW,
            completed_at=NOW,
            technique_run_id=f"prediction-run-{index}",
            prediction_ids=("same-prediction",),
            prediction_bindings=(
                prediction_binding(
                    raw_prediction("same-prediction", "event.same"),
                    EvidenceDirection.SUPPORTING,
                ),
            ),
            configuration_snapshot=ExperimentArmConfigurationSnapshot.from_arm(arm),
            configuration_snapshot_hash=ExperimentArmConfigurationSnapshot.from_arm(
                arm
            ).configuration_hash,
        )
        for index, arm in enumerate(arms)
    )
    with pytest.raises(ValidationError, match="prediction IDs must be unique"):
        ExperimentExecutionLedger(
            planned_arms=arms,
            records=duplicate_prediction_records,
        )

    wrong_snapshot = ExperimentArmConfigurationSnapshot.from_arm(arms[0])
    wrong_snapshot_failure = ExperimentExecutionRecord.model_construct(
        execution_id="wrong-snapshot",
        arm_id=arms[1].arm_id,
        arm_hash=arms[1].arm_hash,
        status=ExecutionStatus.TECHNICAL_FAILURE,
        started_at=NOW,
        completed_at=NOW,
        error_code="failure",
        error_message="wrong snapshot",
        raw_error_payload={"native": True},
        configuration_snapshot=wrong_snapshot,
        configuration_snapshot_hash=wrong_snapshot.configuration_hash,
        prediction_ids=(),
    )
    success_snapshot = ExperimentArmConfigurationSnapshot.from_arm(arms[0])
    success = ExperimentExecutionRecord(
        execution_id="success",
        arm_id=arms[0].arm_id,
        arm_hash=arms[0].arm_hash,
        status=ExecutionStatus.EXECUTED,
        started_at=NOW,
        completed_at=NOW,
        technique_run_id="success-run",
        configuration_snapshot=success_snapshot,
        configuration_snapshot_hash=success_snapshot.configuration_hash,
    )
    with pytest.raises(ValidationError, match="snapshot"):
        ExperimentExecutionLedger(
            planned_arms=arms,
            records=(success, wrong_snapshot_failure),
        )
