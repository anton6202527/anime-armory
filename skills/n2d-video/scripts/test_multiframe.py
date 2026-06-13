#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for video_runner multiframe2video logic. Run from skills/n2d-video/scripts/.

Pinned to the real `dreamina multiframe2video` CLI contract (snapshot in
references/cli_snapshots/dreamina/multiframe2video.txt):
  2 images  → --prompt + --duration
  3+ images → --transition-prompt ×(N-1) + --transition-duration ×(N-1)
  each segment ∈ [0.5,8]s; total ≥ 2; --images comma-separated.
"""
import json
import os

import video_runner as vr


# ── multiframe_segments (pure timing math) ──

def test_segments_from_one_anchor():
    # 6s clip, anchor at 3s → two 3s segments
    assert vr.multiframe_segments(6.0, [3.0]) == [3.0, 3.0]


def test_segments_from_two_anchors():
    assert vr.multiframe_segments(12.0, [4.0, 8.0]) == [4.0, 4.0, 4.0]


def test_segments_two_frames_no_anchor():
    # first+end only, 1 segment = whole clip
    assert vr.multiframe_segments(7.0, []) == [7.0]


def test_segment_too_long_raises():
    # 10s single segment > 8s cap → must add an anchor
    try:
        vr.multiframe_segments(10.0, [])
        assert False, "expected ValueError"
    except ValueError as e:
        assert "8" in str(e) and "anchor" in str(e)


def test_total_below_two_raises():
    try:
        vr.multiframe_segments(1.8, [])
        assert False, "expected ValueError"
    except ValueError as e:
        assert "total" in str(e)


def test_unordered_times_are_sorted():
    # robustness: out-of-order anchors are sorted, not rejected
    assert vr.multiframe_segments(6.0, [4.0, 2.0]) == [2.0, 2.0, 2.0]


def test_duplicate_times_raise():
    # two anchors at the same second → a zero-length segment → reject
    try:
        vr.multiframe_segments(6.0, [3.0, 3.0])
        assert False, "expected ValueError"
    except ValueError as e:
        assert "non-increasing" in str(e)


# ── _dreamina_multiframe_args (CLI argv) ──

def test_two_image_shorthand():
    args = vr._dreamina_multiframe_args(["a.png", "b.png"], [4.0], ["turn around"])
    assert args == ["dreamina", "multiframe2video", "--images", "a.png,b.png",
                    "--prompt", "turn around", "--duration", "4.0"]


def test_three_image_transition_form():
    args = vr._dreamina_multiframe_args(
        ["a.png", "b.png", "c.png"], [3.0, 3.0], ["A→B", "B→C"], poll=120)
    assert args[:4] == ["dreamina", "multiframe2video", "--images", "a.png,b.png,c.png"]
    assert args.count("--transition-prompt") == 2
    assert args.count("--transition-duration") == 2
    # order: prompts then durations
    assert "A→B" in args and "B→C" in args
    assert args[-2:] == ["--poll", "120"]


def test_bad_image_count_raises():
    try:
        vr._dreamina_multiframe_args(["a.png"], [], [])
        assert False
    except ValueError as e:
        assert "2-20" in str(e)


def test_transition_count_mismatch_raises():
    try:
        vr._dreamina_multiframe_args(["a.png", "b.png", "c.png"], [3.0, 3.0], ["only one"])
        assert False
    except ValueError as e:
        assert "transition prompts" in str(e)


# ── clip_anchor_index + attach_multiframe + dispatch (integration) ──

def _make_clip_project(tmp_path, *, duration, anchors, make_pngs=True, end=True):
    root = tmp_path / "work"
    sb_dir = root / "脚本" / "第1集"
    img_dir = root / "出图" / "第1集" / "图片"
    sb_dir.mkdir(parents=True)
    img_dir.mkdir(parents=True)
    cont = {"start_state": "s", "end_state": "e", "transition": "硬切",
            "need_endframe": end}
    if end:
        cont["endframe_png"] = "出图/第1集/图片/Clip_01_end.png"
    if anchors is not None:
        cont["anchors"] = anchors
    sb = {"episode": 1, "policy": {"tailframe_default": True},
          "clips": [{"id": "EP01_CLIP01", "duration": duration,
                     "firstframe_png": "出图/第1集/图片/Clip_01.png", "continuity": cont}]}
    (sb_dir / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    if make_pngs:
        for name in ["Clip_01.png", "Clip_01_end.png", "Clip_01_a1.png", "Clip_01_mid.png"]:
            (img_dir / name).write_bytes(b"x")
    return root


def _item(root, *, end=True):
    img = root / "出图" / "第1集" / "图片"
    it = {"clip": "Clip_01", "image": str((img / "Clip_01.png").resolve()),
          "image_rel": "出图/第1集/图片/Clip_01.png", "story_duration": 6.0}
    if end:
        it["end_image"] = str((img / "Clip_01_end.png").resolve())
        it["end_image_rel"] = "出图/第1集/图片/Clip_01_end.png"
    return it


def test_clip_anchor_index_reads_anchors(tmp_path):
    root = _make_clip_project(tmp_path, duration=6.0, anchors=[
        {"anchor_png": "出图/第1集/图片/Clip_01_a1.png", "at_sec": 3.0, "use": "split", "reason": "中间拍"}])
    idx = vr.clip_anchor_index(root, "第1集")
    assert idx[1]["times"] == [3.0] and idx[1]["images"] == ["出图/第1集/图片/Clip_01_a1.png"]


def test_attach_multiframe_builds_three_keyframes(tmp_path):
    root = _make_clip_project(tmp_path, duration=6.0, anchors=[
        {"anchor_png": "出图/第1集/图片/Clip_01_a1.png", "at_sec": 3.0, "use": "split", "reason": "中间拍：抬眼"}])
    idx = vr.clip_anchor_index(root, "第1集")
    item = _item(root)
    vr.attach_multiframe(root, item, "推近 沈念抬眼", idx)
    assert item["mode_backend"] == "multiframe2video"
    assert len(item["multiframe_images"]) == 3  # first + a1 + end
    assert item["multiframe_segment_durations"] == [3.0, 3.0]
    assert len(item["multiframe_segment_prompts"]) == 2
    # dispatch produces a valid multiframe2video argv
    pf = root / "p.txt"; pf.write_text("推近 沈念抬眼", encoding="utf-8")
    item["prompt_file"] = str(pf)
    argv = vr._dreamina_args(item, {"poll": 0})
    assert argv[1] == "multiframe2video" and argv.count("--transition-prompt") == 2


def test_attach_multiframe_uses_qc_anchors_too(tmp_path):
    # capability-driven: a use=qc anchor still becomes a real keyframe for multiframe2video
    # (segments only need ≥0.5s; the old ≥4s relay floor no longer applies)
    root = _make_clip_project(tmp_path, duration=6.0, anchors=[
        {"anchor_png": "出图/第1集/图片/Clip_01_mid.png", "at_sec": 3.0, "use": "qc", "reason": "qc 基准"}])
    idx = vr.clip_anchor_index(root, "第1集")
    item = _item(root)
    vr.attach_multiframe(root, item, "prompt", idx)
    assert item.get("mode_backend") == "multiframe2video"
    assert len(item["multiframe_images"]) == 3  # first + mid + end


def test_attach_multiframe_skips_when_png_missing(tmp_path):
    root = _make_clip_project(tmp_path, duration=6.0, make_pngs=False, anchors=[
        {"anchor_png": "出图/第1集/图片/Clip_01_a1.png", "at_sec": 3.0, "use": "split", "reason": "x"}])
    # only create first+end, not the anchor
    img = root / "出图" / "第1集" / "图片"
    (img / "Clip_01.png").write_bytes(b"x"); (img / "Clip_01_end.png").write_bytes(b"x")
    idx = vr.clip_anchor_index(root, "第1集")
    item = _item(root)
    vr.attach_multiframe(root, item, "prompt", idx)
    assert "multiframe_images" not in item
    assert "not yet generated" in item["multiframe_skip"]


def test_attach_multiframe_skips_no_end_frame(tmp_path):
    root = _make_clip_project(tmp_path, duration=6.0, end=False, anchors=[
        {"anchor_png": "出图/第1集/图片/Clip_01_a1.png", "at_sec": 3.0, "use": "split", "reason": "x"}])
    idx = vr.clip_anchor_index(root, "第1集")
    item = _item(root, end=False)
    vr.attach_multiframe(root, item, "prompt", idx)
    assert "multiframe_images" not in item and "end frame" in item["multiframe_skip"]


# ── 转场 prompt 用 beats 真运动，不用规划器 reason 元数据（R1 打斗质量关键）──

def test_beat_hint_at_maps_time_to_beat():
    clip = {"duration": 15, "template_contract": {"beats": ["起手", "逼近", "命中", "受击", "收势"]}}
    assert vr.beat_hint_at(clip, 0) == "起手"
    assert vr.beat_hint_at(clip, 6) == "命中"
    assert vr.beat_hint_at(clip, 14.9) == "收势"
    # 无 beats → 空（attach_multiframe 回退到 Clip 主 prompt）
    assert vr.beat_hint_at({"duration": 6}, 3) == ""


def test_fight_transition_prompts_use_beats_not_metadata(tmp_path):
    root = _make_clip_project(tmp_path, duration=15.0, anchors=[
        {"anchor_png": "出图/第1集/图片/Clip_01_a1.png", "at_sec": 3, "use": "split",
         "reason": "auto: R1 高运动模板 fight_exchange（15s/5拍）"},
        {"anchor_png": "出图/第1集/图片/Clip_01_a2.png", "at_sec": 9, "use": "split",
         "reason": "auto: R1 ..."},
    ])
    # 给 clip 加打斗 beats（_make_clip_project 默认不写 template_contract，这里补上）
    import json
    sb_path = tmp_path / "work" / "脚本" / "第1集" / "storyboard.json"
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    sb["clips"][0]["template_contract"] = {"beats": ["起手", "命中", "收势"]}
    sb_path.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    img = root / "出图" / "第1集" / "图片"
    (img / "Clip_01_a1.png").write_bytes(b"x"); (img / "Clip_01_a2.png").write_bytes(b"x")

    idx = vr.clip_anchor_index(root, "第1集")
    item = _item(root); item["story_duration"] = 15.0
    vr.attach_multiframe(root, item, "打斗 力链", idx)
    prompts = item["multiframe_segment_prompts"]
    # 每段 prompt 来自 beats，绝不含 "auto:" 规划元数据
    assert all("auto:" not in p for p in prompts), prompts
    assert "命中" in prompts or "收势" in prompts, prompts


def test_last_segment_prompt_uses_end_state(tmp_path):
    # #7：末段转场 prompt 用 Clip 的 end_state（具体落幅），不是泛化句
    root = _make_clip_project(tmp_path, duration=6.0, anchors=[
        {"anchor_png": "出图/第1集/图片/Clip_01_a1.png", "at_sec": 3.0, "use": "split"}])
    import json
    sb_path = tmp_path / "work" / "脚本" / "第1集" / "storyboard.json"
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    sb["clips"][0]["continuity"]["end_state"] = "沈念起身扶榻、视线移向窗"
    sb_path.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    (root / "出图" / "第1集" / "图片" / "Clip_01_a1.png").write_bytes(b"x")
    idx = vr.clip_anchor_index(root, "第1集")
    item = _item(root)
    vr.attach_multiframe(root, item, "推近", idx)
    assert item["multiframe_segment_prompts"][-1] == "沈念起身扶榻、视线移向窗"
    assert "承接进行中的动作" not in item["multiframe_segment_prompts"][-1]
