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


def test_detect_setups_cleans_voiceover_hook_suffix():
    text = "[镜头1·旁白·阴冷·快] 死了半月的人回家了。 ⚡钩子"
    setups = sp.detect_setups(text, "第1集")
    assert len(setups) == 1
    assert setups[0]["desc"] == "死了半月的人回家了。"


def test_detect_setups_recognizes_ending_hook_marker():
    text = "[镜头20·妖·濒死·慢] 这眼睛……|| 他当年，也有。 🪝集尾"
    setups = sp.detect_setups(text, "第1集")
    assert len(setups) == 1
    assert setups[0]["desc"] == "这眼睛……|| 他当年，也有。"


def test_detect_setups_strips_standalone_hook_marker():
    text = "[镜头25·旁白·慢] 盆底那点微光，又亮了一下。🪝"
    setups = sp.detect_setups(text, "第1集")
    assert len(setups) == 1
    assert setups[0]["desc"] == "盆底那点微光，又亮了一下。"


def test_detect_setups_skips_placeholder_lines():
    text = "# 待精修：按 split_plan.json 的冲突/看点/钩子压缩为 60-90 秒"
    assert sp.detect_setups(text, "第4集") == []
    assert sp.detect_auto_candidates(text, "第4集") == []


def test_detect_setups_skips_voiceover_beat_plan_lines():
    text = "- 集尾硬钩：换皮妖临死认出金睛，说“他当年也有”。"
    assert sp.detect_setups(text, "第1集") == []


def test_detect_setups_skips_voiceover_meta_positioning_lines():
    text = "- 本集功能：尾扣把最差灵米倒进破盆，埋第3集米变金爽点。"
    assert sp.detect_setups(text, "第2集") == []


def test_detect_setups_skips_storyboard_and_json_metadata_lines():
    text = (
        "**片段12（EP01_CLIP12）：时长：4秒**　**节奏**：留白·集尾硬断\n"
        "\"opened_at\": \"EP01_CLIP12 / 集尾\",\n"
        "- 时长：6s；累计：1:19-1:25；节奏：集尾·真相半露\n"
        "- 中段锚帧：2s，集尾微光必须单独锁定\n"
        "- 需要尾帧?：否，集尾终止镜。\n"
        "[镜头25·旁白·慢] 盆底那点微光，又亮了一下。🪝"
    )
    setups = sp.detect_setups(text, "第1集")
    assert [s["desc"] for s in setups] == ["盆底那点微光，又亮了一下。"]


def test_detect_setups_skips_markdown_table_rows():
    text = "| PROP_OLD_COPPER_HALF | 半片旧铜 | 道具/伏笔 | Clip05 | 暗旧铜片，烫红皮肤 |"
    assert sp.detect_setups(text, "第1集") == []


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
    open(os.path.join(ep_dir, "storyboard.json"), "w", encoding="utf-8").write(
        '{"opened_at": "EP01_CLIP12 / 集尾"}')
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
