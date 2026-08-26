#!/usr/bin/env python3
"""Write the exact ordered source/filter/track recipe used by n2d-compose."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


KIND = "n2d_master_render_recipe"
VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def _duration(path: Path) -> Optional[float]:
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        value = float(proc.stdout.strip()) if proc.returncode == 0 else 0.0
        return value if value > 0 else None
    except Exception:
        return None


def _clip_name(path: Path, index: int) -> str:
    match = re.search(r"(?:clip|镜头)[_\s-]?0*(\d+)", path.stem, re.I)
    return f"Clip_{int(match.group(1)):02d}" if match else f"Clip_{index:02d}"


def _frame_sample(path: Path, at_sec: float) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(0.0, at_sec):.6f}",
             "-i", str(path), "-frames:v", "1", "-vf", "scale=32:18,format=gray",
             "-f", "rawvideo", "-"],
            capture_output=True, timeout=90, check=False,
        )
    except Exception:
        return {"available": False}
    if proc.returncode != 0 or len(proc.stdout) != 32 * 18:
        return {"available": False}
    return {
        "available": True,
        "time_sec": round(max(0.0, at_sec), 6),
        "framehash_sha256": hashlib.sha256(proc.stdout).hexdigest(),
        "gray32x18_base64": base64.b64encode(proc.stdout).decode("ascii"),
    }


def append_source(
    ndjson: Path,
    root: Path,
    source: Path,
    normalized: Path,
    edit_duration: Optional[float],
    speed_mode: str,
    video_filter: str,
) -> Dict[str, Any]:
    ndjson.parent.mkdir(parents=True, exist_ok=True)
    index = 1
    if ndjson.is_file():
        index += sum(1 for line in ndjson.read_text(encoding="utf-8").splitlines() if line.strip())
    source_duration = _duration(source)
    normalized_duration = _duration(normalized)
    duration = float(edit_duration or normalized_duration or source_duration or 0.0)
    midpoint = max(0.04, min(max(0.04, duration - 0.04), duration / 2.0))
    row = {
        "order": index,
        "clip": _clip_name(source, index),
        "source": relpath(root, source),
        "source_sha256": sha256_file(source),
        "source_in_sec": 0.0,
        "source_out_sec": round(duration, 6),
        "edit_duration_sec": round(duration, 6),
        "source_duration_sec": round(float(source_duration or 0.0), 6),
        "speed_mode": speed_mode,
        "normalized": relpath(root, normalized),
        "normalized_sha256": sha256_file(normalized),
        "normalized_duration_sec": round(float(normalized_duration or 0.0), 6),
        "video_filter": video_filter,
        "normalized_midpoint_sample": _frame_sample(normalized, midpoint),
    }
    with ndjson.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def _asset(root: Path, path: Optional[Path], role: str) -> Dict[str, Any]:
    if not path or not path.is_file():
        return {"role": role, "path": "", "sha256": "", "status": "absent"}
    return {
        "role": role,
        "path": relpath(root, path),
        "sha256": sha256_file(path),
        "duration_sec": round(float(_duration(path) or 0.0), 6),
        "status": "bound",
    }


def _read_sources(path: Path) -> list[Dict[str, Any]]:
    out: list[Dict[str, Any]] = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def build_recipe(
    root: Path,
    episode: str,
    sources_path: Path,
    picture_path: Path,
    *,
    width: int,
    height: int,
    fps: str,
    filtergraph_path: Optional[Path] = None,
    voice: Optional[Path] = None,
    bgm: Optional[Path] = None,
    clip_audio: Optional[Path] = None,
    foley: Optional[Path] = None,
    subtitle: Optional[Path] = None,
) -> Dict[str, Any]:
    sources = _read_sources(sources_path)
    cursor = 0.0
    for row in sources:
        duration = float(row.get("edit_duration_sec") or row.get("normalized_duration_sec") or 0.0)
        row["timeline_in_sec"] = round(cursor, 6)
        cursor += duration
        row["timeline_out_sec"] = round(cursor, 6)
    filtergraph = ""
    if filtergraph_path and filtergraph_path.is_file():
        filtergraph = filtergraph_path.read_text(encoding="utf-8", errors="replace")
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "episode": episode,
        "generated_at": now_iso(),
        "picture": _asset(root, picture_path, "V1_picture_lock"),
        "master_spec": {
            "width": int(width), "height": int(height), "fps": str(fps),
            "pixel_format": "yuv420p", "color": "bt709_sdr_limited",
            "audio_sample_rate": 48000,
        },
        "ordered_sources": sources,
        "duration_sec": round(cursor, 6),
        "audio_tracks": [
            _asset(root, voice, "A1_dialogue_narration"),
            _asset(root, clip_audio, "A2_native_ambience"),
            _asset(root, foley, "A3_foley"),
            _asset(root, bgm, "A4_bgm"),
        ],
        "subtitle_track": _asset(root, subtitle, "S1_burned_subtitles"),
        "filtergraph": filtergraph,
        "filtergraph_sha256": hashlib.sha256(filtergraph.encode("utf-8")).hexdigest(),
    }
    hash_scope = dict(payload)
    hash_scope.pop("generated_at", None)
    payload["recipe_sha256"] = hashlib.sha256(
        json.dumps(hash_scope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    append = sub.add_parser("append-source")
    append.add_argument("ndjson")
    append.add_argument("root")
    append.add_argument("source")
    append.add_argument("normalized")
    append.add_argument("--duration", type=float)
    append.add_argument("--speed-mode", default="trim")
    append.add_argument("--filter", default="")
    write = sub.add_parser("write")
    write.add_argument("root")
    write.add_argument("episode")
    write.add_argument("sources")
    write.add_argument("picture")
    write.add_argument("output")
    write.add_argument("--width", type=int, required=True)
    write.add_argument("--height", type=int, required=True)
    write.add_argument("--fps", required=True)
    write.add_argument("--filtergraph")
    write.add_argument("--voice")
    write.add_argument("--bgm")
    write.add_argument("--clip-audio")
    write.add_argument("--foley")
    write.add_argument("--subtitle")
    return ap


def _optional_path(value: Optional[str]) -> Optional[Path]:
    return Path(value) if value else None


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.command == "append-source":
        payload = append_source(
            Path(ns.ndjson), Path(ns.root).resolve(), Path(ns.source).resolve(), Path(ns.normalized).resolve(),
            ns.duration, ns.speed_mode, ns.filter,
        )
    else:
        payload = build_recipe(
            Path(ns.root).resolve(), ns.episode, Path(ns.sources), Path(ns.picture),
            width=ns.width, height=ns.height, fps=ns.fps,
            filtergraph_path=_optional_path(ns.filtergraph), voice=_optional_path(ns.voice),
            bgm=_optional_path(ns.bgm), clip_audio=_optional_path(ns.clip_audio),
            foley=_optional_path(ns.foley), subtitle=_optional_path(ns.subtitle),
        )
        atomic_write(Path(ns.output), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
