#!/usr/bin/env python3
"""Build a dense frame watch packet for final-video face drift review.

This is a lightweight companion to `temporal_consistency.py`: it does not need
InsightFace/DINO/VLM. It extracts dense frames from a final master, maps them to
storyboard clip ranges, and writes a contact sheet for human identity review.
Use it when a viewer reports "this close-up face is not the character" or when
CU/MCU/reaction shots were promoted from small/distant anchor faces.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


KIND = "n2d_video_face_drift_watch"


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def number(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def rel(root: Path, path: Path) -> str:
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return str(path)


def find_final_master(root: Path, ep: str) -> Optional[Path]:
    exact = root / "合成" / ep / f"成片_{ep}_zh.mp4"
    if exact.exists():
        return exact
    candidates = sorted((root / "合成" / ep).glob(f"*{ep}*.mp4"))
    return candidates[0] if candidates else None


def resolve_video_path(root: Path, raw: Optional[str]) -> Optional[Path]:
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_absolute() else root / path


def clip_id_from_video(path: Path, clip: Optional[str]) -> str:
    if clip:
        return str(clip)
    m = re.search(r"Clip[_-]?(\d+)", path.name, re.IGNORECASE)
    return f"Clip_{int(m.group(1)):02d}" if m else path.stem


def single_video_segments(path: Path, duration: Optional[float], clip: Optional[str]) -> List[Dict[str, Any]]:
    end = float(duration or 0.0)
    return [{
        "clip": clip_id_from_video(path, clip),
        "start_sec": 0.0,
        "end_sec": round(end, 3),
        "duration_sec": round(end, 3),
        "source": "single_video",
    }]


def storyboard_segments(root: Path, ep: str) -> List[Dict[str, Any]]:
    probe = load_json(root / "生产数据" / f"final_timeline_probe_{ep}.json")
    if isinstance(probe, Mapping) and isinstance(probe.get("segments"), list):
        rows = []
        for row in probe.get("segments") or []:
            if not isinstance(row, Mapping):
                continue
            start = number(row.get("expected_start_sec"))
            end = number(row.get("expected_end_sec"))
            if start is None or end is None:
                continue
            rows.append({
                "clip": str(row.get("clip") or ""),
                "start_sec": round(start, 3),
                "end_sec": round(end, 3),
                "duration_sec": round(end - start, 3),
                "source": "final_timeline_probe",
            })
        if rows:
            return rows

    sb = load_json(root / "脚本" / ep / "storyboard.json")
    clips = sb.get("clips") if isinstance(sb, Mapping) and isinstance(sb.get("clips"), list) else []
    rows: List[Dict[str, Any]] = []
    start = 0.0
    for idx, clip in enumerate(clips or [], 1):
        if not isinstance(clip, Mapping):
            continue
        dur = number(clip.get("duration") or clip.get("duration_sec")) or 0.0
        end = start + dur
        rows.append({
            "clip": f"Clip_{idx:02d}",
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "duration_sec": round(dur, 3),
            "source": "storyboard",
        })
        start = end
    return rows


def clip_for_time(segments: Sequence[Mapping[str, Any]], time_sec: float) -> str:
    for row in segments:
        start = float(row.get("start_sec") or 0.0)
        end = float(row.get("end_sec") or 0.0)
        if start <= time_sec < end:
            return str(row.get("clip") or "")
    if segments and abs(time_sec - float(segments[-1].get("end_sec") or 0.0)) < 0.01:
        return str(segments[-1].get("clip") or "")
    return ""


def sample_times(start: float, end: float, interval: float, max_frames: int) -> List[float]:
    if end < start:
        start, end = end, start
    interval = max(0.1, interval)
    times: List[float] = []
    t = max(0.0, start)
    while t <= end + 1e-6:
        times.append(round(t, 3))
        t += interval
    if max_frames > 0 and len(times) > max_frames:
        keep: List[float] = []
        for i in range(max_frames):
            pos = round(i * (len(times) - 1) / max(1, max_frames - 1))
            keep.append(times[pos])
        times = keep
    return times


def ffprobe_duration(path: Path) -> Optional[float]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return number(proc.stdout.strip()) if proc.returncode == 0 else None


def extract_frames(root: Path, master: Path, out_dir: Path, times: Sequence[float],
                   segments: Sequence[Mapping[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return [], ["ffmpeg not found; dense frames were not extracted"]
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for idx, t in enumerate(times, 1):
        clip = clip_for_time(segments, t)
        safe_clip = clip or "unknown"
        path = out_dir / f"{idx:03d}_{safe_clip}_{t:07.3f}s.jpg"
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}",
            "-i", str(master), "-frames:v", "1", "-q:v", "2", "-y", str(path),
        ]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=60)
        if proc.returncode == 0 and path.exists():
            rows.append({
                "time_sec": round(t, 3),
                "clip": clip,
                "path": rel(root, path),
                "bytes": path.stat().st_size,
            })
        else:
            warnings.append(f"extract failed at {t:.3f}s: {proc.stderr.strip() or proc.returncode}")
    return rows, warnings


def make_contact_sheet(root: Path, frames: Sequence[Mapping[str, Any]], out_path: Path) -> Tuple[str, Optional[str]]:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return "", "Pillow not available; contact sheet skipped"
    thumbs = []
    for row in frames:
        path = root / str(row.get("path") or "")
        if not path.exists():
            continue
        img = Image.open(path).convert("RGB")
        img.thumbnail((220, 390))
        canvas = Image.new("RGB", (230, 430), "white")
        canvas.paste(img, ((230 - img.width) // 2, 6))
        label = f"{row.get('clip') or '?'} @ {row.get('time_sec')}s"
        ImageDraw.Draw(canvas).text((8, 402), label[:34], fill=(0, 0, 0))
        thumbs.append(canvas)
    if not thumbs:
        return "", "no readable frames for contact sheet"
    cols = min(5, len(thumbs))
    rows_n = int(math.ceil(len(thumbs) / cols))
    sheet = Image.new("RGB", (cols * 230, rows_n * 430), (238, 238, 238))
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * 230, (i // cols) * 430))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=90)
    return rel(root, out_path), None


def render_markdown(packet: Mapping[str, Any]) -> str:
    lines = [
        f"# {packet.get('episode')} 视频帧级脸漂观察包",
        "",
        f"- 状态：{packet.get('status')}",
        f"- 母版：`{packet.get('master')}`",
        f"- 时间范围：{packet.get('start_sec')}s - {packet.get('end_sec')}s；间隔 {packet.get('interval_sec')}s",
        f"- contact sheet：`{packet.get('contact_sheet') or ''}`",
        "",
        "## 判定口径",
        "",
        "- 这不是正式验收，只是把最终 MP4 的近景脸漂做成人审证据。",
        "- 任一主角/核心角色清晰近脸看起来不是同一角色，按脸漂 block 记录，不能签收成通过。",
        "- 修法优先回 `n2d-video` 废料重跑；若是从小脸/远脸升格成近脸，先回 `n2d-image` 补同源近景锚帧/表情参考并过 full image_qc。",
        "",
        "## 抽帧",
        "",
    ]
    for row in packet.get("frames") or []:
        lines.append(f"- {row.get('time_sec')}s / {row.get('clip') or '?'} / `{row.get('path')}`")
    warnings = packet.get("warnings") or []
    if warnings:
        lines += ["", "## Warnings", ""]
        lines += [f"- {w}" for w in warnings]
    return "\n".join(lines) + "\n"


def build_packet(root: Path, ep: str, start: Optional[float], end: Optional[float],
                 interval: float, max_frames: int, video: Optional[str] = None,
                 clip: Optional[str] = None) -> Dict[str, Any]:
    ep = ep_label(ep)
    explicit_video = resolve_video_path(root, video)
    master = explicit_video or find_final_master(root, ep)
    if master is None:
        return {
            "kind": KIND,
            "version": 1,
            "episode": ep,
            "status": "missing_final_master",
            "master": "",
            "warnings": ["final master not found"],
        }
    if not master.is_file():
        return {
            "kind": KIND,
            "version": 1,
            "episode": ep,
            "status": "missing_video_source",
            "master": rel(root, master),
            "warnings": [f"video source not found: {master}"],
        }
    duration = ffprobe_duration(master)
    start_sec = 0.0 if start is None else max(0.0, start)
    end_sec = (duration or start_sec) if end is None else max(0.0, end)
    if duration is not None:
        end_sec = min(end_sec, max(0.0, duration - 0.05))
    segments = single_video_segments(master, duration, clip) if explicit_video else storyboard_segments(root, ep)
    times = sample_times(start_sec, end_sec, interval, max_frames)
    source_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", master.stem).strip("_")[:80] or "video"
    packet_id = f"{source_id}_{start_sec:.2f}_{end_sec:.2f}s" if explicit_video else f"{start_sec:.2f}_{end_sec:.2f}s"
    frames_dir = root / "生产数据" / "video_face_drift_watch" / ep / packet_id
    frames, warnings = extract_frames(root, master, frames_dir, times, segments)
    contact_sheet, sheet_warning = make_contact_sheet(
        root,
        frames,
        root / "生产数据" / f"video_face_drift_watch_{ep}_{packet_id}.jpg",
    )
    if sheet_warning:
        warnings.append(sheet_warning)
    return {
        "kind": KIND,
        "version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "episode": ep,
        "status": "ready_for_human_frame_identity_review" if frames else "no_frames_extracted",
        "master": rel(root, master),
        "source_kind": "single_video" if explicit_video else "final_master",
        "source_clip": (clip or "") if explicit_video else "",
        "packet_id": packet_id,
        "master_duration_sec": round(duration, 3) if duration is not None else None,
        "start_sec": round(start_sec, 3),
        "end_sec": round(end_sec, 3),
        "interval_sec": interval,
        "segments_source": segments[0].get("source") if segments else "missing",
        "segments": segments,
        "frames": frames,
        "frames_dir": rel(root, frames_dir),
        "contact_sheet": contact_sheet,
        "policy": {
            "clear_wrong_closeup_face": "block",
            "missing_identity_backend": "use_human_dense_frame_review_or_full_temporal_consistency",
            "return_to_stage": "video_or_image_then_compose",
        },
        "warnings": warnings,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build dense final-video frame packet for human face-drift review")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--start", type=float, default=None)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--interval", type=float, default=0.5)
    ap.add_argument("--max-frames", type=int, default=120)
    ap.add_argument("--video", default=None, help="optional single clip MP4 to inspect before final compose")
    ap.add_argument("--clip", default=None, help="clip id for --video packets, e.g. Clip_03")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ep_label(ns.episode)
    packet = build_packet(root, ep, ns.start, ns.end, ns.interval, ns.max_frames, ns.video, ns.clip)
    if ns.write:
        suffix = str(packet.get("packet_id") or f"{packet.get('start_sec')}_{packet.get('end_sec')}s").replace(".", "_")
        json_path = root / "生产数据" / f"video_face_drift_watch_{ep}_{suffix}.json"
        md_path = root / "生产数据" / f"video_face_drift_watch_{ep}_{suffix}.md"
        packet["json_path"] = rel(root, json_path)
        packet["markdown_path"] = rel(root, md_path)
        write_atomic(json_path, json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
        write_atomic(md_path, render_markdown(packet))
    if ns.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print(f"{packet.get('status')}: {packet.get('contact_sheet') or ''}")
    return 0 if packet.get("status") != "missing_final_master" else 1


if __name__ == "__main__":
    raise SystemExit(main())
