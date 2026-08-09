from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flood_monitor.extract import ExtractionPipeline
from flood_monitor.gis import FloodMap
from flood_monitor.orchestration import WorkflowRequest, route_skills
from flood_monitor.render_html import write_html_pair
from flood_monitor.schemas import RunManifest, SourceRecord


class ReportingAndRoutingTests(unittest.TestCase):
    def test_simple_search_routes_only_required_skills(self) -> None:
        skills = route_skills(WorkflowRequest(product="event_report"))
        self.assertEqual(skills, ["flood-monitor-collect", "flood-monitor-extract", "flood-monitor-report"])

    def test_model_and_drainage_routes(self) -> None:
        model = route_skills(WorkflowRequest(forecast_horizons=[1, 3]))
        drainage = route_skills(WorkflowRequest(drainage_diagnosis=True))
        self.assertIn("flood-monitor-model", model)
        self.assertNotIn("flood-monitor-drainage", model)
        self.assertIn("flood-monitor-drainage", drainage)
        self.assertNotIn("flood-monitor-model", drainage)

    def test_report_keeps_legacy_keys_and_provenance(self) -> None:
        source = SourceRecord(
            source_type="news",
            publisher_or_provider="Local News",
            text="黃大仙道路水浸，水深30厘米。",
            url="https://example.test/report",
            observed_time="2026-06-18T12:00:00+08:00",
            location_name="Wong Tai Sin",
            location=(114.193, 22.341),
        )
        result = ExtractionPipeline().extract([source])
        manifest = RunManifest("Hong Kong", {"start": None, "end": None}, skills_used=["flood-monitor-collect", "flood-monitor-extract", "flood-monitor-report"])
        database = FloodMap().to_database(result.events, observations=result.observations, source_records=[source], manifest=manifest)
        self.assertTrue({"events", "sources", "geojson"}.issubset(database))
        self.assertEqual(database["schema_version"], 2)
        self.assertEqual(database["events"][0]["source_ids"], [source.source_id])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            data = out / "flood_data.json"
            data.write_text(json.dumps(database), encoding="utf-8")
            write_html_pair(data, injected_output=out / "map.html", reader_output=out / "template.html")
            self.assertIn("flood-data", (out / "map.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
