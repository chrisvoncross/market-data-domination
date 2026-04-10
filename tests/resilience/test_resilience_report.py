from __future__ import annotations

import json
import unittest
from pathlib import Path


class ResilienceReportTests(unittest.TestCase):
    def test_report_is_pass_when_present(self) -> None:
        report_path = Path(".artifacts/resilience/resilience_report.json")
        if not report_path.exists():
            self.skipTest("resilience report not generated yet")
        data = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("status"), "pass")
        self.assertGreaterEqual(int(data.get("round_count", 0)), 1)


if __name__ == "__main__":
    unittest.main()
