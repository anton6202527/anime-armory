# -*- coding: utf-8 -*-
"""narrative_risk_weight.py — ConStory 实证驱动的 advisory 优先级加权（**只排序·绝不升阻断**）。

依据 arXiv 2603.05890《Lost in Stories: Consistency Bugs in Long Story Generation》(ConStory-Bench)
的实证结论：长文一致性错误并非均匀分布，而是集中在——
  (a) 叙事**中段 ~40–60%**（开头设定清晰、结尾收束，中段最易自相矛盾）；
  (b) **高 token 熵段落**（信息密度/不确定性高处）；
  (c) 错误类型**成簇共现**（高 churn 章一处崩、附近更可能再崩）。

本模块把"错误更可能藏在哪"翻译成**确定性 advisory 优先级**：给每条 finding 算 priority、
并产出"审查重点章"热点表，让人/LLM 把有限的**语义复审火力**先投到最可能藏 bug 的章节。
token 熵拿不到（那是模型侧量），用两个**确定性代理**：
  - churn = 该章在作者台账里的结构化状态改动数（character_changes + 世界事实），强=情节复杂；
  - 字符级 Shannon 熵（正文 type/entropy 代理），强=信息密度高。

**铁律（B10）**：本模块**只给 priority/factors 并排序，从不碰 severity / blocking**——
定位信号是脆弱启发式，不得升阻断；它只决定"先看哪一章"，不决定"挡不挡发布"。

纯标准库·纯函数·可测：cd skills/novel/_lib && python3 -m pytest test_narrative_risk_weight.py
"""
import math
import re

# 中段窗口与各代理的加权（单一真值，调参集中此处）。base=1.0，命中各代理叠加：
MIDSPAN_LO = 0.40
MIDSPAN_HI = 0.60
MIDSPAN_BONUS = 0.6      # 命中 40–60% 中段
CHURN_BONUS = 0.5       # churn ≥ 高分位
ENTROPY_BONUS = 0.3     # 字符熵 ≥ 高分位
HOTSPOT_PERCENTILE = 0.75  # "高"的判定分位


def _chapter_no(key):
    m = re.search(r"(\d+)", str(key))
    return int(m.group(1)) if m else 0


def chapter_position(chapter, total_chapters):
    """1-based 章号 → 归一化叙事位置 [0,1]（章中点）。total<=0 时返回 0.0。"""
    ch = _chapter_no(chapter)
    if total_chapters and total_chapters > 0 and ch >= 1:
        return min(1.0, max(0.0, (ch - 0.5) / float(total_chapters)))
    return 0.0


def is_midspan(position, lo=MIDSPAN_LO, hi=MIDSPAN_HI):
    """归一化位置是否落在中段窗口（含端点）。"""
    return lo <= position <= hi


def lexical_entropy(text):
    """正文字符级归一化 Shannon 熵 ∈ [0,1]（token 熵的确定性代理·纯函数）。

    去空白后按字符频次算 H，再除以 log2(字符种类) 归一化，使不同长度章可比。
    空/单字符 → 0.0。这是"信息密度"代理，不是语言学严谨度量，够用于排序即可。"""
    chars = [c for c in str(text or "") if not c.isspace()]
    if len(chars) < 2:
        return 0.0
    freq = {}
    for c in chars:
        freq[c] = freq.get(c, 0) + 1
    n = len(chars)
    h = -sum((cnt / n) * math.log2(cnt / n) for cnt in freq.values())
    distinct = len(freq)
    if distinct < 2:
        return 0.0
    return min(1.0, h / math.log2(distinct))


def build_churn_map(state_ledger, world_ledger=None):
    """{章号 -> 结构化状态改动数}。读作者 curated 台账（不扫正文）：

    state_ledger.chapter_deltas[*].character_changes 逐章计数 + 可选 world_ledger.major_changes
    按 established_at/chapter 归入对应章。缺台账 → 空 map（消费端退化为只用中段+熵）。纯函数。"""
    churn = {}
    sl = state_ledger if isinstance(state_ledger, dict) else {}
    deltas = sl.get("chapter_deltas")
    items = []
    if isinstance(deltas, dict):
        items = list(deltas.items())
    elif isinstance(deltas, list):
        items = [((d.get("chapter") or d.get("chapter_key") or i), d) for i, d in enumerate(deltas)]
    for key, delta in items:
        # 与 graph_sentry 同：合并后 chapter_deltas[key] 是 {merged_at, summary:<delta>, verification} 包裹，
        # 裸读 character_changes 会恒 0 → churn 永远为空、热点权重静默退化。解包 summary 兜底。
        if isinstance(delta, dict) and isinstance(delta.get("summary"), dict):
            delta = delta["summary"]
        ch = _chapter_no(key) or (_chapter_no(delta.get("chapter")) if isinstance(delta, dict) else 0)
        if not ch:
            continue
        cc = (delta.get("character_changes") or []) if isinstance(delta, dict) else []
        churn[ch] = churn.get(ch, 0) + (len(cc) if isinstance(cc, list) else 0)
    wl = world_ledger if isinstance(world_ledger, dict) else {}
    for entry in wl.get("major_changes", []) if isinstance(wl, dict) else []:
        if not isinstance(entry, dict):
            continue
        ch = _chapter_no(entry.get("established_at", entry.get("chapter")))
        if ch:
            churn[ch] = churn.get(ch, 0) + 1
    return churn


def _percentile_threshold(values, q=HOTSPOT_PERCENTILE):
    """第 q 分位阈值（≥ 它即"高"）。空/全相等 → 返回比最大值大的哨兵(无章达标)。纯函数。"""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return float("inf")
    if vals[0] == vals[-1]:
        return float("inf")  # 全相等：不挑出"异常高"的章，避免把均匀churn全标热点
    idx = min(len(vals) - 1, int(math.ceil(q * len(vals)) - 1))
    return vals[max(0, idx)]


def chapter_factors(chapter, total_chapters, churn_map=None, entropy_map=None,
                    churn_threshold=None, entropy_threshold=None):
    """单章命中的风险代理列表（'midspan'/'high_churn'/'high_entropy'）+ 该章 priority 权重。

    返回 (weight, factors)。weight = 1.0 + 各命中代理 bonus。纯函数·确定性。"""
    ch = _chapter_no(chapter)
    factors = []
    weight = 1.0
    if is_midspan(chapter_position(ch, total_chapters)):
        factors.append("midspan")
        weight += MIDSPAN_BONUS
    if churn_map and churn_threshold is not None and churn_threshold != float("inf"):
        if churn_map.get(ch, 0) >= churn_threshold:
            factors.append("high_churn")
            weight += CHURN_BONUS
    if entropy_map and entropy_threshold is not None and entropy_threshold != float("inf"):
        if entropy_map.get(ch, 0.0) >= entropy_threshold:
            factors.append("high_entropy")
            weight += ENTROPY_BONUS
    return weight, factors


def prioritize_alerts(alerts, total_chapters, churn_map=None, entropy_map=None):
    """就地给每条 finding 标 priority(float)+priority_factors(list)，并按 priority 降序稳定排序。

    **不碰 severity / blocking**。同 priority 时阻断级优先（保证硬伤永远排在 advisory 前）。
    返回排序后的 alerts（同对象·便于链式）。纯函数（除就地写字段）。"""
    churn_thr = _percentile_threshold((churn_map or {}).values())
    ent_thr = _percentile_threshold((entropy_map or {}).values())
    for a in alerts:
        if not isinstance(a, dict):
            continue
        w, factors = chapter_factors(a.get("chapter"), total_chapters, churn_map, entropy_map,
                                     churn_thr, ent_thr)
        a["priority"] = round(w, 3)
        a["priority_factors"] = factors

    def _key(a):
        if not isinstance(a, dict):
            return (0, 0.0)
        sev_rank = 1 if a.get("severity") == "阻断级" else 0
        return (sev_rank, a.get("priority", 1.0))

    return sorted([a for a in alerts if isinstance(a, dict)], key=_key, reverse=True)


def risk_hotspots(total_chapters, churn_map=None, entropy_map=None, top_k=None):
    """"审查重点章"热点表：按风险代理给所有章打分，挑出命中≥1代理的章（priority>1.0），降序。

    供报告写 review_focus_chapters，引导人/LLM 把语义复审火力先投到这些章。纯函数。"""
    if not total_chapters or total_chapters <= 0:
        return []
    churn_thr = _percentile_threshold((churn_map or {}).values())
    ent_thr = _percentile_threshold((entropy_map or {}).values())
    rows = []
    for ch in range(1, int(total_chapters) + 1):
        w, factors = chapter_factors(ch, total_chapters, churn_map, entropy_map, churn_thr, ent_thr)
        if factors:
            rows.append({"chapter": ch, "priority": round(w, 3), "factors": factors,
                         "churn": (churn_map or {}).get(ch, 0)})
    rows.sort(key=lambda r: (r["priority"], r["churn"], -r["chapter"]), reverse=True)
    return rows[:top_k] if top_k else rows
