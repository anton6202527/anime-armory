#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a layered editing plan from existing novel QA artifacts.

This is deterministic scaffolding: it reads review/score/balance/reader
telemetry/scene-card artifacts and writes an edit plan. It does not rewrite the
manuscript.
"""
import argparse
import glob
import json
import os
import re
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
    if text in {"p0", "p1", "p2", "p3"}:
        return text.upper()
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


def chapter_from_text(value):
    if isinstance(value, int):
        return value
    text = str(value or "")
    match = re.search(r"第0*(\d+)章|chapter[_\s-]?0*(\d+)", text, flags=re.I)
    if match:
        return int(match.group(1) or match.group(2))
    match = re.search(r"0*(\d+)", text)
    return int(match.group(1)) if match else None


def is_ok_verdict(value):
    text = str(value or "").strip()
    return not text or text in {"ok", "OK", "正常", "balanced", "pass"} or text.startswith("✅")


def collect_revision_plan(tasks, root):
    path = os.path.join(root, "修订", "revision_plan.json")
    payload = load_json(path, {}) or {}
    if not isinstance(payload, dict):
        return
    for item in payload.get("tasks") or []:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or "统一修订计划任务待编辑落地"
        phase = phase_for_dimension(
            f"{title} {item.get('source') or ''} {item.get('recommended_skill') or ''}",
            item.get("return_to_stage") or "",
        )
        add_task(
            tasks,
            phase=phase,
            priority=severity_priority(item.get("priority")),
            chapter=item.get("chapter"),
            title=title,
            reason=item.get("reason") or "来自统一修订计划，需在编辑层决定处理顺序与改稿方式。",
            source="修订/revision_plan.json",
            return_stage=item.get("return_to_stage") or "",
            recommended_skill=item.get("recommended_skill") or "novel-craft",
        )


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


def collect_balance(tasks, root):
    path = os.path.join(root, "评分", "pacing_signals.json")
    payload = load_json(path, {}) or {}
    if isinstance(payload, dict) and payload.get("kind") == "novel_pacing_signals":
        for idx, row in enumerate(payload.get("chapters") or [], 1):
            if not isinstance(row, dict):
                continue
            verdict = row.get("verdict") or row.get("status")
            if is_ok_verdict(verdict):
                continue
            chapter = chapter_from_text(row.get("chapter") or row.get("chapter_label")) or idx
            add_task(
                tasks,
                phase="developmental_edit",
                priority="P1" if any(k in str(verdict) for k in ("阻断", "坍塌", "注水", "过快", "过慢", "弱")) else "P2",
                chapter=chapter,
                title=f"节奏诊断转编辑动作：第{chapter}章 {verdict}",
                reason=row.get("reason") or row.get("diagnosis") or row.get("note") or "",
                source="评分/pacing_signals.json",
                return_stage="balance",
                recommended_skill="novel-balance",
            )
        ending_risk = payload.get("烂尾预警") or payload.get("ending_risk_warnings")
        if isinstance(ending_risk, dict):
            overdue = int(ending_risk.get("超期伏笔数") or ending_risk.get("overdue_count") or 0)
            blocking = int(ending_risk.get("烂尾级超期") or ending_risk.get("blocking") or 0)
            if overdue or blocking:
                add_task(
                    tasks,
                    phase="developmental_edit",
                    priority="P1" if blocking else "P2",
                    chapter=chapter_from_text(ending_risk.get("through_chapter")),
                    title=f"伏笔回收编辑排程：超期 {overdue} 条，烂尾级 {blocking} 条",
                    reason=f"伏笔回收率：{ending_risk.get('回收率')}",
                    source="评分/pacing_signals.json",
                    return_stage="balance",
                    recommended_skill="novel-balance",
                )
    for balance_path in sorted(glob.glob(os.path.join(root, "审稿", "*balance*.json")) + glob.glob(os.path.join(root, "评分", "*heatmap*.json"))):
        payload = load_json(balance_path, {}) or {}
        if not isinstance(payload, dict):
            continue
        for item in payload.get("findings") or payload.get("alerts") or []:
            if not isinstance(item, dict):
                continue
            title = item.get("message") or item.get("problem") or "节奏/结构问题待编辑处理"
            add_task(
                tasks,
                phase=phase_for_dimension(title, item.get("return_to_stage") or "balance"),
                priority="P1" if item.get("blocking") else "P2",
                chapter=chapter_from_text(item.get("chapter") or item.get("path")),
                title=title,
                reason=item.get("reason") or "",
                source=os.path.relpath(balance_path, root),
                return_stage=item.get("return_to_stage") or "balance",
                recommended_skill=item.get("recommended_skill") or "novel-balance",
            )


def collect_reader_panel(tasks, root):
    payload = load_json(os.path.join(root, "评分", "reader_panel_signals.json"), {}) or {}
    if not isinstance(payload, dict):
        return
    chapters = payload.get("chapters_read") or []
    chapter = chapters[0] if len(chapters) == 1 else None
    retention = payload.get("retention_prior")
    hook = payload.get("hook_strength")
    if payload.get("signal_only") is True or payload.get("analysis_mode") == "signal_only":
        add_task(
            tasks,
            phase="editorial_assessment",
            priority="P2",
            chapter=chapter,
            title="模拟读者信号仅作低权重留存先验",
            reason="qualitative_completed=false；人格心声/弃书点未补完前不能当完整试读结论。",
            source="评分/reader_panel_signals.json",
            return_stage="simulate",
            recommended_skill="novel-simulate",
        )
    if isinstance(retention, (int, float)) and retention < 0.45:
        add_task(
            tasks,
            phase="developmental_edit",
            priority="P1",
            chapter=chapter,
            title=f"模拟留存先验偏低：{retention}",
            reason=f"hook_strength={hook}; 先复核钩子、爽点密度和弃书点，再回到结构/场景层改稿。",
            source="评分/reader_panel_signals.json",
            return_stage="simulate",
            recommended_skill="novel-simulate",
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
        character_missing = [
            k for k in ("want", "need", "misbelief", "fear", "tactic", "choice_cost")
            if not str(card.get(k) or "").strip()
        ]
        if character_missing:
            add_task(
                tasks,
                phase="developmental_edit",
                priority="P2",
                chapter=card.get("chapter"),
                title=f"补人物内驱字段：{card.get('id') or 'scene'}",
                reason="缺字段：" + "、".join(character_missing) + "；人物容易变成剧情工具人。",
                source="设定/scene_cards.json",
                return_stage="scene_cards",
                recommended_skill="novel-craft",
            )


def dedupe_tasks(tasks):
    seen = set()
    out = []
    for task in tasks:
        key = (
            task.get("phase"),
            task.get("chapter"),
            task.get("title"),
            task.get("recommended_skill"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(task)
    return out


def build_plan(root):
    tasks = []
    collect_revision_plan(tasks, root)
    collect_score(tasks, root)
    collect_review(tasks, root)
    collect_balance(tasks, root)
    collect_reader_feedback(tasks, root)
    collect_reader_panel(tasks, root)
    collect_scene_cards(tasks, root)
    tasks.sort(key=lambda t: (PHASE_ORDER.get(t["phase"], 9), t["priority"], t.get("chapter") or 10**9, t["id"]))
    tasks = dedupe_tasks(tasks)
    for idx, task in enumerate(tasks, 1):
        task["id"] = f"EDIT-{idx:03d}"
    return {
        "schema_version": 1,
        "kind": "novel_edit_plan",
        "project_root": os.path.abspath(root),
        "generated_at": date.today().isoformat(),
        "inputs": {
            "revision_plan": os.path.exists(os.path.join(root, "修订", "revision_plan.json")),
            "review_report": os.path.exists(os.path.join(root, "审稿", "review_report.json")),
            "score_report": os.path.exists(os.path.join(root, "评分", "score_report.json")),
            "pacing_signals": os.path.exists(os.path.join(root, "评分", "pacing_signals.json")),
            "reader_telemetry_summary": os.path.exists(os.path.join(root, "评分", "reader_telemetry_summary.json")),
            "reader_panel_signals": os.path.exists(os.path.join(root, "评分", "reader_panel_signals.json")),
            "scene_cards": os.path.exists(os.path.join(root, "设定", "scene_cards.json")),
        },
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
    lines.extend([
        "## 执行顺序",
        "- 先处理 `editorial_assessment` 与 `developmental_edit`，结构未定稿前不要做大规模润句。",
        "- 每章进入 `line_edit` 前，先生成该章 line edit packet，按场景目的、人物内驱、观察素材、审美样本逐项改。",
        "- 改完一章后记录 before/after 与改动理由，再回跑 `novel-review` 或对应机检。",
        "",
    ])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def _read_jsonl(path, limit=5):
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            if len(out) >= limit:
                break
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


def write_line_edit_packet(root, plan, chapter):
    scene_payload = load_json(os.path.join(root, "设定", "scene_cards.json"), {}) or {}
    scenes = [
        s for s in scene_payload.get("scenes") or []
        if int(s.get("chapter") or 0) == chapter
    ]
    aesthetic = load_json(os.path.join(root, "设定", "aesthetic_bank.json"), {}) or {}
    aesthetic_samples = (aesthetic.get("samples") or [])[:5]
    observations = _read_jsonl(os.path.join(root, "素材", "观察札记.jsonl"), limit=8)
    chapter_tasks = [t for t in plan["tasks"] if t.get("chapter") in (chapter, str(chapter), None)]
    out = os.path.join(root, "修订", f"第{chapter:02d}章_line_edit_packet.md")
    lines = [
        f"# 第{chapter:02d}章 Line Edit Packet",
        "",
        "## 本章编辑目标",
        "- 先确认结构任务是否已处理；若仍有 P0/P1 结构问题，暂停行文润色。",
        "- 本轮只做会提升人物、场景、对白、五感、语言辨识度的改动；每处改动写明理由。",
        "",
        "## 关联编辑任务",
    ]
    if chapter_tasks:
        for task in chapter_tasks:
            lines.append(f"- [{task['priority']}] {task['id']} {task['title']}（来源：{task['source']}）")
    else:
        lines.append("- 暂无显式任务；按场景卡和审美样本做主动精修。")
    lines.extend(["", "## 场景卡检查"])
    if scenes:
        for scene in scenes:
            lines.extend([
                f"### {scene.get('id')}",
                f"- POV/地点：{scene.get('pov') or '待补'} / {scene.get('location') or '待补'}",
                f"- 欲望/阻碍：{scene.get('desire') or '待补'} / {scene.get('obstacle') or '待补'}",
                f"- 转折/价值变化：{scene.get('turn') or '待补'} / {scene.get('value_shift') or '待补'}",
                f"- 人物引擎：want={scene.get('want') or '待补'}；need={scene.get('need') or '待补'}；fear={scene.get('fear') or '待补'}；tactic={scene.get('tactic') or '待补'}；cost={scene.get('choice_cost') or '待补'}",
                f"- 潜台词/五感：{scene.get('subtext') or '待补'} / {scene.get('sensory_anchor') or '待补'}",
                "",
            ])
    else:
        lines.append("- 未找到本章 scene cards；建议先跑 `scene_cards.py scaffold/check`。")
    lines.extend(["", "## 可用观察素材"])
    if observations:
        for obs in observations:
            lines.append(f"- {obs.get('id')} [{obs.get('domain')}] {obs.get('text')}")
    else:
        lines.append("- 未找到观察素材；若本章生活感薄，可先走 `novel-observe`。")
    lines.extend(["", "## 正向审美对照"])
    if aesthetic_samples:
        for sample in aesthetic_samples:
            lines.append(f"- {sample.get('sample_id')}：{sample.get('transfer_rule')}（禁抄：{sample.get('anti_copy_note')}）")
    else:
        lines.append("- 未找到审美样本；可用 `novel-aesthetic` 登记项目 Demo 高光或授权/公版样本。")
    lines.extend([
        "",
        "## 改稿记录",
        "| 位置 | 原问题 | 改法 | 保留理由 | 回测项 |",
        "|---|---|---|---|---|",
        "|  |  |  |  |  |",
    ])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(description="生成 novel 分层编辑计划")
    ap.add_argument("project_root")
    ap.add_argument("--line-packet", type=int, help="同时生成指定章节的 line edit packet")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    plan = build_plan(root)
    out_json = os.path.join(root, "修订", "edit_plan.json")
    out_md = os.path.join(root, "修订", "编辑计划.md")
    write_json(out_json, plan)
    write_markdown(out_md, plan)
    print(f"[ok] edit plan: {out_md}")
    if args.line_packet:
        packet = write_line_edit_packet(root, plan, args.line_packet)
        print(f"[ok] line edit packet: {packet}")
    print(f"[summary] tasks={len(plan['tasks'])}")


if __name__ == "__main__":
    main()
