#!/usr/bin/env python3
"""Tests for shot_split_decision.py."""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import shot_split_decision as SSD  # noqa: E402


def _mk_storyboard(clips):
    root = Path(tempfile.mkdtemp())
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({"clips": clips}, ensure_ascii=False), encoding="utf-8")
    return root


def test_low_risk_keeps_single():
    root = _mk_storyboard([{
        "id": "Clip_01",
        "duration": 3,
        "visual": "沈念推门，烛火微动。",
        "continuity": {"shot_size": "MS", "need_endframe": True, "midframe_exempt_reason": "短镜"},
    }])

    plan = SSD.build_plan(root, "第1集")

    assert plan["ok"]
    assert plan["decisions"][0]["primary_action"] == "keep_single"


def test_multi_talking_closeup_splits_reaction():
    root = _mk_storyboard([{
        "id": "Clip_02",
        "duration": 5,
        "character_ids": ["CHAR_01", "CHAR_02"],
        "native_speech": "你为何骗我？",
        "visual": "双人同框近景对峙说话。",
        "character_slots": [
            {"slot": "LEFT_SLOT", "character": "CHAR_01"},
            {"slot": "RIGHT_SLOT", "character": "CHAR_02"},
        ],
        "same_frame_policy": "shot_reverse_shot",
        "continuity": {"shot_size": "CU 正反打", "need_endframe": True, "midframe": {"midframe_png": "x"}},
    }])

    action = SSD.build_plan(root, "第1集")["decisions"][0]["primary_action"]

    assert action == "split_reaction"


def test_spectacle_template_is_required():
    root = _mk_storyboard([{
        "id": "Clip_03",
        "duration": 6,
        "template": "soul_manifestation",
        "visual": "元神从肉身上方显化，神魂攻击压来。",
        "continuity": {"shot_size": "LS", "need_endframe": True, "midframe": {"midframe_png": "x"}},
    }])

    row = SSD.build_plan(root, "第1集")["decisions"][0]

    assert "template_required" in row["actions"]


def test_high_risk_without_anchor_adds_anchor():
    root = _mk_storyboard([{
        "id": "Clip_04",
        "duration": 10,
        "visual": "角色怒吼说话，表情跨度极大。",
        "native_speech": "你们都退下！",
        "continuity": {"shot_size": "CU", "expression_span": "大", "need_endframe": True},
    }])

    row = SSD.build_plan(root, "第1集")["decisions"][0]

    assert "add_mid_or_multi_anchor" in row["actions"]


def test_long_story_clip_gets_video_shot_segments():
    root = _mk_storyboard([{
        "id": "Clip_04",
        "duration": 33.363,
        "visual": "看见掌心刀法，姜月初判断身份死局，官道远景落幅。",
        "continuity": {"shot_size": "MS", "need_endframe": True},
    }])

    row = SSD.build_plan(root, "第1集")["decisions"][0]

    assert row["primary_action"] == "compress_before_video"
    assert "split_video_shots" in row["actions"]
    assert row["video_shot_policy"]["direct_submit_allowed"] is False
    assert len(row["video_shot_segments"]) == 6
    assert all(seg["duration_sec"] <= 8 for seg in row["video_shot_segments"])
    assert row["story_economy"]["detail_allowed"] is False


def test_long_fight_clip_keeps_detail_but_splits_video_shots():
    root = _mk_storyboard([{
        "id": "Clip_06",
        "duration": 18.0,
        "template": "fight_exchange",
        "visual": "狼妖弹爪扑杀，姜月初拔刀格挡，命中后众人反应。",
        "continuity": {"shot_size": "MS", "need_endframe": True},
    }])

    row = SSD.build_plan(root, "第1集")["decisions"][0]

    assert row["primary_action"] == "split_video_shots"
    assert "compress_before_video" not in row["actions"]
    assert row["story_economy"]["economy_class"] == "premium_detail"


def test_plain_prop_does_not_force_composite():
    root = _mk_storyboard([{
        "id": "Clip_05",
        "duration": 4,
        "object_ids": ["PROP_急报卷轴"],
        "visual": "急报卷轴落在案几上。",
        "continuity": {"shot_size": "MS", "need_endframe": True, "midframe_exempt_reason": "短道具镜"},
    }])

    row = SSD.build_plan(root, "第1集")["decisions"][0]

    assert "defer_to_composite" not in row["actions"]


def test_write_outputs():
    root = _mk_storyboard([{
        "id": "Clip_01",
        "duration": 3,
        "continuity": {"shot_size": "MS", "need_endframe": True, "midframe_exempt_reason": "短镜"},
    }])
    plan = SSD.build_plan(root, "第1集")
    jp, mp = SSD.write_outputs(root, "第1集", plan)

    assert jp.exists()
    assert mp.exists()
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == SSD.KIND


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
