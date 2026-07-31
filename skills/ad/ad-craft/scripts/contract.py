#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine-readable contract for the ad-* (拍广告) skill family.

自包含：生图后端治理、阶段表、选择点、交付矩阵都在广告系列内独立维护。

拍广告线的结构：
- **不拆集**：一条主片是一个整体（可以很长），`_进度.md` 用"阶段进度表"而非"逐集矩阵"。
- **多版本/cutdown 轴**：一条主片常派生多时长（30/15/6s）+ 多比例（16:9/9:16/4:5/1:1）+ A/B，
  这些是 DELIVERABLES，登记在 `_进度.md` 的"交付版本矩阵"里。
"""
from copy import deepcopy


CONTRACT_VERSION = 4

# ── 选择点取值域 ───────────────────────────────────────────────────────────
AD_TYPES = ("TVC", "信息流短视频", "品牌片", "产品demo", "电商详情视频", "直播切片", "自定义")
CAMPAIGN_OBJECTIVES = ("品牌认知", "考虑种草", "转化行动", "全链路", "自定义")
FUNNEL_STAGES = ("awareness", "consideration", "conversion", "full_funnel", "自定义")
CREATIVE_ROUTES = ("功能卖点", "情感共鸣", "幽默", "悬念反转", "名人代言", "场景种草", "自定义")
AD_VISUAL_STYLES = ("写实电影感", "CG质感", "定格动画", "二次元", "极简产品", "国风写意", "自定义")
MASTER_DURATIONS = ("6s", "15s", "30s", "60s", "自定义")
DELIVERY_ASPECTS = ("16:9", "9:16", "4:5", "1:1", "多比例")
CUTDOWN_PLANS = ("主片+15s+6s", "主片+15s", "仅主片", "自定义")
CONSISTENCY_MODES = ("共享定妆+锚点", "指定参考图", "后端主体库", "+LoRA")
# 生视频模型/渠道候选快照（高频变动，freshness.py 据 采集日期 判过期）。
# 生视频候选采集日期：2026-07-11  来源：BytePlus Seedance 2.0 API、Google Veo 3.1 API、项目实际 CLI probe；范围=默认/适配内后端，其余候选执行时仍须 probe
AD_VIDEO_BACKENDS_VERIFIED = {
    "date": "2026-07-11",
    "source": "https://docs.byteplus.com/en/docs/modelark/1520757 ; https://ai.google.dev/gemini-api/docs/video",
    "scope": "default_and_adapter_backends",
}
VIDEO_MODELS = (
    "Seedance 2.0", "Veo 3.1", "Kling 3.0", "Hailuo 02", "Hailuo 2.3",
    "Runway Gen-4", "Luma Ray3.2", "Pika 2.5",
    "HunyuanVideo 1.5", "Wan 2.2", "LTX-2.3", "Sora", "manual",
)
# 渠道的「规范菜单」——每个渠道一行，用于选择点展示 / init 提示（不含别名，避免重复项）。
VIDEO_CHANNELS_MENU = (
    "即梦/Dreamina", "豆包", "海螺AI", "可灵/Kling", "Google Gemini API",
    "Runway API", "Luma Dream Machine", "Pika", "本地/开源", "manual",
)
# 渠道的「可接受全集」——菜单 + 常见别名，用于宽容校验 / 旧项目兼容（不要当 argparse closed-choices 用）。
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
IMAGE_MODELS = (
    "GPT Image 2", "Seedream 4.5", "Nano Banana Pro (Gemini 3 Pro Image)",
    "Kling Image 3.0", "Sora 2", "manual",
)
IMAGE_CHANNELS_MENU = (
    "Codex CLI", "OpenAI Images API", "BytePlus ModelArk API", "Google Gemini API",
    "Kling API", "OpenAI Sora", "manual",
)
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
TARGET_PLATFORMS = (
    "抖音", "快手", "视频号", "B站", "小红书", "朋友圈",
    "OTT电视", "电梯分众", "电商", "YouTube", "TikTok",
    "Instagram Reels", "Facebook Reels", "跨平台", "未定",
)
RELEASE_REGIONS = ("中国大陆", "港澳台", "北美", "东南亚", "全球", "自定义")

# ── 生图后端治理（Codex image2 优先，本线自持）────────────────────────────
# 新项目把「具体模型」与「访问渠道」分列；旧项目的 `生图AI` 只作迁移输入。
# 默认且优先 GPT Image 2 + Codex CLI/OpenAI Images API；其它官方路线只作为签核例外，
# gate 会要求 <作品根>/合规/image_backend_override.json。仍拦 ① 项目内模型/渠道混用
# ② 逆向/未授权出图路径（安全 invariant）。发布标识/声明另由 compliance_manifest 闭环。
# 候选快照新鲜度戳记（本线 _lib/freshness.py 据此判过期）。
# 注意：广告投放侧从严处理，Dreamina/即梦逆向或未授权路径保留在 FORBIDDEN；
# 明确写作“官方 CLI / official CLI / official API”的本机官方工具路径只代表可识别的
# official 后端；是否能付费出图由 gate 的非 Codex 签核闸决定。
# 生图候选采集日期：2026-07-11  来源：OpenAI Images、Google Gemini Image、BytePlus Seedream 官方文档；其它后端执行时仍须官方入口 probe + 项目签核
AD_IMAGE_BACKENDS_VERIFIED = {
    "date": "2026-07-11",
    "source": "https://platform.openai.com/docs/api-reference/images ; https://ai.google.dev/gemini-api/docs/image-generation ; https://docs.byteplus.com/en/docs/ModelArk/1541523",
    "scope": "official_api_and_adapter_verification",
}
AD_APPROVED_IMAGE_BACKENDS = {
    "codex":    {"label": "GPT Image 2", "model": "GPT Image 2", "channels": ["Codex CLI", "OpenAI Images API"], "multi_reference": False, "native_subject": False, "default": True},
    "openai":   {"label": "GPT Image 2", "model": "GPT Image 2", "channels": ["OpenAI Images API"], "multi_reference": False, "native_subject": False},
    "gemini":   {"label": "Nano Banana Pro (Gemini 3 Pro Image)", "model": "Nano Banana Pro (Gemini 3 Pro Image)", "channels": ["Google Gemini API"], "multi_reference": True, "native_subject": False},
    "seedream": {"label": "Seedream 4.5", "model": "Seedream 4.5", "channels": ["BytePlus ModelArk API"], "multi_reference": True, "native_subject": True},
    "kling":    {"label": "Kling Image 3.0", "model": "Kling Image 3.0", "channels": ["Kling API"], "multi_reference": True, "native_subject": True},
    "sora":     {"label": "Sora 2", "model": "Sora 2", "channels": ["OpenAI Sora"], "multi_reference": True, "native_subject": True},
    "dreamina_official": {"label": "自定义模型", "model": "manual", "channels": ["Dreamina/即梦官方 CLI/API"], "multi_reference": False, "native_subject": False},
}
_AD_IMAGE_BACKEND_ALIASES = {
    "codex only": "codex", "codexonly": "codex", "codex": "codex",
    "openai": "openai", "gpt-image": "openai", "gpt image": "openai", "gptimage": "openai",
    "dall-e": "openai", "dalle": "openai",
    "nano banana": "gemini", "nanobanana": "gemini", "nano-banana": "gemini", "gemini": "gemini",
    "seedream": "seedream", "universal reference": "seedream",
    "kling": "kling", "可灵": "kling", "主体库": "kling",
    "sora": "sora", "character cameo": "sora", "cameo": "sora",
    "dreamina/即梦官方 cli": "dreamina_official", "即梦/dreamina官方 cli": "dreamina_official",
    "dreamina official cli": "dreamina_official", "jimeng official cli": "dreamina_official",
    "即梦官方 cli": "dreamina_official", "dreamina official api": "dreamina_official",
    "即梦官方 api": "dreamina_official",
}
_AD_IMAGE_MODEL_ALIASES = {
    "gpt image 2": "codex", "gpt-image-2": "codex", "gpt-image 2": "codex",
    "seedream 4.5": "seedream", "seedream": "seedream",
    "nano banana pro": "gemini", "gemini 3 pro image": "gemini", "nano banana": "gemini",
    "kling image 3.0": "kling", "kling image": "kling",
    "sora 2": "sora", "sora": "sora",
    "dreamina image": "dreamina_official", "即梦 image": "dreamina_official",
}
_AD_IMAGE_CHANNEL_ALIASES = {
    "codex cli": "codex", "openai images api": "openai",
    "byteplus modelark api": "seedream", "google gemini api": "gemini",
    "kling api": "kling", "openai sora": "sora",
    "dreamina/即梦官方 cli/api": "dreamina_official", "dreamina official api": "dreamina_official",
    "即梦官方 api": "dreamina_official", "即梦官方 cli": "dreamina_official",
}
# 逆向/未授权出图路径——安全 invariant，永远 forbidden（官方 Seedream API 不在此列）。
AD_FORBIDDEN_IMAGE_BACKENDS = ("dreamina", "即梦", "同视频ai")


def classify_image_backend(raw):
    """归类生图后端字面值 → (canonical, kind)，kind ∈ {approved, forbidden, unknown}。"""
    text = (raw or "").strip().lower()
    if not text:
        return ("", "unknown")
    # 明确官方 CLI/API 的 Dreamina/即梦不走逆向 forbidden 口径。
    for alias, canonical in _AD_IMAGE_BACKEND_ALIASES.items():
        if canonical == "dreamina_official" and alias in text:
            return (canonical, "approved")
    for bad in AD_FORBIDDEN_IMAGE_BACKENDS:
        if bad in text:
            return ("", "forbidden")
    for alias in sorted(_AD_IMAGE_BACKEND_ALIASES, key=len, reverse=True):
        if alias in text:
            return (_AD_IMAGE_BACKEND_ALIASES[alias], "approved")
    return ("", "unknown")


def classify_image_model(raw):
    """具体生图模型 → (route canonical, kind)；manual/custom 必须走项目签核。"""
    text = (raw or "").strip().lower()
    if not text:
        return ("", "unknown")
    if text in {"manual", "自定义", "自定义模型"}:
        return ("manual", "manual")
    for alias in sorted(_AD_IMAGE_MODEL_ALIASES, key=len, reverse=True):
        if alias in text:
            return (_AD_IMAGE_MODEL_ALIASES[alias], "approved")
    # 兼容旧项目把壳/渠道写进模型栏；能识别但标 legacy，gate 要求迁移。
    canonical, kind = classify_image_backend(text)
    return (canonical, "legacy" if kind == "approved" else kind)


def classify_image_channel(raw):
    """生图访问渠道 → (route canonical, kind)，并永久阻断未授权/逆向路径。"""
    text = (raw or "").strip().lower()
    if not text:
        return ("", "unknown")
    if text in {"manual", "自定义", "自定义渠道"}:
        return ("manual", "manual")
    for alias in sorted(_AD_IMAGE_CHANNEL_ALIASES, key=len, reverse=True):
        if alias in text:
            return (_AD_IMAGE_CHANNEL_ALIASES[alias], "approved")
    if any(bad in text for bad in AD_FORBIDDEN_IMAGE_BACKENDS):
        return ("", "forbidden")
    return ("", "unknown")


# ── 默认设置 + 选择点目录 ───────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "广告类型": "信息流短视频",
    "广告目标": "转化行动",
    "漏斗阶段": "conversion",
    "创意路线": "情感共鸣",
    "基础视觉风格": "写实电影感",
    "主片时长": "30s",
    "交付比例": "16:9",
    "cutdown版本": "主片+15s+6s",
    "生图模型": "GPT Image 2",
    "生图渠道": "Codex CLI",
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
    "广告法地区": "中国大陆",
    "交付规格": "平台默认",
    "生成粒度": "逐个",
    "目标平台": "未定",
    "发行地区": "中国大陆",
}

CHOICE_POINTS = {
    "广告类型": AD_TYPES,
    "广告目标": CAMPAIGN_OBJECTIVES,
    "漏斗阶段": FUNNEL_STAGES,
    "创意路线": CREATIVE_ROUTES,
    "基础视觉风格": AD_VISUAL_STYLES,
    "主片时长": MASTER_DURATIONS,
    "交付比例": DELIVERY_ASPECTS,
    "cutdown版本": CUTDOWN_PLANS,
    "生图模型": IMAGE_MODELS,
    "生图渠道": IMAGE_CHANNELS_MENU,
    "一致性增强": CONSISTENCY_MODES,
    "生视频模型": VIDEO_MODELS,
    "生视频渠道": VIDEO_CHANNELS_MENU,
    "视频模型路由": VIDEO_ROUTING,
    "出视频规格": VIDEO_SPECS,
    "视频分辨率": VIDEO_RESOLUTIONS,
    "配音后端": VOICE_BACKENDS,
    "音乐来源": MUSIC_SOURCES,
    "品牌包装模板": ENDCARD_TEMPLATES,
    "字幕语言": SUBTITLE_LANGS,
    "AI视觉使用披露": AI_VISUAL_USAGE_MODES,
    "广告法地区": ADLAW_REGIONS,
    "交付规格": DELIVERY_SPECS,
    "生成粒度": GRANULARITY,
    "目标平台": TARGET_PLATFORMS,
    "发行地区": RELEASE_REGIONS,
}

# 合规/不可逆/花钱多的点：即便已记录，每次仍确认（见 skills/ad/ad-craft/references/选择点与偏好.md 例外条）。
# 合规面：广告法地区 / 音乐来源；花钱·不可逆面：出图与出视频后端/规格（一旦开跑即烧积分）。
RECONFIRM_CHOICE_POINTS = (
    "广告法地区", "音乐来源",
    "生图模型", "生图渠道", "生视频模型", "生视频渠道", "出视频规格",
)

# ── brief 必填分层（一句话入口的机器判据）────────────────────────────────────
# 必问最小集：缺任一项 ad-concept 不应开工创意（由其第0步访谈式补齐，别让用户填 JSON）。
BRIEF_REQUIRED = ("brand", "product", "usp", "audience", "campaign_objective")
# 可延后合规项：允许标「待补」先做创意/脚本，但进入 GATE_STAGES（花钱/不可逆）前必须补齐。
BRIEF_DEFER_TO_GATE = (
    "claims", "rights", "mandatories.legal_lines",
    "measurement.primary_kpi", "measurement.conversion_event",
)

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

# 投放响度目标（LUFS）+ 安全框。`平台默认` 是明确标注的内部数字母版标准，
# 不是伪称平台官方统一值；`广电TVC` 采用 EBU R128 programme loudness / true-peak 口径。
DELIVERY_PROFILE = {
    "平台默认": {"loudness_lufs": -16.0, "true_peak_db": -1.0, "title_safe": 0.90, "action_safe": 0.93,
                 "authority": "house_standard", "source": "内部数字投放母版；平台未声明统一响度时使用"},
    "广电TVC":  {"loudness_lufs": -23.0, "true_peak_db": -1.0, "title_safe": 0.90, "action_safe": 0.93,
                 "authority": "official_recommendation", "source": "EBU R128 / ITU-R BS.1770"},
    "自定义":   {"loudness_lufs": -16.0, "true_peak_db": -1.0, "title_safe": 0.90, "action_safe": 0.93,
                 "authority": "project_override", "source": "客户/平台书面规格；须在项目留证"},
}

HOUSE_MASTER_PROFILE = {
    "video_codec": "h264", "pixel_format": "yuv420p", "audio_codec": "aac",
    "audio_sample_rate": 48000, "frame_rate_min": 23.0, "frame_rate_max": 30.1,
    "color_primaries": "bt709", "color_transfer": "bt709", "color_space": "bt709",
    "color_range": "tv", "scan_type": "progressive",
    "min_bitrate_warn": 0,
    "authority": "house_standard",
    "note": "稳定上传/审片的内部交付母版；若平台或客户书面规格不同，以项目 override 为准。",
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
    {"key": "handoff",    "label": "AI披露/发布合规",  "owner": "ad-craft", "gate": "AI usage + compliance manifest"},
    {"key": "review",     "label": "质检自审", "owner": "ad-review",  "gate": "M0 delivery review + human sign-off"},
    {"key": "feedback",   "label": "投放反馈(可选)", "owner": "ad-feedback", "gate": "test-learn-refresh report"},
]

STAGE_ACCEPTANCE_VERSION = 3
# 每阶段标准必须说明证据性质：deterministic=机器事实；official=法律/平台；
# house=内部生产标准；human=只能由具名人员签收；heuristic=仅建议，不能伪装硬事实。
# `threshold` 写清通过线，`authority` 写依据层级，`on_fail` 写回退工位；避免只写抽象口号。
STAGE_CRITERIA = {
    "brief": (
        {"id": "brief_required", "evidence": "deterministic", "authority": "project_contract",
         "standard": "brand/product/usp/audience/campaign_objective 齐全", "threshold": "missing_required=0", "on_fail": "ad-concept 补访谈"},
        {"id": "measurement_design", "evidence": "house", "authority": "house_pre_spend_standard",
         "standard": "花钱前明确 primary_kpi 与 conversion_event", "threshold": "两字段均非占位", "on_fail": "回 brief 定义测量设计"},
    ),
    "concept": (
        {"id": "strategy_sections", "evidence": "house", "authority": "house_creative_brief",
         "standard": "Big Idea、key message、目标、创意假设、强制项均落档", "threshold": "5 组结构字段均存在", "on_fail": "ad-concept 补创意包"},
        {"id": "objective_fit", "evidence": "heuristic", "authority": "current_platform_guidance",
         "standard": "ABCD/平台创意原则按广告目标人工评估，不作为效果保证", "threshold": "只允许 WARN/人工判断", "on_fail": "调整创意路线后重评"},
    ),
    "script": (
        {"id": "script_package", "evidence": "deterministic", "authority": "project_contract",
         "standard": "脚本、VO、时间轴完整且非空", "threshold": "3 个产物可解析且非空", "on_fail": "ad-script 补齐"},
        {"id": "ad_law", "evidence": "official", "authority": "applicable_advertising_law",
         "standard": "广告法机检 0 block；语境例外须具名复核与依据", "threshold": "summary.block=0 且报告新鲜", "on_fail": "删改文案或补法务依据"},
    ),
    "voice": (
        {"id": "voice_manifest", "evidence": "deterministic", "authority": "project_contract",
         "standard": "逐句真实音频、voice_key、实测时长与整轨一致", "threshold": "逐句 seconds>0 且 formal 无占位", "on_fail": "ad-voice 重录/重导"},
        {"id": "voice_technical_qc", "evidence": "house", "authority": "house_audio_qc",
         "standard": "ffprobe/ffmpeg 可读、非静音、无严重时长漂移", "threshold": "full precision 且 summary.block=0", "on_fail": "ad-voice 修音频后重测"},
    ),
    "storyboard": (
        {"id": "timing_lock", "evidence": "deterministic", "authority": "project_delivery_contract",
         "standard": "唯一镜头 ID、正时长、总时长/VO/强制项/接缝闸门通过", "threshold": "镜头时长报告 0 block", "on_fail": "ad-script 重排分镜/VO"},
        {"id": "disclosure_presentation", "evidence": "official", "authority": "SAMR_2026_cited_content_guide_plus_house_legibility",
         "standard": "引证来源、条件、范围、有效期与免责声明按 claim_id 同屏/紧邻且可读", "threshold": "结构字段齐全；内部可读性阈值不冒充法定数值", "on_fail": "ad-script 补披露版式并重跑定稿"},
    ),
    "image": (
        {"id": "image_provenance", "evidence": "deterministic", "authority": "project_generation_contract",
         "standard": "所有 job 完成、具体模型/渠道、真实输出与实际参考输入可追溯", "threshold": "非取消 job 全 done 且文件存在", "on_fail": "ad-image 补落档/重出"},
        {"id": "product_qc", "evidence": "deterministic", "authority": "house_visual_qc",
         "standard": "product_qc full precision 且 0 block；视觉启发式只 WARN", "threshold": "precision=full, block=0", "on_fail": "ad-image 修受影响图"},
    ),
    "video": (
        {"id": "video_provenance", "evidence": "deterministic", "authority": "project_generation_contract",
         "standard": "compiled prompt/输入帧/模型路由/输出均可追溯", "threshold": "非取消 job 全 done 且输出存在", "on_fail": "ad-video 补落档/重出"},
        {"id": "video_qc", "evidence": "deterministic", "authority": "house_video_qc",
         "standard": "ffprobe+三帧+接缝实测 full precision，0 block", "threshold": "precision=full, block=0", "on_fail": "ad-video 修 clip/接缝"},
    ),
    "compose": (
        {"id": "delivery_matrix", "evidence": "deterministic", "authority": "house_or_project_delivery_profile",
         "standard": "所有未取消交付件存在并通过时长/比例/编解码/音轨/响度/版位 QC", "threshold": "每件 delivery_qc.passed=true", "on_fail": "ad-compose 重导对应版本"},
        {"id": "color_delivery", "evidence": "deterministic", "authority": "house_SDR_master_profile",
         "standard": "SDR 母版 BT.709/yuv420p/progressive；HDR/混色源须显式转换方案", "threshold": "色彩预检与交付元数据 0 block", "on_fail": "ad-compose 统一色彩管理后重导"},
        {"id": "accessibility_delivery", "evidence": "house", "authority": "WCAG_2_2_plus_house_caption_qc",
         "standard": "预录音频字幕结构完整；按适用级别提供音频描述或媒体替代；有意义非语言音频完整；闪烁风险需人审", "threshold": "accessibility_qc 0 block；启发式闪烁只 WARN", "on_fail": "补字幕/替代媒体/复核后重导"},
        {"id": "rendered_text_delivery", "evidence": "deterministic", "authority": "project_copy_contract_plus_WCAG_2_2",
         "standard": "在最终编码文件上实测字幕、CTA、价格、claim 与免责声明的 OCR 定位、对比度、停留和遮挡；机器只定位，具名人员确认文字与版式", "threshold": "rendered_text_qc 0 block 且报告绑定当前交付件 SHA", "on_fail": "ad-compose 修文字层/版式后重导"},
        {"id": "asr_delivery", "evidence": "deterministic", "authority": "approved_copy_contract",
         "standard": "voiceover.txt、实际 VO、字幕与最终成片音轨四路对账；数字、价格、CTA、claim、法律声明精确匹配", "threshold": "asr_consistency 0 block 且报告绑定当前 VO/字幕/母版", "on_fail": "回 ad-voice/ad-compose 修音轨或字幕"},
    ),
    "handoff": (
        {"id": "release_compliance", "evidence": "official", "authority": "release_jurisdiction_and_platform_rules",
         "standard": "AI/授权/平台声明/版位安全区/元数据证据 release_ready", "threshold": "compliance_manifest.release_ready=true", "on_fail": "发布方/法务补证"},
        {"id": "jurisdiction_coverage", "evidence": "official", "authority": "jurisdiction_specific_review",
         "standard": "非大陆投放逐辖区绑定当前成片的法律复核，不以泛称“海外”代替", "threshold": "每个 release region 有具名、带哈希复核", "on_fail": "补目标辖区法务复核"},
        {"id": "locale_release", "evidence": "deterministic", "authority": "project_locale_contract",
         "standard": "逐 locale 统一翻译、币种、单位、CTA、法律声明、配音、字幕与文字布局", "threshold": "locale_matrix_validation 0 block 且交付件均映射有效 locale", "on_fail": "补本地化与具名语言/排版复核"},
        {"id": "variant_release", "evidence": "deterministic", "authority": "project_release_contract",
         "standard": "每个最终交付件绑定当前 SHA、placement、locale、jurisdiction、claims/disclosures、rights 与 AI label receipt", "threshold": "release_variant_manifest 0 block，逐交付件映射完整", "on_fail": "补发布变体证据或重建 manifest"},
        {"id": "provenance_release", "evidence": "official", "authority": "C2PA_2_3_plus_applicable_AI_label_rules",
         "standard": "直接探测最终文件的 C2PA/隐式元数据；容器不承载时以绑定当前 SHA 的可查询平台/供应商回执补证", "threshold": "provenance_qc 0 block；metadata_status 字符串不能单独通过", "on_fail": "重新嵌入标识或补当前文件回执"},
    ),
    "review": (
        {"id": "machine_review", "evidence": "deterministic", "authority": "project_release_contract",
         "standard": "M0 机器报告 0 block 且未陈旧", "threshold": "summary.block=0 且 SHA/mtime 当前", "on_fail": "回对应生产工位修复"},
        {"id": "human_signoff", "evidence": "human", "authority": "named_release_reviewer",
         "standard": "产品/品牌/人物/场景/道具/字幕/音画/安全区/视觉真实性/闪烁/locale/AI 标识由具名人员逐项签收", "threshold": "全部检查 approved，证据、交付件与逐资产最终 contact sheet 哈希当前", "on_fail": "补具名审片和逐项证据"},
        {"id": "dependency_lineage", "evidence": "deterministic", "authority": "content_addressed_project_graph",
         "standard": "逐阶段、逐镜头、逐交付件的输入输出哈希收据当前；局部输入变化只失效其依赖节点", "threshold": "所有上游 dependency node=current", "on_fail": "只返工 stale 节点并重新验收"},
    ),
    "feedback": (
        {"id": "experiment_design", "evidence": "house", "authority": "platform_experiment_guidance_plus_house_preregistration",
         "standard": "同版位同受众同预算、单变量、预注册 KPI/窗口/样本门槛", "threshold": "validation.approved=true 且 plan SHA 当前", "on_fail": "重做实验设计"},
        {"id": "statistical_read", "evidence": "deterministic", "authority": "raw_platform_data",
         "standard": "无充分区间或不可比层时不得宣布胜者", "threshold": "原始数据哈希当前；不满足则 inconclusive", "on_fail": "延长实验或仅报观察"},
    ),
}

# 高风险（花钱/不可逆/合规）阶段：正式生产入口须先确认。
GATE_STAGES = ("image", "video", "compose")

# 交付件（cutdown 轴）单条 schema —— 写进 _进度.md 交付版本矩阵。
DELIVERABLE_FIELDS = ("deliverable_id", "label", "duration", "aspect", "kind", "spec", "status", "path")
DELIVERABLE_KINDS = ("master", "cutdown", "reframe", "ab_variant")


# 「多比例」展开成的具体交付比例（中心裁切/加边由 ad-compose reframe 产出）。
MULTI_ASPECT_RATIOS = ("16:9", "9:16", "4:5", "1:1")


def default_deliverables(master_duration="30s", aspect="16:9", cutdown_plan="主片+15s+6s"):
    """按主片时长/比例/cutdown 方案派生默认交付件清单。

    - master + cutdowns（按 cutdown 方案）；
    - 当 `交付比例=多比例` 时，再为每个目标比例派生 reframe 交付件（master 比例视为原生，不重复）。
    """
    master_aspect = MULTI_ASPECT_RATIOS[0] if aspect == "多比例" else aspect
    rows = [{
        "deliverable_id": "master", "label": "主片", "duration": master_duration,
        "aspect": master_aspect, "kind": "master", "spec": "平台默认", "status": "⬜", "path": "",
    }]
    extra = {
        "主片+15s+6s": ["15s", "6s"],
        "主片+15s": ["15s"],
        "仅主片": [],
    }.get(cutdown_plan, [])
    for d in extra:
        rows.append({
            "deliverable_id": f"cut_{d}", "label": f"cutdown {d}", "duration": d,
            "aspect": master_aspect, "kind": "cutdown", "spec": "平台默认", "status": "⬜", "path": "",
        })
    if aspect == "多比例":
        for ratio in MULTI_ASPECT_RATIOS:
            if ratio == master_aspect:
                continue
            rows.append({
                "deliverable_id": f"reframe_{ratio.replace(':', 'x')}",
                "label": f"reframe {ratio}", "duration": master_duration,
                "aspect": ratio, "kind": "reframe", "spec": "平台默认", "status": "⬜", "path": "",
            })
    return rows


def stage_table():
    return deepcopy(AD_STAGE_TABLE)


def choice_points():
    return deepcopy(CHOICE_POINTS)


def stage_criteria(stage):
    if stage not in STAGE_CRITERIA:
        raise KeyError(stage)
    return deepcopy(STAGE_CRITERIA[stage])


def video_spec_profile(spec):
    if spec not in VIDEO_SPEC_PROFILE:
        raise KeyError(f"unknown video spec: {spec}")
    return deepcopy(VIDEO_SPEC_PROFILE[spec])


def delivery_profile(spec):
    if spec not in DELIVERY_PROFILE:
        raise KeyError(f"unknown delivery spec: {spec}")
    return deepcopy(DELIVERY_PROFILE[spec])


def resolve_delivery_profile(spec, custom=None):
    """Resolve a built-in profile or a project-evidenced custom override.

    `自定义` must never silently inherit the house -16 LUFS fallback: the project
    has to supply measured targets and provenance in brief.delivery_profiles.自定义.
    """
    if spec != "自定义":
        return delivery_profile(spec)
    custom = custom if isinstance(custom, dict) else {}
    required = ("loudness_lufs", "true_peak_db", "source", "checked_at", "approved_by")
    missing = [key for key in required if custom.get(key) in (None, "")]
    if missing:
        raise ValueError("自定义交付规格缺 " + ", ".join(missing))
    row = deepcopy(DELIVERY_PROFILE["自定义"])
    row.update(custom)
    try:
        row["loudness_lufs"] = float(row["loudness_lufs"])
        row["true_peak_db"] = float(row["true_peak_db"])
    except (TypeError, ValueError) as exc:
        raise ValueError("自定义 loudness_lufs/true_peak_db 必须为数值") from exc
    if not -40 <= row["loudness_lufs"] <= -5 or not -10 <= row["true_peak_db"] <= 0:
        raise ValueError("自定义响度/真峰值超出合理录入范围，需复核书面规格")
    row["authority"] = "project_override"
    return row


def house_master_profile():
    return deepcopy(HOUSE_MASTER_PROFILE)


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
        gate = "M0机器复核 + 具名逐项人工签收" if st["key"] == "review" else ""
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
