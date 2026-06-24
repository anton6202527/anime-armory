#!/usr/bin/env python3
"""setup_payoff_ledger 脚手架单测（纯函数 + 临时作品树）。
cd skills/n2d-script/scripts && python -m pytest test_setup_payoff_ledger.py
"""
from __future__ import annotations

import json
import os

import setup_payoff_ledger as sp


def test_ep_num():
    assert sp.ep_num("第7集") == 7 and sp.ep_num("3") == 3 and sp.ep_num("无") is None


def test_detect_setups_only_on_markers():
    text = "她平静地走过。\n他留下一句意味深长的话，埋下伏笔。\n窗外下着雨。"
    setups = sp.detect_setups(text, "第1集")
    assert len(setups) == 1
    s = setups[0]
    assert s["setup_ep"] == "第1集" and s["payoff_ep"] == "" and s["status"] == "open"
    assert "意味深长" in s["desc"]


def test_detect_setups_dedup():
    text = "埋下伏笔的话。\n埋下伏笔的话。"  # 同句去重
    assert len(sp.detect_setups(text, "第1集")) == 1


def test_merge_candidates_never_clobbers_payoff():
    existing = [{"id": "x", "desc": "玉佩身世", "setup_ep": "第1集", "payoff_ep": "第8集", "status": "done"}]
    cands = [
        {"id": "y", "desc": "玉佩身世", "setup_ep": "第1集", "payoff_ep": "", "status": "open"},  # 同 desc → 不覆盖
        {"id": "z", "desc": "黑衣人是谁", "setup_ep": "第2集", "payoff_ep": "", "status": "open"},  # 新 → 加
    ]
    merged = sp.merge_candidates(existing, cands)
    descs = {p["desc"] for p in merged}
    assert descs == {"玉佩身世", "黑衣人是谁"}
    kept = next(p for p in merged if p["desc"] == "玉佩身世")
    assert kept["payoff_ep"] == "第8集"  # 已填的兑现集没被候选清空


def test_scaffold_end_to_end(tmp_path):
    ep_dir = os.path.join(str(tmp_path), "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "voiceover.txt"), "w", encoding="utf-8").write(
        "他握紧那枚玉佩，眼神成谜。")
    res = sp.scaffold(str(tmp_path), ["第1集"])
    assert res["ledger"]["kind"] == sp.LEDGER_KIND
    assert len(res["new_candidates"]) == 1


def test_write_roundtrip(tmp_path):
    ep_dir = os.path.join(str(tmp_path), "脚本", "第1集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "voiceover.txt"), "w", encoding="utf-8").write("此事另有隐情，暗藏杀机。")
    rc = sp.main([str(tmp_path), "--write"])
    assert rc == 0
    data = json.load(open(os.path.join(str(tmp_path), sp.LEDGER_REL), encoding="utf-8"))
    assert data["kind"] == sp.LEDGER_KIND and len(data["pairs"]) == 1


def test_parse_range():
    avail = ["第1集", "第2集", "第3集", "第5集"]
    assert sp._parse_range("1-3", avail) == ["第1集", "第2集", "第3集"]
    assert sp._parse_range("2,5", avail) == ["第2集", "第5集"]
    assert sp._parse_range("", avail) == avail


def test_detect_auto_candidates_unmarked_foreshadow():
    # 无显式标记、但句式像挖坑 → candidate（待编剧确认）
    text = "他望着那道背影，那个黑衣人到底是谁？\n窗外阳光正好。\n她总觉得这件事不对劲。"
    auto = sp.detect_auto_candidates(text, "第1集")
    descs = " ".join(a["desc"] for a in auto)
    assert all(a["status"] == "candidate" and a["auto"] for a in auto)
    assert "到底是谁" in descs and "不对劲" in descs


def test_detect_auto_skips_explicit_marker_lines():
    # 已被显式标记捞走的句子不重复进 auto
    text = "他到底是谁，埋下伏笔。"
    assert sp.detect_auto_candidates(text, "第1集") == []
    assert len(sp.detect_setups(text, "第1集")) == 1


def test_gate_blocks_unfilled_payoff(tmp_path):
    ep_dir = os.path.join(str(tmp_path), "脚本", "第3集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "voiceover.txt"), "w", encoding="utf-8").write("他留下一句意味深长的话，埋下伏笔。")
    # 没有账本 → setup_unlogged block
    g = sp.gate(str(tmp_path), "第3集")
    assert not g["ok"] and g["findings"][0]["code"] == "setup_unlogged"
    # 建账但 payoff 空 → payoff_unfilled block
    sp.main([str(tmp_path), "--write"])
    g2 = sp.gate(str(tmp_path), "第3集")
    assert not g2["ok"] and any(f["code"] == "payoff_unfilled" for f in g2["findings"])


def test_gate_passes_when_payoff_filled(tmp_path):
    ep_dir = os.path.join(str(tmp_path), "脚本", "第3集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "voiceover.txt"), "w", encoding="utf-8").write("他留下一句意味深长的话，埋下伏笔。")
    detected = sp.detect_setups("他留下一句意味深长的话，埋下伏笔。", "第3集")
    ledger = sp.build_ledger([{**detected[0], "payoff_ep": "第8集", "status": "open"}])
    os.makedirs(os.path.join(str(tmp_path), "设定库"), exist_ok=True)
    json.dump(ledger, open(os.path.join(str(tmp_path), sp.LEDGER_REL), "w", encoding="utf-8"), ensure_ascii=False)
    g = sp.gate(str(tmp_path), "第3集")
    assert g["ok"] and g["detected"] == 1
    # CLI --gate 退出码
    assert sp.main([str(tmp_path), "--gate", "第3集", "--json"]) == 0


def test_gate_ongoing_status_not_blocked(tmp_path):
    ep_dir = os.path.join(str(tmp_path), "脚本", "第3集")
    os.makedirs(ep_dir, exist_ok=True)
    open(os.path.join(ep_dir, "voiceover.txt"), "w", encoding="utf-8").write("他留下一句意味深长的话，埋下伏笔。")
    detected = sp.detect_setups("他留下一句意味深长的话，埋下伏笔。", "第3集")
    ledger = sp.build_ledger([{**detected[0], "payoff_ep": "", "status": "ongoing"}])
    os.makedirs(os.path.join(str(tmp_path), "设定库"), exist_ok=True)
    json.dump(ledger, open(os.path.join(str(tmp_path), sp.LEDGER_REL), "w", encoding="utf-8"), ensure_ascii=False)
    assert sp.gate(str(tmp_path), "第3集")["ok"]
