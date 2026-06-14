#!/usr/bin/env python3
"""Shared constants for the n2d pipeline."""

from __future__ import annotations

# ── identity_registry 共享字段 ──────────────────────────────────────────────
# reference_group 的标准参考视图键
IDENTITY_REFERENCE_KEYS = ("front", "side", "back", "outfit", "turnaround")

# identity_adapter 是否携带"已注册句柄"的字段（任一非空即视为已登记）
IDENTITY_HANDLE_FIELDS = ("id", "handle", "reference", "model_path")

# identity_adapters.<backend>.status 的标准状态集合
IDENTITY_ADAPTER_KNOWN_STATUSES = (
    "unregistered", "fallback_reference_group", "registered", "pending", "training",
    "ready", "error", "deprecated", "unsupported", "not_needed",
)
IDENTITY_ADAPTER_READY_STATUSES = ("registered", "ready")
IDENTITY_ADAPTER_FALLBACK_STATUSES = ("unregistered", "fallback_reference_group", "fallback", "reference_group")
IDENTITY_ADAPTER_PASSIVE_STATUSES = ("unsupported", "not_needed")
IDENTITY_ADAPTER_IN_PROGRESS_STATUSES = ("pending", "training")

# ── compliance / gate 共享状态集合 ────────────────────────────────────────────
COMPLIANCE_ALLOWED_RIGHTS = ("original", "public_domain", "licensed", "stock_licensed", "user_declared", "not_applicable", "unknown", "")
COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED = ("licensed", "stock_licensed", "user_declared")
COMPLIANCE_APPROVED_CHARACTER = ("actor_authorized", "self_authorized", "licensed_likeness", "ai_generated_original", "synthetic_character", "not_applicable")
COMPLIANCE_BLOCKED_CHARACTER = ("unauthorized", "disputed")
COMPLIANCE_SAFE_VOICE = ("authorized_clone", "stock_voice", "human_recording", "synthetic_voice", "not_applicable")
COMPLIANCE_READY_STATUSES = ("ready", "done", "not_applicable")
COMPLIANCE_DONE_STATUSES = ("ready", "done", "approved", "not_applicable")
COMPLIANCE_PLATFORM_REVIEW_STATUSES = ("ready", "done", "not_applicable")
COMPLIANCE_PRE_BROADCAST_STATUSES = ("pending", "ready", "filed", "approved", "not_applicable")
COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS = ("internal_only", "demo", "test")
COMPLIANCE_PLACEHOLDER_MARKERS = ("todo", "待补", "待办", "xxx", "xxx", "...", "n/a?")
COMPLIANCE_OVERSEAS_PLATFORMS = ("tiktok", "youtube", "reelshort", "instagram", "facebook")
COMPLIANCE_DOMESTIC_REGIONS = ("cn", "china", "mainland", "中国", "中国大陆", "内地")
COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS = ("platform_review", "localization", "regulatory_filing")
COMPLIANCE_STATUS_LIKE_VALUES = (
    "pending", "ready", "done", "not_applicable", "filed", "approved",
    "blocked", "missing", "unknown", "todo",
)

# ── 重抽原因分类 ────────────────────────────────────────────────────────────
REDRAW_REASON_ENUM = ("identity_drift", "composition", "action_quality", "glitch", "prompt_adjustment", "other")
REDRAW_REASON_CATEGORIES = {
    "face": "脸漂/身份",
    "outfit": "服装/配色",
    "scene": "场景/光位",
    "style": "画风",
    "prop": "道具/特效",
    "reference_crop": "参考图裁切",
    "prompt_conflict": "prompt 冲突",
    "temporal": "时序/接缝",
    "identity_drift": "脸漂/身份",
    "composition": "构图/景别",
    "action_quality": "动作质量",
    "glitch": "画质瑕疵",
    "prompt_adjustment": "prompt 调整",
    "other": "其他",
}
REDRAW_REASON_KEYWORDS = (
    ("identity_drift", ("崩脸", "不像", "脸飘", "衣服错", "人不对", "身份", "identity", "face")),
    ("composition", ("构图", "景别", "比例", "位置", "遮挡", "composition", "framing")),
    ("action_quality", ("动作", "僵硬", "穿模", "物理", "崩坏", "action", "motion")),
    ("glitch", ("闪烁", "噪点", "画质", "坏帧", "glitch", "artifact")),
    ("prompt_adjustment", ("微调", "加词", "减词", "权重", "prompt")),
)

# ── 音色一致性契约 ──────────────────────────────────────────────────────────
VOICE_KEY_FIELD = "voice_key"
VOICE_KEY_LEGACY_FIELD = "音色键"
VOICE_KEY_PLACEHOLDER_SUFFIX = "_placeholder"

# ── 制作模式 ──────────────────────────────────────────────────────────────
PRODUCTION_MODE_DEFAULT = "配音先行"

# ── 视觉风格 ──────────────────────────────────────────────────────────────
STYLE_CONTRACT_FIELDS = ("风格名", "视觉基调", "镜头与构图", "光色策略", "运动边界", "风格禁忌")
CINEMATIC_CONTRACT_FIELDS = ("摄影基调", "镜头焦段", "光源动机", "色彩策略", "运镜边界", "真实感禁忌")
VISUAL_CONTRACT_FIELDS = ("色调基线", "场景光位锚", "场景轴线视线", "角色状态演进", "景别阶梯")

# ── 镜头类型 ──────────────────────────────────────────────────────────────
SHOT_TYPE_KEYWORDS = (
    ("fight_exchange", ("打斗", "搏斗", "交手", "格挡", "出拳", "挥剑", "命中", "受击", "撞击", "掌风", "刀光", "fight", "combat", "hit")),
    ("chase", ("追逐", "追赶", "追杀", "奔逃", "逃跑", "追上", "紧追", "chase", "running away")),
    ("flight", ("御剑", "飞行", "凌空", "腾空", "掠空", "掠过云", "飞掠", "坠落", "飞檐", "云海穿行", "flight", "flying")),
    ("dialogue_shot_reverse", ("对话反打", "正反打", "反打", "过肩", "对视", "视线对位", "台词", "dialogue", "shot reverse", "ots", "eyeline")),
    ("dialogue_closeup", ("说话特写", "口型", "嘴部", "近景说话", "lip-sync", "mouth", "close-up dialogue")),
    ("magic_burst", ("法术", "符阵", "符纹", "灵光", "灵力", "爆发", "雷劫", "雷落", "光束", "剑气", "护盾", "阵法", "magic", "burst", "spell")),
    ("hug_or_pull", ("拥抱", "抱住", "拉扯", "拉住", "抓腕", "拽住", "推开", "扯住", "拉袖", "tug", "pull", "grab", "hug")),
    ("intimate_interaction", ("牵手", "靠近", "亲密", "搀扶", "扶住", "抚脸", "扶肩", "贴近", "疗伤", "intimate", "touch")),
    ("multi_character_same_frame", ("多人同框", "双人同框", "两人同框", "三人同框", "同框", "同画面", "two-shot", "group shot")),
    ("ensemble_blocking", ("群像", "群戏", "群臣", "门徒", "人群", "围观", "队列", "站位", "多人站位", "围住", "围堵", "众人", "ensemble", "crowd")),
    ("multi_person_blocking", ("多人", "三人", "四人", "multi-person", "blocking")),
    ("empty_establishing", ("空镜", "转场", "远景", "氛围", "环境", "establishing", "ambience", "empty")),
)

SPECIAL_TEMPLATE_SHOT_TYPES = (
    "fight_exchange", "chase", "flight", "dialogue_shot_reverse", "magic_burst",
    "hug_or_pull", "intimate_interaction", "multi_character_same_frame",
    "ensemble_blocking", "multi_person_blocking",
)

# ── 路径与目录 ─────────────────────────────────────────────────────────────
SHARED_ASSET_DIR = "共享"
LEGACY_SHARED_ASSET_DIR = "common"
PRODUCTION_DIR = "生产数据"

# ── 机检精度 ──────────────────────────────────────────────────────────────
PRECISION_FULL = "full"
PRECISION_DEGRADED = "degraded"
PRECISION_NONE = "none"
PRECISION_LEVELS = (PRECISION_FULL, PRECISION_DEGRADED, PRECISION_NONE)

PRECISION_ALIASES = {
    "ok": PRECISION_FULL, "full": PRECISION_FULL,
    "insufficient_precision": PRECISION_DEGRADED, "pillow_fallback": PRECISION_DEGRADED,
    "degraded": PRECISION_DEGRADED,
    "none": PRECISION_NONE, "unavailable": PRECISION_NONE,
}

# ── 产物 Kind ──────────────────────────────────────────────────────────────
MANIFEST_KIND = "n2d_episode_manifest"
IDENTITY_REGISTRY_KIND = "n2d_identity_registry"
ASSET_REFERENCE_REGISTRY_KIND = "n2d_asset_reference_registry"
IDENTITY_ADAPTER_MATRIX_KIND = "n2d_identity_adapter_matrix"
COMPLIANCE_MANIFEST_KIND = "n2d_compliance_manifest"
VIDEO_MODEL_ROUTES_KIND = "n2d_video_model_routes"
MOTION_CONTROL_MANIFEST_KIND = "n2d_motion_control_manifest"
LORA_VALIDATION_REPORT_KIND = "n2d_lora_validation_report"
SKILL_UPDATE_PLAN_KIND = "n2d_skill_update_plan"
SKILL_UPDATE_SNAPSHOT_KIND = "n2d_skill_update_snapshot"
CONSISTENCY_FINDINGS_KIND = "n2d_consistency_findings"
CONTRACT_INHERITANCE_KIND = "n2d_contract_inheritance"
IDENTITY_DRIFT_REPORT_KIND = "n2d_identity_drift_report"
IDENTITY_VOICE_DRIFT_REPORT_KIND = "n2d_identity_voice_drift_report"
IDENTITY_VOICE_PRINT_REPORT_KIND = "n2d_identity_voice_print_report"
PRODUCTION_EVENT_KIND = "n2d_production_event"
PRODUCTION_DASHBOARD_KIND = "n2d_production_dashboard"
PRODUCTION_ALERTS_KIND = "n2d_production_alerts"
ASSET_PACK_KIND = "n2d_asset_pack"
ASSET_RERUN_PLAN_KIND = "n2d_asset_rerun_plan"
BATCH_QUEUE_KIND = "n2d_batch_queue"
DIFFERENTIATION_CANDIDATES_KIND = "n2d_differentiation_candidates"
EPISODE_REVIEW_SCORE_KIND = "n2d_episode_review_score"
GENRE_PERFORMANCE_RECORD_KIND = "n2d_genre_performance_record"
LORA_CARD_KIND = "n2d_lora_card"
LORA_DATASET_MANIFEST_KIND = "n2d_lora_dataset_manifest"
LORA_TRAIN_JOB_KIND = "n2d_lora_train_job"
PLATFORM_FEEDBACK_KIND = "n2d_platform_feedback"
REVIEW_UI_KIND = "n2d_review_ui"
SCORE_VISUAL_CHECKS_KIND = "n2d_score_visual_checks"
VISUAL_STATE_LEDGER_KIND = "n2d_visual_state_ledger"

# ── 重制策略 ──────────────────────────────────────────────────────────────
REGEN_MODE_MINIMAL = "最小"
REGEN_MODE_STRICT_REFRESH = "严审刷新"
LEGACY_REGEN_MODE_KEEP_IMAGES = "保图刷新"

# ── 进度标记 ──────────────────────────────────────────────────────────────
PROGRESS_DONE = "✅"
PROGRESS_TODO = "⬜"
PROGRESS_ROUGH_PREFIX = "⏳"
PROGRESS_PARTIAL_RE = r"(\d+)\s*/\s*(\d+)"

CONTRACT_VERSION = 2
