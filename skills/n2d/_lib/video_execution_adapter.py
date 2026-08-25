#!/usr/bin/env python3
"""Executable video-backend adapter contract v2 for n2d.

The capability catalog answers what a model/channel can do.  This module answers
the separate operational question: can this machine execute the selected route
right now, through which command contract, with which retry/idempotency rules?

Third-party SDKs are deliberately kept outside the repository.  A project may
register a local wrapper in ``生产数据/video_execution_adapters.json``; n2d then
passes a stable JSON request to that wrapper without knowing vendor credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

try:
    from n2d_platform_profiles import effective_frame_backend, normalize_video_backend
except ImportError:  # pragma: no cover
    from .n2d_platform_profiles import effective_frame_backend, normalize_video_backend  # type: ignore


ADAPTER_KIND = "n2d_video_execution_adapter"
REGISTRY_KIND = "n2d_video_execution_adapter_registry"
REQUEST_KIND = "n2d_video_execution_request"
ADAPTER_VERSION = 2
REGISTRY_REL = Path("生产数据") / "video_execution_adapters.json"

MANUAL_VALUES = {"", "manual", "人工", "手动", "手工", "none", "off", "关闭", "无"}
STANDARD_OPERATIONS = ("submit", "query", "cancel")
MULTISHOT_OPERATIONS = ("multishot_submit", "multishot_query", "multishot_cancel")
CORRECTION_OPERATIONS = ("edit", "extend", "replace_range", "remix")

# Built-ins describe only the executable surface.  Creative/model capability
# remains in n2d_platform_profiles and current-evidence files.
BUILTIN_ADAPTERS: Dict[str, Dict[str, Any]] = {
    "dreamina": {
        "kind": ADAPTER_KIND,
        "version": ADAPTER_VERSION,
        "adapter_id": "dreamina_cli_v2",
        "execution_backend": "dreamina",
        "provider": "dreamina",
        "implementation": "embedded",
        "command": ["dreamina"],
        "operations": ["submit", "query"],
        "capabilities": {
            "idempotency": "runner_guarded",
            "async_query": True,
            "cancel": False,
            "multishot": False,
            "batch_async": False,
        },
        "retry_policy": {
            "max_attempts": 3,
            "retryable_classes": ["rate_limited", "transient_network", "provider_5xx"],
            "never_retry_classes": ["auth", "quota", "invalid_request", "policy", "unknown_paid_state"],
        },
        "result_contract": {
            "submit_id": "submit_id",
            "status": "gen_status",
            "output_path": "output_path",
            "error": "fail_reason",
        },
    },
}


def _canon(value: Any) -> str:
    raw = str(value or "").strip()
    return normalize_video_backend(raw, default="") or re.sub(r"[^a-z0-9._-]+", "_", raw.lower()).strip("_")


def registry_path(root: str | Path) -> Path:
    return Path(root) / REGISTRY_REL


def load_registry(root: str | Path) -> Dict[str, Any]:
    path = registry_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"kind": REGISTRY_KIND, "version": ADAPTER_VERSION, "adapters": {}}
    if not isinstance(data, dict):
        return {"kind": REGISTRY_KIND, "version": ADAPTER_VERSION, "adapters": {}}
    adapters = data.get("adapters")
    if isinstance(adapters, list):
        adapters = {
            str(row.get("execution_backend") or row.get("adapter_id") or ""): row
            for row in adapters if isinstance(row, dict)
        }
    data["adapters"] = adapters if isinstance(adapters, dict) else {}
    return data


def _command_tokens(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return shlex.split(value)
    return []


def normalize_adapter(raw: Mapping[str, Any], *, key: str = "") -> Dict[str, Any]:
    operations = raw.get("operations")
    if isinstance(operations, Mapping):
        operation_names = [str(name) for name, enabled in operations.items() if enabled is not False]
    else:
        operation_names = [str(name) for name in (operations or [])]
    execution_backend = _canon(raw.get("execution_backend") or key)
    command = _command_tokens(raw.get("command"))
    return {
        "kind": ADAPTER_KIND,
        "version": ADAPTER_VERSION,
        "adapter_id": str(raw.get("adapter_id") or f"{execution_backend}_wrapper_v2"),
        "execution_backend": execution_backend,
        "provider": str(raw.get("provider") or execution_backend),
        "model": str(raw.get("model") or ""),
        "channel": str(raw.get("channel") or ""),
        "implementation": str(raw.get("implementation") or "wrapper_command"),
        "command": command,
        "operations": sorted(set(operation_names)),
        "operation_commands": dict(raw.get("operation_commands") or {}),
        "capabilities": dict(raw.get("capabilities") or {}),
        "retry_policy": dict(raw.get("retry_policy") or {}),
        "result_contract": dict(raw.get("result_contract") or {}),
        "source": str(raw.get("source") or "project_registry"),
    }


def adapter_for(
    root: str | Path | None,
    backend: Any,
    channel: Any = "",
) -> Optional[Dict[str, Any]]:
    canonical = _canon(backend)
    channel_key = _canon(channel)
    execution = effective_frame_backend(canonical, channel_key)
    if root is not None:
        registry = load_registry(root)
        candidates = (execution, canonical, channel_key)
        for key in candidates:
            raw = (registry.get("adapters") or {}).get(key)
            if isinstance(raw, Mapping):
                return normalize_adapter(raw, key=key)
    raw_builtin = BUILTIN_ADAPTERS.get(execution)
    return normalize_adapter(raw_builtin, key=execution) if raw_builtin else None


def _command_available(command: Sequence[str], which=shutil.which) -> bool:
    if not command:
        return False
    binary = str(command[0])
    if os.path.isabs(binary) or "/" in binary:
        return Path(binary).is_file() and os.access(binary, os.X_OK)
    return which(binary) is not None


def execution_status(
    root: str | Path | None,
    backend: Any,
    channel: Any = "",
    *,
    which=shutil.which,
    required_operations: Sequence[str] = ("submit", "query"),
) -> Dict[str, Any]:
    canonical = _canon(backend)
    channel_key = _canon(channel)
    execution = effective_frame_backend(canonical, channel_key)
    if str(backend or "").strip().lower() in MANUAL_VALUES or execution in MANUAL_VALUES:
        return {
            "kind": "n2d_video_execution_status",
            "version": ADAPTER_VERSION,
            "backend": canonical,
            "channel": channel_key,
            "execution_backend": execution or canonical,
            "state": "manual_required",
            "automated": False,
            "route_executable": True,
            "operations": [],
            "missing_operations": list(required_operations),
            "message": "manual backend: prepare/export job package, then register the returned media",
        }
    adapter = adapter_for(root, canonical, channel_key)
    if adapter is None:
        return {
            "kind": "n2d_video_execution_status",
            "version": ADAPTER_VERSION,
            "backend": canonical,
            "channel": channel_key,
            "execution_backend": execution,
            "state": "unregistered",
            "automated": False,
            "route_executable": False,
            "operations": [],
            "missing_operations": list(required_operations),
            "message": "model route has no local execution adapter; use manual delivery or register a v2 wrapper",
        }
    operations = list(adapter.get("operations") or [])
    command_ready = _command_available(adapter.get("command") or [], which=which)
    required = set(required_operations)
    missing = sorted(required - set(operations))
    if not command_ready:
        state = "registered_missing_command"
    elif missing:
        state = "registered_incomplete"
    else:
        state = "automated_ready"
    automated = state == "automated_ready"
    return {
        "kind": "n2d_video_execution_status",
        "version": ADAPTER_VERSION,
        "backend": canonical,
        "channel": channel_key,
        "execution_backend": execution,
        "state": state,
        "automated": automated,
        "route_executable": automated,
        "adapter_id": adapter.get("adapter_id"),
        "implementation": adapter.get("implementation"),
        "command": list(adapter.get("command") or []),
        "operations": operations,
        "missing_operations": missing,
        "supports_cancel": "cancel" in operations,
        "supports_multishot": all(op in operations for op in ("multishot_submit", "multishot_query")),
        "supports_corrections": sorted(set(operations) & set(CORRECTION_OPERATIONS)),
        "capabilities": dict(adapter.get("capabilities") or {}),
        "message": (
            "local automation is ready" if automated
            else "adapter is registered but its command/required operations are not ready"
        ),
    }


def _json_sha(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_request(
    *,
    operation: str,
    root: str | Path,
    manifest: Mapping[str, Any],
    item: Mapping[str, Any],
    adapter: Mapping[str, Any],
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    root_path = Path(root).resolve()
    prompt_file = Path(str(item.get("prompt_file") or ""))
    try:
        prompt = prompt_file.read_text(encoding="utf-8").strip() if prompt_file.is_file() else str(item.get("prompt") or "")
    except OSError:
        prompt = str(item.get("prompt") or "")
    base = {
        "kind": REQUEST_KIND,
        "version": ADAPTER_VERSION,
        "operation": operation,
        "adapter_id": adapter.get("adapter_id"),
        "execution_backend": adapter.get("execution_backend"),
        "provider": adapter.get("provider"),
        "root": str(root_path),
        "episode": str(manifest.get("episode") or ""),
        "clip": str(item.get("clip") or item.get("group_id") or ""),
        "model": str(item.get("model_version") or manifest.get("model_version") or adapter.get("model") or ""),
        "channel": str(manifest.get("channel") or adapter.get("channel") or ""),
        "mode": str(item.get("mode_backend") or item.get("mode") or "image2video"),
        "duration_sec": item.get("submit_duration") or item.get("duration_sec"),
        "prompt": prompt,
        "negative_prompt": str(item.get("negative_prompt") or ""),
        "inputs": {
            "frames": [str(x) for x in (item.get("multiframe_images") or [])]
            or [str(x) for x in (item.get("image"), item.get("end_image")) if x],
            "references": list(item.get("reference_inputs") or []),
            "controls": list(item.get("control_inputs") or []),
            "audio": list(item.get("audio_inputs") or []),
            "source_video": str((item.get("repair_contract") or {}).get("source_video") or ""),
            "mask": str((item.get("repair_contract") or {}).get("mask") or ""),
        },
        "edit": {
            "operation": operation if operation in CORRECTION_OPERATIONS else "",
            "instruction": str((item.get("repair_contract") or {}).get("instruction") or ""),
            "start_sec": (item.get("repair_contract") or {}).get("start_sec"),
            "end_sec": (item.get("repair_contract") or {}).get("end_sec"),
            "preserve_regions": list((item.get("repair_contract") or {}).get("preserve_regions") or []),
            "source_sha256": str((item.get("repair_contract") or {}).get("source_sha256") or ""),
        },
        "output": {
            "directory": str((root_path / "出视频" / str(manifest.get("episode") or "") / "视频" / "_downloads").resolve()),
            "target": str(item.get("target") or ""),
        },
        "submit_id": str(item.get("submit_id") or ""),
        "trace": dict(item.get("trace") or manifest.get("trace") or {}),
    }
    if extra:
        base.update(dict(extra))
    stable = {k: v for k, v in base.items() if k not in {"idempotency_key", "request_sha256"}}
    base["idempotency_key"] = str(item.get("idempotency_key") or _json_sha(stable))
    base["request_sha256"] = _json_sha({k: v for k, v in base.items() if k != "request_sha256"})
    return base


def write_request(root: str | Path, episode: str, request: Mapping[str, Any]) -> Path:
    op = re.sub(r"[^a-z0-9_-]+", "_", str(request.get("operation") or "request").lower())
    unit = re.sub(r"[^A-Za-z0-9_-]+", "_", str(request.get("clip") or "unit"))
    digest = str(request.get("request_sha256") or _json_sha(request))[:12]
    path = Path(root) / "生产数据" / "video_execution_requests" / episode / f"{unit}_{op}_{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def wrapper_args(adapter: Mapping[str, Any], operation: str, request_path: str | Path) -> list[str]:
    if operation not in set(adapter.get("operations") or []):
        raise RuntimeError(f"adapter {adapter.get('adapter_id')} does not support operation={operation}")
    override = (adapter.get("operation_commands") or {}).get(operation)
    if override:
        tokens = _command_tokens(override)
        return [str(x).replace("{request}", str(request_path)) for x in tokens]
    command = _command_tokens(adapter.get("command"))
    if not command:
        raise RuntimeError(f"adapter {adapter.get('adapter_id')} has no command")
    return [*command, operation, "--request", str(request_path)]


def parse_result(stdout: str, stderr: str = "") -> Dict[str, Any]:
    try:
        data = json.loads(stdout or "{}")
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"raw_stdout": stdout or "", "raw_stderr": stderr or ""}


def result_value(payload: Mapping[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = payload
    for piece in str(path or "").split("."):
        if not piece:
            continue
        if not isinstance(cur, Mapping) or piece not in cur:
            return default
        cur = cur[piece]
    return cur


def normalize_result(adapter: Mapping[str, Any], payload: Mapping[str, Any]) -> Dict[str, Any]:
    contract = adapter.get("result_contract") if isinstance(adapter.get("result_contract"), Mapping) else {}
    return {
        "submit_id": result_value(payload, str(contract.get("submit_id") or "submit_id"), ""),
        "status": result_value(payload, str(contract.get("status") or "status"), ""),
        "output_path": result_value(payload, str(contract.get("output_path") or "output_path"), ""),
        "error": result_value(payload, str(contract.get("error") or "error"), ""),
        "raw": dict(payload),
    }


def classify_failure(returncode: int, payload: Mapping[str, Any], stderr: str = "") -> Dict[str, Any]:
    text = " ".join(str(x or "") for x in (stderr, payload.get("error"), payload.get("message"), payload.get("status"))).lower()
    if returncode == 0 and not any(x in text for x in ("fail", "error", "denied")):
        category = "none"
    elif any(x in text for x in ("429", "rate limit", "too many requests", "限流")):
        category = "rate_limited"
    elif any(x in text for x in ("401", "403", "unauthorized", "forbidden", "api key", "登录")):
        category = "auth"
    elif any(x in text for x in ("quota", "credit", "insufficient balance", "额度", "积分不足")):
        category = "quota"
    elif any(x in text for x in ("policy", "safety", "moderation", "违规", "审核拒绝")):
        category = "policy"
    elif any(x in text for x in ("invalid", "bad request", "unsupported", "参数")):
        category = "invalid_request"
    elif any(x in text for x in ("timeout", "timed out", "connection", "network", "dns")):
        category = "transient_network"
    elif any(x in text for x in ("500", "502", "503", "504", "server error")):
        category = "provider_5xx"
    else:
        category = "unknown_paid_state"
    return {
        "class": category,
        "retryable": category in {"rate_limited", "transient_network", "provider_5xx"},
        "paid_state_uncertain": category == "unknown_paid_state",
    }


__all__ = [
    "ADAPTER_KIND", "ADAPTER_VERSION", "REGISTRY_KIND", "REQUEST_KIND", "CORRECTION_OPERATIONS",
    "adapter_for", "build_request", "classify_failure", "execution_status",
    "load_registry", "normalize_adapter", "normalize_result", "registry_path",
    "wrapper_args", "write_request",
]
