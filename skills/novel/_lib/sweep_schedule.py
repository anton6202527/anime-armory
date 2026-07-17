# -*- coding: utf-8 -*-
"""sweep_schedule.py — 小批回扫 due 点的单一真值源（含中段防守加密）。

此前 draft_packets.batch_review_window 与 flow.batch_review_window 各自用
`chapter % interval` 平铺回扫点。长篇一致性实证（Lost in Stories, arXiv 2603.05890）
显示 **40%-60% 进度带是矛盾高发区**（实体追踪/时间线在中段最易漂移），平铺间隔
恰好在最需要防守的位置密度不变。本模块把 due 点计算收口成单一实现：

- 基础 due：chapter 是 interval 的整数倍（原行为不变）。
- 项目尾 due：chapter == target_chapters（收尾必扫，原行为不变）。
- **中段防守 due**：chapter 落在 [40%, 60%]·target 的进度带内时，
  额外按半间隔（max(1, interval//2)）加密——interval=5 时中段每 2-3 章扫一次。
- 回扫窗口 = (上一个 due 点 + 1, 当前 due 点)：无缝覆盖、无重叠，
  中段加密不会在带边界留未扫缺口。

target_chapters 未知（0）或 < 10 章时不启用中段防守，行为与原平铺完全一致。
纯标准库·纯函数·可测：cd skills/novel/_lib && python3 -m pytest test_sweep_schedule.py
"""

MIDSTORY_BAND = (0.40, 0.60)
MIDSTORY_MIN_TARGET = 10  # 短篇不启用中段防守
HOTSPOT_TOP_K = 5         # 数据自适应 due：最多取几个 churn/熵热点章


def half_interval(interval):
    return max(1, int(interval) // 2)


def in_midstory_band(chapter, target):
    """chapter 是否落在 40%-60% 进度带（矛盾高发区）。target 未知/短篇 → False。"""
    target = int(target or 0)
    if target < MIDSTORY_MIN_TARGET:
        return False
    lo = int(target * MIDSTORY_BAND[0])
    hi = int(target * MIDSTORY_BAND[1])
    return lo <= int(chapter) <= hi


def is_due(chapter, interval, target=0, hotspots=None):
    """本章写后是否触发一次小批回扫。

    hotspots（可选）：churn/熵风险热点章集合（project_hotspots 产出）——数据自适应 due：
    固定 40-60% 带是实证先验，热点表是**本书实际**的状态改动/熵分布；两者互补，
    热点章写后立即回扫而不是等平铺间隔。不传 = 原静态行为，完全向后兼容。"""
    chapter, interval, target = int(chapter), int(interval), int(target or 0)
    if interval <= 0 or chapter <= 0:
        return False
    if chapter % interval == 0:
        return True
    if target and chapter == target:
        return True
    if in_midstory_band(chapter, target) and chapter % half_interval(interval) == 0:
        return True
    if hotspots and chapter in hotspots:
        return True
    return False


def window_for(chapter, interval, target=0, hotspots=None):
    """due 章的回扫窗口 (start, end)：start = 上一 due 点 + 1，保证无缝覆盖。"""
    prev = 0
    for c in range(int(chapter) - 1, 0, -1):
        if is_due(c, interval, target, hotspots):
            prev = c
            break
    return prev + 1, int(chapter)


def next_due_after(chapter, interval, target=0, hotspots=None):
    """下一个 due 点章号；interval<=0 返回 None。"""
    chapter, interval, target = int(chapter), int(interval), int(target or 0)
    if interval <= 0:
        return None
    limit = max(target, chapter + interval)
    for c in range(chapter + 1, limit + 1):
        if is_due(c, interval, target, hotspots):
            return c
    return None


def project_hotspots(root, target=0, top_k=HOTSPOT_TOP_K):
    """读 审稿/state_ledger.json → churn 热点章集合（is_due 的 hotspots 输入·IO 便捷层）。

    只取 factors 含 high_churn/high_entropy 的章——midspan 已由静态带负责，重复计入
    会让整个中段全变 due 点。缺账本/依赖/解析失败 → 空集合（退化为静态调度，绝不阻断）。"""
    try:
        import json
        import os
        from narrative_risk_weight import build_churn_map, risk_hotspots
        path = os.path.join(str(root), "审稿", "state_ledger.json")
        with open(path, encoding="utf-8") as f:
            ledger = json.load(f)
        churn = build_churn_map(ledger)
        total = int(target or 0) or (max(churn) if churn else 0)
        rows = risk_hotspots(total, churn_map=churn)
        picked = [r["chapter"] for r in rows
                  if set(r.get("factors") or []) & {"high_churn", "high_entropy"}]
        return set(picked[:top_k])
    except Exception:
        return set()
