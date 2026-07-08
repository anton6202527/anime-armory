from __future__ import annotations

import json
from pathlib import Path

import creative_governance as cg


def test_scaffold_creates_raci_and_warns_when_only_template_decision(tmp_path: Path) -> None:
    cg.scaffold(tmp_path)

    report = cg.check(tmp_path)

    assert report["status"] == "warn"
    assert (tmp_path / "生产数据" / "crew_raci.json").is_file()
    assert any(f["code"] == "no_real_decisions" for f in report["findings"])


def test_real_decision_and_raci_pass(tmp_path: Path) -> None:
    cg.scaffold(tmp_path)
    decision = {
        "kind": "n2d_creative_decision",
        "version": 1,
        "decision_type": "unlock",
        "owner": "producer",
        "scope": "storyboard_lock",
        "accepted_choice": "只重跑 Clip_02",
        "reason": "导演调整反转镜头",
        "affected_artifacts": ["脚本/第1集/storyboard.json"],
        "affected_stages": ["image_prompt"],
    }
    (tmp_path / "生产数据" / "creative_decisions.jsonl").write_text(json.dumps(decision, ensure_ascii=False) + "\n", encoding="utf-8")

    report = cg.check(tmp_path)

    assert report["status"] == "pass"
    assert report["summary"]["decisions"] == 1


def test_require_decision_blocks_template_and_requires_rerun_scope(tmp_path: Path) -> None:
    cg.scaffold(tmp_path)

    blocked = cg.check(tmp_path, require_decision=True, reason="production")

    assert blocked["status"] == "block"
    assert any(f["code"] == "decision_required" for f in blocked["findings"])

    decision = {
        "kind": "n2d_creative_decision",
        "version": 1,
        "decision_type": "unlock",
        "owner": "producer",
        "scope": "storyboard_lock",
        "accepted_choice": "只重跑 Clip_02",
        "reason": "锁后改了反转镜头",
        "affected_artifacts": ["脚本/第1集/storyboard.json"],
        "affected_stages": ["image_prompt"],
        "follow_up_batch_scope": "Clip_02 only",
    }
    (tmp_path / "生产数据" / "creative_decisions.jsonl").write_text(json.dumps(decision, ensure_ascii=False) + "\n", encoding="utf-8")

    passed = cg.check(tmp_path, require_decision=True, reason="production")

    assert passed["status"] == "pass"
    assert passed["summary"]["production_ready_decisions"] == 1


def test_major_change_reasons_auto_require_decision(tmp_path: Path) -> None:
    cg.scaffold(tmp_path)
    prod = tmp_path / "生产数据"
    (prod / "production_events.jsonl").write_text(
        json.dumps({
            "kind": "n2d_production_event",
            "episode": "第1集",
            "stage": "image",
            "event": "waiver",
            "meta": {"waiver": "skip-final-gate", "reason": "operator override"},
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report = cg.check(tmp_path)

    assert report["status"] == "block"
    assert report["require_decision"] is True
    assert any(f["code"] == "major_change_decision_required" for f in report["findings"])
