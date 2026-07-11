#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""角色一致性硬闸 / 年龄形态继承 开关必须按值显式生效（回归：值"开启"曾因 token 匹配失效）。

运行：cd skills/comic-review/scripts && python3 -m pytest test_review_consistency_hard_gate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import review


PANEL_SCRIPT = {
    "panels": [
        {"panel_id": "P001", "description": "主角出场。", "references": ["CHAR_A"], "characters": ["CHAR_A"]}
    ]
}


def run_gate(settings: dict, registry: dict) -> list[dict]:
    issues: list[dict] = []
    review.check_high_grade_consistency(
        Path("/项目"),
        settings,
        Path("/项目/出图/共享/identity_registry.json"),
        registry,
        PANEL_SCRIPT,
        issues,
    )
    return issues


def reasons(issues: list[dict]) -> str:
    return "；".join(str(item.get("reason") or "") for item in issues)


def test_hard_gate_value_on_activates_dna_block() -> None:
    settings = {"角色一致性硬闸": "开启", "参考一致性策略": "共享参考图", "风格锚": "未指定"}
    registry = {"assets": {"CHAR_A": {"id": "CHAR_A", "type": "character"}}}

    issues = run_gate(settings, registry)

    text = reasons(issues)
    assert "缺少 character_dna/dna_contract" in text
    assert "缺少年龄/形态继承策略" in text
    assert "缺少项目风格锚" in text
    assert all(item["severity"] == "block" for item in issues)


def test_hard_gate_off_and_plain_strategy_stays_silent() -> None:
    settings = {"角色一致性硬闸": "关闭", "年龄形态继承": "关闭", "参考一致性策略": "共享参考图"}
    registry = {"assets": {"CHAR_A": {"id": "CHAR_A", "type": "character"}}}

    assert run_gate(settings, registry) == []


def test_variant_inheritance_value_on_requires_variant_policy() -> None:
    settings = {"角色一致性硬闸": "关闭", "年龄形态继承": "开启", "参考一致性策略": "共享参考图", "风格锚": "水墨国风锚图组"}
    registry = {
        "style_contract": "水墨国风，粗线条。",
        "assets": {"CHAR_A": {"id": "CHAR_A", "type": "character", "character_dna": "方脸短发灰衣。"}},
    }

    issues = run_gate(settings, registry)

    assert "缺少年龄/形态继承策略" in reasons(issues)


def test_legacy_long_strategy_value_still_triggers() -> None:
    settings = {"参考一致性策略": "高一致性共享参考图+多视图+形态继承", "风格锚": ""}
    registry = {}

    issues = run_gate(settings, registry)

    assert "缺少 identity_registry.json" in reasons(issues)


def test_satisfied_registry_passes_hard_gate() -> None:
    settings = {"角色一致性硬闸": "开启", "参考一致性策略": "共享参考图", "风格锚": "未指定"}
    registry = {
        "style_contract": "水墨国风，粗线条。",
        "assets": {
            "CHAR_A": {
                "id": "CHAR_A",
                "type": "character",
                "character_dna": "方脸短发灰衣。",
                "variant_policy": "少年/成年只改比例与服饰层，不换脸。",
            }
        },
    }

    assert run_gate(settings, registry) == []
