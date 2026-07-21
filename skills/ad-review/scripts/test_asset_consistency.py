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



def test_product_brand_assets_included_with_tighter_threshold(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    root = tmp_path / "ad"
    (root / "脚本").mkdir(parents=True)
    (root / "出图" / "共享").mkdir(parents=True)
    images = root / "出图" / "分镜" / "图片"
    images.mkdir(parents=True)
    (root / "脚本" / "storyboard.json").write_text(json.dumps({"shots": [
        {"shot_id": "S1", "assets": {"PROD_MAIN": True}},
        {"shot_id": "S2", "assets": {"PROD_MAIN": True}},
    ]}), encoding="utf-8")
    (root / "出图" / "共享" / "asset_registry.json").write_text(json.dumps({
        "products": [{"id": "PROD_MAIN"}],
    }), encoding="utf-8")
    # 两张结构完全不同的图（宽条带 vs 纯白，dHash 距离 32bit）→ 必须对 PROD_ 也产出漂移 warn
    im1 = Image.new("RGB", (64, 36), "black")
    for x in range(64):
        if (x // 8) % 2 == 0:
            for y in range(36):
                im1.putpixel((x, y), (255, 255, 255))
    im1.save(images / "镜头01.png")
    Image.new("RGB", (64, 36), "white").save(images / "镜头02.png")

    payload = ac.build(root)

    drift = [f for f in payload["findings"] if f["code"] == "cross_shot_visual_drift"]
    assert drift and drift[0]["asset_id"] == "PROD_MAIN"
    assert drift[0].get("priority") == "high"
    assert "阈 26" in drift[0]["msg"]
    # 高优先产品发现要排在最前
    assert payload["findings"][0]["code"] == "cross_shot_visual_drift"
