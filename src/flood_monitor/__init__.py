"""Flood Monitor public package."""

from .models import (
    DepthObservation,
    DrainageAssessment,
    Evidence,
    FloodEvent,
    FloodField,
    Observation,
    RainfallRecord,
    RunManifest,
    SourceRecord,
    TideRecord,
    WaterLevelRecord,
)

__all__ = [
    "FloodMonitor",
    "DepthObservation",
    "DrainageAssessment",
    "Evidence",
    "FloodEvent",
    "FloodField",
    "Observation",
    "RainfallRecord",
    "RunManifest",
    "SourceRecord",
    "TideRecord",
    "WaterLevelRecord",
]


def __getattr__(name: str):
    if name == "FloodMonitor":
        from .monitor import FloodMonitor

        return FloodMonitor
    raise AttributeError(name)
