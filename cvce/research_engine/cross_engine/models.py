"""Policy-neutral contracts for cross-engine calculation research."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class NodeMode(StrEnum):
    TRUE = "true"
    MEAN = "mean"


class CoordinateMode(StrEnum):
    GEOCENTRIC = "geocentric"
    TOPOCENTRIC = "topocentric"


class EphemerisPolicy(StrEnum):
    ALLOW_FALLBACK = "allow_fallback"
    REQUIRE_SWISS_FILE = "require_swiss_file"


class MotionState(StrEnum):
    DIRECT = "direct"
    STATIONARY = "stationary"
    RETROGRADE = "retrograde"


@dataclass(frozen=True, slots=True)
class CalculationProfile:
    profile_id: str
    engine_id: str
    engine_version: str
    ayanamsa: str = "lahiri"
    node_mode: NodeMode = NodeMode.TRUE
    coordinate_mode: CoordinateMode = CoordinateMode.GEOCENTRIC
    house_system: str = "P"
    topocentric_altitude_m: float = 0.0
    ephemeris_policy: EphemerisPolicy = EphemerisPolicy.ALLOW_FALLBACK
    ephemeris_path: str | None = None

    def __post_init__(self) -> None:
        if not self.profile_id or not self.engine_id or not self.engine_version:
            raise ValueError("profile and engine identities are required")
        if not isinstance(self.node_mode, NodeMode):
            raise TypeError("node_mode must be a NodeMode")
        if not isinstance(self.coordinate_mode, CoordinateMode):
            raise TypeError("coordinate_mode must be a CoordinateMode")
        if not isinstance(self.ephemeris_policy, EphemerisPolicy):
            raise TypeError("ephemeris_policy must be an EphemerisPolicy")
        if len(self.house_system) != 1 or not self.house_system.isascii():
            raise ValueError("house_system must be one ASCII Swiss house-system code")
        if not math.isfinite(self.topocentric_altitude_m):
            raise ValueError("topocentric altitude must be finite")
        object.__setattr__(self, "ayanamsa", self.ayanamsa.strip().lower())
        if self.topocentric_altitude_m == 0:
            object.__setattr__(self, "topocentric_altitude_m", 0.0)
        if self.ephemeris_path is not None:
            stripped_path = self.ephemeris_path.strip()
            canonical_path = (
                str(Path(stripped_path).expanduser().resolve()) if stripped_path else None
            )
            object.__setattr__(self, "ephemeris_path", canonical_path)

    @property
    def profile_hash(self) -> str:
        """Stable identity over every calculation-relevant profile field."""

        payload = {
            "engine_id": self.engine_id,
            "engine_version": self.engine_version,
            "ayanamsa": self.ayanamsa,
            "node_mode": self.node_mode.value,
            "coordinate_mode": self.coordinate_mode.value,
            "house_system": self.house_system,
            "topocentric_altitude_m": self.topocentric_altitude_m,
            "ephemeris_policy": self.ephemeris_policy.value,
            "ephemeris_path": self.ephemeris_path,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CalculationRequest:
    case_id: str
    instant: datetime
    latitude: float
    longitude: float
    requested_bodies: tuple[str, ...]
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.case_id or self.instant.tzinfo is None:
            raise ValueError("case_id and timezone-aware instant are required")
        if not -90 <= self.latitude <= 90 or not -180 <= self.longitude <= 180:
            raise ValueError("latitude or longitude is out of range")
        if not self.requested_bodies or len(set(self.requested_bodies)) != len(
            self.requested_bodies
        ):
            raise ValueError("requested_bodies must be non-empty and unique")


@dataclass(frozen=True, slots=True)
class LongitudeClassification:
    sign_index: int
    nakshatra_index: int
    pada: int


@dataclass(frozen=True, slots=True)
class BodyCalculation:
    body: str
    available: bool
    longitude_deg: float | None
    speed_longitude_deg_per_day: float | None
    retrograde: bool | None
    classification: LongitudeClassification | None
    annotations: tuple[str, ...] = ()
    motion_state: MotionState | None = None
    returned_flags: int | None = None

    def __post_init__(self) -> None:
        if not self.body:
            raise ValueError("body identity is required")
        values = (
            self.longitude_deg,
            self.speed_longitude_deg_per_day,
            self.retrograde,
            self.classification,
            self.motion_state,
        )
        if self.available and any(value is None for value in values):
            raise ValueError("available body requires position, speed, motion, and classification")
        if not self.available and any(value is not None for value in values):
            raise ValueError("unavailable body cannot contain calculated values")
        if self.longitude_deg is not None and not 0 <= self.longitude_deg < 360:
            raise ValueError("body longitude must be normalized")
        if self.speed_longitude_deg_per_day is not None and not math.isfinite(
            self.speed_longitude_deg_per_day
        ):
            raise ValueError("body speed must be finite")
        if self.motion_state is not None and self.retrograde != (
            self.motion_state is MotionState.RETROGRADE
        ):
            raise ValueError("retrograde flag must agree with motion state")


@dataclass(frozen=True, slots=True)
class EngineCalculation:
    profile: CalculationProfile
    request_id: str
    julian_day_ut: float | None
    bodies: tuple[BodyCalculation, ...]
    ascendant_deg: float | None = None
    house_cusps_deg: tuple[float, ...] = ()
    available: bool = True
    annotations: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    requested_flags: int | None = None
    returned_flags: tuple[int, ...] = ()
    ephemeris_backend: str | None = None
    ephemeris_files: tuple[str, ...] = ()
    degraded: bool = False

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request identity is required")
        body_ids = [body.body for body in self.bodies]
        if len(body_ids) != len(set(body_ids)):
            raise ValueError("engine calculation body identities must be unique")
        if not self.available and any(body.available for body in self.bodies):
            raise ValueError("unavailable engine calculation cannot contain available bodies")


@dataclass(frozen=True, slots=True)
class BodyDisagreement:
    left_profile_id: str
    right_profile_id: str
    body: str
    longitude_delta_arcsec: float | None
    sign_disagrees: bool | None
    nakshatra_disagrees: bool | None
    pada_disagrees: bool | None
    retrograde_disagrees: bool | None
    annotations: tuple[str, ...] = ()
    motion_state_disagrees: bool | None = None


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    request_id: str
    results: tuple[EngineCalculation, ...]
    disagreements: tuple[BodyDisagreement, ...]
    selected_profile_id: None = None

    def __post_init__(self) -> None:
        profile_ids = [result.profile.profile_id for result in self.results]
        if len(profile_ids) != len(set(profile_ids)):
            raise ValueError("comparison result profile IDs must be unique")
