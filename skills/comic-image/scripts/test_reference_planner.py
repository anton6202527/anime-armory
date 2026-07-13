"""reference_planner 单测。运行：cd skills/comic-image/scripts && python -m pytest test_reference_planner.py"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("reference_planner.py")
spec = importlib.util.spec_from_file_location("reference_planner", SCRIPT)
rp = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(rp)

CAPS_WEAK = {"adapter_id": "openai_gpt_image_project_memory", "persistent_subject": False,
             "single_character_reference_limit": 5, "multi_character_reference_limit": 3}
CAPS_TINY = {"adapter_id": "dreamina_image2image", "persistent_subject": False,
             "single_character_reference_limit": 2, "multi_character_reference_limit": 2}
CAPS_NATIVE = {"adapter_id": "native_subject_capable", "persistent_subject": True,
               "single_character_reference_limit": 4, "multi_character_reference_limit": 3}

FULL_VIEWS = {"face": "f.png", "front": "fr.png", "three_quarter": "tq.png",
              "side": "s.png", "back": "b.png"}


def _char(cid="CHAR_A", views=None, tier="core_full", scope="主角", dna="黑发红衣", **extra):
    c = {"id": cid, "display_name": cid, "tier": tier, "scope": scope,
         "views": dict(views if views is not None else FULL_VIEWS),
         "outfit_ids": set(), "outfit_refs": {}, "dna": dna}
    c.update(extra)
    return c


def test_deltas_detect_closeup_and_emotion():
    d = rp.variation_deltas("面部特写，她眼里含着泪")
    assert "closeup" in d and "strong_emotion" in d


def test_deltas_action_sets_eyeline_lock():
    d = rp.variation_deltas("激烈打斗，长剑劈向对手")
    assert "action_eyeline_lock" in d


def test_full_views_no_missing():
    plan = rp.plan_character_in_panel(_char(), [], multi=False, caps=CAPS_WEAK, scope_is_core=True)
    assert plan["missing_references"] == []
    roles = {r["role"] for r in plan["recommended_references"]}
    assert {"front", "face", "three_quarter"} <= roles


def test_missing_front_flagged():
    plan = rp.plan_character_in_panel(_char(views={"face": "f.png"}), [], False, CAPS_WEAK, True)
    assert any("front" in m or "正面" in m for m in plan["missing_references"])


def test_strong_emotion_wants_expression_bank():
    plan = rp.plan_character_in_panel(_char(), ["strong_emotion"], False, CAPS_WEAK, True)
    assert any("情绪表情库" in m for m in plan["missing_references"])


def test_action_promotes_three_quarter_and_writes_directive():
    plan = rp.plan_character_in_panel(_char(), ["action_eyeline_lock"], False, CAPS_WEAK, True)
    assert plan["pose_gaze_directive"]
    tq = next(r for r in plan["recommended_references"] if r["role"] == "three_quarter")
    fr = next(r for r in plan["recommended_references"] if r["role"] == "front")
    assert tq["strength_hint"] >= 0.78 and fr["strength_hint"] <= 0.55


def test_budget_cap_drops_and_records():
    plan = rp.plan_character_in_panel(_char(), ["extreme_angle", "back_or_over_shoulder"],
                                      False, CAPS_TINY, True)
    assert plan["reference_budget"]["limit"] == 2
    assert plan["reference_budget"]["selected"] == 2
    assert plan["reference_budget"]["dropped"] >= 1
    assert any("参考预算溢出" in m for m in plan["missing_references"])


def test_escalation_for_weak_core_big_delta():
    plan = rp.plan_character_in_panel(_char(scope="主角"), ["closeup"], False, CAPS_WEAK, True)
    assert plan["escalation"]
    # native subject backend should not escalate
    plan2 = rp.plan_character_in_panel(_char(), ["closeup"], False, CAPS_NATIVE, True)
    assert plan2["escalation"] is None


def test_memory_anchor_prepended_highest_priority():
    plan = rp.plan_character_in_panel(_char(), [], False, CAPS_WEAK, True, memory_refs=["mem.png"])
    assert plan["recommended_references"][0]["role"] == "memory_anchor"
    assert plan["memory_anchor_reinjected"] is True


def test_outfit_change_missing_reference_flagged():
    c = _char(panel_outfit_id="OUTFIT_RED")
    plan = rp.plan_character_in_panel(c, [], False, CAPS_WEAK, True)
    assert any("服装参考图" in m for m in plan["missing_references"])


def test_named_minimal_tier_skips_three_quarter_when_static():
    plan = rp.plan_character_in_panel(_char(tier="named_minimal"), [], False, CAPS_WEAK, False)
    roles = {r["role"] for r in plan["recommended_references"]}
    assert "three_quarter" not in roles
    assert "45°/three_quarter 参考（档位或本格变化量需要）" not in plan["missing_references"]


def test_multi_subject_color_collision():
    plans = [{"char_id": "CHAR_A"}, {"char_id": "CHAR_B"}]
    dna = {"CHAR_A": "一身红衣", "CHAR_B": "赤色长袍"}
    mp = rp.plan_multi_subject(plans, CAPS_WEAK, dna, closeup=False)
    assert mp and mp["color_collisions"]


def test_multi_subject_native_mode():
    plans = [{"char_id": "CHAR_A"}, {"char_id": "CHAR_B"}]
    mp = rp.plan_multi_subject(plans, CAPS_NATIVE, {"CHAR_A": "黑", "CHAR_B": "白"}, closeup=False)
    assert mp["mode"] == "native_subject_slots"
    assert mp["color_collisions"] == []


def test_end_to_end_build_plan(tmp_path):
    root = tmp_path
    (root / "脚本" / "第1话").mkdir(parents=True)
    (root / "出图" / "共享").mkdir(parents=True)
    (root / "脚本" / "第1话" / "panel_script.json").write_text(json.dumps({"panels": [
        {"panel_id": "P001", "references": ["CHAR_A", "CHAR_B"], "description": "两人近景对峙，怒目"},
    ]}, ensure_ascii=False), encoding="utf-8")
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({"assets": {
        "CHAR_A": {"id": "CHAR_A", "display_name": "甲", "scope": "主角",
                   "character_dna": "红衣黑发", "views": FULL_VIEWS},
        "CHAR_B": {"id": "CHAR_B", "display_name": "乙", "scope": "配角",
                   "character_dna": "赤袍", "views": FULL_VIEWS},
    }}, ensure_ascii=False), encoding="utf-8")
    report = rp.build_plan(root, "第1话")
    assert report["summary"]["panels_with_characters"] == 1
    codes = {f["code"] for f in report["findings"]}
    assert "multi_character_closeup" in codes            # 近景多人
    assert "same_frame_color_collision" in codes         # 红↔赤 撞色
