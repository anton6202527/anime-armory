#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""风格基准指纹跨话回归 + 相邻格连续性 + 黑白灰量化 + 签收 sha 绑定。

运行：cd skills/comic-review/scripts && python3 -m pytest test_style_baseline_and_tone.py
需要 Pillow；未安装时跳过像素级用例。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import style_consistency

pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def test_only_explicit_context_can_clear_global_block() -> None:
    assert style_consistency.explicit_context_override("block", "ok", True) is True
    assert style_consistency.explicit_context_override("warn", "ok", True) is True
    assert style_consistency.explicit_context_override("block", "ok", False) is False
    assert style_consistency.explicit_context_override("block", "warn", True) is False


def write_panel(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (200, 200)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def make_project(root: Path, chapter: str, colors: list[tuple[int, int, int]], anchors: list[str]) -> None:
    (root / "生产数据").mkdir(parents=True, exist_ok=True)
    panels = []
    for idx, (color, anchor) in enumerate(zip(colors, anchors), 1):
        pid = f"P{idx:03d}"
        panels.append({"panel_id": pid, "description": "画面", "location": "屋内", "scene_anchor_id": anchor})
        write_panel(root / "出图" / chapter / "panels" / f"{pid}.png", color)
    (root / "脚本" / chapter).mkdir(parents=True, exist_ok=True)
    (root / "脚本" / chapter / "panel_script.json").write_text(
        json.dumps({"panels": panels}, ensure_ascii=False), encoding="utf-8"
    )
    (root / "_设置.md").write_text("- 风格锚: STYLE_TEST\n", encoding="utf-8")


def test_baseline_created_then_drift_warns(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    grays = [(120, 120, 120)] * 5
    make_project(root, "第1话", grays, ["LOC_A"] * 5)

    report1 = style_consistency.analyze(root, "第1话")
    baseline_file = root / "出图" / "共享" / "style_baseline.json"
    assert baseline_file.is_file()
    assert json.loads(baseline_file.read_text(encoding="utf-8"))["source_chapter"] == "第1话"
    assert not any(f["code"] == "chapter_style_drift_from_baseline" for f in report1["findings"])

    # 第2话整话一起漂成高饱和红——话内相对比较发现不了，基准回归必须报
    reds = [(220, 30, 30)] * 5
    make_project(root, "第2话", reds, ["LOC_A"] * 5)
    report2 = style_consistency.analyze(root, "第2话")
    assert any(f["code"] == "chapter_style_drift_from_baseline" for f in report2["findings"])


def test_adjacent_same_anchor_grade_jump_warns(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    # 同场景锚相邻两格：暖亮 → 冷暗，冷暖+亮度双跳变
    colors = [(230, 190, 120), (40, 60, 150), (40, 60, 150), (40, 60, 150)]
    make_project(root, "第1话", colors, ["LOC_A", "LOC_A", "LOC_A", "LOC_A"])

    report = style_consistency.analyze(root, "第1话")

    jumps = [f for f in report["findings"] if f["code"] == "adjacent_panel_grade_jump"]
    assert jumps and jumps[0]["panel_id"] == "P002"


def test_tone_value_outlier_flags_black_heavy_panel(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    colors = [(200, 200, 200)] * 4 + [(3, 3, 3)]  # 最后一格黑场占比爆表
    make_project(root, "第1话", colors, ["LOC_A"] * 4 + ["LOC_B"])

    report = style_consistency.analyze(root, "第1话")

    outliers = [f for f in report["findings"] if f["code"] == "tone_value_outlier"]
    assert any(f["panel_id"] == "P005" for f in outliers)


def test_style_acceptance_sha_binding(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    (root / "生产数据").mkdir(parents=True)
    panel = root / "出图" / "第1话" / "panels" / "P001.png"
    write_panel(panel, (10, 10, 10))
    good_sha = style_consistency.file_sha256(panel)
    (root / "生产数据" / "style_consistency_acceptance_第1话.json").write_text(
        json.dumps(
            {
                "accepted_findings": [
                    {"code": "tone_value_outlier", "panel_id": "P001", "reason": "夜戏黑场", "artifact_sha256": good_sha},
                    {"code": "internal_panel_gutters", "panel_id": "P002", "reason": "想洗掉 block"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    findings = [
        {"severity": "warn", "code": "tone_value_outlier", "panel_id": "P001", "artifact": "出图/第1话/panels/P001.png"},
        {"severity": "block", "code": "internal_panel_gutters", "panel_id": "P002", "artifact": "出图/第1话/panels/P002.png"},
    ]
    notes: list[str] = []

    style_consistency.apply_manual_acceptances(root, "第1话", findings, notes)

    assert findings[0]["severity"] == "info"
    assert findings[1]["severity"] == "block"
    assert any("不可签收" in note for note in notes)
