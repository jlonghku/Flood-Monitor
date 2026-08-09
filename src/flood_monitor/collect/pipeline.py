"""Source adapter orchestration without flood-event interpretation."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..schemas import SourceRecord
from ..sources import SourceAdapter
from ..sources.http import SourceFetchError


@dataclass(slots=True)
class CollectionResult:
    records: list[SourceRecord]
    errors: list[str] = field(default_factory=list)
    source_counts: dict[str, int] = field(default_factory=dict)


class CollectionPipeline:
    """Fetch raw records and make repeated acquisition idempotent by source ID."""

    def __init__(self, sources: list[SourceAdapter]) -> None:
        self.sources = sources

    def collect(self, **query) -> CollectionResult:
        records_by_id: dict[str, SourceRecord] = {}
        errors: list[str] = []
        counts: dict[str, int] = {}
        for source in self.sources:
            try:
                records = source.fetch(**query)
            except (SourceFetchError, ValueError, OSError) as exc:
                if query.get("strict_sources"):
                    raise
                errors.append(f"{source.name}: {exc}")
                continue
            for record in records:
                source_id = record.source_id or record.evidence_id
                if source_id and source_id not in records_by_id:
                    records_by_id[source_id] = record
                    counts[record.source_type] = counts.get(record.source_type, 0) + 1
        return CollectionResult(list(records_by_id.values()), errors, counts)
