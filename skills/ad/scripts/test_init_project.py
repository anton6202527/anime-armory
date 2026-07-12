import json
import sys
from pathlib import Path

import init_project


def test_new_project_starts_with_locale_and_accessibility_release_contracts(tmp_path, monkeypatch):
    root = tmp_path / "new-ad"
    monkeypatch.setattr(sys, "argv", ["init_project.py", str(root), "--brand", "星盒"])
    init_project.main()
    brief = json.loads((root / "需求" / "brief.json").read_text(encoding="utf-8"))
    locale = json.loads((root / "合规" / "locale_matrix.json").read_text(encoding="utf-8"))
    assert brief["ai_label_receipts"] == [] and brief["provenance_receipts"] == []
    assert "audio_description" in brief["accessibility"]
    assert locale["deliverable_locales"]
    assert locale["locales"][locale["default_locale"]]["typography_review"]["status"] == "pending"
    assert (root / "生产数据").is_dir() and (root / "投放反馈").is_dir()

