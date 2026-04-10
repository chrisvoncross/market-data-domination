# picows Resilience Deep Dive (2026-04)

## Goal

Capture the concrete `picows` features that materially improve exchange-ingress resilience with low overhead.

## Verified capabilities (official `picows` reference)

- `enable_auto_ping`: active stale-connection detection.
- `auto_ping_strategy`:
  - `PING_WHEN_IDLE`
  - `PING_PERIODICALLY`
- `auto_ping_idle_timeout`: ping cadence/idle threshold.
- `auto_ping_reply_timeout`: fail-fast timeout when pong is missing.
- `enable_auto_pong`: automatic protocol pong replies.
- `disconnect_on_exception`: disconnect on callback exceptions (prevents zombie state).
- `wait_disconnected()`: explicit async wait for disconnect completion.
- `socket_factory`: custom socket creation (for advanced path control).
- `max_frame_size`: safety guard against oversized frames.
- `notify_user_specific_pong_received()`: custom heartbeat integration when exchange uses app-level pong frames.
- `measure_roundtrip_time()`: low-cost RTT checks for diagnostics.

Official sources:
- [picows API reference (latest)](https://picows.readthedocs.io/en/latest/reference.html)
- [picows guides (latest)](https://picows.readthedocs.io/en/latest/guides.html)

## Applied policy in this repository

- Use `enable_auto_ping=True`, `enable_auto_pong=True`.
- Use `PING_PERIODICALLY` with runtime-contract heartbeat values.
- Treat disconnect as normal control event and reconnect with bounded exponential backoff.
- Keep hot-path callback lightweight (parse/minimal routing only).
- Use `max_frame_size` safety bound.
- Preserve JSON app-level pong compatibility where needed.

## Why this is appropriate

This gives robust liveness detection and controlled reconnection while keeping Python control-plane overhead low and deterministic.
