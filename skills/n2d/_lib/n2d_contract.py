#!/usr/bin/env python3
"""Machine-readable contract for the n2d pipeline.

Keep the production rules that scripts share here, then let SKILL.md files
explain the same contract for humans.  This module intentionally stays pure
standard library and performs no network/model calls.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    _fcntl = None


CONTRACT_VERSION = 2
MANIFEST_KIND = "n2d_episode_manifest"


# ── 单机多 worker 文件锁（registry 读-改-写串行化）─────────────────────────
# n2d/progress.py 早已用 flock 保护 `_进度.md` 的读-改-写；身份/资产 registry
# （identity_registry.json + asset_registry.json）此前没有同款保护，n2d-batch 多
# worker / 后台 factory 进程并发 import-character / 改 lora 状态时会后写覆盖前写。
# 这里给出通用 file_lock + 每作品 registry 锁路径，供 market.py / lora.py 共用。
@contextlib.contextmanager
def file_lock(lock_path: str, timeout: float = 30.0, poll: float = 0.1):
    """Serialize a read-modify-write across single-machine multi-worker runs.

    Uses flock(LOCK_EX) where available, else a mkdir spin-lock fallback —
    mirrors n2d/progress.py progress_lock so registry writers get the same
    protection `_进度.md` already has. Releases on exit even if the body raises.
    """
    directory = os.path.dirname(lock_path) or "."
    os.makedirs(directory, exist_ok=True)
    start = time.time()
    if _fcntl is not None:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            while True:
                try:
                    _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.time() - start > timeout:
                        raise TimeoutError(f"file lock timeout ({timeout}s): {lock_path}")
                    time.sleep(poll)
            yield lock_path
        finally:
            try:
                _fcntl.flock(fd, _fcntl.LOCK_UN)
            finally:
                os.close(fd)
    else:  # pragma: no cover - non-POSIX fallback
        lock_dir = lock_path + ".d"
        acquired = False
        try:
            while True:
                try:
                    os.mkdir(lock_dir)
                    acquired = True
                    break
                except FileExistsError:
                    if time.time() - start > timeout:
                        raise TimeoutError(f"file lock timeout ({timeout}s): {lock_path}")
                    time.sleep(poll)
            yield lock_path
        finally:
            if acquired:
                try:
                    os.rmdir(lock_dir)
                except OSError:
                    pass


def registry_lock_path(root: str) -> str:
    """Per-project lock guarding the shared 身份/资产 registries' read-merge-write.
    market.py (import-character/asset) and lora.py (init/train-job/register) hold it
    so concurrent writers serialize instead of clobbering each other."""
    return os.path.join(str(root), "_registry.lock")

# ── n2d 边界型机器产物注册表（单一真值源）──────────────────────────────
# 每个 JSON 产物在顶层写 "kind"。下面这张表只登记需要明确 owner/path/layer/boundary 的
# “边界型产物”：相邻产物职责容易混淆，必须把分工写成机器可读说明。
# 其它散落脚本的 JSON kind 常量集中在本文件后段，但不一定都需要边界元数据。
VISUAL_STATE_LEDGER_KIND = "n2d_visual_state_ledger"
MOTION_CONTROL_MANIFEST_KIND = "n2d_motion_control_manifest"
IDENTITY_REGISTRY_KIND = "n2d_asset_identity_registry"
ASSET_REFERENCE_REGISTRY_KIND = "n2d_asset_reference_registry"
SHARED_ASSET_DIR = "共享"
LEGACY_SHARED_ASSET_DIR = "common"

BOUNDARY_PRODUCT_KINDS: Dict[str, Dict[str, str]] = {
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
    ASSET_REFERENCE_REGISTRY_KIND: {
        "owner": "n2d-image(写) / n2d-review·n2d-score(读校)",
        "path": f"出图/{SHARED_ASSET_DIR}/asset_registry.json",
        "layer": "非人物资产锁定（scene/prop/outfit/vfx）",
        "boundary": (
            "关键场景、反复入镜道具、独立服装/套装、法宝/VFX 的可执行参考资产注册层。"
            "用 LOC_/PROP_/OUTFIT_/VFX_ ID 绑定 reference_group、constraints、drift_forbidden；"
            "角色脸和角色形态仍归 identity_registry，剧情临时状态仍归 visual_state_ledger。"
        ),
    },
}

# Backward-compatible alias. Existing scripts/tests use PRODUCT_KINDS; new code
# should prefer BOUNDARY_PRODUCT_KINDS when it needs owner/path/layer/boundary.
PRODUCT_KINDS = BOUNDARY_PRODUCT_KINDS


def product_kind(kind: str) -> Optional[Dict[str, str]]:
    """查边界型机器产物 kind 的 owner/路径/层/边界。未注册返回 None。"""
    spec = BOUNDARY_PRODUCT_KINDS.get(kind)
    return dict(spec) if spec else None


# ── identity_registry 共享字段（单一真值源）──────────────────────────────
# 写方(n2d-lora/n2d-asset-market/n2d-identity)与校验方(n2d-review gate)必须用同一组键，
# 否则一边写、一边按另一组校验 → gate 误拒合法注册或漏掉缺口。
# reference_group 的标准参考视图键：
IDENTITY_REFERENCE_KEYS = ("front", "side", "back", "outfit", "turnaround")
# identity_adapter 是否携带"已注册句柄"的字段（任一非空即视为已登记）：
IDENTITY_HANDLE_FIELDS = ("id", "handle", "reference", "model_path")

# identity_adapters.<backend>.status 的标准状态集合（identity matrix / review gate 同源）。
IDENTITY_ADAPTER_READY_STATUSES = frozenset({"registered", "ready"})
IDENTITY_ADAPTER_FALLBACK_STATUSES = frozenset({"fallback_reference_group"})
IDENTITY_ADAPTER_PASSIVE_STATUSES = frozenset({"unsupported", "not_needed"})
IDENTITY_ADAPTER_IN_PROGRESS_STATUSES = frozenset({"unregistered", "candidate", "training"})
IDENTITY_ADAPTER_KNOWN_STATUSES = (
    IDENTITY_ADAPTER_READY_STATUSES
    | IDENTITY_ADAPTER_FALLBACK_STATUSES
    | IDENTITY_ADAPTER_PASSIVE_STATUSES
    | IDENTITY_ADAPTER_IN_PROGRESS_STATUSES
)

# 跨项目 fork 溯源：n2d-asset-market 导入角色时写入 registry 的字段。
# fork_history 按时间追加，支持 A→B→C 多级溯源；单层旧字段 source_asset_pack/slug 继续兼容。
IDENTITY_FORK_HISTORY_FIELD = "fork_history"
IDENTITY_FORK_HISTORY_ENTRY_FIELDS = ("from_pack", "from_slug", "from_character_id", "forked_at", "reason")

# 其它机器产物 kind（除 BOUNDARY_PRODUCT_KINDS 已登记项外，散落各脚本的字面值收拢于此）：
LORA_VALIDATION_REPORT_KIND = "n2d_lora_validation_report"
LORA_DATASET_MANIFEST_KIND = "n2d_lora_dataset_manifest"
LORA_TRAIN_JOB_KIND = "n2d_lora_train_job"
LORA_CARD_KIND = "n2d_lora_card"
IDENTITY_ADAPTER_MATRIX_KIND = "n2d_identity_adapter_matrix"
IDENTITY_DRIFT_REPORT_KIND = "n2d_identity_drift_report"
IDENTITY_VOICE_DRIFT_REPORT_KIND = "n2d_identity_voice_drift_report"
IDENTITY_VOICE_PRINT_REPORT_KIND = "n2d_identity_voice_print_report"
CONSISTENCY_FINDINGS_KIND = "n2d_consistency_findings"
CONTRACT_INHERITANCE_KIND = "n2d_contract_inheritance_diff"
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
SKILL_UPDATE_SNAPSHOT_KIND = "n2d_skill_update_snapshot"
SKILL_UPDATE_PLAN_KIND = "n2d_skill_update_plan"

CONSISTENCY_DIMENSIONS: Dict[str, Dict[str, Any]] = {
    "character_consistency": {
        "label": "角色一致性",
        "weight": 20,
        "return_to_stage": "image",
        "scope": "回 n2d-image 重出崩脸/身份漂移镜头；必要时补 identity_registry / reference_group。",
        "audit_labels": ("锚点门(N3)", "脸(G1)", "片内时序(N2)"),
        "keywords": ("角色", "脸", "资产身份", "identity", "face", "锚点"),
    },
    "outfit_consistency": {
        "label": "服装一致性",
        "weight": 12,
        "return_to_stage": "image",
        "scope": "回 n2d-image 重出服装/配色漂移镜头；先检查定妆组和服装参考图。",
        "audit_labels": ("服装配色(N1)",),
        "keywords": ("服装", "配色", "妆造"),
    },
    "scene_consistency": {
        "label": "场景一致性",
        "weight": 12,
        "return_to_stage": "image",
        "scope": "回 n2d-image 修场景定妆、光位锚或尾帧；必要时回 n2d-video 重出接缝 clip。",
        "audit_labels": ("场景(O2)", "接缝接力"),
        "keywords": ("场景", "接缝", "尾帧", "场景资产"),
    },
    "subtitle_correctness": {
        "label": "字幕正确性",
        "weight": 16,
        "return_to_stage": "script_stage2",
        "scope": "回 n2d-script 阶段2重跑 finalize_storyboard / 字幕重定时 / 修翻译层；必要时重出配音 manifest。",
        "audit_labels": ("字幕对齐(L1)",),
        "keywords": ("字幕", "srt", "cue", "对齐", "断句", "漏译", "阅读速度", "双语", "subtitle"),
    },
    "audio_visual_sync": {
        "label": "音画同步",
        "weight": 16,
        "return_to_stage": "compose",
        "scope": "回 n2d-compose 对齐配音轨、clip 时长、原生音轨策略；若时长源头错，回 n2d-script 阶段2。",
        "audit_labels": (),
        "keywords": ("音画", "配音", "原生音", "双人声", "时长", "voice", "audio", "口型", "mouth"),
    },
    "voice_consistency": {
        "label": "音色一致性",
        "weight": 10,
        "return_to_stage": "voice",
        "scope": "回 n2d-voice 按 voicemap 注册音色重配受影响角色台词；重配后复核时长清单与分镜时长。",
        "audit_labels": ("音色声纹", "声纹一致性", "音色漂移"),
        "keywords": ("音色", "声纹", "speaker", "voice print", "voice_key", "voicemap", "克隆音色"),
    },
    "rhythm_density": {
        "label": "节奏密度",
        "weight": 12,
        "return_to_stage": "script_stage2",
        "scope": "回 n2d-script 阶段2重切镜头时长曲线、补钩子/爽点/集尾 cliffhanger。",
        "audit_labels": (),
        "keywords": ("节奏", "钩子", "爽点", "留存", "集尾", "rhythm"),
    },
    "style_consistency": {
        "label": "风格一致性",
        "weight": 12,
        "return_to_stage": "image",
        "scope": "回 n2d-image 继承 style_contract 重出偏风格镜头；必要时回 n2d-script 修 style_contract。",
        "audit_labels": ("风格(S1)", "糊/低质(N4)"),
        "keywords": ("风格", "style", "画风", "基础视觉", "糊", "低质", "清晰度"),
    },
    "semantic_continuity": {
        "label": "语义继承",
        "weight": 8,
        "return_to_stage": "script_stage2",
        "scope": "回 n2d-script 阶段2或 prompt 生成层，修 raw/voiceover→storyboard→出图/出视频的语义谱系断点。",
        "audit_labels": ("语义谱系(P0)",),
        "keywords": ("语义", "谱系", "继承", "semantic", "voiceover", "storyboard"),
    },
    "state_continuity": {
        "label": "状态百科",
        "weight": 8,
        "return_to_stage": "image",
        "scope": "回 n2d-image 修 visual_state_ledger / 出图分镜状态锁；必要时回 storyboard 修角色状态演进。",
        "audit_labels": ("状态百科(P1)",),
        "keywords": ("状态", "动态百科", "visual_state_ledger", "state"),
    },
    "multimodal_continuity": {
        "label": "多模态漂移",
        "weight": 8,
        "return_to_stage": "image",
        "scope": "回 n2d-image 按离群道具/场景/法宝参考组只重出受影响镜头；必要时补资产 taxonomy。",
        "audit_labels": ("多模态(P2)",),
        "keywords": ("多模态", "道具", "法宝", "视觉语义", "embedding"),
    },
    "contract_inheritance": {
        "label": "视觉契约继承",
        "weight": 8,
        "return_to_stage": "video_prompt",
        "scope": "回 n2d-video 修 出视频/prompt/00_总览.md 的本集视觉一致性契约；以出图总览原文为准，光位锚/轴线视线不得改写。",
        "audit_labels": ("契约继承", "视觉契约继承"),
        "keywords": ("契约继承", "contract_inheritance", "光位锚", "轴线视线", "导演一致性"),
    },
}


def consistency_dimensions() -> Dict[str, Dict[str, Any]]:
    """Consistency dimension registry copy for score/review/batch consumers."""
    return {key: dict(spec) for key, spec in CONSISTENCY_DIMENSIONS.items()}


def consistency_dim_key(value: Any) -> Optional[str]:
    """Resolve a consistency key/label/audit label to the canonical dimension key."""
    text = str(value or "").strip()
    if not text:
        return None
    if text in CONSISTENCY_DIMENSIONS:
        return text
    folded = text.lower()
    for key, spec in CONSISTENCY_DIMENSIONS.items():
        labels = (spec.get("label"), *tuple(spec.get("audit_labels", ())))
        if any(str(label or "").strip() == text for label in labels):
            return key
        if folded == key.lower():
            return key
    return None


def consistency_dim_spec(value: Any) -> Optional[Dict[str, Any]]:
    key = consistency_dim_key(value)
    return dict(CONSISTENCY_DIMENSIONS[key]) if key else None


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

# 权利状态为这些值时必须附 evidence/ref（不能只口头声明已授权）。
# gate.py 与 compliance.py 必须共用本集合，避免 source_text 等单键漂移
# （历史上 gate 漏了 stock_licensed → 与 compliance.py --check 给出相反结论）。
COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED = {"licensed", "stock_licensed", "user_declared"}
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

# distribution_intent 为内部 demo（不投放）时，gate 可免检【平台投放相关】字段域；
# 角色/声音授权与 AI 标识仍必检（为日后转投放留底，且授权问题不因内部使用而豁免）。
COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS = {"internal_only"}
# regulatory_filing = 广电总局网络微短剧备案/分级/播前审核（2026 新规：AIGC 全面纳入分级+播前审核）。
# 与 platform_review 同列为内部 demo 免检域（内部预览不投放→不需备案；转投放前必补）。
COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS = ("platform_review", "overseas_localization", "regulatory_filing")
# 播前审核状态取值，复用 platform_review 的 ready/done/not_applicable 三态。
COMPLIANCE_PRE_BROADCAST_STATUSES = {"pending", "ready", "done", "not_applicable"}


# ── 重抽原因分类（单一真值源）────────────────────────────────────────────
# dashboard 记账时 redraw_reason 仍写自由文本，但同时归入这里的枚举维度，
# 让"一致性是不是最大的成本杀手"可统计。归不进的落 other。
REDRAW_REASON_CATEGORIES: Dict[str, str] = {
    "face_consistency": "角色脸漂/崩脸",
    "outfit_consistency": "服装/配色漂移",
    "scene_drift": "场景/光位/背景漂移",
    "style_drift": "画风跳变",
    "prop_structure": "道具结构错误/自检失败",
    "reference_cropping": "参考图裁切/构图问题",
    "prompt_conflict": "prompt 冲突/语义矛盾",
    "timing_mismatch": "时长/时序不符",
    "other": "其他",
}

# 自由文本 → 枚举的关键词表（先匹配先得；存量自由文本回填归类也用它）。
_REDRAW_REASON_KEYWORDS = (
    ("face_consistency", ("崩脸", "脸漂", "换脸", "五官", "脸型", "面部", "face")),
    ("outfit_consistency", ("服装", "衣服", "衣着", "配色", "套装", "outfit")),
    ("scene_drift", ("场景", "光位", "背景", "布景", "光线", "scene")),
    ("style_drift", ("画风", "风格跳", "风格漂", "style")),
    ("prop_structure", ("道具", "法宝", "武器", "结构错", "prop")),
    ("reference_cropping", ("裁切", "裁剪", "构图", "参考图", "crop")),
    ("prompt_conflict", ("prompt", "提示词", "语义", "矛盾", "冲突")),
    ("timing_mismatch", ("时长", "时序", "对不上", "不同步", "timing")),
)


def classify_redraw_reason(text) -> str:
    """自由文本重抽原因 → REDRAW_REASON_CATEGORIES 枚举键（关键词归类，归不进给 other）。"""
    raw = str(text or "").strip().lower()
    if not raw:
        return "other"
    if raw in REDRAW_REASON_CATEGORIES:
        return raw
    for category, keywords in _REDRAW_REASON_KEYWORDS:
        if any(k in raw for k in keywords):
            return category
    return "other"


# ── 音色一致性契约（单一真值源）──────────────────────────────────────────
# 一角一色、跨集持久绑定：voicemap.json 是角色→音色注册表（写方 n2d-voice），
# 配音 manifest 逐句记 voice_key（实际应用的音色键），n2d-identity 跨集对账出 voice_drift_report。
VOICE_MAP_RELPATH = os.path.join("设定库", "voicemap.json")
VOICE_KEY_FIELD = "voice_key"
# render_voice 历史清单写的中文字段名；消费方两者都认、voice_key 优先（写方继续双写保兼容）。
VOICE_KEY_LEGACY_FIELD = "音色键"
# 占位后端（macOS say 应急轨）voice_key 后缀：显式声明「不是 voicemap 注册音色，需重配」。
# 写方 n2d-voice 打标、读方 n2d-identity 跳过漂移比对并单列待重配清单——同一字面值。
VOICE_KEY_PLACEHOLDER_SUFFIX = "#placeholder"


def voicemap_path(root: str) -> str:
    """`<作品根>/设定库/voicemap.json` —— n2d-voice 写、n2d-identity 读校。"""
    return os.path.join(root.rstrip("/"), VOICE_MAP_RELPATH)


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

PROGRESS_DONE = "✅"
PROGRESS_TODO = "⬜"
PROGRESS_ROUGH = "⏳rough"
PROGRESS_ROUGH_PREFIX = "⏳"

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


# `制作模式` 单一真值：键序即菜单顺序，首项为默认。settings.py 的 DEFAULTS / SETTING_SPECS
# 与各 skill 文档都引这里的 production_mode_keys() / PRODUCTION_MODE_DEFAULT，勿再另写三元组。
PRODUCTION_MODE_DEFAULT = next(iter(PRODUCTION_MODES))


def production_mode_keys() -> tuple:
    """三种 `制作模式` 的规范键（有序：配音先行 / 先出视频后配音 / 原生音画）。"""
    return tuple(PRODUCTION_MODES.keys())


def normalize_production_mode(value) -> str:
    """把宽松输入（中英别名 / 空）归一到规范键；识别不出时回落默认（配音先行）。"""
    raw = (value or "").strip()
    if raw in PRODUCTION_MODES:
        return raw
    low = raw.lower()
    if is_native_av_mode(raw):
        return "原生音画"
    if "先出视频" in raw or "video_first" in low or "video-first" in low:
        return "先出视频后配音"
    if "配音先行" in raw or "voice_first" in low or "voice-first" in low:
        return "配音先行"
    return PRODUCTION_MODE_DEFAULT


# ── 横切 readiness 注册表 ───────────────────────────────────────────────
# 这些 skill 不在主流程列(PROGRESS_COLUMNS)/STAGE_GRAPH 路由里，但有作品级“就绪标志”。
# n2d-progress 只消费这张表输出“横切就绪”，避免把按需工具污染进 _进度.md 流程表。
# `artifact` 是相对作品根的就绪标志(glob)，None=仓库级/无 per-work 标志。
# `required_before` 指出它是哪些付费阶段的硬前置(目前只有合规)。
CROSS_CUTTING_READINESS = (
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
    {"key": "feedback", "skill": "n2d-feedback", "label": "投放数据回灌 + 反同质化",
     "artifact": "生产数据/platform_feedback.json", "required_before": (),
     "when": "上线后回灌留存/追更；写题材战绩库 + 差异化候选反哺选题"},
)

# Backward-compatible alias for older consumers. It means “readiness-tracked
# cross-cutting items”, not every cross-cutting tool in the family.
CROSS_CUTTING = CROSS_CUTTING_READINESS

# 横切工具注册表：这些也横切全链，但没有稳定“就绪标志”，或本身是调度/检查工具。
# 它们应出现在索引和调度说明里，但不应出现在 n2d-progress 的“横切就绪”行。
CROSS_CUTTING_TOOLS = (
    {"key": "model_router", "skill": "n2d-model-router", "label": "模型适配层",
     "when": "出视频 prompt 前按 Clip 路由 primary/fallback 后端；不写进 _进度.md"},
    {"key": "batch", "skill": "n2d-batch", "label": "批量任务队列",
     "when": "按 _进度.md / findings 生成队列、claim/mark/reclaim；就绪看 batch_queue.json，不代表作品质量"},
    {"key": "progress", "skill": "n2d-progress", "label": "进度·下一步",
     "when": "只读扫描 _进度.md 并提示下一步；它是观察工具，本身没有就绪状态"},
    {"key": "review", "skill": "n2d-review", "label": "质检·自审",
     "when": "作品质检和流程自审；findings 由 readiness 表产物承接，score/review_ui 见下方观察工具"},
    # 观察/计划类工具：有 per-work 产物但只是「可选观察输出」，不是生产前置/就绪标志 →
    # 列在工具（n2d-progress 以「横切观察·非前置」单列），不混进「横切就绪」误导成必经步骤。
    {"key": "score", "skill": "n2d-score", "label": "自动审片评分",
     "artifact": "生产数据/score_*.json",
     "when": "成片/阶段审查后机器评分，低分回流；可选观察，不阻断生产"},
    {"key": "review_ui", "skill": "n2d-review-ui", "label": "人审可视化",
     "artifact": "生产数据/review_ui_*.html",
     "when": "人判画布：聚合首尾帧/clip/QA flag/机器分；可选观察"},
    {"key": "update", "skill": "n2d-update", "label": "skill 更新重制计划",
     "artifact": "生产数据/skill_update_snapshot.json",
     "when": "n2d skills 更新后生成最小重制计划；按需触发，非前置"},
)


def cross_cutting() -> List[Dict[str, object]]:
    """横切 readiness 注册表（拷贝）。供 n2d-progress 横切就绪检查。"""
    return [dict(item) for item in CROSS_CUTTING_READINESS]


def cross_cutting_tools() -> List[Dict[str, object]]:
    """横切工具注册表（拷贝）。供索引/调度说明感知，不用于就绪度展示。"""
    return [dict(item) for item in CROSS_CUTTING_TOOLS]


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
# ⚠️ 进度：「生图后端垄断」已解除到官方/已登录后端白名单（见下 APPROVED_IMAGE_BACKENDS /
#       classify_image_backend，gate.check_image_ai_policy 消费）；其余两项仍为纯元数据。
CONTESTED = {
    "生图后端垄断": "已放行官方/已登录图片后端：生图AI 是选择点（默认 Codex），放行官方多参考一致性后端（Dreamina/即梦官方 CLI、Seedream 官方API / 可灵主体库 / Nano Banana / Sora Cameo）；gate 不再因『非 Codex』阻断，只拦后端混用 + 未授权/第三方逆向出图。见下 APPROVED_IMAGE_BACKENDS。",
    "占位驱动付费生成": "「先出视频后配音」/ 占位时长可写入 ⏳rough 并仅在该模式下驱动出图·出视频；配音先行仍需 ✅ 真实配音，成片前必须补真音。",
    "基础视觉风格": "视觉风格必须来自选择点「基础视觉风格」与 global_style。新产物写 style_contract；旧 cinematic_contract 仅作兼容，不得把写实电影感当全线不变量。",
}
INVARIANT_NOTE = (
    "其余契约项默认 invariant：阶段顺序 / _进度.md 列名 / 产物路径 / 接力契约（出点=下一入点）/ "
    "合规闸门（克隆授权·AI 标识水印）/ prompt·产物分离 / style_contract 的 style-agnostic 工艺"
    "（光色有逻辑·构图可信·运动克制·禁忌随所选风格派生）。"
)

# ── 生图后端治理：官方/已登录后端白名单 ───────────────────────────────
# 历史口径：gate 硬拦一切非 Codex 出图。当前：`生图AI` 是真选择点，默认仍 Codex；
#   放行【官方/已登录多参考一致性后端】；gate 不再因"非 Codex"阻断，只阻断：
#     ① 同项目/同集【后端混用】（混用才是跨镜一致性杀手）；
#     ② 未授权/第三方逆向图片生成路径（安全 invariant，永不放行）。
#   合规闸门（AI 标识水印 / 克隆·换脸授权）与本次无关，保持不变。
# multi_reference = 一次喂多张参考跨图锁人；native_subject = 注册可复用角色ID/主体库。
# 候选快照新鲜度戳记（本线 _lib/freshness.py 据此判过期）。
# 这是 n2d 线「生图AI」白名单/黑名单——与 ad 线策略故意不同（ad 禁即梦，见 ad-craft/contract.py）。
# 采集日期：2026-06-13  来源：各后端官方一致性能力文档 + 合规口径（待复核）
IMAGE_BACKENDS_VERIFIED = {"date": "2026-06-13", "source": "各后端官方文档 + 合规口径(待复核)"}
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


def lora_dataset_warning_blocks(report) -> List[str]:
    """dataset_has_warnings 的人工覆核判定（lora register / identity binding / review gate 三方同源）。

    有 dataset 警告时必须 manual_review.allow_dataset_warnings 显式放行 + 非空 notes 说明原因。
    返回缺口码：dataset_warnings_without_override / dataset_warnings_override_notes_missing；无警告返回空。
    """
    warnings = report.get("warnings") if isinstance(report.get("warnings"), list) else []
    if "dataset_has_warnings" not in warnings:
        return []
    manual_review = report.get("manual_review")
    manual_review = manual_review if isinstance(manual_review, dict) else {}
    if not manual_review.get("allow_dataset_warnings"):
        return ["dataset_warnings_without_override"]
    if not str(manual_review.get("notes") or "").strip():
        return ["dataset_warnings_override_notes_missing"]
    return []


def lora_report_ready_blocks(report) -> List[str]:
    """validation_report 自身能否支撑 ready 注册的缺口列表（verdict + 必填字段 + 数据集警告覆核）。

    n2d-lora cmd_register 用；磁盘层检查（model 文件存在/实测 hash 比对）由调用方补充——契约层不碰文件系统。
    """
    blocks: List[str] = []
    if not lora_verdict_ok(report.get("verdict")):
        blocks.append(f"validation_verdict_not_pass:{str(report.get('verdict') or '').strip() or 'missing'}")
    for key in LORA_REPORT_REQUIRED_FIELDS:
        if not str(report.get(key, "") or "").strip():
            blocks.append(f"missing_report_field:{key}")
    blocks.extend(lora_dataset_warning_blocks(report))
    return blocks


def lora_registry_ready_blocks(cfg, report) -> List[str]:
    """registry identity_adapters.lora 标 status=ready 时的缺口列表（identity matrix / review gate 同源）。

    cfg=registry 里的 lora 对象；report=按 cfg.validation_report 加载的报告对象（路径非空但读不出传 None）。
    磁盘层检查（model_path 是否存在）仍由调用方补充并命名 ready_model_path_missing。
    """
    blocks: List[str] = []
    for key in LORA_REGISTRY_READY_FIELDS:
        if not str(cfg.get(key, "") or "").strip():
            blocks.append(f"ready_missing_{key}")
    if not str(cfg.get("validation_report", "") or "").strip():
        return blocks  # 缺报告路径已由 ready_missing_validation_report 覆盖
    if not isinstance(report, dict):
        blocks.append("ready_validation_report_missing")
        return blocks
    if report.get("kind") != LORA_VALIDATION_REPORT_KIND:
        blocks.append("ready_validation_report_kind_invalid")
    if not lora_verdict_ok(report.get("verdict")):
        blocks.append("ready_validation_report_not_pass")
    report_hash = str(report.get("model_sha256", "") or "").strip()
    registry_hash = str(cfg.get("model_hash", "") or "").strip()
    if report_hash and registry_hash and report_hash != registry_hash:
        blocks.append("ready_model_hash_mismatch")
    blocks.extend(f"ready_{b}" for b in lora_dataset_warning_blocks(report))
    return blocks


# gap 码 → gate 报告用人读中文（review gate 消费；新增缺口码时同步补一条）。
_LORA_GAP_MESSAGES = {
    "ready_validation_report_missing": "LoRA validation_report 缺失或无法解析",
    "ready_validation_report_kind_invalid": "LoRA validation_report kind 不正确",
    "ready_validation_report_not_pass": "LoRA ready 必须对应 verdict=pass 的验证报告",
    "ready_model_hash_mismatch": "registry model_hash 与 validation_report.model_sha256 不一致",
    "ready_model_path_missing": "LoRA ready 的 model_path 不存在",
    "ready_dataset_warnings_without_override": "LoRA 数据集有 warning，但验证报告缺 allow_dataset_warnings 显式放行",
    "ready_dataset_warnings_override_notes_missing": "LoRA 数据集 warning 被人工放行时，manual_review.notes 必须写明原因",
}


def lora_gap_message(code: str) -> str:
    """LoRA 缺口码 → 人读中文说明（gate 报告用，与缺口码同源演进）。"""
    if code.startswith("ready_missing_"):
        return f"LoRA ready 但缺字段：{code[len('ready_missing_'):]}"
    return _LORA_GAP_MESSAGES.get(code, f"LoRA ready 缺口：{code}")

STAGE_GRAPH: List[Dict[str, object]] = [
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
        # 2026 出视频/合成 拆分后：配音 + 时长清单 一律落 合成/{ep}/配音/（render_voice.py 无条件写此处，
        # 与 制作模式 无关）。历史上 先出视频后配音 曾设想落 出视频/{ep}/配音/，已废弃——勿再加该路径。
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
            "生产数据/identity_adapter_matrix.json",
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
    "出图": "会真出图并消耗额度；先确认生图后端（`生图AI` 选择点：默认 Codex，可选官方/已登录多参考后端 Dreamina/即梦官方 CLI、Seedream/可灵主体库/Nano Banana/Sora Cameo——见 APPROVED_IMAGE_BACKENDS；同项目不得混用、禁第三方逆向/未授权出图）、生图预算，并先跑 image_preflight gate。",
    "视频": "会真出视频并消耗额度；先确认后端/规格并跑 video_preflight gate。",
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


def stage_requires_for_mode(spec: Dict[str, object], mode: str = "") -> tuple:
    """Return hard requirements after production-mode adjustment."""
    requires = tuple(spec.get("requires", ()))
    if is_native_av_mode(mode):
        return tuple(r for r in requires if r != "配音")
    return requires


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


def _fingerprint_episode(episode: Any) -> str:
    """归一集号：能取到数字就用数字（'第1集' / '1' / 'EP01' → '1'），否则用原串小写。"""
    s = str(episode or "").strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    return str(int(digits)) if digits else s.lower()


# 定位串里的镜头号识别：Clip_03 / Clip 3 / Clip-03 / Clip#3 / shot03 / 镜头3 / 镜头_03 / 出图/.../Clip_03.png
_SHOT_TOKEN_RE = re.compile(r"(?:clip|shot|镜头)[\s_\-#]*0*(\d+)", re.IGNORECASE)


def canonical_scope_key(scope: Any) -> str:
    """把定位串归一到稳定 token，让指纹不随定位粒度漂移而变（指纹复检的根因修复）。

    `Clip_03`、`Clip 3`、`Clip_03_首帧`、`Clip_03_尾帧`、`镜头3`、`出图/第2集/图片/Clip_03.png`
    都归到同一个 `clip_3`——同一镜头换个写法/换个帧位/换成产物路径，复检时仍判为同一问题，
    不再因 `Clip_03`→`Clip_03_首帧` 这种粒度变化把已修问题误判 resolved。
    认不出镜头号的串（定妆名、自由文本、无镜头号的产物路径）原样小写返回，行为与历史一致。
    """
    s = str(scope or "").strip()
    if not s:
        return ""
    m = _SHOT_TOKEN_RE.search(s)
    if m:
        return f"clip_{int(m.group(1))}"
    return s.lower()


def finding_fingerprint(episode: Any, stage: Any, dim: Any, scope: Any = "") -> str:
    """一致性问题的稳定指纹 = (集, return_to_stage, 维度[, scope]) 的 sha1 短哈希（单一真值源）。

    返工任务带它、复检从当前 findings 重算它。scope 为空时保持历史粒度 (集×阶段×维度)；
    有 affected_shots / affected_artifacts 时把最小定位也纳入指纹，让同集同维度多个镜头能分别
    resolved / reopen，同时仍可被同一返工任务聚合执行。scope 先过 canonical_scope_key 归一，
    使同一镜头的不同写法/帧位/产物路径产生同一指纹（见 canonical_scope_key）。
    """
    key_parts = [
        _fingerprint_episode(episode),
        str(stage or "").strip().lower(),
        str(dim or "").strip().lower(),
    ]
    scope_s = canonical_scope_key(scope)
    if scope_s:
        key_parts.append(scope_s)
    key = "|".join(key_parts)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


# ── 一致性 finding 归一化（单一真值源，消灭三端散落的 or 链）────────────────────
# review 侧 emit `severity/dimension/message`，review-ui 侧 `sev/dim/msg`，score 侧 `dimensions`(复数)。
# 任何消费端（batch 入队 / feedback / dashboard）都先过 normalize_finding，漏抄别名→静默丢 finding 的坑消失。
_DIM_KEY_BY_LABEL = {spec["label"]: key for key, spec in CONSISTENCY_DIMENSIONS.items()}


def resolve_dim_key(dim: Any) -> str:
    """把维度（可能是 key / 中文 label / 自由文本）解析成 CONSISTENCY_DIMENSIONS 的规范 key；解析不出返回 ''。"""
    d = str(dim or "").strip()
    if not d:
        return ""
    if d in CONSISTENCY_DIMENSIONS:
        return d
    if d in _DIM_KEY_BY_LABEL:
        return _DIM_KEY_BY_LABEL[d]
    for key, spec in CONSISTENCY_DIMENSIONS.items():
        if any(kw and kw in d for kw in spec.get("keywords", ())):
            return key
    return ""


def normalize_finding(raw: Dict[str, Any]) -> Dict[str, Any]:
    """把任意一端 emit 的一致性 finding 归一成规范结构（吸收 sev/dim/msg 别名、补 dim_key、回退 return_to_stage）。"""
    if not isinstance(raw, dict):
        return {}
    severity = str(raw.get("severity") or raw.get("sev") or raw.get("verdict") or "").strip().lower()
    dim = raw.get("dimension") or raw.get("dim") or ""
    if not dim:
        dims = raw.get("dimensions")
        if isinstance(dims, list) and dims:
            dim = dims[0]
    dim_key = str(raw.get("dim_key") or "").strip() or resolve_dim_key(dim)
    stage = str(raw.get("return_to_stage") or raw.get("rerun_from") or "").strip()
    if not stage and dim_key in CONSISTENCY_DIMENSIONS:
        stage = str(CONSISTENCY_DIMENSIONS[dim_key].get("return_to_stage") or "")
    return {
        "severity": severity,
        "dimension": str(dim or "").strip(),
        "dim_key": dim_key,
        "message": str(raw.get("message") or raw.get("msg") or "").strip(),
        "return_to_stage": stage,
        "rerun_scope": str(raw.get("rerun_scope") or raw.get("scope") or "").strip(),
        "loc": str(raw.get("loc") or "").strip(),
        "shot": str(raw.get("shot") or "").strip(),
        "affected_shots": [str(s) for s in (raw.get("affected_shots") or []) if str(s).strip()],
        "affected_artifacts": [str(a) for a in (raw.get("affected_artifacts") or []) if str(a).strip()],
    }


def finding_dim_key(raw: Dict[str, Any]) -> str:
    """finding → 用于分组/指纹的稳定维度键：优先规范 dim_key，回退原 dimension 文本，再回退 '一致性'。"""
    norm = normalize_finding(raw)
    return norm.get("dim_key") or norm.get("dimension") or "一致性"


def finding_scope_keys(raw: Dict[str, Any]) -> List[str]:
    """finding → 最小定位键列表。优先镜头，其次产物，再次 loc；全空则返回 [''] 保持历史粗粒度。"""
    norm = normalize_finding(raw)
    scopes = norm.get("affected_shots") or norm.get("affected_artifacts") or []
    if not scopes and norm.get("loc"):
        scopes = [str(norm["loc"])]
    cleaned: List[str] = []
    seen = set()
    for scope in scopes:
        text = str(scope or "").strip()
        if text and text not in seen:
            seen.add(text)
            cleaned.append(text)
    return cleaned or [""]


def finding_fingerprints(episode: Any, stage: Any, dim: Any, raw: Optional[Dict[str, Any]] = None) -> List[str]:
    """按 finding 的最小定位生成一个或多个指纹；无定位时退回单个粗粒度指纹。"""
    scopes = finding_scope_keys(raw or {})
    return [finding_fingerprint(episode, stage, dim, scope) for scope in scopes]


# ── 镜头类型判定关键词（单一真值源）──────────────────────────────────────────
# router.infer_shot_type 与 gate 专项镜头模板检测此前各维护一张关键词表，已经漂移
# （router fight 有「撞击/combat/hit」、gate 有「搏斗/格挡/受击/掌风/刀光」）。统一到这里，
# 两边消费同一份数据、各自保留自己的匹配器（router 小写匹配、gate 子串匹配）。顺序=匹配优先级。
SHOT_TYPE_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
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
# 需要专项镜头模板的复杂类型（gate 专项模板检测用；不含纯近景说话/空镜/普通运动）
SPECIAL_TEMPLATE_SHOT_TYPES: Tuple[str, ...] = (
    "fight_exchange", "chase", "flight", "dialogue_shot_reverse", "magic_burst",
    "hug_or_pull", "intimate_interaction", "multi_character_same_frame",
    "ensemble_blocking", "multi_person_blocking",
)


def special_template_keywords() -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """gate 专项镜头模板检测用的 (shot_type, keywords) 子集，从 SHOT_TYPE_KEYWORDS 派生（保序）。"""
    sset = set(SPECIAL_TEMPLATE_SHOT_TYPES)
    return tuple((st, kw) for st, kw in SHOT_TYPE_KEYWORDS if st in sset)


def make_consistency_finding(severity: str, dimension: str, message: str, *,
                             return_to_stage: Optional[str] = None, loc: str = "",
                             rerun_scope: str = "", affected_shots: Optional[List[str]] = None,
                             affected_artifacts: Optional[List[str]] = None) -> Dict[str, Any]:
    """规范一致性 finding 工厂——emit 端统一用它，字段名不再各写各的。"""
    return normalize_finding({
        "severity": severity, "dimension": dimension, "message": message,
        "return_to_stage": return_to_stage, "loc": loc, "rerun_scope": rerun_scope,
        "affected_shots": affected_shots or [], "affected_artifacts": affected_artifacts or [],
    })


PRODUCTION_DIR = "生产数据"  # 仪表盘/评分/投放/审片UI 的产出目录（单一真值源）


def production_dir(root: str) -> str:
    """`<作品根>/生产数据/` 绝对路径——dashboard/score/feedback/review-ui/batch 共用。"""
    root = os.fspath(root)
    return os.path.join(root.rstrip("/"), PRODUCTION_DIR)


# 同一进程内每个作品根只告警一次，避免批量脚本刷屏。
_SPLIT_BRAIN_WARNED: set = set()


def _warn_shared_asset_split_brain(base: str) -> None:
    """新旧共享定妆目录并存 = 裂脑高危态：不同 skill 可能各读各的 registry。检测到就大声提示迁移。"""
    current = os.path.join(base, "出图", SHARED_ASSET_DIR)
    legacy = os.path.join(base, "出图", LEGACY_SHARED_ASSET_DIR)
    if base in _SPLIT_BRAIN_WARNED or not (os.path.isdir(current) and os.path.isdir(legacy)):
        return
    _SPLIT_BRAIN_WARNED.add(base)
    import sys as _sys

    print(
        f"[warn] 共享定妆库新旧目录并存（裂脑风险）：{current} 与 {legacy} 同时存在。\n"
        f"       请先迁移收口：python3 skills/n2d/_lib/n2d_contract.py migrate-shared '{base}'",
        file=_sys.stderr,
    )


def shared_asset_dir(root: str, *, prefer_existing: bool = True) -> str:
    """共享定妆库目录。新项目写中文目录；旧英文目录仅作读取兜底（并存时告警，应尽快 migrate-shared 收口）。"""
    base = root.rstrip("/")
    _warn_shared_asset_split_brain(base)
    current = os.path.join(base, "出图", SHARED_ASSET_DIR)
    legacy = os.path.join(base, "出图", LEGACY_SHARED_ASSET_DIR)
    if prefer_existing and not os.path.exists(current) and os.path.exists(legacy):
        return legacy
    return current


def shared_asset_path(root: str, *parts: str, prefer_existing: bool = True) -> str:
    """共享定妆库内路径；写新产物时传 `prefer_existing=False`。"""
    base = root.rstrip("/")
    _warn_shared_asset_split_brain(base)
    current = os.path.join(base, "出图", SHARED_ASSET_DIR, *parts)
    legacy = os.path.join(base, "出图", LEGACY_SHARED_ASSET_DIR, *parts)
    if prefer_existing and not os.path.exists(current) and os.path.exists(legacy):
        return legacy
    return current


def migrate_legacy_shared_assets(root: str, *, apply: bool = True) -> Dict[str, object]:
    """把旧 `出图/common/` 迁到 `出图/共享/`，消除双路径裂脑。

    - 只有 legacy：整体改名为 current；
    - 两边并存：逐文件把 legacy 独有的搬到 current；两边同名的列入 conflicts 留在原地，
      人工裁决（不自动覆盖任何一边）；legacy 清空后删除空目录。
    返回 {"moved": [...], "conflicts": [...], "removed_legacy": bool}；apply=False 只演练不动文件。
    """
    base = root.rstrip("/")
    current = os.path.join(base, "出图", SHARED_ASSET_DIR)
    legacy = os.path.join(base, "出图", LEGACY_SHARED_ASSET_DIR)
    result: Dict[str, object] = {"moved": [], "conflicts": [], "removed_legacy": False}
    if not os.path.isdir(legacy):
        return result
    if not os.path.exists(current):
        if apply:
            os.rename(legacy, current)
        result["moved"] = [LEGACY_SHARED_ASSET_DIR]
        result["removed_legacy"] = True
        return result
    moved: List[str] = []
    conflicts: List[str] = []
    for dirpath, _, files in os.walk(legacy):
        rel_dir = os.path.relpath(dirpath, legacy)
        for name in files:
            rel = name if rel_dir == "." else os.path.join(rel_dir, name)
            src = os.path.join(legacy, rel)
            dst = os.path.join(current, rel)
            if os.path.exists(dst):
                conflicts.append(rel)
                continue
            if apply:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                os.rename(src, dst)
            moved.append(rel)
    result["moved"] = moved
    result["conflicts"] = conflicts
    if apply and not conflicts:
        for dirpath, _, _ in os.walk(legacy, topdown=False):
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
        result["removed_legacy"] = not os.path.exists(legacy)
    return result


def shared_asset_relpath(*parts: str) -> str:
    return os.path.join("出图", SHARED_ASSET_DIR, *parts)


def identity_registry_path(root: str) -> str:
    """角色身份注册表路径，取自 BOUNDARY_PRODUCT_KINDS 注册的 path（move 时只改一处）。"""
    return shared_asset_path(root, "identity_registry.json")


def asset_registry_path(root: str) -> str:
    """非人物关键资产注册表路径，取自 BOUNDARY_PRODUCT_KINDS 注册的 path（move 时只改一处）。"""
    return shared_asset_path(root, "asset_registry.json")


def episode_manifest_path(root: str, ep: str) -> str:
    return os.path.join(root.rstrip("/"), "脚本", ep, "manifest.json")


def _render(path_template: str, ep: str) -> str:
    return path_template.format(ep=ep)


# ── Episode-Specific Path Helpers (SSOT) ─────────────────────────────────
# Avoid hardcoding "脚本/{ep}", "出图/{ep}", etc. in individual scripts.
# {ep} is the episode name/number string.

def episode_script_dir(root: str, ep: str) -> str:
    """Path to the script directory for an episode: `<作品根>/脚本/<ep>/`."""
    return os.path.join(root.rstrip("/"), "脚本", ep)

def episode_image_dir(root: str, ep: str) -> str:
    """Path to the image production directory: `<作品根>/出图/<ep>/`."""
    return os.path.join(root.rstrip("/"), "出图", ep)

def episode_video_dir(root: str, ep: str) -> str:
    """Path to the video production directory: `<作品根>/出视频/<ep>/`."""
    return os.path.join(root.rstrip("/"), "出视频", ep)

def episode_compose_dir(root: str, ep: str) -> str:
    """Path to the composition/final audio directory: `<作品根>/合成/<ep>/`."""
    return os.path.join(root.rstrip("/"), "合成", ep)

def episode_voice_dir(root: str, ep: str) -> str:
    """Path to the voice audio subdirectory: `<作品根>/合成/<ep>/配音/`."""
    return os.path.join(episode_compose_dir(root, ep), "配音")

def episode_storyboard_path(root: str, ep: str) -> str:
    """Path to storyboard.json: `<作品根>/脚本/<ep>/storyboard.json`."""
    return os.path.join(episode_script_dir(root, ep), "storyboard.json")

def episode_timing_path(root: str, ep: str) -> str:
    """Path to episode-wide timings: `<作品根>/脚本/<ep>/镜头时长.json`."""
    return os.path.join(episode_script_dir(root, ep), "镜头时长.json")

def episode_voice_manifest_path(root: str, ep: str) -> str:
    """Path to voice timing manifest: `<作品根>/合成/<ep>/配音/时长清单.json`."""
    return os.path.join(episode_voice_dir(root, ep), "时长清单.json")

def episode_output_video_path(root: str, ep: str, mode: str = "zh") -> str:
    """Path to final MP4: `<作品根>/合成/<ep>/成片_<ep>_<mode>.mp4`."""
    return os.path.join(episode_compose_dir(root, ep), f"成片_{ep}_{mode}.mp4")

# ── Registry Loading (SSOT with Split-Brain Protection) ─────────────────

def load_json_registry(path: str) -> Dict[str, Any]:
    """Load a JSON registry with basic error handling."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}

def load_identity_registry(root: str) -> Dict[str, Any]:
    """Load identity_registry.json from shared_asset_dir (SSOT)."""
    return load_json_registry(identity_registry_path(root))

def load_asset_registry(root: str) -> Dict[str, Any]:
    """Load asset_registry.json from shared_asset_dir (SSOT)."""
    return load_json_registry(asset_registry_path(root))

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


def _episode_names(root: str) -> List[str]:
    script_dir = os.path.join(root.rstrip("/"), "脚本")
    if not os.path.isdir(script_dir):
        return []
    names = [
        name for name in os.listdir(script_dir)
        if os.path.isdir(os.path.join(script_dir, name)) and name.startswith("第") and name.endswith("集")
    ]
    return sorted(names, key=lambda x: int(re.search(r"\d+", x).group(0)) if re.search(r"\d+", x) else 10**9)


def _manifest_schema_version(path: str) -> Optional[int]:
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        return int(data.get("schema_version"))
    except (TypeError, ValueError, AttributeError):
        return None


def contract_version_report(root: str) -> Dict[str, object]:
    """Inspect per-episode manifests against CONTRACT_VERSION."""
    episodes = []
    for ep in _episode_names(root):
        path = episode_manifest_path(root, ep)
        version = _manifest_schema_version(path) if os.path.isfile(path) else None
        status = "missing" if version is None else "current" if version == CONTRACT_VERSION else "stale" if version < CONTRACT_VERSION else "future"
        episodes.append({"episode": ep, "path": path, "schema_version": version, "status": status})
    stale = [e for e in episodes if e["status"] in {"missing", "stale"}]
    future = [e for e in episodes if e["status"] == "future"]
    return {
        "kind": "n2d_contract_version_report",
        "contract_version": CONTRACT_VERSION,
        "root": root,
        "episodes": episodes,
        "stale_or_missing": len(stale),
        "future": len(future),
        "status": "blocked_future" if future else "migration_needed" if stale else "current",
    }


def migrate_v1_to_v2(root: str, *, apply: bool = True) -> Dict[str, object]:
    """Safe v1→v2 migration scaffold.

    v2 is backward-compatible for storyboard fields; the deterministic migration
    is to refresh every episode manifest so downstream tools can reason from the
    current schema version. Media/storyboard files are not rewritten here.
    """
    actions: List[Dict[str, str]] = []
    for ep in _episode_names(root):
        path = episode_manifest_path(root, ep)
        version = _manifest_schema_version(path) if os.path.isfile(path) else None
        if version == CONTRACT_VERSION:
            continue
        actions.append({"episode": ep, "action": "refresh_episode_manifest", "path": path})
        if apply:
            write_episode_manifest(root, ep, extra={"migration_note": "migrated v1->v2 by refreshing manifest"})
    return {"from": 1, "to": 2, "actions": actions, "applied": apply}


CONTRACT_MIGRATIONS = {1: migrate_v1_to_v2}


def migrate_contract(root: str, *, target_version: int = CONTRACT_VERSION, apply: bool = True) -> Dict[str, object]:
    """Run registered contract migrations up to target_version and write a report."""
    if target_version > CONTRACT_VERSION:
        raise ValueError(f"target_version {target_version} is newer than code contract {CONTRACT_VERSION}")
    before = contract_version_report(root)
    if before["status"] == "blocked_future":
        raise ValueError("project has manifests newer than this code contract; upgrade skills before migrating")
    steps: List[Dict[str, object]] = []
    if before["status"] == "migration_needed":
        # Missing manifests are treated as v1-era projects for the current safe scaffold.
        start = 1
        stale_versions = [
            e.get("schema_version") for e in before["episodes"]
            if e.get("status") == "stale" and isinstance(e.get("schema_version"), int)
        ]
        if stale_versions:
            start = max(1, min(stale_versions))
        for version in range(start, target_version):
            migration = CONTRACT_MIGRATIONS.get(version)
            if migration is None:
                raise ValueError(f"missing migration function: v{version}->v{version + 1}")
            steps.append(migration(root, apply=apply))
    after = contract_version_report(root) if apply else before
    report = {
        "kind": "n2d_contract_migration_report",
        "contract_version": CONTRACT_VERSION,
        "target_version": target_version,
        "root": root,
        "applied": apply,
        "before": before,
        "steps": steps,
        "after": after,
    }
    if apply:
        path = os.path.join(production_dir(root), "contract_migration_report.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
        report["report_path"] = path
    return report


if __name__ == "__main__":
    # 维护入口：
    #   python3 skills/n2d/_lib/n2d_contract.py migrate-shared <作品根> [--dry-run]
    #   python3 skills/n2d/_lib/n2d_contract.py check-version <作品根>
    #   python3 skills/n2d/_lib/n2d_contract.py migrate-version <作品根> [--dry-run]
    import argparse

    _parser = argparse.ArgumentParser(description="n2d contract maintenance")
    _sub = _parser.add_subparsers(dest="command", required=True)
    _mig = _sub.add_parser("migrate-shared", help="把旧 出图/common/ 迁到 出图/共享/，消除双路径裂脑")
    _mig.add_argument("root")
    _mig.add_argument("--dry-run", action="store_true")
    _check = _sub.add_parser("check-version", help="检查每集 manifest schema_version 是否落后于当前契约")
    _check.add_argument("root")
    _ver = _sub.add_parser("migrate-version", help="运行契约版本迁移脚手架并刷新每集 manifest")
    _ver.add_argument("root")
    _ver.add_argument("--dry-run", action="store_true")
    _args = _parser.parse_args()
    if _args.command == "migrate-shared":
        _result = migrate_legacy_shared_assets(_args.root, apply=not _args.dry_run)
        print(json.dumps(_result, ensure_ascii=False, indent=2))
        if _result["conflicts"]:
            print("[warn] 存在同名冲突文件，已留在旧目录，请人工裁决后重跑。")
            raise SystemExit(1)
    elif _args.command == "check-version":
        _result = contract_version_report(_args.root)
        print(json.dumps(_result, ensure_ascii=False, indent=2))
        if _result["status"] != "current":
            raise SystemExit(1)
    elif _args.command == "migrate-version":
        _result = migrate_contract(_args.root, apply=not _args.dry_run)
        print(json.dumps(_result, ensure_ascii=False, indent=2))


# ── 机检精度三档（face/voice/seam 等检测器的统一降级词汇）──────────────────────
# full: 真实全精度信号（ArcFace/声纹 embedding 等）→ 正常计分；
# degraded: 有真实但低精度信号（Pillow 基础机检等）→ 消费端降权分，状态封顶 warn；
# none: 无任何信号（缺后端/缺音频）→ insufficient_data，交人判，绝不臆造分数。
# 历史词汇（ok/insufficient_precision/pillow_fallback）经 normalize_precision 归一，旧报告不破坏。
PRECISION_FULL = "full"
PRECISION_DEGRADED = "degraded"
PRECISION_NONE = "none"
PRECISION_LEVELS = (PRECISION_FULL, PRECISION_DEGRADED, PRECISION_NONE)

_PRECISION_ALIASES = {
    "ok": PRECISION_FULL, "full": PRECISION_FULL,
    "insufficient_precision": PRECISION_DEGRADED, "pillow_fallback": PRECISION_DEGRADED,
    "degraded": PRECISION_DEGRADED,
    "none": PRECISION_NONE, "unavailable": PRECISION_NONE,
}


def normalize_precision(result):
    """把检测器报告（available/mode/precision 各家老词汇）归一到三档。

    规则：available=False（无任何信号）→ none，无论 precision 写什么；
    available 真/缺省 → 按 precision 别名表归一，未知/缺省视为 full（真信号默认全精度）。
    收 dict（检测器报告）或裸字符串。
    """
    if isinstance(result, dict):
        if result.get("available") is False:
            return PRECISION_NONE
        return _PRECISION_ALIASES.get(str(result.get("precision") or "").strip().lower(), PRECISION_FULL)
    return _PRECISION_ALIASES.get(str(result or "").strip().lower(), PRECISION_NONE)
