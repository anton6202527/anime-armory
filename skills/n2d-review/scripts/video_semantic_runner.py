#!/usr/bin/env python3
"""Generate local DINOv2 video semantic consistency sidecars.

This runner is intentionally separate from ``video_semantic_consistency.py``:
the gate-side checker stays dependency-free, while this script may be run in a
QC environment with torch/transformers installed. It compares sampled video
frames against the first/end frame images recorded in video batch manifests and
writes ``生产数据/video_semantic_consistency_<ep>.json`` for the existing checker.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


CLIP_RE = re.compile(r"(?i)(?:clip|镜头|镜)\s*[_ -]?0*([0-9]+)")
DEFAULT_MODEL = "facebook/dinov2-small"
DEFAULT_SUBJECT_FLOOR = 0.55
DEFAULT_SUBJECT_WARN = 0.63
DEFAULT_BG_FLOOR = 0.45
DEFAULT_BG_WARN = 0.53


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def _clip_label(value: Any, fallback: str = "") -> str:
    text = str(value or "")
    match = CLIP_RE.search(text)
    if match:
        return f"Clip_{int(match.group(1)):02d}"
    return text.strip() or fallback


def _clip_num(label: str) -> Optional[int]:
    match = CLIP_RE.search(label)
    if not match:
        return None
    return int(match.group(1))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _episode_dir(root: Path, ep: str) -> Path:
    return root / "出视频" / ep / "视频"


def _existing_video(root: Path, ep: str, clip: str, target_path: Any = "") -> Optional[Path]:
    candidates: List[Path] = []
    if target_path:
        raw = Path(str(target_path))
        candidates.append(raw if raw.is_absolute() else root / raw)
    token = clip.replace("_", "")
    for path in sorted(_episode_dir(root, ep).glob("*.mp4")):
        name = path.stem.lower().replace("_", "")
        if token.lower() in name:
            candidates.append(path)
    for path in candidates:
        if path.exists() and path.is_file() and path.stat().st_size > 0:
            return path
    return None


def _manifest_items(root: Path, ep: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for path in sorted((root / "生产数据").glob(f"video_batch_{ep}_*.json")):
        data = _load_json(path)
        if not isinstance(data, Mapping):
            continue
        for item in data.get("items") or []:
            if not isinstance(item, Mapping):
                continue
            label = _clip_label(item.get("clip") or item.get("clip_id"))
            if not label:
                continue
            row = dict(item)
            row["_manifest"] = _rel(root, path)
            out[label] = row
    return out


def _storyboard_rows(root: Path, ep: str) -> Dict[str, Dict[str, Any]]:
    data = _load_json(root / "脚本" / ep / "storyboard.json")
    if not isinstance(data, Mapping):
        return {}
    rows: Dict[str, Dict[str, Any]] = {}
    for idx, clip in enumerate(data.get("clips") or [], 1):
        if not isinstance(clip, Mapping):
            continue
        label = _clip_label(clip.get("id") or clip.get("clip_id"), fallback=f"Clip_{idx:02d}")
        rows[label] = dict(clip)
    return rows


def _infer_image(root: Path, ep: str, clip: str, suffix: str = "") -> Optional[Path]:
    num = _clip_num(clip)
    if num is None:
        return None
    image_dir = root / "出图" / ep / "图片"
    if suffix:
        patterns = [f"Clip{num:02d}_*{suffix}.png", f"Clip_{num:02d}_*{suffix}.png"]
    else:
        patterns = [f"Clip{num:02d}_*.png", f"Clip_{num:02d}_*.png"]
    candidates: List[Path] = []
    for pat in patterns:
        candidates.extend(image_dir.glob(pat))
    if not suffix:
        candidates = [p for p in candidates if not p.stem.endswith("_mid") and not p.stem.endswith("_end")]
    return sorted(candidates)[0] if candidates else None


def _image_path(root: Path, item: Mapping[str, Any], ep: str, clip: str, key: str, fallback_suffix: str = "") -> Optional[Path]:
    rel_key = f"{key}_rel"
    for raw in (item.get(rel_key), item.get(key)):
        if not raw:
            continue
        path = Path(str(raw))
        path = path if path.is_absolute() else root / path
        if path.exists() and path.is_file():
            return path
    return _infer_image(root, ep, clip, fallback_suffix)


def _ffprobe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]
    res = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or f"ffprobe failed for {path}")
    try:
        return max(0.0, float(res.stdout.strip()))
    except ValueError as exc:
        raise RuntimeError(f"ffprobe returned invalid duration for {path}: {res.stdout!r}") from exc


def _extract_frame(video: Path, out_path: Path, at_sec: float) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-ss", f"{max(0.0, at_sec):.3f}",
        "-i", str(video),
        "-frames:v", "1",
        "-q:v", "2",
        "-y", str(out_path),
    ]
    res = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError(res.stderr.strip() or f"ffmpeg failed to extract frame from {video}")


def _sample_frames(root: Path, ep: str, clip: str, video: Path, frames_dir: Path) -> Dict[str, str]:
    duration = _ffprobe_duration(video)
    if duration <= 0:
        raise RuntimeError(f"video duration is zero: {video}")
    points = {
        "start": min(0.25, max(0.0, duration * 0.05)),
        "mid": duration * 0.5,
        "end": max(0.0, duration - min(0.35, duration * 0.05)),
    }
    out: Dict[str, str] = {}
    safe_ep = ep.replace("/", "_")
    for name, at_sec in points.items():
        frame = frames_dir / safe_ep / f"{clip}_{name}.jpg"
        _extract_frame(video, frame, at_sec)
        out[name] = _rel(root, frame)
    return out


def _cosine(a: Any, b: Any) -> float:
    import torch

    return float(torch.nn.functional.cosine_similarity(a, b, dim=0).item())


def _load_model(model_name: str):
    import torch
    from transformers import AutoModel
    from torchvision import transforms
    from torchvision.transforms import InterpolationMode

    device = "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu"
    model = AutoModel.from_pretrained(model_name, local_files_only=True)
    model.to(device)
    model.eval()
    preprocess = transforms.Compose([
        transforms.Resize(256, interpolation=InterpolationMode.BICUBIC),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    return model, preprocess, device


def _embed(path: Path, model: Any, preprocess: Any, device: str) -> Any:
    import torch
    from PIL import Image

    image = Image.open(path).convert("RGB")
    tensor = preprocess(image).unsqueeze(0).to(device)
    with torch.inference_mode():
        out = model(pixel_values=tensor)
        vec = out.last_hidden_state[:, 0, :].squeeze(0).detach().cpu()
    return torch.nn.functional.normalize(vec, dim=0)


def _mean(values: Sequence[float]) -> float:
    nums = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    return round(sum(nums) / len(nums), 4) if nums else 0.0


def _verdict(subject: float, background: float) -> str:
    if subject < DEFAULT_SUBJECT_FLOOR or background < DEFAULT_BG_FLOOR:
        return "block"
    if subject < DEFAULT_SUBJECT_WARN or background < DEFAULT_BG_WARN:
        return "warn"
    return "ok"


def build_report(root: Path, ep: str, *, model_name: str, frames_dir: Path) -> Dict[str, Any]:
    items = _manifest_items(root, ep)
    storyboard = _storyboard_rows(root, ep)
    model, preprocess, device = _load_model(model_name)
    embedding_cache: Dict[Path, Any] = {}

    def emb(path: Path) -> Any:
        key = path.resolve()
        if key not in embedding_cache:
            embedding_cache[key] = _embed(key, model, preprocess, device)
        return embedding_cache[key]

    segments: List[Dict[str, Any]] = []
    frame_manifest: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    labels = sorted(set(items) | set(storyboard), key=lambda x: _clip_num(x) or 9999)
    for label in labels:
        item = items.get(label, {})
        video = _existing_video(root, ep, label, item.get("target_path") or item.get("video_path"))
        if video is None:
            continue
        start_image = _image_path(root, item, ep, label, "image")
        end_image = _image_path(root, item, ep, label, "end_image", "_end")
        if start_image is None:
            skipped.append({"clip": label, "reason": "missing_start_image", "video": _rel(root, video)})
            continue
        try:
            frames = _sample_frames(root, ep, label, video, frames_dir)
            start_frame = root / frames["start"]
            mid_frame = root / frames["mid"]
            end_frame = root / frames["end"]
            start_sim = _cosine(emb(start_image), emb(start_frame))
            mid_sims: List[float] = [_cosine(emb(start_image), emb(mid_frame))]
            end_sims: List[float] = []
            if end_image is not None:
                end_sims.append(_cosine(emb(end_image), emb(end_frame)))
                mid_sims.append(_cosine(emb(end_image), emb(mid_frame)))
            else:
                end_sims.append(_cosine(emb(start_image), emb(end_frame)))
            # VSEM is an endpoint contract check. Mid-clip frames may be valid
            # cutaways/montage beats, so keep their nearest-reference similarity
            # as evidence but do not let it auto-fail the endpoint score.
            subject_similarity = round(min([start_sim, end_sims[0]]), 4)
            background_similarity = _mean([start_sim] + end_sims)
            status = _verdict(subject_similarity, background_similarity)
            row = {
                "clip": label,
                "status": status,
                "subject_similarity": subject_similarity,
                "background_similarity": background_similarity,
                "start_frame_similarity": round(start_sim, 4),
                "mid_frame_nearest_reference_similarity": round(max(mid_sims), 4),
                "end_frame_similarity": round(end_sims[0], 4),
                "video": _rel(root, video),
                "reference_images": {
                    "start": _rel(root, start_image),
                    "end": _rel(root, end_image) if end_image else "",
                },
                "sampled_frames": frames,
                "video_sha256": _sha256(video),
                "reference_sha256": {
                    "start": _sha256(start_image),
                    "end": _sha256(end_image) if end_image else "",
                },
            }
            if status != "ok":
                row["message"] = "DINOv2 whole-frame similarity is below the configured VSEM threshold."
            segments.append(row)
            frame_manifest.append({
                "clip": label,
                "video": _rel(root, video),
                "sampled_frames": frames,
                "reference_images": row["reference_images"],
            })
        except Exception as exc:
            skipped.append({"clip": label, "reason": type(exc).__name__, "message": str(exc), "video": _rel(root, video)})

    return {
        "kind": "n2d_video_semantic_consistency",
        "version": 1,
        "episode": ep,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "runner": "skills/n2d-review/scripts/video_semantic_runner.py",
        "embedding_model": model_name,
        "embedding_method": "dinov2_cls_whole_frame",
        "device": device,
        "subject_similarity_floor": DEFAULT_SUBJECT_FLOOR,
        "subject_similarity_warn": DEFAULT_SUBJECT_WARN,
        "background_similarity_floor": DEFAULT_BG_FLOOR,
        "background_similarity_warn": DEFAULT_BG_WARN,
        "segments": segments,
        "skipped": skipped,
        "frame_sample_manifest": frame_manifest,
        "notes": [
            "DINOv2 whole-frame embeddings are a local semantic/perceptual proxy for video-vs-reference drift.",
            "This does not replace human review for face identity, dialogue, or fine-grained object state.",
        ],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Generate video_semantic_consistency sidecar with local DINOv2 embeddings.")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--frames-dir", default=None, help="Frame evidence directory; default: <root>/生产数据/video_semantic_frames")
    ap.add_argument("--write", action="store_true", help="Write 生产数据/video_semantic_consistency_<episode>.json")
    ap.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    frames_dir = Path(ns.frames_dir) if ns.frames_dir else root / "生产数据" / "video_semantic_frames"
    report = build_report(root, ns.episode, model_name=ns.model, frames_dir=frames_dir)
    if ns.write:
        out = root / "生产数据" / f"video_semantic_consistency_{ns.episode}.json"
        _write_json(out, report)
        if not ns.json:
            print(out)
    if ns.json or not ns.write:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
