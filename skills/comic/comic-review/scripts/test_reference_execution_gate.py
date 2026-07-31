#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_reference_execution：声明的风格锚/绑定主体必须真实进入参考通道。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import gate


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def make_project(tmp_path: Path, hard_gate: str) -> Path:
    root = tmp_path / "作品"
    root.mkdir()
    (root / "_设置.md").write_text(f"- 角色一致性硬闸: {hard_gate}\n", encoding="utf-8")
    return root


def jobs_payload() -> dict:
    return {
        "jobs": [
            {
                "panel_id": "P001",
                "status": "ready",
                "references": [
                    {"id": "CHAR_A", "path": "出图/共享/图片/a.png"},
                    {"id": "STYLE_MAIN", "path": "出图/共享/图片/style.png"},
                ],
                "character_bindings": [{"character_id": "CHAR_A"}],
            }
        ]
    }


def test_style_anchor_omission_blocks_under_hard_gate(tmp_path: Path) -> None:
    root = make_project(tmp_path, "开启")
    write_json(
        root / "生产数据" / "dreamina_reference_bundles" / "第1话" / "P001.json",
        {
            "references": [{"id": "CHAR_A", "role": "front"}],
            "omitted_attachments": [{"id": "STYLE_MAIN"}],
        },
    )
    findings: list[dict] = []
    gate.check_reference_execution(root, "第1话", jobs_payload(), findings)
    style = [item for item in findings if item["code"] == "style_anchor_not_executed"]
    assert len(style) == 1
    assert style[0]["severity"] == "block"
    assert style[0]["confidence"] == "deterministic"


def test_style_anchor_omission_warns_without_hard_gate(tmp_path: Path) -> None:
    root = make_project(tmp_path, "关闭")
    write_json(
        root / "生产数据" / "dreamina_reference_bundles" / "第1话" / "P001.json",
        {"references": [{"id": "CHAR_A", "role": "front"}]},
    )
    findings: list[dict] = []
    gate.check_reference_execution(root, "第1话", jobs_payload(), findings)
    style = [item for item in findings if item["code"] == "style_anchor_not_executed"]
    assert len(style) == 1 and style[0]["severity"] == "warn"


def test_composite_parts_satisfy_execution(tmp_path: Path) -> None:
    root = make_project(tmp_path, "开启")
    write_json(
        root / "生产数据" / "dreamina_reference_bundles" / "第1话" / "P001.json",
        {
            "references": [
                {
                    "id": "CHAR_A",
                    "role": "composite_views",
                    "composite": True,
                    "parts": [{"id": "CHAR_A", "role": "front"}, {"id": "CHAR_A", "role": "face"}],
                },
                {"id": "STYLE_MAIN", "role": "style"},
            ]
        },
    )
    findings: list[dict] = []
    gate.check_reference_execution(root, "第1话", jobs_payload(), findings)
    assert not findings, "拼板部件与风格锚都已执行时不得报缺"


def test_missing_subject_anchor_blocks(tmp_path: Path) -> None:
    root = make_project(tmp_path, "开启")
    write_json(
        root / "生产数据" / "codex_reference_bundles" / "第1话" / "P001.json",
        {"references": [{"id": "STYLE_MAIN", "role": "style"}]},
    )
    findings: list[dict] = []
    gate.check_reference_execution(root, "第1话", jobs_payload(), findings)
    subject = [item for item in findings if item["code"] == "subject_anchor_not_executed"]
    assert len(subject) == 1 and subject[0]["severity"] == "block"


def test_no_bundle_stays_silent(tmp_path: Path) -> None:
    root = make_project(tmp_path, "开启")
    findings: list[dict] = []
    gate.check_reference_execution(root, "第1话", jobs_payload(), findings)
    assert not findings, "无 bundle（旧后端/手工采纳）不得虚构结论"
