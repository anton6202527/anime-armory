#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reference_composite 与参考槽位分配的回归测试。"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
COMIC_LIB = SCRIPT_DIR.parents[1] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))

from PIL import Image

import codex_panel_runner as runner
import reference_composite
from image_backend_adapter import resolve_capabilities


def make_png(path: Path, size: tuple[int, int] = (64, 80), color: tuple[int, int, int] = (200, 30, 30)) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format="PNG")
    return runner.file_sha256(path)


def record(root: Path, rid: str, name: str, role: str, *, required: bool = False) -> dict:
    path = root / "出图" / "共享" / "图片" / name
    sha = make_png(path)
    return {
        "id": rid,
        "path": str(path.relative_to(root)),
        "abs_path": str(path),
        "sha256": sha,
        "role": role,
        "required": required,
    }


def test_executable_limit_is_single_sourced() -> None:
    codex = resolve_capabilities("GPT Image 2", "Codex CLI")
    assert codex.executable_attachment_limit == 5
    assert codex.reference_image_limit == 16
    dreamina = resolve_capabilities("Dreamina 5.0", "Dreamina/即梦官方 CLI")
    assert dreamina.executable_attachment_limit == dreamina.reference_image_limit == 10
    # runner 常量必须来自适配层，不允许双写
    assert runner.CODEX_IMAGE_GENERATION_REFERENCE_LIMIT == 5


def test_style_anchor_gets_reserved_slot() -> None:
    records = [
        {"id": "CHAR_A", "role": "front", "required": True, "path": "a1"},
        {"id": "CHAR_A", "role": "face", "required": False, "path": "a2"},
        {"id": "CHAR_B", "role": "front", "required": False, "path": "b1"},
        {"id": "LOC_X", "role": "location", "required": True, "path": "l1"},
        {"id": "STYLE_MAIN", "role": "style", "required": False, "path": "s1"},
    ]
    selected, omitted = runner.select_reference_attachments(records, 4)
    selected_ids = [item["id"] for item in selected]
    assert "STYLE_MAIN" in selected_ids, "风格锚必须保底占一个物理参考槽"
    assert "CHAR_A" in selected_ids and "CHAR_B" in selected_ids and "LOC_X" in selected_ids
    assert [item["id"] for item in omitted] == ["CHAR_A"], "被省略的只能是同主体的次要视图"


def test_compact_under_limit_is_noop(tmp_path: Path) -> None:
    records = [record(tmp_path, "CHAR_A", "a_front.png", "front", required=True)]
    out, disclosure = reference_composite.compact_records_with_composites(tmp_path, records, 4)
    assert out == records
    assert disclosure["applied"] is False


def test_compact_folds_multi_view_subjects(tmp_path: Path) -> None:
    records = [
        record(tmp_path, "CHAR_A", "a_front.png", "front", required=True),
        record(tmp_path, "CHAR_A", "a_face.png", "face"),
        record(tmp_path, "CHAR_A", "a_tq.png", "three_quarter"),
        record(tmp_path, "CHAR_B", "b_front.png", "front", required=True),
        record(tmp_path, "CHAR_B", "b_face.png", "face"),
        record(tmp_path, "LOC_X", "loc.png", "location", required=True),
        record(tmp_path, "STYLE_MAIN", "style.png", "style"),
    ]
    out, disclosure = reference_composite.compact_records_with_composites(tmp_path, records, 4)
    assert disclosure["applied"] is True
    ids = [item["id"] for item in out]
    # 7 条声明折叠成 4 条物理附件：两个主体各 1 拼板 + LOC + STYLE
    assert ids == ["CHAR_A", "CHAR_B", "LOC_X", "STYLE_MAIN"]
    composites = [item for item in out if item.get("composite")]
    assert {item["id"] for item in composites} == {"CHAR_A", "CHAR_B"}
    for item in composites:
        sheet = tmp_path / item["path"]
        assert sheet.is_file() and sheet.suffix == ".png"
        assert item["sha256"] == runner.file_sha256(sheet)
        assert all(part["sha256"] for part in item["parts"])
    assert reference_composite.attachment_equivalent_count(out) == 7
    # 折叠后全部塞进上限，选择器不再需要省略任何契约
    selected, omitted = runner.select_reference_attachments(out, 4)
    assert len(selected) == 4 and not omitted


def test_compact_cache_is_content_addressed(tmp_path: Path) -> None:
    records = [
        record(tmp_path, "CHAR_A", "a_front.png", "front", required=True),
        record(tmp_path, "CHAR_A", "a_face.png", "face"),
        record(tmp_path, "CHAR_B", "b1.png", "front"),
        record(tmp_path, "LOC_X", "loc.png", "location"),
        record(tmp_path, "STYLE_MAIN", "style.png", "style"),
    ]
    first, _ = reference_composite.compact_records_with_composites(tmp_path, records, 4)
    second, _ = reference_composite.compact_records_with_composites(tmp_path, records, 4)
    sheet_first = next(item for item in first if item.get("composite"))
    sheet_second = next(item for item in second if item.get("composite"))
    assert sheet_first["path"] == sheet_second["path"]
    assert sheet_first["sha256"] == sheet_second["sha256"]


def test_post_qc_counts_composite_parts_as_attached(tmp_path: Path) -> None:
    panel = tmp_path / "出图" / "第1话" / "panels" / "P001.png"
    make_png(panel, size=(1296, 1040))
    records = [
        record(tmp_path, "CHAR_A", "a_front.png", "front", required=True),
        record(tmp_path, "CHAR_A", "a_face.png", "face"),
        record(tmp_path, "STYLE_MAIN", "style.png", "style"),
    ]
    compacted, disclosure = reference_composite.compact_records_with_composites(tmp_path, records, 2)
    assert disclosure["applied"] is True
    job = {
        "panel_id": "P001",
        "size": {"width": 1296, "height": 1040},
        "references": [
            {"id": "CHAR_A", "path": records[0]["path"]},
            {"id": "CHAR_A", "path": records[1]["path"]},
            {"id": "STYLE_MAIN", "path": records[2]["path"]},
        ],
    }
    payload = runner.post_qc_panel(tmp_path, "第1话", job, panel, compacted, [])
    assert payload["attached_equivalent_count"] == 3
    assert payload["composite_attachment_count"] == 1
    assert not [issue for issue in payload["issues"] if issue["category"] == "reference"], (
        "拼板部件应计入已附着参考，不得误报 unresolved reference"
    )
