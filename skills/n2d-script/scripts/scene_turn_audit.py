#!/usr/bin/env python3
"""A2 场必转 / 价值转机检（戏剧结构·剧情好看） — 2026-06-24 流程自审落地。

McKee「场必须转」(value-charge shift)、Save the Cat、MRU 等戏剧结构在 2026 仍是**公认未被任何工具
机检的白区**（narrative-theory survey arXiv:2602.15851）。本检从 voiceover 的 `[情绪]` 标注序列做
"compute-don't-ask"（CML-Bench arXiv:2510.06231 的可复现思路·不问 LLM）三项启发式：

  ① **价值极性翻转**——整集情绪极性(正/负)是否至少翻转一次；零翻转(≥6 拍已知情绪)=一潭死水、场不转；
  ② **憋→放结构**——是否有"负向铺垫段 → 正向兑现"（微短剧物理：铺垫憋屈量≈爽点上限）；
     全程负到底(憋死没放)或全程正到底(爽到底没铺垫)都报；
  ③ **转折点位置**——若有反转 💥，是否被堆在开场前 1/5（LLM 写故事爱把挫折/转折放太早·arXiv:2407.13248）。

诚实边界：极性由情绪词表启发式判，只 flag 候选交人判；全 warn（report-only），`--strict` 有 warn 退 1。
纯 stdlib·纯函数可测。用法：python3 scene_turn_audit.py <作品根> 第N集 [--strict] [--json]
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import List, Optional, Tuple

LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")
REVERSAL_MARK = "💥"

POSITIVE_EMO = ("开心", "高兴", "喜悦", "希望", "欣慰", "释然", "感动", "兴奋", "甜", "暖",
                "扬眉吐气", "解气", "爽", "得意", "笃定", "温柔", "幸福", "安心", "惊喜")
NEGATIVE_EMO = ("难过", "伤心", "痛苦", "悲伤", "愤怒", "恼火", "气愤", "恐惧", "害怕", "惊恐",
                "绝望", "失望", "委屈", "屈辱", "羞辱", "嫉妒", "孤独", "崩溃", "不安", "愧疚",
                "焦虑", "无助", "憋屈", "心碎", "怨", "恨")


def emotion_polarity(emo: str) -> int:
    """情绪标注 → 极性 +1(正)/-1(负)/0(中)。纯函数·可测。"""
    e = str(emo or "")
    if any(w in e for w in NEGATIVE_EMO):
        return -1
    if any(w in e for w in POSITIVE_EMO):
        return 1
    return 0


def polarity_sequence(emos: List[str]) -> List[int]:
    """情绪序列 → 极性序列（保留 0）。纯函数·可测。"""
    return [emotion_polarity(e) for e in emos]


def count_charge_flips(pols: List[int]) -> int:
    """非零极性之间的正负翻转次数（0 跳过不算翻转）。纯函数·可测。"""
    flips = 0
    last = 0
    for p in pols:
        if p == 0:
            continue
        if last != 0 and p != last:
            flips += 1
        last = p
    return flips


def has_setback_then_payoff(pols: List[int]) -> bool:
    """是否存在"负向铺垫 → 正向兑现"（先出现 -1，其后出现 +1）。纯函数·可测。"""
    seen_neg = False
    for p in pols:
        if p < 0:
            seen_neg = True
        elif p > 0 and seen_neg:
            return True
    return False


def known_polarity_set(pols: List[int]) -> set:
    """出现过的非零极性集合。纯函数·可测。"""
    return {p for p in pols if p != 0}


def reversal_positions(marks: List[bool]) -> List[float]:
    """反转标记的相对位置(0~1)。纯函数·可测。"""
    n = len(marks)
    return [i / max(n - 1, 1) for i, m in enumerate(marks) if m]


EARLY_FRACTION = 0.2


def audit_beats(emos: List[str], marks: List[bool], shots: List[int]) -> List[Tuple[str, str, str]]:
    """场必转机检 → [(severity, code, msg)]。纯函数·可测。"""
    findings: List[Tuple[str, str, str]] = []
    pols = polarity_sequence(emos)
    known = [p for p in pols if p != 0]
    if len(known) < 6:
        return findings

    # ① 价值极性零翻转
    flips = count_charge_flips(pols)
    if flips == 0:
        only = known_polarity_set(pols)
        tone = "全程负向" if only == {-1} else ("全程正向" if only == {1} else "极性不翻")
        findings.append(("warn", "no_value_charge_turn",
                         f"{tone}、整集情绪极性零翻转：场不转(McKee value-charge)，观众情绪一潭死水——"
                         "给本集至少一次转折/反转，让价值从正翻负或负翻正"))

    # ② 憋→放结构
    only = known_polarity_set(pols)
    if only == {-1}:
        findings.append(("warn", "all_negative_no_payoff",
                         "全程负向、无正向兑现：憋到底没放（微短剧物理：铺垫憋屈量≈爽点上限，光憋不放=劝退）"))
    elif only == {1}:
        findings.append(("warn", "all_positive_no_setback",
                         "全程正向、无负向铺垫：爽到底没憋（无铺垫的爽=糖精，给个挫折/打压再扬眉吐气）"))
    elif flips > 0 and not has_setback_then_payoff(pols):
        findings.append(("info", "payoff_before_setback",
                         "有极性翻转但未见「先憋后放」（负向铺垫→正向兑现）：核对爽点是否建立在足够铺垫上"))

    # ③ 转折点全堆在开场
    rev = reversal_positions(marks)
    if rev and all(p <= EARLY_FRACTION for p in rev):
        findings.append(("warn", "reversal_too_early",
                         f"反转💥只出现在开场前 {int(EARLY_FRACTION*100)}%（位置 {[round(p,2) for p in rev]}）："
                         "转折堆太早、后段塌（LLM 通病）——把主要转折/挫折放到中后段做 Point-of-No-Return/Major-Setback"))
    return findings


def voiceover_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "voiceover.txt")


def parse_beats(path: str) -> List[Tuple[int, str, bool]]:
    """voiceover.txt → [(镜号, emo, has_reversal_mark)]。纯解析。"""
    rows = []
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return rows
    for raw in text.splitlines():
        line = raw.strip()
        m = LINE_RE.match(line)
        if m:
            rows.append((int(m.group(1)), m.group(3).strip(), REVERSAL_MARK in line))
    return rows


def print_findings(findings: List[Tuple[str, str, str]]) -> None:
    if not findings:
        print("- ✅ 价值转/憋放结构机检通过（情绪有翻转·有铺垫→兑现·转折不堆开场）")
        return
    for sev, code, msg in findings:
        print(f"- {'⚠️' if sev == 'warn' else 'ℹ️'} [{code}] {msg}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) < 2:
        print("用法: scene_turn_audit.py <作品根> 第N集 [--strict] [--json]")
        sys.exit(2)
    root, ep = args[0], (args[1] if args[1].startswith("第") else f"第{args[1]}集")
    beats = parse_beats(voiceover_path(root, ep))
    if not beats:
        print(f"⛔ 缺/空 {voiceover_path(root, ep)}——先跑 n2d-script 阶段1 出 voiceover", file=sys.stderr)
        sys.exit(2)
    emos = [b[1] for b in beats]
    marks = [b[2] for b in beats]
    shots = [b[0] for b in beats]
    findings = audit_beats(emos, marks, shots)
    if "--json" in flags:
        print(json.dumps({"episode": ep, "beats": len(beats),
                          "charge_flips": count_charge_flips(polarity_sequence(emos)),
                          "findings": [{"severity": s, "code": c, "msg": m} for s, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(f"# 场必转/价值转机检（A2·戏剧结构·report-only·启发式） — {ep}")
        print_findings(findings)
        print("> 极性按情绪标注启发式判；逐场 goal/conflict/outcome 与 MRU 仍需人判（白区·见 references/拆集法.md）。")
    warn_n = sum(1 for s, _, _ in findings if s == "warn")
    if "--strict" in flags and warn_n:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
