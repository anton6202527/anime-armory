# -*- coding: utf-8 -*-
"""Regression tests for neutral, context-only behavioral surface comparisons."""
import json
import os

import behavioral_signals as bs


def test_pairwise_surface_difference_reports_literal_distance_only():
    divergent = ["主角当场反杀镇北王", "师妹其实是暗桩会倒戈", "朝廷钦差突然到场搅局"]
    similar = ["主角当场反杀镇北王", "主角会当场反杀镇北王的", "主角当场就反杀了镇北王"]
    assert bs.pairwise_surface_difference(divergent) > 0.8
    assert bs.pairwise_surface_difference(similar) < 0.55
    assert bs.pairwise_surface_difference(["只有一条"]) is None


def test_next_chapter_surface_overlap_has_no_surprise_direction():
    predictions = ["主角当场反杀镇北王", "师妹倒戈"]
    matching = "第二日，主角当场反杀镇北王，血溅五步。"
    unrelated = "圣旨到了：全城戒严，科举提前，主角被点为主考官。"
    assert bs.max_next_chapter_surface_overlap(predictions, matching) > 0.4
    assert bs.max_next_chapter_surface_overlap(predictions, unrelated) < 0.3


def _project(tmp_path, chapter_texts, predictions_by_ch):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    os.makedirs(os.path.join(root, "评分"), exist_ok=True)
    for index, text in enumerate(chapter_texts, 1):
        with open(os.path.join(root, "章节", f"第{index:02d}章.md"), "w", encoding="utf-8") as f:
            f.write(text)
    for chapter, predictions in predictions_by_ch.items():
        with open(os.path.join(root, "评分", f"reader_predictions_第{chapter:02d}章.json"),
                  "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1,
                "kind": "novel_reader_predictions",
                "chapter": chapter,
                "predictions": [{"persona": "rookie", "text": item} for item in predictions],
            }, f, ensure_ascii=False)
    return root


def test_analyze_keeps_overlap_as_question_not_plot_judgment(tmp_path):
    same = [
        "主角当场反杀镇北王", "主角会当场反杀镇北王", "主角当场就反杀镇北王",
        "主角当场反杀了镇北王", "主角必当场反杀镇北王",
    ]
    root = _project(
        tmp_path,
        ["第一章正文。", "翌日校场，主角当场反杀镇北王，血溅五步。"],
        {1: same},
    )
    result = bs.analyze(root)
    assert result["schema_version"] == 2
    assert result["blocking"] == 0
    assert result["alerts"] == []
    assert result["automatic_constraint_eligible"] is False
    row = result["prediction_chapters"][0]
    assert row["pairwise_surface_difference"] is not None
    assert row["next_chapter_max_surface_overlap"] is not None
    question_types = {item["type"] for item in result["questions"]}
    assert question_types == {
        "review_prediction_surface_difference",
        "review_prediction_next_chapter_overlap",
    }
    overlap_question = next(
        item for item in result["questions"]
        if item["type"] == "review_prediction_next_chapter_overlap"
    )
    assert overlap_question["automatic_action"] is None
    assert "不等于陈词滥调" in overlap_question["question"]
    assert "不要求强行反转" in overlap_question["question"]


def test_analyze_skips_without_behavior_inputs(tmp_path):
    result = bs.analyze(str(tmp_path))
    assert result["ran"] is False
    assert "reader_predictions" in result["skipped"]


def test_single_prediction_is_recorded_without_classification(tmp_path):
    root = _project(tmp_path, ["一", "二"], {1: ["只有一条"]})
    result = bs.analyze(root)
    row = result["prediction_chapters"][0]
    assert row["insufficient_for_pairwise"] is True
    assert row["pairwise_surface_difference"] is None
    assert result["alerts"] == []


def test_recall_surface_overlap_is_not_memory_or_retention_score():
    previous = "第二日校场比武，主角当场反杀镇北王，血溅五步，师妹的暗桩身份就此暴露。"
    matching = "主角校场反杀镇北王，师妹身份暴露。"
    unrelated = "皇帝驾崩，太子登基，京城大乱。"
    assert bs.recall_surface_overlap(matching, previous) > 0.5
    assert bs.recall_surface_overlap(unrelated, previous) < 0.25
    assert bs.recall_surface_overlap("", previous) is None
    assert bs.recall_surface_overlap("有内容", "") is None


def _response(perspective, bored=None, confused=None, disbelief=None, recall="",
              favorite_character=None, annoying_character=None):
    return {
        "persona": perspective,
        "bored": bored,
        "confused": confused,
        "disbelief": disbelief,
        "recall": recall,
        "favorite_character": favorite_character,
        "annoying_character": annoying_character,
    }


def _write_survey(root, chapter, responses):
    os.makedirs(os.path.join(root, "评分"), exist_ok=True)
    with open(os.path.join(root, "评分", f"reader_survey_第{chapter:02d}章.json"),
              "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_reader_survey",
            "chapter": chapter,
            "responses": responses,
        }, f, ensure_ascii=False)


def test_survey_annotations_create_neutral_questions_without_majority_causality(tmp_path):
    root = _project(
        tmp_path,
        ["第二日校场比武，主角当场反杀镇北王，血溅五步。", "二", "三"],
        {},
    )
    _write_survey(root, 2, [
        _response(
            "logic",
            bored={"span": "排位流水账"},
            confused={"span": "谁在说话"},
            disbelief={"span": "林昭突然原谅仇人", "characters": ["林昭"]},
            recall="皇帝驾崩太子登基京城大乱",
        ),
        _response("emote", recall="似乎发生了一场比武"),
    ])
    _write_survey(root, 3, [
        _response("rookie", bored="中段走神"),
        _response("logic", bored="中段走神"),
    ])
    result = bs.analyze(root)
    assert result["alerts"] == []
    assert result["blocking"] == 0
    by_type = {item["type"]: item for item in result["questions"]}
    assert {
        "review_bored_annotations",
        "review_confused_annotations",
        "review_disbelief_annotations",
        "review_recall_surface_overlap",
    } <= set(by_type)
    assert "不自动等于 OOC" in by_type["review_disbelief_annotations"]["question"]
    assert "不能推断真实记忆或留存" in by_type["review_recall_surface_overlap"]["question"]
    assert all(item["automatic_action"] is None for item in result["questions"])
    assert result["survey_chapters"][0]["annotations"]["bored"][0]["span"] == "排位流水账"


def test_survey_favorite_and_annoying_are_preserved_without_ranking(tmp_path):
    root = _project(tmp_path, ["一"], {})
    _write_survey(root, 1, [_response(
        "emote",
        favorite_character={"name": "苏九", "reason": "护短"},
        annoying_character={"name": "王管家", "reason": "工具感"},
    )])
    result = bs.analyze(root)
    annotations = result["survey_chapters"][0]["annotations"]
    assert annotations["favorite_character"][0]["name"] == "苏九"
    assert annotations["annoying_character"][0]["name"] == "王管家"
    assert result["questions"] == []


def test_survey_malformed_and_missing_previous_chapter_are_safe(tmp_path):
    root = _project(tmp_path, ["一"], {})
    with open(os.path.join(root, "评分", "reader_survey_第03章.json"), "w",
              encoding="utf-8") as f:
        f.write("{broken json")
    _write_survey(root, 5, [_response("logic", recall="随便复述点什么内容")])
    with open(os.path.join(root, "评分", "reader_survey_第06章.json"), "w",
              encoding="utf-8") as f:
        json.dump({"chapter": 6, "answers": ["旧字段"]}, f, ensure_ascii=False)
    result = bs.analyze(root)
    assert result["ran"] is True
    assert result["alerts"] == []
    assert not [
        item for item in result["questions"]
        if item["type"] == "review_recall_surface_overlap"
    ]
