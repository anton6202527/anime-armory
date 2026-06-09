"""face_consistency 纯数学单测（无需 insightface/GPU）。
cd skills/n2d-review/scripts && python -m pytest test_face_consistency.py
"""
import math
import face_consistency as fc


def test_cosine_basic():
    assert fc.cosine([1, 0], [1, 0]) == 1.0
    assert abs(fc.cosine([1, 0], [0, 1])) < 1e-9
    assert fc.cosine([1, 0], [-1, 0]) == -1.0
    assert fc.cosine([0, 0], [1, 1]) == 0.0  # 零向量保护


def test_cosine_dim_mismatch():
    try:
        fc.cosine([1, 2, 3], [1, 2])
        assert False
    except ValueError:
        pass


def test_calibrate_floor_takes_min():
    assert fc.calibrate_floor([0.9, 0.7, 0.82]) == 0.7


def test_calibrate_floor_fallback_when_single():
    # 单张定妆（无内部对）→ 回退保守同人下限
    assert fc.calibrate_floor([]) == 0.50
    assert fc.calibrate_floor([], fallback=0.55) == 0.55


def test_band_three_zones():
    floor = 0.70  # warn 区 = [0.62, 0.70)，block = <0.62
    assert fc.band(0.80, floor, margin=0.08) == "ok"      # ≥floor
    assert fc.band(0.70, floor, margin=0.08) == "ok"      # =floor 放行
    assert fc.band(0.66, floor, margin=0.08) == "warn"    # floor-margin..floor
    assert fc.band(0.64, floor, margin=0.08) == "warn"    # 区内
    assert fc.band(0.60, floor, margin=0.08) == "block"   # <floor-margin
    assert fc.band(0.20, floor, margin=0.08) == "block"


def test_is_character_asset():
    assert fc.is_character_asset("王敦")
    assert fc.is_character_asset("少年王敦")
    assert not fc.is_character_asset("灵药谷山洞")   # 场景
    assert not fc.is_character_asset("淡青系统符纹光幕")  # 特效
    assert not fc.is_character_asset("豆油灯")        # 道具(灯)
    assert not fc.is_character_asset("未来神界主桌剪影")  # 剪影


def test_severity_order():
    assert fc._sev("block") > fc._sev("warn") > fc._sev("ok") > fc._sev("noface")


def test_anchor_verdict():
    assert fc.anchor_verdict(0, 0.0) == "block"                  # 锚点没脸
    assert fc.anchor_verdict(2, 0.3) == "block"                  # 多张脸
    assert fc.anchor_verdict(1, 0.02, min_ratio=0.06) == "warn"  # 脸太小
    assert fc.anchor_verdict(1, 0.20, min_ratio=0.06) == "ok"    # 单张够大正脸
    assert fc.anchor_verdict(1, 0.06, min_ratio=0.06) == "ok"    # 等于下限放行
