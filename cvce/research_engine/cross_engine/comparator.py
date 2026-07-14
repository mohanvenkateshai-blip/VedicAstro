"""Deterministic comparison that retains all arms and never selects a winner."""

from __future__ import annotations

from itertools import combinations
from queue import Queue
from threading import Thread
from typing import Protocol

from .common import circular_delta_degrees, classify_longitude
from .models import (
    BodyCalculation,
    BodyDisagreement,
    CalculationProfile,
    CalculationRequest,
    ComparisonReport,
    EngineCalculation,
)


class CalculationAdapter(Protocol):
    profile: CalculationProfile

    def calculate(self, request: CalculationRequest) -> EngineCalculation: ...


def compare_engines(
    request: CalculationRequest,
    adapters: tuple[CalculationAdapter, ...],
    *,
    timeout_seconds: float | None = None,
) -> ComparisonReport:
    if not adapters:
        raise ValueError("at least one calculation adapter is required")
    if timeout_seconds is not None and timeout_seconds <= 0:
        raise ValueError("adapter timeout must be positive")
    profiles = tuple(_require_profile(adapter) for adapter in adapters)
    profile_ids = [profile.profile_id for profile in profiles]
    profile_hashes = [profile.profile_hash for profile in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise ValueError("calculation adapter profile IDs must be unique")
    if len(profile_hashes) != len(set(profile_hashes)):
        raise ValueError("calculation adapter profiles must be configuration-unique")
    results = tuple(
        _calculate_or_unavailable(adapter, profile, request, timeout_seconds)
        for adapter, profile in zip(adapters, profiles, strict=True)
    )
    disagreements: list[BodyDisagreement] = []
    for left, right in combinations(results, 2):
        left_bodies = {body.body: body for body in left.bodies}
        right_bodies = {body.body: body for body in right.bodies}
        for body in request.requested_bodies:
            disagreements.append(
                _compare_body(
                    left.profile.profile_id,
                    right.profile.profile_id,
                    body,
                    left_bodies.get(body),
                    right_bodies.get(body),
                )
            )
    return ComparisonReport(request.case_id, results, tuple(disagreements))


def _compare_body(
    left_profile: str,
    right_profile: str,
    body: str,
    left: BodyCalculation | None,
    right: BodyCalculation | None,
) -> BodyDisagreement:
    if left is None or right is None or not left.available or not right.available:
        return BodyDisagreement(
            left_profile,
            right_profile,
            body,
            None,
            None,
            None,
            None,
            None,
            ("one or both engine results are unavailable; neither was discarded",),
        )
    assert left.longitude_deg is not None and right.longitude_deg is not None
    assert left.classification is not None and right.classification is not None
    return BodyDisagreement(
        left_profile,
        right_profile,
        body,
        abs(circular_delta_degrees(left.longitude_deg, right.longitude_deg)) * 3600.0,
        left.classification.sign_index != right.classification.sign_index,
        left.classification.nakshatra_index != right.classification.nakshatra_index,
        left.classification.pada != right.classification.pada,
        left.retrograde != right.retrograde,
        motion_state_disagrees=left.motion_state != right.motion_state,
    )


def _require_profile(adapter: CalculationAdapter) -> CalculationProfile:
    profile = getattr(adapter, "profile", None)
    if not isinstance(profile, CalculationProfile):
        raise TypeError("each calculation adapter requires a CalculationProfile")
    return profile


def _calculate_or_unavailable(
    adapter: CalculationAdapter,
    profile: CalculationProfile,
    request: CalculationRequest,
    timeout_seconds: float | None,
) -> EngineCalculation:
    if timeout_seconds is not None:
        completed: Queue[tuple[bool, object]] = Queue(maxsize=1)

        def invoke() -> None:
            try:
                completed.put((True, adapter.calculate(request)))
            except Exception as exc:
                completed.put((False, exc))

        worker = Thread(
            target=invoke,
            name=f"calculation-{profile.profile_id}",
            daemon=True,
        )
        worker.start()
        worker.join(timeout_seconds)
        if worker.is_alive():
            return _unavailable_result(
                profile,
                request,
                f"adapter timeout: exceeded {timeout_seconds} seconds",
            )
        succeeded, value = completed.get_nowait()
        if not succeeded:
            assert isinstance(value, Exception)
            return _exception_result(profile, request, value)
        result = value
    else:
        try:
            result = adapter.calculate(request)
        except Exception as exc:
            return _exception_result(profile, request, exc)
    malformed = _malformed_reason(result, profile, request)
    if malformed is not None:
        return _unavailable_result(profile, request, f"malformed adapter result: {malformed}")
    assert isinstance(result, EngineCalculation)
    return result


def _exception_result(
    profile: CalculationProfile,
    request: CalculationRequest,
    exc: Exception,
) -> EngineCalculation:
    kind = "timeout" if isinstance(exc, TimeoutError) else "exception"
    return _unavailable_result(
        profile,
        request,
        f"adapter {kind}: {type(exc).__name__}: {exc}",
    )


def _malformed_reason(
    result: object,
    profile: CalculationProfile,
    request: CalculationRequest,
) -> str | None:
    if not isinstance(result, EngineCalculation):
        return "result is not an EngineCalculation"
    if result.profile != profile:
        return "result profile does not match adapter profile"
    if result.request_id != request.case_id:
        return "result request ID does not match request"
    body_ids = tuple(body.body for body in result.bodies)
    if len(body_ids) != len(set(body_ids)):
        return "result body identities are duplicated"
    if body_ids != request.requested_bodies:
        return "result bodies do not exactly match requested body order"
    for body in result.bodies:
        if body.available:
            if body.longitude_deg is None or body.classification is None:
                return f"available body {body.body} is incomplete"
            if body.classification != classify_longitude(body.longitude_deg):
                return f"body {body.body} classification does not match longitude"
    body_flags = tuple(
        body.returned_flags for body in result.bodies if body.returned_flags is not None
    )
    if result.available and body_flags != result.returned_flags:
        return "aggregate returned flags do not match body returned flags"
    return None


def _unavailable_result(
    profile: CalculationProfile,
    request: CalculationRequest,
    reason: str,
) -> EngineCalculation:
    return EngineCalculation(
        profile=profile,
        request_id=request.case_id,
        julian_day_ut=None,
        bodies=tuple(
            BodyCalculation(body, False, None, None, None, None, (reason,))
            for body in request.requested_bodies
        ),
        available=False,
        annotations=(reason,),
        provenance=("comparator retained failed adapter arm as unavailable",),
    )
