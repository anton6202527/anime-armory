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


def _write_profile(root, profile=None, platform=None):
    lines = ["# 设置"]
    if profile:
        lines.append(f"- 创作工艺档：{profile}")
    if platform:
        lines.append(f"- 目标平台：{platform}")
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_profile_scene(root, **fields):
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    scene = {"id": "S1", "chapter": 1, "scene_no": 1}
    scene.update(fields)
    with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "novel_scene_cards", "scenes": [scene]}, f, ensure_ascii=False)


def test_literary_map_accepts_revelation_without_turn_or_value_shift(tmp_path):
    root = str(tmp_path)
    _write_profile(root, profile="literary")
    _write_profile_scene(
        root,
        viewpoint="贴近女儿的限知叙述",
        revelation="读者终于看见旧照片被裁掉的人",
    )

    report = manuscript_map.build_map(root)
    check = manuscript_map.check_map(report)

    assert report["craft_profile"] == "literary"
    assert report["chapters"][0]["narrative_functions"] == ["revelation"]
    assert check["passed"] is True
    assert not any(item["id"].endswith("TURN-MISSING") for item in check["findings"])


def test_experimental_map_accepts_deliberate_stasis(tmp_path):
    root = str(tmp_path)
    _write_profile(root, profile="experimental")
    _write_profile_scene(
        root,
        deliberate_stasis="重复等车让读者体会制度性停滞，下一章的离开因此有重量",
    )

    check = manuscript_map.check_map(manuscript_map.build_map(root))

    assert check["passed"] is True
    assert check["blocking"] == 0


def test_literary_map_missing_all_functions_warns_without_blocking(tmp_path):
    root = str(tmp_path)
    _write_profile(root, profile="literary")
    _write_profile_scene(root, viewpoint="合唱式村庄视点")

    check = manuscript_map.check_map(manuscript_map.build_map(root))

    finding = next(
        item for item in check["findings"]
        if item["id"] == "MANUSCRIPT-MAP-NARRATIVE-FUNCTION-MISSING"
    )
    assert check["passed"] is True
    assert check["blocking"] == 0
    assert finding["severity"] == "warning"
    assert finding["confidence"] == "heuristic"


def test_literary_map_requires_attributable_pov_or_viewpoint(tmp_path):
    root = str(tmp_path)
    _write_profile(root, profile="literary")
    _write_profile_scene(root, motif_return="同一只空碗第三次出现")

    check = manuscript_map.check_map(manuscript_map.build_map(root))

    assert check["passed"] is False
    finding = next(
        item for item in check["findings"]
        if item["id"] == "MANUSCRIPT-MAP-VIEWPOINT-MISSING"
    )
    assert finding["severity"] == "blocking"
    assert finding["confidence"] == "contract"


def test_literary_map_requires_attribution_for_each_scene(tmp_path):
    root = str(tmp_path)
    _write_profile(root, profile="literary")
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump({
            "kind": "novel_scene_cards",
            "scenes": [
                {"id": "S1", "chapter": 1, "scene_no": 1, "viewpoint": "祖母", "motif_return": "旧钟"},
                {"id": "S2", "chapter": 1, "scene_no": 2, "deliberate_stasis": "空房间保持不变"},
            ],
        }, f, ensure_ascii=False)

    report = manuscript_map.build_map(root)
    check = manuscript_map.check_map(report)

    assert report["chapters"][0]["unattributed_scene_ids"] == ["S2"]
    finding = next(item for item in check["findings"] if item["id"] == "MANUSCRIPT-MAP-VIEWPOINT-MISSING")
    assert "S2" in finding["message"]
    assert check["passed"] is False


def test_manuscript_map_check_is_stale_after_profile_change(tmp_path):
    root = str(tmp_path)
    _write_profile(root, profile="genre_novel")
    _write_profile_scene(
        root,
        pov="阿遥",
        desire="离开",
        obstacle="封锁",
        conflict="争执",
        turn="门开了",
        value_shift="困住到可走",
    )
    report = manuscript_map.build_map(root)
    assert manuscript_map.check_map(report)["passed"] is True

    _write_profile(root, profile="literary")
    check = manuscript_map.check_map(report)

    assert check["passed"] is False
    assert check["source_fresh"] is False
    stale = next(item for item in check["findings"] if item["id"] == "MANUSCRIPT-MAP-SOURCE-STALE")
    assert "craft_profile_changed" in stale["message"]


def test_manuscript_map_check_stays_fresh_after_unrelated_platform_change(tmp_path):
    root = str(tmp_path)
    _write_profile(root, profile="literary", platform="跨平台")
    _write_profile_scene(root, viewpoint="无名旁观者", revelation="门牌号码从未存在")
    report = manuscript_map.build_map(root)
    assert manuscript_map.check_map(report)["passed"] is True

    _write_profile(root, profile="literary", platform="晋江")
    check = manuscript_map.check_map(report)

    assert check["source_fresh"] is True
    assert check["passed"] is True
    assert not any(item["id"] == "MANUSCRIPT-MAP-SOURCE-STALE" for item in check["findings"])


def test_manuscript_map_check_is_stale_after_scene_cards_change(tmp_path):
    root = str(tmp_path)
    _write_profile(root, profile="experimental")
    _write_profile_scene(root, deliberate_stasis="等待没有结果")
    report = manuscript_map.build_map(root)
    assert manuscript_map.check_map(report)["passed"] is True

    _write_profile_scene(root, perceptual_shift="钟声忽然不再来自塔楼")
    check = manuscript_map.check_map(report)

    assert check["passed"] is False
    assert check["source_fresh"] is False
    stale = next(item for item in check["findings"] if item["id"] == "MANUSCRIPT-MAP-SOURCE-STALE")
    assert "scene_cards_changed" in stale["message"]


def test_target_platform_does_not_select_literary_profile(tmp_path):
    root = str(tmp_path)
    _write_profile(root, platform="晋江")
    _write_profile_scene(root, revelation="只登记了揭示")

    report = manuscript_map.build_map(root)
    check = manuscript_map.check_map(report)

    assert report["craft_profile"] == "genre_novel"
    assert check["passed"] is False
    ids = {item["id"] for item in check["findings"]}
    assert "MANUSCRIPT-MAP-TURN-MISSING" in ids
    assert "MANUSCRIPT-MAP-VALUE-SHIFT-MISSING" in ids


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


# ── 第五轮：场景落地 / 巧合救场 / 正犯不避 ──────────────────────────────────

def test_grounding_dropped_flagged_and_honored(tmp_path):
    import json, os
    import manuscript_map as mm
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
        f.write("有人在黑暗里数着更声，一声比一声近。" * 10)
    scenes = [_scene(1, 1, pov="沈砚", location="城南义庄", time="三日后")]
    alerts = mm.detect_grounding_dropped(root, scenes)
    assert len(alerts) == 1 and alerts[0]["type"] == "SCENE-GROUNDING-DROPPED"
    # 章首出现地点锚 → 已落地不报
    with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
        f.write("义庄的门板吱呀一响。有人在黑暗里数着更声。" * 10)
    assert mm.detect_grounding_dropped(root, scenes) == []


def test_grounding_skipped_without_fields(tmp_path):
    import manuscript_map as mm
    # pov/location 未填 → 无从对账，跳过
    assert mm.detect_grounding_dropped(str(tmp_path), [_scene(1, 1, pov="", location="")]) == []


def test_coincidence_rescue_only_favorable():
    import manuscript_map as mm
    scenes = [
        _scene(3, 1, turn_source="巧合", outcome="yes"),      # 巧合捞人 → 报
        _scene(4, 1, turn_source="巧合", outcome="no-and"),   # 巧合推人进麻烦 → 合法
        _scene(5, 1, turn_source="主角行动", outcome="yes"),  # 自己挣的 → 合法
    ]
    alerts = mm.detect_coincidence_rescue(scenes)
    assert len(alerts) == 1 and alerts[0]["chapter"] == 3
    assert alerts[0]["type"] == "TURN-COINCIDENCE-RESCUE"


def test_repeat_no_variation_detection():
    import manuscript_map as mm
    a = _scene(2, 1, pov="沈砚", location="演武场", outcome="yes-but",
               desire="在比试中赢下对手证明自己", obstacle="对手境界高出一阶")
    b = _scene(9, 1, pov="沈砚", location="演武场", outcome="yes-but",
               desire="在比试中赢下对手证明自己", obstacle="对手境界高出一阶")
    alerts = mm.detect_repeat_no_variation([a, b])
    assert len(alerts) == 1 and alerts[0]["type"] == "SCENE-REPEAT-NO-VARIATION"
    # 换了地点（一个维度已变）→ 不报
    b2 = dict(b, location="生死台")
    assert mm.detect_repeat_no_variation([a, b2]) == []
    # 同章两场景不比（正犯法管跨章复写）
    b3 = dict(b, chapter=2)
    assert mm.detect_repeat_no_variation([a, b3]) == []


def test_repeat_no_variation_needs_similar_text():
    import manuscript_map as mm
    a = _scene(2, 1, pov="沈砚", location="演武场", outcome="yes-but",
               desire="赢下比试证明自己", obstacle="对手境界更高")
    b = _scene(9, 1, pov="沈砚", location="演武场", outcome="yes-but",
               desire="从看守手里偷出名册", obstacle="巡夜换岗只有一炷香空隙")
    assert mm.detect_repeat_no_variation([a, b]) == []
