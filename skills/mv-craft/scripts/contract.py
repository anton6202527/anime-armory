#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine-readable contract for the mv-* family.

自包含，不引用 n2d-*。生图后端治理与 n2d 同构（阶段1·解除 Codex 垄断），但在本文件
内独立维护一份，符合 mv 线"不复用 n2d-* 家族 skill"的硬约定。
"""
from copy import deepcopy


CONTRACT_VERSION = 1

MV_USE_CASES = ("短视频Hook", "歌曲Demo", "正式MV草稿", "投放版", "自定义")
MV_VISUAL_STYLES = ("电影叙事", "舞台演出", "国风写意", "赛博霓虹", "二次元", "抽象视觉器", "写实旅拍", "自定义")
MV_PLAN_GRANULARITY = ("粗略", "标准", "精细", "自定义")
MV_BEAT_STRATEGIES = ("副歌强卡点", "全程强卡点", "叙事优先", "歌词叙事优先", "人工指定", "自定义")
MV_VIDEO_BACKENDS = ("即梦", "可灵", "Veo", "Seedance", "Runway", "Kling", "manual")
# 阶段1：生图AI 是选择点，默认 Codex；放行官方多参考一致性后端。供 _设置.md 菜单用。
MV_IMAGE_BACKENDS = ("Codex", "Seedream", "可灵主体库", "Nano Banana", "Sora Cameo", "自定义")
MV_VIDEO_SPECS = ("预算充足", "预算一般", "预算不够")
MV_ASPECTS = ("16:9", "9:16", "1:1")
AI_VISUAL_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI视觉")

# ── 生图后端治理：阶段1（解除 Codex 垄断，与 n2d 同构，本线自持）──────────
# `生图AI` 是真选择点，默认 Codex；放行官方多参考一致性后端；mv-image / mv-review
# 不再因"非 Codex"拦截，只拦 ① 项目内后端混用 ② 逆向/未授权出图路径（安全 invariant）。
# 合规闸门（AI 标识水印 / 换脸授权）与本治理无关，保持不变。
MV_APPROVED_IMAGE_BACKENDS = {
    "codex":    {"label": "Codex / 官方 OpenAI gpt-image", "multi_reference": False, "native_subject": False, "default": True},
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
    "nano banana": "gemini", "nanobanana": "gemini", "nano-banana": "gemini", "gemini": "gemini",
    "seedream": "seedream", "universal reference": "seedream",
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
    "MV视觉风格": "电影叙事",
    "MV规划粒度": "标准",
    "卡点策略": "副歌强卡点",
    "生图AI": "Codex",
    "生视频AI": "即梦",
    "出视频规格": "预算一般",
    "合成画幅": "16:9",
    "AI视觉使用披露": "AI-generated",
    "发行目标平台": "未定",
}

CHOICE_POINTS = {
    "MV用途": MV_USE_CASES,
    "MV视觉风格": MV_VISUAL_STYLES,
    "MV规划粒度": MV_PLAN_GRANULARITY,
    "卡点策略": MV_BEAT_STRATEGIES,
    "生图AI": MV_IMAGE_BACKENDS,
    "生视频AI": MV_VIDEO_BACKENDS,
    "出视频规格": MV_VIDEO_SPECS,
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

MV_STAGE_TABLE = [
    {"key": "setup", "label": "项目骨架", "owner": "mv/scripts/init_project.py", "gate": "deterministic"},
    {"key": "beat", "label": "节拍/能量", "owner": "mv-beat/scripts/beat_detect.py", "gate": "beatgrid"},
    {"key": "plan", "label": "clip/timeline 规划", "owner": "mv-plan/scripts/plan_clips.py", "gate": "clip_plan"},
    {"key": "image", "label": "定妆/首帧/尾帧", "owner": "mv-image", "gate": "visual identity"},
    {"key": "video_jobs", "label": "视频任务包", "owner": "mv-video/scripts/video_jobs.py", "gate": "jobs_manifest"},
    {"key": "video", "label": "视频登记/挑版", "owner": "backend + video_jobs.py", "gate": "selected clip videos"},
    {"key": "lyric_sync", "label": "歌词对齐", "owner": "mv-lyric-sync/scripts/align.py", "gate": "subtitles"},
    {"key": "compose", "label": "时间线合成", "owner": "mv-compose", "gate": "timeline + song"},
    {"key": "review", "label": "质检", "owner": "mv-review", "gate": "machine + human review"},
    {"key": "handoff", "label": "发布/交平台", "owner": "mv-craft/scripts/ai_usage.py", "gate": "AI usage disclosure"},
]


def stage_table():
    return deepcopy(MV_STAGE_TABLE)


def choice_points():
    return deepcopy(CHOICE_POINTS)


def video_spec_profile(spec):
    if spec not in VIDEO_SPEC_PROFILE:
        raise KeyError(f"unknown video spec: {spec}")
    return deepcopy(VIDEO_SPEC_PROFILE[spec])


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
