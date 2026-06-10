# -*- coding: utf-8 -*-
"""
test for wiki_builder + logic_sentry.
Run from this directory:
    cd skills/novel-wiki/scripts && python3 -m pytest test_logic_sentry.py
"""
import os
import wiki_builder
import logic_sentry


def _mk_project(tmp_path):
    proj = tmp_path / "书"
    (proj / "设定").mkdir(parents=True)
    (proj / "章节").mkdir(parents=True)
    (proj / "设定" / "角色卡.md").write_text(
        "# 角色卡\n\n## 王敦\n身份：剑修\n\n## 李慕白\n身份：宿敌\n",
        encoding="utf-8")
    (proj / "章节" / "第01章.md").write_text("王敦提剑上山，李慕白在崖边等他。", encoding="utf-8")
    (proj / "章节" / "第02章.md").write_text("一剑落下，李慕白当场身亡，尸身坠崖。", encoding="utf-8")
    return proj


def test_parse_character_names(tmp_path):
    proj = _mk_project(tmp_path)
    names = wiki_builder.parse_character_names(str(proj))
    assert "王敦" in names and "李慕白" in names


def test_build_wiki_detects_death(tmp_path):
    proj = _mk_project(tmp_path)
    wiki = wiki_builder.build_wiki(str(proj))
    assert wiki["李慕白"]["status"] == "deceased"
    assert wiki["李慕白"]["death_chapter"] == 2
    assert wiki["李慕白"].get("auto") is True
    # 王敦 仍存活
    assert wiki["王敦"]["status"] == "active"
    assert wiki["王敦"]["last_seen_chapter"] == 1


def test_flashback_not_counted_as_death(tmp_path):
    proj = tmp_path / "书2"
    (proj / "设定").mkdir(parents=True)
    (proj / "章节").mkdir(parents=True)
    (proj / "设定" / "角色卡.md").write_text("## 李慕白\n", encoding="utf-8")
    (proj / "章节" / "第01章.md").write_text("他回忆起李慕白身亡那夜的雨。", encoding="utf-8")
    wiki = wiki_builder.build_wiki(str(proj))
    # 闪回语境不应判死
    assert wiki["李慕白"]["status"] == "active"


def test_neighbor_death_not_misattributed(tmp_path):
    """'李慕白当场身亡。王敦默立' —— 王敦在死亡词附近但非他死，不得误判。"""
    proj = _mk_project(tmp_path)
    wiki = wiki_builder.build_wiki(str(proj))
    assert wiki["李慕白"]["status"] == "deceased"
    assert wiki["王敦"]["status"] == "active"   # 关键：邻近他人之死不上身


def test_deceased_reactivation_alert(tmp_path):
    proj = _mk_project(tmp_path)
    wiki = wiki_builder.build_wiki(str(proj))
    # 第3章李慕白又活动 → 阻断级告警
    alerts = logic_sentry.scan_chapter(wiki, "李慕白冷笑着挥剑反击。", 3)
    types = [a["type"] for a in alerts]
    assert "deceased_reactivation" in types
    assert any(a["severity"] == "阻断级" for a in alerts)


def test_reactivation_suppressed_by_flashback(tmp_path):
    proj = _mk_project(tmp_path)
    wiki = wiki_builder.build_wiki(str(proj))
    alerts = logic_sentry.scan_chapter(wiki, "王敦想起李慕白当年的笑。", 3)
    assert not any(a["type"] == "deceased_reactivation" for a in alerts)


def test_no_alert_before_death_chapter(tmp_path):
    proj = _mk_project(tmp_path)
    wiki = wiki_builder.build_wiki(str(proj))
    # 死亡章(2)之前/当章不应报复活
    alerts = logic_sentry.scan_chapter(wiki, "李慕白还活着。", 1)
    assert not any(a["type"] == "deceased_reactivation" for a in alerts)


def test_discarded_item_reuse():
    wiki = {"清月剑": {"category": "item", "status": "shattered", "last_update": 5}}
    alerts = logic_sentry.scan_chapter(wiki, "他举起清月剑，再次催动剑气。", 8)
    assert any(a["type"] == "discarded_item_reuse" and a["severity"] == "阻断级" for a in alerts)
    # 仅提及不使用 → 不报
    alerts2 = logic_sentry.scan_chapter(wiki, "清月剑的碎片散落一地。", 8)
    assert not any(a["type"] == "discarded_item_reuse" for a in alerts2)


def test_rebuild_clears_stale_auto_death(tmp_path):
    """重扫时未确认的 auto 死亡先清回 active，让修正传播；人工确认状态保留。"""
    proj = _mk_project(tmp_path)
    stale = {
        "王敦": {"category": "character", "status": "deceased", "death_chapter": 2, "auto": True},
        "李慕白": {"category": "character", "status": "deceased", "auto": False, "location": "断魂崖"},
    }
    wiki = wiki_builder.build_wiki(str(proj), existing=stale)
    assert wiki["王敦"]["status"] == "active"          # 旧误报被纠正
    assert wiki["李慕白"]["status"] == "deceased"        # 人工确认保留
    assert wiki["李慕白"]["location"] == "断魂崖"          # 人工字段不丢


def test_clean_chapter_no_alerts():
    wiki = {"王敦": {"category": "character", "status": "active"}}
    assert logic_sentry.scan_chapter(wiki, "王敦继续赶路。", 10) == []
