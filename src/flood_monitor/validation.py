"""Validation dataset export for flood models."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .gis import FloodMap
from .models import FloodEvent


class ValidationExporter:
    SUPPORTED_MODELS = {"swmm", "anuga", "lisflood-fp", "telemac", "d-hydro", "generic"}

    def export(self, event: FloodEvent, output_dir: str | Path, target_model: str = "generic") -> Path:
        model = target_model.lower()
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported target model: {target_model}")
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "event.json").write_text(json.dumps(event.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        (out / "flood_extent.geojson").write_text(
            json.dumps(FloodMap().to_geojson([event]), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._write_depth_points(event, out / "depth_points.csv")
        self._write_rainfall(event, out / "rainfall.csv")
        self._write_water_levels(event, out / "water_levels.csv")
        self._write_evidence(event, out / "evidence_manifest.csv")
        (out / "README.txt").write_text(
            f"Flood Monitor validation export\nEvent: {event.event_id}\nTarget model: {model}\n"
            "Coordinates: WGS84 lon/lat unless noted in event metadata.\n",
            encoding="utf-8",
        )
        return out

    def _write_depth_points(self, event: FloodEvent, path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "event_id",
                    "time",
                    "lon",
                    "lat",
                    "location_name",
                    "depth_m",
                    "depth_min_m",
                    "depth_max_m",
                    "method",
                    "reference_object",
                    "confidence",
                    "evidence_ids",
                ],
            )
            writer.writeheader()
            for item in event.depth_observations:
                lon, lat = item.location or (None, None)
                dmin, dmax = item.depth_range_m or (None, None)
                writer.writerow(
                    {
                        "event_id": event.event_id,
                        "time": item.time,
                        "lon": lon,
                        "lat": lat,
                        "location_name": item.location_name,
                        "depth_m": item.depth_m,
                        "depth_min_m": dmin,
                        "depth_max_m": dmax,
                        "method": item.method,
                        "reference_object": item.reference_object,
                        "confidence": item.confidence,
                        "evidence_ids": "|".join(item.evidence_ids),
                    }
                )

    def _write_rainfall(self, event: FloodEvent, path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["station_id", "time", "rainfall_mm", "duration_minutes", "lon", "lat", "source"])
            writer.writeheader()
            for item in event.rainfall_records:
                lon, lat = item.location or (None, None)
                writer.writerow(
                    {
                        "station_id": item.station_id,
                        "time": item.time,
                        "rainfall_mm": item.rainfall_mm,
                        "duration_minutes": item.duration_minutes,
                        "lon": lon,
                        "lat": lat,
                        "source": item.source,
                    }
                )

    def _write_water_levels(self, event: FloodEvent, path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["kind", "station_id", "time", "level_m", "datum", "lon", "lat", "source"])
            writer.writeheader()
            for item in event.water_level_records:
                lon, lat = item.location or (None, None)
                writer.writerow(
                    {
                        "kind": "water_level",
                        "station_id": item.station_id,
                        "time": item.time,
                        "level_m": item.level_m,
                        "datum": item.datum,
                        "lon": lon,
                        "lat": lat,
                        "source": item.source,
                    }
                )
            for item in event.tide_records:
                lon, lat = item.location or (None, None)
                writer.writerow(
                    {
                        "kind": "tide",
                        "station_id": item.station_id,
                        "time": item.time,
                        "level_m": item.tide_m,
                        "datum": item.datum,
                        "lon": lon,
                        "lat": lat,
                        "source": item.source,
                    }
                )

    def _write_evidence(self, event: FloodEvent, path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["evidence_id", "source_type", "source_name", "url", "observed_time", "published_time", "location_name", "confidence", "license"],
            )
            writer.writeheader()
            for item in event.evidence:
                writer.writerow(
                    {
                        "evidence_id": item.evidence_id,
                        "source_type": item.source_type,
                        "source_name": item.source_name,
                        "url": item.url,
                        "observed_time": item.observed_time,
                        "published_time": item.published_time,
                        "location_name": item.location_name,
                        "confidence": item.confidence,
                        "license": item.license,
                    }
                )
