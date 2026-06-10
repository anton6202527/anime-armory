#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine-readable contract for the song-* family."""
from copy import deepcopy


CONTRACT_VERSION = 1

COMPOSE_BACKENDS = ("Suno", "Udio", "ACE-Step", "DiffRhythm", "manual")
SONG_USE_CASES = ("短视频Hook", "完整Demo", "发行母带前草稿", "MV源歌", "自定义")
SONG_LANGUAGES = ("中文", "英文", "中英双语", "其他")
TEMPO_PRESETS = ("慢速", "中速", "快速", "自定义BPM")
TAKE_SELECTION_STRATEGIES = ("最佳hook", "最佳人声", "最贴蓝图", "最适合MV", "人工挑版")
AI_AUDIO_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI音频")
AI_LYRICS_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI歌词")

DEFAULT_DURATIONS = {
    "短视频Hook": 45,
    "完整Demo": 120,
    "发行母带前草稿": 180,
    "MV源歌": 120,
    "自定义": None,
}

DEFAULT_SETTINGS = {
    "歌曲用途": "完整Demo",
    "目标时长": "120s",
    "语言": "中文",
    "BPM/速度": "中速",
    "调性": "未定",
    "作曲后端": "Suno",
    "生成版数": "4",
    "挑版策略": "人工挑版",
    "AI音频使用披露": "AI-generated",
    "发行目标平台": "未定",
}

CHOICE_POINTS = {
    "歌曲用途": SONG_USE_CASES,
    "目标时长": ("30s", "45s", "60s", "90s", "120s", "180s", "自定义"),
    "语言": SONG_LANGUAGES,
    "BPM/速度": TEMPO_PRESETS,
    "调性": ("未定", "C", "D", "E", "F", "G", "A", "B", "Am", "Dm", "Em", "自定义"),
    "作曲后端": COMPOSE_BACKENDS,
    "生成版数": ("1", "2", "4", "6", "8"),
    "挑版策略": TAKE_SELECTION_STRATEGIES,
    "AI音频使用披露": AI_AUDIO_USAGE_MODES,
    "发行目标平台": ("抖音", "B站", "小红书", "YouTube", "Spotify", "网易云", "QQ音乐", "跨平台", "未定"),
}

SONG_STAGE_TABLE = [
    {
        "key": "setup",
        "label": "项目骨架",
        "owner": "song-craft/scripts/init_project.py",
        "gate": "deterministic",
        "on_fail": "重跑 init 或换 --out",
    },
    {
        "key": "lyrics",
        "label": "立项 + 词",
        "owner": "song-lyrics",
        "gate": "user-review + singability check",
        "on_fail": "回创作蓝图/副歌 hook/歌词结构",
    },
    {
        "key": "compose_plan",
        "label": "作曲任务包",
        "owner": "song-compose/scripts/compose_song.py",
        "gate": "settings + lyrics",
        "on_fail": "补 _设置.md / 创作蓝图.md / 词/lyrics.md",
    },
    {
        "key": "takes",
        "label": "多版生成 / 注册",
        "owner": "backend + song-compose/scripts/compose_song.py register",
        "gate": "take manifest",
        "on_fail": "补登记 take 或换后端重生成",
    },
    {
        "key": "selection",
        "label": "挑版定稿",
        "owner": "song-compose/scripts/compose_song.py score/select",
        "gate": "user-listening",
        "on_fail": "重评/重生成/回歌词或 style prompt",
    },
    {
        "key": "cover",
        "label": "翻唱/换声",
        "owner": "song-cover",
        "gate": "voice authorization",
        "on_fail": "换合法音色或跳过",
    },
    {
        "key": "review",
        "label": "质检",
        "owner": "song-review",
        "gate": "machine + listening checklist",
        "on_fail": "按报告回 lyrics/compose/cover",
    },
    {
        "key": "handoff",
        "label": "交制 MV / 发布",
        "owner": "mv + song-craft/scripts/ai_usage.py",
        "gate": "AI usage disclosure",
        "on_fail": "补合规留痕或目标平台信息",
    },
]


def duration_for_use_case(use_case):
    if use_case not in DEFAULT_DURATIONS:
        raise KeyError(f"unknown use_case: {use_case}")
    return DEFAULT_DURATIONS[use_case]


def stage_table():
    return deepcopy(SONG_STAGE_TABLE)


def choice_points():
    return deepcopy(CHOICE_POINTS)


def settings_markdown(title, values=None):
    """Return a project _设置.md body using known choice points."""
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
        "- 初始化（按写歌线默认选择，可随时修改）",
    ])
    return "\n".join(lines) + "\n"
