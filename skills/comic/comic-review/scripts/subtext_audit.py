#!/usr/bin/env python3
"""潜台词 / 去 AI 味机检（对白质量·advisory）——参照同仓成熟视频线 A5 的漫画重实现。

为什么存在：`redundancy_audit` 只查「同义反复 / 旁白硬转占比 / 构图重复」——治的是**重复**，
从不查**直白 vs 潜台词**。而 AI 生成脚本最大的「AI 味」恰恰是低隐含度台词：角色自陈情绪、
旁白替角色总结情绪、把动机因果直白说穿、身份/设定硬塞 exposition。漫画比视频更吃亏——
画面本可用表情/肢体/分格演出情绪，对白再直陈情绪 = **画面已演的东西又用文字复述一遍**，
双重告知、活人感尽失。本检对每格 `dialogue[].text`（`text_target` 优先）和 `narration` 做
纯文本启发式，抓四类低隐含度信号 + 集级直白率：

  ① 自陈情绪（self_stated_emotion）——台词里角色直接说自己的情绪（「我好难过 / 我真的很生气 / 我爱你」）。
  ② 情绪概括（narrated_emotion_summary）——旁白替角色总结情绪（「她感到一阵绝望」）= telling not showing。
  ③ 动机过度解释（over_explained_motive）——台词/旁白把动机因果直白说穿（因为…所以… / 之所以…是因为…）。
  ④ 信息直给（exposition_dump）——「其实我是… / 你忘了我是你…」这类身份/设定硬塞。
  集级直白率（on_the_nose_rate）=命中行 / 对白行，超阈提示整体偏直白（说教代理）。

漫画专属加强（comic_redundant_with_art）：命中①/②的那一格若在 `character_bindings[].expression_id`
里已经钉了表情锚（画面本就演这情绪），额外标一句「画面已有表情演绎、对白/旁白再直陈=双重告知」，
把「该改」的优先级顶上去。

诚实边界（写死）：这是 **ImpScore（需训练模型）的词汇启发式代理**，只 flag **候选**交人判，
不算真隐含度、不臆造分。全部 warn/info——**本检是「审」不是「门」**（脆弱关键词启发式不得硬阻断付费）；
gate 里以 advisory 并入，`--strict` 仅用于人手排查时有命中即退 1，正式 gate 从不用它硬拦。

用法（与本线其它 advisory 机检同签名）：
  python3 subtext_audit.py <作品根> 第N话 [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

VERSION = 1
KIND = "comic_subtext_audit"

# 集级直白率警戒线（命中行 / 对白行）。env 可调，默认 0.35：超过 = 整体偏说教。
ON_THE_NOSE_RATE_WARN = float(os.environ.get("COMIC_SUBTEXT_RATE_WARN", "0.35"))
# 触发集级直白率判定所需的最小对白行数（样本太小不下整体结论，降误报）。
MIN_DIALOGUE_LINES = int(os.environ.get("COMIC_SUBTEXT_MIN_LINES", "6"))

NARRATOR_SPEAKERS = ("旁白", "narration", "voiceover", "vo", "ns", "narrator")

# 情绪词表（自陈/概括共用）。只取**明确情绪状态词**，不含中性词，降误报。
EMOTION_WORDS = (
    "难过", "伤心", "痛苦", "悲伤", "心碎", "生气", "愤怒", "恼火", "气愤", "害怕", "恐惧",
    "惊恐", "紧张", "焦虑", "开心", "高兴", "快乐", "兴奋", "喜悦", "嫉妒", "羡慕", "绝望",
    "失望", "委屈", "孤独", "寂寞", "感动", "心动", "想你", "爱你", "恨你", "崩溃", "不安",
    "愧疚", "自责", "释然", "欣慰", "激动", "震惊", "慌张", "无助", "心疼", "心酸",
)
_EMO = "|".join(EMOTION_WORDS)
# ① 自陈情绪："我(很/好/真的/太/这么/如此)*<情绪>"（允许多个程度词叠用：我真的很…）
SELF_EMOTION_RE = re.compile(
    rf"我(?:们)?[，,]?\s*(?:真的|好|很|太|这么|如此|实在|特别|是)*\s*(?:感到|觉得)?\s*(?:{_EMO})"
)
# ② 情绪概括（旁白替角色总结）："(他/她/名字)(感到/觉得/心里/心中)…<情绪>"
EMOTIONAL_SUMMARY_RE = re.compile(
    rf"(?:他|她|它)?(?:[，,]?)?(?:感到|觉得|心里|心中|心头|内心)\s*(?:一阵|一丝|无比|十分|非常|很)?\s*(?:{_EMO})"
)
# ③ 动机过度解释
OVER_EXPLAIN_RE = re.compile(r"因为.{0,40}所以|之所以.{0,30}是因为|正是因为.{0,30}才")
# ④ 信息直给（身份/设定硬塞）
EXPOSITION_RE = re.compile(r"其实我(?:是|就是)|你(?:难道)?忘了我(?:是|就是)|要知道我(?:可)?是|别忘了我(?:是|就是)")

CATEGORY_FIX = {
    "self_stated_emotion": "把「说出情绪」改成「演出情绪」：让表情/肢体/分格/留白承载，对白只留动作或潜台词。",
    "narrated_emotion_summary": "删掉旁白替角色总结的情绪，改用可画的外部动作/细节让读者自己读出（show not tell）。",
    "over_explained_motive": "删掉「因为…所以…」的因果直陈，把动机藏进选择和行动，让读者推断。",
    "exposition_dump": "别用台词硬塞身份/设定，改成通过场景、道具或他人反应侧面带出。",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_chapter(value: str) -> str:
    value = str(value or "").strip()
    return value if value.startswith("第") else f"第{value}话"


def load_panels(root: Path, chapter: str) -> List[Dict[str, Any]]:
    path = root / "脚本" / chapter / "panel_script.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    panels = data.get("panels") if isinstance(data, Mapping) else None
    return [p for p in panels if isinstance(p, Mapping)] if isinstance(panels, list) else []


def panel_texts(panel: Mapping[str, Any]) -> List[Dict[str, str]]:
    """一格里的可嵌字文本行：台词（text_target 优先）+ 旁白。纯函数·可测。

    与 redundancy_audit.panel_texts 同口径，保持本线解析一致。"""
    out: List[Dict[str, str]] = []
    pid = str(panel.get("panel_id") or "?")
    for item in panel.get("dialogue") or []:
        if isinstance(item, Mapping):
            text = str(item.get("text_target") or item.get("text") or "").strip()
            speaker = str(item.get("speaker") or "")
        else:
            text, speaker = str(item or "").strip(), ""
        if text:
            out.append({"panel": pid, "kind": "dialogue", "speaker": speaker, "text": text})
    narration = str(panel.get("narration_target") or panel.get("narration") or "").strip()
    if narration:
        out.append({"panel": pid, "kind": "narration", "speaker": "旁白", "text": narration})
    return out


def is_narrator(kind: str, speaker: str) -> bool:
    if str(kind or "").strip().lower() == "narration":
        return True
    return str(speaker or "").strip().lower() in NARRATOR_SPEAKERS


def is_self_emotion(kind: str, speaker: str, text: str) -> bool:
    """角色自陈情绪（告知非演出）。只对**台词**判（旁白归②）。纯函数·可测。"""
    if is_narrator(kind, speaker):
        return False
    return bool(SELF_EMOTION_RE.search(str(text or "")))


def is_emotional_summary(kind: str, speaker: str, text: str) -> bool:
    """旁白替角色概括情绪（telling not showing）。仅对旁白判。纯函数·可测。"""
    if not is_narrator(kind, speaker):
        return False
    return bool(EMOTIONAL_SUMMARY_RE.search(str(text or "")))


def is_over_explanation(text: str) -> bool:
    """台词/旁白把动机/因果直白说穿。纯函数·可测。"""
    return bool(OVER_EXPLAIN_RE.search(str(text or "")))


def is_exposition_dump(kind: str, speaker: str, text: str) -> bool:
    """身份/设定硬塞 exposition。只对台词判。纯函数·可测。"""
    if is_narrator(kind, speaker):
        return False
    return bool(EXPOSITION_RE.search(str(text or "")))


def panel_has_expression_anchor(panel: Mapping[str, Any]) -> bool:
    """本格是否已在 character_bindings 里钉了表情锚（画面已演该情绪）。纯函数·可测。"""
    for binding in panel.get("character_bindings") or []:
        if isinstance(binding, Mapping) and str(binding.get("expression_id") or "").strip():
            return True
    return False


def classify_line(kind: str, speaker: str, text: str) -> List[str]:
    """一行文本命中的 AI 味类别（可多重）。纯函数·可测。"""
    hits: List[str] = []
    if is_self_emotion(kind, speaker, text):
        hits.append("self_stated_emotion")
    if is_emotional_summary(kind, speaker, text):
        hits.append("narrated_emotion_summary")
    if is_over_explanation(text):
        hits.append("over_explained_motive")
    if is_exposition_dump(kind, speaker, text):
        hits.append("exposition_dump")
    return hits


def finding(code: str, panel: str, category: str, message: str, *,
            severity: str = "warn", quote: str = "", redundant_with_art: bool = False) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "severity": severity,
        "confidence": "heuristic",
        "code": code,
        "panel": panel,
        "category": category,
        "message": message,
    }
    if quote:
        item["quote"] = quote[:60]
    if redundant_with_art:
        item["redundant_with_art"] = True
    return item


def audit(root: Path, chapter: str) -> Dict[str, Any]:
    chapter = normalize_chapter(chapter)
    panels = load_panels(root, chapter)
    findings: List[Dict[str, Any]] = []
    dialogue_lines = 0
    narration_lines = 0
    on_the_nose_lines = 0

    for panel in panels:
        pid = str(panel.get("panel_id") or "?")
        has_expr = panel_has_expression_anchor(panel)
        for row in panel_texts(panel):
            kind, speaker, text = row["kind"], row["speaker"], row["text"]
            if kind == "dialogue":
                dialogue_lines += 1
            else:
                narration_lines += 1
            hits = classify_line(kind, speaker, text)
            if hits and kind == "dialogue":
                on_the_nose_lines += 1
            for category in hits:
                redundant = has_expr and category in ("self_stated_emotion", "narrated_emotion_summary")
                msg = f"{pid} `{category}`：{text[:40]}——{CATEGORY_FIX[category]}"
                if redundant:
                    msg += "（画面已有 expression_id 演绎该情绪，对白/旁白再直陈=双重告知）"
                findings.append(finding(
                    "on_the_nose_line", pid, category, msg,
                    severity="warn", quote=text, redundant_with_art=redundant,
                ))

    rate = round(on_the_nose_lines / dialogue_lines, 3) if dialogue_lines else 0.0
    if dialogue_lines >= MIN_DIALOGUE_LINES and rate >= ON_THE_NOSE_RATE_WARN:
        findings.append(finding(
            "on_the_nose_rate_high", "-", "chapter_level",
            f"本话直白率 {rate:.0%}（{on_the_nose_lines}/{dialogue_lines} 对白行命中低隐含度信号，"
            f"阈 {ON_THE_NOSE_RATE_WARN:.0%}）——整体偏说教/直给，回 comic-script 把情绪与信息改成可画的演出。",
            severity="warn",
        ))

    summary = {
        "panels": len(panels),
        "dialogue_lines": dialogue_lines,
        "narration_lines": narration_lines,
        "on_the_nose_lines": on_the_nose_lines,
        "on_the_nose_rate": rate,
        "must": 0,  # advisory·审不是门：永不产出 must
        "warn": sum(1 for f in findings if f["severity"] == "warn"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
        "redundant_with_art": sum(1 for f in findings if f.get("redundant_with_art")),
    }
    return {
        "kind": KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "chapter": chapter,
        "thresholds": {
            "on_the_nose_rate_warn": ON_THE_NOSE_RATE_WARN,
            "min_dialogue_lines": MIN_DIALOGUE_LINES,
        },
        "summary": summary,
        "findings": findings,
    }


def render_md(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [
        f"# 漫画潜台词 / 去 AI 味机检 · {report.get('chapter')}",
        "",
        f"- 格 {s.get('panels')} · 对白 {s.get('dialogue_lines')} 行 · 旁白 {s.get('narration_lines')} 行",
        f"- 直白率 {float(s.get('on_the_nose_rate') or 0):.0%}（命中 {s.get('on_the_nose_lines')} 行）"
        f" · warn {s.get('warn')} · 画面双重告知 {s.get('redundant_with_art')}",
        "",
        "## Findings",
        "",
    ]
    icon = {"warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['message']}")
    if not report.get("findings"):
        lines.append("- ✅ 未命中低隐含度台词信号。")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    chapter = str(report.get("chapter") or "第1话")
    base = root / "生产数据"
    base.mkdir(parents=True, exist_ok=True)
    (base / f"comic_subtext_audit_{chapter}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (base / f"comic_subtext_audit_{chapter}.md").write_text(render_md(report), encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("chapter")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="人手排查用：有 warn 即 exit 1；正式 gate 从不用它硬拦（advisory·审不是门）")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    report = audit(root, ns.chapter)
    if ns.write:
        write_report(root, report)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_md(report), end="")
    return 1 if ns.strict and report["summary"]["warn"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
