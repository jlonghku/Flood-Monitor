from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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
            one_year_ago = datetime.now(timezone.utc) - timedelta(days=366)
            for event in database["events"]:
                self.assertGreaterEqual(datetime.fromisoformat(event["start_time"]).astimezone(timezone.utc), one_year_ago)


if __name__ == "__main__":
    unittest.main()
