"""face_compare_stitch 单测——纯几何排版 + 绘制 best-effort。

cd skills/n2d-review/scripts && python3 -m pytest test_face_compare_stitch.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("face_compare_stitch.py")
spec = importlib.util.spec_from_file_location("face_compare_stitch", SCRIPT)
fcs = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fcs)


def test_panel_size_keeps_aspect() -> None:
    assert fcs.panel_size(1024, 512, target_w=512) == (512, 256)
    assert fcs.panel_size(512, 1024, target_w=512) == (512, 1024)
    # 非法尺寸 → 方形占位，不除零
    assert fcs.panel_size(0, 0, target_w=512) == (512, 512)
    assert fcs.panel_size(-5, 10, target_w=256) == (256, 256)


def test_canvas_size_two_panels() -> None:
    # 两个 512×256 面板：宽=pad*2 + 512*2 + gap；高=pad*2 + label + max_h
    w, h = fcs.canvas_size([(512, 256), (512, 256)])
    assert w == fcs.PAD * 2 + 512 * 2 + fcs.PANEL_GAP
    assert h == fcs.PAD * 2 + fcs.LABEL_H + 256
    # 空 → 仅内边距
    assert fcs.canvas_size([]) == (fcs.PAD * 2, fcs.PAD * 2)


def test_build_comparison_no_panels_is_false() -> None:
    assert fcs.build_comparison([], "/tmp/none.png") is False


def test_build_comparison_creates_png(tmp_path: Path) -> None:
    Image = None
    try:
        from PIL import Image  # type: ignore
    except Exception:
        pytest.skip("无 Pillow——跳过实际绘制（纯几何已覆盖）")
    ref = tmp_path / "ref.png"
    shot = tmp_path / "shot.png"
    Image.new("RGB", (400, 600), (200, 120, 120)).save(ref)
    Image.new("RGB", (400, 600), (120, 120, 200)).save(shot)
    out = tmp_path / "sub" / "compare.png"
    ok = fcs.build_comparison([("参考·定妆_沈念", str(ref)), ("本镜·Clip_12", str(shot))], str(out))
    assert ok is True
    assert out.is_file()
    with Image.open(out) as im:
        assert im.size == fcs.canvas_size([(512, 768), (512, 768)])


def test_build_comparison_missing_image_draws_placeholder(tmp_path: Path) -> None:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        pytest.skip("无 Pillow")
    out = tmp_path / "compare.png"
    # 两个面板都读不到图 → 仍出图（占位框），返回 True
    ok = fcs.build_comparison([("参考", str(tmp_path / "nope1.png")),
                               ("本镜", str(tmp_path / "nope2.png"))], str(out))
    assert ok is True and out.is_file()
