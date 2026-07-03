"""scale_consistency 纯数学核心单测。

cd skills/n2d-review/scripts && python -m pytest test_scale_consistency.py
"""
import scale_consistency as sc


# ---------- expected_ratio ----------

def test_expected_ratio_basic():
    assert sc.expected_ratio(180, 90) == 2.0


def test_expected_ratio_auto_orders_args():
    # 入参顺序无关，恒返回 大/小 ≥ 1
    assert sc.expected_ratio(90, 180) == 2.0
    assert sc.expected_ratio(172, 168) == sc.expected_ratio(168, 172)


def test_expected_ratio_equal_heights():
    assert sc.expected_ratio(168, 168) == 1.0


def test_expected_ratio_always_ge_one():
    for a, b in [(160, 200), (200, 160), (150, 151)]:
        assert sc.expected_ratio(a, b) >= 1.0


def test_expected_ratio_divide_by_zero_guard():
    # 任一 ≤0（缺/脏数据）→ 回退 1.0，绝不抛 ZeroDivisionError
    assert sc.expected_ratio(170, 0) == 1.0
    assert sc.expected_ratio(0, 0) == 1.0
    assert sc.expected_ratio(0, 170) == 1.0
    assert sc.expected_ratio(-5, 170) == 1.0


# ---------- ratio_band ----------

def test_ratio_band_ok_exact_match():
    assert sc.ratio_band(1.0, 1.0) == "ok"
    assert sc.ratio_band(2.0, 2.0) == "ok"


def test_ratio_band_ok_within_warn_tol():
    # 偏差 0.2 < warn_tol 0.25 → ok
    assert sc.ratio_band(1.2, 1.0) == "ok"


def test_ratio_band_warn_at_boundary():
    # 偏差 == warn_tol(0.25) → warn（含下界）
    assert sc.ratio_band(1.25, 1.0) == "warn"


def test_ratio_band_warn_below_block_tol():
    # 0.25 <= dev < 0.5 → warn
    assert sc.ratio_band(1.4, 1.0) == "warn"


def test_ratio_band_block_at_boundary():
    # 偏差 == block_tol(0.5) → block（含下界，block 优先）
    assert sc.ratio_band(1.5, 1.0) == "block"


def test_ratio_band_block_extreme():
    # 渲染一头是另一头两倍量级，登记约等高 → block
    assert sc.ratio_band(2.0, 1.0) == "block"


def test_ratio_band_symmetric_deviation():
    # 比期望小同样判（一人被画矮）
    assert sc.ratio_band(0.5, 1.0) == "block"


def test_ratio_band_custom_tolerances():
    # 自定义容差：放宽 warn 到 0.4，则 0.3 偏差降为 ok
    assert sc.ratio_band(1.3, 1.0, warn_tol=0.4, block_tol=0.8) == "ok"
    # 收紧 warn 到 0.05，则 0.1 偏差升为 warn
    assert sc.ratio_band(1.1, 1.0, warn_tol=0.05, block_tol=0.8) == "warn"
    # 自定义 block 边界
    assert sc.ratio_band(1.3, 1.0, warn_tol=0.1, block_tol=0.3) == "block"


def test_ratio_band_expected_non_positive_is_ok():
    # expected <= 0（无可比基准）→ 不臆判，一律 ok
    assert sc.ratio_band(5.0, 0.0) == "ok"
    assert sc.ratio_band(5.0, -1.0) == "ok"


def test_ratio_band_relative_not_absolute():
    # 用相对偏差：期望 2.0 时偏差 0.4 绝对值大，但相对 0.2 → ok
    assert sc.ratio_band(2.4, 2.0) == "ok"
