from __future__ import annotations

import unittest

from flood_monitor.drainage import DrainageAnalyzer
from flood_monitor.extract import ExtractionPipeline
from flood_monitor.model import FloodModelPipeline, ModelNotConfiguredError
from flood_monitor.schemas import SourceRecord


class ModelAndDrainageTests(unittest.TestCase):
    def test_model_requires_adapter(self) -> None:
        with self.assertRaises(ModelNotConfiguredError):
            FloodModelPipeline().reconstruct([], [], run_id="RUN-test")

    def test_drainage_output_does_not_claim_causality(self) -> None:
        source = SourceRecord(source_type="news", publisher_or_provider="A", text="元朗道路水浸", location_name="Yuen Long", observed_time="2026-06-18")
        events = ExtractionPipeline().extract([source]).events
        assessment = DrainageAnalyzer().assess(events, assets=[{"asset_id": "INLET-1", "district": "Yuen Long"}])[0]
        self.assertEqual(assessment.conclusion_level, "association")
        self.assertEqual(assessment.diagnostic_hypotheses[0]["causal_status"], "not_established")


if __name__ == "__main__":
    unittest.main()
