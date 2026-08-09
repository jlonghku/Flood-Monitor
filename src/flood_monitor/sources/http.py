"""Generic HTTP JSON source adapters."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..models import Evidence
from ..query import evidence_matches_query
from .base import SourceAdapter


class SourceFetchError(RuntimeError):
    pass


def fetch_json(url: str, timeout: float = 15.0, headers: dict[str, str] | None = None) -> Any:
    request = Request(url, headers=headers or {"User-Agent": "FloodMonitor/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return json.loads(response.read().decode(charset))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise SourceFetchError(f"Failed to fetch JSON from {url}: {exc}") from exc


def fetch_text(url: str, timeout: float = 15.0, headers: dict[str, str] | None = None) -> str:
    request = Request(url, headers=headers or {"User-Agent": "FloodMonitor/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (OSError, URLError) as exc:
        raise SourceFetchError(f"Failed to fetch text from {url}: {exc}") from exc


class HTTPJsonEvidenceSource(SourceAdapter):
    """Fetch evidence from a JSON endpoint using a small mapping config."""

    def __init__(self, name: str, source_type: str, config: dict[str, Any]) -> None:
        super().__init__(name, source_type, config)

    def fetch(self, **query: Any) -> list[Evidence]:
        url = self.config["url"]
        payload = fetch_json(url, timeout=float(self.config.get("timeout", 15)))
        records = self._records(payload)
        evidence = [self._record_to_evidence(record) for record in records]
        return [item for item in evidence if evidence_matches_query(item, **query)]

    def _records(self, payload: Any) -> list[dict[str, Any]]:
        path = self.config.get("records_path")
        data = payload
        if path:
            for part in str(path).split("."):
                data = data[part] if isinstance(data, dict) else data[int(part)]
        if isinstance(data, dict):
            return [data]
        return list(data)

    def _record_to_evidence(self, record: dict[str, Any]) -> Evidence:
        mapping = self.config.get("mapping", {})
        return Evidence(
            source_type=self.source_type,
            source_name=self.name,
            url=self.config.get("url"),
            published_time=self._get(record, mapping.get("published_time")),
            observed_time=self._get(record, mapping.get("observed_time")),
            location_name=self._get(record, mapping.get("location_name")),
            raw_text=self._get(record, mapping.get("raw_text")),
            summary=self._get(record, mapping.get("summary")),
            confidence=float(self.config.get("confidence", 0.6)),
            extracted_facts={"raw_record": record},
        )

    def _get(self, record: dict[str, Any], key: str | None) -> Any:
        if not key:
            return None
        data: Any = record
        for part in key.split("."):
            if not isinstance(data, dict):
                return None
            data = data.get(part)
        return data
