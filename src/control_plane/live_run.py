from __future__ import annotations

import argparse
import asyncio
import json
import resource
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import picows

from control_plane.config import load_config
from control_plane.plan import build_first_pass_plan, validate_against_runtime_contract
from control_plane.registry import TimeframeRegistry
from control_plane.runtime_contract import RuntimeContract, load_runtime_contract


def _rss_kb() -> int:
    status = Path("/proc/self/status").read_text(encoding="utf-8")
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return 0


@dataclass
class LiveStats:
    routed_frames: int = 0
    deal_frames: int = 0
    kline_frames: int = 0
    other_frames: int = 0
    parse_errors: int = 0
    rss_samples_kb: list[int] = field(default_factory=list)

    @property
    def max_rss_kb(self) -> int:
        return max(self.rss_samples_kb) if self.rss_samples_kb else 0


class MexcListener(picows.WSListener):
    def __init__(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=50000)

    def on_ws_connected(self, transport: picows.WSTransport) -> None:
        self.transport = transport

    def on_ws_disconnected(self, transport: picows.WSTransport) -> None:
        pass

    def on_ws_frame(self, transport: picows.WSTransport, frame: picows.WSFrame) -> None:
        if frame.msg_type != picows.WSMsgType.TEXT:
            return
        msg = frame.get_payload_as_utf8_text()
        try:
            self.queue.put_nowait(msg)
        except asyncio.QueueFull:
            # Deliberate loss with backpressure signal would be counters in prod loop.
            pass


def _sub_msgs(symbol: str, intervals: list[str]) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = [{"method": "sub.deal", "param": {"symbol": symbol}}]
    for interval in intervals:
        msgs.append({"method": "sub.kline", "param": {"symbol": symbol, "interval": interval}})
    return msgs


async def _sample_rss(stats: LiveStats, stop_evt: asyncio.Event) -> None:
    while not stop_evt.is_set():
        stats.rss_samples_kb.append(_rss_kb())
        await asyncio.sleep(1.0)


def _extract_symbol(obj: dict[str, Any]) -> str:
    sym = obj.get("symbol")
    if isinstance(sym, str):
        return sym
    data = obj.get("data")
    if isinstance(data, dict):
        s2 = data.get("symbol")
        if isinstance(s2, str):
            return s2
    return ""


async def run_live(
    cfg_path: Path, runtime_path: Path, out_dir: Path, duration_sec: float
) -> dict[str, Any]:
    cfg = load_config(cfg_path)
    runtime: RuntimeContract = load_runtime_contract(runtime_path)
    registry = TimeframeRegistry.from_config(cfg)
    validate_against_runtime_contract(cfg, registry, runtime)
    plan = build_first_pass_plan(cfg, registry)

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "live_raw.ndjson"
    dp_out_path = out_dir / "live_dp_out.ndjson"
    main_log_path = out_dir / "main.log"
    summary_path = out_dir / "live_summary.json"

    listener_factory = MexcListener
    transport, listener = await picows.ws_connect(
        listener_factory,
        "wss://contract.mexc.com/edge",
        websocket_handshake_timeout=runtime.reconnect_backoff_max_sec,
        enable_auto_ping=True,
        auto_ping_idle_timeout=runtime.heartbeat_idle_timeout_sec,
        auto_ping_reply_timeout=runtime.heartbeat_reply_timeout_sec,
        auto_ping_strategy=picows.WSAutoPingStrategy.PING_WHEN_IDLE,
        enable_auto_pong=True,
    )

    intervals = plan.enabled_intervals
    for symbol in plan.symbols:
        for msg in _sub_msgs(symbol, intervals):
            transport.send(picows.WSMsgType.TEXT, json.dumps(msg).encode("utf-8"))

    stats = LiveStats()
    stop_evt = asyncio.Event()
    sampler = asyncio.create_task(_sample_rss(stats, stop_evt))
    start = time.time()
    cpu_start = resource.getrusage(resource.RUSAGE_SELF)
    deadline = start + duration_sec

    with raw_path.open("w", encoding="utf-8") as raw_file, main_log_path.open(
        "w", encoding="utf-8"
    ) as main_log:
        main_log.write(
            f"live_run_start duration_sec={duration_sec} symbols={plan.symbols} channels={plan.channels}\n"
        )
        while time.time() < deadline:
            try:
                line = await asyncio.wait_for(listener.queue.get(), timeout=1.0)
            except TimeoutError:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                stats.parse_errors += 1
                continue

            channel = obj.get("channel")
            if not isinstance(channel, str):
                stats.other_frames += 1
                continue
            if channel not in plan.channels:
                stats.other_frames += 1
                continue

            symbol = _extract_symbol(obj)
            if not symbol:
                continue

            stats.routed_frames += 1
            if channel == "push.deal":
                stats.deal_frames += 1
            elif channel == "push.kline":
                stats.kline_frames += 1

            rec = {"channel": channel, "symbol": symbol, "payload": obj}
            raw_file.write(json.dumps(rec, ensure_ascii=True) + "\n")

        stop_evt.set()
        await sampler
        transport.send_close()
        await transport.wait_disconnected()

        elapsed = time.time() - start
        main_log.write(
            f"live_run_end elapsed_sec={elapsed:.3f} routed={stats.routed_frames} "
            f"deal={stats.deal_frames} kline={stats.kline_frames} parse_errors={stats.parse_errors}\n"
        )

    with raw_path.open("rb") as fin, dp_out_path.open("wb") as fout:
        subprocess.run(
            ["cargo", "run", "--quiet", "--manifest-path", "native/data_plane/Cargo.toml"],
            stdin=fin,
            stdout=fout,
            check=True,
        )

    final_candles = 0
    mismatch = 0
    for line in dp_out_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("event_type") == "final_candle":
            final_candles += 1
        elif obj.get("event_type") == "mismatch_event":
            mismatch += 1

    elapsed = time.time() - start
    cpu_end = resource.getrusage(resource.RUSAGE_SELF)
    cpu_user_sec = max(0.0, cpu_end.ru_utime - cpu_start.ru_utime)
    cpu_sys_sec = max(0.0, cpu_end.ru_stime - cpu_start.ru_stime)
    cpu_total_sec = cpu_user_sec + cpu_sys_sec
    avg_process_cpu_pct = (cpu_total_sec / elapsed) * 100.0 if elapsed > 0 else 0.0

    summary = {
        "status": "ok",
        "contract_version": runtime.version,
        "elapsed_sec": round(elapsed, 3),
        "routed_frames": stats.routed_frames,
        "deal_frames": stats.deal_frames,
        "kline_frames": stats.kline_frames,
        "parse_errors": stats.parse_errors,
        "max_rss_kb": stats.max_rss_kb,
        "cpu_user_sec": round(cpu_user_sec, 6),
        "cpu_sys_sec": round(cpu_sys_sec, 6),
        "avg_process_cpu_pct": round(avg_process_cpu_pct, 3),
        "final_candles": final_candles,
        "mismatch_events": mismatch,
        "paths": {
            "main_log": str(main_log_path),
            "raw": str(raw_path),
            "data_plane_out": str(dp_out_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Live MEXC dry-run through native data seam")
    parser.add_argument("--config", default="docs/handover/farmer-config.json")
    parser.add_argument("--runtime-contract", default="docs/handover/mvp_runtime_contract.json")
    parser.add_argument("--duration-sec", type=float, default=45.0)
    parser.add_argument("--out-dir", default=".artifacts/live")
    args = parser.parse_args()

    summary = asyncio.run(
        run_live(
            cfg_path=Path(args.config),
            runtime_path=Path(args.runtime_contract),
            out_dir=Path(args.out_dir),
            duration_sec=args.duration_sec,
        )
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
