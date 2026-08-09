"""Backward-compatible imports for canonical FloodMonitor schemas."""

from .schemas import (
    BBox,
    DepthObservation,
    DrainageAssessment,
    FloodEvent,
    FloodField,
    JsonDict,
    Observation,
    Point,
    RainfallRecord,
    RunManifest,
    SourceRecord,
    TideRecord,
    WaterLevelRecord,
    clamp01,
    stable_id,
    utc_now_iso,
)

Evidence = SourceRecord

__all__ = [
    "BBox",
    "DepthObservation",
    "DrainageAssessment",
    "Evidence",
    "FloodEvent",
    "FloodField",
    "JsonDict",
    "Observation",
    "Point",
    "RainfallRecord",
    "RunManifest",
    "SourceRecord",
    "TideRecord",
    "WaterLevelRecord",
    "clamp01",
    "stable_id",
    "utc_now_iso",
]
