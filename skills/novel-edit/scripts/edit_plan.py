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


def append_jsonl(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path):
    out = []
    if not os.path.isfile(path):
        return out
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
            lines.append(f"  - 来源：{t.get('source') or 'edit_plan'}；回流：{t.get('recommended_skill') or 'novel-edit'} / {t.get('return_to_stage') or 'edit'}")
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


def _phase_counts(plan):
    counts = {phase: 0 for phase in plan["phases"]}
    for task in plan["tasks"]:
        counts[task["phase"]] = counts.get(task["phase"], 0) + 1
    return counts


def write_editorial_letter(path, plan):
    counts = _phase_counts(plan)
    top_tasks = [t for t in plan["tasks"] if t["priority"] in {"P0", "P1"}][:12]
    lines = [
        "# Editorial Letter",
        "",
        f"- 生成日期：{plan['generated_at']}",
        f"- 项目：{plan['project_root']}",
        "",
        "## 总体判断",
        "",
        "这封主编信只基于已落盘的 review / score / pacing / reader / scene-card 证据生成。它不替作者做文学取舍，作用是把当前稿件需要先解决的结构、人物、节奏和读者承诺问题排成编辑顺序。",
        "",
        "## 编辑轮次概览",
        "",
    ]
    for phase in plan["phases"]:
        lines.append(f"- `{phase}`：{counts.get(phase, 0)} 项")
    lines.extend(["", "## P0/P1 优先处理项", ""])
    if top_tasks:
        for task in top_tasks:
            chapter = f"第{task['chapter']}章 · " if task.get("chapter") else ""
            lines.append(f"- [{task['priority']}] {task['id']} {chapter}{task['title']}（来源：{task['source']}）")
            if task.get("reason"):
                lines.append(f"  - 编辑理由：{task['reason']}")
    else:
        lines.append("- 暂无 P0/P1 编辑任务；可进入 line edit / proofread。")
    lines.extend([
        "",
        "## 建议处理顺序",
        "",
        "1. 先裁决 `editorial_assessment`：是否继续、重开、换定位或重排读者契约。",
        "2. 再执行 `developmental_edit`：主线、人物动机、场景顺序、伏笔回收和节奏。",
        "3. 结构稳定后进入 `line_edit`：对白、五感、句式、文风、去机械感。",
        "4. 最后做 `copyedit_proofread`：错字、标点、术语、称谓、格式和导出检查。",
        "",
        "## 回测要求",
        "",
        "- 结构级改动后回跑 `novel-review` / `novel-score`。",
        "- 行文级改动后回跑 `mechanical_check.py`、文风漂移检查和必要的读者复测。",
        "- 发布前重新生成 release manifest，确保所有报告绑定当前正文 hash。",
    ])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def _extract_markdown_terms(path):
    if not os.path.exists(path):
        return []
    terms = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                term = line.lstrip("#").strip()
                if term and len(term) <= 40:
                    terms.append(term)
            elif line.startswith(("-", "*")) and ("：" in line or ":" in line):
                term = re.split(r"[:：]", line.lstrip("-* ").strip(), maxsplit=1)[0].strip()
                if term and 1 <= len(term) <= 20:
                    terms.append(term)
    out = []
    for term in terms:
        if term not in out:
            out.append(term)
    return out[:80]


def write_style_sheet(path, root):
    alias = load_json(os.path.join(root, "设定", "角色别名.json"), {}) or {}
    aliases = []
    if isinstance(alias, dict):
        for key in ("aliases", "character_aliases", "confirmed_aliases"):
            value = alias.get(key)
            if isinstance(value, dict):
                for canonical, vals in value.items():
                    aliases.append((canonical, vals if isinstance(vals, list) else [vals]))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        aliases.append((item.get("canonical") or item.get("name") or "", item.get("aliases") or []))
    terms = []
    for rel in ("设定/角色卡.md", "设定/世界观.md", "设定/设定圣经.md", "设定/章纲.md"):
        terms.extend(_extract_markdown_terms(os.path.join(root, rel)))
    unique_terms = []
    for term in terms:
        if term and term not in unique_terms:
            unique_terms.append(term)
    settings_text = ""
    settings_path = os.path.join(root, "_设置.md")
    if os.path.exists(settings_path):
        settings_text = open(settings_path, encoding="utf-8", errors="replace").read()
    lines = [
        "# Style Sheet",
        "",
        f"- 生成日期：{date.today().isoformat()}",
        "",
        "## 项目口径",
        "",
        "- 文本主创模式：见 `_设置.md`；若目标平台对 AI 正文敏感，终稿需保持人类主创或 AI 辅助留痕。",
        "- 平台/用途：以 `_设置.md` 与 `_meta.json` 为准；所有术语、称谓、章节标题和敏感表达按该口径统一。",
        "",
        "## 设置摘录",
        "",
    ]
    if settings_text.strip():
        for line in settings_text.splitlines()[:40]:
            if line.strip():
                lines.append(f"- {line.strip()}")
    else:
        lines.append("- 未找到 `_设置.md` 或内容为空。")
    lines.extend(["", "## 角色称谓与别名", ""])
    if aliases:
        for canonical, vals in aliases:
            vals = [str(v) for v in vals if str(v).strip()]
            lines.append(f"- {canonical}：{', '.join(vals) if vals else '待补'}")
    else:
        lines.append("- 未找到 confirmed 角色别名表；建议先跑 `novel-wiki/scripts/alias_scaffold.py` 并人工确认。")
    lines.extend(["", "## 术语与专名候选", ""])
    if unique_terms:
        for term in unique_terms[:60]:
            lines.append(f"- {term}")
    else:
        lines.append("- 待补：从角色卡、世界观、设定圣经、章纲中确认专名和术语。")
    lines.extend([
        "",
        "## Copyedit 统一规则",
        "",
        "- 同一人物在同一叙述距离下称谓保持一致；切换称谓必须服务关系变化或 POV。",
        "- 数字、日期、货币、境界、等级、系统面板字段按设定圣经统一。",
        "- 章节标题、标点、引号和空行按导出目标统一。",
        "- 不把未核验证据写成旁白确定事实；专业事实必须回查 `资料/research_sources.json`。",
        "",
        "## Proofread 最后核对",
        "",
        "- 逐章标题与目录一致。",
        "- 术语、称谓、时间线、伏笔状态和 AI 使用披露与 release manifest 同版。",
    ])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def write_proof_checklist(path, plan):
    lines = [
        "# Proof Checklist",
        "",
        f"- 生成日期：{plan['generated_at']}",
        "",
        "| 项 | 状态 | 证据/命令 | 备注 |",
        "|---|---|---|---|",
        "| 章节标题与导出目录一致 | ⬜ | `python3 skills/novel-craft/scripts/export.py <作品根> --formats txt,docx,outline` |  |",
        "| review report 绑定当前正文 hash | ⬜ | `python3 skills/novel-craft/scripts/report_gate.py <作品根>` |  |",
        "| score report 绑定当前正文 hash | ⬜ | `python3 skills/novel-score/scripts/score.py <作品根> --scope full` | 商业/平台项目必做 |",
        "| 专业资料包未过期 | ⬜ | `python3 skills/novel-research/scripts/research_pack.py check <作品根>` | 高风险过期阻断 |",
        "| P0/P1 编辑任务已关闭 | ⬜ | `修订/edit_plan.json` | open P0/P1 会阻断作者成书流程进入 release |",
        "| 术语/称谓/style sheet 已核对 | ⬜ | `python3 skills/novel-edit/scripts/style_sheet_check.py <作品根> --write` |  |",
        "| AI 使用披露完整 | ⬜ | `python3 skills/novel-craft/scripts/ai_usage.py <作品根> ...` | 发布/平台/出海必做 |",
        "| 合规 profile 最新 | ⬜ | `python3 skills/novel-craft/scripts/compliance_profile.py <作品根> --write` | KDP/中国公开发布/微短剧/出海必做 |",
        "| reader test plan / 真实反馈已处理 | ⬜ | `评分/reader_test_plan.json` / `评分/reader_telemetry_summary.json` | platform/KDP 发布缺真实反馈需 scoped waiver |",
        "| release manifest 就绪 | ⬜ | `python3 skills/novel-craft/scripts/release_manifest.py <作品根> --release-name v1` |  |",
        "",
        "## 校样原则",
        "- Proofread 是最后阶段；结构或行文仍会大改时不要提前做终校。",
        "- 任何正文改动后，旧 review/score/release manifest 都可能 stale，必须重跑对应检查。",
    ]
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


def close_edit_task(root, task_id, *, status="fixed", note="", actor="editor"):
    path = os.path.join(root, "修订", "edit_plan.json")
    plan = load_json(path, {}) or {}
    if not isinstance(plan, dict) or not isinstance(plan.get("tasks"), list):
        raise ValueError("缺少 修订/edit_plan.json 或 tasks 格式无效；先跑 edit_plan.py 生成编辑计划。")
    plan.setdefault("generated_at", date.today().isoformat())
    plan.setdefault("project_root", os.path.abspath(root))
    plan.setdefault("phases", list(PHASE_ORDER))
    target = None
    for task in plan["tasks"]:
        if isinstance(task, dict) and task.get("id") == task_id:
            target = task
            break
    if target is None:
        raise ValueError(f"unknown edit task id: {task_id}")
    target["status"] = status
    target["closed_at"] = date.today().isoformat() if status in {"fixed", "accepted", "waived", "closed", "done", "resolved"} else ""
    target["closed_by"] = actor
    target["closure_note"] = note
    plan["updated_at"] = date.today().isoformat()
    write_json(path, plan)
    write_markdown(os.path.join(root, "修订", "编辑计划.md"), plan)
    append_jsonl(os.path.join(root, "修订", "edit_task_closure.jsonl"), {
        "task_id": task_id,
        "status": status,
        "actor": actor,
        "note": note,
        "closed_at": target.get("closed_at") or date.today().isoformat(),
        "source": "novel-edit/scripts/edit_plan.py",
    })
    return target


def editor_queries_path(root):
    return os.path.join(root, "修订", "editor_queries.jsonl")


def next_query_id(root):
    records = read_jsonl(editor_queries_path(root))
    max_id = 0
    for record in records:
        raw = str(record.get("query_id") or "")
        m = re.search(r"EQ-(\d+)", raw)
        if m:
            max_id = max(max_id, int(m.group(1)))
    return f"EQ-{max_id + 1:03d}"


def add_editor_query(root, *, task_id="", question="", severity="P1", asker="editor"):
    if not question.strip():
        raise ValueError("--query 不能为空")
    payload = {
        "schema_version": 1,
        "kind": "novel_editor_query",
        "query_id": next_query_id(root),
        "task_id": task_id,
        "severity": severity,
        "question": question,
        "asker": asker,
        "status": "open",
        "created_at": date.today().isoformat(),
        "answered_at": "",
        "answer": "",
        "answer_by": "",
    }
    append_jsonl(editor_queries_path(root), payload)
    return payload


def answer_editor_query(root, query_id, *, answer="", actor="author", status="answered"):
    if not answer.strip():
        raise ValueError("--answer 不能为空")
    records = read_jsonl(editor_queries_path(root))
    found = False
    for record in records:
        if record.get("query_id") == query_id:
            record["answer"] = answer
            record["answer_by"] = actor
            record["status"] = status
            record["answered_at"] = date.today().isoformat()
            found = True
    if not found:
        raise ValueError(f"unknown editor query id: {query_id}")
    path = editor_queries_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return next(record for record in records if record.get("query_id") == query_id)


def open_editor_query_count(root):
    closed = {"answered", "accepted", "rejected", "resolved", "waived", "closed"}
    return sum(
        1 for record in read_jsonl(editor_queries_path(root))
        if str(record.get("status") or "open").lower() not in closed
    )


def main():
    ap = argparse.ArgumentParser(description="生成 novel 分层编辑计划")
    ap.add_argument("project_root")
    ap.add_argument("--line-packet", type=int, help="同时生成指定章节的 line edit packet")
    ap.add_argument("--close-task", default="", help="关闭/更新 edit_plan.json 中的任务 ID，如 EDIT-001")
    ap.add_argument("--status", choices=["open", "in_progress", "fixed", "accepted", "waived", "closed", "done", "resolved"], default="fixed")
    ap.add_argument("--note", default="", help="关闭任务时记录处理说明、before/after 或接受风险原因")
    ap.add_argument("--actor", default="editor")
    ap.add_argument("--query-task", default="", help="为某个 edit task 增加 editor query")
    ap.add_argument("--query", default="", help="editor query 问题正文")
    ap.add_argument("--query-severity", choices=["P0", "P1", "P2", "P3"], default="P1")
    ap.add_argument("--asker", default="editor")
    ap.add_argument("--answer-query", default="", help="回答 editor query ID，如 EQ-001")
    ap.add_argument("--answer", default="")
    ap.add_argument("--query-status", choices=["answered", "accepted", "rejected", "follow_up", "resolved", "closed"], default="answered")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if args.query_task or args.query:
        try:
            query = add_editor_query(root, task_id=args.query_task, question=args.query, severity=args.query_severity, asker=args.asker)
        except ValueError as exc:
            raise SystemExit(f"[err] {exc}")
        print(f"[ok] editor query added: {query['query_id']} status={query['status']}")
        print(f"[ok] query log: {editor_queries_path(root)}")
        return
    if args.answer_query:
        try:
            query = answer_editor_query(root, args.answer_query, answer=args.answer, actor=args.actor, status=args.query_status)
        except ValueError as exc:
            raise SystemExit(f"[err] {exc}")
        print(f"[ok] editor query updated: {query['query_id']} status={query.get('status')}")
        print(f"[ok] query log: {editor_queries_path(root)}")
        return
    if args.close_task:
        try:
            task = close_edit_task(root, args.close_task, status=args.status, note=args.note, actor=args.actor)
        except ValueError as exc:
            raise SystemExit(f"[err] {exc}")
        print(f"[ok] edit task updated: {task['id']} status={task.get('status')}")
        print(f"[ok] closure log: {os.path.join(root, '修订', 'edit_task_closure.jsonl')}")
        return
    plan = build_plan(root)
    out_json = os.path.join(root, "修订", "edit_plan.json")
    out_md = os.path.join(root, "修订", "编辑计划.md")
    write_json(out_json, plan)
    write_markdown(out_md, plan)
    write_editorial_letter(os.path.join(root, "修订", "editorial_letter.md"), plan)
    write_style_sheet(os.path.join(root, "修订", "style_sheet.md"), root)
    write_proof_checklist(os.path.join(root, "修订", "proof_checklist.md"), plan)
    print(f"[ok] edit plan: {out_md}")
    print(f"[ok] editorial letter: {os.path.join(root, '修订', 'editorial_letter.md')}")
    print(f"[ok] style sheet: {os.path.join(root, '修订', 'style_sheet.md')}")
    print(f"[ok] proof checklist: {os.path.join(root, '修订', 'proof_checklist.md')}")
    if args.line_packet:
        packet = write_line_edit_packet(root, plan, args.line_packet)
        print(f"[ok] line edit packet: {packet}")
    print(f"[summary] tasks={len(plan['tasks'])}")


if __name__ == "__main__":
    main()
