# -*- coding: utf-8 -*-
import json
import os
import sys
import zipfile

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import import_novel as importer  # noqa: E402


def parse_args(argv):
    return importer.build_arg_parser().parse_args(argv)


def write_minimal_docx(path, paragraphs):
    body = "".join(
        "<w:p><w:r><w:t>{}</w:t></w:r></w:p>".format(p)
        for p in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", document)


def test_sanitize_title_removes_extension_noise():
    assert importer.sanitize_title("  冷宫有妖气_全本.txt  ") == "冷宫有妖气"
    assert importer.sanitize_title("a/b/看花胖子，藏到了飞升.docx") == "看花胖子，藏到了飞升"
    assert importer.sanitize_title("坏/名字:*?<>|.txt") == "名字"


def test_import_txt_creates_project_with_manifest(tmp_path):
    src = tmp_path / "原作_全本.txt"
    src.write_text("# 隐秘书名\n\n第1章 开端\n\n正文。", encoding="utf-8")
    out_root = tmp_path / "写小说"
    args = parse_args([
        str(src),
        "--out-root", str(out_root),
        "--prefer-content-title",
        "--i-have-rights",
    ])

    result = importer.import_novel(str(src), args)

    project = out_root / "隐秘书名"
    assert result["target_root"] == str(project)
    assert (project / "原作.txt").exists()
    assert (project / "小说" / "隐秘书名.txt").exists()
    manifest = json.loads((project / "小说" / "source_manifest.json").read_text(encoding="utf-8"))
    assert manifest["title"] == "隐秘书名"
    assert manifest["source_type"] == "local_txt"
    assert manifest["rights_status"] == "user-declared"
    meta = json.loads((project / "_meta.json").read_text(encoding="utf-8"))
    assert meta["kind"] == "import"
    assert meta["source"] == "原作.txt"


def test_import_docx_uses_stdlib_extractor(tmp_path):
    src = tmp_path / "测试文档.docx"
    write_minimal_docx(src, ["文档里的书名", "第一段正文。"])
    out_root = tmp_path / "写小说"
    args = parse_args([
        str(src),
        "--out-root", str(out_root),
        "--prefer-content-title",
        "--i-have-rights",
    ])

    importer.import_novel(str(src), args)

    project = out_root / "文档里的书名"
    assert "第一段正文。" in (project / "原作.txt").read_text(encoding="utf-8")
    assert (project / "小说" / "文档里的书名.docx").exists()
    manifest = json.loads((project / "小说" / "source_manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_type"] == "local_docx"


def test_existing_new_version_creates_numbered_project(tmp_path):
    src = tmp_path / "重名书.txt"
    src.write_text("第1章\n\n正文。", encoding="utf-8")
    out_root = tmp_path / "写小说"
    (out_root / "重名书").mkdir(parents=True)
    args = parse_args([
        str(src),
        "--out-root", str(out_root),
        "--on-exists", "new-version",
        "--i-have-rights",
    ])

    result = importer.import_novel(str(src), args)

    assert result["action"] == "new-version"
    assert result["target_root"].endswith("重名书-2")
    assert (out_root / "重名书-2" / "原作.txt").exists()


def test_existing_ask_in_noninteractive_errors(tmp_path):
    src = tmp_path / "重名书.txt"
    src.write_text("正文。", encoding="utf-8")
    out_root = tmp_path / "写小说"
    (out_root / "重名书").mkdir(parents=True)
    args = parse_args([str(src), "--out-root", str(out_root), "--i-have-rights"])

    with pytest.raises(importer.ImportErrorWithCode) as exc:
        importer.import_novel(str(src), args)
    assert exc.value.code == 3
    assert "非交互环境不会自动覆盖" in str(exc.value)


def test_generic_url_requires_rights_before_network():
    args = parse_args(["https://example.com/book.txt"])
    with pytest.raises(importer.ImportErrorWithCode) as exc:
        importer.collect_payload("https://example.com/book.txt", args)
    assert exc.value.code == 3
    assert "--i-have-rights" in str(exc.value)
