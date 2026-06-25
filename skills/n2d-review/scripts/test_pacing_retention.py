#!/usr/bin/env python3
"""pacing_retention 纯启发式核心 + 编排测试（无外部模型依赖）。

跑：cd skills/n2d-review/scripts && python3 -m pytest test_pacing_retention.py -q
"""
from __future__ import annotations

import json
import os

import pacing_retention as pr


# ---------- shot_durations / shot_density_per_min ----------

def test_shot_durations_filters_nonpositive_and_bad():
    clips = [{"duration": 8}, {"duration": 0}, {"duration": "x"}, {"duration": 2.5}, {}]
    assert pr.shot_durations(clips) == [8.0, 2.5]


def test_shot_density_per_min():
    assert pr.shot_density_per_min(10, 60) == 10.0
    assert pr.shot_density_per_min(5, 0) == 0.0      # 不除零


def test_benchmark_threshold_loader_uses_json(tmp_path, monkeypatch):
    bench = tmp_path / "industry_benchmark.json"
    bench.write_text(json.dumps({
        "retention_benchmarks": {
            "proxy_thresholds": {"retention_hook_floor": 0.77, "density_fast_per_min": 41}
        }
    }), encoding="utf-8")
    monkeypatch.setenv("N2D_PACE_BENCHMARK_JSON", str(bench))
    pr._BENCHMARK_CACHE = None
    assert pr._bench_value("retention_hook_floor", 0.8) == 0.77
    assert pr._bench_value("density_fast_per_min", 45) == 41.0
    assert pr._bench_value("missing", 12.0) == 12.0
    pr._BENCHMARK_CACHE = None
    os.environ.pop("N2D_PACE_BENCHMARK_JSON", None)


# ---------- hook 关键词 ----------

def test_is_hook_text_and_is_slow_text():
    assert pr.is_hook_text("冷开场·铜镜陌生脸") is True
    assert pr.is_hook_text("cold open hook") is True
    assert pr.is_hook_text("日常·吃饭闲聊") is False
    assert pr.is_slow_text("铺垫·长镜") is True
    assert pr.is_slow_text("爽点·碎切") is False


# ---------- hook_strength ----------

def test_hook_strength_strong_open():
    clips = [{"rhythm": "冷开场·钩子", "duration": 3}]
    h = pr.hook_strength(clips)
    assert h["score"] == 100.0
    assert h["open_is_hook"] is True


def test_hook_strength_slow_non_hook_open_penalized():
    clips = [{"rhythm": "日常铺陈", "label": "起床", "duration": 9}]
    h = pr.hook_strength(clips)
    # 非钩子(-45) + 开场镜过长(-30) → 25
    assert h["score"] == 25.0
    assert h["open_is_hook"] is False
    assert len(h["reasons"]) == 2


def test_hook_strength_empty_is_none_not_fabricated():
    h = pr.hook_strength([])
    assert h["score"] is None        # 无 clips 不臆造分
    assert h["muted_safe"] is None


# ---------- is_muted_safe_hook / 静音首屏 ----------

def test_is_muted_safe_hook_visual_text_structural():
    assert pr.is_muted_safe_hook("特写·一巴掌扇过去") is True      # 视觉冲突
    assert pr.is_muted_safe_hook("烧屏标题卡·三年后") is True       # 烧屏文字
    assert pr.is_muted_safe_hook("冷开场·倒叙") is True            # 结构视觉钩
    assert pr.is_muted_safe_hook("悬念·旁白独白抛问") is False      # 只靠声音/旁白
    assert pr.is_muted_safe_hook("") is False


def test_hook_strength_structural_visual_open_stays_full():
    # 冷开场=结构视觉钩 → 静音安全，不扣静音分（守住既有 100 分契约）
    h = pr.hook_strength([{"rhythm": "冷开场·钩子", "duration": 3}])
    assert h["score"] == 100.0
    assert h["muted_safe"] is True


def test_hook_strength_audio_only_hook_muted_penalized():
    # 是钩子(悬念)但只靠旁白声音、无画面/字幕 → 扣 15 静音分，不叠加非钩子的 -45
    h = pr.hook_strength([{"rhythm": "悬念", "note": "旁白独白抛出身世之谜", "duration": 3}])
    assert h["open_is_hook"] is True
    assert h["muted_safe"] is False
    assert h["score"] == 85.0
    assert any("静音" in r for r in h["reasons"])


def test_analyze_surfaces_muted_first_screen_risk(tmp_path):
    # 首屏是钩子、分没塌（>60），静音风险也要单列成 risk_shot（不被均分掩盖）
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    clips = [{"id": "C1", "rhythm": "悬念", "note": "旁白独白抛身世", "duration": 3}]
    clips += [{"id": f"C{i}", "rhythm": "对话", "duration": d}
              for i, d in zip(range(2, 8), [2, 3, 1, 4, 2, 3])]
    (ep_dir / "storyboard.json").write_text(json.dumps({"clips": clips}), encoding="utf-8")
    res = pr.analyze(str(tmp_path), "第1集")
    kinds = {r["kind"] for r in res["risk_shots"]}
    assert "muted_first_screen" in kinds
    assert res["verdict"] in ("ok", "warn")     # advisory，永不 block


# ---------- pacing_score ----------

def test_pacing_score_healthy_band_full():
    # 20 镜 / 60s = 20/min，落在 [10,45) → 满分
    p = pr.pacing_score([3.0] * 20)
    assert p["score"] == 100.0
    assert round(p["density_per_min"], 0) == 20.0


def test_pacing_score_too_slow_penalized():
    # 4 镜 / 60s = 4/min < 10 → 扣分
    p = pr.pacing_score([15.0] * 4)
    assert p["score"] < 100.0
    assert "偏慢" in " ".join(p["reasons"])


def test_pacing_score_too_fast_penalized():
    # 60 镜 / 60s = 60/min ≥ 45 → 扣分
    p = pr.pacing_score([1.0] * 60)
    assert p["score"] < 100.0
    assert "过密" in " ".join(p["reasons"])


def test_pacing_score_empty_none():
    assert pr.pacing_score([])["score"] is None


# ---------- long_shot_clusters（风险镜定位） ----------

def test_long_shot_clusters_detects_run():
    clips = [
        {"id": "C1", "duration": 2},
        {"id": "C2", "duration": 7},
        {"id": "C3", "duration": 8},
        {"id": "C4", "duration": 9},   # C2-C4 三连长镜 → 聚集
        {"id": "C5", "duration": 2},
    ]
    cl = pr.long_shot_clusters(clips)
    assert len(cl) == 1
    assert cl[0]["clip_ids"] == ["C2", "C3", "C4"]
    assert cl[0]["intentional"] is False   # 无铺垫标注


def test_long_shot_clusters_intentional_when_marked_slow():
    clips = [{"id": f"C{i}", "duration": 8, "rhythm": "铺垫·长镜留白"} for i in range(3)]
    cl = pr.long_shot_clusters(clips)
    assert cl[0]["intentional"] is True   # 有意铺垫 → 降权


def test_long_shot_clusters_below_threshold_ignored():
    clips = [{"id": "C1", "duration": 7}, {"id": "C2", "duration": 8}, {"id": "C3", "duration": 2}]
    assert pr.long_shot_clusters(clips) == []  # 仅 2 连 < cluster_min(3)


# ---------- retention_proxy_score ----------

def test_retention_flat_durations_penalized():
    # 全等长 → CV=0 → 催眠扣分
    r = pr.retention_proxy_score([4.0] * 10, [])
    assert r["score"] < 100.0
    assert r["cv"] == 0.0


def test_retention_varied_durations_ok():
    r = pr.retention_proxy_score([1, 2, 5, 1, 8, 2, 1, 4], [])
    assert r["score"] == 100.0


def test_retention_risky_cluster_penalized():
    clusters = [{"intentional": False}]
    r = pr.retention_proxy_score([1, 2, 5, 1, 8, 2], clusters)
    assert r["risky_clusters"] == 1
    assert r["score"] < 100.0


def test_retention_too_few_shots_none():
    assert pr.retention_proxy_score([4.0], [])["score"] is None


# ---------- advisory_total / advisory_verdict ----------

def test_advisory_total_weighted():
    total = pr.advisory_total({"score": 100.0}, {"score": 100.0}, {"score": 100.0})
    assert total == 100.0
    # 钩子塌(0) 其余满 → 0.4*0 + 0.3*100 + 0.3*100 = 60
    assert pr.advisory_total({"score": 0.0}, {"score": 100.0}, {"score": 100.0}) == 60.0


def test_advisory_total_renormalizes_when_axis_missing():
    # pacing/retention 证据不足(None) → 只按钩子轴归一
    assert pr.advisory_total({"score": 80.0}, {"score": None}, {"score": None}) == 80.0


def test_advisory_total_all_none():
    assert pr.advisory_total({"score": None}, {"score": None}, {"score": None}) is None


def test_advisory_verdict_caps_to_warn_never_block():
    assert pr.advisory_verdict(None) == "inconclusive"   # 证据不足不罚分
    assert pr.advisory_verdict(50.0) == "warn"            # 低分封顶 warn，绝不 block
    assert pr.advisory_verdict(95.0) == "ok"


# ---------- analyze 缺数据优雅跳过 ----------

def test_analyze_skips_without_storyboard(tmp_path):
    (tmp_path / "生产数据").mkdir()
    res = pr.analyze(str(tmp_path), "第1集")
    assert res["available"] is False
    assert res["verdict"] == "inconclusive"
    assert res["score"] is None          # 绝不臆造分
    assert res["notes"]


def test_analyze_skips_when_too_few_clips(tmp_path):
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "storyboard.json").write_text(
        json.dumps({"clips": [{"id": "C1", "duration": 5}, {"id": "C2", "duration": 4}]}),
        encoding="utf-8")
    res = pr.analyze(str(tmp_path), "第1集")
    assert res["available"] is False     # 样本太少不臆造
    assert res["score"] is None


def test_analyze_scores_real_storyboard(tmp_path):
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    clips = [{"id": "C1", "rhythm": "冷开场·钩子", "duration": 3}]
    clips += [{"id": f"C{i}", "rhythm": "对话", "duration": d}
              for i, d in zip(range(2, 12), [2, 3, 1, 4, 2, 1, 3, 2, 5, 2])]
    (ep_dir / "storyboard.json").write_text(json.dumps({"clips": clips}), encoding="utf-8")
    res = pr.analyze(str(tmp_path), "第1集")
    assert res["available"] is True
    assert isinstance(res["score"], float)
    assert res["verdict"] in ("ok", "warn")   # advisory，永不 block


# ---------- to_score_report / write_score_report ----------

def test_to_score_report_never_blocks():
    res = {
        "available": True, "verdict": "warn", "score": 55.0,
        "hook": {"score": 40.0}, "pacing": {"score": 60.0, "density_per_min": 12.0},
        "retention": {"score": 60.0},
        "risk_shots": [{"clips": ["C2", "C3"], "kind": "long_shot_cluster",
                        "verdict": "warn", "message": "长镜聚集"}],
        "notes": [],
    }
    rep = pr.to_score_report(res)
    assert rep["blocks"] == 0            # advisory 永不硬阻断 gate
    assert rep["warnings"] >= 2          # 风险镜 + 低分
    assert rep["metrics"]["verdict"] == "warn"


def test_to_score_report_skip_when_unavailable():
    res = {"available": False, "verdict": "inconclusive", "score": None,
           "risk_shots": [], "notes": ["缺 storyboard"]}
    rep = pr.to_score_report(res)
    assert rep["blocks"] == 0 and rep["warnings"] == 0
    assert rep["evidence"] == ["缺 storyboard"]
    assert rep["metrics"]["available"] is False


def test_write_score_report_roundtrips(tmp_path):
    res = {"available": True, "verdict": "ok", "score": 92.0,
           "hook": {"score": 100.0}, "pacing": {"score": 90.0, "density_per_min": 20.0},
           "retention": {"score": 85.0}, "risk_shots": [], "notes": []}
    path = pr.write_score_report(str(tmp_path), "第1集", res)
    data = json.load(open(path, encoding="utf-8"))
    assert data["blocks"] == 0
    assert data["infos"] == 1           # 通过且无风险镜
    assert data["metrics"]["score"] == 92.0
