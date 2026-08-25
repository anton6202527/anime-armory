from pathlib import Path
import importlib.util


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
    assert tx.verify(tmp_path, "fix-1", "delegate:quality-editor")["status"] == "verified"
    monkeypatch.setattr(tx.subprocess, "run", lambda *a, **k: type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    promoted = tx.promote(tmp_path, "fix-1")
    assert promoted["status"] == "promoted"
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
