#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建【写歌】项目骨架（词 + 歌，不含 MV 视频部分）。

写歌线产出"一首成品歌"（歌/song.wav + 词/lyrics.md）；之后交给 制MV(mv) 做视频。
独立的纯文本骨架 + _meta + _进度。

用法:
    python3 init_project.py --title "<曲名或'待定'>" --genre "<曲风>" \\
        --theme "<一句话主题/情绪>" \\
        [--platform 抖音|网易云|QQ音乐|跨平台] [--mood 燃|治愈|伤感] \\
        [--structure "intro,verse,chorus,verse,chorus,bridge,chorus,outro"] \\
        [--out <根>]
"""
import argparse, json, os, re, sys
from datetime import date

DEFAULT_STRUCTURE = "intro,verse1,pre-chorus,chorus,verse2,pre-chorus,chorus,bridge,chorus,outro"


def slug(s):
    s = re.sub(r"[^\w一-鿿-]+", "", (s or "").strip())
    return s or "新歌待定"


def build_blueprint(title, genre, theme, platform, mood, structure):
    secs = "\n".join(f"- [{s}]" for s in structure)
    return f"""# 创作蓝图 — 歌《{title}》

> 这首歌的"宪法"。动笔前敲定，每条具体可判定。写歌线产出成品歌交给 制MV 做视频。

## 一句话主题 / 情绪
{theme}

## 曲风 / 平台 / 基调
- 曲风：{genre}
- 目标平台：{platform}
- 情绪基调：{mood}

## 歌曲结构（段落骨架）
{secs}

## 演唱（song-compose 后端）
- 演唱音色：（自有 / 授权 / 合成；**不用未授权真人嗓**）
- 后端：（Suno 云 / ACE-Step 本地 / …，见 song SKILL 后端选型）

## 风格卡（有样本就填；否则 Demo 后回填）
- 文风/咬字 / 句子节奏 / 对白比 / 禁忌：
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

> 曲风={meta['genre']} 平台={meta['target_platform']} 段落={len(secs)}。

## 写歌阶段
| 阶段 | skill | 状态 |
|---|---|---|
| 立项 + 词 | song-lyrics | [ ] |
| 作曲 + 演唱 | song-compose | [ ] |
| （可选）翻唱/换声 | song-cover | [ ] |

## 产物
- [ ] 词/lyrics.md（定稿）
- [ ] 歌/song.wav（成品歌）

## 交接
- [ ] 成品歌交 制MV(mv) 做视频 → `制MV/<曲名>/`
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="待定")
    ap.add_argument("--genre", required=True, help="曲风，如 国风/流行/说唱/民谣/电子")
    ap.add_argument("--theme", required=True, help="一句话主题/情绪")
    ap.add_argument("--platform", default="跨平台")
    ap.add_argument("--mood", default="")
    ap.add_argument("--structure", default=DEFAULT_STRUCTURE)
    ap.add_argument("--out", default=None, help="输出根，缺省 写歌/<曲名>/")
    args = ap.parse_args()

    folder = slug(args.title) if args.title != "待定" else f"新歌待定-{slug(args.genre)}"
    out_root = os.path.abspath(args.out or os.path.join("写歌", folder))
    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}（换 --title/--out 或先删）", file=sys.stderr)
        sys.exit(2)

    structure = [s.strip() for s in args.structure.split(",") if s.strip()]
    for sub in ("词", "歌", "素材", "导出"):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    title = args.title
    meta = {
        "kind": "song",
        "title": None if title == "待定" else title,
        "genre": args.genre,
        "theme": args.theme,
        "mood": args.mood,
        "target_platform": args.platform,
        "structure": structure,
        "song_backend": None,
        "vocal_source": None,
        "rights_status": "original",
        "created_at": date.today().isoformat(),
    }
    W = lambda rel, txt: open(os.path.join(out_root, rel), "w", encoding="utf-8").write(txt)
    json.dump(meta, open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    W("创作蓝图.md", build_blueprint(title, args.genre, args.theme, args.platform, args.mood, structure))
    W("词/lyrics.md", build_lyrics(title, structure))
    W("_进度.md", build_progress(title, meta))

    print(f"[ok] 写歌项目骨架 → {out_root}")
    print(f"     创作蓝图.md / 词/lyrics.md（{len(structure)} 段）/ 歌/(成品歌落此) ← 骨架")
    print(f"     _meta: kind=song 曲风=\"{args.genre}\" 平台={args.platform}")
    print(f"[next] song-lyrics 填蓝图+词 → song-compose 出歌 → (可选 song-cover) → 成品歌交 制MV(mv) 做视频")


if __name__ == "__main__":
    main()
