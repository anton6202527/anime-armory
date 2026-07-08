#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Author-facing default workflow for song projects.

The workflow is deterministic: it checks files and known gate reports, writes a
status report under 生产数据, and suggests the next command. It does not write
lyrics, generate audio, or mark progress complete.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import date
from typing import Any


KIND = "song_workflow"


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


def rel_exists(root: str, relpath: str) -> bool:
    return os.path.exists(os.path.join(root, relpath))


def any_glob(root: str, pattern: str) -> bool:
    return bool(glob.glob(os.path.join(root, pattern)))


def lyrics_ready(root: str) -> tuple[bool, list[str]]:
    path = os.path.join(root, "词", "lyrics.md")
    if not os.path.exists(path):
        return False, ["缺少 词/lyrics.md"]
    text = open(path, encoding="utf-8", errors="replace").read()
    blockers = []
    if "（歌词…）" in text or "TODO" in text or "待填" in text:
        blockers.append("歌词仍含占位文本")
    if "[chorus" not in text.lower() and "[副歌" not in text:
        blockers.append("歌词缺 chorus / 副歌段")
    return not blockers, blockers


def manifest_status(root: str) -> tuple[bool, bool, list[str]]:
    payload = load_json(os.path.join(root, "歌", "takes_manifest.json"), {}) or {}
    if payload.get("kind") != "song_take_manifest":
        return False, False, ["缺少 歌/takes_manifest.json"]
    takes = payload.get("takes") if isinstance(payload.get("takes"), list) else []
    registered = any(t.get("status") in {"registered", "selected"} for t in takes if isinstance(t, dict))
    selected = bool(payload.get("selected_take")) and rel_exists(root, "歌/song.wav")
    warnings = []
    if not registered:
        warnings.append("尚未登记任何 take")
    if registered and not selected:
        warnings.append("已有 take 但尚未 selected_take")
    return registered, selected, warnings


def check_report(root: str, relpath: str, passed_key: str = "passed") -> tuple[bool, list[str]]:
    payload = load_json(os.path.join(root, relpath), {}) or {}
    if not isinstance(payload, dict) or not payload:
        return False, [f"缺少 {relpath}"]
    if payload.get(passed_key) is False:
        return False, [f"{relpath}: {passed_key}=false"]
    blocking = payload.get("blocking")
    if isinstance(blocking, int) and blocking:
        return False, [f"{relpath}: blocking={blocking}"]
    blockers = payload.get("blockers")
    if isinstance(blockers, list) and blockers:
        return False, [f"{relpath}: {len(blockers)} 个 blocker"]
    return True, []


def done(condition: bool, *, warning: bool = False) -> str:
    if condition:
        return "done"
    return "warning" if warning else "pending"


def build_steps(root: str) -> list[dict[str, Any]]:
    lyrics_ok, lyrics_blockers = lyrics_ready(root)
    takes_registered, take_selected, take_warnings = manifest_status(root)
    master_ok, master_blockers = check_report(root, "混音/master_check.json")
    rights_ok, rights_blockers = check_report(root, "合规/rights_metadata_check.json")
    release_ok, release_blockers = check_report(root, "导出/release_pack.json", "release_ready")
    feedback_exists = rel_exists(root, "发行/feedback_summary.json")
    return [
        {
            "key": "setup",
            "label": "项目骨架与设置",
            "status": done(rel_exists(root, "_meta.json") and rel_exists(root, "_设置.md") and rel_exists(root, "_进度.md")),
            "evidence": ["_meta.json", "_设置.md", "_进度.md"],
            "blockers": [],
            "warnings": [],
            "command": f'python3 skills/song-settings/scripts/settings_cli.py "{root}" audit',
        },
        {
            "key": "brief",
            "label": "A&R 简报与参考边界",
            "status": done(rel_exists(root, "创作/song_brief.json") and rel_exists(root, "素材/reference_pack.json")),
            "evidence": ["创作/song_brief.json", "素材/reference_pack.json"],
            "blockers": [],
            "warnings": [],
            "command": f'python3 skills/song-craft/scripts/song_brief.py "{root}" --write && python3 skills/song-craft/scripts/reference_pack.py "{root}" --write',
        },
        {
            "key": "lyrics",
            "label": "歌词、Hook 与可唱性",
            "status": done(lyrics_ok and rel_exists(root, "词/lyric_prosody.json")),
            "evidence": ["词/lyrics.md", "词/lyric_prosody.json"],
            "blockers": lyrics_blockers,
            "warnings": [],
            "command": f'python3 skills/song-craft/scripts/lyric_prosody_check.py "{root}" --write',
        },
        {
            "key": "song_form",
            "label": "旋律/和声/曲式草图",
            "status": done(rel_exists(root, "歌/song_form.json") and rel_exists(root, "歌/chord_sheet.md") and rel_exists(root, "歌/topline_notes.md")),
            "evidence": ["歌/song_form.json", "歌/chord_sheet.md", "歌/topline_notes.md"],
            "blockers": [],
            "warnings": [],
            "command": f'python3 skills/song-craft/scripts/melody_chord_packet.py "{root}" --write',
        },
        {
            "key": "compose_plan",
            "label": "作曲任务包",
            "status": done(rel_exists(root, "歌/compose_task.json") and any_glob(root, "歌/compose_prompts/*.md")),
            "evidence": ["歌/compose_task.json", "歌/compose_task.md", "歌/compose_prompts/*.md"],
            "blockers": [],
            "warnings": [],
            "command": f'python3 skills/song-compose/scripts/compose_song.py "{root}"',
        },
        {
            "key": "takes",
            "label": "多版生成与登记",
            "status": done(takes_registered),
            "evidence": ["歌/takes_manifest.json", "歌/takes/*.wav"],
            "blockers": [],
            "warnings": take_warnings,
            "command": f'python3 skills/song-compose/scripts/compose_song.py "{root}" --register "<音频文件>" --take 1',
        },
        {
            "key": "selection",
            "label": "试听挑版与定稿",
            "status": done(take_selected and rel_exists(root, "歌/take_review.json")),
            "evidence": ["歌/take_review.json", "歌/song.wav"],
            "blockers": [],
            "warnings": take_warnings if takes_registered else [],
            "command": f'python3 skills/song-compose/scripts/take_review.py "{root}" --write',
        },
        {
            "key": "master_qc",
            "label": "混音/母带检查",
            "status": done(master_ok),
            "evidence": ["混音/master_check.json", "混音/master_check.md"],
            "blockers": master_blockers if rel_exists(root, "歌/song.wav") else [],
            "warnings": [],
            "command": f'python3 skills/song-review/scripts/master_check.py "{root}" --write',
        },
        {
            "key": "rights",
            "label": "权益元数据与 Split Sheet",
            "status": done(rights_ok),
            "evidence": ["合规/rights_metadata.json", "合规/split_sheet.md"],
            "blockers": rights_blockers,
            "warnings": [],
            "command": f'python3 skills/song-craft/scripts/rights_metadata.py "{root}" --write',
        },
        {
            "key": "release_pack",
            "label": "发布交付包",
            "status": done(release_ok),
            "evidence": ["导出/release_pack.json", "导出/release_pack.md"],
            "blockers": release_blockers,
            "warnings": [],
            "command": f'python3 skills/song-craft/scripts/release_pack.py "{root}" --write',
        },
        {
            "key": "feedback",
            "label": "发行数据回测",
            "status": done(feedback_exists, warning=True),
            "evidence": ["发行/feedback_summary.json", "发行/feedback_report.md"],
            "blockers": [],
            "warnings": [] if feedback_exists else ["未导入发行/投放反馈；成品发布后再回灌即可"],
            "command": f'python3 skills/song-feedback/scripts/feedback_ingest.py "{root}" --input "<反馈.csv或.jsonl>"',
        },
    ]


def build_workflow(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    steps = build_steps(root)
    next_step = next((s for s in steps if s["status"] != "done"), None)
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "current_step": next_step["key"] if next_step else "complete",
        "next_action": next_step["command"] if next_step else "",
        "steps": steps,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Song Workflow",
        "",
        f"- 生成日期：{payload['generated_at']}",
        f"- 当前步骤：{payload['current_step']}",
    ]
    if payload.get("next_action"):
        lines.append(f"- 下一步命令：`{payload['next_action']}`")
    lines.extend(["", "## Steps", ""])
    for step in payload["steps"]:
        mark = {"done": "OK", "warning": "WARN", "pending": "TODO"}.get(step["status"], "TODO")
        lines.append(f"### {mark} {step['label']} (`{step['key']}`)")
        lines.append(f"- 状态：{step['status']}")
        lines.append("- 证据：" + "、".join(f"`{item}`" for item in step["evidence"]))
        if step.get("blockers"):
            lines.append("- 阻断：" + "；".join(str(x) for x in step["blockers"]))
        if step.get("warnings"):
            lines.append("- 警告：" + "；".join(str(x) for x in step["warnings"]))
        lines.append(f"- 建议命令：`{step['command']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_workflow(root: str, payload: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "生产数据")
    json_path = os.path.join(out_dir, "song_workflow.json")
    md_path = os.path.join(out_dir, "song_workflow.md")
    write_json(json_path, payload)
    os.makedirs(out_dir, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(payload))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="检查并输出写歌默认工作流状态")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    payload = build_workflow(root)
    if args.write:
        json_path, md_path = write_workflow(root, payload)
        print(f"[ok] workflow JSON → {json_path}")
        print(f"[ok] workflow MD   → {md_path}")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
