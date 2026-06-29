#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d 源语言/文体体检 + 源理解层闸（拆集前最上游前置）。

章程默认源小说是**现代中文白话文**，但没明文要求。真遇到**文言文/古文**或**外文小说**时，
直接按白话拆集会理解错（source_analyze 的说话动词/引号正则全是现代白话假设）、术语/典故/称谓
全崩。本脚本做三件事：
  1) **体检**：确定性扫源文本 → register ∈ {modern_zh(默认放行) / classical_zh(文言文) / non_chinese(外文)}，
     另标 traditional(繁体白话·只提示不拦)。纯关键词密度判定·不调模型·不臆造。
  2) **提示**：register 非现代白话且未建「源理解层」→ check 返回 needs_comprehension，
     调用方（run.py script_stage1 prework）据此**先停下提示用户**，不闷头拆集。
  3) **建理解层**：--scaffold 写 设定库/source_comprehension.md（现代白话理解层 + 古今词/术语对照 +
     文化/称谓注释 + 改编边界）+ source_comprehension.json（机器记录）。人工补全并把 status 置 confirmed 后，
     check 放行，下游**从理解层（现代白话）拆集**，保留 curated 的古语/术语作台词风格与意象。

用法：
  python3 source_language.py <作品根>               # 体检 + check（人读）
  python3 source_language.py <作品根> --json        # 机器可读 verdict
  python3 source_language.py <作品根> --scaffold     # 建/刷新 源理解层脚手架
  python3 source_language.py <作品根> --scaffold --json

只读源副本 小说/*.txt（与 source_check 同源）。纯标准库。测试：
  cd skills/n2d-script/scripts && python3 -m pytest test_source_language.py
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

KIND = "n2d_source_comprehension"
COMPREHENSION_JSON_REL = os.path.join("设定库", "source_comprehension.json")
COMPREHENSION_MD_REL = os.path.join("设定库", "source_comprehension.md")

# ── 文体判定的标记集（密度判定·单一真值源·可测可调）─────────────────────────
# 文言文强标记（现代白话几乎不用或极少用；之/而/则/其 现代也用→不入强集，避免误判）。
_CLASSICAL_STRONG = "之也矣焉哉乎曰兮耳邪欤歟尔夫盖此乃为汝吾"
# 现代白话语法虚词（高频出现=白话；尤其「的」在白话占 2-5%，文言文几乎为 0）。
# 只收**文言文几乎不用**的现代虚词；故意剔除 可以/已经/知道/现在 等文言也常见的词，避免短文言样本误判。
_MODERN_MARKERS = ("了", "吗", "呢", "着", "这个", "那个", "什么", "我们",
                   "他们", "她们", "怎么", "不是", "一样", "时候", "起来", "出来")
# 繁体专有字（仅提示繁体白话·不拦截；现代繁体白话完全可直接理解）。
_TRAD_ONLY = "個們這說裡麼長東報應發瞭隻來時對開關問題實現點線業"
_CJK_RE = re.compile(r"[一-鿿]")
_HIRAGANA_KATAKANA = re.compile(r"[぀-ヿ]")
_HANGUL = re.compile(r"[가-힣]")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_LATIN_WORD = re.compile(r"[A-Za-z]")

# 判定阈值（保守·宁可放行现代白话也别误拦）：
CLASSICAL_STRONG_MIN = 0.020   # 强文言标记密度 ≥ 2/100 字
MODERN_MARKER_MAX = 0.012      # 且现代虚词密度 < 1.2/100 字
DE_DENSITY_MAX = 0.012         # 且「的」密度 < 1.2/100 字（白话最强判别特征）
NON_CHINESE_CJK_MAX = 0.50     # CJK 占比 < 50% → 判外文
MIN_CONTENT_CHARS = 60         # 去元数据后正文 < 此长度 → 证据不足，按现代白话放行（不误拦短样本/桩）

# 元数据/frontmatter 行（非正文）：markdown 标题/分隔、版权/标签/简介/作者/书名等声明行，判文体前剥离。
_META_LINE_RE = re.compile(r"^\s*(#|---|>|\[|copyright|版权|标签|简介|作者|书名|来源|平台|看点)[:：\s]",
                           re.IGNORECASE)


def _strip_meta(text: str) -> str:
    """剥离开头/通篇的元数据声明行，只留正文供文体判定（避免 latin 版权头等拉偏 CJK 占比）。"""
    keep = []
    for line in (text or "").splitlines():
        if _META_LINE_RE.match(line):
            continue
        keep.append(line)
    return "\n".join(keep)


def _density(text: str, chars: str) -> float:
    if not text:
        return 0.0
    cset = set(chars)
    return sum(1 for c in text if c in cset) / len(text)


def _count_substr(text: str, needles) -> int:
    return sum(text.count(n) for n in needles)


def classify_register(text: str) -> dict:
    """源文本 → {register, lang_guess, cjk_ratio, signals, confidence, scores}。纯函数·可测。

    register: modern_zh（含繁体白话·默认放行）/ classical_zh（文言文）/ non_chinese（外文）。
    先剥元数据行，再判；正文过短（证据不足）一律按现代白话放行，不误拦。"""
    raw = _strip_meta(text or "")
    compact = re.sub(r"\s+", "", raw)
    if len(compact) < MIN_CONTENT_CHARS:
        return {"register": "modern_zh", "lang_guess": "modern_baihua", "cjk_ratio": 0.0,
                "confidence": "low",
                "signals": [f"去元数据后正文仅 {len(compact)} 字 < {MIN_CONTENT_CHARS}，证据不足→按现代白话放行"],
                "scores": {}}
    n = len(compact)
    if n == 0:
        return {"register": "modern_zh", "lang_guess": "unknown", "cjk_ratio": 0.0,
                "confidence": "low", "signals": ["源文本为空"], "scores": {}}
    cjk = len(_CJK_RE.findall(compact))
    cjk_ratio = cjk / n
    signals = []

    # 1) 外文：CJK 占比过低 → 判 non_chinese，再猜脚本/语种。
    if cjk_ratio < NON_CHINESE_CJK_MAX:
        if _HIRAGANA_KATAKANA.search(compact):
            guess = "japanese"
        elif _HANGUL.search(compact):
            guess = "korean"
        elif _CYRILLIC.search(compact):
            guess = "russian/cyrillic"
        elif _LATIN_WORD.search(compact):
            guess = "latin-script (english/european)"
        else:
            guess = "non-chinese (unknown script)"
        signals.append(f"CJK 占比 {cjk_ratio:.0%} < {NON_CHINESE_CJK_MAX:.0%}（疑外文：{guess}）")
        return {"register": "non_chinese", "lang_guess": guess, "cjk_ratio": round(cjk_ratio, 3),
                "confidence": "high" if cjk_ratio < 0.15 else "medium",
                "signals": signals, "scores": {"cjk_ratio": round(cjk_ratio, 3)}}

    # 2) 文言文 vs 现代白话：基于强文言标记 / 现代虚词 / 「的」密度。
    cjk_text = "".join(c for c in compact if _CJK_RE.match(c))
    cjk_n = max(1, len(cjk_text))
    classical = sum(1 for c in cjk_text if c in set(_CLASSICAL_STRONG)) / cjk_n
    de = cjk_text.count("的") / cjk_n
    modern = _count_substr(compact, _MODERN_MARKERS) / cjk_n
    yue = cjk_text.count("曰")  # 「曰」作说话动词=强文言信号
    trad = sum(1 for c in cjk_text if c in set(_TRAD_ONLY)) / cjk_n
    scores = {"classical_strong": round(classical, 4), "de_density": round(de, 4),
              "modern_marker": round(modern, 4), "yue_count": yue,
              "trad_ratio": round(trad, 4), "cjk_ratio": round(cjk_ratio, 3)}

    is_classical = (classical >= CLASSICAL_STRONG_MIN and de < DE_DENSITY_MAX
                    and modern < MODERN_MARKER_MAX)
    if is_classical:
        signals.append(f"强文言标记密度 {classical:.1%} ≥ {CLASSICAL_STRONG_MIN:.0%}"
                       f"，且「的」密度 {de:.1%}、现代虚词 {modern:.1%} 双低（疑文言文/古文）")
        if yue:
            signals.append(f"出现「曰」{yue} 次（文言说话动词）")
        conf = "high" if (classical >= 0.03 and de < 0.005) else "medium"
        return {"register": "classical_zh", "lang_guess": "classical_chinese",
                "cjk_ratio": round(cjk_ratio, 3), "confidence": conf,
                "signals": signals, "scores": scores}

    # 3) 现代白话（默认放行）。繁体只提示不拦。
    if trad >= 0.02:
        signals.append(f"繁体专有字密度 {trad:.1%}（繁体白话·可直接理解·仅提示）")
    signals.append(f"现代白话特征：「的」密度 {de:.1%}、现代虚词 {modern:.1%}")
    return {"register": "modern_zh", "lang_guess": "traditional_baihua" if trad >= 0.02 else "modern_baihua",
            "cjk_ratio": round(cjk_ratio, 3), "confidence": "high",
            "signals": signals, "scores": scores}


def _find_source_text(root: str):
    cands = sorted(glob.glob(os.path.join(root, "小说", "*.txt")))
    return cands[0] if cands else None


def _read_comprehension(root: str):
    p = os.path.join(root, COMPREHENSION_JSON_REL)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def check(root: str) -> dict:
    """体检 + 闸判定。返回 {verdict, register, ...}。

    verdict ∈ {pass, needs_comprehension, no_source}。
    - modern_zh → pass（默认现代白话，直接拆集）。
    - classical_zh / non_chinese 且无 confirmed 理解层 → needs_comprehension（先提示+建层）。
    - 已建 confirmed 且 register 匹配 → pass（下游从理解层拆集）。"""
    src = _find_source_text(root)
    if not src:
        return {"verdict": "no_source", "register": None,
                "message": f"未找到源副本 {root}/小说/*.txt（split_novel 会写规范副本）。"}
    with open(src, encoding="utf-8") as f:
        text = f.read()
    cls = classify_register(text)
    register = cls["register"]
    out = {"verdict": "pass", "register": register, "lang_guess": cls["lang_guess"],
           "confidence": cls["confidence"], "signals": cls["signals"],
           "scores": cls["scores"], "source": os.path.relpath(src, root)}
    if register == "modern_zh":
        return out

    comp = _read_comprehension(root)
    confirmed = bool(comp) and str(comp.get("status") or "").lower() == "confirmed" \
        and comp.get("register") == register
    if confirmed:
        out["verdict"] = "pass"
        out["comprehension"] = "confirmed"
        out["message"] = (f"源文本为 {register}；源理解层已确认（{COMPREHENSION_MD_REL}）→ "
                          "下游从现代白话理解层拆集，保留 curated 古语/术语。")
        return out
    out["verdict"] = "needs_comprehension"
    label = "文言文/古文" if register == "classical_zh" else f"外文（{cls['lang_guess']}）"
    out["message"] = (
        f"⚠️ 源文本疑似 **{label}**（{'；'.join(cls['signals'][:2])}）。章程默认源是现代中文白话文；"
        f"按白话直接拆集会理解错术语/典故/称谓。请先确认语言，再建『源理解层』：\n"
        f"  1) python3 skills/n2d-script/scripts/source_language.py {root} --scaffold\n"
        f"  2) 补全 {COMPREHENSION_MD_REL}（现代白话理解层 + 古今词/术语对照 + 文化注释 + 改编边界）\n"
        f"  3) 把 {COMPREHENSION_JSON_REL} 的 status 置 confirmed，再继续拆集（下游从理解层拆）。")
    return out


_CLASSICAL_TEMPLATE = """# 源理解层 — {title}

> register=**{register}**（{lang_guess}）· 体检置信度 {confidence}。
> 章程默认源是现代中文白话文；本文件是文言文/外文源的**理解层**：下游拆集、写 voiceover 从这里取
> 现代白话理解，**不直接照搬文言原句**，但保留下方 curated 的古语/术语/意象作台词风格与视觉锚点。
> 体检信号：{signals}

## 1. 现代白话理解层（逐章/逐段释义·parse+gloss）
> 把文言原文转成准确的现代白话理解（不是逐字直译，是读懂剧情/动机/因果）。建议逐章一段。
- 第N章：……（待补）

## 2. 古今词 · 典故 · 称谓对照表
> 关键文言词/典故/官职/称谓 → 现代含义 + 是否保留作台词风格。决定哪些古语保留（增古意）哪些转白话（保理解）。
| 文言/典故 | 现代含义 | 改编处理（保留古语台词 / 转白话 / 视觉化） |
|---|---|---|
| （待补） |  |  |

## 3. 文化 / 制度 / 时代注释
> 礼制、官制、地理、典章、风俗等下游出图/分镜需要的背景（避免画错服制/场景/道具）。
- （待补）

## 4. 改编边界（保留 vs 现代化）
> 哪些意象/术语必须保留（视觉奇观/文化标识），哪些必须现代化（否则观众看不懂），台词古白比例倾向。
- 保留：……
- 现代化：……
- 台词风格：……（如"半文半白"/"现代白话+少量古称谓"）

---
确认理解层补全后，把 `设定库/source_comprehension.json` 的 `status` 改为 `confirmed`，再继续拆集。
"""

_FOREIGN_TEMPLATE = """# 源理解层 — {title}

> register=**{register}**（疑 {lang_guess}）· 体检置信度 {confidence}。
> 章程默认源是现代中文白话文；本文件是外文源的**理解层 + 本地化（transcreation）方案**：下游拆集、
> 写 voiceover 从这里取现代中文理解，保留下方 curated 的专名/文化引用/习语本地化决策。
> 体检信号：{signals}

## 1. 现代中文理解层（译文 / 释义）
> 把外文原文转成准确的现代中文理解（读懂剧情/动机/因果）。建议逐章一段。
- 第N章：……（待补）

## 2. 专名 · 术语 · 文化引用 本地化表
> 人名/地名/机构/专有名词/文化引用 → 统一中文译名 + 处理（音译/意译/保留原文/加注）。跨集一致。
| 原文 | 统一中文译名 | 处理（音译/意译/保留/加注） |
|---|---|---|
| （待补） |  |  |

## 3. 习语 / 双关 / 笑点 transcreation 方案
> 直译会丢的习语/双关/幽默/文化梗 → 等效中文表达或视觉化方案（保情绪与笑点，非字面）。
- （待补）

## 4. 改编边界（本地化 vs 异域感）
> 哪些异域元素保留（世界观/视觉差异化卖点），哪些本地化（否则观众有距离感），称谓/语体倾向。
- 保留：……
- 本地化：……
- 语体风格：……

---
确认理解层补全后，把 `设定库/source_comprehension.json` 的 `status` 改为 `confirmed`，再继续拆集。
"""


def scaffold(root: str) -> dict:
    """建/刷新源理解层脚手架（按 register 选模板）。不覆盖已 confirmed 的 md 正文（只回填机器记录）。"""
    src = _find_source_text(root)
    if not src:
        return {"ok": False, "message": f"未找到源副本 {root}/小说/*.txt。"}
    with open(src, encoding="utf-8") as f:
        text = f.read()
    cls = classify_register(text)
    register = cls["register"]
    title = os.path.splitext(os.path.basename(src))[0]
    setdir = os.path.join(root, "设定库")
    os.makedirs(setdir, exist_ok=True)
    md_path = os.path.join(root, COMPREHENSION_MD_REL)
    json_path = os.path.join(root, COMPREHENSION_JSON_REL)

    prev = _read_comprehension(root)
    # 已有且已 confirmed → 不动 md 正文（保人工成果），只刷新机器记录的体检信号。
    wrote_md = False
    if not os.path.exists(md_path):
        tmpl = _CLASSICAL_TEMPLATE if register == "classical_zh" else _FOREIGN_TEMPLATE
        signals_line = "；".join(cls["signals"]) or "（无）"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(tmpl.format(title=title, register=register, lang_guess=cls["lang_guess"],
                                confidence=cls["confidence"], signals=signals_line))
        wrote_md = True

    status = (prev or {}).get("status") if prev and prev.get("register") == register else None
    record = {
        "kind": KIND, "version": 1, "register": register, "lang_guess": cls["lang_guess"],
        "confidence": cls["confidence"], "signals": cls["signals"], "scores": cls["scores"],
        "source": os.path.relpath(src, root),
        "status": status or "draft",
        "comprehension_doc": COMPREHENSION_MD_REL,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return {"ok": True, "register": register, "wrote_md": wrote_md,
            "md": COMPREHENSION_MD_REL, "json": COMPREHENSION_JSON_REL, "status": record["status"],
            "message": (f"源理解层脚手架已就绪（register={register}，status={record['status']}）。"
                        f"补全 {COMPREHENSION_MD_REL} 后把 status 置 confirmed 再拆集。")}


def main(argv=None):
    ap = argparse.ArgumentParser(description="n2d 源语言/文体体检 + 源理解层闸")
    ap.add_argument("root", help="n2d 作品根")
    ap.add_argument("--scaffold", action="store_true", help="建/刷新源理解层脚手架")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.scaffold:
        res = scaffold(args.root)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(("✅ " if res.get("ok") else "⛔ ") + res.get("message", ""))
        return 0 if res.get("ok") else 2

    res = check(args.root)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["verdict"] == "pass" else 1
    verdict = res["verdict"]
    icon = {"pass": "✅", "needs_comprehension": "⚠️", "no_source": "ℹ️"}.get(verdict, "•")
    print(f"{icon} 源语言体检：register={res.get('register')} · verdict={verdict}")
    for s in res.get("signals", []):
        print(f"   - {s}")
    if res.get("message"):
        print(res["message"])
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
