from __future__ import annotations

import unittest
from unittest.mock import patch

from control_plane.resilience_runtime import build_slot_plan, normalize_channel_name, resolve_feed_ips


class ResilienceRuntimeTests(unittest.TestCase):
    def test_normalize_depth_channel(self) -> None:
        self.assertEqual(normalize_channel_name("push.depth"), "push.depth.full")
        self.assertEqual(normalize_channel_name("push.kline"), "push.kline")

    @patch("control_plane.resilience_runtime.socket.getaddrinfo")
    def test_resolve_feed_ips_round_robin(self, mock_getaddrinfo) -> None:
        mock_getaddrinfo.return_value = [
            (None, None, None, None, ("1.1.1.1", 443)),
            (None, None, None, None, ("2.2.2.2", 443)),
            (None, None, None, None, ("1.1.1.1", 443)),
        ]
        ips = resolve_feed_ips(5, "contract.mexc.com", 443)
        self.assertEqual(ips, ["1.1.1.1", "2.2.2.2", "1.1.1.1", "2.2.2.2", "1.1.1.1"])

    def test_build_slot_plan_has_aux_and_duplicated_critical(self) -> None:
        slots = build_slot_plan(
            symbols=["BTC_USDT", "ETH_USDT", "SOL_USDT"],
            channels=[
                "push.deal",
                "push.kline",
                "push.depth.full",
                "push.ticker",
                "push.funding.rate",
                "push.index.price",
                "push.fair.price",
            ],
            intervals=["Min1", "Min5"],
            capture_feeds=2,
            tier1_dedicated=True,
            feed_path_diversity=False,
        )
        labels = [s.label for s in slots]
        self.assertIn("aux", labels)
        self.assertIn("tier1-BTC_USDT", labels)
        self.assertIn("tier1-BTC_USDT-dup1", labels)
        self.assertEqual(len(slots), 7)


if __name__ == "__main__":
    unittest.main()
