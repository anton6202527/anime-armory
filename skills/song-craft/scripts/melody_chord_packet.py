#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a song form, chord sheet, and topline notes packet."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date
from typing import Any


KIND = "song_form_packet"


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


def default_progression(key: str) -> str:
    minor = str(key).lower().endswith("m")
    if minor:
        return "i-VI-III-VII"
    return "I-V-vi-IV"


def build_packet(root: str, args: argparse.Namespace) -> dict[str, Any]:
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    brief = load_json(os.path.join(root, "创作", "song_brief.json"), {}) or {}
    sections = lyric_sections(root) or meta.get("structure") or ["verse1", "chorus"]
    key = args.key or meta.get("key") or "未定"
    bpm = args.bpm or meta.get("bpm") or "中速"
    progression = args.progression or (default_progression(key) if key != "未定" else "I-V-vi-IV / i-VI-III-VII 二选一")
    rows = []
    for section in sections:
        role = section_role(section)
        rows.append({
            "section": section,
            "dramatic_function": role,
            "energy": energy_for(section),
            "chord_progression": progression if "chorus" in section or "副歌" in section else args.verse_progression or progression,
            "topline_direction": topline_for(section),
        })
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "title": meta.get("title") or os.path.basename(root),
        "key": key,
        "bpm": bpm,
        "target_duration_seconds": meta.get("target_duration_seconds"),
        "sonic_identity": brief.get("sonic_identity") or meta.get("genre") or "",
        "sections": rows,
        "notes": args.notes,
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
    ap.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    packet = build_packet(root, args)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
