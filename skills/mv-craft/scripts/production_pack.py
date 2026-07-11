#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate traditional MV production-planning artifacts from clip_plan."""
import argparse
import csv
import importlib.util
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
MV_UTILS_PATH = os.path.join(HERE, "mv_utils.py")


def load_mv_utils():
    spec = importlib.util.spec_from_file_location("mv_utils", MV_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mv_utils = load_mv_utils()
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import export_otio


def setup_key(clip):
    shot = clip.get("shot_design") or {}
    return shot.get("setup_group") or f"{clip.get('section', 'unknown')}/{shot.get('location_id', 'LOC_UNKNOWN')}"


def build_artifacts(root):
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    plan = mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}
    timeline = mv_utils.load_json(os.path.join(root, "分镜", "timeline_manifest.json"), {}) or {}
    jobs = mv_utils.load_json(os.path.join(root, "出视频", "jobs_manifest.json"), {}) or {}
    job_by_id = {j.get("clip_id"): j for j in jobs.get("jobs", [])}
    clips = plan.get("clips") or []

    shot_list = []
    setups = {}
    for idx, clip in enumerate(clips, 1):
        shot = clip.get("shot_design") or {}
        c = clip.get("continuity") or {}
        job = job_by_id.get(clip.get("clip_id"), {})
        key = setup_key(clip)
        setups.setdefault(key, {
            "setup_group": key,
            "location_id": shot.get("location_id", ""),
            "location_name": shot.get("location_name", ""),
            "lighting": shot.get("lighting", ""),
            "clips": [],
            "notes": shot.get("production_design", ""),
        })
        setups[key]["clips"].append(clip.get("clip_id"))
        shot_list.append({
            "order": idx,
            "clip_id": clip.get("clip_id"),
            "section": clip.get("section"),
            "time": f"{clip.get('start')}-{clip.get('end')}",
            "duration": clip.get("duration"),
            "setup_group": key,
            "shot_size": shot.get("shot_size"),
            "angle": shot.get("angle"),
            "camera_movement": shot.get("camera_movement"),
            "lens_feel": shot.get("lens_feel"),
            "blocking": shot.get("blocking"),
            "lighting": shot.get("lighting"),
            "action": c.get("action"),
            "transition": clip.get("transition"),
            "selected_take": job.get("selected_take"),
            "selected_video_path": job.get("selected_video_path") or clip.get("selected_video_path"),
        })

    animatic = {
        "schema_version": 1,
        "kind": "mv_animatic_manifest",
        "generated_at": date.today().isoformat(),
        "title": meta.get("title") or plan.get("title"),
        "scope": plan.get("scope") or "full",
        "song_path": timeline.get("song_path") or "歌/song.wav",
        "clips": [
            {
                "clip_id": c.get("clip_id"),
                "start": c.get("start"),
                "end": c.get("end"),
                "duration": c.get("duration"),
                "image_path": c.get("image_path"),
                "video_path": (job_by_id.get(c.get("clip_id"), {}) or {}).get("selected_video_path") or c.get("selected_video_path"),
                "lyric_hint": c.get("lyric_hint"),
                "action_peak_relative": c.get("action_peak_relative"),
            }
            for c in clips
        ],
        "usage": "Use this as a storyboard/animatic truth source; rebuild after formal full-song mv-plan.",
    }
    return shot_list, list(setups.values()), animatic


def write_artifacts(root, shot_list, setups, animatic):
    prod_dir = os.path.join(root, "制片")
    mv_utils.write_json(os.path.join(root, "分镜", "animatic_manifest.json"), animatic)
    mv_utils.write_json(os.path.join(prod_dir, "shot_list.json"), {
        "schema_version": 1,
        "kind": "mv_shot_list",
        "generated_at": date.today().isoformat(),
        "shots": shot_list,
    })
    setup_lines = ["# setup schedule", "", "| Setup | Location | Lighting | Clips | Notes |", "|---|---|---|---|---|"]
    for s in setups:
        setup_lines.append(f"| {s['setup_group']} | {s.get('location_name','')} | {s.get('lighting','')} | {', '.join(s.get('clips') or [])} | {s.get('notes','')} |")
    mv_utils.write_text(os.path.join(prod_dir, "setup_schedule.md"), "\n".join(setup_lines) + "\n")

    take_log_path = os.path.join(prod_dir, "take_log.csv")
    os.makedirs(os.path.dirname(take_log_path), exist_ok=True)
    with open(take_log_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["clip_id", "take_id", "source", "motion", "identity", "beat_fit", "clarity", "selected", "notes"])
        for shot in shot_list:
            writer.writerow([shot["clip_id"], "", "", "", "", "", "", "", ""])

    checklist = [
        "# picture lock / color pass checklist",
        "",
        "## Picture Lock",
        "- [ ] timeline_manifest 与 clip_plan clip_id 完全一致",
        "- [ ] 每个 clip selected_take 已登记来源、评分和挑版理由",
        "- [ ] video_inherit_contract hard_blocks=0",
        "- [ ] video_qc hard_blocks=0",
        "- [ ] 字幕 alignment_report 覆盖目标范围",
        "- [ ] 成片音轨来自主歌轨，不混入未授权 clip audio",
        "",
        "## Color Pass",
        "- [ ] 段落主色继承 palette_anchor",
        "- [ ] 同 setup_group 内曝光/白平衡/颗粒一致",
        "- [ ] 副歌高光增强但不换主画风",
        "- [ ] 字幕安全区可读，主体不遮挡歌词",
        "",
        "## Deliverables",
        "- [ ] 合规/ai_usage.json 已写",
        "- [ ] 目标平台画幅、码率、字幕位置已确认",
        "- [ ] demo/full scope 已在 _meta 和 alignment_report 明确",
    ]
    mv_utils.write_text(os.path.join(prod_dir, "picture_lock_color_checklist.md"), "\n".join(checklist) + "\n")
    mv_utils.write_json(os.path.join(root, "分镜", "timeline.otio"), export_otio.build(root))
    return prod_dir


def main():
    ap = argparse.ArgumentParser(description="Generate MV production-planning artifacts")
    ap.add_argument("project_root")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    shot_list, setups, animatic = build_artifacts(root)
    out = write_artifacts(root, shot_list, setups, animatic)
    print(f"[ok] production pack → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
