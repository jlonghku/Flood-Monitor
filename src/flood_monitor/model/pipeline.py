"""Model execution boundary with explicit unavailable behavior."""

from __future__ import annotations

from typing import Any

from ..schemas import FloodEvent, FloodField, Observation
from .adapter import HydraulicModelAdapter, ModelNotConfiguredError


class FloodModelPipeline:
    def __init__(self, adapter: HydraulicModelAdapter | None = None) -> None:
        self.adapter = adapter

    def reconstruct(
        self,
        observations: list[Observation],
        events: list[FloodEvent],
        *,
        forcing: dict[str, Any] | None = None,
        run_id: str,
    ) -> list[FloodField]:
        if self.adapter is None:
            raise ModelNotConfiguredError(
                "Flood reconstruction is not configured. Provide a HydraulicModelAdapter and required terrain, drainage, boundary, and forcing data."
            )
        return self.adapter.reconstruct(observations=observations, events=events, forcing=forcing or {}, run_id=run_id)

    def forecast(
        self,
        current_state: list[FloodField],
        *,
        horizons_hours: list[int],
        forcing: dict[str, Any] | None = None,
        run_id: str,
    ) -> list[FloodField]:
        if self.adapter is None:
            raise ModelNotConfiguredError(
                "Flood forecasting is not configured. Provide a HydraulicModelAdapter plus forecast rainfall, tide, drainage state, and boundary conditions."
            )
        allowed = {0, 1, 3, 6}
        invalid = sorted(set(horizons_hours) - allowed)
        if invalid:
            raise ValueError(f"Unsupported forecast horizons: {invalid}; supported hours are 0, 1, 3, and 6")
        return self.adapter.forecast(
            current_state=current_state,
            horizons_hours=horizons_hours,
            forcing=forcing or {},
            run_id=run_id,
        )
