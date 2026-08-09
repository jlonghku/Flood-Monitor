"""Select the minimum FloodMonitor skill chain for a request."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class WorkflowRequest:
    product: str = "event_report"
    source_types: list[str] = field(default_factory=list)
    needs_current_state: bool = False
    forecast_horizons: list[int] = field(default_factory=list)
    drainage_diagnosis: bool = False
    historical_hotspots: bool = False


def route_skills(request: WorkflowRequest) -> list[str]:
    skills = ["flood-monitor-collect", "flood-monitor-extract"]
    if request.needs_current_state or request.forecast_horizons:
        skills.append("flood-monitor-model")
    if request.drainage_diagnosis or request.historical_hotspots:
        skills.append("flood-monitor-drainage")
    skills.append("flood-monitor-report")
    return skills
