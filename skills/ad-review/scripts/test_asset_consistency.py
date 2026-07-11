import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_consistency as ac  # noqa: E402


def test_cross_shot_asset_uses_actual_images_and_contact_sheet(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    root = tmp_path / "ad"
    (root / "脚本").mkdir(parents=True)
    (root / "出图" / "共享").mkdir(parents=True)
    images = root / "出图" / "分镜" / "图片"
    images.mkdir(parents=True)
    (root / "脚本" / "storyboard.json").write_text(json.dumps({"shots": [
        {"shot_id": "S1", "assets": {"CHAR_HOST": True, "LOC_STUDIO": True}},
        {"shot_id": "S2", "assets": {"CHAR_HOST": True, "LOC_STUDIO": True}},
    ]}), encoding="utf-8")
    (root / "出图" / "共享" / "asset_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_HOST"}], "locations": [{"id": "LOC_STUDIO"}],
    }), encoding="utf-8")
    Image.new("RGB", (64, 36), "black").save(images / "镜头01.png")
    Image.new("RGB", (64, 36), "white").save(images / "镜头02.png")

    payload = ac.build(root)

    assert payload["summary"]["block"] == 0
    reviews = [f for f in payload["findings"] if f["code"] == "manual_contact_review_required"]
    assert reviews and reviews[0]["contact_sheet"]
    assert (root / reviews[0]["contact_sheet"]).is_file()

