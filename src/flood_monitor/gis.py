"""Build the Flood Monitor JSON database from fused flood events."""

from __future__ import annotations

import json
from datetime import timezone, datetime
from pathlib import Path

from .models import DrainageAssessment, FloodEvent, FloodField, Observation, RunManifest, SourceRecord


class FloodMap:
    """Convert fused events into the compact JSON database used by HTML views."""

    def to_geojson(
        self,
        events: list[FloodEvent],
        *,
        flood_fields: list[FloodField] | None = None,
        drainage_assessments: list[DrainageAssessment] | None = None,
    ) -> dict:
        features = []
        for event in events:
            if event.flood_extent:
                features.append(
                    {
                        "type": "Feature",
                        "geometry": event.flood_extent,
                        "properties": {**self._event_props(event), "feature_type": "flood_extent"},
                    }
                )
            elif event.bbox:
                features.append(
                    {
                        "type": "Feature",
                        "geometry": self._bbox_polygon(event.bbox),
                        "properties": {**self._event_props(event), "feature_type": "event_bbox"},
                    }
                )
            for depth in event.depth_observations:
                if depth.location:
                    features.append(
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": list(depth.location)},
                            "properties": {
                                **self._event_props(event),
                                "feature_type": "depth_observation",
                                "time": depth.time,
                                "location_name": depth.location_name,
                                "depth_m": depth.depth_m,
                                "depth_range_m": depth.depth_range_m,
                                "method": depth.method,
                                "reference_object": depth.reference_object,
                                "evidence_ids": depth.evidence_ids,
                                "observation_confidence": depth.confidence,
                            },
                        }
                    )
            for rainfall in event.rainfall_records:
                if rainfall.location:
                    features.append(
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": list(rainfall.location)},
                            "properties": {
                                **self._event_props(event),
                                "feature_type": "rainfall_record",
                                "time": rainfall.time,
                                "rainfall_mm": rainfall.rainfall_mm,
                                "duration_minutes": rainfall.duration_minutes,
                                "station_id": rainfall.station_id,
                                "source": rainfall.source,
                            },
                        }
                    )
            for water_level in event.water_level_records:
                if water_level.location:
                    features.append(
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": list(water_level.location)},
                            "properties": {
                                **self._event_props(event),
                                "feature_type": "water_level_record",
                                "time": water_level.time,
                                "level_m": water_level.level_m,
                                "station_id": water_level.station_id,
                                "datum": water_level.datum,
                                "source": water_level.source,
                            },
                        }
                    )
            for evidence in event.evidence:
                if evidence.location:
                    features.append(
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": list(evidence.location)},
                            "properties": self._evidence_props(event, evidence, "source_evidence"),
                        }
                    )
                if evidence.bbox:
                    center = self._bbox_center(evidence.bbox)
                    features.append(
                        {
                            "type": "Feature",
                            "geometry": self._bbox_polygon(evidence.bbox),
                            "properties": self._evidence_props(event, evidence, "source_evidence_area"),
                        }
                    )
                    if evidence.location is None:
                        features.append(
                            {
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": list(center)},
                                "properties": {
                                    **self._evidence_props(event, evidence, "source_evidence_estimated_location"),
                                    "method": "bbox_centroid",
                                    "location_estimation": "source_area_centroid",
                                },
                            }
                        )
        for field in flood_fields or []:
            geometry = field.geometry_or_raster
            if isinstance(geometry, dict) and geometry.get("type") in {"Point", "LineString", "Polygon", "MultiPolygon"}:
                features.append(
                    {
                        "type": "Feature",
                        "geometry": geometry,
                        "properties": {
                            "feature_type": "forecast_field" if field.forecast_horizon else "reconstructed_field",
                            "field_id": field.field_id,
                            "valid_time": field.valid_time,
                            "forecast_horizon": field.forecast_horizon,
                            "source_model": field.source_model,
                            "model_version": field.model_version,
                            "result_kind": field.result_kind,
                            "uncertainty": field.uncertainty,
                            "run_id": field.run_id,
                        },
                    }
                )
        for assessment in drainage_assessments or []:
            for asset in assessment.associated_assets:
                geometry = asset.get("geometry")
                if isinstance(geometry, dict) and geometry.get("type"):
                    features.append(
                        {
                            "type": "Feature",
                            "geometry": geometry,
                            "properties": {
                                "feature_type": "drainage_assessment",
                                "assessment_id": assessment.assessment_id,
                                "spatial_unit": assessment.spatial_unit,
                                "conclusion_level": assessment.conclusion_level,
                                "confidence": assessment.confidence,
                                "asset_id": asset.get("asset_id"),
                            },
                        }
                    )
        return {"type": "FeatureCollection", "features": features}

    def to_database(
        self,
        events: list[FloodEvent],
        *,
        observations: list[Observation] | None = None,
        source_records: list[SourceRecord] | None = None,
        flood_fields: list[FloodField] | None = None,
        drainage_assessments: list[DrainageAssessment] | None = None,
        manifest: RunManifest | None = None,
    ) -> dict:
        times = [event.start_time for event in events if event.start_time]
        fields = flood_fields or []
        drainage = drainage_assessments or []
        requested_range = manifest.requested_time_range if manifest else {}
        demo_snapshot = manifest.configuration.get("demo_snapshot", {}) if manifest else {}
        return {
            "schema_version": 2,
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "region": events[0].region if events else None,
                "start_time": requested_range.get("start") or (min(times) if times else None),
                "end_time": requested_range.get("end") or (max(times) if times else None),
                "event_count": len(events),
                "observation_count": len(observations or []),
                "official_reported_case_total": demo_snapshot.get("official_reported_case_total"),
                "named_location_count": demo_snapshot.get("named_location_count"),
                "coverage_definition": demo_snapshot.get("coverage_definition"),
                "model_field_count": len(fields),
                "drainage_assessment_count": len(drainage),
                "run_id": manifest.run_id if manifest else None,
            },
            "geojson": self.to_geojson(events, flood_fields=fields, drainage_assessments=drainage),
            "events": [event.to_dict() for event in events],
            "sources": [self._source_record(event, evidence) for event in events for evidence in event.evidence],
            "source_records": [item.to_dict() for item in source_records or []],
            "observations": [item.to_dict() for item in observations or []],
            "model_results": [item.to_dict() for item in fields],
            "drainage_results": [item.to_dict() for item in drainage],
            "run_manifest": manifest.to_dict() if manifest else None,
        }

    def write_database(
        self,
        events: list[FloodEvent],
        output_path: str | Path,
        **layers,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_database(events, **layers), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _bbox_polygon(self, bbox: tuple[float, float, float, float]) -> dict:
        min_lon, min_lat, max_lon, max_lat = bbox
        return {
            "type": "Polygon",
            "coordinates": [
                [
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat],
                ]
            ],
        }

    def _bbox_center(self, bbox: tuple[float, float, float, float]) -> tuple[float, float]:
        min_lon, min_lat, max_lon, max_lat = bbox
        return ((min_lon + max_lon) / 2, (min_lat + max_lat) / 2)

    def _event_props(self, event: FloodEvent) -> dict:
        depths = [item.depth_m for item in event.depth_observations if item.depth_m is not None]
        ranges = [item.depth_range_m for item in event.depth_observations if item.depth_range_m]
        return {
            "event_id": event.event_id,
            "name": event.name,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "region": event.region,
            "severity": event.severity,
            "confidence": event.confidence,
            "verification_status": event.verification_status,
            "evidence_level": event.evidence_level,
            "result_kind": "observed_or_inferred_event",
            "bbox": event.bbox,
            "source_count": len(event.evidence),
            "source_summary": event.metadata.get("source_summary", {}),
            "max_depth_m": max(depths) if depths else None,
            "depth_range_m": [min(r[0] for r in ranges), max(r[1] for r in ranges)] if ranges else None,
            "depth_inference": event.metadata.get("depth_inference"),
        }

    def _evidence_props(self, event: FloodEvent, evidence, feature_type: str) -> dict:
        facts = evidence.extracted_facts or {}
        return {
            **self._event_props(event),
            "feature_type": feature_type,
            "evidence_id": evidence.evidence_id,
            "source_type": evidence.source_type,
            "source_name": evidence.source_name,
            "publisher_or_provider": evidence.publisher_or_provider,
            "url": evidence.url,
            "observed_time": evidence.observed_time,
            "published_time": evidence.published_time,
            "location_name": evidence.location_name,
            "summary": evidence.summary,
            "raw_text": evidence.raw_text,
            "area_description": facts.get("area_description"),
            "platform": facts.get("platform"),
            "verification_status": facts.get("verification_status"),
            "evidence_grade": facts.get("evidence_grade"),
            "evidence_kind": facts.get("evidence_kind"),
            "source_note": facts.get("source_note"),
            "search_query": facts.get("search_query"),
            "evidence_confidence": evidence.confidence,
            "license": evidence.license,
        }

    def _source_record(self, event: FloodEvent, evidence) -> dict:
        facts = evidence.extracted_facts or {}
        return {
            "event_id": event.event_id,
            "event_name": event.name,
            "evidence_id": evidence.evidence_id,
            "source_type": evidence.source_type,
            "source_name": evidence.source_name,
            "publisher_or_provider": evidence.publisher_or_provider,
            "platform": facts.get("platform"),
            "verification_status": facts.get("verification_status"),
            "evidence_grade": facts.get("evidence_grade"),
            "evidence_kind": facts.get("evidence_kind"),
            "published_time": evidence.published_time,
            "observed_time": evidence.observed_time,
            "location_name": evidence.location_name,
            "location": evidence.location,
            "bbox": evidence.bbox,
            "area_description": facts.get("area_description"),
            "confidence": evidence.confidence,
            "summary": evidence.summary,
            "raw_text": evidence.raw_text,
            "url": evidence.url,
            "source_note": facts.get("source_note"),
            "search_query": facts.get("search_query"),
            "license": evidence.license,
        }
