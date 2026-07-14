"""High-precision Swiss Ephemeris research adapter."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from threading import RLock

import swisseph as swe

from .common import classify_longitude, classify_motion, estimate_daily_motion, normalize_longitude
from .models import (
    BodyCalculation,
    CalculationProfile,
    CalculationRequest,
    CoordinateMode,
    EngineCalculation,
    EphemerisPolicy,
    MotionState,
    NodeMode,
)

_SWE_LOCK = RLock()
_AYANAMSA = {
    "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,
}
_BODY_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
}


def swiss_profile(
    *,
    ayanamsa: str = "lahiri",
    node_mode: NodeMode = NodeMode.TRUE,
    coordinate_mode: CoordinateMode = CoordinateMode.GEOCENTRIC,
    house_system: str = "P",
    topocentric_altitude_m: float = 0.0,
    ephemeris_policy: EphemerisPolicy = EphemerisPolicy.ALLOW_FALLBACK,
    ephemeris_path: str | None = None,
) -> CalculationProfile:
    normalized_altitude = 0.0 if topocentric_altitude_m == 0 else topocentric_altitude_m
    normalized_ayanamsa = ayanamsa.strip().lower()
    normalized_path = str(Path(ephemeris_path).expanduser().resolve()) if ephemeris_path else None
    altitude = format(normalized_altitude, ".12g")
    path_identity = normalized_path or "default"
    return CalculationProfile(
        profile_id=(
            f"swiss:{normalized_ayanamsa}:{node_mode.value}:{coordinate_mode.value}:alt-{altitude}:"
            f"houses-{house_system}:ephe-{ephemeris_policy.value}:path-{path_identity}"
        ),
        engine_id="swiss_ephemeris",
        engine_version=str(swe.version),
        ayanamsa=normalized_ayanamsa,
        node_mode=node_mode,
        coordinate_mode=coordinate_mode,
        house_system=house_system,
        topocentric_altitude_m=normalized_altitude,
        ephemeris_policy=ephemeris_policy,
        ephemeris_path=normalized_path,
    )


class SwissEphemerisAdapter:
    def __init__(self, profile: CalculationProfile | None = None) -> None:
        self.profile = profile or swiss_profile()

    def calculate(self, request: CalculationRequest) -> EngineCalculation:
        ayanamsa_mode = _AYANAMSA.get(self.profile.ayanamsa.lower())
        if ayanamsa_mode is None:
            return _unavailable(self.profile, request, "unsupported Swiss ayanamsa")
        utc = request.instant.astimezone(UTC)
        hour = utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1e6) / 3600
        jd = swe.julday(utc.year, utc.month, utc.day, hour, swe.GREG_CAL)
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        with _SWE_LOCK:
            if self.profile.ephemeris_path is not None:
                swe.set_ephe_path(self.profile.ephemeris_path)
            swe.set_sid_mode(ayanamsa_mode)
            if self.profile.coordinate_mode is CoordinateMode.TOPOCENTRIC:
                swe.set_topo(
                    request.longitude,
                    request.latitude,
                    self.profile.topocentric_altitude_m,
                )
                flags |= swe.FLG_TOPOCTR
            bodies = tuple(
                self._body(requested, jd, flags) for requested in request.requested_bodies
            )
            returned_flags = tuple(
                body.returned_flags for body in bodies if body.returned_flags is not None
            )
            backend = _combined_backend(returned_flags)
            file_provenance = _ephemeris_file_provenance()
            if (
                self.profile.ephemeris_policy is EphemerisPolicy.REQUIRE_SWISS_FILE
                and backend != "swiss_ephemeris_file"
            ):
                return _unavailable(
                    self.profile,
                    request,
                    "Swiss ephemeris file required but calculation degraded to "
                    f"{backend or 'unknown backend'}",
                    julian_day_ut=jd,
                    requested_flags=flags,
                    returned_flags=returned_flags,
                    backend=backend,
                    ephemeris_files=file_provenance,
                )
            try:
                cusps, ascmc = swe.houses_ex(
                    jd,
                    request.latitude,
                    request.longitude,
                    self.profile.house_system.encode("ascii"),
                    swe.FLG_SIDEREAL,
                )
                house_cusps = tuple(normalize_longitude(value) for value in cusps)
                ascendant = normalize_longitude(ascmc[0])
                house_annotations: tuple[str, ...] = ()
            except swe.Error as exc:
                house_cusps = ()
                ascendant = None
                house_annotations = (f"Swiss houses unavailable: {exc}",)
        return EngineCalculation(
            profile=self.profile,
            request_id=request.case_id,
            julian_day_ut=jd,
            bodies=bodies,
            ascendant_deg=ascendant,
            house_cusps_deg=house_cusps,
            annotations=house_annotations,
            provenance=(
                f"pyswisseph={swe.version}",
                f"requested_flags={flags}",
                f"returned_flags={','.join(str(item) for item in returned_flags)}",
                f"ephemeris_backend={backend}",
                f"requested_ephemeris_path={self.profile.ephemeris_path or 'library-default'}",
                f"swisseph_library={swe.get_library_path()}",
                *(f"ephemeris_file={item}" for item in file_provenance),
                "comparison with PyJHora is not independent when both use Swiss Ephemeris",
                f"input_timezone={request.instant.tzinfo}",
                f"input_utc={utc.isoformat()}",
            ),
            requested_flags=flags,
            returned_flags=returned_flags,
            ephemeris_backend=backend,
            ephemeris_files=file_provenance,
            degraded=backend != "swiss_ephemeris_file",
        )

    def _body(self, body: str, jd: float, flags: int) -> BodyCalculation:
        requested = body
        ketu = body == "Ketu"
        if body in {"Rahu", "Ketu"}:
            body_id = swe.TRUE_NODE if self.profile.node_mode is NodeMode.TRUE else swe.MEAN_NODE
        else:
            body_id = _BODY_IDS.get(body)
        if body_id is None:
            return BodyCalculation(body, False, None, None, None, None, ("unsupported body",))
        try:
            values, returned_flags = swe.calc_ut(jd, body_id, flags)
        except swe.Error as exc:
            return BodyCalculation(body, False, None, None, None, None, (str(exc),))
        longitude = normalize_longitude(values[0] + (180.0 if ketu else 0.0))
        try:
            speed = estimate_daily_motion(
                lambda sample_jd: normalize_longitude(
                    swe.calc_ut(sample_jd, body_id, flags)[0][0] + (180.0 if ketu else 0.0)
                ),
                jd,
            )
        except swe.Error as exc:
            return BodyCalculation(body, False, None, None, None, None, (str(exc),))
        motion_state = classify_motion(speed)
        return BodyCalculation(
            requested,
            True,
            longitude,
            speed,
            motion_state is MotionState.RETROGRADE,
            classify_longitude(longitude),
            (f"returned_flags={returned_flags}", f"backend={_backend(returned_flags)}"),
            motion_state,
            returned_flags,
        )


def _unavailable(
    profile: CalculationProfile,
    request: CalculationRequest,
    reason: str,
    *,
    julian_day_ut: float | None = None,
    requested_flags: int | None = None,
    returned_flags: tuple[int, ...] = (),
    backend: str | None = None,
    ephemeris_files: tuple[str, ...] = (),
) -> EngineCalculation:
    return EngineCalculation(
        profile=profile,
        request_id=request.case_id,
        julian_day_ut=julian_day_ut,
        bodies=tuple(
            BodyCalculation(body, False, None, None, None, None, (reason,))
            for body in request.requested_bodies
        ),
        available=False,
        annotations=(reason,),
        provenance=(
            f"pyswisseph={swe.version}",
            f"swisseph_library={swe.get_library_path()}",
            f"ephemeris_backend={backend}",
            *(f"ephemeris_file={item}" for item in ephemeris_files),
        ),
        requested_flags=requested_flags,
        returned_flags=returned_flags,
        ephemeris_backend=backend,
        ephemeris_files=ephemeris_files,
        degraded=backend not in (None, "swiss_ephemeris_file"),
    )


def _backend(returned_flags: int) -> str:
    if returned_flags & swe.FLG_JPLEPH:
        return "jpl_ephemeris_file"
    if returned_flags & swe.FLG_SWIEPH:
        return "swiss_ephemeris_file"
    if returned_flags & swe.FLG_MOSEPH:
        return "moshier_fallback"
    return "unknown"


def _combined_backend(returned_flags: tuple[int, ...]) -> str | None:
    backends = {_backend(flags) for flags in returned_flags}
    if not backends:
        return None
    if len(backends) == 1:
        return next(iter(backends))
    return "mixed:" + ",".join(sorted(backends))


def _ephemeris_file_provenance() -> tuple[str, ...]:
    records: list[str] = []
    for file_index in (0, 1):
        try:
            filename, start_jd, end_jd, de_number = swe.get_current_file_data(file_index)
        except swe.Error as exc:
            records.append(f"index={file_index}|error={exc}")
            continue
        if filename:
            records.append(
                f"index={file_index}|path={filename}|exists={Path(filename).is_file()}|"
                f"start_jd={start_jd}|end_jd={end_jd}|de={de_number}"
            )
    return tuple(records)
