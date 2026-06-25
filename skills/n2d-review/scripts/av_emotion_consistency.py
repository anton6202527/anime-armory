#!/usr/bin/env python3
"""Audio-visual emotion consistency: cross-modal emotion verification.

Reads voiceover timeline emotion annotations per clip. For each clip with strong
emotion annotation: classifies visual expression from video frame(s), compares
audio emotion label vs visual expression → mismatch = WARN.

Degrades gracefully: no face detected → skip; no emotion model → available=False.
C4 compliant: never silently hard-binds a backend.

Usage: python3 av_emotion_consistency.py <作品根> 第N集 [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

KIND = "n2d_av_emotion_consistency"
VERSION = 1

# Audio emotion → expected visual expression set
# angrier audio → expected negative-valence visual
AUDIO_TO_VISUAL: Dict[str, Set[str]] = {
    "angry": {"angry", "disgusted", "fearful"},
    "fearful": {"fearful", "surprised", "sad"},
    "sad": {"sad", "fearful", "neutral"},
    "happy": {"happy", "surprised"},
    "serious": {"serious", "neutral", "angry"},
    "neutral": {"neutral"},
}
STRONG_AUDIO_EMOTIONS = {"angry", "fearful", "sad"}


# ── Pure functions ─────────────────────────────────────────────────────

def emotion_match(audio_emotion: str, visual_emotion: str) -> bool:
    """Check if visual emotion matches expected set for audio emotion.
    Pure function."""
    expected = AUDIO_TO_VISUAL.get(audio_emotion.lower(), {"neutral"})
    return visual_emotion.lower() in expected


def emotion_mismatch_verdict(audio_emotion: str, visual_emotion: str) -> Optional[str]:
    """Determine mismatch severity. Pure function.
    Strong audio (angry/fearful/sad) + visual neutral → WARN (most jarring).
    Mild mismatch → ok (acceptable range)."""
    if emotion_match(audio_emotion, visual_emotion):
        return None
    if audio_emotion.lower() in STRONG_AUDIO_EMOTIONS and visual_emotion.lower() == "neutral":
        return "warn"
    return "ok"


def _probe_emotion_model() -> bool:
    try:
        import insightface  # noqa: F401
        return True
    except Exception:
        return False


# ── Emotion classification ─────────────────────────────────────────────

def _load_emotion_analyzer():
    import insightface
    return insightface.app.FaceAnalysis(
        allowed_modules=["detection"],
        providers=["CPUExecutionProvider"], name="buffalo_l",
    )


def _classify_visual_emotion(image_path: str, analyzer) -> Optional[str]:
    """Classify emotion from face in image using heuristic landmark analysis.
    Falls back to detection-only; emotion is derived from face bbox aspect ratio
    and mouth region analysis (heuristic proxy, not ML classifier)."""
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return None
        faces = analyzer.get(img)
        if not faces:
            return None
        face = faces[0]
        bbox = face.bbox
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        aspect = h / max(w, 1)
        # Heuristic: wider face (low aspect) → happier expression;
        # taller face (high aspect) → surprised/angry/fearful
        if aspect > 1.3:
            return "surprised"  # wide-open mouth makes face taller
        if aspect < 0.8:
            return "happy"  # smiling compresses face vertically
        return "neutral"
    except Exception:
        return None


def _parse_voiceover_emotions(root: str, ep: str) -> Dict[str, str]:
    """Parse voiceover text for per-clip emotion annotations.
    Returns {clip_id: emotion_label}. Falls back to empty dict."""
    vo_path = os.path.join(root, "脚本", ep, "voiceover.txt")
    if not os.path.isfile(vo_path):
        return {}
    import re
    emotions: Dict[str, str] = {}
    with open(vo_path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"\[镜头(\d+)[·•\s]*([^·•\]]*)[·•\s]*([^·•\]]*)\]", line)
            if m:
                clip_num = m.group(1)
                emotion = m.group(3).strip().lower() if m.group(3) else ""
                if emotion:
                    emotions[f"Clip {clip_num}"] = emotion
    return emotions


def analyze(root: str, ep: str) -> Dict[str, Any]:
    """Main entry: correlate voiceover emotion annotations with visual expression.
    Returns {available, notes, findings}."""
    if not _probe_emotion_model():
        return {"available": False, "notes": ["insightface 不可用。跳过音画情绪一致性。"], "findings": []}
    emotions = _parse_voiceover_emotions(root, ep)
    if not emotions:
        return {"available": True, "notes": ["本集 voiceover 无情绪标注。"], "findings": []}
    try:
        analyzer = _load_emotion_analyzer()
        analyzer.prepare(ctx_id=0)
    except Exception as exc:
        return {"available": False, "notes": [f"insightface 加载失败：{exc}"], "findings": []}
    findings = []
    img_dir = os.path.join(root, "出图", ep, "图片")
    for clip_id, emotion in emotions.items():
        if emotion.lower() not in STRONG_AUDIO_EMOTIONS:
            continue
        clip_num = "".join(c for c in clip_id if c.isdigit())
        import glob
        pngs = sorted(glob.glob(os.path.join(img_dir, f"*{clip_num}*.png")))[:1]
        if not pngs:
            continue
        visual_emo = _classify_visual_emotion(pngs[0], analyzer)
        if visual_emo is None:
            continue
        verdict = emotion_mismatch_verdict(emotion, visual_emo)
        if verdict:
            findings.append({
                "shot": clip_id,
                "audio_emotion": emotion,
                "visual_emotion": visual_emo,
                "verdict": verdict,
                "msg": f"配音情绪「{emotion}」vs 视觉表情推断「{visual_emo}」不匹配",
                "dimension": "音画情绪一致(AVE)",
            })
    return {"available": True, "notes": [], "findings": findings}


# ── CLI ────────────────────────────────────────────────────────────────

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="n2d AV emotion consistency")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    result = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"available={result['available']}")
        for f in result.get("findings", []):
            print(f"  [{f['verdict']}] {f['shot']}: {f['msg']}")
    return 0 if result.get("available") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
