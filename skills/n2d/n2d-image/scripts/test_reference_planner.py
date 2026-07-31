"""reference_planner 单测——逐镜 delta + 后端能力路由 + 升档 + 端到端 build_plan。

cd skills/n2d/n2d-image/scripts && python3 -m pytest test_reference_planner.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("reference_planner.py")
spec = importlib.util.spec_from_file_location("reference_planner", SCRIPT)
rp = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(rp)


# ── 纯函数 ─────────────────────────────────────────────────────────────────────

def test_variation_deltas() -> None:
    ap = {"risky": ["deep_shadow", "extreme_low"]}
    assert "closeup" in rp.variation_deltas("CU 85mm", "", ap)
    assert "strong_emotion" in rp.variation_deltas("", "她崩溃落泪", ap)
    assert "extreme_angle:deep_shadow" in rp.variation_deltas("", "逆光剪影", ap)
    assert rp.variation_deltas("LS 35mm", "平静地走过", {"risky": []}) == []


def test_variation_deltas_structured_fields() -> None:
    # 新 schema：结构化 shot_size/expression_span 直接驱动，不靠 NLP 文本。
    d = rp.variation_deltas("", "", {"risky": ["extreme_low"]},
                            shot_size="沈念面部特写(ECU)", expression_span="大")
    assert "closeup" in d and "strong_emotion" in d
    # expression_span=中 不算大表情
    assert "strong_emotion" not in rp.variation_deltas("", "", {}, shot_size="中景", expression_span="中")


def test_is_action_eyeline_shot() -> None:
    assert rp.is_action_eyeline_shot("fight_exchange 拆招")
    assert rp.is_action_eyeline_shot("姜月初挥戟斩向对手·命中")
    assert rp.is_action_eyeline_shot("magic_burst 法术爆发")
    assert not rp.is_action_eyeline_shot("两人静坐对话，中景")


def test_variation_deltas_action_eyeline_lock() -> None:
    # 动作镜 → action_eyeline_lock；显式 POV/破第四墙镜豁免（允许直视镜头）。
    assert "action_eyeline_lock" in rp.variation_deltas("", "打斗·斜劈·命中", {})
    assert "action_eyeline_lock" in rp.variation_deltas("fight_exchange", "拆招", {})
    assert "action_eyeline_lock" not in rp.variation_deltas("", "两人对坐品茶", {})
    # opponent POV / 破第四墙 → 豁免（即便有打斗词）
    assert "action_eyeline_lock" not in rp.variation_deltas("", "打斗·命中·opponent POV", {})
    assert "action_eyeline_lock" not in rp.variation_deltas("", "拆招·破第四墙直视镜头=导演意图", {})


def test_action_eyeline_lock_promotes_threequarter_and_emits_directive() -> None:
    # 动作镜：¾ 提为主身份锚（strength≥0.78、排在 front 前）、front 降权、开视线指令。
    p = rp.plan_character_in_clip(
        _char(), deltas=["action_eyeline_lock"], multi=False,
        profile=_MULTI_REF, tier="multi_reference", scope_is_core=True,
    )
    refs = p["recommended_references"]
    roles = [r["role"] for r in refs]
    tq = next(r for r in refs if r["role"] == "three_quarter")
    fr = next(r for r in refs if r["role"] == "front")
    assert tq["strength_hint"] >= 0.78 and fr["strength_hint"] <= 0.55
    assert roles.index("three_quarter") < roles.index("front")  # ¾ 排在 front 之前
    assert p["pose_gaze_directive"] and "不直视镜头" in p["pose_gaze_directive"]
    assert any("视线锁定" in s for s in p["prompt_required"])


def test_action_eyeline_lock_flags_missing_threequarter() -> None:
    rg = dict(_RG)
    rg.pop("three_quarter", None)
    p = rp.plan_character_in_clip(
        _char(rg=rg), deltas=["action_eyeline_lock"], multi=False,
        profile=_MULTI_REF, tier="multi_reference", scope_is_core=False,
    )
    assert any("¾" in m or "three_quarter" in m for m in p["missing_references"])
    assert p["pose_gaze_directive"]  # 仍开指令（缺 ¾ 时更要补拍）


def test_non_action_shot_no_directive() -> None:
    p = rp.plan_character_in_clip(
        _char(), deltas=["closeup"], multi=False,
        profile=_MULTI_REF, tier="multi_reference", scope_is_core=True,
    )
    assert p["pose_gaze_directive"] is None and p["prompt_required"] == []


def test_named_minimal_only_requires_threequarter_when_shot_needs_it() -> None:
    rg = {
        "front": _RG["front"],
        "outfit": _RG["outfit"],
        "face_anchor_refs": _RG["face_anchor_refs"],
        "expressions": _RG["expressions"],
    }
    char = {
        **_char(rg=rg, ap={"risky": [], "requires_extra_reference": []}),
        "reference_atlas": {
            "build_tier": "named_minimal",
            "base_views": {"front": {"path": _RG["front"], "status": "ready"}},
            "face_anchor_refs": [{"path": _RG["face_anchor_refs"][0], "status": "ready"}],
        },
    }
    ordinary = rp.plan_character_in_clip(
        char, deltas=[], multi=False, profile=_MULTI_REF,
        tier="multi_reference", scope_is_core=False,
    )
    assert ordinary["library_tier"] == "named_minimal"
    assert not any("three_quarter" in m or "45°" in m for m in ordinary["missing_references"])
    assert "three_quarter" not in {r["role"] for r in ordinary["recommended_references"]}

    closeup = rp.plan_character_in_clip(
        char, deltas=["closeup"], multi=False, profile=_MULTI_REF,
        tier="multi_reference", scope_is_core=False,
    )
    assert any("three_quarter" in m or "45°" in m for m in closeup["missing_references"])


def test_parse_clip_new_schema() -> None:
    clip = {
        "id": "Clip_02", "description": "枯枝指阴狠开口威胁",
        "character_ids": ["CHAR_08", "CHAR_06"],
        "shots": [1],  # 新 schema 的 shots 是 int 列表，不能当 dict
        "template_contract": {"camera_rule": "略仰机位推向枯枝指",
                              "character_slots": {"居中": "CHAR_08 枯枝指"}},
        "continuity": {"shot_size": "枯枝指中近景", "expression_span": "大"},
    }
    parsed = rp.parse_clip(clip)
    assert parsed["character_ids"] == ["CHAR_08", "CHAR_06"]
    assert parsed["shot_size"] == "枯枝指中近景" and parsed["expression_span"] == "大"
    assert "枯枝指" in parsed["text"] and "略仰机位" in parsed["text"]


def test_parse_clip_uses_entity_schedule_visible_characters() -> None:
    clip = {
        "id": "Clip_03",
        "character_ids": ["CHAR_01", "CHAR_02"],
        "entity_schedule": {
            "characters": ["CHAR_01"],
            "offscreen_presence": ["CHAR_02"],
            "forbidden_presence": [],
        },
        "continuity": {"shot_size": "CU"},
    }

    parsed = rp.parse_clip(clip)

    assert parsed["character_ids"] == ["CHAR_01"]


def test_parse_clip_template_contract_string() -> None:
    clip = {
        "id": "Clip_02",
        "description": "姜月初挥戟斩向李乾元",
        "character_ids": ["CHAR_JIANG_YUECHU", "CHAR_LI_QIANYUAN"],
        "template_contract": "fight_exchange",
        "continuity": {"shot_size": "中景", "expression_span": "中"},
    }
    parsed = rp.parse_clip(clip)
    assert parsed["character_ids"] == ["CHAR_JIANG_YUECHU", "CHAR_LI_QIANYUAN"]
    assert "fight_exchange" in parsed["text"]
    assert "姜月初" in parsed["text"]


def test_parse_clip_project_schema_characters_and_clip_id_text() -> None:
    clip = {
        "clip": "Clip_11",
        "scene": "益州上空",
        "characters": ["CHAR_JIANG_YUECHU/燃灯双灯态", "CHAR_YUNLING_DASHENG"],
        "action": "姜月初双心灯燃起，云翎大圣跪伏。",
        "camera": "low angle closeup",
        "template_contract": "breakthrough_reveal",
    }
    parsed = rp.parse_clip(clip)
    assert parsed["character_ids"] == ["CHAR_JIANG_YUECHU", "CHAR_YUNLING_DASHENG"]
    assert "Clip_11" in parsed["text"]
    assert "燃灯双灯态" in parsed["text"]
    assert "breakthrough_reveal" in parsed["text"]


def test_pick_form_prefers_form_name_in_clip_text() -> None:
    char = {
        "forms": [
            {"form": "玄衣战斗态", "asset_key": ""},
            {"form": "燃灯双灯态", "asset_key": ""},
        ]
    }
    picked = rp._pick_form(char, "CHAR_JIANG_YUECHU/燃灯双灯态 双心灯燃起")
    assert picked["form"] == "燃灯双灯态"


def test_clip_present_prefers_character_ids() -> None:
    chars = [{"id": "CHAR_08", "name": "小妖B", "aliases": {"枯枝指"}},
             {"id": "CHAR_99", "name": "路人", "aliases": {"路人"}}]
    # 有 character_ids → 按 id 精确匹配（即使别名也在文本里出现路人）
    present = rp.clip_present({"character_ids": ["CHAR_08"], "text": "路人 枯枝指"}, chars)
    assert [c["id"] for c in present] == ["CHAR_08"]
    # 无 character_ids → 退回别名
    present2 = rp.clip_present({"character_ids": [], "text": "路人路过"}, chars)
    assert [c["id"] for c in present2] == ["CHAR_99"]


def test_is_emotion_bank() -> None:
    assert not rp._is_emotion_bank(["定妆_x_脸部特写.png"])  # 仅中性特写
    assert rp._is_emotion_bank(["a_脸部特写.png", "b.png"])   # ≥2 张
    assert rp._is_emotion_bank(["定妆_x_表情_怒.png"])         # 情绪命名


_RG = {
    "front": "出图/共享/图片/定妆_x.png",
    "three_quarter": "出图/共享/图片/定妆_x_45度.png",
    "side": "出图/共享/图片/定妆_x_侧.png",
    "back": "出图/共享/图片/定妆_x_背.png",
    "outfit": "出图/共享/图片/定妆_x_半身.png",
    "turnaround": "出图/共享/图片/定妆_x_三视图.png",
    "face_anchor_refs": ["出图/共享/图片/定妆_x_脸部特写.png"],
    "expressions": ["出图/共享/图片/定妆_x_脸部特写.png"],  # 仅中性
}
_AP = {"risky": ["deep_shadow", "extreme_low", "face_too_small"],
       "requires_extra_reference": ["side", "back"]}
_MULTI_REF = {"label": "Codex", "canonical": "codex", "multi_reference": True,
              "max_reference_images": None}


def _char(rg=_RG, ap=_AP):
    return {"id": "CHAR_01", "name": "女主", "form": "常态", "reference_group": rg, "angle_policy": ap}


def test_multi_reference_closeup_emotion_flags_missing_bank_and_escalates() -> None:
    p = rp.plan_character_in_clip(
        _char(), deltas=["closeup", "strong_emotion"], multi=False,
        profile=_MULTI_REF, tier="multi_reference", scope_is_core=True,
    )
    roles = [r["role"] for r in p["recommended_references"]]
    assert "front" in roles and "three_quarter" in roles and "face_anchor" in roles and "expression" in roles
    assert any("情绪表情库" in m for m in p["missing_references"])  # 仅中性特写 → 缺情绪库
    assert p["escalation"] and p["needs_action"]


def test_character_plan_requires_baseline_three_quarter_and_face_anchor() -> None:
    rg = dict(_RG)
    rg.pop("three_quarter", None)
    rg.pop("face_anchor_refs", None)
    rg["expressions"] = []
    char = {**_char(rg=rg), "library_tier": "recurring_standard"}
    p = rp.plan_character_in_clip(
        char, deltas=[], multi=False,
        profile=_MULTI_REF, tier="multi_reference", scope_is_core=False,
    )
    assert any("45" in m or "three_quarter" in m for m in p["missing_references"])
    assert any("脸部特写" in m for m in p["missing_references"])
    assert p["needs_action"]


def test_multi_character_adds_controlnet() -> None:
    p = rp.plan_character_in_clip(
        _char(), deltas=[], multi=True,
        profile=_MULTI_REF, tier="multi_reference", scope_is_core=False,
    )
    assert p["controlnet"] == ["pose", "depth"]


def test_native_unregistered_prescribes_diverse_registration() -> None:
    profile = {"label": "Seedream Universal Reference", "canonical": "seedream",
               "multi_reference": True, "max_reference_images": 14,
               "recommended_diverse_reference_min": 8}
    p = rp.plan_character_in_clip(
        _char(), deltas=["closeup"], multi=False,
        profile=profile, tier="native_unregistered", scope_is_core=True,
    )
    assert p["native_subject_action"] and "多样参考" in p["native_subject_action"]
    assert "8" in p["native_subject_action"]
    assert p["needs_action"]


def test_native_subject_no_escalation() -> None:
    profile = {"label": "可灵主体库", "canonical": "kling", "multi_reference": True,
               "max_reference_images": None}
    p = rp.plan_character_in_clip(
        _char(), deltas=["closeup", "strong_emotion"], multi=True,
        profile=profile, tier="native_subject", scope_is_core=True,
    )
    assert p["escalation"] is None  # 已注册主体不再升档
    assert p["native_subject_action"] and "引用" in p["native_subject_action"]


def test_lora_tier_no_escalation() -> None:
    p = rp.plan_character_in_clip(
        _char(), deltas=["closeup", "strong_emotion"], multi=True,
        profile=_MULTI_REF, tier="lora", scope_is_core=True,
    )
    assert p["escalation"] is None  # 最强档，不再建议升档


def test_max_reference_cap_respected() -> None:
    profile = {"label": "Seedream", "canonical": "seedream", "multi_reference": True,
               "max_reference_images": 2}
    p = rp.plan_character_in_clip(
        _char(), deltas=["closeup"], multi=False,
        profile=profile, tier="multi_reference", scope_is_core=False,
    )
    assert len(p["recommended_references"]) <= 2
    assert p["reference_budget"]["limit"] == 2
    assert p["reference_budget"]["dropped"] >= 1
    assert p["dropped_references"]
    assert any("参考预算溢出" in m for m in p["missing_references"])


def test_shortline_no_escalation() -> None:
    p = rp.plan_character_in_clip(
        _char(), deltas=["closeup", "strong_emotion"], multi=True,
        profile=_MULTI_REF, tier="multi_reference", scope_is_core=False,
    )
    assert p["escalation"] is None  # 短线角不前置升档（ROI 最小化）


def test_multi_subject_strategy_requires_split_for_codex_like_backend() -> None:
    chars = [
        {"char_id": "CHAR_01", "form": "常态", "tier": "multi_reference"},
        {"char_id": "CHAR_02", "form": "常服", "tier": "multi_reference"},
    ]
    strategy = rp.plan_multi_subject_strategy(chars, _MULTI_REF)
    assert strategy
    assert strategy["mode"] == "regional_construct_required"
    assert "多人同框身份槽位" in strategy["required_prompt_fields"]
    assert "空场景底板 empty_plate" in strategy["required_prompt_fields"]
    assert "区域遮罩/region masks" in strategy["required_prompt_fields"]
    assert "硬执行" in strategy["execution"]
    assert [s["slot"] for s in strategy["slots"]] == ["LEFT_SLOT", "RIGHT_SLOT"]


def test_distinct_anchors_collision_when_same_palette() -> None:
    dna = {
        "CHAR_01": {"hair": "乌黑长发", "outfit": "绛红长袍"},
        "CHAR_02": {"hair": "黑发束冠", "outfit": "朱红劲装"},
    }
    out = rp.plan_distinct_anchors(dna, ["CHAR_01", "CHAR_02"])
    assert out["collision"] is True
    assert out["collisions"] and "红" in out["collisions"][0]["layer"]


def test_distinct_anchors_no_collision_when_palettes_differ() -> None:
    dna = {
        "CHAR_01": {"hair": "乌黑长发", "outfit": "月白宫装"},
        "CHAR_02": {"hair": "金发", "outfit": "玄黑战甲"},
    }
    out = rp.plan_distinct_anchors(dna, ["CHAR_01", "CHAR_02"])
    assert out["collision"] is False


def test_multi_subject_strategy_adds_distinct_anchor_field_and_scheduling() -> None:
    chars = [
        {"char_id": "CHAR_01", "form": "常态", "tier": "multi_reference"},
        {"char_id": "CHAR_02", "form": "常服", "tier": "multi_reference"},
    ]
    dna = {"CHAR_01": {"hair": "乌黑", "outfit": "红衣"},
           "CHAR_02": {"hair": "乌黑", "outfit": "绛红"}}
    strategy = rp.plan_multi_subject_strategy(chars, _MULTI_REF, dna_by_id=dna, closeup=True)
    assert "区分锚点（互斥发色/服装主色/配饰）" in strategy["required_prompt_fields"]
    assert strategy["distinct_anchors"]["collision"] is True
    assert strategy["shot_scheduling"]["verdict"] == "split_or_layer_required"


def test_multi_subject_strategy_injects_relative_scale_when_declared() -> None:
    # registry 声明的 relative_scale 经 dna_by_id 注入多人同框策略，并加 required_prompt_field；
    # 绝对身高数字不进策略（只 relative_scale）。
    chars = [
        {"char_id": "CHAR_01", "form": "常态", "tier": "multi_reference"},
        {"char_id": "CHAR_02", "form": "常服", "tier": "multi_reference"},
    ]
    dna = {"CHAR_01": {"hair": "乌黑", "outfit": "月白", "relative_scale": ""},
           "CHAR_02": {"hair": "金发", "outfit": "玄黑", "relative_scale": "比沈念高半个头"}}
    strategy = rp.plan_multi_subject_strategy(chars, _MULTI_REF, dna_by_id=dna)
    assert strategy["relative_scale"] == {"CHAR_02": "比沈念高半个头"}
    assert "相对身量/身高比例（relative_scale）" in strategy["required_prompt_fields"]


def test_multi_subject_strategy_no_relative_scale_field_when_absent() -> None:
    chars = [
        {"char_id": "CHAR_01", "form": "常态", "tier": "multi_reference"},
        {"char_id": "CHAR_02", "form": "常服", "tier": "multi_reference"},
    ]
    strategy = rp.plan_multi_subject_strategy(chars, _MULTI_REF)
    assert strategy["relative_scale"] == {}
    assert "相对身量/身高比例（relative_scale）" not in strategy["required_prompt_fields"]


def test_load_character_forms_carries_physical_scale(tmp_path) -> None:
    # registry 的 physical_scale 透传进 norm_forms，供下游 dna_by_id/策略读取
    root = tmp_path
    (root / "出图" / "共享").mkdir(parents=True)
    registry = {"characters": [{
        "id": "CHAR_01", "name": "王敦",
        "forms": [{"form": "常态", "asset_key": "王敦",
                   "character_dna": {"face": "圆脸"},
                   "physical_scale": {"height_cm": 178, "body_type": "微胖",
                                      "relative_scale": "比沈念高半个头"}}],
    }]}
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    forms = rp.load_character_forms(root)
    assert forms[0]["forms"][0]["physical_scale"]["relative_scale"] == "比沈念高半个头"


def test_distinct_anchors_embedding_confusable_overrides_distinct_palette() -> None:
    # 服装/发色不同（颜色桶不撞），但参考脸 embedding 判定易混 → 仍 collision=True，标 embedding_confusable
    dna = {
        "CHAR_01": {"hair": "金发", "outfit": "玄黑战甲"},
        "CHAR_02": {"hair": "乌黑", "outfit": "月白宫装"},
    }
    out = rp.plan_distinct_anchors(dna, ["CHAR_01", "CHAR_02"],
                                   confusable_pairs=[("CHAR_01", "CHAR_02")])
    assert out["collision"] is True
    assert out["collisions"][0]["embedding_confusable"] is True
    assert "embedding" in out["collisions"][0]["layer"]
    assert out["embedding_checked"] is True


def test_distinct_anchors_no_embedding_pairs_falls_back_to_color() -> None:
    dna = {
        "CHAR_01": {"hair": "乌黑", "outfit": "月白宫装"},
        "CHAR_02": {"hair": "金发", "outfit": "玄黑战甲"},
    }
    out = rp.plan_distinct_anchors(dna, ["CHAR_01", "CHAR_02"], confusable_pairs=[])
    assert out["collision"] is False
    assert out["embedding_checked"] is True


def test_compute_confusable_pairs_unavailable_without_insightface(tmp_path) -> None:
    # 无参考图 / 无 insightface → available False，pairs 空（调用方回退颜色桶），不崩
    out = rp.compute_confusable_pairs(tmp_path, {"CHAR_01": None, "CHAR_02": None})
    assert out["pairs"] == set()


def test_multi_subject_strategy_large_same_frame_when_four_named() -> None:
    chars = [{"char_id": f"CHAR_0{i}", "form": "常态", "tier": "multi_reference"} for i in range(1, 5)]
    strategy = rp.plan_multi_subject_strategy(chars, _MULTI_REF, closeup=False)
    assert strategy["shot_scheduling"]["verdict"] == "large_same_frame_requires_strategy"


def test_multi_subject_strategy_native_subject_slots_when_registered() -> None:
    profile = {"label": "可灵主体库", "canonical": "kling", "persistent_subject": True,
               "multi_reference": True}
    chars = [
        {"char_id": "CHAR_01", "form": "常态", "tier": "native_subject"},
        {"char_id": "CHAR_02", "form": "常服", "tier": "native_subject"},
    ]
    strategy = rp.plan_multi_subject_strategy(chars, profile)
    assert strategy
    assert strategy["mode"] == "native_subject_slots"
    assert strategy["persistent_subject"] is True
    assert strategy["needs_registration"] is False


# ── 端到端 ─────────────────────────────────────────────────────────────────────

def _setup_work(tmp_path: Path) -> Path:
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "出图" / "共享").mkdir(parents=True)
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI：Codex\n", encoding="utf-8")
    registry = {
        "kind": "n2d_identity_registry",
        "characters": [{
            "id": "CHAR_01", "name": "沈念", "scope": "全篇女主",
            "forms": [{
                "form": "常态", "asset_key": "沈念_常态",
                "reference_group": _RG,
                "angle_policy": _AP,
                "identity_adapters": {"image": {"codex": {"status": "fallback_reference_group"}}},
            }],
        }],
    }
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    storyboard = {
        "clips": [
            {"id": "C1", "label": "对峙", "shots": [{"lens": "CU 85mm", "desc": "沈念崩溃落泪"}],
             "continuity": {"start_state": "", "end_state": ""}},
            {"id": "C2", "label": "空镜", "shots": [{"lens": "LS 35mm", "desc": "宫墙远景"}],
             "continuity": {"start_state": "", "end_state": ""}},
        ]
    }
    (root / "脚本" / "第1集" / "storyboard.json").write_text(
        json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    return root


def test_build_plan_end_to_end(tmp_path: Path) -> None:
    root = _setup_work(tmp_path)
    plan = rp.build_plan(root, "第1集")
    assert plan["kind"] == rp.PLAN_KIND
    assert plan["backend"] == "codex"
    assert plan["summary"]["clip_count"] == 2
    # C1 是核心女主近景大表情弱后端镜 → 计入大变化镜 + 升 LoRA
    assert plan["summary"]["weak_backend_large_delta_clips"] >= 1
    assert any("CHAR_01" in c for c in plan["summary"]["chars_need_lora"])
    # 落档原子写出
    jp, mp = rp.write_plan(root, "第1集", plan)
    assert jp.exists() and mp.exists()
    assert "逐镜参考规划" in mp.read_text(encoding="utf-8")


def test_build_plan_emits_per_character_memory_consumption_from_real_clips(tmp_path: Path) -> None:
    root = _setup_work(tmp_path)
    _write_memory_anchor_contract_fixture(root, char_key="沈念_常态")

    plan = rp.build_plan(root, "第1集")

    summary = plan["summary"]
    contract = summary["memory_anchor_contract"]
    expected = {"沈念_常态": ["C1"]}
    assert summary["required_char_keys"] == ["沈念_常态"]
    assert summary["consumed_char_keys"] == ["沈念_常态"]
    assert summary["consumed_clip_ids_by_char"] == expected
    assert contract["required_char_keys"] == ["沈念_常态"]
    assert contract["consumed_char_keys"] == ["沈念_常态"]
    assert contract["consumed_clip_ids_by_char"] == expected
    assert contract["unconsumed_char_keys"] == []
    char_plan = plan["clips"][0]["characters"][0]
    assert char_plan["memory_anchor_char_key"] == "沈念_常态"
    assert char_plan["memory_anchor_refs_consumed"] == ["出图/共享/图片/memory_anchor.png"]


def test_build_plan_exposes_required_memory_key_not_consumed_by_any_clip(tmp_path: Path) -> None:
    root = _setup_work(tmp_path)
    _write_memory_anchor_contract_fixture(root, char_key="CHAR_99/常态")

    plan = rp.build_plan(root, "第1集")

    contract = plan["summary"]["memory_anchor_contract"]
    assert contract["status"] == "ready"
    assert contract["required_char_keys"] == ["CHAR_99/常态"]
    assert contract["consumed_char_keys"] == []
    assert contract["consumed_clip_ids_by_char"] == {}
    assert contract["unconsumed_char_keys"] == ["CHAR_99/常态"]
    assert any(
        action.get("kind") == "memory_anchor_unconsumed"
        for action in plan["summary"]["action_required"]
    )


def test_build_plan_emits_multi_subject_actions(tmp_path: Path) -> None:
    root = _setup_work(tmp_path)
    reg_path = root / "出图" / "共享" / "identity_registry.json"
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    registry["characters"].append({
        "id": "CHAR_02", "name": "柳娘子", "scope": "单集配角",
        "forms": [{
            "form": "常服", "asset_key": "柳娘子_常服",
            "reference_group": {
                "front": "出图/共享/图片/定妆_柳娘子.png",
                "outfit": "出图/共享/图片/定妆_柳娘子_半身.png",
            },
            "angle_policy": {"risky": []},
            "identity_adapters": {"image": {"codex": {"status": "fallback_reference_group"}}},
        }],
    })
    reg_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    storyboard_path = root / "脚本" / "第1集" / "storyboard.json"
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    storyboard["clips"][0]["character_ids"] = ["CHAR_01", "CHAR_02"]
    storyboard["clips"][0]["template_contract"] = {
        "blocking": "CHAR_01 画左，CHAR_02 画右",
        "character_slots": {"LEFT_SLOT": "CHAR_01", "RIGHT_SLOT": "CHAR_02"},
    }
    storyboard_path.write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")

    plan = rp.build_plan(root, "第1集")

    actions = plan["summary"]["multi_subject_actions"]
    assert actions and actions[0]["mode"] == "regional_construct_required"
    assert "多人同框策略" in rp.render_md(plan)
    assert "CHAR_01/常态" in actions[0]["chars"]
    assert "CHAR_02/常服" in actions[0]["chars"]


# ── G2 跨集记忆锚（memory-sink）注入 ───────────────────────────────────────────

def _mem_char():
    return {"id": "CHAR_01", "name": "沈念", "form": "常态",
            "reference_group": {"front": "f.png", "three_quarter": "tq.png", "outfit": "o.png"},
            "reference_atlas": {}, "angle_policy": {}}


def _mem_profile():
    return {"label": "X", "canonical": "x", "max_reference_images": 3, "multi_reference": True}


def test_memory_anchor_prepended_as_top_priority_and_survives_cap():
    p = rp.plan_character_in_clip(_mem_char(), ["closeup"], False, _mem_profile(),
                                  "multi_reference", True,
                                  memory_refs=["出图/共享/图片/定妆_沈念_front_ep1.png"])
    roles = [r["role"] for r in p["recommended_references"]]
    assert roles[0] == "memory_anchor"  # 最高优先，封顶时最先保留
    assert p["memory_anchor_reinjected"] is True


def test_memory_anchor_dedups_existing_path():
    p = rp.plan_character_in_clip(_mem_char(), [], False, _mem_profile(),
                                  "multi_reference", False, memory_refs=["f.png"])
    assert sum(1 for r in p["recommended_references"] if r["path"] == "f.png") == 1
    assert p["memory_anchor_reinjected"] is True
    assert p["memory_anchor_refs_consumed"] == ["f.png"]
    assert not any(r["role"] == "memory_anchor" for r in p["recommended_references"])


def test_no_memory_refs_is_status_quo():
    p = rp.plan_character_in_clip(_mem_char(), [], False, _mem_profile(),
                                  "multi_reference", False)
    assert p["memory_anchor_reinjected"] is False
    assert not any(r["role"] == "memory_anchor" for r in p["recommended_references"])


def test_memory_refs_matcher_flexible_keys():
    assert rp._memory_refs_for({"CHAR_01/常态": ["m1.png"]}, "CHAR_01", "沈念", "CHAR_01/常态") == ["m1.png"]
    assert rp._memory_refs_for({"沈念": ["m2.png"]}, "CHAR_01", "沈念", "") == ["m2.png"]
    assert rp._memory_refs_for({"CHAR_99": ["x"]}, "CHAR_01", "沈念", "") == []


def test_memory_refs_matcher_never_substring_binds_char_1_to_char_10():
    mem = {
        "CHAR_10/常态": ["char10.png"],
        "沈念十号/常态": ["name10.png"],
    }

    assert rp._memory_refs_for(mem, "CHAR_1", "沈念", "CHAR_1/常态") == []
    assert rp._memory_match_for(mem, "CHAR_10", "沈念十号", "CHAR_10/常态")[0] == "CHAR_10/常态"


def test_memory_refs_matcher_refuses_ambiguous_character_with_multiple_forms():
    mem = {
        "CHAR_01/常态": ["normal.png"],
        "CHAR_01/战损态": ["battle.png"],
    }

    assert rp._memory_match_for(mem, "CHAR_01", "沈念", "") == ("", [])
    assert rp._memory_match_for(mem, "CHAR_01", "沈念", "CHAR_01/战损态") == (
        "CHAR_01/战损态",
        ["battle.png"],
    )


def _write_memory_anchor_contract_fixture(
    root: Path,
    *,
    available: bool = True,
    char_key: str = "CHAR_01/常态",
    reference_rel: str = "出图/共享/图片/memory_anchor.png",
    create_reference: bool = True,
) -> Path:
    shared = root / "出图" / "共享"
    prod = root / "生产数据"
    shared.mkdir(parents=True, exist_ok=True)
    prod.mkdir(parents=True, exist_ok=True)
    registry = shared / "identity_registry.json"
    if not registry.is_file():
        registry.write_text('{"characters":[]}', encoding="utf-8")
    drift = prod / "identity_drift_report.json"
    drift.write_text('{"characters":{}}', encoding="utf-8")
    storyboard = root / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True, exist_ok=True)
    if not storyboard.is_file():
        storyboard.write_text('{"clips":[]}', encoding="utf-8")
    if create_reference:
        reference = root / reference_rel
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_bytes(b"memory-anchor-pixels")
    plan = {
        "kind": "n2d_memory_anchor_plan",
        "version": 3,
        "status": "ready",
        "episode": "第1集",
        "available": available,
        "source_fingerprint": {
            "identity_registry_sha256": rp._file_sha256(registry),
            "identity_drift_report_sha256": rp._file_sha256(drift),
            "storyboard_sha256": rp._file_sha256(storyboard),
        },
        "rows": [{
            "char": char_key,
            "reinject": True,
            "memory_anchor_refs": [reference_rel],
        }],
    }
    path = prod / "memory_anchor_plan_第1集.json"
    path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return path


def test_memory_anchor_contract_requires_available_and_exact_current_sources(tmp_path: Path):
    root = tmp_path
    plan_path = _write_memory_anchor_contract_fixture(root, available=False)

    memory_map, contract = rp._memory_anchor_contract(root, "第1集")
    assert memory_map == {}
    assert contract["status"] == "invalid"
    assert "plan_available_not_true" in contract["errors"]

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["available"] = True
    plan["source_fingerprint"]["identity_registry_sha256"] = "stale-registry-sha"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    memory_map, contract = rp._memory_anchor_contract(root, "第1集")
    assert memory_map == {}
    assert "identity_registry_sha256_stale" in contract["errors"]

    (root / "生产数据" / "identity_drift_report.json").unlink()
    memory_map, contract = rp._memory_anchor_contract(root, "第1集")
    assert memory_map == {}
    assert "identity_drift_report_missing_or_unreadable" in contract["errors"]


def test_memory_anchor_contract_rejects_legacy_version_and_stale_storyboard(tmp_path: Path):
    plan_path = _write_memory_anchor_contract_fixture(tmp_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["version"] = 2
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    memory_map, contract = rp._memory_anchor_contract(tmp_path, "第1集")
    assert memory_map == {}
    assert "plan_version_legacy" in contract["errors"]

    plan["version"] = 3
    plan["status"] = "warn"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    memory_map, contract = rp._memory_anchor_contract(tmp_path, "第1集")
    assert memory_map == {}
    assert "plan_status_not_ready" in contract["errors"]

    plan["status"] = "ready"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "脚本" / "第1集" / "storyboard.json").write_text(
        '{"clips":[{"id":"Clip_01"}]}', encoding="utf-8"
    )
    memory_map, contract = rp._memory_anchor_contract(tmp_path, "第1集")
    assert memory_map == {}
    assert "storyboard_sha256_stale" in contract["errors"]


def test_memory_anchor_contract_validates_every_reference_file(tmp_path: Path):
    root = tmp_path
    _write_memory_anchor_contract_fixture(root, create_reference=False)

    memory_map, contract = rp._memory_anchor_contract(root, "第1集")

    assert memory_map == {}
    assert contract["status"] == "invalid"
    assert contract["missing_reference_rows"] == ["CHAR_01/常态"]
    assert contract["missing_reference_files"]["CHAR_01/常态"] == [
        "出图/共享/图片/memory_anchor.png"
    ]
    assert any(error.startswith("memory_anchor_ref_missing:CHAR_01/常态:") for error in contract["errors"])


def test_memory_anchor_contract_ready_exposes_reference_sha(tmp_path: Path):
    root = tmp_path
    _write_memory_anchor_contract_fixture(root)

    memory_map, contract = rp._memory_anchor_contract(root, "第1集")

    assert contract["status"] == "ready"
    assert memory_map == {"CHAR_01/常态": ["出图/共享/图片/memory_anchor.png"]}
    assert contract["required_char_keys"] == ["CHAR_01/常态"]
    assert contract["validated_reference_sha256_by_char"]["CHAR_01/常态"]


def test_build_plan_ignores_blackboard_expression_span_edits(tmp_path):
    import sys, os as _os
    sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "_lib"))
    import n2d_intent as ni
    root = _setup_work(tmp_path)
    # C1 改成中性描述 + expression_span=微（storyboard 不触发大表情大变化）
    sbp = root / "脚本" / "第1集" / "storyboard.json"
    sb = json.loads(sbp.read_text(encoding="utf-8"))
    sb["clips"][0]["shots"] = [{"lens": "CU 85mm", "desc": "沈念静静站着"}]
    sb["clips"][0]["continuity"] = {"expression_span": "微", "start_state": "", "end_state": ""}
    sb["clips"][0]["character_ids"] = ["CHAR_01"]
    sbp.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    # storyboard 中性 + expression_span=微 → 不触发 strong_emotion variation_delta
    base = json.dumps(rp.build_plan(root, "第1集"), ensure_ascii=False).count("strong_emotion")
    assert base == 0
    # 手改黑板把 C1 升「大表情」：应无效，出图侧继续以 storyboard 为真值源。
    ni.write_shot_intent(str(root), "第1集")
    obj = ni.load_shot_intent(str(root), "第1集")
    obj["shots"][0]["expression_span"] = "大"
    (root / "脚本" / "第1集" / "shot_intent.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    after = json.dumps(rp.build_plan(root, "第1集"), ensure_ascii=False).count("strong_emotion")
    assert after == 0


def test_reference_feed_tagged_multi_image_for_multi_reference_backend() -> None:
    # 多参考后端 + ≥2 张参考 → 分图分标，给出 @ImageN 标签，明确不要拼 sheet。
    p = rp.plan_character_in_clip(
        _char(), deltas=["closeup"], multi=False,
        profile=_MULTI_REF, tier="multi_reference", scope_is_core=True,
    )
    feed = p["reference_feed"]
    assert feed["mode"] == "tagged_multi_image"
    assert feed["tagged_inputs"] and feed["tagged_inputs"][0].startswith("@Image1")
    assert "sheet" in feed["guidance"]


def test_reference_feed_single_reference_for_non_multi_backend() -> None:
    profile = {"label": "单参考后端", "canonical": "x", "multi_reference": False, "max_reference_images": None}
    p = rp.plan_character_in_clip(
        _char(), deltas=["closeup"], multi=False,
        profile=profile, tier="reference_group", scope_is_core=False,
    )
    feed = p["reference_feed"]
    assert feed["mode"] == "sequential_single_reference"
    assert feed["tagged_inputs"] == []


def test_reference_feed_video_hint_when_backend_ingests_video() -> None:
    profile = {"label": "可灵Elements", "canonical": "kling", "multi_reference": True,
               "max_reference_images": None, "ingests_video": True}
    p = rp.plan_character_in_clip(
        _char(), deltas=["strong_emotion"], multi=False,
        profile=profile, tier="native_unregistered", scope_is_core=True,
    )
    feed = p["reference_feed"]
    assert feed["video_reference_supported"] is True
    assert "视频" in feed["video_reference_hint"]


def test_reference_feed_no_video_hint_when_backend_lacks_video() -> None:
    p = rp.plan_character_in_clip(
        _char(), deltas=["strong_emotion"], multi=False,
        profile=_MULTI_REF, tier="native_unregistered", scope_is_core=True,
    )
    assert p["reference_feed"]["video_reference_supported"] is False
    assert p["reference_feed"]["video_reference_hint"] == ""


# ── 共享资产脸策略规划（治含人资产镜规划侧脸漂盲区·#7） ──
def _mk_assets(tmp_path, assets):
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "asset_registry.json").write_text(
        json.dumps({"assets": assets}, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_plan_shared_assets_faceless_and_none(tmp_path):
    root = _mk_assets(tmp_path, [
        {"id": "WEAPON_H", "type": "weapon", "owner": "CHAR_J", "name": "戟",
         "reference_group": {"scale_reference": "图片/定妆_握持比例.png"}},   # faceless
        {"id": "WEAPON_PLAIN", "type": "weapon", "name": "纯武器美术"},        # none → 跳过
    ])
    sa = rp.plan_shared_assets(root, [])
    assert sa["available"] is True
    ids = {a["asset_id"]: a for a in sa["assets"]}
    assert ids["WEAPON_H"]["face_policy"] == "faceless" and ids["WEAPON_H"]["face_refs"] == []
    assert "WEAPON_PLAIN" not in ids                # none 不进规划
    assert sa["summary"]["faceless"] == 1 and sa["actions"] == []


def test_plan_shared_assets_face_locked_no_owner_actions(tmp_path):
    root = _mk_assets(tmp_path, [
        {"id": "POSTER_BAD", "type": "poster", "name": "群像海报 人物"},       # face_locked·无 owner
    ])
    sa = rp.plan_shared_assets(root, [])
    a = [x for x in sa["assets"] if x["asset_id"] == "POSTER_BAD"][0]
    assert a["face_policy"] == "face_locked" and a["issue"] == "face_locked_no_owner"
    assert any(ac["issue"] == "face_locked_no_owner" for ac in sa["actions"])


def test_plan_shared_assets_face_locked_folds_owner_anchor(tmp_path):
    root = _mk_assets(tmp_path, [
        {"id": "WEAPON_ACT", "type": "weapon", "owner": "CHAR_J", "name": "持械动作参考",
         "reference_group": {"primary": "图片/定妆_WEAPON_ACT_动作_持.png"}},   # face_locked + owner
    ])
    chars = [{"id": "CHAR_J", "forms": [{"form": "常态",
              "reference_group": {"face": "出图/共享/图片/定妆_CHAR_J_脸.png"}}]}]
    sa = rp.plan_shared_assets(root, chars)
    a = [x for x in sa["assets"] if x["asset_id"] == "WEAPON_ACT"][0]
    assert a["face_policy"] == "face_locked" and a["carried_identities"] == ["CHAR_J"]
    assert a["face_refs"] and a["face_refs"][0]["role"] == "face_anchor" and "CHAR_J" in a["face_refs"][0]["carried"]
    assert a.get("issue") is None and sa["actions"] == []
def test_parse_clip_normalizes_structured_character_form_binding():
    parsed = rp.parse_clip({
        "entity_schedule": {"characters": ["CHAR_01/制服态"]},
        "character_ids": ["CHAR_99/不应覆盖"],
        "continuity": {},
    })
    assert parsed["character_ids"] == ["CHAR_01"]
    assert "CHAR_01/制服态" in parsed["text"]
