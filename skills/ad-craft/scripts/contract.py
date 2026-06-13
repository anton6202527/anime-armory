#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine-readable contract for the ad-* (拍广告) skill family.

自包含，不引用 n2d-* / mv-* / novel-*。拍广告线与 mv 线一样遵守"不复用其它家族 skill"
的硬约定——生图后端治理、阶段表、选择点都在本文件内独立维护一份。

拍广告线的结构差异（相对 n2d 逐集矩阵）：
- **不拆集**：一条主片是一个整体（可以很长），`_进度.md` 用"阶段进度表"而非"逐集矩阵"。
- **多版本/cutdown 轴**：一条主片常派生多时长（30/15/6s）+ 多比例（16:9/9:16/1:1）+ A/B，
  这些是 DELIVERABLES，登记在 `_进度.md` 的"交付版本矩阵"里。
"""
from copy import deepcopy


CONTRACT_VERSION = 1

# ── 选择点取值域 ───────────────────────────────────────────────────────────
AD_TYPES = ("TVC", "信息流短视频", "品牌片", "产品demo", "电商详情视频", "直播切片", "自定义")
CREATIVE_ROUTES = ("功能卖点", "情感共鸣", "幽默", "悬念反转", "名人代言", "场景种草", "自定义")
AD_VISUAL_STYLES = ("写实电影感", "CG质感", "定格动画", "二次元", "极简产品", "国风写意", "自定义")
MASTER_DURATIONS = ("6s", "15s", "30s", "60s", "自定义")
DELIVERY_ASPECTS = ("16:9", "9:16", "1:1", "多比例")
CUTDOWN_PLANS = ("主片+15s+6s", "主片+15s", "仅主片", "自定义")
CONSISTENCY_MODES = ("共享定妆+锚点", "指定参考图", "后端主体库", "+LoRA")
VIDEO_MODELS = (
    "Seedance 2.0", "Veo 3.1", "Kling 3.0", "Hailuo 02", "Hailuo 2.3",
    "Runway Gen-4", "Luma Ray3.2", "Pika 2.5",
    "HunyuanVideo 1.5", "Wan 2.2", "LTX-2.3", "Sora", "manual",
)
VIDEO_CHANNELS = (
    "即梦/Dreamina", "即梦", "Dreamina",
    "豆包",
    "海螺AI", "Hailuo",
    "可灵/Kling", "可灵", "Kling",
    "Google Gemini API",
    "Runway API", "Runway",
    "Luma Dream Machine", "Luma",
    "Pika",
    "本地/开源", "manual",
)
# Legacy combined backend list. New projects write `生视频模型` + `生视频渠道`.
VIDEO_BACKENDS = VIDEO_CHANNELS
VIDEO_ROUTING = ("自动按镜头路由", "固定生视频模型", "固定生视频AI")
VIDEO_SPECS = ("预算充足", "预算一般", "预算不够")
VIDEO_RESOLUTIONS = ("720p", "1080p", "4K")
IMAGE_BACKENDS = ("Codex", "OpenAI", "Seedream", "可灵主体库", "Nano Banana", "Sora Cameo", "自定义")
VOICE_BACKENDS = ("CosyVoice", "GPT-SoVITS", "MiniMax", "火山", "say占位", "自定义")
MUSIC_SOURCES = ("授权曲库", "原创定制", "AI生成", "占位")
ENDCARD_TEMPLATES = ("标准片尾", "角标常驻", "片尾+角标", "无", "自定义")
SUBTITLE_LANGS = ("中文", "中英双语", "仅英文", "无字幕")
AI_VISUAL_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI视觉")
ADLAW_REGIONS = ("中国大陆", "海外", "关闭")
DELIVERY_SPECS = ("平台默认", "广电TVC", "自定义")
GRANULARITY = ("逐个", "小批", "按场景分批", "整片", "自定义")
GEN_PRIORITY = ("关键镜优先", "分镜顺序", "先易后难")
REDRAW_BUDGET = ("预算充足", "预算一般")
WATERMARK_AI = ("投放前必打", "始终打")          # 合规·不可逆点：即便记录过每次仍确认
WATERMARK_BRAND = ("打", "不打")
TARGET_PLATFORMS = (
    "抖音", "快手", "视频号", "B站", "小红书", "朋友圈",
    "OTT电视", "电梯分众", "电商", "YouTube", "TikTok", "跨平台", "未定",
)
RELEASE_REGIONS = ("中国大陆", "港澳台", "北美", "东南亚", "全球", "自定义")

# ── 生图后端治理（解除 Codex 垄断，与 n2d/mv 同构，本线自持）────────────────
# `生图AI` 是真选择点，默认 Codex；放行官方多参考一致性后端；只拦 ① 项目内后端混用
# ② 逆向/未授权出图路径（安全 invariant）。合规闸门（AI 标识水印）与本治理无关。
# 候选快照新鲜度戳记（本线 _lib/freshness.py 据此判过期）。
# 注意：ad 线策略与 n2d 故意不同——ad 把 dreamina/即梦放进 FORBIDDEN（投放广告侧合规口径），
# n2d 则放行即梦官方 CLI。两份白名单是「不同策略」不是「重复」，不得合并。
# 采集日期：2026-06-13  来源：各后端官方文档 + 广告投放合规口径（待复核）
AD_IMAGE_BACKENDS_VERIFIED = {"date": "2026-06-13", "source": "各后端官方文档 + 广告投放合规口径(待复核)"}
AD_APPROVED_IMAGE_BACKENDS = {
    "codex":    {"label": "Codex / 官方 OpenAI gpt-image", "multi_reference": False, "native_subject": False, "default": True},
    "openai":   {"label": "官方 OpenAI gpt-image / DALL·E", "multi_reference": False, "native_subject": False},
    "gemini":   {"label": "Nano Banana / Gemini 多参考（原生 SynthID）", "multi_reference": True, "native_subject": False},
    "seedream": {"label": "Seedream Universal Reference（官方 API·免 LoRA 跨图锁主体·≤14 图）", "multi_reference": True, "native_subject": True},
    "kling":    {"label": "可灵 Kling 主体库 / Element Library", "multi_reference": True, "native_subject": True},
    "sora":     {"label": "Sora Character Cameo（可复用主体ID）", "multi_reference": True, "native_subject": True},
}
_AD_IMAGE_BACKEND_ALIASES = {
    "codex only": "codex", "codexonly": "codex", "codex": "codex",
    "openai": "openai", "gpt-image": "openai", "gpt image": "openai", "gptimage": "openai",
    "dall-e": "openai", "dalle": "openai",
    "nano banana": "gemini", "nanobanana": "gemini", "nano-banana": "gemini", "gemini": "gemini",
    "seedream": "seedream", "universal reference": "seedream",
    "kling": "kling", "可灵": "kling", "主体库": "kling",
    "sora": "sora", "character cameo": "sora", "cameo": "sora",
}
# 逆向/未授权出图路径——安全 invariant，永远 forbidden（官方 Seedream API 不在此列）。
AD_FORBIDDEN_IMAGE_BACKENDS = ("dreamina", "即梦", "同视频ai")


def classify_image_backend(raw):
    """归类生图后端字面值 → (canonical, kind)，kind ∈ {approved, forbidden, unknown}。"""
    text = (raw or "").strip().lower()
    if not text:
        return ("", "unknown")
    for bad in AD_FORBIDDEN_IMAGE_BACKENDS:
        if bad in text:
            return ("", "forbidden")
    for alias in sorted(_AD_IMAGE_BACKEND_ALIASES, key=len, reverse=True):
        if alias in text:
            return (_AD_IMAGE_BACKEND_ALIASES[alias], "approved")
    return ("", "unknown")


# ── 默认设置 + 选择点目录 ───────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "广告类型": "信息流短视频",
    "创意路线": "情感共鸣",
    "基础视觉风格": "写实电影感",
    "主片时长": "30s",
    "交付比例": "16:9",
    "cutdown版本": "主片+15s+6s",
    "生图AI": "Codex",
    "一致性增强": "共享定妆+锚点",
    "重抽预算策略": "预算充足",
    "生视频模型": "Seedance 2.0",
    "生视频渠道": "即梦/Dreamina",
    "视频模型路由": "自动按镜头路由",
    "出视频规格": "预算一般",
    "视频分辨率": "720p",
    "配音后端": "CosyVoice",
    "音乐来源": "占位",
    "品牌包装模板": "标准片尾",
    "字幕语言": "中文",
    "AI视觉使用披露": "AI-generated",
    "水印-AI合规标识": "投放前必打",
    "水印-品牌账号": "不打",
    "广告法地区": "中国大陆",
    "交付规格": "平台默认",
    "生成粒度": "逐个",
    "目标平台": "未定",
    "发行地区": "中国大陆",
}

CHOICE_POINTS = {
    "广告类型": AD_TYPES,
    "创意路线": CREATIVE_ROUTES,
    "基础视觉风格": AD_VISUAL_STYLES,
    "主片时长": MASTER_DURATIONS,
    "交付比例": DELIVERY_ASPECTS,
    "cutdown版本": CUTDOWN_PLANS,
    "生图AI": IMAGE_BACKENDS,
    "一致性增强": CONSISTENCY_MODES,
    "生视频模型": VIDEO_MODELS,
    "生视频渠道": VIDEO_CHANNELS,
    "视频模型路由": VIDEO_ROUTING,
    "出视频规格": VIDEO_SPECS,
    "视频分辨率": VIDEO_RESOLUTIONS,
    "配音后端": VOICE_BACKENDS,
    "音乐来源": MUSIC_SOURCES,
    "品牌包装模板": ENDCARD_TEMPLATES,
    "字幕语言": SUBTITLE_LANGS,
    "AI视觉使用披露": AI_VISUAL_USAGE_MODES,
    "水印-AI合规标识": WATERMARK_AI,
    "水印-品牌账号": WATERMARK_BRAND,
    "广告法地区": ADLAW_REGIONS,
    "交付规格": DELIVERY_SPECS,
    "生成粒度": GRANULARITY,
    "目标平台": TARGET_PLATFORMS,
    "发行地区": RELEASE_REGIONS,
}

# 合规/不可逆/花钱多的点：即便已记录，每次仍确认（见 skills/ad-craft/references/选择点与偏好.md 例外条）。
RECONFIRM_CHOICE_POINTS = ("水印-AI合规标识", "广告法地区", "音乐来源")

# ── brief 必填分层（一句话入口的机器判据）────────────────────────────────────
# 必问最小集：缺任一项 ad-concept 不应开工创意（由其第0步访谈式补齐，别让用户填 JSON）。
BRIEF_REQUIRED = ("brand", "product", "usp", "audience")
# 可延后合规项：允许标「待补」先做创意/脚本，但进入 GATE_STAGES（花钱/不可逆）前必须补齐。
BRIEF_DEFER_TO_GATE = ("claims", "rights", "mandatories.legal_lines")

_BRIEF_PENDING_TOKENS = ("", "待补", "tbd")


def _brief_value(brief, dotted):
    node = brief
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _brief_filled(value):
    if isinstance(value, str):
        return value.strip().lower() not in _BRIEF_PENDING_TOKENS
    if isinstance(value, dict):
        return bool(value) and all(_brief_filled(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return bool(value) and all(_brief_filled(v) for v in value)
    return value is not None


def brief_check(brief):
    """brief.json 完整性三层判据。

    返回 {missing_required, missing_deferred, ready, gate_ready}：
    - ready：必问最小集齐了，可开工创意/脚本；
    - gate_ready：连可延后合规项也齐了，可进花钱 gate（出图/出视频/合成）。
    """
    brief = brief or {}
    missing_required = [k for k in BRIEF_REQUIRED if not _brief_filled(_brief_value(brief, k))]
    missing_deferred = [k for k in BRIEF_DEFER_TO_GATE if not _brief_filled(_brief_value(brief, k))]
    return {
        "missing_required": missing_required,
        "missing_deferred": missing_deferred,
        "ready": not missing_required,
        "gate_ready": not (missing_required or missing_deferred),
    }

VIDEO_SPEC_PROFILE = {
    "预算充足": {"resolution": "1080p", "fps": 30, "key_takes": 3, "normal_takes": 2, "quality": "高质量档"},
    "预算一般": {"resolution": "720p", "fps": 24, "key_takes": 2, "normal_takes": 1, "quality": "标准档"},
    "预算不够": {"resolution": "720p", "fps": 24, "key_takes": 1, "normal_takes": 1, "quality": "省积分档"},
}

# 投放响度目标（LUFS）+ 安全框（标题/动作安全比例）。交付规格选择点据此归一。
DELIVERY_PROFILE = {
    "平台默认": {"loudness_lufs": -16.0, "true_peak_db": -1.0, "title_safe": 0.90, "action_safe": 0.93},
    "广电TVC":  {"loudness_lufs": -23.0, "true_peak_db": -2.0, "title_safe": 0.90, "action_safe": 0.93},
    "自定义":   {"loudness_lufs": -16.0, "true_peak_db": -1.0, "title_safe": 0.90, "action_safe": 0.93},
}

# ── 阶段表（不拆集；阶段即进度行）────────────────────────────────────────────
AD_STAGE_TABLE = [
    {"key": "brief",      "label": "客户需求立项", "owner": "ad",          "gate": "brief.json"},
    {"key": "concept",    "label": "创意策划",     "owner": "ad-concept",  "gate": "concept.md"},
    {"key": "script",     "label": "广告脚本+VO+时间轴", "owner": "ad-script", "gate": "广告法机检 + voiceover.txt"},
    {"key": "voice",      "label": "VO配音",       "owner": "ad-voice",    "gate": "时长清单.json"},
    {"key": "storyboard", "label": "分镜(实测时长驱动)", "owner": "ad-script", "gate": "storyboard.json + 镜头时长"},
    {"key": "image",      "label": "定妆库+出图",  "owner": "ad-image",    "gate": "visual identity + 首尾帧"},
    {"key": "video",      "label": "图生视频",     "owner": "ad-video",    "gate": "契约继承 + clip videos"},
    {"key": "compose",    "label": "剪辑包装+交付", "owner": "ad-compose",  "gate": "成片 + cutdown + 交付规格"},
    {"key": "review",     "label": "质检自审", "owner": "ad-review",  "gate": "M0 delivery review + human review"},
    {"key": "handoff",    "label": "AI披露/交付",  "owner": "ad-craft/scripts/ai_usage.py", "gate": "AI usage disclosure"},
]

# 高风险（花钱/不可逆/合规）阶段：正式生产入口须先确认。
GATE_STAGES = ("image", "video", "compose")

# 交付件（cutdown 轴）单条 schema —— 写进 _进度.md 交付版本矩阵。
DELIVERABLE_FIELDS = ("deliverable_id", "label", "duration", "aspect", "kind", "spec", "status", "path")
DELIVERABLE_KINDS = ("master", "cutdown", "reframe", "ab_variant")


def default_deliverables(master_duration="30s", aspect="16:9", cutdown_plan="主片+15s+6s"):
    """按主片时长/比例/cutdown 方案派生默认交付件清单（master + cutdowns）。"""
    rows = [{
        "deliverable_id": "master", "label": "主片", "duration": master_duration,
        "aspect": aspect, "kind": "master", "spec": "平台默认", "status": "⬜", "path": "",
    }]
    extra = {
        "主片+15s+6s": ["15s", "6s"],
        "主片+15s": ["15s"],
        "仅主片": [],
    }.get(cutdown_plan, [])
    for d in extra:
        rows.append({
            "deliverable_id": f"cut_{d}", "label": f"cutdown {d}", "duration": d,
            "aspect": aspect, "kind": "cutdown", "spec": "平台默认", "status": "⬜", "path": "",
        })
    return rows


def stage_table():
    return deepcopy(AD_STAGE_TABLE)


def choice_points():
    return deepcopy(CHOICE_POINTS)


def video_spec_profile(spec):
    if spec not in VIDEO_SPEC_PROFILE:
        raise KeyError(f"unknown video spec: {spec}")
    return deepcopy(VIDEO_SPEC_PROFILE[spec])


def delivery_profile(spec):
    if spec not in DELIVERY_PROFILE:
        raise KeyError(f"unknown delivery spec: {spec}")
    return deepcopy(DELIVERY_PROFILE[spec])


def settings_markdown(title, values=None):
    merged = dict(DEFAULT_SETTINGS)
    if values:
        merged.update({k: v for k, v in values.items() if v is not None})
    lines = [f"# _设置 · {title}", "", "## 选择"]
    for key in DEFAULT_SETTINGS:
        options = " | ".join(str(x) for x in CHOICE_POINTS.get(key, ()))
        suffix = f"  # {options}" if options else ""
        lines.append(f"- {key}: {merged[key]}{suffix}")
    lines.extend(["", "## 记录", "- 初始化（按拍广告线默认选择，可随时修改）"])
    return "\n".join(lines) + "\n"


def progress_markdown(title, deliverables=None):
    """生成不拆集的 `_进度.md`：阶段进度表 + 交付版本矩阵 + 维护记录。"""
    deliverables = deliverables or default_deliverables()
    lines = [
        f"# {title} — 拍广告生产进度",
        "",
        "> 不拆集：一条主片是一个整体。阶段进度见下表；多时长/多比例交付件见"
        "「交付版本矩阵」。状态：✅ 完成 / ⬜ 待做 / ⏳rough 占位。",
        "",
        "## 阶段进度",
        "",
        "| 阶段 | 状态 | 产物 | 备注 |",
        "|---|---|---|---|",
    ]
    for st in AD_STAGE_TABLE:
        gate = "M0必跑；深度流程自审后续增强" if st["key"] == "review" else ""
        lines.append(f"| {st['label']} | ⬜ |  | {gate} |")
    lines.extend(["", "## 交付版本矩阵", "",
                  "| 交付件 | 时长 | 比例 | 类型 | 交付规格 | 状态 | 成片路径 |",
                  "|---|---|---|---|---|---|---|"])
    for d in deliverables:
        lines.append(
            f"| {d['label']} | {d['duration']} | {d['aspect']} | {d['kind']} | "
            f"{d['spec']} | {d['status']} | {d['path']} |"
        )
    lines.extend(["", "## 维护记录", "- 初始化"])
    return "\n".join(lines) + "\n"
