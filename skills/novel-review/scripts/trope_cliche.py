#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trope_cliche.py — 套路/前提级陈词滥调探测器（确定性高精度骨架 + 人判差异化）

补 imagination 侧长期只有**行文级** AI 腔（mechanical_check 的 ai_tell_scan）、没有**情节/前提级**
套路探测的洞：novel-score 的 novelty 维度是事后 LLM 打分，`平台雷点.md` 是人判清单，都不在**开写前**
按结构化信号提示「你这个开局是高频烂大街套路」。本脚本扫**创作蓝图/前提/首章开局**里的高频网文套路开局，
命中即出**建议级**候选（绝不阻断——网文里套路本就是类型语言，问题不在用套路而在**没差异化/没颠覆**）。

诚实边界（对标 logic_sentry「只报硬候选」）：
  - **确定性（脚本算）**：多词 AND 命中高精度套路模式、是否已在「差异化决策/forbidden_tropes」里被点名。
  - **人判/LLM（脚本不臆测）**：这个套路到底有没有被巧妙颠覆、差异化够不够——只提示，不替人下结论。

设计要点：
  - 只收**多词 AND** 的高辨识度开局（单个「系统」「重生」不报，避免噪声）。
  - 若蓝图的「差异化决策」段或 author_intent 的 forbidden_tropes 已点名该套路 → 视为作者已自觉，降一档/抑制。
  - analyze(project) → {ran, alerts,...}，接 consistency_audit 统一 subrunner。

测试：cd skills/novel-review/scripts && python3 -m pytest test_trope_cliche.py
"""
import os
import re
import json
import argparse

# 每条套路 = (套路名, (必现关键词组…), 差异化提示)。多词 AND 命中才算——高辨识度、低误报。
TROPE_BANK = [
    ("系统绑定开局", ("系统", "绑定"),
     "‘叮，系统绑定宿主’式开局极度饱和；若用，务必给系统一个反常规代价/限制或叙事功能，别只当金手指自动贩卖机"),
    # 退婚流不做单关键词条目（"退婚"单命中噪声大），交给下方 _COMBO 的多轴 AND 精判。
    ("赘婿逆袭流", ("赘婿", "岳父"),
     "赘婿被羞辱→扮猪吃虎已成模板；差异化点在于‘为何非入赘不可’的真实处境与代价，而非又一次打脸宴"),
    ("战神/兵王归来", ("兵王", "归来"),
     "‘最强兵王回归都市’高度同质；若用，把‘归来’的心理创伤/身份撕裂写实，别只堆装逼打脸"),
    ("重生复仇流", ("重生", "前世"),
     "‘重活一世手刃仇人’套路化；差异化在于重生者的认知优势如何**反噬**自己，而非全程先知碾压"),
    ("废物觉醒天才", ("废物", "觉醒"),
     "‘废柴一朝觉醒天下第一’是最饱和逆袭壳；把‘废’写成真实的结构性困境、觉醒有代价，才不悬浮"),
    ("神豪/花钱系统", ("神豪", "系统"),
     "‘花钱就变强/花钱返现’神豪系统同质严重；至少让消费与人物欲望/伦理产生张力"),
    ("霸总闪婚/契约", ("霸道总裁", "契约"),
     "‘契约闪婚霸总’是女频最饱和壳之一；差异化靠双方各自的真实动机与权力不对等的代价，而非误会拉扯流水线"),
    ("全家团宠/火葬场", ("团宠", "火葬场"),
     "‘团宠+全员追妻火葬场’情绪配方化；若用，给‘团宠’一个会被打破的裂缝，别一路无脑宠到尾"),
    ("扮猪吃虎打脸宴", ("扮猪吃虎", "打脸"),
     "‘藏拙→宴会打脸’桥段密度过高；把‘藏’的必要性与暴露的风险写足，别为打脸而打脸"),
]

# 组合体：两个关键词各来自不同轴才算命中（比单 bank 条目更精准）。
_COMBO = [
    ("穿越/重生+退婚流", ("穿越", "重生"), ("退婚",),
     "‘穿越/重生即遭退婚→打脸前未婚夫家’是最饱和开局之一；差异化靠退婚背后的真实社会逻辑与主角的非套路反应"),
    ("废物+退婚双废壳", ("废物", "废柴"), ("退婚",),
     "‘废物遭退婚’叠两层最饱和壳；至少颠覆其一（如主角真心想退、或‘废’是伪装）"),
]

DIFF_SECTION_HINTS = ("差异化决策", "差异化", "套路自查", "反套路", "颠覆", "subvert")


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def gather_premise_text(project):
    """收集‘前提层’文本：创作蓝图 + _meta.premise + 首章开局（前 1200 字）。只读，不改。"""
    parts = []
    for rel in ("设定/创作蓝图.md", "设定/蓝图.md"):
        p = os.path.join(project, rel)
        if os.path.exists(p):
            parts.append(_read(p))
    meta = _load_json(os.path.join(project, "_meta.json"))
    for k in ("premise", "logline", "genre"):
        v = meta.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    cdir = os.path.join(project, "章节")
    if os.path.isdir(cdir):
        firsts = sorted(n for n in os.listdir(cdir) if re.search(r"第0*1章", n))
        if firsts:
            parts.append(_read(os.path.join(cdir, firsts[0]))[:1200])
    return "\n".join(parts)


def _differentiation_text(project):
    """作者已自觉点名的套路来源：蓝图差异化段 + author_intent.forbidden_tropes。命中即视为已自觉。"""
    txt = []
    bp = _read(os.path.join(project, "设定", "创作蓝图.md"))
    if any(h in bp for h in DIFF_SECTION_HINTS):
        txt.append(bp)
    ai = _load_json(os.path.join(project, "设定", "author_intent.json"))
    ft = ai.get("forbidden_tropes") if isinstance(ai, dict) else None
    if isinstance(ft, list):
        txt.extend(str(x) for x in ft)
    return "\n".join(txt)


def detect(premise_text, differentiation_text=""):
    """纯函数：命中的套路列表。已被差异化段/forbidden_tropes 点名的套路降为‘已自觉’（severity 更低）。"""
    hits = []
    seen = set()

    def _ack(name, keys):
        # 作者是否已点名这个套路（套路名或其关键词出现在差异化文本里）
        if name in differentiation_text:
            return True
        return any(k in differentiation_text for k in keys)

    for name, keys, hint in TROPE_BANK:
        if not keys or name in seen:
            continue
        if all(k in premise_text for k in keys):
            seen.add(name)
            hits.append((name, keys, hint))
    for name, axis_a, axis_b, hint in _COMBO:
        if name in seen:
            continue
        if any(a in premise_text for a in axis_a) and any(b in premise_text for b in axis_b):
            seen.add(name)
            hits.append((name, tuple(axis_a) + tuple(axis_b), hint))

    out = []
    for name, keys, hint in hits:
        acknowledged = _ack(name, keys)
        out.append({
            "type": "trope_cliche_candidate",
            "trope": name,
            "severity": "建议级",
            "acknowledged": acknowledged,
            "note": (f"命中高频套路「{name}」。" + (hint or "")) +
                    ("　（差异化决策/forbidden_tropes 已点名此套路，视为已自觉——确认颠覆已落到章纲）"
                     if acknowledged else
                     "　未在‘差异化决策/forbidden_tropes’里点名 → 同质化预警：要么写明如何差异化/颠覆，要么换开局"),
            "auto": True,
        })
    return out


def analyze(project):
    """consistency_audit 子检测器契约：analyze(project) → {ran, alerts,...}。全建议级，绝不阻断。"""
    premise = gather_premise_text(project)
    if not premise.strip():
        return {"ran": False, "skipped": "无蓝图/前提/首章文本可扫（先建 设定/创作蓝图.md）"}
    diff = _differentiation_text(project)
    alerts = detect(premise, diff)
    return {
        "kind": "trope_cliche_report",
        "ran": True,
        "premise_chars": len(premise),
        "alert_count": len(alerts),
        "unacknowledged": sum(1 for a in alerts if not a["acknowledged"]),
        "alerts": alerts,
    }


def main():
    ap = argparse.ArgumentParser(description="套路/前提级陈词滥调探测器（建议级）")
    ap.add_argument("project_path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = analyze(args.project_path)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if not res.get("ran"):
        print(f"[skip] {res.get('skipped')}")
        return
    print(f"套路探测：命中 {res['alert_count']} 条（未自觉 {res['unacknowledged']} 条）")
    for a in res["alerts"]:
        mark = "✓已自觉" if a["acknowledged"] else "⚠未点名"
        print(f"  [{mark}] {a['trope']}：{a['note']}")


if __name__ == "__main__":
    main()
