#!/usr/bin/env python3
"""Write an OpenTimelineIO-compatible editorial timeline for n2d.

No OTIO Python package is required: ``.otio`` is a JSON interchange format.
The emitted schema uses standard Timeline/Stack/Track/Clip/Transition objects
and remains importable by OTIO-aware NLE bridges.  A small n2d sidecar records
hashes, missing media and editorial phase for deterministic gates/reviews.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    from seam_contract import normalize_seam_mode
except ImportError:  # pragma: no cover
    from .seam_contract import normalize_seam_mode


KIND = "n2d_editorial_timeline"
VERSION = 1
OTIO_RATE = 30.0


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def as_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
        return number if number > 0 else None
    except Exception:
        return None


def ffprobe_duration(path: Path) -> Optional[float]:
    if not path.is_file():
        return None
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return as_float(proc.stdout.strip()) if proc.returncode == 0 else None
    except Exception:
        return None


def clip_id(row: Mapping[str, Any], idx: int) -> str:
    raw = str(row.get("clip_id") or row.get("clip") or row.get("id") or "").strip()
    match = re.search(r"(?:clip|镜头)[_\s-]?(\d+)", raw, re.I)
    return f"Clip_{int(match.group(1)):02d}" if match else (raw or f"Clip_{idx:02d}")


def _rt(seconds: float, rate: float = OTIO_RATE) -> Dict[str, Any]:
    return {"OTIO_SCHEMA": "RationalTime.1", "rate": rate, "value": round(float(seconds) * rate, 6)}


def _tr(start: float, duration: float, rate: float = OTIO_RATE) -> Dict[str, Any]:
    return {
        "OTIO_SCHEMA": "TimeRange.1",
        "start_time": _rt(start, rate),
        "duration": _rt(duration, rate),
    }


def _media_reference(root: Path, path: Optional[Path], available_sec: float) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if path and path.is_file():
        rel = relpath(root, path)
        sha = sha256_file(path)
        return ({
            "OTIO_SCHEMA": "ExternalReference.1",
            "name": path.name,
            "metadata": {"n2d": {"relative_path": rel, "sha256": sha}},
            "target_url": rel,
            "available_range": _tr(0.0, available_sec),
            "available_image_bounds": None,
        }, {"path": rel, "sha256": sha, "available_sec": round(available_sec, 3)})
    return ({
        "OTIO_SCHEMA": "MissingReference.1",
        "name": "missing_media",
        "metadata": {"n2d": {"missing": True}},
        "available_range": None,
        "available_image_bounds": None,
    }, {"path": "", "sha256": "", "available_sec": round(available_sec, 3)})


def _clip(root: Path, *, name: str, path: Optional[Path], duration: float, metadata: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    source_duration = ffprobe_duration(path) if path and path.suffix.lower() in {".mp4", ".mov", ".mkv", ".wav", ".mp3", ".m4a"} else None
    available = max(float(duration), float(source_duration or 0.0))
    ref, media = _media_reference(root, path, available)
    payload = {
        "OTIO_SCHEMA": "Clip.2",
        "name": name,
        "metadata": {"n2d": dict(metadata)},
        "source_range": _tr(0.0, duration),
        "effects": [],
        "markers": [],
        "enabled": True,
        "media_references": {"DEFAULT_MEDIA": ref},
        "active_media_reference_key": "DEFAULT_MEDIA",
    }
    return payload, media


def _transition(name: str, duration: float, mode: str, evidence: Mapping[str, Any]) -> Dict[str, Any]:
    half = max(0.01, duration / 2.0)
    return {
        "OTIO_SCHEMA": "Transition.1",
        "name": name,
        "metadata": {"n2d": {"seam_mode": mode, "seam_evidence": dict(evidence)}},
        "transition_type": "SMPTE_Dissolve",
        "in_offset": _rt(half),
        "out_offset": _rt(half),
    }


def _track(name: str, kind: str, children: Sequence[Mapping[str, Any]], markers: Sequence[Mapping[str, Any]] = ()) -> Dict[str, Any]:
    return {
        "OTIO_SCHEMA": "Track.1",
        "name": name,
        "metadata": {"n2d": {"track_role": name}},
        "source_range": None,
        "effects": [],
        "markers": list(markers),
        "enabled": True,
        "children": list(children),
        "kind": kind,
    }


def _storyboard(root: Path, ep: str) -> List[Mapping[str, Any]]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    return [row for row in data.get("clips") or [] if isinstance(row, Mapping)]


def _story_duration(row: Mapping[str, Any]) -> float:
    return float(as_float(row.get("edit_target_sec") or row.get("duration_sec") or row.get("duration") or row.get("时长")) or 1.0)


def _proxy_rows(root: Path, ep: str) -> List[Mapping[str, Any]]:
    data = load_json(root / "合成" / ep / "_proxy" / "timeline.json")
    rows = data.get("timeline") or data.get("segments") or []
    return [row for row in rows if isinstance(row, Mapping)]


def _video_rows_from_files(root: Path, ep: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path in sorted((root / "出视频" / ep / "视频").glob("Clip*.mp4")):
        match = re.search(r"Clip[_\s-]?(\d+)(?:_part(\d+))?", path.stem, re.I)
        if not match or any(token in path.name.lower() for token in ("noaudio", "_raw")):
            continue
        cid = f"Clip_{int(match.group(1)):02d}"
        part = int(match.group(2) or 1)
        out.append({
            "clip": f"{cid}_part{part}" if part > 1 else cid,
            "story_clip": cid,
            "source": relpath(root, path),
            "path": str(path),
            "source_status": "legacy_unverified",
        })
    return out


def _video_sound_routes(root: Path, ep: str) -> Dict[str, Dict[str, Any]]:
    payload = load_json(root / "出视频" / ep / "prompt" / "video_model_routes.json")
    return {
        clip_id(row, idx): dict(row)
        for idx, row in enumerate(payload.get("routes") or [], 1)
        if isinstance(row, Mapping)
    }


def _post_lipsync_path(root: Path, ep: str, cid: str, route: Mapping[str, Any]) -> Optional[Path]:
    required = bool(
        route.get("post_lipsync_required") is True
        or str(route.get("audio_strategy") or "") == "base_video_then_post_lipsync"
    )
    if not required:
        return None
    raw = str(route.get("post_lipsync_output") or "").strip()
    path = Path(raw) if raw else root / "出视频" / ep / "视频_lipsync" / f"{cid}_lipsync.mp4"
    path = path if path.is_absolute() else root / path
    return path if path.is_file() else None


def _first_image(root: Path, ep: str, row: Mapping[str, Any], idx: int) -> Optional[Path]:
    continuity = row.get("continuity") if isinstance(row.get("continuity"), Mapping) else {}
    for value in (row.get("firstframe_png"), row.get("first_frame"), row.get("image"), continuity.get("firstframe_png")):
        if value:
            path = Path(str(value))
            path = path if path.is_absolute() else root / path
            if path.is_file():
                return path
    base = root / "出图" / ep / "图片"
    tokens = (f"Clip_{idx:02d}", f"镜头{idx}", f"镜头{idx:02d}")
    for path in sorted(base.glob("*")) if base.is_dir() else []:
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and any(token in path.stem for token in tokens):
            return path
    return None


def _seams(root: Path, ep: str, clips: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    chain = load_json(root / "脚本" / ep / "continuity_chain.json")
    rows = [
        dict(row) for row in chain.get("seams") or []
        if isinstance(row, Mapping) and str(row.get("scope") or "intra_episode") == "intra_episode"
    ]
    if rows:
        return rows
    out = []
    for left, right in zip(clips, clips[1:]):
        continuity = left.get("continuity") if isinstance(left.get("continuity"), Mapping) else {}
        mode = normalize_seam_mode(
            continuity.get("seam_mode"), continuity.get("transition"),
            need_endframe=bool(continuity.get("need_endframe")),
        ).get("mode")
        out.append({
            "from_clip": clip_id(left, len(out) + 1),
            "to_clip": clip_id(right, len(out) + 2),
            "transition": continuity.get("transition") or "",
            "seam_mode": mode or "",
            "seam_evidence": continuity.get("seam_evidence") or {},
        })
    return out


SRT_TS_RE = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")


def _srt_sec(parts: Sequence[str]) -> float:
    h, m, s, ms = [int(x) for x in parts]
    return h * 3600 + m * 60 + s + ms / 1000.0


def subtitle_markers(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8", errors="ignore").strip())
    markers: List[Dict[str, Any]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_idx = next((idx for idx, line in enumerate(lines) if "-->" in line), -1)
        if timing_idx < 0:
            continue
        match = SRT_TS_RE.search(lines[timing_idx])
        if not match:
            continue
        start = _srt_sec(match.groups()[:4])
        end = _srt_sec(match.groups()[4:])
        text = " ".join(lines[timing_idx + 1:])
        markers.append({
            "OTIO_SCHEMA": "Marker.2",
            "name": text[:80] or "subtitle",
            "metadata": {"n2d": {"subtitle_text": text}},
            "marked_range": _tr(start, max(0.04, end - start)),
            "color": "GREEN",
        })
    return markers


def _audio_track(root: Path, name: str, candidates: Iterable[Path], fallback_duration: float) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    path = next((item for item in candidates if item.is_file()), None)
    if not path:
        return _track(name, "Audio", []), []
    duration = ffprobe_duration(path) or fallback_duration
    item, media = _clip(root, name=path.stem, path=path, duration=duration, metadata={"track_role": name})
    return _track(name, "Audio", [item]), [media]


def _planned_voice_track(root: Path, ep: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], int]:
    """Create editable no-media dialogue slots from timing_estimate.json.

    MissingReference is intentional here: it distinguishes an editorial timing
    plan from a rendered voice asset and avoids disposable silence WAV files.
    """
    timing = load_json(root / "合成" / ep / "配音" / "timing_estimate.json")
    rows = timing.get("lines") if isinstance(timing.get("lines"), list) else []
    children: List[Mapping[str, Any]] = []
    media_rows: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            continue
        duration = as_float(row.get("时长") or row.get("estimated_duration_sec"))
        if not duration:
            continue
        role = str(row.get("角色") or row.get("role") or "voice")
        text = str(row.get("文本") or row.get("text") or "")
        item, media = _clip(
            root,
            name=f"VO_PLAN_{idx:03d}_{role}",
            path=None,
            duration=duration,
            metadata={
                "track_role": "A1 Dialogue_Narration",
                "media_status": "planned_missing_reference",
                "timing_basis": "text_estimate_no_audio",
                "line_index": row.get("line_index") or idx,
                "role": role,
                "text": text,
                "gap_after_sec": row.get("gap_after") or 0,
                "voice_lock_required": True,
            },
        )
        children.append(item)
        media_rows.append(media)
    return _track("A1 Dialogue_Narration", "Audio", children), media_rows, len(children)


def build_editorial_timeline(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    ep = episode if episode.startswith("第") and episode.endswith("集") else f"第{episode}集"
    clips = _storyboard(root, ep)
    seams = _seams(root, ep, clips)
    seam_by_from = {str(row.get("from_clip") or ""): row for row in seams}
    proxy_rows = _proxy_rows(root, ep)
    accepted_rows = [row for row in proxy_rows if str(row.get("source_status") or "").lower() == "accepted"]
    # Once runner manifests exist, they are the acceptance truth: downloaded or
    # merely file-present takes stay out of the editorial cut until accept.
    manifest_backed = any(str(row.get("source_manifest") or "").strip() for row in proxy_rows)
    actual_rows = accepted_rows if manifest_backed else (proxy_rows or _video_rows_from_files(root, ep))
    actual_by_story: Dict[str, List[Mapping[str, Any]]] = {}
    for row in actual_rows:
        key = str(row.get("story_clip") or row.get("clip") or "")
        match = re.search(r"Clip[_\s-]?(\d+)", key, re.I)
        key = f"Clip_{int(match.group(1)):02d}" if match else key
        actual_by_story.setdefault(key, []).append(row)
    sound_routes = _video_sound_routes(root, ep)

    picture_children: List[Mapping[str, Any]] = []
    media_rows: List[Dict[str, Any]] = []
    missing: List[str] = []
    actual_story_count = 0
    accepted_story_count = 0
    total = 0.0
    for idx, story in enumerate(clips, 1):
        cid = clip_id(story, idx)
        story_duration = _story_duration(story)
        rows = actual_by_story.get(cid) or []
        lipsync_path = _post_lipsync_path(root, ep, cid, sound_routes.get(cid, {}))
        if lipsync_path:
            base_accepted = any(str(row.get("source_status") or "").lower() == "accepted" for row in rows)
            rows = [{
                "clip": cid,
                "story_clip": cid,
                "source": relpath(root, lipsync_path),
                "path": str(lipsync_path),
                "source_status": "accepted" if base_accepted else "post_lipsync_ready",
                "edit_target_sec": story_duration,
                "derived_from": "neutral_mouth_base_plate",
                "audio_strategy": "base_video_then_post_lipsync",
            }]
        if rows:
            actual_story_count += 1
            if any(str(row.get("source_status") or "").lower() == "accepted" for row in rows):
                accepted_story_count += 1
            per_part = story_duration / max(1, len(rows))
            for part_idx, row in enumerate(rows, 1):
                raw_path = str(row.get("source") or row.get("path") or "")
                path = Path(raw_path)
                path = path if path.is_absolute() else root / path
                duration = float(as_float(row.get("proxy_duration_sec") or row.get("edit_target_sec") or row.get("duration")) or per_part)
                item, media = _clip(
                    root,
                    name=str(row.get("clip") or (cid if len(rows) == 1 else f"{cid}_part{part_idx}")),
                    path=path if path.is_file() else None,
                    duration=duration,
                    metadata={
                        "story_clip": cid,
                        "phase": "actual_video",
                        "source_status": row.get("source_status") or "file_present",
                        "derived_from": row.get("derived_from") or "",
                        "audio_strategy": row.get("audio_strategy") or sound_routes.get(cid, {}).get("audio_strategy") or "",
                    },
                )
                picture_children.append(item)
                media_rows.append(media)
                total += duration
        else:
            image = _first_image(root, ep, story, idx)
            item, media = _clip(
                root, name=cid, path=image, duration=story_duration,
                metadata={"story_clip": cid, "phase": "animatic", "slate": image is None},
            )
            picture_children.append(item)
            media_rows.append(media)
            total += story_duration
            if image is None:
                missing.append(cid)
        seam = seam_by_from.get(cid) or (seams[idx - 1] if idx - 1 < len(seams) else {})
        mode = str(seam.get("seam_mode") or "")
        if idx < len(clips) and mode == "dissolve":
            evidence = seam.get("seam_evidence") if isinstance(seam.get("seam_evidence"), Mapping) else {}
            dissolve_sec = float(as_float(evidence.get("duration_sec")) or 0.25)
            picture_children.append(_transition(f"{cid}_dissolve", dissolve_sec, mode, evidence))
            # OTIO transitions consume media handles around the edit point; a
            # Transition object does not shorten or extend its parent Track.

    final_master = next(iter(sorted((root / "合成" / ep).glob("成片*.mp4"))), None) if (root / "合成" / ep).is_dir() else None
    if final_master:
        phase = "final_master"
    elif clips and accepted_story_count == len(clips):
        phase = "rough_cut"
    elif actual_story_count:
        phase = "assembly"
    else:
        phase = "animatic"
    subtitle_path = root / "脚本" / ep / "字幕_中文.srt"
    markers = subtitle_markers(subtitle_path)
    tracks: List[Mapping[str, Any]] = [_track("V1 Picture", "Video", picture_children, markers)]
    audio_media: List[Dict[str, Any]] = []
    voice_candidates = [
        root / "合成" / ep / "配音" / "voice_zh.wav",
        root / "合成" / ep / "配音" / "voice.wav",
    ]
    voice_track, media = _audio_track(root, "A1 Dialogue_Narration", voice_candidates, total)
    planned_audio_slots = 0
    if not (voice_track.get("children") or []):
        voice_track, media, planned_audio_slots = _planned_voice_track(root, ep)
    tracks.append(voice_track); audio_media.extend(media)
    ambience_candidates = sorted((root / "合成" / ep).rglob("*foley*.wav")) + sorted((root / "合成" / ep).rglob("*ambient*.wav")) + sorted((root / "合成" / ep).rglob("*room*.wav"))
    ambience_track, media = _audio_track(root, "A2 Ambience_Foley", ambience_candidates, total)
    tracks.append(ambience_track); audio_media.extend(media)
    bgm_candidates = sorted((root / "合成" / ep).rglob("*bgm*.wav")) + sorted((root / "合成" / ep).rglob("*bgm*.mp3"))
    bgm_track, media = _audio_track(root, "A3 BGM", bgm_candidates, total)
    tracks.append(bgm_track); audio_media.extend(media)

    casting = load_json(root / "设定库" / "voice_casting.json")
    sound_route = load_json(root / "生产数据" / f"production_mode_route_{ep}.json")
    timing_basis = "final_voice" if any(path.is_file() for path in voice_candidates) else (
        "text_estimate_no_audio" if planned_audio_slots else "none"
    )
    otio = {
        "OTIO_SCHEMA": "Timeline.1",
        "name": f"{ep} n2d editorial",
        "metadata": {
            "n2d": {
                "kind": KIND,
                "version": VERSION,
                "episode": ep,
                "phase": phase,
                "generated_at": now_iso(),
                "seams": seams,
                "timing_basis": timing_basis,
                "planned_audio_slots": planned_audio_slots,
                "voice_casting_status": casting.get("status") or "missing",
                "sound_route_summary": sound_route.get("summary") or {},
            }
        },
        "global_start_time": None,
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "name": "tracks",
            "metadata": {},
            "source_range": None,
            "effects": [],
            "markers": [],
            "enabled": True,
            "children": tracks,
        },
    }
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "generated_at": now_iso(),
        "phase": phase,
        "status": "ready" if clips else "missing_storyboard",
        "duration_sec": round(total, 3),
        "rate": OTIO_RATE,
        "story_clip_count": len(clips),
        "actual_story_clip_count": actual_story_count,
        "accepted_story_clip_count": accepted_story_count,
        "missing_picture_slots": missing,
        "track_names": [str(track.get("name") or "") for track in tracks],
        "timing_basis": timing_basis,
        "planned_audio_slot_count": planned_audio_slots,
        "voice_casting_status": casting.get("status") or "missing",
        "subtitle_marker_count": len(markers),
        "media": media_rows + audio_media,
        "seams": seams,
        "otio": otio,
    }


def write_editorial_timeline(root: Path, payload: Mapping[str, Any]) -> Dict[str, str]:
    ep = str(payload.get("episode") or "")
    work = root / "合成" / ep / "_work"
    prod = root / "生产数据"
    work.mkdir(parents=True, exist_ok=True)
    prod.mkdir(parents=True, exist_ok=True)
    otio_path = work / "editorial_timeline.otio"
    sidecar_path = prod / f"editorial_timeline_{ep}.json"
    otio_data = payload.get("otio") if isinstance(payload.get("otio"), Mapping) else {}
    tmp = otio_path.with_name(f"{otio_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(otio_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, otio_path)
    # Animatic approval binds an immutable phase snapshot. The working OTIO is
    # intentionally refreshed by accepted clips and final-master probes later;
    # using that mutable file as approval evidence would invalidate a legitimate
    # animatic sign-off on every editorial update.
    snapshot_path = work / "animatic_timeline.otio"
    if str(payload.get("phase") or "") == "animatic":
        tmp_snapshot = snapshot_path.with_name(f"{snapshot_path.name}.tmp.{os.getpid()}")
        tmp_snapshot.write_text(json.dumps(otio_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp_snapshot, snapshot_path)
    sidecar = {key: value for key, value in payload.items() if key != "otio"}
    sidecar["otio_path"] = relpath(root, otio_path)
    sidecar["otio_sha256"] = sha256_file(otio_path)
    if snapshot_path.is_file():
        sidecar["animatic_snapshot_path"] = relpath(root, snapshot_path)
        sidecar["animatic_snapshot_sha256"] = sha256_file(snapshot_path)
    tmp_json = sidecar_path.with_name(f"{sidecar_path.name}.tmp.{os.getpid()}")
    tmp_json.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp_json, sidecar_path)
    outputs = {"otio": relpath(root, otio_path), "sidecar": relpath(root, sidecar_path)}
    if snapshot_path.is_file():
        outputs["animatic_snapshot"] = relpath(root, snapshot_path)
    return outputs
