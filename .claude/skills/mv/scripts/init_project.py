#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建【制MV】项目骨架（输入=成品歌，做视频）。

制MV 线消费一首"已经做好的歌"（来自 写歌/<曲名>/ 或用户给的音频）做成 MV 视频。
mv 系列自包含，不复用其它家族 skill；出图/出视频/合成都由 mv 自家 skill 产出。

用法:
    python3 init_project.py --title "<曲名>" \\
        [--song <成品歌.wav/mp3>] [--lyrics <lyrics.md>] \\
        [--platform 抖音|网易云|跨平台] [--aspect 16:9|9:16] \\
        [--structure "intro,verse,chorus,..."] [--out <根>]
"""
import argparse, json, os, re, shutil, sys
from datetime import date

DEFAULT_STRUCTURE = "intro,verse1,pre-chorus,chorus,verse2,pre-chorus,chorus,bridge,chorus,outro"


def slug(s):
    s = re.sub(r"[^\w一-鿿-]+", "", (s or "").strip())
    return s or "新MV待定"


def build_visual_blueprint(title, platform, aspect, structure):
    secs = "\n".join(f"- [{s}] → 画面：" for s in structure)
    return f"""# 视觉蓝图 — MV《{title}》

> 制MV 的"视觉宪法"。歌已做好（见 歌/、词/）；这里只定**怎么用画面承载这首歌**。

## 输入歌
- 歌：`歌/song.wav`（来自 写歌/<曲名>/ 或用户提供）
- 词：`词/lyrics.md`（卡拉OK 对齐用）

## MV 视觉概念
- 画幅：{aspect}　平台：{platform}
- 主角 / 形象 + 锚定（跨镜一致）：
- 场景 / 世界观：
- 画风（global_style）：

## 段落 ↔ 画面映射（副歌高能、verse 叙事、bridge 反转）
{secs}

## 卡点策略
- 副歌踩鼓点切、verse 缓；高潮加速；爽点对齐 beatgrid（mv-beat 产）。

## 卡拉OK字幕
- 语言 / 样式（逐字高亮 .ass）：
"""


def build_progress(title, meta):
    return f"""# 进度 — 制MV《{title}》

> 平台={meta['target_platform']} 画幅={meta['aspect']} 段落={len(meta['structure'])}。输入歌={'已入' if meta['has_song'] else '待放入 歌/'}。

## 输入
- [{'x' if meta['has_song'] else ' '}] 歌/song.wav（成品歌，来自 写歌/ 或用户）
- [{'x' if meta['has_lyrics'] else ' '}] 词/lyrics.md（卡拉OK对齐用）

## 制MV 阶段
| 阶段 | skill | 状态 |
|---|---|---|
| 视觉蓝图 + 设定 | 本调度 + mv-image | [ ] |
| 卡点 beatgrid | mv-beat | [ ] |
| 出图 | mv-image | [ ] |
| 出视频 | mv-video | [ ] |
| 卡拉OK字幕 | mv-lyric-sync | [ ] |
| 合成成片 | mv-compose | [ ] |
| （可选）换脸 | video-faceswap（公共） | [ ] |

## 导出
- [ ] 成片_MV.mp4
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True, help="曲名")
    ap.add_argument("--song", default=None, help="成品歌音频（拷入 歌/song.<ext>）")
    ap.add_argument("--lyrics", default=None, help="歌词 md（拷入 词/lyrics.md）")
    ap.add_argument("--platform", default="跨平台")
    ap.add_argument("--aspect", default="16:9", choices=["16:9", "9:16", "1:1"])
    ap.add_argument("--structure", default=DEFAULT_STRUCTURE)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out_root = os.path.abspath(args.out or os.path.join("制MV", slug(args.title)))
    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}（换 --title/--out 或先删）", file=sys.stderr)
        sys.exit(2)

    structure = [s.strip() for s in args.structure.split(",") if s.strip()]
    for sub in ("歌", "词", "节拍", "字幕", "设定", "设定/characters", "设定/locations",
                "出图/common", "出视频/视频", "导出"):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    has_song = False
    if args.song and os.path.exists(args.song):
        ext = os.path.splitext(args.song)[1] or ".wav"
        shutil.copy(args.song, os.path.join(out_root, "歌", f"song{ext}")); has_song = True
    has_lyrics = False
    if args.lyrics and os.path.exists(args.lyrics):
        shutil.copy(args.lyrics, os.path.join(out_root, "词", "lyrics.md")); has_lyrics = True

    meta = {
        "kind": "mv",
        "title": args.title,
        "target_platform": args.platform,
        "aspect": args.aspect,
        "structure": structure,
        "source_song": os.path.abspath(args.song) if args.song else None,
        "has_song": has_song, "has_lyrics": has_lyrics,
        "created_at": date.today().isoformat(),
    }
    W = lambda rel, txt: open(os.path.join(out_root, rel), "w", encoding="utf-8").write(txt)
    json.dump(meta, open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    W("视觉蓝图.md", build_visual_blueprint(args.title, args.platform, args.aspect, structure))
    W("_进度.md", build_progress(args.title, meta))

    print(f"[ok] 制MV 项目骨架 → {out_root}")
    print(f"     视觉蓝图.md / 歌/{'(已入)' if has_song else '(待放成品歌)'} / 词/{'(已入)' if has_lyrics else '(待放)'}")
    print(f"     节拍/ 字幕/ 设定/ 出图/ 出视频/视频/ ← 预建（mv 自家阶段产物）")
    print(f"     _meta: kind=mv 平台={args.platform} 画幅={args.aspect}")
    print(f"[next] 放入成品歌 → mv-beat 卡点 → mv-image 出图 → mv-video 出视频 → mv-lyric-sync 字幕 → mv-compose 合成（换脸用公共 video-faceswap）")


if __name__ == "__main__":
    main()
