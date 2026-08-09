"""Remote-sensing flood extent extraction interface."""

from __future__ import annotations

from ..models import Evidence


class RemoteSensingExtractor:
    """Normalize externally produced flood polygons.

    The class keeps a stable contract for Sentinel-1/Sentinel-2 algorithms while
    avoiding hidden dependencies in the skill package.
    """

    def from_polygon(
        self,
        polygon_geojson: dict,
        *,
        scene_id: str,
        acquisition_time: str,
        algorithm: str = "manual_or_external",
        confidence: float = 0.75,
    ) -> Evidence:
        return Evidence(
            source_type="remote_sensing",
            source_name="Sentinel or external flood extent",
            observed_time=acquisition_time,
            extracted_facts={
                "flood_extent": polygon_geojson,
                "scene_id": scene_id,
                "algorithm": algorithm,
            },
            confidence=confidence,
        )
