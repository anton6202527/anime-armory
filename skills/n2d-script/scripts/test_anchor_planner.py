#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for anchor_planner.py — run from skills/n2d-script/scripts/."""
import json
import os

import anchor_planner as ap


# ── resolve_default_midframe（选择点解析·纯函数）──

def test_default_midframe_defaults_on_per_choice_point():
    # 缺设置 / 设置开启 → 开（三帧契约全局默认）
    assert ap.resolve_default_midframe(False, False, None) is True
    assert ap.resolve_default_midframe(False, False, "开启") is True
    # 项目设为关闭 → 关
    assert ap.resolve_default_midframe(False, False, "关闭") is False


def test_default_midframe_cli_flags_override_setting():
    # --default-midframe 强开，覆盖关闭设置
    assert ap.resolve_default_midframe(True, False, "关闭") is True
    # --no-default-midframe 强关，覆盖开启设置
    assert ap.resolve_default_midframe(False, True, "开启") is False


# ── plan_anchor_times（纯函数）──

def test_times_snap_to_shot_boundaries():
    # 15s / target 5 → 3 段 2 锚；理想点 5、10 各自吸附容差内的分镜边界
    times = ap.plan_anchor_times(15, [4, 7.5, 11], target_seg=5, min_seg=4)
    assert times == [4, 11]
    # 段长 4 / 7 / 4，全部 ≥ min_seg
    assert all(b - a >= 4 for a, b in zip([0] + times, times + [15]))


def test_times_fall_back_to_even_split_without_boundaries():
    assert ap.plan_anchor_times(12, [], target_seg=5, min_seg=4) == [6]


def test_times_too_short_returns_empty():
    assert ap.plan_anchor_times(7, [3.5], target_seg=5, min_seg=4) == []


def test_times_capped_by_min_segment():
    # 13s 想按 3.5s 切 4 段，但 min_seg=4 → 最多 3 段 2 锚
    times = ap.plan_anchor_times(13, [], target_seg=3.5, min_seg=4)
    assert len(times) == 2
    assert all(b - a >= 4 for a, b in zip([0] + times, times + [13]))


# ── plan_episode（集成）──

def _write_project(tmp_path, clips, events=None):
    root = tmp_path / "作品"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(
        json.dumps({"episode": 1, "policy": {"tailframe_default": True}, "clips": clips},
                   ensure_ascii=False), encoding="utf-8")
    if events:
        prod = root / "生产数据"
        prod.mkdir(parents=True)
        (prod / "production_events.jsonl").write_text(
            "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8")
    return str(root)


def _clip(index, duration, *, template=None, beats=None, shots=None, continuity=None):
    clip = {"id": f"EP01_CLIP{index:02d}", "duration": duration,
            "firstframe_png": f"出图/第1集/图片/镜头{index:02d}_x.png",
            "continuity": continuity or {"start_state": "s", "end_state": "e",
                                         "transition": "硬切", "need_endframe": True}}
    if template:
        clip["template"] = template
        clip["template_contract"] = {"template_id": template, "beats": beats or []}
    if shots is not None:
        clip["shots"] = shots
    return clip


def test_fight_clip_planned_normal_short_clip_not(tmp_path):
    # 10s 打斗：multiframe 地板(1.5s) 下 fight_target=3.5 真正生效 → 2 锚=4帧
    # （旧 4s relay 地板会卡成 1 锚=3帧，那是接 multiframe2video 前的退化行为）
    root = _write_project(tmp_path, [
        _clip(1, 10, template="fight_exchange", beats=["起手", "命中", "收势"],
              shots=[{"t": "0-3s"}, {"t": "3-6.5s"}, {"t": "6.5-10s"}]),
        _clip(2, 7, shots=[{"t": "0-4s"}, {"t": "4-7s"}]),
    ])
    plan = ap.plan_episode(root, "第1集")
    assert [p["clip_index"] for p in plan["planned"]] == [1]
    p = plan["planned"][0]
    assert p["rule"].startswith("R1")
    assert [a["at_sec"] for a in p["anchors"]] == [3.0, 6.5]  # 2 锚 → 4 帧
    assert p["anchors"][0]["anchor_png"] == "出图/第1集/图片/镜头01_x_a1.png"
    assert p["anchors"][1]["anchor_png"] == "出图/第1集/图片/镜头01_x_a2.png"


def test_long_fight_gets_more_than_three_frames(tmp_path):
    # 15s 打斗(Seedance 长镜)：3 锚 → 5 帧。这是"长镜/打斗会超过3帧"的核心兑现。
    root = _write_project(tmp_path, [
        _clip(1, 15, template="fight_exchange",
              beats=["起手", "逼近", "命中", "受击", "收势"],
              shots=[{"t": "0-3s"}, {"t": "3-6s"}, {"t": "6-9s"}, {"t": "9-12s"}, {"t": "12-15s"}]),
    ])
    plan = ap.plan_episode(root, "第1集")
    anchors = plan["planned"][0]["anchors"]
    assert len(anchors) == 3, [a["at_sec"] for a in anchors]  # 首 + 3锚 + 尾 = 5 帧
    # 严格递增、各段 ≥ multiframe 地板
    ts = [0.0] + [a["at_sec"] for a in anchors] + [15.0]
    assert all(ts[i + 1] - ts[i] >= 1.5 for i in range(len(ts) - 1))


def test_relay_floor_still_governs_eligibility(tmp_path):
    # 短打斗(<2×min_seg=8s)仍不触发 R1（避免给短镜过度加锚）；密度地板只管"出几锚"，不放宽门槛。
    root = _write_project(tmp_path, [
        _clip(1, 7, template="fight_exchange", beats=["起手", "命中"],
              shots=[{"t": "0-3.5s"}, {"t": "3.5-7s"}]),
    ])
    plan = ap.plan_episode(root, "第1集")  # 无 default_midframe
    assert plan["planned"] == []  # 7 < 8，不命中 R1


def test_long_normal_clip_planned_by_r2(tmp_path):
    root = _write_project(tmp_path, [
        _clip(1, 12, shots=[{"t": "0-3s"}, {"t": "3-6s"}, {"t": "6-9s"}, {"t": "9-12s"}]),
    ])
    plan = ap.plan_episode(root, "第1集")
    assert len(plan["planned"]) == 1 and plan["planned"][0]["rule"].startswith("R2")
    assert plan["planned"][0]["anchors"][0]["at_sec"] == 6.0  # 吸附分镜边界=理想点


def test_drift_redraw_promotes_clip_by_r3(tmp_path):
    # 9s/2拍 不够 R2（需 ≥3 拍），但有中段漂移重抽记录 → R3 命中
    events = [{"kind": "n2d_production_event", "episode": "第1集", "stage": "video",
               "event": "redraw",
               "generation": {"asset": "出视频/第1集/视频/Clip_01_打斗.mp4",
                              "redraw_reason": "中段动作漂移"}}]
    root = _write_project(tmp_path, [
        _clip(1, 9, shots=[{"t": "0-4.5s"}, {"t": "4.5-9s"}]),
    ], events=events)
    plan = ap.plan_episode(root, "第1集")
    assert len(plan["planned"]) == 1 and plan["planned"][0]["rule"].startswith("R3")


def test_manual_declaration_is_skipped(tmp_path):
    cont = {"start_state": "s", "end_state": "e", "transition": "硬切", "need_endframe": True,
            "midframe": {"midframe_png": "出图/第1集/图片/镜头01_mid.png",
                         "split_at_sec": 5, "reason": "手动"}}
    root = _write_project(tmp_path, [
        _clip(1, 12, shots=[{"t": "0-4s"}, {"t": "4-8s"}, {"t": "8-12s"}], continuity=cont),
    ])
    plan = ap.plan_episode(root, "第1集")
    assert plan["planned"] == []
    assert plan["skipped"] and "人工优先" in plan["skipped"][0]["why"]


def test_write_back_is_idempotent(tmp_path):
    root = _write_project(tmp_path, [
        _clip(1, 12, shots=[{"t": "0-3s"}, {"t": "3-6s"}, {"t": "6-9s"}, {"t": "9-12s"}]),
    ])
    plan = ap.plan_episode(root, "第1集")
    assert ap.write_back(root, "第1集", plan) == 1
    sb = json.loads(open(os.path.join(root, "脚本", "第1集", "storyboard.json"),
                         encoding="utf-8").read())
    anchors = sb["clips"][0]["continuity"]["anchors"]
    assert len(anchors) == 1 and anchors[0]["reason"].startswith("auto: R2")
    # 第二轮：已声明 → 不再规划、不重复写
    plan2 = ap.plan_episode(root, "第1集")
    assert plan2["planned"] == [] and plan2["skipped"]
    assert ap.write_back(root, "第1集", plan2) == 0


# ── 三帧契约（--default-midframe）──

def test_default_midframe_plans_qc_anchor_for_short_clip(tmp_path):
    # 6s 对话镜：拆不了两段（min_seg=4）→ use=qc 的默认中锚，at=duration/2
    root = _write_project(tmp_path, [
        _clip(1, 6, template="dialogue_shot_reverse",
              beats=["抬眼", "轻笑", "定住"], shots=[{"t": "0-6s"}]),
    ])
    plan = ap.plan_episode(root, "第1集", default_midframe=True)
    assert len(plan["planned"]) == 1
    p = plan["planned"][0]
    assert p["rule"].startswith("D0") and p["anchors"][0]["use"] == "qc"
    assert p["anchors"][0]["at_sec"] == 3.0
    assert p["anchors"][0]["anchor_png"].endswith("_mid.png")
    assert "轻笑" in p["anchors"][0]["reason"]  # 中间拍提示
    assert p["added_cost"]["video_segments"] == 0  # qc 不拆段不加视频成本


def test_default_midframe_uses_split_when_long_enough(tmp_path):
    root = _write_project(tmp_path, [_clip(1, 9, shots=[{"t": "0-4.5s"}, {"t": "4.5-9s"}])])
    plan = ap.plan_episode(root, "第1集", default_midframe=True)
    a = plan["planned"][0]["anchors"][0]
    assert a["use"] == "split" and plan["planned"][0]["added_cost"]["video_segments"] == 1


def test_default_midframe_exempts_very_short_clip(tmp_path):
    root = _write_project(tmp_path, [_clip(1, 2.1, shots=[{"t": "0-2.1s"}])])
    plan = ap.plan_episode(root, "第1集", default_midframe=True)
    assert plan["planned"] == []
    assert len(plan["exempted"]) == 1 and "极短镜" in plan["exempted"][0]["reason"]


def test_default_midframe_write_back_sets_policy_and_exemptions(tmp_path):
    root = _write_project(tmp_path, [
        _clip(1, 6, shots=[{"t": "0-6s"}]),
        _clip(2, 2.1, shots=[{"t": "0-2.1s"}]),
    ])
    plan = ap.plan_episode(root, "第1集", default_midframe=True)
    assert ap.write_back(root, "第1集", plan) == 1
    sb = json.loads(open(os.path.join(root, "脚本", "第1集", "storyboard.json"),
                         encoding="utf-8").read())
    assert sb["policy"]["midframe_default"] is True
    assert sb["clips"][0]["continuity"]["anchors"][0]["use"] == "qc"
    assert "极短镜" in sb["clips"][1]["continuity"]["midframe_exempt_reason"]


def test_rule_hit_takes_precedence_over_default(tmp_path):
    # 10s 打斗镜：命中 R1 → 走 split 规则锚（_a1 命名），不落 D0 默认中锚
    root = _write_project(tmp_path, [
        _clip(1, 10, template="fight_exchange", beats=["起手", "命中", "收势"],
              shots=[{"t": "0-3s"}, {"t": "3-6.5s"}, {"t": "6.5-10s"}]),
    ])
    plan = ap.plan_episode(root, "第1集", default_midframe=True)
    assert len(plan["planned"]) == 1
    assert plan["planned"][0]["rule"].startswith("R1")
    assert plan["planned"][0]["anchors"][0]["anchor_png"].endswith("_a1.png")
