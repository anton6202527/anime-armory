import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract  # noqa: E402
import stage_acceptance as sa  # noqa: E402


def write(root, rel, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    else:
        path.write_text(value, encoding="utf-8")
    return path


def test_every_contract_stage_has_explicit_typed_criteria():
    for stage in contract.stage_table():
        rows = contract.stage_criteria(stage["key"])
        assert rows
        assert all(row["evidence"] in {"deterministic", "official", "house", "human", "heuristic"} for row in rows)
        assert all(row.get("authority") and row.get("threshold") and row.get("on_fail") for row in rows)


def test_brief_acceptance_requires_campaign_objective(tmp_path):
    write(tmp_path, "需求/brief.json", {"brand": "B", "product": "P", "usp": ["U"], "audience": "A"})
    report = sa.evaluate(tmp_path, "brief")
    assert report["summary"]["accepted"] is False
    assert any("campaign_objective" in f["msg"] for f in report["findings"])


def test_concept_acceptance_has_machine_completion_standard(tmp_path):
    write(tmp_path, "需求/brief.json", {"brand": "B", "product": "P", "usp": ["U"],
                                         "audience": "A", "campaign_objective": "转化行动"})
    write(tmp_path, "创意/concept.md", "# 概念\n## Big Idea\nX\n## 一句话主张\nY\n## 广告目标\n转化\n## 创意假设\nH1\n## 强制项\nLogo")
    write(tmp_path, "创意/创意脚本.md", "故事展开")
    sa.dependency_graph.accept_stage(tmp_path, "brief")
    report = sa.evaluate(tmp_path, "concept")
    assert report["summary"]["block"] == 0


def test_formal_stage_cannot_skip_missing_upstream_hash_receipts(tmp_path):
    write(tmp_path, "创意/concept.md", "Big Idea key message 广告目标 创意假设 强制项")
    write(tmp_path, "创意/创意脚本.md", "treatment")
    report = sa.evaluate(tmp_path, "concept")
    assert any(row["code"] == "dependency_receipts_missing" and row["severity"] == "block"
               for row in report["findings"])


def test_compose_acceptance_blocks_missing_planned_deliverable(tmp_path):
    write(tmp_path, "合成/delivery_plan.json", {"deliverables": [
        {"deliverable_id": "master", "exists": True},
        {"deliverable_id": "cut_6s", "exists": False},
    ]})
    write(tmp_path, "合成/delivery_qc.json", {"summary": {"block": 0, "warn": 0},
                                                "items": [{"deliverable_id": "master", "passed": True}]})
    report = sa.evaluate(tmp_path, "compose")
    assert any(f["code"] == "deliverable_not_accepted" for f in report["findings"])
