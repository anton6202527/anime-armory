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
import hashlib
import importlib.util
import json
import math
import os
import re
import socket
import sqlite3
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Set, Tuple, runtime_checkable

try:
    import fcntl  # POSIX 文件锁（mac/Linux）
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

SCRIPT_DIR = os.path.dirname(__file__)
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))
COMMON = os.path.join(REPO_SKILLS, "_lib")
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_contract import (  # noqa: E402  生产数据目录 / kind 单一真值源
    ASSET_RERUN_PLAN_KIND,
    BATCH_QUEUE_KIND,
    CONSISTENCY_FINDINGS_KIND,
    CONSISTENCY_LEDGER_KIND,
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
    is_progress_satisfied,
    normalize_episode as route_normalize_episode,
    parse_progress,
    stage_of,
)
try:  # noqa: E402  review done 只认 canonical acceptance contract；缺模块必须 fail-closed
    import acceptance_contract
except Exception:  # pragma: no cover - exercised via fail-closed helper
    acceptance_contract = None
try:  # noqa: E402  paid boundary receipts are producer-owned canonical evidence
    import paid_execution_contract
except Exception:  # pragma: no cover - production completion must fail closed
    paid_execution_contract = None

BATCH_KIND = BATCH_QUEUE_KIND
VERSION = 1
QUEUE_JSON = "batch_queue.json"
QUEUE_MD = "batch_queue.md"
QUEUE_LOCK = "batch_queue.lock"
COORDINATION_JSON = "coordination_backend.json"
JOB_RECEIPTS_JSONL = "job_receipts.jsonl"
JOB_RECONCILE_JSON = "job_reconcile.json"
JOB_RECONCILE_MD = "job_reconcile.md"
SQLITE_DOCTOR_JSON = "sqlite_doctor.json"
SQLITE_DOCTOR_MD = "sqlite_doctor.md"
DEAD_LETTER_JSON = "dead_letter_queue.json"
DEFAULT_LEASE_SECONDS = 1800  # 认领后租约时长；超时未 mark/续租 → 可被回收（断点恢复）
SQLITE_SCHEMA_VERSION = 1

DEFAULT_COST_ESTIMATES = {
    "script_stage1": {"amount": 0.2, "unit": "work_units"},
    "voice": {"amount": 1.0, "unit": "work_units"},
    "script_stage2": {"amount": 0.3, "unit": "work_units"},
    "image_prompt": {"amount": 0.2, "unit": "work_units"},
    "image": {"amount": 3.0, "unit": "work_units"},
    "video_prompt": {"amount": 0.2, "unit": "work_units"},
    "video": {"amount": 12.0, "unit": "work_units"},
    "compose": {"amount": 0.5, "unit": "work_units"},
    "review": {"amount": 0.5, "unit": "work_units"},
}

ACTIVE_STATUSES = {"queued", "running", "provider_pending", "retry_queued", "qa_blocked"}
AGENT_REQUIRED_STAGES = {"script_stage1"}
REPLACEABLE_MERGE_STATUSES = {"queued", "blocked_budget", "qa_blocked"}
BUDGET_FLEXIBLE_STATUSES = {"queued", "blocked_budget"}
BUDGET_IGNORED_STATUSES = {"cancelled", "blocked_agent"}
PRODUCTION_EXECUTION_STAGES = frozenset({"voice", "image", "video", "compose"})
COORDINATION_BACKENDS = {"local_file", "shared_fs", "sqlite", "redis", "db", "object_store"}
# 网络文件系统：SQLite WAL 在其上锁不可靠 → 多机并发指向 NFS 上的 DB 会静默损坏。
NETWORK_FS_TYPES = {"nfs", "nfs4", "cifs", "smbfs", "smb", "smb2", "afpfs", "ncpfs", "9p",
                    "lustre", "ceph", "gpfs", "glusterfs", "fuse.glusterfs", "fuse.sshfs", "fuse.cephfs"}


def _network_fs_type(path: str) -> str:
    """best-effort 判 path 所在挂载点是否网络文件系统，返回类型名（非网络/判不定→""）。

    仅 Linux /proc/mounts 可判（生产 farm 多是 Linux）；macOS 等无 /proc/mounts → 返回 ""（不误报），
    由调用方附「本机无法判定 FS 类型」提示。纯只读。"""
    try:
        target = os.path.realpath(path)
        best_mp, best_type = "", ""
        with open("/proc/mounts", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 3:
                    continue
                mp, fstype = parts[1], parts[2]
                if (target == mp or target.startswith(mp.rstrip("/") + "/")) and len(mp) >= len(best_mp):
                    best_mp, best_type = mp, fstype
        return best_type if best_type.lower() in NETWORK_FS_TYPES else ""
    except Exception:
        return ""


# ── 协调后端 adapter 接口 + 注册表（P2-1）────────────────────────────────────────
# 诚实边界（见 coordination_backend_status）：本机 queue.py 内置 local/shared-FS 文件锁 + lease
# + SQLite 事务后端。真·多机/私有算力池要靠外部协调后端（Redis/DB/对象存储）接管 claim/mark。
# 此前 redis/db/object_store 只能"声明但不激活"（declared_not_active）——是个死路。
# 这里把"一个协调后端要实现什么"收成一个**正式接口 + 注册表**，让外部后端从死路变成可插拔：
#   ops 侧实现下面 6 个方法的类，import queue 后 `queue.register_coordination_backend("redis", RedisBackend)`，
#   再设 `N2D_COORDINATION_BACKEND=redis`，claim/mark/reclaim/renew/load/sync 就会真走它，
#   coordination_backend_status 也会报 active 而非 declared_not_active。sqlite 是内置参考实现。
@runtime_checkable
class CoordinationBackend(Protocol):
    """队列协调后端契约：任何实现这 6 个方法的类都能被注册成 drop-in 多机协调后端。

    语义须与内置 SQLiteQueueBackend 一致：claim 原子认领并下租约；mark 写终态/重排；
    reclaim 回收过期租约的 running 任务；renew 心跳续租；load_queue/sync_from_queue 与 JSON
    可移植镜像对账（JSON 始终是可移植真值镜像，外部后端是协调真值）。
    """

    def load_queue(self) -> Dict[str, Any]: ...
    def sync_from_queue(self, queue: Dict[str, Any]) -> None: ...
    def claim(self, *, limit: Optional[int], worker: Optional[str], lease_seconds: int) -> List[Dict[str, Any]]: ...
    def claim_exact(self, *, task_id: str, expected_plan_digest: str, episode: str,
                    stage_key: str, worker: Optional[str], lease_seconds: int) -> List[Dict[str, Any]]: ...
    def mark(self, task_id_value: str, status: str, note: str = "", **kwargs: Any) -> Dict[str, Any]: ...
    def reclaim(self, *, worker: Optional[str] = None, force_worker: bool = False) -> List[Dict[str, Any]]: ...
    def renew(self, task_ids: Iterable[str], lease_seconds: int, worker: Optional[str] = None) -> int: ...


# backend 名 → 工厂 callable(root)->CoordinationBackend。sqlite 在类定义后注册（见下方）。
_COORDINATION_FACTORIES: Dict[str, "Callable[[str], CoordinationBackend]"] = {}


def register_coordination_backend(name: str, factory: "Callable[[str], CoordinationBackend]") -> None:
    """登记一个外部协调后端工厂，使其成为可激活的 drop-in（不改 queue.py 主体）。

    name 会并入 COORDINATION_BACKENDS（合法 backend 集），factory(root) 须返回符合
    CoordinationBackend 协议的实例。重复登记以最后一次为准（便于 ops 覆盖内置）。
    """
    key = str(name).strip().lower()
    if not key:
        raise ValueError("coordination backend name must be non-empty")
    COORDINATION_BACKENDS.add(key)
    _COORDINATION_FACTORIES[key] = factory


def coordination_backend_name(root: str) -> str:
    """解析当前生效的协调后端名（env > 配置 > 默认 local_file），非法值回落 local_file。"""
    cfg = load_coordination_config(root)
    backend = os.environ.get("N2D_COORDINATION_BACKEND", "").strip().lower()
    backend = backend or str(cfg.get("backend") or "").strip().lower() or "local_file"
    return backend if backend in COORDINATION_BACKENDS else "local_file"


def active_coordination_backend(root: str) -> "Optional[CoordinationBackend]":
    """返回当前生效协调后端的实例；文件型（local_file/shared_fs）或未注册工厂时返回 None。

    这是 claim/mark/reclaim/renew/load_queue/sync 的统一分发口：注册了工厂的后端（sqlite 内置、
    或 ops 注册的 redis/db）走外部协调，否则回退文件锁路径（None）。
    """
    factory = _COORDINATION_FACTORIES.get(coordination_backend_name(root))
    return factory(root) if factory is not None else None


def stable_hash(value: Any, *, length: int = 16) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


TASK_PLAN_FIELDS = (
    "idempotency_key", "episode", "stage_key", "command", "runner_command",
    "reason", "estimated_cost", "rerun_scope", "affected_artifacts",
    "affected_shots", "finding_fingerprints", "producer_manifest", "physical_clips",
)


def task_plan_projection(task: Mapping[str, Any]) -> Dict[str, Any]:
    """Immutable executable planning fields shared by probe, exact claim and runner."""
    return {key: task.get(key) for key in TASK_PLAN_FIELDS}


def task_plan_digest(task: Mapping[str, Any]) -> str:
    raw = json.dumps(
        task_plan_projection(task), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


_CLAIM_STOP_LOSS_MODULE: Any = None


def _claim_stop_loss_module() -> Any:
    """Lazy-load the independent stop-loss evaluator without importing governance.py.

    ``governance.py`` imports this queue module, so importing it here would form a cycle.
    Stop-loss itself has no queue dependency and is the narrow adapter needed at the
    claim critical section.
    """
    global _CLAIM_STOP_LOSS_MODULE
    if _CLAIM_STOP_LOSS_MODULE is None:
        path = Path(SCRIPT_DIR).parent.parent / "scripts" / "stop_loss.py"
        spec = importlib.util.spec_from_file_location("n2d_stop_loss_for_queue_claim", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load stop-loss evaluator: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CLAIM_STOP_LOSS_MODULE = module
    return _CLAIM_STOP_LOSS_MODULE


def _claim_max_dead_letters(root: str) -> int:
    """Read the one critical queue SLO used by governance (default remains zero)."""
    path = Path(production_dir(root)) / "production_slo.json"
    if not path.is_file():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"{path} must be an object")
    node = data.get("queue") if isinstance(data.get("queue"), Mapping) else {}
    return int(node.get("max_dead_letters", 0))


def critical_claim_interlock(root: str, queue: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """Evaluate live critical governance against the queue already inside its lock/txn.

    This intentionally mirrors only governance's *critical* sources: dead letters and
    live stop-loss metrics.  Retry-rate/age/stage-duration rows are warnings and do not
    halt claims.  Passing the in-memory queue avoids a stale second read and, for SQLite,
    avoids trying to open another connection while ``BEGIN IMMEDIATE`` is held.
    """
    violations: List[Dict[str, Any]] = []
    try:
        max_dead = _claim_max_dead_letters(root)
        dead = [
            task for task in queue.get("tasks", [])
            if isinstance(task, Mapping)
            and (task.get("dead_letter") is True or str(task.get("status") or "") == "failed")
        ]
        if len(dead) > max_dead:
            violations.append({
                "level": "critical",
                "kind": "dead_letters",
                "value": len(dead),
                "threshold": max_dead,
            })
        stop_payload = _claim_stop_loss_module().build_report(Path(root))
        for row in stop_payload.get("violations", []) or []:
            if isinstance(row, Mapping) and row.get("level") == "critical":
                violations.append({
                    "level": "critical",
                    "kind": "stop_loss",
                    "metric": row.get("metric"),
                    "value": row.get("value"),
                    "threshold": row.get("threshold"),
                    "action": row.get("action"),
                })
    except Exception as exc:
        # Governance evaluation is itself part of the paid-work safety boundary.
        violations.append({
            "level": "critical",
            "kind": "governance_evaluation_error",
            "error": f"{type(exc).__name__}: {exc}",
        })
    if not violations:
        return None
    return {
        "kind": "n2d_critical_governance_interlock",
        "status": "blocked",
        "violations": violations,
        "summary": {
            "tasks": len(queue.get("tasks", []) or []),
            "dead_letters": sum(
                1 for task in queue.get("tasks", []) or []
                if isinstance(task, Mapping)
                and (task.get("dead_letter") is True or str(task.get("status") or "") == "failed")
            ),
        },
    }


def enforce_claim_governance_interlock(root: str, queue: Mapping[str, Any]) -> None:
    issue = critical_claim_interlock(root, queue)
    if issue is None:
        return
    details = "; ".join(
        str(row.get("kind") or row.get("metric") or row)
        for row in issue.get("violations", [])[:4]
        if isinstance(row, Mapping)
    )
    raise RuntimeError(
        "critical production governance interlock" + (f": {details}" if details else "")
    )


def now_ts() -> float:
    return time.time()


def default_worker() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def lock_path(root: str) -> str:
    return os.path.join(production_dir(root), QUEUE_LOCK)


def coordination_config_path(root: str) -> str:
    return os.path.join(production_dir(root), COORDINATION_JSON)


def job_receipts_path(root: str) -> str:
    return os.path.join(production_dir(root), JOB_RECEIPTS_JSONL)


def job_reconcile_path(root: str) -> str:
    return os.path.join(production_dir(root), JOB_RECONCILE_JSON)


def sqlite_doctor_path(root: str) -> str:
    return os.path.join(production_dir(root), SQLITE_DOCTOR_JSON)


def sqlite_db_path(root: str) -> str:
    cfg = load_coordination_config(root)
    dsn = os.environ.get("N2D_COORDINATION_DSN") or str(cfg.get("dsn") or "")
    if dsn.startswith("sqlite:///"):
        raw = dsn[len("sqlite:///"):]
        return raw if raw.startswith("/") else os.path.join(root, raw)
    if dsn and "://" not in dsn:
        return dsn if os.path.isabs(dsn) else os.path.join(root, dsn)
    return os.path.join(production_dir(root), "batch_queue.sqlite3")


# 锁策略（F3 多机·2026-06-26）：
#   auto（默认）= 有 fcntl 用 flock（本地 FS 可靠、零行为变化）；无 fcntl 退 atomic。
#   atomic      = 强制 O_EXCL 锁文件 + 陈旧锁自动接管——**共享 FS 多机渲染农场**用这个（O_EXCL create
#                 在 NFSv3+ 原子，比 flock 跨 NFS 可靠）。env `N2D_QUEUE_LOCK=atomic` 开启。
#   诚实边界：这把锁只护「读队列→改→写」的临界区；真正的多机安全网是**每任务 lease + reclaim_expired +
#   heartbeat**（已有·一台机器死了它的任务自动回收）。高并发/强一致仍建议接 Redis/DB 协调后端（见 SKILL）。
QUEUE_LOCK_TTL = float(os.environ.get("N2D_QUEUE_LOCK_TTL", "120") or "120")


def load_coordination_config(root: str) -> Dict[str, Any]:
    path = coordination_config_path(root)
    if not os.path.isfile(path):
        return {}
    try:
        data = json.load(open(path, encoding="utf-8"))
        return data if isinstance(data, dict) else {"backend": "local_file", "config_error": "config must be object"}
    except Exception as exc:
        return {"backend": "local_file", "config_error": str(exc)}


def _queue_lock_mode() -> str:
    mode = os.environ.get("N2D_QUEUE_LOCK", "auto").strip().lower()
    if mode not in {"auto", "flock", "atomic"}:
        mode = "auto"
    if mode == "auto":
        return "flock" if fcntl is not None else "atomic"
    if mode == "flock" and fcntl is None:
        return "atomic"
    return mode


def coordination_backend_status(root: str) -> Dict[str, Any]:
    """Describe the queue coordination backend honestly.

    queue.py implements local/shared-filesystem locking.  External backends can
    be declared for an ops wrapper, but are reported as declared_not_active
    until an actual adapter owns claim/mark semantics.
    """
    cfg = load_coordination_config(root)
    backend = os.environ.get("N2D_COORDINATION_BACKEND", "").strip().lower()
    backend = backend or str(cfg.get("backend") or "").strip().lower() or "local_file"
    if backend not in COORDINATION_BACKENDS:
        backend = "local_file"
    lock_mode = _queue_lock_mode()
    dsn = os.environ.get("N2D_COORDINATION_DSN") or str(cfg.get("dsn") or "")
    status: Dict[str, Any] = {
        "backend": backend,
        "status": "ok",
        "lock_mode": lock_mode,
        "lock_ttl_sec": QUEUE_LOCK_TTL,
        "config_path": coordination_config_path(root),
        "external_adapter": False,
        "note": "local queue coordination; leases and reclaim provide crash recovery",
    }
    if backend == "shared_fs":
        status["note"] = "shared filesystem coordination; use N2D_QUEUE_LOCK=atomic for multi-machine workers"
        if lock_mode != "atomic":
            status["status"] = "warn"
            status["warning"] = "shared_fs should set N2D_QUEUE_LOCK=atomic"
    elif backend == "sqlite":
        db = sqlite_db_path(root)
        netfs = _network_fs_type(db)
        st = "ok"
        note = ("SQLite coordination active for claim/mark/reclaim/heartbeat; JSON ledger remains the portable mirror。"
                "SQLite 是单机/本地盘参考实现（claim 走全队列 load-rewrite，O(N)/次）；多机 farm/大队列请用 redis/db 后端。")
        if netfs:
            st = "warn"
            note = (f"⚠ SQLite DB 在网络文件系统({netfs})上：WAL 锁在 NFS/CIFS 上不可靠 → 多机并发会**静默损坏**。"
                    "把 DB 放本地盘，或多机改用 redis/db 后端。") + note
        else:
            note += "（本机无法判定 DB 所在 FS 类型；若在 NFS/CIFS 上，WAL 锁不可靠，勿多机共用。）"
        status.update({
            "status": st,
            "db_path": db,
            "network_fs": netfs or None,
            "external_adapter": True,
            "note": note,
        })
    elif backend in {"redis", "db", "object_store"}:
        if backend in _COORDINATION_FACTORIES:
            # ops 已通过 register_coordination_backend 注册了 drop-in adapter → 真激活。
            status.update({
                "status": "ok",
                "dsn_present": bool(dsn),
                "external_adapter": True,
                "note": f"{backend} coordination adapter registered and active for claim/mark/reclaim/renew; JSON ledger remains the portable mirror.",
            })
        else:
            status.update({
                "status": "declared_not_active",
                "dsn_present": bool(dsn),
                "note": f"{backend} coordination declared, but no adapter registered; call queue.register_coordination_backend('{backend}', Factory) implementing the CoordinationBackend protocol, or use shared_fs atomic mode.",
            })
    if cfg.get("config_error"):
        status["status"] = "warn"
        status["warning"] = f"invalid coordination config: {cfg['config_error']}"
    return status


@contextlib.contextmanager
def _flock_lock(path: str, timeout: float, poll: float):
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


@contextlib.contextmanager
def _atomic_file_lock(path: str, timeout: float, poll: float, ttl: float):
    """O_EXCL 锁文件 + 陈旧锁自动接管（治原 fallback 的「持锁机器死了→永久死锁」缺陷）。

    持锁者把 `hostname:pid:ts` 写进锁文件；竞争者发现锁文件 mtime 超 ttl（持锁者多半已死）就用
    os.rename 原子抢占（rename 同一源只有一个赢，输者重试 O_EXCL create）。O_EXCL create 在 NFSv3+
    原子 → 比 flock 跨 NFS 可靠，适合共享 FS 多机。"""
    deadline = time.time() + timeout
    holder = f"{default_worker()}:{int(now_ts())}"
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o644)
            with contextlib.suppress(OSError):
                os.write(fd, holder.encode("utf-8"))
            break
        except FileExistsError:
            stolen = False
            try:
                if time.time() - os.path.getmtime(path) > ttl:
                    stale = f"{path}.stale.{os.getpid()}.{int(time.time()*1000)}"
                    os.rename(path, stale)            # 原子抢占：同源只有一个 rename 成功
                    with contextlib.suppress(OSError):
                        os.unlink(stale)
                    stolen = True
            except OSError:
                pass                                  # 别人已抢/已删 → 继续自旋重试 create
            if not stolen and time.time() >= deadline:
                raise TimeoutError(f"queue lock timeout ({timeout}s): {path}")
            if not stolen:
                time.sleep(poll)
    try:
        yield
    finally:
        os.close(fd)
        with contextlib.suppress(OSError):
            os.unlink(path)


@contextlib.contextmanager
def queue_lock(root: str, *, timeout: float = 30.0, poll: float = 0.1):
    """单机多 worker / 多机互斥：所有"读队列→改→写"必须在此锁内做，避免双认领/互相覆盖。

    锁策略见 `_queue_lock_mode`（默认 flock·零行为变化；`N2D_QUEUE_LOCK=atomic` 走共享 FS 多机安全的
    O_EXCL+陈旧锁接管）。真正的多机断点恢复靠每任务 lease + reclaim_expired（已有）。
    """
    os.makedirs(production_dir(root), exist_ok=True)
    path = lock_path(root)
    if _queue_lock_mode() == "flock":
        with _flock_lock(path, timeout, poll):
            yield
    else:
        with _atomic_file_lock(path, timeout, poll, QUEUE_LOCK_TTL):
            yield


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


def task_idempotency_key(
    ep: str,
    stage_key: str,
    reason: str,
    *,
    rerun_scope: Optional[str] = None,
    affected_artifacts: Optional[Sequence[str]] = None,
    affected_shots: Optional[Sequence[str]] = None,
    fingerprints: Optional[Sequence[str]] = None,
) -> str:
    return stable_hash({
        "episode": normalize_episode(ep),
        "stage_key": stage_key,
        "reason": reason,
        "rerun_scope": rerun_scope or "",
        "affected_artifacts": sorted(str(item) for item in (affected_artifacts or [])),
        "affected_shots": sorted(str(item) for item in (affected_shots or [])),
        "finding_fingerprints": sorted(str(item) for item in (fingerprints or [])),
    })


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
    idempotency_key = task_idempotency_key(
        ep,
        stage_key,
        reason,
        rerun_scope=rerun_scope,
        affected_artifacts=affected_artifacts,
        affected_shots=affected_shots,
        fingerprints=fingerprints,
    )
    task = {
        "id": task_id(ep, stage_key, reason),
        "idempotency_key": idempotency_key,
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
    if stage_key in AGENT_REQUIRED_STAGES:
        note = (
            f"{stage_key} is an agent creative stage, not a batch shell wrapper; "
            f"run `{command}` manually, then re-plan deterministic downstream stages."
        )
        task.update({
            "status": "blocked_agent",
            "runner_mode": "agent_required",
            "agent_command": command,
            "last_note": note,
        })
        task.setdefault("history", []).append({"ts": now_iso(), "action": "blocked_agent", "note": note})
    return task


def image_physical_shots(root: str, episode: str) -> List[str]:
    """Resolve the whole-episode image scope from the producer-owned prompt pack."""
    prompt = Path(root) / "出图" / normalize_episode(episode) / "prompt" / "01_分镜出图.md"
    try:
        text = prompt.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    shots: List[str] = []
    for match in re.finditer(
        r"^##\s+(?:(?:Clip)[_\s-]*([0-9０-９]+)|镜头\s*([0-9０-９]+))[^\n]*$",
        text,
        re.MULTILINE,
    ):
        raw = (match.group(1) or match.group(2) or "").translate(
            str.maketrans("０１２３４５６７８９", "0123456789")
        )
        if raw:
            shots.append(f"Clip_{int(raw):02d}")
    return list(dict.fromkeys(shots))


def prepared_video_bindings(root: str, episode: str) -> List[Dict[str, str]]:
    """Resolve one executable task per physical clip from prepared producer manifests.

    Newer explicit manifests win when a clip appears in more than one historical batch.  The
    manifest fingerprint is still recomputed by the runner before authorization/submit, so this
    selection cannot make stale inputs executable.
    """
    project = Path(root).expanduser().resolve()
    ep = normalize_episode(episode)
    candidates = sorted(
        (project / PRODUCTION_DIR).glob(f"video_batch_{ep}_*.json"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    by_clip: Dict[str, Dict[str, str]] = {}
    for manifest_path in candidates:
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if normalize_episode(str(payload.get("episode") or "")) != ep:
            continue
        rel = manifest_path.relative_to(project).as_posix()
        for item in payload.get("items") or []:
            if not isinstance(item, Mapping):
                continue
            clip = str(item.get("clip") or "").strip()
            target = str(item.get("target") or "").strip()
            if not clip or not target or clip in by_clip:
                continue
            output = project / "出视频" / ep / "视频" / target
            submit_id = str(item.get("submit_id") or "").strip()
            item_status = str(item.get("status") or "").strip().lower()
            # Keep a submitted request routable after a crash even if download already landed;
            # it may still need QC/receipt/spend finalization.  Accepted/user-provided outputs do
            # not create another paid task.
            if output.is_file() and (not submit_id or item_status == "accepted"):
                continue
            by_clip[clip] = {"clip": clip, "producer_manifest": rel}
    return [by_clip[key] for key in sorted(by_clip)]


def bind_video_task(task: Dict[str, Any], root: str, binding: Mapping[str, str]) -> Dict[str, Any]:
    clip = str(binding.get("clip") or "").strip()
    manifest = str(binding.get("producer_manifest") or "").strip()
    if not clip or not manifest:
        return task
    # One durable queue identity per physical provider request.  The generic stage task id is
    # intentionally expanded here; otherwise every clip in the manifest would alias the same
    # queue row even though their idempotency keys and provider submit ids differ.
    task["id"] = f"{task.get('id')}-{stable_hash(clip, length=8)}"
    task["producer_manifest"] = manifest
    task["physical_clips"] = [clip]
    task["affected_shots"] = [clip]
    task["runner_command"] = (
        "python3 skills/n2d/n2d-video/scripts/video_runner.py execute "
        f"{shlex_quote(root)} {shlex_quote(str(Path(root) / manifest))} --clip {shlex_quote(clip)}"
    )
    return task


def shlex_quote(value: str) -> str:
    """Tiny local quote helper without making queue execution shell-dependent."""
    import shlex
    return shlex.quote(str(value))


def route_tasks(
    root: str,
    *,
    episodes: Optional[Set[str]],
    stage_filters: Optional[Set[str]],
    cost_estimates: Dict[str, Dict[str, Any]],
    max_retries: int,
    strategy: str = "default",
) -> List[Dict[str, Any]]:
    header, rows = parse_progress(root)
    tasks: List[Dict[str, Any]] = []
    
    # Check if Episode 1 Image is done for "front-light" strategy
    ep1_image_done = False
    if strategy == "front-light":
        for row in rows:
            if episode_num(row.get("_ep") or row.get("集", "")) == 1:
                ep1_image_done = is_progress_satisfied(row, header, "出图")
                break

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
            owner = route.get("skill")
            spec = next((s for s in stage_specs() if s.get("owner") == owner), None)
        if not spec or not stage_matches(spec, stage_filters):
            continue
            
        # Optimization Point 4: Async Batch Gate (front-light strategy)
        stage_key = str(spec["key"])
        if strategy == "front-light":
            # If Ep 1 image isn't done, defer image, video, compose for other episodes
            if not ep1_image_done and episode_num(ep) > 1 and stage_key in ("image_prompt", "image", "video_prompt", "video", "compose"):
                continue

        if stage_key == "video":
            bindings = prepared_video_bindings(root, ep)
            if bindings:
                for binding in bindings:
                    task = task_from_spec(
                        root,
                        ep,
                        spec,
                        reason="progress",
                        priority=len(tasks) + 1,
                        cost_estimates=cost_estimates,
                        max_retries=max_retries,
                        affected_shots=[binding["clip"]],
                    )
                    tasks.append(bind_video_task(task, root, binding))
                continue
        affected_shots = image_physical_shots(root, ep) if stage_key == "image" else []
        tasks.append(
            task_from_spec(
                root,
                ep,
                spec,
                reason="progress",
                priority=len(tasks) + 1,
                cost_estimates=cost_estimates,
                max_retries=max_retries,
                affected_shots=affected_shots,
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


def tasks_from_production_events(
    root: str,
    *,
    cost_estimates: Dict[str, Dict[str, Any]],
    max_retries: int,
    episodes: Optional[Set[str]] = None,
    events_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """production_events.jsonl 中「未被后续 pass 承接」的 generation/redraw fail → 重试任务。

    治 G10：手动/外部生成失败（如 Dreamina 超时）只留痕不承接、重试靠人。本入口按
    (episode, stage, asset) 取**最后一条**生成事件——仍是 fail 才入队；后来有 pass 记录
    视为已恢复不再重排。幂等键含失败事件 ts：同一次失败重复 plan 不重复入队，
    新一次失败会生成新任务。
    """
    path = events_path or os.path.join(root, "生产数据", "production_events.jsonl")
    if not os.path.isfile(path):
        return []
    latest: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        stage = str(event.get("stage") or "").strip()
        if stage not in {"image", "video"}:
            continue
        ep_raw = str(event.get("episode") or "").strip()
        if not ep_raw:
            continue
        generation = event.get("generation") if isinstance(event.get("generation"), dict) else {}
        asset = str(generation.get("asset") or event.get("asset") or "").strip()
        if not asset:
            continue
        latest[(normalize_episode(ep_raw), stage, asset)] = event
    tasks: List[Dict[str, Any]] = []
    for (ep, stage, asset), event in sorted(latest.items()):
        generation = event.get("generation") if isinstance(event.get("generation"), dict) else {}
        status = str(generation.get("status") or event.get("status") or "").strip().lower()
        if status not in {"fail", "failed", "error", "timeout"}:
            continue
        if episodes and ep not in episodes and str(event.get("episode") or "").strip() not in episodes:
            continue
        spec = find_stage(stage)
        ts = str(event.get("ts") or "")
        tasks.append(
            task_from_spec(
                root,
                ep,
                spec,
                reason="generation_fail_retry",
                priority=len(tasks) + 1,
                cost_estimates=cost_estimates,
                max_retries=max_retries,
                rerun_scope=f"生成失败未承接自动重试：{asset}（{status} @ {ts or 'unknown'}）",
                affected_artifacts=[asset],
                fingerprints=[f"{ep}|{stage}|{asset}|{ts}"],
            )
        )
    return dedupe_task_ids(tasks)


def tasks_from_shooting_schedule(
    root: str,
    schedule: Dict[str, Any],
    *,
    cost_estimates: Dict[str, Dict[str, Any]],
    max_retries: int,
    episodes: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """Convert P-3 ai_shooting_schedule / batch seed into executable queue tasks."""
    if not isinstance(schedule, dict):
        raise ValueError("not a shooting schedule payload")
    kind = str(schedule.get("kind") or "")
    if kind not in {"n2d_ai_shooting_schedule", "n2d_ai_shooting_schedule_batch_seed"}:
        raise ValueError("not an n2d ai shooting schedule or batch seed")
    default_ep = str(schedule.get("episode") or "").strip()
    source = str(schedule.get("source_schedule") or "脚本/<集>/ai_shooting_schedule.json")
    raw_items = schedule.get("batch_tasks") if kind.endswith("batch_seed") else schedule.get("tasks")
    tasks: List[Dict[str, Any]] = []
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        ep_pair = _episode_from_item(item, default_ep)
        if ep_pair is None:
            continue
        ep_raw, ep = ep_pair
        if not _episode_selected(ep_raw, ep, episodes):
            continue
        cid = str(item.get("clip_id") or item.get("shot") or "").strip()
        if not cid:
            continue
        stage_keys = [str(item.get("stage_key") or "").strip()]
        if not stage_keys[0]:
            stage_keys = ["image", "video"]
        for stage_key in stage_keys:
            spec = find_stage(stage_key)
            scope = str(item.get("rerun_scope") or f"AI shooting schedule {ep} {cid} {stage_key}").strip()
            artifacts = _string_list(item.get("affected_artifacts"))
            shots = _string_list(item.get("affected_shots")) or [cid]
            task = task_from_spec(
                root,
                ep,
                spec,
                reason="shooting_schedule",
                priority=len(tasks) + 1,
                cost_estimates=cost_estimates,
                max_retries=max_retries,
                rerun_scope=scope,
                affected_artifacts=artifacts,
                affected_shots=shots,
            )
            if stage_key == "video":
                bindings = {
                    row["clip"]: row for row in prepared_video_bindings(root, ep)
                }
                if len(shots) == 1 and shots[0] in bindings:
                    bind_video_task(task, root, bindings[shots[0]])
            task["schedule_bucket"] = item.get("schedule_bucket") or ""
            task["risk_tier"] = item.get("risk_tier") or item.get("priority") or ""
            task["source_schedule"] = source
            task["source_schedule_order"] = item.get("source_schedule_order") or item.get("production_order") or ""
            tasks.append(task)
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
    m = re.search(r"(?:Clip|clip|镜头)[_\s-]?(\d+)", loc)
    if m:
        return [f"Clip_{int(m.group(1)):02d}"]
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


LEDGER_TASK_SEVERITIES = {"block", "high"}


def _ledger_root_severity(cause: Dict[str, Any]) -> str:
    return str(cause.get("severity") or cause.get("overall") or cause.get("sev") or "").strip().lower()


def _ledger_root_stage(cause: Dict[str, Any]) -> str:
    for key in ("suggested_return_to_stage", "return_to_stage", "rerun_from"):
        value = str(cause.get(key) or "").strip()
        if value:
            return value
    for symptom in cause.get("symptoms") or []:
        if isinstance(symptom, dict):
            value = str(symptom.get("return_to_stage") or symptom.get("rerun_from") or "").strip()
            if value:
                return value
    return "image"


def _ledger_root_dimensions(cause: Dict[str, Any]) -> List[str]:
    dims = _string_list(cause.get("dimensions"))
    if not dims:
        dims = _string_list(cause.get("dim_keys"))
    if not dims:
        dim = str(cause.get("dimension") or cause.get("dim") or "").strip()
        if dim:
            dims = [dim]
    for symptom in cause.get("symptoms") or []:
        if not isinstance(symptom, dict):
            continue
        dim = finding_dim_key(symptom)
        if dim:
            dims.append(dim)
    return _unique(dims or ["一致性"])


def _ledger_root_shots(cause: Dict[str, Any]) -> List[str]:
    shots = _string_list(cause.get("affected_shots"))
    for symptom in cause.get("symptoms") or []:
        if isinstance(symptom, dict):
            shots.extend(_fallback_shots_from_finding(symptom))
    return _unique(shots)


def _ledger_root_artifacts(cause: Dict[str, Any]) -> List[str]:
    artifacts = _string_list(cause.get("affected_artifacts"))
    artifacts.extend(_string_list(cause.get("sources")))
    for symptom in cause.get("symptoms") or []:
        if not isinstance(symptom, dict):
            continue
        artifacts.extend(_string_list(symptom.get("affected_artifacts")))
        loc = str(symptom.get("loc") or "").strip()
        if "/" in loc or "." in loc:
            artifacts.append(loc)
        source = symptom.get("source")
        if isinstance(source, str) and source.strip():
            artifacts.append(source)
    return _unique(artifacts)


def _ledger_root_scope(cause: Dict[str, Any], dims: Sequence[str], shots: Sequence[str]) -> str:
    parts: List[str] = []
    anchor = str(cause.get("anchor") or cause.get("entity") or "").strip()
    if anchor:
        parts.append(f"根因锚点：{anchor}")
    if dims:
        parts.append("维度：" + "、".join(_unique(dims)))
    message = str(cause.get("message") or cause.get("summary") or "").strip()
    if message:
        parts.append(message)
    for symptom in cause.get("symptoms") or []:
        if not isinstance(symptom, dict):
            continue
        msg = str(symptom.get("text") or symptom.get("message") or symptom.get("msg") or "").strip()
        if msg:
            parts.append(msg)
    if shots:
        parts.append("定位镜头：" + "、".join(shots))
    return "；".join(_unique(parts))


def _ledger_fingerprints(ep: str, stage: str, dims: Sequence[str], cause: Dict[str, Any],
                         *, coarse: bool = False) -> List[str]:
    anchor = str(cause.get("anchor") or cause.get("entity") or "").strip()
    shots = _ledger_root_shots(cause)
    raw_scope = {"affected_shots": shots, "loc": anchor}
    out: List[str] = []
    for dim in dims:
        if coarse:
            out.append(finding_fingerprint(ep, stage, dim))
        else:
            out.extend(finding_fingerprints(ep, stage, dim, raw_scope))
    return _unique(out)


def tasks_from_consistency_ledger(
    root: str,
    ledger: Dict[str, Any],
    *,
    cost_estimates: Dict[str, Dict[str, Any]],
    max_retries: int,
    episodes: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """读 consistency_ledger root_causes → 返工队列任务。

    ledger 是验收唯一交付面；这里消费根因而非零散 symptoms，避免同一角色/资产根因被拆成多条
    互相冲突的返工。只把 block/high 根因入队；warn 仍留作人工/后续观察。
    """
    if not isinstance(ledger, dict) or ledger.get("kind") != CONSISTENCY_LEDGER_KIND:
        raise ValueError(f"not a consistency ledger (expect kind={CONSISTENCY_LEDGER_KIND})")
    default_episode = str(ledger.get("episode") or "").strip()
    tasks: List[Dict[str, Any]] = []
    for cause in ledger.get("root_causes") or []:
        if not isinstance(cause, dict):
            continue
        if _ledger_root_severity(cause) not in LEDGER_TASK_SEVERITIES:
            continue
        ep_pair = _episode_from_item(cause, default_episode)
        if ep_pair is None:
            continue
        ep_raw, ep = ep_pair
        if not _episode_selected(ep_raw, ep, episodes):
            continue
        stage = _ledger_root_stage(cause)
        try:
            spec = find_stage(stage)
        except ValueError:
            stage = "image"
            spec = find_stage(stage)
        dims = _ledger_root_dimensions(cause)
        shots = _ledger_root_shots(cause)
        artifacts = _ledger_root_artifacts(cause)
        tasks.append(
            task_from_spec(
                root,
                ep,
                spec,
                reason="rerun",
                priority=len(tasks) + 1,
                cost_estimates=cost_estimates,
                max_retries=max_retries,
                rerun_scope=_ledger_root_scope(cause, dims, shots),
                affected_artifacts=artifacts,
                affected_shots=shots,
                fingerprints=_ledger_fingerprints(ep, stage, dims, cause),
                coarse_fingerprints=_ledger_fingerprints(ep, stage, dims, cause, coarse=True),
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


def ledger_active_fingerprints(ledger: Dict[str, Any], *, coarse: bool = False) -> Set[str]:
    if not isinstance(ledger, dict):
        return set()
    ep_default = str(ledger.get("episode") or "").strip()
    out: Set[str] = set()
    for cause in ledger.get("root_causes") or []:
        if not isinstance(cause, dict):
            continue
        if _ledger_root_severity(cause) not in LEDGER_TASK_SEVERITIES:
            continue
        ep_pair = _episode_from_item(cause, ep_default)
        if ep_pair is None:
            continue
        stage = _ledger_root_stage(cause)
        dims = _ledger_root_dimensions(cause)
        out.update(_ledger_fingerprints(ep_pair[1], stage, dims, cause, coarse=coarse))
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
    for pattern in ("consistency_findings_*.json", "review_ui_findings_*.json", "gate_findings_*.json", "consistency_ledger_*.json"):
        for path in glob.glob(os.path.join(pdir, pattern)):
            try:
                data = json.load(open(path, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            if episodes and str(data.get("episode") or "").strip() not in episodes:
                continue
            if data.get("kind") == CONSISTENCY_LEDGER_KIND:
                out |= ledger_active_fingerprints(data, coarse=coarse)
            else:
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
    # 与 reapply_ledger_budget 同序（按 priority 贪心）：旧版按插入序裁剪，首次 plan 与
    # 后续 merge 可能 block 不同任务——预算不够时该保高优先级任务，且两条路径结论必须一致。
    for task in sorted(tasks, key=lambda item: int(item.get("priority", 999999))):
        if str(task.get("status") or "queued") in BUDGET_IGNORED_STATUSES:
            continue
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


def _task_estimated_cost(task: Mapping[str, Any]) -> Tuple[Optional[float], str]:
    estimate = task.get("estimated_cost") if isinstance(task.get("estimated_cost"), Mapping) else {}
    try:
        amount = float(estimate.get("amount"))
    except (TypeError, ValueError):
        return None, str(estimate.get("unit") or "").strip()
    if not math.isfinite(amount) or amount < 0:
        return None, str(estimate.get("unit") or "").strip()
    return amount, str(estimate.get("unit") or "").strip()


def _runtime_budget_totals(queue: Mapping[str, Any]) -> Tuple[float, float]:
    reserved = 0.0
    settled = 0.0
    for task in queue.get("tasks", []):
        if not isinstance(task, Mapping):
            continue
        reservation = task.get("budget_reservation")
        if isinstance(reservation, Mapping) and reservation.get("status") == "reserved":
            try:
                reserved += float(reservation.get("amount") or 0.0)
            except (TypeError, ValueError):
                pass
        for charge in task.get("budget_charges", []) or []:
            if not isinstance(charge, Mapping) or charge.get("status") != "settled":
                continue
            try:
                settled += float(charge.get("amount") or 0.0)
            except (TypeError, ValueError):
                pass
    return round(reserved, 6), round(settled, 6)


def refresh_runtime_budget(queue: Dict[str, Any]) -> Dict[str, Any]:
    budget = queue.get("budget") if isinstance(queue.get("budget"), dict) else {}
    reserved, settled = _runtime_budget_totals(queue)
    limit = _budget_limit(budget.get("limit"))
    unit = _budget_unit(budget.get("unit"))
    available = None if limit is None else round(limit - reserved - settled, 6)
    budget.update({
        "runtime_reserved_total": reserved,
        "runtime_settled_total": settled,
        "runtime_available": available,
        "runtime_unit": unit or str(budget.get("unit") or "mixed"),
        "runtime_status": "overrun" if available is not None and available < -1e-9 else "ok",
        "runtime_updated_at": now_iso(),
    })
    queue["budget"] = budget
    return budget


def reserve_task_budget(
    queue: Dict[str, Any],
    task: Dict[str, Any],
    *,
    worker: Optional[str],
    attempt: int,
) -> Optional[str]:
    """Reserve one production attempt inside the same claim critical section/transaction."""
    if str(task.get("stage_key") or "") not in PRODUCTION_EXECUTION_STAGES:
        return None
    amount, unit = _task_estimated_cost(task)
    if amount is None or not unit:
        return "production task estimated_cost is missing/invalid"
    budget = queue.get("budget") if isinstance(queue.get("budget"), dict) else {}
    limit = _budget_limit(budget.get("limit"))
    cap_unit = _budget_unit(budget.get("unit"))
    if limit is not None and cap_unit is None:
        return "runtime budget has a finite limit but mixed/missing unit; cannot reserve safely"
    if cap_unit and cap_unit != unit:
        return f"estimate unit {unit} != runtime budget unit {cap_unit}"

    # A queued task should not retain a reservation. Release a stale same-task hold before
    # checking capacity; active running holds of other workers remain counted.
    previous = task.get("budget_reservation")
    if isinstance(previous, dict) and previous.get("status") == "reserved":
        previous["status"] = "released"
        previous["released_at"] = now_iso()
        previous["release_reason"] = "stale_before_claim"
    reserved, settled = _runtime_budget_totals(queue)
    if limit is not None and settled + reserved + amount > limit + 1e-9:
        refresh_runtime_budget(queue)
        return (
            f"runtime budget cap {limit} {cap_unit} exceeded: "
            f"settled={settled} reserved={reserved} requested={amount}"
        )
    task["budget_reservation"] = {
        "status": "reserved",
        "amount": amount,
        "unit": unit,
        "attempt": int(attempt),
        "worker": worker or "",
        "reserved_at": now_iso(),
    }
    task.setdefault("history", []).append({
        "ts": now_iso(),
        "action": "budget:reserve",
        "amount": amount,
        "unit": unit,
        "attempt": int(attempt),
        "worker": worker or "",
    })
    refresh_runtime_budget(queue)
    return None


def release_task_budget(queue: Dict[str, Any], task: Dict[str, Any], reason: str) -> None:
    reservation = task.get("budget_reservation")
    if not isinstance(reservation, dict) or reservation.get("status") != "reserved":
        refresh_runtime_budget(queue)
        return
    reservation["status"] = "released"
    reservation["released_at"] = now_iso()
    reservation["release_reason"] = str(reason)
    task.setdefault("history", []).append({
        "ts": now_iso(),
        "action": "budget:release",
        "amount": reservation.get("amount"),
        "unit": reservation.get("unit"),
        "attempt": reservation.get("attempt"),
        "reason": str(reason),
    })
    refresh_runtime_budget(queue)


def _reported_actual_cost(task: Mapping[str, Any], runner: Optional[Mapping[str, Any]]) -> Tuple[Optional[float], str, str]:
    candidates = []
    if isinstance(runner, Mapping):
        candidates.extend([runner.get("actual_cost"), runner.get("cost")])
    candidates.append(task.get("actual_cost"))
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        try:
            amount = float(candidate.get("amount"))
        except (TypeError, ValueError):
            continue
        unit = str(candidate.get("unit") or candidate.get("currency") or "").strip()
        if math.isfinite(amount) and amount >= 0 and unit:
            return amount, unit, "reported_actual"
    return None, "", ""


def settle_task_budget(
    queue: Dict[str, Any],
    task: Dict[str, Any],
    runner: Optional[Mapping[str, Any]],
) -> Optional[str]:
    """Settle a successful production attempt, preferring reported actual cost.

    The reservation is always converted into an immutable charge. If reported actual cost is
    malformed, changes currency, exceeds the task approval ceiling, or pushes the runtime cap
    over limit, settlement is recorded conservatively and an issue keeps the task out of done.
    """
    if str(task.get("stage_key") or "") not in PRODUCTION_EXECUTION_STAGES:
        return None
    reservation = task.get("budget_reservation")
    if not isinstance(reservation, dict) or reservation.get("status") != "reserved":
        return "production task missing active atomic budget reservation"
    reserved_amount = float(reservation.get("amount") or 0.0)
    reserved_unit = str(reservation.get("unit") or "")
    actual_amount, actual_unit, source = _reported_actual_cost(task, runner)
    issue = ""
    if actual_amount is None:
        actual_amount, actual_unit, source = reserved_amount, reserved_unit, "estimate_fallback"
    elif actual_unit != reserved_unit:
        issue = f"actual cost unit {actual_unit} != reserved unit {reserved_unit}"
        actual_amount, actual_unit, source = reserved_amount, reserved_unit, "estimate_fallback_unit_mismatch"

    authorization = runner.get("authorization") if isinstance(runner, Mapping) else None
    ceiling = authorization.get("ceiling") if isinstance(authorization, Mapping) else None
    if isinstance(ceiling, Mapping):
        try:
            ceiling_amount = float(ceiling.get("amount"))
        except (TypeError, ValueError):
            ceiling_amount = -1.0
        ceiling_unit = str(ceiling.get("currency") or "")
        if ceiling_unit != actual_unit or ceiling_amount < actual_amount:
            issue = issue or (
                f"actual cost {actual_amount} {actual_unit} exceeds/mismatches authorization ceiling "
                f"{ceiling_amount} {ceiling_unit}"
            )

    charge_id = f"{task.get('id')}:{reservation.get('attempt')}"
    charges = task.setdefault("budget_charges", [])
    if not any(isinstance(row, Mapping) and row.get("charge_id") == charge_id for row in charges):
        charges.append({
            "charge_id": charge_id,
            "status": "settled",
            "amount": actual_amount,
            "unit": actual_unit,
            "source": source,
            "attempt": reservation.get("attempt"),
            "worker": reservation.get("worker"),
            "settled_at": now_iso(),
        })
    reservation["status"] = "settled"
    reservation["settled_at"] = now_iso()
    reservation["actual_amount"] = actual_amount
    reservation["actual_unit"] = actual_unit
    task.setdefault("history", []).append({
        "ts": now_iso(),
        "action": "budget:settle",
        "amount": actual_amount,
        "unit": actual_unit,
        "source": source,
        "attempt": reservation.get("attempt"),
    })
    budget = refresh_runtime_budget(queue)
    if budget.get("runtime_status") == "overrun":
        issue = issue or (
            f"runtime budget overrun after actual settlement: available={budget.get('runtime_available')} "
            f"{budget.get('runtime_unit')}"
        )
    return issue or None


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
    refresh_runtime_budget(queue)
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
    queue = {
        "kind": BATCH_KIND,
        "version": VERSION,
        "root": root,
        "generated_at": now_iso(),
        "updated_at": now_iso(),
        "max_concurrency": max_concurrency,
        "max_retries": max_retries,
        "budget": budget,
        "coordination": coordination_backend_status(root),
        "summary": summarize_tasks(tasks),
        "batches": make_batches(tasks, max_concurrency),
        "tasks": tasks,
    }
    refresh_runtime_budget(queue)
    return queue


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
    backend = active_coordination_backend(root)
    if backend is not None:
        return backend.load_queue()
    return _load_queue_file(root)


def sqlite_backend_active(root: str) -> bool:
    return coordination_backend_status(root).get("backend") == "sqlite"


def _load_queue_file(root: str) -> Dict[str, Any]:
    path = queue_path(root)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    data = json.load(open(path, encoding="utf-8"))
    if not isinstance(data, dict) or data.get("kind") != BATCH_KIND:
        raise ValueError(f"{path} is not an n2d batch queue")
    return data


def _save_queue_file(root: str, queue: Dict[str, Any]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    queue["updated_at"] = now_iso()
    queue.setdefault("coordination", coordination_backend_status(root))
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


class SQLiteQueueBackend:
    """SQLite-backed coordination for queue claim/mark/reclaim/heartbeat.

    JSON remains the portable mirror.  SQLite is the transactional coordination
    backend when `N2D_COORDINATION_BACKEND=sqlite` or coordination_backend.json
    declares `{"backend":"sqlite"}`.
    """

    def __init__(self, root: str):
        self.root = root
        self.db_path = sqlite_db_path(root)

    def connect(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        self.ensure_schema(conn)
        return conn

    @staticmethod
    def ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              priority INTEGER NOT NULL,
              episode TEXT,
              stage_key TEXT,
              worker TEXT,
              lease_until REAL,
              attempts INTEGER NOT NULL DEFAULT 0,
              idempotency_key TEXT,
              dead_letter INTEGER NOT NULL DEFAULT 0,
              updated_at TEXT,
              task_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_claim ON tasks(status, priority)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_lease ON tasks(status, lease_until)")
        conn.execute(
            "INSERT INTO metadata(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(SQLITE_SCHEMA_VERSION),),
        )

    def _sync_from_queue_in_conn(self, conn: sqlite3.Connection, queue: Dict[str, Any]) -> None:
        meta = {k: v for k, v in queue.items() if k != "tasks"}
        conn.execute(
            "INSERT INTO metadata(key, value) VALUES('queue', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (json.dumps(meta, ensure_ascii=False, sort_keys=True),),
        )
        ids = [str(task.get("id") or "") for task in queue.get("tasks", []) if task.get("id")]
        if ids:
            placeholders = ",".join("?" for _ in ids)
            conn.execute(f"DELETE FROM tasks WHERE id NOT IN ({placeholders})", ids)
        else:
            conn.execute("DELETE FROM tasks")
        for task in queue.get("tasks", []):
            tid = str(task.get("id") or "")
            if not tid:
                continue
            conn.execute(
                """
                INSERT INTO tasks(id,status,priority,episode,stage_key,worker,lease_until,attempts,
                                  idempotency_key,dead_letter,updated_at,task_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                  status=excluded.status,
                  priority=excluded.priority,
                  episode=excluded.episode,
                  stage_key=excluded.stage_key,
                  worker=excluded.worker,
                  lease_until=excluded.lease_until,
                  attempts=excluded.attempts,
                  idempotency_key=excluded.idempotency_key,
                  dead_letter=excluded.dead_letter,
                  updated_at=excluded.updated_at,
                  task_json=excluded.task_json
                """,
                (
                    tid,
                    str(task.get("status") or "queued"),
                    int(task.get("priority") or 999999),
                    str(task.get("episode") or ""),
                    str(task.get("stage_key") or ""),
                    str(task.get("worker") or ""),
                    task.get("lease_until"),
                    int(task.get("attempts") or 0),
                    str(task.get("idempotency_key") or ""),
                    1 if task.get("dead_letter") else 0,
                    str(task.get("updated_at") or ""),
                    json.dumps(task, ensure_ascii=False, sort_keys=True),
                ),
            )

    def sync_from_queue(self, queue: Dict[str, Any]) -> None:
        with self.connect() as conn:
            with conn:
                self._sync_from_queue_in_conn(conn, queue)

    def _load_from_conn(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        meta_row = conn.execute("SELECT value FROM metadata WHERE key='queue'").fetchone()
        rows = conn.execute("SELECT task_json FROM tasks ORDER BY priority, id").fetchall()
        if not rows:
            queue = _load_queue_file(self.root)
            self._sync_from_queue_in_conn(conn, queue)
            return queue
        meta = json.loads(meta_row["value"]) if meta_row else {}
        tasks = [json.loads(row["task_json"]) for row in rows]
        queue = dict(meta)
        queue["tasks"] = tasks
        queue["coordination"] = coordination_backend_status(self.root)
        queue["summary"] = summarize_tasks(tasks)
        queue["batches"] = make_batches(tasks, int(queue.get("max_concurrency") or 1))
        return queue

    def load_queue(self) -> Dict[str, Any]:
        if not os.path.isfile(self.db_path):
            queue = _load_queue_file(self.root)
            self.sync_from_queue(queue)
            return queue
        with self.connect() as conn:
            return self._load_from_conn(conn)

    def _transaction(self):
        conn = self.connect()
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        return conn

    def _commit_and_mirror(self, conn: sqlite3.Connection, queue: Dict[str, Any]) -> None:
        self._sync_from_queue_in_conn(conn, queue)
        conn.execute("COMMIT")
        _save_queue_file(self.root, queue)

    def claim(self, *, limit: Optional[int], worker: Optional[str], lease_seconds: int) -> List[Dict[str, Any]]:
        conn = self._transaction()
        committed = False
        try:
            queue = self._load_from_conn(conn)
            reclaim_expired(queue)
            enforce_claim_governance_interlock(self.root, queue)
            claimed = claim_tasks(queue, limit, worker=worker, lease_seconds=lease_seconds)
            self._commit_and_mirror(conn, queue)
            committed = True
            return [dict(task) for task in claimed]
        except Exception:
            if not committed:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def claim_exact(self, *, task_id: str, expected_plan_digest: str, episode: str,
                    stage_key: str, worker: Optional[str], lease_seconds: int) -> List[Dict[str, Any]]:
        conn = self._transaction()
        committed = False
        try:
            try:
                queue = self._load_from_conn(conn)
            except FileNotFoundError:
                queue = _empty_runtime_queue(self.root)
            reclaim_expired(queue)
            enforce_claim_governance_interlock(self.root, queue)
            planned = current_exact_plan(
                self.root,
                task_id_value=task_id,
                expected_plan_digest=expected_plan_digest,
                episode=episode,
                stage_key=stage_key,
                queue=queue,
            )
            materialize_exact_plan(queue, planned, expected_plan_digest)
            claimed = claim_task_exact(
                queue,
                task_id_value=task_id,
                expected_plan_digest=expected_plan_digest,
                worker=worker,
                lease_seconds=lease_seconds,
            )
            self._commit_and_mirror(conn, queue)
            committed = True
            return [dict(task) for task in claimed]
        except Exception:
            if not committed:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def mark(self, task_id_value: str, status: str, note: str = "",
             *, runner: Optional[Dict[str, Any]] = None,
             expected_worker: Optional[str] = None,
             expected_attempt: Optional[int] = None) -> Dict[str, Any]:
        conn = self._transaction()
        committed = False
        try:
            queue = self._load_from_conn(conn)
            task = mark_task(
                queue,
                task_id_value,
                status,
                note,
                expected_worker=expected_worker,
                expected_attempt=expected_attempt,
                runner=runner,
            )
            if runner is not None:
                task["last_runner"] = runner
            self._commit_and_mirror(conn, queue)
            committed = True
            return dict(task)
        except Exception:
            if not committed:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def reclaim(self, *, worker: Optional[str] = None, force_worker: bool = False) -> List[Dict[str, Any]]:
        conn = self._transaction()
        committed = False
        try:
            queue = self._load_from_conn(conn)
            reclaimed = reclaim_expired(queue, worker=worker, force_worker=force_worker)
            self._commit_and_mirror(conn, queue)
            committed = True
            return [dict(task) for task in reclaimed]
        except Exception:
            if not committed:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def renew(self, task_ids: Iterable[str], lease_seconds: int, worker: Optional[str] = None) -> int:
        conn = self._transaction()
        committed = False
        try:
            queue = self._load_from_conn(conn)
            n = renew_lease(queue, task_ids, lease_seconds, worker)
            self._commit_and_mirror(conn, queue)
            committed = True
            return n
        except Exception:
            if not committed:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()


# 内置参考实现：SQLite 事务协调后端登记进注册表，使其与未来 redis/db 走同一分发口。
register_coordination_backend("sqlite", SQLiteQueueBackend)


def save_queue(root: str, queue: Dict[str, Any]) -> None:
    _save_queue_file(root, queue)
    backend = active_coordination_backend(root)
    if backend is not None:
        backend.sync_from_queue(queue)


def _sqlite_rows(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    rows = conn.execute("SELECT id,status,worker,lease_until,attempts,dead_letter,task_json FROM tasks ORDER BY id").fetchall()
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        try:
            task = json.loads(row["task_json"])
        except Exception:
            task = {}
        out[str(row["id"])] = {
            "id": str(row["id"]),
            "status": str(row["status"]),
            "worker": str(row["worker"] or ""),
            "lease_until": row["lease_until"],
            "attempts": int(row["attempts"] or 0),
            "dead_letter": bool(row["dead_letter"]),
            "task_json": task,
        }
    return out


def _task_compare(task: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "status": str(task.get("status") or ""),
        "worker": str(task.get("worker") or ""),
        "attempts": int(task.get("attempts") or 0),
        "dead_letter": bool(task.get("dead_letter")),
        "lease_until": task.get("lease_until"),
    }


def sqlite_doctor(root: str, *, write: bool = False) -> Dict[str, Any]:
    root = root.rstrip("/")
    coord = coordination_backend_status(root)
    if coord.get("backend") != "sqlite":
        payload = {
            "kind": "n2d_sqlite_queue_doctor",
            "version": 1,
            "root": root,
            "backend": coord,
            "status": "skip",
            "issues": [],
            "summary": {"reason": "sqlite backend not active"},
            "generated_at": now_iso(),
        }
        if write:
            write_sqlite_doctor(root, payload)
        return payload

    issues: List[Dict[str, Any]] = []
    db_path = sqlite_db_path(root)
    mirror_path = queue_path(root)
    mirror: Dict[str, Any] = {}
    mirror_tasks: Dict[str, Dict[str, Any]] = {}
    if not os.path.isfile(mirror_path):
        issues.append({"severity": "block", "message": f"missing JSON mirror: {mirror_path}"})
    else:
        try:
            mirror = _load_queue_file(root)
            mirror_tasks = {str(task.get("id")): task for task in mirror.get("tasks", []) if task.get("id")}
        except Exception as exc:
            issues.append({"severity": "block", "message": f"invalid JSON mirror: {exc}"})

    db_tasks: Dict[str, Dict[str, Any]] = {}
    schema_version = ""
    if not os.path.isfile(db_path):
        issues.append({"severity": "block", "message": f"missing SQLite DB: {db_path}"})
    else:
        try:
            backend = SQLiteQueueBackend(root)
            with backend.connect() as conn:
                row = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
                schema_version = str(row["value"]) if row else ""
                if schema_version != str(SQLITE_SCHEMA_VERSION):
                    issues.append({"severity": "block", "message": f"schema_version {schema_version or 'missing'} != {SQLITE_SCHEMA_VERSION}"})
                db_tasks = _sqlite_rows(conn)
                integrity = conn.execute("PRAGMA integrity_check").fetchone()
                if integrity and str(integrity[0]).lower() != "ok":
                    issues.append({"severity": "block", "message": f"sqlite integrity_check={integrity[0]}"})
        except Exception as exc:
            issues.append({"severity": "block", "message": f"cannot inspect SQLite DB: {exc}"})

    mirror_ids = set(mirror_tasks)
    db_ids = set(db_tasks)
    for tid in sorted(db_ids - mirror_ids):
        issues.append({"severity": "block", "task_id": tid, "message": "task exists in SQLite but not JSON mirror"})
    for tid in sorted(mirror_ids - db_ids):
        issues.append({"severity": "block", "task_id": tid, "message": "task exists in JSON mirror but not SQLite"})
    for tid in sorted(db_ids & mirror_ids):
        db_task = _task_compare(db_tasks[tid]["task_json"])
        # Columns are the transactional truth; make the comparison robust to stale task_json inside DB rows.
        db_task.update({k: v for k, v in _task_compare(db_tasks[tid]).items() if v not in ("", None)})
        mirror_task = _task_compare(mirror_tasks[tid])
        if db_task != mirror_task:
            issues.append({
                "severity": "block",
                "task_id": tid,
                "message": "SQLite/JSON mirror task state diverged",
                "sqlite": db_task,
                "json": mirror_task,
            })

    payload = {
        "kind": "n2d_sqlite_queue_doctor",
        "version": 1,
        "root": root,
        "backend": coord,
        "db_path": db_path,
        "mirror_path": mirror_path,
        "schema_version": schema_version,
        "wal": {
            "exists": os.path.isfile(f"{db_path}-wal"),
            "path": f"{db_path}-wal",
        },
        "summary": {
            "sqlite_tasks": len(db_tasks),
            "json_tasks": len(mirror_tasks),
            "issues": len(issues),
        },
        "issues": issues,
        "status": "fail" if any(item.get("severity") == "block" for item in issues) else "pass",
        "generated_at": now_iso(),
    }
    if write:
        write_sqlite_doctor(root, payload)
    return payload


def render_sqlite_doctor(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d SQLite Queue Doctor",
        "",
        f"- 状态：{payload.get('status')}",
        f"- DB：`{payload.get('db_path') or '—'}`",
        f"- JSON mirror：`{payload.get('mirror_path') or '—'}`",
        f"- summary：{payload.get('summary')}",
        "",
        "## Issues",
        "",
    ]
    issues = payload.get("issues") or []
    lines.extend([f"- {item.get('severity')}: {item.get('message')}" for item in issues] or ["- 无"])
    lines.append("")
    return "\n".join(lines)


def write_sqlite_doctor(root: str, payload: Dict[str, Any]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    with open(sqlite_doctor_path(root), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(production_dir(root), SQLITE_DOCTOR_MD), "w", encoding="utf-8") as fh:
        fh.write(render_sqlite_doctor(payload))


def render_markdown(queue: Dict[str, Any]) -> str:
    summary = queue.get("summary", {})
    budget = queue.get("budget", {})
    coordination = queue.get("coordination") if isinstance(queue.get("coordination"), dict) else {}
    lines = [
        "# n2d 批量任务队列",
        "",
        f"- 更新时间：{queue.get('updated_at') or queue.get('generated_at')}",
        f"- 最大并发：{queue.get('max_concurrency')}",
        f"- 重试上限：{queue.get('max_retries')}",
        f"- 预算：{budget.get('accepted_total', 0)} / {budget.get('limit', '—')} {budget.get('unit', '')}",
        f"- 任务数：{summary.get('total', 0)}",
    ]
    if coordination:
        lines.append(
            f"- 协调后端：{coordination.get('backend')} / lock={coordination.get('lock_mode')} / status={coordination.get('status')}"
        )
        if coordination.get("warning"):
            lines.append(f"- 协调提醒：{coordination.get('warning')}")
    lines.extend([
        "",
        "## 状态",
        "",
        "| 状态 | 数量 |",
        "|---|---:|",
    ])
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
        next_attempt = int(task.get("attempts") or 0) + 1
        budget_issue = reserve_task_budget(
            queue,
            task,
            worker=worker,
            attempt=next_attempt,
        )
        if budget_issue:
            task["status"] = "blocked_budget"
            task["budget_note"] = budget_issue
            task["updated_at"] = now_iso()
            task.setdefault("history", []).append({
                "ts": now_iso(),
                "action": "claim:budget_block",
                "reason": budget_issue,
                "worker": worker or "",
            })
            continue
        task["status"] = "running"
        task["attempts"] = next_attempt
        task["updated_at"] = now_iso()
        task["worker"] = worker or ""
        task["lease_until"] = now_ts() + max(1, int(lease_seconds))
        task["lease_until_iso"] = dt.datetime.fromtimestamp(task["lease_until"], dt.timezone.utc).replace(microsecond=0).isoformat()
        task.setdefault("history", []).append(
            {"ts": now_iso(), "action": "claim", "attempt": task["attempts"], "worker": worker or ""}
        )
        claimed.append(task)
        capacity -= 1
    refresh_runtime_budget(queue)
    return claimed


def _empty_runtime_queue(root: str) -> Dict[str, Any]:
    return make_queue(
        root,
        [],
        max_concurrency=1,
        max_retries=1,
        budget=apply_budget([], None, None),
    )


def current_exact_plan(
    root: str,
    *,
    task_id_value: str,
    expected_plan_digest: str,
    episode: str,
    stage_key: str,
    queue: Mapping[str, Any],
) -> Dict[str, Any]:
    planned = route_tasks(
        root,
        episodes={normalize_episode(episode)},
        stage_filters={str(stage_key)},
        cost_estimates=load_cost_estimates(root),
        max_retries=int(queue.get("max_retries") or 1),
    )
    matches = [
        task for task in planned
        if str(task.get("id") or "") == str(task_id_value)
        and task_plan_digest(task) == str(expected_plan_digest)
    ]
    if len(matches) != 1:
        actual = [
            {"task_id": str(task.get("id") or ""), "plan_digest": task_plan_digest(task)}
            for task in planned
        ]
        raise ValueError(
            "exact current plan unavailable or changed: "
            + json.dumps(actual, ensure_ascii=False, sort_keys=True)
        )
    return deepcopy(matches[0])


def materialize_exact_plan(
    queue: Dict[str, Any], planned: Mapping[str, Any], expected_plan_digest: str
) -> Dict[str, Any]:
    """Insert/refresh one fresh plan without replacing running or attempted history."""
    task = deepcopy(dict(planned))
    if task_plan_digest(task) != str(expected_plan_digest):
        raise ValueError("materialized task plan digest mismatch")
    task_id_value = str(task.get("id") or "")
    tasks = queue.setdefault("tasks", [])
    existing = next((row for row in tasks if str(row.get("id") or "") == task_id_value), None)
    if existing is None:
        task.setdefault("history", []).append({
            "ts": now_iso(), "action": "plan:materialize_exact",
            "plan_digest": expected_plan_digest,
        })
        tasks.append(task)
        return task
    if task_plan_digest(existing) == expected_plan_digest:
        return existing
    status = str(existing.get("status") or "")
    if status not in REPLACEABLE_MERGE_STATUSES or int(existing.get("attempts") or 0) != 0:
        raise ValueError(
            f"cannot replace stale exact task {task_id_value}: status={status} "
            f"attempts={existing.get('attempts')}"
        )
    history = list(existing.get("history") or [])
    history.append({
        "ts": now_iso(), "action": "plan:refresh_exact",
        "previous_plan_digest": task_plan_digest(existing),
        "plan_digest": expected_plan_digest,
    })
    task["history"] = history + list(task.get("history") or [])
    tasks[tasks.index(existing)] = task
    return task


def claim_task_exact(
    queue: Dict[str, Any],
    *,
    task_id_value: str,
    expected_plan_digest: str,
    worker: Optional[str],
    lease_seconds: int,
) -> List[Dict[str, Any]]:
    """Claim only the hash-bound task; never fall through to a different priority row."""
    target = next(
        (task for task in queue.get("tasks", []) if str(task.get("id") or "") == task_id_value),
        None,
    )
    if target is None or task_plan_digest(target) != expected_plan_digest:
        raise ValueError("exact task missing or plan digest mismatch at claim")
    prior_status = str(target.get("status") or "")
    if prior_status not in {"queued", "retry_queued", "provider_pending"}:
        return []
    max_concurrency = int(queue.get("max_concurrency") or 1)
    running = sum(1 for task in queue.get("tasks", []) if task.get("status") == "running")
    if running >= max_concurrency:
        return []
    recovering_provider = prior_status == "provider_pending"
    next_attempt = int(target.get("attempts") or 0) if recovering_provider else int(target.get("attempts") or 0) + 1
    if recovering_provider and next_attempt <= 0:
        raise ValueError("provider_pending task has no original claim attempt")
    reservation = target.get("budget_reservation")
    if recovering_provider and not (
        isinstance(reservation, Mapping) and reservation.get("status") == "reserved"
    ):
        raise ValueError("provider_pending task lost its original budget reservation")
    budget_issue = None if recovering_provider else reserve_task_budget(
        queue, target, worker=worker, attempt=next_attempt
    )
    if budget_issue:
        target["status"] = "blocked_budget"
        target["budget_note"] = budget_issue
        target["updated_at"] = now_iso()
        target.setdefault("history", []).append({
            "ts": now_iso(), "action": "claim_exact:budget_block",
            "reason": budget_issue, "worker": worker or "",
        })
        refresh_runtime_budget(queue)
        return []
    target["status"] = "running"
    target["attempts"] = next_attempt
    target["updated_at"] = now_iso()
    target["worker"] = worker or ""
    target["lease_until"] = now_ts() + max(1, int(lease_seconds))
    target["lease_until_iso"] = dt.datetime.fromtimestamp(
        target["lease_until"], dt.timezone.utc
    ).replace(microsecond=0).isoformat()
    target.setdefault("history", []).append({
        "ts": now_iso(),
        "action": "claim_exact:resume_provider" if recovering_provider else "claim_exact",
        "attempt": next_attempt,
        "worker": worker or "", "plan_digest": expected_plan_digest,
    })
    refresh_runtime_budget(queue)
    return [target]


def _clear_lease(task: Dict[str, Any]) -> None:
    for key in ("worker", "lease_until", "lease_until_iso"):
        task.pop(key, None)


def provider_submission_state(queue: Mapping[str, Any], task: Mapping[str, Any]) -> Dict[str, Any]:
    """Read the durable video manifest without importing provider code.

    A submit id is sufficient to resume by query only.  ``submitted_at`` without an id is an
    unknown paid state: it is deliberately distinguished so lease recovery can block replay.
    """
    if str(task.get("stage_key") or "") != "video":
        return {}
    root = Path(str(queue.get("root") or "")).expanduser().resolve()
    manifest_value = str(task.get("producer_manifest") or "").strip()
    clips = [str(value).strip() for value in task.get("physical_clips", []) or [] if str(value).strip()]
    if not manifest_value or len(clips) != 1:
        return {}
    manifest_path = Path(manifest_value).expanduser()
    manifest_path = manifest_path if manifest_path.is_absolute() else root / manifest_path
    try:
        manifest_path = manifest_path.resolve(strict=False)
        manifest_path.relative_to(root)
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    item = next(
        (
            row for row in payload.get("items", []) or []
            if isinstance(row, Mapping) and str(row.get("clip") or "") == clips[0]
        ),
        None,
    )
    if not isinstance(item, Mapping):
        return {}
    submit_id = str(item.get("submit_id") or "").strip()
    status = str(item.get("status") or "").strip().lower()
    terminal_failures = {"failed", "rejected", "cancelled", "canceled"}
    state = (
        "provider_terminal_failure"
        if submit_id and status in terminal_failures
        else "provider_pending" if submit_id else ""
    )
    if not submit_id and (
        item.get("submitted_at") or status in {"submitting", "submitted_unknown_id"}
    ):
        state = "unknown_paid_state"
    if not state:
        return {}
    return {
        "state": state,
        "provider_submit_id": submit_id,
        "provider_status": status,
        "target": str(item.get("target") or ""),
        "download_submit_id": str(item.get("download_submit_id") or ""),
        "download_artifact_sha256": str(item.get("download_artifact_sha256") or ""),
        "producer_manifest": manifest_path.relative_to(root).as_posix(),
        "physical_clip": clips[0],
        "last_query": deepcopy(item.get("last_query")) if isinstance(item.get("last_query"), Mapping) else {},
        "observed_at": now_iso(),
    }


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
        provider_state = provider_submission_state(queue, task)
        if provider_state.get("state") == "provider_pending":
            # The paid request has a durable provider id.  Preserve the original attempt and
            # reservation; the next exact claim may only query/download that id.
            task["status"] = "provider_pending"
            task["provider_job"] = provider_state
            task["updated_at"] = now_iso()
            reason = "lease_expired" if expired else "worker_resume"
            task.setdefault("history", []).append({
                "ts": now_iso(), "action": "reclaim:provider_pending", "reason": reason,
                "prev_worker": task.get("worker", ""), "attempt": int(task.get("attempts") or 0),
                "provider_submit_id": provider_state.get("provider_submit_id"),
            })
            _clear_lease(task)
            reclaimed.append(task)
            continue
        attempts = int(task.get("attempts") or 0)
        max_retries = resolve_max_retries(task, queue)
        reservation = task.get("budget_reservation")
        if (
            str(task.get("stage_key") or "") in PRODUCTION_EXECUTION_STAGES
            and isinstance(reservation, Mapping)
            and reservation.get("status") == "reserved"
        ):
            # A crashed worker leaves no trustworthy "command never started" receipt. Hold the
            # cap conservatively by settling the estimate; otherwise reclaim+retry can double-spend.
            settle_task_budget(queue, task, task.get("last_runner") if isinstance(task.get("last_runner"), Mapping) else None)
        else:
            release_task_budget(queue, task, "lease_expired" if expired else "worker_resume")
        if provider_state.get("state") == "unknown_paid_state":
            # A subprocess may have crossed the paid boundary before dying but no submit id was
            # durably returned.  Never retry this request automatically.
            task["status"] = "blocked_provider_unknown"
            task["provider_job"] = provider_state
            task["last_error_class"] = "provider_paid_state_unknown"
            task["last_note"] = (
                "provider paid state is unknown and has no submit_id; automatic resubmission blocked"
            )
        elif provider_state.get("state") == "provider_terminal_failure":
            task["status"] = "blocked_provider_terminal"
            task["provider_job"] = provider_state
            task["last_error_class"] = "provider_terminal_failure"
            task["last_note"] = (
                "provider returned a terminal failure for the durable submit_id; automatic resubmission blocked"
            )
        else:
            task["status"] = "retry_queued" if attempts <= max_retries else "failed"
        task["updated_at"] = now_iso()
        reason = "lease_expired" if expired else "worker_resume"
        task.setdefault("history", []).append(
            {"ts": now_iso(), "action": "reclaim", "reason": reason, "prev_worker": task.get("worker", ""), "attempt": attempts}
        )
        _clear_lease(task)
        reclaimed.append(task)
    refresh_runtime_budget(queue)
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
    backend = active_coordination_backend(root)
    if backend is not None:
        # Built-in SQLite repeats this check inside BEGIN IMMEDIATE below.  A third-party
        # backend still gets an API-level fail-closed check; its implementation must repeat
        # the same invariant in its own distributed claim transaction.
        if not isinstance(backend, SQLiteQueueBackend):
            enforce_claim_governance_interlock(root, backend.load_queue())
        return backend.claim(limit=limit, worker=worker, lease_seconds=lease_seconds)
    with queue_lock(root):
        queue = load_queue(root)
        reclaim_expired(queue)  # 每次认领前先回收过期租约（自动断点恢复）
        enforce_claim_governance_interlock(root, queue)
        claimed = claim_tasks(queue, limit, worker=worker, lease_seconds=lease_seconds)
        save_queue(root, queue)
        return [dict(task) for task in claimed]


def claim_exact(
    root: str,
    *,
    task_id: str,
    expected_plan_digest: str,
    episode: str,
    stage_key: str,
    worker: Optional[str] = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> List[Dict[str, Any]]:
    """Atomically materialize and claim only the current hash-bound task plan."""
    backend = active_coordination_backend(root)
    if backend is not None:
        exact = getattr(backend, "claim_exact", None)
        if not callable(exact):
            raise RuntimeError(
                f"coordination backend {coordination_backend_name(root)} lacks claim_exact; fail closed"
            )
        if not isinstance(backend, SQLiteQueueBackend):
            enforce_claim_governance_interlock(root, backend.load_queue())
        return exact(
            task_id=task_id,
            expected_plan_digest=expected_plan_digest,
            episode=episode,
            stage_key=stage_key,
            worker=worker,
            lease_seconds=lease_seconds,
        )
    with queue_lock(root):
        try:
            queue = load_queue(root)
        except FileNotFoundError:
            queue = _empty_runtime_queue(root)
        reclaim_expired(queue)
        enforce_claim_governance_interlock(root, queue)
        planned = current_exact_plan(
            root,
            task_id_value=task_id,
            expected_plan_digest=expected_plan_digest,
            episode=episode,
            stage_key=stage_key,
            queue=queue,
        )
        materialize_exact_plan(queue, planned, expected_plan_digest)
        claimed = claim_task_exact(
            queue,
            task_id_value=task_id,
            expected_plan_digest=expected_plan_digest,
            worker=worker,
            lease_seconds=lease_seconds,
        )
        save_queue(root, queue)
        return [dict(task) for task in claimed]


def mark(root: str, task_id_value: str, status: str, note: str = "",
         *, runner: Optional[Dict[str, Any]] = None,
         expected_worker: Optional[str] = None,
         expected_attempt: Optional[int] = None) -> Dict[str, Any]:
    backend = active_coordination_backend(root)
    if backend is not None:
        return backend.mark(
            task_id_value,
            status,
            note,
            runner=runner,
            expected_worker=expected_worker,
            expected_attempt=expected_attempt,
        )
    with queue_lock(root):
        queue = load_queue(root)
        task = mark_task(
            queue,
            task_id_value,
            status,
            note,
            expected_worker=expected_worker,
            expected_attempt=expected_attempt,
            runner=runner,
        )
        if runner is not None:
            task["last_runner"] = runner
        save_queue(root, queue)
        return dict(task)


def reclaim(root: str, *, worker: Optional[str] = None, force_worker: bool = False) -> List[Dict[str, Any]]:
    backend = active_coordination_backend(root)
    if backend is not None:
        return backend.reclaim(worker=worker, force_worker=force_worker)
    with queue_lock(root):
        queue = load_queue(root)
        reclaimed = reclaim_expired(queue, worker=worker, force_worker=force_worker)
        save_queue(root, queue)
        return [dict(task) for task in reclaimed]


def renew(root: str, task_ids: Iterable[str], lease_seconds: int, worker: Optional[str] = None) -> int:
    backend = active_coordination_backend(root)
    if backend is not None:
        return backend.renew(task_ids, lease_seconds, worker)
    with queue_lock(root):
        queue = load_queue(root)
        n = renew_lease(queue, task_ids, lease_seconds, worker)
        if n:
            save_queue(root, queue)
        return n


def resolve_max_retries(task, queue) -> int:
    """任务级显式 max_retries=0（零重试）必须生效：旧写法 `task.get(...) or queue.get(...) or 0`
    会因 0 falsy 被队列默认覆盖，导致无法配置零重试任务。None 才回退队列级。"""
    for source in (task.get("max_retries"), queue.get("max_retries")):
        if source is not None:
            try:
                return int(source)
            except (TypeError, ValueError):
                continue
    return 0


def classify_error(note: str = "", runner: Optional[Mapping[str, Any]] = None) -> str:
    """错误归类（8 类·SKILL 同口径）。⚠️ 关键词启发式：按子串命中、顺序敏感，可能误分类
    （死信 error_class 只作分诊线索，不作根因结论）。runner 显式给出的结构化 error_class
    永远优先于文本猜测。budget 在 capability 之前判：预算类报错常含 "backend" 字样，
    旧顺序会把预算错误误归 capability。"""
    runner = runner or {}
    declared = str(runner.get("error_class") or "").strip()
    if declared in {"preflight_block", "capability", "budget", "timeout",
                    "output_contract", "configuration", "command_failed", "unknown"}:
        return declared
    text = " ".join(
        str(part or "")
        for part in (
            note,
            runner.get("note"),
            runner.get("error"),
            runner.get("stderr"),
            runner.get("stdout"),
        )
    ).lower()
    exit_code = runner.get("exit_code")
    if "next_preflight blocked" in text or "blocked_by_" in text:
        return "preflight_block"
    if "budget" in text or "blocked_budget" in text:
        return "budget"
    if "capability" in text or "evidence" in text or "backend" in text:
        return "capability"
    if "timeout" in text or exit_code in (124, 137):
        return "timeout"
    if "verification failed" in text or "missing output" in text or "progress not done" in text:
        return "output_contract"
    if "slash command" in text or "task has no command" in text:
        return "configuration"
    if isinstance(exit_code, int) and exit_code != 0:
        return "command_failed"
    return "unknown"


def _completion_policy(task: Mapping[str, Any]) -> Dict[str, Any]:
    """Derive completion hardness from the canonical stage contract, not another stage list."""
    stage_key = str(task.get("stage_key") or "")
    try:
        spec = find_stage(stage_key)
    except Exception:
        spec = {}
    hard = bool(
        spec.get("routes")
        and (spec.get("output_contract") or spec.get("outputs") or spec.get("gate_stage"))
    )
    gate_stage = str(task.get("gate_stage") or spec.get("gate_stage") or "").strip()
    return {
        "hard": hard,
        "gate_required": bool(gate_stage),
        "gate_stage": gate_stage,
        "acceptance_required": stage_key == "review",
    }


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sha256_value(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return (
        text.startswith("sha256:")
        and len(text) == 71
        and all(ch in "0123456789abcdef" for ch in text[7:])
    )


def _v2_phase_completion_issue(
    queue: Mapping[str, Any],
    task: Mapping[str, Any],
    runner: Mapping[str, Any],
    authorization: Mapping[str, Any],
) -> Optional[str]:
    """Validate a completed v2 phase-envelope execution without reapplying expiry.

    Expiry was enforced at consume.  Completion/final accounting may happen later and is proved
    by the exact reservation plus its provider completion record.
    """
    root = str(queue.get("root") or "").strip()
    expected_project = "sha256:" + hashlib.sha256(
        str(Path(root).expanduser().resolve()).encode("utf-8")
    ).hexdigest()
    if (
        authorization.get("kind") != "n2d_phase_spend_envelope"
        or authorization.get("line") != "n2d"
        or authorization.get("project_id") != expected_project
        or authorization.get("attempt_id_semantics") != "phase_retry_round"
    ):
        return "production completion v2 envelope identity/project/attempt semantics mismatch"
    approver = str(authorization.get("approver") or "").strip().lower()
    if (
        not approver
        or approver in {"unknown", "system", "agent", "auto", "any", "test"}
        or approver.startswith(("agent:", "auto:", "delegate:", "system:"))
        or not str(authorization.get("approval_reference") or "").strip()
        or not str(authorization.get("source_quote") or "").strip()
    ):
        return "production completion v2 envelope human approval evidence invalid"
    try:
        issued = dt.datetime.fromisoformat(str(authorization.get("issued_at") or "").replace("Z", "+00:00"))
        expires = dt.datetime.fromisoformat(str(authorization.get("expires_at") or "").replace("Z", "+00:00"))
    except ValueError:
        return "production completion v2 envelope timestamps invalid"
    if issued.tzinfo is None or expires.tzinfo is None or expires <= issued:
        return "production completion v2 envelope timestamps invalid"
    execution = runner.get("execution_binding")
    if not isinstance(execution, Mapping):
        return "production completion execution_binding missing"
    execution_keys = ("command_digest", "input_fingerprint", "submit_request_digest", "producer_contract_digest")
    projection = {key: str(execution.get(key) or "") for key in execution_keys}
    if any(not _sha256_value(value) for value in projection.values()):
        return "production completion v2 execution binding missing or invalid"
    scope = {
        "rerun_scope": str(task.get("rerun_scope") or ""),
        "affected_shots": sorted({str(item) for item in task.get("affected_shots", []) if str(item)}),
        "affected_artifacts": sorted({str(item) for item in task.get("affected_artifacts", []) if str(item)}),
    }
    # runner._binding_digest(structured_value) hashes a canonical {"value": ...} wrapper.
    expected_input = _canonical_sha256({"value": {"execution": projection, "scope": scope}})
    for key, expected in (
        ("stage", str(task.get("stage_key") or "")),
        ("scope", scope),
        ("model", str(execution.get("model") or "")),
        ("channel", str(execution.get("channel") or "")),
        ("input_sha256", expected_input),
    ):
        if authorization.get(key) != expected:
            return f"production completion v2 envelope {key} mismatch"
    estimate = task.get("estimated_cost") if isinstance(task.get("estimated_cost"), Mapping) else {}
    try:
        amount = float(estimate.get("amount"))
        ceiling = authorization.get("limits", {}).get("cost_ceiling", {})
        ceiling_amount = float(ceiling.get("amount"))
    except (TypeError, ValueError):
        return "production completion v2 envelope cost invalid"
    currency = str(estimate.get("unit") or "")
    if not math.isfinite(amount) or amount < 0 or currency != str(ceiling.get("currency") or "") or amount > ceiling_amount:
        return "production completion v2 envelope cost ceiling mismatch"
    completion = runner.get("completion") if isinstance(runner.get("completion"), Mapping) else {}
    consumption = completion.get("phase_spend_consumption")
    finalized = completion.get("phase_spend_completion")
    if not isinstance(consumption, Mapping) or consumption.get("status") != "pass":
        return "production completion v2 spend reservation missing"
    row = consumption.get("consumption") if isinstance(consumption.get("consumption"), Mapping) else {}
    attempt = int(task.get("attempts") or 0)
    if (
        consumption.get("authorization_digest") != authorization.get("authorization_digest")
        or row.get("consumption_id") != f"{task.get('id') or 'missing-task'}:{attempt}"
        or str(row.get("attempt_id") or "") != str(attempt)
        or row.get("input_sha256") != expected_input
    ):
        return "production completion v2 spend reservation binding mismatch"
    if (
        not isinstance(finalized, Mapping)
        or finalized.get("status") != "pass"
        or finalized.get("authorization_digest") != authorization.get("authorization_digest")
        or finalized.get("consumption_id") != row.get("consumption_id")
    ):
        return "production completion v2 provider completion finalization missing"
    return None


def _runner_completion_issue(
    queue: Mapping[str, Any],
    task: Mapping[str, Any],
    runner: Optional[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> Optional[str]:
    """Reject internally contradictory completion claims before queue commits ``done``.

    This is a consistency contract, not an identity signature.  Human/payment authority still
    comes from the canonical acceptance/production authorization receipts; the queue merely
    refuses to turn a caller supplied pair of green strings into a terminal state.
    """
    if not isinstance(runner, Mapping):
        return "runner completion evidence missing"
    if runner.get("status") != "pass":
        return f"runner status must be pass, got {runner.get('status') or 'missing'}"
    if runner.get("exit_code") != 0:
        return f"runner exit_code must be 0, got {runner.get('exit_code')!r}"
    execution_started = runner.get("execution_started")
    if execution_started is not True and not (
        policy.get("acceptance_required") and execution_started is False
    ):
        return "runner execution_started must be true (review re-attestation may be false)"

    if str(task.get("stage_key") or "") in PRODUCTION_EXECUTION_STAGES:
        completion = runner.get("completion") if isinstance(runner.get("completion"), Mapping) else {}
        safe_local = (
            str(task.get("stage_key") or "") == "compose"
            and completion.get("safe_local_execution") is True
        )
        if safe_local:
            if runner.get("authorization") or completion.get("paid_execution_expectation"):
                return "safe local compose must not carry paid authorization/expectation"
            return None
        authorization = runner.get("authorization")
        if not isinstance(authorization, Mapping):
            return "production completion missing authorization receipt"
        if authorization.get("decision") != "approved":
            return "production completion authorization decision must be approved"
        declared_authorization_digest = str(authorization.get("authorization_digest") or "")
        if not _sha256_value(declared_authorization_digest):
            return "production completion authorization_digest missing or invalid"
        calculated_authorization_digest = _canonical_sha256({
            key: value for key, value in authorization.items() if key != "authorization_digest"
        })
        if declared_authorization_digest != calculated_authorization_digest:
            return "production completion authorization_digest mismatch"
        if authorization.get("version") == 2:
            v2_issue = _v2_phase_completion_issue(queue, task, runner, authorization)
            if v2_issue:
                return v2_issue
            # The producer receipt checks below are common to v1/v2, but all intervening fields
            # are v1-specific.  Validate the common receipt boundary here and return.
            expectation = completion.get("paid_execution_expectation")
            receipts = completion.get("paid_execution_receipts")
            if paid_execution_contract is None or not isinstance(expectation, Mapping):
                return "production completion paid execution expectation missing"
            if str(expectation.get("digest") or "") != paid_execution_contract.expectation_digest(expectation):
                return "production completion paid execution expectation digest mismatch"
            for key, expected in (
                ("task_id", str(task.get("id") or "")),
                ("episode", normalize_episode(str(task.get("episode") or ""))),
                ("stage", str(task.get("stage_key") or "")),
                ("attempt", int(task.get("attempts") or 0)),
                ("authorization_digest", declared_authorization_digest),
            ):
                if expectation.get(key) != expected:
                    return f"production completion paid expectation {key} mismatch"
            if not isinstance(receipts, Mapping) or receipts.get("status") != "pass":
                return "production completion paid boundary receipts missing or failed"
            current_receipts = paid_execution_contract.verify_expected_receipts(
                Path(str(queue.get("root") or "")), expectation
            )
            if current_receipts.get("status") != "pass":
                return "production completion paid boundary receipts invalid: " + "; ".join(
                    str(item) for item in (current_receipts.get("issues") or [])[:4]
                )
            return None
        if authorization.get("version") != 1:
            return "production completion authorization version invalid"
        approval_id = str(authorization.get("approval_id") or "").strip()
        approver = str(authorization.get("approver") or "").strip()
        if not approval_id:
            return "production completion approval_id missing"
        if not approver or approver.lower() in {"unknown", "system", "agent", "auto", "any", "test"}:
            return "production completion approver missing or placeholder"
        try:
            issued_at = dt.datetime.fromisoformat(str(authorization.get("issued_at") or "").replace("Z", "+00:00"))
            expires_at = dt.datetime.fromisoformat(str(authorization.get("expires_at") or "").replace("Z", "+00:00"))
        except ValueError:
            return "production completion authorization timestamps invalid"
        if issued_at.tzinfo is None or expires_at.tzinfo is None:
            return "production completion authorization timestamps must be timezone-aware"
        now = dt.datetime.now(dt.timezone.utc)
        if issued_at.astimezone(dt.timezone.utc) > now + dt.timedelta(minutes=5):
            return "production completion authorization issued_at is in the future"
        if expires_at.astimezone(dt.timezone.utc) <= now:
            return "production completion authorization expired"
        if expires_at <= issued_at:
            return "production completion authorization expires_at must be after issued_at"
        execution = runner.get("execution_binding")
        if not isinstance(execution, Mapping):
            return "production completion execution_binding missing"
        for key in (
            "command_digest",
            "input_fingerprint",
            "submit_request_digest",
            "producer_contract_digest",
        ):
            if not _sha256_value(execution.get(key)):
                return f"production completion execution_binding.{key} missing or invalid"
        approved_execution = authorization.get("execution")
        execution_keys = (
            "command_digest",
            "input_fingerprint",
            "submit_request_digest",
            "producer_contract_digest",
        )
        execution_projection = {key: str(execution.get(key) or "") for key in execution_keys}
        if not isinstance(approved_execution, Mapping):
            return "production completion authorization execution missing"
        mismatches = [
            key for key in execution_keys
            if str(approved_execution.get(key) or "") != execution_projection[key]
        ]
        if mismatches:
            return "production completion differs from authorized execution: " + ", ".join(mismatches)
        scope = {
            "rerun_scope": str(task.get("rerun_scope") or ""),
            "affected_shots": sorted({str(item) for item in task.get("affected_shots", []) if str(item)}),
            "affected_artifacts": sorted({str(item) for item in task.get("affected_artifacts", []) if str(item)}),
        }
        estimate = task.get("estimated_cost") if isinstance(task.get("estimated_cost"), Mapping) else {}
        try:
            amount = float(estimate.get("amount"))
        except (TypeError, ValueError):
            return "production completion estimated cost invalid"
        currency = str(estimate.get("unit") or "")
        attempt = int(task.get("attempts") or 0)
        task_binding = {
            "task_id": str(task.get("id") or ""),
            "idempotency_key": str(task.get("idempotency_key") or ""),
            "episode": normalize_episode(str(task.get("episode") or "")),
            "stage_key": str(task.get("stage_key") or ""),
            "attempt": attempt,
            "scope": scope,
            "estimated_cost": {"amount": amount, "currency": currency},
            "execution": execution_projection,
        }
        expected_identity = {
            "task_id": task_binding["task_id"],
            "idempotency_key": task_binding["idempotency_key"],
            "task_digest": _canonical_sha256(task_binding),
            "stage_key": task_binding["stage_key"],
            "attempt": attempt,
            "episode": task_binding["episode"],
            "scope": scope,
        }
        for key, expected in expected_identity.items():
            actual = authorization.get(key)
            if key == "episode":
                actual = normalize_episode(str(actual or ""))
            if actual != expected:
                return f"production completion authorization {key} mismatch"
        ceiling = authorization.get("ceiling")
        if not isinstance(ceiling, Mapping):
            return "production completion authorization ceiling missing"
        try:
            ceiling_amount = float(ceiling.get("amount"))
        except (TypeError, ValueError):
            return "production completion authorization ceiling invalid"
        if str(ceiling.get("currency") or "") != currency or amount > ceiling_amount:
            return "production completion authorization ceiling mismatch"
        approved_model = str(authorization.get("model") or "")
        approved_channel = str(authorization.get("channel") or "")
        if not approved_model or not approved_channel:
            return "production completion authorization model/channel missing"
        if approved_model.lower() != "any" and approved_model != str(execution.get("model") or ""):
            return "production completion authorization model mismatch"
        if approved_channel.lower() != "any" and approved_channel != str(execution.get("channel") or ""):
            return "production completion authorization channel mismatch"

        completion = runner.get("completion") if isinstance(runner.get("completion"), Mapping) else {}
        expectation = completion.get("paid_execution_expectation")
        receipts = completion.get("paid_execution_receipts")
        if paid_execution_contract is None:
            return "paid_execution_contract unavailable"
        if not isinstance(expectation, Mapping):
            return "production completion paid execution expectation missing"
        if str(expectation.get("digest") or "") != paid_execution_contract.expectation_digest(expectation):
            return "production completion paid execution expectation digest mismatch"
        for key, expected in (
            ("task_id", task_binding["task_id"]),
            ("episode", task_binding["episode"]),
            ("stage", task_binding["stage_key"]),
            ("attempt", attempt),
            ("authorization_digest", declared_authorization_digest),
        ):
            if expectation.get(key) != expected:
                return f"production completion paid expectation {key} mismatch"
        if not isinstance(receipts, Mapping) or receipts.get("status") != "pass":
            return "production completion paid boundary receipts missing or failed"
        root = str(queue.get("root") or "").strip()
        if not root:
            return "production completion queue root missing"
        current_receipts = paid_execution_contract.verify_expected_receipts(Path(root), expectation)
        if current_receipts.get("status") != "pass":
            return "production completion paid boundary receipts invalid: " + "; ".join(
                str(item) for item in (current_receipts.get("issues") or [])[:4]
            )
    return None


def _paid_output_commit_attestation(
    queue: Mapping[str, Any],
    task: Mapping[str, Any],
    runner: Mapping[str, Any],
) -> Dict[str, Any]:
    """Lock-held, last-moment recheck of the exact bytes produced by a paid task."""
    if paid_execution_contract is None:
        return {"status": "fail", "issues": ["paid_execution_contract unavailable"]}
    completion = runner.get("completion") if isinstance(runner.get("completion"), Mapping) else {}
    expectation = completion.get("paid_execution_expectation")
    verified = completion.get("producer_output_bindings")
    root = str(queue.get("root") or "").strip()
    if not root or not isinstance(expectation, Mapping):
        return {"status": "fail", "issues": ["queue root or paid expectation missing"]}
    return paid_execution_contract.verify_current_output_bindings(
        Path(root), expectation, verified
    )


def completion_commit_digest(commit: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in commit.items() if key != "digest"}
    return _canonical_sha256(payload)


def build_completion_commit(
    task: Mapping[str, Any],
    runner: Mapping[str, Any],
    *,
    acceptance: Optional[Mapping[str, Any]] = None,
    output_attestation: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    execution = runner.get("execution_binding") if isinstance(runner.get("execution_binding"), Mapping) else {}
    authorization = runner.get("authorization") if isinstance(runner.get("authorization"), Mapping) else {}
    acceptance_snapshot: Dict[str, Any] = {}
    if isinstance(acceptance, Mapping):
        acceptance_snapshot = {
            "path": str(acceptance.get("path") or ""),
            "receipt_id": str(acceptance.get("receipt_id") or ""),
            "decision": str(acceptance.get("decision") or ""),
            "reviewer": str(acceptance.get("reviewer") or ""),
            "evidence_digest": str(acceptance.get("evidence_digest") or ""),
        }
    payload: Dict[str, Any] = {
        "kind": "n2d_batch_completion_commit",
        "version": 1,
        "status": "done",
        "task": {
            "id": str(task.get("id") or ""),
            "idempotency_key": str(task.get("idempotency_key") or ""),
            "episode": normalize_episode(str(task.get("episode") or "")),
            "stage_key": str(task.get("stage_key") or ""),
            "attempt": int(task.get("attempts") or 0),
        },
        "content_fingerprint": str(execution.get("input_fingerprint") or ""),
        "execution_binding": deepcopy(dict(execution)),
        "authorization_digest": str(authorization.get("authorization_digest") or ""),
        "completion": deepcopy(dict(runner.get("completion") or {})),
        "output_commit_attestation": deepcopy(dict(output_attestation or {})),
        "runner": {
            "status": runner.get("status"),
            "exit_code": runner.get("exit_code"),
            "execution_started": runner.get("execution_started"),
            "finished_at": str(runner.get("finished_at") or ""),
        },
        "acceptance": acceptance_snapshot,
        "budget_settlement": deepcopy(dict(task.get("budget_settlement") or {})),
        "committed_at": now_iso(),
    }
    payload["digest"] = completion_commit_digest(payload)
    return payload


def completion_commit_issue(task: Mapping[str, Any]) -> Optional[str]:
    commit = task.get("completion_commit")
    if not isinstance(commit, Mapping):
        return "completion_commit missing"
    if commit.get("kind") != "n2d_batch_completion_commit" or commit.get("version") != 1:
        return "completion_commit kind/version invalid"
    if commit.get("status") != "done" or task.get("status") != "done":
        return "completion_commit status contradicts task status"
    if str(commit.get("digest") or "") != completion_commit_digest(commit):
        return "completion_commit digest mismatch"
    identity = commit.get("task") if isinstance(commit.get("task"), Mapping) else {}
    for key, expected in (
        ("id", str(task.get("id") or "")),
        ("episode", normalize_episode(str(task.get("episode") or ""))),
        ("stage_key", str(task.get("stage_key") or "")),
        ("attempt", int(task.get("attempts") or 0)),
    ):
        if identity.get(key) != expected:
            return f"completion_commit task.{key} mismatch"
    if str(task.get("stage_key") or "") in PRODUCTION_EXECUTION_STAGES:
        attestation = commit.get("output_commit_attestation")
        if not isinstance(attestation, Mapping) or attestation.get("status") != "pass":
            return "completion_commit paid output attestation missing or failed"
        declared = str(attestation.get("digest") or "")
        calculated = _canonical_sha256({
            key: value for key, value in attestation.items() if key != "digest"
        })
        if not _sha256_value(declared) or declared != calculated:
            return "completion_commit paid output attestation digest mismatch"
    return None


def _canonical_acceptance_issue(queue: Mapping[str, Any], task: Mapping[str, Any]) -> Optional[str]:
    """Delegate review completion to the one canonical acceptance contract."""
    root = str(queue.get("root") or "").strip()
    episode = normalize_episode(str(task.get("episode") or ""))
    if not root or not episode:
        return "queue root/episode missing; cannot check canonical acceptance"
    try:
        header, rows = parse_progress(root)
    except Exception as exc:
        return f"progress unavailable for acceptance check: {exc}"
    if "验收" not in header:
        return "progress acceptance column missing"
    progress_row = next(
        (
            row for row in rows
            if normalize_episode(str(row.get("_ep") or row.get("集") or "")) == episode
        ),
        None,
    )
    if progress_row is None:
        return f"progress row missing for {episode}"
    if acceptance_contract is None:
        return "canonical acceptance_contract unavailable"
    try:
        result = acceptance_contract.check_acceptance(Path(root).resolve(), episode)
    except Exception as exc:
        return f"canonical acceptance check failed: {type(exc).__name__}: {exc}"
    decision = str(result.get("decision") or "").strip().lower() if isinstance(result, Mapping) else ""
    if not isinstance(result, Mapping) or result.get("status") != "pass" or result.get("valid") is not True:
        issues = result.get("issues") if isinstance(result, Mapping) else None
        detail = "; ".join(str(item) for item in (issues or [])[:4])
        return "canonical acceptance receipt not pass" + (f": {detail}" if detail else "")
    allowed = getattr(acceptance_contract, "ALLOWED_DECISIONS", {"approved", "accepted"})
    if decision not in allowed:
        return f"canonical acceptance decision invalid: {decision or 'missing'}"
    if not is_progress_satisfied(root, progress_row, "验收"):
        return f"progress acceptance not done for {episode}"
    return None


def _failed_before_paid_boundary(runner: Optional[Mapping[str, Any]]) -> bool:
    """Only explicit preflight/config failures prove that no paid command started."""
    if not isinstance(runner, Mapping) or runner.get("execution_started") is not False:
        return False
    error_class = str(runner.get("error_class") or "")
    return error_class in {"preflight_block", "configuration"}


def mark_task(queue: Dict[str, Any], task_id_value: str, status: str, note: str = "",
              *, expected_worker: Optional[str] = None,
              expected_attempt: Optional[int] = None,
              runner: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
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
    requested_status = status
    if status == "pass":
        # done 是 canonical commit，不是“命令返回了 0”。完成硬度直接由 stage contract
        # 推导；review 还必须有绑定母版 SHA 的人工 acceptance receipt。
        policy = _completion_policy(task)
        evidence_runner: Optional[Mapping[str, Any]] = runner if isinstance(runner, Mapping) else None
        if (
            evidence_runner is None
            and policy["acceptance_required"]
            and task.get("status") == "qa_blocked"
            and task.get("completion_block_reason") == "needs_acceptance_signoff"
            and isinstance(task.get("last_runner"), Mapping)
        ):
            evidence_runner = task.get("last_runner")
        completion = evidence_runner.get("completion") if isinstance(evidence_runner, Mapping) else None
        acceptance_snapshot: Optional[Mapping[str, Any]] = None
        output_commit_attestation: Optional[Mapping[str, Any]] = None
        if policy["hard"]:
            runner_issue = _runner_completion_issue(queue, task, evidence_runner, policy)
            if runner_issue:
                raise ValueError(f"task {task_id_value} cannot be marked done: {runner_issue}")
            output_check = completion.get("output_verification") if isinstance(completion, Mapping) else None
            post_gate = completion.get("post_gate") if isinstance(completion, Mapping) else None
            output_ok = isinstance(output_check, Mapping) and output_check.get("status") == "pass"
            gate_status = post_gate.get("status") if isinstance(post_gate, Mapping) else None
            gate_ok = gate_status == "pass" if policy["gate_required"] else gate_status in {"pass", "not_applicable"}
            if not output_ok or not gate_ok:
                raise ValueError(
                    f"task {task_id_value} cannot be marked done without "
                    "output_verification=pass and post_gate=pass/not_applicable"
                )
            if str(task.get("stage_key") or "") in PRODUCTION_EXECUTION_STAGES:
                safe_local = (
                    str(task.get("stage_key") or "") == "compose"
                    and isinstance(completion, Mapping)
                    and completion.get("safe_local_execution") is True
                )
                if safe_local:
                    output_commit_attestation = {
                        "status": "pass",
                        "mode": "safe_local_compose",
                        "output_verification": deepcopy(dict(completion.get("output_verification") or {})),
                    }
                    output_commit_attestation["digest"] = _canonical_sha256(
                        output_commit_attestation
                    )
                else:
                    output_commit_attestation = _paid_output_commit_attestation(
                        queue, task, evidence_runner
                    )
                if output_commit_attestation.get("status") != "pass":
                    details = "; ".join(
                        str(item) for item in (output_commit_attestation.get("issues") or [])[:5]
                    )
                    note = (
                        "paid outputs changed after runner verification"
                        + (f": {details}" if details else "")
                    )
                    if isinstance(evidence_runner, Mapping):
                        task["last_runner"] = deepcopy(dict(evidence_runner))
                    task["last_output_commit_attestation"] = deepcopy(
                        dict(output_commit_attestation)
                    )
                    task["status"] = "qa_blocked"
                    task["completion_block_reason"] = "output_changed_before_commit"
                    task["last_error_class"] = "preflight_block"
                    reservation = task.get("budget_reservation")
                    if isinstance(reservation, Mapping) and reservation.get("status") == "reserved":
                        settlement_issue = settle_task_budget(queue, task, evidence_runner)
                        if settlement_issue:
                            note += f"; budget settlement issue: {settlement_issue}"
                    status = "qa_blocked"
            if status == "pass" and policy["acceptance_required"]:
                acceptance_issue = _canonical_acceptance_issue(queue, task)
                if acceptance_issue:
                    # Review execution is complete, but human acceptance is a separate boundary.
                    # Persist the verified command/output/gate receipt and leave running so no
                    # worker lease is held. After the human issues the canonical receipt, a plain
                    # mark(pass) reuses this evidence and atomically reconciles to done without
                    # executing the review command again.
                    if isinstance(evidence_runner, Mapping):
                        task["last_runner"] = deepcopy(dict(evidence_runner))
                    task["status"] = "qa_blocked"
                    task["completion_block_reason"] = "needs_acceptance_signoff"
                    task["acceptance_issue"] = acceptance_issue
                    task["last_error_class"] = "preflight_block"
                    task.pop("dead_letter", None)
                    task.pop("dead_letter_at", None)
                    status = "qa_blocked"
                    note = (
                        "needs_acceptance_signoff: canonical review evidence persisted; "
                        f"{acceptance_issue}"
                    )
                else:
                    acceptance_snapshot = acceptance_contract.check_acceptance(
                        Path(str(queue.get("root") or "")).resolve(),
                        normalize_episode(str(task.get("episode") or "")),
                    )
        if status == "qa_blocked":
            # Do not continue into production settlement/done below. Review is non-production;
            # this branch simply releases the worker lease at the common tail.
            pass
        elif str(task.get("stage_key") or "") in PRODUCTION_EXECUTION_STAGES:
            reservation = task.get("budget_reservation")
            if not isinstance(reservation, Mapping) or reservation.get("status") != "reserved":
                raise ValueError(
                    f"production task {task_id_value} cannot be marked done without active atomic budget reservation"
                )
            settlement_issue = settle_task_budget(queue, task, evidence_runner)
            if settlement_issue:
                status = "qa_blocked"
                note = f"budget settlement blocked canonical completion: {settlement_issue}"
        if status == "pass":
            task["status"] = "done"
            if policy["hard"] and isinstance(evidence_runner, Mapping):
                task["last_runner"] = deepcopy(dict(evidence_runner))
                task["completion_commit"] = build_completion_commit(
                    task,
                    evidence_runner,
                    acceptance=acceptance_snapshot,
                    output_attestation=output_commit_attestation,
                )
            for key in (
                "last_error_class",
                "dead_letter",
                "dead_letter_at",
                "completion_block_reason",
                "acceptance_issue",
                "last_output_commit_attestation",
            ):
                task.pop(key, None)
        elif status != "qa_blocked":
            task["status"] = "qa_blocked"
            task["last_error_class"] = "budget"
            task.pop("dead_letter", None)
            task.pop("dead_letter_at", None)
    elif status == "fail":
        task.pop("completion_commit", None)
        if str(task.get("stage_key") or "") in PRODUCTION_EXECUTION_STAGES:
            reservation = task.get("budget_reservation")
            if isinstance(reservation, Mapping) and reservation.get("status") == "reserved":
                if _failed_before_paid_boundary(runner):
                    release_task_budget(queue, task, "pre_paid_boundary_failure")
                else:
                    settlement_issue = settle_task_budget(queue, task, runner)
                    if settlement_issue:
                        note = f"{note}; conservative budget settlement: {settlement_issue}" if note else settlement_issue
        else:
            release_task_budget(queue, task, "runner_fail_nonproduction")
        attempts = int(task.get("attempts") or 0)
        max_retries = resolve_max_retries(task, queue)
        task["last_error_class"] = classify_error(note, runner)
        task["status"] = "retry_queued" if attempts <= max_retries else "failed"
        if task["status"] == "failed":
            task["dead_letter"] = True
            task["dead_letter_at"] = now_iso()
    elif status == "qa_blocked":
        task.pop("completion_commit", None)
        # 命令和产物可以已成功，但后置 gate 未通过/无法运行。保留为可人工修复后
        # requeue 的非终态，不消耗普通 command retry，也绝不能计入 done。
        # Gate BLOCK follows a successful command/output pass, so the paid attempt is settled
        # even though canonical completion is withheld. External receipt reconciliation may not
        # have a local reservation; that path simply remains qa_blocked.
        reservation = task.get("budget_reservation")
        if isinstance(reservation, Mapping) and reservation.get("status") == "reserved":
            settlement_issue = settle_task_budget(queue, task, runner)
            if settlement_issue:
                note = f"{note}; budget settlement issue: {settlement_issue}" if note else settlement_issue
        task["status"] = "qa_blocked"
        task["last_error_class"] = "preflight_block"
        task.pop("dead_letter", None)
        task.pop("dead_letter_at", None)
    elif status == "provider_pending":
        task.pop("completion_commit", None)
        if task.get("status") != "running" or str(task.get("stage_key") or "") != "video":
            raise ValueError("provider_pending is only valid for a claimed video task")
        checkpoint = provider_submission_state(queue, task)
        if checkpoint.get("state") != "provider_pending" or not checkpoint.get("provider_submit_id"):
            raise ValueError(
                "provider_pending requires a durable manifest submit_id; unknown paid state must block"
            )
        reservation = task.get("budget_reservation")
        if not isinstance(reservation, Mapping) or reservation.get("status") != "reserved":
            raise ValueError("provider_pending video task must retain its original budget reservation")
        task["status"] = "provider_pending"
        task["provider_job"] = checkpoint
        if isinstance(runner, Mapping):
            task["last_runner"] = deepcopy(dict(runner))
        task["last_error_class"] = "provider_pending"
        task.pop("dead_letter", None)
        task.pop("dead_letter_at", None)
    elif status in {"queued", "blocked_budget", "cancelled"}:
        task.pop("completion_commit", None)
        if (
            task.get("status") == "running"
            and str(task.get("stage_key") or "") in PRODUCTION_EXECUTION_STAGES
            and not _failed_before_paid_boundary(runner)
        ):
            raise ValueError(
                f"running production task {task_id_value} cannot transition to {status} without "
                "structured execution_started=false preflight/config evidence; mark fail to settle "
                "a possibly-spent attempt"
            )
        release_task_budget(queue, task, f"mark:{status}")
        task["status"] = status
    elif status == "running":
        raise ValueError("running is claim-only; use queue claim so lease and atomic budget reservation are created")
    else:
        raise ValueError(f"unknown mark status: {status}")
    if task["status"] != "running":  # 离开 running 即释放租约，便于回收/并发统计
        _clear_lease(task)
    task["updated_at"] = now_iso()
    task.setdefault("history", []).append({
        "ts": now_iso(),
        "action": f"mark:{status}",
        "requested_status": requested_status,
        "note": note,
    })
    if note:
        task["last_note"] = note
    refresh_runtime_budget(queue)
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
    elif ns.from_consistency_ledger:
        with open(ns.from_consistency_ledger, encoding="utf-8") as fh:
            ledger_report = json.load(fh)
        tasks = tasks_from_consistency_ledger(
            root,
            ledger_report,
            cost_estimates=estimates,
            max_retries=ns.max_retries,
            episodes=selected,
        )
    elif ns.from_shooting_schedule:
        schedule_path = ns.from_shooting_schedule
        if not os.path.isabs(schedule_path):
            schedule_path = os.path.join(root, schedule_path)
        with open(schedule_path, encoding="utf-8") as fh:
            schedule_payload = json.load(fh)
        tasks = tasks_from_shooting_schedule(
            root,
            schedule_payload,
            cost_estimates=estimates,
            max_retries=ns.max_retries,
            episodes=selected,
        )
    elif ns.from_events:
        tasks = tasks_from_production_events(
            root,
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
    try:
        claimed = claim(
            ns.root.rstrip("/"),
            limit=ns.limit,
            worker=ns.worker or default_worker(),
            lease_seconds=ns.lease_seconds,
        )
    except (FileNotFoundError, TimeoutError, ValueError, RuntimeError) as exc:
        payload = {
            "kind": "n2d_batch_claim_result",
            "version": 1,
            "status": "blocked",
            "fail_closed": True,
            "claimed": [],
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        print(f"claim blocked ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 2
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


def cmd_heartbeat(ns: argparse.Namespace) -> int:
    n = renew(
        ns.root.rstrip("/"),
        ns.task_id,
        ns.lease_seconds,
        ns.worker or None,
    )
    print(json.dumps({"renewed": n, "task_ids": ns.task_id}, ensure_ascii=False, indent=2))
    return 0 if n else 1


def cmd_status(ns: argparse.Namespace) -> int:
    queue = load_queue(ns.root.rstrip("/"))
    print(render_markdown(queue) if ns.markdown else json.dumps(queue.get("summary", {}), ensure_ascii=False, indent=2))
    return 0


def cmd_coordination_status(ns: argparse.Namespace) -> int:
    status = coordination_backend_status(ns.root.rstrip("/"))
    print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if status.get("status") in {"ok", "warn"} else 1


def cmd_sqlite_doctor(ns: argparse.Namespace) -> int:
    payload = sqlite_doctor(ns.root.rstrip("/"), write=ns.write)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_sqlite_doctor(payload))
    return 1 if payload.get("status") == "fail" else 0


def normalize_job_status(value: str) -> str:
    status = str(value or "").strip().lower()
    aliases = {
        "success": "succeeded",
        "done": "succeeded",
        "pass": "succeeded",
        "ok": "succeeded",
        "error": "failed",
        "fail": "failed",
        "cancel": "cancelled",
        "canceled": "cancelled",
    }
    return aliases.get(status, status or "unknown")


def append_job_receipt(root: str, receipt: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(production_dir(root), exist_ok=True)
    row = dict(receipt)
    row.setdefault("kind", "n2d_external_job_receipt")
    row.setdefault("version", 1)
    row.setdefault("updated_at", now_iso())
    row["status"] = normalize_job_status(str(row.get("status") or "unknown"))
    with open(job_receipts_path(root), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def load_job_receipts(root: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    path = job_receipts_path(root)
    receipts: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        return receipts, errors
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception as exc:
                errors.append({"line": lineno, "error": str(exc)})
                continue
            if not isinstance(item, dict):
                errors.append({"line": lineno, "error": "receipt line is not an object"})
                continue
            item["_line"] = lineno
            item["status"] = normalize_job_status(str(item.get("status") or "unknown"))
            receipts.append(item)
    return receipts, errors


def _receipt_matches(task: Dict[str, Any], receipt: Dict[str, Any]) -> bool:
    tid = str(task.get("id") or "")
    idem = str(task.get("idempotency_key") or "")
    return bool(
        (receipt.get("task_id") and str(receipt.get("task_id")) == tid)
        or (receipt.get("idempotency_key") and str(receipt.get("idempotency_key")) == idem)
    )


def latest_matching_receipt(task: Dict[str, Any], receipts: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    matches = [item for item in receipts if _receipt_matches(task, item)]
    if not matches:
        return None
    return sorted(matches, key=lambda item: (str(item.get("updated_at") or ""), int(item.get("_line") or 0)))[-1]


def reconcile_jobs(root: str, *, apply: bool = False) -> Dict[str, Any]:
    receipts, errors = load_job_receipts(root)
    with queue_lock(root):
        queue = load_queue(root)
        matches: List[Dict[str, Any]] = []
        actions: List[Dict[str, Any]] = []
        for task in queue.get("tasks", []):
            receipt = latest_matching_receipt(task, receipts)
            if not receipt:
                if task.get("status") == "running" and task.get("external_job_id"):
                    actions.append({
                        "task_id": task.get("id"),
                        "action": "warn",
                        "reason": "running task has external_job_id but no receipt",
                    })
                continue
            status = str(receipt.get("status") or "unknown")
            match = {
                "task_id": task.get("id"),
                "idempotency_key": task.get("idempotency_key"),
                "task_status": task.get("status"),
                "receipt_status": status,
                "external_job_id": receipt.get("external_job_id") or receipt.get("job_id") or "",
                "receipt_line": receipt.get("_line"),
            }
            if status == "succeeded" and task.get("status") in {"queued", "retry_queued", "running"}:
                # 外部 job success 只证明远端命令完成，不能替代本地产物校验和后置
                # gate。先停在 qa_blocked，随后由 runner/reconcile workflow 校验后提交 done。
                match["proposed_mark"] = "qa_blocked"
                if apply:
                    mark_task(
                        queue,
                        str(task["id"]),
                        "qa_blocked",
                        "job_reconcile: external job succeeded; awaiting output verification and post gate",
                        runner={"job_receipt": receipt},
                    )
            elif status in {"failed", "cancelled"} and task.get("status") in {"queued", "retry_queued", "running"}:
                match["proposed_mark"] = "fail"
                if apply:
                    mark_task(queue, str(task["id"]), "fail", f"job_reconcile: external job {status}", runner={"job_receipt": receipt})
            elif status in {"submitted", "running"} and task.get("status") != "running":
                match["proposed_mark"] = "none"
                match["warning"] = "external job still active but queue task is not running"
            matches.append(match)
        payload = {
            "kind": "n2d_job_reconcile",
            "version": 1,
            "root": root,
            "applied": apply,
            "receipt_count": len(receipts),
            "receipt_errors": errors,
            "matches": matches,
            "actions": actions,
            "summary": {
                "matched": len(matches),
                "proposed_pass": sum(1 for item in matches if item.get("proposed_mark") == "pass"),
                "proposed_qa_blocked": sum(1 for item in matches if item.get("proposed_mark") == "qa_blocked"),
                "proposed_fail": sum(1 for item in matches if item.get("proposed_mark") == "fail"),
                "warnings": len(actions) + sum(1 for item in matches if item.get("warning")),
            },
            "status": "fail" if errors else "warn" if actions or any(item.get("warning") for item in matches) else "pass",
            "generated_at": now_iso(),
        }
        if apply:
            save_queue(root, queue)
        write_job_reconcile(root, payload)
        return payload


def render_job_reconcile(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d Job Reconcile",
        "",
        f"- 状态：{payload.get('status')}",
        f"- applied：{payload.get('applied')}",
        f"- receipts：{payload.get('receipt_count')}",
        f"- matched：{(payload.get('summary') or {}).get('matched', 0)}",
        "",
        "## Matches",
        "",
        "| task | queue | receipt | proposed | external job |",
        "|---|---|---|---|---|",
    ]
    for item in payload.get("matches") or []:
        lines.append(
            f"| {item.get('task_id')} | {item.get('task_status')} | {item.get('receipt_status')} | "
            f"{item.get('proposed_mark', '—')} | {item.get('external_job_id') or '—'} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_job_reconcile(root: str, payload: Dict[str, Any]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    with open(job_reconcile_path(root), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(production_dir(root), JOB_RECONCILE_MD), "w", encoding="utf-8") as fh:
        fh.write(render_job_reconcile(payload))


def cmd_job_receipt(ns: argparse.Namespace) -> int:
    receipt = append_job_receipt(ns.root.rstrip("/"), {
        "task_id": ns.task_id or "",
        "idempotency_key": ns.idempotency_key or "",
        "external_job_id": ns.external_job_id or "",
        "stage_key": ns.stage_key or "",
        "episode": ns.episode or "",
        "status": ns.status,
        "note": ns.note or "",
    })
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_reconcile_jobs(ns: argparse.Namespace) -> int:
    payload = reconcile_jobs(ns.root.rstrip("/"), apply=ns.apply)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_job_reconcile(payload))
    return 1 if payload.get("status") == "fail" else 0


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
    plan.add_argument("--strategy", default="default", choices=["default", "front-light"], help="Batch planning strategy (e.g. 'front-light' to defer heavy render until Ep 1 style locked)")
    plan.add_argument("--rerun-from", help="stage key/alias for targeted rerun")
    plan.add_argument("--from-asset-impact",
                      help="读 n2d-image asset_impact.py --output-batch-tasks 的 JSON（kind=n2d_asset_rerun_plan），直接建受影响重跑任务")
    plan.add_argument("--from-consistency-findings",
                      help="读 n2d-review consistency_findings_*.json（kind=n2d_consistency_findings），直接建审查返工任务")
    plan.add_argument("--from-consistency-ledger",
                      help="读 n2d-review consistency_ledger_*.json（kind=n2d_consistency_ledger），按 root_causes 直接建审查返工任务")
    plan.add_argument("--from-events", action="store_true",
                      help="从 生产数据/production_events.jsonl 收集未被后续 pass 承接的 generation/redraw fail，生成重试任务")
    plan.add_argument("--from-shooting-schedule",
                      help="读 n2d-script P-3 ai_shooting_schedule 或生产数据/ai_shooting_schedule_batch_seed_*.json，建按 Clip 排序的 image/video 队列任务")
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
    mark.add_argument("--status", required=True, choices=["pass", "fail", "queued", "running", "qa_blocked", "blocked_budget", "cancelled"])
    mark.add_argument("--note")
    mark.add_argument("--worker", help="optional expected worker guard; used by runners to avoid stale marks")
    mark.add_argument("--attempt", type=int, help="optional expected attempt guard; used by runners to avoid stale marks")
    mark.set_defaults(func=cmd_mark)

    reclaim_cmd = sub.add_parser("reclaim", help="回收过期租约的 running 任务 → retry_queued/failed（断点恢复）")
    reclaim_cmd.add_argument("root")
    reclaim_cmd.add_argument("--worker", help="配合 --force-worker：回收该 worker 残留的 running")
    reclaim_cmd.add_argument("--force-worker", action="store_true", help="强制回收 --worker 的 running（不等租约过期；本 worker 重启自愈用）")
    reclaim_cmd.set_defaults(func=cmd_reclaim)

    heartbeat = sub.add_parser("heartbeat", help="续租 running 任务 lease（长任务 worker 心跳）")
    heartbeat.add_argument("root")
    heartbeat.add_argument("task_id", nargs="+")
    heartbeat.add_argument("--worker", help="optional expected worker guard")
    heartbeat.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)
    heartbeat.set_defaults(func=cmd_heartbeat)

    status = sub.add_parser("status", help="print queue status")
    status.add_argument("root")
    status.add_argument("--markdown", action="store_true")
    status.set_defaults(func=cmd_status)

    coord = sub.add_parser("coordination-status", help="print queue coordination backend/lock mode")
    coord.add_argument("root")
    coord.set_defaults(func=cmd_coordination_status)

    sqlite_doc = sub.add_parser("sqlite-doctor", help="check SQLite coordination DB and JSON mirror consistency")
    sqlite_doc.add_argument("root")
    sqlite_doc.add_argument("--write", action="store_true")
    sqlite_doc.add_argument("--json", action="store_true")
    sqlite_doc.set_defaults(func=cmd_sqlite_doctor)

    receipt = sub.add_parser("job-receipt", help="append an external generation job receipt for later reconcile")
    receipt.add_argument("root")
    receipt.add_argument("--task-id")
    receipt.add_argument("--idempotency-key")
    receipt.add_argument("--external-job-id")
    receipt.add_argument("--stage-key")
    receipt.add_argument("--episode")
    receipt.add_argument("--status", required=True, choices=["submitted", "running", "succeeded", "failed", "cancelled", "success", "done", "pass", "fail", "error"])
    receipt.add_argument("--note")
    receipt.set_defaults(func=cmd_job_receipt)

    rec_jobs = sub.add_parser("reconcile-jobs", help="reconcile batch queue tasks from external job receipts")
    rec_jobs.add_argument("root")
    rec_jobs.add_argument("--apply", action="store_true", help="apply pass/fail marks to matched tasks")
    rec_jobs.add_argument("--json", action="store_true")
    rec_jobs.set_defaults(func=cmd_reconcile_jobs)

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
