"""Rule-assisted text extraction for flood evidence."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from ..models import Evidence, Observation

HK_TZ = ZoneInfo("Asia/Hong_Kong")


class TextFloodExtractor:
    """Extract coarse flood facts from Chinese or English reports."""

    FLOOD_TERMS = ("flood", "flooding", "inundation", "ponding", "水浸", " flooding", "淹", "積水", "内涝", "洪水")
    SEVERE_TERMS = ("封路", "停駛", "车门", "車門", "死火", "腰", "severe", "trapped", "road closed")
    MODERATE_TERMS = ("膝", "輪胎", "轮胎", "ankle", "knee", "tire", "tyre", "bumper", "保險桿", "水深")
    DEPTH_PATTERNS = (
        re.compile(r"(?P<cm>\d+(?:\.\d+)?)\s*(?:cm|厘米|公分)"),
        re.compile(r"(?P<m>\d+(?:\.\d+)?)\s*(?:m|米)"),
    )
    REFERENCE_DEPTHS = {
        "ankle": (0.05, 0.15),
        "腳眼": (0.05, 0.15),
        "脚踝": (0.05, 0.15),
        "knee": (0.35, 0.55),
        "膝": (0.35, 0.55),
        "tire": (0.25, 0.45),
        "tyre": (0.25, 0.45),
        "輪胎": (0.25, 0.45),
        "轮胎": (0.25, 0.45),
        "bumper": (0.35, 0.60),
        "保險桿": (0.35, 0.60),
        "door": (0.55, 0.9),
        "車門": (0.55, 0.9),
        "车门": (0.55, 0.9),
        "waist": (0.8, 1.1),
        "腰": (0.8, 1.1),
    }

    def extract(self, evidence: Evidence) -> Evidence:
        text = " ".join(part for part in [evidence.raw_text, evidence.summary] if part)
        facts = dict(evidence.extracted_facts)
        facts.setdefault("is_flood_related", self.is_flood_related(text))
        facts.setdefault("severity", self.estimate_severity(text))
        depth = None if "rainfall_record" in facts else self.extract_depth(text)
        if depth:
            facts.setdefault("depth_observation", depth)
        if "start_time" not in facts:
            facts["start_time"] = evidence.observed_time or evidence.published_time or datetime.now(HK_TZ).isoformat()
        evidence.extracted_facts = facts
        evidence.confidence = max(evidence.confidence, 0.55 if facts["is_flood_related"] else 0.2)
        return evidence

    def to_observation(self, evidence: Evidence) -> Observation | None:
        """Create an Observation only when the record describes actual flooding."""
        facts = evidence.extracted_facts
        if not facts.get("is_flood_related", False):
            return None
        geometry = evidence.geometry_if_provided
        location_precision = facts.get("location_precision", "unknown")
        uncertainty = facts.get("location_uncertainty_m")
        if geometry is None and evidence.location:
            geometry = {"type": "Point", "coordinates": list(evidence.location)}
            location_precision = facts.get("location_precision", "approximate_point")
            uncertainty = uncertainty if uncertainty is not None else 1500.0
        elif geometry is None and evidence.bbox:
            min_lon, min_lat, max_lon, max_lat = evidence.bbox
            geometry = {
                "type": "Polygon",
                "coordinates": [[[min_lon, min_lat], [max_lon, min_lat], [max_lon, max_lat], [min_lon, max_lat], [min_lon, min_lat]]],
            }
            location_precision = facts.get("location_precision", "approximate_area")
        depth = facts.get("depth_observation")
        if isinstance(depth, dict):
            depth = dict(depth)
            depth.setdefault("measured_or_inferred", "measured" if depth.get("method") == "text_reported_measurement" else "inferred")
            depth.setdefault("confidence", evidence.confidence)
        return Observation(
            source_id=evidence.source_id or evidence.evidence_id or "unknown",
            observation_type="visual_report" if evidence.source_type in {"image", "cctv"} else "text_report",
            event_type=facts.get("event_type", "flooding"),
            observed_at=evidence.observed_time or evidence.published_time,
            time_precision=facts.get("time_precision", self._time_precision(evidence.observed_time or evidence.published_time)),
            location_text=evidence.location_name,
            geometry=geometry,
            location_precision=location_precision,
            location_uncertainty=uncertainty,
            location_candidates=facts.get("location_candidates", []),
            water_depth=depth,
            impacts=self._extract_impacts(" ".join(part for part in [evidence.raw_text, evidence.summary] if part)),
            evidence_text=evidence.raw_text or evidence.summary,
            visual_evidence=facts.get("visual_evidence"),
            extraction_method=facts.get("extraction_method", "rule_assisted_text"),
            extraction_confidence=evidence.confidence,
            provenance={
                "source_id": evidence.source_id,
                "url": evidence.url,
                "publisher_or_provider": evidence.publisher_or_provider,
            },
        )

    def is_flood_related(self, text: str) -> bool:
        lowered = text.lower()
        return any(term.lower() in lowered for term in self.FLOOD_TERMS)

    def estimate_severity(self, text: str) -> str:
        lowered = text.lower()
        if any(term.lower() in lowered for term in self.SEVERE_TERMS):
            return "severe"
        if any(term.lower() in lowered for term in self.MODERATE_TERMS):
            return "moderate"
        if self.is_flood_related(text):
            return "minor"
        return "unknown"

    def extract_depth(self, text: str) -> dict | None:
        for pattern in self.DEPTH_PATTERNS:
            match = pattern.search(text)
            if match:
                if match.groupdict().get("cm"):
                    depth_m = float(match.group("cm")) / 100.0
                else:
                    depth_m = float(match.group("m"))
                return {
                    "depth_m": depth_m,
                    "depth_range_m": [max(0, depth_m - 0.05), depth_m + 0.05],
                    "method": "text_reported_measurement",
                    "measured_or_inferred": "measured",
                }
        lowered = text.lower()
        for label, depth_range in self.REFERENCE_DEPTHS.items():
            if label.lower() in lowered:
                return {
                    "depth_m": round(sum(depth_range) / 2, 3),
                    "depth_range_m": list(depth_range),
                    "method": "reference_object_text",
                    "reference_object": label,
                    "measured_or_inferred": "inferred",
                }
        return None

    def _time_precision(self, value: str | None) -> str:
        if not value:
            return "unknown"
        if "T" not in value:
            return "day"
        return "minute" if ":" in value else "hour"

    def _extract_impacts(self, text: str) -> dict:
        lowered = text.lower()
        groups = {
            "traffic": ("封路", "交通", "road closed", "traffic"),
            "vehicle": ("死火", "車輛", "车辆", "vehicle", "stranded car"),
            "pedestrian": ("行人", "被困", "pedestrian", "trapped"),
            "property": ("店舖", "地庫", "房屋", "basement", "property"),
            "emergency_response": ("消防", "警方", "救援", "fire services", "rescue"),
        }
        return {name: True for name, terms in groups.items() if any(term in lowered for term in terms)}
