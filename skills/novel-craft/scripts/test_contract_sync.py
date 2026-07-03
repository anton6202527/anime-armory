#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单一真值源护栏：novel 家族契约只允许有一份实现（novel/_lib/novel_contract.py）；
novel-craft/scripts/contract.py 必须是薄转发 shim，把 _lib 的公共符号原样再导出，
不得自己再 fork 一份契约（历史上是平行 vendored 模块，2026-06 已收敛）。
另保留若干**显式行为断言**，守护契约关键取值不漂（题材/档位/权利/书名）。

从脚本自身目录跑：
    cd skills/novel-craft/scripts && python3 -m pytest test_contract_sync.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LIB = os.path.join(REPO, "skills", "novel", "_lib")
CRAFT = os.path.join(HERE, "contract.py")
sys.path.insert(0, HERE)
sys.path.insert(0, LIB)

import contract  # novel-craft/scripts/contract.py（应为 shim）

# 消费方真正用到的公共 API：shim 必须把这些都转发过来。
PUBLIC_API = (
    "ALLOWED_OUTPUT_FORMATS", "SCALE_PROFILES", "RIGHTS_STATUS_CANONICAL",
    "base_meta", "derive_title", "parse_outputs", "rights_metadata",
    "scale_profile", "demo_chapters_for", "stage_info", "stage_label",
    "stage_table_for_kind", "create_stage_markdown", "derived_stage_markdown",
    "normalize_novel_purpose", "infer_novel_purpose", "resolve_novel_draft_mode",
)


class ContractSingleSourceTest(unittest.TestCase):
    def test_craft_is_thin_shim(self):
        text = open(CRAFT, encoding="utf-8").read()
        self.assertLess(len(text.splitlines()), 60,
                        "novel-craft/scripts/contract.py 又变胖了——契约逻辑应只在 _lib，这里只转发")
        # 不得自行重新定义契约逻辑（应来自转发）
        for marker in ("def derive_title", "CREATE_STAGE_TABLE = [", "def rights_metadata"):
            self.assertNotIn(marker, text,
                             f"shim 不应自行定义契约（命中 {marker!r}）；应从 novel_contract 转发")

    def test_lib_is_real_source(self):
        lib_text = open(os.path.join(LIB, "novel_contract.py"), encoding="utf-8").read()
        for marker in ("def derive_title", "CREATE_STAGE_TABLE = [", "def rights_metadata"):
            self.assertIn(marker, lib_text, f"单一真值源缺 {marker!r}")

    def test_shim_forwards_public_api(self):
        for name in PUBLIC_API:
            self.assertTrue(hasattr(contract, name), f"shim 缺转发：{name}")


class ContractBehaviorTest(unittest.TestCase):
    """显式取值断言（统一前散在 sync 测试里，保留以防关键契约漂移）。"""

    def test_purpose_inference(self):
        self.assertEqual(contract.normalize_novel_purpose("红果漫剧源书"), "漫剧源书")
        self.assertEqual(contract.normalize_novel_purpose("抖音漫剧源书"), "漫剧源书")
        self.assertEqual(contract.infer_novel_purpose(platform="红果"), "漫剧源书")
        self.assertEqual(contract.infer_novel_purpose(platform="抖音漫剧"), "漫剧源书")

    def test_scale_and_words(self):
        self.assertEqual(contract.scale_for_novel_purpose("漫剧源书"), "漫剧")
        self.assertEqual(contract.scale_for_novel_purpose("微短剧源书"), "微短剧")
        self.assertEqual(contract.words_per_chapter_for_context(purpose="漫剧源书"), [1000, 1500])
        self.assertEqual(contract.words_per_chapter_for_context(purpose="微短剧源书"), [1500, 2500])

    def test_draft_mode_and_workflow(self):
        self.assertEqual(contract.resolve_novel_draft_mode(None, purpose="漫剧源书"), "漫剧源书")
        self.assertEqual(contract.resolve_novel_draft_mode("稳妥初稿", purpose="漫剧源书"), "稳妥初稿")
        self.assertEqual(contract.resolve_novel_draft_workflow(None, scale="long", target_chapters=10), "三步迭代")
        self.assertEqual(contract.resolve_novel_draft_workflow(None, target_chapters=30), "三步迭代")
        self.assertEqual(contract.resolve_novel_draft_workflow("默认单步", scale="long"), "默认单步")

    def test_derive_title_rich(self):
        # 富版：spinoff 带角色名特例 + KIND_SUFFIX
        self.assertEqual(contract.derive_title(
            {"kind": "spinoff", "spinoff_character": "赵狞", "source_title": "原书"}), "原书-赵狞外传")
        self.assertEqual(contract.derive_title({"kind": "condense", "source_title": "原书"}), "原书-精简")
        self.assertEqual(contract.derive_title({"title": "已定名"}), "已定名")

    def test_rights_metadata_keys(self):
        meta = contract.rights_metadata("public-domain", source_type="gutenberg")
        self.assertEqual(meta["rights_status"], "public-domain")
        self.assertTrue(meta["requires_region_rights_review"])


if __name__ == "__main__":
    unittest.main()
