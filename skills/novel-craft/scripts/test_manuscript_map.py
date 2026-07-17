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


def test_analyze_adapts_to_review_detector_contract(tmp_path):
    # review 链适配：结构缺口降 advisory（blocking 语义留给 author_workflow 结构闸）
    import json, os
    import manuscript_map as mm
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "novel_scene_cards", "scenes": [
            {"id": "S1-1", "chapter": 1, "scene_no": 1, "pov": "沈砚",
             "desire": "查案", "obstacle": "官府阻挠", "conflict": "对峙",
             "turn": "", "value_shift": ""},   # 缺 turn/value_shift
        ]}, f, ensure_ascii=False)
    res = mm.analyze(root)
    assert res["ran"] is True and res["blocking"] == 0
    types = {a["type"] for a in res["alerts"]}
    assert "MANUSCRIPT-MAP-TURN-MISSING" in types
    assert all(a["severity"] in ("建议级", "info") for a in res["alerts"])


def test_analyze_skips_without_any_plan(tmp_path):
    import manuscript_map as mm
    res = mm.analyze(str(tmp_path))
    assert res["ran"] is False


def test_sequel_gap_run_detection():
    import manuscript_map as mm
    rows = [{"chapter": i, "scene_count": 1, "turn": "反转", "aftermath": ""} for i in range(1, 5)]
    alerts = mm.detect_sequel_gaps(rows)
    assert len(alerts) == 1 and alerts[0]["type"] == "SEQUEL-GAP-RUN"
    assert alerts[0]["chapters"] == [1, 2, 3, 4]
    # 中间有一章落地拍 → run 被打断，不报
    rows[2]["aftermath"] = "他靠着墙滑坐下去，半晌才做了决定。"
    assert mm.detect_sequel_gaps(rows) == []


def test_dropped_sensory_anchor_flagged_and_honored(tmp_path):
    import json, os
    import manuscript_map as mm
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
        f.write("沈砚推门而入，屋里只有烛火在跳。")
    with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "novel_scene_cards", "scenes": [
            {"id": "S1-1", "chapter": 1, "scene_no": 1, "pov": "沈砚",
             "desire": "查案", "obstacle": "阻", "conflict": "冲", "turn": "转", "value_shift": "变",
             "sensory_anchor": "灶上的药味"},
        ]}, f, ensure_ascii=False)
    res = mm.analyze(root)
    types = [a["type"] for a in res["alerts"]]
    assert "SENSORY-ANCHOR-DROPPED" in types    # 药味没写进正文 → 提示
    # 正文兑现意象 → 不再提示
    with open(os.path.join(root, "章节", "第01章.md"), "a", encoding="utf-8") as f:
        f.write("灶上的药味漫出来。")
    res2 = mm.analyze(root)
    assert "SENSORY-ANCHOR-DROPPED" not in [a["type"] for a in res2["alerts"]]
