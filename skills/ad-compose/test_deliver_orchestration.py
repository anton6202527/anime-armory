import json
import sys
from pathlib import Path

import deliver


def _root(tmp_path: Path):
    root = tmp_path / "ad"
    root.mkdir()
    (root / "_设置.md").write_text("- 交付规格: 平台默认\n- 字幕语言: 中文\n", encoding="utf-8")
    (root / "_进度.md").write_text(deliver.contract.progress_markdown("Test", [
        {"deliverable_id": "master", "label": "主片", "duration": "2s", "aspect": "9:16",
         "kind": "master", "spec": "平台默认", "status": "⬜", "path": "合成/成片_主片.mp4"}
    ]), encoding="utf-8")
    (root / "合成").mkdir()
    (root / "合成" / "成片_主片.mp4").write_bytes(b"master")
    return root


def _clean(summary_block=0):
    return {"summary": {"block": summary_block, "warn": 0}}


def test_deliver_writes_current_plan_before_every_downstream_qc(tmp_path, monkeypatch):
    root = _root(tmp_path)

    def delivery_qc(project, plan):
        disk = json.loads((root / "合成" / "delivery_plan.json").read_text(encoding="utf-8"))
        assert disk["deliverables"] == plan["deliverables"]
        return {"items": [{"deliverable_id": "master", "passed": True}], "summary": {"block": 0, "warn": 0}}

    monkeypatch.setattr(deliver.delivery_qc, "build_report", delivery_qc)
    monkeypatch.setattr(deliver.rendered_text_qc, "build", lambda project: _clean())
    monkeypatch.setattr(deliver.asr_consistency, "build", lambda project, run_asr=False: _clean())
    monkeypatch.setattr(deliver.provenance_qc, "build", lambda project: _clean())
    monkeypatch.setattr(deliver.accessibility_qc, "build_report", lambda project, plan: _clean())
    monkeypatch.setattr(sys, "argv", ["deliver.py", str(root), "--mark-existing"])
    assert deliver.main() == 0
    assert "| 主片 | 2s | 9:16 | master | 平台默认 | ✅ | 合成/成片_主片.mp4 |" in (
        root / "_进度.md").read_text(encoding="utf-8")


def test_deliver_does_not_mark_fake_done_when_final_media_qc_blocks(tmp_path, monkeypatch):
    root = _root(tmp_path)
    monkeypatch.setattr(deliver.delivery_qc, "build_report", lambda project, plan: {
        "items": [{"deliverable_id": "master", "passed": True}], "summary": {"block": 0, "warn": 0}})
    monkeypatch.setattr(deliver.rendered_text_qc, "build", lambda project: _clean(1))
    monkeypatch.setattr(deliver.asr_consistency, "build", lambda project, run_asr=False: _clean())
    monkeypatch.setattr(deliver.provenance_qc, "build", lambda project: _clean())
    monkeypatch.setattr(deliver.accessibility_qc, "build_report", lambda project, plan: _clean())
    monkeypatch.setattr(sys, "argv", ["deliver.py", str(root), "--mark-existing"])
    assert deliver.main() == 1
    assert "| 主片 | 2s | 9:16 | master | 平台默认 | ⬜ | 合成/成片_主片.mp4 |" in (
        root / "_进度.md").read_text(encoding="utf-8")

