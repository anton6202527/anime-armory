from __future__ import annotations

import json
from pathlib import Path

import editorial_timeline as et


def test_otio_contains_multitrack_picture_transition_and_subtitle_markers(tmp_path: Path) -> None:
    script = tmp_path / "脚本" / "第1集"
    script.mkdir(parents=True)
    (script / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "Clip_01", "duration": 2, "continuity": {"transition": "溶解", "seam_mode": "dissolve", "seam_evidence": {"duration_sec": 0.25, "editorial_reason": "时间柔和过渡"}}},
            {"id": "Clip_02", "duration": 3, "continuity": {"start_state": "新场景"}},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    (script / "字幕_中文.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n你好\n", encoding="utf-8")

    payload = et.build_editorial_timeline(tmp_path, "第1集")
    assert payload["phase"] == "animatic"
    assert payload["track_names"] == ["V1 Picture", "A1 Dialogue_Narration", "A2 Ambience_Foley", "A3 BGM"]
    assert payload["duration_sec"] == 5.0
    assert payload["rate"] == 30.0
    picture = payload["otio"]["tracks"]["children"][0]
    assert any(item.get("OTIO_SCHEMA") == "Transition.1" for item in picture["children"])
    assert len(picture["markers"]) == 1

    outputs = et.write_editorial_timeline(tmp_path, payload)
    otio = json.loads((tmp_path / outputs["otio"]).read_text(encoding="utf-8"))
    assert otio["OTIO_SCHEMA"] == "Timeline.1"
    assert (tmp_path / outputs["sidecar"]).is_file()
    assert (tmp_path / outputs["animatic_snapshot"]).is_file()


def test_manifest_backed_timeline_uses_only_accepted_video(tmp_path: Path) -> None:
    script = tmp_path / "脚本" / "第1集"
    script.mkdir(parents=True)
    (script / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "Clip_01", "duration": 2},
        {"id": "Clip_02", "duration": 2},
    ]}), encoding="utf-8")
    video = tmp_path / "出视频" / "第1集" / "视频"
    video.mkdir(parents=True)
    accepted = video / "Clip_01.mp4"
    unaccepted = video / "Clip_02.mp4"
    accepted.write_bytes(b"accepted")
    unaccepted.write_bytes(b"downloaded-only")
    proxy = tmp_path / "合成" / "第1集" / "_proxy"
    proxy.mkdir(parents=True)
    (proxy / "timeline.json").write_text(json.dumps({"timeline": [
        {"clip": "Clip_01", "story_clip": "Clip_01", "source": "出视频/第1集/视频/Clip_01.mp4", "source_manifest": "生产数据/video_batch.json", "source_status": "accepted", "edit_target_sec": 2},
        {"clip": "Clip_02", "story_clip": "Clip_02", "source": "出视频/第1集/视频/Clip_02.mp4", "source_manifest": "生产数据/video_batch.json", "source_status": "downloaded", "edit_target_sec": 2},
    ]}), encoding="utf-8")

    payload = et.build_editorial_timeline(tmp_path, "第1集")

    assert payload["phase"] == "assembly"
    assert payload["accepted_story_clip_count"] == 1
    assert payload["missing_picture_slots"] == ["Clip_02"]
    picture = payload["otio"]["tracks"]["children"][0]["children"]
    assert picture[0]["media_references"]["DEFAULT_MEDIA"]["OTIO_SCHEMA"] == "ExternalReference.1"
    assert picture[1]["media_references"]["DEFAULT_MEDIA"]["OTIO_SCHEMA"] == "MissingReference.1"


def test_otio_uses_planned_missing_audio_slots_instead_of_disposable_wav(tmp_path: Path) -> None:
    script = tmp_path / "脚本" / "第1集"
    script.mkdir(parents=True)
    (script / "storyboard.json").write_text(json.dumps({"clips": [{"id": "Clip_01", "duration": 2.0}]}), encoding="utf-8")
    voice = tmp_path / "合成" / "第1集" / "配音"
    voice.mkdir(parents=True)
    (voice / "timing_estimate.json").write_text(json.dumps({
        "kind": "n2d_timing_estimate",
        "version": 1,
        "audio_generated": False,
        "lines": [{"line_index": 1, "角色": "旁白", "文本": "夜色压下来。", "时长": 2.0, "gap_after": 0.0}],
    }, ensure_ascii=False), encoding="utf-8")

    payload = et.build_editorial_timeline(tmp_path, "第1集")
    audio = payload["otio"]["tracks"]["children"][1]

    assert payload["timing_basis"] == "text_estimate_no_audio"
    assert payload["planned_audio_slot_count"] == 1
    assert audio["children"][0]["media_references"]["DEFAULT_MEDIA"]["OTIO_SCHEMA"] == "MissingReference.1"
    assert audio["children"][0]["metadata"]["n2d"]["text"] == "夜色压下来。"
    assert not list(tmp_path.rglob("*.wav"))


def test_otio_v1_replaces_neutral_base_with_post_lipsync_version(tmp_path: Path) -> None:
    script = tmp_path / "脚本" / "第1集"
    script.mkdir(parents=True)
    (script / "storyboard.json").write_text(
        json.dumps({"clips": [{"id": "Clip_01", "duration": 2.0}]}), encoding="utf-8",
    )
    base = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    final = tmp_path / "出视频" / "第1集" / "视频_lipsync" / "Clip_01_lipsync.mp4"
    routes = tmp_path / "出视频" / "第1集" / "prompt" / "video_model_routes.json"
    base.parent.mkdir(parents=True)
    final.parent.mkdir(parents=True)
    routes.parent.mkdir(parents=True)
    base.write_bytes(b"base")
    final.write_bytes(b"post-lipsync")
    routes.write_text(json.dumps({"routes": [{
        "clip_id": "Clip_01",
        "audio_strategy": "base_video_then_post_lipsync",
        "post_lipsync_required": True,
        "post_lipsync_output": "出视频/第1集/视频_lipsync/Clip_01_lipsync.mp4",
    }]}), encoding="utf-8")
    proxy = tmp_path / "合成" / "第1集" / "_proxy"
    proxy.mkdir(parents=True)
    (proxy / "timeline.json").write_text(json.dumps({"timeline": [{
        "clip": "Clip_01", "story_clip": "Clip_01",
        "source": "出视频/第1集/视频/Clip_01.mp4",
        "source_manifest": "生产数据/video_batch.json",
        "source_status": "accepted", "edit_target_sec": 2.0,
    }]}), encoding="utf-8")

    payload = et.build_editorial_timeline(tmp_path, "第1集")
    picture = payload["otio"]["tracks"]["children"][0]["children"][0]
    media = picture["media_references"]["DEFAULT_MEDIA"]

    assert media["target_url"] == "出视频/第1集/视频_lipsync/Clip_01_lipsync.mp4"
    assert picture["metadata"]["n2d"]["derived_from"] == "neutral_mouth_base_plate"
