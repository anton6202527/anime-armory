#!/usr/bin/env python3
"""Canonical media validation, receipt, and compare-and-swap promotion for n2d.

This module is deliberately self-contained so direct compose, n2d-batch and the
release verdict can share one definition of a technically usable master.  A
provider ``succeeded`` flag or a file with an MP4 header is never sufficient.
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
import socket
import struct
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


KIND = "n2d_media_artifact_receipt"
VERSION = 1
VALIDATOR_VERSION = "n2d-media-validator/1"
RECIPE_KIND = "n2d_master_render_recipe"
RECIPE_VERSION = 1
UNKNOWN_COLOR_VALUES = {"", "unknown", "unspecified", "reserved", "n/a"}
REQUIRED_SPEC_FIELDS = {
    "container", "video_codecs", "audio_codecs", "width", "height", "fps",
    "pix_fmt", "color_space", "color_transfer", "color_primaries", "color_range",
    "audio_required", "audio_sample_rate", "audio_channels", "known_color_required",
    "faststart_required", "expected_duration_sec", "duration_tolerance_sec",
    "timeline_recipe_sha256", "timeline_recipe_content_sha256", "target_lufs",
    "true_peak_dbtp",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_sha(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _positive_float(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def _render_recipe(
    path: str | Path | None,
    episode: str,
) -> tuple[Dict[str, Any], str, Optional[float], list[str]]:
    """Load and prove the canonical render recipe used to bind master duration."""
    issues: list[str] = []
    if path is None:
        return {}, "", None, ["render recipe is required"]
    recipe_path = Path(path).resolve()
    if not recipe_path.is_file():
        return {}, "", None, ["render recipe is missing"]
    payload = load_json(recipe_path)
    try:
        version = int(payload.get("version") or 0)
    except (TypeError, ValueError):
        version = 0
    if payload.get("kind") != RECIPE_KIND or version != RECIPE_VERSION:
        issues.append("render recipe kind/version is invalid")
    if str(payload.get("episode") or "") != episode:
        issues.append("render recipe episode does not match")
    sources = payload.get("ordered_sources")
    if not isinstance(sources, list) or not sources:
        issues.append("render recipe has no ordered sources")
    else:
        for index, row in enumerate(sources, 1):
            if not isinstance(row, Mapping):
                issues.append(f"render recipe source {index} is invalid")
                continue
            if not str(row.get("source_sha256") or "") or not _positive_float(
                row.get("edit_duration_sec") or row.get("normalized_duration_sec")
            ):
                issues.append(f"render recipe source {index} lacks SHA/duration")
    hash_scope = dict(payload)
    stored_content_sha = str(hash_scope.pop("recipe_sha256", "") or "")
    hash_scope.pop("generated_at", None)
    calculated_content_sha = canonical_json_sha(hash_scope)
    if not stored_content_sha or stored_content_sha != calculated_content_sha:
        issues.append("render recipe content SHA is invalid")
    picture = payload.get("picture") if isinstance(payload.get("picture"), Mapping) else {}
    expected_duration = _positive_float(picture.get("duration_sec")) or _positive_float(payload.get("duration_sec"))
    if expected_duration is None:
        issues.append("render recipe expected duration is missing")
    return payload, sha256_file(recipe_path), expected_duration, issues


def _bind_spec_to_recipe(
    spec: Mapping[str, Any],
    recipe_path: str | Path,
    episode: str,
) -> tuple[Dict[str, Any], list[str]]:
    payload, recipe_sha, expected_duration, issues = _render_recipe(recipe_path, episode)
    bound = dict(spec)
    if issues:
        return bound, issues
    assert expected_duration is not None
    expected_values = {
        "expected_duration_sec": round(expected_duration, 6),
        "duration_tolerance_sec": float(bound.get("duration_tolerance_sec") or 0.25),
        "timeline_recipe_sha256": recipe_sha,
        "timeline_recipe_content_sha256": str(payload.get("recipe_sha256") or ""),
    }
    for key, value in expected_values.items():
        if key in bound and key != "duration_tolerance_sec" and str(bound[key]) != str(value):
            issues.append(f"spec {key} conflicts with render recipe")
        bound[key] = value
    return bound, issues


def relpath(root: str | Path, path: str | Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except Exception:
        return str(path)


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, target)
    return target


def load_json(path: str | Path) -> Dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _run(
    args: Sequence[str], *, timeout: int = 180, runner=subprocess.run
) -> subprocess.CompletedProcess[str]:
    return runner(
        list(args),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def _fraction(value: Any) -> Optional[float]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        if "/" in raw:
            numerator, denominator = raw.split("/", 1)
            result = float(numerator) / float(denominator)
        else:
            result = float(raw)
        return result if math.isfinite(result) and result > 0 else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def probe_media(path: str | Path, *, runner=subprocess.run) -> Dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        return {"available": False, "error": "missing media"}
    try:
        proc = _run(
            [
                "ffprobe", "-v", "error", "-print_format", "json",
                "-show_streams", "-show_format", str(target),
            ],
            timeout=60,
            runner=runner,
        )
    except FileNotFoundError:
        return {"available": False, "error": "ffprobe unavailable"}
    except subprocess.TimeoutExpired:
        return {"available": False, "error": "ffprobe timed out"}
    except Exception as exc:
        return {"available": False, "error": f"ffprobe failed: {exc}"}
    if proc.returncode != 0:
        return {"available": False, "error": proc.stderr.strip() or "ffprobe failed"}
    try:
        payload = json.loads(proc.stdout or "{}")
    except ValueError as exc:
        return {"available": False, "error": f"invalid ffprobe json: {exc}"}
    streams = payload.get("streams") if isinstance(payload, dict) else []
    streams = streams if isinstance(streams, list) else []
    video = next((row for row in streams if row.get("codec_type") == "video"), {})
    audio = next((row for row in streams if row.get("codec_type") == "audio"), {})
    fmt = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    try:
        duration = float(fmt.get("duration"))
    except (TypeError, ValueError):
        duration = 0.0
    return {
        "available": True,
        "format_name": str(fmt.get("format_name") or ""),
        "duration_sec": round(duration, 6) if duration > 0 else 0.0,
        "bit_rate": str(fmt.get("bit_rate") or ""),
        "video": {
            "codec": str(video.get("codec_name") or ""),
            "profile": str(video.get("profile") or ""),
            "width": int(video.get("width") or 0),
            "height": int(video.get("height") or 0),
            "pix_fmt": str(video.get("pix_fmt") or ""),
            "fps": _fraction(video.get("avg_frame_rate") or video.get("r_frame_rate")),
            "fps_rational": str(video.get("avg_frame_rate") or video.get("r_frame_rate") or ""),
            "color_space": str(video.get("color_space") or ""),
            "color_transfer": str(video.get("color_transfer") or ""),
            "color_primaries": str(video.get("color_primaries") or ""),
            "color_range": str(video.get("color_range") or ""),
        } if video else {},
        "audio": {
            "codec": str(audio.get("codec_name") or ""),
            "sample_rate": int(audio.get("sample_rate") or 0),
            "channels": int(audio.get("channels") or 0),
            "channel_layout": str(audio.get("channel_layout") or ""),
        } if audio else {},
        "stream_count": len(streams),
    }


def full_decode(path: str | Path, *, runner=subprocess.run, timeout: int = 600) -> Dict[str, Any]:
    """Decode the first video and optional first audio stream from start to EOF."""
    try:
        proc = _run(
            [
                "ffmpeg", "-nostdin", "-v", "error", "-xerror", "-err_detect", "explode",
                "-i", str(path), "-map", "0:v:0", "-map", "0:a:0?", "-f", "null", "-",
            ],
            timeout=timeout,
            runner=runner,
        )
    except FileNotFoundError:
        return {"status": "block", "error": "ffmpeg unavailable"}
    except subprocess.TimeoutExpired:
        return {"status": "block", "error": "full decode timed out"}
    except Exception as exc:
        return {"status": "block", "error": f"full decode failed: {exc}"}
    return {
        "status": "pass" if proc.returncode == 0 else "block",
        "returncode": proc.returncode,
        "error": "" if proc.returncode == 0 else (proc.stderr.strip() or "decode failed"),
    }


def measure_loudness(path: str | Path, *, runner=subprocess.run) -> Dict[str, Any]:
    try:
        proc = _run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", str(path),
             "-map", "0:a:0", "-af", "loudnorm=print_format=json", "-f", "null", "-"],
            timeout=900,
            runner=runner,
        )
    except Exception as exc:
        return {"available": False, "error": str(exc)}
    matches = re.findall(r"\{[^{}]*\}", proc.stderr or "", re.DOTALL)
    for raw in reversed(matches):
        try:
            data = json.loads(raw)
            return {
                "available": True,
                "integrated_lufs": float(data["input_i"]),
                "true_peak_dbtp": float(data["input_tp"]),
            }
        except (KeyError, TypeError, ValueError):
            continue
    return {"available": False, "error": "loudnorm measurement unavailable"}


def faststart_status(path: str | Path) -> Dict[str, Any]:
    """Read top-level MP4 atoms and prove that ``moov`` precedes ``mdat``."""
    atoms: list[str] = []
    try:
        size = Path(path).stat().st_size
        with Path(path).open("rb") as fh:
            offset = 0
            while offset + 8 <= size and len(atoms) < 128:
                header = fh.read(8)
                if len(header) < 8:
                    break
                atom_size, atom_type = struct.unpack(">I4s", header)
                atom = atom_type.decode("ascii", errors="replace")
                if atom_size == 1:
                    extended = fh.read(8)
                    if len(extended) < 8:
                        break
                    atom_size = struct.unpack(">Q", extended)[0]
                    header_size = 16
                else:
                    header_size = 8
                if atom_size == 0:
                    atom_size = size - offset
                if atom_size < header_size:
                    break
                atoms.append(atom)
                offset += atom_size
                fh.seek(offset)
    except OSError as exc:
        return {"status": "block", "atoms": atoms, "error": str(exc)}
    ok = "moov" in atoms and "mdat" in atoms and atoms.index("moov") < atoms.index("mdat")
    return {"status": "pass" if ok else "block", "atoms": atoms, "error": "" if ok else "moov atom is not before mdat"}


def _check(checks: list[Dict[str, Any]], code: str, ok: bool, actual: Any, expected: Any) -> None:
    checks.append({
        "code": code,
        "status": "pass" if ok else "block",
        "actual": actual,
        "expected": expected,
    })


def validate_media(
    path: str | Path,
    spec: Optional[Mapping[str, Any]] = None,
    *,
    runner=subprocess.run,
    decode_timeout: int = 600,
) -> Dict[str, Any]:
    target = Path(path)
    spec = dict(spec or {})
    checks: list[Dict[str, Any]] = []
    if not target.is_file():
        _check(checks, "file_exists", False, False, True)
        return {"status": "block", "checks": checks, "probe": {"available": False}}
    _check(checks, "file_nonempty", target.stat().st_size > 0, target.stat().st_size, ">0")
    probe = probe_media(target, runner=runner)
    _check(checks, "ffprobe", bool(probe.get("available")), probe.get("error") or "available", "available")
    if not probe.get("available"):
        return {"status": "block", "checks": checks, "probe": probe}
    expected_container = str(spec.get("container") or "").lower()
    if expected_container:
        actual_containers = {part.strip().lower() for part in str(probe.get("format_name") or "").split(",")}
        _check(checks, "container", expected_container in actual_containers, sorted(actual_containers), expected_container)

    video = probe.get("video") if isinstance(probe.get("video"), dict) else {}
    audio = probe.get("audio") if isinstance(probe.get("audio"), dict) else {}
    actual_duration = float(probe.get("duration_sec") or 0)
    _check(checks, "positive_duration", actual_duration > 0, actual_duration, ">0")
    expected_duration = _positive_float(spec.get("expected_duration_sec"))
    if expected_duration is not None:
        tolerance = float(spec.get("duration_tolerance_sec") or 0.25)
        _check(
            checks,
            "timeline_duration",
            abs(actual_duration - expected_duration) <= tolerance,
            actual_duration,
            f"{expected_duration}±{tolerance}",
        )
        _check(
            checks,
            "timeline_not_truncated",
            actual_duration + tolerance >= expected_duration,
            actual_duration,
            f">={expected_duration - tolerance}",
        )
    _check(checks, "video_stream", bool(video), bool(video), True)
    require_audio = bool(spec.get("audio_required", True))
    if require_audio:
        _check(checks, "audio_stream", bool(audio), bool(audio), True)

    scalar_fields = {
        "width": (video.get("width"), spec.get("width")),
        "height": (video.get("height"), spec.get("height")),
        "pix_fmt": (video.get("pix_fmt"), spec.get("pix_fmt")),
        "color_space": (video.get("color_space"), spec.get("color_space")),
        "color_transfer": (video.get("color_transfer"), spec.get("color_transfer")),
        "color_primaries": (video.get("color_primaries"), spec.get("color_primaries")),
        "color_range": (video.get("color_range"), spec.get("color_range")),
        "audio_sample_rate": (audio.get("sample_rate"), spec.get("audio_sample_rate")),
        "audio_channels": (audio.get("channels"), spec.get("audio_channels")),
    }
    for name, (actual, expected) in scalar_fields.items():
        if expected not in (None, ""):
            _check(checks, name, str(actual) == str(expected), actual, expected)

    allowed_vcodecs = spec.get("video_codecs") or ([spec["video_codec"]] if spec.get("video_codec") else [])
    if allowed_vcodecs:
        _check(checks, "video_codec", video.get("codec") in allowed_vcodecs, video.get("codec"), allowed_vcodecs)
    allowed_acodecs = spec.get("audio_codecs") or ([spec["audio_codec"]] if spec.get("audio_codec") else [])
    if require_audio and allowed_acodecs:
        _check(checks, "audio_codec", audio.get("codec") in allowed_acodecs, audio.get("codec"), allowed_acodecs)

    expected_fps = _fraction(spec.get("fps"))
    actual_fps = _fraction(video.get("fps"))
    if expected_fps:
        tolerance = float(spec.get("fps_tolerance") or 0.02)
        _check(checks, "fps", bool(actual_fps and abs(actual_fps - expected_fps) <= tolerance), actual_fps, expected_fps)

    if bool(spec.get("known_color_required", True)):
        for field in ("color_space", "color_transfer", "color_primaries", "color_range"):
            actual = str(video.get(field) or "").lower()
            if spec.get(field) in (None, ""):
                _check(checks, f"known_{field}", actual not in UNKNOWN_COLOR_VALUES, actual, "known")

    decode = full_decode(target, runner=runner, timeout=decode_timeout)
    _check(checks, "full_decode", decode.get("status") == "pass", decode.get("error") or "decoded", "decoded to EOF")
    if bool(spec.get("faststart_required", True)):
        faststart = faststart_status(target)
        _check(checks, "faststart", faststart.get("status") == "pass", faststart.get("atoms"), "moov before mdat")
    else:
        faststart = {"status": "not_required", "atoms": []}

    loudness: Dict[str, Any] = {"available": False, "status": "not_required"}
    if spec.get("target_lufs") is not None:
        loudness = measure_loudness(target, runner=runner)
        _check(checks, "loudness_measurement", bool(loudness.get("available")), loudness.get("error") or "available", "available")
        if loudness.get("available"):
            target_lufs = float(spec["target_lufs"])
            tolerance = float(spec.get("loudness_tolerance_lu") or 1.0)
            actual_lufs = float(loudness["integrated_lufs"])
            peak_limit = float(spec.get("true_peak_dbtp") or -1.0)
            actual_peak = float(loudness["true_peak_dbtp"])
            _check(checks, "integrated_loudness", abs(actual_lufs - target_lufs) <= tolerance, actual_lufs, f"{target_lufs}±{tolerance}")
            _check(checks, "true_peak", actual_peak <= peak_limit + 0.05, actual_peak, f"<={peak_limit}")
            loudness["status"] = "pass" if abs(actual_lufs - target_lufs) <= tolerance and actual_peak <= peak_limit + 0.05 else "block"

    return {
        "status": "pass" if all(row["status"] == "pass" for row in checks) else "block",
        "checks": checks,
        "probe": probe,
        "decode": decode,
        "faststart": faststart,
        "loudness": loudness,
    }


def default_master_spec(
    *, width: int, height: int, fps: str | float, target_lufs: Optional[float] = None
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "container": "mp4",
        "video_codecs": ["h264"],
        "audio_codecs": ["aac"],
        "width": int(width),
        "height": int(height),
        "fps": str(fps),
        "fps_tolerance": 0.02,
        "pix_fmt": "yuv420p",
        "color_space": "bt709",
        "color_transfer": "bt709",
        "color_primaries": "bt709",
        "color_range": "tv",
        "audio_required": True,
        "audio_sample_rate": 48000,
        "audio_channels": 2,
        "known_color_required": True,
        "faststart_required": True,
    }
    if target_lufs is not None:
        payload["target_lufs"] = float(target_lufs)
        payload["true_peak_dbtp"] = -1.0
    return payload


def receipt_path(root: str | Path, episode: str) -> Path:
    return Path(root) / "生产数据" / f"media_artifact_receipt_{episode}.json"


def build_receipt(
    root: str | Path,
    episode: str,
    artifact: str | Path,
    spec: Mapping[str, Any],
    *,
    recipe_path: str | Path | None = None,
    transaction_id: str = "",
    runner=subprocess.run,
) -> Dict[str, Any]:
    root_path = Path(root).resolve()
    artifact_path = Path(artifact).resolve()
    bound_spec, recipe_issues = _bind_spec_to_recipe(spec, recipe_path, episode) if recipe_path else (
        dict(spec), ["render recipe is required"]
    )
    validation = validate_media(artifact_path, bound_spec, runner=runner) if not recipe_issues else {
        "status": "block",
        "checks": [],
        "error": "; ".join(recipe_issues),
    }
    return _receipt_payload(
        root_path,
        episode,
        artifact_path,
        bound_spec,
        validation,
        recipe_path=recipe_path,
        transaction_id=transaction_id,
    )


def _receipt_payload(
    root: str | Path,
    episode: str,
    artifact: str | Path,
    spec: Mapping[str, Any],
    validation: Mapping[str, Any],
    *,
    recipe_path: str | Path | None = None,
    transaction_id: str = "",
    artifact_sha256: str | None = None,
    artifact_size_bytes: int | None = None,
) -> Dict[str, Any]:
    """Build a receipt from a validation result bound to the exact bytes.

    Promotion validates the staged candidate before touching the canonical
    path.  Reusing that hash-bound result avoids a second post-replace decode
    whose failure would otherwise strand an invalid canonical master.
    """
    root_path = Path(root).resolve()
    artifact_path = Path(artifact).resolve()
    recipe = Path(recipe_path).resolve() if recipe_path else None
    recipe_sha = sha256_file(recipe) if recipe and recipe.is_file() else ""
    artifact_sha = artifact_sha256
    if artifact_sha is None:
        artifact_sha = sha256_file(artifact_path) if artifact_path.is_file() else ""
    artifact_size = artifact_size_bytes
    if artifact_size is None:
        artifact_size = artifact_path.stat().st_size if artifact_path.is_file() else 0
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "validator_version": VALIDATOR_VERSION,
        "episode": episode,
        "generated_at": now_iso(),
        "status": validation.get("status"),
        "transaction_id": transaction_id,
        "canonical_artifact": relpath(root_path, artifact_path),
        "artifact": {
            "path": relpath(root_path, artifact_path),
            "sha256": artifact_sha,
            "size_bytes": artifact_size,
        },
        "spec": dict(spec),
        "spec_sha256": canonical_json_sha(dict(spec)),
        "recipe": {
            "path": relpath(root_path, recipe) if recipe else "",
            "sha256": recipe_sha,
        },
        "validation": validation,
        "completion_definition": "current canonical SHA + current spec SHA + current recipe SHA + full decode/spec validation",
    }
    return payload


def write_receipt(root: str | Path, episode: str, payload: Mapping[str, Any]) -> Path:
    return atomic_write_json(receipt_path(root, episode), payload)


def _required_check_codes(spec: Mapping[str, Any]) -> set[str]:
    required = {
        "file_nonempty", "ffprobe", "container", "positive_duration", "timeline_duration",
        "timeline_not_truncated", "video_stream", "width", "height", "pix_fmt",
        "color_space", "color_transfer", "color_primaries", "color_range",
        "video_codec", "fps", "full_decode", "faststart",
    }
    if bool(spec.get("audio_required", True)):
        required.update({"audio_stream", "audio_codec", "audio_sample_rate", "audio_channels"})
    if spec.get("target_lufs") is not None:
        required.update({"loudness_measurement", "integrated_loudness", "true_peak"})
    return required


def _receipt_structure_issues(payload: Mapping[str, Any], episode: str) -> list[str]:
    issues: list[str] = []
    try:
        version = int(payload.get("version") or 0)
    except (TypeError, ValueError):
        version = 0
    if payload.get("kind") != KIND or version != VERSION:
        issues.append("receipt kind/version is invalid")
    if str(payload.get("episode") or "") != episode:
        issues.append("receipt episode does not match")
    if payload.get("validator_version") != VALIDATOR_VERSION:
        issues.append("receipt validator_version is not current")
    if payload.get("status") != "pass":
        issues.append("receipt status is not pass")

    artifact = payload.get("artifact") if isinstance(payload.get("artifact"), Mapping) else {}
    artifact_path = str(artifact.get("path") or "")
    artifact_sha = str(artifact.get("sha256") or "")
    try:
        artifact_size = int(artifact.get("size_bytes") or 0)
    except (TypeError, ValueError):
        artifact_size = 0
    if not artifact_path or not re.fullmatch(r"[0-9a-f]{64}", artifact_sha) or artifact_size <= 0:
        issues.append("receipt artifact path/SHA/size is invalid")
    if str(payload.get("canonical_artifact") or "") != artifact_path:
        issues.append("receipt canonical_artifact differs from artifact.path")

    spec = payload.get("spec") if isinstance(payload.get("spec"), Mapping) else {}
    missing_spec = sorted(REQUIRED_SPEC_FIELDS - set(spec))
    if missing_spec:
        issues.append("receipt spec misses required fields: " + ", ".join(missing_spec))
    if str(spec.get("container") or "").lower() != "mp4":
        issues.append("receipt spec container is not mp4")
    if "h264" not in list(spec.get("video_codecs") or []):
        issues.append("receipt spec must require H.264 video")
    if "aac" not in list(spec.get("audio_codecs") or []):
        issues.append("receipt spec must require AAC audio")
    if spec.get("audio_required") is not True:
        issues.append("receipt spec must require an audio stream")
    try:
        audio_sample_rate = int(spec.get("audio_sample_rate") or 0)
        audio_channels = int(spec.get("audio_channels") or 0)
    except (TypeError, ValueError):
        audio_sample_rate, audio_channels = 0, 0
    if audio_sample_rate != 48000 or audio_channels != 2:
        issues.append("receipt spec must require 48 kHz stereo audio")
    if str(spec.get("pix_fmt") or "") != "yuv420p":
        issues.append("receipt spec must require yuv420p")
    if any(str(spec.get(field) or "") != expected for field, expected in (
        ("color_space", "bt709"), ("color_transfer", "bt709"),
        ("color_primaries", "bt709"), ("color_range", "tv"),
    )):
        issues.append("receipt spec must require Rec.709 SDR limited range")
    if spec.get("known_color_required") is not True or spec.get("faststart_required") is not True:
        issues.append("receipt spec must require known color metadata and faststart")
    if _positive_float(spec.get("width")) is None or _positive_float(spec.get("height")) is None:
        issues.append("receipt spec dimensions are invalid")
    if _fraction(spec.get("fps")) is None:
        issues.append("receipt spec fps is invalid")
    if _positive_float(spec.get("expected_duration_sec")) is None:
        issues.append("receipt spec expected duration is invalid")
    if _positive_float(spec.get("duration_tolerance_sec")) is None:
        issues.append("receipt spec duration tolerance is invalid")
    try:
        target_lufs = float(spec.get("target_lufs"))
        true_peak = float(spec.get("true_peak_dbtp"))
        if not math.isfinite(target_lufs) or not -40.0 <= target_lufs <= -5.0:
            raise ValueError
        if not math.isfinite(true_peak) or true_peak > 0.0:
            raise ValueError
    except (TypeError, ValueError):
        issues.append("receipt spec loudness/true-peak target is invalid")
    if str(payload.get("spec_sha256") or "") != canonical_json_sha(dict(spec)):
        issues.append("receipt spec SHA is invalid")

    recipe = payload.get("recipe") if isinstance(payload.get("recipe"), Mapping) else {}
    recipe_path_value = str(recipe.get("path") or "")
    recipe_sha = str(recipe.get("sha256") or "")
    if not recipe_path_value or not re.fullmatch(r"[0-9a-f]{64}", recipe_sha):
        issues.append("receipt recipe path/SHA is invalid")
    if recipe_sha != str(spec.get("timeline_recipe_sha256") or ""):
        issues.append("receipt recipe SHA differs from bound spec")

    validation = payload.get("validation") if isinstance(payload.get("validation"), Mapping) else {}
    if validation.get("status") != "pass":
        issues.append("receipt validation status is not pass")
    checks = validation.get("checks") if isinstance(validation.get("checks"), list) else []
    passed_codes = {
        str(row.get("code")) for row in checks
        if isinstance(row, Mapping) and row.get("status") == "pass" and row.get("code")
    }
    missing_checks = sorted(_required_check_codes(spec) - passed_codes)
    if missing_checks:
        issues.append("receipt validation misses passing checks: " + ", ".join(missing_checks))
    decode = validation.get("decode") if isinstance(validation.get("decode"), Mapping) else {}
    try:
        decode_returncode = int(decode.get("returncode"))
    except (TypeError, ValueError):
        decode_returncode = -1
    if decode.get("status") != "pass" or decode_returncode != 0:
        issues.append("receipt full_decode proof is invalid")
    faststart = validation.get("faststart") if isinstance(validation.get("faststart"), Mapping) else {}
    if bool(spec.get("faststart_required", True)) and faststart.get("status") != "pass":
        issues.append("receipt faststart proof is invalid")
    if spec.get("target_lufs") is not None:
        loudness = validation.get("loudness") if isinstance(validation.get("loudness"), Mapping) else {}
        if loudness.get("status") != "pass" or loudness.get("available") is not True:
            issues.append("receipt loudness proof is invalid")
        for field in ("integrated_lufs", "true_peak_dbtp"):
            try:
                if not math.isfinite(float(loudness[field])):
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                issues.append(f"receipt loudness {field} is invalid")
    return issues


def _inside_root(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def current_receipt(
    root: str | Path,
    episode: str,
    canonical: str | Path | None = None,
    *,
    runner=subprocess.run,
    decode_timeout: int = 600,
) -> Dict[str, Any]:
    root_path = Path(root).resolve()
    path = receipt_path(root_path, episode)
    payload = load_json(path)
    result: Dict[str, Any] = {
        "status": "block",
        "path": relpath(root_path, path),
        "issues": [],
        "receipt": payload,
    }
    if not payload:
        result["issues"].append("missing or invalid MediaArtifactReceipt")
        return result
    result["issues"].extend(_receipt_structure_issues(payload, episode))
    artifact_payload = payload.get("artifact") if isinstance(payload.get("artifact"), Mapping) else {}
    artifact_rel = str(artifact_payload.get("path") or "")
    artifact = Path(canonical).resolve() if canonical else (root_path / artifact_rel).resolve()
    if not _inside_root(root_path, artifact):
        result["issues"].append("receipt canonical artifact escapes project root")
    elif artifact.suffix.lower() != ".mp4":
        result["issues"].append("receipt canonical artifact is not an MP4 path")
    elif not artifact.is_file():
        result["issues"].append("receipt canonical artifact is missing")
        return result
    if relpath(root_path, artifact) != artifact_rel:
        result["issues"].append("receipt points at a different canonical artifact")
    actual_sha = sha256_file(artifact)
    if actual_sha != str(artifact_payload.get("sha256") or ""):
        result["issues"].append("receipt artifact SHA is stale")
    try:
        receipt_size = int(artifact_payload.get("size_bytes") or 0)
    except (TypeError, ValueError):
        receipt_size = -1
    if artifact.stat().st_size != receipt_size:
        result["issues"].append("receipt artifact size is stale")
    recipe = payload.get("recipe") if isinstance(payload.get("recipe"), dict) else {}
    recipe_rel = str(recipe.get("path") or "")
    recipe_path_abs: Optional[Path] = None
    if recipe_rel:
        recipe_path_abs = (root_path / recipe_rel).resolve()
        if not _inside_root(root_path, recipe_path_abs):
            result["issues"].append("receipt render recipe escapes project root")
        elif not recipe_path_abs.is_file() or sha256_file(recipe_path_abs) != str(recipe.get("sha256") or ""):
            result["issues"].append("receipt render recipe SHA is stale")
        else:
            recipe_payload, recipe_sha, recipe_duration, recipe_issues = _render_recipe(recipe_path_abs, episode)
            result["issues"].extend(recipe_issues)
            spec = payload.get("spec") if isinstance(payload.get("spec"), Mapping) else {}
            if recipe_sha != str(spec.get("timeline_recipe_sha256") or ""):
                result["issues"].append("current recipe SHA differs from receipt spec")
            if str(recipe_payload.get("recipe_sha256") or "") != str(spec.get("timeline_recipe_content_sha256") or ""):
                result["issues"].append("current recipe content SHA differs from receipt spec")
            expected = _positive_float(spec.get("expected_duration_sec"))
            if recipe_duration is None or expected is None or abs(recipe_duration - expected) > 1e-6:
                result["issues"].append("current recipe duration differs from receipt spec")

    spec = payload.get("spec") if isinstance(payload.get("spec"), Mapping) else {}
    if not result["issues"]:
        current_validation = validate_media(artifact, spec, runner=runner, decode_timeout=decode_timeout)
        result["current_validation"] = current_validation
        if current_validation.get("status") != "pass":
            result["issues"].append("current artifact failed shared media revalidation")
    if not result["issues"]:
        result["status"] = "pass"
    result["artifact"] = relpath(root_path, artifact)
    result["artifact_sha256"] = actual_sha
    return result


def _backup_previous(canonical: Path, versions_dir: Path) -> Optional[Path]:
    if not canonical.is_file():
        return None
    previous_sha = sha256_file(canonical)
    versions_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = versions_dir / f"{canonical.stem}.{stamp}.{previous_sha[:12]}{canonical.suffix}"
    try:
        os.link(canonical, backup)
    except OSError:
        shutil.copy2(canonical, backup)
    return backup


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _promotion_lock_path(canonical: Path) -> Path:
    digest = hashlib.sha256(str(canonical.resolve()).encode("utf-8")).hexdigest()[:16]
    return canonical.parent / f".media-promote.{digest}.lock"


def _acquire_promotion_lock(canonical: Path, transaction_id: str) -> tuple[Optional[Path], Dict[str, Any]]:
    """Acquire the canonical-scoped API lock, recovering only provably dead local owners."""
    lock = _promotion_lock_path(canonical)
    lock.parent.mkdir(parents=True, exist_ok=True)
    hostname = socket.gethostname()
    for _attempt in range(2):
        try:
            lock.mkdir()
        except FileExistsError:
            owner = load_json(lock / "owner.json")
            same_host = str(owner.get("hostname") or "") == hostname
            try:
                owner_pid = int(owner.get("pid") or 0)
            except (TypeError, ValueError):
                owner_pid = 0
            if same_host and owner_pid and not _pid_is_alive(owner_pid):
                # No live process can still own this exact local lock.  Remove
                # only its known metadata and empty directory, then retry once.
                try:
                    (lock / "owner.json").unlink(missing_ok=True)
                    lock.rmdir()
                    continue
                except OSError:
                    pass
            return None, {
                "status": "busy",
                "reason": "canonical_promotion_locked",
                "lock": str(lock),
                "owner": owner,
            }
        owner = {
            "kind": "n2d_media_promotion_lock",
            "pid": os.getpid(),
            "hostname": hostname,
            "transaction_id": transaction_id,
            "canonical": str(canonical),
            "acquired_at": now_iso(),
        }
        atomic_write_json(lock / "owner.json", owner)
        return lock, owner
    return None, {"status": "busy", "reason": "canonical_promotion_locked", "lock": str(lock)}


def _release_promotion_lock(lock: Path) -> None:
    try:
        (lock / "owner.json").unlink(missing_ok=True)
        lock.rmdir()
    except OSError:
        # A stale lock is safer than deleting a path whose contents no longer
        # match the lock protocol; the next caller reports its exact owner/path.
        pass


def _promote_candidate_locked(
    root: str | Path,
    episode: str,
    candidate: str | Path,
    canonical: str | Path,
    expected_sha: str,
    spec: Mapping[str, Any],
    *,
    recipe_path: str | Path | None = None,
    transaction_id: str = "",
    runner=subprocess.run,
) -> Dict[str, Any]:
    root_path = Path(root).resolve()
    candidate_path = Path(candidate).resolve()
    canonical_path = Path(canonical).resolve()
    # CAS is deliberately first: a stale render must be rejected before any
    # expensive decode/QC, and must never touch either candidate or canonical.
    current_sha = sha256_file(canonical_path) if canonical_path.is_file() else "missing"
    if str(expected_sha or "missing") != current_sha:
        return {
            "status": "conflict",
            "reason": "compare_and_swap_failed",
            "expected_sha256": str(expected_sha or "missing"),
            "actual_sha256": current_sha,
        }
    recipe = Path(recipe_path).resolve() if recipe_path else None
    if recipe is None:
        return {"status": "block", "reason": "render_recipe_missing", "recipe": ""}
    bound_spec, recipe_issues = _bind_spec_to_recipe(spec, recipe, episode)
    if recipe_issues:
        return {
            "status": "block",
            "reason": "render_recipe_invalid",
            "recipe": str(recipe),
            "issues": recipe_issues,
        }
    validation = validate_media(candidate_path, bound_spec, runner=runner)
    if validation.get("status") != "pass":
        return {"status": "block", "reason": "candidate_validation_failed", "validation": validation}
    candidate_sha = sha256_file(candidate_path)
    candidate_size = candidate_path.stat().st_size
    receipt = _receipt_payload(
        root_path,
        episode,
        canonical_path,
        bound_spec,
        validation,
        recipe_path=recipe,
        transaction_id=transaction_id,
        artifact_sha256=candidate_sha,
        artifact_size_bytes=candidate_size,
    )
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup_previous(canonical_path, canonical_path.parent / "_versions")
    receipt["previous_version"] = relpath(root_path, backup) if backup else ""
    receipt["promotion"] = {
        "method": "atomic_replace",
        "expected_previous_sha256": current_sha,
        "promoted_at": now_iso(),
    }
    try:
        os.replace(candidate_path, canonical_path)
        if sha256_file(canonical_path) != candidate_sha:
            raise OSError("canonical SHA differs after atomic replace")
        receipt_file = write_receipt(root_path, episode, receipt)
    except Exception as exc:
        # Keep the failed candidate available in its staging location, then
        # restore the previous canonical bytes.  The prior receipt was not
        # touched because receipt publication is the final atomic operation.
        try:
            if canonical_path.is_file() and sha256_file(canonical_path) == candidate_sha:
                candidate_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(canonical_path, candidate_path)
            if backup and backup.is_file():
                restore = canonical_path.with_name(f".{canonical_path.name}.restore.{uuid.uuid4().hex[:8]}")
                shutil.copy2(backup, restore)
                os.replace(restore, canonical_path)
        except Exception as rollback_exc:
            return {
                "status": "block",
                "reason": "promotion_failed_rollback_failed",
                "error": str(exc),
                "rollback_error": str(rollback_exc),
                "backup": relpath(root_path, backup) if backup else "",
            }
        return {
            "status": "block",
            "reason": "promotion_failed_rolled_back",
            "error": str(exc),
            "backup": relpath(root_path, backup) if backup else "",
        }
    return {
        "status": "pass",
        "canonical": relpath(root_path, canonical_path),
        "sha256": receipt["artifact"]["sha256"],
        "receipt": relpath(root_path, receipt_file),
        "previous_version": receipt.get("previous_version") or "",
    }


def promote_candidate(
    root: str | Path,
    episode: str,
    candidate: str | Path,
    canonical: str | Path,
    expected_sha: str,
    spec: Mapping[str, Any],
    *,
    recipe_path: str | Path | None = None,
    transaction_id: str = "",
    runner=subprocess.run,
) -> Dict[str, Any]:
    """Promote one candidate under an API-level canonical-scoped lock.

    The lock covers CAS, complete candidate validation, backup, replace,
    receipt commit and rollback.  Shell callers may also hold a coarser episode
    render lock, but correctness never depends on that outer lock.
    """
    canonical_path = Path(canonical).resolve()
    lock, owner = _acquire_promotion_lock(canonical_path, transaction_id)
    if lock is None:
        return owner
    try:
        return _promote_candidate_locked(
            root,
            episode,
            candidate,
            canonical_path,
            expected_sha,
            spec,
            recipe_path=recipe_path,
            transaction_id=transaction_id,
            runner=runner,
        )
    finally:
        _release_promotion_lock(lock)


def _load_spec(ns: argparse.Namespace) -> Dict[str, Any]:
    if getattr(ns, "spec_json", None):
        return load_json(ns.spec_json)
    return default_master_spec(
        width=int(ns.width),
        height=int(ns.height),
        fps=str(ns.fps),
        target_lufs=float(ns.target_lufs) if ns.target_lufs is not None else None,
    )


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    sha = sub.add_parser("sha")
    sha.add_argument("path")
    probe = sub.add_parser("probe")
    probe.add_argument("path")
    validate = sub.add_parser("validate")
    validate.add_argument("path")
    validate.add_argument("--spec-json")
    validate.add_argument("--width", type=int, default=1080)
    validate.add_argument("--height", type=int, default=1920)
    validate.add_argument("--fps", default="30")
    validate.add_argument("--target-lufs", type=float)
    promote = sub.add_parser("promote")
    promote.add_argument("root")
    promote.add_argument("episode")
    promote.add_argument("candidate")
    promote.add_argument("canonical")
    promote.add_argument("--expected-sha", required=True)
    promote.add_argument("--spec-json")
    promote.add_argument("--width", type=int, default=1080)
    promote.add_argument("--height", type=int, default=1920)
    promote.add_argument("--fps", default="30")
    promote.add_argument("--target-lufs", type=float)
    promote.add_argument("--recipe")
    promote.add_argument("--transaction-id", default="")
    current = sub.add_parser("current")
    current.add_argument("root")
    current.add_argument("episode")
    current.add_argument("--canonical")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.command == "sha":
        path = Path(ns.path)
        print(sha256_file(path) if path.is_file() else "missing")
        return 0
    if ns.command == "probe":
        payload = probe_media(ns.path)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if payload.get("available") else 2
    if ns.command == "validate":
        payload = validate_media(ns.path, _load_spec(ns))
    elif ns.command == "promote":
        payload = promote_candidate(
            ns.root,
            ns.episode,
            ns.candidate,
            ns.canonical,
            ns.expected_sha,
            _load_spec(ns),
            recipe_path=ns.recipe,
            transaction_id=ns.transaction_id,
        )
    else:
        payload = current_receipt(ns.root, ns.episode, ns.canonical)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
