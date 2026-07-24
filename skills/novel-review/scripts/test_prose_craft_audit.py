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


# ── D 组：开场滥调 / 段首同型 ───────────────────────────────────────────────

def test_slush_opening_hits_in_window():
    hits = pca.slush_opening_hits("他从梦中醒来，窗外阳光明媚。")
    cats = {h["category"] for h in hits}
    assert "梦醒起床" in cats and "天气开场" in cats


def test_slush_opening_ignores_mid_chapter():
    # "睁开眼"落在窗口外是正常动作，不算滥调开场
    text = "刀光一闪，他侧身避开。" * 40 + "他缓缓睁开眼。"
    assert pca.slush_opening_hits(text, head_chars=300) == []


def test_paragraph_openers_pronoun_and_name():
    text = "他推门而入。\n他转身关门。\n「你来了。」\n沈砚坐下。\n沈默降临。"
    openers = pca.paragraph_openers(text)
    # 代词取首字（"他"="他"），对白段跳过，2 字取整（"沈砚"≠"沈默"）
    assert openers == ["他", "他", "沈砚", "沈默"]


def test_opener_max_run():
    run, val = pca.opener_max_run(["他", "他", "他", "沈砚", "他"])
    assert run == 3 and val == "他"
    assert pca.opener_max_run([]) == (0, None)


def test_analyze_flags_slush_opening_first_chapter(tmp_path):
    ch1 = "他从梦中醒来，揉了揉眼睛。\n" + "刀光一闪。沈砚侧身。裴决收势。\n" * 10
    root = _project(tmp_path, [ch1])
    res = pca.analyze(root)
    hits = [a for a in res["alerts"] if a["type"] == "slush_opening_cliche"]
    assert len(hits) == 1 and hits[0]["chapter"] == 1
    assert "第一页退稿" in hits[0]["note"]        # 第 1 章文案更重
    assert res["blocking"] == 0


def test_analyze_flags_paragraph_opening_monotony(tmp_path):
    ch = "他推门而入，看清了屋内的陈设与来客。\n他走到桌边，倒了一杯冷茶一饮而尽。\n" \
         "他坐下来，慢条斯理地擦拭刀锋。\n他抬起头，目光落在窗外的更漏上。\n" \
         "他忽然笑了，笑声惊起了檐下宿鸟。\n"
    root = _project(tmp_path, [ch])
    res = pca.analyze(root)
    hits = [a for a in res["alerts"] if a["type"] == "paragraph_opening_monotony"]
    assert len(hits) == 1 and hits[0]["opener"] == "他" and hits[0]["run"] >= 4


def test_analyze_varied_paragraph_openers_no_alert(tmp_path):
    ch = "他推门而入。\n刀光一闪而过。\n沈砚侧身避开。\n烛火晃了两晃。\n裴决收势而立。\n"
    root = _project(tmp_path, [ch])
    res = pca.analyze(root)
    assert [a for a in res["alerts"] if a["type"] == "paragraph_opening_monotony"] == []


# ── E 组：段落极端形态 ───────────────────────────────────────────────────────

def test_paragraph_extremes_detects_wall_and_frag_run():
    wall = "灵气在他经脉里奔涌不休，" * 40   # 单段 ≥400 字
    frags = "\n".join(["一声。", "又一声。", "更近了。", "停了。", "再响。", "门外。", "廊下。", "床前。"])
    walls, frag_best = pca.paragraph_extremes(wall + "\n" + frags)
    assert len(walls) == 1 and frag_best == 8


def test_paragraph_extremes_dialogue_lines_skipped_not_breaking():
    # 对话行天然短：跳过且不断叙述碎段 run
    lines = ["一声。", "「谁？」", "又一声。", "「别动。」", "更近了。", "停了。", "再响。", "门外。", "廊下。", "床前。"]
    _, frag_best = pca.paragraph_extremes("\n".join(lines))
    assert frag_best == 8


def test_paragraph_extremes_normal_prose_clean():
    normal = "他推门而入，看清了屋内的陈设与来客，烛火在穿堂风里晃了两晃才稳住。\n" * 5
    walls, frag_best = pca.paragraph_extremes(normal)
    assert walls == [] and frag_best == 0


def test_analyze_flags_fragmented_paragraph_run(tmp_path):
    frags = "\n".join(["一声。", "又一声。", "更近了。", "停了。", "再响。", "门外。", "廊下。", "床前。", "灭了。"])
    root = _project(tmp_path, [frags])
    res = pca.analyze(root)
    hits = [a for a in res["alerts"] if a["type"] == "fragmented_paragraph_run"]
    assert len(hits) == 1 and hits[0]["run"] >= 8 and res["blocking"] == 0


def test_analyze_flags_wall_of_text(tmp_path):
    ch = ("灵气在他经脉里奔涌不休，" * 40 + "\n") * 2
    root = _project(tmp_path, [ch])
    res = pca.analyze(root)
    assert any(a["type"] == "wall_of_text" for a in res["alerts"])
