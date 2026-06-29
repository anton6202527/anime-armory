# -*- coding: utf-8 -*-
"""repetition.py — 跨章重复率/机械文风的确定性纯函数（novel 线单一真值源）。

novel-review/mechanical_check.py（作品质检·出 advisory findings）与 novel-score（评分·retention
维度先验）共用同一套检测，避免两处各抠各的算法漂移。纯标准库·纯函数·可测：
    cd skills/novel/_lib && python3 -m pytest test_repetition.py

依据：番茄/红果等平台对 AI 生成内容做「连续章节重复率 + 机械化文风」双重质检（红果曾下架高播放
量的 AI 短剧）。这里用字级 shingle Jaccard 近重复 + 跨章开篇/整句模板复用作**代理信号**，只给线索
供人判/作先验，绝不当硬闸（advisory·never 🔴）。阈值为内部经验值，非平台公开数字。
"""
import re

REP_SHINGLE_N = 12                   # 字级 shingle 窗口（近重复检测）
REP_ADJ_JACCARD_YELLOW = 0.18        # 相邻章 shingle Jaccard ≥ 此 → 🟡（疑似套模板/注水复述）
REP_ADJ_JACCARD_GREEN = 0.10         # ≥ 此 → 🟢 轻提示
REP_OPENER_PREFIX = 18               # 每章正文前 N 字做开篇指纹
REP_OPENER_MIN_CH = 3                # 同一开篇指纹在 ≥N 章复现 → 🟡 机械开篇
REP_SENTENCE_MIN_LEN = 12            # 参与跨章复用检测的最短句长（短句复现是正常的）
REP_SENTENCE_MIN_CH = 3              # 同一整句在 ≥N 章逐字复现 → 🟡 机械句复用
REP_SENTENCE_MAX_REPORT = 5          # 最多报告的复用句数（避免刷屏）

THRESHOLDS_PROVENANCE = "internal-heuristic（平台无公开硬数字；advisory·绝不 🔴）"


def normalize_for_rep(text):
    """去空白，得连续字流（shingle/句复用都在去空白后的文本上算）。"""
    return re.sub(r"\s+", "", text or "")


def char_shingles(text, n=REP_SHINGLE_N):
    """字级 n-gram shingle 集合（输入应已去空白）。纯函数。"""
    return {text[i:i + n] for i in range(0, max(0, len(text) - n + 1))}


def adjacent_chapter_jaccard(prev_body, next_body, n=REP_SHINGLE_N):
    """相邻两章字级 shingle 的 Jaccard 近重复率（0-1）。纯函数·可测。

    入参可为原始正文（内部去空白）。任一章短于窗口 → 0.0。"""
    a = char_shingles(normalize_for_rep(prev_body), n)
    b = char_shingles(normalize_for_rep(next_body), n)
    if not a or not b:
        return 0.0
    union = len(a | b)
    return (len(a & b) / union) if union else 0.0


def cross_chapter_repetition(chapters):
    """跨章重复率/机械文风机检（纯函数·advisory·绝不 🔴）。

    chapters: [(章号, 正文), ...]（顺序即检测顺序，建议按章号排序）。返回
    (findings, summary)。findings=[(chapter, severity, dim, msg, evidence)]，chapter=0 表示
    全局结论。检测三类：
      ① 相邻章 shingle Jaccard 近重复（套模板/注水复述·平台连续章节重复率高发）；
      ② 跨章机械开篇（同一开篇指纹在多章复现）；
      ③ 跨章整句逐字复用（AI 机械文风信号）。
    系统面板/签到类复现模板可能命中——advisory 故交人判，不阻断。"""
    out = []
    norm = [(ch, normalize_for_rep(body)) for ch, body in chapters]
    # ① 相邻章近重复
    adj_jaccards = []
    for (pch, pb), (nch, nb) in zip(norm, norm[1:]):
        if len(pb) < REP_SHINGLE_N or len(nb) < REP_SHINGLE_N:
            continue
        j = adjacent_chapter_jaccard(pb, nb)
        adj_jaccards.append((pch, nch, round(j, 4)))
        if j >= REP_ADJ_JACCARD_YELLOW:
            out.append((nch, "🟡", "跨章重复",
                        f"与第{pch}章内容近重复率偏高（shingle Jaccard={j:.0%}）；"
                        f"疑似套模板/注水复述，连续章节高重复是 AI检测高风险信号——拉开情节差异、删复述",
                        f"J={j:.0%}"))
        elif j >= REP_ADJ_JACCARD_GREEN:
            out.append((nch, "🟢", "跨章重复",
                        f"与第{pch}章近重复率略高（Jaccard={j:.0%}）；留意是否复述过多", f"J={j:.0%}"))
    # ② 机械开篇
    openers = {}
    for ch, b in norm:
        if len(b) >= REP_OPENER_PREFIX:
            openers.setdefault(b[:REP_OPENER_PREFIX], []).append(ch)
    mechanical_openers = 0
    for fp, chs in sorted(openers.items(), key=lambda kv: -len(kv[1])):
        if len(chs) >= REP_OPENER_MIN_CH:
            mechanical_openers += 1
            out.append((0, "🟡", "机械开篇",
                        f"{len(chs)} 章用几乎相同的开篇（前{REP_OPENER_PREFIX}字雷同）：第"
                        f"{'、'.join(map(str, chs[:8]))}章；换开篇方式破机械感", fp[:40]))
    # ③ 跨章整句逐字复用
    sent_chapters = {}
    for ch, body in chapters:
        seen = set()
        for s in re.split(r"[。！？!?…\n]+", normalize_for_rep(body)):
            s = s.strip()
            if len(s) >= REP_SENTENCE_MIN_LEN and s not in seen:
                seen.add(s)
                sent_chapters.setdefault(s, set()).add(ch)
    repeated = sorted(((s, chs) for s, chs in sent_chapters.items() if len(chs) >= REP_SENTENCE_MIN_CH),
                      key=lambda kv: (-len(kv[1]), -len(kv[0])))
    for s, chs in repeated[:REP_SENTENCE_MAX_REPORT]:
        out.append((0, "🟡", "机械句复用",
                    f"整句在 {len(chs)} 章逐字复现：「{s[:24]}…」（第{'、'.join(map(str, sorted(chs)[:8]))}章）；"
                    f"AI 机械文风/模板信号，改写或删除（系统面板等刻意模板可忽略）", s[:40]))
    summary = {
        "adjacent_max_jaccard": max((j for _, _, j in adj_jaccards), default=0.0),
        "adjacent_jaccards": adj_jaccards,
        "mechanical_opener_groups": mechanical_openers,
        "repeated_sentences": len(repeated),
        "thresholds": {
            "shingle_n": REP_SHINGLE_N,
            "adjacent_jaccard_yellow": REP_ADJ_JACCARD_YELLOW,
            "adjacent_jaccard_green": REP_ADJ_JACCARD_GREEN,
            "opener_prefix": REP_OPENER_PREFIX,
            "opener_min_chapters": REP_OPENER_MIN_CH,
            "sentence_min_chapters": REP_SENTENCE_MIN_CH,
        },
        "thresholds_provenance": THRESHOLDS_PROVENANCE,
    }
    return out, summary


def retention_prior(summary):
    """把 cross_chapter_repetition 的 summary 折成 retention 维度先验（advisory·纯函数）。

    返回 {level, points, reasons}：level ∈ none/mild/elevated/high；points 是**建议的** retention
    调分上限内提示（负向·0/-1/-2/-3），仅供 novel-score 作有上限的先验，绝不当硬闸。
    判据：相邻章近重复越界、机械开篇组、跨章整句复用——平台连续章节重复率/机械文风是弃读信号。"""
    if not summary:
        return {"level": "none", "points": 0, "reasons": []}
    reasons = []
    score = 0
    jmax = float(summary.get("adjacent_max_jaccard") or 0.0)
    if jmax >= REP_ADJ_JACCARD_YELLOW:
        score += 2
        reasons.append(f"相邻章最高近重复 {jmax:.0%}（≥{REP_ADJ_JACCARD_YELLOW:.0%}）：注水/套模板，弃读风险")
    elif jmax >= REP_ADJ_JACCARD_GREEN:
        score += 1
        reasons.append(f"相邻章近重复 {jmax:.0%} 略高：留意复述")
    openers = int(summary.get("mechanical_opener_groups") or 0)
    if openers:
        score += 1
        reasons.append(f"{openers} 组机械开篇：开篇雷同削弱追读")
    reps = int(summary.get("repeated_sentences") or 0)
    if reps >= 3:
        score += 1
        reasons.append(f"{reps} 句跨章逐字复用：机械文风信号")
    elif reps:
        reasons.append(f"{reps} 句跨章复用（轻）")
    level = "none" if score == 0 else ("mild" if score == 1 else ("elevated" if score == 2 else "high"))
    points = -min(3, score)
    return {"level": level, "points": points, "reasons": reasons}
