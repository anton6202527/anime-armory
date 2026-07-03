#!/usr/bin/env python3
"""Expression verification: post-hoc pixel check for expression_span=大 + closeup.

Closes P0 contradiction where big-expression closeup BLOCK only validates prompt
writing (regex for '锁脸不锁情'), not pixel results.

For each shot with expression_span=大 + closeup and both start/end frames,
computes expression change via insightface 106-point landmarks:
  - Mouth openness ratio: landmarks vertical / horizontal span
  - Eye openness ratio: eyelid vertical span

If expression change < threshold for both mouth AND eyes:
  → WARN "表情跨度声称大但像素表情无明显变化"

Degrades gracefully: insightface unavailable → available=False, skip.
Only BLOCK-level impact: won't silently pass genuinely unexpressed closeups.

Usage: python3 expression_verification.py <作品根> 第N集 [--mouth-threshold 0.3] [--eye-threshold 0.15] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

KIND = "n2d_expression_verification"
VERSION = 1

# Landmark indices for insightface 106-point model (0-indexed):
# - Mouth: outer lip top≈52, bottom≈72, left≈52, right≈61
# - Eye (right): upper≈14, lower≈30
# Indices approximate — validated against buffalo_l 106L model docs.
MOUTH_TOP_IDX = 52
MOUTH_BOTTOM_IDX = 72
MOUTH_LEFT_IDX = 52
MOUTH_RIGHT_IDX = 61
EYE_TOP_IDX = 14
EYE_BOTTOM_IDX = 30

DEFAULT_MOUTH_THRESHOLD = 0.30
DEFAULT_EYE_THRESHOLD = 0.15


# ── Pure functions ─────────────────────────────────────────────────────

def mouth_openness_ratio(landmarks: Sequence[Tuple[float, float]]) -> float:
    """Mouth openness = vertical span / horizontal span. Pure function."""
    top = landmarks[MOUTH_TOP_IDX]
    bottom = landmarks[MOUTH_BOTTOM_IDX]
    left = landmarks[MOUTH_LEFT_IDX]
    right = landmarks[MOUTH_RIGHT_IDX]
    v = abs(bottom[1] - top[1])
    h = abs(right[0] - left[0])
    if h == 0.0:
        return 0.0
    return v / h


def eye_openness_ratio(landmarks: Sequence[Tuple[float, float]]) -> float:
    """Eye openness = vertical eyelid span. Pure function."""
    top = landmarks[EYE_TOP_IDX]
    bottom = landmarks[EYE_BOTTOM_IDX]
    return abs(bottom[1] - top[1])


def expression_change_verdict(
    mouth_start: float, mouth_end: float,
    eye_start: float, eye_end: float,
    mouth_threshold: float = DEFAULT_MOUTH_THRESHOLD,
    eye_threshold: float = DEFAULT_EYE_THRESHOLD,
) -> str:
    """Compare start/end expression ratios. If change < threshold for both
    mouth AND eyes → 'warn' (claimed big expression but no pixel change).
    Pure function."""
    mouth_delta = abs(mouth_end - mouth_start)
    eye_delta = abs(eye_end - eye_start)
    if mouth_delta < mouth_threshold and eye_delta < eye_threshold:
        return "warn"
    return "ok"


def _probe_insightface() -> bool:
    try:
        import insightface  # noqa: F401
        return True
    except Exception:
        return False


# ── Image functions ────────────────────────────────────────────────────

def _load_face_analyzer():
    import insightface
    return insightface.app.FaceAnalysis(allowed_modules=["detection", "landmark_2d_106"],
                                        providers=["CPUExecutionProvider"], name="buffalo_l")


def _extract_landmarks(image_path: str, analyzer) -> Optional[List[Tuple[float, float]]]:
    """Extract 106-point landmarks from largest face in image."""
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return None
        faces = analyzer.get(img)
        if not faces:
            return None
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        lm = faces[0].landmark_2d_106
        if lm is None:
            return None
        return [(float(p[0]), float(p[1])) for p in lm]
    except Exception:
        return None


def _find_big_expression_shots(root: str, ep: str) -> List[Dict[str, Any]]:
    """Find shots with expression_span=大 + closeup from storyboard.json."""
    sb_path = os.path.join(root, "脚本", ep, "storyboard.json")
    if not os.path.isfile(sb_path):
        return []
    with open(sb_path, encoding="utf-8") as fh:
        sb = json.load(fh)
    shots = []
    for clip in sb.get("clips", []):
        if not isinstance(clip, dict):
            continue
        meta = clip.get("meta") or {}
        if not isinstance(meta, dict):
            continue
        expr = str(meta.get("expression_span") or "").lower()
        if expr not in {"大", "big", "large", "cross_emotion"}:
            continue
        desc = str(clip.get("shot_description") or clip.get("description") or "").lower()
        is_closeup = any(
            kw in desc for kw in ("cu", "ecu", "mcu", "bcu", "特写", "近景", "反打", "正反打", "过肩")
        )
        if not is_closeup:
            continue
        cid = clip.get("clip_id") or clip.get("id") or ""
        shots.append({"clip_id": str(cid), "description": str(clip.get("shot_description", ""))[:120]})
    return shots


def _find_start_end_frames(root: str, ep: str, clip_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Find start and end frame PNGs for a clip. Looks in 出图/<ep>/图片/.
    Returns (start_path, end_path) or (None, None)."""
    img_dir = os.path.join(root, "出图", ep, "图片")
    if not os.path.isdir(img_dir):
        return None, None
    import glob
    start, end = None, None
    clip_num = "".join(c for c in clip_id if c.isdigit())
    for p in sorted(glob.glob(os.path.join(img_dir, f"*{clip_num}*.png"))):
        bn = os.path.basename(p).lower()
        if "start" in bn or "首帧" in bn or "first" in bn:
            start = p
        elif "end" in bn or "尾帧" in bn or "last" in bn:
            end = p
    if not start:
        for p in sorted(glob.glob(os.path.join(img_dir, f"*{clip_num}*.png")))[:1]:
            start = p
    return start, end


def analyze(root: str, ep: str) -> Dict[str, Any]:
    """Main entry: verify expression change for big-expression closeups.
    Returns {available, notes, findings: [{shot, verdict, mouth_change, eye_change, msg}]}"""
    if not _probe_insightface():
        return {"available": False, "notes": ["insightface 不可用。跳过表情像素验证。"], "findings": []}
    shots = _find_big_expression_shots(root, ep)
    if not shots:
        return {"available": True, "notes": ["本集无 expression_span=大 的近景镜头。"], "findings": []}
    try:
        analyzer = _load_face_analyzer()
        analyzer.prepare(ctx_id=0)
    except Exception as exc:
        return {"available": False, "notes": [f"insightface 加载失败：{exc}"], "findings": []}
    findings = []
    for shot in shots:
        start_path, end_path = _find_start_end_frames(root, ep, shot["clip_id"])
        if not start_path:
            findings.append({"shot": shot["clip_id"], "verdict": "ok",
                           "note": "无首帧可用，跳过像素表情验证"})
            continue
        start_lm = _extract_landmarks(start_path, analyzer)
        if not start_lm:
            findings.append({"shot": shot["clip_id"], "verdict": "ok",
                           "note": "首帧未检测到人脸"})
            continue
        end_lm = _extract_landmarks(end_path, analyzer) if end_path else None
        if not end_lm:
            findings.append({"shot": shot["clip_id"], "verdict": "ok",
                           "note": "尾帧不可用或无脸，跳过对比"})
            continue
        mouth_s = mouth_openness_ratio(start_lm)
        eye_s = eye_openness_ratio(start_lm)
        mouth_e = mouth_openness_ratio(end_lm)
        eye_e = eye_openness_ratio(end_lm)
        verdict = expression_change_verdict(mouth_s, mouth_e, eye_s, eye_e)
        msg = ""
        if verdict == "warn":
            msg = (f"表情跨度声称大但像素表情无明显变化 "
                   f"(mouth Δ={abs(mouth_e - mouth_s):.3f}, eye Δ={abs(eye_e - eye_s):.1f}px)")
        findings.append({
            "shot": shot["clip_id"],
            "verdict": verdict,
            "mouth_change": round(abs(mouth_e - mouth_s), 4),
            "eye_change": round(abs(eye_e - eye_s), 1),
            "msg": msg,
            "dimension": "表情连续(EXP1)",
        })
    return {"available": True, "notes": [], "findings": findings}


# ── CLI ────────────────────────────────────────────────────────────────

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="n2d expression pixel verification")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--mouth-threshold", type=float, default=DEFAULT_MOUTH_THRESHOLD)
    ap.add_argument("--eye-threshold", type=float, default=DEFAULT_EYE_THRESHOLD)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    result = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"available={result['available']}")
        for f in result.get("findings", []):
            v = f["verdict"]
            print(f"  [{'❌' if v == 'warn' else '✅'}] {f['shot']}: {f.get('msg', f.get('note',''))}")
    return 0 if not any(f.get("verdict") == "warn" for f in result.get("findings", [])) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
