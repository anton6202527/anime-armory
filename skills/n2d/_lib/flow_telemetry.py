#!/usr/bin/env python3
"""Local, append-only flow telemetry for the self-contained n2d line.

This records production *control-plane* facts (stage, stop reason, cache hit,
adapter milestone and elapsed time), never prompts, credentials or media.  The
JSONL event log is the source of truth; a deterministic aggregate is rebuilt
under the same file lock so crashes cannot leave a false success counter.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

try:  # Unix/macOS production path; fallback keeps read-only tooling portable.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore


EVENT_KIND = "n2d_flow_event"
EVENT_VERSION = 1
AGGREGATE_KIND = "n2d_flow_telemetry"
EVENT_REL = Path("生产数据") / "flow_events.jsonl"
AGGREGATE_REL = Path("生产数据") / "flow_telemetry.json"
LOCK_REL = Path("生产数据") / ".flow_telemetry.lock"

# Milestone payload is intentionally allowlisted: adapter stdout/errors can
# contain provider responses or credentials and must not leak into telemetry.
SAFE_EXTRA_KEYS = {
    "clip", "group_id", "batch_id", "adapter_id", "provider", "model",
    "route", "operation", "status", "returncode", "elapsed_sec",
    "failure_class", "retryable", "paid_state_uncertain", "artifact",
    "artifact_sha256", "count", "total", "round_index", "stop_reason",
    "profile", "clip_delivery_complete", "master_delivery_complete", "publish_ready",
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def event_path(root: str | Path) -> Path:
    return Path(root) / EVENT_REL


def aggregate_path(root: str | Path) -> Path:
    return Path(root) / AGGREGATE_REL


@contextmanager
def _locked(root: str | Path):
    path = Path(root) / LOCK_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as fh:
        if fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _events(path: Path) -> list[Dict[str, Any]]:
    out: list[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            row = json.loads(line)
        except (TypeError, ValueError):
            continue
        if isinstance(row, dict) and row.get("kind") == EVENT_KIND:
            out.append(row)
    return out


def _percentile(values: Iterable[float], quantile: float) -> Optional[float]:
    rows = sorted(float(x) for x in values if isinstance(x, (int, float)) and math.isfinite(float(x)))
    if not rows:
        return None
    if len(rows) == 1:
        return round(rows[0], 3)
    pos = (len(rows) - 1) * quantile
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    value = rows[low] if low == high else rows[low] + (rows[high] - rows[low]) * (pos - low)
    return round(value, 3)


def aggregate(events: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    stops: Counter[str] = Counter()
    stages: Counter[str] = Counter()
    milestones: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    previous: Dict[str, str] = {}
    latencies: list[float] = []
    prework_total = prework_hits = 0
    next_count = milestone_count = 0
    for row in events:
        episode = str(row.get("episode") or "全集")
        stage = str(row.get("stage") or "none")
        if stage:
            stages[stage] += 1
        event_type = str(row.get("event_type") or "")
        if event_type == "next_action":
            next_count += 1
            stop = str(row.get("stop_reason") or "unknown")
            stops[stop] += 1
            elapsed = row.get("elapsed_ms")
            if isinstance(elapsed, (int, float)):
                latencies.append(float(elapsed))
            summary = row.get("prework") if isinstance(row.get("prework"), Mapping) else {}
            prework_total += int(summary.get("total") or 0)
            prework_hits += int(summary.get("cache_hits") or 0)
            prev = previous.get(episode)
            if prev and prev != stage:
                transitions[f"{prev}->{stage}"] += 1
            previous[episode] = stage
        elif event_type == "milestone":
            milestone_count += 1
            milestones[str(row.get("milestone") or "unknown")] += 1
    return {
        "kind": AGGREGATE_KIND,
        "version": EVENT_VERSION,
        "updated_at": _now(),
        "event_count": len(events),
        "next_action_count": next_count,
        "milestone_count": milestone_count,
        "stop_reasons": dict(sorted(stops.items())),
        "stages": dict(sorted(stages.items())),
        "milestones": dict(sorted(milestones.items())),
        "stage_transitions": dict(sorted(transitions.items())),
        "prework": {
            "total": prework_total,
            "cache_hits": prework_hits,
            "cache_hit_rate": round(prework_hits / prework_total, 4) if prework_total else None,
        },
        "orchestrator_latency_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "max": round(max(latencies), 3) if latencies else None,
        },
        "last_event_at": str(events[-1].get("at") or "") if events else "",
    }


def append_event(root: str | Path, event: Mapping[str, Any]) -> Dict[str, Any]:
    root_path = Path(root)
    row = {
        "kind": EVENT_KIND,
        "version": EVENT_VERSION,
        "at": _now(),
        **dict(event),
    }
    with _locked(root_path):
        path = event_path(root_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            fh.flush()
        report = aggregate(_events(path))
        _atomic_json(aggregate_path(root_path), report)
    return row


def record_next_action(root: str | Path, payload: Mapping[str, Any], elapsed_ms: float) -> Dict[str, Any]:
    frontier = payload.get("frontier") if isinstance(payload.get("frontier"), Mapping) else {}
    prework = [row for row in (payload.get("prework") or []) if isinstance(row, Mapping)]
    status_counts = Counter(str(row.get("status") or "unknown").lower() for row in prework)
    gate = payload.get("gate") if isinstance(payload.get("gate"), Mapping) else {}
    trace = payload.get("trace") if isinstance(payload.get("trace"), Mapping) else {}
    return append_event(root, {
        "event_type": "next_action",
        "episode": str(frontier.get("ep") or ""),
        "stage": str(frontier.get("stage_key") or frontier.get("label") or "done"),
        "stop_reason": str(payload.get("stop_reason") or "unknown"),
        "elapsed_ms": round(float(elapsed_ms), 3),
        "prework": {
            "total": len(prework),
            "cache_hits": sum(1 for row in prework if row.get("_cached") is True),
            "statuses": dict(sorted(status_counts.items())),
        },
        "gate": {
            "stage": str(gate.get("stage") or ""),
            "blocked": bool(gate.get("blocked")),
        },
        "trace_id": str(trace.get("trace_id") or ""),
        "span_id": str(trace.get("span_id") or ""),
    })


def record_milestone(
    root: str | Path,
    milestone: str,
    *,
    episode: str = "",
    stage: str = "",
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    safe = {str(k): v for k, v in dict(extra or {}).items() if str(k) in SAFE_EXTRA_KEYS}
    return append_event(root, {
        "event_type": "milestone",
        "milestone": str(milestone),
        "episode": str(episode),
        "stage": str(stage or "none"),
        "extra": safe,
    })


def report(root: str | Path, *, refresh: bool = True) -> Dict[str, Any]:
    path = event_path(root)
    if refresh:
        with _locked(root):
            payload = aggregate(_events(path))
            _atomic_json(aggregate_path(root), payload)
            return payload
    try:
        payload = json.loads(aggregate_path(root).read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else aggregate([])
    except (OSError, ValueError):
        return aggregate([])


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    payload = report(Path(ns.root).expanduser().resolve())
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"events={payload['event_count']} next={payload['next_action_count']} "
            f"milestones={payload['milestone_count']} cache_hit_rate={payload['prework']['cache_hit_rate']} "
            f"p50_ms={payload['orchestrator_latency_ms']['p50']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
