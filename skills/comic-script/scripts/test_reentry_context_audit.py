#!/usr/bin/env python3
"""reentry_context_audit 单元测试：前情锚四信号 + 未交代实体 + 自足/首话跳过 + 落盘。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reentry_context_audit as rc


def write_chapter(root: Path, chapter: str, panels):
    d = root / "脚本" / chapter
    d.mkdir(parents=True, exist_ok=True)
    (d / "panel_script.json").write_text(
        json.dumps({"panels": panels}, ensure_ascii=False), encoding="utf-8")


def cb(cid):
    return {"character_id": cid, "form_id": "FORM_BASE"}


def test_panel_char_ids_dedup_and_sources():
    panel = {
        "character_bindings": [cb("CHAR_A"), {"character_id": "CHAR_A"}],
        "characters": ["CHAR_B", {"character_id": "CHAR_C"}],
    }
    assert rc.panel_char_ids(panel) == ["CHAR_A", "CHAR_B", "CHAR_C"]


def test_first_chapter_skipped(tmp_path):
    write_chapter(tmp_path, "第1话", [{"panel_id": "P1", "characters": ["CHAR_X"]}])
    report = rc.audit(tmp_path, "第1话")
    assert report["summary"]["skipped"] is True
    assert report["findings"] == []


def test_reentry_thin_flagged(tmp_path):
    # 第1话建立 CHAR_A；第2话开场无任何前情锚（新场景、无旁白回顾、无常驻角色、无回顾功能）
    write_chapter(tmp_path, "第1话", [
        {"panel_id": "P1", "characters": ["CHAR_A"], "scene_anchor_id": "LOC_TOWN"},
    ])
    write_chapter(tmp_path, "第2话", [
        {"panel_id": "P1", "story_function": "action", "characters": ["CHAR_NEW1"],
         "scene_anchor_id": "LOC_CAVE", "narration": "打斗继续"},
        {"panel_id": "P2", "story_function": "action", "characters": ["CHAR_NEW1"]},
        {"panel_id": "P3", "story_function": "action", "characters": ["CHAR_NEW1"]},
    ])
    report = rc.audit(tmp_path, "第2话")
    codes = {f["code"] for f in report["findings"]}
    assert "reentry_context_thin" in codes


def test_reentry_ok_via_recap_narration(tmp_path):
    write_chapter(tmp_path, "第1话", [{"panel_id": "P1", "characters": ["CHAR_A"]}])
    write_chapter(tmp_path, "第2话", [
        {"panel_id": "P1", "story_function": "recap", "narration": "上一话，阿雪逃出了城",
         "characters": ["CHAR_A"]},
    ])
    report = rc.audit(tmp_path, "第2话")
    assert "reentry_context_thin" not in {f["code"] for f in report["findings"]}


def test_reentry_ok_via_returning_character(tmp_path):
    # 上一话的常驻角色 CHAR_A 在开场再登场 → 前情锚足
    write_chapter(tmp_path, "第1话", [{"panel_id": "P1", "characters": ["CHAR_A"], "scene_anchor_id": "LOC_A"}])
    write_chapter(tmp_path, "第2话", [
        {"panel_id": "P1", "story_function": "action", "characters": ["CHAR_A"], "scene_anchor_id": "LOC_B"},
    ])
    report = rc.audit(tmp_path, "第2话")
    assert "reentry_context_thin" not in {f["code"] for f in report["findings"]}


def test_reentry_ok_via_anchor_continuity(tmp_path):
    write_chapter(tmp_path, "第1话", [{"panel_id": "P9", "characters": ["CHAR_A"], "scene_anchor_id": "LOC_DOCK"}])
    write_chapter(tmp_path, "第2话", [
        {"panel_id": "P1", "story_function": "action", "characters": ["CHAR_A"], "scene_anchor_id": "LOC_DOCK"},
    ])
    report = rc.audit(tmp_path, "第2话")
    assert "reentry_context_thin" not in {f["code"] for f in report["findings"]}


def test_unintroduced_entity_midchapter(tmp_path):
    # CHAR_GHOST 只在第2话中段冒出、无登场功能、不在前话/登记表 → 未交代实体
    write_chapter(tmp_path, "第1话", [{"panel_id": "P1", "characters": ["CHAR_A"]}])
    write_chapter(tmp_path, "第2话", [
        {"panel_id": "P1", "story_function": "recap", "narration": "话说阿雪回到城中", "characters": ["CHAR_A"]},
        {"panel_id": "P2", "story_function": "action", "characters": ["CHAR_A"]},
        {"panel_id": "P3", "story_function": "action", "characters": ["CHAR_A"]},
        {"panel_id": "P4", "story_function": "action", "characters": ["CHAR_GHOST"]},
    ])
    report = rc.audit(tmp_path, "第2话")
    ent = [f for f in report["findings"] if f["code"] == "unintroduced_entity"]
    assert len(ent) == 1 and ent[0]["entity"] == "CHAR_GHOST"


def test_unintroduced_suppressed_when_registered(tmp_path):
    write_chapter(tmp_path, "第1话", [{"panel_id": "P1", "characters": ["CHAR_A"]}])
    write_chapter(tmp_path, "第2话", [
        {"panel_id": "P1", "story_function": "recap", "narration": "话说阿雪回城", "characters": ["CHAR_A"]},
        {"panel_id": "P2", "characters": ["CHAR_A"]},
        {"panel_id": "P3", "characters": ["CHAR_A"]},
        {"panel_id": "P4", "story_function": "action", "characters": ["CHAR_REG"]},
    ])
    # 在登记表登记 CHAR_REG → 不再报
    reg = tmp_path / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(
        json.dumps({"assets": {"CHAR_REG": {"id": "CHAR_REG", "type": "character", "display_name": "登记角"}}},
                   ensure_ascii=False), encoding="utf-8")
    report = rc.audit(tmp_path, "第2话")
    assert "unintroduced_entity" not in {f["code"] for f in report["findings"]}


def test_intro_function_not_flagged(tmp_path):
    write_chapter(tmp_path, "第1话", [{"panel_id": "P1", "characters": ["CHAR_A"]}])
    write_chapter(tmp_path, "第2话", [
        {"panel_id": "P1", "story_function": "recap", "narration": "话说阿雪回城", "characters": ["CHAR_A"]},
        {"panel_id": "P2", "characters": ["CHAR_A"]},
        {"panel_id": "P3", "characters": ["CHAR_A"]},
        {"panel_id": "P4", "story_function": "character_intro", "characters": ["CHAR_NEW"]},
    ])
    report = rc.audit(tmp_path, "第2话")
    assert "unintroduced_entity" not in {f["code"] for f in report["findings"]}


def test_standalone_skipped(tmp_path):
    write_chapter(tmp_path, "第1话", [{"panel_id": "P1", "characters": ["CHAR_A"]}])
    write_chapter(tmp_path, "第2话", [
        {"panel_id": "P1", "story_function": "action", "characters": ["CHAR_Z"], "scene_anchor_id": "LOC_X"},
        {"panel_id": "P2", "characters": ["CHAR_Z"]},
        {"panel_id": "P3", "characters": ["CHAR_Z"]},
        {"panel_id": "P4", "characters": ["CHAR_MID"]},
    ])
    bp = {"chapters": [{"chapter": "第2话", "chapter_type": "oneshot", "format_profile": "four_panel"}]}
    (tmp_path / "脚本" / "split_blueprint.json").write_text(json.dumps(bp, ensure_ascii=False), encoding="utf-8")
    report = rc.audit(tmp_path, "第2话")
    assert report["summary"]["skipped"] is True
    assert report["findings"] == []


def test_write_and_strict(tmp_path):
    write_chapter(tmp_path, "第1话", [{"panel_id": "P1", "characters": ["CHAR_A"], "scene_anchor_id": "LOC_A"}])
    write_chapter(tmp_path, "第2话", [
        {"panel_id": "P1", "story_function": "action", "characters": ["CHAR_NEW"], "scene_anchor_id": "LOC_B"},
        {"panel_id": "P2", "story_function": "action", "characters": ["CHAR_NEW"]},
        {"panel_id": "P3", "story_function": "action", "characters": ["CHAR_NEW"]},
    ])
    rc_code = rc.main([str(tmp_path), "第2话", "--write", "--json", "--strict"])
    assert rc_code == 1
    assert (tmp_path / "生产数据" / "comic_reentry_context_audit_第2话.json").is_file()
    assert (tmp_path / "生产数据" / "comic_reentry_context_audit_第2话.md").is_file()


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
