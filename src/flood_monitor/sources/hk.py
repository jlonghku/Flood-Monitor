"""Hong Kong government and monitoring source adapters."""

from __future__ import annotations

from typing import Any

from ..models import Evidence, RainfallRecord, WaterLevelRecord
from ..query import HK_AREA_BBOXES, HK_BBOX, HK_DISTRICT_CENTROIDS, evidence_matches_query
from .base import SourceAdapter
from .http import SourceFetchError, fetch_json


class HKOSource(SourceAdapter):
    CURRENT_WEATHER_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en"
    WARNING_SUMMARY_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=warnsum&lang=en"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__("Hong Kong Observatory", "hko", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        mode = self.config.get("mode", "current_weather")
        if mode == "current_weather":
            url = self.config.get("url", self.CURRENT_WEATHER_URL)
        elif mode == "warning_summary":
            url = self.config.get("url", self.WARNING_SUMMARY_URL)
        else:
            raise ValueError(f"Unsupported HKO mode: {mode}")
        try:
            payload = fetch_json(url, timeout=float(self.config.get("timeout", 15)))
        except SourceFetchError:
            if self.config.get("raise_on_error"):
                raise
            return []
        evidence = self._current_weather_to_evidence(payload, **query) if mode == "current_weather" else self._warning_summary_to_evidence(payload)
        return [item for item in evidence if evidence_matches_query(item, **query)]

    def _current_weather_to_evidence(self, payload: dict[str, Any], **query: Any) -> list[Evidence]:
        min_rainfall = float(query.get("rainfall_threshold_mm", self.config.get("rainfall_threshold_mm", 30.0)))
        include_below = bool(query.get("include_rainfall_below_threshold", self.config.get("include_rainfall_below_threshold", False)))
        items: list[Evidence] = []
        rainfall = payload.get("rainfall") or {}
        observed_time = rainfall.get("endTime") or payload.get("updateTime")
        for record in rainfall.get("data", []):
            amount = float(record.get("max") or record.get("min") or 0)
            if amount < min_rainfall and not include_below:
                continue
            place = record.get("place")
            location = HK_DISTRICT_CENTROIDS.get(place)
            severity = "severe" if amount >= 70 else "moderate" if amount >= 30 else "minor"
            items.append(
                Evidence(
                    source_type=self.source_type,
                    source_name=self.name,
                    url=self.config.get("url", self.CURRENT_WEATHER_URL),
                    observed_time=observed_time,
                    location_name=place,
                    location=location,
                    raw_text=f"HKO automatic weather station rainfall: {amount:g} mm in the past hour at {place}.",
                    summary=f"Past-hour rainfall {amount:g} mm at {place}",
                    extracted_facts={
                        "is_flood_related": False,
                        "severity": severity,
                        "source_role": "rainfall_context",
                        "rainfall_record": {
                            "station_id": place,
                            "time": observed_time,
                            "rainfall_mm": amount,
                            "duration_minutes": 60,
                            "location": location,
                            "source": self.source_type,
                        },
                    },
                    confidence=0.95 if amount >= min_rainfall else 0.55,
                    license="DATA.GOV.HK / HKO open data",
                )
            )
        for message in payload.get("warningMessage", []):
            text = str(message)
            is_actual_flood_report = self._is_actual_flood_report(text)
            if not is_actual_flood_report:
                continue
            location_name, bbox = self._flood_report_area(text)
            items.append(
                Evidence(
                    source_type=self.source_type,
                    source_name=self.name,
                    url=self.config.get("url", self.CURRENT_WEATHER_URL),
                    observed_time=payload.get("updateTime") or observed_time,
                    location_name=location_name,
                    location=HK_DISTRICT_CENTROIDS.get(location_name),
                    bbox=bbox,
                    raw_text=text,
                    summary=f"HKO warning: {text}",
                    extracted_facts={
                        "is_flood_related": True,
                        "severity": "severe",
                        "source_role": "actual_flood_report",
                        "area_estimation": {"method": "hko_warning_text_area", "basis": location_name} if bbox else None,
                    },
                    confidence=0.9,
                    license="DATA.GOV.HK / HKO open data",
                )
            )
        return items

    def _warning_summary_to_evidence(self, payload: dict[str, Any]) -> list[Evidence]:
        items: list[Evidence] = []
        for code, record in payload.items():
            name = str(record.get("name") or code)
            warning_type = str(record.get("type") or "")
            text = " ".join(part for part in [name, warning_type, record.get("actionCode")] if part)
            is_actual_flood_report = self._is_actual_flood_report(text)
            if not is_actual_flood_report:
                continue
            severity = "severe"
            location_name, bbox = self._flood_report_area(text)
            items.append(
                Evidence(
                    source_type=self.source_type,
                    source_name=self.name,
                    url=self.config.get("url", self.WARNING_SUMMARY_URL),
                    observed_time=record.get("updateTime") or record.get("issueTime"),
                    published_time=record.get("issueTime"),
                    location_name=location_name,
                    location=HK_DISTRICT_CENTROIDS.get(location_name),
                    bbox=bbox,
                    raw_text=f"{name} {warning_type}".strip(),
                    summary=f"HKO warning summary: {name} {warning_type}".strip(),
                    extracted_facts={
                        "is_flood_related": True,
                        "severity": severity,
                        "warning_code": code,
                        "source_role": "actual_flood_report",
                        "area_estimation": {"method": "hko_warning_text_area", "basis": location_name} if bbox else None,
                        "raw_record": record,
                    },
                    confidence=0.92,
                    license="DATA.GOV.HK / HKO open data",
                )
            )
        return items

    def _flood_report_area(self, text: str) -> tuple[str, tuple[float, float, float, float]]:
        lowered = text.lower()
        if "新界北部" in text or "northern new territories" in lowered or "north new territories" in lowered:
            return "Northern New Territories", HK_AREA_BBOXES["Northern New Territories"]
        return "Hong Kong", HK_BBOX

    def _is_actual_flood_report(self, text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in ("flood", "flooding", "水浸", "淹", "積水"))

    def rainfall_to_evidence(self, record: RainfallRecord) -> Evidence:
        return Evidence(
            source_type=self.source_type,
            source_name=self.name,
            observed_time=record.time,
            location=record.location,
            summary=f"{record.duration_minutes}-minute rainfall {record.rainfall_mm} mm at {record.station_id}",
            extracted_facts={"rainfall_record": record.to_dict()},
            confidence=0.95,
        )


class DSDSource(SourceAdapter):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__("Drainage Services Department", "dsd", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        return []

    def water_level_to_evidence(self, record: WaterLevelRecord) -> Evidence:
        return Evidence(
            source_type=self.source_type,
            source_name=self.name,
            observed_time=record.time,
            location=record.location,
            summary=f"Water level {record.level_m} m at {record.station_id}",
            extracted_facts={"water_level_record": record.to_dict()},
            confidence=0.95,
        )


class HongKongOpenDataSource(SourceAdapter):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__("DATA.GOV.HK", "open_data", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        return []
