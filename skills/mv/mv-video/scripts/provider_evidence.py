#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed validation for MV video provider submission evidence.

Evidence schema v2 deliberately removes caller-selected JSON pointers. API
responses are interpreted only by a built-in provider adapter; browser routes
use a named human observation over an immutable screenshot/PDF; and local
routes use one fixed, structured runner receipt. Registered media bytes are
hash-bound as the selected output.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from urllib.parse import urlparse


EVIDENCE_SCHEMA_VERSION = 2
RECEIPT_SCHEMA_VERSION = 2
LOCAL_RECEIPT_SCHEMA_VERSION = 1
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_KINDS = {
    "provider_api_response_json",
    "provider_ui_capture",
    "local_runner_receipt_json",
}
SUCCESS_STATUS = "succeeded"
SUCCESS_STATUS_VALUES = {"complete", "completed", "done", "success", "succeeded"}
BASE_EVIDENCE_FIELDS = {
    "schema_version", "kind", "execution_transport", "adapter_id",
    "route_sha256", "path", "sha256", "selected_asset", "verified_fields",
}
SELECTED_ASSET_FIELDS = {"sha256", "bound_by", "notes"}


# Code-owned interpretations of provider responses. A project capability
# adapter cannot add paths here: an unknown provider must use a manual route
# until a reviewed evidence adapter is shipped.
# Deliberately empty at this snapshot. Official Veo operations expose
# name/done/response but do not promise model + submit time in that response;
# official Runway task detail exposes id/createdAt/status/output but not model.
# Neither single-response format can meet the four-field contract without
# inventing metadata. Add an adapter only with a provider-owned capture format
# that exposes all required fields and has a fixed controls/refs mapping.
TRUSTED_API_ADAPTERS = {}


UI_PROVIDER_HOSTS = {
    "bytedance.dreamina": {"dreamina.capcut.com", "jimeng.jianying.com"},
    "bytedance.jimeng": {"jimeng.jianying.com"},
    "bytedance.doubao": {"www.doubao.com", "doubao.com"},
    "kuaishou.kling": {"klingai.com", "www.klingai.com"},
    "minimax.hailuo": {"hailuoai.video", "www.hailuoai.video"},
    "runway": {"app.runwayml.com"},
    "luma": {"lumalabs.ai", "dream-machine.lumalabs.ai"},
    "luma.dream_machine": {"lumalabs.ai", "dream-machine.lumalabs.ai"},
    "pika": {"pika.art", "www.pika.art"},
}


class _DuplicateJSONKey(ValueError):
    pass


def _strict_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateJSONKey(key)
        value[key] = item
    return value


def _reject_json_constant(_value):
    raise ValueError("provider_evidence_json_nonstandard_constant")


def _load_strict_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(
                handle, object_pairs_hook=_strict_object,
                parse_constant=_reject_json_constant,
            )
    except _DuplicateJSONKey as exc:
        raise ValueError("provider_evidence_json_duplicate_key") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("provider_evidence_json_invalid") from exc


def _stable_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reject_unknown_fields(value, allowed, code):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(code)


def route_requires_evidence(route):
    """Return True for every executable non-manual submission transport."""
    return str((route or {}).get("channel_kind") or "").strip() != "manual"


def _api_adapter_for_route(route, model, adapter_id=""):
    provider_id = str((route or {}).get("provider_id") or "").strip()
    requested = str(adapter_id or "").strip()
    candidates = [
        (name, adapter) for name, adapter in TRUSTED_API_ADAPTERS.items()
        if provider_id in adapter["provider_ids"] and model in adapter["models"]
    ]
    if requested:
        return next(((name, adapter) for name, adapter in candidates if name == requested), (None, None))
    return candidates[0] if len(candidates) == 1 else (None, None)


def evidence_template(route):
    kind = str((route or {}).get("channel_kind") or "").strip()
    model = str((route or {}).get("model") or "").strip()
    adapter_id = ""
    suggested = ""
    if kind == "api":
        suggested = "provider_api_response_json"
        adapter_id, _adapter = _api_adapter_for_route(route, model)
        adapter_id = adapter_id or ""
    elif kind == "web":
        suggested = "provider_ui_capture"
        adapter_id = "named_ui_observation.v1"
    elif kind == "local":
        suggested = "local_runner_receipt_json"
        adapter_id = "mv_video.local_runner_receipt.v1"
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "kind": suggested,
        "execution_transport": "" if kind == "api_or_web" else kind,
        "adapter_id": adapter_id,
        "route_sha256": str((route or {}).get("route_sha256") or ""),
        "path": "",
        "sha256": "",
        "selected_asset": {"sha256": "", "bound_by": "", "notes": ""},
    }


def _content_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_file(root, relative_path, allowed_extensions):
    raw = str(relative_path or "").strip()
    if not raw or os.path.isabs(raw):
        raise ValueError("provider_evidence_path_outside_project")
    project = os.path.realpath(root)
    target = os.path.realpath(os.path.join(project, raw))
    try:
        inside = os.path.commonpath((project, target)) == project
    except ValueError:
        inside = False
    if not inside or target == project:
        raise ValueError("provider_evidence_path_outside_project")
    normalized = os.path.relpath(target, project).replace(os.sep, "/")
    if not normalized.startswith("出视频/provider_evidence/"):
        raise ValueError("provider_evidence_path_not_in_evidence_tree")
    if normalized == "出视频/receipts" or normalized.startswith("出视频/receipts/"):
        raise ValueError("provider_evidence_receipt_self_reference")
    if not os.path.isfile(target):
        raise ValueError("provider_evidence_file_missing")
    if os.path.splitext(target)[1].lower() not in allowed_extensions:
        raise ValueError("provider_evidence_capture_type_invalid")
    return target, normalized


def _json_pointer(document, pointer):
    current = document
    for encoded in str(pointer).split("/")[1:]:
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
            index = int(token)
            if index >= len(current):
                raise ValueError("provider_evidence_adapter_field_missing")
            current = current[index]
        else:
            raise ValueError("provider_evidence_adapter_field_missing")
    return current


def _parse_instant(value, value_format="iso8601"):
    fmt = str(value_format or "iso8601")
    if fmt == "iso8601":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("submitted_at_not_timezone_aware_iso8601")
        raw = value.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError("submitted_at_not_timezone_aware_iso8601") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("submitted_at_not_timezone_aware_iso8601")
        return parsed.astimezone(timezone.utc)
    if fmt in {"unix_seconds", "unix_milliseconds"}:
        if isinstance(value, bool):
            raise ValueError("provider_evidence_submitted_at_invalid")
        try:
            stamp = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("provider_evidence_submitted_at_invalid") from exc
        if fmt == "unix_milliseconds":
            stamp /= 1000.0
        try:
            return datetime.fromtimestamp(stamp, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise ValueError("provider_evidence_submitted_at_invalid") from exc
    raise ValueError("provider_evidence_submitted_at_format_invalid")


def validate_submitted_at(value):
    return _parse_instant(value, "iso8601")


def _canonical_instant(value):
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _normalize_status(value, kind="string"):
    if kind == "done_boolean":
        if value is True:
            return SUCCESS_STATUS
        if value is False:
            return "running"
        raise ValueError("provider_evidence_status_invalid")
    raw = str(value or "").strip().lower()
    if not raw:
        raise ValueError("provider_evidence_status_invalid")
    return SUCCESS_STATUS if raw in SUCCESS_STATUS_VALUES else raw


def _contains_unbound_request_material(document):
    request_keys = {"input", "inputs", "parameters", "prompt", "request", "request_body"}
    stack = [document]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if any(str(key).strip().lower() in request_keys for key in value):
                return True
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    return False


def _validate_selected_asset(evidence, expected_output_sha256, *, human_required):
    selected = evidence.get("selected_asset")
    if not isinstance(selected, dict):
        raise ValueError("provider_evidence_selected_asset_missing")
    _reject_unknown_fields(
        selected, SELECTED_ASSET_FIELDS, "provider_evidence_selected_asset_unknown_field"
    )
    sha = str(selected.get("sha256") or "").strip()
    if not SHA256_RE.fullmatch(sha):
        raise ValueError("provider_evidence_selected_asset_sha256_invalid")
    if expected_output_sha256 and sha != expected_output_sha256:
        raise ValueError("provider_evidence_selected_asset_sha256_mismatch")
    if human_required:
        if not str(selected.get("bound_by") or "").strip():
            raise ValueError("provider_evidence_selected_asset_binder_missing")
        if not str(selected.get("notes") or "").strip():
            raise ValueError("provider_evidence_selected_asset_notes_missing")
    return sha


def _validate_api(route, receipt, evidence, document, expected_output_sha256):
    if "bindings" in evidence:
        raise ValueError("provider_evidence_freeform_bindings_forbidden")
    _reject_unknown_fields(evidence, BASE_EVIDENCE_FIELDS, "provider_evidence_unknown_field")
    model = str((receipt or {}).get("model") or "").strip()
    adapter_id, adapter = _api_adapter_for_route(route, model, evidence.get("adapter_id"))
    if not adapter:
        raise ValueError("provider_evidence_trusted_adapter_unavailable")
    if _contains_unbound_request_material(document):
        raise ValueError("provider_response_contains_unbound_request_material")
    job_id = str(_json_pointer(document, adapter["job_id_pointer"])).strip()
    if not job_id:
        raise ValueError("provider_evidence_job_id_empty")
    instant = _parse_instant(
        _json_pointer(document, adapter["submitted_at_pointer"]), adapter["submitted_at_format"]
    )
    raw_model = str(_json_pointer(document, adapter["model_pointer"])).strip()
    observed_model = adapter["model_values"].get(raw_model)
    if not observed_model:
        raise ValueError("provider_evidence_model_unrecognized")
    status = _normalize_status(
        _json_pointer(document, adapter["status_pointer"]), adapter["status_kind"]
    )
    selected_sha = _validate_selected_asset(evidence, expected_output_sha256, human_required=True)
    return adapter_id, job_id, instant, observed_model, status, selected_sha, "machine_response_plus_named_output_binding"


def _valid_capture_magic(path):
    with open(path, "rb") as handle:
        content = handle.read()
    head = content[:12]
    ext = os.path.splitext(path)[1].lower()
    return (
        (ext == ".png" and head.startswith(b"\x89PNG\r\n\x1a\n")
         and b"IHDR" in content[:64] and content.rstrip().endswith(b"IEND\xaeB`\x82"))
        or (ext in {".jpg", ".jpeg"} and head.startswith(b"\xff\xd8\xff")
            and content.rstrip().endswith(b"\xff\xd9"))
        or (ext == ".pdf" and head.startswith(b"%PDF-") and b"%%EOF" in content[-1024:])
    )


def _validate_ui(route, receipt, evidence, capture_path, expected_output_sha256):
    _reject_unknown_fields(
        evidence, BASE_EVIDENCE_FIELDS | {"ui_observation"},
        "provider_evidence_unknown_field",
    )
    if evidence.get("adapter_id") != "named_ui_observation.v1":
        raise ValueError("provider_evidence_trusted_adapter_unavailable")
    if not _valid_capture_magic(capture_path):
        raise ValueError("provider_evidence_ui_capture_magic_invalid")
    observation = evidence.get("ui_observation")
    if not isinstance(observation, dict):
        raise ValueError("provider_evidence_ui_observation_missing")
    _reject_unknown_fields(observation, {
        "reviewer", "notes", "observed_at", "submitted_at", "provider_id",
        "provider_job_id", "model", "status", "capture_method", "source_url",
    }, "provider_evidence_ui_observation_unknown_field")
    for field, code in (
        ("reviewer", "provider_evidence_ui_reviewer_missing"),
        ("notes", "provider_evidence_ui_notes_missing"),
        ("provider_job_id", "provider_evidence_job_id_empty"),
        ("model", "provider_evidence_model_missing"),
        ("status", "provider_evidence_status_invalid"),
        ("submitted_at", "submitted_at_not_timezone_aware_iso8601"),
    ):
        if not str(observation.get(field) or "").strip():
            raise ValueError(code)
    observed_at = _parse_instant(observation.get("observed_at"), "iso8601")
    instant = _parse_instant(observation.get("submitted_at"), "iso8601")
    if observed_at < instant:
        raise ValueError("provider_evidence_ui_observed_before_submission")
    provider_id = str((route or {}).get("provider_id") or "").strip()
    if str(observation.get("provider_id") or "").strip() != provider_id:
        raise ValueError("provider_evidence_provider_id_mismatch")
    source_url = str(observation.get("source_url") or "").strip()
    if source_url:
        parsed = urlparse(source_url)
        hosts = UI_PROVIDER_HOSTS.get(provider_id)
        if parsed.scheme != "https" or not hosts or parsed.hostname not in hosts:
            raise ValueError("provider_evidence_ui_origin_untrusted")
    if str(observation.get("capture_method") or "").strip() not in {
        "browser_screenshot", "provider_pdf_export",
    }:
        raise ValueError("provider_evidence_ui_capture_method_invalid")
    selected_sha = _validate_selected_asset(evidence, expected_output_sha256, human_required=True)
    return (
        "named_ui_observation.v1",
        str(observation["provider_job_id"]).strip(),
        instant,
        str(observation["model"]).strip(),
        _normalize_status(observation["status"]),
        selected_sha,
        "named_human_observation",
    )


def _validate_local(route, receipt, evidence, document, expected_output_sha256):
    _reject_unknown_fields(evidence, BASE_EVIDENCE_FIELDS, "provider_evidence_unknown_field")
    if evidence.get("adapter_id") != "mv_video.local_runner_receipt.v1":
        raise ValueError("provider_evidence_trusted_adapter_unavailable")
    if not isinstance(document, dict):
        raise ValueError("provider_evidence_local_receipt_invalid")
    if (
        document.get("kind") != "mv_video_local_runner_receipt"
        or int(document.get("schema_version") or 0) != LOCAL_RECEIPT_SCHEMA_VERSION
    ):
        raise ValueError("provider_evidence_local_receipt_invalid")
    _reject_unknown_fields(
        document, {"kind", "schema_version", "provider_id", "runner", "execution"},
        "provider_evidence_local_receipt_unknown_field",
    )
    if str(document.get("provider_id") or "").strip() != str((route or {}).get("provider_id") or "").strip():
        raise ValueError("provider_evidence_provider_id_mismatch")
    runner = document.get("runner")
    execution = document.get("execution")
    if not isinstance(runner, dict) or not isinstance(execution, dict):
        raise ValueError("provider_evidence_local_receipt_invalid")
    _reject_unknown_fields(
        runner, {"name", "version", "operator", "command_sha256"},
        "provider_evidence_local_runner_unknown_field",
    )
    _reject_unknown_fields(execution, {
        "job_id", "submitted_at", "model", "status", "exit_code",
        "request_controls_sha256", "submitted_refs_sha256", "output_asset_sha256",
    }, "provider_evidence_local_execution_unknown_field")
    for field in ("name", "version", "operator"):
        if not str(runner.get(field) or "").strip():
            raise ValueError(f"provider_evidence_local_runner_{field}_missing")
    if not SHA256_RE.fullmatch(str(runner.get("command_sha256") or "")):
        raise ValueError("provider_evidence_local_runner_command_sha256_invalid")
    if execution.get("exit_code") != 0:
        raise ValueError("provider_evidence_local_runner_failed")
    if execution.get("request_controls_sha256") != str((receipt or {}).get("compiled_request_controls_sha256") or ""):
        raise ValueError("provider_evidence_request_controls_mismatch")
    if execution.get("submitted_refs_sha256") != _stable_hash((receipt or {}).get("submitted_refs") or []):
        raise ValueError("provider_evidence_submitted_refs_mismatch")
    selected_sha = str(execution.get("output_asset_sha256") or "").strip()
    if not SHA256_RE.fullmatch(selected_sha):
        raise ValueError("provider_evidence_selected_asset_sha256_invalid")
    if expected_output_sha256 and selected_sha != expected_output_sha256:
        raise ValueError("provider_evidence_selected_asset_sha256_mismatch")
    selected_evidence_sha = _validate_selected_asset(
        evidence, expected_output_sha256, human_required=False
    )
    if selected_evidence_sha != selected_sha:
        raise ValueError("provider_evidence_selected_asset_sha256_mismatch")
    return (
        "mv_video.local_runner_receipt.v1",
        str(execution.get("job_id") or "").strip(),
        _parse_instant(execution.get("submitted_at"), "iso8601"),
        str(execution.get("model") or "").strip(),
        _normalize_status(execution.get("status")),
        selected_sha,
        "structured_local_runner_receipt",
    )


def _allowed_kind(route, evidence):
    channel_kind = str((route or {}).get("channel_kind") or "").strip()
    evidence_kind = str((evidence or {}).get("kind") or "").strip()
    transport = str((evidence or {}).get("execution_transport") or "").strip()
    if channel_kind == "api_or_web":
        if transport not in {"api", "web"}:
            return False, "provider_evidence_execution_transport_missing"
        expected = "provider_api_response_json" if transport == "api" else "provider_ui_capture"
        return evidence_kind == expected, "provider_evidence_kind_route_mismatch"
    expected = {
        "api": "provider_api_response_json",
        "web": "provider_ui_capture",
        "local": "local_runner_receipt_json",
    }.get(channel_kind)
    if not expected:
        return False, "provider_evidence_channel_kind_unsupported"
    if evidence_kind != expected:
        return False, "provider_evidence_kind_route_mismatch"
    if transport != channel_kind:
        return False, "provider_evidence_execution_transport_mismatch"
    return True, ""


def validate_provider_evidence(root, route, receipt, expected_output_sha256=""):
    """Return ``(normalized_evidence, errors)`` for one formal receipt."""
    evidence = (receipt or {}).get("provider_evidence")
    if not isinstance(evidence, dict):
        return None, ["provider_evidence_missing"]
    errors = []
    try:
        schema = int(evidence.get("schema_version") or 0)
    except (TypeError, ValueError):
        schema = 0
    if schema != EVIDENCE_SCHEMA_VERSION:
        errors.append("provider_evidence_schema_mismatch")
    evidence_kind = str(evidence.get("kind") or "").strip()
    if evidence_kind not in EVIDENCE_KINDS:
        errors.append("provider_evidence_kind_invalid")
    allowed, route_error = _allowed_kind(route, evidence)
    if not allowed:
        errors.append(route_error)
    route_sha = str((route or {}).get("route_sha256") or "").strip()
    if route_sha and str(evidence.get("route_sha256") or "").strip() != route_sha:
        errors.append("provider_evidence_route_sha256_mismatch")

    expected_sha = str(evidence.get("sha256") or "").strip()
    if not SHA256_RE.fullmatch(expected_sha):
        errors.append("provider_evidence_sha256_invalid")
    allowed_extensions = ({".png", ".jpg", ".jpeg", ".pdf"}
                          if evidence_kind == "provider_ui_capture" else {".json"})
    try:
        absolute, normalized_path = _project_file(root, evidence.get("path"), allowed_extensions)
    except ValueError as exc:
        errors.append(str(exc))
        return None, list(dict.fromkeys(errors))
    if _content_hash(absolute) != expected_sha:
        errors.append("provider_evidence_sha256_mismatch")

    document = None
    if evidence_kind != "provider_ui_capture":
        try:
            document = _load_strict_json(absolute)
        except ValueError as exc:
            errors.append(str(exc))
            return None, list(dict.fromkeys(errors))
        if isinstance(document, dict) and (
            str(document.get("kind") or "").startswith("mv_video_submit")
            or "template_only" in document
        ):
            errors.append("provider_evidence_receipt_self_reference")

    extracted = None
    if not errors:
        try:
            if evidence_kind == "provider_api_response_json":
                extracted = _validate_api(route, receipt, evidence, document, expected_output_sha256)
            elif evidence_kind == "provider_ui_capture":
                extracted = _validate_ui(route, receipt, evidence, absolute, expected_output_sha256)
            elif evidence_kind == "local_runner_receipt_json":
                extracted = _validate_local(route, receipt, evidence, document, expected_output_sha256)
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))
    if extracted:
        adapter_id, job_id, instant, model, status, selected_sha, evidence_class = extracted
        receipt_job_id = str((receipt or {}).get("provider_job_id") or "").strip()
        receipt_model = str((receipt or {}).get("model") or "").strip()
        try:
            receipt_status = _normalize_status((receipt or {}).get("provider_status"))
        except ValueError as exc:
            errors.append(str(exc))
            receipt_status = ""
        try:
            receipt_instant = validate_submitted_at((receipt or {}).get("submitted_at"))
        except ValueError as exc:
            errors.append(str(exc))
            receipt_instant = None
        if job_id != receipt_job_id:
            errors.append("provider_evidence_job_id_mismatch")
        if model != receipt_model:
            errors.append("provider_evidence_model_mismatch")
        route_model = str((route or {}).get("model") or "").strip()
        if route_model and model != route_model:
            errors.append("provider_evidence_route_model_mismatch")
        if status != receipt_status:
            errors.append("provider_evidence_status_mismatch")
        if status != SUCCESS_STATUS:
            errors.append("provider_evidence_status_not_successful")
        if receipt_instant is not None and abs((instant - receipt_instant).total_seconds()) > 0.001:
            errors.append("provider_evidence_submitted_at_mismatch")
        verified_fields = {
            "adapter_id": adapter_id,
            "evidence_class": evidence_class,
            "provider_id": str((route or {}).get("provider_id") or "").strip(),
            "provider_job_id": job_id,
            "submitted_at_utc": _canonical_instant(instant),
            "model": model,
            "status": status,
            "selected_asset_sha256": selected_sha,
        }
        claimed = evidence.get("verified_fields")
        if claimed is not None and claimed != verified_fields:
            errors.append("provider_evidence_verified_fields_mismatch")
    else:
        verified_fields = None
    if errors:
        return None, list(dict.fromkeys(errors))
    normalized = copy.deepcopy(evidence)
    normalized["path"] = normalized_path
    normalized["verified_fields"] = verified_fields
    return normalized, []
