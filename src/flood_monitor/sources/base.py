"""Source adapter contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..models import Evidence


@dataclass(slots=True)
class SourceAdapter:
    name: str
    source_type: str
    config: dict[str, Any] = field(default_factory=dict)

    def fetch(self, **query: Any) -> list[Evidence]:
        raise NotImplementedError


class Fetcher(Protocol):
    def __call__(self, **query: Any) -> list[Evidence]:
        ...
