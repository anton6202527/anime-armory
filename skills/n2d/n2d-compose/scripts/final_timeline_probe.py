#!/usr/bin/env python3
"""Verify the actual ordered master timeline against its bound render recipe.

Storyboard rows remain expectations only.  A ``pass`` requires the current
MediaArtifactReceipt, the exact ordered source SHA/in-out recipe, decoded sample
frame hashes and measured cut-boundary frames from the canonical master.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

N2D_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
from editorial_timeline import build_editorial_timeline, write_editorial_timeline  # noqa: E402

COMPOSE_DIR = Path(__file__).resolve().parents[1]
if str(COMPOSE_DIR) not in sys.path:
    sys.path.insert(0, str(COMPOSE_DIR))
import media_artifact  # noqa: E402


VERSION = 2


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
            "verdict": "expected_unmeasured",
            "measurement_scope": "storyboard_expectation_only",
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
            "verdict": "expected_unmeasured",
            "measurement_scope": "storyboard_expectation_only",
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


def _frame_sample(path: Path, at_sec: float) -> Optional[Dict[str, Any]]:
    """Decode one frame to a tiny grayscale plane and return a real frame hash."""
    if not path.is_file():
        return None
    cmd = [
        "ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(0.0, at_sec):.6f}",
        "-i", str(path), "-frames:v", "1", "-vf", "scale=32:18,format=gray",
        "-f", "rawvideo", "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=90, check=False)
    except Exception:
        return None
    if proc.returncode != 0 or len(proc.stdout) != 32 * 18:
        return None
    pixels = proc.stdout
    return {
        "sha256": hashlib.sha256(pixels).hexdigest(),
        "pixels": pixels,
        "time_sec": round(max(0.0, at_sec), 6),
    }


def _frame_distance(left: Mapping[str, Any], right: Mapping[str, Any]) -> Optional[float]:
    a, b = left.get("pixels"), right.get("pixels")
    if not isinstance(a, bytes) or not isinstance(b, bytes) or len(a) != len(b) or not a:
        return None
    return sum(abs(x - y) for x, y in zip(a, b)) / (255.0 * len(a))


def _public_sample(sample: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not sample:
        return {"available": False, "framehash_sha256": "", "time_sec": None}
    return {
        "available": True,
        "framehash_sha256": str(sample.get("sha256") or ""),
        "time_sec": sample.get("time_sec"),
    }


def _stored_sample(payload: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, Mapping) or payload.get("available") is not True:
        return None
    try:
        pixels = base64.b64decode(str(payload.get("gray32x18_base64") or ""), validate=True)
    except Exception:
        return None
    if len(pixels) != 32 * 18 or hashlib.sha256(pixels).hexdigest() != str(payload.get("framehash_sha256") or ""):
        return None
    return {"pixels": pixels, "sha256": payload.get("framehash_sha256"), "time_sec": payload.get("time_sec")}


def _recipe_path(root: Path, episode: str) -> Path:
    return root / "生产数据" / "timelines" / episode / "render_recipe.json"


def _actual_segments(root: Path, master: Path, recipe: Mapping[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    segments: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    tolerance = 0.28  # burned subtitles/labels may alter a minority of the frame
    for idx, source in enumerate(recipe.get("ordered_sources") or [], 1):
        if not isinstance(source, Mapping):
            continue
        source_path = root / str(source.get("normalized") or source.get("source") or "")
        expected_sha = str(source.get("normalized_sha256") or source.get("source_sha256") or "")
        actual_sha = media_artifact.sha256_file(source_path) if source_path.is_file() else ""
        timeline_in = as_float(source.get("timeline_in_sec"))
        timeline_out = as_float(source.get("timeline_out_sec"))
        duration = as_float(source.get("edit_duration_sec") or source.get("normalized_duration_sec"))
        if timeline_in is None:
            timeline_in = segments[-1]["actual_end_sec"] if segments else 0.0
        if timeline_out is None and duration is not None:
            timeline_out = timeline_in + duration
        duration = duration or ((timeline_out or 0.0) - timeline_in)
        midpoint = max(0.04, min(max(0.04, duration - 0.04), duration / 2.0))
        source_sample = _stored_sample(source.get("normalized_midpoint_sample")) or _frame_sample(source_path, midpoint)
        master_sample = _frame_sample(master, timeline_in + midpoint)
        distance = _frame_distance(source_sample or {}, master_sample or {})
        # The tiny decoded source sample is embedded in the hash-bound recipe so
        # later cache cleanup does not invalidate a valid master.  If the cache
        # still exists, its whole-file SHA must also remain current.
        hash_ok = bool(expected_sha and source_sample and (not source_path.is_file() or actual_sha == expected_sha))
        sample_ok = distance is not None and distance <= tolerance
        status = "pass" if hash_ok and sample_ok and timeline_out is not None and timeline_out > timeline_in else "block"
        row = {
            "clip": str(source.get("clip") or f"Clip_{idx:02d}"),
            "order": idx,
            "actual_start_sec": round(timeline_in, 6),
            "actual_end_sec": round(float(timeline_out or timeline_in), 6),
            "actual_duration_sec": round(duration, 6),
            "source_in_sec": source.get("source_in_sec"),
            "source_out_sec": source.get("source_out_sec"),
            "source": str(source.get("source") or ""),
            "source_sha256": str(source.get("source_sha256") or ""),
            "normalized": str(source.get("normalized") or ""),
            "normalized_sha256": expected_sha,
            "current_normalized_sha256": actual_sha,
            "source_hash_current": hash_ok,
            "source_sample": _public_sample(source_sample),
            "master_sample": _public_sample(master_sample),
            "sample_distance": round(distance, 6) if distance is not None else None,
            "sample_distance_max": tolerance,
            "verdict": status,
            "measurement_scope": "render_recipe_sha_and_decoded_frame_sample",
        }
        segments.append(row)
        if status != "pass":
            findings.append({
                "severity": "block", "code": "actual_segment_unverified",
                "clip": row["clip"],
                "message": f"{row['clip']} ordered source SHA/frame sample does not match the rendered master",
            })
    return segments, findings


def _actual_cuts(master: Path, segments: Sequence[Mapping[str, Any]], fps: float) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    delta = max(1.0 / max(fps, 1.0), 0.02)
    for left, right in zip(segments, segments[1:]):
        at = as_float(left.get("actual_end_sec"))
        if at is None:
            continue
        before = _frame_sample(master, max(0.0, at - delta))
        after = _frame_sample(master, at + delta)
        status = "pass" if before and after else "block"
        row = {
            "cut": f"{left.get('clip')}->{right.get('clip')}",
            "timecode": round(at, 6),
            "before": _public_sample(before),
            "after": _public_sample(after),
            "verdict": status,
            "measurement_scope": "decoded_master_boundary_framehash",
        }
        rows.append(row)
        if status != "pass":
            findings.append({"severity": "block", "code": "cut_boundary_unreadable", "message": f"cannot decode both sides of {row['cut']}"})
    return rows, findings


def build_report(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    storyboard = load_json(root / "脚本" / episode / "storyboard.json")
    clips = storyboard.get("clips") if isinstance(storyboard, Mapping) else []
    clips = [x for x in clips or [] if isinstance(x, Mapping)]
    expected_segments = storyboard_segments(clips)
    expected_cuts = cut_rows(expected_segments)
    storyboard_expected = expected_segments[-1]["expected_end_sec"] if expected_segments else None
    receipt_check = media_artifact.current_receipt(root, episode)
    receipt = receipt_check.get("receipt") if isinstance(receipt_check.get("receipt"), Mapping) else {}
    artifact_rel = str((receipt.get("artifact") or {}).get("path") or "")
    master = (root / artifact_rel) if artifact_rel else find_final_master(root, episode)
    actual = ffprobe_duration(master) if master else None
    findings: List[Dict[str, Any]] = []
    status = "pass"
    recipe_path = _recipe_path(root, episode)
    recipe = load_json(recipe_path) or {}
    expected = as_float(recipe.get("duration_sec"))
    tolerance = max(0.25, float(expected or 0.0) * 0.005) if expected is not None else 0.25
    segments: List[Dict[str, Any]] = []
    cuts: List[Dict[str, Any]] = []
    if receipt_check.get("status") != "pass":
        status = "block"
        findings.append({"severity": "block", "code": "media_receipt_not_current", "message": "; ".join(receipt_check.get("issues") or ["current MediaArtifactReceipt is missing"] )})
    if master is None:
        status = "block"
        findings.append({"severity": "block", "message": "未找到 canonical 成片，无法验证实际时间线。"})
    elif actual is None:
        status = "block"
        findings.append({"severity": "block", "message": "ffprobe 未能读取 canonical 成片时长。"})
    elif expected is not None and abs(actual - float(expected)) > tolerance:
        status = "block"
        findings.append({
            "severity": "block",
            "message": f"成片时长 {actual:.3f}s 与实际 render recipe {float(expected):.3f}s 相差超过容差 {tolerance:.3f}s。",
            "actual_duration_sec": round(actual, 3),
            "expected_duration_sec": round(float(expected), 3),
        })
    if recipe.get("kind") != "n2d_master_render_recipe" or not recipe.get("ordered_sources"):
        status = "block"
        findings.append({"severity": "block", "code": "render_recipe_missing", "message": "missing exact ordered render recipe"})
    elif master and master.is_file():
        segments, segment_findings = _actual_segments(root, master, recipe)
        fps = float((((receipt.get("validation") or {}).get("probe") or {}).get("video") or {}).get("fps") or 30.0)
        cuts, cut_findings = _actual_cuts(master, segments, fps)
        findings.extend(segment_findings + cut_findings)
        if segment_findings or cut_findings:
            status = "block"
    return {
        "kind": "n2d_final_timeline_probe",
        "version": VERSION,
        "episode": episode,
        "generated_at": now_iso(),
        "status": status,
        "final_master": relpath(root, master) if master else "",
        "expected_duration_sec": round(float(expected), 3) if expected is not None else None,
        "storyboard_expected_duration_sec": round(float(storyboard_expected), 3) if storyboard_expected is not None else None,
        "actual_duration_sec": round(actual, 3) if actual is not None else None,
        "duration_tolerance_sec": round(tolerance, 3),
        "segments": segments,
        "cuts": cuts,
        "expected_segments": expected_segments,
        "expected_cuts": expected_cuts,
        "render_recipe": relpath(root, recipe_path),
        "render_recipe_sha256": media_artifact.sha256_file(recipe_path) if recipe_path.is_file() else "",
        "media_receipt": receipt_check.get("path") or "",
        "media_receipt_status": receipt_check.get("status"),
        "findings": findings,
        "notes": [
            "storyboard rows are expectations only and are never marked pass; pass is reserved for current receipt + actual recipe/source/frame evidence.",
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
            f"<td>{seg.get('actual_start_sec')}</td>"
            f"<td>{seg.get('actual_end_sec')}</td>"
            f"<td>{seg.get('actual_duration_sec')}</td>"
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
    timeline_dir = root / "生产数据" / "timelines" / episode
    timeline_dir.mkdir(parents=True, exist_ok=True)
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
    timeline_path = timeline_dir / "timeline.json"
    tmp = timeline_path.with_name(f"{timeline_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(timeline, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, timeline_path)
    rough_html = root / "生产数据" / "views" / f"rough_cut_preview_{episode}.html"
    rough_html.parent.mkdir(parents=True, exist_ok=True)
    tmp_html = rough_html.with_name(f"{rough_html.name}.tmp.{os.getpid()}")
    tmp_html.write_text(render_rough_cut_html(payload), encoding="utf-8")
    os.replace(tmp_html, rough_html)
    editorial = build_editorial_timeline(root.resolve(), episode)
    editorial_outputs = write_editorial_timeline(root.resolve(), editorial)
    return {
        "timeline": relpath(root, timeline_path),
        "rough_cut_preview": relpath(root, rough_html),
        "editorial_otio": editorial_outputs["otio"],
        "editorial_sidecar": editorial_outputs["sidecar"],
        "editorial_phase": str(editorial.get("phase") or ""),
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
