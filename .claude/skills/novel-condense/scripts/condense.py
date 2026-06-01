#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
condense.py — 章节/*.md 合并 → 导出/*.txt（v1）。docx / n2d 导出 v2 加。

用法:
    python3 condense.py <作品根> [--title <书名>]
"""
import argparse, json, os, re, sys
from datetime import date

CHAPTER_FILE_RE = re.compile(r"^第(\d+)章\.md$")
META_LINE_RE = re.compile(r"^<!--\s*meta:.*-->\s*$")
H1_RE = re.compile(r"^#\s+第\s*\d+\s*章\s*[《<]?([^》>]*)[》>]?\s*$")


def collect_chapters(project_root):
    items = []
    chap_dir = os.path.join(project_root, "章节")
    if not os.path.isdir(chap_dir):
        return items
    for fname in os.listdir(chap_dir):
        m = CHAPTER_FILE_RE.match(fname)
        if not m:
            continue
        idx = int(m.group(1))
        lines = open(os.path.join(chap_dir, fname), encoding="utf-8").read().splitlines()
        title, body_start = "", 0
        for i, ln in enumerate(lines):
            mh = H1_RE.match(ln.strip())
            if mh:
                title, body_start = mh.group(1).strip(), i + 1
                break
        body = [ln for ln in lines[body_start:] if not META_LINE_RE.match(ln)]
        while body and not body[0].strip():
            body.pop(0)
        items.append((idx, title, body))
    items.sort()
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    meta = json.load(open(os.path.join(args.project_root, "_meta.json"), encoding="utf-8"))
    title = args.title or meta.get("title") or f"{meta['source_title']}-精简"
    chapters = collect_chapters(args.project_root)
    if not chapters:
        print("[err] 章节/ 下没有 第NN章.md", file=sys.stderr); sys.exit(2)

    total = sum(len(t) + sum(len(ln.strip()) for ln in body) for _, t, body in chapters)
    out_path = os.path.join(args.project_root, "导出", f"{title}.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# condensed_from: {meta['source_title']}\n")
        f.write(f"# ratio: ÷{meta.get('ratio')}\n")
        f.write(f"# target: {meta.get('target')}\n")
        f.write(f"# chapters: {len(chapters)}\n")
        f.write(f"# chars: {total}\n")
        f.write(f"# rights_status: {meta['rights_status']}\n")
        f.write(f"# generated: {date.today().isoformat()}\n")
        f.write(f"# tool: novel-condense\n\n")
        for idx, t, body in chapters:
            f.write(f"第{idx}章 {t}".rstrip() + "\n\n")
            for ln in body:
                f.write(ln + "\n")
            f.write("\n")
    print(f"[ok] {len(chapters)} 章, {total} 字 → {out_path}")
    if meta.get("target") == "漫剧":
        print("     漫剧友好版可直接喂 n2d-script；docx 导出 v2 加。")
    else:
        print("     docx 导出 v2 加；现可借 novel-spinoff/scripts/export.py 的 write_docx 函数。")


if __name__ == "__main__":
    main()
