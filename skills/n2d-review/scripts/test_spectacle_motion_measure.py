#!/usr/bin/env python3
"""Tests for spectacle_motion_measure pure logic (no cv2/numpy needed).

cd skills/n2d-review/scripts && python -m pytest test_spectacle_motion_measure.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import spectacle_motion_measure as smm  # noqa: E402


def test_dominant_flow_direction_static_and_axes():
    assert smm.dominant_flow_direction(0.0, 0.0, 0.0, 0.1) == "static"
    assert smm.dominant_flow_direction(5.0, 0.5, 0.0, 5.0) == "right"
    assert smm.dominant_flow_direction(-5.0, 0.5, 0.0, 5.0) == "left"
    assert smm.dominant_flow_direction(0.5, 5.0, 0.0, 5.0) == "down"
    assert smm.dominant_flow_direction(0.5, -5.0, 0.0, 5.0) == "up"


def test_dominant_flow_direction_zoom():
    assert smm.dominant_flow_direction(0.2, 0.2, 6.0, 6.0) == "zoom_in"
    assert smm.dominant_flow_direction(0.2, 0.2, -6.0, 6.0) == "zoom_out"


def test_parse_camera_path_direction():
    assert "zoom_in" in smm.parse_camera_path_direction("缓慢推镜怼脸")
    assert "right" in smm.parse_camera_path_direction("pan left to right")
    assert "up" in smm.parse_camera_path_direction("crane up 无人机升起")
    assert smm.parse_camera_path_direction("固定机位") == []


def test_flow_intent_match():
    # 声明推镜，实测 zoom_in → 一致。
    assert smm.flow_intent_match("zoom_in", "缓慢推镜") is True
    # 声明推镜，实测左移 → 不一致。
    assert smm.flow_intent_match("left", "缓慢推镜") is False
    # 声明有方向但实测静止 → 不一致（说动了没动）。
    assert smm.flow_intent_match("static", "pan right") is False
    # 无方向声明 → None（不罚）。
    assert smm.flow_intent_match("right", "") is None


def test_motion_blur_plausibility():
    # 低光流但很糊（静帧发虚）= 不合理；高光流糊 = 合理。
    samples = [(0.1, 5.0), (0.1, 6.0), (8.0, 5.0), (9.0, 4.0)]
    score = smm.motion_blur_plausibility(samples)
    assert score is not None and 0.0 <= score <= 1.0
    # 全部清晰且不动 → 全合理。
    assert smm.motion_blur_plausibility([(0.1, 100.0), (0.1, 110.0)]) == 1.0
    # 样本不足 → None。
    assert smm.motion_blur_plausibility([(1.0, 50.0)]) is None


def test_limb_artifact():
    # 应在场 1 人，多帧检出 2 人 → 多人/多肢嫌疑。
    res = smm.limb_artifact([1, 2, 2, 1], expected_persons=1)
    assert res is not None and res["score"] == 0.5 and res["extra"] == 1
    # 无检测结果或无应在场人数 → None（不臆造）。
    assert smm.limb_artifact([], 1) is None
    assert smm.limb_artifact([1, 1], 0) is None


def test_sample_frame_indices():
    idxs = smm.sample_frame_indices(100, {"base_uniform_frames": 6})
    assert idxs[0] == 0 and idxs[-1] == 99
    assert idxs == sorted(set(idxs))
    assert smm.sample_frame_indices(0, {}) == []


def test_story_clip_id_prefers_clip_number_over_episode_number():
    assert smm._story_clip_id("EP02_CLIP03", 1) == "Clip_03"
    assert smm._story_clip_id("Clip 10", 1) == "Clip_10"
    assert smm._story_clip_id("", 4) == "Clip_04"


def test_clip_media_uses_formal_chinese_video_dir(tmp_path):
    root = tmp_path / "剧"
    video_dir = root / "出视频" / "第2集" / "视频"
    video_dir.mkdir(parents=True)
    wrong = video_dir / "Clip_02_虎妖嘲讽.mp4"
    right = video_dir / "Clip_03_二十年尽压一刀.mp4"
    wrong.write_bytes(b"wrong")
    right.write_bytes(b"right")

    assert smm._clip_media(str(root), "第2集", "Clip_03") == str(right)


def test_measure_degrades_without_cv2(tmp_path):
    # 无 cv2/numpy 时不崩，给安装提示，ok=False。
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "脚本" / "第1集" / "storyboard.json").write_text(
        '{"clips": [{"id": "Clip 1", "template": "fight_exchange"}]}', encoding="utf-8")
    res = smm.measure(str(root), "第1集")
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
        has = True
    except Exception:
        has = False
    if not has:
        assert res["ok"] is False
        assert any("环境未就绪" in n for n in res["notes"])
