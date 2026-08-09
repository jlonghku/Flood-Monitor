"""Spatial evidence sources for GeoJSON and ArcGIS FeatureServer layers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from ..models import Evidence
from ..query import evidence_matches_query
from .base import SourceAdapter
from .http import fetch_json


class GeoJSONSource(SourceAdapter):
    def __init__(self, name: str = "geojson", config: dict[str, Any] | None = None) -> None:
        super().__init__(name, config.get("source_type", "remote_sensing") if config else "remote_sensing", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        payload = self._load_payload()
        evidence = [self._feature_to_evidence(feature) for feature in payload.get("features", [])]
        return [item for item in evidence if evidence_matches_query(item, **query)]

    def _load_payload(self) -> dict[str, Any]:
        if self.config.get("url"):
            return fetch_json(self.config["url"], timeout=float(self.config.get("timeout", 20)))
        path = Path(self.config["path"])
        return json.loads(path.read_text(encoding=self.config.get("encoding", "utf-8")))

    def _feature_to_evidence(self, feature: dict[str, Any]) -> Evidence:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry")
        observed_time = self._first(props, self.config.get("time_fields", ["observed_time", "time", "datetime", "date"]))
        location_name = self._first(props, self.config.get("location_fields", ["location_name", "name", "place", "district"]))
        summary = self._first(props, self.config.get("summary_fields", ["summary", "title", "description", "name"]))
        facts: dict[str, Any] = {"raw_properties": props}
        if geometry and geometry.get("type") in {"Polygon", "MultiPolygon"}:
            facts["flood_extent"] = geometry
            facts["is_flood_related"] = bool(self.config.get("represents_flooding", True))
            facts["event_type"] = "flooding"
            facts["extraction_method"] = "provided_geospatial_extent"
        return Evidence(
            source_type=self.source_type,
            source_name=self.name,
            url=self.config.get("url") or self.config.get("path"),
            observed_time=observed_time,
            location_name=location_name,
            bbox=tuple(feature["bbox"]) if feature.get("bbox") and len(feature["bbox"]) == 4 else None,
            summary=summary,
            geometry_if_provided=geometry,
            extracted_facts=facts,
            confidence=float(self.config.get("confidence", 0.75)),
            license=self.config.get("license"),
        )

    def _first(self, props: dict[str, Any], fields: list[str]) -> Any:
        for field in fields:
            if props.get(field) not in (None, ""):
                return props[field]
        return None


class ArcGISFeatureServerSource(GeoJSONSource):
    def __init__(self, name: str = "arcgis_feature_server", config: dict[str, Any] | None = None) -> None:
        cfg = dict(config or {})
        cfg.setdefault("source_type", "open_data")
        super().__init__(name, cfg)

    def _load_payload(self) -> dict[str, Any]:
        url = self.config["url"]
        if "query?" not in url and not url.endswith("/query"):
            url = url.rstrip("/") + "/query"
        if "?" not in url:
            params = {
                "where": self.config.get("where", "1=1"),
                "outFields": self.config.get("out_fields", "*"),
                "returnGeometry": "true",
                "f": "geojson",
            }
            url = f"{url}?{urlencode(params)}"
        return fetch_json(url, timeout=float(self.config.get("timeout", 20)))
