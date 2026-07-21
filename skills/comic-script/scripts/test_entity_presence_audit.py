#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实体在场契约机检单测（2026-07-17 P015 虎妖漏绑整改）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import entity_presence_audit as epa


def write_fixture(root: Path, panels: list[dict]) -> None:
    (root / "脚本" / "第2话").mkdir(parents=True, exist_ok=True)
    (root / "脚本" / "第2话" / "panel_script.json").write_text(
        json.dumps({"panels": panels}, ensure_ascii=False), encoding="utf-8")
    (root / "出图" / "共享").mkdir(parents=True, exist_ok=True)
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps({
            "schema_version": 2,
            "assets": {
                "MON_TIGER": {"id": "MON_TIGER", "type": "monster", "display_name": "虎山神", "aliases": ["虎妖"]},
                "PROP_DAO": {"id": "PROP_DAO", "type": "prop", "display_name": "断横刀"},
                "STYLE_X": {"id": "STYLE_X", "type": "style", "display_name": "水墨风格锚"},
            },
        }, ensure_ascii=False), encoding="utf-8")


def codes(report: dict) -> list[tuple[str, str, str]]:
    return [(f["code"], f["panel_id"], f["severity"]) for f in report["findings"]]


def test_visual_mention_without_binding_warns_and_dialogue_mention_is_info(tmp_path: Path) -> None:
    write_fixture(tmp_path, [
        {"panel_id": "P001", "description": "远处虎妖压成剪影", "characters": [], "references": []},
        {"panel_id": "P002", "description": "空镜", "dialogue": [{"text": "那把断横刀还在吗"}], "characters": [], "references": []},
        {"panel_id": "P003", "description": "虎妖逼近", "characters": ["MON_TIGER"], "references": ["MON_TIGER"]},
    ])
    report = epa.audit(tmp_path, "第2话")
    got = codes(report)
    assert ("mentioned_not_bound", "P001", "warn") in got
    assert ("mentioned_not_bound", "P002", "info") in got
    assert all(item[1] != "P003" for item in got), "已绑定的格不得误报"


def test_style_assets_are_ignored(tmp_path: Path) -> None:
    write_fixture(tmp_path, [
        {"panel_id": "P001", "description": "整体用水墨风格锚统一", "characters": [], "references": []},
    ])
    report = epa.audit(tmp_path, "第2话")
    assert report["findings"] == []


def test_entity_schedule_contract_checks(tmp_path: Path) -> None:
    write_fixture(tmp_path, [
        {
            "panel_id": "P001",
            "description": "",
            "characters": ["MON_TIGER"],
            "references": ["MON_TIGER"],
            "entity_schedule": {
                "required_presence": ["MON_TIGER/FORM_BASE", "PROP_DAO"],
                "forbidden_presence": ["PROP_DAO"],
            },
        },
        {
            "panel_id": "P002",
            "description": "",
            "characters": [],
            "references": ["PROP_DAO"],
            "entity_schedule": {"required_presence": ["MON_TIGER"], "forbidden_presence": ["PROP_DAO"]},
        },
    ])
    report = epa.audit(tmp_path, "第2话")
    got = codes(report)
    assert ("presence_contract_conflict", "P001", "warn") in got
    assert ("required_entity_unbound", "P002", "warn") in got
    assert ("forbidden_entity_bound", "P002", "warn") in got
    assert report["summary"]["panels_with_schedule"] == 2


def test_derived_schedule_seeds_unscheduled_panels(tmp_path: Path) -> None:
    write_fixture(tmp_path, [
        {"panel_id": "P001", "description": "", "characters": ["MON_TIGER"], "references": ["MON_TIGER", "STYLE_X"]},
    ])
    report = epa.audit(tmp_path, "第2话")
    assert report["derived_schedule"]["P001"] == ["MON_TIGER"]


def test_unbound_mention_ack_downgrades_to_info(tmp_path):
    root = write_project(tmp_path) if "write_project" in globals() else None
    # 独立 fixture：registry + 单格脚本
    import json
    root = tmp_path
    reg = {"assets": {"CHAR_WANG": {"display_name": "王进"}}}
    (root / "出图" / "共享").mkdir(parents=True, exist_ok=True)
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    (root / "脚本" / "第1话").mkdir(parents=True, exist_ok=True)
    panels = [
        {"panel_id": "P001", "description": "王进的背影消失在道口", "characters": [],
         "unbound_mention_ack": {"CHAR_WANG": "仅剪影远景，特意不入定妆"}},
        {"panel_id": "P002", "description": "王进握枪而立", "characters": []},
    ]
    (root / "脚本" / "第1话" / "panel_script.json").write_text(
        json.dumps({"panels": panels}, ensure_ascii=False), encoding="utf-8")
    report = epa.audit(root, "第1话")
    by_pid = {(f["panel_id"], f["severity"]) for f in report["findings"] if f["code"] == "mentioned_not_bound"}
    assert ("P001", "info") in by_pid, "已签收理由的提及应降档 info"
    assert ("P002", "warn") in by_pid, "未签收的画面提及保持 warn"


def test_adopt_derived_writes_explicit_schedule(tmp_path, capsys):
    import json
    root = tmp_path
    (root / "脚本" / "第1话").mkdir(parents=True, exist_ok=True)
    panels = [
        {"panel_id": "P001", "characters": ["CHAR_A"], "references": ["LOC_X"]},
        {"panel_id": "P002", "entity_schedule": {"required_presence": ["CHAR_B"]}},
    ]
    (root / "脚本" / "第1话" / "panel_script.json").write_text(
        json.dumps({"panels": panels}, ensure_ascii=False), encoding="utf-8")
    assert epa.adopt_derived_schedule(root, "第1话") == 0
    script = json.loads((root / "脚本" / "第1话" / "panel_script.json").read_text(encoding="utf-8"))
    p1 = script["panels"][0]
    assert p1["entity_schedule"]["required_presence"] == ["CHAR_A", "LOC_X"]
    assert p1["entity_schedule"]["adopted_from"] == "derived_schedule"
    assert script["panels"][1]["entity_schedule"] == {"required_presence": ["CHAR_B"]}, "已有显式排程的格不动"
