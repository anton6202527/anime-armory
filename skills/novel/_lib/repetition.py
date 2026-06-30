# -*- coding: utf-8 -*-
"""repetition.py — 跨章重复率/机械文风的确定性纯函数（novel 线单一真值源）。

novel-review/mechanical_check.py（作品质检·出 advisory findings）与 novel-score（评分·retention
维度先验）共用同一套检测，避免两处各抠各的算法漂移。纯标准库·纯函数·可测：
    cd skills/novel/_lib && python3 -m pytest test_repetition.py

依据：番茄/红果等平台对 AI 生成内容做「连续章节重复率 + 机械化文风」双重质检（红果曾下架高播放
量的 AI 短剧）。这里用字级 shingle Jaccard 近重复 + 跨章开篇/整句模板复用 + 句首词/短句式模板 + 全书/每章
压缩比（文本多样性代理）作**代理信号**，只给线索供人判/作先验，绝不当硬闸（advisory·never 🔴）。
阈值为内部经验值，非平台公开数字。

设计依据（2025-26 文本多样性/AI-slop 度量研究）：单本书几十~几百章用**精确** Jaccard 既便宜又比
MinHash 准（MinHash 是百万文档级近似，单本书是过度工程）；字级 N-gram 对中文绕开分词错误传播，是
被验证的偏好做法；压缩比(gzip)+句式模板计数是最便宜、覆盖面更广的机械文风/slop 代理（NAACL 2024
文本多样性共识 = 报多个低相关度量）。这些阈值是 project-tuned 启发式，**不**援引语料去重的 0.7-0.8。
"""
import re
import zlib

REP_SHINGLE_N = 12                   # 字级 shingle 窗口（近重复检测）
REP_ADJ_JACCARD_YELLOW = 0.18        # 相邻章 shingle Jaccard ≥ 此 → 🟡（疑似套模板/注水复述）
REP_ADJ_JACCARD_GREEN = 0.10         # ≥ 此 → 🟢 轻提示
REP_OPENER_PREFIX = 18               # 每章正文前 N 字做开篇指纹
REP_OPENER_MIN_CH = 3                # 同一开篇指纹在 ≥N 章复现 → 🟡 机械开篇
REP_SENTENCE_MIN_LEN = 12            # 参与跨章复用检测的最短句长（短句复现是正常的）
REP_SENTENCE_MIN_CH = 3              # 同一整句在 ≥N 章逐字复现 → 🟡 机械句复用
REP_SENTENCE_MAX_REPORT = 5          # 最多报告的复用句数（避免刷屏）
# 句首句式模板（机械句式·AI 文风信号；比逐字整句复用更宽，抓"千篇一律的起手式"）
REP_SENT_OPENER_N = 4                # 句首 n 字做句式指纹
REP_SENT_OPENER_MIN_SENT = 8         # 同一句首指纹复现 ≥N 句
REP_SENT_OPENER_MIN_CH = 3           # 且跨 ≥N 章 → 🟡 机械句式
REP_SENT_OPENER_MAX_REPORT = 5
# 更宽的句式机械信号：句首词频率 + 短句式模板。句首词只做 🟢，短句式模板才 🟡。
REP_SENT_START_N = 2
REP_SENT_START_MIN_SENT = 12
REP_SENT_START_MIN_CH = 3
REP_SENT_START_MAX_REPORT = 5
REP_SHORT_TEMPLATE_MIN_LEN = 6
REP_SHORT_TEMPLATE_MAX_LEN = 24
REP_SHORT_TEMPLATE_MIN_SENT = 6
REP_SHORT_TEMPLATE_MIN_CH = 3
REP_SHORT_TEMPLATE_MAX_REPORT = 5
REP_SHORT_TEMPLATE_ANCHORS = (
    "不是", "而是", "不由得", "忍不住", "下意识", "只觉得", "只见",
    "仿佛", "似乎", "微微", "缓缓", "轻轻", "淡淡", "忽然", "顿时",
    "终于", "已经", "仍然", "依旧", "就在", "这一刻", "那一刻",
    "空气", "时间", "命运", "眼神", "嘴角",
)
# 全书 zlib 压缩比（文本多样性代理；ratio 越低=越重复/套话/句式雷同=slop 信号·保守只 🟢）
REP_COMPRESS_MIN_CHARS = 800         # 低于此字数 gzip 头部开销失真，不算
REP_COMPRESS_LOW_GREEN = 0.36        # 全书压缩比 ≤ 此 → 🟢 文本多样性偏低（保守阈·internal-heuristic）
REP_CHAPTER_COMPRESS_LOW_GREEN = 0.36
REP_COMPRESS_MAX_REPORT = 5
REP_DISTINCT_MIN_NGRAMS = 80

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


def compression_ratio(text):
    """全书/整段 zlib 压缩比 = len(compressed)/len(utf8)，越低=越重复/套话=slop 代理。

    纯函数。文本去空白后算；短于 REP_COMPRESS_MIN_CHARS 字 → None（gzip 头部开销失真）。"""
    norm = normalize_for_rep(text)
    if len(norm) < REP_COMPRESS_MIN_CHARS:
        return None
    raw = norm.encode("utf-8")
    if not raw:
        return None
    return len(zlib.compress(raw, 9)) / len(raw)


def chapter_compression_ratios(chapters):
    """逐章 zlib 压缩比，返回 [(章号, ratio), ...]；短章跳过。"""
    ratios = []
    for ch, body in chapters:
        ratio = compression_ratio(body)
        if ratio is not None:
            ratios.append((ch, round(ratio, 4)))
    return ratios


def distinct_n_ratio(text, n):
    """字级 distinct-n = unique ngrams / total ngrams；短文本返回 None。"""
    norm = normalize_for_rep(text)
    total = len(norm) - n + 1
    if total < REP_DISTINCT_MIN_NGRAMS:
        return None
    grams = [norm[i:i + n] for i in range(total)]
    return len(set(grams)) / total


def _iter_sentences(text):
    for s in re.split(r"[。！？!?…\n]+", normalize_for_rep(text)):
        s = s.strip(" \t\r\n，,；;：:、。！？!?…“”\"'「」『』（）()《》<>—-")
        if s:
            yield s


def sentence_start_token(sentence, n=REP_SENT_START_N):
    """句首词代理：英文/数字按连续 token，中文按前 n 字。"""
    s = (sentence or "").strip(" \t\r\n，,；;：:、。！？!?…“”\"'「」『』（）()《》<>—-")
    if not s:
        return ""
    m = re.match(r"[A-Za-z0-9_]+", s)
    if m:
        return m.group(0).lower()[:12]
    return s[:n]


def sentence_opener_templates(chapters, n=REP_SENT_OPENER_N):
    """句首句式模板复现：同一句首 n 字在多句、多章复现 → 机械句式（AI 文风信号）。纯函数。

    比"跨章整句逐字复用"更宽：抓"千篇一律的起手式"（如每每『他不由得…』『只见那…』）。返回
    [(句首指纹, 复现句数, [章号...]), ...]，按复现句数降序，仅含越双阈（句数+章数）者。"""
    tmpl_ch = {}
    tmpl_count = {}
    for ch, body in chapters:
        for s in _iter_sentences(body):
            if len(s) >= n:
                key = s[:n]
                tmpl_ch.setdefault(key, set()).add(ch)
                tmpl_count[key] = tmpl_count.get(key, 0) + 1
    hits = []
    for key, cnt in sorted(tmpl_count.items(), key=lambda kv: -kv[1]):
        chs = tmpl_ch[key]
        if cnt >= REP_SENT_OPENER_MIN_SENT and len(chs) >= REP_SENT_OPENER_MIN_CH:
            hits.append((key, cnt, sorted(chs)))
    return hits


def sentence_start_tokens(chapters, n=REP_SENT_START_N):
    """高频句首词：同一首词在多句、多章复现。只做轻提示，避免误伤正常叙事视角。"""
    token_ch = {}
    token_count = {}
    for ch, body in chapters:
        for s in _iter_sentences(body):
            key = sentence_start_token(s, n)
            if len(key) >= n:
                token_ch.setdefault(key, set()).add(ch)
                token_count[key] = token_count.get(key, 0) + 1
    hits = []
    for key, cnt in sorted(token_count.items(), key=lambda kv: -kv[1]):
        chs = token_ch[key]
        if cnt >= REP_SENT_START_MIN_SENT and len(chs) >= REP_SENT_START_MIN_CH:
            hits.append((key, cnt, sorted(chs)))
    return hits


def short_sentence_template(sentence):
    """短句式模板代理：保留高机械感结构锚，抹去主语/内容槽。

    不是分词器，也不试图理解语义；只抓重复出现的短句结构，如「<S>不由得<R>」、
    「<S>不是<R>而是<R>」。无锚点的普通短句不返回模板，避免把正常叙事误报成模板。
    """
    s = (sentence or "").strip(" \t\r\n，,；;：:、。！？!?…“”\"'「」『』（）()《》<>—-")
    s = re.sub(r"\d+", "#", s)
    s = re.sub(r"[A-Za-z_]+", "A", s)
    if not (REP_SHORT_TEMPLATE_MIN_LEN <= len(s) <= REP_SHORT_TEMPLATE_MAX_LEN):
        return ""
    not_pos = s.find("不是")
    but_pos = s.find("而是")
    if 0 <= not_pos <= 6 and but_pos > not_pos:
        return "<S>不是<R>而是<R>"
    for anchor in sorted(REP_SHORT_TEMPLATE_ANCHORS, key=len, reverse=True):
        pos = s.find(anchor)
        if 0 <= pos <= 6:
            prefix = "<S>" if pos else ""
            return f"{prefix}{anchor}<R>"
    return ""


def short_sentence_templates(chapters):
    """短句式模板复现，返回 [(template, count, [章号...]), ...]。"""
    tmpl_ch = {}
    tmpl_count = {}
    for ch, body in chapters:
        for s in _iter_sentences(body):
            key = short_sentence_template(s)
            if key:
                tmpl_ch.setdefault(key, set()).add(ch)
                tmpl_count[key] = tmpl_count.get(key, 0) + 1
    hits = []
    for key, cnt in sorted(tmpl_count.items(), key=lambda kv: -kv[1]):
        chs = tmpl_ch[key]
        if cnt >= REP_SHORT_TEMPLATE_MIN_SENT and len(chs) >= REP_SHORT_TEMPLATE_MIN_CH:
            hits.append((key, cnt, sorted(chs)))
    return hits


def cross_chapter_repetition(chapters):
    """跨章重复率/机械文风机检（纯函数·advisory·绝不 🔴）。

    chapters: [(章号, 正文), ...]（顺序即检测顺序，建议按章号排序）。返回
    (findings, summary)。findings=[(chapter, severity, dim, msg, evidence)]，chapter=0 表示
    全局结论。检测五类：
      ① 相邻章 shingle Jaccard 近重复（套模板/注水复述·平台连续章节重复率高发）；
      ② 跨章机械开篇（同一开篇指纹在多章复现）；
      ③ 跨章整句逐字复用（AI 机械文风信号）；
      ④ 句首句式模板复现（千篇一律的起手式·AI 文风信号·比③宽）；
      ⑤ 句首词频率 + 短句式模板（更宽的机械文风代理）；
      ⑥ 全书/每章 zlib 压缩比偏低（文本多样性不足的 slop 代理·保守只 🟢）。
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
    # ④ 句首句式模板（机械句式·AI 文风信号）
    templates = sentence_opener_templates(chapters)
    for key, cnt, chs in templates[:REP_SENT_OPENER_MAX_REPORT]:
        out.append((0, "🟡", "机械句式",
                    f"句首「{key}…」在 {cnt} 句复现（跨 {len(chs)} 章：第{'、'.join(map(str, chs[:8]))}章）；"
                    f"疑似句式模板化的 AI 文风信号，换起手句式（对话/刻意排比可忽略）", key))
    # ⑤ 句首词频率 + 短句式模板（更宽的机械文风代理）
    start_tokens = sentence_start_tokens(chapters)
    for key, cnt, chs in start_tokens[:REP_SENT_START_MAX_REPORT]:
        out.append((0, "🟢", "句首词频率",
                    f"句首词「{key}…」在 {cnt} 句复现（跨 {len(chs)} 章：第{'、'.join(map(str, chs[:8]))}章）；"
                    f"可能是机械起手词高频，建议抽查是否缺少句式变化", key))
    short_templates = short_sentence_templates(chapters)
    for key, cnt, chs in short_templates[:REP_SHORT_TEMPLATE_MAX_REPORT]:
        out.append((0, "🟡", "短句式模板",
                    f"短句式模板「{key}」在 {cnt} 句复现（跨 {len(chs)} 章：第{'、'.join(map(str, chs[:8]))}章）；"
                    f"疑似模板化机械文风，替换为动作/对话/感官差异化句式", key))
    # ⑥ 全书/每章压缩比（文本多样性代理·保守只 🟢）
    book_text = "".join(b for _, b in chapters)
    cratio = compression_ratio(book_text)
    if cratio is not None and cratio <= REP_COMPRESS_LOW_GREEN:
        out.append((0, "🟢", "文本多样性",
                    f"全书 zlib 压缩比偏低（多样性不足的 slop 代理·internal-heuristic）：压缩比 "
                    f"{cratio:.0%} ≤ 阈 {REP_COMPRESS_LOW_GREEN:.0%}；查是否重复/套话/句式雷同", f"{cratio:.0%}"))
    ch_cratios = chapter_compression_ratios(chapters)
    low_ch_cratios = [(ch, ratio) for ch, ratio in ch_cratios if ratio <= REP_CHAPTER_COMPRESS_LOW_GREEN]
    for ch, ratio in low_ch_cratios[:REP_COMPRESS_MAX_REPORT]:
        out.append((ch, "🟢", "文本多样性",
                    f"本章 zlib 压缩比偏低（多样性不足的 slop 代理·internal-heuristic）：压缩比 "
                    f"{ratio:.0%} ≤ 阈 {REP_CHAPTER_COMPRESS_LOW_GREEN:.0%}；抽查是否重复/套话/句式雷同",
                    f"{ratio:.0%}"))
    if len(low_ch_cratios) > REP_COMPRESS_MAX_REPORT:
        out.append((0, "🟢", "文本多样性",
                    f"另有 {len(low_ch_cratios) - REP_COMPRESS_MAX_REPORT} 章压缩比偏低；详见 summary.chapter_compression_ratios",
                    "chapter_compression_ratios"))
    d2 = distinct_n_ratio(book_text, 2)
    d4 = distinct_n_ratio(book_text, 4)
    summary = {
        "adjacent_max_jaccard": max((j for _, _, j in adj_jaccards), default=0.0),
        "adjacent_jaccards": adj_jaccards,
        "mechanical_opener_groups": mechanical_openers,
        "repeated_sentences": len(repeated),
        "sentence_opener_templates": len(templates),
        "sentence_start_token_groups": len(start_tokens),
        "short_sentence_templates": len(short_templates),
        "compression_ratio": cratio,
        "chapter_compression_ratios": ch_cratios,
        "low_chapter_compression_count": len(low_ch_cratios),
        "min_chapter_compression_ratio": min((r for _, r in ch_cratios), default=None),
        "distinct_2": d2,
        "distinct_4": d4,
        "thresholds": {
            "shingle_n": REP_SHINGLE_N,
            "adjacent_jaccard_yellow": REP_ADJ_JACCARD_YELLOW,
            "adjacent_jaccard_green": REP_ADJ_JACCARD_GREEN,
            "opener_prefix": REP_OPENER_PREFIX,
            "opener_min_chapters": REP_OPENER_MIN_CH,
            "sentence_min_chapters": REP_SENTENCE_MIN_CH,
            "sentence_opener_n": REP_SENT_OPENER_N,
            "sentence_opener_min_sentences": REP_SENT_OPENER_MIN_SENT,
            "sentence_opener_min_chapters": REP_SENT_OPENER_MIN_CH,
            "sentence_start_n": REP_SENT_START_N,
            "sentence_start_min_sentences": REP_SENT_START_MIN_SENT,
            "sentence_start_min_chapters": REP_SENT_START_MIN_CH,
            "short_template_min_sentences": REP_SHORT_TEMPLATE_MIN_SENT,
            "short_template_min_chapters": REP_SHORT_TEMPLATE_MIN_CH,
            "compression_low_green": REP_COMPRESS_LOW_GREEN,
            "chapter_compression_low_green": REP_CHAPTER_COMPRESS_LOW_GREEN,
        },
        "thresholds_provenance": THRESHOLDS_PROVENANCE,
    }
    return out, summary


def retention_prior(summary):
    """把 cross_chapter_repetition 的 summary 折成 retention 维度先验（advisory·纯函数）。

    返回 {level, points, reasons}：level ∈ none/mild/elevated/high；points 是**建议的** retention
    调分上限内提示（负向·0/-1/-2/-3），仅供 novel-score 作有上限的先验，绝不当硬闸。
    判据：只让 🟡 级信号进入负向调分；🟢 级信号只进 reasons，避免把正常叙事口吻/轻微重复误扣分。"""
    if not summary:
        return {"level": "none", "points": 0, "reasons": []}
    reasons = []
    score = 0
    jmax = float(summary.get("adjacent_max_jaccard") or 0.0)
    if jmax >= REP_ADJ_JACCARD_YELLOW:
        score += 2
        reasons.append(f"相邻章最高近重复 {jmax:.0%}（≥{REP_ADJ_JACCARD_YELLOW:.0%}）：注水/套模板，弃读风险")
    elif jmax >= REP_ADJ_JACCARD_GREEN:
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
    templates = int(summary.get("sentence_opener_templates") or 0)
    if templates:
        score += 1
        reasons.append(f"{templates} 组机械句式模板：起手句式雷同，阅读疲劳")
    starts = int(summary.get("sentence_start_token_groups") or 0)
    if starts >= 2:
        reasons.append(f"{starts} 组高频句首词（🟢线索）：起手词过度集中，抽查即可")
    elif starts:
        reasons.append(f"{starts} 组高频句首词（🟢轻线索）")
    shorts = int(summary.get("short_sentence_templates") or 0)
    if shorts:
        score += 1
        reasons.append(f"{shorts} 组短句式模板：机械短句复现")
    cratio = summary.get("compression_ratio")
    if cratio is not None and float(cratio) <= REP_COMPRESS_LOW_GREEN:
        reasons.append(f"全书压缩比偏低（🟢多样性线索）：{float(cratio):.0%} ≤ {REP_COMPRESS_LOW_GREEN:.0%}")
    low_ch = int(summary.get("low_chapter_compression_count") or 0)
    if low_ch >= 2:
        reasons.append(f"{low_ch} 章压缩比偏低（🟢多样性线索）：局部文本多样性不足")
    elif low_ch:
        reasons.append(f"{low_ch} 章压缩比偏低（轻）")
    level = "none" if score == 0 else ("mild" if score == 1 else ("elevated" if score == 2 else "high"))
    points = -min(3, score)  # 负向先验硬封顶 -3：新增信号只增检出口径，不抬调分上限
    return {"level": level, "points": points, "reasons": reasons}
