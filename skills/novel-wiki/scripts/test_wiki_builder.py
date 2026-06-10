#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for wiki_builder.py — deterministic dynamic-wiki skeleton.

Run from this directory:
    cd skills/novel-wiki/scripts && python3 -m pytest test_wiki_builder.py
"""
import os
import json
import tempfile

import wiki_builder


def _make_project(char_card=None, chapters=None):
    root = tempfile.mkdtemp()
    if char_card is not None:
        sdir = os.path.join(root, "设定")
        os.makedirs(sdir)
        with open(os.path.join(sdir, "角色卡.md"), "w", encoding="utf-8") as f:
            f.write(char_card)
    if chapters:
        cdir = os.path.join(root, "章节")
        os.makedirs(cdir)
        for name, text in chapters.items():
            with open(os.path.join(cdir, name), "w", encoding="utf-8") as f:
                f.write(text)
    return root


# ---- parse_character_names ----

def test_parse_character_names_from_headings_and_fields():
    card = "## 李锦云\n\n姓名：沈砚之\n身份：男配\n### 苏婉\n"
    root = _make_project(char_card=card)
    names = wiki_builder.parse_character_names(root)
    assert "李锦云" in names
    assert "沈砚之" in names
    assert "苏婉" in names


def test_parse_character_names_empty_without_card():
    root = _make_project()
    assert wiki_builder.parse_character_names(root) == set()


# ---- seeding ----

def test_seeds_entities_as_active_characters():
    card = "## 李锦云\n## 沈砚之\n"
    root = _make_project(char_card=card, chapters={"第1章.md": "李锦云出场，沈砚之随后。"})
    wiki = wiki_builder.build_wiki(root)
    for name in ("李锦云", "沈砚之"):
        assert wiki[name]["category"] == "character"
        # 李锦云/沈砚之 appear in ch1 so status active (no death)
        assert wiki[name]["status"] == "active"


# ---- last_seen_chapter increments ----

def test_last_seen_chapter_increments_across_chapters():
    card = "## 李锦云\n"
    chapters = {
        "第1章.md": "李锦云第一次登场了。",
        "第2章.md": "无关情节，没有提到她。",
        "第5章.md": "李锦云再次现身处理事务。",
    }
    root = _make_project(char_card=card, chapters=chapters)
    wiki = wiki_builder.build_wiki(root)
    assert wiki["李锦云"]["last_seen_chapter"] == 5
    assert wiki["李锦云"]["last_update"] == 5


# ---- death detection ----

def test_death_keyword_sets_deceased_with_fields():
    card = "## 李锦云\n"
    chapters = {"第3章.md": "激战之中，李锦云身亡，无人能救。"}
    root = _make_project(char_card=card, chapters=chapters)
    wiki = wiki_builder.build_wiki(root)
    e = wiki["李锦云"]
    assert e["status"] == "deceased"
    assert e["auto"] is True
    assert e["death_chapter"] == 3
    assert "evidence" in e and e["evidence"]


def test_flashback_context_death_not_flagged():
    card = "## 李锦云\n"
    # death keyword present but within 回忆/梦中 window -> excluded
    chapters = {"第4章.md": "他在梦中再次见到李锦云身亡的那一幕，泪流满面。"}
    root = _make_project(char_card=card, chapters=chapters)
    wiki = wiki_builder.build_wiki(root)
    assert wiki["李锦云"]["status"] == "active"
    assert "death_chapter" not in wiki["李锦云"]


def test_death_keyword_must_follow_name_same_clause():
    card = "## 李锦云\n## 沈砚之\n"
    # 沈砚之 dies; 李锦云 only watches -> only 沈砚之 deceased
    chapters = {"第2章.md": "李锦云眼睁睁看着，沈砚之身亡了。"}
    root = _make_project(char_card=card, chapters=chapters)
    wiki = wiki_builder.build_wiki(root)
    assert wiki["沈砚之"]["status"] == "deceased"
    assert wiki["李锦云"]["status"] == "active"


# ---- merge: auto death reset on rescan, manual preserved ----

def test_auto_death_reset_when_text_corrected():
    card = "## 李锦云\n"
    existing = {
        "李锦云": {"category": "character", "status": "deceased",
                   "death_chapter": 3, "auto": True, "evidence": "李锦云身亡"}
    }
    # new text no longer kills her
    chapters = {"第3章.md": "李锦云安然无恙地走出战场。"}
    root = _make_project(char_card=card, chapters=chapters)
    wiki = wiki_builder.build_wiki(root, existing=existing)
    assert wiki["李锦云"]["status"] == "active"
    assert "death_chapter" not in wiki["李锦云"]
    assert "auto" not in wiki["李锦云"]


def test_manual_death_preserved():
    card = "## 李锦云\n"
    existing = {
        "李锦云": {"category": "character", "status": "deceased"}  # no auto flag = manual
    }
    chapters = {"第3章.md": "李锦云安然无恙地走出战场。"}
    root = _make_project(char_card=card, chapters=chapters)
    wiki = wiki_builder.build_wiki(root, existing=existing)
    assert wiki["李锦云"]["status"] == "deceased"


# ---- write / json output ----

def test_main_writes_dynamic_wiki_json():
    import subprocess
    import sys
    card = "## 李锦云\n"
    chapters = {"第1章.md": "李锦云登场。", "第2章.md": "李锦云身亡了。"}
    root = _make_project(char_card=card, chapters=chapters)
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, "wiki_builder.py")
    r = subprocess.run([sys.executable, script, root],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr

    wiki_path = os.path.join(root, "设定", "动态百科.json")
    assert os.path.exists(wiki_path)
    with open(wiki_path, encoding="utf-8") as f:
        wiki = json.load(f)
    # keyed by entity name with deterministic fields
    assert "李锦云" in wiki
    e = wiki["李锦云"]
    assert e["category"] == "character"
    assert e["status"] == "deceased"
    assert e["last_seen_chapter"] == 2
    assert "last_update" in e
    # location/owner are LLM-filled, never written by the script
    assert "location" not in e
    assert "owner" not in e
