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
