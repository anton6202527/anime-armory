# -*- coding: utf-8 -*-
"""生成次数预算（generation_budget）单测。

盯：① 逐镜预算账（首帧+尾帧+视频）；② 相邻同场景合并候选链（endcard 断链、超上限断链）；
③ 预算线 warn；advisory 底线 summary.block 恒 0。
"""
import json

import generation_budget as gb


def _write_storyboard(root, shots):
    path = root / "脚本" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"shots": shots}, ensure_ascii=False), encoding="utf-8")


def test_missing_storyboard_degrades(tmp_path):
    report = gb.build(tmp_path)
    assert report["available"] is False and report["summary"]["block"] == 0


def test_budget_counts_end_frames(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "C01", "scene": "厨房", "duration": 4, "continuity": {"need_end_frame": True}},
        {"shot_id": "C02", "scene": "厨房", "duration": 4},
    ])
    report = gb.build(tmp_path)
    assert report["totals"] == {"image": 3, "video": 2, "total": 5}


def test_adjacent_same_scene_merge_chain(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "C01", "scene": "厨房", "duration": 4},
        {"shot_id": "C02", "scene": "厨房", "duration": 4},
        {"shot_id": "C03", "scene": "客厅", "duration": 4},
    ])
    report = gb.build(tmp_path)
    assert report["merge_chains"] == [["C01", "C02"]]
    assert any(f["code"] == "merge_candidates_available" for f in report["findings"])


def test_merge_chain_respects_ceiling_and_endcard(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "C01", "scene": "厨房", "duration": 6},
        {"shot_id": "C02", "scene": "厨房", "duration": 6},        # 6+6 > 10s 上限 → 断链
        {"shot_id": "C03", "scene": "尾板", "duration": 2, "endcard": True},
        {"shot_id": "C04", "scene": "尾板", "duration": 2},        # endcard 豁免断链
    ])
    report = gb.build(tmp_path)
    assert report["merge_chains"] == []


def test_missing_duration_not_merged(tmp_path):
    _write_storyboard(tmp_path, [
        {"shot_id": "C01", "scene": "厨房"},
        {"shot_id": "C02", "scene": "厨房"},
    ])
    report = gb.build(tmp_path)
    assert report["merge_chains"] == []   # 时长缺失不可判断链（宁缺毋滥）


def test_budget_over_line_warns(tmp_path, monkeypatch):
    monkeypatch.setattr(gb, "ENV_MAX_GEN", "3")
    _write_storyboard(tmp_path, [
        {"shot_id": "C01", "scene": "厨房", "duration": 4, "continuity": {"need_end_frame": True}},
        {"shot_id": "C02", "scene": "客厅", "duration": 4},
    ])
    report = gb.build(tmp_path)
    assert any(f["code"] == "budget_over_line" and f["severity"] == "warn" for f in report["findings"])
    assert report["summary"]["block"] == 0
