"""stop_loss 边界测试（2026-07 标准审计补：此前无单测，"空账恒 pass"曾冒充"核过 stop-loss"）。

运行：cd skills/n2d/scripts && python -m pytest test_stop_loss.py
"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("stop_loss.py")
spec = importlib.util.spec_from_file_location("stop_loss_mod", SCRIPT)
stop_loss = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(stop_loss)


def test_empty_project_reports_no_evidence_not_pass(tmp_path: Path) -> None:
    report = stop_loss.build_report(tmp_path)
    assert report["status"] == "no_evidence"
    assert any(v["metric"] == "evidence" for v in report["violations"])


def test_findings_over_threshold_go_critical(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir(parents=True)
    findings = [{"severity": "block", "dim": "角色一致性", "msg": "崩脸 脸部漂移"} for _ in range(5)]
    (prod / "gate_findings_image_第1集.json").write_text(
        json.dumps({"findings": findings}, ensure_ascii=False), encoding="utf-8")
    report = stop_loss.build_report(tmp_path, episode="第1集")
    assert report["status"] == "critical"
    assert any(v["metric"] == "qc_block_rate" for v in report["violations"])


def test_missing_dashboard_cost_leaves_warn_not_silence(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir(parents=True)
    (prod / "gate_findings_image_第1集.json").write_text(
        json.dumps({"findings": [{"severity": "info", "dim": "x", "msg": "ok"}]}, ensure_ascii=False), encoding="utf-8")
    report = stop_loss.build_report(tmp_path, episode="第1集")
    assert any(v["metric"] == "cost_per_finished_min" and v["level"] == "warn"
               for v in report["violations"])
