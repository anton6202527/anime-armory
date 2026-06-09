"""quality_check 纯数学单测（无需 Pillow）。
cd skills/n2d-review/scripts && python -m pytest test_quality_check.py
"""
import quality_check as q


def test_laplacian_flat_is_zero():
    flat = [[100.0] * 5 for _ in range(5)]
    assert q.laplacian_variance(flat) == 0.0


def test_laplacian_edge_positive():
    # 左黑右白的竖直边 → 内部有非零 Laplacian → 方差>0
    img = [[0.0, 0.0, 255.0, 255.0, 255.0] for _ in range(5)]
    assert q.laplacian_variance(img) > 0.0


def test_laplacian_small_image():
    assert q.laplacian_variance([[1.0, 2.0]]) == 0.0
    assert q.laplacian_variance([[1.0], [2.0], [3.0]]) == 0.0  # 宽<3


def test_median():
    assert q.median([3, 1, 2]) == 2
    assert q.median([4, 1, 3, 2]) == 2.5
    assert q.median([]) == 0.0
    assert q.median([7]) == 7


def test_blur_band():
    med = 100.0
    assert q.blur_band(90, med) == "ok"          # ≥0.6*med
    assert q.blur_band(60, med) == "ok"          # =0.6*med 放行
    assert q.blur_band(55, med) == "warn"        # [0.4,0.6)*med
    assert q.blur_band(30, med) == "block"       # <0.4*med
    assert q.blur_band(10, 0.0) == "ok"          # 无参考中位数 → 不误杀


# ---------- O3 图像路径回归（合成图·缺 PIL 跳过） ----------

def test_gray2d_and_variance_image_path(tmp_path):
    import pytest
    Image = pytest.importorskip("PIL.Image")
    # 平整纯色 → Laplacian 方差≈0；棋盘 → 方差>0
    flat = Image.new("L", (32, 32), 128)
    pf = tmp_path / "flat.png"; flat.save(pf)
    gf = q._gray_2d(str(pf), size=32)
    assert gf is not None and q.laplacian_variance(gf) == 0.0
    board = Image.new("L", (32, 32))
    for y in range(32):
        for x in range(32):
            board.putpixel((x, y), 255 if (x + y) % 2 == 0 else 0)
    pb = tmp_path / "board.png"; board.save(pb)
    gb = q._gray_2d(str(pb), size=32)
    assert gb is not None and q.laplacian_variance(gb) > 0.0
