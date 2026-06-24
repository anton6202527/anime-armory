#!/usr/bin/env python3
"""Deterministic stage gates for n2d.

This script turns the high-risk SKILL.md rules into repeatable checks.  It does
not create assets; it only reports whether a stage may proceed.

Usage:
  # Production entry: records QA findings and returns this gate's exit code.
  python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_prompt_preflight|image_preflight|video_prompt_preflight|video_preflight|image|video|compose|review

  # Engine/debug entry: deterministic findings only, no dashboard telemetry.
  python3 skills/n2d-review/scripts/gate.py <作品根> 第N集 --stage video --json

Exit codes:
  0 = no blockers
  1 = at least one blocker
  2 = bad invocation / missing project
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

SCRIPT_DIR = os.path.dirname(__file__)
COMMON = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
# n2d 同线姊妹 skill：声纹/音色键跨集一致性核心住在 n2d-identity（独立性审计只拦跨创作线，
# 同线 n2d-* 互引允许）。gate 直接调，让「声纹漂移」在 image gate 渲染前自动落地，
# 不再只靠人手动跑 identity.py --write 当副作用。
_IDENTITY_SCRIPTS = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "n2d-identity", "scripts"))
if _IDENTITY_SCRIPTS not in sys.path:
    sys.path.insert(0, _IDENTITY_SCRIPTS)

from n2d_contract import (  # noqa: E402
    APPROVED_IMAGE_BACKENDS,
    ACTION_BEAT_CATEGORY_SPLIT_THRESHOLD,
    ACTION_CHOREOGRAPHY_COMMON_FIELDS,
    ACTION_CHOREOGRAPHY_SHOT_TYPES,
    ACTION_CHOREOGRAPHY_SPECIFIC_FIELDS,
    ASSET_REFERENCE_REGISTRY_KIND,
    MIN_ACTION_BEAT_SECONDS,
    action_beat_categories,
    beat_decomposition,
    CINEMATIC_CONTRACT_FIELDS,
    CONSISTENCY_DIMENSIONS,
    COMPLIANCE_AI_LABEL_STATUSES,
    COMPLIANCE_ALLOWED_RIGHTS,
    COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS,
    COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS,
    COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED,
    COMPLIANCE_APPROVED_CHARACTER,
    COMPLIANCE_BLOCKED_CHARACTER,
    COMPLIANCE_DONE_STATUSES,
    COMPLIANCE_DOMESTIC_REGIONS,
    COMPLIANCE_MANIFEST_KIND,
    COMPLIANCE_OVERSEAS_PLATFORMS,
    COMPLIANCE_PLACEHOLDER_MARKERS,
    COMPLIANCE_PLATFORM_REVIEW_STATUSES,
    COMPLIANCE_PRE_BROADCAST_STATUSES,
    COMPLIANCE_READY_STATUSES,
    COMPLIANCE_SAFE_VOICE,
    COMPLIANCE_STATUS_LIKE_VALUES,
    EXPRESSION_SPAN_BIG,
    EXPRESSION_SPAN_VALUES,
    GATE_STAGES,
    HIGH_MOTION_TEMPLATES,
    IDENTITY_ADAPTER_MATRIX_KIND,
    IDENTITY_HANDLE_FIELDS,
    IDENTITY_IMAGE_ADAPTERS,
    IDENTITY_REFERENCE_KEYS,
    IDENTITY_REGISTRY_KIND,
    IDENTITY_VIDEO_ADAPTERS,
    image_backend_supports_persistent_subject,
    identity_allowed_modes,
    identity_registry_path,
    MOTION_CONTROL_MANIFEST_KIND,
    MOTION_CONTROL_REQUIRED_SHOT_TYPES,
    MOTION_CONTROL_RISK_FLAGS,
    SPECTACLE_SEQUENCE_PLAN_KIND,
    STYLE_CONTRACT_FIELDS,
    SPECTACLE_TEMPLATE_FIELDS,
    VIDEO_MODEL_ROUTES_KIND,
    VISUAL_CONTRACT_FIELDS,
    VOICE_KEY_FIELD,
    VOICE_KEY_LEGACY_FIELD,
    annotate_finding,
    asset_registry_path,
    classify_image_backend,
    infer_spectacle_type,
    lora_gap_message,
    lora_registry_ready_blocks,
    motion_control_required,
    shared_asset_dir,
    shared_asset_path,
    special_template_keywords,
    stage_for_progress_column,
)
from n2d_contract_diff import diff_contracts  # noqa: E402  视觉契约继承 Diff 核心（common 层单一真值源）
from n2d_handoff import (  # noqa: E402  逐镜身份/资产交接 Diff（common 层单一真值源，与 inherit_contract 共用）
    check_asset_handoff,
    check_identity_handoff,
)
import image_backends  # noqa: E402  出图后端连通性探活 adapter（选择点→探针）
import image_backend_adapter  # noqa: E402  生图后端 API/能力适配层（选择点→能力/刷新证据/推荐）
import video_backend_adapter  # noqa: E402  生视频后端 API/能力适配层（选择点→能力/刷新证据）
from style_policy import face_encoder_policy  # noqa: E402
from n2d_platform_profiles import (  # noqa: E402
    anchor_consumption_plan,
    backend_supports_three_plus_frames,
    video_backend_frame_control,
    video_backend_max_seconds,
)
from n2d_route import (  # noqa: E402
    is_done,
    is_progress_satisfied,
    manifest_path,
    parse_progress,
    voice_is_placeholder,
    voice_meta_path,
    voiceover_fingerprint,
)
from n2d_settings import get_setting, is_native_av, is_video_first  # noqa: E402
from n2d_logic import normalize_camera_move, color_temperature_findings  # noqa: E402  运镜词典归一 + 色温数值化体检
from n2d_cross_episode import (  # noqa: E402  跨集视觉契约方向反转（同地点光位/轴线翻）核心
    cross_episode_diff as _cross_episode_diff,
    overview_rel as _ce_overview_rel,
    prior_episode as _ce_prior_episode,
    _episode_number as _ce_episode_number,
    scene_names as _ce_scene_names,
    core_scene_names as _ce_core_scene_names,
)
import semantic_continuity as semc  # noqa: E402
import state_continuity as statec  # noqa: E402
import multimodal_consistency as mmc  # noqa: E402
import subtitle_align as sa  # noqa: E402
import voice_consistency as vcons  # noqa: E402  音色键/voicemap 跨集对账（确定性）
import voice_print_consistency as vprint  # noqa: E402  声纹 embedding 跨集漂移（启发式·后端可缺）
try:
    from skill_snapshot import fingerprint_is_fresh  # type: ignore
except Exception:  # pragma: no cover - degraded local env
    fingerprint_is_fresh = None  # type: ignore[assignment]

BLOCK, WARN, INFO = "block", "warn", "info"
findings: List[Dict[str, object]] = []
FALLBACK_OFF_VALUES = {"", "无", "不使用", "关闭", "否", "off", "no", "none", "disable", "disabled"}


SPECIAL_SHOT_TEMPLATE_FIELDS: Dict[str, Tuple[str, ...]] = {
    **SPECTACLE_TEMPLATE_FIELDS,
    "dialogue_shot_reverse": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "axis", "eyeline", "shot_pairing",
    ),
    "reveal_reaction_chain": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "reveal_object", "knowledge_order", "reaction_beats", "cut_point",
    ),
    "public_confrontation": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "stakes", "evidence_ladder", "power_shift", "crowd_reaction_order",
    ),
    "magic_burst": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "charge_frame", "release_frame", "effect_asset",
    ),
    "intimate_interaction": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "contact_points", "distance_boundary", "body_overlap_limit",
    ),
    "hug_or_pull": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "contact_points", "force_direction", "body_overlap_limit", "release_frame",
    ),
    "relationship_turn": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "relationship_state_before", "turning_action", "subtext", "relationship_state_after",
    ),
    "multi_character_same_frame": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "character_slots", "face_priority", "overlap_rules",
    ),
    "ensemble_blocking": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "screen_positions", "focus_hierarchy", "crowd_simplification",
    ),
    "multi_person_blocking": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "screen_positions", "speaker_focus", "crowd_simplification",
    ),
}

# 专项镜头模板关键词从 common 派生（与 router.infer_shot_type 同一份 SHOT_TYPE_KEYWORDS，判型口径不再两边漂移）
SPECIAL_SHOT_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = special_template_keywords()

MOTION_CONTROL_KIND = MOTION_CONTROL_MANIFEST_KIND  # 从 n2d_contract 产物 kind 注册表取
# MOTION_CONTROL_REQUIRED_SHOT_TYPES / MOTION_CONTROL_RISK_FLAGS 从 n2d_contract 导入（与 router 同源）
MOTION_CONTROL_ROUTE_FIELDS = (
    "level",
    "required",
    "manifest_required",
    "manifest_path",
    "required_inputs",
    "backend_control_level",
    "failure_modes",
    "gate_policy",
    "degrade_allowed",
)
MOTION_CONTROL_READY_STATUSES = ("ready", "degrade_only")
MOTION_CONTROL_READY_INPUT_STATUSES = ("ready", "not_needed")
MOTION_CONTROL_CONTACT_FIELDS = ("contact_points", "occlusion_order", "body_part_ownership")
MOTION_CONTROL_CONTACT_SHOT_TYPES = ("fight_exchange", "hug_or_pull", "intimate_interaction")

# IDENTITY_REGISTRY_KIND / IDENTITY_ADAPTER_MATRIX_KIND / IDENTITY_REFERENCE_FIELDS /
# IDENTITY_HANDLE_FIELDS 从 n2d_contract 导入（写方 lora/market/identity 同源）
IDENTITY_REFERENCE_FIELDS = IDENTITY_REFERENCE_KEYS
# 角色定妆基础包不可缺失铁律（设计宪法 B7）：三视图是人审拼版，不能替代可喂图拆分资产。
REQUIRED_CHARACTER_MAKEUP_REFERENCE_GROUP_FIELDS = ("front", "three_quarter", "side", "back", "turnaround")
REQUIRED_CHARACTER_MAKEUP_ATLAS_VIEWS = ("front", "three_quarter", "side", "back")
CHARACTER_MAKEUP_BODY_REFERENCE_FIELDS = ("half_body", "full_body", "outfit")
CHARACTER_MAKEUP_FACE_REFERENCE_FIELDS = ("face_anchor_refs", "expressions")
READY_CHARACTER_MAKEUP_STATUSES = {"ready", "registered"}
DERIVED_CHARACTER_MAKEUP_REFERENCE_FIELDS = ("three_quarter", "side", "back", "half_body", "full_body", "face_anchor_refs")
SAME_SOURCE_MAKEUP_DERIVATION_METHODS = {
    "three_quarter": {"turnaround_split", "turnaround_crop"},
    "side": {"turnaround_split", "turnaround_crop"},
    "back": {"turnaround_split", "turnaround_crop"},
    "half_body": {"front_crop", "turnaround_crop"},
    "full_body": {"front_crop", "turnaround_crop"},
    "face_anchor_refs": {"front_crop", "turnaround_crop"},
}
CHARACTER_MAKEUP_DERIVATION_REQUIRED_FIELDS = ("method", "source_path", "source_sha256", "crop_box")
IDENTITY_FORM_FIELDS = (
    "form",
    "asset_key",
    "anchor_phrase",
    "character_dna",
    "reference_group",
    "reference_atlas",
    "identity_adapters",
    "angle_policy",
    "drift_forbidden",
)
CHARACTER_DNA_FIELDS = ("face", "hair", "outfit", "accessories", "texture")
WARDROBE_PROFILE_CORE_FIELDS = ("silhouette", "palette", "forbidden_drift")
WARDROBE_PROFILE_STRUCTURE_FIELD_GROUPS = (
    ("layers",),
    ("collar", "neckline"),
    ("sleeve",),
    ("waist", "belt", "waist_belt"),
    ("hem",),
    ("fabric", "material", "texture"),
)
ASSET_BUNDLE_REQUIRED_SECTIONS = ("reference", "prompts", "lora", "voice", "adapters", "qc")
IDENTITY_ANGLE_FIELDS = ("allowed", "risky", "requires_extra_reference")
IDENTITY_ADAPTER_SECTIONS = ("image", "video")
GENERATION_CONTROL_ALLOWED_SUPPORT = {
    "supported",
    "unsupported",
    "unsupported_or_unknown",
    "backend_dependent",
    "backend_dependent_verify_adapter",
}
GENERATION_CONTROL_USAGE_KEYS = ("turnaround", "expression", "closeup", "shot")
GENERATION_CONTROL_RECORD_KEYS = ("requested_seed", "effective_seed", "seed_effective", "seed_support", "seed_strategy")
# 身份适配状态枚举从契约派生（与 n2d-identity 写入/校验、n2d-asset-market 重置同源，杜绝 gate 单边漂移）
from n2d_contract import (  # noqa: E402
    IDENTITY_ADAPTER_READY_STATUSES as IDENTITY_READY_STATUSES,
    IDENTITY_ADAPTER_KNOWN_STATUSES as IDENTITY_KNOWN_STATUSES,
)
# 后端→允许 mode 表从契约派生（与 n2d-identity 校验、n2d-asset-market 重置同源）
IDENTITY_ALLOWED_IMAGE_MODES = identity_allowed_modes(IDENTITY_IMAGE_ADAPTERS)
IDENTITY_ALLOWED_VIDEO_MODES = identity_allowed_modes(IDENTITY_VIDEO_ADAPTERS)

ASSET_REFERENCE_TYPE_PREFIX = {
    "scene": "LOC_",
    "location": "LOC_",
    "prop": "PROP_",
    "weapon": "WEAPON_",
    "magic_weapon": "WEAPON_",
    "equipment": "WEAPON_",
    "armory": "WEAPON_",
    "outfit": "OUTFIT_",
    "costume": "OUTFIT_",
    "vfx": "VFX_",
    "effect": "VFX_",
}
ASSET_REFERENCE_REQUIRED_FIELDS = ("id", "type", "name", "reference_group", "constraints", "drift_forbidden")
ASSET_PROP_REQUIRED_FIELDS = ("owner", "current_state", "lifecycle")
ASSET_WEAPON_TYPES = {"weapon", "magic_weapon", "equipment", "armory"}
ASSET_WEAPON_PROFILE_FIELDS = (
    "design_intent",
    "silhouette",
    "scale",
    "material",
    "palette",
    "ornament_motif",
    "carry_modes",
    "combat_usage",
    "vfx_signature",
    "forbidden_drift",
)
ASSET_WEAPON_PROFILE_NAMES = ("weapon_profile", "armory_profile", "equipment_profile")
WEAPON_LIKE_ASSET_TERMS = (
    "武器", "兵器", "刀", "剑", "飞剑", "灵剑", "匕首", "长枪", "弓", "鞭", "锤", "戟",
    "法宝", "法器", "灵器", "本命", "佩剑", "剑鞘", "weapon", "blade", "sword", "sabre",
    "saber", "dagger", "spear", "bow", "artifact", "magic_weapon",
)
SIGNATURE_EQUIPMENT_FIELDS = (
    "signature_equipment",
    "signature_equipment_ids",
    "signature_weapons",
    "weapon_ids",
    "equipment",
)
ACTION_EQUIPMENT_TERMS = (
    "打斗", "战斗", "武打", "追逐", "御剑", "飞行", "腾云", "斗法", "施法", "法术", "招式",
    "刀", "剑", "飞剑", "灵剑", "武器", "法宝", "兵器", "combat", "fight", "action_role",
    "combat_role", "weapon", "sword", "flight",
)
ASSET_SCENE_REQUIRED_FIELDS = ("spatial_layout",)
ASSET_SCENE_RELEASE_FIELD_GROUPS = (
    ("floor_plan", "平面图", "scene_floorplan"),
    ("doors_windows", "门窗", "门", "窗"),
    ("axis_rules", "轴线", "180"),
    ("screen_direction_rules", "左右站位", "screen_direction", "画左", "画右"),
)
# G-I2·2026-06-24：场景多机位锁（场景"四视图"）。角色有 reference_atlas.base_views 渲染多视图，
# 场景此前只有单张空板 + 文字 scene_dna + floorplan 坐标，反打同一空间时门窗/纵深/陈设易漂。
# 这里要求 production 核心/高频 LOC 登记 scene_atlas.base_views：front + 至少一个反打/侧机位 ready 板；
# 确实只从单一机位拍的场景显式标 single_angle=true 豁免。
SCENE_ATLAS_ALT_ANGLES = ("back", "left", "right")
SCENE_DNA_REQUIRED_FIELDS = (
    "belonging_anchor",
    "landmarks",
    "spatial_layout",
    "architecture_materials",
    "color_lighting_weather",
    "resident_assets",
    "forbidden",
)

NATIVE_AUDIO_DISCARD = "discard"
NATIVE_AUDIO_AMBIENCE = "ambience"
NATIVE_AUDIO_KEEP = "keep"

COMPLIANCE_KIND = COMPLIANCE_MANIFEST_KIND
COMPLIANCE_READY = COMPLIANCE_READY_STATUSES
COMPLIANCE_DONE = COMPLIANCE_DONE_STATUSES
PLATFORM_REVIEW_STATUSES = COMPLIANCE_PLATFORM_REVIEW_STATUSES
PRE_BROADCAST_STATUSES = COMPLIANCE_PRE_BROADCAST_STATUSES
AI_LABEL_STATUSES = COMPLIANCE_AI_LABEL_STATUSES
STATUS_LIKE_VALUES = COMPLIANCE_STATUS_LIKE_VALUES
OVERSEAS_PLATFORMS = COMPLIANCE_OVERSEAS_PLATFORMS
DOMESTIC_REGIONS = COMPLIANCE_DOMESTIC_REGIONS


def gate_family(stage: str) -> str:
    """Map explicit preflight stages to the production stage they validate."""
    return {
        "image_preflight": "image",
        "video_preflight": "video",
    }.get(stage, stage)


def add(sev: str, dim: str, loc: str, msg: str, **extra: object) -> None:
    item: Dict[str, object] = {"sev": sev, "dim": dim, "loc": loc, "msg": msg}
    item.update(extra)
    findings.append(item)


PRODUCTION_CONSISTENCY_VALUES = {
    "production", "prod", "release", "strict", "final", "publish", "published",
    "production_no_cost_image", "no_cost_image",
    "投放", "上线", "正式", "发布", "严格", "生产", "可投放", "交付",
    "无成本图片", "无成本生图",
}
DEMO_CONSISTENCY_VALUES = {"demo", "draft", "internal", "relaxed", "测试", "草稿", "内部", "宽松"}


def _profile_values(root: str) -> List[str]:
    """Collect explicit consistency profile values from env and project settings."""
    env = os.environ.get("N2D_CONSISTENCY_PROFILE", "").strip()
    values = [env]
    for key in ("一致性严格度", "一致性发布档", "一致性落地档", "一致性验收档", "制作质量档"):
        try:
            values.append(get_setting(root, key, "").strip())
        except Exception:
            continue
    return [v for v in values if v]


def _contains_profile_marker(values: Sequence[str], markers: set) -> bool:
    joined = " ".join(v for v in values if v).lower()
    return any(str(v).lower() in joined for v in markers)


def _production_profile_inferred(root: str, stage: str = "", ep: str = "") -> bool:
    stage_key = gate_family(stage or "")
    if stage_key in {"compose", "review"}:
        return True
    try:
        if len(glob.glob(os.path.join(root, "脚本", "*", "storyboard.json"))) >= 2:
            return True
    except Exception:
        pass
    ep_dirs: List[str] = []
    if ep:
        ep_dirs.extend([
            os.path.join(root, "出视频", ep),
            os.path.join(root, "合成", ep),
            os.path.join(root, "成片", ep),
            os.path.join(root, "交付", ep),
        ])
    ep_dirs.extend([
        os.path.join(root, "合成"),
        os.path.join(root, "成片"),
        os.path.join(root, "交付"),
    ])
    for base in ep_dirs:
        try:
            if any(glob.glob(os.path.join(base, "**", pattern), recursive=True) for pattern in ("*.mp4", "*.mov", "*.m4v")):
                return True
        except Exception:
            continue
    return False


def consistency_release_profile(root: str, stage: str = "", ep: str = "") -> str:
    """Return demo|production for consistency escalation rules."""
    values = _profile_values(root)
    if _contains_profile_marker(values, PRODUCTION_CONSISTENCY_VALUES):
        return "production"
    if _contains_profile_marker(values, DEMO_CONSISTENCY_VALUES):
        return "demo"
    if _production_profile_inferred(root, stage, ep):
        return "production"
    return "demo"


def _settings_values(root: str, keys: Sequence[str]) -> List[str]:
    values: List[str] = []
    for key in keys:
        try:
            values.append(get_setting(root, key, "").strip())
        except Exception:
            continue
    return [v for v in values if v]


def _project_has_english_subtitles(root: str, ep: str) -> bool:
    for rel in (
        os.path.join("脚本", ep, "字幕_英文.srt"),
        os.path.join("脚本", ep, "字幕_双语.srt"),
        os.path.join("脚本", ep, "subtitles_en.srt"),
    ):
        if os.path.isfile(os.path.join(root, rel)):
            return True
    lang_blob = " ".join(_settings_values(root, ("字幕语言", "subtitle_languages", "本地化语言"))).lower()
    return any(token in lang_blob for token in ("en", "english", "英文", "中英", "双语"))


def _project_has_overseas_release_target(root: str) -> bool:
    data = load_json(compliance_manifest_path(root))
    if isinstance(data, dict):
        localization = data.get("localization") if isinstance(data.get("localization"), dict) else {}
        if _status(localization.get("status")) in {"ready", "done"}:
            languages = {str(x).lower() for x in _listify(localization.get("subtitle_languages"))}
            if any(x and x not in {"zh", "cn", "chinese", "中文"} for x in languages):
                return True
        for target in _listify((data.get("platform_review") or {}).get("targets") if isinstance(data.get("platform_review"), dict) else []):
            if not isinstance(target, dict):
                continue
            platform = _status(target.get("platform")).lower()
            region = _status(target.get("region")).lower()
            language = _status(target.get("language")).lower()
            if (
                target.get("requires_localization") is True
                or platform in OVERSEAS_PLATFORMS
                or (region and region not in DOMESTIC_REGIONS)
                or (language and language not in {"zh", "cn", "chinese", "中文"})
            ):
                return True
    blob = " ".join(_settings_values(root, ("目标平台", "发行地区", "合规用途", "变现模式", "distribution_intent"))).lower()
    return any(token.lower() in blob for token in (
        "海外", "出海", "国际", "北美", "global", "overseas", "tiktok", "youtube", "reelshort", "english", "英文"
    ))


def exists(path: str) -> bool:
    return os.path.exists(path)


def load_json(path: str):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


CHARACTER_ID_RE = re.compile(r"\bCHAR_\d{2,}\b")
ASSET_ID_RE = re.compile(r"\b(?:LOC|PROP|WEAPON|OUTFIT|VFX)_\d{2,}\b")

# 一致性机检的结构阈值（单一真值源·别再散成内联魔数）：改判据来这里，别埋进各 check 体里。
ENDFRAME_EXEMPT_REASON_MIN_CHARS = 6   # 首尾双帧豁免理由的实质字数下限（< 此 = 占位/单字 → BLOCK）
ANCHOR_TOKEN_MIN_CHARS = 2             # 锚定相按「·」切后单 token 的最短可比长度（过滤单字噪声）


def _episode_reference_texts(root: str, ep: str) -> Iterable[str]:
    """Text surfaces that define the current episode's registry references."""
    roots = [
        os.path.join(root, "脚本", ep),
        os.path.join(root, "出图", ep, "prompt"),
        os.path.join(root, "出视频", ep, "prompt"),
    ]
    for base in roots:
        if not os.path.isdir(base):
            continue
        for pattern in ("*.md", "*.json", "*.txt"):
            for path in sorted(glob.glob(os.path.join(base, pattern))):
                try:
                    with open(path, encoding="utf-8") as fh:
                        yield fh.read()
                except Exception:
                    continue


def episode_registry_reference_ids(root: str, ep: str) -> Tuple[set, set]:
    """Return character and non-character registry ids used by one episode.

    The registries can contain planned future characters/assets. A stage gate for
    第N集 should validate registry schemas globally, but strict reference image
    existence only for ids this episode actually consumes.
    """
    text = "\n".join(_episode_reference_texts(root, ep))
    return set(CHARACTER_ID_RE.findall(text)), set(ASSET_ID_RE.findall(text))


MIDFRAME_SELF_CHECK_KEYS = ("self_check", "midframe_self_check", "prompt_self_check")
MIDFRAME_SELF_CHECK_PASS = {"pass", "passed", "ok", "true", "yes", "1", "✅", "通过"}
PROHIBITED_FACE_PATCH_LABEL = "本地贴脸修复产物禁用"
PROHIBITED_FACE_PATCH_STRONG_TOKENS = (
    "local_face_patch",
    "face_patch",
    "face-patch",
    "facepaste",
    "face_paste",
    "face paste",
    "faceswap",
    "face_swap",
    "face-swap",
    "facefix",
    "face_fix",
    "inswapper",
    "facefusion",
    "roop",
)
PROHIBITED_FACE_PATCH_OPERATION_TOKENS = (
    "crop_resize_color_match",
    "alpha_blend",
    "poisson_clone",
    "seamless_clone",
)


def _production_events_path(root: str) -> str:
    return os.path.join(root, "生产数据", "production_events.jsonl")


def _norm_rel_path(path: str) -> str:
    return os.path.normpath(str(path).strip()).replace(os.sep, "/")


def _asset_matches(root: str, asset: object, target_rel: str) -> bool:
    if not asset:
        return False
    asset_s = str(asset).strip()
    target_rel_norm = _norm_rel_path(target_rel)
    target_abs = os.path.abspath(target_rel if os.path.isabs(target_rel) else os.path.join(root, target_rel))
    if os.path.isabs(asset_s):
        return os.path.abspath(asset_s) == target_abs
    return _norm_rel_path(asset_s) == target_rel_norm or os.path.abspath(os.path.join(root, asset_s)) == target_abs


def _load_production_events(root: str) -> List[Dict[str, Any]]:
    path = _production_events_path(root)
    if not os.path.isfile(path):
        return []
    events: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if isinstance(item, dict):
                    events.append(item)
    except Exception:
        return []
    return events


def _latest_asset_generation_event(root: str, ep: str, asset_rel: str) -> Optional[Dict[str, Any]]:
    latest: Optional[Dict[str, Any]] = None
    for event in _load_production_events(root):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        generation = event.get("generation") if isinstance(event.get("generation"), dict) else {}
        if _asset_matches(root, generation.get("asset") or event.get("asset"), asset_rel):
            latest = event
    return latest


def _event_generation(event: Dict[str, Any]) -> Dict[str, Any]:
    return event.get("generation") if isinstance(event.get("generation"), dict) else {}


def _event_meta(event: Dict[str, Any]) -> Dict[str, Any]:
    return event.get("meta") if isinstance(event.get("meta"), dict) else {}


def _event_cost(event: Dict[str, Any]) -> Dict[str, Any]:
    return event.get("cost") if isinstance(event.get("cost"), dict) else {}


def _event_asset_rel(root: str, event: Dict[str, Any]) -> Optional[str]:
    generation = _event_generation(event)
    asset = generation.get("asset") or event.get("asset")
    if not asset:
        return None
    raw = str(asset).strip()
    if not raw:
        return None
    if os.path.isabs(raw):
        try:
            return os.path.relpath(os.path.abspath(raw), os.path.abspath(root)).replace(os.sep, "/")
        except Exception:
            return raw.replace(os.sep, "/")
    return _norm_rel_path(raw)


def _is_prohibited_face_patch_event(event: Dict[str, Any]) -> bool:
    generation = _event_generation(event)
    meta = _event_meta(event)
    cost = _event_cost(event)
    fields = [
        event.get("provider"),
        event.get("source"),
        event.get("method"),
        cost.get("provider"),
        cost.get("method"),
        generation.get("provider"),
        generation.get("method"),
        generation.get("redraw_category"),
        generation.get("redraw_reason"),
        meta.get("provider"),
        meta.get("method"),
    ]
    text = " ".join(str(v) for v in fields if v is not None).lower()
    if any(token in text for token in PROHIBITED_FACE_PATCH_STRONG_TOKENS):
        return True
    return ("face" in text or "脸" in text) and any(
        token in text for token in PROHIBITED_FACE_PATCH_OPERATION_TOKENS
    )


def _prohibited_face_patch_outputs(root: str, ep: str) -> List[Dict[str, Any]]:
    latest: Dict[str, tuple[int, Dict[str, Any]]] = {}
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        rel = _event_asset_rel(root, event)
        if rel and rel.endswith(".png"):
            latest[rel] = (idx, event)

    out: List[Dict[str, Any]] = []
    for rel, (line_no, event) in latest.items():
        if not _is_prohibited_face_patch_event(event):
            continue
        generation = _event_generation(event)
        meta = _event_meta(event)
        cost = _event_cost(event)
        out.append({
            "png": rel,
            "line": line_no,
            "provider": str(cost.get("provider") or generation.get("provider") or event.get("provider") or event.get("source") or ""),
            "method": str(meta.get("method") or generation.get("method") or cost.get("method") or event.get("method") or ""),
        })
    return sorted(out, key=lambda r: str(r.get("png") or ""))


def _seed_record_value(event: Dict[str, Any], key: str) -> str:
    meta = _event_meta(event)
    generation = _event_generation(event)
    for source in (meta, generation, event):
        value = source.get(key) if isinstance(source, dict) else None
        value_s = str(value or "").strip()
        if value_s:
            return value_s
    return ""


def check_seed_event_records(root: str, ep: str) -> None:
    """If a generation tried to use a seed, the ledger must say whether it worked.

    Closed backends may not expose seed. That is acceptable only when the
    production event records `seed_effective=false` and the support state, so the
    project does not accidentally treat the output as reproducible.
    """
    path = _production_events_path(root)
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        requested = _seed_record_value(event, "requested_seed")
        if not requested:
            continue
        missing = [
            key for key in ("seed_strategy", "seed_support", "seed_effective")
            if not _seed_record_value(event, key)
        ]
        if missing:
            add(WARN, "固定 Seed", f"{path}:line {idx}",
                "image 生成事件记录了 requested_seed，但缺少 " + ", ".join(missing) +
                "；支持 seed 时要记 effective_seed/seed_effective=true，不支持时要记 seed_effective=false + seed_support=unsupported_or_unknown。")
        effective = _seed_record_value(event, "seed_effective").lower()
        if effective in {"true", "1", "yes", "pass", "supported"} and not _seed_record_value(event, "effective_seed"):
            add(WARN, "固定 Seed", f"{path}:line {idx}",
                "seed_effective=true 但缺 effective_seed；无法证明实际传入的是固定 seed pool。")


RECIPE_EVIDENCE_STAGES = {"image", "video"}
RECIPE_REQUIRED_FIELDS = (
    "recipe_hash",
    "prompt_sha256",
    "reference_bundle_sha256",
    "backend_version",
    "quality_tier",
    "actual_image_inputs",
)


def _event_value_any(event: Mapping[str, Any], *keys: str) -> Any:
    generation = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    meta = event.get("meta") if isinstance(event.get("meta"), Mapping) else {}
    cost = event.get("cost") if isinstance(event.get("cost"), Mapping) else {}
    for key in keys:
        for source in (event, generation, meta, cost):
            value = source.get(key) if isinstance(source, Mapping) else None
            if value not in (None, "", [], {}):
                return value
    return ""


def _event_status_pass(event: Mapping[str, Any]) -> bool:
    generation = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    status = str(generation.get("status") or event.get("status") or "").strip().lower()
    return status in {"", "pass", "passed", "ok", "success", "succeeded", "done", "ready"}


def _final_media_exists(root: str, ep: str, stages: Sequence[str] = ("image", "video")) -> bool:
    return bool(_final_media_rels(root, ep, stages))


def _final_media_rels(root: str, ep: str, stages: Sequence[str] = ("image", "video")) -> List[str]:
    patterns: List[str] = []
    if "image" in stages:
        patterns.append(os.path.join(root, "出图", ep, "图片", "*.png"))
    if "video" in stages:
        patterns.append(os.path.join(root, "出视频", ep, "视频", "*.mp4"))
    rels: List[str] = []
    for pattern in patterns:
        for path in glob.glob(pattern):
            rels.append(_norm_rel_path(os.path.relpath(path, root)))
    return sorted(set(rels))


def _recipe_return_stage_for_asset(rel: str) -> str:
    return "image" if rel.lower().endswith(".png") else "video"


def _recipe_event_missing_fields(event: Mapping[str, Any]) -> List[str]:
    missing = [key for key in RECIPE_REQUIRED_FIELDS if _event_value_any(event, key) in (None, "", [], {})]
    seed_effective = _event_value_any(event, "seed_effective", "effective_seed")
    if seed_effective in (None, "", [], {}):
        missing.append("seed_effective/effective_seed=false")
    else:
        seed_text = str(seed_effective).strip().lower()
        if seed_text in {"true", "1", "yes", "supported", "pass"} and _event_value_any(event, "effective_seed") in (None, "", [], {}):
            missing.append("effective_seed")
        if seed_text in {"false", "0", "no", "none", "unsupported", "unsupported_or_unknown"} and _event_value_any(event, "seed_support") in (None, "", [], {}):
            missing.append("seed_support")
    return missing


def check_generation_recipe_evidence(root: str, ep: str, stage: str) -> None:
    """Release-grade recipe evidence for each final AI-generated image/video media."""
    production = consistency_release_profile(root, stage, ep) == "production"
    sev = BLOCK if production else WARN
    path = _production_events_path(root)
    latest_by_asset: Dict[str, Tuple[int, Mapping[str, Any]]] = {}
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() not in RECIPE_EVIDENCE_STAGES:
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        if not _event_status_pass(event):
            continue
        rel = _event_asset_rel(root, event)
        if rel:
            latest_by_asset[rel] = (idx, event)
    final_rels = _final_media_rels(root, ep, RECIPE_EVIDENCE_STAGES)
    targets = final_rels or sorted(latest_by_asset)
    if not targets:
        if _final_media_exists(root, ep, RECIPE_EVIDENCE_STAGES):
            add(
                sev,
                "生成配方证据",
                path,
                "本集已有最终图片/视频媒体，但 production_events.jsonl 缺 image/video generation/redraw pass 记录；"
                "无法追溯 recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。",
                return_to_stage="image",
            )
        return
    for rel in targets:
        if rel not in latest_by_asset:
            add(
                sev,
                "生成配方证据",
                path,
                f"{rel} 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；"
                "无法追溯 recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。",
                return_to_stage=_recipe_return_stage_for_asset(rel),
            )
            continue
        idx, event = latest_by_asset[rel]
        missing = _recipe_event_missing_fields(event)
        if not missing:
            continue
        add(
            sev,
            "生成配方证据",
            f"{path}:line {idx}",
            f"{rel} 生成事件缺必填配方证据：{', '.join(missing)}。"
            "每个最终媒体必须记录 recipe_hash/prompt_sha256/reference_bundle_sha256/backend_version/"
            "quality_tier/actual_image_inputs，并在 seed 不生效时显式 seed_effective=false + seed_support。",
            return_to_stage=_recipe_return_stage_for_asset(rel),
        )


def _midframe_self_check_value(event: Dict[str, Any]) -> str:
    meta = event.get("meta") if isinstance(event.get("meta"), dict) else {}
    for key in MIDFRAME_SELF_CHECK_KEYS:
        value = str(meta.get(key) or "").strip()
        if value:
            return value
    return ""


def _check_midframe_generation_self_check(root: str, ep: str, rel_png: str, loc: str, idx: int) -> None:
    """A declared midframe may exist on disk but still be a bad anchor.

    The visual judgment is human/agent-side, but the gate can make that judgment
    auditable: every landed `_mid` / anchor must have a latest image generation
    ledger event with status=pass and self_check=pass.
    """
    event = _latest_asset_generation_event(root, ep, rel_png)
    if event is None:
        add(BLOCK, "中段锚帧", loc,
            f"锚帧 {idx} PNG 已存在但缺中段动作自检 pass 记账：{rel_png}；"
            "落档后必须记录 image generation --status pass --meta self_check=pass，"
            "确认它不是只锁人锁景，而是姿态/动作确实落在首尾帧中间。")
        return
    generation = event.get("generation") if isinstance(event.get("generation"), dict) else {}
    status = str(generation.get("status") or event.get("status") or "").strip().lower()
    if status != "pass":
        add(BLOCK, "中段锚帧", loc,
            f"锚帧 {idx} 最近一次生成记录不是 pass（status={status or '缺失'}）：{rel_png}；"
            "先重抽或重新自检并记录 self_check=pass。")
        return
    self_check = _midframe_self_check_value(event)
    if self_check.lower() not in MIDFRAME_SELF_CHECK_PASS:
        add(BLOCK, "中段锚帧", loc,
            f"锚帧 {idx} 缺少通过值 self_check=pass（当前={self_check or '缺失'}）：{rel_png}；"
            "中段锚帧必须按本镜「中段锚帧生成方式/自检」确认动作推进成立，不能只凭 PNG 存在放行。")


def compliance_manifest_path(root: str) -> str:
    return os.path.join(root, "合规", "compliance_manifest.json")


def _listify(value) -> List:
    return value if isinstance(value, list) else []


def _status(value) -> str:
    return str(value or "").strip()


PLACEHOLDER_MARKERS = COMPLIANCE_PLACEHOLDER_MARKERS


def _filled(value) -> bool:
    text = _status(value)
    if not text:
        return False
    lower = text.lower()
    if lower in {"xxx", "xx", "x", "...", "n/a?"}:
        return False
    return not any(marker in lower for marker in PLACEHOLDER_MARKERS)


def _looks_like_status_value(value) -> bool:
    return _status(value).lower() in STATUS_LIKE_VALUES


def _valid_iso_date(value) -> bool:
    try:
        dt.date.fromisoformat(_status(value))
        return True
    except ValueError:
        return False


def _has_embedded_iso_date(value) -> bool:
    match = re.search(r"\d{4}-\d{2}-\d{2}", _status(value))
    if not match:
        return False
    try:
        dt.date.fromisoformat(match.group(0))
        return True
    except ValueError:
        return False


def _is_internal_distribution(data: dict) -> bool:
    """内部 demo（不投放）判定——与 n2d-compliance/scripts/compliance.py 同源：
    只认契约常量 COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS，不再各自维护口语别名。"""
    return _status(data.get("distribution_intent")).lower() in COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS


def _is_publish_intent(data: dict) -> bool:
    return not _is_internal_distribution(data)


# internal_only 免检范围 = 契约 COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS（platform_review / overseas_localization）：
# 这些字段域的 BLOCK 降为 INFO 并加注，角色/声音授权照常 BLOCK。
INTERNAL_SKIP_NOTE = "（内部 demo 免检，转投放前需补）"


def _compliance_block(loc: str, msg: str) -> None:
    add(BLOCK, "合规前置", loc, msg)


def _compliance_warn(loc: str, msg: str) -> None:
    add(WARN, "合规前置", loc, msg)


def _episode_in_scope(ep: str, value) -> bool:
    if value in (None, "", [], "all", "全剧"):
        return True
    if isinstance(value, list):
        return ep in value or "all" in value or "全剧" in value
    return str(value).strip() in (ep, "all", "全剧")


def _identity_character_ids(root: str) -> List[str]:
    data = load_json(identity_registry_path(root))
    if not isinstance(data, dict):
        return []
    ids = []
    for char in data.get("characters", []) or []:
        if isinstance(char, dict) and _status(char.get("id")):
            ids.append(_status(char.get("id")))
    return ids


def _check_compliance_rights(root: str, data: dict, loc: str) -> None:
    rights = data.get("rights")
    if not isinstance(rights, dict):
        _compliance_block(loc, "缺 rights；源小说/改编权/素材版权必须在出图前落合规包")
        return
    source = rights.get("source_text")
    if not isinstance(source, dict):
        _compliance_block(f"{loc} rights.source_text", "缺 source_text 权利来源；必须是 original/public_domain/licensed/user_declared 之一")
    else:
        status = _status(source.get("status"))
        if status not in COMPLIANCE_ALLOWED_RIGHTS or status in ("unknown", ""):
            _compliance_block(f"{loc} rights.source_text", f"源文本权利状态不可用：{status or 'missing'}")
        if status in COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED and not _filled(source.get("evidence")):
            _compliance_block(f"{loc} rights.source_text", "licensed/stock_licensed/user_declared 必须填写 evidence/ref，不能只口头说已授权")

    for key in ("adaptation", "music_bgm", "sfx", "fonts"):
        item = rights.get(key)
        if not isinstance(item, dict):
            _compliance_block(f"{loc} rights.{key}", f"缺 {key} 权利状态；不用也要写 not_applicable，不能空着")
            continue
        status = _status(item.get("status"))
        if not status or status not in COMPLIANCE_ALLOWED_RIGHTS:
            _compliance_block(f"{loc} rights.{key}", f"{key} 权利状态未知：{status or 'missing'}")
        if status in COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED and not _filled(item.get("evidence")):
            _compliance_block(f"{loc} rights.{key}", f"{key} 标为 {status} 但缺 evidence/ref")


def _check_compliance_characters(root: str, data: dict, loc: str) -> None:
    section = data.get("character_likeness")
    if not isinstance(section, dict):
        _compliance_block(loc, "缺 character_likeness；角色形象/真人肖像授权必须在出图前落合规包")
        return
    entries = _listify(section.get("characters"))
    by_id = {str(item.get("character_id")): item for item in entries if isinstance(item, dict) and item.get("character_id")}
    for char_id in _identity_character_ids(root):
        if char_id not in by_id:
            _compliance_block(f"{loc} character_likeness", f"identity_registry 中角色 {char_id} 缺肖像/角色授权记录")
    for idx, item in enumerate(entries, 1):
        if not isinstance(item, dict):
            _compliance_block(f"{loc} character_likeness.characters[{idx}]", "角色授权记录必须是对象")
            continue
        status = _status(item.get("status"))
        iloc = f"{loc} character_likeness.{item.get('character_id', idx)}"
        if status in COMPLIANCE_BLOCKED_CHARACTER or status not in COMPLIANCE_APPROVED_CHARACTER:
            _compliance_block(iloc, f"角色/肖像授权状态不可放行：{status or 'missing'}")
        if status in ("actor_authorized", "self_authorized", "licensed_likeness") and not _filled(item.get("evidence")):
            _compliance_block(iloc, "真人/演员/授权形象必须填写授权 evidence/ref")


def _check_compliance_voice(data: dict, loc: str) -> None:
    section = data.get("voice")
    if not isinstance(section, dict):
        _compliance_block(loc, "缺 voice；声音克隆/参考音授权必须在配音和出视频前落合规包")
        return
    status = _status(section.get("status"))
    if status not in COMPLIANCE_SAFE_VOICE:
        _compliance_block(f"{loc} voice", f"声音授权状态不可放行：{status or 'missing'}")
    if section.get("uses_voice_clone") is True or status == "authorized_clone":
        auth = _status(section.get("authorization_status"))
        if auth != "approved":
            _compliance_block(f"{loc} voice", "使用声音克隆/参考音时 authorization_status 必须是 approved")
        if not _filled(section.get("evidence")):
            _compliance_block(f"{loc} voice", "声音克隆/参考音授权缺 evidence/ref")


def _check_platform_targets(data: dict, loc: str, stage: str) -> None:
    if stage not in ("compose", "review"):
        return
    internal = _is_internal_distribution(data)

    def flag(floc: str, msg: str) -> None:
        # platform_review / overseas_localization ∈ COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS：
        # internal_only 时降 BLOCK → INFO；其余（角色/声音授权）不走本函数、照常 BLOCK。
        if internal:
            add(INFO, "合规前置", floc, f"{msg}{INTERNAL_SKIP_NOTE}")
        else:
            _compliance_block(floc, msg)

    if internal:
        _compliance_warn(
            loc,
            "distribution_intent=internal_only；"
            f"{' / '.join(COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS)} 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放",
        )
    targets = _listify((data.get("platform_review") or {}).get("targets"))
    if not targets:
        flag(f"{loc} platform_review", "发布候选缺 platform_review.targets；目标平台审核必须在合成前确定")
        return
    localization = data.get("localization") if isinstance(data.get("localization"), dict) else {}
    for idx, target in enumerate(targets, 1):
        if not isinstance(target, dict):
            flag(f"{loc} platform_review.targets[{idx}]", "平台审核项必须是对象")
            continue
        platform = _status(target.get("platform"))
        tloc = f"{loc} platform_review.{platform or idx}"
        for key in ("platform", "region", "policy_profile", "profile_checked_at", "copyright_review", "content_rating_review"):
            if not _filled(target.get(key)):
                flag(tloc, f"平台审核缺字段：{key}")
        for key in ("platform", "region"):
            if _filled(target.get(key)) and _looks_like_status_value(target.get(key)):
                flag(tloc, f"{key} 必须是具体平台/地区，不能写状态占位：{_status(target.get(key))}")
        if _filled(target.get("policy_profile")) and not _has_embedded_iso_date(target.get("policy_profile")):
            flag(tloc, "policy_profile 必须带 YYYY-MM-DD 检查日期，例如 douyin_policy_2026-06-08")
        if _filled(target.get("profile_checked_at")) and not _valid_iso_date(target.get("profile_checked_at")):
            flag(tloc, "profile_checked_at 必须是 YYYY-MM-DD")
        for key in ("copyright_review", "content_rating_review"):
            if _status(target.get(key)) not in PLATFORM_REVIEW_STATUSES:
                flag(tloc, f"{key} 必须 ready/done/not_applicable")
        region = _status(target.get("region")).lower()
        overseas = target.get("requires_localization") is True or platform.lower() in OVERSEAS_PLATFORMS or (region and region not in DOMESTIC_REGIONS)
        if overseas:
            if _status(localization.get("status")) not in ("ready", "done"):
                flag(f"{loc} localization", f"{platform or '海外平台'} 目标需要出海本地化；localization.status 必须 ready/done")
            languages = set(str(x).lower() for x in _listify(localization.get("subtitle_languages")))
            required = _status(target.get("language")).lower()
            if required and required not in languages:
                flag(f"{loc} localization", f"目标语言 {required} 不在 subtitle_languages 中")


def _check_regulatory_filing(data: dict, loc: str, stage: str) -> None:
    """广电总局 网络微短剧 备案/分级/播前审核（2026 新规：AIGC 全面纳入分级+播前审核）。
    与 platform_review 同列内部 demo 免检域：internal_only 时 BLOCK 降 INFO。"""
    if stage not in ("compose", "review"):
        return
    internal = _is_internal_distribution(data)

    def flag(floc: str, msg: str) -> None:
        if internal:
            add(INFO, "合规前置", floc, f"{msg}{INTERNAL_SKIP_NOTE}")
        else:
            _compliance_block(floc, msg)

    reg = data.get("regulatory_filing")
    if not isinstance(reg, dict):
        flag(f"{loc} regulatory_filing", "缺 regulatory_filing；境内投放须先过广电备案/分级/播前审核（2026 新规）")
        return
    if reg.get("applicable") is False:
        if not _filled(reg.get("notes")):
            flag(f"{loc} regulatory_filing", "applicable=false 须在 notes 写明理由（纯海外/内部预览等）")
        return
    pbr = _status(reg.get("pre_broadcast_review"))
    if pbr and pbr not in PRE_BROADCAST_STATUSES:
        flag(f"{loc} regulatory_filing", f"pre_broadcast_review 须为 {'/'.join(sorted(PRE_BROADCAST_STATUSES))}；got {pbr}")
    if pbr in ("", "pending"):
        flag(f"{loc} regulatory_filing", "pre_broadcast_review 不能停在 pending（境内投放须先过播前审核）")
    elif stage == "review" and pbr not in COMPLIANCE_DONE:
        flag(f"{loc} regulatory_filing", "pre_broadcast_review 须 done 才能过 review")
    paid = _status(data.get("distribution_intent")) == "paid_distribution"
    if (paid or stage == "review") and not _filled(reg.get("release_filing_no")):
        flag(f"{loc} regulatory_filing", "release_filing_no（上线备案号）付费投放/review 前必填，不能留 TODO 占位")
    if _filled(reg.get("filed_at")) and not _valid_iso_date(reg.get("filed_at")):
        flag(f"{loc} regulatory_filing", "filed_at 须为 YYYY-MM-DD")


def _ai_labeling_required(data: dict) -> bool:
    """AI 生成合成内容标识是否适用。
    默认适用；仅 ai_labeling.applicable is False 关闭提示。AI 标识不得阻断 n2d 主流程。"""
    ai = data.get("ai_labeling")
    if isinstance(ai, dict) and ai.get("applicable") is False:
        return False
    return True


def _check_ai_labeling(data: dict, loc: str, stage: str) -> None:
    """AI 生成合成内容标识只做 INFO 提醒，不阻断 compose/review 主流程。"""
    if stage not in ("compose", "review"):
        return

    def flag(floc: str, msg: str) -> None:
        add(INFO, "合规提示", floc, f"{msg}（AI 标识非阻断；发布前按目标地区/平台补齐）")

    ai = data.get("ai_labeling")
    if not isinstance(ai, dict):
        flag(f"{loc} ai_labeling", "缺 ai_labeling；无法自动准备显式标签/元数据隐式标识")
        return
    if not _ai_labeling_required(data):
        if not _filled(ai.get("notes")):
            flag(f"{loc} ai_labeling", "applicable=false 建议在 notes 写明理由（纯海外按目标平台 AIGC 披露等）")
        return
    label = ai.get("explicit_label") if isinstance(ai.get("explicit_label"), dict) else {}
    meta = ai.get("implicit_metadata") if isinstance(ai.get("implicit_metadata"), dict) else {}
    lstatus = _status(label.get("status"))
    if lstatus and lstatus not in AI_LABEL_STATUSES:
        flag(f"{loc} ai_labeling", f"explicit_label.status 建议为 {'/'.join(AI_LABEL_STATUSES)}；got {lstatus}")
    if not _filled(label.get("text")):
        flag(f"{loc} ai_labeling", "explicit_label.text 缺显式标签文案（如「AI生成」）")
    for key in ("service_provider_code", "content_id"):
        if not _filled(meta.get(key)):
            flag(f"{loc} ai_labeling", f"implicit_metadata.{key} 缺；无法自动写入完整元数据隐式标识")
    if stage == "review":
        if lstatus != "done":
            flag(f"{loc} ai_labeling", "explicit_label.status 尚非 done；成片未确认已落显式标签")
        if meta.get("applied") is not True:
            flag(f"{loc} ai_labeling", "implicit_metadata.applied 尚非 true；成片未确认已写元数据")


def check_compliance_manifest(root: str, ep: str, stage: str) -> None:
    """Front-load rights, character/voice authorization, platform, localization and regulatory gates.

    AI 标识仅做 INFO 待办；不得把未落标升级为 compose/review blocker。
    """
    p = compliance_manifest_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "合规前置", p, "缺少或无法解析合规/compliance_manifest.json；角色授权、声音克隆、平台审核、出海本地化必须进入 gate")
        return
    if data.get("kind") != COMPLIANCE_KIND:
        _compliance_block(p, f"kind 必须是 {COMPLIANCE_KIND}")
    _check_compliance_rights(root, data, p)
    _check_compliance_characters(root, data, p)
    _check_compliance_voice(data, p)
    _check_platform_targets(data, p, stage)
    _check_regulatory_filing(data, p, stage)
    _check_ai_labeling(data, p, stage)


def row_for(root: str, ep: str) -> Tuple[List[str], Optional[Dict[str, str]]]:
    try:
        header, rows = parse_progress(root)
    except Exception as e:
        add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"进度表不可解析：{e}")
        return [], None
    row = next((r for r in rows if r.get("_ep") == ep), None)
    if row is None:
        add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"{ep} 不在进度表")
    return header, row


def require_progress(root: str, ep: str, cols: Iterable[str]) -> None:
    header, row = row_for(root, ep)
    if row is None:
        return
    for col in cols:
        if col not in header:
            add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"缺进度列：{col}")
        elif not is_progress_satisfied(root, row, col):
            add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"{ep}「{col}」未完成（当前 {row.get(col, '⬜')}）")


def _artifact_exists(root: str, ep: str, rel: str) -> bool:
    return os.path.exists(os.path.join(root, str(rel).format(ep=ep)))


def check_progress_artifact_signoff(root: str, ep: str, cols: Iterable[str]) -> None:
    """文本×产物双签：被判 ✅ 的列，用 STAGE_GRAPH 的 output_contract/outputs 验关键产物真在磁盘。

    `require_progress` 只信 `_进度.md` 单元格 ✅，手改进度把"配音 ✅"写上但实际没产 时长清单 也放行。
    本检查把"单一真相"从纯文本升级为"文本+产物双签"：✅ 但关键产物缺 → BLOCK，回退对应阶段。
    """
    header, row = row_for(root, ep)
    if row is None:
        return
    for col in cols:
        if col not in header or not is_done(row.get(col, "")):
            continue  # 未完成的列由 require_progress 负责，这里只验已判 ✅ 的
        spec = stage_for_progress_column(col)
        if not spec:
            continue
        loc = os.path.join(root, "_进度.md")
        oc = spec.get("output_contract")
        if isinstance(oc, dict) and oc.get("any_of"):
            variants = [v for v in oc["any_of"] if isinstance(v, dict)]
            if not any(all(_artifact_exists(root, ep, a) for a in v.get("all_of", ())) for v in variants):
                labels = " 或 ".join(str(v.get("label", "")) for v in variants)
                add(BLOCK, "产物签收", loc,
                    f"{ep}「{col}」标 ✅ 但关键产物缺失（需满足其一：{labels}）——文本与产物背离，补产物或修进度",
                    return_to_stage=spec.get("return_to_stage"))
        else:
            outs = spec.get("outputs") or ()
            if outs and not any(_artifact_exists(root, ep, a) for a in outs):
                add(BLOCK, "产物签收", loc,
                    f"{ep}「{col}」标 ✅ 但「{spec.get('label')}」产物一个都不在磁盘（如 {str(outs[0]).format(ep=ep)}）"
                    f"——幻影完成，补产物或修进度", return_to_stage=spec.get("return_to_stage"))


def progress_fraction_done(root: str, ep: str, col: str) -> bool:
    _, row = row_for(root, ep)
    if not row:
        return False
    return is_done(row.get(col, ""))


def check_placeholder_policy(root: str, ep: str, stage: str) -> None:
    if is_native_av_production(root):
        # 原生音画：说话镜由视频后端一次出同步音画，不靠配音时长；占位/缺配音不作硬闸。
        return
    ph = voice_is_placeholder(root, ep)
    if ph is None:
        if stage in {"image", "video", "compose"}:
            add(BLOCK, "配音", ep, "未找到可判定的时长清单；无法确认真实配音或 rough timing，先跑 n2d-voice 生成 `时长清单.json`")
        else:
            add(WARN, "配音", ep, "未找到可判定的占位字段；若尚未配音，下游应先补齐")
        return
    if not ph:
        return
    if stage == "image" and is_video_first(root):
        add(WARN, "配音", ep, "当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时")
    elif stage == "video" and is_video_first(root):
        add(WARN, "配音", ep, "先出视频后配音模式已放行占位时长进入出视频；后期补真音可能需要重出视频")
    else:
        add(BLOCK, "配音", ep, "配音仍为占位音色；`配音先行` 模式下该阶段不应继续，先 n2d-voice 换真实配音并重定时")


def check_voiceover_fingerprint(root: str, ep: str) -> None:
    """配音定稿后 voiceover.txt 又被改词/插句/删句 → 时长清单/字幕/镜头时长全部过期。

    `validate_timings` 在 n2d-script 阶段2收尾抓这条失配链，但 image/video preflight 此前不复查指纹——
    定稿后裸改台词，下游照常据过期时长出图出视频导致音画错位。这里把同一指纹比对前移到付费阶段闸门。
    原生音画模式镜头时长不依赖配音时长清单，跳过。
    """
    if is_native_av_production(root):
        return
    vo_p = os.path.join(root, "脚本", ep, "voiceover.txt")
    if not os.path.isfile(vo_p):
        return  # 无 voiceover：上游问题，require_progress/其它检查覆盖
    meta_p = voice_meta_path(root, ep)
    if not meta_p:
        # 占位轨/旧产物无指纹 sidecar：仅当配音非占位时温和提示（占位由 check_placeholder_policy 管）
        if voice_is_placeholder(root, ep) is False:
            add(WARN, "配音", vo_p, "无 时长清单.meta.json（旧配音产物）——无法核对配音后 voiceover 是否被改，建议重跑 n2d-voice 生成指纹")
        return
    recorded = (load_json(meta_p) or {}).get("voiceover_fingerprint")
    current = voiceover_fingerprint(vo_p)
    if recorded and current and recorded != current:
        add(
            BLOCK,
            "配音",
            vo_p,
            "voiceover.txt 在配音后被改动（台词指纹失配）→ 时长清单/字幕/镜头时长已过期；重跑 n2d-voice 再回跑 n2d-script 阶段2，过 gate 再出图/出视频",
            return_to_stage="voice",
            rerun_scope="重跑 n2d-voice 生成新时长清单 → 回跑 finalize_storyboard 重定镜头时长/字幕 → 再出图出视频。",
            affected_artifacts=[
                f"合成/{ep}/配音/时长清单.json",
                f"脚本/{ep}/storyboard.json",
                f"脚本/{ep}/字幕中.srt",
            ],
        )


def check_timing_manifest_complete(root: str, ep: str) -> None:
    """时长清单逐句完整性：非占位但残缺也要拦。

    `check_placeholder_policy` 只判「是否占位」、`check_voiceover_fingerprint` 只判「定稿后是否被改」——
    一份非占位但残缺的清单（漏句 / 某句 voice_key 空 / 实测时长<=0）能溜过这两关，下游镜头时长据残缺
    数据切，导致音画错位、塌帧、跨集音色对账缺数据源。这里在付费出图前做逐句对账。
    原生音画模式镜头时长不依赖配音时长清单，跳过。
    """
    if is_native_av_production(root):
        return
    man_p = manifest_path(root, ep)
    rows = load_json(man_p)
    if not isinstance(rows, list) or not rows:
        return  # 缺/空清单由 check_progress_artifact_signoff 覆盖，避免重复上报
    dict_rows = [r for r in rows if isinstance(r, dict)]
    # 行数对账：仅当 voiceover.txt 可解析台词行时（render_voice 逐行正则一行一条，1:1）
    vo_p = os.path.join(root, "脚本", ep, "voiceover.txt")
    vo_lines = 0
    if os.path.isfile(vo_p):
        with open(vo_p, encoding="utf-8") as fh:
            for ln in fh:
                if re.match(r"\[(镜头[^·]*)·([^·]+)·([^\]]*)\]\s*(.+)", ln.strip()):
                    vo_lines += 1
    if vo_lines and len(rows) != vo_lines:
        add(BLOCK, "配音", man_p,
            f"时长清单句数({len(rows)})与 voiceover.txt 台词行数({vo_lines})不符——漏句/多句会让镜头时长整体错位；"
            "重跑 n2d-voice 对齐后再出图。",
            return_to_stage="voice")
        return

    def _dur(r: dict) -> float:
        try:
            return float(r.get("时长") or 0)
        except (TypeError, ValueError):
            return 0.0

    bad_key = [i for i, r in enumerate(dict_rows)
               if not str(r.get(VOICE_KEY_FIELD) or r.get(VOICE_KEY_LEGACY_FIELD) or "").strip()]
    bad_dur = [i for i, r in enumerate(dict_rows) if _dur(r) <= 0]
    if bad_key:
        add(BLOCK, "配音", man_p,
            f"{len(bad_key)} 句缺 voice_key（音色键）——一角一色跨集对账缺数据源，下游 n2d-identity 无法对账；"
            f"重跑 n2d-voice 补齐。受影响句序 {bad_key[:8]}",
            return_to_stage="voice")
    if bad_dur:
        add(BLOCK, "配音", man_p,
            f"{len(bad_dur)} 句实测时长<=0——镜头时长据此为 0 会塌帧/音画错位；重跑 n2d-voice 重测时长。"
            f"受影响句序 {bad_dur[:8]}",
            return_to_stage="voice")


def check_voice_cross_episode(root: str, ep: str) -> None:
    """声纹/音色键跨集一致性，在 image gate 渲染前自动落地（此前只在手动 identity.py --write 时打印、不拦）。

    三层信号，按确定性分级：
    - **voicemap 对账失配 → BLOCK**：本集某角色实际用的音色键 ≠ 设定库/voicemap.json 注册键＝确定性配置
      矛盾（你登记 A 却用了 B），出图/出视频前必须修，否则跨集换脸又换声。占位/应急轨与未登记角色已被
      voice_consistency 排除，不会误判。
    - **音色键跨集漂移 → WARN**：同角色相邻集音色键变了（可能是有意——附身/苍老/闪回换嗓，故只告警交人确认；
      若真是错且 voicemap 在册，上面的 BLOCK 已强制修）。
    - **声纹 embedding 跨集漂移 → WARN**：resemblyzer/speechbrain 量同角色逐句余弦相似度跌破校准 floor。
      纯启发式 + 后端可缺（未装则 available=false，静默跳过、交人判，绝不报假漂移）——不当硬闸，只 WARN。

    全部 try/except 包住：声纹/对账是 advisory 增强，任何数据/后端异常都不该让 gate 崩或误拦正片。
    """
    # ① + ② 音色键 / voicemap（确定性，纯 stdlib，几乎不会异常）
    try:
        report = vcons.build_report(root)
    except Exception:
        report = None
    if isinstance(report, dict):
        man_rel = f"合成/{ep}/配音/时长清单.json"
        for m in report.get("voicemap_mismatches", []):
            if str(m.get("episode")) != ep:
                continue
            add(BLOCK, "跨集音色", f"voicemap:{m.get('character')}",
                f"角色「{m.get('character')}」实际音色键 {m.get('voice_key_used')} ≠ voicemap 注册键 "
                f"{m.get('voice_key_registered')}：跨集会换声穿帮，按注册音色重配（n2d-voice）后再出图。",
                return_to_stage="voice", rerun_scope=m.get("scope", ""),
                affected_shots=m.get("affected_shots", []),
                affected_artifacts=[man_rel, "设定库/voicemap.json"])
        for d in report.get("drifts", []):
            if str(d.get("episode_to")) != ep or d.get("episode_from") == d.get("episode_to"):
                continue  # 只看真·跨集漂移；同集内换键由其它链覆盖
            add(WARN, "跨集音色", f"voice_key:{d.get('character')}",
                f"角色「{d.get('character')}」音色键自 {d.get('episode_from')} 的 {d.get('voice_from')} 漂为 "
                f"{d.get('voice_to')}：确认是否有意（附身/苍老/闪回换嗓），否则回 n2d-voice 对齐前集音色。",
                return_to_stage="voice", rerun_scope=d.get("scope", ""),
                affected_shots=d.get("affected_shots", []),
                affected_artifacts=[man_rel, "设定库/voicemap.json"])
    # ③ 声纹 embedding（启发式·后端可缺）
    try:
        vp = vprint.analyze(root, ep)
    except Exception:
        vp = None
    if isinstance(vp, dict) and vp.get("available"):
        man = str(vp.get("manifest") or "")
        for label, group in sorted((vp.get("groups") or {}).items()):
            if not isinstance(group, dict):
                continue
            sev = vprint._severity_for_group(group)
            if sev not in {"block", "warn"}:
                continue
            lines = group.get("lines") if isinstance(group.get("lines"), list) else []
            bad = sum(1 for ln in lines if isinstance(ln, dict) and ln.get("band") == "bad")
            warn = sum(1 for ln in lines if isinstance(ln, dict) and ln.get("band") == "warn")
            # 声纹是启发式，gate 内统一降为 WARN（不当硬闸）——确定性拦截交给上面的 voicemap BLOCK。
            add(WARN, "跨集声纹", f"voice_print:{label}",
                f"声纹机检「{label}」音色漂移：bad={bad} warn={warn}（floor={group.get('floor')} "
                f"mode={vp.get('mode')}）：核对是否同一音色，必要时回 n2d-voice 重配。",
                return_to_stage="voice",
                rerun_scope="声纹余弦跌破校准 floor；回 n2d-voice 重配受影响角色台词后重测。",
                affected_artifacts=[man] if man else [])


def check_backend_reachable(root: str, ep: str) -> None:
    """付费出图前确认所选生图后端「能落 PNG」。

    SKILL.md 写了「确认能落 PNG 再开工」，但此前无确定性闸门兜底——后端不通（内网 502 /
    CLI 未登录 / 缺 API key）时照样进付费工位，要么白花钱碰壁，要么静默兜底换后端致漂移。
    探针口径走 adapter（image_backends），gate 不 hardcode 任何内网地址/CLI 细节：
      · down（探针确证不可达）→ BLOCK，且明确禁止静默兜底换后端；
      · unknown（无自动探针 / CLI 缺 / 已设 N2D_SKIP_BACKEND_PROBE）→ WARN，提示人工确认；
      · ok → 放行。
    """
    settings_loc = os.path.join(root, "_设置.md")
    setting = get_setting(root, "生图AI", "Codex").strip()
    status, detail = image_backends.probe_backend(setting)
    if status == "down":
        add(BLOCK, "生图后端连通性", settings_loc,
            f"生图后端「{setting}」探活不通：{detail}。出图是付费工位，不通就停——"
            "先修后端（验内网/重登 CLI/补 API key）再出图；禁止静默兜底换别的后端（会引入跨镜后端混用漂移）。",
            return_to_stage="image")
    elif status == "unknown":
        bypass = "（注意：N2D_SKIP_BACKEND_PROBE 已设置，探活被显式跳过）" \
            if os.environ.get("N2D_SKIP_BACKEND_PROBE") else ""
        add(WARN, "生图后端连通性", settings_loc,
            f"生图后端「{setting}」无法自动探活：{detail}{bypass}。出图前请人工确认它能落 PNG"
            "（如 curl 内网健康端点 / 确认即梦官方 CLI 已登录·会员有效 / 确认 API 额度），不通即停，勿静默兜底换后端。")


def _image_backend_gate_workload(root: str, ep: str) -> Dict[str, Any]:
    """把当前集粗略归一成适配层 workload，用于后端升档建议。"""
    try:
        cur = _ce_episode_number(ep) or 0
    except Exception:
        cur = 0
    ep_count = len({os.path.basename(os.path.dirname(p))
                    for p in glob.glob(os.path.join(root, "脚本", "*", "storyboard.json"))})
    long_running = max(int(cur or 0), int(ep_count or 0)) >= LONG_RUNNING_EP_THRESHOLD
    return {
        "has_characters": True,
        "core_character": long_running,
        "needs_persistent_subject": long_running,
        "reference_images": 6 if long_running else 4,
        "official_only": True,
    }


def check_image_backend_api_refresh(root: str, ep: str) -> None:
    """正式付费出图前要求本次后端 API/CLI 能力刷新证据。

    后端能力和 API 名称变化快，不能把旧模型矩阵或菜单文案当事实。这里不在 gate 里联网，
    而是要求操作者/agent 当次查官方文档或 CLI/API help 后，把来源和能力结论写入
    `生产数据/image_backend_capabilities/<backend>.json`；gate 只检查这份证据是否是今天的。
    """
    settings_loc = os.path.join(root, "_设置.md")
    setting = get_setting(root, "生图AI", "Codex").strip()
    status = image_backend_adapter.refresh_evidence_status(root, setting)
    if status.get("status") != "fresh":
        add(
            BLOCK,
            "生图后端适配",
            settings_loc,
            f"生图后端「{setting}」缺少本次官方 API/CLI 刷新证据：{status.get('message')}。"
            "正式付费出图前必须实时查官方文档/本机 CLI 或 API help，确认生成、编辑、多参考、主体库、掩码、输出 schema、价格/额度等当前能力，"
            "再记录刷新证据：`python3 skills/n2d/_lib/image_backend_adapter.py record-refresh <作品根> --backend "
            f"\"{setting}\" --source \"<官方文档或CLI/API证据>\" --note \"<本次能力结论>\"`。"
            f"证据文件：{status.get('path')}。未刷新不得开跑，避免旧 API 或能力误判造成整集返工。",
            return_to_stage="image",
            affected_artifacts=[str(status.get("path") or "")],
        )

    rec = image_backend_adapter.recommend_backend(setting, _image_backend_gate_workload(root, ep))
    standard_plan = image_backend_adapter.standard_plan(setting, _image_backend_gate_workload(root, ep))
    if standard_plan.get("status") == "blocked":
        add(
            BLOCK,
            "生图后端适配",
            settings_loc,
            f"所选生图后端「{setting}」无法满足统一出图能力标准："
            f"{', '.join(standard_plan.get('blocked_standards') or [])}。"
            "标准层不随后端降级；请换官方可审计后端，或先补适配层能力与弥补措施。",
            return_to_stage="image",
        )
    elif standard_plan.get("status") == "mitigations_required":
        items = [str(x) for x in (standard_plan.get("required_mitigations") or [])[:4]]
        add(
            WARN,
            "生图后端适配",
            settings_loc,
            f"统一标准已按「{setting}」自动加载弥补措施：{'；'.join(items)}"
            + ("；..." if len(standard_plan.get("required_mitigations") or []) > 4 else "")
            + "。这些是后端差异的执行补偿，不降低 n2d 的出图标准。",
            return_to_stage="image",
        )
    if rec.get("upgrade_recommended"):
        cur = rec.get("current") or {}
        best = rec.get("recommended") or {}
        adapter = rec.get("adapter") or {}
        add(
            WARN,
            "生图后端适配",
            settings_loc,
            f"适配层评分建议升档：当前「{setting}」score={cur.get('score')}，"
            f"推荐「{best.get('label') or best.get('backend')}」score={best.get('score')}。"
            f"理由：推荐后端能力={','.join(best.get('strengths') or []) or adapter.get('adapter_kind')}；"
            "若确认切换，先统一 `_设置.md` 与全部 prompt 的生图后端，并按新后端重做/刷新本集定妆、参考包和身份注册，禁止半集混用。",
            return_to_stage="image",
        )


def _route_video_backends(routes: Sequence[Dict[str, Any]], allow_empty_fallback: bool) -> List[str]:
    selected: List[str] = []
    for route in routes:
        primary = str(route.get("primary_backend") or "").strip()
        if primary:
            selected.append(primary)
        fallbacks = route.get("fallback_backends")
        if isinstance(fallbacks, list):
            selected.extend(str(item or "").strip() for item in fallbacks)
        elif fallbacks and not allow_empty_fallback:
            selected.append(str(fallbacks).strip())
    out: List[str] = []
    seen: set[str] = set()
    for backend in selected:
        if not backend or not video_backend_adapter.requires_refresh(backend):
            continue
        canonical = str(video_backend_adapter.backend_adapter(backend).get("canonical") or backend)
        if canonical in seen:
            continue
        seen.add(canonical)
        out.append(backend)
    return out


def _video_route_backend_roles(route: Mapping[str, Any], allow_empty_fallback: bool) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    primary = str(route.get("primary_backend") or "").strip()
    if primary:
        out.append(("primary", primary))
    fallbacks = route.get("fallback_backends")
    if isinstance(fallbacks, list):
        out.extend(("fallback", str(item or "").strip()) for item in fallbacks if str(item or "").strip())
    elif fallbacks and not allow_empty_fallback:
        out.append(("fallback", str(fallbacks).strip()))
    return out


def _cap_bool(assertions: Mapping[str, Any], key: str) -> bool:
    value = _cap_value(assertions, key)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "是", "支持"}


def _cap_number(assertions: Mapping[str, Any], key: str, default: float = 0) -> float:
    try:
        return float(_cap_value(assertions, key))
    except Exception:
        return default


def _cap_value(assertions: Mapping[str, Any], key: str) -> Any:
    value = assertions.get(key)
    if isinstance(value, Mapping) and "value" in value:
        return value.get("value")
    return value


def _route_capability_assertion_gaps(route: Mapping[str, Any], assertions: Mapping[str, Any], role: str) -> List[str]:
    gaps: List[str] = []
    clip_id = str(route.get("clip_id") or "?")
    duration = float(route.get("clip_seconds") or 0)
    if duration > 0 and _cap_number(assertions, "max_clip_seconds") and _cap_number(assertions, "max_clip_seconds") < duration:
        gaps.append(f"{clip_id} {role} max_clip_seconds<{duration:g}s")
    mode = str(route.get("mode") or "").lower()
    if mode not in {"text2video", "t2v"} and not _cap_bool(assertions, "supports_first_frame"):
        gaps.append(f"{clip_id} {role} 未确认 supports_first_frame")
    anchor = route.get("anchor_consumption") if isinstance(route.get("anchor_consumption"), Mapping) else {}
    need_end = bool(anchor.get("need_end")) or bool(anchor.get("consumes_endframe"))
    if need_end and not _cap_bool(assertions, "supports_last_frame"):
        gaps.append(f"{clip_id} {role} 未确认 supports_last_frame/尾帧控制")
    anchor_count = int(anchor.get("anchor_count") or 0)
    consumption_mode = str(anchor.get("consumption_mode") or "")
    if anchor_count and consumption_mode == "native_multiframe" and not _cap_bool(assertions, "supports_native_mid_anchors"):
        gaps.append(f"{clip_id} {role} 原生多关键帧未确认 supports_native_mid_anchors")
    if anchor_count and consumption_mode == "native_multiframe" and _cap_number(assertions, "max_timeline_frames", 1) < (1 + anchor_count + (1 if need_end else 0)):
        gaps.append(f"{clip_id} {role} max_timeline_frames 不足以消费首/中/尾")
    native_audio = str(route.get("native_audio_policy") or "").lower()
    if native_audio == "native_speech" and not _cap_bool(assertions, "native_av"):
        gaps.append(f"{clip_id} {role} native_speech 但未确认 native_av")
    if native_audio == "lipsync_condition_only" and not _cap_bool(assertions, "lipsync_audio_ref"):
        gaps.append(f"{clip_id} {role} 口型音频参考但未确认 lipsync_audio_ref")
    identity = str(route.get("identity_requirement") or "").strip().lower()
    if identity not in {"", "none", "not_needed"} and not str(_cap_value(assertions, "identity_mechanism") or "").strip():
        gaps.append(f"{clip_id} {role} 含角色身份要求但未确认 identity_mechanism")
    motion = route.get("motion_control") if isinstance(route.get("motion_control"), Mapping) else {}
    if motion.get("required") is True and not str(_cap_value(assertions, "motion_control_level") or "").strip():
        gaps.append(f"{clip_id} {role} Motion Control required 但未确认 motion_control_level")
    return gaps


def check_video_backend_api_refresh(
    root: str,
    ep: str,
    routes: Sequence[Dict[str, Any]],
    video_channel: str,
    route_path: str,
    allow_empty_fallback: bool = False,
) -> None:
    """正式付费出视频前要求本次视频后端 API/CLI 能力刷新证据。"""
    for backend in _route_video_backends(routes, allow_empty_fallback):
        status = video_backend_adapter.refresh_evidence_status(root, backend, video_channel)
        if status.get("status") == "fresh":
            continue
        adapter = video_backend_adapter.backend_adapter(backend, video_channel)
        channel_note = f"（渠道 {video_channel}，执行后端 {adapter.get('execution_backend')}）" if video_channel else ""
        add(
            BLOCK,
            "生视频后端适配",
            route_path,
            f"生视频后端「{backend}」{channel_note}缺少本次官方 API/CLI 刷新证据：{status.get('message')}。"
            "正式付费出视频前必须实时查官方文档/本机 CLI 或 API help，确认单 Clip 上限、首尾/多帧能力、"
            "原生音画/口型、身份绑定、分辨率/价格/额度和输出 schema，再记录刷新证据："
            "`python3 skills/n2d/_lib/video_backend_adapter.py record-refresh <作品根> --backend "
            f"\"{backend}\" --channel \"{video_channel}\" --source \"<官方文档或CLI/API证据>\" "
            "--note \"<本次能力结论>\"`。"
            f"证据文件：{status.get('path')}。未刷新不得开跑，避免旧 API 或能力误判造成整集返工。",
            return_to_stage="video",
            affected_artifacts=[str(status.get("path") or "")],
        )
    capability_gap_records: List[str] = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        for role, backend in _video_route_backend_roles(route, allow_empty_fallback):
            if not backend or not video_backend_adapter.requires_refresh(backend):
                continue
            status = video_backend_adapter.refresh_evidence_status(root, backend, video_channel)
            if status.get("status") != "fresh":
                continue
            assertions = status.get("capability_assertions") if isinstance(status.get("capability_assertions"), dict) else {}
            capability_gap_records.extend(_route_capability_assertion_gaps(route, assertions, role))
    if capability_gap_records:
        add(
            BLOCK,
            "生视频后端适配",
            route_path,
            "本次视频后端刷新证据缺少或不满足 route 需要的结构化能力断言："
            + "；".join(capability_gap_records[:8])
            + ("；..." if len(capability_gap_records) > 8 else "")
            + "。请重跑 record-refresh 并补 `--capability key=value`，确认首/尾/多帧、native_av、口型音频参考、身份机制和 Motion Control 后再付费出视频。",
            return_to_stage="video",
        )


def drift_advisory_findings(report: Dict[str, Any]) -> List[Tuple[str, str, str, str]]:
    """drift-risk report → [(sev, dim, loc, msg)]。

    两类档分开处理：
      - **预测档** high→WARN·medium→INFO；预测 block 仍是 preflight BLOCK，但维度必须叫“预案”，
        不能伪装成已实测漂移；
      - **实测档** `measured_drift` 存在（face_drift_risk ② 回灌 identity_drift_report 的**已实测**
        跨集漂移，既成事实非预测）→ **BLOCK**：上一集已漂的角色，本集出图前 preflight 硬拦，
        闭合"测了就拦"的环。
    纯函数·可测：不读盘、不 add()。face/asset 两种 report 同形。"""
    items = report.get("characters") or report.get("assets") or []
    is_face = report.get("kind") == "n2d_face_drift_risk"
    dim = "脸漂预案" if is_face else "物料漂移预案"
    label = "脸漂" if is_face else "物料漂移"
    out: List[Tuple[str, str, str, str]] = []
    for r in items:
        band = r.get("band")
        rid = r.get("character_id") or r.get("id") or ""
        name = r.get("name") or rid
        tip = (r.get("suggestions") or [""])[0]
        if band == "block" and r.get("measured_drift"):
            # 实测跨集漂移（measured_drift 已坐实）→ 真 BLOCK，不再当 advisory 滤掉（曾被漏报）
            out.append((BLOCK, "脸漂实测" if is_face else "物料漂移实测", f"{name}（{rid}）",
                        f"上一集已实测{label}漂移（既成事实非预测）：{tip}"))
            continue
        if band not in ("block", "high", "medium"):
            continue
        sev = BLOCK if band == "block" else (WARN if band == "high" else INFO)
        tier = r.get("tier") or r.get("scope") or ""
        out.append((sev, dim, f"{name}（{rid}）",
                    f"本集{label}风险 {band}（分{r.get('score')}{'·'+str(tier) if tier else ''}）：{tip}"))
    return out


def _run_drift_risk_script(script_name: str, root: str, ep: str) -> Optional[Dict[str, Any]]:
    """跑 n2d-image 的 face/asset_drift_risk.py（--json），拿机器报告。跑不起来→None（交由调用方降级 INFO）。"""
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          "n2d-image", "scripts", script_name)
    if not os.path.exists(script):
        return None
    try:
        out = subprocess.check_output([sys.executable, script, root, ep, "--json"],
                                      text=True, stderr=subprocess.DEVNULL, timeout=90)
        return json.loads(out)
    except Exception:
        return None


def check_drift_risk_advisories(root: str, ep: str) -> None:
    """image_preflight 专属：自动跑 face/asset drift_risk 预案，把 high/medium 内联进同一份预检报告。

    动机（E1·让 agent 跑得更顺）：脸漂/物料漂移预案此前是两个独立、要 agent **记得手动跑**的脚本，
    输出又各自落单独 JSON——agent 跑一次 gate 拿 block、还得另记两条 advisory。这里把它们折进
    image_preflight：一个入口 = 阻断 + 预案一次拿齐。advisory only（WARN/INFO），绝不阻断出图。"""
    for script_name, human in (("face_drift_risk.py", "脸漂"), ("asset_drift_risk.py", "物料漂移")):
        report = _run_drift_risk_script(script_name, root, ep)
        if report is None:
            add(INFO, "漂移预案", ep,
                f"{human}风险预案未能自动生成（缺 storyboard/registry 或脚本不可用）——"
                f"出图前可手动跑 skills/n2d-image/scripts/{script_name} 看预案。")
            continue
        rows = drift_advisory_findings(report)
        if not rows:
            add(INFO, "漂移预案", ep, f"{human}风险预案：本集无 high/医 medium 角色/物料（🟢 全低危）。")
            continue
        for sev, dim, loc, msg in rows:
            # 实测漂移=真 BLOCK（return_to_stage=image，须先处置再出图）；预测档仍 advisory
            if sev == BLOCK:
                add(sev, dim, loc, msg, return_to_stage="image")
            else:
                add(sev, dim, loc, msg, advisory=True)


def imaged_episodes(root: str) -> List[str]:
    """已落 PNG 的出图集（出图/<集>/图片/*.png 存在）——measured-drift BLOCK 环应覆盖的历史集。"""
    eps: set = set()
    for p in glob.glob(os.path.join(root, "出图", "*", "图片", "*.png")):
        eps.add(os.path.basename(os.path.dirname(os.path.dirname(p))))
    return sorted(eps)


def drift_report_freshness(prior_imaged_eps: Sequence[str],
                           report: Mapping[str, Any]) -> List[Tuple[str, str]]:
    """历史已出图集 vs identity_drift_report 覆盖集 → freshness findings（纯函数·可测）。

    prior_imaged_eps：本集之前、已落 PNG 的集（measured-drift BLOCK 环理应覆盖的历史集）。
    report：解析后的 identity_drift_report.json（{} = 缺失）。返回 [(severity, msg)]：
      - 报告缺失/未实测(available≠True) 但已有历史出图集 → WARN（环此刻无数据，给重跑命令；
        不硬拦无 insightface 的默认无依赖产线）；
      - 报告在、已实测，却漏覆盖部分历史出图集 → BLOCK（present-but-stale：环会读它并据旧数据
        误判『全绿』放行，比缺报告更危险）。
    无历史出图集（首集）→ []。纯函数·可测。"""
    prior = sorted({str(e).strip() for e in (prior_imaged_eps or []) if str(e).strip()})
    if not prior:
        return []
    measured = isinstance(report, Mapping) and report.get("available") is True
    if not measured:
        return [(WARN,
                 f"脸漂实测报告缺失/未实测（identity_drift_report.json 不存在或 available≠true），但历史集已出图 {prior}："
                 "跨集脸漂「测了就拦」的 BLOCK 环此刻无数据兜底，上一集已漂的脸可能蒙混过本集。装 insightface 后跑 "
                 "`python3 skills/n2d-identity/scripts/identity.py <作品根> --write` 生成实测报告再出图。")]
    covered = {str(e).strip() for e in (report.get("episodes") or [])}
    stale = [e for e in prior if e not in covered]
    if stale:
        return [(BLOCK,
                 f"脸漂实测报告陈旧：已出图历史集 {prior} 中 {stale} 未进 identity_drift_report 覆盖集 {sorted(covered)}——"
                 "报告在、measured-drift 环会读它并据旧数据误判『全绿』放行，比缺报告更危险。重跑 "
                 "`python3 skills/n2d-identity/scripts/identity.py <作品根> --write` 覆盖全部历史出图集后再出图。")]
    return []


def check_drift_report_freshness(root: str, ep: str) -> None:
    """measured-drift BLOCK 环的新鲜度闸：报告缺/陈旧时不让其静默退化成 advisory。

    动机（堵静默退化洞）：跨集脸漂的实测 BLOCK 依赖 生产数据/identity_drift_report.json，而该报告只由
    `identity.py --write` 手动生成、gate 只读不刷（drift_advisory_findings / measured_drift_block）。漏跑/陈旧 →
    上一集已漂的脸蒙混过本集。这里把『历史已出图集是否都被报告覆盖』钉成闸：present-but-stale=BLOCK
    （最危险，留 N2D_ALLOW_DEGRADED_QC=1 逃生口·留痕自负），缺失/未实测=WARN（不硬拦无 insightface 的默认产线）。"""
    cur = _ce_episode_number(ep) or 0
    prior_imaged = [e for e in imaged_episodes(root)
                    if 0 < (_ce_episode_number(e) or 0) < cur] if cur else []
    report = load_json(os.path.join(root, "生产数据", "identity_drift_report.json"))
    if not isinstance(report, dict):
        report = {}
    for sev, msg in drift_report_freshness(prior_imaged, report):
        if sev == BLOCK:
            if os.environ.get("N2D_ALLOW_DEGRADED_QC") == "1":
                add(WARN, "脸漂报告新鲜度", ep, msg + "（已显式 N2D_ALLOW_DEGRADED_QC 放行·自负其责）")
            else:
                add(BLOCK, "脸漂报告新鲜度", ep, msg, return_to_stage="image")
        else:
            add(sev, "脸漂报告新鲜度", ep, msg, advisory=True)


def check_contract_inheritance(root: str, ep: str) -> None:
    """像素层视觉契约 出图→出视频 继承 Diff，逐字段机检（光位锚/轴线视线漂移=BLOCK）。

    这是唯一能抓「人工誊抄改写轴线/光位」的机检；此前只存在于 inherit_contract.py 的裸命令、
    游离在 gate 退出码之外，导致 `dashboard.py gate --stage video` 通过 ≠ 契约继承成立。
    接进 video_preflight/video gate 后，视频侧改写/丢失像素层五字段会被硬拦，并消费 contract_inheritance 维度的回退坐标。
    """
    img_p = os.path.join(root, "出图", ep, "prompt", "00_总览.md")
    vid_p = os.path.join(root, "出视频", ep, "prompt", "00_总览.md")
    if not os.path.isfile(img_p):
        return  # 出图总览缺：上游问题，image_preflight/image gate 负责，不在此重复 BLOCK
    if not os.path.isfile(vid_p):
        return  # 视频总览缺：check_video_prompt_overview 已 BLOCK，避免重复报
    dim = CONSISTENCY_DIMENSIONS["contract_inheritance"]
    for r in diff_contracts(open(img_p, encoding="utf-8").read(), open(vid_p, encoding="utf-8").read()):
        if r["severity"] == "block":
            add(
                BLOCK,
                "契约继承",
                vid_p,
                f"视觉契约继承漂移[{r['field']}]：{r['note']}（出图侧原文：{r['image_text'] or '缺'}）",
                return_to_stage=dim["return_to_stage"],
                rerun_scope=dim["scope"],
                affected_artifacts=[f"出视频/{ep}/prompt/00_总览.md"],
            )
        elif r["status"] == "warn_drift":
            add(WARN, "契约继承", vid_p, f"视觉契约继承提示[{r['field']}]：{r['note']}（出图侧：{r['image_text'] or '缺'}）")


def check_asset_handoff_inheritance(root: str, ep: str) -> None:
    """逐镜物料约束 出图→出视频 继承（LOC/PROP/WEAPON/OUTFIT/VFX）：出图绑定的资产在出视频对应镜
    丢失=block/warn。视觉契约五字段管 episode 级光位/轴线，本检查补**逐镜**资产锚。

    此前只在 inherit_contract.py 裸命令里跑，游离在 gate 退出码之外——`dashboard.py gate --stage video`
    通过 ≠ 资产逐镜交接成立。接进 video gate 后，出图逐镜 prompt 绑的道具/特效在视频侧被丢会被收口。
    （身份交接逐镜锁则由 check_route_identity_readiness / 近景身份锁负责，不在此重复报。）
    """
    res = check_asset_handoff(root, ep)
    if not res.get("available"):
        return  # 上游逐镜 prompt 未到位：image/video 各自 stage gate 负责，不在此重复 BLOCK
    dim = CONSISTENCY_DIMENSIONS["contract_inheritance"]
    vid_rel = res.get("video_clips_file", os.path.join("出视频", ep, "prompt", "01_clips.md"))
    vid_p = os.path.join(root, vid_rel)
    for f in res.get("findings", []):
        if f.get("severity") == "block":
            add(
                BLOCK,
                "契约继承",
                vid_p,
                f"资产逐镜交接[{f.get('code')}]：{f.get('note')}",
                return_to_stage=dim["return_to_stage"],
                rerun_scope=dim["scope"],
                affected_artifacts=[vid_rel],
            )
        else:
            add(WARN, "契约继承", vid_p, f"资产逐镜交接[{f.get('code')}]：{f.get('note')}")


def check_identity_handoff_inheritance(root: str, ep: str) -> None:
    """逐镜身份 出图→出视频 继承：命名角色镜必须锁身份；多锚帧角色 Clip 必须同源
    reference_group / expressions；大表情近景必须锁脸不锁情。

    之前 gate 只通过 video prompt 字段做散点检查，完整身份交接检查只在 inherit_contract.py 裸命令中
    出现。接进 video gate 后，真正提交生视频前会统一阻断“首/中/尾锚图不是同一张脸”的流程漏洞。
    """
    res = check_identity_handoff(root, ep)
    if not res.get("available"):
        return
    dim = CONSISTENCY_DIMENSIONS["contract_inheritance"]
    vid_rel = res.get("clips_file", os.path.join("出视频", ep, "prompt", "01_clips.md"))
    vid_p = os.path.join(root, vid_rel)
    for f in res.get("findings", []):
        if f.get("severity") == "block":
            add(
                BLOCK,
                "契约继承",
                vid_p,
                f"身份逐镜交接[{f.get('code')}]：{f.get('note')}",
                return_to_stage=dim["return_to_stage"],
                rerun_scope=dim["scope"],
                affected_artifacts=[vid_rel],
            )
        else:
            add(WARN, "契约继承", vid_p, f"身份逐镜交接[{f.get('code')}]：{f.get('note')}")


# 核心长线角色判定：scope 自由文本里的"贯穿全篇/长线/主角/主反派"标记。短线配角/单元妖不命中，
# 避免对前几集退场的角色前置高档（对齐 n2d-image「ROI 驱动、默认最小化」）。
_CORE_SCOPE_RE = re.compile(r"全篇|全程|长线|核心|主角|女主|男主|主反派")


def _image_backend_supports_native_subject(canon: str) -> bool:
    """该图后端是否支持注册原生角色主体/Character ID（梯子第②档）。

    真值取 IMAGE_IDENTITY_PROFILES：Dreamina/Nano 属于多参考但无持久主体；
    seedream/kling/sora 才触发注册主体提示。
    """
    return image_backend_supports_persistent_subject(canon or "")


def _image_event_provider(event: Dict[str, Any]) -> str:
    generation = _event_generation(event)
    cost = _event_cost(event)
    meta = _event_meta(event)
    for source in (generation, cost, event, meta):
        if not isinstance(source, dict):
            continue
        value = str(source.get("provider") or "").strip()
        if value and value.lower() not in {"unknown", "manual", "none", "null"}:
            return value
    return ""


def check_image_ai_policy(root: str, ep: str) -> None:
    """阶段2：`生图AI` 是选择点（默认 Codex），放行官方/已登录多参考后端，只拦混用 + 未授权出图。

    跨镜一致性真正的杀手是【同项目混用多个生图后端】，不是"用了非 Codex"。本检查：
      - 官方白名单后端（Codex/OpenAI/Dreamina/即梦官方 CLI/Seedream/可灵主体库/Nano Banana/Sora Cameo）：放行；
      - 未授权出图路径（同视频AI 含糊口径、第三方逆向 CLI/web 自动化）：BLOCK（安全 invariant）；
      - 未知后端：WARN（提示先确认是官方 API）；
      - 同项目/同集出现 ≥2 个不同官方后端：BLOCK（混用）。
    合规闸门（角色/声音克隆授权）由 check_compliance_manifest 负责，与本检查无关。
    """
    settings_loc = os.path.join(root, "_设置.md")
    used: set = set()  # 在用的官方后端 canonical 集合，用于混用检测

    setting = get_setting(root, "生图AI", "Codex").strip()
    canon, kind = classify_image_backend(setting)
    if kind == "forbidden":
        add(
            BLOCK,
            "生图AI一致性",
            settings_loc,
            f"生图AI「{setting}」是未授权/含糊出图路径（同视频AI、第三方逆向 CLI 或 web 自动化），违反安全闸门，永不放行。"
            "请显式改用官方后端：Codex/OpenAI、Dreamina/即梦官方 CLI、Seedream（官方 API）、可灵主体库、Nano Banana、Sora Cameo。",
        )
    elif kind == "unknown":
        add(
            WARN,
            "生图AI一致性",
            settings_loc,
            f"生图AI「{setting}」不在已知官方后端清单内。请先确认它是【官方 API】再用；"
            "已知官方后端：" + "、".join(cfg["label"] for cfg in APPROVED_IMAGE_BACKENDS.values()) + "。",
        )
    else:
        used.add(canon)

    prompt_paths = [
        os.path.join(root, "出图", ep, "prompt", "00_总览.md"),
        os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md"),
        shared_asset_path(root, "prompt", "角色定妆.md"),
        shared_asset_path(root, "prompt", "场景定妆.md"),
        shared_asset_path(root, "prompt", "道具定妆.md"),
        shared_asset_path(root, "prompt", "法宝定妆.md"),
        shared_asset_path(root, "prompt", "特效定妆.md"),
    ]
    backend_decl_re = re.compile(
        r"(?:生图AI|图像后端|图片后端|image backend|image model)\s*[:：]\s*([^\n\r`|]+)",
        re.I,
    )
    forbidden_call_re = re.compile(r"(同视频AI|非官方|第三方|逆向|web\s*自动化).{0,24}(?:生图|出图|image generation|text2image|image2image)", re.I)
    for path in prompt_paths:
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        if forbidden_call_re.search(text):
            add(
                BLOCK,
                "生图AI一致性",
                path,
                "prompt 出现同视频AI/非官方/第三方逆向/web 自动化出图口径；属未授权或含糊出图路径，必须移除。官方 Dreamina CLI 请显式写 “Dreamina/即梦”。",
            )
        for m in backend_decl_re.finditer(text):
            pc, pk = classify_image_backend(m.group(1))
            if pk == "forbidden":
                add(
                    BLOCK,
                    "生图AI一致性",
                    path,
                    f"prompt 标注未授权/含糊出图后端「{m.group(1).strip()}」；请改用官方后端（Codex/OpenAI/Dreamina/Seedream/可灵/Nano Banana/Sora）。",
                )
            elif pk == "approved":
                used.add(pc)

    missing_event_providers: List[str] = []
    event_path = _production_events_path(root)
    latest_success_events: Dict[str, Tuple[int, Dict[str, Any]]] = {}
    unkeyed_success_events: List[Tuple[int, Dict[str, Any], str]] = []
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        generation = _event_generation(event)
        status = str(generation.get("status") or event.get("status") or "").strip().lower()
        if status == "fail":
            continue
        asset = _event_asset_rel(root, event) or str(generation.get("asset") or "")
        if asset:
            latest_success_events[asset] = (idx, event)
        else:
            unkeyed_success_events.append((idx, event, asset))

    # 只以同一 asset 的最新成功落档事件判定后端混用。旧的 pass 会被后续 redraw/generation
    # 覆盖，否则一次全量迁移后端会被历史账本误判成“跨镜混用”。
    event_checks = sorted(
        [(idx, event, asset) for asset, (idx, event) in latest_success_events.items()] + unkeyed_success_events,
        key=lambda item: item[0],
    )
    for idx, event, asset in event_checks:
        provider = _image_event_provider(event)
        if not provider:
            missing_event_providers.append(f"line {idx}: {asset or '(no asset)'}")
            continue
        pc, pk = classify_image_backend(provider)
        if pk == "forbidden":
            add(
                BLOCK,
                "生图AI一致性",
                event_path,
                f"production_events 第{idx}行记录了未授权/含糊出图 provider「{provider}」；真实落档事件不得使用第三方逆向/web 自动化/同视频AI 口径。",
            )
        elif pk == "unknown":
            add(
                WARN,
                "生图AI一致性",
                event_path,
                f"production_events 第{idx}行 provider「{provider}」不在官方后端清单内；请确认其为官方 API/CLI，并补充后端适配。",
            )
        else:
            used.add(pc)
    if missing_event_providers:
        add(
            BLOCK,
            "生图AI一致性",
            event_path,
            "成功/待验收的 image generation/redraw 事件缺 provider，无法证明本集未混用后端："
            + "；".join(missing_event_providers[:8])
            + ("；..." if len(missing_event_providers) > 8 else "")
            + "。请用 dashboard record --provider 补录或重跑生成 adapter。",
        )

    if len(used) >= 2:
        add(
            BLOCK,
            "生图AI一致性",
            settings_loc,
            f"同项目/同集混用多个生图后端（{'、'.join(sorted(used))}）；混用会让同角色脸型/服装/画风跨镜漂移。"
            "请把 _设置.md 与所有 prompt 统一到同一个生图后端后再出图。",
        )

    # 主体库硬闸（一致性梯子第②档）：所选后端**支持原生角色主体/Character ID**（seedream/可灵/sora 等）
    # 而核心长线角色还停在 unregistered 时，付费出图前 BLOCK。注册一次按 ID 跨镜跨集引用，比每张重喂
    # 参考图更稳更省，是压住跨集脸漂的省钱前置。Codex/OpenAI 等无持久主体的后端不触发
    # （default_status=fallback_reference_group → 自动回退参考图派生，不打扰短线/弱后端路线）。"不靠想起来"：
    # 靠 registry adapter 状态机检，不靠人脑记。
    if kind == "approved" and _image_backend_supports_native_subject(canon):
        reg = load_json(identity_registry_path(root))
        if isinstance(reg, dict):
            label = next(
                (cfg["label"] for cfg in APPROVED_IMAGE_BACKENDS.values() if cfg.get("canonical") == canon),
                canon,
            )
            pending: List[str] = []
            for char in reg.get("characters", []) or []:
                if not isinstance(char, dict):
                    continue
                if not _CORE_SCOPE_RE.search(str(char.get("scope") or "")):
                    continue  # 默认最小化：短线配角/单元妖不前置高档，只 nudge 核心长线角
                for form in char.get("forms", []) or []:
                    if not isinstance(form, dict):
                        continue
                    img = (form.get("identity_adapters") or {}).get("image") or {}
                    entry = img.get(canon)
                    status = entry.get("status") if isinstance(entry, dict) else entry
                    if status not in ("registered", "ready"):
                        pending.append(f"{char.get('id')}/{form.get('form')}")
            if pending:
                shown = "、".join(pending[:8]) + ("…" if len(pending) > 8 else "")
                add(
                    BLOCK,
                    "原生主体注册",
                    settings_loc,
                    f"生图AI「{label}」支持原生角色主体/Character ID（一致性梯子第②档），但核心长线角色尚未注册："
                    f"{shown}。注册一次后按 ID 跨镜跨集引用，比每张重喂参考图更稳更省，能压住跨集脸漂。"
                    f"请在该后端控制台用已过自检的定妆三视图注册主体，把返回的 ID/句柄写进 identity_registry "
                    f"对应 forms[].identity_adapters.image.{canon}（status→registered + id/handle），再跑 "
                    "`python3 skills/n2d-identity/scripts/identity.py <作品根> --write` 刷新 adapter matrix。"
                    "（Codex/OpenAI 等无持久主体的后端不触发本硬闸，自动回退参考图派生；"
                    "核心长线角色若选择支持主体库的后端，则先注册再付费出图）",
                )


def _reference_plan_requirement(root: str, ep: str) -> Tuple[str, str]:
    """Return (severity, reason) for missing per-shot reference plan.

    No storyboard/registry signal means no noise.  Core/long-running characters are a hard
    preflight dependency; ordinary character episodes still warn so short demos are not blocked
    before their registry is complete.
    """
    reg = load_json(identity_registry_path(root))
    core_forms: List[str] = []
    if isinstance(reg, dict):
        for char in reg.get("characters", []) or []:
            if not isinstance(char, dict):
                continue
            if not _CORE_SCOPE_RE.search(str(char.get("scope") or "")):
                continue
            for form in char.get("forms", []) or []:
                if isinstance(form, dict):
                    core_forms.append(f"{char.get('id')}/{form.get('form')}")
    if core_forms:
        shown = "、".join(core_forms[:8]) + ("…" if len(core_forms) > 8 else "")
        return BLOCK, f"identity_registry 含核心长线角色：{shown}"

    sb = load_json(storyboard_path(root, ep))
    if isinstance(sb, dict):
        text = json.dumps(sb, ensure_ascii=False)
        if re.search(r"CHAR_[A-Za-z0-9_]+|角色|人物|主角|女主|男主", text):
            return WARN, "storyboard 含人物/角色镜头"
    return "", ""


def check_reference_plan_applied(root: str, ep: str) -> None:
    """逐镜参考规划（reference_planner.py）→ 落实对账。

    跨集脸漂的处方在 `生产数据/reference_plan_第N集.json`（弱后端按每镜变化量该补哪些参考/控制网/升档）。
    本检查在 image_preflight 把该 plan 的**行动项**surfaced 到付费闸门，提醒人审落进 01_分镜出图.md，
    避免"规划了却忘了补"。核心长线角色缺 plan 直接 BLOCK；普通角色镜缺 plan 只 WARN。
    与 image_qc 的 no_expression_lib_ref 互补：前者 pre-gen 选参考，后者 post-gen 验落档。
    """
    plan_path = os.path.join(root, "生产数据", f"reference_plan_{ep}.json")
    plan = load_json(plan_path)
    if not isinstance(plan, dict) or plan.get("kind") != "n2d_reference_plan":
        sev, reason = _reference_plan_requirement(root, ep)
        if sev:
            add(
                sev,
                "参考规划落实",
                plan_path,
                f"缺逐镜参考规划 reference_plan_{ep}.json（{reason}）。付费出图前先跑 "
                f"`python3 skills/n2d-image/scripts/reference_planner.py <作品根> {ep}`，"
                "把每镜该喂的脸锚/表情/侧背/服装/场景/道具/控制网/升档建议落实到 "
                f"`出图/{ep}/prompt/01_分镜出图.md`；否则很容易只写了规则但实际未传对参考。",
                return_to_stage="image",
            )
        return
    summary = plan.get("summary") or {}
    actions = summary.get("action_required") or []
    if not actions:
        return
    weak = summary.get("weak_backend_large_delta_clips") or 0
    reg = summary.get("chars_need_native_registration") or []
    lora = summary.get("chars_need_lora") or []
    clips = sorted({str(a.get("clip")) for a in actions if a.get("clip")})
    shown = "、".join(clips[:8]) + ("…" if len(clips) > 8 else "")
    tail = ""
    if reg:
        tail += f" 待注册原生主体：{'、'.join(reg)}。"
    if lora:
        tail += f" 建议升 LoRA：{'、'.join(lora)}。"
    sev = BLOCK if (weak or reg or lora) else WARN
    add(
        sev,
        "参考规划落实",
        plan_path,
        f"逐镜参考规划有 {len(actions)} 条行动项未确认落实（弱后端×大变化镜 {weak} 镜）："
        f"镜头 {shown}。请按 reference_plan_{ep}.md 把补拍/多样参考/控制网/升档落进 "
        f"出图/{ep}/prompt/01_分镜出图.md 后再付费出图；不能让参考规划停在侧车文件里。{tail}",
        return_to_stage="image",
    )


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def load_storyboard(root: str, ep: str) -> Optional[dict]:
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "故事板", p, "缺少机器可读 storyboard.json；下游无法确定 continuity/need_endframe")
        return None
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        add(BLOCK, "故事板", p, "storyboard.json 缺 clips[]")
        return None
    return data


def check_storyboard_contract(root: str, ep: str, require_frame_assets: bool = True) -> Optional[dict]:
    data = load_storyboard(root, ep)
    if not data:
        return None
    clips = data["clips"]
    policy = data.get("policy")
    if not isinstance(policy, dict) or policy.get("tailframe_default") is not True:
        add(BLOCK, "故事板", storyboard_path(root, ep), "storyboard.json 缺 policy.tailframe_default=true；首尾双帧接力必须作为默认契约")
    prev_end = None
    routes_file = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    routes_map = {}
    if os.path.exists(routes_file):
        try:
            with open(routes_file, encoding="utf-8") as f:
                r_data = json.load(f)
                if isinstance(r_data.get("routes"), list):
                    routes_map = {item.get("id"): item for item in r_data["routes"]}
        except Exception:
            pass

    for i, clip in enumerate(clips, 1):
        loc = f"{storyboard_path(root, ep)} clip#{i}"
        cid = clip.get("id", f"EP{data.get('episode', '01')}_CLIP{i:02d}")
        route = routes_map.get(cid) or {}
        is_t2v = (route.get("mode") == "text2video")

        first_png = clip.get("firstframe_png")
        if not first_png and not is_t2v:
            add(BLOCK, "首帧", loc, "缺 firstframe_png")
        elif first_png and require_frame_assets:
            first_full = first_png if os.path.isabs(first_png) else os.path.join(root, first_png)
            if not os.path.exists(first_full):
                add(BLOCK, "首帧", first_full, "firstframe_png 不存在")
        cont = clip.get("continuity")
        if not isinstance(cont, dict):
            add(BLOCK, "故事板", loc, "缺 continuity 块")
            continue
        for key in ("start_state", "end_state", "transition", "need_endframe"):
            if key not in cont:
                add(BLOCK, "故事板", loc, f"continuity 缺字段：{key}")
        if prev_end and cont.get("start_state") != prev_end:
            add(BLOCK, "故事板", loc, "start_state 未原样继承上一 Clip 的 end_state")
        prev_end = cont.get("end_state")
        # 近景/特写/反打镜必须声明 expression_span——把「跨情绪近景首尾双帧」闸门从 opt-in 收成强制。
        # 没标 span 的大表情近景正是脸被表情带着重画的头号根因；不能靠作者记得打标签，否则双帧保护
        # 恰好在最该保护的未标镜上静默 no-op。远景/空镜由 _clip_is_closeup 收口、不误伤。
        if _clip_is_closeup(clip):
            span = cont.get("expression_span")
            if span in (None, ""):
                add(BLOCK, "表情一致性", loc,
                    "近景/特写/反打镜必须声明 continuity.expression_span（微/中/大）——跨情绪近景是脸随表情"
                    f"漂移的头号根因，不可 opt-in。按起止情绪（{cont.get('start_state')!r}→{cont.get('end_state')!r}）"
                    "补标；大表情(大)须配首尾双帧 need_endframe=true。",
                    return_to_stage="script_stage2")
            elif span not in EXPRESSION_SPAN_VALUES:
                add(BLOCK, "表情一致性", loc,
                    f"continuity.expression_span={span!r} 非法；必须是 {'/'.join(EXPRESSION_SPAN_VALUES)} 之一。",
                    return_to_stage="script_stage2")
        is_high_motion = str(clip.get("template") or "") in HIGH_MOTION_TEMPLATES
        # 高速运动镜首尾双帧不可豁免：快速运动靠首+尾两帧把两端钉死、模型只补中间，是控高动态一致性的
        # 关键手段（与表情近景的 need_endframe 不同关注点——那是脸随表情漂，这是肢体大动作漂）。这类镜
        # 不论是否末镜、都不接受 endframe_exempt_reason，是 i<len 默认闸 + 表情近景闸之外的第三条触发。
        if is_high_motion and cont.get("need_endframe") is not True:
            add(BLOCK, "尾帧", loc,
                f"高速运动镜(template={clip.get('template')})必须 need_endframe=true，且不可用 endframe_exempt_reason 豁免——"
                "快速运动靠首+尾帧钉住两端、模型只补中间是控一致性关键；末镜同样要求。",
                return_to_stage="script_stage2")
        elif i < len(clips) and cont.get("need_endframe") is not True:
            exempt = cont.get("endframe_exempt_reason")
            if not exempt:
                add(BLOCK, "尾帧", loc, "非最终 Clip 默认必须 need_endframe=true；若豁免需填写 endframe_exempt_reason")
            elif len(str(exempt).strip()) < ENDFRAME_EXEMPT_REASON_MIN_CHARS:
                add(BLOCK, "尾帧", loc,
                    f"endframe_exempt_reason 过短（{str(exempt).strip()!r}）——豁免首尾双帧必须写明实质理由"
                    "（如「极短镜<3s 无表情变化」），不接受占位/单字。")
        if cont.get("need_endframe") is True:
            end_png = cont.get("endframe_png")
            if not end_png:
                add(BLOCK, "尾帧", loc, "need_endframe=true 但未填写 endframe_png")
            elif require_frame_assets:
                full = end_png if os.path.isabs(end_png) else os.path.join(root, end_png)
                if not os.path.exists(full):
                    add(BLOCK, "尾帧", full, "need_endframe=true 但尾帧 PNG 不存在")
        # 中段锚帧：声明了 midframe/anchors 就必须是完整可执行契约。
        # 执行成本由后端能力决定（native multiframe / split relay / qc reference），但锚帧 PNG、
        # 时间点和理由缺一不放行，避免生成了 `_mid` 却在视频阶段被静默忽略。
        # midframe = 单锚帧手写糖（_mid）；anchors = 通用 N 锚帧链（_a1.._aN，anchor_planner 写）。
        mid = cont.get("midframe")
        anchors = cont.get("anchors")
        # 三帧契约铁律（默认强制·能力门控）：默认每镜 ≥3 帧（首+中+尾），不因 cost/风格豁免。
        # **唯一豁免**=路由视频后端不支持 ≥3 帧（first-frame-only，连首尾拆段都钉不住第3帧）——
        # 由 adapter 层 backend_supports_three_plus_frames 按后端能力自动判定，不是用户偏好。
        # backend 取 storyboard.policy.video_backend（缺/未知后端 → 按支持·向前看默认强制）。
        # policy 缺失/契约前定稿的旧集据此被拦，须补跑 anchor_planner --write 后才放行。
        sb_backend = policy.get("video_backend") if isinstance(policy, dict) else None
        midframe_enforced = backend_supports_three_plus_frames(sb_backend)
        if midframe_enforced \
                and mid is None and anchors is None and not cont.get("midframe_exempt_reason"):
            add(BLOCK, "中段锚帧", loc,
                "三帧契约铁律（首帧+中段锚帧+尾帧·默认强制）下，每镜必须声明 "
                "continuity.midframe/anchors，或写 midframe_exempt_reason（极短镜<3s豁免）；"
                "跑 anchor_planner.py --default-midframe --write 自动补齐。"
                "（唯一豁免=后端不支持≥3帧，由后端能力自动判定·不因 cost/风格放行）")
        if mid is not None and anchors is not None:
            add(BLOCK, "中段锚帧", loc, "continuity.midframe 与 continuity.anchors 不能同时声明（语义歧义）；单锚帧用 midframe 或一项 anchors，二选一")
            continue
        if mid is not None:
            if not isinstance(mid, dict):
                add(BLOCK, "中段锚帧", loc, "continuity.midframe 必须是 object（midframe_png/split_at_sec/reason）")
                continue
            anchors = [{**mid, "_fields": ("midframe_png", "split_at_sec", "reason")}]
        if anchors is not None:
            if not isinstance(anchors, list) or not anchors:
                add(BLOCK, "中段锚帧", loc, "continuity.anchors 必须是非空 list（每项 anchor_png/at_sec/reason）")
                continue
            duration = clip.get("duration")
            prev_at = 0.0
            for k, a in enumerate(anchors, 1):
                if not isinstance(a, dict):
                    add(BLOCK, "中段锚帧", loc, f"anchors[{k}] 必须是 object（anchor_png/at_sec/reason）")
                    continue
                png_key, at_key, reason_key = a.get("_fields", ("anchor_png", "at_sec", "reason"))
                for label, key in (("锚帧 PNG", png_key), ("锚点秒数", at_key), ("锚帧理由", reason_key)):
                    if a.get(key) in (None, ""):
                        add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 缺字段：{key}（中段锚帧契约必须写明{label}；执行时会按后端能力走原生多帧、拆段接力或 QC/reference）")
                at = a.get(at_key)
                if at not in (None, ""):
                    if isinstance(at, bool) or not isinstance(at, (int, float)):
                        add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 的 {at_key} 必须是数字：{at!r}")
                    else:
                        if isinstance(duration, (int, float)) and not (0 < at < duration):
                            add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 的 {at_key}={at} 必须落在 (0, duration={duration}) 内，各段还须 ≥ 目标后端最短时长")
                        if at <= prev_at:
                            add(BLOCK, "中段锚帧", loc, f"锚帧 {k} 的 {at_key}={at} 必须严格递增（前一锚点 {prev_at}）")
                        prev_at = at if at > prev_at else prev_at
                png = a.get(png_key)
                if png and require_frame_assets:
                    full = png if os.path.isabs(png) else os.path.join(root, png)
                    if not os.path.exists(full):
                        add(BLOCK, "中段锚帧", full, f"声明了锚帧 {k} 但锚帧 PNG 不存在")
                    else:
                        _check_midframe_generation_self_check(root, ep, str(png), loc, k)
    return data


def check_storyboard_visual_contract(root: str, ep: str) -> None:
    """storyboard.json must seed the visual contract at the script stage.

    Axis/eyeline, scene light position, character-state progression and the
    shot-size ladder are director decisions made when the storyboard is cut.
    They must live in storyboard.json's `visual_contract` so n2d-image inherits
    them instead of re-inventing them — the single upstream source of truth for
    everything later baked into first-frame pixels.
    """
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        return  # storyboard 缺失/损坏由 check_storyboard_contract 报，避免重复
    vc = data.get("visual_contract")
    if not isinstance(vc, dict):
        add(BLOCK, "视觉契约", p, "storyboard.json 缺 visual_contract 种子块；轴线/光位/状态/景别是分镜设计阶段的导演决策，须在此写死供出图继承（回 n2d-script 补 visual_contract）")
        return
    for key in VISUAL_CONTRACT_FIELDS:
        if key not in vc:
            add(BLOCK, "视觉契约", p, f"storyboard.json visual_contract 缺字段：{key}")


def check_storyboard_style_contract(root: str, ep: str) -> None:
    """storyboard.json must seed the chosen base visual style contract.

    The style choice belongs in user settings/global_style, not in skill code.
    The contract turns that choice into repeatable constraints so image/video
    prompts inherit one source instead of appending generic style adjectives.
    """
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        return
    sc = data.get("style_contract")
    legacy = False
    fields = STYLE_CONTRACT_FIELDS
    if not isinstance(sc, dict):
        sc = data.get("cinematic_contract")
        legacy = isinstance(sc, dict)
        fields = CINEMATIC_CONTRACT_FIELDS
    if not isinstance(sc, dict):
        add(BLOCK, "基础视觉风格契约", p, "storyboard.json 缺 style_contract 种子块；基础视觉风格必须来自 `_设置.md`/global_style，并在分镜设计阶段写成结构化契约供出图/出视频继承")
        return
    key_name = "cinematic_contract" if legacy else "style_contract"
    for key in fields:
        if key not in sc:
            add(BLOCK, "基础视觉风格契约", p, f"storyboard.json {key_name} 缺字段：{key}")
    # ⑥ 软校验：风格名 应与选择点「基础视觉风格」同源（项目选二次元、契约却写写实=矛盾，gate 只查在场会漏）
    if not legacy:
        chosen = str(get_setting(root, "基础视觉风格", "")).strip()
        name = str(sc.get("风格名", "")).strip()
        if chosen and name and chosen not in name and name not in chosen:
            add(WARN, "风格一致性", p,
                f"style_contract.风格名「{name}」与 _设置.md 基础视觉风格「{chosen}」不一致——风格真值应同源；核对是否选错风格或契约写偏")


STYLEID_CLOSEUP_MARKERS = ("CU", "MCU", "ECU", "近景", "特写", "大特写", "脸部", "面部", "反打", "过肩", "closeup", "close-up")
STYLEID_CLOSEUP_RATIO = 0.4


def _styleid_release_signoff_path(root: str, ep: str = "") -> str:
    suffix = f"_{ep}" if ep else ""
    return os.path.join(root, "生产数据", f"styleid_release_signoff{suffix}.json")


def _styleid_structured_signoff_ok(root: str, ep: str = "") -> bool:
    for path in (_styleid_release_signoff_path(root, ep), _styleid_release_signoff_path(root, "")):
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        if data.get("kind") not in (None, "n2d_styleid_release_signoff"):
            continue
        if data.get("accepted") is not True:
            continue
        if not str(data.get("reviewer") or "").strip():
            continue
        if not str(data.get("reason") or "").strip():
            continue
        if not _override_expiry_ok(data.get("expires_at") or data.get("expires")):
            continue
        return True
    return False


def _storyboard_closeup_character_ratio(root: str, ep: str) -> Tuple[int, int]:
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict):
        return 0, 0
    clips = data.get("clips") or data.get("shots") or []
    if not isinstance(clips, list):
        return 0, 0
    total = 0
    closeups = 0
    for clip in clips:
        if not isinstance(clip, Mapping):
            continue
        text = json.dumps(clip, ensure_ascii=False)
        if not CHARACTER_ID_RE.search(text):
            continue
        total += 1
        if any(marker.lower() in text.lower() for marker in STYLEID_CLOSEUP_MARKERS):
            closeups += 1
    return closeups, total


def _styleid_release_gate_required(root: str, ep: str = "", stage: str = "") -> Tuple[bool, str]:
    if consistency_release_profile(root, stage, ep) == "production":
        return True, "production/release profile"
    if ep:
        closeups, total = _storyboard_closeup_character_ratio(root, ep)
        if total and closeups >= 2 and closeups / max(total, 1) >= STYLEID_CLOSEUP_RATIO:
            return True, f"角色 CU/MCU 近景占比高（{closeups}/{total}）"
    return False, ""


def check_stylized_face_encoder_policy(root: str, ep: str = "", stage: str = "") -> None:
    """风格化项目应把脸一致性机检切到 StyleID；缺权重时标降级 KPI。"""
    style = get_setting(root, "基础视觉风格", "")
    encoder = get_setting(root, "脸一致性机检后端", "arcface")
    policy = face_encoder_policy(style, encoder)
    if not (policy.get("stylized") or policy.get("requested_styleid")):
        return
    if policy.get("status") == "ready":
        return
    settings_loc = os.path.join(root, "_设置.md")
    model_status = str(policy.get("model_status") or "missing")
    model_path = str(policy.get("model_path") or "")
    if policy.get("requested_styleid"):
        detail = "未配置" if model_status == "missing" else f"路径不存在：{model_path}"
        msg = (
            f"基础视觉风格「{style}」已选择脸一致性机检后端=styleid，但 N2D_STYLEID_MODEL {detail}；"
            "StyleID 不可用时会回退 arcface_fallback，本集 character_consistency_kpi 标为降级档。"
        )
    else:
        msg = (
            f"基础视觉风格「{style}」属于风格化/漫剧脸，当前脸一致性机检后端={policy.get('encoder') or encoder}；"
            "建议项目级设置 `脸一致性机检后端: styleid` 并配置 N2D_STYLEID_MODEL。未配置前，"
            "角色脸一致性 KPI 按降级档处理，近景结果需提高人审权重。"
        )
    release_required, reason = _styleid_release_gate_required(root, ep, stage)
    if release_required and not _styleid_structured_signoff_ok(root, ep):
        signoff_rel = os.path.relpath(_styleid_release_signoff_path(root, ep), root)
        add(
            BLOCK,
            "风格化脸机检",
            settings_loc,
            f"{msg} 当前已触发发布闸门（{reason}）：缺可用 N2D_STYLEID_MODEL 时不得进入正式投放/高近景角色镜。"
            f"若确认接受降级，需写结构化 {signoff_rel}（kind=n2d_styleid_release_signoff, "
            "accepted=true, reviewer, reason, expires_at）后复跑。",
            return_to_stage="image",
        )
        return
    if release_required:
        msg += " 已检测到结构化 StyleID 降级签收；仍建议在投放前补 N2D_STYLEID_MODEL 并重跑 full QC。"
    add(WARN, "风格化脸机检", settings_loc, msg, return_to_stage="review")


_TONE_SPLIT_RE = re.compile(r"[；;。.，,\n]")
PROP_ID_ANY_RE = re.compile(r"\bPROP_[\w\-\u4e00-\u9fff]+\b")
POSSESSION_WORDS = (
    "手持", "握", "拿", "抓", "举", "抱着", "持有", "佩戴", "戴着", "holds", "holding", "grabs",
)
POSSESSION_TRANSFER_WORDS = (
    "递给", "交给", "接过", "夺过", "抢过", "掉落", "丢下", "放下", "松开",
    "handoff", "transfer", "release", "drop", "pickup",
)
CORE_POSSESSION_ASSET_WORDS = (
    "武器", "兵器", "剑", "刀", "匕首", "枪", "弓", "箭", "法宝", "灵宝", "神器", "法器",
    "证物", "线索", "信物", "令牌", "钥匙", "圣旨", "密信", "血书", "契约", "玉佩", "玉簪",
    "毒", "药瓶", "丹药", "符", "符箓", "卷轴", "灵珠", "戒指", "weapon", "evidence", "artifact", "relic",
)


def _tone_base(value) -> str:
    """色调基线的基调首句（；。，前），去空白——逐集细化在首句后，基调首句应跨集恒定。"""
    s = str(value or "").strip()
    if not s:
        return ""
    return re.sub(r"\s+", "", _TONE_SPLIT_RE.split(s)[0])


def _earliest_storyboard_ep(root: str) -> Optional[str]:
    """打样集 = 最早一个有 storyboard.json 的集（按集号）。"""
    eps = []
    for p in glob.glob(os.path.join(root, "脚本", "*", "storyboard.json")):
        name = os.path.basename(os.path.dirname(p))
        digits = "".join(c for c in name if c.isdigit())
        if digits:
            eps.append((int(digits), name))
    return min(eps)[1] if eps else None


def _possession_ledger_path_candidates(root: str, ep: str) -> List[str]:
    return [
        os.path.join(root, "生产数据", f"possession_ledger_{ep}.json"),
        os.path.join(root, "生产数据", f"asset_possession_{ep}.json"),
        os.path.join(root, "脚本", ep, "possession_ledger.json"),
        os.path.join(root, "设定库", "possession_ledger.json"),
    ]


def _possession_ledger_exists(root: str, ep: str) -> bool:
    return any(os.path.isfile(p) for p in _possession_ledger_path_candidates(root, ep))


def _possession_mentions_core_asset(text: str, props: Sequence[str]) -> bool:
    blob = str(text or "")
    if any(word.lower() in blob.lower() for word in CORE_POSSESSION_ASSET_WORDS):
        return True
    return any(any(word.lower() in prop.lower() for word in CORE_POSSESSION_ASSET_WORDS) for prop in props)


def check_storyboard_possession_gate(root: str, ep: str) -> None:
    """Storyboard 前置 POS：检测到关键道具持有/交接时，要求账本前移到分镜层。"""
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict):
        return
    clips = data.get("clips") or data.get("shots") or []
    if not isinstance(clips, list):
        return
    mentions: List[str] = []
    transfer_mentions: List[str] = []
    for idx, clip in enumerate(clips, start=1):
        if not isinstance(clip, Mapping):
            continue
        text = json.dumps(clip, ensure_ascii=False)
        props = PROP_ID_ANY_RE.findall(text)
        if not props:
            continue
        if any(w.lower() in text.lower() for w in POSSESSION_WORDS + POSSESSION_TRANSFER_WORDS):
            label = str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")
            shown = f"{label}:{'/'.join(sorted(set(props)))}"
            mentions.append(shown)
            if any(w.lower() in text.lower() for w in POSSESSION_TRANSFER_WORDS):
                transfer_mentions.append(shown)
            elif _possession_mentions_core_asset(text, props):
                transfer_mentions.append(shown)
    if not mentions or _possession_ledger_exists(root, ep):
        return
    target = os.path.join(root, "生产数据", f"possession_ledger_{ep}.json")
    shown = "、".join((transfer_mentions or mentions)[:8]) + ("…" if len(transfer_mentions or mentions) > 8 else "")
    if transfer_mentions:
        add(
            BLOCK,
            "持有账本(POS)",
            storyboard_path(root, ep),
            f"storyboard 已出现核心道具/武器/证物/法宝的持有、交接、丢失或拾取（{shown}），但缺 possession_ledger；"
            f"请先在 {target} 记录 clip、asset、holder、action，避免道具跨镜瞬移。",
            return_to_stage="script_stage2",
        )
    else:
        add(
            WARN,
            "持有账本(POS)",
            storyboard_path(root, ep),
            f"storyboard 已出现关键道具持有关系（{shown}），建议前置 possession_ledger 到分镜 gate；跨镜持有、破损、丢失别只靠 prompt 文本记忆。",
            return_to_stage="script_stage2",
        )


LONG_RUNNING_EP_THRESHOLD = 3  # 到第3集起跨集脸漂累积已成真问题，长线剧用无持久主体后端该提示升档


def long_running_weak_backend_advice(canon: str, cur_ep_num: int, ep_count: int) -> bool:
    """长线剧 × 无持久主体后端 是否应提示升档（纯函数·可测）。
    True = 当前后端无原生主体/角色 ID 能力，且项目确属多集长剧（当前集号或已有集数 ≥ 阈值）；
    单集/双集 demo 与已是持久主体后端都返回 False，不打扰。"""
    if image_backend_supports_persistent_subject(canon or ""):
        return False
    return max(int(cur_ep_num or 0), int(ep_count or 0)) >= LONG_RUNNING_EP_THRESHOLD


IDENTITY_LOCK_READY_STATUSES = {"ready", "registered", "validated", "deployed"}
LOCAL_LORA_IMAGE_BACKENDS = {"local", "local_open_source", "comfyui", "sdxl", "flux", "stable_diffusion", "stable-diffusion"}


def _normalize_lora_backend(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    canon, kind = classify_image_backend(text)
    if canon and kind == "approved":
        return canon
    compact = text.lower().replace(" ", "_")
    if compact in {"stable_diffusion", "stable-diffusion", "sd", "sdxl"}:
        return "sdxl"
    return compact


def _lora_usable_on_image_backend(lora: Mapping[str, Any], image_backend: str) -> bool:
    if str(lora.get("status") or "").strip() not in {"ready", "validated", "deployed"}:
        return False
    current = _normalize_lora_backend(image_backend)
    targets: List[str] = []
    for key in ("target_backends", "backends", "providers", "provider", "backend", "execution_backends"):
        targets.extend(_as_string_list(lora.get(key)))
    normalized_targets = {_normalize_lora_backend(v) for v in targets if _normalize_lora_backend(v)}
    if normalized_targets:
        return "*" in normalized_targets or "any" in normalized_targets or current in normalized_targets
    return current in LOCAL_LORA_IMAGE_BACKENDS


def _image_form_has_identity_lock(form: Mapping[str, Any], image_backend: str = "") -> bool:
    adapters = form.get("identity_adapters") if isinstance(form.get("identity_adapters"), Mapping) else {}
    image = adapters.get("image") if isinstance(adapters.get("image"), Mapping) else {}
    for backend, cfg in image.items():
        if not isinstance(cfg, Mapping):
            continue
        status = str(cfg.get("status") or "").strip()
        mode = str(cfg.get("mode") or "").strip()
        if str(backend) == "face_embedding" and status in IDENTITY_LOCK_READY_STATUSES:
            return True
        if status in IDENTITY_LOCK_READY_STATUSES and (
            image_backend_supports_persistent_subject(str(backend))
            or mode not in {"", "reference_group", "fallback_reference_group", "unsupported", "not_needed"}
        ):
            return True
    face_embedding = adapters.get("face_embedding") if isinstance(adapters.get("face_embedding"), Mapping) else {}
    if str(face_embedding.get("status") or "").strip() in IDENTITY_LOCK_READY_STATUSES:
        return True
    lora = adapters.get("lora") if isinstance(adapters.get("lora"), Mapping) else {}
    if _lora_usable_on_image_backend(lora, image_backend):
        return True
    return False


def core_forms_without_image_identity_lock(root: str, image_backend: str = "") -> Tuple[List[str], bool]:
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return [], False
    missing: List[str] = []
    has_core = False
    for char in reg.get("characters", []) or []:
        if not isinstance(char, dict):
            continue
        scope = f"{char.get('tier') or ''} {char.get('scope') or ''}"
        if not _CORE_SCOPE_RE.search(scope):
            continue
        has_core = True
        cid = str(char.get("id") or "").strip()
        name = str(char.get("name") or cid or "?").strip()
        for form in char.get("forms", []) or []:
            if not isinstance(form, dict):
                continue
            if _image_form_has_identity_lock(form, image_backend):
                continue
            form_name = str(form.get("form") or "").strip()
            missing.append(f"{name}({cid}/{form_name})" if form_name else f"{name}({cid})")
    return missing, has_core


# G-I1·2026-06-24 流程自审落地：长线剧的默认起点应是「可注册主体 ID」（②·先于 LoRA），不是死扛
# 无持久主体的 GPT Image 2。设计宪法 C4 不许私自写死后端——故不做静默 auto-flip，而是给确定性推荐文案，
# 由 gate BLOCK 携带，让用户在 n2d-image 选择点带 ② 推荐升档并摆「换后端=整集重做定妆的一致性税」知情权衡。
IMAGE_IDENTITY_LOCK_RECOMMENDATION = (
    "【G-I1 推荐升档】长线默认起点应为可注册主体 ID（②·先于 LoRA）：可灵主体库 / 即梦角色库 / "
    "Seedream Universal Reference（注册一次按 ID 跨镜跨集引用）；或对核心角色训 LoRA。"
    "hero/反复崩脸角色可叠 max-lock 栈：主体 ID + PuLID(脸保真) + 低强度角色 LoRA(~0.6) + ControlNet。"
    "在 n2d-image 选择点 `生图模型` 带此推荐向用户摆「换后端=整集重做定妆的一致性税」知情权衡，不私自写死后端。"
)


def check_long_running_weak_backend(root: str, ep: str) -> None:
    """image_preflight：长线剧用「无持久主体」后端逐镜参考图派生时，核心/常驻角色必须有身份锁。

    跨集脸漂真因=单张定妆照只是板式、每镜重画脸逐集累积(见 n2d-image 与 references/模型矩阵.md)；
    到第3集仍无 native subject / face_embedding / LoRA 等执行层锁，不能只停留在 WARN。"""
    setting = get_setting(root, "生图AI", "Codex").strip()
    canon, _kind = classify_image_backend(setting)
    try:
        cur = _ce_episode_number(ep) or 0
    except Exception:
        cur = 0
    ep_count = len({os.path.basename(os.path.dirname(p))
                    for p in glob.glob(os.path.join(root, "脚本", "*", "storyboard.json"))})
    if not long_running_weak_backend_advice(canon or "", cur, ep_count):
        return
    missing, has_core = core_forms_without_image_identity_lock(root, canon or setting)
    if missing:
        shown = "、".join(missing[:8]) + ("…" if len(missing) > 8 else "")
        add(
            BLOCK,
            "生图AI一致性",
            f"生图AI={setting}",
            f"长线剧（{ep}）仍用无持久主体后端（{canon or setting}）逐镜参考图派生，且核心/常驻角色缺 native subject / Face Lock / face_embedding / LoRA：{shown}。"
            "第3集起这不是建议项，会跨集累积脸漂；请先注册原生主体、启用 face_embedding，或对核心角色完成 LoRA 后再付费出图。"
            + IMAGE_IDENTITY_LOCK_RECOMMENDATION,
            return_to_stage="image",
        )
        return
    if not has_core:
        add(BLOCK, "生图AI一致性", f"生图AI={setting}",
            f"长线剧（{ep}）仍用无持久主体后端（{canon or setting}）逐镜参考图派生，但 registry 未标出核心/常驻角色；"
            "请先把核心/常驻角色 scope/tier 写入 identity_registry，并为这些角色注册 native subject / Face Lock / face_embedding / LoRA；"
            "否则无法判断谁必须升档，长距离复现会把脸漂累积到后续集。"
            + IMAGE_IDENTITY_LOCK_RECOMMENDATION,
            return_to_stage="image")


def check_cross_episode_style(root: str, ep: str) -> None:
    """跨集色调/风格基线：以打样集为基准比对本集 色调基线基调 + 风格名。

    集级 visual_contract/style_contract 各自自洽、inherit 各自 pass，整部却可能画风跳（第5集冷青灰、第6集暖橙）。
    色调基线允许逐集细化，但其【基调首句】应跨集恒定；风格名应完全一致。漂移→WARN（以打样集为准或确认有意改）。
    """
    base_ep = _earliest_storyboard_ep(root)
    if not base_ep or base_ep == ep:
        return
    # 直接读 JSON（只需契约块，不触发 load_storyboard 的 clips[] 硬校验与副作用 BLOCK）
    base, cur = load_json(storyboard_path(root, base_ep)), load_json(storyboard_path(root, ep))
    if not isinstance(base, dict) or not isinstance(cur, dict):
        return
    p = storyboard_path(root, ep)
    base_tone = _tone_base((base.get("visual_contract") or {}).get("色调基线"))
    cur_tone = _tone_base((cur.get("visual_contract") or {}).get("色调基线"))
    if base_tone and cur_tone and base_tone != cur_tone:
        add(WARN, "跨集色调", p,
            f"本集色调基线基调「{cur_tone}」与打样集 {base_ep}「{base_tone}」不一致——色调可逐集细化但基调应跨集恒定；"
            f"以打样集为准或确认有意改（防整部画风跳）", return_to_stage="script_stage2")
    base_name = str((base.get("style_contract") or {}).get("风格名", "")).strip()
    cur_name = str((cur.get("style_contract") or {}).get("风格名", "")).strip()
    if base_name and cur_name and base_name != cur_name:
        add(WARN, "跨集风格", p,
            f"本集风格名「{cur_name}」与打样集 {base_ep}「{base_name}」不一致——基础视觉风格应跨集统一；核对是否选错风格",
            return_to_stage="script_stage2")


def check_cross_episode_character_definition(root: str, ep: str) -> None:
    """跨集「角色文字定义」漂移信号（advisory·WARN）：本集是否在悄悄重新派生角色而非复用定妆锚。

    identity_registry 是跨集共享的单一真值源（一部一份），但**每集的出图总览/prompt 文字**是手/AI
    现写的，可能把已建卡角色重描成与锚定相矛盾的样子（换发色/换装/换配饰）——这类文字漂移在出图前
    此前零机检（只有渲染后人脸 embedding 可能抓到，且发型/服装人脸检测看不见）。

    本检查保守取信号、不误伤：对 registry 里每个有 `forms[].anchor_phrase`（锚定相）的角色，若其名字/别名
    或 CHAR_id 在本集出图总览里**被引用**，却**一个锚定相描述符都没出现**（凤眼薄唇/乌黑.../月白粗布旧宫装…
    按 `·` 切的 token 全缺）→ WARN：可能跨集重新派生，请核对发型/瞳色/服装/配饰与定妆库一致。只要总览引用了
    锚定相里任一描述符即放行（低误报）。纯 WARN 不 BLOCK——文字矛盾判定本身模糊，先把"零信号"补成"有信号"。
    """
    data = load_json(identity_registry_path(root))
    if not isinstance(data, dict):
        return  # 定妆库未建（如出图前早期）——跳过
    chars = data.get("characters")
    if isinstance(chars, dict):
        chars = list(chars.values())
    if not isinstance(chars, list) or not chars:
        return
    overview_path = os.path.join(root, _ce_overview_rel(ep))
    if not os.path.isfile(overview_path):
        return  # 本集出图总览未生成——跳过，不误报
    try:
        overview = open(overview_path, encoding="utf-8").read()
    except OSError:
        return
    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        names = [n.strip() for n in str(c.get("name") or "").replace("／", "/").split("/") if n.strip()]
        referenced = (cid and cid in overview) or any(n in overview for n in names)
        if not referenced:
            continue
        forms = c.get("forms") if isinstance(c.get("forms"), list) else []
        anchor = str((forms[0] if forms else {}).get("anchor_phrase") or "").strip()
        if not anchor:
            continue  # 无锚定相可比
        tokens = [t.strip() for t in anchor.replace("，", "·").replace(",", "·").split("·") if len(t.strip()) >= ANCHOR_TOKEN_MIN_CHARS]
        if tokens and not any(t in overview for t in tokens):
            label = names[0] if names else cid
            add(WARN, "跨集角色定义", overview_path,
                f"本集出图总览引用了角色「{label}」({cid})，却未出现其 identity_registry 锚定相任一描述符"
                f"（{anchor}）——可能跨集重新派生而非复用定妆。请核对本集发型/瞳色/服装/配饰与定妆库一致，"
                "并在总览引用锚定相（或角色参考图）以防跨集悄悄变样。",
                return_to_stage="image")


def check_cross_episode_contract(root: str, ep: str) -> None:
    """跨集视觉契约方向反转（advisory·WARN）：同一地点跨集光位左右/轴线走向翻 = 越轴/光跳穿帮。

    `check_contract_inheritance` 管**同集内**出图↔出视频逐字一致；`check_cross_episode_style` 管整部色调/
    风格名恒定。本检查补第三类跨集穿帮——读本集与**前一可比集**的 `出图/第N集/prompt/00_总览.md` 视觉契约，
    只在 asset_registry 的 LOC 地点**两集都出现且方向反转**时报（地点共现门控压噪音）。纯启发式，**只 WARN
    不 BLOCK**（同 cross_episode_contract.py 设计）；过去靠人手动跑那个脚本→几乎没人跑，现在并进 gate 自动落地。
    """
    cur_rel = _ce_overview_rel(ep)
    cur_path = os.path.join(root, cur_rel)
    if not os.path.isfile(cur_path):
        return  # 本集出图总览未生成（如 image_preflight 早于出图）——跳过，不误报
    prev_ep = _ce_prior_episode(root, ep)
    if not prev_ep:
        return  # 首集无前集可比
    # 乱序/跳集生产：prior_episode 取的是"最近一个有出图总览的前集"，可能跨过缺总览的中间集。
    # 跨过缺口的对比会让"已覆盖"悄悄变成"跨集没逐集比过"——留个 WARN 信号，别静默跳。
    cur_n = _ce_episode_number(ep)
    prev_n = _ce_episode_number(prev_ep)
    if cur_n is not None and prev_n is not None and prev_n < cur_n - 1:
        add(WARN, "跨集契约", cur_path,
            f"跨集视觉契约对比跨过了缺失的中间集：本集（{ep}）只与 {prev_ep} 比对，"
            f"第 {prev_n + 1}–{cur_n - 1} 集 的出图总览缺失、未参与逐集核对。"
            "按集顺序补齐中间集总览后再核对跨集光位/轴线一致性。")
    prev_path = os.path.join(root, _ce_overview_rel(prev_ep))
    if not os.path.isfile(prev_path):
        return  # 防御：prior_episode 已保证存在
    try:
        prev_text = open(prev_path, encoding="utf-8").read()
        cur_text = open(cur_path, encoding="utf-8").read()
    except OSError:
        return
    diff = _cross_episode_diff(prev_text, cur_text, _ce_scene_names(root), prev_ep=prev_ep, cur_ep=ep,
                               core_scenes=_ce_core_scene_names(root))
    for w in diff.get("warnings", []):
        # P2b：核心主场景（asset_registry 显式标 core）跨集光位/轴线反转升 BLOCK；其余仍 WARN（启发式·人判）。
        sev = BLOCK if w.get("level") == "block" else WARN
        add(sev, "跨集光位轴线", f"{cur_path}（vs {prev_ep}）", w.get("note", ""),
            return_to_stage="image", scene=w.get("scene", ""), kind=w.get("kind", ""),
            rerun_scope="同地点跨集光位/轴线翻=越轴/光跳穿帮；确认是否有意（反打/换机位），否则回 n2d-image 对齐前集 00_总览 视觉契约。",
            affected_artifacts=[cur_rel, _ce_overview_rel(prev_ep), "出图/共享/asset_registry.json"])


def _clip_blob(clip: dict) -> str:
    # 复杂镜头关键词检测只扫散文描述，不扫结构化 `continuity` 块——其 schema 字段名/枚举值（如
    # `eyeline` 字段、`transition:"eyeline"`）与 dialogue_shot_reverse 关键词 `eyeline` 撞名，会让
    # 每个填了 continuity.eyeline（formats §4 要求每 clip 填）的合规 clip 误判成对话反打。
    scanned = {k: v for k, v in clip.items() if k != "continuity"} if isinstance(clip, dict) else clip
    try:
        return json.dumps(scanned, ensure_ascii=False)
    except Exception:
        return str(scanned)


def _first_template_keyword_hit(blob: str) -> Optional[str]:
    low = blob.lower()
    for template_id, words in SPECIAL_SHOT_KEYWORDS:
        for word in words:
            token = str(word).strip()
            if not token:
                continue
            low_token = token.lower()
            # Short ASCII triggers such as "ots" must not fire inside schema
            # keys like "shots"; CJK triggers still use substring matching.
            if low_token.isascii() and re.fullmatch(r"[a-z0-9_+-]+", low_token):
                if re.search(rf"(?<![a-z0-9]){re.escape(low_token)}(?![a-z0-9])", low):
                    return template_id
            elif token in blob:
                return template_id
    return None


def _field_is_missing(contract: dict, key: str) -> bool:
    if key not in contract:
        return True
    value = contract.get(key)
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


def _is_restricted_partial_form(char: dict, form: dict) -> bool:
    """局部出镜角色不应该被强行要求正/侧/背/三视图。"""
    form_name = str(form.get("form") or "").strip()
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), dict) else {}
    build_tier = str(atlas.get("build_tier") or "").strip()
    face_policy = str(char.get("face_policy") or form.get("face_policy") or "").strip()
    forbidden = form.get("drift_forbidden") or char.get("drift_forbidden") or []
    forbidden_blob = " ".join(str(x) for x in forbidden) if isinstance(forbidden, list) else str(forbidden)
    return (
        form_name in {"局部参考", "局部参考（暂不正脸）"}
        and (
            face_policy == "no_full_face"
            or build_tier == "restricted_partial"
            or "no_full_face" in forbidden_blob
            or "no_clear_facial_features" in forbidden_blob
        )
    )


def check_storyboard_special_templates(root: str, ep: str) -> None:
    """Complex shots must be declared through reusable storyboard templates.

    The expensive image/video stages should inherit a structured action/blocking
    contract instead of asking the model to invent fights, chases, reverse shots
    or crowd staging from prose every time.
    """
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        return
    clips = data.get("clips")
    if not isinstance(clips, list):
        return
    for i, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            continue
        loc = f"{p} clip#{i}"
        template_id = str(clip.get("template", "")).strip()
        contract = clip.get("template_contract")
        blob = _clip_blob(clip)
        keyword_template = _first_template_keyword_hit(blob)

        if not template_id:
            if keyword_template:
                add(
                    BLOCK,
                    "专项镜头模板",
                    loc,
                    f"复杂镜头疑似「{keyword_template}」，但缺 template/template_contract；回 n2d-script 按 references/专项镜头模板库.md 套模板，不要从零写 prompt",
                )
            elif isinstance(contract, dict):
                add(BLOCK, "专项镜头模板", loc, "有 template_contract 但缺 template；两者必须成对出现")
            continue

        if template_id not in SPECIAL_SHOT_TEMPLATE_FIELDS:
            add(
                BLOCK,
                "专项镜头模板",
                loc,
                f"未知 template「{template_id}」；只能使用 {', '.join(SPECIAL_SHOT_TEMPLATE_FIELDS.keys())}",
            )
            continue
        if not isinstance(contract, dict):
            add(BLOCK, "专项镜头模板", loc, f"template={template_id} 但缺 template_contract 结构块")
            continue
        if str(contract.get("template_id", "")).strip() != template_id:
            add(BLOCK, "专项镜头模板", loc, f"template_contract.template_id 必须等于 template「{template_id}」")
        for key in SPECIAL_SHOT_TEMPLATE_FIELDS[template_id]:
            if _field_is_missing(contract, key):
                add(BLOCK, "专项镜头模板", loc, f"template={template_id} 的 template_contract 缺字段：{key}")


def _gate_make_clip_id(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("clip_id") or clip.get("id") or clip.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return f"Clip_{idx:02d}"


def check_spectacle_sequence_plan(root: str, ep: str) -> None:
    """Require a sequence-level continuity ledger for spectacle clips before video."""
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict):
        return
    clips = data.get("clips") or []
    if not isinstance(clips, list):
        return
    required: Dict[str, str] = {}
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        kind = infer_spectacle_type(clip)
        if kind:
            required[_gate_make_clip_id(clip, idx)] = kind
    if not required:
        return

    rel = os.path.join("生产数据", f"spectacle_sequence_plan_{ep}.json")
    path = os.path.join(root, rel)
    plan = load_json(path)
    story_rel = os.path.relpath(storyboard_path(root, ep), root)
    if not isinstance(plan, dict):
        add(
            BLOCK,
            "高动态序列总账",
            path,
            f"storyboard 含高动态/大场景 Clip（{', '.join(required)}），但缺 {rel}；"
            "先生成跨 Clip 动作/空间/资产连续性总账，再进视频付费链路。",
            return_to_stage="script_stage2",
            affected_shots=list(required),
            affected_artifacts=[story_rel, rel],
            rerun_scope="运行 python3 skills/n2d-script/scripts/spectacle_sequence_plan.py <作品根> <集> --write 后重跑 video gate。",
        )
        return
    if str(plan.get("kind") or "") != SPECTACLE_SEQUENCE_PLAN_KIND:
        add(
            BLOCK,
            "高动态序列总账",
            path,
            f"spectacle_sequence_plan kind 必须是 {SPECTACLE_SEQUENCE_PLAN_KIND}。",
            return_to_stage="script_stage2",
            affected_artifacts=[rel],
        )
        return
    sequences = plan.get("sequences")
    if not isinstance(sequences, list) or not sequences:
        add(
            BLOCK,
            "高动态序列总账",
            path,
            "spectacle_sequence_plan 缺 sequences[]；不能用空总账放行高动态/大场景视频。",
            return_to_stage="script_stage2",
            affected_shots=list(required),
            affected_artifacts=[rel],
        )
        return
    covered = {
        str(cid)
        for seq in sequences if isinstance(seq, Mapping)
        for cid in (seq.get("clip_order") or [])
    }
    missing = [cid for cid in required if cid not in covered]
    if missing:
        add(
            BLOCK,
            "高动态序列总账",
            path,
            f"spectacle_sequence_plan 未覆盖 storyboard 高动态 Clip：{', '.join(missing)}；"
            "每条打斗/追逐/腾云/大场景都必须进入 sequence_id、handoff_state、path_lock 与引用策略。",
            return_to_stage="script_stage2",
            affected_shots=missing,
            affected_artifacts=[rel, story_rel],
            rerun_scope="重跑 spectacle_sequence_plan.py --write，并检查 clip_order 是否覆盖最新 storyboard。",
        )


def check_action_beat_budget(root: str, ep: str, stage: str = "video") -> None:
    """一镜一主导动作 + 单拍可读时长（Veo「一 clip 一动作」+ 打斗拆 2–3 拍）。

    高动态镜最常见崩法：把整段攻防(攻击+格挡+反击+命中)塞进一条 clip——物理引擎会乱、命中帧读不出。
    按动作节拍类别数 + 单拍时长预算给拆镜信号，把它挡在最贵的出视频之前。
    「单 Clip 时长超后端上限」已由 risk_flags long_duration 闸守，这里只补「节拍塞太满」这层。
    """
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict):
        return
    clips = data.get("clips") or []
    if not isinstance(clips, list):
        return
    story_rel = os.path.relpath(storyboard_path(root, ep), root)
    production = consistency_release_profile(root, stage, ep) == "production"
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        kind = infer_spectacle_type(clip)
        if kind not in ACTION_CHOREOGRAPHY_SHOT_TYPES:
            continue
        clip_id = _gate_make_clip_id(clip, idx)
        cats = action_beat_categories(json.dumps(clip, ensure_ascii=False))
        try:
            dur = float(clip.get("duration") or 0)
        except (TypeError, ValueError):
            dur = 0.0
        beats = beat_decomposition(kind)
        beat_names = "/".join(b["beat"] for b in beats) or "起手/命中/反应"
        # ① 一镜塞了完整攻防回合（跨越 ≥3 个互斥节拍类别）→ 必须拆 beat。production 升 BLOCK。
        if len(cats) >= ACTION_BEAT_CATEGORY_SPLIT_THRESHOLD:
            add(
                BLOCK if production else WARN,
                "动作节拍预算",
                story_rel,
                f"{clip_id}({kind}) 一镜跨越 {len(cats)} 个动作节拍类别（{', '.join(cats)}）——"
                f"把完整攻防回合塞进一条 clip，模型物理易乱、命中帧读不出。按 beat 拆成 {beat_names} 各一镜"
                "（一镜一主导动作，相机从简）。",
                return_to_stage="script_stage2",
                affected_shots=[clip_id],
                affected_artifacts=[story_rel],
                rerun_scope="按 spectacle_sequence_plan 的 beat_decomposition 拆镜，回 n2d-script 阶段2 重切 storyboard，再跑 video gate。",
            )
            continue
        # ② 单拍时长不足：多个节拍挤进过短时长，命中帧/受力方向来不及读清（启发式·WARN）。
        if dur > 0 and len(cats) >= 2 and dur / len(cats) < MIN_ACTION_BEAT_SECONDS:
            add(
                WARN,
                "动作节拍预算",
                story_rel,
                f"{clip_id}({kind}) 时长 {dur:g}s 内塞了 {len(cats)} 个动作节拍（{', '.join(cats)}），"
                f"单拍均不足 {MIN_ACTION_BEAT_SECONDS:g}s——命中帧/受力方向来不及读清。延长该镜或拆成 {beat_names}。",
                return_to_stage="script_stage2",
                affected_shots=[clip_id],
                affected_artifacts=[story_rel],
            )


def identity_adapter_matrix_path(root: str) -> str:
    return os.path.join(root, "生产数据", "identity_adapter_matrix.json")


def _has_identity_handle(cfg: dict) -> bool:
    return any(str(cfg.get(key, "")).strip() for key in IDENTITY_HANDLE_FIELDS)


def _validate_identity_adapter_map(section: object, loc: str, label: str) -> None:
    if not isinstance(section, dict) or not section:
        add(BLOCK, "资产身份注册层", loc, f"`identity_adapters.{label}` 缺失或为空")
        return
    for backend, cfg in section.items():
        bloc = f"{loc} identity_adapters.{label}.{backend}"
        if not isinstance(cfg, dict):
            add(BLOCK, "资产身份注册层", bloc, "adapter 必须是对象，含 mode/status")
            continue
        for key in ("mode", "status"):
            if _field_is_missing(cfg, key):
                add(BLOCK, "资产身份注册层", bloc, f"adapter 缺字段：{key}")
        status = str(cfg.get("status", "")).strip()
        mode = str(cfg.get("mode", "")).strip()
        if status and status not in IDENTITY_KNOWN_STATUSES:
            add(BLOCK, "资产身份注册层", bloc, f"未知 status「{status}」；必须使用结构化枚举，不能自由写")
        allowed_modes = (IDENTITY_ALLOWED_IMAGE_MODES if label == "image" else IDENTITY_ALLOWED_VIDEO_MODES).get(str(backend))
        if allowed_modes and mode and mode not in allowed_modes:
            add(BLOCK, "资产身份注册层", bloc, f"{label}.{backend} mode「{mode}」不匹配后端能力；允许：{', '.join(allowed_modes)}")
        if status in IDENTITY_READY_STATUSES and not _has_identity_handle(cfg):
            add(BLOCK, "资产身份注册层", bloc, "registered/ready 状态必须填写真实 id/handle/reference/model_path，不能空登记")


def _lora_gap_loc_suffix(code: str) -> str:
    """LoRA 缺口码 → finding loc 尾缀（保持与历史逐条检查相同的定位粒度）。"""
    if code == "ready_model_hash_mismatch":
        return ".model_hash"
    if code == "ready_model_path_missing":
        return ".model_path"
    if code.startswith("ready_validation_report") or code.startswith("ready_dataset_warnings"):
        return ".validation_report"
    return ""


def _validate_identity_lora(section: object, loc: str, root: str) -> None:
    """LoRA ready 校验收口到契约单一真值源 lora_registry_ready_blocks / lora_gap_message。

    与 n2d-lora cmd_register、n2d-identity 同源演进；磁盘层检查（model_path 是否存在）按契约约定
    留在调用方（契约层不碰文件系统），缺口码命名 ready_model_path_missing。
    """
    if not isinstance(section, dict):
        add(BLOCK, "资产身份注册层", f"{loc} identity_adapters.lora", "缺 LoRA 状态对象")
        return
    status = str(section.get("status", "")).strip()
    if not status:
        add(BLOCK, "资产身份注册层", f"{loc} identity_adapters.lora", "LoRA 缺 status")
    if status == "ready":
        report = None
        report_rel = str(section.get("validation_report", "")).strip()
        if report_rel:
            report_path = report_rel if os.path.isabs(report_rel) else os.path.join(root, report_rel)
            report = load_json(report_path)  # 读不出 → None，契约层报 ready_validation_report_missing
        codes = lora_registry_ready_blocks(section, report)
        model_rel = str(section.get("model_path", "")).strip()
        if model_rel and not _identity_reference_exists(root, model_rel):
            codes.append("ready_model_path_missing")  # 磁盘检查由调用方补充（契约约定）
        for code in codes:
            add(BLOCK, "资产身份注册层", f"{loc} identity_adapters.lora{_lora_gap_loc_suffix(code)}", lora_gap_message(code))


def _validate_generation_control(section: object, loc: str) -> None:
    """Validate optional fixed seed-pool execution metadata.

    Legacy registries may omit this block; once present, it must be executable so
    backends that expose seed can pass it and backends that do not can record a
    no-op degradation instead of pretending to be reproducible.
    """
    if section is None:
        add(WARN, "固定 Seed", loc,
            "未登记 generation_control 固定 seed pool；若后端支持 seed 将无法统一传参，"
            "不支持 seed 的后端也缺 no-op 降级记录口径。")
        return
    if not isinstance(section, dict):
        add(BLOCK, "固定 Seed", f"{loc} generation_control", "generation_control 必须是对象")
        return
    strategy = str(section.get("seed_strategy") or "").strip()
    if strategy != "fixed_pool":
        add(BLOCK, "固定 Seed", f"{loc} generation_control.seed_strategy",
            "seed_strategy 必须为 fixed_pool；不要无限随机抽 seed。")
    pool = section.get("seed_pool")
    if not isinstance(pool, list) or len(pool) < 4 or not all(isinstance(v, int) for v in pool):
        add(BLOCK, "固定 Seed", f"{loc} generation_control.seed_pool",
            "seed_pool 必须是至少 4 个整数的固定种子池")
        pool_set = set()
    else:
        pool_set = set(pool)
        if len(pool_set) != len(pool):
            add(BLOCK, "固定 Seed", f"{loc} generation_control.seed_pool", "seed_pool 不能有重复 seed")
    usage = section.get("usage")
    if not isinstance(usage, dict):
        add(BLOCK, "固定 Seed", f"{loc} generation_control.usage",
            "usage 必须映射 turnaround/expression/closeup/shot 到 seed")
    else:
        for key in GENERATION_CONTROL_USAGE_KEYS:
            value = usage.get(key)
            if not isinstance(value, int):
                add(BLOCK, "固定 Seed", f"{loc} generation_control.usage.{key}", "usage seed 必须是整数")
            elif pool_set and value not in pool_set:
                add(BLOCK, "固定 Seed", f"{loc} generation_control.usage.{key}",
                    f"usage seed={value} 不在 seed_pool 内")
    support = section.get("backend_support")
    if not isinstance(support, dict) or not support:
        add(BLOCK, "固定 Seed", f"{loc} generation_control.backend_support",
            "backend_support 必须声明各生图后端支持状态")
    else:
        for backend, status in support.items():
            status_s = str(status or "").strip()
            if status_s not in GENERATION_CONTROL_ALLOWED_SUPPORT:
                add(BLOCK, "固定 Seed", f"{loc} generation_control.backend_support.{backend}",
                    f"未知 seed 支持状态「{status_s}」；必须用 supported / unsupported_or_unknown / backend_dependent_verify_adapter 等结构化值")
        codex_status = str(support.get("codex") or "").strip()
        if codex_status != "unsupported_or_unknown":
            add(WARN, "固定 Seed", f"{loc} generation_control.backend_support.codex",
                "Codex 当前不应被默认当成可复现 seed 后端；除非执行 adapter 明确暴露 seed，否则应写 unsupported_or_unknown。")
    fallback = str(section.get("fallback_policy") or "").strip()
    if "record" not in fallback or "seed" not in fallback:
        add(BLOCK, "固定 Seed", f"{loc} generation_control.fallback_policy",
            "fallback_policy 必须说明不支持 seed 时记录 no-op/degraded，而不是静默当可复现")
    record_required = section.get("record_required")
    if not isinstance(record_required, list):
        add(BLOCK, "固定 Seed", f"{loc} generation_control.record_required",
            "record_required 必须列出 seed 记账字段")
    else:
        missing = [key for key in GENERATION_CONTROL_RECORD_KEYS if key not in record_required]
        if missing:
            add(BLOCK, "固定 Seed", f"{loc} generation_control.record_required",
                "record_required 缺字段：" + ", ".join(missing))


def _validate_character_dna(section: object, loc: str) -> None:
    """Validate the five-layer character DNA lock: face + hair + outfit + accessories + texture."""
    if not isinstance(section, dict):
        add(BLOCK, "角色 DNA", f"{loc} character_dna",
            "character_dna 必须是对象，且固定包含 face/hair/outfit/accessories/texture 五层；不能只锁脸。")
        return
    for key in CHARACTER_DNA_FIELDS:
        value = section.get(key)
        if not isinstance(value, str) or not value.strip():
            add(BLOCK, "角色 DNA", f"{loc} character_dna.{key}",
                "角色 DNA 五层必须非空；无配饰也要写“无”，避免下游临场补设定。")


def _performance_signature_present(char: Mapping[str, Any], form: Mapping[str, Any]) -> bool:
    sig = form.get("performance_signature") or char.get("performance_signature")
    if isinstance(sig, Mapping):
        return any(str(v or "").strip() for v in sig.values())
    if isinstance(sig, list):
        return any(str(v or "").strip() for v in sig)
    return bool(str(sig or "").strip())


def _signature_equipment_refs(char: Mapping[str, Any], form: Mapping[str, Any]) -> List[str]:
    """Collect registered protagonist equipment ids from char/form fields."""
    refs: List[str] = []

    def collect(value: object) -> None:
        if value is None:
            return
        if isinstance(value, str):
            for token in re.split(r"[,，、/；;\s]+", value):
                token = token.strip()
                if token:
                    refs.append(token)
            return
        if isinstance(value, Mapping):
            for key in ("id", "asset_id", "weapon_id", "equipment_id", "primary", "ref"):
                item = value.get(key)
                if isinstance(item, str) and item.strip():
                    refs.append(item.strip())
            for key in ("ids", "assets", "weapons", "items"):
                collect(value.get(key))
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                collect(item)

    for source in (char, form):
        for key in SIGNATURE_EQUIPMENT_FIELDS:
            collect(source.get(key))
    out: List[str] = []
    seen = set()
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out


def _core_action_character_needs_equipment(char: Mapping[str, Any], form: Mapping[str, Any]) -> bool:
    """Production action leads should bind their recognisable weapon/prop kit."""
    if char.get("signature_equipment_expected") is True or form.get("signature_equipment_expected") is True:
        return True
    if char.get("combat_role") is True or form.get("combat_role") is True:
        return True
    if char.get("action_role") is True or form.get("action_role") is True:
        return True
    blob = json.dumps({"character": char, "form": form}, ensure_ascii=False).lower()
    core = _CORE_SCOPE_RE.search(f"{char.get('tier') or ''} {char.get('scope') or ''} {char.get('role') or ''} {char.get('name') or ''}")
    return bool(core and any(term.lower() in blob for term in ACTION_EQUIPMENT_TERMS))


def _validate_signature_equipment(char: Mapping[str, Any], form: Mapping[str, Any], floc: str) -> None:
    if not _core_action_character_needs_equipment(char, form):
        return
    refs = _signature_equipment_refs(char, form)
    if not refs:
        add(
            BLOCK,
            "主角装备库",
            f"{floc} signature_equipment",
            "production 核心动作角色缺 signature_equipment；请把主角常用武器/法宝/标志性道具登记为 "
            "WEAPON_xx/PROP_xx/VFX_xx，并在角色 form 上绑定，避免主角形象只锁脸不锁随身装备。",
            return_to_stage="image",
        )
        return
    invalid = [ref for ref in refs if not re.match(r"^(WEAPON|PROP|VFX|OUTFIT)_[A-Za-z0-9_:-]+$", ref)]
    if invalid:
        add(
            BLOCK,
            "主角装备库",
            f"{floc} signature_equipment",
            "signature_equipment 只能引用资产注册 ID（WEAPON_/PROP_/VFX_/OUTFIT_）："
            + ", ".join(invalid[:8]),
            return_to_stage="image",
        )


def _profile_has_any(section: Mapping[str, object], keys: Sequence[str]) -> bool:
    return any(not _field_is_missing(section, key) for key in keys)


def _validate_wardrobe_profile(section: object, loc: str, *, field_name: str = "wardrobe_profile",
                               required: bool = False) -> None:
    """Advisory validation for structured costume contracts.

    Missing profile remains warning-only for backward compatibility; once a
    profile is present, empty shells are surfaced so prompt/QC can rely on it.
    """
    if not isinstance(section, dict):
        sev = BLOCK if required else WARN
        add(sev, "服装契约", f"{loc} {field_name}",
            "缺少结构化服装契约；建议补 silhouette/layers/collar/sleeve/waist/hem/fabric/palette/forbidden_drift，"
            "否则只能靠自由文本锁服装。")
        return
    missing_core = [key for key in WARDROBE_PROFILE_CORE_FIELDS if _field_is_missing(section, key)]
    if missing_core:
        add(WARN, "服装契约", f"{loc} {field_name}",
            f"{field_name} 缺核心字段：" + ", ".join(missing_core))
    missing_structure = ["/".join(group) for group in WARDROBE_PROFILE_STRUCTURE_FIELD_GROUPS if not _profile_has_any(section, group)]
    if missing_structure:
        add(WARN, "服装契约", f"{loc} {field_name}",
            f"{field_name} 缺服装部件字段：" + ", ".join(missing_structure))


def _validate_character_asset_bundle(root: str, char: dict, loc: str) -> None:
    """Every image-entering character must have a portable project-local asset bundle."""
    bundle = char.get("asset_bundle")
    char_id = str(char.get("id") or "").strip()
    if not isinstance(bundle, dict):
        add(BLOCK, "角色资产包", loc,
            "人物角色缺 asset_bundle；所有入镜人物（含短线/功能角色）都必须指向 "
            "设定库/character_assets/<CHAR_ID>__<slug>/manifest.json。角色体量只影响 LoRA/原生主体是否升档，"
            "不影响基础定妆包完整度；否则换模型/工作流/视频工具时无法继承 reference/prompts/lora/voice/adapters/qc。")
        return
    manifest_rel = str(bundle.get("manifest") or "").strip()
    package_dir = str(bundle.get("package_dir") or "").strip()
    if not manifest_rel:
        add(BLOCK, "角色资产包", f"{loc} asset_bundle.manifest", "asset_bundle.manifest 缺失")
        return
    if not package_dir:
        add(BLOCK, "角色资产包", f"{loc} asset_bundle.package_dir", "asset_bundle.package_dir 缺失")
    sections = bundle.get("sections")
    if sections is not None:
        missing_sections = [s for s in ASSET_BUNDLE_REQUIRED_SECTIONS if s not in sections]
        if missing_sections:
            add(BLOCK, "角色资产包", f"{loc} asset_bundle.sections",
                "asset_bundle.sections 缺分区：" + ", ".join(missing_sections))
    manifest_path = manifest_rel if os.path.isabs(manifest_rel) else os.path.join(root, manifest_rel)
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        add(BLOCK, "角色资产包", manifest_path,
            "人物角色 asset_bundle.manifest 不存在或无法解析；资产包不能只写口头约定。")
        return
    if manifest.get("kind") != "n2d_project_character_asset_bundle":
        add(BLOCK, "角色资产包", manifest_path, "manifest.kind 必须是 n2d_project_character_asset_bundle")
    if char_id and str(manifest.get("character_id") or "").strip() != char_id:
        add(BLOCK, "角色资产包", manifest_path,
            f"manifest.character_id 必须等于 registry character id {char_id}")
    directories = manifest.get("directories")
    if not isinstance(directories, dict):
        add(BLOCK, "角色资产包", manifest_path,
            "manifest.directories 必须列出 reference/prompts/lora/voice/adapters/qc")
    else:
        for section in ASSET_BUNDLE_REQUIRED_SECTIONS:
            rel = str(directories.get(section) or "").strip()
            if not rel:
                add(BLOCK, "角色资产包", manifest_path, f"manifest.directories 缺 {section}")
                continue
            full = rel if os.path.isabs(rel) else os.path.join(root, rel)
            if not os.path.isdir(full):
                add(BLOCK, "角色资产包", full, f"角色资产包分区不存在：{section}")
    truth_sources = manifest.get("truth_sources")
    if not isinstance(truth_sources, dict) or not truth_sources.get("identity_registry"):
        add(BLOCK, "角色资产包", manifest_path,
            "manifest.truth_sources 必须指回 identity_registry；资产包不得成为第二真值。")


def _identity_reference_item_path(item: object) -> str:
    """Return a reference path from legacy string or structured dict form."""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("path") or "").strip()
    return ""


def _identity_reference_item_ready(item: object) -> bool:
    """A structured reference is usable only when it is explicitly ready."""
    path = _identity_reference_item_path(item)
    if not path:
        return False
    if isinstance(item, dict):
        return str(item.get("status") or "").strip() in READY_CHARACTER_MAKEUP_STATUSES
    return True


def _identity_reference_item_derivation(item: object) -> dict:
    if not isinstance(item, dict):
        return {}
    derivation = item.get("derivation")
    return derivation if isinstance(derivation, dict) else {}


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_same_source_makeup_derivation(
    root: str,
    item: object,
    key: str,
    floc: str,
    strict_references: bool,
    verify_source_hash: bool,
) -> None:
    """B7: split makeup refs must be derived from one approved source image."""
    if not strict_references or key not in DERIVED_CHARACTER_MAKEUP_REFERENCE_FIELDS:
        return
    if not _identity_reference_item_ready(item):
        return
    derivation = _identity_reference_item_derivation(item)
    missing = [field for field in CHARACTER_MAKEUP_DERIVATION_REQUIRED_FIELDS if not derivation.get(field)]
    method = str(derivation.get("method") or "").strip()
    allowed_methods = SAME_SOURCE_MAKEUP_DERIVATION_METHODS.get(key, set())
    if missing or method not in allowed_methods:
        add(BLOCK, "资产身份注册层", floc,
            f"{key} ready 拆分定妆必须是同源母本派生，登记 "
            "derivation.method/source_path/source_sha256/crop_box；"
            "45°/侧/背只能从人审通过 turnaround 拆，半身/脸部特写只能从已通过正面裁。"
            "禁止逐张文生图补角度导致脸漂。")
        return
    crop_box = derivation.get("crop_box")
    if not isinstance(crop_box, list) or len(crop_box) != 4:
        add(BLOCK, "资产身份注册层", floc,
            f"{key} 同源派生 crop_box 必须是四元数组；否则无法追溯它来自母本哪一块。")
        return
    source_rel = str(derivation.get("source_path") or "").strip()
    if verify_source_hash and source_rel:
        source_path = source_rel if os.path.isabs(source_rel) else os.path.join(root, source_rel)
        if not os.path.exists(source_path):
            add(BLOCK, "资产身份注册层", source_path,
                f"{key} 同源派生 source_path 不存在；ready 拆图来源不可验证。")
            return
        actual = _file_sha256(source_path)
        if actual != str(derivation.get("source_sha256") or "").strip():
            add(BLOCK, "资产身份注册层", source_path,
                f"{key} 同源派生 source_sha256 与当前母本不一致；母本变更后必须重新裁切派生。")


def _identity_expression_path(expr: object) -> str:
    """Return an expression reference path from legacy string or structured dict form."""
    return _identity_reference_item_path(expr)


def _identity_reference_list_paths(value: object) -> List[str]:
    if isinstance(value, list):
        return [_identity_reference_item_path(item) for item in value]
    return []


def _identity_ready_reference_list_paths(value: object) -> List[str]:
    """Atlas references are ready only when status=ready/registered or legacy string has a path."""
    out: List[str] = []
    if not isinstance(value, list):
        return out
    for item in value:
        if isinstance(item, str):
            p = item.strip()
            if p:
                out.append(p)
        elif isinstance(item, dict):
            p = str(item.get("path") or "").strip()
            if p and _identity_reference_item_ready(item):
                out.append(p)
    return out


def _validate_reference_atlas(
    root: str,
    form: dict,
    floc: str,
    strict_references: bool,
    verify_source_hash: bool,
    restricted_partial: bool = False,
) -> None:
    atlas = form.get("reference_atlas")
    if not isinstance(atlas, dict):
        if strict_references:
            add(BLOCK, "资产身份注册层", floc,
                "reference_atlas 必须是对象；所有人物/形态都要登记基础视角、表情参考和动作缺口状态。")
        return
    if restricted_partial:
        if str(atlas.get("build_tier") or "").strip() != "restricted_partial" and strict_references:
            add(BLOCK, "资产身份注册层", floc,
                "restricted_partial 形态的 reference_atlas.build_tier 必须标为 restricted_partial，避免误当完整人物参考。")
        return
    base_views = atlas.get("base_views")
    if not isinstance(base_views, dict):
        if strict_references:
            add(BLOCK, "资产身份注册层", floc,
                "reference_atlas.base_views 缺失；必须登记 front/three_quarter/side/back/half_body 或 full_body 的 ready 状态。")
    else:
        missing_views = [key for key in REQUIRED_CHARACTER_MAKEUP_ATLAS_VIEWS if key not in base_views]
        if "half_body" not in base_views and "full_body" not in base_views:
            missing_views.append("half_body_or_full_body")
        if missing_views and strict_references:
            add(BLOCK, "资产身份注册层", floc,
                "reference_atlas.base_views 缺基础视角：" + ", ".join(missing_views))
        if strict_references:
            not_ready: List[str] = []
            required_view_keys = [key for key in REQUIRED_CHARACTER_MAKEUP_ATLAS_VIEWS if key in base_views]
            required_view_keys.append("half_body" if "half_body" in base_views else "full_body")
            for key in required_view_keys:
                item = base_views.get(key)
                if not _identity_reference_item_ready(item):
                    not_ready.append(key)
                else:
                    _validate_same_source_makeup_derivation(
                        root, item, key, floc, strict_references, verify_source_hash
                    )
            if not_ready:
                add(BLOCK, "资产身份注册层", floc,
                    "reference_atlas.base_views 基础视角必须为 ready 且有路径："
                    + ", ".join(not_ready)
                    + "；所有人物/形态都强制包含 45°/three_quarter 与脸部特写基础锚，不能登记为 planned 后放行。")
    face_anchor_refs = atlas.get("face_anchor_refs")
    expression_refs = atlas.get("expression_refs")
    has_face_anchor_refs = bool(_identity_ready_reference_list_paths(face_anchor_refs))
    has_expression_refs = bool(_identity_ready_reference_list_paths(expression_refs))
    if not has_face_anchor_refs and not has_expression_refs:
        if strict_references:
            add(BLOCK, "资产身份注册层", floc,
                "reference_atlas 至少登记一个 ready 的同源脸部特写/表情参考（face_anchor_refs 或 expression_refs）；"
                "功能角色也不能只靠正脸硬扛近景，planned 脸锚不能放行。")
    if isinstance(face_anchor_refs, list):
        for face_ref in face_anchor_refs:
            _validate_same_source_makeup_derivation(
                root, face_ref, "face_anchor_refs", floc, strict_references, verify_source_hash
            )


def _identity_reference_exists(root: str, rel: str) -> bool:
    full = rel if os.path.isabs(rel) else os.path.join(root, rel)
    return os.path.exists(full)


def _identity_reference_matches_asset_key(asset_key: str, rel: str) -> bool:
    """Registry references must advertise the exact character form they lock."""
    key = str(asset_key or "").strip()
    if not key:
        return True
    stem = os.path.splitext(os.path.basename(str(rel or "").strip()))[0]
    return key in stem


def check_identity_registry(
    root: str,
    require_reference_assets: bool = False,
    required_character_ids: Optional[set] = None,
) -> None:
    """Validate the role identity registry shared by image/video/review stages."""
    p = identity_registry_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "资产身份注册层", p, "缺少或无法解析 identity_registry.json；共享定妆必须升级为角色身份注册层")
        return
    if data.get("kind") not in (None, IDENTITY_REGISTRY_KIND, "n2d_asset_identity_registry"):
        add(BLOCK, "资产身份注册层", p, f"kind 必须是 {IDENTITY_REGISTRY_KIND}")
    chars = data.get("characters")
    if not isinstance(chars, list) or not chars:
        add(BLOCK, "资产身份注册层", p, "characters[] 缺失或为空；明确角色/形态必须登记")
        return

    seen_ids = set()
    for ci, char in enumerate(chars, 1):
        loc = f"{p} character#{ci}"
        if not isinstance(char, dict):
            add(BLOCK, "资产身份注册层", loc, "character 必须是对象")
            continue
        for key in ("id", "name", "scope", "forms"):
            if _field_is_missing(char, key):
                add(BLOCK, "资产身份注册层", loc, f"character 缺字段：{key}")
        char_id = str(char.get("id", "")).strip()
        if char_id:
            if char_id in seen_ids:
                add(BLOCK, "资产身份注册层", loc, f"重复 character id：{char_id}")
            seen_ids.add(char_id)

        _validate_character_asset_bundle(root, char, loc)

        strict_references = required_character_ids is None or char_id in required_character_ids

        forms = char.get("forms")
        if not isinstance(forms, list) or not forms:
            add(BLOCK, "资产身份注册层", loc, "forms[] 缺失或为空；常态/变体必须分别登记")
            continue
        form_count = len(forms)
        for fi, form in enumerate(forms, 1):
            floc = f"{loc} form#{fi}"
            if not isinstance(form, dict):
                add(BLOCK, "资产身份注册层", floc, "form 必须是对象")
                continue
            for key in IDENTITY_FORM_FIELDS:
                if _field_is_missing(form, key):
                    add(BLOCK, "资产身份注册层", floc, f"form 缺字段：{key}")

            _validate_character_dna(form.get("character_dna"), floc)
            if (
                consistency_release_profile(root) == "production"
                and _CORE_SCOPE_RE.search(f"{char.get('tier') or ''} {char.get('scope') or ''}")
                and not _performance_signature_present(char, form)
            ):
                add(
                    BLOCK,
                    "角色表演一致性",
                    f"{floc} performance_signature",
                    "production 核心/长线角色缺 performance_signature；请登记微表情、惯用动作、站姿、说话节奏、眼神反应等表演指纹，"
                    "否则脸像一致但角色表演会跨集漂。",
                    return_to_stage="image",
                )
            if consistency_release_profile(root) == "production":
                _validate_signature_equipment(char, form, floc)
            if "wardrobe_profile" in form:
                _validate_wardrobe_profile(form.get("wardrobe_profile"), floc)

            reference_group = form.get("reference_group")
            restricted_partial = _is_restricted_partial_form(char, form)
            _validate_reference_atlas(
                root,
                form,
                floc,
                strict_references,
                require_reference_assets,
                restricted_partial=restricted_partial,
            )
            if not isinstance(reference_group, dict):
                add(BLOCK, "资产身份注册层", floc, "reference_group 必须是对象")
            else:
                asset_key = str(form.get("asset_key") or "").strip()
                form_name = str(form.get("form") or "").strip()
                # Legacy single-form baseline characters may use `定妆_<角色>.png`.
                # Multi-form or named variant forms must advertise the exact asset_key.
                enforce_asset_key_filename = form_count > 1 or form_name not in {"常态", "局部参考", "局部参考（暂不正脸）"}
                if restricted_partial:
                    partial_keys = ("hand", "silhouette")
                    if strict_references and not any(not _field_is_missing(reference_group, key) for key in partial_keys):
                        add(BLOCK, "资产身份注册层", floc, "restricted_partial reference_group 至少需要 hand 或 silhouette 局部参考路径")
                    for key in partial_keys:
                        if _field_is_missing(reference_group, key):
                            continue
                        rel = str(reference_group.get(key, "")).strip()
                        if require_reference_assets and strict_references and not _identity_reference_exists(root, rel):
                            add(BLOCK, "资产身份注册层", os.path.join(root, rel) if not os.path.isabs(rel) else rel, f"reference_group.{key} 路径不存在")
                else:
                    for key in REQUIRED_CHARACTER_MAKEUP_REFERENCE_GROUP_FIELDS:
                        if _field_is_missing(reference_group, key):
                            if strict_references:
                                add(BLOCK, "资产身份注册层", floc, f"reference_group 缺核心路径：{key}")
                            continue
                        item = reference_group.get(key)
                        rel = _identity_reference_item_path(item)
                        if strict_references and not _identity_reference_item_ready(item):
                            add(BLOCK, "资产身份注册层", floc,
                                f"reference_group.{key} 必须为 ready 且有路径；planned/空路径只能表示待补，不能放行。"
                                "三视图人审拼版不能替代正/45°/侧/背等拆分参考。")
                            continue
                        if asset_key and enforce_asset_key_filename and not _identity_reference_matches_asset_key(asset_key, rel):
                            add(BLOCK, "资产身份注册层", floc,
                                f"reference_group.{key} 路径 `{rel}` 未包含 asset_key={asset_key}；"
                                "服饰/形态变体必须独立定妆，禁止复用其它服饰形态参考")
                        if require_reference_assets and strict_references and not _identity_reference_exists(root, rel):
                            add(BLOCK, "资产身份注册层", os.path.join(root, rel) if not os.path.isabs(rel) else rel, f"reference_group.{key} 路径不存在")
                        _validate_same_source_makeup_derivation(
                            root, item, key, floc, strict_references, require_reference_assets
                        )
                    body_keys = [key for key in CHARACTER_MAKEUP_BODY_REFERENCE_FIELDS if not _field_is_missing(reference_group, key)]
                    if not body_keys:
                        if strict_references:
                            add(BLOCK, "资产身份注册层", floc,
                                "reference_group 缺核心路径：half_body_or_full_body；基础定妆包必须有半身或全身服装参考。")
                    else:
                        body_key = body_keys[0]
                        body_item = reference_group.get(body_key)
                        body_rel = _identity_reference_item_path(body_item)
                        if strict_references and not _identity_reference_item_ready(body_item):
                            add(BLOCK, "资产身份注册层", floc,
                                f"reference_group.{body_key} 必须为 ready 且有路径；planned 服装参考不能放行。")
                        elif asset_key and enforce_asset_key_filename and not _identity_reference_matches_asset_key(asset_key, body_rel):
                            add(BLOCK, "资产身份注册层", floc,
                                f"reference_group.{body_key} 路径 `{body_rel}` 未包含 asset_key={asset_key}；"
                                "服饰/形态变体必须独立定妆，禁止复用其它服饰形态参考")
                        elif require_reference_assets and strict_references and not _identity_reference_exists(root, body_rel):
                            add(BLOCK, "资产身份注册层", os.path.join(root, body_rel) if not os.path.isabs(body_rel) else body_rel, f"reference_group.{body_key} 路径不存在")
                        _validate_same_source_makeup_derivation(
                            root, body_item, body_key, floc, strict_references, require_reference_assets
                        )
                face_anchor_refs = reference_group.get("face_anchor_refs", [])
                expressions = reference_group.get("expressions", [])
                if face_anchor_refs is not None and not isinstance(face_anchor_refs, list):
                    add(BLOCK, "资产身份注册层", floc, "reference_group.face_anchor_refs 必须是列表")
                    face_anchor_refs = []
                if expressions is not None and not isinstance(expressions, list):
                    add(BLOCK, "资产身份注册层", floc, "reference_group.expressions 必须是列表")
                    expressions = []
                face_anchor_paths = [p for p in _identity_ready_reference_list_paths(face_anchor_refs) if p]
                expression_paths = [p for p in _identity_ready_reference_list_paths(expressions) if p]
                if not restricted_partial and strict_references and not (face_anchor_paths or expression_paths):
                    add(BLOCK, "资产身份注册层", floc,
                        "reference_group 至少需要一个同源脸部特写/表情参考：优先写 face_anchor_refs，"
                        "也兼容 expressions；所有人物（含短线/功能角色）都按主角基础定妆包标准执行。")
                for face_ref in face_anchor_refs or []:
                    rel = _identity_reference_item_path(face_ref)
                    if not rel:
                        add(BLOCK, "资产身份注册层", floc,
                            "reference_group.face_anchor_refs 存在空路径；可用字符串路径或 {label/emotion, path} 对象")
                        continue
                    if strict_references and not _identity_reference_item_ready(face_ref):
                        add(BLOCK, "资产身份注册层", floc,
                            "reference_group.face_anchor_refs 必须为 ready 且有路径；planned 脸部特写不能放行。")
                    if require_reference_assets and strict_references and not _identity_reference_exists(root, rel):
                        add(BLOCK, "资产身份注册层", os.path.join(root, rel) if not os.path.isabs(rel) else rel, "reference_group.face_anchor_refs 路径不存在")
                    if asset_key and asset_key not in os.path.basename(rel):
                        add(BLOCK, "资产身份注册层", floc, f"reference_group.face_anchor_refs 跨角色/形态污染：{rel} 不属于 asset_key={asset_key}")
                    _validate_same_source_makeup_derivation(
                        root, face_ref, "face_anchor_refs", floc, strict_references, require_reference_assets
                    )
                for expr in expressions or []:
                    rel = _identity_expression_path(expr)
                    if not rel:
                        add(BLOCK, "资产身份注册层", floc,
                            "reference_group.expressions 存在空路径；可用字符串路径或 {emotion, path} 对象")
                        continue
                    if strict_references and not _identity_reference_item_ready(expr):
                        add(BLOCK, "资产身份注册层", floc,
                            "reference_group.expressions 必须为 ready 且有路径；planned 表情/脸锚不能放行。")
                    if require_reference_assets and strict_references and not _identity_reference_exists(root, rel):
                        add(BLOCK, "资产身份注册层", os.path.join(root, rel) if not os.path.isabs(rel) else rel, "reference_group.expressions 路径不存在")
                    if asset_key and asset_key not in os.path.basename(rel):
                        add(BLOCK, "资产身份注册层", floc, f"reference_group.expressions 跨角色/形态污染：{rel} 不属于 asset_key={asset_key}")

            adapters = form.get("identity_adapters")
            if not isinstance(adapters, dict):
                add(BLOCK, "资产身份注册层", floc, "identity_adapters 必须是对象")
            else:
                for section in IDENTITY_ADAPTER_SECTIONS:
                    _validate_identity_adapter_map(adapters.get(section), floc, section)
                _validate_identity_lora(adapters.get("lora"), floc, root)

            _validate_generation_control(form.get("generation_control"), floc)

            angle_policy = form.get("angle_policy")
            if not isinstance(angle_policy, dict):
                add(BLOCK, "资产身份注册层", floc, "angle_policy 必须是对象")
            else:
                for key in IDENTITY_ANGLE_FIELDS:
                    if _field_is_missing(angle_policy, key):
                        add(BLOCK, "资产身份注册层", floc, f"angle_policy 缺字段：{key}")

            drift_forbidden = form.get("drift_forbidden")
            if not isinstance(drift_forbidden, list) or not drift_forbidden:
                add(BLOCK, "资产身份注册层", floc, "drift_forbidden 必须是非空列表")


_COSTUME_VARIANT_RE = re.compile(r"_(45度|三分之二|侧|侧面|半身|全身|背|背面|脸部特写|三视图|设定表|表情(?:_.+)?)$")
_COSTUME_NON_FACE = ("三视图", "设定表")  # 人审拼版，非脸度量基准；脸部特写/表情仍是可喂图参考


def _costume_stem(basename: str) -> str:
    s = basename[:-4] if basename.endswith(".png") else basename
    return _COSTUME_VARIANT_RE.sub("", s)


def check_costume_registry_reconcile(root: str) -> None:
    """定妆库 ↔ identity_registry 双向对账。

    face 机检按文件名 glob 发现定妆图、identity_registry 按登记的 reference_group 路径锁脸——两套各写各的，
    若 registry 登记 `定妆_X_人皮态.png` 但磁盘只有 `定妆_X.png`，崩脸机检可能测的根本不是 registry 锁的那张。
    本检查对账：① registry 登记但磁盘缺的参考；② 属于已登记角色、磁盘有却没进任何 reference_group 的定妆变体（orphan）。
    场景定妆（不属任何角色）天然不匹配角色 stem，不误报。
    """
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return  # 缺 registry：check_identity_registry 已把关
    registered_rel: set = set()
    for char in reg.get("characters") or []:
        for form in (char.get("forms") or []):
            rg = form.get("reference_group")
            if not isinstance(rg, dict):
                continue
            for val in rg.values():
                for v in (val if isinstance(val, list) else [val]):
                    rel = _identity_reference_item_path(v)
                    if rel:
                        registered_rel.add(rel)
    if not registered_rel:
        return
    registered_base = {os.path.basename(p) for p in registered_rel}
    char_stems = {_costume_stem(b) for b in registered_base}
    # ① registry 登记但磁盘缺（三视图/设定表/表情 不强求落盘）
    for rel in sorted(registered_rel):
        bn = os.path.basename(rel)
        if any(t in bn for t in _COSTUME_NON_FACE):
            continue
        if not os.path.isfile(os.path.join(root, rel)):
            add(WARN, "定妆对账", rel,
                f"identity_registry 登记的定妆参考 {rel} 磁盘缺失；补出该图或修 registry 路径，否则锁脸参考落空")
    # ② 已登记角色的 orphan 变体：磁盘有、属同一角色 stem、却没进 reference_group
    for p in sorted(glob.glob(os.path.join(shared_asset_path(root, "图片"), "定妆_*.png"))):
        bn = os.path.basename(p)
        if any(t in bn for t in _COSTUME_NON_FACE):
            continue
        if bn in registered_base:
            continue
        # 属已登记角色 = 文件名等于某角色 stem，或是其变体（stem_ 前缀）——任意变体后缀都能抓到
        if any(bn == stem + ".png" or bn.startswith(stem + "_") for stem in char_stems):
            add(WARN, "定妆对账", p,
                f"定妆图 {bn} 属已登记角色但未进 identity_registry 任何 reference_group；"
                f"face 机检会按文件名把它当参考、与 registry 锁的不是同一套 → 登记进 registry 或删除")


def _validate_scene_dna(asset: dict, loc: str) -> None:
    scene_dna = asset.get("scene_dna")
    if not isinstance(scene_dna, dict):
        add(BLOCK, "场景 DNA", loc,
            "反复场景缺 scene_dna；必须锁归属锚、地标/识别物、空间布局、建筑材质/主色、光色天气、常驻物件、禁漂项。")
        return
    for key in SCENE_DNA_REQUIRED_FIELDS:
        value = scene_dna.get(key)
        if isinstance(value, list):
            if not any(str(v).strip() for v in value):
                add(BLOCK, "场景 DNA", f"{loc} scene_dna.{key}", "scene_dna 字段必须是非空列表")
        elif not isinstance(value, str) or not value.strip():
            add(BLOCK, "场景 DNA", f"{loc} scene_dna.{key}", "scene_dna 字段必须非空")


def _flatten_asset_terms(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [p.strip() for p in re.split(r"[,，、/；;\n]+", value) if p.strip()]
    if isinstance(value, dict):
        out: List[str] = []
        for v in value.values():
            out.extend(_flatten_asset_terms(v))
        return out
    if isinstance(value, (list, tuple, set)):
        out = []
        for v in value:
            out.extend(_flatten_asset_terms(v))
        return out
    text = str(value).strip()
    return [text] if text else []


def _asset_must_not_have_terms(asset: Mapping[str, object]) -> List[str]:
    constraints = asset.get("constraints") if isinstance(asset.get("constraints"), dict) else {}
    terms: List[str] = []
    for key in ("must_not_have", "forbidden_parts", "negative_structure", "negative"):
        terms.extend(_flatten_asset_terms(asset.get(key)))
        if isinstance(constraints, dict):
            terms.extend(_flatten_asset_terms(constraints.get(key)))
    out: List[str] = []
    seen = set()
    for term in terms:
        t = str(term).strip(" `。，；;、")
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _validate_scene_atlas(asset: dict, loc: str) -> None:
    """G-I2：核心/高频 LOC 的场景多机位锁（场景四视图）。production 档对核心 LOC 强制，

    与角色 reference_atlas.base_views 同构：要求 scene_atlas.base_views 至少 front + 一个反打/侧机位
    (back/left/right) ready 板，锁住反打同一空间时的门窗/纵深/陈设，防 AI 在反打镜里随机增减结构。
    确实只从单一机位拍的场景显式标 scene_atlas.single_angle=true 豁免。dim 独立，不与「空间/场面调度一致性」混。
    """
    atlas = asset.get("scene_atlas")
    if not isinstance(atlas, dict):
        add(BLOCK, "场景多机位锁(G-I2)", loc,
            "production 核心/高频 LOC 缺 scene_atlas（场景多机位锁）：补 base_views 的 front + 至少一个反打/侧机位"
            "(back/left/right) ready 板，防镜头反打同一空间时门窗/纵深/陈设漂移；只从单一机位拍则显式标 "
            "scene_atlas.single_angle=true。", return_to_stage="image")
        return
    if atlas.get("single_angle") is True:
        return
    base_views = atlas.get("base_views")
    if not isinstance(base_views, dict):
        add(BLOCK, "场景多机位锁(G-I2)", loc,
            "scene_atlas.base_views 必须是对象，登记 front + 反打/侧机位(back/left/right)的 ready 状态。",
            return_to_stage="image")
        return
    front_ready = _identity_reference_item_ready(base_views.get("front"))
    alts = [k for k in SCENE_ATLAS_ALT_ANGLES if _identity_reference_item_ready(base_views.get(k))]
    if not front_ready or not alts:
        add(BLOCK, "场景多机位锁(G-I2)", loc,
            "scene_atlas.base_views 需 front + 至少一个反打/侧机位(back/left/right) ready：当前 front="
            + ("ready" if front_ready else "缺") + "、备选机位=" + ("、".join(alts) or "无")
            + "；补多机位板锁住反打空间，或显式标 single_angle=true。", return_to_stage="image")


def _is_core_location_asset(asset: Mapping[str, object]) -> bool:
    blob = json.dumps(asset, ensure_ascii=False).lower()
    if asset.get("core") is True or asset.get("recurrent") is True or asset.get("persistent") is True:
        return True
    try:
        if int(asset.get("frequency") or asset.get("reuse_count") or 0) >= 3:
            return True
    except (TypeError, ValueError):
        pass
    return any(token in blob for token in ("主场景", "核心场景", "高频", "反复", "复用", "recurrent", "core", "main_location"))


def _asset_has_any(asset: Mapping[str, object], aliases: Sequence[str]) -> bool:
    if any(alias in asset and not _field_is_missing(dict(asset), alias) for alias in aliases):
        return True
    constraints = asset.get("constraints") if isinstance(asset.get("constraints"), Mapping) else {}
    scene_dna = asset.get("scene_dna") if isinstance(asset.get("scene_dna"), Mapping) else {}
    for section in (constraints, scene_dna):
        if any(alias in section and str(section.get(alias) or "").strip() for alias in aliases):
            return True
    blob = json.dumps(asset, ensure_ascii=False).lower()
    return any(alias.lower() in blob for alias in aliases)


def _weapon_profile(asset: Mapping[str, object]) -> Tuple[Mapping[str, object], str]:
    for field in ASSET_WEAPON_PROFILE_NAMES:
        value = asset.get(field)
        if isinstance(value, Mapping):
            return value, field
    return {}, ASSET_WEAPON_PROFILE_NAMES[0]


def _is_weapon_like_asset(asset: Mapping[str, object]) -> bool:
    asset_type = str(asset.get("type") or "").strip().lower()
    if asset_type in ASSET_WEAPON_TYPES:
        return True
    if str(asset.get("id") or "").strip().startswith("WEAPON_"):
        return True
    blob = json.dumps(asset, ensure_ascii=False).lower()
    return any(term.lower() in blob for term in WEAPON_LIKE_ASSET_TERMS)


def _asset_owner_present(asset: Mapping[str, object], profile: Mapping[str, object]) -> bool:
    owner_fields = ("owner", "character_id", "owner_character_id", "bound_character", "signature_owner")
    return any(
        str(asset.get(key) or profile.get(key) or "").strip()
        for key in owner_fields
    )


def _validate_weapon_profile(asset: Mapping[str, object], loc: str, *, required: bool = True) -> None:
    profile, field_name = _weapon_profile(asset)
    if not isinstance(profile, Mapping) or not profile:
        sev = BLOCK if required else WARN
        add(
            sev,
            "主角装备库",
            f"{loc} {field_name}",
            "武器/法宝实体缺结构化 weapon_profile；请锁设计意图、剪影、尺度、材质、色卡、纹样母题、携带方式、"
            "战斗用法、VFX 签名和禁漂项，避免每镜重画成不同武器。",
            return_to_stage="image",
        )
        return
    missing = [key for key in ASSET_WEAPON_PROFILE_FIELDS if _field_is_missing(dict(profile), key)]
    if missing:
        add(
            BLOCK if required else WARN,
            "主角装备库",
            f"{loc} {field_name}",
            f"{field_name} 缺字段：" + ", ".join(missing) +
            "；主角武器要像角色定妆一样能被索引和复现。",
            return_to_stage="image",
        )
    if not _asset_owner_present(asset, profile):
        add(
            BLOCK if required else WARN,
            "主角装备库",
            f"{loc} {field_name}",
            "武器/法宝资产缺 owner/character_id；请声明归属角色，方便出图时把主角与专属装备绑定。",
            return_to_stage="image",
        )
    reference_group = asset.get("reference_group") if isinstance(asset.get("reference_group"), Mapping) else {}
    view_keys = ("in_hand", "wield", "wielding", "scale_ref", "scale_reference", "sheathed", "active")
    if isinstance(reference_group, Mapping) and not any(str(reference_group.get(key) or "").strip() for key in view_keys):
        add(
            WARN,
            "主角装备库",
            loc,
            "建议为 WEAPON_ 增加握持/比例参考（in_hand、wielding、scale_reference 或 sheathed），"
            "否则主角图容易出现武器尺寸和手持方式漂移。",
        )


def check_asset_reference_registry(
    root: str,
    require_reference_assets: bool = False,
    required_asset_ids: Optional[set] = None,
) -> None:
    """Validate reusable non-character scene/prop/outfit/vfx asset registry."""
    p = asset_registry_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "资产引用注册层", p, "缺少或无法解析 asset_registry.json；关键场景/道具/武器/服装/VFX 必须升级为 LOC_/PROP_/WEAPON_/OUTFIT_/VFX_ 资产引用注册层")
        return
    if data.get("kind") != ASSET_REFERENCE_REGISTRY_KIND:
        add(BLOCK, "资产引用注册层", p, f"kind 必须是 {ASSET_REFERENCE_REGISTRY_KIND}")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        add(BLOCK, "资产引用注册层", p, "assets[] 缺失或为空；关键场景/道具/武器/服装/VFX 必须登记")
        return

    seen_ids = set()
    for idx, asset in enumerate(assets, 1):
        loc = f"{p} asset#{idx}"
        if not isinstance(asset, dict):
            add(BLOCK, "资产引用注册层", loc, "asset 必须是对象")
            continue
        for key in ASSET_REFERENCE_REQUIRED_FIELDS:
            if _field_is_missing(asset, key):
                add(BLOCK, "资产引用注册层", loc, f"asset 缺字段：{key}")

        asset_id = str(asset.get("id", "")).strip()
        asset_type = str(asset.get("type", "")).strip().lower()
        strict_references = required_asset_ids is None or asset_id in required_asset_ids
        if asset_id:
            if asset_id in seen_ids:
                add(BLOCK, "资产引用注册层", loc, f"重复 asset id：{asset_id}")
            seen_ids.add(asset_id)
        expected_prefix = ASSET_REFERENCE_TYPE_PREFIX.get(asset_type)
        if asset_type and not expected_prefix:
            add(BLOCK, "资产引用注册层", loc, f"未知 type「{asset_type}」；允许：{', '.join(sorted(ASSET_REFERENCE_TYPE_PREFIX))}")
        elif expected_prefix and asset_id and not asset_id.startswith(expected_prefix):
            add(BLOCK, "资产引用注册层", loc, f"type={asset_type} 的 id 必须以 {expected_prefix} 开头")

        if asset_type in {"outfit", "costume"}:
            _validate_wardrobe_profile(asset.get("outfit_profile"), loc, field_name="outfit_profile")

        if asset_type in ASSET_WEAPON_TYPES:
            _validate_weapon_profile(asset, loc, required=True)
        elif asset_type == "prop" and _is_weapon_like_asset(asset):
            _validate_weapon_profile(
                asset,
                loc,
                required=consistency_release_profile(root) == "production",
            )
        elif asset_type in {"vfx", "effect"} and _is_weapon_like_asset(asset):
            profile, _profile_name = _weapon_profile(asset)
            if profile:
                _validate_weapon_profile(asset, loc, required=False)
            else:
                add(
                    WARN,
                    "主角装备库",
                    loc,
                    "该 VFX/法术资产看起来承担武器/法宝识别功能；若它是实体武器或主角本命法宝，请拆成 "
                    "WEAPON_xx 实体资产 + VFX_xx 光效表现，并在角色 signature_equipment 中绑定。",
                )

        # 深度一致性检查：道具生命周期与所有权
        if asset_type == "prop":
            for key in ASSET_PROP_REQUIRED_FIELDS:
                if _field_is_missing(asset, key):
                    add(BLOCK, "资产引用注册层", loc, f"关键道具资产缺生命周期字段：{key}")

        # 深度一致性检查：场景空间布局
        if asset_type in ("scene", "location"):
            for key in ASSET_SCENE_REQUIRED_FIELDS:
                if _field_is_missing(asset, key):
                    add(BLOCK, "资产引用注册层", loc, f"反复场景资产缺空间布局字段：{key}")
            _validate_scene_dna(asset, loc)
            if consistency_release_profile(root) == "production" and _is_core_location_asset(asset):
                missing = [aliases[0] for aliases in ASSET_SCENE_RELEASE_FIELD_GROUPS if not _asset_has_any(asset, aliases)]
                if missing:
                    add(
                        BLOCK,
                        "空间/场面调度一致性",
                        loc,
                        "production 核心/高频 LOC 缺空间发布字段：" + ", ".join(missing) +
                        "；请补平面图、门窗方向、轴线规则和左右站位/screen_direction 规则，避免多集同场景门窗/站位/越轴漂移。",
                        return_to_stage="script_stage2",
                    )
                _validate_scene_atlas(asset, loc)

        reference_group = asset.get("reference_group")
        if not isinstance(reference_group, dict):
            add(BLOCK, "资产引用注册层", loc, "reference_group 必须是对象，至少含 primary")
        else:
            primary = str(reference_group.get("primary", "")).strip()
            if not primary:
                add(BLOCK, "资产引用注册层", loc, "reference_group.primary 缺失或为空")
            elif require_reference_assets and strict_references and not _identity_reference_exists(root, primary):
                add(BLOCK, "资产引用注册层", os.path.join(root, primary) if not os.path.isabs(primary) else primary, "reference_group.primary 路径不存在")
            alternates = reference_group.get("alternates", [])
            if alternates is not None and not isinstance(alternates, list):
                add(BLOCK, "资产引用注册层", loc, "reference_group.alternates 必须是列表")
            for rel in alternates or []:
                rel_s = str(rel or "").strip()
                if not rel_s:
                    add(BLOCK, "资产引用注册层", loc, "reference_group.alternates 存在空路径")
                elif require_reference_assets and strict_references and not _identity_reference_exists(root, rel_s):
                    add(BLOCK, "资产引用注册层", os.path.join(root, rel_s) if not os.path.isabs(rel_s) else rel_s, "reference_group.alternates 路径不存在")

        constraints = asset.get("constraints")
        if not isinstance(constraints, dict) or not constraints:
            add(BLOCK, "资产引用注册层", loc, "constraints 必须是非空对象；不能只登记名字 and 图片")
        else:
            if asset_type in {"scene", "location"}:
                if not any(k in constraints for k in ("layout", "axis", "light_anchor", "structure")):
                    add(BLOCK, "资产引用注册层", loc, "场景资产 constraints 必须锁 layout/axis/light_anchor/structure 至少一项")
                if "lighting_signature" not in constraints:
                    add(WARN, "资产引用注册层", loc, "建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变")

            if asset_type in {"prop", *ASSET_WEAPON_TYPES} and "structure" not in constraints:
                add(BLOCK, "资产引用注册层", loc, "道具/武器资产 constraints 必须锁 structure，避免壶嘴/刀刃/剑柄/剑鞘/镜面等部件幻觉")
            name_blob = f"{asset.get('name', '')}\n{json.dumps(constraints, ensure_ascii=False)}"
            if asset_type == "prop" and _has_any(name_blob, ("铜镜", "赐死", "托盘", "毒酒", "碎瓷", "匕首", "白绫")) and not _has_any(name_blob, (
                "单镜面", "唯一", "数量", "件数", "短颈圆口", "无侧嘴", "无斜嘴", "无双口", "一柄一刃", "同一只",
            )):
                add(BLOCK, "资产引用注册层", loc, "关键道具 constraints 未写结构唯一性；铜镜/托盘/毒酒/碎瓷必须锁数量与部件")
            must_not_terms = _asset_must_not_have_terms(asset)
            if asset_type == "prop" and _has_any(name_blob, ("毒酒", "酒瓶", "瓷瓶", "药瓶", "瓶", "酒盏", "赐死")):
                no_spout_terms = ("壶嘴", "侧嘴", "斜嘴", "喷口", "茶壶嘴", "出水口", "嘴")
                if not any(term in must_not_terms for term in no_spout_terms):
                    add(
                        BLOCK,
                        "资产引用注册层",
                        loc,
                        "瓶/酒/药类关键道具必须在 constraints.must_not_have（或 asset.must_not_have）登记"
                        "壶嘴/侧嘴/喷口/出水口等禁形，避免把酒瓶生成茶壶嘴。",
                    )
            if "must_not_have" in constraints or "must_not_have" in asset:
                if not must_not_terms:
                    add(BLOCK, "资产引用注册层", loc, "must_not_have 必须是非空字符串/列表，不能留空")

        drift_forbidden = asset.get("drift_forbidden")
        if not isinstance(drift_forbidden, list) or not drift_forbidden:
            add(BLOCK, "资产引用注册层", loc, "drift_forbidden 必须是非空列表")


# ── 景别阶梯机检（契约只校验「景别阶梯」字段存在；这里补对实际镜序列的机检）───────────────
# 长词优先（大远景 before 远景、中近景 before 中景、ECU/MCU before CU/MS），英文带词界防 CU 命中 MCU/ECU。
_SHOT_SCALE_MAP = sorted([
    ("大特写", "ECU"), ("极特写", "ECU"), ("ECU", "ECU"),
    ("特写", "CU"), ("CU", "CU"),
    ("中近景", "MCU"), ("中近", "MCU"), ("MCU", "MCU"),
    ("中景", "MS"), ("MS", "MS"),
    ("大远景", "ELS"), ("极远景", "ELS"), ("ELS", "ELS"),
    ("全景", "LS"), ("远景", "LS"), ("LS", "LS"),
], key=lambda kv: -len(kv[0]))
_OTS_RE = re.compile(r"反打|过肩|正反打|OTS|over[\s-]?shoulder", re.I)
SHOT_SCALE_MIN_RUN = 3  # 连续 >=N 镜同景别且非反打 → 景别阶梯单调告警


def shot_scale_class(text: str) -> Optional[str]:
    """从 lens/景别 串抽景别分级 ECU/CU/MCU/MS/LS/ELS。抽不到→None。纯函数·可测。"""
    raw = str(text or "")
    up = raw.upper()
    for tok, cls in _SHOT_SCALE_MAP:
        if tok.isascii():
            if re.search(rf"(?<![A-Z]){re.escape(tok.upper())}(?![A-Z])", up):
                return cls
        elif tok in raw:
            return cls
    return None


def monotonous_scale_runs(classes: Sequence[Optional[str]],
                          min_run: int = SHOT_SCALE_MIN_RUN) -> List[Tuple[int, int, str, int]]:
    """连续 >=min_run 个相同景别分级的区间 [(start_i, end_i, cls, length)]；None 打断连续。纯函数·可测。"""
    runs: List[Tuple[int, int, str, int]] = []
    i, n = 0, len(classes)
    while i < n:
        c = classes[i]
        if c is None:
            i += 1
            continue
        j = i
        while j + 1 < n and classes[j + 1] == c:
            j += 1
        if j - i + 1 >= min_run:
            runs.append((i, j, c, j - i + 1))
        i = j + 1
    return runs


def check_shot_scale_progression(root: str, ep: str) -> None:
    """景别阶梯机检：契约只校验「景别阶梯」字段存在（check_image_prompt_overview）；这里补对**实际镜序列**的机检——
    连续 >=3 镜同景别、且段内无反打/过肩（对白正反打是合法交替变化，豁免）= 景别阶梯单调、缺远近/机位变化 → warn。
    文本匹配较模糊（景别藏在 lens 串里），故 warn 不 block。"""
    sb = load_json(storyboard_path(root, ep))
    if not isinstance(sb, dict):
        return  # storyboard 缺失由 check_storyboard_contract 负责 BLOCK，这里不重复
    clips = sb.get("clips") or sb.get("shots") or []
    if not isinstance(clips, list) or len(clips) < SHOT_SCALE_MIN_RUN:
        return
    classes: List[Optional[str]] = []
    lens_texts: List[str] = []
    ids: List[str] = []
    for i, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            classes.append(None); lens_texts.append(""); ids.append(f"Clip_{i:02d}"); continue
        # 新 schema 的 shots 可能是 int 列表（非 dict）；只读 dict 形 shot，并兜底 continuity.shot_size。
        lens = "；".join(str(s.get("lens", "")) for s in (clip.get("shots") or []) if isinstance(s, dict))
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        scale_text = lens or str(clip.get("景别") or clip.get("shot_size") or cont.get("shot_size") or "")
        classes.append(shot_scale_class(scale_text))
        lens_texts.append(lens or scale_text)
        ids.append(str(clip.get("id") or clip.get("clip") or clip.get("shot") or f"Clip_{i:02d}"))
    for start, end, cls, length in monotonous_scale_runs(classes):
        if any(_OTS_RE.search(lens_texts[k]) for k in range(start, end + 1)):
            continue  # 对白正反打/过肩交替 = 合法景别变化，豁免
        loc = f"{ids[start]}→{ids[end]}"
        add(WARN, "景别阶梯", loc,
            f"连续 {length} 镜同景别 {cls}（{loc}）——景别阶梯单调、缺远近或机位变化；"
            "按导演意图穿插不同景别/机位（或确认为设计内的同景别段）。",
            return_to_stage="image")
    # 抽取健壮性（G）：lens 写了但抽不出景别分级的镜（如「中景偏特写」「平视带点压」这类非标准写法），
    # 景别阶梯机检对它们静默失效——把这些镜醒目报出来，提示规范 lens 写法，避免「全绿=都查过了」的错觉。
    unparsed = [ids[i] for i in range(len(classes)) if classes[i] is None and lens_texts[i].strip()]
    if len(unparsed) >= 2:
        sample = "、".join(unparsed[:6]) + ("…" if len(unparsed) > 6 else "")
        add(WARN, "景别阶梯", sample,
            f"{len(unparsed)} 个镜写了 lens 但抽不出景别分级（{sample}）——景别阶梯单调性机检对它们失效；"
            "把 lens 写成标准景别词（ELS/LS/MS/MCU/CU/ECU 或 大远景/远景/中景/中近景/特写/大特写）再机检。",
            return_to_stage="image")


# 逐镜块切分：`prompt_format.md` 写 `## 镜头 N`，但生成器/旧稿也有 `## 镜头N`（无空格，见
# test_visual_state_manager）——空格设为可选，否则无空格写法整块漏检＝机检静默失效（假绿灯）。
_SHOT_BLOCK_SPLIT_RE = re.compile(r"##\s*镜头\s*\d+")
# 多人同框已显式写清相对尺度的标记（命中任一＝已交代，不告警）。
_PHYSICAL_SCALE_TOKENS = ("仰视", "俯视", "高半个头", "身长", "身高", "比例", "高矮")


def _registry_character_names(root: str) -> List[str]:
    """从 identity_registry 取所有角色显示名/别名（按 / ／ 切）——物理尺寸对账靠它识别同框人物，
    不再硬编码某部 demo 的角色名（旧实现写死「沈念/柳娘子/王敦/小禾」，对其它作品一律静默放行＝假绿灯）。"""
    data = load_json(identity_registry_path(root))
    if not isinstance(data, dict):
        return []
    chars = data.get("characters")
    if isinstance(chars, dict):
        chars = list(chars.values())
    if not isinstance(chars, list):
        return []
    names: List[str] = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        for n in str(c.get("name") or "").replace("／", "/").split("/"):
            n = n.strip()
            if len(n) >= 2 and n not in names:
                names.append(n)
    return names


def check_cinematic_optical_continuity(root: str, ep: str) -> None:
    """Validate that focal lengths match shot sizes to prevent perspective distortion."""
    pd = os.path.join(root, "出图", ep, "prompt")
    f = os.path.join(pd, "01_分镜出图.md")
    if not os.path.exists(f):
        return

    content = open(f, encoding="utf-8").read()
    shots = _SHOT_BLOCK_SPLIT_RE.split(content)

    # ECU/CU=85mm, MS=50mm, LS=35mm, ELS=24mm
    mapping = {
        "ECU": "85mm", "CU": "85mm",
        "MCU": "50mm", "MS": "50mm",
        "LS": "35mm", "ELS": "24mm"
    }

    for shot in shots:
        if not shot.strip(): continue

        shot_size_match = re.search(r"景别\((ELS|LS|MS|MCU|CU|ECU).*?\)", shot)
        if shot_size_match:
            size = shot_size_match.group(1)
            expected_focal = mapping.get(size)
            if expected_focal and expected_focal not in shot:
                add(WARN, "电影光学契约", f, f"镜头景别为 {size}，建议在 prompt 中显式锁定焦段为 {expected_focal} 以保透视一致")


def check_physical_scale_audit(root: str, ep: str) -> None:
    """Validate relative heights in multi-character shots.

    同框 ≥2 个 identity_registry 角色却没交代身高比例/仰俯视 → WARN（多人同框易出比例穿帮）。
    角色名从 registry 取（见 `_registry_character_names`），不写死 demo 名。"""
    pd = os.path.join(root, "出图", ep, "prompt")
    f = os.path.join(pd, "01_分镜出图.md")
    if not os.path.exists(f):
        return

    names = _registry_character_names(root)
    if len(names) < 2:
        return  # 不足两名可识别角色：无从判定同框，跳过（不臆造）

    content = open(f, encoding="utf-8").read()
    shots = _SHOT_BLOCK_SPLIT_RE.split(content)

    for shot in shots:
        if not shot.strip(): continue
        # 取镜内「目标：…」行（出图块标注同框人物处）；无该行则全块兜底扫名字。
        target_lines = re.findall(r"目标：[^\n]*", shot)
        scope = "\n".join(target_lines) if target_lines else shot
        present = {n for n in names if n in scope}
        if len(present) >= 2:
            if not any(k in shot for k in _PHYSICAL_SCALE_TOKENS):
                who = "、".join(sorted(present))
                add(WARN, "物理尺寸对账", f,
                    f"检测到多人同框镜头（{who}），建议显式写明人物之间的【身高比例差】或【仰俯视关系】，防同框比例穿帮")


def check_identity_adapter_matrix(root: str) -> None:
    p = identity_adapter_matrix_path(root)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "资产身份闭环", p, "缺少或无法解析 identity_adapter_matrix.json；先运行 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`")
        return
    if data.get("kind") != IDENTITY_ADAPTER_MATRIX_KIND:
        add(BLOCK, "资产身份闭环", p, f"kind 必须是 {IDENTITY_ADAPTER_MATRIX_KIND}")
    forms = data.get("forms")
    if not isinstance(forms, list) or not forms:
        add(BLOCK, "资产身份闭环", p, "forms[] 为空；identity_registry 没有展开成可执行后端 binding")
        return
    for idx, form in enumerate(forms, 1):
        loc = f"{p} form#{idx}"
        if not isinstance(form, dict):
            add(BLOCK, "资产身份闭环", loc, "form 必须是对象")
            continue
        for key in ("character_id", "form", "reference_group", "image_bindings", "video_bindings", "lora_binding"):
            if _field_is_missing(form, key):
                add(BLOCK, "资产身份闭环", loc, f"adapter matrix form 缺字段：{key}")
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    matrix_fp = str(summary.get("anchor_fingerprint") or "").strip()
    registry = load_json(identity_registry_path(root))
    if not isinstance(registry, dict):
        add(BLOCK, "资产身份闭环", identity_registry_path(root), "无法解析 identity_registry.json；matrix 无法证明相对当前身份库新鲜")
        return
    try:
        from identity import registry_anchor_fingerprint  # type: ignore
        current_fp = registry_anchor_fingerprint(registry)
    except Exception as exc:
        add(BLOCK, "资产身份闭环", p, f"无法计算当前 identity_registry anchor_fingerprint：{type(exc).__name__}: {exc}")
        return
    if not matrix_fp:
        add(BLOCK, "资产身份闭环", p, "identity_adapter_matrix.summary 缺 anchor_fingerprint；请重跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`")
    elif matrix_fp != current_fp:
        add(
            BLOCK,
            "资产身份闭环",
            p,
            "identity_adapter_matrix 已过期：summary.anchor_fingerprint 与当前 identity_registry 不一致；"
            "共享定妆/锚点被改后必须重跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`。",
        )


def check_prompt_checklists(root: str, ep: str, kind: str) -> None:
    if kind == "image":
        p = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
        if not os.path.isfile(p):
            add(BLOCK, "prompt", p, "缺本集分镜出图 prompt")
            return
        text = open(p, encoding="utf-8").read()
        if "生成后自检流程" not in text and "自检（生成后逐张过" not in text:
            add(WARN, "prompt", p, "缺全局生成后自检流程")
        sections = re.findall(r"(?ms)^##\s+(?:镜头\s+\d+|Clip\s+\d+[A-Z]?).*?(?=^##\s+(?:镜头\s+\d+|Clip\s+\d+[A-Z]?)|\Z)", text)
        if not sections:
            add(BLOCK, "prompt", p, "未识别到逐镜 prompt 块")
            return
        # 单图参考后端(无原生主体锁，如 Codex)下，双人同框是实锤脸漂真凶 → 该镜的多角色检查升 BLOCK；
        # 有原生主体能力的后端(Seedream/可灵/Sora)仍按 WARN。能力判定走契约 persistent_subject，不 hardcode。
        _img_canon, _ = classify_image_backend(get_setting(root, "生图AI", "Codex").strip())
        single_ref_backend = not image_backend_supports_persistent_subject(_img_canon)
        for idx, sec in enumerate(sections, 1):
            check_image_shot_prompt_section(p, idx, sec, single_ref_backend=single_ref_backend)
        return
    else:
        check_video_prompt_overview(root, ep)
        p = os.path.join(root, "出视频", ep, "prompt", "01_clips.md")
        if not os.path.isfile(p):
            add(BLOCK, "prompt", p, "缺本集视频 Clip prompt")
            return
        text = open(p, encoding="utf-8").read()
        native_av = is_native_av_production(root)
        if _section_native_audio_opt_in(text) or (native_av and "native_speech" in text):
            overview = os.path.join(root, "出视频", ep, "prompt", "00_总览.md")
            overview_text = open(overview, encoding="utf-8").read() if os.path.isfile(overview) else ""
            if "原生音画 opt-in 清单" not in overview_text:
                add(BLOCK, "原生音画", overview, "逐 Clip prompt 启用了原生音画，但出视频总览缺「原生音画 opt-in 清单」")
            elif native_av:
                # 制作模式=原生音画：台词由后端原生生成是有意为之，不再强制 no_native_speech。
                if not _has_any(overview_text, ("native_speech", "原生人声")):
                    add(WARN, "原生音画", overview, "原生音画模式：总览应说明 native_speech 为有意生成")
            elif not _native_audio_contract_ok(overview_text):
                add(BLOCK, "原生音画", overview, "原生音画 opt-in 清单必须明确 no_native_speech / 无原生人声")
        sections = re.findall(r"(?ms)^##\s+Clip\s+\d+[A-Z]?（.*?(?=^##\s+Clip\s+\d+[A-Z]?（|\Z)", text)
        if not sections:
            add(BLOCK, "prompt", p, "未识别到 Clip prompt 块")
            return
        route_map = _video_route_policy_map(root, ep)
        for idx, sec in enumerate(sections, 1):
            clip_num = _clip_number_from_section(sec, idx)
            check_video_clip_prompt_section(p, sec, route=route_map.get(clip_num))
        return


def _has_any(text: str, needles: Iterable[str]) -> bool:
    return any(n in text for n in needles)


def _headline(section: str, fallback: str) -> str:
    first = next((ln.strip() for ln in section.splitlines() if ln.strip()), "")
    return first or fallback


def _clip_number_from_section(section: str, fallback_index: int) -> int:
    m = re.search(r"(?m)^##\s*Clip[_\s]*(\d+)", section)
    return int(m.group(1)) if m else fallback_index


def _has_field(section: str, label: str) -> bool:
    return bool(re.search(rf"(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*[：:]", section))


def _has_line_field(section: str, label: str) -> bool:
    return bool(re.search(rf"(?m)^\s*(?:[-*]\s*)?(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*[：:]", section))


def _section_requires_motion_control(section: str) -> bool:
    return _has_any(
        section,
        (
            "shot_type=fight_exchange",
            "shot_type=chase",
            "shot_type=flight",
            "shot_type=intimate_interaction",
            "shot_type=hug_or_pull",
            "contact_motion",
            "physical_interaction",
            "feature_melting_risk",
            "high_speed_motion",
            "spatial_path_risk",
        ),
    )


def _route_requires_contact_fields(route: Dict[str, object]) -> bool:
    shot_type = str(route.get("shot_type") or "").strip()
    if shot_type in MOTION_CONTROL_CONTACT_SHOT_TYPES:
        return True
    if shot_type in {"chase", "flight"} or shot_type in {"multi_character_same_frame", "ensemble_blocking", "multi_person_blocking"}:
        return False
    flags = route.get("risk_flags")
    flag_set = set(str(x) for x in flags) if isinstance(flags, list) else set()
    return bool(flag_set & {"contact_motion", "physical_interaction", "feature_melting_risk"})


def _section_shot_type(section: str, route: Optional[Dict[str, Any]] = None) -> str:
    if route:
        shot_type = str(route.get("shot_type") or "").strip()
        if shot_type:
            return shot_type
    m = re.search(r"shot_type\s*=\s*([A-Za-z0-9_]+)", section)
    return m.group(1) if m else ""


def _action_choreography_required_fields(shot_type: str) -> Tuple[str, ...]:
    return ACTION_CHOREOGRAPHY_COMMON_FIELDS + ACTION_CHOREOGRAPHY_SPECIFIC_FIELDS.get(shot_type, ())


def _missing_contract_fields(text: str, fields: Iterable[str]) -> List[str]:
    return [key for key in fields if key not in text]


def native_audio_policy(root: str) -> str:
    return get_setting(root, "视频原生音轨", "丢弃").strip() or "丢弃"


def native_audio_policy_mode(policy: str) -> str:
    normalized = policy.strip().lower().replace(" ", "")
    if normalized in ("丢弃", "discard", "none"):
        return NATIVE_AUDIO_DISCARD
    if "低音量" in policy or "环境声" in policy or normalized in ("ambience", "mix", "low"):
        return NATIVE_AUDIO_AMBIENCE
    if "保留" in policy or normalized in ("keep", "preserve"):
        return NATIVE_AUDIO_KEEP
    return NATIVE_AUDIO_DISCARD


def _section_native_audio_opt_in(section: str) -> bool:
    return _has_any(section, ("audio_intent=ambience", "audio_intent=native_sfx", "低音量混入环境声", "保留原片音轨", "compose_policy=低音量", "compose_policy=保留"))


def _native_audio_contract_ok(text: str) -> bool:
    return _has_any(text, ("无原生人声", "禁止原生人声", "no_native_speech", "no generated native voice"))


NATIVE_AV_PHYSICAL_FIELDS = ("声源归属", "口型策略", "材质/动作声", "空间声学", "字幕/后期策略")
NATIVE_AV_PHYSICS_KIND = "n2d_native_av_physics"


def is_native_av_production(root: str) -> bool:
    """`制作模式=原生音画`：视频后端有意一次生成同步音画（含台词）。"""
    return is_native_av(root)


def native_av_physics_required(root: str, ep: str = "", overview_text: str = "") -> bool:
    """Any retained/mixed native audio needs a physical sidecar, not only native_av mode."""
    if is_native_av_production(root):
        return True
    if native_audio_policy_mode(native_audio_policy(root)) != NATIVE_AUDIO_DISCARD:
        return True
    if overview_text and _section_native_audio_opt_in(overview_text):
        return True
    return False


def _native_audio_policy_line(section: str) -> str:
    m = re.search(r"(?m)^\*\*原生音画策略\*\*.*$", section)
    if m:
        return m.group(0)
    m = re.search(r"(?m)^原生音画策略.*$", section)
    return m.group(0) if m else section


def check_native_audio_opt_in_overview(root: str, ep: str, overview_text: str, loc: str) -> None:
    if is_native_av_production(root):
        # 制作模式=原生音画：native_speech 是有意路由（说话镜一次出同步音画），不强制 no_native_speech。
        # 仍要求总览声明原生音画意图。
        if not _has_any(overview_text, ("native_speech", "原生音画", "原生人声")):
            add(WARN, "原生音画", loc, "原生音画模式：出视频总览应声明 native_speech 路由（台词+口型由后端原生生成）")
        return
    policy = native_audio_policy(root)
    mode = native_audio_policy_mode(policy)
    if mode == NATIVE_AUDIO_DISCARD:
        return
    if "原生音画 opt-in 清单" not in overview_text:
        add(BLOCK, "原生音画", loc, f"`视频原生音轨={policy}` 不是默认丢弃；出视频总览必须写「原生音画 opt-in 清单」，逐 Clip 说明低风险、无口型、无原生人声")
    if not _native_audio_contract_ok(overview_text):
        add(BLOCK, "原生音画", loc, "原生音画 opt-in 清单必须明确 no_native_speech / 无原生人声；否则 compose 不得混入或保留原生音轨")


def check_native_av_physical_contract(root: str, ep: str, overview_text: str, loc: str) -> None:
    if not native_av_physics_required(root, ep, overview_text):
        return
    title = "原生音画物理一致性契约"
    if title not in overview_text:
        add(BLOCK, "原生音画物理一致性", loc,
            f"本集会保留/混入原生音轨或使用原生音画，但缺「{title}」；"
            "必须锁声源归属、口型策略、材质/动作声、空间声学、字幕/后期策略后才能进视频生成/合成")
        return
    for key in NATIVE_AV_PHYSICAL_FIELDS:
        if key not in overview_text:
            add(BLOCK, "原生音画物理一致性", loc, f"{title} 缺字段：{key}")


def native_av_physics_sidecar_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"native_av_physics_{ep}.json")


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on", "可见", "是", "yes/true"}


def _mapping(value: object) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clip_audio_intent(row: Mapping[str, Any]) -> str:
    return str(row.get("audio_intent") or row.get("sound_intent") or row.get("声音意图") or "").strip().lower()


def _clip_compose_policy(row: Mapping[str, Any]) -> str:
    post = _mapping(row.get("post_policy") or row.get("后期策略"))
    return str(row.get("compose_policy") or post.get("compose_policy") or post.get("音轨处理") or "").strip()


def _sidecar_clip_id(row: Mapping[str, Any], idx: int) -> str:
    return str(row.get("clip_id") or row.get("clip") or row.get("id") or f"Clip_{idx:02d}").strip()


def _native_av_physics_clip_errors(row: Mapping[str, Any], idx: int) -> List[str]:
    clip_id = _sidecar_clip_id(row, idx)
    errors: List[str] = []
    intent = _clip_audio_intent(row)
    if not intent:
        errors.append(f"{clip_id} 缺 audio_intent")
    spatial = _mapping(row.get("spatial_acoustics") or row.get("space_acoustics") or row.get("空间声学"))
    if not (spatial.get("space_id") or spatial.get("loc_id") or spatial.get("location") or spatial.get("LOC")):
        errors.append(f"{clip_id} 缺 spatial_acoustics.space_id/LOC")
    if not (spatial.get("distance") or spatial.get("shot_distance") or spatial.get("景别距离")):
        errors.append(f"{clip_id} 缺 spatial_acoustics.distance")
    if not (spatial.get("reverb_profile") or spatial.get("reverb") or spatial.get("acoustic_profile") or spatial.get("混响")):
        errors.append(f"{clip_id} 缺 spatial_acoustics.reverb_profile")
    compose_policy = _clip_compose_policy(row)
    if not compose_policy:
        errors.append(f"{clip_id} 缺 post_policy.compose_policy")

    if intent in {"ambience", "ambient", "environment", "环境声", "native_sfx", "sfx", "action_sfx", "动作声"}:
        source = _mapping(row.get("sound_source") or row.get("speaker_source") or row.get("声源归属"))
        if not (
            source.get("source")
            or source.get("source_id")
            or source.get("asset")
            or source.get("loc_id")
            or row.get("source")
        ):
            errors.append(f"{clip_id} {intent} 缺 sound_source.source/source_id")
        if not (
            source.get("visible_evidence")
            or source.get("visible_action_evidence")
            or row.get("visible_evidence")
            or row.get("visible_action_evidence")
            or row.get("action_sounds")
        ):
            errors.append(f"{clip_id} {intent} 缺 visible_evidence/visible_action_evidence")
        if not any(token in compose_policy for token in ("低音量", "混入", "保留")) and not any(token in compose_policy.lower() for token in ("mix", "keep", "preserve")):
            errors.append(f"{clip_id} {intent} compose_policy 必须说明低音量混入或保留策略")

    if intent in {"native_speech", "speech", "dialogue", "对白", "台词"}:
        speaker = _mapping(row.get("speaker_source") or row.get("sound_source") or row.get("声源归属"))
        if not (speaker.get("character_id") or speaker.get("speaker_id") or speaker.get("subject_id") or speaker.get("voice_id")):
            errors.append(f"{clip_id} native_speech 缺 speaker_source.character_id/speaker_id")
        if not _truthy(speaker.get("on_screen") or speaker.get("visible") or speaker.get("画内")):
            errors.append(f"{clip_id} native_speech 声源未声明画内可见")
        mouth_visible = speaker.get("mouth_visible")
        if mouth_visible is None:
            mouth_visible = row.get("mouth_visible")
        if not _truthy(mouth_visible):
            errors.append(f"{clip_id} native_speech 缺 mouth_visible=true")
        if not (speaker.get("dialogue_ref") or speaker.get("dialogue_text") or speaker.get("text") or row.get("dialogue_ref")):
            errors.append(f"{clip_id} native_speech 缺 dialogue_ref/dialogue_text")
        lipsync = _mapping(row.get("lip_sync") or row.get("口型策略"))
        if not (lipsync.get("policy") or lipsync.get("expected") or lipsync.get("target")):
            errors.append(f"{clip_id} native_speech 缺 lip_sync.policy")
        if "保留" not in compose_policy and "keep" not in compose_policy.lower() and "preserve" not in compose_policy.lower():
            errors.append(f"{clip_id} native_speech compose_policy 必须保留原片音轨")

    action_sounds = row.get("action_sounds") or row.get("动作声") or []
    if intent in {"native_sfx", "sfx", "action_sfx", "动作声"} and not isinstance(action_sounds, list):
        errors.append(f"{clip_id} native_sfx action_sounds 必须是数组")
    if intent in {"native_sfx", "sfx", "action_sfx", "动作声"} and isinstance(action_sounds, list) and not action_sounds:
        errors.append(f"{clip_id} native_sfx action_sounds 不得为空")
    if isinstance(action_sounds, list):
        for j, item in enumerate(action_sounds, start=1):
            if not isinstance(item, Mapping):
                errors.append(f"{clip_id} action_sounds[{j}] 不是对象")
                continue
            if not (item.get("action") or item.get("sound")):
                errors.append(f"{clip_id} action_sounds[{j}] 缺 action/sound")
            if not item.get("visible_evidence"):
                errors.append(f"{clip_id} action_sounds[{j}] 缺 visible_evidence")
            if not (item.get("timing") or item.get("time") or item.get("at")):
                errors.append(f"{clip_id} action_sounds[{j}] 缺 timing")
    return errors


def check_native_av_physics_sidecar(root: str, ep: str, required: Optional[bool] = None) -> None:
    if required is None:
        required = native_av_physics_required(root, ep)
    if not required:
        return
    path = native_av_physics_sidecar_path(root, ep)
    data = load_json(path)
    if not isinstance(data, dict):
        add(
            BLOCK,
            "原生音画物理一致性",
            path,
            "缺机器可读 sidecar：生产数据/native_av_physics_第N集.json；必须逐 Clip 写谁发声、动作声可见证据、空间混响/距离和后期保留策略，不能只靠总览人判。",
            return_to_stage="video",
        )
        return
    if data.get("kind") != NATIVE_AV_PHYSICS_KIND:
        add(BLOCK, "原生音画物理一致性", path, f"native_av_physics sidecar kind 应为 {NATIVE_AV_PHYSICS_KIND}")
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        add(BLOCK, "原生音画物理一致性", path, "native_av_physics sidecar 缺 clips[]；无法逐镜校验声源/动作声/空间声学。")
        return
    for idx, row in enumerate(clips, start=1):
        if not isinstance(row, Mapping):
            add(BLOCK, "原生音画物理一致性", path, f"clips[{idx}] 不是对象")
            continue
        for err in _native_av_physics_clip_errors(row, idx):
            add(BLOCK, "原生音画物理一致性", path, err, return_to_stage="video")


def check_markdown_style_contract(text: str, loc: str, layer: str) -> None:
    if "本集基础视觉风格契约" in text:
        missing = _missing_contract_fields(text, STYLE_CONTRACT_FIELDS)
        if missing:
            add(BLOCK, "基础视觉风格契约", loc, f"本集基础视觉风格契约缺字段：{missing[0]}")
        return
    if "本集真实电影感契约" in text:
        missing = _missing_contract_fields(text, CINEMATIC_CONTRACT_FIELDS)
        if missing:
            add(BLOCK, "基础视觉风格契约", loc, f"本集真实电影感契约缺字段：{missing[0]}")
        return
    add(BLOCK, "基础视觉风格契约", loc, f"缺「本集基础视觉风格契约」；{layer} 必须继承 storyboard.json style_contract，而不是只在 prompt 末尾加某一种风格词")


def check_video_prompt_overview(root: str, ep: str) -> None:
    """Video prompt overview must carry the episode-level director contract.

    Per-clip prompts can be locally valid and still cut together badly.  The
    overview locks the episode's visual grammar before any paid video call.
    """
    p = os.path.join(root, "出视频", ep, "prompt", "00_总览.md")
    if not os.path.isfile(p):
        add(BLOCK, "prompt", p, "缺出视频总览；无法锁本集导演一致性契约")
        return
    text = open(p, encoding="utf-8").read()
    if "本集导演一致性契约" not in text:
        add(BLOCK, "导演一致性", p, "缺「本集导演一致性契约」；不能只按单 Clip 随机写视频 prompt")
        return
    for key in ("主色调", "镜头语法", "轴线", "剧情状态锁", "场景状态"):
        if key not in text:
            add(BLOCK, "导演一致性", p, f"本集导演一致性契约缺字段：{key}")
    check_markdown_style_contract(text, p, "出视频总览")
    check_video_model_routes(root, ep, text, p)
    check_video_closeup_identity_overview(text, p)
    check_native_audio_opt_in_overview(root, ep, text, p)
    check_native_av_physical_contract(root, ep, text, p)
    check_native_av_physics_sidecar(root, ep, native_av_physics_required(root, ep, text))


def check_video_closeup_identity_overview(overview_text: str, overview_path: str) -> None:
    has_identity_overview = _has_any(
        overview_text,
        (
            "本集资产身份速查",
            "本集身份 Adapter Matrix 摘要",
            "identity_adapter_matrix",
            "reference_group",
            "角色身份",
        ),
    )
    if not has_identity_overview:
        return
    if "本集近景身份风险表" not in overview_text:
        add(
            BLOCK,
            "资产身份注册层",
            overview_path,
            "缺「本集近景身份风险表」；CU/MCU/反打/说话镜必须在总览列明脸部特写/表情参考、当前后端身份锁能力、风险等级和降级方案",
        )
        return
    for key in ("脸部", "表情", "风险", "降级"):
        if key not in overview_text:
            add(BLOCK, "资产身份注册层", overview_path, f"本集近景身份风险表缺字段/关键词：{key}")
    if _has_any(overview_text, ("CHAR_02", "配角", "小禾", "柳娘子")) and not _has_any(overview_text, ("MCU", "OTS", "侧脸", "手部", "物件反应")):
        add(
            WARN,
            "资产身份注册层",
            overview_path,
            "本集近景身份风险表未写配角近景降级路径；建议明确 MCU/OTS/侧脸/手部/物件反应镜",
        )


def _route_clip_number(route: Dict[str, Any], fallback_index: int) -> int:
    raw = str(route.get("clip_id") or route.get("clip") or "").strip()
    match = re.search(r"(\d+)", raw)
    return int(match.group(1)) if match else fallback_index


def _video_route_policy_map(root: str, ep: str) -> Dict[int, Dict[str, Any]]:
    data = load_json(os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json"))
    routes = data.get("routes") if isinstance(data, dict) else None
    if not isinstance(routes, list):
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for idx, route in enumerate(routes, 1):
        if isinstance(route, dict):
            out[_route_clip_number(route, idx)] = route
    return out


def _storyboard_frame_requirements(root: str, ep: str) -> Dict[int, Dict[str, int | bool]]:
    """Clip -> ordered frame contract declared by storyboard continuity."""
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        return {}
    out: Dict[int, Dict[str, int | bool]] = {}
    for idx, clip in enumerate(data.get("clips") or [], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        if not isinstance(cont, dict):
            continue
        anchor_count = 0
        if isinstance(cont.get("midframe"), dict):
            anchor_count = 1
        elif isinstance(cont.get("anchors"), list):
            anchor_count = len([a for a in cont.get("anchors") or [] if isinstance(a, dict)])
        need_end = cont.get("need_endframe") is True
        out[idx] = {
            "need_end": need_end,
            "anchor_count": anchor_count,
            "total_timeline_frames": 1 + anchor_count + (1 if need_end else 0),
            # 高风险=高运动模板 或 跨情绪大表情近景：帧能力不匹配时安全网（双帧/多帧插值）静默失效，
            # check_route_frame_capability 据此把 WARN 升 BLOCK（其余镜保持 WARN，有合法降级路径）。
            "high_risk": (str(clip.get("template") or "") in HIGH_MOTION_TEMPLATES
                          or (cont.get("expression_span") == EXPRESSION_SPAN_BIG and _clip_is_closeup(clip))),
        }
    return out


def check_route_frame_capability(
    root: str,
    ep: str,
    route: Dict[str, Any],
    route_path: str,
    idx: int,
    frame_requirements: Dict[int, Dict[str, int | bool]],
    video_channel: str,
) -> None:
    """Warn when the storyboard asks for more timeline frames than the route can consume.

    For ordinary clips the warning is intentional rather than blocking: n2d has
    valid fallback paths (split relay, first+last only, or first frame +
    end_state text). What must not happen is silent degradation where `_mid`
    frames are generated but ignored by the selected backend.

    **高风险镜例外（req.high_risk）**：高运动模板（打斗/追逐/法术/飞行/拥抱拉扯/亲密接触）
    与跨情绪大表情近景，靠帧间插值（双帧/多帧）才稳——后端吃不下首尾/中段帧 = 双帧安全网
    静默失效 = 必崩接触/必脸漂。这类镜帧能力不匹配从 WARN 升 **BLOCK**，强制换后端或显式降级，
    不许靠纯文本约束硬出。
    """
    clip_num = _route_clip_number(route, idx)
    req = frame_requirements.get(clip_num)
    if not req:
        return
    primary = str(route.get("primary_backend") or "").strip()
    control = video_backend_frame_control(primary, video_channel)
    max_frames = int(control.get("max_timeline_frames") or 1)
    total_frames = int(req.get("total_timeline_frames") or 1)
    anchors = int(req.get("anchor_count") or 0)
    need_end = bool(req.get("need_end"))
    consumption = anchor_consumption_plan(primary, video_channel, anchor_count=anchors, need_end=need_end)
    consumption_mode = str(consumption.get("consumption_mode") or "unknown")
    high_risk = bool(req.get("high_risk"))
    sev = BLOCK if high_risk else WARN
    risk_note = (
        "本镜为高运动模板/跨情绪大表情近景，帧间插值是唯一安全网，不许靠纯文本约束硬出（已升级为 BLOCK）。"
        if high_risk else ""
    )
    clip_id = str(route.get("clip_id") or f"Clip_{clip_num:02d}")
    mode = str(control.get("mode") or "unknown")
    verified = str(control.get("verified") or "unknown")
    fallback = str(control.get("fallback") or "Use split relay/manual generation.")
    channel_note = f"（执行渠道：{video_channel}）" if video_channel else ""
    if need_end and not bool(consumption.get("consumes_endframe")):
        add(
            sev,
            "首尾帧能力",
            route_path,
            f"{clip_id} storyboard 需要尾帧接力，但 primary 后端 {primary or 'unknown'}{channel_note} "
            f"的帧能力档案为 {mode}，消费计划为 {consumption_mode}，未确认可消费尾帧。fallback：改走支持首尾帧的后端，"
            f"或退回单首帧 + 强 end_state 文字（接缝/大表情近景风险升高）。能力来源：{verified}{risk_note}",
            return_to_stage="video",
        )
    if anchors and not bool(consumption.get("consumes_mid_anchors_natively")):
        if consumption.get("requires_split_relay"):
            consequence = "该后端通常只能吃首尾两帧，中段锚帧不会在一次请求里成为时间轴关键帧，执行侧必须拆段接力"
        else:
            consequence = "该后端通常只按首帧/参考图生成，中段锚帧和尾帧都可能只剩文字约束"
        add(
            sev,
            "多帧能力",
            route_path,
            f"{clip_id} storyboard 声明了 {anchors} 个中段锚帧（共 {total_frames} 张时间轴帧），"
            f"但 primary 后端 {primary or 'unknown'}{channel_note} 的帧能力档案为 {mode}，"
            f"最多 {max_frames} 张时间轴帧，消费计划为 {consumption_mode}；{consequence}。fallback：{fallback}{risk_note}",
            return_to_stage="video",
        )


MODEL_ROUTE_BASELINE_HIGH_RISK_SHOT_TYPES = {
    "action_fight",
    "action_chase",
    "escape",
    "breakthrough",
    "flight",
    "magic_burst",
    "multi_character_same_frame",
    "ensemble_blocking",
    "intimate_interaction",
    "hug_or_pull",
    "dialogue_closeup",
    "dialogue_shot_reverse",
    "reveal_reaction_chain",
    "confrontation_power_shift",
    "relationship_turn",
}
MODEL_ROUTE_BASELINE_HIGH_RISK_FLAGS = {
    "multi_person",
    "identity_escalated",
    "character_backend_conflict",
    "contact_motion",
    "feature_melting_risk",
    "mouth_visible",
    "native_speech",
    "seam_relay",
    "motion_reference_candidate",
    "requires_motion_control",
    "frame_consumption_degraded",
    "missing_last_frame_capability",
}


def _route_needs_model_baseline(route: Mapping[str, object]) -> bool:
    st = str(route.get("shot_type") or "").strip()
    flags = {str(item) for item in route.get("risk_flags", []) if item} if isinstance(route.get("risk_flags"), list) else set()
    identity = str(route.get("identity_requirement") or "").strip().lower()
    if st in MODEL_ROUTE_BASELINE_HIGH_RISK_SHOT_TYPES:
        return True
    if flags & MODEL_ROUTE_BASELINE_HIGH_RISK_FLAGS:
        return True
    return identity not in {"", "none", "not_needed", "no_character"}


def _identity_route_requires_character_refs(route: Mapping[str, object]) -> bool:
    identity = str(route.get("identity_requirement") or "").strip().lower()
    return identity not in {"", "none", "not_needed", "no_character"}


def _route_clip_character_refs(route: Mapping[str, object]) -> List[Dict[str, str]]:
    raw = route.get("clip_characters")
    refs: List[Dict[str, str]] = []
    if not isinstance(raw, list):
        return refs
    for item in raw:
        cid = ""
        form = ""
        if isinstance(item, Mapping):
            cid = str(item.get("character_id") or item.get("id") or "").strip()
            form = str(item.get("form") or item.get("形态") or "").strip()
        elif isinstance(item, str):
            m = re.search(r"\b(CHAR_[A-Za-z0-9_]+)(?:/([^\s，；、`,|]+))?\b", item)
            if m:
                cid = m.group(1)
                form = (m.group(2) or "").strip()
        if not cid:
            continue
        ref = {"character_id": cid}
        if form:
            ref["form"] = form
        if ref not in refs:
            refs.append(ref)
    return refs


def _baseline_override_accepted(data: Mapping[str, object], route: Optional[Mapping[str, object]] = None) -> bool:
    if os.environ.get("N2D_ALLOW_MODEL_ROUTE_BASELINE_DRIFT") == "1":
        return True
    return not _baseline_override_errors(data, route)


def _as_string_list(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,，、\s]+", value) if part.strip()]
    return []


def _baseline_override_payload(data: Mapping[str, object], route: Optional[Mapping[str, object]] = None) -> Dict[str, object]:
    for obj in (route or {}, data):
        if not isinstance(obj, Mapping):
            continue
        raw = obj.get("baseline_override")
        if isinstance(raw, Mapping):
            return dict(raw)
        if any(k in obj for k in ("baseline_override_accepted", "baseline_override_reason", "baseline_override_reviewer", "baseline_override_expires_at", "baseline_override_affected_routes")):
            return {
                "accepted": obj.get("baseline_override_accepted"),
                "reason": obj.get("baseline_override_reason"),
                "reviewer": obj.get("baseline_override_reviewer"),
                "expires_at": obj.get("baseline_override_expires_at"),
                "affected_routes": obj.get("baseline_override_affected_routes"),
            }
    return {}


def _override_expiry_ok(value: object) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    try:
        expiry = dt.date.fromisoformat(raw[:10])
    except Exception:
        return False
    return expiry >= dt.date.today()


def _baseline_override_errors(data: Mapping[str, object], route: Optional[Mapping[str, object]] = None) -> List[str]:
    payload = _baseline_override_payload(data, route)
    if not payload:
        return ["missing baseline_override"]
    errors: List[str] = []
    if payload.get("accepted") is not True:
        errors.append("accepted 必须为 true")
    if not str(payload.get("reviewer") or "").strip():
        errors.append("reviewer 缺失")
    if not str(payload.get("reason") or "").strip():
        errors.append("reason 缺失")
    if not _override_expiry_ok(payload.get("expires_at") or payload.get("expires")):
        errors.append("expires_at 缺失/过期/格式错误")
    affected = _as_string_list(payload.get("affected_routes"))
    if not affected:
        errors.append("affected_routes 缺失")
    elif route is not None:
        clip_id = str(route.get("clip_id") or "").strip()
        if "*" not in affected and clip_id and clip_id not in affected:
            errors.append(f"affected_routes 未覆盖 {clip_id}")
    return errors
    return False


def check_model_route_baseline_policy(root: str, ep: str, data: Mapping[str, object], routes: Sequence[Dict[str, Any]], path: str) -> None:
    """Episode 2+ high-risk/core routes must be anchored to a cross-episode backend baseline."""
    try:
        ep_num = _ce_episode_number(ep) or 0
    except Exception:
        ep_num = 0
    risky = [r for r in routes if isinstance(r, dict) and _route_needs_model_baseline(r)]
    if ep_num < 2 or not risky:
        return
    baseline_path = os.path.join(root, "设定库", "model_routes_baseline.json")
    if all(_baseline_override_accepted(data, r) for r in risky):
        add(
            WARN,
            "后端跨集锁",
            path,
            "本集高风险/含角色路由使用了结构化 baseline_override；请确认这是有意换后端，而不是漏跑第1集模型路由基线。",
            return_to_stage="video_prompt",
        )
        return
    samples = "、".join(str(r.get("clip_id") or r.get("shot_type") or "?") for r in risky[:6])
    if not os.path.isfile(baseline_path):
        add(
            BLOCK,
            "后端跨集锁",
            baseline_path,
            f"{ep} 含高风险/含角色路由（{samples}）但缺 `设定库/model_routes_baseline.json`。"
            "第2集起必须先用打样集 `n2d-model-router --write-baseline` 建立 shot_type→primary 后端基线，"
            "否则跨集自然路由可能换后端导致脸质感、运动质感和画风漂移。",
            return_to_stage="video_prompt",
            affected_artifacts=[baseline_path, path],
        )
    elif data.get("baseline_anchored") is not True:
        add(
            BLOCK,
            "后端跨集锁",
            path,
            f"{ep} 已存在 model_routes_baseline.json，但本集 video_model_routes.json 未标记 baseline_anchored=true。"
            "请重跑 n2d-model-router 让路由按跨集基线锚定，或写结构化 baseline_override（accepted/reviewer/reason/expires_at/affected_routes）。",
            return_to_stage="video_prompt",
            affected_artifacts=[baseline_path, path],
        )


def check_route_execution_recipe(route: Mapping[str, Any], routes_path: str, idx: int) -> None:
    clip_id = str(route.get("clip_id") or f"routes[{idx}]")
    recipe = route.get("execution_recipe")
    if not isinstance(recipe, Mapping):
        add(
            BLOCK,
            "执行配方",
            routes_path,
            f"{clip_id} 缺 execution_recipe；请重跑 n2d-model-router，让逐 Clip 路由输出可执行输入配方。",
            return_to_stage="video_prompt",
        )
        return
    required_sections = ("frame_inputs", "reference_inputs", "control_inputs", "audio_inputs", "fallback", "capability_match")
    for section in required_sections:
        if not isinstance(recipe.get(section), Mapping):
            add(BLOCK, "执行配方", routes_path, f"{clip_id} execution_recipe 缺结构块：{section}", return_to_stage="video_prompt")
    frame = recipe.get("frame_inputs") if isinstance(recipe.get("frame_inputs"), Mapping) else {}
    refs = recipe.get("reference_inputs") if isinstance(recipe.get("reference_inputs"), Mapping) else {}
    controls = recipe.get("control_inputs") if isinstance(recipe.get("control_inputs"), Mapping) else {}
    for key in ("first_frame", "consumption_mode", "native_timeline_frames"):
        if key not in frame or frame.get(key) in (None, ""):
            add(BLOCK, "执行配方", routes_path, f"{clip_id} execution_recipe.frame_inputs 缺字段：{key}", return_to_stage="video_prompt")
    for key in ("characters", "assets", "max_reference_images", "motion_reference"):
        if key not in refs:
            add(BLOCK, "执行配方", routes_path, f"{clip_id} execution_recipe.reference_inputs 缺字段：{key}", return_to_stage="video_prompt")
    if controls.get("required") is True and not controls.get("manifest_path"):
        add(BLOCK, "执行配方", routes_path, f"{clip_id} 需要 Motion Control 但 execution_recipe.control_inputs 缺 manifest_path", return_to_stage="video_prompt")


def check_video_model_routes(root: str, ep: str, overview_text: str, overview_path: str) -> None:
    if "本集模型路由表" not in overview_text:
        add(BLOCK, "模型路由", overview_path, "缺「本集模型路由表」；出视频必须先跑 n2d-model-router，不能固定一个视频模型或临场乱选后端")
    p = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    if not os.path.isfile(p):
        add(BLOCK, "模型路由", p, "缺 video_model_routes.json；先运行 `python3 skills/n2d-model-router/scripts/router.py <作品根> 第N集 --write`")
        return
    try:
        data = json.load(open(p, encoding="utf-8"))
    except Exception as exc:
        add(BLOCK, "模型路由", p, f"video_model_routes.json 解析失败：{exc}")
        return
    if data.get("kind") != VIDEO_MODEL_ROUTES_KIND:
        add(BLOCK, "模型路由", p, f"video_model_routes.json kind 必须是 {VIDEO_MODEL_ROUTES_KIND}")
    routes = data.get("routes")
    if not isinstance(routes, list) or not routes:
        add(BLOCK, "模型路由", p, "video_model_routes.json routes 为空；逐 Clip 必须有 primary/fallback/mode")
        return
    check_model_route_baseline_policy(root, ep, data, routes, p)
    drift = data.get("baseline_drift")
    if isinstance(drift, list) and drift:
        route_by_id = {str(r.get("clip_id") or ""): r for r in routes if isinstance(r, dict)}
        strict: List[object] = []
        for d in drift:
            route = route_by_id.get(str((d or {}).get("clip_id") or "")) if isinstance(d, dict) else None
            if route is None and isinstance(d, dict):
                route = {"shot_type": d.get("shot_type")}
            if isinstance(route, dict) and _route_needs_model_baseline(route) and not _baseline_override_accepted(data, route):
                strict.append(d)
        sample = "、".join(
            f"{d.get('clip_id')}({d.get('shot_type')}):{d.get('was')}→{d.get('now')}"
            for d in drift[:5] if isinstance(d, dict)
        )
        sev = BLOCK if strict else WARN
        add(
            sev,
            "后端跨集锁",
            p,
            f"{len(drift)} 个 clip 的 shot_type 自然路由与 设定库/model_routes_baseline 不符，已按基线锚定（原后端降 fallback）；"
            + ("高风险/含角色镜头的路由漂移必须写结构化 baseline_override（accepted/reviewer/reason/expires_at/affected_routes）或刷新基线后重跑。"
               if sev == BLOCK else "确认基线后端仍合适，否则 --write-baseline 刷新基线。")
            + sample,
            return_to_stage="video_prompt",
        )
    fallback_setting = get_setting(root, "视频备用后端", "").strip()
    allow_empty_fallback = (
        data.get("routing_mode") == "fixed_default"
        and bool(fallback_setting)
        and (fallback_setting.lower() in FALLBACK_OFF_VALUES or fallback_setting in FALLBACK_OFF_VALUES)
    )
    required = ("clip_id", "shot_type", "primary_backend", "fallback_backends", "mode", "native_audio_policy", "identity_requirement", "motion_control", "degrade_plan")
    frame_requirements = _storyboard_frame_requirements(root, ep)
    video_channel = get_setting(root, "生视频渠道", "").strip()
    check_video_backend_api_refresh(root, ep, routes, video_channel, p, allow_empty_fallback)
    for idx, route in enumerate(routes, 1):
        if not isinstance(route, dict):
            add(BLOCK, "模型路由", p, f"routes[{idx}] 不是对象")
            continue
        for key in required:
            if key == "fallback_backends" and route.get(key) == [] and allow_empty_fallback:
                continue
            if key not in route or route.get(key) in (None, "", []):
                add(BLOCK, "模型路由", p, f"{route.get('clip_id', f'routes[{idx}]')} 缺字段：{key}")
        if _identity_route_requires_character_refs(route) and not _route_clip_character_refs(route):
            clip_id = str(route.get("clip_id") or f"routes[{idx}]")
            add(
                BLOCK,
                "模型路由",
                p,
                f"{clip_id} identity_requirement={route.get('identity_requirement')} 但缺结构化 clip_characters[]；"
                "请重跑 n2d-model-router 生成逐镜角色绑定，避免 gate 无法判断本 clip 的真实身份锁范围。",
                return_to_stage="video_prompt",
            )
        flags = route.get("risk_flags")
        if isinstance(flags, list) and "long_duration" in flags:
            clip_id = str(route.get("clip_id") or f"routes[{idx}]")
            primary = str(route.get("primary_backend") or "")
            max_sec = route.get("max_clip_seconds") or video_backend_max_seconds(primary)
            add(
                BLOCK,
                "单Clip时长",
                p,
                f"{clip_id} 超出 primary 后端 {primary or 'unknown'} 单 Clip 上限 {max_sec}s；回 n2d-script 阶段2 拆 Clip，或重跑 n2d-model-router 选择支持更长单镜的后端后再出视频",
                return_to_stage="script_stage2",
                rerun_scope="按后端单 Clip 上限重切 storyboard.json clips[].duration / 接力契约，重跑 n2d-model-router 与 video_preflight；未过 gate 不出视频。",
                affected_artifacts=[
                    f"脚本/{ep}/storyboard.json",
                    f"出视频/{ep}/prompt/video_model_routes.json",
                    f"出视频/{ep}/prompt",
                ],
            )
        check_route_frame_capability(root, ep, route, p, idx, frame_requirements, video_channel)
        check_route_execution_recipe(route, p, idx)
        check_motion_control_route(root, ep, route, p, idx)
        check_action_choreography_route(route, p, idx)
        # ③ 一角一后端亲和：router 已尽力把核心角色硬钉到原生主体后端；剩余冲突多为同镜多个锁脸后端
        # 无法同时满足，需要拆镜/分区，核心冲突 BLOCK，非核心冲突 WARN。
        conflicts = route.get("character_backend_conflicts")
        if isinstance(conflicts, list) and conflicts:
            clip_id = str(route.get("clip_id") or f"routes[{idx}]")
            bits = "；".join(f"{c.get('character')} 原生主体在 {c.get('prefers_backend')}，本镜路由 {c.get('routed_backend')}"
                             for c in conflicts if isinstance(c, dict))
            sev = BLOCK if any(isinstance(c, dict) and (c.get("enforce") or c.get("core")) for c in conflicts) else WARN
            action = "必须拆正反打/分区让各核心角色走自己的原生后端，或重注册到同一后端" if sev == BLOCK else "拆正反打让该角色单独走其原生后端，或本镜改走该后端，或人工确认可接受"
            add(sev, "一角一后端", p,
                f"{clip_id} 跨集后端亲和冲突：{bits}。同角色跨集换后端→脸质感漂移；处理：{action}。",
                return_to_stage="video")


# 非原生锁绑定 = 仅靠参考组兜底/不支持（换后端会丢真正的锁脸力）。
_NON_NATIVE_BINDINGS = {"reference_group", "fallback_reference_group", "not_needed", "unsupported", ""}
_CORE_SCOPES = {"全篇", "长线", "核心", "主角"}


def check_route_identity_readiness(root: str, ep: str) -> None:
    """换后端丢锁机检：出视频路由用到的 primary/fallback 后端 × identity_adapter_matrix 的角色锁脸能力对账。

    n2d-model-router 选后端时不读 matrix——一个在后端 A 原生注册了 character_id 的角色，若某 clip 被路由到
    后端 B（B 上只有 reference_group 兜底甚至无绑定），锁脸力骤降却无任何机检。本检查在出视频闸门前置对账：
    - 角色在 matrix 有「原生锁」(ready 且 binding 非 reference_group 族)，但路由用到的某 primary/fallback 后端在该角色上
      只有 reference_group 兜底 → 换后端丢原生锁（核心角色 BLOCK / 其余 WARN）；该后端连兜底都没有 → 必丢锁 BLOCK；
    - 全 reference_group 兜底（无任何原生锁，如当前 demo）= 后端间一致，不报（没有原生锁可丢，避免噪声）。
    """
    routes_data = load_json(os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json"))
    matrix_p = identity_adapter_matrix_path(root)
    matrix = load_json(matrix_p)
    if not isinstance(routes_data, dict) or not isinstance(matrix, dict):
        return  # 缺路由/矩阵：check_video_model_routes / check_identity_adapter_matrix 各自把关
    routes = routes_data.get("routes")
    forms = matrix.get("forms")
    if not isinstance(routes, list) or not isinstance(forms, list):
        return
    used_roles: List[Tuple[str, str, str, Tuple[Tuple[str, str], ...]]] = []
    for r in routes:
        if not isinstance(r, dict):
            continue
        clip_id = str(r.get("clip_id") or "?")
        refs = tuple(
            (str(ref.get("character_id") or ""), str(ref.get("form") or ""))
            for ref in _route_clip_character_refs(r)
        )
        for role, backend in _video_route_backend_roles(r, allow_empty_fallback=False):
            if backend:
                used_roles.append((clip_id, role, backend, refs))
    seen_used: set[Tuple[str, str, str, Tuple[Tuple[str, str], ...]]] = set()
    used_roles = [item for item in used_roles if not (item in seen_used or seen_used.add(item))]
    if not used_roles:
        return
    for form in forms:
        if not isinstance(form, dict):
            continue
        form_cid = str(form.get("character_id") or form.get("id") or "").strip()
        form_name = str(form.get("form") or form.get("form_name") or "").strip()
        vb = form.get("video_bindings") if isinstance(form.get("video_bindings"), dict) else {}
        native = sorted(b for b, v in vb.items()
                        if isinstance(v, dict) and v.get("ready")
                        and str(v.get("binding") or "") not in _NON_NATIVE_BINDINGS)
        if not native:
            continue  # 无原生锁 → 全兜底，后端间一致，无锁可丢
        name = form.get("character_name") or form.get("character_id") or "?"
        sev = BLOCK if str(form.get("scope") or "").strip() in _CORE_SCOPES else WARN
        for clip_id, role, b, refs in used_roles:
            if refs:
                matched = False
                for cid, ref_form in refs:
                    if cid != form_cid:
                        continue
                    if ref_form and form_name and ref_form != form_name:
                        continue
                    matched = True
                    break
                if not matched:
                    continue
            if b in native:
                continue
            v = vb.get(b)
            role_note = "fallback" if role == "fallback" else "primary"
            if not (isinstance(v, dict) and v.get("ready")):
                add(BLOCK, "换后端丢锁", matrix_p,
                    f"角色「{name}」已在 {native} 原生锁脸，但 {clip_id} 的 {role_note} 后端 {b} 无可用身份绑定（连 reference_group 兜底都没有）→ 必丢锁；改路由到 {native} 或先在 {b} 注册该角色身份",
                    return_to_stage="video_prompt",
                    rerun_scope=f"重跑 n2d-model-router 把涉及「{name}」的 clip primary/fallback 都约束到 {native}，或在 {b} 注册 character_id/face_lock 后再出视频。",
                    affected_artifacts=[f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/identity_adapter_matrix.json"])
            elif str(v.get("binding") or "") in _NON_NATIVE_BINDINGS:
                add(sev, "换后端丢锁", matrix_p,
                    f"角色「{name}」已在 {native} 原生锁脸，但 {clip_id} 的 {role_note} 后端 {b} 仅 reference_group 兜底 = 换后端丢原生锁、锁脸力下降；核心角色 primary 与 fallback 都应改路由或在 {b} 注册原生身份",
                    return_to_stage="video_prompt",
                    rerun_scope=f"重跑 n2d-model-router 让「{name}」的 clip primary/fallback 优先用 {native}，或在 {b} 注册原生身份；不能让失败重试时 fallback 偷偷掉锁。",
                    affected_artifacts=[f"出视频/{ep}/prompt/video_model_routes.json"])


def _motion_control_required_for_route(route: Dict[str, object]) -> bool:
    # 判定与 router 同源（n2d_contract.motion_control_required），避免两边对"需控制契约"的认定漂移
    flags = route.get("risk_flags")
    return motion_control_required(
        shot_type=route.get("shot_type"),
        risk_flags=flags if isinstance(flags, list) else None,
    )


def _resolve_under_root(root: str, path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(root, path)


def _uri_like(value: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9+.-]*://", value.strip(), flags=re.I))


def _uri_scheme(value: str) -> str:
    m = re.match(r"^([a-z][a-z0-9+.-]*)://", value.strip(), flags=re.I)
    return m.group(1).lower() if m else ""


def _sequence_pattern_to_glob(value: str) -> str:
    text = re.sub(r"%0?\d*d", "*", value)
    return re.sub(r"#+", "*", text)


def _verified_remote_control_input(value: dict) -> bool:
    uri = str(value.get("uri") or "").strip()
    if _uri_scheme(uri) not in {"https", "s3", "gs"}:
        return False
    if not _valid_iso_date(value.get("verified_at")):
        return False
    return any(str(value.get(key) or "").strip() for key in ("sha256", "checksum", "etag"))


def _control_asset_exists(root: str, value: str, *, explicit_glob: bool = False) -> bool:
    text = value.strip()
    if not text:
        return False
    if _uri_like(text):
        return False
    pattern = _sequence_pattern_to_glob(text)
    has_glob = explicit_glob or pattern != text or any(ch in pattern for ch in "*?[]")
    full = _resolve_under_root(root, pattern)
    if has_glob:
        return bool(glob.glob(full))
    return os.path.exists(full)


def _input_ready(root: str, value: object) -> bool:
    if isinstance(value, str):
        return _control_asset_exists(root, value)
    if isinstance(value, dict):
        status = str(value.get("status") or "ready").strip()
        if status not in MOTION_CONTROL_READY_INPUT_STATUSES:
            return False
        if status == "not_needed":
            return True
        uri = str(value.get("uri") or "").strip()
        if uri:
            return _verified_remote_control_input(value)
        glob_value = str(value.get("glob") or "").strip()
        if glob_value:
            return _control_asset_exists(root, glob_value, explicit_glob=True)
        return _control_asset_exists(root, str(value.get("path") or ""))
    return False


def check_motion_control_manifest(root: str, path: str, route: Dict[str, object], required_inputs: List[str]) -> None:
    data = load_json(path)
    loc = path
    if not isinstance(data, dict):
        add(BLOCK, "Motion Control", loc, "motion_control_manifest.json 不是 JSON 对象")
        return
    if data.get("kind") != MOTION_CONTROL_KIND:
        add(BLOCK, "Motion Control", loc, f"motion_control_manifest.json kind 必须是 {MOTION_CONTROL_KIND}")
    status = str(data.get("status") or "").strip()
    if status not in MOTION_CONTROL_READY_STATUSES:
        add(BLOCK, "Motion Control", loc, "status 必须是 ready 或 degrade_only；planned/pending 不能进入付费出视频")
        return
    route_clip_id = str(route.get("clip_id") or "").strip()
    manifest_clip_id = str(data.get("clip_id") or "").strip()
    if manifest_clip_id and route_clip_id and manifest_clip_id != route_clip_id:
        add(BLOCK, "Motion Control", loc, f"clip_id={manifest_clip_id} 与路由 {route_clip_id} 不一致")
    if status == "degrade_only":
        if _field_is_missing(data, "degrade_plan"):
            add(BLOCK, "Motion Control", loc, "status=degrade_only 时必须写 degrade_plan，明确拆手部/反打/释放帧等降级执行")
        return

    inputs = data.get("control_inputs")
    if not isinstance(inputs, dict):
        add(BLOCK, "Motion Control", loc, "status=ready 时必须有 control_inputs 对象")
        return
    for key in required_inputs:
        if key not in inputs or not _input_ready(root, inputs.get(key)):
            add(BLOCK, "Motion Control", loc, f"ready manifest 缺可用控制输入或本地资产：control_inputs.{key}")
    if _route_requires_contact_fields(route):
        for key in MOTION_CONTROL_CONTACT_FIELDS:
            if _field_is_missing(data, key):
                add(BLOCK, "Motion Control", loc, f"高危物理接触 manifest 缺字段：{key}")
    if _field_is_missing(data, "failure_modes"):
        add(WARN, "Motion Control", loc, "建议写 failure_modes：feature_melting / limb_fusion / body_interpenetration 等，方便审片回流")


def check_motion_control_route(root: str, ep: str, route: Dict[str, object], routes_path: str, idx: int) -> None:
    loc = f"{routes_path} {route.get('clip_id', f'routes[{idx}]')}"
    motion = route.get("motion_control")
    if not isinstance(motion, dict):
        add(BLOCK, "Motion Control", loc, "缺 motion_control 对象；重新跑 n2d-model-router 生成可审计控制契约")
        return
    for key in MOTION_CONTROL_ROUTE_FIELDS:
        if key not in motion:
            add(BLOCK, "Motion Control", loc, f"motion_control 缺字段：{key}")

    requires_control = _motion_control_required_for_route(route)
    if not requires_control:
        return
    if motion.get("level") != "required" or motion.get("required") is not True or motion.get("manifest_required") is not True:
        add(BLOCK, "Motion Control", loc, "高危动作/物理镜头必须 motion_control.level=required 且 manifest_required=true")
    manifest_path = str(motion.get("manifest_path") or "").strip()
    if not manifest_path:
        add(BLOCK, "Motion Control", loc, "高危动作/物理镜头缺 motion_control.manifest_path")
        return
    abs_manifest = _resolve_under_root(root, manifest_path)
    if not os.path.isfile(abs_manifest):
        add(BLOCK, "Motion Control", abs_manifest, "缺 motion_control_manifest.json；必须先准备 ready 控制资产，或写 status=degrade_only 的拆镜 manifest")
        return
    required_inputs = motion.get("required_inputs") if isinstance(motion.get("required_inputs"), list) else []
    check_motion_control_manifest(root, abs_manifest, route, [str(item) for item in required_inputs])


def check_action_choreography_route(route: Dict[str, object], routes_path: str, idx: int) -> None:
    shot_type = str(route.get("shot_type") or "").strip()
    if shot_type not in ACTION_CHOREOGRAPHY_SHOT_TYPES:
        return
    loc = f"{routes_path} {route.get('clip_id', f'routes[{idx}]')}"
    choreography = route.get("action_choreography")
    if not isinstance(choreography, dict):
        add(BLOCK, "动作编排", loc, "高动作镜头缺 action_choreography 对象；重跑 n2d-model-router 生成动作编排契约")
        return
    if choreography.get("required") is not True:
        add(BLOCK, "动作编排", loc, "高动作镜头 action_choreography.required 必须为 true")
    for key in ("required_fields", "failure_modes", "gate_policy", "degrade_plan"):
        if key == "degrade_plan":
            if _field_is_missing(route, "degrade_plan") and _field_is_missing(choreography, "degrade_plan"):
                add(BLOCK, "动作编排", loc, "动作编排缺 degrade_plan；失败后必须有拆镜/降级路径")
            continue
        if _field_is_missing(choreography, key):
            add(BLOCK, "动作编排", loc, f"action_choreography 缺字段：{key}")
    declared = set(str(x) for x in choreography.get("required_fields", []) if str(x).strip()) if isinstance(choreography.get("required_fields"), list) else set()
    missing = [field for field in _action_choreography_required_fields(shot_type) if field not in declared]
    if missing:
        add(BLOCK, "动作编排", loc, "action_choreography.required_fields 缺字段：" + ", ".join(missing))


def check_image_prompt_overview(root: str, ep: str) -> None:
    """Image overview must carry the episode-level visual contract.

    The image stage is where visual variables get baked into pixels (color,
    light position, axis/eyeline, character state, shot-size ladder).  Anything
    the video stage cannot change must be decided here, in the overview, before
    any paid image call — mirroring the video stage's director contract so the
    two contracts share one source instead of being re-invented downstream.
    """
    p = os.path.join(root, "出图", ep, "prompt", "00_总览.md")
    if not os.path.isfile(p):
        # 总览缺失由 check_shared_image_index 单独阻断，这里只管契约内容，避免重复报错
        return
    text = open(p, encoding="utf-8").read()
    if "本集视觉一致性契约" not in text:
        add(BLOCK, "视觉契约", p, "缺「本集视觉一致性契约」；像素层导演决策（色调/光位/轴线/状态/景别）必须在出图总览先锁，不能下推到出视频")
        return
    for key in ("色调基线", "光位锚", "轴线", "状态演进", "景别阶梯"):
        if key not in text:
            add(BLOCK, "视觉契约", p, f"本集视觉一致性契约缺字段：{key}")
    check_markdown_style_contract(text, p, "出图总览")


def check_video_clip_prompt_section(path: str, section: str, route: Optional[Dict[str, Any]] = None) -> None:
    name = _headline(section, "Clip")
    loc = f"{path} {name}"

    required_fields = (
        ("导演意图", "缺导演意图；每条视频 prompt 必须先说明本镜剧情功能和为什么这样拍"),
        ("起幅", "缺起幅；必须写清从首帧/上一 Clip 接什么姿态、视线、道具和场景状态开始"),
        ("落幅", "缺落幅；必须写清结尾停到哪里，服务下一镜怎么切"),
        ("场面调度", "缺场面调度；必须锁人物左右站位、轴线、前后景或无人物的画面重心"),
        ("表演节拍", "缺表演节拍；必须按时间段写人物/光效/环境的节拍，不能只有静态动作"),
        ("运动精修", "缺运动精修；必须写幅度/能量/身体守卫，避免视频模型把近景脸、手部和肢体拉变形"),
        ("环境交互", "缺环境交互；必须写动作对光影/粒子/道具/背景的反馈，避免视频只做静态缩放"),
    )
    for label, msg in required_fields:
        if not _has_field(section, label):
            add(BLOCK, "导演调度", loc, msg)

    if "衔接设计" not in section:
        add(BLOCK, "导演调度", loc, "缺衔接设计；视频 prompt 必须继承故事板接力契约")
    if "continuity" not in section:
        add(BLOCK, "导演调度", loc, "缺 continuity 块；start/action/end/constraints/negative 无法被校验")
    for key in ("start_state", "action", "end_state", "constraints", "negative"):
        if key not in section:
            add(BLOCK, "导演调度", loc, f"continuity 缺字段：{key}")

    if "视频 prompt（中文" not in section:
        add(BLOCK, "prompt", loc, "缺视频 prompt（中文）")
    if "视频 prompt（英文" not in section:
        add(BLOCK, "prompt", loc, "缺视频 prompt（英文）兜底")
    for key in ("运动精修约束", "环境交互约束", "人物运动", "镜头运动", "动态细节", "衔接约束", "声音约束"):
        if key not in section:
            add(BLOCK, "prompt", loc, f"中文视频 prompt 缺字段：{key}")
    if "角色身份注册层" not in section:
        add(BLOCK, "资产身份注册层", loc, "缺角色身份注册层字段；含角色镜必须继承 identity_registry.json，无人物镜写“无”")
    if not _has_line_field(section, "身份锁定约束"):
        add(BLOCK, "资产身份注册层", loc, "中文视频 prompt 缺身份锁定约束；必须写明 Character ID/Face Lock/reference controls 或 fallback reference_group")
    closeup_identity_risk = (
        "角色身份注册层" in section
        and not _has_any(section, ("角色身份注册层**：无", "角色身份注册层**： 无", "无人物", "空镜"))
        and _has_any(section, ("mouth_visible", "dialogue_closeup", "dialogue_shot_reverse", "CU", "MCU", "近景", "特写", "反打", "表情", "脸"))
    )
    if closeup_identity_risk:
        if not _has_any(section, ("近景/反打身份锁定", "近景身份锁定", "细粒度身份锁定")):
            add(
                BLOCK,
                "资产身份注册层",
                loc,
                "近景/反打/说话镜缺细粒度身份锁定；必须写脸型、五官比例、发型发髻、标志配饰、服装配色和脸部特写/表情参考或降级方案",
            )
        if "近景身份锁定约束" not in section:
            add(BLOCK, "资产身份注册层", loc, "中文视频 prompt 缺近景身份锁定约束；配角近景需限制低幅度表情/转头，必要时降级 MCU/OTS/侧脸")
        if not _has_any(section, ("脸型", "五官", "发型", "发髻")):
            add(BLOCK, "资产身份注册层", loc, "近景身份锁定未写脸型/五官/发型发髻等不可漂项")
        if not _has_any(section, ("脸部特写", "表情参考", "expressions", "正脸", "front", "reference_group")):
            add(WARN, "资产身份注册层", loc, "近景身份锁定未明确脸部特写/表情参考或 reference_group 来源；配角近景容易漂移")
    if not _has_field(section, "模型路由"):
        add(BLOCK, "模型路由", loc, "缺模型路由字段；每 Clip 必须继承 video_model_routes.json 的 shot_type/primary/fallback/mode/degrade_plan")
    else:
        for key in ("shot_type", "primary_backend", "fallback", "mode", "degrade_plan"):
            if key not in section:
                add(BLOCK, "模型路由", loc, f"模型路由缺字段：{key}")
        has_character_identity_layer = (
            "角色身份注册层" in section
            and not _has_any(section, ("角色身份注册层**：无", "角色身份注册层**： 无", "无人物", "空镜"))
            and bool(re.search(r"\bCHAR_[A-Za-z0-9_]+(?:/[^`\s，；、*]+)?\*?\b", section))
        )
        if has_character_identity_layer and re.search(r"identity_requirement\s*=\s*none\b", section):
            add(
                BLOCK,
                "模型路由",
                loc,
                "模型路由 identity_requirement=none 但本 Clip 写了角色身份注册层/CHAR_xx；必须改为 reference_group 或后端原生身份绑定，避免执行端少传身份参考。",
            )
    if "模型路由约束" not in section:
        add(BLOCK, "模型路由", loc, "中文视频 prompt 缺模型路由约束；必须说明按 primary_backend 写平台参数，失败才切 fallback/degrade_plan")
    shot_type = _section_shot_type(section, route)
    if shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES:
        if not (_has_field(section, "动作编排契约") or _has_field(section, "Action Choreography")):
            add(
                BLOCK,
                "动作编排",
                loc,
                "打斗/追逐/飞行等高动作镜头缺「动作编排契约」；必须写 beats、speed_curve、spatial_path、camera_path、readability_beats 及该镜专属字段，不能只写“精彩打斗/高速飞行”。",
            )
        else:
            missing = _missing_contract_fields(section, _action_choreography_required_fields(shot_type))
            if missing:
                add(BLOCK, "动作编排", loc, "动作编排契约缺字段：" + ", ".join(missing))
        if "动作编排约束" not in section:
            add(BLOCK, "动作编排", loc, "中文视频 prompt 缺动作编排约束；必须说明速度曲线、空间路径、镜头路径、可读性节拍和失败降级。")
        if not _has_any(section, ("动作编排", "Action Choreography", "readability_beats")):
            add(BLOCK, "动作编排", loc, "生成后自检必须包含动作编排/可读性检查项，确认动作方向、速度曲线、空间路径和命中/距离/高度落点。")
    if _section_requires_motion_control(section):
        if not (_has_field(section, "Motion Control") or _has_field(section, "物理交互控制")):
            add(BLOCK, "Motion Control", loc, "高危动作/物理镜头缺 Motion Control / 物理交互控制字段；必须继承 route.motion_control 和 manifest_path")
        else:
            for key in ("level", "manifest_path", "required_inputs", "failure_modes"):
                if key not in section:
                    add(BLOCK, "Motion Control", loc, f"物理交互控制字段缺：{key}")
        if "物理交互约束" not in section:
            add(BLOCK, "Motion Control", loc, "中文视频 prompt 缺物理交互约束；必须说明姿态/深度/实例遮挡或按 degrade_plan 拆镜")
        if not _has_any(section, ("FeatureMelting", "feature_melting", "特征融化")):
            add(BLOCK, "Motion Control", loc, "生成后自检必须包含 FeatureMelting/特征融化检查项")
    if "原生音画策略" not in section:
        add(BLOCK, "原生音画", loc, "缺原生音画策略字段；每 Clip 必须写 audio_intent/risk/mouth_visible/speech_policy/compose_policy，默认丢弃")
    else:
        for key in ("audio_intent", "risk", "mouth_visible", "speech_policy", "compose_policy"):
            if key not in section:
                add(BLOCK, "原生音画", loc, f"原生音画策略缺字段：{key}")
        route_native_policy = str((route or {}).get("native_audio_policy") or "").strip()
        route_mode = str((route or {}).get("mode") or "").strip()
        if route_native_policy == "native_speech" or route_mode == "native_av":
            policy_line = _native_audio_policy_line(section)
            if "native_speech" not in policy_line:
                add(BLOCK, "原生音画", loc, "路由表 native_audio_policy=native_speech，但本 Clip 原生音画策略未写 speech_policy=native_speech")
            if _has_any(policy_line, ("no_native_speech", "禁止原生人声", "无原生人声")):
                add(BLOCK, "原生音画", loc, "路由表要求 native_speech，说话镜不能同时写 no_native_speech / 禁止原生人声；应改为台词+口型由原生音画后端生成并由 compose 保留原片音轨")
            if not _has_any(policy_line, ("audio_intent=native_speech", "台词", "原生人声")):
                add(WARN, "原生音画", loc, "native_speech 镜建议写 audio_intent=native_speech，并说明台词文本/声源/口型策略")
            if not _has_any(policy_line, ("compose_policy=保留原片音轨", "保留原片音轨")):
                add(BLOCK, "原生音画", loc, "native_speech 镜 compose_policy 必须保留原片音轨；否则合成会丢原生台词")
        elif route_native_policy and route_native_policy != "native_speech":
            policy_line = _native_audio_policy_line(section)
            if "native_speech" in policy_line or "allow_native_speech" in policy_line:
                add(BLOCK, "原生音画", loc, f"路由表 native_audio_policy={route_native_policy}，本 Clip 不得写 native_speech/allow_native_speech")
        if _section_native_audio_opt_in(section) and route_native_policy != "native_speech" and route_mode != "native_av":
            native_policy = _native_audio_policy_line(section)
            if not _has_any(section, ("risk=low", "低风险")):
                add(BLOCK, "原生音画", loc, "原生环境声/音效 opt-in 仅允许低风险镜头；必须写 risk=low / 低风险理由")
            if not _has_any(native_policy, ("mouth_visible=no", "无口型", "嘴部不可见")):
                add(BLOCK, "原生音画", loc, "原生环境声/音效 opt-in 必须确认无口型或嘴部不可见")
            if not _native_audio_contract_ok(section):
                add(BLOCK, "原生音画", loc, "原生环境声/音效 opt-in 必须明确 no_native_speech / 禁止原生人声")
    if "原生音画约束" not in section:
        add(BLOCK, "原生音画", loc, "中文视频 prompt 缺原生音画约束；必须说明默认禁止原生人声，或仅允许低风险环境声/动作音效")
    elif route and (
        str(route.get("native_audio_policy") or "").strip() == "native_speech"
        or str(route.get("mode") or "").strip() == "native_av"
    ):
        if not _has_any(section, ("台词", "口型", "native_speech", "保留原片音轨")):
            add(BLOCK, "原生音画", loc, "native_speech 镜的中文原生音画约束必须说明台词、口型和保留原片音轨")

    # ④ 运镜越界 trip-wire：镜头运动含"廉价漂浮/旋转飞行/急速"类运镜 → 疑越 style_contract.运动边界
    m_cam = re.search(r"镜头运动[：:]([^\n；;]*)", section)
    cam = m_cam.group(1) if m_cam else ""
    SUSPECT_MOVES = ("旋转", "360", "环绕飞", "飞行", "急速", "极速", "快速拉近", "急推", "急拉", "乱甩", "甩镜", "螺旋", "翻滚")
    hit = [w for w in SUSPECT_MOVES if w in cam]
    if hit:
        add(WARN, "运动一致性", loc,
            f"镜头运动含「{'/'.join(hit)}」，疑越本集运动边界——核对 `本集基础视觉风格契约/导演一致性契约` 的运动边界禁忌；如确需该运镜须有明确剧情理由（爽点/高光），否则换克制运镜")

    # ⑤ 运镜结构化（消费 CAMERA_MOVE_LEXICON·治"运镜全是自由散文、丢速度/方向"）：
    #    运镜是 2026 一等控制项（Seedance 参考视频运动 / Kling motion-control 端点）。WARN-only，不硬挡。
    if m_cam and cam.strip():
        cm = normalize_camera_move(cam)
        if not cm["recognized"]:
            add(WARN, "运动一致性", loc,
                "镜头运动未用结构化运镜词（推/拉/摇/移/升降/变焦/环绕/跟拍/甩镜/弧线/手持/固定…）：运镜是传达情绪与节奏"
                "最强的工具，自由散文下游模型常乱给。请从 CAMERA_MOVE_LEXICON 取词，运镜服务情绪（逼近=推近/释放=拉远/"
                "高光=环绕/压迫=固定），并填速度+方向 slot。")
        elif cm["moves"] and not cm["speeds"] and not cm["is_static"]:
            add(WARN, "运动一致性", loc,
                f"镜头运动「{'/'.join(m['zh'] for m in cm['moves'])}」缺速度档（缓慢/匀速/快速/轻微/急速冲击）："
                "运镜速度直接决定情绪与节奏感，请补速度词（CAMERA_SPEED_WORDS）。")

    if "检查清单（视频三件套自查" not in section:
        add(BLOCK, "prompt", loc, "缺提交前检查清单")
    if "自检（生成后逐条过" not in section:
        add(BLOCK, "prompt", loc, "缺生成后自检段")


def _reference_block(section: str) -> str:
    m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^\*\*导演视角八维\*\*|^##\s+|\Z)", section)
    return m.group(0) if m else ""


def _section_has_character_refs(section: str) -> bool:
    refs = _reference_block(section)
    if "清空人物参考" in refs or "无需人物参考" in refs or "无人物" in section or "空镜" in section:
        return False
    # 场景/道具/VFX 纯空镜可没有角色锚点；含角色语义或人物定妆引用才按角色镜头卡。
    if _has_any(section, ("角色", "人物", "脸", "脸型", "发型", "服装", "妆造", "锚点句", "同一少女", "同一少年")):
        return True
    asset_names = re.findall(r"定妆_([^`\s，。、,）)]+)", refs)
    non_character_words = (
        "场景", "道具", "寝殿", "宫", "殿", "庭", "院", "山", "洞", "门", "廊",
        "床", "榻", "托盘", "光幕", "符纹", "剑气", "法宝", "特效", "阵", "丹炉",
        "雷", "火", "云", "光效", "地标",
    )
    return any(not _has_any(name, non_character_words) for name in asset_names)


def _character_names_in_refs(refs: str) -> set:
    """参考图块里引用的**角色**定妆基名集合（去形态变体后缀、排除场景/道具/特效）。"""
    non_char = (
        "场景", "道具", "寝殿", "宫", "殿", "庭", "院", "山", "洞", "门", "廊", "道",
        "床", "榻", "托盘", "光幕", "符纹", "剑气", "法宝", "特效", "阵", "丹炉", "炉",
        "雷", "火", "云", "光效", "地标", "花田", "花", "米饼", "灯", "剪影",
    )
    names = set()
    for raw in re.findall(r"定妆_([^`\s，。、,）)]+)", refs):
        if raw.endswith(".png"):
            raw = raw[:-4]
        base = re.sub(
            r"_(侧|半身|全身|背|三视图|设定表|表情|脸部特写|头部特写|面部特写|局部|近景|特写)$",
            "",
            raw,
        )
        if base and not _has_any(base, non_char):
            names.add(base)
    return names


def _needs_closeup_identity_lock(section: str, name: str) -> bool:
    """Reaction/reverse-shot close-ups need finer identity locks than generic anchors.

    Plain reference-group generation often preserves a character *type* but
    redraws face shape, hair bun, or accessories in tight reaction shots.  Keep
    this check scoped to dialogue/reaction close-ups so ordinary medium shots
    are not over-gated.
    """
    focused_lines = "\n".join(
        line for line in section.splitlines()
        if _has_any(line, ("专项镜头模板", "镜头", "①", "template", "shot_type", "导演意图"))
    )
    blob = f"{name}\n{focused_lines}"
    return _has_any(blob, (
        "dialogue_shot_reverse",
        "正反打",
        "反打",
        "过肩",
        "反应镜",
        "表情镜",
        "逼问",
        "假面",
    ))


def _has_closeup_identity_lock(section: str) -> bool:
    has_lock_field = _has_any(section, (
        "近景/反打身份锁定",
        "近景身份锁定",
        "反打身份锁定",
        "细粒度身份锁定",
        "脸部特写",
        "_表情",
    ))
    has_face_detail = _has_any(section, ("脸型", "五官比例", "圆润脸", "窄长", "薄唇", "眼型"))
    has_hair_detail = _has_any(section, ("发型", "发髻", "高圆髻", "发簪", "发饰", "配饰", "头饰"))
    return has_lock_field and has_face_detail and has_hair_detail


def _has_i2i_tail_continuity_lock(section: str) -> bool:
    has_method = _has_any(section, (
        "image2image",
        "image-to-image",
        "图生图",
        "母图",
        "同镜首帧",
        "上一张成图",
        "上一帧成图",
        "前一张成图",
        "尾帧接力生成方式",
    ))
    forbids_text_only = _has_any(section, (
        "不得纯文生图",
        "禁止纯文生图",
        "不纯文生图",
        "不要纯文重抽",
        "不能纯文字重抽",
        "不得纯文字重抽",
    ))
    return has_method and forbids_text_only


# 无持久角色 ID 后端（Codex/OpenAI/Dreamina/Nano）逐镜重画脸——不仅尾帧，**每个**角色镜（含首帧）
# 都必须从共享定妆 image2image / 多图参考派生，否则纯文重抽=跨集换演员。判定走声明的生成方式。
I2I_DERIVATION_MARKERS = (
    "image2image",
    "image-to-image",
    "img2img",
    "i2i",
    "图生图",
    "母图",
    "多图参考派生",
    "参考派生",
    "参考图派生",
    "以定妆",
    "基于定妆",
    "定妆图为底",
    "定妆为母图",
)


def _has_i2i_derivation(section: str) -> bool:
    """本镜是否声明从共享定妆 image2image / 多图参考派生（而非纯文生图）。纯函数·可测。"""
    return _has_any(section, I2I_DERIVATION_MARKERS)


CODEX_FACE_REFERENCE_MARKERS = (
    "脸部特写",
    "面部特写",
    "头部特写",
    "表情库",
    "expressions",
    "表情参考",
    "表情_",
    "_表情",
    "情绪库",
    "微表情参考",
)

CODEX_STRONG_EXPRESSION_MARKERS = (
    "大表情",
    "哭",
    "泣",
    "落泪",
    "含泪",
    "怒",
    "暴怒",
    "狂怒",
    "震惊",
    "惊恐",
    "恐惧",
    "大笑",
    "狂笑",
    "嘶吼",
    "咆哮",
    "痛苦",
    "崩溃",
    "狰狞",
    "扭曲",
    "癫狂",
    "失控",
    "绝望",
    "悲恸",
    "惊愕",
)

CODEX_DARK_VFX_FACE_RISK_MARKERS = (
    "暗光",
    "深暗",
    "深阴影",
    "黑烟",
    "烟雾",
    "浓雾",
    "遮脸",
    "遮住脸",
    "法术特效",
    "特效压脸",
    "脸上叠特效",
    "血光",
    "红纱",
    "金光爆发",
    "黑气",
    "雾化",
)

CODEX_FACE_VISIBILITY_GUARDS = (
    "眼鼻嘴三角区",
    "不遮住眼鼻嘴",
    "不得遮住眼鼻嘴",
    "脸部不被遮挡",
    "脸不被遮挡",
    "特效不遮脸",
    "黑烟不得遮脸",
    "烟雾不得遮脸",
    "保留五官",
    "不重画脸",
    "特效只叠在脸外侧",
    "VFX只叠在脸外侧",
    "五官清晰可见",
)

CODEX_SPLIT_COMPOSITE_MARKERS = (
    "split_composite_required",
    "split_composite",
    "regional_construct_required",
    "regional_construct",
    "分别出图+合成",
    "分别出图 + 合成",
    "分角色出图+合成",
    "分角色出图 + 合成",
    "分区构建",
    "分区逐次构建",
    "区域构建",
    "regional-prompt",
    "region masks",
    "empty_plate",
    "拆成单人镜",
    "拆单人镜",
    "单人分层出图",
    "分层合成",
    "登记降级",
)

CODEX_CONDITIONAL_SPLIT_MARKERS = (
    "若多主体仍不稳",
    "若多人仍不稳",
    "如果多主体仍不稳",
    "如果多人仍不稳",
    "不稳再",
    "仍不稳再",
    "必要时再",
    "需要时再",
)

GENERIC_REFERENCE_INDEX_MARKERS = (
    "参考图①",
    "参考图1",
    "reference image 1",
    "ref image 1",
)

NATIVE_MULTI_SUBJECT_STRATEGY_MARKERS = (
    "主体库",
    "角色ID",
    "角色 ID",
    "Character ID",
    "persistent subject",
    "原生主体",
    "多主体",
    "区域绑定",
    "画面区域绑定",
    "Universal Reference",
    "Seedream",
    "可灵",
    "Kling",
    "Sora Cameo",
    "Nano Banana",
    "多参考",
)

MULTI_SUBJECT_SLOT_MARKERS = (
    "多人同框身份槽位",
    "身份槽位",
    "LEFT_SLOT",
    "RIGHT_SLOT",
    "FOREGROUND_SLOT",
    "BACKGROUND_SLOT",
    "EXTRA_SLOT",
    "画左槽",
    "画右槽",
    "前景槽",
    "后景槽",
)

MULTI_SUBJECT_EXECUTION_STRATEGY_MARKERS = (
    "多人同框执行策略",
    "multi_subject_strategy",
    "native_subject_slots",
    "regional_construct_required",
    "split_composite_required",
    "register_subjects_or_split",
    "shot_reverse_shot",
)

MULTI_SUBJECT_POSITION_MARKERS = (
    "画左",
    "画右",
    "左侧",
    "右侧",
    "前景",
    "后景",
    "前后景",
    "screen_position",
    "screen positions",
    "blocking",
)


def _codex_needs_face_reference(section: str, name: str) -> bool:
    """Codex-like backends re-solve the face per shot; closeups/large expressions need face refs."""
    closeup_or_reaction = _needs_closeup_identity_lock(section, name) or _has_any(
        section,
        ("ECU", "BCU", "CU", "MCU", "近景", "特写", "面部", "脸部", "反打", "过肩", "表情镜", "反应镜"),
    )
    return closeup_or_reaction and _has_any(section, CODEX_STRONG_EXPRESSION_MARKERS + ("正反打", "反打", "过肩", "反应镜", "表情镜"))


def _codex_has_face_reference(section: str) -> bool:
    return _has_any(section, CODEX_FACE_REFERENCE_MARKERS)


def _codex_dark_vfx_face_risk(section: str, name: str) -> bool:
    closeup_or_face = _needs_closeup_identity_lock(section, name) or _has_any(section, ("CU", "MCU", "近景", "特写", "脸", "面部"))
    return closeup_or_face and _has_any(section, CODEX_DARK_VFX_FACE_RISK_MARKERS)


def _codex_has_face_visibility_guard(section: str) -> bool:
    return _has_any(section, CODEX_FACE_VISIBILITY_GUARDS)


def _has_codex_split_composite_strategy(section: str) -> bool:
    if not _has_any(section, CODEX_SPLIT_COMPOSITE_MARKERS):
        return False
    # “若不稳再分层”只是口头兜底，不是执行策略。Codex/OpenAI/Dreamina/Nano/Gemini
    # 这类无持久主体 ID 后端下，多角色同框必须在 prompt 中把分层/合成登记成硬执行。
    return not _has_any(section, CODEX_CONDITIONAL_SPLIT_MARKERS)


def _has_generic_reference_index_lock(section: str) -> bool:
    return _has_any(section.lower(), GENERIC_REFERENCE_INDEX_MARKERS)


def _has_native_multi_subject_strategy(section: str) -> bool:
    return _has_any(section, NATIVE_MULTI_SUBJECT_STRATEGY_MARKERS + CODEX_SPLIT_COMPOSITE_MARKERS + MULTI_SUBJECT_EXECUTION_STRATEGY_MARKERS)


def _has_multi_subject_identity_slots(section: str) -> bool:
    """多人同框必须把每个身份绑定到画面槽位；只写多张参考图或中文名不算。"""
    if not _has_any(section, MULTI_SUBJECT_SLOT_MARKERS):
        return False
    ids = {m.split("/")[0].rstrip("*") for m in re.findall(r"CHAR_[A-Za-z0-9_]+(?:/[^\s`；;，,]*)?", section)}
    if len(ids) < 2:
        return False
    return _has_any(section, MULTI_SUBJECT_POSITION_MARKERS)


def _has_character_id_binding(section: str) -> bool:
    """Character shots must bind concrete registry IDs, not just prose names."""
    return bool(re.search(r"`?CHAR_[A-Za-z0-9_]+/[^`\s；;，,]+`?", section))


def _has_character_aesthetic_baseline(section: str) -> bool:
    """人物镜默认要写审美基线；只做 WARN，避免误伤特殊丑化/怪异角色。"""
    return _has_any(section, (
        "人物审美基线",
        "审美基线",
        "主流审美",
        "镜头友好",
        "可播审美",
        "精致好看",
        "好看但不",
        "五官协调",
        "五官清晰",
        "脸部比例协调",
        "camera-friendly",
        "appealing",
        "attractive",
    ))


def _multi_char_binding_ambiguity(section: str) -> Optional[List[str]]:
    """同框 ≥2 个注册角色但未星标 primary（`CHAR_xx*`）→ 返回角色 ID 列表；否则 None。

    多数后端单图主体锁只支持 1 个主体——不声明锁谁=后端随机挑，同框崩脸不可追责。
    规则出处：n2d-image/references/资产身份注册层.md「多角色同框绑定规则」。纯函数·可测。
    """
    ids = sorted({m.split("/")[0].rstrip("*") for m in re.findall(r"CHAR_[A-Za-z0-9_]+(?:/[^\s`；;，,]*)?", section)})
    if len(ids) < 2:
        return None
    if re.search(r"CHAR_[A-Za-z0-9_]+(?:/[^\s`；;，,]*?)?\*", section):
        return None
    return ids


def _has_asset_id_binding(section: str, prefix: str) -> bool:
    return bool(re.search(rf"`?{re.escape(prefix)}[A-Za-z0-9_]+`?", section))


def _needs_scene_asset_binding(refs: str) -> bool:
    return _has_any(refs, (
        "场景定妆",
        "场景锚",
        "定妆_冷宫寝殿",
        "定妆_场景",
    ))


def _needs_prop_asset_binding(refs: str) -> bool:
    return _has_any(refs, (
        "道具定妆",
        "定妆_斑驳铜镜",
        "定妆_赐死托盘",
        "定妆_毒酒碎瓷",
    ))


def _has_standard_character_turnaround(section: str) -> bool:
    """角色定妆基础包：正/45°/侧/背 + 服装参考 + 脸锚 + 人审拼版。"""
    has_front = _has_any(section, ("正面", "正脸", "主参考", "定妆_<角色>.png"))
    has_three_quarter = _has_any(section, ("45°", "45度", "三分之二侧脸", "3/4", "three_quarter", "_45度"))
    has_side = _has_any(section, ("_侧", "侧面", "侧脸"))
    has_back = _has_any(section, ("_背", "背面", "背身"))
    has_outfit = _has_any(section, ("_半身", "_全身", "半身服装", "全身服装", "服装参考", "体态参考"))
    has_face_anchor = _has_any(section, ("脸部特写", "面部特写", "face_anchor_refs", "基础脸部参考", "表情参考", "同源表情", "表情_"))
    has_board = _has_any(section, ("_三视图", "标准三视图", "正/侧/背", "正面 / 侧面 / 背面"))
    return has_front and has_three_quarter and has_side and has_back and has_outfit and has_face_anchor and has_board


def _is_restricted_partial_prompt_section(section: str) -> bool:
    return _has_any(section, ("局部参考", "restricted_partial", "no_full_face")) and _has_any(section, (
        "绝不正脸",
        "暂不正脸",
        "不建完整正脸",
        "只手",
        "帘后剪影",
        "no_full_face",
        "NEVER showing the face",
    ))


def _has_positive_prompt_heading(section: str, lang: str) -> bool:
    return f"正向 prompt（{lang}" in section


def _uses_halfbody_outfit_ref(section: str) -> bool:
    return _has_any(section, ("_半身", "半身服装", "半身参考", "半身.png", "半身图"))


def _has_halfbody_crop_rule(section: str) -> bool:
    """半身服装参考必须是正面主参考裁切放大，不能补底占位，且主体居中。

    作用域铁律：本规则（含「主体居中」）只针对**定妆照 / 共享定妆库的半身服装参考图**
    （仅 check_common_image_prompts 的 角色定妆.md 调用）。正式剧情**分镜图按导演构图与
    运镜处理、不强制居中**——绝不要把本检查接进 check_image_shot_prompt_section。"""
    has_source = _has_any(section, (
        "从已通过自检的正面主参考",
        "从已通过正面主参考",
        "从已通过的正面主参考",
        "从已通过正面图",
        "从正面主参考",
        "正面主参考裁切",
        "正面图裁切",
    ))
    has_crop = _has_any(section, ("裁切", "裁剪", "crop"))
    has_resize = _has_any(section, ("放大", "重采样", "回 9:16", "回9:16", "9:16"))
    forbids_padding = _has_any(section, (
        "不得用白底",
        "不要用白底",
        "禁止白底",
        "白底/浅灰底/空白",
        "空白补",
        "补满下半截",
        "补下半截",
        "补底",
        "纯色补底",
    ))
    has_centering = _has_any(section, (
        "人物主体居中",
        "人物居中",
        "主体居中",
        "居中裁切",
        "居中重裁",
        "头身中线",
        "画面中线",
        "左右留白",
        "留白基本均衡",
    ))
    return has_source and has_crop and has_resize and forbids_padding and has_centering


def _has_prop_structure_rule(section: str) -> bool:
    """关键道具必须锁结构唯一性，避免模型把描述词误画成新增部件。"""
    return _has_any(section, (
        "结构唯一性",
        "道具结构",
        "结构不幻觉",
        "件数锁定",
        "数量锁定",
        "三件套数量锁定",
        "唯一圆口",
        "唯一短颈",
        "一个圆口",
        "一个短颈圆口",
        "只有一个短颈圆口",
        "一个正常圆口",
        "无侧嘴",
        "无斜嘴",
        "无双口",
        "无多口",
        "无额外壶嘴",
        "无额外开口",
        "无重复瓶口",
        "无出酒嘴",
        "无管状嘴",
        "一柄一刃",
        "只有一柄一刃",
        "无多刃",
        "无双刃",
        "单镜面",
        "无多镜面",
        "不多镜面",
        "无重复镜框",
    ))


def _needs_prop_structure_gate(section: str, name: str, refs: str) -> bool:
    """只卡重道具镜头，避免普通场景里一句“托盘/铜镜”造成全剧误伤。"""
    heavy_title_or_refs = _has_any(
        f"{name}\n{refs}",
        (
            "赐死三件套",
            "毒酒碎裂",
            "定妆_赐死托盘",
            "定妆_毒酒碎瓷",
        ),
    )
    risky_wording = _has_any(section, (
        "毒酒壶",
        "白瓷毒酒壶",
        "毒酒瓷壶",
        "壶嘴",
        "白绫",
        "匕首",
        "短匕首",
        "赐死托盘",
        "赐死三件套",
    ))
    return heavy_title_or_refs or risky_wording


def check_image_shot_prompt_section(path: str, idx: int, section: str,
                                    single_ref_backend: bool = False) -> None:
    name = _headline(section, f"镜头 {idx}")
    loc = f"{path} {name}"

    if "检查清单（八维自查" not in section:
        add(BLOCK, "prompt", loc, "缺提交前检查清单（八维自查·最易漏②机位/⑥光影/⑦张力）")
    if "**自检**" not in section and "逐镜自检" not in section and "自检（生成后逐张过" not in section:
        add(BLOCK, "prompt", loc, "缺生成后逐张自检段")
    if "重抽预算" not in section:
        add(BLOCK, "prompt", loc, "缺重抽预算字段；无法按主要人物/关键镜策略收口")
    if not _has_positive_prompt_heading(section, "中文"):
        add(BLOCK, "prompt", loc, "缺正向 prompt（中文）")
    if not _has_positive_prompt_heading(section, "英文"):
        add(BLOCK, "prompt", loc, "缺正向 prompt（英文）兜底")
    if "负向 prompt" not in section:
        add(BLOCK, "prompt", loc, "缺负向 prompt；人物/场景堵漏不可控")
    elif "风格禁忌" not in section:
        add(BLOCK, "风格一致性", loc, "负向 prompt 未继承 style_contract.风格禁忌；风格禁忌只在契约不进逐镜负向=shot 级防不住风格漂（突然照片感/插画/高饱和），须把本集风格禁忌拼进本镜负向")
    if "导演视角八维" not in section:
        add(BLOCK, "prompt", loc, "缺导演视角八维表；分镜图不能只写画师式描述")

    if not _has_field(section, "光位锚"):
        add(BLOCK, "光影一致性", loc, "缺光位锚字段；同场跨镜主光方向/色温/动机光源会飘，剪起来闪——须继承 00_总览 本场光位锚")
    else:
        # 色温数值化体检（消费 n2d_logic.color_temperature_findings·治"Kelvin 是自由文本从不校验"）：
        m_light = re.search(r"光位锚[^\n]*?[：:]([^\n]*)", section)
        for f in color_temperature_findings(m_light.group(1) if m_light else ""):
            add(WARN, "光影一致性", loc, f["msg"])
    if not _has_field(section, "运动余量"):
        add(BLOCK, "首帧起幅", loc, "缺起幅·运动余量字段；clip 首帧须是起幅而非动作顶点，并按计划运镜预留构图余量")

    refs = _reference_block(section)
    if not refs:
        add(BLOCK, "prompt", loc, "缺参考图块；分镜图必须多图参考派生，禁止纯文生图")
    else:
        if "定妆_" not in refs:
            add(BLOCK, "prompt", loc, "参考图块未引用共享定妆资产；会导致跨镜人物/场景漂移")
        if "强度" not in refs and "strength" not in refs.lower():
            add(WARN, "prompt", loc, "参考图块未标参考强度；多图参考派生稳定性不可复现")
        if _needs_scene_asset_binding(refs) and not _has_asset_id_binding(section, "LOC_"):
            add(
                BLOCK,
                "资产引用注册层",
                loc,
                "参考图块含关键场景定妆但缺 LOC_xx 绑定；必须写 `资产引用注册层` 并引用 asset_registry.json，让执行端自动取场景 reference_group / constraints / drift_forbidden。",
            )
        if _needs_prop_asset_binding(refs) and not _has_asset_id_binding(section, "PROP_"):
            add(
                BLOCK,
                "资产引用注册层",
                loc,
                "参考图块含关键道具定妆但缺 PROP_xx 绑定；必须写 `资产引用注册层` 并引用 asset_registry.json，锁道具结构、件数和禁漂项。",
            )

    if _needs_prop_structure_gate(section, name, refs) and not _has_prop_structure_rule(section):
        add(BLOCK, "道具结构", loc, "关键道具镜头缺结构唯一性闸门；毒酒壶/瓷壶须锁唯一短颈圆口、无侧嘴/斜嘴/双口/额外开口，匕首须一柄一刃，三件套件数须锁定，避免道具幻觉")

    for key in ("①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧"):
        if key not in section:
            add(BLOCK, "prompt", loc, f"导演八维缺 {key} 维标记")

    # 机位即态度，是最易漏的导演决策——②机位 标记在场不等于真填了机位。空/默认正面平视无理由 → WARN。
    cam = re.search(r"\|\s*②[^|]*\|\s*([^|\n]*?)\s*\|", section)
    if cam:
        value = cam.group(1).strip().strip("*` ")
        if (not value) or value in ("正面平视", "平视", "默认", "正面", "默认正面平视", "—", "-", "/"):
            add(WARN, "构图景别", loc,
                "②机位 为空或默认正面平视——机位即态度（八维最易漏）；给本镜一个有叙事理由的机位（俯/仰/过肩/侧/主观），默认平视须注明理由")

    if _section_has_character_refs(section):
        if not _has_character_aesthetic_baseline(section):
            add(
                WARN,
                "人物审美基线",
                loc,
                "含角色镜头缺 `人物审美基线` 或等价说明。除非角色圣经/剧情特别要求丑、怪、病、老、恐怖、粗粝或非主流，"
                "人物默认应按主流可播审美和镜头友好来写：五官比例协调、妆造服装精致耐看、光影让脸好看，同时不覆盖角色 DNA。",
            )
        if not re.search(r"(锚点句|anchor phrase)\s*[:：]", section, re.IGNORECASE):
            add(BLOCK, "角色一致性", loc, "含角色镜头缺锚点句；每镜必须拼角色卡锚点")
        if not _has_field(section, "视线方向"):
            add(BLOCK, "轴线一致性", loc, "含角色镜头缺视线方向；轴线/视线在出图阶段焊进像素、出视频改不动，正反打会穿帮——须对位 00_总览 本场轴线")
        if not _has_any(section, ("脸型与定妆一致", "角色脸/妆造未漂移", "脸/妆造未漂移", "妆造未漂移")):
            add(BLOCK, "角色一致性", loc, "含角色镜头自检未显式检查脸/妆造漂移")
        if not _has_any(section, ("服装配色一致", "服装", "配色")):
            add(BLOCK, "角色一致性", loc, "含角色镜头未显式锁服装/配色")
        if single_ref_backend and not _has_i2i_derivation(section):
            add(
                BLOCK,
                "角色一致性",
                loc,
                "无持久角色 ID 后端(如 Codex/OpenAI/Dreamina/Nano)逐镜重画脸：本镜(含首帧)未声明从共享定妆 "
                "image2image/多图参考派生——纯文生图会把角色重抽成新演员，跨集必漂。"
                "请写明生成方式=以 `定妆_<角色>` 为母图做 image2image/多图参考派生，禁纯文生图。"
                "（原生主体锁后端可豁免；本后端下**每个**角色镜都须 i2i 派生，不止尾帧。）",
            )
        if not _has_any(section, ("资产身份注册层", "身份注册", "identity_registry", "reference_group", "drift_forbidden")):
            add(BLOCK, "资产身份注册层", loc, "含角色镜头缺资产身份注册层约束；必须从 identity_registry.json 继承 reference_group / angle_policy / drift_forbidden")
        if not _has_character_id_binding(section):
            add(
                BLOCK,
                "资产身份注册层",
                loc,
                "含角色镜头缺明确角色 ID 绑定；必须写 `CHAR_xx/形态`，让执行端从 identity_registry.json 自动反查 reference_group，禁止只靠中文角色名或纯文描述生图。",
            )
        ambiguous = _multi_char_binding_ambiguity(section)
        if ambiguous:
            add(
                WARN,
                "资产身份注册层",
                loc,
                f"同框引用多个角色（{'、'.join(ambiguous)}）但未星标 primary（写法 `CHAR_xx*`）；"
                "多数后端单图只锁得住一个主体，不声明锁谁=后端随机挑、崩脸不可追责——"
                "按 资产身份注册层.md「多角色同框绑定规则」给最高优先角色加星，其余降级参考图组。",
            )
        if _needs_closeup_identity_lock(section, name) and not _has_closeup_identity_lock(section):
            add(
                BLOCK,
                "角色一致性",
                loc,
                "正反打/反应/表情近景缺近景身份锁定；fallback reference_group 容易只保留角色大类但重画脸型/发髻/配饰。"
                "请补 `近景/反打身份锁定` 字段，引用脸部特写或表情参考，并明确锁脸型/五官比例/发型发髻/标志配饰。",
            )
        if _needs_closeup_identity_lock(section, name) and not _has_i2i_tail_continuity_lock(section):
            add(
                BLOCK,
                "角色一致性",
                loc,
                "正反打/反应/表情尾帧缺图生图接力约束；只写身份锚点仍可能纯文重抽成新演员。"
                "请补 `尾帧接力生成方式` 字段：尾帧必须以上一张成图或同镜首帧 image2image/图生图为母图，"
                "只改表情/眼神/嘴角，不得纯文生图。",
            )
        if single_ref_backend and _codex_needs_face_reference(section, name) and not _codex_has_face_reference(section):
            add(
                BLOCK,
                "Codex锁脸",
                loc,
                "Codex/OpenAI/Dreamina/Nano/Gemini 这类无持久角色 ID 后端会逐镜重新解脸；"
                "近景/反打/大表情镜不能只靠普通多参考或锚点句。请在本镜显式引用同源脸部特写/表情库 "
                "（expressions / `定妆_<角色>_脸部特写.png` / `定妆_<角色>_表情*.png`），并让尾帧用 image2image 接力，只改表情不重画五官。",
            )
        if single_ref_backend and _codex_dark_vfx_face_risk(section, name) and not _codex_has_face_visibility_guard(section):
            add(
                BLOCK,
                "Codex锁脸",
                loc,
                "暗光/烟雾/VFX 叠脸会诱导无持久角色 ID 后端重画五官；本镜缺脸部可见性约束。"
                "请补约束：眼鼻嘴三角区清晰、特效/黑烟只在脸外侧或后景、不得遮住五官、不得重画脸。",
            )
        if "_侧" not in refs and "_半身" not in refs and "_全身" not in refs and "主体库" not in section and "角色ID" not in section:
            add(WARN, "角色一致性", loc, "含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂")
        chars = _character_names_in_refs(refs)
        # 多人同框（C6 剧情优先：≥4 张清晰脸该出就出，必须登记分区合成把它做对，不删戏/不砍人数）+ 锚点去重（④）。
        _wide_crowd = _has_any(section, ("远景", "大全景", "群像", "人海", "crowd", "wide shot", "extreme long", "ELS"))
        _multi_closeup = _has_any(section, ("ECU", "BCU", "CU", "MCU", "近景", "特写", "面部", "脸部", "反应镜", "表情镜")) \
            and not _has_any(section, ("远景", "全景", "中景"))
        # 把 ≥4 同框「做对」的执行策略（分区合成 / 原生主体策略）——登记了就放行该镜，由下面 ≥2 层继续校验槽位等细节。
        _has_multi_exec_strategy = (
            _has_codex_split_composite_strategy(section) or _has_native_multi_subject_strategy(section)
        )
        if len(chars) >= 4 and not _wide_crowd and not _has_multi_exec_strategy:
            add(
                BLOCK,
                "构图景别",
                loc,
                f"单镜清晰同框 ≥4 具名角色（{'/'.join(sorted(chars))}）未登记分区合成执行策略：单帧 co-gen 4+ 张清晰脸"
                "所有后端都难压（实测 ≤3 更稳）——但这是「要分区合成做对」，不是「删到 ≤3 / 砍同框戏」（设计宪法 C6 剧情优先）。"
                "剧情需要这场 ≥4 人同框就照出：登记 split_composite/分别出图+合成（每主体身份槽位）把每张脸分别做好再合成，"
                "或拆 establish+反打把整场戏拍全；确属远景群像（脸不解析）请在本镜显式标 `远景/群像`。",
                return_to_stage="image",
            )
        if len(chars) >= 2:
            # 升 BLOCK 后，逃生口收紧为「显式 split/分层 执行 token」——不再认裸的「反打/正反打」字样：
            # 那些常作为视线对位/身份锁定的样板话出现在每个对话镜里（一次生成多张脸的同框近景也会写），
            # 认它就等于永不触发。真·反打是拆成单人镜（每帧 1 张脸），本就不该是「多人同框」，故同框近景的
            # 放行只认 分别出图/分层合成/单人分层/景别分层 这类落地执行策略。
            _CLOSEUP_SPLIT_TOKENS = ("shot_reverse_shot", "split_composite", "regional_construct",
                                     "分区构建", "区域构建", "分别出图", "分角色出图",
                                     "拆成单人镜", "拆单人镜", "单人分层", "分层合成", "景别分层")
            if _multi_closeup and not _has_any(section, _CLOSEUP_SPLIT_TOKENS):
                # 多人近景同框是 cross-attention 串脸最高发档（2026 SOTA：单帧多主体身份必相互渗透，
                # 即便最强后端 ~85% 一致、近景更糟；公认最佳实践是「分开生成再合成」而非单帧绑定）。
                # 槽位绑定仍是「一次生成多张脸」，治不了近景串脸——必须拆开生成。
                # 2026-06 由 WARN 升 BLOCK（与「空间绑定对所有后端 block」同向，对最危险的近景档收口）。
                add(
                    BLOCK,
                    "构图景别",
                    loc,
                    f"多人近景同框（{'/'.join(sorted(chars))}）未声明反打/分层/分别出图：近景是多主体 cross-attention "
                    "串脸最高发档，槽位绑定（一次生成多张脸）治不住——必须拆「单人CU + 反打」或「单人分层出图 + 合成」"
                    "分开生成各自的脸；确需同框请降到中景/全景做景别分层（清晰主角1人，余者推后景/虚焦），"
                    "并登记 split_composite/分层合成执行策略。",
                    return_to_stage="image",
                )
            if single_ref_backend and not _has_any(section, ("区分锚点", "互斥锚点", "可区分性", "distinct anchor", "去重锚点", "撞色")):
                add(
                    WARN,
                    "角色一致性",
                    loc,
                    f"多人同框（{'/'.join(sorted(chars))}）缺 `区分锚点` 字段：同框角色发色/发型/服装主色越接近，越易被模型平均成同一张脸。"
                    "逐主体写 5–7 个互斥锚点（各自唯一发色/发型/服装主色HEX/标志配饰）并确保两两不撞色；"
                    "可读 reference_planner 的 `distinct_anchors` 处方。",
                )
            if single_ref_backend and _has_generic_reference_index_lock(section):
                add(
                    BLOCK,
                    "Codex锁脸",
                    loc,
                    "多角色同框镜使用了“参考图①/reference image 1”这类泛化身份锁。"
                    "无持久角色 ID 后端会把第 1 张参考误当成所有人的身份锚，造成配角串脸或重解脸。"
                    "请改成逐主体锁脸句：每个 `CHAR_xx/形态` 分别对应自己的定妆/脸部特写/表情库；"
                    "并在同框镜登记分别出图+合成或切统一的原生主体后端。",
                    return_to_stage="image",
                )
            if single_ref_backend:
                if not _has_codex_split_composite_strategy(section):
                    add(BLOCK, "角色一致性", loc,
                        f"单镜多角色同框（{'/'.join(sorted(chars))}）× 无持久角色 ID 后端(如 Codex)：普通多参考不是持久主体锁，"
                        "每个主体都会被重新解脸，且多人同框无硬位置/主体 ID 绑定时极易串脸。"
                        "本后端下只有「分别出图+合成/单人分层出图」这类硬降级能放行；"
                        "或把项目生图AI统一切到支持原生主体/角色ID的官方后端后再跑 gate。")
                elif not _has_multi_subject_identity_slots(section):
                    add(
                        BLOCK,
                        "角色一致性",
                        loc,
                        f"单镜多角色同框（{'/'.join(sorted(chars))}）虽登记了分层/合成，但缺 `多人同框身份槽位`。"
                        "无持久角色 ID 后端必须逐主体写 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位，"
                        "每个槽位绑定 `CHAR_xx/形态`、画面位置、视线、自己的脸部参考/表情库和 primary 星标；"
                        "否则分层合成阶段仍会串脸或无法追责。",
                        return_to_stage="image",
                    )
            elif not _has_native_multi_subject_strategy(section):
                add(BLOCK, "角色一致性", loc,
                    f"单镜多角色同框（{'/'.join(sorted(chars))}）× 原生主体后端：缺 `多人同框执行策略`"
                    "（native_subject_slots / 区域绑定 / 分别出图+合成）。多主体后端虽有主体绑定能力，但无显式"
                    "空间/主体策略时仍会把参考身份混到错位或把两张脸平均成同一张——逐主体写原生主体名额或区域绑定策略，"
                    "否则不放行（空间绑定是同框一致性硬约束，2026-06 起对所有后端 block，不再降级为建议）。",
                    return_to_stage="image")
            elif not _has_multi_subject_identity_slots(section):
                add(BLOCK, "角色一致性", loc,
                    f"单镜多角色同框（{'/'.join(sorted(chars))}）缺 `多人同框身份槽位`：逐主体绑定 CHAR_xx/形态、"
                    "画面槽位（LEFT/RIGHT/FOREGROUND/BACKGROUND）、视线与各自参考图组，避免多主体后端把参考身份混到错误位置——"
                    "空间槽位绑定是同框一致性硬约束，2026-06 起对所有后端 block，不再降级为建议。",
                    return_to_stage="image")


def _evolution_derived_forms(root: str) -> List[Dict[str, str]]:
    """registry → 成长态派生形态清单：非 `identity_anchor_form` 的 form 必须从锚定/上一形态 image2image 派生。

    治「新境界 form 首现纯文生图重抽新脸」(E)——只纳入渐进升级 evolution_profile 的角色；
    restricted_partial（如垂帘皇后）只有锚定形态、无派生形态，不纳入。纯函数·依赖 registry。"""
    data = load_json(identity_registry_path(root))
    out: List[Dict[str, str]] = []
    if not isinstance(data, dict):
        return out
    for ch in data.get("characters") or []:
        if not isinstance(ch, dict):
            continue
        ep = ch.get("evolution_profile")
        if not isinstance(ep, dict) or "progressive_upgrade" not in str(ep.get("mode") or ""):
            continue
        anchor = str(ep.get("identity_anchor_form") or "")
        for f in ch.get("forms") or []:
            if not isinstance(f, dict):
                continue
            form = str(f.get("form") or "")
            if not form or form == anchor:
                continue
            out.append({"char_id": str(ch.get("id") or ""), "char_name": str(ch.get("name") or ""),
                        "asset_key": str(f.get("asset_key") or ""), "form": form, "anchor_form": anchor})
    return out


def _section_is_derived_form(sec: str, df: Dict[str, str]) -> bool:
    """该定妆 section 是否属于某成长派生形态（按 asset_key 命中，否则 角色名+形态名 同时出现）。"""
    ak = df.get("asset_key") or ""
    if ak and ak in sec:
        return True
    return bool(df.get("char_name") and df["char_name"] in sec and df.get("form") and df["form"] in sec)


def _declares_evolution_derivation(sec: str, anchor_form: str) -> bool:
    """成长派生形态定妆是否声明「从锚定/上一形态 image2image 派生」（而非纯文生图重抽新脸）。"""
    prior_markers = [m for m in (anchor_form, "上一阶段", "上一形态", "前一形态", "上一形",
                                 "基线形态", "锚定形态", "identity_anchor", "派生自", "成长派生") if m]
    return _has_i2i_derivation(sec) and _has_any(sec, prior_markers)


def check_common_image_prompts(root: str) -> None:
    prompt_dir = shared_asset_path(root, "prompt")
    if not os.path.isdir(prompt_dir):
        add(BLOCK, "共享定妆", prompt_dir, "缺共享定妆 prompt 目录")
        return
    derived_forms = _evolution_derived_forms(root)
    for filename in ("角色定妆.md", "场景定妆.md", "道具定妆.md", "法宝定妆.md", "特效定妆.md"):
        p = os.path.join(prompt_dir, filename)
        if not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8").read()
        sections = re.findall(r"(?ms)^##\s+.*?(?=^##\s+|\Z)", text)
        for i, sec in enumerate(sections, 1):
            name = _headline(sec, f"{filename} block#{i}")
            loc = f"{p} {name}"
            if "目标存档" not in sec:
                add(BLOCK, "共享定妆", loc, "缺目标存档；共享资产无法归档追踪")
            if not _has_positive_prompt_heading(sec, "中文"):
                add(BLOCK, "共享定妆", loc, "缺正向 prompt（中文）")
            if not _has_positive_prompt_heading(sec, "英文"):
                add(BLOCK, "共享定妆", loc, "缺正向 prompt（英文）")
            if "负向 prompt" not in sec:
                add(BLOCK, "共享定妆", loc, "缺负向 prompt")
            if "检查清单（定妆自查" not in sec:
                add(BLOCK, "共享定妆", loc, "缺定妆提交前检查清单")
            if "自检（生成后逐张过" not in sec and "**自检**" not in sec:
                add(BLOCK, "共享定妆", loc, "缺生成后落档自检段")
            if filename == "道具定妆.md" and not _has_prop_structure_rule(sec):
                add(BLOCK, "道具结构", loc, "道具定妆缺关键道具结构唯一性闸门；需锁唯一圆口/短颈、无侧嘴/斜嘴/双口/额外开口、多刃/多镜面/件数错等，避免道具结构幻觉")
            if filename == "角色定妆.md":
                if "身份注册" not in sec and "identity_registry" not in sec:
                    add(BLOCK, "资产身份注册层", loc, "角色定妆缺身份注册字段；必须指向 `出图/共享/identity_registry.json` 对应 characters[].forms[]")
                restricted_partial = _is_restricted_partial_prompt_section(sec)
                if not restricted_partial:
                    if "角色定妆组" not in sec:
                        add(BLOCK, "角色一致性", loc, "角色定妆缺定妆组说明；人物角色不能只靠单张正脸")
                    if not _has_standard_character_turnaround(sec):
                        add(BLOCK, "角色定妆基础包", loc,
                            "人物定妆基础包必须写齐：正面主参考 + 45°参考 + 侧面参考 + 背面参考 + 半身/全身服装参考 + "
                            "脸部特写/同源表情参考 + `定妆_<角色>_三视图.png` 人审拼版。"
                            "完整表情组、动作参考、主体库/LoRA 是风险升档项，不替代基础包。")
                if _uses_halfbody_outfit_ref(sec) and not _has_halfbody_crop_rule(sec):
                    add(BLOCK, "服装参考", loc, "半身服装参考必须写明：`定妆_<角色>_半身.png` 从已通过自检的正面主参考裁切并放大/重采样回 9:16；人物主体居中、头身中线接近画面中线、左右留白基本均衡；不得新抽半身导致脸漂，也不得用白底/浅灰底/空白补下半截")
                if "锚点" not in sec:
                    add(BLOCK, "角色一致性", loc, "角色定妆缺锚点字段；下游每镜无锚可拼")
                # E 跨集成长派生形态：新境界/换装升级 form 的定妆必须从锚定/上一形态 image2image 派生，
                # 不得纯文生图重抽一张新脸——否则"同一个人变强"变成"换演员"，且下游每镜会忠实继承这张错脸。
                for df in derived_forms:
                    if _section_is_derived_form(sec, df) and not _declares_evolution_derivation(sec, df["anchor_form"]):
                        add(BLOCK, "跨集成长一致性", loc,
                            f"成长派生形态 `{df['char_name']}/{df['form']}` 的定妆未声明从锚定形态"
                            f"`{df['anchor_form']}` 的正脸/脸部特写 image2image 派生（evolution_profile 渐进升级）。"
                            "纯文生图重抽新脸=同一个人被换成另一张脸，下游每镜还会忠实继承错脸。"
                            "请写明：以 `定妆_<角色>_<锚定形态>` 正脸/脸部特写为母图做 image2image 派生，"
                            "只升级服装/法宝/气场/VFX，锁 identity_invariants（脸型/五官比例/发际线/标志疤痣）。",
                            return_to_stage="image")
                        break


def check_shared_image_index(root: str, ep: str) -> None:
    overview = os.path.join(root, "出图", ep, "prompt", "00_总览.md")
    index = shared_asset_path(root, "prompt", "00_索引.md")
    if not os.path.isfile(overview):
        add(BLOCK, "出图", overview, "缺本集出图总览")
        return
    if not os.path.isfile(index):
        add(BLOCK, "出图", index, "缺共享定妆索引")
        return
    common_dir = shared_asset_dir(root)
    index_text = open(index, encoding="utf-8").read()
    for ln in index_text.splitlines():
        if not ln.strip().startswith("|") or "✅" not in ln:
            continue
        paths = re.findall(r"`([^`]+\.png)`", ln)
        for rel in paths:
            if os.path.isabs(rel):
                full = rel
            else:
                # 路径可能是「作品根相对」(出图/共享/图片/定妆_X.png) 或「共享目录相对」(定妆_X.png)；两种都试
                cand_root = os.path.join(root, rel)
                cand_common = os.path.join(common_dir, rel)
                if os.path.exists(cand_root):
                    full = cand_root
                elif rel.startswith("_") and glob.glob(os.path.join(common_dir, f"*{rel}")):
                    continue
                else:
                    full = cand_common
            if not os.path.exists(full):
                add(BLOCK, "共享定妆", index, f"索引标 ✅ 但 PNG 不存在：{rel}")
    overview_text = open(overview, encoding="utf-8").read()
    missing = []
    in_table = False
    for ln in overview_text.splitlines():
        if ln.startswith("## 共享定妆就绪状态"):
            in_table = True
            continue
        if in_table and ln.startswith("## "):
            break
        if in_table and ln.strip().startswith("|") and "⬜" in ln:
            missing.append(ln.strip())
    if missing:
        add(BLOCK, "共享定妆", overview, f"本集引用的共享定妆仍有未完成项：{missing[0][:120]}")


_FINALIZE_CHAR_RE = re.compile(r"CHAR_[A-Za-z0-9_]+(?:/[^\s`，；、*]+)?")
_FINALIZE_ASSET_RE = re.compile(r"(?:LOC|PROP|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_]+")


def _finalize_evidence(root: str) -> Tuple[set, set, set]:
    """registry → (all_keys, evidence_keys, dirty_keys) 三组机器可读引用键。

    - `all_keys`：所有已登记 form/asset 的引用键（含未追踪的），用于判定一个被引用 id 是否真属本 registry。
    - `evidence_keys`：有**机器可读落档证据**的键——角色 form `self_check_passed==True` *或* 登记了 `anchor_sha`
      （后者覆盖档①参考派生；档②原生主体 ID / 档③ LoRA 的就绪由 check_identity_registry/route 另验，
      故这里 self_check_passed==True 即算证据，不强逼所有 form 都钉 anchor_sha 而误伤档②/③）；资产 `self_check_passed==True`。
    - `dirty_keys`：`self_check_passed==False`（自检未过的脏定妆/脏资产）。
    角色 form 同时登记 `CHAR_xx/形态` 与（单形态时）裸 `CHAR_xx` 两个键。"""
    all_keys: set = set()
    evidence: set = set()
    dirty: set = set()
    try:
        reg = json.loads(open(identity_registry_path(root), encoding="utf-8").read())
    except Exception:
        reg = {}
    for c in (reg.get("characters") or []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        forms = c.get("forms") or []
        for fm in forms:
            if not isinstance(fm, dict):
                continue
            form_name = str(fm.get("form") or "").strip()
            keys = []
            if cid and form_name:
                keys.append(f"{cid}/{form_name}")
            if cid and len(forms) == 1:
                keys.append(cid)
            all_keys.update(keys)
            scp = fm.get("self_check_passed")
            anchored = bool(str(fm.get("anchor_sha") or "").strip())
            if scp is True or anchored:
                evidence.update(keys)
            if scp is False:
                dirty.update(keys)
    try:
        areg = json.loads(open(os.path.join(root, "出图", "共享", "asset_registry.json"), encoding="utf-8").read())
    except Exception:
        areg = {}
    for a in (areg.get("assets") or []):
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id") or "").strip()
        if not aid:
            continue
        all_keys.add(aid)
        scp = a.get("self_check_passed")
        if scp is True:
            evidence.add(aid)
        if scp is False:
            dirty.add(aid)
    return all_keys, evidence, dirty


def check_referenced_assets_finalized(root: str, ep: str) -> None:
    """付费出图前置·机器可读 finalize 闸门（被引用即必需机器证据）：

    - 引用了显式标 `self_check_passed=false` 的脏定妆/资产 → BLOCK（脏锚点下游每镜继承）。
    - **被引用即必需**：一旦项目启用了 finalize/锚点追踪（任一 form/asset 登记过 `self_check_passed` 或 `anchor_sha`），
      本集逐镜引用的、且确属本 registry 的共享定妆/资产，**必须**有机器可读落档证据（self_check_passed=true 或 anchor_sha）；
      仅靠人读 ✅ 或干脆没登记 = 自断言/漏登记，**缺证据即 BLOCK**——堵住「给一部分置 true、其余留空就静默放行」的洞。

    **adoption-gated**：完全没启用追踪的项目（现有作品/先出视频 demo，registry 无任何 self_check_passed/anchor_sha）
    → 跳过，保持 00_索引 人读 ✅ 的既有流程，不突然阻断。"""
    all_keys, evidence, dirty = _finalize_evidence(root)
    if not (evidence or dirty):
        return  # 未启用机器 finalize/锚点追踪：向后兼容，不强加
    shots_md = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    try:
        text = open(shots_md, encoding="utf-8").read()
    except Exception:
        return  # 逐镜 prompt 未写：check_image_prompt_overview 等各自负责
    referenced = set(_FINALIZE_CHAR_RE.findall(text)) | set(_FINALIZE_ASSET_RE.findall(text))

    def _resolve(rid: str, pool: set) -> bool:
        base = rid.split("/")[0]
        if rid in pool:
            return True
        # 裸 CHAR_xx 引用 → 命中其任一形态键
        return rid == base and any(k == base or k.startswith(base + "/") for k in pool)

    dirty_refs: List[str] = []
    missing_refs: List[str] = []
    for rid in sorted(referenced):
        if not _resolve(rid, all_keys):
            continue  # 不属本 registry（typo/未登记类型）→ unknown_char_id/unknown_asset_id 等别的检查负责
        if _resolve(rid, dirty):
            dirty_refs.append(rid)
        elif not _resolve(rid, evidence):
            missing_refs.append(rid)
    for rid in dirty_refs:
        add(BLOCK, "共享定妆", shots_md,
            f"本集逐镜引用了未过落档自检的共享定妆/资产 `{rid}`（registry `self_check_passed=false`）——"
            "脏定妆是锚点，脸/结构漂了下游每镜继承；先过自检并把该项置 true（或人工复核后 `image_qc --mark-finalized`），再付费出图。")
    for rid in missing_refs:
        add(BLOCK, "共享定妆", shots_md,
            f"项目已启用 finalize 追踪，但本集引用的共享定妆/资产 `{rid}` 没有任何机器可读落档证据"
            "（既无 `self_check_passed=true` 也无 `anchor_sha`）——被引用即必需机器证据：人读 ✅/没登记都不算数，"
            "先过落档自检 `image_qc --mark-finalized`（角色 form 默认顺带钉 `anchor_sha` 机器证据）再付费出图。")


def _sha256_file(path: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _form_anchor_relpath(form: Mapping) -> str:
    """form 的锚点定妆图（front 主参考）项目相对路径；缺 front 时回退第一张可用视图。"""
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    front = rg.get("front")
    if isinstance(front, str) and front.strip():
        return front.strip()
    for v in rg.values():
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def check_anchor_fingerprints(root: str, ep: str) -> None:
    """共享定妆锚点指纹钉死（治跨集脸漂的结构根因之一）：identity_registry 的 form 若显式登记
    `anchor_sha`（opt-in），就校验磁盘上 front 定妆图当前 sha256 == 注册值。锚点被悄改/丢失 =
    下游每镜（含跨集每一集）继承换脸 → BLOCK。

    **纯 opt-in**：未登记 `anchor_sha` 的 form = 未启用钉死 → 跳过（向后兼容，现有作品/先出视频
    demo 不被突然阻断）。写入口：`image_qc.py <root> --pin-anchor CHAR_xx/形态`。"""
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return
    reg_path = identity_registry_path(root)
    pinned: List[Tuple[str, str, str]] = []  # (label, expected_sha, rel_path)
    for c in (reg.get("characters") or []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        for fm in (c.get("forms") or []):
            if not isinstance(fm, dict):
                continue
            exp = str(fm.get("anchor_sha") or "").strip()
            if not exp:
                continue
            form_name = str(fm.get("form") or "").strip()
            label = f"{cid}/{form_name}" if form_name else (cid or "?")
            pinned.append((label, exp, _form_anchor_relpath(fm)))
    if not pinned:
        return
    for label, exp, rel in pinned:
        full = os.path.join(root, rel) if rel else ""
        if not rel or not os.path.isfile(full):
            add(BLOCK, "共享定妆", reg_path,
                f"定妆锚点 `{label}` 已登记 anchor_sha 但 front 定妆图缺失"
                f"（{rel or 'reference_group 未填 front'}）——锚点丢失，下游每镜无母图可派生，跨集必漂；"
                "补回原锚点定妆图，或重新 `image_qc --pin-anchor`。")
            continue
        actual = _sha256_file(full)
        if actual != exp:
            add(BLOCK, "共享定妆", reg_path,
                f"定妆锚点 `{label}` 被改动：磁盘 sha256 与 registry `anchor_sha` 不一致"
                f"（pinned={exp[:12]}… actual={(actual or 'none')[:12]}…）——锚点一漂，所有引用它的集都继承换脸。"
                "若为有意更新：重出依赖镜后用 `image_qc --pin-anchor` 重新钉死；否则恢复原锚点定妆图。")


def check_core_anchor_pinning(root: str, ep: str) -> None:
    """核心长线角色未启用锚点钉死的前置提醒（advisory·WARN）。

    `check_anchor_fingerprints` 是纯 opt-in：没登记 `anchor_sha` 的 form 直接跳过——意味着一张被多集
    引用的锁脸定妆图，若在 `n2d-update media` 重刷或重生成时被换掉，下游每一集静默继承新脸而无任何机检
    （`check_referenced_assets_finalized` 只信 self_check_passed 标志、不验像素）。这里补「该钉没钉」的信号：
    对**本集引用到的核心长线角色**（scope/tier 命中贯穿全篇/主角/主反派等），若其 form 一个都没登记
    `anchor_sha` → WARN 建议 `image_qc --pin-anchor` 钉死。只对核心角色报（短线配角/单元妖不前置高档，
    对齐 n2d-image「ROI 驱动」），单条 rollup 不刷屏；纯 WARN 不 BLOCK（向后兼容现有未钉作品）。"""
    data = load_json(identity_registry_path(root))
    if not isinstance(data, dict):
        return
    chars = data.get("characters")
    if isinstance(chars, dict):
        chars = list(chars.values())
    if not isinstance(chars, list) or not chars:
        return
    referenced_ids, _ = episode_registry_reference_ids(root, ep)
    if not referenced_ids:
        return  # 本集还没引用任何登记角色（如出图前早期）——不前置提醒
    unpinned: List[str] = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        if cid not in referenced_ids:
            continue
        scope = f"{c.get('tier') or ''} {c.get('scope') or ''}"
        if not _CORE_SCOPE_RE.search(scope):
            continue  # 仅核心长线角色前置高档
        forms = c.get("forms") if isinstance(c.get("forms"), list) else []
        if any(str((fm or {}).get("anchor_sha") or "").strip() for fm in forms if isinstance(fm, dict)):
            continue  # 已有任一 form 钉死
        names = [n.strip() for n in str(c.get("name") or "").replace("／", "/").split("/") if n.strip()]
        unpinned.append(f"{names[0] if names else cid}({cid})")
    if unpinned:
        add(WARN, "锚点钉死", identity_registry_path(root),
            f"核心长线角色未启用定妆锚点钉死：{('、'.join(unpinned))}——这些脸被多集引用，"
            "重刷/重生成定妆若换脸则下游每集静默继承（anchor_sha 未登记 = check_anchor_fingerprints 跳过）。"
            "建议对其 front 定妆图 `image_qc --pin-anchor CHAR_xx/形态` 钉死，"
            "重制后用 n2d-update media 复核跨集引用集。",
            return_to_stage="image")


def check_expression_anchors(root: str, ep: str) -> None:
    """表情库跨集共享锁定（治"第2集的怒和第5集的怒各画各的"）：form 若显式登记 `expression_anchors`
    （opt-in，每条 `{emotion, path, self_check_passed?, anchor_sha?}`），则该情绪锚必须存在、过自检、未被悄改——
    否则跨集同情绪近景就没有同源母图可派生 → BLOCK。

    **纯 opt-in**：未登记 `expression_anchors` 的 form 跳过（向后兼容）。
    写入口：`image_qc.py <root> --finalize-expr CHAR_xx/形态/情绪`（落自检真值 + 钉 sha）。"""
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return
    reg_path = identity_registry_path(root)
    for c in (reg.get("characters") or []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        for fm in (c.get("forms") or []):
            if not isinstance(fm, dict):
                continue
            anchors = fm.get("expression_anchors")
            if not isinstance(anchors, list):
                continue
            form_name = str(fm.get("form") or "").strip()
            for a in anchors:
                if not isinstance(a, dict):
                    continue
                emotion = str(a.get("emotion") or "?").strip()
                rel = str(a.get("path") or "").strip()
                label = f"{cid}/{form_name}#{emotion}" if form_name else f"{cid}#{emotion}"
                full = os.path.join(root, rel) if rel else ""
                if not rel or not os.path.isfile(full):
                    add(BLOCK, "共享定妆", reg_path,
                        f"表情锚 `{label}` 已登记但图缺失（{rel or '未填 path'}）——跨集同情绪近景无同源母图，"
                        "各集各画各的=情绪一致性崩；补出该情绪脸部特写并 `image_qc --finalize-expr`。")
                    continue
                if a.get("self_check_passed") is False:
                    add(BLOCK, "共享定妆", reg_path,
                        f"表情锚 `{label}` 未过落档自检（self_check_passed=false）——脏情绪锚是跨集同情绪近景的源头；"
                        "先过自检并 `image_qc --finalize-expr` 再付费出图。")
                    continue
                exp = str(a.get("anchor_sha") or "").strip()
                if exp:
                    actual = _sha256_file(full)
                    if actual != exp:
                        add(BLOCK, "共享定妆", reg_path,
                            f"表情锚 `{label}` 被改动：磁盘 sha256 与登记 `anchor_sha` 不一致——一漂则所有引用集同情绪近景换脸；"
                            "有意更新就重出依赖镜后 `image_qc --finalize-expr` 重钉，否则恢复原图。")


def check_character_backend_pin(root: str, ep: str) -> None:
    """一角一后端跨集钉：核心长线 form 若登记 `backend_pin` 后本集换生图后端 → BLOCK，其余 WARN。

    同一角色跨集换后端本身是脸漂源（不同模型脸的先验不同），
    弱后端尤甚。**纯 opt-in**：未登记 backend_pin 跳过。"""
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return
    cur_canon, _ = classify_image_backend(get_setting(root, "生图AI", "Codex").strip())
    reg_path = identity_registry_path(root)
    for c in (reg.get("characters") or []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        for fm in (c.get("forms") or []):
            if not isinstance(fm, dict):
                continue
            pin = str(fm.get("backend_pin") or "").strip()
            if not pin:
                continue
            pin_canon, _ = classify_image_backend(pin)
            if pin_canon == cur_canon:
                continue
            form_name = str(fm.get("form") or "").strip()
            label = f"{cid}/{form_name}" if form_name else (cid or "?")
            is_core = bool(_CORE_SCOPE_RE.search(f"{c.get('tier') or ''} {c.get('scope') or ''}"))
            sev = BLOCK if is_core else WARN
            add(sev, "角色一致性", reg_path,
                f"角色 `{label}` 身份钉在出图后端 `{pin_canon}`，本集项目 生图AI=`{cur_canon}`——"
                "同一角色跨集换后端本身是脸漂源（不同模型脸的先验不同），弱后端尤甚。"
                "要么切回原后端出本集，要么先把该角色升原生主体库/LoRA 再换；确认有意更换则更新 backend_pin。",
                return_to_stage="image")


def check_image_assets(root: str, ep: str) -> None:
    if not progress_fraction_done(root, ep, "出图"):
        add(BLOCK, "出图", os.path.join(root, "_进度.md"), "出图列未满，不能进入出视频")
    png_dir = os.path.join(root, "出图", ep, "图片")
    pngs = glob.glob(os.path.join(png_dir, "*.png"))
    if not pngs:
        add(BLOCK, "出图", png_dir, "本集没有分镜 PNG")


# 近景/特写景别标记（脸占画面主体、表情漂移=脸重画最致命的镜）。
_CLOSEUP_MARKERS = (
    "CU", "ECU", "MCU", "BCU", "特写", "近景", "脸部", "面部",
    "反打", "正反打", "过肩", "OTS", "dialogue_shot_reverse", "dialogue_closeup",
)


def _clip_is_closeup(clip: Dict[str, Any]) -> bool:
    """clip 是否为近景/特写/反打（脸占主体）：扫 template + label + shots[].lens/desc 的景别标记。

    用于「大表情近景必须首尾双帧」闸门——把 expression_span=大 收口到真正的脸戏，避免误伤
    远景/空镜被误标 大 的镜。纯函数·可测。"""
    blob = " ".join(str(clip.get(k) or "") for k in ("template", "label"))
    for shot in clip.get("shots") or []:
        if isinstance(shot, dict):
            blob += " " + " ".join(str(shot.get(k) or "") for k in ("lens", "desc"))
    return _has_any(blob, _CLOSEUP_MARKERS)


def check_expression_span_frame_contract(root: str, ep: str) -> None:
    """出视频前置（脸被表情带着重画的头号根因·机检闸门）：跨情绪近景必须走首尾双帧只插值工艺。

    `prompt_format.md`「近景大表情变化类 Clip」铁律：表情跨度=大（平静→爆哭/隐忍→暴怒）的 CU/MCU/反打镜
    若靠单首帧让模型自由生成中间表情，脸型/五官比例会随表情拉伸漂移、剪起来像换了个人。此前
    `表情跨度` 只活在总览风险表里、是人读自检——gate 看不见、拦不住。本检查把它结构化（storyboard
    `continuity.expression_span` ∈ {微,中,大}）后机检：

      · expression_span 值非法（非 微/中/大）→ BLOCK（typo 防呆）；
      · expression_span=大 且镜为近景/特写/反打 → 必须 need_endframe=true（有止表情尾帧可插值），
        否则 BLOCK——单首帧扛不住跨情绪表情；
      · expression_span=大 但镜非近景 → WARN（远景大表情风险低，或景别标错，提示复核）。

    纯 opt-in：`continuity.expression_span` 缺失=未启用追踪→跳过（现有 demo/未标镜不误伤），与
    `self_check_passed`、`midframe_default` 同款门控。路由后端能否真消费这条尾帧（frames2video/
    multiframe）由 `check_route_frame_capability` 对高风险镜升 BLOCK 兜，本检查不重复报。"""
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        return  # storyboard 缺失/损坏由 check_storyboard_contract 负责
    for i, clip in enumerate(data["clips"], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.get("continuity")
        if not isinstance(cont, dict):
            continue
        span = cont.get("expression_span")
        if span in (None, ""):
            continue  # opt-in：未声明=不追踪
        loc = f"{storyboard_path(root, ep)} clip#{i}"
        if span not in EXPRESSION_SPAN_VALUES:
            add(BLOCK, "表情一致性", loc,
                f"continuity.expression_span={span!r} 非法；必须是 {'/'.join(EXPRESSION_SPAN_VALUES)} 之一"
                "（大=跨情绪如 平静→爆哭/隐忍→暴怒）。")
            continue
        if span != EXPRESSION_SPAN_BIG:
            continue
        if not _clip_is_closeup(clip):
            add(WARN, "表情一致性", loc,
                "expression_span=大 但本镜景别未识别为近景/特写/反打——跨情绪大表情通常是脸戏；"
                "若确为远景/空镜风险较低，否则复核景别或下调跨度档。", return_to_stage="script_stage2")
            continue
        if cont.get("need_endframe") is not True:
            add(BLOCK, "表情一致性", loc,
                "expression_span=大 的近景/特写/反打镜必须 need_endframe=true 走「首尾双帧只插值」"
                "（首=起表情、尾=止表情同源定妆，mode=frames2video，让模型只插值表情肌肉、不自由重画脸）；"
                "缺尾帧=单首帧硬扛跨情绪表情=脸型/五官比例随表情漂移。补 endframe_png（止表情定妆，"
                "如 `镜头N_expr_end.png` 或 reference_group.expressions 对应情绪图）或降级 MCU/OTS/侧脸后下调跨度档。",
                return_to_stage="image")


def _episode_big_expression_closeup_clips(root: str, ep: str) -> List[Tuple[int, Dict[str, Any]]]:
    """本集所有「跨情绪大表情近景」镜：continuity.expression_span=大 且景别为近景/特写/反打。

    返回 [(clip 序号, clip dict)]。storyboard 缺失/损坏返回空（由 check_storyboard_contract 负责）。
    纯函数·可测——`check_core_expression_anchor_coverage` 与 `check_expression_span_frame_contract`
    共用同一镜头集合判据（expression_span=大 + `_clip_is_closeup`），避免两闸口径漂。"""
    data = load_json(storyboard_path(root, ep))
    out: List[Tuple[int, Dict[str, Any]]] = []
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        return out
    for i, clip in enumerate(data["clips"], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.get("continuity")
        if not isinstance(cont, dict) or cont.get("expression_span") != EXPRESSION_SPAN_BIG:
            continue
        if _clip_is_closeup(clip):
            out.append((i, clip))
    return out


def _clip_character_ids(clip: Dict[str, Any]) -> set:
    """从一条 clip 的文本（template/label/scene/desc + shots + continuity 主体字段）扫出引用的
    CHAR_xx id 集合。用于把「大表情近景」镜回连到具体角色，定位该回连哪个角色的表情库。"""
    blob = " ".join(str(clip.get(k) or "") for k in
                    ("template", "label", "scene", "description", "desc", "subject"))
    for shot in clip.get("shots") or []:
        if isinstance(shot, dict):
            blob += " " + " ".join(str(shot.get(k) or "") for k in ("lens", "desc", "scene"))
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    for k in ("subject", "characters", "carries_identity", "subject_characters"):
        v = cont.get(k)
        if isinstance(v, (list, tuple)):
            blob += " " + " ".join(str(x) for x in v)
        elif v:
            blob += " " + str(v)
    return set(CHARACTER_ID_RE.findall(blob))


def check_core_expression_anchor_coverage(root: str, ep: str) -> None:
    """表情库覆盖闸（把表情锚提到与脸锚同级·付费出视频前强制回连表情库）。

    脸锚有两层防线：`check_anchor_fingerprints`（登记后校漂·BLOCK）+ `check_core_anchor_pinning`
    （核心长线角色「该钉没钉」前置提醒·WARN）。表情锚此前只有前者（`check_expression_anchors`
    登记后校漂），缺「该建没建」的前置闸——于是「第2集的怒和第5集的怒各画各的」只能靠人自觉建库。
    本检查补齐缺失的那层，并在「大表情近景 + 核心长线角色 + 即将付费出视频」这一**确定跨集情绪漂移**
    场景把档位从 WARN 升到 BLOCK（对齐 carries_identity 的 spend 闸思路）：

      · 本集存在跨情绪大表情近景镜（expression_span=大 + 近景/特写/反打），且这些镜引用了某**核心
        长线角色**（_CORE_SCOPE_RE 命中 tier/scope），而该角色在 identity_registry 的所有 form 的
        `expression_anchors` 皆空（=没建表情库）→ BLOCK：必须先建表情库并把镜头尾帧回连到表情锚。

    纯 opt-in：本集没有任何 expression_span=大 的镜（现有 demo/未标镜）= 项目未启用表情跨度追踪 → 跳过，
    与 `check_expression_span_frame_contract`、anchor_sha 全家门控一致。非核心/单元角色不前置 BLOCK
    （对齐 n2d-image「ROI 驱动」，避免误伤一次性配角）。登记后表情锚是否被悄改/未过自检由
    `check_expression_anchors` 负责，本检查只补「核心角色大表情近景但表情库为空」这一覆盖缺口，不重复报。"""
    big_clips = _episode_big_expression_closeup_clips(root, ep)
    if not big_clips:
        return  # opt-in：本集无大表情近景=未启用追踪
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return
    chars = reg.get("characters")
    if isinstance(chars, dict):
        chars = list(chars.values())
    if not isinstance(chars, list):
        return
    core_info: Dict[str, Dict[str, Any]] = {}  # cid -> {name, has_expr}
    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        if not cid or not _CORE_SCOPE_RE.search(f"{c.get('tier') or ''} {c.get('scope') or ''}"):
            continue  # 仅核心长线角色前置高档
        has_expr = any(
            isinstance(fm, dict) and isinstance(fm.get("expression_anchors"), list) and fm.get("expression_anchors")
            for fm in (c.get("forms") or [])
        )
        names = [n.strip() for n in str(c.get("name") or "").replace("／", "/").split("/") if n.strip()]
        core_info[cid] = {"name": names[0] if names else cid, "has_expr": has_expr}
    if not core_info:
        return
    missing: Dict[str, List[int]] = {}  # cid -> [clip 序号]
    for idx, clip in big_clips:
        for cid in _clip_character_ids(clip):
            info = core_info.get(cid)
            if info and not info["has_expr"]:
                missing.setdefault(cid, []).append(idx)
    reg_path = identity_registry_path(root)
    for cid, clip_idxs in sorted(missing.items()):
        info = core_info[cid]
        shown = "、".join(f"clip#{n}" for n in clip_idxs[:8])
        add(BLOCK, "表情一致性", reg_path,
            f"核心长线角色 `{info['name']}({cid})` 出现在本集跨情绪大表情近景镜（{shown}）但未建表情库"
            "（identity_registry 该角色所有 form 的 expression_anchors 皆空）——跨集同情绪近景将各画各的、"
            "情绪一致性崩（脸随表情重画的最贵漂移）。先为该情绪出脸部特写定妆并 "
            "`python3 skills/n2d-image/scripts/image_qc.py <作品根> --finalize-expr CHAR_xx/形态/情绪` "
            "落档钉锚，再把这些镜的止表情尾帧回连到表情锚（reference_group.expressions/expression_anchors 同源派生），"
            "让所有集同情绪近景从同一锚 image2image 派生后再付费出视频。",
            return_to_stage="image")


_VID_CLIP_HEAD_RE = re.compile(r"^##\s*Clip[_\s]*(\d+)", re.M)
_VID_FIRST_FRAME_RE = re.compile(r"\*\*首帧\*\*[^`]*`([^`]+\.png)`")
_VID_END_FRAME_RE = re.compile(r"\*\*尾帧\*\*[^`]*`([^`]+\.png)`")
# 匹配 `**中段锚帧**`（单锚帧）和 `**锚帧K**`（N 锚帧链）两种 prompt 字段
_VID_MID_FRAME_RE = re.compile(r"\*\*(?:中段)?锚帧\s*\d*\*\*[^`]*`([^`]+\.png)`")


def check_video_prompt_frames(root: str, ep: str) -> None:
    """付费出视频前置：核验**视频 prompt（`01_clips.md`）实际引用的首帧/尾帧 PNG**——这是 runner
    （`parse_prompt_pack`）真正喂给后端的路径，与 `storyboard.firstframe_png` 分开誊抄、可能漂；
    `check_storyboard_contract` 查的是 storyboard 字段，这里查**真正提交的那条路径**，互补不重复。
      · 首帧 PNG 缺失 → BLOCK（image2video 必失败、白扣一次最贵的钱）；
      · 声明了尾帧但 PNG 缺失 → WARN（双帧接力降级为单首帧，大表情近景有脸重画风险）；
      · storyboard 标 `need_endframe=true` 但视频 prompt 该 Clip 漏写 `**尾帧**` → WARN（双帧意图誊抄时丢了）；
      · storyboard 声明 `continuity.midframe` 但视频 prompt 该 Clip 漏写 `**中段锚帧**`、或引用的
        锚帧 PNG 缺失 → WARN（拆段意图誊抄时丢失/锚帧漂，runner 会按单段出，中段漂移风险回归）；
      · 视频 prompt 引用的首帧路径 ≠ storyboard.firstframe_png（两侧都存在但不是同一张）→ BLOCK
        （誊抄成另一张存在的 PNG，两侧各查存在全绿、却动了错的首帧）；尾帧不一致 → WARN。"""
    p = os.path.join(root, "出视频", ep, "prompt", "01_clips.md")
    if not os.path.exists(p):
        return  # 视频 prompt 缺失由 check_video_prompt_overview 负责
    text = open(p, encoding="utf-8").read()
    need_end: Dict[int, bool] = {}
    need_mid: Dict[int, int] = {}  # Clip → 声明的锚帧数（midframe=1；anchors=len）
    sb_first: Dict[int, str] = {}  # Clip → storyboard.firstframe_png（路径相等校验基准）
    sb_end: Dict[int, str] = {}    # Clip → storyboard.continuity.endframe_png
    sb = load_json(storyboard_path(root, ep))  # 只读取 need_endframe/midframe/anchors/首尾帧，不重复报 storyboard 缺失
    if isinstance(sb, dict) and isinstance(sb.get("clips"), list):
        for i, clip in enumerate(sb["clips"], 1):
            if isinstance(clip, dict) and isinstance(clip.get("continuity"), dict):
                cont = clip["continuity"]
                need_end[i] = cont.get("need_endframe") is True
                if isinstance(cont.get("midframe"), dict):
                    need_mid[i] = 1
                elif isinstance(cont.get("anchors"), list):
                    need_mid[i] = len(cont["anchors"])
                if clip.get("firstframe_png"):
                    sb_first[i] = str(clip["firstframe_png"]).strip()
                if cont.get("endframe_png"):
                    sb_end[i] = str(cont["endframe_png"]).strip()

    def _missing(rel: str) -> bool:
        full = rel if os.path.isabs(rel) else os.path.join(root, rel)
        return not os.path.exists(full)

    def _same_path(a: str, b: str) -> bool:
        """两条 PNG 引用是否指向同一文件：归一化（去 ./、统一分隔符、相对根解析）后比对。"""
        def _norm(rel: str) -> str:
            full = rel if os.path.isabs(rel) else os.path.join(root, rel)
            return os.path.normpath(full)
        return _norm(a) == _norm(b)

    heads = list(_VID_CLIP_HEAD_RE.finditer(text))
    for idx, m in enumerate(heads):
        num = int(m.group(1))
        block = text[m.end(): heads[idx + 1].start() if idx + 1 < len(heads) else len(text)]
        loc = f"出视频/{ep}/prompt/01_clips.md Clip_{num:02d}"
        fm = _VID_FIRST_FRAME_RE.search(block)
        if fm and _missing(fm.group(1).strip()):
            add(BLOCK, "首帧", loc,
                f"视频 prompt 引用的首帧 PNG 不存在：{fm.group(1).strip()}——image2video 调用会失败、"
                "白扣一次最贵工位的钱，先补帧/改路径再出视频。", return_to_stage="image")
        elif fm and num in sb_first and not _missing(fm.group(1).strip()) \
                and not _same_path(fm.group(1).strip(), sb_first[num]):
            add(BLOCK, "首帧", loc,
                f"视频 prompt 首帧引用 `{fm.group(1).strip()}` ≠ storyboard.firstframe_png `{sb_first[num]}`——"
                "两侧各查存在都绿，但誊抄漂成另一张图=image2video 会动错的首帧（最贵工位上动错人/错构图）。"
                "改回与 storyboard 一致的那张，或回 n2d-script 同步 firstframe_png。", return_to_stage="video")
        em = _VID_END_FRAME_RE.search(block)
        if em and _missing(em.group(1).strip()):
            add(WARN, "尾帧", loc,
                f"视频 prompt 声明了尾帧但 PNG 不存在：{em.group(1).strip()}——双帧接力会降级为单首帧"
                "（大表情近景有脸重画风险），先补尾帧或确认降级。", return_to_stage="image")
        elif em and num in sb_end and not _missing(em.group(1).strip()) \
                and not _same_path(em.group(1).strip(), sb_end[num]):
            add(WARN, "尾帧", loc,
                f"视频 prompt 尾帧引用 `{em.group(1).strip()}` ≠ storyboard.endframe_png `{sb_end[num]}`——"
                "誊抄漂成另一张尾帧=双帧插值的落点错，接缝/大表情近景插到错的止帧。确认是有意改写否则改回。",
                return_to_stage="video")
        elif em is None and need_end.get(num):
            add(WARN, "尾帧", loc,
                "storyboard 标 need_endframe=true 但视频 prompt 此 Clip 漏写 `**尾帧**` 引用——"
                "双帧接力意图在誊抄时丢失，runner 会按单首帧出，大表情近景有脸重画风险。",
                return_to_stage="image")
        mids = _VID_MID_FRAME_RE.findall(block)
        for rel in mids:
            if _missing(rel.strip()):
                add(WARN, "中段锚帧", loc,
                    f"视频 prompt 声明了锚帧但 PNG 不存在：{rel.strip()}——拆段接力会降级"
                    "（opt-in 的中段漂移风险回归），先补 `_mid`/`_aK` 锚帧或确认降级。", return_to_stage="image")
        declared = need_mid.get(num, 0)
        if len(mids) < declared:
            add(WARN, "中段锚帧", loc,
                f"storyboard 声明了 {declared} 个锚帧（continuity.midframe/anchors）但视频 prompt 此 Clip 只引用了 {len(mids)} 个"
                "`**中段锚帧**`/`**锚帧K**`——拆段意图在誊抄时丢失，runner 会按少段出，付了出图成本却没拿到中段锚定。",
                return_to_stage="video")


def check_input_frame_qc(root: str, ep: str) -> None:
    """出视频前置（省最贵那一步的钱）：图生视频是 n2d 最贵工位，image2video 会**忠实把首帧缺陷动起来**——
    崩脸的首帧 → 崩脸的片。所以付费出视频前先确认输入首帧已过出图落档机检 `image_qc`。
    读持久化结果（`生产数据/image_qc/<ep>/image_qc_<ep>.json`），**不重跑像素引擎**（每 Clip 提交都重跑太贵）：
      · `summary.hard_blocks>0`（崩脸 / 接缝断 / 降级精度近景 / 非法 CHAR）→ BLOCK，回 n2d-image 修复 + 重跑 QC；
      · 无 image_qc 结果 / 旧版 image_qc 无角色脸覆盖结果 → BLOCK；
      · `qc_environment.precision_level!=full` → BLOCK（降级精度不得进入 video）；
      · 角色脸定妆比对覆盖缺口 → BLOCK；
      · image_qc 结果早于最新 PNG（出图后改过帧没重验）→ BLOCK。"""
    png_dir = os.path.join(root, "出图", ep, "图片")
    pngs = glob.glob(os.path.join(png_dir, "*.png"))
    if not pngs:
        return  # check_image_assets 已 BLOCK「本集没有分镜 PNG」
    qc_path = os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json")
    prohibited = _prohibited_face_patch_outputs(root, ep)
    if prohibited:
        sample = "、".join(p["png"] for p in prohibited[:5])
        more = f" 等 {len(prohibited)} 张" if len(prohibited) > 5 else ""
        add(BLOCK, "出图落档QC", _production_events_path(root),
            f"{PROHIBITED_FACE_PATCH_LABEL}：发现 {len(prohibited)} 张最新 image 落档事件来自本地贴脸/换脸/裁脸贴回画面"
            f"（{sample}{more}）。embedding 分数只是证据，不是目标；不能为了过脸部 embedding QC 把定妆脸盖到镜头上。"
            "这些图不能进 video，必须回 n2d-image 用真实重抽或官方 image2image 派生替换，并重跑 image_qc。",
            return_to_stage="image")
        return
    qc = load_json(qc_path)
    if not isinstance(qc, dict):
        add(BLOCK, "出图落档QC", qc_path,
            "出视频前未见 image_qc 落档机检结果——输入首帧的崩脸/降级精度近景未经核验。"
            "先跑 `dashboard gate --stage image`（或 `image_qc.py`）再出视频，别花图生视频的钱动画一张未验首帧。",
            return_to_stage="image")
        return
    hard = int((qc.get("summary") or {}).get("hard_blocks") or 0)
    if hard > 0:
        add(BLOCK, "出图落档QC", qc_path,
            f"输入首帧 image_qc 仍有 {hard} 项硬阻断（崩脸/接缝断/降级精度近景/非法 CHAR）——"
            "图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。",
            return_to_stage="image")
        return
    coverage = qc.get("face_reference_coverage")
    if not isinstance(coverage, dict):
        add(BLOCK, "出图落档QC", qc_path,
            "输入首帧 image_qc 是旧版结果，缺 `face_reference_coverage` 逐镜角色脸定妆比对覆盖证据。"
            "重跑 image_qc，确认每张已落档角色 PNG 都逐张对定妆/身份主参考过 full QC 后再出视频。",
            return_to_stage="image")
        return
    env = qc.get("qc_environment") or {}
    precision = str(env.get("precision_level") or "")
    if precision != "full":
        add(BLOCK, "出图落档QC", qc_path,
            f"输入首帧 image_qc 精度为 `{precision or 'unknown'}`，不是 full——"
            "含角色镜头图必须用 full 精度脸部参考比对后才能进 video；补 insightface/onnxruntime/buffalo_l 后重跑 image_qc。",
            return_to_stage="image")
        return
    missing = coverage.get("missing") or []
    if coverage.get("verdict") == "block" or missing:
        add(BLOCK, "出图落档QC", qc_path,
            f"角色脸定妆比对覆盖未过：{len(missing)} 张已落档角色图缺 full 比对/未通过比对。"
            "这是进入 video 的硬闸门；回 n2d-image 补检、重抽或修复后重跑 image_qc。",
            return_to_stage="image")
        return
    try:
        if max(os.path.getmtime(p) for p in pngs) > os.path.getmtime(qc_path) + 1:
            add(BLOCK, "出图落档QC", qc_path,
                "输入首帧晚于上次 image_qc（出图后改过帧未重验）——出视频前先重跑 image_qc，避免动画一张未验首帧。",
                return_to_stage="image")
            return
    except OSError:
        pass
    if fingerprint_is_fresh is None:
        add(BLOCK, "出图落档QC", qc_path,
            "无法加载 image_qc 输入指纹校验器（skill_snapshot.fingerprint_is_fresh）——"
            "不能确认该 QC 报告对应当前 prompt/registry/PNG；修复环境并重跑 image_qc。",
            return_to_stage="image")
        return
    fresh = fingerprint_is_fresh(qc.get("inputs_fingerprint"), root)  # type: ignore[misc]
    if fresh is None:
        add(BLOCK, "出图落档QC", qc_path,
            "输入首帧 image_qc 缺 `inputs_fingerprint`（旧版或手写报告），无法证明报告对应当前 prompt/registry/PNG。"
            "重跑 image_qc 生成带输入指纹的报告后再出视频。",
            return_to_stage="image")
        return
    if fresh is False:
        add(BLOCK, "出图落档QC", qc_path,
            "输入首帧 image_qc 的 `inputs_fingerprint` 与当前文件失配（prompt、registry 或 PNG 已变）。"
            "当前结论作废；出视频前先重跑 image_qc。",
            return_to_stage="image")
        return
    # 防伪造：freshness 只证明「报告声明的那批文件没变」，不证明「真把全部 PNG 都验了」——一份手写/陈旧
    # 报告可以只声明 1 张图、算对那张 sha 就过 freshness。这里独立枚举 出图/<ep>/图片/ 的真实 PNG，核对
    # image_qc 指纹是否覆盖每一张实际落档图（按文件名）；有真实 PNG 不在报告核验范围 = 这张根本没被机检 → BLOCK。
    recorded = qc.get("inputs_fingerprint") or {}
    declared_png = {os.path.basename(k) for k in (recorded.get("files") or {}) if str(k).endswith(".png")}
    uncovered = sorted({os.path.basename(p) for p in pngs} - declared_png)
    if uncovered:
        sample = "、".join(uncovered[:5]) + (f" 等 {len(uncovered)} 张" if len(uncovered) > 5 else "")
        add(BLOCK, "出图落档QC", qc_path,
            f"image_qc 指纹只覆盖了报告声明的子集，{len(uncovered)} 张实际落档 PNG 不在核验范围（{sample}）——"
            "这是手写/伪造/陈旧报告的典型特征：声明少量文件算对 sha 就想过 freshness，但这些图根本没被机检过。"
            "重跑 image_qc，让 `inputs_fingerprint` 覆盖 出图/<ep>/图片/ 的全部 PNG 后再出视频。",
            return_to_stage="image")
        return


def ffprobe_json(path: str) -> Optional[dict]:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
            text=True,
        )
        return json.loads(out)
    except Exception:
        return None


def duration(path: str) -> Optional[float]:
    data = ffprobe_json(path)
    if not data:
        return None
    try:
        return float(data.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        return None


def has_audio(path: str) -> Optional[bool]:
    data = ffprobe_json(path)
    if not data:
        return None
    return any(s.get("codec_type") == "audio" for s in data.get("streams", []))


def clip_files(root: str, ep: str) -> List[str]:
    return sorted(glob.glob(os.path.join(root, "出视频", ep, "视频", "*.mp4")))


def stripped_audio_artifacts(root: str, ep: str) -> List[str]:
    """Artifacts that show native clip audio was stripped during n2d-video.

    Source clips under 出视频/第N集/视频 must stay as AI platform originals.
    Compose may create no-audio working files under 合成/第N集/_clipcache, but
    those must not become the formal video-stage assets.
    """
    vid = os.path.join(root, "出视频", ep, "视频")
    if not os.path.isdir(vid):
        return []
    patterns = (
        "*.noaudio.mp4",
        "*_noaudio.mp4",
        "*-noaudio.mp4",
        "*no_audio*.mp4",
        "*silent*.mp4",
        "*无音轨*.mp4",
        "*静音*.mp4",
    )
    hits: List[str] = []
    for pattern in patterns:
        hits.extend(glob.glob(os.path.join(vid, pattern)))
    for dirname in ("_raw_with_audio", "raw_with_audio", "原片含音轨", "带音轨原片"):
        path = os.path.join(vid, dirname)
        if os.path.isdir(path):
            hits.append(path)
    return sorted(set(hits))


def check_video_stage_raw_output_policy(root: str, ep: str) -> None:
    hits = stripped_audio_artifacts(root, ep)
    if hits:
        add(
            BLOCK,
            "原生音轨",
            hits[0],
            "出视频阶段必须保留 AI 平台原片；不得在 `出视频/第N集/视频/` 放 `.noaudio`/静音派生或把原片挪到 `_raw_with_audio/`。"
            "原生音轨统一交 n2d-compose 按 `视频原生音轨` 策略丢弃/混入/保留。",
        )


def voice_track_exists(root: str, ep: str) -> bool:
    voice_dir = os.path.join(root, "合成", ep, "配音")
    return any(os.path.isfile(os.path.join(voice_dir, name)) for name in ("voice_zh.wav", "voice_en.wav", "voice_zh_fitted.wav", "voice_en_fitted.wav"))


def voice_manifest_rows(root: str, ep: str) -> Optional[List[Dict[str, object]]]:
    path = manifest_path(root, ep)
    if not path:
        return None
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    return [row for row in data if isinstance(row, dict)]


def voiceover_role(role: str) -> bool:
    text = (role or "").strip()
    low = text.lower()
    return (
        "旁白" in text
        or "系统" in text
        or low in {"narrator", "voiceover", "system", "sys"}
    )


def voice_track_scope(root: str, ep: str) -> str:
    """Return none / voiceover_only / dialogue_or_unknown for compose double-voice policy."""
    if not voice_track_exists(root, ep):
        return "none"
    rows = voice_manifest_rows(root, ep)
    if not rows:
        return "dialogue_or_unknown"
    roles = [str(row.get("角色") or "").strip() for row in rows]
    if roles and all(role and voiceover_role(role) for role in roles):
        return "voiceover_only"
    return "dialogue_or_unknown"


def check_native_audio_compose_policy(root: str, ep: str, audio_hits: List[str]) -> None:
    policy = native_audio_policy(root)
    mode = native_audio_policy_mode(policy)
    overview = os.path.join(root, "出视频", ep, "prompt", "00_总览.md")
    overview_text = open(overview, encoding="utf-8").read() if os.path.isfile(overview) else ""

    if is_native_av_production(root):
        # 原生音画：台词就在 clip 原生音轨里；compose.sh 默认自动「保留原片音轨」（除非显式丢弃），
        # 所以不能照搬「丢弃会剥离台词」的误报——按有效策略=保留校验。
        if not audio_hits:
            add(WARN, "原生音画", os.path.join(root, "出视频", ep, "视频"),
                "原生音画模式但未在 clip 检测到原生音频流；说话镜台词应由视频后端原生生成，确认出视频后端是否输出了同步音轨")
            return
        if mode == NATIVE_AUDIO_DISCARD:
            add(WARN, "原生音画", os.path.join(root, "_设置.md"),
                "原生音画：未显式设 视频原生音轨，compose 将自动「保留原片音轨」以免丢失原生台词（确需丢弃设 VIDEO_NATIVE_AUDIO_POLICY_EXPLICIT=1）")
        if overview_text:
            check_native_audio_opt_in_overview(root, ep, overview_text, overview)
            check_native_av_physical_contract(root, ep, overview_text, overview)
            check_native_av_physics_sidecar(root, ep, native_av_physics_required(root, ep, overview_text))
        else:
            add(WARN, "原生音画", overview, "缺出视频总览；建议声明 native_speech 路由（台词+口型由后端原生生成）")
        scope = voice_track_scope(root, ep)
        if scope == "voiceover_only":
            add(WARN, "原生音画", os.path.join(root, "合成", ep, "配音"),
                "原生音画 clip 含原生台词，同时检测到旁白/系统 n2d-voice 轨；允许作为后期旁白层，但合成前需确认不与原生台词重叠")
        elif scope == "dialogue_or_unknown":
            add(BLOCK, "原生音画", os.path.join(root, "合成", ep, "配音"),
                "原生音画 clip 已含原生台词，又存在无法确认仅为旁白/系统的 n2d-voice 配音轨；正式合成会双人声，请移除角色配音或把配音清单限定为旁白/系统层")
        return

    if not audio_hits:
        if mode != NATIVE_AUDIO_DISCARD:
            add(WARN, "原生音画", os.path.join(root, "_设置.md"), f"`视频原生音轨={policy}`，但当前 clip 未检测到原生音频流；该设置本集不会生效")
        return

    if mode == NATIVE_AUDIO_DISCARD:
        add(WARN, "原生音轨", audio_hits[0], "clip 含原生音轨；当前策略=丢弃，compose 会剥离以避免原生台词与配音双人声")
        return

    if not overview_text:
        add(BLOCK, "原生音画", overview, f"`视频原生音轨={policy}` 且 clip 含音频流，但缺出视频总览；无法核验 opt-in 清单")
    else:
        check_native_audio_opt_in_overview(root, ep, overview_text, overview)
        check_native_av_physical_contract(root, ep, overview_text, overview)
        check_native_av_physics_sidecar(root, ep, native_av_physics_required(root, ep, overview_text))

    if mode == NATIVE_AUDIO_KEEP and voice_track_exists(root, ep):
        add(BLOCK, "原生音画", os.path.join(root, "合成", ep, "配音"), "`视频原生音轨=保留原片音轨` 且存在 n2d-voice 配音轨；正式合成会双人声，改为「低音量混入环境声」或「丢弃」")


def check_video_assets(root: str, ep: str) -> None:
    check_video_stage_raw_output_policy(root, ep)
    clips = clip_files(root, ep)
    if not clips:
        add(BLOCK, "视频", os.path.join(root, "出视频", ep, "视频"), "缺 clip MP4")
        return
    sb = load_storyboard(root, ep)
    if sb and len(clips) != len(sb.get("clips", [])):
        add(WARN, "视频", os.path.join(root, "出视频", ep, "视频"), f"clip 数 {len(clips)} 与 storyboard clips {len(sb.get('clips', []))} 不一致")
    audio_probe = [(c, has_audio(c)) for c in clips]
    audio_hits = [c for c, a in audio_probe if a]
    unprobeable = [c for c, a in audio_probe if a is None]
    # 双人声硬闸门（原生台词 + n2d-voice 配音）依赖 ffprobe 探测 clip 原生音轨。ffprobe 缺失时
    # has_audio 返回 None → audio_hits 收缩为空 → 双人声 BLOCK 静默到不了。review 是交付边界：
    # 探不了原生音轨又存在配音轨 = 双人声硬闸门其实没校验过，默认 BLOCK（与降级精度一致性审计同一套
    # 「缺核心检测工具→交付边界拦截」策略，逃生口同为 N2D_ALLOW_DEGRADED_QC=1·留痕自负其责）。
    if unprobeable and voice_track_exists(root, ep):
        allow_degraded = os.environ.get("N2D_ALLOW_DEGRADED_QC") == "1"
        sev = WARN if allow_degraded else BLOCK
        tail = ("（已显式 N2D_ALLOW_DEGRADED_QC 放行）" if allow_degraded
                else "装 ffprobe 后重跑，或显式 N2D_ALLOW_DEGRADED_QC=1 放行并自负其责。")
        add(sev, "原生音画", os.path.join(root, "出视频", ep, "视频"),
            f"ffprobe 不可用，{len(unprobeable)} 个 clip 无法探测原生音轨——"
            f"「原生台词 + n2d-voice 配音 = 双人声」硬闸门无法校验，交付边界不放行。{tail}")
    check_native_audio_compose_policy(root, ep, audio_hits)
    shots = load_json(os.path.join(root, "脚本", ep, "镜头时长.json"))
    if isinstance(shots, dict):
        target = sum(float(v) for v in shots.values())
        actuals = [duration(c) for c in clips]
        if all(d is not None for d in actuals):
            total = sum(d for d in actuals if d is not None)
            if abs(total - target) > 1.0:
                add(WARN, "时长", ep, f"clip 总长 {total:.2f}s 与镜头时长累计 {target:.2f}s 差 {abs(total-target):.2f}s")


def check_compose_inputs(root: str, ep: str) -> None:
    check_video_assets(root, ep)
    check_placeholder_policy(root, ep, "compose")
    zh = os.path.join(root, "脚本", ep, "字幕_中文.srt")
    if not os.path.isfile(zh):
        # 原生音画：说话镜台词由视频后端原生生成、不跑逐句配音，finalize 也不产 SRT
        # （字幕走成片后 whisperx 词级对齐，见 n2d SKILL）——此处只提醒、不硬闸。
        if is_native_av_production(root):
            add(WARN, "字幕", zh, "原生音画：暂无中文字幕；成片后请用 whisperx 对原生台词做词级对齐再补字幕")
        else:
            add(BLOCK, "字幕", zh, "缺中文字幕")


def check_voice_conditioned_lipsync_policy(root: str, ep: str, storyboard: Dict[str, object]) -> None:
    """配音条件口型 (lipsync_condition_only) 校验：音轨必须丢弃原生，必须有 voice-first 轨。"""
    clips = storyboard.get("clips") or []
    lp_clips = [c for c in clips if isinstance(c, dict) and c.get("native_audio_policy") == "lipsync_condition_only"]
    if not lp_clips:
        return

    # lipsync_condition_only 模式下，模型音频只作口型参考，合成时必须丢弃
    policy = native_audio_policy(root)
    mode = native_audio_policy_mode(policy)
    if mode != NATIVE_AUDIO_DISCARD:
        add(BLOCK, "口型同步", os.path.join(root, "_设置.md"),
            f"检测到 {len(lp_clips)} 个 lipsync_condition_only 镜（后端音频参考口型），合成时必须「丢弃」模型原生音频，"
            f"否则会与主配音轨重叠。当前设置：视频原生音轨={policy}。")
    
    if not voice_track_exists(root, ep):
        add(BLOCK, "口型同步", os.path.join(root, "合成", ep, "配音"),
            f"检测到 {len(lp_clips)} 个配音条件口型镜，但未检测到主配音轨 (voice_zh.wav)；该模式依赖配音驱动口型，请先 n2d-voice。")


def _clip_label(value: Any) -> List[str]:
    labels: List[str] = []
    if isinstance(value, int):
        labels.append(f"Clip_{value:02d}")
    text = str(value or "")
    for m in re.finditer(r"(?i)(?:Clip|镜头|镜)\s*[_ -]?0*([0-9]+)", text):
        labels.append(f"Clip_{int(m.group(1)):02d}")
    out: List[str] = []
    for item in labels:
        if item not in out:
            out.append(item)
    return out


def _artifact_refs(text: str) -> List[str]:
    pattern = r"(?:出图|出视频|合成|脚本|设定库|合规)/[^\s，。；;|)）]+"
    out: List[str] = []
    for m in re.finditer(pattern, text or ""):
        item = m.group(0).rstrip("，。；;:：")
        if item not in out:
            out.append(item)
    return out


def _continuity_extra(row: Dict[str, Any], ep: str, default_stage: str,
                      default_scope: str, default_artifacts: Sequence[str]) -> Dict[str, object]:
    shots: List[str] = []
    for key in ("shot", "heading", "target", "png", "message", "loc"):
        shots.extend(_clip_label(row.get(key)))
    artifacts = list(default_artifacts)
    for key in ("source", "target", "png", "message", "loc"):
        artifacts.extend(_artifact_refs(str(row.get(key) or "")))
    png = str(row.get("png") or "")
    if png and "/" not in png:
        artifacts.append(f"出图/{ep}/图片/{png}")
    return {
        "return_to_stage": row.get("return_to_stage") or default_stage,
        "rerun_scope": row.get("rerun_scope") or default_scope,
        "affected_shots": sorted(set(shots)),
        "affected_artifacts": sorted(set(a for a in artifacts if a)),
    }


def _add_continuity_rows(dim: str, rows: Sequence[Dict[str, Any]], ep: str, *,
                         default_stage: str, default_scope: str,
                         default_artifacts: Sequence[str]) -> None:
    for row in rows:
        verdict = str(row.get("verdict") or "ok")
        if verdict not in {"block", "warn"}:
            continue
        sev = BLOCK if verdict == "block" else WARN
        loc = str(row.get("target") or row.get("source") or row.get("png") or row.get("heading") or dim)
        msg = str(row.get("message") or "一致性机检发现下游继承风险")
        missing = row.get("missing_terms")
        if missing:
            msg += "；缺：" + "、".join(str(x) for x in list(missing)[:8])
        add(sev, dim, loc, msg, **_continuity_extra(row, ep, default_stage, default_scope, default_artifacts))


def check_semantic_lineage(root: str, ep: str) -> None:
    res = semc.analyze(root, ep)
    _add_continuity_rows(
        "语义谱系(P0)",
        [r for r in res.get("findings", []) if isinstance(r, dict)],
        ep,
        default_stage="script_stage2",
        default_scope="修 storyboard→出图/出视频 prompt 的语义继承缺口；必要时重跑 n2d-script 阶段2。",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt", f"出视频/{ep}/prompt"),
    )


def check_state_continuity(root: str, ep: str) -> None:
    res = statec.analyze(root, ep)
    _add_continuity_rows(
        "状态百科(P1)",
        [r for r in res.get("alerts", []) if isinstance(r, dict)],
        ep,
        default_stage="image",
        default_scope="修 visual_state_ledger / 出图分镜 prompt 的角色/道具状态锁；道具 lifecycle 未结构化的升级为 {states,transitions}；必要时回 storyboard / asset_registry 修状态演进。",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md", "出图/共享/visual_state_ledger.json", "出图/共享/asset_registry.json"),
    )


def check_multimodal_continuity(root: str, ep: str) -> None:
    res = mmc.analyze(root, ep)
    _add_continuity_rows(
        "多模态(P2)",
        [r for r in res.get("shots", []) if isinstance(r, dict)],
        ep,
        default_stage="image",
        default_scope="按离群道具/场景/法宝参考组只重出受影响镜头；必要时补资产定妆 taxonomy。",
        default_artifacts=(f"出图/{ep}/prompt/01_分镜出图.md", f"出图/{ep}/图片"),
    )


def check_subtitle_alignment(root: str, ep: str) -> None:
    """字幕对齐(L1)：双语短语边界/阅读速度/译文完整性（补 mechanical_check 条数对账盲区）。"""
    res = sa.analyze(root, ep)
    _add_continuity_rows(
        "字幕对齐(L1)",
        [r for r in res.get("rows", []) if isinstance(r, dict)],
        ep,
        default_stage="script_stage2",
        default_scope="回 n2d-script 阶段2重跑 finalize_storyboard / 修翻译层，对齐中↔英断句与阅读速度。",
        default_artifacts=(f"脚本/{ep}/字幕_中文.srt", f"脚本/{ep}/字幕_英文.srt"),
    )


TRANSLATION_GLOSSARY_CATEGORIES = ("人名", "称谓", "境界", "招式", "口头禅", "系统提示语")
TRANSLATION_CATEGORY_ALIASES = {
    "人名": ("人名", "角色", "character", "name"),
    "称谓": ("称谓", "尊称", "honorific", "address"),
    "境界": ("境界", "等级", "realm", "rank"),
    "招式": ("招式", "功法", "技能", "spell", "move"),
    "口头禅": ("口头禅", "语域", "catchphrase"),
    "系统提示语": ("系统提示语", "系统", "system_prompt", "system"),
}


def translation_glossary_path(root: str) -> str:
    return os.path.join(root, "设定库", "translation_glossary.json")


def _translation_glossary_terms(data: object) -> List[Mapping[str, Any]]:
    if isinstance(data, dict):
        raw = data.get("terms")
        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, Mapping)]
        rows: List[Mapping[str, Any]] = []
        for cn, en in data.items():
            if cn in {"kind", "version", "coverage", "notes"}:
                continue
            if isinstance(en, str) and en.strip():
                rows.append({"cn": cn, "en": en})
        return rows
    return []


def _translation_term_has_pair(term: Mapping[str, Any]) -> bool:
    source = term.get("cn") or term.get("zh") or term.get("source") or term.get("term") or term.get("name")
    target = term.get("en") or term.get("target") or term.get("canonical") or term.get("translation")
    return bool(str(source or "").strip() and str(target or "").strip())


def _translation_category_covered(data: Mapping[str, Any], terms: Sequence[Mapping[str, Any]], category: str) -> bool:
    coverage = data.get("coverage") if isinstance(data.get("coverage"), Mapping) else {}
    for alias in TRANSLATION_CATEGORY_ALIASES[category]:
        value = coverage.get(alias) if isinstance(coverage, Mapping) else None
        if value in (True, "ready", "done", "not_applicable", "none", "无", "不适用"):
            return True
    for term in terms:
        blob = json.dumps(term, ensure_ascii=False).lower()
        if any(alias.lower() in blob for alias in TRANSLATION_CATEGORY_ALIASES[category]):
            return True
    return False


def check_translation_glossary_release_gate(root: str, ep: str, stage: str) -> None:
    if stage not in {"compose", "review"}:
        return
    required = _project_has_english_subtitles(root, ep) or _project_has_overseas_release_target(root)
    if not required:
        return
    path = translation_glossary_path(root)
    data = load_json(path)
    if not isinstance(data, dict):
        add(
            BLOCK,
            "译名发布闸门",
            path,
            "海外/英文字幕发布前缺 translation_glossary.json；必须锁人名、称谓、境界、招式、口头禅、系统提示语的 canonical 译名，"
            "并让字幕生成与 OCR/字幕检查同用这份 glossary。",
            return_to_stage="script_stage2",
        )
        return
    terms = _translation_glossary_terms(data)
    if not terms or not all(_translation_term_has_pair(term) for term in terms):
        add(
            BLOCK,
            "译名发布闸门",
            path,
            "translation_glossary.json 必须包含非空 terms[]，且每条至少有 cn/source 与 en/canonical；不能只写空壳或说明文字。",
            return_to_stage="script_stage2",
        )
        return
    missing_categories = [cat for cat in TRANSLATION_GLOSSARY_CATEGORIES if not _translation_category_covered(data, terms, cat)]
    if missing_categories:
        add(
            BLOCK,
            "译名发布闸门",
            path,
            "translation_glossary.json 缺覆盖类目：" + "、".join(missing_categories) +
            "；无该类内容也要在 coverage 标 not_applicable，避免海外字幕/称谓/招式名临场多译。",
            return_to_stage="script_stage2",
        )


STRICT_ADVISORY_DIMENSIONS = {
    "轴线视线(X1)",
    "音画同步(AV1)",
    "节奏密度",
    "节奏密度(Rhythm)",
    "持有账本(POS)",
    "生成配方(RCP)",
    "强配方Schema(RCP2)",
    "场景平面(FP1)",
    "人审校准集(CAL)",
    "译名一致(TX1)",
    "表情连续(EXP1)",
    "音乐母题(LM1)",
    "环境声(AMB)",
    "运动质量(MOT1)",
    "相机空间轨迹(CAM1)",
    "主体视频一致(S2V)",
    "高动态成片证据(SPECV)",
}
KEY_SCENE_MARKERS = ("关键", "钩子", "封面", "反转", "高潮", "爆点", "key", "hook", "climax")
# 口型在「带对白的近景/特写」上最容易被观众抓——AV1 的对白近景 WARN 即便不重复/非关键/非交付边界，
# production 下也升 BLOCK（口型对不上的脸部大特写是硬伤）。
CLOSEUP_MARKERS = ("近景", "特写", "大特写", "脸部", "面部", "反打", "过肩", "cu", "mcu", "ecu", "close-up", "closeup")


def _consistency_signoff_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"consistency_advisory_signoff_{ep}.json")


def _row_is_key_scene(row: Mapping[str, Any]) -> bool:
    text = json.dumps(row, ensure_ascii=False).lower()
    return any(marker.lower() in text for marker in KEY_SCENE_MARKERS)


def _row_is_dialogue_closeup(row: Mapping[str, Any]) -> bool:
    """AV1 口型 finding 是否落在带对白的近景/特写（口型穿帮最刺眼处）。"""
    text = json.dumps(row, ensure_ascii=False).lower()
    return any(marker in text for marker in CLOSEUP_MARKERS)


def _consistency_finding_hash(row: Mapping[str, Any]) -> str:
    stable = {
        "dimension": row.get("dimension") or row.get("dim") or "",
        "message": row.get("message") or row.get("msg") or row.get("reason") or "",
        "affected_shots": row.get("affected_shots") if isinstance(row.get("affected_shots"), list) else [],
        "affected_artifacts": row.get("affected_artifacts") if isinstance(row.get("affected_artifacts"), list) else [],
        "loc": row.get("loc") or row.get("path") or "",
    }
    blob = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _signoff_expiry_ok(value: object) -> bool:
    return _override_expiry_ok(value)


def _advisory_row_signed_off(root: str, ep: str, row: Mapping[str, Any]) -> bool:
    data = load_json(_consistency_signoff_path(root, ep))
    if not isinstance(data, dict):
        return False
    accepted = data.get("accepted") or data.get("signoffs") or []
    dim = str(row.get("dimension") or row.get("dim") or "")
    msg = str(row.get("message") or row.get("msg") or "")
    loc = " ".join(str(x) for x in (row.get("affected_artifacts") or []) if x) if isinstance(row.get("affected_artifacts"), list) else ""
    shots = " ".join(str(x) for x in (row.get("affected_shots") or []) if x) if isinstance(row.get("affected_shots"), list) else ""
    row_hash = _consistency_finding_hash(row)
    for item in accepted:
        if not isinstance(item, dict):
            continue
        if item.get("accepted") is not True:
            continue
        if not str(item.get("reviewer") or "").strip():
            continue
        if not str(item.get("reason") or "").strip():
            continue
        if not _signoff_expiry_ok(item.get("expires_at") or item.get("expires")):
            continue
        if str(item.get("finding_hash") or "").strip() == row_hash:
            return True
        if str(item.get("dimension") or item.get("dim") or "").strip() != dim:
            continue
        message_token = str(item.get("message_contains") or "").strip()
        loc_token = str(item.get("loc_contains") or "").strip()
        shot_token = str(item.get("shot") or item.get("affected_shot") or "").strip()
        if message_token and message_token in msg:
            return True
        if loc_token and loc_token in loc:
            return True
        if shot_token and shot_token in shots:
            return True
    return False


def _strict_advisory_should_block(root: str, ep: str, stage: str, row: Mapping[str, Any], summary: Mapping[str, Any]) -> Tuple[bool, str]:
    if consistency_release_profile(root, stage, ep) != "production":
        return False, ""
    dim = str(row.get("dimension") or row.get("dim") or "")
    if dim not in STRICT_ADVISORY_DIMENSIONS:
        return False, ""
    by_dim = summary.get("by_dim") if isinstance(summary.get("by_dim"), Mapping) else {}
    stat = by_dim.get(dim) if isinstance(by_dim.get(dim), Mapping) else {}
    repeated = int(stat.get("warn") or 0) >= 2
    key_scene = _row_is_key_scene(row)
    deliverable = stage in {"compose", "review"}
    # AV1 专属：带对白的近景/特写口型偏移即便孤例也升 block（口型对不上的大特写是观众第一眼硬伤）。
    dialogue_closeup = dim == "音画同步(AV1)" and _row_is_dialogue_closeup(row)
    if not (repeated or key_scene or deliverable or dialogue_closeup):
        return False, ""
    if _advisory_row_signed_off(root, ep, row):
        return False, "已由 consistency_advisory_signoff 签收"
    reason = ("对白近景口型" if dialogue_closeup else "重复同维度" if repeated
              else "关键场景" if key_scene else "交付边界")
    return True, reason


def check_consistency_audit_gate(root: str, ep: str, stage: str = "review") -> None:
    """Final consistency suite gate.

    The detector bundle is useful only if it is on a mandatory path.  Run the
    full audit before image(出图后)/compose/review and mirror active findings into
    gate output; the complete report remains in 生产数据/consistency_findings_<ep>.json.

    `stage` gates how 降级精度 is treated: compose/review are deliverable boundaries,
    so non-full precision (insightface 缺失→脸/像素一致性其实没验证) is a BLOCK there
    unless explicitly waived via `N2D_ALLOW_DEGRADED_QC=1`. At the image 出图后闸门
    降级精度只降为 WARN（不硬拦无依赖产线）——确定性 🔴 维度（手部/天气/身高/称谓/动作）
    照常 BLOCK，把它们挡在最贵的出视频之前。
    """
    script = os.path.join(SCRIPT_DIR, "consistency_audit.py")
    loc = os.path.join(root, "生产数据", f"consistency_findings_{ep}.json")
    profile = consistency_release_profile(root, stage, ep)
    try:
        proc = subprocess.run(
            [sys.executable, script, root, ep, "--json", "--profile", profile],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=1200,
        )
    except Exception as exc:
        add(BLOCK, "一致性总审", loc, f"consistency_audit.py 无法运行：{type(exc).__name__}: {exc}", return_to_stage="review")
        return
    try:
        res = json.loads(proc.stdout or "{}")
    except Exception as exc:
        add(
            BLOCK,
            "一致性总审",
            loc,
            f"consistency_audit.py --json 输出不可解析：{type(exc).__name__}: {exc}；stderr={proc.stderr[:500]}",
            return_to_stage="review",
        )
        return
    if not isinstance(res, dict):
        add(BLOCK, "一致性总审", loc, "consistency_audit.py --json 未返回对象", return_to_stage="review")
        return

    summary = res.get("summary") if isinstance(res.get("summary"), dict) else {}
    precision = str(summary.get("precision_level") or "full")
    if precision != "full":
        # compose/review 都是交付边界：降级精度=脸/像素一致性其实没机检过——不给绿灯，除非显式放行并留痕。
        # image 出图后：demo 仍只 WARN（不硬拦无 insightface 产线，守"不强制装依赖"原则）；但 production
        # profile 已显式选择严格 QC，则把降级精度也升为 BLOCK——把脸漂挡在最贵的出视频之前，而不是拖到 compose。
        allow_degraded = os.environ.get("N2D_ALLOW_DEGRADED_QC") == "1"
        strict_stage = stage in {"compose", "review"} or (stage == "image" and profile == "production")
        if strict_stage and not allow_degraded:
            boundary = "交付边界" if stage in {"compose", "review"} else "production 出图后闸门"
            add(
                BLOCK,
                "一致性总审",
                loc,
                f"一致性审计精度为 {precision}（insightface 等不可用，脸/像素一致性未真正验证）；"
                f"{boundary}不放行——请在 full 环境复跑，或显式 N2D_ALLOW_DEGRADED_QC=1 放行并自负其责。",
                return_to_stage="review",
            )
        else:
            note = "（已显式 N2D_ALLOW_DEGRADED_QC 放行）" if allow_degraded else ""
            add(
                WARN,
                "一致性总审",
                loc,
                f"一致性审计精度为 {precision}；机检通过不等于脸部/像素一致性已完整验证，正式定稿前应在 full 环境复跑。{note}",
                return_to_stage="review",
            )

    block_count = 0
    mapped_warns = 0
    skipped_warns = 0
    for row in res.get("findings", []) or []:
        if not isinstance(row, dict):
            continue
        sev = str(row.get("severity") or row.get("verdict") or "").lower()
        if sev not in {BLOCK, WARN}:
            continue
        strict_block, strict_reason = _strict_advisory_should_block(root, ep, stage, row, summary)
        if sev == WARN and strict_block:
            sev = BLOCK
        if sev == WARN:
            if mapped_warns >= 12:
                skipped_warns += 1  # 不静默丢——循环后出一条 rollup，避免"12 条已处理"的错觉
                continue
            mapped_warns += 1
        else:
            block_count += 1
        dim = str(row.get("dimension") or row.get("dim") or "一致性总审")
        msg = str(row.get("message") or row.get("msg") or row.get("reason") or "一致性审计发现问题")
        if strict_block:
            msg = (
                f"[production一致性升级:{strict_reason}] {msg}。如确认为可接受，写入 "
                f"{os.path.relpath(_consistency_signoff_path(root, ep), root)} 的 accepted 后复跑；"
                f"finding_hash={_consistency_finding_hash(row)}，签收需包含 accepted=true/reviewer/reason/expires_at，"
                "并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。"
            )
        artifacts = row.get("affected_artifacts") if isinstance(row.get("affected_artifacts"), list) else []
        shots = row.get("affected_shots") if isinstance(row.get("affected_shots"), list) else []
        add(
            sev,
            dim,
            str(artifacts[0] if artifacts else loc),
            msg,
            return_to_stage=row.get("return_to_stage") or ("image" if sev == BLOCK else "review"),
            rerun_scope=row.get("rerun_scope") or "按 consistency_findings 报告回源头修复对应一致性维度。",
            affected_shots=shots,
            affected_artifacts=artifacts or [os.path.relpath(loc, root)],
        )

    if skipped_warns:
        add(
            WARN,
            "一致性总审",
            loc,
            f"另有 {skipped_warns} 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 "
            f"生产数据/consistency_findings_{ep}.json，勿当作已全部处理。",
            return_to_stage="review",
        )

    if proc.returncode != 0 and not block_count:
        add(
            BLOCK,
            "一致性总审",
            loc,
            f"consistency_audit.py 退出码 {proc.returncode}，但未导出 block finding；stderr={proc.stderr[:500]}",
            return_to_stage="review",
        )


def run(root: str, ep: str, stage: str) -> None:
    if not os.path.isdir(root):
        add(BLOCK, "路径", root, "作品根不存在")
        return
    check_stage = gate_family(stage)
    av_native = is_native_av_production(root)  # 原生音画：说话镜不跑配音，不要求「配音」列就绪
    if check_stage == "image_prompt_preflight":
        check_compliance_manifest(root, ep, "image")
        # Prompt 生成前只查上游确定性契约；不得要求本阶段即将生成的出图 prompt/registry 已存在。
        image_prereq = ("分镜设计",) if av_native else ("配音", "分镜设计")
        require_progress(root, ep, image_prereq)
        check_progress_artifact_signoff(root, ep, image_prereq)
        check_placeholder_policy(root, ep, "image")
        check_voiceover_fingerprint(root, ep)
        check_timing_manifest_complete(root, ep)
        check_voice_cross_episode(root, ep)
        check_image_ai_policy(root, ep)
        check_backend_reachable(root, ep)
        check_drift_risk_advisories(root, ep)
        check_drift_report_freshness(root, ep)  # measured-drift BLOCK 环的报告新鲜度闸（堵静默退化）
        check_cross_episode_character_definition(root, ep)
        check_storyboard_contract(root, ep, require_frame_assets=False)
        check_storyboard_possession_gate(root, ep)
        check_storyboard_visual_contract(root, ep)
        check_storyboard_style_contract(root, ep)
        check_stylized_face_encoder_policy(root, ep, stage)
        check_storyboard_special_templates(root, ep)
    elif check_stage == "image":
        check_compliance_manifest(root, ep, check_stage)
        # image 阶段只在「先出视频后配音」模式允许 rough timing 做 demo 出图；
        # 配音先行仍必须真实配音。不要把 rough 配音强写成 ✅。
        image_prereq = ("分镜设计",) if av_native else ("配音", "分镜设计")
        require_progress(root, ep, image_prereq)
        check_progress_artifact_signoff(root, ep, image_prereq)
        check_placeholder_policy(root, ep, check_stage)
        check_voiceover_fingerprint(root, ep)
        check_timing_manifest_complete(root, ep)
        check_voice_cross_episode(root, ep)
        check_image_ai_policy(root, ep)
        check_backend_reachable(root, ep)
        if stage == "image_preflight":
            check_image_backend_api_refresh(root, ep)
        # 已测得的跨集脸/资产漂移 BLOCK 不分预检/出图后——整个 image family 都跑，避免直接 `--stage image`
        # 跳过预检时上一集已漂移的角色蒙混过出图后 gate。
        check_drift_risk_advisories(root, ep)
        check_drift_report_freshness(root, ep)  # measured-drift BLOCK 环的报告新鲜度闸（堵静默退化）
        check_cross_episode_character_definition(root, ep)  # 跨集角色文字定义漂移（重派生）信号
        if stage == "image_preflight":
            check_reference_plan_applied(root, ep)  # 逐镜参考规划落实对账（advisory·治跨集脸漂）
            check_long_running_weak_backend(root, ep)  # 长线剧×弱后端→核心/常驻角色必须升原生主体/主体库或身份锁
            check_stylized_face_encoder_policy(root, ep, stage)
        check_identity_registry(root, require_reference_assets=False)
        check_costume_registry_reconcile(root)
        check_asset_reference_registry(root, require_reference_assets=False)
        check_storyboard_contract(root, ep, require_frame_assets=False)
        check_storyboard_possession_gate(root, ep)
        check_storyboard_visual_contract(root, ep)
        check_storyboard_style_contract(root, ep)
        check_cross_episode_style(root, ep)
        check_cross_episode_contract(root, ep)
        check_storyboard_special_templates(root, ep)
        check_image_prompt_overview(root, ep)
        check_prompt_checklists(root, ep, "image")
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        check_shared_image_index(root, ep)
        check_referenced_assets_finalized(root, ep)
        check_anchor_fingerprints(root, ep)
        check_core_anchor_pinning(root, ep)
        check_expression_anchors(root, ep)
        check_character_backend_pin(root, ep)
        check_seed_event_records(root, ep)
        check_generation_recipe_evidence(root, ep, stage)
        check_common_image_prompts(root)
        check_cinematic_optical_continuity(root, ep)
        check_shot_scale_progression(root, ep)
        check_physical_scale_audit(root, ep)
        if stage == "image":
            # 生成后落档机检：崩脸/接缝断/降级精度近景/角色脸覆盖缺口的**像素**硬挡，此前只挂在
            # video / video_prompt_preflight 阶段（gate.py:5770/5794），出图阶段（runner 生成后跑的
            # 就是 `--stage image`）一直不接 → 崩脸要拖到最贵的「出视频」工位才被拦。现接进 image 阶段，
            # 让崩脸在最近的出图闸门即 BLOCK。pre-gen 的 image_preflight 不跑（此时还没 PNG/QC 报告，
            # 见 check_input_frame_qc 对无 PNG 的优雅降级）。
            check_input_frame_qc(root, ep)
            # 一致性总审同样前移到出图后闸门：手部多指/天气硬跳/极端身高/禁用称谓/动作硬断等**确定性
            # 🔴 维度**此前只在 compose/review（已花完出视频钱）才拦。出图后 PNG 已在、clip 未出——
            # 此处跑全套 consistency_audit，确定性 block 维度即 BLOCK，把它们挡在最贵的「出视频」之前。
            # stage="image"：降级精度（缺 insightface）按既有逻辑只降级为 WARN（不硬拦无依赖产线，
            # 交付边界 compose/review 才对降级精度 BLOCK，逃生口仍是 N2D_ALLOW_DEGRADED_QC）。
            check_consistency_audit_gate(root, ep, stage="image")
    elif check_stage == "video_prompt_preflight":
        check_compliance_manifest(root, ep, "video")
        # 视频 prompt 生成前必须证明首帧/尾帧和身份矩阵已可继承，但不得要求视频 prompt 文件已存在。
        video_prereq = ("分镜设计", "出图prompt", "出图") if av_native else ("配音", "分镜设计", "出图prompt", "出图")
        require_progress(root, ep, video_prereq)
        check_progress_artifact_signoff(root, ep, video_prereq)
        check_placeholder_policy(root, ep, "video")
        check_voiceover_fingerprint(root, ep)
        check_timing_manifest_complete(root, ep)
        check_voice_cross_episode(root, ep)
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_identity_adapter_matrix(root)
        check_route_identity_readiness(root, ep)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_storyboard_style_contract(root, ep)
        check_storyboard_special_templates(root, ep)
        check_spectacle_sequence_plan(root, ep)
        check_action_beat_budget(root, ep, check_stage)
        check_expression_span_frame_contract(root, ep)
        check_core_expression_anchor_coverage(root, ep)
        check_image_assets(root, ep)
        check_input_frame_qc(root, ep)
        check_multimodal_continuity(root, ep)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
    elif check_stage == "video":
        check_compliance_manifest(root, ep, check_stage)
        video_prereq = ("分镜设计", "出图prompt") if av_native else ("配音", "分镜设计", "出图prompt")
        require_progress(root, ep, video_prereq)
        check_progress_artifact_signoff(root, ep, video_prereq)
        check_placeholder_policy(root, ep, check_stage)
        check_voiceover_fingerprint(root, ep)
        # 一角一色跨集契约：video 阶段也再校一次（出图→出视频之间若改了 voicemap/补配音）。
        check_timing_manifest_complete(root, ep)
        check_voice_cross_episode(root, ep)
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_identity_adapter_matrix(root)
        check_route_identity_readiness(root, ep)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_storyboard_style_contract(root, ep)
        check_storyboard_special_templates(root, ep)
        check_spectacle_sequence_plan(root, ep)
        check_action_beat_budget(root, ep, check_stage)
        check_expression_span_frame_contract(root, ep)
        check_core_expression_anchor_coverage(root, ep)
        check_image_assets(root, ep)
        check_input_frame_qc(root, ep)
        check_video_prompt_frames(root, ep)
        check_multimodal_continuity(root, ep)
        check_prompt_checklists(root, ep, "video")
        check_video_stage_raw_output_policy(root, ep)
        check_generation_recipe_evidence(root, ep, stage)
        check_contract_inheritance(root, ep)
        check_cross_episode_contract(root, ep)
        check_identity_handoff_inheritance(root, ep)
        check_asset_handoff_inheritance(root, ep)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
    elif check_stage == "compose":
        check_compliance_manifest(root, ep, check_stage)
        require_progress(root, ep, ("视频",))
        check_progress_artifact_signoff(root, ep, ("视频",))
        # 一角一色跨集契约在出图后若被改 voicemap/补配音会失效——compose 终装前再校一次，
        # 不让出图后编辑悄悄绕过跨集换声 BLOCK。（原仅在 image 阶段校验，是上次审计的遗留 gap）
        check_timing_manifest_complete(root, ep)
        check_voice_cross_episode(root, ep)
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_identity_adapter_matrix(root)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_storyboard_special_templates(root, ep)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        # 跨集视觉契约（光位/轴线翻）+ 跨集角色文字定义漂移：出图后到合成前若改了 00_总览.md，
        # 越轴/光跳/换脸会一路绿灯到成片。compose 终装前再校一次——和 check_voice_cross_episode 进
        # compose 同理（不让出图后编辑悄悄绕过跨集一致性），补此前只在 image/video 校验的不对称遗留。
        check_cross_episode_contract(root, ep)
        check_cross_episode_character_definition(root, ep)
        sb = load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
        if sb:
            check_voice_conditioned_lipsync_policy(root, ep, sb)
        check_compose_inputs(root, ep)
        check_stylized_face_encoder_policy(root, ep, stage)
        check_translation_glossary_release_gate(root, ep, stage)
        check_generation_recipe_evidence(root, ep, stage)
        check_consistency_audit_gate(root, ep, stage="compose")
    elif check_stage == "review":
        check_compliance_manifest(root, ep, check_stage)
        referenced_characters, referenced_assets = episode_registry_reference_ids(root, ep)
        check_identity_registry(root, require_reference_assets=True, required_character_ids=referenced_characters)
        check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids=referenced_assets)
        check_identity_adapter_matrix(root)
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_storyboard_special_templates(root, ep)
        check_video_assets(root, ep)
        check_semantic_lineage(root, ep)
        check_state_continuity(root, ep)
        check_multimodal_continuity(root, ep)
        check_subtitle_alignment(root, ep)
        check_stylized_face_encoder_policy(root, ep, stage)
        check_translation_glossary_release_gate(root, ep, stage)
        check_generation_recipe_evidence(root, ep, stage)
        check_cross_episode_contract(root, ep)
        check_cross_episode_character_definition(root, ep)
        check_identity_handoff_inheritance(root, ep)
        check_asset_handoff_inheritance(root, ep)
        check_consistency_audit_gate(root, ep, stage="review")
    else:
        add(BLOCK, "参数", stage, "未知 stage")


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--stage", required=True, choices=GATE_STAGES)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    run(ns.root.rstrip("/"), ns.episode, ns.stage)
    structured = [annotate_finding(f, ns.stage, ep=ns.episode) for f in findings]
    if ns.json:
        print(json.dumps(structured, ensure_ascii=False, indent=2))
    else:
        blocks = sum(1 for f in structured if f["sev"] == BLOCK)
        warns = sum(1 for f in structured if f["sev"] == WARN)
        infos = sum(1 for f in structured if f["sev"] == INFO)
        print(f"=== n2d gate: {ns.root} {ns.episode} stage={ns.stage} ===")
        print(f"block {blocks} · warn {warns} · info {infos}\n")
        order = {BLOCK: 0, WARN: 1, INFO: 2}
        for f in sorted(structured, key=lambda x: order[x["sev"]]):
            icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}[f["sev"]]
            print(f"{icon} [{f['dim']}] {f['loc']}: {f['msg']}")
            if f.get("return_to_stage") and f["sev"] == BLOCK:
                print(f"   ↳ 回退: {f['return_to_stage']} · {f.get('rerun_scope', '')}")
    return 1 if any(f["sev"] == BLOCK for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
