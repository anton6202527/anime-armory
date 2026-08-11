#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d 源语言/文体体检 + 源理解合同闸（拆集前最上游前置）。

章程以前默认源小说是**现代中文白话文**，但真实生产里“看懂语言”还不够。长篇伏笔、爽点账、
人物动机、因果链、设定/战力规则如果不先变成可审计理解层，后面分镜再专业也是在错误理解上精修。
本脚本做三件事：
  1) **体检**：确定性扫源文本 → register ∈ {modern_zh(现代白话) / classical_zh(文言文) / non_chinese(外文)}，
     另标 traditional(繁体白话·提示)，并在不破坏 register 兼容性的前提下识别
     late_imperial_vernacular（近世章回白话：白话叙事夹文言、韵文、说书套语）。纯关键词密度判定·不调模型·不臆造。
  2) **闸门**：只要存在源文本，就必须有 confirmed 的 `source_comprehension.json`，且其中
     `understanding_contract` 的现代理解、承诺账、人物动机、因果链、伏笔账和战力/规则策略可机检。
     调用方（run.py script_stage1 prework）据此**先停下提示用户**，不闷头拆集。
  3) **建理解层**：--scaffold 写 设定库/source_comprehension.md（现代白话理解层 + 古今词/术语对照 +
     文化/称谓注释 + 改编边界 + 叙事/因果/战力合同）+ source_comprehension.json（机器记录）。
     人工补全 JSON 合同并把 status 置 confirmed 后，check 放行；下游**从理解层（现代白话）拆集**。

用法：
  python3 source_language.py <作品根>               # 体检 + 源理解合同 check（人读）
  python3 source_language.py <作品根> --json        # 机器可读 verdict
  python3 source_language.py <作品根> --scaffold     # 建/刷新 源理解层脚手架
  python3 source_language.py <作品根> --scaffold --json

只读源副本 小说/*.txt（与 source_check 同源）。没有源副本时不阻断旧项目/测试夹具，但真实首切应先写源副本。
纯标准库。测试：
  cd skills/n2d/n2d-script/scripts && python3 -m pytest test_source_language.py
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
CONTRACT_KEY = "understanding_contract"

# ── 文体判定的标记集（密度判定·单一真值源·可测可调）─────────────────────────
# 文言文强标记（现代白话几乎不用或极少用；之/而/则/其 现代也用→不入强集，避免误判）。
_CLASSICAL_STRONG = "之也矣焉哉乎曰兮耳邪欤歟尔夫盖此乃为汝吾"
# 现代白话语法虚词（高频出现=白话；尤其「的」在白话占 2-5%，文言文几乎为 0）。
# 只收**文言文几乎不用**的现代虚词；故意剔除 可以/已经/知道/现在 等文言也常见的词，避免短文言样本误判。
_MODERN_MARKERS = ("了", "吗", "呢", "着", "这个", "那个", "什么", "我们",
                   "他们", "她们", "怎么", "不是", "一样", "时候", "起来", "出来")
# 明清章回体/近世白话常见的叙述套语。它不是 classical_zh：正文通常已有白话语法，
# 但若套普通现代白话模板，会漏掉韵文、说书人评论、古今称谓和制度语境的适配工作。
_LATE_IMPERIAL_MARKERS = (
    "看官", "話說", "话说", "且說", "且说", "不題", "不题", "按下", "單表", "单表",
    "正是", "有詩為證", "有诗为证", "詩曰", "诗曰", "詞曰", "词曰", "怎生", "恁的",
    "端的", "那廝", "那厮", "小人", "娘子", "官人", "奴家",
)
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

POWER_SYSTEM_MARKERS = (
    "境界", "修为", "灵根", "战力", "等级", "系统", "面板", "属性", "经验值", "升级",
    "炼气", "筑基", "金丹", "元婴", "渡劫", "功法", "法宝", "武魂", "异能",
)
POWER_SYSTEM_CORE_MARKERS = ("系统", "面板", "属性", "经验值", "升级", "战力", "修为", "靈根", "灵根")

CONTRACT_REQUIRED = (
    "modern_understanding",
    "episode_promise_basis",
    "character_motives",
    "causality_chain",
    "foreshadowing_ledger",
    "adaptation_boundaries",
    "power_system_rules",
)

# 元数据/frontmatter 行（非正文）：markdown 标题/分隔、版权/标签/简介/作者/书名等声明行，判文体前剥离。
_META_LINE_RE = re.compile(r"^\s*(#|---|>|\[|copyright|版权|标签|简介|作者|书名|来源|平台|看点)[:：\s]",
                           re.IGNORECASE)
_CHAPTER_UNIT = "章节回囬囘廻節节卷"
_CHAPTER_HEADING_LINE_RE = re.compile(
    rf"^\s*(?:第\s*[零〇一二三四五六七八九十百千万两\d]+\s*[{_CHAPTER_UNIT}]|Chapter\s+\d+)", re.I
)
_EDITED_HEADING_RE = re.compile(
    rf"^\s*(?:\[编辑\]\s*)?(第\s*[零〇一二三四五六七八九十百千万两\d]+\s*[{_CHAPTER_UNIT}])\s*(.*)$",
    re.I,
)


def _strip_meta(text: str) -> str:
    """剥离开头/通篇的元数据声明行，只留正文供文体判定（避免 latin 版权头等拉偏 CJK 占比）。"""
    keep = []
    for line in (text or "").splitlines():
        if _META_LINE_RE.match(line):
            continue
        keep.append(line)
    return "\n".join(keep)


def _fold_adjacent_duplicate_chapter_headings(text: str) -> str:
    """Fold only physically adjacent, exactly equal chapter-heading lines."""
    kept = []
    previous = None
    for line in (text or "").splitlines():
        if previous is not None and line == previous and _CHAPTER_HEADING_LINE_RE.match(line):
            previous = line
            continue
        kept.append(line)
        previous = line
    return "\n".join(kept)


def _filled(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and not re.search(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", text, re.I)
    if isinstance(value, list):
        return any(_filled(v) for v in value)
    if isinstance(value, dict):
        return any(_filled(v) for v in value.values())
    return bool(value)


def extract_source_unit_inventory(text: str) -> list[dict]:
    """Extract a compact, deterministic chapter/hui inventory without pretending to summarize it.

    Chaptered web exports often add volume wrappers such as ``第1章 … 第一回`` around the real
    ``第一囬 …`` headings. If at least three hui-style headings exist, prefer those and exclude the
    wrapper headings; otherwise retain all recognized chapter units. Exact duplicate headings fold.
    """
    rows = []
    for line_no, line in enumerate((text or "").splitlines(), 1):
        m = _EDITED_HEADING_RE.match(line)
        if not m:
            continue
        unit, title = m.group(1).strip(), m.group(2).strip()
        rows.append({"source_span": unit, "title": title, "line": line_no})
    hui_rows = [row for row in rows if re.search(r"[回囬囘廻]", row["source_span"])]
    selected = hui_rows if len(hui_rows) >= 3 else rows
    out, seen = [], set()
    for row in selected:
        key = (row["source_span"], row["title"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"unit_id": f"SRC_UNIT_{len(out) + 1:04d}", **row})
    return out


def detect_source_traits(text: str) -> dict:
    # Fold before metadata stripping so two headings separated in the original
    # source can never become "adjacent" merely because a metadata line vanished.
    raw = _strip_meta(_fold_adjacent_duplicate_chapter_headings(text or ""))
    compact = re.sub(r"\s+", "", raw)
    chapters = len(re.findall(
        rf"(?:第\s*[零〇一二三四五六七八九十百千万两\d]+\s*[{_CHAPTER_UNIT}]|Chapter\s+\d+)",
        raw,
        re.I,
    ))
    power_counts = {m: raw.count(m) for m in POWER_SYSTEM_MARKERS if raw.count(m)}
    power_total = sum(power_counts.values())
    core_total = sum(raw.count(m) for m in POWER_SYSTEM_CORE_MARKERS)
    # 长篇里“境界”偶见一两次常是普通词义，不能据此误判修炼/系统题材。
    has_power = power_total >= 3 and (len(power_counts) >= 2 or core_total >= 3)
    late_counts = {m: raw.count(m) for m in _LATE_IMPERIAL_MARKERS if raw.count(m)}
    return {
        "content_chars": len(compact),
        "chapter_markers": chapters,
        "long_form": len(compact) >= 50000 or chapters >= 20,
        "power_system_likely": has_power,
        "power_system_signals": power_counts,
        "late_imperial_marker_count": sum(late_counts.values()),
        "late_imperial_marker_types": sorted(late_counts),
    }


def _default_contract(register: str, traits: dict | None = None) -> dict:
    traits = traits or {}
    contract = {
        "modern_understanding": "",
        "episode_promise_basis": [
            {"trace_id": "SRC_PROMISE_001", "promise": "", "opened_at": "", "payoff_or_progress": "", "risk_if_cut": ""}
        ],
        "character_motives": [
            {"trace_id": "SRC_MOTIVE_001", "character": "", "want": "", "obstacle": "", "choice_pressure": "", "arc_delta": ""}
        ],
        "causality_chain": [
            {"trace_id": "SRC_CAUSE_001", "cause": "", "effect": "", "must_keep": "", "adaptation_note": ""}
        ],
        "foreshadowing_ledger": [
            {"trace_id": "SRC_FORESHADOW_001", "setup": "", "payoff_plan": "", "status": "", "do_not_drop_reason": ""}
        ],
        "adaptation_boundaries": {
            "preserve": [],
            "modernize_or_compress": [],
            "do_not_change": [],
        },
        "power_system_rules": {
            "applicable": "yes" if traits.get("power_system_likely") else "no",
            "level_or_rank_rules": [],
            "growth_constraints": [],
            "combat_consistency_rules": [],
            "not_applicable_reason": "" if traits.get("power_system_likely") else "非战力/系统/修炼题材，暂无等级战力规则。",
        },
        "source_register_strategy": {
            "register": register,
            "profile": traits.get("register_profile", ""),
            "dialogue_style": "",
            "terms_to_keep": [],
            "terms_to_translate": [],
        },
    }
    if traits.get("register_profile") == "late_imperial_vernacular":
        contract["premodern_adapter"] = {
            "coverage_scope": "",
            "unit_glosses": [{
                "source_span": "",
                "modern_summary": "",
                "dramatic_function": "",
                "trace_ids": [],
            }],
            "historical_terms": [{
                "source_term": "",
                "modern_meaning": "",
                "screen_treatment": "",
            }],
            "verse_and_commentary_policy": "",
            "narrator_formula_policy": "",
            "historical_context_policy": "",
            "sensitive_content_policy": "",
            "dialogue_style_target": "",
        }
    return contract


def _merge_contract(base: dict, existing) -> dict:
    if not isinstance(existing, dict):
        return base
    out = dict(base)
    for key, value in existing.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            merged = dict(out[key])
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    return out


def comprehension_contract_issues(record: dict | None, expected_register: str, traits: dict | None = None) -> list[str]:
    traits = traits or {}
    issues: list[str] = []
    if not isinstance(record, dict):
        return ["缺 source_comprehension.json。"]
    if record.get("kind") != KIND:
        issues.append(f"kind 必须是 {KIND}。")
    if record.get("register") != expected_register:
        issues.append(f"register 不匹配：record={record.get('register')!r}, expected={expected_register!r}。")
    if str(record.get("status") or "").strip().lower() != "confirmed":
        issues.append("status 不是 confirmed。")
    contract = record.get(CONTRACT_KEY)
    if not isinstance(contract, dict):
        issues.append(f"缺 {CONTRACT_KEY}。")
        return issues
    for key in CONTRACT_REQUIRED:
        if not _filled(contract.get(key)):
            issues.append(f"{CONTRACT_KEY}.{key} 未补齐。")
    power = contract.get("power_system_rules") if isinstance(contract.get("power_system_rules"), dict) else {}
    if traits.get("power_system_likely"):
        needed = ("level_or_rank_rules", "growth_constraints", "combat_consistency_rules")
        missing = [key for key in needed if not _filled(power.get(key))]
        if missing:
            issues.append("疑似战力/系统/修炼题材，power_system_rules 缺：" + "、".join(missing))
    elif not _filled(power.get("not_applicable_reason")) and str(power.get("applicable") or "").lower() in {"no", "false", "否"}:
        issues.append("非战力题材也必须写 power_system_rules.not_applicable_reason。")
    if traits.get("register_profile") == "late_imperial_vernacular":
        adapter = contract.get("premodern_adapter")
        if not isinstance(adapter, dict):
            issues.append("近世章回白话源缺 understanding_contract.premodern_adapter。")
        else:
            required = (
                "coverage_scope", "unit_glosses", "historical_terms", "verse_and_commentary_policy",
                "narrator_formula_policy", "historical_context_policy", "sensitive_content_policy",
                "dialogue_style_target",
            )
            missing = [key for key in required if not _filled(adapter.get(key))]
            if missing:
                issues.append("近世章回白话适配合同缺：" + "、".join(missing))
    return issues


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

    # 3) 现代白话。register 本身不阻断；是否放行取决于源理解合同。
    late_counts = {m: compact.count(m) for m in _LATE_IMPERIAL_MARKERS if compact.count(m)}
    late_total = sum(late_counts.values())
    late_density = late_total / cjk_n
    # 至少三类套语且密度达到 0.06% 才识别；避免现代文偶写一句“话说”就误套章回体模板。
    late_imperial = len(late_counts) >= 3 and late_total >= 6 and late_density >= 0.0006
    scores["late_imperial_marker_density"] = round(late_density, 5)
    scores["late_imperial_marker_types"] = len(late_counts)
    scores["late_imperial_marker_count"] = late_total
    if late_imperial:
        signals.append(
            f"章回体/近世白话套语 {late_total} 处、{len(late_counts)} 类（密度 {late_density:.2%}）"
        )
    if trad >= 0.02:
        signals.append(f"繁体专有字密度 {trad:.1%}（繁体白话·可直接理解·仅提示）")
    signals.append(f"现代白话特征：「的」密度 {de:.1%}、现代虚词 {modern:.1%}")
    return {"register": "modern_zh", "lang_guess": (
                "late_imperial_vernacular" if late_imperial else
                ("traditional_baihua" if trad >= 0.02 else "modern_baihua")
            ),
            "register_profile": "late_imperial_vernacular" if late_imperial else "modern_baihua",
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
    """体检 + 源理解合同闸判定。返回 {verdict, register, ...}。

    verdict ∈ {pass, needs_comprehension, no_source}。
    - 没有源副本 → no_source（兼容旧项目/恢复态；真实首切仍应先写 小说/*.txt）。
    - 有源文本 → 必须有 confirmed 且字段齐全的 source_comprehension.json。
    - 已建 confirmed 且 register/contract 通过 → pass（下游从理解层拆集）。"""
    src = _find_source_text(root)
    if not src:
        return {"verdict": "no_source", "register": None,
                "message": f"未找到源副本 {root}/小说/*.txt（split_novel 会写规范副本）。"}
    with open(src, encoding="utf-8") as f:
        text = f.read()
    cls = classify_register(text)
    traits = detect_source_traits(text)
    traits["register_profile"] = cls.get("register_profile") or cls.get("lang_guess")
    inventory = extract_source_unit_inventory(text)
    traits["source_unit_count"] = len(inventory)
    register = cls["register"]
    out = {"verdict": "pass", "register": register, "lang_guess": cls["lang_guess"],
           "confidence": cls["confidence"], "signals": cls["signals"],
           "scores": cls["scores"], "source": os.path.relpath(src, root),
           "source_traits": traits}
    comp = _read_comprehension(root)
    issues = comprehension_contract_issues(comp, register, traits)
    if not issues:
        out["verdict"] = "pass"
        out["comprehension"] = "confirmed"
        out["message"] = (
            f"源文本 register={register}；源理解合同已确认（{COMPREHENSION_JSON_REL} / {COMPREHENSION_MD_REL}）→ "
            "下游从理解层拆集，保留人物动机、因果链、伏笔账、爽点承诺和战力/规则约束。"
        )
        return out
    out["verdict"] = "needs_comprehension"
    out["contract_issues"] = issues
    label = ("近世章回白话（白话叙事夹文言/韵文/说书套语）"
             if cls.get("register_profile") == "late_imperial_vernacular"
             else ("现代白话" if register == "modern_zh" else ("文言文/古文" if register == "classical_zh" else f"外文（{cls['lang_guess']}）")))
    out["message"] = (
        f"⚠️ 源文本为 **{label}**（{'；'.join(cls['signals'][:2])}）。拆集前必须先确认『源理解合同』，"
        f"把编剧理解、长篇伏笔、爽点账、人物动机、因果链、设定/战力规则变成可审计输入；当前缺口："
        f"{'；'.join(issues[:8])}\n"
        f"  1) python3 skills/n2d/n2d-script/scripts/source_language.py {root} --scaffold\n"
        f"  2) 补全 {COMPREHENSION_MD_REL} 和 {COMPREHENSION_JSON_REL}.{CONTRACT_KEY}\n"
        f"  3) 把 {COMPREHENSION_JSON_REL} 的 status 置 confirmed，再继续拆集。")
    return out


_MODERN_TEMPLATE = """# 源理解合同 — {title}

> register=**{register}**（{lang_guess}）· 体检置信度 {confidence}。
> 本文件是拆集前的**编剧理解合同**：下游不能直接按章节机械切分，必须先消费这里的现代白话理解、
> 爽点/承诺账、人物动机、因果链、伏笔账和设定/战力规则。
> 体检信号：{signals}

## 1. 现代白话理解层（剧情事实，不是分镜）
- （待补）按章节/段落概括关键事件、选择、后果、人物状态变化。

## 2. 爽点 / 承诺 / 兑现账
| 承诺/悬念 | 打开位置 | 兑现/推进计划 | 如果剪掉会破坏什么 |
|---|---|---|---|
| （待补） |  |  |  |

## 3. 人物动机与压力
| 角色 | 想要什么 | 阻碍 | 当前选择压力 | 弧线变化 |
|---|---|---|---|---|
| （待补） |  |  |  |  |

## 4. 因果链
| 原因 | 结果 | 必须保留的剧情功能 | 改编说明 |
|---|---|---|---|
| （待补） |  |  |  |

## 5. 伏笔 / 回收 / 延迟兑现
| 伏笔 | 回收计划 | 状态 | 不可删除原因 |
|---|---|---|---|
| （待补） |  |  |  |

## 6. 设定 / 战力 / 系统规则
> 无战力/系统/等级体系也要写明“不适用原因”，避免后续镜头自由发明规则。
- 规则：……
- 成长限制：……
- 战力一致性：……

## 7. 改编边界
- 必须保留：……
- 可压缩/现代化：……
- 禁止改动：……

---
确认后同步补全 `设定库/source_comprehension.json` 的 `understanding_contract`，并把 `status` 改为 `confirmed`。
"""


_CONTRACT_MD_APPENDIX = """

## 5. 编剧理解合同（所有 register 必填）
> 下方内容必须同步写入 `设定库/source_comprehension.json` 的 `understanding_contract`，否则机器 gate 不放行。

### 5.1 爽点 / 承诺 / 兑现账
| 承诺/悬念 | 打开位置 | 兑现/推进计划 | 如果剪掉会破坏什么 |
|---|---|---|---|
| （待补） |  |  |  |

### 5.2 人物动机与压力
| 角色 | 想要什么 | 阻碍 | 当前选择压力 | 弧线变化 |
|---|---|---|---|---|
| （待补） |  |  |  |  |

### 5.3 因果链
| 原因 | 结果 | 必须保留的剧情功能 | 改编说明 |
|---|---|---|---|
| （待补） |  |  |  |

### 5.4 伏笔 / 回收 / 延迟兑现
| 伏笔 | 回收计划 | 状态 | 不可删除原因 |
|---|---|---|---|
| （待补） |  |  |  |

### 5.5 设定 / 战力 / 系统规则
- 规则：……
- 成长限制：……
- 战力一致性：……
- 不适用原因（如无）：……
"""

_LATE_IMPERIAL_CONTRACT_APPENDIX = _CONTRACT_MD_APPENDIX.replace(
    "## 5. 编剧理解合同（所有 register 必填）", "## 8. 编剧理解合同（所有 register 必填）"
).replace("### 5.", "### 8.")


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

_LATE_IMPERIAL_TEMPLATE = """# 源理解合同 — {title}

> register=**{register}**，profile=**late_imperial_vernacular**（明清章回体/近世白话）· 体检置信度 {confidence}。
> 这类源文本不是纯文言，也不能按普通现代白话直接拆集：正文常混合白话叙事、文言议论、诗词曲、
> 说书人套语、古代称谓与制度风俗。下游必须先从本合同取得**现代剧情理解**，再决定哪些古意保留为
> 台词/旁白/视觉锚，哪些仅作注释或压缩；不得逐句硬译，也不得把诗词、评话和正文机械等权成戏。
> 体检信号：{signals}

## 1. 全书与首批窗口的现代剧情理解
- 全书主线/人物关系/结局方向：……（待补）
- 首批制作覆盖范围：……（待补；写到回/章/段）
- 首批范围逐回释义：……（待补；每回写事件、动机、选择、后果、伏笔与状态变化）

## 2. 逐回释义索引（unit glosses）
| 源范围 | 现代剧情摘要 | 戏剧功能 | 关联 SRC trace_id |
|---|---|---|---|
| （待补） |  |  |  |

## 3. 古今词、称谓、制度与风俗对照
| 原词/称谓/制度 | 现代含义 | 屏幕处理（保留/白话化/视觉化/注释/省略） |
|---|---|---|
| （待补） |  |  |

## 4. 诗词曲、说书人评论与套语策略
- 诗词曲：……（待补；只保留承载人物、预示、反讽或节奏功能者，其余可压缩/视觉化）
- “话说/看官/有诗为证”等说书层：……（待补；定义旁白保留比例，避免全片评书腔）
- 文言议论/历史类比：……（待补；区分剧情因果与作者评论）

## 5. 台词语体目标
- 目标：……（待补；例如“现代可懂白话为骨，保留关键古称谓和少量章回韵味”）
- 禁止：逐字硬译、满篇仿古腔、现代网络梗破坏时代感、把人物称谓关系改错。

## 6. 历史语境与敏感内容改编策略
- 服制/空间/货币/身份秩序/礼俗：……（待补）
- 暴力、性、剥削、未成年人、污名化等内容：……（待补；保剧情因果，不露骨、不猎奇化，不删受害者处境）
- 发行分级与平台边界：……（待补；此处只定创作策略，正式发行仍走合规包）

## 7. 改编边界
- 必须保留：……
- 可现代化/压缩：……
- 禁止改动：……

---
确认后同步补全 `设定库/source_comprehension.json` 的 `understanding_contract`，尤其
`premodern_adapter`，并把 `status` 改为 `confirmed`。
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
    traits = detect_source_traits(text)
    traits["register_profile"] = cls.get("register_profile") or cls.get("lang_guess")
    inventory = extract_source_unit_inventory(text)
    traits["source_unit_count"] = len(inventory)
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
        if traits.get("register_profile") == "late_imperial_vernacular":
            tmpl = _LATE_IMPERIAL_TEMPLATE + _LATE_IMPERIAL_CONTRACT_APPENDIX
        elif register == "classical_zh":
            tmpl = _CLASSICAL_TEMPLATE + _CONTRACT_MD_APPENDIX
        elif register == "non_chinese":
            tmpl = _FOREIGN_TEMPLATE + _CONTRACT_MD_APPENDIX
        else:
            tmpl = _MODERN_TEMPLATE
        signals_line = "；".join(cls["signals"]) or "（无）"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(tmpl.format(title=title, register=register, lang_guess=cls["lang_guess"],
                                confidence=cls["confidence"], signals=signals_line))
        wrote_md = True

    status = (prev or {}).get("status") if prev and prev.get("register") == register else None
    contract = _merge_contract(
        _default_contract(register, traits),
        (prev or {}).get(CONTRACT_KEY) if prev and prev.get("register") == register else None,
    )
    record = {
        "kind": KIND, "version": 1, "register": register, "lang_guess": cls["lang_guess"],
        "register_profile": traits.get("register_profile"),
        "confidence": cls["confidence"], "signals": cls["signals"], "scores": cls["scores"],
        "source_traits": traits,
        "source": os.path.relpath(src, root),
        "source_unit_inventory": inventory,
        "status": status or "draft",
        "comprehension_doc": COMPREHENSION_MD_REL,
        CONTRACT_KEY: contract,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return {"ok": True, "register": register, "wrote_md": wrote_md,
            "md": COMPREHENSION_MD_REL, "json": COMPREHENSION_JSON_REL, "status": record["status"],
            "message": (f"源理解层脚手架已就绪（register={register}，status={record['status']}）。"
                        f"补全 {COMPREHENSION_MD_REL} 后把 status 置 confirmed 再拆集。")}


def main(argv=None):
    ap = argparse.ArgumentParser(description="n2d 源理解合同闸")
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
    print(f"{icon} 源理解合同：register={res.get('register')} · verdict={verdict}")
    for s in res.get("signals", []):
        print(f"   - {s}")
    if res.get("message"):
        print(res["message"])
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
