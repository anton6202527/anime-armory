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

    def test_ad_law_malformed_blocks(self):
        with tempfile.TemporaryDirectory() as root:
            self._base(root)
            self._write_json(root, "脚本/广告法机检报告.json", {"region": "中国大陆"})  # 无 summary
            payload = review.review(root)
            self.assertTrue(any(f["code"] == "ad_law_malformed" for f in payload["findings"]))

    def test_ad_law_disabled_warns(self):
        with tempfile.TemporaryDirectory() as root:
            self._base(root)
            self._write_json(root, "脚本/广告法机检报告.json", {"region": "海外", "disabled": True})
            payload = review.review(root)
            self.assertFalse(any(f["code"] == "ad_law_block" for f in payload["findings"]))
            self.assertTrue(any(f["code"] == "ad_law_disabled" and f["severity"] == "warn"
                                for f in payload["findings"]))

    def test_ai_usage_talent_mismatch_blocks(self):
        # brief 标注使用真人/代言人，但披露未留授权痕迹 → block 空壳披露。
        with tempfile.TemporaryDirectory() as root:
            self._base(root)
            self._write_json(root, "需求/brief.json", {"rights": {"talent": "王某 肖像授权2026-2027"}})
            self._write_json(root, "合规/ai_usage.json", {"visual_mode": "AI-generated", "talent_status": "未记录"})
            payload = review.review(root)
            self.assertTrue(any(f["code"] == "ai_usage_talent_unrecorded" and f["severity"] == "block"
                                for f in payload["findings"]))

    def test_deliverable_claimed_but_missing_blocks(self):
        with tempfile.TemporaryDirectory() as root:
            self._base(root)
            with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
                f.write("""## 交付版本矩阵
| 交付件 | 时长 | 比例 | 类型 | 交付规格 | 状态 | 成片路径 |
|---|---|---|---|---|---|---|
| 主片 | 30s | 16:9 | master | 平台默认 | ✅ | 合成/成片_主片.mp4 |
| cutdown 15s | 15s | 16:9 | cutdown | 平台默认 | ✅ | 合成/cutdown/成片_15s.mp4 |
""")
            payload = review.review(root)
            self.assertTrue(any(f["code"] == "deliverable_claimed_missing" for f in payload["findings"]))

    def test_deliverable_unrendered_warns(self):
        with tempfile.TemporaryDirectory() as root:
            self._base(root)
            with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
                f.write("""## 交付版本矩阵
| 交付件 | 时长 | 比例 | 类型 | 交付规格 | 状态 | 成片路径 |
|---|---|---|---|---|---|---|
| 主片 | 30s | 16:9 | master | 平台默认 | ✅ | 合成/成片_主片.mp4 |
| cutdown 6s | 6s | 16:9 | cutdown | 平台默认 | ⬜ |  |
""")
            payload = review.review(root)
            self.assertEqual(payload["summary"]["block"], 0)
            self.assertTrue(any(f["code"] == "deliverable_unrendered" and f["severity"] == "warn"
                                for f in payload["findings"]))


if __name__ == "__main__":
    unittest.main()
