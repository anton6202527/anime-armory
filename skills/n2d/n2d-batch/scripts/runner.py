#!/usr/bin/env python3
"""Batch worker runner for n2d.

The queue ledger stays in queue.py.  This worker claims tasks, executes the
configured command for each task, records runner telemetry into n2d-dashboard,
and marks the queue task pass/fail so retry policy remains centralized.
"""
from __future__ import annotations

import argparse
import contextlib
from copy import deepcopy
import datetime as dt
import glob
import hashlib
import hmac
import importlib.util
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SCRIPT_DIR = os.path.dirname(__file__)
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))


def _sanitize_import_path_for_stdlib() -> None:
    """Prevent this directory's queue.py from shadowing Python's stdlib queue."""
    script_real = os.path.realpath(SCRIPT_DIR)
    cleaned = []
    for entry in sys.path:
        base = os.getcwd() if entry == "" else entry
        if os.path.realpath(base) == script_real:
            continue
        cleaned.append(entry)
    sys.path[:] = cleaned

    loaded = sys.modules.get("queue")
    loaded_path = getattr(loaded, "__file__", "") if loaded is not None else ""
    if loaded_path and os.path.realpath(loaded_path) == os.path.join(script_real, "queue.py"):
        del sys.modules["queue"]


def load_module(name: str, path: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_sanitize_import_path_for_stdlib()
queue_mod = load_module("n2d_batch_queue_for_runner", os.path.join(SCRIPT_DIR, "queue.py"))
dashboard_mod = load_module(
    "n2d_dashboard_for_runner",
    os.path.join(REPO_SKILLS, "n2d-dashboard", "scripts", "dashboard.py"),
)
run_mod = load_module(
    "n2d_run_for_batch_runner",
    os.path.join(REPO_SKILLS, "run.py"),
)
spend_envelope_mod = load_module(
    "n2d_spend_envelope_for_batch_runner",
    os.path.join(REPO_SKILLS, "_lib", "spend_envelope.py"),
)
governance_mod = load_module(
    "n2d_batch_governance_for_runner",
    os.path.join(SCRIPT_DIR, "governance.py"),
)
media_artifact_mod = load_module(
    "n2d_media_artifact_for_batch_runner",
    os.path.join(REPO_SKILLS, "n2d-compose", "media_artifact.py"),
)
import paid_execution_contract  # noqa: E402  producer-owned final paid-boundary interlock


DEFAULT_CONFIG_NAME = "batch_runner.json"
SOURCE = "n2d-batch/scripts/runner.py"
ALLOW_TEST_FIXTURE_AUTHORIZATION = False
_PRODUCER_MODULES: Dict[str, Any] = {}


class UnrunnableTask(RuntimeError):
    pass


def production_governance_interlock(root: str) -> Optional[Dict[str, Any]]:
    """Live critical stop-loss/dead-letter interlock used at every paid boundary."""
    return governance_mod.critical_interlock(root)


def governance_block_message(issue: Mapping[str, Any]) -> str:
    rows = issue.get("violations") if isinstance(issue.get("violations"), list) else []
    details = "; ".join(
        str(row.get("kind") or row.get("metric") or row)
        for row in rows[:4]
        if isinstance(row, Mapping)
    )
    return "critical production governance interlock" + (f": {details}" if details else "")


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
    if looks_like_agent_skill_command(command):
        raise UnrunnableTask(
            "task command is an agent slash command or skill command, not a shell command; "
            f"add {DEFAULT_CONFIG_NAME}.commands['{task.get('stage_key')}'] or pass --command"
        )
    return command


def looks_like_agent_skill_command(command: str) -> bool:
    text = str(command or "").strip()
    if text.startswith("/"):
        return True
    try:
        parts = shlex.split(text)
    except ValueError:
        parts = text.split()
    if not parts:
        return False
    first = parts[0]
    return first == "n2d" or first.startswith("n2d-")


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
        "N2D_IDEMPOTENCY_KEY": str(task.get("idempotency_key", "")),
        "N2D_RERUN_SCOPE": str(task.get("rerun_scope", "")),
        "N2D_AFFECTED_SHOTS": ",".join(str(item) for item in task.get("affected_shots", [])),
        "N2D_AFFECTED_ARTIFACTS": ",".join(str(item) for item in task.get("affected_artifacts", [])),
    })
    return env


def paid_execution_expectation(task: Mapping[str, Any]) -> Dict[str, Any]:
    stage = str(task.get("stage_key") or "")
    contract = task.get("_runner_producer_contract")
    authorization = task.get("_runner_production_authorization")
    if stage not in PRODUCTION_STAGE_KEYS or not isinstance(contract, Mapping):
        return {}
    if not isinstance(authorization, Mapping):
        raise ProducerContractError("cannot cross paid boundary without production authorization")
    source_rows = contract.get("records")
    if not isinstance(source_rows, list) or not source_rows:
        raise ProducerContractError("paid producer contract has no exact physical request records")
    records: List[Dict[str, Any]] = []
    if stage == "image":
        for row in source_rows:
            if not isinstance(row, Mapping):
                continue
            records.append({
                "shot": str(row.get("shot") or ""),
                "target": str(row.get("target") or ""),
                "input_fingerprint": str(row.get("input_fingerprint") or ""),
                "submit_request_sha256": str(row.get("submit_request_sha256") or ""),
            })
    elif stage == "video":
        batch_fp = str(contract.get("batch_input_fingerprint") or "")
        for row in source_rows:
            if not isinstance(row, Mapping):
                continue
            records.append({
                "clip": str(row.get("clip") or ""),
                "target": str(row.get("target") or ""),
                "input_fingerprint": batch_fp,
                "submit_request_sha256": str(row.get("submit_request_sha256") or ""),
            })
    else:
        raise ProducerContractError(
            f"{stage} producer has no paid-boundary expectation adapter; fail closed"
        )
    if not records or any(
        not row.get("target")
        or not (row.get("shot") or row.get("clip"))
        or not row.get("input_fingerprint")
        or not row.get("submit_request_sha256")
        for row in records
    ):
        raise ProducerContractError("paid execution expectation contains an incomplete physical request")
    return paid_execution_contract.build_expectation(
        stage=stage,
        task_id=str(task.get("id") or ""),
        episode=queue_mod.normalize_episode(str(task.get("episode") or "")),
        attempt=int(task.get("attempts") or 0),
        authorization_digest=str(authorization.get("authorization_digest") or ""),
        records=records,
    )


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
    build: bool = True,
) -> None:
    if no_dashboard:
        return
    meta = {
        "task_id": task.get("id"),
        "idempotency_key": task.get("idempotency_key"),
        "trace_id": task.get("trace_id") or task.get("idempotency_key") or task.get("id"),
        "runner_status": status,
        "exit_code": exit_code,
        "command": command,
        "dry_run": dry_run,
        "error": error,
        "error_class": queue_mod.classify_error(error, {"exit_code": exit_code, "note": error}) if status in {"fail", "qa_blocked"} else "",
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
    # 事件永远先落盘；整盘重建（持事件锁 + O(events) 聚合）开销大，多 worker 下会互相排队。
    # build=False 时由调用方在一个 cycle 结束后只重建一次，避免每个任务都重建。
    if build:
        dashboard_mod.build(root, write=True)


def refresh_gate(root: str, episode: str, stage: str) -> Dict[str, Any]:
    """返工 pass 后重跑该 stage 门禁，刷新 gate_findings_<stage>_<ep>.json（闭环复检的最后一环）。

    这让 --recheck 拿到的是返工 *之后* 的现状指纹，而不是返工前的陈旧 findings——否则复检永远
    在对着旧报告判 resolved/reopen，等于没复检。镜头级 gate 重跑由这里自动接上，无需人工再敲一遍
    dashboard.py gate。仅刷 gate 事件与 findings，不在此重建仪表盘（由调用方在 cycle 末统一重建）。
    返回 {stage, exit_code, blocks, warns, findings_path}（相对 root）。
    """
    ep = dashboard_mod.normalize_episode(episode)
    events, code, findings = dashboard_mod.gate_events(root, ep, stage)
    dashboard_mod.replace_events(
        root,
        lambda event: (
            event.get("episode") == ep
            and event.get("stage") == stage
            and event.get("source") == "n2d-review/scripts/gate.py"
            and event.get("event") in {"qa_gate", "qa_gate_run"}
        ),
        events,
    )
    path = dashboard_mod.write_gate_findings(root, ep, stage, findings)
    blocks = sum(1 for f in findings if isinstance(f, dict) and str(f.get("sev")).lower() == "block")
    warns = sum(1 for f in findings if isinstance(f, dict) and str(f.get("sev")).lower() == "warn")
    return {
        "stage": stage,
        "exit_code": code,
        "blocks": blocks,
        "warns": warns,
        "findings_path": os.path.relpath(path, root),
    }


def _task_stage_spec(task: Dict[str, Any]) -> Dict[str, Any]:
    stage = str(task.get("stage_key") or "")
    try:
        return queue_mod.find_stage(stage)
    except Exception:
        return {}


def _matched_output_paths(root: str, pattern: str) -> List[str]:
    path = pattern if os.path.isabs(pattern) else os.path.join(root, pattern)
    if any(ch in path for ch in "*?["):
        return sorted(glob.glob(path))
    return [path] if os.path.exists(path) else []


def _probe_media_issue(path: str, suffix: str) -> Optional[str]:
    """Prove that a media artifact is decodable, not merely magic-header-shaped."""
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            from PIL import Image

            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                if image.width <= 0 or image.height <= 0:
                    return "image has no decodable pixels"
        except Exception as exc:
            return f"invalid or undecodable {suffix[1:]} media ({exc})"
        return None

    if suffix in {".mp4", ".mov", ".m4v"}:
        validation = media_artifact_mod.validate_media(
            path,
            {"audio_required": False, "known_color_required": False, "faststart_required": False},
        )
        if validation.get("status") != "pass":
            failed = [row for row in validation.get("checks") or [] if row.get("status") == "block"]
            detail = ", ".join(str(row.get("code") or "media") for row in failed) or "shared media validation failed"
            return f"invalid or undecodable {suffix[1:]} media ({detail})"
        return None

    stream = "a:0"
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", stream,
                "-show_entries", "stream=codec_type:format=duration", "-of", "json", path,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except FileNotFoundError:
        return "ffprobe unavailable; media playability cannot be proven"
    except subprocess.TimeoutExpired:
        return "ffprobe timed out"
    if probe.returncode != 0:
        return f"invalid or undecodable {suffix[1:]} media ({probe.stderr.strip() or 'ffprobe failed'})"
    try:
        payload = json.loads(probe.stdout or "{}")
        streams = payload.get("streams") if isinstance(payload, dict) else []
        duration = float(((payload.get("format") or {}).get("duration")))
    except (TypeError, ValueError, json.JSONDecodeError):
        return f"invalid or undecodable {suffix[1:]} media (missing stream/duration)"
    if not streams or duration <= 0:
        return f"invalid or undecodable {suffix[1:]} media (missing stream/duration)"
    map_arg = "0:v:0" if stream.startswith("v") else "0:a:0"
    try:
        decode = subprocess.run(
            ["ffmpeg", "-v", "error", "-xerror", "-i", path, "-map", map_arg, "-f", "null", "-"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=120,
        )
    except FileNotFoundError:
        return "ffmpeg unavailable; full media decode cannot be proven"
    except subprocess.TimeoutExpired:
        return "ffmpeg decode timed out"
    if decode.returncode != 0:
        return f"invalid or undecodable {suffix[1:]} media ({decode.stderr.strip() or 'decode failed'})"
    return None


def _output_content_issue(path: str) -> Optional[str]:
    """产物可用性：空目录、零字节、坏 JSON/媒体头都不算就位。"""
    if os.path.isdir(path):
        saw_file = False
        first_issue = ""
        for base, _dirs, files in os.walk(path):
            for name in files:
                saw_file = True
                issue = _output_content_issue(os.path.join(base, name))
                if issue is None:
                    return None
                first_issue = first_issue or issue
        return "empty directory" if not saw_file else f"directory has no usable files ({first_issue})"
    try:
        if os.path.getsize(path) == 0:
            return "empty file"
    except OSError as exc:
        return f"unreadable ({exc})"
    if path.endswith(".json"):
        try:
            with open(path, encoding="utf-8") as fh:
                json.load(fh)
        except Exception as exc:
            return f"invalid json ({exc})"
    suffix = Path(path).suffix.lower()
    if suffix in {".mp4", ".mov", ".m4v", ".wav", ".png", ".jpg", ".jpeg", ".webp"}:
        try:
            with open(path, "rb") as fh:
                header = fh.read(32)
        except OSError as exc:
            return f"unreadable media ({exc})"
        valid = True
        if suffix in {".mp4", ".mov", ".m4v"}:
            valid = len(header) >= 12 and header[4:8] == b"ftyp"
        elif suffix == ".wav":
            valid = len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"
        elif suffix == ".png":
            valid = header.startswith(b"\x89PNG\r\n\x1a\n")
        elif suffix in {".jpg", ".jpeg"}:
            valid = header.startswith(b"\xff\xd8\xff")
        elif suffix == ".webp":
            valid = len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
        if not valid:
            return f"invalid {suffix[1:]} media header"
        probe_issue = _probe_media_issue(path, suffix)
        if probe_issue:
            return probe_issue
    return None


def _output_exists(root: str, pattern: str) -> bool:
    return any(
        _output_content_issue(path) is None
        for path in _matched_output_paths(root, pattern)
    )


def _missing_outputs(root: str, patterns: Sequence[str], fmt: Dict[str, str]) -> List[str]:
    missing: List[str] = []
    for rel in patterns:
        pattern = str(rel).format(**fmt)
        matched = _matched_output_paths(root, pattern)
        issues = [_output_content_issue(path) for path in matched]
        if any(issue is None for issue in issues):
            continue
        if matched:
            first = next((i for i in issues if i), "unusable")
            missing.append(f"{pattern} ({first})")
        else:
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


def _producer_contract(task: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    direct = task.get("_runner_producer_contract")
    if isinstance(direct, Mapping):
        return direct
    last_runner = task.get("last_runner")
    execution = last_runner.get("execution_binding") if isinstance(last_runner, Mapping) else None
    contract = execution.get("producer_contract") if isinstance(execution, Mapping) else None
    return contract if isinstance(contract, Mapping) else None


def producer_output_bindings(root: str, task: Mapping[str, Any]) -> List[Dict[str, Any]]:
    contract = _producer_contract(task)
    if not isinstance(contract, Mapping):
        return []
    kind = str(contract.get("kind") or "")
    episode = queue_mod.normalize_episode(str(task.get("episode") or contract.get("episode") or ""))
    records = contract.get("records") if isinstance(contract.get("records"), list) else []
    project = Path(root).resolve()
    bindings: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        if kind in {"n2d_image_paid_submit_binding", "n2d_batch_test_fixture_binding"}:
            rel = str(record.get("target") or "")
        elif kind == "n2d_video_paid_submit_binding":
            target = str(record.get("target") or "")
            rel = f"出视频/{episode}/视频/{target}" if target else ""
        else:
            continue
        if not rel:
            bindings.append({"path": "", "exists": False, "sha256": "", "issue": "producer target missing"})
            continue
        path = (project / rel).resolve(strict=False)
        try:
            canonical_rel = path.relative_to(project).as_posix()
        except ValueError:
            bindings.append({
                "path": rel,
                "exists": False,
                "sha256": "",
                "issue": "producer target escapes project root",
            })
            continue
        exists = path.is_file()
        bindings.append({
            "path": canonical_rel,
            "exists": exists,
            "sha256": _sha256_file(path) if exists else "",
            "bytes": path.stat().st_size if exists else 0,
            "issue": paid_execution_contract.artifact_content_issue(path) if exists else "missing",
        })
    return bindings


def verify_producer_contract_outputs(root: str, task: Dict[str, Any]) -> List[str]:
    contract = _producer_contract(task)
    if not isinstance(contract, Mapping):
        return []
    kind = str(contract.get("kind") or "")
    if kind not in {
        "n2d_image_paid_submit_binding",
        "n2d_video_paid_submit_binding",
        "n2d_batch_test_fixture_binding",
    }:
        return []
    bindings = producer_output_bindings(root, task)
    task["_runner_verified_outputs"] = bindings
    if not bindings:
        return ["canonical producer contract has no physical output targets"]
    issues = [
        f"producer target unusable: {row.get('path') or '<missing>'} ({row.get('issue') or 'missing'})"
        for row in bindings
        if row.get("issue")
    ]
    baseline_rows = task.get("_runner_output_baseline")
    baseline = {
        str(row.get("path") or ""): str(row.get("sha256") or "")
        for row in baseline_rows
        if isinstance(row, Mapping) and row.get("exists")
    } if isinstance(baseline_rows, list) else {}
    recovery = task.get("_runner_provider_recovery")
    recovery_target = ""
    recovery_sha = ""
    if isinstance(recovery, Mapping) and recovery.get("provider_submit_id"):
        target = str(recovery.get("target") or "").strip()
        recovery_target = f"出视频/{queue_mod.normalize_episode(str(task.get('episode') or ''))}/视频/{target}"
        if str(recovery.get("download_submit_id") or "") == str(
            recovery.get("provider_submit_id") or ""
        ):
            recovery_sha = str(recovery.get("download_artifact_sha256") or "")
    for row in bindings:
        path = str(row.get("path") or "")
        if row.get("exists") and baseline.get(path) and baseline[path] == str(row.get("sha256") or ""):
            recovered_existing_output = (
                path == recovery_target
                and bool(recovery_sha)
                and hmac.compare_digest(recovery_sha, str(row.get("sha256") or ""))
            )
            if not recovered_existing_output:
                issues.append(f"producer target was not refreshed by this attempt: {path}")
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
    if str(task.get("stage_key") or "") == "compose":
        receipt = media_artifact_mod.current_receipt(root, str(task.get("episode") or ""))
        if receipt.get("status") != "pass":
            issues.append(
                "compose output lacks a current MediaArtifactReceipt: "
                + "; ".join(receipt.get("issues") or ["shared master validation did not pass"])
            )
    issues.extend(verify_producer_contract_outputs(root, task))

    progress_cols = [str(col) for col in spec.get("progress_columns", ()) or ()]
    if str(task.get("stage_key") or "") == "video" and task.get("physical_clips"):
        # A physical provider task completes at downloaded bytes + machine QC.  The episode-level
        # 视频 column is advanced only after every clip crosses the separate current-pixel accept
        # boundary, so it cannot be a per-clip postcondition.
        progress_cols = []
    if str(task.get("stage_key") or "") == "review":
        # `验收` is the later human-only commit. Machine review evidence must be allowed to
        # reach qa_blocked while that cell is still open; queue acceptance enforces it at done.
        progress_cols = [col for col in progress_cols if col != "验收"]
    if progress_cols:
        wanted = queue_mod.normalize_episode(ep)
        try:
            header, rows = queue_mod.parse_progress(root)
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
        missing_columns = [col for col in progress_cols if col not in header]
        if missing_columns:
            issues.append(f"progress column missing: {', '.join(missing_columns)}")
        if row is None:
            issues.append(f"progress row missing: {wanted}")
        else:
            # 用 mode-aware 的 is_progress_satisfied，而非裸 is_done——原生音画下「配音=⬜」、
            # 先出视频下「配音=⏳rough」都属"已满足"，不能误判成 not done。
            missing = [
                col for col in progress_cols
                if col in header and not queue_mod.is_progress_satisfied(root, row, col)
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


# 生产/花钱 stage：canonical preflight 不可关闭（--no-next-preflight / batch_runner.json 均无效）。
# voice 也可能调用付费 TTS；混合模式下的 rough voice 会返回 needs_stage_execution，runner
# 对这种非生成前沿 fail-closed，交回标准 voice preflight，而不是猜测它是否安全。
PRODUCTION_STAGE_KEYS = frozenset({"voice", "image", "video", "compose"})
PAID_STAGE_KEYS = PRODUCTION_STAGE_KEYS  # 旧测试/调用方兼容别名

NEXT_PREFLIGHT_BLOCK_REASONS = {
    "env_missing",
    "blocked_by_entry_check",
    "capability_evidence_required",
    "blocked_by_review_acceptance",
    "blocked_by_gate",
    "blocked_by_image_qc",
    "needs_compliance",
    "needs_choice",
    "unknown_stage",
    "prework_failed",
    "done",
    "needs_stage_execution",
    "needs_acceptance_signoff",
}


def _authorization_from_config(
    task: Dict[str, Any], config: Dict[str, Any], root: str = ""
) -> Optional[Dict[str, Any]]:
    """Resolve an explicit task-bound production approval; queue presence is never approval."""
    embedded = task.get("production_authorization")
    if isinstance(embedded, dict):
        return dict(embedded)
    phase_embedded = task.get("phase_spend_envelope")
    if isinstance(phase_embedded, dict):
        return dict(phase_embedded)
    authorizations = config.get("production_authorizations")
    if isinstance(authorizations, dict):
        receipt = authorizations.get(str(task.get("id") or ""))
        if isinstance(receipt, dict):
            return dict(receipt)
    envelopes = config.get("phase_spend_envelopes")
    if not isinstance(envelopes, dict):
        return None
    candidate = (
        envelopes.get(str(task.get("id") or ""))
        or envelopes.get(str(task.get("stage_key") or ""))
        or envelopes.get("*")
    )
    if isinstance(candidate, dict):
        return dict(candidate)
    if isinstance(candidate, str) and candidate.strip():
        path = Path(candidate).expanduser()
        if not path.is_absolute():
            path = Path(root or ".").expanduser().resolve() / path
        return spend_envelope_mod.load_envelope(path)
    return None


def _canonical_json_digest(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _binding_digest(value: Any) -> str:
    """Normalize an existing digest or hash a structured/string execution input."""
    if value in (None, "", {}):
        return ""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ""
        lowered = text.lower()
        if (
            lowered.startswith("sha256:")
            and len(lowered) == 71
            and all(ch in "0123456789abcdef" for ch in lowered[7:])
        ):
            return lowered
        if len(lowered) == 64 and all(ch in "0123456789abcdef" for ch in lowered):
            return "sha256:" + lowered
        return _canonical_json_digest({"value": text})
    return _canonical_json_digest({"value": value})


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_execution_contract(command: str) -> Dict[str, Any]:
    """Bind resolved argv plus every explicit shell/Python entrypoint's current bytes."""
    try:
        argv = shlex.split(str(command or ""))
    except ValueError:
        argv = str(command or "").split()
    entrypoints: List[Dict[str, str]] = []
    for raw in argv:
        if not str(raw).lower().endswith((".py", ".sh")):
            continue
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.is_file():
            entrypoints.append({"path": str(path.resolve()), "sha256": _sha256_file(path)})
    return {"command": str(command or ""), "argv": argv, "entrypoints": entrypoints}


class ProducerContractError(ValueError):
    """The paid producer could not expose an exact current request contract."""


def _load_producer_module(key: str, relative_path: str, *, module_name: Optional[str] = None) -> Any:
    environment = {
        name: value
        for name, value in os.environ.items()
        if name.startswith("N2D_") or name in {"ASPECT", "PATH", "PYTHONPATH"}
    }
    environment_key = hashlib.sha256(
        json.dumps(environment, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    cache_key = f"{key}:{environment_key}"
    cached = _PRODUCER_MODULES.get(cache_key)
    if cached is not None:
        if module_name:
            sys.modules[module_name] = cached
        return cached
    path = os.path.join(REPO_SKILLS, relative_path)
    loaded = load_module(module_name or f"n2d_batch_producer_{key}_{environment_key}", path)
    _PRODUCER_MODULES[cache_key] = loaded
    return loaded


def _producer_environment(
    root: str,
    task: Mapping[str, Any],
    config: Mapping[str, Any],
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    effective = env_for_task(root, dict(task), dict(config))
    configured = config.get("env") if isinstance(config.get("env"), Mapping) else {}
    names = sorted(
        set(str(key) for key in configured)
        | {key for key in effective if key.startswith("N2D_")}
        | {key for key in ("ASPECT", "PATH", "PYTHONPATH") if key in effective}
    )
    values = {key: str(effective.get(key) or "") for key in names}
    return effective, {
        "kind": "n2d_producer_execution_environment",
        "version": 1,
        "keys": names,
        # Values may include credentials.  Bind them without serializing secrets into receipts.
        "digest": _canonical_json_digest({"values": values}),
    }


@contextlib.contextmanager
def _temporary_environment(effective: Mapping[str, str]):
    changed = {
        key: (key in os.environ, os.environ.get(key))
        for key, value in effective.items()
        if os.environ.get(key) != str(value)
    }
    try:
        for key in changed:
            os.environ[key] = str(effective[key])
        yield
    finally:
        for key, (existed, value) in changed.items():
            if existed:
                os.environ[key] = str(value)
            else:
                os.environ.pop(key, None)


def _producer_environment_bound(fn):
    def wrapped(root: str, task: Dict[str, Any], config: Dict[str, Any], resolved_command: str):
        effective, binding = _producer_environment(root, task, config)
        with _temporary_environment(effective):
            contract = fn(root, task, config, resolved_command)
        if not isinstance(contract, dict):
            raise ProducerContractError("producer resolver returned a non-object contract")
        contract = dict(contract)
        contract["execution_environment"] = binding
        return contract
    wrapped.__name__ = fn.__name__
    wrapped.__doc__ = fn.__doc__
    return wrapped


def _csv_values(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        rows = value
    else:
        rows = re.split(r"[,，]", str(value or ""))
    return [str(row).strip() for row in rows if str(row).strip()]


def _command_option(command: str, name: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = str(command or "").split()
    flag = f"--{name}"
    for index, part in enumerate(parts):
        if part == flag and index + 1 < len(parts):
            return str(parts[index + 1])
        if part.startswith(flag + "="):
            return part.split("=", 1)[1]
    return ""


def _producer_command(stage: str, resolved_command: str, config: Dict[str, Any]) -> str:
    env = config.get("env") if isinstance(config.get("env"), dict) else {}
    if stage == "image":
        return str(env.get("N2D_IMAGE_COMMAND") or resolved_command)
    return str(resolved_command)


def _assert_direct_python_producer(command: str, script_name: str) -> None:
    raw = str(command or "")
    if any(token in raw for token in ("\n", "\r", "`", "$(", ";", "&&", "||", "|", ">", "<")):
        raise ProducerContractError(
            "paid producer argv contains shell control or command-substitution syntax"
        )
    try:
        argv = shlex.split(raw)
    except ValueError as exc:
        raise ProducerContractError("producer command is not valid argv") from exc
    if len(argv) < 2:
        raise ProducerContractError("producer command is incomplete")
    executable = Path(argv[0]).name.lower()
    if not executable.startswith("python"):
        raise ProducerContractError(
            "paid producer must be a direct Python argv; env/shell/wrapper commands may strip "
            "the authorized paid-boundary expectation"
        )
    script_indexes = [index for index, token in enumerate(argv[1:], 1) if Path(token).name == script_name]
    if script_indexes != [1]:
        raise ProducerContractError(
            f"paid producer must directly execute {script_name} as argv[1]"
        )


def _assert_safe_image_launcher(
    root: str,
    episode: str,
    resolved_command: str,
    producer_command: str,
) -> None:
    """Allow a direct producer or the one audited image wrapper, never an arbitrary shell."""
    if str(resolved_command).strip() == str(producer_command).strip():
        return
    try:
        argv = shlex.split(str(resolved_command or ""))
    except ValueError as exc:
        raise ProducerContractError("image launcher is not valid argv") from exc
    wrapper = (Path(__file__).resolve().parent / "run_n2d_image.sh").resolve()
    if (
        len(argv) != 4
        or Path(argv[0]).name != "bash"
        or Path(argv[1]).expanduser().resolve(strict=False) != wrapper
        or Path(argv[2]).expanduser().resolve(strict=False) != Path(root).expanduser().resolve()
        or queue_mod.normalize_episode(argv[3]) != episode
    ):
        raise ProducerContractError(
            "paid image launcher must be the direct producer argv or the exact canonical "
            "run_n2d_image.sh <root> <episode> argv; arbitrary outer wrappers are forbidden"
        )


@_producer_environment_bound
def resolve_image_producer_contract(
    root: str,
    task: Dict[str, Any],
    config: Dict[str, Any],
    resolved_command: str,
) -> Dict[str, Any]:
    """Recompute the image producer's exact paid request fingerprints, target by target."""
    producer_command = _producer_command("image", resolved_command, config)
    expected_script = (
        "dreamina_image_runner.py" if "dreamina_image_runner.py" in producer_command.lower()
        else "codex_image_runner.py"
    )
    _assert_direct_python_producer(producer_command, expected_script)
    lowered = producer_command.lower()
    if "codex_image_runner.py" in lowered:
        backend = "codex"
        image = _load_producer_module(
            "codex_image",
            "n2d-image/scripts/codex_image_runner.py",
            module_name="codex_image_runner",
        )
        dreamina = None
    elif "dreamina_image_runner.py" in lowered:
        backend = "dreamina"
        image = _load_producer_module(
            "codex_image",
            "n2d-image/scripts/codex_image_runner.py",
            module_name="codex_image_runner",
        )
        dreamina = _load_producer_module(
            "dreamina_image",
            "n2d-image/scripts/dreamina_image_runner.py",
        )
    else:
        raise ProducerContractError(
            "image producer is not a supported canonical resolver (expected codex_image_runner.py or dreamina_image_runner.py)"
        )

    project = Path(root).expanduser().resolve()
    episode = queue_mod.normalize_episode(str(task.get("episode") or ""))
    _assert_safe_image_launcher(root, episode, resolved_command, producer_command)
    env = config.get("env") if isinstance(config.get("env"), dict) else {}
    task_shots = _csv_values(task.get("affected_shots"))
    command_shots_raw = _command_option(producer_command, "shots")
    if "N2D_AFFECTED_SHOTS" in command_shots_raw:
        command_shots_raw = ",".join(task_shots)
    command_shots = _csv_values(command_shots_raw or env.get("N2D_AFFECTED_SHOTS"))
    if task_shots and command_shots and set(task_shots) != set(command_shots):
        raise ProducerContractError(
            "image task affected_shots do not match the physical --shots executed by the producer"
        )
    if task_shots and not command_shots:
        raise ProducerContractError(
            "image task has an affected_shots scope but the resolved producer command does not execute it"
        )
    shots = command_shots
    shared = _csv_values(_command_option(producer_command, "shared-targets"))
    if not shots and not shared:
        raise ProducerContractError("image canonical resolver needs explicit shots/shared-targets")
    targets: List[Any] = []
    if shared:
        targets.extend(image.build_shared_targets(project, shared))
    if shots:
        targets.extend(image.build_targets(project, episode, shots))
    if not targets:
        raise ProducerContractError("image canonical resolver resolved no paid targets")

    selection = image.current_image_backend_selection(str(project))
    producer_model = str(
        env.get("N2D_IMAGE_MODEL")
        or selection.get("image_model")
        or selection.get("model")
        or ""
    )
    producer_channel = str(selection.get("channel") or selection.get("access") or "")
    records: List[Dict[str, Any]] = []
    for target in targets:
        seed = image.logical_seed(project, episode, target.shot, target.rel_path)
        retry_guidance = ""
        if backend == "codex":
            if "--force" in producer_command and image.png_valid(project / target.rel_path):
                retry_guidance = image.target_qc_retry_guidance(project, episode, target)
            bundle = image.reference_bundle_for_target(project, episode, target)
            refs = image.codex_reference_inputs_for_target(project, episode, target, bundle)
            refs = image.prepare_reference_inputs(project, episode, refs, write=False)
            if any((row.get("reference_quality") or {}).get("status") == "would_enhance" for row in refs):
                raise ProducerContractError(
                    f"image target {target.rel_path} has an unmaterialized enhanced reference; prepare it before approval"
                )
            compiled = image.compile_target_image_request(
                project,
                episode,
                target,
                refs,
                backend="codex",
                model=producer_model,
                channel=producer_channel,
                retry_guidance=retry_guidance,
            )
            compiler_errors = list((compiled.get("lint") or {}).get("errors") or [])
            if compiler_errors:
                raise ProducerContractError(
                    f"image target {target.rel_path} has an invalid compiled request: "
                    + ",".join(str(item) for item in compiler_errors)
                )
            fingerprint = image.image_generation_input_fingerprint(
                project,
                episode,
                target,
                seed=seed,
                compiled_request=compiled,
                reference_inputs=refs,
                backend_key="codex",
            )
            task_id = str(task.get("id") or "manual")
            temp_path = (
                Path(tempfile.gettempdir())
                / "n2d_codex_image_runner"
                / task_id
                / f"{episode}_{image.temp_token(target.shot)}_{Path(target.rel_path).stem}.png"
            )
            actual_prompt = image.build_codex_prompt(
                project,
                episode,
                target,
                temp_path,
                seed,
                bundle,
                None,
                retry_guidance=retry_guidance,
                compiled_request=compiled,
            )
            exact_submit = image.codex_exact_submit_request(
                image.repo_root(), actual_prompt, refs
            )
            submit_sha = str(exact_submit.get("sha256") or "")
        else:
            assert dreamina is not None
            canonical_reset = "--canonical-reset" in producer_command
            retry_guidance = image.target_qc_retry_guidance(project, episode, target)
            ref_paths = dreamina.prompt_reference_paths(
                project,
                target,
                episode,
                canonical_reset=canonical_reset,
            )
            refs = dreamina.dreamina_reference_inputs(
                project,
                target,
                ref_paths,
                episode,
                canonical_reset=canonical_reset,
            )
            model_version = _command_option(producer_command, "model-version") or str(
                env.get("N2D_DREAMINA_IMAGE_MODEL") or producer_model or "5.0"
            )
            resolution = _command_option(producer_command, "resolution-type") or str(
                env.get("N2D_DREAMINA_IMAGE_RESOLUTION") or "2k"
            )
            compiled = dreamina.build_dreamina_compiled_request(
                project,
                episode,
                target,
                refs,
                model_version=model_version,
                resolution_type=resolution,
                retry_guidance=retry_guidance,
            )
            compiler_errors = list((compiled.get("lint") or {}).get("errors") or [])
            if compiler_errors:
                raise ProducerContractError(
                    f"image target {target.rel_path} has an invalid compiled request: "
                    + ",".join(str(item) for item in compiler_errors)
                )
            fingerprint = dreamina.dreamina_generation_input_fingerprint(
                project,
                episode,
                target,
                seed=seed,
                compiled_request=compiled,
                reference_inputs=refs,
            )
            submit_sha = str(compiled.get("compiled_request_sha256") or "")
        if not fingerprint or not submit_sha:
            raise ProducerContractError(f"image producer contract incomplete for {target.rel_path}")
        records.append({
            "target": str(target.rel_path),
            "shot": str(target.shot),
            "input_fingerprint": str(fingerprint),
            "submit_request_sha256": submit_sha,
            "compiled_request_sha256": str(compiled.get("compiled_request_sha256") or ""),
            "model": str(compiled.get("model") or (model_version if backend == "dreamina" else producer_model) or ""),
            "channel": str(compiled.get("channel") or producer_channel or backend),
        })
    models = sorted({row["model"] for row in records if row.get("model")})
    channels = sorted({row["channel"] for row in records if row.get("channel")})
    contract = {
        "kind": "n2d_image_paid_submit_binding",
        "version": 1,
        "backend": backend,
        "episode": episode,
        "model": models[0] if len(models) == 1 else ("mixed:" + ",".join(models) if models else ""),
        "channel": channels[0] if len(channels) == 1 else ("mixed:" + ",".join(channels) if channels else ""),
        "producer_script_sha256": _sha256_file(Path(image.__file__).resolve()),
        "records": sorted(records, key=lambda row: (row["target"], row["shot"])),
    }
    return contract


def _video_range(config: Dict[str, Any], resolved_command: str) -> str:
    env = config.get("env") if isinstance(config.get("env"), dict) else {}
    value = str(env.get("N2D_VIDEO_RANGE") or "")
    if not value:
        match = re.search(r"(?:^|\s)N2D_VIDEO_RANGE=([^\s]+)", resolved_command)
        value = match.group(1).strip("'\"") if match else ""
    return value


@_producer_environment_bound
def resolve_video_producer_contract(
    root: str,
    task: Dict[str, Any],
    config: Dict[str, Any],
    resolved_command: str,
) -> Dict[str, Any]:
    """Resolve a prepared manifest and recompute each exact video submit snapshot."""
    _assert_direct_python_producer(resolved_command, "video_runner.py")
    env = config.get("env") if isinstance(config.get("env"), dict) else {}
    if "run_n2d_video.sh" in resolved_command and (
        str(env.get("N2D_VIDEO_AUTO_SUBMIT") or "") == "1"
        or str(env.get("N2D_VIDEO_SUBMIT_ONE") or "").strip()
    ):
        raise ProducerContractError(
            "video prepare+submit wrapper mutates producer inputs after authorization; "
            "prepare first, then authorize an exact video_runner.py submit command"
        )
    video = _load_producer_module("video", "n2d-video/scripts/video_runner.py")
    project = Path(root).expanduser().resolve()
    episode = queue_mod.normalize_episode(str(task.get("episode") or ""))
    candidates: List[Path] = []
    explicit_manifest = str(task.get("producer_manifest") or task.get("video_manifest") or "").strip()
    if explicit_manifest:
        explicit_path = Path(explicit_manifest).expanduser()
        explicit_path = explicit_path if explicit_path.is_absolute() else project / explicit_path
        try:
            explicit_path.resolve(strict=False).relative_to(project)
        except ValueError as exc:
            raise ProducerContractError("video producer_manifest escapes project root") from exc
        candidates = [explicit_path]
    range_value = _video_range(config, resolved_command)
    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", range_value)
    if range_value and not match:
        raise ProducerContractError(f"video range is invalid: {range_value}")
    if match:
        expected_range_manifest = video.manifest_path(
            project, episode, int(match.group(1)), int(match.group(2))
        )
        if candidates and candidates[0].resolve(strict=False) != expected_range_manifest.resolve(strict=False):
            raise ProducerContractError(
                "video producer_manifest conflicts with explicit N2D_VIDEO_RANGE " + range_value
            )
        candidates = [expected_range_manifest]
        if not expected_range_manifest.is_file():
            raise ProducerContractError(f"video prepared manifest missing for explicit range {range_value}")
    if not candidates:
        candidates = sorted((project / "生产数据").glob(f"video_batch_{episode}_*.json"))
    candidates = [path for path in candidates if path.is_file()]
    if len(candidates) != 1:
        raise ProducerContractError(
            f"video canonical resolver needs exactly one prepared manifest, found {len(candidates)}"
        )
    manifest_path = candidates[0]
    manifest = video.load_json(manifest_path)
    manifest_episode = queue_mod.normalize_episode(str(manifest.get("episode") or ""))
    if manifest_episode != episode:
        raise ProducerContractError(
            f"video producer manifest episode mismatch: {manifest_episode or 'missing'} != {episode}"
        )
    issues = video.video_manifest_fingerprint_issues(project, manifest)
    if issues:
        raise ProducerContractError("video prepared manifest is stale: " + ",".join(issues))
    task_requested = _csv_values(task.get("physical_clips") or task.get("producer_clip"))
    direct_clip = _command_option(resolved_command, "clip")
    one = str(env.get("N2D_VIDEO_SUBMIT_ONE") or "").strip()
    if direct_clip:
        requested = [direct_clip]
    elif one:
        requested = [one]
    elif str(env.get("N2D_VIDEO_AUTO_SUBMIT") or "") == "1":
        requested = [str(row.get("clip") or "") for row in manifest.get("items") or [] if isinstance(row, Mapping)]
    else:
        requested = []
    if task_requested and requested and set(task_requested) != set(requested):
        raise ProducerContractError(
            "video task physical_clips do not match the clips executed by the resolved submit command"
        )
    if not requested:
        raise ProducerContractError(
            "video canonical resolver needs an explicit physical clip in the actual submit argv "
            "(--clip) or its configured N2D_VIDEO_SUBMIT_ONE/AUTO_SUBMIT wrapper"
        )
    records: List[Dict[str, Any]] = []
    for clip in requested:
        try:
            item = video.find_item(manifest, clip)
            _backend_key, adapter = video.resolve_video_backend({**manifest, "_root": str(project)})
            if str(adapter.get("implementation") or "embedded") == "embedded":
                args, _request_path = video._adapter_invocation(
                    project,
                    deepcopy(manifest),
                    deepcopy(item),
                    adapter,
                    "submit",
                )
                snapshot = video.build_submit_snapshot(project, manifest, item, adapter, args, None)
                submit_sha = str(snapshot.get("sha256") or "")
            else:
                request = video.execution_adapter_v2.build_request(
                    operation="submit",
                    root=project,
                    manifest=manifest,
                    item=item,
                    adapter=adapter,
                )
                submit_sha = str(request.get("request_sha256") or "")
        except Exception as exc:
            raise ProducerContractError(f"video submit contract unavailable for {clip}: {exc}") from exc
        if not submit_sha:
            raise ProducerContractError(f"video submit contract missing digest for {clip}")
        records.append({
            "clip": clip,
            "target": str(item.get("target") or ""),
            "submit_request_sha256": submit_sha,
        })
    batch_fp = video.current_video_manifest_input_fingerprint(project, manifest)
    contract = {
        "kind": "n2d_video_paid_submit_binding",
        "version": 1,
        "episode": episode,
        "manifest": manifest_path.relative_to(project).as_posix(),
        "batch_input_fingerprint": str(batch_fp.get("sha256") or ""),
        "backend": str(manifest.get("backend") or ""),
        "model": str(manifest.get("model_version") or ""),
        "channel": str(manifest.get("channel") or manifest.get("backend") or ""),
        "records": sorted(records, key=lambda row: row["clip"]),
    }
    return contract


@_producer_environment_bound
def resolve_voice_producer_contract(
    root: str, task: Dict[str, Any], config: Dict[str, Any], resolved_command: str
) -> Dict[str, Any]:
    raise ProducerContractError(
        "voice producer has no canonical prepared per-line submit manifest yet; "
        "a generic file hash cannot authorize TTS spend"
    )


@_producer_environment_bound
def resolve_compose_producer_contract(
    root: str, task: Dict[str, Any], config: Dict[str, Any], resolved_command: str
) -> Dict[str, Any]:
    raise ProducerContractError(
        "compose producer has no canonical prepared ordered render manifest yet; "
        "runtime glob/file hashes cannot authorize the render"
    )


def resolve_stage_producer_contract(
    root: str,
    task: Dict[str, Any],
    config: Dict[str, Any],
    resolved_command: str,
) -> Dict[str, Any]:
    stage = str(task.get("stage_key") or "")
    resolvers = {
        "image": resolve_image_producer_contract,
        "video": resolve_video_producer_contract,
        "voice": resolve_voice_producer_contract,
        "compose": resolve_compose_producer_contract,
    }
    resolver = resolvers.get(stage)
    if resolver is None:
        raise ProducerContractError(f"no canonical producer resolver for stage {stage or 'missing'}")
    return resolver(root, task, config, resolved_command)


def production_execution_binding(task: Dict[str, Any]) -> Dict[str, str]:
    command_digest = str(task.get("_runner_command_digest") or "")
    if not command_digest:
        command = task.get("resolved_command") or task.get("runner_command") or task.get("command")
        command_digest = _binding_digest(command)
    input_value = task.get("_runner_input_fingerprint")
    if input_value in (None, ""):
        input_value = task.get("input_fingerprint") or task.get("content_fingerprint")
    submit_value = task.get("_runner_submit_request_digest")
    if submit_value in (None, ""):
        submit_value = (
            task.get("submit_request_sha256")
            or task.get("request_sha256")
            or task.get("compiled_request_sha256")
            or task.get("submit_request")
        )
    return {
        "command_digest": _binding_digest(command_digest),
        "input_fingerprint": _binding_digest(input_value),
        "submit_request_digest": _binding_digest(submit_value),
        "producer_contract_digest": _binding_digest(task.get("_runner_producer_contract")),
    }


def bind_production_execution_context(
    root: str,
    task: Dict[str, Any],
    config: Dict[str, Any],
    resolved_command: str,
) -> Dict[str, str]:
    """Bind the exact executable command and current canonical content before approval check."""
    task["_runner_command_digest"] = _binding_digest(command_execution_contract(resolved_command))
    task.pop("_runner_producer_contract_issue", None)
    try:
        contract = resolve_stage_producer_contract(root, task, config, resolved_command)
        task["_runner_producer_contract"] = contract
        stage = str(task.get("stage_key") or "")
        if stage == "image":
            input_value = [row.get("input_fingerprint") for row in contract.get("records") or []]
            submit_value = [row.get("submit_request_sha256") for row in contract.get("records") or []]
            if contract.get("model"):
                task["_runner_execution_model"] = str(contract.get("model"))
            if contract.get("channel"):
                task["_runner_execution_channel"] = str(contract.get("channel"))
        elif stage == "video":
            input_value = contract.get("batch_input_fingerprint")
            submit_value = [row.get("submit_request_sha256") for row in contract.get("records") or []]
            if contract.get("model"):
                task["_runner_execution_model"] = str(contract.get("model"))
            if contract.get("channel"):
                task["_runner_execution_channel"] = str(contract.get("channel"))
        else:
            input_value = contract
            submit_value = contract
        task["_runner_input_fingerprint"] = _binding_digest(input_value)
        task["_runner_submit_request_digest"] = _binding_digest(submit_value)
    except Exception as exc:
        # Unit/compatibility fixtures may explicitly install a process-local test switch. There
        # is deliberately no JSON/env escape hatch: production cannot turn a made-up fingerprint
        # into authority merely by adding a config field.
        if ALLOW_TEST_FIXTURE_AUTHORIZATION and task.get("input_fingerprint"):
            fixture_shot = str(next(iter(task.get("affected_shots") or []), "fixture-target"))
            fixture_target = str(next(
                iter(task.get("affected_artifacts") or []),
                f"生产数据/test-fixtures/{task.get('id') or 'task'}.png",
            ))
            fixture_submit = str(
                task.get("submit_request_sha256") or task.get("request_sha256") or "fixture"
            )
            task["_runner_producer_contract"] = {
                "kind": "n2d_batch_test_fixture_binding",
                "version": 1,
                "input_fingerprint": task.get("input_fingerprint"),
                "submit_request_digest": fixture_submit,
                "records": [{
                    "shot": fixture_shot,
                    "target": fixture_target,
                    "input_fingerprint": str(task.get("input_fingerprint") or ""),
                    "submit_request_sha256": fixture_submit,
                }],
            }
            task["_runner_input_fingerprint"] = _binding_digest(task.get("input_fingerprint"))
            task["_runner_submit_request_digest"] = _binding_digest(
                task.get("submit_request_sha256") or task.get("request_sha256") or "fixture"
            )
        else:
            task.pop("_runner_producer_contract", None)
            task["_runner_input_fingerprint"] = ""
            task["_runner_submit_request_digest"] = ""
            task["_runner_producer_contract_issue"] = f"{type(exc).__name__}: {exc}"
    return production_execution_binding(task)


def production_task_scope(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rerun_scope": str(task.get("rerun_scope") or ""),
        "affected_shots": sorted({str(item) for item in task.get("affected_shots", []) if str(item)}),
        "affected_artifacts": sorted({str(item) for item in task.get("affected_artifacts", []) if str(item)}),
    }


def production_authorized_attempt(task: Mapping[str, Any]) -> int:
    """One approval authorizes exactly one claim attempt, never an unlimited retry loop."""
    attempts = max(0, int(task.get("attempts") or 0))
    return attempts if task.get("status") in {"running", "provider_pending"} and attempts > 0 else attempts + 1


def provider_recovery_checkpoint(root: str, task: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the durable provider checkpoint for a one-clip video task, if any."""
    return queue_mod.provider_submission_state({"root": root}, task)


def _only_recoverable_in_flight_issues(issues: Sequence[Any]) -> bool:
    texts = [str(item) for item in issues if str(item).strip()]
    allowed = (
        "consumption_id has uncertain in_flight provider state",
        "consumption_id already completed; provider replay blocked",
        "prior spend consumption has uncertain in_flight provider state",
    )
    return bool(texts) and all(any(fragment in text for fragment in allowed) for text in texts)


def production_task_digest(task: Dict[str, Any]) -> str:
    estimate = task.get("estimated_cost") if isinstance(task.get("estimated_cost"), dict) else {}
    try:
        amount = float(estimate.get("amount"))
    except (TypeError, ValueError):
        amount = -1.0
    binding = {
        "task_id": str(task.get("id") or ""),
        "idempotency_key": str(task.get("idempotency_key") or ""),
        "episode": queue_mod.normalize_episode(str(task.get("episode") or "")),
        "stage_key": str(task.get("stage_key") or ""),
        "attempt": production_authorized_attempt(task),
        "scope": production_task_scope(task),
        "estimated_cost": {
            "amount": amount,
            "currency": str(estimate.get("unit") or ""),
        },
        "execution": production_execution_binding(task),
    }
    return _canonical_json_digest(binding)


def production_authorization_digest(receipt: Dict[str, Any]) -> str:
    payload = {key: value for key, value in receipt.items() if key != "authorization_digest"}
    return _canonical_json_digest(payload)


def make_production_authorization(
    task: Dict[str, Any],
    *,
    approval_id: str,
    approver: str,
    model: str,
    channel: str,
    expires_at: Optional[str] = None,
    ceiling: Optional[float] = None,
    currency: Optional[str] = None,
    root: str = "",
    resolved_command: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a canonical signed-by-digest approval receipt for humans/control planes.

    SHA-256 is tamper evidence, not identity cryptography: the real approver identity remains a
    required audited field. A future remote approval service may replace this with a digital
    signature without changing the task-bound payload.
    """
    bound_task = deepcopy(task)
    command = str(
        resolved_command
        or bound_task.get("resolved_command")
        or bound_task.get("runner_command")
        or bound_task.get("command")
        or ""
    )
    bind_production_execution_context(root, bound_task, config or {}, command)
    execution = production_execution_binding(bound_task)
    if bound_task.get("_runner_producer_contract_issue"):
        raise ValueError(
            "cannot issue production authorization: "
            + str(bound_task.get("_runner_producer_contract_issue"))
        )
    if not execution["command_digest"]:
        raise ValueError("cannot issue production authorization without resolved command digest")
    if not execution["input_fingerprint"]:
        raise ValueError("cannot issue production authorization without canonical input_fingerprint")
    if not execution["submit_request_digest"] or not execution["producer_contract_digest"]:
        raise ValueError("cannot issue production authorization without canonical producer submit contract")
    estimate = bound_task.get("estimated_cost") if isinstance(bound_task.get("estimated_cost"), dict) else {}
    amount = float(estimate.get("amount") or 0.0) if ceiling is None else float(ceiling)
    unit = str(currency or estimate.get("unit") or "")
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    expiry = expires_at or (now + dt.timedelta(hours=1)).isoformat()
    receipt: Dict[str, Any] = {
        "version": 1,
        "approval_id": str(approval_id),
        "decision": "approved",
        "approver": str(approver),
        "issued_at": now.isoformat(),
        "expires_at": str(expiry),
        "task_id": str(bound_task.get("id") or ""),
        "idempotency_key": str(bound_task.get("idempotency_key") or ""),
        "task_digest": production_task_digest(bound_task),
        "attempt": production_authorized_attempt(bound_task),
        "stage_key": str(bound_task.get("stage_key") or ""),
        "episode": queue_mod.normalize_episode(str(bound_task.get("episode") or "")),
        "scope": production_task_scope(bound_task),
        "execution": execution,
        "model": str(model),
        "channel": str(channel),
        "ceiling": {"amount": amount, "currency": unit},
    }
    receipt["authorization_digest"] = production_authorization_digest(receipt)
    return receipt


def phase_envelope_input_digest(task: Dict[str, Any]) -> str:
    """Bind the v2 phase envelope to the full current executable input, not a label."""
    return _binding_digest({
        "execution": production_execution_binding(task),
        "scope": production_task_scope(task),
    })


def _phase_call_count(task: Mapping[str, Any]) -> int:
    contract = task.get("_runner_producer_contract")
    rows = contract.get("records") if isinstance(contract, Mapping) else None
    return max(1, len(rows)) if isinstance(rows, list) else 1


def _phase_cost(task: Mapping[str, Any]) -> Tuple[float, str]:
    estimate = task.get("estimated_cost") if isinstance(task.get("estimated_cost"), Mapping) else {}
    try:
        amount = float(estimate.get("amount"))
    except (TypeError, ValueError) as exc:
        raise ValueError("production task estimated_cost.amount missing/invalid") from exc
    currency = str(estimate.get("unit") or "").strip()
    if not math.isfinite(amount) or amount < 0 or not currency:
        raise ValueError("production task estimated_cost must be finite, non-negative, and have a unit")
    return amount, currency


def _phase_consumption_kwargs(task: Dict[str, Any]) -> Dict[str, Any]:
    model, channel = _execution_model_channel(task)
    amount, currency = _phase_cost(task)
    attempt = production_authorized_attempt(task)
    return {
        "stage": str(task.get("stage_key") or ""),
        "model": model,
        "channel": channel,
        "input_sha256": phase_envelope_input_digest(task),
        "scope": production_task_scope(task),
        "consumption_id": f"{task.get('id') or 'missing-task'}:{attempt}",
        "attempt_id": str(attempt),
        "calls": _phase_call_count(task),
        "cost": amount,
        "currency": currency,
    }


def recovered_spend_consumption(
    task: Dict[str, Any], authorization: Mapping[str, Any]
) -> Dict[str, Any]:
    """Reconstruct the already-consumed reservation binding without consuming again."""
    request = _phase_consumption_kwargs(task)
    row = {
        "consumption_id": request["consumption_id"],
        "attempt_id": request["attempt_id"],
        "calls": request["calls"],
        "cost": {"amount": request["cost"], "currency": request["currency"]},
        "stage": request["stage"],
        "model": request["model"],
        "channel": request["channel"],
        "input_sha256": request["input_sha256"],
        "scope": request["scope"],
        "state": "in_flight",
    }
    return {
        "status": "pass",
        "idempotent": True,
        "replay_blocked": True,
        "recovered": True,
        "envelope_id": str(authorization.get("envelope_id") or ""),
        "authorization_digest": str(authorization.get("authorization_digest") or ""),
        "consumption": row,
    }


def _parse_aware_datetime(value: Any) -> Optional[dt.datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(dt.timezone.utc)


def _execution_model_channel(task: Dict[str, Any]) -> Tuple[str, str]:
    model = str(
        task.get("_runner_execution_model")
        or task.get("model")
        or task.get("model_id")
        or task.get("backend_model")
        or ""
    ).strip()
    channel = str(
        task.get("_runner_execution_channel")
        or task.get("channel")
        or task.get("provider")
        or task.get("backend")
        or ""
    ).strip()
    return model, channel


def _bind_execution_context(task: Dict[str, Any], config: Dict[str, Any]) -> None:
    stage = str(task.get("stage_key") or "")
    owner = str(task.get("owner") or "")
    env = config.get("env") if isinstance(config.get("env"), dict) else {}
    for singular, plural, env_key, internal in (
        ("model", "models", "N2D_MODEL", "_runner_execution_model"),
        ("channel", "channels", "N2D_CHANNEL", "_runner_execution_channel"),
    ):
        if task.get(internal):
            continue
        value = task.get(singular)
        mapping = config.get(plural)
        if not value and isinstance(mapping, dict):
            value = mapping.get(stage) or mapping.get(owner) or mapping.get("*")
        if not value:
            value = config.get(singular) or env.get(env_key)
        if value:
            task[internal] = str(value)


def _authorization_issue(task: Dict[str, Any], root: str = "") -> Optional[str]:
    if (
        ALLOW_TEST_FIXTURE_AUTHORIZATION
        and task.get("input_fingerprint")
        and not task.get("_runner_producer_contract")
    ):
        fixture_command = str(task.get("resolved_command") or task.get("runner_command") or task.get("command") or "")
        bind_production_execution_context("", task, {}, fixture_command)
    receipt = task.get("_runner_production_authorization")
    if not isinstance(receipt, dict):
        return "missing task-bound production_authorization"
    if receipt.get("version") == spend_envelope_mod.VERSION:
        if not root:
            return "phase production authorization requires project root binding"
        try:
            result = spend_envelope_mod.verify(root, receipt, **_phase_consumption_kwargs(task))
        except (ValueError, spend_envelope_mod.SpendEnvelopeError) as exc:
            return f"phase production authorization invalid: {exc}"
        checkpoint = provider_recovery_checkpoint(root, task)
        recoverable = (
            checkpoint.get("state") == "provider_pending"
            and bool(checkpoint.get("provider_submit_id"))
            and _only_recoverable_in_flight_issues(result.get("issues") or [])
        )
        if result.get("status") != "pass" and not recoverable:
            return "phase production authorization blocked: " + "; ".join(
                str(item) for item in (result.get("issues") or [])
            )
        return None
    if receipt.get("version") != 1:
        return "production_authorization.version must be 1 or phase envelope version 2"
    declared_digest = str(receipt.get("authorization_digest") or "")
    if not declared_digest.startswith("sha256:") or not hmac.compare_digest(
        declared_digest,
        production_authorization_digest(receipt),
    ):
        return "production_authorization authorization_digest mismatch (tampered or non-canonical)"
    if str(receipt.get("decision") or "").strip().lower() not in {"approved", "authorized"}:
        return "production_authorization.decision must be approved"
    approval_id = str(receipt.get("approval_id") or "").strip()
    if not approval_id:
        return "production_authorization.approval_id is required"
    approver = str(receipt.get("approver") or "").strip()
    if not approver or approver.lower() in {"unknown", "system", "agent", "auto", "any", "test"}:
        return "production_authorization.approver must identify a real accountable approver"
    issued_at = _parse_aware_datetime(receipt.get("issued_at"))
    expires_at = _parse_aware_datetime(receipt.get("expires_at"))
    if issued_at is None:
        return "production_authorization.issued_at must be timezone-aware ISO-8601"
    if expires_at is None:
        return "production_authorization.expires_at must be timezone-aware ISO-8601"
    now = dt.datetime.now(dt.timezone.utc)
    if issued_at > now + dt.timedelta(minutes=5):
        return "production_authorization.issued_at is in the future"
    if expires_at <= now:
        return "production_authorization expired"
    if expires_at <= issued_at:
        return "production_authorization.expires_at must be after issued_at"
    idempotency_key = str(task.get("idempotency_key") or "")
    if not idempotency_key:
        return "production task missing idempotency_key; cannot bind authorization"
    if task.get("_runner_producer_contract_issue"):
        return "canonical producer contract unavailable: " + str(task.get("_runner_producer_contract_issue"))
    execution = production_execution_binding(task)
    if not execution.get("command_digest"):
        return "production execution missing resolved command digest"
    if not execution.get("input_fingerprint"):
        return "production execution missing canonical input_fingerprint"
    if not execution.get("submit_request_digest") or not execution.get("producer_contract_digest"):
        return "production execution missing canonical producer submit contract"
    expected = {
        "task_id": str(task.get("id") or ""),
        "idempotency_key": idempotency_key,
        "task_digest": production_task_digest(task),
        "stage_key": str(task.get("stage_key") or ""),
        "attempt": production_authorized_attempt(task),
        "episode": queue_mod.normalize_episode(str(task.get("episode") or "")),
        "scope": production_task_scope(task),
        "execution": execution,
    }
    actual = {
        "task_id": str(receipt.get("task_id") or ""),
        "idempotency_key": str(receipt.get("idempotency_key") or ""),
        "task_digest": str(receipt.get("task_digest") or ""),
        "stage_key": str(receipt.get("stage_key") or ""),
        "attempt": receipt.get("attempt"),
        "episode": queue_mod.normalize_episode(str(receipt.get("episode") or "")),
        "scope": receipt.get("scope"),
        "execution": receipt.get("execution"),
    }
    mismatches = [key for key in expected if actual[key] != expected[key]]
    if mismatches:
        return "production_authorization scope mismatch: " + ", ".join(mismatches)
    approved_model = str(receipt.get("model") or "").strip()
    approved_channel = str(receipt.get("channel") or "").strip()
    if not approved_model or not approved_channel:
        return "production_authorization.model and channel must be explicitly declared (concrete or any)"
    actual_model, actual_channel = _execution_model_channel(task)
    if approved_model.lower() != "any":
        if not actual_model:
            return f"production execution model missing; approval is bound to {approved_model}"
        if approved_model != actual_model:
            return f"production_authorization model mismatch: approved={approved_model} actual={actual_model}"
    if approved_channel.lower() != "any":
        if not actual_channel:
            return f"production execution channel missing; approval is bound to {approved_channel}"
        if approved_channel != actual_channel:
            return f"production_authorization channel mismatch: approved={approved_channel} actual={actual_channel}"
    estimate = task.get("estimated_cost") if isinstance(task.get("estimated_cost"), dict) else {}
    try:
        estimated_amount = float(estimate.get("amount"))
    except (TypeError, ValueError):
        return "production task estimated_cost.amount missing/invalid; cannot enforce authorization ceiling"
    estimated_currency = str(estimate.get("unit") or "").strip()
    if not math.isfinite(estimated_amount) or estimated_amount < 0 or not estimated_currency:
        return "production task estimated_cost must be finite, non-negative, and have a unit"
    ceiling = receipt.get("ceiling")
    if not isinstance(ceiling, dict):
        return "production_authorization.ceiling must contain amount and currency"
    try:
        ceiling_amount = float(ceiling.get("amount"))
    except (TypeError, ValueError):
        return "production_authorization.ceiling.amount invalid"
    ceiling_currency = str(ceiling.get("currency") or "").strip()
    if not math.isfinite(ceiling_amount) or ceiling_amount < 0 or not ceiling_currency:
        return "production_authorization.ceiling must be finite, non-negative, and have currency"
    if ceiling_currency != estimated_currency:
        return (
            "production_authorization ceiling currency mismatch: "
            f"approved={ceiling_currency} estimate={estimated_currency}"
        )
    if estimated_amount > ceiling_amount:
        return (
            "production task estimated cost exceeds authorization ceiling: "
            f"{estimated_amount} > {ceiling_amount} {ceiling_currency}"
        )
    return None


def _canonical_next_preflight_issue(
    root: str,
    task: Dict[str, Any],
    *,
    preview: bool = False,
) -> Optional[Dict[str, Any]]:
    """Validate the queue task against run.py's canonical current frontier.

    Production accepts either the legacy payment stop plus a valid receipt, or an exact
    ``needs_stage_execution`` card whose current v2 envelope probe is authorized.  Local no-BGM
    compose may also use ``needs_stage_execution`` without a payment receipt.  In every paid case
    this runner remains the only component allowed to consume authorization.
    """
    ep = str(task.get("episode") or "")
    try:
        na = run_mod.next_action(root, ep, preview=preview)
    except Exception as exc:
        return {"stop_reason": "next_preflight_error", "headline": str(exc)}
    stop = str(na.get("stop_reason") or "")
    card = na.get("action_card") or {}
    frontier = na.get("frontier")

    def issue(reason: str, headline: str = "") -> Dict[str, Any]:
        return {
            "stop_reason": reason,
            "headline": headline or card.get("headline") or "",
            "to_user": card.get("to_user") or "",
            "frontier": frontier,
            "gate": na.get("gate"),
        }

    if stop == "done" or not isinstance(frontier, dict):
        return issue(stop or "missing_frontier", "canonical frontier is complete or missing")
    task_stage = str(task.get("stage_key") or "")
    frontier_stage = str(frontier.get("stage_key") or "")
    frontier_ep = queue_mod.normalize_episode(str(frontier.get("ep") or ""))
    task_ep = queue_mod.normalize_episode(ep)
    if frontier_stage != task_stage or frontier_ep != task_ep:
        return issue(
            "frontier_mismatch",
            f"queued task {task_ep}/{task_stage} != current frontier {frontier_ep}/{frontier_stage}",
        )
    if task_stage in PRODUCTION_STAGE_KEYS:
        phase_probe = card.get("phase_spend_envelope") if isinstance(
            card.get("phase_spend_envelope"), Mapping
        ) else {}
        execution_effect = card.get("execution_effect") if isinstance(
            card.get("execution_effect"), Mapping
        ) else {}
        authorized_execution = (
            stop == "needs_stage_execution"
            and phase_probe.get("status") in {"authorized", "authorized_recovery"}
        )
        safe_local_compose = (
            task_stage == "compose"
            and stop == "needs_stage_execution"
            and execution_effect.get("safe_local_execution") is True
            and execution_effect.get("local_only") is True
            and execution_effect.get("paid") is False
        )
        if stop != "needs_payment_confirm" and not authorized_execution and not safe_local_compose:
            return issue(
                stop or "production_frontier_not_authorized",
                f"production frontier is not executable from batch (stop_reason={stop or 'missing'})",
            )
        if safe_local_compose:
            task["_runner_safe_local_execution"] = True
            return None
        auth_issue = _authorization_issue(task, root)
        if auth_issue:
            return issue("production_authorization_required", auth_issue)
        return None
    if stop in NEXT_PREFLIGHT_BLOCK_REASONS:
        return issue(stop)
    return None


def next_preflight_issue(root: str, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compatibility wrapper used by tests and callers; canonical check runs non-preview."""
    return _canonical_next_preflight_issue(root, task, preview=False)


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
    next_preflight: bool = True,
    build_dashboard: bool = True,
    record_telemetry: bool = True,
) -> Dict[str, Any]:
    started = time.monotonic()
    command = ""
    status = "fail"
    exit_code: Optional[int] = None
    note = ""
    stdout = ""
    stderr = ""
    execution_started = False
    acceptance_waiting = False
    output_verification: Dict[str, Any] = {"status": "not_run", "issues": []}
    try:
        stage_key = str(task.get("stage_key") or "")
        task.pop("_runner_safe_local_execution", None)
        _bind_execution_context(task, config)
        # Resolve and hash the exact command before authorization. A configured command is part
        # of the paid request; changing it invalidates the old receipt even when task_id is stable.
        command = resolve_command(root, task, config, command_override)
        bind_production_execution_context(root, task, config, command)
        task["_runner_output_baseline"] = producer_output_bindings(root, task)
        authorization = _authorization_from_config(task, config, root)
        if authorization is not None:
            task["_runner_production_authorization"] = authorization
        # Payment authorization and human acceptance are canonical boundaries, not optional
        # runner conveniences. In particular, --no-next-preflight must never turn
        # needs_acceptance_signoff into an executable review command.
        forced_preflight = not next_preflight and (
            stage_key in PRODUCTION_STAGE_KEYS or stage_key == "review"
        )
        if next_preflight or forced_preflight:
            issue = next_preflight_issue(root, task)
            if issue:
                if stage_key == "review" and issue.get("stop_reason") == "needs_acceptance_signoff":
                    # The canonical state says review work already reached the human boundary.
                    # Re-attest current outputs/gate below without running the configured review
                    # command, then let queue.mark persist an awaiting-acceptance receipt.
                    acceptance_waiting = True
                else:
                    prefix = (
                        (
                            f"production stage {stage_key} 强制 canonical preflight（关闭配置无效）· "
                            if stage_key in PRODUCTION_STAGE_KEYS
                            else "review human-acceptance 强制 canonical preflight（关闭配置无效）· "
                        )
                        if forced_preflight else ""
                    )
                    raise UnrunnableTask(
                        f"{prefix}next_preflight blocked: "
                        f"{issue.get('stop_reason')} · {issue.get('headline') or issue.get('to_user')}"
                    )
        task.setdefault("history", []).append({
            "ts": queue_mod.now_iso(),
            "action": "runner:start",
            "command": command,
        })
        if acceptance_waiting:
            issues = verify_task_completion(root, task)
            if issues:
                status = "qa_blocked"
                note = "acceptance evidence verification failed: " + "; ".join(issues[:6])
                output_verification = {"status": "fail", "issues": issues[:20]}
            else:
                status = "pass"
                exit_code = 0
                note = "needs_acceptance_signoff: command not rerun; current review evidence re-attested"
                output_verification = {"status": "pass", "issues": []}
        elif dry_run:
            status = "pass"
            note = "dry-run"
            exit_code = 0
        else:
            child_env = env_for_task(root, task, config)
            paid_stage_execution = (
                stage_key in PRODUCTION_STAGE_KEYS
                and task.get("_runner_safe_local_execution") is not True
            )
            if paid_stage_execution:
                expectation = paid_execution_expectation(task)
                if not expectation:
                    raise ProducerContractError(
                        f"{stage_key} paid execution expectation unavailable"
                    )
                child_env.update(
                    paid_execution_contract.environment_for_expectation(expectation)
                )
                task["_runner_paid_expectation"] = expectation
                authorization = task.get("_runner_production_authorization")
                if (
                    isinstance(authorization, Mapping)
                    and authorization.get("version") == spend_envelope_mod.VERSION
                ):
                    # Last local boundary before the provider subprocess.  A reservation is
                    # intentionally *not* executable-idempotent: if this process dies after a
                    # provider may have charged, the same id and every later call fail closed
                    # until durable provider completion evidence finalizes the reservation.
                    checkpoint = provider_recovery_checkpoint(root, task)
                    if checkpoint.get("state") == "unknown_paid_state":
                        raise UnrunnableTask(
                            "video provider paid state is unknown and has no submit_id; "
                            "automatic resubmission is blocked"
                        )
                    if (
                        checkpoint.get("state") == "provider_pending"
                        and checkpoint.get("provider_submit_id")
                    ):
                        task["_runner_provider_recovery"] = checkpoint
                        task["_runner_spend_consumption"] = recovered_spend_consumption(
                            task, authorization
                        )
                    else:
                        governance_issue = production_governance_interlock(root)
                        if governance_issue:
                            raise UnrunnableTask(governance_block_message(governance_issue))
                        task["_runner_spend_consumption"] = spend_envelope_mod.consume(
                            root, authorization, **_phase_consumption_kwargs(task)
                        )
            execution_started = True
            exit_code, stdout, stderr = run_process(
                command,
                shell=shell,
                timeout_sec=timeout_sec,
                env=child_env,
            )
            status = "pass" if exit_code == 0 else "fail"
            note = f"exit_code={exit_code}"
            if status == "fail" and stage_key == "video":
                checkpoint = provider_recovery_checkpoint(root, task)
                if (
                    checkpoint.get("state") == "provider_pending"
                    and checkpoint.get("provider_submit_id")
                ):
                    status = "provider_pending"
                    task["_runner_provider_recovery"] = checkpoint
                    note = (
                        f"provider job remains pending after runner exit_code={exit_code}; "
                        f"resume query-only submit_id={checkpoint.get('provider_submit_id')}"
                    )
                elif checkpoint.get("state") in {
                    "unknown_paid_state",
                    "provider_terminal_failure",
                }:
                    status = "qa_blocked"
                    task["_runner_provider_recovery"] = checkpoint
                    note = (
                        "provider state cannot be replayed safely; automatic resubmission blocked "
                        f"({checkpoint.get('state')})"
                    )
            if paid_stage_execution:
                producer_contract = task.get("_runner_producer_contract")
                if (
                    ALLOW_TEST_FIXTURE_AUTHORIZATION
                    and isinstance(producer_contract, Mapping)
                    and producer_contract.get("kind") == "n2d_batch_test_fixture_binding"
                ):
                    # Unit fixtures still cross the same on-disk producer-owned boundary.  The
                    # only test concession is synthesizing the producer call itself; queue
                    # completion never trusts a fabricated in-memory green status.
                    fixture_env = dict(child_env)
                    fixture_env.update(paid_execution_contract.environment_for_expectation(expectation))
                    with _temporary_environment(fixture_env):
                        for expected_row in expectation.get("records") or []:
                            fixture_path = (Path(root) / str(expected_row.get("target") or "")).resolve()
                            fixture_path.parent.mkdir(parents=True, exist_ok=True)
                            from PIL import Image
                            Image.new("RGB", (2, 2), (0, 0, 0)).save(fixture_path)
                            identity = str(expected_row.get("clip") or expected_row.get("shot") or "")
                            paid_execution_contract.enforce_expected_paid_request(
                                stage=stage_key,
                                identity=identity,
                                target=str(expected_row.get("target") or ""),
                                input_fingerprint=str(expected_row.get("input_fingerprint") or ""),
                                submit_request_sha256=str(expected_row.get("submit_request_sha256") or ""),
                            )
                    paid_receipts = paid_execution_contract.verify_expected_receipts(
                        Path(root), expectation
                    )
                    task["_runner_verified_outputs"] = producer_output_bindings(root, task)
                else:
                    paid_receipts = paid_execution_contract.verify_expected_receipts(
                        Path(root), expectation
                    )
                task["_runner_paid_receipts"] = paid_receipts
                if status == "pass" and paid_receipts.get("status") != "pass":
                    status = "fail"
                    note = "paid boundary verification failed: " + "; ".join(
                        str(item) for item in (paid_receipts.get("issues") or [])[:6]
                    )
            # 生产阶段不可跳过后置条件；--no-verify-outputs 只用于非生产工具任务。
            effective_verify_outputs = verify_outputs or stage_key in PRODUCTION_STAGE_KEYS
            if status == "pass" and effective_verify_outputs:
                issues = verify_task_completion(root, task)
                if issues:
                    status = "fail"
                    note = "verification failed: " + "; ".join(issues[:6])
                    output_verification = {"status": "fail", "issues": issues[:20]}
                else:
                    output_verification = {"status": "pass", "issues": []}
            elif status == "pass":
                output_verification = {"status": "not_applicable", "issues": []}
            if (
                status == "pass"
                and paid_stage_execution
                and isinstance(task.get("_runner_spend_consumption"), Mapping)
            ):
                authorization = task.get("_runner_production_authorization")
                consumption = task["_runner_spend_consumption"].get("consumption") or {}
                completion_evidence = {
                    "kind": "n2d_provider_completion_evidence",
                    "paid_execution_receipts": dict(task.get("_runner_paid_receipts") or {}),
                    "producer_output_bindings": list(task.get("_runner_verified_outputs") or []),
                }
                task["_runner_spend_completion"] = spend_envelope_mod.finalize(
                    root,
                    authorization,
                    consumption_id=str(consumption.get("consumption_id") or ""),
                    evidence=completion_evidence,
                )
    except subprocess.TimeoutExpired as exc:
        checkpoint = provider_recovery_checkpoint(root, task)
        if (
            checkpoint.get("state") == "provider_pending"
            and checkpoint.get("provider_submit_id")
        ):
            status = "provider_pending"
        elif checkpoint.get("state") in {"unknown_paid_state", "provider_terminal_failure"}:
            status = "qa_blocked"
        else:
            status = "fail"
        if status == "provider_pending":
            task["_runner_provider_recovery"] = checkpoint
        exit_code = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        note = (
            f"provider query timeout after {timeout_sec}s; resume original "
            f"submit_id={checkpoint.get('provider_submit_id')}"
            if status == "provider_pending"
            else "provider paid state cannot be replayed safely after timeout; resubmission blocked"
            if status == "qa_blocked"
            else f"timeout after {timeout_sec}s"
        )
    except UnrunnableTask as exc:
        status = "fail"
        note = str(exc)
    except Exception as exc:  # pragma: no cover - defensive guard for worker
        checkpoint = provider_recovery_checkpoint(root, task)
        if (
            str(task.get("stage_key") or "") == "video"
            and checkpoint.get("state") == "provider_pending"
            and checkpoint.get("provider_submit_id")
        ):
            status = "provider_pending"
            task["_runner_provider_recovery"] = checkpoint
            note = (
                f"{type(exc).__name__}: {exc}; provider submit is durable, resume query-only "
                f"submit_id={checkpoint.get('provider_submit_id')}"
            )
        elif (
            str(task.get("stage_key") or "") == "video"
            and checkpoint.get("state") in {"unknown_paid_state", "provider_terminal_failure"}
        ):
            status = "qa_blocked"
            task["_runner_provider_recovery"] = checkpoint
            note = f"{type(exc).__name__}: {exc}; provider state cannot be replayed safely"
        else:
            status = "fail"
            note = f"{type(exc).__name__}: {exc}"
    duration = time.monotonic() - started
    error_class = queue_mod.classify_error(note, {"exit_code": exit_code, "stdout": stdout, "stderr": stderr, "note": note}) if status == "fail" else ""
    task["last_runner"] = {
        "command": command,
        "status": status,
        "exit_code": exit_code,
        "error_class": error_class,
        "duration_sec": round(duration, 3),
        "stdout": truncate(stdout),
        "stderr": truncate(stderr),
        "note": note,
        "execution_started": execution_started,
        "finished_at": queue_mod.now_iso(),
        "completion": {
            "output_verification": output_verification,
            "post_gate": {"status": "pending"},
        },
    }
    authorization = task.pop("_runner_production_authorization", None)
    execution_model = task.pop("_runner_execution_model", None)
    execution_channel = task.pop("_runner_execution_channel", None)
    command_digest = task.pop("_runner_command_digest", None)
    input_fingerprint = task.pop("_runner_input_fingerprint", None)
    submit_request_digest = task.pop("_runner_submit_request_digest", None)
    producer_contract = task.pop("_runner_producer_contract", None)
    producer_contract_issue = task.pop("_runner_producer_contract_issue", None)
    paid_expectation = task.pop("_runner_paid_expectation", None)
    paid_receipts = task.pop("_runner_paid_receipts", None)
    spend_consumption = task.pop("_runner_spend_consumption", None)
    spend_completion = task.pop("_runner_spend_completion", None)
    provider_recovery = task.pop("_runner_provider_recovery", None)
    safe_local_execution = bool(task.pop("_runner_safe_local_execution", False))
    output_baseline = task.pop("_runner_output_baseline", None)
    verified_outputs = task.pop("_runner_verified_outputs", None)
    if isinstance(authorization, dict):
        task["last_runner"]["authorization"] = dict(authorization)
    task["last_runner"]["execution_binding"] = {
        "model": execution_model or "",
        "channel": execution_channel or "",
        "command_digest": command_digest or "",
        "input_fingerprint": input_fingerprint or "",
        "submit_request_digest": submit_request_digest or "",
        "producer_contract_digest": _binding_digest(producer_contract),
        "producer_contract": dict(producer_contract) if isinstance(producer_contract, Mapping) else None,
        "producer_contract_issue": producer_contract_issue or "",
        "paid_expectation_digest": str(paid_expectation.get("digest") or "")
        if isinstance(paid_expectation, Mapping) else "",
    }
    task["last_runner"]["completion"]["producer_output_baseline"] = output_baseline or []
    task["last_runner"]["completion"]["producer_output_bindings"] = verified_outputs or []
    task["last_runner"]["completion"]["paid_execution_receipts"] = (
        dict(paid_receipts) if isinstance(paid_receipts, Mapping) else {}
    )
    task["last_runner"]["completion"]["paid_execution_expectation"] = (
        dict(paid_expectation) if isinstance(paid_expectation, Mapping) else {}
    )
    task["last_runner"]["completion"]["phase_spend_consumption"] = (
        dict(spend_consumption) if isinstance(spend_consumption, Mapping) else {}
    )
    task["last_runner"]["completion"]["phase_spend_completion"] = (
        dict(spend_completion) if isinstance(spend_completion, Mapping) else {}
    )
    task["last_runner"]["completion"]["provider_recovery"] = (
        dict(provider_recovery) if isinstance(provider_recovery, Mapping) else {}
    )
    task["last_runner"]["completion"]["safe_local_execution"] = safe_local_execution
    task.setdefault("history", []).append({
        "ts": queue_mod.now_iso(),
        "action": f"runner:{status}",
        "exit_code": exit_code,
        "note": note,
    })
    if record_telemetry:
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
                build=build_dashboard,
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
    next_preflight: bool = True,
    auto_gate: bool = True,
) -> List[Dict[str, Any]]:
    if dry_run:
        # Defensive API guard: a caller that already supplied claimed-looking tasks still gets
        # a read-only preview. Never mark/heartbeat/dashboard from a dry-run code path.
        return [
            {
                "id": task.get("id"),
                "episode": task.get("episode"),
                "stage_key": task.get("stage_key"),
                "runner_status": "would_run",
                "queue_status": task.get("status"),
                "attempts": task.get("attempts"),
                "exit_code": None,
                "note": "dry-run preview; queue not mutated",
            }
            for task in claimed
        ]
    results: List[Dict[str, Any]] = []
    # 同一 cycle 内每个任务只追加事件、不各自重建仪表盘；循环结束统一重建一次（见 append_runner_event）。
    defer_build = len(claimed) > 1 and not no_dashboard
    gate_refreshed_any = False
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
                next_preflight=next_preflight,
                build_dashboard=not defer_build,
                record_telemetry=False,
            )
        finally:
            stop_evt.set()
            if hb is not None:
                hb.join(timeout=2)
        # 命令成功只是候选完成。先验证 post gate，再以结构化 completion evidence 提交；
        # gate BLOCK/异常停在 qa_blocked，绝不先 mark done 再 best-effort 补门禁。
        gate_stage = str(task.get("gate_stage") or _task_stage_spec(task).get("gate_stage") or "").strip()
        production_stage = str(task.get("stage_key") or "") in PRODUCTION_STAGE_KEYS
        gate_refreshed: Optional[Dict[str, Any]] = None
        post_gate: Dict[str, Any] = {"status": "not_applicable" if not gate_stage else "pending"}
        if result["status"] == "pass" and gate_stage and (auto_gate or production_stage):
            try:
                gate_refreshed = refresh_gate(root, str(task.get("episode") or ""), gate_stage)
                gate_refreshed_any = True
                gate_ok = (
                    isinstance(gate_refreshed, dict)
                    and gate_refreshed.get("exit_code") == 0
                    and gate_refreshed.get("blocks") == 0
                )
                post_gate = {
                    "status": "pass" if gate_ok else "block",
                    **(gate_refreshed if isinstance(gate_refreshed, dict) else {}),
                }
                if not gate_ok:
                    result["status"] = "qa_blocked"
                    result["note"] = (
                        f"post gate blocked: stage={gate_stage} "
                        f"exit_code={gate_refreshed.get('exit_code') if isinstance(gate_refreshed, dict) else 'missing'} "
                        f"blocks={gate_refreshed.get('blocks') if isinstance(gate_refreshed, dict) else 'missing'}"
                    )
            except Exception as exc:
                gate_refreshed = {"stage": gate_stage, "error": f"{type(exc).__name__}: {exc}"}
                post_gate = {"status": "error", **gate_refreshed}
                result["status"] = "qa_blocked"
                result["note"] = f"post gate error: stage={gate_stage} · {type(exc).__name__}: {exc}"
        elif result["status"] == "pass" and gate_stage:
            post_gate = {"status": "skipped", "stage": gate_stage}

        last_runner = result["task"].setdefault("last_runner", {})
        completion = last_runner.setdefault("completion", {})
        completion["post_gate"] = post_gate
        if result["status"] == "qa_blocked":
            last_runner["status"] = "qa_blocked"
            last_runner["error_class"] = "preflight_block"
            last_runner["note"] = result["note"]
            result["task"].setdefault("history", []).append({
                "ts": queue_mod.now_iso(),
                "action": "runner:qa_blocked",
                "note": result["note"],
            })

        # 最终 telemetry 只写一次，记录 gate 后的 canonical runner status。
        try:
            append_runner_event(
                root,
                result["task"],
                command=str(last_runner.get("command") or ""),
                status=str(result["status"]),
                exit_code=result["exit_code"],
                duration_sec=float(last_runner.get("duration_sec") or 0.0),
                dry_run=False,
                error=result["note"] if result["status"] != "pass" else "",
                no_dashboard=no_dashboard,
                build=not defer_build,
            )
        except Exception as exc:
            last_runner["telemetry_error"] = f"{type(exc).__name__}: {exc}"

        # 锁内重读最新队列再 mark，并校验 worker/attempt，避免租约过期后的旧 worker 覆盖新认领。
        try:
            marked = queue_mod.mark(
                root,
                task_id,
                result["status"],
                result["note"],
                runner=last_runner,
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
        if marked.get("status") == "qa_blocked" and result["status"] == "pass":
            result["status"] = "qa_blocked"
            result["note"] = str(marked.get("last_note") or "canonical completion was QA/budget blocked")
        record = {
            "id": marked.get("id"),
            "episode": marked.get("episode"),
            "stage_key": marked.get("stage_key"),
            "runner_status": result["status"],
            "queue_status": marked.get("status"),
            "attempts": marked.get("attempts"),
            "exit_code": result["exit_code"],
            "note": result["note"],
        }
        if gate_refreshed is not None:
            record["gate_refreshed"] = gate_refreshed
        results.append(record)
        if stop_on_fail and result["status"] != "pass":
            break
    if not no_dashboard and (defer_build or gate_refreshed_any):
        # cycle 内已追加全部事件（含自动门禁重跑），这里统一重建一次（best-effort，失败不影响已 mark 的任务）。
        try:
            dashboard_mod.build(root, write=True)
        except Exception:  # pragma: no cover - 仪表盘重建 best-effort
            pass
    return results


def _preview_candidates(root: str, limit: Optional[int]) -> List[Dict[str, Any]]:
    ledger = queue_mod.load_queue(root)
    max_concurrency = int(ledger.get("max_concurrency") or 1)
    running = sum(1 for task in ledger.get("tasks", []) if task.get("status") == "running")
    capacity = max(0, max_concurrency - running)
    if limit is not None:
        capacity = min(capacity, max(0, int(limit)))
    ready = [
        deepcopy(task)
        for task in sorted(ledger.get("tasks", []), key=lambda item: int(item.get("priority", 999999)))
        if task.get("status") in {"queued", "retry_queued"}
    ]
    return ready[:capacity]


def _preview_once(
    root: str,
    *,
    limit: Optional[int],
    config: Dict[str, Any],
    command_override: Optional[str],
    next_preflight: bool,
    worker: str,
) -> Dict[str, Any]:
    candidates = _preview_candidates(root, limit)
    results: List[Dict[str, Any]] = []
    for task in candidates:
        issue: Optional[Dict[str, Any]] = None
        _bind_execution_context(task, config)
        try:
            command = resolve_command(root, task, config, command_override)
            bind_production_execution_context(root, task, config, command)
        except Exception as exc:
            command = ""
            issue = {"stop_reason": "configuration", "headline": str(exc)}
        authorization = _authorization_from_config(task, config, root)
        if authorization is not None:
            task["_runner_production_authorization"] = authorization
        stage_key = str(task.get("stage_key") or "")
        if issue is None and (next_preflight or stage_key in PRODUCTION_STAGE_KEYS):
            issue = _canonical_next_preflight_issue(root, task, preview=True)
        task.pop("_runner_production_authorization", None)
        task.pop("_runner_execution_model", None)
        task.pop("_runner_execution_channel", None)
        task.pop("_runner_command_digest", None)
        task.pop("_runner_input_fingerprint", None)
        task.pop("_runner_submit_request_digest", None)
        task.pop("_runner_producer_contract", None)
        task.pop("_runner_producer_contract_issue", None)
        results.append({
            "id": task.get("id"),
            "episode": task.get("episode"),
            "stage_key": stage_key,
            "runner_status": "blocked" if issue else "would_run",
            "queue_status": task.get("status"),
            "attempts": task.get("attempts"),
            "exit_code": None,
            "command": command,
            "note": (
                f"dry-run blocked: {issue.get('stop_reason')} · {issue.get('headline') or issue.get('to_user') or ''}"
                if issue else "dry-run preview; queue not claimed or marked"
            ),
        })
    return {
        "claimed": 0,
        "previewed": len(candidates),
        "processed": 0,
        "results": results,
        "worker": worker,
        "config": config.get("_path"),
        "dry_run": True,
    }


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
    verify_outputs: bool = True,
    stop_on_fail: bool = False,
    worker: Optional[str] = None,
    lease_seconds: int = queue_mod.DEFAULT_LEASE_SECONDS,
    next_preflight: Optional[bool] = None,
    auto_gate: bool = True,
    task_id: Optional[str] = None,
    expected_plan_digest: Optional[str] = None,
    episode: Optional[str] = None,
    stage_key: Optional[str] = None,
) -> Dict[str, Any]:
    config = load_config(root, config_path)
    worker = worker or queue_mod.default_worker()
    # 配置可关：batch_runner.json 里 "auto_gate": false → 关掉返工后自动重跑门禁（CLI --no-gate 同效）。
    effective_auto_gate = auto_gate and bool(config.get("auto_gate", True))
    # 安全默认：批处理默认也消费单集编排器的硬阻断，只有项目配置或 CLI 显式关闭才绕过。
    effective_next_preflight = bool(config.get("next_preflight", True)) if next_preflight is None else bool(next_preflight)
    if dry_run:
        if task_id or expected_plan_digest or episode or stage_key:
            raise ValueError("exact task binding is executable-only; omit --dry-run")
        return _preview_once(
            root,
            limit=limit,
            config=config,
            command_override=command_override,
            next_preflight=effective_next_preflight,
            worker=worker,
        )
    governance_issue = production_governance_interlock(root)
    if governance_issue:
        return {
            "claimed": 0,
            "processed": 0,
            "results": [{
                "id": str(task_id or ""),
                "episode": str(episode or ""),
                "stage_key": str(stage_key or ""),
                "runner_status": "fail",
                "queue_status": "blocked_governance",
                "attempts": None,
                "exit_code": None,
                "note": governance_block_message(governance_issue),
                "governance": governance_issue,
            }],
            "worker": worker,
            "config": config.get("_path"),
        }
    exact_values = (task_id, expected_plan_digest, episode, stage_key)
    if any(value is not None for value in exact_values) and not all(
        str(value or "").strip() for value in exact_values
    ):
        raise ValueError(
            "exact claim requires --task-id, --expected-plan-digest, --episode and --stage together"
        )
    # Both paths reclaim inside the same queue transaction.  Exact action cards never fall
    # through to a different priority row if their task id or immutable plan digest changed.
    if all(str(value or "").strip() for value in exact_values):
        try:
            claimed = queue_mod.claim_exact(
                root,
                task_id=str(task_id),
                expected_plan_digest=str(expected_plan_digest),
                episode=str(episode),
                stage_key=str(stage_key),
                worker=worker,
                lease_seconds=lease_seconds,
            )
        except (FileNotFoundError, TimeoutError, ValueError, RuntimeError) as exc:
            # A stale action card or a governance race is an expected fail-closed outcome,
            # not an interpreter crash.  Keep the exact error visible in the machine result
            # and never fall through to a generic queue claim.
            return {
                "claimed": 0,
                "processed": 0,
                "results": [{
                    "id": str(task_id),
                    "episode": str(episode),
                    "stage_key": str(stage_key),
                    "runner_status": "fail",
                    "queue_status": "blocked_exact_claim",
                    "attempts": None,
                    "exit_code": None,
                    "note": f"exact hash-bound claim blocked: {exc}",
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                }],
                "worker": worker,
                "config": config.get("_path"),
            }
        if not claimed:
            return {
                "claimed": 0,
                "processed": 0,
                "results": [{
                    "id": str(task_id),
                    "episode": str(episode),
                    "stage_key": str(stage_key),
                    "runner_status": "fail",
                    "queue_status": "not_claimable",
                    "attempts": None,
                    "exit_code": None,
                    "note": "exact hash-bound task is not claimable; no fallback task was run",
                }],
                "worker": worker,
                "config": config.get("_path"),
            }
    else:
        claimed = queue_mod.claim(
            root, limit=limit, worker=worker, lease_seconds=lease_seconds
        )
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
        next_preflight=effective_next_preflight,
        auto_gate=effective_auto_gate,
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
    next_preflight: Optional[bool] = None,
    auto_gate: bool = True,
) -> Dict[str, Any]:
    if dry_run:
        # A dry-run cannot drain a queue because it intentionally changes no state. Preview one
        # capacity-limited cycle and report zero processed work.
        preview = run_once(
            root,
            limit=limit,
            config_path=config_path,
            command_override=command_override,
            shell=shell,
            timeout_sec=timeout_sec,
            dry_run=True,
            no_dashboard=True,
            verify_outputs=verify_outputs,
            stop_on_fail=stop_on_fail,
            worker=worker,
            lease_seconds=lease_seconds,
            next_preflight=next_preflight,
            auto_gate=auto_gate,
        )
        return {
            "processed": 0,
            "previewed": preview.get("previewed", 0),
            "results": preview.get("results", []),
            "dry_run": True,
        }
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
            next_preflight=next_preflight,
            auto_gate=auto_gate,
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
    ap.add_argument("--task-id", help="claim only this action-card task id")
    ap.add_argument("--expected-plan-digest", help="required immutable plan digest for --task-id")
    ap.add_argument("--episode", help="current episode bound by an exact action card")
    ap.add_argument("--stage", dest="exact_stage", help="current stage bound by an exact action card")
    ap.add_argument("--max-tasks", type=int, help="hard cap when using --until-empty")
    ap.add_argument("--sleep-sec", type=float, default=0.0)
    ap.add_argument("--config", help="batch runner config; defaults to 生产数据/batch_runner.json")
    ap.add_argument("--command", help="override command template for every claimed task")
    ap.add_argument("--shell", action="store_true", help="execute command through the shell")
    ap.add_argument("--timeout-sec", type=float)
    ap.add_argument("--dry-run", action="store_true", help="read-only preview; do not claim, execute, write telemetry, or mark")
    ap.add_argument("--no-dashboard", action="store_true", help="do not write runner telemetry to n2d-dashboard")
    verify = ap.add_mutually_exclusive_group()
    verify.add_argument("--verify-outputs", dest="verify_outputs", action="store_true",
                        help="after exit 0, require contract outputs and progress columns (default; retained for emphasis)")
    verify.add_argument("--no-verify-outputs", dest="verify_outputs", action="store_false",
                        help="skip verification only for non-production utility tasks; voice/image/video/compose still force it")
    ap.set_defaults(verify_outputs=True)
    ap.add_argument("--stop-on-fail", action="store_true")
    ap.add_argument("--worker", help="worker id（默认 host:pid）；多 worker 各起一个；--resume 自愈需稳定 id")
    ap.add_argument("--lease-seconds", type=int, default=queue_mod.DEFAULT_LEASE_SECONDS,
                    help=f"任务租约秒数（执行期自动心跳续租）；默认 {queue_mod.DEFAULT_LEASE_SECONDS}")
    ap.add_argument("--resume", action="store_true",
                    help="开跑前先回收本 --worker 上次崩溃残留的 running 任务（断点恢复），再继续认领")
    ap.add_argument("--no-gate", action="store_true",
                    help="关掉非生产任务的自动 gate；voice/image/video/compose 的声明 gate 仍强制执行")
    ap.add_argument("--next-preflight", action="store_true",
                    help="显式开启执行前 n2d/run.py next 动作卡（默认已开启，保留该参数用于兼容/强调）")
    ap.add_argument("--no-next-preflight", action="store_true",
                    help="显式关闭执行前 n2d/run.py next 动作卡；仅用于已确认 wrapper 自带等价 gate 的场景")
    ap.add_argument("--recheck", action="store_true",
                    help="跑完后用 生产数据/ 最新审查产物的指纹复检：问题消失的返工任务标 resolved、复发的 reopen"
                         "（闭环复检；返工后门禁已自动刷新，--recheck 即对现状判定）")
    ap.add_argument("--coarse-recheck", action="store_true",
                    help="--recheck 时启用粗粒度回退：精确指纹对不上但该(集×阶段×维度)桶仍有问题则不判 resolved 而 reopen，"
                         "堵定位串大改导致的漏放")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    if ns.until_empty and any(
        value for value in (ns.task_id, ns.expected_plan_digest, ns.episode, ns.exact_stage)
    ):
        raise SystemExit("--until-empty cannot be combined with exact action-card claim options")
    root = ns.root.rstrip("/")
    worker = ns.worker or queue_mod.default_worker()
    cli_next_preflight: Optional[bool]
    if ns.no_next_preflight:
        cli_next_preflight = False
    elif ns.next_preflight:
        cli_next_preflight = True
    else:
        cli_next_preflight = None
    if ns.resume and not ns.dry_run:
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
            next_preflight=cli_next_preflight,
            auto_gate=not ns.no_gate,
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
            next_preflight=cli_next_preflight,
            auto_gate=not ns.no_gate,
            task_id=ns.task_id,
            expected_plan_digest=ns.expected_plan_digest,
            episode=ns.episode,
            stage_key=ns.exact_stage,
        )
    if ns.recheck and not ns.dry_run:
        try:
            queue = queue_mod.load_queue(root)
            active = queue_mod.collect_active_fingerprints(root)
            coarse_active = queue_mod.collect_active_fingerprints(root, coarse=True) if ns.coarse_recheck else None
            queue_mod.reconcile_resolved(queue, active, coarse_active=coarse_active)
            queue_mod.save_queue(root, queue)
            info = queue.get("recheck", {})
            tail = f" reopened_coarse={info.get('reopened_coarse', 0)}" if coarse_active is not None else ""
            print(f"[recheck] resolved={info.get('resolved', 0)} reopened={info.get('reopened', 0)}{tail}"
                  f"（现存一致性问题指纹 {len(active)} 个）", file=sys.stderr)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[recheck] 跳过：{exc}", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not any(item.get("runner_status") in {"fail", "qa_blocked"} for item in result.get("results", [])) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
