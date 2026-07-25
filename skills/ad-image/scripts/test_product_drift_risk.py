# -*- coding: utf-8 -*-
"""产品漂移风险账本（product_drift_risk）单测。

盯三条纪律：① 风险信号词面打分+排序，endcard 豁免；② 实测回灌只认 product_qc 已报镜；
③ 高危镜不在打样集 → warn；advisory 底线 summary.block 恒 0。
"""
import json

import product_drift_risk as pdr


def _write(root, rel, payload):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _storyboard(shots):
    return {"kind": "ad_storyboard", "shots": shots}


def test_missing_storyboard_degrades(tmp_path):
    report = pdr.build(tmp_path)
    assert report["available"] is False and report["summary"]["block"] == 0


def test_risk_signals_score_and_rank(tmp_path):
    _write(tmp_path, "脚本/storyboard.json", _storyboard([
        {"shot_id": "镜头01", "shot": "产品特写 玻璃瓶身高光 包装文字清晰", "scene": "桌面"},
        {"shot_id": "镜头02", "shot": "远景 街道空镜", "scene": "街道"},
        {"shot_id": "镜头03", "shot": "片尾 endcard logo板", "scene": "尾板"},
    ]))
    report = pdr.build(tmp_path)
    labels = [r["label"] for r in report["shots"]]
    assert "镜头03" not in labels                      # endcard 豁免
    assert labels[0] == "镜头01"                       # 特写+材质+文字 → 排最前
    assert report["shots"][0]["score"] > 30
    assert report["summary"]["block"] == 0


def test_measured_feedback_promotes_to_high(tmp_path):
    _write(tmp_path, "脚本/storyboard.json", _storyboard([
        {"shot_id": "镜头02", "shot": "产品中景 摆在桌上", "scene": "桌面"},
    ]))
    _write(tmp_path, "出图/分镜/product_qc.json", {
        "summary": {"block": 0, "warn": 1},
        "findings": [{"severity": "warn", "code": "product_dhash", "msg": "镜头02 疑产品漂移"}],
    })
    report = pdr.build(tmp_path)
    row = next(r for r in report["shots"] if r["label"] == "镜头02")
    assert row["tier"] == "high" and any("measured" in s for s in row["signals"])


def test_high_risk_unpiloted_warns(tmp_path):
    _write(tmp_path, "脚本/storyboard.json", _storyboard([
        {"shot_id": "镜头01", "shot": "产品特写 微距 玻璃瓶 包装文字 俯拍", "scene": "桌面"},
    ]))
    _write(tmp_path, "生产数据/ad_pilot_matrix.json", {
        "coverage": {"hook": {"label": "镜头09"}, "product_hero": None},
    })
    report = pdr.build(tmp_path)
    assert any(f["code"] == "high_risk_unpiloted" and f["severity"] == "warn"
               for f in report["findings"])


def test_reference_plan_delta_and_gap_feed_score(tmp_path):
    _write(tmp_path, "脚本/storyboard.json", _storyboard([
        {"shot_id": "镜头01", "shot": "产品特写", "scene": "桌面"},
    ]))
    _write(tmp_path, "生产数据/ad_reference_plan.json", {
        "shots": [{"shot": "镜头01",
                   "plans": [{"asset_id": "hero", "delta_score": 1.5, "registered": False}]}],
    })
    report = pdr.build(tmp_path)
    signals = report["shots"][0]["signals"]
    assert any("delta_score" in s for s in signals) and any("reference_gap" in s for s in signals)
