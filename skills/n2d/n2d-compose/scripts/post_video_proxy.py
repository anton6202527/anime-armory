#!/usr/bin/env python3
"""Build an actual post-video rough-cut proxy from accepted physical clips.

This is intentionally smaller than n2d-compose: no voice, BGM, subtitles,
grade or release packaging.  It trims each generated take to edit_target_sec,
normalizes proxy codecs, joins in storyboard order, and writes lineage evidence.
When ffmpeg is unavailable it still writes a resumable plan instead of claiming
that a playable rough cut exists.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


KIND = "n2d_post_video_proxy"
VERSION = 1
CLIP_RE = re.compile(r"Clip[_-]?(\d+)(?:[^/]*?_part(\d+))?", re.IGNORECASE)

SCRIPT_DIR = Path(__file__).resolve().parent
COMPOSE_DIR = SCRIPT_DIR.parent
N2D_LIB = SCRIPT_DIR.parents[1] / "_lib"
if str(COMPOSE_DIR) not in sys.path:
    sys.path.insert(0, str(COMPOSE_DIR))
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))

try:
    from flow_telemetry import record_milestone as _record_flow_milestone
except Exception:  # pragma: no cover - proxy rendering remains independent
    _record_flow_milestone = None
from editorial_timeline import build_editorial_timeline, write_editorial_timeline  # noqa: E402
from compose_clip_resolver import resolve_clip_video, route_index  # noqa: E402


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def clip_parts(value: Any) -> Tuple[int, int]:
    match = CLIP_RE.search(str(value or ""))
    if not match:
        return (10**9, 1)
    return (int(match.group(1)), int(match.group(2) or 1))


def _positive_float(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def ffprobe_duration(path: Path) -> Optional[float]:
    if shutil.which("ffprobe") is None:
        return None
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return _positive_float(proc.stdout.strip()) if proc.returncode == 0 else None


def storyboard_durations(root: Path, episode: str) -> Dict[int, float]:
    data = load_json(root / "脚本" / episode / "storyboard.json")
    out: Dict[int, float] = {}
    for idx, row in enumerate(data.get("clips") or [], 1):
        if not isinstance(row, Mapping):
            continue
        number, _ = clip_parts(row.get("id") or row.get("clip") or f"Clip_{idx:02d}")
        duration = _positive_float(row.get("duration") or row.get("duration_sec") or row.get("时长"))
        if number < 10**9 and duration:
            out[number] = duration
    return out


def _target_path(root: Path, episode: str, item: Mapping[str, Any]) -> Path:
    explicit = str(item.get("target_path") or "").strip()
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else root / path
    return root / "出视频" / episode / "视频" / str(item.get("target") or "")


def _manifest_assets(root: Path, episode: str) -> List[Dict[str, Any]]:
    latest: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    for path in sorted((root / "生产数据").glob(f"video_batch_{episode}_*.json")):
        data = load_json(path)
        for item in data.get("items") or []:
            if not isinstance(item, Mapping):
                continue
            if str(item.get("status") or "").strip().lower() != "accepted":
                continue
            clip = str(item.get("clip") or "")
            target = _target_path(root, episode, item)
            if not clip or not target.is_file():
                continue
            score = target.stat().st_mtime
            duration = (
                _positive_float(item.get("edit_target_duration"))
                or _positive_float((item.get("duration_plan") or {}).get("edit_target_sec") if isinstance(item.get("duration_plan"), Mapping) else None)
                or _positive_float(item.get("story_duration"))
            )
            row = {
                "clip": clip,
                "story_clip": str(item.get("story_clip") or item.get("relay_parent") or clip),
                "path": str(target),
                "source_manifest": str(path),
                "source_status": str(item.get("status") or "file_present"),
                "edit_target_sec": duration,
                "model": str(item.get("model_version") or data.get("model_version") or ""),
                "provider": str(item.get("cost_provider") or data.get("backend") or ""),
            }
            if clip not in latest or score > latest[clip][0]:
                latest[clip] = (score, row)
    return [row for _, row in latest.values()]


def _fallback_assets(root: Path, episode: str) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[int, int], Path] = {}
    for path in (root / "出视频" / episode / "视频").glob("Clip*.mp4"):
        if any(token in path.name.lower() for token in ("noaudio", "_raw")):
            continue
        key = clip_parts(path.name)
        if key[0] >= 10**9:
            continue
        if key not in grouped or path.stat().st_mtime > grouped[key].stat().st_mtime:
            grouped[key] = path
    return [
        {
            "clip": f"Clip_{number:02d}" + (f"_part{part}" if part > 1 else ""),
            "story_clip": f"Clip_{number:02d}",
            "path": str(path),
            "source_manifest": "",
            "source_status": "formal_directory_fallback",
            "edit_target_sec": None,
            "model": "",
            "provider": "",
        }
        for (number, part), path in grouped.items()
    ]


def discover_assets(root: Path, episode: str) -> List[Dict[str, Any]]:
    # With manifests present, acceptance is the editorial truth. Directory
    # presence only proves download, so fallback is reserved for legacy work.
    manifest_paths = list((root / "生产数据").glob(f"video_batch_{episode}_*.json"))
    assets = _manifest_assets(root, episode) if manifest_paths else _fallback_assets(root, episode)
    routes = route_index(root, episode)
    for row in assets:
        cid = str(row.get("story_clip") or row.get("clip") or "")
        match = CLIP_RE.search(cid)
        cid = f"Clip_{int(match.group(1)):02d}" if match else cid
        selected, source_kind = resolve_clip_video(
            root, episode, cid, row.get("path"), routes, allow_base_preview=True,
        )
        if selected and selected.is_file():
            row["path"] = str(selected)
        row["picture_version"] = source_kind
    return sorted(assets, key=lambda row: (*clip_parts(row.get("clip")), str(row.get("path"))))


def build_plan(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    durations = storyboard_durations(root, episode)
    assets = discover_assets(root, episode)
    present_numbers = {clip_parts(row.get("clip"))[0] for row in assets}
    expected_numbers = sorted(durations)
    missing = [f"Clip_{n:02d}" for n in expected_numbers if n not in present_numbers]
    parts_per_story: Dict[int, int] = {}
    for row in assets:
        number, _part = clip_parts(row.get("clip"))
        parts_per_story[number] = parts_per_story.get(number, 0) + 1
    timeline: List[Dict[str, Any]] = []
    cursor = 0.0
    for row in assets:
        number, _part = clip_parts(row.get("clip"))
        duration = _positive_float(row.get("edit_target_sec"))
        if duration is None and number in durations:
            duration = durations[number] / max(1, parts_per_story.get(number, 1))
        actual = ffprobe_duration(Path(str(row["path"])))
        usable = min(duration, actual) if duration and actual else (duration or actual)
        item = dict(row)
        item.update({
            "source": relpath(root, Path(str(row["path"]))),
            "source_sha256": sha256_file(Path(str(row["path"]))),
            "source_duration_sec": round(actual, 3) if actual else None,
            "edit_target_sec": round(duration, 3) if duration else None,
            "proxy_duration_sec": round(usable, 3) if usable else None,
            "timeline_start_sec": round(cursor, 3),
            "timeline_end_sec": round(cursor + float(usable or 0), 3),
        })
        cursor += float(usable or 0)
        timeline.append(item)
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "generated_at": now_iso(),
        "status": "incomplete" if missing or not assets else "planned",
        "rendered": False,
        "expected_story_clips": [f"Clip_{n:02d}" for n in expected_numbers],
        "missing_story_clips": missing,
        "timeline": timeline,
        "expected_proxy_duration_sec": round(cursor, 3),
        "output": f"合成/{episode}/_proxy/actual_rough_cut.mp4",
        "notes": [
            "This proxy uses accepted/generated clip pixels and edit targets only; voice/BGM/subtitles/grade remain outside scope.",
            "Hybrid talking shots use post-lipsync video when present; otherwise the rough proxy may retain the explicitly marked base-preview plate.",
        ],
    }


def _proxy_geometry(root: Path) -> Tuple[int, int]:
    text = ""
    try:
        text = (root / "_设置.md").read_text(encoding="utf-8")
    except OSError:
        pass
    return (1280, 720) if re.search(r"画幅\s*[:：]\s*16\s*[:：]\s*9", text) else (720, 1280)


def render_proxy(root: Path, episode: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    if plan.get("missing_story_clips") or not plan.get("timeline"):
        plan["status"] = "incomplete"
        return plan
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        plan["status"] = "planned_ffmpeg_missing"
        plan.setdefault("notes", []).append("ffmpeg/ffprobe unavailable; plan saved for later render")
        return plan
    width, height = _proxy_geometry(root)
    proxy_dir = root / "合成" / episode / "_proxy"
    work = proxy_dir / "_work"
    work.mkdir(parents=True, exist_ok=True)
    normalized: List[Path] = []
    for idx, item in enumerate(plan.get("timeline") or [], 1):
        source = root / str(item.get("source"))
        if not source.is_file():
            plan["status"] = "render_failed"
            plan.setdefault("notes", []).append(f"source disappeared: {source}")
            return plan
        out = work / f"{idx:03d}_{item.get('clip')}.mp4"
        duration = _positive_float(item.get("proxy_duration_sec"))
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps=24"
        )
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(source)]
        if duration:
            cmd += ["-t", f"{duration:.3f}"]
        cmd += ["-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", str(out)]
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0 or not out.is_file():
            plan["status"] = "render_failed"
            plan.setdefault("notes", []).append(f"normalize failed for {item.get('clip')}: {proc.stderr[-400:]}")
            return plan
        normalized.append(out)

    list_path = work / "list.txt"
    list_path.write_text("".join(f"file '{path.resolve()}'\n" for path in normalized), encoding="utf-8")
    output = proxy_dir / "actual_rough_cut.mp4"
    storyboard = root / "脚本" / episode / "storyboard.json"
    report = proxy_dir / "seam_report.md"
    try:
        import seam_concat

        rc = seam_concat.run(
            str(list_path), str(output), storyboard=str(storyboard),
            fallback="cut", dissolve_sec=0.15, report=str(report), plan_only=False,
        )
    except Exception as exc:  # pragma: no cover - fallback still leaves evidence
        rc = 1
        plan.setdefault("notes", []).append(f"seam_concat error: {type(exc).__name__}: {exc}")
    if rc != 0 or not output.is_file():
        plan["status"] = "render_failed"
        return plan
    plan.update({
        "status": "ready",
        "rendered": True,
        "output": relpath(root, output),
        "output_sha256": sha256_file(output),
        "actual_proxy_duration_sec": round(ffprobe_duration(output) or 0.0, 3),
        "seam_report": relpath(root, report) if report.is_file() else "",
        "rendered_at": now_iso(),
    })
    return plan


def write_plan(root: Path, episode: str, payload: Mapping[str, Any]) -> Path:
    path = root / "生产数据" / f"post_video_proxy_{episode}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    timeline = root / "合成" / episode / "_proxy" / "timeline.json"
    timeline.parent.mkdir(parents=True, exist_ok=True)
    timeline.write_text(json.dumps({
        "kind": "n2d_post_video_proxy_timeline",
        "version": VERSION,
        "episode": episode,
        "status": payload.get("status"),
        "output": payload.get("output"),
        "timeline": payload.get("timeline") or [],
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_and_maybe_render(root: Path, episode: str, *, render: bool) -> Dict[str, Any]:
    payload = build_plan(root, episode)
    if render:
        payload = render_proxy(root.resolve(), episode, payload)
    path = write_plan(root.resolve(), episode, payload)
    payload["manifest_path"] = relpath(root.resolve(), path)
    editorial = build_editorial_timeline(root.resolve(), episode)
    payload["editorial_timeline"] = {
        "phase": editorial.get("phase"),
        "status": editorial.get("status"),
        "outputs": write_editorial_timeline(root.resolve(), editorial),
    }
    if _record_flow_milestone is not None:
        try:
            _record_flow_milestone(
                root.resolve(),
                "actual_rough_cut_ready" if payload.get("status") == "ready" else "actual_rough_cut_planned",
                episode=episode,
                stage="compose_proxy",
                extra={
                    "status": payload.get("status"),
                    "artifact": payload.get("output"),
                    "artifact_sha256": payload.get("output_sha256"),
                    "count": len(payload.get("timeline") or []),
                },
            )
        except Exception:
            pass
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    payload = build_and_maybe_render(Path(ns.root), ns.episode, render=ns.render)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else f"{ns.episode} post-video proxy: {payload['status']} · {payload.get('output')}")
    return 0 if payload.get("status") in {"ready", "planned", "planned_ffmpeg_missing"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
