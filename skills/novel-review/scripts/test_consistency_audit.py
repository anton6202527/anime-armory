#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for consistency_audit.py — deterministic wiring exercised offline.

We exercise run_logic() directly (offline, no subprocess): it builds the wiki
via wiki_builder and runs logic_sentry per chapter, then writes the documented
summaries. main()'s mechanical step shells out, so we don't drive it here.

Run from this directory:
    cd skills/novel-review/scripts && python3 -m pytest test_consistency_audit.py
"""
import os
import json
import tempfile

import consistency_audit


def _make_project(char_card, chapters):
    """char_card: text for 设定/角色卡.md. chapters: {filename: text}."""
    root = tempfile.mkdtemp()
    sdir = os.path.join(root, "设定")
    cdir = os.path.join(root, "章节")
    os.makedirs(sdir)
    os.makedirs(cdir)
    # In the real runner, run_mechanical() creates 审稿/ before run_logic() writes
    # its summary there; replicate that precondition when calling run_logic directly.
    os.makedirs(os.path.join(root, "审稿"))
    with open(os.path.join(sdir, "角色卡.md"), "w", encoding="utf-8") as f:
        f.write(char_card)
    for name, text in chapters.items():
        with open(os.path.join(cdir, name), "w", encoding="utf-8") as f:
            f.write(text)
    return root


def test_run_logic_skips_without_character_card():
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "章节"))
    res = consistency_audit.run_logic(root)
    assert res["ran"] is False
    assert "skipped" in res


def test_run_logic_flags_deceased_reactivation():
    # Chapter 1: 李锦云 dies (death keyword immediately after name).
    # Chapter 3: dead character acts again, non-flashback -> blocking alert.
    card = "## 李锦云\n\n姓名：李锦云\n身份：女主\n"
    chapters = {
        "第1章.md": "战场之上，李锦云身亡，全场震动，再无人能挡住敌军的攻势了。",
        "第2章.md": "众人收拾残局，悲痛欲绝，缓缓离开了这片焦土。",
        "第3章.md": "李锦云缓步走入大殿，冷冷开口下令，所有人都跪伏在地。",
    }
    root = _make_project(card, chapters)
    res = consistency_audit.run_logic(root)

    assert res["ran"] is True
    assert res["alerts"] >= 1
    assert res["blocking"] >= 1

    # documented summary file exists with documented shape
    summary_path = os.path.join(root, "审稿", "logic_alerts_summary.json")
    assert os.path.exists(summary_path)
    assert summary_path == res["json"]
    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)
    assert set(["blocking", "total", "alerts"]).issubset(summary.keys())
    types = {a["type"] for a in summary["alerts"]}
    assert "deceased_reactivation" in types

    # wiki was written by run_logic
    wiki_path = os.path.join(root, "设定", "动态百科.json")
    assert os.path.exists(wiki_path)
    with open(wiki_path, encoding="utf-8") as f:
        wiki = json.load(f)
    assert wiki["李锦云"]["status"] == "deceased"
    assert wiki["李锦云"]["death_chapter"] == 1


def test_run_logic_clean_when_no_conflict():
    card = "## 李锦云\n\n姓名：李锦云\n"
    chapters = {
        "第1章.md": "李锦云走进庭院，看着满园花开，心情很好。",
        "第2章.md": "李锦云与友人对弈，谈笑风生，一切如常。",
    }
    root = _make_project(card, chapters)
    res = consistency_audit.run_logic(root)
    assert res["ran"] is True
    assert res["blocking"] == 0

    summary_path = os.path.join(root, "审稿", "logic_alerts_summary.json")
    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)
    assert summary["blocking"] == 0


def test_run_style_skips_without_anchor():
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "章节"))
    res = consistency_audit.run_style(root, anchor=None)
    assert res["ran"] is False
    assert "skipped" in res


def test_chapters_helper_sorts_by_index():
    card = "## 李锦云\n"
    chapters = {
        "第10章.md": "十",
        "第2章.md": "二",
        "第1章.md": "一",
    }
    root = _make_project(card, chapters)
    chs = consistency_audit._chapters(root)
    indices = [idx for idx, _ in chs]
    assert indices == [1, 2, 10]


def test_run_style_reuses_chapter_fingerprint_cache(monkeypatch):
    root = _make_project(
        "## 李锦云\n",
        {
            "第1章.md": "李锦云走进庭院。她看见春光明亮，语句舒展而平稳。",
            "第2章.md": "李锦云在雨声里写信。她慢慢解释旧日误会。",
        },
    )
    anchor_path = os.path.join(root, "设定", "风格指纹.json")
    anchor_fp = consistency_audit.extract_style.fingerprint(
        "李锦云走进庭院。她看见春光明亮，语句舒展而平稳。",
        source="anchor",
    )
    with open(anchor_path, "w", encoding="utf-8") as f:
        json.dump(anchor_fp, f, ensure_ascii=False)

    cache = {}
    first = consistency_audit.run_style(root, anchor_path, cache=cache)
    assert first["ran"] is True
    assert first["cache_misses"] == 2

    def fail_if_recomputed(*_args, **_kwargs):
        raise AssertionError("cached chapter fingerprints should be reused")

    monkeypatch.setattr(consistency_audit.extract_style, "fingerprint", fail_if_recomputed)
    second = consistency_audit.run_style(root, anchor_path, cache=cache)
    assert second["ran"] is True
    assert second["cache_hits"] == 2
    assert second["cache_misses"] == 0
