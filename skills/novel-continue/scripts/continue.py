#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
continue.py — 章节/*.md 合并 → 导出/*.txt（v1）。docx 导出 v2 加。
支持 --combine：原作 + 新章节合一输出。

用法:
    python3 continue.py <作品根> [--title <书名>] [--combine]
"""
import argparse, json, os, re, sys
from datetime import date

CHAPTER_FILE_RE = re.compile(r"^第(\d+)章\.md$")
META_LINE_RE = re.compile(r"^<!--\s*meta:.*-->\s*$")
H1_RE = re.compile(r"^#\s+第\s*\d+\s*章\s*[《<]?([^》>]*)[》>]?\s*$")
ORIG_CHAP_RE = re.compile(r"^\s*第\s*[0-9零一二三四五六七八九十百千两]+\s*[章回节卷]")


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


def count_orig_chapters(orig_txt_path):
    return sum(1 for ln in open(orig_txt_path, encoding="utf-8") if ORIG_CHAP_RE.match(ln))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ap.add_argument("--title", default=None)
    ap.add_argument("--combine", action="store_true",
                    help="合本输出：原作 + 新章节合一")
    args = ap.parse_args()

    meta = json.load(open(os.path.join(args.project_root, "_meta.json"), encoding="utf-8"))
    title = args.title or meta.get("title") or f"{meta['source_title']}-续写"
    new_chapters = collect_chapters(args.project_root)
    if not new_chapters:
        print("[err] 章节/ 下没有 第NN章.md", file=sys.stderr); sys.exit(2)

    new_total = sum(len(t) + sum(len(ln.strip()) for ln in body) for _, t, body in new_chapters)

    if args.combine:
        out_path = os.path.join(args.project_root, "导出", f"{meta['source_title']}-合本.txt")
    else:
        out_path = os.path.join(args.project_root, "导出", f"{title}.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        # provenance
        f.write(f"# continued_from: {meta['source_title']}\n")
        f.write(f"# mode: {meta['mode']}\n")
        f.write(f"# new_chapters: {len(new_chapters)}\n")
        f.write(f"# new_chars: {new_total}\n")
        f.write(f"# direction: {meta.get('direction_chosen', 'unspecified')}\n")
        f.write(f"# rights_status: {meta['rights_status']}\n")
        f.write(f"# generated: {date.today().isoformat()}\n")
        f.write(f"# tool: novel-continue\n")
        f.write(f"# combined: {args.combine}\n\n")

        if args.combine:
            # 拼上原作
            orig_path = os.path.join(args.project_root, "原作.txt")
            orig_text = open(orig_path, encoding="utf-8").read()
            # 跳过原作头部 # 注释行
            kept = []
            skip = True
            for ln in orig_text.splitlines():
                if skip and (ln.startswith("#") or ln.strip() == ""):
                    continue
                skip = False
                kept.append(ln)
            f.write("\n".join(kept))
            if kept and kept[-1].strip():
                f.write("\n")
            f.write("\n--- 续写新章节 ---\n\n")

        # 新章节，章号从原作末章续编
        orig_count = count_orig_chapters(os.path.join(args.project_root, "原作.txt")) \
            if args.combine else 0
        for idx, t, body in new_chapters:
            display_idx = orig_count + idx if args.combine else idx
            f.write(f"第{display_idx}章 {t}".rstrip() + "\n\n")
            for ln in body:
                f.write(ln + "\n")
            f.write("\n")

    print(f"[ok] 新章节 {len(new_chapters)} 章 / {new_total} 字 → {out_path}")
    if args.combine:
        print(f"     合本模式：新章节起始编号 = 第 {orig_count + 1} 章")
    print("     docx 导出 v2 加；现可借 novel-spinoff/scripts/export.py 的 write_docx 函数。")


if __name__ == "__main__":
    main()
