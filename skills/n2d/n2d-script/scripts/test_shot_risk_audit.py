#!/usr/bin/env python3
"""Tests for shot_risk_audit.py."""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import shot_risk_audit as SRA  # noqa: E402


def _mk_storyboard(clips):
    d = tempfile.mkdtemp()
    ep = Path(d) / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({"clips": clips}, ensure_ascii=False), encoding="utf-8")
    return d


def test_low_risk_clip_passes():
    root = _mk_storyboard([{
        "id": "EP01_CLIP01",
        "duration": 4,
        "continuity": {"shot_size": "MS", "need_endframe": True, "midframe_exempt_reason": "短镜"},
        "shots": [{"desc": "沈念推门进入，烛火微动"}],
    }])

    result = SRA.audit(root, "第1集")

    assert result["ok"]
    assert result["summary"]["max_score"] < 6


def test_low_light_ambience_does_not_infer_stealth_stalk():
    root = _mk_storyboard([{
        "id": "EP01_CLIP02",
        "duration": 4,
        "continuity": {"shot_size": "MS", "need_endframe": True, "midframe_exempt_reason": "短镜"},
        "shots": [{"desc": "王敦只露下半张脸在暗处，狱卒灯笼冷光扫过地砖。"}],
    }])

    result = SRA.audit(root, "第1集")
    clip = result["clips"][0]

    assert result["ok"]
    assert clip["spectacle_type"] is None
    assert "spectacle_stealth_stalk" not in clip["tags"]


def test_active_stalking_still_infers_stealth_stalk():
    root = _mk_storyboard([{
        "id": "EP01_CLIP03",
        "duration": 4,
        "continuity": {"shot_size": "MS", "need_endframe": True, "midframe_exempt_reason": "短镜"},
        "shots": [{"desc": "黑衣人尾随女主穿过暗走廊，借门缝和脚步声逼近。"}],
    }])

    result = SRA.audit(root, "第1集")
    clip = result["clips"][0]

    assert clip["spectacle_type"] == "stealth_stalk"
    assert "spectacle_stealth_stalk" in clip["tags"]


def test_closed_door_retreat_reference_does_not_infer_meditation():
    root = _mk_storyboard([{
        "id": "EP01_CLIP04",
        "duration": 4,
        "continuity": {"shot_size": "LS", "need_endframe": True, "midframe_exempt_reason": "短镜"},
        "shots": [{"desc": "远处老祖闭关石门震开，红色城阵像大网扣住街巷。"}],
    }])

    result = SRA.audit(root, "第1集")
    clip = result["clips"][0]

    assert result["ok"]
    assert clip["spectacle_type"] is None
    assert "spectacle_meditation_cultivation" not in clip["tags"]


def test_visible_breathing_cultivation_still_infers_meditation():
    root = _mk_storyboard([{
        "id": "EP01_CLIP05",
        "duration": 4,
        "continuity": {"shot_size": "MS", "need_endframe": True, "midframe_exempt_reason": "短镜"},
        "shots": [{"desc": "少年闭关打坐，吐纳三息，青白灵气沿丹田周天流转。"}],
    }])

    result = SRA.audit(root, "第1集")
    clip = result["clips"][0]

    assert clip["spectacle_type"] == "meditation_cultivation"
    assert "spectacle_meditation_cultivation" in clip["tags"]


def test_multi_subject_without_slots_or_strategy_is_must():
    root = _mk_storyboard([{
        "id": "EP01_CLIP09",
        "duration": 6,
        "character_ids": ["CHAR_01", "CHAR_02", "CHAR_03", "CHAR_04"],
        "continuity": {"shot_size": "CU", "need_endframe": True, "midframe": {"midframe_png": "x", "split_at_sec": 3, "reason": "test"}},
        "shots": [{"desc": "四人同框近景对峙"}],
    }])

    result = SRA.audit(root, "第1集")

    assert not result["ok"]
    assert any(f["code"] == "multi_subject_missing_slots_or_strategy" for f in result["findings"])


def test_offscreen_character_does_not_trigger_multi_subject_gate():
    root = _mk_storyboard([{
        "id": "EP01_CLIP10",
        "duration": 4,
        "continuity": {"shot_size": "CU", "midframe_exempt_reason": "短镜"},
        "entity_schedule": {
            "characters": ["CHAR_01", "CHAR_02"],
            "required_presence": ["CHAR_01"],
            "offscreen_presence": ["CHAR_02"],
            "forbidden_presence": [],
        },
        "shots": [{"desc": "CHAR_01 单人近景，CHAR_02 只有画外声"}],
    }])

    result = SRA.audit(root, "第1集")

    assert result["ok"]
    assert not any(f["code"] == "multi_subject_missing_slots_or_strategy" for f in result["findings"])


def test_high_motion_long_clip_without_anchor_warns():
    root = _mk_storyboard([{
        "id": "EP01_CLIP03",
        "duration": 10,
        "template": "fight_exchange",
        "continuity": {"shot_size": "MS", "need_endframe": True},
        "shots": [{"desc": "沈念疾驰翻滚，剑气命中敌人"}],
    }])

    result = SRA.audit(root, "第1集")

    assert result["ok"]
    assert any(f["code"] == "high_risk_without_mid_anchor" for f in result["findings"])
    assert result["pilot_candidates"][0]["id"] == "EP01_CLIP03"


def test_spectacle_type_risk_is_typed():
    root = _mk_storyboard([{
        "id": "EP01_CLIP04",
        "duration": 6,
        "template": "flight",
        "continuity": {"shot_size": "WS", "need_endframe": True},
        "shots": [{"desc": "腾云驾雾穿过云海，山体快速后退"}],
    }])

    result = SRA.audit(root, "第1集")
    clip = result["clips"][0]

    assert clip["spectacle_type"] == "flight"
    assert "spectacle_flight" in clip["tags"]
    assert any("altitude" in rec or "altitude" in str(rec).lower() for rec in clip["recommendations"])


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
