from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("post_video_proxy.py")
spec = importlib.util.spec_from_file_location("post_video_proxy", SCRIPT)
proxy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(proxy)


def _storyboard(root: Path) -> None:
    path = root / "脚本" / "第1集" / "storyboard.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "clips": [
            {"id": "Clip_01", "duration": 4},
            {"id": "Clip_02", "duration": 3},
        ],
    }), encoding="utf-8")


def test_plan_uses_physical_parts_in_story_order(tmp_path: Path, monkeypatch) -> None:
    _storyboard(tmp_path)
    video = tmp_path / "出视频" / "第1集" / "视频"
    video.mkdir(parents=True)
    for name in ("Clip_01_x_part1.mp4", "Clip_01_x_part2.mp4", "Clip_02_y.mp4"):
        (video / name).write_bytes(name.encode())
    pdir = tmp_path / "生产数据"
    pdir.mkdir(exist_ok=True)
    (pdir / "video_batch_第1集_01_02.json").write_text(json.dumps({
        "episode": "第1集",
        "items": [
            {"clip": "Clip_02", "target": "Clip_02_y.mp4", "status": "accepted", "edit_target_duration": 3},
            {"clip": "Clip_01_part2", "story_clip": "Clip_01", "target": "Clip_01_x_part2.mp4", "status": "accepted", "edit_target_duration": 2},
            {"clip": "Clip_01_part1", "story_clip": "Clip_01", "target": "Clip_01_x_part1.mp4", "status": "accepted", "edit_target_duration": 2},
        ],
    }), encoding="utf-8")
    monkeypatch.setattr(proxy, "ffprobe_duration", lambda _path: 9.0)

    plan = proxy.build_plan(tmp_path, "第1集")

    assert [row["clip"] for row in plan["timeline"]] == ["Clip_01_part1", "Clip_01_part2", "Clip_02"]
    assert plan["missing_story_clips"] == []
    assert plan["expected_proxy_duration_sec"] == 7.0


def test_incomplete_plan_names_missing_story_clip(tmp_path: Path, monkeypatch) -> None:
    _storyboard(tmp_path)
    video = tmp_path / "出视频" / "第1集" / "视频"
    video.mkdir(parents=True)
    (video / "Clip_01_only.mp4").write_bytes(b"mp4")
    monkeypatch.setattr(proxy, "ffprobe_duration", lambda _path: 4.0)

    plan = proxy.build_plan(tmp_path, "第1集")

    assert plan["status"] == "incomplete"
    assert plan["missing_story_clips"] == ["Clip_02"]


def test_manifest_presence_never_promotes_downloaded_unaccepted_media(tmp_path: Path, monkeypatch) -> None:
    _storyboard(tmp_path)
    video = tmp_path / "出视频" / "第1集" / "视频"
    video.mkdir(parents=True)
    for name in ("Clip_01.mp4", "Clip_02.mp4"):
        (video / name).write_bytes(name.encode())
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "video_batch_第1集_01_02.json").write_text(json.dumps({
        "episode": "第1集",
        "items": [
            {"clip": "Clip_01", "target": "Clip_01.mp4", "status": "accepted", "edit_target_duration": 4},
            {"clip": "Clip_02", "target": "Clip_02.mp4", "status": "downloaded", "edit_target_duration": 3},
        ],
    }), encoding="utf-8")
    monkeypatch.setattr(proxy, "ffprobe_duration", lambda _path: 4.0)

    plan = proxy.build_plan(tmp_path, "第1集")

    assert [row["clip"] for row in plan["timeline"]] == ["Clip_01"]
    assert plan["missing_story_clips"] == ["Clip_02"]
    assert plan["status"] == "incomplete"


def test_missing_ffmpeg_writes_resumable_plan(tmp_path: Path, monkeypatch) -> None:
    _storyboard(tmp_path)
    video = tmp_path / "出视频" / "第1集" / "视频"
    video.mkdir(parents=True)
    (video / "Clip_01.mp4").write_bytes(b"one")
    (video / "Clip_02.mp4").write_bytes(b"two")
    monkeypatch.setattr(proxy, "ffprobe_duration", lambda _path: 4.0)
    monkeypatch.setattr(proxy.shutil, "which", lambda _name: None)

    payload = proxy.build_and_maybe_render(tmp_path, "第1集", render=True)

    assert payload["status"] == "planned_ffmpeg_missing"
    assert (tmp_path / "生产数据" / "post_video_proxy_第1集.json").is_file()
    assert not (tmp_path / "合成" / "第1集" / "_proxy" / "actual_rough_cut.mp4").exists()


def test_proxy_prefers_post_lipsync_picture_when_available(tmp_path: Path, monkeypatch) -> None:
    _storyboard(tmp_path)
    video = tmp_path / "出视频" / "第1集" / "视频"
    final_dir = tmp_path / "出视频" / "第1集" / "视频_lipsync"
    prompt = tmp_path / "出视频" / "第1集" / "prompt"
    video.mkdir(parents=True)
    final_dir.mkdir(parents=True)
    prompt.mkdir(parents=True)
    (video / "Clip_01.mp4").write_bytes(b"base")
    (video / "Clip_02.mp4").write_bytes(b"two")
    final = final_dir / "Clip_01_lipsync.mp4"
    final.write_bytes(b"final-mouth")
    (prompt / "video_model_routes.json").write_text(json.dumps({"routes": [{
        "clip_id": "Clip_01",
        "audio_strategy": "base_video_then_post_lipsync",
        "post_lipsync_required": True,
    }]}), encoding="utf-8")
    monkeypatch.setattr(proxy, "ffprobe_duration", lambda _path: 4.0)

    plan = proxy.build_plan(tmp_path, "第1集")

    first = plan["timeline"][0]
    assert first["source"] == "出视频/第1集/视频_lipsync/Clip_01_lipsync.mp4"
    assert first["picture_version"] == "post_lipsync"
