#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""image_backend_adapter 单测。从本目录跑：
    cd skills/ad/_lib && python3 -m pytest test_image_backend_adapter.py
覆盖：能力三态（unknown 不当支持）/ Codex-OpenAI 无持久主体库 → 梯子封顶「指定参考图」/
未知后端保守 profile（known=False·预算 1）/ 四档档名与 `一致性增强` 选择点一一对齐 /
lock_tier_for 对 product vs character 的行为。
"""
import pytest

from image_backend_adapter import (
    ALL_CAPABILITIES,
    ASSET_KIND_BRAND,
    ASSET_KIND_CHARACTER,
    ASSET_KIND_LOCATION,
    ASSET_KIND_PRODUCT,
    ASSET_KIND_PROP,
    ASSET_KIND_UNKNOWN,
    CAP_AVAILABLE,
    CAP_CONTROLNET,
    CAP_FACE_EMBEDDING,
    CAP_LORA,
    CAP_MASK_INPAINT,
    CAP_MULTI_REFERENCE,
    CAP_REFERENCE,
    CAP_SEED_CONTROL,
    CAP_SUBJECT_LIBRARY,
    CAP_UNAVAILABLE,
    CAP_UNKNOWN,
    TIER_DIRECTED_REFERENCE,
    TIER_LADDER,
    TIER_LORA,
    TIER_SETTING_VALUE,
    TIER_SHARED_KIT,
    TIER_SUBJECT_LIBRARY,
    UNKNOWN_BACKEND_REFERENCE_LIMIT,
    asset_kind_for_id,
    backends_reaching_tier,
    capability_state,
    describe,
    has_capability,
    lock_tier_for,
    normalize_backend,
    profile_for,
    reference_limit_for,
    seed_capability,
    tier_for_setting,
    tier_rank,
    tier_setting_value,
    unknown_capabilities,
    unknown_profile,
)


# ── 能力三态：unknown 是诚实位，绝不当作「支持」 ─────────────────────────────────

def test_capability_states_are_tri_state_over_all_capabilities():
    caps = profile_for("Nano Banana Pro")["capabilities"]
    assert set(caps) == set(ALL_CAPABILITIES)
    assert set(caps.values()) <= {CAP_AVAILABLE, CAP_UNKNOWN, CAP_UNAVAILABLE}
    # gemini：多参考已确证；持久主体库无公开证据 → unknown；LoRA 无挂载点 → unavailable。
    assert caps[CAP_MULTI_REFERENCE] == CAP_AVAILABLE
    assert caps[CAP_SUBJECT_LIBRARY] == CAP_UNKNOWN
    assert caps[CAP_LORA] == CAP_UNAVAILABLE


def test_has_capability_only_accepts_available_never_unknown():
    gemini = profile_for("Nano Banana Pro")
    assert capability_state(gemini, CAP_SUBJECT_LIBRARY) == CAP_UNKNOWN
    # 未知 ≠ 支持：路由决策不得据 unknown 升档。
    assert has_capability(gemini, CAP_SUBJECT_LIBRARY) is False
    assert has_capability(gemini, CAP_MULTI_REFERENCE) is True
    assert has_capability(gemini, CAP_LORA) is False


def test_unknown_capability_state_is_reported_not_silently_unsupported():
    # unknown 必须在报告里显性列出——「未知」与「不支持」对人的下一步动作完全不同。
    assert unknown_capabilities(profile_for("Nano Banana Pro")) == sorted(
        [CAP_SUBJECT_LIBRARY, CAP_CONTROLNET, CAP_MASK_INPAINT, CAP_SEED_CONTROL])
    assert unknown_capabilities(profile_for("Seedream 4.5")) == sorted(
        [CAP_CONTROLNET, CAP_MASK_INPAINT, CAP_SEED_CONTROL])


def test_capability_state_of_unlisted_capability_is_unknown_not_crash():
    assert capability_state(profile_for("GPT Image 2"), "teleportation") == CAP_UNKNOWN
    assert has_capability(profile_for("GPT Image 2"), "teleportation") is False


# ── Codex / OpenAI：无持久主体库 → 梯子封顶「指定参考图」 ────────────────────────

def test_openai_gpt_image_2_has_no_persistent_subject_library():
    profile = profile_for("GPT Image 2", "Codex CLI")
    assert profile["backend"] == "openai"
    assert profile["known"] is True
    # Codex/OpenAI 无持久主体，自动回退 reference_group 兜底。
    # 这里必须是 unavailable（明确不支持），不是 unknown——否则会被误读成「也许能升档」。
    assert capability_state(profile, CAP_SUBJECT_LIBRARY) == CAP_UNAVAILABLE
    assert capability_state(profile, CAP_LORA) == CAP_UNAVAILABLE
    assert capability_state(profile, CAP_MULTI_REFERENCE) == CAP_AVAILABLE


@pytest.mark.parametrize("kind", [ASSET_KIND_PRODUCT, ASSET_KIND_BRAND, ASSET_KIND_CHARACTER])
def test_openai_ladder_caps_at_directed_reference_for_every_asset_kind(kind):
    profile = profile_for("GPT Image 2", "Codex CLI")
    # ad 线默认路线的真实天花板：产品/代言人都只能靠多参考硬堆，够不着主体库/LoRA。
    assert lock_tier_for(profile, kind) == TIER_DIRECTED_REFERENCE
    assert tier_setting_value(lock_tier_for(profile, kind)) == "指定参考图"


def test_openai_reference_limit_is_five():
    assert reference_limit_for(profile_for("GPT Image 2", "Codex CLI")) == 5


# ── 未知后端 → 保守 profile，绝不假装支持 ───────────────────────────────────────

def test_unknown_backend_falls_back_to_conservative_profile():
    profile = profile_for("MyCustomDiffusion v9", "自建 runner")
    assert profile["known"] is False
    assert profile["backend"] == "unknown"
    assert reference_limit_for(profile) == UNKNOWN_BACKEND_REFERENCE_LIMIT == 1
    # 只假定最基本的单张图生图，其余全 unknown——不假装支持，也不谎称不支持。
    assert capability_state(profile, CAP_REFERENCE) == CAP_AVAILABLE
    for cap in (CAP_MULTI_REFERENCE, CAP_SUBJECT_LIBRARY, CAP_FACE_EMBEDDING,
                CAP_LORA, CAP_CONTROLNET, CAP_MASK_INPAINT, CAP_SEED_CONTROL):
        assert capability_state(profile, cap) == CAP_UNKNOWN
        assert has_capability(profile, cap) is False
    assert profile["requested_model"] == "MyCustomDiffusion v9"
    assert profile["requested_channel"] == "自建 runner"


def test_unknown_backend_ladder_floors_at_shared_kit_for_all_kinds():
    profile = profile_for("MyCustomDiffusion v9")
    for kind in (ASSET_KIND_PRODUCT, ASSET_KIND_CHARACTER, ASSET_KIND_UNKNOWN):
        # 地板永远成立（一张图 + 锚点句），但绝不因 unknown 升到「指定参考图」。
        assert lock_tier_for(profile, kind) == TIER_SHARED_KIT


def test_empty_backend_declaration_is_unknown_not_default_openai():
    profile = profile_for("", "")
    assert profile["known"] is False
    assert "未声明" in profile["label"]
    assert normalize_backend("", "") == ""


def test_unknown_profile_label_carries_raw_request():
    assert "Foo Bar" in unknown_profile("Foo Bar", "")["label"]


# ── 后端归一：模型优先于渠道 ────────────────────────────────────────────────────

@pytest.mark.parametrize("model,channel,expected", [
    ("GPT Image 2", "Codex CLI", "openai"),
    ("gpt-image-1", "", "openai"),
    ("Nano Banana Pro", "Google Gemini API", "gemini"),
    ("Seedream 4.5", "BytePlus ModelArk", "seedream"),
    ("Kling Image 3.0", "", "kling"),
    ("即梦 Dreamina Image", "", "dreamina"),
    ("", "Codex CLI", "openai"),          # 只有渠道时才回落到渠道
    ("完全没听过的模型", "没听过的渠道", ""),
])
def test_normalize_backend(model, channel, expected):
    assert normalize_backend(model, channel) == expected


def test_model_wins_over_channel_so_codex_channel_does_not_hijack_seedream():
    # 防回归：`生图渠道=Codex CLI` 不得把 `生图模型=Seedream 4.5` 误判成 openai。
    assert normalize_backend("Seedream 4.5", "Codex CLI") == "seedream"
    assert profile_for("Seedream 4.5", "Codex CLI")["backend"] == "seedream"


# ── 四档：档名/档数与用户可见的 `一致性增强` 选择点一一对齐 ──────────────────────

def test_tier_ladder_maps_one_to_one_onto_consistency_setting_values():
    # 防以后有人另造第五档 / 改档名：用户在 _设置.md 选的是哪档，报告里说的就得是哪档。
    assert TIER_LADDER == (TIER_SHARED_KIT, TIER_DIRECTED_REFERENCE, TIER_SUBJECT_LIBRARY, TIER_LORA)
    assert TIER_SETTING_VALUE == {
        TIER_SHARED_KIT: "共享定妆+锚点",
        TIER_DIRECTED_REFERENCE: "指定参考图",
        TIER_SUBJECT_LIBRARY: "后端主体库",
        TIER_LORA: "+LoRA",
    }
    assert list(TIER_SETTING_VALUE) == list(TIER_LADDER)
    assert len(set(TIER_SETTING_VALUE.values())) == 4


def test_tier_rank_is_monotonic_and_unknown_tier_is_minus_one():
    assert [tier_rank(t) for t in TIER_LADDER] == [0, 1, 2, 3]
    assert tier_rank(TIER_SUBJECT_LIBRARY) > tier_rank(TIER_DIRECTED_REFERENCE) > tier_rank(TIER_SHARED_KIT)
    assert tier_rank("face_embedding") == -1  # face_embedding 不是一档
    assert tier_rank("") == -1


@pytest.mark.parametrize("tier,value", list(TIER_SETTING_VALUE.items()))
def test_setting_value_round_trips_back_to_tier_id(tier, value):
    assert tier_setting_value(tier) == value
    assert tier_for_setting(value) == tier


def test_tier_for_setting_does_not_guess():
    assert tier_for_setting("") is None
    assert tier_for_setting("随便什么档") is None
    # 用户可能带前缀写；只要包含契约取值就认得出。
    assert tier_for_setting("一致性增强：后端主体库") == TIER_SUBJECT_LIBRARY


def test_tier_setting_value_of_unknown_tier_echoes_input():
    assert tier_setting_value("no_such_tier") == "no_such_tier"


# ── lock_tier_for：product vs character ────────────────────────────────────────

def test_subject_library_backend_lifts_product_to_tier_two():
    for model in ("Seedream 4.5", "Kling Image 3.0"):
        profile = profile_for(model)
        assert lock_tier_for(profile, ASSET_KIND_PRODUCT) == TIER_SUBJECT_LIBRARY
        assert lock_tier_for(profile, ASSET_KIND_BRAND) == TIER_SUBJECT_LIBRARY
        # LoRA 无官方挂载点 → 连代言人也停在第②档。
        assert lock_tier_for(profile, ASSET_KIND_CHARACTER) == TIER_SUBJECT_LIBRARY


def test_lora_tier_is_character_only_and_never_lifts_product():
    # ad-image/SKILL.md：「③LoRA 仅核心长线代言人」——不给产品包装升这档。
    lora_backend = {"capabilities": {CAP_REFERENCE: CAP_AVAILABLE,
                                     CAP_MULTI_REFERENCE: CAP_AVAILABLE,
                                     CAP_SUBJECT_LIBRARY: CAP_AVAILABLE,
                                     CAP_LORA: CAP_AVAILABLE}}
    assert lock_tier_for(lora_backend, ASSET_KIND_CHARACTER) == TIER_LORA
    for kind in (ASSET_KIND_PRODUCT, ASSET_KIND_BRAND, ASSET_KIND_LOCATION,
                 ASSET_KIND_PROP, ASSET_KIND_UNKNOWN):
        assert lock_tier_for(lora_backend, kind) == TIER_SUBJECT_LIBRARY


def test_face_embedding_never_lifts_a_tier_for_product_packaging():
    # 脸嵌入对产品包装无意义，且用户契约里没这一档 → 不得成为升档理由。
    face_only = {"capabilities": {CAP_REFERENCE: CAP_AVAILABLE,
                                  CAP_FACE_EMBEDDING: CAP_AVAILABLE}}
    assert lock_tier_for(face_only, ASSET_KIND_PRODUCT) == TIER_SHARED_KIT
    assert lock_tier_for(face_only, ASSET_KIND_CHARACTER) == TIER_SHARED_KIT


def test_lock_tier_for_ignores_unknown_capabilities():
    # subject_library=unknown 的 gemini 不得被升到第②档（诚实边界）。
    assert lock_tier_for(profile_for("Nano Banana Pro"), ASSET_KIND_PRODUCT) == TIER_DIRECTED_REFERENCE
    assert lock_tier_for(profile_for("即梦 Dreamina"), ASSET_KIND_PRODUCT) == TIER_DIRECTED_REFERENCE


def test_lock_tier_for_accepts_model_string_directly():
    assert lock_tier_for("GPT Image 2", ASSET_KIND_PRODUCT) == TIER_DIRECTED_REFERENCE
    assert lock_tier_for("Kling Image 3.0", ASSET_KIND_PRODUCT) == TIER_SUBJECT_LIBRARY


def test_lock_tier_for_defaults_to_unknown_asset_kind():
    assert lock_tier_for(profile_for("GPT Image 2")) == TIER_DIRECTED_REFERENCE


# ── 资产 ID → 类型 ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("asset_id,kind", [
    ("PROD_STARBOX_APP", ASSET_KIND_PRODUCT),
    ("BRAND_STARBOX", ASSET_KIND_BRAND),
    ("CHAR_host", ASSET_KIND_CHARACTER),
    ("LOC_kitchen", ASSET_KIND_LOCATION),
    ("PROP_cup", ASSET_KIND_PROP),
    ("product", ASSET_KIND_UNKNOWN),
    ("", ASSET_KIND_UNKNOWN),
    ("PRODUCE_x", ASSET_KIND_UNKNOWN),   # 前缀是 `PROD_`，不是「PROD 开头」
    ("prod_lower", ASSET_KIND_UNKNOWN),  # 大小写敏感：与 product_qc 的 PROD_ 口径同源
])
def test_asset_kind_for_id(asset_id, kind):
    assert asset_kind_for_id(asset_id) == kind


# ── seed 控制能力三态（逐后端如实标注·查不到证据一律 unknown） ────────────────────

def test_seed_capability_is_tri_state_per_backend():
    # openai：兄弟线 Codex 渠道 runner 落档 no-seed-api 降级口径 → 明确 unavailable。
    assert seed_capability(profile_for("GPT Image 2", "Codex CLI")) == CAP_UNAVAILABLE
    # 其余登记后端：仓内无传 seed 的调用证据 → unknown，绝不猜 available。
    for model in ("Nano Banana Pro", "Seedream 4.5", "Kling Image 3.0", "即梦 Dreamina"):
        assert seed_capability(profile_for(model)) == CAP_UNKNOWN
    # 未知后端 → unknown（保守，不谎称不支持）。
    assert seed_capability(profile_for("MyCustomDiffusion v9")) == CAP_UNKNOWN


def test_seed_capability_accepts_model_string_and_never_counts_as_available():
    assert seed_capability("GPT Image 2") == CAP_UNAVAILABLE
    # unknown/unavailable 都不得被 has_capability 当成支持。
    for model in ("GPT Image 2", "Seedream 4.5", "没听过的后端"):
        assert has_capability(profile_for(model), CAP_SEED_CONTROL) is False


def test_seed_control_is_a_capability_not_a_tier():
    # seed 只是可复现随机起点，不是一致性梯子的档位——不得因 seed 升档。
    assert CAP_SEED_CONTROL in ALL_CAPABILITIES
    assert tier_rank(CAP_SEED_CONTROL) == -1


# ── 升档可达路由：够得着建议档的后端清单（advisory·来自能力表） ───────────────────

def test_backends_reaching_subject_library_for_product_are_seedream_and_kling():
    reached = backends_reaching_tier(TIER_SUBJECT_LIBRARY, ASSET_KIND_PRODUCT)
    assert {r["backend"] for r in reached} == {"seedream", "kling"}
    # label 必须带「模型+渠道」信息，供人直接对照 _设置.md 切换。
    for row in reached:
        assert row["label"]


def test_backends_reaching_directed_reference_includes_all_multi_reference_backends():
    reached = {r["backend"] for r in backends_reaching_tier(TIER_DIRECTED_REFERENCE, ASSET_KIND_PRODUCT)}
    assert reached == {"openai", "gemini", "seedream", "kling", "dreamina"}


def test_backends_reaching_lora_is_empty_and_unknown_tier_is_empty():
    # 现表无任何后端有 LoRA 挂载点 → 如实空清单（调用方应建议人工降低期望/补定妆参考）。
    assert backends_reaching_tier(TIER_LORA, ASSET_KIND_CHARACTER) == []
    assert backends_reaching_tier("no_such_tier", ASSET_KIND_PRODUCT) == []


def test_backends_reaching_tier_ignores_unknown_subject_library():
    # gemini/dreamina 的 subject_library=unknown → 不得被列为「够得着第②档」。
    reached = {r["backend"] for r in backends_reaching_tier(TIER_SUBJECT_LIBRARY, ASSET_KIND_BRAND)}
    assert "gemini" not in reached and "dreamina" not in reached


# ── profile 隔离 / 预算 / 摘要 ──────────────────────────────────────────────────

def test_profile_for_returns_a_copy_so_callers_cannot_mutate_the_table():
    a = profile_for("GPT Image 2")
    a["capabilities"][CAP_SUBJECT_LIBRARY] = CAP_AVAILABLE
    a["reference_limit"] = 99
    b = profile_for("GPT Image 2")
    assert capability_state(b, CAP_SUBJECT_LIBRARY) == CAP_UNAVAILABLE
    assert reference_limit_for(b) == 5


def test_reference_limit_never_below_one_and_survives_garbage():
    assert reference_limit_for({"reference_limit": 0}) == 1
    assert reference_limit_for({"reference_limit": -3}) == 1
    assert reference_limit_for({"reference_limit": None}) == UNKNOWN_BACKEND_REFERENCE_LIMIT
    assert reference_limit_for({"reference_limit": "四"}) == UNKNOWN_BACKEND_REFERENCE_LIMIT


def test_every_registered_profile_carries_provenance_and_is_json_safe():
    import json
    for model in ("GPT Image 2", "Nano Banana Pro", "Seedream 4.5", "Kling Image 3.0", "即梦"):
        profile = profile_for(model)
        # 参考预算是内部启发式，不是厂商承诺 → 必须自带 provenance 标注。
        assert profile["provenance"] == "internal-heuristic·confidence=low"
        assert profile["reference_limit"] >= 1
        json.dumps(profile, ensure_ascii=False)  # 可直接塞进 JSON 报告
    assert profile_for("没听过")["provenance"] == "internal-heuristic·confidence=low"


def test_describe_states_known_flag_and_available_capabilities():
    text = describe(profile_for("GPT Image 2", "Codex CLI"))
    assert "known=true" in text and "参考上限 5" in text
    assert CAP_MULTI_REFERENCE in text and CAP_SUBJECT_LIBRARY not in text

    unknown = describe(profile_for("没听过的后端"))
    assert "known=false" in unknown and "参考上限 1" in unknown
