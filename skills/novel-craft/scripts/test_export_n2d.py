# -*- coding: utf-8 -*-
"""
test for export.py 的 novel→n2d 交接接缝。
从本目录跑：cd skills/novel-craft/scripts && python3 -m pytest test_export_n2d.py
"""
import json
import os
import export


def test_find_drama_repo_root(tmp_path):
    repo = tmp_path / "repo"
    (repo / "制漫剧").mkdir(parents=True)
    (repo / "写小说" / "我的书").mkdir(parents=True)
    proj = str(repo / "写小说" / "我的书")
    assert export._find_drama_repo_root(proj) == str(repo)


def test_find_drama_repo_root_none(tmp_path):
    proj = tmp_path / "孤儿项目"
    proj.mkdir()
    assert export._find_drama_repo_root(str(proj)) is None


def test_resolve_canonical_dest(tmp_path):
    repo = tmp_path / "repo"
    (repo / "制漫剧").mkdir(parents=True)
    proj = str(repo / "写小说" / "暗河")
    os.makedirs(proj)
    dest, mode = export.resolve_n2d_dest(proj, "暗河", None)
    assert mode == "canonical"
    assert dest == os.path.join(str(repo), "制漫剧", "暗河")


def test_resolve_explicit_dest(tmp_path):
    proj = str(tmp_path / "proj")
    os.makedirs(proj)
    dest, mode = export.resolve_n2d_dest(proj, "暗河", str(tmp_path / "制漫剧" / "别名"))
    assert mode == "explicit"
    assert dest.endswith(os.path.join("制漫剧", "别名"))


def test_resolve_legacy_fallback(tmp_path):
    proj = str(tmp_path / "无制漫剧" / "proj")
    os.makedirs(proj)
    dest, mode = export.resolve_n2d_dest(proj, "暗河", None)
    assert mode == "legacy"
    assert dest.endswith(os.path.join("导出", "n2d-script"))


def test_write_n2d_lays_docx_and_handoff(tmp_path):
    proj = str(tmp_path / "写小说" / "暗河")
    os.makedirs(proj)
    src_docx = tmp_path / "src.docx"
    src_docx.write_bytes(b"PK\x03\x04 fake-docx-bytes")  # 任意文件即可，shutil.copy 不校验
    dest = str(tmp_path / "制漫剧" / "暗河")
    meta = {"source_title": "暗河", "kind": "create", "rights_status": "owned"}

    dest_docx = export.write_n2d(dest, str(src_docx), "暗河", meta, proj)

    # docx 落在 作品根/小说/ 下，split_novel 取其父即得正确作品根
    assert dest_docx == os.path.join(dest, "小说", "暗河.docx")
    assert os.path.isfile(dest_docx)
    assert os.path.basename(os.path.dirname(dest_docx)) == "小说"

    handoff = os.path.join(dest, "小说", "_n2d_handoff.json")
    assert os.path.isfile(handoff)
    ho = json.load(open(handoff, encoding="utf-8"))
    assert ho["title"] == "暗河"
    assert ho["source_novel_project"] == "暗河"
    assert ho["rights_status"] == "owned"
    assert len(ho["docx_sha256"]) == 64  # 真算了 hash
