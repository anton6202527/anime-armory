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
    # first-frame-only：唯一豁免
    assert p.backend_supports_three_plus_frames("seedance") is False
    assert p.backend_supports_three_plus_frames("sora") is False
    assert p.backend_supports_three_plus_frames("runway") is False
    assert p.backend_supports_three_plus_frames("pika") is False
    # 未知/缺省 → 向前看默认假定支持（强制）
    assert p.backend_supports_three_plus_frames(None) is True
    assert p.backend_supports_three_plus_frames("某新后端2027") is True
