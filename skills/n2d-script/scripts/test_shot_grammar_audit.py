"""cd skills/n2d-script/scripts && python -m pytest test_shot_grammar_audit.py"""
import json

import shot_grammar_audit as sg


def test_scale_rank_aliases():
    assert sg.scale_rank("MS（中景，不撞上一镜）") == 4
    assert sg.scale_rank("CU 特写") == 2
    assert sg.scale_rank("MCU 中近景") == 3      # MCU 不被 CU 子串先吞
    assert sg.scale_rank("ELS establish 定场") == 7
    assert sg.scale_rank("") is None
    assert sg.scale_rank("说话镜") is None


def test_consecutive_same_scale_runs():
    assert sg.consecutive_same_scale_runs([4, 4, 4, 2], 3) == [(0, 2, 4)]
    assert sg.consecutive_same_scale_runs([4, 2, 4, 2], 3) == []
    assert sg.consecutive_same_scale_runs([2, None, 2, 2, 2], 3) == [(2, 4, 2)]   # None 断开


def test_has_establishing_and_spread():
    assert sg.has_establishing([2, 4, 6]) is True
    assert sg.has_establishing([1, 2, 3, 4]) is False
    assert sg.scale_spread([2, 4, 7]) == 5
    assert sg.scale_spread([4, 4, 4]) == 0


def _clip(shot, rhythm=""):
    return {"continuity": {"shot_size": shot}, "rhythm": rhythm}


def test_audit_flags_same_scale_run_and_no_establishing():
    clips = [_clip("MS"), _clip("MS"), _clip("MS"), _clip("MCU")]
    codes = {c for _s, c, _m in sg.audit_clips(clips)}
    assert "same_scale_run" in codes
    assert "no_establishing" in codes


def test_audit_flags_peak_not_closeup():
    clips = [_clip("ELS 定场"), _clip("MS"), _clip("MS", rhythm="爽点·CU硬切")]
    codes = {c for _s, c, _m in sg.audit_clips(clips)}
    assert "peak_not_closeup" in codes      # 爽点镜却是 MS


def test_audit_clean_progression_passes():
    clips = [_clip("ELS 定场"), _clip("MS 中景"), _clip("MCU 中近景"),
             _clip("CU 特写", rhythm="爽点·CU硬切")]
    codes = {c for _s, c, _m in sg.audit_clips(clips)}
    assert "same_scale_run" not in codes
    assert "no_establishing" not in codes
    assert "peak_not_closeup" not in codes
    assert "flat_scale" not in codes


def test_thirty_degree_proxy():
    clips = [_clip("CU 特写 仰拍"), _clip("CU 特写 仰拍")]
    codes = {c for _s, c, _m in sg.audit_clips(clips)}
    assert "thirty_degree_risk" in codes


def test_missing_shot_size_is_info():
    clips = [_clip(""), _clip("说话镜")]
    sevs = {s for s, _c, _m in sg.audit_clips(clips)}
    assert sevs == {"info"}


def test_transition_helpers():
    assert sg.has_expressive_transition(["hard_cut", "j_cut"])
    assert sg.has_expressive_transition(["match_cut"])
    assert not sg.has_expressive_transition(["hard_cut", "", "硬切"])


def _clip_t(shot, transition=""):
    return {"continuity": {"shot_size": shot, "transition": transition}}


def test_monotone_hard_cuts_flagged():
    # 5+ 镜全硬切、零变化型转场 → B2 warn
    clips = [_clip_t("ELS 定场", "hard_cut"), _clip_t("MS 中景", "hard_cut"),
             _clip_t("MCU 中近景", "hard_cut"), _clip_t("CU 特写", "hard_cut"),
             _clip_t("MS 中景", "hard_cut")]
    codes = {c for _s, c, _m in sg.audit_clips(clips)}
    assert "monotone_hard_cuts" in codes


def test_expressive_transition_no_flag():
    clips = [_clip_t("ELS 定场", "hard_cut"), _clip_t("MS 中景", "j_cut"),
             _clip_t("MCU 中近景", "eyeline"), _clip_t("CU 特写", "match_cut"),
             _clip_t("MS 中景", "l_cut")]
    codes = {c for _s, c, _m in sg.audit_clips(clips)}
    assert "monotone_hard_cuts" not in codes
