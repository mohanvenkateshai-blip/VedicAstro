"""Optional jyotishganit research arm with explicit provenance limitations."""

from __future__ import annotations

import hashlib
from datetime import UTC, timedelta
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .common import circular_delta_degrees, classify_longitude, classify_motion
from .models import (
    BodyCalculation,
    CalculationProfile,
    CalculationRequest,
    CoordinateMode,
    EngineCalculation,
    MotionState,
    NodeMode,
)


class JyotishGanitAdapter:
    def __init__(self) -> None:
        try:
            package_version = version("jyotishganit")
        except PackageNotFoundError:
            package_version = "not-installed"
        self.profile = CalculationProfile(
            profile_id=f"jyotishganit:{package_version}:true-chitra:mean-node:de421",
            engine_id="jyotishganit",
            engine_version=package_version,
            ayanamsa="true_chitra_paksha",
            node_mode=NodeMode.MEAN,
            coordinate_mode=CoordinateMode.GEOCENTRIC,
            house_system="W",
        )

    def calculate(self, request: CalculationRequest) -> EngineCalculation:
        try:
            current, runtime_provenance = self._positions(request)
            utc = request.instant.astimezone(UTC)
            before = self._positions_at(request, utc - timedelta(minutes=30))
            after = self._positions_at(request, utc + timedelta(minutes=30))
        except Exception as exc:
            reason = f"jyotishganit unavailable: {type(exc).__name__}: {exc}"
            return EngineCalculation(
                self.profile,
                request.case_id,
                None,
                tuple(
                    BodyCalculation(body, False, None, None, None, None, (reason,))
                    for body in request.requested_bodies
                ),
                available=False,
                annotations=(reason,),
                provenance=("optional jyotishganit package",),
            )
        bodies = []
        for body in request.requested_bodies:
            longitude = current.get(body)
            if longitude is None:
                bodies.append(
                    BodyCalculation(body, False, None, None, None, None, ("body unavailable",))
                )
                continue
            # The samples are one hour apart; normalize the finite difference to
            # the same degrees-per-day unit exposed by Swiss Ephemeris.
            speed = 24 * circular_delta_degrees(
                after.get(body, longitude), before.get(body, longitude)
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
                    ("motion sampled at UTC +/-30 minutes",),
                    motion_state,
                )
            )
        return EngineCalculation(
            self.profile,
            request.case_id,
            None,
            tuple(bodies),
            provenance=(
                *runtime_provenance,
                "independent Skyfield/JPL calculation arm relative to Swiss Ephemeris",
            ),
        )

    def _positions_at(self, request: CalculationRequest, instant) -> dict[str, float]:
        shifted = CalculationRequest(
            request.case_id,
            instant,
            request.latitude,
            request.longitude,
            request.requested_bodies,
            request.tags,
        )
        return self._positions(shifted)[0]

    def _positions(self, request: CalculationRequest) -> tuple[dict[str, float], tuple[str, ...]]:
        import jyotishganit.main as jgm
        from jyotishganit import __version__ as module_version
        from jyotishganit.core import astronomical

        offset = request.instant.utcoffset()
        if offset is None:
            raise ValueError("timezone offset unavailable")
        chart = jgm.calculate_birth_chart(
            request.instant.replace(tzinfo=None),
            request.latitude,
            request.longitude,
            offset.total_seconds() / 3600,
        )
        payload = jgm.get_birth_chart_json(chart)
        ayanamsa = payload.get("ayanamsa", {})
        if ayanamsa.get("name") != "True Chitra Paksha":
            raise RuntimeError("unverified jyotishganit ayanamsa configuration")
        signs = (
            "Aries",
            "Taurus",
            "Gemini",
            "Cancer",
            "Leo",
            "Virgo",
            "Libra",
            "Scorpio",
            "Sagittarius",
            "Capricorn",
            "Aquarius",
            "Pisces",
        )
        result: dict[str, float] = {}
        for house in payload["d1Chart"]["houses"]:
            if house["sign"] not in signs:
                continue
            sign = signs.index(house["sign"])
            for occupant in house.get("occupants", ()):
                name = occupant.get("celestialBody")
                if name:
                    result[name] = sign * 30 + float(occupant["signDegrees"])
        ephemeris = astronomical.get_ephemeris()
        ephemeris_path = Path(str(getattr(ephemeris, "path", "")))
        if ephemeris_path.name != "de421.bsp" or not ephemeris_path.is_file():
            raise RuntimeError("jyotishganit JPL DE421 ephemeris is not locally verified")
        if "Rahu" not in result:
            raise RuntimeError("jyotishganit mean-node output is unavailable")
        skyfield_time = astronomical.skyfield_time_from_datetime(
            request.instant.replace(tzinfo=None), offset.total_seconds() / 3600
        )
        centuries = (skyfield_time.tt - 2451545.0) / 36525.0
        expected_rahu = (125.04452 - 1934.136261 * centuries - float(ayanamsa["value"])) % 360
        node_delta = abs(circular_delta_degrees(result["Rahu"], expected_rahu))
        if node_delta > 1e-7:
            raise RuntimeError("jyotishganit mean-node configuration could not be verified")
        provenance = (
            f"jyotishganit_distribution={self.profile.engine_version}",
            f"jyotishganit_module={module_version}",
            "ayanamsa=True Chitra Paksha (runtime verified)",
            "node_mode=mean (runtime numerically verified)",
            f"jpl_ephemeris={ephemeris_path}",
            f"jpl_ephemeris_sha256={_sha256(ephemeris_path)}",
        )
        return result, provenance


@lru_cache(maxsize=8)
def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
