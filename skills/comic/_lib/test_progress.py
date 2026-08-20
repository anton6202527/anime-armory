from pathlib import Path

import progress


def test_stage_alias_is_atomic_and_logged(tmp_path: Path) -> None:
    (tmp_path / "_进度.md").write_text(
        "| 话 | 传统收尾 | 审查 |\n|---|---|---|\n| 第1话 | ⬜ | ⬜ |\n",
        encoding="utf-8",
    )
    assert progress.update_stage(tmp_path, "第1话", "原稿收尾", "✅", evidence="receipt.json")
    assert "| 第1话 | ✅ | ⬜ |" in (tmp_path / "_进度.md").read_text(encoding="utf-8")
    ledger = (tmp_path / "生产数据/progress_transitions.jsonl").read_text(encoding="utf-8")
    assert '"evidence": "receipt.json"' in ledger
    assert not progress.update_stage(tmp_path, "第1话", "原稿收尾", "✅")


def test_checklist_update_preserves_other_lines(tmp_path: Path) -> None:
    (tmp_path / "_进度.md").write_text(
        "# 进度\n- [ ] 第1话 页面图\n- [x] 其它\n",
        encoding="utf-8",
    )
    assert progress.update_checklist(tmp_path, {"第1话 页面图": True})
    text = (tmp_path / "_进度.md").read_text(encoding="utf-8")
    assert "- [x] 第1话 页面图" in text
    assert "- [x] 其它" in text
