#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge review/score/balance/feedback/simulate signals into one revision plan."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import date
from typing import Any

from store import atomic_write_json, atomic_write_text, file_lock


PLAN_KIND = "novel_revision_plan"


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Any) -> None:
    atomic_write_json(path, payload)


def _chapter_from_text(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    text = str(value or "")
    match = re.search(r"第0*(\d+)章|chapter[_\s-]?0*(\d+)", text, flags=re.I)
    if match:
        return int(match.group(1) or match.group(2))
    match = re.search(r"0*(\d+)", text)
    return int(match.group(1)) if match else None


def _task(task_id: str, source: str, title: str, *, priority: str = "P2",
          chapter: int | None = None, skill: str = "novel-review",
          stage: str = "review", reason: str = "") -> dict[str, Any]:
    return {
        "id": task_id,
        "source": source,
        "priority": priority,
        "chapter": chapter,
        "return_to_stage": stage,
        "recommended_skill": skill,
        "title": title,
        "reason": reason,
    }


def tasks_from_review(root: str) -> list[dict[str, Any]]:
    payload = load_json(os.path.join(root, "审稿", "review_report.json"), {}) or {}
    if not isinstance(payload, dict):
        return []
    tasks = []
    for idx, finding in enumerate(payload.get("findings") or [], 1):
        if not isinstance(finding, dict):
            continue
        affected = finding.get("affected_files") or []
        chapter = _chapter_from_text(" ".join(str(item) for item in affected)) or _chapter_from_text(finding.get("chapter"))
        blocking = finding.get("blocking") is True or finding.get("severity") == "blocking"
        tasks.append(_task(
            f"REV-{idx:03d}",
            "review_report",
            finding.get("problem") or finding.get("dimension") or "审稿问题待修",
            priority="P0" if blocking else "P1",
            chapter=chapter,
            skill=finding.get("recommended_skill") or "novel-review",
            stage=finding.get("return_to_stage") or "review",
            reason=finding.get("fix_hint") or finding.get("reason") or "",
        ))
    return tasks


def tasks_from_score(root: str) -> list[dict[str, Any]]:
    payload = load_json(os.path.join(root, "评分", "score_report.json"), {}) or {}
    if not isinstance(payload, dict):
        return []
    tasks = []
    verdict = payload.get("verdict")
    if verdict in {"大改", "弃稿重立"}:
        tasks.append(_task(
            "SCORE-VERDICT",
            "score_report",
            f"评分结论：{verdict}",
            priority="P0",
            skill="novel-score",
            stage="direction_spec" if verdict == "弃稿重立" else "rewrite",
            reason=str(payload.get("rewrite_roi") or payload.get("tier") or ""),
        ))
    for idx, action in enumerate(payload.get("next_actions") or [], 1):
        if not isinstance(action, dict):
            continue
        tasks.append(_task(
            f"SCORE-ACTION-{idx:03d}",
            "score_report",
            action.get("action") or action.get("title") or "评分建议待执行",
            priority=action.get("priority") or "P1",
            chapter=_chapter_from_text(action.get("chapter") or action.get("scope")),
            skill=action.get("recommended_skill") or "novel-rewrite",
            stage=action.get("return_to_stage") or "rewrite",
            reason=action.get("reason") or "",
        ))
    return tasks


def tasks_from_feedback(root: str) -> list[dict[str, Any]]:
    payload = load_json(os.path.join(root, "评分", "reader_telemetry_summary.json"), {}) or {}
    if not isinstance(payload, dict):
        return []
    tasks = []
    for chapter in payload.get("weakest_chapters") or []:
        tasks.append(_task(
            f"FEEDBACK-CH{int(chapter):02d}",
            "reader_telemetry_summary",
            f"真实反馈弱章复核：第{int(chapter):02d}章",
            priority="P1",
            chapter=int(chapter),
            skill="novel-review",
            stage="review",
            reason="完读/弃读/负评触发 weakest_chapters。",
        ))
    for item in (payload.get("experiments") or {}).get("best_by_ab_test") or []:
        caveat = item.get("caveat")
        tasks.append(_task(
            f"EXPERIMENT-{item.get('ab_test_id')}",
            "reader_telemetry_summary",
            f"A/B 结果归档：{item.get('ab_test_id')} → {item.get('variant_id')}",
            priority="P2" if caveat else "P1",
            skill="novel-feedback",
            stage="telemetry",
            reason="take_ids=" + ",".join(item.get("take_ids") or []) + (f"；{caveat}" if caveat else ""),
        ))
    return tasks


def tasks_from_simulate(root: str) -> list[dict[str, Any]]:
    payload = load_json(os.path.join(root, "评分", "reader_panel_signals.json"), {}) or {}
    if not isinstance(payload, dict):
        return []
    if payload.get("signal_only") is True or payload.get("analysis_mode") == "signal_only":
        return [_task(
            "SIMULATE-SIGNAL-ONLY",
            "reader_panel_signals",
            "模拟读者信号仅作低权重留存先验",
            priority="P2",
            skill="novel-simulate",
            stage="simulate",
            reason="qualitative_completed=false 时不能当完整试读结论。",
        )]
    return []


def tasks_from_market_evidence(root: str) -> list[dict[str, Any]]:
    payload = load_json(os.path.join(root, "评分", "market_evidence_tasks.json"), {}) or {}
    if not isinstance(payload, dict):
        return []
    tasks = []
    for idx, item in enumerate(payload.get("tasks") or [], 1):
        if not isinstance(item, dict):
            continue
        tasks.append(_task(
            f"MARKET-EVIDENCE-{idx:03d}",
            "market_evidence_tasks",
            item.get("title") or "补齐目标平台市场证据",
            priority=item.get("priority") or "P1",
            skill=item.get("recommended_skill") or "novel-research",
            stage=item.get("return_to_stage") or "market_baseline",
            reason=item.get("reason") or "",
        ))
    jobs = load_json(os.path.join(root, "评分", "market_evidence_jobs.json"), {}) or {}
    if isinstance(jobs, dict) and jobs.get("jobs"):
        tasks.append(_task(
            "MARKET-EVIDENCE-JOBS",
            "market_evidence_jobs",
            "执行市场证据深搜 job 并回灌 manual_evidence",
            priority="P1",
            skill="novel-score",
            stage="market_baseline",
            reason="评分目录存在 market_evidence_jobs.json；需完成搜索、结构化证据和重新采集。",
        ))
    return tasks


def tasks_from_balance(root: str) -> list[dict[str, Any]]:
    tasks = []
    for path in sorted(glob.glob(os.path.join(root, "审稿", "*balance*.json")) + glob.glob(os.path.join(root, "评分", "*heatmap*.json"))):
        payload = load_json(path, {}) or {}
        if not isinstance(payload, dict):
            continue
        findings = payload.get("findings") or payload.get("alerts") or []
        for idx, finding in enumerate(findings, 1):
            if not isinstance(finding, dict):
                continue
            tasks.append(_task(
                f"BALANCE-{os.path.basename(path)}-{idx:03d}",
                os.path.basename(path),
                finding.get("message") or finding.get("problem") or "节奏/结构问题待修",
                priority="P1" if finding.get("blocking") else "P2",
                chapter=_chapter_from_text(finding.get("chapter") or finding.get("path")),
                skill=finding.get("recommended_skill") or "novel-balance",
                stage=finding.get("return_to_stage") or "balance",
                reason=finding.get("reason") or "",
            ))
    pacing = load_json(os.path.join(root, "评分", "pacing_signals.json"), {}) or {}
    if isinstance(pacing, dict) and pacing.get("kind") == "novel_pacing_signals":
        for idx, row in enumerate(pacing.get("chapters") or [], 1):
            if not isinstance(row, dict):
                continue
            verdict = str(row.get("verdict") or row.get("status") or "").strip()
            if not verdict or verdict in {"ok", "OK", "正常", "balanced", "pass"}:
                continue
            chapter = _chapter_from_text(row.get("chapter") or row.get("chapter_label"))
            tasks.append(_task(
                f"PACING-CH{chapter or idx:02d}",
                "pacing_signals",
                f"节奏诊断：第{chapter or '?'}章 {verdict}",
                priority="P1" if any(k in verdict for k in ("阻断", "坍塌", "注水", "过快", "过慢", "弱")) else "P2",
                chapter=chapter,
                skill="novel-balance",
                stage="balance",
                reason=row.get("reason") or row.get("diagnosis") or row.get("note") or "",
            ))
        ending_risk = pacing.get("烂尾预警") or pacing.get("ending_risk_warnings") or []
        if isinstance(ending_risk, dict):
            overdue = int(ending_risk.get("超期伏笔数") or ending_risk.get("overdue_count") or 0)
            blocking = int(ending_risk.get("烂尾级超期") or ending_risk.get("blocking") or 0)
            if overdue or blocking:
                tasks.append(_task(
                    "PACING-ENDRISK-SUMMARY",
                    "pacing_signals",
                    f"烂尾预警：超期伏笔 {overdue} 条，烂尾级 {blocking} 条",
                    priority="P1" if blocking else "P2",
                    chapter=_chapter_from_text(ending_risk.get("through_chapter")),
                    skill="novel-balance",
                    stage="balance",
                    reason=f"伏笔回收率：{ending_risk.get('回收率')}",
                ))
        else:
            for idx, warning in enumerate(ending_risk, 1):
                if not isinstance(warning, dict):
                    continue
                title = warning.get("title") or warning.get("thread") or warning.get("id") or "伏笔回收风险"
                tasks.append(_task(
                    f"PACING-ENDRISK-{idx:03d}",
                    "pacing_signals",
                    f"烂尾预警：{title}",
                    priority="P1",
                    chapter=_chapter_from_text(warning.get("chapter") or warning.get("due_chapter") or warning.get("path")),
                    skill="novel-balance",
                    stage="balance",
                    reason=warning.get("reason") or warning.get("suggestion") or warning.get("description") or "",
                ))
    return tasks


# ── macro-before-micro 修订纪律（传统编辑共识：结构未锁前不做行文级修补，否则
# 移场景/并章/砍支线时行文功夫全部白费）。三层：
#   structure（结构级：方向/主线/大纲/弃稿/烂尾/时间线）
#   scene    （场景级：节奏/钩子/桥段/人物戏——默认档）
#   line     （行文级：文风/措辞/AI腔/对话标签/重复率）
# 纪律落地为**排序 + 缓办标记**，不删任务：同优先级内 structure 先行；存在未决
# 结构级 P0/P1 时，行文级任务打 deferred_until_structure 标记（干了也可能白干）。
TIER_RANK = {"structure": 0, "scene": 1, "line": 2}
_STRUCTURE_STAGES = {"direction_spec", "rewrite", "blueprint", "outline", "structure"}
_STRUCTURE_KW = ("结构", "主线", "大纲", "方向", "弃稿", "大改", "烂尾", "伏笔",
                 "时间线", "逻辑", "设定矛盾", "情节", "弧段", "支线")
_LINE_KW = ("文风", "行文", "措辞", "病句", "错别字", "润色", "语感", "AI腔", "AI 腔",
            "过滤词", "对话标签", "重复率", "回声", "拐杖", "用词", "句长", "文笔")


def classify_tier(task: dict[str, Any]) -> str:
    """把修订任务归到 structure/scene/line 三层。纯函数·可测。

    判据优先级：结构级 stage > 结构级关键词 > 行文级关键词 > 默认 scene。
    结构级判据放最前——"文风大改"这类混合措辞按结构处理（宁高勿低，先锁大再修小）。
    """
    blob = f"{task.get('title') or ''} {task.get('reason') or ''}"
    if task.get("return_to_stage") in _STRUCTURE_STAGES:
        return "structure"
    if any(k in blob for k in _STRUCTURE_KW):
        return "structure"
    if any(k in blob for k in _LINE_KW):
        return "line"
    return "scene"


def apply_tier_discipline(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """给任务打 tier 标签、同优先级内按 macro→micro 重排、给行文级打缓办标记。

    返回摘要 {counts, deferred_line_tasks}。原地修改 tasks 的顺序与字段。
    """
    for t in tasks:
        t["tier"] = classify_tier(t)
    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    tasks.sort(key=lambda t: (rank.get(t.get("priority"), 9), TIER_RANK.get(t.get("tier"), 9),
                              t.get("chapter") or 9999, t.get("id") or ""))
    structure_open = any(
        t["tier"] == "structure" and t.get("priority") in ("P0", "P1") for t in tasks
    )
    deferred = 0
    if structure_open:
        for t in tasks:
            if t["tier"] == "line":
                t["deferred_until_structure"] = True
                t["reason"] = (t.get("reason") or "") + (
                    "；[macro-first] 存在未决结构级修订——结构未锁前行文级修补可能白费，建议后置"
                )
                deferred += 1
    counts = {tier: sum(1 for t in tasks if t.get("tier") == tier) for tier in TIER_RANK}
    return {"counts": counts, "deferred_line_tasks": deferred,
            "structure_open": structure_open}


def dedupe(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    for task in sorted(tasks, key=lambda t: (rank.get(t.get("priority"), 9), t.get("chapter") or 9999, t.get("id"))):
        key = (task.get("chapter"), task.get("title"), task.get("recommended_skill"))
        if key in seen:
            continue
        seen.add(key)
        out.append(task)
    return out


def _resolve_conflicts(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """处理跨来源信号冲突：

    1. 弃稿重立降级：score 判"弃稿重立"时，方向都变了——非 score 来源的 P0
       自动降为 P2（不再是紧急修复，而是"待新方向确定后重新评估"）。
    2. 跨源对立检测：review 和 balance 对同一章给出相反建议时，打 conflict 标签。"""
    # 检查是否有弃稿重立判决
    has_kill = any(
        t.get("source") == "score_report"
        and t.get("priority") == "P0"
        and "弃稿重立" in str(t.get("title", ""))
        for t in tasks
    )
    if has_kill:
        for t in tasks:
            if t.get("priority") == "P0" and t.get("source") != "score_report":
                t["priority"] = "P2"
                t["title"] = f"[已降级-方向已变] {t['title']}"
                t["reason"] = (t.get("reason") or "") + (
                    "；评分结论为「弃稿重立」，方向设定变更后此问题需在新框架下重新评估"
                )
                t["resolution"] = {
                    "type": "score_kill_demotes_non_score_p0",
                    "winner": "score_report",
                    "loser": t.get("source"),
                    "decision": "demote_to_P2",
                    "explanation": "评分结论为「弃稿重立」时，方向规格已失效；非评分 P0 不再作为当前稿紧急修补项，而是等待新方向确定后重新评估。",
                    "next_gate": "direction_spec",
                }

    # 跨源对立检测：review 和 balance 对同一章的建议是否指向相反方向
    review_tasks = [t for t in tasks if t.get("source") == "review_report"]
    # balance 侧任务靠 stage/技能识别，而非 source 子串——pacing 任务 source 为
    # "pacing_signals"（不含 "balance"），是 balance 侧的主力信号，旧的子串匹配
    # 会把它整段漏掉，导致 review↔节奏 的同章方向冲突从不触发。
    balance_tasks = [
        t for t in tasks
        if t.get("return_to_stage") == "balance"
        or t.get("recommended_skill") == "novel-balance"
        or (t.get("source") and "balance" in t["source"])
    ]
    for rt in review_tasks:
        rch = rt.get("chapter")
        if rch is None:
            continue
        for bt in balance_tasks:
            if bt.get("chapter") != rch:
                continue
            # 同一章 + 路由到不同阶段 → 标记
            if rt.get("return_to_stage") != bt.get("return_to_stage"):
                conflict_label = f"跨源冲突：review→{rt.get('return_to_stage')} vs balance→{bt.get('return_to_stage')}"
                resolution = {
                    "type": "cross_source_stage_conflict",
                    "winner": "manual_editor_review",
                    "decision": "hold_for_editor_arbitration",
                    "explanation": "同一章的审稿信号与节奏/结构信号要求回到不同阶段；不能自动串行执行，否则可能互相覆盖。需先人工裁决主问题，再执行获胜路径。",
                    "candidates": [
                        {
                            "task_id": rt["id"],
                            "source": rt.get("source"),
                            "stage": rt.get("return_to_stage"),
                            "skill": rt.get("recommended_skill"),
                        },
                        {
                            "task_id": bt["id"],
                            "source": bt.get("source"),
                            "stage": bt.get("return_to_stage"),
                            "skill": bt.get("recommended_skill"),
                        },
                    ],
                }
                rt["conflict"] = True
                rt.setdefault("conflict_with", []).append(bt["id"])
                rt["conflict_note"] = conflict_label
                rt["conflict_resolution"] = resolution
                bt["conflict"] = True
                bt.setdefault("conflict_with", []).append(rt["id"])
                bt["conflict_note"] = conflict_label
                bt["conflict_resolution"] = resolution

    return tasks


def conflict_summary(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return compact, explicit conflict/resolution records for plan consumers."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for task in tasks:
        resolution = task.get("conflict_resolution") or task.get("resolution")
        if not isinstance(resolution, dict):
            continue
        key = (str(task.get("id") or ""), str(resolution.get("type") or ""))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "task_id": task.get("id"),
            "chapter": task.get("chapter"),
            "source": task.get("source"),
            "priority": task.get("priority"),
            "title": task.get("title"),
            "note": task.get("conflict_note") or task.get("reason") or "",
            "resolution": resolution,
        })
    return out


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# 修订计划",
        "",
        f"- 生成日期：{plan['generated_at']}",
        f"- 任务数：{len(plan['tasks'])}",
    ]
    # 弃稿重立摘要
    if plan.get("kill_verdict_demotions"):
        lines.append(f"- ⚠️ 弃稿重立降级：{plan['kill_verdict_demotions']} 项非评分 P0 已降为 P2（方向设定已变）")
    # 冲突摘要
    conflicts = [t for t in plan["tasks"] if t.get("conflict")]
    if conflicts:
        lines.append(f"- ⚠️ 跨源冲突：{len(conflicts)} 项任务存在 review/balance 方向矛盾，已标记 `conflict: true`")
    if plan.get("conflict_summary"):
        lines.append(f"- 冲突/裁决解释：{len(plan['conflict_summary'])} 条")
    tier = plan.get("tier_discipline") or {}
    if tier.get("structure_open") and tier.get("deferred_line_tasks"):
        lines.append(f"- 🧱 macro-first：存在未决结构级修订，{tier['deferred_line_tasks']} 项"
                     f"行文级任务已标记缓办（结构未锁前行文修补可能白费）")
    lines.extend([
        "",
        "| priority | tier | chapter | skill | stage | title | reason |",
        "|---|---|---:|---|---|---|---|",
    ])
    for task in plan["tasks"]:
        prefix = "⚠️ " if task.get("conflict") else ""
        tier_cell = task.get("tier") or ""
        if task.get("deferred_until_structure"):
            tier_cell += "·缓办"
        lines.append(
            f"| {prefix}{task['priority']} | {tier_cell} | {task.get('chapter') or ''} | {task['recommended_skill']} | "
            f"{task['return_to_stage']} | {task['title']} | {task.get('reason') or ''} |"
        )
    if not plan["tasks"]:
        lines.append("| - |  |  | - | - | 暂无可合并修订任务 |  |")
    if plan.get("conflict_summary"):
        lines.extend(["", "## 冲突与裁决解释", ""])
        for item in plan["conflict_summary"]:
            resolution = item.get("resolution") or {}
            candidates = resolution.get("candidates") or []
            candidate_text = ""
            if candidates:
                candidate_text = "；候选：" + " / ".join(
                    f"{c.get('task_id')}→{c.get('stage')}({c.get('skill')})" for c in candidates
                )
            lines.append(
                f"- {item.get('task_id')}：{resolution.get('type')}；"
                f"decision={resolution.get('decision')}；{resolution.get('explanation')}{candidate_text}"
            )
    return "\n".join(lines) + "\n"


def build_plan(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    tasks = []
    tasks.extend(tasks_from_review(root))
    tasks.extend(tasks_from_score(root))
    tasks.extend(tasks_from_balance(root))
    tasks.extend(tasks_from_feedback(root))
    tasks.extend(tasks_from_simulate(root))
    tasks.extend(tasks_from_market_evidence(root))

    # 跨来源冲突处理（先于 dedupe，因为降级可能影响去重键）
    kill_count = sum(
        1 for t in tasks
        if t.get("source") == "score_report" and t.get("priority") == "P0"
        and "弃稿重立" in str(t.get("title", ""))
    )
    _resolve_conflicts(tasks)
    planned_tasks = dedupe(tasks)
    tier_discipline = apply_tier_discipline(planned_tasks)

    return {
        "schema_version": 1,
        "kind": PLAN_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "inputs": {
            "review_report": os.path.exists(os.path.join(root, "审稿", "review_report.json")),
            "score_report": os.path.exists(os.path.join(root, "评分", "score_report.json")),
            "pacing_signals": os.path.exists(os.path.join(root, "评分", "pacing_signals.json")),
            "reader_telemetry_summary": os.path.exists(os.path.join(root, "评分", "reader_telemetry_summary.json")),
            "reader_panel_signals": os.path.exists(os.path.join(root, "评分", "reader_panel_signals.json")),
            "market_evidence_tasks": os.path.exists(os.path.join(root, "评分", "market_evidence_tasks.json")),
            "market_evidence_jobs": os.path.exists(os.path.join(root, "评分", "market_evidence_jobs.json")),
        },
        "tasks": planned_tasks,
        "kill_verdict_demotions": demoted_count(planned_tasks) if kill_count else 0,
        "conflict_summary": conflict_summary(planned_tasks),
        "tier_discipline": tier_discipline,
    }


def demoted_count(tasks: list[dict[str, Any]]) -> int:
    """统计被降级的任务数（标题中含 [已降级] 前缀）。"""
    return sum(1 for t in tasks if "[已降级" in str(t.get("title", "")))


def write_plan(root: str, plan: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "修订")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "revision_plan.json")
    md_path = os.path.join(out_dir, "修订计划.md")
    # 加锁串行化：避免两个 planner 并发 read-modify-write 互相覆盖。
    with file_lock(os.path.join(out_dir, "revision_plan.lock")):
        atomic_write_json(json_path, plan)
        atomic_write_text(md_path, render_markdown(plan))
    return json_path, md_path


def main() -> int:
    ap = argparse.ArgumentParser(description="合并 review/score/balance/feedback/simulate 为统一修订计划")
    ap.add_argument("project_root")
    ap.add_argument("--json", action="store_true", help="打印 JSON")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    plan = build_plan(root)
    json_path, md_path = write_plan(root, plan)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    print(f"[ok] revision plan JSON → {json_path}")
    print(f"[ok] revision plan MD   → {md_path}")
    print(f"[summary] tasks={len(plan['tasks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
