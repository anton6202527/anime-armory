#!/usr/bin/env python3
"""axis_geometry 纯数学核心单测。

跑：cd skills/n2d/n2d-review/scripts && python -m pytest test_axis_geometry.py
（只覆盖无依赖的纯几何：facing_from_kps / facing_sign / screen_side / axis_break / axis_band；
不触 insightface 图像层。）
"""
from __future__ import annotations

import axis_geometry as ag


# ---------- facing_from_kps ----------

def test_facing_from_kps_zero_inter_eye_guard():
    # 双眼重合 → 无瞳距尺度 → 不臆造朝向，返回 0.0
    assert ag.facing_from_kps(50.0, 50.0, 80.0) == 0.0


def test_facing_from_kps_frontal_is_near_zero():
    # 鼻尖恰在双眼中点 → 正脸 ≈ 0
    assert ag.facing_from_kps(40.0, 60.0, 50.0) == 0.0


def test_facing_from_kps_faces_right_positive():
    # 鼻尖在眼中点右侧 → 朝右 → 正
    val = ag.facing_from_kps(40.0, 60.0, 56.0)  # eye_mid=50, inter=20 → (56-50)/20=0.3
    assert val > 0
    assert abs(val - 0.3) < 1e-9


def test_facing_from_kps_faces_left_negative():
    # 鼻尖在眼中点左侧 → 朝左 → 负
    val = ag.facing_from_kps(40.0, 60.0, 44.0)  # (44-50)/20 = -0.3
    assert val < 0
    assert abs(val + 0.3) < 1e-9


def test_facing_from_kps_clamped_to_unit_range():
    # 极端鼻偏 → 钳到 [-1,1]
    assert ag.facing_from_kps(40.0, 60.0, 200.0) == 1.0
    assert ag.facing_from_kps(40.0, 60.0, -200.0) == -1.0


# ---------- facing_sign ----------

def test_facing_sign_deadzone_is_zero():
    assert ag.facing_sign(0.0) == 0
    assert ag.facing_sign(0.05) == 0      # 在默认 0.08 带内
    assert ag.facing_sign(-0.05) == 0


def test_facing_sign_outside_deadzone():
    assert ag.facing_sign(0.2) == 1
    assert ag.facing_sign(-0.2) == -1


def test_facing_sign_boundary_inclusive():
    # 恰在 deadzone 边界 → 计为该侧（>=/<=）
    assert ag.facing_sign(0.08) == 1
    assert ag.facing_sign(-0.08) == -1


def test_facing_sign_custom_deadzone():
    assert ag.facing_sign(0.2, deadzone=0.3) == 0
    assert ag.facing_sign(0.4, deadzone=0.3) == 1


# ---------- screen_side ----------

def test_screen_side_left_center_right():
    assert ag.screen_side(50.0, 1000.0) == -1    # 远左
    assert ag.screen_side(500.0, 1000.0) == 0    # 正中
    assert ag.screen_side(950.0, 1000.0) == 1    # 远右


def test_screen_side_center_deadzone():
    # 偏离中线 < 10% 图宽 → 居中
    assert ag.screen_side(540.0, 1000.0) == 0    # offset 0.04
    assert ag.screen_side(620.0, 1000.0) == 1    # offset 0.12


def test_screen_side_zero_width_guard():
    assert ag.screen_side(123.0, 0.0) == 0


# ---------- axis_break ----------

def test_axis_break_opposite_facing_true():
    # 朝右(+1)→朝左(-1)，同侧 → 朝向反转越轴
    assert ag.axis_break(1, 1, -1, 1) is True


def test_axis_break_same_facing_false():
    # 朝向一致、同侧 → 不越轴
    assert ag.axis_break(1, 1, 1, 1) is False


def test_axis_break_frontal_never_breaks():
    # 任一镜正脸(0) → 朝向模糊，不判越轴（且若两侧居中也不判）
    assert ag.axis_break(0, 0, 1, 0) is False
    assert ag.axis_break(-1, 0, 0, 0) is False


def test_axis_break_side_jump_true():
    # 朝向都一致(无反转)，但屏幕从左(-1)跳到右(+1) → 跳边越轴
    assert ag.axis_break(1, -1, 1, 1) is True


def test_axis_break_side_center_no_jump():
    # 一侧居中(0) → 跳边不成立；朝向也未反转 → False
    assert ag.axis_break(1, 0, 1, 1) is False


# ---------- axis_band ----------

def test_axis_band_warn_only():
    # 检出越轴 → warn（永不 block）
    assert ag.axis_band(1) == "warn"
    assert ag.axis_band(3) == "warn"


def test_axis_band_ok_when_none():
    assert ag.axis_band(0) == "ok"
    assert ag.axis_band(-1) == "ok"
