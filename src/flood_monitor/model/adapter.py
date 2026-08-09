"""Adapter contract for external hydraulic or surrogate models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..schemas import FloodEvent, FloodField, Observation


class ModelNotConfiguredError(RuntimeError):
    """Raised when reconstruction or forecast is requested without an adapter."""


class HydraulicModelAdapter(ABC):
    """Integrate a model without coupling FloodMonitor to one engine."""

    name = "unconfigured"
    version = "unknown"

    @abstractmethod
    def reconstruct(
        self,
        *,
        observations: list[Observation],
        events: list[FloodEvent],
        forcing: dict[str, Any],
        run_id: str,
    ) -> list[FloodField]:
        raise NotImplementedError

    @abstractmethod
    def forecast(
        self,
        *,
        current_state: list[FloodField],
        horizons_hours: list[int],
        forcing: dict[str, Any],
        run_id: str,
    ) -> list[FloodField]:
        raise NotImplementedError
