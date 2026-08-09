"""Cross-source observation matching and flood-event fusion."""

from __future__ import annotations

import json
import re
from hashlib import sha1
from statistics import mean
from urllib.parse import urlsplit, urlunsplit

from .models import DepthObservation, Evidence, FloodEvent, Observation, clamp01, stable_id


class FloodFusionEngine:
    """Fuse observations without treating copied reports as corroboration."""

    def __init__(self, region: str = "Hong Kong") -> None:
        self.region = region

    def fuse_observations(
        self,
        observations: list[Observation],
        records_by_id: dict[str, Evidence],
    ) -> list[FloodEvent]:
        groups: dict[str, list[Observation]] = {}
        for observation in observations:
            groups.setdefault(self._observation_group_key(observation), []).append(observation)
        return [self._event_from_observations(group, records_by_id) for group in groups.values()]

    def fuse_evidence(self, evidence_items: list[Evidence]) -> list[FloodEvent]:
        """Compatibility path for already-extracted legacy Evidence objects."""
        events = [FloodEvent.from_evidence(item, region=self.region) for item in evidence_items if item.extracted_facts.get("is_flood_related", True)]
        return self.merge_events(events)

    def merge_events(self, events: list[FloodEvent]) -> list[FloodEvent]:
        groups: dict[str, list[FloodEvent]] = {}
        for event in events:
            groups.setdefault(self._legacy_group_key(event), []).append(event)
        merged = [self._merge_legacy_group(group) for group in groups.values()]
        for event in merged:
            self._record_source_summary(event)
        return merged

    def _event_from_observations(
        self,
        observations: list[Observation],
        records_by_id: dict[str, Evidence],
    ) -> FloodEvent:
        records = [records_by_id[item.source_id] for item in observations if item.source_id in records_by_id]
        first = observations[0]
        times = [item.observed_at for item in observations if item.observed_at]
        start = min(times) if times else "unknown"
        end = max(times) if len(times) > 1 else None
        locations = [item.location_text for item in observations if item.location_text]
        location_name = locations[0] if locations else self.region
        independent_count = len({self._independence_key(record) for record in records})
        official = any(record.source_type in {"government", "hko", "dsd", "open_data"} for record in records)
        sensor = any(record.source_type in {"sensor", "water_level"} for record in records)
        verification = (
            "sensor_verified" if sensor else "official_verified" if official else "cross_verified" if independent_count >= 2 else "single_source"
        )
        if records and all(record.source_type in {"social", "community", "rumor"} for record in records):
            verification = "unverified" if independent_count < 2 else "cross_verified"
        evidence_level = self._evidence_level(records, independent_count, official, sensor)
        confidence_values = [item.extraction_confidence for item in observations]
        confidence = clamp01(mean(confidence_values) + min(0.18, max(0, independent_count - 1) * 0.09))
        bbox = self._observation_bbox(observations)
        event = FloodEvent(
            event_id=stable_id("FM", self.region, start[:10], location_name, sorted(item.source_id for item in observations)),
            name=f"Flood event near {location_name}",
            start_time=start,
            end_time=end,
            event_type=first.event_type,
            region=self.region,
            status="confirmed" if official or sensor or independent_count >= 2 else "candidate",
            severity=self._max_severity(record.extracted_facts.get("severity", "unknown") for record in records),
            confidence=confidence,
            verification_status=verification,
            evidence_level=evidence_level,
            bbox=bbox,
            flood_extent=self._first_extent(observations, records),
            location_precision=self._least_precise(item.location_precision for item in observations),
            evidence=records,
            observation_ids=[item.observation_id or "" for item in observations],
            source_ids=sorted({item.source_id for item in observations}),
            provenance={
                "observation_ids": [item.observation_id for item in observations],
                "source_ids": sorted({item.source_id for item in observations}),
                "fusion_method": "date_location_semantic_key_v1",
            },
            metadata={"independent_source_count": independent_count, "observation_count": len(observations)},
        )
        for observation in observations:
            depth = observation.water_depth
            if not isinstance(depth, dict):
                continue
            location = self._point_from_geometry(observation.geometry)
            event.depth_observations.append(
                DepthObservation(
                    location=location,
                    time=observation.observed_at,
                    depth_m=depth.get("depth_m"),
                    depth_range_m=tuple(depth["depth_range_m"]) if depth.get("depth_range_m") else None,
                    method=depth.get("method", "unknown"),
                    reference_object=depth.get("reference_object"),
                    location_name=observation.location_text,
                    evidence_ids=[observation.source_id],
                    confidence=float(depth.get("confidence", observation.extraction_confidence)),
                    measured_or_inferred=depth.get("measured_or_inferred", "unknown"),
                )
            )
        self._record_source_summary(event)
        return event

    def _observation_group_key(self, observation: Observation) -> str:
        date = (observation.observed_at or "unknown")[:10]
        place = self._normalize_text(observation.location_text or "")
        if not place:
            point = self._point_from_geometry(observation.geometry)
            place = f"{point[0]:.3f},{point[1]:.3f}" if point else observation.observation_id or observation.source_id
        return f"{self.region.lower()}|{date}|{place}|{observation.event_type}"

    def _legacy_group_key(self, event: FloodEvent) -> str:
        date = event.start_time[:10] if event.start_time else "unknown"
        place = event.evidence[0].location_name if event.evidence else event.name
        return f"{event.region}|{date}|{self._normalize_text(place or '')}"

    def _merge_legacy_group(self, group: list[FloodEvent]) -> FloodEvent:
        if len(group) == 1:
            return group[0]
        first = group[0]
        evidence = [item for event in group for item in event.evidence]
        independent = len({self._independence_key(item) for item in evidence})
        merged = FloodEvent(
            event_id=stable_id("FM", first.region, first.start_time[:10], first.name, sorted(item.source_id for item in evidence)),
            name=first.name,
            start_time=min(event.start_time for event in group if event.start_time),
            end_time=max((event.end_time for event in group if event.end_time), default=None),
            event_type=first.event_type,
            region=first.region,
            status="confirmed" if independent >= 2 else "candidate",
            severity=self._max_severity(event.severity for event in group),
            confidence=clamp01(mean(event.confidence for event in group) + min(0.18, max(0, independent - 1) * 0.09)),
            verification_status="cross_verified" if independent >= 2 else "single_source",
            evidence_level="multiple_independent_reports" if independent >= 2 else "single_public_report",
            bbox=self._merge_bbox([event.bbox for event in group if event.bbox]),
            flood_extent=next((event.flood_extent for event in group if event.flood_extent), None),
            location_precision=self._least_precise(event.location_precision for event in group),
            depth_observations=[item for event in group for item in event.depth_observations],
            rainfall_records=[item for event in group for item in event.rainfall_records],
            water_level_records=[item for event in group for item in event.water_level_records],
            tide_records=[item for event in group for item in event.tide_records],
            evidence=evidence,
            observation_ids=sorted({item for event in group for item in event.observation_ids}),
            source_ids=sorted({item.source_id or "" for item in evidence if item.source_id}),
            metadata={"fusion_group_size": len(group), "independent_source_count": independent},
        )
        return merged

    def _independence_key(self, record: Evidence) -> str:
        group = record.metadata.get("syndication_group") or record.extracted_facts.get("syndication_group")
        if group:
            return f"syndication:{group}"
        text = self._normalize_text(record.raw_text or record.summary or "")
        if text:
            return "content:" + sha1(text.encode("utf-8")).hexdigest()[:16]
        if record.url:
            parts = urlsplit(record.url)
            return "url:" + urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        return record.source_id or "unknown"

    def _evidence_level(self, records, independent_count: int, official: bool, sensor: bool) -> str:
        if sensor:
            return "direct_sensor_evidence"
        if official:
            return "direct_official_evidence"
        if any(item.source_type in {"image", "cctv"} for item in records):
            return "visual_evidence"
        if independent_count >= 2:
            return "multiple_independent_reports"
        if any(item.source_type == "news" for item in records):
            return "specific_media_report"
        return "single_public_report"

    def _observation_bbox(self, observations: list[Observation]):
        boxes = []
        for item in observations:
            geometry = item.geometry or {}
            if geometry.get("type") == "Point":
                lon, lat = geometry["coordinates"][:2]
                boxes.append((float(lon), float(lat), float(lon), float(lat)))
            elif geometry.get("type") == "Polygon":
                coords = geometry.get("coordinates", [[]])[0]
                if coords:
                    boxes.append((min(p[0] for p in coords), min(p[1] for p in coords), max(p[0] for p in coords), max(p[1] for p in coords)))
        return self._merge_bbox(boxes)

    def _first_extent(self, observations, records):
        for record in records:
            extent = record.extracted_facts.get("flood_extent")
            if extent:
                return extent
        for observation in observations:
            if observation.geometry and observation.geometry.get("type") in {"Polygon", "MultiPolygon"}:
                return observation.geometry
        return None

    def _point_from_geometry(self, geometry):
        if geometry and geometry.get("type") == "Point":
            coordinates = geometry.get("coordinates") or []
            if len(coordinates) >= 2:
                return (float(coordinates[0]), float(coordinates[1]))
        return None

    def _record_source_summary(self, event: FloodEvent) -> None:
        summary: dict[str, int] = {}
        for item in event.evidence:
            summary[item.source_type] = summary.get(item.source_type, 0) + 1
        event.metadata["source_summary"] = summary

    def _merge_bbox(self, boxes):
        if not boxes:
            return None
        return (min(box[0] for box in boxes), min(box[1] for box in boxes), max(box[2] for box in boxes), max(box[3] for box in boxes))

    def _max_severity(self, severities) -> str:
        order = ["unknown", "minor", "moderate", "severe", "extreme"]
        values = list(severities) or ["unknown"]
        return max(values, key=lambda item: order.index(item) if item in order else 0)

    def _least_precise(self, precisions) -> str:
        order = ["exact_point", "point", "building", "intersection", "road_segment", "approximate_point", "neighborhood", "district", "approximate_area", "unknown"]
        values = list(precisions) or ["unknown"]
        return max(values, key=lambda item: order.index(item) if item in order else len(order) - 1)

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"\W+", "", value.lower(), flags=re.UNICODE)
