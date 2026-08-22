#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Author-facing workflow checklist for novel projects.

This script turns the novel family into a step-by-step author workflow. It only
checks artifacts and writes status reports under 生产数据; it never writes prose or
marks progress complete.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import date
from typing import Any


NOVEL_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if NOVEL_LIB not in sys.path:
    sys.path.insert(0, NOVEL_LIB)
from craft_profile import resolve_craft_profile, validate_craft_contract_snapshot  # noqa: E402
from authenticity_contract import evaluate_authenticity_read  # noqa: E402
from novel_pipeline import human_stage_approval_status, stage_by_key  # noqa: E402
from project_io import load_project_settings  # noqa: E402
from exploration import ExplorationError, exploration_status as read_exploration_status  # noqa: E402


WORKFLOW_KIND = "novel_author_workflow"

BLUEPRINT_ARTIFACTS_BY_KIND = {
    "create": ["设定/创作蓝图.md"],
    "rewrite": ["设定/改动spec.md"],
    "continue": ["设定/续写方向.md", "设定/末章状态.md"],
    "expand": ["设定/事件骨架.json", "设定/章节映射.md"],
    "condense": ["设定/主线骨架.json", "设定/章节映射.md"],
    "spinoff": ["设定/锚点表.json"],
}


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    out: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if isinstance(payload, dict):
                out.append(payload)
    return out


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def rel_exists(root: str, relpath: str) -> bool:
    return os.path.exists(os.path.join(root, relpath))


def any_glob(root: str, pattern: str) -> bool:
    return bool(glob.glob(os.path.join(root, pattern)))


def exploration_evidence_status(root: str) -> dict[str, Any]:
    """Summarize optional non-canon exploration evidence for author navigation.

    Absence is optional and never blocks.  Once a manifest exists, corruption
    is a blocker because the workflow must not recommend formal absorption from
    stale seed/draft/sidecar/candidate evidence.  This helper is read-only and
    deliberately does not treat a candidate as formal stage completion.
    """
    exploration_root = os.path.join(root, "探索")
    if not os.path.lexists(exploration_root):
        return {
            "initialized": False,
            "integrity_ok": True,
            "human_first_seed_count": 0,
            "draft_count": 0,
            "candidate_count": 0,
            "decision_counts": {},
            "blockers": [],
            "warnings": ["未建立非正史探索区（可选，不阻断正式成书流程）"],
        }
    try:
        status = read_exploration_status(root)
    except (ExplorationError, OSError, TypeError, ValueError) as exc:
        return {
            "initialized": True,
            "integrity_ok": False,
            "human_first_seed_count": 0,
            "draft_count": 0,
            "candidate_count": 0,
            "decision_counts": {},
            "blockers": [f"探索区无法验证：{exc}"],
            "warnings": [],
        }
    if not status.get("initialized"):
        return {
            "initialized": False,
            "integrity_ok": True,
            "human_first_seed_count": 0,
            "draft_count": 0,
            "candidate_count": 0,
            "decision_counts": {},
            "blockers": [],
            "warnings": ["探索目录尚无 manifest（可选，不阻断；不会自动推进正式阶段）"],
        }

    decisions = status.get("decisions") or []
    decision_counts: dict[str, int] = {}
    for item in decisions:
        if not isinstance(item, dict):
            continue
        key = str(item.get("decision") or "unknown")
        decision_counts[key] = decision_counts.get(key, 0) + 1
    candidate_count = sum(
        1 for item in decisions
        if isinstance(item, dict) and item.get("decision") == "promote_candidate"
    )
    seed_count = len(status.get("seeds") or [])
    draft_count = len(status.get("drafts") or [])
    integrity_ok = bool(status.get("integrity_ok"))
    warnings = [
        f"非正史探索证据：human-first seed={seed_count}，探索稿={draft_count}，"
        f"晋升候选={candidate_count}；候选不会自动完成蓝图、Demo 或正式章节阶段。"
    ]
    if seed_count == 0:
        warnings.append("探索区没有 human-first seed；允许用于建议后试写，但不得倒签作者原始种子。")
    blockers = [] if integrity_ok else [
        "探索区完整性损坏：seed/draft/sidecar/decision/candidate 至少一项 hash 不匹配；"
        "先修复或作为新快照重新登记，禁止据此吸收进正式流程。"
    ]
    return {
        "initialized": True,
        "integrity_ok": integrity_ok,
        "human_first_seed_count": seed_count,
        "draft_count": draft_count,
        "candidate_count": candidate_count,
        "decision_counts": decision_counts,
        "blockers": blockers,
        "warnings": warnings,
    }


def blueprint_artifacts(meta: dict[str, Any]) -> list[str]:
    kind = str(meta.get("kind") or "create").strip().lower()
    if kind in {"", "original", "原创", "import"}:
        kind = "create"
    return list(BLUEPRINT_ARTIFACTS_BY_KIND.get(kind, BLUEPRINT_ARTIFACTS_BY_KIND["create"]))


def draft_progress(root: str, meta: dict[str, Any]) -> tuple[bool, list[str]]:
    chapter_count = len(glob.glob(os.path.join(root, "章节", "第*.md")))
    target = as_int(meta.get("target_chapters"))
    ledger_ok = rel_exists(root, "审稿/state_ledger.json")
    warnings: list[str] = []
    if target and chapter_count < target:
        warnings.append(f"正文仅完成 {chapter_count}/{target} 章，不能把首章存在误判为全稿完成")
    if not ledger_ok:
        warnings.append("缺少审稿/state_ledger.json，写后状态闭环未建立")
    complete = chapter_count > 0 and ledger_ok and (not target or chapter_count >= target)
    return complete, warnings


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clipped_items(items: list[str], *, limit: int = 5) -> list[str]:
    if len(items) <= limit:
        return items
    return [*items[:limit], f"...另 {len(items) - limit} 项"]


def review_blockers(root: str) -> tuple[list[str], list[str]]:
    payload = load_json(os.path.join(root, "审稿", "review_report.json"), {}) or {}
    if not isinstance(payload, dict) or not payload:
        return [], []
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    blockers: list[str] = []
    warnings: list[str] = []
    count = as_int(summary.get("blocking_count"))
    if count:
        blockers.append(f"review_report 仍有 {count} 个阻断问题")
    verdict = str(summary.get("verdict") or payload.get("verdict") or "").strip()
    if verdict and verdict not in {"pass", "通过", "ok", "OK", "minor", "小改"}:
        warnings.append(f"review_report verdict={verdict}")
    for item in payload.get("findings") or []:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "").lower()
        message = item.get("problem") or item.get("message") or item.get("dimension") or "审稿问题"
        if item.get("blocking") or severity in {"blocking", "block", "阻断级", "p0"}:
            blockers.append(str(message))
        elif severity in {"warning", "warn", "建议级", "p1"}:
            warnings.append(str(message))
    return clipped_items(blockers), clipped_items(warnings)


def score_blockers(root: str, *, commercial: bool) -> tuple[list[str], list[str]]:
    path = os.path.join(root, "评分", "score_report.json")
    payload = load_json(path, {}) or {}
    if not isinstance(payload, dict) or not payload:
        return (["商业/平台项目缺少 score_report"] if commercial else []), []
    decision = payload.get("production_decision") if isinstance(payload.get("production_decision"), dict) else {}
    verdict = str(payload.get("verdict") or "").strip()
    production_decision = str(decision.get("decision") or "").strip()
    blockers: list[str] = []
    warnings: list[str] = []
    if production_decision == "kill" or verdict in {"弃稿重立", "kill"}:
        warnings.append(
            f"score 建议为 {verdict or production_decision}；该量规结论仅供编辑复核，不自动阻断定稿"
        )
    elif production_decision in {"revise", "major_rewrite"} or verdict in {"大改", "小改"}:
        warnings.append(f"score 结论为 {verdict or production_decision}，需确认修订项已处理")
    freshness = payload.get("market_baseline", {}).get("freshness") if isinstance(payload.get("market_baseline"), dict) else {}
    if isinstance(freshness, dict) and freshness.get("blocking"):
        blockers.append("score 使用的市场基准已过期或证据不足")
    return blockers, warnings


def research_blockers(root: str) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    needs = load_json(os.path.join(root, "资料", "research_needs.json"), {}) or {}
    if isinstance(needs, dict) and needs:
        blocking_count = as_int(needs.get("blocking_count"))
        warning_count = as_int(needs.get("warning_count"))
        if blocking_count:
            blockers.append(f"research_needs 有 {blocking_count} 个阻断级资料缺口")
        if warning_count:
            warnings.append(f"research_needs 有 {warning_count} 个建议级资料缺口")
        open_market = needs.get("open_market_evidence_tasks") or []
        if open_market:
            warnings.append(f"仍有 {len(open_market)} 个市场证据任务未补")
    support = load_json(os.path.join(root, "审稿", "research_fact_support.json"), {}) or {}
    if isinstance(support, dict) and support:
        support_blocking = as_int(support.get("blocking"))
        if support_blocking:
            blockers.append(f"research_fact_support 有 {support_blocking} 个专业事实证据阻断")
        for item in support.get("alerts") or []:
            if not isinstance(item, dict):
                continue
            message = item.get("message") or item.get("type") or "专业资料问题"
            if item.get("severity") == "阻断级":
                blockers.append(str(message))
            elif item.get("severity") == "建议级":
                warnings.append(str(message))
    if rel_exists(root, "资料/research_sources.json") and not rel_exists(root, "资料/research_scene_usage.json"):
        warnings.append("已有 research_sources.json，但未生成 research_scene_usage.json；专业事实尚未映射到章节/场景")
    return clipped_items(blockers), clipped_items(warnings)


def author_intent_status(root: str) -> tuple[bool, list[str]]:
    check = load_json(os.path.join(root, "设定", "author_intent_check.json"), {}) or {}
    if isinstance(check, dict) and check.get("kind") == "novel_author_intent_check":
        return bool(check.get("passed")), [
            str(item.get("message") or item.get("id"))
            for item in check.get("findings") or []
            if isinstance(item, dict) and item.get("severity") == "blocking"
        ]
    payload = load_json(os.path.join(root, "设定", "author_intent.json"), {}) or {}
    if isinstance(payload, dict) and payload.get("kind") == "novel_author_intent":
        missing = []
        for field in ("core_theme", "non_negotiables"):
            value = payload.get(field)
            if not value or "待填写" in str(value):
                missing.append(f"author_intent.{field} 未完成")
        return not missing, missing
    return False, ["缺少作者意图档案：设定/author_intent.json"]


def manuscript_map_status(root: str) -> tuple[bool, list[str]]:
    check = load_json(os.path.join(root, "设定", "manuscript_map_check.json"), {}) or {}
    if isinstance(check, dict) and check.get("kind") == "novel_manuscript_map_check":
        snapshot_status = validate_craft_contract_snapshot(
            root,
            check.get("source_snapshot"),
            resolve_craft_profile(load_project_settings(root)),
        )
        if not snapshot_status["fresh"]:
            return False, [
                "manuscript_map_check 已过期（"
                + ", ".join(snapshot_status["issues"])
                + "）；请重跑 manuscript_map.py --write，旧通过记录不能放行"
            ]
        blockers = [
            str(item.get("message") or item.get("id"))
            for item in check.get("findings") or []
            if isinstance(item, dict) and item.get("severity") == "blocking"
        ]
        if check.get("passed") is not True and not blockers:
            blockers.append("manuscript_map_check 未明确通过；请重跑结构地图检查")
        return not blockers and check.get("passed") is True, blockers
    if rel_exists(root, "设定/manuscript_map.json"):
        return False, ["已有 manuscript_map 但缺少可验证的新鲜 check；请重跑 manuscript_map.py --write"]
    return False, ["缺少 manuscript_map；中长篇 review 缺结构地图基准"]


def metadata_pack_status(root: str) -> tuple[bool, list[str]]:
    check = load_json(os.path.join(root, "导出", "metadata_pack_check.json"), {}) or {}
    if isinstance(check, dict) and check.get("kind") == "novel_metadata_pack_check":
        return bool(check.get("passed")), [
            str(item.get("message") or item.get("id"))
            for item in check.get("findings") or []
            if isinstance(item, dict) and item.get("severity") == "blocking"
        ]
    payload = load_json(os.path.join(root, "导出", "metadata_pack.json"), {}) or {}
    if isinstance(payload, dict) and payload.get("kind") == "novel_metadata_pack":
        missing = []
        for field in ("title", "short_blurb", "categories"):
            if not payload.get(field):
                missing.append(f"metadata_pack.{field} 未完成")
        return not missing, missing
    return False, ["缺少导出/metadata_pack.json"]


def ai_usage_ready(root: str) -> tuple[bool, list[str]]:
    payload = load_json(os.path.join(root, "合规", "ai_usage.json"), {}) or {}
    if not isinstance(payload, dict) or not payload:
        return False, ["缺少合规/ai_usage.json"]
    if payload.get("text_mode") in {"AI-generated", "AI-assisted"} and not payload.get("chapter_usage"):
        return False, ["AI 使用披露缺 chapter_usage 逐章记录"]
    return True, []


def open_editor_queries(root: str) -> int:
    closed = {"answered", "accepted", "rejected", "resolved", "waived", "closed"}
    return sum(
        1 for record in load_jsonl(os.path.join(root, "修订", "editor_queries.jsonl"))
        if str(record.get("status") or "open").lower() not in closed
    )


def reader_blockers(root: str, *, validation_required: bool) -> tuple[list[str], list[str]]:
    if has_reader_evidence(root):
        payload = load_json(os.path.join(root, "评分", "reader_telemetry_summary.json"), {}) or {}
        warnings: list[str] = []
        if isinstance(payload, dict):
            flags = payload.get("flags") or []
            weakest = payload.get("weakest_chapters") or []
            if flags:
                warnings.append(f"真实读者反馈含风险旗标：{', '.join(str(x) for x in flags[:3])}")
            if weakest:
                warnings.append(f"真实读者掉点章节：{', '.join(str(x) for x in weakest[:5])}")
        return [], warnings
    if validation_required and has_reader_data_waiver(root):
        return [], ["缺少 reader_telemetry_summary.json，但 data_validated_launch 已有 scoped reader-data waiver"]
    if validation_required:
        return ["data_validated_launch 缺少 reader_telemetry_summary.json 或明确 reader_data waiver"], []
    if has_reader_plan(root):
        return [], ["已有 reader_test_plan，但还没有真实读者 telemetry"]
    return [], ["未建立 reader_test_plan；真实读者数据属于市场验证，不是发布合规前置条件"]


def edit_task_counts(root: str) -> tuple[int, int, int]:
    payload = load_json(os.path.join(root, "修订", "edit_plan.json"), {}) or {}
    tasks = payload.get("tasks") if isinstance(payload, dict) else []
    if not isinstance(tasks, list):
        return 0, 0, 0
    closed = {"fixed", "accepted", "waived", "closed", "done", "resolved"}
    open_p0_p1 = 0
    open_p2_plus = 0
    total_open = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        status = str(task.get("status") or "open").strip().lower()
        if status in closed:
            continue
        total_open += 1
        priority = str(task.get("priority") or "").upper()
        if priority in {"P0", "P1"}:
            open_p0_p1 += 1
        else:
            open_p2_plus += 1
    return open_p0_p1, open_p2_plus, total_open


def authenticity_blockers(root: str) -> tuple[list[str], list[str]]:
    """Check an opted-in authenticity read without judging its conclusions.

    The workflow blocks only when the project itself set
    ``required_for_release``.  Otherwise the same incomplete/stale conditions
    remain visible as editorial warnings.
    """
    report = evaluate_authenticity_read(root)
    if not report.get("applicable"):
        return [], []
    blockers = [
        str(item.get("message") or item.get("id"))
        for item in report.get("findings") or []
        if item.get("severity") == "blocking"
    ]
    warnings = [
        f"{item.get('message') or item.get('id')}（可选咨询，不阻断普通发布）"
        for item in report.get("findings") or []
        if item.get("severity") != "blocking"
    ]
    return blockers, warnings


def release_blockers(root: str) -> tuple[list[str], list[str]]:
    payload = load_json(os.path.join(root, "导出", "release_manifest.json"), {}) or {}
    readiness = payload.get("release_readiness") if isinstance(payload.get("release_readiness"), dict) else {}
    blockers = [
        f"{item.get('id')}: {item.get('message')}"
        for item in readiness.get("blockers") or []
        if isinstance(item, dict)
    ]
    warnings = [
        f"{item.get('id')}: {item.get('message')}"
        for item in readiness.get("warnings") or []
        if isinstance(item, dict)
    ]
    return clipped_items(blockers), clipped_items(warnings)


def demo_passed(root: str) -> bool:
    payload = load_json(os.path.join(root, "审稿", "demo_gate.json"), {}) or {}
    return payload.get("status") == "passed"


def demo_readiness(root: str, *, demo_ok: bool, commercial: bool) -> tuple[bool, list[str], list[str]]:
    path = os.path.join(root, "审稿", "demo_readiness.json")
    payload = load_json(path, {}) or {}
    blockers: list[str] = []
    warnings: list[str] = []
    if not demo_ok:
        blockers.append("demo_gate 未通过")
    if isinstance(payload, dict) and payload:
        for item in payload.get("issues") or []:
            if not isinstance(item, dict):
                continue
            message = f"{item.get('id')}: {item.get('message')}"
            if item.get("severity") == "blocking":
                blockers.append(message)
            else:
                warnings.append(message)
        if payload.get("ready_for_batch") is False:
            blockers.append("demo_readiness.ready_for_batch=false")
    elif demo_ok and commercial:
        warnings.append("商业/平台项目建议先跑 demo_readiness.py --write，确认商业评分与文学锚点都可批量写")
    return not blockers, clipped_items(blockers), clipped_items(warnings)


def score_decision(root: str) -> str:
    payload = load_json(os.path.join(root, "评分", "score_report.json"), {}) or {}
    decision = payload.get("production_decision") or {}
    return str(decision.get("decision") or payload.get("verdict") or "")


def has_reader_evidence(root: str) -> bool:
    return rel_exists(root, "评分/reader_telemetry_summary.json")


def has_reader_plan(root: str) -> bool:
    return rel_exists(root, "评分/reader_test_plan.json")


def has_reader_data_waiver(root: str) -> bool:
    path = os.path.join(root, "审稿", "waiver_log.jsonl")
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if not isinstance(payload, dict):
                continue
            if payload.get("type") not in {"reader_data_missing", "reader_telemetry_missing"}:
                continue
            scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
            release_profile = str(scope.get("release_profile") or "")
            if release_profile == "data_validated_launch":
                return True
    return False


def market_validation_required(root: str) -> bool:
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    values = [meta.get("release_profile"), meta.get("launch_profile")]
    settings_path = os.path.join(root, "_设置.md")
    if os.path.exists(settings_path):
        with open(settings_path, encoding="utf-8", errors="replace") as f:
            values.append(f.read())
    blob = " ".join(str(value or "") for value in values)
    return "data_validated_launch" in blob or "数据验证发布" in blob


def release_ready(root: str) -> bool:
    payload = load_json(os.path.join(root, "导出", "release_manifest.json"), {}) or {}
    return bool(payload.get("release_ready"))


def done(condition: bool, *, warning: bool = False) -> str:
    if condition:
        return "done"
    return "warning" if warning else "pending"


def build_steps(root: str) -> list[dict[str, Any]]:
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    settings_exists = rel_exists(root, "_设置.md")
    project_settings = load_project_settings(root) or {}
    delegated_review = str(project_settings.get("审阅策略") or "用户授权制作代理") == "用户授权制作代理"
    approval_args = (
        '--delegated --agent "delegate:novel-specialist-reviewer" '
        '--reason "按当前输入、产物与审阅清单完成独立代理复核"'
        if delegated_review
        else '--agent "<复核人>" --reason "<批准说明>"'
    )
    commercial_text = " ".join([
        str(meta.get("purpose") or ""),
        str(meta.get("target_platform") or ""),
        open(os.path.join(root, "_设置.md"), encoding="utf-8", errors="replace").read()
        if settings_exists else "",
    ])
    commercial = any(key in commercial_text for key in ("商业连载", "红果", "番茄", "抖音", "漫剧", "短剧", "微短剧", "KDP", "出海"))
    demo_ok = demo_passed(root)
    demo_ready, demo_blocking, demo_warnings = demo_readiness(root, demo_ok=demo_ok, commercial=commercial)
    score = score_decision(root)
    review_blocking, review_warnings = review_blockers(root)
    score_blocking, score_warnings = score_blockers(root, commercial=commercial)
    research_blocking, research_warnings = research_blockers(root)
    validation_required = market_validation_required(root)
    release_profile = "data_validated_launch" if validation_required else "platform_publish"
    reader_blocking, reader_warnings = reader_blockers(root, validation_required=validation_required)
    release_blocking, release_warnings = release_blockers(root)
    score_ok = rel_exists(root, "评分/score_report.json") and not score_blocking
    review_ok = rel_exists(root, "审稿/review_report.json") and not review_blocking
    reader_warning = has_reader_plan(root) and not has_reader_evidence(root)
    edit_deliverables = all(rel_exists(root, rel) for rel in (
        "修订/edit_plan.json",
        "修订/editorial_letter.md",
        "修订/style_sheet.md",
        "修订/proof_checklist.md",
    ))
    edit_open_p0_p1, edit_open_p2_plus, _edit_open_total = edit_task_counts(root)
    edit_blocking = [f"edit_plan 仍有 {edit_open_p0_p1} 个 P0/P1 未关闭任务"] if edit_open_p0_p1 else []
    query_count = open_editor_queries(root)
    if query_count:
        edit_blocking.append(f"仍有 {query_count} 个 editor query 未回答/关闭")
    edit_warnings = [f"edit_plan 仍有 {edit_open_p2_plus} 个 P2+ 未关闭任务"] if edit_open_p2_plus else []
    authenticity_blocking, authenticity_warnings = authenticity_blockers(root)
    edit_blocking.extend(authenticity_blocking)
    edit_warnings.extend(authenticity_warnings)
    edit_command = (
        f'python3 skills/novel/novel-edit/scripts/authenticity_read.py check "{root}" --write'
        if authenticity_blocking
        else f'python3 skills/novel/novel-edit/scripts/edit_plan.py "{root}"'
    )
    intent_ok, intent_blocking = author_intent_status(root)
    map_ok, map_blocking = manuscript_map_status(root)
    ai_ok, ai_blocking = ai_usage_ready(root)
    metadata_ok, metadata_blocking = metadata_pack_status(root)
    blueprint_evidence = blueprint_artifacts(meta)
    blueprint_ready = all(rel_exists(root, rel) for rel in blueprint_evidence)
    blueprint_stage = stage_by_key("blueprint", meta=meta, root=root)
    blueprint_approved, blueprint_approval_message, _ = human_stage_approval_status(root, blueprint_stage or {})
    setting_stage = stage_by_key("setting", meta=meta, root=root)
    setting_approved, setting_approval_message, _ = human_stage_approval_status(root, setting_stage or {})
    blueprint_contract_ready = blueprint_ready and rel_exists(root, "设定/读者契约.md") and intent_ok
    blueprint_command = (
        f'python3 skills/novel/scripts/pipeline_runner.py "{root}" --approve-stage blueprint '
        + approval_args
        if blueprint_contract_ready and not blueprint_approved
        else f'python3 skills/novel/novel-craft/scripts/author_intent.py scaffold "{root}"'
    )
    setting_outputs_ready = bool(setting_stage) and all(
        any_glob(root, pattern) for pattern in (setting_stage.get("outputs") or [])
    )
    setting_command = (
        f'python3 skills/novel/scripts/pipeline_runner.py "{root}" --approve-stage setting '
        + approval_args
        if setting_outputs_ready and not setting_approved
        else f'python3 skills/novel/novel-craft/scripts/manuscript_map.py "{root}" --write'
    )
    draft_complete, draft_warnings = draft_progress(root, meta)
    exploration_evidence = exploration_evidence_status(root)
    steps: list[dict[str, Any]] = [
        {
            "key": "setup",
            "label": "入口分流与项目设置",
            "status": done(rel_exists(root, "_meta.json") and settings_exists and rel_exists(root, "_进度.md")),
            "why": "先确定作品根、用途、平台、输出格式、文本主创模式和 AI 使用披露。",
            "evidence": ["_meta.json", "_设置.md", "_进度.md"],
            "blockers": [],
            "warnings": [],
            "command": f'python3 skills/novel/novel-settings/scripts/settings_cli.py "{root}" audit',
        },
        {
            "key": "exploration",
            "label": "Human-first seed 与非正史探索证据",
            "status": (
                "pending" if exploration_evidence["blockers"] else
                "done" if exploration_evidence["initialized"] else
                "warning"
            ),
            "why": "先看作者原始种子与探索候选是否完整；候选只帮助理解故事，绝不自动推进正式蓝图、Demo、章节或进度。",
            "evidence": [
                "探索/manifest.json",
                "探索/种子/*",
                "探索/草稿/*",
                "探索/决策/*",
                "探索/晋升候选/*",
            ],
            "blockers": exploration_evidence["blockers"],
            "warnings": exploration_evidence["warnings"],
            "summary": {
                key: exploration_evidence[key]
                for key in (
                    "initialized",
                    "integrity_ok",
                    "human_first_seed_count",
                    "draft_count",
                    "candidate_count",
                    "decision_counts",
                )
            },
            "command": f'python3 skills/novel/novel-craft/scripts/exploration.py "{root}" status --json',
        },
        {
            "key": "blueprint",
            "label": "构思蓝图与读者契约",
            "status": done(
                blueprint_ready
                and rel_exists(root, "设定/读者契约.md")
                and intent_ok
                and blueprint_approved
            ),
            "why": "蓝图、作者意图和读者契约是后续每章不偏题、不忘承诺、不牺牲主题的作者宪法。",
            "evidence": [*blueprint_evidence, "设定/读者契约.md", "设定/author_intent.json"],
            "blockers": [
                *intent_blocking,
                *([] if blueprint_approved else [blueprint_approval_message]),
            ],
            "warnings": [],
            "command": blueprint_command,
        },
        {
            "key": "evidence",
            "label": "资料、观察与审美准备",
            "status": done(
                not research_blocking and (
                rel_exists(root, "资料/research_sources.json")
                or rel_exists(root, "素材/观察札记.jsonl")
                or rel_exists(root, "设定/aesthetic_bank.json")
                ),
                warning=not research_blocking,
            ),
            "why": "专业事实、生活材料和正向审美样本要在写章前准备，缺一项不必硬挡普通项目，但要明示。",
            "evidence": ["资料/research_needs.json", "资料/research_sources.json", "资料/research_scene_usage.json", "素材/观察札记.jsonl", "设定/aesthetic_bank.json"],
            "blockers": research_blocking,
            "warnings": research_warnings,
            "command": f'python3 skills/novel/novel-research/scripts/research_pack.py scene-usage "{root}"',
        },
        {
            "key": "setting_scene",
            "label": "设定圣经、场景卡与结构地图",
            "status": done(
                (rel_exists(root, "设定/角色卡.md") or rel_exists(root, "设定/人物.md") or rel_exists(root, "设定/设定圣经.md"))
                and rel_exists(root, "设定/scene_cards.json")
                and map_ok
                and setting_approved
            ),
            "why": "角色、规则、场景目的和全书结构地图先结构化，后续 review 才能按基准判断是否跑偏。",
            "evidence": ["设定/角色卡.md", "设定/人物.md", "设定/设定圣经.md", "设定/scene_cards.json", "设定/manuscript_map.json"],
            "blockers": [
                *map_blocking,
                *([] if setting_approved else [setting_approval_message]),
            ],
            "warnings": [],
            "command": setting_command,
        },
        {
            "key": "demo",
            "label": "Demo 章与 Demo Gate",
            "status": done(demo_ready),
            "why": "前 1-3 章先验证文风、钩子、爽点、读者承诺和设定自洽。",
            "evidence": ["章节/第01章.md", "审稿/demo_gate.json", "审稿/demo_readiness.json"],
            "blockers": demo_blocking,
            "warnings": demo_warnings,
            "command": f'python3 skills/novel/novel-craft/scripts/demo_readiness.py "{root}" --write',
        },
        {
            "key": "draft_loop",
            "label": "分章写作与状态账本",
            "status": done(draft_complete, warning=True),
            "why": "正文、state_delta、state_verify 和 state_ledger 必须闭环，避免越写越漂。",
            "evidence": ["写作任务/第*.md", "章节/第*.md", "审稿/state_ledger.json"],
            "blockers": [],
            "warnings": draft_warnings,
            "command": f'python3 skills/novel/scripts/flow.py "{root}"',
        },
        {
            "key": "review_score",
            "label": "方向评分与硬伤审稿",
            "status": done(review_ok and (score_ok or not commercial)),
            "why": "score 判值不值得继续，review 抠硬伤；商业/平台项目缺 score 不应进入定稿。",
            "evidence": ["审稿/review_report.json", "评分/score_report.json"],
            "blockers": [*review_blocking, *score_blocking],
            "warnings": [*review_warnings, *score_warnings],
            "command": f'python3 skills/novel/novel-craft/scripts/revision_planner.py "{root}"',
        },
        {
            "key": "reader_validation",
            "label": "读者测试与真实反馈",
            "status": done(
                has_reader_evidence(root) and not reader_blocking,
                warning=not reader_blocking,
            ),
            "why": "真实完读/弃读用于市场验证；仅 data_validated_launch 把它作为硬前置，普通发布不要求先有历史遥测。",
            "evidence": ["评分/reader_test_plan.json", "评分/reader_telemetry_summary.json", "评分/reader_panel_signals.json"],
            "blockers": reader_blocking,
            "warnings": reader_warnings,
            "command": f'python3 skills/novel/novel-feedback/scripts/reader_test_plan.py "{root}" --scope opening:1-3',
        },
        {
            "key": "edit",
            "label": "分层专业编辑",
            "status": done(edit_deliverables and not edit_blocking),
            "why": "先 editorial/developmental，再 line edit，最后 copyedit/proofread；真实性/文化审读按项目显式选择接入。",
            "evidence": ["修订/edit_plan.json", "修订/editorial_letter.md", "修订/style_sheet.md", "修订/proof_checklist.md", "修订/authenticity_read.json"],
            "blockers": edit_blocking,
            "warnings": edit_warnings,
            "command": edit_command,
        },
        {
            "key": "publish_pack",
            "label": "AI/合规与发布元数据",
            "status": done(ai_ok and rel_exists(root, "合规/compliance_profile.json") and metadata_ok),
            "why": "发布前必须把 AI 使用、平台辖区合规和商品页元数据固定成同一版证据。",
            "evidence": ["合规/ai_usage.json", "合规/compliance_profile.json", "导出/metadata_pack.json"],
            "blockers": [*ai_blocking, *metadata_blocking],
            "warnings": [],
            "command": f'python3 skills/novel/novel-craft/scripts/metadata_pack.py "{root}" --write',
        },
        {
            "key": "release",
            "label": "导出与发布版本清单",
            "status": done(release_ready(root)),
            "why": "release manifest 绑定正文、导出物、review、score、AI 披露、合规和资料包 hash。",
            "evidence": ["导出/*.txt", "导出/release_manifest.json"],
            "blockers": release_blocking,
            "warnings": release_warnings,
            "command": f'python3 skills/novel/novel-craft/scripts/release_manifest.py "{root}" --release-name v1 --release-profile {release_profile}',
        },
    ]
    return steps


def build_workflow(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    steps = build_steps(root)
    # warning 是非阻断提示，不应劫持作者导航；只有 pending 才是当前必做步骤。
    next_step = next((step for step in steps if step["status"] == "pending"), None)
    return {
        "schema_version": 1,
        "kind": WORKFLOW_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "reference": "skills/novel/novel-craft/references/author-workflow.md",
        "current_step": next_step["key"] if next_step else "complete",
        "next_action": next_step["command"] if next_step else "",
        "steps": steps,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 作者成书流程状态",
        "",
        f"- 生成日期：{payload['generated_at']}",
        f"- 当前步骤：{payload['current_step']}",
    ]
    if payload.get("next_action"):
        lines.append(f"- 下一步命令：`{payload['next_action']}`")
    lines.extend(["", "## 步骤"])
    for step in payload["steps"]:
        mark = {"done": "✅", "warning": "🟡", "pending": "⬜"}.get(step["status"], "⬜")
        lines.append(f"### {mark} {step['label']} (`{step['key']}`)")
        lines.append(f"- 状态：{step['status']}")
        lines.append(f"- 作用：{step['why']}")
        lines.append("- 证据：" + "、".join(f"`{item}`" for item in step["evidence"]))
        if step.get("blockers"):
            lines.append("- 阻断：" + "；".join(str(item) for item in step["blockers"]))
        if step.get("warnings"):
            lines.append("- 警告：" + "；".join(str(item) for item in step["warnings"]))
        lines.append(f"- 建议命令：`{step['command']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_workflow(root: str, payload: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "生产数据")
    json_path = os.path.join(out_dir, "author_workflow.json")
    md_path = os.path.join(out_dir, "作者成书流程.md")
    write_json(json_path, payload)
    os.makedirs(out_dir, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(payload))
    return json_path, md_path


def main() -> int:
    ap = argparse.ArgumentParser(description="检查并输出作者成书通用流程状态")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true", help="write 生产数据/author_workflow.json and 作者成书流程.md")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        raise SystemExit(f"[err] 找不到作品根：{root}")
    payload = build_workflow(root)
    if args.write:
        json_path, md_path = write_workflow(root, payload)
        print(f"[ok] author workflow: {md_path}")
        print(f"[ok] author workflow json: {json_path}")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
