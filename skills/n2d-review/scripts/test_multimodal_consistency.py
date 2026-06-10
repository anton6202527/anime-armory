"""multimodal_consistency 单测。
cd skills/n2d-review/scripts && python -m pytest test_multimodal_consistency.py
"""
import pytest

import multimodal_consistency as mm


def test_math_helpers():
    assert mm.median([3, 1, 2]) == 2
    assert mm.median([4, 1, 3, 2]) == 2.5
    assert mm.is_outlier(0.4, 0.1, factor=1.8, floor=0.1) is True
    assert mm.is_outlier(0.12, 0.1, factor=1.8, floor=0.1) is False
    assert mm.normalize_asset("定妆_沈念_半身.png") == "沈念"


def test_embedding_roundtrip(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    a = Image.new("RGB", (32, 32), (255, 0, 0))
    p = tmp_path / "a.png"
    a.save(p)
    emb = mm.image_embedding(str(p))
    assert emb is not None
    assert len(emb) == 128


def test_analyze_flags_asset_group_outlier(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    root = tmp_path / "制漫剧" / "测试剧"
    ep = "第1集"
    img_dir = root / "出图" / ep / "图片"
    prompt_dir = root / "出图" / ep / "prompt"
    img_dir.mkdir(parents=True)
    prompt_dir.mkdir(parents=True)
    colors = [(255, 0, 0), (250, 10, 0), (0, 0, 255)]
    for i, color in enumerate(colors, start=1):
        im = Image.new("RGB", (32, 32), color)
        im.save(img_dir / f"Clip_{i:02d}.png")
    (prompt_dir / "01_分镜出图.md").write_text(
        "## Clip 1\n目标：出图/第1集/图片/Clip_01.png\n**参考图**：`定妆_法宝血玉.png`\n"
        "## Clip 2\n目标：出图/第1集/图片/Clip_02.png\n**参考图**：`定妆_法宝血玉.png`\n"
        "## Clip 3\n目标：出图/第1集/图片/Clip_03.png\n**参考图**：`定妆_法宝血玉.png`\n",
        encoding="utf-8",
    )
    res = mm.analyze(str(root), ep, factor=1.05, floor=0.01)
    assert res["available"] is True
    assert "法宝血玉" in res["groups"]
    assert any(s["asset"] == "法宝血玉" for s in res["shots"])


def test_identity_registry_drives_non_character_asset_classification(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    reg_dir = root / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(
        '{"characters":[{"name":"沈念","forms":[{"asset_key":"沈念","reference_group":{"front":"出图/共享/图片/定妆_沈念.png"}}]}]}',
        encoding="utf-8",
    )
    refs = ["沈念", "血玉"]
    assert mm.non_character_refs(str(root), refs, mm.identity_character_assets(str(root))) == ["血玉"]
