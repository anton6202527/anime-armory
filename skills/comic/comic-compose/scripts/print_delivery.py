#!/usr/bin/env python3
"""Scaffold and sign the comic print-delivery contract.

The contract describes measurable print geometry and color/font policy.  The
separate receipt records the human checks that cannot be inferred from pixels
and binds them to the current contract and PDF SHA.  Neither command claims to
be a printer upload or a PDF/X conversion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _margins(value: float) -> dict[str, float]:
    return {"top": value, "bottom": value, "inside": value, "outside": value}


def current_pdf(root: Path, chapter: str) -> tuple[Path, dict[str, Any]]:
    manifest = load_json(root / "排版" / chapter / "export_manifest.json", {})
    for item in manifest.get("documents") or []:
        if isinstance(item, Mapping) and str(item.get("format") or "").lower() == "pdf":
            path = root / str(item.get("path") or "")
            if path.is_file():
                return path, dict(item)
    raise ValueError("当前 export_manifest.json 没有已落盘 PDF；先用 export_longstrip.py --formats pdf --render")


def init_contract(
    root: Path,
    chapter: str,
    *,
    trim_width_mm: float,
    trim_height_mm: float,
    bleed_mm: float,
    safe_mm: float,
    dpi: int,
    binding_edge: str,
    reading_direction: str,
    color_mode: str,
    icc_policy: str,
    icc_profile_name: str,
    vendor_profile: str,
    vendor_requirement_evidence: str,
) -> Path:
    if min(trim_width_mm, trim_height_mm, bleed_mm, safe_mm) < 0 or trim_width_mm <= 0 or trim_height_mm <= 0:
        raise ValueError("trim 必须为正数，bleed/safe 不得为负数")
    if dpi < 300:
        raise ValueError("印刷合同 dpi 不得低于 300；低分辨率只能留在数字预览介质")
    if (reading_direction == "rtl" and binding_edge != "right") or (reading_direction == "ltr" and binding_edge != "left"):
        raise ValueError("reading_direction 与 binding_edge 不一致（rtl→right，ltr→left）")
    manifest = load_json(root / "排版" / chapter / "export_manifest.json", {})
    page_order = [str(item.get("path") or "") for item in manifest.get("pages") or [] if isinstance(item, Mapping)]
    vendor_key = str(vendor_profile or "custom").strip().lower()
    if vendor_key == "kdp" and abs(bleed_mm - 3.2) > 0.05:
        raise ValueError("KDP bleed profile requires 3.2 mm (0.125 in) bleed")
    if vendor_key == "kdp" and dpi < 300:
        raise ValueError("KDP interior images require at least 300 dpi")
    if vendor_key == "kdp" and not vendor_requirement_evidence:
        vendor_requirement_evidence = "https://kdp.amazon.com/en_US/help/topic/G201857950 (checked 2026-08-25)"
    payload = {
        "schema_version": 1,
        "kind": "comic_print_delivery_contract",
        "chapter": chapter,
        "document_role": "interior_pages",
        "vendor_profile": vendor_profile,
        "vendor_requirement_evidence": vendor_requirement_evidence,
        "geometry_mm": {
            "trim": {"width": trim_width_mm, "height": trim_height_mm},
            "bleed": _margins(bleed_mm),
            "safe_area": _margins(safe_mm),
        },
        "dpi": dpi,
        "binding": {
            "edge": binding_edge,
            "reading_direction": reading_direction,
            "duplex": True,
            "first_page_side": "recto",
        },
        "page_order": page_order,
        "font_handling": {
            "mode": "rasterized",
            "embedding_requirement": "not_applicable_after_flattening",
            "license_status": "must_be_cleared_in__meta_rights",
        },
        "color": {
            "mode": color_mode,
            "icc_policy": icc_policy,
            "icc_profile_name": icc_profile_name,
            "icc_profile_path": "",
        },
        "transparency_policy": "flattened",
        "vendor_rules": ({
            "single_pages_not_spreads": True,
            "crop_marks": False,
            "minimum_dpi": 300,
            "minimum_font_pt": 7,
            "bleed_mm": 3.2,
            "gutter_depends_on_page_count_and_trim": True,
            "gutter_must_be_confirmed_against_current_kdp_calculator": True,
            "font_mode": "rasterized_or_embedded",
            "transparency": "flattened",
        } if vendor_key == "kdp" else {}),
        "required_human_checks": [
            "safe_area_content_clear",
            "page_order_and_binding_correct",
            "color_and_icc_match_vendor",
            "font_handling_and_license_confirmed",
        ],
        "limitations": [
            "This contract covers interior pages only; cover/spine/imposition require a separate vendor contract.",
            "Pillow raster PDF is not asserted to be PDF/X.",
        ],
    }
    return write_json(root / "排版" / chapter / "print_delivery_contract.json", payload)


def create_readiness_receipt(
    root: Path,
    chapter: str,
    *,
    reviewer: str,
    reason: str,
    confirmed_checks: Mapping[str, bool],
) -> Path:
    if not reviewer.strip() or not reason.strip():
        raise ValueError("--reviewer 与 --reason 必填")
    if not confirmed_checks or not all(confirmed_checks.values()):
        raise ValueError("四项人审确认必须全部显式勾选；不能由脚本代替人判")
    contract_path = root / "排版" / chapter / "print_delivery_contract.json"
    contract = load_json(contract_path, {})
    if not isinstance(contract, Mapping) or contract.get("kind") != "comic_print_delivery_contract":
        raise ValueError("缺有效 print_delivery_contract.json")
    pdf_path, document = current_pdf(root, chapter)
    payload = {
        "schema_version": 1,
        "kind": "comic_print_readiness_receipt",
        "chapter": chapter,
        "status": "approved",
        "reviewer": reviewer.strip(),
        "reason": reason.strip(),
        "approved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "contract": {"path": str(contract_path.relative_to(root)), "sha256": sha256_file(contract_path)},
        "pdf": {"path": str(pdf_path.relative_to(root)), "sha256": sha256_file(pdf_path)},
        "pdf_document_record_sha256": hashlib.sha256(
            json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "checks": dict(confirmed_checks),
    }
    return write_json(root / "生产数据" / f"print_readiness_receipt_{chapter}.json", payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="漫画印刷规格合同与人审签收")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="写可验证的印刷规格合同（不代表已可印）")
    init.add_argument("--trim-width-mm", type=float, required=True)
    init.add_argument("--trim-height-mm", type=float, required=True)
    init.add_argument("--bleed-mm", type=float, default=3.2)
    init.add_argument("--safe-mm", type=float, default=6.4)
    init.add_argument("--dpi", type=int, default=300)
    init.add_argument("--binding-edge", choices=("left", "right"), required=True)
    init.add_argument("--reading-direction", choices=("ltr", "rtl"), required=True)
    init.add_argument("--color-mode", choices=("RGB", "CMYK", "L", "1"), default="RGB")
    init.add_argument("--icc-policy", choices=("embedded", "printer_managed_srgb", "printer_managed_gray"), default="printer_managed_srgb")
    init.add_argument("--icc-profile-name", default="sRGB IEC61966-2.1")
    init.add_argument("--vendor-profile", choices=("custom", "kdp"), default="custom")
    init.add_argument("--vendor-requirement-evidence", default="")

    accept = sub.add_parser("accept", help="绑定当前合同/PDF SHA，签收不能自动证明的人审项")
    accept.add_argument("--reviewer", required=True)
    accept.add_argument("--reason", required=True)
    accept.add_argument("--confirm-safe-area", action="store_true")
    accept.add_argument("--confirm-page-order", action="store_true")
    accept.add_argument("--confirm-color-icc", action="store_true")
    accept.add_argument("--confirm-font-handling", action="store_true")

    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    try:
        if args.command == "init":
            path = init_contract(
                root, args.chapter,
                trim_width_mm=args.trim_width_mm, trim_height_mm=args.trim_height_mm,
                bleed_mm=args.bleed_mm, safe_mm=args.safe_mm, dpi=args.dpi,
                binding_edge=args.binding_edge, reading_direction=args.reading_direction,
                color_mode=args.color_mode, icc_policy=args.icc_policy,
                icc_profile_name=args.icc_profile_name, vendor_profile=args.vendor_profile,
                vendor_requirement_evidence=args.vendor_requirement_evidence,
            )
        else:
            path = create_readiness_receipt(
                root, args.chapter, reviewer=args.reviewer, reason=args.reason,
                confirmed_checks={
                    "safe_area_content_clear": args.confirm_safe_area,
                    "page_order_and_binding_correct": args.confirm_page_order,
                    "color_and_icc_match_vendor": args.confirm_color_icc,
                    "font_handling_and_license_confirmed": args.confirm_font_handling,
                },
            )
    except ValueError as exc:
        print(f"[block] {exc}")
        return 2
    print(f"[ok] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
