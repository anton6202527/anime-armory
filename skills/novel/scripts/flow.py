#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flow.py — novel 管线指挥官：分析当前进度，检测操作摩擦，建议下一步行动。

它不仅读取 _进度.md 的打钩状态，还会扫描磁盘产物（任务包、状态增量、对账单）
来判断项目是否真正处于“可推进一步”的状态。
"""
import os
import sys
import json
import re
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from novel_route import summarize
from novel_contract import is_long_arc_project
from project_io import load_project_settings

_STAGE_TABLE_MARKERS = ("novel-derived-stage-table", "novel-create-stage-table", "novel-import-stage-table")

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def get_task_packets(root, ch_num):
    task_dir = os.path.join(root, "写作任务")
    if not os.path.isdir(task_dir):
        return []
    packets = []
    for f in os.listdir(task_dir):
        if f.startswith(f"第{ch_num:02d}章") and f.endswith(".md"):
            packets.append(f)
    return packets


def batch_review_interval(settings, meta):
    value = settings.get("小批回扫间隔") or meta.get("batch_review_interval") or meta.get("review_interval") or "5章"
    text = str(value or "").strip().lower()
    if text in {"", "关闭", "off", "none", "0", "0章"}:
        return 0
    match = re.search(r"(\d+)", text)
    return max(1, int(match.group(1))) if match else 5


def batch_review_window(ch_num, interval, meta):
    if interval <= 0:
        return None
    target = int(meta.get("target_chapters") or 0)
    if ch_num % interval == 0 or (target and ch_num == target and ch_num % interval != 0):
        return ((ch_num - 1) // interval) * interval + 1, ch_num
    next_due = ((ch_num - 1) // interval + 1) * interval
    return None, min(next_due, target) if target else next_due


def arc_window_for_chapter(ch_num, interval, meta):
    interval = interval or 5
    target = int(meta.get("target_chapters") or 0)
    start = ((ch_num - 1) // interval) * interval + 1
    end = start + interval - 1
    if target:
        end = min(end, target)
    return start, end


def long_arc_mode(settings, meta):
    # 单一真值源在 novel_contract.is_long_arc_project（flow 与 qa_gate 共用）。
    return is_long_arc_project(meta, settings)


REVISION_SIGNAL_RELS = (
    "审稿/review_report.json",
    "评分/score_report.json",
    "评分/pacing_signals.json",
    "评分/reader_telemetry_summary.json",
    "评分/reader_panel_signals.json",
    "评分/market_evidence_tasks.json",
    "评分/market_evidence_jobs.json",
)


def revision_plan_hint(root):
    sources = [os.path.join(root, rel) for rel in REVISION_SIGNAL_RELS if os.path.exists(os.path.join(root, rel))]
    if not sources:
        return ""
    plan = os.path.join(root, "修订", "revision_plan.json")
    latest_source = max(os.path.getmtime(path) for path in sources)
    if not os.path.exists(plan):
        reason = "已有审稿/评分/反馈信号，但缺少统一修订计划"
    elif os.path.getmtime(plan) < latest_source:
        reason = "统一修订计划早于最新审稿/评分/反馈信号"
    else:
        return ""
    return f"{reason}：python3 skills/novel-craft/scripts/revision_planner.py \"{root}\""


def is_stage_checklist(root):
    path = os.path.join(root, "_进度.md")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return False
    return any(marker in text for marker in _STAGE_TABLE_MARKERS)

def run_stage_checklist_flow(root):
    script = os.path.join(_SKILLS, "novel-craft", "scripts", "progress.py")
    print("📍 当前项目使用同构阶段清单进度；转交 novel-craft progress reader。")
    result = subprocess.run([sys.executable, script, root])
    sys.exit(result.returncode)

def main():
    if len(sys.argv) < 2:
        print("用法: flow.py <作品根>"); sys.exit(1)
        
    root = os.path.abspath(sys.argv[1].rstrip('/'))
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}"); sys.exit(1)

    meta = load_json(os.path.join(root, "_meta.json"))
    settings = load_project_settings(root)
    draft_workflow = (
        settings.get("小说生成工作流")
        or meta.get("draft_workflow")
        or meta.get("writing_workflow")
        or "默认单步"
    )
    live_check = "边写边自检" in str(draft_workflow)
    review_interval = batch_review_interval(settings, meta)
    if is_stage_checklist(root):
        run_stage_checklist_flow(root)

    res = summarize(root)
    if "error" in res:
        print(f"[err] 进度读取失败: {res['error']}"); sys.exit(1)

    first = res.get("first") # {"ch": "第01章", "label": "正文初稿", "skill": "...", ...}
    if not first:
        print("🎉 全部完结！"); return

    ch_text = first["ch"]
    ch_num = int(re.search(r"(\d+)", ch_text).group(1))
    stage_label = first["label"]
    
    print(f"📍 当前进度焦点：{ch_text}「{stage_label}」")
    print(f"⚙️ 小说生成工作流：{draft_workflow}")
    
    # 状态哨兵
    advice = []
    blockers = []
    
    # 1. Demo Gate 检查
    demo_count = int(meta.get("demo_chapters") or 0)
    if ch_num > demo_count and demo_count > 0:
        gate = load_json(os.path.join(root, "审稿", "demo_gate.json"))
        if gate.get("status") != "passed":
            blockers.append(f"🔴 Demo Gate 未通过（当前第 {ch_num} 章 > Demo 数 {demo_count}）")
            advice.append(f"运行 novel-review 审阅前 {demo_count} 章并生成 demo_gate.json。")

    # 2. 状态增量与对账检查
    if stage_label in ["机检", "审稿", "评分"]:
        delta_path = os.path.join(root, "审稿", f"state_delta_{ch_text}.json")
        if not os.path.exists(delta_path):
            blockers.append(f"🔴 缺失本章状态增量 (State Delta)：{delta_path}")
            advice.append(f"请阅读该章内容，提取新事实/人物变动/伏笔，写入 {delta_path}。")
        else:
            # 检查是否已合并入 ledger
            ledger = load_json(os.path.join(root, "审稿", "state_ledger.json"))
            c_key = f"chapter_{ch_num:02d}"
            if c_key not in ledger.get("chapter_deltas", {}):
                blockers.append(f"🟡 状态增量尚未合并入 Master Ledger")
                advice.append(f"运行对账并合并：python3 skills/novel-craft/scripts/reconcile_ledger.py \"{root}\" --chapter {ch_num} --merge --verified <结论.json>")

    # 3. 任务包检查 (如果是正文初稿阶段)
    if stage_label == "正文初稿":
        if long_arc_mode(settings, meta):
            start, end = arc_window_for_chapter(ch_num, review_interval or 5, meta)
            arc_plan = os.path.join(root, "审稿", f"arc_plan_第{start:02d}-{end:02d}章.json")
            if not os.path.exists(arc_plan):
                advice.append(
                    f"长篇弧段包：先生成第 {start:02d}-{end:02d} 章弧段计划："
                    f"python3 skills/novel-craft/scripts/arc_packets.py \"{root}\" --arc {start}-{end}"
                )
        packets = get_task_packets(root, ch_num)
        if not packets:
            advice.append(f"生成写作任务包：python3 skills/novel-craft/scripts/draft_packets.py \"{root}\" --chapter {ch_num}")
        else:
            advice.append(f"检测到现有任务包：{', '.join(packets)}。请按任务包要求完成写作。")
            if live_check:
                conclusion_path = os.path.join(root, "审稿", f"state_verify_{ch_text}.json")
                advice.append(
                    f"边写边自检：正文、审稿/state_delta_{ch_text}.json 与对账结论 {conclusion_path} 落盘后，执行 "
                    f"python3 skills/novel/scripts/post_write.py \"{root}\" --chapter {ch_text} --conclusion \"{conclusion_path}\""
                )
                window = batch_review_window(ch_num, review_interval, meta)
                if window and window[0] is not None:
                    start, end = window
                    advice.append(
                        f"小批回扫：本章自检通过后跑第 {start:02d}-{end:02d} 章 review："
                        f"python3 skills/novel-review/scripts/mechanical_check.py \"{root}\" "
                        f"--range {start}-{end} --json-out \"{root}/审稿/batch_mechanical_第{start:02d}-{end:02d}章.json\""
                    )
                elif window:
                    _unused, next_due = window
                    advice.append(f"小批回扫节奏：每 {review_interval} 章一次，下一次预计第 {next_due:02d} 章写后触发。")

    if long_arc_mode(settings, meta) and stage_label in ["机检", "审稿", "评分"]:
        start, end = arc_window_for_chapter(ch_num, review_interval or 5, meta)
        if ch_num == end:
            arc_report = os.path.join(root, "审稿", f"arc_gate_第{start:02d}-{end:02d}章.json")
            if not os.path.exists(arc_report):
                advice.append(
                    f"长篇弧段 gate：本窗口到第 {end:02d} 章，建议跑 "
                    f"python3 skills/novel-review/scripts/arc_gate.py \"{root}\" --arc {start}-{end}"
                )

    revision_hint = revision_plan_hint(root)
    if revision_hint:
        advice.append(revision_hint)

    # 输出
    if blockers:
        print("\n🚧 阻断项：")
        for b in blockers:
            print(f"  {b}")

    # 已审出但未消除的建议级问题（🟡）——路由不回炉，但不能静默吞掉。
    flagged = res.get("flagged") or []
    if flagged:
        print("\n🟡 已记录、未消除的建议级问题（不阻断，但请确认是已接受还是待修）：")
        for f in flagged:
            print(f"  - {f['ch']}「{f['col']}」：{f['value']}")
            
    print("\n💡 建议行动：")
    if advice:
        for a in advice:
            print(f"  - {a}")
    else:
        cmd = first.get("cmd", "").format(root=root, ch=ch_text)
        print(f"  - 按照进度建议执行：{cmd}")

    if live_check:
        print(f"\n[提示] 当前已选择 边写边自检；post_write 必须带 --conclusion 才会合并账本并标记进度。")
    else:
        print(f"\n[提示] 运行 post_write 脚本并带 --conclusion，可在合并账本后自动勾选进度并触发百科/哨兵/力量体系检查；也可在 `_设置.md` 选择 `小说生成工作流：边写边自检`。")

if __name__ == "__main__":
    main()
