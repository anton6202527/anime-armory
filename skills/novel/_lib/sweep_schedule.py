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


def is_due(chapter, interval, target=0):
    """本章写后是否触发一次小批回扫。"""
    chapter, interval, target = int(chapter), int(interval), int(target or 0)
    if interval <= 0 or chapter <= 0:
        return False
    if chapter % interval == 0:
        return True
    if target and chapter == target:
        return True
    if in_midstory_band(chapter, target) and chapter % half_interval(interval) == 0:
        return True
    return False


def window_for(chapter, interval, target=0):
    """due 章的回扫窗口 (start, end)：start = 上一 due 点 + 1，保证无缝覆盖。"""
    prev = 0
    for c in range(int(chapter) - 1, 0, -1):
        if is_due(c, interval, target):
            prev = c
            break
    return prev + 1, int(chapter)


def next_due_after(chapter, interval, target=0):
    """下一个 due 点章号；interval<=0 返回 None。"""
    chapter, interval, target = int(chapter), int(interval), int(target or 0)
    if interval <= 0:
        return None
    limit = max(target, chapter + interval)
    for c in range(chapter + 1, limit + 1):
        if is_due(c, interval, target):
            return c
    return None
