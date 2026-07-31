#!/usr/bin/env python3
"""Production data dashboard for n2d.

The dashboard is intentionally event based: every expensive generation or QA
gate appends one JSONL record, then this script rebuilds stable JSON/Markdown
summaries.  It keeps production metrics separate from `_进度.md`, which remains
the stage state machine.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as dt
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

SCRIPT_DIR = os.path.dirname(__file__)
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))
COMMON = os.path.join(REPO_SKILLS, "_lib")
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

try:
    from n2d_route import normalize_episode, parse_progress, stage_of
except Exception:  # pragma: no cover - dashboard still works without progress
    normalize_episode = lambda x: str(x)  # type: ignore[assignment]
    parse_progress = None  # type: ignore[assignment]
    stage_of = None  # type: ignore[assignment]

from n2d_contract import (  # 生产数据目录 / kind / 重抽原因枚举 单一真值源
    CONSISTENCY_FINDINGS_KIND,
    GATE_STAGES,
    PRODUCTION_ALERTS_KIND,
    PRODUCTION_DASHBOARD_KIND,
    PRODUCTION_DIR,
    PRODUCTION_EVENT_KIND,
    REDRAW_REASON_CATEGORIES,
    classify_redraw_reason,
    finding_dim_key,
    normalize_finding,
    production_dir,
)
from n2d_thresholds import DEFAULT_THRESHOLDS, THRESHOLDS_FILE, load_thresholds, load_benchmark  # 告警阈值单一真值源（与 n2d-score 共用）

try:
    from skill_snapshot import artifact_fingerprint  # type: ignore
except Exception:  # pragma: no cover - degraded local env
    artifact_fingerprint = None  # type: ignore[assignment]

try:
    from gate_receipt import unresolved_waivers as _gr_unresolved_waivers  # type: ignore
except Exception:  # pragma: no cover - degraded local env
    _gr_unresolved_waivers = None  # type: ignore[assignment]


def _unresolved_unverified_waivers(root: str) -> List[Dict[str, Any]]:
    """未销账的「未验证强标 ✅」债（缺凭据则空表，不阻断仪表盘自身）。"""
    if not root or _gr_unresolved_waivers is None:
        return []
    try:
        return list(_gr_unresolved_waivers(root))
    except Exception:
        return []


def loads_json_from_noisy_stdout(text: str) -> Any:
    """Parse JSON even when native model libraries print diagnostics first."""
    raw = (text or "").strip()
    if not raw:
        raise json.JSONDecodeError("empty stdout", text or "", 0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    last: Any = None
    for match in re.finditer(r"[\{\[]", text):
        try:
            obj, end = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if not text[match.start() + end:].strip():
            return obj
        last = obj
    if last is None:
        raise json.JSONDecodeError("no JSON object found", text, 0)
    return last

EVENT_KIND = PRODUCTION_EVENT_KIND
DASHBOARD_KIND = PRODUCTION_DASHBOARD_KIND
EVENT_VERSION = 1
EVENTS_FILE = "production_events.jsonl"
EVENTS_LOCK = "production_events.lock"
DASHBOARD_JSON = "dashboard.json"
DASHBOARD_MD = "dashboard.md"
DASHBOARD_HTML = "dashboard.html"
ALERTS_JSON = "alerts.json"
ALERTS_MD = "alerts.md"
PLATFORM_METRICS_STEM = "platform_metrics"
GATE_FINDINGS_PREFIX = "gate_findings"

REVENUE_PRIMARY_FIELDS = ("revenue", "gross_revenue", "total_revenue", "income", "回收", "收入")
REVENUE_COMPONENT_FIELDS = ("ad_revenue", "paid_revenue", "platform_revenue", "creator_revenue", "iap_revenue")
SPEND_FIELDS = ("distribution_spend", "promotion_spend", "ad_spend", "traffic_cost", "platform_spend", "投放成本")
PLAYS_FIELDS = ("plays", "views", "播放量")
RUNTIME_FIELDS = ("final_duration_sec", "runtime_sec", "video_duration_sec", "total_duration_sec", "duration_sec")
CURRENCY_FIELDS = ("revenue_currency", "currency", "unit")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def events_path(root: str) -> str:
    return os.path.join(production_dir(root), EVENTS_FILE)


def events_lock_path(root: str) -> str:
    return os.path.join(production_dir(root), EVENTS_LOCK)


@contextlib.contextmanager
def event_lock(root: str, *, timeout: float = 30.0, poll: float = 0.1):
    """Serialize event-ledger writes and dashboard rebuilds on local filesystems."""
    os.makedirs(production_dir(root), exist_ok=True)
    path = events_lock_path(root)
    if fcntl is not None:
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            deadline = time.time() + timeout
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.time() >= deadline:
                        raise TimeoutError(f"dashboard event lock timeout ({timeout}s): {path}")
                    time.sleep(poll)
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
    else:  # pragma: no cover - non-POSIX fallback
        deadline = time.time() + timeout
        while True:
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o644)
                break
            except FileExistsError:
                if time.time() >= deadline:
                    raise TimeoutError(f"dashboard event lock timeout ({timeout}s): {path}")
                time.sleep(poll)
        try:
            yield
        finally:
            os.close(fd)
            with contextlib.suppress(OSError):
                os.unlink(path)


def atomic_write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def gate_findings_path(root: str, episode: str, stage: str) -> str:
    return os.path.join(production_dir(root), f"{GATE_FINDINGS_PREFIX}_{stage}_{normalize_episode(episode)}.json")


def as_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def first_present(row: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def first_float(row: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
    for key in keys:
        value = as_float(row.get(key))
        if value is not None:
            return value
    return None


def hms(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def parse_meta(values: Iterable[str]) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"--meta must be key=value, got: {item}")
        key, value = item.split("=", 1)
        meta[key.strip()] = value.strip()
    return meta


def make_event(
    episode: str,
    stage: str,
    event: str,
    *,
    ts: Optional[str] = None,
    source: str = "manual",
    cost: Optional[Dict[str, Any]] = None,
    duration_sec: Optional[float] = None,
    generation: Optional[Dict[str, Any]] = None,
    qa: Optional[Dict[str, Any]] = None,
    release: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "kind": EVENT_KIND,
        "version": EVENT_VERSION,
        "ts": ts or now_iso(),
        "episode": normalize_episode(episode),
        "stage": stage,
        "event": event,
        "source": source,
    }
    if cost:
        item["cost"] = {k: v for k, v in cost.items() if v not in (None, "")}
    if duration_sec is not None:
        item["duration_sec"] = duration_sec
    if generation:
        item["generation"] = {k: v for k, v in generation.items() if v not in (None, "")}
    if qa:
        item["qa"] = {k: v for k, v in qa.items() if v not in (None, "")}
    if release:
        item["release"] = {k: v for k, v in release.items() if v not in (None, "")}
    if meta:
        item["meta"] = {k: v for k, v in meta.items() if v not in (None, "")}
    trace = trace_context(item.get("meta") if isinstance(item.get("meta"), dict) else {})
    if trace:
        item["trace"] = trace
    return item


def trace_context(meta: Dict[str, Any]) -> Dict[str, Any]:
    trace_id = str(meta.get("trace_id") or os.environ.get("N2D_TRACE_ID") or "").strip()
    task_id = str(meta.get("task_id") or os.environ.get("N2D_TASK_ID") or "").strip()
    idem = str(meta.get("idempotency_key") or os.environ.get("N2D_IDEMPOTENCY_KEY") or "").strip()
    span_id = str(meta.get("span_id") or os.environ.get("N2D_SPAN_ID") or "").strip()
    if not trace_id and (task_id or idem):
        trace_id = idem or task_id
    out = {
        "trace_id": trace_id,
        "span_id": span_id or task_id,
        "task_id": task_id,
        "idempotency_key": idem,
    }
    return {k: v for k, v in out.items() if v}


def _load_events_unlocked(root: str) -> List[Dict[str, Any]]:
    path = events_path(root)
    if not os.path.isfile(path):
        return []
    events: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSONL: {exc}") from exc
            if isinstance(item, dict):
                events.append(item)
    return events


def load_events(root: str) -> List[Dict[str, Any]]:
    with event_lock(root):
        return _load_events_unlocked(root)


def _write_events_unlocked(root: str, events: List[Dict[str, Any]]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    text = "".join(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n" for event in events)
    atomic_write_text(events_path(root), text)


def write_events(root: str, events: List[Dict[str, Any]]) -> None:
    with event_lock(root):
        _write_events_unlocked(root, events)


def _append_events_unlocked(root: str, events: Iterable[Dict[str, Any]]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    with open(events_path(root), "a", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def append_events(root: str, events: Iterable[Dict[str, Any]]) -> None:
    with event_lock(root):
        _append_events_unlocked(root, events)


def replace_events(root: str, predicate: Callable[[Dict[str, Any]], bool], new_events: List[Dict[str, Any]]) -> None:
    with event_lock(root):
        kept = [event for event in _load_events_unlocked(root) if not predicate(event)]
        kept.extend(new_events)
        _write_events_unlocked(root, kept)


def progress_index(root: str) -> Dict[str, Dict[str, Any]]:
    if parse_progress is None or stage_of is None:
        return {}
    try:
        header, rows = parse_progress(root)
    except Exception:
        return {}
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ep = row.get("_ep") or row.get("集")
        if not ep:
            continue
        try:
            route = stage_of(root, row, header)
        except Exception:
            route = {}
        index[ep] = {
            "episode": ep,
            "num": row.get("_num", 10**9),
            "next_stage": route.get("label") or "",
            "next_skill": route.get("skill") or "",
            "row": {k: v for k, v in row.items() if not k.startswith("_")},
        }
    return index


def default_input(root: str, stem: str) -> Optional[str]:
    base = production_dir(root)
    for ext in ("csv", "jsonl", "json"):
        path = os.path.join(base, f"{stem}.{ext}")
        if os.path.isfile(path):
            return path
    return None


def read_records(path: str) -> List[Dict[str, Any]]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as fh:
            return [dict(row) for row in csv.DictReader(fh)]
    if ext == ".jsonl":
        rows: List[Dict[str, Any]] = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return [row for row in rows if isinstance(row, dict)]
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return [dict(row) for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        for key in ("records", "metrics", "rows"):
            if isinstance(data.get(key), list):
                return [dict(row) for row in data[key] if isinstance(row, dict)]
    return []


def storyboard_duration(root: str, ep: str) -> Tuple[Optional[float], str]:
    path = os.path.join(root, "脚本", normalize_episode(ep), "storyboard.json")
    if not os.path.isfile(path):
        return None, ""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return None, ""
    if not isinstance(data, dict):
        return None, ""
    value = as_float(data.get("total_duration"))
    if value and value > 0:
        return value, path
    clips = data.get("clips")
    if isinstance(clips, list):
        total = 0.0
        for clip in clips:
            if isinstance(clip, dict):
                total += as_float(clip.get("duration")) or 0.0
        if total > 0:
            return total, path
    return None, ""


def blank_episode(ep: str, progress: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "episode": ep,
        "progress_next_stage": (progress or {}).get("next_stage", ""),
        "progress_next_skill": (progress or {}).get("next_skill", ""),
        "event_count": 0,
        "duration_sec": 0.0,
        "duration_hms": "0s",
        "runtime_sec": None,
        "runtime_hms": "—",
        "runtime_source": "",
        "cost_totals": {},
        "cost_by_provider": {},
        "cost_per_finished_min": {},
        "elapsed_per_finished_min_sec": None,
        "generation_attempts": 0,
        "generation_passes": 0,
        "generation_fails": 0,
        "one_pass_count": 0,
        "one_pass_rate": None,
        "redraw_count": 0,
        "redraw_rate": None,
        "redraw_reasons": {},
        "redraw_categories": {},
        "qa_gate_runs": 0,
        "qa_gate_passes": 0,
        "qa_blockers": 0,
        "qa_warnings": 0,
        "qa_infos": 0,
        "qa_blockers_historical": 0,
        "qa_warnings_historical": 0,
        "warnings_per_attempt": None,
        "blockers_per_attempt": None,
        "false_positive_recoveries": 0,
        "false_positive_recovery_rate": None,
        "consistency_blockers": 0,
        "consistency_warnings": 0,
        "generation_pass_rate": None,
        "deliverable_pass_rate": None,
        "final_pass_rate": None,
        "release_rows": 0,
        "release_plays": 0,
        "release_revenue_totals": {},
        "release_spend_totals": {},
        "release_net_totals": {},
        "recoup_ratio": {},
        "stages": {},
        "recent_blockers": [],
        "missing_deliverables": [],
        "image_qc_passive": {},
        "consistency_ledger": {},
        "retention_3s": None,
        "retention_15s": None,
        "completion_rate": None,
        "follow_next_rate": None,
    }


def stage_bucket(ep_summary: Dict[str, Any], stage: str) -> Dict[str, Any]:
    stages = ep_summary["stages"]
    if stage not in stages:
        stages[stage] = {
            "duration_sec": 0.0,
            "generation_attempts": 0,
            "generation_passes": 0,
            "generation_fails": 0,
            "redraw_count": 0,
            "qa_blockers": 0,
            "qa_warnings": 0,
            "qa_infos": 0,
            "missing_deliverables": 0,
        }
    return stages[stage]


def add_qa_signal(summary: Dict[str, Any], stage: str, severity: str, dim: str, loc: str, msg: str) -> None:
    """Fold synthetic/current-evidence QA into an episode summary."""
    sb = stage_bucket(summary, stage)
    severity = str(severity or "").lower()
    if severity == "block":
        summary["qa_blockers"] += 1
        sb["qa_blockers"] += 1
        if len(summary["recent_blockers"]) < 8:
            summary["recent_blockers"].append({"stage": stage, "dim": dim, "loc": loc, "msg": msg})
    elif severity == "warn":
        summary["qa_warnings"] += 1
        sb["qa_warnings"] += 1
    elif severity == "info":
        summary["qa_infos"] += 1
        sb["qa_infos"] += 1


def supersedable_qa_key(event: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    """Return the current-verdict key for manual per-asset QA events.

    A rejected generation remains useful historical evidence, but once the same
    asset has a later accepted visual verdict it must no longer count as an
    *active* blocker. The dimension is deliberately not part of the key: each
    manual QA event carries the generation-level accepted/rejected status, while
    ``qa.dim`` records why that attempt passed or failed. Gate snapshots are
    intentionally excluded:
    dashboard ``gate`` already replaces those events as a stage-level snapshot.
    """
    if str(event.get("event") or "") != "qa":
        return None
    qa = event.get("qa") if isinstance(event.get("qa"), dict) else {}
    generation = event.get("generation") if isinstance(event.get("generation"), dict) else {}
    asset = str(generation.get("asset") or qa.get("loc") or "").strip()
    if not asset:
        return None
    return (
        normalize_episode(str(event.get("episode") or "未知集")),
        str(event.get("stage") or "unknown"),
        os.path.normpath(asset),
    )


def latest_supersedable_qa_indexes(events: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str], int]:
    latest: Dict[Tuple[str, str, str], int] = {}
    for index, event in enumerate(events):
        key = supersedable_qa_key(event)
        if key is not None:
            latest[key] = index
    return latest


def add_counter_value(target: Dict[str, float], key: str, amount: float) -> None:
    target[key] = round(float(target.get(key, 0.0)) + amount, 6)


def is_false_positive_waiver(event: Dict[str, Any]) -> bool:
    """Whether a waiver records a gate false-positive recovery.

    This keeps "gate was too noisy" measurable without changing historical QA
    event schemas.  Operators can record it with:
    `dashboard.py waiver ... --waiver false_positive --reason 误报`.
    """
    if str(event.get("event") or "") != "waiver":
        return False
    meta = event.get("meta") if isinstance(event.get("meta"), dict) else {}
    blob = " ".join(str(meta.get(k) or "") for k in ("waiver", "reason", "scope")).lower()
    markers = ("false_positive", "false-positive", "false positive", "误报", "假阳性")
    return any(marker in blob for marker in markers)


def cost_keys(cost: Dict[str, Any]) -> Tuple[str, str]:
    unit = str(cost.get("unit") or cost.get("currency") or "amount")
    provider = str(cost.get("provider") or "unknown")
    # quality_tier（fast/pro/high）随成本事件带上时折进 provider 维，让 cost_by_provider 自动拆出
    # 同后端的 fast vs pro 花销（成本×质量轴的回看）；无 tier 时维持旧键格式，老事件零影响。
    tier = str(cost.get("quality_tier") or "").strip()
    # urgency_tier（realtime/batch_24h·G8）正交折进 provider 维，回看「隔夜批量档省了多少」；
    # 仅 batch_24h 时加后缀（realtime 是默认·不污染旧键），老事件零影响。
    urgency = str(cost.get("urgency_tier") or "").strip()
    base = f"{provider}@{tier}" if tier else provider
    if urgency and urgency != "realtime":
        base = f"{base}#{urgency}"
    provider_key = f"{base}:{unit}"
    return unit, provider_key


def add_release_amounts(summary: Dict[str, Any], *, unit: str, revenue: float = 0.0, spend: float = 0.0) -> None:
    if revenue > 0:
        add_counter_value(summary["release_revenue_totals"], unit, revenue)
    if spend > 0:
        add_counter_value(summary["release_spend_totals"], unit, spend)
    if revenue or spend:
        add_counter_value(summary["release_net_totals"], unit, revenue - spend)


def set_runtime(summary: Dict[str, Any], value: Optional[float], source: str) -> None:
    if value is None or value <= 0:
        return
    current = as_float(summary.get("runtime_sec"))
    if current is None or current <= 0:
        summary["runtime_sec"] = round(float(value), 3)
        summary["runtime_source"] = source


def release_amount(row: Dict[str, Any]) -> float:
    primary = first_float(row, REVENUE_PRIMARY_FIELDS)
    if primary is not None:
        return primary
    return sum(first_float(row, (key,)) or 0.0 for key in REVENUE_COMPONENT_FIELDS)


def spend_amount(row: Dict[str, Any]) -> float:
    return sum(first_float(row, (key,)) or 0.0 for key in SPEND_FIELDS)


def apply_release_row(summary: Dict[str, Any], row: Dict[str, Any], source: str) -> None:
    summary["release_rows"] += 1
    plays = first_float(row, PLAYS_FIELDS)
    if plays and plays > 0:
        summary["release_plays"] += int(round(plays))
    unit = str(first_present(row, CURRENCY_FIELDS) or "CNY")
    add_release_amounts(summary, unit=unit, revenue=release_amount(row), spend=spend_amount(row))
    set_runtime(summary, first_float(row, RUNTIME_FIELDS), source)
    # 留存信号：取最新行覆盖（同集多次投放取最新）
    for key in ("retention_3s", "retention_15s", "completion_rate", "follow_next_rate", "bounce_3s"):
        val = first_float(row, (key, f"{key}_rate", f"{key}%", key.replace("_", "")))
        if val is not None:
            summary[key] = val


def resolvable_asset_path(root: str, raw: Any) -> Optional[str]:
    """Return an absolute path for project-local assets that are meaningful to verify.

    Old/manual events sometimes only recorded ``Clip_01.png``.  Those are not
    enough to resolve unambiguously, so they are left out of current-file checks.
    """
    asset = str(raw or "").strip()
    if not asset or re_like_url(asset):
        return None
    if os.path.isabs(asset):
        return asset
    norm = asset.replace("\\", "/")
    if "/" not in norm:
        return None
    if norm.startswith(("../", "./")):
        return None
    root_abs = os.path.abspath(root)
    norm_abs = os.path.abspath(norm)
    if norm_abs == root_abs or norm_abs.startswith(root_abs + os.sep):
        return norm_abs
    return os.path.join(root, norm)


def re_like_url(value: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9+.-]*://", value, re.I))


def current_missing_pass_assets(root: str, events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Latest pass events whose declared deliverable file no longer exists."""
    latest: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for index, event in enumerate(events):
        generation = event.get("generation") if isinstance(event.get("generation"), dict) else {}
        asset = generation.get("asset") or event.get("asset")
        resolved = resolvable_asset_path(root, asset)
        if not resolved:
            continue
        ep = normalize_episode(str(event.get("episode") or "未知集"))
        stage = str(event.get("stage") or "unknown")
        key = (ep, stage, os.path.normpath(resolved))
        latest[key] = {"event": event, "path": resolved, "index": index}
    missing: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for (ep, stage, _path_key), row in latest.items():
        event = row["event"]
        generation = event.get("generation") if isinstance(event.get("generation"), dict) else {}
        status = str(generation.get("status") or event.get("status") or "").lower()
        if status not in {"pass", "passed", "ok", "accept", "accepted"}:
            continue
        path = str(row["path"])
        if os.path.isfile(path):
            continue
        missing[ep].append({
            "stage": stage,
            "asset": generation.get("asset") or event.get("asset"),
            "path": path,
            "ts": event.get("ts"),
            "provider": generation.get("provider") or event.get("source") or "",
        })
    return dict(missing)


def apply_missing_deliverable_signals(root: str, events: List[Dict[str, Any]], episodes: Dict[str, Dict[str, Any]]) -> None:
    for ep, rows in current_missing_pass_assets(root, events).items():
        if ep not in episodes:
            episodes[ep] = blank_episode(ep)
        summary = episodes[ep]
        for row in rows:
            stage = str(row.get("stage") or "unknown")
            rel = str(row.get("asset") or row.get("path") or "")
            summary["missing_deliverables"].append(row)
            sb = stage_bucket(summary, stage)
            sb["missing_deliverables"] = int(sb.get("missing_deliverables") or 0) + 1
            add_qa_signal(
                summary,
                stage,
                "block",
                "产物存在性",
                rel,
                f"最新 `{stage}` pass 事件登记的产物不存在：{rel}。"
                "事件账本不能替代当前文件存在性；重出或恢复该产物后再放行。",
            )


def divide_dict(values: Dict[str, float], denominator: Optional[float]) -> Dict[str, float]:
    if denominator is None or denominator <= 0:
        return {}
    return {key: round(float(amount) / denominator, 6) for key, amount in values.items()}


def ratio_dict(numerators: Dict[str, float], denominators: Dict[str, float]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for key, numerator in numerators.items():
        denom = float(denominators.get(key) or 0.0)
        if denom > 0:
            result[key] = round(float(numerator) / denom, 6)
    return result


def flow_speed_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Measure gate throughput without weakening the gate profile."""
    parsed: List[Tuple[dt.datetime, Dict[str, Any]]] = []
    for event in events:
        raw = str(event.get("ts") or "").strip()
        if not raw:
            continue
        try:
            when = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        parsed.append((when.astimezone(dt.timezone.utc), event))
    if not parsed:
        return {"time_to_first_episode_sec": None, "time_to_first_episode_hours": None, "time_to_first_episode_hms": "—",
                "gates_passed": 0, "gates_passed_per_day": None}
    parsed.sort(key=lambda row: row[0])
    start = parsed[0][0]
    passed: List[dt.datetime] = []
    first_episode_done: Optional[dt.datetime] = None
    for when, event in parsed:
        if str(event.get("event") or "") != "qa_gate_run":
            continue
        gate = event.get("qa_gate") if isinstance(event.get("qa_gate"), dict) else {}
        if int(gate.get("blocks") or 0) != 0:
            continue
        passed.append(when)
        if (normalize_episode(str(event.get("episode") or "")) == "第1集"
                and str(event.get("stage") or "") in {"compose", "review"}
                and first_episode_done is None):
            first_episode_done = when
    span_days = max(1.0, (parsed[-1][0] - start).total_seconds() / 86400.0)
    seconds = (first_episode_done - start).total_seconds() if first_episode_done else None
    return {
        "time_to_first_episode_sec": round(seconds, 3) if seconds is not None else None,
        "time_to_first_episode_hours": round(seconds / 3600.0, 3) if seconds is not None else None,
        "time_to_first_episode_hms": hms(seconds) if seconds is not None else "—",
        "gates_passed": len(passed),
        "gates_passed_per_day": round(len(passed) / span_days, 3),
        "measurement_start": start.isoformat(),
        "first_episode_gate": first_episode_done.isoformat() if first_episode_done else "",
    }


def aggregate_events(root: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    progress = progress_index(root)
    episodes: Dict[str, Dict[str, Any]] = {
        ep: blank_episode(ep, info) for ep, info in progress.items()
    }
    release_metrics_path = default_input(root, PLATFORM_METRICS_STEM)
    latest_qa_indexes = latest_supersedable_qa_indexes(events)

    for event_index, event in enumerate(events):
        ep = normalize_episode(str(event.get("episode") or "未知集"))
        stage = str(event.get("stage") or "unknown")
        if ep not in episodes:
            episodes[ep] = blank_episode(ep)
        summary = episodes[ep]
        sb = stage_bucket(summary, stage)
        summary["event_count"] += 1

        duration = as_float(event.get("duration_sec"))
        if duration and duration > 0:
            summary["duration_sec"] += duration
            sb["duration_sec"] += duration

        cost = event.get("cost")
        if isinstance(cost, dict):
            amount = as_float(cost.get("amount"))
            if amount and amount > 0:
                unit_key, provider_key = cost_keys(cost)
                add_counter_value(summary["cost_totals"], unit_key, amount)
                add_counter_value(summary["cost_by_provider"], provider_key, amount)

        generation = event.get("generation") if isinstance(event.get("generation"), dict) else {}
        event_name = str(event.get("event") or "")
        has_generation = bool(generation) or event_name in {"generation", "redraw"}
        if has_generation:
            attempt_count = int(as_float(generation.get("attempts") if generation else None) or 1)
            attempt_count = max(1, attempt_count)
            summary["generation_attempts"] += attempt_count
            sb["generation_attempts"] += attempt_count
            status = str(generation.get("status") or event.get("status") or "").lower()
            if status in {"pass", "passed", "ok", "accept", "accepted"}:
                summary["generation_passes"] += 1
                sb["generation_passes"] += 1
                explicit_attempt = int(as_float(generation.get("attempt")) or 1)
                if event_name == "generation" and attempt_count == 1 and explicit_attempt <= 1:
                    summary["one_pass_count"] += 1
            elif status in {"fail", "failed", "reject", "rejected"}:
                summary["generation_fails"] += 1
                sb["generation_fails"] += 1

            reason = generation.get("redraw_reason") or event.get("redraw_reason")
            if event_name == "redraw" or reason:
                summary["redraw_count"] += 1
                sb["redraw_count"] += 1
                reason_text = str(reason or "未注明")
                reasons = Counter(summary["redraw_reasons"])
                reasons[reason_text] += 1
                summary["redraw_reasons"] = dict(reasons)
                # 维度归类：显式 redraw_category 合法则尊重，否则按自由文本关键词归类
                # （存量事件读时归类即可，不改写历史 jsonl）
                explicit = str(generation.get("redraw_category") or event.get("redraw_category") or "").strip()
                category = explicit if explicit in REDRAW_REASON_CATEGORIES else classify_redraw_reason(reason_text)
                categories = Counter(summary["redraw_categories"])
                categories[category] += 1
                summary["redraw_categories"] = dict(categories)

        if event_name == "qa_gate_run":
            qa_gate = event.get("qa_gate") if isinstance(event.get("qa_gate"), dict) else {}
            summary["qa_gate_runs"] += 1
            if int(qa_gate.get("blocks") or 0) == 0:
                summary["qa_gate_passes"] += 1

        if is_false_positive_waiver(event):
            summary["false_positive_recoveries"] += 1

        qa = event.get("qa") if isinstance(event.get("qa"), dict) else {}
        if qa:
            severity = str(qa.get("severity") or qa.get("sev") or "").lower()
            if severity == "block":
                summary["qa_blockers_historical"] += 1
            elif severity == "warn":
                summary["qa_warnings_historical"] += 1
            qa_key = supersedable_qa_key(event)
            if qa_key is None or latest_qa_indexes.get(qa_key) == event_index:
                add_qa_signal(
                    summary,
                    stage,
                    severity,
                    str(qa.get("dim") or ""),
                    str(qa.get("loc") or ""),
                    str(qa.get("msg") or ""),
                )

        # 一致性审查事件：consistency_audit 写 meta.{total_block,total_warn} 但此前无人读 → 统计失真。
        # 接入：单列 consistency_blockers/warnings，并把 block 计入 qa_blockers，让阈值告警看得到审查检出。
        if event_name == "consistency_findings":
            meta = event.get("meta") if isinstance(event.get("meta"), dict) else {}
            c_block = int(as_float(meta.get("total_block")) or 0)
            c_warn = int(as_float(meta.get("total_warn")) or 0)
            summary["consistency_blockers"] += c_block
            summary["consistency_warnings"] += c_warn
            sb["consistency_blockers"] = sb.get("consistency_blockers", 0) + c_block
            sb["consistency_warnings"] = sb.get("consistency_warnings", 0) + c_warn
            if c_block:
                summary["qa_blockers"] += c_block
                sb["qa_blockers"] += c_block

        release = event.get("release") if isinstance(event.get("release"), dict) else {}
        if release or event_name in {"release", "revenue"}:
            apply_release_row(summary, release, "production_events.jsonl")

    if release_metrics_path:
        try:
            release_rows = read_records(release_metrics_path)
        except Exception as exc:
            # 文件存在但读取失败（编码坏/截断/非法 JSON）——别静默当无数据：
            # 否则操作者看到 release_metrics_file 有值，却不知投放行已全部丢弃，成本回收/通过率指标静默不全。
            print(f"[dashboard][warn] 投放数据文件存在但读取失败（{release_metrics_path}）：{exc}；"
                  f"本次跳过全部投放行，回收比/通过率等指标可能不完整——修复该文件后重建。", file=sys.stderr)
            release_rows = []
        for row in release_rows:
            ep = normalize_episode(str(row.get("episode") or ""))
            if not ep:
                continue
            if ep not in episodes:
                episodes[ep] = blank_episode(ep)
            apply_release_row(episodes[ep], row, release_metrics_path)

    apply_missing_deliverable_signals(root, events, episodes)
    apply_passive_image_qc_signals(root, events, episodes)
    apply_passive_consistency_ledger_signals(root, episodes)

    for summary in episodes.values():
        if not summary.get("runtime_sec"):
            runtime, source = storyboard_duration(root, summary["episode"])
            set_runtime(summary, runtime, source)
        summary["duration_sec"] = round(float(summary["duration_sec"]), 3)
        summary["duration_hms"] = hms(summary["duration_sec"])
        if summary.get("runtime_sec"):
            summary["runtime_sec"] = round(float(summary["runtime_sec"]), 3)
            summary["runtime_hms"] = hms(float(summary["runtime_sec"]))
            runtime_min = float(summary["runtime_sec"]) / 60.0
            summary["cost_per_finished_min"] = divide_dict(summary["cost_totals"], runtime_min)
            summary["elapsed_per_finished_min_sec"] = round(summary["duration_sec"] / runtime_min, 3) if runtime_min > 0 else None
        denom = summary["generation_passes"] + summary["generation_fails"]
        generation_rate = round(summary["generation_passes"] / denom, 4) if denom else None
        summary["generation_pass_rate"] = generation_rate
        if summary["qa_blockers"]:
            summary["deliverable_pass_rate"] = 0.0
        else:
            summary["deliverable_pass_rate"] = generation_rate
        # Backward-compatible threshold key. Semantics are now deliverability,
        # not raw generation attempt pass rate.
        summary["final_pass_rate"] = summary["deliverable_pass_rate"]
        if summary["generation_attempts"]:
            summary["one_pass_rate"] = round(summary["one_pass_count"] / summary["generation_attempts"], 4)
            summary["redraw_rate"] = round(summary["redraw_count"] / summary["generation_attempts"], 4)
            summary["warnings_per_attempt"] = round(summary["qa_warnings"] / summary["generation_attempts"], 4)
            summary["blockers_per_attempt"] = round(summary["qa_blockers"] / summary["generation_attempts"], 4)
        qa_noise = int(summary["qa_blockers"] or 0) + int(summary["qa_warnings"] or 0)
        if qa_noise:
            summary["false_positive_recovery_rate"] = round(summary["false_positive_recoveries"] / qa_noise, 4)
        summary["recoup_ratio"] = ratio_dict(summary["release_net_totals"], summary["cost_totals"])
        for sb in summary["stages"].values():
            sb["duration_sec"] = round(float(sb["duration_sec"]), 3)

    ordered = sorted(
        episodes.values(),
        key=lambda item: (
            progress.get(item["episode"], {}).get("num", 10**9),
            item["episode"],
        ),
    )

    totals = {
        "episode_count": len(ordered),
        "event_count": sum(item["event_count"] for item in ordered),
        "duration_sec": round(sum(float(item["duration_sec"]) for item in ordered), 3),
        "runtime_sec": round(sum(float(item.get("runtime_sec") or 0.0) for item in ordered), 3),
        "generation_attempts": sum(item["generation_attempts"] for item in ordered),
        "generation_passes": sum(item["generation_passes"] for item in ordered),
        "generation_fails": sum(item["generation_fails"] for item in ordered),
        "one_pass_count": sum(item["one_pass_count"] for item in ordered),
        "redraw_count": sum(item["redraw_count"] for item in ordered),
        "redraw_categories": dict(sum((Counter(item.get("redraw_categories") or {}) for item in ordered), Counter())),
        "qa_blockers": sum(item["qa_blockers"] for item in ordered),
        "qa_warnings": sum(item["qa_warnings"] for item in ordered),
        "qa_infos": sum(item["qa_infos"] for item in ordered),
        "qa_blockers_historical": sum(item["qa_blockers_historical"] for item in ordered),
        "qa_warnings_historical": sum(item["qa_warnings_historical"] for item in ordered),
        "warnings_per_attempt": None,
        "blockers_per_attempt": None,
        "false_positive_recoveries": sum(item["false_positive_recoveries"] for item in ordered),
        "false_positive_recovery_rate": None,
        "consistency_blockers": sum(item.get("consistency_blockers") or 0 for item in ordered),
        "consistency_warnings": sum(item.get("consistency_warnings") or 0 for item in ordered),
        "cost_totals": {},
        "cost_per_finished_min": {},
        "elapsed_per_finished_min_sec": None,
        "one_pass_rate": None,
        "redraw_rate": None,
        "release_rows": sum(item["release_rows"] for item in ordered),
        "release_plays": sum(item["release_plays"] for item in ordered),
        "release_revenue_totals": {},
        "release_spend_totals": {},
        "release_net_totals": {},
        "recoup_ratio": {},
    }
    totals["duration_hms"] = hms(float(totals["duration_sec"]))
    totals["runtime_hms"] = hms(float(totals["runtime_sec"])) if totals["runtime_sec"] else "—"
    denom = totals["generation_passes"] + totals["generation_fails"]
    generation_rate = round(totals["generation_passes"] / denom, 4) if denom else None
    totals["generation_pass_rate"] = generation_rate
    totals["deliverable_pass_rate"] = 0.0 if totals["qa_blockers"] else generation_rate
    totals["final_pass_rate"] = totals["deliverable_pass_rate"]
    if totals["generation_attempts"]:
        totals["one_pass_rate"] = round(totals["one_pass_count"] / totals["generation_attempts"], 4)
        totals["redraw_rate"] = round(totals["redraw_count"] / totals["generation_attempts"], 4)
        totals["warnings_per_attempt"] = round(totals["qa_warnings"] / totals["generation_attempts"], 4)
        totals["blockers_per_attempt"] = round(totals["qa_blockers"] / totals["generation_attempts"], 4)
    total_noise = int(totals["qa_blockers"] or 0) + int(totals["qa_warnings"] or 0)
    if total_noise:
        totals["false_positive_recovery_rate"] = round(totals["false_positive_recoveries"] / total_noise, 4)
    cost_total: Dict[str, float] = {}
    revenue_total: Dict[str, float] = {}
    spend_total: Dict[str, float] = {}
    net_total: Dict[str, float] = {}
    for item in ordered:
        for key, amount in item["cost_totals"].items():
            add_counter_value(cost_total, key, float(amount))
        for key, amount in item["release_revenue_totals"].items():
            add_counter_value(revenue_total, key, float(amount))
        for key, amount in item["release_spend_totals"].items():
            add_counter_value(spend_total, key, float(amount))
        for key, amount in item["release_net_totals"].items():
            add_counter_value(net_total, key, float(amount))
    totals["cost_totals"] = cost_total
    runtime_min = float(totals["runtime_sec"]) / 60.0 if totals["runtime_sec"] else None
    totals["cost_per_finished_min"] = divide_dict(cost_total, runtime_min)
    totals["elapsed_per_finished_min_sec"] = round(totals["duration_sec"] / runtime_min, 3) if runtime_min else None
    totals["release_revenue_totals"] = revenue_total
    totals["release_spend_totals"] = spend_total
    totals["release_net_totals"] = net_total
    totals["recoup_ratio"] = ratio_dict(net_total, cost_total)
    totals["consistency_ledger_counts"] = {
        key: sum(int((item.get("consistency_ledger") or {}).get("counts", {}).get(key) or 0) for item in ordered)
        for key in ("block", "high", "medium")
    }
    totals["flow_speed"] = flow_speed_metrics(events)

    retention_trend = {}
    eps_with_ret3 = [
        (ep.get("episode", ""), ep.get("retention_3s"))
        for ep in ordered
        if ep.get("retention_3s") is not None
    ]
    if len(eps_with_ret3) >= 2:
        values = [v for _, v in eps_with_ret3]
        names = [n for n, _ in eps_with_ret3]
        n = len(values)
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den else 0.0
        delta = values[-1] - values[0]
        retention_trend = {
            "episodes_tracked": n,
            "first_episode": names[0],
            "last_episode": names[-1],
            "first_retention_3s": round(values[0], 4),
            "last_retention_3s": round(values[-1], 4),
            "slope_per_episode": round(slope, 6),
            "total_delta": round(delta, 4),
            "trend_direction": "declining" if slope < -0.01 else ("improving" if slope > 0.01 else "stable"),
        }

    return {
        "kind": DASHBOARD_KIND,
        "version": 1,
        "root": root,
        "generated_at": now_iso(),
        "event_file": events_path(root),
        "release_metrics_file": release_metrics_path or "",
        "industry_benchmark": load_benchmark(root),
        "totals": totals,
        "episodes": ordered,
        "retention_trend": retention_trend,
    }


def format_cost(costs: Dict[str, float]) -> str:
    if not costs:
        return "—"
    return " / ".join(f"{key} {value:.2f}" for key, value in sorted(costs.items()))


def format_rate(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def format_per_min(values: Dict[str, float]) -> str:
    if not values:
        return "—"
    return " / ".join(f"{key} {value:.2f}/min" for key, value in sorted(values.items()))


def format_ratio(values: Dict[str, float]) -> str:
    if not values:
        return "—"
    return " / ".join(f"{key} {value:.2f}x" for key, value in sorted(values.items()))


def _benchmark_rows(dashboard: Dict[str, Any]) -> List[str]:
    """行业基准对照（只读·非闸门）：把 ROI 实测值并排到行业宣传基准，给一条达标/差距参照线。"""
    bench = dashboard.get("industry_benchmark") or {}
    if not bench:
        return []
    totals = dashboard["totals"]
    rows: List[str] = [
        "",
        f"## 行业基准对照（只读 · 非闸门 · 采集 {bench.get('collected', '—')}）",
        "",
        "> 厂商宣传口径、会过期，只作并排参照线，不参与告警/阻断。可在 `_设置.md`（`基准一次通过率`/`基准重抽率`）或 `生产数据/industry_benchmark.json` 覆盖；以一次 `n2d-review` 流程自审复核为准。",
        "",
        "| 指标 | 本作实测 | 行业基准 | 对照 |",
        "|---|---:|---:|:---:|",
    ]
    schema_errors = bench.get("_retention_benchmark_schema_errors") or []
    if schema_errors:
        rows.extend([
            "> ⚠️ 项目级 `生产数据/industry_benchmark.json` 的 `retention_benchmarks` 未通过 provenance schema，"
            "本次留存基准已回退到仓库参考值。先跑 `python3 skills/n2d/n2d-dashboard/scripts/validate_benchmark_schema.py <path>` 修正。",
            f"> 首个错误：{schema_errors[0]}",
            "",
        ])

    def mark(actual: Optional[float], target: Optional[float], higher_better: bool) -> str:
        if actual is None or target is None:
            return "—"
        ok = actual >= target if higher_better else actual <= target
        return "✅ 达标" if ok else "⚠️ 差距"

    one_pass = totals.get("one_pass_rate")
    redraw = totals.get("redraw_rate")
    rows.append(
        f"| 一次通过率 | {format_rate(one_pass)} | {format_rate(bench.get('one_pass_rate'))} | "
        f"{mark(one_pass, bench.get('one_pass_rate'), True)} |"
    )
    rows.append(
        f"| 重抽率 | {format_rate(redraw)} | {format_rate(bench.get('redraw_rate'))} | "
        f"{mark(redraw, bench.get('redraw_rate'), False)} |"
    )
    cpm = totals.get("cost_per_finished_min", {})
    bench_cpm = bench.get("cost_per_min", {})
    for cur, target in sorted(bench_cpm.items()):
        if not isinstance(target, (int, float)):
            continue  # 防御：基准里若混入非数值（如说明字段），不参与每分钟成本格式化
        actual = cpm.get(cur)
        actual_txt = f"{cur} {actual:.2f}/min" if actual is not None else "—"
        rows.append(
            f"| 每分钟成本（{cur}） | {actual_txt} | {cur} {target:.2f}/min | "
            f"{mark(actual, target, False)} |"
        )
    rows.append(
        f"| 跨集角色一致性 | 见 n2d-score 视觉分 | {format_rate(bench.get('cross_ep_consistency'))} | "
        "— |"
    )
    retention = (bench.get("retention_benchmarks") or {}) if isinstance(bench.get("retention_benchmarks"), dict) else {}
    app_ref = retention.get("app_retention_reference") or {}
    global_ref = app_ref.get("global_short_drama_apps") or {}
    china_ref = app_ref.get("china_short_drama_apps") or {}
    if global_ref or china_ref:
        rows.extend([
            "",
            "### 留存基准（只读）",
            "",
            "| 指标 | 全球短剧App参考 | 中国短剧App参考 | 说明 |",
            "|---|---:|---:|---|",
            (
                f"| D1 留存 | {format_rate(global_ref.get('d1_retention'))} | "
                f"{format_rate(china_ref.get('d1_retention'))} | App/剧集包级，不替代单集 retention_3s/15s |"
            ),
            (
                f"| D7 留存 | {format_rate(global_ref.get('d7_retention'))} | "
                f"{format_rate(china_ref.get('d7_retention'))} | 用于判断剧集包/账号复访能力 |"
            ),
            (
                f"| D14 留存 | {format_rate(global_ref.get('d14_retention'))} | "
                f"{format_rate(china_ref.get('d14_retention'))} | 长线追更和订阅复访参考 |"
            ),
        ])
    creative = retention.get("creative_attention") or {}
    if creative:
        rows.extend([
            "",
            f"> 首屏创意参考：前3秒交代内容主张={creative.get('first_3s_proposition_required', True)}；"
            f"前6秒强钩={creative.get('first_6s_hook_required', True)}；"
            f"字幕/烧屏文字 {creative.get('caption_words_per_sec_band', ['—', '—'])[0]}-"
            f"{creative.get('caption_words_per_sec_band', ['—', '—'])[1]} words/sec。",
        ])
    return rows


def render_markdown(dashboard: Dict[str, Any]) -> str:
    totals = dashboard["totals"]
    lines = [
        "# n2d 生产数据仪表盘",
        "",
        f"- 生成时间：{dashboard['generated_at']}",
        f"- 事件日志：`{dashboard['event_file']}`",
        f"- 投放数据：`{dashboard.get('release_metrics_file') or '未发现 platform_metrics.*'}`",
        "",
        "## 总览",
        "",
        "| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 生成通过率 | 可交付通过率 |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {totals['episode_count']} | {totals['event_count']} | {format_cost(totals['cost_totals'])} | "
            f"{totals['duration_hms']} | {totals['generation_attempts']} | {totals['redraw_count']} | "
            f"{totals['qa_blockers']} | {totals['qa_warnings']} | {format_rate(totals.get('generation_pass_rate'))} | "
            f"{format_rate(totals['final_pass_rate'])} |"
        ),
        "",
        "## ROI",
        "",
        "| 成片分钟 | 每分钟成本 | 每集耗时 | 一次通过率 | 重抽率 | 投放播放 | 投放收入 | 投放成本 | 净回收 | 回收/生产成本 |",
        "|---:|---|---:|---:|---:|---:|---|---|---|---:|",
        (
            f"| {totals.get('runtime_hms', '—')} | {format_per_min(totals.get('cost_per_finished_min', {}))} | "
            f"{totals['duration_hms']} | {format_rate(totals.get('one_pass_rate'))} | "
            f"{format_rate(totals.get('redraw_rate'))} | {totals.get('release_plays', 0)} | "
            f"{format_cost(totals.get('release_revenue_totals', {}))} | {format_cost(totals.get('release_spend_totals', {}))} | "
            f"{format_cost(totals.get('release_net_totals', {}))} | {format_ratio(totals.get('recoup_ratio', {}))} |"
        ),
        "",
        "## Gate 噪声",
        "",
        "| warn/生成 | block/生成 | 误报回收 | 误报回收率 |",
        "|---:|---:|---:|---:|",
        (
            f"| {totals.get('warnings_per_attempt') if totals.get('warnings_per_attempt') is not None else '—'} | "
            f"{totals.get('blockers_per_attempt') if totals.get('blockers_per_attempt') is not None else '—'} | "
            f"{totals.get('false_positive_recoveries', 0)} | {format_rate(totals.get('false_positive_recovery_rate'))} |"
        ),
        *_benchmark_rows(dashboard),
        "",
        "## 逐集",
        "",
        "| 集 | 当前前沿 | 成本 | 每分钟成本 | 耗时 | 一次通过率 | 重抽率 | 重抽原因Top3 | QA阻断 | 净回收 | 回收/成本 | 3s留存 | 15s留存 | 完播率 | 追更率 |",
        "|---|---|---|---|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for item in dashboard["episodes"]:
        reasons = Counter(item["redraw_reasons"]).most_common(3)
        reason_text = "；".join(f"{k}×{v}" for k, v in reasons) if reasons else "—"
        ret3 = format_rate(item.get("retention_3s"))
        ret15 = format_rate(item.get("retention_15s"))
        comp = format_rate(item.get("completion_rate"))
        follow = format_rate(item.get("follow_next_rate"))
        lines.append(
            f"| {item['episode']} | {item.get('progress_next_stage') or '—'} | "
            f"{format_cost(item['cost_totals'])} | {format_per_min(item.get('cost_per_finished_min', {}))} | "
            f"{item['duration_hms']} | {format_rate(item.get('one_pass_rate'))} | "
            f"{format_rate(item.get('redraw_rate'))} | {reason_text} | "
            f"{item['qa_blockers']} | {format_cost(item.get('release_net_totals', {}))} | {format_ratio(item.get('recoup_ratio', {}))} | "
            f"{ret3} | {ret15} | {comp} | {follow} |"
        )

    # 重抽原因分维度统计：一致性相关类小计单列，"一致性是不是最大成本杀手"一眼可见
    categories = dict((dashboard.get("totals") or {}).get("redraw_categories") or {})
    if categories:
        total_redraws = sum(categories.values()) or 1
        consistency_keys = ("face_consistency", "outfit_consistency", "scene_drift", "style_drift")
        consistency_subtotal = sum(categories.get(k, 0) for k in consistency_keys)
        lines += [
            "",
            "## 重抽原因分维度",
            "",
            "| 维度 | 次数 | 占比 |",
            "|---|---:|---:|",
        ]
        for key, count in sorted(categories.items(), key=lambda kv: -kv[1]):
            label = REDRAW_REASON_CATEGORIES.get(key, key)
            lines.append(f"| {label} ({key}) | {count} | {count / total_redraws:.0%} |")
        lines.append(
            f"| **一致性小计**（脸漂/服装/场景/画风） | **{consistency_subtotal}** | **{consistency_subtotal / total_redraws:.0%}** |"
        )

    blockers = [
        (item["episode"], blocker)
        for item in dashboard["episodes"]
        for blocker in item.get("recent_blockers", [])
    ]
    if blockers:
        lines.extend(["", "## 最新阻断", ""])
        for ep, blocker in blockers[:20]:
            lines.append(
                f"- {ep} / {blocker.get('stage', '')} / {blocker.get('dim', '')}: "
                f"{blocker.get('loc', '')} — {blocker.get('msg', '')}"
            )

    ledger_rows = [
        item for item in dashboard["episodes"]
        if (item.get("consistency_ledger") or {}).get("row_count")
    ]
    if ledger_rows:
        lines.extend([
            "",
            "## 验收总账",
            "",
            "| 集 | 状态 | 实体数 | block | high | medium | 重点实体 |",
            "|---|---|---:|---:|---:|---:|---|",
        ])
        for item in ledger_rows:
            ledger = item.get("consistency_ledger") or {}
            counts = ledger.get("counts") or {}
            severe = ledger.get("severe_rows") or []
            focus = "；".join(
                f"{row.get('name') or row.get('id')}({row.get('overall')})"
                for row in severe[:3]
            ) or "—"
            surface = ledger.get("delivery_surface") or {}
            lines.append(
                f"| {item['episode']} | {surface.get('status') or '—'} | {ledger.get('row_count', 0)} | "
                f"{counts.get('block', 0)} | {counts.get('high', 0)} | {counts.get('medium', 0)} | {focus} |"
            )

    lines.append("")
    return "\n".join(lines)


def write_dashboard(root: str, dashboard: Dict[str, Any]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    json_path = os.path.join(production_dir(root), DASHBOARD_JSON)
    md_path = os.path.join(production_dir(root), DASHBOARD_MD)
    atomic_write_text(json_path, json.dumps(dashboard, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    atomic_write_text(md_path, render_markdown(dashboard))


def consistency_ledger_path(root: str, episode: str) -> str:
    return os.path.join(production_dir(root), f"consistency_ledger_{normalize_episode(episode)}.json")


def apply_passive_consistency_ledger_signals(root: str, episodes: Dict[str, Dict[str, Any]]) -> None:
    pattern = os.path.join(production_dir(root), "consistency_ledger_*.json")
    for path in sorted(glob.glob(pattern)):
        name = os.path.basename(path)
        if not name.startswith("consistency_ledger_") or not name.endswith(".json"):
            continue
        ep = normalize_episode(name[len("consistency_ledger_"):-len(".json")])
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if ep not in episodes:
            episodes[ep] = blank_episode(ep)
        counts = data.get("counts") if isinstance(data.get("counts"), dict) else {}
        surface = data.get("delivery_surface") if isinstance(data.get("delivery_surface"), dict) else {}
        rows = [row for row in (data.get("rows") or []) if isinstance(row, dict)]
        severe = [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "kind": row.get("kind"),
                "overall": row.get("overall"),
                "prevent": row.get("prevent"),
                "detect": row.get("detect"),
                "contract": row.get("contract"),
            }
            for row in rows
            if str(row.get("overall") or "") in {"block", "high", "warn", "medium"}
        ]
        episodes[ep]["consistency_ledger"] = {
            "path": os.path.relpath(path, root),
            "counts": {k: int(counts.get(k) or 0) for k in ("block", "high", "medium")},
            "delivery_surface": surface,
            "severe_rows": severe[:8],
            "row_count": len(rows),
        }


# ── 阈值告警引擎（纯本地·纯标准库·跨 AI 通用）────────────────────────────
# 检测/计算全本地：对已构建的 dashboard 汇总做阈值判定。送达分三层：
#   ① 默认：写 alerts.json/md + stderr + 退出码（全平台通用，零依赖）；
#   ② 可选本机：osascript(macOS) / notify-send(Linux) 弹窗（best-effort）；
#   ③ 可选外发：N2D_ALERT_WEBHOOK 环境变量 → stdlib POST JSON（飞书/Slack/Discord 通吃）。
# 循环触发不依赖任何 harness：record/gate 每次写事件即重建并评估（推送路径）；
# 需要常亮看板时用内置 `watch` 子命令轮询（hook/cron/loop 只是可选外壳）。

def _alert(level: str, kind: str, scope: str, message: str, **extra: Any) -> Dict[str, Any]:
    out = {"level": level, "kind": kind, "scope": scope, "message": message}
    out.update(extra)
    return out


def evaluate_alerts(dashboard: Dict[str, Any], thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    totals = dashboard.get("totals", {}) or {}

    # QA 阻断（默认开箱即告）
    cap = thresholds.get("qa_blockers_ceiling")
    blockers = int(totals.get("qa_blockers") or 0)
    if cap is not None and blockers > cap:
        alerts.append(_alert("critical", "qa_blockers", "totals",
                             f"QA 阻断 {blockers} 项（阈值 >{cap:g}）；先按 recent_blockers 修复再继续付费生成",
                             value=blockers, threshold=cap))

    # 未验证回写债：progress.py 在缺/陈旧/无指纹凭据时被 N2D_PROGRESS_ALLOW_UNVERIFIED 强标 ✅。
    # 这类绿灯是「声明非现实」，必须在仪表盘醒目计债（且对当前产物重跑闸门后自动销账，不误报）。
    debts = _unresolved_unverified_waivers(dashboard.get("root") or "")
    if debts:
        eps = sorted({str(w.get("episode")) for w in debts if w.get("episode")})
        ep_disp = "、".join(eps[:6]) + ("…" if len(eps) > 6 else "")
        alerts.append(_alert("critical", "unverified_progress", "totals",
                             f"{len(debts)} 处未验证强标 ✅（{ep_disp}）：受闸列没有「真跑过+指纹新鲜」的闸门凭据，"
                             f"本季视为 provisional；对当前产物重跑对应 dashboard gate 销账。",
                             value=len(debts)))

    # 通过率下限
    floor = thresholds.get("final_pass_rate_floor")
    rate = totals.get("final_pass_rate")
    if floor is not None and rate is not None and rate < floor:
        alerts.append(_alert("critical", "final_pass_rate", "totals",
                             f"总通过率 {rate*100:.1f}% 低于下限 {floor*100:.1f}%",
                             value=rate, threshold=floor))

    # 重抽率上限
    ceil = thresholds.get("redraw_rate_ceiling")
    rr = totals.get("redraw_rate")
    if ceil is not None and rr is not None and rr > ceil:
        alerts.append(_alert("warn", "redraw_rate", "totals",
                             f"重抽率 {rr*100:.1f}% 高于上限 {ceil*100:.1f}%，查重抽原因聚类",
                             value=rr, threshold=ceil))

    # 成本上限（按币种）
    cap_amt = thresholds.get("budget_cap")
    warn_ratio = thresholds.get("budget_warn_ratio") or 0.8
    if cap_amt:
        for cur, amount in (totals.get("cost_totals") or {}).items():
            amount = float(amount)
            if amount >= cap_amt:
                alerts.append(_alert("critical", "budget", "totals",
                                     f"累计成本 {cur} {amount:.2f} 达/超上限 {cap_amt:.2f}，停止付费生成或调预算",
                                     value=amount, threshold=cap_amt, currency=cur))
            elif amount >= cap_amt * warn_ratio:
                alerts.append(_alert("warn", "budget", "totals",
                                     f"累计成本 {cur} {amount:.2f} 已达上限 {cap_amt:.2f} 的 {warn_ratio*100:.0f}%",
                                     value=amount, threshold=cap_amt * warn_ratio, currency=cur))

    # 每分钟成本上限（按币种）
    cpm_ceil = thresholds.get("cost_per_min_ceiling")
    if cpm_ceil:
        for cur, amount in (totals.get("cost_per_finished_min") or {}).items():
            if float(amount) > cpm_ceil:
                alerts.append(_alert("warn", "cost_per_min", "totals",
                                     f"每分钟成本 {cur} {float(amount):.2f}/min 高于上限 {cpm_ceil:.2f}",
                                     value=float(amount), threshold=cpm_ceil, currency=cur))

    # 回收比下限（仅有投放数据时）
    rf = thresholds.get("recoup_floor")
    if rf is not None:
        for cur, ratio in (totals.get("recoup_ratio") or {}).items():
            if float(ratio) < rf:
                alerts.append(_alert("warn", "recoup", "totals",
                                     f"回收比 {cur} {float(ratio):.2f}x 低于下限 {rf:.2f}x（投放 ROI 预警）",
                                     value=float(ratio), threshold=rf, currency=cur))

    # 逐集定位：通过率下限 / QA 阻断 / 留存信号
    project_genre = ""
    try:
        _settings_path = os.path.join(root, "_设置.md")
        if os.path.isfile(_settings_path):
            with open(_settings_path, encoding="utf-8") as _sf:
                for _line in _sf:
                    if _line.strip().startswith("- 题材:") or _line.strip().startswith("- 题材："):
                        project_genre = _line.split(":", 1)[-1].strip().split("：", 1)[-1].strip()
                        break
    except Exception:
        pass
    genre_adjustments = {}
    try:
        _bench_path = os.path.join(os.path.dirname(__file__), "..", "references", "industry_benchmark.json")
        with open(_bench_path, encoding="utf-8") as _bf:
            _bench = json.load(_bf)
        genre_adjustments = _bench.get("genre_retention_adjustments", {})
    except Exception:
        pass
    for ep in dashboard.get("episodes", []) or []:
        name = ep.get("episode", "?")
        if floor is not None and ep.get("final_pass_rate") is not None and ep["final_pass_rate"] < floor:
            alerts.append(_alert("warn", "final_pass_rate", name,
                                 f"{name} 通过率 {ep['final_pass_rate']*100:.1f}% 低于下限 {floor*100:.1f}%",
                                 value=ep["final_pass_rate"], threshold=floor, episode=name))
        if cap is not None and int(ep.get("qa_blockers") or 0) > cap:
            alerts.append(_alert("warn", "qa_blockers", name,
                                 f"{name} QA 阻断 {ep['qa_blockers']} 项",
                                 value=int(ep["qa_blockers"]), threshold=cap, episode=name))
        # 留存信号：3s 留存低于地板 → critical（首帧钩失效，用户秒退）
        ret3_floor = thresholds.get("retention_3s_floor")
        if ret3_floor is not None and project_genre and genre_adjustments:
            _genre_key = project_genre if project_genre in genre_adjustments else "default"
            _multiplier = genre_adjustments.get(_genre_key, {}).get("retention_3s_multiplier", 1.0)
            ret3_floor = ret3_floor * _multiplier
        ret3 = ep.get("retention_3s")
        if ret3_floor is not None and ret3 is not None and ret3 < ret3_floor:
            alerts.append(_alert("critical", "retention_3s", name,
                                 f"{name} 3s 留存 {ret3*100:.1f}% 低于地板 {ret3_floor*100:.1f}%（首帧钩失效）",
                                 value=ret3, threshold=ret3_floor, episode=name))
        # 跳出率上限：3s 跳出过高 = 开场留不住人
        bounce_cap = thresholds.get("bounce_3s_ceiling")
        bounce = ep.get("bounce_3s")
        if bounce_cap is not None and bounce is not None and bounce > bounce_cap:
            alerts.append(_alert("warn", "bounce_3s", name,
                                 f"{name} 3s 跳出率 {bounce*100:.1f}% 超过上限 {bounce_cap*100:.1f}%",
                                 value=bounce, threshold=bounce_cap, episode=name))
        # 追更率地板：低于地板 = 集尾钩失效，观众不追下一集
        follow_floor = thresholds.get("follow_next_rate_floor")
        follow = ep.get("follow_next_rate")
        if follow_floor is not None and follow is not None and follow < follow_floor:
            alerts.append(_alert("warn", "follow_next_rate", name,
                                 f"{name} 追更率 {follow*100:.1f}% 低于地板 {follow_floor*100:.1f}%（集尾钩失效）",
                                 value=follow, threshold=follow_floor, episode=name))
        bdv_ceiling = thresholds.get("beat_density_variance_ceiling")
        if bdv_ceiling is not None:
            pacing_path = os.path.join(production_dir(root), f"pacing_retention_{normalize_episode(name)}.json")
            if os.path.isfile(pacing_path):
                try:
                    with open(pacing_path, encoding="utf-8") as pf:
                        pacing_data = json.load(pf)
                    bdv = pacing_data.get("beat_density_variance")
                    if bdv is not None and bdv > bdv_ceiling:
                        alerts.append(_alert("warn", "beat_density_variance", name,
                                             f"{name} 节拍密度方差 {bdv:.3f} 超过上限 {bdv_ceiling:.3f}（节奏紊乱·留存杀手）",
                                             value=bdv, threshold=bdv_ceiling, episode=name))
                except Exception:
                    pass
        if project_genre and genre_adjustments and ret3 is not None:
            _gk = project_genre if project_genre in genre_adjustments else "default"
            _gn = genre_adjustments.get(_gk, {}).get("note", "")
            if _gn:
                try:
                    _hf = 0.8
                    _bp = os.path.join(os.path.dirname(__file__), "..", "references", "industry_benchmark.json")
                    with open(_bp, encoding="utf-8") as _bf2:
                        _bd2 = json.load(_bf2)
                    _hf = _bd2.get("retention_benchmarks", {}).get("proxy_thresholds", {}).get("retention_hook_floor", 0.8)
                except Exception:
                    _hf = 0.8
                _genre_bench = _hf * genre_adjustments.get(_gk, {}).get("retention_3s_multiplier", 1.0)
                if ret3 < _genre_bench * 0.8:
                    alerts.append(_alert("info", "retention_3s_genre_benchmark", name,
                                         f"{name} 3s 留存 {ret3*100:.1f}% 显著低于 {project_genre}题材基准 {_genre_bench*100:.1f}%——{_gn}",
                                         value=ret3, threshold=_genre_bench, episode=name))
    return alerts


def render_alerts_markdown(root: str, alerts: List[Dict[str, Any]], thresholds: Dict[str, Any]) -> str:
    lines = ["# n2d 生产告警", "", f"- root: {root}", f"- generated_at: {now_iso()}",
             f"- 告警数: {len(alerts)}（critical {_count_level(alerts,'critical')} / warn {_count_level(alerts,'warn')}）", ""]
    if not alerts:
        lines.append("✅ 无告警：所有已配置阈值均未触发。")
        return "\n".join(lines) + "\n"
    lines += ["| 级别 | 类型 | 范围 | 说明 |", "|---|---|---|---|"]
    order = {"critical": 0, "warn": 1, "info": 2}
    for a in sorted(alerts, key=lambda x: order.get(x.get("level"), 9)):
        icon = "🔴" if a["level"] == "critical" else "🟡"
        lines.append(f"| {icon} {a['level']} | {a['kind']} | {a['scope']} | {a['message'].replace('|','/')} |")
    lines += ["", "## 当前阈值", "```json", json.dumps(thresholds, ensure_ascii=False, indent=2), "```"]
    return "\n".join(lines) + "\n"


def _count_level(alerts: List[Dict[str, Any]], level: str) -> int:
    return sum(1 for a in alerts if a.get("level") == level)


def write_alerts(root: str, alerts: List[Dict[str, Any]], thresholds: Dict[str, Any]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    payload = {
        "kind": PRODUCTION_ALERTS_KIND,
        "version": 1,
        "root": root,
        "generated_at": now_iso(),
        "thresholds": thresholds,
        "counts": {"critical": _count_level(alerts, "critical"), "warn": _count_level(alerts, "warn")},
        "alerts": alerts,
    }
    atomic_write_text(
        os.path.join(production_dir(root), ALERTS_JSON),
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(os.path.join(production_dir(root), ALERTS_MD), render_alerts_markdown(root, alerts, thresholds))


def print_alerts(alerts: List[Dict[str, Any]]) -> None:
    for a in alerts:
        icon = "🔴" if a.get("level") == "critical" else "🟡"
        print(f"[alert]{icon} {a.get('level')} {a.get('kind')} ({a.get('scope')}): {a.get('message')}", file=sys.stderr)


def notify_desktop(alerts: List[Dict[str, Any]]) -> None:
    """本机弹窗，best-effort：macOS osascript / Linux notify-send。失败静默。"""
    criticals = [a for a in alerts if a.get("level") == "critical"]
    targets = criticals or alerts
    if not targets:
        return
    title = f"n2d 告警：{_count_level(alerts,'critical')} critical / {_count_level(alerts,'warn')} warn"
    body = "；".join(a.get("message", "") for a in targets[:3])
    try:
        if shutil.which("osascript"):
            text = body.replace('"', "'")
            subprocess.run(["osascript", "-e", f'display notification "{text}" with title "{title}"'],
                           check=False, capture_output=True, timeout=10)
        elif shutil.which("notify-send"):
            subprocess.run(["notify-send", title, body], check=False, capture_output=True, timeout=10)
    except Exception:
        pass


def post_webhook(alerts: List[Dict[str, Any]], url: str) -> None:
    """外发 webhook，best-effort：stdlib POST JSON（飞书/Slack/Discord 等通吃）。失败静默。"""
    if not url or not alerts:
        return
    import urllib.request
    text = f"n2d 告警 {_count_level(alerts,'critical')} critical / {_count_level(alerts,'warn')} warn\n" + \
           "\n".join(f"- {a.get('level')} {a.get('kind')}: {a.get('message')}" for a in alerts[:10])
    # 兼容飞书自定义机器人(text)、Slack/Discord(text/content)；下游各取所需字段。
    payload = {"msg_type": "text", "content": {"text": text}, "text": text}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        pass


def render_html(dashboard: Dict[str, Any], alerts: List[Dict[str, Any]], *, refresh: int = 0) -> str:
    totals = dashboard.get("totals", {}) or {}
    meta_refresh = f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""
    rows = []
    for ep in dashboard.get("episodes", []) or []:
        rows.append(
            f"<tr><td>{ep.get('episode','')}</td><td>{format_cost(ep.get('cost_totals',{}))}</td>"
            f"<td>{format_rate(ep.get('generation_pass_rate'))}</td><td>{format_rate(ep.get('final_pass_rate'))}</td>"
            f"<td>{format_rate(ep.get('redraw_rate'))}</td>"
            f"<td>{ep.get('qa_blockers',0)}</td><td>{ep.get('qa_warnings',0)}</td>"
            f"<td>{format_rate(ep.get('retention_3s'))}</td>"
            f"<td>{format_rate(ep.get('retention_15s'))}</td>"
            f"<td>{format_rate(ep.get('completion_rate'))}</td>"
            f"<td>{format_rate(ep.get('follow_next_rate'))}</td></tr>"
        )
    alert_rows = "".join(
        f'<li class="{a.get("level")}">{"🔴" if a.get("level")=="critical" else "🟡"} '
        f'<b>{a.get("kind")}</b> ({a.get("scope")}): {a.get("message")}</li>'
        for a in alerts
    ) or "<li>✅ 无告警</li>"
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">{meta_refresh}
<title>n2d 仪表盘</title><style>
body{{font-family:system-ui,sans-serif;margin:24px;background:#0f1115;color:#e6e6e6}}
h1,h2{{font-weight:600}} table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #333;padding:6px 10px;text-align:left}} th{{background:#1a1d24}}
.critical{{color:#ff6b6b}} .warn{{color:#ffd166}} ul{{line-height:1.8}}
.bar{{background:#1a1d24;padding:10px 14px;border-radius:8px;margin-bottom:16px}}
</style></head><body>
<h1>n2d 生产数据仪表盘</h1>
<div class="bar">root: {dashboard.get('root','')} ｜ 生成: {dashboard.get('generated_at','')} ｜
成本 {format_cost(totals.get('cost_totals',{}))} ｜ 生成通过率 {format_rate(totals.get('generation_pass_rate'))} ｜
可交付通过率 {format_rate(totals.get('final_pass_rate'))} ｜
重抽率 {format_rate(totals.get('redraw_rate'))} ｜ QA阻断 {totals.get('qa_blockers',0)} / warn {totals.get('qa_warnings',0)}</div>
<h2>告警（{_count_level(alerts,'critical')} critical / {_count_level(alerts,'warn')} warn）</h2>
<ul>{alert_rows}</ul>
<h2>逐集</h2>
<table><tr><th>集</th><th>成本</th><th>生成通过率</th><th>可交付通过率</th><th>重抽率</th><th>QA阻断</th><th>QA警告</th><th>3s留存</th><th>15s留存</th><th>完播率</th><th>追更率</th></tr>
{''.join(rows) or '<tr><td colspan=7>暂无数据</td></tr>'}</table>
<p style="color:#888">{"自动刷新 "+str(refresh)+"s" if refresh else "静态快照"} ｜ 纯本地生成，无外部依赖</p>
</body></html>"""


def build(root: str, *, write: bool = True, alerts: bool = True, notify: bool = False,
          webhook: Optional[str] = None, html: bool = False, refresh: int = 0) -> Dict[str, Any]:
    with event_lock(root):
        dashboard = aggregate_events(root, _load_events_unlocked(root))
        alert_list: List[Dict[str, Any]] = []
        thresholds = DEFAULT_THRESHOLDS
        if alerts:
            thresholds = load_thresholds(root)
            alert_list = evaluate_alerts(dashboard, thresholds)
            dashboard["alerts"] = alert_list
            dashboard["alert_counts"] = {"critical": _count_level(alert_list, "critical"),
                                         "warn": _count_level(alert_list, "warn")}
        if write:
            write_dashboard(root, dashboard)
            if alerts:
                write_alerts(root, alert_list, thresholds)
            if html:
                atomic_write_text(
                    os.path.join(production_dir(root), DASHBOARD_HTML),
                    render_html(dashboard, alert_list, refresh=refresh),
                )
    if alerts and alert_list:
        if notify:
            notify_desktop(alert_list)
        if webhook:
            post_webhook(alert_list, webhook)
    return dashboard


def event_from_record_args(ns: argparse.Namespace) -> Dict[str, Any]:
    provider = str(ns.provider or "").strip()
    cost = None
    if ns.cost is not None:
        cost = {
            "amount": ns.cost,
            "currency": ns.currency,
            "unit": ns.unit or ns.currency,
            "provider": provider,
        }
    generation = None
    if ns.asset or ns.attempt or ns.status or ns.redraw_reason or ns.attempts:
        generation = {
            "asset": ns.asset,
            "attempt": ns.attempt,
            "attempts": ns.attempts,
            "status": ns.status,
            "redraw_reason": ns.redraw_reason,
            "provider": provider if provider and provider != "unknown" else None,
        }
        if ns.redraw_reason or getattr(ns, "redraw_category", None):
            explicit = str(getattr(ns, "redraw_category", "") or "").strip()
            generation["redraw_category"] = (
                explicit if explicit in REDRAW_REASON_CATEGORIES else classify_redraw_reason(ns.redraw_reason)
            )
    qa = None
    if ns.qa_sev or ns.qa_dim or ns.qa_loc or ns.qa_msg:
        qa = {
            "severity": ns.qa_sev,
            "dim": ns.qa_dim,
            "loc": ns.qa_loc,
            "msg": ns.qa_msg,
        }
    release = None
    if ns.plays is not None or ns.revenue is not None or ns.spend is not None or ns.runtime_sec is not None:
        release = {
            "plays": ns.plays,
            "revenue": ns.revenue,
            "spend": ns.spend,
            "currency": ns.revenue_currency,
            "runtime_sec": ns.runtime_sec,
        }
    return make_event(
        ns.episode,
        ns.stage,
        ns.event,
        source="manual",
        cost=cost,
        duration_sec=ns.duration_sec,
        generation=generation,
        qa=qa,
        release=release,
        meta=parse_meta(ns.meta or []),
    )


def _unique(items: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


# 各 gate stage 的「新鲜度锚定产物」globs（相对作品根）。收据 inputs_fingerprint 必须覆盖
# **本阶段所认证的产物 + 上游身份真值**，否则「绿闸」的指纹只剩 storyboard.json：闸后换脸/重出
# PNG/改角色卡都判 fresh，等于闸验声明不验现实（正是 gate_receipt 模块要堵的洞）。
# 只锚定内容型真值（PNG/MP4/prompt/角色卡/字幕），不含机器每轮重写的账本。glob 在盖章时快照展开；
# 记录列表内文件被改/删即失配（fingerprint_is_fresh 按记录键重算）——闸后重出/换素材必被抓。
_GATE_FRESHNESS_GLOBS: Dict[str, Tuple[str, ...]] = {
    "image": (
        "出图/{ep}/图片/**/*.png",
        "出图/共享/图片/**/*.png",
        "出图/{ep}/prompt/**/*.md",
        "出图/共享/prompt/**/*.md",
        "设定库/characters/**/*.md",
        "设定库/characters/**/*.json",
    ),
    "video": (
        "出视频/{ep}/视频/**/*.mp4",
        "出视频/{ep}/prompt/**/*.md",
        "出图/{ep}/图片/**/*.png",
        "设定库/characters/**/*.md",
        "设定库/characters/**/*.json",
    ),
    "compose": (
        "合成/{ep}/成片*.mp4",
        "出视频/{ep}/视频/**/*.mp4",
        "脚本/{ep}/字幕_中文.srt",
        "脚本/{ep}/字幕_英文.srt",
    ),
    "review": (
        "合成/{ep}/成片*.mp4",
    ),
}
# preflight（花钱前）与落档回验共用同一组锚定：preflight 时产物多半尚不存在，glob 展开为空、
# 指纹自然只含 storyboard（preflight 收据本就不授权进度 ✅，见 gate_receipt.ENFORCED_COLUMN_GATE_STAGE）。
_GATE_FRESHNESS_GLOBS["image_preflight"] = _GATE_FRESHNESS_GLOBS["image"]
_GATE_FRESHNESS_GLOBS["video_preflight"] = _GATE_FRESHNESS_GLOBS["video"]
# prompt-preflight（写 prompt 前的闸）同族：产物多半尚未生成，glob 展开为空无害；
# 但 video_prompt_preflight 要核验已就绪的首帧 PNG、image_prompt_preflight 要核验角色卡/上游，
# 漏登记会让这两个 stage 的收据退回 storyboard-only。GATE_STAGES 全集必须都有锚定（下方测试守 set 相等）。
_GATE_FRESHNESS_GLOBS["image_prompt_preflight"] = _GATE_FRESHNESS_GLOBS["image"]
_GATE_FRESHNESS_GLOBS["video_prompt_preflight"] = _GATE_FRESHNESS_GLOBS["video"]


def _gate_freshness_extra_files(root: str, episode: str, stage: str) -> List[str]:
    """本阶段新鲜度锚定产物的**具体**相对路径（glob 在盖章时快照展开，只取现存文件）。

    与 findings 无关：即使 0 findings（绿闸），也覆盖本阶段认证的 PNG/MP4/prompt + 角色卡，
    使闸后任何对这些文件的修改/删除都让收据 stale，逼重跑闸门再回写进度完成态。"""
    ep = normalize_episode(episode)
    out: set = set()
    for pattern in _GATE_FRESHNESS_GLOBS.get(str(stage), ()):  # 未登记 stage → 空（回退旧行为，只锚 storyboard）
        abs_pattern = os.path.join(root, pattern.format(ep=ep))
        for match in glob.glob(abs_pattern, recursive=True):
            if not os.path.isfile(match):
                continue
            rel = os.path.relpath(match, root).replace(os.sep, "/")
            # 跳过 `_` 前缀缓存目录（_downloads/_work/_clipcache/_voicecache/_proxy…）：
            # 架构约定其为可重建缓存、非业务真值，锚进去会因缓存 churn 造成假 stale。
            # 只看路径段是否以 `_` 起头，不误伤 定妆_主角.png 这类名内下划线。
            if any(seg.startswith("_") for seg in rel.split("/")):
                continue
            out.add(rel)
    return sorted(out)


def gate_findings_payload(root: str, episode: str, stage: str, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert gate.py findings into batch-compatible n2d_consistency_findings."""
    rows: List[Dict[str, Any]] = []
    severity_counts: Dict[str, int] = {"block": 0, "warn": 0, "info": 0}
    by_dim: Dict[str, Dict[str, int]] = {}
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for item in findings:
        if not isinstance(item, dict):
            continue
        norm = normalize_finding(item)
        sev = norm["severity"] or "info"
        if sev not in severity_counts:
            sev = "info"
        dim_key = finding_dim_key(item)
        dim = norm["dimension"] or str(item.get("dim") or item.get("dimension") or dim_key or "QA")
        row = {
            "severity": sev,
            "sev": sev,
            "dimension": dim,
            "dim": dim,
            "dim_key": dim_key if dim_key != "一致性" else norm.get("dim_key", ""),
            "message": norm["message"],
            "msg": norm["message"],
            "loc": norm["loc"],
            "episode": episode,
            "gate_stage": stage,
            "return_to_stage": norm["return_to_stage"],
            "rerun_scope": norm["rerun_scope"],
            "affected_shots": norm["affected_shots"],
            "affected_artifacts": norm["affected_artifacts"],
            "source": "n2d-dashboard/gate",
        }
        rows.append(row)
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        dim_counts = by_dim.setdefault(dim, {"block": 0, "warn": 0, "info": 0})
        dim_counts[sev] = dim_counts.get(sev, 0) + 1

        if sev not in {"block", "warn"}:
            continue
        return_stage = row["return_to_stage"] or stage
        group_key = (str(return_stage), str(row["dim_key"] or dim))
        group = grouped.setdefault(group_key, {
            "return_to_stage": return_stage,
            "dimensions": [row["dim_key"] or dim],
            "scope": [],
            "affected_shots": [],
            "affected_artifacts": [],
            "findings": [],
        })
        group["scope"].append(row["rerun_scope"] or row["message"])
        group["affected_shots"].extend(row["affected_shots"])
        group["affected_artifacts"].extend(row["affected_artifacts"])
        group["findings"].append(row)

    auto_tasks: List[Dict[str, Any]] = []
    for group in grouped.values():
        shots = _unique(group["affected_shots"])
        artifacts = _unique(group["affected_artifacts"])
        scope_parts = _unique(group["scope"])
        if shots:
            scope_parts.append("定位镜头：" + "、".join(shots))
        if artifacts:
            scope_parts.append("定位产物：" + "、".join(artifacts[:8]))
        auto_tasks.append({
            "return_to_stage": group["return_to_stage"],
            "dimensions": group["dimensions"],
            "scope": "；".join(scope_parts),
            "affected_shots": shots,
            "affected_artifacts": artifacts,
            "findings": group["findings"][:12],
        })

    # 输入指纹：证「这份缓存判定对应当前产物」。下游（release_manifest）据此判定缓存是否陈旧，
    # 堵「gate 从未跑过/产物已改但仍读旧 gate_findings 当作 0 block」的证声明不证现实。
    fp_files = sorted(
        {
            a
            for row in rows
            for a in (row.get("affected_artifacts") or [])
            if isinstance(a, str) and a.strip()
        }
        | {f"脚本/{normalize_episode(episode)}/storyboard.json"}
        # 阶段级新鲜度锚定：不依赖 findings 是否指向产物。绿闸也覆盖本阶段认证的
        # PNG/MP4/prompt + 角色卡，堵「闸后重出/换脸/改卡仍判 fresh」的证声明不证现实。
        | set(_gate_freshness_extra_files(root, episode, stage))
    )
    inputs_fingerprint = None
    if artifact_fingerprint is not None:
        try:
            inputs_fingerprint = artifact_fingerprint(root, fp_files)
        except Exception:
            inputs_fingerprint = None

    return {
        "kind": CONSISTENCY_FINDINGS_KIND,
        "version": 1,
        "root": root,
        "episode": episode,
        "gate_stage": stage,
        "generated_at": now_iso(),
        "inputs_fingerprint": inputs_fingerprint,
        "summary": {"total": len(rows), "severity": severity_counts, "by_dim": by_dim},
        "findings": rows,
        "auto_return_tasks": auto_tasks,
        "source": {"kind": "n2d_gate", "path": "n2d-review/scripts/gate.py"},
    }


def write_gate_findings(root: str, episode: str, stage: str, findings: List[Dict[str, Any]]) -> str:
    path = gate_findings_path(root, episode, stage)
    atomic_write_text(path, json.dumps(gate_findings_payload(root, episode, stage, findings), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path


def image_qc_failure_finding(root: str, episode: str, reason: str) -> Dict[str, Any]:
    return {
        "sev": "block",
        "dim": "出图落档QC",
        "loc": os.path.join(root, "生产数据", "image_qc", normalize_episode(episode)),
        "msg": f"image gate 无法取得 image_qc findings：{reason}；出图落档回验必须 fail-closed，先修复 image_qc 再放行。",
        "return_to_stage": "image",
        "rerun_scope": "修复 n2d-image/scripts/image_qc.py 或本机依赖后，重跑 dashboard gate --stage image。",
        "affected_artifacts": [f"生产数据/image_qc/{normalize_episode(episode)}"],
    }


def image_qc_report_path(root: str, episode: str) -> str:
    ep = normalize_episode(episode)
    return os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json")


def image_qc_fingerprint_status(root: str, payload: Dict[str, Any]) -> Tuple[str, str]:
    """fresh/stale/unknown for an image_qc report's declared input files."""
    recorded = payload.get("inputs_fingerprint")
    if not isinstance(recorded, dict):
        return "unknown", "报告缺 `inputs_fingerprint`，无法确认它对应当前 prompt/registry/PNG"
    files = recorded.get("files")
    sha = recorded.get("sha")
    if not isinstance(files, dict) or not isinstance(sha, str) or not sha:
        return "unknown", "报告 `inputs_fingerprint` 结构不完整"
    if artifact_fingerprint is None:
        return "unknown", "无法加载 skill_snapshot.artifact_fingerprint，不能校验报告新鲜度"
    current = artifact_fingerprint(root, list(files.keys()))  # type: ignore[misc]
    if current.get("sha") == sha:
        return "fresh", ""
    current_files = current.get("files") if isinstance(current.get("files"), dict) else {}
    changed: List[str] = []
    for rel in sorted(set(files) | set(current_files)):
        before = files.get(rel)
        after = current_files.get(rel)
        if before == after:
            continue
        if before and not after:
            state = "缺失"
        elif after and not before:
            state = "新增"
        else:
            state = "变更"
        changed.append(f"{rel}({state})")
    sample = "、".join(changed[:8]) + ("…" if len(changed) > 8 else "")
    return "stale", f"报告 `inputs_fingerprint` 与当前文件失配：{sample or '输入文件已变化'}"


def image_qc_missing_prop_shape_confirmation_dependency(payload: Dict[str, Any], episode: str) -> bool:
    """Old image_qc reports did not fingerprint manual prop-shape confirmations.

    If a report contains prop-shape review state but its fingerprint does not
    include the confirmation file, a later manual confirmation can make the
    report stale without changing any of its recorded inputs.  Force a rerun
    instead of trusting that old verdict.
    """
    review = payload.get("prop_shape_review")
    if not isinstance(review, dict):
        return False
    targets = review.get("targets")
    total = review.get("total")
    if not targets and not total:
        return False
    recorded = payload.get("inputs_fingerprint")
    files = recorded.get("files") if isinstance(recorded, dict) else None
    if not isinstance(files, dict):
        return False
    ep = normalize_episode(episode)
    confirmation_rel = os.path.join("生产数据", "image_qc", ep, "prop_shape_confirmations.json").replace(os.sep, "/")
    return confirmation_rel not in {str(k).replace(os.sep, "/") for k in files.keys()}


def image_qc_missing_declared_episode_images(payload: Dict[str, Any], episode: str) -> List[str]:
    recorded = payload.get("inputs_fingerprint")
    files = recorded.get("files") if isinstance(recorded, dict) else None
    if not isinstance(files, dict):
        return []
    ep = normalize_episode(episode)
    prefix = f"出图/{ep}/图片/"
    missing: List[str] = []
    for raw_rel, digest in files.items():
        rel = str(raw_rel).replace(os.sep, "/")
        if not rel.startswith(prefix):
            continue
        ext = os.path.splitext(rel)[1].lower()
        if ext in {".png", ".jpg", ".jpeg", ".webp"} and not digest:
            missing.append(rel)
    return sorted(set(missing))


def image_qc_report_paths(root: str) -> List[str]:
    base = os.path.join(root, "生产数据", "image_qc")
    return sorted(glob.glob(os.path.join(base, "*", "image_qc_*.json")))


def load_image_qc_module() -> Optional[Any]:
    script = os.path.join(REPO_SKILLS, "n2d-image", "scripts", "image_qc.py")
    if not os.path.isfile(script):
        return None
    spec = importlib.util.spec_from_file_location("n2d_image_qc_for_dashboard", script)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def image_qc_report_findings(root: str, episode: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    path = image_qc_report_path(root, episode)
    if not os.path.isfile(path):
        return None, None
    try:
        payload = json.load(open(path, encoding="utf-8"))
        status, _reason = image_qc_fingerprint_status(root, payload)
        if status != "fresh":
            return None, None
        missing_images = image_qc_missing_declared_episode_images(payload, episode)
        if missing_images:
            sample = "、".join(missing_images[:8]) + ("…" if len(missing_images) > 8 else "")
            return None, f"image_qc 报告声明的本集出图文件尚未落档：{sample}；先完成出图落档后重跑 image_qc"
        if image_qc_missing_prop_shape_confirmation_dependency(payload, episode):
            return None, None
        env = payload.get("qc_environment") if isinstance(payload.get("qc_environment"), dict) else {}
        if str(env.get("precision_level") or "") != "full":
            return None, None
        mod = load_image_qc_module()
        if mod is None:
            return None, "无法加载 image_qc.py"
        findings = mod.to_findings(payload)  # type: ignore[attr-defined]
        if not isinstance(findings, list):
            return None, "既有 image_qc 报告转换结果不是 findings list"
        return [f for f in findings if isinstance(f, dict)], None
    except Exception as exc:
        return None, f"读取既有 image_qc 报告失败：{type(exc).__name__}: {exc}"


def image_preflight_qc_findings(root: str, episode: str) -> List[Dict[str, Any]]:
    """Return image_qc findings that are meaningful before paid shot generation.

    `image_qc --findings` writes a full report as a side effect.  Running that
    from preflight can turn planned-but-not-generated PNGs into bogus face/prop
    blocks and make the passive dashboard counters fail.  Preflight therefore
    imports the lint-only helpers directly and leaves pixel review to
    `dashboard gate --stage image`.
    """
    mod = load_image_qc_module()
    if mod is None:
        return []
    ep = normalize_episode(episode)
    out: List[Dict[str, Any]] = []
    try:
        lint = mod.lint_prompts(mod.Path(root), ep)  # type: ignore[attr-defined]
        hard_codes = set(getattr(mod, "HARD_LINT_CODES", ()))
        for item in (lint.get("findings") or []):
            if not isinstance(item, dict):
                continue
            hard = item.get("level") == "block" and item.get("code") in hard_codes
            sev = "block" if hard else ("info" if item.get("level") == "info" else "warn")
            out.append({
                "sev": sev,
                "dim": "image_prompt_lint",
                "loc": item.get("loc"),
                "msg": item.get("msg"),
                "return_to_stage": "image",
            })
        prohibited = mod.prohibited_face_patch_outputs(mod.Path(root), ep)  # type: ignore[attr-defined]
        label = getattr(mod, "PROHIBITED_FACE_PATCH_LABEL", "本地贴脸修复产物禁用")
        for item in (prohibited.get("outputs") or []):
            if not isinstance(item, dict):
                continue
            out.append({
                "sev": "block",
                "dim": "character_consistency",
                "loc": item.get("png"),
                "msg": (
                    f"{label}：{item.get('png')} 最新落档事件来自 "
                    f"`{item.get('provider') or 'unknown'}` / `{item.get('method') or 'unknown'}`。"
                    "不能用裁脸/贴脸/换脸产物进入正式图生视频。"
                ),
                "return_to_stage": "image",
            })
    except Exception:
        return []
    return out


def apply_passive_image_qc_signals(root: str, events: List[Dict[str, Any]], episodes: Dict[str, Dict[str, Any]]) -> None:
    """Make standalone image_qc reports visible in dashboard builds.

    Gate events remain authoritative.  This only fills the gap where image_qc
    was run directly and no ``dashboard gate --stage image`` event exists.
    """
    gated_eps: Set[str] = {
        normalize_episode(str(event.get("episode") or ""))
        for event in events
        if event.get("stage") == "image"
        and event.get("event") == "qa_gate_run"
        and event.get("source") == "n2d-review/scripts/gate.py"
    }
    for path in image_qc_report_paths(root):
        name = os.path.basename(path)
        match = re.match(r"image_qc_(.+)\.json$", name)
        if not match:
            continue
        ep = normalize_episode(match.group(1))
        if ep in gated_eps:
            continue
        try:
            payload = json.load(open(path, encoding="utf-8"))
        except Exception as exc:
            payload = {}
            status, reason = "unknown", f"image_qc 报告不可读：{type(exc).__name__}: {exc}"
        else:
            status, reason = image_qc_fingerprint_status(root, payload)
        if ep not in episodes:
            episodes[ep] = blank_episode(ep)
        summary = episodes[ep]
        summary["image_qc_passive"] = {"path": path, "freshness": status}
        if status != "fresh":
            add_qa_signal(
                summary,
                "image",
                "block",
                "出图落档QC",
                path,
                f"发现未入账 image_qc 报告但其新鲜度为 `{status}`：{reason}。"
                "先重跑 `dashboard gate --stage image` 或 image_qc，不能用旧报告证明图片一致。",
            )
            continue
        report_summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        hard = int(as_float(report_summary.get("hard_blocks")) or 0)
        advisory = int(as_float(report_summary.get("advisory")) or 0)
        summary["image_qc_passive"].update({"hard_blocks": hard, "advisory": advisory})
        if hard:
            summary["consistency_blockers"] += hard
            image_bucket = stage_bucket(summary, "image")
            image_bucket["consistency_blockers"] = image_bucket.get("consistency_blockers", 0) + hard
            add_qa_signal(
                summary,
                "image",
                "block",
                "出图落档QC",
                path,
                f"image_qc standalone 报告有 {hard} 个硬阻断但未见 dashboard image gate 入账；"
                "必须修复/重抽并重跑 `dashboard gate --stage image`。",
            )
            if hard > 1:
                summary["qa_blockers"] += hard - 1
                image_bucket["qa_blockers"] += hard - 1
        if advisory:
            summary["consistency_warnings"] += advisory
            image_bucket = stage_bucket(summary, "image")
            image_bucket["consistency_warnings"] = image_bucket.get("consistency_warnings", 0) + advisory
            summary["qa_warnings"] += advisory
            image_bucket["qa_warnings"] += advisory


def run_image_qc_findings(root: str, episode: str, *, fail_closed: bool) -> List[Dict[str, Any]]:
    report_findings, report_error = image_qc_report_findings(root, episode)
    if report_findings is not None:
        return report_findings
    if report_error:
        return [image_qc_failure_finding(root, episode, report_error)] if fail_closed else []
    script = os.path.join(REPO_SKILLS, "n2d-image", "scripts", "image_qc.py")
    if not os.path.isfile(script):
        return [image_qc_failure_finding(root, episode, f"脚本缺失：{script}")] if fail_closed else []
    image_qc_python = os.environ.get("N2D_IMAGE_QC_PYTHON") or sys.executable
    try:
        proc = subprocess.run(
            [image_qc_python, script, root, episode, "--findings"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=600,
        )
    except Exception as exc:
        return [image_qc_failure_finding(root, episode, f"{type(exc).__name__}: {exc}")] if fail_closed else []
    try:
        data = loads_json_from_noisy_stdout(proc.stdout or "[]")
    except Exception as exc:
        detail = str(exc)
        if proc.stderr:
            detail += f"; stderr={proc.stderr[:500]}"
        return [image_qc_failure_finding(root, episode, detail)] if fail_closed else []
    if not isinstance(data, list):
        return [image_qc_failure_finding(root, episode, "输出不是 findings list")] if fail_closed else []
    return [f for f in data if isinstance(f, dict)]


def image_qc_findings(root: str, episode: str) -> List[Dict[str, Any]]:
    """Backward-compatible helper for preflight callers/tests.

    Preflight should be best-effort because an empty/new project can legitimately
    have no generated PNGs yet.  The post-image gate still uses fail-closed mode.
    """
    return run_image_qc_findings(root, episode, fail_closed=False)


def gate_events(root: str, episode: str, stage: str) -> Tuple[List[Dict[str, Any]], int, List[Dict[str, Any]]]:
    gate_py = os.path.join(REPO_SKILLS, "n2d-review", "scripts", "gate.py")
    proc = subprocess.run(
        [sys.executable, gate_py, root, episode, "--stage", stage, "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        findings = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gate.py --json did not return JSON: {exc}\n{proc.stdout}\n{proc.stderr}") from exc
    if not isinstance(findings, list):
        raise RuntimeError("gate.py --json returned a non-list payload")

    # C：出图 gate 合并 image_qc 的生图后像素/lint 机检（崩脸/纯文生图/非法 CHAR_id = block）。
    # image_preflight 只合并可在付费前判断的 lint/精度/禁用产物类项；道具禁形逐图确认等像素复核
    # 留到 image 阶段，避免未烧分镜图时被旧 PNG 或待确认 PNG 卡住。
    return_code = proc.returncode
    if stage in {"image_preflight", "image"}:
        qc = image_preflight_qc_findings(root, episode) if stage == "image_preflight" else run_image_qc_findings(root, episode, fail_closed=True)
        findings.extend(qc)
        if return_code == 0 and any(str(f.get("sev")).lower() == "block" for f in qc):
            return_code = 1   # image_qc 硬阻断也让出图 gate 失败

    counts = Counter(str(item.get("sev") or "").lower() for item in findings if isinstance(item, dict))
    ts = now_iso()
    events = [
        make_event(
            episode,
            stage,
            "qa_gate_run",
            ts=ts,
            source="n2d-review/scripts/gate.py",
            meta={"exit_code": return_code},
        )
    ]
    events[0]["qa_gate"] = {
        "blocks": counts.get("block", 0),
        "warns": counts.get("warn", 0),
        "infos": counts.get("info", 0),
    }
    for item in findings:
        if not isinstance(item, dict):
            continue
        qa = {
            "severity": item.get("sev"),
            "dim": item.get("dim"),
            "loc": item.get("loc"),
            "msg": item.get("msg"),
        }
        meta = {
            "return_to_stage": item.get("return_to_stage"),
            "rerun_scope": item.get("rerun_scope"),
            "affected_artifacts": item.get("affected_artifacts"),
        }
        events.append(
            make_event(
                episode,
                stage,
                "qa_gate",
                ts=ts,
                source="n2d-review/scripts/gate.py",
                qa=qa,
                meta=meta,
            )
        )
    return events, return_code, findings


def _resolve_webhook(ns: argparse.Namespace) -> Optional[str]:
    return getattr(ns, "webhook", None) or os.environ.get("N2D_ALERT_WEBHOOK")


def _build_kwargs(ns: argparse.Namespace, *, write: bool) -> Dict[str, Any]:
    alerts = not getattr(ns, "no_alert", False)
    return {
        "write": write,
        "alerts": alerts,
        "notify": getattr(ns, "notify", False),
        "webhook": _resolve_webhook(ns),
        "html": getattr(ns, "html", False),
    }


def cmd_record(ns: argparse.Namespace) -> int:
    event = event_from_record_args(ns)
    append_events(ns.root, [event])
    if not ns.no_build:
        dashboard = build(ns.root, **_build_kwargs(ns, write=True))
        print_alerts(dashboard.get("alerts", []))
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


def cmd_waiver(ns: argparse.Namespace) -> int:
    """记录一次一致性闸门放行/逃生口（执行时「松动」留痕）。

    任何绕过/降级硬闸门的逃生口——`--skip-preflight` / `--skip-final-gate` /
    `--skip-image-qc` / `N2D_ALLOW_DEGRADED_QC` / 缺 ffprobe·insightface 降级 /
    `lora register --force` / `validate --approved` 等——都该写一条 waiver 事件，
    让「松动」从静默变成 dashboard 上可见、可审计的留痕。"""
    meta = {"waiver": ns.waiver, "reason": ns.reason, "scope": ns.scope}
    event = make_event(ns.episode, ns.stage, "waiver", source=ns.source, meta=meta)
    append_events(ns.root, [event])
    if not ns.no_build:
        dashboard = build(ns.root, **_build_kwargs(ns, write=True))
        print_alerts(dashboard.get("alerts", []))
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


def cmd_gate(ns: argparse.Namespace) -> int:
    ep = normalize_episode(ns.episode)
    events, code, findings = gate_events(ns.root, ep, ns.stage)
    if ns.append:
        append_events(ns.root, events)
    else:
        replace_events(
            ns.root,
            lambda event: (
                event.get("episode") == ep
                and event.get("stage") == ns.stage
                and event.get("source") == "n2d-review/scripts/gate.py"
                and event.get("event") in {"qa_gate", "qa_gate_run"}
            ),
            events,
        )
    findings_path = write_gate_findings(ns.root, ep, ns.stage, findings)
    if not ns.no_build:
        dashboard = build(ns.root, **_build_kwargs(ns, write=True))
        print_alerts(dashboard.get("alerts", []))
    print(json.dumps({"gate_exit_code": code, "recorded_events": len(events), "findings_path": findings_path}, ensure_ascii=False, indent=2))
    return code


def cmd_build(ns: argparse.Namespace) -> int:
    dashboard = build(ns.root, **_build_kwargs(ns, write=not ns.no_write), refresh=ns.refresh)
    if not ns.markdown:
        print_alerts(dashboard.get("alerts", []))
    print(render_markdown(dashboard) if ns.markdown else json.dumps(dashboard, ensure_ascii=False, indent=2))
    # 退出码：有 critical 告警 → 非零，方便 batch/cron/CI 据此停线。
    if getattr(ns, "fail_on_critical", False) and _count_level(dashboard.get("alerts", []), "critical"):
        return 3
    return 0


def _serve_dir(directory: str, port: int):
    import functools
    import http.server
    import socketserver
    import threading
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def cmd_watch(ns: argparse.Namespace) -> int:
    """本地轮询：events.jsonl 变化即重建+评估+告警。纯标准库，跨 AI 通用。
    hook/cron/loop 只是可选外壳；`--once` 适合 cron 单次，常驻则默认循环。"""
    root = ns.root
    epath = events_path(root)
    webhook = _resolve_webhook(ns)
    httpd = None
    if ns.serve is not None:
        os.makedirs(production_dir(root), exist_ok=True)
        httpd = _serve_dir(production_dir(root), ns.serve)
        print(f"[watch] serving {production_dir(root)} → http://127.0.0.1:{ns.serve}/{DASHBOARD_HTML}", file=sys.stderr)
    last_mtime = -1.0
    try:
        while True:
            mtime = os.path.getmtime(epath) if os.path.isfile(epath) else 0.0
            if mtime != last_mtime:
                last_mtime = mtime
                # 单轮 build 失败（如某行 events.jsonl 半写坏触发 ValueError）不能拖垮监控守护进程——
                # 否则告警/预算闸门静默停摆而生产继续。捕获、留痕、继续轮询。
                try:
                    dashboard = build(root, write=True, alerts=not ns.no_alert, notify=ns.notify,
                                      webhook=webhook, html=True, refresh=ns.interval if ns.serve is not None else 0)
                    alist = dashboard.get("alerts", [])
                    stamp = now_iso()
                    print(f"[watch {stamp}] rebuilt · {_count_level(alist,'critical')} critical / {_count_level(alist,'warn')} warn", file=sys.stderr)
                    print_alerts(alist)
                except Exception as exc:
                    print(f"[watch {now_iso()}] rebuild 失败（跳过本轮，监控继续）：{exc}", file=sys.stderr)
            if ns.once:
                break
            time.sleep(ns.interval)
    except KeyboardInterrupt:
        print("\n[watch] stopped", file=sys.stderr)
    finally:
        if httpd is not None:
            httpd.shutdown()
    return 0


# ── 成本预检（pre-flight forecast）——开跑前估这集要花多少、预算够撑几集 ──
# dashboard 此前只**事后**记账（stage 完成才 record）；这里用历史 ¥/finished-min × 本集计划时长
# 给一个开跑前的预测，并把已有的 redraw_categories 滚动出来当"过去钱漏在哪"的上下文。纯函数·可测。

def forecast_episode_cost(cost_per_min: Dict[str, float], planned_min: float) -> Dict[str, float]:
    """逐货币单位：预测成本 = 历史 ¥/finished-min × 本集计划输出分钟。纯函数。"""
    if not isinstance(cost_per_min, dict) or not planned_min or planned_min <= 0:
        return {}
    out: Dict[str, float] = {}
    for unit, per_min in cost_per_min.items():
        amount = as_float(per_min)
        if amount and amount > 0:
            out[unit] = round(amount * planned_min, 2)
    return out


def affordable_episode_count(remaining_budget: float, per_episode_cost: float) -> Optional[int]:
    """剩余预算还能撑几集（向下取整）。单集成本未知/<=0 → None（无法判断，不臆造）。纯函数。"""
    if not per_episode_cost or per_episode_cost <= 0 or remaining_budget is None:
        return None
    return max(0, int(remaining_budget // per_episode_cost))


def top_redraw_leak(redraw_categories: Dict[str, Any], top: int = 3) -> List[Tuple[str, int]]:
    """show 级重抽归因 Top-N（'过去钱漏在哪'）。读已有 totals.redraw_categories，不重算。纯函数。"""
    counts = {str(k): int(as_float(v) or 0) for k, v in (redraw_categories or {}).items()}
    return sorted(((k, c) for k, c in counts.items() if c > 0), key=lambda kv: kv[1], reverse=True)[:top]


def anchor_plan_budget(root: str, ep: str) -> Dict[str, Any]:
    """Read anchor planner sidecar so video forecast does not hide mid-frame costs."""
    rel = os.path.join(PRODUCTION_DIR, f"anchor_plan_{normalize_episode(ep)}.json")
    path = os.path.join(root, rel)
    out: Dict[str, Any] = {
        "available": False,
        "path": rel,
        "clips_planned": 0,
        "total_anchors": 0,
        "added_images": 0,
        "added_video_segments": 0,
    }
    if not os.path.isfile(path):
        out["note"] = "缺 anchor_plan；当前 forecast 只覆盖历史每分钟成本和视频规格，不含 `_mid/_aK` 新增图片或 split relay 拆段成本。"
        return out
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        out["note"] = f"anchor_plan 读取失败：{type(exc).__name__}: {exc}"
        return out
    if not isinstance(data, dict) or data.get("kind") != "n2d_anchor_plan":
        out["note"] = "anchor_plan kind 非 n2d_anchor_plan；忽略，避免误报成本。"
        return out
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    out.update({
        "available": True,
        "clips_planned": int(as_float(summary.get("clips_planned")) or 0),
        "total_anchors": int(as_float(summary.get("total_anchors")) or 0),
        "added_images": int(as_float(summary.get("added_images")) or 0),
        "added_video_segments": int(as_float(summary.get("added_video_segments")) or 0),
    })
    return out


def cmd_forecast(ns: argparse.Namespace) -> int:
    root, ep = ns.root, normalize_episode(ns.episode)
    agg = aggregate_events(root, load_events(root))
    totals = agg.get("totals", {})
    cpm = totals.get("cost_per_finished_min") or {}
    finished_min = round(float(totals.get("runtime_sec") or 0.0) / 60.0, 2)
    planned_sec, src = storyboard_duration(root, ep)
    planned_min = round((planned_sec or 0.0) / 60.0, 2)
    anchor_budget = anchor_plan_budget(root, ep)

    out: Dict[str, Any] = {
        "kind": "n2d_cost_forecast", "episode": ep,
        "history_finished_min": finished_min, "cost_per_finished_min": cpm,
        "planned_min": planned_min, "planned_source": src,
        "forecast_cost": {}, "notes": [],
        "anchor_plan": anchor_budget,
        "redraw_leak_top": [{"category": c, "count": n} for c, n in top_redraw_leak(totals.get("redraw_categories", {}))],
        "show_redraw_rate": totals.get("redraw_rate"),
    }
    if anchor_budget.get("note"):
        out["notes"].append(str(anchor_budget["note"]))
    if not cpm:
        out["notes"].append("无历史成本（cost_per_finished_min 为空）——先用 `record` 记几集真实成本再预检；本次只能给 redraw 漏点。")
    if not planned_min:
        out["notes"].append(f"缺本集计划时长（脚本/{ep}/storyboard.json 无 total_duration/clips）——无法估时长×单价，先跑分镜设计。")
    if cpm and planned_min:
        out["forecast_cost"] = forecast_episode_cost(cpm, planned_min)
        if ns.budget is not None:
            unit = ns.unit
            per_ep = float(out["forecast_cost"].get(unit, 0.0))
            out["budget"] = {"unit": unit, "remaining": ns.budget,
                             "this_episode": per_ep,
                             "over_budget": bool(per_ep and per_ep > ns.budget),
                             "more_episodes_affordable": affordable_episode_count(ns.budget, per_ep)}

    if ns.json:
        print(json.dumps(out, ensure_ascii=False, indent=2)); return 0
    print(f"=== 成本预检：{root} {ep} ===")
    print(f"历史已完成 {finished_min} 分钟 · ¥/min(by unit): {format_cost(cpm) if cpm else '—'}")
    print(f"本集计划 {planned_min} 分钟（{src or '缺 storyboard'}）")
    if out["forecast_cost"]:
        print(f"→ 预测成本：{format_cost(out['forecast_cost'])}")
    if anchor_budget.get("available"):
        print(
            "→ 三帧锚帧计划："
            f"新增锚帧图 {anchor_budget['added_images']} 张；"
            f"命中 Clip {anchor_budget['clips_planned']} 个；"
            f"frames2video/split relay 预计额外视频段 {anchor_budget['added_video_segments']} 段。"
        )
    b = out.get("budget")
    if b:
        warn = "⚠️ 超预算" if b["over_budget"] else "✅ 在预算内"
        more = b["more_episodes_affordable"]
        print(f"→ 预算 {b['remaining']} {b['unit']}：本集 {b['this_episode']} → {warn}"
              + (f"；剩余还能撑约 {more} 集" if more is not None else ""))
    if out["redraw_leak_top"]:
        leaks = "、".join(f"{x['category']}×{x['count']}" for x in out["redraw_leak_top"])
        print(f"过去重抽漏点 Top（先治这些省钱）：{leaks}（重抽率 {out['show_redraw_rate']}）")
    for n in out["notes"]:
        print(f"  · {n}")
    return 0


def _ident_ep_num(name: str) -> int:
    digits = "".join(c for c in str(name) if c.isdigit())
    return int(digits) if digits else 0


def identity_consistency_kpi(report: Dict[str, Any]) -> Dict[str, Any]:
    """从 n2d-identity 的 identity_drift_report 滚出工作级「跨集角色一致性」KPI（纯函数·可测）。

    不写死相似度阈值——显著漂移沿用报表里**自标定 flag-band** 产出的 warn/block；趋势=该角色 mean_score
    按集号首→末是否下降。软门：有 block 级漂移 / ≥2 集 warn / mean_score 趋势下降 → degrade=True
    （advisory，让"第几集开始系统性退化"可被监控，**不阻断生产**）。"""
    chars = report.get("characters") or {}
    rows: List[Dict[str, Any]] = []
    earliest_bad: Optional[Tuple[int, str]] = None
    for name, info in sorted(chars.items()):
        if not isinstance(info, dict):
            continue
        eps = info.get("episodes") or {}
        total_block = int(info.get("total_block") or 0)
        total_warn = int(info.get("total_warn") or 0)
        first_bad = str(info.get("first_bad_episode") or "").strip()
        bad_ep_count = sum(1 for e in eps.values()
                           if isinstance(e, dict) and ((e.get("warn") or 0) or (e.get("block") or 0)))
        scored = sorted((_ident_ep_num(ep), e.get("mean_score")) for ep, e in eps.items()
                        if isinstance(e, dict) and e.get("mean_score") is not None)
        trend = None
        if len(scored) >= 2:
            first_s, last_s = scored[0][1], scored[-1][1]
            trend = {"first": first_s, "last": last_s, "declining": float(last_s) < float(first_s)}
        significant = (total_block > 0 or bad_ep_count >= 2 or first_bad != ""
                       or bool(trend and trend["declining"]))
        if significant and first_bad:
            n = _ident_ep_num(first_bad)
            if n and (earliest_bad is None or n < earliest_bad[0]):
                earliest_bad = (n, first_bad)
        rows.append({"character": name, "first_bad_episode": first_bad,
                     "total_block": total_block, "total_warn": total_warn,
                     "bad_episode_count": bad_ep_count, "trend": trend, "significant": significant})
    drifting = [r for r in rows if r["significant"]]
    return {
        "available": bool(report.get("available", True)) and bool(chars),
        "characters_tracked": len(rows),
        "characters_drifting": len(drifting),
        "earliest_systemic_episode": (earliest_bad[1] if earliest_bad else ""),
        "degrade": bool(drifting),
        "rows": rows,
    }


def cmd_identity(ns: argparse.Namespace) -> int:
    root = ns.root
    path = os.path.join(root, "生产数据", "identity_drift_report.json")
    if not os.path.isfile(path):
        note = ("缺 生产数据/identity_drift_report.json —— 先跑 "
                "`python3 skills/n2d/n2d-identity/scripts/identity.py <作品根> --episodes 1-N --write`。")
        if ns.json:
            print(json.dumps({"kind": "n2d_identity_kpi", "available": False, "note": note},
                             ensure_ascii=False, indent=2))
        else:
            print(f"=== 跨集角色一致性 KPI：{root} ===\n  · {note}")
        return 0
    try:
        report = json.loads(open(path, encoding="utf-8").read())
    except Exception as exc:  # noqa: BLE001
        print(f"⛔ 无法解析 {path}：{exc}")
        return 1
    kpi = identity_consistency_kpi(report)
    kpi["kind"] = "n2d_identity_kpi"
    kpi["root"] = root
    if ns.json:
        print(json.dumps(kpi, ensure_ascii=False, indent=2))
        return 0
    print(f"=== 跨集角色一致性 KPI：{root} ===")
    if not kpi["available"]:
        print("  · 漂移报表无可用角色数据（available=false 或无角色）——先跑 n2d-identity 落档。")
        return 0
    flag = "⚠️ 有系统性退化" if kpi["degrade"] else "✅ 跨集稳定"
    line = f"追踪角色 {kpi['characters_tracked']} · 漂移角色 {kpi['characters_drifting']} → {flag}"
    if kpi["earliest_systemic_episode"]:
        line += f"；系统性退化最早自 {kpi['earliest_systemic_episode']}"
    print(line)
    for r in kpi["rows"]:
        if not r["significant"]:
            continue
        t = r["trend"]
        trend_s = ""
        if t and t.get("first") is not None and t.get("last") is not None:
            arrow = "↓" if t.get("declining") else "→"
            trend_s = f"，相似度 {float(t['first']):.2f}{arrow}{float(t['last']):.2f}"
        bad = f"，首崩 {r['first_bad_episode']}" if r["first_bad_episode"] else ""
        print(f"  · {r['character']}：block×{r['total_block']} warn×{r['total_warn']}{bad}{trend_s}")
    if kpi["degrade"]:
        print("  → 软门建议：核心角色跨集退化——回 n2d-image 升原生主体/主体库或 LoRA"
              "（见 n2d/references/模型矩阵.md 一致性梯子），按 first_bad_episode 起重出受影响镜头。")
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d production data dashboard")
    sub = ap.add_subparsers(dest="cmd", required=True)

    record = sub.add_parser("record", help="append one production event")
    record.add_argument("root")
    record.add_argument("--episode", required=True)
    record.add_argument("--stage", required=True)
    record.add_argument("--event", required=True, choices=["generation", "redraw", "qa", "cost", "duration", "manual", "release", "revenue"])
    record.add_argument("--cost", type=float)
    record.add_argument("--currency", default="CNY")
    record.add_argument("--unit")
    record.add_argument("--provider", default="unknown")
    record.add_argument("--duration-sec", type=float)
    record.add_argument("--asset")
    record.add_argument("--attempt", type=int)
    record.add_argument("--attempts", type=int)
    record.add_argument("--status", choices=["pass", "fail", "accepted", "rejected"])
    record.add_argument("--redraw-reason")
    record.add_argument("--redraw-category", choices=sorted(REDRAW_REASON_CATEGORIES),
                        help="重抽原因维度（契约 REDRAW_REASON_CATEGORIES）；缺省按 --redraw-reason 关键词自动归类")
    record.add_argument("--qa-sev", choices=["block", "warn", "info"])
    record.add_argument("--qa-dim")
    record.add_argument("--qa-loc")
    record.add_argument("--qa-msg")
    record.add_argument("--plays", type=float)
    record.add_argument("--revenue", type=float)
    record.add_argument("--spend", type=float)
    record.add_argument("--revenue-currency", default="CNY")
    record.add_argument("--runtime-sec", type=float)
    record.add_argument("--meta", action="append", default=[])
    record.add_argument("--no-build", action="store_true")
    _add_alert_args(record)
    record.set_defaults(func=cmd_record)

    waiver = sub.add_parser("waiver", help="记录一次一致性闸门放行/逃生口（执行时松动留痕）")
    waiver.add_argument("root")
    waiver.add_argument("--episode", required=True)
    waiver.add_argument("--stage", required=True)
    waiver.add_argument("--waiver", required=True,
                        help="逃生口标识，如 skip-preflight / skip-final-gate / skip-image-qc / allow-degraded-qc / ffprobe-missing / lora-force")
    waiver.add_argument("--reason", default="", help="为何放行（自负其责的依据）")
    waiver.add_argument("--scope", default="", help="影响范围，如 第N集/全集/某Clip")
    waiver.add_argument("--source", default="manual")
    waiver.add_argument("--no-build", action="store_true")
    _add_alert_args(waiver)
    waiver.set_defaults(func=cmd_waiver)

    gate = sub.add_parser("gate", help="run n2d-review gate and record QA findings")
    gate.add_argument("root")
    gate.add_argument("episode")
    gate.add_argument("--stage", required=True, choices=list(GATE_STAGES))  # 与裸 gate.py 同源，避免新增 gate 阶段时 wrapper 拒收
    gate.add_argument("--append", action="store_true", help="append instead of replacing previous gate events for this episode/stage")
    gate.add_argument("--no-build", action="store_true")
    _add_alert_args(gate)
    gate.set_defaults(func=cmd_gate)

    build_cmd = sub.add_parser("build", help="rebuild dashboard outputs (+评估阈值告警)")
    build_cmd.add_argument("root")
    build_cmd.add_argument("--no-write", action="store_true")
    build_cmd.add_argument("--markdown", action="store_true")
    build_cmd.add_argument("--refresh", type=int, default=0, help="HTML 自动刷新秒数（配合 --html）")
    build_cmd.add_argument("--fail-on-critical", action="store_true", help="有 critical 告警时退出码 3（供 batch/cron/CI 停线）")
    _add_alert_args(build_cmd)
    build_cmd.set_defaults(func=cmd_build)

    watch_cmd = sub.add_parser("watch", help="本地轮询监控：events 变化即重建+告警（纯标准库，跨 AI 通用）")
    watch_cmd.add_argument("root")
    watch_cmd.add_argument("--interval", type=int, default=15, help="轮询/HTML刷新间隔秒（默认 15）")
    watch_cmd.add_argument("--serve", type=int, nargs="?", const=8787, default=None, metavar="PORT",
                           help="本机起 http.server 看 dashboard.html（默认端口 8787）")
    watch_cmd.add_argument("--once", action="store_true", help="只跑一遍就退出（适合 cron）")
    _add_alert_args(watch_cmd)
    watch_cmd.set_defaults(func=cmd_watch)

    forecast_cmd = sub.add_parser("forecast", help="开跑前成本预检：历史 ¥/min × 本集计划时长 + 预算够撑几集 + 重抽漏点")
    forecast_cmd.add_argument("root")
    forecast_cmd.add_argument("episode")
    forecast_cmd.add_argument("--budget", type=float, default=None, help="剩余预算（配合 --unit 判超支/还能撑几集）")
    forecast_cmd.add_argument("--unit", default="CNY", help="预算货币单位（默认 CNY，须与 record 的 cost.unit 一致）")
    forecast_cmd.add_argument("--json", action="store_true")
    forecast_cmd.set_defaults(func=cmd_forecast)

    identity_cmd = sub.add_parser("identity", help="跨集角色一致性 KPI：读 identity_drift_report，汇报漂移角色/系统性退化起点/相似度趋势 + 软门告警")
    identity_cmd.add_argument("root")
    identity_cmd.add_argument("--json", action="store_true")
    identity_cmd.set_defaults(func=cmd_identity)

    return ap


def _add_alert_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--no-alert", action="store_true", help="跳过阈值评估与 alerts 写出")
    p.add_argument("--notify", action="store_true", help="critical 告警时本机弹窗（macOS osascript / Linux notify-send，best-effort）")
    p.add_argument("--webhook", help="告警 POST 到此 URL；缺省读环境变量 N2D_ALERT_WEBHOOK")
    p.add_argument("--html", action="store_true", help="额外写 dashboard.html 静态看板")


def main(argv: List[str]) -> int:
    ns = parser().parse_args(argv)
    ns.root = ns.root.rstrip("/")
    return ns.func(ns)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
