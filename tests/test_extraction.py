from __future__ import annotations

import unittest

from flood_monitor.extract import ExtractionPipeline
from flood_monitor.schemas import SourceRecord


class ExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = ExtractionPipeline(region="Hong Kong")

    def test_rainfall_alone_cannot_create_event(self) -> None:
        rainfall = SourceRecord(
            source_type="hko",
            publisher_or_provider="HKO",
            text="Past-hour rainfall 80 mm and black rainstorm warning.",
            observed_time="2026-06-18T10:00:00+08:00",
            extracted_facts={"is_flood_related": False, "rainfall_record": {"station_id": "A", "time": "2026-06-18T10:00:00+08:00", "rainfall_mm": 80}},
        )
        result = self.pipeline.extract([rainfall])
        self.assertEqual(result.observations, [])
        self.assertEqual(result.events, [])

    def test_text_flood_produces_observation_and_depth_range(self) -> None:
        record = SourceRecord(
            source_type="news",
            publisher_or_provider="Local News",
            text="元朗道路水浸，水深及膝，車輛受阻。",
            observed_time="2026-06-18T10:05:00+08:00",
            location_name="元朗",
            location=(114.03, 22.445),
        )
        result = self.pipeline.extract([record])
        self.assertEqual(len(result.observations), 1)
        self.assertEqual(len(result.events), 1)
        depth = result.observations[0].water_depth
        self.assertEqual(depth["depth_range_m"], [0.35, 0.55])
        self.assertEqual(depth["measured_or_inferred"], "inferred")

    def test_missing_depth_stays_missing_and_location_is_approximate(self) -> None:
        record = SourceRecord(
            source_type="news",
            publisher_or_provider="Local News",
            text="沙田有道路水浸報告。",
            observed_time="2026-06-18T10:05:00+08:00",
            location_name="Sha Tin",
            location=(114.195, 22.381),
        )
        result = self.pipeline.extract([record])
        observation = result.observations[0]
        self.assertIsNone(observation.water_depth)
        self.assertEqual(observation.location_precision, "approximate_point")
        self.assertGreater(observation.location_uncertainty, 0)
        self.assertEqual(result.events[0].depth_observations, [])

    def test_duplicate_copy_is_not_independent_confirmation(self) -> None:
        records = [
            SourceRecord(source_type="news", publisher_or_provider=name, text="元朗道路水浸，交通受阻。", url=url, observed_time="2026-06-18T10:00:00+08:00", location_name="Yuen Long")
            for name, url in [("A", "https://a.test/story"), ("B", "https://b.test/copy")]
        ]
        event = self.pipeline.extract(records).events[0]
        self.assertEqual(event.metadata["independent_source_count"], 1)
        self.assertEqual(event.verification_status, "single_source")

    def test_nearby_distinct_places_are_not_merged(self) -> None:
        records = [
            SourceRecord(source_type="news", publisher_or_provider="A", text="道路水浸", observed_time="2026-06-18T10:00:00+08:00", location_name="Road A", location=(114.100, 22.400)),
            SourceRecord(source_type="news", publisher_or_provider="B", text="道路水浸", observed_time="2026-06-18T10:02:00+08:00", location_name="Road B", location=(114.101, 22.401)),
        ]
        self.assertEqual(len(self.pipeline.extract(records).events), 2)


if __name__ == "__main__":
    unittest.main()
