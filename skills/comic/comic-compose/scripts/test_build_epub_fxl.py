from pathlib import Path
import json
import zipfile

from build_epub_fxl import build


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
