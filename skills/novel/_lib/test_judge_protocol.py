# -*- coding: utf-8 -*-
"""cd skills/novel/_lib && python3 -m pytest test_judge_protocol.py"""
import judge_protocol as jp


def test_position_stable_winner():
    assert jp.position_stable_winner("稿A", "稿A") == "稿A"   # 两序一致
    assert jp.position_stable_winner("稿A", "稿B") is None     # 翻面=位置偏
    assert jp.position_stable_winner("稿A", None) is None
    assert jp.position_stable_winner("", "") is None


def test_consensus_accepts_only_unanimous_stable():
    judgements = [
        {"judge": "m1", "ab_winner": "稿A", "ba_winner": "稿A"},
        {"judge": "m2", "ab_winner": "稿A", "ba_winner": "稿A"},
    ]
    r = jp.pairwise_consensus(judgements)
    assert r["decision"] == "稿A" and r["winner"] == "稿A"
    assert r["stable_votes"] == 2 and r["position_biased"] == 0


def test_consensus_position_bias_drops_to_tie():
    # 单判官且翻面 → 稳定票0 < 2 → tie
    judgements = [{"judge": "m1", "ab_winner": "稿A", "ba_winner": "稿B"}]
    r = jp.pairwise_consensus(judgements)
    assert r["decision"] == jp.TIE
    assert r["position_biased"] == 1 and r["stable_votes"] == 0


def test_consensus_disagreement_is_tie():
    judgements = [
        {"judge": "m1", "ab_winner": "稿A", "ba_winner": "稿A"},
        {"judge": "m2", "ab_winner": "稿B", "ba_winner": "稿B"},
    ]
    r = jp.pairwise_consensus(judgements)
    assert r["decision"] == jp.TIE and r["winner"] is None
    assert "分歧" in r["reason"]


def test_single_judge_insufficient_even_if_stable():
    judgements = [{"judge": "m1", "ab_winner": "稿A", "ba_winner": "稿A"}]
    r = jp.pairwise_consensus(judgements, min_judges=2)
    assert r["decision"] == jp.TIE  # 单判官不足，需 dual


def test_zscore_normalize_removes_leniency():
    z = jp.zscore_normalize([8, 8, 8])      # 严判官但无区分 → 全0
    assert z == [0.0, 0.0, 0.0]
    z2 = jp.zscore_normalize([1, 5, 9])
    assert z2[0] < 0 < z2[2] and abs(sum(z2)) < 1e-6


def test_aggregate_rubric_flags_high_variance():
    panel = {
        "m1": {"hook": 9, "logic": 5},
        "m2": {"hook": 8, "logic": 5},
        "m3": {"hook": 2, "logic": 5},   # hook 上judge严重分歧
    }
    agg = jp.aggregate_rubric(panel, variance_threshold=1.0)
    assert agg["hook"]["confidence"] == "low"   # 高方差 → 降信
    assert agg["logic"]["confidence"] == "ok"   # 一致


def test_debias_verdict_end_to_end():
    judgements = [
        {"judge": "m1", "ab_winner": "稿A", "ba_winner": "稿A"},
        {"judge": "m2", "ab_winner": "稿A", "ba_winner": "稿A"},
    ]
    panel = {"m1": {"hook": 9}, "m2": {"hook": 8}}
    out = jp.debias_verdict(judgements, panel=panel)
    assert out["winner"] == "稿A" and out["confidence"] == "high"
    # 有高方差准则 → medium
    out2 = jp.debias_verdict(judgements, panel={"m1": {"hook": 9}, "m2": {"hook": 2}})
    assert out2["confidence"] == "medium"
    # tie → low
    out3 = jp.debias_verdict([{"judge": "m1", "ab_winner": "稿A", "ba_winner": "稿B"}])
    assert out3["decision"] == jp.TIE and out3["confidence"] == "low"
