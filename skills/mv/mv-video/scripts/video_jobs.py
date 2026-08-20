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
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date

try:
    import fcntl
except ImportError:  # pragma: no cover - MV production hosts are macOS/Linux.
    fcntl = None

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CONTRACT_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "contract.py")
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "mv_utils.py")
GATE_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "gate.py")
COMPLETION_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "completion.py")
CAMERA_MANIFEST_REL = "skills/mv/references/运镜/manifest.json"
MV_LIB = os.path.join(REPO, "skills", "mv", "_lib")

# mv 线自包含的两轴标记（质量档 + 运动参考），与本文件同目录。
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if MV_LIB not in sys.path:
    sys.path.insert(0, MV_LIB)
import motion_axes
from mv_video_prompt_compiler import compile_prompt, render_markdown
import provider_evidence
from signature_effects import signature_effect_directive
import video_capabilities

EFFECT_MANIFEST_REL = "skills/mv/references/特效镜头/manifest.json"
COMPILER_PATH = os.path.join(MV_LIB, "mv_video_prompt_compiler.py")
CAPABILITY_PATH = os.path.join(MV_LIB, "video_capabilities.py")
PROVIDER_EVIDENCE_PATH = os.path.join(HERE, "provider_evidence.py")
MANIFEST_SCHEMA_VERSION = 4
SUBMIT_RECEIPT_KIND = "mv_video_submit_receipt"
SEQUENCE_RECEIPT_KIND = "mv_video_sequence_submit_receipt"
CUT_MAP_KIND = "mv_video_sequence_cut_map"

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


def load_completion():
    spec = importlib.util.spec_from_file_location("mv_completion_for_video_jobs", COMPLETION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

contract = load_contract()
mv_utils = load_mv_utils()
mv_gate = load_gate()

def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def _sequence_split_work_dir(root, unit_id, take_id):
    """Create one project-local, invocation-owned sequence split directory."""
    base = os.path.join(root, "出视频", "takes", "_sequence_split")
    os.makedirs(base, exist_ok=True)
    safe_unit = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(unit_id or "sequence"))
    safe_take = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(take_id or "take"))
    return tempfile.mkdtemp(prefix=f"{safe_unit}_{safe_take}_", dir=base)


def _cleanup_sequence_split_work_dir(root, path):
    """Remove only a work directory created beneath this project's split root."""
    base = os.path.realpath(os.path.join(root, "出视频", "takes", "_sequence_split"))
    target = os.path.realpath(path)
    try:
        inside = os.path.commonpath((base, target)) == base
    except ValueError:
        inside = False
    if not inside or target == base:
        raise RuntimeError(f"refusing to clean non-invocation split path: {path}")
    shutil.rmtree(target, ignore_errors=True)


@contextmanager
def _registration_lock(root):
    """Serialize stable take + manifest commits across video_jobs processes."""
    if fcntl is None:
        raise SystemExit("[err] 当前平台缺少跨进程文件锁，拒绝无保护地登记视频 take")
    lock_dir = os.path.join(root, "出视频", ".locks")
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, "video_jobs.register.lock")
    with open(lock_path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic_copy_to_stable_path(src, dst):
    """Copy through a unique sibling and atomically publish the complete file."""
    parent = os.path.dirname(dst)
    os.makedirs(parent, exist_ok=True)
    fd, staging = tempfile.mkstemp(
        prefix=f".{os.path.basename(dst)}.register_", suffix=".tmp", dir=parent
    )
    os.close(fd)
    try:
        shutil.copy2(src, staging)
        os.replace(staging, dst)
    finally:
        if os.path.exists(staging):
            os.unlink(staging)


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


def stable_hash(value):
    return video_capabilities.stable_hash(value)


def load_adapter_record(root, explicit_path=""):
    path = os.path.abspath(explicit_path) if explicit_path else os.path.join(root, "出视频", "provider_adapter.json")
    if not os.path.isfile(path):
        return None, ""
    payload = mv_utils.load_json(path, None)
    if not isinstance(payload, dict):
        raise SystemExit(f"[err] provider adapter 不是 JSON object：{path}")
    return payload, rel(root, path) if os.path.commonpath((root, path)) == root else path


def normalize_model(value):
    raw = str(value or "").strip()
    normalized = contract.normalize_video_model(raw)
    # New current models live in the capability graph without changing the
    # legacy settings menu.  Exact spelling is required; no old name upgrades.
    return normalized if normalized in video_capabilities.MODEL_CAPABILITIES else raw


def normalize_channel(value):
    raw = str(value or "").strip()
    normalized = contract.normalize_video_channel(raw)
    return normalized if normalized in video_capabilities.CHANNELS else raw


def resolve_provider_route(model, channel, adapter_record=None, context=""):
    try:
        return video_capabilities.resolve_route(model, channel, adapter_record)
    except ValueError as exc:
        prefix = f"{context} " if context else ""
        raise SystemExit(
            f"[err] {prefix}生视频 model×channel 路由不可执行：{model} × {channel}；{exc}。"
            "manual/自定义必须提供显式 provider adapter record，已知模型也不得跨厂商渠道混配"
        )


def _reference_role(row):
    path = str((row or {}).get("path") or "")
    use = str((row or {}).get("use") or "").lower()
    ext = os.path.splitext(path)[1].lower()
    if "audio" in use or "口型" in use or ext in {".wav", ".mp3", ".m4a", ".flac"}:
        return "reference_audio"
    if "motion" in use or "video" in use or "运动" in use or ext in {".mp4", ".mov", ".webm", ".mkv"}:
        return "reference_video"
    return "reference_image"


def request_input_roles(root, clip, include_end=True, sequence_role=False):
    rows = []
    first = str(clip.get("image_path") or "").strip()
    if first:
        rows.append({
            "role": "reference_image" if sequence_role else "start_frame",
            "path": first,
            "sha256": mv_utils.content_hash(os.path.join(root, first)),
            "use": "sequence_shot_anchor" if sequence_role else "first_frame",
        })
    end = str(clip.get("end_frame_path") or "").strip()
    if include_end and clip.get("need_end_frame") and end:
        rows.append({
            "role": "end_frame", "path": end,
            "sha256": mv_utils.content_hash(os.path.join(root, end)), "use": "end_frame",
        })
    for ref_row in clip.get("reference_inputs") or []:
        if not isinstance(ref_row, dict) or not str(ref_row.get("path") or "").strip():
            continue  # provider asset IDs are not silently treated as file submissions
        path = str(ref_row["path"]).strip()
        rows.append({
            "role": _reference_role(ref_row), "path": path,
            "sha256": mv_utils.content_hash(os.path.join(root, path)),
            "use": str(ref_row.get("use") or "reference"),
        })
    missing = [row["path"] for row in rows if not row["sha256"]]
    if missing:
        raise SystemExit(f"[err] provider request input 缺当前文件/SHA：{', '.join(missing)}")
    unique = []
    seen = set()
    for row in rows:
        key = (row["role"], row["path"])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def planned_request_controls(root, clip, spec_profile, route, quality_tier, *, sequence_role=False):
    capability = route.get("capability") or {}
    wants_end = bool(clip.get("need_end_frame")) and not sequence_role
    supports_end = int(((capability.get("input_roles") or {}).get("end_frame") or {}).get("max_count") or 0) > 0
    mode = "multi_shot_sequence" if sequence_role else (
        "frames2video" if wants_end and supports_end else "image2video"
    )
    return {
        "duration_seconds": float(clip.get("duration") or 0),
        "fps": int(spec_profile["fps"]),
        "resolution": str(spec_profile["resolution"]).lower(),
        "mode": mode,
        "quality_tier": quality_tier,
        "input_roles": request_input_roles(root, clip, include_end=wants_end, sequence_role=sequence_role),
        "end_frame_intent": "submit" if wants_end and supports_end else (
            "editorial_match_review" if wants_end else "none"
        ),
    }


def prompt_bundle_for_take(
    clip, backend, spec_profile, take_id, video_model="", quality_tier=None,
    motion_reference=None, provider_route=None, planned_controls=None, root="",
):
    c = clip.get("continuity", {})
    shot = clip.get("shot_design") or {}
    ident = clip.get("identity_contract") or {}
    reference_inputs = clip.get("reference_inputs") or []
    if quality_tier is None:
        quality_tier = motion_axes.quality_tier_for_clip(clip, backend)
    if motion_reference is None:
        motion_reference = motion_axes.motion_reference_plan(clip, backend)
    if provider_route is None:
        provider_route = resolve_provider_route(normalize_model(video_model), normalize_channel(backend))
    model_profile = video_capabilities.legacy_projection(provider_route.get("capability") or {})
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
    # 特效镜头主动接入：本镜运镜/动作/母题里点名命名特效（子弹时间/升格KO/巨星名场面/城市夜驾…）时，
    # 暴露可粘贴核心 prompt，并对高身份风险特效把该特效 negatives + 身份锁词并入提交负向 prompt。
    signature_probe = " ".join(part for part in [
        camera_motion, str(c.get("action") or ""), str(shot.get("shot_size") or ""),
        environment_motion, str(clip.get("transition_motif") or ""),
        str(clip.get("signature_effect") or ""),
    ] if part)
    signature_line, signature_negatives, _signature_high_risk = signature_effect_directive(signature_probe)
    for term in signature_negatives:
        if term not in negative_elements:
            negative_elements.append(term)
    wants_end_frame = bool(clip.get("need_end_frame"))
    supports_end_frame = bool(model_profile.get("start_end_frames"))
    mode = "frames2video" if wants_end_frame and supports_end_frame else "image2video"
    continuity_implementation = (
        "native_start_end_frames" if mode == "frames2video"
        else ("multi_shot_sequence_or_editorial_match_review" if wants_end_frame else "first_frame_only")
    )
    if planned_controls is None:
        if not root:
            # Compatibility for direct prompt-only callers; production jobs
            # always pass a project root and pre-hashed structured controls.
            planned_controls = {
                "duration_seconds": float(clip.get("duration") or 0),
                "fps": int(spec_profile["fps"]),
                "resolution": str(spec_profile["resolution"]).lower(),
                "mode": mode,
                "quality_tier": quality_tier,
                "input_roles": [],
            }
        else:
            planned_controls = planned_request_controls(root, clip, spec_profile, provider_route, quality_tier)
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
        "frame_inputs": [value for value in (
            clip.get("image_path"),
            clip.get("end_frame_path") if mode == "frames2video" else "",
        ) if value],
        "reference_inputs": reference_inputs,
        "provider_route": provider_route,
        "planned_request_controls": planned_controls,
    }
    try:
        compiled = compile_prompt(canonical)
    except ValueError as exc:
        raise SystemExit(f"[err] {clip.get('clip_id')} provider request controls blocked: {exc}")
    if compiled["lint"]["errors"]:
        raise SystemExit(f"[err] {clip.get('clip_id')} prompt compiler blocked: {compiled['lint']['errors']}")
    lines = [
        f"# {clip['clip_id']} {take_id} 视频生成任务",
        "",
        f"- 生视频模型：{video_model or '未记录'}",
        f"- 生视频渠道：{backend}",
        f"- provider_id：{provider_route.get('provider_id')}",
        f"- capability graph：{provider_route.get('capability_graph_version')} / {provider_route.get('capability_graph_sha256')}",
        f"- 分辨率：{spec_profile['resolution']}",
        f"- 帧率：{spec_profile['fps']}fps",
        f"- 质量档：{spec_profile['quality']}",
        f"- 本镜质量档意图(quality_tier)：{quality_tier}  # high→后端 pro/高质量档，fast→量产省档，n/a→该后端无档（不改后端，仅意图）",
        f"- 运动参考(motion_reference)：{'适用·' + motion_reference.get('note', '') if motion_reference.get('applicable') else '不适用（非舞蹈/环绕镜或后端不支持视频参考）'}",
        f"- 模型能力：reference_images={model_profile.get('reference_images')} start_end_frames={model_profile.get('start_end_frames')} native_audio={model_profile.get('native_audio')} native_audio_disableable={(provider_route.get('capability') or {}).get('native_audio', {}).get('disableable')}",
        f"- 接缝实现：{continuity_implementation}",
        f"- 渠道类型：{channel_profile.get('type', 'unknown')}；官方API={channel_profile.get('official_api', False)}",
        f"- 首帧：`{clip.get('image_path')}`",
        (f"- 尾帧：`{clip.get('end_frame_path')}`（原生首尾帧提交）" if mode == "frames2video"
         else (f"- 尾帧目标：`{clip.get('end_frame_path')}`（当前模型 profile 未证实首尾帧；不得伪装已提交，改走多镜头单次生成或剪辑匹配复核）"
               if wants_end_frame else "- 尾帧：不使用")),
        f"- 时长：{clip.get('duration')}s",
        f"- 转场：{clip.get('transition')}",
        f"- 动作家族：{clip.get('action_family', '')}",
        f"- 动作峰值：{clip.get('action_peak', clip.get('end'))}s",
        f"- 转场母题：{clip.get('transition_motif', '')}",
        f"- 景别：{shot.get('shot_size', '')}",
        f"- 运镜参考：{CAMERA_MANIFEST_REL}",
        f"- 特效镜头参考：{EFFECT_MANIFEST_REL}",
        f"- 运镜：{shot.get('camera_movement', '')}",
        (f"- {signature_line}" if signature_line
         else "- 特效镜头/Signature Effect：本镜未点名命名特效；如需招牌镜头（子弹时间/升格KO/巨星名场面/城市夜驾/逆转引力…）见特效镜头库。"),
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


def sequence_units(
    root, clips, video_model, backend, model_profile=None, spec_profile=None,
    adapter_record=None,
):
    """Compile contiguous same-setup clips into optional multi-shot units.

    Per-clip jobs remain the acceptance ledger.  A capable backend may produce
    one coherent sequence, which is then cut at the locked boundaries and each
    resulting clip is registered/scored normally.
    """
    groups, current = [], []
    current_model = current_backend = None

    def flush():
        nonlocal current, current_model, current_backend
        if len(current) > 1:
            groups.append((current, current_model, current_backend))
        current, current_model, current_backend = [], None, None

    for clip in clips:
        clip_model = normalize_model(clip.get("video_model") or video_model)
        clip_backend = normalize_channel(clip.get("video_channel") or clip.get("video_backend") or backend)
        route = resolve_provider_route(clip_model, clip_backend, adapter_record, str(clip.get("clip_id") or ""))
        clip_profile = video_capabilities.legacy_projection(route.get("capability") or {})
        if not clip_profile.get("multi_shot"):
            flush()
            continue
        limit = float(clip_profile.get("max_sequence_seconds") or 15)
        setup = (clip.get("shot_design") or {}).get("setup_group")
        total = sum(float(row.get("duration") or 0) for row in current)
        same_context = bool(
            current
            and clip_model == current_model
            and clip_backend == current_backend
            and clip.get("section") == current[-1].get("section")
            and setup == (current[-1].get("shot_design") or {}).get("setup_group")
        )
        if current and (not same_context or total + float(clip.get("duration") or 0) > limit):
            flush()
        if not current:
            current_model, current_backend = clip_model, clip_backend
        current.append(clip)
    flush()

    units = []
    spec_profile = spec_profile or {"resolution": "720p", "fps": 24, "quality": "standard"}
    for index, (group, group_model, group_backend) in enumerate(groups, 1):
        unit_id = f"Sequence_{index:03d}"
        route = resolve_provider_route(group_model, group_backend, adapter_record, unit_id)
        shot_cues = []
        for shot_index, clip in enumerate(group, 1):
            continuity = clip.get("continuity") or {}
            shot = clip.get("shot_design") or {}
            shot_cues.append(
                f"Shot {shot_index} [{clip.get('duration')}s]: {continuity.get('action')}; "
                f"camera {shot.get('camera_movement')}; cut at {clip.get('end')}s by "
                f"{(clip.get('seam_contract') or {}).get('kind')}"
            )
        reference_inputs = []
        for clip in group:
            reference_inputs.extend(clip.get("reference_inputs") or [])
        input_roles = []
        for clip in group:
            input_roles.extend(request_input_roles(root, clip, include_end=False, sequence_role=True))
        input_roles = list({(row["role"], row["path"]): row for row in input_roles}.values())
        planned_controls = {
            "duration_seconds": round(sum(float(clip.get("duration") or 0) for clip in group), 6),
            "fps": int(spec_profile["fps"]),
            "resolution": str(spec_profile["resolution"]).lower(),
            "mode": "multi_shot_sequence",
            "quality_tier": "high" if any(str(clip.get("beat_role")) == "key" for clip in group) else "fast",
            "input_roles": input_roles,
            "end_frame_intent": "none",
        }
        canonical = {
            "clip_id": unit_id,
            "backend": group_model or group_backend,
            "mode": "multi_shot_sequence",
            "primary_action": " Then ".join(shot_cues),
            "camera_motion": "Execute the listed shot-specific camera moves and preserve the signed cut order",
            "environment_motion": "Keep the same setup topology, performer identity, wardrobe, props and color script across shots",
            "rhythm": "Cuts must land on the supplied locked shot boundaries; no extra shots",
            "end_state": (group[-1].get("continuity") or {}).get("end_state"),
            "negative_elements": ["extra shots", "identity drift", "wardrobe change", "embedded captions", "generated song"],
            "frame_inputs": [clip.get("image_path") for clip in group if clip.get("image_path")],
            "reference_inputs": reference_inputs,
            "provider_route": route,
            "planned_request_controls": planned_controls,
        }
        try:
            compiled = compile_prompt(canonical)
        except ValueError:
            # sequence_units are optional optimizations; an over-capacity
            # group falls back to its already compiled per-clip jobs.
            continue
        if compiled["lint"]["errors"]:
            continue
        prompt_rel = f"出视频/prompt/{unit_id}.md"
        lines = [
            f"# {unit_id} 多镜头一次生成合同",
            "",
            f"- 模型：{group_model}",
            f"- 渠道：{group_backend}",
            f"- provider_id：{route.get('provider_id')}",
            f"- clips：{', '.join(clip.get('clip_id') for clip in group)}",
            f"- 总时长：{sum(float(clip.get('duration') or 0) for clip in group):.3f}s",
            "- 接受方式：一次生成后按 timeline_manifest 锁定边界切回逐 clip；每段仍须 register/score/select，不得用整段文件绕过挑版与 QC。",
            "",
            "## Shot cues",
            *[f"- {cue}" for cue in shot_cues],
            "",
            render_markdown(compiled),
        ]
        mv_utils.write_text(os.path.join(root, prompt_rel), "\n".join(lines) + "\n")
        units.append({
            "unit_id": unit_id,
            "mode": "multi_shot_sequence",
            "status": "route_candidate",
            "video_model": group_model,
            "video_channel": group_backend,
            "clip_ids": [clip.get("clip_id") for clip in group],
            "duration": round(sum(float(clip.get("duration") or 0) for clip in group), 3),
            "prompt_path": prompt_rel,
            "submit_prompt": compiled["prompt"],
            "negative_prompt": compiled["negative_prompt"],
            "provider_route": route,
            "planned_request_controls": planned_controls,
            "planned_request_controls_sha256": compiled["planned_request_controls_sha256"],
            "compiled_request_controls": compiled["request_controls"],
            "compiled_request_controls_sha256": compiled["compiled_request_controls_sha256"],
            "source_contract_sha256": compiled["source_contract_sha256"],
            "submit_prompt_sha256": hashlib.sha256(compiled["prompt"].encode("utf-8")).hexdigest(),
            "acceptance_boundary": "split_to_locked_clips_then_register_score_select",
        })
    return units


def receipt_template(record, take=None, *, take_id="", sequence=False):
    """Write a non-evidentiary template that must be completed after submit."""
    route = (take or {}).get("provider_route") or record.get("provider_route") or {}
    controls = (take or {}).get("compiled_request_controls") or record.get("compiled_request_controls") or {}
    control_hash = ((take or {}).get("compiled_request_controls_sha256")
                    or record.get("compiled_request_controls_sha256") or stable_hash(controls))
    item_id = record.get("unit_id") if sequence else record.get("clip_id")
    take_id = take_id or (take or {}).get("take_id") or "take_01"
    rows = []
    for row in controls.get("input_roles") or []:
        rows.append({
            "role": row.get("role"), "path": row.get("path"), "sha256": row.get("sha256"),
            "confirmed_submitted": False,
        })
    payload = {
        "schema_version": provider_evidence.RECEIPT_SCHEMA_VERSION,
        "kind": SEQUENCE_RECEIPT_KIND if sequence else SUBMIT_RECEIPT_KIND,
        "template_only": True,
        "job_id": f"{item_id}/{take_id}",
        "clip_id": None if sequence else item_id,
        "unit_id": item_id if sequence else None,
        "take_id": take_id,
        "model": record.get("video_model"),
        "channel": record.get("video_channel") or record.get("backend"),
        "provider_id": route.get("provider_id"),
        "provider_job_id": "",
        "provider_status": "",
        "compiled_request_controls_sha256": control_hash,
        "request_controls": controls,
        "submitted_refs": rows,
        "submitted_at": "",
        "provider_evidence": (
            provider_evidence.evidence_template(route)
            if provider_evidence.route_requires_evidence(route) else None
        ),
        "manual_attestation": {"reviewer": "", "notes": ""},
    }
    return payload


def build_freshness_snapshot(root, manifest):
    project_files = {
        "_设置.md": mv_utils.content_hash(os.path.join(root, "_设置.md")),
        "分镜/clip_plan.json": mv_utils.content_hash(os.path.join(root, "分镜", "clip_plan.json")),
        "生产数据/image_qc/image_qc.json": mv_utils.content_hash(
            os.path.join(root, "生产数据", "image_qc", "image_qc.json")
        ),
    }
    reference_files = {}
    prompt_files = {}
    for job in manifest.get("jobs") or []:
        for take in job.get("takes") or []:
            prompt_path = str(take.get("prompt_path") or "")
            if prompt_path:
                prompt_files[prompt_path] = mv_utils.content_hash(os.path.join(root, prompt_path))
            for row in (take.get("compiled_request_controls") or {}).get("input_roles") or []:
                path = str(row.get("path") or "")
                if path:
                    reference_files[path] = mv_utils.content_hash(os.path.join(root, path))
    for unit in manifest.get("sequence_units") or []:
        prompt_path = str(unit.get("prompt_path") or "")
        if prompt_path:
            prompt_files[prompt_path] = mv_utils.content_hash(os.path.join(root, prompt_path))
        for row in (unit.get("compiled_request_controls") or {}).get("input_roles") or []:
            path = str(row.get("path") or "")
            if path:
                reference_files[path] = mv_utils.content_hash(os.path.join(root, path))
    adapter_path = str(manifest.get("provider_adapter_path") or "")
    if adapter_path and not os.path.isabs(adapter_path):
        project_files[adapter_path] = mv_utils.content_hash(os.path.join(root, adapter_path))
    implementation_files = {
        "skills/mv/_lib/mv_video_prompt_compiler.py": mv_utils.content_hash(COMPILER_PATH),
        "skills/mv/_lib/video_capabilities.py": mv_utils.content_hash(CAPABILITY_PATH),
        "skills/mv/mv-video/scripts/provider_evidence.py": mv_utils.content_hash(PROVIDER_EVIDENCE_PATH),
    }
    project_files.update(prompt_files)
    project_files.update(reference_files)
    return {
        "schema_version": 1,
        "project_files": project_files,
        "implementation_files": implementation_files,
        "settings_sha256": project_files.get("_设置.md", ""),
        "compiler_sha256": implementation_files["skills/mv/_lib/mv_video_prompt_compiler.py"],
        "capability_implementation_sha256": implementation_files["skills/mv/_lib/video_capabilities.py"],
        "capability_graph_sha256": video_capabilities.graph_sha256(),
        "image_qc_sha256": project_files.get("生产数据/image_qc/image_qc.json", ""),
        "prompt_bundle_sha256": stable_hash(prompt_files),
        "reference_inputs_sha256": stable_hash(reference_files),
    }


def freshness_errors(root, manifest):
    snapshot = manifest.get("freshness") or {}
    if not snapshot:
        return ["missing_manifest_freshness_snapshot"]
    errors = []
    for path, expected in (snapshot.get("project_files") or {}).items():
        current = mv_utils.content_hash(os.path.join(root, path))
        if current != expected:
            errors.append(f"project_file_changed:{path}")
    for path, expected in (snapshot.get("implementation_files") or {}).items():
        current = mv_utils.content_hash(os.path.join(REPO, path))
        if current != expected:
            errors.append(f"implementation_file_changed:{path}")
    if snapshot.get("capability_graph_sha256") != video_capabilities.graph_sha256():
        errors.append("capability_graph_changed")
    return errors


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
    adapter_record, adapter_record_path = load_adapter_record(root, getattr(args, "adapter_record", "") or "")
    legacy_model, legacy_channel = contract.legacy_video_route(settings.get("生视频AI") or "")
    video_model = normalize_model(
        settings.get("生视频模型") or legacy_model or contract.DEFAULT_SETTINGS["生视频模型"]
    )
    backend = normalize_channel(
        args.backend or settings.get("生视频渠道") or legacy_channel or contract.DEFAULT_SETTINGS["生视频渠道"]
    )
    spec = args.video_spec or settings.get("出视频规格") or "预算一般"
    lip_mode = settings.get("演唱口型") or "仅正面演唱镜"
    profile = contract.video_spec_profile(spec)
    default_route = resolve_provider_route(video_model, backend, adapter_record, "项目默认")
    model_profile = video_capabilities.legacy_projection(default_route.get("capability") or {})
    try:
        channel_profile = contract.video_channel_profile(backend)
    except KeyError:
        channel_profile = {
            "type": default_route.get("channel_kind"),
            "official_api": default_route.get("channel_kind") == "api",
            "notes": "由 mv-video capability graph / adapter record 解析",
        }
    jobs = []
    for clip in plan.get("clips", []):
        clip_model = normalize_model(clip.get("video_model") or video_model)
        clip_backend = normalize_channel(clip.get("video_channel") or clip.get("video_backend") or backend)
        clip_route = resolve_provider_route(clip_model, clip_backend, adapter_record, clip.get("clip_id"))
        clip_model_profile = video_capabilities.legacy_projection(clip_route.get("capability") or {})
        try:
            clip_channel_profile = contract.video_channel_profile(clip_backend)
        except KeyError:
            clip_channel_profile = {
                "type": clip_route.get("channel_kind"),
                "official_api": clip_route.get("channel_kind") == "api",
            }
        image_path = clip.get("image_path")
        if image_path:
            full_image_path = os.path.join(root, image_path)
            if not os.path.exists(full_image_path):
                print(f"[warn] {clip['clip_id']} 缺首帧 PNG：{image_path}，请确保 mv-image 出图完毕再开始生成视频。")
                
        route_capability_label = f"{clip_model} / {clip_backend}"
        quality_tier = motion_axes.quality_tier_for_clip(clip, route_capability_label)
        motion_reference = motion_axes.motion_reference_plan(clip, route_capability_label)
        controls_planned = planned_request_controls(root, clip, profile, clip_route, quality_tier)
        requested = profile["key_takes"] if clip.get("beat_role") == "key" else profile["normal_takes"]
        takes = []
        for i in range(1, requested + 1):
            take_id = f"take_{i:02d}"
            prompt_path = os.path.join("出视频", "prompt", f"{clip['clip_id']}_{take_id}.md")
            prompt_text, compiled = prompt_bundle_for_take(
                clip, clip_backend, profile, take_id, clip_model, quality_tier, motion_reference,
                provider_route=clip_route, planned_controls=controls_planned, root=root,
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
                "provider_route": clip_route,
                "planned_request_controls": controls_planned,
                "planned_request_controls_sha256": compiled["planned_request_controls_sha256"],
                "compiled_request_controls": compiled["request_controls"],
                "compiled_request_controls_sha256": compiled["compiled_request_controls_sha256"],
                "submit_prompt": submit_prompt,
                "negative_prompt": compiled["negative_prompt"],
                "source_contract_sha256": compiled["source_contract_sha256"],
                "submit_prompt_sha256": hashlib.sha256(submit_prompt.encode("utf-8")).hexdigest(),
                "submit_prompt_chars": len(submit_prompt),
                "video_path": os.path.join("出视频", "takes", clip["clip_id"], f"{take_id}.mp4"),
                "score": {},
                "notes": "",
                "registered_at": None,
                "submit_receipt_template_path": os.path.join(
                    "出视频", "receipts", f"{clip['clip_id']}_{take_id}.submit.json"
                ),
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
            "action_family": clip.get("action_family", ""),
            "seam_contract": clip.get("seam_contract") or {},
            "lip_sync_required": bool(
                lip_mode != "关闭"
                and (clip.get("action_family") == "performance_vocal" or clip.get("vocal_lyrics"))
            ),
            "backend": clip_backend,
            "video_model": clip_model,
            "video_spec": spec,
            "provider_route": clip_route,
            "model_profile": clip_model_profile,
            "channel_profile": clip_channel_profile,
            "quality_tier": quality_tier,
            "motion_reference": motion_reference,
            "continuity_implementation": (
                "native_start_end_frames"
                if clip.get("need_end_frame") and clip_model_profile.get("start_end_frames")
                else ("multi_shot_sequence_or_editorial_match_review" if clip.get("need_end_frame") else "first_frame_only")
            ),
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
    units = sequence_units(
        root, plan.get("clips") or [], video_model, backend, model_profile,
        spec_profile=profile, adapter_record=adapter_record,
    )
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "kind": "mv_video_jobs",
        "generated_at": date.today().isoformat(),
        "root_rel": ".",
        "title": plan.get("title") or os.path.basename(root),
        "video_model": video_model,
        "video_channel": backend,
        "backend": backend,
        "backend_policy": "capability_routed" if any(j.get("backend") != backend or j.get("video_model") != video_model for j in jobs) else "uniform_default",
        "video_spec": spec,
        "spec_profile": profile,
        "model_profile": model_profile,
        "channel_profile": channel_profile,
        "provider_route": default_route,
        "provider_adapter_path": adapter_record_path,
        "provider_adapter_sha256": stable_hash(adapter_record) if adapter_record else "",
        "capability_graph_version": video_capabilities.CAPABILITY_GRAPH_VERSION,
        "capability_graph_sha256": video_capabilities.graph_sha256(),
        "clip_plan_path": "分镜/clip_plan.json",
        "clip_plan_sha256": mv_utils.content_hash(plan_path),
        "sequence_units": units,
        "jobs": jobs,
    }
    for job in jobs:
        for take in job.get("takes") or []:
            template = receipt_template(job, take)
            mv_utils.write_json(os.path.join(root, take["submit_receipt_template_path"]), template)
    for unit in units:
        unit["submit_receipt_template_path"] = os.path.join(
            "出视频", "receipts", f"{unit['unit_id']}_take_01.submit.json"
        )
        mv_utils.write_json(
            os.path.join(root, unit["submit_receipt_template_path"]),
            receipt_template(unit, None, take_id="take_01", sequence=True),
        )
    manifest["freshness"] = build_freshness_snapshot(root, manifest)
    out = os.path.join(root, "出视频", "jobs_manifest.json")
    mv_utils.write_json(out, manifest)
    try:
        load_completion().mark_stage_complete(root, "video_jobs")
    except ValueError as exc:
        raise SystemExit(f"[err] video_jobs completion health 未通过：{exc}")
    return out, manifest


def load_manifest(root):
    path = os.path.join(root, "出视频", "jobs_manifest.json")
    if not os.path.exists(path):
        raise SystemExit("[err] 缺 出视频/jobs_manifest.json，先运行 video_jobs.py 生成任务包")
    manifest = mv_utils.load_json(path, {})
    recorded = manifest.get("clip_plan_sha256")
    current = mv_utils.content_hash(os.path.join(root, "分镜", "clip_plan.json"))
    if recorded and recorded != current:
        raise SystemExit("[err] jobs_manifest 已过期：clip_plan 变化；重建任务包后再登记/评分/挑版")
    if int(manifest.get("schema_version") or 0) >= MANIFEST_SCHEMA_VERSION:
        stale = freshness_errors(root, manifest)
        if stale:
            raise SystemExit(
                "[err] jobs_manifest 已过期：" + "；".join(stale[:8])
                + "；settings/compiler/prompt/image QC/reference 任一变化都必须重建任务包"
            )
    return path, manifest


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


def find_sequence_unit(manifest, unit_id):
    for unit in manifest.get("sequence_units", []):
        if unit.get("unit_id") == unit_id:
            return unit
    raise SystemExit(f"[err] jobs_manifest 里没有多镜头单元 {unit_id}")


def load_submit_receipt(path):
    if not path or not os.path.isfile(path):
        raise SystemExit(f"[err] 缺实际 submit receipt：{path or '未提供'}")
    payload = mv_utils.load_json(path, None)
    if not isinstance(payload, dict):
        raise SystemExit(f"[err] submit receipt 不是 JSON object：{path}")
    return payload


def _safe_project_ref(root, path):
    absolute = os.path.abspath(os.path.join(root, str(path or "")))
    if os.path.commonpath((root, absolute)) != root:
        raise SystemExit(f"[err] submit receipt reference 越出作品根：{path}")
    return absolute


def validate_submit_receipt(
    root, record, take_id, payload, *, sequence=False, expected_output_sha256=""
):
    expected_kind = SEQUENCE_RECEIPT_KIND if sequence else SUBMIT_RECEIPT_KIND
    item_id = record.get("unit_id") if sequence else record.get("clip_id")
    expected_job_id = f"{item_id}/{take_id}"
    route = record.get("provider_route") or {}
    controls = record.get("compiled_request_controls") or {}
    controls_hash = record.get("compiled_request_controls_sha256") or stable_hash(controls)
    channel = record.get("video_channel") or record.get("backend")
    formal_route = provider_evidence.route_requires_evidence(route)
    try:
        receipt_schema = int(payload.get("schema_version") or 0)
    except (TypeError, ValueError):
        receipt_schema = 0
    errors = []
    if payload.get("kind") != expected_kind:
        errors.append("receipt_schema_mismatch")
    if formal_route and receipt_schema != provider_evidence.RECEIPT_SCHEMA_VERSION:
        errors.append("provider_evidence_receipt_schema_required")
    elif not formal_route and receipt_schema not in {1, provider_evidence.RECEIPT_SCHEMA_VERSION}:
        errors.append("receipt_schema_mismatch")
    if payload.get("template_only") is not False:
        errors.append("receipt_is_unattested_template")
    if str(payload.get("job_id") or "") != expected_job_id:
        errors.append("receipt_job_id_mismatch")
    if str(payload.get("take_id") or "") != take_id:
        errors.append("receipt_take_id_mismatch")
    if str(payload.get("model") or "") != str(record.get("video_model") or ""):
        errors.append("receipt_model_mismatch")
    if str(payload.get("channel") or "") != str(channel or ""):
        errors.append("receipt_channel_mismatch")
    if str(payload.get("provider_id") or "") != str(route.get("provider_id") or ""):
        errors.append("receipt_provider_id_mismatch")
    if not str(payload.get("provider_job_id") or "").strip():
        errors.append("receipt_provider_job_id_missing")
    if not str(payload.get("submitted_at") or "").strip():
        errors.append("receipt_submitted_at_missing")
    else:
        try:
            provider_evidence.validate_submitted_at(payload.get("submitted_at"))
        except ValueError as exc:
            errors.append(str(exc))
    if formal_route and not str(payload.get("provider_status") or "").strip():
        errors.append("receipt_provider_status_missing")
    if str(payload.get("compiled_request_controls_sha256") or "") != controls_hash:
        errors.append("receipt_compiled_controls_hash_mismatch")
    actual_controls = payload.get("request_controls") or {}
    if actual_controls != controls or stable_hash(actual_controls) != controls_hash:
        errors.append("receipt_request_controls_mismatch")

    expected_refs = {}
    for row in controls.get("input_roles") or []:
        key = (str(row.get("role") or ""), str(row.get("path") or ""))
        expected_refs[key] = str(row.get("sha256") or "")
    actual_refs = {}
    for row in payload.get("submitted_refs") or []:
        if not isinstance(row, dict):
            errors.append("receipt_ref_not_object")
            continue
        key = (str(row.get("role") or ""), str(row.get("path") or ""))
        sha = str(row.get("sha256") or "")
        if row.get("confirmed_submitted") is not True:
            errors.append(f"receipt_ref_not_confirmed:{key[0]}:{key[1]}")
        if not video_capabilities.SHA256_RE.fullmatch(sha):
            errors.append(f"receipt_ref_sha_invalid:{key[0]}:{key[1]}")
        else:
            current = mv_utils.content_hash(_safe_project_ref(root, key[1]))
            if current != sha:
                errors.append(f"receipt_ref_current_sha_mismatch:{key[0]}:{key[1]}")
        if key in actual_refs:
            errors.append(f"receipt_ref_duplicate:{key[0]}:{key[1]}")
        actual_refs[key] = sha
    if actual_refs != expected_refs:
        errors.append("receipt_submitted_refs_do_not_match_compiled_controls")

    normalized_provider_evidence = None
    if formal_route:
        normalized_provider_evidence, evidence_errors = provider_evidence.validate_provider_evidence(
            root, route, payload, expected_output_sha256
        )
        errors.extend(evidence_errors)
    else:
        attest = payload.get("manual_attestation") or {}
        if not str(attest.get("reviewer") or "").strip():
            errors.append("manual_receipt_reviewer_missing")
        if not str(attest.get("notes") or "").strip():
            errors.append("manual_receipt_notes_missing")
    if errors:
        raise SystemExit("[err] submit receipt 被拒：" + "；".join(errors))
    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    if formal_route:
        normalized["provider_evidence"] = normalized_provider_evidence
    normalized.pop("receipt_sha256", None)
    normalized["receipt_sha256"] = stable_hash(normalized)
    return normalized


def _record_registered_take(
    root, manifest_path, manifest, job, take, src, receipt=None, generation=None, persist=True
):
    dst = os.path.join(root, take["video_path"])
    _atomic_copy_to_stable_path(src, dst)
    take["status"] = "registered"
    take["registered_at"] = date.today().isoformat()
    take["video_sha256"] = mv_utils.content_hash(dst)
    take.pop("first_frame_sha256", None)
    take.pop("end_frame_sha256", None)
    if receipt:
        take["submit_receipt"] = receipt
        take["submitted_reference_sha256_by_role"] = [
            {"role": row.get("role"), "path": row.get("path"), "sha256": row.get("sha256")}
            for row in receipt.get("submitted_refs") or []
        ]
        inherited = job.get("inherited_contract") or {}
        first_path = inherited.get("image_path")
        end_path = inherited.get("end_frame_path")
        for row in receipt.get("submitted_refs") or []:
            if row.get("path") == first_path and row.get("role") in {"start_frame", "reference_image"}:
                take["first_frame_sha256"] = row.get("sha256")
            if row.get("path") == end_path and row.get("role") == "end_frame":
                take["end_frame_sha256"] = row.get("sha256")
    else:
        take.pop("submit_receipt", None)
        take.pop("submitted_reference_sha256_by_role", None)
    if generation:
        take["generation"] = {k: v for k, v in generation.items() if v not in (None, "", [], {})}
    take["score"] = {}
    take.pop("scored_by", None)
    take.pop("scored_at", None)
    take.pop("selection_waiver", None)
    if job.get("selected_take") == take.get("take_id"):
        job["selected_take"] = None
        job.pop("selected_at", None)
        take["selection_invalidated_reason"] = "selected take was re-registered; score/select and video QC must run again"
    if persist:
        mv_utils.write_json(manifest_path, manifest)
    return dst


def validate_cut_map(unit, jobs, src, actual_duration, payload):
    errors = []
    if not isinstance(payload, dict) or payload.get("kind") != CUT_MAP_KIND or int(payload.get("schema_version") or 0) != 1:
        errors.append("cut_map_schema_mismatch")
    if str(payload.get("unit_id") or "") != str(unit.get("unit_id") or ""):
        errors.append("cut_map_unit_id_mismatch")
    if str(payload.get("source_sha256") or "") != mv_utils.content_hash(src):
        errors.append("cut_map_source_sha256_mismatch")
    if not str(payload.get("reviewer") or "").strip():
        errors.append("cut_map_reviewer_missing")
    if not str(payload.get("notes") or "").strip():
        errors.append("cut_map_notes_missing")
    method = str(payload.get("review_method") or "")
    if method not in {"frame_accurate_visual_review", "nle_marker_export", "provider_shot_metadata_verified"}:
        errors.append("cut_map_review_method_not_evidentiary")
    try:
        boundaries = [float(v) for v in payload.get("actual_boundaries_seconds") or []]
    except (TypeError, ValueError):
        boundaries = []
        errors.append("cut_map_boundaries_invalid")
    if len(boundaries) != len(jobs) + 1:
        errors.append("cut_map_boundary_count_mismatch")
    elif any(b <= a for a, b in zip(boundaries, boundaries[1:])):
        errors.append("cut_map_boundaries_not_strictly_increasing")
    else:
        edge_tolerance = max(1 / 24, actual_duration * 0.01)
        if abs(boundaries[0]) > edge_tolerance or abs(boundaries[-1] - actual_duration) > edge_tolerance:
            errors.append("cut_map_source_edges_mismatch")
        for index, job in enumerate(jobs):
            observed = boundaries[index + 1] - boundaries[index]
            planned = float(job.get("duration") or 0)
            tolerance = max(0.10, planned * 0.02)
            if abs(observed - planned) > tolerance:
                errors.append(
                    f"cut_map_segment_duration_mismatch:{job.get('clip_id')}:{observed:.3f}!={planned:.3f}"
                )
    if errors:
        raise SystemExit("[err] 多镜头 cut map 被拒：" + "；".join(errors))
    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    normalized["cut_map_sha256"] = stable_hash(payload)
    return boundaries, normalized


def register_sequence(root, unit_id, take_id, src, cut_map_path="", submit_receipt=None):
    """Split a reviewed multi-shot master at named, observed boundaries."""
    if not os.path.isfile(src):
        raise SystemExit(f"[err] 找不到多镜头母片：{src}")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("[err] 多镜头母片拆分需要 ffmpeg + ffprobe")
    _manifest_path, manifest = load_manifest(root)
    unit = find_sequence_unit(manifest, unit_id)
    clip_ids = unit.get("clip_ids") or []
    if len(clip_ids) < 2:
        raise SystemExit(f"[err] {unit_id} 不是有效的多镜头单元")
    jobs = [find_job(manifest, clip_id) for clip_id in clip_ids]
    # Fail before writing anything if the requested take slot does not exist.
    for job in jobs:
        find_take(job, take_id)
    expected = sum(float(job.get("duration") or 0) for job in jobs)
    probed = mv_utils.ffprobe_json(src, "-show_entries", "format=duration")
    try:
        actual = float((probed.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        raise SystemExit("[err] 无法读取多镜头母片时长")
    tolerance = max(0.10, expected * 0.02)
    if abs(actual - expected) > tolerance:
        raise SystemExit(
            f"[err] {unit_id} 母片 {actual:.3f}s 与锁定总时长 {expected:.3f}s "
            f"相差超过 {tolerance:.3f}s；先按任务时长重出，不能靠批量变速掩盖"
        )

    if not cut_map_path or not os.path.isfile(cut_map_path):
        raise SystemExit(
            "[err] --register-sequence 必须提供 --cut-map；需由具名复核者写实际镜头边界，"
            "不能把计划累计时长直接当作母片真实切点"
        )
    cut_payload = mv_utils.load_json(cut_map_path, None)
    boundaries, _verified_cut_map = validate_cut_map(unit, jobs, src, actual, cut_payload)
    sequence_receipt = None
    payload = None
    if int(manifest.get("schema_version") or 0) >= MANIFEST_SCHEMA_VERSION:
        payload = load_submit_receipt(submit_receipt) if isinstance(submit_receipt, str) else submit_receipt
        if not isinstance(payload, dict):
            raise SystemExit("[err] schema v4 多镜头登记必须提供 --submit-receipt")
        sequence_receipt = validate_submit_receipt(
            root, unit, take_id, payload, sequence=True,
            expected_output_sha256=mv_utils.content_hash(src),
        )

    prepared = []
    temp_dir = _sequence_split_work_dir(root, unit_id, take_id)
    try:
        for index, job in enumerate(jobs):
            source_start = boundaries[index]
            source_end = boundaries[index + 1]
            duration = source_end - source_start
            clip_id = job.get("clip_id")
            segment = os.path.join(temp_dir, f"{clip_id}_{take_id}.mp4")
            command = [
                "ffmpeg", "-n", "-v", "error", "-i", src, "-ss", f"{source_start:.6f}",
                "-t", f"{duration:.6f}", "-an", "-c:v", "libx264", "-profile:v", "high",
                "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                segment,
            ]
            proc = subprocess.run(command, capture_output=True, text=True)
            if proc.returncode:
                raise SystemExit(proc.stderr.strip() or f"[err] {clip_id} 序列拆分失败")
            prepared.append((clip_id, segment, source_start, duration))

        # Splitting may take minutes. Serialize only the stable-file + ledger
        # commit, then re-read and revalidate the current manifest while locked.
        with _registration_lock(root):
            manifest_path, manifest = load_manifest(root)
            unit = find_sequence_unit(manifest, unit_id)
            current_clip_ids = unit.get("clip_ids") or []
            if current_clip_ids != clip_ids:
                raise SystemExit(
                    f"[err] {unit_id} 拆分期间 sequence unit 已变化；请按当前任务包重新登记"
                )
            jobs = [find_job(manifest, clip_id) for clip_id in current_clip_ids]
            for job in jobs:
                find_take(job, take_id)
            locked_boundaries, verified_cut_map = validate_cut_map(
                unit, jobs, src, actual, cut_payload
            )
            if locked_boundaries != boundaries:
                raise SystemExit(f"[err] {unit_id} 拆分期间 cut map 解释发生变化；请重新登记")

            if int(manifest.get("schema_version") or 0) >= MANIFEST_SCHEMA_VERSION:
                if not isinstance(payload, dict):
                    raise SystemExit("[err] schema v4 多镜头登记必须提供 --submit-receipt")
                sequence_receipt = validate_submit_receipt(
                    root, unit, take_id, payload, sequence=True,
                    expected_output_sha256=mv_utils.content_hash(src),
                )
            else:
                sequence_receipt = None

            registrations = []
            # All splits succeeded; publish complete files atomically and write
            # one coherent manifest while no other register process can interleave.
            for clip_id, segment, source_start, duration in prepared:
                job = find_job(manifest, clip_id)
                take = find_take(job, take_id)
                derived_receipt = None
                if sequence_receipt:
                    relevant_paths = {
                        str((job.get("inherited_contract") or {}).get("image_path") or ""),
                        str((job.get("inherited_contract") or {}).get("end_frame_path") or ""),
                    }
                    relevant_paths.update(
                        str(row.get("path") or "")
                        for row in job.get("reference_inputs") or []
                        if isinstance(row, dict)
                    )
                    derived_receipt = json.loads(json.dumps(sequence_receipt, ensure_ascii=False))
                    parent_receipt_sha256 = derived_receipt.pop("receipt_sha256", "")
                    derived_receipt.update({
                        "kind": "mv_video_sequence_derived_receipt",
                        "parent_unit_id": unit_id,
                        "parent_job_id": sequence_receipt.get("job_id"),
                        "parent_receipt_sha256": parent_receipt_sha256,
                        "job_id": f"{clip_id}/{take_id}",
                        "clip_id": clip_id,
                        "unit_id": unit_id,
                        "submitted_refs": [
                            row for row in sequence_receipt.get("submitted_refs") or []
                            if str(row.get("path") or "") in relevant_paths
                        ],
                    })
                    derived_receipt["receipt_sha256"] = stable_hash(derived_receipt)
                dst = _record_registered_take(
                    root, manifest_path, manifest, job, take, segment,
                    receipt=derived_receipt, persist=False,
                )
                registrations.append({
                    "clip_id": clip_id,
                    "take_id": take_id,
                    "video_path": rel(root, dst),
                    "video_sha256": mv_utils.content_hash(dst),
                    "source_start": round(source_start, 6),
                    "duration": round(duration, 6),
                })

            unit.update({
                "status": "split_registered",
                "registered_at": date.today().isoformat(),
                "source_basename": os.path.basename(src),
                "source_sha256": mv_utils.content_hash(src),
                "source_duration": round(actual, 6),
                "submit_receipt": sequence_receipt,
                "verified_cut_map": verified_cut_map,
                "registrations": registrations,
            })
            mv_utils.write_json(manifest_path, manifest)
            return registrations
    finally:
        _cleanup_sequence_split_work_dir(root, temp_dir)


def register_take(root, clip_id, take_id, src, generation=None, submit_receipt=None):
    if not os.path.exists(src):
        raise SystemExit(f"[err] 找不到视频文件：{src}")
    with _registration_lock(root):
        manifest_path, manifest = load_manifest(root)
        job = find_job(manifest, clip_id)
        take = find_take(job, take_id)
        receipt = None
        if int(manifest.get("schema_version") or 0) >= MANIFEST_SCHEMA_VERSION:
            payload = load_submit_receipt(submit_receipt) if isinstance(submit_receipt, str) else submit_receipt
            if not isinstance(payload, dict):
                raise SystemExit("[err] schema v4 register 必须提供 --submit-receipt；计划首尾帧不能冒充实际提交证据")
            generation = generation or {}
            if generation.get("seed") or generation.get("params"):
                raise SystemExit(
                    "[err] schema v4 不接受登记时追加未编译的 seed/generation-param；"
                    "所有实际请求控制必须先进入 compiled_request_controls 并由 submit receipt 精确绑定"
                )
            supplemental_job_id = str(generation.get("provider_job_id") or "").strip()
            if supplemental_job_id and supplemental_job_id != str(payload.get("provider_job_id") or "").strip():
                raise SystemExit("[err] --provider-job-id 与 submit receipt.provider_job_id 冲突")
            expected = dict(job)
            expected.update({
                "provider_route": take.get("provider_route") or job.get("provider_route"),
                "compiled_request_controls": take.get("compiled_request_controls"),
                "compiled_request_controls_sha256": take.get("compiled_request_controls_sha256"),
            })
            receipt = validate_submit_receipt(
                root, expected, take_id, payload,
                expected_output_sha256=mv_utils.content_hash(src),
            )
            generation = None  # receipt is the sole v4 provider submission ledger
        # schema <=3 stays readable/registerable, but never auto-creates frame SHA
        # evidence. Rebuilding the job pack upgrades it to the strict receipt path.
        return _record_registered_take(
            root, manifest_path, manifest, job, take, src,
            receipt=receipt, generation=generation,
        )


def score_take(root, clip_id, take_id, args):
    if not str(args.reviewer or "").strip():
        raise SystemExit("[err] take 评分必须提供 --reviewer；挑版判断不能匿名")
    manifest_path, manifest = load_manifest(root)
    job = find_job(manifest, clip_id)
    take = find_take(job, take_id)
    video_path = os.path.join(root, take.get("video_path") or "")
    if not os.path.isfile(video_path):
        raise SystemExit(f"[err] {clip_id} {take_id} 尚未 --register 实际视频，不能给不存在的 take 评分")
    if take.get("video_sha256") != mv_utils.content_hash(video_path):
        raise SystemExit(f"[err] {clip_id} {take_id} 登记后文件已变化；请重新 --register 再评分")
    score = dict(take.get("score") or {})
    for key, attr in (
        ("motion", "motion_score"),
        ("identity", "identity_score"),
        ("beat_fit", "beat_score"),
        ("clarity", "clarity_score"),
        ("seam_fit", "seam_score"),
        ("lip_sync", "lip_sync_score"),
    ):
        value = getattr(args, attr)
        if value is not None:
            score[key] = value
    nums = [
        value for key, value in score.items()
        if key != "average" and isinstance(value, (int, float))
    ]
    if nums:
        score["average"] = round(sum(nums) / len(nums), 2)
    take["score"] = score
    take["scored_by"] = str(args.reviewer).strip()
    take["scored_at"] = date.today().isoformat()
    if args.notes is not None:
        take["notes"] = args.notes
    take["status"] = "scored"
    if job.get("selected_take") == take_id:
        job["selected_take"] = None
        job.pop("selected_at", None)
        take["selection_invalidated_reason"] = "selected take was rescored; select and video QC must run again"
    mv_utils.write_json(manifest_path, manifest)


def selection_errors(take, job=None):
    score = take.get("score") or {}
    required = ["motion", "identity", "beat_fit", "clarity"]
    job = job or {}
    if (job.get("seam_contract") or {}).get("continuity_required"):
        required.append("seam_fit")
    if job.get("lip_sync_required"):
        required.append("lip_sync")
    missing = [key for key in required if not isinstance(score.get(key), (int, float))]
    errors = [f"评分缺字段：{', '.join(missing)}"] if missing else []
    if not str(take.get("scored_by") or "").strip():
        errors.append("评分缺 scored_by")
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


def select_take(root, clip_id, take_id, waiver_reason="", reviewer=""):
    manifest_path, manifest = load_manifest(root)
    job = find_job(manifest, clip_id)
    take = find_take(job, take_id)
    errors = selection_errors(take, job)
    if errors and not waiver_reason:
        raise SystemExit("[err] 挑版被阻断：" + "；".join(errors) + "。先补全四维评分，或显式 --waiver-reason 留痕")
    if errors:
        if not str(reviewer or "").strip():
            raise SystemExit("[err] --waiver-reason 必须同时提供 --reviewer；例外挑版不能匿名")
        take["selection_waiver"] = {
            "reason": waiver_reason,
            "reviewer": str(reviewer).strip(),
            "date": date.today().isoformat(),
            "errors": errors,
        }
    else:
        take.pop("selection_waiver", None)
    src = os.path.join(root, take["video_path"])
    if not os.path.exists(src):
        raise SystemExit(f"[err] {clip_id} {take_id} 尚未登记视频：{take['video_path']}")
    registered_hash = str(take.get("video_sha256") or "")
    current_hash = mv_utils.content_hash(src)
    if not registered_hash or registered_hash != current_hash:
        raise SystemExit(f"[err] {clip_id} {take_id} 登记后文件已变化；请重新 --register 再评分/挑版")
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
    take.pop("selection_invalidated_reason", None)
    mv_utils.write_json(manifest_path, manifest)
    update_timeline(root, clip_id, rel(root, dst))
    if all(j.get("selected_take") for j in manifest.get("jobs", [])):
        run_final_video_checks(root)
        print(
            "[next] 所有项目均需逐镜/接缝具名语义签收："
            "video_qc.py --accept-semantic --reviewer <name> --notes <复核说明>"
        )
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
    ap.add_argument("--backend", help="生视频访问渠道；先经适配层归一，未知渠道会透明拒绝")
    ap.add_argument("--adapter-record", help="manual/自定义 model×channel 的显式 provider adapter JSON")
    ap.add_argument("--video-spec", choices=contract.MV_VIDEO_SPECS)
    ap.add_argument("--register", help="登记一个外部生成的视频文件")
    ap.add_argument("--register-sequence", help="登记多镜头母片并按具名复核的真实边界拆回逐 clip take")
    ap.add_argument("--unit", help="配合 --register-sequence，如 Sequence_001")
    ap.add_argument("--submit-receipt", help="实际 provider submit receipt JSON；schema v4 登记必填")
    ap.add_argument("--cut-map", help="多镜头母片的具名实际边界复核 JSON；--register-sequence 必填")
    ap.add_argument("--clip", help="配合 --register/--select 使用，1/Clip_001 均可")
    ap.add_argument("--take", help="配合 --register/--select 使用，1/take_01 均可")
    ap.add_argument("--score", help="给某个 clip 的 take 评分，1/Clip_001 均可")
    ap.add_argument("--motion-score", type=int, choices=range(1, 6))
    ap.add_argument("--identity-score", type=int, choices=range(1, 6))
    ap.add_argument("--beat-score", type=int, choices=range(1, 6))
    ap.add_argument("--clarity-score", type=int, choices=range(1, 6))
    ap.add_argument("--seam-score", type=int, choices=range(1, 6), help="连续接缝的姿态相位/方向/光色适配；该镜要求连续时必填")
    ap.add_argument("--lip-sync-score", type=int, choices=range(1, 6), help="performance_vocal 且启用口型时必填")
    ap.add_argument("--reviewer", help="评分人；--score 必填")
    ap.add_argument("--notes")
    ap.add_argument("--select", help="选择某个 clip 的 take 定稿，1/Clip_001 均可")
    ap.add_argument("--waiver-reason", help="评分未达门槛时的显式人工放行原因；会写入 manifest")
    ap.add_argument("--seed", help="仅旧 schema 登记兼容；schema v4 的 seed 必须先进入 compiled controls/receipt")
    ap.add_argument("--generation-param", action="append", default=[], metavar="K=V",
                    help="仅旧 schema 登记兼容；schema v4 禁止登记时追加未编译参数")
    ap.add_argument("--provider-job-id", default="", help="旧 schema 兼容；v4 若提供必须与 submit receipt 完全一致")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    if not any((args.register, args.register_sequence, args.score, args.select)):
        out, manifest = create_jobs(root, args)
        print(f"[ok] video jobs → {out}（{len(manifest['jobs'])} clips）")
        return

    if args.register:
        clip_id = normalize_clip_id(args.clip)
        take_id = normalize_take_id(args.take)
        params = {}
        for pair in args.generation_param:
            if "=" not in pair:
                raise SystemExit(f"[err] --generation-param 格式应为 K=V，收到：{pair}")
            key, value = pair.split("=", 1)
            params[key.strip()] = value.strip()
        generation = {"seed": (args.seed or "").strip(), "params": params,
                      "provider_job_id": args.provider_job_id.strip()}
        dst = register_take(
            root, clip_id, take_id, args.register, generation=generation,
            submit_receipt=args.submit_receipt,
        )
        print(f"[ok] {clip_id} {take_id} 登记 → {dst}")

    if args.register_sequence:
        if not args.unit:
            raise SystemExit("[err] --register-sequence 必须同时提供 --unit Sequence_XXX")
        take_id = normalize_take_id(args.take or "1")
        rows = register_sequence(
            root, args.unit, take_id, args.register_sequence,
            cut_map_path=args.cut_map or "", submit_receipt=args.submit_receipt,
        )
        print(f"[ok] {args.unit} 已按具名复核的真实切点拆分并登记 {len(rows)} 个 {take_id}")

    if args.score:
        clip_id = normalize_clip_id(args.score)
        take_id = normalize_take_id(args.take)
        score_take(root, clip_id, take_id, args)
        print(f"[ok] {clip_id} {take_id} 评分已写入 jobs_manifest.json")

    if args.select:
        clip_id = normalize_clip_id(args.select)
        take_id = normalize_take_id(args.take)
        dst = select_take(root, clip_id, take_id, args.waiver_reason or "", args.reviewer or "")
        print(f"[ok] {clip_id} {take_id} 已定稿 → {dst}")


if __name__ == "__main__":
    main()
