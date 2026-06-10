#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create and maintain MV video generation job manifests.

Usage:
    python3 video_jobs.py <制MV作品根>
    python3 video_jobs.py <制MV作品根> --register ./clip.mp4 --clip Clip_001 --take 1
    python3 video_jobs.py <制MV作品根> --score Clip_001 --take 1 --motion-score 5 --identity-score 4
    python3 video_jobs.py <制MV作品根> --select Clip_001 --take 1
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
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "mv_utils.py")

def load_contract():
    spec = importlib.util.spec_from_file_location("mv_contract", CONTRACT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def load_mv_utils():
    spec = importlib.util.spec_from_file_location("mv_utils", MV_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

contract = load_contract()
mv_utils = load_mv_utils()

def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def normalize_clip_id(value):
    text = str(value or "").strip()
    if re.fullmatch(r"\d+", text):
        return f"Clip_{int(text):03d}"
    if re.fullmatch(r"clip[_-]?\d+", text, flags=re.I):
        n = re.search(r"\d+", text).group(0)
        return f"Clip_{int(n):03d}"
    if re.fullmatch(r"Clip_\d{3,}", text):
        return text
    raise SystemExit(f"[err] clip id 无效：{value}（用 1 / Clip_001）")


def normalize_take_id(value):
    text = str(value or "").strip()
    if re.fullmatch(r"\d+", text):
        return f"take_{int(text):02d}"
    if re.fullmatch(r"take[_-]?\d+", text, flags=re.I):
        n = re.search(r"\d+", text).group(0)
        return f"take_{int(n):02d}"
    raise SystemExit(f"[err] take id 无效：{value}（用 1 / take_01）")


def prompt_for_take(clip, backend, spec_profile, take_id):
    c = clip.get("continuity", {})
    lines = [
        f"# {clip['clip_id']} {take_id} 视频生成任务",
        "",
        f"- 后端：{backend}",
        f"- 分辨率：{spec_profile['resolution']}",
        f"- 帧率：{spec_profile['fps']}fps",
        f"- 质量档：{spec_profile['quality']}",
        f"- 首帧：`{clip.get('image_path')}`",
        f"- 时长：{clip.get('duration')}s",
        f"- 转场：{clip.get('transition')}",
        "",
        "## continuity",
        f"- start_state：{c.get('start_state', '')}",
        f"- action：{c.get('action', '')}",
        f"- end_state：{c.get('end_state', '')}",
        f"- constraints：{c.get('constraints', '')}",
        f"- negative：{c.get('negative', '')}",
        "",
        "## Prompt",
        f"人物运动：{c.get('action', '')}；镜头运动：服务 {clip.get('section')} 段落张力；动态细节：发丝、衣摆、光斑或环境粒子随节拍变化；卡点约束：动作峰值对齐 {clip.get('end')}s；声音约束：无对白、无旁白、不要生成原生人声。",
    ]
    return "\n".join(lines) + "\n"


def create_jobs(root, args):
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    plan = mv_utils.load_json(plan_path, None)
    if not plan:
        raise SystemExit("[err] 缺 分镜/clip_plan.json，先跑 mv-plan/scripts/plan_clips.py")
    settings = mv_utils.parse_settings(root)
    backend = args.backend or settings.get("生视频AI") or "即梦"
    spec = args.video_spec or settings.get("出视频规格") or "预算一般"
    if backend not in contract.MV_VIDEO_BACKENDS:
        raise SystemExit(f"[err] 不支持的生视频AI：{backend}")
    profile = contract.video_spec_profile(spec)
    jobs = []
    for clip in plan.get("clips", []):
        image_path = clip.get("image_path")
        if image_path:
            full_image_path = os.path.join(root, image_path)
            if not os.path.exists(full_image_path):
                print(f"[warn] {clip['clip_id']} 缺首帧 PNG：{image_path}，请确保 mv-image 出图完毕再开始生成视频。")
                
        requested = profile["key_takes"] if clip.get("beat_role") == "key" else profile["normal_takes"]
        takes = []
        for i in range(1, requested + 1):
            take_id = f"take_{i:02d}"
            prompt_path = os.path.join("出视频", "prompt", f"{clip['clip_id']}_{take_id}.md")
            mv_utils.write_text(os.path.join(root, prompt_path), prompt_for_take(clip, backend, profile, take_id))
            takes.append({
                "take_id": take_id,
                "status": "planned",
                "prompt_path": prompt_path,
                "video_path": os.path.join("出视频", "takes", clip["clip_id"], f"{take_id}.mp4"),
                "score": {},
                "notes": "",
                "registered_at": None,
            })
        jobs.append({
            "clip_id": clip["clip_id"],
            "section": clip["section"],
            "duration": clip["duration"],
            "beat_role": clip.get("beat_role", "normal"),
            "backend": backend,
            "video_spec": spec,
            "requested_takes": requested,
            "selected_take": None,
            "selected_video_path": clip.get("selected_video_path") or os.path.join("出视频", "视频", f"{clip['clip_id']}.mp4"),
            "takes": takes,
        })
    manifest = {
        "schema_version": 1,
        "kind": "mv_video_jobs",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": plan.get("title") or os.path.basename(root),
        "backend": backend,
        "video_spec": spec,
        "spec_profile": profile,
        "clip_plan_path": "分镜/clip_plan.json",
        "jobs": jobs,
    }
    out = os.path.join(root, "出视频", "jobs_manifest.json")
    mv_utils.write_json(out, manifest)
    return out, manifest


def load_manifest(root):
    path = os.path.join(root, "出视频", "jobs_manifest.json")
    if not os.path.exists(path):
        raise SystemExit("[err] 缺 出视频/jobs_manifest.json，先运行 video_jobs.py 生成任务包")
    return path, mv_utils.load_json(path, {})


def find_job(manifest, clip_id):
    for job in manifest.get("jobs", []):
        if job.get("clip_id") == clip_id:
            return job
    raise SystemExit(f"[err] manifest 里没有 {clip_id}")


def find_take(job, take_id):
    for take in job.get("takes", []):
        if take.get("take_id") == take_id:
            return take
    raise SystemExit(f"[err] {job.get('clip_id')} 没有 {take_id}")


def register_take(root, clip_id, take_id, src):
    if not os.path.exists(src):
        raise SystemExit(f"[err] 找不到视频文件：{src}")
    manifest_path, manifest = load_manifest(root)
    job = find_job(manifest, clip_id)
    take = find_take(job, take_id)
    dst = os.path.join(root, take["video_path"])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)
    take["status"] = "registered"
    take["registered_at"] = date.today().isoformat()
    mv_utils.write_json(manifest_path, manifest)
    return dst


def score_take(root, clip_id, take_id, args):
    manifest_path, manifest = load_manifest(root)
    job = find_job(manifest, clip_id)
    take = find_take(job, take_id)
    score = dict(take.get("score") or {})
    for key, attr in (
        ("motion", "motion_score"),
        ("identity", "identity_score"),
        ("beat_fit", "beat_score"),
        ("clarity", "clarity_score"),
    ):
        value = getattr(args, attr)
        if value is not None:
            score[key] = value
    nums = [v for v in score.values() if isinstance(v, (int, float))]
    if nums:
        score["average"] = round(sum(nums) / len(nums), 2)
    take["score"] = score
    if args.notes is not None:
        take["notes"] = args.notes
    if take.get("status") == "planned":
        take["status"] = "scored"
    mv_utils.write_json(manifest_path, manifest)


def select_take(root, clip_id, take_id):
    manifest_path, manifest = load_manifest(root)
    job = find_job(manifest, clip_id)
    take = find_take(job, take_id)
    src = os.path.join(root, take["video_path"])
    if not os.path.exists(src):
        raise SystemExit(f"[err] {clip_id} {take_id} 尚未登记视频：{take['video_path']}")
    dst = os.path.join(root, job["selected_video_path"])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)
    for row in job.get("takes", []):
        if row["take_id"] == take_id:
            row["status"] = "selected"
        elif row.get("status") == "selected":
            row["status"] = "registered"
    job["selected_take"] = take_id
    job["selected_at"] = date.today().isoformat()
    mv_utils.write_json(manifest_path, manifest)
    update_timeline(root, clip_id, rel(root, dst))
    return dst


def update_timeline(root, clip_id, video_rel):
    path = os.path.join(root, "分镜", "timeline_manifest.json")
    if not os.path.exists(path):
        return
    timeline = mv_utils.load_json(path, {})
    for clip in timeline.get("clips", []):
        if clip.get("clip_id") == clip_id:
            clip["video_path"] = video_rel
            clip["selected_at"] = date.today().isoformat()
    mv_utils.write_json(path, timeline)


def main():
    ap = argparse.ArgumentParser(description="生成/维护 mv-video 任务 manifest")
    ap.add_argument("project_root")
    ap.add_argument("--backend", choices=contract.MV_VIDEO_BACKENDS)
    ap.add_argument("--video-spec", choices=contract.MV_VIDEO_SPECS)
    ap.add_argument("--register", help="登记一个外部生成的视频文件")
    ap.add_argument("--clip", help="配合 --register/--select 使用，1/Clip_001 均可")
    ap.add_argument("--take", help="配合 --register/--select 使用，1/take_01 均可")
    ap.add_argument("--score", help="给某个 clip 的 take 评分，1/Clip_001 均可")
    ap.add_argument("--motion-score", type=int, choices=range(1, 6))
    ap.add_argument("--identity-score", type=int, choices=range(1, 6))
    ap.add_argument("--beat-score", type=int, choices=range(1, 6))
    ap.add_argument("--clarity-score", type=int, choices=range(1, 6))
    ap.add_argument("--notes")
    ap.add_argument("--select", help="选择某个 clip 的 take 定稿，1/Clip_001 均可")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    if not any((args.register, args.score, args.select)):
        out, manifest = create_jobs(root, args)
        print(f"[ok] video jobs → {out}（{len(manifest['jobs'])} clips）")
        return

    if args.register:
        clip_id = normalize_clip_id(args.clip)
        take_id = normalize_take_id(args.take)
        dst = register_take(root, clip_id, take_id, args.register)
        print(f"[ok] {clip_id} {take_id} 登记 → {dst}")

    if args.score:
        clip_id = normalize_clip_id(args.score)
        take_id = normalize_take_id(args.take)
        score_take(root, clip_id, take_id, args)
        print(f"[ok] {clip_id} {take_id} 评分已写入 jobs_manifest.json")

    if args.select:
        clip_id = normalize_clip_id(args.select)
        take_id = normalize_take_id(args.take)
        dst = select_take(root, clip_id, take_id)
        print(f"[ok] {clip_id} {take_id} 已定稿 → {dst}")


if __name__ == "__main__":
    main()
