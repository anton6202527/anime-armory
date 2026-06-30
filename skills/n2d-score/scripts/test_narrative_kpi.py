#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""长篇叙事 KPI 单元测试。

cd skills/n2d-score/scripts && python -m pytest test_narrative_kpi.py
"""
import os
import sys
import tempfile
import json
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import narrative_kpi as N  # noqa: E402


def test_empty_signals_inconclusive():
    k = N.build_narrative_kpi(None)
    assert k["narrative_continuity"] is None
    assert k["verdict"] is None
    assert k["signals_used"] == []


def test_full_signals_above_line():
    k = N.build_narrative_kpi({
        "payoff_completed_rate": 0.8, "payoff_planned_rate": 1.0, "cold_open_chain_rate": 1.0,
        "homogenization_max": 0.0, "emotion_variation": 0.7,
        "narrative_atom_density": 0.8, "entity_schedule_coverage": 1.0,
        "open_setups": 2, "episodes_counted": 5,
    })
    assert 0.0 <= k["narrative_continuity"] <= 1.0
    assert k["verdict"] == "above"
    assert set(k["signals_used"]) == {
        "payoff_completed", "payoff_planned", "cold_open_chain", "anti_trope",
        "emotion_variation", "narrative_atom_density", "entity_schedule",
    }
    assert k["subscores"]["anti_trope"] == 1.0  # 1 - homogenization 0.0


def test_below_line():
    k = N.build_narrative_kpi({"payoff_rate": 0.2, "cold_open_chain_rate": 0.0,
                               "homogenization_max": 0.9, "emotion_variation": 0.1})
    assert k["verdict"] == "below"


def test_partial_signals_only_payoff():
    k = N.build_narrative_kpi({"payoff_completed_rate": 0.6})
    assert k["signals_used"] == ["payoff_completed"]
    assert k["narrative_continuity"] == 0.6  # 仅一个子项 → 等于它本身


def test_homogenization_inverts_to_anti_trope():
    k = N.build_narrative_kpi({"homogenization_max": 0.25})
    assert k["subscores"]["anti_trope"] == 0.75


def test_clamp_out_of_range():
    k = N.build_narrative_kpi({"payoff_rate": 1.5, "cold_open_chain_rate": -0.3})
    assert k["subscores"]["payoff_completed"] == 1.0
    assert k["subscores"]["cold_open_chain"] == 0.0


def test_payoff_rate_from_ledger():
    pairs = [{"status": "done"}, {"payoff_ep": "第3集"}, {"status": "open"}, {"status": "ongoing"}]
    r = N.payoff_rate_from_ledger(pairs)
    assert r["total"] == 4
    assert r["payoff_completed_rate"] == 0.25
    assert r["payoff_planned_rate"] == 0.75
    assert r["payoff_rate"] == 0.25
    assert r["open_setups"] == 1
    assert r["planned_setups"] == 3
    assert r["completed_setups"] == 1


def test_payoff_rate_empty():
    assert N.payoff_rate_from_ledger([])["payoff_rate"] is None
    assert N.payoff_rate_from_ledger(None)["payoff_rate"] is None


def test_collect_on_empty_root_is_graceful():
    d = tempfile.mkdtemp()
    sig = N.collect_narrative_signals(d)
    # 空项目：不崩，子信号多为 None
    assert sig["payoff_rate"] is None
    assert "cold_open_chain_rate" in sig


def test_release_line_env_override(monkeypatch=None):
    os.environ["N2D_NARRATIVE_RELEASE_LINE"] = "0.95"
    try:
        k = N.build_narrative_kpi({"payoff_rate": 0.9, "cold_open_chain_rate": 0.9})
        assert k["release_line"] == 0.95
        assert k["verdict"] == "below"  # 0.9 < 0.95
    finally:
        del os.environ["N2D_NARRATIVE_RELEASE_LINE"]


def test_profile_changes_release_line():
    demo = N.build_narrative_kpi({"payoff_completed_rate": 0.65, "profile": "demo"})
    prod = N.build_narrative_kpi({"payoff_completed_rate": 0.65, "profile": "production"})
    assert demo["release_line"] == 0.60 and demo["verdict"] == "above"
    assert prod["release_line"] == 0.78 and prod["verdict"] == "below"


def test_narrative_atom_density_collects_from_voiceover():
    root = Path(tempfile.mkdtemp())
    epd = root / "脚本" / "第1集"
    epd.mkdir(parents=True)
    (epd / "voiceover.txt").write_text(
        "\n".join([
            "[镜头1·沈念·惊恐·快] 危机来了！",
            "[镜头2·沈念·冷冽·快] 原来玉佩是假的。",
            "[镜头3·沈念·决绝·快] 她决定反击。",
            "[镜头4·沈念·痛快·快] 真相揭开。",
        ]),
        encoding="utf-8",
    )
    beat = N._load_beat_audit()
    assert beat is not None
    assert N._narrative_atom_density(beat, str(root)) == 1.0


def test_entity_schedule_coverage_collects_storyboards():
    root = Path(tempfile.mkdtemp())
    epd = root / "脚本" / "第1集"
    epd.mkdir(parents=True)
    (epd / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "C01", "entity_schedule": {"characters": ["CHAR_01"]}},
            {"id": "C02", "character_ids": ["CHAR_02"]},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    assert N._entity_schedule_coverage(str(root)) == 0.5
