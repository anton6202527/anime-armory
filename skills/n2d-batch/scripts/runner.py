#!/usr/bin/env python3
"""Batch worker runner for novel2drama/n2d.

The queue ledger stays in queue.py.  This worker claims tasks, executes the
configured command for each task, records runner telemetry into n2d-dashboard,
and marks the queue task pass/fail so retry policy remains centralized.
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = os.path.dirname(__file__)
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))


def load_module(name: str, path: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


queue_mod = load_module("n2d_batch_queue_for_runner", os.path.join(SCRIPT_DIR, "queue.py"))
dashboard_mod = load_module(
    "n2d_dashboard_for_runner",
    os.path.join(REPO_SKILLS, "n2d-dashboard", "scripts", "dashboard.py"),
)


DEFAULT_CONFIG_NAME = "batch_runner.json"
SOURCE = "n2d-batch/scripts/runner.py"


class UnrunnableTask(RuntimeError):
    pass


def production_dir(root: str) -> str:
    return os.path.join(root, queue_mod.PRODUCTION_DIR)


def default_config_path(root: str) -> str:
    return os.path.join(production_dir(root), DEFAULT_CONFIG_NAME)


def load_config(root: str, path: Optional[str]) -> Dict[str, Any]:
    config_path = path or default_config_path(root)
    if not os.path.isfile(config_path):
        return {"commands": {}, "env": {}, "_path": config_path, "_exists": False}
    with open(config_path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{config_path} must be a JSON object")
    data.setdefault("commands", {})
    data.setdefault("env", {})
    data["_path"] = config_path
    data["_exists"] = True
    if not isinstance(data["commands"], dict):
        raise ValueError(f"{config_path}.commands must be an object")
    if not isinstance(data["env"], dict):
        raise ValueError(f"{config_path}.env must be an object")
    return data


def task_format_map(root: str, task: Dict[str, Any]) -> Dict[str, str]:
    affected_shots = ",".join(str(item) for item in task.get("affected_shots", []))
    affected_artifacts = ",".join(str(item) for item in task.get("affected_artifacts", []))
    return {
        "root": root,
        "ep": str(task.get("episode", "")),
        "episode": str(task.get("episode", "")),
        "task_id": str(task.get("id", "")),
        "stage_key": str(task.get("stage_key", "")),
        "stage": str(task.get("stage_key", "")),
        "owner": str(task.get("owner", "")),
        "reason": str(task.get("reason", "")),
        "scope": str(task.get("rerun_scope", "")),
        "affected_shots": affected_shots,
        "affected_artifacts": affected_artifacts,
    }


def resolve_command(root: str, task: Dict[str, Any], config: Dict[str, Any], override: Optional[str]) -> str:
    commands = config.get("commands", {})
    keys = [
        str(task.get("stage_key", "")),
        str(task.get("owner", "")),
        "*",
    ]
    template = override or task.get("runner_command")
    if not template:
        for key in keys:
            if key and key in commands:
                template = commands[key]
                break
    if not template:
        template = task.get("command")
    if not template:
        raise UnrunnableTask("task has no command")
    command = str(template).format(**task_format_map(root, task))
    if command.strip().startswith("/"):
        raise UnrunnableTask(
            "task command is an agent slash command, not a shell command; "
            f"add {DEFAULT_CONFIG_NAME}.commands['{task.get('stage_key')}'] or pass --command"
        )
    return command


def env_for_task(root: str, task: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, str]:
    env = dict(os.environ)
    env.update({str(k): str(v) for k, v in config.get("env", {}).items()})
    env.update({
        "N2D_ROOT": root,
        "N2D_EPISODE": str(task.get("episode", "")),
        "N2D_TASK_ID": str(task.get("id", "")),
        "N2D_STAGE": str(task.get("stage_key", "")),
        "N2D_OWNER": str(task.get("owner", "")),
        "N2D_REASON": str(task.get("reason", "")),
        "N2D_RERUN_SCOPE": str(task.get("rerun_scope", "")),
        "N2D_AFFECTED_SHOTS": ",".join(str(item) for item in task.get("affected_shots", [])),
        "N2D_AFFECTED_ARTIFACTS": ",".join(str(item) for item in task.get("affected_artifacts", [])),
    })
    return env


def truncate(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def append_runner_event(
    root: str,
    task: Dict[str, Any],
    *,
    command: str,
    status: str,
    exit_code: Optional[int],
    duration_sec: float,
    dry_run: bool,
    error: str = "",
    no_dashboard: bool = False,
) -> None:
    if no_dashboard:
        return
    meta = {
        "task_id": task.get("id"),
        "runner_status": status,
        "exit_code": exit_code,
        "command": command,
        "dry_run": dry_run,
        "error": error,
        "attempt": task.get("attempts"),
    }
    event = dashboard_mod.make_event(
        str(task.get("episode", "")),
        str(task.get("stage_key", "")),
        "manual",
        source=SOURCE,
        duration_sec=round(duration_sec, 3),
        meta=meta,
    )
    dashboard_mod.append_events(root, [event])
    dashboard_mod.build(root, write=True)


def _task_stage_spec(task: Dict[str, Any]) -> Dict[str, Any]:
    stage = str(task.get("stage_key") or "")
    try:
        return queue_mod.find_stage(stage)
    except Exception:
        return {}


def _output_exists(root: str, pattern: str) -> bool:
    path = pattern if os.path.isabs(pattern) else os.path.join(root, pattern)
    return bool(glob.glob(path)) if any(ch in path for ch in "*?[") else os.path.exists(path)


def _missing_outputs(root: str, patterns: Sequence[str], fmt: Dict[str, str]) -> List[str]:
    missing: List[str] = []
    for rel in patterns:
        pattern = str(rel).format(**fmt)
        if not _output_exists(root, pattern):
            missing.append(pattern)
    return missing


def _option_patterns(option: Any) -> Tuple[str, List[str]]:
    if isinstance(option, dict):
        label = str(option.get("label") or "option")
        values = option.get("all_of") or option.get("outputs") or ()
        if isinstance(values, str):
            return label, [values]
        return label, [str(item) for item in values]
    return str(option), [str(option)]


def verify_output_contract(root: str, task: Dict[str, Any], spec: Dict[str, Any]) -> List[str]:
    fmt = task_format_map(root, task)
    contract = spec.get("output_contract")
    if not isinstance(contract, dict):
        return [f"missing output: {item}" for item in _missing_outputs(root, spec.get("outputs", ()) or (), fmt)]

    issues: List[str] = []
    required = contract.get("required") or contract.get("all_of") or ()
    if isinstance(required, str):
        required = (required,)
    for item in _missing_outputs(root, [str(rel) for rel in required], fmt):
        issues.append(f"missing output: {item}")

    any_of = contract.get("any_of") or ()
    if isinstance(any_of, (str, dict)):
        any_of = (any_of,)
    options = list(any_of)
    if options:
        option_failures: List[str] = []
        for option in options:
            label, patterns = _option_patterns(option)
            missing = _missing_outputs(root, patterns, fmt)
            if not missing:
                return issues
            option_failures.append(f"{label}: missing {', '.join(missing)}")
        issues.append("missing output option: " + " | ".join(option_failures))
    return issues


def verify_task_completion(root: str, task: Dict[str, Any]) -> List[str]:
    """Best-effort postcondition check for batch commands.

    This is intentionally optional because some wrappers perform partial work.
    When enabled, a stage command must both advance its progress columns and
    leave the declared contract outputs in place.
    """
    issues: List[str] = []
    spec = _task_stage_spec(task)
    ep = str(task.get("episode") or "")
    issues.extend(verify_output_contract(root, task, spec))

    progress_cols = [str(col) for col in spec.get("progress_columns", ()) or ()]
    if progress_cols:
        try:
            header, rows = queue_mod.parse_progress(root)
            wanted = queue_mod.normalize_episode(ep)
            row = next(
                (
                    item for item in rows
                    if queue_mod.normalize_episode(str(item.get("_ep") or item.get("集") or "")) == wanted
                ),
                None,
            )
        except Exception as exc:
            issues.append(f"cannot read progress: {exc}")
            row = None
            header = []
        if row is not None:
            missing = [
                col for col in progress_cols
                if col in header and not queue_mod.is_done(str(row.get(col, "")))
            ]
            if missing:
                issues.append(f"progress not done: {', '.join(missing)}")
    return issues


def run_process(command: str, *, shell: bool, timeout_sec: Optional[float], env: Dict[str, str]) -> Tuple[int, str, str]:
    args: Any = command if shell else shlex.split(command)
    proc = subprocess.run(
        args,
        shell=shell,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_sec,
        env=env,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def execute_task(
    root: str,
    task: Dict[str, Any],
    config: Dict[str, Any],
    *,
    command_override: Optional[str],
    shell: bool,
    timeout_sec: Optional[float],
    dry_run: bool,
    no_dashboard: bool,
    verify_outputs: bool,
) -> Dict[str, Any]:
    started = time.monotonic()
    command = ""
    status = "fail"
    exit_code: Optional[int] = None
    note = ""
    stdout = ""
    stderr = ""
    try:
        command = resolve_command(root, task, config, command_override)
        task.setdefault("history", []).append({
            "ts": queue_mod.now_iso(),
            "action": "runner:start",
            "command": command,
        })
        if dry_run:
            status = "pass"
            note = "dry-run"
            exit_code = 0
        else:
            exit_code, stdout, stderr = run_process(
                command,
                shell=shell,
                timeout_sec=timeout_sec,
                env=env_for_task(root, task, config),
            )
            status = "pass" if exit_code == 0 else "fail"
            note = f"exit_code={exit_code}"
            if status == "pass" and verify_outputs:
                issues = verify_task_completion(root, task)
                if issues:
                    status = "fail"
                    note = "verification failed: " + "; ".join(issues[:6])
    except subprocess.TimeoutExpired as exc:
        status = "fail"
        exit_code = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        note = f"timeout after {timeout_sec}s"
    except UnrunnableTask as exc:
        status = "fail"
        note = str(exc)
    except Exception as exc:  # pragma: no cover - defensive guard for worker
        status = "fail"
        note = f"{type(exc).__name__}: {exc}"
    duration = time.monotonic() - started
    task["last_runner"] = {
        "command": command,
        "status": status,
        "exit_code": exit_code,
        "duration_sec": round(duration, 3),
        "stdout": truncate(stdout),
        "stderr": truncate(stderr),
        "note": note,
        "finished_at": queue_mod.now_iso(),
    }
    task.setdefault("history", []).append({
        "ts": queue_mod.now_iso(),
        "action": f"runner:{status}",
        "exit_code": exit_code,
        "note": note,
    })
    try:
        append_runner_event(
            root,
            task,
            command=command,
            status=status,
            exit_code=exit_code,
            duration_sec=duration,
            dry_run=dry_run,
            error=note if status == "fail" else "",
            no_dashboard=no_dashboard,
        )
    except Exception as exc:
        task["last_runner"]["telemetry_error"] = f"{type(exc).__name__}: {exc}"
    return {"task": task, "status": status, "exit_code": exit_code, "note": note}


def _heartbeat(root: str, task_id: str, lease_seconds: int, worker: str, stop_evt: threading.Event) -> None:
    """长任务执行期间周期性续租，防止 lease 过期被别的 worker 误回收。"""
    interval = max(5.0, lease_seconds / 3.0)
    while not stop_evt.wait(interval):
        try:
            queue_mod.renew(root, [task_id], lease_seconds, worker)
        except Exception:  # pragma: no cover - heartbeat best-effort
            pass


def run_claimed(
    root: str,
    claimed: List[Dict[str, Any]],
    config: Dict[str, Any],
    *,
    worker: str,
    lease_seconds: int,
    command_override: Optional[str],
    shell: bool,
    timeout_sec: Optional[float],
    dry_run: bool,
    no_dashboard: bool,
    verify_outputs: bool,
    stop_on_fail: bool,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for task in claimed:
        task_id = str(task["id"])
        stop_evt = threading.Event()
        hb = None
        if not dry_run:
            hb = threading.Thread(target=_heartbeat, args=(root, task_id, lease_seconds, worker, stop_evt), daemon=True)
            hb.start()
        try:
            result = execute_task(
                root,
                task,
                config,
                command_override=command_override,
                shell=shell,
                timeout_sec=timeout_sec,
                dry_run=dry_run,
                no_dashboard=no_dashboard,
                verify_outputs=verify_outputs,
            )
        finally:
            stop_evt.set()
            if hb is not None:
                hb.join(timeout=2)
        # 锁内重读最新队列再 mark，并校验 worker/attempt，避免租约过期后的旧 worker 覆盖新认领。
        try:
            marked = queue_mod.mark(
                root,
                task_id,
                result["status"],
                result["note"],
                runner=result["task"].get("last_runner"),
                expected_worker=worker,
                expected_attempt=int(task.get("attempts") or 0),
            )
        except ValueError as exc:
            results.append({
                "id": task_id,
                "episode": task.get("episode"),
                "stage_key": task.get("stage_key"),
                "runner_status": "fail",
                "queue_status": "stale_mark_rejected",
                "attempts": task.get("attempts"),
                "exit_code": result["exit_code"],
                "note": f"mark_rejected: {exc}",
            })
            if stop_on_fail:
                break
            continue
        results.append({
            "id": marked.get("id"),
            "episode": marked.get("episode"),
            "stage_key": marked.get("stage_key"),
            "runner_status": result["status"],
            "queue_status": marked.get("status"),
            "attempts": marked.get("attempts"),
            "exit_code": result["exit_code"],
            "note": result["note"],
        })
        if stop_on_fail and result["status"] != "pass":
            break
    return results


def run_once(
    root: str,
    *,
    limit: Optional[int],
    config_path: Optional[str] = None,
    command_override: Optional[str] = None,
    shell: bool = False,
    timeout_sec: Optional[float] = None,
    dry_run: bool = False,
    no_dashboard: bool = False,
    verify_outputs: bool = False,
    stop_on_fail: bool = False,
    worker: Optional[str] = None,
    lease_seconds: int = queue_mod.DEFAULT_LEASE_SECONDS,
) -> Dict[str, Any]:
    config = load_config(root, config_path)
    worker = worker or queue_mod.default_worker()
    # claim() 锁内：先回收过期租约（自动断点恢复）再认领，并打 worker+lease。
    claimed = queue_mod.claim(root, limit=limit, worker=worker, lease_seconds=lease_seconds)
    results = run_claimed(
        root,
        claimed,
        config,
        worker=worker,
        lease_seconds=lease_seconds,
        command_override=command_override,
        shell=shell,
        timeout_sec=timeout_sec,
        dry_run=dry_run,
        no_dashboard=no_dashboard,
        verify_outputs=verify_outputs,
        stop_on_fail=stop_on_fail,
    )
    return {
        "claimed": len(claimed),
        "processed": len(results),
        "results": results,
        "worker": worker,
        "config": config.get("_path"),
    }


def run_until_empty(
    root: str,
    *,
    limit: Optional[int],
    max_tasks: Optional[int],
    sleep_sec: float,
    config_path: Optional[str],
    command_override: Optional[str],
    shell: bool,
    timeout_sec: Optional[float],
    dry_run: bool,
    no_dashboard: bool,
    verify_outputs: bool,
    stop_on_fail: bool,
    worker: Optional[str] = None,
    lease_seconds: int = queue_mod.DEFAULT_LEASE_SECONDS,
) -> Dict[str, Any]:
    all_results: List[Dict[str, Any]] = []
    while max_tasks is None or len(all_results) < max_tasks:
        effective_limit = limit
        if max_tasks is not None:
            remaining = max_tasks - len(all_results)
            effective_limit = remaining if effective_limit is None else min(effective_limit, remaining)
        result = run_once(
            root,
            limit=effective_limit,
            config_path=config_path,
            command_override=command_override,
            shell=shell,
            timeout_sec=timeout_sec,
            dry_run=dry_run,
            no_dashboard=no_dashboard,
            verify_outputs=verify_outputs,
            stop_on_fail=stop_on_fail,
            worker=worker,
            lease_seconds=lease_seconds,
        )
        all_results.extend(result["results"])
        if result["claimed"] == 0:
            break
        if stop_on_fail and any(item["runner_status"] != "pass" for item in result["results"]):
            break
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return {"processed": len(all_results), "results": all_results}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d batch worker runner")
    ap.add_argument("root")
    ap.add_argument("--limit", type=int, default=1, help="tasks to claim per cycle; concurrency cap still applies")
    ap.add_argument("--until-empty", action="store_true", help="keep claiming until no task is claimable")
    ap.add_argument("--max-tasks", type=int, help="hard cap when using --until-empty")
    ap.add_argument("--sleep-sec", type=float, default=0.0)
    ap.add_argument("--config", help="batch runner config; defaults to 生产数据/batch_runner.json")
    ap.add_argument("--command", help="override command template for every claimed task")
    ap.add_argument("--shell", action="store_true", help="execute command through the shell")
    ap.add_argument("--timeout-sec", type=float)
    ap.add_argument("--dry-run", action="store_true", help="claim and mark pass without running the command")
    ap.add_argument("--no-dashboard", action="store_true", help="do not write runner telemetry to n2d-dashboard")
    ap.add_argument("--verify-outputs", action="store_true", help="after exit 0, require contract outputs and progress columns to be complete")
    ap.add_argument("--stop-on-fail", action="store_true")
    ap.add_argument("--worker", help="worker id（默认 host:pid）；多 worker 各起一个；--resume 自愈需稳定 id")
    ap.add_argument("--lease-seconds", type=int, default=queue_mod.DEFAULT_LEASE_SECONDS,
                    help=f"任务租约秒数（执行期自动心跳续租）；默认 {queue_mod.DEFAULT_LEASE_SECONDS}")
    ap.add_argument("--resume", action="store_true",
                    help="开跑前先回收本 --worker 上次崩溃残留的 running 任务（断点恢复），再继续认领")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = ns.root.rstrip("/")
    worker = ns.worker or queue_mod.default_worker()
    if ns.resume:
        reclaimed = queue_mod.reclaim(root, worker=worker, force_worker=True)
        if reclaimed:
            print(f"[resume] reclaimed {len(reclaimed)} stale running task(s) of worker {worker}", file=sys.stderr)
    if ns.until_empty:
        result = run_until_empty(
            root,
            limit=ns.limit,
            max_tasks=ns.max_tasks,
            sleep_sec=ns.sleep_sec,
            config_path=ns.config,
            command_override=ns.command,
            shell=ns.shell,
            timeout_sec=ns.timeout_sec,
            dry_run=ns.dry_run,
            no_dashboard=ns.no_dashboard,
            verify_outputs=ns.verify_outputs,
            stop_on_fail=ns.stop_on_fail,
            worker=worker,
            lease_seconds=ns.lease_seconds,
        )
    else:
        result = run_once(
            root,
            limit=ns.limit,
            config_path=ns.config,
            command_override=ns.command,
            shell=ns.shell,
            timeout_sec=ns.timeout_sec,
            dry_run=ns.dry_run,
            no_dashboard=ns.no_dashboard,
            verify_outputs=ns.verify_outputs,
            stop_on_fail=ns.stop_on_fail,
            worker=worker,
            lease_seconds=ns.lease_seconds,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not any(item.get("runner_status") == "fail" for item in result.get("results", [])) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
