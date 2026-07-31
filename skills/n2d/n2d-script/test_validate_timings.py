#!/usr/bin/env python3
"""Tests for validate_timings deterministic helpers.

Run from this directory:
    cd skills/n2d/n2d-script && python3 -m pytest test_validate_timings.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importing the module triggers its own sys.path.insert for ../common.
import validate_timings as V  # noqa: E402
import validate_storyboard_contract as VC  # noqa: E402
from voice_preproduction import build_timing_estimate, timing_path  # noqa: E402


_SRT = (
    "1\n"
    "00:00:00,000 --> 00:00:02,500\n"
    "第一句中文\n"
    "First line\n"
    "\n"
    "2\n"
    "00:00:02,500 --> 00:00:05,000\n"
    "第二句中文\n"
    "Second line\n"
)


# ── srt_blocks / _srt_text ──
def test_srt_blocks_count(tmp_path):
    p = tmp_path / "sub.srt"
    p.write_text(_SRT, encoding="utf-8")
    blocks = V.srt_blocks(str(p))
    assert len(blocks) == 2


def test_srt_blocks_missing_file():
    assert V.srt_blocks("/nonexistent/path/x.srt") == []


def test_srt_text_extracts_text_lines(tmp_path):
    p = tmp_path / "sub.srt"
    p.write_text(_SRT, encoding="utf-8")
    blocks = V.srt_blocks(str(p))
    txt = V._srt_text(blocks[0])
    # index line + timecode stripped; text lines (3rd onward) joined
    assert "第一句中文" in txt
    assert "First line" in txt
    assert "00:00:00" not in txt


# ── _is_placeholder_en_blocks ──
def test_is_placeholder_en_blocks_true():
    placeholder = (
        "1\n00:00:00,000 --> 00:00:02,000\n"
        "English subtitles for overseas platforms (TODO placeholder)\n"
    )
    blocks = placeholder.strip().split("\n\n")
    # Build blocks the same way srt_blocks would (single block here)
    assert V._is_placeholder_en_blocks([placeholder.strip()]) is True


def test_is_placeholder_en_blocks_false_real_text(tmp_path):
    p = tmp_path / "en.srt"
    p.write_text(_SRT, encoding="utf-8")
    blocks = V.srt_blocks(str(p))
    assert V._is_placeholder_en_blocks(blocks) is False


def test_is_placeholder_en_blocks_empty():
    assert V._is_placeholder_en_blocks([]) is False


# ── srt_last_end time math ──
def test_srt_last_end_value(tmp_path):
    p = tmp_path / "sub.srt"
    p.write_text(_SRT, encoding="utf-8")
    last = V.srt_last_end(str(p))
    # last block ends at 00:00:05,000 = 5.0s
    assert abs(last - 5.0) < 1e-6


def test_srt_last_end_missing():
    assert V.srt_last_end("/nonexistent/x.srt") is None


def test_validate_no_wav_timing_estimate_passes_with_explicit_warning(tmp_path, capsys):
    root = Path(tmp_path)
    ep = "第1集"
    script = root / "脚本" / ep
    script.mkdir(parents=True)
    (script / "voiceover.txt").write_text("[镜头1·旁白·克制] 夜色压下来。\n", encoding="utf-8")
    payload = build_timing_estimate(root, ep)
    path = timing_path(root, ep)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    line = payload["lines"][0]
    (script / "镜头时长.json").write_text(
        json.dumps({"镜头1": line["时长"] + line["gap_after"]}, ensure_ascii=False), encoding="utf-8"
    )
    (script / "字幕_中文.srt").write_text(
        f"1\n00:00:00,000 --> 00:00:{line['end']:06.3f}\n夜色压下来。\n".replace(".", ",", 1),
        encoding="utf-8",
    )

    code = V._validate_estimated_timing(
        str(root), ep, str(script / "镜头时长.json"), str(script / "字幕_中文.srt"), 0.5,
    )

    assert code == 0
    assert "不是最终配音" in capsys.readouterr().out
    assert not list(root.rglob("*.wav"))


# ── _validate_native_av branch ──
def _make_native(root, ep, shots, clips):
    sdir = os.path.join(root, "脚本", ep)
    os.makedirs(sdir, exist_ok=True)
    shots_p = os.path.join(sdir, "镜头时长.json")
    json.dump(shots, open(shots_p, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"clips": clips},
              open(os.path.join(sdir, "storyboard.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    return shots_p


def test_native_av_pass_when_matching(tmp_path, capsys):
    root, ep = str(tmp_path), "第1集"
    # ∑镜头时长 = 5.0; ∑clip.duration = 5.0 → within tol → rc 0
    shots_p = _make_native(root, ep,
                           {"镜头1": 2.0, "镜头2": 3.0},
                           [{"duration": 2.0}, {"duration": 3.0}])
    rc = V._validate_native_av(root, ep, shots_p, 0.5)
    assert rc == 0


def test_native_av_fail_when_mismatched(tmp_path):
    root, ep = str(tmp_path), "第1集"
    # ∑镜头时长 = 5.0; ∑clip.duration = 8.0 → diff 3.0 > tol → rc 1
    shots_p = _make_native(root, ep,
                           {"镜头1": 2.0, "镜头2": 3.0},
                           [{"duration": 4.0}, {"duration": 4.0}])
    rc = V._validate_native_av(root, ep, shots_p, 0.5)
    assert rc == 1


def test_native_av_missing_shots_file_fails(tmp_path):
    root, ep = str(tmp_path), "第1集"
    shots_p = os.path.join(root, "脚本", ep, "镜头时长.json")  # not created
    rc = V._validate_native_av(root, ep, shots_p, 0.5)
    assert rc == 1


# ── per_shot_overflow（逐镜头真音超槽预检，与 compose 拟合同 max_stretch 口径）──
def test_per_shot_overflow_flags_single_shot_over_stretch():
    # 镜头1 真音 5.0 > 槽位 3.0×1.25=3.75 → overflow；镜头2 在容忍内
    man = [{"镜头": "镜头1", "时长": 5.0, "gap_after": 0.0},
           {"镜头": "镜头2", "时长": 2.0, "gap_after": 0.0}]
    shots = {"镜头1": 3.0, "镜头2": 2.0}
    ov = V.per_shot_overflow(man, shots, 1.25)
    assert [o[0] for o in ov] == ["镜头1"]
    assert ov[0][1] == 5.0 and ov[0][2] == 3.0


def test_per_shot_overflow_total_cancels_but_single_overflows():
    # ∑真音 = ∑槽位 = 8.0（总长校验会通过），但镜头1 单镜溢出 → 仍被逐镜抓出
    man = [{"镜头": "镜头1", "时长": 5.0}, {"镜头": "镜头2", "时长": 3.0}]
    shots = {"镜头1": 3.0, "镜头2": 5.0}
    assert sum(r["时长"] for r in man) == sum(shots.values())  # 总长相等
    ov = V.per_shot_overflow(man, shots, 1.25)
    assert [o[0] for o in ov] == ["镜头1"]


def test_per_shot_overflow_aggregates_multi_line_shot_with_gap():
    # 单镜多句：聚合 ∑(时长+gap) = 2+0.5+2 = 4.5 > 3.0×1.25 → overflow
    man = [{"镜头": "镜头1", "时长": 2.0, "gap_after": 0.5},
           {"镜头": "镜头1", "时长": 2.0, "gap_after": 0.0}]
    shots = {"镜头1": 3.0}
    ov = V.per_shot_overflow(man, shots, 1.25)
    assert ov and ov[0][0] == "镜头1" and ov[0][1] == 4.5


def test_per_shot_overflow_within_stretch_is_clean():
    # 真音 3.5 ≤ 3.0×1.25=3.75 → 不报（与 compose stretch 档一致，不是 overflow）
    man = [{"镜头": "镜头1", "时长": 3.5}]
    shots = {"镜头1": 3.0}
    assert V.per_shot_overflow(man, shots, 1.25) == []


# ── target-duration deviation WARN (Fix 2) ──
def test_target_deviation_warn_none_without_target():
    # 不给 target → 无新行为（向后兼容）
    assert V.target_deviation_warn(90.0, None) is None
    assert V.target_deviation_warn(90.0, 0) is None


def test_target_deviation_warn_within_tolerance():
    # 偏离在 15% 内 → 不 WARN
    assert V.target_deviation_warn(95.0, 90.0) is None  # ~5.6%


def test_target_deviation_warn_too_short():
    # ∑镜头时长 远短于软节奏意图 → WARN（偏短），不是硬闸门。
    msg = V.target_deviation_warn(50.0, 90.0)  # ~44% short
    assert msg is not None and "偏短" in msg and "软节奏意图" in msg and "WARN" in msg


def test_target_deviation_warn_too_long():
    msg = V.target_deviation_warn(130.0, 90.0)  # ~44% long
    assert msg is not None and "偏长" in msg


# ── storyboard contract blocks clip with missing duration (Fix 1a) ──
def _write_storyboard(root, ep, clips):
    sdir = os.path.join(root, "脚本", ep)
    os.makedirs(sdir, exist_ok=True)
    data = {
        "visual_contract": {f: "x" for f in VC.VISUAL_CONTRACT_FIELDS},
        "style_contract": {**{f: "x" for f in VC.STYLE_CONTRACT_FIELDS}, "style_anchor": ["出图/共享/图片/风格锚_x.png"]},
        "clips": clips,
    }
    json.dump(data, open(os.path.join(sdir, "storyboard.json"), "w", encoding="utf-8"),
              ensure_ascii=False)


def test_contract_blocks_clip_missing_duration(tmp_path):
    root, ep = str(tmp_path), "第1集"
    _write_storyboard(root, ep, [
        {"id": "EP01_CLIP01", "duration": 7, "continuity": {
            "start_state": "a", "end_state": "b", "transition": "cut",
            "need_endframe": False, "midframe_exempt_reason": "x"}},
        {"id": "EP01_CLIP02", "continuity": {  # 缺 duration
            "start_state": "a", "end_state": "b", "transition": "cut",
            "need_endframe": False, "midframe_exempt_reason": "x"}},
    ])
    res = VC.validate(root, ep)
    dur_blocks = [r for r in res["findings"]
                  if r["dimension"] == "镜头时长" and r["severity"] == "block"]
    assert len(dur_blocks) == 1
    assert "EP01_CLIP02" in dur_blocks[0]["loc"]
    assert res["ok"] is False


def test_contract_allows_clip_with_duration(tmp_path):
    root, ep = str(tmp_path), "第1集"
    _write_storyboard(root, ep, [
        {"id": "EP01_CLIP01", "duration": 7, "continuity": {
            "start_state": "a", "end_state": "b", "transition": "cut",
            "need_endframe": False, "midframe_exempt_reason": "x"}},
    ])
    res = VC.validate(root, ep)
    assert not [r for r in res["findings"] if r["dimension"] == "镜头时长"]


def test_contract_ignores_three_track_metadata_for_template_detection(tmp_path):
    root, ep = str(tmp_path), "第1集"
    _write_storyboard(root, ep, [
        {
            "id": "EP01_CLIP01",
            "duration": 7,
            "voiceover_indices": [1, 2],
            "dialogue_indices": [1],
            "narration_indices": [2],
            "screen_text_lines": [
                {"text": "第七日", "render_policy": "compose_overlay_only"}
            ],
            "continuity": {
                "start_state": "a",
                "end_state": "b",
                "eyeline": "主角看向画右下道具",
                "transition": "cut",
                "need_endframe": False,
                "midframe_exempt_reason": "x",
            },
        },
    ])
    res = VC.validate(root, ep)
    template_blocks = [
        r for r in res["findings"]
        if r["dimension"] == "专项镜头模板" and r["severity"] == "block"
    ]
    assert template_blocks == []


# ── 软节奏目标自动取（从 _设置.md「拆集节奏」预设；兼容旧「单集时长」） ──
def _write_setting(root, value):
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# 设置\n- 拆集节奏: {value}\n")


def _write_legacy_duration_setting(root, value):
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# 设置\n- 单集时长: {value}\n")


def test_episode_target_default_front_long_short_first_vs_rest(tmp_path):
    root = str(tmp_path)
    # 缺设置 = 默认「前长后短」：第1集 soft 150 / 其余集 soft 90
    assert V.episode_target_seconds(root, "第1集") == 150.0
    assert V.episode_target_seconds(root, "第2集") == 90.0


def test_episode_target_preset_presets(tmp_path):
    root = str(tmp_path)
    _write_setting(root, "快节奏")
    assert V.episode_target_seconds(root, "第1集") == 60.0  # compatible soft seconds
    _write_setting(root, "长集")
    assert V.episode_target_seconds(root, "第3集") == 150.0


def test_episode_target_parameterized_override(tmp_path):
    root = str(tmp_path)
    _write_setting(root, "自定义(95s)")
    assert V.episode_target_seconds(root, "第2集") == 95.0
    _write_setting(root, "快节奏(70-90)")  # 括号软范围中点优先于预设
    assert V.episode_target_seconds(root, "第2集") == 80.0


def test_episode_target_reads_legacy_single_episode_duration_key(tmp_path):
    root = str(tmp_path)
    _write_legacy_duration_setting(root, "快节奏")
    assert V.episode_target_seconds(root, "第2集") == 60.0
