#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漂移护栏：novel/_lib/novel_contract.py 与 novel-craft/scripts/contract.py 是
独立两条 import 路径下的 vendored 契约模块（独立性要求各 skill 可单独打包）。
两份**共享的常量表 + 纯权利计算**必须逐值一致——任何一处改了忘了另一处即判失败，
与 test_scale_contract.py / test_qa_gate_sync.py 同构。

从脚本自身目录跑：
    cd skills/novel-craft/scripts && python3 -m pytest test_contract_sync.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LIB = os.path.join(REPO, "skills", "novel", "_lib")
sys.path.insert(0, HERE)
sys.path.insert(0, LIB)

import contract as craft  # novel-craft/scripts/contract.py
import novel_contract as lib  # novel/_lib/novel_contract.py


# 必须逐值一致的共享常量（任意一份改了都要同步另一份）
SHARED_TABLES = (
    "RIGHTS_STATUS_CANONICAL",
    "REGION_ALIASES",
    "PUBLIC_DOMAIN_LICENSE_URLS",
    "SCALE_PROFILES",
    "SCALE_ALIASES",
    "SCALE_CHOICES",
    "NOVEL_DRAFT_MODES",
    "CHAPTER_GRANULARITY",
    "AI_TEXT_USAGE_MODES",
    "ALLOWED_OUTPUT_FORMATS",
)

# rights_metadata 在两份模块里必须给出逐字段一致的结果（vendored 纯函数）
RIGHTS_CASES = (
    ("original", {}),
    ("public-domain", {}),
    ("public-domain", {"source_type": "gutenberg"}),
    ("public-domain", {"source_type": "wikisource"}),
    ("user-declared", {"rights_declared": True}),
    ("授权", {"distribution_regions": "CN,US"}),
    ("unknown", {}),
)


class ContractSyncTest(unittest.TestCase):
    def test_shared_tables_value_equal(self):
        for name in SHARED_TABLES:
            with self.subTest(table=name):
                self.assertTrue(hasattr(craft, name), f"craft contract 缺 {name}")
                self.assertTrue(hasattr(lib, name), f"novel_contract 缺 {name}")
                self.assertEqual(getattr(craft, name), getattr(lib, name),
                                 f"{name} 在两份契约模块间漂移——请同步")

    def test_rights_metadata_value_equal(self):
        for status, kwargs in RIGHTS_CASES:
            with self.subTest(status=status, kwargs=kwargs):
                self.assertEqual(
                    craft.rights_metadata(status, **kwargs),
                    lib.rights_metadata(status, **kwargs),
                    f"rights_metadata({status!r}, {kwargs}) 两份契约模块结果不一致——请同步",
                )


if __name__ == "__main__":
    unittest.main()
