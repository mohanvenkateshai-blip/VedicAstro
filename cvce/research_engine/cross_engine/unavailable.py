from __future__ import annotations

from .models import BodyCalculation, CalculationProfile, CalculationRequest, EngineCalculation


class UnavailableEngineAdapter:
    def __init__(self, profile: CalculationProfile | str, reason: str) -> None:
        self.profile = (
            profile
            if isinstance(profile, CalculationProfile)
            else CalculationProfile(
                profile_id=profile,
                engine_id=profile,
                engine_version="unavailable",
            )
        )
        self.reason = reason

    def calculate(self, request: CalculationRequest) -> EngineCalculation:
        return EngineCalculation(
            profile=self.profile,
            request_id=request.case_id,
            julian_day_ut=None,
            bodies=tuple(
                BodyCalculation(body, False, None, None, None, None, (self.reason,))
                for body in request.requested_bodies
            ),
            available=False,
            annotations=(self.reason,),
            provenance=("engine unavailable; result retained as an explicit research arm",),
        )
