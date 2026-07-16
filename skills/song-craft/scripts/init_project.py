#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建【写歌】项目骨架（词 + 歌）。

写歌线产出"一首成品歌"（歌/song.wav + 词/lyrics.md）。
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
import uuid
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


def build_synopsis(theme, genre, mood, out_root):
    """作品卡片一句话简介（≤240 字）。

    song 是纯音频线、无图片产物：卡片只固化 synopsis，不出封面。
    取数优先级（立项当刻能组一句就组，否则占位后续回填）：
      1) 创作/song_brief.json 的核心承诺（core_promise，立项后由 song_brief 回填时优先）
      2) 立项 meta 的 theme + genre/mood 组一句
    """
    brief_path = os.path.join(out_root, "创作", "song_brief.json")
    if os.path.exists(brief_path):
        try:
            with open(brief_path, encoding="utf-8") as f:
                promise = (json.load(f).get("core_promise") or "").strip()
            if promise and "待填写" not in promise:
                return promise[:240]
        except Exception:
            pass
    theme = (theme or "").strip()
    tags = "·".join(x for x in ((genre or "").strip(), (mood or "").strip()) if x)
    if theme and tags:
        text = f"{theme}（{tags}）"
    elif theme:
        text = theme
    elif tags:
        text = tags
    else:
        text = "待补：作品简介（可由 song_brief 核心承诺回填）"
    return text[:240]


def build_blueprint(title, meta):
    secs = "\n".join(f"- [{s}]" for s in meta["structure"])
    duration = f"{meta['target_duration_seconds']}s" if meta.get("target_duration_seconds") else "未定"
    return f"""# 创作蓝图 — 歌《{title}》

> 这首歌的"宪法"。动笔前敲定，每条具体可判定。写歌线只负责产出成品歌。

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
- 乐器编制：{meta['instrumentation']}
- 人声类型：{meta['vocal_type']}

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

> 结构化歌词：段落标签 + 词。song-compose 用它生成歌。
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
| A&R 简报 / 参考边界 | song-craft/scripts/song_brief.py + reference_pack.py | [ ] |
| 立项 + 词 | song-lyrics | [ ] |
| 歌词可唱性检查 | song-craft/scripts/lyric_prosody_check.py | [ ] |
| 旋律/和声/曲式草图 | song-craft/scripts/melody_chord_packet.py | [ ] |
| 作曲任务包 | song-compose/scripts/compose_song.py | [ ] |
| 多版生成 / 注册 | song-compose + 后端 | [ ] |
| 挑版定稿 | song-compose/scripts/compose_song.py | [ ] |
| 多版试听评审 | song-compose/scripts/take_review.py | [ ] |
| timecode 局部返修 | song-compose/scripts/revision_plan.py | [ ] |
| （可选）翻唱/换声 | song-cover | [ ] |
| 质检 | song-review | [ ] |
| 表演/混音人工签核 | song-review/scripts/mix_signoff.py | [ ] |
| 交付母版格式归一 | song-craft/scripts/master_delivery.py | [ ] |
| 母带 BS.1770 检查 | song-review/scripts/master_check.py | [ ] |
| AI 使用披露 | song-craft/scripts/ai_usage.py | [ ] |
| 权益元数据 | song-craft/scripts/rights_metadata.py | [ ] |
| 发行级元数据 | song-craft/scripts/release_metadata.py | [ ] |
| 发布交付包 | song-craft/scripts/release_pack.py | [ ] |
| （可选）发行数据回测 | song-feedback | [ ] |

## 产物
- [ ] 词/lyrics.md（定稿）
- [ ] 歌/compose_task.md（作曲任务包）
- [ ] 歌/takes_manifest.json（多版记录）
- [ ] 歌/song.wav（成品歌）
- [ ] 混音/pre_master.wav + mix_signoff.json（人工签核）
- [ ] 导出/master.wav + master_delivery.json（交付母版）
- [ ] 合规/AI使用说明.md（发布/交平台前）
- [ ] 合规/rights_metadata.json（权益/版税元数据）
- [ ] 发行/release_metadata.json（平台发行元数据）
- [ ] 导出/release_pack.json（发布交付证据）

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
    ap.add_argument("--instrumentation", default=contract.DEFAULT_SETTINGS["乐器编制"], help="乐器编制，如 piano and strings")
    ap.add_argument("--vocal-type", default=contract.DEFAULT_SETTINGS["人声类型"], help="人声类型，如 合成女声/合成男声/男女对唱")
    ap.add_argument("--takes", type=int, default=int(contract.DEFAULT_SETTINGS["生成版数"]))
    ap.add_argument("--compose-backend", default=contract.DEFAULT_SETTINGS["作曲后端"], choices=contract.COMPOSE_BACKENDS)
    ap.add_argument("--take-selection", default=contract.DEFAULT_SETTINGS["挑版策略"], choices=contract.TAKE_SELECTION_STRATEGIES)
    ap.add_argument("--ai-audio-usage", default=contract.DEFAULT_SETTINGS["AI音频使用披露"], choices=contract.AI_AUDIO_USAGE_MODES)
    ap.add_argument("--vocal-source", default="", help="自有嗓 / 授权音色 / 合成音色；可先留空，出歌前必须补")
    ap.add_argument("--publish-target", default="未定")
    ap.add_argument("--out", default=None, help="输出根，缺省 创作区/写歌/<曲名>/")
    args = ap.parse_args()

    folder = slug(args.title) if args.title != "待定" else f"新歌待定-{slug(args.genre)}"
    out_root = os.path.abspath(args.out or os.path.join("创作区", "写歌", folder))
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
        "project_id": f"song_{uuid.uuid4().hex[:16]}",
        "line": "song",
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
        "instrumentation": args.instrumentation,
        "vocal_type": args.vocal_type,
        "structure": structure,
        "song_backend": args.compose_backend,
        "compose_backend": args.compose_backend,
        "requested_takes": args.takes,
        "take_selection_strategy": args.take_selection,
        "ai_audio_usage": args.ai_audio_usage,
        "vocal_source": args.vocal_source or None,
        "rights_status": "original",
        # 作品卡片字段：synopsis=一句话简介；cover=作品封面。
        # song 纯音频线无图片产物 → cover 恒为 null，桌面卡片回退产线图标占位。
        "synopsis": build_synopsis(args.theme, args.genre, args.mood, out_root),
        "cover": None,
        "created_at": date.today().isoformat(),
    }
    settings = {
        "歌曲用途": args.use_case,
        "目标时长": f"{duration}s" if duration else "未定",
        "语言": args.language,
        "BPM/速度": args.bpm,
        "调性": args.key,
        "乐器编制": args.instrumentation,
        "人声类型": args.vocal_type,
        "作曲后端": args.compose_backend,
        "生成版数": str(args.takes),
        "挑版策略": args.take_selection,
        "AI音频使用披露": args.ai_audio_usage,
        "发行目标平台": publish_target,
    }

    with open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.makedirs(os.path.join(out_root, "生产数据"), exist_ok=True)
    with open(os.path.join(out_root, "生产数据", "artifact_catalog.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1, "kind": "artifact_catalog", "status": "bootstrap",
            "generated_at": date.today().isoformat(),
            "project": {"project_id": meta["project_id"], "line": "song", "title": meta.get("title") or slug(title), "root_rel": "."},
            "summary": {"artifact_count": 0, "total_bytes": 0, "disposable_bytes": 0, "invalid_count": 0},
            "event_sources": [], "view_sources": [], "artifacts": [], "duplicates": [],
        }, f, ensure_ascii=False, indent=2)
    write(os.path.join(out_root, "_设置.md"), contract.settings_markdown(title, settings))
    write(os.path.join(out_root, "创作蓝图.md"), build_blueprint(title, meta))
    write(os.path.join(out_root, "词", "lyrics.md"), build_lyrics(title, structure))
    write(os.path.join(out_root, "_进度.md"), build_progress(title, meta))

    print(f"[ok] 写歌项目骨架 → {out_root}")
    print(f"     _设置.md / 创作蓝图.md / 词/lyrics.md（{len(structure)} 段）/ 歌/takes/ / 合规/")
    print(f"     _meta: kind=song 曲风=\"{args.genre}\" 后端={args.compose_backend} 生成版数={args.takes}")
    print("[next] song-lyrics 填蓝图+词 → compose_song.py 生成任务包 → 多版挑版 → song-review")


if __name__ == "__main__":
    main()
