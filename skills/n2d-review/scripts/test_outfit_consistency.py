"""outfit_consistency 纯数学单测（无需 Pillow）。
cd skills/n2d-review/scripts && python -m pytest test_outfit_consistency.py
"""
import outfit_consistency as oc


def test_hist_normalizes_to_one():
    # 两个有色像素 → 归一化后和≈1
    h = oc.weighted_hue_hist([(0.0, 1.0, 1.0), (0.5, 1.0, 1.0)], bins=4)
    assert abs(sum(h) - 1.0) < 1e-9
    assert h[0] > 0 and h[2] > 0  # hue 0→bin0, hue .5→bin2


def test_gray_and_dark_pixels_ignored():
    # 饱和度0(灰) + 明度0(黑) 权重为0 → 全零直方图
    h = oc.weighted_hue_hist([(0.3, 0.0, 1.0), (0.3, 1.0, 0.0)], bins=4)
    assert sum(h) == 0.0


def test_weight_by_saturation_value():
    # 同色相、不同 s*v → 权重不同但归一后集中在同一 bin
    h = oc.weighted_hue_hist([(0.1, 1.0, 1.0), (0.1, 0.5, 0.5)], bins=10)
    assert abs(sum(h) - 1.0) < 1e-9
    assert h[1] == 1.0  # 全落 bin1


def test_hue_upper_bound_clamped():
    h = oc.weighted_hue_hist([(1.0, 1.0, 1.0)], bins=8)
    assert h[7] == 1.0  # hue=1.0 夹到最后一个 bin


def test_hist_sim_identical_vs_orthogonal():
    a = oc.weighted_hue_hist([(0.0, 1.0, 1.0)], bins=4)
    b = oc.weighted_hue_hist([(0.0, 1.0, 1.0)], bins=4)
    c = oc.weighted_hue_hist([(0.75, 1.0, 1.0)], bins=4)  # bin3
    assert abs(oc.hist_sim(a, b) - 1.0) < 1e-9
    assert oc.hist_sim(a, c) == 0.0  # 不同 bin → 正交


def test_empty_samples():
    assert oc.weighted_hue_hist([], bins=4) == [0.0, 0.0, 0.0, 0.0]


# ---------- O3 图像路径回归（合成图·缺 PIL 跳过） ----------

def test_palette_hist_image_path(tmp_path):
    import pytest
    Image = pytest.importorskip("PIL.Image")
    red = Image.new("RGB", (32, 32), (220, 20, 20))    # 纯红 → 色相直方图集中
    p = tmp_path / "red.png"; red.save(p)
    h = oc._palette_hist(str(p), bins=12)
    assert h is not None and abs(sum(h) - 1.0) < 1e-6
    assert max(h) > 0.8                                  # 集中在红色 bin
    # 灰图 → 无有色像素 → 全零
    gray = Image.new("RGB", (16, 16), (128, 128, 128))
    pg = tmp_path / "gray.png"; gray.save(pg)
    hg = oc._palette_hist(str(pg), bins=12)
    assert hg is not None and sum(hg) == 0.0
