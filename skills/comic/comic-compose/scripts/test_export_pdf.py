from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from PIL import Image


SCRIPT = Path(__file__).with_name("export_longstrip.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_pdf_only_export_writes_real_registered_document_without_raster_fallback(tmp_path: Path) -> None:
    root = tmp_path / "作品"
    panel = root / "出图" / "第1话" / "panels" / "P001.png"
    panel.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 32), (20, 40, 80)).save(panel)
    write_json(root / "排版" / "第1话" / "layout.json", {
        "segments": [{
            "segment_id": "S001", "width": 64, "height": 32,
            "reading_order": ["P001"],
            "panels": [{"panel_id": "P001", "x": 0, "y": 0, "w": 64, "h": 32, "bubble_slots": []}],
        }],
    })
    (root / "_设置.md").write_text("- 导出格式: pdf\n- 目标平台: 通用\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(root), "--chapter", "第1话", "--formats", "pdf", "--render", "--no-lettering"],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    manifest = json.loads((root / "排版" / "第1话" / "export_manifest.json").read_text(encoding="utf-8"))
    assert manifest["rendered"] == []
    assert manifest["format_fulfillment"]["verdict"] == "pass"
    assert manifest["delivery_mediums"] == ["print_pdf"]
    assert len(manifest["documents"]) == 1
    document = manifest["documents"][0]
    pdf = root / document["path"]
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert document["format"] == "pdf"
    assert document["page_count"] == 1
    assert document["font_handling"]["mode"] == "rasterized"
    assert document["source_pages"][0]["has_alpha"] is False


def test_requested_pdf_without_render_is_explicitly_unfulfilled(tmp_path: Path) -> None:
    root = tmp_path / "作品"
    panel = root / "出图" / "第1话" / "panels" / "P001.png"
    panel.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8)).save(panel)
    write_json(root / "排版" / "第1话" / "layout.json", {
        "segments": [{"width": 8, "height": 8, "panels": [{"panel_id": "P001", "x": 0, "y": 0, "w": 8, "h": 8}]}],
    })
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(root), "--formats", "pdf", "--no-lettering"],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0
    manifest = json.loads((root / "排版" / "第1话" / "export_manifest.json").read_text(encoding="utf-8"))
    assert manifest["documents"] == []
    assert manifest["format_fulfillment"]["verdict"] == "block"
    assert manifest["format_fulfillment"]["missing"] == ["pdf"]
    assert "pdf_export_error" in manifest


def test_kuaikan_profile_writes_real_300dpi_png_metadata(tmp_path: Path) -> None:
    root = tmp_path / "作品"
    panel = root / "出图" / "第1话" / "panels" / "P001.png"
    panel.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1280, 10)).save(panel)
    write_json(root / "排版" / "第1话" / "layout.json", {
        "segments": [{
            "width": 1280, "height": 10,
            "panels": [{"panel_id": "P001", "x": 0, "y": 0, "w": 1280, "h": 10}],
        }],
    })
    (root / "_设置.md").write_text("- 目标平台: 快看漫画投稿\n- 导出格式: png\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(root), "--formats", "png", "--render", "--no-lettering"],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads((root / "排版" / "第1话" / "export_manifest.json").read_text(encoding="utf-8"))
    output = root / manifest["rendered"][0]["path"]
    with Image.open(output) as image:
        assert image.mode == "RGB"
        assert abs(float(image.info["dpi"][0]) - 300) < 2
    assert manifest["rendered"][0]["dpi"] == 300.0
    assert "platform_dpi_mismatch" not in {item["code"] for item in manifest["platform_findings"]}
