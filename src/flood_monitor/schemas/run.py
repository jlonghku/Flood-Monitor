"""Reproducible workflow run manifest."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .common import JsonDict, stable_id, utc_now_iso


@dataclass(slots=True)
class RunManifest:
    requested_region: str
    requested_time_range: JsonDict
    run_id: str | None = None
    started_at: str = field(default_factory=utc_now_iso)
    completed_at: str | None = None
    skills_used: list[str] = field(default_factory=list)
    source_counts: dict[str, int] = field(default_factory=dict)
    observation_count: int = 0
    event_count: int = 0
    model_runs: list[JsonDict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    software_version: str = "0.2.0"
    configuration: JsonDict = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.run_id = self.run_id or stable_id(
            "RUN", self.started_at, self.requested_region, self.requested_time_range, self.configuration
        )

    def finish(self) -> None:
        self.completed_at = utc_now_iso()

    def to_dict(self) -> JsonDict:
        return asdict(self)
