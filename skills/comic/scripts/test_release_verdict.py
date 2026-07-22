from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image


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
    write_json(report_path, {
        "kind": "comic_gate", "stage": "review", "chapter": "第1话", "verdict": "pass",
        "inputs_fingerprint": current,
    })
    write_json(root / "生产数据" / "gate_receipts" / "review_第1话.json", {
        "kind": "comic_gate_receipt", "stage": "review", "chapter": "第1话",
        "receipt_id": "receipt-1",
        "verdict": "pass",
        "execution_authorized": True,
        "inputs_fingerprint_sha256": current["sha256"],
        "report_path": str(report_path.relative_to(root)),
        "report_sha256": release_verdict.sha256_file(report_path),
    })
    return artifacts


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
    assert payload["review_receipt"]["receipt_id"] == "receipt-1"
    assert release_verdict.build(tmp_path, "第1话", "digital")["verdict"] == "pass"


def test_public_release_blocks_missing_or_ambiguous_rights(tmp_path: Path) -> None:
    artifacts = prepare_project(tmp_path)
    write_json(tmp_path / "生产数据" / "release_acceptance_第1话.json", {
        "status": "approved", "profile": "digital", "reviewer": "editor",
        "reason": "发布前最终复核", "approved_at": "2026-07-14T00:00:00Z",
        "artifacts": artifacts,
        "review_receipt": release_verdict.review_receipt_binding(tmp_path, "第1话"),
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
    })
    report = release_verdict.build(tmp_path, "第1话", "print")
    assert "release_acceptance_profile_mismatch" in {item["code"] for item in report["issues"]}


def test_accept_can_replace_a_current_acceptance_for_another_profile(tmp_path: Path) -> None:
    prepare_project(tmp_path)
    release_verdict.create_acceptance(
        tmp_path, "第1话", "digital", reviewer="editor", reason="数字发布复核"
    )
    path = release_verdict.create_acceptance(
        tmp_path, "第1话", "print", reviewer="print-editor", reason="印刷交付复核"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["profile"] == "print"
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
