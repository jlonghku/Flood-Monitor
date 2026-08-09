"""Raw source record contract used by collection adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .common import BBox, JsonDict, Point, clamp01, stable_id, utc_now_iso


@dataclass(slots=True)
class SourceRecord:
    """A normalized but uninterpreted item acquired from a source.

    Legacy Evidence field names remain accepted so existing adapters and JSON
    files continue to work during the schema migration.
    """

    source_type: str
    publisher_or_provider: str | None = None
    source_id: str | None = None
    title: str | None = None
    url: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None
    text: str | None = None
    language: str | None = None
    media: list[JsonDict] = field(default_factory=list)
    geometry_if_provided: JsonDict | None = None
    metadata: JsonDict = field(default_factory=dict)
    retrieval_status: str = "ok"
    provenance: JsonDict = field(default_factory=dict)

    # Compatibility fields used by the original package and input schema.
    source_name: str | None = None
    evidence_id: str | None = None
    published_time: str | None = None
    observed_time: str | None = None
    location_name: str | None = None
    location: Point | None = None
    bbox: BBox | None = None
    raw_text: str | None = None
    summary: str | None = None
    extracted_facts: JsonDict = field(default_factory=dict)
    confidence: float = 0.5
    license: str | None = None

    def __post_init__(self) -> None:
        self.publisher_or_provider = self.publisher_or_provider or self.source_name or "unknown"
        self.source_name = self.source_name or self.publisher_or_provider
        self.published_at = self.published_at or self.published_time
        self.published_time = self.published_time or self.published_at
        self.text = self.text or self.raw_text
        self.raw_text = self.raw_text or self.text
        self.title = self.title or self.summary
        self.summary = self.summary or self.title
        self.retrieved_at = self.retrieved_at or utc_now_iso()
        self.source_id = self.source_id or self.evidence_id or stable_id(
            "SRC",
            self.source_type,
            self.publisher_or_provider,
            self.url,
            self.published_at,
            self.observed_time,
            self.text,
        )
        self.evidence_id = self.evidence_id or self.source_id
        self.confidence = clamp01(self.confidence)
        self.provenance.setdefault("source_id", self.source_id)
        if self.url:
            self.provenance.setdefault("url", self.url)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SourceRecord":
        known = {field.name for field in cls.__dataclass_fields__.values()}
        payload = {key: item for key, item in value.items() if key in known}
        if isinstance(payload.get("location"), list):
            payload["location"] = tuple(payload["location"])
        if isinstance(payload.get("bbox"), list):
            payload["bbox"] = tuple(payload["bbox"])
        extra = {key: item for key, item in value.items() if key not in known}
        payload.setdefault("metadata", {}).update(extra)
        return cls(**payload)

    def to_dict(self) -> JsonDict:
        return asdict(self)


# Backward-compatible public name.
Evidence = SourceRecord
