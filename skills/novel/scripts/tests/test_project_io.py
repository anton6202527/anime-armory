#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
COMMON = os.path.join(REPO, "skills", "novel", "_lib")
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

import project_io  # noqa: E402


def test_read_chapters_sorts_and_filters_range():
    root = tempfile.mkdtemp()
    cdir = os.path.join(root, "章节")
    os.makedirs(cdir)
    for name in ("第10章.md", "第2章.txt", "第1章.md", "_草稿.md"):
        with open(os.path.join(cdir, name), "w", encoding="utf-8") as f:
            f.write(name)

    chapters = project_io.read_chapters(root, "2-10")
    assert [idx for idx, _path, _text in chapters] == [2, 10]
    assert [os.path.basename(path) for _idx, path, _text in chapters] == ["第2章.txt", "第10章.md"]


def test_find_chapter_file_and_label():
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "章节"))
    path = os.path.join(root, "章节", "第03章_雨夜.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("正文")

    assert project_io.chapter_label(3) == "第03章"
    assert project_io.find_chapter_file(root, 3) == path


def test_load_project_settings_uses_existing_parser():
    root = tempfile.mkdtemp()
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("- **小说生成模式**：商业连载\n- 发行地区：US # comment\n")
    settings = project_io.load_project_settings(root)
    assert settings["小说生成模式"] == "商业连载"
    assert settings["发行地区"] == "US"
