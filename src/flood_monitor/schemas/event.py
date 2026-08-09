"""Consolidated flood-event and hydro-meteorological contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .common import BBox, JsonDict, Point, clamp01, stable_id, utc_now_iso
from .source import SourceRecord


@dataclass(slots=True)
class DepthObservation:
    location: Point | None
    time: str | None = None
    depth_m: float | None = None
    depth_range_m: tuple[float, float] | None = None
    method: str = "unknown"
    reference_object: str | None = None
    location_name: str | None = None
    evidence_ids: list[str] = field(default_factory=list)
    confidence: float = 0.5
    measured_or_inferred: Literal["measured", "inferred", "unknown"] = "unknown"

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class RainfallRecord:
    station_id: str
    time: str
    rainfall_mm: float
    duration_minutes: int = 60
    location: Point | None = None
    source: str = "unknown"

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class WaterLevelRecord:
    station_id: str
    time: str
    level_m: float
    datum: str | None = None
    location: Point | None = None
    source: str = "unknown"

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class TideRecord:
    station_id: str
    time: str
    tide_m: float
    datum: str | None = None
    location: Point | None = None
    source: str = "unknown"

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class FloodEvent:
    event_id: str
    name: str
    start_time: str
    end_time: str | None = None
    event_type: str = "flooding"
    region: str = "unknown"
    status: Literal["candidate", "confirmed", "archived", "rejected"] = "candidate"
    severity: Literal["unknown", "minor", "moderate", "severe", "extreme"] = "unknown"
    confidence: float = 0.5
    verification_status: str = "unverified"
    evidence_level: str = "weak"
    bbox: BBox | None = None
    flood_extent: JsonDict | None = None
    location_precision: str = "unknown"
    spatial_extent: JsonDict | None = None
    depth_observations: list[DepthObservation] = field(default_factory=list)
    rainfall_records: list[RainfallRecord] = field(default_factory=list)
    water_level_records: list[WaterLevelRecord] = field(default_factory=list)
    tide_records: list[TideRecord] = field(default_factory=list)
    evidence: list[SourceRecord] = field(default_factory=list)
    observation_ids: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    provenance: JsonDict = field(default_factory=dict)
    metadata: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.confidence = clamp01(self.confidence)
        if not self.source_ids:
            self.source_ids = [item.source_id or "" for item in self.evidence if item.source_id]
        self.provenance.setdefault("source_ids", list(self.source_ids))

    @classmethod
    def from_evidence(cls, evidence: SourceRecord, region: str = "Hong Kong") -> "FloodEvent":
        """Compatibility constructor for previously extracted evidence."""
        facts = evidence.extracted_facts
        start = facts.get("start_time") or evidence.observed_time or evidence.published_time or utc_now_iso()
        event = cls(
            event_id=stable_id("FM", region, start, evidence.location_name, evidence.url),
            name=facts.get("name") or f"Flood event near {evidence.location_name or region}",
            start_time=start,
            end_time=facts.get("end_time"),
            event_type=facts.get("event_type", "flooding"),
            region=region,
            severity=facts.get("severity", "unknown"),
            confidence=evidence.confidence,
            verification_status=facts.get("verification_status", "single_source"),
            evidence_level=facts.get("evidence_grade", "single_public_report"),
            bbox=evidence.bbox,
            flood_extent=facts.get("flood_extent"),
            location_precision=facts.get("location_precision", "point" if evidence.location else "area" if evidence.bbox else "unknown"),
            evidence=[evidence],
        )
        depth = facts.get("depth_observation")
        if isinstance(depth, dict):
            event.depth_observations.append(
                DepthObservation(
                    location=evidence.location,
                    time=depth.get("time") or evidence.observed_time,
                    depth_m=depth.get("depth_m"),
                    depth_range_m=tuple(depth["depth_range_m"]) if depth.get("depth_range_m") else None,
                    method=depth.get("method", "text"),
                    reference_object=depth.get("reference_object"),
                    location_name=evidence.location_name,
                    evidence_ids=[evidence.source_id or ""],
                    confidence=float(depth.get("confidence", evidence.confidence)),
                    measured_or_inferred=depth.get("measured_or_inferred", "inferred"),
                )
            )
        if event.bbox is None and evidence.location:
            lon, lat = evidence.location
            event.bbox = (lon, lat, lon, lat)
        return event

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FloodEvent":
        payload = dict(value)
        payload["depth_observations"] = [DepthObservation(**item) for item in payload.get("depth_observations", [])]
        payload["rainfall_records"] = [RainfallRecord(**item) for item in payload.get("rainfall_records", [])]
        payload["water_level_records"] = [WaterLevelRecord(**item) for item in payload.get("water_level_records", [])]
        payload["tide_records"] = [TideRecord(**item) for item in payload.get("tide_records", [])]
        payload["evidence"] = [SourceRecord.from_dict(item) for item in payload.get("evidence", [])]
        if isinstance(payload.get("bbox"), list):
            payload["bbox"] = tuple(payload["bbox"])
        known = {field.name for field in cls.__dataclass_fields__.values()}
        return cls(**{key: item for key, item in payload.items() if key in known})

    def to_dict(self) -> JsonDict:
        return asdict(self)
