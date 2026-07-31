"""combat_punch 单测——打斗命中帧微震屏（保时长·only fight/magic·有命中秒才加）。

cd skills/n2d/n2d-compose/scripts && python3 -m pytest test_combat_punch.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import combat_punch as cp  # noqa: E402


def test_punch_vf_basic_shape():
    vf = cp.punch_vf([1.8], 1080, 1920)
    assert vf.startswith("crop=") and vf.endswith("scale=1080:1920")
    assert "between(t\\,1.71\\,1.89)" in vf  # ±0.09 窗口·逗号已转义
    assert "sin(2*PI*40.0*t)" in vf and "cos(2*PI*33.0*t)" in vf


def test_punch_vf_multi_apex_sums_windows():
    vf = cp.punch_vf([2.0, 7.0], 1080, 1920)
    assert "between(t\\,1.91\\,2.09)+between(t\\,6.91\\,7.09)" in vf  # 多命中各一抖·求和


def test_punch_vf_amp_within_headroom_no_clamp():
    # 抖幅必须 ≤ headroom（保证 crop 偏移永不越界·无需 clip()）。
    w, h, zoom = 1080, 1920, cp.DEFAULT_ZOOM
    cw, ch = cp._even(w / zoom), cp._even(h / zoom)
    cx0, cy0 = (w - cw) / 2, (h - ch) / 2
    headroom = min(cx0, cy0)
    amp = round(min(headroom * 0.55, 14.0), 1)
    assert amp < headroom  # 偏移 cx0±amp ∈ [0, w-cw]
    assert f"+{amp}*sin" in cp.punch_vf([1.8], w, h)


def test_punch_vf_empty_when_no_apex_or_bad_size():
    assert cp.punch_vf([], 1080, 1920) == ""
    assert cp.punch_vf([1.8], 0, 0) == ""
    assert cp.punch_vf([1.8], 40, 40) == ""        # 太小·headroom<3 → 不抖
    assert cp.punch_vf([-1.0], 1080, 1920) == ""   # 非法秒


def test_clip_punch_fragment_only_combat_with_apex():
    fight = {"template": "fight_exchange", "duration": 6.0,
             "template_contract": {"impact_frame": "命中 1.8s"}}
    assert cp.clip_punch_fragment(fight, 1080, 1920).startswith("crop=")
    # magic_burst with collision
    magic = {"template": "magic_burst", "duration": 8.0,
             "template_contract": {"collision_or_apex_frame": "撞点 3.2s"}}
    assert cp.clip_punch_fragment(magic, 1080, 1920).startswith("crop=")
    # non-combat template → ""
    assert cp.clip_punch_fragment({"template": "dialogue", "duration": 6.0,
                                   "template_contract": {"impact_frame": "命中 1.8s"}}, 1080, 1920) == ""
    # combat but no apex sec → ""
    assert cp.clip_punch_fragment({"template": "fight_exchange", "duration": 6.0}, 1080, 1920) == ""


def test_clip_punch_fragment_uses_anchors():
    clip = {"template": "fight_exchange", "duration": 10.0,
            "continuity": {"anchors": [{"use": "keyframe", "at_sec": 2.0},
                                       {"use": "keyframe", "at_sec": 7.0}]}}
    vf = cp.clip_punch_fragment(clip, 720, 1280)
    assert "between(t\\,1.91\\,2.09)" in vf and "between(t\\,6.91\\,7.09)" in vf


def test_build_plan(tmp_path):
    import json
    sb = {"clips": [
        {"id": "C1", "template": "fight_exchange", "duration": 6.0,
         "template_contract": {"impact_frame": "命中 1.8s"}},
        {"id": "C2", "template": "dialogue", "duration": 5.0},
    ]}
    d = tmp_path / "脚本" / "第1集"
    d.mkdir(parents=True)
    (d / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    plan = cp.build_plan(str(tmp_path), "第1集", 1080, 1920)
    assert len(plan) == 1 and plan[0]["clip_index"] == 1 and plan[0]["apex_secs"] == [1.8]
