#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""consistency_scaffold 的伏笔自动播种 + 章节切分单测。

cd skills/novel/_lib && python3 -m pytest test_consistency_scaffold.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

import consistency_scaffold as cs

CHAPTER_RE = re.compile(r"^\s*第\s*[0-9一二三四五六七八九十百千]+\s*章")


def test_split_source_chapters_basic():
    text = "第1章 起\n正文一。\n第2章 承\n正文二。\n"
    chs = cs.split_source_chapters(text, CHAPTER_RE)
    assert [c[0] for c in chs] == [1, 2]
    assert "正文一" in chs[0][1] and "正文二" in chs[1][1]


def test_split_no_title_single_chapter():
    chs = cs.split_source_chapters("没有章节标题的整段正文。", CHAPTER_RE)
    assert len(chs) == 1 and chs[0][0] == 1


def test_split_empty_text():
    assert cs.split_source_chapters("   \n  ", CHAPTER_RE) == []


def test_extract_candidates_hits_anchor():
    chs = [(3, "他收起断剑，殊不知这一念之差日后才知埋下大祸。"),
           (4, "平平无奇的一天，什么都没发生。")]
    cands = cs.extract_foreshadow_candidates(chs)
    assert len(cands) == 1
    c = cands[0]
    assert c["planted_chapter"] == 3
    assert c["auto_extracted"] is True and c["confirmed"] is False
    assert c["status"] == "pending" and c["expected_payoff_chapter"] is None
    assert c["anchor"] in c["description"]


def test_extract_candidates_dedup_same_sentence():
    # 同一句含两个锚词只产一条
    chs = [(1, "殊不知按下不表。")]
    cands = cs.extract_foreshadow_candidates(chs)
    assert len(cands) == 1


def test_extract_candidates_respects_max():
    body = "。".join(f"殊不知第{i}件事另有玄机" for i in range(50))
    cands = cs.extract_foreshadow_candidates([(1, body)], max_candidates=5)
    assert len(cands) == 5


def test_extract_candidates_no_false_positive_on_plain_text():
    chs = [(1, "她走进房间，打开窗户，看着远处的山。")]
    assert cs.extract_foreshadow_candidates(chs) == []


def test_skeleton_embeds_seeds():
    seeds = [{"id": "AUTO_001", "confirmed": False}]
    sk = cs.foreshadow_ledger_skeleton(seeds)
    assert sk["seeds"] == seeds
    assert cs.foreshadow_ledger_skeleton()["seeds"] == []


def test_registry_files_carry_foreshadow_seeds():
    seeds = cs.extract_foreshadow_candidates([(2, "殊不知此乃后话。")])
    files = dict(cs.consistency_registry_files("现代言情", foreshadow_seeds=seeds))
    ledger = json.loads(files["设定/foreshadowing_ledger.json"])
    assert ledger["seeds"] and ledger["seeds"][0]["confirmed"] is False
