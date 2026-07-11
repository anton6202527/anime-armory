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
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CONTRACT_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "contract.py")
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "mv_utils.py")
GATE_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "gate.py")
CAMERA_MANIFEST_REL = "skills/mv/references/运镜/manifest.json"
MV_LIB = os.path.join(REPO, "skills", "mv", "_lib")

# mv 线自包含的两轴标记（质量档 + 运动参考），与本文件同目录。
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if MV_LIB not in sys.path:
    sys.path.insert(0, MV_LIB)
import motion_axes
from mv_video_prompt_compiler import compile_prompt, render_markdown

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

def load_gate():
    spec = importlib.util.spec_from_file_location("mv_gate", GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

contract = load_contract()
mv_utils = load_mv_utils()
mv_gate = load_gate()

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


def prompt_bundle_for_take(clip, backend, spec_profile, take_id, video_model="", quality_tier=None, motion_reference=None):
    c = clip.get("continuity", {})
    shot = clip.get("shot_design") or {}
    ident = clip.get("identity_contract") or {}
    reference_inputs = clip.get("reference_inputs") or []
    if quality_tier is None:
        quality_tier = motion_axes.quality_tier_for_clip(clip, backend)
    if motion_reference is None:
        motion_reference = motion_axes.motion_reference_plan(clip, backend)
    try:
        model_profile = contract.video_model_profile(video_model)
    except KeyError:
        model_profile = {}
    try:
        channel_profile = contract.video_channel_profile(backend)
    except KeyError:
        channel_profile = {}
    camera_motion = str(shot.get("camera_movement") or "固定机位，保持首帧构图，动作峰值后稳定落幅")
    environment_motion = str(
        clip.get("environment_motion")
        or clip.get("dynamic_detail")
        or c.get("environment_motion")
        or shot.get("environment_motion")
        or ""
    )
    negative_raw = str(c.get("negative") or "换脸、换衣、新增人物、文字或水印、原生人声")
    negative_elements = [v.strip() for v in re.split(r"[、,，;；]", negative_raw) if v.strip()]
    mode = "frames2video" if clip.get("need_end_frame") else "image2video"
    canonical = {
        "clip_id": clip.get("clip_id"),
        "backend": video_model or backend,
        "mode": mode,
        "primary_action": c.get("action"),
        "camera_motion": camera_motion,
        "environment_motion": environment_motion,
        "rhythm": f"动作峰值对齐 {clip.get('action_peak', clip.get('end'))}s；结尾保留 8-12 帧稳定落幅",
        "end_state": c.get("end_state"),
        "negative_elements": negative_elements,
        "frame_inputs": [
            value for value in (clip.get("image_path"), clip.get("end_frame_path") if clip.get("need_end_frame") else "") if value
        ],
        "reference_inputs": reference_inputs,
    }
    compiled = compile_prompt(canonical)
    if compiled["lint"]["errors"]:
        raise SystemExit(f"[err] {clip.get('clip_id')} prompt compiler blocked: {compiled['lint']['errors']}")
    lines = [
        f"# {clip['clip_id']} {take_id} 视频生成任务",
        "",
        f"- 生视频模型：{video_model or '未记录'}",
        f"- 生视频渠道：{backend}",
        f"- 分辨率：{spec_profile['resolution']}",
        f"- 帧率：{spec_profile['fps']}fps",
        f"- 质量档：{spec_profile['quality']}",
        f"- 本镜质量档意图(quality_tier)：{quality_tier}  # high→后端 pro/高质量档，fast→量产省档，n/a→该后端无档（不改后端，仅意图）",
        f"- 运动参考(motion_reference)：{'适用·' + motion_reference.get('note', '') if motion_reference.get('applicable') else '不适用（非舞蹈/环绕镜或后端不支持视频参考）'}",
        f"- 模型能力：reference_images={model_profile.get('reference_images')} start_end_frames={model_profile.get('start_end_frames')} native_audio={model_profile.get('native_audio')}",
        f"- 渠道类型：{channel_profile.get('type', 'unknown')}；官方API={channel_profile.get('official_api', False)}",
        f"- 首帧：`{clip.get('image_path')}`",
        f"- 尾帧：`{clip.get('end_frame_path')}`" if clip.get("need_end_frame") else "- 尾帧：不使用",
        f"- 时长：{clip.get('duration')}s",
        f"- 转场：{clip.get('transition')}",
        f"- 动作家族：{clip.get('action_family', '')}",
        f"- 动作峰值：{clip.get('action_peak', clip.get('end'))}s",
        f"- 转场母题：{clip.get('transition_motif', '')}",
        f"- 景别：{shot.get('shot_size', '')}",
        f"- 运镜参考：{CAMERA_MANIFEST_REL}",
        f"- 运镜：{shot.get('camera_movement', '')}",
        f"- 光影：{shot.get('lighting', '')}",
        f"- 参考输入：{', '.join(str(x.get('path') or x.get('asset_id')) for x in reference_inputs)}",
        "",
        "## inherited_contract",
        f"- lead_id：{ident.get('lead_id', '')}",
        f"- lead_identity_anchor：{ident.get('lead_identity_anchor', '')}",
        f"- reference_group：{ident.get('reference_group', '')}",
        f"- forbidden_drift：{', '.join(ident.get('forbidden_drift') or [])}",
        "",
        "## continuity",
        f"- start_state：{c.get('start_state', '')}",
        f"- action：{c.get('action', '')}",
        f"- end_state：{c.get('end_state', '')}",
        f"- constraints：{c.get('constraints', '')}",
        f"- negative：{c.get('negative', '')}",
        "",
        "## 导演执行合同（不可整段提交）",
        f"人物运动：{c.get('action', '')}；动作家族：{clip.get('action_family', '')}；镜头运动：{camera_motion}；运镜参考：{CAMERA_MANIFEST_REL}；光影继承：{shot.get('lighting', '')}；明确环境响应：{environment_motion or '无新增，保持首帧环境'}；卡点约束：动作峰值对齐 {clip.get('action_peak', clip.get('end'))}s；转场母题：{clip.get('transition_motif', '')}；继承约束：不得重定脸、服装、道具、场景 setup、光色基调；声音约束：视频只生成画面，成片歌曲由合成阶段铺设。",
        "",
        "## 模型提交边界",
        "以上是完整 MV 生产合同，供身份/接缝/卡点/参考输入闸门、人工复核和溯源使用，不得整段提交。后端只接收下方编译块；歌曲、歌词、身份注册表、资产路径、渠道说明和审计文字不进入主 prompt。",
        "",
        render_markdown(compiled),
    ]
    return "\n".join(lines) + "\n", compiled


def prompt_for_take(clip, backend, spec_profile, take_id, video_model="", quality_tier=None, motion_reference=None):
    """Compatibility wrapper returning the full contract Markdown."""
    return prompt_bundle_for_take(
        clip, backend, spec_profile, take_id, video_model, quality_tier, motion_reference
    )[0]


def create_jobs(root, args):
    errors, warnings = mv_gate.check(root, "video_jobs")
    for msg in warnings:
        print(f"[warn] {msg}")
    if errors:
        raise SystemExit("\n".join(f"[err] {msg}" for msg in errors))
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    plan = mv_utils.load_json(plan_path, None)
    if not plan:
        raise SystemExit("[err] 缺 分镜/clip_plan.json，先跑 mv-plan/scripts/plan_clips.py")
    settings = mv_utils.parse_settings(root)
    video_model = settings.get("生视频模型") or settings.get("生视频AI") or contract.DEFAULT_SETTINGS["生视频模型"]
    backend = args.backend or settings.get("生视频渠道") or settings.get("生视频AI") or contract.DEFAULT_SETTINGS["生视频渠道"]
    spec = args.video_spec or settings.get("出视频规格") or "预算一般"
    if backend not in contract.MV_VIDEO_CHANNELS:
        raise SystemExit(f"[err] 不支持的生视频渠道：{backend}")
    if video_model not in contract.MV_VIDEO_MODELS:
        raise SystemExit(f"[err] 不支持的生视频模型：{video_model}")
    profile = contract.video_spec_profile(spec)
    model_profile = contract.video_model_profile(video_model)
    channel_profile = contract.video_channel_profile(backend)
    jobs = []
    for clip in plan.get("clips", []):
        clip_model = clip.get("video_model") or video_model
        clip_backend = clip.get("video_channel") or clip.get("video_backend") or backend
        if clip_model not in contract.MV_VIDEO_MODELS:
            raise SystemExit(f"[err] {clip.get('clip_id')} 不支持的生视频模型：{clip_model}")
        if clip_backend not in contract.MV_VIDEO_CHANNELS:
            raise SystemExit(f"[err] {clip.get('clip_id')} 不支持的生视频渠道：{clip_backend}")
        clip_model_profile = contract.video_model_profile(clip_model)
        clip_channel_profile = contract.video_channel_profile(clip_backend)
        image_path = clip.get("image_path")
        if image_path:
            full_image_path = os.path.join(root, image_path)
            if not os.path.exists(full_image_path):
                print(f"[warn] {clip['clip_id']} 缺首帧 PNG：{image_path}，请确保 mv-image 出图完毕再开始生成视频。")
                
        quality_tier = motion_axes.quality_tier_for_clip(clip, clip_backend)
        motion_reference = motion_axes.motion_reference_plan(clip, clip_backend)
        requested = profile["key_takes"] if clip.get("beat_role") == "key" else profile["normal_takes"]
        takes = []
        for i in range(1, requested + 1):
            take_id = f"take_{i:02d}"
            prompt_path = os.path.join("出视频", "prompt", f"{clip['clip_id']}_{take_id}.md")
            prompt_text, compiled = prompt_bundle_for_take(
                clip, clip_backend, profile, take_id, clip_model, quality_tier, motion_reference
            )
            mv_utils.write_text(os.path.join(root, prompt_path), prompt_text)
            submit_prompt = str(compiled["prompt"])
            takes.append({
                "take_id": take_id,
                "status": "planned",
                "prompt_path": prompt_path,
                "prompt_source_kind": "compiled_submit_prompt",
                "prompt_compiler": {
                    key: compiled[key]
                    for key in (
                        "kind", "version", "profile_version", "profile", "backend", "mode", "language",
                        "native_audio_policy",
                    )
                },
                "submit_prompt": submit_prompt,
                "negative_prompt": compiled["negative_prompt"],
                "source_contract_sha256": compiled["source_contract_sha256"],
                "submit_prompt_sha256": hashlib.sha256(submit_prompt.encode("utf-8")).hexdigest(),
                "submit_prompt_chars": len(submit_prompt),
                "video_path": os.path.join("出视频", "takes", clip["clip_id"], f"{take_id}.mp4"),
                "score": {},
                "notes": "",
                "registered_at": None,
            })
        # 两轴增量标记（quality_tier / motion_reference 已在 takes 循环前算好）：
        #   quality_tier：副歌高光/卡点爽点镜→high，verse 铺垫镜→fast，后端无档→n/a
        #   motion_reference：舞蹈/环绕运镜镜+后端支持 reference_video_motion 时 advisory 提示
        #   均为增量字段·不改后端选择（mv 全程同一后端）
        jobs.append({
            "clip_id": clip["clip_id"],
            "section": clip["section"],
            "duration": clip["duration"],
            "beat_role": clip.get("beat_role", "normal"),
            "backend": clip_backend,
            "video_model": clip_model,
            "video_spec": spec,
            "model_profile": clip_model_profile,
            "channel_profile": clip_channel_profile,
            "quality_tier": quality_tier,
            "motion_reference": motion_reference,
            "reference_inputs": clip.get("reference_inputs") or [],
            "inherited_contract": {
                "image_path": clip.get("image_path"),
                "end_frame_path": clip.get("end_frame_path") if clip.get("need_end_frame") else "",
                "identity_contract": clip.get("identity_contract") or {},
                "shot_design": clip.get("shot_design") or {},
                "continuity": clip.get("continuity") or {},
            },
            "requested_takes": requested,
            "selected_take": None,
            "selected_video_path": clip.get("selected_video_path") or os.path.join("出视频", "视频", f"{clip['clip_id']}.mp4"),
            "takes": takes,
        })
    manifest = {
        "schema_version": 2,
        "kind": "mv_video_jobs",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": plan.get("title") or os.path.basename(root),
        "video_model": video_model,
        "video_channel": backend,
        "backend": backend,
        "backend_policy": "capability_routed" if any(j.get("backend") != backend or j.get("video_model") != video_model for j in jobs) else "uniform_default",
        "video_spec": spec,
        "spec_profile": profile,
        "model_profile": model_profile,
        "channel_profile": channel_profile,
        "clip_plan_path": "分镜/clip_plan.json",
        "jobs": jobs,
    }
    out = os.path.join(root, "出视频", "jobs_manifest.json")
    mv_utils.write_json(out, manifest)
    mv_utils.update_progress_stage(root, "video_jobs")
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


def selection_errors(take):
    score = take.get("score") or {}
    required = ("motion", "identity", "beat_fit", "clarity")
    missing = [key for key in required if not isinstance(score.get(key), (int, float))]
    errors = [f"评分缺字段：{', '.join(missing)}"] if missing else []
    if not missing:
        average = sum(float(score[key]) for key in required) / len(required)
        if average < 3.0:
            errors.append(f"平均分 {average:.2f} < 3.0")
        if float(score["identity"]) < 3:
            errors.append(f"identity={score['identity']} < 3")
    return errors


def run_final_video_checks(root):
    commands = [
        [sys.executable, os.path.join(HERE, "inherit_contract.py"), root],
        [sys.executable, os.path.join(HERE, "video_qc.py"), root],
    ]
    for command in commands:
        proc = subprocess.run(command, text=True, capture_output=True)
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.returncode:
            raise SystemExit(proc.stderr.strip() or f"[err] {' '.join(command)} failed")


def select_take(root, clip_id, take_id, waiver_reason=""):
    manifest_path, manifest = load_manifest(root)
    job = find_job(manifest, clip_id)
    take = find_take(job, take_id)
    errors = selection_errors(take)
    if errors and not waiver_reason:
        raise SystemExit("[err] 挑版被阻断：" + "；".join(errors) + "。先补全四维评分，或显式 --waiver-reason 留痕")
    if errors:
        take["selection_waiver"] = {"reason": waiver_reason, "date": date.today().isoformat(), "errors": errors}
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
    if all(j.get("selected_take") for j in manifest.get("jobs", [])):
        run_final_video_checks(root)
        meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
        if meta.get("is_demo"):
            mv_utils.update_progress_stage(root, "video")
        else:
            print("[next] 正式项目需逐镜/接缝人审：video_qc.py --accept-semantic --reviewer <name>")
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
    ap.add_argument("--waiver-reason", help="评分未达门槛时的显式人工放行原因；会写入 manifest")
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
        dst = select_take(root, clip_id, take_id, args.waiver_reason or "")
        print(f"[ok] {clip_id} {take_id} 已定稿 → {dst}")


if __name__ == "__main__":
    main()
