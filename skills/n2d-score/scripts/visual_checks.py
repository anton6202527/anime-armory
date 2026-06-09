#!/usr/bin/env python3
"""Visual-facing checks for n2d-score.

This script intentionally keeps heavyweight detectors optional.  It always
emits JSON; missing Pillow / OCR / ffmpeg / lip-sync reports are represented as
skipped sections so the score can distinguish "not checked" from "passed".
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import SCORE_VISUAL_CHECKS_KIND  # noqa: E402  产物 kind 单一真值源
from n2d_route import manifest_path, normalize_episode  # noqa: E402  集号/清单路径单一真值源

KIND = SCORE_VISUAL_CHECKS_KIND
VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def section(name: str) -> Dict[str, Any]:
    return {"name": name, "available": True, "skipped": False, "blocks": 0, "warnings": 0, "infos": 0, "evidence": [], "metrics": {}}


def mark_skip(sec: Dict[str, Any], msg: str) -> Dict[str, Any]:
    sec["available"] = False
    sec["skipped"] = True
    sec["evidence"].append(msg)
    return sec


def rel_path(root: str, path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return path if os.path.isabs(path) else os.path.join(root, path)


def load_json(path: str) -> Optional[Any]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def load_storyboard(root: str, ep: str) -> Optional[Dict[str, Any]]:
    data = load_json(storyboard_path(root, ep))
    return data if isinstance(data, dict) else None


def ffprobe_duration(path: str) -> Optional[float]:
    if not os.path.isfile(path) or not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", path],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(out)
        return float((data.get("format") or {}).get("duration"))
    except Exception:
        return None


def final_video_candidates(root: str, ep: str) -> List[str]:
    patterns = [
        os.path.join(root, "合成", ep, f"*成片*{ep}*.mp4"),
        os.path.join(root, "合成", ep, "成片*.mp4"),
        os.path.join(root, "出视频", ep, "成片*.mp4"),
        os.path.join(root, f"*成片*{ep}*.mp4"),
    ]
    seen: Dict[str, None] = {}
    for pat in patterns:
        for path in glob.glob(pat):
            seen[path] = None
    return sorted(seen)


def voice_candidates(root: str, ep: str) -> List[str]:
    patterns = [
        os.path.join(root, "合成", ep, "配音", "voice_*.wav"),
        os.path.join(root, "合成", ep, "配音", "voice.wav"),
        os.path.join(root, "出视频", ep, "配音", "voice_*.wav"),
        os.path.join(root, "出视频", ep, "配音", "voice.wav"),
    ]
    seen: Dict[str, None] = {}
    for pat in patterns:
        for path in glob.glob(pat):
            seen[path] = None
    return list(seen)


def tc_to_sec(text: str) -> float:
    h, m, rest = text.strip().split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    raw = open(path, encoding="utf-8").read().strip()
    cues: List[Dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [line for line in block.splitlines() if line.strip()]
        idx = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if idx is None:
            continue
        try:
            start, end = [part.strip() for part in lines[idx].split("-->", 1)]
            cues.append({"start": tc_to_sec(start), "end": tc_to_sec(end), "text": "\n".join(lines[idx + 1:])})
        except Exception:
            continue
    return cues


def srt_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "字幕_中文.srt")


def normalize_text(text: str) -> str:
    return re.sub(r"[\s，。！？、,.!?;:：；'\"“”‘’《》<>（）()\[\]【】—-]+", "", text or "").lower()


def text_match(expected: str, actual: str) -> bool:
    exp = normalize_text(expected)
    got = normalize_text(actual)
    if not exp:
        return True
    if not got:
        return False
    if exp in got or got in exp:
        return True
    window = 4 if len(exp) >= 4 else max(2, len(exp))
    return any(exp[i:i + window] in got for i in range(0, max(1, len(exp) - window + 1)))


def hamming(a: int, b: int) -> int:
    return int((a ^ b).bit_count())


def dhash(path: str) -> Optional[int]:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    try:
        img = Image.open(path).convert("L").resize((9, 8))
        vals = list(img.getdata())
        bits = 0
        for y in range(8):
            for x in range(8):
                bits = (bits << 1) | (1 if vals[y * 9 + x] > vals[y * 9 + x + 1] else 0)
        return bits
    except Exception:
        return None


def check_image_similarity(root: str, ep: str) -> Dict[str, Any]:
    sec = section("image_similarity")
    sb = load_storyboard(root, ep)
    if not sb:
        return mark_skip(sec, "缺 storyboard.json，无法比对尾帧与下一首帧")
    clips = [c for c in sb.get("clips", []) if isinstance(c, dict)]
    pairs: List[Tuple[str, str, str]] = []
    for prev, nxt in zip(clips, clips[1:]):
        endp = ((prev.get("continuity") or {}) if isinstance(prev.get("continuity"), dict) else {}).get("endframe_png")
        firstp = nxt.get("firstframe_png")
        a = rel_path(root, endp)
        b = rel_path(root, firstp)
        if a and b and os.path.isfile(a) and os.path.isfile(b):
            pairs.append((str(prev.get("label") or prev.get("id") or "?"), a, b))
    if not pairs:
        return mark_skip(sec, "没有可比对的 endframe_png -> next firstframe_png 图片对")
    distances = []
    for label, a, b in pairs:
        ha, hb = dhash(a), dhash(b)
        if ha is None or hb is None:
            return mark_skip(sec, "Pillow 不可用或图片不可读，图像相似度跳过")
        dist = hamming(ha, hb)
        distances.append(dist)
        if dist > 22:
            sec["blocks"] += 1
            sec["evidence"].append(f"{label} 接缝 dHash 距离 {dist} > 22：尾帧与下一首帧视觉差异过大")
        elif dist > 14:
            sec["warnings"] += 1
            sec["evidence"].append(f"{label} 接缝 dHash 距离 {dist} > 14：建议人判确认跳切")
    sec["metrics"] = {"pairs": len(pairs), "max_dhash_distance": max(distances), "avg_dhash_distance": round(sum(distances) / len(distances), 3)}
    if not sec["evidence"]:
        sec["infos"] += 1
        sec["evidence"].append(f"接缝图片相似度通过：{len(pairs)} 对，max_dHash={max(distances)}")
    return sec


def extract_frame(video: str, at_sec: float, out_png: str) -> bool:
    if not shutil.which("ffmpeg"):
        return False
    proc = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at_sec:.3f}", "-i", video, "-frames:v", "1", out_png],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0 and os.path.isfile(out_png)


def ocr_bottom_text(png: str) -> Optional[str]:
    try:
        from PIL import Image  # type: ignore
        import pytesseract  # type: ignore
    except Exception:
        return None
    try:
        img = Image.open(png)
        w, h = img.size
        crop = img.crop((0, int(h * 0.58), w, h))
        try:
            return pytesseract.image_to_string(crop, lang="chi_sim+eng")
        except Exception:
            return pytesseract.image_to_string(crop)
    except Exception:
        return None


def load_existing_report(root: str, ep: str, names: Sequence[str]) -> Optional[Dict[str, Any]]:
    paths = []
    for name in names:
        paths.extend([
            os.path.join(root, "生产数据", "score_inputs", f"{ep}_{name}.json"),
            os.path.join(root, "生产数据", f"{name}_{ep}.json"),
        ])
    for path in paths:
        data = load_json(path)
        if isinstance(data, dict):
            return data
    return None


def report_counts(data: Dict[str, Any]) -> Tuple[int, int, int, List[str]]:
    blocks = int(data.get("blocks") or data.get("block") or 0)
    warnings = int(data.get("warnings") or data.get("warn") or 0)
    infos = int(data.get("infos") or data.get("ok") or 0)
    evidence = data.get("evidence") or data.get("notes") or []
    if isinstance(evidence, str):
        evidence = [evidence]
    return blocks, warnings, infos, [str(x) for x in evidence]


def check_subtitle_ocr(root: str, ep: str, max_cues: int = 8) -> Dict[str, Any]:
    sec = section("subtitle_ocr")
    existing = load_existing_report(root, ep, ("subtitle_ocr", "ocr_subtitle"))
    if existing:
        sec["blocks"], sec["warnings"], sec["infos"], sec["evidence"] = report_counts(existing)
        sec["metrics"] = existing.get("metrics", {})
        return sec
    finals = final_video_candidates(root, ep)
    cues = parse_srt(srt_path(root, ep))
    if not finals or not cues:
        return mark_skip(sec, "缺成片或中文字幕 SRT，字幕 OCR 跳过")
    if not shutil.which("ffmpeg"):
        return mark_skip(sec, "缺 ffmpeg，字幕 OCR 无法抽帧")
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except Exception:
        return mark_skip(sec, "缺 pytesseract/Pillow，字幕 OCR 跳过")
    checked = 0
    mismatches = 0
    with tempfile.TemporaryDirectory(prefix="n2d_score_ocr_") as tmp:
        step = max(1, len(cues) // max_cues)
        for idx, cue in enumerate(cues[::step][:max_cues], 1):
            at = (float(cue["start"]) + float(cue["end"])) / 2.0
            png = os.path.join(tmp, f"cue_{idx:02d}.png")
            if not extract_frame(finals[0], at, png):
                continue
            got = ocr_bottom_text(png)
            if got is None:
                continue
            checked += 1
            if not text_match(str(cue.get("text") or ""), got):
                mismatches += 1
                sec["warnings"] += 1
                sec["evidence"].append(f"cue@{at:.2f}s OCR 不匹配：期望『{str(cue.get('text',''))[:18]}』/ OCR『{got.strip()[:18]}』")
    if checked == 0:
        return mark_skip(sec, "未能成功 OCR 任一字幕帧")
    sec["metrics"] = {"checked_cues": checked, "mismatches": mismatches}
    if mismatches >= max(2, checked // 2):
        sec["blocks"] += 1
        sec["evidence"].append(f"OCR 不匹配 {mismatches}/{checked}，疑似烧字错位或字幕不可读")
    elif mismatches == 0:
        sec["infos"] += 1
        sec["evidence"].append(f"字幕 OCR 抽检通过：{checked} 条")
    return sec


def storyboard_duration(sb: Optional[Dict[str, Any]]) -> Optional[float]:
    if not sb:
        return None
    try:
        total = float(sb.get("total_duration"))
        if total > 0:
            return total
    except Exception:
        pass
    clips = [c for c in sb.get("clips", []) if isinstance(c, dict)]
    vals = []
    for c in clips:
        try:
            vals.append(float(c.get("duration") or 0))
        except Exception:
            pass
    return sum(vals) if vals else None


def check_av_duration(root: str, ep: str) -> Dict[str, Any]:
    sec = section("av_duration")
    final = final_video_candidates(root, ep)
    voices = voice_candidates(root, ep)
    cues = parse_srt(srt_path(root, ep))
    sb = load_storyboard(root, ep)
    final_dur = ffprobe_duration(final[0]) if final else None
    voice_dur = ffprobe_duration(voices[0]) if voices else None
    srt_dur = cues[-1]["end"] if cues else None
    story_dur = storyboard_duration(sb)
    sec["metrics"] = {"final_sec": final_dur, "voice_sec": voice_dur, "srt_sec": srt_dur, "storyboard_sec": story_dur}
    if final_dur is None:
        return mark_skip(sec, "缺成片或 ffprobe 不可用，成片音画时长对账跳过")
    compared = 0
    for label, target, block_tol, warn_tol in (("voice", voice_dur, 1.5, 0.6), ("srt", srt_dur, 1.0, 0.4), ("storyboard", story_dur, 2.0, 1.0)):
        if target is None:
            continue
        compared += 1
        diff = abs(final_dur - float(target))
        if diff > block_tol:
            sec["blocks"] += 1
            sec["evidence"].append(f"成片 vs {label} 时长差 {diff:.2f}s > {block_tol}s")
        elif diff > warn_tol:
            sec["warnings"] += 1
            sec["evidence"].append(f"成片 vs {label} 时长差 {diff:.2f}s > {warn_tol}s")
    if compared == 0:
        return mark_skip(sec, "只有成片时长，缺配音/SRT/storyboard 参照")
    if not sec["evidence"]:
        sec["infos"] += 1
        sec["evidence"].append(f"音画时长对账通过：成片 {final_dur:.2f}s")
    return sec


def prompt_text(root: str, ep: str) -> str:
    p = os.path.join(root, "出视频", ep, "prompt", "01_clips.md")
    return open(p, encoding="utf-8").read() if os.path.isfile(p) else ""


def check_lip_sync(root: str, ep: str) -> Dict[str, Any]:
    sec = section("lip_sync")
    existing = load_existing_report(root, ep, ("lip_sync", "lipsync", "syncnet"))
    if existing:
        sec["blocks"], sec["warnings"], sec["infos"], sec["evidence"] = report_counts(existing)
        sec["metrics"] = existing.get("metrics", {})
        return sec
    text = prompt_text(root, ep)
    if not text:
        return mark_skip(sec, "缺视频 prompt，无法判断口型风险；可提供 lip_sync_第N集.json 接入外部检测")
    mouth_yes = len(re.findall(r"mouth_visible\s*=\s*yes|口型可见|正面说话|张口", text, flags=re.I))
    mouth_no = len(re.findall(r"mouth_visible\s*=\s*no", text, flags=re.I))
    sec["metrics"] = {"mouth_visible_yes_hits": mouth_yes, "mouth_visible_no_hits": mouth_no}
    if mouth_yes:
        sec["warnings"] += 1
        sec["evidence"].append(f"发现 {mouth_yes} 处可见口型风险，但缺 lip-sync/SyncNet 外部检测报告")
    else:
        sec["infos"] += 1
        sec["evidence"].append("未发现 mouth_visible=yes 风险标记；口型检测可按需接入外部报告")
    return sec


def load_manifest(root: str, ep: str) -> List[Dict[str, Any]]:
    path = manifest_path(root, ep)
    data = load_json(path) if path else None
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def check_final_rhythm_density(root: str, ep: str) -> Dict[str, Any]:
    sec = section("final_rhythm_density")
    sb = load_storyboard(root, ep)
    clips = [c for c in (sb or {}).get("clips", []) if isinstance(c, dict)] if sb else []
    final = final_video_candidates(root, ep)
    final_dur = ffprobe_duration(final[0]) if final else storyboard_duration(sb)
    if not final_dur or final_dur <= 0 or not clips:
        return mark_skip(sec, "缺成片/故事板时长或 clips[]，成片节奏密度跳过")
    density = len(clips) / final_dur * 60.0
    manifest = load_manifest(root, ep)
    hooks = [m for m in manifest if str(m.get("钩子") or "").strip()]
    hook_interval = final_dur / len(hooks) if hooks else None
    sec["metrics"] = {"clip_count": len(clips), "final_sec": round(final_dur, 3), "shot_density_per_min": round(density, 3), "hook_count": len(hooks), "hook_interval_sec": None if hook_interval is None else round(hook_interval, 3)}
    if density < 10:
        sec["warnings"] += 1
        sec["evidence"].append(f"成片镜头密度 {density:.1f}/min 偏慢，可能前段留不住")
    elif density >= 45:
        sec["warnings"] += 1
        sec["evidence"].append(f"成片镜头密度 {density:.1f}/min 过密，可能造成跳出")
    if hook_interval is None:
        sec["warnings"] += 1
        sec["evidence"].append("配音时长清单缺钩子/爽点/集尾标记，无法确认成片钩子密度")
    elif hook_interval > 30:
        sec["blocks"] += 1
        sec["evidence"].append(f"平均钩子间隔 {hook_interval:.1f}s > 30s，节奏密度阻断")
    elif hook_interval > 20:
        sec["warnings"] += 1
        sec["evidence"].append(f"平均钩子间隔 {hook_interval:.1f}s > 20s，节奏偏稀")
    if manifest:
        tail = manifest[-2:] if len(manifest) >= 2 else manifest
        if not any(str(m.get("钩子") or "").strip() for m in tail):
            sec["warnings"] += 1
            sec["evidence"].append("成片尾部 2 句缺 cliffhanger/钩子标记")
    if not sec["evidence"]:
        sec["infos"] += 1
        sec["evidence"].append(f"成片节奏密度通过：{density:.1f}/min")
    return sec


def analyze(root: str, ep: str) -> Dict[str, Any]:
    ep = normalize_episode(ep)
    sections = {
        "image_similarity": check_image_similarity(root, ep),
        "subtitle_ocr": check_subtitle_ocr(root, ep),
        "av_duration": check_av_duration(root, ep),
        "lip_sync": check_lip_sync(root, ep),
        "final_rhythm_density": check_final_rhythm_density(root, ep),
    }
    return {"kind": KIND, "version": VERSION, "root": root, "episode": ep, "generated_at": now_iso(), "sections": sections}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d-score visual checks")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true", help="kept for symmetry; output is always JSON")
    return ap


def main(argv: List[str]) -> int:
    ns = parser().parse_args(argv)
    print(json.dumps(analyze(ns.root.rstrip("/"), ns.episode), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
