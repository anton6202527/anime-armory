# -*- coding: utf-8 -*-
"""多视图定妆分参考（derive_reference_views）单测。

盯三条纪律：
  ① 只产图 + manifest，**绝不改 asset_registry**（母本治理归 gate registry_snapshot）；
  ② 裁切可溯源（source sha256 + 归一化框），重跑同源幂等替换；
  ③ 太小的分参考（<min_view_px）宁可失败也不落盘——小图对身份锁定没意义。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_reference_views as drv  # noqa: E402

PIL = drv._load_pil()
pytestmark = pytest.mark.skipif(PIL is None, reason="需要 Pillow")


def _project(tmp_path: Path, size=(800, 800)) -> Path:
    root = tmp_path / "广告项目"
    (root / "出图" / "定妆").mkdir(parents=True)
    (root / "设定库").mkdir(parents=True)
    im = PIL.new("RGB", size)
    # 四象限四色，便于断言裁切正确
    for (x0, y0, color) in ((0, 0, (255, 0, 0)), (size[0] // 2, 0, (0, 255, 0)),
                            (0, size[1] // 2, (0, 0, 255)), (size[0] // 2, size[1] // 2, (255, 255, 0))):
        im.paste(PIL.new("RGB", (size[0] // 2, size[1] // 2), color), (x0, y0))
    im.save(root / "出图" / "定妆" / "PROD_X.png")
    (root / "设定库" / "asset_registry.json").write_text(
        json.dumps({"PROD_X": {"reference_images": ["出图/定妆/PROD_X.png"]}}, ensure_ascii=False),
        encoding="utf-8")
    return root


def test_grid_derive_writes_views_manifest_and_patch_without_touching_registry(tmp_path):
    root = _project(tmp_path)
    registry_before = (root / "设定库" / "asset_registry.json").read_text(encoding="utf-8")

    rc = drv.main([str(root), "--asset", "PROD_X", "--source", "出图/定妆/PROD_X.png",
                   "--grid", "2x2", "--names", "正面,四分之三,侧面,背面"])

    assert rc == 0
    views_dir = root / "出图" / "共享" / "定妆视图" / "PROD_X"
    assert {p.name for p in views_dir.iterdir()} == {"正面.png", "四分之三.png", "侧面.png", "背面.png"}
    with PIL.open(views_dir / "正面.png") as im:
        assert im.size == (400, 400)
        assert im.convert("RGB").getpixel((200, 200)) == (255, 0, 0)  # 左上象限
    manifest = json.loads((root / "生产数据" / "ad_reference_views.json").read_text(encoding="utf-8"))
    rec = manifest["records"][0]
    assert rec["source"]["sha256"] and len(rec["views"]) == 4
    patch = rec["suggested_registry_patch"]
    assert len(patch["append_reference_images"]) == 4
    assert all(p.startswith("出图/共享/定妆视图/PROD_X/") for p in patch["append_reference_images"])
    # registry 母本一字未动
    assert (root / "设定库" / "asset_registry.json").read_text(encoding="utf-8") == registry_before


def test_rerun_same_source_is_idempotent_in_manifest(tmp_path):
    root = _project(tmp_path)
    args = [str(root), "--asset", "PROD_X", "--source", "出图/定妆/PROD_X.png", "--grid", "2x2"]
    assert drv.main(args) == 0
    assert drv.main(args) == 0
    manifest = json.loads((root / "生产数据" / "ad_reference_views.json").read_text(encoding="utf-8"))
    assert len(manifest["records"]) == 1  # 同 asset+同源 sha 替换，不累积


def test_explicit_boxes_and_validation(tmp_path):
    root = _project(tmp_path)
    rc = drv.main([str(root), "--asset", "PROD_X", "--source", "出图/定妆/PROD_X.png",
                   "--box", "上半:0,0,1,0.5", "--box", "下半:0,0.5,1,1"])
    assert rc == 0

    # 坐标越界 / 太小的视图 / 非法 asset 前缀 / grid+box 同给 → 全部拒绝
    bad = [
        ["--box", "坏:0.5,0,0.2,1"],
        ["--box", "太小:0,0,0.05,0.05"],
    ]
    for extra in bad:
        assert drv.main([str(root), "--asset", "PROD_X", "--source", "出图/定妆/PROD_X.png"] + extra) == 2
    assert drv.main([str(root), "--asset", "小明", "--source", "出图/定妆/PROD_X.png", "--grid", "2x2"]) == 2
    assert drv.main([str(root), "--asset", "PROD_X", "--source", "出图/定妆/PROD_X.png",
                     "--grid", "2x2", "--box", "a:0,0,1,1"]) == 2
