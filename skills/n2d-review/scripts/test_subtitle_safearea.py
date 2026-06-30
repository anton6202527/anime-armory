#!/usr/bin/env python3
"""subtitle_safearea 纯数学单测。
cd skills/n2d-review/scripts && python -m pytest test_subtitle_safearea.py -q
"""
import subtitle_safearea as ssa


# ---------- in_subtitle_band ----------

def test_in_band_face_low_enters():
    # 脸下缘在底部 90% 处，默认带顶 0.82 → 进带
    assert ssa.in_subtitle_band(0.90) is True


def test_in_band_face_high_clears():
    # 脸下缘在画面中段 → 不进带
    assert ssa.in_subtitle_band(0.50) is False
    assert ssa.in_subtitle_band(0.81) is False


def test_in_band_boundary_inclusive():
    # 恰好贴带顶 → 算进带（含等号）
    assert ssa.in_subtitle_band(0.82) is True


def test_in_band_custom_band_top():
    assert ssa.in_subtitle_band(0.80, band_top_frac=0.75) is True
    assert ssa.in_subtitle_band(0.70, band_top_frac=0.75) is False
    assert ssa.in_subtitle_band(0.75, band_top_frac=0.75) is True


def test_in_band_full_bottom():
    assert ssa.in_subtitle_band(1.0) is True


# ---------- safearea_band ----------

def test_safearea_ok_when_none_in_band():
    assert ssa.safearea_band(0) == "ok"


def test_safearea_warn_when_any_in_band():
    assert ssa.safearea_band(1) == "warn"
    assert ssa.safearea_band(3) == "warn"


def test_safearea_never_blocks():
    # advisory：进带再多也只 warn，绝不 block
    for n in (0, 1, 5, 99):
        assert ssa.safearea_band(n) in ("ok", "warn")
