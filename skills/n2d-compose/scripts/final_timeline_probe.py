#!/usr/bin/env python3
"""Lightweight final-master timeline probe for n2d production evidence.

This script intentionally measures only what is locally available without heavy
AV analyzers: final MP4 duration and storyboard-derived segment/cut positions.
Brightness, loudness, silence-gap, SyncNet, and scene-embed metrics remain absent
unless a dedicated backend writes them elsewhere.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def as_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def clip_label(row: Mapping[str, Any], idx: int) -> str:
    raw = str(row.get("clip_id") or row.get("clip") or row.get("id") or row.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return raw or f"Clip_{idx:02d}"


def storyboard_segments(clips: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    t = 0.0
    for idx, clip in enumerate(clips, 1):
        dur = as_float(clip.get("duration") or clip.get("duration_sec") or clip.get("时长"))
        if dur is None or dur <= 0:
            continue
        start = t
        end = t + dur
        segments.append({
            "clip": clip_label(clip, idx),
            "expected_start_sec": round(start, 3),
            "expected_end_sec": round(end, 3),
            "expected_duration_sec": round(dur, 3),
            "verdict": "pass",
            "measurement_scope": "storyboard_expected_timeline",
        })
        t = end
    return segments


def cut_rows(segments: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for left, right in zip(segments, segments[1:]):
        t = as_float(left.get("expected_end_sec"))
        if t is None:
            continue
        rows.append({
            "cut": f"{left.get('clip')}->{right.get('clip')}",
            "timecode": round(t, 3),
            "verdict": "pass",
            "measurement_scope": "storyboard_expected_cut",
        })
    return rows


def ffprobe_duration(path: Path) -> Optional[float]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return as_float(proc.stdout.strip())


def find_final_master(root: Path, episode: str) -> Optional[Path]:
    base = root / "合成" / episode
    candidates = [
        base / f"成片_{episode}_zh.mp4",
        base / f"成片_{episode}.mp4",
        base / "成片.mp4",
    ]
    candidates.extend(sorted(base.glob("成片*.mp4")))
    for path in candidates:
        if path.is_file():
            return path
    return None


def build_report(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    storyboard = load_json(root / "脚本" / episode / "storyboard.json")
    clips = storyboard.get("clips") if isinstance(storyboard, Mapping) else []
    clips = [x for x in clips or [] if isinstance(x, Mapping)]
    segments = storyboard_segments(clips)
    cuts = cut_rows(segments)
    expected = segments[-1]["expected_end_sec"] if segments else None
    master = find_final_master(root, episode)
    actual = ffprobe_duration(master) if master else None
    tolerance = max(1.0, float(expected or 0.0) * 0.02) if expected is not None else 1.0
    findings: List[Dict[str, Any]] = []
    status = "pass"
    if master is None:
        status = "missing_final_master"
        findings.append({"severity": "warn", "message": "未找到成片 MP4，无法量最终时间线。"})
    elif actual is None:
        status = "duration_unavailable"
        findings.append({"severity": "warn", "message": "ffprobe 未能读取成片时长。"})
    elif expected is not None and abs(actual - float(expected)) > tolerance:
        status = "warn"
        findings.append({
            "severity": "warn",
            "message": f"成片时长 {actual:.3f}s 与 storyboard 预计 {float(expected):.3f}s 相差超过容差 {tolerance:.3f}s。",
            "actual_duration_sec": round(actual, 3),
            "expected_duration_sec": round(float(expected), 3),
        })
    return {
        "kind": "n2d_final_timeline_probe",
        "version": VERSION,
        "episode": episode,
        "generated_at": now_iso(),
        "status": status,
        "final_master": relpath(root, master) if master else "",
        "expected_duration_sec": round(float(expected), 3) if expected is not None else None,
        "actual_duration_sec": round(actual, 3) if actual is not None else None,
        "duration_tolerance_sec": round(tolerance, 3),
        "segments": segments,
        "cuts": cuts,
        "findings": findings,
        "notes": [
            "本探针仅记录最终成片时长与 storyboard 理论时间线；亮度/响度/静音缝需重型 AV 后端另写字段。",
        ],
    }


def write_report(root: Path, episode: str, payload: Mapping[str, Any]) -> str:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"final_timeline_probe_{episode}.json"
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return relpath(root, path)


def render_rough_cut_html(payload: Mapping[str, Any]) -> str:
    rows = []
    for seg in payload.get("segments") or []:
        if not isinstance(seg, Mapping):
            continue
        rows.append(
            "<tr>"
            f"<td>{seg.get('clip')}</td>"
            f"<td>{seg.get('expected_start_sec')}</td>"
            f"<td>{seg.get('expected_end_sec')}</td>"
            f"<td>{seg.get('expected_duration_sec')}</td>"
            f"<td>{seg.get('verdict')}</td>"
            "</tr>"
        )
    return """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rough Cut Preview</title>
<style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:24px;line-height:1.5}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px 8px;text-align:left}</style>
</head>
<body>
""" + f"""
<h1>{payload.get('episode')} Rough Cut Timeline</h1>
<p>final_master: {payload.get('final_master') or '-'}</p>
<p>duration: actual={payload.get('actual_duration_sec')} expected={payload.get('expected_duration_sec')}</p>
<table><thead><tr><th>Clip</th><th>Start</th><th>End</th><th>Duration</th><th>Verdict</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table>
</body></html>
"""


def write_timeline_outputs(root: Path, episode: str, payload: Dict[str, Any]) -> Dict[str, str]:
    work = root / "合成" / episode / "_work"
    work.mkdir(parents=True, exist_ok=True)
    timeline = {
        "kind": "n2d_rough_cut_timeline",
        "version": VERSION,
        "episode": episode,
        "generated_at": payload.get("generated_at") or now_iso(),
        "status": payload.get("status"),
        "final_master": payload.get("final_master") or "",
        "expected_duration_sec": payload.get("expected_duration_sec"),
        "actual_duration_sec": payload.get("actual_duration_sec"),
        "segments": payload.get("segments") or [],
        "cuts": payload.get("cuts") or [],
    }
    timeline_path = work / "timeline.json"
    tmp = timeline_path.with_name(f"{timeline_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(timeline, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, timeline_path)
    rough_html = root / "合成" / episode / "rough_cut_preview.html"
    tmp_html = rough_html.with_name(f"{rough_html.name}.tmp.{os.getpid()}")
    tmp_html.write_text(render_rough_cut_html(payload), encoding="utf-8")
    os.replace(tmp_html, rough_html)
    return {
        "timeline": relpath(root, timeline_path),
        "rough_cut_preview": relpath(root, rough_html),
    }


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="write lightweight final timeline probe")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    payload = build_report(root, ns.episode)
    if ns.write:
        payload["output"] = write_report(root, ns.episode, payload)
        payload["timeline_outputs"] = write_timeline_outputs(root, ns.episode, payload)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['episode']} final_timeline_probe: {payload['status']}")
        print(f"  final_master: {payload.get('final_master') or '-'}")
        print(f"  duration: actual={payload.get('actual_duration_sec')} expected={payload.get('expected_duration_sec')}")
    return 0 if payload.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
