#!/usr/bin/env python3
"""context_loader.py — 为 novel-* 家族提供统一的创作上下文（Wiki + 设定 + 前文）。

聚合以下信息：
1. 动态百科 (Dynamic Wiki)
2. 设定圣经 & 角色卡
3. 章节细纲 (Outline)
4. 前文窗口 (Previous Context Window)
5. 项目设置 (Settings)
"""
import os
import sys
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from project_io import read_chapters, load_project_settings
from novel_contract import get_product_path
from consistency_scaffold import resolve_character_card

def load_wiki(root):
    try:
        path = get_product_path(root, "wiki")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def load_blueprint_or_bible(root, filename):
    path = os.path.join(root, "设定", filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# 退场/弃置类"未来态"状态：带章号戳且戳晚于 as_of → 该事件此刻尚未发生（diegetic-time 过滤回滚）
_FUTURE_ROLLBACK_STATUS = {"deceased", "discarded", "shattered", "lost",
                          "丢弃", "损毁", "破碎", "遗失", "摧毁"}


def filter_wiki_as_of(wiki, as_of_chapter):
    """把动态百科裁成"截至第 as_of_chapter 章（含）"的视图：**晚于该章**才发生的死亡/退场/弃置
    状态回滚成"尚未发生"。返回过滤后的**副本**，不改原 wiki；as_of 为 None/非数 → 原样返回。

    diegetic time（故事内时间）过滤：正文逐章检索 retrieval.py 早已按章号截断，但 context_loader
    把**整本书的动态 wiki** 注入创作上下文——改写/扩写/编辑中段章时（全书 wiki 已存在），
    "某角色第 50 章死"会泄漏进第 30 章的创作上下文，造成剧透/前后矛盾。此处按 as_of 回滚未来态。
    对标 2026 长篇生成 SOTA（SCORE / Diegetic Knowledge Graph：只检索 story-time ≤ 当前的内容）。"""
    try:
        as_of = int(as_of_chapter)
    except (TypeError, ValueError):
        return wiki
    if not isinstance(wiki, dict):
        return wiki
    out = {}
    for name, e in wiki.items():
        if not isinstance(e, dict):
            out[name] = e
            continue
        e2 = dict(e)
        dc = e2.get("death_chapter")
        if isinstance(dc, (int, float)) and not isinstance(dc, bool) and dc > as_of and e2.get("status") == "deceased":
            e2["status"] = "active"
            e2.pop("death_chapter", None)
            e2["_as_of_rolled_back"] = f"death@{int(dc)}>as_of{as_of}"
        lu = e2.get("last_update")
        if (e2.get("status") in _FUTURE_ROLLBACK_STATUS
                and isinstance(lu, (int, float)) and not isinstance(lu, bool) and lu > as_of):
            e2["status"] = "active"
            e2["_as_of_rolled_back"] = f"status@{int(lu)}>as_of{as_of}"
        out[name] = e2
    return out


def load_power_system(root, as_of_chapter=None):
    """力量体系登记 + 每角色"当前成长状态"（progression 中章号最大的快照）。

    让写章上下文带上"主角现在 Lv.5/筑基中期/力量30"这种真值，作者/AI 在已知现状上推进，
    而不是凭空发明等级数值（避免等级跳变/数值矛盾的根因）。缺登记返回空 dict。

    as_of_chapter 给定时做 diegetic-time 过滤：**只取章号 ≤ as_of 的快照**算"当前现状"，
    防止改写/扩写中段章时把"第 50 章已 Lv.9"这种未来越级状态泄漏进第 30 章上下文。"""
    path = os.path.join(root, "设定", "power_system_registry.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            reg = json.load(f)
    except (OSError, ValueError):
        return {}
    try:
        as_of = int(as_of_chapter)
    except (TypeError, ValueError):
        as_of = None
    current = {}
    for snap in reg.get("progression") or []:
        if not isinstance(snap, dict):
            continue
        char = str(snap.get("character") or "主角")
        ch = snap.get("chapter")
        try:
            ch_n = float(ch)
        except (TypeError, ValueError):
            ch_n = -1
        if as_of is not None and ch_n > as_of:
            continue  # 未来快照不参与"当前现状"（防剧透越级泄漏）
        if char not in current or ch_n >= current[char].get("_ch_n", -1):
            current[char] = {**snap, "_ch_n": ch_n}
    for v in current.values():
        v.pop("_ch_n", None)
    return {
        "system_type": reg.get("system_type"),
        "tiers": reg.get("tiers"),
        "panel_schema": reg.get("panel_schema"),
        "pacing": reg.get("pacing"),
        "current_state": current,   # {角色: 最新快照(level/tier/attrs/战力)}
    }

def get_drafting_context(root, chapter_num, window_size=3):
    """为第 N 章创作提供完整上下文。"""
    settings = load_project_settings(root)
    # diegetic-time 过滤：注入"截至本章（含）"的世界状态，晚于本章的死亡/退场/越级视为尚未发生，
    # 防止改写/扩写/编辑中段章时全书 wiki 的未来态泄漏进创作上下文（剧透/前后矛盾）。
    as_of = chapter_num
    wiki = filter_wiki_as_of(load_wiki(root), as_of)

    # 1. 基础设定
    blueprint = load_blueprint_or_bible(root, "创作蓝图.md")
    bible = load_blueprint_or_bible(root, "设定圣经.md")
    # 角色卡文件名走 resolve_character_card 单一真值源（同时认 角色卡.md 与 人物.md）：
    # continue/expand/condense 派生线写的是 设定/人物.md，写死文件名会让派生线的
    # 写章上下文角色卡恒为空（与 wiki_builder/logic_sentry 消费侧同源）。
    char_card_path = resolve_character_card(root)
    char_card = ""
    if char_card_path and os.path.exists(char_card_path):
        with open(char_card_path, "r", encoding="utf-8") as f:
            char_card = f.read()
    
    # 2. 细纲 (从设定/章纲.md 提取)
    outline = ""
    outline_path = os.path.join(root, "设定", "章纲.md")
    if os.path.exists(outline_path):
        with open(outline_path, "r", encoding="utf-8") as f:
            all_outline = f.read()
            # 简单正则寻找 "第N章" 的部分
            m = re.search(rf"第\s*0*{chapter_num}\s*章\s*(.*?)(?=^第|\Z)", all_outline, re.MULTILINE | re.DOTALL)
            if m:
                outline = m.group(1).strip()

    # 3. 前文窗口
    prev_chapters = []
    if chapter_num > 1:
        start = max(1, chapter_num - window_size)
        prev_chapters = read_chapters(root, chapter_range=(start, chapter_num - 1))

    return {
        "chapter_num": chapter_num,
        "settings": settings,
        "wiki": wiki,
        "blueprint": blueprint,
        "bible": bible,
        "character_card": char_card,
        "outline": outline,
        # 力量体系现状：穿越/系统流写章前让作者/AI 知道主角当前等级/境界/属性/战力，按它推进不凭空发明。
        # as_of 过滤：只给截至本章的成长态，不泄漏未来越级。
        "power_system": load_power_system(root, as_of_chapter=as_of),
        "previous_chapters": [
            {"idx": idx, "path": path, "text": text[:2000] + "..." if len(text) > 2000 else text}
            for idx, path, text in prev_chapters
        ]
    }

import re
