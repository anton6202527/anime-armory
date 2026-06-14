#!/usr/bin/env python3
"""Shared schemas and metadata for the n2d pipeline."""

from __future__ import annotations
from typing import Dict, List, Any, Tuple
try:
    from n2d_const import *
except ImportError:
    from .n2d_const import *

# ── n2d 边界型机器产物注册表 ──────────────────────────────────────────────
BOUNDARY_PRODUCT_KINDS = {
    MANIFEST_KIND: {
        "owner": "n2d (contract)",
        "path": "脚本/{ep}/manifest.json",
        "layer": "contract",
        "boundary": "episode_summary",
    },
    IDENTITY_REGISTRY_KIND: {
        "owner": "n2d-identity",
        "path": f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
        "layer": "shared_asset",
        "boundary": "identity_definition",
    },
    ASSET_REFERENCE_REGISTRY_KIND: {
        "owner": "n2d-asset-market",
        "path": f"出图/{SHARED_ASSET_DIR}/asset_registry.json",
        "layer": "shared_asset",
        "boundary": "asset_definition",
    },
    IDENTITY_ADAPTER_MATRIX_KIND: {
        "owner": "n2d-identity",
        "path": f"{PRODUCTION_DIR}/identity_adapter_matrix.json",
        "layer": "production_data",
        "boundary": "adapter_mapping",
    },
    COMPLIANCE_MANIFEST_KIND: {
        "owner": "n2d-compliance",
        "path": "合规/compliance_manifest.json",
        "layer": "governance",
        "boundary": "rights_clearance",
    },
    VIDEO_MODEL_ROUTES_KIND: {
        "owner": "n2d-model-router",
        "path": f"{PRODUCTION_DIR}/video_model_routes.json",
        "layer": "production_data",
        "boundary": "routing_decisions",
    },
    MOTION_CONTROL_MANIFEST_KIND: {
        "owner": "n2d-video",
        "path": f"{PRODUCTION_DIR}/motion_control_manifest.json",
        "layer": "production_data",
        "boundary": "control_readiness",
    },
    CONTRACT_INHERITANCE_KIND: {
        "owner": "n2d-video",
        "path": f"{PRODUCTION_DIR}/contract_inheritance_{{ep}}.json",
        "layer": "production_data",
        "boundary": "visual_contract_handoff",
    },
    VISUAL_STATE_LEDGER_KIND: {
        "owner": "n2d-image",
        "path": f"出图/{SHARED_ASSET_DIR}/visual_state_ledger.json",
        "layer": "shared_asset",
        # 边界须点明与 identity_registry 的分工：本账本记【状态演进】(受伤/战损/获法宝随集累积)，
        # identity_registry 记【身份锁定】(角色是谁)，互补不重叠（见 test_visual_state_manager）。
        "boundary": "state_continuity_vs_identity_registry",
    },
    ASSET_RERUN_PLAN_KIND: {
        "owner": "n2d-image",
        "path": f"{PRODUCTION_DIR}/asset_rerun_plan_{{ep}}.json",
        "layer": "production_data",
        "boundary": "rerun_plan",
    },
    BATCH_QUEUE_KIND: {
        "owner": "n2d-batch",
        "path": f"{PRODUCTION_DIR}/batch_queue.json",
        "layer": "production_data",
        "boundary": "work_queue",
    },
    EPISODE_REVIEW_SCORE_KIND: {
        "owner": "n2d-score",
        "path": f"{PRODUCTION_DIR}/score_{{ep}}.json",
        "layer": "production_data",
        "boundary": "review_score",
    },
    SCORE_VISUAL_CHECKS_KIND: {
        "owner": "n2d-score",
        "path": f"{PRODUCTION_DIR}/score_inputs/{{ep}}_visual.json",
        "layer": "production_data",
        "boundary": "visual_score_inputs",
    },
    REVIEW_UI_KIND: {
        "owner": "n2d-review-ui",
        "path": f"{PRODUCTION_DIR}/review_ui_{{ep}}.json",
        "layer": "production_data",
        "boundary": "human_review_ui",
    },
    PLATFORM_FEEDBACK_KIND: {
        "owner": "n2d-feedback",
        "path": f"{PRODUCTION_DIR}/platform_feedback.json",
        "layer": "production_data",
        "boundary": "feedback_metrics",
    },
    GENRE_PERFORMANCE_RECORD_KIND: {
        "owner": "n2d-feedback",
        "path": f"{PRODUCTION_DIR}/genre_performance.jsonl",
        "layer": "production_data",
        "boundary": "market_signal",
    },
    DIFFERENTIATION_CANDIDATES_KIND: {
        "owner": "n2d-feedback",
        "path": f"{PRODUCTION_DIR}/differentiation_candidates.json",
        "layer": "production_data",
        "boundary": "market_positioning",
    },
    LORA_CARD_KIND: {
        "owner": "n2d-lora",
        "path": "设定库/lora/{character}/{form}/lora_card.json",
        "layer": "training_asset",
        "boundary": "lora_card",
    },
    LORA_DATASET_MANIFEST_KIND: {
        "owner": "n2d-lora",
        "path": "设定库/lora/{character}/{form}/dataset_manifest.json",
        "layer": "training_asset",
        "boundary": "lora_dataset",
    },
    LORA_TRAIN_JOB_KIND: {
        "owner": "n2d-lora",
        "path": "设定库/lora/{character}/{form}/train_job.json",
        "layer": "training_asset",
        "boundary": "lora_train_job",
    },
    ASSET_PACK_KIND: {
        "owner": "n2d-asset-market",
        "path": "资产库/{slug}/asset_pack.json",
        "layer": "asset_market",
        "boundary": "asset_pack",
    },
}

PRODUCT_KINDS = BOUNDARY_PRODUCT_KINDS

PROGRESS_COLUMNS = (
    "集", "字数", "raw", "剧本改编", "bgm", "封面", "配音", "分镜设计",
    "素材清单", "字幕中", "字幕英", "出图prompt", "出图", "视频prompt", "视频", "成片",
)

IDENTITY_FORK_HISTORY_FIELD = "fork_history"
IDENTITY_FORK_HISTORY_ENTRY_FIELDS = (
    "from_pack",
    "from_slug",
    "from_character_id",
    "forked_at",
    "reason",
)

# ── 一致性维度定义 ────────────────────────────────────────────────────────────
CONSISTENCY_DIMENSIONS: Dict[str, Dict[str, Any]] = {
    "face": {
        "label": "人脸一致性",
        "keywords": ("脸", "不像", "漂移", "face"),
        "return_to_stage": "image",
    },
    "voice": {
        "label": "音色一致性",
        "keywords": ("声音", "音色", "配音", "voice"),
        "return_to_stage": "voice",
    },
    "outfit": {
        "label": "服装一致性",
        "keywords": ("衣服", "服装", "饰品", "outfit"),
        "return_to_stage": "image",
    },
    "scene": {
        "label": "场景一致性",
        "keywords": ("场景", "环境", "背景", "scene"),
        "return_to_stage": "image",
    },
    "motion": {
        "label": "动作连贯性",
        "keywords": ("动作", "连贯", "穿模", "motion"),
        "return_to_stage": "video",
    },
    "contract_inheritance": {
        "label": "契约继承",
        "keywords": ("契约", "继承", "光位", "轴线", "contract"),
        "return_to_stage": "video_prompt",
        "scope": "修正出视频总览/逐 Clip prompt，使其继承出图侧视觉契约。",
    },
}

# ── STAGE_GRAPH ──────────────────────────────────────────────────────────────
STAGE_GRAPH: List[Dict[str, Any]] = [
    {
        "key": "source",
        "label": "源文本落档",
        "owner": "n2d-script",
        "progress_columns": ("raw",),
        "command": "n2d-script {root}",
        "routes": False,
        "gate_stage": None,
        "requires": (),
        "outputs": ("脚本/{ep}/raw.txt",),
        "return_to_stage": "source",
    },
    {
        "key": "script_stage1",
        "label": "阶段1·剧本改编",
        "owner": "n2d-script",
        "progress_columns": ("剧本改编", "bgm", "封面"),
        "command": "n2d-script {root} {ep}",
        "routes": True,
        "gate_stage": None,
        "requires": ("raw",),
        "outputs": (
            "脚本/{ep}/voiceover.txt",
            "脚本/{ep}/bgm.txt",
            "脚本/{ep}/封面.md",
            "设定库/global_style.md",
            "设定库/characters/_角色总表.md",
            "设定库/locations/_场景总表.md",
        ),
        "return_to_stage": "script_stage1",
    },
    {
        "key": "voice",
        "label": "角色配音",
        "owner": "n2d-voice",
        "progress_columns": ("配音",),
        "command": "n2d-voice {root} {ep}",
        "routes": True,
        "gate_stage": None,
        "requires": ("剧本改编",),
        "outputs": (
            "合成/{ep}/配音/voice_zh.wav",
            "合成/{ep}/配音/时长清单.json",
            "合成/{ep}/配音/_占位说明.md",
        ),
        "output_contract": {
            "any_of": (
                {
                    "label": "真实配音",
                    "all_of": (
                        "合成/{ep}/配音/voice_zh.wav",
                        "合成/{ep}/配音/时长清单.json",
                    ),
                },
                {
                    "label": "视频先行占位时长",
                    "all_of": (
                        "合成/{ep}/配音/_占位说明.md",
                        "合成/{ep}/配音/时长清单.json",
                    ),
                },
            ),
        },
        "return_to_stage": "voice",
    },
    {
        "key": "script_stage2",
        "label": "阶段2·分镜设计",
        "owner": "n2d-script",
        "progress_columns": ("分镜设计", "素材清单", "字幕中", "字幕英"),
        "command": "n2d-script {root} {ep}  (配音后定稿)",
        "routes": True,
        "gate_stage": None,
        "requires": ("配音",),
        "outputs": (
            "脚本/{ep}/分镜剧本.md",
            "脚本/{ep}/故事板.md",
            "脚本/{ep}/storyboard.json",
            "脚本/{ep}/素材清单.md",
            "脚本/{ep}/字幕_中文.srt",
            "脚本/{ep}/字幕_英文.srt",
            "脚本/{ep}/镜头时长.json",
        ),
        "return_to_stage": "script_stage2",
    },
    {
        "key": "image_prompt",
        "label": "出图prompt",
        "owner": "n2d-image",
        "progress_columns": ("出图prompt",),
        "command": "n2d-image {root} {ep}",
        "routes": True,
        "gate_stage": "image_preflight",
        "requires": ("配音", "分镜设计"),
        "outputs": (
            f"出图/{SHARED_ASSET_DIR}/prompt/00_索引.md",
            "出图/{ep}/prompt/00_总览.md",
            "出图/{ep}/prompt/01_分镜出图.md",
        ),
        "return_to_stage": "image_prompt",
    },
    {
        "key": "image",
        "label": "出图",
        "owner": "n2d-image",
        "progress_columns": ("出图",),
        "command": "n2d-image {root} {ep}",
        "routes": True,
        "gate_stage": "image",
        "requires": ("出图prompt",),
        "outputs": (
            f"出图/{SHARED_ASSET_DIR}/图片",
            "出图/{ep}/图片",
        ),
        "return_to_stage": "image",
    },
    {
        "key": "video_prompt",
        "label": "视频prompt",
        "owner": "n2d-video",
        "progress_columns": ("视频prompt",),
        "command": "n2d-video {root} {ep}",
        "routes": True,
        "gate_stage": "video_preflight",
        "requires": ("出图",),
        "outputs": (
            "出视频/{ep}/prompt/00_总览.md",
            "出视频/{ep}/prompt/01_clips.md",
        ),
        "return_to_stage": "video_prompt",
    },
    {
        "key": "video",
        "label": "图生视频",
        "owner": "n2d-video",
        "progress_columns": ("视频",),
        "command": "n2d-video {root} {ep}",
        "routes": True,
        "gate_stage": "video",
        "requires": ("视频prompt", "出图"),
        "outputs": ("出视频/{ep}/视频",),
        "return_to_stage": "video",
    },
    {
        "key": "compose",
        "label": "合成成片",
        "owner": "n2d-compose",
        "progress_columns": ("成片",),
        "command": "n2d-compose {root} {ep}",
        "routes": True,
        "gate_stage": "compose",
        "requires": ("视频",),
        "outputs": (
            "合成/{ep}/成片_{ep}_zh.mp4",
            "合成/{ep}/成片_{ep}_bilingual.mp4",
        ),
        "output_contract": {
            "any_of": (
                {"label": "中文字幕成片", "all_of": ("合成/{ep}/成片_{ep}_zh.mp4",)},
                {"label": "双语成片", "all_of": ("合成/{ep}/成片_{ep}_bilingual.mp4",)},
            ),
        },
        "return_to_stage": "compose",
    },
    {
        "key": "review",
        "label": "审查验收",
        "owner": "n2d-review",
        "progress_columns": (),
        "command": "n2d-review {root} {ep}",
        "routes": False,
        "gate_stage": "review",
        "requires": ("成片",),
        "outputs": (
            "合成/{ep}/成片_{ep}_zh.mp4",
            "合成/{ep}/成片_{ep}_bilingual.mp4",
        ),
        "output_contract": {
            "any_of": (
                {"label": "中文字幕成片", "all_of": ("合成/{ep}/成片_{ep}_zh.mp4",)},
                {"label": "双语成片", "all_of": ("合成/{ep}/成片_{ep}_bilingual.mp4",)},
            ),
        },
        "return_to_stage": "review",
    },
]

GATE_RECOVERY: Dict[str, Any] = {
    "image_preflight": {
        "return_to_stage": "image_prompt",
        "rerun_scope": "先修合规包、配音/分镜、storyboard visual/style_contract、出图 prompt、共享定妆与资产注册层，再重跑 image_preflight；未过不得调用生图后端。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            f"出图/{SHARED_ASSET_DIR}/asset_registry.json",
            f"出图/{SHARED_ASSET_DIR}/prompt",
            "出图/{ep}/prompt",
        ),
    },
    "image": {
        "return_to_stage": "image_prompt",
        "rerun_scope": "先修 storyboard.json visual_contract/style_contract、出图 prompt、共享定妆，再重跑 image gate；未过 gate 不生图。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            f"出图/{SHARED_ASSET_DIR}/prompt",
            "出图/{ep}/prompt",
            "出图/{ep}/图片",
        ),
    },
    "video_preflight": {
        "return_to_stage": "video_prompt",
        "rerun_scope": "先修身份矩阵/路由、首尾帧、视频 prompt、导演一致性契约、基础视觉风格契约或缺失 PNG，再重跑 video_preflight；未过不得调用出视频后端。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            f"出图/{SHARED_ASSET_DIR}/asset_registry.json",
            f"{PRODUCTION_DIR}/identity_adapter_matrix.json",
            "出图/{ep}/图片",
            "出视频/{ep}/prompt",
            "出视频/{ep}/control",
        ),
    },
    "video": {
        "return_to_stage": "video_prompt",
        "rerun_scope": "先修尾帧、视频 prompt、导演一致性契约、基础视觉风格契约或缺失 PNG，再重跑 video gate；未过 gate 不出视频。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            "出图/{ep}/图片",
            "出视频/{ep}/prompt",
            "出视频/{ep}/视频",
        ),
    },
    "compose": {
        "return_to_stage": "compose",
        "rerun_scope": "先补视频/字幕/真配音，再重跑 compose gate；通过后再合成。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            "出视频/{ep}/视频",
            "合成/{ep}/配音",
            "脚本/{ep}/字幕_中文.srt",
            "合成/{ep}",
        ),
    },
    "review": {
        "return_to_stage": "review",
        "rerun_scope": "按 finding 回退到最早受影响阶段。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            "出视频/{ep}/视频",
            "合成/{ep}",
        ),
    },
}

GATE_STAGES = tuple(GATE_RECOVERY.keys())

IDENTITY_IMAGE_ADAPTERS: Dict[str, Dict[str, Any]] = {
    "codex": {
        "allowed_modes": ("reference_group",),
        "default_mode": "reference_group",
        "default_status": "fallback_reference_group",
    },
    "openai": {
        "allowed_modes": ("reference_group",),
        "default_mode": "reference_group",
        "default_status": "fallback_reference_group",
    },
    "dreamina": {
        "allowed_modes": ("reference_group",),
        "default_mode": "reference_group",
        "default_status": "fallback_reference_group",
    },
    "seedream": {
        "allowed_modes": ("universal_reference", "reference_group"),
        "default_mode": "universal_reference",
        "default_status": "unregistered",
    },
    "kling": {
        "allowed_modes": ("character_id", "subject_library", "custom_model", "element_library", "reference_group"),
        "default_mode": "character_id",
        "default_status": "unregistered",
    },
    "sora": {
        "allowed_modes": ("character_cameo", "reference_group"),
        "default_mode": "character_cameo",
        "default_status": "unregistered",
    },
}

IDENTITY_VIDEO_ADAPTERS: Dict[str, Dict[str, Any]] = {
    "dreamina": {
        "allowed_modes": ("first_last_frame", "reference_group"),
        "default_mode": "first_last_frame",
        "default_status": "fallback_reference_group",
    },
    "kling": {
        "allowed_modes": ("character_id", "reference_group"),
        "default_mode": "character_id",
        "default_status": "unregistered",
    },
    "seedance": {
        "allowed_modes": ("face_lock", "reference_group"),
        "default_mode": "face_lock",
        "default_status": "unregistered",
    },
    "veo": {
        "allowed_modes": ("reference_controls", "reference_group"),
        "default_mode": "reference_controls",
        "default_status": "unregistered",
    },
    "sora": {
        "allowed_modes": ("character_cameo", "reference_media", "reference_group"),
        "default_mode": "character_cameo",
        "default_status": "unregistered",
    },
}

MOTION_CONTROL_REQUIRED_SHOT_TYPES = (
    "fight_exchange",
    "chase",
    "flight",
    "hug_or_pull",
    "intimate_interaction",
    "multi_character_same_frame",
    "ensemble_blocking",
    "multi_person_blocking",
)
MOTION_CONTROL_RISK_FLAGS = (
    "physical_contact",
    "complex_blocking",
    "multi_character_overlap",
    "high_speed_motion",
    "extreme_camera",
    "identity_high_risk",
)

# ── 生图后端治理 ─────────────────────────────────────────────────────────────
# 采集日期：2026-06-14  来源：n2d-image/SKILL.md 放行清单 + 各后端官方文档
APPROVED_IMAGE_BACKENDS: Dict[str, Dict[str, Any]] = {
    "codex": {
        "name": "Codex",
        "label": "Codex",
        "canonical": "codex",
        "multi_reference": True,
        "native_subject": False,
        "tier": "tier-1",
    },
    "dreamina_official": {
        "name": "Dreamina/即梦官方 CLI",
        "label": "Dreamina/即梦官方 CLI",
        "canonical": "dreamina",
        "multi_reference": True,
        "native_subject": True,
        "tier": "tier-1",
    },
    "seedream": {
        "name": "Seedream",
        "label": "Seedream",
        "canonical": "seedream",
        "multi_reference": True,
        "native_subject": True,
        "tier": "tier-1",
    },
    "kling_subject": {
        "name": "可灵主体库",
        "label": "可灵主体库",
        "canonical": "kling",
        "multi_reference": True,
        "native_subject": True,
        "tier": "tier-2",
    },
    "nano_banana": {
        "name": "Nano Banana",
        "label": "Nano Banana",
        "canonical": "nano_banana",
        "multi_reference": True,
        "native_subject": False,
        "tier": "tier-2",
    },
    "sora_cameo": {
        "name": "Sora Cameo",
        "label": "Sora Cameo",
        "canonical": "sora",
        "multi_reference": True,
        "native_subject": True,
        "tier": "tier-2",
    },
}

IMAGE_BACKEND_ALIASES = {
    "即梦": "dreamina_official",
    "dreamina": "dreamina_official",
    "codex": "codex",
    "seedream": "seedream",
    "可灵": "kling_subject",
    "kling": "kling_subject",
    "nano banana": "nano_banana",
    "sora": "sora_cameo",
}

FORBIDDEN_IMAGE_BACKEND_KEYWORDS = ("同视频ai", "同视频AI", "第三方", "逆向", "web自动化", "web 自动化")

# ── 横切 readiness 注册表 ───────────────────────────────────────────────
READINESS_TRACKED_SKILLS: List[Dict[str, Any]] = [
    {
        "key": "compliance",
        "label": "合规治理",
        "skill": "n2d-compliance",
        "artifact": "合规/compliance_manifest.json",
        "required_before": ("image", "video", "compose"),
    },
    {
        "key": "identity",
        "label": "身份一致性",
        "skill": "n2d-identity",
        "artifact": f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
        "required_before": ("image", "video"),
    },
    {
        "key": "motion-control",
        "label": "Motion Control",
        "skill": "n2d-video",
        "artifact": f"{PRODUCTION_DIR}/motion_control_manifest.json",
        "required_before": ("video",),
    },
]

CROSS_CUTTING_TOOLS: List[Dict[str, Any]] = [
    {"key": "update", "label": "重制/更新", "skill": "n2d-update", "artifact": f"{PRODUCTION_DIR}/skill_update_plan_*.json"},
    {"key": "batch", "label": "批量调度", "skill": "n2d-batch", "artifact": f"{PRODUCTION_DIR}/batch_queue.json"},
    {"key": "score", "label": "评分审计", "skill": "n2d-score", "artifact": f"{PRODUCTION_DIR}/score_*.json"},
    {"key": "dashboard", "label": "生产看板", "skill": "n2d-dashboard", "artifact": f"{PRODUCTION_DIR}/dashboard.json"},
    {"key": "feedback", "label": "返工反馈", "skill": "n2d-feedback", "artifact": f"{PRODUCTION_DIR}/platform_feedback.json"},
]

CONTINUITY_FIELDS = (
    "start_state",
    "action",
    "end_state",
    "constraints",
    "negative",
    "transition",
    "need_endframe",
)

COSTLY_HINTS = {
    "配音": "声音克隆需肖像/音色授权（合规闸门）",
    "出图": "会真出图·消耗额度 → 开跑前确认生图后端 + 重抽预算档位",
    "视频": "会真出视频·消耗额度 → 开跑前确认生视频后端",
    "成片": "合成成片（混音+烧字幕），相对便宜但耗时",
}
