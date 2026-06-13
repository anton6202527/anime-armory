#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest

import contract
import gate
import progress_set


class ProgressSetTest(unittest.TestCase):
    def test_set_stage_text(self):
        md = contract.progress_markdown("测试广告")
        out = progress_set.set_stage_text(md, "script", "✅", "脚本/广告脚本.md", "0 block", "脚本完成")
        self.assertIn("| 广告脚本+VO+时间轴 | ✅ | 脚本/广告脚本.md | 0 block |", out)
        self.assertIn("脚本完成", out)

    def test_set_deliverable_text(self):
        md = contract.progress_markdown("测试广告")
        out = progress_set.set_deliverable_text(md, "cut_15s", "✅", "合成/cutdown/成片_15s.mp4")
        self.assertIn("| cutdown 15s | 15s | 16:9 | cutdown | 平台默认 | ✅ | 合成/cutdown/成片_15s.mp4 |", out)


class GateTest(unittest.TestCase):
    def _write_json(self, root, rel, payload):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _base_project(self, root):
        self._write_json(root, "需求/brief.json", {
            "brand": "山岚",
            "product": "手冲咖啡",
            "usp": ["48小时内烘焙"],
            "audience": "都市白领",
            "claims": ["48小时内烘焙（有据）"],
            "rights": {"talent": "未使用真人", "music": "授权曲库", "fonts": "思源黑体", "assets": "自有素材"},
            "mandatories": {"legal_lines": ["广告"]},
        })
        self._write_json(root, "脚本/广告法机检报告.json", {"summary": {"block": 0, "warn": 0}})
        self._write_json(root, "脚本/storyboard.json", {"shots": [{"shot_id": "S1", "duration": 3}]})
        self._write_json(root, "脚本/镜头时长.json", {"findings": []})
        self._write_json(root, "配音/时长清单.json", {"has_placeholder": False, "lines": []})

    def test_image_gate_passes_base_project(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            payload = gate.run_gate(root, "image")
            self.assertEqual(payload["summary"]["block"], 0)

    def test_gate_blocks_deferred_brief(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            self._write_json(root, "需求/brief.json", {
                "brand": "山岚", "product": "咖啡", "usp": ["现磨"], "audience": "白领",
                "claims": ["待补"], "rights": {"talent": "未使用真人", "music": "待补", "fonts": "待补", "assets": "待补"},
                "mandatories": {"legal_lines": ["待补"]},
            })
            payload = gate.run_gate(root, "image")
            self.assertGreater(payload["summary"]["block"], 0)
            self.assertTrue(any(f["code"] == "brief_deferred_missing" for f in payload["findings"]))

    def test_compose_blocks_placeholder_voice(self):
        with tempfile.TemporaryDirectory() as root:
            self._base_project(root)
            self._write_json(root, "配音/时长清单.json", {"has_placeholder": True, "lines": []})
            os.makedirs(os.path.join(root, "出图", "分镜"), exist_ok=True)
            open(os.path.join(root, "出图", "分镜", "镜头1.png"), "wb").close()
            os.makedirs(os.path.join(root, "出视频", "分镜", "视频"), exist_ok=True)
            open(os.path.join(root, "出视频", "分镜", "视频", "clip_01.mp4"), "wb").close()
            payload = gate.run_gate(root, "compose")
            self.assertTrue(any(f["code"] == "voice_placeholder" and f["severity"] == "block" for f in payload["findings"]))


if __name__ == "__main__":
    unittest.main()
