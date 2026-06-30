"""从本目录跑：cd skills/n2d-review/scripts && python -m pytest test_style_consistency.py"""
import style_consistency as sc


def test_channel_hist_normalizes():
    h = sc.channel_hist([0.0, 0.5, 0.99], bins=4)
    assert abs(sum(h) - 1.0) < 1e-9
    assert h[0] > 0 and h[-1] > 0


def test_channel_hist_empty_is_zero():
    assert sc.channel_hist([], bins=4) == [0.0, 0.0, 0.0, 0.0]


def test_fingerprint_assembles_with_edge_weight():
    fp = sc.style_fingerprint([0.5, 0.5], [0.25, 0.75], 0.3)
    assert fp == [0.5, 0.5, 0.25, 0.75, 0.3, 0.3, 0.3, 0.3]  # EDGE_WEIGHT_DIMS=4


def test_cohesion_identical_fps_are_one():
    fps = [[1.0, 0.0, 0.0]] * 3
    cs = sc.cohesion_scores(fps)
    assert all(abs(c - 1.0) < 1e-9 for c in cs)


def test_cohesion_flags_the_outlier_lowest():
    # 三张相似 + 一张正交离群 → 离群那张内聚度最低
    fps = [[1.0, 0.0], [0.99, 0.01], [0.98, 0.02], [0.0, 1.0]]
    cs = sc.cohesion_scores(fps)
    assert cs.index(min(cs)) == 3


def test_median():
    assert sc.median([0.2, 0.9, 0.5]) == 0.5
    assert sc.median([0.2, 0.8]) == 0.5
    assert sc.median([]) == 0.0


def test_style_band_median_centered():
    # median-中心：正常波动(略低于中位)放行，只有显著低于中位才漂
    med, margin = 0.90, 0.06
    assert sc.style_band(0.88, med, margin) == "ok"      # 中位下 0.02，正常波动
    assert sc.style_band(0.83, med, margin) == "warn"    # [median-2m, median-m)
    assert sc.style_band(0.70, med, margin) == "block"   # 真离群
    assert sc.style_band(0.95, med, margin) == "ok"      # 高于中位


# ── 跨集画风基线（集级指纹 vs 基线集）单测 ──

def test_mean_fingerprint():
    assert sc.mean_fingerprint([[1.0, 0.0], [0.0, 1.0]]) == [0.5, 0.5]
    assert sc.mean_fingerprint([]) is None
    assert sc.mean_fingerprint([[1.0], [1.0, 2.0]]) is None  # 维度不齐不硬凑


def test_cross_band_thresholds():
    assert sc.cross_band(0.01) == "ok"
    assert sc.cross_band(sc.CROSS_EP_WARN + 0.01) == "warn"
    assert sc.cross_band(sc.CROSS_EP_BLOCK + 0.01) == "block"
    assert sc.cross_band(None) == "skipped"


def test_ep_num_sort_key():
    assert sc._ep_num("第3集") == 3
    assert sc._ep_num("封面") == 10**9
