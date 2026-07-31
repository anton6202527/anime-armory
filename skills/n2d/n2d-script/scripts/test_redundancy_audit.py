"""redundancy_audit 单测。运行：cd skills/n2d/n2d-script/scripts && python -m pytest test_redundancy_audit.py"""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).with_name("redundancy_audit.py")
spec = importlib.util.spec_from_file_location("redundancy_audit", SCRIPT)
ra = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ra)


def test_redundant_pairs_catch_paraphrase():
    lines = [
        {"shot": 3, "role": "系统", "text": "击杀闻弦境生物，获得其道行二十年。"},
        {"shot": 15, "role": "系统", "text": "击杀闻弦境生物，获得其道行一百年。"},
        {"shot": 5, "role": "姜月初", "text": "今晚的月色真好。"},
    ]
    pairs = ra.redundant_pairs(lines)
    assert len(pairs) == 1 and pairs[0]["shots"] == [3, 15]


def test_short_lines_do_not_false_positive():
    lines = [{"shot": 1, "role": "甲", "text": "什么？"}, {"shot": 2, "role": "乙", "text": "什么？"}]
    assert ra.redundant_pairs(lines) == []


def test_repeated_fact_mentions_across_wordings():
    lines = [
        {"shot": 3, "role": "旁白", "text": "他一口气吞了二十年道行。"},
        {"shot": 4, "role": "姜月初", "text": "二十年道行，就这么到手了？"},
        {"shot": 8, "role": "旁白", "text": "凭着这二十年道行，她第一次觉得稳了。"},
    ]
    facts = ra.repeated_fact_mentions(lines)
    assert any("二十年道" in f["phrase"] or "十年道行" in f["phrase"] for f in facts)


def test_role_names_excluded_from_fact_mentions():
    lines = [
        {"shot": i, "role": "虎山神大王", "text": f"虎山神大王第{i}次说话。"} for i in (1, 2, 3)
    ]
    facts = ra.repeated_fact_mentions(lines)
    assert not any("虎山神大" in f["phrase"] for f in facts)


def test_narration_ratio_and_threshold():
    lines = ([{"shot": i, "role": "旁白", "text": "x"} for i in range(6)]
             + [{"shot": 9, "role": "甲", "text": "y"} for _ in range(4)])
    assert ra.narration_ratio(lines) == 0.6


def test_repeated_compositions_same_signature():
    clips = [
        {"id": "C1", "location_id": "LOC_01", "character_ids": ["A"], "shots": [{"lens": "CU 固定"}]},
        {"id": "C2", "location_id": "LOC_01", "character_ids": ["A"], "shots": [{"lens": "CU 推近"}]},
        {"id": "C3", "location_id": "LOC_01", "character_ids": ["A"], "shots": [{"lens": "LS 固定"}]},
    ]
    groups = ra.repeated_compositions(clips)
    assert len(groups) == 1 and groups[0]["clips"] == ["C1", "C2"]


def test_unannotated_lens_not_penalized():
    clips = [{"id": "C1", "location_id": "L", "character_ids": ["A"], "shots": [{}]},
             {"id": "C2", "location_id": "L", "character_ids": ["A"], "shots": [{}]}]
    assert ra.repeated_compositions(clips) == []
