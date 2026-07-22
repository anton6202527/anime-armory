#!/usr/bin/env python3
"""Tests for clip_economy_planner.py（集级生成次数预算 + 合并候选·report-only）。"""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import clip_economy_planner as CEP  # noqa: E402


def _mk_storyboard(clips):
    root = Path(tempfile.mkdtemp())
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(
        json.dumps({"clips": clips}, ensure_ascii=False), encoding="utf-8")
    return root


def _clip(i, duration=5.0, **kw):
    clip = {
        "id": f"Clip_{i:02d}", "duration": duration, "scene": "山村小院，夜",
        "location_id": "LOC_yard", "character_ids": ["CHAR_01"],
        "continuity": {"seam_mode": "hard_cut"},
    }
    clip.update(kw)
    return clip


def test_adjacent_same_scene_clips_form_merge_groups_and_reduce_takes():
    root = _mk_storyboard([_clip(i) for i in range(1, 7)])
    plan = CEP.build_plan(root, "第1集")
    assert plan["ok"] is True
    s = plan["summary"]
    # 6×5s → 6 takes；15s 窗口下 3+3 并成 2 组 → 2 takes
    assert s["current_estimated_takes"] == 6
    assert s["merge_groups"] == 2
    assert s["projected_takes_after_merge"] == 2
    assert all(len(g["members"]) == 3 for g in plan["merge_groups"])


def test_high_risk_clip_breaks_chain_and_never_merges():
    clips = [_clip(i) for i in range(1, 5)]
    clips[1]["template"] = "fight_exchange"
    root = _mk_storyboard(clips)
    plan = CEP.build_plan(root, "第1集")
    member_ids = {m for g in plan["merge_groups"] for m in g["members"]}
    assert "Clip_02" not in member_ids
    row = next(r for r in plan["clips"] if r["clip"] == "Clip_02")
    assert row["mergeable"] is False and "安全拆分优先" in row["merge_blocked_reason"]


def test_risk_anchor_chain_clip_never_merges():
    clips = [
        _clip(1),
        _clip(2, continuity={"seam_mode": "hard_cut", "anchors": [
            {"at_sec": 2.0, "use": "keyframe", "reason": "apex: 命中/爆发帧"},
        ]}),
        _clip(3),
    ]
    root = _mk_storyboard(clips)
    plan = CEP.build_plan(root, "第1集")
    member_ids = {m for g in plan["merge_groups"] for m in g["members"]}
    assert "Clip_02" not in member_ids


def test_derived_edit_cut_or_r2_anchors_do_not_block_merge():
    # E1 边界/R2 普通长镜/D0 中锚是派生物：合并后重跑 anchor_planner 会重新规划，不应挡合并
    clips = [
        _clip(1, continuity={"seam_mode": "hard_cut", "anchors": [
            {"at_sec": 2.0, "use": "edit_cut", "reason": "edit_cut: storyboard 镜位切换边界"},
        ]}),
        _clip(2, continuity={"seam_mode": "hard_cut", "anchors": [
            {"at_sec": 2.5, "use": "split", "reason": "auto: R2 普通长镜（10s/3拍）"},
        ]}),
    ]
    root = _mk_storyboard(clips)
    plan = CEP.build_plan(root, "第1集")
    member_ids = {m for g in plan["merge_groups"] for m in g["members"]}
    assert member_ids == {"Clip_01", "Clip_02"}


def test_scene_change_breaks_chain():
    clips = [_clip(1), _clip(2), _clip(3, location_id="LOC_forest"), _clip(4, location_id="LOC_forest")]
    root = _mk_storyboard(clips)
    plan = CEP.build_plan(root, "第1集")
    assert [g["members"] for g in plan["merge_groups"]] == [
        ["Clip_01", "Clip_02"], ["Clip_03", "Clip_04"],
    ]


def test_window_cap_limits_group_span():
    root = _mk_storyboard([_clip(i, duration=7.0) for i in range(1, 4)])
    plan = CEP.build_plan(root, "第1集", max_take_sec=15.0)
    # 7+7=14 ≤ 15，再加 7 超窗 → [1,2] 一组，Clip_03 落单
    assert [g["members"] for g in plan["merge_groups"]] == [["Clip_01", "Clip_02"]]
    assert plan["merge_groups"][0]["combined_sec"] == 14.0


def test_single_take_policy_clip_counts_one_take():
    clip = _clip(
        1, duration=10.0, take_policy="single_take_multishot",
        shots=[
            {"t": [0, 4], "lens": "MS", "desc": "推门"},
            {"t": [4, 7], "lens": "MCU", "desc": "抬头"},
            {"t": [7, 10], "lens": "CU", "desc": "递木牌"},
        ],
    )
    root = _mk_storyboard([clip])
    plan = CEP.build_plan(root, "第1集")
    assert plan["summary"]["current_estimated_takes"] == 1


def test_editorial_shots_without_policy_count_per_shot_takes():
    clip = _clip(
        1, duration=10.0,
        shots=[
            {"t": [0, 4], "lens": "MS", "desc": "推门"},
            {"t": [4, 10], "lens": "CU", "desc": "递木牌"},
        ],
    )
    root = _mk_storyboard([clip])
    plan = CEP.build_plan(root, "第1集")
    assert plan["summary"]["current_estimated_takes"] == 2


def test_findings_are_report_only_heuristic():
    root = _mk_storyboard([_clip(i, duration=4.0) for i in range(1, 12)])
    plan = CEP.build_plan(root, "第1集")
    assert plan["findings"], "过碎密度应产 warn"
    assert all(f["severity"] == "warn" for f in plan["findings"])
    assert all(f.get("confidence") == "heuristic" for f in plan["findings"])


def test_missing_storyboard_warns_not_blocks():
    plan = CEP.build_plan(Path(tempfile.mkdtemp()), "第1集")
    assert plan["ok"] is False
    assert all(f["severity"] == "warn" for f in plan["findings"])


def test_write_outputs(tmp_path=None):
    root = _mk_storyboard([_clip(1), _clip(2)])
    plan = CEP.build_plan(root, "第1集")
    jp, mp = CEP.write_outputs(root, "第1集", plan)
    assert jp.exists() and mp.exists()
    data = json.loads(jp.read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_clip_economy_plan"
    assert "合并候选组" in mp.read_text(encoding="utf-8")


def test_emit_merge_draft_builds_reviewable_fragment():
    root = _mk_storyboard([
        _clip(1, label="推门", shots=[{"t": [0, 5], "lens": "MS", "desc": "推门"}]),
        _clip(2, label="抬头"),
        _clip(3, label="递木牌"),
    ])
    plan = CEP.build_plan(root, "第1集")
    clips, err = CEP.load_storyboard(root, "第1集")
    assert err is None
    draft = CEP.build_merge_draft(clips, plan["merge_groups"], "第1集")
    assert draft["kind"] == "n2d_clip_economy_merge_draft"
    assert draft["status"] == "draft"
    dc = draft["draft_clips"][0]
    assert dc["source_clips"] == ["Clip_01", "Clip_02", "Clip_03"]
    assert dc["take_policy"] == "single_take_multishot"
    assert dc["duration"] == 15.0
    assert [s["t"] for s in dc["shots"]] == [[0.0, 5.0], [5.0, 10.0], [10.0, 15.0]]
    assert dc["shots"][0]["lens"] == "MS"
    assert any("anchor_planner" in item for item in dc["manual_merge_required"])


def test_emit_merge_draft_cli_writes_file():
    root = _mk_storyboard([_clip(1), _clip(2)])
    rc = CEP.main([str(root), "第1集", "--emit-merge-draft", "--json"])
    assert rc == 0
    draft_path = root / "生产数据" / "clip_economy_merge_draft_第1集.json"
    assert draft_path.exists()
    data = json.loads(draft_path.read_text(encoding="utf-8"))
    assert data["draft_clips"][0]["source_clips"] == ["Clip_01", "Clip_02"]


def test_single_take_candidates_cover_editorial_split_clips():
    # 相邻合不动（各 12s 超窗）但内部被编辑镜位强拆的镜 → 补 take_policy 候选
    clips = [
        _clip(1, duration=12.0, shots=[
            {"t": [0, 4], "lens": "MS", "desc": "推门"},
            {"t": [4, 8], "lens": "MCU", "desc": "抬头"},
            {"t": [8, 12], "lens": "CU", "desc": "递木牌"},
        ]),
        _clip(2, duration=12.0, shots=[
            {"t": [0, 6], "lens": "MS", "desc": "接木牌"},
            {"t": [6, 12], "lens": "CU", "desc": "端详"},
        ]),
    ]
    root = _mk_storyboard(clips)
    plan = CEP.build_plan(root, "第1集")
    s = plan["summary"]
    assert s["current_estimated_takes"] == 5  # 3 + 2
    assert s["merge_groups"] == 0             # 12+12 超 15s 窗口
    assert s["single_take_candidates"] == 2
    assert s["projected_takes_after_merge"] == 2  # 各自一次生成
    savings = {c["clip"]: c["saving_takes"] for c in plan["single_take_candidates"]}
    assert savings == {"Clip_01": 2, "Clip_02": 1}


def test_single_take_candidates_skip_high_risk_and_merged_members():
    clips = [
        _clip(1, duration=12.0, template="fight_exchange", shots=[
            {"t": [0, 6], "lens": "MS", "desc": "扑杀"},
            {"t": [6, 12], "lens": "CU", "desc": "命中"},
        ]),
        _clip(2), _clip(3),  # 5+5 → 合并组成员，不重复进单 Clip 候选
    ]
    root = _mk_storyboard(clips)
    plan = CEP.build_plan(root, "第1集")
    assert plan["summary"]["single_take_candidates"] == 0
