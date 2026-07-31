#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Event cooldown mechanism tests (P2-⑦)."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "draft_packets.py")

_spec = importlib.util.spec_from_file_location("draft_packets", SCRIPT)
dp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dp)


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


class EventCooldownTest(unittest.TestCase):

    def test_detect_conflict_payoff(self):
        hits = dp.detect_event_types("主角打脸反派后碾压全场，反杀宿敌爆锤对手")
        self.assertTrue(hits.get("conflict_payoff"))

    def test_detect_character_bond(self):
        hits = dp.detect_event_types("两人并肩作战后互诉衷肠，建立深厚羁绊")
        self.assertTrue(hits.get("character_bond"))

    def test_detect_world_flavor(self):
        hits = dp.detect_event_types("主角来到传说中古地遗迹，秘境深处异象频现")
        self.assertTrue(hits.get("world_flavor"))

    def test_detect_crisis_escalation(self):
        hits = dp.detect_event_types("死局降临，绝境中的陷阱形成计中计，风暴将至")
        self.assertTrue(hits.get("crisis_escalation"))

    def test_detect_faction_management(self):
        hits = dp.detect_event_types("主角整合势力，门派联盟博弈站队，暗棋布局")
        self.assertTrue(hits.get("faction_management"))

    def test_empty_text_no_hits(self):
        hits = dp.detect_event_types("")
        self.assertEqual(hits, {})

    def test_no_false_positives(self):
        hits = dp.detect_event_types("主角走在街上买了碗面吃")
        self.assertFalse(any(hits.values()))


class EventCoolingSectionTest(unittest.TestCase):

    def test_first_chapter_no_warnings(self):
        with tempfile.TemporaryDirectory() as root:
            section, tracker = dp.event_cooldown_section(root, 1, "主角打脸反派复仇横扫")
            self.assertEqual(section, "")  # 首章无冷却违规
            self.assertIn(1, tracker["events"][0].values())

    def test_cooldown_violation_detected(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "设定"), exist_ok=True)
            # 第 1 章：冲突爽点 — 需要持久化 tracker 才能在第 2 章检测冷却
            _, tracker1 = dp.event_cooldown_section(root, 1, "主角打脸虐菜反杀")
            _write_json(os.path.join(root, dp.EVENT_COOLDOWN_PATH), tracker1)
            # 第 2 章：又是冲突爽点 — 违反冷却（冷却 2 章）
            section, tracker2 = dp.event_cooldown_section(root, 2, "大战反杀爆锤")
            self.assertIn("⚠️", section)
            self.assertIn("冲突爽点", section)

    def test_missing_bond_reminder(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "设定"), exist_ok=True)
            for ch in range(1, 9):
                _, tr = dp.event_cooldown_section(root, ch, f"第{ch}章战斗打斗反杀虐菜")
                _write_json(os.path.join(root, dp.EVENT_COOLDOWN_PATH), tr)
            # 第 9 章仍无羁绊（第 1 章以来 9 章未出现）
            section, tracker = dp.event_cooldown_section(root, 9, "终极大战决战")
            self.assertIn("💡", section)
            self.assertIn("人物羁绊", section)

    def test_bond_resets_reminder(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "设定"), exist_ok=True)
            _, tr = dp.event_cooldown_section(root, 1, "打斗秒杀")
            _write_json(os.path.join(root, dp.EVENT_COOLDOWN_PATH), tr)
            _, tr = dp.event_cooldown_section(root, 3, "并肩守护建立深深羁绊")  # 第 3 章有羁绊
            _write_json(os.path.join(root, dp.EVENT_COOLDOWN_PATH), tr)
            # 第 4-7 章无羁绊
            for ch in range(4, 8):
                _, tr = dp.event_cooldown_section(root, ch, "打斗战斗")
                _write_json(os.path.join(root, dp.EVENT_COOLDOWN_PATH), tr)
            section, _ = dp.event_cooldown_section(root, 8, "又是大战")
            # 从第 3 章算起 gap = 8-3 = 5 >= 5
            self.assertIn("💡", section)

    def test_tracker_saved(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "设定"))
            section, tracker = dp.event_cooldown_section(root, 1, "主角打脸反杀，走进市井茶楼听说秘境传说")
            self.assertIn("events", tracker)
            self.assertGreaterEqual(len(tracker["events"]), 2)  # conflict_payoff + world_flavor
            self.assertIn(1, tracker["last_seen"].values())


if __name__ == "__main__":
    unittest.main()
