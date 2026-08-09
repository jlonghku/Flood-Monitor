"""Curated, reproducible data used by the Hong Kong one-year demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEMO_DATA_PATH = Path(__file__).with_name("data") / "hk_one_year_demo.json"


def load_hk_one_year_demo(path: str | Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load the snapshot metadata and expand its named location records.

    The source file stores one episode-level citation plus the locations that
    citation explicitly names. Official totals are kept as metadata; unnamed
    cases are never converted into invented point events.
    """

    payload = json.loads(Path(path or DEMO_DATA_PATH).read_text(encoding="utf-8"))
    snapshot = dict(payload["snapshot"])
    items: list[dict[str, Any]] = []

    for episode in payload["episodes"]:
        locations = episode["locations"]
        named_record_count = sum(not item.get("aggregate", False) for item in locations)
        for location in locations:
            publisher = location.get("publisher", episode["publisher"])
            url = location.get("url", episode["url"])
            source_type = location.get("source_type", episode.get("source_type", "news"))
            confidence = float(location.get("confidence", episode.get("confidence", 0.82)))
            is_aggregate = bool(location.get("aggregate", False))
            facts = {
                "is_flood_related": True,
                "event_type": "flooding",
                "evidence_grade": "A" if source_type in {"government", "dsd"} else "B",
                "evidence_kind": "aggregate_case_summary" if is_aggregate else "named_flood_report",
                "verification_status": (
                    "official_verified" if source_type in {"government", "dsd"} else "media_citing_official_report"
                ),
                "severity": location.get("severity", episode.get("severity", "minor")),
                "location_precision": "approximate_area" if is_aggregate else "approximate_point",
                "location_uncertainty_m": location.get("location_uncertainty_m", 1200.0),
                "area_description": location.get("area_description", location["name"]),
                "source_note": "Demo snapshot record; no water depth is inferred unless the cited source states one.",
                "episode_id": episode["episode_id"],
                "official_reported_case_count": episode["official_reported_case_count"],
                "named_records_in_snapshot": named_record_count,
                "is_aggregate_summary": is_aggregate,
            }
            item: dict[str, Any] = {
                "source_type": source_type,
                "publisher_or_provider": publisher,
                "published_time": location.get("published_time", episode["published_time"]),
                "observed_time": location.get("observed_time", episode["observed_time"]),
                "location_name": location["name"],
                "raw_text": location["text"],
                "summary": location.get("summary", location["text"]),
                "url": url,
                "confidence": confidence,
                "license": episode.get("license"),
                "metadata": {
                    "demo_snapshot": snapshot["snapshot_id"],
                    "episode_id": episode["episode_id"],
                    "official_reported_case_count": episode["official_reported_case_count"],
                    "named_records_in_snapshot": named_record_count,
                    "coverage_note": episode["coverage_note"],
                    "is_aggregate_summary": is_aggregate,
                },
                "extracted_facts": facts,
            }
            if location.get("location"):
                item["location"] = tuple(location["location"])
            if location.get("bbox"):
                item["bbox"] = tuple(location["bbox"])
            items.append(item)

    snapshot["record_count"] = len(items)
    snapshot["named_location_count"] = sum(not item["metadata"]["is_aggregate_summary"] for item in items)
    snapshot["official_reported_case_total"] = sum(
        int(episode["official_reported_case_count"]) for episode in payload["episodes"]
    )
    return snapshot, items
