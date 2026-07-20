#!/usr/bin/env python3
"""Shared constants for the n2d pipeline."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Tuple

# ── identity_registry 共享字段 ──────────────────────────────────────────────
# identity adapter 的历史最小 reference_group 键；不等于 B7 分档的全部必需视图。
# core_full 的五角契约由 CHARACTER_LIBRARY_CORE_VIEWS 单独定义，避免让
# recurring/named 的 adapter matrix 被这个历史通用常量一刀切升档。
IDENTITY_REFERENCE_KEYS = ("front", "side", "back", "outfit", "turnaround")

# ── 人物角色库分档契约（B7 单一真值源）──────────────────────────────
CHARACTER_LIBRARY_TIER_CORE = "core_full"
CHARACTER_LIBRARY_TIER_STANDARD = "recurring_standard"
CHARACTER_LIBRARY_TIER_MINIMAL = "named_minimal"
CHARACTER_LIBRARY_TIER_PARTIAL = "restricted_partial"
CHARACTER_LIBRARY_TIERS: Tuple[str, ...] = (
    CHARACTER_LIBRARY_TIER_CORE,
    CHARACTER_LIBRARY_TIER_STANDARD,
    CHARACTER_LIBRARY_TIER_MINIMAL,
    CHARACTER_LIBRARY_TIER_PARTIAL,
)
CHARACTER_LIBRARY_TIER_RANK = {
    CHARACTER_LIBRARY_TIER_PARTIAL: 0,
    CHARACTER_LIBRARY_TIER_MINIMAL: 1,
    CHARACTER_LIBRARY_TIER_STANDARD: 2,
    CHARACTER_LIBRARY_TIER_CORE: 3,
}
CHARACTER_LIBRARY_CORE_VIEWS: Tuple[str, ...] = (
    "front",
    "three_quarter",
    "side",
    "rear_three_quarter",
    "back",
)
CHARACTER_LIBRARY_REQUIRED_VIEWS = {
    CHARACTER_LIBRARY_TIER_CORE: CHARACTER_LIBRARY_CORE_VIEWS,
    CHARACTER_LIBRARY_TIER_STANDARD: ("front", "three_quarter"),
    CHARACTER_LIBRARY_TIER_MINIMAL: ("front",),
    CHARACTER_LIBRARY_TIER_PARTIAL: (),
}
CHARACTER_LIBRARY_REQUIRED_REFERENCE_GROUP_FIELDS = {
    CHARACTER_LIBRARY_TIER_CORE: CHARACTER_LIBRARY_CORE_VIEWS + ("turnaround",),
    CHARACTER_LIBRARY_TIER_STANDARD: ("front", "three_quarter"),
    CHARACTER_LIBRARY_TIER_MINIMAL: ("front",),
    CHARACTER_LIBRARY_TIER_PARTIAL: (),
}

# ── 核心人物逐视图人工收据契约（B7 单一真值源）──────────────────────
# producer、image_qc、出图 runner 和 n2d-review consumer 都必须消费这一份，
# 避免 expression 被误写成 turnaround 合同，或某个消费侧只看“字段非空”。
IDENTITY_REVIEW_BINDING_FINGERPRINT_KIND = (
    "sha256:canonical-json(char,form,tier,view,path,png_sha256)"
)
IDENTITY_TURNAROUND_REVIEW_CONTRACT = "n2d_turnaround_view_review_v1"
IDENTITY_EXPRESSION_REVIEW_CONTRACT = "n2d_expression_review_v1"
IDENTITY_TURNAROUND_REQUIRED_CRITERIA = frozenset({
    "identity_and_costume_same_source",
    "head_top_and_foot_line_aligned",
    "body_centerline_and_height_aligned",
    "neutral_background_light_pose",
    "full_body_head_to_foot_visible",
})
IDENTITY_EXPRESSION_REQUIRED_CRITERIA = frozenset({
    "same_identity_as_canonical_face_anchor",
    "expression_readable_without_identity_drift",
    "hair_accessories_and_costume_continuity",
    "neutral_or_declared_expression_lighting",
})
_IDENTITY_AUTOMATED_REVIEWER_RE = re.compile(
    r"(?:^|[^a-z0-9])(bot|codex|agent|runner)(?:[^a-z0-9]|$)",
    re.IGNORECASE,
)
_IDENTITY_AUTOMATED_REVIEWER_CN = ("机器人", "智能体", "自动审", "自动化审核")


def identity_review_contract_for_view(view: object) -> str:
    return (
        IDENTITY_EXPRESSION_REVIEW_CONTRACT
        if str(view or "").strip() == "expression"
        else IDENTITY_TURNAROUND_REVIEW_CONTRACT
    )


def identity_review_required_criteria(view: object) -> frozenset[str]:
    return (
        IDENTITY_EXPRESSION_REQUIRED_CRITERIA
        if str(view or "").strip() == "expression"
        else IDENTITY_TURNAROUND_REQUIRED_CRITERIA
    )


def identity_reviewer_appears_automated(value: object) -> bool:
    reviewer = str(value or "").strip()
    return bool(
        not reviewer
        or _IDENTITY_AUTOMATED_REVIEWER_RE.search(reviewer.lower())
        or any(marker in reviewer for marker in _IDENTITY_AUTOMATED_REVIEWER_CN)
    )


def identity_reviewed_at_errors(value: object) -> Tuple[str, ...]:
    reviewed_at = str(value or "").strip()
    if not reviewed_at:
        return ("reviewed_at_missing",)
    try:
        parsed = dt.datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except ValueError:
        return ("reviewed_at_invalid",)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return ("reviewed_at_timezone_missing",)
    return ()


def identity_review_binding_fingerprint(
    *,
    character_id: object,
    form: object,
    library_tier: object,
    view: object,
    path: object,
    png_sha256: object,
) -> str:
    payload = {
        "character_id": str(character_id or ""),
        "form": str(form or ""),
        "library_tier": str(library_tier or ""),
        "path": str(path or ""),
        "png_sha256": str(png_sha256 or ""),
        "view": str(view or ""),
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
CHARACTER_LIBRARY_CORE_SCOPE_RE = re.compile(
    r"全篇|全程|长线|核心|主角|女主|男主|主反派"
)
CHARACTER_LIBRARY_RECURRING_SCOPE_RE = re.compile(
    r"常驻|多集|中长线|反复|复现|复用|主要配角|男二|女二|主反派|贯穿"
)
RESTRICTED_PARTIAL_FORBIDDEN_PART_RE = re.compile(
    r"(?:^|[_\s/-])(?:face|facial|head|portrait|front)(?:$|[_\s/-])|正脸|面部|五官|头部",
    re.I,
)


def normalize_character_library_tier(value: object, *, default: str = "") -> str:
    """将旧档位别名归一。

    空值不再在契约层偷偷当作 core_full；由调用方显式决定缺失值是
    阻断、迁移警告，还是使用剧情权重推导的期望档位。
    """
    tier = str(value or "").strip()
    if tier in CHARACTER_LIBRARY_TIERS:
        return tier
    if tier.startswith(CHARACTER_LIBRARY_TIER_PARTIAL):
        return CHARACTER_LIBRARY_TIER_PARTIAL
    if tier in {"standard_full", "full_makeup_pack", "full", "core"}:
        return CHARACTER_LIBRARY_TIER_CORE
    return default if default in CHARACTER_LIBRARY_TIERS else ""


def infer_character_library_tier(
    *,
    scope: str = "",
    narrative_tier: str = "",
    episode_count: int = 0,
    restricted: bool = False,
) -> str:
    """按剧情权重推导最低角色库档位，不信任资产自报档位。"""
    if restricted:
        return CHARACTER_LIBRARY_TIER_PARTIAL
    try:
        appearances = max(0, int(episode_count or 0))
    except (TypeError, ValueError):
        appearances = 0
    scope_text = str(scope or "")
    narrative_text = str(narrative_tier or "")
    if (
        narrative_text == "核心长线"
        or CHARACTER_LIBRARY_CORE_SCOPE_RE.search(f"{scope_text} {narrative_text}")
        or appearances >= 10
    ):
        return CHARACTER_LIBRARY_TIER_CORE
    if appearances >= 3 or CHARACTER_LIBRARY_RECURRING_SCOPE_RE.search(scope_text):
        return CHARACTER_LIBRARY_TIER_STANDARD
    return CHARACTER_LIBRARY_TIER_MINIMAL


def restricted_partial_contract_valid(record: Mapping[str, Any]) -> bool:
    """验证核心角色走局部/不露脸路径时的可审计例外。

    只写 ``library_tier=restricted_partial`` 或 ``face_policy=no_full_face`` 是自报，
    不足以让主角降档。
    """
    contract = record.get("restricted_partial_contract")
    if not isinstance(contract, Mapping):
        return False
    allowed = contract.get("allowed_parts")
    face_policy = str(record.get("face_policy") or "").strip()
    contract_face_policy = str(contract.get("face_policy") or "").strip()
    allowed_values = [str(item).strip() for item in allowed] if isinstance(allowed, (list, tuple)) else []
    return bool(
        str(contract.get("status") or "").strip().lower() == "approved"
        and len(str(contract.get("reason") or "").strip()) >= 8
        and str(contract.get("reviewer") or "").strip()
        and allowed_values
        and not any(RESTRICTED_PARTIAL_FORBIDDEN_PART_RE.search(item) for item in allowed_values)
        and face_policy in {"no_full_face", "no_clear_facial_features"}
        and contract_face_policy == face_policy
    )


def character_library_tier_for_record(
    record: Mapping[str, Any],
    *,
    observed_episode_count: int = 0,
) -> str:
    """返回人物记录应满足的最低档位。

    显式档位可以主动升档，但不能把主角/核心长线降档来绕过多视图。
    restricted_partial 只在有明确局部/不露正脸语义时作为独立路径。

    ``observed_episode_count`` 由 registry 外的已物化故事产物提供时，只能
    抬高最低档，不能降档。默认 0 保持旧项目兼容；本函数不自行读文件，
    避免把可选故事索引缺失误当成一次出场。
    """
    explicit = normalize_character_library_tier(record.get("library_tier"))
    visual_tier = normalize_character_library_tier(record.get("tier"))
    face_policy = str(record.get("face_policy") or "").strip()
    restricted_requested = bool(
        record.get("restricted_partial") is True
        or explicit == CHARACTER_LIBRARY_TIER_PARTIAL
        or visual_tier == CHARACTER_LIBRARY_TIER_PARTIAL
        or face_policy in {"no_full_face", "no_clear_facial_features"}
    )
    try:
        recorded_episode_count = max(
            0,
            int(record.get("planned_episode_count") or record.get("episode_count") or 0),
        )
    except (TypeError, ValueError):
        recorded_episode_count = 0
    try:
        independent_episode_count = max(0, int(observed_episode_count or 0))
    except (TypeError, ValueError):
        independent_episode_count = 0
    inferred = infer_character_library_tier(
        scope=str(record.get("scope") or ""),
        narrative_tier=(
            "核心长线"
            if record.get("core") is True or record.get("long_line") is True
            else str(record.get("narrative_tier") or "")
        ),
        episode_count=max(recorded_episode_count, independent_episode_count),
        restricted=False,
    )
    entity_id = str(record.get("id") or record.get("character_id") or "").strip().upper()
    scope_text = str(record.get("scope") or "")
    group_or_crowd = bool(
        entity_id.startswith(("GROUP_", "CROWD_"))
        or re.search(r"群像|群演|人群|crowd|group", scope_text, re.I)
    )
    # 具名人物不能靠自报 partial 绕开复现/核心最低档。任何 recurring/core
    # 人物都必须有审批合同；GROUP_/CROWD_ 群像保持局部资产路径。单集
    # minimal 功能角色保留结构化 restricted_partial/no-face 的旧项目兼容。
    if restricted_requested and (
        restricted_partial_contract_valid(record)
        or group_or_crowd
        or inferred == CHARACTER_LIBRARY_TIER_MINIMAL
    ):
        return CHARACTER_LIBRARY_TIER_PARTIAL
    if explicit == CHARACTER_LIBRARY_TIER_PARTIAL:
        explicit = ""
    if not explicit:
        return inferred
    return max((explicit, inferred), key=lambda tier: CHARACTER_LIBRARY_TIER_RANK[tier])


def required_character_library_views(tier: object) -> Tuple[str, ...]:
    normalized = normalize_character_library_tier(tier)
    return CHARACTER_LIBRARY_REQUIRED_VIEWS.get(normalized, ())


def required_character_reference_group_fields(tier: object) -> Tuple[str, ...]:
    normalized = normalize_character_library_tier(tier)
    return CHARACTER_LIBRARY_REQUIRED_REFERENCE_GROUP_FIELDS.get(normalized, ())


def character_library_tier_is_at_least(actual: object, expected: object) -> bool:
    actual_tier = normalize_character_library_tier(actual)
    expected_tier = normalize_character_library_tier(expected)
    if not actual_tier or not expected_tier:
        return False
    if CHARACTER_LIBRARY_TIER_PARTIAL in {actual_tier, expected_tier}:
        return actual_tier == expected_tier
    return CHARACTER_LIBRARY_TIER_RANK[actual_tier] >= CHARACTER_LIBRARY_TIER_RANK[expected_tier]

# identity_adapter 是否携带"已注册句柄"的字段（任一非空即视为已登记）
IDENTITY_HANDLE_FIELDS = ("id", "handle", "reference", "model_path")

# identity_adapters.<backend>.status 的标准状态集合
IDENTITY_ADAPTER_KNOWN_STATUSES = (
    "unregistered", "fallback_reference_group", "registered", "candidate", "pending", "training",
    "ready", "abandoned", "error", "deprecated", "unsupported", "not_needed",
)
IDENTITY_ADAPTER_READY_STATUSES = ("registered", "ready")
IDENTITY_ADAPTER_FALLBACK_STATUSES = ("unregistered", "fallback_reference_group", "fallback", "reference_group")
IDENTITY_ADAPTER_PASSIVE_STATUSES = ("unsupported", "not_needed")
IDENTITY_ADAPTER_IN_PROGRESS_STATUSES = ("candidate", "pending", "training")

# ── compliance / gate 共享状态集合 ────────────────────────────────────────────
COMPLIANCE_ALLOWED_RIGHTS = ("original", "public_domain", "licensed", "stock_licensed", "user_declared", "not_applicable", "unknown", "")
COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED = ("licensed", "stock_licensed", "user_declared")
COMPLIANCE_APPROVED_CHARACTER = ("actor_authorized", "self_authorized", "licensed_likeness", "ai_generated_original", "synthetic_character", "not_applicable")
COMPLIANCE_BLOCKED_CHARACTER = ("unauthorized", "disputed")
COMPLIANCE_SAFE_VOICE = ("authorized_clone", "stock_voice", "human_recording", "synthetic_voice", "not_applicable")
COMPLIANCE_READY_STATUSES = ("ready", "done", "not_applicable")
COMPLIANCE_DONE_STATUSES = ("ready", "done", "approved", "not_applicable")
COMPLIANCE_PLATFORM_REVIEW_STATUSES = ("ready", "done", "not_applicable")
COMPLIANCE_PRE_BROADCAST_STATUSES = ("pending", "ready", "filed", "approved", "done", "not_applicable")
COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS = ("internal_only", "demo", "test")
COMPLIANCE_PLACEHOLDER_MARKERS = ("todo", "待补", "待办", "xxx", "xxx", "...", "n/a?")
COMPLIANCE_OVERSEAS_PLATFORMS = ("tiktok", "youtube", "reelshort", "instagram", "facebook")
COMPLIANCE_DOMESTIC_REGIONS = ("cn", "china", "mainland", "中国", "中国大陆", "内地")
COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS = ("platform_review", "localization", "regulatory_filing")
# AI 生成合成内容标识：n2d 只保留非阻断 manifest / best-effort 后处理 / 发布待办提示。
# 显式标签、元数据隐式标识、数字水印和平台披露不得成为主流程 blocker。
COMPLIANCE_AI_LABEL_STATUSES = ("pending", "done", "not_applicable")
COMPLIANCE_AI_LABEL_DEFAULT_TEXT = "AI生成"
COMPLIANCE_AI_LABEL_SPEC = "GB45438-2025"
# AI 标识字段仅供 INFO 提醒和发布检查参考，不参与主流程放行。
COMPLIANCE_STATUS_LIKE_VALUES = (
    "pending", "ready", "done", "not_applicable", "filed", "approved",
    "blocked", "missing", "unknown", "todo",
)

# ── 重抽原因分类 ────────────────────────────────────────────────────────────
REDRAW_REASON_ENUM = ("identity_drift", "composition", "action_quality", "glitch", "prompt_adjustment", "other")
# 重抽原因九类维度（单一真值源）。键名与消费端对齐：dashboard render 的「一致性小计」按
# (face_consistency/outfit_consistency/scene_drift/style_drift) 求和，n2d-score / SKILL.md 同此命名。
# 2026-06-15：const 曾漂成另一套键(identity_drift/composition/glitch…)与 render+test+doc 全部脱节，
# 致「一致性小计」恒为 0、文本归类落不进消费维度；此处恢复为文档化的九类。
REDRAW_REASON_CATEGORIES = {
    "face_consistency": "脸漂/身份",
    "outfit_consistency": "服装/配色",
    "scene_drift": "场景/光位",
    "style_drift": "画风",
    "prop_structure": "道具/特效",
    "reference_crop": "参考图裁切",
    "prompt_conflict": "prompt 冲突",
    "temporal": "时序/接缝",
    "backend_migration": "后端/管线迁移",
    "other": "其他",
}
# 自由文本 → 维度：按序首个命中即归类（顺序即优先级），无命中落 other。
# 顺序上 prop_structure 放在 scene_drift 前——"道具/法宝结构"含"结构"易被场景类误吞。
REDRAW_REASON_KEYWORDS = (
    ("face_consistency", ("崩脸", "不像", "脸飘", "脸漂", "人不对", "换脸", "身份", "identity", "face")),
    ("outfit_consistency", ("衣服", "服装", "配色", "妆造", "outfit")),
    ("prop_structure", ("道具", "法宝", "结构", "件数", "特效", "prop")),
    ("scene_drift", ("场景", "光位", "背景", "环境", "scene")),
    ("style_drift", ("画风", "风格", "style")),
    ("temporal", ("接缝", "时序", "闪烁", "跳切", "flicker", "seam", "temporal")),
    ("backend_migration", ("后端迁移", "管线迁移", "backend_migration", "pipeline_upgrade")),
    ("reference_crop", ("参考图", "裁切", "crop")),
    ("prompt_conflict", ("prompt 冲突", "提示词冲突", "词冲突", "prompt conflict")),
)

# ── 音色一致性契约 ──────────────────────────────────────────────────────────
VOICE_KEY_FIELD = "voice_key"
VOICE_KEY_LEGACY_FIELD = "音色键"
VOICE_KEY_PLACEHOLDER_SUFFIX = "_placeholder"
EMOTION_FLOW_FIELD = "emotion_flow"

# ── 制作模式 ──────────────────────────────────────────────────────────────
# 2026-07-10 默认改为「混合自动路由」：项目级只锁“时间基准先行”，再按镜头分流。
# 可见口型对白走表演音轨/导引音轨或“基础视频→后期表演驱动”；旁白/内心/口外音
# 只用无音频时长估算锁节奏；动作/空镜/蒙太奇画面先行；原生音画仍逐镜显式落合同。
# 三种旧模式保留为用户显式固定策略，不静默迁移既有 `_设置.md`。
PRODUCTION_MODE_DEFAULT = "混合自动路由"

# ── 视觉风格 ──────────────────────────────────────────────────────────────
STYLE_CONTRACT_FIELDS = ("风格名", "视觉基调", "镜头与构图", "光色策略", "运动边界", "风格禁忌")
CINEMATIC_CONTRACT_FIELDS = ("摄影基调", "镜头焦段", "光源动机", "色彩策略", "运镜边界", "真实感禁忌")
VISUAL_CONTRACT_FIELDS = ("色调基线", "场景光位锚", "场景轴线视线", "角色状态演进", "景别阶梯")
SPATIAL_ANCHOR_FIELD = "spatial_anchor"
IDENTITY_ANCHOR_POINTS_FIELD = "identity_anchor_points"

# ── 镜头类型 ──────────────────────────────────────────────────────────────
SHOT_TYPE_KEYWORDS = (
    ("fight_exchange", ("打斗", "搏斗", "交手", "格挡", "出拳", "挥剑", "命中", "受击", "撞击", "掌风", "刀光", "fight", "combat", "hit")),
    ("mount_ride", (
        "御兽", "骑乘", "骑兽", "坐骑", "灵兽", "妖兽", "骑马", "骑狼", "骑虎", "骑龙", "兽背",
        "mount ride", "riding beast", "mounted",
    )),
    ("road_vehicle", (
        "汽车", "轿车", "出租车", "网约车", "警车", "救护车", "摩托", "电动车", "公交车", "地铁进站",
        "开车", "驾驶", "方向盘", "车道", "变道", "刹车", "急刹", "追车", "车流", "高架", "公路",
        "car", "taxi", "police car", "motorcycle", "driving", "traffic", "lane", "brake", "car chase",
    )),
    ("vehicle_ride", (
        "马车", "车驾", "车队", "车轮", "车夫", "缰绳", "马匹拉车", "载具行进", "驾驶马车",
        "carriage", "wagon", "chariot", "vehicle ride",
    )),
    ("vessel_flight", (
        "飞舟", "灵舟", "云舟", "法舟", "飞梭", "御物飞行", "飞行法器", "御舟", "空中舟",
        "flying vessel", "airship", "flying boat",
    )),
    ("chase", ("追逐", "追赶", "追杀", "奔逃", "逃跑", "追上", "紧追", "chase", "running away")),
    ("stealth_stalk", (
        "尾随", "跟踪", "潜入", "潜行", "躲藏", "偷窥", "窥视", "门缝", "暗处", "暗影", "脚步声",
        "走廊尽头", "手电", "手电光", "光束扫过", "stalk", "stalking", "stealth", "sneak", "shadow",
    )),
    ("flight", (
        "御剑", "御剑飞行", "飞行", "凌空", "腾空", "腾云", "驾雾", "腾云驾雾", "掠空", "掠过云",
        "飞掠", "坠落", "飞檐", "云海穿行", "空中追逐", "剑光飞行", "flight", "flying", "cloud riding",
        "sword flight",
    )),
    ("reveal_reaction_chain", ("真相揭示", "身份曝光", "身份揭露", "掉马", "马甲暴露", "真实身份", "当众揭穿", "揭穿", "揭露", "证据链", "血书", "遗诏", "密信", "内鬼", "身世", "认亲", "reveal", "identity reveal")),
    ("public_confrontation", ("公开对质", "当众对质", "公堂", "朝堂", "审讯", "逼问", "盘问", "质问", "谈判", "交易", "交涉", "智斗", "权谋", "当众打脸", "反将一军", "confrontation", "interrogation", "negotiation")),
    ("dialogue_shot_reverse", ("对话反打", "正反打", "反打", "过肩", "对视", "视线对位", "台词", "dialogue", "shot reverse", "ots", "eyeline")),
    ("dialogue_closeup", ("说话特写", "口型", "嘴部", "近景说话", "lip-sync", "mouth", "close-up dialogue")),
    ("tribulation_breakthrough", (
        "渡劫", "天劫", "雷劫", "天雷", "雷云", "劫雷", "破境", "突破", "境界突破", "光柱冲天",
        "金丹", "元婴", "化神", "晋升境界", "heavenly tribulation", "breakthrough", "light pillar",
    )),
    ("meditation_cultivation", (
        "打坐", "静坐", "入定", "冥想", "闭关", "吐纳", "调息", "运功", "周天", "内视", "修炼", "蒲团",
        "灵气入体", "气海", "丹田", "meditation", "cultivation meditation", "breathing exercise",
    )),
    ("dual_cultivation", (
        "双修", "合修", "共修", "双人修炼", "灵力交汇", "阴阳调和", "疗伤合修", "掌心相抵",
        "dual cultivation", "paired cultivation", "energy circulation between two",
    )),
    ("alchemy_forging", (
        "炼丹", "丹炉", "开炉", "成丹", "丹药", "药材入炉", "火候", "炼器", "铸剑", "锻炉", "淬炼",
        "法器出炉", "alchemy", "pill refining", "forging", "furnace",
    )),
    ("array_ritual", (
        "阵法", "法阵", "大阵", "阵图", "起阵", "破阵", "阵眼", "符文", "结界", "封印", "祭坛",
        "传送阵", "ritual array", "magic circle", "formation", "seal",
    )),
    ("soul_manifestation", (
        "神魂", "神识", "元神", "元神出窍", "魂魄", "魂体", "夺舍", "夺体", "搜魂", "识海",
        "灵魂出窍", "二我", "spirit soul", "nascent soul", "soul possession",
    )),
    ("realm_portal", (
        "穿越", "魂穿", "身穿", "穿到", "醒来在", "异界", "时空裂缝", "传送门", "传送阵", "秘境入口",
        "遗迹入口", "跨界", "portal", "transmigration", "isekai", "secret realm entrance",
    )),
    ("contract_summon", (
        "契约灵兽", "灵兽契约", "血契", "认主", "召唤", "召唤阵", "召唤兽", "魔兽契约", "法灵",
        "契约印记", "契约成立", "summon", "contract beast", "binding mark",
    )),
    ("talent_test", (
        "测灵", "测灵石", "灵根测试", "资质测试", "天赋测试", "觉醒仪式", "血脉觉醒", "武魂觉醒",
        "水晶柱", "天赋等级", "测试台", "talent test", "bloodline awakening", "spirit root",
    )),
    ("magic_burst", ("法术", "符阵", "符纹", "灵光", "灵力", "爆发", "雷劫", "雷落", "光束", "剑气", "护盾", "阵法", "magic", "burst", "spell")),
    ("screen_insert", (
        "手机屏幕", "手机界面", "聊天记录", "短信", "来电", "通话界面", "定位", "转账", "付款码",
        "电脑屏幕", "监控画面", "监控回放", "CCTV", "时间码", "弹窗", "录音波形", "邮件界面",
        "phone screen", "chat log", "text message", "computer screen", "surveillance footage", "cctv",
    )),
    ("evidence_search", (
        "搜证", "线索", "物证", "证物", "证物袋", "血迹", "指纹", "脚印", "监控证据", "档案", "翻找",
        "搜查", "现场勘查", "照片墙", "线索板", "clue", "evidence", "crime scene", "fingerprint", "blood stain",
    )),
    ("kiss_or_near_kiss", (
        "接吻", "亲吻", "吻别", "吻住", "额头吻", "脸颊吻", "唇边停住", "差点吻上", "近吻", "轻吻",
        "kiss", "kissing", "near kiss", "forehead kiss", "cheek kiss",
    )),
    ("hug_or_pull", ("拥抱", "抱住", "拉扯", "拉住", "抓腕", "拽住", "推开", "扯住", "拉袖", "tug", "pull", "grab", "hug")),
    ("intimate_interaction", ("牵手", "靠近", "亲密", "搀扶", "扶住", "抚脸", "扶肩", "贴近", "疗伤", "intimate", "touch")),
    ("relationship_turn", ("告白", "表白", "承认心意", "心动", "定情", "决裂", "分手", "误会爆发", "反目", "和解", "破镜重圆", "救赎", "互相救场", "吃醋", "护短", "原谅", "relationship turn", "confession", "reconciliation")),
    ("multi_character_same_frame", ("多人同框", "双人同框", "两人同框", "三人同框", "同框", "同画面", "two-shot", "group shot")),
    ("ensemble_blocking", ("群像", "群戏", "群臣", "门徒", "人群", "围观", "队列", "站位", "多人站位", "围住", "围堵", "众人", "ensemble", "crowd")),
    ("multi_person_blocking", ("多人", "三人", "四人", "multi-person", "blocking")),
    ("empty_establishing", ("空镜", "转场", "远景", "氛围", "环境", "establishing", "ambience", "empty")),
)

SPECIAL_TEMPLATE_SHOT_TYPES = (
    "fight_exchange", "chase", "flight", "mount_ride", "vehicle_ride", "vessel_flight",
    "road_vehicle", "stealth_stalk", "screen_insert", "evidence_search",
    "tribulation_breakthrough", "meditation_cultivation", "dual_cultivation", "alchemy_forging", "array_ritual", "soul_manifestation",
    "realm_portal", "contract_summon", "talent_test",
    "dialogue_shot_reverse", "magic_burst",
    "reveal_reaction_chain", "public_confrontation", "relationship_turn",
    "kiss_or_near_kiss", "hug_or_pull", "intimate_interaction", "multi_character_same_frame",
    "ensemble_blocking", "multi_person_blocking",
)

# 高物理风险/高运动模板：人物姿态一动就崩、接触/遮挡靠帧间插值才稳。这些镜若后端吃不下
# 首尾/中段锚帧，安全网（双帧/多帧插值）会静默失效 → 帧能力不匹配从 WARN 升 BLOCK。
# 单一真值源：anchor_planner（排锚帧密度）与 gate（帧能力闸门）共用，避免两处各定义一份漂移。
HIGH_MOTION_TEMPLATES = frozenset({
    "fight_exchange", "chase", "magic_burst", "flight",
    "mount_ride", "vehicle_ride", "vessel_flight", "road_vehicle", "stealth_stalk",
    "tribulation_breakthrough", "array_ritual", "soul_manifestation", "realm_portal", "contract_summon",
    "kiss_or_near_kiss", "hug_or_pull", "intimate_interaction", "dual_cultivation",
})

# 近景表情跨度档（角色脸的情绪从起到止跨几档）。单一真值源：storyboard.continuity.expression_span
# 与 gate 的「大表情近景必须首尾双帧」闸门共用。`大`=跨情绪（平静→爆哭/隐忍→暴怒），是脸被表情
# 带着重画的头号根因，必须走 frames2video 首尾双帧只插值或 MCU 保真实现。
EXPRESSION_SPAN_VALUES = ("微", "中", "大")
EXPRESSION_SPAN_BIG = "大"

# 近景微表情节拍（FACS/AU 级）。`expression_span` 锁情绪跨度，但近景观众看的是肌肉级微表情——
# 只写"愤怒/隐忍"会出空洞脸或被模型重画。近景/特写人物镜应在 prompt 写一条 `微表情节拍`，用
# FACS Action Unit 级可见线索描述本镜表情的起→止（与峰值），`expression_span=大` 时首帧=起 AU 组、
# 尾帧=止 AU 组，走首尾双帧只插值（锁脸不锁情）。表情库可用 GPT Image 2 原生 expression-sheet
# 以正面脸锚为母图一次性派生同源多情绪。AU 术语优先英文（FACS 最稳），中文给口语化等义。
MICRO_EXPRESSION_FIELD = "微表情节拍"  # storyboard.continuity / 逐镜 prompt 的字段名（单一真值源）
FACS_AU_REGIONS = {
    "brow": ("AU1 inner-brow raise", "AU2 outer-brow raise", "AU4 brow lower/furrow"),
    "eye": ("AU5 upper-lid raise", "AU6 cheek raise", "AU7 lid tighten", "gaze focus", "welling tears"),
    "nose_cheek": ("AU9 nose wrinkle", "AU11 nasolabial deepen"),
    "mouth": ("AU12 lip-corner pull", "AU14 dimpler", "AU15 lip-corner depress",
              "AU17 chin raise", "AU23 lip tighten", "AU24 lip press"),
    "micro_motion": ("held breath", "nostril flare", "throat swallow", "jaw micro-tremor"),
}

# ── 运镜词典（中→英→[速度+方向+起止点] 槽位 + 自由文本触发词）──────────────────────────────
# 把运镜从"只有关键词"升级成结构化：每条带 en（喂英文 prompt）+ slots（速度/方向/起止点该填什么）
# + triggers（自由文本里的同义触发子串，让分镜散文「推近/拉远/横摇」也能归一到本词典）。
# 动作镜 prompt 应从这里取词并填槽（Veo/即梦运镜段是传达情绪与速度感最强的工具），而非自由散文。
# 消费方：n2d_logic.normalize_camera_move() → gate.check_video_clip_prompt_section ⑤运镜结构化（WARN）。
# 视觉参考图/结构化 manifest：skills/n2d/references/运镜/manifest.json。
# 大体积 animated WebP 走内容寻址 R2 + 用户缓存；本地 contact sheet 保证离线可理解。
CAMERA_MOVE_LEXICON = {
    "推镜头": {"en": "dolly in", "slots": ("speed", "end_size"), "triggers": ("推镜", "推近", "前推", "镜头前推", "推进", "dolly in", "push in")},
    "拉镜头": {"en": "dolly out", "slots": ("speed", "end_size"), "triggers": ("拉镜", "拉远", "后拉", "后移", "镜头后移", "dolly out", "pull back")},
    "摇镜头": {"en": "pan / tilt", "slots": ("speed", "direction"), "triggers": ("摇镜", "横摇", "上摇", "下摇", "左摇", "右摇", "镜头上摇", "镜头下摇", "镜头左摇", "镜头右摇", "pan", "tilt")},
    "移镜头": {"en": "tracking / truck", "slots": ("speed", "direction"), "triggers": ("移镜", "平移", "横移", "侧移", "左移", "右移", "镜头左移", "镜头右移", "tracking", "truck")},
    "升降": {"en": "crane / pedestal", "slots": ("speed", "direction", "end_height"), "triggers": ("升降", "升镜", "降镜", "上升", "下降", "镜头上升", "镜头下降", "crane", "pedestal", "jib")},
    "变焦": {"en": "zoom", "slots": ("speed", "end_size"), "triggers": ("变焦", "zoom")},
    "变焦推进": {"en": "zoom in", "slots": ("speed", "end_size"), "triggers": ("变焦推进", "zoom in")},
    "变焦拉远": {"en": "zoom out", "slots": ("speed", "end_size"), "triggers": ("变焦拉远", "zoom out")},
    "柯克变焦": {"en": "dolly zoom / vertigo effect", "slots": ("speed", "end_size", "background_scale"), "triggers": ("柯克变焦", "滑动变焦", "希区柯克变焦", "dolly zoom", "vertigo effect")},
    "环绕": {"en": "orbit / circular (360°)", "slots": ("speed", "direction", "arc"), "triggers": ("环绕", "环绕拍摄", "绕拍", "360", "orbit", "circular")},
    "跟拍": {"en": "following / tracking follow", "slots": ("speed", "direction"), "triggers": ("跟拍", "跟随", "跟随拍摄", "跟移", "following", "follow shot")},
    "第一视角": {"en": "first-person POV", "slots": ("speed", "direction"), "triggers": ("第一视角", "主观视角", "POV", "fpv", "first-person")},
    "甩镜": {"en": "whip pan", "slots": ("direction",), "triggers": ("甩镜", "甩动", "whip")},
    "冲击变焦": {"en": "crash zoom", "slots": ("end_size",), "triggers": ("冲击变焦", "急推急拉", "crash zoom")},
    "手持晃动": {"en": "handheld shake", "slots": ("strength",), "triggers": ("手持", "手持拍摄", "晃动", "晃镜", "handheld", "shaky")},
    "弧线运镜": {"en": "180-degree arc shot", "slots": ("direction", "start_subject", "end_subject"), "triggers": ("弧线", "弧形", "arc shot", "arc move")},
    "无人机航拍": {"en": "aerial drone shot", "slots": ("speed", "direction", "end_height"), "triggers": ("无人机", "高空航拍", "航拍", "drone", "aerial")},
    "无人机升起": {"en": "aerial drone ascend", "slots": ("speed", "end_height"), "triggers": ("无人机升起", "drone ascend", "aerial ascend")},
    "盘旋抬升": {"en": "spiral crane up", "slots": ("speed", "direction", "arc", "end_height"), "triggers": ("盘旋抬升", "螺旋上升", "spiral up", "spiral crane up")},
    "盘旋下降": {"en": "spiral crane down", "slots": ("speed", "direction", "arc", "end_height"), "triggers": ("盘旋下降", "螺旋下降", "spiral down", "spiral crane down")},
    "滚筒旋转": {"en": "barrel roll / camera roll", "slots": ("speed", "direction", "roll_angle"), "triggers": ("滚筒旋转", "镜头滚转", "滚转", "翻滚镜头", "barrel roll", "camera roll")},
}
# 速度词槽候选（填进 slots.speed），中→英；含口语别名（normalize_camera_move 按子串匹配）。
CAMERA_SPEED_WORDS = {
    "缓慢": "slow", "匀速": "steady", "快速": "rapid", "急速冲击": "fast snap", "轻微": "gentle",
    "急速": "fast snap", "急": "fast snap", "慢": "slow", "微": "gentle",
}
# 静止机位词（不属运动，但属合法的"已声明运镜"，不该被判"未用结构化运镜"）。
STATIC_CAMERA_WORDS = ("固定", "静止", "不动", "锁定机位", "定镜", "无运镜", "static", "fixed", "locked")

CAMERA_MOVE_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "references" / "运镜" / "manifest.json"


def _unique_str_tuple(values):
    out = []
    seen = set()
    for value in values or ():
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return tuple(out)


def _load_camera_move_manifest():
    try:
        return json.loads(CAMERA_MOVE_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": 0, "moves": []}


def _manifest_media_ref(entry):
    media = entry.get("media")
    if not isinstance(media, dict):
        return None
    ref = {
        "id": str(entry.get("id") or "").strip(),
        "preview": str(media.get("preview") or "").strip(),
        "contact_sheet": str(media.get("contact_sheet") or "").strip(),
        "source": str(media.get("source") or "").strip(),
    }
    remote = media.get("remote")
    if isinstance(remote, dict):
        ref["remote"] = {
            key: remote[key]
            for key in ("filename", "url", "object_key", "sha256", "bytes", "content_type")
            if remote.get(key) not in (None, "")
        }
    return {k: v for k, v in ref.items() if v}


def _extend_static_camera_words_from_manifest(words):
    extra = []
    for entry in CAMERA_MOVE_MANIFEST.get("moves") or []:
        if not isinstance(entry, dict) or str(entry.get("lexicon_kind") or "") != "static":
            continue
        extra.extend(entry.get("aliases_zh") or ())
        extra.extend(entry.get("aliases_en") or ())
        extra.append(entry.get("name_zh") or "")
        extra.append(entry.get("name_en") or "")
    return _unique_str_tuple(tuple(words) + tuple(extra))


def _apply_camera_move_manifest():
    for entry in CAMERA_MOVE_MANIFEST.get("moves") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("lexicon_kind") or "") == "static":
            continue
        key = str(entry.get("lexicon_key") or entry.get("name_zh") or "").strip()
        if not key:
            continue
        trigger_values = [
            key,
            entry.get("name_zh"),
            entry.get("name_en"),
            *(entry.get("aliases_zh") or ()),
            *(entry.get("aliases_en") or ()),
        ]
        slots = _unique_str_tuple(entry.get("slots") or ())
        triggers = _unique_str_tuple(trigger_values)
        media_ref = _manifest_media_ref(entry)
        existing = CAMERA_MOVE_LEXICON.get(key)
        if existing:
            merged = dict(existing)
            merged["slots"] = _unique_str_tuple(tuple(existing.get("slots") or ()) + slots)
            merged["triggers"] = _unique_str_tuple(tuple(existing.get("triggers") or ()) + triggers)
            if media_ref:
                merged["media_refs"] = list(existing.get("media_refs") or []) + [media_ref]
            for field in ("category", "risk_level"):
                if field not in merged and entry.get(field):
                    merged[field] = entry.get(field)
            CAMERA_MOVE_LEXICON[key] = merged
            continue
        spec = {
            "en": str(entry.get("name_en") or key),
            "slots": slots,
            "triggers": triggers,
        }
        for field in ("category", "risk_level", "prompt_template"):
            if entry.get(field):
                spec[field] = entry.get(field)
        if media_ref:
            spec["media_refs"] = [media_ref]
        CAMERA_MOVE_LEXICON[key] = spec


CAMERA_MOVE_MANIFEST = _load_camera_move_manifest()
STATIC_CAMERA_WORDS = _extend_static_camera_words_from_manifest(STATIC_CAMERA_WORDS)
_apply_camera_move_manifest()

# ── 运动强度连续档（替代 HIGH_MOTION_TEMPLATES 二分的细粒度补充）──────────────────────────────
# HIGH_MOTION_TEMPLATES 是「是否高风险」的二分闸；这里给 0–3 连续档，供 prompt 调 motion strength/
# cfg 与下游采样密度参考（强动作降 cfg/motion strength 换脸稳是 2026 公认做法）。1=轻微局部动，
# 2=明显全身/主体动，3=高速大幅动作(打斗/追逐/飞行/御兽/载具/潜行峰值)。0=静帧/空镜。
MOTION_INTENSITY_LEVELS = (0, 1, 2, 3)
MOTION_INTENSITY_BY_TEMPLATE = {
    "fight_exchange": 3, "chase": 3, "flight": 3,
    "mount_ride": 3, "vehicle_ride": 3, "vessel_flight": 3,
    "road_vehicle": 3, "stealth_stalk": 3,
    "tribulation_breakthrough": 3, "array_ritual": 2, "soul_manifestation": 2,
    "meditation_cultivation": 1, "dual_cultivation": 1,
    "realm_portal": 2, "contract_summon": 2, "alchemy_forging": 2, "talent_test": 1,
    "magic_burst": 3,
    "kiss_or_near_kiss": 2, "hug_or_pull": 2, "intimate_interaction": 2,
    "evidence_search": 1, "screen_insert": 0,
    "dialogue_closeup": 1, "dialogue_shot_reverse": 1,
    "empty_establishing": 0,
}

# ── 负向身份锁词表（动作镜默认注入的 negative prompt）──────────────────────────────────────
# 高动态镜身份最常见崩法：脸/下巴漂移、服装变色、配饰消失、年龄漂移、背景闪烁。Kling 官方给的
# 负向词把这些显式钉死。prompt 生成器对吃身份的镜默认拼上（单一真值源，避免各处各写一份）。
IDENTITY_LOCK_NEGATIVE_TERMS = (
    "de-aging", "morphing features", "shifting jawline", "changing face shape",
    "changing clothes", "color shift", "disappearing accessories",
    "extra limbs", "extra fingers", "flickering background", "identity drift",
)

# ── 题材母题(motif) ──────────────────────────────────────────────────────────
# 穿越/系统流等爽文里高频复现的"母题场景"（系统面板出现/升级/签到/抽奖/爆装备）：相对固定的
# 场景模板 + 每次出现带成长属性（面板进化、等级只增不减）。motif 是 n2d 线内一等概念，靠
# motif_registry.json（数据真值）+ 专项镜头模板库.md 的 motif 模板（镜头契约）+ asset_registry 的
# VFX lifecycle（成长状态机·只进不退）+ n2d-compose 期 overlay（清晰数值文字层）贯穿全流程。
# 检测特征是单一真值源：split/分镜检测器（motif_detector）与 gate 共用，避免两处各定义一份漂移。
MOTIF_ID_PREFIX = "MOTIF_"
# 题材 → 关键词。检测器据此识别题材；命中关键词数 ≥ GENRE_MIN_HITS 即判定，多题材取命中最多者。
GENRE_KEYWORDS = (
    ("系统流", ("系统", "面板", "宿主", "绑定", "签到", "任务奖励", "抽奖", "属性面板", "经验值", "升级", "金手指", "叮——", "恭喜宿主")),
    ("穿越", ("穿越", "重生", "魂穿", "异世界", "回到古代", "前世", "上一世", "醒来发现", "莫名来到")),
    ("修仙", ("修仙", "修真", "灵气", "渡劫", "金丹", "元婴", "筑基", "境界", "御剑", "宗门", "灵根")),
    ("都市", ("总裁", "豪门", "霸总", "微信", "写字楼", "董事长", "集团", "都市")),
    ("宫斗", ("皇上", "娘娘", "嫔妃", "后宫", "册封", "贵妃", "冷宫", "凤印", "圣旨")),
    ("赘婿", ("赘婿", "上门女婿", "岳父", "丈母娘", "入赘", "废物女婿")),
    ("战神", ("战神", "兵王", "退役", "佣兵", "龙组", "镇国", "特种兵")),
)
GENRE_MIN_HITS = 2
# 母题类型 → 关键词。检测器在分镜/正文里据此识别母题桥段。系统面板是首个落地样板；
# 后续 level_up/signin/gacha/loot/cheat 只在此加枚举值 + motif_registry 配置，不改架构。
MOTIF_TYPE_KEYWORDS = (
    ("system_panel", ("系统面板", "面板", "属性栏", "状态栏", "属性面板", "数据面板", "光幕", "虚拟屏", "信息面板", "等级", "经验条", "属性值")),
    ("level_up", ("升级", "等级提升", "突破", "进阶", "level up", "境界提升", "属性提升", "经验满")),
    ("system_refresh", ("系统刷新", "系统更新", "系统升级", "新功能解锁", "系统进化", "面板进化", "系统重启")),
    ("signin", ("签到", "每日签到", "连续签到", "签到奖励", "打卡")),
    ("gacha", ("抽奖", "抽卡", "转盘", "开箱", "幸运抽取", "十连")),
    ("loot", ("爆装备", "掉落", "爆出", "获得装备", "开宝箱", "战利品", "掉宝")),
    ("cheat", ("金手指", "外挂", "作弊器", "系统绑定", "激活系统", "系统降临")),
)
MOTIF_TYPE_MIN_HITS = 1
# 母题首样板：系统面板。绑定的 VFX 资产 id（asset_registry 里的成长 VFX，lifecycle 锁档位只进不退）。
SYSTEM_PANEL_MOTIF_ID = "MOTIF_系统面板"
SYSTEM_PANEL_VFX_ID = "VFX_系统面板"
SYSTEM_PANEL_TEMPLATE_ID = "system_panel"
# motif 成长状态机：这些字段只增不减（机检退级=block），与 asset_lifecycle 的 lifecycle 单调校验同源。
MOTIF_MONOTONIC_FIELDS_DEFAULT = ("level", "panel_tier")
# system_panel overlay 文字层默认字段（n2d-compose render_panel 据此渲染清晰数值，AI 只出空光幕底）。
SYSTEM_PANEL_OVERLAY_FIELDS = ("title", "level", "attrs")

# ── 拆集边界启发式词典（题材可扩展·单一真值源）─────────────────────────────
# split_novel.py（粗切）与 boundary_audit.py（预筛）共用：识别"可作粗胚右边界的强钩"+
# "冲突→爽点/反转"闭环信号。仅启发式，最终钩力/闭环由人或 LLM 精修判定。
# 题材词面在 base 之上按命中题材合并——治"词典只覆盖古言爽文/修仙，女频情感/悬疑/都市退化成无闭环"。
# 默认（未识别题材）= base ∪ 古装动作，复刻历史正则覆盖，保证旧项目行为不变。
# 取值键与 GENRE_KEYWORDS 题材键松对齐；女频/悬疑等可经 _设置.md `题材` 自由文本子串命中。

# 集尾强钩（句尾收束信号）：悬念/惊叹/省略/破折号 + 反转/突变/疑问/紧迫词（题材无关，恒并入）。
BOUNDARY_STRONG_END_BASE = (
    "？", "！", "…", "——", "?", "!",
    "竟然", "竟", "居然", "原来", "没想到", "不料", "岂料",
    "突然", "猛地", "猛然", "骤然", "霎时", "忽然",
    "难道", "莫非", "是谁", "什么", "为什么", "怎么", "凭什么",
    "来了", "出事", "不好了", "糟了", "完了",
)
# 冲突信号（base：通用对抗/危机·题材无关）
BOUNDARY_CONFLICT_BASE = (
    "逼", "威胁", "羞辱", "责罚", "围住", "拦住", "抓住", "质问", "审问",
    "怒", "恨", "怕", "惊", "哭", "跪", "危", "险", "死", "陷害", "冤", "背叛", "惩罚",
)
# 爽点/反转信号（base：通用反击/翻盘/揭示·题材无关）
BOUNDARY_PAYOFF_BASE = (
    "反击", "还手", "夺回", "臣服", "震住", "压住", "赢", "胜", "救", "成功",
    "冷笑", "一笑", "抬头", "睁眼", "原来", "竟然", "竟", "居然", "没想到",
    "不料", "岂料", "突然", "猛地", "反而", "却",
)

# 题材扩展词面：base ∪ 命中题材桶。
BOUNDARY_GENRE_LEXICON = {
    # 古装动作（宫斗/修仙/武侠/战神古装向）：原正则覆盖的古言爽文/打斗词面（=历史默认）。
    "古装动作": {
        "strong_end": ("妖", "斩了", "破阵"),
        "conflict": ("冷宫", "刀", "剑", "血", "毒", "妖", "怪", "追", "逃", "抢", "夺", "打", "杀"),
        "payoff": ("夺回", "跪倒", "跪下", "觉醒", "突破", "升级", "斩", "破阵", "出关", "破境"),
    },
    # 女频情感/言情/虐恋/甜宠/霸总：误会/心动/醋意/告白/虐恋/HE。
    "女频情感": {
        "strong_end": ("心动了", "脸红了", "她哭了", "他走了", "分手吧", "我喜欢你", "原来你也"),
        "conflict": ("误会", "争吵", "冷战", "吃醋", "醋意", "心碎", "失望", "决裂", "分手",
                     "退婚", "嫉妒", "猜忌", "绿茶", "白莲", "抢走", "插足", "误解", "怀疑"),
        "payoff": ("告白", "表白", "和好", "心动", "脸红", "护住", "宠", "撑腰", "复合",
                   "在一起", "拥抱", "破镜重圆", "释怀", "原谅", "心软", "动情"),
    },
    # 悬疑/推理/犯罪/探案：线索/真凶/反转/不在场。
    "悬疑": {
        "strong_end": ("是凶手", "另有其人", "他没死", "线索断了", "真相是", "活着"),
        "conflict": ("尸体", "凶手", "失踪", "被杀", "命案", "嫌疑", "跟踪", "陷阱",
                     "栽赃", "灭口", "勒索", "绑架", "密室", "作案"),
        "payoff": ("真凶", "破案", "真相", "证据", "识破", "反杀", "翻案", "锁定",
                   "招供", "落网", "反转", "水落石出"),
    },
    # 都市/职场/逆袭/赘婿/战神现代向：身份反差/打脸/逆袭。
    "都市": {
        "strong_end": ("打脸", "是大佬", "真实身份", "后台竟是"),
        "conflict": ("看不起", "嘲讽", "针对", "排挤", "刁难", "解雇", "下马威",
                     "踩", "欺压", "讽刺", "刁蛮"),
        "payoff": ("打脸", "逆袭", "真实身份", "扮猪吃虎", "碾压", "震惊全场",
                   "封神", "翻盘", "实力", "曝光", "镇住"),
    },
}

# 题材自由文本子串 → lexicon 桶（别名归一）。同一 genre_text 可命中多桶，全部并入。
BOUNDARY_GENRE_ALIASES = (
    (("女频", "情感", "言情", "虐恋", "甜宠", "恋爱", "霸总", "总裁", "豪门", "宠妻", "婚"), "女频情感"),
    (("悬疑", "推理", "犯罪", "探案", "罪案", "刑侦", "灵异", "无限"), "悬疑"),
    (("都市", "职场", "逆袭", "赘婿", "战神", "兵王", "高武"), "都市"),
    (("宫斗", "宅斗", "后宫", "古言", "古装", "宫廷"), "古装动作"),
    (("修仙", "修真", "玄幻", "仙侠", "武侠", "洪荒"), "古装动作"),
)


def boundary_buckets(genre_text):
    """题材文本 → 命中的 lexicon 桶名列表；未命中返回历史默认 ['古装动作']。"""
    text = (genre_text or "").strip().lower()
    hits = []
    for needles, bucket in BOUNDARY_GENRE_ALIASES:
        if any(n in text for n in needles) and bucket not in hits:
            hits.append(bucket)
    return hits or ["古装动作"]


def boundary_lexicon(genre_text=None):
    """返回 (strong_end, conflict, payoff) 三元组：base ∪ 命中题材桶。

    供 split_novel / boundary_audit 构建正则。未识别题材时复刻历史覆盖（base ∪ 古装动作）。
    """
    buckets = boundary_buckets(genre_text)
    strong = list(BOUNDARY_STRONG_END_BASE)
    conflict = list(BOUNDARY_CONFLICT_BASE)
    payoff = list(BOUNDARY_PAYOFF_BASE)
    for b in buckets:
        spec = BOUNDARY_GENRE_LEXICON.get(b, {})
        strong += list(spec.get("strong_end", ()))
        conflict += list(spec.get("conflict", ()))
        payoff += list(spec.get("payoff", ()))
    # 去重保序
    dedup = lambda xs: list(dict.fromkeys(xs))
    return dedup(strong), dedup(conflict), dedup(payoff)


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
EMOTION_FLOW_KIND = "n2d_emotion_flow"
LORA_VALIDATION_REPORT_KIND = "n2d_lora_validation_report"
SKILL_UPDATE_PLAN_KIND = "n2d_skill_update_plan"
SKILL_UPDATE_SNAPSHOT_KIND = "n2d_skill_update_snapshot"
CONSISTENCY_FINDINGS_KIND = "n2d_consistency_findings"
IMAGE_QC_REPORT_KIND = "n2d_image_qc"
GATE_FINDINGS_KIND = "n2d_gate_findings"
CONSISTENCY_LEDGER_KIND = "n2d_consistency_ledger"
CONSISTENCY_POLICY_LATTICE_KIND = "n2d_consistency_policy_lattice"
CONSISTENCY_DEPENDENCY_GRAPH_KIND = "n2d_consistency_dependency_graph"
INTENTIONAL_DISCONTINUITY_MANIFEST_KIND = "n2d_intentional_discontinuity_manifest"
CONTRACT_INHERITANCE_KIND = "n2d_contract_inheritance"
IDENTITY_DRIFT_REPORT_KIND = "n2d_identity_drift_report"
IDENTITY_VOICE_DRIFT_REPORT_KIND = "n2d_identity_voice_drift_report"
IDENTITY_VOICE_PRINT_REPORT_KIND = "n2d_identity_voice_print_report"
PRODUCTION_EVENT_KIND = "n2d_production_event"
PRODUCTION_DASHBOARD_KIND = "n2d_production_dashboard"
PRODUCTION_ALERTS_KIND = "n2d_production_alerts"
ASSET_PACK_KIND = "n2d_asset_pack"
ASSET_RERUN_PLAN_KIND = "n2d_asset_rerun_plan"
MOTIF_REGISTRY_KIND = "n2d_motif_registry"          # 题材母题数据真值（出图/共享/motif_registry.json）
MOTIF_PLAN_KIND = "n2d_motif_plan"                  # 母题检测建议（生产数据/motif_plan_第N集.{json,md}）
COMBAT_REGISTRY_KIND = "n2d_combat_registry"        # 招式/打斗套路真值（出图/共享/combat_registry.json）
BATCH_QUEUE_KIND = "n2d_batch_queue"
ARTIFACT_LINEAGE_MANIFEST_KIND = "n2d_artifact_lineage_manifest"
PRODUCTION_READINESS_KIND = "n2d_production_readiness"
GATE_POLICY_COVERAGE_KIND = "n2d_gate_policy_coverage"
GENERATION_RECIPE_MANIFEST_KIND = "n2d_generation_recipe_manifest"
GENRE_PACK_KIND = "n2d_genre_pack"
GENRE_PACK_CONTEXT_KIND = "n2d_genre_pack_context"
DIFFERENTIATION_CANDIDATES_KIND = "n2d_differentiation_candidates"
EPISODE_REVIEW_SCORE_KIND = "n2d_episode_review_score"
# 外部投放战绩 JSONL 可复用该 kind；保持无前缀便于非 n2d 工具读取。
GENRE_PERFORMANCE_RECORD_KIND = "genre_performance_record"
LORA_CARD_KIND = "n2d_lora_card"
LORA_DATASET_MANIFEST_KIND = "n2d_lora_dataset_manifest"
LORA_TRAIN_JOB_KIND = "n2d_lora_train_job"
LORA_EXCEPTION_SCOPE_KIND = "n2d_lora_exception_scope"
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

# ── 一致性 lint 共享词表（单一真值源）──────────────────────────────────────────
# 历史上 image_qc / gate / face_drift_risk / shot_risk_audit 各存一份近义词表，成员逐渐
# 漂移 → 同一镜「出图放行 / 质检阻断」口径分裂（const 漂离消费端 bug 家族）。统一收口到这里，
# 消费端一律 import，不得在 .py 内用字面量重新定义同名集合（test_marker_single_source.py 守护）。
# 各集合为历史各副本成员的并集；多主体放行集走「越全越宽松」的安全方向，使 block ⊆ review block。

# 近景大表情触发词（让 AI 重画整张脸 → 表情镜脸漂的强情绪标记）
STRONG_EMOTION_MARKERS = (
    "哭", "泣", "落泪", "含泪", "泪", "怒", "愤", "暴怒", "狂怒", "震惊", "惊恐", "恐惧",
    "狂喜", "大笑", "狂笑", "嘶吼", "咆哮", "嚎", "痛苦", "崩溃", "狰狞", "扭曲", "癫狂",
    "失控", "绝望", "悲恸", "惊愕",
)
# 表情库 / 基础脸锚参考标记（近景大表情角色镜须引用同源参考，否则脸漂）
EXPRESSION_LIB_MARKERS = (
    "face_anchor_refs", "基础脸锚", "脸部特写",
    "表情库", "expressions", "表情_", "_表情", "情绪库", "微表情参考",
)

# 多人同框策略词表（按语义分类；消费端按需 concat）。
# ① 分层/分区/分别出图合成（无持久主体 ID 后端的执行路径）
SPLIT_COMPOSITE_MARKERS = (
    "split_composite", "split_composite_required",
    "regional_construct", "regional_construct_required",
    "shot_reverse_shot_or_split_composite_required",
    "regional-prompt", "region masks",
    "分别出图+合成", "分别出图 + 合成", "分角色出图+合成", "分角色出图 + 合成",
    "分别出图", "分角色出图", "分区构建", "分区逐次构建", "区域构建",
    "empty_plate", "拆成单人镜", "拆单人镜", "单人分层出图", "单人分层",
    "分层合成", "景别分层", "登记降级",
)
# ② 原生持久主体（主体库 / 角色 ID / 多参考绑定后端）
NATIVE_MULTI_SUBJECT_STRATEGY_MARKERS = (
    "主体库", "角色ID", "角色 ID", "Character ID", "persistent subject",
    "原生主体", "多主体", "区域绑定", "Universal Reference",
    "Seedream", "可灵", "Kling", "Sora Cameo", "Nano Banana", "多参考",
)
# ③ 执行策略字段标记（storyboard 里登记的执行路径键）
MULTI_SUBJECT_EXECUTION_STRATEGY_MARKERS = (
    "多人同框执行策略", "multi_subject_strategy", "native_subject_slots",
    "regional_construct_required", "split_composite_required",
    "register_subjects_or_split", "shot_reverse_shot", "same_frame_policy",
)
# ④ 身份槽位标记（每个身份绑画面槽位）
MULTI_SUBJECT_SLOT_MARKERS = (
    "多人同框身份槽位", "身份槽位", "character_slots", "subject_slots",
    "screen_positions", "face_priority",
    "LEFT_SLOT", "RIGHT_SLOT", "FOREGROUND_SLOT", "BACKGROUND_SLOT", "EXTRA_SLOT",
    "画左槽", "画右槽", "前景槽", "后景槽",
)
# ⑤ 画面站位标记（逐角色空间位置）
MULTI_SUBJECT_POSITION_MARKERS = (
    "画左", "画右", "左侧", "右侧", "前景", "后景", "前后景",
    "screen_position", "screen positions", "blocking",
)
# 多人同框「已登记执行策略」放行集 = 分层 + 原生 + 执行策略三类并集。
# image_qc 用它放宽 block、gate 用它判 _has_native_multi_subject_strategy、shot_risk 用它判
# has_multi_subject_strategy —— 三处同源 → block ⊆ review block 结构性成立，不再靠人手同步。
MULTI_SUBJECT_ACCEPTING_MARKERS = (
    SPLIT_COMPOSITE_MARKERS
    + NATIVE_MULTI_SUBJECT_STRATEGY_MARKERS
    + MULTI_SUBJECT_EXECUTION_STRATEGY_MARKERS
)

# ── 镜头不是对视对象铁律（camera-is-not-the-gaze-target·单一真值源）──────────────
# 为防脸漂反复强调「清晰正脸/主检脸/frontal」会把扩散模型带偏成「角色正对镜头摆拍/自拍肖像」，
# 削弱力线/空间关系/真实感（打斗里视线本该锁对手·武器·撞点，而非镜头）。锁脸不放弃，但≠正对镜头。
# 全局负面（非 POV 镜默认注入两个 runner + 建议进 global_style 全集统一负面词）：
CAMERA_GAZE_NEGATIVES = (
    "looking at viewer", "eye contact with camera", "looking into the camera",
    "直视镜头", "看镜头", "对视镜头",
    "portrait pose", "front-facing symmetric stance", "正对镜头摆拍", "肖像摆拍",
    "fashion portrait", "magazine cover pose", "selfie", "自拍感",
)
# POV / 破第四墙 / 对观众压迫感特写 = 唯一例外（此时允许直视镜头）。与 image_qc 审计同源。
CAMERA_GAZE_EXCEPTION_MARKERS = (
    "opponent pov", "camera-as-opponent", "first-person pov", "pov shot", "direct address",
    "fourth wall", "主观镜头", "主观视角", "镜头代表对手", "镜头=对手", "第一人称", "破第四墙",
    "直视镜头=导演意图", "看镜头=导演意图", "对观众压迫", "压迫感特写",
)


def is_camera_gaze_pov_exempt(text: str) -> bool:
    """本镜是否显式声明 POV/破第四墙/对观众特写（→ 允许直视镜头·免「镜头非对视对象」铁律）。纯函数。"""
    t = str(text or "").lower()
    return any(m.lower() in t for m in CAMERA_GAZE_EXCEPTION_MARKERS)


# ── 武器/武技碰撞（weapon-clash·单一真值源）──────────────────────────────────────
# 缺口：打斗常被拆成单人正反打 + 单向命中（A 打中 B），很少出现「双方兵器/武技在画面里硬碰硬相交于
# 一点」的撞点镜（剑刃交击迸火星/格挡较力/双术对冲）。clash 是 **mutual**（力对力·谁都还没落）且
# **face-safe**——构图焦点是**接触点**，脸只需 ¾/侧轮廓非主体，故与脸一致性铁律不冲突，反而正好不需
# 正对镜头。检测命中即在出图侧注入撞点构图、在授权侧提示单独出一帧。melee 与法术对冲都算。
WEAPON_CLASH_MARKERS = (
    "相交", "相击", "相撞", "对撞", "对轰", "硬碰硬", "格挡", "招架", "格开", "架住", "格架",
    "兵器相", "刀剑相", "剑刃相", "刀光剑影", "较力", "顶法", "僵持", "迸火", "火星四溅",
    "劲气对冲", "掌力相抵", "拳掌相接", "兵刃交", "刀枪相", "枪戟相",
    "clash", "parry", "blade lock", "weapon lock", "cross blades", "deflect",
)


def is_weapon_clash_shot(text: str) -> bool:
    """本镜是否为兵器/武技硬碰硬相交的撞点镜（双方武器或两道劲气在接触点相击）。纯函数·可测。

    用于：① 出图侧注入「两兵器相交于焦点·迸火星·力对冲·双方侧轮廓·camera observer·双主体接触非单人正反打」
    构图；② 授权侧提示该镜应单独写 clash_frame / collision_or_apex_frame 撞点帧。face-safe·与脸铁律协同。"""
    t = str(text or "").lower()
    return any(str(m).lower() in t for m in WEAPON_CLASH_MARKERS)


# 出图侧撞点构图指令（runner 注入·正向）：让模型把两件兵器/两道劲气画成在同一接触点硬碰硬。
WEAPON_CLASH_COMPOSE_GUIDANCE = (
    "本镜是兵器/武技对撞镜（含相交/格挡/对轰/较力）：画面焦点 = 双方武器（或两道劲气）在同一接触点"
    "**硬碰硬相交**——迸火星/能量挤压/力的对冲与僵持可见；两件兵器都要清楚入框（这一镜是**双主体接触**，"
    "不是单人正反打）；双方取 ¾ 或侧轮廓（脸非焦点·face-safe·不必正对镜头）；camera=observer 不偏帮任何一方，"
    "机位放在能同时看清两件兵器接触点与力线传递的角度。"
)


# ── 打斗/动作高潮镜·视觉盛宴增强（"经费在燃烧"·单一真值源）────────────────────────────
# 缺口：打斗的电影级制作语言（体积光/大气纵深/环境受力/运动能量）目前主要散落在 `打斗分镜.md`
# 散文示例和 SPECTACLE_ADVISORY_FIELDS（per-clip 建议字段·靠作者誊抄）里——和"看镜头"同一类
# 不可靠链路：作者漏写一个打斗镜，那一镜就平光、平面、零环境反馈，看着"经费没烧"。这里把它兑现成
# **检测到打斗/法术/动作高潮镜就由两个出图 runner 同源注入的保底层**（与 apex_light 协同：plan 字段
# 引导作者、本注入保底；与脸/视线铁律协同：所有特效服务动作与主体可读，不糊脸不盖受力点）。
# 风格中性（只给电影摄影语法·不绑某种 look），与 global_style/风格禁忌 组合后由风格契约收口。
COMBAT_SPECTACLE_MARKERS = (
    "打斗", "交手", "缠斗", "拆招", "出招", "过招", "挥剑", "劈砍", "斩击", "出拳", "出掌",
    "踢腿", "命中", "击中", "接触帧", "撞点", "冲击波", "气浪", "爆发", "炸开", "迸射",
    "震开", "震飞", "击飞", "重创", "破防", "突破", "渡劫", "雷劫", "御剑", "御兽",
    "剑气", "刀气", "掌风", "拳劲", "劲气", "灵力", "法力", "能量", "术法", "法术", "结界",
    "fight_exchange", "magic_burst", "impact_frame", "collision_or_apex", "clash_frame",
    "combat", "punch", "slash", "strike", "impact", "blast", "burst", "shockwave", "spell", "magic",
)


def is_combat_spectacle_shot(text: str) -> bool:
    """本镜是否打斗/法术/动作高潮镜（需要堆视觉盛宴的"经费在燃烧"镜）。纯函数·可测。

    命中 COMBAT_SPECTACLE_MARKERS 或兵器对撞镜即为真。用于两个出图 runner 同源注入
    COMBAT_SPECTACLE_RICHNESS_GUIDANCE（体积光/大气纵深/环境受力/运动能量四层保底层）。"""
    t = str(text or "").lower()
    if any(str(m).lower() in t for m in COMBAT_SPECTACLE_MARKERS):
        return True
    return is_weapon_clash_shot(text)


# 出图侧视觉盛宴注入（runner 注入·正向·四层）：在保住身份与动作可读的前提下，把"经费在燃烧"的
# 电影级动作制作语言堆进打斗镜。分层喂以保密度而不糊成词堆；调色给具体科学方向而非泛 "cinematic" 套词。
#
# ⚠️ 风格自适应（P0-1）：四层「视觉盛宴」此前是**单一写实电影语法**（体积光丁达尔 / motion blur 拖影 /
# 大气透视）。但 `recommend_style` 本身能把本剧定成 二次元赛璐璐 / 水墨国风 / Q版 / 纸片剪影——这些
# 风格**反对**写实体积光与真实 motion blur，硬塞会糊成四不像、和 `global_style/风格禁忌` 打架。
# 故按风格族分流：cinematic（写实/电影/厚涂/国漫写实/暗黑悬疑…）走原写实四层；cel（赛璐璐/二次元/
# 条漫/韩漫/乙女）把 motion blur 换赛璐璐速度线·体积光换硬边卡通光束；ink（水墨）改飞白泼墨气劲·留白
# 纵深；flat（Q版/剪影/定格/低多边形/玩具）改夸张图形化冲击·克制堆料。`COMBAT_SPECTACLE_RICHNESS_GUIDANCE`
# 保留为 cinematic 默认（向后兼容既有 import/测试），新增分流入口 `combat_spectacle_guidance_for_style`。
COMBAT_SPECTACLE_RICHNESS_GUIDANCE = (
    "本镜是打斗/法术/动作高潮镜——在身份与动作可读优先的前提下，按电影级动作大片标准堆视觉信息密度"
    "（\"经费在燃烧\"），分四层落实，特效一律服务动作与主体、绝不糊脸或盖过受力点："
    "① 光：体积光 / 丁达尔光束穿过烟尘或雾气；强逆光 + 边缘轮廓光把主体从压暗环境里拔出来、明暗对比拉大"
    "（拒绝平光）；命中/爆发帧给一束 motivated 强光。"
    "② 纵深：前景放虚焦的余烬/火星/飞尘/断裂物做前景遮挡，中景清晰主体，远景用大气透视压灰——三层纵深拉开空间，别贴成平面。"
    "③ 环境受力：动作让环境有反应——扬尘、碎屑顺受力方向飞溅、地面皲裂/凹陷、气浪掀动布幔草木、火星四溅，"
    "战场可见破坏感与规模感。"
    "④ 运动能量：高速段顺攻击方向给速度线 + 拖影 motion blur；发丝/衣摆/飘带被气流甩动（二级运动）；"
    "命中瞬间呈升格慢放般的张力定格（动态定格·不是平静站姿）。"
    "调色走具体色彩科学（压暗环境、提亮主体、控制高光溢出），避免泛泛\"cinematic/电影感\"套词；色与光遵守本场光位锚与风格禁忌。"
)

_SPECTACLE_CEL_GUIDANCE = (
    "本镜是打斗/法术/动作高潮镜——按二次元/赛璐璐动作番标准堆视觉信息密度（身份与动作可读优先、"
    "绝不糊脸或盖过受力点），分四层落实，全程保持赛璐璐平涂质感、不混入写实胶片颗粒/景深虚焦："
    "① 光：硬边赛璐璐高光 + 强对比投影；光柱/耶稣光做成卡通光束（非写实体积光雾化）；命中/爆发帧给夸张高光爆点。"
    "② 纵深：前景放动态遮挡（飞溅碎片/花瓣/符纸），中景主体清晰，背景用分层平涂或简化——靠分层与对比拉空间，不靠写实大气透视压灰。"
    "③ 环境受力：碎屑/尘片顺受力方向飞溅、地裂、气浪掀动衣摆草木，破坏感用图形化块面处理（漫画式碎裂）。"
    "④ 运动能量：高速段给赛璐璐速度线 / 集中线 / 动势线（非写实长拖影 motion blur）；发丝衣摆飘带被气流甩动（二级运动）；"
    "命中瞬间用冲击星芒 / 震动线 / 动态定格强调张力。"
    "色与光遵守本场光位锚与风格禁忌。"
)

_SPECTACLE_INK_GUIDANCE = (
    "本镜是打斗/法术/动作高潮镜——按水墨写意动作标准堆张力（身份与动作可读优先、绝不糊脸或盖过受力点），"
    "分四层落实，全程保持水墨写意质感、不混入 3D 体积光/写实景深："
    "① 光：以墨色浓淡与留白代替写实布光——主体浓墨实笔拔出、环境淡墨虚化；不用写实体积光丁达尔/胶片高光。"
    "② 纵深：近实远虚靠墨阶与留白（近景浓墨、中景灰墨、远景大面积留白）拉空间，不用写实大气透视/虚焦余烬。"
    "③ 环境受力：以泼墨/飞白/水痕扩散表现气劲冲击——墨点迸溅、纸面气流掀动、笔势带出破坏感，写意而非写实碎屑物理。"
    "④ 运动能量：高速段用飞白笔触/拖墨/笔势走向表现速度（非写实速度线/motion blur）；衣袂发丝以线条动势甩动；"
    "命中瞬间用墨爆/笔锋顿挫定格张力。"
    "色与光遵守本场光位锚与风格禁忌。"
)

_SPECTACLE_FLAT_GUIDANCE = (
    "本镜是打斗/法术/动作高潮镜——按夸张风格化卡通标准堆张力（身份与动作可读优先、绝不糊脸或盖过受力点），"
    "克制堆料、避免与平面/夸张风格打架，分四层落实，保持本风格平面/Q版/玩具质感、绝不注入写实电影摄影语言"
    "（体积光/景深虚焦/真实 motion blur）："
    "① 光：简化硬光 + 大色块对比；命中帧给夸张卡通高光/星芒；不用写实体积光雾化、不用胶片颗粒。"
    "② 纵深：靠大小对比与图层错位拉空间，前景放夸张冲击图形；不强求写实三层大气透视。"
    "③ 环境受力：用图形化卡通烟云/爆炸团/碎块/夸张变形（squash & stretch）表现冲击与破坏，不追写实碎屑物理。"
    "④ 运动能量：高速段给夸张动势线/速度线/集中线 + 形变；命中瞬间用大号冲击星芒/震动符号/夸张定格。"
    "色与光遵守本场光位锚与风格禁忌。"
)

# 风格族分流（substring 匹配，非命中即 cinematic 默认）。precedence: ink → flat → cel → cinematic。
# 日漫剧场版光影 / 厚涂幻想 / 3D卡通电影感 等本就含写实体积光与大气纵深 → 留 cinematic。
SPECTACLE_STYLE_PROFILES: Dict[str, str] = {
    "cinematic": COMBAT_SPECTACLE_RICHNESS_GUIDANCE,
    "cel": _SPECTACLE_CEL_GUIDANCE,
    "ink": _SPECTACLE_INK_GUIDANCE,
    "flat": _SPECTACLE_FLAT_GUIDANCE,
}
_SPECTACLE_INK_MARKERS = ("水墨",)
_SPECTACLE_FLAT_MARKERS = ("Q版", "q版", "纸片", "剪影", "定格", "低多边形", "玩具")
_SPECTACLE_CEL_MARKERS = ("赛璐璐", "二次元", "条漫", "动态漫画", "韩漫", "乙女")


def spectacle_style_family(style_text: str) -> str:
    """把风格名/风格句（含「风格禁忌」）归到 cinematic/cel/ink/flat 之一。纯函数·可测。

    入参可为 style_contract 的风格名、style_contract_phrase 整句、或 _设置.md 风格值；
    空串或无命中 → "cinematic"（保守回到原写实四层，向后兼容）。"""
    t = str(style_text or "")
    if any(m in t for m in _SPECTACLE_INK_MARKERS):
        return "ink"
    if any(m in t for m in _SPECTACLE_FLAT_MARKERS):
        return "flat"
    if any(m in t for m in _SPECTACLE_CEL_MARKERS):
        return "cel"
    return "cinematic"


def combat_spectacle_guidance_for_style(style_text: str = "") -> str:
    """按本剧风格族返回打斗镜「经费在燃烧」视觉盛宴注入文案（四层·风格自适应）。

    两个出图 runner 在 ``is_combat_spectacle_shot`` 命中后调用，避免给赛璐璐/水墨/Q版剧
    硬塞写实体积光与 motion blur（和 global_style/风格禁忌 打架·糊成四不像）。"""
    return SPECTACLE_STYLE_PROFILES[spectacle_style_family(style_text)]
