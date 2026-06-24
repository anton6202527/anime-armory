#!/usr/bin/env python3
"""A5 潜台词/去AI味机检（对白质量·剧情好看） — 2026-06-24 流程自审落地。

`story_integrity_audit` 只有"非推进对白"代理，**不查直白 vs 潜台词**——而潜台词正是人 vs AI 的真差距
（AI 能写对白，难写精准潜台词；说教/直给情绪是短剧观众的头号劝退）。本检对 `voiceover.txt` 做纯文本
启发式，抓 ImpScore 论文（arXiv:2411.05172）意义上的**低隐含度台词** + StoryScope（2604.03136）五类"AI味"：

  ① 自陈情绪——角色直接说出自己情绪（"我好难过/我真的很生气/我爱你"）= 告知非演出；
  ② 情绪概括——旁白替角色总结情绪（"她感到一阵绝望"）= telling not showing；
  ③ 动机过度解释——台词里 因为…所以…/之所以…是因为… 把动机直白说穿；
  ④ 信息直给——"其实我是…/你忘了我是你…" 这类身份/设定硬塞 exposition；
  集级算**直白率**（命中行/对白行）作说教代理，超阈提示整体偏直白。

诚实边界（写死）：这是 **ImpScore（需训练模型）的词汇启发式代理**，只 flag **候选**交人判，不计算真隐含度、
不臆造分；全部 warn/info（report-only），`--strict` 有 warn 即退 1。纯 stdlib·纯函数可测。
用法：python3 subtext_audit.py <作品根> 第N集 [--strict] [--json]
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import List, Optional, Tuple

LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")
NARRATOR_ROLES = ("旁白", "narration", "voiceover", "vo", "ns")

# 情绪词表（自陈/概括共用）。只取**明确情绪状态词**，不含中性词，降误报。
EMOTION_WORDS = (
    "难过", "伤心", "痛苦", "悲伤", "心碎", "生气", "愤怒", "恼火", "气愤", "害怕", "恐惧",
    "惊恐", "紧张", "焦虑", "开心", "高兴", "快乐", "兴奋", "喜悦", "嫉妒", "羡慕", "绝望",
    "失望", "委屈", "孤独", "寂寞", "感动", "心动", "想你", "爱你", "恨你", "崩溃", "不安",
    "愧疚", "自责", "释然", "欣慰", "激动",
)
_EMO = "|".join(EMOTION_WORDS)
# ① 自陈情绪："我(很/好/真的/太/这么/如此)*<情绪>"（允许多个程度词叠用：我真的很…）
SELF_EMOTION_RE = re.compile(rf"我(?:们)?[，,]?\s*(?:真的|好|很|太|这么|如此|实在|特别|是)*\s*(?:感到|觉得)?\s*(?:{_EMO})")
# ② 情绪概括（旁白替角色总结）："(他/她/名字)(感到/觉得/心里/心中)…<情绪>"
EMOTIONAL_SUMMARY_RE = re.compile(rf"(?:他|她|它)?(?:[，,]?)?(?:感到|觉得|心里|心中|心头|内心)\s*(?:一阵|一丝|无比|十分|非常|很)?\s*(?:{_EMO})")
# ③ 动机过度解释
OVER_EXPLAIN_RE = re.compile(r"因为.{0,40}所以|之所以.{0,30}是因为|正是因为.{0,30}才")
# ④ 信息直给（身份/设定硬塞）
EXPOSITION_RE = re.compile(r"其实我(?:是|就是)|你(?:难道)?忘了我(?:是|就是)|要知道我(?:可)?是|别忘了我(?:是|就是)")


def is_self_emotion(text: str) -> bool:
    """角色自陈情绪（告知非演出）。纯函数·可测。"""
    return bool(SELF_EMOTION_RE.search(str(text or "")))


def is_emotional_summary(role: str, text: str) -> bool:
    """旁白替角色概括情绪（telling not showing）。仅对旁白行判。纯函数·可测。"""
    if str(role or "").strip().lower() not in NARRATOR_ROLES:
        return False
    return bool(EMOTIONAL_SUMMARY_RE.search(str(text or "")))


def is_over_explanation(text: str) -> bool:
    """台词把动机/因果直白说穿。纯函数·可测。"""
    return bool(OVER_EXPLAIN_RE.search(str(text or "")))


def is_exposition_dump(text: str) -> bool:
    """身份/设定硬塞 exposition。纯函数·可测。"""
    return bool(EXPOSITION_RE.search(str(text or "")))


def classify_line(role: str, text: str) -> List[str]:
    """单行命中的"AI味"标签列表。纯函数·可测。"""
    tags = []
    if is_self_emotion(text):
        tags.append("self_emotion")
    if is_emotional_summary(role, text):
        tags.append("emotional_summary")
    if is_over_explanation(text):
        tags.append("over_explanation")
    if is_exposition_dump(text):
        tags.append("exposition_dump")
    return tags


def onthenose_rate(flagged: int, total: int) -> float:
    """直白率（命中行/对白行）。纯函数·可测。"""
    return round(flagged / total, 3) if total else 0.0


_TAG_MSG = {
    "self_emotion": "自陈情绪（直说「我很…」）：把情绪演出来（动作/细节/潜台词），别直接报情绪名",
    "emotional_summary": "旁白替角色概括情绪（「她感到…」）：show don't tell，用画面/行为带情绪",
    "over_explanation": "动机过度解释（因为…所以…）：把因果藏进潜台词，别在台词里说穿",
    "exposition_dump": "身份/设定硬塞 exposition：用情境/行为透露，别让角色对着观众报设定",
}
ONTHENOSE_RATE_WARN = 0.22


def parse_voiceover(path: str) -> List[Tuple[int, str, str]]:
    """voiceover.txt → [(镜号, role, text)]。纯解析。"""
    rows = []
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return rows
    for raw in text.splitlines():
        m = LINE_RE.match(raw.strip())
        if m:
            rows.append((int(m.group(1)), m.group(2).strip(), m.group(5).strip()))
    return rows


def audit_lines(rows: List[Tuple[int, str, str]]) -> List[Tuple[str, str, str]]:
    """逐行潜台词机检 → [(severity, code, msg)]。纯函数·可测。"""
    findings: List[Tuple[str, str, str]] = []
    dialogue_total = 0
    flagged = 0
    for shot, role, text in rows:
        is_dialogue = str(role).strip().lower() not in NARRATOR_ROLES
        if is_dialogue:
            dialogue_total += 1
        tags = classify_line(role, text)
        if tags:
            if is_dialogue:
                flagged += 1
            for tag in tags:
                findings.append(("warn", tag, f"镜{shot}「{role}」：{_TAG_MSG[tag]}（「{text[:18]}…」）"))
    rate = onthenose_rate(flagged, dialogue_total)
    if dialogue_total >= 5 and rate >= ONTHENOSE_RATE_WARN:
        findings.append(("warn", "onthenose_rate_high",
                         f"本集直白率 {rate}（{flagged}/{dialogue_total} 对白行直说情绪/动机/设定）≥{ONTHENOSE_RATE_WARN}："
                         "整体偏说教，多用潜台词/留白；说教是短剧观众头号劝退"))
    return findings


def voiceover_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "voiceover.txt")


def print_findings(findings: List[Tuple[str, str, str]]) -> None:
    if not findings:
        print("- ✅ 未抓到明显直白/说教候选（潜台词机检为启发式初筛，仍需人判台词质感）")
        return
    for sev, code, msg in findings:
        print(f"- {'⚠️' if sev == 'warn' else 'ℹ️'} [{code}] {msg}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) < 2:
        print("用法: subtext_audit.py <作品根> 第N集 [--strict] [--json]")
        sys.exit(2)
    root, ep = args[0], (args[1] if args[1].startswith("第") else f"第{args[1]}集")
    path = voiceover_path(root, ep)
    rows = parse_voiceover(path)
    if not rows:
        print(f"⛔ 缺/空 {path}——先跑 n2d-script 阶段1 出 voiceover", file=sys.stderr)
        sys.exit(2)
    findings = audit_lines(rows)
    if "--json" in flags:
        print(json.dumps({"episode": ep, "lines": len(rows),
                          "findings": [{"severity": s, "code": c, "msg": m} for s, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(f"# 潜台词/去AI味机检（A5·report-only·启发式初筛） — {ep}")
        print_findings(findings)
        print("> 这是 ImpScore 的词汇代理，只 flag 候选；真潜台词质感（言外之意/反话/沉默）仍需人判。")
    warn_n = sum(1 for s, _, _ in findings if s == "warn")
    if "--strict" in flags and warn_n:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
