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
        [--visual-style 电影叙事] [--plan-granularity 标准] [--out <根>]
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
from datetime import date


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CONTRACT_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "contract.py")


def load_contract():
    spec = importlib.util.spec_from_file_location("mv_contract", CONTRACT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


contract = load_contract()
DEFAULT_STRUCTURE = "intro,verse1,pre-chorus,chorus,verse2,pre-chorus,chorus,bridge,chorus,outro"


def slug(s):
    s = re.sub(r"[^\w一-鿿-]+", "", (s or "").strip())
    return s or "新MV待定"


def build_visual_blueprint(title, meta):
    secs = "\n".join(f"- [{s}] → 画面：" for s in meta["structure"])
    return f"""# 视觉蓝图 — MV《{title}》

> 制MV 的"视觉宪法"。歌已做好（见 歌/、词/）；这里只定**怎么用画面承载这首歌**。

## 输入歌
- 歌：`歌/song.wav`（来自 写歌/<曲名>/ 或用户提供）
- 词：`词/lyrics.md`（卡拉OK 对齐用）
- 输入歌权利：{meta['song_rights_status']}

## MV 视觉概念
- 画幅：{meta['aspect']}　平台：{meta['target_platform']}
- MV用途：{meta['use_case']}
- 视觉风格：{meta['visual_style']}
- 主角 / 形象 + 锚定（跨镜一致）：
- 场景 / 世界观：
- 画风（global_style）：

## 段落 ↔ 画面映射（副歌高能、verse 叙事、bridge 反转）
{secs}

## 卡点策略
- {meta['beat_strategy']}；高潮加速；爽点对齐 beatgrid（mv-beat 产）。

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
| clip/timeline 规划 | mv-plan | [ ] |
| 出图 | mv-image | [ ] |
| 视频任务包 | mv-video/scripts/video_jobs.py | [ ] |
| 出视频登记/挑版 | mv-video + 后端 | [ ] |
| 卡拉OK字幕 | mv-lyric-sync | [ ] |
| 合成成片 | mv-compose | [ ] |
| 质检 | mv-review | [ ] |
| AI 使用披露 | mv-craft/scripts/ai_usage.py | [ ] |
| （可选）换脸 | shared-video-faceswap（公共） | [ ] |

## 导出
- [ ] 成片_MV.mp4
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True, help="曲名")
    ap.add_argument("--song", default=None, help="成品歌音频（拷入 歌/song.<ext>）")
    ap.add_argument("--lyrics", default=None, help="歌词 md（拷入 词/lyrics.md）")
    ap.add_argument("--platform", default="跨平台")
    ap.add_argument("--aspect", default="16:9", choices=contract.MV_ASPECTS)
    ap.add_argument("--structure", default=DEFAULT_STRUCTURE)
    ap.add_argument("--use-case", default=contract.DEFAULT_SETTINGS["MV用途"], choices=contract.MV_USE_CASES)
    ap.add_argument("--visual-style", default=contract.DEFAULT_SETTINGS["MV视觉风格"], choices=contract.MV_VISUAL_STYLES)
    ap.add_argument("--plan-granularity", default=contract.DEFAULT_SETTINGS["MV规划粒度"], choices=contract.MV_PLAN_GRANULARITY)
    ap.add_argument("--beat-strategy", default=contract.DEFAULT_SETTINGS["卡点策略"], choices=contract.MV_BEAT_STRATEGIES)
    ap.add_argument("--video-backend", default=contract.DEFAULT_SETTINGS["生视频AI"], choices=contract.MV_VIDEO_BACKENDS)
    ap.add_argument("--video-spec", default=contract.DEFAULT_SETTINGS["出视频规格"], choices=contract.MV_VIDEO_SPECS)
    ap.add_argument("--ai-visual-usage", default=contract.DEFAULT_SETTINGS["AI视觉使用披露"], choices=contract.AI_VISUAL_USAGE_MODES)
    ap.add_argument("--song-rights-status", default="original", help="original/licensed/public-domain/unknown")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out_root = os.path.abspath(args.out or os.path.join("制MV", slug(args.title)))
    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}（换 --title/--out 或先删）", file=sys.stderr)
        sys.exit(2)

    structure = [s.strip() for s in args.structure.split(",") if s.strip()]
    for sub in (
        "歌", "词", "节拍", "字幕", "分镜", "设定", "设定/characters", "设定/locations",
        "出图/共享", "出图/段落/prompt", "出图/段落/图片",
        "出视频/视频", "出视频/prompt", "出视频/takes", "导出", "合规",
    ):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    has_song = False
    if args.song and os.path.exists(args.song):
        ext = os.path.splitext(args.song)[1] or ".wav"
        target = "song.wav" if ext.lower() == ".wav" else f"song{ext}"
        shutil.copy(args.song, os.path.join(out_root, "歌", target))
        has_song = True
        
        # Check for demucs vocals
        vocals_src = os.path.join(os.path.dirname(args.song), "_demucs", "vocals", "vocals.wav")
        vocals_src_alt = os.path.join(os.path.dirname(args.song), "_demucs", "vocals.wav")
        v_src = vocals_src if os.path.exists(vocals_src) else (vocals_src_alt if os.path.exists(vocals_src_alt) else None)
        if v_src:
            os.makedirs(os.path.join(out_root, "歌", "_demucs"), exist_ok=True)
            shutil.copy(v_src, os.path.join(out_root, "歌", "_demucs", "vocals.wav"))
            
    has_lyrics = False
    if args.lyrics and os.path.exists(args.lyrics):
        shutil.copy(args.lyrics, os.path.join(out_root, "词", "lyrics.md"))
        has_lyrics = True

    publish_target = args.platform
    meta = {
        "schema_version": 1,
        "kind": "mv",
        "title": args.title,
        "target_platform": args.platform,
        "publish_target": publish_target,
        "aspect": args.aspect,
        "structure": structure,
        "use_case": args.use_case,
        "visual_style": args.visual_style,
        "plan_granularity": args.plan_granularity,
        "beat_strategy": args.beat_strategy,
        "image_backend": "Codex",
        "video_backend": args.video_backend,
        "video_spec": args.video_spec,
        "ai_visual_usage": args.ai_visual_usage,
        "song_rights_status": args.song_rights_status,
        "source_song": os.path.abspath(args.song) if args.song else None,
        "has_song": has_song,
        "has_lyrics": has_lyrics,
        "created_at": date.today().isoformat(),
    }
    settings = {
        "MV用途": args.use_case,
        "MV视觉风格": args.visual_style,
        "MV规划粒度": args.plan_granularity,
        "卡点策略": args.beat_strategy,
        "生图AI": "Codex",
        "生视频AI": args.video_backend,
        "出视频规格": args.video_spec,
        "合成画幅": args.aspect,
        "AI视觉使用披露": args.ai_visual_usage,
        "发行目标平台": publish_target,
    }
    with open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    write(os.path.join(out_root, "_设置.md"), contract.settings_markdown(args.title, settings))
    write(os.path.join(out_root, "视觉蓝图.md"), build_visual_blueprint(args.title, meta))
    write(os.path.join(out_root, "_进度.md"), build_progress(args.title, meta))

    print(f"[ok] 制MV 项目骨架 → {out_root}")
    print(f"     _设置.md / 视觉蓝图.md / 分镜/ / 歌/{'(已入)' if has_song else '(待放成品歌)'} / 词/{'(已入)' if has_lyrics else '(待放)'}")
    print("     节拍/ 字幕/ 设定/ 出图/ 出视频/ 合规/ ← 预建（mv 自家阶段产物）")
    print(f"     _meta: kind=mv 平台={args.platform} 画幅={args.aspect} 风格={args.visual_style}")
    print("[next] 放入成品歌 → mv-beat → mv-plan → mv-image → video_jobs.py → mv-video → mv-lyric-sync → mv-compose")


if __name__ == "__main__":
    main()
