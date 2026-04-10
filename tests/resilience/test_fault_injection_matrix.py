from __future__ import annotations

import asyncio
import time
import unittest
from unittest.mock import patch

from control_plane.resilience_runtime import SlotListener, SlotPlan, run_slot_worker
from control_plane.runtime_contract import RuntimeContract


class _FakeTransport:
    def __init__(self) -> None:
        self.sent = 0
        self.closed = False

    def send(self, _msg_type, _payload) -> None:
        self.sent += 1

    def send_close(self) -> None:
        self.closed = True

    async def wait_disconnected(self) -> None:
        await asyncio.sleep(0)


def _runtime_for_tests() -> RuntimeContract:
    return RuntimeContract(
        version="test",
        channels=["push.deal", "push.kline"],
        required_interval="Min1",
        dedupe_trade_id_fields=["i", "trade_id"],
        heartbeat_idle_timeout_sec=0.1,
        heartbeat_reply_timeout_sec=0.1,
        reconnect_backoff_base_sec=0.01,
        reconnect_backoff_max_sec=0.02,
        cpu_budget_pct=25.0,
        ram_budget_mb=4096,
        max_lag_ms=30000,
        max_drop_rate=0.0,
        max_write_p95_ms=60000,
    )


class FaultInjectionMatrixTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_failure_backoff_matrix(self) -> None:
        slot = SlotPlan(
            slot_id=1,
            label="test-fail",
            channel_type="deal",
            channels=["push.deal"],
            symbols=["BTC_USDT"],
            intervals=["Min1"],
            pinned_ip=None,
        )
        metric = {
            "connect_attempts": 0,
            "connect_success": 0,
            "connect_failures": 0,
            "reconnects": 0,
            "queue_drops": 0,
            "channel_counts": {},
        }
        merged_q: asyncio.Queue[tuple[int, str]] = asyncio.Queue(maxsize=10)

        async def _always_fail(*_args, **_kwargs):
            raise RuntimeError("forced connect failure")

        with patch("control_plane.resilience_runtime.picows.ws_connect", _always_fail):
            await run_slot_worker(
                slot=slot,
                deadline_ts=time.time() + 0.08,
                runtime=_runtime_for_tests(),
                merged_q=merged_q,
                slot_metric=metric,
                on_global_drop=lambda: None,
            )

        self.assertGreaterEqual(metric["connect_attempts"], 1)
        self.assertEqual(metric["connect_success"], 0)
        self.assertGreaterEqual(metric["connect_failures"], 1)

    async def test_reconnect_counter_increments_after_second_success(self) -> None:
        slot = SlotPlan(
            slot_id=2,
            label="test-reconnect",
            channel_type="deal",
            channels=["push.deal"],
            symbols=["BTC_USDT"],
            intervals=["Min1"],
            pinned_ip=None,
        )
        metric = {
            "connect_attempts": 0,
            "connect_success": 0,
            "connect_failures": 0,
            "reconnects": 0,
            "queue_drops": 0,
            "channel_counts": {},
        }
        merged_q: asyncio.Queue[tuple[int, str]] = asyncio.Queue(maxsize=10)

        async def _connect_then_disconnect(listener_factory, *_args, **_kwargs):
            listener = listener_factory()
            transport = _FakeTransport()

            async def _disconnect_soon() -> None:
                await asyncio.sleep(0.01)
                listener.disconnected.set()

            asyncio.create_task(_disconnect_soon())
            return transport, listener

        with patch("control_plane.resilience_runtime.picows.ws_connect", _connect_then_disconnect):
            await run_slot_worker(
                slot=slot,
                deadline_ts=time.time() + 0.18,
                runtime=_runtime_for_tests(),
                merged_q=merged_q,
                slot_metric=metric,
                on_global_drop=lambda: None,
            )

        self.assertGreaterEqual(metric["connect_success"], 1)
        if metric["connect_success"] > 1:
            self.assertGreaterEqual(metric["reconnects"], 1)

    def test_slot_listener_queue_drop_injection(self) -> None:
        drops: list[int] = []
        frame_q: asyncio.Queue[tuple[int, str]] = asyncio.Queue(maxsize=1)
        listener = SlotListener(slot_id=9, frame_queue=frame_q, on_drop=lambda sid: drops.append(sid))
        frame_q.put_nowait((9, "occupied"))

        class _Frame:
            msg_type = 1  # WSMsgType.TEXT in production path

            @staticmethod
            def get_payload_as_utf8_text() -> str:
                return '{"channel":"push.deal","symbol":"BTC_USDT"}'

        class _WsMsgType:
            TEXT = 1

        class _PicowsShim:
            WSMsgType = _WsMsgType

        with patch("control_plane.resilience_runtime.picows", _PicowsShim):
            listener.on_ws_frame(None, _Frame())

        self.assertEqual(drops, [9])


if __name__ == "__main__":
    unittest.main()
