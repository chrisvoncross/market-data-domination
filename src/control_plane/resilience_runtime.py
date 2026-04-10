from __future__ import annotations

import asyncio
import json
import socket
import time
from dataclasses import dataclass
from typing import Any, Callable

import picows

from control_plane.runtime_contract import RuntimeContract

TIER1_SYMBOLS = {"BTC_USDT", "ETH_USDT", "SOL_USDT"}
AUX_CHANNELS = {
    "push.depth.full",
    "push.ticker",
    "push.funding.rate",
    "push.index.price",
    "push.fair.price",
}


@dataclass
class SlotPlan:
    slot_id: int
    label: str
    channel_type: str
    channels: list[str]
    symbols: list[str]
    intervals: list[str]
    pinned_ip: str | None = None


def resolve_feed_ips(slot_count: int, host: str, port: int) -> list[str | None]:
    try:
        records = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        unique_ips = sorted({r[4][0] for r in records})
    except OSError:
        unique_ips = []
    if not unique_ips:
        return [None] * slot_count
    return [unique_ips[i % len(unique_ips)] for i in range(slot_count)]


def build_slot_plan(
    symbols: list[str],
    channels: list[str],
    intervals: list[str],
    *,
    capture_feeds: int,
    tier1_dedicated: bool,
    feed_path_diversity: bool,
    host: str = "contract.mexc.com",
    port: int = 443,
) -> list[SlotPlan]:
    slots: list[SlotPlan] = []
    slot_id = 0

    has_deal = "push.deal" in channels
    has_kline = "push.kline" in channels
    aux_channels = [x for x in channels if x in AUX_CHANNELS]

    tier1 = [s for s in symbols if s in TIER1_SYMBOLS]
    rest = [s for s in symbols if s not in TIER1_SYMBOLS]

    if tier1_dedicated and has_deal and has_kline:
        for sym in tier1:
            slots.append(
                SlotPlan(
                    slot_id=slot_id,
                    label=f"tier1-{sym}",
                    channel_type="mixed",
                    channels=["push.deal", "push.kline"],
                    symbols=[sym],
                    intervals=intervals,
                )
            )
            slot_id += 1

    if has_deal and rest:
        slots.append(
            SlotPlan(
                slot_id=slot_id,
                label="deal-shard",
                channel_type="deal",
                channels=["push.deal"],
                symbols=rest,
                intervals=intervals,
            )
        )
        slot_id += 1

    if has_kline and rest:
        slots.append(
            SlotPlan(
                slot_id=slot_id,
                label="kline-shard",
                channel_type="kline",
                channels=["push.kline"],
                symbols=rest,
                intervals=intervals,
            )
        )
        slot_id += 1

    if not tier1_dedicated:
        if has_deal:
            slots.append(
                SlotPlan(
                    slot_id=slot_id,
                    label="deal",
                    channel_type="deal",
                    channels=["push.deal"],
                    symbols=symbols,
                    intervals=intervals,
                )
            )
            slot_id += 1
        if has_kline:
            slots.append(
                SlotPlan(
                    slot_id=slot_id,
                    label="kline",
                    channel_type="kline",
                    channels=["push.kline"],
                    symbols=symbols,
                    intervals=intervals,
                )
            )
            slot_id += 1

    if aux_channels:
        slots.append(
            SlotPlan(
                slot_id=slot_id,
                label="aux",
                channel_type="aux",
                channels=aux_channels,
                symbols=symbols,
                intervals=intervals,
            )
        )
        slot_id += 1

    critical = [s for s in slots if s.channel_type in {"mixed", "deal", "kline"}]
    for dup_ix in range(1, max(1, capture_feeds)):
        for base in critical:
            slots.append(
                SlotPlan(
                    slot_id=slot_id,
                    label=f"{base.label}-dup{dup_ix}",
                    channel_type=base.channel_type,
                    channels=list(base.channels),
                    symbols=list(base.symbols),
                    intervals=list(base.intervals),
                )
            )
            slot_id += 1

    if feed_path_diversity:
        pinned_ips = resolve_feed_ips(len(slots), host=host, port=port)
        for slot, ip in zip(slots, pinned_ips):
            slot.pinned_ip = ip

    return slots


def normalize_channel_name(channel: str) -> str:
    if channel == "push.depth":
        return "push.depth.full"
    return channel


def build_subscriptions(slot: SlotPlan) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    for symbol in slot.symbols:
        for channel in slot.channels:
            if channel == "push.deal":
                msgs.append({"method": "sub.deal", "param": {"symbol": symbol}})
            elif channel == "push.kline":
                for interval in slot.intervals:
                    msgs.append({"method": "sub.kline", "param": {"symbol": symbol, "interval": interval}})
            elif channel == "push.depth.full":
                msgs.append({"method": "sub.depth.full", "param": {"symbol": symbol, "limit": 20}})
            elif channel == "push.ticker":
                msgs.append({"method": "sub.ticker", "param": {"symbol": symbol}})
            elif channel == "push.funding.rate":
                msgs.append({"method": "sub.funding.rate", "param": {"symbol": symbol}})
            elif channel == "push.index.price":
                msgs.append({"method": "sub.index.price", "param": {"symbol": symbol}})
            elif channel == "push.fair.price":
                msgs.append({"method": "sub.fair.price", "param": {"symbol": symbol}})
    return msgs


class SlotListener(picows.WSListener):
    def __init__(
        self,
        slot_id: int,
        frame_queue: asyncio.Queue[tuple[int, str]],
        on_drop: Callable[[int], None] | None = None,
    ) -> None:
        self.slot_id = slot_id
        self.frame_queue = frame_queue
        self.on_drop = on_drop
        self.disconnected = asyncio.Event()

    def on_ws_connected(self, transport: picows.WSTransport) -> None:
        self.transport = transport
        self.disconnected.clear()

    def on_ws_disconnected(self, transport: picows.WSTransport) -> None:
        self.disconnected.set()

    def on_ws_frame(self, transport: picows.WSTransport, frame: picows.WSFrame) -> None:
        if frame.msg_type != picows.WSMsgType.TEXT:
            return
        msg = frame.get_payload_as_utf8_text()
        try:
            self.frame_queue.put_nowait((self.slot_id, msg))
        except asyncio.QueueFull:
            if self.on_drop is not None:
                self.on_drop(self.slot_id)

    def send_user_specific_ping(self, transport: picows.WSTransport) -> None:
        transport.send(picows.WSMsgType.TEXT, b'{"method":"ping"}')

    def is_user_specific_pong(self, frame: picows.WSFrame) -> bool:
        if frame.msg_type not in (picows.WSMsgType.TEXT, picows.WSMsgType.BINARY):
            return False
        payload = bytes(frame.get_payload_as_memoryview()).lower()
        return b"pong" in payload or b"\"method\":\"pong\"" in payload


async def run_slot_worker(
    slot: SlotPlan,
    deadline_ts: float,
    runtime: RuntimeContract,
    merged_q: asyncio.Queue[tuple[int, str]],
    slot_metric: dict[str, Any],
    on_global_drop: Callable[[], None],
) -> None:
    backoff_sec = runtime.reconnect_backoff_base_sec
    while time.time() < deadline_ts:
        slot_metric["connect_attempts"] += 1

        def _on_drop(_slot_id: int) -> None:
            slot_metric["queue_drops"] = slot_metric.get("queue_drops", 0) + 1
            on_global_drop()

        listener = SlotListener(slot.slot_id, merged_q, on_drop=_on_drop)

        def _socket_factory(_parsed_url: Any) -> socket.socket:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(runtime.reconnect_backoff_max_sec)
            assert slot.pinned_ip is not None
            sock.connect((slot.pinned_ip, 443))
            sock.setblocking(False)
            return sock

        connect_kwargs: dict[str, Any] = {}
        if slot.pinned_ip is not None:
            connect_kwargs["socket_factory"] = _socket_factory

        try:
            transport, _ws_listener = await picows.ws_connect(
                lambda: listener,
                "wss://contract.mexc.com/edge",
                websocket_handshake_timeout=runtime.reconnect_backoff_max_sec,
                enable_auto_ping=True,
                auto_ping_idle_timeout=runtime.heartbeat_idle_timeout_sec,
                auto_ping_reply_timeout=runtime.heartbeat_reply_timeout_sec,
                auto_ping_strategy=picows.WSAutoPingStrategy.PING_PERIODICALLY,
                enable_auto_pong=True,
                max_frame_size=10 * 1024 * 1024,
                **connect_kwargs,
            )
        except Exception:
            slot_metric["connect_failures"] += 1
            await asyncio.sleep(min(backoff_sec, max(0.1, deadline_ts - time.time())))
            backoff_sec = min(backoff_sec * 2.0, runtime.reconnect_backoff_max_sec)
            continue

        slot_metric["connect_success"] += 1
        if slot_metric["connect_success"] > 1:
            slot_metric["reconnects"] += 1
        backoff_sec = runtime.reconnect_backoff_base_sec

        for msg in build_subscriptions(slot):
            transport.send(picows.WSMsgType.TEXT, json.dumps(msg).encode("utf-8"))

        while time.time() < deadline_ts:
            if listener.disconnected.is_set():
                break
            await asyncio.sleep(0.2)
        transport.send_close()
        try:
            await transport.wait_disconnected()
        except Exception:
            pass
