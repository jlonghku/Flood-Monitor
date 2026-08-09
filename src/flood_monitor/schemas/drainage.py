"""Drainage assessment output contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .common import JsonDict, stable_id


@dataclass(slots=True)
class DrainageAssessment:
    spatial_unit: str
    assessment_id: str | None = None
    associated_assets: list[JsonDict] = field(default_factory=list)
    flood_history: JsonDict = field(default_factory=dict)
    model_indicators: JsonDict = field(default_factory=dict)
    diagnostic_hypotheses: list[JsonDict] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    recommended_follow_up: list[str] = field(default_factory=list)
    provenance: JsonDict = field(default_factory=dict)
    conclusion_level: str = "association"

    def __post_init__(self) -> None:
        self.assessment_id = self.assessment_id or stable_id("DRN", self.spatial_unit, self.evidence)

    def to_dict(self) -> JsonDict:
        return asdict(self)
