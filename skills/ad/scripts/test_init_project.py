import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("init_project.py")
    spec = importlib.util.spec_from_file_location("ad_init_project_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


init_project = load_module()


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
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    catalog = json.loads((root / "生产数据" / "artifact_catalog.json").read_text(encoding="utf-8"))
    assert meta["line"] == "ad" and meta["project_id"].startswith("ad_")
    assert catalog["status"] == "bootstrap"
    assert catalog["project"]["project_id"] == meta["project_id"]


def test_existing_legacy_meta_does_not_get_a_mismatched_bootstrap_catalog(tmp_path, monkeypatch):
    root = tmp_path / "legacy-ad"
    root.mkdir()
    (root / "_meta.json").write_text('{"kind":"ad_project","title":"旧广告"}', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["init_project.py", str(root), "--brand", "旧品牌"])
    init_project.main()
    assert not (root / "生产数据" / "artifact_catalog.json").exists()
