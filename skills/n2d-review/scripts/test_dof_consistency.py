"""dof_consistency 单测——景深代理纯数学 + 自标定离群 + 优雅跳过。

cd skills/n2d-review/scripts && python3 -m pytest test_dof_consistency.py
"""
from __future__ import annotations

from pathlib import Path

import dof_consistency as dof


def test_median():
    assert dof.median([]) == 0.0
    assert dof.median([3, 1, 2]) == 2
    assert dof.median([1, 2, 3, 4]) == 2.5


def _grid(fn):
    return [[float(fn(x, y)) for x in range(16)] for y in range(16)]


def test_dof_ratio_deep_vs_shallow():
    # 深焦：全图都有细节（棋盘）→ 背景/主体清晰度相近 → 比值接近 1
    deep = _grid(lambda x, y: 255 if (x + y) % 2 else 0)
    rd = dof.dof_ratio(deep)
    assert rd is not None and rd > 0.7
    # 浅景深：只有中心有细节、四周平坦 → 背景清晰度低 → 比值明显 < 深焦
    def shallow_fn(x, y):
        c = 4 <= x < 12 and 4 <= y < 12
        return (255 if (x + y) % 2 else 0) if c else 128
    rs = dof.dof_ratio(_grid(shallow_fn))
    assert rs is not None and rs < rd


def test_dof_ratio_flat_center_returns_none():
    # 主体区全平（清晰度≈0）→ 无法判，返回 None（不假报）。
    # 细节只在最外两圈，给中心区(含其右/下边界 read-ahead)留出平坦缓冲，避免边界细节漏入。
    def fn(x, y):
        border = x < 2 or x >= 14 or y < 2 or y >= 14
        return (255 if (x + y) % 2 else 0) if border else 128
    assert dof.dof_ratio(_grid(fn)) is None


def test_analyze_skips_without_pillow(monkeypatch):
    monkeypatch.setattr(dof.scn, "_probe_pillow", lambda: False)
    res = dof.analyze("/nonexistent", "第1集")
    assert res["available"] is False and res["shots"] == []
    assert any("Pillow" in n for n in res["notes"])


def test_analyze_flags_intra_scene_dof_outlier(tmp_path: Path, monkeypatch):
    from PIL import Image
    if not dof.scn._probe_pillow():
        return
    root = tmp_path / "剧"
    imgdir = root / "出图" / "第1集"
    imgdir.mkdir(parents=True)

    def _save(name, shallow):
        im = Image.new("L", (64, 64), 128)
        px = im.load()
        rng = range(20, 44) if shallow else range(0, 64)   # 浅:仅中心细节; 深:全图细节
        for y in rng:
            for x in rng:
                px[x, y] = 255 if (x + y) % 2 else 0
        im.save(imgdir / name)

    _save("EP01_CLIP01.png", shallow=False)   # 深焦
    _save("EP01_CLIP02.png", shallow=False)   # 深焦
    _save("EP01_CLIP03.png", shallow=True)    # 浅景深离群
    # 三镜同属一个场景（绕过 01_分镜出图.md 解析，直接喂场景映射）
    monkeypatch.setattr(dof.scn, "_scene_of_shot", lambda r, e: {
        "EP01_CLIP01.png": "冷宫", "EP01_CLIP02.png": "冷宫", "EP01_CLIP03.png": "冷宫"})
    res = dof.analyze(str(root), "第1集")
    assert res["available"] is True
    warns = [s for s in res["shots"] if s["verdict"] == "warn"]
    assert any(s["png"] == "EP01_CLIP03.png" for s in warns)   # 浅景深镜被标横跳
