"""Evidence-labelled hotspot and drainage association analysis."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..schemas import DrainageAssessment, FloodEvent, FloodField


class DrainageAnalyzer:
    """Summarize recurrent flooding without asserting unsupported causality."""

    def assess(
        self,
        events: list[FloodEvent],
        *,
        assets: list[dict[str, Any]] | None = None,
        model_fields: list[FloodField] | None = None,
    ) -> list[DrainageAssessment]:
        by_place: dict[str, list[FloodEvent]] = defaultdict(list)
        for event in events:
            place = next((item.location_name for item in event.evidence if item.location_name), event.region)
            by_place[place].append(event)
        assessments: list[DrainageAssessment] = []
        for place, place_events in by_place.items():
            associated = [asset for asset in assets or [] if self._same_spatial_unit(asset, place)]
            hypotheses = []
            follow_up = []
            if associated:
                hypotheses.append(
                    {
                        "type": "spatial_association",
                        "statement": "Flood observations and drainage assets share the same declared spatial unit.",
                        "support": "proximity_or_name_match_only",
                        "causal_status": "not_established",
                    }
                )
                follow_up.append("Check asset condition, capacity, surcharge history, and downstream boundary conditions before causal attribution.")
            if len(place_events) > 1:
                follow_up.append("Review recurrence across independent storms and normalize by observation coverage.")
            assessments.append(
                DrainageAssessment(
                    spatial_unit=place,
                    associated_assets=associated,
                    flood_history={
                        "event_count": len(place_events),
                        "event_ids": [event.event_id for event in place_events],
                        "max_reported_depth_m": self._max_depth(place_events),
                    },
                    model_indicators={"field_ids": [field.field_id for field in model_fields or []]},
                    diagnostic_hypotheses=hypotheses,
                    confidence=0.45 if associated else 0.2,
                    evidence=[event.event_id for event in place_events],
                    recommended_follow_up=follow_up or ["Add drainage asset or hydraulic-model evidence before diagnosing a bottleneck."],
                    provenance={"method": "event_frequency_and_declared_spatial_association_v1"},
                    conclusion_level="association" if associated else "hotspot_summary",
                )
            )
        return assessments

    def _same_spatial_unit(self, asset: dict[str, Any], place: str) -> bool:
        values = [asset.get("spatial_unit"), asset.get("district"), asset.get("location_name")]
        return any(str(value).lower() == place.lower() for value in values if value)

    def _max_depth(self, events: list[FloodEvent]) -> float | None:
        values = [depth.depth_m for event in events for depth in event.depth_observations if depth.depth_m is not None]
        return max(values) if values else None
