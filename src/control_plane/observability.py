from __future__ import annotations

import asyncio
import json
import resource
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ObservabilityConfig:
    sample_interval_sec: float = 1.0
    history_sec: int = 60
    incident_cooldown_sec: float = 15.0
    rss_trigger_kb: int = 450_000
    cpu_trigger_pct: float = 80.0
    queue_trigger_depth: int = 10_000
    memory_psi_some_avg10_trigger: float = 0.25
    cpu_psi_some_avg10_trigger: float = 0.50
    cpu_spike_pct: float = 25.0
    rss_spike_step_kb: int = 8192
    queue_spike_depth: int = 1000


def _rss_kb() -> int:
    status = Path("/proc/self/status").read_text(encoding="utf-8")
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return 0


def _parse_pressure_file(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    out: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.strip().split()
        if not parts:
            continue
        kind = parts[0]
        for token in parts[1:]:
            if "=" not in token:
                continue
            key, raw = token.split("=", 1)
            try:
                out[f"{kind}_{key}"] = float(raw)
            except ValueError:
                continue
    return out


def _cgroup_pressure_root() -> Path | None:
    cgroup_path = "/"
    try:
        for line in Path("/proc/self/cgroup").read_text(encoding="utf-8").splitlines():
            parts = line.split(":")
            if len(parts) == 3:
                cgroup_path = parts[2] or "/"
                break
    except OSError:
        return None
    cgroup_root = Path("/sys/fs/cgroup")
    if cgroup_path.startswith("/"):
        candidate = cgroup_root / cgroup_path[1:]
    else:
        candidate = cgroup_root / cgroup_path
    return candidate if candidate.exists() else None


def read_psi_snapshot() -> dict[str, float]:
    result: dict[str, float] = {}
    cgroup_root = _cgroup_pressure_root()
    for resource_name in ("cpu", "memory", "io"):
        cgroup_file = None if cgroup_root is None else cgroup_root / f"{resource_name}.pressure"
        if cgroup_file is not None and cgroup_file.exists():
            values = _parse_pressure_file(cgroup_file)
        else:
            values = _parse_pressure_file(Path(f"/proc/pressure/{resource_name}"))
        for k, v in values.items():
            result[f"{resource_name}_{k}"] = v
    return result


class ObservabilityMonitor:
    def __init__(
        self,
        config: ObservabilityConfig,
        metrics_provider: Callable[[], dict[str, int | float]],
    ) -> None:
        self.config = config
        self.metrics_provider = metrics_provider
        self.history: deque[dict[str, Any]] = deque(maxlen=max(1, int(config.history_sec / config.sample_interval_sec)))
        self.full_samples: list[dict[str, Any]] = []
        self.incidents: list[dict[str, Any]] = []
        self.spikes: list[dict[str, Any]] = []
        self.stage_transitions: list[dict[str, Any]] = []
        self._task: asyncio.Task[None] | None = None
        self._stop_evt = asyncio.Event()
        self._last_incident_ts = 0.0
        self._cpu_prev = resource.getrusage(resource.RUSAGE_SELF)
        self._cpu_prev_ts = time.monotonic()
        self.sample_count = 0
        self.max_rss_kb = 0
        self.max_cpu_pct = 0.0
        self.max_queue_depth = 0

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_evt.set()
        if self._task is not None:
            await self._task

    async def _run(self) -> None:
        while not self._stop_evt.is_set():
            now_wall = time.time()
            now_mono = time.monotonic()
            usage = resource.getrusage(resource.RUSAGE_SELF)
            dt = max(1e-6, now_mono - self._cpu_prev_ts)
            cpu_dt = max(0.0, (usage.ru_utime + usage.ru_stime) - (self._cpu_prev.ru_utime + self._cpu_prev.ru_stime))
            cpu_pct = (cpu_dt / dt) * 100.0
            self._cpu_prev = usage
            self._cpu_prev_ts = now_mono

            sample: dict[str, Any] = {
                "ts": now_wall,
                "rss_kb": _rss_kb(),
                "cpu_pct": round(cpu_pct, 3),
            }
            sample.update(self.metrics_provider())
            sample.update(read_psi_snapshot())
            self.history.append(sample)
            self.full_samples.append(sample)
            self.sample_count += 1
            self.max_rss_kb = max(self.max_rss_kb, int(sample.get("rss_kb", 0)))
            self.max_cpu_pct = max(self.max_cpu_pct, float(sample.get("cpu_pct", 0.0)))
            self.max_queue_depth = max(self.max_queue_depth, int(sample.get("queue_depth", 0)))

            incident = self._maybe_incident(sample)
            if incident is not None:
                self.incidents.append(incident)
            self._maybe_spikes(sample)

            await asyncio.sleep(self.config.sample_interval_sec)

    def _maybe_incident(self, sample: dict[str, Any]) -> dict[str, Any] | None:
        now = float(sample["ts"])
        if now - self._last_incident_ts < self.config.incident_cooldown_sec:
            return None

        trigger_kind = ""
        if float(sample.get("rss_kb", 0.0)) >= self.config.rss_trigger_kb:
            trigger_kind = "memory_rss_breach"
        elif float(sample.get("memory_some_avg10", 0.0)) >= self.config.memory_psi_some_avg10_trigger:
            trigger_kind = "memory_pressure"
        elif float(sample.get("cpu_pct", 0.0)) >= self.config.cpu_trigger_pct:
            trigger_kind = "cpu_saturation"
        elif float(sample.get("cpu_some_avg10", 0.0)) >= self.config.cpu_psi_some_avg10_trigger:
            trigger_kind = "cpu_pressure"
        elif float(sample.get("queue_depth", 0.0)) >= self.config.queue_trigger_depth:
            trigger_kind = "queue_pressure"

        if not trigger_kind:
            return None

        self._last_incident_ts = now
        recent = list(self.history)[-min(10, len(self.history)) :]
        max_cpu = max((float(x.get("cpu_pct", 0.0)) for x in recent), default=0.0)
        max_rss = max((float(x.get("rss_kb", 0.0)) for x in recent), default=0.0)
        max_queue = max((float(x.get("queue_depth", 0.0)) for x in recent), default=0.0)

        return {
            "incident_id": f"inc-{int(now * 1_000_000)}",
            "trigger_time": now,
            "trigger_kind": trigger_kind,
            "window_pre_sec": min(self.config.history_sec, 10),
            "window_post_sec": 0,
            "psi_cpu_some": float(sample.get("cpu_some_avg10", 0.0)),
            "psi_mem_some": float(sample.get("memory_some_avg10", 0.0)),
            "psi_io_some": float(sample.get("io_some_avg10", 0.0)),
            "rss_kb": int(sample.get("rss_kb", 0)),
            "cpu_pct": float(sample.get("cpu_pct", 0.0)),
            "queue_depth": int(sample.get("queue_depth", 0)),
            "write_lag_ms": float(sample.get("write_lag_ms", 0.0)),
            "top_stage": str(sample.get("top_stage", "unknown")),
            "top_stage_share_pct": float(sample.get("top_stage_share_pct", 0.0)),
            "action_taken": "observe_only",
            "confidence": 0.8,
            "context_json": json.dumps(
                {
                    "max_cpu_pct_10s": round(max_cpu, 3),
                    "max_rss_kb_10s": int(max_rss),
                    "max_queue_depth_10s": int(max_queue),
                    "drops_total": int(sample.get("drops_total", 0)),
                },
                separators=(",", ":"),
                ensure_ascii=True,
            ),
        }

    def _maybe_spikes(self, sample: dict[str, Any]) -> None:
        if float(sample.get("cpu_pct", 0.0)) >= self.config.cpu_spike_pct:
            self.spikes.append(
                {
                    "ts": float(sample.get("ts", 0.0)),
                    "kind": "cpu_spike",
                    "value": float(sample.get("cpu_pct", 0.0)),
                    "stage": str(sample.get("top_stage", "unknown")),
                }
            )
        if int(sample.get("queue_depth", 0)) >= self.config.queue_spike_depth:
            self.spikes.append(
                {
                    "ts": float(sample.get("ts", 0.0)),
                    "kind": "queue_spike",
                    "value": int(sample.get("queue_depth", 0)),
                    "stage": str(sample.get("top_stage", "unknown")),
                }
            )
        if len(self.full_samples) >= 2:
            prev = self.full_samples[-2]
            rss_now = int(sample.get("rss_kb", 0))
            rss_prev = int(prev.get("rss_kb", 0))
            delta = rss_now - rss_prev
            if delta >= self.config.rss_spike_step_kb:
                self.spikes.append(
                    {
                        "ts": float(sample.get("ts", 0.0)),
                        "kind": "rss_step_spike",
                        "value": delta,
                        "stage": str(sample.get("top_stage", "unknown")),
                    }
                )

    def record_stage_transition(self, from_stage: str, to_stage: str, elapsed_sec: float) -> None:
        self.stage_transitions.append(
            {
                "ts": time.time(),
                "kind": "stage_transition",
                "from_stage": from_stage,
                "to_stage": to_stage,
                "elapsed_sec": round(max(0.0, elapsed_sec), 6),
            }
        )

    def latest_snapshot(self) -> dict[str, Any]:
        if not self.history:
            return {}
        return dict(self.history[-1])

    def rollup(self) -> dict[str, Any]:
        def _pctl(values: list[float], pct: float) -> float:
            if not values:
                return 0.0
            sorted_vals = sorted(values)
            idx = int((len(sorted_vals) - 1) * pct)
            return float(sorted_vals[idx])

        cpu_vals = [float(x.get("cpu_pct", 0.0)) for x in self.full_samples]
        rss_vals = [float(x.get("rss_kb", 0.0)) for x in self.full_samples]
        q_vals = [float(x.get("queue_depth", 0.0)) for x in self.full_samples]
        return {
            "sample_count": self.sample_count,
            "max_rss_kb": self.max_rss_kb,
            "max_cpu_pct": round(self.max_cpu_pct, 3),
            "max_queue_depth": self.max_queue_depth,
            "incident_count": len(self.incidents),
            "spike_count": len(self.spikes),
            "stage_transition_count": len(self.stage_transitions),
            "cpu_p95_pct": round(_pctl(cpu_vals, 0.95), 3),
            "cpu_p99_pct": round(_pctl(cpu_vals, 0.99), 3),
            "rss_p95_kb": int(_pctl(rss_vals, 0.95)),
            "rss_p99_kb": int(_pctl(rss_vals, 0.99)),
            "queue_p95": int(_pctl(q_vals, 0.95)),
            "queue_p99": int(_pctl(q_vals, 0.99)),
        }

    def write_artifacts(self, out_dir: Path) -> dict[str, str]:
        out_dir.mkdir(parents=True, exist_ok=True)
        samples_path = out_dir / "observability_samples.ndjson"
        incidents_path = out_dir / "observability_incidents.ndjson"
        spikes_path = out_dir / "observability_spikes.ndjson"
        transitions_path = out_dir / "observability_stage_transitions.ndjson"

        with samples_path.open("w", encoding="utf-8") as f:
            for row in self.full_samples:
                f.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n")

        with incidents_path.open("w", encoding="utf-8") as f:
            for row in self.incidents:
                f.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n")

        with spikes_path.open("w", encoding="utf-8") as f:
            for row in self.spikes:
                f.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n")

        with transitions_path.open("w", encoding="utf-8") as f:
            for row in self.stage_transitions:
                f.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n")

        return {
            "samples": str(samples_path),
            "incidents": str(incidents_path),
            "spikes": str(spikes_path),
            "stage_transitions": str(transitions_path),
        }
