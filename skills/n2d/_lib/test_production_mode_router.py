from __future__ import annotations

import json

import production_mode_router as pmr


def test_spoken_performance_recommends_mixed_when_routes_differ() -> None:
    result = pmr.recommend_mode({
        "spoken_line_count": 8,
        "speaking_clip_count": 4,
        "closeup_speaking_clip_count": 2,
        "native_speech_clip_count": 0,
        "placeholder_timing": True,
        "audio_strategy_counts": {
            "base_video_then_post_lipsync": 2,
            "rough_timing_final_dub_later": 1,
            "picture_first": 1,
        },
    }, "先出视频后配音")
    assert result["recommended_mode"] == "混合自动路由"
    assert result["aligned"] is False
    assert {row["code"] for row in result["risks"]} >= {"uniform_video_first_rework", "placeholder_audio_waste"}


def test_silent_action_can_recommend_video_first_and_native_av_is_opt_in() -> None:
    silent = pmr.recommend_mode({
        "spoken_line_count": 0, "speaking_clip_count": 0,
        "voiceover_present": True, "storyboard_clip_count": 3,
        "action_or_montage_clip_count": 3,
        "audio_strategy_counts": {"picture_first": 3},
    }, "配音先行")
    assert silent["recommended_mode"] == "先出视频后配音"
    native = pmr.recommend_mode({"spoken_line_count": 1, "speaking_clip_count": 1, "native_speech_clip_count": 1}, "原生音画")
    assert native["recommended_mode"] == "原生音画"


def test_missing_material_does_not_mistake_absence_for_silent_action() -> None:
    result = pmr.recommend_mode({
        "spoken_line_count": 0, "speaking_clip_count": 0,
        "voiceover_present": False, "storyboard_clip_count": 0,
    }, "配音先行")
    assert result["recommended_mode"] == "混合自动路由"
    assert result["risks"][0]["code"] == "insufficient_evidence"


def test_native_av_opt_in_is_not_overridden_before_native_clip_contracts_exist() -> None:
    result = pmr.recommend_mode({
        "spoken_line_count": 6,
        "speaking_clip_count": 3,
        "native_speech_clip_count": 0,
        "storyboard_clip_count": 3,
    }, "原生音画")

    assert result["recommended_mode"] == "原生音画"
    assert result["aligned"] is True
    assert {row["code"] for row in result["risks"]} == {"native_contract_missing"}


def test_visible_dialogue_without_audio_routes_to_base_video_then_post_lipsync(tmp_path) -> None:
    voice = tmp_path / "脚本" / "第1集" / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    voice.write_text("[镜头1·沈念·迟疑] 你看见了吗？\n", encoding="utf-8")
    clips = [{"id": "Clip_01", "voiceover_indices": [1], "dialogue_indices": [1], "mouth_visible": True, "template": "dialogue_shot_reverse"}]
    _path, lines, _fingerprint = pmr.load_voiceover(tmp_path, "第1集")
    routes = pmr.build_clip_sound_routes(
        tmp_path, "第1集", clips, lines,
        casting={}, timing_estimate={"kind": "n2d_timing_estimate", "lines": [{"idx": 0}]},
        final_manifest=[],
    )
    route = routes[0]
    assert route["audio_strategy"] == "base_video_then_post_lipsync"
    assert route["base_video_only"] is True
    assert route["post_lipsync_required"] is True
    assert route["post_lipsync_output"] == "出视频/第1集/视频_lipsync/Clip_01_lipsync.mp4"
    assert route["can_generate_final_performance"] is False


def test_visible_dialogue_with_guide_uses_performance_audio_first(tmp_path) -> None:
    guide = tmp_path / "导引.wav"
    guide.write_bytes(b"guide")
    voice = tmp_path / "脚本" / "第1集" / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    voice.write_text("[镜头1·沈念·克制] 别动。\n", encoding="utf-8")
    clips = [{"id": "Clip_01", "voiceover_indices": [1], "dialogue_indices": [1], "mouth_visible": True, "guide_audio": "导引.wav"}]
    _path, lines, _fingerprint = pmr.load_voiceover(tmp_path, "第1集")
    route = pmr.build_clip_sound_routes(
        tmp_path, "第1集", clips, lines, casting={}, timing_estimate={}, final_manifest=[],
    )[0]
    assert route["audio_strategy"] == "performance_audio_first"
    assert route["performance_track_status"] == "guide_ready"
    assert route["can_generate_final_performance"] is True


def test_explicit_mouth_hidden_beats_closeup_inference(tmp_path) -> None:
    voice = tmp_path / "脚本" / "第1集" / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    voice.write_text("[镜头1·沈念·内心] 不能让他看出来。\n", encoding="utf-8")
    clips = [{
        "id": "EP01_CLIP01",
        "voiceover_indices": [1],
        "dialogue_indices": [1],
        "narration_indices": [],
        "mouth_visible": False,
        "shots": [{"lens": "CU", "description": "单人眼神近景"}],
    }]
    _path, lines, _fingerprint = pmr.load_voiceover(tmp_path, "第1集")

    route = pmr.build_clip_sound_routes(
        tmp_path, "第1集", clips, lines, casting={},
        timing_estimate={"kind": "n2d_timing_estimate", "lines": [{"idx": 0}]},
        final_manifest=[],
    )[0]

    assert route["mouth_visible"] is False
    assert route["audio_strategy"] == "post_dub"
    assert route["post_lipsync_required"] is False


def test_explicit_mouth_hidden_releases_stale_paid_base_lipsync_commitment(tmp_path) -> None:
    voice = tmp_path / "脚本" / "第1集" / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    voice.write_text("[镜头1·沈念·内心] 不能让他看出来。\n", encoding="utf-8")
    video = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"paid-base-video")
    clips = [{
        "id": "EP01_CLIP01",
        "voiceover_indices": [1],
        "dialogue_indices": [1],
        "narration_indices": [],
        "mouth_visible": False,
        "shots": [{"lens": "CU", "description": "单人眼神近景，台词为口外音"}],
    }]
    _path, lines, _fingerprint = pmr.load_voiceover(tmp_path, "第1集")

    route = pmr.build_clip_sound_routes(
        tmp_path, "第1集", clips, lines, casting={}, timing_estimate={}, final_manifest=[],
        previous_routes={"Clip_01": {
            "audio_strategy": "base_video_then_post_lipsync",
            "base_video_only": True,
        }},
    )[0]

    assert route["mouth_visible"] is False
    assert route["audio_strategy"] == "post_dub"
    assert route["base_video_only"] is False
    assert route["post_lipsync_required"] is False
    assert route["route_commitment"] == "uncommitted"


def test_declared_narration_track_overrides_non_narrator_role_name(tmp_path) -> None:
    voice = tmp_path / "脚本" / "第1集" / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    voice.write_text("[镜头1·系统·空灵] 道行到账。\n", encoding="utf-8")
    clips = [{
        "id": "EP01_CLIP13",
        "voiceover_indices": [1],
        "dialogue_indices": [],
        "narration_indices": [1],
        "mouth_visible": False,
        "template": "system_panel",
    }]
    _path, lines, _fingerprint = pmr.load_voiceover(tmp_path, "第1集")

    route = pmr.build_clip_sound_routes(
        tmp_path, "第1集", clips, lines, casting={},
        timing_estimate={"kind": "n2d_timing_estimate", "lines": [{"idx": 0}]},
        final_manifest=[],
    )[0]

    assert route["content_class"] == "narration_or_offscreen"
    assert route["audio_strategy"] == "rough_timing_final_dub_later"
    assert route["mouth_visible"] is False


def test_collect_signals_respects_declared_tracks_and_mouth_visibility(tmp_path) -> None:
    script = tmp_path / "脚本" / "第1集"
    script.mkdir(parents=True)
    (script / "voiceover.txt").write_text(
        "[镜头1·系统·空灵] 道行到账。\n[镜头2·沈念·克制] 别动。\n",
        encoding="utf-8",
    )
    (script / "storyboard.json").write_text(json.dumps({"clips": [
        {
            "id": "EP01_CLIP01", "voiceover_indices": [1],
            "dialogue_indices": [], "narration_indices": [1],
            "mouth_visible": False, "shots": [{"lens": "CU"}],
        },
        {
            "id": "EP01_CLIP02", "voiceover_indices": [2],
            "dialogue_indices": [2], "narration_indices": [],
            "mouth_visible": True, "shots": [{"lens": "CU"}],
        },
    ]}), encoding="utf-8")

    signals = pmr.collect_signals(tmp_path, "第1集")

    assert signals["speaking_clip_count"] == 1
    assert signals["mouth_visible_clip_count"] == 1
    assert signals["closeup_speaking_clip_count"] == 1


def test_existing_base_plate_keeps_post_lipsync_route_when_final_voice_arrives(tmp_path) -> None:
    (tmp_path / "_设置.md").write_text("- 制作模式: 混合自动路由\n", encoding="utf-8")
    script = tmp_path / "脚本" / "第1集"
    script.mkdir(parents=True)
    (script / "voiceover.txt").write_text("[镜头1·沈念·克制] 别动。\n", encoding="utf-8")
    (script / "storyboard.json").write_text(json.dumps({"clips": [{
        "id": "Clip_01", "voiceover_indices": [1], "dialogue_indices": [1],
        "mouth_visible": True, "template": "dialogue_shot_reverse", "duration": 2.0,
    }]}), encoding="utf-8")
    base = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    plan = tmp_path / "出视频" / "第1集" / "prompt" / "video_model_routes.json"
    base.parent.mkdir(parents=True)
    plan.parent.mkdir(parents=True)
    base.write_bytes(b"paid-base-pixels")
    plan.write_text(json.dumps({"routes": [{
        "clip_id": "Clip_01", "audio_strategy": "base_video_then_post_lipsync",
        "base_video_only": True, "post_lipsync_required": True,
    }]}), encoding="utf-8")
    voice = tmp_path / "合成" / "第1集" / "配音"
    voice.mkdir(parents=True)
    (voice / "line_00.wav").write_bytes(b"final-audio")
    (voice / "时长清单.json").write_text(json.dumps([
        {"idx": 0, "时长": 1.2, "占位": False, "voice_key": "locked:shen"},
    ]), encoding="utf-8")

    route = pmr.build_route(tmp_path, "第1集")["clip_routes"][0]

    assert route["performance_track_status"] == "final_ready"
    assert route["audio_strategy"] == "base_video_then_post_lipsync"
    assert route["route_commitment"] == "base_plate_already_generated"
    assert route["post_lipsync_required"] is True
