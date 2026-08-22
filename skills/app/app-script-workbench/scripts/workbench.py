#!/usr/bin/env python3
"""Build, migrate, validate, and complete the standalone canvas workbench v3 contract."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

SCHEMA = "app-script-workbench/v3"
SKILL = "app-script-workbench"
LEGACY_SCHEMAS = {
    "app-script-workbench/v2",
    "app-script-workbench/v1",
    "n2d-script-workbench/v1",
    "app-n2d-script-workbench/v1",
}
LEGACY_SKILLS = {"n2d-script-workbench", "app-n2d-script-workbench"}
WORKFLOW_STATES = {"draft", "ready", "running", "needs_revision", "blocked", "machine_complete", "complete"}
ACCEPTANCE_POLICIES = {"delegated", "human"}
ASSET_KINDS = {"character", "scene", "prop"}
ASSET_STATES = {"pending", "generating", "machine_complete", "accepted", "failed", "stale"}
ASSET_SOURCES = {"none", "ai", "canvas", "upload"}
JOB_KINDS = {"asset_image", "shot_image", "shot_video", "master"}
JOB_STATES = {"draft", "ready", "queued", "running", "succeeded", "failed", "cancelled", "blocked", "stale"}
RESULT_REVIEWS = {"pending", "machine_complete", "accepted", "rejected", "stale"}
MASTER_STATES = {"pending", "machine_complete", "stale"}
QC_VERDICTS = {"pending", "pass", "block", "stale"}
REVIEWER_KINDS = {"delegated_agent", "human"}
COMPLETION_DEFINITION = "app-script-workbench/final-master/v2"
SHA256_LENGTH = 64
HUMAN_CONFIRMATION_KIND = "current_artifact_bytes"

SHOT_FIELDS = ("id", "duration", "visual", "scale", "lighting", "dialogue", "sound", "camera", "final_prompt", "color")
SHOT_REQUIRED_TEXT_FIELDS = ("id", "visual", "scale", "lighting", "sound", "camera")
ASSET_FIELDS = ("id", "kind", "name", "description", "prompt", "status", "source", "sha256")
ASSET_EVIDENCE_FIELDS = ("path", "attachmentId", "nodeId", "imageUrl", "mimeType", "error")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON 顶层必须是 object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically replace one workbench document in its own directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary:
            try:
                Path(temporary).unlink()
            except FileNotFoundError:
                pass


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != SHA256_LENGTH:
        return False
    return all(character in "0123456789abcdef" for character in value.lower())


def canonical_json(value: Any) -> str:
    """Cross-runtime canonical form: sorted keys, UTF-8 text, compact separators."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(canonical_content(payload)).encode("utf-8")).hexdigest()


def stable_id(prefix: str, index: int, name: str) -> str:
    digest = hashlib.sha256(f"{prefix}:{index}:{name}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"


def _clean_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).replace("\x00", "").strip() or fallback


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        cleaned = _clean_text(item)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _clean_blocks(value: Any) -> list[str]:
    """Never turn malformed blocking evidence into an accidental empty list."""
    if value is None:
        return []
    if isinstance(value, list):
        return _clean_list(value)
    if isinstance(value, str):
        cleaned = _clean_text(value)
        return [cleaned] if cleaned else []
    return ["malformed blocks field"]


def _has_timezone_timestamp(value: Any) -> bool:
    text = _clean_text(value)
    if not text:
        return False
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _is_named_human(value: Any) -> bool:
    reviewer = _clean_text(value)
    if len(reviewer) < 2:
        return False
    lowered = reviewer.casefold()
    return not any(token in lowered for token in ("agent", "delegate", "auto", "robot", "system", "model", "助手", "代理"))


def normalize_confirmation(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    return {
        "kind": _clean_text(source.get("kind")),
        "artifact_sha256": _clean_text(source.get("artifact_sha256") or source.get("output_sha256")).lower(),
        "current_pixels_reviewed": source.get("current_pixels_reviewed") is True,
        "decision": _clean_text(source.get("decision")),
        "statement": _clean_text(source.get("statement")),
    }


def _unique_id(candidate: str, fallback: str, seen: set[str]) -> str:
    base = candidate or fallback
    if base not in seen:
        seen.add(base)
        return base
    suffix = 2
    while f"{base}-{suffix}" in seen:
        suffix += 1
    result = f"{base}-{suffix}"
    seen.add(result)
    return result


def normalize_shot(raw: dict[str, Any], index: int, seen: set[str] | None = None) -> dict[str, Any]:
    visual = _clean_text(raw.get("visual") or raw.get("description"))
    try:
        parsed = float(raw.get("duration") or 5)
        duration = min(15, max(5, math.floor(parsed + 0.5))) if math.isfinite(parsed) else 5
    except (TypeError, ValueError, OverflowError):
        duration = 5
    candidate = _clean_text(raw.get("id"))
    fallback = stable_id("shot", index, visual)
    shot_id = _unique_id(candidate, fallback, seen) if seen is not None else candidate or fallback
    return {
        "id": shot_id,
        "duration": duration,
        "visual": visual,
        "scale": _clean_text(raw.get("scale"), "中景"),
        "lighting": _clean_text(raw.get("lighting"), "自然光，电影感"),
        "dialogue": _clean_text(raw.get("dialogue")),
        "sound": _clean_text(raw.get("sound"), "环境底噪"),
        "camera": _clean_text(raw.get("camera"), "固定机位"),
        "final_prompt": _clean_text(raw.get("final_prompt") or raw.get("finalPrompt")),
        "color": _clean_text(raw.get("color")),
    }


def normalize_asset(raw: dict[str, Any], index: int, seen: set[str] | None = None) -> dict[str, Any]:
    kind = _clean_text(raw.get("kind"), "character")
    if kind not in ASSET_KINDS:
        kind = "character"
    name = _clean_text(raw.get("name"))
    candidate = _clean_text(raw.get("id"))
    fallback = stable_id("asset", index, f"{kind}:{name}")
    asset_id = _unique_id(candidate, fallback, seen) if seen is not None else candidate or fallback
    status = _clean_text(raw.get("status"), "pending")
    if status == "ready":
        status = "machine_complete"
    source = _clean_text(raw.get("source"), "none")
    result: dict[str, Any] = {
        "id": asset_id,
        "kind": kind,
        "name": name,
        "description": _clean_text(raw.get("description")),
        "prompt": _clean_text(raw.get("prompt")),
        "status": status if status in ASSET_STATES else "pending",
        "source": source if source in ASSET_SOURCES else "none",
        "sha256": _clean_text(raw.get("sha256") or raw.get("content_sha256")).lower(),
        "acceptance_receipt": normalize_acceptance_receipt(raw.get("acceptance_receipt") or raw.get("acceptance")),
    }
    for field in ASSET_EVIDENCE_FIELDS:
        value = _clean_text(raw.get(field))
        if value:
            result[field] = value
    if result["status"] in {"machine_complete", "accepted"} and not has_real_asset_source(result):
        result["status"] = "pending"
    return result


def normalize_delivery_spec(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    return {
        "container": _clean_text(source.get("container"), "mp4").lower(),
        "mime_type": _clean_text(source.get("mime_type") or source.get("mimeType"), "video/mp4").lower(),
        "aspect_ratio": _clean_text(source.get("aspect_ratio") or source.get("aspectRatio"), "16:9"),
        "resolution": _clean_text(source.get("resolution"), "project"),
        "require_audio": source.get("require_audio") is True or source.get("requireAudio") is True,
    }


def normalize_acceptance_receipt(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    return {
        "reviewer_kind": _clean_text(source.get("reviewer_kind") or source.get("reviewerKind")),
        "reviewer_name": _clean_text(source.get("reviewer_name") or source.get("reviewerName") or source.get("reviewer")),
        "verdict": _clean_text(source.get("verdict"), "pending"),
        "content_sha256": _clean_text(source.get("content_sha256") or source.get("input_sha256")).lower(),
        "output_sha256": _clean_text(source.get("output_sha256")).lower(),
        "criteria": _clean_list(source.get("criteria")),
        "blocks": _clean_blocks(source.get("blocks")),
        "reviewed_at": _clean_text(source.get("reviewed_at") or source.get("reviewedAt")),
        "confirmation": normalize_confirmation(source.get("confirmation")),
    }


def normalize_machine_receipt(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    return {
        "reviewer_kind": _clean_text(source.get("reviewer_kind") or source.get("reviewerKind")),
        "verdict": _clean_text(source.get("verdict"), "pending"),
        "content_sha256": _clean_text(source.get("content_sha256") or source.get("input_sha256")).lower(),
        "output_sha256": _clean_text(source.get("output_sha256")).lower(),
        "checks": _clean_list(source.get("checks") or source.get("criteria")),
        "blocks": _clean_blocks(source.get("blocks")),
        "completed_at": _clean_text(source.get("completed_at") or source.get("reviewed_at") or source.get("reviewedAt")),
    }


def normalize_job(raw: dict[str, Any], index: int) -> dict[str, Any]:
    kind = _clean_text(raw.get("kind"), "shot_video")
    status = _clean_text(raw.get("status"), "draft")
    return {
        "id": _clean_text(raw.get("id"), stable_id("job", index, f"{kind}:{raw.get('shot_id', '')}")),
        "kind": kind if kind in JOB_KINDS else "shot_video",
        "shot_id": _clean_text(raw.get("shot_id") or raw.get("shotId")),
        "input_sha256": _clean_text(raw.get("input_sha256") or raw.get("content_sha256")).lower(),
        "status": status if status in JOB_STATES else "draft",
        "run_id": _clean_text(raw.get("run_id") or raw.get("runId")),
        "error": _clean_text(raw.get("error")),
    }


def normalize_result(raw: dict[str, Any], index: int) -> dict[str, Any]:
    shot_id = _clean_text(raw.get("shot_id") or raw.get("shotId"))
    review = _clean_text(raw.get("review"), "pending")
    if review == "ready":
        review = "machine_complete"
    result = {
        "id": _clean_text(raw.get("id"), stable_id("result", index, shot_id)),
        "kind": "shot_video",
        "shot_id": shot_id,
        "input_sha256": _clean_text(raw.get("input_sha256") or raw.get("content_sha256")).lower(),
        "path": _clean_text(raw.get("path")),
        "sha256": _clean_text(raw.get("sha256") or raw.get("output_sha256")).lower(),
        "review": review if review in RESULT_REVIEWS else "pending",
        "machine_receipt": normalize_machine_receipt(raw.get("machine_receipt") or raw.get("machineReceipt")),
        "acceptance_receipt": normalize_acceptance_receipt(raw.get("acceptance_receipt") or raw.get("acceptance")),
        "notes": _clean_text(raw.get("notes")),
    }
    legacy_receipt = raw.get("legacy_acceptance_receipt")
    if isinstance(legacy_receipt, dict):
        result["legacy_acceptance_receipt"] = legacy_receipt
    return result


def normalize_master(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    status = _clean_text(source.get("status"), "pending")
    if status == "ready":
        status = "machine_complete"
    try:
        duration = float(source.get("duration") or 0)
        if not math.isfinite(duration) or duration < 0:
            duration = 0
    except (TypeError, ValueError, OverflowError):
        duration = 0
    return {
        "status": status if status in MASTER_STATES else "pending",
        "input_sha256": _clean_text(source.get("input_sha256") or source.get("content_sha256")).lower(),
        "path": _clean_text(source.get("path")),
        "sha256": _clean_text(source.get("sha256") or source.get("output_sha256")).lower(),
        "mime_type": _clean_text(source.get("mime_type") or source.get("mimeType"), "video/mp4").lower(),
        "duration": duration,
    }


def normalize_qc_receipt(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    verdict = _clean_text(source.get("verdict"), "pending")
    result = {
        "verdict": verdict if verdict in QC_VERDICTS else "pending",
        "reviewer_kind": _clean_text(source.get("reviewer_kind") or source.get("reviewerKind")),
        "content_sha256": _clean_text(source.get("content_sha256")).lower(),
        "master_sha256": _clean_text(source.get("master_sha256") or source.get("output_sha256")).lower(),
        "checks": _clean_list(source.get("checks")),
        "blocks": _clean_blocks(source.get("blocks")),
        "notes": _clean_text(source.get("notes")),
        "reviewed_at": _clean_text(source.get("reviewed_at") or source.get("reviewedAt")),
        "receipt_path": _clean_text(source.get("receipt_path") or source.get("receiptPath")),
        "receipt_sha256": _clean_text(source.get("receipt_sha256") or source.get("receiptSha256")).lower(),
    }
    return result


def normalize_final_acceptance_receipt(raw: Any) -> dict[str, Any]:
    return normalize_acceptance_receipt(raw)


def canonical_content(payload: dict[str, Any]) -> dict[str, Any]:
    """Return only production intent; runtime, layout, UI color, and timestamps stay out."""
    shots = []
    for raw in payload.get("shots", []):
        if isinstance(raw, dict):
            shots.append({field: raw.get(field, "") for field in SHOT_FIELDS if field != "color"})
    assets = []
    for raw in payload.get("assets", []):
        if isinstance(raw, dict):
            assets.append({
                "id": raw.get("id", ""),
                "kind": raw.get("kind", ""),
                "name": raw.get("name", ""),
                "description": raw.get("description", ""),
                "prompt": raw.get("prompt", ""),
                "sha256": raw.get("sha256", ""),
            })
    return {
        "acceptance_policy": payload.get("acceptance_policy", "delegated"),
        "assets": assets,
        "delivery_spec": normalize_delivery_spec(payload.get("delivery_spec")),
        "global_style": payload.get("global_style", ""),
        "shots": shots,
        "title": payload.get("title", ""),
    }


def _resolve_media_path(value: str, base_dir: Path | None) -> Path | None:
    if not value:
        return None
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        if base_dir is None:
            return None
        candidate = base_dir / candidate
    try:
        return candidate.resolve()
    except OSError:
        return candidate.absolute()


def file_matches(value: str, expected_sha256: str, base_dir: Path | None) -> bool:
    if base_dir is None or not value or not is_sha256(expected_sha256):
        return False
    candidate = _resolve_media_path(value, base_dir)
    if candidate is None or not candidate.is_file():
        return False
    try:
        return file_sha256(candidate) == expected_sha256.lower()
    except OSError:
        return False


def has_real_asset_source(asset: dict[str, Any], base_dir: Path | None = None) -> bool:
    if asset.get("source") == "none" or not is_sha256(asset.get("sha256")):
        return False
    path_value = _clean_text(asset.get("path"))
    if path_value:
        return file_matches(path_value, str(asset.get("sha256")), base_dir) if base_dir is not None else True
    if _clean_text(asset.get("attachmentId")) or _clean_text(asset.get("nodeId")):
        return True
    image_url = _clean_text(asset.get("imageUrl")).lower()
    return image_url.startswith(("http://", "https://", "data:image/", "/")) and not image_url.startswith("blob:")


def human_acceptance_receipt_passes(receipt: dict[str, Any], current_hash: str, output_hash: str) -> bool:
    confirmation = receipt.get("confirmation", {})
    return (
        receipt.get("reviewer_kind") == "human"
        and _is_named_human(receipt.get("reviewer_name"))
        and receipt.get("verdict") == "accepted"
        and receipt.get("content_sha256") == current_hash
        and receipt.get("output_sha256") == output_hash
        and bool(receipt.get("criteria"))
        and not receipt.get("blocks")
        and _has_timezone_timestamp(receipt.get("reviewed_at"))
        and isinstance(confirmation, dict)
        and confirmation.get("kind") == HUMAN_CONFIRMATION_KIND
        and confirmation.get("artifact_sha256") == output_hash
        and confirmation.get("current_pixels_reviewed") is True
        and confirmation.get("decision") == "accept"
        and bool(_clean_text(confirmation.get("statement")))
    )


def machine_receipt_passes(receipt: dict[str, Any], current_hash: str, output_hash: str) -> bool:
    return (
        receipt.get("reviewer_kind") in REVIEWER_KINDS
        and receipt.get("verdict") == "pass"
        and receipt.get("content_sha256") == current_hash
        and receipt.get("output_sha256") == output_hash
        and bool(receipt.get("checks"))
        and not receipt.get("blocks")
    )


def asset_is_accepted(asset: dict[str, Any], payload: dict[str, Any], base_dir: Path | None) -> bool:
    output_hash = str(asset.get("sha256", ""))
    path = str(asset.get("path", ""))
    return (
        asset.get("status") == "accepted"
        and file_matches(path, output_hash, base_dir)
        and human_acceptance_receipt_passes(
            asset.get("acceptance_receipt", {}),
            str(payload.get("content_sha256", "")),
            output_hash,
        )
    )


def result_is_machine_complete(result: dict[str, Any], payload: dict[str, Any], base_dir: Path | None) -> bool:
    current_hash = str(payload.get("content_sha256", ""))
    output_hash = str(result.get("sha256", ""))
    return (
        result.get("review") in {"machine_complete", "accepted"}
        and result.get("input_sha256") == current_hash
        and file_matches(str(result.get("path", "")), output_hash, base_dir)
        and machine_receipt_passes(result.get("machine_receipt", {}), current_hash, output_hash)
    )


def result_is_accepted(result: dict[str, Any], payload: dict[str, Any], base_dir: Path | None) -> bool:
    current_hash = str(payload.get("content_sha256", ""))
    output_hash = str(result.get("sha256", ""))
    return (
        result.get("review") == "accepted"
        and result.get("input_sha256") == current_hash
        and result_is_machine_complete(result, payload, base_dir)
        and human_acceptance_receipt_passes(
            result.get("acceptance_receipt", {}),
            current_hash,
            output_hash,
        )
    )


def master_is_ready(payload: dict[str, Any], base_dir: Path | None) -> bool:
    master = payload.get("master", {})
    return (
        isinstance(master, dict)
        and master.get("status") == "machine_complete"
        and master.get("input_sha256") == payload.get("content_sha256")
        and file_matches(str(master.get("path", "")), str(master.get("sha256", "")), base_dir)
    )


def qc_receipt_passes(payload: dict[str, Any], base_dir: Path | None) -> bool:
    receipt = payload.get("qc_receipt", {})
    master = payload.get("master", {})
    if not isinstance(receipt, dict) or not isinstance(master, dict):
        return False
    return (
        receipt.get("verdict") == "pass"
        and receipt.get("content_sha256") == payload.get("content_sha256")
        and receipt.get("master_sha256") == master.get("sha256")
        and bool(receipt.get("checks"))
        and not receipt.get("blocks")
        and receipt.get("reviewer_kind") in REVIEWER_KINDS
        and file_matches(
            str(receipt.get("receipt_path", "")),
            str(receipt.get("receipt_sha256", "")),
            base_dir,
        )
    )


def final_acceptance_passes(payload: dict[str, Any]) -> bool:
    receipt = payload.get("final_acceptance_receipt", {})
    master = payload.get("master", {})
    if not isinstance(receipt, dict) or not isinstance(master, dict):
        return False
    return human_acceptance_receipt_passes(
        receipt,
        str(payload.get("content_sha256", "")),
        str(master.get("sha256", "")),
    )


def authoring_gaps(payload: dict[str, Any], base_dir: Path | None) -> list[str]:
    gaps: list[str] = []
    shots = payload.get("shots", [])
    if not isinstance(shots, list) or not shots:
        gaps.append("至少需要一个镜头")
    else:
        for index, shot in enumerate(shots, 1):
            if not isinstance(shot, dict):
                gaps.append(f"镜头 {index} 格式无效")
                continue
            if not all(_clean_text(shot.get(field)) for field in SHOT_REQUIRED_TEXT_FIELDS):
                gaps.append(f"镜头 {shot.get('id') or index} 的制作字段未补齐")
            try:
                duration = float(shot.get("duration", 0))
            except (TypeError, ValueError):
                duration = 0
            if not math.isfinite(duration) or duration < 5 or duration > 15:
                gaps.append(f"镜头 {shot.get('id') or index} 的时长不在 5–15 秒")
            if not _clean_text(shot.get("final_prompt")):
                gaps.append(f"镜头 {shot.get('id') or index} 缺最终提示词")
    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        gaps.append("assets 必须是 array")
    else:
        for index, asset in enumerate(assets, 1):
            if (
                not isinstance(asset, dict)
                or asset.get("status") not in {"machine_complete", "accepted"}
                or not has_real_asset_source(asset, base_dir)
            ):
                gaps.append(f"资产 {asset.get('id') if isinstance(asset, dict) else index} 未绑定当前真实内容 SHA")
    return gaps


def machine_completion_gaps(payload: dict[str, Any], base_dir: Path | None) -> list[str]:
    gaps = authoring_gaps(payload, base_dir)
    current_hash = str(payload.get("content_sha256", ""))
    for index, asset in enumerate(payload.get("assets", []), 1):
        if isinstance(asset, dict) and not asset_is_accepted(asset, payload, base_dir):
            gaps.append(f"资产 {asset.get('id') or index} 缺具名真人对当前图片字节的验收回执")
    results = payload.get("results", []) if isinstance(payload.get("results"), list) else []
    for shot in payload.get("shots", []):
        if not isinstance(shot, dict):
            continue
        shot_id = str(shot.get("id", ""))
        if not any(
            isinstance(result, dict) and result.get("shot_id") == shot_id and result_is_machine_complete(result, payload, base_dir)
            for result in results
        ):
            gaps.append(f"镜头 {shot_id} 缺少绑定当前内容哈希与真实字节的 machine_complete 视频")
    current_jobs = [
        job for job in payload.get("jobs", [])
        if isinstance(job, dict) and job.get("input_sha256") == current_hash
    ]
    if any(job.get("status") in {"queued", "running", "blocked"} for job in current_jobs):
        gaps.append("仍有当前版本任务未结束或被硬闸阻断")
    if not master_is_ready(payload, base_dir):
        gaps.append("最终母版不存在、字节 SHA 不匹配或未绑定当前内容哈希")
    if not qc_receipt_passes(payload, base_dir):
        gaps.append("最终 QC 收据未通过、收据文件字节不匹配、含 block 或未同时绑定内容与母版 SHA")
    return list(dict.fromkeys(gaps))


def completion_gaps(payload: dict[str, Any], base_dir: Path | None) -> list[str]:
    gaps = machine_completion_gaps(payload, base_dir)
    if not final_acceptance_passes(payload):
        gaps.append("最终母版缺具名真人、带时区且绑定当前字节 SHA 的显式验收回执")
    return list(dict.fromkeys(gaps))


def _invalidate_runtime(payload: dict[str, Any]) -> None:
    for job in payload.get("jobs", []):
        if isinstance(job, dict):
            job["status"] = "stale"
    for result in payload.get("results", []):
        if isinstance(result, dict):
            result["review"] = "stale"
    master = payload.get("master")
    if isinstance(master, dict) and (master.get("path") or master.get("sha256") or master.get("input_sha256")):
        master["status"] = "stale"
    receipt = payload.get("qc_receipt")
    if isinstance(receipt, dict) and receipt.get("verdict") != "pending":
        receipt["verdict"] = "stale"
    final_receipt = payload.get("final_acceptance_receipt")
    if isinstance(final_receipt, dict) and final_receipt.get("verdict") != "pending":
        final_receipt["verdict"] = "stale"


def _invalidate_mismatched_runtime(payload: dict[str, Any], base_dir: Path | None) -> None:
    current_hash = payload.get("content_sha256")
    broken_asset = False
    for asset in payload.get("assets", []):
        if isinstance(asset, dict) and asset.get("status") in {"machine_complete", "accepted"}:
            if not has_real_asset_source(asset, base_dir):
                asset["status"] = "stale"
                broken_asset = True
            elif asset.get("status") == "accepted" and not asset_is_accepted(asset, payload, base_dir):
                asset["status"] = "machine_complete"
    if broken_asset:
        _invalidate_runtime(payload)
    for job in payload.get("jobs", []):
        if isinstance(job, dict) and job.get("input_sha256") != current_hash:
            job["status"] = "stale"
    for result in payload.get("results", []):
        if not isinstance(result, dict):
            continue
        if result.get("input_sha256") != current_hash:
            result["review"] = "stale"
        elif result.get("review") in {"machine_complete", "accepted"} and not result_is_machine_complete(result, payload, base_dir):
            result["review"] = "stale"
        elif result.get("review") == "accepted" and not result_is_accepted(result, payload, base_dir):
            result["review"] = "machine_complete"
    master = payload.get("master", {})
    if isinstance(master, dict):
        if master.get("input_sha256") and master.get("input_sha256") != current_hash:
            master["status"] = "stale"
        elif master.get("status") == "machine_complete" and base_dir is not None and not file_matches(
            str(master.get("path", "")), str(master.get("sha256", "")), base_dir
        ):
            master["status"] = "stale"
    receipt = payload.get("qc_receipt", {})
    if isinstance(receipt, dict) and receipt.get("verdict") == "pass":
        if (
            receipt.get("content_sha256") != current_hash
            or not isinstance(master, dict)
            or receipt.get("master_sha256") != master.get("sha256")
            or master.get("status") != "machine_complete"
            or not file_matches(
                str(receipt.get("receipt_path", "")),
                str(receipt.get("receipt_sha256", "")),
                base_dir,
            )
        ):
            receipt["verdict"] = "stale"
    final_receipt = payload.get("final_acceptance_receipt", {})
    if isinstance(final_receipt, dict) and final_receipt.get("verdict") == "accepted" and not final_acceptance_passes(payload):
        final_receipt["verdict"] = "stale"


def derive_state(payload: dict[str, Any], base_dir: Path | None) -> str:
    if not completion_gaps(payload, base_dir):
        return "complete"
    if not machine_completion_gaps(payload, base_dir):
        return "machine_complete"
    current_hash = payload.get("content_sha256")
    jobs = [job for job in payload.get("jobs", []) if isinstance(job, dict) and job.get("input_sha256") == current_hash]
    if any(job.get("status") == "blocked" for job in jobs):
        return "blocked"
    if any(job.get("status") in {"queued", "running"} for job in jobs):
        return "running"
    results = [result for result in payload.get("results", []) if isinstance(result, dict) and result.get("input_sha256") == current_hash]
    master = payload.get("master", {})
    receipt = payload.get("qc_receipt", {})
    broken_evidence = (
        any(job.get("status") == "failed" for job in jobs)
        or any(result.get("review") == "rejected" for result in results)
        or (isinstance(receipt, dict) and receipt.get("verdict") == "block")
        or (isinstance(master, dict) and master.get("status") == "machine_complete" and not master_is_ready(payload, base_dir))
        or any(result.get("review") in {"machine_complete", "accepted"} and not result_is_machine_complete(result, payload, base_dir) for result in results)
    )
    if broken_evidence:
        return "needs_revision"
    return "ready" if not authoring_gaps(payload, base_dir) else "draft"


def refresh_document(payload: dict[str, Any], base_dir: Path | None = None) -> bool:
    """Recompute the one authoring hash, invalidate stale evidence, and derive the one state."""
    expected = content_sha256(payload)
    previous = payload.get("content_sha256")
    authoring_changed = previous != expected
    payload["content_sha256"] = expected
    if authoring_changed:
        _invalidate_runtime(payload)
    _invalidate_mismatched_runtime(payload, base_dir)
    payload["completion"] = {"definition": COMPLETION_DEFINITION}
    payload["state"] = derive_state(payload, base_dir)
    return authoring_changed


def _migrate_legacy_runtime(payload: dict[str, Any], source_schema: str) -> None:
    """Keep old bytes/jobs recoverable while refusing legacy acceptance as human proof."""
    for asset in payload.get("assets", []):
        if not isinstance(asset, dict):
            continue
        if asset.get("status") == "accepted":
            asset["legacy_acceptance_receipt"] = asset.get("acceptance_receipt", {})
            asset["status"] = "machine_complete"
        asset["acceptance_receipt"] = normalize_acceptance_receipt(None)
    for result in payload.get("results", []):
        if not isinstance(result, dict):
            continue
        old = result.get("acceptance_receipt", {})
        if result.get("review") == "accepted":
            result["legacy_acceptance_receipt"] = old
            migrated_machine = {
                "reviewer_kind": old.get("reviewer_kind", ""),
                "verdict": "pass" if old.get("verdict") == "accepted" else "pending",
                "content_sha256": old.get("content_sha256", ""),
                "output_sha256": old.get("output_sha256", ""),
                "checks": old.get("criteria", []),
                "blocks": old.get("blocks", []),
                "completed_at": old.get("reviewed_at", ""),
            }
            result["machine_receipt"] = normalize_machine_receipt(migrated_machine)
            result["review"] = "machine_complete"
        result["acceptance_receipt"] = normalize_acceptance_receipt(None)
    payload["final_acceptance_receipt"] = normalize_final_acceptance_receipt(None)
    payload["migration"] = {
        "source_schema": source_schema or "unknown",
        "human_acceptance_reconfirmation_required": True,
        "legacy_evidence_preserved": True,
    }


def build(raw: dict[str, Any], base_dir: Path | None = None) -> dict[str, Any]:
    incoming_schema = raw.get("schema")
    current = incoming_schema == SCHEMA and raw.get("skill") in {None, SKILL}
    legacy = incoming_schema in LEGACY_SCHEMAS or raw.get("skill") in LEGACY_SKILLS
    runtime_compatible = current or legacy
    seen_shots: set[str] = set()
    seen_assets: set[str] = set()
    raw_shots = raw.get("shots", []) if isinstance(raw.get("shots"), list) else []
    raw_assets = raw.get("assets", []) if isinstance(raw.get("assets"), list) else []
    policy = _clean_text(raw.get("acceptance_policy") or raw.get("acceptancePolicy"), "delegated")
    if policy not in ACCEPTANCE_POLICIES:
        policy = "delegated"
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "skill": SKILL,
        "title": _clean_text(raw.get("title"), "未命名故事脚本"),
        "global_style": _clean_text(raw.get("global_style") or raw.get("globalStyle"), "电影级画面，主体一致，细节清晰"),
        "acceptance_policy": policy,
        "delivery_spec": normalize_delivery_spec(raw.get("delivery_spec") or raw.get("deliverySpec")),
        "shots": [normalize_shot(item, index, seen_shots) for index, item in enumerate(raw_shots, 1) if isinstance(item, dict)],
        "assets": [normalize_asset(item, index, seen_assets) for index, item in enumerate(raw_assets, 1) if isinstance(item, dict)],
        "content_sha256": _clean_text(raw.get("content_sha256")).lower() if runtime_compatible else "",
        "state": _clean_text(raw.get("state"), "draft") if current else "draft",
        "jobs": [normalize_job(item, index) for index, item in enumerate(raw.get("jobs", []), 1) if runtime_compatible and isinstance(item, dict)],
        "results": [normalize_result(item, index) for index, item in enumerate(raw.get("results", []), 1) if runtime_compatible and isinstance(item, dict)],
        "master": normalize_master(raw.get("master") if runtime_compatible else None),
        "qc_receipt": normalize_qc_receipt(raw.get("qc_receipt") if runtime_compatible else None),
        "final_acceptance_receipt": normalize_final_acceptance_receipt(raw.get("final_acceptance_receipt") if current else None),
        "completion": {"definition": COMPLETION_DEFINITION},
    }
    if legacy:
        _migrate_legacy_runtime(payload, _clean_text(incoming_schema))
    refresh_document(payload, base_dir)
    return payload


def compose_prompt(style: str, shot: dict[str, Any]) -> str:
    parts = [style, f"{shot['scale']}，{shot['visual']}", f"光影氛围：{shot['lighting']}。"]
    if _clean_text(shot.get("dialogue")):
        parts.append(f"对白与旁白：{shot['dialogue']}。")
    parts.extend((f"音效：{shot['sound']}。", f"运镜：{shot['camera']}。", "主体一致，细节清晰，电影级构图。"))
    return " ".join(part.strip() for part in parts if part.strip())


def compose_document(payload: dict[str, Any], base_dir: Path | None = None) -> bool:
    for shot in payload.get("shots", []):
        if isinstance(shot, dict):
            shot["final_prompt"] = compose_prompt(str(payload.get("global_style", "")), shot)
    return refresh_document(payload, base_dir)


def validate(payload: dict[str, Any], base_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema 必须为 {SCHEMA}")
    if payload.get("skill") != SKILL:
        errors.append(f"skill 必须为 {SKILL}")
    if payload.get("state") not in WORKFLOW_STATES:
        errors.append("state 无效")
    if payload.get("acceptance_policy") not in ACCEPTANCE_POLICIES:
        errors.append("acceptance_policy 无效")
    if not _clean_text(payload.get("title")):
        errors.append("title 不能为空")
    if not _clean_text(payload.get("global_style")):
        errors.append("global_style 不能为空")
    delivery = payload.get("delivery_spec")
    if not isinstance(delivery, dict):
        errors.append("delivery_spec 必须是 object")
    else:
        for field in ("container", "mime_type", "aspect_ratio", "resolution"):
            if not _clean_text(delivery.get(field)):
                errors.append(f"delivery_spec.{field} 不能为空")
        if not isinstance(delivery.get("require_audio"), bool):
            errors.append("delivery_spec.require_audio 必须是 boolean")
    shots = payload.get("shots")
    if not isinstance(shots, list) or not shots:
        errors.append("shots 至少需要一个镜头")
    else:
        seen: set[str] = set()
        for index, shot in enumerate(shots, 1):
            if not isinstance(shot, dict):
                errors.append(f"shots[{index}] 必须是 object")
                continue
            for field in SHOT_FIELDS:
                if field not in shot:
                    errors.append(f"shots[{index}].{field} 缺失")
            for field in SHOT_REQUIRED_TEXT_FIELDS:
                if not _clean_text(shot.get(field)):
                    errors.append(f"shots[{index}].{field} 缺失")
            shot_id = _clean_text(shot.get("id"))
            if shot_id in seen:
                errors.append(f"shots[{index}].id 重复")
            seen.add(shot_id)
            try:
                duration = float(shot.get("duration", 0))
                if not math.isfinite(duration) or duration < 5 or duration > 15:
                    errors.append(f"shots[{index}].duration 必须在 5–15 秒之间")
            except (TypeError, ValueError):
                errors.append(f"shots[{index}].duration 必须是数字")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        errors.append("assets 必须是 array")
    else:
        seen_assets: set[str] = set()
        for index, asset in enumerate(assets, 1):
            if not isinstance(asset, dict):
                errors.append(f"assets[{index}] 必须是 object")
                continue
            for field in ASSET_FIELDS:
                if field not in asset:
                    errors.append(f"assets[{index}].{field} 缺失")
            asset_id = _clean_text(asset.get("id"))
            if not asset_id or not _clean_text(asset.get("name")):
                errors.append(f"assets[{index}].id/name 缺失")
            if asset_id in seen_assets:
                errors.append(f"assets[{index}].id 重复")
            seen_assets.add(asset_id)
            if asset.get("kind") not in ASSET_KINDS:
                errors.append(f"assets[{index}].kind 无效")
            if asset.get("status") not in ASSET_STATES:
                errors.append(f"assets[{index}].status 无效")
            if asset.get("source") not in ASSET_SOURCES:
                errors.append(f"assets[{index}].source 无效")
            if asset.get("status") in {"machine_complete", "accepted"} and not has_real_asset_source(asset, base_dir):
                errors.append(f"assets[{index}] machine_complete 时必须绑定真实来源与当前内容 SHA-256")
            if asset.get("status") == "accepted" and not asset_is_accepted(asset, payload, base_dir):
                errors.append(f"assets[{index}] accepted 必须有具名真人、带时区、绑定当前图片字节 SHA 的回执")
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        errors.append("jobs 必须是 array")
    else:
        seen_jobs: set[str] = set()
        for index, job in enumerate(jobs, 1):
            if not isinstance(job, dict):
                errors.append(f"jobs[{index}] 必须是 object")
                continue
            job_id = _clean_text(job.get("id"))
            if not job_id or job_id in seen_jobs:
                errors.append(f"jobs[{index}].id 缺失或重复")
            seen_jobs.add(job_id)
            if job.get("kind") not in JOB_KINDS or job.get("status") not in JOB_STATES:
                errors.append(f"jobs[{index}].kind/status 无效")
            if not is_sha256(job.get("input_sha256")):
                errors.append(f"jobs[{index}].input_sha256 无效")
    results = payload.get("results")
    if not isinstance(results, list):
        errors.append("results 必须是 array")
    else:
        for index, result in enumerate(results, 1):
            if not isinstance(result, dict):
                errors.append(f"results[{index}] 必须是 object")
                continue
            if result.get("kind") != "shot_video" or result.get("review") not in RESULT_REVIEWS:
                errors.append(f"results[{index}].kind/review 无效")
            if not _clean_text(result.get("shot_id")) or not is_sha256(result.get("input_sha256")):
                errors.append(f"results[{index}] 必须绑定 shot_id 与 input_sha256")
            if result.get("review") == "accepted" and not result_is_accepted(result, payload, base_dir):
                errors.append(f"results[{index}] accepted 必须有有效机器证据和具名真人当前字节回执")
            elif result.get("review") == "machine_complete" and not result_is_machine_complete(result, payload, base_dir):
                errors.append(f"results[{index}] machine_complete 必须绑定当前真实文件 SHA 与机器检查回执")
    master = payload.get("master")
    if not isinstance(master, dict) or master.get("status") not in MASTER_STATES:
        errors.append("master.status 无效")
    elif master.get("status") == "machine_complete" and not master_is_ready(payload, base_dir):
        errors.append("master machine_complete 时必须绑定当前内容哈希与真实字节 SHA")
    receipt = payload.get("qc_receipt")
    if not isinstance(receipt, dict) or receipt.get("verdict") not in QC_VERDICTS:
        errors.append("qc_receipt.verdict 无效")
    elif receipt.get("verdict") == "pass" and not qc_receipt_passes(payload, base_dir):
        errors.append("qc_receipt pass 时必须双绑当前内容与母版 SHA、列出 checks、无 block，且 receipt_path 的当前文件字节必须匹配 receipt_sha256")
    final_receipt = payload.get("final_acceptance_receipt")
    if not isinstance(final_receipt, dict):
        errors.append("final_acceptance_receipt 必须是 object")
    elif final_receipt.get("verdict") == "accepted" and not final_acceptance_passes(payload):
        errors.append("final_acceptance_receipt accepted 必须由具名真人显式绑定当前母版字节 SHA")
    completion = payload.get("completion")
    if not isinstance(completion, dict) or completion.get("definition") != COMPLETION_DEFINITION:
        errors.append(f"completion.definition 必须为 {COMPLETION_DEFINITION}")
    expected_hash = content_sha256(payload)
    if payload.get("content_sha256") != expected_hash:
        errors.append("content_sha256 与规范化 authoring 内容不一致")
    expected_state = derive_state(payload, base_dir)
    if payload.get("state") != expected_state:
        errors.append(f"state 与唯一完成定义不一致，应为 {expected_state}")
    if payload.get("state") == "complete" and completion_gaps(payload, base_dir):
        errors.append("complete 不满足唯一完成谓词")
    return errors


def load_document(path: Path) -> tuple[dict[str, Any], bool, bool]:
    raw = read_json(path)
    migrated = raw.get("schema") in LEGACY_SCHEMAS or raw.get("skill") in LEGACY_SKILLS
    data = build(raw, path.parent)
    refreshed = migrated or data != raw
    return data, migrated, refreshed


def status_payload(data: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    gaps = completion_gaps(data, base_dir)
    return {
        "state": data.get("state"),
        "content_sha256": data.get("content_sha256"),
        "machine_complete": not machine_completion_gaps(data, base_dir),
        "complete": not gaps,
        "completion_definition": COMPLETION_DEFINITION,
        "shots": len(data.get("shots", [])),
        "assets": len(data.get("assets", [])),
        "jobs": len(data.get("jobs", [])),
        "results": len(data.get("results", [])),
        "gaps": gaps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="归一化输入并创建或迁移 v3 工作台 JSON")
    init_parser.add_argument("--input", type=Path, required=True)
    init_parser.add_argument("--output", type=Path, required=True)
    compose_parser = subparsers.add_parser("compose", help="合成全部最终提示词并使旧运行证据失效")
    compose_parser.add_argument("path", type=Path)
    compose_parser.add_argument("--write", action="store_true")
    validate_parser = subparsers.add_parser("validate", help="迁移/刷新后验证 v3 工作台")
    validate_parser.add_argument("path", type=Path)
    status_parser = subparsers.add_parser("status", help="刷新并报告唯一状态、哈希和完成缺口")
    status_parser.add_argument("path", type=Path)
    status_parser.add_argument("--write", action="store_true")
    complete_parser = subparsers.add_parser("complete", help="按唯一完成谓词验收，不制造完成证据")
    complete_parser.add_argument("path", type=Path)
    complete_parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if args.command == "init":
        raw = read_json(args.input)
        migrated = raw.get("schema") in LEGACY_SCHEMAS or raw.get("skill") in LEGACY_SKILLS
        payload = build(raw, args.output.parent)
        errors = validate(payload, args.output.parent)
        if errors:
            print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 1
        write_json(args.output, payload)
        print(json.dumps({"ok": True, "output": str(args.output), "migrated": migrated, **status_payload(payload, args.output.parent)}, ensure_ascii=False))
        return 0

    payload, migrated, refreshed = load_document(args.path)
    if args.command == "compose":
        refreshed = compose_document(payload, args.path.parent) or refreshed
    else:
        refreshed = refresh_document(payload, args.path.parent) or refreshed
    errors = validate(payload, args.path.parent)
    if getattr(args, "write", False) and not errors:
        write_json(args.path, payload)

    if args.command == "compose":
        if errors:
            print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 1
        if args.write:
            print(json.dumps({"ok": True, "migrated": migrated, "refreshed": refreshed, **status_payload(payload, args.path.parent)}, ensure_ascii=False))
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    summary = status_payload(payload, args.path.parent)
    response = {"ok": not errors, "migrated": migrated, "refreshed": refreshed, "errors": errors, **summary}
    print(json.dumps(response, ensure_ascii=False, indent=2))
    if args.command == "complete":
        return 0 if not errors and summary["complete"] else 1
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
