#!/usr/bin/env python3
"""Recoverable n2d video batch runner.

The runner keeps a stable manifest in `生产数据/video_batch_<episode>_<range>.json`
and drives the expensive image2video step from that manifest. It is deliberately
small: stage-specific creative decisions still live in n2d-video prompts and
gates; this script handles state, subprocess calls, downloads, QC, telemetry,
and progress updates. The costly submit command runs video_preflight by default
immediately before invoking the backend.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR.parents[1]
REPO_ROOT = SKILLS_DIR.parent
COMMON_DIR = SKILLS_DIR / "n2d" / "_lib"
DASHBOARD_PY = SKILLS_DIR / "n2d-dashboard" / "scripts" / "dashboard.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

try:
    from n2d_route import normalize_episode, parse_progress
except Exception:  # pragma: no cover
    normalize_episode = lambda value: str(value).strip()  # type: ignore[assignment]
    parse_progress = None  # type: ignore[assignment]

import video_qc

CLIP_HEADING_RE = re.compile(r"^##\s*Clip[_\s]*(\d+)(?:（([^）]+)）)?", re.MULTILINE)
FIRST_FRAME_RE = re.compile(r"\*\*首帧\*\*[^`]*`([^`]+\.png)`")
END_FRAME_RE = re.compile(r"\*\*尾帧\*\*[^`]*`([^`]+\.png)`")
ZH_PROMPT_RE = re.compile(r"###\s*视频 prompt（中文[^`]*```(?:\w+)?\s*(.*?)```", re.DOTALL)
FENCE_RE = re.compile(r"```(?:\w+)?\s*(.*?)```", re.DOTALL)
DURATION_RE = re.compile(r"时长\s*([0-9]+(?:\.[0-9]+)?)\s*s", re.IGNORECASE)


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def formal_video_dir(root: Path, episode: str) -> Path:
    return root / "出视频" / episode / "视频"


def prompt_pack_path(root: Path, episode: str) -> Path:
    return root / "出视频" / episode / "prompt" / "01_clips.md"


def batch_id(start: int, end: int) -> str:
    return f"{start:02d}_{end:02d}"


def manifest_path(root: Path, episode: str, start: int, end: int) -> Path:
    return production_dir(root) / f"video_batch_{episode}_{batch_id(start, end)}.json"


def stable_prompt_dir(root: Path, episode: str, start: int, end: int) -> Path:
    return production_dir(root) / "video_batches" / episode / batch_id(start, end) / "prompts"


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, item: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def clip_key(number: int) -> str:
    return f"Clip_{number:02d}"


def _duration_from_heading(text: str) -> Optional[float]:
    match = DURATION_RE.search(text or "")
    return float(match.group(1)) if match else None


def submit_duration(story_duration: Optional[float], minimum: int = 4, maximum: int = 15) -> int:
    if story_duration is None:
        return minimum
    return max(minimum, min(maximum, int(math.ceil(story_duration))))


def _extract_prompt(block: str) -> str:
    match = ZH_PROMPT_RE.search(block)
    if match:
        return match.group(1).strip()
    fallback = FENCE_RE.search(block)
    if fallback:
        return fallback.group(1).strip()
    raise ValueError("clip block has no fenced video prompt")


def split_clip_blocks(text: str) -> List[Tuple[int, str, str]]:
    matches = list(CLIP_HEADING_RE.finditer(text))
    blocks: List[Tuple[int, str, str]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        number = int(match.group(1))
        heading = match.group(0).strip()
        blocks.append((number, heading, text[start:end]))
    return blocks


def parse_prompt_pack(root: Path, episode: str, start: int, end: int) -> List[Dict[str, Any]]:
    text = prompt_pack_path(root, episode).read_text(encoding="utf-8")
    out: List[Dict[str, Any]] = []
    for number, heading, block in split_clip_blocks(text):
        if number < start or number > end:
            continue
        first = FIRST_FRAME_RE.search(block)
        if not first:
            raise ValueError(f"{clip_key(number)} missing **首帧** PNG path")
        image_rel = first.group(1).strip()
        image = (root / image_rel).resolve() if not Path(image_rel).is_absolute() else Path(image_rel)
        
        last = END_FRAME_RE.search(block)
        end_image_rel = last.group(1).strip() if last else None
        end_image = (root / end_image_rel).resolve() if end_image_rel and not Path(end_image_rel).is_absolute() else (Path(end_image_rel) if end_image_rel else None)

        prompt = _extract_prompt(block)
        target = Path(image.name).with_suffix(".mp4").name
        story_duration = _duration_from_heading(heading) or _duration_from_heading(block)
        out.append({
            "clip": clip_key(number),
            "heading": heading,
            "image": str(image),
            "image_rel": image_rel,
            "end_image": str(end_image) if end_image else None,
            "end_image_rel": end_image_rel,
            "target": target,
            "story_duration": story_duration,
            "submit_duration": submit_duration(story_duration),
            "prompt_text": prompt,
            "status": "prepared",
        })
    expected = set(range(start, end + 1))
    got = {int(item["clip"].split("_")[1]) for item in out}
    missing = sorted(expected - got)
    if missing:
        raise ValueError("missing clip prompt blocks: " + ", ".join(clip_key(n) for n in missing))
    return out


def _clip_number(item: Dict[str, Any]) -> Optional[int]:
    m = re.search(r"(\d+)", str(item.get("clip") or ""))
    return int(m.group(1)) if m else None


def attach_multiframe(root: Path, item: Dict[str, Any], prompt_text: str,
                      anchors_by_clip: Dict[int, Dict[str, Any]]) -> None:
    """If the clip has valid in-range mid-anchors, attach multiframe2video fields to the item.

    Builds the ordered keyframe list [首帧, *锚帧(按 at_sec), 尾帧] and per-segment durations.
    Requires an end frame (the chain terminates at it) and a real clip duration. On any contract
    violation (segment out of [0.5,8], total<2, missing PNG) records item['multiframe_skip'] and
    leaves the item to fall back to the existing image2video/multimodal2video path."""
    num = _clip_number(item)
    info = anchors_by_clip.get(num) if num is not None else None
    if not info:
        return
    # Capability-driven, not label-driven: multiframe2video segments only need ≥0.5s, so EVERY
    # valid anchor is a usable keyframe — including ones the planner marked use=qc back when the
    # only executor was the ≥4s frames2video relay. The `use` field is now an advisory hint; the
    # multiframe_segments contract below is the real gate. (frames2video-only backends still treat
    # qc anchors as验收 baselines — that lives in their own path, not here.)
    split = [(t, png, hint) for t, png, use, hint in
             zip(info["times"], info["images"], info["uses"], info["hints"])
             if t is not None and png]
    if not split:
        item["multiframe_skip"] = "no anchors with both at_sec and png"
        return
    end_rel = item.get("end_image_rel")
    if not (end_rel and item.get("end_image") and Path(item["end_image"]).is_file()):
        item["multiframe_skip"] = "no end frame; multiframe chain needs a terminal keyframe"
        return
    duration = item.get("story_duration") or info.get("duration")
    if not isinstance(duration, (int, float)):
        item["multiframe_skip"] = "no clip duration to derive segment timing"
        return
    split.sort(key=lambda x: float(x[0]))
    anchor_times = [float(t) for t, _, _ in split]
    try:
        seg_durs = multiframe_segments(float(duration), anchor_times)
    except ValueError as exc:
        item["multiframe_skip"] = str(exc)
        return
    images_rel = [item["image_rel"]] + [png for _, png, _ in split] + [end_rel]
    images_abs = [str((root / r).resolve()) if not Path(r).is_absolute() else r for r in images_rel]
    missing = [r for r, a in zip(images_rel, images_abs) if not Path(a).is_file()]
    if missing:
        item["multiframe_skip"] = "anchor/keyframe PNG not yet generated: " + ", ".join(missing)
        return
    head = prompt_text.splitlines()[0].strip() if prompt_text.strip() else ""
    # 末段转场 prompt 用 Clip 的 end_state（具体落幅），缺则泛化句兜底
    last_dest = (info.get("end_state") or "").strip() or "承接进行中的动作，停在尾帧落幅"
    seg_prompts = []  # N-1 transition prompts; destination keyframe's beat hint, else clip head
    dests = [h for _, _, h in split] + [last_dest]
    for hint in dests:
        seg_prompts.append((hint or head or "continue the motion smoothly").strip()[:200])
    item["mode_backend"] = "multiframe2video"
    item["multiframe_images"] = images_abs
    item["multiframe_images_rel"] = images_rel
    item["multiframe_segment_durations"] = seg_durs
    item["multiframe_segment_prompts"] = seg_prompts


def prepare_manifest(root: Path, episode: str, start: int, end: int, *, backend: str, resolution: str,
                     model_version: str, force: bool = False) -> Dict[str, Any]:
    episode = normalize_episode(episode)
    path = manifest_path(root, episode, start, end)
    if path.exists() and not force:
        return load_json(path)
    prompts_dir = stable_prompt_dir(root, episode, start, end)
    prompts_dir.mkdir(parents=True, exist_ok=True)
    anchors_by_clip = clip_anchor_index(root, episode)
    items = []
    for item in parse_prompt_pack(root, episode, start, end):
        prompt_text = item.pop("prompt_text")
        prompt_file = prompts_dir / f"{item['target'][:-4]}.prompt.txt"
        prompt_file.write_text(prompt_text + "\n", encoding="utf-8")
        item["prompt_file"] = str(prompt_file)
        attach_multiframe(root, item, prompt_text, anchors_by_clip)
        items.append(item)
    payload = {
        "kind": "n2d_video_batch",
        "version": 1,
        "episode": episode,
        "batch": f"{start:02d}-{end:02d}",
        "batch_id": batch_id(start, end),
        "backend": backend,
        "model_version": model_version,
        "video_resolution": resolution,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "items": items,
    }
    atomic_write_json(path, payload)
    return payload




def find_item(manifest: Dict[str, Any], clip: str) -> Dict[str, Any]:
    for item in manifest.get("items", []):
        if item.get("clip") == clip:
            return item
    target = clip if clip.startswith("Clip_") else clip_key(int(clip))
    for item in manifest.get("items", []):
        if item.get("clip") == target:
            return item
    raise KeyError(f"clip not in manifest: {target}")


def update_manifest(path: Path, manifest: Dict[str, Any]) -> None:
    manifest["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    atomic_write_json(path, manifest)


# ── multiframe2video (即梦 智能多帧) — native multi-keyframe → one continuous clip ──
# Replaces the split-into-segments + ffmpeg-concat relay for backends that take N keyframes
# natively. CLI contract (verified via probe_cli.py, snapshot in references/cli_snapshots/):
#   dreamina multiframe2video --images a.png,b.png[,c.png...]
#     2 images : --prompt P --duration D
#     3+ images: --transition-prompt × (N-1)  --transition-duration × (N-1)
#   each segment ∈ [0.5, 8]s; total ≥ 2s; ratio inferred from first image;
#   model_version / video_resolution NOT supported by this command.
MULTIFRAME_SEG_MIN = 0.5
MULTIFRAME_SEG_MAX = 8.0
MULTIFRAME_TOTAL_MIN = 2.0


def multiframe_segments(clip_duration: float, anchor_times: Sequence[float], *,
                        seg_min: float = MULTIFRAME_SEG_MIN, seg_max: float = MULTIFRAME_SEG_MAX,
                        total_min: float = MULTIFRAME_TOTAL_MIN) -> List[float]:
    """Keyframe times [0, *anchor_times, clip_duration] → consecutive segment durations.

    Validates the CLI contract: each segment in [seg_min, seg_max], total ≥ total_min,
    strictly increasing. Raises ValueError (with a fix hint) so the caller can fall back
    to image2video/frames2video instead of submitting an invalid task."""
    times = [0.0] + sorted(float(t) for t in anchor_times) + [float(clip_duration)]
    segs = [round(times[i + 1] - times[i], 3) for i in range(len(times) - 1)]
    if any(s <= 0 for s in segs):
        raise ValueError(f"multiframe: non-increasing keyframe times {times}")
    bad = [s for s in segs if s < seg_min or s > seg_max]
    if bad:
        raise ValueError(
            f"multiframe: segment(s) {bad} outside [{seg_min},{seg_max}]s (all={segs}); "
            "re-plan anchors (anchor_planner) so each gap fits — too long→add anchor, too short→drop one")
    if round(sum(segs), 3) < total_min:
        raise ValueError(f"multiframe: total {sum(segs):.3f}s < {total_min}s; clip too short for multiframe2video")
    return segs


def _dreamina_multiframe_args(images: Sequence[str], segment_durations: Sequence[float],
                              segment_prompts: Sequence[str], *, poll: int = 0) -> List[str]:
    """Build the `dreamina multiframe2video` argv. N images → N-1 segments."""
    n = len(images)
    if not (2 <= n <= 20):
        raise ValueError(f"multiframe2video needs 2-20 images, got {n}")
    if len(segment_durations) != n - 1:
        raise ValueError(f"{n} images need {n - 1} segment durations, got {len(segment_durations)}")
    args = ["dreamina", "multiframe2video", "--images", ",".join(images)]
    if n == 2:
        prompt = (list(segment_prompts) or [""])[0]
        args += ["--prompt", prompt, "--duration", str(segment_durations[0])]
    else:
        if len(segment_prompts) != n - 1:
            raise ValueError(f"{n} images need {n - 1} transition prompts, got {len(segment_prompts)}")
        for p in segment_prompts:
            args += ["--transition-prompt", p]
        for d in segment_durations:
            args += ["--transition-duration", str(d)]
    if poll:
        args += ["--poll", str(poll)]
    return args


# Required flags per dreamina command, asserted live before each paid submit (CLI-drift guard).
_CLI_REQUIRED_FLAGS = {
    "multiframe2video": ["images", "prompt", "duration", "transition-prompt", "transition-duration"],
    "frames2video": ["first", "last", "prompt", "duration"],
    "image2video": ["image", "prompt"],
    "multimodal2video": ["image", "prompt", "duration"],
}


def verify_cli_contract(cli: str, command: str) -> None:
    """Run `<cli> <command> --help` and assert the flags the arg builder uses still exist.
    Raises RuntimeError on drift so we don't burn credits on a stale invocation. Silently
    skips if probe_cli or the CLI isn't importable/available (don't block on the guard itself)."""
    requires = _CLI_REQUIRED_FLAGS.get(command)
    if not requires:
        return
    try:
        import probe_cli
        binary = probe_cli.resolve_bin(cli, None)
        if not binary:
            return  # CLI not found here (e.g. manual/headless env) — submit path handles that
        ok, msg = probe_cli.verify(cli, binary, command, requires)
    except Exception:
        return  # probe unavailable → don't block; this is a guard, not a gate
    if not ok:
        raise RuntimeError(
            f"CLI contract drift before paid submit: {msg}. "
            f"Re-run `python3 skills/n2d-video/scripts/probe_cli.py probe` to refresh snapshots "
            f"and update the arg builder before spending credits.")


def storyboard_path(root: Path, episode: str) -> Path:
    return root / "脚本" / normalize_episode(episode) / "storyboard.json"


def beat_hint_at(clip: Dict[str, Any], at_sec: Optional[float]) -> str:
    """表演节拍中 at_sec 时刻"到达的那一拍"，取自 template_contract.beats。

    用作 multiframe2video 的**转场 prompt** —— 让每段描述真实运动（起手→命中），而不是规划器
    的元数据 reason（"auto: R1 高运动模板…"，那是给人读报告的、绝不能当运动描述喂模型）。
    缺 beats 时返回 ""（attach_multiframe 会回退到 Clip 主 prompt 头）。"""
    tc = clip.get("template_contract")
    beats = tc.get("beats") if isinstance(tc, dict) else None
    if not (isinstance(beats, list) and beats):
        return ""
    duration = clip.get("duration")
    if not isinstance(at_sec, (int, float)) or not isinstance(duration, (int, float)) or duration <= 0:
        return str(beats[len(beats) // 2])  # 无可用时间 → 取中间拍
    idx = int(float(at_sec) / float(duration) * len(beats))
    return str(beats[max(0, min(len(beats) - 1, idx))])


def clip_anchor_index(root: Path, episode: str) -> Dict[int, Dict[str, Any]]:
    """{clip_number: {"times": [at_sec...], "images": [rel png...], "hints": [beat...], "duration"}}
    from storyboard.json. 读 continuity.anchors（N 锚链）或 continuity.midframe（单锚）。

    `hints` 是各锚帧的**运动转场提示**，按 at_sec 从 template_contract.beats 取真值（见 beat_hint_at），
    不再把规划器 reason 当 prompt。capability-driven：所有有 at_sec+png 的锚帧都返回，use 字段仅作
    advisory（multiframe2video 段只需 ≥0.5s，旧 use=qc 标签不再拦）。storyboard 缺失时返回 {}。"""
    path = storyboard_path(root, episode)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for i, clip in enumerate(data.get("clips") or [], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        anchors = cont.get("anchors")
        if anchors is None and isinstance(cont.get("midframe"), dict):
            mid = cont["midframe"]
            anchors = [{"anchor_png": mid.get("midframe_png"), "at_sec": mid.get("split_at_sec"),
                        "use": "split"}]
        if not isinstance(anchors, list) or not anchors:
            continue
        times, images, uses, hints = [], [], [], []
        for a in anchors:
            if not isinstance(a, dict):
                continue
            times.append(a.get("at_sec"))
            images.append(a.get("anchor_png"))
            uses.append(a.get("use", "split"))
            # 转场 prompt 用真运动（按 at_sec 取拍），不用规划器 reason 元数据
            hints.append(beat_hint_at(clip, a.get("at_sec")))
        out[i] = {"times": times, "images": images, "uses": uses, "hints": hints,
                  "duration": clip.get("duration"),
                  "end_state": str(cont.get("end_state") or "")}  # 末段转场 prompt 用它，比泛化句具体
    return out


def _dreamina_args(item: Dict[str, Any], manifest: Dict[str, Any]) -> List[str]:
    prompt = Path(item["prompt_file"]).read_text(encoding="utf-8").strip()

    # Native multi-keyframe path (即梦 智能多帧): first + mid-anchors + end → one continuous clip.
    # Prepared by prepare_manifest when storyboard has valid in-range anchors; falls back below
    # if the segment contract can't be met (recorded as item["multiframe_skip"]).
    mf_images = item.get("multiframe_images")
    if mf_images and len(mf_images) >= 2 and item.get("multiframe_segment_durations"):
        seg_prompts = item.get("multiframe_segment_prompts") or (
            [prompt] if len(mf_images) == 2 else [prompt] * (len(mf_images) - 1))
        return _dreamina_multiframe_args(
            mf_images, item["multiframe_segment_durations"], seg_prompts,
            poll=int(manifest.get("poll") or 0))

    # Two-frame (首帧 + 尾帧) clip without mid-anchors → multimodal2video with both frames.
    has_end_image = item.get("end_image") and Path(item["end_image"]).is_file()
    if has_end_image:
        return [
            "dreamina", "multimodal2video",
            "--image", item["image"],
            "--image", item["end_image"],
            "--prompt", prompt,
            "--duration", str(item["submit_duration"]),
            "--ratio", "9:16",
            "--video_resolution", manifest.get("video_resolution") or "720p",
            "--model_version", manifest.get("model_version") or "3.0",
        ]

    # Fallback to standard image2video for single-frame sources
    return [
        "dreamina",
        "image2video",
        "--image",
        item["image"],
        "--prompt",
        prompt,
        "--duration",
        str(item["submit_duration"]),
        "--video_resolution",
        manifest.get("video_resolution") or "720p",
        "--model_version",
        manifest.get("model_version") or "3.0",
    ]


def append_submission_log(root: Path, episode: str, row: Dict[str, Any]) -> None:
    append_jsonl(production_dir(root) / f"video_submissions_{episode}.jsonl", row)


def run_preflight_gate(root: Path, episode: str, stage: str = "video_preflight") -> None:
    proc = subprocess.run(
        [sys.executable, str(DASHBOARD_PY), "gate", str(root), episode, "--stage", stage],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        detail = "\n".join(part for part in (proc.stdout.strip(), proc.stderr.strip()) if part)
        raise RuntimeError(f"{stage} gate blocked video backend submission.\n{detail}")


def submit_clip(root: Path, manifest_file: Path, clip: str, *, dry_run: bool = False,
                skip_preflight: bool = False) -> Dict[str, Any]:
    manifest = load_json(manifest_file)
    episode = manifest["episode"]
    item = find_item(manifest, clip)
    if item.get("submit_id") and item.get("status") not in {"failed", "rejected"}:
        raise RuntimeError(f"{item['clip']} already has submit_id={item['submit_id']}; query or reject before resubmitting")
    args = _dreamina_args(item, manifest)
    command = args[1] if len(args) > 1 else args[0]
    safe_args = [args[0], command, "…(args elided)…"]
    if dry_run:
        return {"dry_run": True, "cmd_argv": safe_args, "clip": item["clip"],
                "backend_command": command}
    # "每次都跑一遍": cheap live --help check before spending credits — fail fast if the CLI
    # contract drifted out from under the arg builder (no-op/skip if probe unavailable).
    verify_cli_contract(args[0], command)
    if not skip_preflight:
        run_preflight_gate(root, episode)
    item.update({"status": "submitting", "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    item.pop("fail_reason", None)
    update_manifest(manifest_file, manifest)
    started = time.time()
    proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    elapsed = time.time() - started
    parsed: Dict[str, Any] = {}
    try:
        parsed = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        parsed = {"raw_stdout": proc.stdout}
    row = {
        "clip": item["clip"],
        "cmd_argv": safe_args,
        "image": item["image"],
        "duration": item["submit_duration"],
        "returncode": proc.returncode,
        "elapsed_sec": elapsed,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    append_submission_log(root, episode, row)
    item["last_submit_returncode"] = proc.returncode
    item["last_submit_elapsed_sec"] = elapsed
    item["last_submit_stdout_path"] = str(production_dir(root) / f"video_submissions_{episode}.jsonl")
    if proc.returncode != 0:
        item["status"] = "submit_failed"
        item["fail_reason"] = proc.stderr.strip() or f"exit {proc.returncode}"
    else:
        item["submit_id"] = parsed.get("submit_id") or item.get("submit_id")
        item["gen_status"] = parsed.get("gen_status")
        item["credit_count"] = parsed.get("credit_count")
        item["logid"] = parsed.get("logid")
        if parsed.get("gen_status") == "fail":
            item["status"] = "failed"
            item["fail_reason"] = parsed.get("fail_reason") or "generation failed"
        else:
            item["status"] = "submitted" if item.get("submit_id") else "submitted_unknown_id"
            item.pop("fail_reason", None)
    update_manifest(manifest_file, manifest)
    return item


def _mp4_set(directory: Path) -> set[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    return {p.resolve() for p in directory.glob("*.mp4")}


def _newest_mp4(directory: Path, before: set[Path]) -> Optional[Path]:
    candidates = [p for p in directory.glob("*.mp4") if p.resolve() not in before]
    if not candidates:
        candidates = list(directory.glob("*.mp4"))
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def query_clip(root: Path, manifest_file: Path, clip: str, *, download: bool = True, force: bool = False) -> Dict[str, Any]:
    manifest = load_json(manifest_file)
    episode = manifest["episode"]
    item = find_item(manifest, clip)
    submit_id = item.get("submit_id")
    if not submit_id:
        raise RuntimeError(f"{item['clip']} has no submit_id")
    download_dir = formal_video_dir(root, episode) / "_downloads"
    before = _mp4_set(download_dir)
    args = ["dreamina", "query_result", f"--submit_id={submit_id}", f"--download_dir={download_dir}"]
    proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    item["last_query_returncode"] = proc.returncode
    item["last_query_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    try:
        item["last_query"] = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        item["last_query"] = {"raw_stdout": proc.stdout}
    if proc.returncode != 0:
        item["status"] = "query_failed"
        item["fail_reason"] = proc.stderr.strip() or f"query_result exit {proc.returncode}"
        update_manifest(manifest_file, manifest)
        return item
    item.pop("fail_reason", None)
    found = _newest_mp4(download_dir, before) if download else None
    if found:
        target = formal_video_dir(root, episode) / item["target"]
        if target.exists() and not force:
            item["status"] = "downloaded_existing_target"
            item["downloaded_path"] = str(found)
            item["target_path"] = str(target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(found), str(target))
            item["status"] = "downloaded"
            item["target_path"] = str(target)
    else:
        item["status"] = "queried"
    update_manifest(manifest_file, manifest)
    return item


def _load_dashboard_module():
    path = SKILLS_DIR / "n2d-dashboard" / "scripts" / "dashboard.py"
    spec = importlib.util.spec_from_file_location("n2d_dashboard", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def qc_override_payload(clip: str, machine: Dict[str, Any]) -> Dict[str, Any]:
    """人工 --allow-qc-block 放行 seam block = 一条机检误报样本（纯函数·可测）。

    回灌 dashboard 事件流，给接缝阈值（SEAM_WARN/BLOCK·色距·跨集风格）攒校准数据：
    override 多的阈值段该放宽，从未 override 的 block 段说明阈值可信。
    """
    return {
        "qa": {
            "check": "seam_machine",
            "outcome": "human_override_false_positive",
            "seam_blocks": machine.get("seam_blocks", 0),
            "seam_warns": machine.get("seam_warns", 0),
            "intra_blocks": machine.get("intra_blocks", 0),
        },
        "meta": {"clip": clip, "note": "接缝/近景片内身份机检 block 被人工放行——误报样本，供阈值校准"},
    }


def record_qc_override(root: Path, episode: str, item: Dict[str, Any]) -> None:
    dashboard = _load_dashboard_module()
    payload = qc_override_payload(item.get("clip", "?"), item.get("qc_machine") or {})
    event = dashboard.make_event(episode, "video", "qa", source="n2d-video/video_runner.py", **payload)
    dashboard.append_events(str(root), [event])


def record_acceptance(root: Path, episode: str, item: Dict[str, Any], qc_clip: Optional[Dict[str, Any]]) -> None:
    dashboard = _load_dashboard_module()
    cost = None
    if item.get("credit_count") is not None:
        cost = {
            "amount": item.get("credit_count"),
            "currency": "credits",
            "unit": "credits",
            "provider": "dreamina",
        }
    duration = item.get("last_submit_elapsed_sec")
    meta = {"native_audio": "unknown"}
    if qc_clip and qc_clip.get("has_audio") is not None:
        meta["native_audio"] = "yes" if qc_clip.get("has_audio") else "no"
    machine = item.get("qc_machine") or {}
    if machine.get("seams_checked"):
        meta["seam_check"] = "block" if machine.get("seam_blocks") else ("warn" if machine.get("seam_warns") else "pass")
    if machine.get("intra_checked"):
        meta["intra_identity_check"] = "block" if machine.get("intra_blocks") else ("warn" if machine.get("intra_warns") else "pass")
    event = dashboard.make_event(
        episode,
        "video",
        "generation",
        source="n2d-video/video_runner.py",
        cost=cost,
        duration_sec=duration,
        generation={"asset": item.get("target_path") or item.get("target"), "status": "pass"},
        meta=meta,
    )
    dashboard.append_events(str(root), [event])
    dashboard.build(str(root), write=True)


def count_formal_clips(root: Path, episode: str) -> int:
    return len([p for p in formal_video_dir(root, episode).glob("Clip_*.mp4") if ".noaudio" not in p.name and "_noaudio" not in p.name])


def progress_denominator(root: Path, episode: str) -> int:
    if parse_progress is not None:
        try:
            header, rows = parse_progress(str(root))
            for row in rows:
                if row.get("_ep") == episode:
                    cell = str(row.get("视频") or "")
                    match = re.search(r"/\s*(\d+)", cell)
                    if match:
                        return int(match.group(1))
        except Exception:
            pass
    try:
        return len(split_clip_blocks(prompt_pack_path(root, episode).read_text(encoding="utf-8")))
    except Exception:
        return 0


def update_progress(root: Path, episode: str) -> None:
    total = progress_denominator(root, episode)
    if total <= 0:
        return
    count = count_formal_clips(root, episode)
    progress_py = SKILLS_DIR / "n2d" / "progress.py"
    subprocess.run([sys.executable, str(progress_py), "set", str(root), episode, "视频", f"{count}/{total}"], check=False)


def accept_clip(root: Path, manifest_file: Path, clip: str, *, no_record: bool = False, no_progress: bool = False,
                allow_qc_block: bool = False) -> Dict[str, Any]:
    manifest = load_json(manifest_file)
    episode = manifest["episode"]
    item = find_item(manifest, clip)
    target = Path(item.get("target_path") or formal_video_dir(root, episode) / item["target"])
    if not target.exists():
        raise FileNotFoundError(target)
    qc_range = f"{item['clip'].split('_')[1]}_{item['clip'].split('_')[1]}"
    qc = video_qc.run_qc(root, episode, [target], qc_range)
    qc_clip = qc["clips"][0] if qc.get("clips") else None
    machine = qc.get("machine_summary") or {}
    item["qc_machine"] = machine
    qc_blocks = int(machine.get("seam_blocks") or 0) + int(machine.get("intra_blocks") or 0)
    if qc_blocks and not allow_qc_block:
        reasons = []
        if machine.get("seam_blocks"):
            reasons.append(f"接缝机检 block×{machine['seam_blocks']}（尾帧没接上相邻镜首帧，出视频会跳切）")
        if machine.get("intra_blocks"):
            reasons.append(f"近景片内身份 block×{machine['intra_blocks']}（脸被表情带着重画，非双帧接力镜）")
        item["status"] = "qc_blocked"
        item["qc_json"] = qc.get("json_path")
        item["fail_reason"] = "；".join(reasons) + "。重出本镜或确认误报后 --allow-qc-block 强制验收"
        update_manifest(manifest_file, manifest)
        raise RuntimeError(f"{item['clip']} {item['fail_reason']}（详见 {qc.get('markdown_path')}）")
    overridden = bool(qc_blocks) and allow_qc_block
    item["status"] = "accepted"
    item["qc_overridden"] = overridden
    item["target_path"] = str(target)
    item["qc_json"] = qc.get("json_path")
    item["qc_markdown"] = qc.get("markdown_path")
    item["accepted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    update_manifest(manifest_file, manifest)
    if not no_record:
        if overridden:
            record_qc_override(root, episode, item)
        record_acceptance(root, episode, item, qc_clip)
    if not no_progress:
        update_progress(root, episode)
    return item


def run_batch_qc(root: Path, manifest_file: Path) -> Dict[str, Any]:
    manifest = load_json(manifest_file)
    episode = manifest["episode"]
    clips = []
    for item in manifest.get("items", []):
        target = Path(item.get("target_path") or formal_video_dir(root, episode) / item["target"])
        if target.exists():
            clips.append(target)
    if not clips:
        raise RuntimeError("no downloaded target clips in manifest")
    return video_qc.run_qc(root, episode, clips, manifest.get("batch_id") or manifest.get("batch", "batch").replace("-", "_"))


def status_summary(manifest: Dict[str, Any]) -> str:
    counts: Dict[str, int] = {}
    for item in manifest.get("items", []):
        counts[item.get("status", "unknown")] = counts.get(item.get("status", "unknown"), 0) + 1
    lines = [f"{manifest.get('episode')} {manifest.get('batch')} {counts}"]
    for item in manifest.get("items", []):
        sid = f" submit_id={item.get('submit_id')}" if item.get("submit_id") else ""
        lines.append(f"- {item.get('clip')} {item.get('status')}{sid} target={item.get('target')}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("root")
    p.add_argument("episode")
    p.add_argument("--range", required=True)
    p.add_argument("--backend", default="dreamina")
    p.add_argument("--resolution", default="720p")
    p.add_argument("--model-version", default="3.0")
    p.add_argument("--force", action="store_true")

    for name in ("submit", "query", "accept"):
        p = sub.add_parser(name)
        p.add_argument("root")
        p.add_argument("manifest")
        p.add_argument("--clip", required=True)
        if name == "submit":
            p.add_argument("--dry-run", action="store_true")
            p.add_argument("--skip-preflight", action="store_true",
                           help="skip default video_preflight gate before backend submission")
        if name == "query":
            p.add_argument("--no-download", action="store_true")
            p.add_argument("--force", action="store_true")
        if name == "accept":
            p.add_argument("--no-record", action="store_true")
            p.add_argument("--no-progress", action="store_true")
            p.add_argument("--allow-qc-block", action="store_true",
                           help="接缝机检 block 时仍强制验收（确认是误报/有意跳切再用）")

    p = sub.add_parser("qc")
    p.add_argument("root")
    p.add_argument("manifest")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("status")
    p.add_argument("manifest")

    ns = ap.parse_args(argv)
    if ns.cmd == "prepare":
        start, end = video_qc.parse_clip_range(ns.range)
        payload = prepare_manifest(
            Path(ns.root).expanduser().resolve(),
            ns.episode,
            start,
            end,
            backend=ns.backend,
            resolution=ns.resolution,
            model_version=ns.model_version,
            force=ns.force,
        )
        print(manifest_path(Path(ns.root).expanduser().resolve(), normalize_episode(ns.episode), start, end))
        print(status_summary(payload))
        return 0
    if ns.cmd == "status":
        print(status_summary(load_json(Path(ns.manifest))))
        return 0
    root = Path(ns.root).expanduser().resolve()
    manifest_file = Path(ns.manifest).expanduser().resolve()
    if ns.cmd == "submit":
        print(json.dumps(submit_clip(root, manifest_file, ns.clip, dry_run=ns.dry_run,
                                     skip_preflight=ns.skip_preflight), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if ns.cmd == "query":
        print(json.dumps(query_clip(root, manifest_file, ns.clip, download=not ns.no_download, force=ns.force), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if ns.cmd == "accept":
        print(json.dumps(accept_clip(root, manifest_file, ns.clip, no_record=ns.no_record, no_progress=ns.no_progress,
                                     allow_qc_block=ns.allow_qc_block), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if ns.cmd == "qc":
        payload = run_batch_qc(root, manifest_file)
        if ns.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(payload["markdown_path"])
        return 1 if (payload.get("machine_summary") or {}).get("seam_blocks") else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
