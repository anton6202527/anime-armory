#!/usr/bin/env python3
"""Extract real final-video evidence for product/character/scene/prop review.

The script samples first/middle/last frames from every shot clip and every
rendered deliverable, then builds per-asset contact sheets.  dHash is advisory
only; semantic identity is deliberately left to named human review whose
evidence is bound by human_signoff.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping


KIND = "ad_final_media_consistency"
SCHEMA_VERSION = 1
ASSET_RE = re.compile(r"\b(?:PROD|BRAND|CHAR|LOC|PROP)_[A-Za-z0-9_]+\b")
CATEGORY = {"PROD": "product", "BRAND": "product", "CHAR": "character", "LOC": "scene", "PROP": "prop"}


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _duration(path: Path):
    exe = shutil.which("ffprobe")
    if not exe or not path.is_file():
        return None
    proc = subprocess.run([exe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                          capture_output=True, text=True)
    try:
        value = float(proc.stdout.strip())
        return value if proc.returncode == 0 and value > 0 else None
    except ValueError:
        return None


def _extract(path: Path, at: float, out: Path):
    exe = shutil.which("ffmpeg")
    if not exe:
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([exe, "-y", "-v", "error", "-ss", f"{max(0.0, at):.3f}", "-i", str(path),
                           "-frames:v", "1", str(out)], capture_output=True)
    return proc.returncode == 0 and out.is_file() and out.stat().st_size > 0


def _assets(shot: Mapping[str, Any]):
    raw = shot.get("assets") or {}
    values = []
    if isinstance(raw, Mapping):
        values.extend(str(key) for key, used in raw.items() if used)
    elif isinstance(raw, list):
        values.extend(str(v) for v in raw)
    text = json.dumps(shot, ensure_ascii=False)
    values.extend(ASSET_RE.findall(text))
    return sorted({value for value in values if ASSET_RE.fullmatch(value)})


def _shot_label(shot: Mapping[str, Any], pos: int):
    raw = str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or "")
    match = re.search(r"\d+", raw)
    return f"镜头{int(match.group()):02d}" if match else f"镜头{pos:02d}"


def _shot_id(shot: Mapping[str, Any], pos: int):
    return str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or f"S{pos:02d}")


def _deliverable_shots(root: Path, item: Mapping[str, Any], shots):
    """Return ordered shot rows represented by a rendered deliverable."""
    if item.get("kind") != "cutdown":
        return shots, True
    duration = str(item.get("duration") or "")
    safe = re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", duration).strip("_")
    candidates = [root / "合成" / "cutdown" / f"plan_{duration}.json",
                  root / "合成" / "cutdown" / f"plan_{safe}.json"]
    plan = next((load(path, {}) for path in candidates if path.is_file()), {}) or {}
    kept = [str(value) for value in plan.get("kept_shots") or []]
    if not kept:
        return [], False
    by_id = {_shot_id(row, pos): row for pos, row in enumerate(shots, 1)}
    return [by_id[sid] for sid in kept if sid in by_id], True


def _load_image_tools():
    try:
        from PIL import Image, ImageDraw  # type: ignore
        return Image, ImageDraw
    except Exception:
        return None, None


def _dhash(path: Path, Image):
    try:
        image = Image.open(path).convert("L").resize((9, 8))
        pixels = list(image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata())
        bits = 0
        for y in range(8):
            for x in range(8):
                bits = (bits << 1) | (pixels[y * 9 + x] < pixels[y * 9 + x + 1])
        return bits
    except Exception:
        return None


def _sheet(root: Path, asset_id: str, rows, Image, ImageDraw):
    loaded = []
    for row in rows:
        path = root / row["path"]
        try:
            image = Image.open(path).convert("RGB")
            image.thumbnail((320, 180))
            loaded.append((row, image.copy()))
        except Exception:
            continue
    if not loaded:
        return None
    cols = min(3, len(loaded)); cell_h = 212
    canvas = Image.new("RGB", (320 * cols, cell_h * ((len(loaded) + cols - 1) // cols)), "white")
    draw = ImageDraw.Draw(canvas)
    for pos, (row, image) in enumerate(loaded):
        x, y = (pos % cols) * 320, (pos // cols) * cell_h
        canvas.paste(image, (x, y))
        draw.text((x + 4, y + 184), f"{row['source_id']} {row['sample']}", fill="black")
    safe = re.sub(r"[^A-Za-z0-9_.\-]+", "_", asset_id)
    out = root / "生产数据" / "final_media_contact_sheets" / f"{safe}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=90)
    return {"path": out.relative_to(root).as_posix(), "sha256": sha(out), "frames": len(loaded)}


def build(root: Path, *, write_frames=True):
    root = root.resolve()
    storyboard = load(root / "脚本" / "storyboard.json", {}) or {}
    plan = load(root / "合成" / "delivery_plan.json", {}) or {}
    Image, ImageDraw = _load_image_tools()
    findings = []
    frames = []
    by_asset: dict[str, list[dict[str, Any]]] = {}
    source_media = []
    shots = [row for row in (storyboard.get("shots") or storyboard.get("clips") or []) if isinstance(row, Mapping)]
    for pos, shot in enumerate(shots, 1):
        label = _shot_label(shot, pos)
        path = root / "出视频" / "分镜" / "视频" / f"{label}.mp4"
        aids = _assets(shot)
        if not path.is_file():
            findings.append({"severity": "block", "code": "final_clip_missing", "msg": f"缺最终 clip：{path.relative_to(root)}"})
            continue
        source_media.append({"source_id": label, "path": path.relative_to(root).as_posix(), "sha256": sha(path)})
        duration = _duration(path)
        if duration is None:
            findings.append({"severity": "block", "code": "final_clip_unprobeable", "msg": f"无法实测 {label} 时长"})
            continue
        for name, ratio in (("first", 0.05), ("middle", 0.5), ("last", 0.95)):
            rel = Path("生产数据") / "final_media_frames" / label / f"{name}.jpg"
            target = root / rel
            ok = _extract(path, duration * ratio, target) if write_frames else target.is_file()
            if not ok:
                findings.append({"severity": "block", "code": "final_frame_extract_failed", "msg": f"{label} {name} 抽帧失败"})
                continue
            row = {"source_id": label, "sample": name, "path": rel.as_posix(), "sha256": sha(target), "asset_ids": aids}
            frames.append(row)
            for aid in aids:
                by_asset.setdefault(aid, []).append(row)
    deliverables = []
    for item in plan.get("deliverables") or []:
        if item.get("status") == "cancelled":
            continue
        did = str(item.get("deliverable_id") or "")
        path = root / str(item.get("expected_path") or "")
        duration = _duration(path)
        deliverables.append({"deliverable_id": did, "path": str(item.get("expected_path") or ""),
                             "sha256": sha(path), "duration": duration})
        if duration is None:
            findings.append({"severity": "block", "code": "deliverable_unprobeable", "msg": f"无法抽查交付件 {did}"})
            continue
        represented, mapping_ok = _deliverable_shots(root, item, shots)
        if not mapping_ok:
            findings.append({"severity": "block", "code": "cutdown_shot_mapping_missing",
                             "msg": f"{did} 缺 cutdown kept_shots，无法把最终编码帧绑定到资产"})
        planned = [max(0.0, float(row.get("duration") or row.get("duration_sec") or 0)) for row in represented]
        total = sum(planned)
        if represented and total <= 0:
            findings.append({"severity": "block", "code": "deliverable_shot_timing_missing",
                             "msg": f"{did} 镜头时长无效，无法从最终编码文件按镜抽帧"})
        cursor = 0.0
        for pos, (shot, planned_duration) in enumerate(zip(represented, planned), 1):
            sid = _shot_id(shot, pos)
            start = duration * cursor / total if total > 0 else 0.0
            end = duration * (cursor + planned_duration) / total if total > 0 else 0.0
            cursor += planned_duration
            aids = _assets(shot)
            for name, ratio in (("first", 0.05), ("middle", 0.5), ("last", 0.95)):
                rel = Path("生产数据") / "final_media_frames" / "deliverables" / did / sid / f"{name}.jpg"
                target = root / rel
                ok = _extract(path, start + (end - start) * ratio, target) if write_frames else target.is_file()
                if not ok:
                    findings.append({"severity": "block", "code": "deliverable_shot_frame_extract_failed",
                                     "msg": f"{did}/{sid} {name} 抽帧失败"})
                    continue
                frame_row = {"source_id": f"{did}:{sid}", "sample": name, "path": rel.as_posix(),
                             "sha256": sha(target), "asset_ids": aids, "media_level": "final_deliverable"}
                frames.append(frame_row)
                for aid in aids:
                    by_asset.setdefault(aid, []).append(frame_row)
        for name, ratio in (("first", 0.05), ("middle", 0.5), ("last", 0.95)):
            rel = Path("生产数据") / "final_media_frames" / "deliverables" / did / f"{name}.jpg"
            target = root / rel
            ok = _extract(path, duration * ratio, target) if write_frames else target.is_file()
            if ok:
                frames.append({"source_id": did, "sample": name, "path": rel.as_posix(), "sha256": sha(target),
                               "asset_ids": [], "media_level": "final_deliverable_global"})
            else:
                findings.append({"severity": "block", "code": "deliverable_frame_extract_failed", "msg": f"{did} {name} 抽帧失败"})
    sheets = {}
    if Image is None:
        findings.append({"severity": "block", "code": "contact_sheet_dependency_missing", "msg": "缺 Pillow，不能生成最终媒体并排证据"})
    else:
        for aid, rows in by_asset.items():
            result = _sheet(root, aid, rows, Image, ImageDraw) if write_frames else None
            if result is None:
                findings.append({"severity": "block", "code": "asset_contact_sheet_missing", "msg": f"{aid} 无最终媒体 contact sheet"})
                continue
            sheets[aid] = {**result, "category": CATEGORY.get(aid.split("_", 1)[0], "asset")}
            hashes = [_dhash(root / row["path"], Image) for row in rows]
            valid = [value for value in hashes if value is not None]
            max_distance = max(((a ^ b).bit_count() for i, a in enumerate(valid) for b in valid[i + 1:]), default=0)
            if max_distance > 30:
                findings.append({"severity": "warn", "code": "final_asset_visual_drift", "asset_id": aid,
                                 "msg": f"{aid} 最终视频样帧全帧 dHash 最大差 {max_distance}bit；仅提示具名并排复核",
                                 "confidence": "heuristic", "contact_sheet": result["path"]})
    categories = {}
    for aid, row in sheets.items():
        categories.setdefault(row["category"], []).append(aid)
    return {
        "schema_version": SCHEMA_VERSION, "kind": KIND,
        "qc_environment": {"ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")),
                           "pillow": Image is not None, "precision_level": "full" if all((shutil.which("ffmpeg"), shutil.which("ffprobe"), Image)) else "structural"},
        "source_media": source_media, "deliverables": deliverables, "frames": frames,
        "assets": {aid: {"category": CATEGORY.get(aid.split("_", 1)[0], "asset"),
                         "frame_count": len(rows), "contact_sheet": sheets.get(aid)} for aid, rows in by_asset.items()},
        "categories": categories, "manual_review_required": sorted(categories),
        "findings": findings,
        "summary": {"block": sum(f["severity"] == "block" for f in findings),
                    "warn": sum(f["severity"] == "warn" for f in findings)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="extract final ad media contact sheets")
    ap.add_argument("project_root")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    payload = build(root, write_frames=True)
    out = root / "生产数据" / "final_media_consistency.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# final media consistency block={payload['summary']['block']} warn={payload['summary']['warn']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
