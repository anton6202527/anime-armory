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

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from novel_route import summarize, STAGES, is_done
from project_io import load_project_settings

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def is_n2d_bound(root, meta, settings):
    if meta.get("scale") == "漫剧" or meta.get("kind") == "漫剧源书":
        return True
    platform = str(settings.get("目标平台", "")).lower()
    if any(k in platform for k in ["漫剧", "短剧", "n2d"]):
        return True
    return False

def get_task_packets(root, ch_num):
    task_dir = os.path.join(root, "写作任务")
    if not os.path.isdir(task_dir):
        return []
    packets = []
    for f in os.listdir(task_dir):
        if f.startswith(f"第{ch_num:02d}章") and f.endswith(".md"):
            packets.append(f)
    return packets

def main():
    if len(sys.argv) < 2:
        print("用法: flow.py <作品根>"); sys.exit(1)
        
    root = os.path.abspath(sys.argv[1].rstrip('/'))
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}"); sys.exit(1)

    meta = load_json(os.path.join(root, "_meta.json"))
    settings = load_project_settings(root)
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

    # 3. N2D 就绪检查
    if is_n2d_bound(root, meta, settings) and stage_label in ["机检", "审稿"]:
        n2d_res = load_json(os.path.join(root, "审稿", "n2d_readiness.json"))
        # 简单查一下当前章是否有结果
        found_ch = False
        for c in n2d_res.get("chapters", []):
            if c["chapter"] == ch_num:
                found_ch = True; break
        if not found_ch:
            advice.append(f"建议运行 N2D 就绪机检：python3 skills/novel-review/scripts/n2d_readiness_check.py \"{root}\" --range {ch_num}")

    # 4. 任务包检查 (如果是正文初稿阶段)
    if stage_label == "正文初稿":
        packets = get_task_packets(root, ch_num)
        if not packets:
            advice.append(f"生成写作任务包：python3 skills/novel-craft/scripts/draft_packets.py \"{root}\" --chapter {ch_num}")
        else:
            advice.append(f"检测到现有任务包：{', '.join(packets)}。请按任务包要求完成写作。")

    # 输出
    if blockers:
        print("\n🚧 阻断项：")
        for b in blockers:
            print(f"  {b}")
            
    print("\n💡 建议行动：")
    if advice:
        for a in advice:
            print(f"  - {a}")
    else:
        cmd = first.get("cmd", "").format(root=root, ch=ch_text)
        print(f"  - 按照进度建议执行：{cmd}")

    print(f"\n[提示] 运行 post_write 脚本可自动勾选进度并触发百科/哨兵/N2D 检查。")

if __name__ == "__main__":
    main()
