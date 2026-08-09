"""Local JSON/CSV evidence imports."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ..models import Evidence
from ..query import evidence_matches_query, parse_bbox
from .base import SourceAdapter
from .rss import infer_hk_bbox, infer_hk_location


class LocalFileEvidenceSource(SourceAdapter):
    def __init__(self, name: str = "local_file", config: dict[str, Any] | None = None) -> None:
        super().__init__(name, config.get("source_type", "manual") if config else "manual", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        path = Path(self.config["path"])
        rows = self._read_rows(path)
        evidence = [self._row_to_evidence(row) for row in rows]
        return [item for item in evidence if evidence_matches_query(item, **query)]

    def _read_rows(self, path: Path) -> list[dict[str, Any]]:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding=self.config.get("encoding", "utf-8")))
            if isinstance(payload, dict) and "source_records" in payload:
                payload = payload["source_records"]
            if isinstance(payload, dict) and "items" in payload:
                payload = payload["items"]
            if isinstance(payload, dict):
                payload = [payload]
            return list(payload)
        with path.open(newline="", encoding=self.config.get("encoding", "utf-8")) as handle:
            return list(csv.DictReader(handle))

    def _row_to_evidence(self, row: dict[str, Any]) -> Evidence:
        if any(key in row for key in ("source_id", "publisher_or_provider", "published_at", "retrieved_at", "text", "provenance")):
            payload = dict(row)
            payload.setdefault("source_type", self.source_type)
            payload.setdefault("publisher_or_provider", payload.get("source_name") or self.name)
            return Evidence.from_dict(payload)
        lon = row.get("lon") or row.get("longitude")
        lat = row.get("lat") or row.get("latitude")
        location = (float(lon), float(lat)) if lon not in (None, "") and lat not in (None, "") else None
        text = " ".join(
            str(part)
            for part in [row.get("location_name"), row.get("place"), row.get("area_description"), row.get("raw_text"), row.get("text"), row.get("summary"), row.get("title")]
            if part
        )
        location_name = row.get("location_name") or row.get("place") or None
        inferred_location_name, inferred_location = infer_hk_location(text)
        if location is None:
            location = inferred_location
        if location_name is None:
            location_name = inferred_location_name
        bbox = self._row_bbox(row)
        if bbox is None and location is None:
            bbox = infer_hk_bbox(text)
        facts: dict[str, Any] = {"raw_record": row}
        for key in ("area_description", "platform", "verification_status", "evidence_grade", "evidence_kind", "search_query", "source_note"):
            if row.get(key):
                facts[key] = row[key]
        if "verification_status" not in facts and (row.get("source_type") or self.source_type) in {"social", "rumor", "community"}:
            facts["verification_status"] = "unverified"
        if "evidence_grade" not in facts and facts.get("verification_status") == "unverified":
            facts["evidence_grade"] = "lead"
        if bbox and location is None:
            facts["area_estimation"] = {"method": "text_area_to_bbox", "basis": location_name or row.get("area_description") or text}
        if row.get("depth_m"):
            depth = float(row["depth_m"])
            facts["depth_observation"] = {
                "depth_m": depth,
                "depth_range_m": [float(row.get("depth_min_m", max(0, depth - 0.05))), float(row.get("depth_max_m", depth + 0.05))],
                "method": row.get("method") or "manual_file",
                "reference_object": row.get("reference_object") or None,
            }
        return Evidence(
            source_type=row.get("source_type") or self.source_type,
            source_name=row.get("source_name") or self.name,
            evidence_id=row.get("evidence_id") or None,
            url=row.get("url") or row.get("path") or str(self.config["path"]),
            published_time=row.get("published_time") or None,
            observed_time=row.get("observed_time") or row.get("time") or None,
            location_name=location_name,
            location=location,
            bbox=bbox,
            raw_text=row.get("raw_text") or row.get("text") or None,
            summary=row.get("summary") or row.get("title") or None,
            extracted_facts=facts,
            confidence=float(row.get("confidence") or self.config.get("confidence", 0.65)),
            license=row.get("license") or self.config.get("license"),
        )

    def _row_bbox(self, row: dict[str, Any]) -> tuple[float, float, float, float] | None:
        if row.get("bbox"):
            return parse_bbox(row["bbox"])
        keys = ("min_lon", "min_lat", "max_lon", "max_lat")
        if all(row.get(key) not in (None, "") for key in keys):
            return tuple(float(row[key]) for key in keys)  # type: ignore[return-value]
        return None
