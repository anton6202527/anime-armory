#!/usr/bin/env python3
"""Shared spectacle/action contracts for n2d.

This module is the single n2d-line source for high-dynamic and large-scale
shot contracts.  Script audits, review gates, and model routing should import
these fields instead of drifting separate fight/chase/flight definitions.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from n2d_const import SHOT_TYPE_KEYWORDS
except ImportError:  # pragma: no cover - package import fallback
    from .n2d_const import SHOT_TYPE_KEYWORDS

TEMPLATE_BASE_FIELDS: Tuple[str, ...] = (
    "template_id",
    "beats",
    "blocking",
    "camera_rule",
    "continuity_must",
    "negative",
)

ACTION_CHOREOGRAPHY_SHOT_TYPES: Tuple[str, ...] = (
    "fight_exchange",
    "chase",
    "magic_burst",
    "flight",
    "mount_ride",
    "vehicle_ride",
    "vessel_flight",
    "road_vehicle",
    "stealth_stalk",
)
PREMIUM_SPECTACLE_FIELDS: Tuple[str, ...] = (
    "keyframe_plan",
    "post_cue_points",
    "physics_guard",
)
ACTION_CHOREOGRAPHY_COMMON_FIELDS: Tuple[str, ...] = (
    "beats",
    "speed_curve",
    "spatial_path",
    "camera_path",
    "readability_beats",
    "degrade_plan",
) + PREMIUM_SPECTACLE_FIELDS
ACTION_CHOREOGRAPHY_SPECIFIC_FIELDS: Dict[str, Tuple[str, ...]] = {
    "fight_exchange": (
        "attack_path",
        "impact_frame",
        "contact_points",
        "force_direction",
        "recovery_beat",
    ),
    "magic_burst": (
        "charge_frame",
        "release_frame",
        "effect_asset",
        "energy_path",
        "collision_or_apex_frame",
        "power_shift",
    ),
    "chase": (
        "screen_direction",
        "distance_curve",
        "obstacle_beats",
        "parallax_layers",
        "overtake_or_escape_beat",
    ),
    "flight": (
        "flight_path",
        "altitude_curve",
        "pose_lock",
        "parallax_layers",
        "mount_or_cloud_lock",
    ),
    "mount_ride": (
        "mount_contact",
        "gait_cycle",
        "screen_direction",
        "parallax_layers",
        "harness_lock",
    ),
    "vehicle_ride": (
        "vehicle_lock",
        "wheel_rotation",
        "harness_lock",
        "screen_direction",
        "parallax_layers",
    ),
    "vessel_flight": (
        "vehicle_lock",
        "flight_path",
        "altitude_curve",
        "screen_direction",
        "parallax_layers",
    ),
    "road_vehicle": (
        "vehicle_lock",
        "wheel_rotation",
        "driver_control_lock",
        "lane_lock",
        "traffic_flow",
        "screen_direction",
        "parallax_layers",
    ),
    "stealth_stalk": (
        "screen_direction",
        "distance_curve",
        "occlusion_layers",
        "light_shadow_lock",
        "reveal_or_hide_beat",
        "parallax_layers",
    ),
}

SPECTACLE_TEMPLATE_FIELDS: Dict[str, Tuple[str, ...]] = {
    "fight_exchange": TEMPLATE_BASE_FIELDS + (
        "attack_path",
        "impact_frame",
        "action_scope",
        "contact_points",
        "force_direction",
        "screen_direction",  # 越轴锁：双人近身搏杀是 180° 越轴最高发区，必须锁银幕方向（与 chase/flight 同源）
        "speed_curve",
        "spatial_path",
        "camera_path",
        "readability_beats",
        "recovery_beat",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "chase": TEMPLATE_BASE_FIELDS + (
        "screen_direction",
        "distance_curve",
        "obstacle_beats",
        "speed_curve",
        "spatial_path",
        "camera_path",
        "parallax_layers",
        "readability_beats",
        "overtake_or_escape_beat",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "magic_burst": TEMPLATE_BASE_FIELDS + (
        "charge_frame",
        "release_frame",
        "effect_asset",
        "energy_path",
        "collision_or_apex_frame",
        "power_shift",
        "vfx_asset_lock",
        "intensity_curve",
        "speed_curve",
        "spatial_path",
        "camera_path",
        "screen_direction",  # 越轴锁：斗法对轰双方法术轴线必须锁，否则爆发帧两边乱飞、命中读不清
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "flight": TEMPLATE_BASE_FIELDS + (
        "pose_lock",
        "background_motion",
        "altitude_path",
        "speed_curve",
        "flight_path",
        "altitude_curve",
        "camera_path",
        "spatial_path",
        "parallax_layers",
        "mount_or_cloud_lock",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "mount_ride": TEMPLATE_BASE_FIELDS + (
        "mount_contact",
        "gait_cycle",
        "harness_lock",
        "speed_curve",
        "spatial_path",
        "camera_path",
        "screen_direction",
        "parallax_layers",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "vehicle_ride": TEMPLATE_BASE_FIELDS + (
        "vehicle_lock",
        "wheel_rotation",
        "harness_lock",
        "speed_curve",
        "spatial_path",
        "camera_path",
        "screen_direction",
        "parallax_layers",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "vessel_flight": TEMPLATE_BASE_FIELDS + (
        "vehicle_lock",
        "flight_path",
        "altitude_path",
        "altitude_curve",
        "speed_curve",
        "spatial_path",
        "camera_path",
        "screen_direction",
        "parallax_layers",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "road_vehicle": TEMPLATE_BASE_FIELDS + (
        "vehicle_lock",
        "wheel_rotation",
        "driver_control_lock",
        "lane_lock",
        "traffic_flow",
        "speed_curve",
        "spatial_path",
        "camera_path",
        "screen_direction",
        "parallax_layers",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "stealth_stalk": TEMPLATE_BASE_FIELDS + (
        "screen_direction",
        "distance_curve",
        "occlusion_layers",
        "light_shadow_lock",
        "speed_curve",
        "spatial_path",
        "camera_path",
        "parallax_layers",
        "reveal_or_hide_beat",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "screen_insert": TEMPLATE_BASE_FIELDS + (
        "device_lock",
        "screen_content_ref",
        "text_layer",
        "overlay_content",
        "reflection_policy",
        "hand_pose_lock",
        "readability_beats",
    ),
    "evidence_search": TEMPLATE_BASE_FIELDS + (
        "clue_object",
        "search_path",
        "reveal_frame",
        "evidence_chain",
        "hand_pose_lock",
        "occlusion_order",
        "contamination_guard",
        "readability_beats",
    ),
    "tribulation_breakthrough": TEMPLATE_BASE_FIELDS + (
        "tribulation_stage",
        "lightning_path",
        "impact_frame",
        "shield_lock",
        "breakthrough_light",
        "vfx_asset_lock",
        "intensity_curve",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "meditation_cultivation": TEMPLATE_BASE_FIELDS + (
        "posture_lock",
        "breath_cycle",
        "energy_flow",
        "aura_vfx_lock",
        "inner_state_beat",
        "environment_stillness",
        "micro_motion",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "alchemy_forging": TEMPLATE_BASE_FIELDS + (
        "furnace_or_forge_lock",
        "material_sequence",
        "process_stage_ladder",
        "flame_control",
        "heat_curve",
        "material_state_ladder",
        "tool_hand_pose",
        "product_lock",
        "reveal_frame",
        "vfx_asset_lock",
        "success_or_failure_beat",
        "failure_or_success_safety",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "dual_cultivation": TEMPLATE_BASE_FIELDS + (
        "adult_consent_lock",
        "non_explicit_boundary",
        "paired_posture_lock",
        "distance_boundary",
        "contact_points",
        "energy_circulation",
        "breath_sync",
        "aura_vfx_lock",
        "relationship_state",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "kiss_or_near_kiss": TEMPLATE_BASE_FIELDS + (
        "age_context_lock",
        "consent_lock",
        "non_explicit_boundary",
        "relationship_state",
        "approach_path",
        "face_angle_lock",
        "contact_or_near_contact_frame",
        "hand_position_lock",
        "body_overlap_limit",
        "breath_pause",
        "micro_expression_beats",
        "readability_beats",
        "degrade_plan",
    ) + PREMIUM_SPECTACLE_FIELDS,
    "array_ritual": TEMPLATE_BASE_FIELDS + (
        "array_geometry_lock",
        "activation_steps",
        "symbol_layer_policy",
        "caster_positions",
        "energy_flow",
        "purpose_lock",
        "vfx_asset_lock",
        "readability_beats",
    ),
    "soul_manifestation": TEMPLATE_BASE_FIELDS + (
        "body_soul_identity_lock",
        "soul_form_lock",
        "opacity_curve",
        "emergence_path",
        "host_body_lock",
        "conflict_or_probe_target",
        "readability_beats",
        "degrade_plan",
    ),
    "realm_portal": TEMPLATE_BASE_FIELDS + (
        "portal_lock",
        "source_world_anchor",
        "destination_anchor",
        "entry_exit_path",
        "body_continuity_lock",
        "transition_vfx",
        "readability_beats",
        "degrade_plan",
    ),
    "contract_summon": TEMPLATE_BASE_FIELDS + (
        "summon_entity_lock",
        "contract_mark",
        "ritual_anchor",
        "summon_path",
        "scale_relationship",
        "ownership_transition",
        "readability_beats",
        "degrade_plan",
    ),
    "talent_test": TEMPLATE_BASE_FIELDS + (
        "test_artifact_lock",
        "measurement_rule",
        "result_stage",
        "overlay_policy",
        "crowd_reaction_chain",
        "vfx_asset_lock",
        "readability_beats",
    ),
}

COMPACT_NARRATIVE_TEMPLATE_FIELDS: Dict[str, Tuple[str, ...]] = {
    # Vertical n2d episodes often need tight narrative-compression templates
    # that are not high-motion spectacles but still carry prompt-critical
    # blocking, beat, and continuity contracts.
    "task_order": TEMPLATE_BASE_FIELDS + (
        "post_cue_points",
        "character_slots",
        "same_frame_policy",
        "overlap_rules",
        "face_priority",
    ),
    "compressed_flashback": TEMPLATE_BASE_FIELDS + (
        "post_cue_points",
        "character_slots",
        "same_frame_policy",
        "overlap_rules",
        "face_priority",
    ),
    "night_route_choice": TEMPLATE_BASE_FIELDS + (
        "post_cue_points",
    ),
    "labor_montage": TEMPLATE_BASE_FIELDS + (
        "post_cue_points",
        "degrade_plan",
    ),
    "object_discovery": TEMPLATE_BASE_FIELDS + (
        "evidence_chain",
        "post_cue_points",
        "vfx_rule",
    ),
    # Narrative/directing templates are prompt-critical even though they are
    # not motion spectacles.  Keeping their required fields in the shared
    # contract lets storyboard backfill and review gates use one schema.
    "dialogue_shot_reverse": TEMPLATE_BASE_FIELDS + (
        "axis",
        "eyeline",
        "shot_pairing",
        "screen_sides",
        "coverage_order",
        "camera_coverage",
        "lens_height_distance_match",
        "crossing_axis_policy",
        "buffer_or_reestablishing",
    ),
    "reveal_reaction_chain": TEMPLATE_BASE_FIELDS + (
        "reveal_object",
        "knowledge_order",
        "reaction_beats",
        "cut_point",
    ),
    "relationship_turn": TEMPLATE_BASE_FIELDS + (
        "relationship_state_before",
        "turning_action",
        "subtext",
        "relationship_state_after",
    ),
    "multi_character_same_frame": TEMPLATE_BASE_FIELDS + (
        "character_slots",
        "face_priority",
        "overlap_rules",
    ),
    "ensemble_blocking": TEMPLATE_BASE_FIELDS + (
        "screen_positions",
        "focus_hierarchy",
        "crowd_simplification",
    ),
    "multi_person_blocking": TEMPLATE_BASE_FIELDS + (
        "screen_positions",
        "speaker_focus",
        "crowd_simplification",
    ),
}

LARGE_ESTABLISHING_FIELDS: Tuple[str, ...] = (
    "geography_map",
    "scale_reference",
    "parallax_planes",
    "landmark_anchor",
    "camera_path",
    "establishing_progression",
    "reuse_asset_id",
)

SPECTACLE_KINDS: Tuple[str, ...] = (
    "fight_exchange",
    "chase",
    "flight",
    "mount_ride",
    "vehicle_ride",
    "vessel_flight",
    "road_vehicle",
    "stealth_stalk",
    "screen_insert",
    "evidence_search",
    "tribulation_breakthrough",
    "magic_burst",
    "meditation_cultivation",
    "alchemy_forging",
    "dual_cultivation",
    "kiss_or_near_kiss",
    "array_ritual",
    "soul_manifestation",
    "realm_portal",
    "contract_summon",
    "talent_test",
    "large_establishing",
)

SPECTACLE_PLAN_KIND = "n2d_spectacle_plan"
SPECTACLE_SEQUENCE_PLAN_KIND = "n2d_spectacle_sequence_plan"
SPECTACLE_PROBE_PACK_KIND = "n2d_spectacle_probe_pack"
SPECTACLE_BACKEND_BENCHMARK_KIND = "n2d_spectacle_backend_benchmark"
ACTION_EDIT_CUES_KIND = "n2d_action_edit_cues"
SPECTACLE_VIDEO_QC_KIND = "n2d_spectacle_video_qc"
MOTION_REFERENCE_LIBRARY_KIND = "n2d_motion_reference_library"
SCENE_LAYER_PACK_KIND = "n2d_scene_layer_pack"
TRAJECTORY_CONTROLLER_PLAN_KIND = "n2d_trajectory_controller_plan"

GENERIC_TEMPLATE_VALUES = frozenset({
    "generic",
    "general",
    "normal",
    "ordinary",
    "custom",
    "unknown",
    "none",
    "null",
    "普通",
    "普通镜头",
    "常规镜头",
    "通用",
    "自由镜头",
})

LARGE_ESTABLISHING_RE = re.compile(
    r"(大场景|大场面|宏大|全景|全貌|鸟瞰|航拍|俯瞰|广角远景|万人|千军|战场|城池|城门|"
    r"宗门大殿|山门全景|云海|秘境|仙宫|天宫|巨型|wide establishing|epic|vast|aerial)",
    re.I,
)
STEALTH_STALK_WEAK_AMBIENCE_TERMS = frozenset({
    "暗处", "暗影", "脚步声", "走廊尽头", "手电", "手电光", "光束扫过", "shadow",
})
STEALTH_STALK_STRONG_TERMS = (
    "尾随", "跟踪", "潜入", "潜行", "躲藏", "偷窥", "窥视", "门缝",
    "stalk", "stalking", "stealth", "sneak",
)
MEDITATION_CULTIVATION_WEAK_TERMS = frozenset({"闭关"})
MEDITATION_CULTIVATION_STRONG_TERMS = (
    "打坐", "静坐", "入定", "冥想", "吐纳", "调息", "运功", "周天", "内视",
    "修炼", "蒲团", "灵气入体", "气海", "丹田",
    "meditation", "cultivation meditation", "breathing exercise",
)


def field_missing(value: Any) -> bool:
    if value in (None, ""):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, tuple, dict, set)) and not value:
        return True
    return False


def clip_blob(clip: Mapping[str, Any]) -> str:
    """Freeform visual/action text used for spectacle inference.

    Do not scan structural fields such as character_ids, subtitle_lines,
    entity_schedule, or auto anchor reasons: tokens like ``CHAR_*`` contain
    ``car`` and ability names like ``潜行`` can describe information gained,
    not an actual stealth shot.
    """
    parts: List[str] = []
    for key in (
        "label",
        "scene",
        "description",
        "summary",
        "action",
        "visual",
        "画面",
        "镜头",
        "template",
    ):
        value = clip.get(key)
        if isinstance(value, (str, int, float)):
            parts.append(str(value))
    for key in ("large_scene_contract", "spectacle_contract"):
        value = clip.get(key)
        if isinstance(value, Mapping):
            parts.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
    shots = clip.get("shots")
    if isinstance(shots, list):
        for shot in shots:
            if not isinstance(shot, Mapping):
                continue
            for key in ("desc", "description", "video_prompt", "camera", "action", "visual", "画面", "镜头"):
                value = shot.get(key)
                if isinstance(value, (str, int, float)):
                    parts.append(str(value))
    return " ".join(parts)


def _has_any(text: str, words: Iterable[str]) -> bool:
    low = text.lower()
    for word in words:
        token = str(word).strip().lower()
        if not token:
            continue
        if token.isascii() and re.fullmatch(r"[a-z0-9_+-]+", token):
            if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", low):
                return True
        elif token in low:
            return True
    return False


def _probable_stealth_stalk(text: str, keywords: Iterable[str]) -> bool:
    """Avoid classifying generic low-light staging as a stealth-stalk shot."""
    if not _has_any(text, keywords):
        return False
    if _has_any(text, STEALTH_STALK_STRONG_TERMS):
        return True
    # "暗处/脚步声/手电" are often ambience/light cues in prison or night
    # scenes.  They need an active stalking/hiding verb before taking on the
    # heavier stealth-stalk contract.
    if _has_any(text, STEALTH_STALK_WEAK_AMBIENCE_TERMS):
        return False
    return True


def _probable_meditation_cultivation(text: str, keywords: Iterable[str]) -> bool:
    """Avoid treating a closed-door retreat reference as a visible cultivation shot."""
    if not _has_any(text, keywords):
        return False
    if _has_any(text, MEDITATION_CULTIVATION_STRONG_TERMS):
        return True
    if _has_any(text, MEDITATION_CULTIVATION_WEAK_TERMS):
        return False
    return True


def infer_spectacle_type(clip: Mapping[str, Any]) -> Optional[str]:
    """Return the spectacle/template kind when a clip needs structured handling."""
    template = str(clip.get("template") or "").strip()
    if template in SPECTACLE_TEMPLATE_FIELDS:
        return template
    if template in {"large_establishing", "epic_establishing"}:
        return "large_establishing"
    if template and template.lower() not in GENERIC_TEMPLATE_VALUES:
        # An explicit non-spectacle template is the stronger signal.  Keyword
        # fallback is for untemplated/generic legacy clips only; otherwise
        # dialogue/reveal/ensemble shots get misclassified by incidental words
        # such as "shadow", "spirit root", or "beast".
        return None

    text = clip_blob(clip)
    for shot_type, keywords in SHOT_TYPE_KEYWORDS:
        if shot_type == "stealth_stalk":
            if _probable_stealth_stalk(text, keywords):
                return shot_type
            continue
        if shot_type == "meditation_cultivation":
            if _probable_meditation_cultivation(text, keywords):
                return shot_type
            continue
        if shot_type in SPECTACLE_TEMPLATE_FIELDS and _has_any(text, keywords):
            return shot_type
    if LARGE_ESTABLISHING_RE.search(text):
        return "large_establishing"
    return None


def action_choreography_required_fields(shot_type: str) -> Tuple[str, ...]:
    if shot_type not in ACTION_CHOREOGRAPHY_SHOT_TYPES:
        return ()
    return ACTION_CHOREOGRAPHY_COMMON_FIELDS + ACTION_CHOREOGRAPHY_SPECIFIC_FIELDS[shot_type]


def spectacle_required_fields(kind: str) -> Tuple[str, ...]:
    if kind in SPECTACLE_TEMPLATE_FIELDS:
        return SPECTACLE_TEMPLATE_FIELDS[kind]
    if kind in COMPACT_NARRATIVE_TEMPLATE_FIELDS:
        return COMPACT_NARRATIVE_TEMPLATE_FIELDS[kind]
    if kind == "large_establishing":
        return LARGE_ESTABLISHING_FIELDS
    return ()


# 战斗视觉盛宴·建议字段（advisory·缺=WARN 不阻断·促 prompt 与下游继承）——四轴在 apex 同帧撞点：
#   combat_micro_expression 表情：命中/受击/发力帧的 FACS 微表情（咬牙/狰狞/痛呼·AU4眉压+AU7睑紧+AU38鼻翼），
#                                 治"表情只在对白近景、打斗脸是空的"。
#   secondary_motion        动作物理：发丝/衣摆/碎屑顺攻击方向甩出 + 落地扬尘（治"激烈动作里布料冻住"的假）。
#   apex_light              光线：命中/爆发帧的 motivated 闪光 + apex 轮廓光/边缘光（把主体从暗背景拔出·打击感），
#                                 给 scene_consistency.verify_impact_frames 的 >15% 亮度涌动一个**有意目标**。
SPECTACLE_ADVISORY_FIELDS: Dict[str, Tuple[str, ...]] = {
    "fight_exchange": ("combat_micro_expression", "secondary_motion", "apex_light"),
    "magic_burst": ("combat_micro_expression", "secondary_motion", "apex_light"),
}


def spectacle_advisory_fields(kind: str) -> Tuple[str, ...]:
    """战斗镜建议字段（非阻断·缺则 WARN）：表情/二级运动/apex 光效——让四轴在命中帧汇聚成视觉盛宴。"""
    return SPECTACLE_ADVISORY_FIELDS.get(kind, ())


def missing_fields(record: Mapping[str, Any], fields: Iterable[str]) -> List[str]:
    return [field for field in fields if field_missing(record.get(field))]


def motion_control_inputs_for_spectacle(kind: str) -> Tuple[str, ...]:
    if kind == "fight_exchange":
        return ("pose_sequence", "depth_sequence", "instance_masks", "contact_map", "camera_path")
    if kind == "chase":
        return ("pose_sequence", "depth_sequence", "camera_path", "spatial_path", "parallax_layers")
    if kind == "magic_burst":
        return ("depth_sequence", "camera_path", "spatial_path", "vfx_layers", "parallax_layers")
    if kind == "flight":
        return ("pose_sequence", "depth_sequence", "camera_path", "spatial_path", "parallax_layers")
    if kind == "mount_ride":
        return ("pose_sequence", "depth_sequence", "instance_masks", "contact_map", "camera_path", "spatial_path", "parallax_layers")
    if kind == "vehicle_ride":
        return ("depth_sequence", "camera_path", "spatial_path", "parallax_layers")
    if kind == "vessel_flight":
        return ("depth_sequence", "camera_path", "spatial_path", "parallax_layers")
    if kind == "road_vehicle":
        return ("depth_sequence", "camera_path", "spatial_path", "parallax_layers")
    if kind == "stealth_stalk":
        return ("pose_sequence", "depth_sequence", "camera_path", "spatial_path", "parallax_layers")
    if kind == "tribulation_breakthrough":
        return ("depth_sequence", "camera_path", "vfx_layers")
    if kind == "meditation_cultivation":
        return ("pose_sequence", "depth_sequence", "vfx_layers")
    if kind == "alchemy_forging":
        return ("depth_sequence", "camera_path", "vfx_layers", "parallax_layers")
    if kind == "dual_cultivation":
        return ("pose_sequence", "depth_sequence", "instance_masks", "contact_map", "vfx_layers", "camera_path")
    if kind == "kiss_or_near_kiss":
        return ("pose_sequence", "depth_sequence", "instance_masks", "contact_map", "camera_path")
    if kind == "soul_manifestation":
        return ("pose_sequence", "depth_sequence", "instance_masks", "camera_path")
    if kind == "realm_portal":
        return ("depth_sequence", "camera_path", "spatial_path", "vfx_layers")
    if kind == "contract_summon":
        return ("depth_sequence", "camera_path", "spatial_path", "vfx_layers")
    if kind == "large_establishing":
        return ("camera_path", "depth_sequence", "parallax_layers")
    return ()


# ── 动作节拍预算（Veo「一 clip 一主导动作」+ 打斗拆 2–3 拍）────────────────────────────────
# 高动态镜最常见的崩法是「一镜塞完整攻防回合」：模型把攻击+格挡+反击+命中挤进一条 clip，
# 物理引擎会乱（多个冲突动作同时发生）。把动作文字归到几个互斥的「节拍类别」，一镜跨越的类别越多，
# 越该按 beat 拆镜。词典是启发式（中英关键词），消费方应以 warn 为主、production 交付边界再升 block。
ACTION_BEAT_LEXICON: Dict[str, Tuple[str, ...]] = {
    "attack": (
        "出拳", "挥拳", "挥剑", "挥刀", "劈", "斩", "刺", "踢出", "扫腿", "突进", "冲撞", "进攻", "攻击",
        "出招", "施法", "射出", "掷出", "扑向", "punch", "strike", "slash", "kick", "lunge", "thrust", "swing",
    ),
    "block": (
        "格挡", "招架", "格开", "架住", "举盾", "护住", "闪避", "侧闪", "后撤", "躲开", "翻滚避开",
        "block", "parry", "guard", "dodge", "evade", "deflect",
    ),
    "counter": (
        "反击", "回击", "反打", "还击", "借力反", "顺势反", "反手", "counter", "riposte", "counterattack",
    ),
    "impact": (
        "命中", "击中", "打中", "劈中", "斩中", "踢中", "砸中", "撞上", "击飞", "打飞", "踢飞", "贯穿",
        "破防", "倒地", "吐血", "hit", "impact", "land the", "knock", "smash",
    ),
}

# 单个动作节拍可读下限（秒）：低于此，命中帧/受力方向来不及读清（启发式·env/选择点可调）。
MIN_ACTION_BEAT_SECONDS = 1.2
# 一镜跨越的节拍类别数达到此值，视为「一镜塞了完整攻防回合」，应拆 beat。
ACTION_BEAT_CATEGORY_SPLIT_THRESHOLD = 3


def action_beat_categories(text: str) -> List[str]:
    """文字命中了哪些互斥动作节拍类别（attack/block/counter/impact）。纯函数·可测。"""
    low = str(text or "").lower()
    hits: List[str] = []
    for cat, words in ACTION_BEAT_LEXICON.items():
        if any(str(w).strip().lower() in low for w in words if str(w).strip()):
            hits.append(cat)
    return hits


def beat_decomposition(kind: str) -> List[Dict[str, Any]]:
    """该奇观类型推荐的逐拍拆镜（一拍一 clip，相机简单）。供 sequence_plan/gate/script 共用。"""
    plans = {
        "fight_exchange": [
            {"beat": "setup_attack", "intent": "起手/突进，锁攻击方向与力的来源", "camera": "简单跟随，勿叠运镜"},
            {"beat": "impact", "intent": "命中帧硬约束：接触点+受力方向可读，hit_stop 2 帧", "camera": "稳定，留命中帧"},
            {"beat": "react_recover", "intent": "受击反应/收招，交代攻防转换", "camera": "反打或反应特写"},
        ],
        "magic_burst": [
            {"beat": "charge", "intent": "蓄力帧锁颜色/来源/手势或武器，特效资产先入库", "camera": "近中景或手部/武器特写"},
            {"beat": "release", "intent": "释放路径只保留一条 energy_path，首尾/中段锚住方向", "camera": "顺能量方向推进或侧向跟随"},
            {"beat": "collision_or_apex", "intent": "撞点/剑气峰值/护盾破裂单独可读，留 hit_stop 或闪白", "camera": "稳定或撞点 CU"},
            {"beat": "aftermath", "intent": "余波、尘、衣摆、地裂和角色状态交代结果", "camera": "反应或拉远留白"},
        ],
        "chase": [
            {"beat": "approach", "intent": "追逃距离曲线起点，锁 screen_direction", "camera": "跟拍同一主方向"},
            {"beat": "obstacle", "intent": "障碍/变向一个结果，速度交给前景与视差", "camera": "加速后切"},
            {"beat": "overtake_or_escape", "intent": "拉开或逼近的结算拍", "camera": "cut_on_motion"},
        ],
        "flight": [
            {"beat": "takeoff", "intent": "起飞/腾空，锁 pose 与御剑/云形", "camera": "仰角起势"},
            {"beat": "cruise", "intent": "巡航，速度交给云层/山体视差", "camera": "侧向横移"},
            {"beat": "arrive_or_maneuver", "intent": "抵达或变向一个机动", "camera": "推进或环绕一次"},
        ],
        "mount_ride": [
            {"beat": "mount_establish", "intent": "交代骑手、坐骑尺度和接触点", "camera": "中远景侧向建立"},
            {"beat": "gait_cycle", "intent": "锁一个步态循环，速度交给尘土/草木/披风", "camera": "侧向跟拍"},
            {"beat": "turn_or_arrive", "intent": "转向、跃过障碍或停步结算", "camera": "切反应或低角度"},
        ],
        "vehicle_ride": [
            {"beat": "vehicle_establish", "intent": "交代马车/载具外形、马匹和缰绳连接", "camera": "侧向或三分之四建立"},
            {"beat": "rolling_motion", "intent": "锁车厢不变，轮转/马蹄/尘土制造速度", "camera": "低角度跟拍"},
            {"beat": "obstacle_or_stop", "intent": "颠簸、转弯、急停或抵达一个结果", "camera": "动作切或反应镜"},
        ],
        "vessel_flight": [
            {"beat": "launch_or_enter", "intent": "飞舟/法器入画，锁船体/法器剪影", "camera": "仰角或远景建立"},
            {"beat": "cruise", "intent": "船体姿态稳定，云层/山河/前景视差高速后掠", "camera": "侧向跟飞"},
            {"beat": "maneuver_or_arrive", "intent": "转向、穿云、抵达或悬停结算", "camera": "缓推或俯冲一次"},
        ],
        "road_vehicle": [
            {"beat": "vehicle_establish", "intent": "交代车型、车道、行驶方向和驾驶关系", "camera": "侧向或三分之四建立"},
            {"beat": "traffic_motion", "intent": "锁车体，轮转/车流/街灯视差制造速度", "camera": "车侧跟拍或车内低幅度"},
            {"beat": "brake_turn_or_arrive", "intent": "刹车、变道、转弯或抵达一个结果", "camera": "低角度轮胎/车内反应/路口切"},
        ],
        "stealth_stalk": [
            {"beat": "hide_establish", "intent": "交代跟踪者/被跟踪者距离和遮挡层", "camera": "过肩或远中景"},
            {"beat": "shadow_approach", "intent": "距离缓慢变化，灯影/门缝/前景遮挡制造悬念", "camera": "慢跟或固定窥视"},
            {"beat": "reveal_or_hide", "intent": "露出一眼、错身躲开、脚步声逼近或目标消失", "camera": "半拍定格或硬切"},
        ],
        "screen_insert": [
            {"beat": "device_establish", "intent": "先看清手机/电脑/监控设备和持有关系", "camera": "固定近景"},
            {"beat": "overlay_read", "intent": "屏幕内容由 overlay 清晰呈现，不让模型画文字", "camera": "稳住屏幕平面"},
            {"beat": "reaction_or_cutaway", "intent": "切到角色反应或证据物，承接信息", "camera": "反打或手部插入"},
        ],
        "evidence_search": [
            {"beat": "search", "intent": "沿固定路径搜查，不乱翻新物件", "camera": "手部/物件近景"},
            {"beat": "clue_reveal", "intent": "物证露出并给可读半拍", "camera": "CU 定住"},
            {"beat": "chain_reaction", "intent": "证物入袋/拍照/角色反应，接证据链", "camera": "动作切或反打"},
        ],
        "tribulation_breakthrough": [
            {"beat": "omen_gather", "intent": "天象/雷云/威压建立，锁劫雷 VFX 形态", "camera": "大远景缓推"},
            {"beat": "strike_or_guard", "intent": "一道主雷或护体抵挡，impact_frame 清楚", "camera": "稳定留命中半拍"},
            {"beat": "breakthrough_release", "intent": "撑过后光柱/气息突破，强度递增后留白", "camera": "拉远显尺度"},
        ],
        "meditation_cultivation": [
            {"beat": "posture_settle", "intent": "打坐/入定姿态先锁，衣摆、发丝、蒲团和手印不漂", "camera": "固定中近景或低幅慢推"},
            {"beat": "breath_energy_cycle", "intent": "吐纳节奏与灵气入体路径清楚，气海/丹田/周天只走一条能量路径", "camera": "稳定，必要时切手印/胸口/丹田"},
            {"beat": "inner_state_response", "intent": "内视、心魔压制、境界波纹或环境响应给可读半拍", "camera": "微推或特写留白"},
            {"beat": "return_or_hold", "intent": "收功、睁眼、气息沉静或下一镜钩子，结果明确", "camera": "落回稳定构图"},
        ],
        "alchemy_forging": [
            {"beat": "setup_materials", "intent": "丹炉/锻炉、材料顺序和手部操作建立", "camera": "道具近景"},
            {"beat": "process_stage_ladder", "intent": "按投料/升温/凝丹或熔炼/锻打/淬火阶段递进，不跳阶段", "camera": "固定或慢推"},
            {"beat": "state_transform", "intent": "火候曲线、材料状态和灵纹流转清楚，炉体和火色不漂", "camera": "细节 CU 或炉口稳定镜"},
            {"beat": "reveal_result", "intent": "开炉/成丹/出器或失败爆烟，产品给可读半拍", "camera": "CU 定住"},
        ],
        "dual_cultivation": [
            {"beat": "consent_posture_establish", "intent": "成年人、双方自愿、非露骨边界先锁；双人姿态和距离清楚", "camera": "中景稳定，避免裸露/性行为暗示"},
            {"beat": "breath_sync", "intent": "呼吸同频，手印/掌心/背靠背等安全接触点不串位", "camera": "固定或低幅环绕"},
            {"beat": "energy_circulation", "intent": "灵力循环路径、阴阳/疗伤/破境目的清楚，身体动作保持克制", "camera": "能量路径跟随或叠 VFX"},
            {"beat": "result_hold", "intent": "疗伤见效、气息平复、关系状态或修为共鸣给留白；越界风险时淡出/只留能量隐喻", "camera": "反应特写或光雾淡出"},
        ],
        "kiss_or_near_kiss": [
            {"beat": "consent_and_approach", "intent": "年龄语境、双方自愿和关系状态先锁；靠近路径清楚，不突然贴脸", "camera": "MCU/OTS 稳定，轴线不乱跳"},
            {"beat": "face_angle_and_pause", "intent": "脸部角度、视线、呼吸停顿和微表情可读，避免五官变形", "camera": "固定或极缓推近"},
            {"beat": "contact_or_near_contact", "intent": "接触/差点接触帧给半拍；闭口轻吻、额头吻、脸颊吻或近吻按边界执行", "camera": "不大幅环绕，不遮住两张脸的身份锚"},
            {"beat": "separate_or_hold", "intent": "分开、拥抱承接、错开或留白，落到可接下一镜的表情/手部", "camera": "反应特写或手部插入"},
        ],
        "array_ritual": [
            {"beat": "geometry_establish", "intent": "俯视锚定阵图几何、符文层和施法者位置", "camera": "顶视或高角"},
            {"beat": "activation_steps", "intent": "按顺序点亮阵眼/符文/光轨，不自由改几何", "camera": "跟随能量流"},
            {"beat": "purpose_release", "intent": "封印/传送/困敌/防护等用途结果清楚", "camera": "切阵内主体"},
        ],
        "soul_manifestation": [
            {"beat": "body_anchor", "intent": "肉身/宿主静止锚定，身份和姿态先锁", "camera": "中近景稳定"},
            {"beat": "soul_emerge", "intent": "元神/神识沿 emergence_path 显形，透明度曲线清楚", "camera": "缓推或仰角"},
            {"beat": "probe_or_conflict", "intent": "探查、相争、夺舍成败或神魂攻击结果", "camera": "反应或命中定格"},
        ],
        "realm_portal": [
            {"beat": "portal_establish", "intent": "时空裂缝/传送阵/秘境入口形态锁定", "camera": "远中景建立"},
            {"beat": "entry_or_cross", "intent": "人物进入/被卷入/穿越落点，身体连续不换人", "camera": "跟随或背影入门"},
            {"beat": "destination_reveal", "intent": "异界/秘境/现代-古代落点给环境锚", "camera": "反打显景"},
        ],
        "contract_summon": [
            {"beat": "ritual_anchor", "intent": "契约阵、血契/印记、召唤主体位置建立", "camera": "顶视或手部近景"},
            {"beat": "summon_reveal", "intent": "召唤兽/法灵显形，尺度和剪影锁住", "camera": "低角度显尺度"},
            {"beat": "ownership_lock", "intent": "契约印记落定、主仆/伙伴关系成立", "camera": "印记/眼神反应"},
        ],
        "talent_test": [
            {"beat": "artifact_setup", "intent": "测灵石/觉醒台/水晶柱和测试规则建立", "camera": "道具近景"},
            {"beat": "result_rise", "intent": "光柱/颜色/刻度按规则显现，结果不要乱跳", "camera": "固定读数"},
            {"beat": "crowd_reaction", "intent": "众人反应链和身份/天赋揭示承接", "camera": "反打群像"},
        ],
    }
    return plans.get(kind, [])


def default_degrade_plan(kind: str) -> str:
    plans = {
        "fight_exchange": "拆成起手/命中/反应三镜；命中帧做尾帧硬约束，接触失败则改手部特写+反打。",
        "chase": "拆成追方/逃方/障碍结果三镜；保持同一 screen_direction，用前景遮挡和反打表达速度。",
        "magic_burst": "拆成蓄力/释放/撞点或峰值/余波四镜；撞点与特效峰值单独锁图，失败时改 VFX overlay + 反应镜。",
        "flight": "拆成起飞/巡航/机动/抵达；人物姿态锁定，把速度交给云层、山体和镜头路径。",
        "mount_ride": "拆成建立坐骑/步态循环/转向或抵达；骑手姿态和接触点锁住，速度交给背景、尘土和镜头。",
        "vehicle_ride": "拆成载具建立/轮转行进/障碍或停步；马车结构、轮子和缰绳锁住，复杂全景长跑改特写+反打。",
        "vessel_flight": "拆成入画/巡航/机动或抵达；飞舟或法器剪影锁住，云层和山河视差负责速度。",
        "road_vehicle": "拆成车辆建立/轮转车流/刹车转弯或抵达；车体和车道锁住，速度交给车轮、街灯、车流和镜头。",
        "stealth_stalk": "拆成建立距离/遮挡逼近/露出或躲开；用灯影、门缝、前景遮挡和声音制造悬疑，不做一镜复杂追打。",
        "screen_insert": "屏幕画面先出静态关键帧，文字/数字/聊天内容走 compose overlay；不让视频模型生成可读文字。",
        "evidence_search": "拆成搜查手部/物证露出/证据链反应；物证形态和位置锁住，避免一镜乱翻出新道具。",
        "tribulation_breakthrough": "拆天象/主雷命中/突破光柱三镜；劫雷、护体光、突破光柱入库，雷击命中帧单独锁图。",
        "meditation_cultivation": "拆姿态建立/吐纳周天/内视或灵气响应/收功四镜；人物少动，灵气、尘粒、衣摆和环境响应承担高级感。",
        "alchemy_forging": "拆材料入炉/阶段递进/状态转化/开炉成品；炉体、火色、材料和成品入库，产品可读半拍不让模型临场发明。",
        "dual_cultivation": "拆自愿边界建立/呼吸同步/能量循环/结果留白；保持成年人、非露骨、无裸露和无性行为表现，越界风险时改手印、背影、光雾或淡出。",
        "kiss_or_near_kiss": "拆自愿靠近/脸部角度与停顿/接触或近吻/分开或留白；年龄语境和非露骨边界不清时改额头吻、脸颊吻、错肩、手部或反应镜。",
        "array_ritual": "先出阵图俯视锚，再按阵眼逐步点亮；符文/几何可走 overlay 或定妆图，失败时拆局部阵眼和结果镜。",
        "soul_manifestation": "拆肉身锚定/元神显形/探查或成败；元神由肉身定妆派生，避免二我不同人。",
        "realm_portal": "拆入口建立/进入或卷入/落地显景；入口和目的地分别锁资产，穿越不在同镜改脸改服。",
        "contract_summon": "拆契约阵/召唤显形/印记落定；召唤兽或法灵入库，印记和归属关系给半拍。",
        "talent_test": "拆测试道具/结果显现/众人反应；数值、等级、天赋名走 overlay，AI 只画光柱和道具。",
        "large_establishing": "先出静态全景关键帧，再做慢推/横移/分层 parallax；复杂人群改剪影或分层合成。",
    }
    return plans.get(kind, "失败两次后拆镜、降运动量，并回到 storyboard 补契约。")


def spectacle_recommendations(kind: str) -> List[str]:
    recs = {
        "fight_exchange": [
            "每个 Clip 只保留一次攻击意图：setup -> attack -> impact -> reaction -> recovery。",
            "必须写 impact_frame/contact_points/force_direction，命中帧可读性优先于花哨运镜。",
            "必须写 keyframe_plan/post_cue_points/physics_guard：把命中帧、hit-stop、受力方向、肢体/武器归属写成可检查契约。",
            "准备 pose/depth/instance/contact_map；缺控制资产时不要进付费视频，先拆镜或 degrade_only。",
        ],
        "magic_burst": [
            "法术/剑气/武技 VFX 必须入库并写 effect_asset/vfx_asset_lock，颜色、形状、来源点和轨迹跨镜不漂。",
            "collision_or_apex_frame 是武技爽点帧：撞点、破防、护盾碎裂或峰值剑气必须单独可读。",
            "必须写 keyframe_plan/post_cue_points/physics_guard，明确蓄力、释放、撞点/峰值、余波和音画爆点。",
        ],
        "chase": [
            "screen_direction 只允许一条主方向；distance_curve 只能收近或拉远，不在同镜来回重置。",
            "速度交给 parallax_layers、前景遮挡、衣摆发丝和跟拍，主体姿态变化要少。",
            "必须写 keyframe_plan/post_cue_points/physics_guard，尤其是障碍/变向/追上或逃脱的可读结果帧。",
            "准备 camera_path/spatial_path/parallax_layers，障碍点要有 obstacle_beats。",
        ],
        "flight": [
            "锁 pose_lock 和 mount_or_cloud_lock；腾云/御剑形状不能边飞边变。",
            "altitude_curve 与 flight_path 分开写，云海/山体作为 parallax 层运动。",
            "必须写 keyframe_plan/post_cue_points/physics_guard，确保起飞/穿云/机动/抵达的 apex 或落幅帧可读。",
            "大机动拆成巡航和变向两镜；缺控制资产时用背景动、人物少动。",
        ],
        "mount_ride": [
            "坐骑必须入 BEAST/MOUNT 资产库，锁体型、角/鳞/毛色、鞍具和骑手接触点。",
            "gait_cycle 只写一种主步态；速度交给尘土、草木、披风、鬃毛和侧向跟拍。",
            "不稳时拆成坐骑特写、骑手反应、侧向奔跑、落地/停步四类短镜。",
        ],
        "vehicle_ride": [
            "vehicle_lock 锁车厢、车轮数量/位置、车辕和马匹连接，不让轮子变形或凭空增减。",
            "wheel_rotation 与 harness_lock 分开写：轮转/马蹄动，车厢外形和缰绳连接不变。",
            "不稳时用轮子/马蹄/车夫手部/车内反应镜承载行驶感，避免一镜全景长跑。",
        ],
        "vessel_flight": [
            "飞舟/法器入 VEHICLE/PROP 资产库，锁剪影、桅帆/船舷/阵纹和拖光颜色。",
            "船体姿态尽量稳定，速度来自云海、山河和前景遮挡物视差。",
            "转向/俯冲/悬停拆短镜，避免飞舟边飞边改形或尺度跳变。",
        ],
        "road_vehicle": [
            "现代车辆入 VEHICLE 资产库，锁车型、车牌是否可见、车灯、车轮数量和车身颜色。",
            "driver_control_lock 锁方向盘/手/踏板或驾驶位关系；lane_lock 锁车道、路口和屏幕方向。",
            "追车/急刹不稳时拆成轮胎、后视镜、驾驶员反应、车外掠过和抵达停住。",
        ],
        "stealth_stalk": [
            "尾随/潜入镜头先锁空间轴线、距离曲线和遮挡层，别让两人突然换方向或瞬移。",
            "light_shadow_lock 写清灯源、暗区、剪影边缘和手电范围，悬疑感来自可控明暗而非糊黑。",
            "露出/躲开只给一个 reveal_or_hide_beat；复杂追逐转 chase，审讯转 public_confrontation。",
        ],
        "screen_insert": [
            "手机/电脑/监控屏幕必须 text_layer=overlay；AI 只画设备、反光和空白/模糊界面底，不烤文字。",
            "screen_content_ref 写清内容来源（聊天记录/通话/监控时间码/转账/定位），compose 期叠清晰文字。",
            "reflection_policy 锁反光和屏幕角度；手指滑动、弹窗、来电只做低幅度变化。",
        ],
        "evidence_search": [
            "物证进 PROP/EVIDENCE 资产库，锁血迹/指纹/照片/钥匙/票据/证物袋形态和位置。",
            "search_path 只写一条搜查路径；reveal_frame 给物证露出半拍，证据链用 evidence_chain 承接。",
            "避免一镜连续翻箱、发现、追人、打斗；后两者拆到 chase/fight_exchange。",
        ],
        "tribulation_breakthrough": [
            "劫雷/护体光/突破光柱进 VFX 资产库，锁颜色、形态、粗细和命中点。",
            "intensity_curve 必须递增；每个 Clip 只处理一道主雷、一次抵挡或一次突破释放。",
            "雷击 impact_frame 单独可读，突破后留白，不要全程乱闪。",
        ],
        "meditation_cultivation": [
            "打坐/静坐/冥想不是空镜：posture_lock、breath_cycle、energy_flow 和 aura_vfx_lock 必须可见可审。",
            "人物主体少动，微动作只给呼吸、指节、衣摆、发丝、灵气粒子和环境响应；不要让角色站起或乱换手印。",
            "inner_state_beat 要明确是内视、心魔压制、气海波纹、灵气入体还是收功钩子；一镜只给一个内在结果。",
            "必须写 keyframe_plan/post_cue_points/physics_guard，确保起势、周天峰值、结果留白都有锚。",
        ],
        "alchemy_forging": [
            "丹炉/锻炉、材料、火焰、成品进 PROP/VFX 资产库；火色和炉纹不要跨镜变。",
            "material_sequence、process_stage_ladder、heat_curve 和 material_state_ladder 分开写，避免材料乱飞、火候无层次或跳阶段。",
            "reveal_frame 要给成丹/出器/失败爆烟的可读半拍；产品锁图，失败形态也要锁。",
            "必须写 keyframe_plan/post_cue_points/physics_guard，确保投料、升温、转化和开炉爽点可控。",
        ],
        "dual_cultivation": [
            "双修只按成年人、双方明确自愿、非露骨的修炼/疗伤/能量循环表达；禁止裸露、性行为动作和未成年人语义。",
            "paired_posture_lock、distance_boundary、contact_points 和 breath_sync 必须清楚，接触以掌心、背靠背、手印或光流为主。",
            "energy_circulation 和 aura_vfx_lock 承担奇观感，relationship_state 写信任、疗伤、共鸣或克制亲密，不写露骨身体描写。",
            "越界或接触不稳时立即降级为手部特写、背影、光雾、反应镜或淡出。",
        ],
        "kiss_or_near_kiss": [
            "接吻/近吻必须写 age_context_lock、consent_lock 和 non_explicit_boundary；不清楚就改近吻停顿、额头吻、脸颊吻或错肩。",
            "face_angle_lock、contact_or_near_contact_frame、hand_position_lock 和 body_overlap_limit 必须清楚，避免脸融合、手穿模和身体重叠。",
            "表情靠 micro_expression_beats 和 breath_pause，动作保持克制；不要写露骨舌吻、脱衣或性行为暗示。",
            "接触不稳时拆成靠近、眼神停顿、手部/发丝、反应镜和分开落幅。",
        ],
        "array_ritual": [
            "阵图先做俯视锚或 overlay 几何层，AI 不负责临场画对称符文。",
            "activation_steps 只点亮 2-4 个明确阵眼/光轨；purpose_lock 写封印、传送、困敌或防护。",
            "多人施法时 caster_positions 写清槽位，避免阵内人物跳位。",
        ],
        "soul_manifestation": [
            "元神/神识形态由角色肉身定妆派生，body_soul_identity_lock 必须说明二者同一身份。",
            "opacity_curve 和 emergence_path 分开写，视频只做透明度/光流/缓升，不重画脸。",
            "夺舍/神魂攻击要给成败帧；不要一镜画两个魂自由缠斗。",
        ],
        "realm_portal": [
            "portal_lock 锁裂缝/传送阵/秘境门形态；source_world_anchor 与 destination_anchor 都要明确。",
            "entry_exit_path 只做进入、卷入或落地一个动作；跨世界换装/换脸另拆后态定妆。",
            "穿越第一眼要给环境锚，避免观众不知道到了哪里。",
        ],
        "contract_summon": [
            "召唤兽/法灵进 BEAST/MOUNT/PROP 资产库，summon_entity_lock 锁剪影、颜色和尺度。",
            "contract_mark 锁印记位置、颜色和归属，ownership_transition 给契约成立半拍。",
            "若后续骑乘，召唤后再接 mount_ride，不在契约镜里直接骑跑。",
        ],
        "talent_test": [
            "测灵石/觉醒台/水晶柱进 PROP，measurement_rule 写颜色、刻度、亮度或阶段。",
            "天赋名、数值、等级、系统提示走 overlay_policy，不让视频模型生成可读字。",
            "crowd_reaction_chain 接 reveal_reaction_chain 或 public_confrontation，避免结果出来没人反应。",
        ],
        "large_establishing": [
            "先写 geography_map/landmark_anchor/scale_reference，避免大场景只剩氛围词。",
            "把远中近 parallax_planes 分层，慢推/横移优先，少做自由旋转航拍。",
            "可复用 LOC/asset_registry 的场景资产，复杂人群用剪影/雾化/后期层而不是清晰逐人生成。",
        ],
    }
    return list(recs.get(kind, []))


def premium_spectacle_passes(kind: str) -> Dict[str, Any]:
    """经费燃烧级奇观镜的结构化制作通道。纯函数，供 plan/sequence/video/review 复用。"""
    if kind not in SPECTACLE_KINDS:
        return {}
    impact_label = {
        "fight_exchange": "impact_frame",
        "magic_burst": "collision_or_apex_frame",
        "tribulation_breakthrough": "impact_frame/breakthrough_light",
        "flight": "apex_or_maneuver_frame",
        "chase": "obstacle_or_overtake_frame",
        "meditation_cultivation": "inner_state_or_aura_frame",
        "alchemy_forging": "reveal_frame",
        "dual_cultivation": "energy_circulation_apex_frame",
        "kiss_or_near_kiss": "contact_or_near_contact_frame",
    }.get(kind, "apex_or_result_frame")
    return {
        "level": "premium_action_spectacle" if kind in ACTION_CHOREOGRAPHY_SHOT_TYPES else "premium_spectacle",
        "required_contract_fields": list(PREMIUM_SPECTACLE_FIELDS),
        "keyframe_policy": {
            "required": ["start", "intent_mid", impact_label, "result_or_recovery", "end"],
            "rule": "首帧定身份/空间，中段定动作方向，命中/峰值帧定爽点，尾帧定结果；后端不吃多锚时拆段接力。",
        },
        "post_cue_policy": {
            "required": ["pre_peak", "peak", "aftershock_or_hold"],
            "rule": "hit-stop/闪白/震屏/速度坡/音效峰值必须与命中或峰值帧对齐，不能用糊和乱抖遮动作。",
        },
        "physics_guard_policy": {
            "required": ["subject_identity", "axis_or_path", "contact_or_vfx_shape", "no_extra_motion"],
            "rule": "守住身份、轴线/路径、接触点或特效形态；一镜只给一个主要结果。",
        },
        "qc_dimensions": [
            "keyframe_coverage",
            "impact_apex_readability",
            "edit_sfx_sync",
            "optical_flow_direction",
            "motion_smoothness",
            "subject_identity",
        ],
    }


# ── 动作镜成片 QC：八维机检 + 高级制作三项（VBench + GenVID artifact eval 拆解）─────────────
# 一个生成的动作镜「成功与否」先拆成 8 个可机检维度，再加 3 个「经费燃烧感」制作维度：
# 关键帧覆盖、命中/峰值可读、剪辑/音效同步。spectacle_video_qc 据此逐镜汇总「哪几维已被实测证据覆盖、
# 哪几维还空」。evidence_keys=外部 runner 写进 sidecar 的实测字段名（任一命中即视为该维已实测）。
# 重活仍在 out-of-repo conda（见 references/动作镜QC机检.md）。
SPECTACLE_QC_DIMENSIONS: Tuple[Dict[str, Any], ...] = (
    {"key": "optical_flow_direction", "label": "光流方向↔意图对账",
     "proves": "成片实际运动/运镜方向与 prompt 声明的 camera_path/动作方向一致（Kling 笔刷方向≠prompt 必崩的机检版）",
     "evidence_keys": ("optical_flow_direction", "flow_intent_match", "flow_direction_error"),
     "runner": "new", "sample": "high_flow"},
    {"key": "limb_artifact", "label": "肢体畸变/多手多脚",
     "proves": "无异常肢体/多手多脚/穿插畸形（HADM 类，动作峰值帧最易崩）",
     "evidence_keys": ("limb_artifact_score", "extra_limbs", "deformation_score"),
     "runner": "new", "sample": "high_flow"},
    {"key": "motion_smoothness", "label": "运动平滑/动作完成度",
     "proves": "运动平滑、动态程度合理、无冻结帧/异常 jerk、动作有头有尾完成",
     "evidence_keys": ("motion_smoothness", "jerk", "dynamic_degree", "action_completion", "freeze_frame"),
     "runner": "motion_quality_consistency", "sample": "uniform"},
    {"key": "motion_blur_plausibility", "label": "运动模糊合理性",
     "proves": "该糊的高速段糊、不该糊的清楚（区分意图性运动模糊 vs 画质崩坏）",
     "evidence_keys": ("motion_blur_plausibility", "imaging_quality", "blur_score"),
     "runner": "new", "sample": "high_flow"},
    {"key": "endframe_match", "label": "首尾 match-on-action 衔接",
     "proves": "本镜首/尾帧与相邻 clip 末/首帧的动作/视觉衔接（动作匹配剪辑成立）",
     "evidence_keys": ("endframe_match", "seam_action_match", "match_on_action"),
     "runner": "temporal_consistency", "sample": "boundary"},
    {"key": "axis_continuity", "label": "跨镜动作连续+180°轴线",
     "proves": "相机轨迹稳、不越轴(180°线)、方向不跳变、视差合理",
     "evidence_keys": ("trajectory_error", "axis_consistency", "crossing_line", "parallax_flow_score"),
     "runner": "camera_trajectory_consistency", "sample": "uniform"},
    {"key": "subject_identity", "label": "主体身份保持",
     "proves": "运动中脸/服装/主体不漂、多主体不串换",
     "evidence_keys": ("subject_fidelity", "identity_drift", "subject_swap"),
     "runner": "subject_video_consistency", "sample": "high_flow"},
    {"key": "temporal_flicker", "label": "时序闪烁",
     "proves": "相邻帧无闪烁/抖动/背景跳变（TCI）",
     "evidence_keys": ("temporal_flicker", "tci", "flicker_score"),
     "runner": "temporal_consistency", "sample": "uniform"},
    {"key": "keyframe_coverage", "label": "关键帧覆盖",
     "proves": "start/mid/impact-or-apex/result/end 等关键帧或拆段锚实际存在，后端未吞掉中段计划",
     "evidence_keys": ("keyframe_plan_coverage", "start_mid_impact_end_coverage", "keyframes_present", "anchor_coverage"),
     "runner": "video_preflight_or_anchor_runner", "sample": "contract"},
    {"key": "impact_apex_readability", "label": "命中/峰值帧可读",
     "proves": "打斗命中、武技撞点、突破主雷或飞行机动峰值在成片中可见、可停、可读",
     "evidence_keys": ("impact_frame_readable", "apex_frame_readable", "collision_point_visibility", "readability_hold_score"),
     "runner": "video_qc_or_human_signoff", "sample": "peak"},
    {"key": "edit_sfx_sync", "label": "剪辑/音效同步",
     "proves": "hit-stop、速度坡、闪白、震屏、whoosh/impact/thunder 等 cue 与峰值帧同步，不用乱抖遮丑",
     "evidence_keys": ("edit_sfx_sync", "hit_stop_sync", "speed_ramp_sync", "sfx_peak_alignment"),
     "runner": "compose_qc_or_human_signoff", "sample": "peak"},
)


def spectacle_qc_dimension_status(external: Mapping[str, Any]) -> Dict[str, str]:
    """逐镜核验状态：external sidecar 命中该维任一 evidence_key → verified，否则 unverified。纯函数·可测。"""
    out: Dict[str, str] = {}
    for dim in SPECTACLE_QC_DIMENSIONS:
        keys = dim["evidence_keys"]  # type: ignore[index]
        verified = any(
            str(k) in external and external.get(str(k)) not in (None, "", [], {})
            for k in keys
        )
        out[str(dim["key"])] = "verified" if verified else "unverified"
    return out


def high_flow_sampling_plan(kind: str, duration: float = 0.0) -> Dict[str, Any]:
    """高光流帧重点采样策略：动作峰值处(高光流)最易出 artifact，重模型 runner 应在此加密采样。

    返回供外部 runner 消费的采样契约——FMG-DFS 思路：先用光流定位 motion-salient 段，再在峰值帧
    加密抽帧检肢体畸变/身份漂/模糊。纯函数·可测；duration<=0 时给默认密度。
    """
    try:
        dur = float(duration)
    except (TypeError, ValueError):
        dur = 0.0
    base = max(6, int(round(dur))) if dur > 0 else 6
    peak = "高光流(动作峰值)段每 0.2s 一帧" if kind in ACTION_CHOREOGRAPHY_SHOT_TYPES else "运动显著段加密"
    return {
        "strategy": "optical_flow_guided",
        "base_uniform_frames": min(base, 24),
        "peak_density": peak,
        "boundary_frames": ["first", "last"],
        "note": "FMG-DFS：光流定位 motion-salient 片段→峰值/命中帧加密采样检肢体畸变、身份漂、运动模糊与爽点可读性。",
    }


def edit_cues_for_spectacle(kind: str, contract: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    contract = contract or {}
    if kind == "fight_exchange":
        impact = str(contract.get("impact_frame") or "impact")
        return [
            {"cue": "pre_impact_whoosh", "when": "attack_path wind-up", "layer": "weapon/cloth/air"},
            {"cue": "speed_ramp", "when": "attack_path before impact", "curve": "fast_in_slow_on_hit"},
            {"cue": "hit_stop", "when": impact, "duration_frames": 2, "purpose": "make impact readable"},
            {"cue": "screen_shake", "when": impact, "strength": "low", "purpose": "sell force without hiding contact"},
            {"cue": "impact_sfx", "when": impact, "layer": "weapon_or_body_hit"},
            {"cue": "micro_silence_drop", "when": impact, "duration_frames": 2, "purpose": "make the hit feel expensive"},
            {"cue": "aftershock_sweetener", "when": "recovery_beat", "layer": "debris/cloth/breath"},
        ]
    if kind == "magic_burst":
        peak = str(contract.get("collision_or_apex_frame") or contract.get("release_frame") or "collision_or_apex")
        return [
            {"cue": "charge_riser", "when": "charge_frame", "layer": "low_hum + particle_spark"},
            {"cue": "release_whoosh", "when": "release_frame", "layer": "air_shear"},
            {"cue": "white_flash", "when": peak, "duration_frames": 2},
            {"cue": "impact_or_energy_boom", "when": peak, "layer": "sub_hit + crackle"},
            {"cue": "screen_shake", "when": peak, "strength": "medium-low", "purpose": "sell power without hiding VFX shape"},
            {"cue": "aftershock_tail", "when": "aftermath/result", "layer": "reverb + dust/embers"},
        ]
    if kind == "chase":
        return [
            {"cue": "speed_ramp", "when": "obstacle_beats", "curve": "accelerate_then_cut"},
            {"cue": "foreground_whoosh", "when": "parallax layer crosses frame"},
            {"cue": "cut_on_motion", "when": "overtake_or_escape_beat"},
            {"cue": "breath_or_footstep_sfx", "when": "distance_curve changes"},
        ]
    if kind == "flight":
        return [
            {"cue": "wind_whoosh", "when": "flight_path begins"},
            {"cue": "cloud_pass", "when": "altitude_curve changes"},
            {"cue": "parallax_swell", "when": "camera_path pushes through clouds"},
            {"cue": "altitude_music_lift", "when": "arrival or reveal beat"},
        ]
    if kind == "mount_ride":
        return [
            {"cue": "hoof_or_claw_rhythm", "when": "gait_cycle begins"},
            {"cue": "foreground_whoosh", "when": "parallax layer crosses frame"},
            {"cue": "dust_or_grass_swell", "when": "speed_curve rises"},
            {"cue": "mount_breath_or_roar", "when": "turn_or_arrive beat"},
        ]
    if kind == "vehicle_ride":
        return [
            {"cue": "wheel_rattle", "when": "wheel_rotation visible"},
            {"cue": "harness_jingle", "when": "harness_lock crosses frame"},
            {"cue": "road_dust", "when": "speed_curve rises"},
            {"cue": "brake_or_bump_sfx", "when": "obstacle_or_stop beat"},
        ]
    if kind == "vessel_flight":
        return [
            {"cue": "wind_whoosh", "when": "vehicle_lock enters frame"},
            {"cue": "cloud_pass", "when": "altitude_curve changes"},
            {"cue": "parallax_swell", "when": "camera_path pushes through clouds"},
            {"cue": "engine_or_array_hum", "when": "maneuver_or_arrive beat"},
        ]
    if kind == "road_vehicle":
        return [
            {"cue": "engine_bed", "when": "vehicle_lock enters frame"},
            {"cue": "tire_roll", "when": "wheel_rotation visible"},
            {"cue": "traffic_whoosh", "when": "parallax_layers cross frame"},
            {"cue": "brake_or_turn_sfx", "when": "brake_turn_or_arrive beat"},
        ]
    if kind == "stealth_stalk":
        return [
            {"cue": "low_room_tone", "when": "hide_establish begins"},
            {"cue": "footstep_isolation", "when": "distance_curve closes"},
            {"cue": "light_flicker_or_breath", "when": "occlusion layer changes"},
            {"cue": "sting_or_silence", "when": "reveal_or_hide_beat"},
        ]
    if kind == "screen_insert":
        return [
            {"cue": "ui_tick", "when": "overlay_content appears"},
            {"cue": "notification_sfx", "when": "screen_content_ref changes"},
            {"cue": "hard_cut_to_reaction", "when": "readability_beats complete"},
        ]
    if kind == "evidence_search":
        return [
            {"cue": "cloth_or_paper_rustle", "when": "search_path begins"},
            {"cue": "clue_sting", "when": "reveal_frame"},
            {"cue": "camera_shutter_or_bag_sfx", "when": "evidence_chain records clue"},
        ]
    if kind == "tribulation_breakthrough":
        return [
            {"cue": "thunder_roll", "when": "omen_gather"},
            {"cue": "white_flash", "when": "impact_frame", "duration_frames": 2},
            {"cue": "low_shockwave", "when": "shield_lock or impact_frame"},
            {"cue": "music_peak_then_hold", "when": "breakthrough_light"},
        ]
    if kind == "meditation_cultivation":
        return [
            {"cue": "breath_bed", "when": "breath_cycle begins", "layer": "low_air + chest_sub"},
            {"cue": "aura_swell", "when": "energy_flow reaches dantian/meridian", "layer": "soft_chime + particle"},
            {"cue": "inner_state_sting", "when": "inner_state_beat", "purpose": "make the invisible cultivation beat readable"},
            {"cue": "silence_hold", "when": "return_or_hold", "duration_frames": 8, "purpose": "sell calm power"},
        ]
    if kind == "alchemy_forging":
        return [
            {"cue": "flame_bed", "when": "flame_control begins"},
            {"cue": "metal_or_furnace_ping", "when": "material_sequence changes"},
            {"cue": "heat_riser", "when": "heat_curve reaches peak"},
            {"cue": "transformation_spark", "when": "material_state_ladder changes stage"},
            {"cue": "open_furnace_chime", "when": "reveal_frame or success_or_failure_beat"},
            {"cue": "product_hold_sweetener", "when": "product_lock readable"},
        ]
    if kind == "dual_cultivation":
        return [
            {"cue": "consent_silence_hold", "when": "adult_consent_lock/readability_beats", "purpose": "do not eroticize; establish trust and safety"},
            {"cue": "breath_sync_pulse", "when": "breath_sync begins", "layer": "two_soft_breaths + low_hum"},
            {"cue": "energy_loop_swell", "when": "energy_circulation apex", "layer": "aura_chime + sub_swell"},
            {"cue": "fade_or_hold", "when": "result_hold", "purpose": "non-explicit result beat"},
        ]
    if kind == "kiss_or_near_kiss":
        return [
            {"cue": "room_tone_drop", "when": "consent_and_approach", "purpose": "make the pause readable without eroticizing"},
            {"cue": "breath_pause", "when": "breath_pause", "layer": "soft breath + fabric"},
            {"cue": "micro_silence_hold", "when": "contact_or_near_contact_frame", "duration_frames": 6},
            {"cue": "soft_reaction_chime", "when": "separate_or_hold", "purpose": "sell relationship turn"},
        ]
    if kind == "array_ritual":
        return [
            {"cue": "array_hum", "when": "array_geometry_lock appears"},
            {"cue": "glyph_tick", "when": "activation_steps each light"},
            {"cue": "energy_swell", "when": "purpose_lock releases"},
        ]
    if kind == "soul_manifestation":
        return [
            {"cue": "spirit_whoosh", "when": "soul_form_lock emerges"},
            {"cue": "opacity_swell", "when": "opacity_curve reaches visible"},
            {"cue": "identity_sting", "when": "body_soul_identity_lock readable"},
        ]
    if kind == "realm_portal":
        return [
            {"cue": "portal_low_rumble", "when": "portal_lock activates"},
            {"cue": "suck_in_whoosh", "when": "entry_exit_path begins"},
            {"cue": "hard_cut_or_bloom", "when": "destination_anchor reveals"},
        ]
    if kind == "contract_summon":
        return [
            {"cue": "ritual_pulse", "when": "ritual_anchor lights"},
            {"cue": "summon_roar_or_chime", "when": "summon_entity_lock reveals"},
            {"cue": "contract_mark_lock", "when": "ownership_transition completes"},
        ]
    if kind == "talent_test":
        return [
            {"cue": "artifact_resonance", "when": "test_artifact_lock activates"},
            {"cue": "result_riser", "when": "result_stage rises"},
            {"cue": "crowd_gasp", "when": "crowd_reaction_chain begins"},
        ]
    if kind == "large_establishing":
        return [
            {"cue": "slow_push", "when": "establishing_progression starts"},
            {"cue": "scale_reveal_sfx", "when": "landmark_anchor appears"},
            {"cue": "ambient_bed", "when": "full clip", "layer": "wind/crowd/temple"},
            {"cue": "title_or_locator_hold", "when": "scale_reference is readable"},
        ]
    return []
