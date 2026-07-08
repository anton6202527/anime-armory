#!/usr/bin/env python3
from pathlib import Path

import repair_preflight as rp


def test_build_report_runs_full_video_prompt_preflight_stack(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def row(name, status="pass"):
        return {"step": name, "status": status}

    monkeypatch.setattr(rp, "update_plan_check", lambda root, ep: calls.append("update_plan") or row("update_plan"))
    monkeypatch.setattr(rp, "production_breakdown_check", lambda root, ep, write_missing: calls.append("production_breakdown") or row("production_breakdown"))
    monkeypatch.setattr(rp, "production_locks_check", lambda root, ep, stage, write_missing: calls.append(("production_locks", stage)) or row("production_locks", "block"))
    monkeypatch.setattr(rp, "preventive_contracts_check", lambda root, ep, stage, write_missing: calls.append(("preventive_contracts", stage)) or row("preventive_contracts"))
    monkeypatch.setattr(rp, "image_qc_status", lambda root, ep, repair_qc: calls.append("image_qc") or row("image_qc"))

    report = rp.build_report(tmp_path, "第1集", "video_prompt_preflight", write_missing=True, repair_qc=False)

    assert report["status"] == "block"
    assert calls == [
        "update_plan",
        "production_breakdown",
        ("production_locks", "video_prompt_preflight"),
        ("preventive_contracts", "video_prompt_preflight"),
        "image_qc",
    ]


def test_build_report_runs_locks_for_image_stage(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def row(name, status="pass"):
        return {"step": name, "status": status}

    monkeypatch.setattr(rp, "update_plan_check", lambda root, ep: calls.append("update_plan") or row("update_plan"))
    monkeypatch.setattr(rp, "production_breakdown_check", lambda root, ep, write_missing: calls.append("production_breakdown") or row("production_breakdown"))
    monkeypatch.setattr(rp, "production_locks_check", lambda root, ep, stage, write_missing: calls.append(("production_locks", stage)) or row("production_locks"))
    monkeypatch.setattr(rp, "preventive_contracts_check", lambda root, ep, stage, write_missing: calls.append(("preventive_contracts", stage)) or row("preventive_contracts"))

    report = rp.build_report(tmp_path, "第1集", "image", write_missing=False, repair_qc=False)

    assert report["status"] == "pass"
    assert calls == [
        "update_plan",
        "production_breakdown",
        ("production_locks", "image"),
        ("preventive_contracts", "image"),
    ]


def test_main_writes_report_and_exits_nonzero_when_blocked(monkeypatch, tmp_path: Path, capsys) -> None:
    root = tmp_path / "work"

    def fake_build_report(root_path, ep, stage, write_missing, repair_qc):
        return {
            "kind": rp.KIND,
            "version": rp.VERSION,
            "root": str(root_path),
            "episode": ep,
            "stage": stage,
            "status": "block",
            "summary": {"steps": 1, "block": 1, "warn": 0, "pass": 0},
            "steps": [{"step": "update_plan", "status": "block"}],
        }

    monkeypatch.setattr(rp, "build_report", fake_build_report)

    code = rp.main([str(root), "第1集", "--stage", "image_preflight", "--write-missing", "--json"])

    out = capsys.readouterr().out
    assert code == 1
    assert "image_preflight" in out
    assert (root / "生产数据" / "repair_preflight_image_preflight_第1集.json").is_file()
