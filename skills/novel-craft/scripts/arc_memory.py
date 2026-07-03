#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold/check arc-level memory summaries for long-form novel drafting."""
import argparse
import json
import os
import re
from datetime import date


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def parse_arc(value):
    m = re.fullmatch(r"(\d+)-(\d+)", value or "")
    if not m:
        raise SystemExit("--arc 格式应为 1-5")
    start, end = int(m.group(1)), int(m.group(2))
    if start > end:
        start, end = end, start
    return start, end


def chapter_path(root, chapter):
    return os.path.join(root, "章节", f"第{chapter:02d}章.md")


def read_excerpt(path, limit=240):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read().strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def arc_id(start, end):
    return f"ARC-{start:03d}-{end:03d}"


def scaffold(root, start, end, title):
    path = os.path.join(root, "设定", "arc_summaries.json")
    data = load_json(path, {}) or {}
    if data.get("kind") != "novel_arc_summaries":
        data = {
            "schema_version": 1,
            "kind": "novel_arc_summaries",
            "updated_at": date.today().isoformat(),
            "arcs": [],
        }
    aid = arc_id(start, end)
    data["arcs"] = [a for a in data.get("arcs", []) if a.get("id") != aid]
    evidence = []
    for chapter in range(start, end + 1):
        excerpt = read_excerpt(chapter_path(root, chapter))
        if excerpt:
            evidence.append({"chapter": chapter, "excerpt": excerpt})
    data["arcs"].append({
        "id": aid,
        "range": f"{start}-{end}",
        "title": title or f"第{start:02d}-{end:02d}章弧段",
        "plot_summary": "",
        "character_changes": [],
        "open_threads": [],
        "payoffs": [],
        "carry_forward": [],
        "source_evidence": evidence,
    })
    data["arcs"].sort(key=lambda a: parse_arc(a.get("range", "0-0"))[0])
    data["updated_at"] = date.today().isoformat()
    write_json(path, data)

    emo_path = os.path.join(root, "设定", "emotional_progression.json")
    emo = load_json(emo_path, {}) or {}
    if emo.get("kind") != "novel_emotional_progression":
        emo = {
            "schema_version": 1,
            "kind": "novel_emotional_progression",
            "updated_at": date.today().isoformat(),
            "chapters": [],
        }
    existing = {int(c.get("chapter") or 0) for c in emo.get("chapters", []) if isinstance(c, dict)}
    for chapter in range(start, end + 1):
        if chapter in existing:
            continue
        emo["chapters"].append({
            "chapter": chapter,
            "dominant_emotion": "",
            "tension_score": None,
            "reader_promise_progress": "",
            "next_emotional_debt": "",
        })
    emo["chapters"].sort(key=lambda c: int(c.get("chapter") or 0))
    emo["updated_at"] = date.today().isoformat()
    write_json(emo_path, emo)
    return path, emo_path


def check(root):
    payload = load_json(os.path.join(root, "设定", "arc_summaries.json"), {}) or {}
    findings = []
    if payload.get("kind") != "novel_arc_summaries":
        findings.append({"id": "ARC-MEMORY-MISSING", "severity": "warning", "reason": "缺少 arc_summaries.json"})
    for arc in payload.get("arcs") or []:
        missing = [k for k in ("plot_summary", "carry_forward") if not arc.get(k)]
        if missing:
            findings.append({
                "id": "ARC-MEMORY-INCOMPLETE",
                "severity": "warning",
                "arc": arc.get("id"),
                "reason": "弧段摘要缺字段：" + "、".join(missing),
            })
    return {
        "schema_version": 1,
        "kind": "novel_arc_memory_check",
        "warnings": len(findings),
        "findings": findings,
    }


def main():
    ap = argparse.ArgumentParser(description="scaffold/check arc memory summaries")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scaffold")
    sc.add_argument("project_root")
    sc.add_argument("--arc", required=True)
    sc.add_argument("--title", default="")
    ck = sub.add_parser("check")
    ck.add_argument("project_root")
    ck.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if args.cmd == "scaffold":
        start, end = parse_arc(args.arc)
        paths = scaffold(root, start, end, args.title)
        print("[ok] arc memory: " + " / ".join(paths))
        return
    result = check(root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[summary] warnings={result['warnings']}")
        for item in result["findings"]:
            print(f"- {item['id']}: {item['reason']}")


if __name__ == "__main__":
    main()
