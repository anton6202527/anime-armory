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


# ── 复杂度感知预算 + 片段经济强度档（P3）──

def _mk_with_settings(clips, settings_text):
    root = _mk_storyboard(clips)
    (root / "_设置.md").write_text(settings_text, encoding="utf-8")
    return root


def test_simple_narrative_gets_low_budget():
    # 1 场景 / 1 角色 → simple 档。
    root = _mk_storyboard([_clip(i) for i in range(1, 5)])
    plan = CEP.build_plan(root, "第1集")
    cx = plan["summary"]["complexity"]
    assert cx["class"] == "simple"
    assert plan["summary"]["budget_per_min"] <= 8.0


def test_many_locations_is_complex():
    clips = [_clip(i, location_id=f"LOC_{i}", scene=f"场景{i}") for i in range(1, 7)]
    root = _mk_storyboard(clips)
    cx = CEP.build_plan(root, "第1集")["summary"]["complexity"]
    assert cx["class"] == "complex"
    assert cx["distinct_locations"] >= 4


def test_action_raises_budget_not_complexity_class():
    # 单场景单角色但多打斗镜：仍是 simple 广度，但预算被动作加成抬高。
    clips = [_clip(i) for i in range(1, 6)]
    for j in (1, 2, 3):
        clips[j]["template"] = "fight_exchange"
    cx = CEP.build_plan(_mk_storyboard(clips), "第1集")["summary"]["complexity"]
    assert cx["class"] == "simple"
    assert cx["action_budget_allowance"] > 0


def test_conservative_default_never_blocks():
    # 无 片段经济 设置 → 保守：即便超预算也 should_block=False。
    clips = [_clip(i, duration=5.0) for i in range(1, 13)]  # 密集短镜
    plan = CEP.build_plan(_mk_storyboard(clips), "第1集")
    assert plan["summary"]["economy_mode"].startswith("未设置")
    assert plan["should_block"] is False


def test_tight_mode_blocks_when_over_budget_with_savings():
    # 片段经济=紧凑 + 超预算 + 有可采纳合并 → should_block=True。
    clips = [_clip(i, duration=5.0) for i in range(1, 13)]
    root = _mk_with_settings(clips, "片段经济: 紧凑\n")
    plan = CEP.build_plan(root, "第1集")
    assert plan["summary"]["economy_mode"] == "紧凑"
    assert plan["summary"]["over_budget"] is True
    assert plan["should_block"] is True
    assert any(f["code"] == "generation_density_over_budget" and f["severity"] == "block"
               for f in plan["findings"])


def test_tight_mode_strict_exit_code():
    clips = [_clip(i, duration=5.0) for i in range(1, 13)]
    root = _mk_with_settings(clips, "片段经济: 紧凑\n")
    rc = CEP.main([str(root), "第1集", "--strict", "--json"])
    assert rc == 1
    # 保守档同样输入 → exit 0
    root2 = _mk_storyboard(clips)
    assert CEP.main([str(root2), "第1集", "--strict", "--json"]) == 0


def test_extreme_mode_tightens_budget():
    clips = [_clip(i, duration=8.0) for i in range(1, 5)]
    base = CEP.build_plan(_mk_storyboard(clips), "第1集")["summary"]["budget_per_min"]
    root = _mk_with_settings(clips, "片段经济: 极简\n")
    tight = CEP.build_plan(root, "第1集")["summary"]["budget_per_min"]
    assert tight < base  # 极简收紧一档


# ── 沉没成本口径（2026-07-23）：已生成视频的 Clip 不计省次数、不触发 enforce 阻断 ──

def _touch_video(root, ordinal, name="已生成"):
    d = root / "出视频" / "第1集" / "视频"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"Clip_{ordinal:02d}_{name}_part1.mp4").write_bytes(b"x")


def _multi_shot_clip(i, duration=12.0):
    third = duration / 3.0
    return _clip(i, duration=duration, shots=[
        {"t": [0, third], "lens": "MS 50mm", "desc": "起"},
        {"t": [third, third * 2], "lens": "CU 85mm", "desc": "承"},
        {"t": [third * 2, duration], "lens": "MS 35mm", "desc": "合"},
    ])


def test_generated_clip_excluded_from_single_take_candidates():
    root = _mk_storyboard([_multi_shot_clip(1), _clip(2, duration=9.0, scene="县衙大堂", location_id="LOC_hall")])
    _touch_video(root, 1)
    plan = CEP.build_plan(root, "第1集")
    assert plan["summary"]["sunk_cost_clips"] == 1
    assert all(c["clip"] != "Clip_01" for c in plan["single_take_candidates"])
    codes = {f["code"] for f in plan["findings"]}
    assert "sunk_cost_clips_excluded" in codes
    info = next(f for f in plan["findings"] if f["code"] == "sunk_cost_clips_excluded")
    assert info["severity"] == "info" and "Clip_01" in info["message"]


def test_generated_clip_breaks_merge_chain():
    root = _mk_storyboard([_clip(1), _clip(2), _clip(3)])
    _touch_video(root, 2)
    plan = CEP.build_plan(root, "第1集")
    member_ids = {m for g in plan["merge_groups"] for m in g["members"]}
    assert "Clip_02" not in member_ids


def test_tight_mode_does_not_block_when_only_savings_are_sunk_cost():
    # 密集多 take 但全部已生成 → 无可采纳节省 → 紧凑档不阻断（可执行、不死锁）
    clips = [_multi_shot_clip(i, duration=6.0) for i in range(1, 4)]
    for i, c in enumerate(clips, 1):
        c["scene"] = f"独立场景{i}"
        c["location_id"] = f"LOC_{i}"
        c["character_ids"] = [f"CHAR_{i:02d}", f"CHAR_{i+10:02d}"]
    root = _mk_storyboard(clips)
    (root / "_设置.md").write_text("- 片段经济：紧凑\n", encoding="utf-8")
    for i in range(1, 4):
        _touch_video(root, i)
    plan = CEP.build_plan(root, "第1集")
    assert plan["summary"]["sunk_cost_clips"] == 3
    assert plan["single_take_candidates"] == []
    assert plan["should_block"] is False
    over = [f for f in plan["findings"] if f["code"] == "generation_density_over_budget"]
    assert all(f["severity"] == "warn" for f in over)


def test_tight_mode_still_blocks_when_ungenerated_candidate_exists():
    clips = [_multi_shot_clip(1, duration=6.0), _multi_shot_clip(2, duration=6.0)]
    for i, c in enumerate(clips, 1):
        c["scene"] = f"独立场景{i}"
        c["location_id"] = f"LOC_{i}"
        c["character_ids"] = [f"CHAR_{i:02d}", f"CHAR_{i+10:02d}"]
    root = _mk_storyboard(clips)
    (root / "_设置.md").write_text("- 片段经济：紧凑\n", encoding="utf-8")
    _touch_video(root, 1)  # Clip_02 未生成，仍是可采纳候选
    plan = CEP.build_plan(root, "第1集")
    if plan["summary"]["over_budget"]:
        assert plan["should_block"] is True
    assert any(c["clip"] == "Clip_02" for c in plan["single_take_candidates"])


def test_video_out_field_also_marks_sunk_cost():
    root = _mk_storyboard([_multi_shot_clip(1)])
    rel = "出视频/第1集/视频/自定义名.mp4"
    (root / "出视频" / "第1集" / "视频").mkdir(parents=True, exist_ok=True)
    (root / rel).write_bytes(b"x")
    clips_path = root / "脚本" / "第1集" / "storyboard.json"
    data = json.loads(clips_path.read_text(encoding="utf-8"))
    data["clips"][0]["video_out"] = rel
    clips_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    plan = CEP.build_plan(root, "第1集")
    assert plan["summary"]["sunk_cost_clips"] == 1
    assert plan["single_take_candidates"] == []


def test_clip_count_over_budget_warns_for_simple_narrative():
    # 8 个短 clip、简单叙事（1 场景/1 角色）→ clip 数超预算，但未设 enforce → warn。
    root = _mk_storyboard([_clip(i) for i in range(1, 9)])
    plan = CEP.build_plan(root, "第1集")
    s = plan["summary"]
    assert s["complexity"]["class"] == "simple"
    assert s["clips_over_budget"] is True
    codes = {(f["code"], f["severity"]) for f in plan["findings"]}
    assert ("clip_count_over_budget", "warn") in codes
    assert plan["should_block"] is False  # 保守/未设置不阻断


def test_clip_count_over_budget_blocks_under_enforce_with_savings():
    # 紧凑档 + clip 数超预算 + 有可采纳合并（相邻同景）+ 未生成 → block。
    root = _mk_with_settings([_clip(i) for i in range(1, 9)], "- 片段经济：紧凑\n")
    plan = CEP.build_plan(root, "第1集")
    assert plan["summary"]["clips_over_budget"] is True
    assert plan["summary"]["merge_groups"] >= 1  # savings available
    block_codes = {f["code"] for f in plan["findings"] if f["severity"] == "block"}
    assert "clip_count_over_budget" in block_codes
    assert plan["should_block"] is True


def test_long_clip_forcing_parts_is_flagged():
    # 20s 单 clip 会被拆成多段付费 part → long_clips_force_part_split。
    root = _mk_storyboard([_clip(1, duration=20.0), _clip(2, duration=5.0)])
    plan = CEP.build_plan(root, "第1集")
    assert plan["summary"]["long_clips_forcing_parts"] >= 1
    assert any(f["code"] == "long_clips_force_part_split" for f in plan["findings"])
    assert any(c["clip"] == "Clip_01" for c in plan["long_clips"])


def test_long_clip_flag_excludes_sunk_cost_generated():
    # 已生成的长 clip 是沉没成本，不点名 shorten（不追溯返工）。
    root = _mk_storyboard([_clip(1, duration=20.0), _clip(2, duration=5.0)])
    _touch_video(root, 1)
    plan = CEP.build_plan(root, "第1集")
    assert all(c["clip"] != "Clip_01" for c in plan["long_clips"])


def test_state_suffix_variants_count_as_one_character():
    # "CHAR_01/囚服态" 与 "CHAR_01/制服态" 是同一角色的两个状态，不得数成两人虚抬复杂度。
    clips = [
        _clip(1, character_ids=["CHAR_01/囚服态", "CHAR_02/遗体态"]),
        _clip(2, character_ids=["CHAR_01/制服态", "CHAR_03"]),
    ]
    root = _mk_storyboard(clips)
    plan = CEP.build_plan(root, "第1集")
    cx = plan["summary"]["complexity"]
    assert cx["distinct_characters"] == 3  # CHAR_01/02/03
    assert cx["class"] == "simple"
