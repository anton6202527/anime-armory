#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""normalize_camera_move 单元测试。

cd skills/n2d/_lib && python -m pytest test_camera_move.py
让 CAMERA_MOVE_LEXICON / CAMERA_SPEED_WORDS 成为活引用（被 gate ⑤运镜结构化消费）。
"""
from n2d_logic import normalize_camera_move
from n2d_const import CAMERA_MOVE_LEXICON, STATIC_CAMERA_WORDS


def test_recognizes_zh_trigger_alias():
    # "推近" 是 推镜头 的触发别名（分镜散文不会写词典 key "推镜头"）
    r = normalize_camera_move("略俯 MCU 缓慢推近")
    assert any(m["zh"] == "推镜头" for m in r["moves"])
    assert "缓慢" in r["speeds"]
    assert r["recognized"]


def test_freeform_not_recognized():
    r = normalize_camera_move("镜头慢慢靠近她然后停下")
    assert r["moves"] == []
    assert not r["is_static"]
    assert r["recognized"] is False


def test_static_counts_as_declared():
    r = normalize_camera_move("固定机位")
    assert r["is_static"] is True
    assert r["recognized"] is True
    assert r["moves"] == []


def test_move_without_speed():
    r = normalize_camera_move("环绕拍摄主角")
    assert any(m["zh"] == "环绕" for m in r["moves"])
    assert r["speeds"] == []


def test_en_trigger_matches():
    r = normalize_camera_move("slow dolly in on her face")
    assert any(m["zh"] == "推镜头" for m in r["moves"])
    assert "缓慢" in r["speeds"]  # en "slow" 命中速度词 缓慢


def test_every_lexicon_entry_has_triggers_and_slots():
    # 防止以后给词典加条目却忘了 triggers/slots（gate ⑤ 依赖 triggers）
    for zh, spec in CAMERA_MOVE_LEXICON.items():
        assert spec.get("triggers"), f"{zh} 缺 triggers"
        assert spec.get("en"), f"{zh} 缺 en"
        assert "slots" in spec, f"{zh} 缺 slots"


def test_empty_text():
    r = normalize_camera_move("")
    assert r["recognized"] is False
    assert r["moves"] == []
