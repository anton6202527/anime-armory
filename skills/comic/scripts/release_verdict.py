#!/usr/bin/env python3
"""Build a SHA-bound comic delivery/release verdict.

Technical completion, production review and public/commercial release are kept
as separate states.  The script only reports and writes evidence; it never
publishes or changes ``_进度.md``.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


COMIC_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from contracts import sha256_file, stable_sha256, stage_inputs_fingerprint  # noqa: E402
from platform_profiles import profile_for_platform, validate_manifest  # noqa: E402
from settings import get_setting  # noqa: E402


PROFILES = ("internal", "digital", "print", "commercial")
PUBLIC_PROFILES = ("digital", "print", "commercial")
RIGHTS_CLEARED_VALUES = {
    "authorized",
    "cleared",
    "generated_original",
    "licensed",
    "not_applicable",
    "open_license",
    "original",
    "owned",
    "public_domain",
    "self_created",
    "self_owned",
    "不适用",
    "公共领域",
    "公版",
    "原创",
    "已授权",
    "已清权",
    "开源许可",
    "自制",
    "自有",
}


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def issue(code: str, reason: str, *, domain: str, blocking_profiles: tuple[str, ...] = PROFILES) -> dict[str, Any]:
    return {
        "code": code,
        "reason": reason,
        "domain": domain,
        "blocking_profiles": list(blocking_profiles),
    }


def rights_value_is_cleared(value: Any) -> bool:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized in RIGHTS_CLEARED_VALUES


def normalize_image_format(value: Any) -> str:
    normalized = str(value or "").strip().lower().lstrip(".")
    return {"jpeg": "jpg", "tiff": "tif"}.get(normalized, normalized)


def _manifest_artifact_path(root: Path, raw_path: Any) -> tuple[Path | None, str]:
    value = str(raw_path or "").strip()
    if not value:
        return None, ""
    root_resolved = root.resolve()
    candidate = Path(value).expanduser()
    candidate = candidate.resolve() if candidate.is_absolute() else (root_resolved / candidate).resolve()
    try:
        relative = candidate.relative_to(root_resolved)
    except ValueError:
        return None, value
    return candidate, str(relative)


def rendered_artifacts(root: Path, manifest: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    artifacts_by_path: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    try:
        from PIL import Image
    except ImportError:
        Image = None

    failed_paths: set[str] = set()
    for section in ("pages", "rendered"):
        entries = manifest.get(section) or []
        if not isinstance(entries, list):
            issues.append(issue("export_artifact_list_invalid", f"manifest.{section} 必须是数组。", domain="technical"))
            continue
        for index, item in enumerate(entries):
            if not isinstance(item, Mapping) or not str(item.get("path") or "").strip():
                issues.append(
                    issue(
                        "export_artifact_entry_invalid",
                        f"manifest.{section}[{index}] 缺有效 path。",
                        domain="technical",
                    )
                )
                continue
            path, relative = _manifest_artifact_path(root, item.get("path"))
            if path is None:
                issues.append(
                    issue(
                        "export_artifact_outside_project",
                        f"manifest.{section}[{index}] 路径不在作品根内：{item.get('path')}",
                        domain="technical",
                    )
                )
                continue
            if not path.is_file():
                issues.append(issue("rendered_artifact_missing", relative, domain="technical"))
                continue

            artifact = artifacts_by_path.get(relative)
            if artifact is None and relative not in failed_paths:
                if Image is None:
                    issues.append(
                        issue(
                            "image_decoder_unavailable",
                            "缺 Pillow，无法证明最终图片可完整解码。",
                            domain="technical",
                        )
                    )
                    failed_paths.add(relative)
                    continue
                try:
                    with Image.open(path) as image:
                        detected_format = normalize_image_format(image.format)
                        image.load()
                        actual_size = {"width": int(image.width), "height": int(image.height)}
                except (OSError, ValueError, SyntaxError) as exc:
                    issues.append(
                        issue(
                            "export_artifact_decode_failed",
                            f"{relative} 不是可完整解码的图片：{exc}",
                            domain="technical",
                        )
                    )
                    failed_paths.add(relative)
                    continue
                if not detected_format:
                    issues.append(
                        issue(
                            "export_artifact_format_unknown",
                            f"{relative} 无法识别实际图片格式。",
                            domain="technical",
                        )
                    )
                    failed_paths.add(relative)
                    continue
                artifact = {
                    "path": relative,
                    "sha256": sha256_file(path),
                    "size": path.stat().st_size,
                    "dimensions": actual_size,
                    "format": detected_format,
                    "manifest_sections": [],
                }
                artifacts_by_path[relative] = artifact
            if artifact is None:
                continue
            if section not in artifact["manifest_sections"]:
                artifact["manifest_sections"].append(section)

            declared_size = item.get("size")
            if declared_size is not None and not isinstance(declared_size, Mapping):
                issues.append(
                    issue(
                        "export_artifact_dimensions_invalid",
                        f"{relative} 的 manifest size 必须是 width/height 对象。",
                        domain="technical",
                    )
                )
            elif isinstance(declared_size, Mapping):
                for axis in ("width", "height"):
                    if declared_size.get(axis) in (None, ""):
                        continue
                    try:
                        expected = int(declared_size[axis])
                    except (TypeError, ValueError):
                        issues.append(
                            issue(
                                "export_artifact_dimensions_invalid",
                                f"{relative} 的 manifest {axis} 不是有效整数。",
                                domain="technical",
                            )
                        )
                        continue
                    actual = int(artifact["dimensions"][axis])
                    if expected != actual:
                        issues.append(
                            issue(
                                "export_artifact_dimensions_mismatch",
                                f"{relative} manifest {axis}={expected}，实际为 {actual}。",
                                domain="technical",
                            )
                        )

            declared_format = normalize_image_format(item.get("format"))
            if declared_format and declared_format != artifact["format"]:
                issues.append(
                    issue(
                        "export_artifact_format_mismatch",
                        f"{relative} manifest format={declared_format}，实际为 {artifact['format']}。",
                        domain="technical",
                    )
                )
    return list(artifacts_by_path.values()), issues


def platform_release_checks(
    root: Path,
    manifest: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    """Recheck the current target platform from verified image facts.

    Compose-time findings may have been generated under a draft/demo usage or
    an earlier target platform.  Release therefore recompiles the profile with
    publish-like severity and replaces declared dimensions/formats with facts
    obtained from decoding the current files.
    """
    target_platform = get_setting(str(root), "目标平台", str(manifest.get("target_platform") or "通用"))
    platform_profile = profile_for_platform(target_platform)
    verified = dict(manifest)
    artifact_map = {str(item.get("path") or ""): item for item in artifacts}
    for section in ("pages", "rendered"):
        verified_items: list[dict[str, Any]] = []
        entries = manifest.get(section) or []
        if not isinstance(entries, list):
            entries = []
        for item in entries:
            if not isinstance(item, Mapping):
                continue
            normalized = dict(item)
            _path, relative = _manifest_artifact_path(root, item.get("path"))
            artifact = artifact_map.get(relative)
            if artifact:
                normalized["size"] = dict(artifact.get("dimensions") or {})
                normalized["format"] = str(artifact.get("format") or "")
                normalized["path"] = relative
            verified_items.append(normalized)
        verified[section] = verified_items

    findings = validate_manifest(root, verified, platform_profile, usage="发布候选")
    findings_as_issues: list[dict[str, Any]] = []
    for finding in findings:
        blocking = PUBLIC_PROFILES if str(finding.get("severity") or "").lower() == "block" else ()
        reason = str(finding.get("reason") or "")
        suggested_fix = str(finding.get("suggested_fix") or "").strip()
        if suggested_fix:
            reason = f"{reason} 修复：{suggested_fix}"
        findings_as_issues.append(
            issue(
                str(finding.get("code") or "platform_profile"),
                reason,
                domain="platform",
                blocking_profiles=blocking,
            )
        )
    return findings_as_issues, target_platform, platform_profile.to_manifest()


def check_review_receipt(root: Path, chapter: str) -> list[dict[str, Any]]:
    receipt_path = root / "生产数据" / "gate_receipts" / f"review_{chapter}.json"
    receipt = load_json(receipt_path, {})
    if not isinstance(receipt, Mapping) or not receipt:
        return [issue("review_gate_receipt_missing", "缺当前 review gate receipt。", domain="production")]
    current = stage_inputs_fingerprint(root, chapter, "review")
    if (
        receipt.get("kind") != "comic_gate_receipt"
        or receipt.get("stage") != "review"
        or receipt.get("chapter") != chapter
        or receipt.get("execution_authorized") is not True
    ):
        return [issue("review_gate_receipt_invalid", "review receipt 的 kind/stage/chapter 或执行授权无效。", domain="production")]
    if receipt.get("inputs_fingerprint_sha256") != current.get("sha256"):
        return [issue("review_gate_receipt_stale", "review 后输入已变化，旧 gate receipt 失效。", domain="production")]
    report_path = root / str(receipt.get("report_path") or "")
    if not report_path.is_file():
        return [issue("review_gate_report_missing", "review receipt 指向的报告缺失。", domain="production")]
    if str(receipt.get("report_sha256") or "") != sha256_file(report_path):
        return [issue("review_gate_report_stale", "review gate 报告与 receipt SHA 不一致。", domain="production")]
    report = load_json(report_path, {})
    report_inputs = report.get("inputs_fingerprint") if isinstance(report, Mapping) and isinstance(report.get("inputs_fingerprint"), Mapping) else {}
    if (
        not isinstance(report, Mapping)
        or report.get("kind") != "comic_gate"
        or report.get("stage") != "review"
        or report.get("chapter") != chapter
        or report.get("verdict") != receipt.get("verdict")
        or report_inputs.get("sha256") != current.get("sha256")
        or report_inputs.get("sha256") != receipt.get("inputs_fingerprint_sha256")
    ):
        return [issue("review_gate_report_invalid", "review gate 报告合同、verdict 或输入指纹与 receipt 不一致。", domain="production")]
    # Don't trust the recorded verdict: recompute it from the findings' own
    # severities.  A hand-edit that flips verdict block→warn while leaving
    # block-severity findings in place (and re-hashing report_sha256, which the
    # gate report file is not itself part of the review fingerprint) would
    # otherwise pass every check above and release the chapter.
    report_findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    recomputed_verdict = (
        "block" if any(isinstance(f, Mapping) and f.get("severity") == "block" for f in report_findings)
        else "warn" if any(isinstance(f, Mapping) and f.get("severity") == "warn" for f in report_findings)
        else "pass"
    )
    if recomputed_verdict != report.get("verdict"):
        return [issue(
            "review_gate_report_verdict_tampered",
            f"review gate 报告 verdict={report.get('verdict')!r} 与其 findings 严重度重算值 {recomputed_verdict!r} 不一致（疑似手改绕过 block）。",
            domain="production",
        )]
    # Recompute the receipt_id over the same material the gate signs, so tampering
    # with findings content (not just the verdict field) is caught.
    recorded_receipt_id = str(report.get("receipt_id") or "")
    if recorded_receipt_id:
        expected_receipt_id = stable_sha256({
            "project_root": ".",
            "chapter": chapter,
            "stage": "review",
            "inputs": report_inputs.get("sha256"),
            "verdict": report.get("verdict"),
            "findings": report_findings,
        })
        if recorded_receipt_id != expected_receipt_id:
            return [issue(
                "review_gate_receipt_id_mismatch",
                "review gate receipt_id 与报告内容重算值不一致（findings/verdict/输入被改动过）。",
                domain="production",
            )]
    if recomputed_verdict == "block" or receipt.get("verdict") == "block":
        return [issue("review_gate_blocked", "review gate 仍有 block。", domain="production")]
    return []


def review_gate_summary(root: Path, chapter: str) -> dict[str, Any]:
    """机检真相摘要：verdict + 计数 + 有效豁免清单，嵌进发布裁决供叙事对账。

    背景：历史上 review gate 实为 warn（如 0 block/133 warn）而 `_进度.md`
    叙事写「pass」，完成度表述比机检结论乐观。发布裁决是叙事的上游证据，
    必须原样携带机检结论；任何「内部验收通过」的表述都应引用本区块。
    """
    receipt = load_json(root / "生产数据" / "gate_receipts" / f"review_{chapter}.json", {})
    report = load_json(root / "生产数据" / f"comic_gate_review_{chapter}.json", {})
    counts = {}
    report_summary = report.get("summary") if isinstance(report, Mapping) and isinstance(report.get("summary"), Mapping) else {}
    for key in ("block_count", "warn_count", "info_count"):
        value = report_summary.get(key)
        if isinstance(value, int):
            counts[key] = value
    waivers = []
    waiver_dir = root / "生产数据" / "gate_waivers"
    if waiver_dir.is_dir():
        for path in sorted(waiver_dir.glob(f"*{chapter}_latest.json")):
            payload = load_json(path, {})
            if isinstance(payload, Mapping):
                waivers.append(
                    {
                        "path": str(path.relative_to(root)),
                        "stage": str(payload.get("stage") or ""),
                        "reason": str(payload.get("reason") or ""),
                        "created_at": str(payload.get("created_at") or ""),
                    }
                )
    return {
        "receipt_verdict": str(receipt.get("verdict") or "missing") if isinstance(receipt, Mapping) else "missing",
        "counts": counts,
        "waivers": waivers,
    }


def vlm_adjudication_summary(root: Path, chapter: str) -> dict[str, Any]:
    """VLM 三轴（角色/生物身份、背景、道具）裁决覆盖摘要。

    2026-07 实证：两话 103 条任务 0 裁决仍以 internal profile 放行——
    「画错生物形态」类漂移全程无人拦。gate 只 warn（advisory 哲学），
    闭环必须在发布裁决收口（strict 档拒空壳的通用模式）。
    只统计 SHA 仍然有效的裁决：重抽过的格旧裁决不算数。
    """
    tasks_payload = load_json(root / "生产数据" / f"comic_vlm_judge_tasks_{chapter}.json", {})
    tasks = tasks_payload.get("tasks") if isinstance(tasks_payload, Mapping) else None
    tasks = [task for task in tasks or [] if isinstance(task, Mapping)]
    expected = {
        str(task.get("task_id")): str((task.get("panel") or {}).get("sha256") or "")
        for task in tasks
        if task.get("task_id")
    }
    verdict_payload = load_json(root / "生产数据" / f"comic_vlm_judge_verdicts_{chapter}.json", {})
    records = verdict_payload.get("verdicts") if isinstance(verdict_payload, Mapping) else None
    adjudicated: dict[str, str] = {}
    for record in records or []:
        if not isinstance(record, Mapping):
            continue
        task_id = str(record.get("task_id") or "")
        if task_id not in expected:
            continue
        if str(record.get("panel_sha256") or "") != expected[task_id]:
            continue  # 该格已重抽，旧裁决作废
        verdict = str(record.get("verdict") or "")
        if verdict in {"pass", "suspect"}:
            adjudicated[task_id] = verdict
    open_suspects = sorted(tid for tid, verdict in adjudicated.items() if verdict == "suspect")
    return {
        "tasks_file_present": bool(tasks_payload),
        "total": len(expected),
        "adjudicated": len(adjudicated),
        "open_suspects": open_suspects,
    }


def check_vlm_adjudication(root: Path, chapter: str, summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    total = int(summary.get("total") or 0)
    adjudicated = int(summary.get("adjudicated") or 0)
    open_suspects = list(summary.get("open_suspects") or [])
    if not summary.get("tasks_file_present"):
        if (root / "生产数据" / f"comic_character_consistency_{chapter}.json").is_file():
            issues.append(issue(
                "vlm_tasks_missing",
                "角色一致性报告存在但 VLM 并排判定任务包缺失——身份三轴机检未建立，不能声称完成生产验收。",
                domain="production",
            ))
        return issues
    if total > 0 and adjudicated == 0:
        issues.append(issue(
            "vlm_adjudication_missing",
            f"VLM 并排判定任务包 {total} 条、有效裁决 0 条——角色/生物身份、背景、道具三轴机检空转，"
            "画错生物形态这类漂移不会被拦。先用 vlm_adjudicate.py queue/submit 完成裁决。",
            domain="production",
        ))
    elif total > 0 and adjudicated < total:
        issues.append(issue(
            "vlm_adjudication_partial",
            f"VLM 裁决覆盖不完整：{adjudicated}/{total}（重抽过的格需重建任务包后再裁决）。",
            domain="release",
            blocking_profiles=PUBLIC_PROFILES,
        ))
    if open_suspects:
        issues.append(issue(
            "vlm_suspect_unresolved",
            f"VLM 裁决存在未处置的 suspect {len(open_suspects)} 条（{', '.join(open_suspects[:6])}"
            f"{' …' if len(open_suspects) > 6 else ''}）——确认漂移的格必须重抽并重新裁决，或书面豁免。",
            domain="release",
            blocking_profiles=PUBLIC_PROFILES,
        ))
    return issues


def review_receipt_binding(root: Path, chapter: str) -> dict[str, str]:
    path = root / "生产数据" / "gate_receipts" / f"review_{chapter}.json"
    receipt = load_json(path, {})
    if not isinstance(receipt, Mapping) or not path.is_file():
        return {}
    return {
        "path": str(path.relative_to(root)),
        "sha256": sha256_file(path),
        "receipt_id": str(receipt.get("receipt_id") or ""),
        "report_sha256": str(receipt.get("report_sha256") or ""),
    }


def check_acceptance(root: Path, chapter: str, artifacts: list[dict[str, Any]], profile: str) -> list[dict[str, Any]]:
    path = root / "生产数据" / f"release_acceptance_{chapter}.json"
    acceptance = load_json(path, {})
    if not isinstance(acceptance, Mapping) or not acceptance:
        return [
            issue(
                "release_acceptance_missing",
                "发布候选缺 SHA 绑定的人工签收。",
                domain="release",
                blocking_profiles=("digital", "print", "commercial"),
            )
        ]
    if str(acceptance.get("status") or "").lower() not in {"approved", "accepted", "pass"}:
        return [issue("release_acceptance_not_approved", "人工发布签收未批准。", domain="release", blocking_profiles=("digital", "print", "commercial"))]
    if (
        not str(acceptance.get("reviewer") or "").strip()
        or not str(acceptance.get("approved_at") or "").strip()
        or not str(acceptance.get("reason") or "").strip()
    ):
        return [issue("release_acceptance_identity_missing", "发布签收缺 reviewer/approved_at/reason。", domain="release", blocking_profiles=("digital", "print", "commercial"))]
    if str(acceptance.get("profile") or "") != profile:
        return [issue(
            "release_acceptance_profile_mismatch",
            f"发布签收 profile={acceptance.get('profile') or 'missing'}，不能授权当前 {profile} 交付。",
            domain="release",
            blocking_profiles=("digital", "print", "commercial"),
        )]
    recorded = acceptance.get("artifacts")
    recorded_map = {
        str(item.get("path")): str(item.get("sha256"))
        for item in recorded or []
        if isinstance(item, Mapping) and item.get("path") and item.get("sha256")
    }
    current_map = {item["path"]: item["sha256"] for item in artifacts}
    if not recorded_map or recorded_map != current_map:
        return [issue("release_acceptance_stale", "发布签收没有精确绑定当前全部导出物 SHA。", domain="release", blocking_profiles=("digital", "print", "commercial"))]
    recorded_review = acceptance.get("review_receipt") if isinstance(acceptance.get("review_receipt"), Mapping) else {}
    if dict(recorded_review) != review_receipt_binding(root, chapter):
        return [issue("release_acceptance_review_stale", "发布签收未精确绑定当前 review gate receipt。", domain="release", blocking_profiles=("digital", "print", "commercial"))]
    return []


def create_acceptance(
    root: Path,
    chapter: str,
    profile: str,
    *,
    reviewer: str,
    reason: str,
) -> Path:
    if profile == "internal":
        raise ValueError("internal profile does not need a public release acceptance")
    if not reviewer.strip() or not reason.strip():
        raise ValueError("--reviewer and --reason are required")
    preflight = build(root, chapter, profile)
    acceptance_codes = {
        "release_acceptance_missing",
        "release_acceptance_not_approved",
        "release_acceptance_identity_missing",
        "release_acceptance_profile_mismatch",
        "release_acceptance_stale",
        "release_acceptance_review_stale",
    }
    blockers = [
        item for item in preflight["issues"]
        if profile in item["blocking_profiles"] and item["code"] not in acceptance_codes
    ]
    if blockers:
        raise ValueError("release preflight blocked: " + ",".join(item["code"] for item in blockers))
    receipt = review_receipt_binding(root, chapter)
    if not receipt:
        raise ValueError("current review receipt missing")
    payload = {
        "schema_version": 1,
        "kind": "comic_release_acceptance",
        "status": "approved",
        "chapter": chapter,
        "profile": profile,
        "reviewer": reviewer.strip(),
        "reason": reason.strip(),
        "approved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "artifacts": preflight["artifacts"],
        "review_receipt": receipt,
    }
    path = root / "生产数据" / f"release_acceptance_{chapter}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build(root: Path, chapter: str, profile: str) -> dict[str, Any]:
    manifest_path = root / "排版" / chapter / "export_manifest.json"
    manifest = load_json(manifest_path, {})
    issues: list[dict[str, Any]] = []
    if not isinstance(manifest, Mapping) or not manifest:
        issues.append(issue("export_manifest_missing", "缺 export_manifest.json。", domain="technical"))
        artifacts: list[dict[str, Any]] = []
    else:
        artifacts, artifact_issues = rendered_artifacts(root, manifest)
        issues.extend(artifact_issues)
        if manifest.get("missing_panels"):
            issues.append(issue("manifest_missing_panels", "manifest 仍列出缺图。", domain="technical"))
        if manifest.get("render_error"):
            issues.append(issue("manifest_render_error", str(manifest.get("render_error")), domain="technical"))
        if not artifacts:
            issues.append(issue("rendered_artifacts_empty", "没有已落盘的最终导出物。", domain="technical"))

    platform_issues, target_platform, platform_profile = platform_release_checks(
        root,
        manifest if isinstance(manifest, Mapping) else {},
        artifacts,
    )
    issues.extend(platform_issues)

    issues.extend(check_review_receipt(root, chapter))
    adjudication = vlm_adjudication_summary(root, chapter)
    issues.extend(check_vlm_adjudication(root, chapter, adjudication))
    issues.extend(check_acceptance(root, chapter, artifacts, profile))

    meta = load_json(root / "_meta.json", {})
    rights = meta.get("rights") if isinstance(meta, Mapping) and isinstance(meta.get("rights"), Mapping) else {}
    for key in ("source_status", "font_status", "asset_status"):
        if not rights_value_is_cleared(rights.get(key)):
            issues.append(
                issue(
                    f"{key}_unverified",
                    f"{key}={rights.get(key) or 'missing'}；公开/印刷/商用交付必须显式声明原创、自有、公版、已授权、开源许可或不适用。",
                    domain="rights",
                    blocking_profiles=("digital", "print", "commercial"),
                )
            )

    technical_blocks = [item for item in issues if item["domain"] == "technical"]
    production_blocks = [item for item in issues if item["domain"] in {"technical", "production"}]
    profile_blocks = [item for item in issues if profile in item["blocking_profiles"]]
    delivery_states = {
        "technical_complete": not technical_blocks,
        "production_complete": not production_blocks,
        "publish_ready_internal": not production_blocks,
        "publish_ready_digital": not [item for item in issues if "digital" in item["blocking_profiles"]],
        "publish_ready_print": not [item for item in issues if "print" in item["blocking_profiles"]],
        "publish_ready_commercial": not [item for item in issues if "commercial" in item["blocking_profiles"]],
    }
    return {
        "schema_version": 1,
        "kind": "comic_release_verdict",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "project_root": str(root),
        "chapter": chapter,
        "profile": profile,
        "target_platform": target_platform,
        "platform_profile": platform_profile,
        "verdict": "pass" if not profile_blocks else "blocked",
        "review_gate_summary": review_gate_summary(root, chapter),
        "vlm_adjudication": adjudication,
        "delivery_states": delivery_states,
        "artifacts": artifacts,
        "issues": issues,
    }


def write_outputs(root: Path, chapter: str, report: Mapping[str, Any]) -> tuple[Path, Path]:
    json_path = root / "生产数据" / f"release_verdict_{chapter}.json"
    md_path = root / "生产数据" / f"release_verdict_{chapter}.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gate_summary = report.get("review_gate_summary") or {}
    counts = gate_summary.get("counts") or {}
    lines = [
        f"# 漫画发布裁决 — {chapter}",
        "",
        f"- profile: {report.get('profile')}",
        f"- verdict: {report.get('verdict')}",
        "",
        "## 机检结论（review gate 真相区块——任何「验收通过」叙事必须引用本区块，不得只写 pass）",
        "",
        f"- review receipt verdict: **{gate_summary.get('receipt_verdict', 'missing')}**"
        + (
            f"（block {counts.get('block_count', '?')} / warn {counts.get('warn_count', '?')} / info {counts.get('info_count', '?')}）"
            if counts
            else ""
        ),
    ]
    for waiver in gate_summary.get("waivers") or []:
        lines.append(
            f"- 豁免留痕: `{waiver.get('path')}`（{waiver.get('stage')}；{waiver.get('reason')}）"
        )
    adjudication = report.get("vlm_adjudication") or {}
    if adjudication.get("tasks_file_present"):
        lines.append(
            f"- VLM 三轴裁决覆盖: {adjudication.get('adjudicated', 0)}/{adjudication.get('total', 0)}"
            + (f"，未处置 suspect {len(adjudication.get('open_suspects') or [])} 条" if adjudication.get("open_suspects") else "")
        )
    lines += [
        "",
        "## Delivery states",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in (report.get("delivery_states") or {}).items())
    lines += ["", "## Issues", ""]
    lines.extend(f"- {item.get('code')}: {item.get('reason')}" for item in report.get("issues") or [])
    if not report.get("issues"):
        lines.append("- 无。")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="漫画技术/生产/发布状态分离裁决")
    parser.add_argument("project_root")
    parser.add_argument("chapter")
    parser.add_argument("--profile", choices=PROFILES, default="internal")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--accept", action="store_true", help="为当前导出物和 review receipt 写 SHA 绑定的人工发布签收")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    if args.accept:
        try:
            create_acceptance(root, args.chapter, args.profile, reviewer=args.reviewer, reason=args.reason)
        except ValueError as exc:
            print(f"[block] {exc}", file=sys.stderr)
            return 2
    report = build(root, args.chapter, args.profile)
    if args.write:
        write_outputs(root, args.chapter, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"verdict={report['verdict']} profile={args.profile}")
    return 1 if report["verdict"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
