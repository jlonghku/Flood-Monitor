"""Auditable extraction and evidence-fusion workflow."""

from __future__ import annotations

from dataclasses import dataclass

from ..extractors import TextFloodExtractor
from ..fusion import FloodFusionEngine
from ..schemas import FloodEvent, Observation, RainfallRecord, SourceRecord, WaterLevelRecord


@dataclass(slots=True)
class ExtractionResult:
    observations: list[Observation]
    events: list[FloodEvent]
    context_records: list[SourceRecord]


class ExtractionPipeline:
    def __init__(self, region: str = "Hong Kong") -> None:
        self.region = region
        self.text = TextFloodExtractor()
        self.fusion = FloodFusionEngine(region=region)

    def extract(self, records: list[SourceRecord]) -> ExtractionResult:
        observations: list[Observation] = []
        flood_records: dict[str, SourceRecord] = {}
        context_records: list[SourceRecord] = []
        for record in records:
            extracted = self.text.extract(record)
            observation = self.text.to_observation(extracted)
            if observation is None:
                context_records.append(extracted)
                continue
            observations.append(observation)
            if extracted.source_id:
                flood_records[extracted.source_id] = extracted
        events = self.fusion.fuse_observations(observations, flood_records)
        self._attach_context(events, context_records)
        return ExtractionResult(observations, events, context_records)

    def _attach_context(self, events: list[FloodEvent], records: list[SourceRecord]) -> None:
        """Attach environmental context only after direct flood events exist."""
        if not events:
            return
        for record in records:
            facts = record.extracted_facts
            rainfall = facts.get("rainfall_record")
            if isinstance(rainfall, dict):
                target = self._context_target(events, record)
                target.rainfall_records.append(
                    RainfallRecord(
                        station_id=str(rainfall.get("station_id") or record.location_name or "unknown"),
                        time=rainfall.get("time") or record.observed_time or target.start_time,
                        rainfall_mm=float(rainfall.get("rainfall_mm") or 0),
                        duration_minutes=int(rainfall.get("duration_minutes") or 60),
                        location=tuple(rainfall["location"]) if rainfall.get("location") else record.location,
                        source=rainfall.get("source") or record.source_type,
                    )
                )
            water = facts.get("water_level_record")
            if isinstance(water, dict):
                target = self._context_target(events, record)
                target.water_level_records.append(
                    WaterLevelRecord(
                        station_id=str(water.get("station_id") or record.location_name or "unknown"),
                        time=water.get("time") or record.observed_time or target.start_time,
                        level_m=float(water.get("level_m") or 0),
                        datum=water.get("datum"),
                        location=tuple(water["location"]) if water.get("location") else record.location,
                        source=water.get("source") or record.source_type,
                    )
                )

    def _context_target(self, events: list[FloodEvent], record: SourceRecord) -> FloodEvent:
        if record.location_name:
            for event in events:
                if any(item.location_name == record.location_name for item in event.evidence):
                    return event
        return events[0]
