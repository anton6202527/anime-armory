#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Init metadata closure tests for derived novel skills."""
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXPAND_INIT = os.path.join(REPO, "skills", "novel-expand", "scripts", "init_project.py")
CONDENSE_INIT = os.path.join(REPO, "skills", "novel-condense", "scripts", "init_project.py")
CONTINUE_INIT = os.path.join(REPO, "skills", "novel-continue", "scripts", "init_project.py")
SPINOFF_INIT = os.path.join(REPO, "skills", "novel-spinoff", "scripts", "init_project.py")
REWRITE_INIT = os.path.join(REPO, "skills", "novel-rewrite", "scripts", "init_project.py")
CREATE_INIT = os.path.join(REPO, "skills", "novel-create", "scripts", "init_project.py")
DRAFT_PACKETS = os.path.join(HERE, "draft_packets.py")
sys.path.insert(0, HERE)
from contract import demo_chapters_for  # noqa: E402  共享 demo 章数真值源


def write_source(tmp):
    path = os.path.join(tmp, "源书.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# copyright: public-domain\n\n第1章 开端\n\n" + "正文" * 500)
    return path


def write_demo_gate(root):
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(os.path.join(root, "审稿", "demo_gate.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_demo_gate",
            "status": "passed",
            "style_anchor": {},
            "reader_promises": [],
            "setting_constraints": [],
        }, f, ensure_ascii=False)


def assert_next_packet_runs(testcase, root):
    write_demo_gate(root)
    with open(os.path.join(root, "设定", "读者契约.md"), "w", encoding="utf-8") as f:
        f.write("# 读者契约\n核心题旨：测试占位。\n")
    got = subprocess.run(
        [sys.executable, DRAFT_PACKETS, root, "--next"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    testcase.assertEqual(got.returncode, 0, got.stderr)
    testcase.assertTrue(os.path.isdir(os.path.join(root, "写作任务")))


class InitMetadataTest(unittest.TestCase):
    def test_expand_writes_target_chapters_for_draft_packets(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = write_source(tmp)
            root = os.path.join(tmp, "expand")
            subprocess.run(
                [
                    sys.executable, EXPAND_INIT, src,
                    "--out", root,
                    "--target-chapters", "5",
                    "--draft-mode", "商业连载",
                    "--chapter-granularity", "小批",
                    "--ai-text-usage", "AI-assisted",
                ],
                cwd=REPO,
                check=True,
                capture_output=True,
                text=True,
            )
            with open(os.path.join(root, "_meta.json"), encoding="utf-8") as f:
                meta = json.load(f)
            self.assertEqual(meta["target_chapters"], 5)
            self.assertIn("target_words_per_chapter", meta)
            self.assertEqual(meta["draft_mode"], "商业连载")
            self.assertEqual(meta["chapter_granularity"], "小批")
            self.assertEqual(meta["ai_text_usage"], "AI-assisted")
            assert_next_packet_runs(self, root)

    def test_condense_writes_manga_score_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = write_source(tmp)
            root = os.path.join(tmp, "condense")
            subprocess.run(
                [sys.executable, CONDENSE_INIT, src, "--out", root, "--target", "漫剧", "--target-chapters", "5"],
                cwd=REPO,
                check=True,
                capture_output=True,
                text=True,
            )
            with open(os.path.join(root, "_meta.json"), encoding="utf-8") as f:
                meta = json.load(f)
            self.assertEqual(meta["target_chapters"], 5)
            self.assertEqual(meta["target_platform"], "漫剧")
            self.assertEqual(meta["draft_mode"], "漫剧源书")
            self.assertEqual(meta["chapter_granularity"], "逐章")
            self.assertIn("ai_text_usage", meta)
            with open(os.path.join(root, "_设置.md"), encoding="utf-8") as f:
                settings = f.read()
            self.assertIn("小说生成模式**：漫剧源书", settings)
            assert_next_packet_runs(self, root)

    def test_continue_maps_new_chapters_to_target_chapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = write_source(tmp)
            root = os.path.join(tmp, "continue")
            subprocess.run(
                [sys.executable, CONTINUE_INIT, src, "--out", root, "--mode", "sequel", "--new-chapters", "5"],
                cwd=REPO,
                check=True,
                capture_output=True,
                text=True,
            )
            with open(os.path.join(root, "_meta.json"), encoding="utf-8") as f:
                meta = json.load(f)
            self.assertEqual(meta["target_chapters"], 5)
            self.assertIn("target_words_per_chapter", meta)
            self.assertEqual(meta["draft_mode"], "稳妥初稿")
            self.assertEqual(meta["chapter_granularity"], "逐章")
            self.assertIn("ai_text_usage", meta)
            with open(os.path.join(root, "_设置.md"), encoding="utf-8") as f:
                settings = f.read()
            self.assertIn("小说生成模式**：稳妥初稿", settings)
            assert_next_packet_runs(self, root)

    def _meta_demo(self, init_script, src, root, chapter_flag, n, extra=()):
        subprocess.run(
            [sys.executable, init_script, src, "--out", root, chapter_flag, str(n), *extra],
            cwd=REPO, check=True, capture_output=True, text=True,
        )
        with open(os.path.join(root, "_meta.json"), encoding="utf-8") as f:
            return json.load(f)["demo_chapters"]

    def test_demo_chapters_uses_shared_contract(self):
        # 用 helper 与旧公式分叉的值锁住单一真值源：
        #   demo_chapters_for(30)=3（旧 expand/condense min(2,30)=2），demo_chapters_for(3)=0（旧=2 / continue 旧=1）
        self.assertEqual(demo_chapters_for(30), 3)
        self.assertEqual(demo_chapters_for(3), 0)
        with tempfile.TemporaryDirectory() as tmp:
            src = write_source(tmp)
            for name, init in (("expand", EXPAND_INIT), ("condense", CONDENSE_INIT)):
                self.assertEqual(self._meta_demo(init, src, os.path.join(tmp, f"{name}30"), "--target-chapters", 30), 3, name)
                self.assertEqual(self._meta_demo(init, src, os.path.join(tmp, f"{name}03"), "--target-chapters", 3), 0, name)
            self.assertEqual(self._meta_demo(CONTINUE_INIT, src, os.path.join(tmp, "cont30"), "--new-chapters", 30, ("--mode", "sequel")), 3)
            self.assertEqual(self._meta_demo(CONTINUE_INIT, src, os.path.join(tmp, "cont03"), "--new-chapters", 3, ("--mode", "sequel")), 0)

    def test_create_demo_chapters_respects_target_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n, expected in ((3, 0), (30, 3)):
                root = os.path.join(tmp, f"create{n}")
                subprocess.run(
                    [
                        sys.executable, CREATE_INIT,
                        "--title", f"测试新书{n}",
                        "--genre", "玄幻",
                        "--premise", "少年以有代价的雷火术逆转宗门危机",
                        "--scale", "long",
                        "--target-chapters", str(n),
                        "--out", root,
                    ],
                    cwd=REPO,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                with open(os.path.join(root, "_meta.json"), encoding="utf-8") as f:
                    meta = json.load(f)
                self.assertEqual(meta["target_chapters"], n)
                self.assertEqual(meta["demo_chapters"], expected)

    def test_spinoff_writes_generation_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = write_source(tmp)
            root = os.path.join(tmp, "spinoff")
            subprocess.run(
                [
                    sys.executable, SPINOFF_INIT, src,
                    "--character", "王敦",
                    "--mode", "parallel",
                    "--scale", "short",
                    "--target-chapters", "5",
                    "--draft-mode", "商业连载",
                    "--chapter-granularity", "小批",
                    "--ai-text-usage", "AI-assisted",
                    "--out", root,
                ],
                cwd=REPO,
                check=True,
                capture_output=True,
                text=True,
            )
            with open(os.path.join(root, "_meta.json"), encoding="utf-8") as f:
                meta = json.load(f)
            self.assertEqual(meta["target_chapters"], 5)
            self.assertEqual(meta["draft_mode"], "商业连载")
            self.assertEqual(meta["chapter_granularity"], "小批")
            self.assertEqual(meta["ai_text_usage"], "AI-assisted")
            assert_next_packet_runs(self, root)

    def test_rewrite_writes_generation_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = write_source(tmp)
            root = os.path.join(tmp, "rewrite")
            subprocess.run(
                [
                    sys.executable, REWRITE_INIT, src,
                    "--rewrite-type", "换主角并加任务系统",
                    "--scale", "short",
                    "--target-chapters", "5",
                    "--draft-mode", "漫剧源书",
                    "--chapter-granularity", "逐章",
                    "--ai-text-usage", "AI-generated",
                    "--out", root,
                ],
                cwd=REPO,
                check=True,
                capture_output=True,
                text=True,
            )
            with open(os.path.join(root, "_meta.json"), encoding="utf-8") as f:
                meta = json.load(f)
            self.assertEqual(meta["target_chapters"], 5)
            self.assertEqual(meta["draft_mode"], "漫剧源书")
            self.assertEqual(meta["chapter_granularity"], "逐章")
            self.assertEqual(meta["ai_text_usage"], "AI-generated")
            assert_next_packet_runs(self, root)


if __name__ == "__main__":
    unittest.main()
