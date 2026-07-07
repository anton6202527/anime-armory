from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("pilot_check.py")
spec = importlib.util.spec_from_file_location("pilot_check", SCRIPT)
pilot_check = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(pilot_check)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def test_pilot_check_requires_artifact_and_qc_evidence(tmp_path: Path) -> None:
    _write_json(tmp_path / "生产数据" / "pilot_acceptance_第1集.json", {
        "status": "accepted",
        "reviewer": "human-qc",
        "risk_selection": {"method": "风险排序"},
        "clips": [{"clip_id": "Clip_01"}, {"clip_id": "Clip_02"}],
        "coverage": ["face", "scene", "action", "lipsync", "seam", "routing"],
        "checks": {"face": "pass", "scene": "pass", "action": "pass", "lipsync": "pass", "seam": "pass", "routing": "pass"},
    })

    report = pilot_check.check(tmp_path, "第1集")

    assert report["status"] == "blocked"
    assert any("artifact_path" in issue for issue in report["issues"])
    assert any("qc_report" in issue for issue in report["issues"])
