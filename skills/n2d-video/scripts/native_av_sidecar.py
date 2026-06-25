#!/usr/bin/env python3
"""Native A/V sidecar writer for n2d-video.

This module does not certify that generated audio is correct. It creates the
machine sidecars that downstream gates need, marks unverifiable evidence as
``needs_review``, and extracts native-speech audio segments when a clip with an
audio track is accepted.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


PHYSICS_KIND = "n2d_native_av_physics"
VOICE_KIND = "n2d_native_voice_identity_segments"
VERSION = 1

CHAR_RE = re.compile(r"\b(CHAR[_-]?\d+)\b", re.IGNORECASE)
CLIP_RE = re.compile(r"\bClip[_\s-]?(\d+)\b", re.IGNORECASE)
LOC_RE = re.compile(r"\b(LOC[_-]?\d+)\b", re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def physics_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"native_av_physics_{episode}.json"


def voice_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"native_voice_identity_{episode}.json"


def rel_to_root(root: Path, path: Optional[Path]) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def load_json_object(path: Path, *, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else (default or {})
    except (OSError, ValueError):
        return default or {}


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_text(path: Optional[Path]) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def normalize_clip_id(value: Any) -> str:
    text = str(value or "").strip()
    m = CLIP_RE.search(text)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return text


def normalize_character_id(value: Any) -> str:
    text = str(value or "").strip()
    m = CHAR_RE.search(text)
    if not m:
        return text
    return m.group(1).replace("-", "_").upper()


def infer_character_id(text: str) -> str:
    m = CHAR_RE.search(text or "")
    return normalize_character_id(m.group(1)) if m else ""


def infer_location_id(text: str) -> str:
    m = LOC_RE.search(text or "")
    return m.group(1).replace("-", "_").upper() if m else ""


def infer_audio_intent(text: str, *, has_audio: Optional[bool] = None) -> str:
    low = str(text or "").lower()
    if "native_speech" in low or "speech_policy=native_speech" in low or "原生说话" in text or "台词+口型" in text:
        return "native_speech"
    if "native_sfx" in low or "动作音效" in text or "动作声" in text or "拟音" in text:
        return "native_sfx"
    if "ambience" in low or "环境声" in text or "氛围声" in text:
        return "ambience"
    if "audio_intent=none" in low or "无原生音频" in text:
        return "none"
    return "ambience" if has_audio else "none"


def infer_compose_policy(text: str, audio_intent: str) -> str:
    low = str(text or "").lower()
    if "compose_policy=保留原片音轨" in text or "保留原片音轨" in text:
        return "保留原片音轨"
    if "compose_policy=低音量混入环境声" in text or "低音量混入" in text:
        return "低音量混入环境声"
    if "compose_policy=丢弃" in text or "丢弃" in text:
        return "丢弃"
    if audio_intent == "native_speech":
        return "保留原片音轨"
    if audio_intent in {"ambience", "native_sfx"}:
        return "低音量混入环境声"
    return "丢弃"


def _mouth_visible(text: str) -> bool:
    low = str(text or "").lower()
    if "mouth_visible=no" in low or "mouth_visible=false" in low or "无口型" in text:
        return False
    if "mouth_visible=yes" in low or "mouth_visible=true" in low or "口型" in text:
        return True
    return True


def build_physics_clip(
    *,
    root: Path,
    episode: str,
    clip_id: str,
    prompt_text: str,
    video_path: Optional[Path] = None,
    has_audio: Optional[bool] = None,
) -> Dict[str, Any]:
    audio_intent = infer_audio_intent(prompt_text, has_audio=has_audio)
    character_id = infer_character_id(prompt_text)
    location_id = infer_location_id(prompt_text)
    compose_policy = infer_compose_policy(prompt_text, audio_intent)
    clip = {
        "clip_id": normalize_clip_id(clip_id),
        "audio_intent": audio_intent,
        "video_path": rel_to_root(root, video_path),
        "has_audio": has_audio,
        "evidence_status": "needs_review",
        "review_status": "needs_review",
        "generated_by": "n2d-video/native_av_sidecar.py",
        "updated_at": now_iso(),
        "speaker_source": {},
        "lip_sync": {"status": "not_applicable", "evidence": "needs_review"},
        "action_sounds": [],
        "spatial_acoustics": {
            "space_id": location_id or "needs_review",
            "distance": "needs_review",
            "reverb_profile": "needs_review",
        },
        "post_policy": {
            "compose_policy": compose_policy,
            "processing": "compose_stage_controls_native_track",
        },
    }
    if audio_intent == "native_speech":
        mouth = _mouth_visible(prompt_text)
        clip["speaker_source"] = {
            "character_id": character_id or "needs_review",
            "speaker_key": f"{character_id}_native" if character_id else "needs_review",
            "on_screen": bool(character_id),
            "mouth_visible": mouth,
            "dialogue_ref": "needs_review",
        }
        clip["lip_sync"] = {
            "status": "needs_review",
            "mouth_visible": mouth,
            "evidence": "accepted_clip_requires_human_or_machine_lipsync_review",
        }
    elif audio_intent in {"ambience", "native_sfx"}:
        key = "ambience_source" if audio_intent == "ambience" else "source"
        clip["speaker_source"] = {
            key: location_id or "needs_review",
            "visible_evidence": "needs_review",
        }
        if audio_intent == "native_sfx":
            clip["action_sounds"] = [{
                "source": "needs_review",
                "visible_evidence": "needs_review",
                "timing": "needs_review",
            }]
    else:
        clip["speaker_source"] = {"source": "none"}
    return clip


def _upsert_by_key(rows: List[Dict[str, Any]], row: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    wanted = str(row.get(key) or "")
    out: List[Dict[str, Any]] = []
    replaced = False
    for item in rows:
        if isinstance(item, dict) and str(item.get(key) or "") == wanted:
            out.append(row)
            replaced = True
        elif isinstance(item, dict):
            out.append(item)
    if not replaced:
        out.append(row)
    return out


def upsert_physics(root: Path, episode: str, row: Dict[str, Any]) -> Path:
    path = physics_path(root, episode)
    data = load_json_object(path, default={})
    if data.get("kind") not in {None, "", PHYSICS_KIND}:
        raise ValueError(f"{path} kind is not {PHYSICS_KIND}")
    rows = data.get("clips") if isinstance(data.get("clips"), list) else []
    data.update({
        "kind": PHYSICS_KIND,
        "version": VERSION,
        "episode": episode,
        "updated_at": now_iso(),
        "clips": _upsert_by_key(rows, row, "clip_id"),
    })
    atomic_write_json(path, data)
    return path


def extract_audio_segment(root: Path, episode: str, clip_id: str, video_path: Path) -> Tuple[Optional[Path], str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None, "ffmpeg_missing"
    out_dir = root / "出视频" / episode / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{normalize_clip_id(clip_id)}_native.wav"
    proc = subprocess.run(
        [ffmpeg, "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(out)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0 or not out.is_file():
        return None, f"ffmpeg_failed:{(proc.stderr or proc.stdout or '')[:160]}"
    return out, "extracted"


def upsert_voice_segment(root: Path, episode: str, segment: Dict[str, Any]) -> Path:
    path = voice_path(root, episode)
    data = load_json_object(path, default={})
    if data.get("kind") not in {None, "", VOICE_KIND}:
        raise ValueError(f"{path} kind is not {VOICE_KIND}")
    rows = data.get("segments") if isinstance(data.get("segments"), list) else []
    data.update({
        "kind": VOICE_KIND,
        "version": VERSION,
        "episode": episode,
        "updated_at": now_iso(),
        "segments": _upsert_by_key(rows, segment, "clip_id"),
    })
    atomic_write_json(path, data)
    return path


def update_sidecars(
    root: Path,
    episode: str,
    item: Mapping[str, Any],
    video_path: Path,
    qc_clip: Optional[Mapping[str, Any]] = None,
    *,
    prompt_text: Optional[str] = None,
    extract_audio: bool = True,
) -> Dict[str, Any]:
    root = Path(root)
    episode = str(episode)
    clip_id = normalize_clip_id(item.get("clip") or item.get("clip_id") or video_path.stem)
    prompt_path = Path(str(item.get("prompt_file"))) if item.get("prompt_file") else None
    text = prompt_text if prompt_text is not None else (str(item.get("prompt_text") or "") or _read_text(prompt_path))
    has_audio_raw = qc_clip.get("has_audio") if isinstance(qc_clip, Mapping) else None
    has_audio = bool(has_audio_raw) if has_audio_raw is not None else None
    physics = build_physics_clip(
        root=root,
        episode=episode,
        clip_id=clip_id,
        prompt_text=text or "",
        video_path=video_path,
        has_audio=has_audio,
    )
    physics_file = upsert_physics(root, episode, physics)
    result: Dict[str, Any] = {
        "status": "updated",
        "physics_path": rel_to_root(root, physics_file),
        "voice_path": "",
        "audio_extract": "not_applicable",
        "audio_intent": physics.get("audio_intent"),
    }

    if physics.get("audio_intent") != "native_speech":
        return result
    if has_audio is False:
        result["audio_extract"] = "skipped:no_audio_track"
        return result
    speaker = physics.get("speaker_source") if isinstance(physics.get("speaker_source"), dict) else {}
    character_id = str(speaker.get("character_id") or "")
    if not character_id or character_id == "needs_review":
        result["audio_extract"] = "skipped:character_id_needs_review"
        return result
    if not extract_audio:
        result["audio_extract"] = "skipped:disabled"
        return result

    wav, status = extract_audio_segment(root, episode, clip_id, video_path)
    result["audio_extract"] = status
    if wav is None:
        return result
    segment = {
        "clip_id": clip_id,
        "character_id": character_id,
        "speaker_key": str(speaker.get("speaker_key") or f"{character_id}_native"),
        "wav": rel_to_root(root, wav),
        "source_video": rel_to_root(root, video_path),
        "evidence_status": "needs_review",
        "review_status": "needs_review",
        "updated_at": now_iso(),
    }
    voice_file = upsert_voice_segment(root, episode, segment)
    result["voice_path"] = rel_to_root(root, voice_file)
    return result


def _bool_or_none(value: str) -> Optional[bool]:
    v = str(value or "").strip().lower()
    if v in {"1", "true", "yes", "y", "有", "是"}:
        return True
    if v in {"0", "false", "no", "n", "无", "否"}:
        return False
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="write/update native A/V sidecars for an accepted n2d video clip")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--clip", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--prompt-file")
    ap.add_argument("--has-audio", default="unknown")
    ap.add_argument("--no-extract-audio", action="store_true")
    args = ap.parse_args(argv)

    item = {"clip": args.clip}
    if args.prompt_file:
        item["prompt_file"] = args.prompt_file
    qc_clip = {"has_audio": _bool_or_none(args.has_audio)}
    result = update_sidecars(
        Path(args.root),
        args.episode,
        item,
        Path(args.video),
        qc_clip,
        extract_audio=not args.no_extract_audio,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
