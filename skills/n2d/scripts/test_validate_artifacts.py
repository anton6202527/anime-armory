from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("validate_artifacts.py")
spec = importlib.util.spec_from_file_location("validate_artifacts", SCRIPT)
validate_artifacts = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validate_artifacts)


def test_validate_artifacts_cli_writes_report(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "batch_queue.json").write_text(
        json.dumps({"kind": "n2d_batch_queue", "version": 1, "root": str(tmp_path), "tasks": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    rc = validate_artifacts.main([str(tmp_path), "--write"])

    assert rc == 0
    assert (prod / "artifact_validation.json").is_file()
    assert (prod / "artifact_validation.md").is_file()
    payload = json.loads((prod / "artifact_validation.json").read_text(encoding="utf-8"))
    assert payload["scanned_count"] == 1
    assert payload["skipped_count"] == 0
    markdown = (prod / "artifact_validation.md").read_text(encoding="utf-8")
    assert "已严格扫描：1" in markdown
    assert "已跳过：0" in markdown


def test_validate_artifacts_cli_reports_structured_skips(tmp_path: Path) -> None:
    (tmp_path / "小说").mkdir()
    (tmp_path / "小说" / "_源指纹.json").write_text('{"sha256":"abc"}', encoding="utf-8")

    rc = validate_artifacts.main([str(tmp_path), "--write", "--strict-unknown"])

    assert rc == 0
    payload = json.loads((tmp_path / "生产数据" / "artifact_validation.json").read_text(encoding="utf-8"))
    assert payload["scanned_count"] == 0
    assert payload["skipped_count"] == 1
    assert payload["skipped"][0]["skip_reason"]["code"] == "source_fingerprint"


def test_release_strict_report_binds_current_scanned_content(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    queue = prod / "batch_queue.json"
    queue.write_text(
        json.dumps({
            "kind": "n2d_batch_queue", "version": 1,
            "root": str(tmp_path), "tasks": [],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    rc = validate_artifacts.main([
        str(tmp_path), "--write", "--scope", "release", "--strict-unknown",
    ])
    assert rc == 0
    report = json.loads((prod / "artifact_validation.json").read_text(encoding="utf-8"))
    assert report["kind"] == "n2d_artifact_validation"
    assert report["version"] == 1
    assert Path(report["root"]) == tmp_path.resolve()
    assert report["scope"] == "release"
    assert report["strict_unknown"] is True
    assert report["completion_inputs_only"] is True
    assert report["source"]["evidence_sha256"]
    assert report["content_sha256"]
    assert report["scanned"][0]["sha256"]

    current = validate_artifacts.scan_artifacts(
        str(tmp_path), strict_unknown=True, scope="release", completion_inputs_only=True
    )
    assert report == current

    queue.write_text(
        json.dumps({
            "kind": "n2d_batch_queue", "version": 1,
            "root": str(tmp_path), "tasks": [{
                "id": "task-1", "episode": "第1集", "stage_key": "image", "status": "pending",
            }],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    changed = validate_artifacts.scan_artifacts(
        str(tmp_path), strict_unknown=True, scope="release", completion_inputs_only=True
    )
    assert changed["source"]["evidence_sha256"] != report["source"]["evidence_sha256"]
    assert changed != report
