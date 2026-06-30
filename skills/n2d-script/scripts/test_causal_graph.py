"""cd skills/n2d-script/scripts && python -m pytest test_causal_graph.py"""
import causal_graph as cg


def test_signal_helpers():
    assert cg.is_reversal_or_surprise("他竟然是卧底", False)
    assert cg.is_reversal_or_surprise("平平无奇的一天", True)      # 有反转标记
    assert not cg.is_reversal_or_surprise("她端起茶", False)
    assert cg.is_self_caused("因为你骗了我，我才离开")
    assert cg.leads_with_consequence("所以她决定复仇")
    assert cg.has_choice("她决定动手")


def test_build_edges_consequence_and_choice():
    texts = ["她发现了账本", "于是她去报官", "官府不理"]
    edges = cg.build_causal_edges(texts)
    assert (0, 1) in edges          # "于是"引导 → 0→1


def test_build_edges_evidence_to_reveal():
    texts = ["看鞋。看血。再看那碗茶，茶面一丝都没晃。", "回来的，是剥了他脸、披着他皮的东西。"]
    edges = cg.build_causal_edges(texts)
    assert (0, 1) in edges          # 证据链 → 揭穿/反转


def test_contrivance_candidate_flagged():
    texts = ["平静的午后", "她喝着茶", "他突然拔刀相向", "众人惊散"]
    marks = [False, False, False, False]
    edges = cg.build_causal_edges(texts)
    cands = cg.contrivance_candidates(texts, marks, edges)
    assert 2 in cands               # "突然拔刀"无前因、非自解释 → 天降候选


def test_caused_reversal_not_flagged():
    # 反转有前因（选择→后果 + 自解释）→ 不报
    texts = ["她决定摊牌", "于是当众揭穿，原来管家才是真凶"]
    marks = [False, True]
    edges = cg.build_causal_edges(texts)
    cands = cg.contrivance_candidates(texts, marks, edges)
    assert 1 not in cands           # 有 0→1 入边


def test_evidence_reversal_not_flagged():
    texts = ["看鞋。看血。再看那碗茶，茶面一丝都没晃。", "回来的，是剥了他脸、披着他皮的东西。"]
    marks = [False, True]
    edges = cg.build_causal_edges(texts)
    cands = cg.contrivance_candidates(texts, marks, edges)
    assert 1 not in cands


def test_causal_coverage():
    texts = ["她决定查案", "于是突然发现线索", "竟然另有隐情"]
    marks = [False, False, False]
    edges = cg.build_causal_edges(texts)
    caused, big = cg.causal_coverage(texts, marks, edges)
    assert big == 2                 # 两个惊变词 beat
    assert caused >= 1              # beat1 有入边(0→1)


def test_audit_short_episode_skipped():
    beats = [(1, "旁白", "突然", False), (2, "甲", "竟然", False)]
    assert cg.audit_beats(beats) == []   # <4 beat 跳过


def test_audit_flags_contrivance_and_low_coverage():
    beats = [
        (1, "旁白", "平静的清晨", False),
        (2, "甲", "他突然倒地不起", False),
        (3, "乙", "她竟然认得这毒", False),
        (4, "丙", "没想到门外站着仇人", False),
    ]
    findings = cg.audit_beats(beats)
    codes = {c for _s, c, _m in findings}
    assert "contrivance_candidate" in codes
    assert "low_causal_coverage" in codes
    assert all(s == "warn" for s, _c, _m in findings)


def test_idiot_plot_signal():
    # 误会 + 不沟通 → 降智候选
    assert cg.idiot_plot_signal("她误会了，却百口莫辩，没机会解释")
    # 不沟通 + 无视铁证
    assert cg.idiot_plot_signal("他不肯说，对方也证据确凿地不信")
    # 单独"以为"不报（高频词，需配合不沟通/无视）
    assert not cg.idiot_plot_signal("我以为你会来")
    assert not cg.idiot_plot_signal("她端起茶盏")


def test_audit_flags_idiot_plot():
    beats = [
        (1, "旁白", "她决定去找他对质", False),
        (2, "甲", "他误会了她，却不容分说，不肯解释", False),
        (3, "乙", "众人散去", False),
        (4, "丙", "她还是没能说清", False),
    ]
    codes = {c for _s, c, _m in cg.audit_beats(beats)}
    assert "idiot_plot_candidate" in codes
