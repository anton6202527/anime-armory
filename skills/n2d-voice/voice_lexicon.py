#!/usr/bin/env python3
"""专名/多音字读音词典——治「voice-first 管线里人名/境界/招式被 TTS 读错且跨集读音漂」。

为什么需要：n2d 是配音先行，但 render_voice 此前只清洗标记、对**怎么念**毫无控制。仙侠/宫斗
最容易翻车的恰是专名——多音字（重华/华/燕/朝/和…）、生僻字、自造术语，同一个名字一集里能读
两个音，极其出戏。G2P/多音字消歧是中文 TTS 前端的核心难题，但简单云端 TTS API（MiniMax/火山）
不收音素；唯一**跨后端通用**的纠音手段是「谐音替换」：把会读错的词换成读音相同、TTS 必读对的
字串，只喂给合成，**字幕/清单仍保留原字**。音素级后端（GLM-TTS 混合音素、零样本）则另存拼音。

铁律——念白文本与显示文本分离：
  to_spoken(原文) → 喂 TTS 的「念白文本」（谐音替换后）
  原文（items[i][1]）→ 进 时长清单/字幕 的「显示文本」（永远是规范字）
二者绝不混用：谐音字只下到声学层，观众看到的永远是正名。

词典：<作品根>/设定库/读音词典.json
  {"重华": {"pinyin":"chóng huá","spoken":"虫华","note":"剑名，非 zhòng"},
   "燕王": {"pinyin":"yān wáng","spoken":"烟王"}}
  数据源建议从 n2d-script 的 global_style.md「关键术语表」起一份清单（scan_glossary 可抽候选）。

纯函数（load/normalize/to_spoken/coverage）无依赖、带 pytest。render_voice 仅一行接入：
解包台词后 `text = voice_lexicon.to_spoken(text, LEXICON)`，故谐音只进合成不进清单。

用法（独立巡检）：python3 voice_lexicon.py <作品根> 第N集 [--json]
  扫 voiceover.txt：报词典命中（将纠音的词）+ 术语表里出现却无读音条目的专名（建议补）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple


# ---------- 纯函数（无依赖 · pytest 覆盖） ----------

def normalize_lexicon(raw: dict) -> Dict[str, dict]:
    """原始 json → {term: {pinyin, spoken, note}}。容错：值可为 str（视作 spoken）或 dict。
    丢弃空 term。纯函数·可测。"""
    out: Dict[str, dict] = {}
    for term, val in (raw or {}).items():
        t = str(term or "").strip()
        if not t:
            continue
        if isinstance(val, str):
            out[t] = {"pinyin": "", "spoken": val.strip(), "note": ""}
        elif isinstance(val, dict):
            out[t] = {"pinyin": str(val.get("pinyin") or "").strip(),
                      "spoken": str(val.get("spoken") or "").strip(),
                      "note": str(val.get("note") or "").strip()}
    return out


def _terms_longest_first(lexicon: Dict[str, dict]) -> List[str]:
    """长词优先匹配，避免「重华剑」先被「重」误吞——按 term 长度降序。"""
    return sorted(lexicon.keys(), key=len, reverse=True)


def to_spoken(text: str, lexicon: Dict[str, dict]) -> str:
    """把会读错的专名替换成「念白文本」（其 spoken 谐音串），只用于喂 TTS。
    无 spoken（仅给了 pinyin、留待音素后端）的词不改字面。长词优先、非重叠替换。纯函数·可测。"""
    if not text or not lexicon:
        return text
    terms = [t for t in _terms_longest_first(lexicon) if lexicon[t].get("spoken")]
    if not terms:
        return text
    pattern = re.compile("|".join(re.escape(t) for t in terms))
    return pattern.sub(lambda m: lexicon[m.group(0)]["spoken"], text)


def applied_terms(text: str, lexicon: Dict[str, dict]) -> List[str]:
    """text 里实际会被纠音的词（有 spoken 且出现）。纯函数·可测。"""
    hits: List[str] = []
    for t in _terms_longest_first(lexicon):
        if lexicon[t].get("spoken") and t in text:
            hits.append(t)
    return hits


def pinyin_hints(text: str, lexicon: Dict[str, dict]) -> List[Tuple[str, str]]:
    """text 里命中且带 pinyin 的词 → [(term, pinyin)]，供音素级后端（GLM-TTS/零样本）注入。纯函数·可测。"""
    out: List[Tuple[str, str]] = []
    for t in _terms_longest_first(lexicon):
        if lexicon[t].get("pinyin") and t in text:
            out.append((t, lexicon[t]["pinyin"]))
    return out


# ---------- IO ----------

def load_lexicon(root: str) -> Dict[str, dict]:
    """读 <root>/设定库/读音词典.json；缺/坏 → 空词典（render_voice 据此原样念，零副作用）。"""
    path = os.path.join(root, "设定库", "读音词典.json")
    try:
        return normalize_lexicon(json.load(open(path, encoding="utf-8")))
    except Exception:
        return {}


def scan_glossary_terms(root: str) -> List[str]:
    """从 global_style.md「关键术语表/境界/势力」段粗抽专名候选（2-6 字、非纯标点），
    供巡检比对「术语表有名、读音词典却没收」的漏网专名。best-effort，找不到返回 []。"""
    cands: set = set()
    for rel in ("脚本/global_style.md", "设定库/global_style.md", "脚本/世界观.md"):
        p = os.path.join(root, *rel.split("/"))
        if not os.path.isfile(p):
            continue
        txt = open(p, encoding="utf-8").read()
        # 抓「关键术语表/术语/境界/势力」之后的列表项与表格首列里的中文专名
        for m in re.finditer(r"[｜|·、，,：:]\s*([一-鿿]{2,6})", txt):
            cands.add(m.group(1))
        for m in re.finditer(r"(?m)^[\s\-*]+([一-鿿]{2,6})", txt):
            cands.add(m.group(1))
    return sorted(cands)


def _voiceover_text(root: str, ep: str) -> str:
    p = os.path.join(root, "脚本", ep, "voiceover.txt")
    try:
        return open(p, encoding="utf-8").read()
    except Exception:
        return ""


def analyze(root: str, ep: str) -> dict:
    lex = load_lexicon(root)
    vo = _voiceover_text(root, ep)
    res: dict = {"available": bool(lex), "terms": len(lex), "applied": [], "missing_pinyin": [],
                 "glossary_uncovered": [], "notes": []}
    if not lex:
        res["notes"].append("无 设定库/读音词典.json——TTS 将原样念，专名/多音字读错与跨集读音漂无防护。"
                            "建议据 global_style 术语表起一份（scan_glossary 列了候选）。")
    if vo:
        res["applied"] = applied_terms(vo, lex)
        res["missing_pinyin"] = [t for t in applied_terms(vo, lex) if not lex[t].get("pinyin")]
        covered = set(lex.keys())
        res["glossary_uncovered"] = [g for g in scan_glossary_terms(root)
                                     if g in vo and g not in covered][:30]
    else:
        res["notes"].append(f"缺 脚本/{ep}/voiceover.txt——只校词典本体，未比对本集台词。")
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 读音词典巡检：{ns.root} {ns.episode}（词条 {res['terms']}）===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if res["applied"]:
        print("将纠音（谐音只下到声学层，字幕保留正名）：" + "、".join(res["applied"]))
    if res["glossary_uncovered"]:
        print("⚠️ 术语表出现、读音词典未收（建议补，防读错/读音漂）：" + "、".join(res["glossary_uncovered"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
