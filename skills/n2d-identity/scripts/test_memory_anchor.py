"""memory_anchor 纯函数单测。
cd skills/n2d-identity/scripts && python -m pytest test_memory_anchor.py
"""
import memory_anchor as ma


_ANCHORS = {"CHAR_01": ["出图/共享/图片/定妆_沈念_front.png", "出图/共享/图片/定妆_沈念_side.png"]}


def _char(episodes, *, recurrence=None, total_block=0):
    return {"episodes": {e: {} for e in episodes},
            "recurrence": recurrence or {"max_gap": 0, "long_gap_reentries": [], "high_risk": False},
            "total_block": total_block}


def test_long_gap_reentry_triggers_reinject():
    chars = {"CHAR_01": _char(["第1集", "第4集"], recurrence={
        "max_gap": 2, "high_risk": True,
        "long_gap_reentries": [{"at": "第4集", "prev": "第1集", "gap": 2}]})}
    rows = ma.memory_anchor_rows(chars, _ANCHORS, "第4集")
    assert len(rows) == 1
    r = rows[0]
    assert r["reinject"] and "长间隔再登场" in r["reason"]
    assert r["memory_sink_episode"] == "第1集"
    assert r["memory_anchor_refs"][0].endswith("front.png")


def test_late_episode_triggers_reinject_even_without_gap():
    # 连续出场（无长间隔），但距首登场≥5集 → 晚集累积漂移防护
    eps = [f"第{i}集" for i in range(1, 8)]
    chars = {"CHAR_01": _char(eps)}
    rows = ma.memory_anchor_rows(chars, _ANCHORS, "第7集")
    assert rows and "晚集累积漂移" in rows[0]["reason"]


def test_measured_drift_triggers_reinject():
    chars = {"CHAR_01": _char(["第1集", "第2集"], total_block=3)}
    rows = ma.memory_anchor_rows(chars, _ANCHORS, "第2集")
    assert rows and "已测出跨集漂移" in rows[0]["reason"]


def test_early_stable_character_not_reinjected():
    # 第2集、无 gap、无漂移、非晚集 → 不重注入（不无脑刷）
    chars = {"CHAR_01": _char(["第1集", "第2集"])}
    rows = ma.memory_anchor_rows(chars, _ANCHORS, "第2集")
    assert rows == []


def test_char_not_in_target_episode_skipped():
    chars = {"CHAR_01": _char(["第1集", "第4集"], recurrence={
        "max_gap": 2, "high_risk": True,
        "long_gap_reentries": [{"at": "第4集", "prev": "第1集", "gap": 2}]})}
    # 目标第3集，角色本集不出场 → 跳过
    rows = ma.memory_anchor_rows(chars, _ANCHORS, "第3集")
    assert rows == []


def test_char_memory_anchors_extracts_front_first():
    registry = {"characters": [{"name": "沈念", "forms": [{
        "asset_key": "CHAR_SHEN/常态",
        "reference_group": {"front": "a_front.png", "side": "a_side.png",
                            "back": "a_back.png", "outfit": "a_outfit.png"}}]}]}
    anchors = ma.char_memory_anchors(registry)
    assert anchors["CHAR_SHEN/常态"][0] == "a_front.png"
    assert len(anchors["CHAR_SHEN/常态"]) == ma.MAX_MEMORY_REFS  # 截到上限


def test_reinject_flagged_even_without_anchor_path():
    # 无定妆锚路径仍标 reinject（参考留空待人补），不静默漏掉长间隔角色
    chars = {"CHAR_09": _char(["第1集", "第5集"], recurrence={
        "max_gap": 3, "high_risk": True,
        "long_gap_reentries": [{"at": "第5集", "prev": "第1集", "gap": 3}]})}
    rows = ma.memory_anchor_rows(chars, {}, "第5集")
    assert rows and rows[0]["reinject"] and rows[0]["memory_anchor_refs"] == []
