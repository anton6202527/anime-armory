"""reference_planner 单测——逐镜 delta + 后端能力路由 + 升档 + 端到端 build_plan。

cd skills/n2d-image/scripts && python3 -m pytest test_reference_planner.py
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
    p = rp.plan_character_in_clip(
        _char(rg=rg), deltas=[], multi=False,
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


def test_no_memory_refs_is_status_quo():
    p = rp.plan_character_in_clip(_mem_char(), [], False, _mem_profile(),
                                  "multi_reference", False)
    assert p["memory_anchor_reinjected"] is False
    assert not any(r["role"] == "memory_anchor" for r in p["recommended_references"])


def test_memory_refs_matcher_flexible_keys():
    assert rp._memory_refs_for({"CHAR_01/常态": ["m1.png"]}, "CHAR_01", "沈念", "CHAR_01/常态") == ["m1.png"]
    assert rp._memory_refs_for({"沈念": ["m2.png"]}, "CHAR_01", "沈念", "") == ["m2.png"]
    assert rp._memory_refs_for({"CHAR_99": ["x"]}, "CHAR_01", "沈念", "") == []
