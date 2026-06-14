#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""finalize_storyboard 纯函数单测。
    cd skills/ad-script && python3 test_finalize_storyboard.py
"""
import unittest

import finalize_storyboard as fs


class FinalizeStoryboardTest(unittest.TestCase):
    def test_parse_seconds(self):
        self.assertEqual(fs.parse_seconds("30s"), 30.0)
        self.assertEqual(fs.parse_seconds("15"), 15.0)
        self.assertEqual(fs.parse_seconds("1:30"), 90.0)

    def test_vo_total(self):
        dl = [{"时长": 2.0, "gap_after": 0.5}, {"时长": 3.0, "占位": True}]
        total, ph = fs.vo_total(dl)
        self.assertEqual(total, 5.5)
        self.assertTrue(ph)

    def test_shot_durations(self):
        sb = {"shots": [{"shot_id": "S1", "duration": 5}, {"clip_id": "S2", "时长": 4}]}
        self.assertEqual(fs.shot_durations(sb), [("S1", 5.0), ("S2", 4.0)])

    def test_fit_check_master_mismatch_block(self):
        f = fs.fit_check(30, 20, 0)
        self.assertTrue(any(x["kind"] == "master_duration_mismatch" and x["severity"] == "block" for x in f))

    def test_fit_check_within_tol_ok(self):
        self.assertEqual(fs.fit_check(30, 30.2, 28), [])

    def test_fit_check_vo_overflow_block(self):
        f = fs.fit_check(30, 28, 32)
        self.assertTrue(any(x["kind"] == "vo_overflow" and x["severity"] == "block" for x in f))

    def test_seam_check_warn(self):
        sb = {"shots": [{"continuity": {"need_end_frame": True}}]}
        f = fs.seam_check(sb)
        self.assertTrue(any(x["kind"] == "seam_missing_transition" for x in f))

    # ── 占位：顶层 has_placeholder 为单一真值源 ──────────────────────────
    def test_has_placeholder_top_level_truth(self):
        # 顶层 has_placeholder=True 即占位，即便逐句没标 占位
        dl = {"has_placeholder": True, "lines": [{"seconds": 2.0}]}
        self.assertTrue(fs.has_placeholder(dl))
        _, ph = fs.vo_total(dl)
        self.assertTrue(ph)

    def test_has_placeholder_top_level_false_overrides(self):
        # 顶层显式 False 即权威值，不再回退逐句推断
        dl = {"has_placeholder": False, "lines": [{"seconds": 2.0, "占位": True}]}
        self.assertFalse(fs.has_placeholder(dl))

    def test_has_placeholder_fallback_per_line(self):
        # 顶层缺失时回退逐句 占位
        dl = {"lines": [{"seconds": 2.0, "占位": True}]}
        self.assertTrue(fs.has_placeholder(dl))

    def test_vo_total_seconds_field(self):
        dl = {"has_placeholder": False, "lines": [{"seconds": 2.0}, {"seconds": 3.0}]}
        total, ph = fs.vo_total(dl)
        self.assertEqual(total, 5.0)
        self.assertFalse(ph)

    # ── tol 随主片长度缩放 ──────────────────────────────────────────────
    def test_fit_check_tol_scales_with_master(self):
        # 长片 100s：0.8s 偏差在 max(0.5, 100*0.03)=3.0 容差内 → 不报
        self.assertEqual(fs.fit_check(100, 100.8, 90), [])
        # 短片 10s：tol=max(0.5,0.3)=0.5，0.8s 偏差超容差 → 报
        f = fs.fit_check(10, 10.8, 9)
        self.assertTrue(any(x["kind"] == "master_duration_mismatch" for x in f))

    # ── 单镜 VO 溢出 ──────────────────────────────────────────────────
    def test_shot_vo_overflow(self):
        sb = {"shots": [{"shot_id": "S1", "duration": 3.0, "vo_lines": [1, 2]}]}
        dl = {"lines": [{"idx": 1, "seconds": 2.5}, {"idx": 2, "seconds": 2.0}]}
        f = fs.shot_vo_overflow_check(sb, dl)
        self.assertTrue(any(x["kind"] == "shot_vo_overflow" for x in f))

    def test_shot_vo_no_overflow_when_fits(self):
        sb = {"shots": [{"shot_id": "S1", "duration": 5.0, "vo_lines": [1]}]}
        dl = {"lines": [{"idx": 1, "seconds": 2.5}]}
        self.assertEqual(fs.shot_vo_overflow_check(sb, dl), [])

    # ── 强制项落镜 ──────────────────────────────────────────────────────
    def test_forced_asset_missing_blocks(self):
        brief = {"mandatories": {"logo": True, "slogan": "轻盈一天", "cta": "立即购买",
                                 "legal_lines": ["广告"]}}
        sb = {"shots": [{"shot_id": "S1", "frame": "产品镜", "assets": {"PROD_main": True}}]}
        f = fs.forced_asset_check(brief, sb)
        kinds = [x["kind"] for x in f]
        self.assertTrue(all(k == "forced_asset_missing" for k in kinds))
        self.assertGreaterEqual(len(f), 1)

    def test_forced_asset_covered_ok(self):
        brief = {"mandatories": {"logo": True, "slogan": "轻盈一天", "cta": "立即购买",
                                 "legal_lines": ["广告"]}}
        sb = {"shots": [
            {"shot_id": "S1", "frame": "end card: logo + 轻盈一天", "assets": {"PROD_logo": True}},
            {"shot_id": "S2", "frame": "立即购买", "legal_lines": ["广告"]},
        ]}
        f = fs.forced_asset_check(brief, sb)
        self.assertEqual(f, [])

    def test_forced_asset_deferred_skipped(self):
        # 强制项标"待补"或空 → 本步不拦
        brief = {"mandatories": {"logo": "待补", "legal_lines": []}}
        sb = {"shots": [{"shot_id": "S1", "frame": "x"}]}
        self.assertEqual(fs.forced_asset_check(brief, sb), [])


class FinalizeMainTest(unittest.TestCase):
    """端到端跑 main()：占位硬拦 / --allow-placeholder 放行 / master 缺失 warn。"""

    def _make_project(self, placeholder=True):
        import os
        import json
        import tempfile
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "脚本"))
        os.makedirs(os.path.join(d, "配音"))
        sb = {"master_seconds": 30, "shots": [
            {"shot_id": "S1", "duration": 30.0,
             "continuity": {"transition": "硬切", "need_end_frame": False}},
        ]}
        with open(os.path.join(d, "脚本", "storyboard.json"), "w", encoding="utf-8") as f:
            json.dump(sb, f, ensure_ascii=False)
        dl = {"kind": "say", "has_placeholder": placeholder, "lines": [
            {"idx": 1, "role": "旁白", "text": "x", "seconds": 28.0, "占位": placeholder, "voice_key": "say"},
        ]}
        with open(os.path.join(d, "配音", "时长清单.json"), "w", encoding="utf-8") as f:
            json.dump(dl, f, ensure_ascii=False)
        return d

    def _run(self, root, *extra):
        import os
        import sys
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        cmd = [sys.executable, os.path.join(here, "finalize_storyboard.py"), root,
               "--master", "30s", *extra]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_placeholder_blocks(self):
        d = self._make_project(placeholder=True)
        r = self._run(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("占位", r.stdout)

    def test_allow_placeholder_passes(self):
        d = self._make_project(placeholder=True)
        r = self._run(d, "--allow-placeholder")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_env_allow_placeholder_passes(self):
        import os
        d = self._make_project(placeholder=True)
        here = os.path.dirname(os.path.abspath(__file__))
        import sys
        import subprocess
        env = dict(os.environ, FINALIZE_ALLOW_PLACEHOLDER="1")
        cmd = [sys.executable, os.path.join(here, "finalize_storyboard.py"), d, "--master", "30s"]
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_master_none_warns(self):
        # 不传 --master 且无 _设置.md → master_unspecified warn，但不 block（占位放行后）
        import os
        import sys
        import subprocess
        d = self._make_project(placeholder=False)
        here = os.path.dirname(os.path.abspath(__file__))
        cmd = [sys.executable, os.path.join(here, "finalize_storyboard.py"), d]
        r = subprocess.run(cmd, capture_output=True, text=True)
        self.assertIn("主片目标=未设", r.stdout)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
