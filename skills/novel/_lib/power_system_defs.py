#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""力量体系(power system) 单一真值源：题材/母题关键词 + 研究落地的等级体系/面板/升级节奏候选模板。

novel 线内独立模块。被
novel-wiki/scripts/power_system.py（检测+机检引擎）、novel-review consistency_audit、post_write 消费。

为什么需要：穿越/系统流爽文的"等级/成长数值"一致性是命门——等级跳变、战力前后矛盾、属性突变、
升级节奏崩（数值膨胀/越级无理由）是高发穿帮。本模块把网文力量体系的专业惯例固化成机器可校验的默认。

⚠️ 候选快照（易变·境界序列/数值惯例会随市场流变）。
采集日期：2026-06-19  来源：知乎《系统文基础设定详解》、起点/凡人修仙传境界体系讨论、
maliangwriter《系统流/无限流 AI 创作指南：面板设计》、知乎"网文战力崩坏根本原因"。
正式落地某剧时仍由作者按设定圣经覆盖；这里只给"未声明时的合理默认 + 机检判据"。
"""
from __future__ import annotations

from typing import Optional, Tuple

# kind 写进 设定/power_system_registry.json 的 "kind" 字段（NOVEL_PRODUCT_KINDS 用短键 "power_system"）。
POWER_SYSTEM_REGISTRY_KIND = "novel_power_system_registry"

# ── 题材检测关键词（novel 线本地·命中 ≥ GENRE_MIN_HITS 即判定，多题材取最多者）────────────
GENRE_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("系统流", ("系统", "面板", "宿主", "绑定", "签到", "任务奖励", "抽奖", "属性面板",
              "经验值", "升级", "金手指", "叮——", "恭喜宿主", "积分", "技能点", "兑换")),
    ("穿越", ("穿越", "重生", "魂穿", "异世界", "回到古代", "前世", "上一世", "醒来发现", "莫名来到")),
    ("修仙", ("修仙", "修真", "灵气", "渡劫", "金丹", "元婴", "筑基", "练气", "境界", "御剑", "宗门", "灵根")),
    ("玄幻", ("斗气", "魔法", "斗气大陆", "武魂", "魂环", "异火", "斗技", "玄气", "武灵")),
    ("都市", ("总裁", "豪门", "霸总", "微信", "写字楼", "董事长", "集团")),
    ("战神", ("战神", "兵王", "退役", "佣兵", "龙组", "镇国", "特种兵")),
)
GENRE_MIN_HITS = 2

# 触发力量体系自检的题材（有明确等级/数值成长的题材才需要逐章数值一致性机检）。
POWER_GENRES = ("系统流", "修仙", "玄幻", "战神")

# ── 母题桥段关键词（系统面板/升级 等复现场景"在场"检测）──────────────────────────────
# novel 侧只用来判"系统流小说在某段落里有没有该出现的面板/升级桥段"。
MOTIF_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("system_panel", ("系统面板", "面板", "属性栏", "状态栏", "属性面板", "数据面板", "光幕", "信息面板")),
    ("level_up", ("升级", "等级提升", "突破", "进阶", "境界提升", "属性提升", "经验满", "恭喜宿主")),
    ("signin", ("签到", "每日签到", "连续签到", "签到奖励", "打卡")),
    ("gacha", ("抽奖", "抽卡", "转盘", "开箱", "幸运抽取", "十连")),
    ("loot", ("爆装备", "掉落", "爆出", "获得装备", "开宝箱", "战利品", "掉宝")),
)
MOTIF_MIN_HITS = 1

# ── 等级体系候选模板（按系统类型）──────────────────────────────────────────────────
# 修仙标准境界（凡人修仙传体系）：每境界再分 初/中/后/大圆满。
CULTIVATION_REALMS = ("练气", "筑基", "结丹", "元婴", "化神", "炼虚", "合体", "大乘", "渡劫")
CULTIVATION_REALMS_EXTENDED = CULTIVATION_REALMS + ("真仙", "金仙", "太乙", "大罗")
CULTIVATION_SUBTIERS = ("初期", "中期", "后期", "大圆满")
# 玄幻斗气类常见序列（候选·可被设定圣经覆盖）。
XUANHUAN_TIERS = ("斗者", "斗师", "大斗师", "斗灵", "斗王", "斗皇", "斗宗", "斗尊", "斗圣", "斗帝")

# ── 系统流面板默认模板（研究：属性 ≤ 7）────────────────────────────────────────────
SYSTEM_PANEL_TEMPLATE = {
    "level_field": "等级",
    "exp_field": "经验值",
    # 5 核心属性 + 至多 2 特殊属性（因果/气运），总数 ≤ ATTRS_MAX。
    "core_attrs": ("力量", "敏捷", "体质", "精神", "幸运"),
    "special_attr_examples": ("因果值", "气运", "魅力", "悟性"),
    "resources": ("技能点", "积分"),   # 积分=商城点
}
ATTRS_MAX = 7  # 面板属性总数上限（超过=信息过载，建议精简）

# ── 升级节奏默认（研究落地）──────────────────────────────────────────────────────
PACING_DEFAULTS = {
    "per_chapter": "小奖：经验值/常见道具/线索（量级如 经验+50）",
    "every_5_chapters": "中奖：属性突破 / 新技能",
    "every_20_chapters": "大奖：隐藏任务 / 稀有装备 / 越阶(rank jump)",
    "attr_relevance_window": 10,   # 每个属性 ≥ 每 10 章要在剧情里起一次作用，否则是装饰位
    "panel_audit_window": 10,      # 每 10 章核对一次角色面板（人工+机检）
    "max_tier_jump_per_chapter": 1,  # 单章境界/大级跳变上限（越级须有明确代价/机缘，否则疑似数值膨胀）
}

# ── 成长单调字段（只增不减·机检退档=阻断级）──────────────────────────────────────
# 等级/境界序/战力一旦在某章是 N，后续章不能 < N（除非显式标 跌境/废修/封印 等剧情事件）。
MONOTONIC_FIELDS = ("level", "等级", "tier_rank", "境界序", "战力", "power")
# 允许下跌的剧情豁免标记（progression 快照写 regress_reason 命中这些即不判退档为阻断）。
REGRESS_EXEMPT_KEYWORDS = ("跌境", "废修", "废了", "自废", "封印", "重伤", "夺舍失败", "境界跌落", "散功")


def genre_needs_power_check(genre: str) -> bool:
    """该题材是否带等级数值成长、需要力量体系自检（系统流/修仙/玄幻/战神）。纯函数·可测。"""
    return any(g in str(genre or "") for g in POWER_GENRES)


def detect_system_type(genre: str) -> str:
    """题材 → 默认力量体系类型（决定用哪套等级模板）。纯函数·可测。"""
    g = str(genre or "")
    if "修仙" in g or "修真" in g:
        return "修仙"
    if "玄幻" in g:
        return "玄幻"
    if "系统" in g:
        return "系统流"
    return "通用"


def default_tier_sequence(system_type: str) -> Tuple[str, ...]:
    """力量体系类型 → 默认等级/境界序列候选。系统流走数值等级（空序列=用 level_cap）。纯函数·可测。"""
    if system_type == "修仙":
        return CULTIVATION_REALMS
    if system_type == "玄幻":
        return XUANHUAN_TIERS
    return ()  # 系统流/通用：数值等级，无命名境界


def starter_registry(system_type: str) -> dict:
    """按力量体系类型给一份可写入 设定/power_system_registry.json 的脚手架骨架。纯函数·可测。"""
    seq = default_tier_sequence(system_type)
    tiers = {
        "kind": "realm" if seq else "level",
        "sequence": list(seq),
        "subtiers": list(CULTIVATION_SUBTIERS) if system_type == "修仙" else [],
        "level_cap": None if seq else 100,
    }
    panel = {
        "level_field": SYSTEM_PANEL_TEMPLATE["level_field"],
        "exp_field": SYSTEM_PANEL_TEMPLATE["exp_field"],
        "attrs": list(SYSTEM_PANEL_TEMPLATE["core_attrs"]),
        "resources": list(SYSTEM_PANEL_TEMPLATE["resources"]),
    } if system_type in ("系统流", "通用") else {}
    return {
        "kind": POWER_SYSTEM_REGISTRY_KIND,
        "version": 1,
        "system_type": system_type,
        "tiers": tiers,
        "panel_schema": panel,
        "pacing": dict(PACING_DEFAULTS),
        "progression": [],   # 逐章成长快照，写章时由作者/检测器累积；机检单调不回退
        "_note": "候选默认（power_system_defs.py·采集 2026-06-19），按设定圣经覆盖；progression 逐章填实际等级/属性/战力。",
    }
