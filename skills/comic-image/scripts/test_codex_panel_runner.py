from pathlib import Path
import importlib.util
import json


MODULE_PATH = Path(__file__).with_name("codex_panel_runner.py")
SPEC = importlib.util.spec_from_file_location("comic_codex_panel_runner", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def write_current_gate_receipt(root: Path, jobs: Path, *, verdict: str = "pass") -> Path:
    chapter = "第1话"
    report = root / "生产数据" / f"comic_gate_image_preflight_{chapter}.json"
    fingerprint = runner.stage_inputs_fingerprint(root, chapter, "image_preflight")
    runner.write_json(report, {
        "kind": "comic_gate", "stage": "image_preflight", "chapter": chapter, "verdict": verdict,
        "inputs_fingerprint": fingerprint,
    })
    receipt = runner.gate_receipt_path(root, chapter)
    runner.write_json(receipt, {
        "kind": "comic_gate_receipt",
        "stage": "image_preflight",
        "chapter": chapter,
        "verdict": verdict,
        "execution_authorized": verdict != "block",
        "panel_jobs_sha256": runner.file_sha256(jobs),
        "inputs_fingerprint_sha256": fingerprint["sha256"],
        "report_path": str(report.relative_to(root)),
        "report_sha256": runner.file_sha256(report),
    })
    return receipt


def test_reference_attachment_budget_prioritizes_identity_scene_and_prop() -> None:
    records = [
        {"id": "STYLE_A", "path": "style.png"},
        {"id": "LOC_A", "path": "loc.png"},
        {"id": "CHAR_A", "path": "a.png"},
        {"id": "CHAR_B", "path": "b.png"},
        {"id": "PROP_A", "path": "prop.png"},
        {"id": "FX_A", "path": "fx.png"},
    ]

    selected, omitted = runner.select_reference_attachments(records)

    assert [record["id"] for record in selected] == ["STYLE_A", "LOC_A", "CHAR_A", "CHAR_B", "PROP_A"]
    assert [record["id"] for record in omitted] == ["FX_A"]


def test_reference_manifest_discloses_omitted_text_only_contract(tmp_path: Path) -> None:
    used = [{"id": "CHAR_A", "path": "a.png", "abs_path": "/tmp/a.png", "sha256": "a"}]
    omitted = [{"id": "FX_A", "path": "fx.png", "abs_path": "/tmp/fx.png", "sha256": "f"}]

    path = runner.write_reference_manifest(tmp_path, "第1话", "P001", used, omitted)
    payload = runner.load_json(path)

    assert payload["reference_attachment_limit"] == 5
    assert payload["omitted_attachment_count"] == 1
    assert payload["omitted_attachments"][0]["id"] == "FX_A"
    assert "textual_contract_retained" in payload["omitted_attachments"][0]["reason"]


def test_post_qc_accepts_disclosed_tool_limit_omission(tmp_path: Path, monkeypatch) -> None:
    panel = tmp_path / "P015.png"
    panel.write_bytes(b"png")
    monkeypatch.setattr(runner, "png_valid", lambda _path: True)
    monkeypatch.setattr(runner, "image_size", lambda _path: (100, 100))
    monkeypatch.setattr(runner, "likely_blank_bubble_regions", lambda _path: [])
    job = {
        "panel_id": "P015",
        "size": {"width": 100, "height": 100},
        "references": [{"id": f"REF_{index}"} for index in range(6)],
    }
    used = [{"id": f"REF_{index}"} for index in range(5)]
    omitted = [{"id": "REF_5"}]

    payload = runner.post_qc_panel(tmp_path, "第1话", job, panel, used, omitted)

    assert payload["verdict"] == "pass"
    assert payload["omitted_attachment_count"] == 1
    assert payload["manual_review_required"] is False


def test_gate_receipt_must_bind_current_panel_jobs_sha(tmp_path: Path) -> None:
    jobs = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    jobs.parent.mkdir(parents=True)
    jobs.write_text('{"jobs": []}\n', encoding="utf-8")
    write_current_gate_receipt(tmp_path, jobs)
    assert runner.validate_gate_receipt(tmp_path, "第1话", jobs)["status"] == "current_pass"
    jobs.write_text('{"jobs": [{"panel_id":"P1"}]}\n', encoding="utf-8")
    assert runner.validate_gate_receipt(tmp_path, "第1话", jobs)["status"] == "stale_or_not_passed"


def test_warn_receipt_can_authorize_when_there_are_no_blocks(tmp_path: Path) -> None:
    jobs = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    jobs.parent.mkdir(parents=True)
    jobs.write_text('{"jobs": []}', encoding="utf-8")
    write_current_gate_receipt(tmp_path, jobs, verdict="warn")
    assert runner.validate_gate_receipt(tmp_path, "第1话", jobs)["status"] == "current_pass"


def test_gate_receipt_stales_when_non_job_preflight_input_changes(tmp_path: Path) -> None:
    jobs = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    jobs.parent.mkdir(parents=True)
    jobs.write_text('{"jobs": []}', encoding="utf-8")
    settings = tmp_path / "_设置.md"
    settings.write_text("- 生产档位: 连载标准\n", encoding="utf-8")
    write_current_gate_receipt(tmp_path, jobs)
    assert runner.validate_gate_receipt(tmp_path, "第1话", jobs)["status"] == "current_pass"
    settings.write_text("- 生产档位: 出版交付\n", encoding="utf-8")
    assert runner.validate_gate_receipt(tmp_path, "第1话", jobs)["status"] == "stale_or_not_passed"


def test_skip_gate_waiver_is_persistent_and_sha_bound(tmp_path: Path) -> None:
    jobs = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    jobs.parent.mkdir(parents=True)
    jobs.write_text('{"jobs": []}\n', encoding="utf-8")
    status = {"status": "missing", "reason": "receipt_missing"}
    path = runner.write_gate_waiver(tmp_path, "第1话", jobs, "人工确认本次误报", "P001", status)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["reason"] == "人工确认本次误报"
    assert payload["panel_jobs_sha256"] == runner.file_sha256(jobs)
    assert payload["targets"] == ["P001"]
    assert (path.parent / "image_preflight_第1话_latest.json").is_file()
