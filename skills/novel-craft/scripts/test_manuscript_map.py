#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import manuscript_map


def test_manuscript_map_builds_from_scene_cards_and_chapters():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "设定"), exist_ok=True)
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        with open(os.path.join(root, "设定", "章纲.md"), "w", encoding="utf-8") as f:
            f.write("第01章《雨夜》— 主角做出选择\n")
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("正文\n")
        with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
            json.dump({
                "kind": "novel_scene_cards",
                "scenes": [{
                    "id": "SC001-01",
                    "chapter": 1,
                    "scene_no": 1,
                    "pov": "姜月",
                    "desire": "离开宴席",
                    "obstacle": "被当众逼问",
                    "turn": "她公开拒绝婚约",
                    "value_shift": "被动到主动",
                    "reveal_or_payoff": "玉佩发光",
                    "sensory_anchor": "雨声",
                }],
            }, f, ensure_ascii=False)
        report = manuscript_map.build_map(root)
        check = manuscript_map.check_map(report)
        assert report["chapters"][0]["chapter"] == 1
        assert report["chapters"][0]["turn"] == "她公开拒绝婚约"
        assert check["passed"] is True


def test_manuscript_map_blocks_missing_turn_in_scene_card():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "设定"), exist_ok=True)
        with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
            json.dump({"kind": "novel_scene_cards", "scenes": [{"id": "S1", "chapter": 1, "scene_no": 1, "value_shift": "低到高"}]}, f)
        report = manuscript_map.build_map(root)
        check = manuscript_map.check_map(report)
        assert check["passed"] is False
        assert any(item["id"] == "MANUSCRIPT-MAP-TURN-MISSING" for item in check["findings"])
