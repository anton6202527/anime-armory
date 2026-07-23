#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pilot_matrix 单测。从本目录跑：
    cd skills/ad-image/scripts && python3 -m pytest test_pilot_matrix.py
覆盖：缺 storyboard → available=false 降级 / 典型分镜五轴全覆盖且去重 ≤5 镜 /
ad_reference_plan 存在时 risk_max 按 delta_score 取镜 / 无文字镜 → text_render 如实 absent /
block 恒 0（advisory·计划不是门）/ 单镜可覆盖多轴时补画风对比样本 / --write 落盘。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_matrix as pm  # noqa: E402


# ── 夹具：最小广告项目（拍广告不拆集，粒度是镜头） ──────────────────────────────

def _project(tmp_path, *, shots=None, reference_plan=None, name="广告项目"):
    root = tmp_path / name
    (root / "脚本").mkdir(parents=True)
    if shots is not None:
        (root / "脚本" / "storyboard.json").write_text(
            json.dumps({"aspect": "9:16", "shots": shots}, ensure_ascii=False), encoding="utf-8")
    if reference_plan is not None:
        (root / "生产数据").mkdir(parents=True, exist_ok=True)
        (root / "生产数据" / "ad_reference_plan.json").write_text(
            json.dumps(reference_plan, ensure_ascii=False), encoding="utf-8")
    return root


# 典型 4 镜广告：钩子人物镜 / 产品 hero / 人+产品同框 / 片尾文字板。
TYPICAL_SHOTS = [
    {"id": "S1", "shot": "男主皱眉盯着手机，痛点开场", "assets": {"CHAR_A": True}},
    {"id": "S2", "shot": "产品特写 beauty shot，瓶身旋转，光泽质感", "assets": {"PROD_X": True}},
    {"id": "S3", "shot": "男主手持产品微笑展示", "assets": {"CHAR_A": True, "PROD_X": True}},
    {"id": "S4", "shot": "片尾板：logo + slogan + CTA 立即下单", "endcard": True},
]


def _coverage(report):
    return {row["axis"]: row for row in report["coverage"]}


def _pick_axes(report):
    out = set()
    for pick in report["picks"]:
        out.update(pick["axes"])
    return out


# ── 缺料降级 ─────────────────────────────────────────────────────────────────

def test_missing_storyboard_is_degraded_not_crash(tmp_path):
    root = _project(tmp_path)  # 没写 storyboard
    report = pm.build(root)
    assert report["available"] is False
    assert report["summary"]["block"] == 0
    assert any(f["code"] == "storyboard_missing" for f in report["findings"])
    # 所有轴 absent，picks 为空——不臆造。
    assert all(row["status"] == "absent" for row in report["coverage"])
    assert report["picks"] == []


def test_empty_storyboard_is_degraded(tmp_path):
    root = _project(tmp_path, shots=[])
    report = pm.build(root)
    assert report["available"] is False
    assert any(f["code"] == "storyboard_empty" for f in report["findings"])


def test_strict_exit_code_on_unavailable(tmp_path):
    root = _project(tmp_path)
    assert pm.main([str(root), "--strict"]) == 1
    assert pm.main([str(root)]) == 0  # 默认 advisory：恒 0


# ── 典型分镜：五轴全覆盖 + 去重 ────────────────────────────────────────────────

def test_typical_storyboard_covers_all_axes_with_dedup(tmp_path):
    root = _project(tmp_path, shots=TYPICAL_SHOTS)
    report = pm.build(root)
    assert report["available"] is True
    cov = _coverage(report)
    assert all(cov[axis]["status"] == "covered" for axis in pm.REQUIRED_COVERAGE)
    # 去重：≤5 镜，且每镜唯一。
    labels = [p["shot"] for p in report["picks"]]
    assert len(labels) == len(set(labels))
    assert 2 <= len(labels) <= pm.MAX_PICKS
    assert _pick_axes(report) >= set(pm.REQUIRED_COVERAGE)
    # 语义指定：hook=首镜；product_hero=S2（hero 语义）；multi_entity=S3；text_render=S4。
    assert cov["hook"]["shot"] == "镜头1"
    assert cov["product_hero"]["shot"] == "镜头2"
    assert cov["multi_entity"]["shot"] == "镜头3"
    assert cov["text_render"]["shot"] == "镜头4"
    # 缺参考处方 → risk_max 回退为资产最多的镜（S3 有 2 个资产）。
    assert cov["risk_max"]["shot"] == "镜头3"
    assert any(f["code"] == "reference_plan_missing" for f in report["findings"])


def test_picks_carry_reasons_and_review_focus(tmp_path):
    root = _project(tmp_path, shots=TYPICAL_SHOTS)
    report = pm.build(root)
    for pick in report["picks"]:
        assert pick["reasons"], pick["shot"]
        assert pick["review_focus"], pick["shot"]
    hero = next(p for p in report["picks"] if "product_hero" in p["axes"])
    assert any("品牌色" in item for item in hero["review_focus"])
    text = next(p for p in report["picks"] if "text_render" in p["axes"])
    assert any("错别字" in item for item in text["review_focus"])


# ── ad_reference_plan 存在 → risk_max 按 delta_score ─────────────────────────

def test_reference_plan_risk_ranking_is_honored(tmp_path):
    plan = {"kind": "ad_reference_plan", "shots": [
        {"shot": "镜头1", "assets": [{"asset_id": "CHAR_A", "delta_score": 1.0}]},
        {"shot": "镜头2", "assets": [{"asset_id": "PROD_X", "delta_score": 4.5}]},
        {"shot": "镜头3", "assets": [{"asset_id": "CHAR_A", "delta_score": 2.0},
                                     {"asset_id": "PROD_X", "delta_score": 3.0}]},
    ]}
    root = _project(tmp_path, shots=TYPICAL_SHOTS, reference_plan=plan)
    report = pm.build(root)
    cov = _coverage(report)
    assert cov["risk_max"]["shot"] == "镜头2"
    assert not any(f["code"] == "reference_plan_missing" for f in report["findings"])
    risk_pick = next(p for p in report["picks"] if "risk_max" in p["axes"])
    assert "4.5" in " ".join(risk_pick["reasons"])


def test_stale_reference_plan_label_falls_back(tmp_path):
    # 处方里的镜头标签在当前 storyboard 里不存在（过期处方）→ 回退实体计数，不崩溃。
    plan = {"kind": "ad_reference_plan", "shots": [
        {"shot": "镜头99", "assets": [{"asset_id": "PROD_X", "delta_score": 9.9}]},
    ]}
    root = _project(tmp_path, shots=TYPICAL_SHOTS, reference_plan=plan)
    report = pm.build(root)
    assert _coverage(report)["risk_max"]["shot"] == "镜头3"


# ── 轴无候选 → 如实 absent，不臆造 ────────────────────────────────────────────

def test_no_text_shots_reports_absent_honestly(tmp_path):
    shots = [s for s in TYPICAL_SHOTS if s["id"] != "S4"]
    root = _project(tmp_path, shots=shots)
    report = pm.build(root)
    cov = _coverage(report)
    assert cov["text_render"]["status"] == "absent"
    assert cov["text_render"]["shot"] is None
    assert "text_render" not in _pick_axes(report)
    assert "text_render" in report["summary"]["axes_absent"]
    assert any(f["code"] == "coverage_axis_absent" for f in report["findings"])


def test_single_shot_ad_adds_no_fake_axes(tmp_path):
    # 一镜到底广告：只有 1 镜时全部轴指到同一镜或 absent；不足 2 镜不硬凑。
    root = _project(tmp_path, shots=[
        {"id": "S1", "shot": "产品特写 beauty shot，logo 与 slogan 露出", "assets": {"PROD_X": True}}])
    report = pm.build(root)
    assert len(report["picks"]) == 1
    assert report["picks"][0]["shot"] == "镜头1"
    assert report["summary"]["block"] == 0


def test_style_probe_added_when_one_pick_but_more_shots(tmp_path):
    # 首镜同时是产品 hero+文字镜 → 五轴聚在一镜；第二镜补画风对比样本（不虚构轴覆盖）。
    root = _project(tmp_path, shots=[
        {"id": "S1", "shot": "产品特写 beauty shot，logo slogan 文字露出", "assets": {"PROD_X": True}},
        {"id": "S2", "shot": "空镜过渡"},
    ])
    report = pm.build(root)
    labels = [p["shot"] for p in report["picks"]]
    assert labels == ["镜头1", "镜头2"]
    probe = report["picks"][1]
    assert probe["axes"] == ["style_probe"]
    assert "style_probe" not in {row["axis"] for row in report["coverage"]}


# ── advisory 纪律：block 恒 0 ─────────────────────────────────────────────────

@pytest.mark.parametrize("shots", [None, [], TYPICAL_SHOTS])
def test_block_is_always_zero(tmp_path, shots):
    root = _project(tmp_path, shots=shots)
    report = pm.build(root)
    assert report["summary"]["block"] == 0


# ── --write 落盘 ─────────────────────────────────────────────────────────────

def test_write_report_lands_json_and_md(tmp_path):
    root = _project(tmp_path, shots=TYPICAL_SHOTS)
    report = pm.build(root)
    paths = pm.write_report(root, report)
    data = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert data["kind"] == "ad_pilot_matrix"
    assert data["summary"]["block"] == 0
    md = Path(paths["md"]).read_text(encoding="utf-8")
    assert "打样矩阵" in md
    assert "镜头1" in md
