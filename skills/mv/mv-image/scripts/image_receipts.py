#!/usr/bin/env python3
"""MV image B14 per-asset preflight/submission/postflight receipts.

This module is deliberately self-contained inside the MV line.  It does not call
an image provider.  Instead it makes the expensive provider call auditable:

* ``preflight`` freezes the target, prompt, model/channel and exact image
  references before spending.  Every reference is project-local, decodable and
  bound by SHA-256 plus owner/use metadata.  A new target cannot start until its
  predecessor has a current accepted receipt.
* ``record_generation.py`` calls :func:`record_submission` after the provider
  returns, proving that the references actually submitted equal the frozen plan.
  Provider-backed routes must also bind a project-local schema-v2 manifest to an
  independent raw API JSON or trusted-origin HAR capture whose selected output
  bytes equal the asset; a bare, self-declared provider job ID is not a receipt.
* ``postflight`` binds the current pixels to a full, current ``image_qc`` report
  and a named side-by-side visual review.  Anything other than machine ``ok`` +
  visual ``pass`` is recorded as rejected, never accepted.

Ledger: ``生产数据/image_acceptance/image_acceptance.json``.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse


LEDGER_KIND = "mv_image_acceptance_ledger"
LEDGER_SCHEMA_VERSION = 1
LEDGER_REL = Path("生产数据") / "image_acceptance" / "image_acceptance.json"
QC_REL = Path("生产数据") / "image_qc" / "image_qc.json"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
EXCLUDED_PARTS = {"废料", "rejected", "rejects", "trash", "tmp", "temp", "prompt"}
IDENTITY_SCOPES = {"contains_identity", "no_identity"}
ASSET_KINDS = {"auto", "clip_start", "clip_end", "shared_costume", "shared_location",
               "shared_asset", "candidate", "cover", "other_image"}
PROVIDER_EVIDENCE_KIND = "mv_image_provider_evidence"
PROVIDER_EVIDENCE_SCHEMA_VERSION = 2
PROVIDER_EVIDENCE_SOURCES = {"api_response_json", "ui_export"}
LOCAL_CHANNELS = {
    "local", "offline", "local/offline", "local_cli", "local cli",
    "本地", "离线", "本地离线",
}
LOCAL_MODEL_RE = re.compile(r"^(?:local|offline|本地|离线)(?::|/).+", re.I)
PROVIDER_CLOCK_SKEW = timedelta(minutes=2)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROVIDER_JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{5,255}$")
PROVIDER_PLACEHOLDER_RE = re.compile(
    r"(?:^|[._:/-])(?:test|fake|dummy|sample|example|placeholder|unknown|pending|todo|tbd|none|null)"
    r"(?:$|[._:/-])",
    re.I,
)
PROVIDER_ADAPTERS: Dict[str, Dict[str, Any]] = {
    "openai_responses_image_v1": {
        "provider": "openai",
        "source": "api_response_json",
        "channels": {"codex", "openai api"},
        "capture_suffixes": {".json"},
    },
    "openai_responses_image_har_v1": {
        "provider": "openai",
        "source": "ui_export",
        "channels": {"codex", "openai api"},
        "capture_suffixes": {".har"},
    },
}
EVIDENCE_COMMON_KEYS = {
    "kind", "schema_version", "source", "adapter_id", "attempt_id",
    "preflight_sha256", "raw_capture", "output_selector",
}


class ReceiptError(ValueError):
    """A deterministic B14 precondition failed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_path(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def provider_evidence_required(channel: str, model: str = "") -> bool:
    """Only an explicitly local route *and* local-qualified model is exempt.

    ``channel=local`` is user-controlled metadata, so it cannot turn a known
    cloud model into an evidence-free route.  Unknown/custom routes therefore
    fail closed.
    """
    local_channel = str(channel or "").strip().casefold() in LOCAL_CHANNELS
    local_model = bool(LOCAL_MODEL_RE.fullmatch(str(model or "").strip()))
    return not (local_channel and local_model)


def _strict_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ReceiptError(f"JSON 含重复键：{key}")
        out[key] = value
    return out


def _loads_json_strict(raw: bytes | str, label: str) -> Any:
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return json.loads(text, object_pairs_hook=_strict_object)
    except ReceiptError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{label} 不是严格 UTF-8 JSON：{exc}") from exc


def _parse_iso_time(value: Any, label: str) -> datetime:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise ReceiptError(f"{label} 必须是带时区的 ISO-8601 时间") from exc
    return parsed.astimezone(timezone.utc)


def _timestamp_value(value: Any) -> Optional[datetime]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        seconds = float(value)
        if abs(seconds) >= 1_000_000_000_000:
            seconds /= 1000.0
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    raw = str(value or "").strip()
    if not raw:
        return None
    if re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
        try:
            return _timestamp_value(float(raw))
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _valid_provider_job_id(value: str) -> bool:
    raw = str(value or "").strip()
    return bool(PROVIDER_JOB_ID_RE.fullmatch(raw) and not PROVIDER_PLACEHOLDER_RE.search(raw))


def _capture_ref(root: Path, evidence_path: Path, row: Any,
                 suffixes: set[str]) -> Tuple[Dict[str, str], Path]:
    if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
        raise ReceiptError("raw_capture 必须严格为 {path,sha256}")
    raw_rel, raw_path = _relative(root, str(row.get("path") or ""), must_exist=True)
    if raw_path.resolve() == evidence_path.resolve():
        raise ReceiptError("evidence manifest 不能同时充当原始 provider capture")
    if not raw_rel.startswith("\u751f\u4ea7\u6570\u636e/provider_evidence/raw/"):
        raise ReceiptError("raw_capture 必须落在 生产数据/provider_evidence/raw/")
    if raw_path.suffix.casefold() not in suffixes:
        raise ReceiptError(f"raw_capture 后缀必须是 {sorted(suffixes)}")
    current_sha = sha256_path(raw_path)
    recorded_sha = str(row.get("sha256") or "")
    if not SHA256_RE.fullmatch(recorded_sha) or recorded_sha != current_sha:
        raise ReceiptError("raw_capture.sha256 未绑定当前原始捕获文件")
    return {"path": raw_rel, "sha256": current_sha}, raw_path


def _openai_response_values(payload: Any, *, selector: int, expected_job_id: str,
                            model: str, asset_sha256: str, not_before: str) -> Dict[str, Any]:
    """Extract one exact OpenAI Responses image output; never recursive-search."""
    if not isinstance(payload, Mapping) or not payload:
        raise ReceiptError("OpenAI Responses capture 必须是非空 JSON object")
    response_id = str(payload.get("id") or "").strip()
    if not _valid_provider_job_id(response_id):
        raise ReceiptError("OpenAI Responses capture 缺非占位 response id")
    if str(payload.get("model") or "").strip() != str(model or "").strip():
        raise ReceiptError("OpenAI Responses /model 与实际 --model 不一致")
    if str(payload.get("status") or "").strip().casefold() != "completed":
        raise ReceiptError("OpenAI Responses /status 不是 completed")
    created_at = _timestamp_value(payload.get("created_at"))
    if created_at is None:
        raise ReceiptError("OpenAI Responses /created_at 必须是可解析 provider time")
    now = datetime.now(timezone.utc)
    if created_at > now + PROVIDER_CLOCK_SKEW:
        raise ReceiptError("provider time 晚于当前时间（超出 2 分钟时钟偏差）")
    if not_before:
        preflight_time = _parse_iso_time(not_before, "preflight.created_at")
        if created_at < preflight_time - PROVIDER_CLOCK_SKEW:
            raise ReceiptError("provider time 早于本次 preflight，不能复用旧结果")
    outputs = payload.get("output")
    if not isinstance(outputs, list) or selector < 0 or selector >= len(outputs):
        raise ReceiptError("output_selector 超出 OpenAI Responses /output 范围")
    selected = outputs[selector]
    if not isinstance(selected, Mapping):
        raise ReceiptError("被选 OpenAI /output 不是 object")
    if str(selected.get("type") or "") != "image_generation_call":
        raise ReceiptError("被选 OpenAI /output/type 不是 image_generation_call")
    job_id = str(selected.get("id") or "").strip()
    if job_id != expected_job_id or not _valid_provider_job_id(job_id):
        raise ReceiptError("OpenAI /output/{selector}/id 与 --provider-job-id 不一致或为占位")
    if str(selected.get("status") or "").strip().casefold() != "completed":
        raise ReceiptError("OpenAI /output/{selector}/status 不是 completed")
    encoded = selected.get("result")
    if not isinstance(encoded, str) or not encoded.strip():
        raise ReceiptError("OpenAI /output/{selector}/result 缺 base64 图片字节")
    try:
        output_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ReceiptError("OpenAI /output/{selector}/result 不是严格 base64") from exc
    output_sha = hashlib.sha256(output_bytes).hexdigest()
    if not output_bytes or output_sha != asset_sha256:
        raise ReceiptError("provider output 字节 SHA-256 与当前资产不一致")
    return {
        "provider": "openai",
        "provider_response_id": response_id,
        "provider_job_id": job_id,
        "submitted_at": created_at.replace(microsecond=0).isoformat(),
        "model": str(model).strip(),
        "result_status": "completed",
        "provider_output_sha256": output_sha,
    }


def _openai_response_from_har(raw_path: Path, entry_selector: int) -> Any:
    har = _loads_json_strict(raw_path.read_bytes(), "UI HAR export")
    entries = ((har.get("log") or {}).get("entries")
               if isinstance(har, Mapping) and isinstance(har.get("log"), Mapping) else None)
    if not isinstance(entries, list) or entry_selector < 0 or entry_selector >= len(entries):
        raise ReceiptError("entry_selector 超出 HAR log.entries 范围")
    entry = entries[entry_selector]
    request = entry.get("request") if isinstance(entry, Mapping) else None
    response = entry.get("response") if isinstance(entry, Mapping) else None
    if not isinstance(request, Mapping) or not isinstance(response, Mapping):
        raise ReceiptError("被选 HAR entry 缺 request/response object")
    parsed_url = urlparse(str(request.get("url") or ""))
    trusted_path = (parsed_url.path == "/v1/responses"
                    or parsed_url.path.startswith("/v1/responses/"))
    if (parsed_url.scheme.casefold() != "https" or parsed_url.hostname != "api.openai.com"
            or not trusted_path):
        raise ReceiptError("HAR request 不是受信 api.openai.com/v1/responses origin")
    if str(request.get("method") or "").upper() not in {"GET", "POST"}:
        raise ReceiptError("HAR request method 必须是 GET/POST")
    if response.get("status") != 200:
        raise ReceiptError("HAR provider response HTTP status 不是 200")
    content = response.get("content")
    if not isinstance(content, Mapping):
        raise ReceiptError("HAR response 缺 content")
    mime = str(content.get("mimeType") or "").split(";", 1)[0].strip().casefold()
    if mime not in {"application/json", "text/json"}:
        raise ReceiptError("HAR response content 不是 JSON")
    text = content.get("text")
    if not isinstance(text, str) or not text:
        raise ReceiptError("HAR response content.text 为空")
    if str(content.get("encoding") or "").casefold() == "base64":
        try:
            body = base64.b64decode(text, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ReceiptError("HAR response content.text base64 不可解码") from exc
    elif content.get("encoding") in {None, ""}:
        body = text.encode("utf-8")
    else:
        raise ReceiptError("HAR response content.encoding 只支持空或 base64")
    return _loads_json_strict(body, "HAR provider response body")


def validate_provider_evidence(root: Path, evidence: str | Path, *, expected_job_id: str,
                               model: str, channel: str, asset_sha256: str,
                               expected_attempt_id: str, expected_preflight_sha256: str,
                               not_before: str = "") -> Dict[str, Any]:
    """Validate and normalize one project-local provider evidence record.

    This proves local integrity and field consistency, not provider identity.  A
    cryptographic provider signature/API verification would be needed for that
    stronger claim.
    """
    evidence_value = str(evidence or "").strip()
    if not evidence_value:
        raise ReceiptError("正式 provider 结果必须提供 --provider-evidence")
    evidence_rel, evidence_path = _relative(root, evidence_value, must_exist=True)
    if evidence_path.suffix.lower() != ".json":
        raise ReceiptError("--provider-evidence 必须是作品根内 JSON 文件")
    if not evidence_rel.startswith("生产数据/provider_evidence/"):
        raise ReceiptError("provider evidence manifest 必须落在 生产数据/provider_evidence/")
    try:
        payload = _loads_json_strict(evidence_path.read_bytes(), "provider evidence manifest")
    except OSError as exc:
        raise ReceiptError(f"provider evidence JSON 不可读：{evidence_rel}") from exc
    if not isinstance(payload, dict) or not payload:
        raise ReceiptError("provider evidence 必须是非空 JSON object，不能是任意占位")
    schema_version = payload.get("schema_version")
    if (payload.get("kind") != PROVIDER_EVIDENCE_KIND
            or isinstance(schema_version, bool)
            or schema_version != PROVIDER_EVIDENCE_SCHEMA_VERSION):
        raise ReceiptError(
            f"provider evidence 必须是 schema v{PROVIDER_EVIDENCE_SCHEMA_VERSION} "
            f"{PROVIDER_EVIDENCE_KIND}")
    source = str(payload.get("source") or "").strip()
    if source not in PROVIDER_EVIDENCE_SOURCES:
        raise ReceiptError(f"provider evidence source 必须是 {sorted(PROVIDER_EVIDENCE_SOURCES)}")
    allowed_manifest_keys = set(EVIDENCE_COMMON_KEYS)
    if source == "ui_export":
        allowed_manifest_keys.add("entry_selector")
    if set(payload) != allowed_manifest_keys:
        unknown = sorted(set(payload) - allowed_manifest_keys)
        missing = sorted(allowed_manifest_keys - set(payload))
        raise ReceiptError(
            f"provider evidence manifest 字段必须严格匹配 schema；unknown={unknown}, missing={missing}")
    adapter_id = str(payload.get("adapter_id") or "").strip()
    adapter = PROVIDER_ADAPTERS.get(adapter_id)
    if not adapter or adapter.get("source") != source:
        raise ReceiptError("adapter_id 未受信或与 evidence source 不匹配")
    if str(channel or "").strip().casefold() not in adapter["channels"]:
        raise ReceiptError("model/channel 路由不在该受信 provider adapter 允许范围")
    expected_job_id = str(expected_job_id or "").strip()
    if not _valid_provider_job_id(expected_job_id):
        raise ReceiptError("--provider-job-id 必须是非占位 provider job/request/task id（至少 6 字符）")
    attempt_id = str(payload.get("attempt_id") or "").strip()
    if not expected_attempt_id or attempt_id != expected_attempt_id:
        raise ReceiptError("provider evidence.attempt_id 未绑定当前 B14 attempt")
    preflight_sha = str(payload.get("preflight_sha256") or "").strip()
    if (not SHA256_RE.fullmatch(preflight_sha)
            or preflight_sha != str(expected_preflight_sha256 or "")):
        raise ReceiptError("provider evidence.preflight_sha256 未绑定当前 preflight")
    selector = payload.get("output_selector")
    if isinstance(selector, bool) or not isinstance(selector, int) or selector < 0:
        raise ReceiptError("output_selector 必须是非负整数")
    capture, raw_path = _capture_ref(
        root, evidence_path, payload.get("raw_capture"), set(adapter["capture_suffixes"]))
    if source == "api_response_json":
        response_payload = _loads_json_strict(raw_path.read_bytes(), "raw provider API capture")
        entry_selector: Optional[int] = None
    else:
        entry_selector_raw = payload.get("entry_selector")
        if (isinstance(entry_selector_raw, bool) or not isinstance(entry_selector_raw, int)
                or entry_selector_raw < 0):
            raise ReceiptError("entry_selector 必须是非负整数")
        entry_selector = entry_selector_raw
        response_payload = _openai_response_from_har(raw_path, entry_selector)
    extracted = _openai_response_values(
        response_payload, selector=selector, expected_job_id=expected_job_id,
        model=model, asset_sha256=asset_sha256, not_before=not_before)

    normalized: Dict[str, Any] = {
        "path": evidence_rel,
        "sha256": sha256_path(evidence_path),
        "kind": PROVIDER_EVIDENCE_KIND,
        "schema_version": PROVIDER_EVIDENCE_SCHEMA_VERSION,
        "source": source,
        "adapter_id": adapter_id,
        "attempt_id": attempt_id,
        "preflight_sha256": preflight_sha,
        "raw_capture": capture,
        "output_selector": selector,
        "provider": str(adapter["provider"]),
        "provider_job_id": extracted["provider_job_id"],
        "provider_response_id": extracted["provider_response_id"],
        "submitted_at": extracted["submitted_at"],
        "model": str(model).strip(),
        "channel": str(channel).strip(),
        "asset_sha256": asset_sha256,
        "result_status": extracted["result_status"],
        "provider_output_sha256": extracted["provider_output_sha256"],
        "acceptance_eligible": True,
        "verification_scope": "locally_verified_provider_capture",
        "provider_authenticity": "not_proven_offline",
    }
    if entry_selector is not None:
        normalized["entry_selector"] = entry_selector
    return normalized


def provider_evidence_findings(root: Path, submission: Mapping[str, Any], *,
                               not_before: str = "") -> List[str]:
    """Recompute provider evidence from disk for status/postflight/QC audits."""
    findings: List[str] = []
    channel = str(submission.get("channel") or "").strip()
    model = str(submission.get("model") or "").strip()
    required = provider_evidence_required(channel, model)
    job_id = str(submission.get("provider_job_id") or "").strip()
    recorded = submission.get("provider_evidence")
    if submission.get("provider_evidence_required") not in {None, required}:
        findings.append("provider_evidence_requirement_mismatch")
    if required and not job_id:
        findings.append("provider_job_id_missing")
    if required and not isinstance(recorded, Mapping):
        findings.append("provider_evidence_missing")
        return findings
    if not required and not job_id and not recorded:
        return findings
    if not job_id or not isinstance(recorded, Mapping):
        findings.append("provider_job_and_evidence_must_be_paired")
        return findings
    try:
        normalized = validate_provider_evidence(
            root, str(recorded.get("path") or ""), expected_job_id=job_id,
            model=model, channel=channel,
            asset_sha256=str(submission.get("asset_sha256") or ""),
            expected_attempt_id=str(submission.get("attempt_id") or ""),
            expected_preflight_sha256=str(submission.get("bound_preflight_sha256") or ""),
            not_before=not_before)
    except ReceiptError as exc:
        findings.append(f"provider_evidence_invalid:{exc}")
        return findings
    if dict(recorded) != normalized:
        findings.append("provider_evidence_receipt_mismatch")
    return findings


def _relative(root: Path, value: str | Path, *, must_exist: bool = False) -> Tuple[str, Path]:
    raw = Path(value).expanduser()
    absolute = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        rel = absolute.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ReceiptError(f"路径必须在作品根内：{absolute}") from exc
    if not rel or rel == ".":
        raise ReceiptError("路径不能是作品根本身")
    if must_exist and not absolute.is_file():
        raise ReceiptError(f"文件不存在：{rel}")
    return rel, absolute


def probe_decodable(path: Path) -> Tuple[bool, Dict[str, Any]]:
    """Decode all pixels with Pillow; header-only/placeholder files do not pass."""
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return False, {"error": "missing_pillow", "install": "python -m pip install pillow"}
    try:
        with Image.open(path) as image:
            width, height = image.size
            image.load()
            fmt = str(image.format or "").upper()
        if width <= 0 or height <= 0:
            raise ValueError("zero-sized image")
        return True, {"width": width, "height": height, "format": fmt}
    except Exception as exc:
        return False, {"error": f"decode_failed:{exc}"}


def ledger_path(root: Path) -> Path:
    return root / LEDGER_REL


def empty_ledger() -> Dict[str, Any]:
    return {
        "kind": LEDGER_KIND,
        "schema_version": LEDGER_SCHEMA_VERSION,
        "updated_at": utc_now(),
        "sequence": [],
        "assets": {},
        "summary": {},
    }


def load_ledger(root: Path) -> Dict[str, Any]:
    path = ledger_path(root)
    if not path.is_file():
        return empty_ledger()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReceiptError(f"B14 ledger 不可读：{path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("kind") != LEDGER_KIND:
        raise ReceiptError(f"B14 ledger kind 错误：{path}")
    if data.get("schema_version") != LEDGER_SCHEMA_VERSION:
        raise ReceiptError(
            f"B14 ledger schema 不支持：{data.get('schema_version')}（当前 {LEDGER_SCHEMA_VERSION}）")
    data.setdefault("sequence", [])
    data.setdefault("assets", {})
    data.setdefault("summary", {})
    return data


def write_ledger(root: Path, ledger: Dict[str, Any]) -> Path:
    path = ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = utc_now()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    os.replace(tmp, path)
    return path


def classify_asset(rel: str) -> str:
    lower = rel.lower()
    name = Path(rel).stem.lower()
    parts = set(Path(rel).parts)
    if "封面" in parts or name in {"cover", "封面"}:
        return "cover"
    if any(part in {"候选", "candidates", "candidate"} for part in parts):
        return "candidate"
    if re.search(r"clip[_-]?\d+.*(?:_end|尾帧)$", name, re.I):
        return "clip_end"
    if re.search(r"clip[_-]?\d+", name, re.I):
        return "clip_start"
    if "共享" in parts or "common" in parts:
        if any(token in lower for token in ("服装", "定妆", "character", "costume", "主角", "主唱")):
            return "shared_costume"
        if any(token in lower for token in ("场景", "location", "scene", "背景")):
            return "shared_location"
        return "shared_asset"
    return "other_image"


def _clip_plan_paths(root: Path) -> Dict[str, str]:
    path = root / "分镜" / "clip_plan.json"
    if not path.is_file():
        return {}
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, str] = {}
    for clip in plan.get("clips", []) if isinstance(plan, dict) else []:
        if not isinstance(clip, dict):
            continue
        first = str(clip.get("image_path") or "").strip()
        if first:
            try:
                rel, _ = _relative(root, first)
                out[rel] = "clip_start"
            except ReceiptError:
                pass
        if clip.get("need_end_frame"):
            end = str(clip.get("end_frame_path") or "").strip()
            if end:
                try:
                    rel, _ = _relative(root, end)
                    out[rel] = "clip_end"
                except ReceiptError:
                    pass
    return out


def upstream_contract_for_asset(root: Path, rel: str) -> Dict[str, Any]:
    """Resolve the current clip/reference-plan contract for one image path."""
    plan_path = root / "分镜" / "clip_plan.json"
    if not plan_path.is_file():
        return {}
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReceiptError(f"clip_plan.json 不可读：{exc}") from exc
    matched: Dict[str, Any] = {}
    for clip in plan.get("clips", []) if isinstance(plan, dict) else []:
        if not isinstance(clip, dict):
            continue
        paths = [str(clip.get("image_path") or "").strip()]
        if clip.get("need_end_frame"):
            paths.append(str(clip.get("end_frame_path") or "").strip())
        normalized = set()
        for raw in paths:
            if not raw:
                continue
            try:
                normalized.add(_relative(root, raw)[0])
            except ReceiptError:
                continue
        if rel in normalized:
            matched = clip
            break
    if not matched:
        return {}
    clip_id = str(matched.get("clip_id") or matched.get("id") or "")
    reference_row: Dict[str, Any] = {}
    reference_plan_path = root / "分镜" / "reference_plan.json"
    if reference_plan_path.is_file():
        try:
            reference_plan = json.loads(reference_plan_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ReceiptError(f"reference_plan.json 不可读：{exc}") from exc
        reference_row = next((
            row for row in (reference_plan.get("clips", []) if isinstance(reference_plan, dict) else [])
            if isinstance(row, dict) and str(row.get("clip_id") or "") == clip_id
        ), {})
    refs: List[Any] = []
    refs.extend(matched.get("reference_inputs") or [])
    refs.extend(reference_row.get("reference_inputs") or [])
    required_paths: set[str] = set()
    required_subjects: set[str] = set()
    for reference in refs:
        if isinstance(reference, str) and reference.strip():
            required_paths.add(_relative(root, reference.strip())[0])
        elif isinstance(reference, Mapping):
            raw_path = str(reference.get("path") or "").strip()
            if raw_path:
                required_paths.add(_relative(root, raw_path)[0])
            subject = str(reference.get("subject_id") or reference.get("character_id") or "").strip()
            if subject:
                required_subjects.add(subject)
    expected_prompt = str(matched.get("image_prompt_path") or "").strip()
    if expected_prompt:
        expected_prompt = _relative(root, expected_prompt)[0]
    identity_contract = matched.get("identity_contract") if isinstance(matched.get("identity_contract"), Mapping) else {}
    carries_identity = bool(
        matched.get("identity_ids") or reference_row.get("identity_ids")
        or identity_contract.get("lead_id") or identity_contract.get("identity_ids")
        or any("identity" in str(ref.get("use") or "").lower()
               for ref in refs if isinstance(ref, Mapping))
    )
    raw_contract = {"clip": matched, "reference_plan_row": reference_row}
    return {
        "clip_id": clip_id,
        "expected_prompt": expected_prompt,
        "required_reference_paths": sorted(required_paths),
        "required_subject_ids": sorted(required_subjects),
        "carries_identity": carries_identity,
        "contract_sha256": stable_hash(raw_contract),
    }


def discover_image_assets(root: Path, *, include_missing_planned: bool = True) -> Dict[str, str]:
    """Discover every B14 image: clip frames, shared assets, candidates and cover."""
    out = _clip_plan_paths(root) if include_missing_planned else {}
    image_root = root / "出图"
    if image_root.is_dir():
        for path in image_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            rel = path.resolve().relative_to(root.resolve()).as_posix()
            if any(part.lower() in EXCLUDED_PARTS or part in EXCLUDED_PARTS for part in Path(rel).parts):
                continue
            out.setdefault(rel, classify_asset(rel))
    return dict(sorted(out.items()))


def parse_reference_spec(root: Path, raw: str) -> Dict[str, Any]:
    """Parse ``PATH::OWNER::USE`` into a current decodable reference receipt."""
    parts = [part.strip() for part in str(raw).split("::", 2)]
    if len(parts) != 3 or not all(parts):
        raise ReceiptError(
            f"--reference-spec 必须是 PATH::OWNER::USE，收到：{raw!r}")
    rel, path = _relative(root, parts[0], must_exist=True)
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        raise ReceiptError(f"参考输入不是受支持图片：{rel}")
    decodable, probe = probe_decodable(path)
    if not decodable:
        raise ReceiptError(f"参考输入不可解码：{rel} · {probe.get('error')}")
    return {
        "path": rel,
        "sha256": sha256_path(path),
        "owner": parts[1],
        "use": parts[2],
        "decodable": True,
        "probe": probe,
    }


def _without_hash(row: Mapping[str, Any], key: str) -> Dict[str, Any]:
    return {k: v for k, v in row.items() if k != key}


def preflight_hash(preflight: Mapping[str, Any]) -> str:
    return stable_hash(_without_hash(preflight, "receipt_sha256"))


def submission_hash(submission: Mapping[str, Any]) -> str:
    return stable_hash(_without_hash(submission, "receipt_sha256"))


def acceptance_hash(asset: str, attempt_id: str, postflight: Mapping[str, Any]) -> str:
    return stable_hash({
        "asset": asset,
        "attempt_id": attempt_id,
        "postflight": _without_hash(postflight, "acceptance_sha256"),
    })


def _current(asset_record: Mapping[str, Any]) -> Mapping[str, Any]:
    value = asset_record.get("current")
    return value if isinstance(value, Mapping) else {}


def current_acceptance_valid(root: Path, ledger: Mapping[str, Any], rel: str,
                             *, _seen: Optional[set[str]] = None) -> Tuple[bool, List[str]]:
    """Validate current pixels and the recursively bound predecessor acceptance."""
    findings: List[str] = []
    seen = set(_seen or set())
    if rel in seen:
        return False, ["previous_acceptance_cycle"]
    seen.add(rel)
    record = (ledger.get("assets") or {}).get(rel) or {}
    current = _current(record)
    post = current.get("postflight") if isinstance(current.get("postflight"), Mapping) else {}
    if post.get("status") != "accepted":
        findings.append("postflight_not_accepted")
        return False, findings
    pre = current.get("preflight") if isinstance(current.get("preflight"), Mapping) else {}
    submission = current.get("submission") if isinstance(current.get("submission"), Mapping) else {}
    if pre.get("status") != "ready" or pre.get("receipt_sha256") != preflight_hash(pre):
        findings.append("invalid_preflight_receipt")
    if submission.get("status") != "recorded" or submission.get("receipt_sha256") != submission_hash(submission):
        findings.append("invalid_submission_receipt")
    if submission.get("bound_preflight_sha256") != pre.get("receipt_sha256"):
        findings.append("submission_preflight_binding_mismatch")
    asset_path = root / rel
    current_sha = sha256_path(asset_path)
    if not current_sha:
        findings.append("asset_missing")
    elif post.get("asset_sha256") != current_sha:
        findings.append("asset_changed_after_acceptance")
    expected_acceptance = acceptance_hash(rel, str(current.get("attempt_id") or ""), post)
    if post.get("acceptance_sha256") != expected_acceptance:
        findings.append("invalid_acceptance_hash")
    if submission.get("asset_sha256") != current_sha:
        findings.append("submission_pixels_stale")
    planned_prompt = pre.get("prompt") if isinstance(pre.get("prompt"), Mapping) else {}
    actual_prompt = submission.get("prompt") if isinstance(submission.get("prompt"), Mapping) else {}
    if planned_prompt != actual_prompt:
        findings.append("planned_actual_prompt_mismatch")
    prompt_rel = str(actual_prompt.get("path") or "")
    if not prompt_rel or sha256_path(root / prompt_rel) != actual_prompt.get("sha256"):
        findings.append("prompt_stale")
    frozen_upstream = pre.get("upstream_contract") if isinstance(pre.get("upstream_contract"), Mapping) else {}
    if frozen_upstream:
        try:
            current_upstream = upstream_contract_for_asset(root, rel)
        except ReceiptError:
            current_upstream = {}
        if (not current_upstream or current_upstream.get("contract_sha256")
                != frozen_upstream.get("contract_sha256")):
            findings.append("upstream_clip_or_reference_contract_stale")
    if pre.get("model") != submission.get("model") or pre.get("channel") != submission.get("channel"):
        findings.append("planned_actual_route_mismatch")
    findings.extend(provider_evidence_findings(
        root, submission, not_before=str(pre.get("created_at") or "")))
    planned_refs = {
        str(row.get("path")): str(row.get("sha256"))
        for row in pre.get("planned_references", []) if isinstance(row, Mapping)
    }
    actual_refs = {
        str(row.get("path")): str(row.get("sha256"))
        for row in submission.get("actual_references", []) if isinstance(row, Mapping)
    }
    if planned_refs != actual_refs:
        findings.append("planned_actual_references_mismatch")
    for ref_rel, ref_sha in actual_refs.items():
        ref_path = root / ref_rel
        if sha256_path(ref_path) != ref_sha:
            findings.append(f"reference_pixels_stale:{ref_rel}")
            continue
        decodable, _probe = probe_decodable(ref_path)
        if not decodable:
            findings.append(f"reference_not_decodable:{ref_rel}")
    machine = post.get("machine_qc") if isinstance(post.get("machine_qc"), Mapping) else {}
    visual = post.get("visual_review") if isinstance(post.get("visual_review"), Mapping) else {}
    if machine.get("verdict") != "ok" or machine.get("precision_level") != "full":
        findings.append("machine_qc_not_full_ok")
    report_rel = str(machine.get("report_path") or "")
    if not report_rel or sha256_path(root / report_rel) != machine.get("report_sha256"):
        findings.append("machine_qc_report_stale")
    if (visual.get("verdict") != "pass" or not str(visual.get("reviewer") or "").strip()
            or not str(visual.get("notes") or "").strip()):
        findings.append("visual_review_not_named_pass")
    if post.get("bound_submission_sha256") != submission.get("receipt_sha256"):
        findings.append("postflight_submission_binding_mismatch")
    previous = pre.get("previous_acceptance") if isinstance(pre.get("previous_acceptance"), Mapping) else {}
    previous_rel = str(previous.get("asset") or "")
    if previous_rel:
        valid, previous_findings = current_acceptance_valid(root, ledger, previous_rel, _seen=seen)
        if not valid:
            findings.append(f"previous_acceptance_stale:{previous_rel}:{','.join(previous_findings)}")
        else:
            prior_post = _current((ledger.get("assets") or {}).get(previous_rel) or {}).get("postflight") or {}
            if previous.get("acceptance_sha256") != prior_post.get("acceptance_sha256"):
                findings.append(f"previous_acceptance_replaced:{previous_rel}")
            if previous.get("asset_sha256") != prior_post.get("asset_sha256"):
                findings.append(f"previous_pixels_replaced:{previous_rel}")
    return not findings, findings


def _predecessor(ledger: Mapping[str, Any], rel: str) -> Optional[str]:
    sequence = [str(x) for x in ledger.get("sequence", [])]
    if rel in sequence:
        idx = sequence.index(rel)
        return sequence[idx - 1] if idx > 0 else None
    return sequence[-1] if sequence else None


def create_preflight(root: Path, *, asset: str, asset_kind: str, owner: str, use: str,
                     identity_scope: str, model: str, channel: str, prompt: str,
                     reference_specs: Sequence[str], subject_ids: Sequence[str] = (),
                     previous_asset: str = "", notes: str = "") -> Dict[str, Any]:
    if identity_scope not in IDENTITY_SCOPES:
        raise ReceiptError(f"identity_scope 必须是 {sorted(IDENTITY_SCOPES)}")
    if asset_kind not in ASSET_KINDS:
        raise ReceiptError(f"asset_kind 必须是 {sorted(ASSET_KINDS)}")
    if not owner.strip() or not use.strip():
        raise ReceiptError("目标图片必须填写非空 --owner 与 --use")
    if not model.strip() or not channel.strip():
        raise ReceiptError("必须填写具体 --model 与访问 --channel")
    rel, _target = _relative(root, asset)
    if Path(rel).suffix.lower() not in IMAGE_SUFFIXES:
        raise ReceiptError(f"目标不是受支持图片路径：{rel}")
    prompt_rel, prompt_path = _relative(root, prompt, must_exist=True)
    references = [parse_reference_spec(root, spec) for spec in reference_specs]
    ref_paths = [row["path"] for row in references]
    if len(ref_paths) != len(set(ref_paths)):
        raise ReceiptError("planned references 含重复路径")
    if identity_scope == "contains_identity" and not references:
        raise ReceiptError("承载主体身份的图片必须至少有一个同源、可解码参考输入")
    planned_subject_ids = sorted({str(v).strip() for v in subject_ids if str(v).strip()})
    upstream = upstream_contract_for_asset(root, rel)
    if upstream:
        expected_prompt = str(upstream.get("expected_prompt") or "")
        if expected_prompt and expected_prompt != prompt_rel:
            raise ReceiptError(
                f"preflight prompt 与 clip_plan 不一致：期望 {expected_prompt}，收到 {prompt_rel}")
        missing_upstream_refs = sorted(set(upstream.get("required_reference_paths") or []) - set(ref_paths))
        if missing_upstream_refs:
            raise ReceiptError(f"preflight 漏掉上游 reference_plan 引用：{', '.join(missing_upstream_refs)}")
        missing_upstream_subjects = sorted(
            set(upstream.get("required_subject_ids") or []) - set(planned_subject_ids))
        if missing_upstream_subjects:
            raise ReceiptError(
                f"preflight 漏掉上游 subject IDs：{', '.join(missing_upstream_subjects)}")
        if upstream.get("carries_identity") and identity_scope != "contains_identity":
            raise ReceiptError("上游 clip identity contract 承载主体身份，不能声明 --identity-scope no_identity")

    ledger = load_ledger(root)
    expected_previous = _predecessor(ledger, rel)
    asserted_previous = ""
    if previous_asset:
        asserted_previous, _ = _relative(root, previous_asset)
        if asserted_previous != expected_previous:
            raise ReceiptError(
                f"上一资产必须是序列直接前驱：期望 {expected_previous or '<首张>'}，收到 {asserted_previous}")
    previous_rel = expected_previous
    previous_receipt: Dict[str, Any] = {}
    if previous_rel:
        valid, findings = current_acceptance_valid(root, ledger, previous_rel)
        if not valid:
            raise ReceiptError(f"上一资产尚无当前像素 accepted：{previous_rel} · {', '.join(findings)}")
        previous_post = _current((ledger.get("assets") or {}).get(previous_rel) or {}).get("postflight") or {}
        previous_current = _current((ledger.get("assets") or {}).get(previous_rel) or {})
        previous_submission = (previous_current.get("submission")
                               if isinstance(previous_current.get("submission"), Mapping) else {})
        if (previous_submission.get("model") != model.strip()
                or previous_submission.get("channel") != channel.strip()):
            raise ReceiptError(
                "model/channel 与上一 accepted 资产不一致；一支 MV 不得静默混用后端。"
                "若要整曲迁移，从 sequence 第一张新建 preflight 并逐张重做")
        previous_receipt = {
            "asset": previous_rel,
            "asset_sha256": previous_post.get("asset_sha256"),
            "acceptance_sha256": previous_post.get("acceptance_sha256"),
        }

    record = (ledger.get("assets") or {}).get(rel) or {}
    attempt_number = len(record.get("attempts") or []) + 1
    attempt_id = f"attempt-{attempt_number:04d}"
    preflight: Dict[str, Any] = {
        "status": "ready",
        "created_at": utc_now(),
        "planned_asset": rel,
        "model": model.strip(),
        "channel": channel.strip(),
        "prompt": {"path": prompt_rel, "sha256": sha256_path(prompt_path)},
        "planned_references": references,
        "planned_subject_ids": planned_subject_ids,
        "upstream_contract": upstream,
        "previous_acceptance": previous_receipt,
        "notes": notes.strip(),
    }
    preflight["receipt_sha256"] = preflight_hash(preflight)
    current = {"attempt_id": attempt_id, "preflight": preflight, "submission": {}, "postflight": {}}
    new_record = {
        "asset_kind": classify_asset(rel) if asset_kind == "auto" else asset_kind.strip(),
        "owner": owner.strip(),
        "use": use.strip(),
        "identity_scope": identity_scope,
        "attempts": list(record.get("attempts") or []) + [current],
        "current": current,
    }
    ledger.setdefault("assets", {})[rel] = new_record
    if rel not in ledger.setdefault("sequence", []):
        ledger["sequence"].append(rel)
    ledger["summary"] = audit_ledger(root, ledger=ledger)["summary"]
    path = write_ledger(root, ledger)
    return {"ledger_path": str(path), "asset": rel, "asset_kind": new_record["asset_kind"],
            "attempt_id": attempt_id, "preflight": preflight}


def _provider_output_binding(evidence: Mapping[str, Any]) -> Tuple[str, str, int] | None:
    adapter_id = str(evidence.get("adapter_id") or "").strip()
    job_id = str(evidence.get("provider_job_id") or "").strip()
    selector = evidence.get("output_selector")
    if (not adapter_id or not job_id or isinstance(selector, bool)
            or not isinstance(selector, int)):
        return None
    return adapter_id, job_id, selector


def _ensure_provider_output_unique(ledger: Mapping[str, Any], evidence: Mapping[str, Any], *,
                                   asset: str, attempt_id: str) -> None:
    binding = _provider_output_binding(evidence)
    if binding is None:
        return
    for other_asset, record in (ledger.get("assets") or {}).items():
        if not isinstance(record, Mapping):
            continue
        attempts = list(record.get("attempts") or [])
        current_view = record.get("current")
        if isinstance(current_view, Mapping):
            attempts.append(current_view)
        for attempt in attempts:
            if not isinstance(attempt, Mapping):
                continue
            other_attempt = str(attempt.get("attempt_id") or "")
            if str(other_asset) == asset and other_attempt == attempt_id:
                continue
            submission = attempt.get("submission")
            if not isinstance(submission, Mapping):
                continue
            other_evidence = submission.get("provider_evidence")
            if (isinstance(other_evidence, Mapping)
                    and _provider_output_binding(other_evidence) == binding):
                raise ReceiptError(
                    "provider output (adapter_id, job_id, output_selector) 已绑定其他 attempt；"
                    "同一 job 多图必须使用不同 output_selector")


def record_submission(root: Path, *, asset: str, model: str, channel: str, prompt: str,
                      references: Sequence[str], subject_ids: Sequence[str] = (),
                      provider_job_id: str = "", provider_evidence: str = "") -> Dict[str, Any]:
    """Validate and record the provider's actual submitted inputs."""
    rel, target_path = _relative(root, asset, must_exist=True)
    decodable, asset_probe = probe_decodable(target_path)
    if not decodable:
        raise ReceiptError(f"生成结果不可解码：{rel} · {asset_probe.get('error')}")
    prompt_rel, prompt_path = _relative(root, prompt, must_exist=True)
    ledger = load_ledger(root)
    record = (ledger.get("assets") or {}).get(rel)
    if not isinstance(record, dict):
        raise ReceiptError(f"缺逐图 preflight：{rel}；先跑 image_receipts.py preflight")
    current = record.get("current") if isinstance(record.get("current"), dict) else {}
    existing_postflight = current.get("postflight") if isinstance(current.get("postflight"), dict) else {}
    if existing_postflight.get("status") in {"accepted", "rejected"}:
        raise ReceiptError(
            f"当前 attempt 已有 {existing_postflight.get('status')} postflight；"
            "不得用新 submission 覆盖，先新建 preflight attempt")
    pre = current.get("preflight") if isinstance(current.get("preflight"), dict) else {}
    if pre.get("status") != "ready" or pre.get("receipt_sha256") != preflight_hash(pre):
        raise ReceiptError(f"preflight 无效或被改写：{rel}")
    if pre.get("model") != model.strip() or pre.get("channel") != channel.strip():
        raise ReceiptError("实际 model/channel 与 preflight 计划不一致")
    planned_prompt = pre.get("prompt") or {}
    if planned_prompt.get("path") != prompt_rel or planned_prompt.get("sha256") != sha256_path(prompt_path):
        raise ReceiptError("实际 prompt 路径或 SHA-256 与 preflight 计划不一致")
    frozen_upstream = pre.get("upstream_contract") if isinstance(pre.get("upstream_contract"), Mapping) else {}
    if frozen_upstream:
        current_upstream = upstream_contract_for_asset(root, rel)
        if (not current_upstream or current_upstream.get("contract_sha256")
                != frozen_upstream.get("contract_sha256")):
            raise ReceiptError("上游 clip/reference contract 在 preflight 后已变化；必须重跑 preflight")

    planned_by_path = {
        str(row.get("path")): row for row in pre.get("planned_references", []) if isinstance(row, dict)
    }
    actual_rows: List[Dict[str, Any]] = []
    for raw in references:
        actual_rel, actual_path = _relative(root, raw, must_exist=True)
        planned = planned_by_path.get(actual_rel)
        if not planned:
            raise ReceiptError(f"实际提交了计划外参考：{actual_rel}")
        decodable_ref, probe = probe_decodable(actual_path)
        current_sha = sha256_path(actual_path)
        if not decodable_ref:
            raise ReceiptError(f"实际参考不可解码：{actual_rel} · {probe.get('error')}")
        if current_sha != planned.get("sha256"):
            raise ReceiptError(f"实际参考 SHA-256 与 preflight 不一致：{actual_rel}")
        actual_rows.append({
            "path": actual_rel,
            "sha256": current_sha,
            "owner": planned.get("owner"),
            "use": planned.get("use"),
            "decodable": True,
            "probe": probe,
        })
    actual_paths = {row["path"] for row in actual_rows}
    missing = sorted(set(planned_by_path) - actual_paths)
    if missing:
        raise ReceiptError(f"计划参考未实际提交：{', '.join(missing)}")
    if len(actual_rows) != len(actual_paths):
        raise ReceiptError("actual references 含重复路径")
    planned_subjects = sorted(str(x) for x in pre.get("planned_subject_ids", []))
    actual_subjects = sorted({str(x).strip() for x in subject_ids if str(x).strip()})
    if actual_subjects != planned_subjects:
        raise ReceiptError(
            f"实际 subject IDs 与 preflight 不一致：planned={planned_subjects}, actual={actual_subjects}")
    previous = pre.get("previous_acceptance") or {}
    if previous:
        valid, findings = current_acceptance_valid(root, ledger, str(previous.get("asset") or ""))
        if not valid:
            raise ReceiptError(f"提交时上一资产验收已失效：{', '.join(findings)}")

    job_id = provider_job_id.strip()
    evidence_value = str(provider_evidence or "").strip()
    evidence_required = provider_evidence_required(channel, model)
    if evidence_required and not job_id:
        raise ReceiptError("正式 provider 结果必须提供非占位 --provider-job-id")
    if evidence_required and not evidence_value:
        raise ReceiptError("正式 provider 结果必须提供项目内 --provider-evidence JSON")
    if bool(job_id) != bool(evidence_value):
        raise ReceiptError("--provider-job-id 与 --provider-evidence 必须成对提供")
    evidence_record: Dict[str, Any] = {}
    if evidence_value:
        evidence_record = validate_provider_evidence(
            root, evidence_value, expected_job_id=job_id, model=model.strip(),
            channel=channel.strip(), asset_sha256=sha256_path(target_path),
            expected_attempt_id=str(current.get("attempt_id") or ""),
            expected_preflight_sha256=str(pre.get("receipt_sha256") or ""),
            not_before=str(pre.get("created_at") or ""))
        _ensure_provider_output_unique(
            ledger, evidence_record, asset=rel,
            attempt_id=str(current.get("attempt_id") or ""))

    existing_submission = (current.get("submission")
                           if isinstance(current.get("submission"), Mapping) else {})
    submission: Dict[str, Any] = {
        "status": "recorded",
        "submitted_at": (str(existing_submission.get("submitted_at") or "")
                         if existing_submission.get("status") == "recorded" else utc_now()),
        "attempt_id": str(current.get("attempt_id") or ""),
        "asset_sha256": sha256_path(target_path),
        "asset_decodable": True,
        "asset_probe": asset_probe,
        "model": model.strip(),
        "channel": channel.strip(),
        "prompt": {"path": prompt_rel, "sha256": sha256_path(prompt_path)},
        "actual_references": sorted(actual_rows, key=lambda row: row["path"]),
        "actual_subject_ids": actual_subjects,
        "provider_job_id": job_id,
        "provider_evidence_required": evidence_required,
        "provider_evidence": evidence_record,
        "bound_preflight_sha256": pre.get("receipt_sha256"),
    }
    submission["receipt_sha256"] = submission_hash(submission)
    if existing_submission.get("status") == "recorded":
        if dict(existing_submission) == submission:
            return {"asset": rel, "attempt_id": current.get("attempt_id"),
                    "preflight_sha256": pre.get("receipt_sha256"),
                    "submission": dict(existing_submission), "idempotent": True}
        raise ReceiptError(
            "当前 attempt 已有不同 submission；只允许字节级幂等重放，"
            "更换 job/evidence/像素必须新建 preflight attempt")
    current["submission"] = submission
    current["postflight"] = {}
    # Keep the history entry and current view as the same logical attempt value.
    attempts = record.get("attempts") or []
    if attempts:
        attempts[-1] = current
    ledger["summary"] = audit_ledger(root, ledger=ledger)["summary"]
    write_ledger(root, ledger)
    return {"asset": rel, "attempt_id": current.get("attempt_id"),
            "preflight_sha256": pre.get("receipt_sha256"), "submission": submission}


def _rows_for_asset(rows: Iterable[Mapping[str, Any]], rel: str) -> List[Mapping[str, Any]]:
    out = []
    for row in rows:
        candidate = str(row.get("png") or row.get("asset") or "").replace(os.sep, "/")
        if candidate == rel:
            out.append(row)
    return out


def machine_qc_for_asset(root: Path, report: Mapping[str, Any], rel: str,
                         record: Mapping[str, Any]) -> Tuple[str, List[str]]:
    """Return pass/block for this asset only; unrelated clips do not poison it."""
    findings: List[str] = []
    actual_sha = sha256_path(root / rel)
    if report.get("kind") != "mv_image_qc":
        findings.append("wrong_qc_kind")
    precision = str((report.get("qc_environment") or {}).get("precision_level") or "")
    if precision != "full":
        findings.append(f"qc_precision_not_full:{precision or 'missing'}")
    if (report.get("assets_sha256") or {}).get(rel) != actual_sha:
        findings.append("qc_asset_sha256_missing_or_stale")

    integrity_rows = _rows_for_asset((report.get("asset_integrity") or {}).get("rows", []), rel)
    if not integrity_rows:
        findings.append("asset_integrity_missing")
    elif any(row.get("verdict") != "ok" for row in integrity_rows):
        findings.append("asset_integrity_not_ok")

    identity_scope = str(record.get("identity_scope") or "")
    face_rows = _rows_for_asset(((report.get("checks") or {}).get("face") or {}).get("shots", []), rel)
    if rel in {str(value) for value in (((report.get("checks") or {}).get("face") or {})
                                        .get("costume_outlier_assets", []) or [])}:
        findings.append("costume_identity_outlier")
    if identity_scope == "contains_identity":
        if not face_rows:
            findings.append("identity_face_check_missing")
        elif any(row.get("verdict") != "ok" for row in face_rows):
            findings.append("identity_face_check_not_ok")
    elif any(row.get("verdict") == "block" for row in face_rows):
        findings.append("face_check_block")

    asset_kind = str(record.get("asset_kind") or "")
    palette_rows = _rows_for_asset(((report.get("checks") or {}).get("palette") or {}).get("shots", []), rel)
    if not asset_kind.startswith("shared_") and palette_rows:
        if any(row.get("verdict") != "ok" for row in palette_rows):
            findings.append("palette_check_not_ok")

    clip_key = Path(rel).stem
    if clip_key.endswith("_end"):
        clip_key = clip_key[:-4]
    for finding in (report.get("shot_variety") or {}).get("findings", []) or []:
        if not isinstance(finding, Mapping):
            continue
        if clip_key in {str(value) for value in finding.get("clips", []) or []}:
            findings.append(f"shot_variety_not_ok:{finding.get('code') or 'finding'}")
    if str(record.get("asset_kind") or "").startswith("clip_"):
        for finding in (report.get("lint") or {}).get("findings", []) or []:
            if not isinstance(finding, Mapping):
                continue
            if clip_key and clip_key in str(finding.get("msg") or ""):
                findings.append(f"prompt_lint_not_ok:{finding.get('code') or 'finding'}")

    provenance_rows = _rows_for_asset((report.get("generation_provenance") or {}).get("rows", []), rel)
    if not provenance_rows or any(row.get("verdict") != "ok" for row in provenance_rows):
        findings.append("generation_provenance_not_ok")
    current = record.get("current") if isinstance(record.get("current"), Mapping) else {}
    current_pre = current.get("preflight") if isinstance(current.get("preflight"), Mapping) else {}
    current_submission = (current.get("submission")
                          if isinstance(current.get("submission"), Mapping) else {})
    for row in provenance_rows:
        if (row.get("b14_attempt_id") != current.get("attempt_id")
                or row.get("b14_preflight_sha256") != current_pre.get("receipt_sha256")
                or row.get("b14_submission_sha256") != current_submission.get("receipt_sha256")):
            findings.append("qc_generation_event_not_bound_to_current_attempt")
    if (report.get("generation_provenance") or {}).get("uniform") is False:
        findings.append("project_model_channel_not_uniform")
    if _rows_for_asset((report.get("prohibited_local_patch_outputs") or {}).get("outputs", []), rel):
        findings.append("prohibited_local_patch")
    return ("pass" if not findings else "block"), findings


def record_postflight(root: Path, *, asset: str, qc_report: str, reviewer: str,
                      visual_verdict: str, notes: str) -> Dict[str, Any]:
    rel, target_path = _relative(root, asset, must_exist=True)
    if visual_verdict not in {"pass", "reject", "unverifiable"}:
        raise ReceiptError("--visual-verdict 必须是 pass|reject|unverifiable")
    if not reviewer.strip() or not notes.strip():
        raise ReceiptError("逐图目视必须填写具名 --reviewer 与非空 --notes")
    qc_rel, qc_path = _relative(root, qc_report or QC_REL.as_posix(), must_exist=True)
    try:
        report = json.loads(qc_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReceiptError(f"image_qc 报告不可读：{qc_rel}: {exc}") from exc
    ledger = load_ledger(root)
    record = (ledger.get("assets") or {}).get(rel)
    if not isinstance(record, dict):
        raise ReceiptError(f"缺逐图 preflight：{rel}")
    current = record.get("current") if isinstance(record.get("current"), dict) else {}
    existing_postflight = current.get("postflight") if isinstance(current.get("postflight"), dict) else {}
    if existing_postflight.get("status") in {"accepted", "rejected"}:
        raise ReceiptError(
            f"当前 attempt 已有 {existing_postflight.get('status')} postflight；"
            "不得覆盖逐图结论，先新建 preflight attempt（rejected 需重抽）")
    submission = current.get("submission") if isinstance(current.get("submission"), dict) else {}
    if submission.get("status") != "recorded" or submission.get("receipt_sha256") != submission_hash(submission):
        raise ReceiptError(f"缺有效 actual submission receipt：{rel}")
    current_sha = sha256_path(target_path)
    if submission.get("asset_sha256") != current_sha:
        raise ReceiptError(f"当前像素已不同于 actual submission：{rel}")
    machine_verdict, machine_findings = machine_qc_for_asset(root, report, rel, record)
    preflight = current.get("preflight") if isinstance(current.get("preflight"), dict) else {}
    machine_findings.extend(provider_evidence_findings(
        root, submission, not_before=str(preflight.get("created_at") or "")))
    for reference in submission.get("actual_references", []) or []:
        if not isinstance(reference, dict):
            machine_findings.append("invalid_actual_reference_receipt")
            continue
        reference_rel = str(reference.get("path") or "")
        reference_path = root / reference_rel
        if sha256_path(reference_path) != reference.get("sha256"):
            machine_findings.append(f"reference_changed_after_submission:{reference_rel}")
            continue
        ref_decodable, _ref_probe = probe_decodable(reference_path)
        if not ref_decodable:
            machine_findings.append(f"reference_not_decodable_after_submission:{reference_rel}")
    prompt_row = submission.get("prompt") if isinstance(submission.get("prompt"), dict) else {}
    if sha256_path(root / str(prompt_row.get("path") or "")) != prompt_row.get("sha256"):
        machine_findings.append("prompt_changed_after_submission")
    previous = preflight.get("previous_acceptance") if isinstance(preflight.get("previous_acceptance"), dict) else {}
    if previous:
        valid_previous, previous_findings = current_acceptance_valid(
            root, ledger, str(previous.get("asset") or ""))
        if not valid_previous:
            machine_findings.append(f"previous_acceptance_stale:{','.join(previous_findings)}")
    machine_verdict = "pass" if not machine_findings else "block"
    accepted = machine_verdict == "pass" and visual_verdict == "pass"
    # Global image_qc is refreshed after every image.  Preserve an immutable
    # per-attempt snapshot so accepting image N+1 does not invalidate the
    # already accepted image N merely because the aggregate report was rerun.
    safe_asset = re.sub(r"[^A-Za-z0-9._-]+", "_", rel).strip("_")[-96:] or "asset"
    attempt_id = str(current.get("attempt_id") or "attempt")
    snapshot_rel = (LEDGER_REL.parent / "qc_snapshots" /
                    f"{safe_asset}.{attempt_id}.{current_sha[:12]}.json")
    snapshot_path = root / snapshot_rel
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    postflight: Dict[str, Any] = {
        "status": "accepted" if accepted else "rejected",
        "reviewed_at": utc_now(),
        "asset_sha256": current_sha,
        "machine_qc": {
            "source_report_path": qc_rel,
            "report_path": snapshot_rel.as_posix(),
            "report_sha256": sha256_path(snapshot_path),
            "verdict": "ok" if machine_verdict == "pass" else "block",
            "precision_level": str((report.get("qc_environment") or {}).get("precision_level") or ""),
            "findings": machine_findings,
        },
        "visual_review": {
            "reviewer": reviewer.strip(),
            "verdict": visual_verdict,
            "notes": notes.strip(),
            "scope": "current_pixels_side_by_side_with_planned_references_and_previous_accepted_asset",
        },
        "bound_submission_sha256": submission.get("receipt_sha256"),
    }
    postflight["acceptance_sha256"] = acceptance_hash(
        rel, str(current.get("attempt_id") or ""), postflight)
    current["postflight"] = postflight
    attempts = record.get("attempts") or []
    if attempts:
        attempts[-1] = current
    ledger["summary"] = audit_ledger(root, ledger=ledger)["summary"]
    path = write_ledger(root, ledger)
    return {"ledger_path": str(path), "asset": rel, "attempt_id": current.get("attempt_id"),
            "accepted": accepted, "postflight": postflight}


def audit_ledger(root: Path, *, ledger: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    data = dict(ledger or load_ledger(root))
    assets = data.get("assets") or {}
    expected = discover_image_assets(root, include_missing_planned=True)
    for rel in data.get("sequence", []) or []:
        expected.setdefault(str(rel), classify_asset(str(rel)))
    rows: List[Dict[str, Any]] = []
    accepted = stale = untracked = missing = 0
    for rel, kind in expected.items():
        path = root / rel
        findings: List[str] = []
        if not path.is_file():
            findings.append("asset_missing")
            missing += 1
        if rel not in assets:
            findings.append("untracked_asset")
            untracked += 1
        else:
            valid, invalid = current_acceptance_valid(root, data, rel)
            if not valid:
                findings.extend(invalid)
        if not findings:
            accepted += 1
            status = "accepted"
        else:
            stale += 1
            status = "stale"
        rows.append({"asset": rel, "asset_kind": kind, "status": status,
                     "asset_sha256": sha256_path(path), "findings": findings})
    summary = {
        "computed_at": utc_now(),
        "expected": len(expected),
        "tracked": sum(1 for rel in expected if rel in assets),
        "accepted": accepted,
        "stale": stale,
        "untracked": untracked,
        "missing": missing,
        "all_current_accepted": bool(expected) and stale == 0,
    }
    return {"kind": "mv_image_acceptance_audit", "schema_version": 1,
            "ledger_path": LEDGER_REL.as_posix(), "summary": summary, "rows": rows}


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="MV B14 逐图生成前/后双闸收据")
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="花费前冻结单张目标与参考输入")
    pre.add_argument("project_root")
    pre.add_argument("--asset", required=True)
    pre.add_argument("--asset-kind", default="auto", choices=sorted(ASSET_KINDS))
    pre.add_argument("--owner", required=True, help="本张主体/资产 owner，如 lead:主唱")
    pre.add_argument("--use", required=True, help="本张用途，如 clip_start / identity_master / cover")
    pre.add_argument("--identity-scope", required=True, choices=sorted(IDENTITY_SCOPES))
    pre.add_argument("--model", required=True)
    pre.add_argument("--channel", required=True)
    pre.add_argument("--prompt", required=True)
    pre.add_argument("--reference-spec", action="append", default=[], metavar="PATH::OWNER::USE",
                     help="计划真实提交的参考图；每张重复一次")
    pre.add_argument("--subject-id", action="append", default=[])
    pre.add_argument("--previous-asset", default="",
                     help="可选显式断言；必须等于 ledger 序列直接前驱且其当前像素已 accepted")
    pre.add_argument("--notes", default="")

    post = sub.add_parser("postflight", help="机检后绑定当前像素与具名逐图目视")
    post.add_argument("project_root")
    post.add_argument("--asset", required=True)
    post.add_argument("--qc-report", default=QC_REL.as_posix())
    post.add_argument("--reviewer", required=True)
    post.add_argument("--visual-verdict", required=True, choices=("pass", "reject", "unverifiable"))
    post.add_argument("--notes", required=True)

    status = sub.add_parser("status", help="核验全集当前像素 accepted 状态")
    status.add_argument("project_root")
    status.add_argument("--json", action="store_true")

    ns = parser.parse_args(argv)
    root = Path(ns.project_root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"找不到作品根：{root}")
    try:
        if ns.command == "preflight":
            result = create_preflight(
                root, asset=ns.asset, asset_kind=ns.asset_kind, owner=ns.owner, use=ns.use,
                identity_scope=ns.identity_scope, model=ns.model, channel=ns.channel,
                prompt=ns.prompt, reference_specs=ns.reference_spec,
                subject_ids=ns.subject_id, previous_asset=ns.previous_asset, notes=ns.notes)
            _print_json(result)
            return 0
        if ns.command == "postflight":
            result = record_postflight(
                root, asset=ns.asset, qc_report=ns.qc_report, reviewer=ns.reviewer,
                visual_verdict=ns.visual_verdict, notes=ns.notes)
            _print_json(result)
            return 0 if result["accepted"] else 1
        audit = audit_ledger(root)
        ledger = load_ledger(root)
        ledger["summary"] = audit["summary"]
        write_ledger(root, ledger)
        if ns.json:
            _print_json(audit)
        else:
            summary = audit["summary"]
            print(f"B14 images: accepted {summary['accepted']}/{summary['expected']} · "
                  f"stale {summary['stale']} · untracked {summary['untracked']} · missing {summary['missing']}")
            for row in audit["rows"]:
                if row["findings"]:
                    print(f"[block] {row['asset']}: {', '.join(row['findings'])}")
        return 0 if audit["summary"]["all_current_accepted"] else 1
    except ReceiptError as exc:
        print(f"[block] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
