"""scene_consistency 纯数学单测 + O3 图像路径回归（PIL 缺则 skip）。
cd skills/n2d-review/scripts && python -m pytest test_scene_consistency.py
"""
import scene_consistency as sc


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
