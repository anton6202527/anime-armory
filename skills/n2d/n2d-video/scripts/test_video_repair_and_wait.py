from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("video_runner.py")
spec = importlib.util.spec_from_file_location("video_runner_repair_under_test", SCRIPT)
video_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(video_runner)


def _project(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path
    source = root / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"source-video-pixels")
    registry = root / "生产数据" / "video_execution_adapters.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "kind": "n2d_video_execution_adapter_registry",
        "version": 2,
        "adapters": {
            "seedance": {
                "adapter_id": "seedance_edit_test_v2",
                "execution_backend": "seedance",
                "provider": "test",
                "command": ["/bin/true"],
                "operations": ["submit", "query", "edit", "extend", "replace_range", "remix"],
            }
        },
    }), encoding="utf-8")
    manifest = root / "生产数据" / "video_batch_第1集_01_01.json"
    manifest.write_text(json.dumps({
        "episode": "第1集",
        "batch_id": "01_01",
        "backend": "seedance",
        "channel": "",
        "model_version": "seedance-2",
        "video_budget_tier": "普通",
        "video_resolution": "720p",
        "ratio": "9:16",
        "items": [{
            "clip": "Clip_01",
            "target": "Clip_01.mp4",
            "status": "accepted",
            "submit_duration": 5,
        }],
    }), encoding="utf-8")
    return root, manifest


def test_prepare_repair_is_idempotent_and_never_overwrites_source(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path)
    first = video_runner.prepare_repair_item(
        root, manifest, "Clip_01",
        operation="replace_range",
        instruction="只修复手部形变，保持脸、背景与镜头路径。",
        start_sec=1.0,
        end_sec=2.0,
        preserve_regions=["face", "background", "camera_path"],
    )
    second = video_runner.prepare_repair_item(
        root, manifest, "Clip_01",
        operation="replace_range",
        instruction="只修复手部形变，保持脸、背景与镜头路径。",
        start_sec=1.0,
        end_sec=2.0,
        preserve_regions=["face", "background", "camera_path"],
    )
    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert first["clip"] == second["clip"]
    assert first["target"] != "Clip_01.mp4"
    assert first["repair_contract"]["source_sha256"]
    assert first["repair_contract"]["promotion_policy"].startswith("variant_only")
    assert len(data["items"]) == 2


def test_wait_uses_backoff_until_downloaded(tmp_path: Path) -> None:
    states = iter([{"status": "queried"}, {"status": "queried"}, {"status": "downloaded"}])
    sleeps = []

    result = video_runner.wait_for_clip(
        tmp_path, tmp_path / "manifest.json", "Clip_01",
        initial_delay_sec=2.0,
        max_delay_sec=8.0,
        jitter_ratio=0.0,
        sleep_fn=lambda seconds: sleeps.append(seconds),
        query_fn=lambda *a, **k: next(states),
    )

    assert result["status"] == "downloaded"
    assert result["wait_receipt"]["polls"] == 3
    assert sleeps == [2.0, 4.0]


def test_wait_stops_on_non_retryable_query_failure(tmp_path: Path) -> None:
    result = video_runner.wait_for_clip(
        tmp_path, tmp_path / "manifest.json", "Clip_01",
        sleep_fn=lambda _seconds: None,
        query_fn=lambda *a, **k: {
            "status": "query_failed",
            "last_query_adapter": {"failure": {"retryable": False}},
        },
    )
    assert result["status"] == "query_failed"
    assert result["wait_receipt"]["polls"] == 1
