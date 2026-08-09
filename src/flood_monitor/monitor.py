"""Flood Monitor public API facade."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .collect import CollectionPipeline
from .demo import load_hk_one_year_demo
from .drainage import DrainageAnalyzer
from .extract import ExtractionPipeline
from .gis import FloodMap
from .model import FloodModelPipeline, ModelNotConfiguredError
from .models import Evidence, FloodEvent, Observation, RunManifest, SourceRecord
from .query import event_matches_query
from .render_html import write_html_pair
from .sources import (
    ArcGISFeatureServerSource,
    GeoJSONSource,
    HKOSource,
    LocalFileEvidenceSource,
    NewsSource,
    RSSFeedSource,
    SourceAdapter,
    WebArticleSource,
    GDELTMediaSearchSource,
)


class FloodMonitor:
    def __init__(self, sources: list[SourceAdapter] | None = None, region: str = "Hong Kong") -> None:
        self.region = region
        self.sources = sources or []
        self.collection = CollectionPipeline(self.sources)
        self.extraction = ExtractionPipeline(region=region)
        self.model = FloodModelPipeline()
        self.drainage = DrainageAnalyzer()
        self._source_records: list[SourceRecord] = []
        self._observations: list[Observation] = []
        self._events: dict[str, FloodEvent] = {}
        self._flood_fields = []
        self._drainage_assessments = []
        self.source_errors: list[str] = []
        self.manifest: RunManifest | None = None

    def search(self, **query: Any) -> list[FloodEvent]:
        self.manifest = RunManifest(
            requested_region=str(query.get("region") or self.region),
            requested_time_range={"start": query.get("start_time"), "end": query.get("end_time")},
            skills_used=["flood-monitor-collect", "flood-monitor-extract", "flood-monitor-report"],
            configuration={key: value for key, value in query.items() if "key" not in key.lower() and "token" not in key.lower()},
        )
        records = self.collect(**query)
        events = self.extract(records)
        events = [event for event in events if event_matches_query(event, **query)]
        for event in events:
            self._events[event.event_id] = event
        self.manifest.event_count = len(events)
        self.manifest.finish()
        return events

    def collect(self, **query: Any) -> list[SourceRecord]:
        """Acquire normalized source records without declaring flood events."""
        result = self.collection.collect(**query)
        self._source_records = result.records
        self.source_errors = result.errors
        if self.manifest:
            self.manifest.source_counts = result.source_counts
            self.manifest.warnings.extend(result.errors)
        return result.records

    def extract(self, records: list[SourceRecord] | None = None) -> list[FloodEvent]:
        """Interpret raw records as observations and consolidated flood events."""
        result = self.extraction.extract(records if records is not None else self._source_records)
        self._observations = result.observations
        if self.manifest:
            self.manifest.observation_count = len(result.observations)
        return result.events

    def add_evidence(self, evidence: Evidence) -> list[FloodEvent]:
        self._source_records.append(evidence)
        events = self.extract([evidence])
        for event in events:
            self._events[event.event_id] = event
        return events

    def get_event(self, event_id: str) -> FloodEvent | None:
        return self._events.get(event_id)

    def get_events(self) -> list[FloodEvent]:
        return list(self._events.values())

    def get_source_records(self) -> list[SourceRecord]:
        return list(self._source_records)

    def get_observations(self) -> list[Observation]:
        return list(self._observations)

    @classmethod
    def hong_kong_live(
        cls,
        *,
        rainfall_threshold_mm: float = 30.0,
        include_rainfall_below_threshold: bool = False,
        raise_on_error: bool = True,
        rss_urls: list[str] | None = None,
        article_urls: list[str] | None = None,
        geojson_urls: list[str] | None = None,
        arcgis_urls: list[str] | None = None,
        local_files: list[str] | None = None,
        media_search: bool = False,
    ) -> "FloodMonitor":
        sources: list[SourceAdapter] = [
            HKOSource(
                    {
                        "rainfall_threshold_mm": rainfall_threshold_mm,
                        "include_rainfall_below_threshold": include_rainfall_below_threshold,
                        "raise_on_error": raise_on_error,
                    }
            ),
            HKOSource({"mode": "warning_summary", "raise_on_error": raise_on_error}),
        ]
        if rss_urls:
            sources.append(RSSFeedSource("rss_media", {"urls": rss_urls}))
        if media_search:
            sources.append(GDELTMediaSearchSource())
        if article_urls:
            sources.append(WebArticleSource("web_articles", {"urls": article_urls}))
        for idx, url in enumerate(geojson_urls or []):
            sources.append(GeoJSONSource(f"geojson_{idx + 1}", {"url": url, "source_type": "remote_sensing"}))
        for idx, url in enumerate(arcgis_urls or []):
            sources.append(ArcGISFeatureServerSource(f"arcgis_{idx + 1}", {"url": url}))
        for idx, path in enumerate(local_files or []):
            sources.append(LocalFileEvidenceSource(f"local_file_{idx + 1}", {"path": path}))
        return cls(sources, region="Hong Kong")

    @classmethod
    def multisource(
        cls,
        *,
        region: str = "Hong Kong",
        rss_urls: list[str] | None = None,
        article_urls: list[str] | None = None,
        geojson_urls: list[str] | None = None,
        arcgis_urls: list[str] | None = None,
        local_files: list[str] | None = None,
        media_search: bool = False,
    ) -> "FloodMonitor":
        sources: list[SourceAdapter] = []
        if rss_urls:
            sources.append(RSSFeedSource("rss_media", {"urls": rss_urls}))
        if media_search:
            sources.append(GDELTMediaSearchSource())
        if article_urls:
            sources.append(WebArticleSource("web_articles", {"urls": article_urls}))
        for idx, url in enumerate(geojson_urls or []):
            sources.append(GeoJSONSource(f"geojson_{idx + 1}", {"url": url, "source_type": "remote_sensing"}))
        for idx, url in enumerate(arcgis_urls or []):
            sources.append(ArcGISFeatureServerSource(f"arcgis_{idx + 1}", {"url": url}))
        for idx, path in enumerate(local_files or []):
            sources.append(LocalFileEvidenceSource(f"local_file_{idx + 1}", {"path": path}))
        return cls(sources, region=region)

    def map(
        self,
        events: FloodEvent | list[FloodEvent] | None = None,
        output_path: str | Path = "map.html",
        template_path: str | Path | None = None,
        database_filename: str | None = None,
        reader_output_path: str | Path | None = None,
    ) -> Path:
        event_list = self._coerce_events(events)
        html_path = Path(output_path)
        database_path = html_path.with_name(database_filename or "flood_data.json")
        reader_path = Path(reader_output_path) if reader_output_path else html_path.with_name("template.html")
        FloodMap().write_database(
            event_list,
            database_path,
            observations=self._observations,
            source_records=self._source_records,
            flood_fields=self._flood_fields,
            drainage_assessments=self._drainage_assessments,
            manifest=self.manifest,
        )
        write_html_pair(
            database_path,
            injected_output=html_path,
            reader_output=reader_path,
            template_path=template_path or Path(__file__).with_name("template.html"),
        )
        return html_path

    def to_json(self) -> str:
        return json.dumps([event.to_dict() for event in self.get_events()], indent=2, ensure_ascii=False)

    def _coerce_events(self, events: FloodEvent | list[FloodEvent] | None) -> list[FloodEvent]:
        if events is None:
            return self.get_events()
        if isinstance(events, FloodEvent):
            return [events]
        return events

def demo_monitor() -> FloodMonitor:
    snapshot, items = load_hk_one_year_demo()
    source = NewsSource("demo_hk_public_records", {"items": items})
    monitor = FloodMonitor([source])
    monitor.search(
        start_time=snapshot["start_time"],
        end_time=snapshot["end_time"],
        region=snapshot["region"],
    )
    if monitor.manifest:
        monitor.manifest.configuration["demo_snapshot"] = snapshot
        monitor.manifest.warnings.extend(snapshot["limitations"])
    return monitor


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _load_events(path: str | Path) -> list[FloodEvent]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("events", [payload])
    return [FloodEvent.from_dict(item) for item in payload]


def _configured_monitor(args) -> FloodMonitor:
    if args.live_hk:
        return FloodMonitor.hong_kong_live(
            rainfall_threshold_mm=args.rainfall_threshold_mm,
            include_rainfall_below_threshold=args.include_rainfall_below_threshold,
            raise_on_error=True,
            rss_urls=args.rss_url,
            article_urls=args.article_url,
            geojson_urls=args.geojson_url,
            arcgis_urls=args.arcgis_url,
            local_files=args.input_file,
            media_search=args.media_search,
        )
    return FloodMonitor.multisource(
        region=args.region,
        rss_urls=args.rss_url,
        article_urls=args.article_url,
        geojson_urls=args.geojson_url,
        arcgis_urls=args.arcgis_url,
        local_files=args.input_file,
        media_search=args.media_search,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="FloodMonitor modular flood intelligence CLI")
    parser.add_argument("command", nargs="?", choices=["run", "collect", "extract", "model", "drainage", "report"], help="pipeline stage; legacy flags remain supported")
    parser.add_argument("--demo", action="store_true", help="run the bundled one-year Hong Kong public-record snapshot")
    parser.add_argument("--live-hk", action="store_true", help="fetch live Hong Kong HKO open data")
    parser.add_argument("--multisource", action="store_true", help="run configured RSS/article/GIS/file sources without default HKO sources")
    parser.add_argument("--start-time")
    parser.add_argument("--end-time")
    parser.add_argument("--region", default="Hong Kong")
    parser.add_argument("--bbox", help="min_lon,min_lat,max_lon,max_lat")
    parser.add_argument("--rainfall-threshold-mm", type=float, default=30.0)
    parser.add_argument("--include-rainfall-below-threshold", action="store_true")
    parser.add_argument("--rss-url", action="append", default=[], help="RSS/Atom feed URL to scan for flood reports; can repeat")
    parser.add_argument("--media-search", action="store_true", help="search public news coverage through GDELT DOC API")
    parser.add_argument("--max-media-records", type=int, default=50)
    parser.add_argument("--strict-sources", action="store_true", help="fail the run if any configured source cannot be fetched")
    parser.add_argument("--diagnostics", action="store_true", help="print source collection diagnostics to stderr")
    parser.add_argument("--article-url", action="append", default=[], help="public article URL to parse; can repeat")
    parser.add_argument("--geojson-url", action="append", default=[], help="GeoJSON URL containing flood extent or observations; can repeat")
    parser.add_argument("--arcgis-url", action="append", default=[], help="ArcGIS FeatureServer layer/query URL; can repeat")
    parser.add_argument("--input-file", action="append", default=[], help="local CSV/JSON evidence file; can repeat")
    parser.add_argument("--events-file", help="existing flood_data.json or event JSON for report/model/drainage")
    parser.add_argument("--forecast-horizon", action="append", type=int, default=[], help="forecast horizon in hours: 1, 3, or 6")
    parser.add_argument("--html-template", help="HTML template path; defaults to the packaged Flood Monitor template")
    parser.add_argument("--database-file", default="flood_data.json", help="JSON database file written beside map.html")
    parser.add_argument("--injected-html", default="map.html", help="self-contained injected HTML output")
    parser.add_argument("--reader-html", default="template.html", help="HTML output that reads the JSON database file")
    parser.add_argument("--print-json", action="store_true", help="also print event JSON to stdout")
    parser.add_argument("--output-dir", default="flood-monitor-demo-output")
    args = parser.parse_args()
    command = args.command or "run"
    if args.demo:
        monitor = demo_monitor()
    elif command == "report" and args.events_file:
        monitor = FloodMonitor(region=args.region)
        events = _load_events(args.events_file)
        monitor._events = {event.event_id: event for event in events}
        monitor.manifest = RunManifest(
            requested_region=args.region,
            requested_time_range={"start": args.start_time, "end": args.end_time},
            skills_used=["flood-monitor-report"],
        )
        monitor.manifest.event_count = len(events)
        monitor.manifest.finish()
    else:
        monitor = _configured_monitor(args)
        if command == "collect":
            monitor.manifest = RunManifest(
                requested_region=args.region,
                requested_time_range={"start": args.start_time, "end": args.end_time},
                skills_used=["flood-monitor-collect"],
            )
            monitor.collect(
                start_time=args.start_time,
                end_time=args.end_time,
                region=args.region,
                bbox=args.bbox,
                max_media_records=args.max_media_records,
                strict_sources=args.strict_sources,
            )
            monitor.manifest.finish()
        else:
            monitor.search(
                start_time=args.start_time,
                end_time=args.end_time,
                region=args.region,
                bbox=args.bbox,
                max_media_records=args.max_media_records,
                strict_sources=args.strict_sources,
            )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if command == "collect" and not args.demo:
        source_path = _write_json(out / "source_records.json", [item.to_dict() for item in monitor.get_source_records()])
        if monitor.manifest:
            monitor.manifest.outputs.append(str(source_path))
            _write_json(out / "run_manifest.json", monitor.manifest.to_dict())
    else:
        events = monitor.get_events()
        if command == "model":
            if args.events_file:
                events = _load_events(args.events_file)
            try:
                monitor._flood_fields = monitor.model.reconstruct(
                    monitor.get_observations(), events, forcing={}, run_id=monitor.manifest.run_id if monitor.manifest else "untracked"
                )
                if args.forecast_horizon:
                    monitor._flood_fields.extend(
                        monitor.model.forecast(
                            monitor._flood_fields,
                            horizons_hours=args.forecast_horizon,
                            forcing={},
                            run_id=monitor.manifest.run_id if monitor.manifest else "untracked",
                        )
                    )
            except ModelNotConfiguredError as exc:
                parser.error(str(exc))
        if command == "drainage":
            if args.events_file:
                events = _load_events(args.events_file)
            monitor._drainage_assessments = monitor.drainage.assess(events)
            if monitor.manifest and "flood-monitor-drainage" not in monitor.manifest.skills_used:
                monitor.manifest.skills_used.insert(-1, "flood-monitor-drainage")
        map_path = monitor.map(
            events,
            out / args.injected_html,
            template_path=args.html_template,
            database_filename=args.database_file,
            reader_output_path=out / args.reader_html,
        )
        _write_json(out / "observations.json", [item.to_dict() for item in monitor.get_observations()])
        if monitor._flood_fields:
            _write_json(out / "model_results.json", [item.to_dict() for item in monitor._flood_fields])
        if monitor._drainage_assessments:
            _write_json(out / "drainage_results.json", [item.to_dict() for item in monitor._drainage_assessments])
        if monitor.manifest:
            monitor.manifest.outputs.extend([str(out / args.database_file), str(map_path), str(out / args.reader_html)])
            _write_json(out / "run_manifest.json", monitor.manifest.to_dict())
    if args.diagnostics and monitor.source_errors:
        print("FloodMonitor source errors:", file=sys.stderr)
        for error in monitor.source_errors:
            print(f"- {error}", file=sys.stderr)
    if args.print_json:
        print(monitor.to_json())


if __name__ == "__main__":
    main()
