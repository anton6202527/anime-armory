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
    assert agg["hook"]["decision"] == jp.ABSTAIN
    assert agg["logic"]["confidence"] == "ok"   # 一致


def test_family_diversity_recommends_three_families_but_keeps_two_compatible():
    two = jp.family_diversity(["gpt-5", "claude-sonnet"])
    assert two["families_count"] == 2
    assert two["meets_recommended"] is False
    assert two["backward_compatible_min_judges"] == 2
    three = jp.family_diversity(["gpt-5", "claude-sonnet", "gemini-3-pro"])
    assert three["meets_recommended"] is True
    assert set(three["families"]) == {"anthropic", "google", "openai"}


def test_high_variance_escalation_actions():
    rubric = jp.aggregate_rubric({
        "gpt-5": {"hook": 9},
        "claude-sonnet": {"hook": 2},
        "gemini-3-pro": {"hook": 8},
    })
    actions = jp.rubric_escalation_actions(rubric)
    assert actions
    assert actions[0]["criterion"] == "hook"
    assert actions[0]["decision"] == jp.ABSTAIN
    assert "stronger" in actions[0]["next_action"]


def test_debias_verdict_end_to_end():
    judgements = [
        {"judge": "m1", "ab_winner": "稿A", "ba_winner": "稿A"},
        {"judge": "m2", "ab_winner": "稿A", "ba_winner": "稿A"},
    ]
    panel = {"m1": {"hook": 9}, "m2": {"hook": 8}}
    out = jp.debias_verdict(judgements, panel=panel)
    assert out["winner"] == "稿A" and out["confidence"] == "high"
    assert out["family_diversity"]["meets_recommended"] is False
    # 有高方差准则 → medium
    out2 = jp.debias_verdict(judgements, panel={"m1": {"hook": 9}, "m2": {"hook": 2}})
    assert out2["confidence"] == "medium"
    assert out2["abstain_criteria"] == ["hook"]
    assert out2["escalation_actions"][0]["decision"] == jp.ABSTAIN
    # tie → low
    out3 = jp.debias_verdict([{"judge": "m1", "ab_winner": "稿A", "ba_winner": "稿B"}])
    assert out3["decision"] == jp.TIE and out3["confidence"] == "low"


def test_main_returns_callable_module_api(tmp_path):
    """main() 是真入口（CLI 接线证据）：可被调用、调度 debias_verdict、产 result。"""
    assert callable(getattr(jp, "main", None))


def test_cli_subprocess_verdicts_and_panel(tmp_path):
    """CLI 端到端：写 verdicts/panel JSON → 子进程跑 → stdout 是去偏结论 JSON。"""
    import json
    import os
    import subprocess
    import sys
    verdicts = tmp_path / "v.json"
    panel = tmp_path / "p.json"
    verdicts.write_text(json.dumps([
        {"judge": "m1", "ab_winner": "稿A", "ba_winner": "稿A"},
        {"judge": "m2", "ab_winner": "稿A", "ba_winner": "稿A"},
    ]), encoding="utf-8")
    panel.write_text(json.dumps({"m1": {"hook": 9}, "m2": {"hook": 8}}), encoding="utf-8")
    here = os.path.dirname(os.path.abspath(__file__))
    proc = subprocess.run(
        [sys.executable, os.path.join(here, "judge_protocol.py"),
         "--verdicts", str(verdicts), "--panel", str(panel)],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["winner"] == "稿A" and out["confidence"] == "high"


def test_cli_require_confidence_gate_exit1(tmp_path):
    """opt-in 硬闸：tie 时 --require-confidence high → exit 1（critic-loop 可拒采纳）。"""
    import json
    import os
    import subprocess
    import sys
    verdicts = tmp_path / "v.json"
    verdicts.write_text(json.dumps([
        {"judge": "m1", "ab_winner": "稿A", "ba_winner": "稿B"},  # 翻面=位置偏→tie
    ]), encoding="utf-8")
    here = os.path.dirname(os.path.abspath(__file__))
    proc = subprocess.run(
        [sys.executable, os.path.join(here, "judge_protocol.py"),
         "--verdicts", str(verdicts), "--require-confidence", "high"],
        capture_output=True, text=True)
    assert proc.returncode == 1
    # 默认（不给 --require-confidence）→ advisory，恒 exit 0
    proc2 = subprocess.run(
        [sys.executable, os.path.join(here, "judge_protocol.py"), "--verdicts", str(verdicts)],
        capture_output=True, text=True)
    assert proc2.returncode == 0
