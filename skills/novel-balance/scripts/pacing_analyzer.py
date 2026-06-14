#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pacing_analyzer.py — 情节热力图（确定性信号 + LLM 语义校准骨架）

诚实分工（同家族 mechanical/script 哲学）：
  - 脚本逐章算**确定性近似信号**：冲突强度、信息密度、爽点密度（口径见
    references/heatmap-method.md，爽点关键词与 novel-simulate rookie 人格同源）。
  - 最终曲线的语义校准（"这段是不是真注水 / 真高潮"）由 LLM 代理读文本补全。
  - 产物：人读 `评分/情节热力图_<日期>.md` + 机读 `评分/pacing_signals.json`。

  python3 pacing_analyzer.py <作品根> [--range 1-100]

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
from project_io import parse_chapter_range, read_chapters  # noqa: E402

_CJK = r"一-鿿"

# 冲突/转折关键词（冲突强度近似）
CONFLICT_KW = ["杀", "血", "刀", "剑", "怒", "吼", "战", "斗", "击", "破", "死", "逼",
               "撕", "崩", "爆", "厉", "狠", "拼", "夺", "反", "叛", "敌", "危", "险",
               "突然", "猛地", "骤然", "竟", "却", "不料", "没想到"]

# 爽点关键词（与 novel-simulate rookie 人格 kw 同一口径，见 heatmap-method.md）
PAYOFF_KW = ["打脸", "逆袭", "碾压", "突破", "反杀", "升级", "扮猪", "装", "解气",
             "翻盘", "吊打", "震惊", "废柴", "崛起", "无敌", "暴击", "斩杀"]


def _cjk_len(s):
    return len(re.findall(f"[{_CJK}]", s))


def _density(text, kw):
    chars = _cjk_len(text) or 1
    hits = sum(text.count(w) for w in kw)
    return round(hits / chars * 1000, 2)  # 命中 / 千字


def _lexical_diversity(text):
    grams = re.findall(f"[{_CJK}]{{4}}", text)
    if not grams:
        return 0.0
    return round(len(set(grams)) / len(grams), 3)


def _scale(value, lo, hi):
    """把 [lo,hi] 区间的原始值线性映射到 1-10 整数分。"""
    if hi <= lo:
        return 1
    if value <= lo:
        return 1
    if value >= hi:
        return 10
    return int(round(1 + 9 * (value - lo) / (hi - lo)))


def _chapter_num(name):
    m = re.search(r"(\d+)", name)
    return int(m.group(1)) if m else 10 ** 6


def list_chapters(project, rng=None):
    return [(idx, text) for idx, _path, text in read_chapters(project, rng)]


def parse_range(s):
    return parse_chapter_range(s)


def analyze(project, rng=None):
    chs = list_chapters(project, rng)
    if not chs:
        return None
    rows = []
    for idx, text in chs:
        conflict = _density(text, CONFLICT_KW)
        payoff = _density(text, PAYOFF_KW)
        diversity = _lexical_diversity(text)
        rows.append({
            "chapter": idx,
            "chars": _cjk_len(text),
            "conflict_per_kchar": conflict,
            "payoff_per_kchar": payoff,
            "lexical_diversity": diversity,
            "conflict_score": _scale(conflict, 0, 12),      # 冲突强度 1-10
            "info_score": _scale(diversity, 0.50, 0.95),    # 信息密度 1-10
            "payoff_score": _scale(payoff, 0, 10),          # 爽点密度 1-10
        })
    return rows


def flag_rows(rows):
    """逐章判定 + 连续注水检测（确定性预警；语义由 LLM 复核）。"""
    n = len(rows)
    for i, r in enumerate(rows):
        verdict = "✅ 节奏紧凑"
        # 单章低谷
        if r["conflict_score"] <= 3 and r["info_score"] <= 2:
            verdict = "⚠️ 低冲突+低信息，疑似注水"
        if r["conflict_score"] <= 2 and r["info_score"] <= 1 and r["payoff_score"] <= 1:
            verdict = "🔴 三项皆低，弃书点风险"
        r["verdict"] = verdict
    # 连续注水段：≥5 章 conflict≤3 且 info≤2
    run = 0
    for r in rows:
        low = r["conflict_score"] <= 3 and r["info_score"] <= 2
        run = run + 1 if low else 0
        if run >= 5:
            r["verdict"] = "🌊 连续注水段（≥5章）"
    return rows


def write_report(project, rows):
    date = datetime.now().strftime("%Y-%m-%d")
    rdir = os.path.join(project, "评分")
    os.makedirs(rdir, exist_ok=True)

    sig_path = os.path.join(rdir, "pacing_signals.json")
    with open(sig_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": date,
            "kind": "novel_pacing_signals",
            "note": "确定性近似信号；语义校准（真注水/真高潮）待 LLM 代理读文本补全",
            "chapters": rows,
        }, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(rdir, f"情节热力图_{date}.md")
    lines = [
        f"# 情节热力图报告 — {date}",
        "",
        f"- 章节数：{len(rows)}",
        "- 信号为确定性近似（口径见 `novel-balance/references/heatmap-method.md`）；语义校准由 AI 代理读文本补全。",
        "",
        "| 章节 | 冲突强度 | 信息密度 | 爽点分 | 判定 |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| 第{r['chapter']}章 | {r['conflict_score']} | {r['info_score']} | "
            f"{r['payoff_score']} | {r['verdict']} |")
    lines += [
        "",
        "> 「判定」为脚本按确定性阈值给出的初判；连续注水段 / 高潮过密 / 节奏脱节的"
        "最终结论需 AI 代理结合语义复核（参见 heatmap-method.md 预警规则）。",
        "",
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md_path, sig_path


def main():
    parser = argparse.ArgumentParser(description="情节热力图（确定性信号 + LLM 校准骨架）")
    parser.add_argument("project_path", help="Path to the novel project root")
    parser.add_argument("--range", help="章节范围，如 1-100 或单章 12")
    args = parser.parse_args()

    rng = parse_range(args.range)
    rows = analyze(args.project_path, rng)
    if not rows:
        print(f"Error: {args.project_path}/章节 下没有可读章节（或 --range 无命中）")
        return
    flag_rows(rows)
    md_path, sig_path = write_report(args.project_path, rows)
    flagged = sum(1 for r in rows if not r["verdict"].startswith("✅"))
    print(f"情节热力图：{len(rows)} 章，{flagged} 章有节奏预警")
    print(f"  人读报告 → {md_path}")
    print(f"  机读信号 → {sig_path}")
    print("  ⚠️ 注水/高潮过密/脱节的最终判定需 AI 代理读文本做语义校准")


if __name__ == "__main__":
    main()
