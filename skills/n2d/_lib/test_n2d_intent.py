#!/usr/bin/env python3
"""逐镜意图黑板（StageC）单测。cd skills/n2d/_lib && python -m pytest test_n2d_intent.py"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n2d_intent as ni  # noqa: E402


def _write_sb(tmp_path, clips, evolution=None):
    ep_dir = os.path.join(str(tmp_path), "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    sb = {"clips": clips}
    if evolution is not None:
        sb["visual_contract"] = {"角色状态演进": evolution}
    with open(os.path.join(ep_dir, "storyboard.json"), "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False)
    return str(tmp_path)


def test_build_derives_per_shot_intent(tmp_path):
    root = _write_sb(tmp_path, [
        {"id": "Clip_01", "shot_type": "reveal", "description": "近景特写",
         "continuity": {"expression_span": "大", "need_endframe": True, "action_beat": True}},
        {"id": "Clip_02", "description": "空镜", "continuity": {}},
    ])
    obj = ni.build_shot_intent(root, "第1集")
    assert obj["kind"] == ni.SHOT_INTENT_KIND
    s1 = obj["shots"][0]
    assert s1["clip_no"] == 1 and s1["expression_span"] == "大"
    assert s1["need_endframe"] is True and s1["action_beat"] is True and s1["closeup"] is True
    assert obj["shots"][1]["need_endframe"] is False


def test_write_load_roundtrip_and_path(tmp_path):
    root = _write_sb(tmp_path, [{"id": "Clip_01", "continuity": {}}])
    path = ni.write_shot_intent(root, "第1集")
    assert path.endswith(os.path.join("脚本", "第1集", "shot_intent.json"))
    loaded = ni.load_shot_intent(root, "第1集")
    assert loaded and loaded["kind"] == ni.SHOT_INTENT_KIND
    assert ni.shot_intent_for(root, "第1集", 1)["clip_no"] == 1
    assert ni.shot_intent_for(root, "第1集", 99) is None


def test_explicit_evolution_only_consumes_field_tagged(tmp_path):
    # 黑板含一条作者 field-tag 的 face 声明 + 一条未标 field 的脚手架（不被消费·防双源）。
    root = _write_sb(tmp_path, [{"id": "Clip_01", "continuity": {}}])
    ni.write_shot_intent(root, "第1集")
    path = ni.shot_intent_path(root, "第1集")
    obj = ni.load_shot_intent(root, "第1集")
    obj["allowed_evolution"] = [
        {"character": "沈念", "from_shot": 5, "to_shot": 9, "field": "face", "desc": "无痕易容(关键词漏检)", "source": "author"},
        {"character": "李四", "from_shot": 3, "to_shot": None, "field": "", "desc": "未标 field 脚手架", "source": "seed"},
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)

    face = ni.explicit_evolution_for(root, "第1集", "face")
    assert face == {"沈念": [(5, 9, "无痕易容(关键词漏检)")]}      # 只消费 field=="face"
    assert ni.explicit_evolution_for(root, "第1集", "hair") == {}  # 未声明 hair
    assert ni.explicit_evolution_for(root, "第1集", "costume") == {}  # field="" 的脚手架不算


def test_author_entries_preserved_on_rebuild(tmp_path):
    root = _write_sb(tmp_path, [{"id": "Clip_01", "continuity": {}}],
                     evolution={"王五": [{"自": "Clip3", "状态": "换上铠甲"}]})
    ni.write_shot_intent(root, "第1集")
    path = ni.shot_intent_path(root, "第1集")
    obj = ni.load_shot_intent(root, "第1集")
    obj["allowed_evolution"].append(
        {"character": "沈念", "from_shot": 5, "to_shot": 9, "field": "face", "desc": "易容", "source": "author"})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    # 重建后作者条目仍在
    ni.write_shot_intent(root, "第1集")
    after = ni.load_shot_intent(root, "第1集")
    authored = [e for e in after["allowed_evolution"] if e.get("source") == "author"]
    assert any(e["character"] == "沈念" and e["field"] == "face" for e in authored)


def test_missing_blackboard_returns_empty(tmp_path):
    root = str(tmp_path)
    assert ni.load_shot_intent(root, "第1集") is None
    assert ni.explicit_evolution_for(root, "第1集", "face") == {}


def test_stale_blackboard_self_invalidates(tmp_path):
    # 黑板建于 1 镜 storyboard；作者声明 face 演进。随后 storyboard 改成 3 镜（镜数变）→ 黑板陈旧。
    root = _write_sb(tmp_path, [{"id": "Clip_01", "continuity": {}}])
    ni.write_shot_intent(root, "第1集")
    path = ni.shot_intent_path(root, "第1集")
    obj = ni.load_shot_intent(root, "第1集")
    obj["allowed_evolution"] = [
        {"character": "沈念", "from_shot": 1, "to_shot": 1, "field": "face", "desc": "易容", "source": "author"}]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    # 新鲜：1 镜 == 1 镜 → 消费作者声明
    assert ni.blackboard_is_stale(root, "第1集") is False
    assert ni.explicit_evolution_for(root, "第1集", "face") == {"沈念": [(1, 1, "易容")]}
    # storyboard 改成 3 镜（黑板未重建）→ 陈旧 → 不据可能错位的声明降级真崩
    _write_sb(tmp_path, [{"id": f"Clip_{i:02d}", "continuity": {}} for i in range(1, 4)])
    assert ni.blackboard_is_stale(root, "第1集") is True
    assert ni.explicit_evolution_for(root, "第1集", "face") == {}


def test_stale_blackboard_detects_equal_count_content_change(tmp_path):
    # 等镜数内容改（换镜/改写）：旧的纯镜数比对抓不到，storyboard_sha 指纹能抓到。
    root = _write_sb(tmp_path, [{"id": "Clip_01", "description": "她站在门口", "continuity": {}}])
    ni.write_shot_intent(root, "第1集")
    path = ni.shot_intent_path(root, "第1集")
    obj = ni.load_shot_intent(root, "第1集")
    assert obj.get("storyboard_sha")
    obj["allowed_evolution"] = [
        {"character": "沈念", "from_shot": 1, "to_shot": 1, "field": "face", "desc": "易容", "source": "author"}]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    assert ni.blackboard_is_stale(root, "第1集") is False
    # 镜数不变（仍 1 镜），但内容改写 → 指纹失配 → 陈旧
    _write_sb(tmp_path, [{"id": "Clip_01", "description": "他坐在床上", "continuity": {}}])
    assert ni.blackboard_is_stale(root, "第1集") is True
    assert ni.explicit_evolution_for(root, "第1集", "face") == {}


def test_old_blackboard_without_sha_falls_back_to_clip_count(tmp_path):
    # 旧黑板无 storyboard_sha：回退镜数比对（向后兼容）。
    root = _write_sb(tmp_path, [{"id": "Clip_01", "continuity": {}}])
    ni.write_shot_intent(root, "第1集")
    path = ni.shot_intent_path(root, "第1集")
    obj = ni.load_shot_intent(root, "第1集")
    obj.pop("storyboard_sha", None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    assert ni.blackboard_is_stale(root, "第1集") is False  # 1 镜 == 1 镜
    _write_sb(tmp_path, [{"id": f"Clip_{i:02d}", "continuity": {}} for i in range(1, 3)])
    assert ni.blackboard_is_stale(root, "第1集") is True   # 1 != 2


def test_handoff_ignores_blackboard_derived_field_edits(tmp_path):
    # expression_span/need_endframe 是 storyboard 派生投影，不允许手改黑板覆盖生成/交接契约。
    import n2d_handoff as hf
    ep = "第1集"
    ep_dir = os.path.join(str(tmp_path), "脚本", ep)
    os.makedirs(ep_dir)
    # storyboard：Clip1 cont 无 need_endframe、expression_span=中
    with open(os.path.join(ep_dir, "storyboard.json"), "w", encoding="utf-8") as f:
        json.dump({"clips": [{"id": "Clip_01", "description": "近景特写",
                              "continuity": {"expression_span": "中"}}]}, f, ensure_ascii=False)
    # 无黑板：本地派生 need_endframe=False, expression_span=中
    base = hf._storyboard_clip_meta(str(tmp_path), ep)
    assert base[1]["need_endframe"] is False and base[1]["expression_span"] == "中"
    # 手改黑板派生字段：应被忽略，真正要改必须回 storyboard。
    ni.write_shot_intent(str(tmp_path), ep)
    obj = ni.load_shot_intent(str(tmp_path), ep)
    obj["shots"][0]["expression_span"] = "大"
    obj["shots"][0]["need_endframe"] = True
    with open(ni.shot_intent_path(str(tmp_path), ep), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    after = hf._storyboard_clip_meta(str(tmp_path), ep)
    assert after[1]["expression_span"] == "中"
    assert after[1]["need_endframe"] is False
    # closeup/action_beat 仍走本地（更丰富）派生
    assert after[1]["closeup"] is True


def test_handoff_ignores_blackboard_motion_intensity_edits(tmp_path):
    # motion_intensity 同样以 storyboard 为真值源；手改黑板不能让 action_beat 升格。
    import n2d_handoff as hf
    ep = "第1集"
    ep_dir = os.path.join(str(tmp_path), "脚本", ep)
    os.makedirs(ep_dir)
    # storyboard：中性描述、无 action 关键词、cont 无 motion → action_beat=False
    with open(os.path.join(ep_dir, "storyboard.json"), "w", encoding="utf-8") as f:
        json.dump({"clips": [{"id": "Clip_01", "description": "他站着说话", "continuity": {}}]},
                  f, ensure_ascii=False)
    base = hf._storyboard_clip_meta(str(tmp_path), ep)
    assert base[1]["action_beat"] is False
    # 手改黑板 motion_intensity=高
    ni.write_shot_intent(str(tmp_path), ep)
    obj = ni.load_shot_intent(str(tmp_path), ep)
    obj["shots"][0]["motion_intensity"] = "高"
    with open(ni.shot_intent_path(str(tmp_path), ep), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    after = hf._storyboard_clip_meta(str(tmp_path), ep)
    assert after[1]["motion_intensity"] == ""
    assert after[1]["action_beat"] is False
