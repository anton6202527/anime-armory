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

    # 跨源对立检测：review 和 balance 对同一章的建议是否指向相反方向
    stage_conflict_pairs = [
        # (stage_a, stage_b, label) — 当两个来源把同一章路由到相反阶段时触发
        ({"review", "rewrite"}, {"balance"}, "节奏/审核方向交叉"),
        ({"review"}, {"direction_spec"}, "修改 vs 重设方向冲突"),
    ]
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
                rt["conflict"] = True
                rt.setdefault("conflict_with", []).append(bt["id"])
                rt["conflict_note"] = conflict_label
                bt["conflict"] = True
                bt.setdefault("conflict_with", []).append(rt["id"])
                bt["conflict_note"] = conflict_label

    return tasks


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
    lines.extend([
        "",
        "| priority | chapter | skill | stage | title | reason |",
        "|---|---:|---|---|---|---|",
    ])
    for task in plan["tasks"]:
        prefix = "⚠️ " if task.get("conflict") else ""
        lines.append(
            f"| {prefix}{task['priority']} | {task.get('chapter') or ''} | {task['recommended_skill']} | "
            f"{task['return_to_stage']} | {task['title']} | {task.get('reason') or ''} |"
        )
    if not plan["tasks"]:
        lines.append("| - |  | - | - | 暂无可合并修订任务 |  |")
    return "\n".join(lines) + "\n"


def build_plan(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    tasks = []
    tasks.extend(tasks_from_review(root))
    tasks.extend(tasks_from_score(root))
    tasks.extend(tasks_from_balance(root))
    tasks.extend(tasks_from_feedback(root))
    tasks.extend(tasks_from_simulate(root))

    # 跨来源冲突处理（先于 dedupe，因为降级可能影响去重键）
    kill_count = sum(
        1 for t in tasks
        if t.get("source") == "score_report" and t.get("priority") == "P0"
        and "弃稿重立" in str(t.get("title", ""))
    )
    _resolve_conflicts(tasks)

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
        },
        "tasks": dedupe(tasks),
        "kill_verdict_demotions": demoted_count(tasks) if kill_count else 0,
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
