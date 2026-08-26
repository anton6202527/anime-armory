from pathlib import Path
import json
import zipfile

import build_epub_fxl
from build_epub_fxl import build, main, write_contract


def test_builds_real_fixed_layout_epub(tmp_path: Path):
    from PIL import Image
    page = tmp_path / "排版" / "第1话" / "pages" / "001.png"; page.parent.mkdir(parents=True)
    Image.new("RGB", (100, 200), "white").save(page)
    manifest = page.parents[1] / "export_manifest.json"
    manifest.write_text(json.dumps({"pages": [{"path": str(page.relative_to(tmp_path)), "size": {"width": 100, "height": 200}}]}), encoding="utf-8")
    epub, pages = build(tmp_path, "第1话", title="Test", language="zh-Hans", alt_map={"page_001": "A reviewed page description"})
    with zipfile.ZipFile(epub) as archive:
        entries = archive.infolist()
        assert entries[0].filename == "mimetype" and entries[0].compress_type == zipfile.ZIP_STORED
        assert b"pre-paginated" in archive.read("EPUB/package.opf")
        assert b'alt="A reviewed page description"' in archive.read("EPUB/pages/page_001.xhtml")
    assert pages[0]["id"] == "page_001"
    first = epub.read_bytes()
    epub2, _ = build(tmp_path, "第1话", title="Test", language="zh-Hans", alt_map={"page_001": "A reviewed page description"})
    assert epub2.read_bytes() == first


def test_semantic_transcript_preserves_panel_and_dialogue_order(tmp_path: Path):
    from PIL import Image
    page = tmp_path / "排版" / "第1话" / "pages" / "001.png"; page.parent.mkdir(parents=True)
    Image.new("RGB", (100, 200), "white").save(page)
    manifest = page.parents[1] / "export_manifest.json"
    manifest.write_text(json.dumps({"pages": [{"path": str(page.relative_to(tmp_path))}]}), encoding="utf-8")
    semantics = {"page_001": {
        "alt": "两格漫画。", "long_description": "角色先观察，再回应。",
        "reading_order": ["P002", "P001"],
        "panels": [
            {"panel_id": "P001", "description": "回应特写", "dialogue": [{"speaker": "乙", "text": "收到"}]},
            {"panel_id": "P002", "description": "观察全景", "dialogue": [{"speaker": "甲", "text": "看那里"}]},
        ],
    }}
    epub, pages = build(tmp_path, "第1话", title="Test", language="zh-Hans", alt_map=semantics)
    with zipfile.ZipFile(epub) as archive:
        body = archive.read("EPUB/pages/page_001.xhtml").decode("utf-8")
        assert body.index("Panel P002") < body.index("Panel P001")
        assert body.index("甲:") < body.index("乙:")
        assert 'aria-describedby="transcript-page_001"' in body
        assert b"longDescription" in archive.read("EPUB/package.opf")
    assert [panel["panel_id"] for panel in pages[0]["semantic"]["panels"]] == ["P002", "P001"]


def test_invalid_semantics_do_not_overwrite_previous_epub(tmp_path: Path):
    from PIL import Image
    page = tmp_path / "排版" / "第1话" / "pages" / "001.png"; page.parent.mkdir(parents=True)
    Image.new("RGB", (100, 200), "white").save(page)
    manifest = page.parents[1] / "export_manifest.json"
    manifest.write_text(json.dumps({"pages": [{"path": str(page.relative_to(tmp_path))}]}), encoding="utf-8")
    epub, _ = build(tmp_path, "第1话", title="Test", language="zh-Hans", alt_map={"page_001": "valid"})
    before = epub.read_bytes()
    import pytest
    with pytest.raises(ValueError, match="duplicate"):
        build(tmp_path, "第1话", title="Test", language="zh-Hans", alt_map={"page_001": {
            "alt": "bad", "panels": [{"panel_id": "P1"}, {"panel_id": "P1"}],
        }})
    assert epub.read_bytes() == before


def test_rtl_layout_sets_spine_page_progression(tmp_path: Path):
    from PIL import Image
    page = tmp_path / "排版" / "第1话" / "pages" / "001.png"; page.parent.mkdir(parents=True)
    Image.new("RGB", (100, 200), "white").save(page)
    manifest = page.parents[1] / "export_manifest.json"
    manifest.write_text(json.dumps({"pages": [{"path": str(page.relative_to(tmp_path))}]}), encoding="utf-8")
    (page.parents[1] / "layout.json").write_text(json.dumps({"reading_direction": "从右到左"}), encoding="utf-8")
    epub, _ = build(tmp_path, "第1话", title="RTL", language="ja", alt_map={"page_001": "右から左"})
    with zipfile.ZipFile(epub) as archive:
        assert b'<spine page-progression-direction="rtl">' in archive.read("EPUB/package.opf")


def test_cli_invalid_attestation_preserves_active_epub_manifest_and_contract(tmp_path: Path):
    from PIL import Image
    page = tmp_path / "排版" / "第1话" / "pages" / "001.png"; page.parent.mkdir(parents=True)
    Image.new("RGB", (100, 200), "white").save(page)
    manifest = page.parents[1] / "export_manifest.json"
    manifest.write_text(json.dumps({"pages": [{"path": str(page.relative_to(tmp_path))}]}), encoding="utf-8")
    epub, pages = build(tmp_path, "第1话", title="Old", language="zh-Hans", alt_map={"page_001": "旧语义"})
    contract = write_contract(tmp_path, "第1话", epub, pages, title="Old", language="zh-Hans", reviewer="accessibility-editor", reason="reviewed")
    alt = tmp_path / "new_alt.json"; alt.write_text(json.dumps({"page_001": "全新语义"}), encoding="utf-8")
    before = {path: path.read_bytes() for path in (epub, manifest, contract)}
    assert main([str(tmp_path), "--chapter", "第1话", "--title", "New", "--alt-json", str(alt), "--reviewer", "delegate:bot", "--reason", "invalid"]) == 2
    assert all(path.read_bytes() == content for path, content in before.items())


def test_accessible_group_promotion_rolls_back_if_manifest_switch_fails(tmp_path: Path, monkeypatch):
    chapter_dir = tmp_path / "排版" / "第1话"; chapter_dir.mkdir(parents=True)
    final_epub = chapter_dir / "accessible" / "第1话.epub"; final_epub.parent.mkdir()
    final_contract = chapter_dir / "accessible_digital_contract.json"
    final_manifest = chapter_dir / "export_manifest.json"
    for path, body in ((final_epub, b"old epub"), (final_contract, b"old contract"), (final_manifest, b"old manifest")):
        path.write_bytes(body)
    stage = chapter_dir / ".accessible_staging_fixture"; stage.mkdir()
    staged_epub = stage / "第1话.epub"; staged_epub.write_bytes(b"new epub")
    staged_contract = stage / "contract.json"; staged_contract.write_bytes(b"new contract")
    staged_manifest = stage / "manifest.json"; staged_manifest.write_bytes(b"new manifest")
    real_replace = build_epub_fxl.os.replace

    def fail_manifest(source, target):
        if Path(source) == staged_manifest and Path(target) == final_manifest:
            raise OSError("injected manifest switch failure")
        return real_replace(source, target)

    monkeypatch.setattr(build_epub_fxl.os, "replace", fail_manifest)
    import pytest
    with pytest.raises(OSError, match="injected"):
        build_epub_fxl._promote_accessible_group(tmp_path, "第1话", stage, [
            (staged_epub, final_epub), (staged_contract, final_contract), (staged_manifest, final_manifest),
        ])
    assert final_epub.read_bytes() == b"old epub"
    assert final_contract.read_bytes() == b"old contract"
    assert final_manifest.read_bytes() == b"old manifest"
    assert not (chapter_dir / ".accessible_promotion.json").exists()
