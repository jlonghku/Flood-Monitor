"""Model reconstruction and forecast output contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .common import JsonDict, stable_id


@dataclass(slots=True)
class FloodField:
    valid_time: str
    geometry_or_raster: JsonDict
    source_model: str
    field_id: str | None = None
    forecast_horizon: int = 0
    depth: JsonDict | None = None
    extent: JsonDict | None = None
    velocity_if_available: JsonDict | None = None
    model_version: str | None = None
    observation_constraints: list[str] = field(default_factory=list)
    uncertainty: JsonDict = field(default_factory=dict)
    run_id: str | None = None
    provenance: JsonDict = field(default_factory=dict)
    result_kind: str = "reconstructed"

    def __post_init__(self) -> None:
        self.field_id = self.field_id or stable_id(
            "FLD", self.source_model, self.model_version, self.valid_time, self.forecast_horizon, self.run_id
        )

    def to_dict(self) -> JsonDict:
        return asdict(self)
