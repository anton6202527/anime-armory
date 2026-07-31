#!/usr/bin/env python3
"""Caption structure and conservative flash screening for ad deliverables.

WCAG requirements are kept separate from house thresholds: missing/invalid
captions can block when prerecorded audio is present; reading speed and the
low-resolution flash detector are advisory signals. Definitive flash safety
and meaningful non-speech coverage remain named human sign-off items.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


HOUSE_CAPTION_PROFILE = {
    "max_cjk_chars_per_second_warn": 12.0,
    "min_cue_seconds_warn": 0.7,
    "authority": "house_caption_legibility_screen",
}
TIMESTAMP = re.compile(
    r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{3})\s*-->\s*"
    r"(?P<h2>\d{2}):(?P<m2>\d{2}):(?P<s2>\d{2})[,.](?P<ms2>\d{3})"
)


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


def _seconds(match, suffix=""):
    return (int(match.group("h" + suffix)) * 3600 + int(match.group("m" + suffix)) * 60 +
            int(match.group("s" + suffix)) + int(match.group("ms" + suffix)) / 1000)


def parse_srt_text(raw: str):
    cues = []
    blocks = re.split(r"\r?\n\s*\r?\n", raw.strip()) if raw.strip() else []
    for pos, block in enumerate(blocks, 1):
        lines = [line.rstrip() for line in block.splitlines()]
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            cues.append({"index": pos, "error": "timestamp_missing", "text": "\n".join(lines)})
            continue
        match = TIMESTAMP.search(lines[timing_index])
        if not match:
            cues.append({"index": pos, "error": "timestamp_invalid", "text": "\n".join(lines[timing_index + 1:])})
            continue
        cues.append({
            "index": pos, "start": _seconds(match), "end": _seconds(match, "2"),
            "text": "\n".join(lines[timing_index + 1:]).strip(),
        })
    return cues


def parse_settings(path: Path):
    out = {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in raw.splitlines():
        m = re.match(r"\s*[-*]?\s*([^:：#]+)[:：]\s*([^#]+)", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def audio_present(path: Path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.is_file():
        return None
    proc = subprocess.run([
        ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index",
        "-of", "csv=p=0", str(path),
    ], capture_output=True, text=True)
    return proc.returncode == 0 and bool(proc.stdout.strip())


def flash_screen(path: Path):
    """Return a low-resolution heuristic; never a compliance verdict."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not path.is_file():
        return None
    width, height, fps = 64, 36, 12
    proc = subprocess.run([
        ffmpeg, "-v", "error", "-i", str(path), "-vf", f"scale={width}:{height}:flags=area,fps={fps},format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ], capture_output=True)
    if proc.returncode:
        return None
    size = width * height
    frames = [proc.stdout[i:i + size] for i in range(0, len(proc.stdout) - size + 1, size)]
    events = []
    for i, (a, b) in enumerate(zip(frames, frames[1:]), 1):
        changed = sum(abs(x - y) >= 80 for x, y in zip(a, b)) / size
        if changed >= 0.25:
            events.append(i / fps)
    peak = 0
    for event in events:
        peak = max(peak, sum(event <= other < event + 1.0 for other in events))
    return {"sample_fps": fps, "frame_size": f"{width}x{height}", "large_change_events": len(events),
            "peak_transitions_per_second": peak, "possible_over_three_flashes": peak > 6}


def _caption_path(root: Path, language: str):
    if language == "仅英文":
        return root / "脚本" / "字幕_en.srt"
    return root / "脚本" / "字幕_zh.srt"


def _norm_text(value):
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value or "").lower())


def _event_covered(event, cues):
    wanted = _norm_text(event.get("caption") or event.get("text") or event.get("label"))
    try:
        start = float(event.get("start")); end = float(event.get("end"))
    except (TypeError, ValueError):
        return False
    for cue in cues:
        if cue.get("error"):
            continue
        overlap = float(cue.get("start") or 0) < end and float(cue.get("end") or 0) > start
        if overlap and wanted and wanted in _norm_text(cue.get("text")):
            return True
    return False


def _queryable(root: Path, value):
    ref = str(value or "").strip()
    if not ref:
        return False
    if ref.startswith(("https://", "http://", "record:")):
        return True
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return path.is_file()


def _localized_event(event, locale):
    row = dict(event) if isinstance(event, dict) else event
    if not isinstance(row, dict):
        return row
    translations = row.get("captions_by_locale") if isinstance(row.get("captions_by_locale"), dict) else {}
    if locale and translations.get(locale):
        row["caption"] = translations[locale]
    return row


def _validate_cues(cues, findings, access, wcag_a, *, label="字幕", locale=""):
    previous_end = -1.0
    for cue in cues:
        if cue.get("error") or not cue.get("text"):
            findings.append({"severity": "block", "code": "caption_cue_malformed",
                             "msg": f"{label} cue {cue.get('index')} 时间码/文本无效"})
            continue
        start, end = float(cue["start"]), float(cue["end"])
        if end <= start or start < previous_end - 1e-6:
            findings.append({"severity": "block", "code": "caption_timing_invalid",
                             "msg": f"{label} cue {cue['index']} 非正时长或与前条重叠"})
        duration = max(0.001, end - start)
        chars = len(re.sub(r"[\s\W_]+", "", cue["text"], flags=re.UNICODE))
        cps = chars / duration
        cue["duration_seconds"] = round(duration, 3)
        cue["chars_per_second"] = round(cps, 2)
        if duration < HOUSE_CAPTION_PROFILE["min_cue_seconds_warn"]:
            findings.append({"severity": "warn", "code": "caption_duration_house_warn",
                             "msg": f"{label} cue {cue['index']} 仅 {duration:.2f}s，低于内部快筛；请实机审读"})
        if cps > HOUSE_CAPTION_PROFILE["max_cjk_chars_per_second_warn"]:
            findings.append({"severity": "warn", "code": "caption_speed_house_warn",
                             "msg": f"{label} cue {cue['index']} 约 {cps:.1f} 字符/秒，超过内部快筛；请实机审读"})
        previous_end = max(previous_end, end)
    if access.get("meaningful_non_speech_audio") is True:
        tagged = any(re.search(r"[\[（(].{1,30}[\]）)]", cue.get("text") or "") for cue in cues)
        if not tagged:
            findings.append({"severity": "block" if wcag_a else "warn", "code": "non_speech_caption_review",
                             "msg": f"{label} 未见音乐/音效标注，但 brief 声明有意义非语言音频；需逐段确认"})
    events = access.get("meaningful_non_speech_events") or []
    if isinstance(events, dict):
        events = [events]
    for pos, raw in enumerate(events, 1):
        event = _localized_event(raw, locale)
        if (not isinstance(event, dict) or (event.get("start") is None) or
                (event.get("end") is None) or not (event.get("caption") or event.get("text") or event.get("label"))):
            findings.append({"severity": "block", "code": "non_speech_event_malformed",
                             "msg": f"{label} 非语言音频事件 {pos} 缺 start/end/caption"})
        elif not _event_covered(event, cues):
            findings.append({"severity": "block" if wcag_a or access.get("non_speech_captioning_required") else "warn",
                             "code": "non_speech_event_uncovered",
                             "msg": f"{label} 有意义非语言音频事件 {pos} 未被同时段字幕完整覆盖"})


def build_report(root: Path, plan: dict):
    root = root.resolve()
    brief = load(root / "需求" / "brief.json", {}) or {}
    settings = parse_settings(root / "_设置.md")
    access = brief.get("accessibility") if isinstance(brief.get("accessibility"), dict) else {}
    target_level = str(access.get("target_level") or "").strip().upper()
    wcag_a = target_level in {"WCAG2.2-A", "WCAG2.2-AA", "WCAG2.2-AAA", "A", "AA", "AAA"}
    wcag_aa = target_level in {"WCAG2.2-AA", "WCAG2.2-AAA", "AA", "AAA"}
    language = str(settings.get("字幕语言") or access.get("subtitle_language") or "中文")
    exception = access.get("caption_exception") if isinstance(access.get("caption_exception"), dict) else {}
    deliverables = [row for row in (plan.get("deliverables") or []) if row.get("exists")]
    media_rows = []
    any_audio = False
    placement_caption_required = any(
        spec.get("captions_required") is True
        for row in deliverables for spec in (row.get("platform_constraints") or []) if isinstance(spec, dict)
    )
    findings = []
    for row in deliverables:
        path = root / str(row.get("expected_path") or "")
        has_audio = audio_present(path)
        any_audio = any_audio or has_audio is True
        flash = flash_screen(path)
        media_rows.append({"deliverable_id": row.get("deliverable_id"), "path": row.get("expected_path"),
                           "sha256": sha(path), "has_audio": has_audio, "flash_screen": flash})
        if flash is None:
            findings.append({"severity": "warn", "code": "flash_screen_unavailable",
                             "msg": f"{row.get('deliverable_id')} 未完成闪烁启发式；须保留具名人工/专业工具复核"})
        elif flash["possible_over_three_flashes"]:
            findings.append({"severity": "warn", "code": "possible_flash_risk",
                             "msg": f"{row.get('deliverable_id')} 低分辨率快筛发现密集大幅亮度变化；不是定论，须按 WCAG 阈值复核"})
    captions_needed = any_audio or placement_caption_required
    if captions_needed and language == "无字幕":
        valid_exception = (exception.get("approved") is True and exception.get("approved_by") and
                           exception.get("reason") and exception.get("no_meaningful_audio") is True)
        if not valid_exception:
            findings.append({"severity": "block", "code": "captions_required",
                             "msg": "正式交付含预录音频或映射到要求字幕的 sound-off placement，但设置为无字幕；须补字幕或留具名例外"})
    caption = _caption_path(root, language)
    cues = []
    if captions_needed and language != "无字幕":
        if not caption.is_file() or not caption.read_text(encoding="utf-8").strip():
            findings.append({"severity": "block", "code": "caption_file_missing",
                             "msg": f"正式交付需要字幕但文件缺失/为空：{caption.relative_to(root)}"})
        else:
            cues = parse_srt_text(caption.read_text(encoding="utf-8"))
            _validate_cues(cues, findings, access, wcag_a, label="主字幕")

    matrix = load(root / "合规" / "locale_matrix.json", {}) or {}
    locale_rows = matrix.get("locales") if isinstance(matrix.get("locales"), dict) else {}
    locale_captions = {}
    if captions_needed:
        primary_resolved = caption.resolve() if caption.exists() else caption
        for locale, row in locale_rows.items():
            if not isinstance(row, dict):
                continue
            relpath = str(row.get("subtitle_path") or "")
            path = root / relpath if relpath else Path()
            if not relpath or not path.is_file() or not path.read_text(encoding="utf-8").strip():
                findings.append({"severity": "block", "code": "locale_caption_file_missing",
                                 "msg": f"{locale} 最终字幕文件缺失/为空：{relpath or '(missing path)'}"})
                locale_captions[str(locale)] = {"path": relpath, "sha256": None, "cues": []}
                continue
            localized = cues if path.resolve() == primary_resolved else parse_srt_text(path.read_text(encoding="utf-8"))
            if path.resolve() != primary_resolved:
                _validate_cues(localized, findings, access, wcag_a, label=f"{locale} 字幕", locale=str(locale))
            locale_captions[str(locale)] = {"path": relpath, "sha256": sha(path), "cues": localized}

    description_required = bool(access.get("audio_description_required")) or wcag_aa
    alternative_required = bool(access.get("media_alternative_required")) or (wcag_a and not description_required)
    description = access.get("audio_description") if isinstance(access.get("audio_description"), dict) else {}
    alternative = access.get("media_alternative") if isinstance(access.get("media_alternative"), dict) else {}
    if description_required:
        valid = (str(description.get("status") or "").lower() == "approved" and description.get("approved_by") and
                 _queryable(root, description.get("path")) and _queryable(root, description.get("evidence")))
        if not valid:
            findings.append({"severity": "block", "code": "audio_description_missing",
                             "msg": "目标无障碍档要求预录视频音频描述，但缺 approved/path/evidence/approved_by"})
    elif alternative_required:
        valid = (str(alternative.get("status") or "").lower() == "approved" and alternative.get("approved_by") and
                 _queryable(root, alternative.get("path")) and _queryable(root, alternative.get("evidence")))
        if not valid:
            findings.append({"severity": "block", "code": "media_alternative_missing",
                             "msg": "目标无障碍档要求预录媒体替代，但缺 approved/path/evidence/approved_by"})
    if len(locale_rows) > 1 and (description_required or alternative_required):
        key = "audio_descriptions" if description_required else "media_alternatives"
        localized_assets = access.get(key) if isinstance(access.get(key), dict) else {}
        global_asset = description if description_required else alternative
        global_locales = {str(value) for value in global_asset.get("locales") or []}
        missing_localized = []
        for locale in locale_rows:
            row = localized_assets.get(locale) if isinstance(localized_assets.get(locale), dict) else None
            if row is None and str(locale) in global_locales:
                row = global_asset
            valid = bool(row and str(row.get("status") or "").lower() == "approved" and row.get("approved_by") and
                         _queryable(root, row.get("path")) and _queryable(root, row.get("evidence")))
            if not valid:
                missing_localized.append(str(locale))
        if missing_localized:
            findings.append({"severity": "block", "code": "localized_accessibility_alternative_missing",
                             "msg": f"多语言项目缺逐 locale {'音频描述' if description_required else '媒体替代'}：" +
                                    ", ".join(missing_localized)})
    rendered_text = load(root / "合成" / "rendered_text_qc.json", {}) or {}
    rendered_blocks = int(((rendered_text.get("summary") or {}).get("block")) or 0) if rendered_text else None
    if wcag_a and (rendered_blocks is None or rendered_blocks):
        findings.append({"severity": "block", "code": "rendered_text_accessibility_missing",
                         "msg": "WCAG 目标要求最终文字/对比度报告当前有效且 0 block"})
    elif not rendered_text:
        findings.append({"severity": "warn", "code": "rendered_text_accessibility_pending",
                         "msg": "尚无最终像素文字/对比度报告；普通交付由具名审片闭合"})
    return {
        "schema_version": 2, "kind": "ad_accessibility_qc",
        "standards": [
            {"authority": "W3C_WCAG_2_2", "criterion": "1.2.2 Captions (Prerecorded)",
             "source": "https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded"},
            {"authority": "W3C_WCAG_2_2", "criterion": "2.3.1 Three Flashes or Below Threshold",
             "source": "https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold"},
            {"authority": "W3C_WCAG_2_2", "criterion": "1.2.3/1.2.5 Audio Description or Media Alternative",
             "source": "https://www.w3.org/WAI/WCAG22/Understanding/audio-description-prerecorded"},
            {"authority": "W3C_WCAG_2_2", "criterion": "1.4.3 Contrast (Minimum)",
             "source": "https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum"},
            HOUSE_CAPTION_PROFILE,
        ],
        "accessibility_profile": {"target_level": target_level or "project_default",
                                  "audio_description_required": description_required,
                                  "media_alternative_required": alternative_required},
        "caption": {"language": language, "required_by_prerecorded_audio": any_audio,
                    "required_by_placement": placement_caption_required,
                    "path": str(caption.relative_to(root)), "sha256": sha(caption), "cues": cues},
        "locale_captions": locale_captions,
        "deliverables": media_rows, "findings": findings,
        "summary": {"block": sum(f["severity"] == "block" for f in findings),
                    "warn": sum(f["severity"] == "warn" for f in findings)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="ad captions + flash accessibility QC")
    ap.add_argument("project_root")
    ap.add_argument("--plan", default=None)
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    plan_path = Path(ns.plan) if ns.plan else root / "合成" / "delivery_plan.json"
    plan = load(plan_path, {}) or {}
    payload = build_report(root, plan)
    out = root / "合成" / "accessibility_qc.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# accessibility QC block={payload['summary']['block']} warn={payload['summary']['warn']}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
