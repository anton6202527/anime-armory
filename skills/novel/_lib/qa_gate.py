#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared QA gate reader for novel-* projects.

Reads review_report.json, score_report.json, and research packet indexes
without editing anything. The gate is intentionally small so progress.py and
export.py can share the same blocking rules.
"""
import glob
import json
import os
import sys
import hashlib
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.join(_SKILLS, "novel", "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from project_io import load_project_settings  # noqa: E402

_RESEARCH = os.path.join(_SKILLS, "novel-research", "scripts")
if _RESEARCH not in sys.path:
    sys.path.insert(0, _RESEARCH)
try:
    import research_pack as _research_pack  # noqa: E402
except Exception:  # pragma: no cover - gate degrades if optional script is broken
    _research_pack = None

from novel_contract import normalize_rights_status, parse_regions
from report_snapshot import snapshot_chapters, validate_snapshot
from waivers import baseline_freshness_scope, has_waiver, load_waivers
try:
    import compliance_profile as _compliance_profile  # noqa: E402
except Exception:  # pragma: no cover - optional gate degrades defensively
    _compliance_profile = None


BLOCKING_SCORE_VERDICTS = {"大改", "弃稿重立"}
COMMERCIAL_SCORE_MODES = {"商业连载", "漫剧源书"}
COMMERCIAL_SCORE_TARGETS = ("红果", "番茄", "抖音", "漫剧", "短剧", "微短剧")
RIGHTS_REGION_EXPORT_FORMATS = {"combine"}
AI_USAGE_MODES = {"AI-generated", "AI-assisted", "未使用AI文本"}
AI_USAGE_REQUIRED_TARGETS = (
    "红果", "番茄", "抖音", "漫剧", "短剧", "微短剧", "商业连载",
    "出海", "海外", "KDP", "Kindle", "Amazon", "YouTube", "TikTok",
)

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
        meta.get("purpose"),
        meta.get("target_platform"),
        meta.get("target"),
        ",".join(meta.get("outputs") or []),
        settings.get("小说用途"),
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


def _ai_usage_required(project_root, export_formats):
    if not export_formats:
        return False
    if _score_required(project_root):
        return True
    meta = _load_meta(project_root)
    settings = _load_settings(project_root)
    target_parts = [
        meta.get("draft_mode"),
        meta.get("purpose"),
        meta.get("target_platform"),
        meta.get("target"),
        ",".join(meta.get("outputs") or []),
        settings.get("小说用途"),
        settings.get("目标平台"),
        settings.get("目标用途"),
        settings.get("出海目标平台"),
        settings.get("目标语言"),
    ]
    target = " ".join(str(part or "") for part in target_parts)
    return any(key in target for key in AI_USAGE_REQUIRED_TARGETS)


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


def _research_alert_id(alert_type):
    text = str(alert_type or "alert").upper().replace("_", "-")
    return f"RESEARCH-{text}"


def _research_gate(project_root):
    path = os.path.join(project_root, "资料", "research_sources.json")
    report = {
        "kind": "research",
        "path": path,
        "exists": os.path.exists(path),
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    if _research_pack is None:
        report["warnings"].append(_warning(
            "RESEARCH-UNAVAILABLE",
            "research",
            "novel-research",
            "无法加载 novel-research/scripts/research_pack.py；专业资料包 freshness gate 暂未运行。",
        ))
        return report
    try:
        payload = _research_pack.check_project(project_root, write=False)
    except Exception as exc:  # pragma: no cover - defensive gate for corrupt indexes
        report["blockers"].append(_warning(
            "RESEARCH-CHECK-FAILED",
            "research",
            "novel-research",
            f"专业资料包检查失败：{exc}",
        ))
        report["blocking"] = True
        return report
    for alert in payload.get("alerts") or []:
        reason = alert.get("message") or alert.get("type") or "专业资料包检查发现问题"
        detail = []
        if alert.get("domain"):
            detail.append(f"domain={alert['domain']}")
        if alert.get("evidence"):
            detail.append(f"evidence={alert['evidence']}")
        if detail:
            reason = reason + "；" + " ".join(detail)
        item = _warning(_research_alert_id(alert.get("type")), "research", "novel-research", reason)
        stale_block = alert.get("type") in {
            "pack_stale",
            "pack_missing_updated_at",
            "missing_required_research_pack",
        }
        if alert.get("severity") == "阻断级" and stale_block:
            report["blockers"].append(item)
        else:
            report["warnings"].append(item)
    if report["blockers"]:
        report["next_actions"].append({
            "priority": "P0",
            "return_to_stage": "research",
            "recommended_skill": "novel-research",
            "action": "补齐或刷新专业资料包后，重跑 review/export gate。",
        })
    report["blocking"] = bool(report["blockers"])
    return report


def _compliance_gate(project_root, *, require=False):
    path = os.path.join(project_root, "合规", "compliance_profile.json")
    report = {
        "kind": "compliance_profile",
        "path": path,
        "exists": os.path.exists(path),
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    if _compliance_profile is None:
        report["warnings"].append(_warning(
            "COMPLIANCE-UNAVAILABLE",
            "compliance",
            "novel-craft",
            "无法加载 compliance_profile.py；平台/辖区合规 profile 暂未运行。",
        ))
        return report
    try:
        profile = _compliance_profile.build_profile(project_root)
    except Exception as exc:  # pragma: no cover - corrupt project metadata
        item = _warning(
            "COMPLIANCE-CHECK-FAILED",
            "compliance",
            "novel-craft",
            f"合规 profile 检查失败：{exc}",
        )
        (report["blockers"] if require else report["warnings"]).append(item)
        report["blocking"] = bool(report["blockers"])
        return report
    blockers, warnings = _compliance_profile.gate_items(profile)
    for req in blockers:
        report["blockers"].append(_warning(
            "COMPLIANCE-" + str(req.get("id") or "unknown").upper().replace("_", "-"),
            "compliance",
            "novel-craft",
            req.get("reason") or req.get("title") or "平台/辖区合规要求未满足",
        ))
    for req in warnings:
        report["warnings"].append(_warning(
            "COMPLIANCE-" + str(req.get("id") or "unknown").upper().replace("_", "-"),
            "compliance",
            "novel-craft",
            req.get("reason") or req.get("title") or "平台/辖区合规提醒",
        ))
    if report["blockers"]:
        report["next_actions"].append({
            "priority": "P0",
            "return_to_stage": "compliance",
            "recommended_skill": "novel-craft",
            "action": "跑 compliance_profile.py --write；在平台/交付侧完成披露/权利/标识后用 --confirm <requirement_id> 留痕。",
        })
    report["blocking"] = bool(report["blockers"])
    return report


def _reader_panel_gate(project_root):
    path = os.path.join(project_root, "评分", "reader_panel_signals.json")
    payload = _load_json(path)
    report = {
        "kind": "reader_panel",
        "path": path,
        "exists": payload is not None,
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    if not isinstance(payload, dict):
        return report
    if payload.get("signal_only") is True or payload.get("analysis_mode") == "signal_only":
        report["warnings"].append(_warning(
            "SIMULATE-SIGNAL-ONLY",
            "score",
            "novel-simulate",
            "reader_panel_signals.json 是 signal-only 机读留存先验，不能当完整读者试读证据；score/revision 只能低权重使用，优先真实反馈。",
        ))
    if payload.get("qualitative_completed") is False:
        report["next_actions"].append({
            "priority": "P2",
            "return_to_stage": "simulate",
            "recommended_skill": "novel-simulate",
            "action": "补完人格心声/弃书点等定性面板，或导入 novel-feedback 的真实读者数据。",
        })
    return report


def _chapter_number_from_name(path):
    import re
    match = re.search(r"第0*(\d+)章", os.path.basename(path))
    return int(match.group(1)) if match else None


def _chapter_files(project_root):
    chapter_dir = os.path.join(project_root, "章节")
    if not os.path.isdir(chapter_dir):
        return []
    out = []
    for name in os.listdir(chapter_dir):
        if not name.endswith(".md"):
            continue
        num = _chapter_number_from_name(name)
        if num is not None:
            out.append((num, os.path.join(chapter_dir, name)))
    out.sort(key=lambda item: (item[0], item[1]))
    return out


def _state_delta_path(project_root, chapter):
    return os.path.join(project_root, "审稿", f"state_delta_第{chapter:02d}章.json")


def _chapter_path(project_root, chapter, fallback=None):
    if fallback:
        return fallback
    canonical = os.path.join(project_root, "章节", f"第{chapter:02d}章.md")
    if os.path.exists(canonical):
        return canonical
    for ch_num, path in _chapter_files(project_root):
        if ch_num == chapter:
            return path
    return canonical


def _chapter_ledger_key(chapter):
    return f"chapter_{chapter:02d}"


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _state_closure_gate(project_root, *, chapter=None, require=False):
    report = {
        "kind": "state_closure",
        "path": os.path.join(project_root, "审稿", "state_ledger.json"),
        "exists": os.path.exists(os.path.join(project_root, "审稿", "state_ledger.json")),
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    chapters = [(chapter, None)] if chapter else _chapter_files(project_root)
    if not chapters:
        return report
    ledger = _load_json(report["path"]) or {}
    chapter_deltas = ledger.get("chapter_deltas") if isinstance(ledger, dict) else {}
    if not isinstance(chapter_deltas, dict):
        chapter_deltas = {}
    for ch_num, chapter_path in chapters:
        chapter_file = _chapter_path(project_root, ch_num, chapter_path)
        if not os.path.exists(chapter_file):
            item = _warning(
                "STATE-CHAPTER-MISSING",
                "state_closure",
                "novel",
                f"第{ch_num:02d}章正文缺失：章节/第{ch_num:02d}章.md。",
            )
            (report["blockers"] if require else report["warnings"]).append(item)
            continue
        delta_path = _state_delta_path(project_root, ch_num)
        if not os.path.exists(delta_path):
            item = _warning(
                "STATE-DELTA-MISSING",
                "state_closure",
                "novel",
                f"第{ch_num:02d}章缺少写后状态增量：审稿/state_delta_第{ch_num:02d}章.json。",
            )
            (report["blockers"] if require else report["warnings"]).append(item)
            continue
        delta = _load_json(delta_path)
        if not isinstance(delta, dict):
            item = _warning(
                "STATE-DELTA-SCHEMA",
                "state_closure",
                "novel",
                f"第{ch_num:02d}章状态增量不是 JSON object：审稿/state_delta_第{ch_num:02d}章.json。",
            )
            (report["blockers"] if require else report["warnings"]).append(item)
            continue
        got = delta.get("chapter")
        if got is not None:
            try:
                got = int(got)
            except (TypeError, ValueError):
                got = None
            if got != ch_num:
                item = _warning(
                    "STATE-DELTA-CHAPTER",
                    "state_closure",
                    "novel",
                    f"第{ch_num:02d}章状态增量 chapter 字段不匹配。",
                )
                (report["blockers"] if require else report["warnings"]).append(item)
                continue
        key = _chapter_ledger_key(ch_num)
        if key not in chapter_deltas:
            item = _warning(
                "STATE-LEDGER-MISSING",
                "state_closure",
                "novel-craft",
                f"第{ch_num:02d}章 state_delta 尚未合并进 审稿/state_ledger.json。",
            )
            (report["blockers"] if require else report["warnings"]).append(item)
            continue
        entry = chapter_deltas.get(key)
        verification = entry.get("verification") if isinstance(entry, dict) else None
        if not isinstance(verification, dict):
            item = _warning(
                "STATE-LEDGER-UNVERIFIED",
                "state_closure",
                "novel-craft",
                f"第{ch_num:02d}章账本缺少 verification 指纹，无法证明 state_delta 与正文是同一版。",
            )
            (report["blockers"] if require else report["warnings"]).append(item)
            continue
        expected = {
            "chapter_file_hash": _sha256_file(chapter_file),
            "delta_hash": _sha256_file(delta_path),
        }
        for hash_key, current in expected.items():
            recorded = str(verification.get(hash_key) or "").strip()
            if not recorded:
                item = _warning(
                    "STATE-LEDGER-UNVERIFIED",
                    "state_closure",
                    "novel-craft",
                    f"第{ch_num:02d}章账本 verification 缺少 {hash_key}。",
                )
                (report["blockers"] if require else report["warnings"]).append(item)
                break
            if recorded != current:
                item = _warning(
                    "STATE-LEDGER-STALE",
                    "state_closure",
                    "novel-craft",
                    f"第{ch_num:02d}章账本 verification.{hash_key} 已过期；正文或 state_delta 修改后需重新对账并合并。",
                )
                (report["blockers"] if require else report["warnings"]).append(item)
                break
    report["blocking"] = bool(report["blockers"])
    return report


def _ai_usage_gate(project_root, *, require=False):
    path = os.path.join(project_root, "合规", "ai_usage.json")
    payload = _load_json(path)
    report = {
        "kind": "ai_usage",
        "path": path,
        "exists": payload is not None,
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    if payload is None:
        item = _warning(
            "AI-USAGE-MISSING",
            "compliance",
            "novel-craft",
            "缺少 合规/ai_usage.json；发布、商用、平台交付或出海前必须记录 AI 使用披露。",
        )
        (report["blockers"] if require else report["warnings"]).append(item)
        report["blocking"] = bool(report["blockers"])
        return report
    issues = []
    if not isinstance(payload, dict):
        issues.append("ai_usage 必须是 JSON object")
    else:
        if payload.get("schema_version") != 1:
            issues.append("schema_version 必须为 1")
        if payload.get("kind") != "novel_ai_usage":
            issues.append("kind 必须为 novel_ai_usage")
        text_mode = payload.get("text_mode")
        if text_mode not in AI_USAGE_MODES:
            issues.append("text_mode 必须为 AI-generated/AI-assisted/未使用AI文本")
        if text_mode in {"AI-generated", "AI-assisted"} and not str(payload.get("human_contribution") or "").strip():
            issues.append("AI 生成/辅助文本必须填写 human_contribution，记录创意、改写、审稿取舍等人工贡献")
        detail = payload.get("disclosure_detail")
        if detail is not None and not isinstance(detail, dict):
            issues.append("disclosure_detail 必须是 object")
    if issues:
        item = _warning(
            "AI-USAGE-SCHEMA",
            "compliance",
            "novel-craft",
            "；".join(issues[:6]),
        )
        (report["blockers"] if require else report["warnings"]).append(item)
    elif isinstance(payload, dict):
        detail = payload.get("disclosure_detail") or {}
        missing_detail = []
        for key in ("text_directness", "human_steering", "replaceability", "direct_incorporation", "review_steps"):
            if key not in detail:
                missing_detail.append(key)
        if missing_detail:
            report["warnings"].append(_warning(
                "AI-USAGE-DETAIL-MISSING",
                "compliance",
                "novel-craft",
                "AI 使用披露缺少细粒度字段："
                + "、".join(missing_detail)
                + "；建议用 novel-craft/scripts/ai_usage.py 重新生成，便于平台/读者披露。",
            ))
    report["blocking"] = bool(report["blockers"])
    return report


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
        "purpose": str(meta.get("purpose") or settings.get("小说用途") or settings.get("目标用途") or ""),
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


def _arc_long_project(project_root):
    """长篇判定（与 draft_packets 三步迭代阈值同口径）：scale=long 或 target_chapters>=30。"""
    meta = _load_json(os.path.join(project_root, "_meta.json")) or {}
    scale = str(meta.get("scale") or "").lower()
    try:
        target = int(meta.get("target_chapters") or 0)
    except (TypeError, ValueError):
        target = 0
    return scale in {"long", "长篇"} or target >= 30


def _arc_gate(project_root, *, require=False):
    """弧段（中段跑偏）gate：把 arc_gate.py 产出的 审稿/arc_gate_*.json 纳入导出闸门。

    - 任何 arc_gate 报告仍含阻断（blocking>0）→ 阻断导出（堵住「跑了 arc_gate 看到阻断却照样导出」）。
    - 长篇项目从未跑过 arc_gate → 警告（中段跑偏是长篇头号杀手，导出前提示先压力测试）。
    清除办法：修正问题后重跑 `novel-review/scripts/arc_gate.py --arc A-B` 覆盖旧报告。
    """
    review_dir = os.path.join(project_root, "审稿")
    report = {
        "kind": "arc",
        "path": review_dir,
        "exists": False,
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    paths = sorted(glob.glob(os.path.join(review_dir, "arc_gate_*.json")))
    report["exists"] = bool(paths)
    for path in paths:
        payload = _load_json(path) or {}
        try:
            nblock = int(payload.get("blocking") or 0)
        except (TypeError, ValueError):
            nblock = 0
        if nblock > 0:
            report["blockers"].append({
                "id": "ARC-BLOCK",
                "stage": "review",
                "skill": "novel-review",
                "reason": (f"弧段 gate {os.path.basename(path)} 仍有 {nblock} 项阻断"
                           f"（中段跑偏/连续不推进读者契约）；修正后重跑 arc_gate.py 覆盖旧报告再导出。"),
            })
    if not paths and require:
        report["warnings"].append(_warning(
            "ARC-MISSING", "review", "novel-review",
            "长篇项目从未跑过弧段 gate（arc_gate）；中段跑偏是长篇头号杀手，导出前建议先跑 "
            "novel-review/scripts/arc_gate.py --arc <起>-<止> 对各 arc 做压力测试。",
        ))
    report["blocking"] = bool(report["blockers"])
    return report


def collect_gate_status(project_root, *, require_review_report=False, require_score_report=None,
                        export_formats=None, require_state_closure=False,
                        state_chapter=None, require_ai_usage=None):
    root = os.path.abspath(project_root)
    global_waivers = load_waivers(root)
    if require_ai_usage is None:
        require_ai_usage = _ai_usage_required(root, export_formats)
    reports = [
        _rights_gate(root, export_formats=export_formats),
        _research_gate(root),
        _review_gate(root, require_report=require_review_report),
        _score_gate(root, require_report=require_score_report, global_waivers=global_waivers),
        _arc_gate(root, require=_arc_long_project(root)),
        _reader_panel_gate(root),
    ]
    if require_state_closure:
        reports.append(_state_closure_gate(root, chapter=state_chapter, require=True))
    if require_ai_usage or export_formats:
        reports.append(_ai_usage_gate(root, require=require_ai_usage))
        reports.append(_compliance_gate(root, require=bool(export_formats)))
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
