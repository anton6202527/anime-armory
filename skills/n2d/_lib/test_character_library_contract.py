from n2d_const import (
    CHARACTER_LIBRARY_CORE_VIEWS,
    CHARACTER_LIBRARY_TIER_CORE,
    CHARACTER_LIBRARY_TIER_MINIMAL,
    CHARACTER_LIBRARY_TIER_PARTIAL,
    CHARACTER_LIBRARY_TIER_STANDARD,
    character_library_tier_for_record,
    character_library_tier_is_at_least,
    infer_character_library_tier,
    identity_review_binding_fingerprint,
    identity_review_contract_for_view,
    identity_review_required_criteria,
    identity_reviewed_at_errors,
    identity_reviewer_appears_automated,
    required_character_library_views,
)


def test_core_contract_includes_rear_three_quarter_as_independent_view() -> None:
    assert CHARACTER_LIBRARY_CORE_VIEWS == (
        "front",
        "three_quarter",
        "side",
        "rear_three_quarter",
        "back",
    )
    assert required_character_library_views(CHARACTER_LIBRARY_TIER_CORE) == CHARACTER_LIBRARY_CORE_VIEWS


def test_story_weight_cannot_self_report_a_lower_tier() -> None:
    record = {
        "scope": "贯穿全篇女主",
        "narrative_tier": "核心长线",
        "library_tier": CHARACTER_LIBRARY_TIER_MINIMAL,
        "planned_episode_count": 2,
    }
    assert character_library_tier_for_record(record) == CHARACTER_LIBRARY_TIER_CORE


def test_explicit_upgrade_is_preserved() -> None:
    record = {
        "scope": "第1集具名短线角色",
        "library_tier": CHARACTER_LIBRARY_TIER_STANDARD,
        "planned_episode_count": 1,
    }
    assert character_library_tier_for_record(record) == CHARACTER_LIBRARY_TIER_STANDARD


def test_episode_thresholds_and_reuse_scope_are_deterministic() -> None:
    assert infer_character_library_tier(episode_count=10) == CHARACTER_LIBRARY_TIER_CORE
    assert infer_character_library_tier(episode_count=3) == CHARACTER_LIBRARY_TIER_STANDARD
    assert infer_character_library_tier(scope="第1集起复用") == CHARACTER_LIBRARY_TIER_STANDARD
    assert infer_character_library_tier(episode_count=1) == CHARACTER_LIBRARY_TIER_MINIMAL
    assert infer_character_library_tier(scope="只作为本集公务角色，不抢主角视觉重心") == CHARACTER_LIBRARY_TIER_MINIMAL
    assert character_library_tier_for_record({"core": True}) == CHARACTER_LIBRARY_TIER_CORE


def test_registry_external_observed_episode_count_can_only_raise_minimum_tier() -> None:
    forged_low = {
        "scope": "第1集具名短线角色",
        "library_tier": CHARACTER_LIBRARY_TIER_MINIMAL,
        "planned_episode_count": 1,
    }
    assert character_library_tier_for_record(
        forged_low, observed_episode_count=3
    ) == CHARACTER_LIBRARY_TIER_STANDARD
    assert character_library_tier_for_record(
        forged_low, observed_episode_count=10
    ) == CHARACTER_LIBRARY_TIER_CORE
    # 缺独立索引保持历史行为，不把 unknown 猜成复现角色。
    assert character_library_tier_for_record(forged_low) == CHARACTER_LIBRARY_TIER_MINIMAL


def test_restricted_partial_is_not_ranked_as_a_downgrade() -> None:
    record = {
        "scope": "核心长线但只显示肩背剪影",
        "library_tier": CHARACTER_LIBRARY_TIER_PARTIAL,
        "face_policy": "no_full_face",
        "restricted_partial_contract": {
            "status": "approved",
            "reason": "创意设定为全程帘后肩背剪影，本季不露脸。",
            "reviewer": "director:fixture",
            "allowed_parts": ["shoulder_back", "silhouette"],
            "face_policy": "no_full_face",
        },
    }
    assert character_library_tier_for_record(record) == CHARACTER_LIBRARY_TIER_PARTIAL
    assert not character_library_tier_is_at_least(
        CHARACTER_LIBRARY_TIER_PARTIAL, CHARACTER_LIBRARY_TIER_MINIMAL
    )


def test_core_cannot_self_report_restricted_partial_without_approved_contract() -> None:
    record = {
        "scope": "贯穿全篇女主",
        "library_tier": CHARACTER_LIBRARY_TIER_PARTIAL,
        "tier": CHARACTER_LIBRARY_TIER_PARTIAL,
        "face_policy": "no_full_face",
        "restricted_partial": True,
    }
    assert character_library_tier_for_record(record) == CHARACTER_LIBRARY_TIER_CORE


def test_one_off_partial_is_compatible_but_recurring_cannot_bypass_without_contract() -> None:
    named = {
        "id": "CHAR_GUEST",
        "scope": "第1集具名角色",
        "library_tier": CHARACTER_LIBRARY_TIER_PARTIAL,
        "face_policy": "no_full_face",
        "restricted_partial": True,
    }
    assert character_library_tier_for_record(named) == CHARACTER_LIBRARY_TIER_PARTIAL
    assert character_library_tier_for_record(
        named, observed_episode_count=3
    ) == CHARACTER_LIBRARY_TIER_STANDARD

    group = dict(named, id="GROUP_MARKET", scope="集市群像")
    assert character_library_tier_for_record(group) == CHARACTER_LIBRARY_TIER_PARTIAL


def test_restricted_partial_contract_must_match_face_policy_and_cannot_allow_face() -> None:
    base = {
        "scope": "贯穿全篇神秘主角",
        "library_tier": CHARACTER_LIBRARY_TIER_PARTIAL,
        "face_policy": "no_full_face",
        "restricted_partial_contract": {
            "status": "approved",
            "reason": "本季只以帘后剪影和手部动作建立身份。",
            "reviewer": "director:fixture",
            "allowed_parts": ["hand", "silhouette"],
            "face_policy": "no_clear_facial_features",
        },
    }
    assert character_library_tier_for_record(base) == CHARACTER_LIBRARY_TIER_CORE

    base["restricted_partial_contract"]["face_policy"] = "no_full_face"
    base["restricted_partial_contract"]["allowed_parts"] = ["full_face", "silhouette"]
    assert character_library_tier_for_record(base) == CHARACTER_LIBRARY_TIER_CORE


def test_identity_review_contract_is_single_source_and_fail_closed() -> None:
    assert identity_review_contract_for_view("front") == "n2d_turnaround_view_review_v1"
    assert identity_review_contract_for_view("expression") == "n2d_expression_review_v1"
    assert "full_body_head_to_foot_visible" in identity_review_required_criteria("side")
    assert "expression_readable_without_identity_drift" in identity_review_required_criteria("expression")
    assert identity_reviewer_appears_automated("codex-agent") is True
    assert identity_reviewer_appears_automated("角色设定组/终审A") is False
    assert identity_reviewed_at_errors("2026-07-14T12:00:00") == (
        "reviewed_at_timezone_missing",
    )
    assert identity_reviewed_at_errors("2026-07-14T12:00:00+08:00") == ()
    assert len(identity_review_binding_fingerprint(
        character_id="CHAR_01",
        form="常态",
        library_tier="core_full",
        view="front",
        path="出图/共享/图片/front.png",
        png_sha256="a" * 64,
    )) == 64
