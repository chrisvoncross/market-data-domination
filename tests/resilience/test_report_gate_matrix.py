from __future__ import annotations

import unittest


REQUIRED_CHANNELS = {
    "push.deal",
    "push.kline",
    "push.depth.full",
    "push.ticker",
    "push.funding.rate",
    "push.index.price",
    "push.fair.price",
}


def _gate_failures(report: dict) -> list[str]:
    failures: list[str] = []
    runs = report.get("runs", [])
    if not isinstance(runs, list) or not runs:
        return ["no runs"]
    for idx, run in enumerate(runs):
        prefix = f"run[{idx}]"
        if run.get("status") != "ok":
            failures.append(f"{prefix}: status!=ok")
        if int(run.get("parse_errors", 0)) != 0:
            failures.append(f"{prefix}: parse_errors")
        if int(run.get("connect_failures", 0)) != 0:
            failures.append(f"{prefix}: connect_failures")
        if run.get("missing_channels_observed"):
            failures.append(f"{prefix}: missing_channels_observed")
        counts = run.get("channel_counts", {})
        observed = {k for k, v in counts.items() if isinstance(v, int) and v > 0}
        missing = REQUIRED_CHANNELS - observed
        if missing:
            failures.append(f"{prefix}: required_channel_counts_missing")
    return failures


def _base_report() -> dict:
    return {
        "status": "pass",
        "round_count": 1,
        "runs": [
            {
                "status": "ok",
                "parse_errors": 0,
                "connect_failures": 0,
                "missing_channels_observed": [],
                "channel_counts": {ch: 1 for ch in REQUIRED_CHANNELS},
            }
        ],
    }


class ReportGateMatrixTests(unittest.TestCase):
    def test_gate_passes_clean_report(self) -> None:
        failures = _gate_failures(_base_report())
        self.assertEqual(failures, [])

    def test_gate_fails_on_missing_channels_observed(self) -> None:
        report = _base_report()
        report["runs"][0]["missing_channels_observed"] = ["push.ticker"]
        failures = _gate_failures(report)
        self.assertTrue(any("missing_channels_observed" in x for x in failures))

    def test_gate_fails_on_connect_failures(self) -> None:
        report = _base_report()
        report["runs"][0]["connect_failures"] = 2
        failures = _gate_failures(report)
        self.assertTrue(any("connect_failures" in x for x in failures))

    def test_gate_fails_on_parse_errors(self) -> None:
        report = _base_report()
        report["runs"][0]["parse_errors"] = 1
        failures = _gate_failures(report)
        self.assertTrue(any("parse_errors" in x for x in failures))

    def test_gate_fails_when_required_channel_count_missing(self) -> None:
        report = _base_report()
        del report["runs"][0]["channel_counts"]["push.funding.rate"]
        failures = _gate_failures(report)
        self.assertTrue(any("required_channel_counts_missing" in x for x in failures))


if __name__ == "__main__":
    unittest.main()
