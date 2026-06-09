#!/usr/bin/env python3
"""Batch queue ledger for novel2drama/n2d.

This script plans and tracks work; it does not execute model calls.  Actual
generation still goes through the corresponding n2d skill.  Keeping the queue
as a deterministic JSON ledger lets multiple agents claim tasks safely, retry
failures, cap budget, and rerun only affected scopes.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import socket
import sys
import time
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    import fcntl  # POSIX 文件锁（mac/Linux）
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

SCRIPT_DIR = os.path.dirname(__file__)
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))
COMMON = os.path.join(REPO_SKILLS, "common")
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_contract import (  # noqa: E402  生产数据目录 / kind 单一真值源
    BATCH_QUEUE_KIND,
    PRODUCTION_DIR,
    production_dir,
    stage_for_key,
    stage_for_progress_column,
    stage_specs,
)
from n2d_route import (  # noqa: E402
    episode_number as route_episode_number,
    is_done,
    normalize_episode as route_normalize_episode,
    parse_progress,
    stage_of,
)

BATCH_KIND = BATCH_QUEUE_KIND
VERSION = 1
QUEUE_JSON = "batch_queue.json"
QUEUE_MD = "batch_queue.md"
QUEUE_LOCK = "batch_queue.lock"
DEFAULT_LEASE_SECONDS = 1800  # 认领后租约时长；超时未 mark/续租 → 可被回收（断点恢复）

DEFAULT_COST_ESTIMATES = {
    "script_stage1": {"amount": 0.2, "unit": "work_units"},
    "voice": {"amount": 1.0, "unit": "work_units"},
    "script_stage2": {"amount": 0.3, "unit": "work_units"},
    "image_prompt": {"amount": 0.2, "unit": "work_units"},
    "image": {"amount": 3.0, "unit": "work_units"},
    "video_prompt": {"amount": 0.2, "unit": "work_units"},
    "video": {"amount": 12.0, "unit": "work_units"},
    "compose": {"amount": 0.5, "unit": "work_units"},
}

ACTIVE_STATUSES = {"queued", "running", "retry_queued"}
REPLACEABLE_MERGE_STATUSES = {"queued", "blocked_budget"}
BUDGET_FLEXIBLE_STATUSES = {"queued", "blocked_budget"}
BUDGET_IGNORED_STATUSES = {"cancelled"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def now_ts() -> float:
    return time.time()


def default_worker() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def lock_path(root: str) -> str:
    return os.path.join(production_dir(root), QUEUE_LOCK)


@contextlib.contextmanager
def queue_lock(root: str, *, timeout: float = 30.0, poll: float = 0.1):
    """单机多 worker 互斥：所有"读队列→改→写"必须在此锁内做，避免双认领/互相覆盖。

    主用 POSIX `fcntl.flock`（本地 FS 可靠）；无 fcntl 时退回 O_EXCL 锁文件自旋。
    注意：flock 跨 NFS 不可靠——多机请用真正的协调后端，不要靠本锁。
    """
    os.makedirs(production_dir(root), exist_ok=True)
    path = lock_path(root)
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
                        raise TimeoutError(f"queue lock timeout ({timeout}s): {path}")
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
                    raise TimeoutError(f"queue lock timeout ({timeout}s): {path}")
                time.sleep(poll)
        try:
            yield
        finally:
            os.close(fd)
            with contextlib.suppress(OSError):
                os.unlink(path)


def queue_path(root: str) -> str:
    return os.path.join(production_dir(root), QUEUE_JSON)


def queue_md_path(root: str) -> str:
    return os.path.join(production_dir(root), QUEUE_MD)


def normalize_episode(value: str) -> str:
    return route_normalize_episode(value)


def episode_num(ep: str) -> int:
    n = route_episode_number(ep)
    return n if n is not None else 10**9


def parse_episode_selector(selector: Optional[str]) -> Optional[Set[str]]:
    if not selector:
        return None
    selected: Set[str] = set()
    for part in selector.split(","):
        token = part.strip()
        if not token:
            continue
        range_sep = next((sep for sep in ("-", "–", "—", "~", "～", "至") if sep in token), None)
        if range_sep:
            start_s, end_s = token.split(range_sep, 1)
            start, end = route_episode_number(start_s), route_episode_number(end_s)
            if start is None or end is None:
                raise ValueError(f"invalid episode range: {part}")
            if end < start:
                start, end = end, start
            for n in range(start, end + 1):
                selected.add(f"第{n}集")
            continue
        selected.add(normalize_episode(token))
    return selected


def load_cost_estimates(root: str) -> Dict[str, Dict[str, Any]]:
    estimates = {k: dict(v) for k, v in DEFAULT_COST_ESTIMATES.items()}
    path = os.path.join(production_dir(root), "stage_cost_estimates.json")
    if not os.path.isfile(path):
        return estimates
    data = json.load(open(path, encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be an object")
    for key, value in data.items():
        if isinstance(value, dict) and "amount" in value:
            estimates[key] = dict(value)
        elif isinstance(value, (int, float)):
            unit = estimates.get(key, {}).get("unit", "work_units")
            estimates[key] = {"amount": float(value), "unit": unit}
    return estimates


def stage_aliases(spec: Dict[str, Any]) -> Set[str]:
    aliases = {
        str(spec.get("key", "")),
        str(spec.get("label", "")),
        str(spec.get("owner", "")),
        str(spec.get("gate_stage", "")),
    }
    aliases.update(str(col) for col in spec.get("progress_columns", ()))
    return {item for item in aliases if item}


def stage_matches(spec: Dict[str, Any], filters: Optional[Set[str]]) -> bool:
    if not filters:
        return True
    return bool(stage_aliases(spec) & filters)


def find_stage(value: str) -> Dict[str, Any]:
    spec = stage_for_key(value)
    if spec:
        return spec
    for candidate in stage_specs():
        if value in stage_aliases(candidate):
            return candidate
    raise ValueError(f"unknown stage: {value}")


def task_id(ep: str, stage_key: str, reason: str, index: int = 0) -> str:
    base = f"{episode_num(ep):03d}-{stage_key}-{reason}"
    return base if index == 0 else f"{base}-{index}"


def task_from_spec(
    root: str,
    ep: str,
    spec: Dict[str, Any],
    *,
    reason: str,
    priority: int,
    cost_estimates: Dict[str, Dict[str, Any]],
    max_retries: int,
    rerun_scope: Optional[str] = None,
    affected_artifacts: Optional[List[str]] = None,
    affected_shots: Optional[List[str]] = None,
) -> Dict[str, Any]:
    stage_key = str(spec["key"])
    estimate = dict(cost_estimates.get(stage_key, {"amount": 0.0, "unit": "work_units"}))
    return {
        "id": task_id(ep, stage_key, reason),
        "episode": ep,
        "stage_key": stage_key,
        "stage_label": spec.get("label", ""),
        "owner": spec.get("owner", ""),
        "command": str(spec.get("command", "")).format(root=root, ep=ep),
        "gate_stage": spec.get("gate_stage"),
        "status": "queued",
        "attempts": 0,
        "max_retries": max_retries,
        "priority": priority,
        "reason": reason,
        "estimated_cost": estimate,
        "rerun_scope": rerun_scope or "",
        "affected_artifacts": affected_artifacts or [],
        "affected_shots": affected_shots or [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "history": [],
    }


def route_tasks(
    root: str,
    *,
    episodes: Optional[Set[str]],
    stage_filters: Optional[Set[str]],
    cost_estimates: Dict[str, Dict[str, Any]],
    max_retries: int,
) -> List[Dict[str, Any]]:
    header, rows = parse_progress(root)
    tasks: List[Dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: int(item.get("_num", 10**9))):
        ep = row.get("_ep") or row.get("集")
        if not ep:
            continue
        ep_key = normalize_episode(ep)
        if episodes and ep not in episodes and ep_key not in episodes:
            continue
        route = stage_of(root, row, header)
        col = route.get("col")
        if not col:
            continue
        spec = stage_for_progress_column(str(col))
        if not spec:
            # Special production-mode routes can point to a skill instead of a
            # direct progress column; currently this is used for补真实配音.
            owner = route.get("skill")
            spec = next((s for s in stage_specs() if s.get("owner") == owner), None)
        if not spec or not stage_matches(spec, stage_filters):
            continue
        tasks.append(
            task_from_spec(
                root,
                ep,
                spec,
                reason="progress",
                priority=len(tasks) + 1,
                cost_estimates=cost_estimates,
                max_retries=max_retries,
            )
        )
    return dedupe_task_ids(tasks)


def rerun_tasks(
    root: str,
    *,
    episodes: Set[str],
    rerun_from: str,
    cost_estimates: Dict[str, Dict[str, Any]],
    max_retries: int,
    rerun_scope: Optional[str],
    affected_artifacts: List[str],
    affected_shots: List[str],
) -> List[Dict[str, Any]]:
    spec = find_stage(rerun_from)
    tasks: List[Dict[str, Any]] = []
    for ep in sorted(episodes, key=episode_num):
        tasks.append(
            task_from_spec(
                root,
                ep,
                spec,
                reason="rerun",
                priority=len(tasks) + 1,
                cost_estimates=cost_estimates,
                max_retries=max_retries,
                rerun_scope=rerun_scope,
                affected_artifacts=affected_artifacts,
                affected_shots=affected_shots,
            )
        )
    return dedupe_task_ids(tasks)


def dedupe_task_ids(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, int] = {}
    for task in tasks:
        tid = str(task["id"])
        seen[tid] = seen.get(tid, 0) + 1
        if seen[tid] > 1:
            task["id"] = f"{tid}-{seen[tid]}"
    return tasks


def apply_budget(tasks: List[Dict[str, Any]], limit: Optional[float], unit: Optional[str]) -> Dict[str, Any]:
    total = 0.0
    accepted = 0.0
    blocked = 0
    for task in tasks:
        estimate = task.get("estimated_cost", {})
        amount = float(estimate.get("amount") or 0.0)
        est_unit = str(estimate.get("unit") or "work_units")
        if unit and est_unit != unit:
            task["status"] = "blocked_budget"
            task["budget_note"] = f"estimate unit {est_unit} != budget unit {unit}"
            blocked += 1
            continue
        total += amount
        if limit is not None and accepted + amount > limit:
            task["status"] = "blocked_budget"
            task["budget_note"] = f"budget cap {limit} {unit or est_unit} exceeded"
            blocked += 1
        else:
            accepted += amount
    return {
        "limit": limit,
        "unit": unit or "mixed",
        "estimated_total": round(total, 6),
        "accepted_total": round(accepted, 6),
        "blocked_tasks": blocked,
    }


def _budget_limit(value: Any) -> Optional[float]:
    if value in (None, "", "—"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _budget_unit(value: Any) -> Optional[str]:
    unit = str(value or "").strip()
    return None if not unit or unit == "mixed" else unit


def reapply_ledger_budget(queue: Dict[str, Any]) -> Dict[str, Any]:
    """Recompute budget against the whole queue ledger after additive planning.

    Historical done/running/retry tasks keep their state but still consume the
    ledger budget.  Only never-started queued/blocked_budget tasks are toggled
    by the recalculation.
    """
    old_budget = queue.get("budget") if isinstance(queue.get("budget"), dict) else {}
    limit = _budget_limit(old_budget.get("limit"))
    unit = _budget_unit(old_budget.get("unit"))
    total = 0.0
    accepted = 0.0
    blocked = 0
    for task in sorted(queue.get("tasks", []), key=lambda item: int(item.get("priority", 999999))):
        status = str(task.get("status") or "queued")
        if status in BUDGET_IGNORED_STATUSES:
            continue
        estimate = task.get("estimated_cost", {})
        amount = float(estimate.get("amount") or 0.0)
        est_unit = str(estimate.get("unit") or "work_units")
        flexible = status in BUDGET_FLEXIBLE_STATUSES and int(task.get("attempts") or 0) == 0
        if unit and est_unit != unit:
            if flexible:
                task["status"] = "blocked_budget"
                task["budget_note"] = f"estimate unit {est_unit} != budget unit {unit}"
            blocked += 1
            continue
        total += amount
        if flexible:
            if limit is not None and accepted + amount > limit:
                task["status"] = "blocked_budget"
                task["budget_note"] = f"ledger budget cap {limit} {unit or est_unit} exceeded"
                blocked += 1
            else:
                task["status"] = "queued"
                task.pop("budget_note", None)
                accepted += amount
            continue
        if status != "blocked_budget":
            accepted += amount
        else:
            blocked += 1
    budget = dict(old_budget)
    budget.update({
        "limit": limit,
        "unit": unit or "mixed",
        "estimated_total": round(total, 6),
        "accepted_total": round(accepted, 6),
        "blocked_tasks": blocked,
        "scope": "ledger",
        "recomputed_at": now_iso(),
    })
    queue["budget"] = budget
    return budget


def make_batches(tasks: List[Dict[str, Any]], max_concurrency: int) -> List[List[str]]:
    ready = [task for task in sorted(tasks, key=lambda item: int(item["priority"])) if task["status"] == "queued"]
    batches: List[List[str]] = []
    for i in range(0, len(ready), max(1, max_concurrency)):
        batches.append([str(task["id"]) for task in ready[i:i + max(1, max_concurrency)]])
    return batches


def make_queue(
    root: str,
    tasks: List[Dict[str, Any]],
    *,
    max_concurrency: int,
    max_retries: int,
    budget: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "kind": BATCH_KIND,
        "version": VERSION,
        "root": root,
        "generated_at": now_iso(),
        "updated_at": now_iso(),
        "max_concurrency": max_concurrency,
        "max_retries": max_retries,
        "budget": budget,
        "summary": summarize_tasks(tasks),
        "batches": make_batches(tasks, max_concurrency),
        "tasks": tasks,
    }


def _next_available_task_id(existing_ids: Set[str], task: Dict[str, Any]) -> str:
    base = str(task.get("id") or "")
    if base not in existing_ids:
        return base
    index = 2
    while f"{base}-{index}" in existing_ids:
        index += 1
    return f"{base}-{index}"


def merge_queues(existing: Dict[str, Any], planned: Dict[str, Any]) -> Dict[str, Any]:
    """Merge a newly planned queue into an existing ledger without clobbering work in flight.

    Default planning is additive: running/retry/done/failed task history is preserved.
    Only never-started queued/budget-blocked tasks with the same id are refreshed from
    the latest plan.  New tasks whose id collides with non-replaceable history get a
    stable numeric suffix so fresh reruns can be enqueued without erasing old attempts.
    """
    merged = deepcopy(existing)
    merged["root"] = planned.get("root", merged.get("root"))
    merged["max_concurrency"] = planned.get("max_concurrency", merged.get("max_concurrency", 1))
    merged["max_retries"] = planned.get("max_retries", merged.get("max_retries", 0))
    merged["budget"] = planned.get("budget", merged.get("budget", {}))
    merged["last_plan_at"] = planned.get("generated_at") or now_iso()

    tasks = list(merged.get("tasks", []))
    index = {str(task.get("id")): i for i, task in enumerate(tasks)}
    existing_ids = set(index)
    for incoming in planned.get("tasks", []):
        task = deepcopy(incoming)
        tid = str(task.get("id") or "")
        if tid in index:
            old = tasks[index[tid]]
            old_status = str(old.get("status") or "")
            old_attempts = int(old.get("attempts") or 0)
            if old_status in REPLACEABLE_MERGE_STATUSES and old_attempts == 0:
                history = list(old.get("history", []))
                history.append({"ts": now_iso(), "action": "plan:refresh", "prev_status": old_status})
                task["history"] = history + list(task.get("history", []))
                tasks[index[tid]] = task
                existing_ids.add(tid)
            else:
                task["id"] = _next_available_task_id(existing_ids, task)
                task.setdefault("history", []).append(
                    {"ts": now_iso(), "action": "plan:dedupe", "base_id": tid}
                )
                existing_ids.add(str(task["id"]))
                tasks.append(task)
            continue
        existing_ids.add(tid)
        tasks.append(task)
    merged["tasks"] = tasks
    return merged


def _has_running(queue: Dict[str, Any]) -> bool:
    return any(task.get("status") == "running" for task in queue.get("tasks", []))


def write_planned_queue(root: str, planned: Dict[str, Any], *, replace: bool = False, force: bool = False) -> Dict[str, Any]:
    """Write a planned queue safely.

    - default: merge into any existing queue under the queue lock;
    - --replace: overwrite the ledger, but refuse to clobber running tasks unless
      --force is supplied.
    """
    with queue_lock(root):
        try:
            existing = load_queue(root)
        except FileNotFoundError:
            existing = None
        if replace:
            if existing and _has_running(existing) and not force:
                raise RuntimeError("existing batch queue has running tasks; use --force to replace anyway")
            out = planned
        elif existing:
            reclaim_expired(existing)
            out = merge_queues(existing, planned)
        else:
            out = planned
        reapply_ledger_budget(out)
        save_queue(root, out)
        return deepcopy(out)


def summarize_tasks(tasks: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    stages: Dict[str, int] = {}
    for task in tasks:
        status = str(task.get("status", "unknown"))
        stage = str(task.get("stage_key", "unknown"))
        counts[status] = counts.get(status, 0) + 1
        stages[stage] = stages.get(stage, 0) + 1
    return {"total": len(tasks), "by_status": counts, "by_stage": stages}


def load_queue(root: str) -> Dict[str, Any]:
    path = queue_path(root)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    data = json.load(open(path, encoding="utf-8"))
    if not isinstance(data, dict) or data.get("kind") != BATCH_KIND:
        raise ValueError(f"{path} is not an n2d batch queue")
    return data


def save_queue(root: str, queue: Dict[str, Any]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    queue["updated_at"] = now_iso()
    queue["summary"] = summarize_tasks(queue.get("tasks", []))
    queue["batches"] = make_batches(queue.get("tasks", []), int(queue.get("max_concurrency") or 1))
    # 原子写：temp + os.replace，读者永远看不到半截文件（同盘原子）。
    target = queue_path(root)
    tmp = f"{target}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(queue, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, target)
    with open(queue_md_path(root), "w", encoding="utf-8") as fh:  # md 仅供人读，直接写即可
        fh.write(render_markdown(queue))


def render_markdown(queue: Dict[str, Any]) -> str:
    summary = queue.get("summary", {})
    budget = queue.get("budget", {})
    lines = [
        "# n2d 批量任务队列",
        "",
        f"- 更新时间：{queue.get('updated_at') or queue.get('generated_at')}",
        f"- 最大并发：{queue.get('max_concurrency')}",
        f"- 重试上限：{queue.get('max_retries')}",
        f"- 预算：{budget.get('accepted_total', 0)} / {budget.get('limit', '—')} {budget.get('unit', '')}",
        f"- 任务数：{summary.get('total', 0)}",
        "",
        "## 状态",
        "",
        "| 状态 | 数量 |",
        "|---|---:|",
    ]
    for status, count in sorted(summary.get("by_status", {}).items()):
        lines.append(f"| {status} | {count} |")
    lines.extend([
        "",
        "## 任务",
        "",
        "| ID | 集 | Stage | Owner | 状态 | 尝试 | 估算成本 | 范围 |",
        "|---|---|---|---|---|---:|---:|---|",
    ])
    for task in sorted(queue.get("tasks", []), key=lambda item: int(item.get("priority", 999999))):
        est = task.get("estimated_cost", {})
        amount = est.get("amount", 0)
        unit = est.get("unit", "")
        scope = task.get("rerun_scope") or ",".join(task.get("affected_shots", [])) or "—"
        lines.append(
            f"| {task.get('id')} | {task.get('episode')} | {task.get('stage_key')} | "
            f"{task.get('owner')} | {task.get('status')} | {task.get('attempts', 0)} | "
            f"{amount} {unit} | {scope} |"
        )
    lines.append("")
    return "\n".join(lines)


def claim_tasks(
    queue: Dict[str, Any],
    limit: Optional[int],
    *,
    worker: Optional[str] = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> List[Dict[str, Any]]:
    max_concurrency = int(queue.get("max_concurrency") or 1)
    running = sum(1 for task in queue.get("tasks", []) if task.get("status") == "running")
    capacity = max(0, max_concurrency - running)
    if limit is not None:
        capacity = min(capacity, limit)
    claimed: List[Dict[str, Any]] = []
    for task in sorted(queue.get("tasks", []), key=lambda item: int(item.get("priority", 999999))):
        if capacity <= 0:
            break
        if task.get("status") not in {"queued", "retry_queued"}:
            continue
        task["status"] = "running"
        task["attempts"] = int(task.get("attempts") or 0) + 1
        task["updated_at"] = now_iso()
        task["worker"] = worker or ""
        task["lease_until"] = now_ts() + max(1, int(lease_seconds))
        task["lease_until_iso"] = dt.datetime.fromtimestamp(task["lease_until"], dt.timezone.utc).replace(microsecond=0).isoformat()
        task.setdefault("history", []).append(
            {"ts": now_iso(), "action": "claim", "attempt": task["attempts"], "worker": worker or ""}
        )
        claimed.append(task)
        capacity -= 1
    return claimed


def _clear_lease(task: Dict[str, Any]) -> None:
    for key in ("worker", "lease_until", "lease_until_iso"):
        task.pop(key, None)


def reclaim_expired(
    queue: Dict[str, Any],
    *,
    now: Optional[float] = None,
    worker: Optional[str] = None,
    force_worker: bool = False,
) -> List[Dict[str, Any]]:
    """回收"running 但租约过期"的任务（worker 崩了/被杀）→ retry_queued 或 failed。
    force_worker=True 时，额外强制回收 worker==自己 的 running（用于本 worker --resume 自愈）。"""
    now = now_ts() if now is None else now
    reclaimed: List[Dict[str, Any]] = []
    for task in queue.get("tasks", []):
        if task.get("status") != "running":
            continue
        lease = task.get("lease_until")
        expired = isinstance(lease, (int, float)) and lease < now
        mine = force_worker and worker and task.get("worker") == worker
        if not (expired or mine):
            continue
        attempts = int(task.get("attempts") or 0)
        max_retries = int(task.get("max_retries") or queue.get("max_retries") or 0)
        task["status"] = "retry_queued" if attempts <= max_retries else "failed"
        task["updated_at"] = now_iso()
        reason = "lease_expired" if expired else "worker_resume"
        task.setdefault("history", []).append(
            {"ts": now_iso(), "action": "reclaim", "reason": reason, "prev_worker": task.get("worker", ""), "attempt": attempts}
        )
        _clear_lease(task)
        reclaimed.append(task)
    return reclaimed


def renew_lease(queue: Dict[str, Any], task_ids: Iterable[str], lease_seconds: int, worker: Optional[str] = None) -> int:
    """心跳续租：把仍 running 且属于本 worker 的任务租约往后延，防止长任务被误回收。"""
    ids = set(task_ids)
    renewed = 0
    for task in queue.get("tasks", []):
        if task.get("id") in ids and task.get("status") == "running" and (worker is None or task.get("worker") == worker):
            task["lease_until"] = now_ts() + max(1, int(lease_seconds))
            task["lease_until_iso"] = dt.datetime.fromtimestamp(task["lease_until"], dt.timezone.utc).replace(microsecond=0).isoformat()
            renewed += 1
    return renewed


# ── 锁内封装：所有"读→改→写"的安全入口（runner/CLI 用这些，不要裸调上面的纯函数）──

def claim(root: str, *, limit: Optional[int] = None, worker: Optional[str] = None,
          lease_seconds: int = DEFAULT_LEASE_SECONDS) -> List[Dict[str, Any]]:
    with queue_lock(root):
        queue = load_queue(root)
        reclaim_expired(queue)  # 每次认领前先回收过期租约（自动断点恢复）
        claimed = claim_tasks(queue, limit, worker=worker, lease_seconds=lease_seconds)
        save_queue(root, queue)
        return [dict(task) for task in claimed]


def mark(root: str, task_id_value: str, status: str, note: str = "",
         *, runner: Optional[Dict[str, Any]] = None,
         expected_worker: Optional[str] = None,
         expected_attempt: Optional[int] = None) -> Dict[str, Any]:
    with queue_lock(root):
        queue = load_queue(root)
        task = mark_task(
            queue,
            task_id_value,
            status,
            note,
            expected_worker=expected_worker,
            expected_attempt=expected_attempt,
        )
        if runner is not None:
            task["last_runner"] = runner
        save_queue(root, queue)
        return dict(task)


def reclaim(root: str, *, worker: Optional[str] = None, force_worker: bool = False) -> List[Dict[str, Any]]:
    with queue_lock(root):
        queue = load_queue(root)
        reclaimed = reclaim_expired(queue, worker=worker, force_worker=force_worker)
        save_queue(root, queue)
        return [dict(task) for task in reclaimed]


def renew(root: str, task_ids: Iterable[str], lease_seconds: int, worker: Optional[str] = None) -> int:
    with queue_lock(root):
        queue = load_queue(root)
        n = renew_lease(queue, task_ids, lease_seconds, worker)
        if n:
            save_queue(root, queue)
        return n


def mark_task(queue: Dict[str, Any], task_id_value: str, status: str, note: str = "",
              *, expected_worker: Optional[str] = None,
              expected_attempt: Optional[int] = None) -> Dict[str, Any]:
    task = next((item for item in queue.get("tasks", []) if item.get("id") == task_id_value), None)
    if task is None:
        raise KeyError(task_id_value)
    if expected_worker is not None and task.get("worker") != expected_worker:
        raise ValueError(
            f"task {task_id_value} is not owned by worker {expected_worker}; current worker={task.get('worker') or '-'}"
        )
    if expected_attempt is not None and int(task.get("attempts") or 0) != int(expected_attempt):
        raise ValueError(
            f"task {task_id_value} attempt mismatch; expected {expected_attempt}, current {task.get('attempts') or 0}"
        )
    if status == "pass":
        task["status"] = "done"
    elif status == "fail":
        attempts = int(task.get("attempts") or 0)
        max_retries = int(task.get("max_retries") or queue.get("max_retries") or 0)
        task["status"] = "retry_queued" if attempts <= max_retries else "failed"
    elif status in {"queued", "running", "blocked_budget", "cancelled"}:
        task["status"] = status
    else:
        raise ValueError(f"unknown mark status: {status}")
    if task["status"] != "running":  # 离开 running 即释放租约，便于回收/并发统计
        _clear_lease(task)
    task["updated_at"] = now_iso()
    task.setdefault("history", []).append({"ts": now_iso(), "action": f"mark:{status}", "note": note})
    if note:
        task["last_note"] = note
    return task


def cmd_plan(ns: argparse.Namespace) -> int:
    root = ns.root.rstrip("/")
    selected = parse_episode_selector(ns.episodes)
    estimates = load_cost_estimates(root)
    if ns.rerun_from:
        if not selected:
            raise SystemExit("--rerun-from requires --episodes")
        tasks = rerun_tasks(
            root,
            episodes=selected,
            rerun_from=ns.rerun_from,
            cost_estimates=estimates,
            max_retries=ns.max_retries,
            rerun_scope=ns.scope,
            affected_artifacts=ns.affected_artifact or [],
            affected_shots=ns.affected_shot or [],
        )
    else:
        stage_filters = set(ns.stage or [])
        tasks = route_tasks(
            root,
            episodes=selected,
            stage_filters=stage_filters or None,
            cost_estimates=estimates,
            max_retries=ns.max_retries,
        )
    budget = apply_budget(tasks, ns.budget, ns.budget_unit)
    queue = make_queue(
        root,
        tasks,
        max_concurrency=ns.max_concurrency,
        max_retries=ns.max_retries,
        budget=budget,
    )
    if not ns.no_write:
        queue = write_planned_queue(root, queue, replace=ns.replace, force=ns.force)
    print(render_markdown(queue) if ns.markdown else json.dumps(queue, ensure_ascii=False, indent=2))
    return 0


def cmd_claim(ns: argparse.Namespace) -> int:
    claimed = claim(
        ns.root.rstrip("/"),
        limit=ns.limit,
        worker=ns.worker or default_worker(),
        lease_seconds=ns.lease_seconds,
    )
    print(json.dumps(claimed, ensure_ascii=False, indent=2))
    return 0 if claimed else 1


def cmd_mark(ns: argparse.Namespace) -> int:
    task = mark(
        ns.root.rstrip("/"),
        ns.task_id,
        ns.status,
        ns.note or "",
        expected_worker=ns.worker,
        expected_attempt=ns.attempt,
    )
    print(json.dumps(task, ensure_ascii=False, indent=2))
    return 0


def cmd_reclaim(ns: argparse.Namespace) -> int:
    reclaimed = reclaim(
        ns.root.rstrip("/"),
        worker=ns.worker or None,
        force_worker=ns.force_worker,
    )
    print(json.dumps({"reclaimed": len(reclaimed), "tasks": [t.get("id") for t in reclaimed]}, ensure_ascii=False, indent=2))
    return 0


def cmd_status(ns: argparse.Namespace) -> int:
    queue = load_queue(ns.root.rstrip("/"))
    print(render_markdown(queue) if ns.markdown else json.dumps(queue.get("summary", {}), ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d batch queue planner")
    sub = ap.add_subparsers(dest="cmd", required=True)

    plan = sub.add_parser("plan", help="scan _进度.md and write a batch queue")
    plan.add_argument("root")
    plan.add_argument("--episodes", help="episode selector, e.g. 1-5,8 or 第1集,第2集")
    plan.add_argument("--stage", action="append", help="filter by stage key/owner/label/progress column")
    plan.add_argument("--max-concurrency", type=int, default=2)
    plan.add_argument("--max-retries", type=int, default=1)
    plan.add_argument("--budget", type=float)
    plan.add_argument("--budget-unit")
    plan.add_argument("--rerun-from", help="stage key/alias for targeted rerun")
    plan.add_argument("--scope", help="human-readable rerun scope")
    plan.add_argument("--affected-artifact", action="append", default=[])
    plan.add_argument("--affected-shot", action="append", default=[])
    plan.add_argument("--no-write", action="store_true")
    plan.add_argument("--replace", action="store_true", help="replace the existing queue instead of merging")
    plan.add_argument("--force", action="store_true", help="with --replace, allow overwriting a queue with running tasks")
    plan.add_argument("--markdown", action="store_true")
    plan.set_defaults(func=cmd_plan)

    claim_cmd = sub.add_parser("claim", help="claim queued tasks up to concurrency (atomic, with lease)")
    claim_cmd.add_argument("root")
    claim_cmd.add_argument("--limit", type=int)
    claim_cmd.add_argument("--worker", help="worker id（默认 host:pid）；多 worker 必给稳定 id 才能 --resume 自愈")
    claim_cmd.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS,
                           help=f"租约秒数；超时未 mark/续租即可被回收（默认 {DEFAULT_LEASE_SECONDS}）")
    claim_cmd.set_defaults(func=cmd_claim)

    mark = sub.add_parser("mark", help="mark a task pass/fail/etc.")
    mark.add_argument("root")
    mark.add_argument("task_id")
    mark.add_argument("--status", required=True, choices=["pass", "fail", "queued", "running", "blocked_budget", "cancelled"])
    mark.add_argument("--note")
    mark.add_argument("--worker", help="optional expected worker guard; used by runners to avoid stale marks")
    mark.add_argument("--attempt", type=int, help="optional expected attempt guard; used by runners to avoid stale marks")
    mark.set_defaults(func=cmd_mark)

    reclaim_cmd = sub.add_parser("reclaim", help="回收过期租约的 running 任务 → retry_queued/failed（断点恢复）")
    reclaim_cmd.add_argument("root")
    reclaim_cmd.add_argument("--worker", help="配合 --force-worker：回收该 worker 残留的 running")
    reclaim_cmd.add_argument("--force-worker", action="store_true", help="强制回收 --worker 的 running（不等租约过期；本 worker 重启自愈用）")
    reclaim_cmd.set_defaults(func=cmd_reclaim)

    status = sub.add_parser("status", help="print queue status")
    status.add_argument("root")
    status.add_argument("--markdown", action="store_true")
    status.set_defaults(func=cmd_status)
    return ap


def main(argv: List[str]) -> int:
    ns = parser().parse_args(argv)
    return ns.func(ns)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
