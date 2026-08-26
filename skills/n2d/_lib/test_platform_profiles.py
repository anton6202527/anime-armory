"""video backend capability profile tests.

Run from this directory:
  python3 -m pytest test_platform_profiles.py
"""
from __future__ import annotations

import n2d_platform_profiles as profiles


def test_dreamina_has_native_multiframe_contract():
    control = profiles.video_backend_frame_control("dreamina")
    assert control["mode"] == "multi_keyframe"
    assert control["supports_native_mid_anchors"] is True
    assert control["max_timeline_frames"] == 20


def test_seedance_via_dreamina_uses_dreamina_frame_contract():
    control = profiles.video_backend_frame_control("Seedance 2.0", "即梦/Dreamina")
    assert control["mode"] == "multi_keyframe"
    assert control["supports_native_mid_anchors"] is True


def test_direct_seedance_is_conservative_first_frame_only():
    control = profiles.video_backend_frame_control("Seedance 2.0")
    assert control["mode"] == "first_frame_or_channel"
    assert control["supports_last_frame"] is False
    assert control["supports_native_mid_anchors"] is False


def test_luma_supports_first_last_but_not_native_mid_anchors():
    control = profiles.video_backend_frame_control("Luma Ray3.2")
    assert control["mode"] == "first_last"
    assert control["max_timeline_frames"] == 2
    assert control["supports_native_mid_anchors"] is False


def test_backend_supports_three_plus_frames_capability_gate():
    import n2d_platform_profiles as p
    # 只有单次原生请求真能消费 3+ 时间轴帧才算；首尾拆段接力不是原生三帧。
    assert p.backend_supports_three_plus_frames("dreamina") is True
    assert p.backend_supports_three_plus_frames("即梦") is True
    assert p.backend_supports_three_plus_frames("kling") is False
    assert p.backend_supports_three_plus_frames("veo") is False
    assert p.backend_supports_three_plus_frames("luma") is False
    assert p.backend_supports_three_plus_frames("seedance") is False
    assert p.backend_supports_three_plus_frames("sora") is False
    assert p.backend_supports_three_plus_frames("runway") is False
    assert p.backend_supports_three_plus_frames("pika") is False
    # 未知/缺省 → 需要刷新/探活/人工确认，不默认假定支持三帧
    assert p.backend_supports_three_plus_frames(None) is False
    assert p.backend_supports_three_plus_frames("某新后端2027") is False


def test_frame_strategy_separates_editorial_cuts_from_continuous_keyframes():
    low_risk = profiles.select_video_frame_strategy("veo", shot_count=1, need_end=True)
    editorial = profiles.select_video_frame_strategy(
        "veo", shot_count=2, anchor_count=1, need_end=True
    )
    risky_relay = profiles.select_video_frame_strategy(
        "kling", shot_count=1, anchor_count=1, need_end=True, requires_mid_anchors=True
    )
    risky_native = profiles.select_video_frame_strategy(
        "dreamina", shot_count=1, anchor_count=1, need_end=True, requires_mid_anchors=True
    )

    assert low_risk["strategy"] == "first_last"
    assert editorial["strategy"] == "edit_cut"
    assert risky_relay["strategy"] == "split_relay"
    assert risky_native["strategy"] == "native_multiframe"


def test_backend_duration_quantization_preserves_edit_target():
    veo = profiles.quantize_video_duration(5.1, "veo")
    dreamina = profiles.quantize_video_duration(2.1, "dreamina", model_version="3.0")
    native = profiles.quantize_video_duration(2.1, "dreamina", mode="native_multiframe")
    luma = profiles.quantize_video_duration(2.0, "luma")

    assert (veo["edit_target_sec"], veo["backend_request_sec"]) == (5.1, 6.0)
    assert (dreamina["edit_target_sec"], dreamina["backend_request_sec"]) == (2.1, 3.0)
    assert native["backend_request_sec"] == 2.1
    assert luma["backend_request_sec"] == 5.0
    assert all(row["trim_mode"] == "trim_tail" for row in (veo, dreamina, luma))


def test_anchor_consumption_plan_distinguishes_native_and_split():
    assert profiles.anchor_consumption_plan("dreamina", anchor_count=1, need_end=True)["consumption_mode"] == "native_multiframe"
    assert profiles.anchor_consumption_plan("kling", anchor_count=1, need_end=True)["consumption_mode"] == "split_relay"
    assert profiles.anchor_consumption_plan("seedance", anchor_count=1, need_end=True)["consumption_mode"] == "unsupported_mid_anchor"
    assert profiles.anchor_consumption_plan("某新后端2027", anchor_count=1, need_end=True)["consumption_mode"] == "unknown_manual_confirm"


def test_anchor_consumption_plan_never_invents_endframe():
    native = profiles.anchor_consumption_plan("dreamina", anchor_count=1, need_end=False)
    split = profiles.anchor_consumption_plan("kling", anchor_count=1, need_end=False)
    first = profiles.anchor_consumption_plan("kling", anchor_count=0, need_end=False)

    assert native["consumption_mode"] == "native_multiframe"
    assert native["consumes_endframe"] is False
    assert "first/mid/end" not in native["action"]
    assert split["consumption_mode"] == "split_relay"
    assert split["consumes_endframe"] is False
    assert first["consumption_mode"] == "first_frame"
    assert first["consumes_endframe"] is False


def test_sora_is_legacy_not_auto_routed_or_native_av():
    assert profiles.video_backend_auto_routable("sora") is False
    assert "sora" not in profiles.NATIVE_AV_BACKENDS
    info = profiles.video_backend_capability_confidence("sora")
    assert info["confidence"] == "deprecated"
    assert info["paid_routing_allowed"] is False


def test_capability_confidence_uses_execution_backend_channel():
    via_dreamina = profiles.video_backend_capability_confidence("Seedance 2.0", "即梦/Dreamina")
    direct_seedance = profiles.video_backend_capability_confidence("Seedance 2.0")
    assert via_dreamina["execution_backend"] == "dreamina"
    assert via_dreamina["confidence"] == "evidence"
    assert direct_seedance["confidence"] == "conservative"


def test_spectacle_backend_prior_ranking_orders_by_action_type():
    # 冷启动先验：打斗物理首选 kling，连续追逐首选 seedance，飞行/大场景首选 veo。
    assert profiles.spectacle_backend_prior_ranking("fight_exchange")[0] == "kling"
    assert profiles.spectacle_backend_prior_ranking("chase")[0] == "seedance"
    assert profiles.spectacle_backend_prior_ranking("flight")[0] == "veo"
    assert profiles.spectacle_backend_prior_ranking("large_establishing")[0] == "veo"
    # 不识别的类型 → 空 tuple
    assert profiles.spectacle_backend_prior_ranking("nope") == ()
    assert profiles.spectacle_backend_prior_ranking(None) == ()
    # 排序里只含 auto-routable 后端（sora 是 legacy，绝不出现在先验里）
    for st in profiles.SPECTACLE_BACKEND_PRIOR:
        ranking = profiles.spectacle_backend_prior_ranking(st)
        assert "sora" not in ranking
        assert all(profiles.video_backend_auto_routable(b) for b in ranking)


def test_wan_registered_as_self_host_multishot_backend():
    # G-V1：开源/自托管的原生多镜后端 Wan 入档，能力字段判定 → 被 multishot 识别（不 hardcode 厂商名）。
    assert profiles.video_backend_supports_multishot("wan") is True
    assert profiles.video_backend_supports_multishot("万相") is True   # 别名归一
    assert profiles.normalize_video_backend("Wan 2.6", default="") == "wan"


def test_native_multishot_set_includes_cloud_and_selfhost():
    # 云端(可灵/Seedance) + 自托管(Wan) 都在多镜原生集里。
    assert {"kling", "seedance", "wan"} <= set(profiles.MULTISHOT_NATIVE_BACKENDS)


def test_pixverse_c1_is_verified_manual_reference_to_video_candidate():
    assert profiles.video_backend_supports_multishot("PixVerse C1") is True
    assert profiles.video_backend_supports_reference_to_video("PixVerse C1") is True
    assert profiles.video_backend_auto_routable("PixVerse C1") is False


def test_single_take_multishot_capability_gate():
    assert profiles.single_take_multishot_supported("seedance", 12) is True
    assert profiles.single_take_multishot_supported("seedance", 20) is False
    assert profiles.single_take_multishot_supported("kling", 10) is True
    assert profiles.single_take_multishot_supported("luma", 4) is False
    assert profiles.single_take_multishot_supported("seedance", None) is True


def test_select_strategy_honors_take_policy_on_multishot_backend():
    plan = profiles.select_video_frame_strategy(
        "seedance", "", shot_count=3, anchor_count=2, need_end=True,
        take_policy="single_take_multishot", duration_sec=12,
    )
    assert plan["strategy"] == "single_take_multishot"
    assert plan["take_policy"] == "single_take_multishot"


def test_select_strategy_falls_back_to_edit_cut_when_unsupported():
    plan = profiles.select_video_frame_strategy(
        "luma", "", shot_count=3, anchor_count=2, need_end=True,
        take_policy="single_take_multishot", duration_sec=12,
    )
    assert plan["strategy"] in {"edit_cut", "edit_cut_pending_assets"}
    assert "fallback" in plan["reason"]
    over = profiles.select_video_frame_strategy(
        "seedance", "", shot_count=3, anchor_count=2, need_end=True,
        take_policy="single_take_multishot", duration_sec=22,
    )
    assert over["strategy"] in {"edit_cut", "edit_cut_pending_assets"}


def test_anchor_consumption_plan_single_take_mode():
    plan = profiles.anchor_consumption_plan(
        "seedance", "", anchor_count=2, need_end=False,
        frame_strategy="single_take_multishot",
    )
    assert plan["consumption_mode"] == "single_take_multishot"
    unsupported = profiles.anchor_consumption_plan(
        "luma", "", anchor_count=0, need_end=False,
        frame_strategy="single_take_multishot",
    )
    assert unsupported["consumption_mode"] == "unsupported_multishot_take"


def test_single_take_merge_ceiling_floor_and_capability():
    from n2d_platform_profiles import single_take_merge_ceiling_seconds
    # 未定/未知后端 → floor（历史 15s）；小上限后端不把合并压得比历史更碎。
    assert single_take_merge_ceiling_seconds("") == 15.0
    assert single_take_merge_ceiling_seconds("不存在的后端") == 15.0
    assert single_take_merge_ceiling_seconds("Veo 3.1") == 15.0  # veo 8s → floor 兜底
    assert single_take_merge_ceiling_seconds("Seedance 2.0") == 15.0  # 当前家族上限 15
    # floor 之上跟随已验后端能力（floor 缩小时能看到真实后端上限生效）。
    assert single_take_merge_ceiling_seconds("Veo 3.1", floor=6.0) == 8.0


def test_single_take_merge_ceiling_follows_capability_lift(monkeypatch):
    # 前向接线：per-run 证据把家族上限升到 30 后，合并上限自动跟进（不需改脚本层）。
    import n2d_platform_profiles as P
    monkeypatch.setitem(P.VIDEO_BACKEND_MAX_SECONDS, "seedance", 30)
    assert P.single_take_merge_ceiling_seconds("Seedance 2.5") == 30.0


def test_current_catalog_separates_seedance_advertised_capability_from_runnable_cap():
    seedance = profiles.video_backend_profile("Seedance 2.5")
    assert seedance["advertised_max_clip_seconds"] == 30
    assert seedance["max_clip_seconds"] == 15
    assert seedance["official_reference_limits"] == {"images": 30, "videos": 10, "audios": 10}
    assert seedance["availability"]["status"] == "product_rollout_api_pending"


def test_current_gemini_omni_model_id_is_not_stale_preview_alias():
    omni = profiles.video_backend_profile("Gemini Omni Flash")
    assert omni["default_model_version"] == "gemini-omni-flash"
    assert profiles.normalize_video_backend("gemini-omni-flash", default="") == "gemini_omni"
