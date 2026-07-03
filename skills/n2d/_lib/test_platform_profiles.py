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
    # 原生多帧 / 首尾档（可拆段凑≥3帧）→ 强制三帧
    assert p.backend_supports_three_plus_frames("dreamina") is True
    assert p.backend_supports_three_plus_frames("即梦") is True
    assert p.backend_supports_three_plus_frames("kling") is True
    assert p.backend_supports_three_plus_frames("veo") is True
    assert p.backend_supports_three_plus_frames("luma") is True
    # first-frame-only：视频消费能力不足；不代表图片阶段可省中段锚帧。
    assert p.backend_supports_three_plus_frames("seedance") is False
    assert p.backend_supports_three_plus_frames("sora") is False
    assert p.backend_supports_three_plus_frames("runway") is False
    assert p.backend_supports_three_plus_frames("pika") is False
    # 未知/缺省 → 需要刷新/探活/人工确认，不默认假定支持三帧
    assert p.backend_supports_three_plus_frames(None) is False
    assert p.backend_supports_three_plus_frames("某新后端2027") is False


def test_anchor_consumption_plan_distinguishes_native_and_split():
    assert profiles.anchor_consumption_plan("dreamina", anchor_count=1, need_end=True)["consumption_mode"] == "native_multiframe"
    assert profiles.anchor_consumption_plan("kling", anchor_count=1, need_end=True)["consumption_mode"] == "split_relay"
    assert profiles.anchor_consumption_plan("seedance", anchor_count=1, need_end=True)["consumption_mode"] == "unsupported_mid_anchor"
    assert profiles.anchor_consumption_plan("某新后端2027", anchor_count=1, need_end=True)["consumption_mode"] == "unknown_manual_confirm"


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
