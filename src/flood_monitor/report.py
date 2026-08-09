"""Structured flood-event reports."""

from __future__ import annotations

from pathlib import Path

from .models import FloodEvent


class FloodReport:
    def render_markdown(self, event: FloodEvent) -> str:
        depths = [item.depth_m for item in event.depth_observations if item.depth_m is not None]
        max_depth = max(depths) if depths else None
        evidence_lines = "\n".join(
            f"- `{item.evidence_id}` {item.source_type}/{item.source_name}; "
            f"observed={item.observed_time or 'unknown'}; published={item.published_time or 'unknown'}; "
            f"location={item.location_name or item.location or item.bbox or 'unknown'}; "
            f"confidence={item.confidence:.2f}; "
            f"{item.summary or item.url or item.raw_text or 'evidence'}"
            for item in event.evidence
        ) or "- No evidence records."
        depth_lines = "\n".join(
            f"- {item.time or 'unknown time'} {item.location_name or item.location or 'unknown location'}: "
            f"{item.depth_m if item.depth_m is not None else 'unknown'} m; "
            f"range={item.depth_range_m or 'unknown'}; "
            f"method={item.method}; reference={item.reference_object or 'none'}; "
            f"evidence={', '.join(item.evidence_ids) or 'none'}; confidence={item.confidence:.2f}"
            for item in event.depth_observations
        ) or "- No depth observations."
        rainfall_lines = "\n".join(
            f"- {item.time} {item.station_id}: {item.rainfall_mm} mm/{item.duration_minutes} min; "
            f"location={item.location or 'unknown'}; source={item.source}"
            for item in event.rainfall_records
        ) or "- No rainfall records."
        water_level_lines = "\n".join(
            f"- {item.time} {item.station_id}: {item.level_m} m; datum={item.datum or 'unknown'}; "
            f"location={item.location or 'unknown'}; source={item.source}"
            for item in event.water_level_records
        ) or "- No water-level records."
        inference = event.metadata.get("depth_inference")
        inference_lines = "- No cross-source depth inference." if not inference else (
            f"- Method: {inference.get('method')}\n"
            f"- Basis: {inference.get('basis')}\n"
            f"- Note: {inference.get('note')}"
        )
        return f"""# {event.name}

## Event Overview

- Event ID: `{event.event_id}`
- Region: {event.region}
- Status: {event.status}
- Severity: {event.severity}
- Confidence: {event.confidence:.2f}
- Start: {event.start_time}
- End: {event.end_time or "ongoing/unknown"}
- Bounding box: {event.bbox or "unknown"}

## Timeline

- {event.start_time}: first observed or inferred flood signal.
- {event.end_time or "Unknown"}: event end time.

## Spatial Distribution

- Flood extent: {"available" if event.flood_extent else "not available"}
- Bounding box / source area: {event.bbox or "unknown"}
- Depth observation count: {len(event.depth_observations)}
- Maximum observed depth: {f"{max_depth:.2f} m" if max_depth is not None else "unknown"}

## Water Depth Evidence

{depth_lines}

## Cross-Source Estimates

{inference_lines}

## Hydro-Meteorological Records

- Rainfall records: {len(event.rainfall_records)}
- Water-level records: {len(event.water_level_records)}
- Tide records: {len(event.tide_records)}

### Rainfall

{rainfall_lines}

### Water Level

{water_level_lines}

## Evidence Summary

{evidence_lines}
"""

    def write(self, event: FloodEvent, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render_markdown(event), encoding="utf-8")
        return path
