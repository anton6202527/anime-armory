#!/usr/bin/env python3
"""Machine-readable contract for the novel2drama/n2d pipeline.

Keep the production rules that scripts share here, then let SKILL.md files
explain the same contract for humans.  This module intentionally stays pure
standard library and performs no network/model calls.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, Iterable, List, Optional


CONTRACT_VERSION = 2
MANIFEST_KIND = "n2d_episode_manifest"

# ── n2d 机器产物 kind 注册表（单一真值源）────────────────────────────────
# 每个 JSON 产物在顶层写 "kind": <这里的值>，校验/消费方据此识别。把散落各脚本的 kind
# 字面值收拢一处，并标明 owner / 路径 / 所属"层"与边界——尤其澄清相邻产物的职责分工，
# 避免把会变的状态塞进锁身份的 registry、或反之。
VISUAL_STATE_LEDGER_KIND = "n2d_visual_state_ledger"
MOTION_CONTROL_MANIFEST_KIND = "n2d_motion_control_manifest"
IDENTITY_REGISTRY_KIND = "n2d_asset_identity_registry"
SHARED_ASSET_DIR = "共享"
LEGACY_SHARED_ASSET_DIR = "common"

PRODUCT_KINDS: Dict[str, Dict[str, str]] = {
    VISUAL_STATE_LEDGER_KIND: {
        "owner": "n2d-image",
        "path": f"出图/{SHARED_ASSET_DIR}/visual_state_ledger.json",
        "layer": "状态演进（state evolution）",
        "boundary": (
            "记录角色随剧情变化的【可变视觉状态】（受伤/战损/衣破/获得法宝/脏污），按集累积、可失效，"
            "出图前注入分镜 prompt。与 identity_registry 互补、严格分工——"
            "identity_registry 锁【不变身份】(定妆库人脸/形态/asset_key)，visual_state_ledger 叠【会变的状态修饰符】。"
            "不得在此登记角色身份/定妆；也不得把临时战损塞进 identity_registry。"
        ),
    },
    MOTION_CONTROL_MANIFEST_KIND: {
        "owner": "n2d-model-router(声明) / n2d-review(校验)",
        "path": "出视频/{ep}/control/{clip_id}/motion_control_manifest.json",
        "layer": "运动控制（motion control）",
        "boundary": (
            "高危物理接触镜头的 pose/depth/instance + 接触约束控制资产；router 声明 level=required、"
            "gate 校验 ready/degrade_only。判定 shot_type 见 MOTION_CONTROL_REQUIRED_SHOT_TYPES。"
        ),
    },
    IDENTITY_REGISTRY_KIND: {
        "owner": "n2d-image(写) / n2d-identity·n2d-review(读校)",
        "path": f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
        "layer": "身份锁定（identity）",
        "boundary": (
            "角色【不变身份】注册层：定妆库人脸/形态/asset_key/reference_group/identity_adapters。"
            "跨集一致性的源头。会变的剧情状态属 visual_state_ledger，不在此。"
        ),
    },
}


def product_kind(kind: str) -> Optional[Dict[str, str]]:
    """查机器产物 kind 的 owner/路径/层/边界（单一真值源）。未注册返回 None。"""
    spec = PRODUCT_KINDS.get(kind)
    return dict(spec) if spec else None


# ── identity_registry 共享字段（单一真值源）──────────────────────────────
# 写方(n2d-lora/n2d-asset-market/n2d-identity)与校验方(n2d-review gate)必须用同一组键，
# 否则一边写、一边按另一组校验 → gate 误拒合法注册或漏掉缺口。
# reference_group 的标准参考视图键：
IDENTITY_REFERENCE_KEYS = ("front", "side", "back", "outfit", "turnaround")
# identity_adapter 是否携带"已注册句柄"的字段（任一非空即视为已登记）：
IDENTITY_HANDLE_FIELDS = ("id", "handle", "reference", "model_path")

# 其它机器产物 kind（除 PRODUCT_KINDS 已登记三项外，散落各脚本的字面值收拢于此）：
LORA_VALIDATION_REPORT_KIND = "n2d_lora_validation_report"
LORA_DATASET_MANIFEST_KIND = "n2d_lora_dataset_manifest"
LORA_TRAIN_JOB_KIND = "n2d_lora_train_job"
LORA_CARD_KIND = "n2d_lora_card"
IDENTITY_ADAPTER_MATRIX_KIND = "n2d_identity_adapter_matrix"
IDENTITY_DRIFT_REPORT_KIND = "n2d_identity_drift_report"
VIDEO_MODEL_ROUTES_KIND = "n2d_video_model_routes"
COMPLIANCE_MANIFEST_KIND = "n2d_compliance_manifest"
ASSET_PACK_KIND = "n2d_cross_project_asset_pack"
ASSET_RERUN_PLAN_KIND = "n2d_asset_rerun_plan"
BATCH_QUEUE_KIND = "n2d_batch_queue"
PRODUCTION_EVENT_KIND = "n2d_production_event"
PRODUCTION_DASHBOARD_KIND = "n2d_production_dashboard"
PRODUCTION_ALERTS_KIND = "n2d_production_alerts"
PLATFORM_FEEDBACK_KIND = "n2d_platform_feedback"
GENRE_PERFORMANCE_RECORD_KIND = "genre_performance_record"
DIFFERENTIATION_CANDIDATES_KIND = "n2d_differentiation_candidates"
REVIEW_UI_KIND = "n2d_review_ui"
EPISODE_REVIEW_SCORE_KIND = "n2d_episode_review_score"
SCORE_VISUAL_CHECKS_KIND = "n2d_score_visual_checks"


# ── compliance / gate 共享状态集合（单一真值源）────────────────────────────
COMPLIANCE_ALLOWED_RIGHTS = {
    "original",
    "public_domain",
    "licensed",
    "user_declared",
    "synthetic",
    "stock_licensed",
    "not_applicable",
}
COMPLIANCE_APPROVED_CHARACTER = {
    "synthetic_character",
    "original_character",
    "actor_authorized",
    "self_authorized",
    "licensed_likeness",
    "not_applicable",
}
COMPLIANCE_BLOCKED_CHARACTER = {
    "unknown",
    "real_person_unlicensed",
    "public_figure_unlicensed",
    "minor_unverified",
}
COMPLIANCE_SAFE_VOICE = {
    "no_clone",
    "synthetic_voice",
    "platform_stock_voice",
    "authorized_clone",
    "not_applicable",
}
COMPLIANCE_READY_STATUSES = {"planned", "ready", "done", "not_applicable", "not_supported"}
COMPLIANCE_DONE_STATUSES = {"done", "not_applicable"}
COMPLIANCE_PLATFORM_REVIEW_STATUSES = {"ready", "done", "not_applicable"}
COMPLIANCE_STATUS_LIKE_VALUES = {
    "ready",
    "done",
    "planned",
    "pending",
    "unknown",
    "not_applicable",
    "not_supported",
    "internal_only",
    "publish_candidate",
    "paid_distribution",
    "na",
    "n/a",
    "none",
    "null",
    "未定",
    "无",
}
COMPLIANCE_PLACEHOLDER_MARKERS = (
    "todo",
    "tbd",
    "placeholder",
    "example",
    "待补",
    "待填写",
    "待定",
    "示例",
    "样例",
    "占位",
)
COMPLIANCE_OVERSEAS_PLATFORMS = {"youtube", "tiktok", "instagram", "reels", "shorts", "x", "twitter"}
COMPLIANCE_DOMESTIC_REGIONS = {"cn", "china", "中国", "mainland_china", "zh-cn"}


# ── identity_adapters 后端能力表（单一真值源）─────────────────────────────
# 三方共用：n2d-asset-market 重置时按 default_mode/default_status 构造，
# n2d-identity / n2d-review gate 按 allowed_modes 校验。三处曾各写一份 → default_mode
# 必须 ∈ allowed_modes，否则"刚重置的 registry 过不了自己的校验"。handle=该后端登记句柄字段名。
IDENTITY_IMAGE_ADAPTERS: Dict[str, Dict[str, object]] = {
    "codex":    {"allowed_modes": ("reference_group",), "default_mode": "reference_group", "default_status": "fallback_reference_group"},
    "openai":   {"allowed_modes": ("reference_group",), "default_mode": "reference_group", "default_status": "fallback_reference_group"},
    "dreamina": {"allowed_modes": ("reference_group",), "default_mode": "reference_group", "default_status": "fallback_reference_group"},
    "kling":    {"allowed_modes": ("character_id", "subject_library", "custom_model", "element_library"), "default_mode": "subject_library", "default_status": "unregistered", "handle": "id"},
    "seedream": {"allowed_modes": ("universal_reference",), "default_mode": "universal_reference", "default_status": "unregistered", "handle": "reference"},
    "sora":     {"allowed_modes": ("character_cameo",), "default_mode": "character_cameo", "default_status": "unregistered", "handle": "id"},
}
IDENTITY_VIDEO_ADAPTERS: Dict[str, Dict[str, object]] = {
    "dreamina": {"allowed_modes": ("first_last_frame", "reference_group"), "default_mode": "first_last_frame", "default_status": "fallback_reference_group"},
    "kling":    {"allowed_modes": ("character_id",), "default_mode": "character_id", "default_status": "unregistered", "handle": "id"},
    "seedance": {"allowed_modes": ("face_lock",), "default_mode": "face_lock", "default_status": "unregistered", "handle": "reference"},
    "veo":      {"allowed_modes": ("reference_controls",), "default_mode": "reference_controls", "default_status": "unregistered", "handle": "id"},
}


def identity_allowed_modes(adapters: Dict[str, Dict[str, object]]) -> Dict[str, tuple]:
    """{backend: allowed_modes} —— 供 identity/gate 校验 adapter mode 合法性。"""
    return {b: tuple(spec["allowed_modes"]) for b, spec in adapters.items()}


def identity_reset_template(adapters: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, str]]:
    """{backend: {mode, status, [handle字段]}} —— 供 market 重置 identity_adapters。"""
    out: Dict[str, Dict[str, str]] = {}
    for backend, spec in adapters.items():
        entry: Dict[str, str] = {"mode": str(spec["default_mode"]), "status": str(spec["default_status"])}
        handle = spec.get("handle")
        if handle:
            entry[str(handle)] = ""
        out[backend] = entry
    return out

PROGRESS_COLUMNS = (
    "集",
    "字数",
    "raw",
    "剧本改编",
    "bgm",
    "封面",
    "配音",
    "分镜设计",
    "素材清单",
    "字幕中",
    "字幕英",
    "出图prompt",
    "出图",
    "视频prompt",
    "视频",
    "成片",
)

PRODUCTION_MODES = {
    "配音先行": {
        "label": "配音先行",
        "recommended": True,
        "summary": "真实配音时长驱动分镜、出图、出视频，音画最准、返工最少。",
    },
    "先出视频后配音": {
        "label": "先出视频后配音",
        "recommended": False,
        "summary": "估算时长先锁镜头，合成前补真实配音；适合 demo，但可能重切/重出视频。",
    },
    "原生音画": {
        "label": "原生音画（native AV）",
        "recommended": False,
        "summary": (
            "Seedance 2.0 / Veo 3 / Sora 类后端一次生成同步音画（含台词+口型+环境声），"
            "说话镜走 native_speech 路由、绕过配音先行的时长清单；少了逐句音色控制，但避免"
            "「配音→对口型」代差与占位返工。AI 标识/克隆授权仍由 compliance gate 管。"
        ),
    },
}


def is_native_av_mode(mode) -> bool:
    """`制作模式` 是否为原生音画（native synchronized AV）。"""
    return "原生音画" in (mode or "") or "native_av" in (mode or "").lower()


# ── 横切 skill 注册表 ───────────────────────────────────────────────────
# 这些 skill 不在主流程列(PROGRESS_COLUMNS)/STAGE_GRAPH 路由里——它们是按需横切的能力层。
# 把它们登记在契约这一处单一真值源，让 n2d-progress 能感知"横切就绪度"、让索引/调度有据可查，
# 而不必污染 _进度.md 的逐集流程表。`artifact` 是相对作品根的就绪标志(glob)，None=仓库级/无per-work标志。
# `required_before` 指出它是哪些付费阶段的硬前置(目前只有合规)。
CROSS_CUTTING = (
    {"key": "compliance", "skill": "n2d-compliance", "label": "合规与版权前置",
     "artifact": "合规/compliance_manifest.json", "required_before": ("image", "video", "compose", "review"),
     "when": "新剧/投放前；image 起每个付费阶段 gate 都读它"},
    {"key": "identity", "skill": "n2d-identity", "label": "角色身份闭环",
     "artifact": "生产数据/identity_adapter_matrix.json", "required_before": (),
     "when": "出图/出视频前生成 adapter matrix；审片看跨集漂移"},
    {"key": "lora", "skill": "n2d-lora", "label": "LoRA 生命周期",
     "artifact": "设定库/lora", "required_before": (),
     "when": "仅核心长线角色；reference_group/原生主体压不住才上"},
    {"key": "asset_market", "skill": "n2d-asset-market", "label": "跨项目资产库",
     "artifact": None, "required_before": (),
     "when": "开新剧/新增角色场景前先查资产库复用（仓库级，无 per-work 标志）"},
    {"key": "dashboard", "skill": "n2d-dashboard", "label": "生产数据仪表盘",
     "artifact": "生产数据/dashboard.json", "required_before": (),
     "when": "每次生成/审查/投放回收后记账；watch 实时监控"},
    {"key": "score", "skill": "n2d-score", "label": "自动审片评分",
     "artifact": "生产数据/score_*.json", "required_before": (),
     "when": "成片/阶段审查后机器评分，低分回流"},
    {"key": "review_ui", "skill": "n2d-review-ui", "label": "人审可视化",
     "artifact": "生产数据/review_ui_*.html", "required_before": (),
     "when": "人判画布：聚合首尾帧/clip/QA flag/机器分"},
    {"key": "feedback", "skill": "n2d-feedback", "label": "投放数据回灌 + 反同质化",
     "artifact": "生产数据/platform_feedback.json", "required_before": (),
     "when": "上线后回灌留存/追更；写题材战绩库 + 差异化候选反哺选题"},
)


def cross_cutting() -> List[Dict[str, object]]:
    """横切 skill 注册表（拷贝）。供 n2d-progress 横切就绪检查、索引/调度感知。"""
    return [dict(item) for item in CROSS_CUTTING]


VISUAL_CONTRACT_FIELDS = (
    "色调基线",
    "场景光位锚",
    "场景轴线视线",
    "角色状态演进",
    "景别阶梯",
)

STYLE_CONTRACT_FIELDS = (
    "风格名",
    "视觉基调",
    "镜头与构图",
    "光色策略",
    "运动边界",
    "风格禁忌",
)

# Backward-compatible legacy field set.  Existing projects may still carry
# `cinematic_contract`; new storyboard.json files should write `style_contract`.
CINEMATIC_CONTRACT_FIELDS = (
    "摄影基调",
    "镜头焦段",
    "光源动机",
    "色彩策略",
    "运镜边界",
    "真实感禁忌",
)

# ── 契约治理：invariant（已定不变量，可硬化）vs contested（待决原则，应保持 soft）──
# 见 docs/n2d-原则变更提案-契约治理与一致性占位.md 提案一 P1.1/P1.3。
# 治理原则：标 contested 的原则不应被新增 BLOCK gate / "必须/只能/不可选" 措辞进一步硬化；
#       可以把现有 contested 的 BLOCK 降级为 WARN/choice（解除垄断）。
# ⚠️ 进度：「生图后端垄断」已推进到阶段2（见下 APPROVED_IMAGE_BACKENDS / classify_image_backend，
#       gate.check_image_ai_policy 消费）；其余两项仍为阶段0 纯元数据。
CONTESTED = {
    "生图后端垄断": "已推进到【阶段2·官方即梦放行】：生图AI 是选择点（默认 Codex），放行官方多参考一致性后端（Dreamina/即梦官方 CLI、Seedream 官方API / 可灵主体库 / Nano Banana / Sora Cameo）；gate 不再因『非 Codex』阻断，只拦后端混用 + 未授权/第三方逆向出图。见下 APPROVED_IMAGE_BACKENDS。",
    "占位驱动付费生成": "「先出视频后配音」/ 占位时长驱动出图·出视频，与配音先行不变量冲突（提案三，目标 rough→refine 两遍制）。",
    "基础视觉风格": "视觉风格必须来自选择点「基础视觉风格」与 global_style。新产物写 style_contract；旧 cinematic_contract 仅作兼容，不得把写实电影感当全线不变量。",
}
INVARIANT_NOTE = (
    "其余契约项默认 invariant：阶段顺序 / _进度.md 列名 / 产物路径 / 接力契约（出点=下一入点）/ "
    "合规闸门（克隆授权·AI 标识水印）/ prompt·产物分离 / style_contract 的 style-agnostic 工艺"
    "（光色有逻辑·构图可信·运动克制·禁忌随所选风格派生）。"
)

# ── 生图后端治理：阶段1（解除 Codex 垄断）──────────────────────────────
# 历史阶段0：gate 硬拦一切非 Codex 出图。阶段2：`生图AI` 是真选择点，默认仍 Codex；
#   放行【官方/已登录多参考一致性后端】；gate 不再因"非 Codex"阻断，只阻断：
#     ① 同项目/同集【后端混用】（混用才是跨镜一致性杀手）；
#     ② 未授权/第三方逆向图片生成路径（安全 invariant，永不放行）。
#   合规闸门（AI 标识水印 / 克隆·换脸授权）与本次无关，保持不变。
# multi_reference = 一次喂多张参考跨图锁人；native_subject = 注册可复用角色ID/主体库。
APPROVED_IMAGE_BACKENDS = {
    "codex":    {"label": "Codex / 官方 OpenAI gpt-image", "multi_reference": False, "native_subject": False, "default": True},
    "openai":   {"label": "官方 OpenAI gpt-image / DALL·E", "multi_reference": False, "native_subject": False},
    "dreamina": {"label": "Dreamina/即梦官方 CLI（会员账号登录·text2image/image2image）", "multi_reference": True, "native_subject": False},
    "gemini":   {"label": "Nano Banana / Gemini 多参考（原生 SynthID）", "multi_reference": True, "native_subject": False},
    "seedream": {"label": "Seedream Universal Reference（官方 API·免 LoRA 跨图锁人·≤14 图）", "multi_reference": True, "native_subject": True},
    "kling":    {"label": "可灵 Kling 主体库 / Custom Model / Element Library", "multi_reference": True, "native_subject": True},
    "sora":     {"label": "Sora Character Cameo（可复用角色ID）", "multi_reference": True, "native_subject": True},
}

# 别名 → canonical。只收官方入口名。
_IMAGE_BACKEND_ALIASES = {
    "codex only": "codex", "codexonly": "codex", "codex": "codex",
    "openai": "openai", "gpt-image": "openai", "gpt image": "openai", "gptimage": "openai",
    "dall-e": "openai", "dalle": "openai",
    "dreamina": "dreamina", "即梦": "dreamina", "jimeng": "dreamina",
    "nano banana": "gemini", "nanobanana": "gemini", "nano-banana": "gemini", "gemini": "gemini",
    "seedream": "seedream", "universal reference": "seedream",
    "kling": "kling", "可灵": "kling", "主体库": "kling",
    "sora": "sora", "character cameo": "sora", "cameo": "sora",
}

# 未授权 / 非官方自动化出图路径——安全 invariant，gate 永远 BLOCK，不属 contested。
# 注意：Dreamina/即梦官方 CLI 和 ByteDance 官方 Seedream API 均属 approved；
# 这里拦的是含糊的"同视频AI"口径或明确第三方逆向/网页自动化。
FORBIDDEN_IMAGE_BACKENDS = ("同视频ai", "非官方dreamina", "第三方dreamina", "dreamina逆向", "即梦逆向", "web自动化")


def classify_image_backend(raw: Optional[str]) -> tuple:
    """归类一个生图后端字面值。

    返回 (canonical, kind)，kind ∈ {"approved", "forbidden", "unknown"}：
      - approved：官方后端（白名单），返回 canonical key；
      - forbidden：未授权/第三方逆向出图路径（安全 invariant，gate 必拦）；
      - unknown：未知后端（gate 给 WARN 选择点提示，不硬拦）。
    """
    text = (raw or "").strip().lower()
    if not text:
        return ("", "unknown")
    for bad in FORBIDDEN_IMAGE_BACKENDS:
        if bad in text:
            return ("", "forbidden")
    for alias in sorted(_IMAGE_BACKEND_ALIASES, key=len, reverse=True):
        if alias in text:
            return (_IMAGE_BACKEND_ALIASES[alias], "approved")
    return ("", "unknown")

CONTINUITY_FIELDS = (
    "start_state",
    "action",
    "end_state",
    "constraints",
    "negative",
    "transition",
    "need_endframe",
)

# ── Motion Control 判定：高危物理接触镜头需要控制契约 + ready manifest ──────
# router(n2d-model-router) 声明控制要求、gate(n2d-review) 校验控制资产——两边必须用
# 同一组 shot_type / risk_flag 判定，否则一边定 level=required 另一边放行（曾各写一份字面值）。
# 单一真值源在此；router.CONTACT_SHOT_TYPES、gate.MOTION_CONTROL_REQUIRED_SHOT_TYPES 都从这里派生。
MOTION_CONTROL_REQUIRED_SHOT_TYPES = ("fight_exchange", "intimate_interaction", "hug_or_pull")
MOTION_CONTROL_RISK_FLAGS = ("physical_interaction", "feature_melting_risk", "contact_motion")


def motion_control_required(shot_type=None, risk_flags=None) -> bool:
    """高危物理接触镜头是否必须 Motion Control 控制契约（pose/depth/instance + 接触约束）。
    router 用它定 motion_control.level=required，gate 用它定是否硬闸 ready manifest——同一判定。"""
    if str(shot_type or "").strip() in MOTION_CONTROL_REQUIRED_SHOT_TYPES:
        return True
    if risk_flags:
        return any(f in MOTION_CONTROL_RISK_FLAGS for f in risk_flags)
    return False


# ── LoRA ready 判定：注册为 ready 必须满足的报告/registry 字段 + verdict ──────
# n2d-lora cmd_register 写 ready、n2d-review gate._validate_identity_lora 校验 registry ready，
# 两边须用同一组要求；漂了就会出现"注册放行但审片拦"或反之。单一真值源在此。
LORA_READY_VERDICTS = ("pass",)
# validation_report 必填字段（lora register 读 report 决定能否升 ready）
LORA_REPORT_REQUIRED_FIELDS = ("base_model", "model_path", "trigger", "model_sha256")
# registry identity_adapters.lora 里 status=ready 时的必填字段（gate 校验 registry 用；
# report 的 model_sha256 落到 registry 叫 model_hash，validation_report 是回链路径）
LORA_REGISTRY_READY_FIELDS = ("base_model", "model_path", "trigger", "validation_report", "model_hash")


def lora_verdict_ok(verdict) -> bool:
    """validation_report.verdict 是否达到可注册 ready 的判定（单一真值源）。"""
    return str(verdict or "").strip() in LORA_READY_VERDICTS

STAGE_GRAPH: List[Dict[str, object]] = [
    {
        "key": "source",
        "label": "源文本落档",
        "owner": "n2d-script",
        "progress_columns": ("raw",),
        "command": "/n2d-script {root}",
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
        "command": "/n2d-script {root} {ep}",
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
        "command": "/n2d-voice {root} {ep}",
        "routes": True,
        "gate_stage": None,
        "requires": ("剧本改编",),
        "outputs": (
            "合成/{ep}/配音/voice_zh.wav",
            "合成/{ep}/配音/时长清单.json",
            "合成/{ep}/配音/_占位说明.md",
            "出视频/{ep}/配音/时长清单.json",
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
                        "出视频/{ep}/配音/时长清单.json",
                    ),
                },
                {
                    "label": "视频先行真实配音清单",
                    "all_of": (
                        "出视频/{ep}/配音/时长清单.json",
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
        "command": "/n2d-script {root} {ep}  (配音后定稿)",
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
        "command": "/n2d-image {root} {ep}",
        "routes": True,
        "gate_stage": "image",
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
        "command": "/n2d-image {root} {ep}",
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
        "command": "/n2d-video {root} {ep}",
        "routes": True,
        "gate_stage": "video",
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
        "command": "/n2d-video {root} {ep}",
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
        "command": "/n2d-compose {root} {ep}",
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
        "command": "/n2d-review {root} {ep}",
        "routes": False,
        "gate_stage": "review",
        "requires": ("成片",),
        "outputs": (
            "合成/{ep}/成片_{ep}_zh_水印.mp4",
            "合成/{ep}/成片_{ep}_bilingual_水印.mp4",
        ),
        "output_contract": {
            "any_of": (
                {"label": "中文字幕水印成片", "all_of": ("合成/{ep}/成片_{ep}_zh_水印.mp4",)},
                {"label": "双语水印成片", "all_of": ("合成/{ep}/成片_{ep}_bilingual_水印.mp4",)},
            ),
        },
        "return_to_stage": "review",
    },
]

GATE_RECOVERY = {
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
        "rerun_scope": "先补视频/字幕/真配音/水印策略，再重跑 compose gate；通过后再合成。",
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
        "rerun_scope": "按 finding 回退到最早受影响阶段；若只缺水印，补 watermark 即可。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            "出视频/{ep}/视频",
            "合成/{ep}",
        ),
    },
}

GATE_STAGES = tuple(GATE_RECOVERY)

COSTLY_HINTS = {
    "配音": "声音克隆需授权；即便设置里有默认值，也要确认合规与后端。",
    "出图": "会真出图并消耗额度；先确认生图后端（`生图AI` 选择点：默认 Codex，可选官方/已登录多参考后端 Dreamina/即梦官方 CLI、Seedream/可灵主体库/Nano Banana/Sora Cameo——见 APPROVED_IMAGE_BACKENDS；同项目不得混用、禁第三方逆向/未授权出图）、生图预算与 image gate。",
    "视频": "会真出视频并消耗额度；先确认后端/规格并跑 video gate。",
    "成片": "合成相对便宜但会产投放候选；先跑 compose gate 并确认水印策略。",
}


def stage_specs() -> List[Dict[str, object]]:
    return [dict(spec) for spec in STAGE_GRAPH]


def routing_stages():
    """Return the legacy `n2d_route.STAGES` tuple shape."""
    return [
        (list(spec["progress_columns"]), str(spec["label"]), str(spec["owner"]), str(spec["command"]))
        for spec in STAGE_GRAPH
        if spec.get("routes")
    ]


def stage_for_key(key: str) -> Optional[Dict[str, object]]:
    return next((dict(spec) for spec in STAGE_GRAPH if spec["key"] == key), None)


def stage_for_progress_column(column: str) -> Optional[Dict[str, object]]:
    for spec in STAGE_GRAPH:
        if column in spec.get("progress_columns", ()):
            return dict(spec)
    return None


def gate_recovery(stage: str, ep: Optional[str] = None) -> Dict[str, object]:
    data = dict(GATE_RECOVERY.get(stage, {}))
    if not data:
        return {}
    if ep:
        data["affected_artifacts"] = [str(p).format(ep=ep) for p in data.get("affected_artifacts", ())]
    return data


def annotate_finding(finding: Dict[str, str], gate_stage: str, ep: Optional[str] = None) -> Dict[str, object]:
    """Add machine-readable rollback fields without changing the old fields."""
    out: Dict[str, object] = dict(finding)
    recovery = gate_recovery(gate_stage, ep=ep)
    if not recovery:
        return out
    out.setdefault("return_to_stage", recovery.get("return_to_stage"))
    out.setdefault("rerun_scope", recovery.get("rerun_scope"))
    out.setdefault("affected_artifacts", recovery.get("affected_artifacts", ()))
    return out


PRODUCTION_DIR = "生产数据"  # 仪表盘/评分/投放/审片UI 的产出目录（单一真值源）


def production_dir(root: str) -> str:
    """`<作品根>/生产数据/` 绝对路径——dashboard/score/feedback/review-ui/batch 共用。"""
    return os.path.join(root.rstrip("/"), PRODUCTION_DIR)


def shared_asset_dir(root: str, *, prefer_existing: bool = True) -> str:
    """共享定妆库目录。新项目写中文目录；旧英文目录仍可作为读取兜底。"""
    base = root.rstrip("/")
    current = os.path.join(base, "出图", SHARED_ASSET_DIR)
    legacy = os.path.join(base, "出图", LEGACY_SHARED_ASSET_DIR)
    if prefer_existing and not os.path.exists(current) and os.path.exists(legacy):
        return legacy
    return current


def shared_asset_path(root: str, *parts: str, prefer_existing: bool = True) -> str:
    """共享定妆库内路径；写新产物时传 `prefer_existing=False`。"""
    base = root.rstrip("/")
    current = os.path.join(base, "出图", SHARED_ASSET_DIR, *parts)
    legacy = os.path.join(base, "出图", LEGACY_SHARED_ASSET_DIR, *parts)
    if prefer_existing and not os.path.exists(current) and os.path.exists(legacy):
        return legacy
    return current


def shared_asset_relpath(*parts: str) -> str:
    return os.path.join("出图", SHARED_ASSET_DIR, *parts)


def identity_registry_path(root: str) -> str:
    """角色身份注册表路径，取自 PRODUCT_KINDS 注册的 path（move 时只改一处）。"""
    return shared_asset_path(root, "identity_registry.json")


def episode_manifest_path(root: str, ep: str) -> str:
    return os.path.join(root.rstrip("/"), "脚本", ep, "manifest.json")


def _render(path_template: str, ep: str) -> str:
    return path_template.format(ep=ep)


def _sha256(path: str) -> Optional[str]:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _dir_count(path: str) -> Optional[int]:
    if not os.path.isdir(path):
        return None
    total = 0
    for _, _, files in os.walk(path):
        total += len(files)
    return total


def artifact_snapshot(root: str, ep: str, rel_path: str, stage_key: str) -> Dict[str, object]:
    rel = _render(rel_path, ep)
    full = os.path.join(root.rstrip("/"), rel)
    exists = os.path.exists(full)
    item: Dict[str, object] = {
        "stage": stage_key,
        "path": rel,
        "exists": exists,
        "kind": "dir" if os.path.isdir(full) else "file" if os.path.isfile(full) else "missing",
    }
    digest = _sha256(full)
    if digest:
        item["sha256"] = digest
    count = _dir_count(full)
    if count is not None:
        item["file_count"] = count
    return item


def collect_episode_artifacts(root: str, ep: str, stage: Optional[str] = None) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    for spec in STAGE_GRAPH:
        key = str(spec["key"])
        if stage and key != stage:
            continue
        for rel in spec.get("outputs", ()):
            items.append(artifact_snapshot(root, ep, str(rel), key))
    return items


def build_episode_manifest(
    root: str,
    ep: str,
    stage: Optional[str] = None,
    extra: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    try:
        from n2d_settings import production_mode
    except ImportError:
        from .n2d_settings import production_mode

    data: Dict[str, object] = {
        "kind": MANIFEST_KIND,
        "schema_version": CONTRACT_VERSION,
        "episode": ep,
        "stage": stage or "all",
        "production_mode": production_mode(root),
        "artifacts": collect_episode_artifacts(root, ep, stage=stage),
    }
    if extra:
        data.update(extra)
    return data


def write_episode_manifest(
    root: str,
    ep: str,
    stage: Optional[str] = None,
    extra: Optional[Dict[str, object]] = None,
) -> str:
    path = episode_manifest_path(root, ep)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = build_episode_manifest(root, ep, stage=stage, extra=extra)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path
