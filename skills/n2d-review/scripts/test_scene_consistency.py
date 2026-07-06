"""scene_consistency 纯数学单测 + O3 图像路径回归（PIL 缺则 skip）。
cd skills/n2d-review/scripts && python -m pytest test_scene_consistency.py
"""
import scene_consistency as sc
import json


def test_dhash_bits_monotonic_row():
    # 递增行 → 每对 左<右 → 全 1；递减 → 全 0
    assert sc.dhash_bits([[1, 2, 3, 4]]) == [1, 1, 1]
    assert sc.dhash_bits([[4, 3, 2, 1]]) == [0, 0, 0]
    assert sc.dhash_bits([[5, 5]]) == [0]  # 相等不算 左<右


def test_hamming():
    assert sc.hamming([1, 0, 1], [1, 0, 1]) == 0
    assert sc.hamming([1, 0, 1], [0, 0, 1]) == 1
    assert sc.hamming([1, 1], [0, 0]) == 2


def test_median():
    assert sc.median([3, 1, 2]) == 2
    assert sc.median([4, 1, 3, 2]) == 2.5
    assert sc.median([]) == 0.0


def test_is_outlier_needs_both_factor_and_floor():
    # 超中位*factor 但绝对距没过 floor → 不算（小组防误杀）
    assert sc.is_outlier(20, 10, factor=1.8, floor=12) is True   # 20>18 且 20>12
    assert sc.is_outlier(17, 10, factor=1.8, floor=12) is False  # 17<18
    assert sc.is_outlier(11, 1, factor=1.8, floor=12) is False   # 11>1.8 但 11<12 floor
    assert sc.is_outlier(13, 1, factor=1.8, floor=12) is True    # 13>1.8 且 13>12


# ---------- O3 图像路径回归（合成图·缺 PIL 跳过） ----------

def test_dhash_image_roundtrip(tmp_path):
    import pytest
    Image = pytest.importorskip("PIL.Image")
    # 左黑右白 → resize 后行内 左<右 应多为 1；同图 hamming=0、与反相图 hamming 高
    a = Image.new("RGB", (18, 16))
    for y in range(16):
        for x in range(18):
            v = 0 if x < 9 else 255
            a.putpixel((x, y), (v, v, v))
    pa = tmp_path / "a.png"; a.save(pa)
    ha = sc._dhash_image(str(pa))
    assert ha is not None and len(ha) == 64
    assert sc.hamming(ha, ha) == 0


# ── lighting_signature 数值强制（LSIG·#6）：接活死 schema，实测色相/饱和度 vs 注册值 ──
# 运行：cd skills/n2d-review/scripts && python -m pytest test_scene_consistency.py -k lighting
def test_hue_circular_dist():
    assert sc.hue_circular_dist(10, 350) == 20.0
    assert sc.hue_circular_dist(0, 180) == 180.0
    assert sc.hue_circular_dist(220, 225) == 5.0


def _patch_lsig(monkeypatch, registry, smap, meas):
    monkeypatch.setattr(sc, "_probe_pillow", lambda: True)
    monkeypatch.setattr(sc, "_load_asset_registry", lambda root: registry)
    monkeypatch.setattr(sc, "_scene_of_shot", lambda root, ep: smap)
    monkeypatch.setattr(sc, "_mean_hue_sat", lambda path: meas)


def test_lighting_signature_flags_hue_drift(monkeypatch):
    reg = {"LOC_01": {"id": "LOC_01", "name": "大殿",
                      "constraints": {"lighting_signature": {"mean_hue": 220, "saturation_range": [0.1, 0.4]}}}}
    _patch_lsig(monkeypatch, reg, {"a.png": "大殿"}, (30.0, 0.25))  # 色相 30° 远离 220°
    rows = sc.lighting_signature_rows("r", "第1集")
    assert len(rows) == 1 and rows[0]["verdict"] == "warn" and "色相" in rows[0]["msg"]


def test_lighting_signature_flags_saturation_out_of_range(monkeypatch):
    reg = {"LOC_01": {"id": "LOC_01", "name": "大殿",
                      "constraints": {"lighting_signature": {"mean_hue": 220, "saturation_range": [0.1, 0.4]}}}}
    _patch_lsig(monkeypatch, reg, {"a.png": "大殿"}, (222.0, 0.9))  # 色相贴合但饱和度爆高
    rows = sc.lighting_signature_rows("r", "第1集")
    assert len(rows) == 1 and "饱和度" in rows[0]["msg"]


def test_lighting_signature_pass_when_within(monkeypatch):
    reg = {"LOC_01": {"id": "LOC_01", "name": "大殿",
                      "constraints": {"lighting_signature": {"mean_hue": 220, "saturation_range": [0.1, 0.4]}}}}
    _patch_lsig(monkeypatch, reg, {"a.png": "大殿"}, (225.0, 0.3))
    assert sc.lighting_signature_rows("r", "第1集") == []


def test_lighting_signature_skips_unregistered(monkeypatch):
    _patch_lsig(monkeypatch, {}, {"a.png": "无名场景"}, (30.0, 0.9))
    assert sc.lighting_signature_rows("r", "第1集") == []


# ── 跨集结构原型（majority_bits / scene_struct_prototypes）────────────────────
def test_majority_bits_basic():
    assert sc.majority_bits([[1, 1, 0, 0], [1, 0, 0, 1], [1, 1, 1, 0]]) == [1, 1, 0, 0]
    assert sc.majority_bits([]) == []
    assert sc.majority_bits([[1, 0]]) == [1, 0]  # 单条原样


def test_majority_bits_tie_breaks_to_zero():
    # 平票（2 个 1，2 个 0）→ 非「过半」→ 0
    assert sc.majority_bits([[1, 1], [1, 1], [0, 0], [0, 0]]) == [0, 0]


def test_scene_struct_prototypes_groups_by_scene(monkeypatch):
    monkeypatch.setattr(sc, "_probe_pillow", lambda: True)
    monkeypatch.setattr(sc, "_scene_of_shot", lambda r, e: {"a.png": "大殿", "b.png": "大殿", "c.png": "偏厅"})
    hashes = {"大殿/a.png": [1] * 64, "大殿/b.png": [1] * 64, "偏厅/c.png": [0] * 64}
    monkeypatch.setattr(sc, "_dhash_image", lambda p: hashes.get("大殿/a.png") if p.endswith("a.png")
                        else hashes.get("大殿/b.png") if p.endswith("b.png") else hashes.get("偏厅/c.png"))
    protos = sc.scene_struct_prototypes("r", "第1集")
    assert protos["大殿"] == [1] * 64 and protos["偏厅"] == [0] * 64


def test_scene_struct_prototypes_empty_without_pillow(monkeypatch):
    monkeypatch.setattr(sc, "_probe_pillow", lambda: False)
    assert sc.scene_struct_prototypes("r", "第1集") == {}


def test_scene_of_shot_reads_current_loc_bound_prompt(tmp_path):
    root = tmp_path / "剧"
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    shared = root / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "asset_registry.json").write_text(
        json.dumps({"assets": [{"id": "LOC_01", "name": "荒野尸骸战场"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (prompt_dir / "01_分镜出图.md").write_text(
        "\n".join([
            "## 镜头 1（`EP01_CLIP01`）",
            "**目标落档**：`出图/第1集/图片/Clip01_first.png` `出图/第1集/图片/Clip01_end.png`",
            "**参考图**：",
            "- 场景定妆：`出图/共享/图片/定妆_场景_荒野尸骸战场.png`，绑定 `LOC_01`。",
        ]),
        encoding="utf-8",
    )

    assert sc._scene_of_shot(str(root), "第1集") == {
        "图片/Clip01_first.png": "荒野尸骸战场",
        "图片/Clip01_end.png": "荒野尸骸战场",
    }


def test_verify_impact_frames_skips_null_template_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "_probe_pillow", lambda: True)
    root = tmp_path / "剧"
    sb = root / "脚本" / "第1集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(
        json.dumps({"clips": [{"id": "Clip_01", "template_contract": None}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    assert sc.verify_impact_frames(str(root), "第1集") == []
