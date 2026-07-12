#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check lyric prosody and hook readiness for songwriting."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date
from typing import Any

import song_utils


KIND = "song_lyric_prosody_check"


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


def parse_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        match = song_utils.SECTION_RE.match(stripped)
        if match:
            current = {"tag": match.group(1).strip().lower(), "raw_tag": match.group(0), "lines": []}
            sections.append(current)
            continue
        if current is None:
            continue
        if not stripped or stripped.startswith("#") or stripped.startswith(">") or song_utils.STAGE_DIR.match(stripped):
            continue
        current["lines"].append({
            "line": lineno,
            "text": stripped,
            "chars": song_utils.line_chars(stripped),
            "last_word": song_utils.extract_last_word(stripped),
        })
    return sections


def check(root: str) -> dict[str, Any]:
    lyrics_path = os.path.join(root, "词", "lyrics.md")
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    findings: list[dict[str, Any]] = []
    if not os.path.exists(lyrics_path):
        return {
            "schema_version": 1,
            "kind": KIND,
            "generated_at": date.today().isoformat(),
            "project_root": os.path.abspath(root),
            "passed": False,
            "blocking": 1,
            "warnings": 0,
            "sections": [],
            "findings": [{"id": "PROSODY-MISSING-LYRICS", "severity": "blocking", "message": "缺少 词/lyrics.md。"}],
        }
    text = open(lyrics_path, encoding="utf-8").read()
    sections = parse_sections(text)
    title = str(meta.get("title") or "").strip()
    form_type = str(meta.get("song_form_type") or meta.get("form_type") or "sectional").strip().lower()
    genre = str(meta.get("genre") or "").lower()
    chorus_required = form_type not in {"through_composed", "through-composed", "通谱", "rap", "spoken"} and "说唱" not in genre
    density_profile = "rap" if form_type in {"rap", "spoken"} or "说唱" in genre else "song"

    def issue(issue_id: str, severity: str, message: str, location: str = "词/lyrics.md") -> None:
        findings.append({"id": issue_id, "severity": severity, "message": message, "location": location})

    if not sections:
        issue("PROSODY-NO-SECTIONS", "blocking", "未解析到段落标签。")
    chorus_sections = [s for s in sections if "chorus" in s["tag"] or "副歌" in s["tag"]]
    if not chorus_sections and chorus_required:
        issue("PROSODY-NO-CHORUS", "blocking", "当前 sectional/pop 曲式缺少 chorus / 副歌段。")
    elif not chorus_sections:
        issue("PROSODY-NO-CHORUS", "warning", f"{form_type} 曲式没有副歌；请确认记忆锚由 refrain、flow 或主题动机承担。")
    else:
        chorus_text = "\n".join(row["text"] for sec in chorus_sections for row in sec["lines"])
        if title and title not in chorus_text:
            issue("PROSODY-TITLE-HOOK", "warning", "标题没有出现在副歌中；若标题不是 hook，请确认传播记忆点。", "[chorus]")
        repeated = repeated_lines(chorus_sections)
        if not repeated:
            issue("PROSODY-HOOK-REPEAT", "warning", "副歌没有明显重复句；短视频/流行歌 hook 可能不够稳。", "[chorus]")
    for sec in sections:
        counts = [row["chars"] for row in sec["lines"] if row["chars"] > 0]
        if not counts:
            continue
        spread = max(counts) - min(counts)
        avg = sum(counts) / len(counts)
        spread_limit = 10 if density_profile == "rap" else 6
        dense_limit = 28 if density_profile == "rap" else 18
        if spread > spread_limit:
            issue("PROSODY-LINE-SPREAD", "warning", f"{sec['raw_tag']} 行长极差 {spread}，旋律复用会变难。", sec["raw_tag"])
        if avg > dense_limit:
            issue("PROSODY-DENSE-LINES", "warning", f"{sec['raw_tag']} 平均 {avg:.1f} 字/行，可能咬字过密。", sec["raw_tag"])
        if avg < 4 and len(counts) >= 2:
            issue("PROSODY-SPARSE-LINES", "warning", f"{sec['raw_tag']} 平均 {avg:.1f} 字/行，可能信息不足或只适合作短 hook。", sec["raw_tag"])
    verses = [s for s in sections if "verse" in s["tag"] or "主歌" in s["tag"]]
    if len(verses) >= 2 and form_type not in {"through_composed", "through-composed", "通谱"}:
        a = [row["chars"] for row in verses[0]["lines"]]
        b = [row["chars"] for row in verses[1]["lines"]]
        if len(a) != len(b):
            issue("PROSODY-VERSE-SYMMETRY", "warning", "前两个 verse 行数不一致，同一旋律复用会变难。", "[verse]")
        elif any(abs(x - y) > 4 for x, y in zip(a, b)):
            issue("PROSODY-VERSE-LINE-MATCH", "warning", f"前两个 verse 对应行字数差异较大：{a} vs {b}。", "[verse]")
    blockers = [f for f in findings if f["severity"] == "blocking"]
    return {
        "schema_version": 2,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "passed": not blockers,
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "profile": {"form_type": form_type, "density": density_profile, "chorus_required": chorus_required},
        "sections": sections,
        "findings": findings,
    }


def repeated_lines(chorus_sections: list[dict[str, Any]]) -> list[str]:
    seen: dict[str, int] = {}
    for sec in chorus_sections:
        for row in sec["lines"]:
            text = row["text"].strip()
            if len(text) >= 4:
                seen[text] = seen.get(text, 0) + 1
    return [line for line, count in seen.items() if count >= 2]


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Lyric Prosody Check",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- passed：{report.get('passed')}",
        f"- blocking：{report.get('blocking')} warnings：{report.get('warnings')}",
        f"- profile：{(report.get('profile') or {}).get('form_type', 'sectional')} / {(report.get('profile') or {}).get('density', 'song')}",
        "",
        "## Sections",
        "",
    ]
    for sec in report.get("sections") or []:
        counts = [row["chars"] for row in sec.get("lines") or []]
        lines.append(f"- {sec.get('raw_tag')}: {len(counts)} 行 · 字数 {counts}")
    if report.get("findings"):
        lines.extend(["", "## Findings", ""])
        for item in report["findings"]:
            lines.append(f"- [{item['severity']}] {item['id']} {item.get('location')}: {item['message']}")
    return "\n".join(lines).rstrip() + "\n"


def write_report(root: str, report: dict[str, Any]) -> tuple[str, str]:
    out_dir = os.path.join(root, "词")
    json_path = os.path.join(out_dir, "lyric_prosody.json")
    md_path = os.path.join(out_dir, "lyric_prosody.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="检查歌词可唱性、hook 和乐句对称")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = check(root)
    if args.write:
        json_path, md_path = write_report(root, report)
        print(f"[ok] lyric prosody JSON → {json_path}")
        print(f"[ok] lyric prosody MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
