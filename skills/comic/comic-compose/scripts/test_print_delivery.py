from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image


MODULE_PATH = Path(__file__).with_name("print_delivery.py")
SPEC = importlib.util.spec_from_file_location("comic_print_delivery", MODULE_PATH)
assert SPEC and SPEC.loader
print_delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(print_delivery)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_print_contract_refuses_sub_300_dpi(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="300"):
        print_delivery.init_contract(
            tmp_path, "第1话", trim_width_mm=176, trim_height_mm=250,
            bleed_mm=3.2, safe_mm=6.4, dpi=150, binding_edge="left",
            reading_direction="ltr", color_mode="RGB",
            icc_policy="printer_managed_srgb", icc_profile_name="sRGB",
            vendor_profile="custom", vendor_requirement_evidence="vendor spec",
        )


def test_kdp_profile_records_current_vendor_constraints(tmp_path: Path) -> None:
    path = print_delivery.init_contract(
        tmp_path, "第1话", trim_width_mm=176, trim_height_mm=250,
        bleed_mm=3.2, safe_mm=6.4, dpi=300, binding_edge="left",
        reading_direction="ltr", color_mode="RGB",
        icc_policy="printer_managed_srgb", icc_profile_name="sRGB",
        vendor_profile="kdp", vendor_requirement_evidence="",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["vendor_rules"]["single_pages_not_spreads"] is True
    assert payload["vendor_rules"]["crop_marks"] is False
    assert "G201857950" in payload["vendor_requirement_evidence"]


def test_print_receipt_binds_current_contract_and_pdf_sha(tmp_path: Path) -> None:
    page = tmp_path / "排版" / "第1话" / "pages" / "page_001.png"
    page.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 32)).save(page)
    pdf = tmp_path / "排版" / "第1话" / "print" / "第1话.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    Image.open(page).save(pdf, "PDF", resolution=300)
    document = {"path": str(pdf.relative_to(tmp_path)), "format": "pdf", "sha256": print_delivery.sha256_file(pdf)}
    write_json(tmp_path / "排版" / "第1话" / "export_manifest.json", {
        "pages": [{"path": str(page.relative_to(tmp_path))}], "documents": [document],
    })
    contract = print_delivery.init_contract(
        tmp_path, "第1话", trim_width_mm=5.4187, trim_height_mm=2.7093,
        bleed_mm=0, safe_mm=0.5, dpi=300, binding_edge="left",
        reading_direction="ltr", color_mode="RGB",
        icc_policy="printer_managed_srgb", icc_profile_name="sRGB IEC61966-2.1",
        vendor_profile="custom", vendor_requirement_evidence="vendor spec",
    )
    receipt = print_delivery.create_readiness_receipt(
        tmp_path, "第1话", reviewer="print-editor", reason="逐页检查",
        confirmed_checks={
            "safe_area_content_clear": True,
            "page_order_and_binding_correct": True,
            "color_and_icc_match_vendor": True,
            "font_handling_and_license_confirmed": True,
        },
    )
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["contract"]["sha256"] == print_delivery.sha256_file(contract)
    assert payload["pdf"]["sha256"] == print_delivery.sha256_file(pdf)
