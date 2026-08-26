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
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Mapping


ADAPTER_REGISTRY_REL = Path("生产数据") / "print_delivery_adapters.json"
ADAPTER_PROTOCOL = "comic_print_pdf_v1"


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.pending.{os.getpid()}")
    pending.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, path)
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _margins(value: float) -> dict[str, float]:
    return {"top": value, "bottom": value, "inside": value, "outside": value}


def current_pdf(root: Path, chapter: str) -> tuple[Path, dict[str, Any]]:
    manifest = load_json(root / "排版" / chapter / "export_manifest.json", {})
    for target_format in ("pdf_x4", "pdf"):
        for item in manifest.get("documents") or []:
            if isinstance(item, Mapping) and str(item.get("format") or "").lower() == target_format:
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
    renderer_mode: str = "raster_readiness",
    pdf_standard: str = "none",
    font_mode: str = "rasterized",
    icc_profile_path: str = "",
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
    professional = renderer_mode == "professional_external" or pdf_standard.upper() == "PDF/X-4"
    if professional and renderer_mode != "professional_external":
        raise ValueError("PDF/X-4 只能使用 professional_external renderer_mode")
    if professional and pdf_standard.upper() != "PDF/X-4":
        raise ValueError("professional_external 当前只接受显式 PDF/X-4 合同")
    profile = Path(icc_profile_path).expanduser().resolve() if icc_profile_path else None
    if professional and (not profile or not profile.is_file()):
        raise ValueError("PDF/X-4 合同必须绑定真实 ICC profile 文件")
    if professional and font_mode not in {"embedded", "outlined"}:
        raise ValueError("PDF/X-4 字体策略必须是 embedded 或 outlined")
    payload = {
        "schema_version": 2,
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
        "renderer": {"mode": renderer_mode, "adapter_protocol": ADAPTER_PROTOCOL if professional else ""},
        "pdf_standard": pdf_standard.upper() if professional else "not_asserted",
        "font_handling": {
            "mode": font_mode,
            "embedding_requirement": "all_fonts_embedded_or_outlined" if professional else "not_applicable_after_flattening",
            "license_status": "must_be_cleared_in__meta_rights",
        },
        "color": {
            "mode": color_mode,
            "icc_policy": icc_policy,
            "icc_profile_name": icc_profile_name,
            "icc_profile_path": str(profile) if profile else "",
            "icc_profile_sha256": sha256_file(profile) if profile else "",
        },
        "transparency_policy": "pdf_x4_managed" if professional else "flattened",
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
            "Pillow raster PDF is not asserted to be PDF/X." if not professional else "PDF/X-4 is asserted only after a configured adapter validator passes and its receipt is SHA-bound.",
        ],
    }
    return write_json(root / "排版" / chapter / "print_delivery_contract.json", payload)


def _adapter_rows(root: Path) -> list[dict[str, Any]]:
    registry = load_json(root / ADAPTER_REGISTRY_REL, {})
    rows = registry.get("adapters") if isinstance(registry, Mapping) else []
    valid: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, Mapping) or str(row.get("protocol") or "") != ADAPTER_PROTOCOL: continue
        command = row.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(token, str) and token for token in command): continue
        resolved = command[0] if Path(command[0]).is_absolute() else shutil.which(command[0])
        if not resolved or not Path(resolved).is_file(): continue
        valid.append({**dict(row), "command": [str(resolved), *command[1:]]})
    return valid


def _adapter_command(adapter: Mapping[str, Any], *, request: Path, output: Path, receipt: Path) -> list[str]:
    original = list(adapter.get("command") or [])
    values = {"{request}": str(request), "{output}": str(output), "{receipt}": str(receipt)}
    command = [token.replace("{request}", values["{request}"]).replace("{output}", values["{output}"]).replace("{receipt}", values["{receipt}"]) for token in original]
    if not any("{request}" in token for token in original): command += ["--request", str(request)]
    if not any("{output}" in token for token in original): command += ["--output", str(output)]
    if not any("{receipt}" in token for token in original): command += ["--receipt", str(receipt)]
    return command


def _page_inputs(root: Path, chapter: str) -> list[dict[str, str]]:
    manifest = load_json(root / "排版" / chapter / "export_manifest.json", {})
    rows = []
    for item in manifest.get("pages") or []:
        if not isinstance(item, Mapping) or not item.get("path"): continue
        path = (root / str(item["path"])).resolve()
        if path.is_file(): rows.append({"path": str(path.relative_to(root)), "sha256": sha256_file(path)})
    if not rows: raise ValueError("专业印刷渲染缺当前 export_manifest 页面输入")
    return rows


def _internal_pdf_markers(path: Path, contract: Mapping[str, Any], expected_pages: int) -> dict[str, Any]:
    """Check objective PDF markers; the external validator remains authoritative."""
    try: raw = path.read_bytes()
    except OSError as exc: raise ValueError(f"专业渲染器没有产出 PDF: {exc}") from exc
    checks = {
        "pdf_header": raw.startswith(b"%PDF-"),
        "trim_box": b"/TrimBox" in raw,
        "bleed_box": b"/BleedBox" in raw,
        "output_intent": b"/OutputIntent" in raw or b"/OutputIntents" in raw,
        "pdf_x4_identifier": b"PDF/X-4" in raw,
    }
    if str((contract.get("font_handling") or {}).get("mode")) == "embedded":
        checks["embedded_font_marker"] = any(token in raw for token in (b"/FontFile", b"/FontFile2", b"/FontFile3"))
    page_markers = len(re.findall(rb"/Type\s*/Page(?!s)\b", raw))
    checks["page_count_marker"] = page_markers == expected_pages
    if not all(checks.values()): raise ValueError("专业 PDF 内部结构标记失败: " + ", ".join(key for key, ok in checks.items() if not ok))
    return {"status": "pass", "validator": "comic_internal_pdf_markers_v1", "checks": checks, "page_count": page_markers}


def render_professional(root: Path, chapter: str, *, adapter_id: str = "") -> Path:
    """Render and validate into staging, then atomically promote one PDF."""
    contract_path = root / "排版" / chapter / "print_delivery_contract.json"
    contract = load_json(contract_path, {})
    if not isinstance(contract, Mapping) or contract.get("kind") != "comic_print_delivery_contract":
        raise ValueError("缺有效 print_delivery_contract.json")
    if (contract.get("renderer") or {}).get("mode") != "professional_external" or contract.get("pdf_standard") != "PDF/X-4":
        raise ValueError("当前合同不是 professional_external PDF/X-4")
    profile_path = Path(str((contract.get("color") or {}).get("icc_profile_path") or ""))
    if not profile_path.is_file() or sha256_file(profile_path) != str((contract.get("color") or {}).get("icc_profile_sha256") or ""):
        raise ValueError("ICC profile 当前文件与合同 SHA 不一致")
    adapters = _adapter_rows(root)
    adapter = next((row for row in adapters if not adapter_id or str(row.get("id") or "") == adapter_id), None)
    if adapter is None: raise ValueError("没有可执行的 comic_print_pdf_v1 专业渲染/验证适配器")
    pages = _page_inputs(root, chapter)
    output = root / "排版" / chapter / "print" / f"{chapter}_PDF-X-4.pdf"; output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="comic-print-", dir=str(output.parent)) as folder:
        stage = Path(folder); pending = stage / output.name; validator_path = stage / "validator_receipt.json"
        contract_sha = sha256_file(contract_path)
        inputs_sha = canonical_sha256(pages)
        request = {
            "protocol": ADAPTER_PROTOCOL, "chapter": chapter,
            "contract": {"path": str(contract_path.relative_to(root)), "sha256": contract_sha},
            "pages": pages, "inputs_sha256": inputs_sha,
            "output": str(pending), "validator_receipt": str(validator_path),
        }
        request_path = stage / "request.json"; request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
        proc = subprocess.run(_adapter_command(adapter, request=request_path, output=pending, receipt=validator_path), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0: raise ValueError(f"专业渲染器失败: {(proc.stderr or proc.stdout or '')[-1500:]}")
        internal = _internal_pdf_markers(pending, contract, len(pages))
        pending_sha = sha256_file(pending)
        validator = load_json(validator_path, {})
        validator_checks = validator.get("checks") if isinstance(validator, Mapping) else {}
        if (
            not isinstance(validator, Mapping)
            or validator.get("status") != "pass"
            or validator.get("pdf_standard") != "PDF/X-4"
            or not validator.get("validator")
            or str(validator.get("asset_sha256") or "") != pending_sha
            or str(validator.get("contract_sha256") or "") != contract_sha
            or str(validator.get("inputs_sha256") or "") != inputs_sha
            or not isinstance(validator_checks, Mapping)
            or not validator_checks
            or not all(validator_checks.values())
        ):
            raise ValueError("适配器 validator 必须全通过并精确绑定 staged PDF、合同与页面输入 SHA")
        os.replace(pending, output)
    receipt_path = root / "生产数据" / f"professional_print_receipt_{chapter}.json"
    receipt = {
        "schema_version": 1, "kind": "comic_professional_print_receipt", "status": "pass", "chapter": chapter,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "adapter": {"id": str(adapter.get("id") or ""), "protocol": ADAPTER_PROTOCOL},
        "contract": {"path": str(contract_path.relative_to(root)), "sha256": contract_sha},
        "inputs_sha256": inputs_sha,
        "inputs": pages,
        "pdf": {"path": str(output.relative_to(root)), "sha256": sha256_file(output), "standard": "PDF/X-4"},
        "internal_validation": internal, "external_validator_receipt": validator,
        "external_validator_receipt_sha256": canonical_sha256(validator),
    }
    write_json(receipt_path, receipt)
    manifest_path = root / "排版" / chapter / "export_manifest.json"; manifest = load_json(manifest_path, {})
    documents = [row for row in manifest.get("documents") or [] if not (isinstance(row, Mapping) and str(row.get("format") or "").lower() == "pdf_x4")]
    manifest["documents"] = documents + [{"format": "pdf_x4", "path": str(output.relative_to(root)), "sha256": sha256_file(output), "receipt": str(receipt_path.relative_to(root))}]
    write_json(manifest_path, manifest)
    return receipt_path


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
    professional_path = root / "生产数据" / f"professional_print_receipt_{chapter}.json"
    professional = load_json(professional_path, {})
    if isinstance(professional, Mapping) and professional.get("status") == "pass":
        payload["professional_print_receipt"] = {"path": str(professional_path.relative_to(root)), "sha256": sha256_file(professional_path)}
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
    init.add_argument("--renderer-mode", choices=("raster_readiness", "professional_external"), default="raster_readiness")
    init.add_argument("--pdf-standard", choices=("none", "PDF/X-4"), default="none")
    init.add_argument("--font-mode", choices=("rasterized", "embedded", "outlined"), default="rasterized")
    init.add_argument("--icc-profile-path", default="")

    accept = sub.add_parser("accept", help="绑定当前合同/PDF SHA，签收不能自动证明的人审项")
    accept.add_argument("--reviewer", required=True)
    accept.add_argument("--reason", required=True)
    accept.add_argument("--confirm-safe-area", action="store_true")
    accept.add_argument("--confirm-page-order", action="store_true")
    accept.add_argument("--confirm-color-icc", action="store_true")
    accept.add_argument("--confirm-font-handling", action="store_true")

    render = sub.add_parser("render-professional", help="经注册适配器生成并验证 PDF/X-4，再原子提升")
    render.add_argument("--adapter-id", default="")

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
                renderer_mode=args.renderer_mode, pdf_standard=args.pdf_standard,
                font_mode=args.font_mode, icc_profile_path=args.icc_profile_path,
            )
        elif args.command == "accept":
            path = create_readiness_receipt(
                root, args.chapter, reviewer=args.reviewer, reason=args.reason,
                confirmed_checks={
                    "safe_area_content_clear": args.confirm_safe_area,
                    "page_order_and_binding_correct": args.confirm_page_order,
                    "color_and_icc_match_vendor": args.confirm_color_icc,
                    "font_handling_and_license_confirmed": args.confirm_font_handling,
                },
            )
        else:
            path = render_professional(root, args.chapter, adapter_id=args.adapter_id)
    except ValueError as exc:
        print(f"[block] {exc}")
        return 2
    print(f"[ok] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
