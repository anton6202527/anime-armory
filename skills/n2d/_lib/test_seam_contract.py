from __future__ import annotations

import seam_contract as sc


def test_only_continuous_take_relay_requires_identical_boundary_frame() -> None:
    assert sc.requires_boundary_frame("continuous_take_relay") is True
    for mode in ("match_on_action", "graphic_match", "eyeline_cut", "reaction_cut", "j_cut", "l_cut", "dissolve", "hard_cut"):
        assert sc.requires_boundary_frame(mode) is False


def test_transition_migration_classifies_without_claiming_explicit_source() -> None:
    result = sc.normalize_seam_mode("", "动作切 match on action", need_endframe=False)
    assert result == {"mode": "match_on_action", "source": "legacy_inferred", "recognized": True}
    assert sc.missing_evidence("match_on_action", {"action_phase_out": "抬手"}) == ("action_phase_in", "screen_direction")
    assert sc.normalize_seam_mode("", "relay")["mode"] == "continuous_take_relay"


def test_graphic_match_is_not_a_relay_and_has_visual_rhyme_evidence() -> None:
    result = sc.normalize_seam_mode("", "match cut 构图匹配")
    assert result["mode"] == "graphic_match"
    assert sc.requires_boundary_frame(result["mode"]) is False
    assert sc.missing_evidence("graphic_match", {"match_element_out": "圆月"}) == (
        "match_element_in", "composition_relation",
    )


def test_end_anchor_is_separate_from_cross_clip_relay() -> None:
    assert sc.needs_end_anchor({"continuity": {"seam_mode": "continuous_take_relay"}}) is True
    assert sc.needs_end_anchor({"continuity": {"seam_mode": "hard_cut", "need_endframe": True}}) is False
    assert sc.needs_end_anchor({"continuity": {"seam_mode": "hard_cut", "end_anchor_required": True}}) is True
    assert sc.needs_end_anchor({"continuity": {"seam_mode": "graphic_match", "endframe_png": "tail.png"}}) is True
    assert sc.needs_end_anchor({"continuity": {"need_endframe": True}}) is True
    assert sc.needs_end_anchor({
        "endframe_png": "stale.png",
        "continuity": {"need_endframe": False, "endframe_exempt_reason": "末镜不使用尾锚"},
    }) is False
    assert sc.needs_end_anchor({"continuity": {}}) is False


def test_placeholder_evidence_cannot_be_signed_as_editorial_decision() -> None:
    assert sc.missing_evidence("hard_cut", {"editorial_intent": "待补：editorial_intent"}) == ("editorial_intent",)
    assert sc.missing_evidence("hard_cut", {"editorial_intent": "用冲击性直切把反应提前半拍"}) == ()
