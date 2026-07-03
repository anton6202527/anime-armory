#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extract_anchors 的纯逻辑单测（章节切分 + 配角锚点粗筛）。

从脚本自身目录跑：
    cd skills/novel-spinoff/scripts && python3 -m pytest test_extract_anchors.py
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_anchors import split_into_chapters, scan_candidates  # noqa: E402


class SplitChaptersTest(unittest.TestCase):
    def test_no_chapter_marker_whole_as_one(self):
        ch = split_into_chapters("正文一段。\n又一段。")
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch[0][0], 1)
        self.assertEqual(ch[0][1], "（全本）")

    def test_splits_on_headings_and_skips_provenance(self):
        text = (
            "# copyright: public-domain\n"
            "# source: gutenberg\n"
            "\n"
            "第一章 启程\n正文A。\n"
            "第二章 风雪\n正文B。\n"
        )
        ch = split_into_chapters(text)
        self.assertEqual([c[0] for c in ch], [1, 2])
        # provenance 头不应混进第一章标题
        self.assertTrue(ch[0][1].startswith("第一章"))
        self.assertIn("正文A", ch[0][2])
        self.assertNotIn("copyright", ch[0][2])
        self.assertIn("正文B", ch[1][2])

    def test_supports_hui_juan_headings(self):
        ch = split_into_chapters("第1回 开篇\n甲。\n第2卷 风起\n乙。")
        self.assertEqual(len(ch), 2)


class ScanCandidatesTest(unittest.TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_finds_hits_and_locates_chapter(self):
        path = self._write("第一章\n张三走来。\n第二章\n无关。\n")
        cands = scan_candidates(path, "张三")
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["source_chapter"], 1)
        self.assertEqual(cands[0]["id"], "C001")
        self.assertIn("张三", cands[0]["excerpt"])

    def test_adjacent_hits_merge_within_window(self):
        # 同章两个紧邻命中应合并为一个候选（hit_count=2）
        path = self._write("第一章\n张三说，然后张三又说。\n")
        cands = scan_candidates(path, "张三")
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["hit_count"], 2)

    def test_distant_hits_do_not_merge(self):
        # 跨越 MERGE_WITHIN 的两个命中应是两个候选
        far = "张三" + ("填" * 400) + "张三"
        path = self._write(f"第一章\n{far}\n")
        cands = scan_candidates(path, "张三")
        self.assertEqual(len(cands), 2)

    def test_absent_character_yields_nothing(self):
        path = self._write("第一章\n这里没有目标。\n")
        self.assertEqual(scan_candidates(path, "李四"), [])


if __name__ == "__main__":
    unittest.main()
