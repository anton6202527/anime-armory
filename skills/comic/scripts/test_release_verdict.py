from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from PIL import Image
import pytest


MODULE_PATH = Path(__file__).with_name("release_verdict.py")
SPEC = importlib.util.spec_from_file_location("comic_release_verdict", MODULE_PATH)
assert SPEC and SPEC.loader
release_verdict = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_verdict)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def write_png(path: Path, size: tuple[int, int], color: tuple[int, int, int] = (40, 80, 120)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format="PNG")


def write_valid_epub(root: Path) -> Path:
    epub = root / "排版" / "第1话" / "accessible" / "第1话.epub"
    epub.parent.mkdir(parents=True, exist_ok=True)
    container = """<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""
    package = """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
 <metadata>
  <dc:identifier id="pub-id">urn:test:comic</dc:identifier>
  <dc:title>作品 第1话</dc:title><dc:language>zh-Hans</dc:language>
  <meta property="rendition:layout">pre-paginated</meta>
  <meta property="schema:accessMode">visual</meta>
  <meta property="schema:accessModeSufficient">visual,textual</meta>
  <meta property="schema:accessibilityFeature">alternativeText</meta>
  <meta property="schema:accessibilityHazard">none</meta>
  <meta property="schema:accessibilitySummary">Human-reviewed page alternatives.</meta>
 </metadata>
 <manifest>
  <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
  <item id="page_001" href="page_001.xhtml" media-type="application/xhtml+xml"/>
  <item id="page-image" href="page_001.png" media-type="image/png"/>
 </manifest>
 <spine><itemref idref="page_001"/></spine>
</package>"""
    nav = """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>目录</title></head><body><nav epub:type="toc"><ol><li><a href="page_001.xhtml">第1页</a></li></ol></nav></body></html>"""
    page = """<html xmlns="http://www.w3.org/1999/xhtml"><head><title>第1页</title></head>
<body><img src="page_001.png" alt="主角站在雨中的整页画面。"/></body></html>"""
    with zipfile.ZipFile(epub, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("EPUB/package.opf", package)
        archive.writestr("EPUB/nav.xhtml", nav)
        archive.writestr("EPUB/page_001.xhtml", page)
        archive.writestr("EPUB/page_001.png", b"fixture-image-bytes")
    return epub


def review_receipt_id(chapter: str, inputs_sha: str, verdict: str, findings: list[dict]) -> str:
    return release_verdict.stable_sha256({
        "project_root": ".", "chapter": chapter, "stage": "review",
        "inputs": inputs_sha, "verdict": verdict, "findings": findings,
    })


def prepare_project(
    root: Path,
    *,
    target_platform: str = "通用",
    rendered_size: tuple[int, int] = (1440, 32),
    page_size: tuple[int, int] | None = None,
    declared_page_size: tuple[int, int] | None = None,
) -> list[dict]:
    (root / "_设置.md").write_text(
        f"- 漫画形态: 条漫\n- 目标平台: {target_platform}\n- 合规用途: demo学习\n",
        encoding="utf-8",
    )
    (root / "_进度.md").write_text("# progress\n", encoding="utf-8")
    rendered = root / "排版" / "第1话" / "长图" / "longstrip.png"
    write_png(rendered, rendered_size)
    manifest = {
        "kind": "comic_export_manifest",
        "missing_panels": [],
        "pages": [],
        "rendered": [{
            "path": "排版/第1话/长图/longstrip.png",
            "format": "png",
            "size": {"width": rendered_size[0], "height": rendered_size[1]},
        }],
    }
    if page_size:
        page = root / "排版" / "第1话" / "pages" / "page_001.png"
        write_png(page, page_size, (100, 60, 20))
        declared = declared_page_size or page_size
        manifest["pages"] = [{
            "path": "排版/第1话/pages/page_001.png",
            "format": "png",
            "size": {"width": declared[0], "height": declared[1]},
        }]
    write_json(root / "排版" / "第1话" / "export_manifest.json", manifest)
    write_json(root / "_meta.json", {"rights": {
        "source_status": "original",
        "font_status": "licensed",
        "asset_status": "licensed",
    }})
    artifacts, _ = release_verdict.rendered_artifacts(root, manifest)
    current = release_verdict.stage_inputs_fingerprint(root, "第1话", "review")
    report_path = root / "生产数据" / "comic_gate_review_第1话.json"
    receipt_id = review_receipt_id("第1话", current["sha256"], "pass", [])
    write_json(report_path, {
        "kind": "comic_gate", "stage": "review", "chapter": "第1话", "verdict": "pass",
        "inputs_fingerprint": current, "findings": [], "receipt_id": receipt_id,
    })
    write_json(root / "生产数据" / "gate_receipts" / "review_第1话.json", {
        "kind": "comic_gate_receipt", "stage": "review", "chapter": "第1话",
        "receipt_id": receipt_id,
        "verdict": "pass",
        "execution_authorized": True,
        "inputs_fingerprint_sha256": current["sha256"],
        "report_path": str(report_path.relative_to(root)),
        "report_sha256": release_verdict.sha256_file(report_path),
    })
    return artifacts


def refresh_review_receipt(root: Path) -> None:
    current = release_verdict.stage_inputs_fingerprint(root, "第1话", "review")
    report_path = root / "生产数据" / "comic_gate_review_第1话.json"
    receipt_id = review_receipt_id("第1话", current["sha256"], "pass", [])
    write_json(report_path, {
        "kind": "comic_gate", "stage": "review", "chapter": "第1话", "verdict": "pass",
        "inputs_fingerprint": current, "findings": [], "receipt_id": receipt_id,
    })
    write_json(root / "生产数据" / "gate_receipts" / "review_第1话.json", {
        "kind": "comic_gate_receipt", "stage": "review", "chapter": "第1话",
        "receipt_id": receipt_id, "verdict": "pass", "execution_authorized": True,
        "inputs_fingerprint_sha256": current["sha256"],
        "report_path": str(report_path.relative_to(root)),
        "report_sha256": release_verdict.sha256_file(report_path),
    })


def prepare_print_delivery(root: Path) -> None:
    manifest_path = root / "排版" / "第1话" / "export_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    page_path = root / "排版" / "第1话" / "pages" / "page_001.png"
    write_png(page_path, (64, 32), (100, 60, 20))
    page_record = {
        "path": str(page_path.relative_to(root)), "format": "png",
        "size": {"width": 64, "height": 32},
    }
    manifest["pages"] = [page_record]
    pdf_path = root / "排版" / "第1话" / "print" / "第1话.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    Image.open(page_path).convert("RGB").save(pdf_path, "PDF", resolution=300)
    document = {
        "path": str(pdf_path.relative_to(root)), "format": "pdf", "page_count": 1,
        "page_order": [page_record["path"]], "dpi": 300, "color_mode": "RGB",
        "source_pages": [{
            "path": page_record["path"], "sha256": release_verdict.sha256_file(page_path),
            "pixel_size": {"width": 64, "height": 32}, "mode": "RGB", "has_alpha": False,
        }],
        "sha256": release_verdict.sha256_file(pdf_path),
    }
    manifest["documents"] = [document]
    write_json(manifest_path, manifest)
    trim_w = 64 / 300 * 25.4
    trim_h = 32 / 300 * 25.4
    contract_path = root / "排版" / "第1话" / "print_delivery_contract.json"
    contract = {
        "schema_version": 1, "kind": "comic_print_delivery_contract", "chapter": "第1话",
        "vendor_requirement_evidence": "fixture vendor accepts printer-managed sRGB",
        "geometry_mm": {
            "trim": {"width": trim_w, "height": trim_h},
            "bleed": {"top": 0, "bottom": 0, "inside": 0, "outside": 0},
            "safe_area": {"top": 0.5, "bottom": 0.5, "inside": 0.5, "outside": 0.5},
        },
        "dpi": 300,
        "binding": {"reading_direction": "ltr", "edge": "left"},
        "page_order": [page_record["path"]],
        "font_handling": {"mode": "rasterized"},
        "color": {"mode": "RGB", "icc_policy": "printer_managed_srgb", "icc_profile_name": "sRGB IEC61966-2.1"},
    }
    write_json(contract_path, contract)
    write_json(root / "生产数据" / "print_readiness_receipt_第1话.json", {
        "kind": "comic_print_readiness_receipt", "chapter": "第1话", "status": "approved",
        "reviewer": "print-editor", "reason": "逐页印前复核", "approved_at": "2026-08-20T00:00:00Z",
        "contract": {"path": str(contract_path.relative_to(root)), "sha256": release_verdict.sha256_file(contract_path)},
        "pdf": {"path": str(pdf_path.relative_to(root)), "sha256": release_verdict.sha256_file(pdf_path)},
        "pdf_document_record_sha256": release_verdict.stable_sha256(document),
        "checks": {
            "safe_area_content_clear": True, "page_order_and_binding_correct": True,
            "color_and_icc_match_vendor": True, "font_handling_and_license_confirmed": True,
        },
    })
    refresh_review_receipt(root)


def prepare_accessible_delivery(root: Path, epub: Path | None = None) -> tuple[Path, Path]:
    epub = epub or write_valid_epub(root)
    manifest_path = root / "排版" / "第1话" / "export_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    semantic_sha = release_verdict.stable_sha256([{"page_id": "page_001", "panels": [{"panel_id": "P001", "description": "fixture panel"}]}])
    manifest["documents"] = [{
        "path": str(epub.relative_to(root)), "format": "epub",
        "sha256": release_verdict.sha256_file(epub),
        "semantic_transcript_sha256": semantic_sha,
        "semantic_coverage": {"panels": 1, "dialogue": 0, "speaker": 0, "descriptions": 1, "long_descriptions": 0},
    }]
    write_json(manifest_path, manifest)
    contract_path = root / "排版" / "第1话" / "accessible_digital_contract.json"
    write_json(contract_path, {
        "schema_version": 2, "kind": "comic_accessible_digital_contract", "chapter": "第1话",
        "artifact": {"path": str(epub.relative_to(root)), "sha256": release_verdict.sha256_file(epub)},
        "rendering": {"rendition_layout": "pre-paginated"},
        "reading_order": ["page_001"],
        "text_alternatives": {
            "coverage": 1.0, "missing": [], "reviewer": "a11y-editor",
            "reviewed_at": "2026-08-20T00:00:00Z", "reason": "逐页核对替代文本与画面语义",
        },
        "semantic_transcript": {
            "sha256": semantic_sha, "pages": 1, "panels": 1, "dialogue_lines": 0,
            "speaker_attribution_coverage": 1.0, "extended_descriptions": 1,
            "programmatic_order": ["P001"],
        },
        "navigation": {"toc": True, "landmarks": ["bodymatter"]},
        "accessibility_metadata": {
            "title": "作品 第1话", "language": "zh-Hans",
            "access_modes": ["visual", "textual"],
            "access_mode_sufficient": [["textual"]],
            "accessibility_features": ["alternativeText", "readingOrder"],
            "accessibility_hazards": ["none"],
            "accessibility_summary": "human reviewed alternatives",
        },
        "provenance": {
            "formal_baseline": {"standard": "EPUB Accessibility 1.1", "url": "https://www.w3.org/TR/epub-a11y-11/"},
            "candidate_tracking": {"standard": "EPUB Accessibility 1.2 Candidate Recommendation", "not_claimed_as_formal_baseline": True},
        },
        "assurance": {"level": "workflow_readiness_human_attested", "not_conformance_certification": True},
    })
    refresh_review_receipt(root)
    return epub, contract_path


def test_internal_separates_production_from_public_acceptance(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    report = release_verdict.build(tmp_path, "第1话", "internal")
    assert report["verdict"] == "pass"
    assert report["delivery_states"]["production_complete"]
    assert not report["delivery_states"]["publish_ready_digital"]


def test_public_requires_exact_current_artifact_acceptance(tmp_path: Path) -> None:
    artifacts = prepare_project(tmp_path)
    write_json(tmp_path / "生产数据" / "release_acceptance_第1话.json", {
        "status": "approved", "profile": "digital", "reviewer": "editor",
        "reason": "发布前最终复核", "approved_at": "2026-07-14T00:00:00Z",
        "artifacts": artifacts,
        "review_receipt": release_verdict.review_receipt_binding(tmp_path, "第1话"),
        "finding_dispositions": release_verdict.finding_disposition_binding(tmp_path, "第1话"),
    })
    report = release_verdict.build(tmp_path, "第1话", "digital")
    assert report["verdict"] == "pass"
    (tmp_path / artifacts[0]["path"]).write_bytes(b"changed")
    stale = release_verdict.build(tmp_path, "第1话", "digital")
    assert stale["verdict"] == "blocked"
    assert "release_acceptance_stale" in {item["code"] for item in stale["issues"]}


def test_review_receipt_stales_when_review_input_changes(tmp_path: Path) -> None:
    artifacts = prepare_project(tmp_path)
    write_json(tmp_path / "生产数据" / "release_acceptance_第1话.json", {
        "status": "approved", "profile": "digital", "reviewer": "editor",
        "reason": "发布前最终复核", "approved_at": "2026-07-14T00:00:00Z",
        "artifacts": artifacts,
        "review_receipt": release_verdict.review_receipt_binding(tmp_path, "第1话"),
        "finding_dispositions": release_verdict.finding_disposition_binding(tmp_path, "第1话"),
    })
    (tmp_path / "_设置.md").write_text("- 漫画形态: 页漫\n", encoding="utf-8")
    report = release_verdict.build(tmp_path, "第1话", "digital")
    assert "review_gate_receipt_stale" in {item["code"] for item in report["issues"]}


def test_review_report_must_bind_same_current_fingerprint(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    report_path = tmp_path / "生产数据" / "comic_gate_review_第1话.json"
    gate_report = json.loads(report_path.read_text(encoding="utf-8"))
    gate_report["inputs_fingerprint"]["sha256"] = "tampered"
    write_json(report_path, gate_report)
    receipt_path = tmp_path / "生产数据" / "gate_receipts" / "review_第1话.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["report_sha256"] = release_verdict.sha256_file(report_path)
    write_json(receipt_path, receipt)
    verdict = release_verdict.build(tmp_path, "第1话", "internal")
    assert "review_gate_report_invalid" in {item["code"] for item in verdict["issues"]}


def test_review_verdict_cannot_be_downgraded_below_its_findings(tmp_path: Path) -> None:
    # forge: leave verdict "pass" but a block-severity finding is present.
    prepare_project(tmp_path)
    report_path = tmp_path / "生产数据" / "comic_gate_review_第1话.json"
    gate_report = json.loads(report_path.read_text(encoding="utf-8"))
    gate_report["findings"] = [{"severity": "block", "code": "hidden", "reason": "r", "artifact": "a"}]
    write_json(report_path, gate_report)
    receipt_path = tmp_path / "生产数据" / "gate_receipts" / "review_第1话.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["report_sha256"] = release_verdict.sha256_file(report_path)
    write_json(receipt_path, receipt)
    verdict = release_verdict.build(tmp_path, "第1话", "internal")
    assert "review_gate_report_verdict_tampered" in {item["code"] for item in verdict["issues"]}


def test_accept_command_helper_binds_artifacts_and_review_receipt(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    path = release_verdict.create_acceptance(
        tmp_path,
        "第1话",
        "digital",
        reviewer="editor",
        reason="发布前已并排检查",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["artifacts"]
    report = json.loads((tmp_path / "生产数据" / "comic_gate_review_第1话.json").read_text(encoding="utf-8"))
    assert payload["review_receipt"]["receipt_id"] == report["receipt_id"]
    assert release_verdict.build(tmp_path, "第1话", "digital")["verdict"] == "pass"


def test_public_release_blocks_missing_or_ambiguous_rights(tmp_path: Path) -> None:
    artifacts = prepare_project(tmp_path)
    write_json(tmp_path / "生产数据" / "release_acceptance_第1话.json", {
        "status": "approved", "profile": "digital", "reviewer": "editor",
        "reason": "发布前最终复核", "approved_at": "2026-07-14T00:00:00Z",
        "artifacts": artifacts,
        "review_receipt": release_verdict.review_receipt_binding(tmp_path, "第1话"),
        "finding_dispositions": release_verdict.finding_disposition_binding(tmp_path, "第1话"),
    })
    write_json(tmp_path / "_meta.json", {"rights": {
        "source_status": "original_or_user_provided",
        "font_status": "pending_before_publish",
    }})
    report = release_verdict.build(tmp_path, "第1话", "digital")
    assert report["verdict"] == "blocked"
    assert {
        "source_status_unverified", "font_status_unverified", "asset_status_unverified",
    }.issubset({item["code"] for item in report["issues"]})
    assert release_verdict.build(tmp_path, "第1话", "internal")["verdict"] == "pass"


def test_release_acceptance_is_scoped_to_delivery_profile(tmp_path: Path) -> None:
    artifacts = prepare_project(tmp_path)
    write_json(tmp_path / "生产数据" / "release_acceptance_第1话.json", {
        "status": "approved", "profile": "digital", "reviewer": "editor",
        "reason": "数字发布复核", "approved_at": "2026-07-14T00:00:00Z",
        "artifacts": artifacts,
        "review_receipt": release_verdict.review_receipt_binding(tmp_path, "第1话"),
        "finding_dispositions": release_verdict.finding_disposition_binding(tmp_path, "第1话"),
    })
    report = release_verdict.build(tmp_path, "第1话", "print")
    assert "release_acceptance_profile_mismatch" in {item["code"] for item in report["issues"]}


def test_accept_can_replace_a_current_acceptance_for_another_profile(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    release_verdict.create_acceptance(
        tmp_path, "第1话", "digital", reviewer="editor", reason="数字发布复核"
    )
    prepare_print_delivery(tmp_path)
    path = release_verdict.create_acceptance(
        tmp_path, "第1话", "print", reviewer="print-editor", reason="印刷交付复核"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["profile"] == "print"
    assert payload["medium"] == "print_pdf"
    assert payload["usage"] == "public"
    assert payload["reviewer"] == "print-editor"
    assert release_verdict.build(tmp_path, "第1话", "print")["verdict"] == "pass"


def test_release_covers_pages_and_blocks_corrupt_images(tmp_path: Path) -> None:
    artifacts = prepare_project(tmp_path, page_size=(1440, 24))
    assert {item["path"] for item in artifacts} == {
        "排版/第1话/pages/page_001.png",
        "排版/第1话/长图/longstrip.png",
    }
    (tmp_path / "排版" / "第1话" / "pages" / "page_001.png").write_bytes(b"not an image")

    report = release_verdict.build(tmp_path, "第1话", "internal")
    assert report["verdict"] == "blocked"
    assert not report["delivery_states"]["technical_complete"]
    assert "export_artifact_decode_failed" in {item["code"] for item in report["issues"]}


def test_release_blocks_manifest_dimension_mismatch(tmp_path: Path) -> None:
    prepare_project(tmp_path, page_size=(1440, 24), declared_page_size=(940, 24))
    report = release_verdict.build(tmp_path, "第1话", "internal")
    assert not report["delivery_states"]["technical_complete"]
    assert "export_artifact_dimensions_mismatch" in {item["code"] for item in report["issues"]}


def test_release_rechecks_current_platform_with_publish_like_severity(tmp_path: Path) -> None:
    prepare_project(tmp_path, target_platform="Tapas", rendered_size=(1440, 32))
    report = release_verdict.build(tmp_path, "第1话", "digital")
    assert report["target_platform"] == "Tapas"
    assert report["verdict"] == "blocked"
    assert "platform_width_mismatch" in {item["code"] for item in report["issues"]}


def _write_vlm_tasks(root: Path, tasks: list[dict]) -> None:
    write_json(root / "生产数据" / "comic_vlm_judge_tasks_第1话.json", {
        "kind": "comic_vlm_judge_tasks", "chapter": "第1话",
        "task_count": len(tasks), "tasks": tasks,
    })


def test_zero_vlm_adjudication_blocks_production_even_internal(tmp_path: Path) -> None:
    # 103 条任务 0 裁决仍 internal 放行的空转旁路必须堵死。
    # vlm 文件先落盘再建 receipt，避免 review 指纹陈旧混入 production block 干扰断言。
    _write_vlm_tasks(tmp_path, [
        {"task_id": "P001__CHAR_A__character", "axis": "character_identity",
         "panel": {"panel_id": "P001", "sha256": "aa"}},
        {"task_id": "P001__LOC_X__background", "axis": "background_continuity",
         "panel": {"panel_id": "P001", "sha256": "aa"}},
    ])
    prepare_project(tmp_path)
    report = release_verdict.build(tmp_path, "第1话", "internal")
    codes = {item["code"] for item in report["issues"]}
    assert "vlm_adjudication_missing" in codes
    assert not report["delivery_states"]["production_complete"]
    assert report["vlm_adjudication"]["total"] == 2
    assert report["vlm_adjudication"]["adjudicated"] == 0


def test_partial_or_suspect_vlm_adjudication_blocks_public_only(tmp_path: Path) -> None:
    _write_vlm_tasks(tmp_path, [
        {"task_id": "T1", "axis": "character_identity", "panel": {"sha256": "aa"}},
        {"task_id": "T2", "axis": "prop_identity", "panel": {"sha256": "bb"}},
        {"task_id": "T3", "axis": "background_continuity", "panel": {"sha256": "cc"}},
    ])
    write_json(tmp_path / "生产数据" / "comic_vlm_judge_verdicts_第1话.json", {"verdicts": [
        {"task_id": "T1", "panel_sha256": "aa", "verdict": "pass"},
        {"task_id": "T2", "panel_sha256": "bb", "verdict": "suspect"},
        {"task_id": "T3", "panel_sha256": "STALE", "verdict": "pass"},  # 该格已重抽，裁决作废
    ]})
    prepare_project(tmp_path)
    report = release_verdict.build(tmp_path, "第1话", "internal")
    codes = {item["code"] for item in report["issues"]}
    assert "vlm_adjudication_missing" not in codes
    assert "vlm_adjudication_partial" in codes
    assert "vlm_suspect_unresolved" in codes
    assert report["delivery_states"]["production_complete"]  # 部分覆盖不拦内部
    assert not report["delivery_states"]["publish_ready_digital"]
    assert report["vlm_adjudication"]["adjudicated"] == 2
    assert report["vlm_adjudication"]["open_suspects"] == ["T2"]


def test_missing_vlm_tasks_without_consistency_report_is_backwards_compatible(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    report = release_verdict.build(tmp_path, "第1话", "internal")
    codes = {item["code"] for item in report["issues"]}
    assert not codes & {"vlm_tasks_missing", "vlm_adjudication_missing"}


def test_missing_vlm_tasks_with_consistency_report_blocks_production(tmp_path: Path) -> None:
    write_json(tmp_path / "生产数据" / "comic_character_consistency_第1话.json", {"kind": "x"})
    prepare_project(tmp_path)
    report = release_verdict.build(tmp_path, "第1话", "internal")
    assert "vlm_tasks_missing" in {item["code"] for item in report["issues"]}
    assert not report["delivery_states"]["production_complete"]


def test_medium_and_usage_axes_allow_commercial_print_without_legacy_conflation(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    prepare_print_delivery(tmp_path)
    path = release_verdict.create_acceptance(
        tmp_path, "第1话", "commercial", medium="print_pdf", usage="commercial",
        reviewer="publisher", reason="商业印刷当前 PDF 最终复核",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["medium"] == "print_pdf"
    assert payload["usage"] == "commercial"
    report = release_verdict.build(
        tmp_path, "第1话", "commercial", medium="print_pdf", usage="commercial"
    )
    assert report["verdict"] == "pass"
    assert report["delivery_axis"] == "print_pdf+commercial"


def test_platform_preview_requires_actual_platform_source_and_current_screenshot_sha(tmp_path: Path) -> None:
    artifacts = prepare_project(tmp_path, target_platform="Tapas", rendered_size=(940, 32))
    desktop = tmp_path / "生产数据" / "previews" / "desktop.png"
    mobile = tmp_path / "生产数据" / "previews" / "mobile.png"
    write_png(desktop, (1200, 800))
    write_png(mobile, (390, 844))
    release_verdict.create_platform_preview_receipt(
        tmp_path, "第1话", desktop_screenshot=desktop, mobile_screenshot=mobile,
        reviewer="editor", reason="双端检查", preview_source="local_simulation",
    )
    manifest = json.loads((tmp_path / "排版" / "第1话" / "export_manifest.json").read_text(encoding="utf-8"))
    issues = release_verdict.check_platform_preview_receipt(
        tmp_path, "第1话", manifest, artifacts, "Tapas", "web_images", "public"
    )
    assert {item["code"] for item in issues} == {"platform_preview_not_actual"}

    release_verdict.create_platform_preview_receipt(
        tmp_path, "第1话", desktop_screenshot=desktop, mobile_screenshot=mobile,
        reviewer="editor", reason="平台后台双端检查", preview_source="actual_platform_preview",
    )
    assert release_verdict.check_platform_preview_receipt(
        tmp_path, "第1话", manifest, artifacts, "Tapas", "web_images", "public"
    ) == []
    write_png(mobile, (391, 844), (1, 2, 3))
    stale = release_verdict.check_platform_preview_receipt(
        tmp_path, "第1话", manifest, artifacts, "Tapas", "web_images", "public"
    )
    assert {item["code"] for item in stale} == {"platform_preview_screenshot_stale"}


def test_platform_without_verified_viewports_does_not_invent_pc_mobile_gate(tmp_path: Path) -> None:
    artifacts = prepare_project(tmp_path, target_platform="MANGA Plus Creators")
    manifest = json.loads((tmp_path / "排版" / "第1话" / "export_manifest.json").read_text(encoding="utf-8"))
    assert release_verdict.check_platform_preview_receipt(
        tmp_path, "第1话", manifest, artifacts, "MANGA Plus Creators", "web_images", "public"
    ) == []


def test_acceptance_stales_when_disposition_ledger_changes(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    release_verdict.create_acceptance(
        tmp_path, "第1话", "digital", reviewer="editor", reason="当前处置账与导出复核"
    )
    ledger = tmp_path / "生产数据" / "finding_dispositions" / "第1话.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("{}\n", encoding="utf-8")
    report = release_verdict.build(tmp_path, "第1话", "digital")
    assert "release_acceptance_dispositions_stale" in {item["code"] for item in report["issues"]}


def test_epub_fxl_rejects_plain_image_package_and_requires_accessibility_contract(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    report = release_verdict.build(
        tmp_path, "第1话", "internal", medium="epub_fxl", usage="internal"
    )
    assert report["verdict"] == "blocked"
    assert "accessible_contract_missing" in {item["code"] for item in report["issues"]}
    assert report["delivery_states"]["publish_ready_epub_fxl_public"] is False


def test_epub_fxl_accepts_structural_epub_only_as_human_attested_workflow_readiness(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    prepare_accessible_delivery(tmp_path)
    report = release_verdict.build(
        tmp_path, "第1话", "internal", medium="epub_fxl", usage="internal"
    )
    assert report["verdict"] == "pass"
    assert not {item["code"] for item in report["issues"]} & {
        "accessible_epub_missing_or_stale", "accessible_metadata_incomplete",
        "accessible_assurance_overclaim", "epub_structural_validation_failed",
    }


def test_epub_skeleton_cannot_pass_with_self_declared_accessibility_contract(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    epub = tmp_path / "排版" / "第1话" / "accessible" / "skeleton.epub"
    epub.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", "<container/>")
        archive.writestr("EPUB/package.opf", "<package/>")
    prepare_accessible_delivery(tmp_path, epub)
    report = release_verdict.build(tmp_path, "第1话", "internal", medium="epub_fxl", usage="internal")
    codes = {item["code"] for item in report["issues"]}
    assert report["verdict"] == "blocked"
    assert "epub_structural_validation_failed" in codes
    evidence = next(item for item in report["artifacts"] if item.get("format") == "epub")["epub_structural_evidence"]
    assert evidence["container_valid"] is False
    assert evidence["spine_valid"] is False


def test_accessibility_contract_change_stales_epub_release_acceptance(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    _epub, contract_path = prepare_accessible_delivery(tmp_path)
    release_verdict.create_acceptance(
        tmp_path, "第1话", "digital", medium="epub_fxl", usage="public",
        reviewer="publisher", reason="EPUB 与无障碍合同复核",
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["human_review_note"] = "changed after acceptance"
    write_json(contract_path, contract)
    report = release_verdict.build(tmp_path, "第1话", "digital", medium="epub_fxl", usage="public")
    assert "release_acceptance_medium_binding_stale" in {item["code"] for item in report["issues"]}


def test_accessibility_human_attestation_requires_named_reviewer_time_and_reason(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    _epub, contract_path = prepare_accessible_delivery(tmp_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["text_alternatives"]["reviewer"] = ""
    write_json(contract_path, contract)
    report = release_verdict.build(tmp_path, "第1话", "internal", medium="epub_fxl", usage="internal")
    assert "accessible_text_alternatives_attestation_missing" in {item["code"] for item in report["issues"]}
    assert report["verdict"] == "blocked"


def test_print_contract_and_receipt_replacement_stales_total_release_acceptance(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    prepare_print_delivery(tmp_path)
    release_verdict.create_acceptance(
        tmp_path, "第1话", "print", reviewer="publisher", reason="印刷合同与 PDF 最终复核"
    )
    contract_path = tmp_path / "排版" / "第1话" / "print_delivery_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["vendor_requirement_evidence"] = "replacement vendor evidence"
    write_json(contract_path, contract)
    receipt_path = tmp_path / "生产数据" / "print_readiness_receipt_第1话.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["contract"]["sha256"] = release_verdict.sha256_file(contract_path)
    receipt["reason"] = "新合同四项重新复核"
    write_json(receipt_path, receipt)
    report = release_verdict.build(tmp_path, "第1话", "print")
    assert "release_acceptance_medium_binding_stale" in {item["code"] for item in report["issues"]}


def test_preview_order_swap_stales_preview_and_release_acceptance(tmp_path: Path) -> None:
    prepare_project(tmp_path, target_platform="Tapas", rendered_size=(940, 32))
    second = tmp_path / "排版" / "第1话" / "长图" / "part_002.png"
    thumb = tmp_path / "排版" / "第1话" / "platform" / "episode.png"
    write_png(second, (940, 32), (9, 8, 7))
    write_png(thumb, (300, 300), (4, 5, 6))
    manifest_path = tmp_path / "排版" / "第1话" / "export_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["rendered"].append({
        "path": str(second.relative_to(tmp_path)), "format": "png",
        "size": {"width": 940, "height": 32}, "segment_index": 2,
    })
    manifest["rendered"][0]["segment_index"] = 1
    manifest["platform_assets"] = {"episode": {
        "path": str(thumb.relative_to(tmp_path)), "format": "png",
        "size": {"width": 300, "height": 300}, "sha256": release_verdict.sha256_file(thumb),
    }}
    write_json(manifest_path, manifest)
    refresh_review_receipt(tmp_path)
    desktop = tmp_path / "生产数据" / "previews" / "desktop.png"
    mobile = tmp_path / "生产数据" / "previews" / "mobile.png"
    write_png(desktop, (1200, 800)); write_png(mobile, (390, 844))
    release_verdict.create_platform_preview_receipt(
        tmp_path, "第1话", desktop_screenshot=desktop, mobile_screenshot=mobile,
        reviewer="editor", reason="实际后台双端预览", preview_source="actual_platform_preview",
    )
    release_verdict.create_acceptance(
        tmp_path, "第1话", "digital", reviewer="publisher", reason="当前上传顺序复核"
    )
    manifest["rendered"] = list(reversed(manifest["rendered"]))
    write_json(manifest_path, manifest)
    refresh_review_receipt(tmp_path)
    report = release_verdict.build(tmp_path, "第1话", "digital")
    codes = {item["code"] for item in report["issues"]}
    assert "platform_preview_receipt_stale" in codes
    assert "release_acceptance_preview_stale" in codes


def test_review_report_cannot_delete_findings_and_receipt_id(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    report_path = tmp_path / "生产数据" / "comic_gate_review_第1话.json"
    gate_report = json.loads(report_path.read_text(encoding="utf-8"))
    gate_report.pop("findings")
    gate_report.pop("receipt_id")
    write_json(report_path, gate_report)
    receipt_path = tmp_path / "生产数据" / "gate_receipts" / "review_第1话.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt.pop("receipt_id")
    receipt["report_sha256"] = release_verdict.sha256_file(report_path)
    write_json(receipt_path, receipt)
    report = release_verdict.build(tmp_path, "第1话", "internal")
    assert "review_gate_findings_missing" in {item["code"] for item in report["issues"]}
    assert report["verdict"] == "blocked"


def test_disposition_ledger_integrity_errors_block_public_not_internal() -> None:
    issues = release_verdict.check_finding_dispositions({
        "available": True, "unresolved_count": 0, "ledger_integrity_error_count": 1,
    })
    assert {item["code"] for item in issues} == {"finding_disposition_ledger_integrity_failed"}
    assert release_verdict.issue_blocks(issues[0], "web_images", "public") is True
    assert release_verdict.issue_blocks(issues[0], "web_images", "internal") is False


def test_write_outputs_promotes_immutable_digest_bundle_via_active_pointer(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    report = release_verdict.build(tmp_path, "第1话", "internal")
    release_verdict.write_outputs(tmp_path, "第1话", report)
    contract_path = tmp_path / "生产数据" / "release_contract_第1话.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    bundle = tmp_path / contract["bundle_path"]
    assert contract["release_digest"] == report["release_digest"]
    assert bundle.is_file()
    assert release_verdict.sha256_file(bundle) == contract["bundle_sha256"]
    first_bundle_sha = contract["bundle_sha256"]

    # Volatile report metadata may change, but the digest bundle remains the
    # first immutable evidence packet for those exact material inputs.
    refreshed = dict(report)
    refreshed["created_at"] = "2099-01-01T00:00:00+00:00"
    release_verdict.write_outputs(tmp_path, "第1话", refreshed)
    second = json.loads(contract_path.read_text(encoding="utf-8"))
    assert second["bundle_path"] == contract["bundle_path"]
    assert second["bundle_sha256"] == first_bundle_sha


def test_release_revision_pointer_is_last_and_post_pointer_crash_is_consistent(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    first = release_verdict.build(tmp_path, "第1话", "internal")
    release_verdict.write_outputs(tmp_path, "第1话", first)
    contract_path = tmp_path / "生产数据" / "release_contract_第1话.json"
    first_contract = json.loads(contract_path.read_text(encoding="utf-8"))
    assert first_contract["schema_version"] == 3
    assert release_verdict.verify_stored_completion(tmp_path, "第1话")["current"] is True
    second = dict(first)
    second.update({"usage": "public", "delivery_axis": "web_images+public"})
    second["release_digest"] = release_verdict.canonical_release_digest(second)
    second["business_status"] = release_verdict.build_completion_verdict(tmp_path, second)["status"]

    def fail_before_pointer(stage: str) -> None:
        if stage == "before_pointer":
            raise RuntimeError("injected before active pointer")

    with pytest.raises(RuntimeError, match="before active pointer"):
        release_verdict.write_outputs(
            tmp_path, "第1话", second, _fault_hook=fail_before_pointer
        )
    assert json.loads(contract_path.read_text(encoding="utf-8")) == first_contract
    # The compatibility completion may have advanced, but authoritative
    # readers follow the old revision's immutable candidate until the pointer
    # switches.
    assert release_verdict.verify_stored_completion(tmp_path, "第1话")["current"] is True

    report_path = tmp_path / "second-release-report.json"
    report_path.write_text(json.dumps(second, ensure_ascii=False), encoding="utf-8")
    script = (
        "import importlib.util,json,os,pathlib\n"
        f"p=pathlib.Path({str(MODULE_PATH)!r})\n"
        "s=importlib.util.spec_from_file_location('release_crash_tested',p)\n"
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
        f"root=pathlib.Path({str(tmp_path)!r})\n"
        f"report=json.loads(pathlib.Path({str(report_path)!r}).read_text(encoding='utf-8'))\n"
        "def crash(stage):\n"
        "  if stage=='after_pointer': os._exit(47)\n"
        "m.write_outputs(root,'第1话',report,_fault_hook=crash)\n"
    )
    crashed = subprocess.run([sys.executable, "-c", script], check=False)
    assert crashed.returncode == 47
    active = json.loads(contract_path.read_text(encoding="utf-8"))
    assert active["release_digest"] == second["release_digest"]
    assert (tmp_path / active["completion_path"]).is_file()
    assert release_verdict.verify_stored_completion(tmp_path, "第1话")["current"] is True


def test_final_acceptance_atomically_selects_new_completion_candidate(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    report = release_verdict.build(tmp_path, "第1话", "internal")
    release_verdict.write_outputs(tmp_path, "第1话", report)
    contract_path = tmp_path / "生产数据" / "release_contract_第1话.json"
    before = json.loads(contract_path.read_text(encoding="utf-8"))
    assert release_verdict.verify_stored_completion(tmp_path, "第1话")["status"] == "machine_ready"

    release_verdict.accept_final(
        tmp_path, report, accepted_by="Wesley", note="current release pixels accepted"
    )

    after = json.loads(contract_path.read_text(encoding="utf-8"))
    assert after["release_digest"] == before["release_digest"]
    assert after["completion_path"] != before["completion_path"]
    verified = release_verdict.verify_stored_completion(tmp_path, "第1话")
    assert verified["current"] is True
    assert verified["status"] == "accepted"


def test_professional_print_receipt_binds_pages_pdf_and_both_validators(tmp_path: Path) -> None:
    page = tmp_path / "排版" / "第1话" / "pages" / "page_001.png"
    write_png(page, (32, 32))
    profile = tmp_path / "profiles" / "press.icc"
    profile.parent.mkdir(parents=True)
    profile.write_bytes(b"icc-profile")
    pdf = tmp_path / "排版" / "第1话" / "print" / "第1话_PDF-X-4.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.7\n/Type /Page /TrimBox /BleedBox /OutputIntent PDF/X-4\n%%EOF")
    contract_path = tmp_path / "排版" / "第1话" / "print_delivery_contract.json"
    contract = {
        "kind": "comic_print_delivery_contract", "chapter": "第1话", "pdf_standard": "PDF/X-4",
        "renderer": {"mode": "professional_external"}, "dpi": 300,
        "geometry_mm": {"trim": {"width": 100, "height": 150}, "bleed": {"top": 3, "bottom": 3, "inside": 3, "outside": 3}, "safe_area": {"top": 5, "bottom": 5, "inside": 5, "outside": 5}},
        "binding": {"reading_direction": "ltr", "edge": "left"},
        "font_handling": {"mode": "outlined"},
        "color": {"icc_profile_path": str(profile), "icc_profile_sha256": release_verdict.sha256_file(profile)},
    }
    write_json(contract_path, contract)
    external = {"status": "pass", "pdf_standard": "PDF/X-4", "validator": "fixture", "checks": {"boxes": True, "icc": True}}
    receipt_path = tmp_path / "生产数据" / "professional_print_receipt_第1话.json"
    receipt = {
        "kind": "comic_professional_print_receipt", "status": "pass", "chapter": "第1话",
        "contract": {"path": str(contract_path.relative_to(tmp_path)), "sha256": release_verdict.sha256_file(contract_path)},
        "inputs": [{"path": str(page.relative_to(tmp_path)), "sha256": release_verdict.sha256_file(page)}],
        "pdf": {"path": str(pdf.relative_to(tmp_path)), "sha256": release_verdict.sha256_file(pdf), "standard": "PDF/X-4"},
        "internal_validation": {"status": "pass", "checks": {"header": True, "output_intent": True}},
        "external_validator_receipt": external,
        "external_validator_receipt_sha256": release_verdict.stable_sha256(external),
    }
    write_json(receipt_path, receipt)
    write_json(tmp_path / "生产数据" / "print_readiness_receipt_第1话.json", {
        "kind": "comic_print_readiness_receipt", "status": "approved", "reviewer": "press-editor",
        "checks": {"safe": True, "order": True, "color": True, "font": True},
        "professional_print_receipt": {"path": str(receipt_path.relative_to(tmp_path)), "sha256": release_verdict.sha256_file(receipt_path)},
    })
    manifest = {
        "pages": [{"path": str(page.relative_to(tmp_path))}],
        "documents": [{"format": "pdf_x4", "path": str(pdf.relative_to(tmp_path)), "sha256": release_verdict.sha256_file(pdf)}],
    }
    artifacts = [{
        "format": "pdf", "declared_document_format": "pdf_x4",
        "path": str(pdf.relative_to(tmp_path)), "sha256": release_verdict.sha256_file(pdf),
    }]
    assert release_verdict.print_delivery_checks(tmp_path, "第1话", manifest, artifacts) == []
    medium_binding = release_verdict.medium_specific_binding(
        tmp_path, "第1话", "print_pdf", manifest, artifacts
    )
    assert medium_binding["icc_profile"] == {
        "path": "profiles/press.icc",
        "sha256": release_verdict.sha256_file(profile),
        "declared_sha256": release_verdict.sha256_file(profile),
        "profile_name": "press.icc",
        "source_kind": "project_file",
    }
    settings = tmp_path / "_设置.md"
    settings.write_text(
        "- 交付介质: print_pdf\n- 交付用途: internal\n- 目标平台: 通用\n",
        encoding="utf-8",
    )
    release_report = {
        "schema_version": 2,
        "kind": "comic_release_verdict",
        "chapter": "第1话",
        "medium": "print_pdf",
        "usage": "internal",
        "target_platform": "通用",
        "delivery_axis": "print_pdf+internal",
        "profile": "print",
        "verdict": "pass",
        "issues": [],
        "artifacts": artifacts,
        "settings_binding": {
            "path": "_设置.md", "sha256": release_verdict.sha256_file(settings),
        },
        "medium_specific_binding": medium_binding,
    }
    release_report["release_digest"] = release_verdict.canonical_release_digest(release_report)
    release_verdict.write_outputs(tmp_path, "第1话", release_report)
    assert release_verdict.verify_stored_completion(tmp_path, "第1话")["current"] is True
    profile.write_bytes(b"tampered-icc-profile")
    stale = release_verdict.verify_stored_completion(tmp_path, "第1话")
    assert stale["current"] is False
    assert any("icc_profile" in problem for problem in stale["issues"])

    external["checks"]["icc"] = False
    receipt["external_validator_receipt"] = external
    receipt["external_validator_receipt_sha256"] = release_verdict.stable_sha256(external)
    write_json(receipt_path, receipt)
    assert "professional_print_receipt_invalid_or_stale" in {
        item["code"] for item in release_verdict.print_delivery_checks(tmp_path, "第1话", manifest, artifacts)
    }


def test_c2pa_sidecar_never_satisfies_signed_claim(tmp_path: Path) -> None:
    sidecar = tmp_path / "out.png.provenance.json"
    write_json(sidecar, {"kind": "comic_c2pa_compatible_disclosure_sidecar", "c2pa_status": "not_signed"})
    issues = release_verdict.check_c2pa_truth(tmp_path, {
        "artifact_credentials": [{
            "path": "out.png", "sha256": "a" * 64, "c2pa_status": "signed",
            "c2pa_receipt": {"path": sidecar.name, "sha256": release_verdict.sha256_file(sidecar)},
        }]
    })
    assert {item["code"] for item in issues} == {"c2pa_signed_claim_invalid"}
    assert release_verdict.check_c2pa_truth(tmp_path, {
        "artifact_credentials": [{"path": "out.png", "sha256": "a" * 64, "c2pa_status": "not_signed"}]
    }) == []
