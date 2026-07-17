# -*- coding: utf-8 -*-
"""test_context_loader — diegetic-time（故事内时间）as-of 过滤。

Run: cd skills/novel/_lib && python3 -m pytest test_context_loader.py
"""
import context_loader as cl


def test_filter_wiki_rolls_back_future_death():
    wiki = {"李慕白": {"category": "character", "status": "deceased", "death_chapter": 50}}
    # 写第 30 章：第 50 章才死 → 此刻还活着
    out = cl.filter_wiki_as_of(wiki, 30)
    assert out["李慕白"]["status"] == "active"
    assert "death_chapter" not in out["李慕白"]
    assert out["李慕白"]["_as_of_rolled_back"].startswith("death@50")
    # 原 wiki 不被改（返回副本）
    assert wiki["李慕白"]["status"] == "deceased"


def test_filter_wiki_keeps_past_and_current_death():
    wiki = {"甲": {"category": "character", "status": "deceased", "death_chapter": 20}}
    assert cl.filter_wiki_as_of(wiki, 30)["甲"]["status"] == "deceased"   # 过去已死·保留
    assert cl.filter_wiki_as_of(wiki, 20)["甲"]["status"] == "deceased"   # 本章死·保留（as_of 含当章）


def test_filter_wiki_rolls_back_future_discarded_item():
    wiki = {"清月剑": {"category": "item", "status": "shattered", "last_update": 40}}
    out = cl.filter_wiki_as_of(wiki, 25)
    assert out["清月剑"]["status"] == "active"
    out2 = cl.filter_wiki_as_of(wiki, 45)
    assert out2["清月剑"]["status"] == "shattered"  # 已发生·保留


def test_filter_wiki_none_as_of_passthrough():
    wiki = {"甲": {"status": "deceased", "death_chapter": 50}}
    assert cl.filter_wiki_as_of(wiki, None) is wiki  # 非数 → 原样


def test_drafting_context_resolves_renwu_md_character_card(tmp_path):
    # 派生线（continue/expand/condense）落的是 设定/人物.md 而非 角色卡.md——
    # 写死文件名会让派生线写章上下文角色卡恒为空（B2 消费侧漏网点，2026-07 修）。
    root = tmp_path
    (root / "设定").mkdir()
    (root / "设定" / "人物.md").write_text("## 王敦\n性格：狂狷", encoding="utf-8")
    ctx = cl.get_drafting_context(str(root), 1)
    assert "王敦" in ctx["character_card"]


def test_drafting_context_prefers_canonical_card(tmp_path):
    root = tmp_path
    (root / "设定").mkdir()
    (root / "设定" / "角色卡.md").write_text("## 正主", encoding="utf-8")
    (root / "设定" / "人物.md").write_text("## 备胎", encoding="utf-8")
    ctx = cl.get_drafting_context(str(root), 1)
    assert "正主" in ctx["character_card"]


def test_load_power_system_as_of_filters_future(tmp_path):
    import json
    root = tmp_path
    (root / "设定").mkdir()
    (root / "设定" / "power_system_registry.json").write_text(json.dumps({
        "system_type": "修仙",
        "progression": [
            {"character": "主角", "chapter": 10, "tier": "炼气"},
            {"character": "主角", "chapter": 50, "tier": "元婴"},
        ]
    }), encoding="utf-8")
    # 写第 30 章：只能看到 ≤30 的最新态（炼气），看不到第 50 章的元婴
    ps = cl.load_power_system(str(root), as_of_chapter=30)
    assert ps["current_state"]["主角"]["tier"] == "炼气"
    # 无 as_of → 取全局最新（元婴）
    ps_all = cl.load_power_system(str(root))
    assert ps_all["current_state"]["主角"]["tier"] == "元婴"
