#!/usr/bin/env python3
"""Bind a human picture-lock decision to the exact plan, animatic, song and frames."""
import argparse
import os
import sys
from datetime import date

import mv_utils


def build_lock(root, reviewer, notes):
    reviewer = str(reviewer or "").strip()
    lowered = reviewer.lower()
    if len(reviewer) < 2 or any(
        token in lowered for token in ("codex", "chatgpt", "claude", "agent", "bot", "机器人", "自动化")
    ) or reviewer in {"待填", "待定", "匿名"}:
        raise RuntimeError("picture lock 必须记录真实具名人工 reviewer")
    notes = str(notes or "").strip()
    if not notes or notes in {"待填", "待定", "n/a"}:
        raise RuntimeError("picture lock 必须记录非空审片说明")
    plan = mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}
    settings = mv_utils.parse_settings(root)
    required = [
        "分镜/clip_plan.json",
        "分镜/timeline_manifest.json",
        "节拍/beatgrid.json",
        "分镜/animatic.mp4",
        "生产数据/animatic/animatic.json",
        "生产数据/image_qc/image_qc.json",
        "分镜/timeline.otio",
        "生产数据/otio/otio_receipt.json",
    ]
    # picture lock precedes paid video generation, so preview/demo labels cannot
    # weaken its evidence set.  Route decisions come from settings, never from
    # the compatibility-only `_meta.is_demo` mirror.
    required.extend(("评分/pacing_prescore.json", "分镜/semantic_prompts.json"))
    vocal_performance = any(
        clip.get("action_family") == "performance_vocal" or clip.get("vocal_lyrics")
        for clip in plan.get("clips", []) if isinstance(clip, dict)
    )
    if settings.get("字幕语言", "中文") != "无字幕" or (
        vocal_performance and settings.get("演唱口型", "仅正面演唱镜") != "关闭"
    ):
        required.append("字幕/alignment_report.json")
    missing = [rel for rel in required if not os.path.exists(os.path.join(root, rel))]
    if missing:
        raise RuntimeError(f"picture lock 缺前置：{', '.join(missing)}")
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    otio_receipt = mv_utils.load_json(os.path.join(root, "生产数据", "otio", "otio_receipt.json"), {}) or {}
    editorial_hash = mv_utils.timeline_edit_hash(timeline)
    if otio_receipt.get("timeline_edit_sha256") != editorial_hash:
        raise RuntimeError("OTIO 与当前 timeline 编辑决定不一致；先重跑 production_pack.py 或 export_otio.py")
    # timeline/OTIO themselves may receive selected media paths after lock;
    # bind their normalized edit contract instead of the mutable raw files.
    paths = [rel for rel in required if rel not in {"分镜/timeline_manifest.json", "分镜/timeline.otio", "生产数据/otio/otio_receipt.json"}]
    song = mv_utils.find_song(root)
    if not song:
        raise RuntimeError("缺 歌/song.*")
    paths.append(mv_utils.relpath(root, song))
    for clip in plan.get("clips", []):
        if clip.get("image_path"):
            paths.append(clip["image_path"])
        if clip.get("need_end_frame") and clip.get("end_frame_path"):
            paths.append(clip["end_frame_path"])
        if clip.get("image_prompt_path"):
            paths.append(clip["image_prompt_path"])
        if clip.get("video_prompt_path"):
            paths.append(clip["video_prompt_path"])
    for optional in ("视觉蓝图.md", "词/lyrics.md", "分镜/semantic_prompts.json"):
        if os.path.exists(os.path.join(root, optional)):
            paths.append(optional)
    paths = list(dict.fromkeys(paths))
    missing_bound = [rel for rel in paths if not os.path.exists(os.path.join(root, rel))]
    if missing_bound:
        raise RuntimeError(f"picture lock 缺待签收输入：{missing_bound[0]}")
    return {
        "schema_version": 2, "kind": "mv_picture_lock", "accepted": True,
        "reviewer": reviewer, "date": date.today().isoformat(), "notes": notes,
        "decision": "picture_locked",
        "review_dimensions": [
            "narrative", "coverage", "musical_sections", "cut_rhythm", "action_peak",
            "seam_intent", "screen_direction", "identity", "wardrobe_props",
            "scene_topology", "color_script", "subtitle_safe_area",
        ],
        "editorial_timeline_sha256": editorial_hash,
        "otio_timeline_sha256": otio_receipt.get("timeline_edit_sha256"),
        "inputs_sha256": {rel: mv_utils.content_hash(os.path.join(root, rel)) for rel in paths},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    root = os.path.abspath(args.project_root)
    try:
        payload = build_lock(root, args.reviewer, args.notes)
    except RuntimeError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 1
    path = os.path.join(root, "制片", "picture_lock.json")
    mv_utils.write_json(path, payload)
    mv_utils.update_progress_stage(root, "picture_lock")
    print(f"[ok] picture lock → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
