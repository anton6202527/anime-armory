#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local batch queue for novel production tasks.

The queue is intentionally file-backed and VCS-free. It is safe for single-machine
multi-worker use through flock + atomic replace. The JSON file remains the
portable source of truth; workers only claim tasks through this script.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - macOS/Linux project tool
    fcntl = None
try:
    import resource
except Exception:  # pragma: no cover - resource is POSIX-only
    resource = None


QUEUE_KIND = "novel_batch_queue"
QUEUE_SCHEMA_VERSION = 1
RUN_ARTIFACT_KIND = "novel_batch_task_run"
FINAL_STATUSES = {"completed", "failed", "dead_letter", "skipped"}
CLAIMABLE_STATUSES = {"pending", "retry_queued"}
DEFAULT_MAX_LOG_BYTES = int(os.environ.get("NOVEL_BATCH_MAX_LOG_BYTES", "262144"))
DEFAULT_SNAPSHOT_INCLUDE = (
    "_meta.json",
    "_设置.md",
    "_进度.md",
    "章节/",
    "导出/",
    "审稿/",
    "评分/",
    "修订/",
    "合规/",
    "资料/",
    "素材/",
    "设定/",
    "写作任务/",
    "语义任务/",
    "生产数据/",
)
DEFAULT_SNAPSHOT_EXCLUDE = (
    "生产数据/batch_runs/",
    "生产数据/novel_batch_queue.json",
    "生产数据/novel_batch_queue.json.lock",
    "生产数据/novel_dashboard_history.jsonl",
    "__pycache__/",
    ".pytest_cache/",
    "*.lock",
)
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|authorization|bearer|token|password|secret)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CRAFT_SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "..", "novel-craft", "scripts"))
if CRAFT_SCRIPTS not in sys.path:
    sys.path.insert(0, CRAFT_SCRIPTS)

try:
    from provenance import append_event
except Exception:  # pragma: no cover - provenance is additive
    append_event = None

ALLOWED_COMMAND_SCRIPTS = (
    "skills/novel-review/scripts/reader_contract_sentry.py",
    "skills/novel-review/scripts/consistency_audit.py",
    "skills/novel-review/scripts/build_review_report.py",
    "skills/novel-score/scripts/score.py",
    "skills/novel-score/scripts/collect_market_baseline.py",
    "skills/novel-craft/scripts/revision_planner.py",
    "skills/novel-dashboard/scripts/dashboard.py",
)


def now_ts() -> float:
    return time.time()


def iso(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or now_ts(), timezone.utc).isoformat(timespec="seconds")


def parse_chapters(value: str) -> list[int]:
    chapters: set[int] = set()
    for part in re.split(r"\s*,\s*", value.strip()):
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
            if end < start:
                raise ValueError(f"invalid chapter range: {part}")
            chapters.update(range(start, end + 1))
        else:
            chapters.add(int(part))
    return sorted(chapters)


def stable_task_id(kind: str, chapter: int | None, command: str, scope: str = "") -> str:
    key = f"{kind}|{chapter or ''}|{scope}|{command}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]
    if chapter is not None:
        return f"{kind}_ch{chapter:02d}_{digest}"
    return f"{kind}_{digest}"


def safe_component(value: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", str(value or "").strip())
    return safe.strip("._") or "task"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def render_template(
    template: str,
    root: str,
    chapter: int | None,
    task_id: str,
    extra: dict[str, Any] | None = None,
) -> str:
    chapter_label = f"第{chapter:02d}章" if chapter is not None else ""
    values = {
        "root": root,
        "chapter": chapter or "",
        "chapter_label": chapter_label,
        "task_id": task_id,
    }
    values.update(extra or {})
    return template.format(**values)


def default_command_template(kind: str) -> str:
    if kind == "review":
        return (
            "python3 skills/novel-review/scripts/reader_contract_sentry.py "
            "\"{root}\" --chapter {chapter_label}"
        )
    if kind == "score":
        return "python3 skills/novel-score/scripts/score.py \"{root}\" --scope chapter --chapter {chapter}"
    if kind == "revision":
        return "python3 skills/novel-craft/scripts/revision_planner.py \"{root}\""
    if kind == "dashboard":
        return "python3 skills/novel-dashboard/scripts/dashboard.py \"{root}\" --write"
    if kind == "market_evidence":
        return (
            "python3 skills/novel-score/scripts/collect_market_baseline.py "
            "\"{root}/评分\" --target-platform \"{target_platform}\" --allow-fetch-errors"
        )
    return "echo \"manual task {task_id}\""


def command_argv(command: str, *, allow_manual: bool = False) -> list[str]:
    """Parse and allowlist a queued command without invoking a shell."""
    argv = shlex.split(str(command or ""))
    if not argv:
        raise ValueError("empty command")
    if allow_manual:
        return argv
    python_bins = {"python", "python3", os.path.basename(sys.executable)}
    if os.path.basename(argv[0]) not in python_bins:
        raise ValueError("command runner only allows Python skill scripts unless --allow-manual is set")
    if len(argv) < 2:
        raise ValueError("python command is missing script path")
    script = argv[1].replace(os.sep, "/")
    if script.startswith("./"):
        script = script[2:]
    if script not in ALLOWED_COMMAND_SCRIPTS:
        raise ValueError(f"script is not in novel-batch allowlist: {argv[1]}")
    return argv


def tail_text(text: str, limit: int = 4000) -> str:
    text = redact_log(text or "")
    return text[-limit:] if len(text) > limit else text


def byte_len(text: str) -> int:
    return len(str(text or "").encode("utf-8", errors="replace"))


def redact_log(text: str) -> str:
    out = str(text or "")
    for pattern in SECRET_PATTERNS:
        out = pattern.sub(lambda m: f"{m.group(1)}=<redacted>" if m.lastindex and m.lastindex >= 1 else "<redacted>", out)
    return out


def truncate_log(text: str, max_bytes: int) -> tuple[str, bool]:
    if max_bytes < 0:
        return text, False
    data = text.encode("utf-8", errors="replace")
    if len(data) <= max_bytes:
        return text, False
    marker = f"\n[novel-batch log truncated to last {max_bytes} bytes]\n"
    marker_bytes = marker.encode("utf-8")
    keep = max(0, max_bytes - len(marker_bytes))
    clipped = marker_bytes + data[-keep:] if keep else marker_bytes
    return clipped.decode("utf-8", errors="replace"), True


def sanitize_log(text: str, *, max_bytes: int, full_log: bool, redact: bool = True) -> tuple[str, dict[str, Any]]:
    original = str(text or "")
    sanitized = redact_log(original) if redact else original
    written, truncated = (sanitized, False) if full_log else truncate_log(sanitized, max_bytes)
    return written, {
        "original_bytes": byte_len(original),
        "written_bytes": byte_len(written),
        "truncated": truncated,
        "redacted": redact,
        "max_log_bytes": None if full_log else max_bytes,
    }


def usage_snapshot() -> dict[str, Any]:
    if resource is None:
        return {}
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "child_user_cpu_sec": float(ru.ru_utime),
        "child_system_cpu_sec": float(ru.ru_stime),
        "child_max_rss_kb": int(ru.ru_maxrss),
    }


def usage_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    if not before or not after:
        return {}
    return {
        "child_user_cpu_sec": round(float(after.get("child_user_cpu_sec") or 0) - float(before.get("child_user_cpu_sec") or 0), 6),
        "child_system_cpu_sec": round(float(after.get("child_system_cpu_sec") or 0) - float(before.get("child_system_cpu_sec") or 0), 6),
        "child_max_rss_kb": int(after.get("child_max_rss_kb") or 0),
    }


def path_matches(rel_path: str, patterns: tuple[str, ...] | list[str]) -> bool:
    rel_path = rel_path.strip("/")
    for pattern in patterns:
        pat = str(pattern or "").strip()
        if not pat:
            continue
        pat = pat.replace(os.sep, "/")
        is_dir_pattern = pat.endswith("/")
        pat = pat.strip("/")
        if is_dir_pattern:
            if rel_path == pat or rel_path.startswith(pat + "/"):
                return True
            continue
        if fnmatch.fnmatch(rel_path, pat) or rel_path == pat:
            return True
    return False


def relpath(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


class NovelBatchQueue:
    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self.queue_file = os.path.join(self.root_dir, "生产数据", "novel_batch_queue.json")
        self.lock_file = self.queue_file + ".lock"
        os.makedirs(os.path.dirname(self.queue_file), exist_ok=True)

    @contextmanager
    def locked(self):
        if fcntl is None:
            raise RuntimeError("fcntl is required for the local file coordination backend")
        os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
        with open(self.lock_file, "a+", encoding="utf-8") as lockf:
            fcntl.flock(lockf, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lockf, fcntl.LOCK_UN)

    def empty_queue(self) -> dict[str, Any]:
        return {
            "schema_version": QUEUE_SCHEMA_VERSION,
            "kind": QUEUE_KIND,
            "project_root": self.root_dir,
            "created_at": iso(),
            "updated_at": iso(),
            "coordination": {
                "backend": "local_file",
                "lock_file": os.path.relpath(self.lock_file, self.root_dir).replace(os.sep, "/"),
                "multi_machine_safe": False,
            },
            "budget": {"max_tasks": None, "planned_tasks": 0, "completed_tasks": 0, "failed_tasks": 0},
            "tasks": [],
            "events": [],
        }

    def read_queue(self) -> dict[str, Any]:
        if not os.path.exists(self.queue_file):
            return self.empty_queue()
        with open(self.queue_file, encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict) or payload.get("kind") != QUEUE_KIND:
            raise ValueError(f"not a novel batch queue: {self.queue_file}")
        payload.setdefault("tasks", [])
        payload.setdefault("events", [])
        payload.setdefault("budget", {})
        return payload

    def write_queue(self, data: dict[str, Any]) -> None:
        data["updated_at"] = iso()
        tmp = f"{self.queue_file}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, self.queue_file)

    def provenance(self, event_type: str, *, metadata: dict[str, Any] | None = None) -> None:
        if not append_event:
            return
        append_event(
            self.root_dir,
            event_type=event_type,
            tool="novel-batch/scripts/queue.py",
            outputs=[self.queue_file],
            metadata=metadata or {},
        )

    def event(self, queue: dict[str, Any], event_type: str, **payload: Any) -> None:
        events = queue.setdefault("events", [])
        events.append({"at": iso(), "event_type": event_type, **payload})
        if len(events) > 200:
            del events[:-200]

    def upsert_tasks(self, tasks: list[dict[str, Any]], *, max_tasks: int | None = None) -> dict[str, Any]:
        with self.locked():
            queue = self.read_queue()
            by_key = {task.get("idempotency_key") or task["id"]: task for task in queue.get("tasks", [])}
            added = 0
            updated = 0
            for task in tasks:
                key = task.get("idempotency_key") or task["id"]
                if key in by_key:
                    existing = by_key[key]
                    preserve = {k: existing.get(k) for k in ("status", "attempts", "worker", "started_at", "completed_at", "last_error") if k in existing}
                    existing.update(task)
                    existing.update({k: v for k, v in preserve.items() if v not in (None, "")})
                    existing["updated_at"] = iso()
                    updated += 1
                else:
                    task.setdefault("status", "pending")
                    task.setdefault("attempts", 0)
                    task.setdefault("created_at", iso())
                    task.setdefault("updated_at", iso())
                    queue["tasks"].append(task)
                    by_key[key] = task
                    added += 1
            budget = queue.setdefault("budget", {})
            if max_tasks is not None:
                budget["max_tasks"] = max_tasks
            budget["planned_tasks"] = len(queue.get("tasks", []))
            self.event(queue, "tasks_planned", added=added, updated=updated)
            self.write_queue(queue)
            self.provenance("batch_tasks_planned", metadata={"added": added, "updated": updated, "task_count": len(queue.get("tasks", []))})
            return {"added": added, "updated": updated, "queue": queue}

    def claim_task(self, worker_id: str, *, lease_sec: int = 900, kinds: set[str] | None = None) -> dict[str, Any] | None:
        with self.locked():
            queue = self.read_queue()
            self._reclaim_expired_locked(queue)
            tasks = sorted(
                queue.get("tasks", []),
                key=lambda task: (int(task.get("priority_rank", 50)), task.get("created_at", ""), task.get("id", "")),
            )
            for task in tasks:
                if task.get("status") not in CLAIMABLE_STATUSES:
                    continue
                if kinds and task.get("kind") not in kinds:
                    continue
                max_retries = int(task.get("max_retries", 1))
                attempts = int(task.get("attempts") or 0)
                if attempts > max_retries:
                    task["status"] = "dead_letter"
                    task["updated_at"] = iso()
                    continue
                task["status"] = "running"
                task["worker"] = worker_id
                task["attempts"] = attempts + 1
                task["started_at"] = task.get("started_at") or iso()
                task["lease_expires_at"] = now_ts() + lease_sec
                task["lease_expires_at_iso"] = iso(task["lease_expires_at"])
                task["updated_at"] = iso()
                self.event(queue, "task_claimed", task_id=task.get("id"), worker=worker_id)
                self.write_queue(queue)
                self.provenance("batch_task_claimed", metadata={"task_id": task.get("id"), "worker": worker_id})
                return task
            self.write_queue(queue)
            return None

    def renew(self, task_id: str, worker_id: str, *, lease_sec: int = 900) -> dict[str, Any]:
        with self.locked():
            queue = self.read_queue()
            task = self._find_task(queue, task_id)
            self._require_worker(task, worker_id)
            if task.get("status") != "running":
                raise ValueError(f"task {task_id} is not running")
            task["lease_expires_at"] = now_ts() + lease_sec
            task["lease_expires_at_iso"] = iso(task["lease_expires_at"])
            task["updated_at"] = iso()
            self.event(queue, "task_renewed", task_id=task_id, worker=worker_id)
            self.write_queue(queue)
            self.provenance("batch_task_renewed", metadata={"task_id": task_id, "worker": worker_id})
            return task

    def mark(self, task_id: str, worker_id: str, status: str, *, error_class: str = "", message: str = "") -> dict[str, Any]:
        with self.locked():
            queue = self.read_queue()
            task = self._find_task(queue, task_id)
            self._require_worker(task, worker_id)
            if status in {"pass", "completed"}:
                task["status"] = "completed"
                task["completed_at"] = iso()
                task.pop("lease_expires_at", None)
                task.pop("lease_expires_at_iso", None)
                queue.setdefault("budget", {})["completed_tasks"] = self._count(queue, "completed")
                self.event(queue, "task_completed", task_id=task_id, worker=worker_id)
            elif status in {"fail", "failed"}:
                max_retries = int(task.get("max_retries", 1))
                attempts = int(task.get("attempts") or 0)
                task["last_error"] = {"class": error_class or "TaskFailed", "message": message, "at": iso()}
                if attempts <= max_retries:
                    task["status"] = "retry_queued"
                    task["worker"] = ""
                    task.pop("lease_expires_at", None)
                    task.pop("lease_expires_at_iso", None)
                    self.event(queue, "task_retry_queued", task_id=task_id, attempts=attempts)
                else:
                    task["status"] = "dead_letter"
                    task["completed_at"] = iso()
                    self.event(queue, "task_dead_lettered", task_id=task_id, attempts=attempts)
                queue.setdefault("budget", {})["failed_tasks"] = self._count(queue, "failed") + self._count(queue, "dead_letter")
            elif status == "skipped":
                task["status"] = "skipped"
                task["completed_at"] = iso()
                task["skip_reason"] = message
                task.pop("lease_expires_at", None)
                task.pop("lease_expires_at_iso", None)
                self.event(queue, "task_skipped", task_id=task_id, worker=worker_id, reason=message)
            else:
                raise ValueError(f"unsupported mark status: {status}")
            task["updated_at"] = iso()
            self.write_queue(queue)
            self.provenance(
                "batch_task_marked",
                metadata={
                    "task_id": task_id,
                    "worker": worker_id,
                    "status": task.get("status"),
                    "requested_status": status,
                    "error_class": error_class,
                },
            )
            return task

    def reclaim_expired(self) -> dict[str, Any]:
        with self.locked():
            queue = self.read_queue()
            reclaimed = self._reclaim_expired_locked(queue)
            if reclaimed:
                self.event(queue, "expired_leases_reclaimed", count=reclaimed)
            self.write_queue(queue)
            if reclaimed:
                self.provenance("batch_expired_leases_reclaimed", metadata={"reclaimed": reclaimed})
            return {"reclaimed": reclaimed, "queue": queue}

    def status(self) -> dict[str, Any]:
        with self.locked():
            queue = self.read_queue()
            self._reclaim_expired_locked(queue)
            summary: dict[str, int] = {}
            by_kind: dict[str, dict[str, int]] = {}
            for task in queue.get("tasks", []):
                status = str(task.get("status") or "unknown")
                kind = str(task.get("kind") or "manual")
                summary[status] = summary.get(status, 0) + 1
                by_kind.setdefault(kind, {})[status] = by_kind.setdefault(kind, {}).get(status, 0) + 1
            queue["summary"] = {"total": len(queue.get("tasks", [])), "by_status": summary, "by_kind": by_kind}
            self.write_queue(queue)
            return queue

    def run_one(
        self,
        worker_id: str,
        *,
        lease_sec: int = 900,
        kinds: set[str] | None = None,
        timeout_sec: int = 1800,
        allow_manual: bool = False,
        dry_run: bool = False,
        snapshot_include: list[str] | None = None,
        snapshot_exclude: list[str] | None = None,
        max_log_bytes: int = DEFAULT_MAX_LOG_BYTES,
        full_log: bool = False,
        redact_logs: bool = True,
    ) -> dict[str, Any]:
        task = self.claim_task(worker_id, lease_sec=lease_sec, kinds=kinds)
        if not task:
            return {"status": "empty"}
        before = self.output_snapshot(include_patterns=snapshot_include, exclude_patterns=snapshot_exclude)
        try:
            argv = command_argv(task.get("command") or "", allow_manual=allow_manual)
        except Exception as exc:
            payload = {"status": "command_not_allowed", "task_id": task["id"], "message": str(exc)}
            self.mark(task["id"], worker_id, "fail", error_class="CommandNotAllowed", message=str(exc))
            artifact_rel, _artifact = self.write_run_artifact(
                task,
                worker_id,
                payload,
                argv=[],
                stdout="",
                stderr=str(exc),
                before=before,
                after=self.output_snapshot(include_patterns=snapshot_include, exclude_patterns=snapshot_exclude),
                max_log_bytes=max_log_bytes,
                full_log=full_log,
                redact_logs=redact_logs,
                snapshot_policy=self.snapshot_policy(snapshot_include, snapshot_exclude),
            )
            payload["run_artifact"] = artifact_rel
            self.attach_run_artifact(task["id"], artifact_rel, {
                "status": payload["status"],
                "message": payload["message"],
            })
            self.provenance("batch_task_executed", metadata=payload)
            return payload
        if dry_run:
            payload = {"status": "dry_run", "task_id": task["id"], "argv": argv}
            self.mark(task["id"], worker_id, "skipped", message="dry-run")
            artifact_rel, _artifact = self.write_run_artifact(
                task,
                worker_id,
                payload,
                argv=argv,
                before=before,
                after=self.output_snapshot(include_patterns=snapshot_include, exclude_patterns=snapshot_exclude),
                max_log_bytes=max_log_bytes,
                full_log=full_log,
                redact_logs=redact_logs,
                snapshot_policy=self.snapshot_policy(snapshot_include, snapshot_exclude),
                resource_metrics={"elapsed_ms": 0, "timeout_sec": timeout_sec},
            )
            payload["run_artifact"] = artifact_rel
            self.attach_run_artifact(task["id"], artifact_rel, {
                "status": payload["status"],
                "returncode": None,
                "elapsed_ms": 0,
            })
            self.provenance("batch_task_executed", metadata=payload)
            return payload
        started = now_ts()
        usage_before = usage_snapshot()
        try:
            proc = subprocess.run(
                argv,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                timeout=timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = int((now_ts() - started) * 1000)
            usage_after = usage_snapshot()
            resource_metrics = {
                "elapsed_ms": elapsed_ms,
                "timeout_sec": timeout_sec,
                **usage_delta(usage_before, usage_after),
            }
            payload = {
                "status": "failed",
                "task_id": task["id"],
                "returncode": None,
                "elapsed_ms": elapsed_ms,
                "stdout_tail": tail_text(exc.stdout if isinstance(exc.stdout, str) else ""),
                "stderr_tail": tail_text(exc.stderr if isinstance(exc.stderr, str) else ""),
                "timeout_sec": timeout_sec,
                "resource_metrics": resource_metrics,
            }
            after = self.output_snapshot(include_patterns=snapshot_include, exclude_patterns=snapshot_exclude)
            self.mark(
                task["id"],
                worker_id,
                "fail",
                error_class="CommandTimeout",
                message=f"timeout_sec={timeout_sec}",
            )
            artifact_rel, _artifact = self.write_run_artifact(
                task,
                worker_id,
                payload,
                argv=argv,
                stdout=exc.stdout if isinstance(exc.stdout, str) else "",
                stderr=exc.stderr if isinstance(exc.stderr, str) else "",
                before=before,
                after=after,
                max_log_bytes=max_log_bytes,
                full_log=full_log,
                redact_logs=redact_logs,
                snapshot_policy=self.snapshot_policy(snapshot_include, snapshot_exclude),
                resource_metrics=resource_metrics,
            )
            payload["run_artifact"] = artifact_rel
            self.attach_run_artifact(task["id"], artifact_rel, {
                "status": payload["status"],
                "returncode": payload["returncode"],
                "elapsed_ms": payload["elapsed_ms"],
                "timeout_sec": timeout_sec,
            })
            self.provenance("batch_task_executed", metadata=payload)
            return payload
        elapsed_ms = int((now_ts() - started) * 1000)
        usage_after = usage_snapshot()
        resource_metrics = {
            "elapsed_ms": elapsed_ms,
            "timeout_sec": timeout_sec,
            **usage_delta(usage_before, usage_after),
        }
        payload = {
            "status": "completed" if proc.returncode == 0 else "failed",
            "task_id": task["id"],
            "returncode": proc.returncode,
            "elapsed_ms": elapsed_ms,
            "stdout_tail": tail_text(proc.stdout),
            "stderr_tail": tail_text(proc.stderr),
            "resource_metrics": resource_metrics,
        }
        after = self.output_snapshot(include_patterns=snapshot_include, exclude_patterns=snapshot_exclude)
        if proc.returncode == 0:
            self.mark(task["id"], worker_id, "pass")
        else:
            self.mark(
                task["id"],
                worker_id,
                "fail",
                error_class="CommandFailed",
                message=f"returncode={proc.returncode}; stderr_tail={payload['stderr_tail']}",
            )
        artifact_rel, artifact = self.write_run_artifact(
            task,
            worker_id,
            payload,
            argv=argv,
            stdout=proc.stdout,
            stderr=proc.stderr,
            before=before,
            after=after,
            max_log_bytes=max_log_bytes,
            full_log=full_log,
            redact_logs=redact_logs,
            snapshot_policy=self.snapshot_policy(snapshot_include, snapshot_exclude),
            resource_metrics=resource_metrics,
        )
        payload["run_artifact"] = artifact_rel
        payload["output_change_count"] = (
            int((artifact.get("output_artifacts") or {}).get("added_count") or 0)
            + int((artifact.get("output_artifacts") or {}).get("changed_count") or 0)
            + int((artifact.get("output_artifacts") or {}).get("removed_count") or 0)
        )
        self.attach_run_artifact(task["id"], artifact_rel, {
            "status": payload["status"],
            "returncode": payload["returncode"],
            "elapsed_ms": payload["elapsed_ms"],
            "output_change_count": payload["output_change_count"],
            "child_max_rss_kb": resource_metrics.get("child_max_rss_kb"),
        })
        self.provenance("batch_task_executed", metadata=payload)
        return payload

    def governance_report(self) -> dict[str, Any]:
        queue = self.status()
        tasks = queue.get("tasks", [])
        current = now_ts()
        dead = [task for task in tasks if task.get("status") == "dead_letter"]
        retry = [task for task in tasks if task.get("status") == "retry_queued"]
        expired_running = [
            task for task in tasks
            if task.get("status") == "running" and float(task.get("lease_expires_at") or 0) < current
        ]
        return {
            "schema_version": 1,
            "kind": "novel_batch_governance_report",
            "generated_at": iso(),
            "project_root": self.root_dir,
            "queue_path": self.queue_file,
            "summary": queue.get("summary") or {},
            "slo": {
                "dead_letter_count": len(dead),
                "retry_queued_count": len(retry),
                "expired_running_count": len(expired_running),
            },
            "run_artifacts": self.run_artifact_summary(),
            "dead_letter": dead,
            "retry_queued": retry,
            "expired_running": expired_running,
            "recommended_actions": self._governance_actions(dead, retry, expired_running),
        }

    def write_governance_report(self) -> tuple[str, str, dict[str, Any]]:
        report = self.governance_report()
        json_path = os.path.join(self.root_dir, "生产数据", "novel_batch_report.json")
        md_path = os.path.join(self.root_dir, "生产数据", "novel_batch_report.md")
        tmp = f"{json_path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, json_path)
        lines = [
            "# Novel Batch Governance Report",
            "",
            f"- generated_at: {report['generated_at']}",
            f"- dead_letter: {report['slo']['dead_letter_count']}",
            f"- retry_queued: {report['slo']['retry_queued_count']}",
            f"- expired_running: {report['slo']['expired_running_count']}",
            f"- run_artifacts: {(report.get('run_artifacts') or {}).get('count', 0)}",
            f"- run_status: {(report.get('run_artifacts') or {}).get('by_status') or {}}",
            "",
            "## Recommended Actions",
            "",
        ]
        actions = report.get("recommended_actions") or []
        lines.extend(f"- {item}" for item in actions) if actions else lines.append("- none")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        self.provenance("batch_governance_report_written", metadata={"json": json_path, "md": md_path, "dead_letter_count": report["slo"]["dead_letter_count"]})
        return json_path, md_path, report

    def _governance_actions(self, dead: list[dict[str, Any]], retry: list[dict[str, Any]], expired: list[dict[str, Any]]) -> list[str]:
        actions: list[str] = []
        if expired:
            actions.append("run `python3 skills/novel-batch/scripts/queue.py reclaim <作品根>` before claiming new work")
        if dead:
            actions.append("inspect dead-letter tasks and repair root cause before replanning")
        if retry:
            actions.append("claim retry_queued tasks after confirming the previous failure is transient")
        return actions

    def _reclaim_expired_locked(self, queue: dict[str, Any]) -> int:
        count = 0
        current = now_ts()
        for task in queue.get("tasks", []):
            if task.get("status") != "running":
                continue
            expires = float(task.get("lease_expires_at") or 0)
            if expires and expires < current:
                task["status"] = "retry_queued"
                task["worker"] = ""
                task["updated_at"] = iso()
                task["last_error"] = {"class": "LeaseExpired", "message": "worker lease expired", "at": iso()}
                task.pop("lease_expires_at", None)
                task.pop("lease_expires_at_iso", None)
                count += 1
        return count

    def _find_task(self, queue: dict[str, Any], task_id: str) -> dict[str, Any]:
        for task in queue.get("tasks", []):
            if task.get("id") == task_id:
                return task
        raise KeyError(f"unknown task id: {task_id}")

    def _require_worker(self, task: dict[str, Any], worker_id: str) -> None:
        owner = str(task.get("worker") or "")
        if owner and owner != worker_id:
            raise PermissionError(f"task {task.get('id')} is owned by worker {owner}, not {worker_id}")

    def _count(self, queue: dict[str, Any], status: str) -> int:
        return sum(1 for task in queue.get("tasks", []) if task.get("status") == status)

    @staticmethod
    def snapshot_policy(include_patterns: list[str] | None = None, exclude_patterns: list[str] | None = None) -> dict[str, Any]:
        return {
            "include": list(include_patterns or DEFAULT_SNAPSHOT_INCLUDE),
            "exclude": list(DEFAULT_SNAPSHOT_EXCLUDE) + list(exclude_patterns or []),
        }

    def output_snapshot(
        self,
        *,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Hash project files likely to be written by batch tasks.

        Queue internals and the run artifact directory are excluded so the diff
        describes task outputs, not scheduler bookkeeping.
        """
        snapshot: dict[str, dict[str, Any]] = {}
        policy = self.snapshot_policy(include_patterns, exclude_patterns)
        include = tuple(policy["include"])
        exclude = tuple(policy["exclude"])
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            rel_dir = relpath(self.root_dir, dirpath) if dirpath != self.root_dir else ""
            dirnames[:] = [
                name for name in dirnames
                if not path_matches(f"{rel_dir}/{name}/".strip("/"), exclude)
            ]
            for name in filenames:
                path = os.path.join(dirpath, name)
                rel = relpath(self.root_dir, path)
                if not path_matches(rel, include):
                    continue
                if path_matches(rel, exclude):
                    continue
                if not os.path.isfile(path):
                    continue
                snapshot[rel] = {
                    "path": rel,
                    "sha256": sha256_file(path),
                    "size_bytes": os.path.getsize(path),
                    "mtime": datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).isoformat(timespec="seconds"),
                }
        return snapshot

    @staticmethod
    def diff_snapshots(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> dict[str, Any]:
        added = [after[path] for path in sorted(after) if path not in before]
        changed = [
            {**after[path], "previous_sha256": before[path].get("sha256", "")}
            for path in sorted(after)
            if path in before and after[path].get("sha256") != before[path].get("sha256")
        ]
        removed = [before[path] for path in sorted(before) if path not in after]
        return {
            "added": added,
            "changed": changed,
            "removed": removed,
            "added_count": len(added),
            "changed_count": len(changed),
            "removed_count": len(removed),
        }

    def write_run_artifact(
        self,
        task: dict[str, Any],
        worker_id: str,
        payload: dict[str, Any],
        *,
        argv: list[str] | None = None,
        stdout: str = "",
        stderr: str = "",
        before: dict[str, dict[str, Any]] | None = None,
        after: dict[str, dict[str, Any]] | None = None,
        max_log_bytes: int = DEFAULT_MAX_LOG_BYTES,
        full_log: bool = False,
        redact_logs: bool = True,
        snapshot_policy: dict[str, Any] | None = None,
        resource_metrics: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        runs_dir = os.path.join(self.root_dir, "生产数据", "batch_runs")
        os.makedirs(runs_dir, exist_ok=True)
        attempt = int(task.get("attempts") or 0)
        base = f"{safe_component(str(task.get('id') or 'task'))}_attempt{attempt:02d}"
        json_path = os.path.join(runs_dir, f"{base}.json")
        stdout_path = os.path.join(runs_dir, f"{base}.stdout.log")
        stderr_path = os.path.join(runs_dir, f"{base}.stderr.log")
        stdout_text, stdout_meta = sanitize_log(stdout or "", max_bytes=max_log_bytes, full_log=full_log, redact=redact_logs)
        stderr_text, stderr_meta = sanitize_log(stderr or "", max_bytes=max_log_bytes, full_log=full_log, redact=redact_logs)
        with open(stdout_path, "w", encoding="utf-8") as f:
            f.write(stdout_text)
        with open(stderr_path, "w", encoding="utf-8") as f:
            f.write(stderr_text)
        diff = self.diff_snapshots(before or {}, after or {}) if before is not None and after is not None else {}
        artifact = {
            "schema_version": 1,
            "kind": RUN_ARTIFACT_KIND,
            "generated_at": iso(),
            "project_root": self.root_dir,
            "task": {
                "id": task.get("id"),
                "kind": task.get("kind"),
                "scope": task.get("scope"),
                "chapter": task.get("chapter"),
                "priority": task.get("priority"),
                "attempt": attempt,
                "worker": worker_id,
                "command": task.get("command") or "",
            },
            "argv": argv or [],
            "result": payload,
            "logs": {
                "stdout_path": relpath(self.root_dir, stdout_path),
                "stderr_path": relpath(self.root_dir, stderr_path),
                "stdout_sha256": sha256_file(stdout_path),
                "stderr_sha256": sha256_file(stderr_path),
                "stdout_bytes": os.path.getsize(stdout_path),
                "stderr_bytes": os.path.getsize(stderr_path),
                "stdout": stdout_meta,
                "stderr": stderr_meta,
                "policy": {
                    "full_log": full_log,
                    "redact_logs": redact_logs,
                    "max_log_bytes": None if full_log else max_log_bytes,
                },
            },
            "resource_metrics": resource_metrics or {},
            "snapshot_policy": snapshot_policy or self.snapshot_policy(),
            "output_artifacts": diff,
        }
        tmp = f"{json_path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(artifact, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, json_path)
        return relpath(self.root_dir, json_path), artifact

    def attach_run_artifact(self, task_id: str, artifact_rel: str, summary: dict[str, Any]) -> None:
        with self.locked():
            queue = self.read_queue()
            task = self._find_task(queue, task_id)
            artifacts = task.setdefault("run_artifacts", [])
            if artifact_rel not in artifacts:
                artifacts.append(artifact_rel)
            task["last_run_artifact"] = artifact_rel
            task["last_run_summary"] = summary
            task["updated_at"] = iso()
            self.write_queue(queue)

    def run_artifact_summary(self) -> dict[str, Any]:
        runs_dir = os.path.join(self.root_dir, "生产数据", "batch_runs")
        artifacts: list[dict[str, Any]] = []
        if os.path.isdir(runs_dir):
            for name in sorted(os.listdir(runs_dir)):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(runs_dir, name)
                try:
                    with open(path, encoding="utf-8") as f:
                        payload = json.load(f)
                except Exception:
                    continue
                if payload.get("kind") != RUN_ARTIFACT_KIND:
                    continue
                result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
                outputs = payload.get("output_artifacts") if isinstance(payload.get("output_artifacts"), dict) else {}
                logs = payload.get("logs") if isinstance(payload.get("logs"), dict) else {}
                resources = payload.get("resource_metrics") if isinstance(payload.get("resource_metrics"), dict) else {}
                artifacts.append({
                    "path": relpath(self.root_dir, path),
                    "task_id": (payload.get("task") or {}).get("id"),
                    "status": result.get("status") or "unknown",
                    "returncode": result.get("returncode"),
                    "elapsed_ms": result.get("elapsed_ms"),
                    "child_max_rss_kb": resources.get("child_max_rss_kb"),
                    "log_bytes": int(logs.get("stdout_bytes") or 0) + int(logs.get("stderr_bytes") or 0),
                    "log_truncated": bool((logs.get("stdout") or {}).get("truncated") or (logs.get("stderr") or {}).get("truncated")),
                    "generated_at": payload.get("generated_at") or "",
                    "output_change_count": int(outputs.get("added_count") or 0) + int(outputs.get("changed_count") or 0) + int(outputs.get("removed_count") or 0),
                })
        by_status: dict[str, int] = {}
        elapsed_values = []
        output_changes = 0
        log_bytes = 0
        truncated_logs = 0
        max_rss_values = []
        for artifact in artifacts:
            status = str(artifact.get("status") or "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            if isinstance(artifact.get("elapsed_ms"), int):
                elapsed_values.append(int(artifact["elapsed_ms"]))
            output_changes += int(artifact.get("output_change_count") or 0)
            log_bytes += int(artifact.get("log_bytes") or 0)
            if artifact.get("log_truncated"):
                truncated_logs += 1
            if isinstance(artifact.get("child_max_rss_kb"), int):
                max_rss_values.append(int(artifact["child_max_rss_kb"]))
        latest = sorted(artifacts, key=lambda item: item.get("generated_at") or "", reverse=True)[:10]
        return {
            "count": len(artifacts),
            "by_status": by_status,
            "avg_elapsed_ms": int(sum(elapsed_values) / len(elapsed_values)) if elapsed_values else 0,
            "max_elapsed_ms": max(elapsed_values) if elapsed_values else 0,
            "max_child_rss_kb": max(max_rss_values) if max_rss_values else 0,
            "log_bytes": log_bytes,
            "truncated_log_count": truncated_logs,
            "output_change_count": output_changes,
            "latest": latest,
        }


def build_tasks(root: str, kind: str, chapters: list[int], command_template: str,
                *, max_retries: int, priority: str) -> list[dict[str, Any]]:
    priority_rank = {"P0": 0, "P1": 10, "P2": 20, "P3": 30}.get(priority, 50)
    if not chapters:
        task_id = stable_task_id(kind, None, command_template, scope="project")
        return [{
            "id": task_id,
            "idempotency_key": task_id,
            "kind": kind,
            "scope": "project",
            "chapter": None,
            "priority": priority,
            "priority_rank": priority_rank,
            "max_retries": max_retries,
            "command": render_template(command_template, root, None, task_id),
        }]
    tasks = []
    for chapter in chapters:
        task_id = stable_task_id(kind, chapter, command_template)
        tasks.append({
            "id": task_id,
            "idempotency_key": task_id,
            "kind": kind,
            "scope": f"chapter:{chapter}",
            "chapter": chapter,
            "priority": priority,
            "priority_rank": priority_rank,
            "max_retries": max_retries,
            "command": render_template(command_template, root, chapter, task_id),
        })
    return tasks


def load_market_evidence_jobs(root: str) -> list[dict[str, Any]]:
    path = os.path.join(root, "评分", "market_evidence_jobs.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"market evidence jobs not found: {path}")
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or payload.get("kind") != "novel_market_evidence_jobs":
        raise ValueError(f"not a novel_market_evidence_jobs file: {path}")
    jobs = payload.get("jobs") or []
    if not isinstance(jobs, list):
        raise ValueError("market_evidence_jobs.json jobs must be a list")
    return [job for job in jobs if isinstance(job, dict)]


def build_market_evidence_tasks(
    root: str,
    command_template: str,
    *,
    max_retries: int,
    priority: str,
) -> list[dict[str, Any]]:
    priority_rank = {"P0": 0, "P1": 10, "P2": 20, "P3": 30}.get(priority, 50)
    tasks: list[dict[str, Any]] = []
    for job in load_market_evidence_jobs(root):
        job_id = str(job.get("id") or f"job_{len(tasks) + 1:03d}")
        target = str(job.get("target_platform") or "")
        scope = f"market_evidence:{job_id}"
        task_id = stable_task_id("market_evidence", None, command_template, scope=scope)
        task = {
            "id": task_id,
            "idempotency_key": task_id,
            "kind": "market_evidence",
            "scope": scope,
            "chapter": None,
            "priority": priority,
            "priority_rank": priority_rank,
            "max_retries": max_retries,
            "command": render_template(
                command_template,
                root,
                None,
                task_id,
                {
                    "job_id": job_id,
                    "target_platform": target,
                    "baseline_date": job.get("baseline_date") or "",
                },
            ),
            "market_evidence_job": job,
            "search_queries": list(job.get("search_queries") or []),
            "required_output_schema": dict(job.get("required_output_schema") or {}),
            "manual_evidence_format": job.get("manual_evidence_format") or "",
            "return_command_template": job.get("return_command_template") or "",
            "target_platform": target,
            "baseline_date": job.get("baseline_date") or "",
            "source_task_id": job.get("source_task_id") or "",
        }
        tasks.append(task)
    return tasks


def print_payload(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if isinstance(payload, dict) and payload.get("kind") == QUEUE_KIND:
            summary = payload.get("summary") or {}
            print(f"queue: {payload.get('project_root')}")
            print(f"tasks: {summary.get('total', len(payload.get('tasks') or []))}")
            print(f"by_status: {summary.get('by_status') or {}}")
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="novel local batch queue")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="add idempotent tasks")
    plan.add_argument("project_root")
    plan.add_argument("--kind", default="review", choices=["review", "score", "revision", "dashboard", "manual", "market_evidence"])
    plan.add_argument("--chapters", default="", help="chapter list/ranges, e.g. 1-5,9")
    plan.add_argument("--command-template", help="format string with {root}, {chapter}, {chapter_label}, {task_id}")
    plan.add_argument("--max-retries", type=int, default=1)
    plan.add_argument("--priority", default="P1")
    plan.add_argument("--max-tasks", type=int)
    plan.add_argument("--json", action="store_true")

    claim = sub.add_parser("claim", help="claim one pending task")
    claim.add_argument("project_root")
    claim.add_argument("--worker", required=True)
    claim.add_argument("--lease-sec", type=int, default=900)
    claim.add_argument("--kind", action="append", help="limit claimable kind; repeatable")
    claim.add_argument("--json", action="store_true")

    renew = sub.add_parser("renew", help="renew a running task lease")
    renew.add_argument("project_root")
    renew.add_argument("--task-id", required=True)
    renew.add_argument("--worker", required=True)
    renew.add_argument("--lease-sec", type=int, default=900)
    renew.add_argument("--json", action="store_true")

    mark = sub.add_parser("mark", help="mark task pass/fail/skipped")
    mark.add_argument("project_root")
    mark.add_argument("--task-id", required=True)
    mark.add_argument("--worker", required=True)
    mark.add_argument("--status", required=True, choices=["pass", "fail", "completed", "failed", "skipped"])
    mark.add_argument("--error-class", default="")
    mark.add_argument("--message", default="")
    mark.add_argument("--json", action="store_true")

    reclaim = sub.add_parser("reclaim", help="return expired running tasks to retry queue")
    reclaim.add_argument("project_root")
    reclaim.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="show queue status")
    status.add_argument("project_root")
    status.add_argument("--json", action="store_true")

    dead = sub.add_parser("dead-letter", help="show dead-letter tasks")
    dead.add_argument("project_root")
    dead.add_argument("--json", action="store_true")

    run_one = sub.add_parser("run-one", help="claim and execute one allowlisted task")
    run_one.add_argument("project_root")
    run_one.add_argument("--worker", required=True)
    run_one.add_argument("--lease-sec", type=int, default=900)
    run_one.add_argument("--timeout-sec", type=int, default=1800)
    run_one.add_argument("--kind", action="append", help="limit claimable kind; repeatable")
    run_one.add_argument("--allow-manual", action="store_true", help="allow non-allowlisted manual commands")
    run_one.add_argument("--dry-run", action="store_true")
    run_one.add_argument("--snapshot-include", action="append", help="include output path pattern/prefix; repeatable")
    run_one.add_argument("--snapshot-exclude", action="append", help="exclude output path pattern/prefix; repeatable")
    run_one.add_argument("--max-log-bytes", type=int, default=DEFAULT_MAX_LOG_BYTES, help="per-stream log bytes to keep unless --full-log")
    run_one.add_argument("--full-log", action="store_true", help="store full redacted stdout/stderr logs")
    run_one.add_argument("--no-log-redaction", action="store_true", help="disable batch log redaction for a trusted local run")
    run_one.add_argument("--json", action="store_true")

    report = sub.add_parser("report", help="write batch governance report")
    report.add_argument("project_root")
    report.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    queue = NovelBatchQueue(root)

    try:
        if args.command == "plan":
            chapters = parse_chapters(args.chapters) if args.chapters else []
            template = args.command_template or default_command_template(args.kind)
            if args.kind == "market_evidence":
                if chapters:
                    raise ValueError("market_evidence tasks are project-scoped; do not pass --chapters")
                tasks = build_market_evidence_tasks(root, template, max_retries=args.max_retries, priority=args.priority)
            else:
                tasks = build_tasks(root, args.kind, chapters, template, max_retries=args.max_retries, priority=args.priority)
            result = queue.upsert_tasks(tasks, max_tasks=args.max_tasks)
            payload = {"added": result["added"], "updated": result["updated"], "queue_path": queue.queue_file}
            print_payload(payload, args.json)
        elif args.command == "claim":
            task = queue.claim_task(args.worker, lease_sec=args.lease_sec, kinds=set(args.kind or []))
            print_payload(task or {"status": "empty"}, args.json)
        elif args.command == "renew":
            print_payload(queue.renew(args.task_id, args.worker, lease_sec=args.lease_sec), args.json)
        elif args.command == "mark":
            print_payload(queue.mark(args.task_id, args.worker, args.status, error_class=args.error_class, message=args.message), args.json)
        elif args.command == "reclaim":
            print_payload(queue.reclaim_expired(), args.json)
        elif args.command == "status":
            print_payload(queue.status(), args.json)
        elif args.command == "dead-letter":
            payload = queue.status()
            tasks = [task for task in payload.get("tasks", []) if task.get("status") == "dead_letter"]
            print_payload({"dead_letter": tasks, "count": len(tasks)}, args.json)
        elif args.command == "run-one":
            payload = queue.run_one(
                args.worker,
                lease_sec=args.lease_sec,
                kinds=set(args.kind or []),
                timeout_sec=args.timeout_sec,
                allow_manual=args.allow_manual,
                dry_run=args.dry_run,
                snapshot_include=args.snapshot_include,
                snapshot_exclude=args.snapshot_exclude,
                max_log_bytes=args.max_log_bytes,
                full_log=args.full_log,
                redact_logs=not args.no_log_redaction,
            )
            print_payload(payload, args.json)
            if payload.get("status") in {"failed", "command_not_allowed"}:
                return 1
        elif args.command == "report":
            json_path, md_path, report_payload = queue.write_governance_report()
            payload = {"json_path": json_path, "md_path": md_path, **report_payload}
            print_payload(payload, args.json)
    except Exception as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
