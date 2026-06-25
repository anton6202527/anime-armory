from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("native_av_sidecar.py")
spec = importlib.util.spec_from_file_location("native_av_sidecar", SCRIPT)
native_av_sidecar = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(native_av_sidecar)


def test_build_physics_clip_marks_native_speech_needs_review(tmp_path: Path) -> None:
    row = native_av_sidecar.build_physics_clip(
        root=tmp_path,
        episode="第1集",
        clip_id="Clip_01",
        prompt_text="CHAR_01 原生说话镜；audio_intent=native_speech；mouth_visible=yes；LOC_02",
        video_path=tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4",
        has_audio=True,
    )

    assert row["audio_intent"] == "native_speech"
    assert row["speaker_source"]["character_id"] == "CHAR_01"
    assert row["speaker_source"]["mouth_visible"] is True
    assert row["spatial_acoustics"]["space_id"] == "LOC_02"
    assert row["evidence_status"] == "needs_review"
    assert row["post_policy"]["compose_policy"] == "保留原片音轨"


def test_update_sidecars_writes_physics_and_skips_voice_without_audio(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("CHAR_01 台词+口型由后端生成；audio_intent=native_speech", encoding="utf-8")
    video = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"mp4")

    res = native_av_sidecar.update_sidecars(
        tmp_path,
        "第1集",
        {"clip": "Clip_01", "prompt_file": str(prompt)},
        video,
        {"has_audio": False},
    )

    physics = json.loads((tmp_path / "生产数据" / "native_av_physics_第1集.json").read_text(encoding="utf-8"))
    assert physics["kind"] == native_av_sidecar.PHYSICS_KIND
    assert physics["clips"][0]["clip_id"] == "Clip_01"
    assert res["audio_extract"] == "skipped:no_audio_track"
    assert not (tmp_path / "生产数据" / "native_voice_identity_第1集.json").exists()


def test_update_sidecars_can_disable_audio_extract_but_write_voice_status(tmp_path: Path) -> None:
    video = tmp_path / "出视频" / "第1集" / "视频" / "Clip_02.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"mp4")

    res = native_av_sidecar.update_sidecars(
        tmp_path,
        "第1集",
        {"clip": "Clip_02", "prompt_text": "CHAR_02 audio_intent=native_speech mouth_visible=yes"},
        video,
        {"has_audio": True},
        extract_audio=False,
    )

    assert res["audio_extract"] == "skipped:disabled"
    physics = json.loads((tmp_path / "生产数据" / "native_av_physics_第1集.json").read_text(encoding="utf-8"))
    assert physics["clips"][0]["speaker_source"]["speaker_key"] == "CHAR_02_native"
