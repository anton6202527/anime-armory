from pathlib import Path
import importlib.util
import json
import subprocess
import sys

import pytest


MODULE = Path(__file__).with_name("revision_transaction.py")
SPEC = importlib.util.spec_from_file_location("comic_revision_transaction_tested", MODULE)
assert SPEC and SPEC.loader
tx = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(tx)


def test_revision_verify_and_promote(tmp_path: Path, monkeypatch):
    source = tmp_path / "脚本" / "第1话" / "panel_script.json"
    source.parent.mkdir(parents=True); source.write_text('{"v":1}', encoding="utf-8")
    started = tx.start(tmp_path, "fix-1", "第1话", ["脚本/第1话/panel_script.json"])
    candidate = tmp_path / started["files"][0]["candidate_path"]
    candidate.write_text('{"v":2}', encoding="utf-8")
    assert tx.verify(tmp_path, "fix-1", "delegate:quality-editor")["status"] == "prepared"
    monkeypatch.setattr(tx.subprocess, "run", lambda *a, **k: type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    promoted = tx.promote(tmp_path, "fix-1")
    assert promoted["status"] == "committed"
    assert source.read_text(encoding="utf-8") == '{"v":2}'


def test_gate_failure_rolls_back(tmp_path: Path, monkeypatch):
    source = tmp_path / "排版" / "第1话" / "layout.json"
    source.parent.mkdir(parents=True); source.write_text('{"v":1}', encoding="utf-8")
    started = tx.start(tmp_path, "fix-2", "第1话", ["排版/第1话/layout.json"])
    (tmp_path / started["files"][0]["candidate_path"]).write_text('{"v":2}', encoding="utf-8")
    tx.verify(tmp_path, "fix-2", "reviewer")
    monkeypatch.setattr(tx.subprocess, "run", lambda *a, **k: type("P", (), {"returncode": 1, "stdout": "", "stderr": "bad"})())
    result = tx.promote(tmp_path, "fix-2")
    assert result["status"] == "rolled_back"
    assert source.read_text(encoding="utf-8") == '{"v":1}'


def test_real_process_crash_during_promotion_recovers_all_files(tmp_path: Path):
    first = tmp_path / "脚本" / "第1话" / "a.json"
    second = tmp_path / "脚本" / "第1话" / "b.json"
    first.parent.mkdir(parents=True)
    first.write_text('{"v":1}', encoding="utf-8")
    second.write_text('{"v":1}', encoding="utf-8")
    started = tx.start(
        tmp_path, "crash-1", "第1话",
        ["脚本/第1话/a.json", "脚本/第1话/b.json"],
    )
    for row in started["files"]:
        (tmp_path / row["candidate_path"]).write_text('{"v":2}', encoding="utf-8")
    tx.verify(tmp_path, "crash-1", "quality-editor")
    script = (
        "import importlib.util, os, pathlib\n"
        f"p=pathlib.Path({str(MODULE)!r})\n"
        "s=importlib.util.spec_from_file_location('crash_revision',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
        "orig=m._atomic_copy; calls={'n':0}\n"
        "def crash(source,target):\n"
        " orig(source,target); calls['n']+=1\n"
        " if calls['n']==1: os._exit(37)\n"
        "m._atomic_copy=crash\n"
        f"m.promote(pathlib.Path({str(tmp_path)!r}),'crash-1')\n"
    )
    crashed = subprocess.run([sys.executable, "-c", script], check=False)
    assert crashed.returncode == 37
    assert tx.load(tmp_path, "crash-1")["status"] == "promoting"
    recovered = tx.recover(tmp_path, "crash-1")
    assert recovered["status"] == "rolled_back"
    assert first.read_text(encoding="utf-8") == '{"v":1}'
    assert second.read_text(encoding="utf-8") == '{"v":1}'
    assert "promotion_started" in (tmp_path / "生产数据" / "revision_transactions" / "crash-1" / "wal.jsonl").read_text(encoding="utf-8")


def test_old_committed_transaction_refuses_to_overwrite_newer_frontier(tmp_path: Path, monkeypatch):
    source = tmp_path / "脚本" / "第1话" / "panel_script.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"v":1}', encoding="utf-8")
    started = tx.start(tmp_path, "old-committed", "第1话", ["脚本/第1话/panel_script.json"])
    candidate = tmp_path / started["files"][0]["candidate_path"]
    candidate.write_text('{"v":2}', encoding="utf-8")
    tx.verify(tmp_path, "old-committed", "quality-editor")
    monkeypatch.setattr(
        tx.subprocess,
        "run",
        lambda *a, **k: type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    )
    assert tx.promote(tmp_path, "old-committed")["status"] == "committed"
    source.write_text('{"v":3}', encoding="utf-8")

    with pytest.raises(ValueError, match="CAS conflict"):
        tx.rollback(tmp_path, "old-committed")

    assert source.read_text(encoding="utf-8") == '{"v":3}'
    conflicted = tx.load(tmp_path, "old-committed")
    assert conflicted["status"] == "rollback_conflict"
    plan_path = tmp_path / conflicted["rollback_conflict"]["plan_path"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["status"] == "manual_three_way_required"
    assert plan["conflicts"][0]["current_sha256"] == tx.sha(source)
