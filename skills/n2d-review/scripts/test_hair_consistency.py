"""hair_consistency 纯数学单测（无需 Pillow；图像路径回归在装了 PIL 时跑）。
cd skills/n2d-review/scripts && python -m pytest test_hair_consistency.py
"""
import hair_consistency as hc


# ---------- 复合指纹拼接/归一（纯数学） ----------

def test_unit_sum_normalizes():
    assert abs(sum(hc._unit_sum([1.0, 3.0])) - 1.0) < 1e-9
    assert hc._unit_sum([1.0, 3.0]) == [0.25, 0.75]


def test_unit_sum_all_zero_kept():
    assert hc._unit_sum([0.0, 0.0]) == [0.0, 0.0]


def test_combine_fingerprint_weights_and_concats():
    # 发色段 [1,0] 归一→[1,0]，发型段 [0,1] 归一→[0,1]；hue_weight=0.5
    fp = hc.combine_fingerprint([1.0, 0.0], [0.0, 1.0], hue_weight=0.5)
    assert fp == [0.5, 0.0, 0.0, 0.5]


def test_combine_fingerprint_weight_extremes():
    only_hue = hc.combine_fingerprint([2.0, 2.0], [1.0, 0.0], hue_weight=1.0)
    assert only_hue == [0.5, 0.5, 0.0, 0.0]      # 发型段权重 0
    only_edge = hc.combine_fingerprint([2.0, 2.0], [1.0, 3.0], hue_weight=0.0)
    assert only_edge == [0.0, 0.0, 0.25, 0.75]   # 发色段权重 0


def test_combine_fingerprint_weight_clamped():
    # hue_weight 越界被夹到 [0,1]
    assert hc.combine_fingerprint([1.0], [1.0], hue_weight=5.0) == [1.0, 0.0]
    assert hc.combine_fingerprint([1.0], [1.0], hue_weight=-5.0) == [0.0, 1.0]


def test_hair_sim_identical_vs_orthogonal():
    a = hc.combine_fingerprint([1.0, 0.0], [1.0, 0.0])
    b = hc.combine_fingerprint([1.0, 0.0], [1.0, 0.0])
    c = hc.combine_fingerprint([0.0, 1.0], [0.0, 1.0])
    assert abs(hc.hair_sim(a, b) - 1.0) < 1e-9
    assert hc.hair_sim(a, c) == 0.0   # 发色+发型都换 → 正交


def test_head_box_upper_center():
    # 头部框：上半 head_frac、水平居中（裁掉两侧 10%）
    box = hc._head_box(100, 200, head_frac=0.55)
    left, top, right, bottom = box
    assert top == 0 and bottom == 110          # 200*0.55
    assert left == 10 and right == 90          # 居中 80%


# ---------- 图像路径回归（合成图·缺 PIL 跳过） ----------

def test_fingerprint_image_path(tmp_path):
    import pytest
    Image = pytest.importorskip("PIL.Image")
    # 上半红发、下半深底 → 头部区主色稳定
    im = Image.new("RGB", (64, 64), (10, 10, 10))
    for y in range(0, 30):
        for x in range(0, 64):
            im.putpixel((x, y), (210, 30, 30))
    p = tmp_path / "hair.png"; im.save(p)
    fp = hc._hair_fingerprint(str(p), bins=12, grid=4, hue_weight=0.5, head_frac=0.55)
    assert fp is not None and len(fp) == 12 + 16     # 色相 bins + grid*grid
    assert abs(sum(fp) - 1.0) < 1e-6                 # 两段各归一后按权重拼接，总和≈1


def test_same_image_high_sim_recolored_low(tmp_path):
    import pytest
    Image = pytest.importorskip("PIL.Image")

    def make(color):
        im = Image.new("RGB", (64, 64), (10, 10, 10))
        for y in range(0, 30):
            for x in range(0, 64):
                im.putpixel((x, y), color)
        q = tmp_path / f"{color}.png"; im.save(q)
        return hc._hair_fingerprint(str(q), bins=12, grid=4, hue_weight=0.5, head_frac=0.55)

    red_a = make((210, 30, 30))
    red_b = make((205, 35, 35))
    blue = make((30, 30, 210))     # 发色大改（红→蓝）
    assert hc.hair_sim(red_a, red_b) > hc.hair_sim(red_a, blue)
