#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""import_novel.py 的纯函数单测：书名推断 / 权利状态 / --on-exists 目标解析。

覆盖 773 行导入器里不碰网络、不写盘的可判定逻辑——书名清洗与白名单后缀剥离、
通用名甄别、正文首行取题、HTML <title>/og:title 抽取、编码嗅探、公版/授权权利判定、
以及目标已存在时 new-version / use-existing / overwrite(+force) / ask(非交互) 的分支。

从脚本自身目录跑：
    cd skills/novel/scripts && python3 -m pytest test_import_novel.py
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import import_novel as imp  # noqa: E402


class SanitizeTitleTest(unittest.TestCase):
    def test_strips_import_extension(self):
        self.assertEqual(imp.sanitize_title("时间的针脚.txt"), "时间的针脚")
        self.assertEqual(imp.sanitize_title("book.docx"), "book")

    def test_trailing_marketing_word_is_a_suffix(self):
        # TITLE_SUFFIX_RE 把结尾的「小说」当营销后缀剥掉（如 "某某小说.txt"）
        self.assertEqual(imp.sanitize_title("我的小说.txt"), "我的")

    def test_strips_known_suffixes(self):
        self.assertEqual(imp.sanitize_title("斗破苍穹-全本"), "斗破苍穹")
        self.assertEqual(imp.sanitize_title("凡人修仙传_精校.txt"), "凡人修仙传")
        self.assertEqual(imp.sanitize_title("某书全集完结"), "某书")

    def test_takes_last_path_component(self):
        self.assertEqual(imp.sanitize_title("/books/某某传.txt"), "某某传")
        self.assertEqual(imp.sanitize_title("dir\\子目录\\书名"), "书名")

    def test_illegal_chars_become_dash(self):
        self.assertEqual(imp.sanitize_title("My:Book"), "My-Book")

    def test_html_and_percent_unescape(self):
        self.assertEqual(imp.sanitize_title("A&amp;B"), "A&B")
        self.assertEqual(imp.sanitize_title("%E4%B9%A6"), "书")

    def test_empty_falls_back(self):
        self.assertEqual(imp.sanitize_title(""), "未命名小说")
        self.assertEqual(imp.sanitize_title("   "), "未命名小说")

    def test_length_capped_at_80(self):
        self.assertEqual(len(imp.sanitize_title("书" * 200)), 80)


class StripKnownSuffixesTest(unittest.TestCase):
    def test_repeated_suffixes_all_stripped(self):
        self.assertEqual(imp.strip_known_suffixes("书名全本完结"), "书名")

    def test_no_suffix_unchanged(self):
        self.assertEqual(imp.strip_known_suffixes("书名"), "书名")


class IsGenericTitleTest(unittest.TestCase):
    def test_generic_stems(self):
        for t in ("book", "novel", "未命名", "小说", "正文", ""):
            self.assertTrue(imp.is_generic_title(t), t)

    def test_pure_digits_are_generic(self):
        self.assertTrue(imp.is_generic_title("123"))
        self.assertTrue(imp.is_generic_title("00012"))

    def test_real_title_not_generic(self):
        self.assertFalse(imp.is_generic_title("斗破苍穹"))


class TitleFromUrlPathTest(unittest.TestCase):
    def test_last_segment(self):
        self.assertEqual(imp.title_from_url_path("https://x.com/books/仙逆/"), "仙逆")

    def test_empty_path(self):
        self.assertEqual(imp.title_from_url_path("https://x.com/"), "未命名小说")


class PlausibleContentTitleTest(unittest.TestCase):
    def test_chapter_heading_rejected(self):
        self.assertIsNone(imp.plausible_content_title("第一章 开端"))
        self.assertIsNone(imp.plausible_content_title("第 12 回 风波"))

    def test_metadata_lines_rejected(self):
        self.assertIsNone(imp.plausible_content_title("作者：张三"))
        self.assertIsNone(imp.plausible_content_title("Copyright 2026"))

    def test_too_long_rejected(self):
        self.assertIsNone(imp.plausible_content_title("标" * 41))

    def test_too_much_punctuation_rejected(self):
        self.assertIsNone(imp.plausible_content_title("你好，世界。再见！收尾；"))

    def test_markdown_heading_kept(self):
        self.assertEqual(imp.plausible_content_title("# 山海异闻"), "山海异闻")


class InferTitleFromTextTest(unittest.TestCase):
    def test_non_generic_fallback_wins(self):
        self.assertEqual(
            imp.infer_title_from_text("第一行正文\n", "斗破苍穹"), "斗破苍穹"
        )

    def test_generic_fallback_uses_content(self):
        text = "玄霄列传\n第一章 起\n正文……\n"
        self.assertEqual(imp.infer_title_from_text(text, "download"), "玄霄列传")

    def test_prefer_content_overrides_good_fallback(self):
        text = "真正书名\n正文……\n"
        self.assertEqual(
            imp.infer_title_from_text(text, "占位书名", prefer_content=True),
            "真正书名",
        )

    def test_no_content_candidate_returns_fallback(self):
        text = "第一章 起\n第二章 承\n"
        self.assertEqual(imp.infer_title_from_text(text, "book"), "book")


class ExtractHtmlTitleTest(unittest.TestCase):
    def test_og_title_preferred(self):
        html = '<meta property="og:title" content="天行健"><title>别的</title>'
        self.assertEqual(imp.extract_html_title(html), "天行健")

    def test_title_tag_strips_site_suffix(self):
        self.assertEqual(
            imp.extract_html_title("<title>书名 | 某某书库</title>"), "书名"
        )
        self.assertEqual(
            imp.extract_html_title("<title>书名 - Project Gutenberg</title>"), "书名"
        )

    def test_no_title(self):
        self.assertIsNone(imp.extract_html_title("<p>无标题</p>"))
        self.assertIsNone(imp.extract_html_title(""))


class DecodeBytesTest(unittest.TestCase):
    def test_utf8(self):
        text, enc = imp.decode_bytes("中文测试".encode("utf-8"))
        self.assertEqual(text, "中文测试")
        self.assertIn(enc, {"utf-8", "utf-8-sig"})

    def test_gb18030_fallback(self):
        text, enc = imp.decode_bytes("简体中文".encode("gb18030"))
        self.assertEqual(text, "简体中文")
        self.assertEqual(enc, "gb18030")

    def test_preferred_encoding_first(self):
        text, enc = imp.decode_bytes("中文".encode("gb18030"), preferred="gb18030")
        self.assertEqual((text, enc), ("中文", "gb18030"))


class RightsStatusForTest(unittest.TestCase):
    def test_public_domain_sources(self):
        self.assertEqual(imp.rights_status_for("gutenberg", False), "public-domain")
        self.assertEqual(imp.rights_status_for("wikisource", False), "public-domain")

    def test_declared_rights(self):
        self.assertEqual(imp.rights_status_for("generic", True), "user-declared")

    def test_unknown_without_rights(self):
        self.assertEqual(imp.rights_status_for("generic", False), "unknown")


class NextAvailableRootTest(unittest.TestCase):
    def test_unused_base_returned_as_is(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "书名")
            self.assertEqual(imp.next_available_root(base), base)

    def test_increments_until_free(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "书名")
            os.makedirs(base)
            self.assertEqual(imp.next_available_root(base), base + "-2")
            os.makedirs(base + "-2")
            self.assertEqual(imp.next_available_root(base), base + "-3")


class ResolveTargetRootTest(unittest.TestCase):
    def _existing(self, d, title="测试书"):
        root = os.path.join(d, title)
        os.makedirs(root)
        return root

    def test_create_when_absent(self):
        with tempfile.TemporaryDirectory() as d:
            root, action = imp.resolve_target_root("测试书", d, "ask")
            self.assertEqual(action, "create")
            self.assertEqual(os.path.basename(root), "测试书")

    def test_new_version(self):
        with tempfile.TemporaryDirectory() as d:
            self._existing(d)
            root, action = imp.resolve_target_root("测试书", d, "new-version")
            self.assertEqual(action, "new-version")
            self.assertTrue(root.endswith("测试书-2"))

    def test_use_existing(self):
        with tempfile.TemporaryDirectory() as d:
            existing = self._existing(d)
            root, action = imp.resolve_target_root("测试书", d, "use-existing")
            self.assertEqual((root, action), (existing, "use-existing"))

    def test_overwrite_with_force(self):
        with tempfile.TemporaryDirectory() as d:
            existing = self._existing(d)
            root, action = imp.resolve_target_root(
                "测试书", d, "overwrite", force=True
            )
            self.assertEqual((root, action), (existing, "overwrite"))

    def test_overwrite_without_force_noninteractive_raises(self):
        with tempfile.TemporaryDirectory() as d, _isatty(False):
            self._existing(d)
            with self.assertRaises(imp.ImportErrorWithCode) as cm:
                imp.resolve_target_root("测试书", d, "overwrite", force=False)
            self.assertEqual(cm.exception.code, 3)

    def test_ask_noninteractive_raises(self):
        with tempfile.TemporaryDirectory() as d, _isatty(False):
            self._existing(d)
            with self.assertRaises(imp.ImportErrorWithCode) as cm:
                imp.resolve_target_root("测试书", d, "ask")
            self.assertEqual(cm.exception.code, 3)

    def test_abort(self):
        with tempfile.TemporaryDirectory() as d:
            self._existing(d)
            with self.assertRaises(imp.ImportErrorWithCode) as cm:
                imp.resolve_target_root("测试书", d, "abort")
            self.assertEqual(cm.exception.code, 3)

    def test_ask_interactive_delegates_to_prompt(self):
        # tty=True 时走 prompt_existing；注入 input_func 选 new-version
        with tempfile.TemporaryDirectory() as d, _isatty(True):
            self._existing(d)
            root, action = imp.resolve_target_root(
                "测试书", d, "ask", input_func=_answers(["n"])
            )
            self.assertEqual(action, "new-version")


class PromptExistingTest(unittest.TestCase):
    def test_new(self):
        self.assertEqual(
            imp.prompt_existing("/r", "书", input_func=_answers(["n"])), "new-version"
        )

    def test_use(self):
        self.assertEqual(
            imp.prompt_existing("/r", "书", input_func=_answers(["u"])), "use-existing"
        )

    def test_overwrite_requires_confirm_word(self):
        self.assertEqual(
            imp.prompt_existing("/r", "书", input_func=_answers(["o", "覆盖"])),
            "overwrite",
        )

    def test_overwrite_wrong_confirm_then_abort(self):
        self.assertEqual(
            imp.prompt_existing("/r", "书", input_func=_answers(["o", "no", "a"])),
            "abort",
        )

    def test_empty_answer_aborts(self):
        self.assertEqual(
            imp.prompt_existing("/r", "书", input_func=_answers([""])), "abort"
        )


def _answers(seq):
    it = iter(seq)
    return lambda *_a, **_k: next(it)


def _isatty(value):
    return mock.patch.object(imp.sys.stdin, "isatty", lambda: value)


if __name__ == "__main__":
    unittest.main()
