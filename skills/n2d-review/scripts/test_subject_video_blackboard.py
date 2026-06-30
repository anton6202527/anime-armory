#!/usr/bin/env python3
"""subject_video_consistency 不读黑板派生动作字段。
cd skills/n2d-review/scripts && python -m pytest test_subject_video_blackboard.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "n2d", "_lib"))
import subject_video_consistency as svc
import n2d_intent as ni


def test_high_motion_ignores_blackboard_derived_motion_edits(tmp_path):
    ep = "第1集"
    ep_dir = tmp_path / "脚本" / ep
    ep_dir.mkdir(parents=True)
    # storyboard：两镜都中性，无动作信号 → 派生空集
    (ep_dir / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "Clip_01", "description": "他静静站着"},
        {"id": "Clip_02", "description": "空镜远景"},
    ]}, ensure_ascii=False), encoding="utf-8")
    assert svc._high_motion_clips(str(tmp_path), ep) == set()
    # 手改黑板声明 Clip_01 高动作：motion_intensity 是 storyboard 派生投影，应被忽略。
    ni.write_shot_intent(str(tmp_path), ep)
    obj = ni.load_shot_intent(str(tmp_path), ep)
    obj["shots"][0]["motion_intensity"] = "高"
    (ep_dir / "shot_intent.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    assert svc._high_motion_clips(str(tmp_path), ep) == set()
