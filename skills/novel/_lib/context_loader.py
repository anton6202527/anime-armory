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

def load_power_system(root):
    """力量体系登记 + 每角色"当前成长状态"（progression 中章号最大的快照）。

    让写章上下文带上"主角现在 Lv.5/筑基中期/力量30"这种真值，作者/AI 在已知现状上推进，
    而不是凭空发明等级数值（避免等级跳变/数值矛盾的根因）。缺登记返回空 dict。"""
    path = os.path.join(root, "设定", "power_system_registry.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            reg = json.load(f)
    except (OSError, ValueError):
        return {}
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
    wiki = load_wiki(root)
    
    # 1. 基础设定
    blueprint = load_blueprint_or_bible(root, "创作蓝图.md")
    bible = load_blueprint_or_bible(root, "设定圣经.md")
    char_card = load_blueprint_or_bible(root, "角色卡.md")
    
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
        "power_system": load_power_system(root),
        "previous_chapters": [
            {"idx": idx, "path": path, "text": text[:2000] + "..." if len(text) > 2000 else text}
            for idx, path, text in prev_chapters
        ]
    }

import re
