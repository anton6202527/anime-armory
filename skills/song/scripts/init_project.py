#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建【写歌】项目骨架（词 + 歌，不含 MV 视频部分）。

写歌线产出"一首成品歌"（歌/song.wav + 词/lyrics.md）；之后交给 制MV(mv) 做视频。
独立的纯文本骨架 + _设置 + _meta + _进度。

用法:
    python3 init_project.py --title "<曲名或'待定'>" --genre "<曲风>" \\
        --theme "<一句话主题/情绪>" \\
        [--platform 抖音|网易云|QQ音乐|跨平台] [--mood 燃|治愈|伤感] \\
        [--use-case 完整Demo] [--duration 120] [--takes 4] \\
        [--compose-backend Suno|Udio|ACE-Step|DiffRhythm|manual] [--out <根>]
"""
import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import date


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CONTRACT_PATH = os.path.join(REPO, "skills", "song-craft", "scripts", "contract.py")


def load_contract():
    spec = importlib.util.spec_from_file_location("song_contract", CONTRACT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


contract = load_contract()

DEFAULT_STRUCTURE = "intro,verse1,pre-chorus,chorus,verse2,pre-chorus,chorus,bridge,chorus,outro"


def slug(s):
    s = re.sub(r"[^\w一-鿿-]+", "", (s or "").strip())
    return s or "新歌待定"


def build_blueprint(title, meta):
    secs = "\n".join(f"- [{s}]" for s in meta["structure"])
    duration = f"{meta['target_duration_seconds']}s" if meta.get("target_duration_seconds") else "未定"
    return f"""# 创作蓝图 — 歌《{title}》

> 这首歌的"宪法"。动笔前敲定，每条具体可判定。写歌线产出成品歌交给 制MV 做视频。

## 一句话主题 / 情绪
{meta['theme']}

## 曲风 / 平台 / 基调
- 曲风：{meta['genre']}
- 目标平台：{meta['target_platform']}
- 情绪基调：{meta['mood']}
- 歌曲用途：{meta['use_case']}
- 目标时长：{duration}
- 语言：{meta['language']}
- BPM/速度：{meta['bpm']}
- 调性：{meta['key']}

## 歌曲结构（段落骨架）
{secs}

## 演唱（song-compose 后端）
- 作曲后端：{meta['song_backend']}
- 生成版数：{meta['requested_takes']}
- 挑版策略：{meta['take_selection_strategy']}
- 演唱音色：（自有 / 授权 / 合成；**不用未授权真人嗓**）

## 风格卡（有样本就填；否则 Demo 后回填）
- 文风/咬字 / 句子节奏 / 禁忌：
"""


def build_lyrics(title, structure):
    blocks = "\n\n".join(f"[{s}]\n（歌词…）" for s in structure)
    return f"""# 歌词 — 《{title}》

> 结构化歌词：段落标签 + 词。song-compose 用它生成歌；下游 制MV 的 mv-lyric-sync 用它对齐卡拉OK。
> 作词工艺见 song-lyrics/references/songcraft.md（结构/押韵/字数贴旋律/hook）。

{blocks}
"""


def build_progress(title, meta):
    secs = meta["structure"]
    return f"""# 进度 — 写歌《{title}》

> 曲风={meta['genre']} 平台={meta['target_platform']} 段落={len(secs)} 生成版数={meta['requested_takes']}。

## 写歌阶段
| 阶段 | skill | 状态 |
|---|---|---|
| 立项 + 词 | song-lyrics | [ ] |
| 作曲任务包 | song-compose/scripts/compose_song.py | [ ] |
| 多版生成 / 注册 | song-compose + 后端 | [ ] |
| 挑版定稿 | song-compose/scripts/compose_song.py | [ ] |
| （可选）翻唱/换声 | song-cover | [ ] |
| 质检 | song-review | [ ] |
| AI 使用披露 | song-craft/scripts/ai_usage.py | [ ] |

## 产物
- [ ] 词/lyrics.md（定稿）
- [ ] 歌/compose_task.md（作曲任务包）
- [ ] 歌/takes_manifest.json（多版记录）
- [ ] 歌/song.wav（成品歌）
- [ ] 合规/AI使用说明.md（发布/交平台前）

## 交接
- [ ] 成品歌交 制MV(mv) 做视频 → `制MV/<曲名>/`
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="待定")
    ap.add_argument("--genre", required=True, help="曲风，如 国风/流行/说唱/民谣/电子")
    ap.add_argument("--theme", required=True, help="一句话主题/情绪")
    ap.add_argument("--platform", default="跨平台")
    ap.add_argument("--mood", default="")
    ap.add_argument("--structure", default=DEFAULT_STRUCTURE)
    ap.add_argument("--use-case", default=contract.DEFAULT_SETTINGS["歌曲用途"], choices=contract.SONG_USE_CASES)
    ap.add_argument("--duration", type=int, default=None, help="目标时长秒数；缺省按歌曲用途给建议")
    ap.add_argument("--language", default=contract.DEFAULT_SETTINGS["语言"], choices=contract.SONG_LANGUAGES)
    ap.add_argument("--bpm", default=contract.DEFAULT_SETTINGS["BPM/速度"], help="慢速/中速/快速/自定义BPM 或具体数值")
    ap.add_argument("--key", default=contract.DEFAULT_SETTINGS["调性"], help="调性，如 Am/C/未定")
    ap.add_argument("--takes", type=int, default=int(contract.DEFAULT_SETTINGS["生成版数"]))
    ap.add_argument("--compose-backend", default=contract.DEFAULT_SETTINGS["作曲后端"], choices=contract.COMPOSE_BACKENDS)
    ap.add_argument("--take-selection", default=contract.DEFAULT_SETTINGS["挑版策略"], choices=contract.TAKE_SELECTION_STRATEGIES)
    ap.add_argument("--ai-audio-usage", default=contract.DEFAULT_SETTINGS["AI音频使用披露"], choices=contract.AI_AUDIO_USAGE_MODES)
    ap.add_argument("--vocal-source", default="", help="自有嗓 / 授权音色 / 合成音色；可先留空，出歌前必须补")
    ap.add_argument("--publish-target", default="未定")
    ap.add_argument("--out", default=None, help="输出根，缺省 写歌/<曲名>/")
    args = ap.parse_args()

    folder = slug(args.title) if args.title != "待定" else f"新歌待定-{slug(args.genre)}"
    out_root = os.path.abspath(args.out or os.path.join("写歌", folder))
    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}（换 --title/--out 或先删）", file=sys.stderr)
        sys.exit(2)
    if args.takes < 1:
        print("[err] --takes 必须 >= 1", file=sys.stderr)
        sys.exit(2)

    structure = [s.strip() for s in args.structure.split(",") if s.strip()]
    for sub in ("词", "歌", "歌/takes", "歌/compose_prompts", "素材", "导出", "合规"):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    title = args.title
    duration = args.duration if args.duration is not None else contract.duration_for_use_case(args.use_case)
    publish_target = args.publish_target if args.publish_target != "未定" else args.platform
    meta = {
        "schema_version": 1,
        "kind": "song",
        "title": None if title == "待定" else title,
        "genre": args.genre,
        "theme": args.theme,
        "mood": args.mood,
        "target_platform": args.platform,
        "publish_target": publish_target,
        "use_case": args.use_case,
        "target_duration_seconds": duration,
        "language": args.language,
        "bpm": args.bpm,
        "key": args.key,
        "structure": structure,
        "song_backend": args.compose_backend,
        "compose_backend": args.compose_backend,
        "requested_takes": args.takes,
        "take_selection_strategy": args.take_selection,
        "ai_audio_usage": args.ai_audio_usage,
        "vocal_source": args.vocal_source or None,
        "rights_status": "original",
        "created_at": date.today().isoformat(),
    }
    settings = {
        "歌曲用途": args.use_case,
        "目标时长": f"{duration}s" if duration else "未定",
        "语言": args.language,
        "BPM/速度": args.bpm,
        "调性": args.key,
        "作曲后端": args.compose_backend,
        "生成版数": str(args.takes),
        "挑版策略": args.take_selection,
        "AI音频使用披露": args.ai_audio_usage,
        "发行目标平台": publish_target,
    }

    with open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    write(os.path.join(out_root, "_设置.md"), contract.settings_markdown(title, settings))
    write(os.path.join(out_root, "创作蓝图.md"), build_blueprint(title, meta))
    write(os.path.join(out_root, "词", "lyrics.md"), build_lyrics(title, structure))
    write(os.path.join(out_root, "_进度.md"), build_progress(title, meta))

    print(f"[ok] 写歌项目骨架 → {out_root}")
    print(f"     _设置.md / 创作蓝图.md / 词/lyrics.md（{len(structure)} 段）/ 歌/takes/ / 合规/")
    print(f"     _meta: kind=song 曲风=\"{args.genre}\" 后端={args.compose_backend} 生成版数={args.takes}")
    print("[next] song-lyrics 填蓝图+词 → compose_song.py 生成任务包 → 多版挑版 → song-review → mv")


if __name__ == "__main__":
    main()
