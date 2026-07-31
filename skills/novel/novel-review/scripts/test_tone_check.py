#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_tone_check.py — tone_check 纯函数 + 对账逻辑单测

cd skills/novel/novel-review/scripts && python3 -m pytest test_tone_check.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tone_check as tc


# ── emotion_scores ────────────────────────────────────────────────────────
def test_emotion_scores_counts_keywords():
    text = "她笑了笑，心里满是欢喜。"
    scores = tc.emotion_scores(text)
    assert scores.get("喜悦", 0) >= 2  # 笑×2 + 欢/喜
    # 只保留命中的情绪，无信号情绪不出现
    assert "愤怒" not in scores


def test_emotion_scores_empty_text():
    assert tc.emotion_scores("") == {}
    assert tc.emotion_scores(None) == {}


def test_emotion_scores_custom_lexicon():
    lex = {"A": ["甲"], "B": ["乙"]}
    assert tc.emotion_scores("甲甲乙", lexicon=lex) == {"A": 2, "B": 1}


# ── dominant_emotion ──────────────────────────────────────────────────────
def test_dominant_emotion_sad_passage():
    text = "泪水滑落，她心如刀绞，悲痛欲绝，泣不成声，绝望地哭着。"
    assert tc.dominant_emotion(text) == "悲伤"


def test_dominant_emotion_tense_passage():
    text = "危机逼近，千钧一发，他屏息凝重，剑拔弩张，气氛紧绷到了极点。"
    assert tc.dominant_emotion(text) == "紧张"


def test_dominant_emotion_no_signal():
    assert tc.dominant_emotion("桌上放着一本书。") is None
    assert tc.dominant_emotion("") is None


# ── map_target_emotion ────────────────────────────────────────────────────
def test_map_target_emotion_english_and_chinese():
    assert tc.map_target_emotion("Light, comedic, fast-paced") == "喜悦"
    assert tc.map_target_emotion("Gritty, oppressive, sensory-heavy") == "紧张"
    assert tc.map_target_emotion("curiosity") == "好奇悬疑"
    assert tc.map_target_emotion("悲伤") == "悲伤"
    assert tc.map_target_emotion("无法识别的标签xyz") is None
    assert tc.map_target_emotion(None) is None


# ── tone_band ─────────────────────────────────────────────────────────────
def test_tone_band_match_ok():
    assert tc.tone_band("悲伤", "悲伤") == "ok"


def test_tone_band_mismatch_warn():
    assert tc.tone_band("喜悦", "悲伤") == "warn"


def test_tone_band_missing_target_ok():
    assert tc.tone_band("悲伤", None) == "ok"
    assert tc.tone_band(None, "悲伤") == "ok"
    assert tc.tone_band(None, None) == "ok"


def test_tone_band_adjacent_tolerated():
    # 紧张 与 恐惧 邻近 → 容差，不报偏离
    assert tc.tone_band("紧张", "恐惧") == "ok"


# ── target_for_chapter（两种 shape）───────────────────────────────────────
def test_target_for_chapter_arcs_shape():
    data = {"arcs": [
        {"range": "1-50", "arc_name": "初入江湖", "target_vibe": "Light, comedic"},
        {"range": "51-120", "arc_name": "家族覆灭", "target_vibe": "Gritty, oppressive"},
    ]}
    assert tc.target_for_chapter(data, 10) == "Light, comedic"
    assert tc.target_for_chapter(data, 60) == "Gritty, oppressive"
    assert tc.target_for_chapter(data, 999) is None


def test_target_for_chapter_per_chapter_shape():
    data = [
        {"chapter": 1, "target_emotion": "悲伤"},
        {"chapter": 2, "vibe": "curiosity"},
    ]
    assert tc.target_for_chapter(data, 1) == "悲伤"
    assert tc.target_for_chapter(data, 2) == "curiosity"
    assert tc.target_for_chapter(data, 3) is None


# ── analyze（端到端，含优雅跳过）──────────────────────────────────────────
def _mk_project(tmp_path, tone_data, chapters):
    proj = tmp_path / "proj"
    (proj / "设定").mkdir(parents=True)
    (proj / "章节").mkdir(parents=True)
    if tone_data is not None:
        (proj / "设定" / "tone_curve.json").write_text(
            json.dumps(tone_data, ensure_ascii=False), encoding="utf-8")
    for idx, body in chapters:
        (proj / "章节" / f"第{idx:02d}章.txt").write_text(body, encoding="utf-8")
    return str(proj)


def test_analyze_skips_without_tone_curve(tmp_path):
    proj = _mk_project(tmp_path, None, [(1, "随便写点字。")])
    res = tc.analyze(proj)
    assert res["ran"] is False
    assert "tone_curve" in res["skipped"]
    assert res["alerts"] == []


def test_analyze_flags_deviation(tmp_path):
    # 目标=悲伤，实测正文却是浓烈喜悦 → 报 tone_deviation 建议级
    tone = [{"chapter": 1, "target_emotion": "悲伤"}]
    body = "她笑着，满心欢喜，开怀大笑，乐不可支，甜滋滋的。"
    proj = _mk_project(tmp_path, tone, [(1, body)])
    res = tc.analyze(proj)
    assert res["ran"] is True
    devs = [a for a in res["alerts"] if a["type"] == "tone_deviation"]
    assert len(devs) == 1
    a = devs[0]
    assert a["severity"] == "建议级"
    assert a["chapter"] == 1
    assert a["realized"] == "喜悦"
    assert a["target"] == "悲伤"
    assert a["auto"] is True


def test_analyze_no_alert_on_match(tmp_path):
    tone = [{"chapter": 1, "target_emotion": "悲伤"}]
    body = "泪如雨下，悲痛欲绝，绝望地哭泣，心如刀割。"
    proj = _mk_project(tmp_path, tone, [(1, body)])
    res = tc.analyze(proj)
    assert res["ran"] is True
    assert [a for a in res["alerts"] if a["type"] == "tone_deviation"] == []
    ch = res["chapters"][0]
    assert ch["band"] == "ok"
    assert ch["realized"] == "悲伤"


def test_tension_score_calm_vs_tense():
    calm = "他慢慢走过田野，看着夕阳，心里很平静很温暖很柔和。" * 10
    tense = "危机！他猛地转身，紧张地盯着门口——敌人来了？压抑得让人窒息！" * 10
    assert tc.tension_score(calm) < 5
    assert tc.tension_score(tense) >= 5
    assert tc.tension_score("") is None  # 空正文缺信号


def test_write_progression_fills_dominant_and_tension_preserving_human_fields():
    import tempfile
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"))
        os.makedirs(os.path.join(root, "设定"))
        calm = "他慢慢走过田野，看着夕阳，很平静。" * 10
        for i in range(1, 3):
            with open(os.path.join(root, "章节", f"第{i:02d}章.md"), "w", encoding="utf-8") as f:
                f.write(f"# 第{i}章\n{calm}")
        # 预置一条带人工字段的行，回填不应清掉它
        with open(os.path.join(root, "设定", "emotional_progression.json"), "w", encoding="utf-8") as f:
            json.dump({"kind": "novel_emotional_progression", "chapters": [
                {"chapter": 1, "dominant_emotion": "", "tension_score": None,
                 "reader_promise_progress": "主角立志复仇", "next_emotional_debt": "亏欠师父"}]}, f,
                ensure_ascii=False)
        n = tc.write_progression(root)
        assert n == 2
        emo = json.load(open(os.path.join(root, "设定", "emotional_progression.json"), encoding="utf-8"))
        ch1 = next(c for c in emo["chapters"] if c["chapter"] == 1)
        assert ch1["tension_score"] is not None and ch1["auto_measured"] is True
        assert ch1["reader_promise_progress"] == "主角立志复仇"  # 人工字段保留


if __name__ == "__main__":
    sys.exit(os.system(f"python3 -m pytest {os.path.abspath(__file__)} -v"))
