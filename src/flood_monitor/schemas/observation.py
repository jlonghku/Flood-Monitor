"""Extracted flood observation contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .common import JsonDict, stable_id


@dataclass(slots=True)
class Observation:
    source_id: str
    observation_type: str = "text_report"
    event_type: str = "flooding"
    observation_id: str | None = None
    observed_at: str | None = None
    time_precision: Literal["exact", "minute", "hour", "day", "approximate", "unknown"] = "unknown"
    location_text: str | None = None
    geometry: JsonDict | None = None
    location_precision: str = "unknown"
    location_uncertainty: float | None = None
    location_candidates: list[JsonDict] = field(default_factory=list)
    water_depth: JsonDict | None = None
    impacts: JsonDict = field(default_factory=dict)
    evidence_text: str | None = None
    visual_evidence: JsonDict | None = None
    extraction_method: str = "rule_assisted_text"
    extraction_confidence: float = 0.5
    provenance: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.observation_id = self.observation_id or stable_id(
            "OBS", self.source_id, self.observation_type, self.observed_at, self.location_text, self.evidence_text
        )
        self.provenance.setdefault("source_id", self.source_id)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Observation":
        known = {field.name for field in cls.__dataclass_fields__.values()}
        return cls(**{key: item for key, item in value.items() if key in known})

    def to_dict(self) -> JsonDict:
        return asdict(self)
