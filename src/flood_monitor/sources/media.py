"""News, social, and user-upload source adapters."""

from __future__ import annotations

from typing import Any

from ..models import Evidence
from ..query import evidence_matches_query
from .base import SourceAdapter


class NewsSource(SourceAdapter):
    def __init__(self, name: str = "news", config: dict[str, Any] | None = None) -> None:
        super().__init__(name, "news", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        items = self.config.get("items", [])
        evidence = [Evidence(source_type="news", source_name=self.name, **item) for item in items]
        return [item for item in evidence if evidence_matches_query(item, **query)]


class SocialMediaSource(SourceAdapter):
    def __init__(self, name: str = "social", config: dict[str, Any] | None = None) -> None:
        super().__init__(name, "social", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        items = self.config.get("items", [])
        evidence = [Evidence(source_type="social", source_name=self.name, **item) for item in items]
        return [item for item in evidence if evidence_matches_query(item, **query)]


class UserUploadSource(SourceAdapter):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__("user_upload", "image", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        items = self.config.get("items", [])
        evidence = [Evidence(source_type="image", source_name=self.name, **item) for item in items]
        return [item for item in evidence if evidence_matches_query(item, **query)]


class CCTVSource(SourceAdapter):
    """Normalize configured public CCTV frame metadata without interpreting pixels."""

    def __init__(self, name: str = "public_cctv", config: dict[str, Any] | None = None) -> None:
        super().__init__(name, "cctv", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        records = []
        for item in self.config.get("items", []):
            payload = dict(item)
            metadata = dict(payload.pop("metadata", {}))
            metadata.setdefault("camera_id", payload.pop("camera_id", None))
            metadata.setdefault("frame_timestamp", payload.get("observed_time") or payload.get("published_time"))
            payload.setdefault("media", [{"type": "image", "url": payload.get("frame_url")} ] if payload.get("frame_url") else [])
            payload.pop("frame_url", None)
            records.append(Evidence(source_type="cctv", source_name=self.name, metadata=metadata, **payload))
        return [item for item in records if evidence_matches_query(item, **query)]
