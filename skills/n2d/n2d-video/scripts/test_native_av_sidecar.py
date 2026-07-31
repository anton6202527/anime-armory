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
    assert row["speaker_source"]["on_screen"] is True
    assert row["speaker_source"]["mouth_visible"] is True
    assert row["speaker_source"]["dialogue_ref"] == "needs_review"
    assert row["lip_sync"]["policy"] == "native_dialogue_match"
    assert row["spatial_acoustics"]["space_id"] == "LOC_02"
    assert row["evidence_status"] == "needs_review"
    assert row["post_policy"]["compose_policy"] == "保留原片音轨"


def test_build_physics_clip_parses_named_registry_ids_and_dialogue_contract(tmp_path: Path) -> None:
    row = native_av_sidecar.build_physics_clip(
        root=tmp_path,
        episode="第1集",
        clip_id="Clip_01",
        prompt_text=(
            "character_ids=CHAR_HE_PINGSHENG, CHAR_ZHANG_LAODA; asset_ids=LOC_ZAYI_DADIAN; "
            "原生音画约束：台词+口型由原生音画后端生成。 "
            "allowed_character_dialogue_indices=[2, 3]"
        ),
        video_path=tmp_path / "出视频" / "第1集" / "视频" / "Clip_01.mp4",
        has_audio=True,
    )

    assert row["audio_intent"] == "native_speech"
    assert row["speaker_source"]["character_id"] == "CHAR_HE_PINGSHENG"
    assert row["speaker_source"]["on_screen"] is True
    assert row["speaker_source"]["dialogue_ref"] == "dialogue_fact_contract.allowed_character_dialogue_indices=[2, 3]"
    assert row["lip_sync"]["policy"] == "native_dialogue_match"
    assert row["spatial_acoustics"]["space_id"] == "LOC_ZAYI_DADIAN"


def test_no_native_speech_is_not_misclassified_as_native_speech(tmp_path: Path) -> None:
    row = native_av_sidecar.build_physics_clip(
        root=tmp_path,
        episode="第1集",
        clip_id="Clip_08",
        prompt_text=(
            "原生音画约束：audio_intent=none; speech_policy=no_native_speech; "
            "native_audio_policy=lipsync_condition_only；台词+口型只作口型条件，不保留模型音频。"
        ),
        video_path=tmp_path / "出视频" / "第1集" / "视频" / "Clip_08.mp4",
        has_audio=False,
    )

    assert row["audio_intent"] == "none"
    assert row["post_policy"]["compose_policy"] == "丢弃"
    assert row["lip_sync"]["status"] == "not_applicable"


def test_upsert_physics_prunes_missing_video_rows(tmp_path: Path) -> None:
    physics = tmp_path / "生产数据" / "native_av_physics_第1集.json"
    physics.parent.mkdir()
    physics.write_text(
        json.dumps(
            {
                "kind": native_av_sidecar.PHYSICS_KIND,
                "clips": [
                    {
                        "clip_id": "Clip_03",
                        "audio_intent": "native_speech",
                        "video_path": "出视频/第1集/视频/Clip_03_stale_parent.mp4",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    video = tmp_path / "出视频" / "第1集" / "视频" / "Clip_03_part1.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"mp4")

    native_av_sidecar.upsert_physics(
        tmp_path,
        "第1集",
        {
            "clip_id": "Clip_03_part1",
            "audio_intent": "none",
            "video_path": "出视频/第1集/视频/Clip_03_part1.mp4",
        },
    )

    data = json.loads(physics.read_text(encoding="utf-8"))
    assert [row["clip_id"] for row in data["clips"]] == ["Clip_03_part1"]


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
