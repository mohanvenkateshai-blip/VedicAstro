"""Adapter for the explicitly approximate preserved astronomy arm."""

from __future__ import annotations

from datetime import UTC

import swisseph as swe

from vedic_engine.core.astronomy import (
    LEGACY_APPROXIMATE_ENGINE_ID,
    LEGACY_APPROXIMATE_ENGINE_VERSION,
    ascendant,
    lahiri_ayanamsha,
    legacy_approximate_all_positions,
)

from .common import classify_longitude, classify_motion, estimate_daily_motion
from .models import (
    BodyCalculation,
    CalculationProfile,
    CalculationRequest,
    CoordinateMode,
    EngineCalculation,
    MotionState,
    NodeMode,
)


def legacy_approximate_profile() -> CalculationProfile:
    return CalculationProfile(
        profile_id="legacy-approximate:lahiri:true-node:geocentric",
        engine_id=LEGACY_APPROXIMATE_ENGINE_ID,
        engine_version=LEGACY_APPROXIMATE_ENGINE_VERSION,
        ayanamsa="simplified_lahiri",
        node_mode=NodeMode.TRUE,
        coordinate_mode=CoordinateMode.GEOCENTRIC,
        house_system="W",
    )


class LegacyApproximateAdapter:
    def __init__(self) -> None:
        self.profile = legacy_approximate_profile()

    def calculate(self, request: CalculationRequest) -> EngineCalculation:
        utc = request.instant.astimezone(UTC)
        hour = utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1e6) / 3600
        jd = swe.julday(utc.year, utc.month, utc.day, hour, swe.GREG_CAL)
        positions = legacy_approximate_all_positions(jd)
        bodies = []
        for body in request.requested_bodies:
            longitude = positions.get(body)
            if longitude is None:
                bodies.append(
                    BodyCalculation(body, False, None, None, None, None, ("unsupported body",))
                )
                continue
            speed = estimate_daily_motion(
                lambda sample_jd, body=body: legacy_approximate_all_positions(sample_jd)[body],
                jd,
            )
            motion_state = classify_motion(speed)
            bodies.append(
                BodyCalculation(
                    body,
                    True,
                    longitude,
                    speed,
                    motion_state is MotionState.RETROGRADE,
                    classify_longitude(longitude),
                    (
                        "approximate research arm; not Swiss Ephemeris",
                        "motion estimated by centered 0.1-day longitude difference",
                    ),
                    motion_state,
                )
            )
        ayanamsa = lahiri_ayanamsha(jd)
        return EngineCalculation(
            profile=self.profile,
            request_id=request.case_id,
            julian_day_ut=jd,
            bodies=tuple(bodies),
            ascendant_deg=ascendant(jd, request.latitude, request.longitude, ayanamsa),
            annotations=("houses are not calculated by the approximate arm",),
            provenance=(
                "Schlyter/ELP-style truncated approximation",
                "preserved for research comparison, not a precision reference",
                f"input_timezone={request.instant.tzinfo}",
            ),
        )
