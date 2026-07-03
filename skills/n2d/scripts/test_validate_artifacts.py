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
