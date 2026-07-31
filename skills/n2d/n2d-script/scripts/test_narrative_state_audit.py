#!/usr/bin/env python3
"""narrative_state_audit 单测（知识倒流 / 位置瞬移 / 关系候选）。
cd skills/n2d/n2d-script/scripts && python -m pytest test_narrative_state_audit.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import narrative_state_audit as N  # noqa: E402


def _mk(eps):
    d = tempfile.mkdtemp()
    for ep, vo in eps.items():
        epd = Path(d) / "脚本" / ep
        epd.mkdir(parents=True)
        (epd / "voiceover.txt").write_text(vo, encoding="utf-8")
    return d


def codes(findings):
    return {f["code"] for f in findings}


def test_detect_knowledge_marks_candidate():
    text = "[镜头1·沈念·惊恐·快] 她这才知道【真凶令牌】的秘密。"
    k = N.detect_knowledge(text, "第5集")
    assert len(k) == 1
    assert k[0]["character"] == "沈念" and k[0]["status"] == "candidate" and k[0]["auto"]
    assert k[0]["keyword"] == "真凶令牌"          # 【…】可靠专名自动预填
    assert k[0]["known_from_ep"] == "第5集"


def test_detect_locations():
    text = "[镜头1·沈念·平静·慢] 她回到京城府。\n[镜头2·旁白·低沉] 前往南山寺。"
    locs = N.detect_locations(text, "第3集")
    places = {l["place"] for l in locs}
    assert "京城府" in places or "京城" in places
    assert any("寺" in p or "南山" in p for p in places)


def test_premature_knowledge_pure():
    # 声明第5集才知道「真凶」，但第3集沈念已提及「真凶」→ knowledge_premature
    knowledge = [{"character": "沈念", "keyword": "真凶", "known_from_ep": "第5集", "fact": "真凶身份"}]
    ep_texts = {
        "第3集": "[镜头1·沈念·冷冽·快] 我早晚要揪出真凶。",
        "第5集": "[镜头1·沈念·震惊·快] 原来真凶是他。",
    }
    f = N.premature_knowledge(knowledge, ep_texts)
    assert "knowledge_premature" in codes(f)
    assert f[0]["seen_ep"] == 3 and f[0]["declared_ep"] == 5


def test_premature_knowledge_no_false_when_after():
    knowledge = [{"character": "沈念", "keyword": "真凶", "known_from_ep": "第3集", "fact": "真凶"}]
    ep_texts = {"第3集": "[镜头1·沈念·震惊·快] 原来真凶是他。",
                "第5集": "[镜头1·沈念·冷冽·快] 真凶已伏法。"}
    assert N.premature_knowledge(knowledge, ep_texts) == []


def test_premature_skips_incomplete_entries():
    # keyword 没填 → 跳过，不误报
    knowledge = [{"character": "沈念", "keyword": "", "known_from_ep": "第5集", "fact": "x"}]
    ep_texts = {"第3集": "[镜头1·沈念·冷冽·快] 随便一句。"}
    assert N.premature_knowledge(knowledge, ep_texts) == []


def test_location_jump_pure():
    locations = [
        {"character": "沈念", "ep": "第3集", "place": "京城"},
        {"character": "沈念", "ep": "第4集", "place": "南山"},
    ]
    ep_texts = {"第3集": "[镜头1·沈念·平静·慢] 在京城闲坐。",
                "第4集": "[镜头1·沈念·平静·慢] 身处南山。"}   # 两集都无转场
    f = N.location_jumps(locations, ep_texts)
    assert "location_jump" in codes(f)


def test_location_jump_suppressed_by_transition():
    locations = [
        {"character": "沈念", "ep": "第3集", "place": "京城"},
        {"character": "沈念", "ep": "第4集", "place": "南山"},
    ]
    ep_texts = {"第3集": "[镜头1·沈念·平静·慢] 在京城。她决定前往南山。",
                "第4集": "[镜头1·沈念·平静·慢] 身处南山。"}   # 有转场标记
    assert N.location_jumps(locations, ep_texts) == []


def test_check_end_to_end_and_write():
    d = _mk({
        "第3集": "[镜头1·沈念·冷冽·快] 我早晚揪出【真凶】。\n[镜头2·沈念·平静·慢] 她在京城。",
        "第5集": "[镜头1·沈念·震惊·快] 她这才知道【真凶】是他。",
    })
    # 建账写盘
    assert N.main([d, "--write", "--json"]) == 0
    led = N.load_existing(d)
    assert led and led["kind"] == N.LEDGER_KIND
    assert len(led["knowledge"]) >= 1


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
