#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical keyword banks for the novel-* deterministic signal scripts.

单一定义源：爽点 / 冲突 / 钩子 / 情感 / 信息（套路）关键词都在这里定义一次，
novel-balance / novel-simulate / novel-promote 共同 import，避免逐脚本复制后漂移。

口径说明见 `skills/novel-balance/references/heatmap-method.md`（pacing 确定性信号），
本模块是其代码侧的落地：referencE 文档讲口径，本文件是被三个脚本共用的实际词表。

附带一个轻量的「目标平台 → 评判档」分类器 `classify_platform`，让 balance/simulate/promote
能像 novel-score 一样按平台调整判据（品质/情感向不用爽文那把密度尺），而不是把单一平台写死。
"""
from __future__ import annotations

from typing import Optional

# ── 爽点（期待兑现：逆袭/打脸/升级）──────────────────────────────
# novel-simulate rookie 人格、novel-balance 爽点密度、novel-promote 都消费这同一份。
PAYOFF_KW = [
    "打脸", "逆袭", "碾压", "突破", "反杀", "升级", "扮猪", "装", "解气",
    "翻盘", "吊打", "震惊", "废柴", "崛起", "无敌", "暴击", "斩杀",
]

# ── 女频「情绪兑现」爽点（拉扯/虐恋/双向奔赴的满足 beat）──────────────
# 2026 女频（无CP大女主 / 强暧昧拉扯 / 古言情绪）的"爽"是情绪价值被满足，不是打脸逆袭。
# 单用 PAYOFF_KW（打脸/碾压）量女频会把拉扯文误判"低爽点/注水"——本桶作为正交叠加，
# 女频项目里并入爽点池（见 payoff_bank_for）。与 EMOTION_KW 区别：EMOTION_KW 是情绪"存在"，
# 本桶是情绪"兑现/翻盘"（破镜重圆/双向奔赴/护妻/复合/打脸情敌）这类期待被满足的高光。
FEMALE_PAYOFF_KW = [
    "双向奔赴", "破镜重圆", "复合", "告白", "心动", "吃醋", "独宠", "护妻",
    "宠溺", "撩", "暧昧", "拉扯", "醋意", "占有", "心疼", "守护", "回应",
    "和好", "表白", "牵手", "对视", "反差", "下跪", "追妻", "悔",
]

# ── 冲突 / 转折（冲突强度近似）──────────────────────────────────
CONFLICT_KW = [
    "杀", "血", "刀", "剑", "怒", "吼", "战", "斗", "击", "破", "死", "逼",
    "撕", "崩", "爆", "厉", "狠", "拼", "夺", "反", "叛", "敌", "危", "险",
    "突然", "猛地", "骤然", "竟", "却", "不料", "没想到",
]

# novel-promote 的冲突词表历史上口径更偏「宣发爆点」（含 reaction 词），单列保留其侧重，
# 但仍集中在本模块统一维护，避免散落脚本里。
PROMO_CONFLICT_KW = [
    "杀", "战", "斗", "反杀", "逼", "怒", "敌", "危", "险", "背叛", "夺",
    "破", "逃", "追", "撞", "斩", "跪", "威胁", "审判",
]

# ── 钩子 / 悬念标记 ───────────────────────────────────────────
# 章末钩子强度（simulate）。
HOOK_MARKERS = [
    "？", "?", "但", "却", "突然", "竟", "竟然", "居然", "不料", "没想到",
    "此时", "就在", "猛地", "骤然", "下一刻", "原来",
]

# 宣发场景里挖钩子用的更宽口径（含"真相/秘密/只见"等爆点引子）。
PROMO_HOOK_KW = [
    "突然", "竟", "竟然", "却", "不料", "没想到", "下一刻", "原来", "真相",
    "秘密", "最后", "只见", "谁也没想到",
]

# ── 反转 / 转折标记（反转密度近似）────────────────────────────────
# 商业爽文早期反转密度默认预警线由 novel-balance/pacing_analyzer.py 管理；
# 市场基线更新时应校准，不在词库里写死来源结论。
# 反转 = 身份/关系/目标/信息态势的实质翻转，这里用确定性"翻转引子词"做近似计数，
# 命中是**候选线索**（闪回/伏笔可豁免），最终是否真反转由 LLM 复核。
REVERSAL_KW = [
    "反转", "逆转", "竟然", "没想到", "没料到", "不料", "原来", "惊变",
    "突变", "陡然", "骤变", "反杀", "翻盘", "揭穿", "真相", "身份暴露",
    "竟是", "居然是", "却不知", "万万没想到", "峰回路转",
]

# ── 情感 / 互动（emote 人格、宣发情绪爆点）────────────────────────
EMOTION_KW = [
    "心疼", "温柔", "守护", "拥抱", "告白", "吃醋", "暧昧", "牵手",
    "对视", "脸红", "心动", "眼泪", "微笑", "羁绊", "并肩", "回眸",
]

# novel-promote 情绪爆点更偏「虐/宿命」侧重，单列保留。
PROMO_EMOTION_KW = [
    "心疼", "泪", "恨", "爱", "痛", "冷笑", "颤", "绝望", "不甘", "宿命",
    "温柔", "沉默", "崩溃", "拥抱", "告白", "抬头",
]

# ── 逻辑 / 设定（logic 人格）──────────────────────────────────
LOGIC_KW = [
    "因为", "所以", "原理", "规则", "体系", "推断", "逻辑", "境界",
    "等级", "代价", "限制", "条件", "破绽", "证据", "推理", "布局",
]

# ── 套路 / 同质化（critic 人格、套路密度）────────────────────────
CLICHE_KW = [
    "退婚", "老爷爷", "戒指", "系统", "穿越", "重生", "神医", "赘婿",
    "废柴逆袭", "扮猪吃虎", "纨绔", "圣女", "天才", "炼丹", "宗门",
]

# ── 视觉高光（宣发出图爆点）──────────────────────────────────
PROMO_VISUAL_KW = [
    "血", "光", "火", "雷", "剑", "刀", "影", "雾", "雨", "风", "焰", "骨",
    "裂", "碎", "爆", "坠", "冲", "领域", "符", "阵", "城", "宫", "殿",
]


# ── 目标平台 → 评判档 ────────────────────────────────────────
# 与 novel-score 的「商业爽文向 / 品质向」二分同源：品质/情感向平台不该被爽文密度尺判注水。
# 候选值口径见 novel-craft/references/选择点与偏好.md 的 `目标平台`：
#   起点 | 番茄 | 晋江 | 抖音漫剧 | 红果 | 历史向 | 跨平台 …（+ 自定义自由值）
LITERARY_PLATFORM_MARKERS = ("品质", "晋江", "历史", "情感", "言情", "纯文学", "文学")
COMMERCIAL_PLATFORM_MARKERS = (
    "爽文", "红果", "抖音", "番茄", "短剧", "漫剧", "推文", "tiktok", "douyin",
)

PROFILE_LITERARY = "品质向"
PROFILE_COMMERCIAL = "商业爽文向"

# 女频是**正交**维度（与品质/商业二分独立）：番茄女频=商业向、晋江=品质向，都可能是女频。
# 命中只决定"爽点是否并入情绪兑现桶"，不改 classify_platform 的二分（避免下游分支全改）。
# 女频信号可来自 `目标平台` 也可来自 `题材`/`赛道` 选择点（如"无CP大女主""暧昧拉扯""古言"）。
FEMALE_ORIENTED_MARKERS = (
    "女频", "女生", "言情", "古言", "现言", "大女主", "无cp", "无 cp", "甜宠",
    "虐恋", "暧昧", "拉扯", "宠文", "耽美", "bl", "girl", "晋江",
)


def classify_platform(target_platform: Optional[str]) -> str:
    """把 `目标平台` 归一成评判档：'品质向' 或 '商业爽文向'。

    与 novel-score 的取档逻辑保持一致（'品质' 命中即品质向），并补充按平台名识别
    晋江/历史向/情感向等品质/情感侧平台。无法判定时保守落 '商业爽文向'（密尺，多报不漏报）。
    """
    text = str(target_platform or "").strip().lower()
    if not text:
        return PROFILE_COMMERCIAL
    if any(marker.lower() in text for marker in LITERARY_PLATFORM_MARKERS):
        return PROFILE_LITERARY
    if any(marker.lower() in text for marker in COMMERCIAL_PLATFORM_MARKERS):
        return PROFILE_COMMERCIAL
    return PROFILE_COMMERCIAL


def is_literary(target_platform: Optional[str]) -> bool:
    return classify_platform(target_platform) == PROFILE_LITERARY


def is_female_oriented(*signals: Optional[str]) -> bool:
    """女频判定（正交于品质/商业档）。任一选择点信号命中女频标记即 True。

    传 `目标平台`、`题材`、`赛道` 等任意若干信号字符串；空/无命中 → False（按通用爽文量爽点）。
    """
    text = " ".join(str(s or "") for s in signals).strip().lower()
    if not text:
        return False
    return any(marker in text for marker in FEMALE_ORIENTED_MARKERS)


def payoff_bank_for(*signals: Optional[str]) -> list:
    """返回该项目应使用的爽点词桶：女频并入情绪兑现桶，否则只用通用 PAYOFF_KW。

    balance/simulate 等"爽点密度"消费方用它取桶，避免女频拉扯文被打脸尺误判注水。
    """
    if is_female_oriented(*signals):
        return PAYOFF_KW + FEMALE_PAYOFF_KW
    return list(PAYOFF_KW)
