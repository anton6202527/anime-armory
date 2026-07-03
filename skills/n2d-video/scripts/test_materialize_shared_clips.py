from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("materialize_shared_clips.py")
spec = importlib.util.spec_from_file_location("materialize_shared_clips", SCRIPT)
materialize = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(materialize)


def test_materialize_shared_video_symlinks_into_episode_dir(tmp_path: Path) -> None:
    shared = tmp_path / "出视频" / "共享" / "视频" / "宫门推.mp4"
    shared.parent.mkdir(parents=True)
    shared.write_bytes(b"mp4")
    sb = tmp_path / "脚本" / "第1集" / "storyboard.json"
    sb.parent.mkdir(parents=True)
    sb.write_text(
        json.dumps({"clips": [{"id": "Clip_01", "shared_video": "宫门推.mp4"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    payload = materialize.run(tmp_path, "第1集")

    dest = tmp_path / "出视频" / "第1集" / "视频" / "Clip_01_宫门推.mp4"
    assert dest.exists()
    assert dest.resolve() == shared.resolve()
    assert payload["summary"] == {"total": 1, "ok": 1, "errors": 0}
    manifest = tmp_path / "生产数据" / "shared_video_materialized_第1集.json"
    assert json.loads(manifest.read_text(encoding="utf-8"))["kind"] == materialize.KIND


def test_materialize_shared_video_reports_missing_source(tmp_path: Path) -> None:
    sb = tmp_path / "脚本" / "第1集" / "storyboard.json"
    sb.parent.mkdir(parents=True)
    sb.write_text(
        json.dumps({"clips": [{"id": "Clip_02", "shared_video": "缺失.mp4"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    payload = materialize.run(tmp_path, "第1集")

    assert payload["summary"]["errors"] == 1
    assert payload["rows"][0]["status"] == "missing_source"
