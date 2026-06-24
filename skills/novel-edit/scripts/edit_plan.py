#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a layered editing plan from existing novel QA artifacts.

This is deterministic scaffolding: it reads review/score/balance/reader
telemetry/scene-card artifacts and writes an edit plan. It does not rewrite the
manuscript.
"""
import argparse
import json
import os
from datetime import date


PHASE_ORDER = {
    "editorial_assessment": 0,
    "developmental_edit": 1,
    "line_edit": 2,
    "copyedit_proofread": 3,
}


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def severity_priority(value):
    text = str(value or "").lower()
    if text in {"blocking", "阻断级", "block"}:
        return "P0"
    if text in {"suggestion", "建议级", "warn", "warning"}:
        return "P1"
    return "P2"


def phase_for_dimension(dimension, return_stage=""):
    text = f"{dimension} {return_stage}"
    if any(k in text for k in ("outline", "demo", "reader_contract", "plot", "structure", "arc", "节奏", "题旨", "读者承诺", "主线", "章纲")):
        return "developmental_edit"
    if any(k in text for k in ("prose", "style", "voice", "dialogue", "文风", "对白", "AI味", "行文", "五感")):
        return "line_edit"
    if any(k in text for k in ("typo", "format", "copy", "proof", "错字", "标点", "术语", "格式")):
        return "copyedit_proofread"
    return "editorial_assessment"


def add_task(tasks, *, phase, priority, title, reason, chapter=None, source="", return_stage="", recommended_skill="novel-edit"):
    tasks.append({
        "id": f"EDIT-{len(tasks) + 1:03d}",
        "phase": phase,
        "priority": priority,
        "chapter": chapter,
        "title": title,
        "reason": reason,
        "source": source,
        "return_to_stage": return_stage,
        "recommended_skill": recommended_skill,
    })


def collect_review(tasks, root):
    path = os.path.join(root, "审稿", "review_report.json")
    payload = load_json(path, {}) or {}
    for item in payload.get("findings") or []:
        dimension = item.get("dimension") or item.get("stage") or item.get("return_to_stage") or "review"
        phase = phase_for_dimension(dimension, item.get("return_to_stage"))
        add_task(
            tasks,
            phase=phase,
            priority=severity_priority(item.get("severity") or ("blocking" if item.get("blocking") else "")),
            chapter=item.get("chapter"),
            title=item.get("problem") or item.get("dimension") or "审稿问题待处理",
            reason=item.get("fix_hint") or item.get("evidence") or item.get("problem") or "",
            source="审稿/review_report.json",
            return_stage=item.get("return_to_stage") or "",
            recommended_skill=item.get("recommended_skill") or "novel-review",
        )


def collect_score(tasks, root):
    path = os.path.join(root, "评分", "score_report.json")
    payload = load_json(path, {}) or {}
    decision = (payload.get("production_decision") or {}).get("decision")
    verdict = payload.get("verdict")
    if decision in {"revise", "kill"} or verdict in {"大改", "弃稿重立"}:
        add_task(
            tasks,
            phase="editorial_assessment",
            priority="P0",
            title=f"评分结论需编辑决策：{verdict or decision}",
            reason=(payload.get("production_decision") or {}).get("reason") or payload.get("rewrite_roi") or "",
            source="评分/score_report.json",
            return_stage=(payload.get("next_actions") or [{}])[0].get("return_to_stage", ""),
            recommended_skill=(payload.get("next_actions") or [{}])[0].get("recommended_skill", "novel-score"),
        )


def collect_reader_feedback(tasks, root):
    payload = load_json(os.path.join(root, "评分", "reader_telemetry_summary.json"), {}) or {}
    for chapter in payload.get("weakest_chapters") or []:
        add_task(
            tasks,
            phase="developmental_edit",
            priority="P1",
            chapter=chapter,
            title=f"真实读者掉点章节复盘：第{chapter}章",
            reason="真实读者反馈标记为 weakest_chapters；先用 novel-balance/novel-review 定因，再改结构或场景。",
            source="评分/reader_telemetry_summary.json",
            return_stage="review",
            recommended_skill="novel-feedback",
        )


def collect_scene_cards(tasks, root):
    payload = load_json(os.path.join(root, "设定", "scene_cards.json"), {}) or {}
    for card in payload.get("scenes") or []:
        missing = [k for k in ("pov", "desire", "obstacle", "conflict", "turn", "value_shift") if not str(card.get(k) or "").strip()]
        if missing:
            add_task(
                tasks,
                phase="developmental_edit",
                priority="P1",
                chapter=card.get("chapter"),
                title=f"场景卡缺关键戏剧功能：{card.get('id') or 'scene'}",
                reason="缺字段：" + "、".join(missing),
                source="设定/scene_cards.json",
                return_stage="outline",
                recommended_skill="novel-craft",
            )


def build_plan(root):
    tasks = []
    collect_score(tasks, root)
    collect_review(tasks, root)
    collect_reader_feedback(tasks, root)
    collect_scene_cards(tasks, root)
    tasks.sort(key=lambda t: (PHASE_ORDER.get(t["phase"], 9), t["priority"], t.get("chapter") or 10**9, t["id"]))
    for idx, task in enumerate(tasks, 1):
        task["id"] = f"EDIT-{idx:03d}"
    return {
        "schema_version": 1,
        "kind": "novel_edit_plan",
        "project_root": os.path.abspath(root),
        "generated_at": date.today().isoformat(),
        "phases": list(PHASE_ORDER),
        "tasks": tasks,
    }


def write_markdown(path, plan):
    lines = [
        "# 编辑计划",
        "",
        f"- 生成日期：{plan['generated_at']}",
        f"- 任务数：{len(plan['tasks'])}",
        "",
    ]
    for phase in plan["phases"]:
        phase_tasks = [t for t in plan["tasks"] if t["phase"] == phase]
        if not phase_tasks:
            continue
        lines.append(f"## {phase}")
        for t in phase_tasks:
            chapter = f"第{t['chapter']}章 · " if t.get("chapter") else ""
            lines.append(f"- [{t['priority']}] {t['id']} {chapter}{t['title']}")
            if t.get("reason"):
                lines.append(f"  - 原因：{t['reason']}")
            lines.append(f"  - 来源：{t['source']}；回流：{t['recommended_skill']} / {t['return_to_stage'] or 'edit'}")
        lines.append("")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def main():
    ap = argparse.ArgumentParser(description="生成 novel 分层编辑计划")
    ap.add_argument("project_root")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    plan = build_plan(root)
    out_json = os.path.join(root, "修订", "edit_plan.json")
    out_md = os.path.join(root, "修订", "编辑计划.md")
    write_json(out_json, plan)
    write_markdown(out_md, plan)
    print(f"[ok] edit plan: {out_md}")
    print(f"[summary] tasks={len(plan['tasks'])}")


if __name__ == "__main__":
    main()
