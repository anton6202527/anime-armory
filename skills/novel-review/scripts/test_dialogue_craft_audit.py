#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_dialogue_craft_audit — 对白工艺机检（直给/零摩擦/播报/潜台词说破）。

Run: cd skills/novel-review/scripts && python3 -m pytest test_dialogue_craft_audit.py
"""
import json
import os

import dialogue_craft_audit as dca


# ── on_the_nose_hits ─────────────────────────────────────────────────────────

def test_on_the_nose_requires_emotion_plus_causal():
    # 情绪自陈 + 因果连词 同句 → 命中
    hits = dca.on_the_nose_hits(["「我很生气，因为你背叛了我。」"])
    assert len(hits) == 1


def test_plain_emotion_statement_not_on_the_nose():
    # 只有情绪自陈、无因果链 → 不算（人类也直说"我怕"）
    assert dca.on_the_nose_hits(["「我好害怕。」"]) == []


def test_causal_without_emotion_not_on_the_nose():
    assert dca.on_the_nose_hits(["「因为下雨，所以我们回去吧。」"]) == []


def test_on_the_nose_splits_sentences():
    # 情绪句与因果句分属两句 → 不算共现
    assert dca.on_the_nose_hits(["「我很生气。因为今天下雨。」"]) == []


# ── friction_count ───────────────────────────────────────────────────────────

def test_friction_detects_resistance():
    lines = ["「不行。」", "「凭什么让我去？」", "「此事休提。」"]
    assert dca.friction_count(lines) >= 3


def test_cooperative_dialogue_zero_friction():
    lines = ["「好的，我马上去。」", "「一切听你安排。」"]
    assert dca.friction_count(lines) == 0


# ── as_you_know_hits ─────────────────────────────────────────────────────────

def test_as_you_know_long_broadcast_hits():
    line = "「你也知道，我们沈家三代单传，祖上定下的规矩是嫡长子必须在十八岁之前完成祭祖大典才能继位。」"
    assert len(dca.as_you_know_hits([line])) == 1


def test_as_you_know_short_line_exempt():
    # 短句寒暄不算播报
    assert dca.as_you_know_hits(["「你也知道我的。」"]) == []


# ── subtext_spoken_hits ──────────────────────────────────────────────────────

def test_subtext_fragment_spoken_aloud():
    subtexts = ["他其实早就认出了她，但不能相认"]
    dialogue = ["「其实我早就认出了她，但不能相认。」"]
    hits = dca.subtext_spoken_hits(dialogue, subtexts)
    assert hits and hits[0]["fragment"]


def test_subtext_kept_underwater_no_hit():
    subtexts = ["他其实早就认出了她"]
    dialogue = ["「这位姑娘看着面生。」"]
    assert dca.subtext_spoken_hits(dialogue, subtexts) == []


# ── _load_scene_subtexts / analyze 优雅跳过 ──────────────────────────────────

def test_load_scene_subtexts(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "设定"))
    payload = {"kind": "novel_scene_cards", "scenes": [
        {"id": "SC001-01", "chapter": 1, "subtext": "他在撒谎"},
        {"id": "SC002-01", "chapter": 2, "subtext": ""},
    ]}
    with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    subs = dca._load_scene_subtexts(root)
    assert subs == {1: ["他在撒谎"]}


def test_analyze_skips_without_chapters(tmp_path):
    res = dca.analyze(str(tmp_path))
    assert res["ran"] is False and "skipped" in res
