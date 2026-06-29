"""object_state_continuity (OST) 纯函数 + 编排单测。
cd skills/n2d-review/scripts && python -m pytest test_object_state_continuity.py
"""
import json
import os
import object_state_continuity as ost


def test_prop_tokens_strips_prefix_and_shorts():
    toks = ost.prop_tokens("PROP_青瓷茶盏", "青瓷茶盏")
    assert "青瓷茶盏" in toks
    assert all(len(t) >= 2 for t in toks)


def test_state_hit_returns_first_synonym():
    assert ost.state_hit("案上茶盏已空见底", ("空", "见底")) == "空"
    assert ost.state_hit("案上茶盏盛满热茶", ("空", "见底")) is None


def test_declared_pair_transition_exempts():
    tl = [{"clip": 5, "from": "满", "to": "空"}]
    assert ost.declared_pair_transition(tl, ("满",), ("空",)) is True
    assert ost.declared_pair_transition([], ("满",), ("空",)) is False


def test_conflicts_for_prop_flags_undeclared_flip():
    clip_texts = [
        ("Clip_03", "案上青瓷茶盏盛满热茶"),
        ("Clip_07", "青瓷茶盏空了见底"),
    ]
    tokens = {"青瓷茶盏"}
    out = ost.conflicts_for_prop(clip_texts, tokens, timeline=[])
    assert len(out) == 1 and out[0]["pair"] == ("满", "空")
    assert out[0]["a_clip"] == "Clip_03" and out[0]["b_clip"] == "Clip_07"


def test_conflicts_for_prop_exempts_declared():
    clip_texts = [("Clip_03", "茶盏盛满"), ("Clip_07", "茶盏空了")]
    tl = [{"clip": 5, "from": "满", "to": "空"}]
    assert ost.conflicts_for_prop(clip_texts, {"茶盏"}, tl) == []


def test_analyze_end_to_end(tmp_path):
    root = str(tmp_path)
    shared = os.path.join(root, "出图", "共享")
    epd = os.path.join(root, "脚本", "第1集")
    os.makedirs(shared); os.makedirs(epd)
    json.dump({"kind": "n2d_visual_state_ledger", "props": {
        "PROP_烛台": {"name": "烛台", "timeline": []}
    }}, open(os.path.join(shared, "visual_state_ledger.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"clips": [
        {"id": "Clip_01", "shots": [{"desc": "烛台烛火通明，映亮书案"}]},
        {"id": "Clip_02", "shots": [{"desc": "烛台早已熄灭，屋内漆黑"}]},
    ]}, open(os.path.join(epd, "storyboard.json"), "w", encoding="utf-8"), ensure_ascii=False)
    rep = ost.analyze(root, "第1集")
    assert rep["available"]
    assert any("烛台" in s["message"] and s["verdict"] == "warn" for s in rep["shots"])


def test_analyze_skips_without_props(tmp_path):
    assert ost.analyze(str(tmp_path), "第1集")["available"] is False


def test_physics_irreversible_reversion_flagged_and_restore_exempt():
    import object_state_continuity as ost
    tokens = {"青玉佩", "玉佩"}
    # 碎后无解释又完好 → 物理不可逆穿帮
    flip = [("Clip1", "青玉佩 完好"), ("Clip2", "青玉佩 摔碎 在地"), ("Clip3", "青玉佩 完好如初 泛光")]
    c = ost.conflicts_for_prop(flip, tokens, [])
    assert any(x.get("physics_violation") and x["pair"] == ("完好", "破损") for x in c)
    # 写明重铸修复 → 豁免（合法复原）
    repaired = [("Clip1", "青玉佩 完好"), ("Clip2", "青玉佩 摔碎"), ("Clip3", "工匠 重铸 修复 青玉佩 完好")]
    assert not any(x.get("physics_violation") for x in ost.conflicts_for_prop(repaired, tokens, []))
    # 闪回倒叙 → 豁免（后镜是更早时间）
    flashback = [("Clip1", "玉佩 摔碎"), ("Clip2", "闪回 当年 玉佩 完好")]
    assert not any(x.get("physics_violation") for x in ost.conflicts_for_prop(flashback, tokens, []))


def test_reversible_pairs_not_flagged_as_physics():
    import object_state_continuity as ost
    # 满↔空 可再斟满 → 即便跨镜翻转，也只是普通未声明 warn，绝不标 physics_violation
    cups = [("Clip1", "酒壶 倒满"), ("Clip2", "酒壶 空了")]
    c = ost.conflicts_for_prop(cups, {"酒壶"}, [])
    assert c and not any(x.get("physics_violation") for x in c)
