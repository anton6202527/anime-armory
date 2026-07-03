#!/usr/bin/env python3
"""scene_blocking_continuity 纯文本核心 + 编排测试（无依赖）。

跑：cd skills/n2d-review/scripts && python -m pytest test_scene_blocking_continuity.py
"""
from __future__ import annotations

import json

import scene_blocking_continuity as sb


# ---------- parse_blocking ----------

def test_parse_registered_layout():
    # 真实契约样例：visual_contract.场景轴线视线.<LOC>.站位
    m = sb.parse_blocking("沈念居画左、柳娘子居画右后")
    assert m["沈念"]["side"] == "left"
    assert m["沈念"]["depth"] is None
    assert m["柳娘子"]["side"] == "right"
    assert m["柳娘子"]["depth"] == "back"   # 「…右后」→ 后景


def test_parse_per_shot_blocking_ignores_non_actors():
    m = sb.parse_blocking("沈念画左床榻，柳娘子画右门口，二人隔床幔对视")
    assert m["沈念"]["side"] == "left"
    assert m["柳娘子"]["side"] == "right"
    assert "二人" not in m   # 无方位的碎词不入；门口非人名


def test_parse_short_token_not_a_name():
    # 「二人画左」——「二人」是 2 字会被收？语义上是碎词，但 conflict 仅对 ref∩cur 判，故无害。
    m = sb.parse_blocking("门口处空无一人")
    assert m == {}   # 无方位词


def test_parse_center_and_none():
    m = sb.parse_blocking("沈念居中而立")
    assert m["沈念"]["side"] == "center"


# ---------- is_reverse_shot ----------

def test_is_reverse_shot():
    assert sb.is_reverse_shot("过肩反打柳娘子") is True
    assert sb.is_reverse_shot("正反打守床→门横轴") is True
    assert sb.is_reverse_shot("固定中景，无翻转") is False


# ---------- blocking_band ----------

def test_band_same_side_ok():
    assert sb.blocking_band({"side": "left"}, {"side": "left"}, locked=True, reverse_shot=False) == "ok"


def test_band_side_flip_locked_is_block():
    assert sb.blocking_band({"side": "left"}, {"side": "right"}, locked=True, reverse_shot=False) == "block"


def test_band_side_flip_chain_is_warn():
    assert sb.blocking_band({"side": "left"}, {"side": "right"}, locked=False, reverse_shot=False) == "warn"


def test_band_reverse_shot_suppresses():
    assert sb.blocking_band({"side": "left"}, {"side": "right"}, locked=True, reverse_shot=True) == "ok"


def test_band_depth_flip():
    assert sb.blocking_band({"depth": "front"}, {"depth": "back"}, locked=True, reverse_shot=False) == "block"
    assert sb.blocking_band({"depth": "front"}, {"depth": "back"}, locked=False, reverse_shot=False) == "warn"


def test_band_center_not_conflict():
    # center↔left 不算左右相反（不硬判）
    assert sb.blocking_band({"side": "center"}, {"side": "left"}, locked=True, reverse_shot=False) == "ok"


# ---------- analyze 端到端 ----------

def _write_sb(tmp_path, ep, payload):
    d = tmp_path / "脚本" / ep
    d.mkdir(parents=True)
    (d / "storyboard.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_analyze_locked_violation_blocks(tmp_path):
    _write_sb(tmp_path, "第1集", {
        "visual_contract": {"场景轴线视线": {"冷宫寝殿": {"站位": "沈念居画左、柳娘子居画右后"}}},
        "clips": [
            {"id": "Clip01", "scene": "冷宫寝殿/夜/内",
             "template_contract": {"blocking": "沈念画左床榻，柳娘子画右门口"}},
            {"id": "Clip05", "scene": "冷宫寝殿/夜/内",
             "template_contract": {"blocking": "沈念画右窗边"}},   # 违锁：注册画左→本镜画右，无反打
        ],
    })
    res = sb.analyze(str(tmp_path), "第1集")
    assert res["available"] is True
    blocks = [s for s in res["shots"] if s["verdict"] == "block"]
    assert any(s["clip"] == "Clip05" and s["char"] == "沈念" for s in blocks)


def test_analyze_reverse_shot_suppressed(tmp_path):
    _write_sb(tmp_path, "第1集", {
        "visual_contract": {"场景轴线视线": {"冷宫寝殿": {"站位": "沈念居画左"}}},
        "clips": [
            {"id": "Clip05", "scene": "冷宫寝殿/夜/内",
             "template_contract": {"blocking": "沈念画右", "continuity_must": ["过肩反打"]}},
        ],
    })
    res = sb.analyze(str(tmp_path), "第1集")
    assert [s for s in res["shots"] if s["verdict"] == "block"] == []   # 反打抑制


def test_analyze_chain_mode_warn_without_registration(tmp_path):
    # 无注册站位 → 退回首镜参考，链式 warn
    _write_sb(tmp_path, "第1集", {
        "clips": [
            {"id": "Clip01", "scene": "大殿/日/内", "template_contract": {"blocking": "沈念画左、柳娘画右"}},
            {"id": "Clip02", "scene": "大殿/日/内", "template_contract": {"blocking": "沈念画右"}},  # 链式翻转
        ],
    })
    res = sb.analyze(str(tmp_path), "第1集")
    assert any(s["verdict"] == "warn" and s["char"] == "沈念" for s in res["shots"])
    assert all(s["verdict"] != "block" for s in res["shots"])   # 无锁不升 block


def test_analyze_missing_storyboard_skips(tmp_path):
    res = sb.analyze(str(tmp_path), "第1集")
    assert res["available"] is False
    assert res["notes"]
