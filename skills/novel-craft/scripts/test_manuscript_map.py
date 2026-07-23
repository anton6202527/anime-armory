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


def _scene(ch, no, **over):
    s = {"id": f"S{ch}-{no}", "chapter": ch, "scene_no": no}
    s.update(over)
    return s


def test_outcome_yes_run_detection():
    import manuscript_map as mm
    scenes = [_scene(i, 1, outcome="yes") for i in range(1, 5)]
    alerts = mm.detect_outcome_signals(scenes)
    assert any(a["type"] == "OUTCOME-YES-RUN" for a in alerts)
    # 中间一场付了代价（yes-but）→ run 断开，不报
    scenes[2]["outcome"] = "yes-but"
    assert not any(a["type"] == "OUTCOME-YES-RUN"
                   for a in mm.detect_outcome_signals(scenes))


def test_outcome_run_broken_by_unfilled_scene():
    import manuscript_map as mm
    # 3 yes + 1 未填 + 2 yes：未填视为断开（宁漏勿误）→ 只有前段 3 连报
    scenes = ([_scene(i, 1, outcome="yes") for i in range(1, 4)]
              + [_scene(4, 1, outcome="")]
              + [_scene(i, 1, outcome="yes") for i in range(5, 7)])
    alerts = [a for a in mm.detect_outcome_signals(scenes) if a["type"] == "OUTCOME-YES-RUN"]
    assert len(alerts) == 1 and alerts[0]["chapter"] == 1


def test_outcome_skipped_when_fill_rate_low():
    import manuscript_map as mm
    # 10 场只填 3 场（<50%）→ 引擎未启用，整组优雅跳过
    scenes = [_scene(i, 1, outcome="yes" if i <= 3 else "") for i in range(1, 11)]
    assert mm.detect_outcome_signals(scenes) == []


def test_outcome_no_cost_climb_ratio():
    import manuscript_map as mm
    # 12 场已填：9 yes + 3 no-and（75% > 60%）→ 整体无对抗感；穿插排列避免触发 yes-run
    kinds = ["yes", "yes", "no-and"] * 3 + ["yes", "yes", "no-and"]
    scenes = [_scene(i, 1, outcome=k) for i, k in enumerate(kinds[:12], start=1)]
    alerts = mm.detect_outcome_signals(scenes, run_len=99)
    assert any(a["type"] == "OUTCOME-NO-COST-CLIMB" for a in alerts)
    # 样本 <10 → 不算
    assert not any(a["type"] == "OUTCOME-NO-COST-CLIMB"
                   for a in mm.detect_outcome_signals(scenes[:9], run_len=99))


def test_plotline_long_run_detection():
    import manuscript_map as mm
    scenes = [_scene(i, 1, plotline="主线") for i in range(1, 8)]
    alerts = mm.detect_plotline_long_runs(scenes)
    assert len(alerts) == 1 and alerts[0]["type"] == "PLOTLINE-LONG-RUN"
    # 中间插一场支线（横云断山）→ 不报
    scenes[3]["plotline"] = "支线·药铺"
    assert mm.detect_plotline_long_runs(scenes) == []


def test_plotline_skipped_when_fill_rate_low():
    import manuscript_map as mm
    scenes = ([_scene(i, 1, plotline="主线") for i in range(1, 7)]
              + [_scene(i, 1, plotline="") for i in range(7, 14)])
    assert mm.detect_plotline_long_runs(scenes) == []


def _write_progression(root, scores):
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    with open(os.path.join(root, "设定", "emotional_progression.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "novel_emotional_progression",
                   "chapters": [{"chapter": i, "tension_score": s}
                                for i, s in enumerate(scores, start=1)]}, f, ensure_ascii=False)


def test_climax_no_afterwave_detection(tmp_path):
    import manuscript_map as mm
    root = str(tmp_path)
    # 第 5 章是显著峰值（均值+1σ 以上）
    _write_progression(root, [1.0, 1.2, 1.1, 1.3, 9.0, 1.2, 1.0])
    scenes = [
        _scene(5, 1, turn="决战", aftermath=""),           # 峰值章末场景无余波
        _scene(6, 1, conflict="新敌来袭"),                 # 下一章开场即新冲突
    ]
    alerts = mm.detect_climax_no_afterwave(root, scenes)
    assert len(alerts) == 1 and alerts[0]["type"] == "CLIMAX-NO-AFTERWAVE"
    assert alerts[0]["chapter"] == 5
    # 峰值章补了余波 → 不报
    scenes[0]["aftermath"] = "他跪坐在灰烬里，数完了阵亡者的名字。"
    assert mm.detect_climax_no_afterwave(root, scenes) == []


def test_climax_skipped_without_curve_or_flat(tmp_path):
    import manuscript_map as mm
    root = str(tmp_path)
    scenes = [_scene(5, 1), _scene(6, 1, conflict="冲")]
    # 无曲线文件 → 跳过
    assert mm.detect_climax_no_afterwave(root, scenes) == []
    # 曲线太短 → 跳过
    _write_progression(root, [1.0, 9.0])
    assert mm.detect_climax_no_afterwave(root, scenes) == []
    # 曲线全平（无显著峰）→ 跳过
    _write_progression(root, [2.0] * 8)
    assert mm.detect_climax_no_afterwave(root, scenes) == []


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
