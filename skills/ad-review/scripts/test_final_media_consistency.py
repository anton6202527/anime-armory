import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import final_media_consistency as fm  # noqa: E402


def _video(path: Path, color: str):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg required for final-media integration")
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"color=c={color}:s=320x240:d=2", "-c:v", "mpeg4", str(path)], check=True)


def test_final_media_extracts_encoded_shot_frames_and_asset_contact_sheets(tmp_path):
    pytest.importorskip("PIL.Image")
    root = tmp_path / "ad"
    _video(root / "出视频" / "分镜" / "视频" / "镜头01.mp4", "red")
    _video(root / "合成" / "成片_主片.mp4", "blue")
    (root / "脚本").mkdir()
    (root / "脚本" / "storyboard.json").write_text(json.dumps({"shots": [{
        "shot_id": "S1", "duration": 2,
        "assets": {"PROD_BOX": True, "CHAR_HOST": True, "LOC_DESK": True, "PROP_PEN": True},
    }]}), encoding="utf-8")
    (root / "合成" / "delivery_plan.json").write_text(json.dumps({"deliverables": [{
        "deliverable_id": "master", "kind": "master", "duration": "2s", "exists": True,
        "status": "rendered", "expected_path": "合成/成片_主片.mp4",
    }]}), encoding="utf-8")
    report = fm.build(root)
    assert report["summary"]["block"] == 0
    assert set(report["categories"]) == {"product", "character", "scene", "prop"}
    for asset_id, row in report["assets"].items():
        assert row["frame_count"] == 6  # final clip 3 + final encoded deliverable shot 3
        sheet = row["contact_sheet"]
        assert sheet["sha256"] and (root / sheet["path"]).is_file(), asset_id
    assert any(row.get("media_level") == "final_deliverable" for row in report["frames"])

