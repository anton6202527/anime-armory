# -*- coding: utf-8 -*-
"""test_behavioral_signals — 行为式读者模拟确定性度量。

Run: cd skills/novel-simulate/scripts && python3 -m pytest test_behavioral_signals.py
"""
import json
import os

import behavioral_signals as bs


def test_guess_diversity_high_when_divergent():
    preds = ["主角当场反杀镇北王", "师妹其实是暗桩会倒戈", "朝廷钦差突然到场搅局"]
    assert bs.guess_diversity(preds) > 0.8


def test_guess_diversity_low_when_same_direction():
    preds = ["主角当场反杀镇北王", "主角会当场反杀镇北王的", "主角当场就反杀了镇北王"]
    assert bs.guess_diversity(preds) < 0.55


def test_surprise_low_when_predicted():
    preds = ["主角当场反杀镇北王", "师妹倒戈"]
    actual = "第二日，主角当场反杀镇北王，血溅五步。"
    assert bs.surprise_score(preds, actual) < 0.6


def test_surprise_high_when_unexpected():
    preds = ["主角当场反杀镇北王", "师妹倒戈"]
    actual = "谁也没想到，圣旨到了：全城戒严，科举提前，主角被点为主考官。"
    assert bs.surprise_score(preds, actual) > 0.7


def _project(tmp_path, chapter_texts, predictions_by_ch):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    os.makedirs(os.path.join(root, "评分"), exist_ok=True)
    for i, t in enumerate(chapter_texts, 1):
        with open(os.path.join(root, "章节", f"第{i:02d}章.md"), "w", encoding="utf-8") as f:
            f.write(t)
    for ch, preds in predictions_by_ch.items():
        with open(os.path.join(root, "评分", f"reader_predictions_第{ch:02d}章.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"schema_version": 1, "kind": "novel_reader_predictions",
                       "chapter": ch, "predictions": [{"persona": "rookie", "text": p} for p in preds]},
                      f, ensure_ascii=False)
    return root


def test_analyze_flags_predictable_and_collapsed(tmp_path):
    same = ["主角当场反杀镇北王", "主角会当场反杀镇北王", "主角当场就反杀镇北王",
            "主角当场反杀了镇北王", "主角必当场反杀镇北王"]
    root = _project(tmp_path,
                    ["第一章正文。", "翌日校场，主角当场反杀镇北王，血溅五步。"],
                    {1: same})
    res = bs.analyze(root)
    assert res["ran"] is True and res["blocking"] == 0
    types = {a["type"] for a in res["alerts"]}
    assert "suspense_collapse" in types      # 全员同向 → 悬念塌缩
    assert "predictable_plot" in types       # 真实下一章被猜中 → 剧情太顺


def test_analyze_skips_without_predictions(tmp_path):
    res = bs.analyze(str(tmp_path))
    assert res["ran"] is False and "reader_predictions" in res["skipped"]


def test_insufficient_predictions_not_judged(tmp_path):
    root = _project(tmp_path, ["一", "二"], {1: ["只有一条", "两条"]})
    res = bs.analyze(root)
    assert res["ran"] is True and res["alerts"] == []
    assert res["chapters"][0].get("insufficient") is True


# ---------- beta reader 六问问卷聚合 ----------

def test_recall_containment_high_when_faithful():
    prev = "第二日校场比武，主角当场反杀镇北王，血溅五步，师妹的暗桩身份就此暴露。"
    recall = "主角校场反杀镇北王，师妹身份暴露。"
    assert bs.recall_containment(recall, prev) > 0.5


def test_recall_containment_low_when_wrong():
    prev = "第二日校场比武，主角当场反杀镇北王，血溅五步。"
    recall = "皇帝驾崩，太子登基，京城大乱。"
    assert bs.recall_containment(recall, prev) < 0.25
    assert bs.recall_containment("", prev) is None
    assert bs.recall_containment("有内容", "") is None


def _resp(persona, bored=None, confused=None, disbelief=None, recall=""):
    return {"persona": persona, "bored": bored, "confused": confused,
            "disbelief": disbelief, "recall": recall}


def _write_survey(root, ch, responses):
    os.makedirs(os.path.join(root, "评分"), exist_ok=True)
    with open(os.path.join(root, "评分", f"reader_survey_第{ch:02d}章.json"),
              "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "kind": "novel_reader_survey",
                   "chapter": ch, "responses": responses}, f, ensure_ascii=False)


def test_survey_bored_run_and_confusion_spike(tmp_path):
    root = _project(tmp_path, ["一", "二", "三"], {})
    for ch in (2, 3):
        _write_survey(root, ch, [
            _resp("rookie", bored={"span": "排位流水账"}),
            _resp("logic", bored="中段走神"),
            _resp("emote"),
        ])
    _write_survey(root, 1, [
        _resp("rookie", confused={"span": "谁在说话"}),
        _resp("logic", confused="时间线乱了"),
        _resp("emote"),
    ])
    res = bs.analyze(root)
    assert res["ran"] is True and res["blocking"] == 0
    by_type = {a["type"]: a for a in res["alerts"]}
    assert by_type["reader_bored_run"]["chapters"] == [2, 3]
    assert "排位流水账" in by_type["reader_bored_run"]["note"]
    assert by_type["reader_confusion_spike"]["chapter"] == 1


def test_survey_bored_single_chapter_not_a_run(tmp_path):
    root = _project(tmp_path, ["一", "二"], {})
    _write_survey(root, 1, [_resp("rookie", bored="水"), _resp("logic", bored="水")])
    res = bs.analyze(root)
    assert not [a for a in res["alerts"] if a["type"] == "reader_bored_run"]


def test_survey_disbelief_and_recall_failure(tmp_path):
    root = _project(tmp_path,
                    ["第二日校场比武，主角当场反杀镇北王，血溅五步。", "二"], {})
    _write_survey(root, 2, [
        _resp("logic", disbelief={"span": "林昭突然原谅仇人", "characters": ["林昭"]},
              recall="皇帝驾崩太子登基京城大乱"),
        _resp("emote", recall="似乎是宫里出了什么事来着"),
    ])
    res = bs.analyze(root)
    by_type = {a["type"]: a for a in res["alerts"]}
    assert by_type["reader_disbelief"]["characters"] == ["林昭"]
    assert by_type["recall_failure"]["chapter"] == 1  # 复述的是上一章
    assert res["survey_chapters"][0]["responses"] == 2


def test_survey_healthy_no_alerts_and_minority_not_flagged(tmp_path):
    root = _project(tmp_path,
                    ["第二日校场比武，主角当场反杀镇北王，血溅五步。", "二"], {})
    _write_survey(root, 2, [
        _resp("rookie", bored="有点水", recall="主角校场反杀镇北王"),  # 1/3 不过半
        _resp("logic", recall="主角当场反杀镇北王血溅五步"),
        _resp("emote", recall="校场比武反杀镇北王"),
    ])
    res = bs.analyze(root)
    assert res["ran"] is True and res["alerts"] == []


def test_survey_malformed_and_missing_prev_chapter_skipped(tmp_path):
    root = _project(tmp_path, ["一"], {})
    with open(os.path.join(root, "评分", "reader_survey_第03章.json"), "w",
              encoding="utf-8") as f:
        f.write("{broken json")
    # 第 5 章问卷但无第 4 章正文 → recall 不判；旧 schema（无 responses）→ 跳过
    _write_survey(root, 5, [_resp("logic", recall="随便复述点什么内容")])
    with open(os.path.join(root, "评分", "reader_survey_第06章.json"), "w",
              encoding="utf-8") as f:
        json.dump({"chapter": 6, "answers": ["旧字段"]}, f, ensure_ascii=False)
    res = bs.analyze(root)
    assert res["ran"] is True
    assert not [a for a in res["alerts"] if a["type"] == "recall_failure"]
