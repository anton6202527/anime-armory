from __future__ import annotations

import json
from pathlib import Path

import contracts


def test_stage_fingerprint_changes_when_missing_input_appears(tmp_path: Path) -> None:
    root = tmp_path
    (root / "_设置.md").write_text("- 漫画形态: 条漫\n", encoding="utf-8")
    before = contracts.stage_inputs_fingerprint(root, "第1话", "script")
    script = root / "脚本" / "第1话" / "panel_script.json"
    script.parent.mkdir(parents=True)
    script.write_text(json.dumps({"panels": []}), encoding="utf-8")
    after = contracts.stage_inputs_fingerprint(root, "第1话", "script")
    assert before["sha256"] != after["sha256"]


def test_receipt_requires_exact_current_fingerprint() -> None:
    assert contracts.receipt_is_current({"inputs_fingerprint_sha256": "a"}, {"sha256": "a"})
    assert not contracts.receipt_is_current({"inputs_fingerprint_sha256": "a"}, {"sha256": "b"})
    assert not contracts.receipt_is_current({}, {"sha256": "a"})


def test_approval_requires_reviewer_time_decision_and_sha() -> None:
    payload = {
        "status": "approved",
        "approval": {
            "decision": "approved",
            "reviewer": "editor",
            "approved_at": "2026-07-14T00:00:00Z",
            "inputs_sha256": "abc",
        },
    }
    assert contracts.approval_is_current(payload, current_inputs_sha256="abc") == (True, "")
    ok, reason = contracts.approval_is_current(payload, current_inputs_sha256="def")
    assert not ok and reason == "approval stale"


def test_editorial_approval_shape_is_supported() -> None:
    payload = {
        "workflow_status": "approved",
        "approval": {
            "status": "approved",
            "reviewed_by": "editor",
            "reviewed_at": "2026-07-14T00:00:00Z",
            "subject_sha256": "subject",
        },
    }
    assert contracts.approval_is_current(payload, current_inputs_sha256="subject") == (True, "")


def test_progress_change_does_not_invalidate_production_receipt(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 生产档位: 连载标准\n", encoding="utf-8")
    (tmp_path / "_进度.md").write_text("草稿\n", encoding="utf-8")
    before = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "layout")
    (tmp_path / "_进度.md").write_text("已完成\n", encoding="utf-8")
    after = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "layout")
    assert before["sha256"] == after["sha256"]


def test_review_fingerprint_binds_rendered_artifact_bytes(tmp_path: Path) -> None:
    artifact = tmp_path / "排版" / "第1话" / "长图" / "final.png"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"v1")
    manifest = tmp_path / "排版" / "第1话" / "export_manifest.json"
    manifest.write_text(
        json.dumps({"rendered": [{"path": "排版/第1话/长图/final.png"}]}),
        encoding="utf-8",
    )
    before = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "review")
    artifact.write_bytes(b"v2")
    after = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "review")
    assert before["sha256"] != after["sha256"]


def test_review_fingerprint_is_transitive_over_development_and_source(tmp_path: Path) -> None:
    strategy = tmp_path / "开发包" / "adaptation_strategy.json"
    strategy.parent.mkdir(parents=True)
    strategy.write_text('{"status":"confirmed","boundary":"v1"}', encoding="utf-8")
    source = tmp_path / "源本" / "story.md"
    source.parent.mkdir(parents=True)
    source.write_text("第一版", encoding="utf-8")
    blueprint = tmp_path / "脚本" / "split_blueprint.json"
    blueprint.parent.mkdir(parents=True)
    blueprint.write_text(json.dumps({
        "chapters": [{"chapter": "第1话", "source_spans": [{"source_path": "源本/story.md", "whole_file": True}]}],
    }), encoding="utf-8")
    before = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "review")
    source.write_text("第二版", encoding="utf-8")
    after_source = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "review")
    assert before["sha256"] != after_source["sha256"]
    strategy.write_text('{"status":"confirmed","boundary":"v2"}', encoding="utf-8")
    after_strategy = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "review")
    assert after_source["sha256"] != after_strategy["sha256"]


def test_preflight_and_review_bind_model_signoff_and_real_reference_bytes(tmp_path: Path) -> None:
    registry = tmp_path / "出图" / "共享" / "identity_registry.json"
    reference = tmp_path / "出图" / "共享" / "图片" / "CHAR_A_front.png"
    reference.parent.mkdir(parents=True)
    reference.write_bytes(b"ref-v1")
    registry.write_text(json.dumps({
        "assets": {"CHAR_A": {"views": {"front": "出图/共享/图片/CHAR_A_front.png"}}},
    }), encoding="utf-8")
    signoff = tmp_path / "生产数据" / "comic_model_pack_signoffs" / "CHAR_A.json"
    signoff.parent.mkdir(parents=True)
    signoff.write_text('{"decision":"approved"}', encoding="utf-8")
    before = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "review")
    reference.write_bytes(b"ref-v2")
    after_reference = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "review")
    assert before["sha256"] != after_reference["sha256"]
    signoff.write_text('{"decision":"revoked"}', encoding="utf-8")
    after_signoff = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "review")
    assert after_reference["sha256"] != after_signoff["sha256"]


def test_review_fingerprint_binds_manifest_pages_not_only_rendered(tmp_path: Path) -> None:
    page = tmp_path / "排版" / "第1话" / "pages" / "p001.png"
    page.parent.mkdir(parents=True)
    page.write_bytes(b"page-v1")
    manifest = tmp_path / "排版" / "第1话" / "export_manifest.json"
    manifest.write_text(json.dumps({"pages": [{"path": "排版/第1话/pages/p001.png"}]}), encoding="utf-8")
    before = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "review")
    page.write_bytes(b"page-v2")
    after = contracts.stage_inputs_fingerprint(tmp_path, "第1话", "review")
    assert before["sha256"] != after["sha256"]
