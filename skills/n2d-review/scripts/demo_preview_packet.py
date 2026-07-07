#!/usr/bin/env python3
"""Build an internal demo preview packet for a finished n2d episode.

This is deliberately lighter than the formal review/release path: it packages
the final master, sampled frames, existing QA reports, and a human watch
checklist for personal demo / learning use. It never marks acceptance.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


KIND = "n2d_demo_preview_packet"
REPO_ROOT = Path(__file__).resolve().parents[3]
N2D_LIB = REPO_ROOT / "skills" / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))

try:
    from settings import get_setting  # type: ignore
except Exception:  # pragma: no cover - keep the packet usable outside the repo.
    get_setting = None  # type: ignore


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


def rel(root: Path, path: Optional[Path]) -> str:
    if path is None:
        return ""
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return str(path)


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def sha256(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def number(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def setting_value(root: Path, key: str, default: str = "") -> str:
    if get_setting is None:
        return default
    try:
        return str(get_setting(str(root), key, default))
    except Exception:
        return default


def find_final_master(root: Path, ep: str) -> Optional[Path]:
    exact = root / "合成" / ep / f"成片_{ep}_zh.mp4"
    if exact.exists():
        return exact
    candidates = sorted((root / "合成" / ep).glob(f"*{ep}*.mp4"))
    return candidates[0] if candidates else None


def ffprobe(path: Path) -> Dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return {"available": False, "error": "ffprobe not found"}
    except subprocess.TimeoutExpired:
        return {"available": False, "error": "ffprobe timeout"}
    if proc.returncode != 0:
        return {"available": False, "error": proc.stderr.strip() or "ffprobe failed"}
    data = json.loads(proc.stdout or "{}")
    data["available"] = True
    return data


def video_meta(root: Path, path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {"exists": False, "path": ""}
    probe = ffprobe(path)
    streams = probe.get("streams") if isinstance(probe, dict) else []
    video_stream = next((s for s in streams or [] if s.get("codec_type") == "video"), {})
    audio_streams = [s for s in streams or [] if s.get("codec_type") == "audio"]
    duration = number((probe.get("format") or {}).get("duration")) if probe.get("available") else None
    return {
        "exists": True,
        "path": rel(root, path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "duration_sec": round(duration, 3) if duration is not None else None,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "video_codec": video_stream.get("codec_name"),
        "audio_streams": len(audio_streams),
        "has_audio": bool(audio_streams),
        "ffprobe": {"available": probe.get("available", False), "error": probe.get("error", "")},
    }


def storyboard_data(root: Path, ep: str) -> Dict[str, Any]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    return data if isinstance(data, dict) else {}


def clip_duration(clip: Mapping[str, Any]) -> float:
    for key in ("duration_sec", "duration", "seconds", "时长"):
        value = number(clip.get(key))
        if value is not None and value > 0:
            return value
    timing = clip.get("timing")
    if isinstance(timing, Mapping):
        for key in ("duration_sec", "duration", "seconds"):
            value = number(timing.get(key))
            if value is not None and value > 0:
                return value
    return 0.0


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def storyboard_clips(root: Path, ep: str) -> Tuple[List[Dict[str, Any]], Optional[float]]:
    data = storyboard_data(root, ep)
    total = number(data.get("total_duration") or (data.get("pacing_allocation") or {}).get("total_duration_sec"))
    clips = data.get("clips") if isinstance(data.get("clips"), list) else []
    rows: List[Dict[str, Any]] = []
    start = 0.0
    for idx, clip in enumerate(clips or [], 1):
        if not isinstance(clip, Mapping):
            continue
        dur = clip_duration(clip)
        end = start + dur
        rows.append({
            "clip": clip_id(clip, idx),
            "duration_sec": round(dur, 3),
            "story_start_sec": round(start, 3),
            "story_mid_sec": round(start + dur / 2.0, 3),
            "story_end_sec": round(end, 3),
        })
        start = end
    if total is None and start > 0:
        total = start
    return rows, total


def _dedupe_points(points: Sequence[Dict[str, Any]], min_gap: float = 0.35) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for point in sorted(points, key=lambda p: float(p.get("time_sec") or 0.0)):
        t = float(point.get("time_sec") or 0.0)
        if rows and abs(t - float(rows[-1].get("time_sec") or 0.0)) < min_gap:
            continue
        rows.append(point)
    return rows


def sample_points_from_storyboard(
    clips: Sequence[Mapping[str, Any]],
    storyboard_total_sec: Optional[float] = None,
    master_duration_sec: Optional[float] = None,
    max_samples: int = 14,
) -> List[Dict[str, Any]]:
    """Pick opening, clip midpoints, and tail points scaled to the final master."""
    duration = master_duration_sec or storyboard_total_sec or 0.0
    scale = 1.0
    if storyboard_total_sec and master_duration_sec and storyboard_total_sec > 0:
        scale = master_duration_sec / storyboard_total_sec
    cap = max(0.0, duration - 0.2) if duration else None

    raw: List[Dict[str, Any]] = []
    raw.append({
        "label": "opening",
        "clip": "",
        "reason": "start hook",
        "source_time_sec": 0.8,
        "time_sec": 0.8,
    })
    for row in clips:
        mid = number(row.get("story_mid_sec"))
        if mid is None:
            continue
        raw.append({
            "label": f"{row.get('clip')}_mid",
            "clip": row.get("clip", ""),
            "reason": "clip midpoint",
            "source_time_sec": round(mid, 3),
            "time_sec": round(mid * scale, 3),
        })
    if duration:
        raw.append({
            "label": "tail",
            "clip": "",
            "reason": "ending hook",
            "source_time_sec": round((storyboard_total_sec or duration) - 0.6, 3),
            "time_sec": round(max(0.0, duration - 0.6), 3),
        })

    points: List[Dict[str, Any]] = []
    for point in raw:
        t = float(point.get("time_sec") or 0.0)
        if cap is not None:
            t = min(max(0.0, t), cap)
        else:
            t = max(0.0, t)
        item = dict(point)
        item["time_sec"] = round(t, 3)
        if abs(scale - 1.0) > 0.001:
            item["storyboard_to_master_scale"] = round(scale, 6)
        points.append(item)

    points = _dedupe_points(points)
    if len(points) <= max_samples:
        return points

    first = points[:1]
    last = points[-1:]
    middle = points[1:-1]
    keep = max_samples - len(first) - len(last)
    if keep <= 0:
        return (first + last)[:max_samples]
    if keep >= len(middle):
        return first + middle + last
    selected = []
    for i in range(keep):
        pos = round(i * (len(middle) - 1) / max(1, keep - 1))
        selected.append(middle[pos])
    return first + selected + last


def source_report_summary(root: Path, ep: str) -> Dict[str, Any]:
    prod = root / "生产数据"
    release = load_json(prod / f"release_verdict_{ep}.json")
    score = load_json(prod / f"score_{ep}.json")
    final_probe = load_json(prod / f"final_timeline_probe_{ep}.json")
    review_ui = load_json(prod / f"review_ui_{ep}.json")
    gate_files = sorted(prod.glob(f"gate_findings_*_{ep}.json"))
    gates = []
    for path in gate_files:
        data = load_json(path)
        summary = data.get("summary") if isinstance(data, dict) else None
        counts = data.get("counts") if isinstance(data, dict) else None
        gates.append({"path": rel(root, path), "summary": summary or counts or {}})
    return {
        "final_timeline_probe": {
            "path": f"生产数据/final_timeline_probe_{ep}.json",
            "status": final_probe.get("status") if isinstance(final_probe, dict) else "missing",
            "actual_duration_sec": final_probe.get("actual_duration_sec") if isinstance(final_probe, dict) else None,
            "findings": len(final_probe.get("findings") or []) if isinstance(final_probe, dict) else None,
        },
        "release_verdict": {
            "path": f"生产数据/release_verdict_{ep}.json",
            "status": release.get("status") if isinstance(release, dict) else "missing",
            "profile": release.get("profile") if isinstance(release, dict) else None,
            "summary": release.get("summary") if isinstance(release, dict) else None,
            "blocking_reasons": len(release.get("blocking_reasons") or []) if isinstance(release, dict) else None,
        },
        "score": {
            "path": f"生产数据/score_{ep}.json",
            "status": score.get("status") if isinstance(score, dict) else "missing",
            "total_score": score.get("total_score") if isinstance(score, dict) else None,
            "threshold": score.get("threshold") if isinstance(score, dict) else None,
        },
        "review_ui": {
            "path": f"生产数据/review_ui_{ep}.json",
            "score_status": ((review_ui.get("score") or {}).get("status")) if isinstance(review_ui, dict) else "missing",
            "global_flags": len(review_ui.get("global_flags") or []) if isinstance(review_ui, dict) else None,
            "clips": len(review_ui.get("clips") or []) if isinstance(review_ui, dict) else None,
        },
        "gates": gates,
    }


def compliance_summary(root: Path) -> Dict[str, Any]:
    data = load_json(root / "合规" / "compliance_manifest.json")
    if not isinstance(data, dict):
        return {"available": False}
    intended = data.get("intended_use") if isinstance(data.get("intended_use"), Mapping) else {}
    return {
        "available": True,
        "distribution_intent": data.get("distribution_intent"),
        "intended_use": {
            "purpose": intended.get("purpose"),
            "public_release": intended.get("public_release"),
            "paid_distribution": intended.get("paid_distribution"),
        },
        "ai_labeling": data.get("ai_labeling") if isinstance(data.get("ai_labeling"), Mapping) else {},
    }


def packet_status(asset: Mapping[str, Any], settings: Mapping[str, Any], compliance: Mapping[str, Any]) -> str:
    if not asset.get("exists"):
        return "needs_final_master"
    use = str(settings.get("合规用途") or "").lower()
    strictness = str(settings.get("一致性严格度") or "").lower()
    intent = str(compliance.get("distribution_intent") or "").lower()
    public_release = bool((compliance.get("intended_use") or {}).get("public_release"))
    paid = bool((compliance.get("intended_use") or {}).get("paid_distribution"))
    if use == "internal_only" and strictness in {"demo", "宽松"} and intent in {"internal_only", ""} and not public_release and not paid:
        return "ready_for_human_demo_preview"
    return "settings_need_demo_confirmation"


def extract_frames(master: Path, out_dir: Path, samples: Sequence[Mapping[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return [], ["ffmpeg not found; frames were not extracted"]
    rows: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for idx, sample in enumerate(samples, 1):
        time_sec = float(sample.get("time_sec") or 0.0)
        safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(sample.get("label") or f"sample_{idx:02d}")).strip("_")
        path = out_dir / f"{idx:02d}_{safe_label}_{time_sec:06.2f}s.jpg"
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{time_sec:.3f}",
            "-i",
            str(master),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            "-y",
            str(path),
        ]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=60)
        if proc.returncode == 0 and path.exists():
            rows.append({
                "sample": sample.get("label"),
                "time_sec": round(time_sec, 3),
                "path": str(path),
                "bytes": path.stat().st_size,
            })
        else:
            warnings.append(f"frame extract failed at {time_sec:.3f}s: {proc.stderr.strip() or proc.returncode}")
    return rows, warnings


def make_contact_sheet(frames: Sequence[Mapping[str, Any]], samples: Sequence[Mapping[str, Any]], out_path: Path) -> Tuple[Optional[Path], Optional[str]]:
    if not frames:
        return None, "no frames available for contact sheet"
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None, "Pillow not available; contact sheet skipped"

    thumbs = []
    labels = []
    sample_by_label = {str(s.get("label")): s for s in samples}
    for frame in frames:
        path = Path(str(frame.get("path") or ""))
        if not path.exists():
            continue
        img = Image.open(path).convert("RGB")
        img.thumbnail((210, 360))
        canvas = Image.new("RGB", (220, 410), "white")
        x = (220 - img.width) // 2
        canvas.paste(img, (x, 8))
        sample = sample_by_label.get(str(frame.get("sample"))) or {}
        label = f"{frame.get('sample') or ''} @ {frame.get('time_sec')}s"
        if sample.get("clip"):
            label = f"{sample.get('clip')} @ {frame.get('time_sec')}s"
        labels.append(label)
        thumbs.append(canvas)

    if not thumbs:
        return None, "no readable frames for contact sheet"

    cols = min(4, len(thumbs))
    rows = int(math.ceil(len(thumbs) / cols))
    sheet = Image.new("RGB", (cols * 220, rows * 410), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, thumb in enumerate(thumbs):
        x = (idx % cols) * 220
        y = (idx // cols) * 410
        sheet.paste(thumb, (x, y))
        draw.text((x + 8, y + 372), labels[idx][:34], fill=(0, 0, 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=90)
    return out_path, None


def human_checklist() -> List[Dict[str, str]]:
    return [
        {"id": "full_watch", "check": "完整观看最终母版，不跳看，记录影响理解或观感的 timecode。"},
        {"id": "opening_hook", "check": "前 15 秒能否看懂冲突、身份悬念和继续看的理由。"},
        {"id": "voice_clarity", "check": "旁白/对白是否清楚；是否有双人声、爆音、突然变声或明显环境噪声。"},
        {"id": "subtitle_readability", "check": "字幕不挡脸、不挡关键动作，节奏上来得及读。"},
        {"id": "identity_break", "check": "主角、核心妖魔、飞鹰门人是否出现一眼可见的换脸/换装/形体跳变。"},
        {"id": "frame_face_drift", "check": "发现近景脸不像同一角色时，记录 timecode，并跑 video_face_drift_watch.py 生成密集抽帧拼版；不要只依赖逐 Clip 中点抽样。"},
        {"id": "action_readability", "check": "Clip06/Clip10 等动作爽点是否能看清出手、命中、反馈。"},
        {"id": "seam_flow", "check": "相邻 clip 接缝是否突兀闪切，时间/空间关系是否能顺着看。"},
        {"id": "ending_hook", "check": "结尾是否留出继续看第2集的疑问或爽点承诺。"},
    ]


def production_debt_notes() -> List[str]:
    return [
        "当前包按 internal_only / demo 学习用途生成，不要求公开发布或付费投放级通过。",
        "若转 production / 公开发布 / 付费投放，再补 DINOv2+SyncNet、scene_embed DINOv2、resident_presence OWLv2、VLM video judge。",
        "若转公开发布，再补显式 AI 标签、目标平台审核/备案/本地化合规，并重跑 gate、score、ledger、review-ui、release_verdict。",
        "本包不是 n2d-review 正式验收，不回写验收通过。",
    ]


def build_packet(root: Path, ep: str, max_samples: int = 14) -> Dict[str, Any]:
    ep = ep_label(ep)
    master = find_final_master(root, ep)
    asset = video_meta(root, master)
    clips, storyboard_total = storyboard_clips(root, ep)
    master_duration = number(asset.get("duration_sec"))
    samples = sample_points_from_storyboard(clips, storyboard_total, master_duration, max_samples=max_samples)
    settings = {
        "合规用途": setting_value(root, "合规用途", "internal_only"),
        "一致性严格度": setting_value(root, "一致性严格度", "demo"),
        "AI显式角标": setting_value(root, "AI显式角标", "仅元数据"),
    }
    compliance = compliance_summary(root)
    status = packet_status(asset, settings, compliance)
    return {
        "kind": KIND,
        "version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "episode": ep,
        "root": str(root),
        "status": status,
        "scope": {
            "preview_scope": "personal_demo_learning",
            "public_release": False,
            "formal_acceptance": False,
            "not_formal_acceptance": True,
            "manual_watch_required": True,
        },
        "settings": settings,
        "compliance": compliance,
        "asset": asset,
        "storyboard": {
            "clips": len(clips),
            "storyboard_total_sec": storyboard_total,
            "storyboard_to_master_scale": round(master_duration / storyboard_total, 6) if storyboard_total and master_duration else None,
        },
        "sample_points": samples,
        "source_reports": source_report_summary(root, ep),
        "checklist": human_checklist(),
        "production_debt_notes": production_debt_notes(),
        "artifacts": {},
        "warnings": [],
    }


def render_markdown(packet: Mapping[str, Any]) -> str:
    asset = packet.get("asset") or {}
    reports = packet.get("source_reports") or {}
    artifacts = packet.get("artifacts") or {}
    release = reports.get("release_verdict") or {}
    score = reports.get("score") or {}
    lines = [
        "# 第1集 Demo 预览包" if packet.get("episode") == "第1集" else f"# {packet.get('episode')} Demo 预览包",
        "",
        f"- 状态：{packet.get('status')}",
        "- 用途：自用 demo / 学习预览；不是正式验收，不回写验收通过。",
        f"- 最终母版：`{asset.get('path') or 'missing'}`",
        f"- 时长/画幅：{asset.get('duration_sec')}s / {asset.get('width')}x{asset.get('height')}",
        f"- SHA256：`{asset.get('sha256') or ''}`",
        f"- 抽帧目录：`{artifacts.get('frames_dir') or ''}`",
        f"- contact sheet：`{artifacts.get('contact_sheet') or ''}`",
        "",
        "## 现有账本只作参考",
        "",
        f"- release_verdict：{release.get('status')} / profile={release.get('profile')} / summary={json.dumps(release.get('summary') or {}, ensure_ascii=False)}",
        f"- score：{score.get('total_score')}/{score.get('threshold')} / {score.get('status')}",
        f"- final_timeline_probe：{(reports.get('final_timeline_probe') or {}).get('status')}",
        "",
        "## 人工观看清单",
        "",
    ]
    for row in packet.get("checklist") or []:
        lines.append(f"- [ ] {row.get('check')}")
    lines.extend(["", "## 抽帧点", ""])
    for sample in packet.get("sample_points") or []:
        clip = f" / {sample.get('clip')}" if sample.get("clip") else ""
        lines.append(f"- {sample.get('label')}{clip}: {sample.get('time_sec')}s ({sample.get('reason')})")
    lines.extend(["", "## 生产/公开发布债务", ""])
    for note in packet.get("production_debt_notes") or []:
        lines.append(f"- {note}")
    warnings = packet.get("warnings") or []
    if warnings:
        lines.extend(["", "## 生成告警", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, packet: Dict[str, Any]) -> Tuple[Path, Path]:
    prod = root / "生产数据"
    json_path = prod / f"demo_preview_{ep}.json"
    md_path = prod / f"demo_preview_{ep}.md"
    write_atomic(json_path, json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
    write_atomic(md_path, render_markdown(packet))
    return json_path, md_path


def build_and_write(root: Path, ep: str, max_samples: int = 14, write_frames: bool = False) -> Dict[str, Any]:
    ep = ep_label(ep)
    packet = build_packet(root, ep, max_samples=max_samples)
    artifacts: Dict[str, Any] = {}
    warnings: List[str] = list(packet.get("warnings") or [])
    master_path = root / str((packet.get("asset") or {}).get("path") or "")
    if write_frames and master_path.exists():
        frames_dir = root / "生产数据" / "demo_preview_frames" / ep
        frames, frame_warnings = extract_frames(master_path, frames_dir, packet.get("sample_points") or [])
        artifacts["frames_dir"] = rel(root, frames_dir)
        artifacts["frames"] = [{**row, "path": rel(root, Path(str(row.get("path"))))} for row in frames]
        warnings.extend(frame_warnings)
        sheet_path, sheet_warning = make_contact_sheet(
            frames,
            packet.get("sample_points") or [],
            root / "生产数据" / f"demo_preview_contact_sheet_{ep}.jpg",
        )
        if sheet_path:
            artifacts["contact_sheet"] = rel(root, sheet_path)
        if sheet_warning:
            warnings.append(sheet_warning)
    elif write_frames:
        warnings.append("final master missing; frames were not extracted")
    packet["artifacts"] = artifacts
    packet["warnings"] = warnings
    json_path, md_path = write_outputs(root, ep, packet)
    packet["output"] = {"json": rel(root, json_path), "markdown": rel(root, md_path)}
    write_outputs(root, ep, packet)
    return packet


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build an internal demo preview packet for n2d.")
    parser.add_argument("work_root")
    parser.add_argument("episode")
    parser.add_argument("--write", action="store_true", help="extract frames and write JSON/Markdown outputs")
    parser.add_argument("--max-samples", type=int, default=14)
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args(argv)

    root = Path(args.work_root).resolve()
    ep = ep_label(args.episode)
    packet = build_and_write(root, ep, max_samples=args.max_samples, write_frames=args.write)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        out = packet.get("output") or {}
        print(f"{packet['status']}: {out.get('json', '')}")
    return 0 if packet.get("status") != "needs_final_master" else 1


if __name__ == "__main__":
    raise SystemExit(main())
