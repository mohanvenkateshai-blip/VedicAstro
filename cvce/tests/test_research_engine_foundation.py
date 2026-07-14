from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from pydantic import ValidationError
from research_engine import (
    DEFAULT_EVENT_REGISTRY,
    DEFAULT_TIMING_REGISTRY,
    EventRegistry,
    EventRegistryEntry,
    ImmutableResearchStore,
    RawPrediction,
    RawScore,
    RawTiming,
    ResearchAnnotation,
    ResearchStoreConflict,
    ResearchStoreIntegrityError,
    ResearchStoreSchemaError,
    RunArtifactReference,
    RunStatus,
    TechniqueConfiguration,
    TechniqueItemError,
    TechniqueRun,
    TechniqueRunError,
    TimingTolerance,
    canonical_json,
    stable_hash,
)


def configuration() -> TechniqueConfiguration:
    return TechniqueConfiguration(
        configuration_id="cfg-vimshottari-001",
        technique_code="vimshottari_dasha",
        technique_version="parashara.variant-a.1",
        implementation_version="cvce-0.1.0",
        school_or_lineage="Parashara lineage, research source A",
        ayanamsa="lahiri",
        ephemeris="swiss-ephemeris-2.10",
        house_or_bhava_system="whole-sign-rashi",
        dasha_system="vimshottari",
        dasha_depth=3,
        parameters={"ayanamsa": "lahiri", "year_days": 365.25636},
        original_configuration_payload={
            "native_year_unit": "savanna-ish",
            "unmapped_switch": 7,
        },
    )


def prediction() -> RawPrediction:
    return RawPrediction(
        prediction_id="raw-prediction-001",
        source_item_key="rule-42",
        event_code="sensitive.health.mortality.native_source_code",
        original_event_label="Ayu indication",
        original_prose="Exact source wording — retained, not product output.",
        timing=RawTiming(
            kind="ghati",
            native_value="18 ghati after sunrise",
            timezone="Asia/Kolkata",
            tolerance=TimingTolerance(value="2", unit="ghati", direction="plus_or_minus"),
            original_payload={"ghati": 18, "anchor": "sunrise"},
        ),
        scores=(
            RawScore(
                score_code="bala",
                original_value="42/60",
                numeric_value=42.0,
                native_unit="shashtiamsa",
                formula_version="source-formula-v2",
                polarity_mapping={"above_40": "supporting", "below_20": "opposing"},
                normalization_metadata={
                    "normalized": False,
                    "reason": "native score retained",
                },
                original_payload={"numerator": 42, "denominator": 60},
            ),
        ),
        native_direction="dakshina",
        native_polarity="mishra",
        magnitude="madhyama",
        conditions=("Only when the source prerequisite is present.",),
        supporting_factor_refs=("raw-factor-1", "raw-factor-2"),
        opposing_factor_refs=("raw-factor-9",),
        original_payload={"rule": 42, "verdict": "mishra", "weight": -3},
    )


def run() -> TechniqueRun:
    raw_input = {"chart_ref": "deidentified-1", "native_flags": [1, 0, 1]}
    return TechniqueRun(
        run_id="run-001",
        configuration=configuration(),
        original_input_payload=raw_input,
        original_input_payload_hash=stable_hash(raw_input),
        event_registry_id="vedicastro-research-events",
        event_registry_version="1.0.0",
        event_registry_hash=DEFAULT_EVENT_REGISTRY.registry_hash,
        timing_registry_id="vedicastro-research-timing",
        timing_registry_version="1.0.0",
        timing_registry_hash=DEFAULT_TIMING_REGISTRY.registry_hash,
        started_at=datetime(2026, 7, 14, 10, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 14, 10, 1, tzinfo=UTC),
        status=RunStatus.PARTIAL,
        predictions=(prediction(),),
        item_errors=(
            TechniqueItemError(
                item_key="rule-99",
                phase="rule_evaluation",
                error_code="native_division_by_zero",
                message="Original technique item could not be evaluated.",
                original_item_payload={"rule": 99, "divisor": 0},
            ),
        ),
        run_metadata={"worker": "local", "seed": 20260714},
    )


def seed_default_registries(store: ImmutableResearchStore) -> None:
    store.append_event_registry(DEFAULT_EVENT_REGISTRY)
    store.append_timing_registry(DEFAULT_TIMING_REGISTRY)


def test_raw_contract_round_trip_is_lossless_and_deterministic():
    original = run()

    restored = TechniqueRun.model_validate_json(canonical_json(original))

    assert restored == original
    assert restored.predictions[0].original_prose == prediction().original_prose
    assert restored.predictions[0].scores[0].original_value == "42/60"
    assert restored.predictions[0].scores[0].formula_version == "source-formula-v2"
    assert restored.predictions[0].scores[0].normalization_metadata["normalized"] is False
    assert restored.predictions[0].native_polarity == "mishra"
    assert restored.predictions[0].magnitude == "madhyama"
    assert restored.predictions[0].supporting_factor_refs == ("raw-factor-1", "raw-factor-2")
    assert restored.configuration.school_or_lineage == "Parashara lineage, research source A"
    assert restored.configuration.dasha_depth == 3
    assert restored.configuration.configuration_hash == stable_hash(restored.configuration)
    assert restored.original_input_payload_hash == stable_hash(restored.original_input_payload)
    assert restored.event_registry_version == "1.0.0"
    assert stable_hash(restored) == stable_hash(original)
    assert stable_hash(original) == stable_hash(original)
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})


def test_scalar_and_list_native_payloads_round_trip_without_shape_coercion():
    original = run().model_copy(
        update={
            "configuration": configuration().model_copy(
                update={"original_configuration_payload": ["switch-a", 7, False]}
            ),
            "original_input_payload": ["native-chart", 12, {"flags": [1, 0]}],
            "original_input_payload_hash": stable_hash(["native-chart", 12, {"flags": [1, 0]}]),
            "predictions": (
                prediction().model_copy(
                    update={
                        "original_payload": "verbatim scalar prediction payload",
                        "scores": (
                            prediction()
                            .scores[0]
                            .model_copy(update={"original_payload": [42, 60, "native-pair"]}),
                        ),
                    }
                ),
            ),
            "item_errors": (
                run().item_errors[0].model_copy(update={"original_item_payload": [99, 0]}),
            ),
        }
    )

    restored = TechniqueRun.model_validate_json(canonical_json(original))

    assert restored == original
    assert restored.original_input_payload[0] == "native-chart"
    assert restored.configuration.original_configuration_payload == ["switch-a", 7, False]
    assert restored.predictions[0].original_payload == "verbatim scalar prediction payload"
    assert restored.predictions[0].scores[0].original_payload == [42, 60, "native-pair"]
    assert restored.item_errors[0].original_item_payload == [99, 0]


def test_failed_zero_prediction_run_and_external_snapshot_are_sealed():
    failed = run().model_copy(
        update={
            "run_id": "run-failed",
            "status": RunStatus.FAILED,
            "predictions": (),
            "item_errors": (),
            "run_errors": (
                TechniqueRunError(
                    phase="ephemeris_initialization",
                    error_code="ephemeris_unavailable",
                    message="Native technique could not start.",
                    retryable=True,
                    original_error_payload=["SE1", 503],
                ),
            ),
            "artifact_references": (
                RunArtifactReference(
                    artifact_id="stderr-001",
                    kind="stderr",
                    uri="research://runs/run-failed/stderr",
                    content_hash="b" * 64,
                ),
            ),
            "external_input_snapshot_ref": "research://snapshots/source-chart-001",
            "external_input_snapshot_hash": "c" * 64,
        }
    )

    restored = TechniqueRun.model_validate_json(canonical_json(failed))

    assert restored.status is RunStatus.FAILED
    assert restored.predictions == ()
    assert restored.run_errors[0].original_error_payload == ["SE1", 503]
    assert restored.external_input_snapshot_hash == "c" * 64
    assert restored.original_input_payload_hash == stable_hash(restored.original_input_payload)
    assert restored.original_input_payload_hash != restored.external_input_snapshot_hash


def test_declared_embedded_input_hash_mismatch_is_rejected():
    data = run().model_dump(mode="python")
    data["original_input_payload_hash"] = "f" * 64

    with pytest.raises(ValidationError, match="does not match original_input_payload"):
        TechniqueRun.model_validate(data)


def test_legacy_input_hash_alias_migrates_only_when_it_matches_embedded_payload():
    data = run().model_dump(mode="python")
    embedded_hash = data.pop("original_input_payload_hash")
    data["input_snapshot_hash"] = embedded_hash

    restored = TechniqueRun.model_validate(data)

    assert restored.original_input_payload_hash == embedded_hash
    assert "original_input_payload_hash" in restored.model_dump(mode="json")
    assert "input_snapshot_hash" not in restored.model_dump(mode="json")


def test_run_state_machine_is_fail_closed():
    partial = run()
    completed_with_errors = partial.model_dump(mode="python")
    completed_with_errors["status"] = RunStatus.COMPLETED
    with pytest.raises(ValidationError, match="completed run cannot contain"):
        TechniqueRun.model_validate(completed_with_errors)

    partial_without_predictions = partial.model_dump(mode="python")
    partial_without_predictions["predictions"] = ()
    with pytest.raises(ValidationError, match="partial run requires predictions"):
        TechniqueRun.model_validate(partial_without_predictions)

    failed_with_prediction = partial.model_dump(mode="python")
    failed_with_prediction.update(
        status=RunStatus.FAILED,
        item_errors=(),
        run_errors=(
            TechniqueRunError(
                phase="execution",
                error_code="failed",
                message="failed",
            ),
        ),
    )
    with pytest.raises(ValidationError, match="failed run requires zero predictions"):
        TechniqueRun.model_validate(failed_with_prediction)

    missing_external_hash = partial.model_dump(mode="python")
    missing_external_hash["external_input_snapshot_ref"] = "research://snapshot/one"
    with pytest.raises(ValidationError, match="reference and hash"):
        TechniqueRun.model_validate(missing_external_hash)


def test_timing_registry_covers_native_resolution_and_tolerance():
    required = {
        "instant",
        "minute",
        "ghati",
        "hora",
        "day",
        "tithi",
        "week",
        "fortnight",
        "month",
        "quarter",
        "year",
        "multiyear",
        "open",
        "native",
    }

    assert required <= {entry.code for entry in DEFAULT_TIMING_REGISTRY.entries}
    assert (
        RawTiming(kind="vendor_specific_nadi", native_value="3 nadi").kind == "vendor_specific_nadi"
    )
    assert DEFAULT_TIMING_REGISTRY.registry_hash == stable_hash(DEFAULT_TIMING_REGISTRY)


def test_event_registry_is_open_and_does_not_filter_sensitive_domains():
    registry = EventRegistry(
        registry_id="research-events",
        version="2026.07.14",
        entries=(
            EventRegistryEntry(
                code="health.mortality",
                domain="health",
                label="Mortality claim in source corpus",
                sensitive=True,
                metadata={"research_only": True},
            ),
        ),
    )

    assert registry.entries[0].code == "health.mortality"
    assert registry.registry_hash == stable_hash(registry)
    assert (
        RawPrediction(
            prediction_id="p-open",
            event_code="unknown.future.event",
            original_payload={"raw": True},
        ).event_code
        == "unknown.future.event"
    )


def test_default_event_registry_is_research_metadata_and_never_an_allowlist():
    domains = {entry.domain for entry in DEFAULT_EVENT_REGISTRY.entries}
    required_domains = {
        "health",
        "conception",
        "pregnancy",
        "childbirth",
        "injury",
        "accident",
        "violence",
        "crime",
        "legal",
        "relationships",
        "finance",
        "employment",
        "education",
        "property",
        "travel",
        "family",
        "spiritual",
    }

    assert required_domains <= domains
    assert DEFAULT_EVENT_REGISTRY.metadata["open_registry"] is True
    assert DEFAULT_EVENT_REGISTRY.metadata["is_allowlist"] is False
    assert DEFAULT_EVENT_REGISTRY.metadata["authorizes_product_output"] is False
    assert all(entry.metadata["research_only"] is True for entry in DEFAULT_EVENT_REGISTRY.entries)
    assert any(entry.sensitive for entry in DEFAULT_EVENT_REGISTRY.entries)
    assert "not a product allowlist" in (DEFAULT_EVENT_REGISTRY.description or "")


def test_store_replays_identical_run_and_enforces_append_only(tmp_path):
    database = tmp_path / "research.sqlite3"
    original = run()
    annotation = ResearchAnnotation(
        annotation_id="annotation-001",
        run_id=original.run_id,
        prediction_id=original.predictions[0].prediction_id,
        annotation_type="source_alignment",
        payload={"aligned": False, "reason": "translation ambiguity"},
        created_at=datetime(2026, 7, 14, 11, 0, tzinfo=UTC),
        actor_id="researcher-01",
    )

    with ImmutableResearchStore(database) as store:
        seed_default_registries(store)
        run_hash = store.append_run(original)
        annotation_hash = store.append_annotation(annotation)
        restored = store.replay_run(original.run_id)
        restored_annotation = store.replay_annotation(annotation.annotation_id)

        assert restored == original
        assert stable_hash(restored) == run_hash
        assert restored_annotation == annotation
        assert stable_hash(restored_annotation) == annotation_hash

        with pytest.raises(ResearchStoreConflict):
            store.append_run(original)
        with pytest.raises(ResearchStoreConflict):
            store.append_annotation(annotation)

    database_connection = sqlite3.connect(database)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only research store"):
            database_connection.execute(
                "UPDATE technique_runs SET payload_json = ? WHERE run_id = ?",
                ("{}", original.run_id),
            )
    finally:
        database_connection.close()


def test_annotation_supersession_requires_existing_same_run_prediction_lineage(tmp_path):
    original_run = run()
    second_run = run().model_copy(update={"run_id": "run-002"})
    first = ResearchAnnotation(
        annotation_id="annotation-first",
        run_id=original_run.run_id,
        prediction_id=original_run.predictions[0].prediction_id,
        annotation_type="source_alignment",
        payload={"state": "needs_review"},
        created_at=datetime(2026, 7, 14, 11, 0, tzinfo=UTC),
        actor_id="researcher-01",
    )
    replacement = ResearchAnnotation(
        annotation_id="annotation-replacement",
        run_id=original_run.run_id,
        prediction_id=original_run.predictions[0].prediction_id,
        annotation_type="source_alignment",
        payload={"state": "confirmed"},
        created_at=datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
        actor_id="researcher-02",
        supersedes_annotation_id=first.annotation_id,
    )

    with ImmutableResearchStore(tmp_path / "annotations.sqlite3") as store:
        seed_default_registries(store)
        store.append_run(original_run)
        store.append_run(second_run)
        store.append_annotation(first)
        store.append_annotation(replacement)

        assert store.replay_annotation(first.annotation_id) == first
        assert store.replay_annotation(replacement.annotation_id) == replacement

        missing_prior = replacement.model_copy(
            update={
                "annotation_id": "annotation-missing-prior",
                "supersedes_annotation_id": "annotation-does-not-exist",
            }
        )
        with pytest.raises(ResearchStoreConflict, match="does not exist"):
            store.append_annotation(missing_prior)

        cross_run = replacement.model_copy(
            update={
                "annotation_id": "annotation-cross-run",
                "run_id": second_run.run_id,
            }
        )
        with pytest.raises(ResearchStoreConflict, match="same run, prediction, and type"):
            store.append_annotation(cross_run)

        cross_type = replacement.model_copy(
            update={
                "annotation_id": "annotation-cross-type",
                "annotation_type": "different_research_question",
            }
        )
        with pytest.raises(ResearchStoreConflict, match="same run, prediction, and type"):
            store.append_annotation(cross_type)

        non_monotonic = replacement.model_copy(
            update={
                "annotation_id": "annotation-non-monotonic",
                "created_at": first.created_at,
                "supersedes_annotation_id": first.annotation_id,
            }
        )
        with pytest.raises(ResearchStoreConflict, match="created after its parent"):
            store.append_annotation(non_monotonic)

        second_successor = replacement.model_copy(
            update={
                "annotation_id": "annotation-second-successor",
                "created_at": datetime(2026, 7, 14, 13, 0, tzinfo=UTC),
            }
        )
        with pytest.raises(ResearchStoreConflict, match="parent already has a successor"):
            store.append_annotation(second_successor)


def test_store_versions_and_replays_open_registries(tmp_path):
    event_registry = EventRegistry(
        registry_id="event-research",
        version="1.0.0",
        entries=(EventRegistryEntry(code="custom.event", domain="custom", label="Custom event"),),
    )

    with ImmutableResearchStore(tmp_path / "registry.sqlite3") as store:
        store.append_event_registry(event_registry)
        store.append_timing_registry(DEFAULT_TIMING_REGISTRY)

        assert store.replay_event_registry("event-research", "1.0.0") == event_registry
        assert (
            store.replay_timing_registry(
                DEFAULT_TIMING_REGISTRY.registry_id, DEFAULT_TIMING_REGISTRY.version
            )
            == DEFAULT_TIMING_REGISTRY
        )

        with pytest.raises(ResearchStoreConflict):
            store.append_event_registry(event_registry)


def test_run_append_requires_existing_registry_versions_and_exact_hashes(tmp_path):
    database = tmp_path / "registry-binding.sqlite3"
    with ImmutableResearchStore(database) as store:
        with pytest.raises(ResearchStoreConflict, match="version does not exist"):
            store.append_run(run())

        seed_default_registries(store)
        mismatched = run().model_copy(
            update={"run_id": "run-bad-registry", "event_registry_hash": "f" * 64}
        )
        with pytest.raises(ResearchStoreConflict, match="hash does not match"):
            store.append_run(mismatched)

        missing_refs = run().model_copy(
            update={
                "run_id": "run-missing-refs",
                "event_registry_id": None,
                "event_registry_version": None,
                "event_registry_hash": None,
            }
        )
        with pytest.raises(ResearchStoreConflict, match="requires event and timing registry refs"):
            store.append_run(missing_refs)


def test_store_fails_closed_for_unjournaled_or_unknown_schema(tmp_path):
    legacy = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(legacy)
    connection.execute("CREATE TABLE technique_runs (run_id TEXT PRIMARY KEY)")
    connection.close()
    with pytest.raises(ResearchStoreSchemaError, match="unjournaled legacy"):
        ImmutableResearchStore(legacy)

    future = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(future)
    connection.execute(
        "CREATE TABLE research_schema_migrations "
        "(version INTEGER PRIMARY KEY, name TEXT, checksum TEXT, applied_at TEXT)"
    )
    connection.execute(
        "INSERT INTO research_schema_migrations VALUES (999, 'future', ?, ?)",
        ("f" * 64, datetime.now(UTC).isoformat()),
    )
    connection.commit()
    connection.close()
    with pytest.raises(ResearchStoreSchemaError, match="version or migration checksum mismatch"):
        ImmutableResearchStore(future)


def test_shared_store_serializes_concurrent_appends(tmp_path):
    with ImmutableResearchStore(tmp_path / "shared.sqlite3") as store:
        seed_default_registries(store)
        barrier = Barrier(4)

        def append(index: int) -> str:
            barrier.wait()
            return store.append_run(run().model_copy(update={"run_id": f"shared-{index}"}))

        with ThreadPoolExecutor(max_workers=4) as executor:
            hashes = tuple(executor.map(append, range(4)))

        assert len(set(hashes)) == 4
        assert all(
            store.replay_run(f"shared-{index}").run_id == f"shared-{index}" for index in range(4)
        )


def test_multiple_store_instances_handle_write_contention(tmp_path):
    database = tmp_path / "multi-instance.sqlite3"
    with ImmutableResearchStore(database) as setup:
        seed_default_registries(setup)

    first = ImmutableResearchStore(database)
    second = ImmutableResearchStore(database)
    barrier = Barrier(2)

    def append(store: ImmutableResearchStore, run_id: str) -> str:
        barrier.wait()
        return store.append_run(run().model_copy(update={"run_id": run_id}))

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(append, first, "multi-1"),
                executor.submit(append, second, "multi-2"),
            )
            hashes = tuple(future.result() for future in futures)
        assert len(set(hashes)) == 2
        assert first.replay_run("multi-2").run_id == "multi-2"
        assert second.replay_run("multi-1").run_id == "multi-1"
    finally:
        first.close()
        second.close()


def test_append_boundary_revalidates_bypassed_models_without_poisoning_store(tmp_path):
    database = tmp_path / "boundary.sqlite3"
    valid = run()
    with ImmutableResearchStore(database) as store:
        seed_default_registries(store)
        store.append_run(valid)

        tampered_hash = run().model_copy(
            update={
                "run_id": "tampered-hash",
                "original_input_payload": {"different": "payload"},
            }
        )
        with pytest.raises(ResearchStoreIntegrityError, match="persistence-boundary"):
            store.append_run(tampered_hash)

        contradictory_status = run().model_copy(
            update={"run_id": "contradictory-status", "status": RunStatus.COMPLETED}
        )
        with pytest.raises(ResearchStoreIntegrityError, match="persistence-boundary"):
            store.append_run(contradictory_status)

        invalid_annotation = ResearchAnnotation(
            annotation_id="valid-before-copy",
            run_id=valid.run_id,
            prediction_id=valid.predictions[0].prediction_id,
            annotation_type="review",
            payload={"state": "draft"},
            created_at=datetime(2026, 7, 14, 11, 0, tzinfo=UTC),
            actor_id="researcher",
        ).model_copy(update={"supersedes_annotation_id": "valid-before-copy"})
        with pytest.raises(ResearchStoreIntegrityError, match="persistence-boundary"):
            store.append_annotation(invalid_annotation)

        duplicate_event_registry = DEFAULT_EVENT_REGISTRY.model_copy(
            update={
                "registry_id": "invalid-event-registry",
                "entries": (
                    DEFAULT_EVENT_REGISTRY.entries[0],
                    DEFAULT_EVENT_REGISTRY.entries[0],
                ),
            }
        )
        duplicate_timing_registry = DEFAULT_TIMING_REGISTRY.model_copy(
            update={
                "registry_id": "invalid-timing-registry",
                "entries": (
                    DEFAULT_TIMING_REGISTRY.entries[0],
                    DEFAULT_TIMING_REGISTRY.entries[0],
                ),
            }
        )
        with pytest.raises(ResearchStoreIntegrityError, match="persistence-boundary"):
            store.append_event_registry(duplicate_event_registry)
        with pytest.raises(ResearchStoreIntegrityError, match="persistence-boundary"):
            store.append_timing_registry(duplicate_timing_registry)

        assert store.replay_run(valid.run_id) == valid
        with pytest.raises(KeyError):
            store.replay_run("tampered-hash")
        with pytest.raises(KeyError):
            store.replay_run("contradictory-status")


def test_concurrent_cold_open_serializes_schema_initialization(tmp_path):
    database = tmp_path / "cold-open.sqlite3"
    peers = 6
    barrier = Barrier(peers)

    def cold_open(_: int) -> None:
        barrier.wait()
        with ImmutableResearchStore(database):
            pass

    with ThreadPoolExecutor(max_workers=peers) as executor:
        tuple(executor.map(cold_open, range(peers)))

    connection = sqlite3.connect(database)
    try:
        journal = connection.execute(
            "SELECT version, name, COUNT(*) FROM research_schema_migrations GROUP BY version, name"
        ).fetchall()
        assert journal == [(1, "0001_immutable_research_store", 1)]
    finally:
        connection.close()
    with ImmutableResearchStore(database) as reopened:
        seed_default_registries(reopened)
        reopened.append_run(run())
        assert reopened.replay_run(run().run_id) == run()


@pytest.mark.parametrize(
    "tamper_sql, expected",
    (
        ("DROP TRIGGER technique_runs_no_update", "trigger set"),
        ("DROP INDEX research_annotations_one_successor", "uniqueness index"),
        ("ALTER TABLE technique_runs ADD COLUMN injected TEXT", "columns drifted"),
    ),
)
def test_schema_verification_rejects_physical_drift(tmp_path, tamper_sql, expected):
    database = tmp_path / f"schema-drift-{expected.replace(' ', '-')}.sqlite3"
    with ImmutableResearchStore(database):
        pass
    connection = sqlite3.connect(database)
    connection.execute(tamper_sql)
    connection.commit()
    connection.close()

    with pytest.raises(ResearchStoreSchemaError, match=expected):
        ImmutableResearchStore(database)


@pytest.mark.parametrize(
    "replacement_sql",
    (
        "CREATE TRIGGER technique_runs_no_update BEFORE UPDATE ON event_registries "
        "BEGIN SELECT RAISE(ABORT, 'append-only research store'); END",
        "CREATE TRIGGER technique_runs_no_update BEFORE UPDATE ON technique_runs WHEN 0 "
        "BEGIN SELECT RAISE(ABORT, 'append-only research store'); END",
        "CREATE TRIGGER technique_runs_no_update BEFORE UPDATE ON technique_runs "
        "BEGIN SELECT 1; SELECT RAISE(ABORT, 'append-only research store'); END",
    ),
)
def test_trigger_verification_rejects_swapped_targets_or_malicious_bodies(
    tmp_path, replacement_sql
):
    database = tmp_path / f"malicious-trigger-{stable_hash(replacement_sql)[:8]}.sqlite3"
    valid = run()
    with ImmutableResearchStore(database) as store:
        seed_default_registries(store)
        store.append_run(valid)

    connection = sqlite3.connect(database)
    connection.execute("DROP TRIGGER technique_runs_no_update")
    connection.execute(replacement_sql)
    connection.commit()
    connection.close()

    with pytest.raises(ResearchStoreSchemaError, match="trigger definition drifted"):
        ImmutableResearchStore(database)

    connection = sqlite3.connect(database)
    connection.execute("DROP TRIGGER technique_runs_no_update")
    connection.execute(
        "CREATE TRIGGER technique_runs_no_update BEFORE UPDATE ON technique_runs "
        "BEGIN SELECT RAISE(ABORT, 'append-only research store'); END"
    )
    connection.commit()
    connection.close()

    with ImmutableResearchStore(database) as restored:
        assert restored.replay_run(valid.run_id) == valid
    connection = sqlite3.connect(database)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only research store"):
            connection.execute(
                "UPDATE technique_runs SET payload_json = '{}' WHERE run_id = ?",
                (valid.run_id,),
            )
    finally:
        connection.close()
