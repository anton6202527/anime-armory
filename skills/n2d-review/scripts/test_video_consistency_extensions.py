import json
from pathlib import Path

import camera_trajectory_consistency as cam
import causal_event_consistency as causal
import dialogue_av_consistency as dav
import video_semantic_consistency as vsem
import video_vlm_consistency as vvlm


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_video_vlm_report_blocks_failed_judgement(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"video_vlm_consistency_{ep}.json",
        {"judgements": [{"clip": "Clip_03", "question": "主角是否仍拿着玉簪", "match": False, "confidence": 0.86}]},
    )
    res = vvlm.analyze(str(tmp_path), ep)
    assert res["available"] is True
    assert res["findings"][0]["verdict"] == "block"
    assert res["findings"][0]["affected_shots"] == ["Clip_03"]


def test_video_semantic_report_bands_subject_similarity(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"video_semantic_consistency_{ep}.json",
        {"segments": [{"clip": "Clip_02", "subject_similarity": 0.41, "background_similarity": 0.50}]},
    )
    res = vsem.analyze(str(tmp_path), ep)
    assert any(row["verdict"] == "block" and row["subject_similarity"] == 0.41 for row in res["findings"])


def test_dialogue_av_requires_report_for_native_multi_speaker_final(tmp_path: Path) -> None:
    ep = "第1集"
    voice = tmp_path / "脚本" / ep / "voiceover.txt"
    voice.parent.mkdir(parents=True)
    voice.write_text("沈念：你来了。\n柳娘子：我一直在。\n", encoding="utf-8")
    _write_json(
        tmp_path / "生产数据" / "video_model_routes.json",
        {"routes": [{"clip_id": "Clip_01", "primary_backend": "NativeAV", "native_audio": True}]},
    )
    video = tmp_path / "合成" / ep / "成片.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    res = dav.analyze(str(tmp_path), ep)
    assert res["available"] is True
    assert "dialogue_av_alignment" in res["findings"][0]["message"]


def test_causal_event_warns_missing_graph_when_risky_video_exists(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "脚本" / ep / "storyboard.json",
        {"clips": [{"id": "Clip_01", "action": "沈念击中烛台，烛台摔碎后火焰熄灭"}]},
    )
    video = tmp_path / "出视频" / ep / "视频" / "Clip_01.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    res = causal.analyze(str(tmp_path), ep)
    assert res["available"] is True
    assert any("causal_event_graph" in row["message"] for row in res["findings"])


def test_camera_trajectory_report_blocks_axis_flip(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(
        tmp_path / "生产数据" / f"camera_trajectory_probe_{ep}.json",
        {"shots": [{"clip": "Clip_04", "axis_flip": True, "trajectory_error": 0.41}]},
    )
    res = cam.analyze(str(tmp_path), ep)
    assert any(row["verdict"] == "block" and "越轴" in row["message"] for row in res["findings"])
