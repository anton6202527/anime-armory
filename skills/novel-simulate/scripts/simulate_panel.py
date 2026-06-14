#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simulate_panel.py — 多代理人「模拟读者」试读（确定性信号 + LLM 定性骨架）

诚实分工（同家族 mechanical/script 哲学）：
  - 脚本算**确定性信号**：各人格关心的关键词密度、章末钩子强度、词汇多样性、套路命中。
  - 真正的"读者心声/弃书点"由 LLM 在交互节点按人格 prompt 读文本补全（报告里留占位）。
  - 另产一份机读 `评分/reader_panel_signals.json`（含 retention_prior），供 novel-score 当第一方留存先验。

  python3 simulate_panel.py <作品根> [--scope opening|chapter] [--chapter N] [--personas rookie,logic,emote,critic]

无第三方库，纯标准库。
"""
import os
import re
import json
import argparse
import sys
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.join(_SKILLS, "novel", "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from project_io import read_chapters  # noqa: E402

_CJK = r"一-鿿"

PERSONAS = {
    "rookie": {"name": "小白爽文党", "focus": "节奏/升级感/反杀/不憋屈",
               "kw": ["打脸", "逆袭", "碾压", "突破", "反杀", "升级", "扮猪", "装", "解气",
                      "翻盘", "吊打", "震惊", "废柴", "崛起", "无敌", "暴击", "斩杀"]},
    "logic": {"name": "逻辑考据党", "focus": "设定自洽/力量体系/无降智",
              "kw": ["因为", "所以", "原理", "规则", "体系", "推断", "逻辑", "境界",
                     "等级", "代价", "限制", "条件", "破绽", "证据", "推理", "布局"]},
    "emote": {"name": "情感/互动党", "focus": "人物弧光/CP/情感张力/金句",
              "kw": ["心疼", "温柔", "守护", "拥抱", "告白", "吃醋", "暧昧", "牵手",
                     "对视", "脸红", "心动", "眼泪", "微笑", "羁绊", "并肩", "回眸"]},
    "critic": {"name": "毒舌老书虫", "focus": "同质化套路/文笔/新意",
               "kw": ["退婚", "老爷爷", "戒指", "系统", "穿越", "重生", "神医", "赘婿",
                      "废柴逆袭", "扮猪吃虎", "纨绔", "圣女", "天才", "炼丹", "宗门"]},
}

HOOK_MARKERS = ["？", "?", "但", "却", "突然", "竟", "竟然", "居然", "不料", "没想到",
                "此时", "就在", "猛地", "骤然", "下一刻", "原来"]


def _cjk_len(s):
    return len(re.findall(f"[{_CJK}]", s))


def list_chapters(project):
    return [(idx, text) for idx, _path, text in read_chapters(project)]


def _density(text, kw):
    chars = _cjk_len(text) or 1
    hits = sum(text.count(w) for w in kw)
    return round(hits / chars * 1000, 2)  # 命中 / 千字


def _hook_strength(text):
    """取每章末尾 ~120 字看钩子标记密度，平均成 0-1。"""
    tails = []
    for seg in re.split(r"\n{2,}", text):
        seg = seg.strip()
        if not seg:
            continue
    # 用整章末段近似
    tail = text[-160:]
    hits = sum(tail.count(m) for m in HOOK_MARKERS)
    return min(1.0, round(hits / 5, 2))


def _lexical_diversity(text):
    grams = re.findall(f"[{_CJK}]{{4}}", text)
    if not grams:
        return 0.0
    return round(len(set(grams)) / len(grams), 3)


def analyze(project, scope, chapter, personas):
    chs = list_chapters(project)
    if not chs:
        return None
    if scope == "opening":
        target = chs[:3]
    else:
        target = [c for c in chs if c[0] == chapter] or chs[:1]
    text = "\n".join(t for _, t in target)

    persona_signals = {}
    for pid in personas:
        meta = PERSONAS[pid]
        persona_signals[pid] = {
            "name": meta["name"],
            "focus": meta["focus"],
            "keyword_density_per_kchar": _density(text, meta["kw"]),
        }

    hook = sum(_hook_strength(t) for _, t in target) / len(target)
    diversity = _lexical_diversity(text)
    cliche = _density(text, PERSONAS["critic"]["kw"])

    # 留存先验：爽点密度 + 钩子强度 为正，套路堆叠为负，归一到 0-1
    shuang = persona_signals.get("rookie", {}).get("keyword_density_per_kchar", 0)
    retention_prior = max(0.0, min(1.0, round(
        0.45 * min(shuang / 6, 1) + 0.35 * hook + 0.20 * min(diversity / 0.9, 1) - 0.10 * min(cliche / 5, 1), 3)))

    return {
        "analysis_mode": "signal_only",
        "signal_only": True,
        "qualitative_completed": False,
        "personas_completed": [],
        "agent_filled_at": None,
        "scope": scope,
        "chapters_read": [idx for idx, _ in target],
        "sampled_chars": _cjk_len(text),
        "personas": persona_signals,
        "hook_strength": round(hook, 3),
        "lexical_diversity": diversity,
        "cliche_density_per_kchar": cliche,
        "retention_prior": retention_prior,
        "note": "信号为确定性近似；弃书点/爽点捕获的定性判断由 LLM 按人格读文本补全",
    }


def write_report(project, sig, personas):
    date = datetime.now().strftime("%Y-%m-%d")
    rdir = os.path.join(project, "评分")
    os.makedirs(rdir, exist_ok=True)

    # 机读信号（供 novel-score 读）
    sig_path = os.path.join(rdir, "reader_panel_signals.json")
    with open(sig_path, "w", encoding="utf-8") as f:
        json.dump({"date": date, **sig}, f, ensure_ascii=False, indent=2)

    # 人读报告（LLM 填定性）
    md_path = os.path.join(rdir, f"读者试读反馈_{date}.md")
    lines = [
        f"# 读者试读反馈报告 — {date}",
        "",
        f"- 范围：{sig['scope']}（第 {sig['chapters_read']} 章）",
        f"- 完成状态：{sig.get('analysis_mode', 'signal_only')}；定性补全：{sig.get('qualitative_completed', False)}",
        f"- 留存先验（确定性近似）：**{sig['retention_prior']}** ｜ 钩子强度 {sig['hook_strength']} ｜ "
        f"词汇多样性 {sig['lexical_diversity']} ｜ 套路密度 {sig['cliche_density_per_kchar']}/千字",
        "",
        "> 下表「确定性信号」由脚本算出；「人格心声 / 弃书点」需 AI 代理按人格 prompt 读文本后补全（占位待填）。",
        "",
    ]
    for pid in personas:
        ps = sig["personas"][pid]
        lines += [
            f"## {ps['name']}（{ps['focus']}）",
            f"- 确定性信号：关注词密度 **{ps['keyword_density_per_kchar']}** / 千字",
            "- 【AI 代理填写】这类读者读完的直白心声：",
            "- 【AI 代理填写】最带劲的点（爽点捕获）：",
            "- 【AI 代理填写】最想点叉退出的点（弃书点预警）：",
            "",
        ]
    lines += [
        "## 综合（AI 代理填写）",
        "- 受众兼容度（哪类读者最买账）：",
        "- 弃书点 Top3 + 针对性改法：",
        "",
        "--- 报告骨架完，待 AI 代理补定性 ---",
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md_path, sig_path


def main():
    p = argparse.ArgumentParser(description="模拟读者试读（确定性信号 + LLM 定性骨架）")
    p.add_argument("project_path")
    p.add_argument("--scope", default="opening", choices=["opening", "chapter"])
    p.add_argument("--chapter", type=int, default=1)
    p.add_argument("--personas", default="rookie,logic,emote,critic")
    args = p.parse_args()

    personas = [x.strip() for x in args.personas.split(",") if x.strip() in PERSONAS]
    if not personas:
        personas = list(PERSONAS)
    sig = analyze(args.project_path, args.scope, args.chapter, personas)
    if sig is None:
        print(f"Error: {args.project_path}/章节 下没有可读章节")
        return
    md_path, sig_path = write_report(args.project_path, sig, personas)
    print(f"模拟读者面板：{', '.join(PERSONAS[p]['name'] for p in personas)}")
    print(f"  留存先验 {sig['retention_prior']} · 钩子 {sig['hook_strength']} · 套路 {sig['cliche_density_per_kchar']}/千字")
    print(f"  报告骨架 → {md_path}")
    print(f"  机读信号 → {sig_path}（novel-score 读作第一方留存先验）")
    print("  ⚠️ 定性反馈待 AI 代理按人格读文本补全报告里的【AI 代理填写】项")


if __name__ == "__main__":
    main()
