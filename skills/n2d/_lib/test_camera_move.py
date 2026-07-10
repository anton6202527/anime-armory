#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""normalize_camera_move 单元测试。

cd skills/n2d/_lib && python -m pytest test_camera_move.py
让 CAMERA_MOVE_LEXICON / CAMERA_SPEED_WORDS 成为活引用（被 gate ⑤运镜结构化消费）。
"""
from n2d_logic import normalize_camera_move
from n2d_const import CAMERA_MOVE_LEXICON, CAMERA_MOVE_MANIFEST, STATIC_CAMERA_WORDS


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


def test_visual_reference_camera_moves_are_recognized():
    samples = {
        "镜头左移，匀速保持轴线": "移镜头",
        "盘旋抬升到高空俯视": "盘旋抬升",
        "滚筒旋转制造失控感": "滚筒旋转",
        "第一视角快速穿过人群": "第一视角",
        "柯克变焦表现心理失衡": "柯克变焦",
    }
    for text, expected in samples.items():
        r = normalize_camera_move(text)
        assert any(m["zh"] == expected for m in r["moves"]), text
        assert r["recognized"] is True


def test_manifest_added_camera_moves_are_recognized():
    samples = {
        "甩镜向右切到敌人": "甩镜",
        "急拉变焦暴露整个包围圈": "冲击变焦",
        "焦点转移：从前景符纸转到她的眼睛": "焦点转移",
        "摇臂揭示整座城池": "摇臂揭示",
        "稳定器跟拍主角穿过长廊": "稳定器跟拍",
        "低机位贴地跟拍刀尖前冲": "低机位贴地跟拍",
        "前景遮挡揭示门后的人": "前景遮挡揭示",
        "顶视俯拍阵法几何": "顶视俯拍",
        "载具跟拍马车侧向疾驰": "载具跟拍",
    }
    for text, expected in samples.items():
        r = normalize_camera_move(text)
        assert any(m["zh"] == expected for m in r["moves"]), text
        assert r["recognized"] is True


def test_camera_move_manifest_shape():
    moves = CAMERA_MOVE_MANIFEST.get("moves") or []
    assert len(moves) >= 33
    assert sum(1 for item in moves if item.get("media")) == 23
    assert sum(1 for item in moves if item.get("status") == "added_without_visual_reference") >= 10


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
