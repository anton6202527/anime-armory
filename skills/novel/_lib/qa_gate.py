#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared QA gate reader for novel-* projects.

Reads review_report.json and score_report.json without editing anything. The
gate is intentionally small so progress.py and export.py can share the same
blocking rules.
"""
import json
import os
import sys
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.join(_SKILLS, "novel", "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from project_io import load_project_settings  # noqa: E402

from novel_contract import normalize_rights_status, parse_regions
from report_snapshot import snapshot_chapters, validate_snapshot
from waivers import baseline_freshness_scope, has_waiver, load_waivers


BLOCKING_SCORE_VERDICTS = {"大改", "弃稿重立"}
COMMERCIAL_SCORE_MODES = {"商业连载", "漫剧源书"}
COMMERCIAL_SCORE_TARGETS = ("红果", "番茄", "抖音", "漫剧")
RIGHTS_REGION_EXPORT_FORMATS = {"n2d", "combine"}

REVIEW_REQUIRED_FIELDS = (
    "schema_version",
    "kind",
    "project_root",
    "generated_at",
    "scope",
    "source_snapshot",
    "summary",
    "mechanical_findings_path",
    "waivers",
    "findings",
    "next_actions",
)

SCORE_REQUIRED_FIELDS = (
    "schema_version",
    "kind",
    "project_root",
    "generated_at",
    "target_platform",
    "score_task_id",
    "score_task_path",
    "assessment_prompt_hash",
    "scope",
    "source_snapshot",
    "market_baseline",
    "scores",
    "deductions",
    "total_score",
    "tier",
    "verdict",
    "production_decision",
    "rewrite_roi",
    "waivers",
    "next_actions",
)


def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_meta(project_root):
    return _load_json(os.path.join(project_root, "_meta.json")) or {}


def _load_settings(project_root):
    return load_project_settings(project_root)


def _load_source_manifest(project_root, meta):
    candidates = []
    if meta.get("source_manifest"):
        candidates.append(os.path.join(project_root, str(meta["source_manifest"])))
    candidates.append(os.path.join(project_root, "小说", "source_manifest.json"))
    for path in candidates:
        payload = _load_json(path)
        if isinstance(payload, dict):
            payload["_manifest_path"] = path
            return payload
    return {}


def _score_required(project_root):
    meta = _load_meta(project_root)
    settings = _load_settings(project_root)
    mode = str(meta.get("draft_mode") or settings.get("小说生成模式") or "").strip()
    target_parts = [
        meta.get("target_platform"),
        meta.get("target"),
        ",".join(meta.get("outputs") or []),
        settings.get("目标平台"),
        settings.get("目标用途"),
        settings.get("输出格式"),
    ]
    target = " ".join(str(part or "") for part in target_parts)
    return mode in COMMERCIAL_SCORE_MODES or any(key in target for key in COMMERCIAL_SCORE_TARGETS)


def _target_distribution_regions(meta, settings):
    for key in ("target_distribution_regions", "发行地区"):
        value = meta.get(key) if key in meta else settings.get(key)
        regions = parse_regions(value)
        regions = [r for r in regions if r != "UNSPECIFIED"]
        if regions:
            return regions
    return []


def _source_distribution_regions(rights):
    covered = [r for r in parse_regions(rights.get("rights_covered_regions")) if r != "UNSPECIFIED"]
    if covered:
        return covered
    return [r for r in parse_regions(rights.get("distribution_regions")) if r != "UNSPECIFIED"]


def _region_covered(target_regions, source_regions):
    if not target_regions:
        return False
    if "GLOBAL" in source_regions:
        return True
    return all(region in source_regions for region in target_regions)


def _rights_blocking_context(project_root, export_formats):
    formats = set(export_formats or [])
    return bool(formats & RIGHTS_REGION_EXPORT_FORMATS) or _score_required(project_root)


def _rights_gate(project_root, *, export_formats=None):
    meta = _load_meta(project_root)
    settings = _load_settings(project_root)
    manifest = _load_source_manifest(project_root, meta)
    rights = dict(manifest)
    rights.update({k: v for k, v in meta.items() if k.startswith("rights_") or k in {
        "rights_status",
        "rights_jurisdiction",
        "rights_basis",
        "source_license_url",
        "rights_covered_regions",
        "distribution_regions",
        "requires_user_rights",
        "requires_region_rights_review",
        "rights_declared",
    }})
    raw_status = rights.get("rights_status")
    status = normalize_rights_status(raw_status)
    report = {
        "kind": "rights",
        "path": manifest.get("_manifest_path") or os.path.join(project_root, "_meta.json"),
        "exists": bool(meta or manifest),
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    if not (meta or manifest):
        report["warnings"].append(_warning(
            "RIGHTS-MISSING-META",
            "rights",
            "novel",
            "缺少 _meta.json/source_manifest.json；无法做完整权利辖区审计。",
        ))
        return report

    if raw_status in (None, ""):
        report["warnings"].append(_warning(
            "RIGHTS-STATUS-MISSING",
            "rights",
            "novel",
            "缺少 rights_status；旧项目可继续，但导出/发布前应补 _meta.json/source_manifest.json 权利字段。",
        ))
    elif status == "unknown":
        report["blockers"].append(_warning(
            "RIGHTS-UNKNOWN",
            "rights",
            "novel",
            "权利来源为 unknown；先确认 public-domain/user-owned/user-declared/original，不能导出或改编。",
        ))
    elif rights.get("requires_user_rights") and not (rights.get("rights_declared") or meta.get("rights_declared_at")):
        report["blockers"].append(_warning(
            "RIGHTS-USER-REQUIRED",
            "rights",
            "novel",
            "来源需要用户权利声明；请补授权证明或改用公版/自有文本。",
        ))
    elif status in {"user-owned", "user-declared"} and not (rights.get("rights_declared") or meta.get("rights_declared_at")):
        report["warnings"].append(_warning(
            "RIGHTS-DECLARATION-MISSING",
            "rights",
            "novel",
            "权利状态为自有/授权，但缺 rights_declared 或 rights_declared_at 留痕；发布前补授权记录。",
        ))

    if status == "public-domain":
        target_regions = _target_distribution_regions(meta, settings)
        source_regions = _source_distribution_regions(rights)
        high_risk = _rights_blocking_context(project_root, export_formats)
        if not target_regions:
            item = _warning(
                "RIGHTS-PD-REGION-UNSET",
                "rights",
                "novel",
                "公版来源缺少计划发行地区；Project Gutenberg/Wikisource 等来源的公版判断不自动覆盖所有地区。",
            )
            if high_risk:
                report["blockers"].append(item)
            else:
                report["warnings"].append(item)
        elif not _region_covered(target_regions, source_regions):
            item = _warning(
                "RIGHTS-PD-REGION-GAP",
                "rights",
                "novel",
                "公版来源辖区/发行地区不匹配："
                f"source_regions={source_regions or ['未写']} target_regions={target_regions}；"
                "补 rights_jurisdiction/rights_covered_regions/target_distribution_regions 或完成地区版权复核。",
            )
            report["blockers"].append(item)
        elif rights.get("requires_region_rights_review"):
            report["warnings"].append(_warning(
                "RIGHTS-PD-REGION-REVIEW",
                "rights",
                "novel",
                f"公版来源已覆盖目标地区 {target_regions}，但仍需保留来源许可/公版依据以备发布审查。",
            ))

    report["blocking"] = bool(report["blockers"])
    return report


def _warning(wid, stage, skill, reason):
    return {"id": wid, "stage": stage, "skill": skill, "reason": reason}


def _missing_fields(payload, fields):
    return [field for field in fields if field not in payload]


def _require_dict(payload, field, issues):
    if field in payload and not isinstance(payload.get(field), dict):
        issues.append(f"{field} 必须是 object")


def _require_list(payload, field, issues):
    if field in payload and not isinstance(payload.get(field), list):
        issues.append(f"{field} 必须是 list")


def _require_nonempty_string(payload, field, issues):
    if field in payload and not str(payload.get(field) or "").strip():
        issues.append(f"{field} 不能为空")


def validate_review_report_schema(payload):
    if not isinstance(payload, dict):
        return ["review_report 必须是 JSON object"]
    issues = []
    for field in _missing_fields(payload, REVIEW_REQUIRED_FIELDS):
        issues.append(f"缺少必填字段 {field}")
    if payload.get("schema_version") != 1:
        issues.append("schema_version 必须为 1")
    if payload.get("kind") != "novel_review_report":
        issues.append("kind 必须为 novel_review_report")
    for field in ("project_root", "generated_at"):
        _require_nonempty_string(payload, field, issues)
    for field in ("scope", "source_snapshot", "summary"):
        _require_dict(payload, field, issues)
    for field in ("waivers", "findings", "next_actions"):
        _require_list(payload, field, issues)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    for field in ("blocking_count", "suggestion_count", "polish_count", "waiver_count", "verdict"):
        if field not in summary:
            issues.append(f"summary 缺少 {field}")
    return issues


def validate_score_report_schema(payload, project_root=None):
    if not isinstance(payload, dict):
        return ["score_report 必须是 JSON object"]
    issues = []
    for field in _missing_fields(payload, SCORE_REQUIRED_FIELDS):
        issues.append(f"缺少必填字段 {field}")
    if payload.get("schema_version") != 1:
        issues.append("schema_version 必须为 1")
    if payload.get("kind") != "novel_score_report":
        issues.append("kind 必须为 novel_score_report")
    for field in ("generated_at", "target_platform", "score_task_id", "score_task_path",
                  "assessment_prompt_hash", "tier", "verdict", "rewrite_roi"):
        _require_nonempty_string(payload, field, issues)
    for field in ("scope", "source_snapshot", "market_baseline", "production_decision"):
        _require_dict(payload, field, issues)
    for field in ("scores", "deductions", "waivers", "next_actions"):
        _require_list(payload, field, issues)
    if "total_score" in payload and not isinstance(payload.get("total_score"), (int, float)):
        issues.append("total_score 必须是 number")
    baseline = payload.get("market_baseline") if isinstance(payload.get("market_baseline"), dict) else {}
    if "freshness" not in baseline:
        issues.append("market_baseline 缺少 freshness")
    elif not isinstance(baseline.get("freshness"), dict):
        issues.append("market_baseline.freshness 必须是 object")
    if project_root and str(payload.get("score_task_path") or "").strip():
        task_path = payload["score_task_path"]
        if not os.path.isabs(task_path):
            task_path = os.path.join(project_root, task_path)
        if not os.path.exists(task_path):
            issues.append("score_task_path 指向的 score_task.json 不存在")
    return issues


def _record_schema_issues(report, issues, *, block, wid, stage, skill):
    if not issues:
        return
    reason = "；".join(issues[:8])
    if len(issues) > 8:
        reason += f"；另有 {len(issues) - 8} 项"
    item = _warning(wid, stage, skill, reason)
    if block:
        report["blockers"].append(item)
    else:
        report["warnings"].append(item)


def missing_score_report_scope(project_root):
    meta = _load_meta(project_root)
    settings = _load_settings(project_root)
    snapshot = snapshot_chapters(project_root, mode="missing_score_report")
    return {
        "draft_mode": str(meta.get("draft_mode") or settings.get("小说生成模式") or ""),
        "target_platform": str(meta.get("target_platform") or settings.get("目标平台") or ""),
        "target": str(meta.get("target") or settings.get("目标用途") or ""),
        "outputs": ",".join(meta.get("outputs") or []),
        "chapter_count": len(snapshot.get("files") or []),
        "source_aggregate_hash": snapshot.get("aggregate_hash") or "",
    }


def _review_gate(project_root, *, require_report=False):
    path = os.path.join(project_root, "审稿", "review_report.json")
    payload = _load_json(path)
    report = {
        "kind": "review",
        "path": path,
        "exists": payload is not None,
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    if payload is None:
        item = _warning(
            "REVIEW-MISSING",
            "review",
            "novel-review",
            "缺少 审稿/review_report.json；导出前必须先生成审稿报告，或显式强制导出并留 waiver。",
        )
        if require_report:
            report["blockers"].append(item)
            report["blocking"] = True
        else:
            report["warnings"].append(item)
        return report
    _record_schema_issues(
        report,
        validate_review_report_schema(payload),
        block=require_report,
        wid="REVIEW-SCHEMA",
        stage="review",
        skill="novel-review",
    )
    snapshot_ok, snapshot_msg = validate_snapshot(project_root, payload.get("source_snapshot"))
    if not snapshot_ok:
        item = _warning("REVIEW-SNAPSHOT", "review", "novel-review", snapshot_msg)
        if require_report:
            report["blockers"].append(item)
        else:
            report["warnings"].append(item)
    for waiver in payload.get("waivers") or []:
        report["warnings"].append(_warning(
            waiver.get("id") or "REVIEW-WAIVER",
            "review",
            "novel-review",
            waiver.get("risk") or waiver.get("reason") or "review_report 含显式豁免",
        ))
    findings = payload.get("findings") or []
    for finding in findings:
        severity = finding.get("severity")
        if finding.get("blocking") is True or severity == "blocking":
            report["blockers"].append({
                "id": finding.get("id"),
                "stage": finding.get("return_to_stage"),
                "skill": finding.get("recommended_skill"),
                "reason": finding.get("problem") or finding.get("fix_hint") or finding.get("dimension"),
            })
    report["next_actions"] = payload.get("next_actions") or []
    report["blocking"] = bool(report["blockers"])
    return report


def _score_gate(project_root, *, require_report=None, global_waivers=None):
    global_waivers = global_waivers or []
    if require_report is None:
        require_report = _score_required(project_root)
    path = os.path.join(project_root, "评分", "score_report.json")
    payload = _load_json(path)
    report = {
        "kind": "score",
        "path": path,
        "exists": payload is not None,
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    if payload is None:
        scope = missing_score_report_scope(project_root)
        item = _warning(
            "SCORE-MISSING",
            "score",
            "novel-score",
            "缺少 评分/score_report.json；非商业/非漫剧项目可作为 warning，商业连载或漫剧源书导出前必须评分。",
        )
        if require_report and not has_waiver(global_waivers, "missing_score_report", scope):
            report["blockers"].append(item)
            report["blocking"] = True
        else:
            report["warnings"].append(item)
        return report
    _record_schema_issues(
        report,
        validate_score_report_schema(payload, project_root),
        block=require_report,
        wid="SCORE-SCHEMA",
        stage="score",
        skill="novel-score",
    )
    snapshot_ok, snapshot_msg = validate_snapshot(project_root, payload.get("source_snapshot"))
    if not snapshot_ok:
        item = _warning("SCORE-SNAPSHOT", "score", "novel-score", snapshot_msg)
        if require_report:
            report["blockers"].append(item)
        else:
            report["warnings"].append(item)
    verdict = payload.get("verdict")
    if verdict in BLOCKING_SCORE_VERDICTS:
        report["blockers"].append({
            "id": "SCORE-VERDICT",
            "stage": _first_return_stage(payload) or "demo",
            "skill": _first_recommended_skill(payload) or "novel-score",
            "reason": f"score_report verdict={verdict}",
        })
    report_waivers = payload.get("waivers") or []
    for waiver in report_waivers:
        report["warnings"].append(_warning(
            waiver.get("id") or "SCORE-WAIVER",
            "score",
            "novel-score",
            waiver.get("risk") or waiver.get("reason") or "score_report 含显式豁免",
        ))
    freshness = ((payload.get("market_baseline") or {}).get("freshness") or {})
    if freshness.get("blocking"):
        scope = baseline_freshness_scope(freshness)
        item = {
            "id": "SCORE-BASELINE",
            "stage": "score",
            "skill": "novel-score",
            "reason": freshness.get("reason") or f"market baseline freshness={freshness.get('status')}",
        }
        if (
            has_waiver(report_waivers, "score_baseline_freshness", scope)
            or has_waiver(global_waivers, "score_baseline_freshness", scope)
        ):
            report["warnings"].append(item)
        else:
            report["blockers"].append(item)
    report["next_actions"] = payload.get("next_actions") or []
    report["blocking"] = bool(report["blockers"])
    return report


def _first_return_stage(payload):
    for action in payload.get("next_actions") or []:
        stage = action.get("return_to_stage")
        if stage:
            return stage
    return None


def _first_recommended_skill(payload):
    for action in payload.get("next_actions") or []:
        skill = action.get("recommended_skill")
        if skill:
            return skill
    return None


def collect_gate_status(project_root, *, require_review_report=False, require_score_report=None,
                        export_formats=None):
    root = os.path.abspath(project_root)
    global_waivers = load_waivers(root)
    reports = [
        _rights_gate(root, export_formats=export_formats),
        _review_gate(root, require_report=require_review_report),
        _score_gate(root, require_report=require_score_report, global_waivers=global_waivers),
    ]
    blockers = []
    warnings = []
    next_actions = []
    for report in reports:
        blockers.extend(report["blockers"])
        warnings.extend(report.get("warnings") or [])
        next_actions.extend(report["next_actions"])
    for waiver in global_waivers:
        warnings.append(_warning(
            waiver.get("id") or "WAIVER",
            waiver.get("affected_gate") or "gate",
            waiver.get("source") or "manual",
            waiver.get("reason") or "存在显式豁免记录",
        ))
    return {
        "schema_version": 1,
        "kind": "novel_qa_gate",
        "project_root": root,
        "generated_at": date.today().isoformat(),
        "blocking": bool(blockers),
        "reports": reports,
        "blockers": blockers,
        "warnings": warnings,
        "waivers": global_waivers,
        "next_actions": next_actions,
    }


def format_gate_status(status):
    lines = ["# novel QA gate"]
    if not status["blocking"]:
        lines.append("[ok] 未发现 review/score 阻断。")
        if status.get("warnings"):
            lines.append("")
            lines.append("Warnings:")
            for warning in status["warnings"]:
                stage = warning.get("stage") or "unknown"
                skill = warning.get("skill") or "manual"
                reason = warning.get("reason") or "未填写原因"
                wid = warning.get("id") or "-"
                lines.append(f"- {wid} [{stage}] {skill}: {reason}")
        return "\n".join(lines)
    lines.append("[block] 存在阻断项，不能直接进入 export。")
    for blocker in status["blockers"]:
        stage = blocker.get("stage") or "unknown"
        skill = blocker.get("skill") or "manual"
        reason = blocker.get("reason") or "未填写原因"
        bid = blocker.get("id") or "-"
        lines.append(f"- {bid} [{stage}] {skill}: {reason}")
    if status.get("next_actions"):
        lines.append("\n建议回流：")
        for action in status["next_actions"][:5]:
            priority = action.get("priority") or "-"
            stage = action.get("return_to_stage") or "-"
            skill = action.get("recommended_skill") or "-"
            desc = action.get("action") or "-"
            lines.append(f"- {priority} [{stage}] {skill}: {desc}")
    if status.get("warnings"):
        lines.append("\nWarnings:")
        for warning in status["warnings"]:
            stage = warning.get("stage") or "unknown"
            skill = warning.get("skill") or "manual"
            reason = warning.get("reason") or "未填写原因"
            wid = warning.get("id") or "-"
            lines.append(f"- {wid} [{stage}] {skill}: {reason}")
    return "\n".join(lines)
