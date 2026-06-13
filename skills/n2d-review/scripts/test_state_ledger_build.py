import json

import state_ledger_build as build


def test_build_visual_state_ledger_from_storyboards(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    ep1 = root / "脚本" / "第1集"
    ep2 = root / "脚本" / "第2集"
    ep1.mkdir(parents=True)
    ep2.mkdir(parents=True)
    (ep1 / "storyboard.json").write_text(json.dumps({
        "visual_contract": {
            "角色状态演进": {
                "沈念": [
                    {"自": "Clip2", "状态": "左颊新伤", "保持": "至集尾"},
                    {"自": "Clip5", "状态": "金瞳觉醒", "保持": "跨集持续"},
                ]
            }
        }
    }, ensure_ascii=False), encoding="utf-8")
    (ep2 / "storyboard.json").write_text(json.dumps({
        "visual_contract": {
            "角色状态演进": {
                "沈念": [{"自": "Clip1", "状态": "金瞳觉醒解除", "保持": "本镜"}]
            }
        }
    }, ensure_ascii=False), encoding="utf-8")

    data = build.build(str(root))
    assert data["kind"] == build.KIND
    info = data["characters"]["沈念"]
    assert len(info["timeline"]) == 3
    # 至集尾状态只进 timeline，不成为跨集 active modifier。
    assert all("左颊新伤" not in m["description"] for m in info["modifiers"])
    assert any(m["description"] == "金瞳觉醒" and m["active"] is False and m["removed_in"] == "第2集"
               for m in info["modifiers"])


def test_props_from_registry_parses_lifecycle_timeline():
    reg = {"assets": [
        {"id": "PROP_01", "type": "prop", "name": "赐死托盘", "owner": "CHAR_LIU",
         "current_state": "broken",
         "lifecycle": {"states": ["intact", "broken"],
                       "transitions": [{"from": "intact", "to": "broken", "trigger": "Clip_48_摔碎"}]}},
        {"id": "LOC_01", "type": "scene", "name": "冷宫"},
    ]}
    props = build.props_from_registry(reg)
    assert list(props) == ["PROP_01"]
    p = props["PROP_01"]
    assert p["expected_state"] == "broken"
    assert p["timeline"][0]["clip"] == 48
    assert p["issues"] == []


def test_props_from_registry_flags_stale_current_state():
    reg = {"assets": [
        {"id": "PROP_02", "type": "prop", "name": "玉佩", "current_state": "intact",
         "lifecycle": {"states": ["intact", "bloodied"],
                       "transitions": [{"from": "intact", "to": "bloodied", "trigger": "镜头12染血"}]}},
    ]}
    p = build.props_from_registry(reg)["PROP_02"]
    assert p["expected_state"] == "bloodied"
    assert any("落后于最后一笔" in i for i in p["issues"])


def test_props_from_registry_flags_undeclared_state_and_empty():
    reg = {"assets": [
        {"id": "PROP_03", "type": "prop", "name": "剑", "current_state": "ghost",
         "lifecycle": {"states": ["intact"], "transitions": []}},
    ]}
    p = build.props_from_registry(reg)["PROP_03"]
    assert any("不在 lifecycle.states" in i for i in p["issues"])
    assert build.props_from_registry(None) == {}
    assert build.props_from_registry({}) == {}


def test_props_from_registry_freetext_lifecycle_degrades_honestly():
    reg = {"assets": [
        {"id": "PROP_05", "type": "prop", "name": "铜镜", "current_state": "intact",
         "lifecycle": "Clip01-05 作为错脸载体；后续保持同一面铜镜。"},
    ]}
    p = build.props_from_registry(reg)["PROP_05"]
    assert p["timeline"] == [] and p["expected_state"] == "intact"
    assert "lifecycle_note" in p
    assert any("自由文本" in i for i in p["issues"])


def test_props_freetext_static_defaults_to_single_state_not_empty():
    # 「结构化是默认」：静态道具自由文本也给单状态结构化记录 states=[current_state]，不再留空
    reg = {"assets": [
        {"id": "PROP_06", "type": "prop", "name": "铜镜", "current_state": "intact",
         "lifecycle": "Clip01-05 作为错脸载体；后续保持同一面铜镜。"},
    ]}
    p = build.props_from_registry(reg)["PROP_06"]
    assert p["states"] == ["intact"]            # 默认结构化，不留空
    assert p["stateful_freetext"] is False      # 无演进语义 → 不当作待升级


def test_props_freetext_stateful_is_flagged_for_structuring():
    # 自由文本但含状态演进语义（染血）→ 标 stateful_freetext + 明确「应结构化」issue（堵"声明但不验证"）
    reg = {"assets": [
        {"id": "PROP_07", "type": "prop", "name": "信物玉佩", "current_state": "clean",
         "lifecycle": "Clip14 在打斗中染血，此后一直带血。"},
    ]}
    p = build.props_from_registry(reg)["PROP_07"]
    assert p["stateful_freetext"] is True
    assert p["states"] == ["clean"]
    assert any("状态演进语义" in i and "结构化" in i for i in p["issues"])
