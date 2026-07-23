# -*- coding: utf-8 -*-
"""test_prose_craft_audit — 传统行文手艺 + 篇章叙事指纹。

Run: cd skills/novel-review/scripts && python3 -m pytest test_prose_craft_audit.py
"""
import os

import prose_craft_audit as pca


# ── 纯函数 ──────────────────────────────────────────────────────────────────

def test_split_narration_dialogue():
    text = "沈砚推门而入。\n「你来了。」\n他点点头。\n裴决说：「坐。」"
    narration, dialogue = pca.split_narration_dialogue(text)
    assert len(narration) == 2 and len(dialogue) == 2


def test_filter_words_only_in_narration():
    narration = ["他看到刀光一闪。", "他感到一阵寒意。"]
    assert pca.filter_word_count(narration) == 2


def test_adverb_dialogue_tag():
    assert pca.adverb_tag_count("他冷冷地说道：「滚。」") == 1
    assert pca.adverb_tag_count("他说：「滚。」") == 0


def test_moralizing_tail_weighted():
    body = "打斗。" * 100
    tail = "这一刻，他终于明白，守护才是最重要的。"
    assert pca.moralizing_hits(body + tail) > pca.moralizing_hits(tail + body)


def test_physio_requires_cooccurrence():
    assert pca.physio_cooccur_count("他的心脏猛地一紧。") == 1
    assert pca.physio_cooccur_count("刀刺进胸口，血流了一地。") == 0   # 打斗字面，无生理动词共现
    assert pca.physio_cooccur_count("他很生气。") == 0


def test_setting_mirror_cooccurrence():
    assert pca.setting_mirror_count("天色暗了下来，正如他此刻的心情。") == 1
    assert pca.setting_mirror_count("天色暗了下来。他很难过。") == 0   # 不同句不算


def test_info_dump_paragraph_detection():
    dump = ("这个世界的力量体系分为九个境界，每个境界之下又有等级之分，规则是灵气决定等级，"
            "等级决定地位，而宗门的体系则依据规则运转，代价与限制皆有定数，境界突破的条件是"
            "灵气积累与悟性，等级越高代价越大，这是这个世界最根本的规则与体系设定。"
            "所谓境界，即是灵气在经脉中的容量等级；所谓宗门，即是按境界划分权力的组织体系；"
            "每一次突破都要付出代价，每一层等级都对应新的规则限制，逻辑严密，环环相扣。")
    assert len(pca.info_dump_paragraphs(dump)) == 1
    scene = "沈砚推门而入，「你来了」，裴决抬起头。" * 8
    assert pca.info_dump_paragraphs(scene) == []


# ── analyze() 集成 ──────────────────────────────────────────────────────────

def _project(tmp_path, texts):
    d = os.path.join(str(tmp_path), "章节")
    os.makedirs(d, exist_ok=True)
    for i, t in enumerate(texts, 1):
        with open(os.path.join(d, f"第{i:02d}章.md"), "w", encoding="utf-8") as f:
            f.write(t)
    return str(tmp_path)


def test_analyze_flags_filter_words_and_is_advisory(tmp_path):
    filtered = "他看到刀光。他感到寒意。他注意到脚步。他发现血迹。他意识到危险。他觉得不对。\n" * 6
    root = _project(tmp_path, [filtered])
    res = pca.analyze(root)
    assert res["ran"] is True and res["blocking"] == 0
    assert any(a["type"] == "filter_words" for a in res["alerts"])
    assert all(a["severity"] in ("建议级", "info") for a in res["alerts"])


def test_analyze_clean_prose_no_alerts(tmp_path):
    clean = ("刀光一闪。沈砚侧身，刀锋擦着耳际钉进门板。\n"
             "「好快的刀。」\n"
             "裴决收势而立，指节抵着刀背。院里的灯笼晃了两晃。\n") * 6
    root = _project(tmp_path, [clean])
    res = pca.analyze(root)
    assert res["ran"] is True
    assert [a for a in res["alerts"] if a["type"] == "filter_words"] == []


def test_analyze_moralizing_ending_bookwide(tmp_path):
    ch = "打斗。" * 60 + "这一刻，他终于明白，守护才是最重要的。人生就是不断失去。"
    root = _project(tmp_path, [ch, ch])
    res = pca.analyze(root)
    assert any(a["type"] == "moralizing_ending" for a in res["alerts"])


def test_analyze_empty_skips(tmp_path):
    res = pca.analyze(str(tmp_path))
    assert res["ran"] is False


# ── C 组：句节奏 / 拐杖短语 / 回声 / 视角跳头 ────────────────────────────────

def test_sentence_lengths_splits():
    lens = pca.sentence_lengths(["他走了。她也走了！天黑了？"])
    assert lens == [3, 4, 3]


def test_rhythm_stats_monotone_low_cv():
    rs = pca.rhythm_stats([10] * 40)
    assert rs["cv"] == 0.0 and rs["max_run"] == 40


def test_rhythm_stats_varied_high_cv():
    rs = pca.rhythm_stats([3, 25, 8, 40, 5, 18, 2, 33] * 5)
    assert rs["cv"] > 0.3


def test_crutch_phrase_counts():
    text = "他忍不住皱了皱眉，又忍不住叹气。"
    counts = pca.crutch_phrase_counts(text)
    assert counts.get("忍不住") == 2 and counts.get("皱了皱眉") == 1


def test_echo_hits_proximity():
    # "青铜灯" 在近窗内复读 3 次 → 回声
    text = "他举起青铜灯。青铜灯的光很暗。她盯着青铜灯看了很久。"
    hits = pca.echo_hits(text, window=60, min_repeats=3)
    assert any(h["phrase"] == "青铜灯" for h in hits)


def test_echo_hits_far_apart_ok():
    text = "他举起青铜灯。" + "无关内容。" * 60 + "青铜灯又亮了。" + "填充。" * 60 + "青铜灯灭了。"
    hits = pca.echo_hits(text, window=60, min_repeats=3)
    assert not any(h["phrase"] == "青铜灯" for h in hits)


def test_echo_excludes_roster_names():
    text = "沈砚之走了。沈砚之回来了。沈砚之又走了。"
    hits = pca.echo_hits(text, exclude=("沈砚之",), window=60, min_repeats=3)
    assert hits == []


def test_interiority_subjects_roster():
    text = "沈砚心想，此人必有蹊跷。裴决暗道不好。沈砚心道：稳住。"
    subs = pca.interiority_subjects(text, roster=("沈砚", "裴决"))
    assert subs == {"沈砚": 2, "裴决": 1}


def test_interiority_fallback_without_roster():
    text = "沈砚心想，此人必有蹊跷。"
    subs = pca.interiority_subjects(text)
    assert "沈砚" in subs
