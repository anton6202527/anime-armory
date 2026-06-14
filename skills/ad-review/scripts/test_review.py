#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest

import review


class ReviewTest(unittest.TestCase):
    def _write_json(self, root, rel, payload):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _base(self, root):
        os.makedirs(os.path.join(root, "合成"), exist_ok=True)
        open(os.path.join(root, "合成", "成片_主片.mp4"), "wb").close()
        self._write_json(root, "脚本/广告法机检报告.json", {"summary": {"block": 0, "warn": 0}})
        self._write_json(root, "配音/时长清单.json", {"has_placeholder": False})
        self._write_json(root, "合规/ai_usage.json", {"visual_mode": "AI-generated"})
        with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
            f.write("""## 交付版本矩阵
| 交付件 | 时长 | 比例 | 类型 | 交付规格 | 状态 | 成片路径 |
|---|---|---|---|---|---|---|
| 主片 | 30s | 16:9 | master | 平台默认 | ✅ | 合成/成片_主片.mp4 |
""")

    def test_review_passes_base(self):
        with tempfile.TemporaryDirectory() as root:
            self._base(root)
            payload = review.review(root)
            self.assertEqual(payload["summary"]["block"], 0)

    def test_review_blocks_placeholder(self):
        with tempfile.TemporaryDirectory() as root:
            self._base(root)
            self._write_json(root, "配音/时长清单.json", {"has_placeholder": True})
            payload = review.review(root)
            self.assertTrue(any(f["code"] == "voice_placeholder" for f in payload["findings"]))

    def test_review_blocks_missing_ai_usage(self):
        with tempfile.TemporaryDirectory() as root:
            self._base(root)
            os.remove(os.path.join(root, "合规", "ai_usage.json"))
            payload = review.review(root)
            self.assertTrue(any(f["code"] == "ai_usage_missing" for f in payload["findings"]))


if __name__ == "__main__":
    unittest.main()
