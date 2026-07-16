#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建【制MV】项目骨架（输入=成品歌或歌曲企划，做视频）。

制MV 线可消费一首"已经做好的歌"（用户给的音频或本项目内文件），
也可先按歌曲企划做 rough 视觉蓝图，等最终歌入库后再进入正式卡点和 timeline。
mv 系列自包含，不复用其它家族 skill；出图/出视频/合成都由 mv 自家 skill 产出。

用法:
    python3 init_project.py --title "<曲名>" \\
    [--song <成品歌.wav/mp3>] [--lyrics <lyrics.md>] [--song-timing 先传音乐|后配歌曲] \\
        [--platform 抖音|网易云|跨平台] [--aspect 16:9|9:16] \\
        [--visual-style 电影叙事] [--plan-granularity 标准] [--out <根>]
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import uuid
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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_synopsis(title, visual_style, use_case):
    """立项当刻用既有 MV用途/视觉风格 组一句作品卡片简介（≤240 字）。

    只用 mv 本线 _meta 既有字段；缺则占位后续回填。不跨线取数。
    """
    style = (visual_style or "").strip()
    use = (use_case or "").strip()
    if style and use:
        text = f"《{title}》——{style}风格的{use} MV。"
    elif use:
        text = f"《{title}》——{use} MV。"
    elif style:
        text = f"《{title}》——{style}风格 MV。"
    else:
        text = f"《{title}》——制MV 作品（简介待补）。"
    return text[:240]


def build_visual_blueprint(title, meta):
    secs = "\n".join(f"- [{s}] → 画面：" for s in meta["structure"])
    rough_status = (
        "rough（待成品歌/beatgrid 复核）"
        if meta["song_timing"] == "后配歌曲" and not meta["has_song"]
        else "正式蓝图输入就绪"
    )
    song_line = (
        "`歌/song.wav`（待用户提供或本项目内补入最终音频）"
        if meta["song_timing"] == "后配歌曲" and not meta["has_song"]
        else "`歌/song.wav`（本项目输入音频）"
    )
    if (meta.get("subtitle_language") == "无字幕"
            and meta.get("lip_sync_mode") == "关闭" and not meta["has_lyrics"]):
        lyrics_line = "无（纯器乐/纯视觉路线：无字幕且关闭演唱口型）"
    elif meta["song_timing"] == "后配歌曲" and not meta["has_lyrics"]:
        lyrics_line = "`词/lyrics.md`（可先用草稿；最终歌入库后按实唱复核）"
    else:
        lyrics_line = "`词/lyrics.md`（字幕/唱演时间轴用）"
    timing_note = (
        "本项目选择【后配歌曲】：当前视觉蓝图只能做 rough 概念；最终歌定稿/上传后必须重跑 mv-beat，并用真实 beatgrid 复核蓝图与 timeline。"
        if meta["song_timing"] == "后配歌曲"
        else "本项目选择【先传音乐】：先锁成品歌与歌词，再按真实 beatgrid 做视觉蓝图与 timeline。"
    )
    return f"""# 视觉蓝图 — MV《{title}》

> 制MV 的"视觉宪法"。本文件只定**怎么用画面承载这首歌**；后配歌曲模式下先做 rough，最终歌入库后必须复核。

## 输入歌
- 状态：{rough_status}
- 歌：{song_line}
- 词：{lyrics_line}
- 歌曲输入时序：{meta['song_timing']}
- 输入歌权利：{meta['song_rights_status']}
- 流程提示：{timing_note}

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
    stage_lines = []
    done = {
        "setup": True,
        "song_ingest": meta["has_song"],
    }
    for st in contract.workflow_stage_table(
        meta["song_timing"], meta.get("subtitle_language"), meta.get("lip_sync_mode")
    ):
        status = "[x]" if done.get(st["key"], False) else "[ ]"
        if st["key"] == "song_ingest" and not meta["has_song"] and meta["song_timing"] == "后配歌曲":
            note = "（视觉草案后再补）"
        elif st["key"] == "beat" and not meta["has_song"]:
            note = "（等歌定稿）"
        elif st["key"] == "script" and meta["song_timing"] == "后配歌曲" and not meta["has_song"]:
            note = "（rough，歌定稿后复核）"
        elif st["key"] == "script_review" and meta["song_timing"] == "后配歌曲" and not meta["has_song"]:
            note = "（等歌定稿+beatgrid）"
        else:
            note = ""
        stage_lines.append(f"| {st['label']}{note} | {st['owner']} | {status} |")
    stages = "\n".join(stage_lines)
    lyrics_optional = meta.get("subtitle_language") == "无字幕" and meta.get("lip_sync_mode") == "关闭"
    return f"""# 进度 — 制MV《{title}》

> 平台={meta['target_platform']} 画幅={meta['aspect']} 段落={len(meta['structure'])}。歌曲输入时序={meta['song_timing']}。输入歌={'已入' if meta['has_song'] else '待放入 歌/'}。

## 输入
- [{'x' if meta['has_song'] else ' '}] 歌/song.wav（本项目输入音频）
- [{'x' if meta['has_lyrics'] else ' '}] 词/lyrics.md（{'纯器乐路线可选' if lyrics_optional else '字幕/唱演时间轴必需'}）

## 制MV 阶段
| 阶段 | skill | 状态 |
|---|---|---|
{stages}

## 作品封面（卡片竖版 key visual）
- [ ] 封面 prompt/job 包（`出图/封面/`；纯净机仅产 job 包，`_meta.cover` 保持 null）
- [ ] 封面已渲染并回填 `_meta.cover`

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
    ap.add_argument("--song-timing", default=None, choices=contract.MV_SONG_TIMINGS,
                    help="歌曲输入时序：先传音乐=先锁音频再卡点；后配歌曲=先做视觉草案，歌定稿后再卡点")
    ap.add_argument("--platform", default="跨平台")
    ap.add_argument("--aspect", default="16:9", choices=contract.MV_ASPECTS)
    ap.add_argument("--structure", default=DEFAULT_STRUCTURE)
    ap.add_argument("--use-case", default=contract.DEFAULT_SETTINGS["MV用途"], choices=contract.MV_USE_CASES)
    ap.add_argument("--visual-style", default=contract.DEFAULT_SETTINGS["MV视觉风格"], choices=contract.MV_VISUAL_STYLES)
    ap.add_argument("--plan-granularity", default=contract.DEFAULT_SETTINGS["MV规划粒度"], choices=contract.MV_PLAN_GRANULARITY)
    ap.add_argument("--beat-strategy", default=contract.DEFAULT_SETTINGS["卡点策略"], choices=contract.MV_BEAT_STRATEGIES)
    ap.add_argument("--image-model", default=contract.DEFAULT_SETTINGS["生图模型"], choices=contract.MV_IMAGE_MODELS)
    ap.add_argument("--image-channel", default=contract.DEFAULT_SETTINGS["生图渠道"], choices=contract.MV_IMAGE_CHANNELS)
    ap.add_argument("--video-model", default=None, choices=contract.MV_VIDEO_MODELS,
                    help="可选：固定/覆盖生视频模型；默认不在立项时强问")
    ap.add_argument("--video-channel", default=None, choices=contract.MV_VIDEO_CHANNELS,
                    help="可选：固定/覆盖生视频渠道/产品；默认在 mv-video 阶段按可用入口处理")
    ap.add_argument("--video-backend", default=None, choices=contract.MV_VIDEO_BACKENDS,
                    help="兼容旧参数：等同于 --video-channel")
    ap.add_argument("--video-spec", default=contract.DEFAULT_SETTINGS["出视频规格"], choices=contract.MV_VIDEO_SPECS)
    ap.add_argument("--lip-sync", default=contract.DEFAULT_SETTINGS["演唱口型"], choices=contract.MV_LIPSYNC_MODES)
    ap.add_argument("--subtitle-language", default=contract.DEFAULT_SETTINGS["字幕语言"], choices=contract.MV_SUBTITLE_MODES)
    ap.add_argument("--ai-visual-usage", default=contract.DEFAULT_SETTINGS["AI视觉使用披露"], choices=contract.AI_VISUAL_USAGE_MODES)
    ap.add_argument("--song-rights-status", default="original",
                    help="original/licensed/public-domain/unknown（仓库默认用户为歌曲权利人；明确第三方素材时必须改成对应状态）")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out_root = os.path.abspath(args.out or os.path.join("创作区", "制MV", slug(args.title)))
    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}（换 --title/--out 或先删）", file=sys.stderr)
        sys.exit(2)

    structure = [s.strip() for s in args.structure.split(",") if s.strip()]
    song_timing = args.song_timing or contract.DEFAULT_SETTINGS["歌曲输入时序"]
    video_model = args.video_model or contract.DEFAULT_SETTINGS["生视频模型"]
    video_channel = args.video_channel or args.video_backend or contract.DEFAULT_SETTINGS["生视频渠道"]
    for sub in (
        "歌", "词", "节拍", "字幕", "分镜", "设定", "设定/characters", "设定/locations",
        "出图/共享", "出图/段落/prompt", "出图/段落/图片",
        "出图/封面/prompt", "出图/封面/图片",
        "出视频/视频", "出视频/prompt", "出视频/takes", "导出", "合规",
    ):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    has_song = False
    source_song_rel = None
    source_song_sha256 = None
    if args.song and os.path.exists(args.song):
        ext = os.path.splitext(args.song)[1] or ".wav"
        target = "song.wav" if ext.lower() == ".wav" else f"song{ext}"
        imported_song = os.path.join(out_root, "歌", target)
        shutil.copy(args.song, imported_song)
        has_song = True
        source_song_rel = f"歌/{target}"
        source_song_sha256 = sha256_file(imported_song)
        
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
        "project_id": f"mv_{uuid.uuid4().hex[:16]}",
        "line": "mv",
        "title": args.title,
        "target_platform": args.platform,
        "publish_target": publish_target,
        "aspect": args.aspect,
        "structure": structure,
        "use_case": args.use_case,
        "synopsis": build_synopsis(args.title, args.visual_style, args.use_case),
        "cover": None,
        "song_timing": song_timing,
        "visual_style": args.visual_style,
        "plan_granularity": args.plan_granularity,
        "beat_strategy": args.beat_strategy,
        "image_model": args.image_model,
        "image_channel": args.image_channel,
        "image_backend": args.image_channel,
        "video_model": video_model,
        "video_channel": video_channel,
        "video_backend": video_channel,
        "video_spec": args.video_spec,
        "lip_sync_mode": args.lip_sync,
        "subtitle_language": args.subtitle_language,
        "ai_visual_usage": args.ai_visual_usage,
        "song_rights_status": args.song_rights_status,
        "source_song": source_song_rel,
        "source_song_origin": ({
            "original_name": os.path.basename(args.song),
            "imported_copy_rel": source_song_rel,
            "sha256": source_song_sha256,
        } if source_song_rel else None),
        "has_song": has_song,
        "has_lyrics": has_lyrics,
        "is_demo": args.use_case in {"短视频Hook", "歌曲Demo"},
        "created_at": date.today().isoformat(),
    }
    settings = {
        "MV用途": args.use_case,
        "歌曲输入时序": song_timing,
        "MV视觉风格": args.visual_style,
        "MV规划粒度": args.plan_granularity,
        "卡点策略": args.beat_strategy,
        "生图AI": args.image_channel,
        "生图模型": args.image_model,
        "生图渠道": args.image_channel,
        "生视频模型": video_model,
        "生视频渠道": video_channel,
        "出视频规格": args.video_spec,
        "演唱口型": args.lip_sync,
        "字幕语言": args.subtitle_language,
        "合成画幅": args.aspect,
        "AI视觉使用披露": args.ai_visual_usage,
        "发行目标平台": publish_target,
    }
    with open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.makedirs(os.path.join(out_root, "生产数据"), exist_ok=True)
    with open(os.path.join(out_root, "生产数据", "artifact_catalog.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1, "kind": "artifact_catalog", "status": "bootstrap",
            "generated_at": date.today().isoformat(),
            "project": {"project_id": meta["project_id"], "line": "mv", "title": args.title, "root_rel": "."},
            "summary": {"artifact_count": 0, "total_bytes": 0, "disposable_bytes": 0, "invalid_count": 0},
            "event_sources": [], "view_sources": [], "artifacts": [], "duplicates": [],
        }, f, ensure_ascii=False, indent=2)
    write(os.path.join(out_root, "_设置.md"), contract.settings_markdown(args.title, settings))
    write(os.path.join(out_root, "视觉蓝图.md"), build_visual_blueprint(args.title, meta))
    write(os.path.join(out_root, "_进度.md"), build_progress(args.title, meta))

    print(f"[ok] 制MV 项目骨架 → {out_root}")
    print(f"     _设置.md / 视觉蓝图.md / 分镜/ / 歌/{'(已入)' if has_song else '(待放成品歌)'} / 词/{'(已入)' if has_lyrics else '(待放)'}")
    print("     节拍/ 字幕/ 设定/ 出图/ 出视频/ 合规/ ← 预建（mv 自家阶段产物）")
    print(f"     _meta: kind=mv 平台={args.platform} 画幅={args.aspect} 风格={args.visual_style} 歌曲输入时序={song_timing}")
    lyric_step = " → mv-lyric-sync" if args.subtitle_language != "无字幕" or args.lip_sync != "关闭" else ""
    if song_timing == "后配歌曲" and not has_song:
        print(f"[next] mv-script rough视觉蓝图 → 补入成品歌 → mv-beat{lyric_step} → mv-script复核 → mv-plan → mv-score → mv-image → picture lock → mv-video → mv-compose")
    else:
        print(f"[next] 放入/确认成品歌 → mv-beat{lyric_step} → mv-script → mv-plan → mv-score → mv-image → picture lock → video_jobs.py → mv-video → mv-compose")


if __name__ == "__main__":
    main()
