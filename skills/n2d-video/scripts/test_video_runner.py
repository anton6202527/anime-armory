from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("video_runner.py")
spec = importlib.util.spec_from_file_location("video_runner", SCRIPT)
video_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(video_runner)


PROMPT_PACK = """# clips

## Clip 06（时长 4.760s · 镜头 EP01_CLIP06）

**首帧**：`出图/第1集/图片/Clip_06_小禾撞门.png`

### 视频 prompt（中文，目标=即梦）
```
continuity:
  start_state: A
  action: B
  end_state: C
人物运动：小禾撞门；
镜头运动：固定；
```

## Clip 07（时长 6.080s · 镜头 EP01_CLIP07）

**首帧**：`出图/第1集/图片/Clip_07_催命酒到门前.png`

### 视频 prompt（中文，目标=即梦）
```
continuity:
  start_state: D
  action: E
  end_state: F
人物运动：托盘入画；
镜头运动：慢推；
```
"""


def test_prepare_manifest_uses_stable_prompt_files(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_clips.md").write_text(PROMPT_PACK, encoding="utf-8")
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    (image_dir / "Clip_06_小禾撞门.png").write_bytes(b"png")
    (image_dir / "Clip_07_催命酒到门前.png").write_bytes(b"png")

    manifest = video_runner.prepare_manifest(
        tmp_path,
        "第1集",
        6,
        7,
        backend="dreamina",
        resolution="720p",
        model_version="3.0",
    )

    assert manifest["kind"] == "n2d_video_batch"
    assert manifest["batch_id"] == "06_07"
    assert [item["clip"] for item in manifest["items"]] == ["Clip_06", "Clip_07"]
    assert manifest["items"][0]["submit_duration"] == 5
    assert manifest["items"][1]["submit_duration"] == 7
    prompt_file = Path(manifest["items"][0]["prompt_file"])
    assert prompt_file.is_file()
    assert "/private/tmp" not in str(prompt_file)
    assert prompt_file.read_text(encoding="utf-8").startswith("continuity:")
    assert (tmp_path / "生产数据" / "video_batch_第1集_06_07.json").is_file()


def test_submit_duration_has_dreamina_floor() -> None:
    assert video_runner.submit_duration(2.1) == 4
    assert video_runner.submit_duration(4.0) == 4
    assert video_runner.submit_duration(4.1) == 5


def test_submit_clip_runs_video_preflight_before_backend(monkeypatch, tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("人物运动：抬眼；\n镜头运动：慢推；", encoding="utf-8")
    manifest_file = tmp_path / "manifest.json"
    video_runner.atomic_write_json(
        manifest_file,
        {
            "episode": "第1集",
            "items": [
                {
                    "clip": "Clip_01",
                    "target": "Clip_01.mp4",
                    "image": str(tmp_path / "first.png"),
                    "prompt_file": str(prompt),
                    "submit_duration": 4,
                    "status": "prepared",
                }
            ],
        },
    )
    preflight_calls = []

    def fake_preflight(root, episode, stage="video_preflight"):
        preflight_calls.append((root, episode, stage))

    class Proc:
        returncode = 0
        stdout = '{"submit_id":"abc123","gen_status":"processing"}'
        stderr = ""

    monkeypatch.setattr(video_runner, "run_preflight_gate", fake_preflight)
    monkeypatch.setattr(video_runner, "verify_cli_contract", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(video_runner.subprocess, "run", lambda *args, **kwargs: Proc())

    result = video_runner.submit_clip(tmp_path, manifest_file, "Clip_01")

    assert preflight_calls == [(tmp_path, "第1集", "video_preflight")]
    assert result["submit_id"] == "abc123"
    assert result["status"] == "submitted"


def test_resolve_video_backend_dreamina_and_aliases():
    for raw in ("dreamina", "即梦", "Jimeng", None, ""):
        key, adapter = video_runner.resolve_video_backend({"backend": raw} if raw is not None else {})
        assert key == "dreamina"
        assert adapter["provider"] == "dreamina"
        assert adapter["submit_args"] is video_runner._dreamina_args


def test_resolve_video_backend_unsupported_reports_gap_not_silent_switch():
    import pytest

    with pytest.raises(RuntimeError) as exc:
        video_runner.resolve_video_backend({"backend": "kling"})
    msg = str(exc.value)
    assert "kling" in msg and "不偷偷换路" in msg  # C2: stop & report, never substitute dreamina


def test_resolve_video_backend_manual_points_to_accept():
    import pytest

    with pytest.raises(RuntimeError) as exc:
        video_runner.resolve_video_backend({"backend": "manual"})
    assert "accept" in str(exc.value)


def test_submit_clip_unsupported_backend_never_calls_a_cli(monkeypatch, tmp_path: Path):
    import pytest

    manifest_file = tmp_path / "manifest.json"
    video_runner.atomic_write_json(
        manifest_file,
        {"episode": "第1集", "backend": "veo",
         "items": [{"clip": "Clip_01", "target": "Clip_01.mp4", "image": str(tmp_path / "f.png"),
                    "prompt_file": str(tmp_path / "p.txt"), "submit_duration": 4, "status": "prepared"}]},
    )

    def boom(*_a, **_k):  # any subprocess call = silent switch leaked through
        raise AssertionError("must not invoke any backend CLI for an unsupported backend")

    monkeypatch.setattr(video_runner.subprocess, "run", boom)
    # even dry_run resolves the backend first, so it fails fast without building dreamina argv
    with pytest.raises(RuntimeError):
        video_runner.submit_clip(tmp_path, manifest_file, "Clip_01", dry_run=True)


def test_qc_override_payload_marks_false_positive_sample():
    p = video_runner.qc_override_payload("Clip_02", {"seam_blocks": 1, "seam_warns": 2})
    assert p["qa"]["outcome"] == "human_override_false_positive"
    assert p["qa"]["seam_blocks"] == 1 and p["qa"]["seam_warns"] == 2
    assert p["meta"]["clip"] == "Clip_02"
    assert video_runner.qc_override_payload("x", {})["qa"]["seam_blocks"] == 0
