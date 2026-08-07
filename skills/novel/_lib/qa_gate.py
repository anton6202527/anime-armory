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
_SKILLS = os.path.abspath(os.path.join(_HERE, ".."))
_COMMON = os.path.join(_SKILLS, "_lib")
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

from novel_contract import is_long_arc_project, normalize_rights_status, parse_regions
from report_snapshot import snapshot_chapters, validate_snapshot
from waivers import baseline_freshness_scope, has_waiver, load_waivers
try:
    import source_language as _source_language  # 源语言/文体闸（同 _lib）
except Exception:  # pragma: no cover - defensive
    _source_language = None
try:
    import compliance_profile as _compliance_profile  # noqa: E402
except Exception:  # pragma: no cover - optional gate degrades defensively
    _compliance_profile = None


ADVISORY_SCORE_VERDICTS = {"大改", "弃稿重立"}
COMMERCIAL_SCORE_MODES = {"商业连载", "漫剧源书"}
COMMERCIAL_SCORE_TARGETS = ("红果", "番茄", "抖音", "漫剧", "短剧", "微短剧")
RIGHTS_REGION_EXPORT_FORMATS = {"combine"}
AI_USAGE_MODES = {"AI-generated", "AI-assisted", "未使用AI文本"}
AI_USAGE_REQUIRED_TARGETS = (
    "红果", "番茄", "抖音", "漫剧", "短剧", "微短剧", "商业连载",
    "出海", "海外", "KDP", "Kindle", "Amazon", "YouTube", "TikTok",
)
STRICT_AI_TEXT_TARGETS = (
    "晋江", "晋江文学城",
)
RUNTIME_AI_POLICY_REVIEW_TARGETS = (
    "起点", "番茄", "七猫", "纵横", "中文网文平台", "红果", "抖音",
)
TEXT_AUTHORSHIP_MODES = {"人类主创", "AI辅助", "AI生成"}
PLATFORM_AI_EVIDENCE_REL = os.path.join("合规", "platform_ai_evidence.json")
PLATFORM_AI_EXCEPTION_WAIVER = "ai_generated_text_platform_exception"

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


# 中文（无需出海披露）的语言标记；其余非空语言视为出海译制（需 AI 文本披露）。
_DOMESTIC_LANGUAGE_MARKS = ("中文", "简体", "繁体", "汉语", "国语", "zh", "chinese")


def _scope_signal_text(project_root):
    """**平台/用途声明字段**拼成的检索文本——_score_required / _ai_usage_required /
    严格AI（_platform_ai_gate）三处共用的**单一真值源**。

    脆弱性收敛历程：
    1. 此前三处各自拼一份 blob、字段集还不一致——收敛到这里。
    2. **剔除 目标语言**——那是语言而非投放范围，子串（"海外英文版"含"海外"）会把
       score/AI披露/严格AI 误触发成硬阻断；出海与否改由 _targets_overseas 按字段显式判定。
    3. **只读平台/用途声明字段，不再读格式/模式字段**：`输出格式`/`outputs` 是交付格式、
       `draft_mode`/`小说生成模式` 是生成模式，都不是「投到哪个平台」的声明，混进 blob 后
       它们里的平台子串会误触发。生成模式对 score 的影响已由 _score_required 的
       `mode in COMMERCIAL_SCORE_MODES` 精确集合判定覆盖，无需再靠子串。
    平台声明的权威字段是结构化的 `目标平台`/`target_platform`/`出海目标平台`；半结构化的
    `目标用途`/`小说用途`/`purpose` 用户常在此写"红果漫剧"，亦为声明，保留（有测试锁定）。
    """
    meta = _load_meta(project_root)
    settings = _load_settings(project_root)
    parts = [
        # 结构化平台声明（权威）
        meta.get("target_platform"),
        settings.get("目标平台"),
        settings.get("出海目标平台"),
        # 半结构化用途/平台意图声明
        meta.get("purpose"),
        meta.get("target"),
        settings.get("小说用途"),
        settings.get("目标用途"),
    ]
    return " ".join(str(part or "") for part in parts)


def _targets_overseas(project_root):
    """出海判定（替代把 目标语言 拼进关键词 blob 的子串近似）：声明了出海目标平台，
    或目标语言是非中文。"""
    meta = _load_meta(project_root)
    settings = _load_settings(project_root)
    if str(settings.get("出海目标平台") or "").strip():
        return True
    lang = str(settings.get("目标语言") or meta.get("target_language") or "").strip().lower()
    return bool(lang) and not any(mark in lang for mark in _DOMESTIC_LANGUAGE_MARKS)


def _score_required(project_root):
    meta = _load_meta(project_root)
    settings = _load_settings(project_root)
    mode = str(meta.get("draft_mode") or settings.get("小说生成模式") or "").strip()
    target = _scope_signal_text(project_root)
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
    if _targets_overseas(project_root):  # 出海译制需 AI 文本披露（替代 目标语言 子串近似）
        return True
    target = _scope_signal_text(project_root)
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
            "reader_panel_signals.json 是合成叙事探针，不能当真实读者或留存证据；score 不得据此自动调分，revision 只能把它当人工复核假设。",
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


def _target_text(project_root):
    # 收敛到单一真值源 _scope_signal_text（不再各拼一份、不再含 目标语言）。
    return _scope_signal_text(project_root)


def _normalize_text_authorship(value):
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if text in TEXT_AUTHORSHIP_MODES:
        return text
    if lowered in {"human", "human-primary", "human_primary", "人写", "人工主创"}:
        return "人类主创"
    if lowered in {"ai-assisted", "ai assisted", "assist", "辅助", "ai辅助"}:
        return "AI辅助"
    if lowered in {"ai-generated", "ai generated", "generated", "ai生成", "ai起草"}:
        return "AI生成"
    return text


def _text_authorship_from_ai_usage(payload):
    if not isinstance(payload, dict):
        return ""
    mode = _normalize_text_authorship(payload.get("text_authorship_mode"))
    if mode:
        return mode
    text_mode = payload.get("text_mode")
    if text_mode == "AI-generated":
        return "AI生成"
    if text_mode == "AI-assisted":
        return "AI辅助"
    if text_mode == "未使用AI文本":
        return "人类主创"
    return ""


def _strict_platform_hits(target):
    return sorted({key for key in STRICT_AI_TEXT_TARGETS if key in str(target or "")})


def _platform_ai_evidence_path(project_root):
    return os.path.join(project_root, PLATFORM_AI_EVIDENCE_REL)


def platform_ai_exception_scope(project_root, target=None, mode=None):
    """Scope for waiving AI-generated text on otherwise strict platforms.

    The waiver binds to the concrete evidence file hash. Updating platform
    evidence requires a fresh waiver, so stale/manual waivers cannot silently
    carry across rule changes.
    """
    path = _platform_ai_evidence_path(project_root)
    evidence_hash = _sha256_file(path) if os.path.exists(path) else ""
    hits = _strict_platform_hits(target if target is not None else _target_text(project_root))
    return {
        "target_platforms": ",".join(hits),
        "text_authorship_mode": str(mode or ""),
        "evidence_hash": evidence_hash,
    }


def _platform_ai_exception(project_root, target, mode, global_waivers):
    path = _platform_ai_evidence_path(project_root)
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return False, [f"缺少 {PLATFORM_AI_EVIDENCE_REL}；需补目标平台接受 AI 正文的当日正式证据。"]
    issues = []
    if payload.get("schema_version") != 1:
        issues.append("schema_version 必须为 1")
    if payload.get("kind") != "novel_platform_ai_evidence":
        issues.append("kind 必须为 novel_platform_ai_evidence")
    evidence_date = str(payload.get("evidence_date") or payload.get("checked_at") or "").strip()
    if evidence_date != date.today().isoformat():
        issues.append(f"evidence_date 必须是当日 {date.today().isoformat()}（当前 {evidence_date or '未写'}）")
    source_url = str(payload.get("source_url") or payload.get("url") or "").strip()
    if not source_url.startswith(("https://", "http://")):
        issues.append("source_url/url 必须是可追溯网页链接")
    if not str(payload.get("summary") or "").strip():
        issues.append("summary 必须说明平台规则与适用边界")
    accepted = payload.get("accepted_text_authorship_modes")
    if isinstance(accepted, str):
        accepted = [accepted]
    if not isinstance(accepted, list) or mode not in [str(x).strip() for x in accepted]:
        issues.append(f"accepted_text_authorship_modes 必须包含 {mode}")
    evidence_target = " ".join(str(payload.get(field) or "") for field in ("target_platform", "platform", "scope"))
    hits = _strict_platform_hits(target)
    if hits and not any(hit in evidence_target for hit in hits):
        issues.append(f"证据 target_platform/platform/scope 未覆盖当前严格平台：{','.join(hits)}")
    if issues:
        return False, issues
    scope = platform_ai_exception_scope(project_root, target, mode)
    if not has_waiver(global_waivers, PLATFORM_AI_EXCEPTION_WAIVER, scope):
        return False, [
            "已有平台证据但缺少 scoped waiver；请用 "
            f"type={PLATFORM_AI_EXCEPTION_WAIVER}、scope={scope} 写入 审稿/waiver_log.jsonl。"
        ]
    return True, [f"已用 {PLATFORM_AI_EVIDENCE_REL} + scoped waiver 放行 AI生成 正文平台例外。"]


def _platform_ai_gate(project_root, *, global_waivers=None):
    """Gate platform-submission risk separately from generic disclosure.

    AI usage disclosure answers "what must be recorded"; this gate answers
    "is this authorship mode compatible with the target platform workflow".
    """
    global_waivers = global_waivers or []
    settings = _load_settings(project_root)
    payload = _load_json(os.path.join(project_root, "合规", "ai_usage.json"))
    setting_mode = _normalize_text_authorship(settings.get("文本主创模式"))
    usage_mode = _text_authorship_from_ai_usage(payload)
    mode = setting_mode or usage_mode or ""
    target = _target_text(project_root)
    strict_target = any(key in target for key in STRICT_AI_TEXT_TARGETS)
    runtime_review_target = any(key in target for key in RUNTIME_AI_POLICY_REVIEW_TARGETS)
    report = {
        "kind": "platform_ai_text",
        "path": os.path.join(project_root, "_设置.md"),
        "exists": bool(setting_mode or usage_mode),
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    if mode and mode not in TEXT_AUTHORSHIP_MODES:
        report["warnings"].append(_warning(
            "AI-AUTHORSHIP-UNKNOWN",
            "compliance",
            "novel-craft",
            f"文本主创模式无法归一：{mode}；请在 _设置.md 写 人类主创 / AI辅助 / AI生成。",
        ))
        return report
    if setting_mode and usage_mode and setting_mode != usage_mode:
        report["blockers"].append(_warning(
            "AI-AUTHORSHIP-CONFLICT",
            "compliance",
            "novel-craft",
            f"_设置.md 文本主创模式={setting_mode}，但 合规/ai_usage.json 推断为 {usage_mode}；发布/投稿前需统一。",
        ))
    if strict_target and not mode:
        report["warnings"].append(_warning(
            "AI-AUTHORSHIP-MISSING",
            "compliance",
            "novel-craft",
            "晋江投稿缺少 文本主创模式；发布前须明确 人类主创 / AI辅助 / AI生成，并按当前原创写作规范核对 AI 使用层级。",
        ))
    elif strict_target and mode == "AI生成":
        exception_ok, exception_notes = _platform_ai_exception(project_root, target, mode, global_waivers)
        if exception_ok:
            report["warnings"].append(_warning(
                "AI-GENERATED-TEXT-PLATFORM-WAIVED",
                "compliance",
                "novel-craft",
                "；".join(exception_notes),
            ))
        else:
            report["blockers"].append(_warning(
                "AI-GENERATED-TEXT-PLATFORM-RISK",
                "compliance",
                "novel-craft",
                "晋江当前公开原创写作规范只允许校对级，以及创意环节的要素级/粗纲级 AI 使用；当前为 AI生成 正文。请改走合规的人类主创/限定 AI辅助流程，"
                "或补目标平台当日接受 AI 正文投稿的正式证据与 scoped waiver 留痕。"
                " 例外缺口：" + "；".join(exception_notes[:4]),
            ))
    elif strict_target and mode == "AI辅助":
        report["warnings"].append(_warning(
            "AI-ASSISTED-TEXT-PLATFORM-REVIEW",
            "compliance",
            "novel-craft",
            "晋江目标下，AI辅助应限制在当前公开规范允许的校对级、要素级与粗纲级；描写、细纲、叙事级用途不应提交。保存 AI 前原稿、对话过程、首次输出及人工复核记录。",
        ))
    elif runtime_review_target and not mode:
        report["warnings"].append(_warning(
            "AI-AUTHORSHIP-MISSING",
            "compliance",
            "novel-craft",
            "目标平台的公开 AI 正文许可边界未统一核验；发布前明确文本主创模式，并检查作者后台、签约合同、活动规则或编辑通知。",
        ))
    elif runtime_review_target and mode == "AI生成":
        report["warnings"].append(_warning(
            "AI-GENERATED-TEXT-POLICY-UNRESOLVED",
            "compliance",
            "novel-craft",
            "未找到足以支持该平台“全稿 AI 正文可发布”的通用现行公开规则。平台提供 AI 工具或要求标识都不等于允许全稿投稿；发布前运行时核验作者后台/合同/活动规则。",
        ))
    elif runtime_review_target and mode == "AI辅助":
        report["warnings"].append(_warning(
            "AI-ASSISTED-TEXT-PLATFORM-REVIEW",
            "compliance",
            "novel-craft",
            "AI辅助范围与目标平台规则需运行时核验；记录 human_steering、review_steps、AI 前稿与最终人工修改，不把“平台提供 AI 工具”外推成全稿许可。",
        ))
    if report["blockers"]:
        report["next_actions"].append({
            "priority": "P0",
            "return_to_stage": "draft",
            "recommended_skill": "novel-craft",
            "action": "把 _设置.md 的 文本主创模式 改为 人类主创/AI辅助，并按 novel-edit/novel-review 完成人工主创与编辑留痕；或补平台接受 AI 正文的证据和 waiver。",
        })
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
    if verdict in ADVISORY_SCORE_VERDICTS:
        report["warnings"].append({
            "id": "SCORE-VERDICT",
            "stage": _first_return_stage(payload) or "demo",
            "skill": _first_recommended_skill(payload) or "novel-score",
            "reason": (
                f"score_report verdict={verdict}；该结论来自主观量规/模型判断，仅作编辑建议，"
                "不得单独阻断写作、导出或发布。"
            ),
            "confidence": "heuristic",
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
    """长弧/长篇判定——单一真值源 novel_contract.is_long_arc_project（与 flow 共用）。

    含 scale/target>=30 **以及** 商业连载/漫剧·微短剧源书 模式·用途——它们即便章数 <30
    也按长弧处理。此前本函数漏了 mode/purpose，与 flow.long_arc_mode 漂移，导致商业连载
    短项目在导出闸收不到 ARC-MISSING / scene_cards 提醒。"""
    meta = _load_meta(project_root)
    settings = _load_settings(project_root)
    return is_long_arc_project(meta, settings)


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


def _demo_gate(project_root):
    """Demo gate 导出侧复检：demo_gate 在 draft_packets 是**写入期**硬闸（Demo 过审前
    不批量写章），但导出/QA gate 此前完全不读它——若有人走旁路写章、或当初取了
    `--allow-missing-demo` 的 waiver，就能在 Demo 从未过审的情况下一路导出。

    - `demo_chapters>0` 且已写到 demo 之后的章（批量生产已发生）且 demo_gate 未 passed
      （缺失或 status≠passed）→ 阻断导出。
    - 仍在 demo 阶段（写的章数 ≤ demo_chapters）但未过审 → 仅提醒。
    - `demo_chapters=0`（无 Demo 概念，如短篇/部分派生）→ 不产出任何条目。
    """
    meta = _load_meta(project_root)
    report = {
        "kind": "demo_gate",
        "path": os.path.join(project_root, "审稿", "demo_gate.json"),
        "exists": False,
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    try:
        demo_count = int(meta.get("demo_chapters") or 0)
    except (TypeError, ValueError):
        demo_count = 0
    if demo_count <= 0:
        return report
    payload = _load_json(report["path"]) or {}
    report["exists"] = bool(payload)
    status = payload.get("status")
    chapters_written = len(_chapter_files(project_root))
    passed = status == "passed"
    if passed:
        return report
    if chapters_written > demo_count:
        report["blockers"].append({
            "id": "DEMO-GATE-NOT-PASSED",
            "stage": "review",
            "skill": "novel-review",
            "reason": (f"已写到第 {chapters_written} 章（超过 demo_chapters={demo_count}），"
                       f"但 审稿/demo_gate.json status={status!r}（未通过/缺失）；批量生产前 Demo "
                       f"必须过审。补审前 {demo_count} 章并用 novel-review 生成 demo_gate.json（status=passed）"
                       f"后再导出，或显式记 waiver。"),
        })
        report["next_actions"].append({
            "priority": "P0",
            "return_to_stage": "review",
            "recommended_skill": "novel-review",
            "action": f"审阅前 {demo_count} 章，写 审稿/demo_gate.json（status=passed）后重跑 QA gate。",
        })
    else:
        report["warnings"].append(_warning(
            "DEMO-GATE-PENDING", "review", "novel-review",
            f"Demo 阶段（已写 {chapters_written}/{demo_count} 章）尚未过审；批量生产前先过 Demo gate。",
        ))
    report["blocking"] = bool(report["blockers"])
    return report


def _scene_cards_gate(project_root):
    path = os.path.join(project_root, "设定", "scene_cards.json")
    payload = _load_json(path)
    report = {
        "kind": "scene_cards",
        "path": path,
        "exists": isinstance(payload, dict),
        "blocking": False,
        "blockers": [],
        "warnings": [],
        "next_actions": [],
    }
    required_fields = ("pov", "desire", "obstacle", "conflict", "turn", "value_shift")
    if not isinstance(payload, dict):
        if _score_required(project_root) or _arc_long_project(project_root):
            report["warnings"].append(_warning(
                "SCENE-CARDS-MISSING",
                "outline",
                "novel-craft",
                "商业/长篇项目建议建立 设定/scene_cards.json，把章节拆到 POV/目标/阻碍/冲突/转折/价值变化的场景级打磨单位。",
            ))
            report["next_actions"].append({
                "priority": "P1",
                "return_to_stage": "outline",
                "recommended_skill": "novel-craft",
                "action": "运行 scene_cards.py scaffold 后补齐场景卡，再重出 draft packets。",
            })
        return report
    if payload.get("kind") != "novel_scene_cards":
        report["warnings"].append(_warning(
            "SCENE-CARDS-SCHEMA",
            "outline",
            "novel-craft",
            "scene_cards.json kind 不是 novel_scene_cards；请用 scene_cards.py scaffold/check 重建或迁移。",
        ))
        return report
    for scene in payload.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        missing = [field for field in required_fields if not str(scene.get(field) or "").strip()]
        if missing:
            report["blockers"].append(_warning(
                "SCENE-CARD-MISSING-FIELDS",
                "outline",
                "novel-craft",
                f"{scene.get('id') or 'scene'} 缺关键字段：{'、'.join(missing)}；没有目标/阻碍/转折/价值变化的场景不能进入高质量定稿。",
            ))
    if report["blockers"]:
        report["next_actions"].append({
            "priority": "P1",
            "return_to_stage": "outline",
            "recommended_skill": "novel-craft",
            "action": "补齐 scene_cards.json 后重跑 scene_cards.py check，并重新生成对应章节任务包。",
        })
    report["blocking"] = bool(report["blockers"])
    return report


def _source_language_gate(project_root):
    """源语言/文体闸：原作.txt 若是文言文/外文且未建 confirmed 源理解层 → 阻断（先建理解层再改写成白话文）。

    现代白话 / 无原作（原创从零）→ clean。纯结构化判定（不调模型），与 source_language.check 单一真值源。"""
    report = {"kind": "source_language", "blocking": False,
              "blockers": [], "warnings": [], "next_actions": []}
    if _source_language is None:
        return report
    try:
        res = _source_language.check(project_root)
    except Exception:  # pragma: no cover - defensive
        return report
    if res.get("verdict") == "needs_comprehension":
        reg = res.get("register")
        label = "文言文/古文" if reg == "classical_zh" else "外文"
        report["blockers"].append(_warning(
            "SOURCE-LANG-COMPREHENSION", "source_language", "novel-rewrite",
            f"原作疑似{label}（{reg}）：默认假设原作是现代中文白话文，按白话直接改写会错术语/典故/称谓。"
            "先 `python3 skills/novel/_lib/source_language.py <项目根> --scaffold` 建 设定/source_comprehension.md "
            "源理解层并补全，把 source_comprehension.json 的 status 置 confirmed 后再改写。"))
        report["blocking"] = True
        report["next_actions"].append({
            "priority": "P0",
            "return_to_stage": "source_language",
            "recommended_skill": "novel-rewrite",
            "action": "建并确认源理解层（现代白话理解 + 古今词/术语对照 + 文化注释 + 改写边界），再改写成白话文。",
        })
    return report


def collect_gate_status(project_root, *, require_review_report=False, require_score_report=None,
                        export_formats=None, require_state_closure=True,
                        state_chapter=None, require_ai_usage=None):
    root = os.path.abspath(project_root)
    global_waivers = load_waivers(root)
    if require_ai_usage is None:
        require_ai_usage = _ai_usage_required(root, export_formats)
    reports = [
        _source_language_gate(root),
        _rights_gate(root, export_formats=export_formats),
        _research_gate(root),
        _review_gate(root, require_report=require_review_report),
        _score_gate(root, require_report=require_score_report, global_waivers=global_waivers),
        _arc_gate(root, require=_arc_long_project(root)),
        _reader_panel_gate(root),
        _platform_ai_gate(root, global_waivers=global_waivers),
        _scene_cards_gate(root),
        _demo_gate(root),
    ]
    if require_state_closure:
        # 短篇自动豁免：<5 章的短故事不需要完整 state_ledger，仅出 advisory 级别提醒。
        # 但豁免**只针对全项目闭环完整性扫描**（state_chapter=None）；当调用方显式指定
        # state_chapter（novel-gate review/score --chapter 的逐章准入），该章的 state_delta
        # 与合并是这一章的硬作业，与项目总章数无关——否则 <5 章短篇在 review 闸永远收不到
        # STATE-DELTA-MISSING 阻断，整条逐章 review 闸对短篇空转。
        chapters = _chapter_files(root)
        effective_require = (state_chapter is not None) or (len(chapters) >= 5)
        state_report = _state_closure_gate(root, chapter=state_chapter, require=effective_require)
        if not effective_require and state_report.get("warnings"):
            state_report.setdefault("warnings", []).insert(0, _warning(
                "STATE-SHORT-WAIVER", "state_closure", "novel",
                "短篇项目（<5 章）：state_closure 仅作提醒，不阻断。长篇小说（>=5 章）会自动升为阻断级检查。",
            ))
        reports.append(state_report)
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
