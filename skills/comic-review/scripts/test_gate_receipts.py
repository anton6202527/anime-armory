from __future__ import annotations

import json
from pathlib import Path

import gate


def test_heuristic_block_is_forced_down_to_warn() -> None:
    findings: list[dict] = []
    gate.add(
        findings,
        "block",
        "uncalibrated_score",
        "P001",
        "numeric proxy",
        "review",
        "human review",
        confidence="heuristic",
    )
    assert findings[0]["severity"] == "warn"
    assert findings[0]["confidence"] == "heuristic"


def test_gate_receipt_binds_current_inputs(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 漫画形态: 条漫\n", encoding="utf-8")
    jobs = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    jobs.parent.mkdir(parents=True)
    jobs.write_text('{"jobs": []}', encoding="utf-8")
    report = gate.make_report(tmp_path, "第1话", "script", [], [])
    paths = gate.write_outputs(tmp_path, "第1话", "script", report)
    receipt = json.loads((tmp_path / paths["receipt"]).read_text(encoding="utf-8"))
    assert receipt["verdict"] == "pass"
    assert receipt["execution_authorized"] is True
    assert receipt["inputs_fingerprint_sha256"] == report["inputs_fingerprint"]["sha256"]
    assert receipt["report_sha256"]
    assert receipt["panel_jobs_sha256"]
    assert receipt["panel_jobs_sha256"] == receipt["artifacts"]["panel_jobs_sha256"]


def test_receipt_input_hash_changes_when_script_changes(tmp_path: Path) -> None:
    script = tmp_path / "脚本" / "第1话" / "panel_script.json"
    script.parent.mkdir(parents=True)
    script.write_text('{"panels": []}', encoding="utf-8")
    first = gate.make_report(tmp_path, "第1话", "script", [], [])
    script.write_text('{"panels": [{"panel_id": "P001"}]}', encoding="utf-8")
    second = gate.make_report(tmp_path, "第1话", "script", [], [])
    assert first["inputs_fingerprint"]["sha256"] != second["inputs_fingerprint"]["sha256"]


def test_visual_metric_block_is_downgraded_but_missing_file_is_not() -> None:
    findings: list[dict] = []
    gate.merge_consistency_report(
        {
            "findings": [
                {"severity": "block", "code": "internal_panel_gutters", "evidence_family": "layout_geometry"},
                {"severity": "block", "code": "panel_image_missing", "evidence_family": "artifact_presence"},
            ]
        },
        findings,
        category="style_consistency",
    )
    assert [item["severity"] for item in findings] == ["warn", "block"]
