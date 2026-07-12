"""comic redundancy_audit 单测。运行：cd skills/comic-review/scripts && python -m pytest test_redundancy_audit.py"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("redundancy_audit.py")
spec = importlib.util.spec_from_file_location("comic_redundancy_audit", SCRIPT)
ra = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ra)


def _panel(pid, *, dialogue=(), narration="", chars=("CHAR_A",), loc="LOC_001", art=""):
    return {"panel_id": pid, "dialogue": [{"speaker": "甲", "text": t} for t in dialogue],
            "narration": narration, "characters": list(chars),
            "scene_anchor_id": loc, "art_notes": art, "description": ""}


def test_redundant_pairs_cross_panel_only():
    rows = (ra.panel_texts(_panel("P1", dialogue=["击杀闻弦境生物，获得其道行二十年。"]))
            + ra.panel_texts(_panel("P2", dialogue=["击杀闻弦境生物，获得其道行一百年。"])))
    pairs = ra.redundant_pairs(rows)
    assert len(pairs) == 1 and pairs[0]["panels"] == ["P1", "P2"]
    # 同格内台词-旁白呼应不罚
    same = ra.panel_texts(_panel("P3", dialogue=["冈上有虎，独行者死。"], narration="冈上有虎，独行者死！"))
    assert ra.redundant_pairs(same) == []


def test_repeated_fact_mentions_excludes_names():
    rows = []
    for i, t in enumerate(("他吞了二十年道行。", "二十年道行到手了。", "凭二十年道行她稳了。"), 1):
        rows += ra.panel_texts(_panel(f"P{i}", narration=t))
    facts = ra.repeated_fact_mentions(rows, exclude_names={"CHAR_A"})
    assert any("十年道行" in f["phrase"] or "二十年道" in f["phrase"] for f in facts)


def test_narration_stats_ratio():
    panels = [_panel(f"P{i}", narration="旁白交代。") for i in range(3)] + [
        _panel("P9", dialogue=["台词。"])]
    narr, texty = ra.narration_stats(panels)
    assert (narr, texty) == (3, 4)


def test_repeated_compositions_needs_lens():
    panels = [
        _panel("P1", art="近景 对峙", chars=("A", "B")),
        _panel("P2", art="近景 逼视", chars=("A", "B")),
        _panel("P3", art="全景 交代", chars=("A", "B")),
        _panel("P4", art="", chars=("A", "B")),  # 未标景别不参与
    ]
    groups = ra.repeated_compositions(panels)
    assert len(groups) == 1 and groups[0]["panels"] == ["P1", "P2"]
