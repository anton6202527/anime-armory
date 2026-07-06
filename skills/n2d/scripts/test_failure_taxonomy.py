from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("failure_taxonomy.py")
spec = importlib.util.spec_from_file_location("failure_taxonomy", SCRIPT)
failure_taxonomy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(failure_taxonomy)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def test_production_profile_escalates_report_only_warn(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "合规" / "compliance_manifest.json", {"distribution_intent": "internal_only"})
    _write_json(tmp_path / "生产数据" / f"gate_findings_review_{ep}.json", {
        "findings": [{"severity": "warn", "dimension": "场景连续性", "message": "关键反打镜头接缝不稳，需要导演确认"}]
    })
    _write_json(tmp_path / "生产数据" / f"score_{ep}.json", {"status": "pass", "score": 91, "threshold": 80})

    payload = failure_taxonomy.build_taxonomy(tmp_path, ep, profile="production")

    assert payload["status"] == "blocked"
    item = payload["items"][0]
    assert item["escalated_severity"] == "block"
    assert "production_profile" in item["escalation_reasons"]
    assert item["category"] == "director_blocking"
    plan = payload["return_plan"][0]
    assert plan["category"] == "director_blocking"
    assert "导演" in plan["owner"]
    assert any("director_blocking_pack.py" in cmd for cmd in plan["rerun_after_fix"])


def test_low_score_context_does_not_escalate_report_only_warn_in_demo(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "合规" / "compliance_manifest.json", {"distribution_intent": "internal_only"})
    _write_json(tmp_path / "生产数据" / f"gate_findings_review_{ep}.json", {
        "findings": [{"severity": "warn", "dimension": "台词", "message": "旁白解释略生硬"}]
    })
    _write_json(tmp_path / "生产数据" / f"score_{ep}.json", {"status": "warn", "score": 62, "threshold": 80})

    payload = failure_taxonomy.build_taxonomy(tmp_path, ep, profile="demo")

    assert payload["status"] == "warn"
    item = payload["items"][0]
    assert item["category"] == "script"
    assert item["escalation_reasons"] == []
    assert item["escalated_severity"] == "warn"
    plan = payload["return_plan"][0]
    assert plan["category"] == "script"
    assert "编剧" in plan["owner"]


def test_repeated_report_only_requires_independent_sources_and_strict_context(tmp_path: Path) -> None:
    ep = "第1集"
    _write_json(tmp_path / "合规" / "compliance_manifest.json", {"distribution_intent": "commercial"})
    _write_json(tmp_path / "生产数据" / f"gate_findings_review_{ep}.json", {
        "findings": [{"severity": "warn", "dimension": "字幕正确性", "message": "译名略不统一"}]
    })
    _write_json(tmp_path / "生产数据" / f"review_ui_findings_{ep}.json", {
        "findings": [
            {"sev": "warn", "dim": "字幕正确性", "msg": "译名略不统一"},
            {"sev": "warn", "dim": "字幕正确性", "msg": "字幕术语需人工确认"},
        ]
    })
    _write_json(tmp_path / "生产数据" / f"score_{ep}.json", {"status": "pass", "score": 91, "threshold": 80})

    payload = failure_taxonomy.build_taxonomy(tmp_path, ep, profile="demo")

    assert payload["status"] == "blocked"
    assert any("repeated_independent_report_only_findings" in item["escalation_reasons"]
               for item in payload["items"])
