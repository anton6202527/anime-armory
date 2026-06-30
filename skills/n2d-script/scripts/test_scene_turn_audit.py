"""cd skills/n2d-script/scripts && python -m pytest test_scene_turn_audit.py"""
import scene_turn_audit as sc


def test_polarity_and_flips():
    assert sc.emotion_polarity("绝望") == -1
    assert sc.emotion_polarity("扬眉吐气") == 1
    assert sc.emotion_polarity("平静") == 0
    assert sc.count_charge_flips([-1, -1, 1, 1, -1]) == 2
    assert sc.count_charge_flips([-1, 0, 0, -1]) == 0      # 0 不算翻转


def test_setback_then_payoff():
    assert sc.has_setback_then_payoff([-1, -1, 1])
    assert not sc.has_setback_then_payoff([1, 1, -1])      # 先正后负 ≠ 憋→放
    assert not sc.has_setback_then_payoff([1, 1, 1])


def test_reversal_positions():
    assert sc.reversal_positions([True, False, False, False, False]) == [0.0]
    assert sc.reversal_positions([False, False, False, False, True]) == [1.0]


def test_no_turn_all_negative():
    emos = ["委屈", "难过", "绝望", "痛苦", "愤怒", "崩溃"]
    marks = [False] * 6
    codes = {c for _s, c, _m in sc.audit_beats(emos, marks, list(range(6)))}
    assert "no_value_charge_turn" in codes
    assert "all_negative_no_payoff" in codes


def test_healthy_setback_then_payoff_passes():
    emos = ["委屈", "屈辱", "愤怒", "笃定", "扬眉吐气", "释然"]
    marks = [False, False, False, True, False, False]   # 反转在中段
    findings = sc.audit_beats(emos, marks, list(range(6)))
    codes = {c for _s, c, _m in findings}
    assert "no_value_charge_turn" not in codes
    assert "all_negative_no_payoff" not in codes
    assert "reversal_too_early" not in codes


def test_reversal_too_early():
    emos = ["惊", "委屈", "难过", "绝望", "痛苦", "崩溃", "愤怒"]
    marks = [True, False, False, False, False, False, False]   # 反转只在开头
    codes = {c for _s, c, _m in sc.audit_beats(emos, marks, list(range(7)))}
    assert "reversal_too_early" in codes


def test_short_episode_skipped():
    emos = ["难过", "难过"]
    assert sc.audit_beats(emos, [False, False], [0, 1]) == []
