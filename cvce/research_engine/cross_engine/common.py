from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Callable

from .models import LongitudeClassification, MotionState

STATIONARY_THRESHOLD_DEG_PER_DAY = 1.0 / 3600.0


def normalize_longitude(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("longitude must be finite")
    normalized = value % 360.0
    if normalized == 360.0:
        return math.nextafter(360.0, 0.0)
    return normalized


def classify_longitude(value: float) -> LongitudeClassification:
    longitude = normalize_longitude(value)
    sign = _partition_index(longitude, 12)
    nakshatra = _partition_index(longitude, 27)
    quarter = _partition_index(longitude, 108)
    return LongitudeClassification(
        sign_index=sign,
        nakshatra_index=nakshatra,
        pada=quarter % 4 + 1,
    )


def circular_delta_degrees(left: float, right: float) -> float:
    return (left - right + 540.0) % 360.0 - 180.0


def classify_motion(
    speed_deg_per_day: float,
    *,
    stationary_threshold_deg_per_day: float = STATIONARY_THRESHOLD_DEG_PER_DAY,
) -> MotionState:
    if not math.isfinite(speed_deg_per_day):
        raise ValueError("motion speed must be finite")
    if stationary_threshold_deg_per_day < 0:
        raise ValueError("stationary threshold cannot be negative")
    if abs(speed_deg_per_day) <= stationary_threshold_deg_per_day:
        return MotionState.STATIONARY
    if speed_deg_per_day < 0:
        return MotionState.RETROGRADE
    return MotionState.DIRECT


def estimate_daily_motion(
    position_at: Callable[[float], float],
    jd_ut: float,
    *,
    half_window_days: float = 0.05,
) -> float:
    if half_window_days <= 0:
        raise ValueError("motion sampling window must be positive")
    before = position_at(jd_ut - half_window_days)
    after = position_at(jd_ut + half_window_days)
    return circular_delta_degrees(after, before) / (2 * half_window_days)


def _partition_index(longitude: float, partitions: int) -> int:
    # The boundary table makes exact mathematical boundaries right-closed while
    # preserving the immediately adjacent representable floats on either side.
    boundaries = tuple(360.0 * index / partitions for index in range(partitions + 1))
    return bisect_right(boundaries, longitude) - 1
