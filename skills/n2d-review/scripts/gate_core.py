#!/usr/bin/env python3
"""gate_core — gate.py 的共享基座（按证据族拆分 keystone·增量2）。

gate.py 与 gates/<family>.py 都从这里取：BLOCK/WARN/INFO、findings（append-only 单一列表对象）、
add()、常量族、无状态助手（IO/事件账本/profile 解析/WARN 分级/evidence_family）。
根治「check_ 迁出 gate.py → 循环导入」：共享符号住基座，gate.py/gates 单向依赖基座。

本文件由 gate.py 机械拆出（行为零变化）；__all__ 显式导出所有顶层名（含 _ 私有），
让 gate.py 的 `from gate_core import *` 能拿到全部基座符号。
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
# 多主体策略/槽位/站位词表单一真值源（n2d_const）：与 image_qc / shot_risk_audit / face_drift_risk
# 同源（CODEX_SPLIT_COMPOSITE_MARKERS = SPLIT_COMPOSITE_MARKERS）。本文件禁止再字面量重定义同名集合
# （test_marker_single_source.py 守护）。这是 block ⊆ review block 不靠人手同步的结构性保证。
from n2d_const import (  # noqa: E402
    SPLIT_COMPOSITE_MARKERS as CODEX_SPLIT_COMPOSITE_MARKERS,
    NATIVE_MULTI_SUBJECT_STRATEGY_MARKERS,
    MULTI_SUBJECT_EXECUTION_STRATEGY_MARKERS,
    MULTI_SUBJECT_SLOT_MARKERS,
    MULTI_SUBJECT_POSITION_MARKERS,
)
from seam_contract import needs_end_anchor  # noqa: E402
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
    CHARACTER_LIBRARY_CORE_VIEWS,
    CHARACTER_LIBRARY_TIER_CORE,
    CHARACTER_LIBRARY_TIER_STANDARD,
    CHARACTER_LIBRARY_TIER_MINIMAL,
    CHARACTER_LIBRARY_TIER_PARTIAL,
    CHARACTER_LIBRARY_TIERS,
    character_library_tier_for_record,
    character_library_tier_is_at_least,
    normalize_character_library_tier as canonical_normalize_character_library_tier,
    required_character_library_views,
    required_character_reference_group_fields,
    restricted_partial_contract_valid,
    image_backend_supports_persistent_subject,
    identity_allowed_modes,
    identity_registry_path,
    MOTION_CONTROL_MANIFEST_KIND,
    MOTION_CONTROL_REQUIRED_SHOT_TYPES,
    MOTION_CONTROL_RISK_FLAGS,
    production_mode_keys,
    SPECTACLE_SEQUENCE_PLAN_KIND,
    STYLE_CONTRACT_FIELDS,
    COMPACT_NARRATIVE_TEMPLATE_FIELDS,
    SPECTACLE_TEMPLATE_FIELDS,
    GENERIC_TEMPLATE_VALUES,
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
from n2d_registry import episode_png_fingerprint  # noqa: E402  内容级新鲜度指纹（与 identity.py 共用单一真值源）
from n2d_contract_diff import diff_contracts, diff_storyboard_image_contract  # noqa: E402  视觉契约继承 Diff 核心（common 层单一真值源）
from n2d_handoff import (  # noqa: E402  逐镜身份/资产交接 Diff（common 层单一真值源，与 inherit_contract 共用）
    check_asset_handoff,
    check_identity_handoff,
)
from n2d_thresholds import load_thresholds  # noqa: E402  告警阈值单一真值源（budget_cap 等，与 dashboard/score 共用）
import image_backends  # noqa: E402  出图后端连通性探活 adapter（选择点→探针）
import image_backend_adapter  # noqa: E402  生图后端 API/能力适配层（选择点→能力/刷新证据/推荐）
import video_backend_adapter  # noqa: E402  生视频后端 API/能力适配层（选择点→能力/刷新证据）
import backend_smoke  # noqa: E402  后端 smoke 证据（可选硬闸：最近可运行证明）
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
from n2d_settings import get_setting, is_hybrid_routing, is_native_av, is_video_first  # noqa: E402
from n2d_logic import normalize_camera_move, color_temperature_findings  # noqa: E402  运镜词典归一 + 色温数值化体检
from gate_policy_matrix import family_for_stage as policy_family_for_stage, validate_matrix as validate_gate_policy_matrix  # noqa: E402
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
try:
    import skill_freshness  # type: ignore  # 花钱出图/出视频前的 skill 漂移体检
except Exception:  # pragma: no cover - degraded local env
    skill_freshness = None  # type: ignore[assignment]
BLOCK, WARN, INFO = "block", "warn", "info"
findings: List[Dict[str, object]] = []
FALLBACK_OFF_VALUES = {"", "无", "不使用", "关闭", "否", "off", "no", "none", "disable", "disabled"}
def _loads_json_from_noisy_stdout(text: str) -> Any:
    """Parse JSON even when native libraries printed probe logs before it.

    Some visual stacks print provider/model diagnostics to stdout instead of
    stderr.  Gate should still fail closed if no JSON exists, but it should not
    turn a real consistency finding into a fake "unparseable stdout" blocker.
    """
    raw = (text or "").strip()
    if not raw:
        raise json.JSONDecodeError("empty stdout", text or "", 0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    last: Any = None
    for match in re.finditer(r"[\{\[]", text):
        try:
            obj, end = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if not text[match.start() + end:].strip():
            return obj
        last = obj
    if last is None:
        raise json.JSONDecodeError("no JSON object found", text, 0)
    return last
# ── WARN risk_score tiering ──────────────────────────────────────────────
# Every WARN finding carries a risk_score (0.0–1.0) so the gate output can
# distinguish high-severity warns (likely real issues needing attention) from
# minor/advisory ones (cosmetic / constructional suggestions).  Detection logic
# is unchanged — this is a display/priority layer only.
#
# Tiers:  >=0.7  warn_hi   ❗ high — likely real issue, prioritise
#         0.4-0.7 warn_mod  ⚠️  moderate — needs human judgment
#         <0.4    warn_minor ℹ️  minor — cosmetic / advisory / constructional
WARN_HI, WARN_MOD_CUT, WARN_MINOR_CUT = 0.7, 0.4, 0.0
# Default risk_score per dimension family (substring match, case-insensitive).
# The mapping is checked in order — first match wins.  Explicit risk_score=
# kwarg on add() always takes precedence over the auto-derived default.
_RISK_DEFAULTS: List[Tuple[str, float]] = [
    # face / identity — highest risk: drift here is the most audience-visible
    ("脸", 0.8), ("face", 0.8), ("identity", 0.8), ("角色一致", 0.8),
    ("identity", 0.8), ("锚点", 0.8), ("fidelity", 0.8),
    # cross-episode / voice identity — hard to fix later
    ("跨集", 0.7), ("voice", 0.7), ("声纹", 0.7), ("音色", 0.7),
    ("契约", 0.7), ("contract", 0.7),
    # scene / outfit / blocking — moderate
    ("场景", 0.5), ("服装", 0.5), ("outfit", 0.5), ("scene", 0.5),
    ("hair", 0.5), ("发型", 0.5),
    # scale / spatial / physical
    ("景别", 0.5), ("构图", 0.5), ("物理", 0.5), ("scale", 0.5),
    # style / tone / color — lower: can be intentional creative choice
    ("风格", 0.3), ("style", 0.3), ("色调", 0.3), ("光影", 0.3),
    ("电影光学", 0.3),
    # operational / advisory — lowest
    ("prompt", 0.2), ("seed", 0.2), ("预算", 0.2), ("budget", 0.2),
    ("配音", 0.2), ("合规", 0.2), ("尾帧", 0.3), ("中段锚帧", 0.3),
    ("原生", 0.3),
]
def _default_risk_score(dim: str) -> float:
    """Auto-derived risk_score from the dimension name.  Returns 0.5 (moderate)
    for unrecognised dims — conservative, neither under- nor over-alarming."""
    dim_lower = dim.lower()
    for pattern, score in _RISK_DEFAULTS:
        if pattern in dim_lower:
            return score
    return 0.5  # unrecognised → moderate (conservative)
def _warn_tier(risk_score: Optional[float]) -> str:
    """Map risk_score to a display tier label."""
    if risk_score is None:
        return "warn_mod"
    if risk_score >= WARN_HI:
        return "warn_hi"
    if risk_score >= WARN_MOD_CUT:
        return "warn_mod"
    return "warn_minor"
def _warn_icon(tier: str) -> str:
    return {"warn_hi": "❗", "warn_mod": "⚠️", "warn_minor": "ℹ️"}.get(tier, "⚠️")
def _default_evidence_family(dim: str, msg: str = "", loc: str = "") -> str:
    """Coarse evidence provenance used by correlation upgrades.

    Correlation should not turn three copies of the same weak signal into a hard
    blocker.  A best-effort family is enough here: detector rows can override it
    with explicit `evidence_family`, while older findings remain usable.
    """
    hay = " ".join((dim or "", msg or "", loc or "")).lower()
    rules = (
        # frame_format := 画面比例/画幅/安全框/构图比例——**画面格式**，与人脸 crop 无关，须先于
        # face_embedding 的「比例」判，否则一条画幅比例 finding 会和真脸漂 finding 误并成同族、低估独立根因数
        # （P1-8：歧义子串「比例」既指 身高比例[身份] 又指 画面比例[格式]，分流后者）。
        ("frame_format", ("画面比例", "画幅", "构图比例", "aspect", "安全框", "letterbox", "画框", "16:9", "9:16")),
        # face_embedding := everything derived from the SAME face/head crop. 发型/表情/身高比例/
        # 辨识标记 all read that one region, so a single drifted face trips them together — they
        # are NOT independent corroboration and must collapse to one family, else the correlation
        # upgrade self-confirms on one root cause (掣肘三：相关探测器虚假升级)。「标记」收窄成「辨识标记」，
        # 避免「时间标记/标记点」等泛义子串误并入脸族。
        ("face_embedding", ("脸", "face", "identity", "arcface", "styleid", "主体视频", "s2v",
                            "发型", "hair", "表情", "expression", "比例", "scale",
                            "辨识标记", "marks", "异瞳", "胎记", "疤", "纹身")),
        ("text_contract", ("语义", "契约", "contract", "storyboard", "prompt", "状态百科", "state")),
        ("pixel_hash", ("接缝", "dhash", "flicker", "temporal", "片内时序", "闪烁")),
        ("appearance_embedding", ("多模态", "clip", "dino", "dreamsim", "外观判官", "服装", "配色")),
        ("scene_geometry", ("场景", "轴线", "视线", "平面", "相机", "camera", "blocking")),
        ("motion_physics", ("运动", "物理", "因果", "motion", "physics", "高动态", "specv")),
        ("audio_sync", ("音画", "口型", "声纹", "音色", "audio", "voice", "lipsync", "环境声")),
        ("human_signoff", ("人审", "signoff", "calibration", "校准")),
    )
    for family, tokens in rules:
        if any(token in hay for token in tokens):
            return family
    return "unknown"

_ROOT_CAUSE_RULES: List[Tuple[str, Tuple[str, ...], str, str]] = [
    ("script", ("剧本", "改编", "剧情", "节奏", "台词", "对白", "旁白", "因果", "动机", "伏笔", "爽点", "story", "beat", "dialogue"), "编剧/故事编辑", "回 n2d-script 修剧本/台词/故事账本后重跑相关 gate"),
    ("director_blocking", ("导演", "分镜", "景别", "机位", "轴线", "调度", "运镜", "动作线", "转场", "接缝", "blocking", "staging", "camera"), "导演/分镜", "回导演排戏包或 storyboard 修机位/轴线/接缝后重跑 gate"),
    ("production_breakdown", ("制片", "拆解", "call_sheet", "资产", "身份注册", "continuity_breakdown", "production_breakdown", "ledger", "state_continuity", "引用槽", "reference_slot"), "制片主任/场记", "回 production_breakdown/continuity/registry 补交接证据后重跑 gate"),
    ("image_prompt", ("出图", "图像", "prompt", "脸", "五官", "发型", "服装", "角色一致", "场景", "道具", "风格", "光影", "image_qc", "reference"), "出图提示/美术资产", "回参考包、定妆、逐镜 prompt 或 image_qc 修复后重跑 gate"),
    ("backend", ("后端", "模型", "路由", "seed", "motion control", "mouth", "口型", "唇形", "音画", "video_backend", "lipsync", "provider"), "模型路由/后端适配", "回模型路由、能力证据、口型/原生音画策略后重跑 gate"),
    ("qc", ("qc", "review", "score", "评分", "验收", "新鲜度", "stale", "指纹", "freshness", "校准", "golden"), "QC/验收", "重跑过期 QC、score、ledger、review-ui 或校准集"),
]


def _default_root_cause(dim: str, msg: str = "", loc: str = "") -> Dict[str, str]:
    hay = " ".join((dim or "", msg or "", loc or "")).lower()
    for layer, tokens, owner, scope in _ROOT_CAUSE_RULES:
        if any(token.lower() in hay for token in tokens):
            return {"root_cause_layer": layer, "owner": owner, "minimal_rerun_scope": scope}
    return {
        "root_cause_layer": "qc",
        "owner": "QC/验收",
        "minimal_rerun_scope": "先由 failure_taxonomy 复核根因，再回对应 stage 最小返工",
    }


SPECIAL_SHOT_TEMPLATE_FIELDS: Dict[str, Tuple[str, ...]] = {
    **SPECTACLE_TEMPLATE_FIELDS,
    **COMPACT_NARRATIVE_TEMPLATE_FIELDS,
    "dialogue_shot_reverse": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "axis", "eyeline", "shot_pairing", "screen_sides", "coverage_order",
        "camera_coverage", "lens_height_distance_match", "crossing_axis_policy",
        "buffer_or_reestablishing",
    ),
    "reveal_reaction_chain": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "reveal_object", "knowledge_order", "reaction_beats", "cut_point",
    ),
    "public_confrontation": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "stakes", "evidence_ladder", "power_shift", "crowd_reaction_order",
    ),
    "magic_burst": SPECTACLE_TEMPLATE_FIELDS["magic_burst"],
    "system_panel": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "motif_id", "vfx_asset", "text_layer", "growth_ref", "panel_tier",
    ),
    "intimate_interaction": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "consent_boundary", "contact_points", "distance_boundary", "body_overlap_limit",
        "occlusion_order", "body_part_ownership", "relationship_state", "readability_beats", "degrade_plan",
    ),
    "hug_or_pull": (
        "template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative",
        "consent_boundary", "contact_points", "force_direction", "body_overlap_limit",
        "occlusion_order", "body_part_ownership", "hold_or_release_frame", "release_frame",
        "relationship_state", "readability_beats", "degrade_plan",
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
MOTION_CONTROL_CONTACT_SHOT_TYPES = ("fight_exchange", "kiss_or_near_kiss", "hug_or_pull", "intimate_interaction", "dual_cultivation")
# IDENTITY_REGISTRY_KIND / IDENTITY_ADAPTER_MATRIX_KIND / IDENTITY_REFERENCE_FIELDS /
# IDENTITY_HANDLE_FIELDS 从 n2d_contract 导入（写方 lora/market/identity 同源）
IDENTITY_REFERENCE_FIELDS = IDENTITY_REFERENCE_KEYS
# 角色定妆基础包不可缺失铁律（设计宪法 B7）：只保留历史导出名，
# 真正的档位/视图集合位于 n2d/_lib/n2d_const.py，写方和审方不再各自拷贝。
REQUIRED_CHARACTER_MAKEUP_REFERENCE_GROUP_FIELDS = required_character_reference_group_fields(
    CHARACTER_LIBRARY_TIER_CORE
)
REQUIRED_CHARACTER_MAKEUP_ATLAS_VIEWS = CHARACTER_LIBRARY_CORE_VIEWS
CHARACTER_MAKEUP_BODY_REFERENCE_FIELDS = ("half_body", "full_body", "outfit")
CHARACTER_MAKEUP_FACE_REFERENCE_FIELDS = ("face_anchor_refs", "expressions")
READY_CHARACTER_MAKEUP_STATUSES = {"ready", "registered"}
DERIVED_CHARACTER_MAKEUP_REFERENCE_FIELDS = (
    "three_quarter", "side", "rear_three_quarter", "back",
    "half_body", "full_body", "face_anchor_refs",
)
SAME_SOURCE_MAKEUP_DERIVATION_METHODS = {
    "three_quarter": {"turnaround_split", "turnaround_crop", "controlled_multiref_generation"},
    "side": {"turnaround_split", "turnaround_crop", "controlled_multiref_generation"},
    "rear_three_quarter": {"turnaround_split", "turnaround_crop", "controlled_multiref_generation"},
    "back": {"turnaround_split", "turnaround_crop", "controlled_multiref_generation"},
    "half_body": {"front_crop", "turnaround_crop", "controlled_multiref_generation"},
    "full_body": {"front_crop", "turnaround_crop", "controlled_multiref_generation"},
    "face_anchor_refs": {"front_crop", "turnaround_crop", "controlled_multiref_generation"},
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
    "prop": ("PROP_", "MOUNT_GROUP_"),
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
# scene_dna.dof_profile.depth_intent 可识别档（per-scene 景深锁·与 dof_consistency._norm_dof_intent 同义词集）
_DOF_INTENT_TOKENS = ("shallow", "浅", "奶油", "虚化", "bokeh", "deep", "深焦", "全清", "pan_focus", "medium", "中", "适中")
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
# 启发式 BLOCK→WARN 降级账本（#3·2026-06-28）：blanket 降级曾让「任何 confidence=heuristic 的
# would-be BLOCK」**静默**变 WARN，整类阈值/关键词检测器结构上无法阻断、且无人知道降了多少条。
# 收口两件事：①charter-locked 维度即便信号是启发式也**不降级**（lock 胜过 demotion，堵「把本该
# locked 的 BLOCK 标成 heuristic 偷降级」）；②其余降级逐条计账，run() 末尾汇成可查 rollup，
# 把「静默侵蚀」变「可见事实」。
_HEURISTIC_BLOCK_DEMOTIONS: List[Dict[str, str]] = []
_CHARTER_LOCKED_DIMS_CACHE: Optional[frozenset] = None
def _charter_locked_dims() -> frozenset:
    """charter 里 may_be_profile_gated=False 的无条件 BLOCK 闸所守护的 dim 集合（缓存）。"""
    global _CHARTER_LOCKED_DIMS_CACHE
    if _CHARTER_LOCKED_DIMS_CACHE is None:
        try:
            from consistency_charter import CHARTER  # 同目录·纯 stdlib
            _CHARTER_LOCKED_DIMS_CACHE = frozenset(
                str(e.get("dim"))
                for e in CHARTER.values()
                if e.get("required_severity") == "block" and not e.get("may_be_profile_gated")
            )
        except Exception:
            _CHARTER_LOCKED_DIMS_CACHE = frozenset()
    return _CHARTER_LOCKED_DIMS_CACHE
def heuristic_demotion_rollup(demotions: Sequence[Mapping[str, str]], stage: str) -> Optional[Tuple[str, str, str]]:
    """降级账本 → 单条 WARN rollup (sev, loc, msg)，或 None（无降级）。纯函数·可测。"""
    if not demotions:
        return None
    dims = sorted({str(d.get("dim") or "?") for d in demotions})
    return (
        WARN,
        "gate:heuristic_demotion_rollup",
        f"{stage}：{len(demotions)} 条启发式 would-be-BLOCK 已降为 WARN（维度：{('、'.join(dims))[:200]}）。"
        f"低置信信号不硬阻断是有意设计，但此处显式计账，便于复盘是否有真问题被低置信信号漏挡。",
    )
def add(sev: str, dim: str, loc: str, msg: str, risk_score: Optional[float] = None, **extra: object) -> None:
    # P1（2026-06-26）：脆弱启发式（关键词命中/任意数值阈值/小样本回归）不得硬阻断发布。
    # 任何带 confidence="heuristic" 的 finding 若声明为 BLOCK，统一自动降为 WARN——防阈值沙化把低置信
    # 信号升成发布阻断、与确定性/像素/embedding 证据闸互相掣肘。确定性闸不带该标记、不受影响。
    if extra.get("confidence") == "heuristic" and sev == BLOCK:
        if dim in _charter_locked_dims():
            # charter-locked 维度：lock 胜过 demotion——保留 BLOCK，升级为「需确定性/像素证据复核」，
            # 而非静默降级（堵「把 locked BLOCK 标 heuristic 偷降」）。
            msg = f"{msg}（charter-locked 维度·启发式信号不降级，须以确定性/像素证据复核）"
        else:
            sev = WARN
            msg = f"{msg}（启发式低置信·自动降为 WARN 不硬阻断）"
            _HEURISTIC_BLOCK_DEMOTIONS.append({"dim": str(dim), "loc": str(loc)})
    item: Dict[str, object] = {"sev": sev, "dim": dim, "loc": loc, "msg": msg}
    if sev == WARN:
        # Auto-derive risk_score from dim if not explicitly provided; explicit
        # kwarg always wins.  Non-WARN findings don't carry risk_score.
        item["risk_score"] = risk_score if risk_score is not None else _default_risk_score(dim)
    item.update(extra)
    if item.get("evidence_family") in (None, "", [], {}):
        item["evidence_family"] = _default_evidence_family(dim, msg, loc)
    root_cause = _default_root_cause(dim, msg, loc)
    for key, value in root_cause.items():
        if item.get(key) in (None, "", [], {}):
            item[key] = value
    findings.append(item)
# ── 降级 QC waiver 单一计数账本（#4·2026-06-27）────────────────────────────────
# N2D_ALLOW_DEGRADED_QC=1 此前散落在 gate 多处，各自把一致性 BLOCK 静默降级成 WARN，只在 finding
# message 里留句注释——"本集这次到底凭多少条降级 waiver 放行 / 是不是满档跑的一致性"无从查起。
# 收口成单一 chokepoint：每次降级放行都 note 一条结构化 waiver，run() 末尾汇成一条 rollup finding，
# 把"满档 vs 凭 waiver 交付"变成 gate 输出里的可查字段（与 image runner 的 record_waiver 互补——
# 那条管 --skip-* 显式跳闸，这条管 N2D_ALLOW_DEGRADED_QC 缺依赖降级放行）。
_DEGRADED_QC_WAIVERS: List[Dict[str, str]] = []
def degraded_qc_mode(root: str = "") -> str:
    """Return the active degraded-QC waiver mode, if any.

    `N2D_ALLOW_DEGRADED_QC=1` remains the universal explicit escape hatch. For
    self-use projects, the same intent can be persisted in project settings so a
    review rerun does not depend on remembering a shell env var.
    """
    if os.environ.get("N2D_ALLOW_DEGRADED_QC") == "1":
        return "env"
    if not root:
        return ""
    try:
        profile = consistency_release_profile(root)
    except Exception:
        profile = "demo"
    if profile != "demo":
        return ""
    intents = [v.lower() for v in _settings_values(root, ("合规用途", "distribution_intent"))]
    try:
        data = load_json(compliance_manifest_path(root))
        if isinstance(data, dict):
            intents.append(_status(data.get("distribution_intent")).lower())
    except Exception:
        pass
    if any(v in COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS for v in intents):
        return "project_internal_demo"
    return ""


def degraded_qc_active(root: str = "") -> bool:
    """Whether degraded heavy-QC evidence is explicitly accepted for this run."""
    return bool(degraded_qc_mode(root))


def degraded_qc_waiver_label(root: str = "") -> str:
    mode = degraded_qc_mode(root)
    if mode == "project_internal_demo":
        return "项目设置 internal_only + demo"
    if mode == "env":
        return "N2D_ALLOW_DEGRADED_QC=1"
    return "未开启"
def note_degraded_qc_waiver(dim: str, ep: str, loc: str, reason: str) -> None:
    """单一计数 chokepoint：登记一条因 N2D_ALLOW_DEGRADED_QC 把一致性 BLOCK 降级放行的 waiver。
    各降级点照常 add(WARN, …) 出人类可读 note；额外调本函数把它计入账本（结构化·可查）。"""
    _DEGRADED_QC_WAIVERS.append({"dim": str(dim), "ep": str(ep), "loc": str(loc), "reason": str(reason)})
def consistency_waiver_rollup(waivers: Sequence[Mapping[str, str]], stage: str) -> Optional[Tuple[str, str, str]]:
    """降级 waiver 账本 → 单条 rollup finding (sev, loc, msg)，或 None（满档·无 waiver）。纯函数·可测。

    只做可见化记账：是否 BLOCK 已由各原降级点决定（这里不二次阻断，避免双重 block）。交付边界
    compose/review 多一句"非满档交付"强提示。让"本集这次 gate 满档跑 vs 凭 N 条 waiver 放行"成为
    gate 输出里的一条结构化 finding（dashboard 据此可统计 full_grade 率）。"""
    if not waivers:
        return None
    dims = sorted({str(w.get("dim") or "") for w in waivers if w.get("dim")})
    n = len(waivers)
    boundary = "（交付边界·非满档一致性交付）" if stage in {"compose", "review"} else ""
    msg = (f"本集本次 gate 凭 {n} 条降级 QC waiver 放行{boundary}：维度 {('、').join(dims)}。"
           f"这些维度未在满档(full)精度下验证，全靠 N2D_ALLOW_DEGRADED_QC 显式放行——已记账 `full_grade=false`，"
           f"装齐依赖复跑可消账。")
    return (WARN, "一致性满档账", msg)
CONSISTENCY_RULE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "episode_narrative_floor": {
        "dimension": "系列留存",
        "source": "skills/n2d-script/scripts/beat_audit.py",
        "gate_function": "check_episode_narrative_floor",
        "stages": ("image_preflight",),
        "tests": ("test_episode_narrative_floor_production_blocks_must",),
    },
    "series_retention_gate": {
        "dimension": "系列留存",
        "source": "skills/n2d-script/scripts/beat_audit.py --series",
        "gate_function": "check_series_retention_gate",
        "stages": ("image_preflight", "compose", "review"),
        "tests": ("test_cold_open_chain_blocks_at_image_preflight_production",),
    },
    "lora_exception_scope": {
        "dimension": "LoRA例外范围",
        "source": "skills/n2d-lora/scripts/lora.py exception-scope",
        "gate_function": "check_lora_exception_scope",
        "stages": ("image_prompt_preflight", "image_preflight", "image"),
        "sidecars": ("生产数据/lora_exception_scope_{ep}.json",),
        "tests": ("test_lora_sidechain_requires_exception_scope",),
    },
    "subjectless_backend_lock_profile": {
        "dimension": "生图AI一致性",
        "source": "identity_registry.json + _设置.md",
        "gate_function": "check_long_running_weak_backend",
        "stages": ("image_preflight",),
        "tests": ("test_long_running_subjectless_backend_blocks_in_demo_too",),
    },
    "reference_plan_application": {
        "dimension": "参考规划落实",
        "source": "生产数据/reference_plan_{ep}.json",
        "gate_function": "check_reference_plan_applied",
        "stages": ("image_preflight",),
        "sidecars": ("生产数据/reference_plan_{ep}.json", "生产数据/reference_plan_application_{ep}.json"),
        "tests": ("test_reference_plan_blocks_high_risk_actions_in_demo",),
    },
    "generation_recipe_provenance": {
        "dimension": "生成配方证据",
        "source": "生产数据/production_events.jsonl",
        "gate_function": "check_generation_recipe_evidence",
        "stages": ("image", "video", "compose", "review"),
        "tests": ("test_generation_recipe_evidence_passes_complete_event",),
    },
    "skill_freshness": {
        "dimension": "物料新鲜度",
        "source": "生产数据/skill_update_snapshot.json (n2d/_lib/skill_freshness.py)",
        "gate_function": "check_skill_freshness",
        "stages": ("image_prompt_preflight", "image_preflight", "video_prompt_preflight", "video_preflight"),
        "tests": ("test_skill_freshness_blocks_on_material_drift_before_spend",),
    },
    "referenced_markers_resolve": {
        "dimension": "资产引用注册层",
        "source": "identity_registry.json + asset_registry.json + 本集分镜/prompt",
        "gate_function": "check_referenced_markers_resolve",
        "stages": ("image_preflight", "image", "video_prompt_preflight", "video", "compose", "review"),
        "tests": ("test_referenced_markers_unknown_id_blocks",),
    },
    "storyboard_adjacent_clip_distinctness": {
        "dimension": "Clip 去重",
        "source": "脚本/第N集/storyboard.json clips[]",
        "gate_function": "_check_storyboard_adjacent_clip_distinctness",
        "stages": ("video_preflight",),
        "tests": ("test_storyboard_adjacent_duplicate_clips_warn",),
    },
    "evidence_grade": {
        "dimension": "证据等级",
        "source": "consistency_audit.py summary.evidence_grade (proof_type 账本)",
        "gate_function": "evidence_grade_findings",
        "stages": ("image", "video", "compose", "review"),
        "tests": ("test_evidence_grade_findings_blocks_at_delivery",),
    },
    "consistency_waiver_ledger": {
        "dimension": "一致性满档账",
        "source": "N2D_ALLOW_DEGRADED_QC 降级放行计数（note_degraded_qc_waiver 单一 chokepoint）",
        "gate_function": "consistency_waiver_rollup",
        "stages": ("image", "video", "compose", "review"),
        "tests": ("test_consistency_waiver_rollup_counts_and_dedups_dims",),
    },
}
def _production_mode_contract_issues() -> List[str]:
    """Lint n2d production-mode menu against the executable enum order."""
    skill_path = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "n2d", "SKILL.md"))
    try:
        text = open(skill_path, encoding="utf-8").read()
    except OSError as exc:
        return [f"cannot read n2d/SKILL.md: {exc}"]
    modes = list(production_mode_keys())
    expected = dict(zip(("A", "B", "C", "D"), modes))
    issues: List[str] = []
    for letter, mode in expected.items():
        if not re.search(rf"\*\*{letter}\.\s*{re.escape(mode)}", text):
            issues.append(f"menu {letter} should be {mode}")
    if "B（后配音）" in text or "C（后配音）" in text:
        issues.append("后配音/先出视频后配音 must map to D")
    return issues
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
CHARACTER_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_])`?(CHAR_[A-Za-z0-9_]*[A-Za-z0-9]\*?(?:/[A-Za-z0-9_\u4e00-\u9fff-]+)?\*?)`?"
)
CHARACTER_ID_RE = re.compile(r"(?<![A-Za-z0-9_])CHAR_[A-Za-z0-9_]*[A-Za-z0-9](?![A-Za-z0-9_])")
ASSET_ID_BODY_RE = r"[A-Za-z0-9_\u4e00-\u9fff:-]*[A-Za-z0-9\u4e00-\u9fff]"
ASSET_ID_RE = re.compile(
    rf"(?<![A-Za-z0-9_])(?:MOUNT_GROUP|LOC|PROP|WEAPON|OUTFIT|VFX)_{ASSET_ID_BODY_RE}(?![A-Za-z0-9_\u4e00-\u9fff:-])"
)
SIGNATURE_EQUIPMENT_ID_RE = re.compile(rf"^(?:MOUNT_GROUP|WEAPON|PROP|VFX|OUTFIT)_{ASSET_ID_BODY_RE}$")
# 一致性机检的结构阈值（单一真值源·别再散成内联魔数）：改判据来这里，别埋进各 check 体里。
ENDFRAME_EXEMPT_REASON_MIN_CHARS = 6   # 首尾双帧豁免理由的实质字数下限（< 此 = 占位/单字 → BLOCK）
ANCHOR_TOKEN_MIN_CHARS = 2             # 锚定相按「·」切后单 token 的最短可比长度（过滤单字噪声）
def _episode_reference_texts(root: str, ep: str) -> Iterable[str]:
    """Text surfaces that define the current episode's registry references."""
    storyboard = os.path.join(root, "脚本", ep, "storyboard.json")
    if os.path.isfile(storyboard):
        try:
            with open(storyboard, encoding="utf-8") as fh:
                yield fh.read()
        except Exception:
            pass
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
                name = os.path.basename(path)
                if name == "storyboard.json":
                    continue
                if any(token in name for token in ("素材清单", "物料清单", "asset_list")):
                    continue
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
    char_refs = episode_registry_identity_refs(root, ep, text=text)
    reg_chars, reg_assets = _registered_registry_ids(root)
    char_refs = {_normalize_registered_character_marker(ref, reg_chars) for ref in char_refs}
    asset_refs = {_normalize_registered_asset_marker(ref, reg_assets) for ref in ASSET_ID_RE.findall(text)}
    return {ref.split("/", 1)[0] for ref in char_refs}, asset_refs


_STRUCTURED_CHARACTER_ID_RE = re.compile(
    r"^CHAR_[A-Za-z0-9_\u4e00-\u9fff-]*[A-Za-z0-9\u4e00-\u9fff]$"
)


def _structured_character_ids(value: object) -> set[str]:
    """Extract CHAR ids only from a field already declared as character data.

    This deliberately does not scan arbitrary prose.  Storyboards from older
    projects may omit structured ids; absence is unknown/no evidence, not a
    reason to promote a character and block the project.
    """
    values: List[object]
    if isinstance(value, Mapping):
        values = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        values = list(value)
    elif isinstance(value, str):
        values = [part for part in re.split(r"[,，、;；\s]+", value) if part]
    else:
        values = []
    out: set[str] = set()
    for item in values:
        raw = item
        if isinstance(item, Mapping):
            raw = item.get("character_id") or item.get("char_id") or item.get("id")
        token = str(raw or "").strip().strip("`").rstrip("*")
        base = token.split("/", 1)[0]
        if _STRUCTURED_CHARACTER_ID_RE.fullmatch(base):
            out.add(base)
    return out


def _schedule_hidden_character_ids(schedule: object) -> set[str]:
    if not isinstance(schedule, Mapping):
        return set()
    hidden: set[str] = set()
    for key in ("offscreen_presence", "forbidden_presence", "画外保留", "禁止出现"):
        hidden.update(_structured_character_ids(schedule.get(key)))
    return hidden


def _schedule_visible_character_ids(schedule: object) -> set[str]:
    if not isinstance(schedule, Mapping):
        return set()
    visible: set[str] = set()
    for key in (
        "characters",
        "character_ids",
        "角色",
        "required_presence",
        "foreground_presence",
        "visible_presence",
    ):
        visible.update(_structured_character_ids(schedule.get(key)))
    return visible - _schedule_hidden_character_ids(schedule)


def _storyboard_hidden_character_ids(record: object) -> set[str]:
    """Return explicit offscreen/forbidden ids for one clip or physical shot."""
    if not isinstance(record, Mapping):
        return set()
    hidden = _schedule_hidden_character_ids(record)
    hidden.update(
        _schedule_hidden_character_ids(record.get("entity_schedule") or record.get("实体排程"))
    )
    return hidden


def _storyboard_clip_visible_character_ids(clip: object) -> set[str]:
    """Return visible ids from explicit Stage-2 fields, never prose regexes."""
    if not isinstance(clip, Mapping):
        return set()
    # `character_ids: []` is an explicit object/location-only clip.  Mirror
    # story_quality_pack semantics and do not resurrect ids from side fields.
    if "character_ids" in clip:
        return _structured_character_ids(clip.get("character_ids")) - _storyboard_hidden_character_ids(clip)
    visible = _structured_character_ids(clip.get("characters"))
    visible.update(_schedule_visible_character_ids(clip.get("entity_schedule") or clip.get("实体排程")))
    for shot in clip.get("shots") or []:
        if not isinstance(shot, Mapping):
            continue
        if "character_ids" in shot:
            shot_visible = _structured_character_ids(shot.get("character_ids"))
        else:
            shot_visible = _structured_character_ids(shot.get("characters"))
            shot_visible.update(
                _schedule_visible_character_ids(shot.get("entity_schedule") or shot.get("实体排程"))
            )
        visible.update(shot_visible - _storyboard_hidden_character_ids(shot))
    return visible - _storyboard_hidden_character_ids(clip)


def _storyboard_character_appearance_evidence(root: str) -> Dict[str, Dict[str, Any]]:
    """Observed per-character episode lower bounds from materialized storyboards.

    The result is independent of identity_registry/bundle/manifest/atlas tier
    declarations.  Only parseable storyboards with structured visible CHAR ids
    count.  Missing/legacy prose-only storyboards yield no row, preserving old
    project compatibility instead of guessing from names or free text.
    """
    episodes_by_character: Dict[str, set[str]] = {}
    sources_by_character: Dict[str, set[str]] = {}
    pattern = os.path.join(root, "脚本", "*", "storyboard.json")
    for path in sorted(glob.glob(pattern)):
        data = load_json(path)
        clips = data.get("clips") if isinstance(data, Mapping) else None
        if not isinstance(clips, list):
            continue
        visible: set[str] = set()
        for clip in clips:
            visible.update(_storyboard_clip_visible_character_ids(clip))
        if not visible:
            continue
        episode = os.path.basename(os.path.dirname(path))
        source = os.path.relpath(path, root).replace(os.sep, "/")
        for character_id in visible:
            episodes_by_character.setdefault(character_id, set()).add(episode)
            sources_by_character.setdefault(character_id, set()).add(source)
    return {
        character_id: {
            "episode_count": len(episodes),
            "episodes": sorted(episodes, key=lambda value: (_ce_episode_number(value) or 10**9, value)),
            "sources": sorted(sources_by_character.get(character_id, set())),
            "source_kind": "materialized_storyboard_structured_presence",
        }
        for character_id, episodes in sorted(episodes_by_character.items())
    }


def _normalize_registered_character_marker(ref: str, registered_chars: set) -> str:
    token = str(ref or "").strip().rstrip("*")
    if not token:
        return token
    if "/" in token:
        base, form = token.split("/", 1)
        normalized_base = _normalize_registered_character_marker(base, registered_chars)
        return f"{normalized_base}/{form}" if form else normalized_base
    if token in registered_chars:
        return token
    if token.endswith("_partial"):
        base = token[: -len("_partial")]
        if base in registered_chars:
            return base
    m = re.match(r"^(.+)_\d{1,3}$", token)
    if m and m.group(1) in registered_chars:
        return m.group(1)
    return token


def _normalize_registered_asset_marker(ref: str, registered_assets: set) -> str:
    """Collapse readable `ID_name` mentions back to the registered asset id.

    Prompt/card text often writes assets as `LOC_01_荒野尸骸战场` or
    `WEAPON_01-横刀` for human readability while the registry id remains
    `LOC_01` / `WEAPON_01`.  Unknown ids must still block, so we only trim when a
    known registered id is a delimiter-separated prefix.
    """
    token = str(ref or "").strip()
    if not token or token in registered_assets:
        return token
    for aid in sorted((str(a or "").strip() for a in registered_assets), key=len, reverse=True):
        if aid and any(token.startswith(aid + sep) for sep in ("_", ":", "-")):
            return aid
        if aid and token.startswith(aid):
            suffix = token[len(aid):]
            if suffix and not re.match(r"[A-Za-z0-9_]", suffix[0]):
                return aid
    return token
def episode_registry_identity_refs(root: str, ep: str, text: Optional[str] = None) -> set:
    """Return exact character identity refs consumed by one episode.

    `CHAR_X/形态` refs let the gate validate only the forms used by the current
    episode, while bare `CHAR_X` keeps the legacy "all forms for this character"
    behavior for intentionally form-agnostic references.
    """
    blob = text if text is not None else "\n".join(_episode_reference_texts(root, ep))
    refs: set = set()
    for raw in CHARACTER_REF_RE.findall(blob):
        ref = str(raw or "").strip().replace("*/", "/").rstrip("*")
        if ref:
            refs.add(ref)
    return refs
def _episode_has_per_shot_frames(root: str, ep: str) -> bool:
    """本集是否已产出逐镜帧 PNG（出图/<集>/图片/*.png）。

    两层出图不变量的判据：逐镜帧存在 ⇒ 早该过了"共享定妆库先行"阶段。用于在出图后闸门
    把"被引用共享资产(多角度定妆/武器/服饰)必须真在磁盘"从声明级升到文件级——而不会卡死
    共享库自举那一次（彼时还没有任何逐镜帧）。"""
    try:
        # 与 gate 其余存在性核对（_identity_reference_exists=os.path.exists）同口径，不引外部 png_valid。
        return any(os.path.isfile(p) for p in glob.glob(os.path.join(root, "出图", ep, "图片", "*.png")))
    except Exception:
        return False
def _registered_registry_ids(root: str) -> Tuple[set, set]:
    """已登记的 character id 与 asset id 集合（identity_registry + asset_registry）。

    缺文件/解析失败 → 返回空集（registry 本身的存在性/schema 由 check_identity_registry /
    check_asset_reference_registry 各自 BLOCK，这里不重复报错，只为标记解析提供「已登记」基准）。
    纯读盘·无副作用·可测。"""
    char_ids: set = set()
    asset_ids: set = set()
    idata = load_json(identity_registry_path(root))
    if isinstance(idata, dict):
        for char in idata.get("characters") or []:
            if isinstance(char, dict):
                cid = str(char.get("id", "")).strip()
                if cid:
                    char_ids.add(cid)
    adata = load_json(asset_registry_path(root))
    if isinstance(adata, dict):
        for asset in adata.get("assets") or []:
            if isinstance(asset, dict):
                aid = str(asset.get("id", "")).strip()
                if aid:
                    asset_ids.add(aid)
    return char_ids, asset_ids
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
def _project_local_asset_rel(root: str, asset: object) -> str:
    raw = str(asset or "").strip()
    if not raw:
        return ""
    root_abs = os.path.abspath(root)
    if os.path.isabs(raw):
        try:
            raw_abs = os.path.abspath(raw)
            if os.path.commonpath([root_abs, raw_abs]) == root_abs:
                return os.path.relpath(raw_abs, root_abs).replace(os.sep, "/")
        except Exception:
            pass
    root_name = os.path.basename(root_abs)
    parts = [p for p in _norm_rel_path(raw).split("/") if p and p != "."]
    for idx in range(len(parts) - 1, -1, -1):
        if parts[idx] == root_name:
            tail = parts[idx + 1:]
            if tail:
                return _norm_rel_path("/".join(tail))
    return _norm_rel_path(raw)
def _asset_matches(root: str, asset: object, target_rel: str) -> bool:
    if not asset:
        return False
    asset_s = str(asset).strip()
    target_rel_norm = _norm_rel_path(target_rel)
    target_abs = os.path.abspath(target_rel if os.path.isabs(target_rel) else os.path.join(root, target_rel))
    asset_rel_norm = _project_local_asset_rel(root, asset_s)
    if asset_rel_norm == target_rel_norm:
        return True
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
    return _project_local_asset_rel(root, raw)
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
RECIPE_EVIDENCE_STAGES = {"image", "video"}
RECIPE_REQUIRED_FIELDS = (
    "provider",
    "model",
    "channel",
    "route_hash",
    "capability_evidence_id",
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
    if str(_event_value_any(event, "stage") or "").strip() == "video":
        for key in ("route_execution_recipe_hash", "post_video_qc"):
            if _event_value_any(event, key) in (None, "", [], {}):
                missing.append(key)
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
        if not status or status not in COMPLIANCE_ALLOWED_RIGHTS or status == "unknown":
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
    internal = _is_internal_distribution(data)
    release_strict = stage in ("compose", "review", "release") or _status(data.get("distribution_intent")) == "paid_distribution"

    def flag(floc: str, msg: str) -> None:
        # platform_review / overseas_localization 是发布边界域：
        # internal_only 始终降 INFO；publish_candidate 在 image/video 阶段先列 INFO 待办；
        # paid_distribution 或 compose/review/release 边界才 BLOCK。
        if internal:
            add(INFO, "合规前置", floc, f"{msg}{INTERNAL_SKIP_NOTE}")
        elif not release_strict:
            add(INFO, "合规前置", floc, f"{msg}（发布/合成前需补；当前 {stage} 阶段不阻断）")
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
    internal = _is_internal_distribution(data)
    release_strict = stage in ("compose", "review", "release") or _status(data.get("distribution_intent")) == "paid_distribution"

    def flag(floc: str, msg: str) -> None:
        if internal:
            add(INFO, "合规前置", floc, f"{msg}{INTERNAL_SKIP_NOTE}")
        elif not release_strict:
            add(INFO, "合规前置", floc, f"{msg}（发布/合成前需补；当前 {stage} 阶段不阻断）")
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
def progress_fraction_done(root: str, ep: str, col: str) -> bool:
    _, row = row_for(root, ep)
    if not row:
        return False
    return is_done(row.get(col, ""))
def evaluate_budget_gate(cost_totals, cost_per_min, budget_cap, planned_min, *, warn_ratio=0.8):
    """付费前预算闸门判定（纯函数·可测）。返回 [(sev, currency, spent, forecast, reason), ...]。

    budget_cap 为 None/<=0 → []（无配置上限，graceful skip，不强加预算）。逐币种：
      · 已花 spent ≥ cap → block（已达/超累计上限，硬停）；
      · 已花 + 本集预测 forecast > cap → block（本集预测将冲破上限，别开跑）；
      · 已花 ≥ cap×warn_ratio → warn（接近上限）。
    forecast = cost_per_min[cur] × planned_min（缺历史单价/计划时长 → forecast=0，只按已花判，不臆造）。
    口径与 dashboard.evaluate_alerts 的 budget_cap 一致——区别只是这条跑在「付费前」、那条跑在「事后 rebuild」。"""
    out = []
    try:
        cap = float(budget_cap) if budget_cap is not None else None
    except (TypeError, ValueError):
        cap = None
    if not cap or cap <= 0:
        return out
    try:
        pmin = float(planned_min or 0.0)
    except (TypeError, ValueError):
        pmin = 0.0
    currencies = set(cost_totals or {}) | set(cost_per_min or {})
    for cur in sorted(currencies):
        try:
            spent = float((cost_totals or {}).get(cur, 0.0) or 0.0)
        except (TypeError, ValueError):
            spent = 0.0
        try:
            per_min = float((cost_per_min or {}).get(cur, 0.0) or 0.0)
        except (TypeError, ValueError):
            per_min = 0.0
        forecast = round(per_min * pmin, 2) if (per_min > 0 and pmin > 0) else 0.0
        if spent >= cap:
            out.append(("block", cur, spent, forecast,
                        f"累计成本 {cur} {spent:.2f} 已达/超上限 {cap:.2f}"))
        elif forecast > 0 and (spent + forecast) > cap:
            out.append(("block", cur, spent, forecast,
                        f"已花 {cur} {spent:.2f} + 本集预测 {forecast:.2f} = {spent + forecast:.2f} 将超上限 {cap:.2f}"))
        elif spent >= cap * warn_ratio:
            out.append(("warn", cur, spent, forecast,
                        f"累计成本 {cur} {spent:.2f} 已达上限 {cap:.2f} 的 {warn_ratio * 100:.0f}%"))
    return out
def _episode_planned_minutes(root: str, ep: str) -> float:
    """本集计划输出分钟（预算 forecast 用）：storyboard total_duration 优先，否则 ∑clips[].duration；缺→0。"""
    data = load_json(storyboard_path(root, ep))
    if not isinstance(data, dict):
        return 0.0
    try:
        sec = float(data.get("total_duration") or 0.0)
    except (TypeError, ValueError):
        sec = 0.0
    if sec <= 0:
        clips = data.get("clips") if isinstance(data.get("clips"), list) else []
        s = 0.0
        for c in clips:
            if isinstance(c, dict):
                try:
                    s += float(c.get("duration", 0) or 0)
                except (TypeError, ValueError):
                    pass
        sec = s
    return round(sec / 60.0, 4) if sec > 0 else 0.0
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
def _truthy_setting(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "开启", "是", "硬闸", "强制"}
def backend_smoke_gate_enabled(root: str) -> bool:
    env = os.environ.get("N2D_REQUIRE_BACKEND_SMOKE", "")
    if env:
        return _truthy_setting(env)
    if _truthy_setting(get_setting(root, "后端Smoke硬闸", "")):
        return True
    # production / 付费 / batch 放量默认强制证活性：仅刷官方文档、或没有产物的手录 pass 都不等于
    # 当前账号/渠道真能跑。demo/内部预览仍可用 env/设置显式关闭或保持非阻断。
    try:
        if consistency_release_profile(root) == "production":
            return True
    except Exception:
        pass
    intent_blob = " ".join(_settings_values(root, ("合规用途", "distribution_intent", "投放时效", "urgency"))).lower()
    if any(token in intent_blob for token in ("paid_distribution", "付费", "商业", "batch", "batch_24h", "隔夜批量", "批量", "flex")):
        return True
    data = load_json(compliance_manifest_path(root))
    if isinstance(data, dict):
        if _status(data.get("distribution_intent")) == "paid_distribution":
            return True
    return False
def backend_smoke_max_age_days() -> int:
    raw = os.environ.get("N2D_BACKEND_SMOKE_MAX_AGE_DAYS", "7")
    try:
        return max(0, int(raw))
    except ValueError:
        return 7
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
    relay = route.get("duration_segment_relay") if isinstance(route.get("duration_segment_relay"), Mapping) else {}
    if relay.get("supported") and relay.get("max_segment_seconds"):
        try:
            duration = float(relay.get("max_segment_seconds") or duration)
        except Exception:
            pass
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
    if native_audio == "lipsync_condition_only" and role != "fallback" and not _cap_bool(assertions, "lipsync_audio_ref"):
        gaps.append(f"{clip_id} {role} 口型音频参考但未确认 lipsync_audio_ref")
    identity = str(route.get("identity_requirement") or "").strip().lower()
    if identity not in {"", "none", "not_needed"} and not str(_cap_value(assertions, "identity_mechanism") or "").strip():
        gaps.append(f"{clip_id} {role} 含角色身份要求但未确认 identity_mechanism")
    motion = route.get("motion_control") if isinstance(route.get("motion_control"), Mapping) else {}
    if motion.get("required") is True and not str(_cap_value(assertions, "motion_control_level") or "").strip():
        gaps.append(f"{clip_id} {role} Motion Control required 但未确认 motion_control_level")
    return gaps
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
def imaged_episodes(root: str) -> List[str]:
    """已落 PNG 的出图集（出图/<集>/图片/*.png 存在）——measured-drift BLOCK 环应覆盖的历史集。"""
    eps: set = set()
    for p in glob.glob(os.path.join(root, "出图", "*", "图片", "*.png")):
        eps.add(os.path.basename(os.path.dirname(os.path.dirname(p))))
    return sorted(eps)
def drift_report_freshness(prior_imaged_eps: Sequence[str],
                           report: Mapping[str, Any],
                           current_fingerprints: Optional[Mapping[str, Optional[str]]] = None,
                           ) -> List[Tuple[str, str]]:
    """历史已出图集 vs identity_drift_report 覆盖集/内容指纹 → freshness findings（纯函数·可测）。

    prior_imaged_eps：本集之前、已落 PNG 的集（measured-drift BLOCK 环理应覆盖的历史集）。
    report：解析后的 identity_drift_report.json（{} = 缺失）。
    current_fingerprints：{ep: 当前 PNG 集合指纹}（episode_png_fingerprint 算，None=该集无 PNG）；
        缺省/None 表示调用方不做内容级核对（仅集级覆盖）。返回 [(severity, msg)]：
      - 报告缺失/未实测(available≠True) 但已有历史出图集 → WARN（环此刻无数据，给重跑命令；
        不硬拦无 insightface 的默认无依赖产线）；
      - 报告在、已实测，却漏覆盖部分历史出图集 → BLOCK（**集级** present-but-stale）；
      - 报告覆盖了某集、但该集 PNG 指纹与报告记录的不一致 → BLOCK（**内容级** stale：图重出过、
        报告基于旧像素，集级覆盖看着没问题其实已过期，是比集级漏覆盖更隐蔽的『陈旧绿』）；
      - 报告无 png_fingerprints 字段（早于内容指纹的旧报告）但当前有 PNG → WARN（无法证明内容新鲜，
        给重跑命令补盖指纹；不硬拦既有产线）。
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
    # 内容级核对：仅当调用方传入了当前指纹时进行（保持纯函数对旧调用零行为变更）。
    if current_fingerprints is None:
        return []
    recorded = report.get("png_fingerprints")
    if not isinstance(recorded, Mapping):
        # 旧报告无指纹字段：覆盖集没问题但无法证明内容新鲜（图可能重出过）。
        if any(current_fingerprints.get(e) for e in prior):
            return [(WARN,
                     f"脸漂实测报告早于内容指纹（无 png_fingerprints 字段），无法证明它是基于当前 PNG 像素所算——"
                     f"历史集 {prior} 若在报告生成后重出过图，measured-drift 环会据旧像素误判。重跑 "
                     "`python3 skills/n2d-identity/scripts/identity.py <作品根> --write` 补盖内容指纹。")]
        return []
    content_stale = []
    for e in prior:
        cur = current_fingerprints.get(e)
        rec = recorded.get(e)
        # 当前无 PNG（cur=None）跳过；报告缺该集指纹但集级已覆盖 → 视作旧字段缺失，按内容不可证处理。
        if cur is None:
            continue
        if rec is None:
            content_stale.append(f"{e}(报告缺该集指纹)")
        elif str(rec) != str(cur):
            content_stale.append(f"{e}(指纹不符)")
    if content_stale:
        return [(BLOCK,
                 f"脸漂实测报告内容级陈旧：历史集 {content_stale} 的当前 PNG 像素与报告记录的指纹不一致——"
                 "图在报告生成后重出过，集级覆盖看着没问题、报告其实基于旧像素，measured-drift 环会误判『全绿』。重跑 "
                 "`python3 skills/n2d-identity/scripts/identity.py <作品根> --write` 基于当前 PNG 重算后再出图。")]
    return []
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
LORA_EXCEPTION_SCOPE_KIND = "n2d_lora_exception_scope"
LORA_SIDECAR_REQUIRED_FIELDS = (
    "episode",
    "character_id",
    "form",
    "clips",
    "reason",
    "project_image_model",
    "lora_base_model",
    "style_bridge",
)
LORA_SIDECAR_QC_REQUIRED = (
    "full image_qc face_reference_coverage",
    "style_consistency",
    "local_face_patch_guard",
)
LORA_SIDECHAIN_TOKENS = (
    "lora",
    "loramodel",
    "safetensors",
    "comfy",
    "comfyui",
    "flux",
    "sdxl",
    "stable diffusion",
    "stable_diffusion",
)
def _lora_exception_scope_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"lora_exception_scope_{ep}.json")
def _validate_lora_exception_scope(scope: Mapping[str, Any], ep: str) -> List[str]:
    blocks: List[str] = []
    if scope.get("kind") != LORA_EXCEPTION_SCOPE_KIND:
        blocks.append(f"kind must be {LORA_EXCEPTION_SCOPE_KIND}")
    if str(scope.get("episode") or "").strip() != ep:
        blocks.append(f"episode must be {ep}")
    for key in LORA_SIDECAR_REQUIRED_FIELDS:
        if scope.get(key) in (None, "", [], {}):
            blocks.append(f"missing {key}")
    if scope.get("scope") != "hero_shots_only":
        blocks.append("scope must be hero_shots_only")
    if scope.get("not_a_project_model_switch") is not True:
        blocks.append("not_a_project_model_switch must be true")
    clips = scope.get("clips")
    if not isinstance(clips, list) or not all(str(c).strip() for c in clips):
        blocks.append("clips must be a non-empty string list")
    qc = {str(v).strip() for v in (scope.get("qc_required") or []) if str(v).strip()} if isinstance(scope.get("qc_required"), list) else set()
    missing_qc = [item for item in LORA_SIDECAR_QC_REQUIRED if item not in qc]
    if missing_qc:
        blocks.append("qc_required missing " + ", ".join(missing_qc))
    return blocks
def _lora_scope_clips(scope: Mapping[str, Any]) -> set:
    return {str(c).strip() for c in (scope.get("clips") or []) if str(c).strip()} if isinstance(scope.get("clips"), list) else set()
def _event_clip_id(event: Mapping[str, Any], asset_rel: str = "") -> str:
    generation = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    meta = event.get("meta") if isinstance(event.get("meta"), Mapping) else {}
    for source in (event, generation, meta):
        for key in ("clip", "clip_id", "clipId", "shot", "shot_id"):
            value = source.get(key) if isinstance(source, Mapping) else None
            value_s = str(value or "").strip()
            if value_s:
                return value_s
    text = asset_rel or str(generation.get("asset") or event.get("asset") or "")
    m = re.search(r"(Clip[_-]?\d+)", text, re.I)
    if m:
        token = m.group(1).replace("-", "_")
        m2 = re.search(r"(\d+)", token)
        return f"Clip_{int(m2.group(1)):02d}" if m2 else token
    return ""
def _is_lora_sidechain_event(provider: str, event: Mapping[str, Any]) -> bool:
    generation = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    meta = event.get("meta") if isinstance(event.get("meta"), Mapping) else {}
    cost = event.get("cost") if isinstance(event.get("cost"), Mapping) else {}
    fields: List[str] = [provider]
    for source in (event, generation, meta, cost):
        if not isinstance(source, Mapping):
            continue
        for key in (
            "provider",
            "source",
            "method",
            "model",
            "image_model",
            "backend",
            "lora",
            "lora_model",
            "lora_model_path",
            "lora_base_model",
            "workflow",
        ):
            fields.append(str(source.get(key) or ""))
    haystack = " ".join(fields).lower().replace("-", "_")
    return any(token.replace("-", "_") in haystack for token in LORA_SIDECHAIN_TOKENS)
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
REFERENCE_PLAN_APPLICATION_KIND = "n2d_reference_plan_application"
def _reference_plan_application_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"reference_plan_application_{ep}.json")
def _reference_plan_prompt_path(root: str, ep: str) -> str:
    return os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
def _safe_sha256(path: str) -> str:
    try:
        return _file_sha256(path)
    except Exception:
        return ""
def _reference_plan_application_status(root: str, ep: str, plan_path: str, action_count: int) -> Tuple[bool, str, str]:
    """Structured human/application evidence that reference_plan actions reached final prompts.

    This keeps the load-bearing gate strict: pending actions still block by default.  The
    only release valve is a signed sidecar bound to the exact plan and prompt hashes, so a
    stale "已落实" note cannot silently bypass a changed plan or changed prompt.
    """
    app_path = _reference_plan_application_path(root, ep)
    app = load_json(app_path)
    if not isinstance(app, dict):
        return False, app_path, "缺 reference_plan_application 结构化落实证据"
    if app.get("kind") != REFERENCE_PLAN_APPLICATION_KIND:
        return False, app_path, f"kind 必须是 {REFERENCE_PLAN_APPLICATION_KIND}"
    if app.get("accepted") is not True:
        return False, app_path, "accepted 必须为 true"
    if not str(app.get("reviewer") or "").strip():
        return False, app_path, "reviewer 不能为空"

    plan_sha = _safe_sha256(plan_path)
    if not plan_sha or str(app.get("plan_sha256") or "").strip() != plan_sha:
        return False, app_path, "plan_sha256 与当前 reference_plan 不一致"

    prompt_rel = str(app.get("prompt_path") or os.path.join("出图", ep, "prompt", "01_分镜出图.md")).strip()
    prompt_path = prompt_rel if os.path.isabs(prompt_rel) else os.path.join(root, prompt_rel)
    prompt_sha = _safe_sha256(prompt_path)
    if not prompt_sha:
        return False, app_path, "prompt_path 不存在或不可读"
    if str(app.get("prompt_sha256") or "").strip() != prompt_sha:
        return False, app_path, "prompt_sha256 与当前分镜 prompt 不一致"

    try:
        applied_count = int(app.get("applied_action_count"))
    except Exception:
        applied_count = -1
    if applied_count < action_count:
        return False, app_path, f"applied_action_count={applied_count} 少于待落实行动项 {action_count}"
    evidence = app.get("applied_evidence")
    if not isinstance(evidence, list) or not evidence:
        return False, app_path, "applied_evidence 必须列出落实字段/取舍理由"
    return True, app_path, "ok"
DIRECTOR_CAMERA_PLAN_APPLICATION_KIND = "n2d_director_camera_plan_application"
def _director_plan_application_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"director_camera_plan_applied_{ep}.json")
def _director_plan_application_status(root: str, ep: str, plan_path: str) -> Dict[str, Any]:
    """逐镜结构化签收：导演运镜计划每镜落进哪个 prompt（出图/出视频）的精确归属证据。

    返回 {accepted, reason, app_path, scopes:{scope:{applied_ids:set, fresh:bool, prompt_path}}}。
    与 reference_plan 同范式：SHA 绑定 plan + 每 scope prompt，stale plan/prompt 不放行（freshness 死扣），
    把 P0-3 文档级烟雾收据升成逐镜精确归属。无效/未签收时 accepted=False、scopes 空，check 自动回退烟雾收据。
    """
    app_path = _director_plan_application_path(root, ep)
    app = load_json(app_path)
    out: Dict[str, Any] = {"accepted": False, "reason": "", "app_path": app_path, "scopes": {}}
    if not isinstance(app, dict):
        out["reason"] = "缺 director_camera_plan_applied 结构化签收"
        return out
    if app.get("kind") != DIRECTOR_CAMERA_PLAN_APPLICATION_KIND:
        out["reason"] = f"kind 必须是 {DIRECTOR_CAMERA_PLAN_APPLICATION_KIND}"
        return out
    if app.get("accepted") is not True:
        out["reason"] = "accepted 必须为 true"
        return out
    if not str(app.get("reviewer") or "").strip():
        out["reason"] = "reviewer 不能为空"
        return out
    plan_sha = _safe_sha256(plan_path)
    if not plan_sha or str(app.get("plan_sha256") or "").strip() != plan_sha:
        out["reason"] = "plan_sha256 与当前 director_camera_plan 不一致（plan 变了需重新签收）"
        return out
    default_prompt = {
        "出图": os.path.join("出图", ep, "prompt", "01_分镜出图.md"),
        "出视频": os.path.join("出视频", ep, "prompt", "01_clips.md"),
    }
    scopes: Dict[str, Any] = {}
    for entry in app.get("scopes") or []:
        if not isinstance(entry, dict):
            continue
        scope = str(entry.get("scope") or "").strip()
        if scope not in default_prompt:
            continue
        prompt_rel = str(entry.get("prompt_path") or default_prompt[scope]).strip()
        prompt_path = prompt_rel if os.path.isabs(prompt_rel) else os.path.join(root, prompt_rel)
        psha = _safe_sha256(prompt_path)
        fresh = bool(psha) and str(entry.get("prompt_sha256") or "").strip() == psha
        ids = {str(x).strip() for x in (entry.get("applied_clip_ids") or []) if str(x).strip()}
        scopes[scope] = {"applied_ids": ids, "fresh": fresh, "prompt_path": prompt_path}
    out["accepted"] = True
    out["reason"] = "ok"
    out["scopes"] = scopes
    return out
def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")
def load_storyboard(root: str, ep: str) -> Optional[dict]:
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "故事板", p, "缺少机器可读 storyboard.json；下游无法确定 continuity/seam_mode/end_anchor")
        return None
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        add(BLOCK, "故事板", p, "storyboard.json 缺 clips[]")
        return None
    return data
def _route_allows_no_firstframe(route: Mapping[str, Any]) -> bool:
    """Only empty T2V or a ready explicit reference-to-video contract may skip a hero frame."""
    mode = str(route.get("mode") or "").strip().lower()
    if mode in {"reference_to_video", "reference2video", "r2v"}:
        contract = route.get("reference_to_video_contract")
        return route.get("reference_bundle_status") == "ready" and isinstance(contract, Mapping) and bool(contract)
    if mode not in {"text2video", "t2v"}:
        return False
    identity = str(route.get("identity_requirement") or "").strip().lower()
    if identity in {"", "none", "not_needed"}:
        return True
    return route.get("experimental_t2v") is True
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
    # 铁律 B11（2026-06-27）：风格化项目脸一致性发布闸 demo 也要求（不随 profile 降级）。
    # 但 prompt 生成阶段还没有像素可验，不应因本机缺 StyleID 权重阻断出图 prompt 产物；
    # 真正进入付费/像素/发布边界时仍按 demo=production 硬闸执行。
    if str(stage or "") in {"image_prompt_preflight", "image_prompt"}:
        return False, "prompt-only stage"
    # 注：调用方 check_stylized_face_encoder_policy 已先 early-return 非风格化项目，故这里对
    # 风格化项目在像素/发布阶段生效，等于"风格化项目 demo=production 都要 StyleID 发布闸"。
    return True, "release standard (demo=production·B11)"
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
LONG_RUNNING_EP_THRESHOLD = 3  # 到第3集起跨集脸漂累积已成真问题，长线剧用无持久主体 ID 后端该提示升档
def long_running_weak_backend_advice(canon: str, cur_ep_num: int, ep_count: int) -> bool:
    """长线剧 × 无持久主体后端 是否应提示升档（纯函数·可测）。
    True = 当前后端无原生主体/角色 ID 能力，且项目确属多集长剧（当前集号或已有集数 ≥ 阈值）；
    单集/双集 demo 与已是持久主体后端都返回 False，不打扰。"""
    if image_backend_supports_persistent_subject(canon or ""):
        return False
    return max(int(cur_ep_num or 0), int(ep_count or 0)) >= LONG_RUNNING_EP_THRESHOLD
def _long_running_subjectless_severity(root: str, ep: str) -> str:
    """长线剧×无持久主体后端→核心/常驻角色缺身份锁=无条件 BLOCK（demo 与 production 同标准）。

    铁律（2026-06-27 用户裁决·见 docs/skill-design-principles.md B11 + consistency_charter）：为高质量
    出图/出视频建的 load-bearing 一致性闸**不得按 profile 降级，demo 不得降低标准**。此前 c9d37df5 把它
    悄悄改成 production-only（提交信息只说"措辞优化"）→默认 demo 不挡跨集脸漂，现恢复无条件 BLOCK。"""
    return BLOCK
IDENTITY_LOCK_READY_STATUSES = {"ready", "registered", "validated", "deployed"}
IMAGE2IMAGE_REFERENCE_LOCK_MODES = {
    "image2image_reference_chain",
    "controlled_multiref_generation",
    "project_memory_reference_bundle",
    "true_image_reference_chain",
}
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
def _image2image_reference_lock_ready(cfg: Mapping[str, Any]) -> bool:
    """Ready execution lock for subjectless backends using real image inputs.

    This is not a persistent subject ID. It only satisfies the long-running
    gate when the project explicitly commits to actual image inputs, a
    reference manifest, and full QC so the chain is auditable.
    """
    status = str(cfg.get("status") or "").strip()
    mode = str(cfg.get("mode") or cfg.get("method") or "").strip()
    if status not in IDENTITY_LOCK_READY_STATUSES or mode not in IMAGE2IMAGE_REFERENCE_LOCK_MODES:
        return False
    actual_refs = (
        cfg.get("actual_image_input_required") is True
        or cfg.get("reference_manifest_required") is True
        or bool(str(cfg.get("reference_input_mode") or "").strip())
    )
    full_qc = (
        cfg.get("full_qc_required") is True
        or str(cfg.get("qc_policy") or "").strip().lower() in {"full", "full_image_qc", "full_qc"}
    )
    return actual_refs and full_qc
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
        if mode in IMAGE2IMAGE_REFERENCE_LOCK_MODES:
            if _image2image_reference_lock_ready(cfg):
                return True
            continue
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
def identity_lock_gap_notes(root: str, image_backend: str = "") -> List[str]:
    """Human-readable details for identity-lock blockers without changing pass/fail.

    `core_forms_without_image_identity_lock()` intentionally returns display labels only.
    This companion explains common near-miss states, especially LoRA `training`/`candidate`
    records that are useful progress but still not executable locks until model + validation
    are present and usable on the current image backend.
    """
    reg = load_json(identity_registry_path(root))
    if not isinstance(reg, dict):
        return []
    notes: List[str] = []
    for char in reg.get("characters", []) or []:
        if not isinstance(char, dict):
            continue
        scope = f"{char.get('tier') or ''} {char.get('scope') or ''}"
        if not _CORE_SCOPE_RE.search(scope):
            continue
        cid = str(char.get("id") or "").strip()
        name = str(char.get("name") or cid or "?").strip()
        for form in char.get("forms", []) or []:
            if not isinstance(form, dict) or _image_form_has_identity_lock(form, image_backend):
                continue
            form_name = str(form.get("form") or "").strip()
            label = f"{name}({cid}/{form_name})" if form_name else f"{name}({cid})"
            adapters = form.get("identity_adapters") if isinstance(form.get("identity_adapters"), Mapping) else {}
            image = adapters.get("image") if isinstance(adapters.get("image"), Mapping) else {}
            near_image2image = []
            for backend, cfg in image.items():
                if not isinstance(cfg, Mapping):
                    continue
                mode = str(cfg.get("mode") or cfg.get("method") or "").strip()
                if mode in IMAGE2IMAGE_REFERENCE_LOCK_MODES and not _image2image_reference_lock_ready(cfg):
                    near_image2image.append(str(backend))
            lora = adapters.get("lora") if isinstance(adapters.get("lora"), Mapping) else {}
            if not isinstance(lora, Mapping) or not lora:
                if near_image2image:
                    notes.append(f"{label}: image2image参考链未满足 ready 条件（{','.join(near_image2image)} 缺真实图片入参/reference_manifest/full QC 声明）")
                else:
                    notes.append(f"{label}: LoRA=absent")
                continue
            status = str(lora.get("status") or "absent").strip() or "absent"
            gaps: List[str] = []
            if not str(lora.get("model_path") or "").strip():
                gaps.append("缺 model_path/.safetensors")
            if not str(lora.get("validation_report") or "").strip():
                gaps.append("缺 validation_report")
            if not _lora_usable_on_image_backend(lora, image_backend):
                gaps.append(f"不可用于当前生图后端 {image_backend or 'unknown'}")
            train_job_rel = str(lora.get("train_job") or "").strip()
            if train_job_rel:
                train_job_path = train_job_rel if os.path.isabs(train_job_rel) else os.path.join(root, train_job_rel)
                train_job = load_json(train_job_path)
                if isinstance(train_job, Mapping):
                    package = train_job.get("cloud_package") if isinstance(train_job.get("cloud_package"), Mapping) else {}
                    if package:
                        pkg_status = str(package.get("status") or "").strip()
                        if pkg_status:
                            gaps.append(f"cloud_package={pkg_status}")
            if near_image2image:
                gaps.append(f"image2image参考链未满足 ready 条件: {','.join(near_image2image)}")
            notes.append(f"{label}: LoRA={status}" + (f"（{'; '.join(gaps)}）" if gaps else ""))
    return notes
# G-I1·2026-06-24 流程自审落地：长线剧的默认起点应是「可注册主体 ID」（②·先于 LoRA），不是死扛
# 无持久主体的 GPT Image 2。设计宪法 C4 不许私自写死后端——故不做静默 auto-flip，而是给确定性推荐文案，
# 由 gate BLOCK 携带，让用户在 n2d-image 选择点带 ② 推荐升档并摆「换后端=整集重做定妆的一致性税」知情权衡。
IMAGE_IDENTITY_LOCK_RECOMMENDATION = (
    "【G-I1 推荐升档】长线默认起点应为可注册主体 ID（②·先于 LoRA）：可灵主体库 / 即梦角色库 / "
    "Seedream Universal Reference（注册一次按 ID 跨镜跨集引用）；或对核心角色训 LoRA。"
    "hero/反复崩脸角色可叠 max-lock 栈：主体 ID + PuLID(脸保真) + 低强度角色 LoRA(~0.6) + ControlNet。"
    "在 n2d-image 选择点 `生图模型` 带此推荐向用户摆「换后端=整集重做定妆的一致性税」知情权衡，不私自写死后端。"
)
def _clip_blob(clip: dict) -> str:
    # 复杂镜头关键词检测只扫散文描述，不扫结构化 `continuity` 块——其 schema 字段名/枚举值（如
    # `eyeline` 字段、`transition:"eyeline"`）与 dialogue_shot_reverse 关键词 `eyeline` 撞名，会让
    # 每个填了 continuity.eyeline（formats §4 要求每 clip 填）的合规 clip 误判成对话反打。
    # 三轨元数据同理：`dialogue_indices` 是对白分配账本，不代表该镜头是对话反打复杂镜。
    ignored = {
        "continuity",
        "dialogue_indices",
        "narration_indices",
        "screen_text_lines",
        "screen_text_policy",
    }
    scanned = {k: v for k, v in clip.items() if k not in ignored} if isinstance(clip, dict) else clip
    try:
        return json.dumps(scanned, ensure_ascii=False)
    except Exception:
        return str(scanned)
def _first_template_keyword_hit(blob: str) -> Optional[str]:
    realm_portal_weak_terms = {
        "穿越", "魂穿", "身穿", "穿到", "醒来在", "异界", "transmigration", "isekai",
    }
    realm_portal_visual_terms = {
        "时空裂缝", "传送门", "传送阵", "秘境入口", "遗迹入口", "跨界", "portal",
        "secret realm entrance", "卷入", "裂缝", "旋涡", "漩涡",
        "门实体", "光门", "空间门", "portal_lock", "source_world_anchor", "destination_anchor",
    }
    low = blob.lower()
    for template_id, words in SPECIAL_SHOT_KEYWORDS:
        for word in words:
            token = str(word).strip()
            if not token:
                continue
            low_token = token.lower()
            if template_id == "realm_portal" and low_token in realm_portal_weak_terms:
                has_visual_portal = any(term in blob or term.lower() in low for term in realm_portal_visual_terms)
                if not has_visual_portal:
                    continue
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
    tier = str(char.get("tier") or form.get("tier") or "").strip()
    forbidden = form.get("drift_forbidden") or char.get("drift_forbidden") or []
    forbidden_blob = " ".join(str(x) for x in forbidden) if isinstance(forbidden, list) else str(forbidden)
    partial_marked = (
        form.get("restricted_partial") is True
        or tier == "restricted_partial"
        or build_tier.startswith("restricted_partial")
    )
    requested = (
        partial_marked
        or (
            form_name in {"局部参考", "局部参考（暂不正脸）"}
            and (
                face_policy == "no_full_face"
                or build_tier.startswith("restricted_partial")
                or "no_full_face" in forbidden_blob
                or "no_clear_facial_features" in forbidden_blob
            )
        )
    )
    if not requested:
        return False
    # 主角/核心长线不得靠 form.build_tier 自报 partial 降档。
    # 若创意上确实全程帘后/局部，必须在角色或形态登记可审计例外。
    if character_library_tier_for_record(char) == CHARACTER_LIBRARY_TIER_CORE:
        combined = dict(char)
        for key in (
            "restricted_partial_contract",
            "face_policy",
            "restricted_partial",
            "library_tier",
            "tier",
        ):
            if key in form:
                combined[key] = form.get(key)
        return restricted_partial_contract_valid(combined)
    return True
def _gate_make_clip_id(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("clip_id") or clip.get("id") or clip.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return f"Clip_{idx:02d}"
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
        if status in IDENTITY_READY_STATUSES and not _has_identity_handle(cfg) and not _image2image_reference_lock_ready(cfg):
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
            "核心动作角色缺 signature_equipment；请把主角常用武器/法宝/标志性道具登记为 "
            "WEAPON_xx/PROP_xx/VFX_xx，并在角色 form 上绑定，避免主角形象只锁脸不锁随身装备。",
            return_to_stage="image",
        )
        return
    invalid = [ref for ref in refs if not SIGNATURE_EQUIPMENT_ID_RE.match(ref)]
    if invalid:
        add(
            BLOCK,
            "主角装备库",
            f"{floc} signature_equipment",
            "signature_equipment 只能引用资产注册 ID（WEAPON_/PROP_/VFX_/OUTFIT_/MOUNT_GROUP_）："
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
def _validate_character_asset_bundle(
    root: str,
    char: dict,
    loc: str,
    *,
    expected_tier: str = "",
    expected_tier_evidence: Optional[Mapping[str, Any]] = None,
) -> None:
    """Every image-entering character must have a portable project-local asset bundle."""
    bundle = char.get("asset_bundle")
    char_id = str(char.get("id") or "").strip()
    expected_tier = (
        canonical_normalize_character_library_tier(expected_tier)
        or character_library_tier_for_record(char)
    )
    observed_count = 0
    if isinstance(expected_tier_evidence, Mapping):
        try:
            observed_count = max(0, int(expected_tier_evidence.get("episode_count") or 0))
        except (TypeError, ValueError):
            observed_count = 0
    evidence_suffix = ""
    if observed_count:
        episodes = expected_tier_evidence.get("episodes") if isinstance(expected_tier_evidence, Mapping) else []
        episode_sample = "、".join(str(value) for value in (episodes or [])[:5])
        evidence_suffix = (
            f" registry 外已物化 storyboard 的结构化在场证据显示该角色至少出场 {observed_count} 集"
            + (f"（{episode_sample}{'…' if len(episodes or []) > 5 else ''}）" if episode_sample else "")
            + "；该观测是最低档下界，不能由四份资产声明共同降档覆盖。"
        )
    if not isinstance(bundle, dict):
        add(BLOCK, "角色资产包", loc,
            "人物角色缺 asset_bundle；所有入镜人物（含短线/功能角色）都必须指向 "
            "角色库/<CHAR_ID>__<slug>/manifest.json。角色体量决定角色库档位（core_full / recurring_standard / "
            "named_minimal），但不取消基础资产包；否则换模型/工作流/视频工具时无法继承 "
            "reference/prompts/lora/voice/adapters/qc。")
        return
    manifest_rel = str(bundle.get("manifest") or "").strip()
    package_dir = str(bundle.get("package_dir") or "").strip()
    if not manifest_rel:
        add(BLOCK, "角色资产包", f"{loc} asset_bundle.manifest", "asset_bundle.manifest 缺失")
        return
    if not package_dir:
        add(BLOCK, "角色资产包", f"{loc} asset_bundle.package_dir", "asset_bundle.package_dir 缺失")
    normalized_manifest_rel = manifest_rel.replace("\\", "/")
    if normalized_manifest_rel.startswith("设定库/character_assets/"):
        add(
            WARN,
            "角色资产包",
            f"{loc} asset_bundle.manifest",
            "仍在使用旧路径 `设定库/character_assets/`；请迁到作品根 `角色库/`，不要长期并存两套目录。",
        )
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
    char_tier_raw = str(char.get("library_tier") or "").strip()
    bundle_tier_raw = str(bundle.get("tier") or "").strip()
    declared_char_tier = canonical_normalize_character_library_tier(char_tier_raw)
    declared_bundle_tier = canonical_normalize_character_library_tier(bundle_tier_raw)
    manifest_tier_raw = str(manifest.get("library_tier") or "").strip()
    manifest_tier = canonical_normalize_character_library_tier(manifest_tier_raw)
    if manifest_tier_raw and not manifest_tier:
        add(BLOCK, "角色资产包", manifest_path,
            "library_tier 必须是 core_full / recurring_standard / named_minimal / restricted_partial")
    elif not manifest_tier:
        add(BLOCK, "角色资产包", manifest_path,
            "角色资产包未登记 library_tier；档位是多视图验收的承重证据，"
            "不能用缺省值猜测。请迁移后重跑定妆包生成。")
    if not char_tier_raw or not declared_char_tier:
        add(
            BLOCK,
            "角色资产包",
            loc,
            "registry character.library_tier 缺失或非法；人物剧情档位必须在角色真值源显式落档。",
        )
    if not bundle_tier_raw or not declared_bundle_tier:
        add(
            BLOCK,
            "角色资产包",
            loc,
            "asset_bundle.tier 缺失或非法；资产包引用不能靠 manifest 猜档位。",
        )
    tier_sources = {
        "character.library_tier": declared_char_tier,
        "asset_bundle.tier": declared_bundle_tier,
        "manifest.library_tier": manifest_tier,
    }
    for source, tier in tier_sources.items():
        if tier and not character_library_tier_is_at_least(tier, expected_tier):
            add(
                BLOCK,
                "角色资产包",
                manifest_path,
                f"{source}={tier} 低于剧情权重推导的最低档位 {expected_tier}；"
                f"主角/核心长线不得靠自报降档绕过多视图。{evidence_suffix}",
            )
    canonical_bundle_tier = declared_char_tier or expected_tier
    disagreements = {
        source: tier
        for source, tier in tier_sources.items()
        if tier and canonical_bundle_tier and tier != canonical_bundle_tier
    }
    for index, form in enumerate(char.get("forms") or []):
        if not isinstance(form, Mapping):
            continue
        atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
        atlas_raw = str(atlas.get("build_tier") or "").strip()
        atlas_tier = canonical_normalize_character_library_tier(atlas_raw)
        if not atlas_raw:
            disagreements[f"forms[{index}].reference_atlas.build_tier"] = "(missing)"
        elif not atlas_tier:
            disagreements[f"forms[{index}].reference_atlas.build_tier"] = atlas_raw
        elif atlas_tier and canonical_bundle_tier and atlas_tier != canonical_bundle_tier:
            disagreements[f"forms[{index}].reference_atlas.build_tier"] = atlas_tier
    if disagreements:
        detail = ", ".join(f"{source}={tier}" for source, tier in sorted(disagreements.items()))
        add(
            BLOCK,
            "角色资产包",
            manifest_path,
            f"角色库档位必须在 character / asset_bundle / manifest / reference_atlas 四处一致；"
            f"当前主档={canonical_bundle_tier}，冲突：{detail}。",
        )
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
            "45°/侧/背优先从人审通过 turnaround 拆，半身/脸部特写优先从已通过正面裁；"
            "若使用真实 image2image/multiref 后端生成，必须登记 method=controlled_multiref_generation "
            "并保留可校验 source_path/source_sha256。"
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


def _normalize_character_library_tier(value: object) -> str:
    """历史兼容包装；新代码应直接使用 n2d_contract 的归一函数。"""
    return canonical_normalize_character_library_tier(
        value, default=CHARACTER_LIBRARY_TIER_CORE
    )


def _required_character_makeup_views(
    form: Mapping[str, Any], expected_tier: str = ""
) -> Tuple[str, ...]:
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    tier = canonical_normalize_character_library_tier(
        expected_tier or atlas.get("build_tier"), default=CHARACTER_LIBRARY_TIER_CORE
    )
    return required_character_library_views(tier)


def _required_character_reference_group_fields(
    form: Mapping[str, Any], expected_tier: str = ""
) -> Tuple[str, ...]:
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    tier = canonical_normalize_character_library_tier(
        expected_tier or atlas.get("build_tier"), default=CHARACTER_LIBRARY_TIER_CORE
    )
    return required_character_reference_group_fields(tier)


def _validate_reference_atlas(
    root: str,
    form: dict,
    floc: str,
    strict_references: bool,
    verify_source_hash: bool,
    restricted_partial: bool = False,
    expected_tier: str = "",
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
    raw_build_tier = str(atlas.get("build_tier") or "").strip()
    library_tier = canonical_normalize_character_library_tier(raw_build_tier)
    minimum_tier = canonical_normalize_character_library_tier(expected_tier) or library_tier
    if strict_references and not library_tier:
        add(BLOCK, "资产身份注册层", floc,
            "reference_atlas.build_tier 缺失或非法；不得用缺省档位猜测必需视图。")
    if (
        strict_references
        and library_tier
        and minimum_tier
        and not character_library_tier_is_at_least(library_tier, minimum_tier)
    ):
        add(
            BLOCK,
            "资产身份注册层",
            floc,
            f"reference_atlas.build_tier={library_tier} 低于该人物最低档位 {minimum_tier}；"
                "不得通过伪造低档 atlas 规避核心多视图。",
            )
    effective_tier = minimum_tier or library_tier or CHARACTER_LIBRARY_TIER_CORE
    required_views = _required_character_makeup_views(form, effective_tier)
    base_views = atlas.get("base_views")
    if not isinstance(base_views, dict):
        if strict_references:
            add(BLOCK, "资产身份注册层", floc,
                f"reference_atlas.base_views 缺失；角色库档位 {effective_tier} 必须登记本档基础角度与 "
                "half_body 或 full_body 的 ready 状态。")
    else:
        missing_views = [key for key in required_views if key not in base_views]
        if "half_body" not in base_views and "full_body" not in base_views:
            missing_views.append("half_body_or_full_body")
        if missing_views and strict_references:
            add(BLOCK, "资产身份注册层", floc,
                "reference_atlas.base_views 缺基础视角：" + ", ".join(missing_views))
        if strict_references:
            not_ready: List[str] = []
            required_view_keys = [key for key in required_views if key in base_views]
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
                    + f"；当前角色库档位={effective_tier}，本档必需项不能登记为 planned 后放行。")
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
_COSTUME_VARIANT_RE = re.compile(r"_(45度|三分之二|侧|侧面|半身|全身|背|背面|脸部特写|三视图|设定表|表情(?:_.+)?)$")
_COSTUME_NON_FACE = ("三视图", "设定表")  # 人审拼版，非脸度量基准；脸部特写/表情仍是可喂图参考
def _costume_stem(basename: str) -> str:
    s = basename[:-4] if basename.endswith(".png") else basename
    return _COSTUME_VARIANT_RE.sub("", s)
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
    # dof_profile（可选·per-scene 景深锁）：登记了就必须用可识别 depth_intent，否则景深锁(DOFL)静默失效。
    dof_profile = scene_dna.get("dof_profile")
    if isinstance(dof_profile, dict) and dof_profile.get("depth_intent") is not None:
        intent = str(dof_profile.get("depth_intent") or "").strip().lower()
        if not any(m in intent for m in _DOF_INTENT_TOKENS):
            add(WARN, "场景 DNA", f"{loc} scene_dna.dof_profile.depth_intent",
                f"dof_profile.depth_intent=「{dof_profile.get('depth_intent')}」无法识别（应含 shallow/浅·deep/深焦·medium/中）；"
                "景深锁(DOFL)会对该场景静默失效，请改用可识别值。")
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
def _weapon_term_is_negated(blob: str, start: int) -> bool:
    """Do not promote assets to weapon-like solely from negative/forbidden text."""
    window = blob[max(0, start - 12):start]
    return any(token in window for token in ("不要", "不得", "不能", "不应", "不是", "非", "禁止", "避免", "不放大成"))
def _is_weapon_like_asset(asset: Mapping[str, object]) -> bool:
    asset_type = str(asset.get("type") or "").strip().lower()
    if asset_type in ASSET_WEAPON_TYPES:
        return True
    if str(asset.get("id") or "").strip().startswith("WEAPON_"):
        return True
    weapon_like_role = str(asset.get("weapon_like_role") or "").strip().lower()
    if weapon_like_role in {"vfx_only", "effect_only", "not_entity_weapon", "not_weapon", "prop_only"}:
        return False
    if asset_type in {"vfx", "effect"} and asset.get("is_entity_weapon") is False:
        return False
    if asset_type in {"vfx", "effect"} and weapon_like_role in {"vfx_only", "effect_only", "not_entity_weapon"}:
        return False
    # Scan creative semantics only.  Evidence metadata such as
    # ``artifact_sha256`` contains the English word ``artifact`` and used to
    # promote every finalized prop (bucket, cloth bag, nameplate...) to a
    # magic weapon.  Paths, hashes, receipts and adapter records are not
    # evidence of an asset's story function.
    semantic = {
        key: asset.get(key)
        for key in (
            "id", "type", "name", "description", "positive", "current_state",
            "weapon_like_role", "constraints", "drift_forbidden", "scene_dna",
            "lifecycle", "notes",
        )
        if key in asset
    }
    blob = json.dumps(semantic, ensure_ascii=False).lower()
    for term in WEAPON_LIKE_ASSET_TERMS:
        needle = term.lower()
        if re.fullmatch(r"[a-z_]+", needle):
            if re.search(rf"(?<![a-z]){re.escape(needle)}(?![a-z])", blob):
                return True
        elif needle in blob:
            start = blob.find(needle)
            if not _weapon_term_is_negated(blob, start):
                return True
    return False
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
def _registry_relative_scales(root: str) -> Dict[str, str]:
    """从 identity_registry 取每个角色显示名 → 声明的 physical_scale.relative_scale（相对身量）。
    只有 relative_scale 进 prompt（绝对 height_cm/体重是写作元数据，不注入），故对账只看它。
    取角色任一 form 上首个非空 relative_scale；名字按 / ／ 切，与 `_registry_character_names` 同口径。"""
    data = load_json(identity_registry_path(root))
    if not isinstance(data, dict):
        return {}
    chars = data.get("characters")
    if isinstance(chars, dict):
        chars = list(chars.values())
    if not isinstance(chars, list):
        return {}
    out: Dict[str, str] = {}
    for c in chars:
        if not isinstance(c, dict):
            continue
        rs = ""
        for f in (c.get("forms") or []):
            if isinstance(f, dict):
                cand = str((f.get("physical_scale") or {}).get("relative_scale") or "").strip()
                if cand:
                    rs = cand
                    break
        if not rs:
            continue
        for n in str(c.get("name") or "").replace("／", "/").split("/"):
            n = n.strip()
            if len(n) >= 2:
                out.setdefault(n, rs)
    return out
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
            "shot_type=mount_ride",
            "shot_type=vehicle_ride",
            "shot_type=vessel_flight",
            "shot_type=road_vehicle",
            "shot_type=stealth_stalk",
            "shot_type=kiss_or_near_kiss",
            "shot_type=intimate_interaction",
            "shot_type=hug_or_pull",
            "shot_type=dual_cultivation",
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
NATIVE_AV_SUBTITLE_ALIGNMENT_KIND = "n2d_native_av_subtitle_alignment"
NATIVE_VOICE_IDENTITY_SEGMENTS_KIND = "n2d_native_voice_identity_segments"
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
def native_av_physics_sidecar_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"native_av_physics_{ep}.json")
def native_av_subtitle_alignment_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"native_av_subtitle_alignment_{ep}.json")
def native_voice_identity_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"native_voice_identity_{ep}.json")
def native_voice_print_report_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"identity_voice_print_{ep}.json")
def _distribution_intent(root: str) -> str:
    data = load_json(compliance_manifest_path(root))
    if isinstance(data, dict):
        return _status(data.get("distribution_intent"))
    return _status(get_setting(root, "合规用途", ""))
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
        need_end = needs_end_anchor(clip)
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
MODEL_ROUTE_BASELINE_HIGH_RISK_SHOT_TYPES = {
    "action_fight",
    "action_chase",
    "escape",
    "breakthrough",
    "flight",
    "mount_ride",
    "vehicle_ride",
    "vessel_flight",
    "road_vehicle",
    "stealth_stalk",
    "magic_burst",
    "meditation_cultivation",
    "alchemy_forging",
    "dual_cultivation",
    "kiss_or_near_kiss",
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
    "consent_non_explicit_required",
    "energy_circulation_required",
    "micro_motion_readability_risk",
    "face_contact_risk",
    "micro_expression_required",
}
MODEL_ROUTE_SPEECH_SHOT_TYPES = {
    "dialogue_closeup",
    "dialogue_shot_reverse",
    "reveal_reaction_chain",
    "public_confrontation",
    "relationship_turn",
}
def _route_is_speech_like(route: Mapping[str, object]) -> bool:
    st = str(route.get("shot_type") or "").strip()
    flags = route.get("risk_flags")
    flag_set = {str(x) for x in flags} if isinstance(flags, list) else set()
    if st in MODEL_ROUTE_SPEECH_SHOT_TYPES:
        return True
    return "mouth_visible" in flag_set
def _route_needs_mouth_visible_audit(route: Mapping[str, object]) -> bool:
    native_policy = str(route.get("native_audio_policy") or "").strip()
    mode = str(route.get("mode") or "").strip()
    if native_policy in {"ambience", "native_sfx", "native_speech", "lipsync_condition_only"}:
        return True
    if mode in {"native_av", "voice_conditioned_lipsync"}:
        return True
    return _route_is_speech_like(route)
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
def _route_is_high_action(route: Mapping[str, Any]) -> bool:
    shot_type = str(route.get("shot_type") or "").strip()
    flags = {str(x).strip() for x in _listify(route.get("risk_flags")) if str(x).strip()}
    return (
        shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES
        or shot_type in MOTION_CONTROL_REQUIRED_SHOT_TYPES
        or bool(flags & set(MOTION_CONTROL_RISK_FLAGS))
        or bool(flags & {"high_action", "spectacle", "contact_motion", "fast_motion", "physics"})
    )
# 非原生锁绑定 = 仅靠参考组兜底/不支持（换后端会丢真正的锁脸力）。
_NON_NATIVE_BINDINGS = {"reference_group", "fallback_reference_group", "not_needed", "unsupported", ""}
_CORE_SCOPES = {"全篇", "长线", "核心", "主角"}
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
        "战场", "尸城", "破屋", "朝堂", "御案", "急报", "戟", "白气", "精气",
        "绘卷", "虚影", "龙珠", "雾影", "系统面板",
        "角色", "<角色>", "铜镜", "镜", "VFX", "万妖血脉", "噬妖", "系统面板", "潜行边缘",
    )
    names = set()
    for raw in re.findall(r"定妆_([^`\s，。、,）)]+)", refs):
        raw = re.sub(r"\.(?:png|jpe?g|webp)$", "", raw, flags=re.I)
        base = raw
        # Strip view/crop suffixes first, then local form labels. Otherwise
        # `定妆_沈念_常态_45度.png` and `定妆_沈念_常态_半身.png` are counted as
        # different "characters", which creates false multi-subject blockers.
        for _ in range(2):
            base = re.sub(
                r"_(45度|45°|三分之二|three_quarter|侧|侧面|半身|全身|背|背面|三视图|设定表|表情|脸部特写|头部特写|面部特写|局部|近景|特写|主参考|母本)$",
                "",
                base,
            )
            base = re.sub(
                r"_(常态|觉醒态|觉醒蓝调母本|战场形态|朝堂常态|断臂校尉|残兵剪影|群臣剪影|潜行态|人形|妖形|小妖群|裂口妖|少年态|幼年态|成年态|受伤态|伪装态|战斗态)$",
                "",
                base,
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
# CODEX_SPLIT_COMPOSITE_MARKERS 已上提 n2d_const.SPLIT_COMPOSITE_MARKERS（见文件顶部 import 别名）。
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
def _has_asset_id_binding(section: str, prefix: Any) -> bool:
    prefixes = prefix if isinstance(prefix, (list, tuple, set)) else (prefix,)
    return any(
        re.search(rf"`?{re.escape(str(p))}[A-Za-z0-9_\u4e00-\u9fff]+`?", section)
        for p in prefixes
        if str(p)
    )
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
    """核心角色定妆基础包：正/前45°/侧/后45°/背 + 服装参考 + 脸锚 + 人审拼版。"""
    has_front = _has_any(section, ("正面", "正脸", "主参考", "定妆_<角色>.png"))
    has_three_quarter = _has_any(section, ("45°", "45度", "三分之二侧脸", "3/4", "three_quarter", "_45度"))
    has_side = _has_any(section, ("_侧", "侧面", "侧脸"))
    has_rear_three_quarter = _has_any(section, (
        "后45°", "后 45°", "后45度", "后 45 度", "后三分之二", "rear_three_quarter",
    ))
    has_back = _has_any(section, ("_背", "背面", "背身"))
    has_outfit = _has_any(section, ("_半身", "_全身", "半身服装", "全身服装", "服装参考", "体态参考"))
    has_face_anchor = _has_any(section, ("脸部特写", "面部特写", "face_anchor_refs", "基础脸部参考", "表情参考", "同源表情", "表情_"))
    has_board = _has_any(section, (
        "_三视图", "标准三视图", "正/侧/背", "正面 / 侧面 / 背面",
        "turnaround", "五角周转", "五角设定表", "周转表",
    ))
    return (
        has_front
        and has_three_quarter
        and has_side
        and has_rear_three_quarter
        and has_back
        and has_outfit
        and has_face_anchor
        and has_board
    )
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
    has_resize = _has_any(section, (
        "放大", "重采样", "回项目画幅", "保持项目画幅", "恢复项目画幅",
        "回原画幅", "保持原画幅", "回 9:16", "回9:16", "9:16",
    ))
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
_FINALIZE_CHAR_RE = re.compile(r"CHAR_[A-Za-z0-9_\u4e00-\u9fff]+(?:/[^\s`，；、*]+)?")
_FINALIZE_ASSET_RE = re.compile(r"(?:MOUNT_GROUP|LOC|PROP|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_\u4e00-\u9fff]+")
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
def _sha256_file(path: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None
def _reference_node_path(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, Mapping):
        path = str(value.get("path") or "").strip()
        if path:
            return path
    if isinstance(value, list):
        for item in value:
            path = _reference_node_path(item)
            if path:
                return path
    return ""


def _form_anchor_relpath(form: Mapping) -> str:
    """form 的锚点定妆图项目相对路径；局部群像优先 silhouette 而不是 hand/outfit 片段。"""
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    partial_refs = atlas.get("partial_refs") if isinstance(atlas.get("partial_refs"), Mapping) else {}
    primary_keys = ("front", "primary", "silhouette")
    secondary_keys = ("three_quarter", "side", "halfbody", "outfit", "hand")
    for key in primary_keys:
        path = _reference_node_path(rg.get(key))
        if path:
            return path
    for key in primary_keys:
        path = _reference_node_path(partial_refs.get(key))
        if path:
            return path
    for key in secondary_keys:
        path = _reference_node_path(rg.get(key))
        if path:
            return path
    for key in secondary_keys:
        path = _reference_node_path(partial_refs.get(key))
        if path:
            return path
    for value in rg.values():
        path = _reference_node_path(value)
        if path:
            return path
    for value in partial_refs.values():
        path = _reference_node_path(value)
        if path:
            return path
    return ""
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
_VID_CLIP_HEAD_RE = re.compile(r"^##\s*Clip[_\s]*(\d+)", re.M)
_VID_FIRST_FRAME_RE = re.compile(r"\*\*首帧\*\*[^`]*`([^`]+\.png)`")
_VID_END_FRAME_RE = re.compile(r"\*\*尾帧\*\*[^`]*`([^`]+\.png)`")
# 匹配 `**中段锚帧**`（单锚帧）和 `**锚帧K**`（N 锚帧链）两种 prompt 字段
_VID_MID_FRAME_RE = re.compile(r"\*\*(?:中段)?锚帧\s*\d*\*\*[^`]*`([^`]+\.png)`")
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
def native_av_subtitle_alignment_required(root: str, stage: str) -> bool:
    if not is_native_av_production(root):
        return False
    if stage in {"review", "release"}:
        return True
    return _status(_distribution_intent(root)).lower() == "paid_distribution"
def _native_av_subtitle_status_ok(value: Any) -> bool:
    return str(value or "").strip().lower() in {"pass", "passed", "ok", "ready", "aligned", "done"}
def _native_av_subtitle_word_level(data: Mapping[str, Any]) -> bool:
    summary = data.get("summary") if isinstance(data.get("summary"), Mapping) else {}
    for container in (data, summary):
        for key in ("word_level", "word_level_alignment", "词级对齐"):
            if container.get(key) is True:
                return True
        granularity = str(container.get("alignment_granularity") or container.get("granularity") or "").lower()
        if "word" in granularity or "词" in granularity:
            return True
    return False
def _native_av_subtitle_errors(root: str, ep: str, data: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if data.get("kind") != NATIVE_AV_SUBTITLE_ALIGNMENT_KIND:
        errors.append(f"kind 应为 {NATIVE_AV_SUBTITLE_ALIGNMENT_KIND}")
    summary = data.get("summary") if isinstance(data.get("summary"), Mapping) else {}
    status = data.get("status") or summary.get("status") or data.get("verdict") or summary.get("verdict")
    if not _native_av_subtitle_status_ok(status):
        errors.append("status/verdict 必须为 pass/aligned/ready/done，不能把未对齐字幕当发布证据")
    tool = str(data.get("alignment_tool") or data.get("source") or data.get("aligner") or summary.get("alignment_tool") or "")
    if not tool.strip():
        errors.append("缺 alignment_tool/source；需记录 whisperx 或等效词级对齐工具")
    if not _native_av_subtitle_word_level(data):
        errors.append("缺词级对齐证据（word_level=true 或 alignment_granularity=word）")
    rel = str(data.get("subtitle_path") or summary.get("subtitle_path") or os.path.join("脚本", ep, "字幕_中文.srt"))
    sub_path = rel if os.path.isabs(rel) else os.path.join(root, rel)
    if not os.path.isfile(sub_path):
        errors.append(f"字幕文件不存在：{rel}")
    clips = data.get("clips")
    if clips is not None:
        if not isinstance(clips, list):
            errors.append("clips 必须是数组")
        else:
            bad = [
                str((row or {}).get("clip_id") or idx)
                for idx, row in enumerate(clips, start=1)
                if isinstance(row, Mapping)
                and not _native_av_subtitle_status_ok(row.get("status") or row.get("verdict") or "pass")
            ]
            if bad:
                errors.append("存在未通过字幕对齐的 Clip：" + "、".join(bad[:8]))
    return errors
def native_voice_identity_required(root: str, ep: str, stage: str) -> bool:
    # 铁律 B11（2026-06-27）：原生音画项目的原生音画身份 demo 也强制（不随 profile 降级）。
    return bool(is_native_av_production(root))
def _native_voice_segments_errors(root: str, ep: str, data: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if data.get("kind") != NATIVE_VOICE_IDENTITY_SEGMENTS_KIND:
        errors.append(f"kind 应为 {NATIVE_VOICE_IDENTITY_SEGMENTS_KIND}")
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append("segments 必须是非空数组")
        return errors
    usable = 0
    for idx, row in enumerate(segments, start=1):
        if not isinstance(row, Mapping):
            errors.append(f"segment#{idx} 必须是对象")
            continue
        char = str(row.get("character_id") or row.get("character") or row.get("speaker") or "").strip()
        key = str(row.get("speaker_key") or row.get("voice_key") or row.get("native_voice_key") or "").strip()
        wav = str(row.get("wav") or row.get("line_wav") or row.get("segment_wav") or row.get("audio_path") or "").strip()
        if not char:
            errors.append(f"segment#{idx} 缺 character_id/character")
        if not key:
            errors.append(f"segment#{idx} 缺 speaker_key/voice_key")
        if not wav:
            errors.append(f"segment#{idx} 缺 wav/audio_path")
            continue
        wav_path = wav if os.path.isabs(wav) else os.path.join(root, wav)
        if not os.path.isfile(wav_path):
            errors.append(f"segment#{idx} wav 不存在：{wav}")
        else:
            usable += 1
    if usable == 0:
        errors.append("没有可用 wav 片段")
    return errors[:12]
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
    "视频语义一致(VSEM)",
    "高动态成片证据(SPECV)",
}
REQUIRED_VIDEO_EVIDENCE_DIMENSIONS = {
    "运动质量(MOT1)",
    "相机空间轨迹(CAM1)",
    "主体视频一致(S2V)",
    "视频语义一致(VSEM)",
    "高动态成片证据(SPECV)",
}
# `视频证据强度=严格`（P5·2026-07-24 opt-in 强度档）：五个视频证据维度在 video 阶段的
# WARN 直接升 BLOCK——身份/运动/语义漂移在整批 clip 付费前就挡下，而不是等 compose/review
# 交付边界才硬化。默认 标准 保持既有行为（只在 evidence_missing/重复/关键场/交付边界升级），
# 现网项目零变化；净效果只加 BLOCK 不松任何既有闸（B11 对偶方向安全）。签收逃生口照旧。
_VIDEO_EVIDENCE_STRICT_VALUES = {"严格", "strict"}
_VIDEO_EVIDENCE_STRICT_CACHE: Dict[str, bool] = {}


def _video_evidence_strict_enabled(root: str) -> bool:
    key = os.path.abspath(str(root or "."))
    if key not in _VIDEO_EVIDENCE_STRICT_CACHE:
        enabled = False
        try:
            from settings import load_settings  # n2d/_lib（COMMON 已入 sys.path）
            raw = str(load_settings(key).get("视频证据强度") or "").strip().lower()
            enabled = raw in _VIDEO_EVIDENCE_STRICT_VALUES
        except Exception:
            enabled = False
        _VIDEO_EVIDENCE_STRICT_CACHE[key] = enabled
    return _VIDEO_EVIDENCE_STRICT_CACHE[key]
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
    loc_parts = [str(row.get(key) or "") for key in ("loc", "path", "png", "asset")]
    if isinstance(row.get("affected_artifacts"), list):
        loc_parts.extend(str(x) for x in row.get("affected_artifacts") or [] if x)
    loc = " ".join(part for part in loc_parts if part)
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
# W2/W3 光照/光位连续性 metric（world_continuity 产出，平时 advisory）——核心场景×交付边界升 BLOCK 的子集。
# **不含 daypart(W1)**：daypart 自己已是 2 级跳硬 block / 1 级软 warn，且昼夜切换常合法，留人工签收，不在此硬化。
_CORE_SCENE_LIGHT_BLOCK_METRICS = {"light_dir", "light_elevation", "light_anchor", "light_anchor_registered"}
# 核心打斗镜剪辑撞点硬化 code（combat_cue_apex_audit 产出·平时 advisory）——核心打斗镜×交付边界升 BLOCK 的子集。
# 只升「impact_frame 没带秒(峰值无处钉)」与「峰值钉的秒没 keyframe 锚(引用不存在的关键帧)」；
# combat_apex_no_edit_cue(info·有锚没用上·补强建议)不在硬化集。
_CORE_COMBAT_APEX_BLOCK_CODES = {"combat_apex_untimestamped", "combat_cue_apex_no_keyframe"}


def _row_scene_is_core(root: str, row: Mapping[str, Any]) -> bool:
    """finding 的 scene 是否命中 asset_registry 标注的核心场景（子串包含·与 scene_geometry 同口径）。"""
    scene = str(row.get("scene") or "").strip()
    if not scene or scene == "(全集)":
        return False
    try:
        cores = _ce_core_scene_names(root)
    except Exception:
        return False
    return any((scene in c or c in scene) for c in cores if c)


def _strict_advisory_should_block(root: str, ep: str, stage: str, row: Mapping[str, Any], summary: Mapping[str, Any]) -> Tuple[bool, str]:
    # 铁律 B11（2026-06-27）：strict-advisory 维度升 BLOCK 的实质条件（重复≥2/关键场/交付边界/对白近景
    # 口型/视频证据缺失）demo 也适用——去掉 `profile==production` 前置免单。注：真·脆弱启发式 finding 标
    # confidence="heuristic" 仍被 add() 自动降回 WARN（B10 兜底），故这里不会把低置信信号硬升成发布阻断。
    dim = str(row.get("dimension") or row.get("dim") or "")
    # 核心场景交付硬化（2026-06-28）：W2/W3 光照/光位连续性(light_dir/elevation/anchor)平时 advisory，但在
    # **核心场景 × 交付边界(compose/review)** 升 BLOCK——核心场景跨镜光位左右翻/顶底光跳是观众一眼硬伤，
    # 交付前必须挡。只升 light_* metric（不动 daypart W1·不动非核心场景·不动 image/video 阶段·几何 O2 在
    # 探测器侧本就核心=block 无需此处）。仍走 _advisory_row_signed_off：确属有意重打光可签收降回 WARN
    # （天气时辰(W1) 在 INTENTIONAL_DISCONTINUITY_ELIGIBLE_DIMENSIONS）。net 加 BLOCK·不松动既有任何闸。
    if (dim == "天气时辰(W1)"
            and str(row.get("metric") or "") in _CORE_SCENE_LIGHT_BLOCK_METRICS
            and stage in {"compose", "review"}
            and _row_scene_is_core(root, row)):
        if _advisory_row_signed_off(root, ep, row):
            return False, "已由 consistency_advisory_signoff 签收"
        return True, "核心场景交付边界光照不连续"
    # 核心打斗镜剪辑撞点硬化（2026-06-28·P1 升闸）：打斗剪辑 cue↔apex 对齐(combat_cue_apex_audit)平时 advisory，
    # 但 fight_exchange/magic_burst 的「impact_frame 没带秒/峰值钉的秒没 keyframe 锚」在
    # **核心打斗镜(核心场景 LOC 或 高潮/爆点/关键/反转 key 镜) × 交付边界(compose/review)** 升 BLOCK——
    # 剪辑峰值对不上命中关键帧=打击感软散，交付前挡。combat_apex_no_edit_cue(info)不在硬化集。
    # 走 _advisory_row_signed_off：确属有意/可接受可签收降回 WARN（与 W2/W3 同口径·net 加 BLOCK 不松动既有）。
    if (dim == "打斗撞点(SPEC-APEX)"
            and str(row.get("metric") or "") in _CORE_COMBAT_APEX_BLOCK_CODES
            and stage in {"compose", "review"}
            and (_row_scene_is_core(root, row) or _row_is_key_scene(row))):
        if _advisory_row_signed_off(root, ep, row):
            return False, "已由 consistency_advisory_signoff 签收"
        return True, "核心打斗镜剪辑撞点未对齐 apex 关键帧"
    if dim not in STRICT_ADVISORY_DIMENSIONS:
        return False, ""
    by_dim = summary.get("by_dim") if isinstance(summary.get("by_dim"), Mapping) else {}
    stat = by_dim.get(dim) if isinstance(by_dim.get(dim), Mapping) else {}
    repeated = int(stat.get("warn") or 0) >= 2
    key_scene = _row_is_key_scene(row)
    deliverable = stage in {"compose", "review"}
    video_evidence_missing = (
        stage == "video"
        and dim in REQUIRED_VIDEO_EVIDENCE_DIMENSIONS
        and bool(row.get("evidence_missing") or row.get("required_evidence_missing"))
    )
    # `视频证据强度=严格`（opt-in）：video 阶段五个视频证据维度的任何 finding 都升 BLOCK，
    # 在整批 clip 付费前拦住身份/运动/语义漂移；默认 标准 不改变既有触发条件。
    video_evidence_strict = (
        stage == "video"
        and dim in REQUIRED_VIDEO_EVIDENCE_DIMENSIONS
        and _video_evidence_strict_enabled(root)
    )
    # AV1 专属：带对白的近景/特写口型偏移即便孤例也升 block（口型对不上的大特写是观众第一眼硬伤）。
    dialogue_closeup = dim == "音画同步(AV1)" and _row_is_dialogue_closeup(row)
    if not (repeated or key_scene or deliverable or dialogue_closeup
            or video_evidence_missing or video_evidence_strict):
        return False, ""
    if _advisory_row_signed_off(root, ep, row):
        return False, "已由 consistency_advisory_signoff 签收"
    reason = ("对白近景口型" if dialogue_closeup else "重复同维度" if repeated
              else "关键场景" if key_scene else "视频后验证据缺失" if video_evidence_missing
              else "视频证据严格档" if video_evidence_strict else "交付边界")
    return True, reason
# 可被「有意不连续」签收为 WARN 的 native BLOCK 维度——只限世界/光线/轴线/调色/景深/状态转场
# 这类「创作者确可有意改变」的连续性轴（昼夜转场、越轴反打、戏剧性重打光、调色风格切换…）。
# 脸(G1)/辨识标记时序(MK1)/纯文生图/资产生命周期回退/契约继承不在此列：那些是真穿帮，
# 不接受「有意」签收，必须回源头修复。
INTENTIONAL_DISCONTINUITY_ELIGIBLE_DIMENSIONS = {
    "天气时辰(W1)",
    "光位方向(W2)",
    "轴线视线(X1)",
    "色温调色(GRADE1)",
    "景深一致(DOF1)",
    "合法不连续(DIS1)",
    "合法状态转场(STE)",
    "跨集场景漂移(SCNX)",
}
def _intentional_discontinuity_module():
    """Lazy-import sibling intentional_discontinuity.py as the single source of truth
    for signoff matching, so the gate doesn't fork a private copy of the match logic
    (independence rule: cross-skill copies drift). Returns the module or None."""
    cache = _intentional_discontinuity_module.__dict__
    if "mod" in cache:
        return cache["mod"]
    mod = None
    try:
        import importlib.util
        path = os.path.join(SCRIPT_DIR, "intentional_discontinuity.py")
        spec = importlib.util.spec_from_file_location("n2d_intentional_discontinuity", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
    except Exception:
        mod = None
    cache["mod"] = mod
    return mod
def _sanitized_intentional_manifest(root: str, ep: str) -> Optional[Dict[str, Any]]:
    """Load 生产数据/intentional_discontinuity_<ep>.json and keep only well-formed,
    NON-EXPIRED entries (clip_id + dimension + concrete reason + valid expires_at).
    `finding_is_signed_off` itself does not enforce expiry, so we filter here — an
    expired/incomplete exception can never sign anything off (forces re-confirmation,
    matching the advisory_signoff and compliance-gate re-confirm discipline)."""
    path = os.path.join(root, "生产数据", f"intentional_discontinuity_{ep}.json")
    data = load_json(path)
    if not isinstance(data, dict):
        return None
    entries = data.get("accepted") or data.get("exceptions") or data.get("signed_off") or []
    valid: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        clip = str(entry.get("clip_id") or entry.get("clip") or "").strip()
        dim = str(entry.get("dimension") or entry.get("dim") or "").strip()
        reason = str(entry.get("reason") or "").strip()
        if not clip or not dim or len(reason) < 8:
            continue
        if not _override_expiry_ok(entry.get("expires_at") or entry.get("expires")):
            continue
        valid.append(entry)
    return {"accepted": valid} if valid else None
def _native_block_intentional_signoff(root: str, ep: str, row: Mapping[str, Any]) -> Tuple[bool, str]:
    """Whether a native consistency BLOCK row is a *signed-off intended discontinuity*
    and may be downgraded to WARN at the delivery gate. Only eligible continuity
    dimensions qualify (lighting/world/axis/grade/dof/state-transition); face/marks-
    timeline/纯文生图/lifecycle are never sign-off-able here.

    Honors BOTH escape-hatch files so they finally both reach the gate (C1/C2):
      · intentional_discontinuity_<ep>.json — the creative "I intend this discontinuity"
        manifest (clip_id+dimension+reason), previously honored ONLY in the ledger/report;
      · consistency_advisory_signoff_<ep>.json — the production risk-acceptance signoff.
    """
    dim = str(row.get("dimension") or row.get("dim") or "")
    if dim not in INTENTIONAL_DISCONTINUITY_ELIGIBLE_DIMENSIONS:
        return False, ""
    manifest = _sanitized_intentional_manifest(root, ep)
    mod = _intentional_discontinuity_module()
    if manifest and mod is not None:
        shots = row.get("affected_shots") if isinstance(row.get("affected_shots"), list) else []
        arts = row.get("affected_artifacts") if isinstance(row.get("affected_artifacts"), list) else []
        haystack = [str(x) for x in (list(shots) + list(arts) + [row.get("loc") or row.get("path") or ""]) if x]
        match_row = {
            "dimension": dim,
            "message": str(row.get("message") or row.get("msg") or ""),
            "text": " ".join(haystack),
        }
        try:
            if mod.finding_is_signed_off(match_row, manifest):
                return True, "intentional_discontinuity"
        except Exception:
            pass
    if _advisory_row_signed_off(root, ep, row):
        return True, "consistency_advisory_signoff"
    return False, ""
def _canonical_fingerprint_fresh(root: str, canonical_path: str):
    """True/False/None：canonical 表是否对应当前图片（None=无 inputs_fingerprint 无法判定）。

    与 check_drift_report_freshness 同源——复用 skill_snapshot.fingerprint_is_fresh 的内容指纹，
    把「文件在=放行」收紧为「指纹对得上当前图=放行」。"""
    if fingerprint_is_fresh is None:
        return None
    try:
        data = json.load(open(canonical_path, encoding="utf-8"))
    except Exception:
        return None
    return fingerprint_is_fresh((data or {}).get("inputs_fingerprint"), root)
def _check_fidelity_gate_active(root: str, ep: str, stage: str) -> None:
    """Ensure fidelity-gate (vlm_verify --write canonical pass table) is active.

    Follows the check_drift_report_freshness pattern: absent with prior episodes
    judged = stale (BLOCK), absent in production boundary = BLOCK, absent in image
    stage = advisory only (don't block pipelines without VLM backend).

    compose/review + production → BLOCK (risk 0.9): delivery boundary requires
    canonical verification that face scores aren't gamed by stable-but-wrong renders.
    video + production → WARN (risk 0.7): pre-warning before compose block.
    image → WARN (risk 0.5): don't block image gen for pipelines without VLM backend.
    """
    canonical_path = os.path.join(root, "生产数据", f"vlm_canonical_{ep}.json")
    has_canonical = os.path.isfile(canonical_path)
    stale_reason = None
    if has_canonical:
        # #4（2026-06-28）：不再只看「文件在不在」——必须证明 canonical 表对应当前这批图。
        # vlm_verify 后图片若又重出，旧 canonical 的脸分数不能再用来糊弄终验（present-but-stale）。
        fresh = _canonical_fingerprint_fresh(root, canonical_path)
        if fresh is True:
            return  # 真新鲜：照旧放行
        # 陈旧 / 无指纹无法自证：当作「fidelity-gate 未对当前图激活」同等处理，落入下方分级逻辑。
        stale_reason = ("canonical 表已陈旧——vlm_verify 落档后图片又重出" if fresh is False
                        else "canonical 表无 inputs_fingerprint，无法证明对应当前图片（旧版 vlm_verify 产物）")
    # Check if any prior episode has canonical data (stale detection)
    prior_canonical = False
    try:
        prod_dir = os.path.join(root, "生产数据")
        if os.path.isdir(prod_dir):
            for fn in os.listdir(prod_dir):
                if fn.startswith("vlm_canonical_") and fn.endswith(".json") and fn != f"vlm_canonical_{ep}.json":
                    prior_canonical = True
                    break
    except Exception:
        pass
    return_to = "image"
    scope = "回 n2d-image 重出 canonical 不通过的镜"
    allow_degraded = degraded_qc_active(root)
    # 铁律 B11（2026-06-27）：终验 fidelity-gate（像素 VLM 脸验证）demo 与 production 同标准——
    # 不随 profile 降级；缺 VLM 后端不再是 demo 静默 WARN 免单，而是 BLOCK，唯一出口是显式留痕
    # N2D_ALLOW_DEGRADED_QC=1（C4 豁免堵死：把"缺依赖默认放行"改成"缺依赖必须显式自负其责"）。
    if stage in {"compose", "review"}:
        if allow_degraded:
            note_degraded_qc_waiver("fidelity-gate", ep, canonical_path,
                                    stale_reason or "VLM fidelity-gate 未激活·终验降级放行")
            add(WARN, "fidelity-gate", canonical_path,
                f"{(stale_reason + '；') if stale_reason else ''}"
                f"终验 fidelity-gate 未激活但已通过{degraded_qc_waiver_label(root)}放行（自负其责·已留痕）；"
                "脸一致分数未经 VLM canonical 验证，mechanical pass 不构成角色设定完整验证。",
                risk_score=0.8)
            return
        msg = (
            "终验须 fidelity-gate 激活——跑 vlm_verify --write 落 canonical 通过表。"
            "缺 VLM 语义判定时，脸(G1)的机械通过不构成角色设定完整验证。"
            "（无 VLM 后端时装依赖或显式 N2D_ALLOW_DEGRADED_QC=1 / 项目 internal_only demo 自负其责。）"
        )
        if stale_reason:
            msg = f"{stale_reason}（旧绿不算数·必须对当前图重跑 vlm_verify --write）——{msg}"
        elif prior_canonical:
            msg = f"前集已有 canonical 表，本集 stale（未重跑 vlm_verify --write）——{msg}"
        add(BLOCK, "fidelity-gate", canonical_path, msg,
            risk_score=0.9,
            return_to_stage=return_to,
            rerun_scope=scope,
            affected_artifacts=[canonical_path])
    elif stage == "video":
        add(WARN, "fidelity-gate", canonical_path,
            f"{(stale_reason + '；') if stale_reason else ''}"
            "出视频后建议跑 vlm_verify --write 落 canonical 通过表，否则 compose/review gate 会 BLOCK。",
            risk_score=0.7)
    else:
        add(WARN, "fidelity-gate", canonical_path,
            f"{(stale_reason + '；') if stale_reason else ''}"
            "fidelity-gate 未激活；vlm_verify --write 可在出图后跑 canonical 通过表。image 阶段不硬拦（出图后还没建 canonical 表），但 compose/review 会 BLOCK。",
            risk_score=0.5)
def _autorun_scene_verifier(root: str, ep: str, producer: str) -> None:
    """best-effort 自动跑场景验证器 producer（item 2：消「忘了手动 --write 而静默没跑」覆盖洞）。
    缺后端时它只产 probe-only sidecar（detector_ran=false），正好让覆盖闸看出「跑了但休眠」。"""
    script = os.path.join(SCRIPT_DIR, producer)
    if not os.path.isfile(script):
        return
    try:
        subprocess.run([sys.executable, script, root, ep, "--write"],
                       capture_output=True, timeout=600, check=False)
    except Exception:
        pass
def correlate_findings(gate_findings: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Auto-upgrade to BLOCK when multiple WARN_HI findings cluster on same clip.

    Groups findings by affected_artifacts / affected_shots. When the same clip has
    >=3 WARNs across >=3 different dimensions, >=2 independent evidence families,
    AND all are WARN_HI (risk_score >= 0.7), auto-upgrade the cluster to a BLOCK
    with a note about possible backend mismatch.

    Returns list of new BLOCK findings (to be added to gate output).
    Pure logic, no model/IO dependency.
    """
    CORRELATE_MIN_WARNS = 3
    CORRELATE_MIN_DIMS = 3
    CORRELATE_MIN_EVIDENCE_FAMILIES = 2

    groups: Dict[str, List[Dict[str, object]]] = {}
    for f in gate_findings:
        if f.get("sev") != WARN:
            continue
        rs = f.get("risk_score")
        try:
            rs = float(rs) if rs is not None else 0.0
        except (TypeError, ValueError):
            rs = 0.0
        if rs < 0.7:
            continue
        shots = f.get("affected_shots") or []
        artifacts = f.get("affected_artifacts") or []
        keys = [str(s) for s in shots] + [str(a) for a in artifacts]
        for key in keys:
            if key:
                groups.setdefault(key, []).append(f)

    upgrades: List[Dict[str, object]] = []
    for key, cluster in groups.items():
        unique = {(f.get("dim"), f.get("msg")): f for f in cluster}.values()
        if len(unique) < CORRELATE_MIN_WARNS:
            continue
        dims = {str(f.get("dim") or "") for f in unique} - {""}
        if len(dims) < CORRELATE_MIN_DIMS:
            continue
        families = {
            str(f.get("evidence_family") or _default_evidence_family(
                str(f.get("dim") or ""),
                str(f.get("msg") or ""),
                str(f.get("loc") or ""),
            ))
            for f in unique
        } - {""}
        # "unknown" is the unclassified default bucket, NOT an independent signal: it must
        # never serve as the 2nd family that licenses an auto-BLOCK. Require ≥2 *named*
        # independent families (掣肘三：去除 {face_embedding, unknown}=2 的虚假升级路径).
        independent_families = families - {"unknown"}
        if len(independent_families) < CORRELATE_MIN_EVIDENCE_FAMILIES:
            continue
        families = independent_families
        affected_shots = list({s for f in unique for s in (f.get("affected_shots") or []) if s})
        msg = (
            f"多维度同时漂移——{len(dims)} 个维度({', '.join(sorted(dims)[:5])})"
            f"同时对 {key} 报 WARN_HI（{len(unique)} 条，证据族 {', '.join(sorted(families)[:4])}）。"
            "可能后端不适配此镜头类型，建议切后端或重出。"
        )
        upgrades.append({
            "sev": BLOCK,
            "dim": "一致性总审",
            "loc": key,
            "msg": msg,
            "risk_score": 0.9,
            "return_to_stage": "image",
            "rerun_scope": "建议切后端或重出受影响镜头。",
            "affected_shots": affected_shots,
            "affected_artifacts": [key],
            "correlation_note": "由跨检测器相关性升级自动生成",
        })
    return upgrades
_SEV_RANK = {BLOCK: 3, WARN: 2, INFO: 1}
def consolidate_findings_by_shot(gate_findings: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """逐镜 finding 归并/仲裁（report 层·不改 verdict）——correlate_findings 的去重对偶。

    同一镜被多个检测器报（脸漂+表情+口型…）→ 按 `evidence_family` 去重（同证据族=同一根因，只计一次，
    防"双计数"），记最坏严重度、贡献维度、独立证据族数。让报告/dashboard 单点呈现"这一镜有问题"、
    severity 以**最坏维度**为准而非按条数累加，而不是让读者从散落的 N 条里自己拼。

    返回逐镜仲裁条目（按最坏严重度→镜名排序）。纯逻辑·无 IO·可测。"""
    by_shot: Dict[str, List[Dict[str, object]]] = {}
    for f in gate_findings:
        if f.get("sev") not in _SEV_RANK:
            continue
        for s in (f.get("affected_shots") or []):
            key = str(s)
            if key:
                by_shot.setdefault(key, []).append(f)
    out: List[Dict[str, object]] = []
    for shot, items in by_shot.items():
        dims = sorted({str(f.get("dim") or "") for f in items} - {""})
        families = {
            str(f.get("evidence_family") or _default_evidence_family(
                str(f.get("dim") or ""), str(f.get("msg") or ""), str(f.get("loc") or "")))
            for f in items
        } - {""}
        independent = sorted(families - {"unknown"})
        worst_rank = max((_SEV_RANK.get(f.get("sev"), 0) for f in items), default=0)
        worst_sev = {3: BLOCK, 2: WARN, 1: INFO}.get(worst_rank, INFO)
        out.append({
            "shot": shot,
            "verdict": worst_sev,
            "dims": dims,
            "independent_evidence_families": independent,
            "raw_finding_count": len(items),
            "merged_family_count": max(1, len(independent)),
        })
    out.sort(key=lambda r: (-_SEV_RANK.get(str(r["verdict"]), 0), str(r["shot"])))
    return out
SERIES_RETENTION_DIM = "系列留存(SERIES)"
def _series_ep_int(ep: str) -> Optional[int]:
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else None
PILOT_ARC_CONTRACT_REL = os.path.join("设定库", "pilot_arc_contract.json")
PILOT_ARC_REQUIRED_FIELDS = (
    "series_promise",
    "protagonist_desire",
    "repeatable_pleasure_loop",
    "long_question",
    "first_payoff_ep",
    "first_complication_ep",
    "first_reversal_ep",
)
def evidence_grade_findings(summary: Mapping[str, Any], stage: str,
                            allow_waiver: bool = False) -> List[Tuple[str, str]]:
    """证据等级账本 → [(sev, msg)]（纯函数·可测）。

    消费 consistency_audit 的 summary.evidence_grade.under_proven（advanced tier：torch-DINOv2 跨帧
    主体一致 / SyncNet 口型词级，依赖缺位时此前完全不阻断也不可见）。证据档=最弱可适用维度的级别。
    交付边界 compose/review → BLOCK(PENDING) 除非显式 waiver；更早阶段(image/video) → WARN 预警。
    无 under_proven → []。pixel tier 的 degraded 由全局 precision 闸处置，不在此重复 block。"""
    eg = summary.get("evidence_grade") if isinstance(summary.get("evidence_grade"), Mapping) else {}
    under = [str(d) for d in (eg.get("under_proven") or [])]
    if not under:
        return []
    weakest = str(eg.get("weakest") or "")
    base = (f"证据等级未达标(PENDING)：{('、').join(under)} 本可验到 embedding/pixel 级，本次只到结构/启发式级"
            f"（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）"
            f"{('；本集最弱证据级=' + weakest) if weakest else ''}。")
    delivery = stage in {"compose", "review"}
    if delivery and not allow_waiver:
        return [(BLOCK, base + "交付边界不放行——在装好进阶依赖的环境复跑，或显式 N2D_ALLOW_DEGRADED_QC=1 / 项目 internal_only demo 自负其责。")]
    note = "（已显式降级 QC 放行·自负其责）" if allow_waiver else "（出图/出视频阶段先 WARN，交付边界 compose/review 将 BLOCK）"
    return [(WARN, base + note)]
def _finding_sort_key(f: dict) -> tuple:
    """Sort key for gate findings: BLOCK → WARN (by risk_score desc) → INFO.
    Pure, testable, module-level so warn grading tests can call it."""
    order = {BLOCK: 0, WARN: 1, INFO: 2}
    sev_order = order.get(f.get("sev", INFO), 99)
    if f.get("sev") == WARN:
        rs = f.get("risk_score")
        # Negate so higher risk sorts earlier.  Ungraded warns default to 0.5
        # (moderate) which is also negated for correct interleaving.
        effective = float(rs) if rs is not None else 0.5
        return (sev_order, -effective)
    return (sev_order, 0.0)

__all__ = [
    'annotations',
    'argparse',
    'dt',
    'glob',
    'hashlib',
    'json',
    'os',
    're',
    'subprocess',
    'sys',
    'Any',
    'Dict',
    'Iterable',
    'List',
    'Mapping',
    'Optional',
    'Sequence',
    'Tuple',
    'SCRIPT_DIR',
    'COMMON',
    '_IDENTITY_SCRIPTS',
    'CODEX_SPLIT_COMPOSITE_MARKERS',
    'NATIVE_MULTI_SUBJECT_STRATEGY_MARKERS',
    'MULTI_SUBJECT_EXECUTION_STRATEGY_MARKERS',
    'MULTI_SUBJECT_SLOT_MARKERS',
    'MULTI_SUBJECT_POSITION_MARKERS',
    'APPROVED_IMAGE_BACKENDS',
    'ACTION_BEAT_CATEGORY_SPLIT_THRESHOLD',
    'ACTION_CHOREOGRAPHY_COMMON_FIELDS',
    'ACTION_CHOREOGRAPHY_SHOT_TYPES',
    'ACTION_CHOREOGRAPHY_SPECIFIC_FIELDS',
    'ASSET_REFERENCE_REGISTRY_KIND',
    'MIN_ACTION_BEAT_SECONDS',
    'action_beat_categories',
    'beat_decomposition',
    'CINEMATIC_CONTRACT_FIELDS',
    'CONSISTENCY_DIMENSIONS',
    'COMPLIANCE_AI_LABEL_STATUSES',
    'COMPLIANCE_ALLOWED_RIGHTS',
    'COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS',
    'COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS',
    'COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED',
    'COMPLIANCE_APPROVED_CHARACTER',
    'COMPLIANCE_BLOCKED_CHARACTER',
    'COMPLIANCE_DONE_STATUSES',
    'COMPLIANCE_DOMESTIC_REGIONS',
    'COMPLIANCE_MANIFEST_KIND',
    'COMPLIANCE_OVERSEAS_PLATFORMS',
    'COMPLIANCE_PLACEHOLDER_MARKERS',
    'COMPLIANCE_PLATFORM_REVIEW_STATUSES',
    'COMPLIANCE_PRE_BROADCAST_STATUSES',
    'COMPLIANCE_READY_STATUSES',
    'COMPLIANCE_SAFE_VOICE',
    'COMPLIANCE_STATUS_LIKE_VALUES',
    'EXPRESSION_SPAN_BIG',
    'EXPRESSION_SPAN_VALUES',
    'GATE_STAGES',
    'HIGH_MOTION_TEMPLATES',
    'IDENTITY_ADAPTER_MATRIX_KIND',
    'IDENTITY_HANDLE_FIELDS',
    'IDENTITY_IMAGE_ADAPTERS',
    'IDENTITY_REFERENCE_KEYS',
    'IDENTITY_REGISTRY_KIND',
    'IDENTITY_VIDEO_ADAPTERS',
    'image_backend_supports_persistent_subject',
    'identity_allowed_modes',
    'identity_registry_path',
    'MOTION_CONTROL_MANIFEST_KIND',
    'MOTION_CONTROL_REQUIRED_SHOT_TYPES',
    'MOTION_CONTROL_RISK_FLAGS',
    'production_mode_keys',
    'SPECTACLE_SEQUENCE_PLAN_KIND',
    'STYLE_CONTRACT_FIELDS',
    'SPECTACLE_TEMPLATE_FIELDS',
    'GENERIC_TEMPLATE_VALUES',
    'VIDEO_MODEL_ROUTES_KIND',
    'VISUAL_CONTRACT_FIELDS',
    'VOICE_KEY_FIELD',
    'VOICE_KEY_LEGACY_FIELD',
    'annotate_finding',
    'asset_registry_path',
    'classify_image_backend',
    'infer_spectacle_type',
    'lora_gap_message',
    'lora_registry_ready_blocks',
    'motion_control_required',
    'shared_asset_dir',
    'shared_asset_path',
    'special_template_keywords',
    'stage_for_progress_column',
    'episode_png_fingerprint',
    'diff_contracts',
    'diff_storyboard_image_contract',
    'check_asset_handoff',
    'check_identity_handoff',
    'load_thresholds',
    'image_backends',
    'image_backend_adapter',
    'video_backend_adapter',
    'backend_smoke',
    'face_encoder_policy',
    'anchor_consumption_plan',
    'backend_supports_three_plus_frames',
    'video_backend_frame_control',
    'video_backend_max_seconds',
    'is_done',
    'is_progress_satisfied',
    'manifest_path',
    'parse_progress',
    'voice_is_placeholder',
    'voice_meta_path',
    'voiceover_fingerprint',
    'get_setting',
    'is_hybrid_routing',
    'is_native_av',
    'is_video_first',
    'normalize_camera_move',
    'color_temperature_findings',
    'policy_family_for_stage',
    'validate_gate_policy_matrix',
    '_cross_episode_diff',
    '_ce_overview_rel',
    '_ce_prior_episode',
    '_ce_episode_number',
    '_ce_scene_names',
    '_ce_core_scene_names',
    'semc',
    'statec',
    'mmc',
    'sa',
    'vcons',
    'vprint',
    'fingerprint_is_fresh',
    'skill_freshness',
    'BLOCK',
    'WARN',
    'INFO',
    'findings',
    'FALLBACK_OFF_VALUES',
    '_loads_json_from_noisy_stdout',
    'WARN_HI',
    'WARN_MOD_CUT',
    'WARN_MINOR_CUT',
    '_RISK_DEFAULTS',
    '_default_risk_score',
    '_warn_tier',
    '_warn_icon',
    '_default_evidence_family',
    'SPECIAL_SHOT_TEMPLATE_FIELDS',
    'SPECIAL_SHOT_KEYWORDS',
    'MOTION_CONTROL_KIND',
    'MOTION_CONTROL_ROUTE_FIELDS',
    'MOTION_CONTROL_READY_STATUSES',
    'MOTION_CONTROL_READY_INPUT_STATUSES',
    'MOTION_CONTROL_CONTACT_FIELDS',
    'MOTION_CONTROL_CONTACT_SHOT_TYPES',
    'IDENTITY_REFERENCE_FIELDS',
    'REQUIRED_CHARACTER_MAKEUP_REFERENCE_GROUP_FIELDS',
    'REQUIRED_CHARACTER_MAKEUP_ATLAS_VIEWS',
    'CHARACTER_LIBRARY_TIER_CORE',
    'CHARACTER_LIBRARY_TIER_STANDARD',
    'CHARACTER_LIBRARY_TIER_MINIMAL',
    'CHARACTER_LIBRARY_TIER_PARTIAL',
    'CHARACTER_LIBRARY_TIERS',
    'CHARACTER_MAKEUP_BODY_REFERENCE_FIELDS',
    'CHARACTER_MAKEUP_FACE_REFERENCE_FIELDS',
    'READY_CHARACTER_MAKEUP_STATUSES',
    'DERIVED_CHARACTER_MAKEUP_REFERENCE_FIELDS',
    'SAME_SOURCE_MAKEUP_DERIVATION_METHODS',
    'CHARACTER_MAKEUP_DERIVATION_REQUIRED_FIELDS',
    'IDENTITY_FORM_FIELDS',
    'CHARACTER_DNA_FIELDS',
    'WARDROBE_PROFILE_CORE_FIELDS',
    'WARDROBE_PROFILE_STRUCTURE_FIELD_GROUPS',
    'ASSET_BUNDLE_REQUIRED_SECTIONS',
    'IDENTITY_ANGLE_FIELDS',
    'IDENTITY_ADAPTER_SECTIONS',
    'GENERATION_CONTROL_ALLOWED_SUPPORT',
    'GENERATION_CONTROL_USAGE_KEYS',
    'GENERATION_CONTROL_RECORD_KEYS',
    'IDENTITY_READY_STATUSES',
    'IDENTITY_KNOWN_STATUSES',
    'IDENTITY_ALLOWED_IMAGE_MODES',
    'IDENTITY_ALLOWED_VIDEO_MODES',
    'ASSET_REFERENCE_TYPE_PREFIX',
    'ASSET_REFERENCE_REQUIRED_FIELDS',
    'ASSET_PROP_REQUIRED_FIELDS',
    'ASSET_WEAPON_TYPES',
    'ASSET_WEAPON_PROFILE_FIELDS',
    'ASSET_WEAPON_PROFILE_NAMES',
    'WEAPON_LIKE_ASSET_TERMS',
    'SIGNATURE_EQUIPMENT_FIELDS',
    'ACTION_EQUIPMENT_TERMS',
    'ASSET_SCENE_REQUIRED_FIELDS',
    'ASSET_SCENE_RELEASE_FIELD_GROUPS',
    'SCENE_ATLAS_ALT_ANGLES',
    'SCENE_DNA_REQUIRED_FIELDS',
    '_DOF_INTENT_TOKENS',
    'NATIVE_AUDIO_DISCARD',
    'NATIVE_AUDIO_AMBIENCE',
    'NATIVE_AUDIO_KEEP',
    'COMPLIANCE_KIND',
    'COMPLIANCE_READY',
    'COMPLIANCE_DONE',
    'PLATFORM_REVIEW_STATUSES',
    'PRE_BROADCAST_STATUSES',
    'AI_LABEL_STATUSES',
    'STATUS_LIKE_VALUES',
    'OVERSEAS_PLATFORMS',
    'DOMESTIC_REGIONS',
    'gate_family',
    '_HEURISTIC_BLOCK_DEMOTIONS',
    '_CHARTER_LOCKED_DIMS_CACHE',
    '_charter_locked_dims',
    'heuristic_demotion_rollup',
    'add',
    '_DEGRADED_QC_WAIVERS',
    'degraded_qc_mode',
    'degraded_qc_active',
    'degraded_qc_waiver_label',
    'note_degraded_qc_waiver',
    'consistency_waiver_rollup',
    'CONSISTENCY_RULE_REGISTRY',
    '_production_mode_contract_issues',
    'PRODUCTION_CONSISTENCY_VALUES',
    'DEMO_CONSISTENCY_VALUES',
    '_profile_values',
    '_contains_profile_marker',
    '_production_profile_inferred',
    'consistency_release_profile',
    '_settings_values',
    '_project_has_english_subtitles',
    '_project_has_overseas_release_target',
    'exists',
    'load_json',
    'CHARACTER_REF_RE',
    'CHARACTER_ID_RE',
    'ASSET_ID_RE',
    'ENDFRAME_EXEMPT_REASON_MIN_CHARS',
    'ANCHOR_TOKEN_MIN_CHARS',
    '_episode_reference_texts',
    'episode_registry_reference_ids',
    '_STRUCTURED_CHARACTER_ID_RE',
    '_structured_character_ids',
    '_schedule_visible_character_ids',
    '_storyboard_clip_visible_character_ids',
    '_storyboard_character_appearance_evidence',
    'episode_registry_identity_refs',
    '_episode_has_per_shot_frames',
    '_registered_registry_ids',
    'MIDFRAME_SELF_CHECK_KEYS',
    'MIDFRAME_SELF_CHECK_PASS',
    'PROHIBITED_FACE_PATCH_LABEL',
    'PROHIBITED_FACE_PATCH_STRONG_TOKENS',
    'PROHIBITED_FACE_PATCH_OPERATION_TOKENS',
    '_production_events_path',
    '_norm_rel_path',
    '_asset_matches',
    '_load_production_events',
    '_latest_asset_generation_event',
    '_event_generation',
    '_event_meta',
    '_event_cost',
    '_event_asset_rel',
    '_is_prohibited_face_patch_event',
    '_prohibited_face_patch_outputs',
    '_seed_record_value',
    'RECIPE_EVIDENCE_STAGES',
    'RECIPE_REQUIRED_FIELDS',
    '_event_value_any',
    '_event_status_pass',
    '_final_media_exists',
    '_final_media_rels',
    '_recipe_return_stage_for_asset',
    '_recipe_event_missing_fields',
    '_midframe_self_check_value',
    '_check_midframe_generation_self_check',
    'compliance_manifest_path',
    '_listify',
    '_status',
    'PLACEHOLDER_MARKERS',
    '_filled',
    '_looks_like_status_value',
    '_valid_iso_date',
    '_has_embedded_iso_date',
    '_is_internal_distribution',
    '_is_publish_intent',
    'INTERNAL_SKIP_NOTE',
    '_compliance_block',
    '_compliance_warn',
    '_episode_in_scope',
    '_identity_character_ids',
    '_check_compliance_rights',
    '_check_compliance_characters',
    '_check_compliance_voice',
    '_check_platform_targets',
    '_check_regulatory_filing',
    '_ai_labeling_required',
    '_check_ai_labeling',
    'row_for',
    'require_progress',
    '_artifact_exists',
    'progress_fraction_done',
    'evaluate_budget_gate',
    '_episode_planned_minutes',
    '_image_backend_gate_workload',
    '_truthy_setting',
    'backend_smoke_gate_enabled',
    'backend_smoke_max_age_days',
    '_route_video_backends',
    '_video_route_backend_roles',
    '_cap_bool',
    '_cap_number',
    '_cap_value',
    '_route_capability_assertion_gaps',
    'drift_advisory_findings',
    '_run_drift_risk_script',
    'imaged_episodes',
    'drift_report_freshness',
    '_CORE_SCOPE_RE',
    '_image_backend_supports_native_subject',
    '_image_event_provider',
    'LORA_EXCEPTION_SCOPE_KIND',
    'LORA_SIDECAR_REQUIRED_FIELDS',
    'LORA_SIDECAR_QC_REQUIRED',
    'LORA_SIDECHAIN_TOKENS',
    '_lora_exception_scope_path',
    '_validate_lora_exception_scope',
    '_lora_scope_clips',
    '_event_clip_id',
    '_is_lora_sidechain_event',
    '_reference_plan_requirement',
    'REFERENCE_PLAN_APPLICATION_KIND',
    '_reference_plan_application_path',
    '_reference_plan_prompt_path',
    '_safe_sha256',
    '_reference_plan_application_status',
    'DIRECTOR_CAMERA_PLAN_APPLICATION_KIND',
    '_director_plan_application_path',
    '_director_plan_application_status',
    'storyboard_path',
    'load_storyboard',
    '_route_allows_no_firstframe',
    'STYLEID_CLOSEUP_MARKERS',
    'STYLEID_CLOSEUP_RATIO',
    '_styleid_release_signoff_path',
    '_styleid_structured_signoff_ok',
    '_storyboard_closeup_character_ratio',
    '_styleid_release_gate_required',
    '_TONE_SPLIT_RE',
    'PROP_ID_ANY_RE',
    'POSSESSION_WORDS',
    'POSSESSION_TRANSFER_WORDS',
    'CORE_POSSESSION_ASSET_WORDS',
    '_tone_base',
    '_earliest_storyboard_ep',
    '_possession_ledger_path_candidates',
    '_possession_ledger_exists',
    '_possession_mentions_core_asset',
    'LONG_RUNNING_EP_THRESHOLD',
    'long_running_weak_backend_advice',
    '_long_running_subjectless_severity',
    'IDENTITY_LOCK_READY_STATUSES',
    'LOCAL_LORA_IMAGE_BACKENDS',
    '_normalize_lora_backend',
    '_lora_usable_on_image_backend',
    '_image_form_has_identity_lock',
    'core_forms_without_image_identity_lock',
    'identity_lock_gap_notes',
    'IMAGE_IDENTITY_LOCK_RECOMMENDATION',
    '_clip_blob',
    '_first_template_keyword_hit',
    '_field_is_missing',
    '_is_restricted_partial_form',
    '_gate_make_clip_id',
    'identity_adapter_matrix_path',
    '_has_identity_handle',
    '_validate_identity_adapter_map',
    '_lora_gap_loc_suffix',
    '_validate_identity_lora',
    '_validate_generation_control',
    '_validate_character_dna',
    '_performance_signature_present',
    '_signature_equipment_refs',
    '_core_action_character_needs_equipment',
    '_validate_signature_equipment',
    '_profile_has_any',
    '_validate_wardrobe_profile',
    '_validate_character_asset_bundle',
    '_identity_reference_item_path',
    '_identity_reference_item_ready',
    '_identity_reference_item_derivation',
    '_file_sha256',
    '_validate_same_source_makeup_derivation',
    '_identity_expression_path',
    '_identity_reference_list_paths',
    '_identity_ready_reference_list_paths',
    '_normalize_character_library_tier',
    '_required_character_makeup_views',
    '_required_character_reference_group_fields',
    '_validate_reference_atlas',
    '_identity_reference_exists',
    '_identity_reference_matches_asset_key',
    '_COSTUME_VARIANT_RE',
    '_COSTUME_NON_FACE',
    '_costume_stem',
    '_validate_scene_dna',
    '_flatten_asset_terms',
    '_asset_must_not_have_terms',
    '_validate_scene_atlas',
    '_is_core_location_asset',
    '_asset_has_any',
    '_weapon_profile',
    '_is_weapon_like_asset',
    '_asset_owner_present',
    '_validate_weapon_profile',
    '_SHOT_SCALE_MAP',
    '_OTS_RE',
    'SHOT_SCALE_MIN_RUN',
    'shot_scale_class',
    'monotonous_scale_runs',
    '_SHOT_BLOCK_SPLIT_RE',
    '_PHYSICAL_SCALE_TOKENS',
    '_registry_character_names',
    '_registry_relative_scales',
    '_has_any',
    '_headline',
    '_clip_number_from_section',
    '_has_field',
    '_has_line_field',
    '_section_requires_motion_control',
    '_route_requires_contact_fields',
    '_section_shot_type',
    '_action_choreography_required_fields',
    '_missing_contract_fields',
    'native_audio_policy',
    'native_audio_policy_mode',
    '_section_native_audio_opt_in',
    '_native_audio_contract_ok',
    'NATIVE_AV_PHYSICAL_FIELDS',
    'NATIVE_AV_PHYSICS_KIND',
    'NATIVE_AV_SUBTITLE_ALIGNMENT_KIND',
    'NATIVE_VOICE_IDENTITY_SEGMENTS_KIND',
    'is_native_av_production',
    'native_av_physics_required',
    '_native_audio_policy_line',
    'native_av_physics_sidecar_path',
    'native_av_subtitle_alignment_path',
    'native_voice_identity_path',
    'native_voice_print_report_path',
    '_distribution_intent',
    '_truthy',
    '_mapping',
    '_clip_audio_intent',
    '_clip_compose_policy',
    '_sidecar_clip_id',
    '_native_av_physics_clip_errors',
    '_route_clip_number',
    '_video_route_policy_map',
    '_storyboard_frame_requirements',
    'MODEL_ROUTE_BASELINE_HIGH_RISK_SHOT_TYPES',
    'MODEL_ROUTE_BASELINE_HIGH_RISK_FLAGS',
    'MODEL_ROUTE_SPEECH_SHOT_TYPES',
    '_route_is_speech_like',
    '_route_needs_mouth_visible_audit',
    '_route_needs_model_baseline',
    '_identity_route_requires_character_refs',
    '_route_clip_character_refs',
    '_baseline_override_accepted',
    '_as_string_list',
    '_baseline_override_payload',
    '_override_expiry_ok',
    '_baseline_override_errors',
    '_route_is_high_action',
    '_NON_NATIVE_BINDINGS',
    '_CORE_SCOPES',
    '_motion_control_required_for_route',
    '_resolve_under_root',
    '_uri_like',
    '_uri_scheme',
    '_sequence_pattern_to_glob',
    '_verified_remote_control_input',
    '_control_asset_exists',
    '_input_ready',
    '_reference_block',
    '_section_has_character_refs',
    '_character_names_in_refs',
    '_needs_closeup_identity_lock',
    '_has_closeup_identity_lock',
    '_has_i2i_tail_continuity_lock',
    'I2I_DERIVATION_MARKERS',
    '_has_i2i_derivation',
    'CODEX_FACE_REFERENCE_MARKERS',
    'CODEX_STRONG_EXPRESSION_MARKERS',
    'CODEX_DARK_VFX_FACE_RISK_MARKERS',
    'CODEX_FACE_VISIBILITY_GUARDS',
    'CODEX_CONDITIONAL_SPLIT_MARKERS',
    'GENERIC_REFERENCE_INDEX_MARKERS',
    '_codex_needs_face_reference',
    '_codex_has_face_reference',
    '_codex_dark_vfx_face_risk',
    '_codex_has_face_visibility_guard',
    '_has_codex_split_composite_strategy',
    '_has_generic_reference_index_lock',
    '_has_native_multi_subject_strategy',
    '_has_multi_subject_identity_slots',
    '_has_character_id_binding',
    '_has_character_aesthetic_baseline',
    '_multi_char_binding_ambiguity',
    '_has_asset_id_binding',
    '_needs_scene_asset_binding',
    '_needs_prop_asset_binding',
    '_has_standard_character_turnaround',
    '_is_restricted_partial_prompt_section',
    '_has_positive_prompt_heading',
    '_uses_halfbody_outfit_ref',
    '_has_halfbody_crop_rule',
    '_has_prop_structure_rule',
    '_needs_prop_structure_gate',
    '_evolution_derived_forms',
    '_section_is_derived_form',
    '_declares_evolution_derivation',
    '_FINALIZE_CHAR_RE',
    '_FINALIZE_ASSET_RE',
    '_finalize_evidence',
    '_sha256_file',
    '_form_anchor_relpath',
    '_CLOSEUP_MARKERS',
    '_clip_is_closeup',
    '_episode_big_expression_closeup_clips',
    '_clip_character_ids',
    '_VID_CLIP_HEAD_RE',
    '_VID_FIRST_FRAME_RE',
    '_VID_END_FRAME_RE',
    '_VID_MID_FRAME_RE',
    'ffprobe_json',
    'duration',
    'has_audio',
    'clip_files',
    'stripped_audio_artifacts',
    'voice_track_exists',
    'voice_manifest_rows',
    'voiceover_role',
    'voice_track_scope',
    'native_av_subtitle_alignment_required',
    '_native_av_subtitle_status_ok',
    '_native_av_subtitle_word_level',
    '_native_av_subtitle_errors',
    'native_voice_identity_required',
    '_native_voice_segments_errors',
    '_clip_label',
    '_artifact_refs',
    '_continuity_extra',
    '_add_continuity_rows',
    'TRANSLATION_GLOSSARY_CATEGORIES',
    'TRANSLATION_CATEGORY_ALIASES',
    'translation_glossary_path',
    '_translation_glossary_terms',
    '_translation_term_has_pair',
    '_translation_category_covered',
    'STRICT_ADVISORY_DIMENSIONS',
    'REQUIRED_VIDEO_EVIDENCE_DIMENSIONS',
    'KEY_SCENE_MARKERS',
    'CLOSEUP_MARKERS',
    '_consistency_signoff_path',
    '_row_is_key_scene',
    '_row_is_dialogue_closeup',
    '_consistency_finding_hash',
    '_signoff_expiry_ok',
    '_advisory_row_signed_off',
    '_strict_advisory_should_block',
    'INTENTIONAL_DISCONTINUITY_ELIGIBLE_DIMENSIONS',
    '_intentional_discontinuity_module',
    '_sanitized_intentional_manifest',
    '_native_block_intentional_signoff',
    '_canonical_fingerprint_fresh',
    '_check_fidelity_gate_active',
    '_autorun_scene_verifier',
    'correlate_findings',
    '_SEV_RANK',
    'consolidate_findings_by_shot',
    'SERIES_RETENTION_DIM',
    '_series_ep_int',
    'PILOT_ARC_CONTRACT_REL',
    'PILOT_ARC_REQUIRED_FIELDS',
    'evidence_grade_findings',
    '_finding_sort_key',
]
