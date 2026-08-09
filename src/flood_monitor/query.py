"""Query parsing and spatiotemporal filtering helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from .models import BBox, Evidence, FloodEvent


HK_DISTRICT_CENTROIDS: dict[str, tuple[float, float]] = {
    "Central & Western District": (114.154, 22.286),
    "Eastern District": (114.225, 22.281),
    "Kwai Tsing": (114.129, 22.354),
    "Islands District": (113.946, 22.286),
    "North District": (114.143, 22.501),
    "Sai Kung": (114.264, 22.382),
    "Sha Tin": (114.195, 22.381),
    "Southern District": (114.162, 22.247),
    "Tai Po": (114.169, 22.450),
    "Tsuen Wan": (114.114, 22.371),
    "Tuen Mun": (113.976, 22.391),
    "Wan Chai": (114.174, 22.277),
    "Yuen Long": (114.030, 22.445),
    "Yau Tsim Mong": (114.170, 22.311),
    "Sham Shui Po": (114.160, 22.331),
    "Kowloon City": (114.188, 22.328),
    "Wong Tai Sin": (114.193, 22.341),
    "Kwun Tong": (114.226, 22.313),
    "Northern New Territories": (114.080, 22.500),
}

HK_BBOX: BBox = (113.82, 22.13, 114.44, 22.57)

HK_AREA_BBOXES: dict[str, BBox] = {
    "Hong Kong": HK_BBOX,
    "Northern New Territories": (113.93, 22.39, 114.25, 22.57),
    "North District": (114.03, 22.45, 114.24, 22.57),
    "Yuen Long": (113.93, 22.39, 114.08, 22.52),
    "Tai Po": (114.10, 22.38, 114.27, 22.52),
}


def parse_time(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        try:
            if len(text) == 14 and text.isdigit():
                dt = datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            elif len(text) == 16 and text.endswith("Z") and text[8] == "T":
                dt = datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            else:
                if text.endswith("Z"):
                    text = f"{text[:-1]}+00:00"
                dt = datetime.fromisoformat(text)
        except ValueError:
            try:
                dt = parsedate_to_datetime(str(value))
            except (TypeError, ValueError):
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def within_time_range(observed_time: str | None, start_time: Any = None, end_time: Any = None) -> bool:
    if not observed_time:
        return True
    observed = parse_time(observed_time)
    start = parse_time(start_time)
    end = parse_time(end_time)
    if observed is None:
        return True
    if start and observed < start:
        return False
    if end and observed > end:
        return False
    return True


def parse_bbox(value: Any) -> BBox | None:
    if value is None:
        return None
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
    else:
        parts = list(value)
    if len(parts) != 4:
        raise ValueError("bbox must contain min_lon,min_lat,max_lon,max_lat")
    min_lon, min_lat, max_lon, max_lat = (float(part) for part in parts)
    return (min_lon, min_lat, max_lon, max_lat)


def bbox_intersects(a: BBox | None, b: BBox | None) -> bool:
    if a is None or b is None:
        return True
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def point_in_bbox(point: tuple[float, float] | None, bbox: BBox | None) -> bool:
    if point is None or bbox is None:
        return True
    lon, lat = point
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def text_matches_region(text: str | None, region: str | None) -> bool:
    if not region or not text:
        return True
    return region.lower() in text.lower()


def evidence_matches_query(evidence: Evidence, **query: Any) -> bool:
    if not within_time_range(evidence.observed_time or evidence.published_time, query.get("start_time"), query.get("end_time")):
        return False
    bbox = parse_bbox(query.get("bbox") or query.get("area_bbox")) if query.get("bbox") or query.get("area_bbox") else None
    if bbox and not point_in_bbox(evidence.location, bbox) and not bbox_intersects(evidence.bbox, bbox):
        return False
    region = query.get("region")
    if isinstance(region, str) and region.lower() in {"hong kong", "hk", "香港"}:
        return True
    if region and not (
        text_matches_region(evidence.location_name, region)
        or text_matches_region(evidence.source_name, region)
        or text_matches_region(evidence.summary, region)
        or text_matches_region(evidence.raw_text, region)
    ):
        return False
    return True


def event_matches_query(event: FloodEvent, **query: Any) -> bool:
    if not within_time_range(event.start_time, query.get("start_time"), query.get("end_time")):
        return False
    bbox = parse_bbox(query.get("bbox") or query.get("area_bbox")) if query.get("bbox") or query.get("area_bbox") else None
    if bbox and not bbox_intersects(event.bbox, bbox):
        if not any(point_in_bbox(item.location, bbox) for item in event.depth_observations):
            return False
    region = query.get("region")
    if isinstance(region, str) and region.lower() in {"hong kong", "hk", "香港"}:
        return True
    if region and not text_matches_region(event.region, region) and not text_matches_region(event.name, region):
        return False
    return True
