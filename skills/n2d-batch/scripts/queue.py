#!/usr/bin/env python3
"""Batch queue ledger for n2d.

This script plans and tracks work; it does not execute model calls.  Actual
generation still goes through the corresponding n2d skill.  Keeping the queue
as a deterministic JSON ledger lets multiple agents claim tasks safely, retry
failures, cap budget, and rerun only affected scopes.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import glob
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
COMMON = os.path.join(REPO_SKILLS, "n2d", "_lib")
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_contract import (  # noqa: E402  生产数据目录 / kind 单一真值源
    ASSET_RERUN_PLAN_KIND,
    BATCH_QUEUE_KIND,
    CONSISTENCY_FINDINGS_KIND,
    PRODUCTION_DIR,
    finding_dim_key,
    finding_fingerprint,
    finding_fingerprints,
    normalize_finding,
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
    fingerprints: Optional[List[str]] = None,
    coarse_fingerprints: Optional[List[str]] = None,
) -> Dict[str, Any]:
    stage_key = str(spec["key"])
    estimate = dict(cost_estimates.get(stage_key, {"amount": 0.0, "unit": "work_units"}))
    command = str(spec.get("command", "")).format(root=root, ep=ep)
    # 最小范围返工：受影响镜头注入命令，让执行端只重跑这些镜头而非整集（不再只是元数据）。
    shots = [s for s in (affected_shots or []) if str(s).strip()]
    if shots and "--shots" not in command:
        command = f"{command} --shots {','.join(shots)}"
    return {
        "id": task_id(ep, stage_key, reason),
        "episode": ep,
        "stage_key": stage_key,
        "stage_label": spec.get("label", ""),
        "owner": spec.get("owner", ""),
        "command": command,
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
        "finding_fingerprints": sorted(set(fingerprints or [])),  # 同一问题指纹：防复审堆叠 + 修复后复检判 resolved
        # 粗粒度指纹 (集×阶段×维度，丢镜头定位)：复检 --coarse 回退用——精确指纹因定位串大改对不上时，
        # 只要本镜头所属 (集,阶段,维度) 桶仍有 findings 就不误判 resolved（宁可多复核，不漏放）。
        "coarse_fingerprints": sorted(set(coarse_fingerprints or [])),
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


def tasks_from_asset_impact(
    root: str,
    plan: Dict[str, Any],
    *,
    cost_estimates: Dict[str, Dict[str, Any]],
    max_retries: int,
    episodes: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """读 asset_impact.py `--output-batch-tasks` 的 n2d_asset_rerun_plan JSON → 队列任务。

    `rerun_tasks[]` 字段与本模块 rerun 入参一一对应：episode / rerun_from / scope /
    affected_artifacts / affected_shots（定妆变更连锁的最小范围重跑，不整集重来）。
    """
    if not isinstance(plan, dict) or plan.get("kind") != ASSET_RERUN_PLAN_KIND:
        raise ValueError(f"not an asset rerun plan (expect kind={ASSET_RERUN_PLAN_KIND})")
    tasks: List[Dict[str, Any]] = []
    for item in plan.get("rerun_tasks") or []:
        if not isinstance(item, dict):
            continue
        ep_raw = str(item.get("episode") or "").strip()
        if not ep_raw:
            continue
        ep = normalize_episode(ep_raw)
        if episodes and ep_raw not in episodes and ep not in episodes:
            continue
        spec = find_stage(str(item.get("rerun_from") or "image"))
        tasks.append(
            task_from_spec(
                root,
                ep,
                spec,
                reason="rerun",
                priority=len(tasks) + 1,
                cost_estimates=cost_estimates,
                max_retries=max_retries,
                rerun_scope=str(item.get("scope") or ""),
                affected_artifacts=[str(a) for a in item.get("affected_artifacts") or []],
                affected_shots=[str(s) for s in item.get("affected_shots") or []],
            )
        )
    return dedupe_task_ids(tasks)


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item not in (None, "")]


def _unique(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _episode_from_item(item: Dict[str, Any], default_episode: str) -> Optional[Tuple[str, str]]:
    ep_raw = str(item.get("episode") or default_episode or "").strip()
    if not ep_raw:
        return None
    return ep_raw, normalize_episode(ep_raw)


def _episode_selected(ep_raw: str, ep: str, episodes: Optional[Set[str]]) -> bool:
    return not episodes or ep_raw in episodes or ep in episodes


def _fallback_shots_from_finding(finding: Dict[str, Any]) -> List[str]:
    shots = _string_list(finding.get("affected_shots"))
    if shots:
        return shots
    shot = str(finding.get("shot") or "").strip()
    if shot:
        if shot.isdigit():
            return [f"Clip_{int(shot):02d}"]
        return [shot]
    loc = str(finding.get("loc") or "").strip()
    if loc.startswith(("Clip_", "Clip ", "镜头")):
        return [loc]
    return []


def tasks_from_consistency_findings(
    root: str,
    report: Dict[str, Any],
    *,
    cost_estimates: Dict[str, Dict[str, Any]],
    max_retries: int,
    episodes: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """读 n2d-review consistency_findings JSON → 最小范围返工队列任务。

    新报告优先消费 `auto_return_tasks`，这是 review 侧已经聚合好的回退建议；
    老报告没有该字段时，按 (episode, return_to_stage, dim) 从 block/warn findings
    做保守聚合，保证审查结果仍能进入 batch 闭环。
    """
    if not isinstance(report, dict) or report.get("kind") != CONSISTENCY_FINDINGS_KIND:
        raise ValueError(f"not a consistency findings report (expect kind={CONSISTENCY_FINDINGS_KIND})")
    default_episode = str(report.get("episode") or "").strip()
    tasks: List[Dict[str, Any]] = []

    auto_tasks = [item for item in report.get("auto_return_tasks") or [] if isinstance(item, dict)]
    if auto_tasks:
        for item in auto_tasks:
            ep_pair = _episode_from_item(item, default_episode)
            if ep_pair is None:
                continue
            ep_raw, ep = ep_pair
            if not _episode_selected(ep_raw, ep, episodes):
                continue
            stage = str(item.get("return_to_stage") or item.get("rerun_from") or "image")
            spec = find_stage(stage)
            dims = [
                finding_dim_key({"dimension": d})
                for d in (_string_list(item.get("dimensions")) or [str(item.get("dim") or item.get("dimension") or "一致性")])
            ]
            raw_scope = {
                "affected_shots": _string_list(item.get("affected_shots")),
                "affected_artifacts": _string_list(item.get("affected_artifacts")),
                "loc": item.get("loc") or "",
            }
            fps = [fp for d in dims for fp in finding_fingerprints(ep, stage, d, raw_scope)]
            coarse = [finding_fingerprint(ep, stage, d) for d in dims]
            tasks.append(
                task_from_spec(
                    root,
                    ep,
                    spec,
                    reason="rerun",
                    priority=len(tasks) + 1,
                    cost_estimates=cost_estimates,
                    max_retries=max_retries,
                    rerun_scope=str(item.get("scope") or item.get("rerun_scope") or ""),
                    affected_artifacts=_string_list(item.get("affected_artifacts")),
                    affected_shots=_string_list(item.get("affected_shots")),
                    fingerprints=fps,
                    coarse_fingerprints=coarse,
                )
            )
        return dedupe_task_ids(tasks)

    grouped: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for finding in report.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        norm = normalize_finding(finding)  # 归一三端别名：sev/dim/msg → 规范字段，不再散落 or 链
        if norm["severity"] not in {"block", "warn"}:
            continue
        ep_pair = _episode_from_item(finding, default_episode)
        if ep_pair is None:
            continue
        ep_raw, ep = ep_pair
        if not _episode_selected(ep_raw, ep, episodes):
            continue
        stage = norm["return_to_stage"] or "image"
        dim = finding_dim_key(finding)  # 规范维度键，task 端与 audit 端指纹可对账
        key = (ep, stage, dim)
        item = grouped.setdefault(
            key,
            {
                "ep": ep,
                "stage": stage,
                "dim": dim,
                "scope": [],
                "affected_artifacts": [],
                "affected_shots": [],
                "fingerprints": [],
            },
        )
        msg = norm["rerun_scope"] or norm["message"]
        item["scope"].append(f"{dim} 返修" + (f"：{msg}" if msg else ""))
        item["affected_artifacts"].extend(norm["affected_artifacts"])
        shots = norm["affected_shots"] or _fallback_shots_from_finding(finding)
        item["affected_shots"].extend(shots)
        scoped = dict(norm)
        scoped["affected_shots"] = shots
        item["fingerprints"].extend(finding_fingerprints(ep, stage, dim, scoped))

    for item in grouped.values():
        artifacts = _unique(item["affected_artifacts"])
        shots = _unique(item["affected_shots"])
        scope = "；".join(_unique(item["scope"]))
        if shots and "定位镜头" not in scope:
            scope += "；定位镜头：" + "、".join(shots)
        tasks.append(
            task_from_spec(
                root,
                str(item["ep"]),
                find_stage(str(item["stage"])),
                reason="rerun",
                priority=len(tasks) + 1,
                cost_estimates=cost_estimates,
                max_retries=max_retries,
                rerun_scope=scope,
                affected_artifacts=artifacts,
                affected_shots=shots,
                fingerprints=_unique(item["fingerprints"]) or [finding_fingerprint(item["ep"], item["stage"], item["dim"])],
                coarse_fingerprints=[finding_fingerprint(item["ep"], item["stage"], item["dim"])],
            )
        )
    return dedupe_task_ids(tasks)


def report_active_fingerprints(report: Dict[str, Any], *, coarse: bool = False) -> Set[str]:
    """一份 consistency_findings 报告 → 当前仍存在的指纹集合。

    复检用：返工跑完后重算这份集合，done 任务的指纹若已不在其中 = 问题消失 → resolved；
    仍在 = 复发 → reopen。粒度与 tasks_from_consistency_findings 建的指纹一致。
    coarse=True 时丢镜头定位，只产 (集×阶段×维度) 粗指纹，供 --coarse 回退匹配。
    """
    if not isinstance(report, dict):
        return set()
    ep_default = str(report.get("episode") or "").strip()
    out: Set[str] = set()
    for item in report.get("auto_return_tasks") or []:
        if not isinstance(item, dict):
            continue
        ep_pair = _episode_from_item(item, ep_default)
        if ep_pair is None:
            continue
        stage = str(item.get("return_to_stage") or item.get("rerun_from") or "image")
        dims = [
            finding_dim_key({"dimension": d})
            for d in (_string_list(item.get("dimensions")) or [str(item.get("dim") or item.get("dimension") or "一致性")])
        ]
        raw_scope = {
            "affected_shots": _string_list(item.get("affected_shots")),
            "affected_artifacts": _string_list(item.get("affected_artifacts")),
            "loc": item.get("loc") or "",
        }
        for d in dims:
            if coarse:
                out.add(finding_fingerprint(ep_pair[1], stage, d))
            else:
                out.update(finding_fingerprints(ep_pair[1], stage, d, raw_scope))
    for finding in report.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        norm = normalize_finding(finding)
        if norm["severity"] not in {"block", "warn"}:
            continue
        ep_pair = _episode_from_item(finding, ep_default)
        if ep_pair is None:
            continue
        stage = norm["return_to_stage"] or "image"
        dim = finding_dim_key(finding)
        if coarse:
            out.add(finding_fingerprint(ep_pair[1], stage, dim))
        else:
            out.update(finding_fingerprints(ep_pair[1], stage, dim, finding))
    return out


def reconcile_resolved(
    queue: Dict[str, Any],
    active_fingerprints: Set[str],
    *,
    coarse_active: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """复检回写：用最新审查仍存在的指纹集合，把已 done 的返工任务判 resolved / reopen。

    - done 任务的指纹全部不在 active 集合 → 该问题已修复，标 resolved=true（保留历史，不静默覆盖）；
    - done 任务仍有指纹在 active 集合 → 修了没真消失，reopen（status→queued、resolved=false、留痕 reopened）。
    只动 done 任务；queued/running/failed 不碰（避免误改在途/未启动）。返回受影响计数。

    coarse_active 给定时启用粗粒度回退：精确指纹已全部消失、但该任务所属 (集×阶段×维度) 桶在最新
    findings 里仍有问题时，不判 resolved 而是 reopen（reopened_coarse）。这堵住「定位串大改→精确
    指纹对不上→已修问题被误判 resolved」的漏放；代价是同桶若有别的镜头未修，已修镜头也会被一起
    召回复核（宁可多复核、不漏放）。默认 None=关闭，行为与历史完全一致。
    """
    resolved = reopened = reopened_coarse = 0
    for task in queue.get("tasks", []):
        if str(task.get("status")) != "done":
            continue
        fps = set(task.get("finding_fingerprints") or [])
        if not fps:
            continue  # 无指纹（老任务/非一致性返工）：不参与复检
        still = fps & active_fingerprints
        history = task.setdefault("history", [])
        coarse_still: Set[str] = set()
        if not still and coarse_active is not None:
            coarse_still = set(task.get("coarse_fingerprints") or []) & coarse_active
        if still:
            task["status"] = "queued"
            task["attempts"] = 0
            task["resolved"] = False
            history.append({"ts": now_iso(), "action": "recheck:reopened", "fingerprints": sorted(still)})
            reopened += 1
        elif coarse_still:
            task["status"] = "queued"
            task["attempts"] = 0
            task["resolved"] = False
            history.append({"ts": now_iso(), "action": "recheck:reopened_coarse", "fingerprints": sorted(coarse_still)})
            reopened_coarse += 1
        else:
            task["resolved"] = True
            task["resolved_at"] = now_iso()
            history.append({"ts": now_iso(), "action": "recheck:resolved"})
            resolved += 1
    queue["recheck"] = {
        "resolved": resolved,
        "reopened": reopened,
        "reopened_coarse": reopened_coarse,
        "at": now_iso(),
    }
    return queue


def collect_active_fingerprints(
    root: str, episodes: Optional[Set[str]] = None, *, coarse: bool = False
) -> Set[str]:
    """扫 生产数据/ 下最新审查产物（consistency_findings_*.json + review_ui_findings_*.json）→
    当前仍存在的一致性问题指纹集合。复检的"现状"输入。coarse=True 产 (集×阶段×维度) 粗指纹。"""
    out: Set[str] = set()
    pdir = production_dir(root)
    for pattern in ("consistency_findings_*.json", "review_ui_findings_*.json", "gate_findings_*.json"):
        for path in glob.glob(os.path.join(pdir, pattern)):
            try:
                data = json.load(open(path, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            if episodes and str(data.get("episode") or "").strip() not in episodes:
                continue
            out |= report_active_fingerprints(data, coarse=coarse)
    return out


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
    # 指纹索引：同一一致性问题（同指纹）已被某任务跟踪 → 不再堆叠新任务。
    fp_index: Dict[str, int] = {}
    for i, t in enumerate(tasks):
        for fp in t.get("finding_fingerprints") or []:
            fp_index.setdefault(str(fp), i)
    for incoming in planned.get("tasks", []):
        task = deepcopy(incoming)
        tid = str(task.get("id") or "")
        inc_fps = [str(fp) for fp in (task.get("finding_fingerprints") or [])]
        match_i = next((fp_index[fp] for fp in inc_fps if fp in fp_index), None)
        if match_i is not None:
            # 同指纹问题已在队列：复发则 reopen 旧任务，未启动则刷新，在途则跳过——绝不堆叠重复任务。
            old = tasks[match_i]
            old_status = str(old.get("status") or "")
            old.setdefault("history", [])
            old["finding_fingerprints"] = sorted(set(old.get("finding_fingerprints") or []) | set(inc_fps))
            if old_status in {"done", "failed"}:
                old["status"] = "queued"
                old["attempts"] = 0
                old["resolved"] = False
                old["rerun_scope"] = task.get("rerun_scope") or old.get("rerun_scope", "")
                old["affected_shots"] = _unique(list(old.get("affected_shots") or []) + list(task.get("affected_shots") or []))
                old["history"].append({"ts": now_iso(), "action": "plan:reopen_recurring", "prev_status": old_status})
            elif old_status in REPLACEABLE_MERGE_STATUSES:
                old["history"].append({"ts": now_iso(), "action": "plan:refresh_same_fingerprint"})
            else:  # running/retry：同问题在途，跳过新计划
                old["history"].append({"ts": now_iso(), "action": "plan:skip_in_flight_duplicate"})
            for fp in inc_fps:
                fp_index.setdefault(fp, match_i)
            continue
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
                for fp in inc_fps:
                    fp_index.setdefault(fp, len(tasks) - 1)
            continue
        existing_ids.add(tid)
        tasks.append(task)
        for fp in inc_fps:
            fp_index.setdefault(fp, len(tasks) - 1)
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
    if ns.from_asset_impact:
        with open(ns.from_asset_impact, encoding="utf-8") as fh:
            impact_plan = json.load(fh)
        tasks = tasks_from_asset_impact(
            root,
            impact_plan,
            cost_estimates=estimates,
            max_retries=ns.max_retries,
            episodes=selected,
        )
    elif ns.from_consistency_findings:
        with open(ns.from_consistency_findings, encoding="utf-8") as fh:
            findings_report = json.load(fh)
        tasks = tasks_from_consistency_findings(
            root,
            findings_report,
            cost_estimates=estimates,
            max_retries=ns.max_retries,
            episodes=selected,
        )
    elif ns.rerun_from:
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


def cmd_recheck(ns: argparse.Namespace) -> int:
    root = ns.root.rstrip("/")
    queue = load_queue(root)
    episodes = parse_episode_selector(ns.episodes) if ns.episodes else None
    active = collect_active_fingerprints(root, episodes)
    coarse_active = collect_active_fingerprints(root, episodes, coarse=True) if getattr(ns, "coarse", False) else None
    reconcile_resolved(queue, active, coarse_active=coarse_active)
    info = queue.get("recheck", {})
    save_queue(root, queue)
    tail = f" reopened_coarse={info.get('reopened_coarse', 0)}" if coarse_active is not None else ""
    print(f"recheck: resolved={info.get('resolved', 0)} reopened={info.get('reopened', 0)}{tail}"
          f"（现存一致性问题指纹 {len(active)} 个）")
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
    plan.add_argument("--from-asset-impact",
                      help="读 n2d-image asset_impact.py --output-batch-tasks 的 JSON（kind=n2d_asset_rerun_plan），直接建受影响重跑任务")
    plan.add_argument("--from-consistency-findings",
                      help="读 n2d-review consistency_findings_*.json（kind=n2d_consistency_findings），直接建审查返工任务")
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

    recheck = sub.add_parser("recheck", help="复检：用最新审查产物的指纹，把已修复的返工任务标 resolved / 复发的 reopen")
    recheck.add_argument("root")
    recheck.add_argument("--episodes", help="只复检指定集，如 1-5,8 或 第1集,第2集")
    recheck.add_argument("--coarse", action="store_true",
                         help="粗粒度回退：精确指纹对不上但该(集×阶段×维度)桶仍有问题时不判 resolved 而 reopen，"
                              "堵定位串大改导致的漏放（代价：同桶未修镜头会把已修镜头一起召回复核）")
    recheck.set_defaults(func=cmd_recheck)
    return ap


def main(argv: List[str]) -> int:
    ns = parser().parse_args(argv)
    return ns.func(ns)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
