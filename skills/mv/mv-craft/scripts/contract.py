#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine-readable contract for the mv-* family.

自包含：生图后端治理、阶段表、选择点都在 mv 系列内独立维护。
"""
from copy import deepcopy
import hashlib
import json


CONTRACT_VERSION = 3

MV_USE_CASES = ("短视频Hook", "歌曲Demo", "正式MV草稿", "投放版", "自定义")
MV_SONG_TIMINGS = ("先传音乐", "后配歌曲")
MV_VISUAL_STYLES = ("电影叙事", "舞台演出", "国风写意", "赛博霓虹", "二次元", "抽象视觉器", "写实旅拍", "自定义")
MV_PLAN_GRANULARITY = ("粗略", "标准", "精细", "自定义")
MV_BEAT_STRATEGIES = ("副歌强卡点", "全程强卡点", "叙事优先", "歌词叙事优先", "人工指定", "自定义")
# Primary menu = capabilities reverified from official sources on 2026-08-20.
# Profiles below retain older names only so existing projects can still be read;
# they are not silently promoted into a new project's current candidate menu.
MV_VIDEO_MODELS = (
    "Seedance 2.5", "Gemini Omni Flash Preview", "Veo 3.1", "Kling 3.0", "Runway Gen-4.5",
    "Luma Ray3.2", "manual", "自定义",
)
MV_LEGACY_VIDEO_MODELS = (
    "Seedance 2.0", "Luma Ray3 / Ray3.14",
    "Hailuo 02", "Hailuo 2.3", "Runway Gen-4", "Pika 2.5",
    "HunyuanVideo 1.5", "Wan 2.2", "LTX-2.3", "Sora 2", "Sora",
)
MV_VIDEO_CHANNELS = (
    "即梦/Dreamina", "即梦", "Dreamina",
    "豆包",
    "火山方舟/Volcengine API",
    "海螺AI", "Hailuo",
    "可灵/Kling", "可灵", "Kling",
    "Google Gemini API",
    "Runway API", "Runway",
    "Luma Dream Machine", "Luma",
    "Pika",
    "本地/开源", "manual",
)
# Legacy combined backend list. New projects write `生视频模型` + `生视频渠道`.
MV_VIDEO_BACKENDS = MV_VIDEO_CHANNELS
# 图片生成同视频一样拆成「具体模型」与「访问渠道」两轴；生图AI 仅作旧项目兼容。
MV_IMAGE_MODELS = (
    "GPT Image 2", "Seedream 5.0 Lite", "Nano Banana Pro (Gemini 3 Pro Image)", "自定义",
)
MV_IMAGE_CHANNELS = (
    "Codex", "OpenAI API", "火山方舟/Seedream", "Google Gemini API",
    "可灵/Kling", "manual",
)
MV_IMAGE_BACKENDS = ("Codex", "Seedream", "可灵主体库", "Nano Banana", "Sora Cameo", "自定义")
MV_CONSISTENCY_MODES = ("共享定妆+锚点", "指定参考图", "后端主体库", "+LoRA")
MV_VIDEO_SPECS = ("预算充足", "预算一般", "预算不够")
MV_ASPECTS = ("16:9", "9:16", "1:1")
MV_LIPSYNC_MODES = ("关闭", "仅正面演唱镜", "全演唱镜", "后期口型修复", "自定义")
MV_SUBTITLE_MODES = ("中文", "中英双语", "仅英文", "无字幕")
AI_VISUAL_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI视觉")

MV_VIDEO_MODEL_PROFILES = {
    "Seedance 2.5": {
        "reference_images": True, "start_end_frames": False, "reference_video_motion": True,
        "native_audio": True, "audio_reference": True, "multi_shot": True, "max_sequence_seconds": 30,
        "best_for": "30 秒内多镜头段落与复杂多模态参考；按能力图约束输入角色、数量与渠道",
    },
    "Seedance 2.0": {
        "reference_images": True, "start_end_frames": False, "reference_video_motion": True,
        "native_audio": True, "audio_reference": True, "multi_shot": True, "max_sequence_seconds": 15,
        "best_for": "多模态参考、15秒内多镜头段落、复杂动作；首尾帧须按实际渠道再次核验",
    },
    "Veo 3.1": {
        "reference_images": True, "start_end_frames": True, "reference_video_motion": False,
        "native_audio": True, "multi_shot": False, "best_for": "电影感、首尾帧桥接、少量关键镜",
    },
    "Gemini Omni Flash Preview": {
        "reference_images": True, "start_end_frames": False, "reference_video_motion": False,
        "native_audio": True, "multi_shot": False, "preview": True,
        "requires_runtime_adapter": True,
        "best_for": "Gemini Interactions API 预览候选；公开执行矩阵未稳定，必须具名 adapter，不能借用 Veo 参数",
    },
    "Kling 3.0": {
        "reference_images": True, "start_end_frames": True, "reference_video_motion": True,
        "native_audio": True, "multi_shot": True, "max_sequence_seconds": 15,
        "best_for": "多镜头叙事、Elements 主体、动作镜、演唱口型/原生音频候选",
    },
    "Hailuo 02": {
        "reference_images": True, "start_end_frames": True, "reference_video_motion": False,
        "native_audio": False, "best_for": "人物表演、短镜头补片",
    },
    "Hailuo 2.3": {
        "reference_images": True, "start_end_frames": True, "reference_video_motion": False,
        "native_audio": False, "best_for": "人物表演、短镜头补片",
    },
    "Runway Gen-4.5": {
        "reference_images": True, "start_end_frames": False, "reference_video_motion": False,
        "native_audio": False, "multi_shot": False,
        "best_for": "高动作质量、复杂连续指令、电影质感；当前公开控制以 T2V/I2V 为主",
    },
    "Runway Gen-4": {
        "reference_images": True, "start_end_frames": True, "reference_video_motion": False,
        "native_audio": False, "best_for": "单参考角色一致性、广告/时尚质感关键镜",
    },
    "Luma Ray3 / Ray3.14": {
        "reference_images": True, "start_end_frames": True, "reference_video_motion": False,
        "native_audio": False, "best_for": "角色参考、keyframe、HDR/调色链路",
    },
    "Luma Ray3.2": {
        "reference_images": True, "start_end_frames": True, "reference_video_motion": True,
        "native_audio": False, "multi_shot": True, "max_sequence_seconds": 20,
        "best_for": "角色参考、keyframe、视频修改与多镜头；按能力图核验实际渠道",
    },
    "Pika 2.5": {
        "reference_images": True, "start_end_frames": True, "reference_video_motion": False,
        "native_audio": False, "best_for": "风格化短镜和补片",
    },
    "HunyuanVideo 1.5": {
        "reference_images": False, "start_end_frames": False, "reference_video_motion": False,
        "native_audio": False, "best_for": "本地/开源预算路径",
    },
    "Wan 2.2": {
        "reference_images": True, "start_end_frames": True, "reference_video_motion": False,
        "native_audio": False, "best_for": "本地/开源图生视频路径",
    },
    "LTX-2.3": {
        "reference_images": False, "start_end_frames": False, "reference_video_motion": False,
        "native_audio": False, "best_for": "本地快速预演",
    },
    "Sora": {
        "reference_images": True, "start_end_frames": True, "reference_video_motion": False,
        "native_audio": False, "legacy": True,
        "best_for": "旧项目兼容；当前可用性必须按官方产品/地区重新核验，不进入新项目默认菜单",
    },
    "Sora 2": {
        "reference_images": True, "start_end_frames": False, "reference_video_motion": False,
        "native_audio": True, "multi_shot": True,
        "legacy": True,
        "best_for": "旧项目兼容；当前可用性、产品迁移与真人授权逐次核验，不进入新项目默认菜单",
    },
    "manual": {
        "reference_images": False, "start_end_frames": False, "reference_video_motion": False,
        "native_audio": False, "best_for": "人工网页/外包登记",
    },
}

_MV_VIDEO_MODEL_ALIASES = {
    "seedance": "Seedance 2.0", "seedance 2": "Seedance 2.0",
    "veo": "Veo 3.1", "veo 3": "Veo 3.1",
    "omni": "Gemini Omni Flash Preview", "gemini omni": "Gemini Omni Flash Preview",
    "gemini omni flash": "Gemini Omni Flash Preview",
    "kling": "Kling 3.0", "可灵": "Kling 3.0",
    "hailuo": "Hailuo 2.3", "海螺": "Hailuo 2.3",
    "runway": "Runway Gen-4.5", "gen-4.5": "Runway Gen-4.5",
    "luma": "Luma Ray3 / Ray3.14", "ray3": "Luma Ray3 / Ray3.14",
    "pika": "Pika 2.5", "hunyuanvideo": "HunyuanVideo 1.5",
    "wan": "Wan 2.2", "ltx": "LTX-2.3", "sora": "Sora",
    "manual": "manual",
}

MV_VIDEO_CHANNEL_PROFILES = {
    "即梦/Dreamina": {"type": "web_or_app", "official_api": False, "notes": "仅登记人工/网页产物；不要伪装自动化"},
    "即梦": {"type": "web_or_app", "official_api": False, "notes": "同 即梦/Dreamina"},
    "Dreamina": {"type": "web_or_app", "official_api": False, "notes": "同 即梦/Dreamina"},
    "豆包": {"type": "web_or_app", "official_api": False, "notes": "仅登记人工/网页产物"},
    "火山方舟/Volcengine API": {"type": "api", "official_api": True, "notes": "仅在能力图 access_status 可执行时提交；pending 不能冒充可用"},
    "海螺AI": {"type": "web_or_app", "official_api": False, "notes": "仅登记人工/网页产物"},
    "Hailuo": {"type": "web_or_app", "official_api": False, "notes": "同 海螺AI"},
    "可灵/Kling": {"type": "api_or_web", "official_api": True, "notes": "优先记录 start/end frame 与主体参考输入"},
    "可灵": {"type": "api_or_web", "official_api": True, "notes": "同 可灵/Kling"},
    "Kling": {"type": "api_or_web", "official_api": True, "notes": "同 可灵/Kling"},
    "Google Gemini API": {"type": "api", "official_api": True, "notes": "记录参考图数量、首尾帧和音频能力"},
    "Runway API": {"type": "api", "official_api": True, "notes": "记录角色参考、首尾帧和版本"},
    "Runway": {"type": "api_or_web", "official_api": True, "notes": "同 Runway API"},
    "Luma Dream Machine": {"type": "api_or_web", "official_api": True, "notes": "记录 keyframe/character reference/HDR"},
    "Luma": {"type": "api_or_web", "official_api": True, "notes": "同 Luma Dream Machine"},
    "Pika": {"type": "api_or_web", "official_api": True, "notes": "记录版本和参考输入"},
    "本地/开源": {"type": "local", "official_api": False, "notes": "记录模型权重、commit/版本、参数"},
    "manual": {"type": "manual", "official_api": False, "notes": "人工登记；必须留来源和挑版理由"},
}

_MV_VIDEO_CHANNEL_ALIASES = {
    "dreamina": "Dreamina", "即梦": "即梦", "即梦/dreamina": "即梦/Dreamina",
    "豆包": "豆包", "hailuo": "Hailuo", "海螺": "海螺AI", "海螺ai": "海螺AI",
    "kling": "Kling", "可灵": "可灵", "可灵/kling": "可灵/Kling",
    "google gemini api": "Google Gemini API", "runway": "Runway", "runway api": "Runway API",
    "luma": "Luma", "luma dream machine": "Luma Dream Machine", "pika": "Pika",
    "本地/开源": "本地/开源", "manual": "manual",
}

_MV_LEGACY_VIDEO_ROUTES = {
    "即梦": ("Seedance 2.0", "即梦"),
    "dreamina": ("Seedance 2.0", "Dreamina"),
    "seedance": ("Seedance 2.0", "即梦/Dreamina"),
    "可灵": ("Kling 3.0", "可灵"),
    "kling": ("Kling 3.0", "Kling"),
    "veo": ("Veo 3.1", "Google Gemini API"),
    "omni": ("Gemini Omni Flash Preview", "Google Gemini API"),
    "runway": ("Runway Gen-4.5", "Runway"),
    "sora": ("Sora", "manual"),
    "manual": ("manual", "manual"),
}

# ── 生图后端治理：阶段1（解除 Codex 垄断，本线自持）──────────────────────
# `生图AI` 是真选择点，默认 Codex；放行官方多参考一致性后端；mv-image / mv-review
# 不再因"非 Codex"拦截，只拦 ① 项目内后端混用 ② 逆向/未授权出图路径（安全 invariant）。
# AI 标识/披露/水印不再由本流水线处理，移到工具之外按平台/地区法规自行处理，与本治理无关。
MV_APPROVED_IMAGE_BACKENDS = {
    "codex":    {"label": "GPT Image 2 via Codex", "multi_reference": True, "native_subject": False, "default": True},
    "openai":   {"label": "官方 OpenAI gpt-image / DALL·E", "multi_reference": False, "native_subject": False},
    "gemini":   {"label": "Nano Banana / Gemini 多参考（原生 SynthID）", "multi_reference": True, "native_subject": False},
    "seedream": {"label": "Seedream Universal Reference（官方 API·免 LoRA 跨图锁人·≤14 图）", "multi_reference": True, "native_subject": True},
    "kling":    {"label": "可灵 Kling 主体库 / Custom Model / Element Library", "multi_reference": True, "native_subject": True},
    "sora":     {"label": "Sora Character Cameo（可复用角色ID）", "multi_reference": True, "native_subject": True},
}
_MV_IMAGE_BACKEND_ALIASES = {
    "codex only": "codex", "codexonly": "codex", "codex": "codex",
    "openai": "openai", "gpt-image": "openai", "gpt image": "openai", "gptimage": "openai",
    "dall-e": "openai", "dalle": "openai",
    "gpt image 2": "openai", "gpt-image-2": "openai",
    "nano banana": "gemini", "nanobanana": "gemini", "nano-banana": "gemini", "gemini": "gemini",
    "seedream": "seedream", "seedream 5.0 lite": "seedream", "universal reference": "seedream",
    "kling": "kling", "可灵": "kling", "主体库": "kling",
    "sora": "sora", "character cameo": "sora", "cameo": "sora",
}
# 逆向/未授权出图路径——安全 invariant，永远 forbidden（官方 Seedream API 不在此列）。
MV_FORBIDDEN_IMAGE_BACKENDS = ("dreamina", "即梦", "同视频ai")


def classify_image_backend(raw):
    """归类生图后端字面值 → (canonical, kind)，kind ∈ {approved, forbidden, unknown}。"""
    text = (raw or "").strip().lower()
    if not text:
        return ("", "unknown")
    for bad in MV_FORBIDDEN_IMAGE_BACKENDS:
        if bad in text:
            return ("", "forbidden")
    for alias in sorted(_MV_IMAGE_BACKEND_ALIASES, key=len, reverse=True):
        if alias in text:
            return (_MV_IMAGE_BACKEND_ALIASES[alias], "approved")
    return ("", "unknown")


DEFAULT_SETTINGS = {
    "MV用途": "歌曲Demo",
    "歌曲输入时序": "先传音乐",
    "MV视觉风格": "电影叙事",
    "MV规划粒度": "标准",
    "卡点策略": "副歌强卡点",
    "生图AI": "Codex",
    "生图模型": "GPT Image 2",
    "生图渠道": "Codex",
    "MV一致性增强": "共享定妆+锚点",
    "生视频模型": "Seedance 2.5",
    "生视频渠道": "即梦/Dreamina",
    "出视频规格": "预算一般",
    "演唱口型": "仅正面演唱镜",
    "字幕语言": "中文",
    "合成画幅": "16:9",
    "AI视觉使用披露": "AI-generated",
    "发行目标平台": "未定",
}

CHOICE_POINTS = {
    "MV用途": MV_USE_CASES,
    "歌曲输入时序": MV_SONG_TIMINGS,
    "MV视觉风格": MV_VISUAL_STYLES,
    "MV规划粒度": MV_PLAN_GRANULARITY,
    "卡点策略": MV_BEAT_STRATEGIES,
    "生图AI": MV_IMAGE_BACKENDS,
    "生图模型": MV_IMAGE_MODELS,
    "生图渠道": MV_IMAGE_CHANNELS,
    "MV一致性增强": MV_CONSISTENCY_MODES,
    "生视频模型": MV_VIDEO_MODELS,
    "生视频渠道": MV_VIDEO_CHANNELS,
    "出视频规格": MV_VIDEO_SPECS,
    "演唱口型": MV_LIPSYNC_MODES,
    "字幕语言": MV_SUBTITLE_MODES,
    "合成画幅": MV_ASPECTS,
    "AI视觉使用披露": AI_VISUAL_USAGE_MODES,
    "发行目标平台": ("抖音", "B站", "小红书", "YouTube", "Spotify", "网易云", "QQ音乐", "跨平台", "未定"),
}

VIDEO_SPEC_PROFILE = {
    "预算充足": {"resolution": "1080p", "fps": 30, "key_takes": 3, "normal_takes": 2, "quality": "高质量档"},
    "预算一般": {"resolution": "720p", "fps": 24, "key_takes": 2, "normal_takes": 1, "quality": "标准档"},
    "预算不够": {"resolution": "720p", "fps": 24, "key_takes": 1, "normal_takes": 1, "quality": "省积分档"},
}

PLAN_GRANULARITY_PROFILE = {
    "粗略": {"verse_bars": 4, "chorus_bars": 2, "max_clips": 16},
    "标准": {"verse_bars": 2, "chorus_bars": 1, "max_clips": 32},
    "精细": {"verse_bars": 1, "chorus_bars": 1, "max_clips": 64},
    "自定义": {"verse_bars": 2, "chorus_bars": 1, "max_clips": 32},
}

# Only these preferences affect clip/timeline planning.  A release-only change
# must not stale picture lock; a planning change must always do so.  Writers and
# gates share this function to avoid a split-brain digest definition.
MV_PLAN_SETTING_KEYS = (
    "MV用途", "MV视觉风格", "MV规划粒度", "卡点策略", "合成画幅", "出视频规格",
)


def plan_settings_digest(settings):
    payload = {
        key: settings.get(key)
        for key in MV_PLAN_SETTING_KEYS
        if settings.get(key) is not None
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

MV_STAGE_TABLE = [
    {"key": "setup", "label": "项目骨架", "owner": "mv/scripts/init_project.py", "gate": "deterministic"},
    {"key": "song_ingest", "label": "歌曲入库/定稿", "owner": "user-file-ingest", "gate": "歌/song.*; lyrics conditional on subtitle/lipsync"},
    {"key": "beat", "label": "节拍/能量", "owner": "mv-beat/scripts/beat_detect.py", "gate": "beatgrid"},
    {"key": "lyric_sync", "label": "歌词时间轴", "owner": "mv-lyric-sync/scripts/align.py", "gate": "hash-bound forced alignment or signed review"},
    {"key": "script", "label": "视觉蓝图/设定", "owner": "mv-script", "gate": "visual blueprint"},
    {"key": "script_review", "label": "视觉蓝图复核", "owner": "mv-script", "gate": "beatgrid-reviewed blueprint"},
    {"key": "plan", "label": "clip/timeline 规划", "owner": "mv-plan/scripts/plan_clips.py", "gate": "clip_plan"},
    {"key": "semantic_plan", "label": "语义分镜注入", "owner": "mv-plan/scripts/compose_prompts.py", "gate": "full hash-bound semantic coverage"},
    {"key": "pacing_check", "label": "节奏预检", "owner": "mv-score/scripts/score_pacing.py", "gate": "fresh deterministic receipt"},
    {"key": "image", "label": "定妆/首帧/尾帧", "owner": "mv-image", "gate": "visual identity"},
    {"key": "picture_lock", "label": "Animatic/Picture Lock", "owner": "mv-craft", "gate": "named hash-bound signoff"},
    {"key": "video_jobs", "label": "视频任务包", "owner": "mv-video/scripts/video_jobs.py", "gate": "jobs_manifest"},
    {"key": "video", "label": "视频登记/挑版", "owner": "backend + video_jobs.py", "gate": "selected clip videos"},
    {"key": "compose", "label": "时间线合成", "owner": "mv-compose", "gate": "timeline + song"},
    {"key": "disclosure", "label": "AI使用披露", "owner": "mv-craft/scripts/ai_usage.py", "gate": "current AI usage disclosure"},
    {"key": "provenance", "label": "来源链锁定", "owner": "mv-craft/scripts/provenance.py", "gate": "final provenance after disclosure"},
    {"key": "review", "label": "质检", "owner": "mv-review", "gate": "machine + human review"},
    {"key": "handoff", "label": "发布/交平台", "owner": "mv-craft/scripts/completion.py", "gate": "named hash-bound handoff receipt"},
]


def stage_table():
    return deepcopy(MV_STAGE_TABLE)


def runtime_state_from_settings(settings=None):
    """Derive compatibility/runtime fields from the project settings truth.

    `_meta.json` mirrors these fields for older stage scripts, but it is not an
    independent preference store.  ``is_demo`` remains a compatibility tag;
    load-bearing gates must not use it to lower their enforcement floor.
    """
    supplied = {k: v for k, v in (settings or {}).items() if v not in (None, "")}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(supplied)
    # Read historical one-axis settings without letting modern defaults erase
    # the route the user had explicitly chosen.
    if "生视频AI" in supplied:
        legacy_model, legacy_channel = legacy_video_route(supplied["生视频AI"])
        if "生视频模型" not in supplied and legacy_model:
            merged["生视频模型"] = legacy_model
        if "生视频渠道" not in supplied and legacy_channel:
            merged["生视频渠道"] = legacy_channel
    if "生图渠道" not in supplied and supplied.get("生图AI"):
        merged["生图渠道"] = supplied["生图AI"]
    use_case = merged["MV用途"]
    platform = merged["发行目标平台"]
    return {
        "use_case": use_case,
        "song_timing": merged["歌曲输入时序"],
        "is_demo": use_case in {"短视频Hook", "歌曲Demo"},
        "aspect": merged["合成画幅"],
        "target_platform": platform,
        "publish_target": platform,
        "visual_style": merged["MV视觉风格"],
        "plan_granularity": merged["MV规划粒度"],
        "beat_strategy": merged["卡点策略"],
        "image_model": merged["生图模型"],
        "image_channel": merged["生图渠道"],
        "image_backend": merged["生图渠道"],
        "video_model": merged["生视频模型"],
        "video_channel": merged["生视频渠道"],
        "video_backend": merged["生视频渠道"],
        "video_spec": merged["出视频规格"],
        "lip_sync_mode": merged["演唱口型"],
        "subtitle_language": merged["字幕语言"],
        "ai_visual_usage": merged["AI视觉使用披露"],
    }


def validate_stage_table(stage_actions=None):
    """Return structural contract issues instead of failing later at routing."""
    issues = []
    keys = []
    labels = []
    for index, row in enumerate(MV_STAGE_TABLE):
        missing = [name for name in ("key", "label", "owner", "gate") if not row.get(name)]
        if missing:
            issues.append(f"stage[{index}] missing fields: {', '.join(missing)}")
        keys.append(row.get("key"))
        labels.append(row.get("label"))
    duplicate_keys = sorted({key for key in keys if key and keys.count(key) > 1})
    duplicate_labels = sorted({label for label in labels if label and labels.count(label) > 1})
    if duplicate_keys:
        issues.append(f"duplicate stage keys: {duplicate_keys}")
    if duplicate_labels:
        issues.append(f"duplicate stage labels: {duplicate_labels}")

    known = set(keys)
    reached = set()
    for timing in MV_SONG_TIMINGS:
        workflow = workflow_stage_table(timing, "中文", "仅正面演唱镜")
        workflow_keys = [row["key"] for row in workflow]
        unknown = [key for key in workflow_keys if key not in known]
        if unknown:
            issues.append(f"{timing} workflow has unknown stages: {unknown}")
        if len(workflow_keys) != len(set(workflow_keys)):
            issues.append(f"{timing} workflow has duplicate stages")
        reached.update(workflow_keys)
    unreachable = sorted(known - reached)
    if unreachable:
        issues.append(f"unreachable stages: {unreachable}")
    if stage_actions is not None:
        action_keys = set(stage_actions)
        missing_actions = sorted(known - action_keys)
        extra_actions = sorted(action_keys - known)
        if missing_actions:
            issues.append(f"stages missing run actions: {missing_actions}")
        if extra_actions:
            issues.append(f"run actions without contract stage: {extra_actions}")
    return issues


def workflow_stage_table(song_timing=None, subtitle_mode=None, lip_sync_mode=None):
    """Return stage order; lyric alignment is conditional for instrumental MVs."""
    timing = song_timing or DEFAULT_SETTINGS["歌曲输入时序"]
    by_key = {s["key"]: s for s in MV_STAGE_TABLE}
    if timing == "后配歌曲":
        keys = [
            "setup", "script", "song_ingest", "beat", "lyric_sync", "script_review", "plan",
            "semantic_plan", "pacing_check", "image", "picture_lock", "video_jobs", "video", "compose",
            "disclosure", "provenance", "review", "handoff",
        ]
    else:
        keys = [
            "setup", "song_ingest", "beat", "lyric_sync", "script", "plan", "semantic_plan", "pacing_check",
            "image", "picture_lock", "video_jobs", "video", "compose", "disclosure", "provenance", "review", "handoff",
        ]
    subtitle_mode = subtitle_mode or DEFAULT_SETTINGS["字幕语言"]
    lip_sync_mode = lip_sync_mode or DEFAULT_SETTINGS["演唱口型"]
    if subtitle_mode == "无字幕" and lip_sync_mode == "关闭":
        keys = [key for key in keys if key != "lyric_sync"]
    return deepcopy([by_key[k] for k in keys])


def choice_points():
    return deepcopy(CHOICE_POINTS)


def video_spec_profile(spec):
    if spec not in VIDEO_SPEC_PROFILE:
        raise KeyError(f"unknown video spec: {spec}")
    return deepcopy(VIDEO_SPEC_PROFILE[spec])


def video_model_profile(model):
    model = normalize_video_model(model)
    if model not in MV_VIDEO_MODEL_PROFILES:
        raise KeyError(f"unknown video model: {model}")
    return deepcopy(MV_VIDEO_MODEL_PROFILES[model])


def video_channel_profile(channel):
    channel = normalize_video_channel(channel)
    if channel not in MV_VIDEO_CHANNEL_PROFILES:
        raise KeyError(f"unknown video channel: {channel}")
    return deepcopy(MV_VIDEO_CHANNEL_PROFILES[channel])


def normalize_video_model(value):
    raw = str(value or "").strip()
    if raw in MV_VIDEO_MODEL_PROFILES:
        return raw
    return _MV_VIDEO_MODEL_ALIASES.get(raw.lower(), raw)


def normalize_video_channel(value):
    raw = str(value or "").strip()
    if raw in MV_VIDEO_CHANNEL_PROFILES:
        return raw
    return _MV_VIDEO_CHANNEL_ALIASES.get(raw.lower(), raw)


def legacy_video_route(value):
    """Map the old one-axis `生视频AI` value to an explicit model/channel pair."""
    raw = str(value or "").strip()
    return _MV_LEGACY_VIDEO_ROUTES.get(raw.lower(), (raw, raw))


def plan_granularity_profile(granularity):
    if granularity not in PLAN_GRANULARITY_PROFILE:
        raise KeyError(f"unknown plan granularity: {granularity}")
    return deepcopy(PLAN_GRANULARITY_PROFILE[granularity])


def settings_markdown(title, values=None):
    merged = dict(DEFAULT_SETTINGS)
    if values:
        merged.update({k: v for k, v in values.items() if v is not None})
    lines = [
        f"# _设置 · {title}",
        "",
        "## 选择",
    ]
    for key in DEFAULT_SETTINGS:
        options = " | ".join(str(x) for x in CHOICE_POINTS.get(key, ()))
        suffix = f"  # {options}" if options else ""
        lines.append(f"- {key}: {merged[key]}{suffix}")
    lines.extend([
        "",
        "## 记录",
        "- 初始化（按制MV线默认选择，可随时修改）",
    ])
    return "\n".join(lines) + "\n"
