#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a manuscript map from outline, scene cards, and drafted chapters."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from datetime import date
from typing import Any


MAP_KIND = "novel_manuscript_map"
CHECK_KIND = "novel_manuscript_map_check"
CHAPTER_RE = re.compile(r"第\s*0*(\d+)\s*章\s*(?:[《<]([^》>]+)[》>])?\s*(?:[—-]\s*(.*))?")


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


def output_paths(root: str) -> tuple[str, str, str]:
    setting_dir = os.path.join(root, "设定")
    return (
        os.path.join(setting_dir, "manuscript_map.json"),
        os.path.join(setting_dir, "manuscript_map.md"),
        os.path.join(setting_dir, "manuscript_map_check.json"),
    )


def parse_outline(root: str) -> dict[int, dict[str, str]]:
    path = os.path.join(root, "设定", "章纲.md")
    out: dict[int, dict[str, str]] = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            m = CHAPTER_RE.search(raw)
            if not m:
                continue
            chapter = int(m.group(1))
            out[chapter] = {
                "title": (m.group(2) or "").strip(),
                "outline_beat": (m.group(3) or raw.strip()).strip(),
            }
    return out


def chapter_number_from_path(path: str) -> int | None:
    m = re.search(r"第0*(\d+)章", os.path.basename(path))
    return int(m.group(1)) if m else None


def chapter_files(root: str) -> dict[int, str]:
    out: dict[int, str] = {}
    for path in sorted(glob.glob(os.path.join(root, "章节", "第*.md"))):
        number = chapter_number_from_path(path)
        if number is not None:
            out[number] = os.path.relpath(path, root).replace(os.sep, "/")
    return out


def _first_nonempty(values: list[Any]) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def build_map(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    outline = parse_outline(root)
    files = chapter_files(root)
    scene_payload = load_json(os.path.join(root, "设定", "scene_cards.json"), {}) or {}
    scenes = [s for s in scene_payload.get("scenes") or [] if isinstance(s, dict)]
    by_chapter: dict[int, list[dict[str, Any]]] = {}
    for scene in scenes:
        try:
            chapter = int(scene.get("chapter") or 0)
        except (TypeError, ValueError):
            continue
        if chapter:
            by_chapter.setdefault(chapter, []).append(scene)
    chapters = sorted(set(outline) | set(files) | set(by_chapter))
    rows = []
    for chapter in chapters:
        chapter_scenes = sorted(by_chapter.get(chapter, []), key=lambda s: int(s.get("scene_no") or 0))
        row = {
            "chapter": chapter,
            "title": outline.get(chapter, {}).get("title", ""),
            "chapter_path": files.get(chapter, ""),
            "outline_beat": outline.get(chapter, {}).get("outline_beat", ""),
            "scene_count": len(chapter_scenes),
            "povs": sorted({str(s.get("pov")) for s in chapter_scenes if str(s.get("pov") or "").strip()}),
            "primary_desire": _first_nonempty([s.get("desire") for s in chapter_scenes]),
            "primary_obstacle": _first_nonempty([s.get("obstacle") for s in chapter_scenes]),
            "value_shift": _first_nonempty([s.get("value_shift") for s in chapter_scenes]),
            "turn": _first_nonempty([s.get("turn") for s in chapter_scenes]),
            "reveal_or_payoff": [
                str(s.get("reveal_or_payoff")).strip()
                for s in chapter_scenes
                if str(s.get("reveal_or_payoff") or "").strip()
            ],
            "sensory_anchors": [
                str(s.get("sensory_anchor")).strip()
                for s in chapter_scenes
                if str(s.get("sensory_anchor") or "").strip()
            ],
            "scene_ids": [str(s.get("id") or "") for s in chapter_scenes if s.get("id")],
        }
        row["review_use"] = "确认本章是否推进读者承诺、人物选择和价值转折；若缺 turn/value_shift，先回章纲或场景卡。"
        rows.append(row)
    return {
        "schema_version": 1,
        "kind": MAP_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "chapter_count": len(rows),
        "source": {
            "outline": os.path.exists(os.path.join(root, "设定", "章纲.md")),
            "scene_cards": scene_payload.get("kind") == "novel_scene_cards",
            "chapter_files": len(files),
        },
        "chapters": rows,
    }


def check_map(report: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if report.get("kind") != MAP_KIND:
        findings.append({"id": "MANUSCRIPT-MAP-MISSING", "severity": "blocking", "message": "manuscript_map.json 缺失或格式错误"})
    if not report.get("chapters"):
        findings.append({"id": "MANUSCRIPT-MAP-EMPTY", "severity": "warning", "message": "结构地图没有章节；请先补章纲或场景卡。"})
    for row in report.get("chapters") or []:
        chapter = row.get("chapter")
        if not row.get("outline_beat") and not row.get("scene_ids"):
            findings.append({"id": "MANUSCRIPT-MAP-CHAPTER-UNPLANNED", "severity": "warning", "chapter": chapter, "message": "本章缺章纲和场景卡来源。"})
        if row.get("scene_count") and not row.get("turn"):
            findings.append({"id": "MANUSCRIPT-MAP-TURN-MISSING", "severity": "blocking", "chapter": chapter, "message": "本章场景卡缺 turn，无法判断价值转折。"})
        if row.get("scene_count") and not row.get("value_shift"):
            findings.append({"id": "MANUSCRIPT-MAP-VALUE-SHIFT-MISSING", "severity": "blocking", "chapter": chapter, "message": "本章场景卡缺 value_shift，review 无法判定推进。"})
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": report.get("project_root"),
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "passed": not blockers,
        "findings": findings,
    }


def render_markdown(report: dict[str, Any], check: dict[str, Any] | None = None) -> str:
    lines = [
        "# Manuscript Map",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- 章节数：{report.get('chapter_count')}",
        f"- 来源：{report.get('source')}",
        "",
        "| 章 | 标题 | 场景 | POV | 欲望/阻碍 | 转折 | 价值变化 | 揭示/回收 | 正文 |",
        "|---:|---|---:|---|---|---|---|---|---|",
    ]
    for row in report.get("chapters") or []:
        lines.append(
            "| "
            + " | ".join([
                str(row.get("chapter")),
                _cell(row.get("title")),
                str(row.get("scene_count")),
                _cell("、".join(row.get("povs") or [])),
                _cell(f"{row.get('primary_desire') or ''} / {row.get('primary_obstacle') or ''}"),
                _cell(row.get("turn")),
                _cell(row.get("value_shift")),
                _cell("；".join(row.get("reveal_or_payoff") or [])),
                _cell(row.get("chapter_path")),
            ])
            + " |"
        )
    if check and check.get("findings"):
        lines.extend(["", "## Findings", ""])
        for item in check["findings"]:
            chapter = f" 第{int(item['chapter']):02d}章" if item.get("chapter") else ""
            lines.append(f"- [{item.get('severity')}] {item.get('id')}{chapter}: {item.get('message')}")
    return "\n".join(lines).rstrip() + "\n"


def _cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def write_outputs(root: str, report: dict[str, Any], check: dict[str, Any]) -> tuple[str, str, str]:
    json_path, md_path, check_path = output_paths(root)
    write_json(json_path, report)
    write_json(check_path, check)
    write_text(md_path, render_markdown(report, check))
    return json_path, md_path, check_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成/检查长篇结构地图")
    parser.add_argument("project_root")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    report = build_map(root)
    check = check_map(report)
    if args.write:
        json_path, md_path, check_path = write_outputs(root, report, check)
        print(f"[ok] manuscript map JSON → {json_path}")
        print(f"[ok] manuscript map MD   → {md_path}")
        print(f"[ok] manuscript map check→ {check_path}")
    if args.json:
        print(json.dumps({"map": report, "check": check}, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report, check))
    return 0 if check["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
