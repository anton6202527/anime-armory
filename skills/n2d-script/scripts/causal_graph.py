#!/usr/bin/env python3
"""A1 因果链图（剧情合理性骨架） — 2026-06-24 流程自审落地。

此前 choice→consequence 只是 `story_integrity_audit` 的**词汇共现**（有"选择"词+有"后果"词就算过）。
本检按 Causal Plot Graph 思路（R²·arXiv:2503.15655）从 `voiceover.txt` 抽一张**前向因果图**：
beat 为节点，因果连接词 / 选择→后果邻接 为边，再按两条 R² 审计信号 flag：

  ① **天降/为反转而反转候选**——重大事件（反转 💥 或"突然/竟然/原来/没想到"惊变）却**无入边因果**
     且**台词自身不含因为/由于**自解释 → 事件从天而降（正打"反派智障逻辑/工业糖精"：反转靠巧合不靠铺垫）；
  ② **因果覆盖率**——重大事件中能追溯到原因的比例，过低=全靠巧合推进。

诚实边界（写死·呼应 arXiv:2410.23884）：**先抽结构再判，绝不内联问 LLM"合理吗"**（LLM 会默认套刻板印象）；
本检是**词汇/邻接启发式**，只 flag 候选交人判，不证明因果、不臆造分；全部 warn/info（report-only）。
纯 stdlib·纯函数可测。用法：python3 causal_graph.py <作品根> 第N集 [--strict] [--json]
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")

REVERSAL_MARK = "💥"
# 惊变/天降标记：被叙述成"凭空发生"的词。
SURPRISE_WORDS = ("突然", "忽然", "竟然", "居然", "没想到", "不料", "谁知", "原来", "莫名",
                  "无缘无故", "凭空", "平白", "猛地", "陡然")
# 台词自身含的因果自解释（有它=事件自带因，不算天降）。
SELF_CAUSE_RE = re.compile(r"因为|由于|因|既然|为了|只因|正因")
# 引导"后果"的连接词（出现在 beat 句首/句中→上一 beat 是它的因）。
CONSEQUENCE_LEAD = ("所以", "于是", "因此", "结果", "这才", "才", "便", "致使", "导致", "以至", "故而")
# 选择/决断动词（choice 侧）。
CHOICE_WORDS = ("决定", "选择", "打算", "决意", "下定决心", "要去", "起身", "动手", "出手",
                "答应", "拒绝", "立誓", "发誓", "决然")
EVIDENCE_WORDS = ("证据", "线索", "物证", "脚印", "血", "血迹", "鞋", "皂靴", "茶面", "查清",
                  "盘问", "画押", "看鞋", "看血", "账册", "供词", "尸身", "验尸")
REVEAL_WORDS = ("揭穿", "真相", "原来", "竟是", "其实", "不是", "并非", "回来的，是",
                "披着", "剥了", "露出", "暴露")

# A6 降智/工业糖精：冲突/误会靠"角色不沟通/无视铁证"硬维持（#1 工业糖精信号·反派智障逻辑）。
MISUNDERSTANDING_WORDS = ("误会", "误解", "误以为", "错以为", "当成", "当作", "错把", "以为")
NO_COMM_WORDS = ("没解释", "不解释", "不肯说", "没机会解释", "百口莫辩", "有口难辩", "没问",
                 "不愿多说", "不想解释", "懒得解释", "没说清", "来不及解释", "不愿说明", "不肯解释")
IGNORE_EVIDENCE_WORDS = ("无视", "不信", "不听", "不顾", "视而不见", "充耳不闻", "不容分说",
                         "不由分说", "铁证如山", "证据确凿")


def idiot_plot_signal(text: str) -> bool:
    """该 beat 是否"冲突靠不沟通/无视铁证硬维持"（降智候选）。纯函数·可测。

    需同时有【误会/冲突语境】+【不沟通 或 无视证据】信号——避免单独"以为"等高频词误报。
    """
    t = str(text or "")
    has_misunderstand = any(w in t for w in MISUNDERSTANDING_WORDS)
    has_no_comm = any(w in t for w in NO_COMM_WORDS)
    has_ignore = any(w in t for w in IGNORE_EVIDENCE_WORDS)
    return (has_misunderstand and (has_no_comm or has_ignore)) or (has_no_comm and has_ignore)


def is_reversal_or_surprise(text: str, has_reversal_mark: bool) -> bool:
    """该 beat 是否重大事件（反转标记 或 惊变词）。纯函数·可测。"""
    if has_reversal_mark:
        return True
    return any(w in str(text or "") for w in SURPRISE_WORDS)


def is_self_caused(text: str) -> bool:
    """台词自身是否含因果自解释（因为/由于…）。纯函数·可测。"""
    return bool(SELF_CAUSE_RE.search(str(text or "")))


def leads_with_consequence(text: str) -> bool:
    """该 beat 是否由后果连接词引导（→上一 beat 是其因）。纯函数·可测。"""
    t = str(text or "").lstrip("，,。.、 　")
    return any(t.startswith(w) or (w in t[:8]) for w in CONSEQUENCE_LEAD)


def has_choice(text: str) -> bool:
    """该 beat 是否含选择/决断动词。纯函数·可测。"""
    return any(w in str(text or "") for w in CHOICE_WORDS)


def has_evidence_signal(text: str) -> bool:
    """该 beat 是否含证据链/审案推进信号。纯函数·可测。"""
    return any(w in str(text or "") for w in EVIDENCE_WORDS)


def has_reveal_signal(text: str) -> bool:
    """该 beat 是否含揭示/反转落点信号。纯函数·可测。"""
    return any(w in str(text or "") for w in REVEAL_WORDS)


def build_causal_edges(texts: List[str]) -> Set[Tuple[int, int]]:
    """前向因果边集合 {(因 index, 果 index)}。纯函数·可测。

    边来源：① 后果连接词引导的 beat ← 前一 beat；② 选择 beat → 下一 beat；
    ③ 证据链 beat → 紧邻揭示/反转 beat（侦探/审案题材常用）。
    """
    edges: Set[Tuple[int, int]] = set()
    n = len(texts)
    for i in range(1, n):
        if leads_with_consequence(texts[i]):
            edges.add((i - 1, i))
        if has_evidence_signal(texts[i - 1]) and has_reveal_signal(texts[i]):
            edges.add((i - 1, i))
    for i in range(n - 1):
        if has_choice(texts[i]):
            edges.add((i, i + 1))
    return edges


def contrivance_candidates(texts: List[str], reversal_marks: List[bool],
                           edges: Set[Tuple[int, int]]) -> List[int]:
    """天降/为反转而反转候选 index：重大事件 ∧ 无入边 ∧ 非自解释。纯函数·可测。"""
    incoming = {j for _i, j in edges}
    out = []
    for idx, text in enumerate(texts):
        if not is_reversal_or_surprise(text, reversal_marks[idx]):
            continue
        if idx in incoming:
            continue
        if is_self_caused(text):
            continue
        out.append(idx)
    return out


def causal_coverage(texts: List[str], reversal_marks: List[bool],
                    edges: Set[Tuple[int, int]]) -> Tuple[int, int]:
    """重大事件因果覆盖：(有因的重大事件数, 重大事件总数)。纯函数·可测。"""
    incoming = {j for _i, j in edges}
    big = [i for i, t in enumerate(texts) if is_reversal_or_surprise(t, reversal_marks[i])]
    caused = [i for i in big if i in incoming or is_self_caused(texts[i])]
    return len(caused), len(big)


COVERAGE_WARN = 0.5


def parse_beats(path: str) -> List[Tuple[int, str, str, bool]]:
    """voiceover.txt → [(镜号, role, text, has_reversal_mark)]。纯解析。"""
    rows = []
    try:
        raw_text = open(path, encoding="utf-8").read()
    except OSError:
        return rows
    for raw in raw_text.splitlines():
        line = raw.strip()
        m = LINE_RE.match(line)
        if m:
            text = m.group(5).strip()
            rows.append((int(m.group(1)), m.group(2).strip(), text, REVERSAL_MARK in line))
    return rows


def audit_beats(beats: List[Tuple[int, str, str, bool]]) -> List[Tuple[str, str, str]]:
    """因果图机检 → [(severity, code, msg)]。纯函数·可测。"""
    findings: List[Tuple[str, str, str]] = []
    texts = [b[2] for b in beats]
    marks = [b[3] for b in beats]
    shots = [b[0] for b in beats]
    if len(texts) < 4:
        return findings
    edges = build_causal_edges(texts)
    for idx in contrivance_candidates(texts, marks, edges):
        kind = "反转" if marks[idx] else "惊变"
        findings.append(("warn", "contrivance_candidate",
                         f"镜{shots[idx]} {kind}事件无前因（无因果入边、台词也没说因）：「{texts[idx][:20]}…」"
                         "——疑似天降/为反转而反转，给它种个铺垫或让它由前面的选择/事件导出（铺垫憋屈量≈爽点上限）"))
    for idx, text in enumerate(texts):
        if idiot_plot_signal(text):
            findings.append(("warn", "idiot_plot_candidate",
                             f"镜{shots[idx]} 冲突/误会疑似靠角色不沟通/无视铁证硬维持：「{text[:20]}…」"
                             "——#1 工业糖精信号（反派智障逻辑/为虐而虐）；让破局来自关键证据而非降智，或给不沟通一个真实理由"))
    caused, big = causal_coverage(texts, marks, edges)
    if big >= 3:
        cov = round(caused / big, 3)
        if cov < COVERAGE_WARN:
            findings.append(("warn", "low_causal_coverage",
                             f"重大事件因果覆盖率 {cov}（{caused}/{big} 个能追溯到原因）<{COVERAGE_WARN}："
                             "剧情多靠巧合/突然推进而非选择→后果链，补因果链让「合理」立住"))
    return findings


def voiceover_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "voiceover.txt")


def print_findings(findings: List[Tuple[str, str, str]]) -> None:
    if not findings:
        print("- ✅ 未抓到明显无前因的天降事件（因果图为启发式初筛，深层动机仍需人判）")
        return
    for sev, code, msg in findings:
        print(f"- {'⚠️' if sev == 'warn' else 'ℹ️'} [{code}] {msg}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) < 2:
        print("用法: causal_graph.py <作品根> 第N集 [--strict] [--json]")
        sys.exit(2)
    root, ep = args[0], (args[1] if args[1].startswith("第") else f"第{args[1]}集")
    beats = parse_beats(voiceover_path(root, ep))
    if not beats:
        print(f"⛔ 缺/空 {voiceover_path(root, ep)}——先跑 n2d-script 阶段1 出 voiceover", file=sys.stderr)
        sys.exit(2)
    findings = audit_beats(beats)
    if "--json" in flags:
        edges = sorted(build_causal_edges([b[2] for b in beats]))
        print(json.dumps({"episode": ep, "beats": len(beats), "causal_edges": edges,
                          "findings": [{"severity": s, "code": c, "msg": m} for s, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(f"# 因果链图机检（A1·剧情合理·report-only·启发式初筛） — {ep}")
        print_findings(findings)
        print("> 先抽因果结构再判（不内联问 LLM「合理吗」·防套刻板印象）；深层动机/世界观自洽仍需人判。")
    warn_n = sum(1 for s, _, _ in findings if s == "warn")
    if "--strict" in flags and warn_n:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
