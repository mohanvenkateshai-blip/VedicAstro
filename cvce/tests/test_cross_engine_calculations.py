from __future__ import annotations

import math
import os
import time
from datetime import UTC, datetime, timedelta
from itertools import combinations
from zoneinfo import ZoneInfo

import pytest
from cross_engine_reference_cases import REFERENCE_GROUPS, REFERENCE_PROVENANCE
from research_engine.cross_engine import (
    CalculationRequest,
    CoordinateMode,
    EphemerisPolicy,
    JyotishGanitAdapter,
    LegacyApproximateAdapter,
    MotionState,
    NodeMode,
    SwissEphemerisAdapter,
    UnavailableEngineAdapter,
    classify_longitude,
    compare_engines,
    swiss_profile,
)


def _request(group) -> CalculationRequest:
    case_id, instant, latitude, longitude, tags, expected = group
    return CalculationRequest(
        case_id=case_id,
        instant=datetime.fromisoformat(instant),
        latitude=latitude,
        longitude=longitude,
        requested_bodies=tuple(expected),
        tags=tags,
    )


def _body_map(result):
    return {body.body: body for body in result.bodies}


def test_circular_regression_fixture_is_explicitly_not_an_independent_oracle() -> None:
    assert sum(len(group[-1]) for group in REFERENCE_GROUPS) >= 30
    tags = {tag for group in REFERENCE_GROUPS for tag in group[4]}
    assert {"sign-boundary", "ingress", "station", "retrograde", "dst", "node"} <= tags
    assert "circular regression fixture" in " ".join(REFERENCE_PROVENANCE)
    assert "not an independent oracle" in " ".join(REFERENCE_PROVENANCE)


@pytest.mark.parametrize("group", REFERENCE_GROUPS, ids=lambda group: group[0])
def test_swiss_circular_regression_longitudes_are_stable(group) -> None:
    profile = swiss_profile(
        ephemeris_policy=EphemerisPolicy.REQUIRE_SWISS_FILE,
        ephemeris_path=os.environ.get("CVCE_SWISS_EPHEMERIS_PATH"),
    )
    result = SwissEphemerisAdapter(profile).calculate(_request(group))
    expected = group[-1]

    assert result.available, result.annotations
    assert result.ephemeris_backend == "swiss_ephemeris_file"
    assert result.profile.engine_version
    assert result.profile.node_mode is NodeMode.TRUE
    assert len(result.house_cusps_deg) == 12
    bodies = _body_map(result)
    for name, (longitude, speed, sign, nakshatra, pada) in expected.items():
        actual = bodies[name]
        assert actual.available
        delta = abs((actual.longitude_deg - longitude + 180) % 360 - 180)
        assert delta * 3600 <= 0.5
        assert actual.speed_longitude_deg_per_day == pytest.approx(speed, abs=5e-4)
        assert actual.classification.sign_index == sign
        assert actual.classification.nakshatra_index == nakshatra
        assert actual.classification.pada == pada


@pytest.mark.parametrize(
    ("longitude", "expected"),
    (
        (0.0, (0, 0, 1)),
        (30.0 - 1e-10, (0, 2, 1)),
        (30.0, (1, 2, 2)),
        (360.0, (0, 0, 1)),
        (13 + 1 / 3 - 1e-10, (0, 0, 4)),
        (13 + 1 / 3, (0, 1, 1)),
        (3 + 1 / 3 - 1e-10, (0, 0, 1)),
        (3 + 1 / 3, (0, 0, 2)),
    ),
)
def test_classification_is_deterministic_at_boundaries(longitude, expected) -> None:
    classification = classify_longitude(longitude)
    assert (
        classification.sign_index,
        classification.nakshatra_index,
        classification.pada,
    ) == expected


@pytest.mark.parametrize(
    ("partitions", "index_attribute"),
    ((12, "sign"), (27, "nakshatra"), (108, "quarter")),
)
def test_every_partition_boundary_is_exact_and_ulp_safe(partitions, index_attribute) -> None:
    def index(longitude: float) -> int:
        classification = classify_longitude(longitude)
        if index_attribute == "sign":
            return classification.sign_index
        if index_attribute == "nakshatra":
            return classification.nakshatra_index
        return classification.nakshatra_index * 4 + classification.pada - 1

    for boundary_index in range(1, partitions):
        boundary = 360.0 * boundary_index / partitions
        assert index(math.nextafter(boundary, -math.inf)) == boundary_index - 1
        assert index(boundary) == boundary_index
        assert index(math.nextafter(boundary, math.inf)) == boundary_index

    assert index(math.nextafter(0.0, -math.inf)) == partitions - 1
    assert index(0.0) == 0
    assert index(math.nextafter(0.0, math.inf)) == 0
    assert index(math.nextafter(360.0, -math.inf)) == partitions - 1
    assert index(360.0) == 0
    assert index(math.nextafter(360.0, math.inf)) == 0


def test_true_and_mean_node_profiles_remain_distinct() -> None:
    request = CalculationRequest(
        "node-modes",
        datetime.fromisoformat("2000-01-01T12:00:00+00:00"),
        0.0,
        0.0,
        ("Rahu", "Ketu"),
    )
    true_result = SwissEphemerisAdapter(swiss_profile(node_mode=NodeMode.TRUE)).calculate(request)
    mean_result = SwissEphemerisAdapter(swiss_profile(node_mode=NodeMode.MEAN)).calculate(request)

    assert true_result.profile.profile_id != mean_result.profile.profile_id
    assert _body_map(true_result)["Rahu"].longitude_deg != pytest.approx(
        _body_map(mean_result)["Rahu"].longitude_deg
    )
    for result in (true_result, mean_result):
        rahu = _body_map(result)["Rahu"].longitude_deg
        ketu = _body_map(result)["Ketu"].longitude_deg
        assert (ketu - rahu) % 360 == pytest.approx(180.0)


def test_topocentric_profile_changes_lunar_position() -> None:
    request = CalculationRequest(
        "coordinate-modes",
        datetime.fromisoformat("2024-04-13T20:30:00+05:30"),
        12.97,
        77.59,
        ("Moon",),
    )
    geocentric = SwissEphemerisAdapter().calculate(request)
    topocentric = SwissEphemerisAdapter(
        swiss_profile(
            coordinate_mode=CoordinateMode.TOPOCENTRIC,
            topocentric_altitude_m=920.0,
        )
    ).calculate(request)

    assert topocentric.profile.coordinate_mode is CoordinateMode.TOPOCENTRIC
    assert _body_map(geocentric)["Moon"].longitude_deg != pytest.approx(
        _body_map(topocentric)["Moon"].longitude_deg
    )
    assert geocentric.profile.profile_hash != topocentric.profile.profile_hash


def test_profile_identity_includes_altitude_and_every_ephemeris_choice() -> None:
    low = swiss_profile(
        coordinate_mode=CoordinateMode.TOPOCENTRIC,
        topocentric_altitude_m=10.0,
    )
    high = swiss_profile(
        coordinate_mode=CoordinateMode.TOPOCENTRIC,
        topocentric_altitude_m=11.0,
    )
    strict = swiss_profile(ephemeris_policy=EphemerisPolicy.REQUIRE_SWISS_FILE)

    assert low.profile_id != high.profile_id
    assert low.profile_hash != high.profile_hash
    assert strict.profile_hash != swiss_profile().profile_hash
    assert swiss_profile(ayanamsa=" LAHIRI ", topocentric_altitude_m=-0.0) == swiss_profile()


def test_swiss_records_requested_returned_flags_backend_and_files() -> None:
    request = CalculationRequest(
        "swiss-provenance",
        datetime.fromisoformat("2024-04-13T20:30:00+05:30"),
        12.97,
        77.59,
        ("Sun", "Moon"),
    )
    result = SwissEphemerisAdapter().calculate(request)

    assert result.requested_flags is not None
    assert len(result.returned_flags) == 2
    assert all(body.returned_flags is not None for body in result.bodies)
    assert result.ephemeris_backend in {
        "swiss_ephemeris_file",
        "moshier_fallback",
        "jpl_ephemeris_file",
    }
    assert "swisseph_library=" in " ".join(result.provenance)
    assert "ephemeris_backend=" in " ".join(result.provenance)
    assert all("path=" in record for record in result.ephemeris_files)
    assert result.degraded == (result.ephemeris_backend != "swiss_ephemeris_file")


def test_swiss_required_file_mode_fails_instead_of_silently_degrading(monkeypatch) -> None:
    import research_engine.cross_engine.swiss as swiss_module

    monkeypatch.setattr(swiss_module, "_combined_backend", lambda _flags: "moshier_fallback")
    request = CalculationRequest(
        "strict-swiss",
        datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        0.0,
        0.0,
        ("Sun",),
    )
    result = SwissEphemerisAdapter(
        swiss_profile(ephemeris_policy=EphemerisPolicy.REQUIRE_SWISS_FILE)
    ).calculate(request)

    assert not result.available
    assert result.degraded
    assert "required" in result.annotations[0]


def test_comparator_retains_every_result_disagreement_and_unavailability() -> None:
    request = CalculationRequest(
        "retain-all",
        datetime.fromisoformat("2024-04-13T20:30:00+05:30"),
        12.97,
        77.59,
        ("Sun", "Moon"),
    )
    adapters = (
        SwissEphemerisAdapter(),
        LegacyApproximateAdapter(),
        UnavailableEngineAdapter("independent-reference", "dependency not installed"),
    )
    report = compare_engines(request, adapters)

    assert len(report.results) == 3
    assert tuple(result.profile.profile_id for result in report.results) == tuple(
        adapter.profile.profile_id for adapter in adapters
    )
    assert report.selected_profile_id is None
    expected_pairs = len(tuple(combinations(adapters, 2)))
    assert len(report.disagreements) == expected_pairs * len(request.requested_bodies)
    unavailable = report.results[-1]
    assert not unavailable.available
    assert "dependency not installed" in unavailable.annotations
    related = [
        disagreement
        for disagreement in report.disagreements
        if "independent-reference" in disagreement.right_profile_id
    ]
    assert related
    assert all(item.longitude_delta_arcsec is None for item in related)
    assert all(item.annotations for item in related)


def test_comparator_reports_arcseconds_without_selecting_a_winner() -> None:
    request = CalculationRequest(
        "arcseconds",
        datetime.fromisoformat("2024-04-13T20:30:00+05:30"),
        12.97,
        77.59,
        ("Sun",),
    )
    swiss = SwissEphemerisAdapter()
    legacy = LegacyApproximateAdapter()
    left = _body_map(swiss.calculate(request))["Sun"].longitude_deg
    right = _body_map(legacy.calculate(request))["Sun"].longitude_deg
    report = compare_engines(request, (swiss, legacy))
    expected = abs((left - right + 180) % 360 - 180) * 3600

    assert report.disagreements[0].longitude_delta_arcsec == pytest.approx(expected)
    assert report.selected_profile_id is None


def test_comparator_rejects_duplicate_profile_ids_and_configurations() -> None:
    request = CalculationRequest(
        "duplicates",
        datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        0.0,
        0.0,
        ("Sun",),
    )
    first = SwissEphemerisAdapter()
    with pytest.raises(ValueError, match="profile IDs"):
        compare_engines(request, (first, first))

    same_config_new_id = type(first.profile)(
        profile_id="different-label",
        engine_id=first.profile.engine_id,
        engine_version=first.profile.engine_version,
        ayanamsa=first.profile.ayanamsa,
        node_mode=first.profile.node_mode,
        coordinate_mode=first.profile.coordinate_mode,
        house_system=first.profile.house_system,
        topocentric_altitude_m=first.profile.topocentric_altitude_m,
        ephemeris_policy=first.profile.ephemeris_policy,
        ephemeris_path=first.profile.ephemeris_path,
    )
    with pytest.raises(ValueError, match="configuration-unique"):
        compare_engines(request, (first, SwissEphemerisAdapter(same_config_new_id)))


@pytest.mark.parametrize("failure", (RuntimeError("boom"), TimeoutError("slow")))
def test_comparator_retains_exception_and_timeout_arms_as_unavailable(failure) -> None:
    class FailingAdapter:
        profile = swiss_profile(ayanamsa="raman")

        def calculate(self, _request):
            raise failure

    request = CalculationRequest(
        "failed-arm",
        datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        0.0,
        0.0,
        ("Sun",),
    )
    report = compare_engines(request, (SwissEphemerisAdapter(), FailingAdapter()))

    assert len(report.results) == 2
    assert not report.results[1].available
    assert type(failure).__name__ in report.results[1].annotations[0]
    assert report.disagreements[0].longitude_delta_arcsec is None


def test_comparator_retains_malformed_arm_as_unavailable() -> None:
    class MalformedAdapter:
        profile = swiss_profile(ayanamsa="raman")

        def calculate(self, _request):
            return {"not": "an EngineCalculation"}

    request = CalculationRequest(
        "malformed-arm",
        datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        0.0,
        0.0,
        ("Sun",),
    )
    result = compare_engines(request, (SwissEphemerisAdapter(), MalformedAdapter())).results[1]

    assert not result.available
    assert "malformed adapter result" in result.annotations[0]


def test_comparator_enforces_timeout_and_retains_slow_arm() -> None:
    class SlowAdapter:
        profile = swiss_profile(ayanamsa="raman")

        def calculate(self, _request):
            time.sleep(0.2)
            raise AssertionError("late result must not replace timeout record")

    request = CalculationRequest(
        "slow-arm",
        datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        0.0,
        0.0,
        ("Sun",),
    )
    started = time.monotonic()
    result = compare_engines(
        request,
        (SwissEphemerisAdapter(), SlowAdapter()),
        timeout_seconds=0.02,
    ).results[1]

    assert time.monotonic() - started < 0.15
    assert not result.available
    assert "adapter timeout" in result.annotations[0]


def test_unsupported_swiss_profile_is_explicitly_unavailable() -> None:
    profile = swiss_profile()
    invalid = type(profile)(
        profile_id="swiss:unsupported",
        engine_id=profile.engine_id,
        engine_version=profile.engine_version,
        ayanamsa="not-a-real-ayanamsa",
    )
    request = CalculationRequest(
        "unsupported",
        datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        0.0,
        0.0,
        ("Sun",),
    )
    result = SwissEphemerisAdapter(invalid).calculate(request)

    assert not result.available
    assert result.bodies[0].annotations == ("unsupported Swiss ayanamsa",)


def test_jyotishganit_arm_never_claims_unaudited_independence() -> None:
    request = CalculationRequest(
        "jyotishganit",
        datetime.fromisoformat("2024-04-13T20:30:00+05:30"),
        12.97,
        77.59,
        ("Sun", "Moon"),
    )
    result = JyotishGanitAdapter().calculate(request)

    if result.available:
        assert result.profile.engine_version not in {"installed-package", "not-installed"}
        assert result.profile.node_mode is NodeMode.MEAN
        assert "runtime verified" in " ".join(result.provenance)
        assert "jpl_ephemeris_sha256=" in " ".join(result.provenance)
        assert all(body.speed_longitude_deg_per_day is not None for body in result.bodies)
    else:
        assert result.annotations


def test_jyotishganit_motion_samples_are_shifted_in_utc() -> None:
    class RecordingAdapter(JyotishGanitAdapter):
        def __init__(self):
            super().__init__()
            self.instants = []

        def _positions(self, request):
            self.instants.append(request.instant)
            longitude = request.instant.astimezone(UTC).timestamp() / 86400 % 360
            return {"Sun": longitude}, ("verified test double",)

    adapter = RecordingAdapter()
    request = CalculationRequest(
        "dst-sampling",
        datetime(2024, 3, 31, 1, 30, tzinfo=ZoneInfo("Europe/Dublin")),
        53.35,
        -6.26,
        ("Sun",),
    )
    result = adapter.calculate(request)

    assert result.available
    assert adapter.instants[1].tzinfo is UTC
    assert adapter.instants[2].tzinfo is UTC
    assert adapter.instants[2] - adapter.instants[1] == timedelta(hours=1)


def test_motion_state_uses_one_stationary_threshold_across_arms() -> None:
    request = CalculationRequest(
        "stationary",
        datetime.fromisoformat("2024-04-25T08:54:00-04:00"),
        40.71,
        -74.0,
        ("Mercury",),
    )
    swiss = SwissEphemerisAdapter().calculate(request).bodies[0]
    legacy = LegacyApproximateAdapter().calculate(request).bodies[0]

    assert swiss.motion_state is MotionState.STATIONARY
    for body in (swiss, legacy):
        assert body.retrograde == (body.motion_state is MotionState.RETROGRADE)


def test_legacy_arm_is_explicitly_approximate() -> None:
    adapter = LegacyApproximateAdapter()
    assert "approx" in adapter.profile.engine_id
    assert "legacy" in adapter.profile.profile_id


def test_legacy_node_has_no_unsupported_swiss_accuracy_claim() -> None:
    from vedic_engine.core.astronomy import rahu_true_tropical

    assert "Matches Swiss" not in (rahu_true_tropical.__doc__ or "")
