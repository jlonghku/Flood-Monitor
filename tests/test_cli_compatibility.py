from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


class CLICompatibilityTests(unittest.TestCase):
    def test_legacy_demo_flag_generates_compatible_outputs(self) -> None:
        project = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env["PYTHONPATH"] = str(project / "src")
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, "-m", "flood_monitor.monitor", "--demo", "--output-dir", tmp],
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ("flood_data.json", "map.html", "template.html"):
                self.assertTrue((Path(tmp) / name).exists(), name)
            database = json.loads((Path(tmp) / "flood_data.json").read_text(encoding="utf-8"))
            metadata = database["metadata"]
            self.assertEqual(metadata["region"], "Hong Kong")
            self.assertEqual(metadata["start_time"], "2025-08-09T00:00:00+08:00")
            self.assertEqual(metadata["end_time"], "2026-08-09T23:59:59+08:00")
            self.assertEqual(metadata["event_count"], 32)
            self.assertEqual(metadata["named_location_count"], 31)
            self.assertEqual(metadata["official_reported_case_total"], 68)
            self.assertEqual(len(database["events"]), 32)
            self.assertEqual(len(database["source_records"]), 32)
            self.assertEqual(len(database["observations"]), 32)
            self.assertGreaterEqual(len({event["start_time"][:10] for event in database["events"]}), 6)
            for event in database["events"]:
                observed = datetime.fromisoformat(event["start_time"])
                self.assertGreaterEqual(observed, datetime.fromisoformat(metadata["start_time"]))
                self.assertLessEqual(observed, datetime.fromisoformat(metadata["end_time"]))
                self.assertEqual(event["region"], "Hong Kong")
                self.assertTrue(event["evidence"][0]["url"])
                self.assertFalse(event["depth_observations"])


if __name__ == "__main__":
    unittest.main()
