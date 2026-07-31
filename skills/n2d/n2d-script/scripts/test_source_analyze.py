import json

import source_analyze


def test_extract_characters_filters_system_and_action_false_positives():
    text = """
【击杀燃灯境生物，获得道行十一万九千八百五十五年】
【当前道行：四十九万八千六百七十二年】
无数道精气，自城中妖魔尸首中飘出。
一道黑影一次次被抛向空中。
姜月初冷笑道：“老子还是你娘呢！”
李乾元低声道：“我是你爹。”
云翎大圣苦笑道：“其实他没有骗你。”
"""
    names = {item["name"] for item in source_analyze.extract_characters(text, limit=20)}

    assert "姜月初" in names
    assert "李乾元" in names
    assert "云翎大圣" in names
    assert "获得" not in names
    assert "当前" not in names
    assert "无数" not in names
    assert "一道" not in names
    assert "你爹" not in names


def test_extract_characters_filters_speech_modifier_false_positives():
    text = """
姜月初侧过头，轻声道：“无需担心。”
随后缓缓落下。
顾挽澜思索片刻，还是沉声答道：“西域妖庭底蕴不浅。”
这番话，说得还算客气。
徐骁漠然看着脚下妖群，冷声道：“随我南下。”
"""
    names = {item["name"] for item in source_analyze.extract_characters(text, limit=20)}

    assert "姜月初" in names
    assert "徐骁" in names
    assert "轻声" not in names
    assert "随后" not in names
    assert "还是" not in names
    assert "这番话" not in names
    assert "漠然" not in names


def test_extract_characters_ignores_non_speech_action_and_daoxing_fragments():
    text = """
姜月初站起身，环顾四周。
高临下地看着妖魔，少女没有说话。
【是否消耗道行：六万年】
要知道，这世道并不太平。
他顿了顿，抱拳道：“属下领命。”
魏合继续说道：“不是这样。”
试探着问道：“能走吗？”
躬身说道：“遵旨。”
忽而笑道：“来了。”
喃喃道：“不该如此。”
姜月初冷声道：“杀。”
"""
    names = {item["name"] for item in source_analyze.extract_characters(text, limit=20)}

    assert "姜月初" in names
    assert "姜月初站" not in names
    assert "高临下地" not in names
    assert "是否消耗" not in names
    assert "要知" not in names
    assert "这世" not in names
    assert "没有" not in names
    assert "他顿了顿" not in names
    assert "抱拳" not in names
    assert "魏合继续" not in names
    assert "试探着" not in names
    assert "躬身" not in names
    assert "忽而" not in names
    assert "喃喃" not in names


def test_extract_characters_filters_sigh_and_self_directed_action_false_positives():
    text = """
姜月初叹了口气说道：“罢了。”
叹了口气说道：“今日到此。”
魏合自顾自说道：“无需理会。”
自顾自说道：“继续。”
"""
    names = {item["name"] for item in source_analyze.extract_characters(text, limit=20)}

    assert "姜月初" in names
    assert "魏合" in names
    assert "叹了口气" not in names
    assert "自顾自" not in names


def test_source_integrity_folds_only_adjacent_exact_headings_and_keeps_line_evidence():
    text = """本书单身。
第1章 起
第1章 起
正文。
第2章 承

第2章 承
第4章 转
第4章 转
广武县
正文继续。
朱厌

第5章 合
第5章 合
--------------
歇一天，明天继续还债
"""
    analysis = source_analyze.analyze_source("测试", text)
    integrity = analysis["source_integrity"]

    # Only physically adjacent, exactly equal headings are folded. The two
    # chapter-2 headings separated by a blank line both remain analysis input.
    assert analysis["stats"]["chapters"] == 5
    assert integrity["raw_chapter_heading_count"] == 8
    assert integrity["adjacent_duplicate_heading_count"] == 3
    assert integrity["chapter_headings_after_fold"] == 5
    assert integrity["unique_chapter_count"] == 4
    assert integrity["missing_chapter_numbers"] == [3]
    assert integrity["completion_status"] == "likely_ongoing"
    assert {item["line"] for item in integrity["suspected_captions"]} >= {10, 12}
    assert any(item["line"] == 17 for item in integrity["author_notes"])
    assert any(item["line"] == 17 and item["kind"] == "ongoing" for item in integrity["completion_clues"])

    rendered = source_analyze.render_analysis_md(analysis)
    assert "## 源完整性（source_integrity）" in rendered
    assert "相邻完全重复标题：3" in rendered
    assert "L17：歇一天，明天继续还债" in rendered


def test_duplicate_heading_fold_is_exact_not_merely_same_chapter_number():
    text = "第1章 甲\n第1章 乙\n第1章 乙\n"

    assert source_analyze.chapter_count(text) == 2
    assert source_analyze.fold_adjacent_duplicate_chapter_headings(text).splitlines() == [
        "第1章 甲", "第1章 乙"
    ]


def test_cli_recovers_episode_count_from_bounded_split_plan_header(tmp_path):
    root = tmp_path / "work"
    source = tmp_path / "novel.txt"
    source.write_text("第1章 起\n正文。\n", encoding="utf-8")
    plan = root / "脚本" / "split_plan.json"
    plan.parent.mkdir(parents=True)
    # Deliberately not valid full JSON: the CLI only needs the stable header
    # field and must not parse/read the 44-MiB-class body to recover this count.
    plan.write_bytes(
        b'{"schema_version":2,"estimated_total_episode_count":830,"source_units":['
        + b"x" * (source_analyze.SPLIT_PLAN_HEAD_BYTES * 2)
    )

    assert source_analyze.main([str(source), "--root", str(root), "--title", "测试"]) == 0

    analysis = json.loads((root / "设定库" / "source_analysis.json").read_text(encoding="utf-8"))
    assert analysis["stats"]["episode_scaffolds"] == 830
    assert analysis["stats"]["episode_scaffolds_source"].endswith(
        "split_plan.json:estimated_total_episode_count"
    )


def test_explicit_episode_sequence_wins_over_split_plan_estimate(tmp_path):
    root = tmp_path / "work"
    plan = root / "脚本" / "split_plan.json"
    plan.parent.mkdir(parents=True)
    plan.write_text('{"estimated_total_episode_count": 830}', encoding="utf-8")

    analysis = source_analyze.write_analysis(str(root), "测试", "第1章 起\n正文。", ["第一集"])

    assert analysis["stats"]["episode_scaffolds"] == 1
    assert "episode_scaffolds_source" not in analysis["stats"]


def test_missing_split_plan_keeps_legacy_zero_for_cli_analysis(tmp_path):
    root = tmp_path / "work"

    analysis = source_analyze.write_analysis(str(root), "测试", "第1章 起\n正文。")

    assert analysis["stats"]["episode_scaffolds"] == 0
    assert "episode_scaffolds_source" not in analysis["stats"]
