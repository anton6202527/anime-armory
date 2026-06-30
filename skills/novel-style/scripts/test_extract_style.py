# -*- coding: utf-8 -*-
"""
test for extract_style.
Run from this directory:
    cd skills/novel-style/scripts && python3 -m pytest test_extract_style.py
"""
import extract_style as es


SHORT = "他来了。她走了。风停了。雨下了。剑出鞘。血溅地。人倒下。天亮了。"
LONG = ("当那道身影在漫天飞舞的暗金色光雨之中缓缓转过身来的时候所有人都屏住了呼吸"
        "因为他们终于意识到这个看似柔弱的女子竟然才是真正掌控全局的那个人而他们不过是棋子。"
        "她抬起手指轻轻一点周遭的空间便如同被无形巨力撕裂开来露出深不见底的幽暗裂隙。")


def test_fingerprint_basic_fields():
    fp = es.fingerprint(SHORT)
    assert fp["schema_version"] == 1
    assert fp["sentence_count"] >= 6
    assert "syntax_profile" in fp and "dialogue_ratio" in fp
    assert "lexicon_anchor" in fp and "rhythm" in fp
    assert fp["style_source_rights"]["status"] == "project-demo"


def test_fingerprint_records_style_source_rights():
    fp = es.fingerprint(
        SHORT,
        source_rights="licensed",
        style_source_name="样本集",
        style_source_author="授权作者",
        authorization_note="合同授权",
    )
    rights = fp["style_source_rights"]
    assert rights["status"] == "licensed"
    assert rights["source_author"] == "授权作者"
    assert "未授权姓名式复刻" in rights["policy"]


def test_short_text_is_fast_pulse():
    fp = es.fingerprint(SHORT)
    assert fp["syntax_profile"]["short_sentence_ratio"] > 0.8
    assert fp["rhythm"]["pace_tag"] == "fast_pulse"


def test_long_text_is_dense():
    fp = es.fingerprint(LONG)
    assert fp["syntax_profile"]["avg_sentence_length"] > 24
    assert fp["rhythm"]["pace_tag"] == "dense"


def test_dialogue_ratio_detects_quotes():
    no_dlg = es.fingerprint("他沉默地走过长街没有说一句话。")
    with_dlg = es.fingerprint("他停下脚步，「你究竟是谁」，声音冷得像冰。")
    assert with_dlg["dialogue_ratio"] > no_dlg["dialogue_ratio"]
    assert with_dlg["dialogue_ratio"] > 0


def test_compare_identical_no_drift():
    fp = es.fingerprint(SHORT)
    res = es.compare(fp, fp)
    assert res["drift_score"] == 0.0
    assert res["drift_flag"] is False
    assert res["flags"] == []


def test_compare_short_vs_long_flags_drift():
    res = es.compare(es.fingerprint(SHORT), es.fingerprint(LONG))
    assert res["drift_flag"] is True
    assert res["drift_score"] > 0
    metrics = {f["metric"] for f in res["flags"]}
    # 句长与节奏标签必然漂
    assert "avg_sentence_length" in metrics or "pace_tag" in metrics


def test_lexicon_filters_stopwords():
    fp = es.fingerprint("剑气剑气剑气纵横，剑气剑气贯长虹，剑气所至。")
    terms = {x["term"] for x in fp["lexicon_anchor"]}
    assert "剑气" in terms
    # 纯停用词不应成为锚点
    assert "的了" not in terms
