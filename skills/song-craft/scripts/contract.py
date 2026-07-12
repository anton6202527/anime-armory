#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine-readable contract for the song-* family."""
from copy import deepcopy


CONTRACT_VERSION = 1

COMPOSE_BACKENDS = ("Suno", "Udio", "ACE-Step", "DiffRhythm", "manual")
SONG_USE_CASES = ("短视频Hook", "完整Demo", "发行母带前草稿", "自定义")
SONG_LANGUAGES = ("中文", "英文", "中英双语", "其他")
TEMPO_PRESETS = ("慢速", "中速", "快速", "自定义BPM")
TAKE_SELECTION_STRATEGIES = ("最佳hook", "最佳人声", "最贴蓝图", "最贴成品用途", "人工挑版")
AI_AUDIO_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI音频")
AI_LYRICS_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI歌词")

DEFAULT_DURATIONS = {
    "短视频Hook": 45,
    "完整Demo": 120,
    "发行母带前草稿": 180,
    "自定义": None,
}

DEFAULT_SETTINGS = {
    "歌曲用途": "完整Demo",
    "目标时长": "120s",
    "语言": "中文",
    "BPM/速度": "中速",
    "调性": "未定",
    "乐器编制": "未定",
    "人声类型": "合成女声",
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
    "乐器编制": ("未定", "piano and strings", "guitar band", "电子合成器", "国风器乐", "自定义"),
    "人声类型": ("合成女声", "合成男声", "男女对唱", "自有嗓", "授权音色", "自定义"),
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
        "key": "brief",
        "label": "A&R 简报 / 参考边界",
        "owner": "song-craft/scripts/song_brief.py + reference_pack.py",
        "gate": "target listener + reference boundary",
        "on_fail": "补目标听众、核心承诺、参考曲边界",
    },
    {
        "key": "lyrics",
        "label": "立项 + 词",
        "owner": "song-lyrics",
        "gate": "user-review + singability check",
        "on_fail": "回创作蓝图/副歌 hook/歌词结构",
    },
    {
        "key": "song_form",
        "label": "旋律/和声/曲式草图",
        "owner": "song-craft/scripts/melody_chord_packet.py",
        "gate": "chord sheet + topline notes",
        "on_fail": "补 key/BPM/和弦走向/topline 方向",
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
        "key": "revision",
        "label": "timecode 局部返修",
        "owner": "song-compose/scripts/revision_plan.py + backend",
        "gate": "blocking notes resolved or accepted",
        "on_fail": "按 repaint/regenerate job 生成新 take 后重评",
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
        "key": "mix_signoff",
        "label": "表演/混音人工签核",
        "owner": "song-review/scripts/mix_signoff.py",
        "gate": "human listening receipt bound to pre-master hash",
        "on_fail": "回局部返修、换声或重混",
    },
    {
        "key": "master_delivery",
        "label": "交付母版格式归一",
        "owner": "song-craft/scripts/master_delivery.py",
        "gate": "current mix signoff + lossless delivery receipt",
        "on_fail": "补签核或重做 pre-master",
    },
    {
        "key": "master_qc",
        "label": "混音/母带检查",
        "owner": "song-review/scripts/master_check.py",
        "gate": "audio delivery quality",
        "on_fail": "回 song-compose / 混音母带处理",
    },
    {
        "key": "rights",
        "label": "权益元数据",
        "owner": "song-craft/scripts/rights_metadata.py",
        "gate": "split sheet + rights metadata",
        "on_fail": "补贡献者 split、ISRC/ISWC/授权状态",
    },
    {
        "key": "release_metadata",
        "label": "发行级元数据",
        "owner": "song-craft/scripts/release_metadata.py",
        "gate": "track/release metadata + roles + explicit/date/territory/P/C lines",
        "on_fail": "补发行元数据并重跑检查",
    },
    {
        "key": "handoff",
        "label": "发布交付包",
        "owner": "song-craft/scripts/release_pack.py",
        "gate": "release pack evidence",
        "on_fail": "补 AI 使用披露、权益、母带或封面/元数据",
    },
    {
        "key": "feedback",
        "label": "发行数据回测",
        "owner": "song-feedback/scripts/feedback_ingest.py",
        "gate": "real listener/platform data",
        "on_fail": "补同条件样本或回 lyrics/compose/release strategy",
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
