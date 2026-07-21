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


def test_structured_medium_expression_overrides_story_function_heuristic():
    d = rp.variation_deltas("他从恐惧转为主动隐瞒", "turning_point")
    assert "strong_emotion" in d
    adjusted = rp.apply_structured_expression_intensity(d, "medium")
    assert "strong_emotion" not in adjusted


def test_explicit_panel_strong_overrides_structured_medium_expression():
    d = rp.variation_deltas("他压低声音", "turning_point")
    adjusted = rp.apply_structured_expression_intensity(d, "medium", explicit_panel_strong=True)
    assert "strong_emotion" in adjusted


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
    assert any("强情绪格缺对应表情参考" in m for m in plan["missing_references"])


def test_back_emotion_shot_keeps_back_and_expression_before_optional_views():
    char = _char(
        panel_expression_id="EXPR_STUNNED",
        expression_refs={"EXPR_STUNNED": "expr.png"},
        expression_emotions={"EXPR_STUNNED": "stunned"},
    )
    plan = rp.plan_character_in_panel(
        char,
        ["back_or_over_shoulder", "strong_emotion"],
        multi=True,
        caps={**CAPS_WEAK, "multi_character_reference_limit": 4},
        scope_is_core=True,
    )
    roles = [item["role"] for item in plan["recommended_references"]]
    assert roles == ["front", "face", "expression", "back"]
    assert not any("参考预算溢出" in item for item in plan["missing_references"])


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


def test_monster_placeholder_outfit_does_not_create_clothing_gap():
    c = _char(cid="MON_TIGER", panel_outfit_id="OUTFIT_BASE", asset_type="monster")
    plan = rp.plan_character_in_panel(c, [], False, CAPS_WEAK, True)
    assert not any("服装参考图" in m for m in plan["missing_references"])


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


def test_structured_binding_is_required_and_unknown_state_blocks():
    chars = {
        "CHAR_A": {
            "forms": {"FORM_BASE": {}}, "outfits": {"OUTFIT_BASE": {}},
            "expressions": {"EXPR_NEUTRAL": {}}, "states": {"STATE_BASE": {"form_id": "FORM_BASE", "outfit_id": "OUTFIT_BASE", "expression_id": "EXPR_NEUTRAL"}},
        }
    }
    _bindings, findings = rp.validate_panel_bindings({"panel_id": "P1", "characters": ["阿甲", "CHAR_A"]}, chars)
    codes = {item["code"] for item in findings}
    assert "named_character_without_stable_id" in codes
    assert "missing_structured_character_binding" in codes

    panel = {"panel_id": "P2", "character_bindings": [{
        "character_id": "CHAR_A", "form_id": "FORM_BASE", "outfit_id": "OUTFIT_BASE",
        "expression_id": "EXPR_NEUTRAL", "state_id": "STATE_UNKNOWN",
    }]}
    _bindings, findings = rp.validate_panel_bindings(panel, chars)
    assert any(item["code"] == "character_binding_state_id_unknown" for item in findings)


def test_attachment_allocation_is_fair_and_keeps_location_and_prop(tmp_path):
    paths = {}
    for name in ("a-front", "a-face", "b-front", "b-face", "loc", "prop"):
        path = tmp_path / f"{name}.png"
        path.write_bytes(name.encode())
        paths[name] = path.name
    char_plans = [
        {"char_id": "CHAR_A", "recommended_references": [{"role": "front", "path": paths["a-front"]}, {"role": "face", "path": paths["a-face"]}]},
        {"char_id": "CHAR_B", "recommended_references": [{"role": "front", "path": paths["b-front"]}, {"role": "face", "path": paths["b-face"]}]},
    ]
    registry = {"assets": {
        "LOC_ROOM": {"anchor_path": paths["loc"]},
        "PROP_KEY": {"anchor_path": paths["prop"]},
    }}
    panel = {"references": ["LOC_ROOM", "PROP_KEY"]}
    caps = {"adapter_id": "openai_gpt_image_project_memory", "reference_image_limit": 16, "executable_attachment_limit": 5}
    result = rp.allocate_panel_attachments(tmp_path, panel, char_plans, registry, caps)
    selected_ids = [item["id"] for item in result["selected"]]
    assert result["limit"] == 5
    assert {"CHAR_A", "CHAR_B", "LOC_ROOM", "PROP_KEY"} <= set(selected_ids)
    assert selected_ids.index("CHAR_A") != selected_ids.index("CHAR_B")


def test_critical_reference_budget_overflow_requests_split(tmp_path):
    char_plans = []
    for index in range(4):
        path = tmp_path / f"c{index}.png"
        path.write_bytes(b"x")
        char_plans.append({"char_id": f"CHAR_{index}", "recommended_references": [{"role": "front", "path": path.name}]})
    loc = tmp_path / "loc.png"
    prop = tmp_path / "prop.png"
    loc.write_bytes(b"l")
    prop.write_bytes(b"p")
    registry = {"assets": {"LOC_A": {"anchor_path": loc.name}, "PROP_A": {"anchor_path": prop.name}}}
    result = rp.allocate_panel_attachments(tmp_path, {"references": ["LOC_A", "PROP_A"]}, char_plans, registry,
                                           {"adapter_id": "openai_gpt_image_project_memory", "reference_image_limit": 16, "executable_attachment_limit": 5})
    assert result["over_capacity"] is True
    assert "拆成单人反打" in result["split_suggestion"]


def test_end_to_end_build_plan(tmp_path):
    root = tmp_path
    (root / "脚本" / "第1话").mkdir(parents=True)
    (root / "出图" / "共享").mkdir(parents=True)
    bindings = [
        {"character_id": cid, "form_id": "FORM_BASE", "outfit_id": "OUTFIT_BASE", "expression_id": "EXPR_ANGRY", "state_id": "STATE_ANGRY"}
        for cid in ("CHAR_A", "CHAR_B")
    ]
    (root / "脚本" / "第1话" / "panel_script.json").write_text(json.dumps({"panels": [
        {"panel_id": "P001", "characters": ["CHAR_A", "CHAR_B"], "references": ["CHAR_A", "CHAR_B"],
         "character_bindings": bindings, "description": "两人近景对峙，怒目"},
    ]}, ensure_ascii=False), encoding="utf-8")
    image_dir = root / "出图" / "共享" / "图片"
    image_dir.mkdir(parents=True)
    assets = {}
    for cid, dna in (("CHAR_A", "红衣黑发"), ("CHAR_B", "赤袍")):
        views = {}
        for view in FULL_VIEWS:
            path = image_dir / f"{cid}__{view}.png"
            path.write_bytes(f"{cid}-{view}".encode())
            views[view] = str(path.relative_to(root))
        expression_path = image_dir / f"{cid}__angry.png"
        expression_path.write_bytes(f"{cid}-angry".encode())
        assets[cid] = {
            "id": cid, "type": "character", "display_name": cid, "scope": "主角" if cid == "CHAR_A" else "配角",
            "character_dna": dna, "views": views,
            "forms": {"FORM_BASE": {"id": "FORM_BASE", "name": "常态", "reference_images": [views["front"]]}},
            "outfits": {"OUTFIT_BASE": {"id": "OUTFIT_BASE", "name": "基础服装", "reference_images": [views["front"]]}},
            "expressions": {"EXPR_ANGRY": {"id": "EXPR_ANGRY", "name": "愤怒", "emotion": "anger", "reference_images": [str(expression_path.relative_to(root))]}},
            "states": {"STATE_ANGRY": {"id": "STATE_ANGRY", "form_id": "FORM_BASE", "outfit_id": "OUTFIT_BASE", "expression_id": "EXPR_ANGRY"}},
        }
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({"schema_version": 2, "kind": "comic_identity_registry", "assets": assets}, ensure_ascii=False), encoding="utf-8")
    report = rp.build_plan(root, "第1话")
    assert report["summary"]["panels_with_characters"] == 1
    codes = {f["code"] for f in report["findings"]}
    assert "multi_character_closeup" in codes            # 近景多人
    assert "same_frame_color_collision" in codes         # 红↔赤 撞色
