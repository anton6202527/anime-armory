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
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

SCRIPT_DIR = os.path.dirname(__file__)
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))
COMMON = os.path.join(REPO_SKILLS, "n2d", "_lib")
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
    return item


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
        "consistency_blockers": 0,
        "consistency_warnings": 0,
        "final_pass_rate": None,
        "release_rows": 0,
        "release_plays": 0,
        "release_revenue_totals": {},
        "release_spend_totals": {},
        "release_net_totals": {},
        "recoup_ratio": {},
        "stages": {},
        "recent_blockers": [],
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
        }
    return stages[stage]


def add_counter_value(target: Dict[str, float], key: str, amount: float) -> None:
    target[key] = round(float(target.get(key, 0.0)) + amount, 6)


def cost_keys(cost: Dict[str, Any]) -> Tuple[str, str]:
    unit = str(cost.get("unit") or cost.get("currency") or "amount")
    provider = str(cost.get("provider") or "unknown")
    return unit, f"{provider}:{unit}"


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


def aggregate_events(root: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    progress = progress_index(root)
    episodes: Dict[str, Dict[str, Any]] = {
        ep: blank_episode(ep, info) for ep, info in progress.items()
    }
    release_metrics_path = default_input(root, PLATFORM_METRICS_STEM)

    for event in events:
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

        qa = event.get("qa") if isinstance(event.get("qa"), dict) else {}
        if qa:
            severity = str(qa.get("severity") or qa.get("sev") or "").lower()
            if severity == "block":
                summary["qa_blockers"] += 1
                sb["qa_blockers"] += 1
                if len(summary["recent_blockers"]) < 8:
                    summary["recent_blockers"].append({
                        "stage": stage,
                        "dim": qa.get("dim", ""),
                        "loc": qa.get("loc", ""),
                        "msg": qa.get("msg", ""),
                    })
            elif severity == "warn":
                summary["qa_warnings"] += 1
                sb["qa_warnings"] += 1
            elif severity == "info":
                summary["qa_infos"] += 1
                sb["qa_infos"] += 1

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
        if denom:
            summary["final_pass_rate"] = round(summary["generation_passes"] / denom, 4)
        if summary["generation_attempts"]:
            summary["one_pass_rate"] = round(summary["one_pass_count"] / summary["generation_attempts"], 4)
            summary["redraw_rate"] = round(summary["redraw_count"] / summary["generation_attempts"], 4)
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
    totals["final_pass_rate"] = round(totals["generation_passes"] / denom, 4) if denom else None
    if totals["generation_attempts"]:
        totals["one_pass_rate"] = round(totals["one_pass_count"] / totals["generation_attempts"], 4)
        totals["redraw_rate"] = round(totals["redraw_count"] / totals["generation_attempts"], 4)
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
        "| 集数 | 事件数 | 成本 | 耗时 | 生成次数 | 重抽 | QA阻断 | QA警告 | 最终通过率 |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|",
        (
            f"| {totals['episode_count']} | {totals['event_count']} | {format_cost(totals['cost_totals'])} | "
            f"{totals['duration_hms']} | {totals['generation_attempts']} | {totals['redraw_count']} | "
            f"{totals['qa_blockers']} | {totals['qa_warnings']} | {format_rate(totals['final_pass_rate'])} |"
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
        *_benchmark_rows(dashboard),
        "",
        "## 逐集",
        "",
        "| 集 | 当前前沿 | 成本 | 每分钟成本 | 耗时 | 一次通过率 | 重抽率 | 重抽原因Top3 | QA阻断 | 净回收 | 回收/成本 |",
        "|---|---|---|---|---:|---:|---:|---|---:|---|---:|",
    ]
    for item in dashboard["episodes"]:
        reasons = Counter(item["redraw_reasons"]).most_common(3)
        reason_text = "；".join(f"{k}×{v}" for k, v in reasons) if reasons else "—"
        lines.append(
            f"| {item['episode']} | {item.get('progress_next_stage') or '—'} | "
            f"{format_cost(item['cost_totals'])} | {format_per_min(item.get('cost_per_finished_min', {}))} | "
            f"{item['duration_hms']} | {format_rate(item.get('one_pass_rate'))} | "
            f"{format_rate(item.get('redraw_rate'))} | {reason_text} | "
            f"{item['qa_blockers']} | {format_cost(item.get('release_net_totals', {}))} | {format_ratio(item.get('recoup_ratio', {}))} |"
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

    lines.append("")
    return "\n".join(lines)


def write_dashboard(root: str, dashboard: Dict[str, Any]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    json_path = os.path.join(production_dir(root), DASHBOARD_JSON)
    md_path = os.path.join(production_dir(root), DASHBOARD_MD)
    atomic_write_text(json_path, json.dumps(dashboard, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    atomic_write_text(md_path, render_markdown(dashboard))


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

    # 逐集定位：通过率下限 / QA 阻断（让告警指到具体集）
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
            f"<td>{format_rate(ep.get('final_pass_rate'))}</td><td>{format_rate(ep.get('redraw_rate'))}</td>"
            f"<td>{ep.get('qa_blockers',0)}</td><td>{ep.get('qa_warnings',0)}</td></tr>"
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
成本 {format_cost(totals.get('cost_totals',{}))} ｜ 通过率 {format_rate(totals.get('final_pass_rate'))} ｜
重抽率 {format_rate(totals.get('redraw_rate'))} ｜ QA阻断 {totals.get('qa_blockers',0)} / warn {totals.get('qa_warnings',0)}</div>
<h2>告警（{_count_level(alerts,'critical')} critical / {_count_level(alerts,'warn')} warn）</h2>
<ul>{alert_rows}</ul>
<h2>逐集</h2>
<table><tr><th>集</th><th>成本</th><th>通过率</th><th>重抽率</th><th>QA阻断</th><th>QA警告</th></tr>
{''.join(rows) or '<tr><td colspan=6>暂无数据</td></tr>'}</table>
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
    cost = None
    if ns.cost is not None:
        cost = {
            "amount": ns.cost,
            "currency": ns.currency,
            "unit": ns.unit or ns.currency,
            "provider": ns.provider,
        }
    generation = None
    if ns.asset or ns.attempt or ns.status or ns.redraw_reason or ns.attempts:
        generation = {
            "asset": ns.asset,
            "attempt": ns.attempt,
            "attempts": ns.attempts,
            "status": ns.status,
            "redraw_reason": ns.redraw_reason,
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

    return {
        "kind": CONSISTENCY_FINDINGS_KIND,
        "version": 1,
        "root": root,
        "episode": episode,
        "gate_stage": stage,
        "generated_at": now_iso(),
        "summary": {"total": len(rows), "severity": severity_counts, "by_dim": by_dim},
        "findings": rows,
        "auto_return_tasks": auto_tasks,
        "source": {"kind": "n2d_gate", "path": "n2d-review/scripts/gate.py"},
    }


def write_gate_findings(root: str, episode: str, stage: str, findings: List[Dict[str, Any]]) -> str:
    path = gate_findings_path(root, episode, stage)
    atomic_write_text(path, json.dumps(gate_findings_payload(root, episode, stage, findings), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path


def image_qc_findings(root: str, episode: str) -> List[Dict[str, Any]]:
    """出图阶段额外跑 image_qc.py（生图后像素一致性 + 逐镜 prompt lint），转成与 gate.py
    同形的 findings 合并入账。dashboard 在 n2d-image / n2d-review 之上，用 subprocess 调
    避免 n2d-review→n2d-image 循环依赖。脚本缺失/出错/输出非 JSON → 返回 []（绝不阻断 gate）。
    生图前跑（无 PNG）时像素项自然空，lint 仍能提前抓非法 CHAR_id；生图后跑则验像素。"""
    script = os.path.join(REPO_SKILLS, "n2d-image", "scripts", "image_qc.py")
    if not os.path.isfile(script):
        return []
    try:
        proc = subprocess.run(
            [sys.executable, script, root, episode, "--findings"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=600,
        )
        data = json.loads(proc.stdout or "[]")
    except Exception:
        return []
    return [f for f in data if isinstance(f, dict)] if isinstance(data, list) else []


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
    # image_preflight 也合并它：无 PNG 时像素项自然为空，但 prompt lint 可在付费生图前拦非法 CHAR_id/纯文生图风险。
    return_code = proc.returncode
    if stage in {"image_preflight", "image"}:
        qc = image_qc_findings(root, episode)
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


def cmd_forecast(ns: argparse.Namespace) -> int:
    root, ep = ns.root, normalize_episode(ns.episode)
    agg = aggregate_events(root, load_events(root))
    totals = agg.get("totals", {})
    cpm = totals.get("cost_per_finished_min") or {}
    finished_min = round(float(totals.get("runtime_sec") or 0.0) / 60.0, 2)
    planned_sec, src = storyboard_duration(root, ep)
    planned_min = round((planned_sec or 0.0) / 60.0, 2)

    out: Dict[str, Any] = {
        "kind": "n2d_cost_forecast", "episode": ep,
        "history_finished_min": finished_min, "cost_per_finished_min": cpm,
        "planned_min": planned_min, "planned_source": src,
        "forecast_cost": {}, "notes": [],
        "redraw_leak_top": [{"category": c, "count": n} for c, n in top_redraw_leak(totals.get("redraw_categories", {}))],
        "show_redraw_rate": totals.get("redraw_rate"),
    }
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
