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


def test_low_risk_short_multi_lens_clip_auto_collapses_to_single_take():
    # 拆镜经济性回修：低风险、纯镜位覆盖、跨度 ≤ 硬上限的多镜位短 Clip 默认合并为一次多镜生成，
    # 不再自动拆成多个独立付费 take，也不需要 storyboard 显式声明 take_policy。
    root = _mk_storyboard([{
        "id": "Clip_07",
        "duration": 5.0,
        "visual": "先看刀柄，再硬切到人物反应。",
        "shots": [
            {"t": "0-2s", "lens": "ECU", "description": "手握刀柄"},
            {"t": "2-5s", "lens": "CU", "description": "人物抬眼"},
        ],
        "continuity": {"shot_size": "ECU→CU", "need_endframe": True},
    }])

    row = SSD.build_plan(root, "第1集")["decisions"][0]

    assert row["primary_action"] == "single_take_multishot"
    assert row["single_take_multishot"] is True
    assert row["single_take_source"] == "auto_low_risk_editorial"
    assert "split_video_shots" not in row["actions"]
    assert row["video_shot_policy"]["direct_submit_allowed"] is True
    assert all(seg["reason"] == "single_take_multishot_internal_shot" and seg["physical_take"] is False
               for seg in row["video_shot_segments"])


def test_multi_lens_clip_opts_out_of_auto_single_take():
    # storyboard 显式 take_policy=split_each：尊重逐镜独立付费 take，不自动合并。
    root = _mk_storyboard([{
        "id": "Clip_07",
        "duration": 5.0,
        "take_policy": "split_each",
        "visual": "先看刀柄，再硬切到人物反应。",
        "shots": [
            {"t": "0-2s", "lens": "ECU", "description": "手握刀柄"},
            {"t": "2-5s", "lens": "CU", "description": "人物抬眼"},
        ],
        "continuity": {"shot_size": "ECU→CU", "need_endframe": True},
    }])

    row = SSD.build_plan(root, "第1集")["decisions"][0]

    assert row["single_take_multishot"] is False
    assert row["primary_action"] == "split_video_shots"
    assert [segment["duration_sec"] for segment in row["video_shot_segments"]] == [2.0, 3.0]
    assert all(segment["reason"] == "storyboard_editorial_cut" for segment in row["video_shot_segments"])


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


def test_take_policy_single_take_multishot_honored_for_normal_dialogue():
    root = _mk_storyboard([{
        "id": "Clip_01", "duration": 10.0, "take_policy": "single_take_multishot",
        "label": "小院对话", "scene": "山村小院",
        "shots": [
            {"t": [0, 4], "lens": "MS", "desc": "少年推门进院"},
            {"t": [4, 7], "lens": "MCU", "desc": "老人抬头"},
            {"t": [7, 10], "lens": "CU", "desc": "少年递出木牌"},
        ],
        "continuity": {"seam_mode": "hard_cut"},
    }])
    plan = SSD.build_plan(root, "第1集")
    d = plan["decisions"][0]
    assert d["single_take_multishot"] is True
    assert "single_take_multishot" in d["actions"]
    assert "split_video_shots" not in d["actions"]
    assert d["video_shot_policy"]["direct_submit_allowed"] is True
    assert all(seg["reason"] == "single_take_multishot_internal_shot" and seg["physical_take"] is False
               for seg in d["video_shot_segments"])
    assert plan["summary"]["single_take_multishot"] == 1


def test_take_policy_ignored_over_hard_max():
    root = _mk_storyboard([{
        "id": "Clip_01", "duration": 18.0, "take_policy": "single_take_multishot",
        "label": "超长镜", "continuity": {},
    }])
    plan = SSD.build_plan(root, "第1集")
    d = plan["decisions"][0]
    assert d["single_take_multishot"] is False
    assert "超过单次生成硬上限" in d["take_policy_ignored_reason"]
    assert "split_video_shots" in d["actions"]


def test_take_policy_ignored_for_spectacle_or_high_risk():
    root = _mk_storyboard([{
        "id": "Clip_01", "duration": 10.0, "take_policy": "single_take_multishot",
        "label": "妖狼扑杀打斗", "template": "fight_exchange",
        "shots": [
            {"t": [0, 5], "lens": "MS", "desc": "妖狼扑杀"},
            {"t": [5, 10], "lens": "CU", "desc": "格挡命中"},
        ],
        "continuity": {},
    }])
    plan = SSD.build_plan(root, "第1集")
    d = plan["decisions"][0]
    assert d["single_take_multishot"] is False
    assert "安全拆分与锚帧链优先" in d["take_policy_ignored_reason"]
    assert plan["summary"]["take_policy_ignored"] == 1


def test_high_action_clip_not_auto_collapsed_without_explicit_policy():
    # 无显式 take_policy 的高动作/奇观多镜位镜不得默认自动合并——安全拆分优先。
    root = _mk_storyboard([{
        "id": "Clip_01", "duration": 10.0,
        "label": "妖狼扑杀打斗", "template": "fight_exchange",
        "shots": [
            {"t": [0, 5], "lens": "MS", "desc": "妖狼扑杀"},
            {"t": [5, 10], "lens": "CU", "desc": "格挡命中"},
        ],
        "continuity": {},
    }])
    plan = SSD.build_plan(root, "第1集")
    d = plan["decisions"][0]
    assert d["single_take_multishot"] is False
    assert plan["summary"]["single_take_auto"] == 0
