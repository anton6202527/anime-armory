#!/usr/bin/env python3
"""题材感知风格推荐 + 风格契约预设的单元测试。

运行：cd skills/n2d/_lib && python -m pytest test_n2d_visual_styles.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from n2d_visual_styles import (  # noqa: E402
    DEFAULT_STYLE,
    STYLE_OPTIONS,
    GENRE_STYLE_AFFINITY,
    KEYWORD_STYLE_AFFINITY,
    recommend_style,
    format_style_recommendation_markdown,
    style_contract_for,
)


def test_every_affinity_target_is_a_real_style():
    """推荐表里每个目标风格都必须是菜单里真实存在的值（防笔误漂出菜单）。"""
    valid = set(STYLE_OPTIONS)
    for genre, affinity in GENRE_STYLE_AFFINITY.items():
        for style, weight in affinity:
            assert style in valid, f"题材 {genre} 指向了不存在的风格 {style}"
            assert weight > 0
    for kw, affinity in KEYWORD_STYLE_AFFINITY:
        for style, weight in affinity:
            assert style in valid, f"关键词 {kw} 指向了不存在的风格 {style}"
            assert weight > 0


def test_no_signal_falls_back_to_default():
    rec = recommend_style(genres=(), genre_text="")
    assert rec["recommended"] == DEFAULT_STYLE
    assert rec["is_default_fallback"] is True
    assert rec["ranked"] == []
    assert "未检测到题材信号" in rec["rationale"]


def test_xianxia_system_genre_recommends_guofeng_default():
    """本仓库 demo《从变身少女开始斩妖除魔》：修仙+系统流+穿越+斩妖 → 冷灰写实3D国风漫剧。"""
    rec = recommend_style(
        genres=("修仙", "系统流", "穿越"),
        genre_text="从变身少女开始斩妖除魔 修仙",
    )
    assert rec["recommended"] == "冷灰写实3D国风漫剧"
    assert rec["is_default_fallback"] is True
    # 国漫写实应是强次选（修仙+系统流都投它）。
    ranked = dict(rec["ranked"])
    assert ranked["国漫写实"] >= 4
    assert "斩妖" in rec["rationale"] or "修仙" in rec["rationale"]


def test_palace_drama_recommends_yunv():
    rec = recommend_style(genres=("宫斗",), genre_text="宫廷 女频 言情")
    assert rec["recommended"] == "古风乙女清雅"
    assert rec["is_default_fallback"] is False


def test_urban_warlord_recommends_cinematic():
    rec = recommend_style(genres=("战神", "都市"), genre_text="")
    assert rec["recommended"] == "写实电影感"


def test_suspense_keyword_pushes_dark_realism():
    rec = recommend_style(genres=(), genre_text="刑侦 悬疑 复仇")
    assert rec["recommended"] == "暗黑悬疑写实"


def test_tie_break_prefers_menu_order_default_first():
    """两风格平分时，按 STYLE_OPTIONS 顺序取靠前者（DEFAULT 在首位故偏稳）。"""
    # 穿越：冷灰+1, 国漫写实+1 平分 → 取菜单更靠前的 冷灰写实3D国风漫剧。
    rec = recommend_style(genres=("穿越",), genre_text="")
    assert rec["recommended"] == DEFAULT_STYLE


def test_signals_are_explainable():
    rec = recommend_style(genres=("修仙",), genre_text="斩妖")
    keys = {(s["source"], s["key"]) for s in rec["signals"]}
    assert ("genre", "修仙") in keys
    assert ("keyword", "斩妖") in keys


def test_format_markdown_contains_recommendation_and_caveat():
    rec = recommend_style(genres=("修仙",), genre_text="斩妖")
    md = format_style_recommendation_markdown(rec)
    assert rec["recommended"] in md
    assert "预选默认" in md  # 强调可覆盖、非铁律
    assert "候选排名" in md


def test_recommended_style_has_a_full_contract():
    """推荐出来的任何风格都必须能取到完整六字段契约（下游 scaffold 依赖）。"""
    for genre in GENRE_STYLE_AFFINITY:
        rec = recommend_style(genres=(genre,), genre_text="")
        contract = style_contract_for(rec["recommended"])
        for field in ("风格名", "视觉基调", "镜头与构图", "光色策略", "运动边界", "风格禁忌", "style_anchor"):
            assert field in contract and contract[field]
