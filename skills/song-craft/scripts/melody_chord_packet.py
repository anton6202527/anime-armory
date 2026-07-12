#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a song form, chord sheet, and topline notes packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date
from typing import Any


KIND = "song_form_packet"
CHECK_KIND = "song_form_check"


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def lyric_sections(root: str) -> list[str]:
    path = os.path.join(root, "词", "lyrics.md")
    if not os.path.exists(path):
        return []
    text = open(path, encoding="utf-8").read()
    return [m.group(1).strip().lower() for m in re.finditer(r"^\s*\[([^\]]+)\]\s*$", text, flags=re.M)]


def _arg(args: argparse.Namespace, name: str, default: Any = "") -> Any:
    return getattr(args, name, default)


def build_packet(root: str, args: argparse.Namespace) -> dict[str, Any]:
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    brief = load_json(os.path.join(root, "创作", "song_brief.json"), {}) or {}
    sections = lyric_sections(root) or meta.get("structure") or ["verse1", "chorus"]
    key = _arg(args, "key") or meta.get("key") or "未定"
    bpm = _arg(args, "bpm") or meta.get("bpm") or "未定"
    form_type = _arg(args, "form_type") or meta.get("song_form_type") or meta.get("form_type") or "sectional"
    progression = _arg(args, "progression") or "待作曲确认；不得把通用和弦循环当成默认答案"
    meter = _arg(args, "meter") or meta.get("meter") or "4/4"
    target_duration = meta.get("target_duration_seconds")
    default_bars = _arg(args, "section_bars", 0) or 0
    rows = []
    for section in sections:
        role = section_role(section)
        rows.append({
            "section": section,
            "dramatic_function": role,
            "energy": energy_for(section),
            "bars": default_bars or None,
            "chord_progression": progression if "chorus" in section or "副歌" in section else _arg(args, "verse_progression") or progression,
            "harmonic_rhythm": _arg(args, "harmonic_rhythm") or "待作曲确认",
            "topline_direction": topline_for(section),
        })
    return {
        "schema_version": 2,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "title": meta.get("title") or os.path.basename(root),
        "key": key,
        "bpm": bpm,
        "meter": meter,
        "form_type": form_type,
        "target_duration_seconds": target_duration,
        "vocal_range": _arg(args, "vocal_range") or meta.get("vocal_range") or "待演唱者/模型确认",
        "tessitura": _arg(args, "tessitura") or meta.get("tessitura") or "待演唱者/模型确认",
        "sonic_identity": brief.get("sonic_identity") or meta.get("genre") or "",
        "sections": rows,
        "notes": _arg(args, "notes"),
    }


def check_packet(packet: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def issue(issue_id: str, severity: str, message: str) -> None:
        findings.append({"id": issue_id, "severity": severity, "message": message, "path": "歌/song_form.json"})

    if not packet.get("sections"):
        issue("FORM-NO-SECTIONS", "blocking", "曲式没有任何段落。")
    try:
        bpm = float(packet.get("bpm"))
        if not 30 <= bpm <= 260:
            issue("FORM-BPM-RANGE", "blocking", "BPM 必须在 30-260 的可执行范围内。")
    except (TypeError, ValueError):
        issue("FORM-BPM-MISSING", "blocking", "BPM 必须是明确数字，不能只写快/中/慢。")
    if packet.get("key") in {"", None, "未定"}:
        issue("FORM-KEY-MISSING", "warning", "调性未定；模型生成可继续，但真人演唱前必须按音域确认。")
    if not re.fullmatch(r"\d+\s*/\s*\d+", str(packet.get("meter") or "")):
        issue("FORM-METER", "blocking", "拍号必须使用如 4/4、6/8 的格式。")
    if packet.get("target_duration_seconds"):
        bars = [row.get("bars") for row in packet.get("sections") or []]
        if not any(isinstance(value, int) and value > 0 for value in bars):
            issue("FORM-BARS-MISSING", "warning", "已定义目标时长但未定义段落小节数，结构时长仍不可核算。")
    if "待作曲确认" in " ".join(str(row.get("chord_progression") or "") for row in packet.get("sections") or []):
        issue("FORM-HARMONY-OPEN", "warning", "和声仍是开放决策；这是创作提示，不应被误报为已完成谱曲。")
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": packet.get("project_root"),
        "source_sha256": hashlib.sha256(json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "passed": not blockers,
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "findings": findings,
    }


def section_role(section: str) -> str:
    s = section.lower()
    if "chorus" in s or "副歌" in s:
        return "hook/emotional release"
    if "pre" in s:
        return "build tension into chorus"
    if "bridge" in s or "桥" in s:
        return "contrast or emotional turn"
    if "intro" in s:
        return "establish sound identity"
    if "outro" in s:
        return "resolve and leave aftertaste"
    return "story/detail setup"


def energy_for(section: str) -> str:
    s = section.lower()
    if "chorus" in s:
        return "high"
    if "pre" in s or "bridge" in s:
        return "medium-high"
    if "intro" in s or "outro" in s:
        return "low"
    return "medium"


def topline_for(section: str) -> str:
    s = section.lower()
    if "chorus" in s:
        return "higher register, repeatable hook, stable landing notes"
    if "pre" in s:
        return "ascending phrase, unresolved cadence"
    if "bridge" in s:
        return "new melodic contour, then return to chorus"
    return "narrower range, conversational melody"


def render_chord_sheet(packet: dict[str, Any]) -> str:
    lines = [
        f"# Chord Sheet - {packet.get('title')}",
        "",
        f"- Key: {packet.get('key')}",
        f"- BPM: {packet.get('bpm')}",
        f"- Sonic identity: {packet.get('sonic_identity') or '未填写'}",
        "",
    ]
    for row in packet.get("sections") or []:
        lines.append(f"## [{row['section']}]")
        lines.append(f"- function: {row['dramatic_function']}")
        lines.append(f"- energy: {row['energy']}")
        lines.append(f"- chords: {row['chord_progression']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_topline(packet: dict[str, Any]) -> str:
    lines = [
        f"# Topline Notes - {packet.get('title')}",
        "",
        "Use these notes as direction for a human topliner or a music-generation style prompt. Do not treat them as a fixed melody.",
        "",
    ]
    for row in packet.get("sections") or []:
        lines.append(f"- [{row['section']}]: {row['topline_direction']} ({row['energy']})")
    if packet.get("notes"):
        lines.extend(["", "## Notes", "", str(packet["notes"])])
    return "\n".join(lines).rstrip() + "\n"


def write_packet(root: str, packet: dict[str, Any]) -> tuple[str, str, str]:
    song_dir = os.path.join(root, "歌")
    json_path = os.path.join(song_dir, "song_form.json")
    chord_path = os.path.join(song_dir, "chord_sheet.md")
    topline_path = os.path.join(song_dir, "topline_notes.md")
    write_json(json_path, packet)
    write_json(os.path.join(song_dir, "song_form_check.json"), check_packet(packet))
    write_text(chord_path, render_chord_sheet(packet))
    write_text(topline_path, render_topline(packet))
    return json_path, chord_path, topline_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成旋律/和声/曲式草图包")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--key", default="")
    ap.add_argument("--bpm", default="")
    ap.add_argument("--progression", default="")
    ap.add_argument("--verse-progression", default="")
    ap.add_argument("--form-type", default="")
    ap.add_argument("--meter", default="")
    ap.add_argument("--section-bars", type=int, default=0)
    ap.add_argument("--harmonic-rhythm", default="")
    ap.add_argument("--vocal-range", default="")
    ap.add_argument("--tessitura", default="")
    ap.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    packet = build_packet(root, args)
    check = check_packet(packet)
    if args.write:
        json_path, chord_path, topline_path = write_packet(root, packet)
        print(f"[ok] song form   → {json_path}")
        print(f"[ok] chord sheet → {chord_path}")
        print(f"[ok] topline     → {topline_path}")
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_chord_sheet(packet))
        print(render_topline(packet))
    return 0 if check["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
