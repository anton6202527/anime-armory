#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic gates for MV stages."""
import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import mv_utils


def _settings_mode(root, meta):
    settings = mv_utils.parse_settings(root)
    return meta.get("song_timing") or settings.get("歌曲输入时序") or "先传音乐"


def _has_rough_blueprint(root):
    text = mv_utils.read_text(os.path.join(root, "视觉蓝图.md"))
    return "rough（待成品歌/beatgrid 复核）" in text or "状态：rough" in text


def _load_plan(root):
    return mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}


def check(root, stage):
    errors = []
    warnings = []
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    mode = _settings_mode(root, meta)
    song = mv_utils.find_song(root)
    lyrics = os.path.join(root, "词", "lyrics.md")
    beatgrid = os.path.join(root, "节拍", "beatgrid.json")
    blueprint = os.path.join(root, "视觉蓝图.md")
    clip_plan = os.path.join(root, "分镜", "clip_plan.json")
    timeline = os.path.join(root, "分镜", "timeline_manifest.json")

    if stage in {"beat", "plan", "image", "video_jobs", "lyric_sync", "compose"} and not song:
        errors.append("缺 歌/song.*，先用 song 线产出或让用户上传最终成品歌")
    if stage in {"plan", "image", "video_jobs", "lyric_sync", "compose"} and not os.path.exists(lyrics):
        errors.append("缺 词/lyrics.md")
    if stage in {"plan", "image", "video_jobs", "compose"} and not os.path.exists(beatgrid):
        errors.append("缺 节拍/beatgrid.json，先跑 mv-beat")
    if stage in {"script_review", "plan", "image", "video_jobs"} and not os.path.exists(blueprint):
        errors.append("缺 视觉蓝图.md")
    if stage in {"plan", "image", "video_jobs", "compose"} and _has_rough_blueprint(root):
        errors.append("视觉蓝图仍是 rough，正式产物阶段前先用 mv-script 复核")
    if stage in {"image", "video_jobs", "compose"} and not os.path.exists(clip_plan):
        errors.append("缺 分镜/clip_plan.json，先跑 mv-plan")
    if stage == "compose" and not os.path.exists(timeline):
        errors.append("缺 分镜/timeline_manifest.json，compose 默认不按目录猜顺序")

    if stage == "video_jobs" and os.path.exists(clip_plan):
        plan = _load_plan(root)
        missing = []
        for clip in plan.get("clips", []):
            image_path = clip.get("image_path")
            if image_path and not os.path.exists(os.path.join(root, image_path)):
                missing.append(f"{clip.get('clip_id')}:{image_path}")
        if missing:
            errors.append(f"缺 {len(missing)} 个首帧 PNG，先跑 mv-image；例：{missing[0]}")

    if stage == "compose" and os.path.exists(timeline):
        data = mv_utils.load_json(timeline, {}) or {}
        missing = []
        for clip in data.get("clips", []):
            video_path = clip.get("video_path")
            if not video_path or not os.path.exists(os.path.join(root, video_path)):
                missing.append(clip.get("clip_id") or video_path or "unknown")
        if missing:
            errors.append(f"timeline 有 {len(missing)} 个 clip 未选中视频，例：{missing[0]}")

    if stage == "lyric_sync" and os.path.exists(lyrics):
        lines = [
            x.strip() for x in mv_utils.read_text(lyrics).splitlines()
            if x.strip() and not x.strip().startswith("#") and not mv_utils.SECTION_RE.match(x.strip())
        ]
        if not lines:
            errors.append("词/lyrics.md 没有可对齐歌词行")

    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description="检查制MV阶段前置 gate")
    ap.add_argument("project_root")
    ap.add_argument("stage")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    errors, warnings = check(root, args.stage)
    for msg in warnings:
        print(f"[warn] {msg}")
    if errors:
        for msg in errors:
            print(f"[err] {msg}", file=sys.stderr)
        return 1
    print(f"[ok] gate pass: {args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
